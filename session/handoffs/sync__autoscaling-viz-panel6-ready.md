from: autoscaling-viz
to: sync
session: autoscaling-viz-panel6

## What changed

Commit `cff4e4c0` on `autoscaling-viz` (tip; was `5a0c607f`) — "feat(viz): add panel 6 --
scaling-decision reasons from controller.log". Implements
`planning/autoscaling-viz-decision-panel-plan.md` (Item 1 of
`planning/autoscaling-viz-followon-plan.md`) in full: `extract_real_trace.py` parses
`analyzer-result` / `scaling-decision` / analyzer-absent lines out of `controller.log` into a new
`derived.scaling_log` bundle key; `render_real_trace.py` adds panel 6 (reason-code strip per
analyzer lane, decision markers via the existing shared axvline loop, analyzer-absent annotation,
legend, degrade-to-`empty()` when no data) and bumps the grid to `subplots(7, 1, ...)`. Coverage
row 17 ("Scaling-decision log present") added.

Verified against real 2026-08-10 campaign data (not synthetic): `m-satta-dwell` (both analyzers, 9
scale transitions visible, reason codes track the dwell cycle), `m-ta-staircase` (TA-only,
absent-analyzer annotation fires correctly), and a no-`controller.log` bundle (clean degrade). All
three re-renders viewed as PNGs. `make test`/`lint`/`gofmt` are N/A — Python-only worktree, no
Makefile, no test suite, per the Type 3's own Verification section.

Nothing pushed. Branch is 7 commits ahead of `origin/autoscaling-viz` (6 pre-existing from
2026-08-08 plus this one). Working tree clean.

A `review__autoscaling-viz-ready.md` trigger is already filed for the plan-agent to route to
`/code-review` per §5.4 — this handoff is the CURRENT-update half, not a push-ready declaration.

## Update CURRENT.md

In the autoscaling-viz entry under § Recent activity: record panel 6 as landed, code-complete, in
review — commit `cff4e4c0` (tip, was `5a0c607f`), Item 1 of the follow-on epic. Note the plan-doc
correction below. Items 2-6 of the follow-on epic (panel 4 queue-source design, estimation-model
code, EPP scorer signal, coverage-check doc, folder-structure question) remain open, out of scope
for this Type 3.

## Open questions / follow-ups

- **Plan-doc correction, not yet fixed anywhere**: `planning/autoscaling-viz-decision-panel-plan.md`
  § Data source says the analyzer-absent line fires "zero or one per run, not per tick" — verified
  wrong by direct count on `m-ta-dwell/controller.log` (8 occurrences, one per ~60s tick). Does not
  change the implementation (a first-seen boolean/timestamp was already the right capture), just
  the doc's own description. Flagged for whoever owns that plan doc next — coders don't edit Type 3
  plans.
- Full detail, judgment calls (height ratio, bundle key shape, coverage row), and verification
  narrative: `session/status/autoscaling-viz.md` (rewritten in place, prior 2026-08-08 state
  preserved below the fold).
