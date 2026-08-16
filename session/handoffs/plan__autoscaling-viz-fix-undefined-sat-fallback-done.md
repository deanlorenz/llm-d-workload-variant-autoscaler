from: autoscaling-viz
to: planner
session: autoscaling-viz-fix-undefined-sat-fallback-done

## Task done

`autoscaling-viz__fix-undefined-sat-fallback.md` is complete. Commit `0aade22f` on `autoscaling-viz`
(tip; was `f92d3c19`). Fixes the review finding in
`plan__autoscaling-viz-review-panel4-sat-nameerror.md`: `render_real_trace.py:874`'s `k_sat =
sat.get('threshold') or SAT` referenced an undefined name.

Added `SAT = 0.85` as a local module constant (matching this file's existing constant style, e.g.
`BIN`/`GRID`/`W_WORK`), not an import of `extract_real_trace`'s own `SAT`, since this file is
designed to run standalone against just a `bundle.json`.

**Verified both directions, not just that the name now exists**: reproduced the exact `NameError` on
the prior commit (`f92d3c19`) using a synthetically null-`threshold` bundle, then confirmed the same
input renders clean after the fix. Full detail in `session/status/autoscaling-viz.md`, rewritten in
place, prior entries preserved below the fold.

## Filesystem actions taken

- `autoscaling-viz__fix-undefined-sat-fallback.md.WIP` -> `.DONE` (alongside this write).
- This `plan__` handoff filed.

## Nothing else touched

Single-line-plus-comment fix, one file. Branch tip `0aade22f`, working tree otherwise clean (same
pre-existing untracked review-sample files, nothing new this task -- no re-render needed since this
is a latent-only fix that no existing bundle actually triggers).
