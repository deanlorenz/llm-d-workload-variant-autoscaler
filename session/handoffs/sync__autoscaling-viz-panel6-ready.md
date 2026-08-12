from: autoscaling-viz
to: sync
session: autoscaling-viz-decision-panel

## What changed
Commit `cff4e4c0` on `autoscaling-viz` (tip, was `5a0c607f`): panel 6 (scaling-decision reasons)
added to render_real_trace.py, controller.log parsing added to extract_real_trace.py. Completes
the Type 3 `planning/autoscaling-viz-decision-panel-plan.md` (parent epic Item 1 of
`planning/autoscaling-viz-followon-plan.md`), picked up from the `to: autoscaling-viz` handoff
`autoscaling-viz__decision-panel-ready.md` (now `.DONE`). Full detail in
`session/status/autoscaling-viz.md` (rewritten in place, prior state preserved below the new entry).

Verified against real campaign data (not synthetic): m-satta-dwell (both analyzers), m-ta-staircase
(TA-only, absent-analyzer annotation), and a no-controller-log bundle (degrade path). All three
re-renders viewed as PNGs. Not pushed — local commit only, 7 commits ahead of origin/autoscaling-viz
now (was 6).

Wrote review__autoscaling-viz-ready.md trigger per §5.4 before this handoff, per convention.

## Update CURRENT.md
The autoscaling-viz entry under "Recent activity" should note: decision-panel plan (Item 1 of the
follow-on epic) is code-complete and in review, tip `cff4e4c0`. The follow-on epic
(planning/autoscaling-viz-followon-plan.md) still has Items 2-6 open (panel 4 queue-source design,
estimation-model code, EPP scorer signal, coverage-check doc, folder-structure question) --
explicitly out of scope for this Type 3, not touched.

## Open questions / follow-ups
- A real correction to the plan doc's own claim: the saturation-analyzer-absent line fires every
  ~60s tick, not "zero or one per run, not per tick" as the plan states. Doesn't change any code,
  but the plan doc's § Data source text is now slightly wrong for a future reader. Not fixed by me
  (coders don't edit Type 3 plan docs) -- flagging for whoever owns that doc next.
- Item 3 of the coverage-check decision (whether to add row 17) was resolved YES per the plan's own
  "recommended" language -- not a new open question, just noting the judgment call was exercised as
  the plan anticipated.
