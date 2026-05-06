# ENGINE: Generic Multi-Analyzer Pipeline

> **Status: PLANNED** — Independent of TA branches. No dependency on TA1/TA2/TA3.
> Part of #1005 (infrastructure enabler). Unblocks the TA wiring PR.

---

## Context

The engine today has a hardcoded saturation-only path in `runAnalyzersAndScore()`. Adding
a second analyzer currently requires name-dispatch (`if aw.Name == "throughput"`). This PR
replaces the name-dispatch with a generic map-based runner and implements a correct
multi-analyzer combine step.

The changes are confined to the engine orchestration layer
(`internal/engines/saturation/`). No analyzer packages, no collector, no optimizer, no
CRD changes.

---

## What Exists Today

### Generic pieces already in place

- `interfaces.Analyzer` — `Name() string` + `Analyze(ctx, AnalyzerInput) (*AnalyzerResult, error)`.
  Both `SaturationAnalyzer` (V2) and `ThroughputAnalyzer` implement it.
- `config.Analyzers []AnalyzerScoreConfig` — per-analyzer `Enabled *bool`, `Score float64`,
  `ScaleUpThreshold`, `ScaleDownBoundary`. The scoring loop in `runAnalyzersAndScore` already
  iterates this list; it just name-dispatches inside.
- `GreedyByScoreOptimizer` — consumes a single `AnalyzerResult` per model; handles
  multi-variant fair-share by `Score`, cheapest-first scale-up, and GPU accounting via
  `AcceleratorName`.
- `CostAwareOptimizer` — same, unlimited mode.

### What the current `runAnalyzersAndScore` does

```
1. Apply per-saturation threshold overrides from config.Analyzers
2. Call runV2AnalysisOnly() → baseResult (saturation's AnalyzerResult)
3. Score loop over config.Analyzers:
     if aw.Name == SaturationAnalyzerName:
         totalWeighted += baseResult.RC × aw.Score
         // future: add "throughput", "slo" cases
4. baseResult.Score = priority × totalWeighted
5. return baseResult
```

The "future" comment is what this PR implements.

---

## Design Decisions

### D1 — Generic map-based runner (accepted)

Replace the name-dispatch with a registered map of `interfaces.Analyzer` on the
`Engine` struct:

```go
analyzers map[string]interfaces.Analyzer  // name → implementation
```

`runAnalyzersAndScore` iterates `config.Analyzers` and looks up each analyzer by name:
```
for _, aw := range config.Analyzers {
    analyzer, ok := e.analyzers[aw.Name]
    if !ok { /* log unknown, skip */ continue }
    result, err := analyzer.Analyze(ctx, input)
    ...
}
```

The saturation analyzer is still in the map (`"saturation"` key). Its special treatment
(always-run, metadata source) is handled outside the generic loop.

**Rejected alternative:** Keep adding `case "throughput":` branches. This requires engine
changes for every new analyzer and grows unboundedly.

### D2 — Saturation always runs, even when `enabled: false` (accepted)

The optimizer requires `Cost` and `AcceleratorName` per variant for:
- Scale-up variant selection: `sortByCostEfficiencyAsc` (cheapest first)
- Scale-down variant selection: `sortByCostDesc` (most expensive first)
- GPU inventory: `available[vc.AcceleratorName]` — if `""`, the optimizer skips the variant

These fields come exclusively from the CRD (via the capacity store / VA spec). Only the
saturation analyzer has access to them. Other analyzers (e.g., throughput) read only
Prometheus metrics and have no CRD access.

Therefore: saturation always runs. The `enabled: false` flag only controls whether
saturation's RC/SC contribute to the combine step. Saturation's `VariantCapacities`
(with `Cost`, `AcceleratorName`, `Role`) always form the base of the returned
`AnalyzerResult`.

**Future improvement:** When `VariantReplicaState` is extended to carry `Cost` and
`AcceleratorName` (currently read from scale target but not exposed on the state), the
engine can populate these fields directly without requiring saturation to run.

### D3 — Package location: stay in `saturation` for now

`engine.go` and `engine_v2.go` currently live in `internal/engines/saturation/`. The
code orchestrates all analyzers, not just saturation — but renaming the package now would
be large churn with no functional benefit.

**Recommendation:** Keep in `saturation` package for this PR. Track a future rename
(e.g., to `multianalyzer` or `autoscaler`) as a cleanup PR once at least two analyzers
are registered and the package no longer feels saturation-specific.

### D4 — Combine algorithm: model-level, dimensionless normalization (replaces D4 from PR-5 plan)

**Key constraint:** Multiple analyzers use different capacity units (tokens for saturation,
tok/s for throughput). Their RC/SC values cannot be directly compared or added.

**Key insight:** RC and SC are model-level aggregates, not per-variant. The combine
determines:
1. **Direction** — should we scale up or down?
2. **Magnitude** — by how much, in saturation units (so the optimizer can use saturation's VariantCapacities)?

The optimizer handles per-variant allocation from the combined model-level RC/SC using
each variant's `PerReplicaCapacity`, `Cost`, and `AcceleratorName`.

**Algorithm:**

For each enabled analyzer `i` (after running saturation separately for metadata):

```
# Normalize RC/SC to dimensionless utilization fraction
sat_total = Σ_v ( VariantCapacities_sat_v.TotalCapacity )   # current total sat supply

util_excess_i = RC_i / Σ_v ( VariantCapacities_i_v.TotalCapacity )  # if > 0: analyzer says insufficient supply
util_slack_i  = SC_i / Σ_v ( VariantCapacities_i_v.TotalCapacity )  # if > 0: analyzer says excess supply

# Cold-start guard: if TotalCapacity_i = 0 and RC_i > 0 → needs at least 1 replica
cold_start_i = (TotalCapacity_i == 0 AND RC_i > 0)
```

Combine:
```
scale_up   = any_i ( util_excess_i > 0 OR cold_start_i )   # any analyzer sees insufficient supply
scale_down = all_i ( util_slack_i > 0 )                    # all analyzers see excess supply

combined.RC = max_i( util_excess_i ) × sat_total   # back to saturation units
combined.SC = min_i( util_slack_i )  × sat_total   # 0 if any analyzer disagrees
```

The returned `AnalyzerResult` carries:
- `RequiredCapacity = combined.RC` (> 0 triggers scale-up)
- `SpareCapacity = combined.SC` (> 0 triggers scale-down)
- `VariantCapacities = saturation's VariantCapacities` (with Cost, AcceleratorName, Role, PerReplicaCapacity)
- `Score = priority × Σ_i( RC_i × aw.Score_i )`

The optimizer then resolves per-variant decisions: for scale-up, which combination of
variants (cheapest first) covers `RC`? For scale-down, which variants (most expensive
per supply first) free up `SC`?

**Why this normalization:**
- `Σ_v(TotalCapacity_i_v)` is the true total model supply in analyzer i's units, weighted
  by actual replica counts — not a mean, not a simplification.
- `util_excess_i` is dimensionless: "what fraction more supply is needed?"
- Combining dimensionless fractions with `max`/`min` is unit-safe.
- Denormalizing with `sat_total` gives the optimizer a magnitude in the units it expects.

### D5 — Analyzer name constants stay in their respective packages

`const ThroughputAnalyzerName = "throughput"` lives in the `throughput` package
(already present as `throughput.AnalyzerName`). It is NOT added to `interfaces/analyzer.go`.

`interfaces.SaturationAnalyzerName` stays in interfaces only because the saturation
engine uses it internally for config override logic (threshold overrides applied before
running the saturation analyzer). This is saturation-specific; it is not a generic
contract.

### D6 — SchedulerQueue stays nil

`AnalyzerInput.SchedulerQueue` is nil (existing TODO). `estimateQueueDemand` in the
throughput analyzer returns 0 gracefully. Queue wiring is a separate later PR.

---

## Files to Change

| File | Change |
|---|---|
| `internal/engines/saturation/engine.go` | Add `analyzers map[string]interfaces.Analyzer`; populate in `NewEngine()`; register TA queries |
| `internal/engines/saturation/engine_v2.go` | Rewrite `runAnalyzersAndScore()`: generic loop + combine |

No changes to analyzer packages, collector, optimizer, or CRD.

---

## `engine.go` Changes

Add `analyzers map[string]interfaces.Analyzer` to the `Engine` struct (alongside the
existing named fields, which stay for now as the capacity-store pre-population path):

```go
// analyzers is the generic name-to-implementation registry used by runAnalyzersAndScore.
analyzers map[string]interfaces.Analyzer
```

In `NewEngine()`, after creating `saturationV2Analyzer` and `capacityStore`:

```go
engine.analyzers = map[string]interfaces.Analyzer{
    interfaces.SaturationAnalyzerName: saturation_v2.NewSaturationAnalyzer(capacityStore),
    throughput.AnalyzerName:           throughput.NewThroughputAnalyzer(),
}
```

Also call `registration.RegisterThroughputAnalyzerQueries(metricsRegistry)` alongside
the existing saturation/queueing/scale-to-zero registrations.

The named `saturationV2Analyzer` field is kept — it is still referenced directly in
`runV2AnalysisOnly()` for the capacity-store pre-population path (which must run before
the analyzer loop).

---

## `engine_v2.go` Changes to `runAnalyzersAndScore()`

Three changes to the existing function:

**1. Pre-population step** — unchanged. The capacity store pre-population (reading
`VariantAutoscaling` CRD → `Cost`, `AcceleratorName`) always runs before the analyzer
loop, since it is a prerequisite for saturation's VariantCapacities to be meaningful.

**2. Saturation always runs** — call `runV2AnalysisOnly()` unconditionally to obtain
`satResult` (the base with `VariantCapacities` carrying `Cost`, `AcceleratorName`, `Role`).
Track whether saturation's `enabled` flag is set to decide whether its RC/SC contribute
to the combine.

**3. Generic loop + combine** — for each `aw` in `config.Analyzers` with `enabled != false`:

```
for _, aw := range config.Analyzers {
    if aw.Enabled != nil && !*aw.Enabled { continue }
    analyzer, ok := e.analyzers[aw.Name]
    if !ok { log.Info("unknown analyzer, skipping", "name", aw.Name); continue }

    result_i, err := analyzer.Analyze(ctx, input)
    if err != nil { log.Error(...); continue }

    results = append(results, analyzerWeighted{result: result_i, score: aw.Score})
}

combined := combineResults(satResult, results)   // implements D4 algorithm above
combined.Score = config.Priority * totalWeighted  // Σ(RC_i × score_i) from enabled analyzers
return combined, nil
```

The `combineResults` helper implements D4: normalize each analyzer's RC/SC to
dimensionless utilization excess/slack using each analyzer's own TotalCapacity sum, apply
any-up/all-down, denormalize using saturation's TotalCapacity. Returns an `AnalyzerResult`
with saturation's `VariantCapacities` as the base (preserving `Cost`, `AcceleratorName`,
`Role` for the optimizer).

---

## Unit Tests

New test file `internal/engines/saturation/engine_combine_test.go` covers:

| Scenario | Verify |
|---|---|
| Single analyzer (saturation only) | Pass-through: combined == saturation result |
| Two analyzers, both say scale-up | combined.RC = max(util_excess_sat, util_excess_tp) × sat_total |
| Two analyzers, only TA says scale-up | combined.RC > 0 (any-up fires) |
| Two analyzers, only saturation says scale-down | combined.SC = 0 (all-down requires agreement) |
| Both say scale-down | combined.SC = min(util_slack) × sat_total |
| Saturation disabled, TA enabled | saturation RC/SC zeroed from combine; saturation VariantCapacities still in returned result |
| Unknown analyzer name in config | Logged and skipped; remaining analyzers processed |
| Cold-start (TotalCapacity = 0, RC > 0) | combined.RC > 0 (scale-up triggered) |

---

## E2E Tests

Two scenarios validating the multi-analyzer combine at the engine level (no TA-specific
Prometheus setup needed — use the existing simulator framework):

| Scenario | Config | What to verify |
|---|---|---|
| Saturation-only scale-up | `analyzers: [{saturation, enabled:true, score:1.0}]` | RC from saturation flows through unchanged (regression: existing behavior preserved) |
| Dual-analyzer, TA triggers up but saturation idle | `analyzers: [{saturation, enabled:true, score:0.5}, {throughput, enabled:true, score:0.5}]` with simulated high tok/s demand | Combined RC > 0 → replica added even though saturation says RC = 0 |

---

## Not in This PR

- ThroughputAnalyzer registration in the engine — separate TA wiring PR
- Renaming `saturation` engine package — future cleanup PR
- Moving `Cost`/`AcceleratorName` out of capacity store — requires VariantReplicaState extension
- SchedulerQueue wiring
- Per-analyzer `ScaleUpThreshold`/`ScaleDownBoundary` override generalization (currently
  only applied for saturation; can be generalized in a later PR)

---

## Open Questions

**OQ1: What happens when `sat_total = 0` in `combineResults`?**
When all replicas are at zero (true cold start), saturation's TotalCapacity = 0.
Denormalization fails. Mitigation: detect `sat_total = 0` and special-case:
if any analyzer has RC > 0, return a unit RC (e.g., `combined.RC = 1.0` in saturation
units) to trigger the optimizer to add at least one replica. The optimizer will pick
the cheapest variant.

**OQ2: Score formula when saturation is disabled.**
When `saturation: enabled: false`, saturation contributes RC=0 to the score sum.
`Score = priority × (0×sat_score + RC_tp×tp_score)`. This is correct: the score
reflects TA's demand only, which is the right priority signal for the cross-model
optimizer.
