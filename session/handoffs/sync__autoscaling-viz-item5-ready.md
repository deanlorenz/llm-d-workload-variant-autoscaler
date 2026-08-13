from: autoscaling-viz
to: sync
session: autoscaling-viz-item5-ready

## What changed

Commit `34afc197` on `autoscaling-viz` (tip; was `cff4e4c0`) — "docs(viz): add COVERAGE-CHECKS.md
reference, cross-link from README". Implements Item 5 of
`planning/autoscaling-viz-followon-plan.md` (coverage-check reference doc, DECIDED-not-yet-written):
transcribes the Type 1's coverage-check table (`autoscaling-viz-design.md` § Coverage-check
specification) into a new `COVERAGE-CHECKS.md` at the worktree root, cross-linked from README.

Reconciled against current code, not copied verbatim from the Type 1 — the Type 1's table predates
panel 6 and has 16 rows; live re-extraction against `real-trace/staircase-20260803` and a
2026-08-10 campaign run dir confirmed the current extractor emits 17: panel 6 added a new row 16
("Scaling-decision log present") ahead of the old conditional row ("Knee matches shape
prediction"), now renumbered 17. The doc reflects the verified live order, not the stale table.

`make test`/`lint`/`gofmt` N/A — Python-only worktree, no Makefile, no test suite, per the Type 3's
own Verification section (same as every prior entry on this branch).

Nothing pushed. Branch is 9 commits ahead of `origin/autoscaling-viz`. Working tree clean.

## Update CURRENT.md

In the autoscaling-viz entry under § Recent activity: record Item 5 (coverage-check reference doc)
as landed — commit `34afc197` (tip, was `cff4e4c0`). Items 2, 3, 4, 6 of the follow-on epic remain
open, gated on Dean, unchanged.

## Open questions / follow-ups

- **Routing question on `autoscaling-viz-panels__kickoff.md`** — this trigger is addressed to "a new
  dedicated session" for a *planning* review of panel design, not a coding task. Marked `.WIP` (see
  the companion `plan__` handoff for the full account) but not acted on by this coder session,
  consistent with Dean's direct instruction that planning questions route to a planner. Needs either
  planner pickup or a routing confirmation.
- **Confirmed-again footgun**: the inert-allowlist issue (writes to `plans/session/status/` and
  `plans/session/handoffs/` blocked by the worktree-isolation guard, contra CONVENTIONS) is still
  live as of this session — see the `plan__` handoff for detail. Worked around, not fixed.
