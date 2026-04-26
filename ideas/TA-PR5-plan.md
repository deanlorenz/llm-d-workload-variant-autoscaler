# PR-5: Wire ThroughputAnalyzer into the Engine Pipeline

> **Status: PLANNED** — Target branch TA3. Depends on PR-3 (#1052) and PR-4 merging first.
> Part of #1005; does not close it.

## Context

PRs 1–4 built and tested the ThroughputAnalyzer in isolation. PR-5 completes the
multi-analyzer infrastructure that is already partially in place in `runAnalyzersAndScore`
and registers the ThroughputAnalyzer into it.

**Scope:** engine wiring only. No changes to the analyzer package, the collector, the
optimizer, or existing analyzers.

---

## Relationship to the Queueing Model Analyzer

The queueing model analyzer has its own `optimizeQueueingModel()` path — it replaces
saturation entirely via a `switch analyzerName` in `optimize()`. It does not go through
`runAnalyzersAndScore` and cannot run alongside other analyzers.

The ThroughputAnalyzer is different: it goes through `runAnalyzersAndScore` alongside
saturation V2. This is the intended multi-analyzer path — `config.Analyzers` already
carries the per-analyzer `Enabled`, `Score`, and threshold overrides for it.

---

## What Is Already in Place

### Generic infrastructure (exists today)

- `interfaces.Analyzer` — `Name() string` + `Analyze(ctx, AnalyzerInput) (*AnalyzerResult, error)`.
  Both `SaturationAnalyzer` (V2) and `ThroughputAnalyzer` implement it.
- `config.Analyzers []AnalyzerScoreConfig` — per-analyzer `Enabled *bool`, `Score float64`,
  `ScaleUpThreshold`, `ScaleDownBoundary`. The existing scoring loop in `runAnalyzersAndScore`
  iterates this list with the comment `// future: add "throughput", "slo" cases`.
- `GreedyByScoreOptimizer` — already handles multiple models (fair-share by Score),
  multiple variants (cheapest first via `cost/perReplicaCapacity`), P/D role allocation
  (by `RoleCapacities` demand fractions), and GPU constraints. It consumes a single
  `AnalyzerResult` per model; `runAnalyzersAndScore` is responsible for producing it.
- `CostAwareOptimizer` — same variant and replica logic, unlimited mode.

### What TA3 adds (already committed)

- `ThroughputAnalyzer.Analyze()` — returns `AnalyzerResult` with `RequiredCapacity`,
  `SpareCapacity`, `VariantCapacities.PerReplicaCapacity` in tok/s units.
- `RegisterThroughputAnalyzerQueries()` — registers three Prometheus queries.
- `replica_metrics.go` — already populates `GenerationTokenRate`, `KvUtilization`,
  `VLLMRequestRate` on every cycle.

---

## Key Design Decisions

### Generic runner, not name-dispatched

`runAnalyzersAndScore` should iterate `config.Analyzers` and look up each by name in
a registered map of `interfaces.Analyzer`. It does not need to know which specific
analyzer it is running — it just calls `Analyze()` and collects the result.

The existing name-dispatch (`if aw.Name == interfaces.SaturationAnalyzerName`) is replaced
by a generic lookup: `analyzer, ok := e.analyzers[aw.Name]`.

### Single AnalyzerResult to the optimizer

The optimizer takes one `AnalyzerResult` per model. The engine combines results from
all enabled analyzers before calling the optimizer. Combining is generic:

- **Scale up** if **any** enabled analyzer returns `RequiredCapacity > 0`.
- **Scale down** only if **all** enabled analyzers agree (`SpareCapacity > 0`).

Since analyzers use different capacity units, combining is done in replica space:
`replicas_needed_i = ceil(RC_i / PerReplicaCapacity_i)` per variant per analyzer.
The combined replica target is then re-expressed as RC in saturation units (using
saturation's `PerReplicaCapacity`) so the optimizer receives a consistent result.

Saturation's `VariantCapacities` are used as the base for the combined result — they
provide the `Cost`, `AcceleratorName`, and `Role` fields the optimizer needs for
variant selection, P/D allocation, and GPU accounting.

### Per-analyzer enable/disable

Users add entries to `config.Analyzers` to enable or disable each analyzer:

```yaml
analyzers:
  - name: saturation
    enabled: true
    score: 1.0
  - name: throughput
    enabled: true
    score: 1.0
```

For e2e isolation (TA only):

```yaml
analyzers:
  - name: saturation
    enabled: false
  - name: throughput
    enabled: true
    score: 1.0
```

The saturation capacity-store pre-population (`LoadFromScaleTarget`) must still run
when saturation data is needed — this is a side-effect step that stays outside the
generic loop.

### SchedulerQueue remains nil

`AnalyzerInput.SchedulerQueue` is nil (existing TODO). `estimateQueueDemand` returns
0 gracefully. Queue demand wiring is a separate later PR.

### No TA-specific config

`ThroughputAnalyzer.Analyze()` ignores `input.Config` and uses internal constants.
No new ConfigMap type needed.

---

## Components

### `internal/interfaces/analyzer.go`

Add `ThroughputAnalyzerName = "throughput"` constant.

### `internal/engines/saturation/engine.go`

- **`Engine` struct**: add `analyzers map[string]interfaces.Analyzer` (name → implementation).
- **`NewEngine()`**:
  - Populate the map: `"saturation"` → `saturation_v2.NewSaturationAnalyzer(capacityStore)`,
    `"throughput"` → `throughput.NewThroughputAnalyzer()`.
  - Call `registration.RegisterThroughputAnalyzerQueries(metricsRegistry)`.
  - The named fields `saturationV2Analyzer` may stay for capacity-store pre-population
    (called outside the generic loop) or be replaced by a type-assert from the map.

### `internal/engines/saturation/engine_v2.go` — `runAnalyzersAndScore()`

Three changes:

1. **Generic execution**: replace the name-dispatch with a map lookup. For each enabled
   `aw` in `config.Analyzers`, call `e.analyzers[aw.Name].Analyze(ctx, input)`.

2. **Generic combine**: convert each result to replicas via `RC / PerReplicaCapacity`,
   apply any-up / all-down, re-express as RC in saturation units. Return the single
   combined `AnalyzerResult`.

3. **Generic Score**: `totalWeighted += result.RequiredCapacity × aw.Score` for each
   enabled analyzer (removes the TODO comment).

---

## Data Flow

```
config.Analyzers: [{saturation, enabled, score}, {throughput, enabled, score}]
    │
    runAnalyzersAndScore()
        │
        capacity store pre-population (saturation-specific, outside loop)
        │
        for each enabled aw:
            result_i = e.analyzers[aw.Name].Analyze(ctx, AnalyzerInput)
        │
        combine(results):
            replicas_i = ceil(RC_i / PerReplicaCapacity_i) per variant per analyzer
            RC_combined = max(replicas) × sat.PerReplicaCapacity  [any-up]
            SC_combined = min(freed)  × sat.PerReplicaCapacity    [all-down]
            Score       = priority × Σ(RC_i × score_i)
        │
        return AnalyzerResult{RC_combined, SC_combined, VariantCapacities_sat, Score}
        │
    optimizer.Optimize():
        GreedyByScore: fair-share across models by Score, cheapest variant first,
                       role-proportional for P/D, GPU-constrained
        CostAware:     unlimited, cheapest variant, no cross-model coordination
        │
    ScaleToZeroEnforcer per model
        │
    applySaturationDecisions()
```

---

## E2e Tests

Planned as part of this PR (or immediately before submission). High-level scenarios:

- **Scale-up under load**: simulator with known ITL + request rate > single-replica
  supply → TA RC > 0 → replica added.
- **Scale-down on idle**: load drops, EPP deployed → TA SC > 0 → replica removed.
- **TA-only mode** (`saturation: enabled: false`): TA drives all decisions; isolates
  TA behavior for validation without saturation interference.
- **Both analyzers**: either triggers scale-up; scale-down requires both to agree.
- **Cold start**: tier-2 constrained OLS path still emits a valid non-zero signal.

Simulator parameters used: `--inter-token-latency`, `--max-num-seqs`, `--kv-cache-size`,
`--block-size`. The detailed e2e plan (exact parameters and expected replica counts)
will be a sub-document of this PR.

---

## Not in this PR

- SchedulerQueue wiring (flow-control metrics) — later PR
- Tier-3 `itlKnowledgeStore` wiring — later PR
- `DefaultKSat` alignment with EPP system-wide k_sat — later PR
- Prefill-specific rate signals — later PR
