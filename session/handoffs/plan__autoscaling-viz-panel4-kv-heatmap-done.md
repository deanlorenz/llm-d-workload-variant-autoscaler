from: autoscaling-viz
to: planner
session: autoscaling-viz-panel4-kv-heatmap-done

## Task done

`autoscaling-viz__panel4-kv-heatmap-plan-ready.md` is complete. Commit `0a2be3be` on
`autoscaling-viz` (tip; was `9da9f7a2`). Implements
`planning/autoscaling-viz-panel4-kv-heatmap-plan.md` (Item 2/S) in full: panel 4 fully retired and
replaced with a per-pod KV% heatmap, plus panel 3's separately-noted running-count average line
folded in.

This is a genuinely new visual (first `imshow` use in this file, per the spec's own framing) --
found two real defects during verification that weren't obvious from the code alone:

1. A crash: passing a plain list-of-RGBA-tuples to `imshow()` raised a numpy "inhomogeneous shape"
   error. Fixed with an explicit numpy array.
2. A layout collision: the mean-KV secondary axis's own [0,1] ticks/label visually collided with the
   colorbar in the same cramped space (both show the same KV% scale). Fixed by hiding the secondary
   axis's own ticks/label entirely -- the colorbar is now the one shared scale reference.

One judgment call worth flagging: the old panel 4 also carried a router-imbalance text annotation,
co-located there for space reasons unrelated to its queue content. The spec's retirement scope was
specifically the three queue series, not this annotation, so I kept it on the new panel 4 rather than
guessing it should be dropped too -- flagging in case that's not what was intended.

Full detail (the colormap anchoring, the outlier-marking rule, the dead/live-pod distinction) is in
`session/status/autoscaling-viz.md`, rewritten in place, prior entries preserved below the fold.

## Verification, per the spec's own checklist

`m-satta-dwell` re-rendered fresh against the exact committed tip `0a2be3be`:

```
session-notes/review-samples/m-satta-dwell-kv-heatmap-0a2be3be.png
```

(+ matching bundle.json/coverage.json). **Stamp confirmed matching `git rev-parse --short HEAD`**
(`0a2be3be`) in both `coverage.json`'s `extractor_sha` and the PNG's own embedded metadata.
Color transition at k_sat is visually sharp (a genuine saturation event on this run shows as a
distinct white/green-to-red change, not a gradual blend). Dead/live/saturated pods all
distinguishable. Also spot-checked the golden pre-redesign 2-pod bundle for backward compat -- no
crash, same distinctions hold at the small end of the pod-count range.

Per the spec's own instruction: **not marking push-ready**. This may need a visual-tuning follow-up
round the same way Task 8's hatch work did -- the outlier-marking rule especially is explicitly
provisional.

## Filesystem actions taken

- `autoscaling-viz__panel4-kv-heatmap-plan-ready.md.WIP` -> `.DONE` (alongside this write).
- This `plan__` handoff filed with the exact render path and confirmed stamp.

## Nothing else touched

Branch tip `0a2be3be`, working tree otherwise clean (same pre-existing untracked review-sample
files, plus this task's own new render).
