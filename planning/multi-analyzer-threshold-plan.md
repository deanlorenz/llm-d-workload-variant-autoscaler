# Multi-Analyzer Threshold — Plan

> **Status: ACTIVE** — PR [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228)
> open, ev-shindin assigned. 4 commits on `multi-analyzer-registration`@`66001d47`;
> tip `b8b823b0`. Awaiting CI + reviewer feedback.
>
> **Cross-cutting design context:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
> (mission, architecture, alternatives considered including the rejected combine
> algorithm, future direction). This plan is per-PR implementation only.

---

## Scope

Item 2 of the design split (see `multi-analyzer-design.md` § Tasks): **engine
post-step universally calibrates RC/SC for every analyzer's result, plus shared
aggregation helpers for analyzer authors**. Concretely:

- New engine post-step `applyUniversalThreshold` applies the pure formula
  `RC = max(0, TD/scaleUp − Anticipated)` / `SC = max(0, TS − TD/scaleDown)` at
  model scope and every `RoleCapacity` entry. Strict no-fallback —
  `TotalAnticipatedSupply == 0` is a literal value, not a sentinel.
- Per-analyzer threshold overrides (`AnalyzerScoreConfig.ScaleUpThreshold` /
  `ScaleDownBoundary`) resolved per analyzer via `resolveThresholds`; the
  resolved pair applies uniformly at every scope for that analyzer. No per-role
  overrides.
- New `internal/engines/aggregation/` package with pure helpers
  (`SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`,
  `AggregateByRole`) for analyzer authors. Enforces the linearity invariant
  the optimizer's per-variant scaling math depends on.
- Sat_v2 simplification: drops in-analyzer RC/SC (engine post-step is sole
  writer); calls helpers for per-scope `Total*`; populates per-role
  `TotalAnticipatedSupply`.
- Saturation-only override-resolution loop (precursor on main, predates #1113)
  deleted — the universal post-step subsumes it.

For the **architectural decisions** (per-variant canonical model, linearity
invariant, engine writes RC/SC, strict no-fallback, alternatives considered),
see [`multi-analyzer-design.md`](multi-analyzer-design.md) §§ Architecture +
Alternatives considered.

---

## Branch state

- **Branch:** `multi-analyzer-threshold` in worktree `multi-analyzer-threshold/`.
- **Base:** `multi-analyzer-registration`@`66001d47` (PR #1225 head).
- **Tip:** `b8b823b0` (4 commits).
- **Origin:** pushed; PR #1228 OPEN against `llm-d/llm-d-workload-variant-autoscaler:main`.
- **Stacked PR diff** until #1225 merges and threshold rebases onto main.

---

## Commits landed

1. **`f59377f6`** — `engines: universal threshold post-step — pure formula at every scope`
   - Adds `applyUniversalThreshold(*AnalyzerResult, scaleUp, scaleDown)` —
     strict no-fallback at model + each `RoleCapacity` entry.
   - Adds `resolveThresholds(name, cfg) → (scaleUp, scaleDown)` for per-analyzer
     overrides.
   - In `runAnalyzersAndScore`: calls `applyUniversalThreshold(baseResult, ...)`
     after `runV2AnalysisOnly` for saturation; deletes the precursor
     saturation-only override-resolution loop.
   - `runRegisteredAnalyzers` takes `cfg` and calls `applyUniversalThreshold`
     per non-saturation analyzer.
   - `runRegisteredAnalyzer` returns `*AnalyzerResult` so the caller can apply
     post-step.
   - `interfaces/analyzer.go`: `AnalyzerResult.TotalAnticipatedSupply` and
     `RoleCapacity.TotalAnticipatedSupply` field doc-comments updated to
     "analyzer-supplied; engine reads as-is".
   - `engine_register_test.go`: 3 `runRegisteredAnalyzers` call sites updated
     to pass `config.SaturationScalingConfig{}`.
   - `engine_v2_threshold_test.go` (new): pure-formula specs at model + per-role.

2. **`4f1ab001`** — `engines/aggregation: shared helpers for analyzer aggregations`
   - New package `internal/engines/aggregation/`.
   - `ScopeTotals{TotalSupply, TotalAnticipatedSupply, TotalDemand}`.
   - Pure functions: `SumTotalSupply`, `SumTotalAnticipatedSupply`,
     `SumTotalDemand`, `AggregateByRole`.
   - `aggregation_test.go`: empty/single/multi-variant, mixed roles, empty role
     canonicalized to `RoleBoth`, zero PRC, zero replicas.
   - Imports only `internal/interfaces` — no engine/analyzer deps.
   - Not yet wired to any analyzer.

3. **`a8147e8c`** — `engines/saturation_v2: use aggregation helpers; drop in-analyzer RC/SC`
   - Phase 3: replace manual loop with `aggregation.Sum*` helper calls.
   - Phase 4: delete the in-analyzer RC/SC computation block.
   - `aggregateByRole`: replace inline aggregation with
     `aggregation.AggregateByRole`; drop per-role threshold formula; populate
     per-role `TotalAnticipatedSupply`.
   - `analyzer_test.go`: assertions migrated — sat_v2 tests verify `Total*`
     fields are populated correctly; per-scope RC/SC tests moved to
     `engine_v2_threshold_test.go` from commit 1.

4. **`b8b823b0`** — `docs: developer-guide — analyzer responsibilities + universal threshold post-step + helpers`
   - `docs/developer-guide/saturation-scaling-config.md`: rewrite "Universal
     Threshold Post-Step" section. Cover: per-variant canonical model;
     responsibility split (who writes / who reads each field); linearity
     invariant with formula; shared helpers (import path + usage examples);
     engine post-step formula at every scope; per-analyzer overrides; P/D
     disaggregation (same formula, no per-role overrides).
   - `docs/developer-guide/saturation-scaling-config.md`: post-review addendum
     applied as part of this commit (see § Addendum below) — new "Analyzer
     inputs" subsection covering `SchedulerQueue` semantics.
   - `internal/interfaces/analyzer.go`: extended `SchedulerQueue` field
     doc-comment.

---

## Verified

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty output.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- `go test -race ./internal/engines/saturation/...` — clean.
- DCO sign-off on all 4 commits.

---

## Coordination

- **Stacked on PR #1225 (`multi-analyzer-registration`).** Until #1225 merges
  and #1228 rebases onto main, the diff includes #1225's 3 commits plus our 4.
- **Provides `internal/engines/aggregation/`** for any analyzer to use; today
  consumed only by sat_v2.
- **Sat_v2 simplification** (commit 3) lands here. Was originally deferred to a
  follow-up PR; folded into the threshold rework after design discussion.
- **Cross-rebase target for `multi-analyzer-optimizer`.** When the optimizer
  PR's last commit lands locally, it cross-rebases onto this branch's tip
  (`b8b823b0`) to pick up registration plumbing + threshold post-step + sat_v2
  simplification + aggregation helpers in one hop. The optimizer plan
  ([`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md))
  documents the rebase mechanics.

---

## Open items

- **`enabled: false` veto on scale-down (cross-cutting bug).** The slice
  predicate `needsScaleDown(s) = ∀ e ∈ s : e.Spare > 0` (in
  `pipeline/analyzer_helpers.go` from the optimizer branch) treats a disabled
  analyzer (`Spare=0`) as a veto. Surfaces when sat_v2 is `enabled:false` and
  TA wants to scale down: saturation's `Spare=0` blocks all-down. Tracked in
  the optimizer plan for fix; flagged here because the threshold post-step is
  what populates the `Spare` value the predicate reads.
- **Engine model-level RC/SC for disaggregated models is buggy.** Today's
  post-step sums roles additively for model-level `Total*`, then calibrates.
  For disaggregated, the additive value is meaningless (roles aren't fungible).
  Harmless once the optimizer no longer reads it for disaggregated models.
  Follow-up: remove or redefine in the engine post-step. See
  [`multi-analyzer-design.md`](multi-analyzer-design.md) § Future direction → F5.

---

## Addendum (2026-06-02): post-review doc clarifications — applied in commit 4

Review of an earlier tip (`1ba3c978`) flagged that docs didn't make explicit
that `SchedulerQueue` is shared input across analyzers (not sat_v2-specific),
that demand-extraction from it IS per-analyzer (uses each analyzer's unit),
and that queue items aren't yet variant-attributed.

Applied changes:

- **`internal/interfaces/analyzer.go`** — extended `SchedulerQueue` field
  doc-comment to clarify it's shared input across analyzers; per-analyzer
  demand extraction; queue items are model-scoped, not variant/role-attributed.
- **`docs/developer-guide/saturation-scaling-config.md`** — new
  "Analyzer inputs" subsection between "Per-variant data is canonical" and
  "Linearity invariant".

Changes are in commit 4 of this branch (`b8b823b0`). The original verbatim
patch text is preserved in the plans-branch git history (commit `79a7647f`).

---

## History note (force-push rework)

This branch was force-pushed once during development. The pre-rework tip
`be25890f` (3 commits: `c2f57c9f`, `06b9d236`, `be25890f`) was replaced with
the current 4-commit structure after the architecture discussion that
locked the per-variant canonical model + strict no-fallback engine post-step
(see [`multi-analyzer-design.md`](multi-analyzer-design.md) § Alternatives →
A5). Pre-rework commits are reachable via `git reflog` until ~30 days of
inactivity for diff comparison if needed.

---

## References

- [`multi-analyzer-design.md`](multi-analyzer-design.md) — cross-cutting design
  doc: mission, architecture, alternatives considered, future direction.
- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md)
  — sibling Type 3 plan for PR #1225 (Item 3, this branch's base).
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) —
  sibling Type 3 plan for the optimizer branch (Item 1).
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder agent
  rules.
- [`PR1113-review.md`](PR1113-review.md) — historical review of original
  PR #1113 that decided the 3-PR split.
