o# Multi-Analyzer Optimizer — Plan

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
- **Base:** rebased onto `main@d9e4ae1f` (post-#1228); now needs re-rebase onto `main@badc48be` (post-#1237) — see § CURRENT NEXT ACTION below.
- **Tip:** `ee8bd815` (16 commits); PR #1246 OPEN against `main`.
- **Origin:** pushed at `ee8bd815`.
- **Backup ref:** `backup/multi-analyzer-optimizer-pre-rebase` → `ae456aa0`.

---

## CURRENT NEXT ACTION (coder): rebase onto `main@badc48be` (#1237) + adopt #1237's scale-down primitive + fix lint

> Two things landed after PR #1246 opened: (1) CI `lint-and-test` failed on three
> golangci-lint findings (`make lint` is now a required gate), and (2) **PR #1237
> merged** to upstream/main as `badc48be` ("fix(optimizer): role-aware scale-down
> for disaggregated models") — it reworked the *same* `cost_aware_optimizer.go`
> scale-down. This plan section is self-contained; it specifies the exact target
> code. Follow it literally — it is the output of a long design discussion you
> were not part of, so do **not** infer scope beyond what is written here.

**Scope note (boundary).** This is a non-trivial rebase, so CONVENTIONS step 0
("commit messages must reflect the diff") requires a **pre-rebase plan**. Per
that step's role rule: you are the **coder** and have no write access to
`plans/planning/`, so write the pre-rebase plan in your
`plans/session/status/multi-analyzer-optimizer.md` (or a `plan__*.md` handoff)
— **not** under `planning/`. That is the *only* exception-free way to satisfy
step 0 in your scope; it is not a contradiction with CONVENTIONS, it is what
CONVENTIONS step 0 now says for the coder role. All code edits stay inside the
`multi-analyzer-optimizer` worktree.

### Step 1 — Rebase onto the post-#1237 main

```
git fetch upstream
git rebase --onto upstream/main d9e4ae1f multi-analyzer-optimizer   # d9e4ae1f = current base; replays the 16 commits
```

Resolve conflicts so the branch reaches the **target end-state in Step 2** (do
not try to preserve intermediate-commit shapes hunk-by-hunk; resolve toward the
final functions below). The conflict is concentrated in `cost_aware_optimizer.go`
(both #1237 and our Phase-3 rewrote it) with smaller touches in
`greedy_score_optimizer.go` and `cost_aware_optimizer_test.go`.

### Step 2 — Target end-state: reuse #1237's `scaleDownVariantSet` as the shared shedding primitive

**Design decision (do not deviate):** our multi-analyzer role-iterated scale-down
**reuses** #1237's `scaleDownVariantSet` + `anyHasReplicas` as the shedding
skeleton — do **not** drop them, do **not** keep a parallel hand-rolled loop.
#1237's function is *generalized* to inject the sizing/bookkeeping so it works in
the multi-analyzer slice world. Concretely, `cost_aware_optimizer.go` must end up
with these four functions:

**(a) `scaleDownVariantSet` — generalized (keep #1237's name + skeleton; replace the
single `spare float64` with injected `maxRemovable`/`onRemove`; take variants
PRE-SORTED, drop the internal sort):**
```go
// scaleDownVariantSet sheds replicas from sortedVariants (PRE-SORTED cost-desc,
// cheapest last). minReplicas floor and cheapest-at-1 protection are enforced
// here. maxRemovable returns how many replicas of vc the caller permits to remove;
// onRemove is invoked after committing n so the caller can update its spare bookkeeping.
func scaleDownVariantSet(
	ctx context.Context,
	sortedVariants []interfaces.VariantCapacity,
	targets map[string]int,
	states map[string]interfaces.VariantReplicaState,
	maxRemovable func(vc interfaces.VariantCapacity) int,
	onRemove func(vc interfaces.VariantCapacity, n int),
) {
	logger := ctrl.LoggerFrom(ctx)
	for i, vc := range sortedVariants {
		if vc.PerReplicaCapacity <= 0 {
			continue
		}
		current := targets[vc.VariantName]
		minReplicas := 0
		if states != nil {
			if st, ok := states[vc.VariantName]; ok && st.MinReplicas != nil {
				minReplicas = *st.MinReplicas
			}
		}
		removable := current - minReplicas
		if removable <= 0 {
			continue
		}
		n := maxRemovable(vc)
		if n > removable {
			n = removable
		}
		// cheapest-at-1: the last (cheapest) variant is protected at 1 only when no
		// more-expensive variant still holds replicas (#1237's positional rule).
		if i == len(sortedVariants)-1 && current-n < 1 && !anyHasReplicas(sortedVariants[:i], targets) {
			n = current - 1
		}
		if n <= 0 {
			continue
		}
		targets[vc.VariantName] = current - n
		onRemove(vc, n)
		logger.V(logging.DEBUG).Info("scale-down: removed replicas",
			"variant", vc.VariantName, "removed", n, "cost", vc.Cost)
	}
}
```
Keep #1237's `anyHasReplicas` unchanged.

**(b) `sortVariantsForScaleDown` — new helper, the deterministic comparator:**
```go
// sortVariantsForScaleDown orders a role's variants for cost-greedy scale-down:
//   1. Cost descending — shed the most expensive first.
//   2. Tie: score-weighted per-replica capacity ascending — Σ_i Score_i·PRC_i[v].
//   3. Tie: variant name ascending — full determinism.
// With a single analyzer (Score=1) this reduces to Cost-desc then PRC-asc, i.e.
// #1237's existing tie-break.
func sortVariantsForScaleDown(s []NamedAnalyzerResult, roleVCs []interfaces.VariantCapacity) []interfaces.VariantCapacity {
	weighted := func(name string) float64 {
		sum := 0.0
		for _, e := range s {
			if e.Result == nil {
				continue
			}
			sum += e.Score * prcForVariant(e.Result, name)
		}
		return sum
	}
	out := append([]interfaces.VariantCapacity(nil), roleVCs...)
	sort.Slice(out, func(i, j int) bool {
		if out[i].Cost != out[j].Cost {
			return out[i].Cost > out[j].Cost
		}
		wi, wj := weighted(out[i].VariantName), weighted(out[j].VariantName)
		if wi != wj {
			return wi < wj
		}
		return out[i].VariantName < out[j].VariantName
	})
	return out
}
```

**(c) `scaleDownRoleIterated` — rewrite as a thin per-role iterator over (a):**
```go
func scaleDownRoleIterated(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	targets map[string]int,
	stateMap ...map[string]interfaces.VariantReplicaState,
) {
	var states map[string]interfaces.VariantReplicaState
	if len(stateMap) > 0 {
		states = stateMap[0]
	}
	// distinct roles, "" → interfaces.RoleBoth, sorted (keep the existing collection logic)
	roles := distinctRolesSorted(variants)
	for _, role := range roles {
		if !needsScaleDownForRole(s, role) { // all-down ENTRY gate — `if`, not `for`
			continue
		}
		roleVCs := variantsForRole(variants, role)
		if len(roleVCs) == 0 {
			continue
		}
		sorted := sortVariantsForScaleDown(s, roleVCs)
		scaleDownVariantSet(ctx, sorted, targets, states,
			func(vc interfaces.VariantCapacity) int { return safeRemovalReplicasForRole(s, vc.VariantName, role) },
			func(vc interfaces.VariantCapacity, n int) { applyDeallocationForRole(s, vc.VariantName, role, n) },
		)
	}
}
```
Notes that are NOT optional:
- The outer `for needsScaleDownForRole(...)` loop and its `removed` progress
  guard are **gone** — replaced by the single `if` entry gate + one pass through
  `scaleDownVariantSet`. (A single cost-desc pass with `min_i` sizing is
  sufficient: removals only consume spare, so a repeat pass removes nothing.)
- `distinctRolesSorted` is whatever the current code already does to collect roles
  (`""`→`RoleBoth`, `sort.Strings`); keep it (extract to a helper or inline).

**(d) `variantsForRole` — unify on ONE definition in `analyzer_helpers.go`,
using #1237's exact-match body (handles mixed models) and the `interfaces.RoleBoth`
constant:**
```go
// variantsForRole returns the capacities whose role matches role exactly,
// canonicalizing an empty Role to interfaces.RoleBoth.
func variantsForRole(vcs []interfaces.VariantCapacity, role string) []interfaces.VariantCapacity {
	out := make([]interfaces.VariantCapacity, 0, len(vcs))
	for _, vc := range vcs {
		r := vc.Role
		if r == "" {
			r = interfaces.RoleBoth
		}
		if r == role {
			out = append(out, vc)
		}
	}
	return out
}
```
- Replace our current early-return body (`if role=="" || role==RoleBoth { return vcs }`)
  with the exact-match body above. Keep it in `analyzer_helpers.go`. **Drop #1237's
  duplicate `variantsForRole` in `cost_aware_optimizer.go`** (otherwise: redeclared-
  in-package compile error).
- This is behavior-equivalent on supported model shapes (non-disaggregated: all
  variants are `""`/`RoleBoth`, so exact-match on `RoleBoth` returns all — same as
  the early-return) and additionally correct for mixed sets. The test suites
  (ours + #1237's, which both survive the rebase) are the equivalence proof.

**(e) Deletions** — after (a)–(d), these become unused; remove them (golangci-lint
`unused` will fail otherwise):
- `findCheapestVariant` — replaced by `scaleDownVariantSet`'s positional cheapest-at-1.
- our old `sortByCostDesc` — replaced by `sortVariantsForScaleDown`. (Confirm no
  other caller first; scale-**up** uses `sortByCostEfficiencyAsc`, a different func.)
- Run the § Phase 3 grep-to-zero **plus** `findCheapestVariant` and `sortByCostDesc`
  after this step; must be empty.

`greedy_score_optimizer.go`: its scale-down already delegates to
`scaleDownRoleIterated`, so no separate change beyond reconciling #1237's ~8-line
touch during the rebase. `cost_aware_optimizer_test.go`: drop #1237's tests that
exercised the old single-`AnalyzerResult` `scaleDownVariantSet(spare)` signature
(that signature no longer exists); keep/extend our role-iterated scale-down specs.

### Step 3 — Fix the three lint findings (from #1246 CI)

- `analyzer_helpers.go` `initRoleState` — **nakedret**: replace the bare `return`
  with explicit `return roles, pickerState`.
- `analyzer_helpers_test.go` `makeNamedPD` — **unparam**: `vPName` always receives
  `"pf"`; drop the parameter and inline the constant.
- `analyzer_helpers_test.go` — **gocritic captLocal**: rename local `RC` → `rc`.

### Step 4 — Verify (full gate set, in order)

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
- **`make lint` — clean** (the gate #1246 failed; do NOT skip).
- `go build ./...` — clean.
- `make test` — pass; `go test -race ./internal/engines/...` — clean.
- **Grep-to-zero** — § Phase 3 list **+ `findCheapestVariant` + `sortByCostDesc`** — empty.
- **Behaviour backstops:** D-only scale-up gate (`anyRoleNeedsScaleUp`),
  role-generic `allocateForModelPaired`, α removed, `AnalyzerResult.Score` gone,
  SchedulerQueue threaded. Disaggregated **scale-down** still role-iterated and
  cheapest-protected (the #1237 behaviour, now via the shared primitive) — confirm
  via the disaggregated scale-down specs.
- **Per-file diff inventory:** for each touched file,
  `git diff ee8bd815 <post-rebase-tip> -- <file>`, and confirm no optimizer
  behaviour was lost in the rebase (silent-hunk-drop guard).
- DCO sign-off on all rebased commits.

### Step 5 — Hand off

Report: new tip, per-file diff inventory, `make lint` output (clean), grep-to-zero
(empty), and confirmation the disaggregated scale-down specs pass. Do **not**
push — PR #1246 is OPEN; Dean force-with-lease pushes after review. Keep
`backup/...@ae456aa0` until merge.

> The older "Post-#1237 merge: rebase plan" section below predates this discussion
> and is **superseded** — follow this section.

---

## Rebase onto main (post-#1228 merge) — CURRENT NEXT ACTION (coder)

> PR #1228 (threshold) merged into upstream/main on 2026-06-08 as `d9e4ae1f`.
> `origin/main` is fast-forwarded to it. The optimizer's base `b8b823b0` was the
> *old* threshold tip; the threshold work is now on main in its merged form, so
> the optimizer must rebase onto main and the PR targets `main`.

This is a single, self-contained pass — do it once, verify, hand off. Do not
improvise scope beyond what's here.

**0. Pre-rebase plan (CONVENTIONS step 0).** Before touching anything, write
`planning/multi-analyzer-optimizer-rebase-main.md` (ephemeral; delete after the
rebase verifies): the 16-commit list with a one-line "behaviour to preserve" per
commit (mined from each commit message), the files expected to conflict (below),
and the post-rebase verification checklist (below). This is mandatory because
threshold-owned files moved between `b8b823b0` and `d9e4ae1f`.

**1. Confirm starting state.**
```
git -C ../Main rev-parse main          # must be d9e4ae1f
git rev-parse HEAD                       # must be 1648f3f6
git rev-parse 0ecb6038^                  # must be b8b823b0 (the rebase base)
```

**2. Rebase — replay exactly the 16 optimizer commits onto main:**
```
git rebase --onto main b8b823b0 multi-analyzer-optimizer
```
This drops the old threshold base (now on main in merged form) and replays only
the 16 `pipeline:`/`engines:` optimizer commits.

**3. Expected conflicts** (the merged threshold rewrote these; keep main's
threshold version, re-apply the optimizer delta on top):
- `internal/engines/saturation/engine_v2.go` — main has the merged
  `applyUniversalThreshold` / `resolveThresholds` / `runRegisteredAnalyzers`;
  the optimizer adds the `[]NamedAnalyzerResult` slice collection, `scoreForAnalyzer`,
  SchedulerQueue threading, and the renamed `runAnalyzers`. Keep main's threshold
  bodies; layer the optimizer's slice/score/queue changes on top.
- `internal/engines/analyzers/saturation_v2/analyzer.go` — main has the merged
  aggregation-helper version; the optimizer did not need to change it beyond what
  threshold already did. Prefer main's version; re-apply only genuine optimizer hunks.
- `internal/interfaces/analyzer.go` — main (threshold) added `TotalAnticipatedSupply`
  etc.; the optimizer's cleanup commit dropped `AnalyzerResult.Score`. Resolution:
  keep main's threshold additions AND drop `AnalyzerResult.Score` (the optimizer's
  intent). Verify the field is gone post-rebase.
- `internal/engines/saturation/engine.go`, `engine_register_test.go`,
  `engine_queueing_model.go` — minor; reconcile by keeping main's shape + optimizer's
  slice/Score/queue wiring.

**4. Per-commit + per-file checks (CONVENTIONS "commit messages must reflect the
diff").** After the rebase: for each touched file run
`git diff <pre-rebase-tip 1648f3f6> <post-rebase-tip> -- <file>` and confirm every
behaviour each commit's message claims is still present. Cross-rebase three-way
merge silently drops hunks that no longer apply — this check is mandatory, not
optional.

**5. Grep-to-zero (deletions must survive the rebase).** Re-run the § Phase 3
grep-to-zero; must be empty. A rebase can resurrect a deleted symbol via a
conflict mis-resolution.

**6. Behaviour backstops — confirm these still hold post-rebase:**
- D-only scale-up gate (`anyRoleNeedsScaleUp`) — the D-only test passes.
- One role-generic `allocateForModelPaired` + `scaleDownRoleIterated`; no
  `allocateForModelPairedB2`, no `isDisaggregated` dispatch.
- α removed from the Greedy picker.
- `AnalyzerResult.Score` field gone; `NamedAnalyzerResult.Score` populated by
  `scoreForAnalyzer`.
- SchedulerQueue threaded to `AnalyzerInput` for every analyzer.

**7. Gates:** `gofmt -l` empty, `go build ./...` clean, `make test` pass,
`go test -race ./internal/engines/...` clean, DCO sign-off on all 16 rebased commits.

**8. Hand off.** Report new tip + the per-file diff inventory + grep-to-zero output.
Do NOT push (Dean force-with-lease pushes after review — this rebase rewrites the
16 commits, so origin will need `--force-with-lease`). Delete the pre-rebase plan
doc once verified. The `backup/multi-analyzer-optimizer-pre-rebase@ae456aa0` ref
stays until the PR opens.

After this rebase the optimizer PR targets **`main`** (single-purpose diff: the
16 optimizer commits only).

> Separate concern: PR #1237 (`fix/role-aware-scaledown`) — if/when it merges, the
> `variantsForRole` collision + scale-down consolidation in § "Post-#1237 merge:
> rebase plan" still apply. Not part of this #1228 rebase.

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
- **N4 — deferred.** Original recommendation: sort role keys in
  `costAwareScaleDownRoleIterated` for deterministic iteration. PR
  #1237's review (see § "Post-#1237 merge: rebase plan" below) makes
  the case that per-role iteration is order-independent because each
  role's shed touches a disjoint variant set. We agree; sorting adds
  nothing today. May revisit if a future test observes iteration
  order.
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
| ~~**N4**~~ — Deferred (per-role iteration is order-independent; PR #1237 alignment). | — |

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

### Pre-phase-2 failure mode being fixed (asymmetric P/D demand)

The current paired-scale-up code (commits 1–7) has a **silent bug** under
asymmetric demand changes that B2's picker reshape eliminates. Concrete
failure case:

- Workload state: model has positive D-side demand (`RoleCapacities[D].RC > 0`),
  P-side fully provisioned (`RoleCapacities[P].RC = 0`).
- Optimizer dispatch (pre-phase-2):
  ```go
  initDisaggregatedRemaining(s)              // sets Remaining = RoleCapacities[P].RC = 0
  if needsScaleUp(s) {                       // returns ∃ e: e.Remaining > 0 → false
      allocateForModelPaired(...)
  } else {
      costAwareScaleDownRoleIterated(...)    // ← incorrect branch taken
  }
  ```
- Result: optimizer routes to scale-down even though D needs more capacity.
  `RoleSpare[P]` may also be 0 → scale-down does nothing → D under-provisioning
  persists across cycles.

The reverse case (P needs scale-up, D fine) **happens to work** because P-anchor
makes `Remaining = RC_P > 0`, triggering the paired branch, and `analyzerAlpha`
returns α=0 (`!tracksD`) so `applyAllocationPaired` falls through to a
P-only commit. But the asymmetry is fragile and depends on edge-case branches
in `analyzerAlpha`.

**Phase-2 fix.** `RolePairedState` (per-(analyzer, role) demand) plus
`needsScaleUpPaired(s, state, roles) = ∃ role: roleAggRemaining > 0` removes
the P-anchor entirely. Both directions of asymmetric demand trigger correctly:

| Pre-state | Pre-phase-2 | Phase-2 |
|---|---|---|
| RC_P > 0, RC_D > 0 | Paired scale-up (correct) | Per-role independent + min-util commit (correct) |
| RC_P > 0, RC_D = 0 | Paired scale-up, α=0 P-only commit (works by edge case) | Same outcome via per-role; D drops from min |
| RC_P = 0, RC_D > 0 | **Routes to scale-down (wrong)** | Per-role; P drops from min, D scales up |
| RC_P = 0, RC_D = 0 | Scale-down (correct) | Same |

The bug is only present under asymmetric demand changes that drive D-only need
between cycles (e.g., decode load grows while prefill steady). Most workloads
keep α stable enough that pre-phase-2 code happened to work; the bug surfaces
at workload transitions and persists silently if the asymmetry is sustained.

### Scale-down asymmetry (PR #1237 alignment)

The dual concern — **scale-down** asymmetry where one role has spare and the
other is saturated — is what PR #1237 fixes for the legacy single-analyzer
path. Our `costAwareScaleDownRoleIterated` (commit 4) implements the same
role-iterated independent shed for the multi-analyzer slice. Both:

- Iterate roles independently (PR #1237: over `result.RoleCapacities`; ours:
  over `roles []string` against `RoleSpare`).
- Skip roles with no spare.
- Per-role cheapest-at-1 protection, preventing whole-role zeroing.

So the asymmetric-shed bug ev-shindin documented in #1237 is already absent
from our optimizer branch's disag path. The branches converge on the same
algorithm; rebase merges them cleanly with one helper de-duplication (see §
"Post-#1237 merge: rebase plan" below).

### Post-#1237 merge: rebase plan

PR [#1237](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1237)
("fix(optimizer): role-aware scale-down for disaggregated models") targets
`main`. When it merges, our optimizer branch rebases onto a new `main` whose
`cost_aware_optimizer.go` has been refactored. **Coder must handle this on
rebase**, not as a pre-emptive change. Concrete points to expect:

1. **`variantsForRole` helper collision.** PR #1237 adds
   `variantsForRole(capacities, role)` to `cost_aware_optimizer.go` with
   exact-match semantics. Our `analyzer_helpers.go` already defines
   `variantsForRole(vcs, role)` with identical exact-match semantics.
   Three-way merge surfaces the function in both places. **Resolution:**
   keep ours in `analyzer_helpers.go` (more general home); drop the copy
   PR #1237 introduces during rebase resolution; verify call sites in the
   rebased `costAwareScaleDown` import from `analyzer_helpers`.

2. **`costAwareScaleDown` two-branch refactor.** PR #1237 splits
   `costAwareScaleDown` into a disag branch (per-role iteration) and a
   non-disag branch, both calling new `scaleDownVariantSet`. Our branch
   keeps `costAwareScaleDown` as the non-disag path and adds a separate
   `costAwareScaleDownRoleIterated` for multi-analyzer disag. **Possible
   simplification on rebase:** retire `costAwareScaleDownRoleIterated`;
   extend PR #1237's `scaleDownVariantSet` to accept a multi-analyzer
   slice and use `safeRemovalReplicasForRole`'s `min_i` math for
   cross-analyzer aggregation. Outcome: one unified scale-down code path,
   role-iterated, multi-analyzer-aware. Decision deferred to coder
   judgment on rebase — consolidate if cheap, leave separate if it would
   require restructuring more than the rebase warrants.

3. **`Result` field on `ModelScalingRequest` in #1237 tests.** PR #1237's
   new test fixtures use `Result: &interfaces.AnalyzerResult{...}` on
   `ModelScalingRequest`. Our cleanup commit (`b4181281`) dropped the
   `Result` field. Post-rebase, those test fixtures must migrate to the
   slice shape: `AnalyzerResults: []NamedAnalyzerResult{{Name:
   SaturationAnalyzerName, Result: &interfaces.AnalyzerResult{...},
   Remaining: ..., Spare: ..., RoleSpare: ...}}`. Mechanical rewrite, but
   the kind that's easy to miss; this is exactly what the new CONVENTIONS
   "Commit messages must reflect the diff" rule is for. Verify on rebase.

4. **N4 sort role keys — deferred.** The original review (N4) flagged
   non-deterministic Go map iteration in `costAwareScaleDownRoleIterated`
   and recommended sorting role keys. PR #1237 explicitly defends the
   non-deterministic iteration: *"Each role owns a disjoint set of
   variants and sheds against its own spare, so the map's iteration order
   does not affect the outcome."* The reasoning is correct — the per-role
   sheds are fully independent, no cross-iteration state. **Drop N4 from
   phase-2 scope.** May resurface if a future test observes iteration
   order; revisit then.

The phase-2 commits land on the optimizer branch first; #1237 rebase
happens afterward. Coder uses the procedure in `CONVENTIONS.md` (Commit
messages must reflect the diff — pre-rebase plan + post-rebase per-file
diff inventory + per-commit message-vs-diff check).

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

## Phase 3: Unify disaggregated / non-disaggregated paths

> **Status: PLANNED.** Collapses the two parallel optimizer code paths —
> disaggregated and non-disaggregated — into one `(model, role)` path. This
> also fixes a correctness bug in the current split: when only decode needs
> scale-up (prefill RC = 0, decode RC > 0), the model-level scale-up gate reads
> the prefill-anchored `Remaining = 0` and routes the model to scale-down
> instead of allocating decode capacity. The unification removes the
> P-anchored scalar entirely, so the gate is per-role and the bug cannot occur.
> Lands as additional commits on `multi-analyzer-optimizer` before the PR opens.

### Principle

Every model decomposes into `(model, role)` units. Non-disaggregated = a
single role `"both"`. Disaggregated = `{prefill, decode}`. One scale-up path,
one scale-down path, no `if req.Disaggregated` at dispatch. Arity-1 (`{both}`)
is the degenerate case of the general role-keyed logic:

- joint scale-up with one role → `min` over one role = identity → plain allocation;
- role-iterated scale-down with one role → plain scale-down.

This is design [`multi-analyzer-design.md`](multi-analyzer-design.md)
§ Architecture/D realised in code, and the arity-1 reduction of § F11.

### Ownership — do NOT move summation

- **Analyzer owns aggregation.** `saturation_v2/analyzer.go` sums per-variant
  `Total*` into model-level (`aggregation.SumTotal*`) and per-role
  (`aggregation.AggregateByRole`) totals. RC/SC left zero.
- **Engine owns threshold.** `applyUniversalThreshold` reads the analyzer's
  `Total*` at model scope and each `RoleCapacities[role]` scope and writes
  RC/SC. Nothing else aggregates.
- The optimizer **consumes** analyzer sums + engine thresholds. It must **not**
  re-sum. The non-disaggregated single-role view (below) is an alias of the
  model-level value, not a re-aggregation.

### RC/SC scope

RC/SC are per-scope, not per-variant. `VariantCapacity` carries
`PerReplicaCapacity`, `TotalCapacity`, `TotalDemand`, `Utilization` (+ identity).
RC/SC live on `RoleCapacities[role]` (disaggregated) and model-level
`AnalyzerResult` (non-disaggregated). The model-level RC/SC for a **disaggregated**
model is the legacy/meaningless additive-over-non-fungible-roles value (design
F5) — not read by the unified optimizer.

### `initRoleState` — unified role-state init

One function replacing `initDisaggregatedRemaining` + `InitRolePairedState`. For
each model's analyzer slice:

- **Disaggregated** (`RoleCapacities != nil`): roles = keys of `RoleCapacities`;
  per-role RC → picker-local role-remaining; per-role SC → `s[i].RoleSpare[role]`.
- **Non-disaggregated** (`RoleCapacities == nil`): synthesize a single `"both"`
  role from the model-level scalars — RC from `Result.RequiredCapacity`, SC from
  `Result.SpareCapacity`. The engine's model-level value *is* the single-role
  aggregate here (the analyzer summed all variants; `RoleCapacities` is nil
  precisely because there's one role). No re-summation.

Returns `roles []string` + the picker-local `RolePairedState` (per-(analyzer,
role) remaining RC). Per-role SC populated on the existing `RoleSpare` field.

### `Remaining` / `Spare` scalars — kept, read-only

The model-level `Remaining`/`Spare` fields on `NamedAnalyzerResult` stay as the
engine's read-only output. `initRoleState` reads them once to synthesize the
`"both"` role for non-disaggregated models. The optimizer no longer mutates
them for dynamic bookkeeping — all mutation moves to `RoleSpare` (scale-down)
and picker-local `RolePairedState` (scale-up). **No engine change, no struct
change** — the work is contained in the optimizer. (Making per-role canonical
end-to-end and dropping these scalars is a future change — see
[`multi-analyzer-design.md`](multi-analyzer-design.md) § Future direction F12.)

### Dispatch (both optimizers, identical)

```
roles, pickerState := initRoleState(s)
if anyRoleNeedsScaleUp(pickerState, roles):
    allocateForModelPaired(...)        // joint over roles; arity-1 = plain
else:
    scaleDownRoleIterated(..., roles)  // per-role independent; arity-1 = plain
```

No `if req.Disaggregated`. `req.Disaggregated` (wired in N2) becomes
informational — kept on the request for logging/metrics; the optimizer derives
roles from `RoleCapacities`/synthesis, not the flag.

### Scale-up — one role-generic joint allocator

- `allocateForModelPairedB2` → renamed `allocateForModelPaired` (drop the
  ticket-label suffix).
- Inner loop generalised from hardcoded `"prefill"`/`"decode"` to a loop over
  `roles`: per-role independent sizing (`roleBottleneckReplicas`), `util_role`
  per role, `Δ_util = min_role util_role`, trim each role to the joint bound,
  commit `(k_role)` per role. Arity-1: `min` over one role = identity → plain
  per-role allocation.
- 0-cases unchanged: `demand_role = 0 → util_role = 1` (drops from min);
  `demand_role > 0, capacity = 0 → util_role = 0` (joint bound 0 until allocated).

### Scale-down — one role-iterated path

- `costAwareScaleDownRoleIterated` → `scaleDownRoleIterated`, the single
  scale-down path. Its arity-1 (`roles = ["both"]`) case **is** the old
  non-disaggregated `costAwareScaleDown`. Delete `costAwareScaleDown`.
- Per-role: cheapest-cost-desc shed, per-role cheapest-at-1 protection,
  `minReplicas` floor, `safeRemovalReplicasForRole` (cross-analyzer `min_i`),
  `applyDeallocationForRole`. Unchanged from Phase 2 except it now also serves
  the `"both"` single-role case.

### Pickers — role-generic, optimizer-specific

Picker becomes `pick(role) → (variant, capN)`:

- **CostAware**: cheapest-cost-efficiency variant *in that role*, with
  maxReplicas headroom as cap. Variant **choice** per role is independent
  (role costs are additive — no cross term); the joint min-util commit bounds
  the **count**. Replaces `costGreedyPickPaired` (which hardcoded P/D) and the
  single-variant `costGreedyPick`.
  - **Note — cost-optimality under integer rounding is OUT of scope:** the
    cheapest-`cost/PRC` ranking is not always the cheapest *actual* allocation
    when RC is small relative to PRC (a high-PRC variant overshoots and costs
    more than a cheaper low-PRC one). This is **pre-existing** behaviour of the
    cost optimizer, unchanged by Phase 3. Keep the existing cheapest-efficiency
    picker exactly as-is — do not "improve" it here. (Tracked as a follow-up;
    see § "Cost picker: integer-rounding suboptimality" below.)
- **Greedy**: cheapest with GPU budget + per-role fair-share cap. **α is
  removed** — today's `fairSharePickPaired` scales the decode side by
  `α = D/P` (a pre-B2 workaround); the joint min-util commit is now the
  coupling, so per-role fair-share caps + the min-util trim replace α entirely
  (matches design "α stops appearing in serve-math"). Per-(model, role) fair
  share, bounded by `min(util_role)`.

### `fairShareValue` — sum role-remaining

`fairShareValue(priority, s)` currently reads the model `Remaining` scalar.
Change to sum picker-local role-remaining over roles:
`priority × Σ_i Score_i × Σ_role roleRemaining[i][role]`. Arity-1 (`{both}`) is
identical to today. Computed after `initRoleState` so the role-state is
available.

### Deletions — wrap → verify → inline → delete (do NOT bulk-delete)

Each function being replaced is removed in four steps, with `make test` green
at every step. Do **not** delete a function and rewrite its callers in one
move — that is where behaviour gets silently dropped.

1. **Wrap.** Write the new role-keyed function. Make the old function a thin
   wrapper that calls the new one (for the arity-1 / `"both"` case, the new
   function must reproduce the old behaviour exactly). Old call sites are
   untouched.
2. **Verify.** Run `make test`. All existing specs pass through the wrapper —
   this proves the new function is behaviour-preserving before any caller moves.
3. **Inline.** Update call sites one at a time to call the new function
   directly instead of the wrapper. Run `make test` after each.
4. **Delete.** Once a function has no remaining callers, delete it. Run
   `make test` again to confirm nothing referenced it.

Functions to retire this way:
- `costAwareScaleUp` → folds into the role-generic joint scale-up (arity-1).
- `costAwareScaleDown` → folds into `scaleDownRoleIterated` (arity-1).
- Greedy `allocateToVariants` → folds into the role-generic joint scale-up.
- `costGreedyPickPaired`, `fairSharePickPaired` α logic → role-generic pickers.
- `initDisaggregatedRemaining`, `InitRolePairedState` → merged into `initRoleState`.
- Single-variant helpers (`needsScaleUp`, `needsScaleDown`, `bottleneckReplicas`,
  `safeRemovalReplicas`, `applyAllocation`, `applyDeallocation`): keep as arity-1
  wrappers if still convenient, or delete once unreferenced. Coder's call on the
  cleanest shape — but follow the same four steps for each.

### Tests

- Collapse the parallel non-disaggregated specs onto the arity-1 role path
  (they should pass unchanged through `roles = ["both"]`).
- **Add the missing spec:** `RC_P = 0, RC_D > 0` → decode scales up, prefill
  unchanged. This is the D-only case the old model-level gate silently routed
  to scale-down; the test proves the per-role gate handles it.
- Greedy: a disaggregated fair-share spec that asserts the min-util coupling
  with α removed (P and D advance by matched util, not by a fixed α ratio).

### Commit shape (Phase 3)

Coder may reorganise; the review-ready history should land roughly as:

1. `pipeline: initRoleState — unify role-state init`.
2. `pipeline: role-generic joint scale-up + role-iterated scale-down; delete parallel non-disag paths`.
3. `pipeline: greedy fair-share per-role + min-util coupling; drop α`.
4. `pipeline: tests — D-only scale-up, arity-1 collapse, greedy min-util coupling`.

**Commit 5 — cleanup pass (the delete step; outstanding).** Commits 1–4 landed
the wrap + inline; the **delete step of § Deletions was not done**, so the old
implementations remain orphaned alongside the new ones (both compile; tests
pass; behaviour intact). Land a 5th commit that finishes it:

- **Delete the orphaned functions** (0 production callers): `allocateForModelPairedB2`
  + `needsScaleUpPaired` + `PickPairFn`; `costGreedyPickPaired`, `fairSharePickPaired`,
  `costGreedyPick`, `fairSharePick`; `costAwareScaleUp`, `costAwareScaleDown`; the free
  `allocateForModel` + `needsScaleUp`, `bottleneckReplicas`, `needsScaleDown`,
  `safeRemovalReplicas`; `isDisaggregated`, `InitRolePairedState`. Several are still
  referenced only by tests-of-dead-code — migrate or remove those specs in the same commit.
- **Collapse the passthrough**: rename `costAwareScaleDownRoleIterated` →
  `scaleDownRoleIterated`, drop the one-line wrapper.
- **Fix stale comments**: the greedy tombstone referencing `allocateForModelPairedB2`,
  the "B2 paired scale-up helpers" header, and the `RolePairedState` α comment.
- Delete one function at a time, `make test` green after each (delete is the
  same wrap→verify→inline→**delete** discipline run to its last step — do not bulk-delete).

**Commit 5 follow-up (review of `2a3b5c40` found two leftovers).** The cleanup
landed the bulk correctly; two orphans were missed. Fold these into the cleanup
commit (amend `2a3b5c40`):

- **Delete `applyDeallocation`** (analyzer_helpers.go) — now 0 production callers
  (its only caller was the deleted non-disag `costAwareScaleDown`; role scale-down
  uses `applyDeallocationForRole`). Remove its test block (`analyzer_helpers_test.go`
  `Describe("applyDeallocation", …)`) and trim the `optimizer_interfaces.go` doc-comment
  that still names it ("applyAllocation / applyDeallocation …" → just `applyAllocation`).
- **Reword two stale test descriptions** in `greedy_score_optimizer_test.go` that name the
  deleted `costAwareScaleDown` in their `It(...)` strings (≈ lines 375 and 1028) → refer to
  `scaleDownRoleIterated` / "role-iterated scale-down". String-only; the tests themselves
  stay valid.

**Verification step (run and report — must come back empty).** After the deletes,
the coder runs and pastes the output of:

```
grep -rn 'allocateForModelPairedB2\|needsScaleUpPaired\|PickPairFn\|costGreedyPickPaired\|fairSharePickPaired\|costGreedyPick\|fairSharePick\|costAwareScaleUp\|costAwareScaleDown\|costAwareScaleDownRoleIterated\|isDisaggregated\|InitRolePairedState\|\bneedsScaleUp\b\|\bneedsScaleDown\b\|\bbottleneckReplicas\b\|\bsafeRemovalReplicas\b\|\bapplyDeallocation\b' internal/engines/pipeline/
```

Expected: **no matches** (including in `_test.go`). Any hit is either a missed
deletion or a stale comment/string to fix. This grep-to-zero check is the gate for
"the delete step is complete" — do not report push-ready until it is empty.

### Cost picker: integer-rounding suboptimality (pre-existing — follow-up, NOT Phase 3)

The cost picker sorts by `cost/PerReplicaCapacity` ascending and allocates
`ceil(RC/PRC)` of the most-efficient variant. Under integer rounding this is
not always the cheapest *actual* allocation. Worked example:

- A: cost 10, PRC 10 → efficiency 1.0
- B: cost 4, PRC 3 → efficiency 1.33
- RC = 3

Efficiency-greedy picks A (lower `cost/PRC`), allocates `ceil(3/10) = 1` → cost
**10**. But B alone: `ceil(3/3) = 1` → capacity 3 ≥ RC, cost **4**. B is cheaper
and sufficient; the picker mis-picks because `cost/PRC` measures cost-per-unit
assuming the capacity is fully used, ignoring the overshoot when `RC < PRC`. The
cheapest actual allocation ranks by `ceil(RC/PRC) × cost`, not `cost/PRC`.

This is **pre-existing** (inherited from the legacy cost optimizer; the slice
migration did not change the picker) and **orthogonal** to the unification. In
production PRC is in tokens (large) and RC is large, so the marginal overshoot
is usually small — but at the tail (small residual RC, last replica) it
mis-picks. **Out of scope for Phase 3**; tracked as a follow-up issue (see
CURRENT § Issues to Open). Phase 3 must not silently "improve" the picker —
keep cheapest-efficiency, change only the role-generic plumbing.

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
