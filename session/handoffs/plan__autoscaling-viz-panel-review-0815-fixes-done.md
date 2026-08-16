from: autoscaling-viz
to: planner
session: autoscaling-viz-panel-review-0815-fixes-done

## Task done

`autoscaling-viz__panel-review-0815-fixes-plan-ready.md` is complete. Commit `9da9f7a2` on
`autoscaling-viz` (tip; was `d7fa6ee5`). Implements
`planning/autoscaling-viz-panel-review-20260815-fixes-plan.md` (Items Q/R/T/U/W) in full,
`render_real_trace.py` only, no extractor changes.

Worth flagging: **Item R retracts part of Task 8's own work** (waiting's hatch character back to
diagonal, since the line width/color choices from Task 8 were already correct per Dean's own
confirmation). And **Item W is a real correctness finding, not a cosmetic tweak** — the
investigation (against the `m-satta-dwell-fresh-d7fa6ee5.png` sample from the prior render request)
found the drain-window band had been showing normal, healthy, sometimes-spiking pod activity the
entire time, never an actual wind-down, for all 6 pods checked. Relabeled to describe what the
signal actually is (proximity to a fleet-level scale-down event) rather than what it isn't (a
verified per-pod drain).

## Verification, per the spec's own checklist

Both required cells extracted+rendered **fresh against the exact committed tip** `9da9f7a2`:

- `session-notes/review-samples/m-satta-dwell-panelreview0815fixes-9da9f7a2.png` (+ matching
  bundle.json/coverage.json) -- Items R, T, W all visually confirmed (diagonal waiting hatch,
  "replica-delta" y-label with reason-code annotations on the lines, the relabeled drain-window
  legend text).
- `session-notes/review-samples/m-ta-prefill-knee-panelreview0815fixes-9da9f7a2.png` (+ matching
  bundle.json/coverage.json) -- Items Q and U confirmed (mean±std corner text on panel 1b; suptitle
  clean of "WEAK TIME ANCHOR", footer's first line carries it instead).

**Stamps confirmed matching `git rev-parse --short HEAD` (`9da9f7a2`) on both renders**, both places
(`coverage.json` `extractor_sha`, and the PNG's own embedded `render_sha`/`extractor_sha` metadata).

Per the spec's own instruction: **not marking anything push-ready** -- this is a report of the
fixes and their verification, not a push-ready declaration. Full detail in
`session/status/autoscaling-viz.md`, rewritten in place, prior entries preserved below the fold.

## Filesystem actions taken

- `autoscaling-viz__panel-review-0815-fixes-plan-ready.md.WIP` -> `.DONE` (alongside this write).
- This `plan__` handoff filed with the exact render paths and confirmed stamps.

## Nothing else touched

Branch tip `9da9f7a2`, working tree otherwise clean (same pre-existing untracked review-sample
files, plus this task's own two new render pairs).
