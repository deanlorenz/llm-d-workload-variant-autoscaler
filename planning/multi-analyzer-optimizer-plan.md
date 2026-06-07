# Multi-Analyzer Optimizer — Plan

> **Status: ACTIVE** — all commits landed locally; cross-rebased onto
> `multi-analyzer-threshold@b8b823b0` (PR #1228 head). 7 commits; tip
> `3fe287fe`. Awaiting Dean force-with-lease push to
> `origin/multi-analyzer-optimizer` and PR creation. SchedulerQueue wiring
> from `engine-queue-fix` (commit `01ed7d8d`) absorbed during the
> cross-rebase — `engine-queue-fix` is no longer needed as a separate PR.
>
> **Cross-cutting design context:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
> (mission, architecture including paired allocation + role-iterated scale-down,
> alternatives including compound-variant rejection, future direction). This
> plan is per-PR implementation only.

---

## Scope

Item 1 of the design split (see `multi-analyzer-design.md` § Tasks): **delete
the engine-side combine; per-analyzer slice flows to the optimizers**. Both
optimizers (`CostAwareOptimizer`, `GreedyByScoreOptimizer`) consume the slice
via shared free functions in `pipeline/analyzer_helpers.go`. Disaggregated
models use paired (P, D) scale-up + role-iterated scale-down (no pairing on
scale-down — roles are independent at scale-down). Plus: SchedulerQueue
wiring (formerly the deferred `engine-queue-fix` branch) absorbed during the
cross-rebase.

For the **architectural decisions** (per-variant canonical model; linearity
invariant; α from `TotalDemand`; paired-allocation math; role-iterated
scale-down rationale; alternatives considered), see
[`multi-analyzer-design.md`](multi-analyzer-design.md) §§ Architecture +
Alternatives considered.

---

## Branch state

- **Branch:** `multi-analyzer-optimizer` in worktree `multi-analyzer-optimizer/`.
- **Base (post-cross-rebase):** `multi-analyzer-threshold`@`b8b823b0` (PR #1228 head).
- **Tip:** `3fe287fe` (7 commits).
- **Backup ref:** `backup/multi-analyzer-optimizer-pre-rebase` → `ae456aa0`
  (pre-rebase tip, in case of need).
- **Origin:** local-only post-rebase. Awaiting force-with-lease push.

---

## Commit stack (on top of `b8b823b0`)

1. **`0ecb6038`** — `pipeline: add NamedAnalyzerResult and AnalyzerResults to ModelScalingRequest`
   - `NamedAnalyzerResult{Name, Result, Score, Remaining, Spare, RoleSpare}`.
   - `ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult`.
   - Engine populates working state from engine-calibrated values; helpers
     mutate working state and never touch `Result`.

2. **`cc53eb6d`** — `pipeline: add per-analyzer slice helpers for scale-up/down decisions`
   - Single-variant helpers in `pipeline/analyzer_helpers.go`:
     `needsScaleUp`, `needsScaleDown`, `bottleneckReplicas`,
     `safeRemovalReplicas`, `applyAllocation`, `applyDeallocation`,
     `saturationEntry`, `PickVariantFn`, `allocateForModel`.
   - Specs in `analyzer_helpers_test.go`.

3. **`6c2312e1`** — `pipeline: migrate CostAwareOptimizer to per-analyzer slice`
   - Non-disaggregated path. Reads `req.AnalyzerResults` via
     `saturationEntry()`; gates via `needsScaleUp`/`needsScaleDown`;
     `costGreedyPick` + `allocateForModel` for scale-up; safe-removal loop
     for scale-down. Greedy scale-down call site updated to the new signature.

4. **`3319db36`** — `pipeline: paired helpers + CostAware disaggregated path (role-iterated scale-down)`
   - `RoleSpare map[string]float64` field on `NamedAnalyzerResult`.
   - `analyzerAlpha(r) → (α, tracksP, tracksD)` — α from
     `RoleCapacities[D].TotalDemand / RoleCapacities[P].TotalDemand`. Edge
     cases handled (P=0 ∧ D>0 sets α=1 and skips P-side; D=0 skips D-side).
   - Paired scale-up helpers: `bottleneckReplicasPaired`,
     `applyAllocationPaired`, `PickPairFn`, `allocateForModelPaired`.
   - Role-iterated scale-down helpers: `safeRemovalReplicasForRole`,
     `applyDeallocationForRole`, `needsScaleDownForRole`, `variantsForRole`.
   - `isDisaggregated([]VariantCapacity) bool`.
   - `CostAwareOptimizer` dispatches on disaggregation.

5. **`5550dc19`** — `pipeline: migrate GreedyByScoreOptimizer to per-analyzer slice (both paths)`
   - `fairShareValue(priority, s) = priority × Σ_i(Remaining_i × Score_i)` —
     replaces the engine-side combined `Score` field.
   - Non-disaggregated: `fairSharePick` (single-variant, fair-share-bounded).
   - Disaggregated: `fairSharePickPaired`. Role-iterated scale-down via the
     role helpers from commit 4.
   - `allocateByRole` (legacy role-budget split) removed.

6. **`b4181281`** — `pipeline: cleanup — drop Result/Score fields, rename runAnalyzers, add comment`
   - Drop `ModelScalingRequest.Result` and `AnalyzerResult.Score`.
   - Rename `runAnalyzersAndScore` → `runAnalyzers`.
   - Drop saturation-only score-compute loop in engine.
   - `buildDecisionsWithOptimizer` reason-strings cleaned to read from the
     slice.
   - Comment on the `removed` flag in `costAwareScaleDown` (see § Code-shape
     notes below).

7. **`3fe287fe`** — `engines/saturation: cross-rebase fixups after threshold rebase`
   - Resolve `engine_v2.go` conflicts: keep threshold's post-step pattern,
     layer 1.1's slice collection on top (collect non-saturation results
     into `[]NamedAnalyzerResult` instead of discarding).
   - Absorb SchedulerQueue wiring from `engine-queue-fix` (commit
     `01ed7d8d`): `modelData.schedulerQueue` field + `CollectSchedulerQueueMetrics`
     call in `prepareModelData`; threaded through `runV2AnalysisOnly` →
     `runAnalyzers` → `collectV2ModelRequest` → `AnalyzerInput.SchedulerQueue`
     (both construction sites).
   - Optimizer name constants (`pipeline.CostAwareOptimizerName` etc.)
     removed; replaced with string literals at call sites in `engine.go` and
     `engine_test.go` (per cross-rebase resolution).

---

## Verified

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass (including new `aggregation`, `throughput`,
  `annotations` packages from the threshold rebase).
- `go test -race ./internal/engines/saturation/...` — clean (~7.7s).
- DCO sign-off on all 7 commits.

---

## Coordination

- **PR #1225 (`multi-analyzer-registration`)** — base for cross-rebase
  (transitively, via threshold). Stable. Awaiting reviewer.
- **PR #1228 (`multi-analyzer-threshold`)** — direct cross-rebase target.
  Awaiting reviewer.
- **PR #1237 (`fix/role-aware-scaledown`)** — independent upstream fix on the
  legacy single-analyzer path. End-result equivalent to our role-iterated
  scale-down for the single-analyzer case. See
  [`multi-analyzer-design.md`](multi-analyzer-design.md) § Alternatives → A
  for the equivalence reasoning.
- **`engine-queue-fix`** — **absorbed.** SchedulerQueue wiring (commit
  `01ed7d8d`) was folded into commit 7 of this stack during the cross-rebase.
  The `engine-queue-fix` branch can be closed; its single commit is now part
  of this PR.
- **PR #1113** — superseded; will be closed.

---

## Semantic changes worth flagging in PR description

- **Greedy GPU exhaustion on one role blocks paired scale-up** for that
  model — cannot allocate P without D or vice versa. This is the correct
  semantics for paired allocation (the `d`-link), but reviewers should know
  it's a behavior change vs. the legacy role-budget split.
- **Greedy `Score` ordering vs. allocation sizing.** `Score` inflates the
  fair-share ordering priority but does not affect replica-count sizing —
  allocation is sized by per-analyzer `Remaining`, not by `Score`. Was true
  before but worth re-confirming under the new shape.
- **`AnalyzerResult.Score` field dropped.** Computed on demand via
  `fairShareValue(priority, s)`. `GreedyByScoreOptimizer` keeps its name for
  historical compatibility but no longer reads a combined `Score` field.

---

## Code-shape notes for reviewer

- **`removed` flag in `costAwareScaleDown` outer loop.** The pattern
  `for needsScaleDown(s) { ... if !removed { break } }` guards against an
  infinite loop where some analyzer's `Spare > 0` but no variant can give
  up replicas (all at `minReplicas` floor, or PRC mismatch makes
  `safeRemovalReplicas` return 0 for every variant). Comment in commit 6
  documents the invariant.

---

## Open items

- **Dev-guide (Type 4 doc) for the optimizer redesign.** Threshold's
  dev-guide already covers the architecture (per-variant canonical;
  responsibility split; engine post-step). The optimizer-side doc could
  add: per-analyzer slice contract, helper API summary, paired allocation
  for P/D, role-iterated scale-down. Either fold into this PR or file as a
  follow-up.
- **Future direction:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
  § Future direction (pre-analysis extraction; vector α; per-analyzer
  observability metrics; engine model-level RC/SC bug for disaggregated;
  enabled-false veto fix; replica-count accounting consistency).

---

## Next steps for Dean

1. `git push --force-with-lease origin multi-analyzer-optimizer` from the
   optimizer worktree (after explicit approval per CONVENTIONS).
2. Open PR. Base options:
   - `main` directly (will show all commits up the chain until #1225 + #1228
     merge — same stacked-PR pattern as #1228).
   - Wait for #1228 to merge, then rebase onto main and open against main —
     cleanest single-purpose PR but blocks.
3. Close `engine-queue-fix` branch/worktree — its content is in commit 7.
4. Decide on dev-guide (this PR or follow-up).

---

## Phase 2: Post-review fixes (in scope on this branch)

Phase 1 (commits 1–7, tip `3fe287fe` + dev-guide stub `233867bd`) is in
review. Findings in
[`multi-analyzer-optimizer-review.md`](multi-analyzer-optimizer-review.md)
(B1, B2, T1, N2, N3, N4) land as additional commits on this branch — no
new PR. Design framing in
[`multi-analyzer-design.md`](multi-analyzer-design.md) § Architecture/D
reshapes B2 from a one-line guard fix into a picker math restructure.
**No `NamedAnalyzerResult` signature changes** (per design § Alternatives
→ A10); per-role demand bookkeeping is picker-local for the duration of
one model's allocation pass.

### Decisions vs. review findings

- **N1 — function rename rejected.** Keep `runAnalyzersAndScore`. The
  function will populate `NamedAnalyzerResult.Score` (B1 fix), making
  the name accurate again.
- **N2 — `ModelScalingRequest.Disaggregated` kept.** Engine populates
  it (already does in `collectV2ModelRequest`); optimizer changes to
  **consume** the flag rather than re-derive via
  `isDisaggregated([]VariantCapacity)`. Aligns with design § H (engine
  is the broker for cross-cutting flags).
- **N2 — `filterVariantCapacitiesByRole` dropped.** Use
  `variantsForRole` from `analyzer_helpers.go` instead. Drop its test.
- **N2 — middle return value of `runAnalyzersAndScore` dropped after
  verification.** All analyzer data must continue to reach the
  optimizer. The middle return today is the saturation `baseResult`,
  which is *also* slot 0 of the slice — provably redundant. Coder
  must verify no caller depends on it independently of the slice
  before dropping; signature becomes 2-tuple.
- **N3 — defensive copy dropped (both branches symmetric).** Engine
  builds a fresh `ModelScalingRequest` per optimize cycle; optimizer
  may mutate freely. The disaggregated-branch defensive copy in
  `CostAwareOptimizer.Optimize` was unnecessary; drop for symmetry
  with non-disag.
- **N4 — sort role keys in `costAwareScaleDownRoleIterated`.**
  Deterministic iteration; no behavior change for arity 2.
- **Dev-guide update deferred** to the post-review polish item already
  tracked in CURRENT § Issues to Open.

### Scope summary (revised)

| Finding | Scope | Files (primary) |
|---|---|---|
| **B1** — Engine populates `NamedAnalyzerResult.Score` from `config.Analyzers[name].Score` (default 1.0 when absent) in `runAnalyzersAndScore` (V2) and the QM construction site. | `internal/engines/saturation/engine_v2.go`, `internal/engines/saturation/engine_queueing_model.go` |
| **B2** — Reshape paired scale-up to per-(model, role) independent sizing + joint commit bounded by `min_role util_role`. Trim over-allocated role; release excess to next iteration. Picker-local per-role bookkeeping (not on slice field). | `internal/engines/pipeline/analyzer_helpers.go`, `internal/engines/pipeline/cost_aware_optimizer.go`, `internal/engines/pipeline/greedy_score_optimizer.go` |
| **T1** — Engine-level config-population assertions; remove hardcoded `Score: 1.0` from `withSatEntry`-style fixtures; multi-model fair-share priority integration test; B2 atomicity tests. | `internal/engines/saturation/*_test.go`, `internal/engines/pipeline/*_test.go` |
| **N2** — Optimizer consumes `req.Disaggregated`; drop `filterVariantCapacitiesByRole` + its test; verify-then-drop middle return of `runAnalyzersAndScore`. | `internal/engines/pipeline/{analyzer_helpers,cost_aware_optimizer,greedy_score_optimizer}.go`, `internal/engines/saturation/{engine_v2,engine}.go` |
| **N3** — Drop disaggregated-branch defensive copy in `CostAwareOptimizer.Optimize`. | `internal/engines/pipeline/cost_aware_optimizer.go` |
| **N4** — Sort role keys in `costAwareScaleDownRoleIterated`. | `internal/engines/pipeline/cost_aware_optimizer.go` |

### B2 picker reshape — implementation guide

Per design § Architecture/D, paired scale-up is no longer "compute
(n_P, n_D) together using α." Each role is an independent (model, role)
mini-model for sizing; a joint-commit step bounds by min util.

**Per-iteration math:**

1. Per role, size independently using the same primitives as non-disag:
   `n_role = max_i ceil(roleRemaining_i^role / PRC_i[v_role])` for the
   picked variant in that role. Cross-analyzer aggregation unchanged.
2. Compute candidate joint commit. For each analyzer:
   `served_i^role = n_role × PRC_i[v_role]`,
   `util_role = served^role / Demand_role` where `Demand_role` is
   per-analyzer `r.RoleCapacities[role].RC` (initial), tracked locally
   minus already-allocated-this-pass.
3. `Δ_util = min_role { util_role }`. Trim the over-allocated role:
   `k_role = floor(Δ_util × Demand_role / PRC_i[v_role])`.
4. Commit `(k_P, k_D)` to `targets`; decrement picker-local
   `roleRemaining_role` and the model-level `Remaining` field
   (P-anchor convention) by matched joint serve in P-units.
5. Loop until `Δ_util = 0` (no role has headroom on this candidate)
   OR every role's `roleRemaining = 0` OR no variant has accelerator
   capacity.

**0-cases (per design § D):**

- `Demand_role = 0` → `util_role = 1` by convention; role drops from
  min. Reduces to single-role allocation when only one role has
  demand.
- `Demand_role > 0, Capacity_role = 0` (cold start) → `util_role = 0`
  → joint commit is 0 until allocation lands in that role. Picker
  must pick a variant of that role to advance.

**Per-role bookkeeping shape:** picker-local
`roleRemaining map[string]float64` per analyzer, mirroring `RoleSpare`'s
shape. Initialized at picker entry from per-analyzer
`r.RoleCapacities[role].RC`. Decremented per joint commit. Lives only
inside the picker function — not stored on `NamedAnalyzerResult` (per
design A10). Future PR can promote to a struct field if it becomes
load-bearing.

**Cross-analyzer aggregation unchanged.** Per-role sizing in step 1 is
already cross-analyzer-aware (`max_i` over analyzers). Adding a role
axis doesn't change how analyzers are aggregated; it adds an outer
`min` over role axis at commit time. (See design § D "Same calculus as
cross-analyzer aggregation.")

**α stops appearing in serve-math.** Today's `analyzerAlpha`,
`bottleneckReplicasPaired`, `applyAllocationPaired`,
`costGreedyPickPaired`, `fairSharePickPaired` retire. Their test specs
migrate to per-role tests of the simpler primitives. If a future
picker wants to size one role from another, α can be derived inline
from `RoleCapacities[*].TotalDemand` at sizing time only, but the new
matched-pair commit doesn't need it.

### Test plan

- **T1.1 — Engine config-population test.** Build `config.Analyzers[]`
  with explicit `Score` per entry; run `runAnalyzersAndScore`; assert
  each `req.AnalyzerResults[i].Score` matches the config entry. Same
  shape for `req.Disaggregated` (engine-populated, optimizer-consumed
  per N2) and per-analyzer threshold overrides on the produced slice.
- **T1.2 — Strip `Score: 1.0` from `withSatEntry` /
  `withSatEntryV2`.** Helpers default to `Score: 0` (matching prod
  default-of-uninit) or take a config-derived value. Tests that
  previously relied on the hardcoded fixture set Score explicitly.
- **T1.3 — Multi-model fair-share priority test.** Two models with
  different priorities and different `Analyzers[].Score`; assert
  Greedy ordering reflects priority. Would have caught B1.
- **B2.1 — Joint-commit atomicity, role-exhausted.** Paired scale-up
  where one role has `Capacity_role = 0` → assert no commitment on
  the over-allocated role; symmetric for `Demand_role = 0` (single-
  role reduction).
- **B2.2 — Util-bottleneck trim.** Paired scale-up where ceil-rounded
  sizing yields higher util on one role; assert over-allocated role
  trimmed; matched serve advances both roles by same Δ_util.

### Verification gates (re-run after each commit)

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- `go test -race ./internal/engines/saturation/... ./internal/engines/pipeline/...` — clean.
- DCO sign-off on every new commit.

### Commit shape (3 commits)

1. **B1 + T1.** Engine populates Score in `runAnalyzersAndScore` (V2)
   and the QM construction site; engine-level config-population test
   added (T1.1); `withSatEntry`-style helpers stripped of hardcoded
   Score (T1.2); multi-model priority integration test added (T1.3).
2. **B2.** Picker reshape (per-role independent sizing + joint-commit
   min-trim, picker-local `roleRemaining`); B2.1 + B2.2 tests added.
   Old paired helpers retired; their existing specs migrate to
   per-role tests of the simpler primitives.
3. **N2 + N3 + N4 cleanup.** Optimizer reads `req.Disaggregated`
   (instead of re-deriving via `isDisaggregated`); drop
   `filterVariantCapacitiesByRole` + test; verify-then-drop middle
   return of `runAnalyzersAndScore`; drop disaggregated-branch
   defensive copy in CostAware; sort role keys in
   `costAwareScaleDownRoleIterated`.

Force-with-lease push only after Dean's explicit confirmation per
CONVENTIONS.

### Coordination

- All work on `multi-analyzer-optimizer` branch. No new PR.
- Branch is local-only post phase 1; phase-2 commits add to the
  existing stack.
- No interaction with #1225 / #1228 (upstream; will rebase onto when
  they merge).

---

## References

- [`multi-analyzer-design.md`](multi-analyzer-design.md) — cross-cutting design
  doc.
- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md)
  — Item 3 (PR #1225) sibling plan.
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) —
  Item 2 (PR #1228) sibling plan and direct cross-rebase target.
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder
  agent rules.
- [`PR1113-review.md`](PR1113-review.md) — historical review of original
  PR #1113 that decided the 3-PR split.
