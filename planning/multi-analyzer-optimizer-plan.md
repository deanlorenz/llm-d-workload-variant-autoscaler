# Multi-Analyzer Optimizer — Per-Variant Slice Migration Plan

> **Status: IN PROGRESS** — Item 1 of `planning/PR1113-review.md`. Two commits landed
> on top of pre-rewrite engine tip `a93bc5dc`; 1.3–1.5 pending. Branch will cross-rebase
> onto `multi-analyzer-threshold@b8b823b0` (PR #1228) when 1.5 lands, picking up the
> registration plumbing (PR #1225, `66001d47`) and the threshold post-step + aggregation
> helpers (PR #1228, `b8b823b0`) in one hop.

---

## Context

The engine today combines per-analyzer results into a single `*AnalyzerResult` via
`combineAnalyzerResults` and passes it to the optimizer through `ModelScalingRequest.Result`.
The optimizer then drives scaling decisions off that combined value's `RequiredCapacity` /
`SpareCapacity`.

This plan replaces the engine-side combine with a **per-analyzer slice flowing through
to the optimizers**. Each optimizer reads a `[]NamedAnalyzerResult` and applies shared
free functions (`bottleneckReplicas`, `safeRemovalReplicas`, `applyAllocation`, …) over
the slice. No new public interface, no helper object, no `Combiner`. Slice mutated in
place during allocation. Pickers (cost-greedy for `CostAwareOptimizer`,
fair-share-bounded for `GreedyByScoreOptimizer`) are the only optimizer-specific
divergence.

Scale-down processes each model independently — no shared scarce resource exists during
scale-down (cluster GPU budget only grows), `SC_i ≥ 0` is local to each model's slice,
no per-(variant) cross-model `MinReplicas` floor.

---

## Architectural decisions (locked)

### Per-analyzer slice contract

`pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult` is the per-model
input the optimizer reads. Saturation is always the first entry (the keeper of variant
identity until the future pre-analysis-extraction PR removes that responsibility). Other
enabled analyzers follow in registration order.

```go
type NamedAnalyzerResult struct {
    Name      string
    Result    *interfaces.AnalyzerResult  // engine-calibrated; never mutated by helpers
    Remaining float64                     // working RC counter for the optimizer
    Spare     float64                     // working SC counter for the optimizer
}
```

**Working counters (refinement during 1.1 implementation):** the helpers
mutate `Remaining` and `Spare` as allocation progresses; `Result.RequiredCapacity`
and `Result.SpareCapacity` stay pristine. This preserves the "engine post-step
is the sole writer of RC/SC" invariant from PR #1228 — the working state of the
optimizer's iterative allocation is decoupled from the analyzer's calibrated
output. The engine initializes `Remaining`/`Spare` from `Result.RequiredCapacity`/
`Result.SpareCapacity` when populating `AnalyzerResults`.

### Linearity invariant (the contract the helpers depend on)

Adding `n` replicas of variant `v` reduces analyzer `i`'s `RequiredCapacity` by exactly
`n × PerReplicaCapacity_i[v]`. Symmetric for removal. This holds because every analyzer's
`Total*` fields are sums over per-variant primitives (enforced by
`internal/engines/aggregation/` helpers that PR #1228 introduces). An analyzer that
violates the invariant silently breaks the optimizer's allocation — analyzers must use
the helpers (or produce identical math).

### Engine writes RC/SC; optimizer reads

After PR #1228 merges, the engine post-step (`applyUniversalThreshold`) is the sole
writer of `RC`/`SC` at every scope (model + per-role). Analyzer-written values are
discarded. The optimizer reads engine-calibrated values per analyzer; per-analyzer
threshold overrides are honored upstream, so the optimizer doesn't re-resolve them.

### Pipeline helpers (`internal/engines/pipeline/analyzer_helpers.go`)

- `needsScaleUp(s)` — any-up gate: `Remaining_i > 0` for at least one analyzer.
- `needsScaleDown(s)` — all-down gate: `Spare_i > 0` for every analyzer.
- `bottleneckReplicas(s, v)` — `max_i ceil(Remaining_i / PRC_i[v])`; cold-start guard for `PRC=0`.
- `safeRemovalReplicas(s, v)` — `min_i floor(Spare_i / PRC_i[v])`.
- `applyAllocation(s, v, n)` — subtracts `n × PRC_i[v]` from each analyzer's `Remaining`; clamps to 0. Does NOT touch `Result.RequiredCapacity`.
- `applyDeallocation(s, v, n)` — symmetric for `Spare`. Does NOT touch `Result.SpareCapacity`.
- `saturationEntry(s)` — looks up saturation by name (variant-metadata keeper).
- `PickVariantFn` — optimizer-specific variant selector; returns `(variant, capN)`.
- `allocateForModel(...)` — generic scale-up inner loop using `pick`.

These operate on `[]NamedAnalyzerResult`. Distinct concern from `internal/engines/aggregation/`
(introduced by PR #1228) which operates on `[]VariantCapacity` for analyzer authors.

### Pickers

- **CostAware** picker: cheapest-first by cost-efficiency (`Cost / PRC`); cap is unlimited
  (`math.MaxInt`); GPU budget honored via `stateMap`/`available`.
- **Greedy** picker: fair-share-bounded; cap is the analyzer's fair-share target ÷ `PRC[v]`.

---

## Roadmap commits

Each commit compiles, passes `make test`, is DCO-signed.

### 1.1 ✅ `27a15e2e` — pipeline: NamedAnalyzerResult + AnalyzerResults field

Landed against `a93bc5dc` (pre-rewrite engine). Adds:
- `pipeline.NamedAnalyzerResult{Name, Result, Remaining, Spare}` — `Result` is the
  engine-calibrated `*AnalyzerResult` (never mutated); `Remaining`/`Spare` are the
  optimizer's working RC/SC counters that helpers mutate during allocation.
- `pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult` alongside legacy
  `Result`.
- Engine populates both (`Result` via combine; `AnalyzerResults` saturation-first then
  enabled non-saturation analyzers in config order, with `Remaining` initialized from
  `Result.RequiredCapacity` and `Spare` from `Result.SpareCapacity`).

**Design refinement — Remaining/Spare counters.** The original plan had helpers
mutate `Result.RequiredCapacity`/`Result.SpareCapacity` directly. During implementation
we noticed this conflicts with PR #1228's "engine post-step is the sole writer of
RC/SC" invariant: once the optimizer mutates `Result.RC`, the analyzer's calibrated
output is lost. The fix is to add separate working counters on `NamedAnalyzerResult`
and have helpers operate on those. The helper API stays the same shape (same names,
same signatures); only the field they touch changes.

**Cross-rebase reshape needed** — see § Cross-rebase mechanics below.

### 1.2 ✅ `3b21c347` — pipeline: helpers in `analyzer_helpers.go`

Landed against `a93bc5dc`. Adds the 8 helpers listed above + 21 specs.
Helpers operate on `Remaining`/`Spare` and never mutate `Result`. Helpers
intentionally unused by optimizers at this commit; wired in 1.3/1.4.

**Cross-rebase impact:** clean (pure addition to `pipeline/`; no engine changes).

### 1.3 ✅ `d35aa532` — CostAware migration

`CostAwareOptimizer` migrated to per-analyzer slice via the new helpers.

**Landed:**

1. **Gate:** `needsScaleUp(req.AnalyzerResults)` / `needsScaleDown(req.AnalyzerResults)`
   replace `req.Result.RequiredCapacity > 0` / `SpareCapacity > 0`.
2. **Scale-up:** `allocateForModel(...)` + `costGreedyPick` (cheapest by `cost / PRC[v]`,
   `capN = math.MaxInt`, respects `maxReplicas` headroom + GPU budget via
   `stateMap`/`available`).
3. **Scale-down:** safe-removal loop using `safeRemovalReplicas(req.AnalyzerResults, v)`
   + `applyDeallocation`. Cheapest-variant protection retained; `minReplicas` honored.
4. **Variant metadata:** `saturationEntry(req.AnalyzerResults).VariantCapacities` for
   `Cost`/`AcceleratorName`/`Role`.
5. **`buildDecisionsWithOptimizer`:** still reads `req.Result` for reason strings + per-variant
   `Utilization`. Cleaned in 1.5.
6. **Greedy unchanged** — still reads `req.Result`. Greedy scale-down call site updated to
   the new function signature.
7. **Tests:** `cost_aware_optimizer_test.go` fixtures updated to populate `AnalyzerResults`.

### 1.4 ⏳ — Greedy migration

Migrate `GreedyByScoreOptimizer` to read `req.AnalyzerResults`.

- Add `fairShareValue(priority, s)` private helper computed on demand from the working
  slice (no stored `Score` field needed).
- Provide a fair-share-bounded `PickVariantFn`.
- Replace `fairShareScaleUp` / `allocateToVariants` with `allocateForModel`.
- Per-role logic: read `req.AnalyzerResults[i].Result.RoleCapacities[role]` (engine
  post-step writes per-role RC/SC).
- Update `greedy_score_optimizer_test.go`.

### 1.5 ⏳ — Cleanup (simplified post-cross-rebase)

After cross-rebase onto threshold tip, several items are already done upstream. Final
state of 1.5:

| Item | Status post-rebase |
|---|---|
| Delete `combineAnalyzerResults` | **Already done** (registration PR deleted it). |
| Delete `enabledAnalyzerResult` | **Already done**. |
| Delete `engine_combine_test.go` | **Already done**. |
| Drop `ModelScalingRequest.Result` field | Pending in 1.5. |
| Drop `AnalyzerResult.Score` field | Pending in 1.5. |
| Rename `runAnalyzersAndScore` → `runAnalyzers` | Pending in 1.5. |
| Drop saturation-only score-compute loop in engine | Pending in 1.5 (threshold still computes Score on saturation's calibrated RC). |
| Final dev-guide commit | Pending (small additions; threshold's dev-guide rewrite already covers most of the architecture). |

`buildDecisionsWithOptimizer` reason-strings that still reference `req.Result.RequiredCapacity` /
`SpareCapacity` cleaned up here. `Utilization` plumbing for `VariantDecision` stays
(reads `vc.Utilization` per variant — unchanged).

---

## Cross-rebase mechanics (after 1.5 lands locally; before push)

### Target

Rebase the 1.1–1.5 stack onto `multi-analyzer-threshold@b8b823b0` (PR #1228 head).

That picks up in one hop:
- Registration plumbing (`66001d47`): `analyzers []analyzerEntry` + `analyzersSnapshot` +
  `started bool` + race-fix; `RegisterAnalyzer` panics on duplicate name and on late
  registration.
- Combine deletion (registration PR): `combineAnalyzerResults`, `enabledAnalyzerResult`,
  `sumTotalCapacity`, `engine_combine_test.go` — all already gone upstream.
- Threshold post-step (`b8b823b0`): `applyUniversalThreshold` + `resolveThresholds`;
  engine writes RC/SC for saturation and every role; per-analyzer threshold overrides
  honored at every scope.
- Aggregation helpers (`internal/engines/aggregation/`): `SumTotalSupply`,
  `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`. Used by analyzers,
  not by the optimizer's pipeline helpers.
- Sat_v2 simplification: drops in-analyzer RC/SC (engine post-step is sole writer);
  uses aggregation helpers; populates `TotalAnticipatedSupply` and per-role
  `TotalAnticipatedSupply`.

### Expected conflicts

| File | Conflict scope |
|---|---|
| `internal/engines/saturation/engine_v2.go` | **Major.** 1.1's combine-and-collect rewrite of `runAnalyzersAndScore` collides with threshold's post-step-and-discard rewrite. Manual reshape required (see below). |
| `internal/engines/saturation/engine_combine_test.go` | Both delete; trivial. |
| `internal/engines/pipeline/optimizer_interfaces.go` | Clean (threshold doesn't touch). |
| `internal/engines/pipeline/analyzer_helpers.go` + test | Clean (1.2 pure addition). |
| `internal/engines/pipeline/cost_aware_optimizer.go` (after 1.3) | Likely clean — threshold doesn't touch optimizer files. |
| `internal/engines/pipeline/greedy_score_optimizer.go` (after 1.4) | Likely clean. |

### `runAnalyzersAndScore` reshape

The signature evolution:

```
a93bc5dc base:    (...) (*AnalyzerResult, error)                     // returns combined
optimizer 1.1:    (...) ([]NamedAnalyzerResult, *AnalyzerResult, error)  // adds named slice
threshold tip:    (...) (*AnalyzerResult, error)                     // returns sat-only-calibrated
post-rebase:      (...) ([]NamedAnalyzerResult, error)               // slice only; sat at slice[0]
```

Caller-side (`collectV2ModelRequest`):

```go
namedResults, err := e.runAnalyzersAndScore(...)
if err != nil { return nil, err }
req.AnalyzerResults = namedResults
if len(namedResults) > 0 {
    req.Result = namedResults[0].Result   // transitional; 1.5 drops Result field
}
```

Engine-side body (after rebase):

```go
// 1. Run saturation via runV2AnalysisOnly (threshold's pattern).
satResult, err := e.runV2AnalysisOnly(ctx, ...)
if err != nil { return nil, err }

// 2. Apply post-step to saturation (threshold's pattern, kept verbatim).
satUp, satDown := resolveThresholds(interfaces.SaturationAnalyzerName, config)
applyUniversalThreshold(satResult, satUp, satDown)

// 3. Build AnalyzerInput once.
input := interfaces.AnalyzerInput{...}

// 4. Iterate snapshot, run + calibrate + COLLECT non-saturation results.
namedResults := []pipeline.NamedAnalyzerResult{
    {Name: interfaces.SaturationAnalyzerName, Result: satResult},
}
for _, entry := range e.analyzersSnapshot {
    if entry.name == interfaces.SaturationAnalyzerName { continue }
    result := runRegisteredAnalyzer(ctx, logger, entry, modelID, input)
    if result == nil { continue }
    up, down := resolveThresholds(entry.name, config)
    applyUniversalThreshold(result, up, down)
    namedResults = append(namedResults, pipeline.NamedAnalyzerResult{Name: entry.name, Result: result})
}

// 5. Score (still on saturation's calibrated RC; dropped in 1.5).
totalWeighted := 0.0
for _, aw := range config.Analyzers {
    if aw.Enabled != nil && !*aw.Enabled { continue }
    if aw.Name == interfaces.SaturationAnalyzerName {
        totalWeighted += satResult.RequiredCapacity * aw.Score
    }
}
satResult.Score = config.Priority * totalWeighted

return namedResults, nil
```

The shape: threshold's strict-no-fallback post-step semantics are preserved verbatim;
only the discard step is replaced with append-and-collect. `runRegisteredAnalyzers`
(plural) becomes redundant after this reshape — its body inlines into the loop above.
Either delete it or keep it as a side-helper that returns the collected slice; choose
whichever yields the cleaner diff.

### Rebase steps

```
git -C multi-analyzer-optimizer fetch origin multi-analyzer-threshold
git -C multi-analyzer-optimizer rebase b8b823b0
# Resolve conflict in engine_v2.go per § runAnalyzersAndScore reshape above.
# 1.1's commit body and message stay; only the conflict-resolution adjusts the diff.
git rebase --continue
# 1.2 should apply cleanly (pure addition).
# 1.3 / 1.4 / 1.5 (when present) likely clean — but verify each.

# Verify after rebase:
gofmt -l ./internal/... ./pkg/... ./cmd/...
go vet ./...
go build ./...
make test
go test -race ./internal/engines/saturation/...
git log b8b823b0..HEAD --format='%h %s%n%b' | grep -E '^[0-9a-f]+|Signed-off-by'  # DCO check
```

Force-push policy: `--force-with-lease`, only after all commits land locally and verify
clean. State reason ("rebased onto multi-analyzer-threshold tip per cross-rebase plan").
**Do NOT push without explicit Dean confirmation per CONVENTIONS.**

The pre-rebase tip (current `956e60b6`) stays reachable via `git reflog` for ~30 days.

---

## Verification gates

Each commit (existing or new) must satisfy:

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty output.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- DCO sign-off (`Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`).

Final pre-push gate after cross-rebase: `go test -race ./internal/engines/saturation/...`
clean.

---

## Coordination

- **PR #1225 (`multi-analyzer-registration`)** — base for this branch's eventual cross-rebase
  (transitively, via threshold). Stable. Awaiting reviewer.
- **PR #1228 (`multi-analyzer-threshold`)** — cross-rebase target. Awaiting reviewer.
  Threshold post-step + aggregation helpers + sat_v2 simplification all sit on top of
  registration's commits.
- **`engine-queue-fix`** — blocked on whichever Item 3 PR (PR #1225) merges. Independent
  of this branch.
- **PR #1113** — superseded; will be closed by Dean after coordinating with ev-shindin.

This branch does **not** depend on either PR merging before continuing 1.3–1.5 locally.
The cross-rebase happens after 1.5 lands locally; until then, work proceeds against the
current `956e60b6` tip on `a93bc5dc`.

---

## Open items

- **Q4 — picker contract / cap responsibility (Commit 1.4).** `allocateForModel` takes
  `min(capN, bottleneckReplicas)`. For Greedy, `capN` comes from the fair-share target ÷ PRC.
  Not blocking — defaulting to this; flag for review when 1.4 is ready.
- **Q5 — test layer placement.** Catalog the migrated combine specs from `engine_combine_test.go`
  before moving any. Helper layer (1.2 — done) vs optimizer layer (1.4). Will list the
  catalog in the next status handoff.
- **`TryAllocate(ctx, ...)` signature change** from PR #1026: appears at rebase time;
  mechanical pass-through.
- **Per-analyzer threshold overrides:** honored upstream by PR #1228. Optimizer reads
  engine-calibrated values; no further work on this front in this PR.
- **Future pre-analysis extraction:** sat_v2 today carries variant identity (Cost,
  AcceleratorName, Role, replica counts) that any analyzer or the optimizer may need.
  The deferred future PR extracts that into a common pre-analysis stack so sat_v2 becomes
  one of N peers. **Out of scope** for this PR; `saturationEntry()` helper in
  `analyzer_helpers.go` is a TODO marker for that follow-up.
- **Per-analyzer observability metrics** (Prometheus gauges labeled by `analyzer_name`):
  follow-up after this PR merges. Already noted in `session/CURRENT.md` "Issues to Open".
