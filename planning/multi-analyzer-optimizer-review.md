# Multi-Analyzer Optimizer — Code Review

**Status: FINAL**
**Reviewer:** plan-agent (reviewer role), 2026-06-07
**Branch reviewed:** `multi-analyzer-optimizer` @ `233867bd` (8 commits on `multi-analyzer-threshold@b8b823b0`).
**Compared against:** [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) and [`multi-analyzer-design.md`](multi-analyzer-design.md).

> Method: read the code first to understand what it does, then compared
> against the plan + design doc. No code modifications. No tests run in the
> coder's worktree; relied on the coder's "all gates green" report per
> Dean's standing instruction.

---

## What the code does (independent reading)

### Slice contract
`pipeline.NamedAnalyzerResult{Name, Result, Score, Remaining, Spare, RoleSpare}`
carries each analyzer's engine-calibrated result plus optimizer working
state. Engine builds `AnalyzerResults` saturation-first, then enabled
non-saturation analyzers in registration order. `Remaining`/`Spare`
initialised from `Result.RequiredCapacity`/`SpareCapacity` (model scope).
For disaggregated models the optimizer calls `initDisaggregatedRemaining(s)`
which overwrites `Remaining` with `RoleCapacities[prefill].RC` (P-scope) and
populates `RoleSpare[role]` per role from `RoleCapacities[role].SC`.

### Helpers (`analyzer_helpers.go`)
- **Single-variant** (non-disaggregated): `needsScaleUp`, `needsScaleDown`,
  `bottleneckReplicas`, `safeRemovalReplicas`, `applyAllocation`,
  `applyDeallocation`, `saturationEntry`, `PickVariantFn`,
  `allocateForModel`.
- **Paired** (disaggregated scale-up): `analyzerAlpha`,
  `bottleneckReplicasPaired`, `applyAllocationPaired`, `PickPairFn`,
  `allocateForModelPaired`. α derived from `RoleCapacities[*].TotalDemand`.
  Edge cases: P>0,D>0 → α=D/P; P>0,D=0 → α=0,!tracksD; P=0,D>0 → α=1,
  !tracksP; both=0 → !tracksP,!tracksD.
- **Role-iterated** (disaggregated scale-down):
  `safeRemovalReplicasForRole`, `applyDeallocationForRole`,
  `needsScaleDownForRole`, `variantsForRole`. Mutate per-role `RoleSpare`.
- Helpers never mutate `Result` — only working scratch state. ✅

### Optimizers
- **`CostAwareOptimizer.Optimize`** dispatches on `isDisaggregated`.
  Disaggregated: defensive slice copy + `initDisaggregatedRemaining` →
  `allocateForModelPaired` with `costGreedyPickPaired` (if
  `needsScaleUp(s)`) OR `costAwareScaleDownRoleIterated`. Non-disaggregated:
  in-place on `req.AnalyzerResults`, calls `costAwareScaleUp` /
  `costAwareScaleDown`. Cheapest-variant protection + `minReplicas` floor
  preserved on both scale-down paths.
- **`GreedyByScoreOptimizer.Optimize`** uses
  `fairShareValue(priority, s) = priority × Σᵢ(Remainingᵢ × Scoreᵢ)`,
  fallback to `max_i(Remainingᵢ)` when weighted=0. Builds `scaleUpWork`
  for models that need scale-up; iterative mean-based fair-sharing across
  active models. Dispatch on disaggregation: paired vs single picker.
  Scale-down delegates to CostAware-side helpers (single-variant or
  role-iterated).

### Engine integration
- `runAnalyzersAndScore` (`engine_v2.go`) runs saturation, applies
  threshold post-step, iterates `analyzersSnapshot` (skip saturation),
  calibrates each result via `applyUniversalThreshold`, and appends to
  `[]NamedAnalyzerResult`. Returns `(namedResults, baseResult, error)` —
  middle return unused.
- `collectV2ModelRequest` populates `ModelScalingRequest.AnalyzerResults`
  and `Disaggregated`.
- `engine_queueing_model.go` migrated to the new shape.
- SchedulerQueue threaded through `prepareModelData` →
  `runV2AnalysisOnly` → `AnalyzerInput.SchedulerQueue` (both construction
  sites).
- `interfaces.AnalyzerResult.Score` field DROPPED.

---

## Plan-vs-code matrix

| Plan element | In code? |
|---|---|
| `NamedAnalyzerResult{Name, Result, Score, Remaining, Spare, RoleSpare}` | ✅ all 6 fields |
| Single-variant helpers (8) | ✅ |
| Paired helpers (5) | ✅ |
| Role-iterated helpers (4) | ✅ |
| α from `TotalDemand` (workload invariant), edge-case rules | ✅ |
| `isDisaggregated(VariantCapacity)` dispatch | ✅ |
| CostAware paired scale-up + role-iterated scale-down | ✅ |
| Greedy migration, both paths | ✅ |
| `fairShareValue = priority × Σ(Remaining × Score)` | ✅ formula present |
| `ModelScalingRequest.Result` dropped | ✅ |
| `AnalyzerResult.Score` field dropped from interface | ✅ |
| `runAnalyzersAndScore` → `runAnalyzers` rename (plan §1.6) | ❌ **NOT DONE** |
| SchedulerQueue threaded (engine-queue-fix absorbed) | ✅ |
| `Score` populated from `AnalyzerScoreConfig.Score` (per doc-comment) | ❌ **NOT DONE** — see Bug 1 |

---

## Findings

### B1 — Bug (significant). Engine fails to populate `NamedAnalyzerResult.Score` — silently lost during cross-rebase

This is best framed as a config-population gap, not a scoring-only bug.
The engine is responsible for populating all configuration and general
parameters for analyzers and optimizers (scores, thresholds,
disaggregation flag, GPU capacities, …). Score is the field that
regressed; the same author missed `Disaggregated` too (set on
`ModelScalingRequest` but never read — optimizers re-derive from
`VariantCapacity.Role`; benign duplication, but a tell that the
config-bridging code wasn't being checked).

- **Location:** `internal/engines/saturation/engine_v2.go runAnalyzersAndScore`
  (saturation entry construction + post-saturation analyzer loop) and
  `internal/engines/saturation/engine_queueing_model.go` (mirror path).
- **Problem:** `NamedAnalyzerResult.Score` is documented as
  *"per-analyzer weight from AnalyzerScoreConfig"* but no production
  code path sets it. It is set ONLY by test fixtures (`withSatEntry`
  helpers in `cost_aware_optimizer_test.go` and
  `greedy_score_optimizer_test.go` hardcode `Score: 1.0`). The only
  references to `.Score` in production code today are the **producer**
  (`config/saturation_scaling.go`, defaults `Analyzers[i].Score = 1.0`)
  and the **consumer** (`pipeline/greedy_score_optimizer.go`, reads
  `e.Score`). The bridging code in the engine that's supposed to plumb
  producer to consumer is missing.
- **Effect on `GreedyByScoreOptimizer`:**
  - With all `Score=0`: `weighted = Σ(Remaining × 0) = 0`, so
    `fsv = priority × 0 = 0`. Fallback path returns
    `max_i(Remaining_i)`, which discards `priority`.
  - Net: high-priority models with low remaining lose to low-priority
    models with high remaining. Fair-share priority is broken;
    GreedyByScore degrades to "highest absolute remaining wins."

#### Root cause — cross-rebase loss

Forensics across `backup/multi-analyzer-optimizer-pre-rebase` (`ae456aa0`)
and the current optimizer stack:

1. **Pre-rebase commit 4** (`445a782d`, paired helpers + CostAware
   disaggregated path) is the commit that introduced both
   `NamedAnalyzerResult.Score` AND the engine-side population. Its
   engine_v2.go content built the slice with explicit
   `Score: satScore` (with `satScore = 1.0` default lookup loop over
   `config.Analyzers[]`) on the saturation slot and `Score: aw.Score` on
   each non-saturation entry. Field and fill-in shipped together as one
   unit.
2. **Pre-rebase tip** (`ae456aa0`, the cleanup commit equivalent of
   today's `b4181281`) preserved the wiring intact.
3. **Cross-rebase** (`git rebase --onto b8b823b0`) replayed each commit's
   diff onto the new threshold tip whose `runAnalyzersAndScore` body was
   different. The replay of pre-rebase commit 4's engine_v2.go hunks
   landed as post-rebase commit 4 (`3319db36`) — but its diff for
   engine_v2.go contains only `computeCurrentGPUUsage` updates and a
   return-tuple change. **The `Score: satScore` and `Score: aw.Score`
   write hunks did not survive merge resolution.**
4. **The commit message survived the loss.** `3319db36`'s body still
   says *"Engine populates Score from AnalyzerScoreConfig.Score."*
5. **Cleanup commit `b4181281`** repeats the false claim
   (*"AnalyzerResult.Score removed. Fair-share priority uses
   NamedAnalyzerResult.Score (per-analyzer weight from
   AnalyzerScoreConfig)"*). `interfaces.AnalyzerResult.Score` was
   deleted in this commit; the slice's `Score` was never set; nothing
   in production fills the gap.

The framing **"a rebase removed essential functionality" is correct,
literally**. Git's three-way merge could not apply the Score-write
hunks against the changed `runAnalyzersAndScore` body, the resolution
kept the slice-shape change without the Score-fill change, no marker,
no error. **Commit messages survived; code didn't.**

#### Fix shape

In `runAnalyzersAndScore`, when constructing each `NamedAnalyzerResult`
(saturation slot 0 + per-analyzer loop), look up the analyzer's score
from `config.Analyzers[i].Score` with a 1.0 default when absent (the
config loader already defaults to 1.0 when the field is zero, so a plain
lookup is sufficient if the slot is found). Apply the same fix in
`engine_queueing_model.go`. While there, audit `Disaggregated` —
either remove the unused field or make optimizers consume it.

### B2 — Bug. Paired scale-up commits unmatched replicas when one role's headroom is exhausted

- **Locations:**
  - `internal/engines/pipeline/analyzer_helpers.go allocateForModelPaired`
    inner-loop guard
  - `internal/engines/pipeline/greedy_score_optimizer.go allocateToVariantsPaired`
    inner-loop guard
- **Problem:** loop exit condition is `if nP <= 0 && nD <= 0 { break }`
  (AND, not OR). When `nP > 0` and `nD = 0` (decode side exhausted,
  prefill side still has headroom):
  - `applyAllocationPaired` correctly serves
    `min(nP × prcP, 0/α) = 0` model demand → `Remaining` doesn't move
  - but `targets[vP] += nP` still commits prefill replicas
  - `available[acc] -= nP × gpus` and `consumed += nP × prcP` consumed
  - next iteration may pick differently or stall on the same condition
- **Effect:** optimizer commits prefill-only or decode-only replica counts
  despite paired-allocation semantics. The done-handoff flagged that
  *"GPU exhaustion on one role blocks the paired scale-up for that
  model — cannot allocate P without D or vice versa."* The current code
  doesn't block; it commits wasted replicas.
- **Fix:** change `&&` to `||` in both call sites. Re-check whether
  `applyAllocationPaired` should be called at all when one side is 0.
- **Tests:** likely no current test exercises a one-side-exhausted state.
  Add a unit test that drives `nD = 0` while `nP > 0` and asserts no
  prefill-only commits.

### N1 — NTH (cleanup). `runAnalyzersAndScore` not renamed

- **Location:** `internal/engines/saturation/engine_v2.go`.
- Plan §1.6 and the commit message of `b4181281` (*"cleanup — drop
  Result/Score fields, **rename runAnalyzers**, add comment"*) say the
  function is renamed. The function is still named `runAnalyzersAndScore`
  in the final tree. Since the score-compute loop is gone the name is
  also misleading.
- **Fix:** complete the rename (or update commit-message wording).

### N2 — NTH (cleanup). Dead-code residue

- **`ModelScalingRequest.Disaggregated bool`** — set in
  `collectV2ModelRequest` but never read; both optimizers dispatch via
  `isDisaggregated(satEntry.VariantCapacities)`. Either drop the field or
  wire it into the dispatch (and skip the per-call recompute).
- **`filterVariantCapacitiesByRole`** in `greedy_score_optimizer.go` —
  used only by its own test. Functionally equivalent to `variantsForRole`
  in `analyzer_helpers.go`. Remove duplicate (and its test).
- **`runAnalyzersAndScore` middle return value** —
  `(namedResults, *AnalyzerResult, error)`; caller discards the second
  return. The doc-comment on it referred to a transitional `Result`
  pointer that is now gone. Drop the middle return.

### N3 — NTH (code shape). Asymmetric defensive copy in CostAwareOptimizer

`CostAwareOptimizer.Optimize` makes a defensive copy of
`req.AnalyzerResults` ONLY in the disaggregated branch; non-disaggregated
mutates in place. End behavior is fine since each request is processed
once, but the asymmetry is a footgun if a future refactor adds a second
pass over the same request.

### N4 — NTH (determinism). `costAwareScaleDownRoleIterated` iterates Go map

`for role := range roles` over a `map[string]...` is non-deterministic.
With only 2 roles ({P, D}) and per-role independence at scale-down the
end state is the same, but any test or log relying on order is flaky.
Sort role keys before iterating.

### N5 — NTH (multi-analyzer future). `fairSharePickPaired` α-derivation

`GreedyByScoreOptimizer.fairSharePickPaired` derives α from the **first**
analyzer that tracks D. With multiple analyzers having different α (e.g.
sat_v2 ≈ 0.3, TA = 1.0), only that one analyzer's α drives the picker's
D-side cap, while `bottleneckReplicasPaired` and `applyAllocationPaired`
honor each analyzer's α separately. For the current single-analyzer
(sat_v2) production this is harmless; flag for the multi-analyzer-with-
divergent-α future. Already noted under § Future direction → "vector α"
in `multi-analyzer-design.md`.

### T1 — Test gap (significant). Engine→optimizer config-population responsibility is invisible to the test suite

This is the gap that hid B1 across the rebase. Three independent
shortcomings, each sufficient on its own to mask a regression in
config-population:

1. **Zero engine-level assertions on what `runAnalyzersAndScore`
   writes.** Searched `internal/engines/saturation/*_test.go` for any
   `Score` assertion — none. The engine→optimizer wiring is invisible
   to the test suite. Also true for `Disaggregated`, and weakly true
   for thresholds (the post-step is tested in
   `engine_v2_threshold_test.go`, but per-analyzer override resolution
   into the slice is not asserted).
2. **Test helpers fabricate state the engine never produces.** The
   `withSatEntry` / `withSatEntryV2` helpers in
   `cost_aware_optimizer_test.go` and `greedy_score_optimizer_test.go`
   hardcode `Score: 1.0`. Optimizer tests pass under the hardcoded
   fixture; production runs with `Score = 0`. Helpers should mirror
   what the engine does, not paper over it.
3. **No multi-model fair-share-priority end-to-end test.** A test that
   gave two models different `config.Analyzers[].Score` values and
   asserted Greedy ordering would have failed B1 on day one. None
   exists.

#### Fix shape

- **Engine-level config-population test.** New
  `internal/engines/saturation/engine_v2_population_test.go` (or
  extension of an existing file). Build a `config.Analyzers[]` with
  explicit Score values per analyzer; run `runAnalyzersAndScore`;
  assert each `req.AnalyzerResults[i].Score` matches the corresponding
  `config.Analyzers[match].Score`. Same shape for `Disaggregated`,
  per-analyzer threshold overrides on the produced slice (the
  post-step's RC/SC values), and any other field the engine populates.
- **Strip hardcoded `Score: 1.0` from `withSatEntry` helpers.** Either
  default to `Score: 0` (matches prod default of zero unless wired) or
  take the score as a parameter / derive from a fixture config. The
  helper must not lie about the engine's behavior.
- **Multi-model fair-share-priority integration test.** Two or more
  models with different priorities and different `Analyzers[].Score`
  values; assert Greedy allocates to the higher-priority-weighted
  model first.

This T1 work should land in the same PR as the B1 fix, not a
follow-up. The whole point is "next time silent loss converts to a red
test."

### N6 — NTH (doc). `mergeConstraints` location/comment

`mergeConstraints` lives in `cost_aware_optimizer.go` with a comment
"currently unused in CostAwareOptimizer but available for limited mode".
It IS used by `GreedyByScoreOptimizer.Optimize`. Either move to a shared
file or drop the misleading comment.

---

## Confirmed correct

- α-from-`TotalDemand` rule + all four edge cases.
- Linearity invariant respected: `applyAllocation*` and
  `applyDeallocation*` mutate only working `Remaining`/`Spare`/`RoleSpare`;
  `Result` is never touched.
- Engine post-step (`applyUniversalThreshold`) remains the sole writer of
  RC/SC. Optimizer working state is initialised from those engine-
  calibrated values and decremented in place.
- Scale-down: P/D treated as independent (no pairing) — matches the
  Architecture/D rationale and PR #1237's pattern. Cheapest-variant
  protection scoped per-role.
- SchedulerQueue threading is end-to-end; covers V2 saturation and
  queueing-model paths.
- `engine_queueing_model.go` migrated to the new slice shape (commonly
  forgotten when the primary path changes; this one is correct).
- Cross-rebase resolution coherent: registration plumbing + threshold
  post-step + sat_v2 simplification + aggregation helpers + slice flow
  all coexist sensibly in `runAnalyzersAndScore`.

---

## Recommendation

Two real bugs to address before reviewer-visible PR:

1. **B1** — populate `NamedAnalyzerResult.Score` from
   `config.Analyzers[].Score` in both engine construction sites; without
   this, GreedyByScore's fair-share priority is broken in production.
2. **B2** — paired-scale-up loop guard `&&` → `||` (or equivalent
   one-side-exhausted handling); add a test for `nD=0, nP>0` (and the
   mirror).

The rename (N1), dead-code (N2), and other NTH items are doc-quality
follow-ups. Could be a single small commit on top, or split.

The architecture matches the plan and the design doc. The bugs are in
score-population and one paired-loop guard — small surface area, both
fixable in compact commits.

---

## References

- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) —
  per-PR plan reviewed against.
- [`multi-analyzer-design.md`](multi-analyzer-design.md) — cross-cutting
  design doc.
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) —
  cross-rebase base.
