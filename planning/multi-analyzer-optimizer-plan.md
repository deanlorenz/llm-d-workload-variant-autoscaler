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
