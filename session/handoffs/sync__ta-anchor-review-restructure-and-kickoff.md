from: review agent (design-review continuation)
to: sync
session: ta-anchor review restructure + TA-0.9-enablement plan kickoff

## What changed (all on disk, uncommitted — plans branch)

1. **`planning/ta-anchor-refactor-review.md` restructured** into two clean parts (was an
   interleaved review+correction). Now:
   - **Part 1 — Review of the superseded `ta-anchor-refactor-plan.md`** (F1–F12, C1, E1–E13
     coder-executability findings, Confirmed-correct, Recommended-disposition). On record only;
     carries a blockquote that its per-finding "Fix (planner)" directions are superseded by Part 2.
   - **Part 2 — Recommended course of change: spec for the new Type-3 plan** (§2.1 corrected
     two-phase mechanism; §2.2 how it resolves the Part-1 findings; §2.3 decisions — QM=error,
     liveness=do-nothing, AnalyzerName-validation=separate PR, scale-from-zero=orthogonal;
     §2.4 partial-scale-from-zero **STILL UNDER DISCUSSION**; §2.5 TA-side self-fallback **agreed**;
     §2.6 test requirements; §2.7 scope fences). Doc still **Status: DRAFT**. 971 lines.
   - Key design deltas from the superseded plan: **no stored `.Anchor` field** (derived on demand);
     order-independent ballot with per-entry status tags; anchor built by **per-variant merge keyed
     by `VariantName`** ((a) identity from sat, (b) sizing from binding analyzer, per-variant
     fallback to sat's (b) before disabled-entry removal).

2. **Kickoff issued** for a NEW Type-3 plan:
   `session/handoffs/plan__ta09-critical-enablement-plan-kickoff.md` (to: planner). Task: author a
   new Type-3 plan (new filename, likely fresh branch) fixing **all critical TA enablement issues
   for 0.9**, using the map doc for current code + review Part 2 as the spec.
   **This kickoff SUPERSEDES `plan__ta-anchor-refactor-mechanism-redesign.md`** (still `.WIP`) —
   different deliverable (new plan, not fold-into-old-plan) and the old handoff's `L490-784`
   section refs are stale after the restructure.

3. **Auto-review armed.** Dean authorized an automatic plan review when ready (he's asleep). The
   planner will drop `session/handoffs/review__ta09-enablement-plan-ready.md` (exact filename
   dictated in the kickoff, to avoid colliding with the code-reviewer's
   `review__ta-anchor-refactor-criteria.md` or the coder's `ta-anchor-refactor__*` triggers). A
   persistent monitor watches that exact path; on arrival I mark it `.WIP`, review the new plan
   against Part 2, write a standalone review section, mark `.DONE`.

## Suggested CURRENT.md update (anchor-refactor mission row / activity)

The anchor-refactor mission has **pivoted from "fold correction into the existing plan" to "author
a fresh Type-3 TA-0.9-enablement plan against a corrected mechanism spec."** Reflect in the
`ta-anchor-refactor` PR-Status row / Recent-activity abstract:
- Review doc `ta-anchor-refactor-review.md` restructured → Part 1 (old-plan review) + Part 2 (spec
  for the new plan); DRAFT.
- New planner kickoff sent for a fresh TA-0.9-enablement Type-3 plan (new file, likely fresh
  branch); `ta-anchor-refactor-plan.md` is now the **superseded** doc (Part 1 subject).
- Mechanism now: no stored `.Anchor` field; two-phase (generation tags status / getter binds &
  per-variant-merges by VariantName); QM=error (DEFERRED); TA-side self-fallback agreed (with
  Cost/AcceleratorName ranking-inversion guard); partial-scale-from-zero mechanism still under
  discussion.
- Branch `34055d77` (Dean's stored-`.Anchor`, positional-binding commit) and the Aug-4 fold-in
  (`68bda1a1`/`192ae06b`, `cloneAnalyzerResult` + 87-site `withSatEntry`) are **both superseded**
  by the no-stored-field design — planner decides fresh-branch vs. rework in the new plan.

## Open questions / follow-ups (none blocking)

- Whether to commit the restructured review doc + these handoffs to the `plans` branch — deferred
  to Dean (no commit made without his say-so).
- §2.4 (partial scale-from-zero mechanism A/B) remains an open design question for Dean to finalize
  before it can enter any committed plan scope.
- Pre-existing sat-v2 bug flagged (aggregateByVariant never backfills Cost/AcceleratorName for
  zero-replica variants) — standalone fix, not this plan; keep on the Issues-to-Open radar.
