# Multi-Analyzer Optimizer — Code Review

**Status: DONE — MERGED 2026-06-10**
**Reviewer:** plan-agent (reviewer role), 2026-06-07 (P1/P2), 2026-06-08 (P3/P4)
**Branch reviewed:** `multi-analyzer-optimizer` @ `ad1a8e1e` (17 commits on `main@badc48be` post-#1237).
Phase 1 review covers commits 1–8 (tip `233867bd`). Phase 2 addendum covers commits 9–11 (tip `4bfac2fa`). Phase 3 addendum covers commits 12–15 (tip `680b1fb8`). Phase 4 addendum covers the rebase onto `main@badc48be` + lint-fix (tip `ad1a8e1e`).
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

---

## Phase 2 addendum — commits 9–11 (tip `4bfac2fa`)

**Commits reviewed:**
- `f3184dbb` — B1+T1: populate `NamedAnalyzerResult.Score` from config
- `20d76972` — B2: paired scale-up reshape (per-role sizing + util-min joint commit)
- `4bfac2fa` — N2+N3+N4: Disaggregated flag, drop dead code, sort roles

---

### What the new code does (independent reading)

**B1 (`f3184dbb`):** `scoreForAnalyzer(name, cfg)` added to `engine_v2.go` — walks `cfg.Analyzers` for a matching name, returns `aw.Score` when > 0, else 1.0. Called for the saturation entry and every non-saturation entry in `runAnalyzersAndScore`. `Score` is now populated from config rather than left zero.

**B2 (`20d76972`):** Paired scale-up restructured:
- `RolePairedState = []map[string]float64` — picker-local per-role demand, indexed `[analyzer-index][role]`. Lives only inside the allocation pass (not on `NamedAnalyzerResult`, per design A10).
- `InitRolePairedState(s)` — initialises from `RoleCapacities[role].RequiredCapacity`.
- `roleBottleneckReplicas`, `roleAggRemaining`, `needsScaleUpPaired` — per-role analogues of the single-variant helpers.
- `allocateForModelPairedB2`: per-role independent sizing via `roleBottleneckReplicas`, joint-commit bounded by `min_role util_role`. 0-case: `demand_role = 0 → util_role = 1.0`. Trim formula: `k_role = max(floor(Δ_util × demand / prc), min(1, n_role))`. Both `targets[vP]` and `targets[vD]` committed; `available` decremented for both. `applyAllocation(s, vP, kP)` decrements model-level `Remaining` (P-anchor only, per convention). Old `analyzerAlpha`, `bottleneckReplicasPaired`, `applyAllocationPaired` helpers removed.

**N2+N3+N4 (`4bfac2fa`):**
- Optimizers now consume `req.Disaggregated` directly; `filterVariantCapacitiesByRole` dropped; `variantsForRole` used instead.
- Defensive copy dropped in `CostAwareOptimizer.Optimize` disaggregated branch — symmetric with non-disaggregated.
- `sort.Strings(roles)` added in `costAwareScaleDownRoleIterated` for deterministic role-iteration order.
- `allocateToVariantsPaired` tombstone comment at `greedy_score_optimizer.go:290`.

---

### Findings

#### B2-gate: D-only demand silently ignored — **blocker**

The outer gate in both optimizers still uses model-level `needsScaleUp(s)`, which checks `e.Remaining`. After `initDisaggregatedRemaining`, `Remaining = RoleCapacities["prefill"].RequiredCapacity`. When only decode needs scale-up (P RC = 0, D RC > 0):

```go
// CostAwareOptimizer.Optimize (cost_aware_optimizer.go:59–66)
initDisaggregatedRemaining(s)
if needsScaleUp(s) {           // Remaining = P RC = 0 → false
    allocateForModelPairedB2(...)  // ← never reached
} else {
    costAwareScaleDownRoleIterated(...)  // ← wrong branch; no-op (D has no spare)
}
```

Same failure in Greedy: `scaleUpWork` gate is `needsScaleUp(s) || fsv > 0`. With `Remaining = P RC = 0`, `Σ(Remaining_i × Score_i) = 0` → `fsv = 0`. D-only demand is invisible to both optimizers.

The plan (`optimizer-plan.md` § "Pre-phase-2 failure mode") explicitly identifies this as the failure case B2 must fix. The B2 inner loop (`allocateForModelPairedB2`) handles D-only via `needsScaleUpPaired` + 0-case, but the outer gate was never updated to use it. The described failure mode is still present post-B2.

**Fix:** change the disaggregated gate from `needsScaleUp(s)` to `needsScaleUpPaired(s, InitRolePairedState(s), []string{"prefill","decode"})` in both `CostAwareOptimizer.Optimize` and the Greedy dispatch. Requires one additional `ps := InitRolePairedState(s)` call before the gate in each path.

**Missing test:** no spec covers P RC = 0, D RC > 0 → expects D-side scale-up replicas.

#### B1 on QM path — plan discrepancy, low impact

`engine_queueing_model.go:77` has `Score: 1.0 // QM path: single analyzer, no per-entry score config`. The plan (§ Scope summary B1) includes the QM construction site. Practical impact is low (QM is single-analyzer; Score = 1.0 is the correct default). But `scoreForAnalyzer(interfaces.SaturationAnalyzerName, config)` could be called here instead of hardcoding, for consistency with the V2 path.

#### N4 implemented despite being marked deferred — minor

Plan marks N4 deferred; code at `costAwareScaleDownRoleIterated:412` has `sort.Strings(roles)`. The sort is harmless and a robustness improvement for tests. No action needed — note for the PR description.

#### Doc stub URL points to personal fork — cosmetic

`docs/developer-guide/multi-analyzer-pipeline.md:46` links to `github.com/deanlorenz/...`. In the upstream PR this should be `github.com/llm-d/...` (or the line dropped, since the plans branch doesn't exist upstream). Fix before pushing to origin.

---

### Confirmed correct in Phase 2

- B1 in `engine_v2.go`: `scoreForAnalyzer` called for saturation + every `analyzersSnapshot` entry; default 1.0 when config has no entry or Score ≤ 0. ✅
- B2 inner loop: `targets[vP] += kP` and `targets[vD] += kD` both committed (lines 468–469). ✅
- `applyAllocation(s, vP, kP)` P-anchor is correct: D-side model-level `Remaining` intentionally not decremented (inner loop uses `pickerState`, not `Remaining`). ✅
- `available` decremented for both `vP` and `vD` accelerators inside `allocateForModelPairedB2`. ✅
- N2: `req.Disaggregated` consumed in both optimizers; `isDisaggregated(satEntry.VariantCapacities)` removed. ✅
- N2: `runAnalyzersAndScore` returns 2-tuple; middle return dropped. ✅
- N3: defensive copy dropped; both branches symmetric. ✅
- T1: `greedy_score_optimizer_test.go` "Score-Based Priority" context validates `fairShareValue = priority × Σ(Remaining × Score)` with explicit `Score` values mirroring the B1 engine fix. ✅
- Role-iterated scale-down: correct — uses `RoleSpare` for gate and mutation; `cheapest` scoped per-role. ✅

---

### Phase 2 verdict

One blocker (B2-gate not updated), one plan discrepancy (B1 QM path, low impact), two cosmetics (N4 harmless, doc URL). The B2 gate fix is small — change the gate check in two call sites, add one test spec. Everything else is solid. Not ready for push until the gate is fixed.

---

## Phase 3 addendum — commits 12–15 (tip `680b1fb8`)

**Commits reviewed:**
- `5c18f4c5` — pipeline: initRoleState — unify role-state init
- `2d0ce096` — pipeline: role-generic joint allocator + scale-down; unify dispatch paths
- `0c06dcee` — pipeline: Greedy per-role fair-share + drop α
- `680b1fb8` — pipeline: Phase 3 tests — D-only scale-up, min-util coupling

### What the new code does (independent reading)

Both optimizers now share one dispatch (no `if req.Disaggregated`):
`initRoleState(s) → anyRoleNeedsScaleUp(ps, roles) ? allocateForModelPaired : scaleDownRoleIterated`.

- `initRoleState` (analyzer_helpers:222) returns `(roles, pickerState)`. Disaggregated:
  roles + per-role RC/SC from `RoleCapacities`. Non-disaggregated: one synthetic `"both"`
  role from the model-level `Remaining`/`Spare` scalars (no re-aggregation). Populates
  `RoleSpare` for scale-down; `pickerState` for scale-up.
- `allocateForModelPaired` (analyzer_helpers:449) is role-generic: per-iteration it picks one
  variant per role via a `RolePickFn`, sizes each independently (`roleBottleneckReplicas`),
  computes `Δ_util = min_role util_role`, trims, and joint-commits. Arity-1 (`["both"]`)
  reduces to plain allocation.
- CostAware picker `costGreedyRolePick` (cost_aware:81) and Greedy picker `fairShareRolePick`
  (greedy:284) are role-scoped; α is gone — the joint Δ_util commit is the coupling.
- `fairShareValue` (greedy:49) sums picker-local role-remaining across roles.

### Confirmed correct

- **Unified dispatch in both optimizers** (cost_aware:59–66, greedy:108–118 + 145–148). ✅
- **D-only gate bug is dead.** `anyRoleNeedsScaleUp` checks every role's picker-state, so
  `RC_P=0, RC_D>0` enters scale-up. Tested: `cost_aware_optimizer_test.go:590` and
  `greedy_score_optimizer_test.go:1108`. ✅
- **`initRoleState` non-disag synthesis** aliases model-level RC/SC as the `"both"` role; no
  re-aggregation. ✅
- **α removed** from the Greedy picker; min-util commit is the coupling. ✅
- **Arity-1 reduction** sound (`min` over one role = identity). ✅
- **P-anchor model-level `Remaining` update** (analyzer_helpers:535–543) keeps Greedy non-disag
  `fairShareValue` convergent. ✅

### Finding P3.1 — dead code: the DELETE step was skipped (blocks push)

The Phase 3 plan's deletion discipline is **wrap → verify → inline → delete**. Wrap + verify +
inline are done (new code wired, tests green) but the **delete step was not** — the old
implementations remain alongside the new ones. Orphaned (0 production callers, verified by
ref-count):

- `allocateForModelPairedB2` + now-exclusive deps `needsScaleUpPaired`, `PickPairFn`
- `costGreedyPickPaired`, `fairSharePickPaired`, `costGreedyPick`, `fairSharePick`
- `costAwareScaleUp`, `costAwareScaleDown`
- free `allocateForModel` (analyzer_helpers:145 — the Greedy *method* of the same name shadows
  it in grep) + its now-dead deps `needsScaleUp`, `bottleneckReplicas`, `needsScaleDown`,
  `safeRemovalReplicas`
- `isDisaggregated`, `InitRolePairedState`

Not a correctness bug — behaviour is intact (wrap-before-delete did its job: no silent loss).
But it is **incomplete against the plan** and ships a confusing diff: two scale-up
implementations (`allocateForModelPaired` + `allocateForModelPairedB2`), two pickers per
optimizer, dead scale-down — ev-shindin will not know which is live, and a future caller could
wire the dead `allocateForModelPairedB2`. Several orphans are still referenced only by
tests-of-dead-code (`allocateForModelPairedB2`, `costAwareScaleDown`, `isDisaggregated`,
`needsScaleUpPaired`, `needsScaleUp`, `needsScaleDown`, `bottleneckReplicas`,
`safeRemovalReplicas`, `InitRolePairedState`), so the delete must migrate/remove those specs too.

**Fix:** complete step 4 — delete the orphaned functions and their dead tests, `make test` green.
Apply the same wrap→verify→inline→delete care in reverse: delete one function, run tests,
proceed. Do not bulk-delete.

### Finding P3.2 — passthrough wrappers (collapse / delete)

- `scaleDownRoleIterated` (cost_aware:110–118) is a pure single-call passthrough to
  `costAwareScaleDownRoleIterated`. Collapse: rename `costAwareScaleDownRoleIterated` →
  `scaleDownRoleIterated`, drop the wrapper.
- `InitRolePairedState` (analyzer_helpers:279–282) is a delegation wrapper over `initRoleState`
  with 0 callers — delete (part of P3.1).

### Finding P3.3 — stale comments (doc)

- Greedy tombstone (greedy:278–279): "Greedy's disaggregated scale-up now delegates to
  **allocateForModelPairedB2**" — it delegates to `allocateForModelPaired` now.
- The "B2 paired scale-up helpers" header (analyzer_helpers:260) and the `RolePairedState` doc
  ("α … only in picker sizing") are stale after α removal.

### Phase 3 verdict

The unification logic, the D-only fix, and the new tests are correct — the substance is right
and behaviour is preserved. The gap is the **cleanup half**: the deletion step (P3.1), one
passthrough collapse (P3.2), and stale comments (P3.3). **Not push-ready** until those land as a
5th Phase 3 commit (delete orphaned functions + their dead tests, collapse the scale-down
wrapper, fix the comments, `make test` green). This is incomplete scope, not a correctness
blocker — distinct from the Phase 2 verdict, which was a real bug.

---

## Phase 4 addendum (2026-06-08): rebase onto `main@badc48be` (post-#1237) + lint-fix

**Scope.** Reviewer pass over the rebase the optimizer coder performed after PR #1237
(*role-aware scale-down for disaggregated models*) merged into `upstream/main` as `badc48be`.
Optimizer was rebased `git rebase --onto upstream/main d9e4ae1f`; conflicts resolved toward
the target end-state in [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md)
§ "CURRENT NEXT ACTION" Step 2; one lint-fix commit (`ad1a8e1e`) on top to clear the 5
golangci-lint findings (3 from #1246 CI + 2 surfaced by `make lint` locally). New tip
`ad1a8e1e`, 17 commits = 16 rebased + 1 lint. Origin still at pre-rebase `ee8bd815`.

### P3.1/P3.2/P3.3 gap from Phase 3 — closed

Phase 3 verdict said "not push-ready until a 5th cleanup commit lands". That commit is now in
the stack as `2711bdc1` (`pipeline: Phase 3 cleanup — delete orphaned functions, collapse
passthrough`). Verified via grep-to-zero in production code:
`findCheapestVariant`, `sortByCostDesc`, `costAwareScaleDownRoleIterated`,
`filterVariantCapacitiesByRole`, standalone `applyDeallocation`, `allocateForModelPairedB2`,
`needsScaleUp`, `needsScaleDown`, `bottleneckReplicas`, `safeRemovalReplicas`,
`isDisaggregated`, `InitRolePairedState`, `needsScaleUpPaired`, `PickPairFn`, `PickVariantFn` —
0 production references. The one tombstone match is a comment in
`greedy_score_optimizer_test.go` explaining the removal. The scale-down passthrough wrapper
is collapsed (`scaleDownRoleIterated` is now the implementation, not a wrapper). Stale Greedy
tombstone comment + the "B2" header are gone. ✅

### Target end-state from § Step 2 — verified literally

| Plan target | In code | Verdict |
|---|---|---|
| `scaleDownVariantSet` (generalized #1237 primitive with `maxRemovable`/`onRemove` callbacks; PRE-SORTED input; `minReplicas` floor + cheapest-at-1 enforced internally) | [cost_aware_optimizer.go:111–152](../multi-analyzer-optimizer/internal/engines/pipeline/cost_aware_optimizer.go#L111-L152) | ✅ byte-equivalent to spec |
| `sortVariantsForScaleDown` — Cost-desc → score-weighted PRC-asc → name-asc | [cost_aware_optimizer.go:161–184](../multi-analyzer-optimizer/internal/engines/pipeline/cost_aware_optimizer.go#L161-L184) | ✅ byte-equivalent to spec |
| `scaleDownRoleIterated` — thin per-role iterator over `scaleDownVariantSet` (single `if !needsScaleDownForRole(...)` entry gate, no outer loop) | [cost_aware_optimizer.go:307–350](../multi-analyzer-optimizer/internal/engines/pipeline/cost_aware_optimizer.go#L307-L350) | ✅ matches spec; `distinctRolesSorted` inlined per the plan's "extract or inline" allowance |
| `variantsForRole` — single definition in `analyzer_helpers.go`, exact-match body, `Role==""` canonicalised to `interfaces.RoleBoth` | [analyzer_helpers.go:175–187](../multi-analyzer-optimizer/internal/engines/pipeline/analyzer_helpers.go#L175-L187) | ✅ byte-equivalent; no duplicate in `cost_aware_optimizer.go` |
| `anyHasReplicas` (kept from #1237 unchanged) | [cost_aware_optimizer.go:187–194](../multi-analyzer-optimizer/internal/engines/pipeline/cost_aware_optimizer.go#L187-L194) | ✅ |

### Per-file diff inventory `ee8bd815..ad1a8e1e`

```
internal/engines/pipeline/analyzer_helpers.go      |  19 +--
internal/engines/pipeline/analyzer_helpers_test.go |  48 ++--
internal/engines/pipeline/cost_aware_optimizer.go  | 187 ++++++---
internal/engines/pipeline/cost_aware_optimizer_test.go | 171 +++++++++--
```

`greedy_score_optimizer.go` net diff = 0 (a hunk from the rebase reintroduced a trailing
blank, which the lint-fix commit then removed; file is byte-identical pre/post-rebase).
Greedy still delegates scale-down to `scaleDownRoleIterated`; no Greedy-specific behaviour
change. `cost_aware_optimizer_test.go`: +4 disaggregated-scale-down `It(...)` specs (#1237's
tests preserved per plan: *"the test suites — ours + #1237's — both survive the rebase as
the equivalence proof"*); −2 `It(...)` for deleted helpers (`sortByCostDesc`,
`findCheapestVariant`) — correct.

### Lint-fix commit `ad1a8e1e` is mechanical only

Read the diff: `nakedret` → `return roles, pickerState`; `unparam` → inlined `"pf"`/`"dc"`
in `makeNamedPD`; `gocritic captLocal` → `RC`/`SC` → `rc`/`sc` in test helpers; one trailing
blank line in `greedy_score_optimizer.go`; 4 test cases switched from stale `Result:` field
to `withSatEntry` helper; `variantsForRole` "both"/"" test updated for the exact-match
contract. **No behaviour change.** ✅

### Behaviour deltas worth flagging in PR description (not regressions)

1. **Cheapest-variant tie-break is now deterministic.** Before:
   `findCheapestVariant` returned the first input-order variant at min-cost. After: positional
   rule on the sorted slice — among ties at min-cost, the alphabetically-largest name is the
   protected one (because `sortVariantsForScaleDown` puts cheapest last with name-asc
   tie-break). Plan-acknowledged: *"With a single analyzer (Score=1) this reduces to
   Cost-desc then PRC-asc, i.e. #1237's existing tie-break."* Strictly more deterministic;
   no scenario where this is worse.
2. **Outer scale-down loop replaced by single-pass.** Before:
   `for needsScaleDownForRole(...) { ... if !removed { break } }` — could re-iterate. After:
   single `if` entry gate + one pass through `scaleDownVariantSet`. Plan rationale: *"a single
   cost-desc pass with min_i sizing is sufficient: removals only consume spare, so a repeat
   pass removes nothing."* Equivalent terminal state, fewer iterations.

### Phase 1/2 review findings — addressed

- **B1** (Score never populated): commit `9935aded` populates
  `NamedAnalyzerResult.Score` via `scoreForAnalyzer(name, config)` at both V2 and QM
  construction sites; T1.3 adds a multi-model fair-share priority integration test that
  exercises the path. ✅
- **B2** (paired scale-up commits unmatched replicas on one-side exhaustion): commit
  `feac0d30` reshapes paired scale-up (per-role sizing + util-min joint commit); commit
  `afbc0182` makes the joint allocator role-generic; α removed in `48437abb`. ✅

### Gates per coder status file

`make lint` 0 issues (the gate #1246 CI failed on); `gofmt` clean; `go build` clean;
`make test` 136/136; `go test -race ./internal/engines/...` clean; DCO 17/17.

### Phase 4 verdict — push-ready

No silent hunk drops; target end-state matches plan literally; lint-fix is mechanical;
P3 gap closed; B1+B2 addressed in earlier commits in this stack; gates green per coder.

**Force-with-lease push to `origin/multi-analyzer-optimizer` is approved.** PR #1246 will
update automatically. Lease anchor `ee8bd815` (current origin tip). Backup ref
`backup/multi-analyzer-optimizer-pre-rebase` to be kept until merge per plan.

### Small follow-up (not blocking)

The B1 fix removed hardcoded `Score: 1.0` from common test helpers
(`withSatEntry`/`withSatEntryV2`/`makeNamed`/`makeNamedPD`) so existing tests exercise the
production fallback path and a single new T1.3 integration test covers multi-model priority.
Add at least one more multi-model fair-share test with **non-uniform `Score` values across
analyzers** to widen the priority-path coverage. File on the planner's Issues-to-Open queue
post-merge — not a release blocker.
