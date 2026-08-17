# Panel 4/3/6 visual follow-up after first KV% heatmap render — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 2. Follow-up to [`autoscaling-viz-panel4-kv-heatmap-plan.md`](autoscaling-viz-panel4-kv-heatmap-plan.md)
(commit `0a2be3be`) — Dean's direct feedback on the first render, viewed by the planner against a
local re-render of that commit's code (`session-notes/review-samples/m-satta-dwell-panelreview0815fixes-9da9f7a2-bundle.json`,
extractor unchanged by `0a2be3be` so this bundle is valid input). Six items, three panels; no design
questions reopened — the heatmap concept and color-scale anchor from the first spec are confirmed
good, these are visual-execution fixes.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Panel 4, item 1 — row separators {#p4-separators}](#panel-4-item-1--row-separators-p4-separators) L24:33
- [Panel 4, item 2 — order rows by scale-up sequence {#p4-order}](#panel-4-item-2--order-rows-by-scale-up-sequence-p4-order) L34:49
- [Panel 4, item 3 — outlier ticks read as clutter {#p4-outliers}](#panel-4-item-3--outlier-ticks-read-as-clutter-p4-outliers) L50:64
- [Panel 3, item 4 — mean-running line color {#p3-color}](#panel-3-item-4--mean-running-line-color-p3-color) L65:73
- [Panel 3, item 5 — secondary-axis zero alignment {#p3-axis}](#panel-3-item-5--secondary-axis-zero-alignment-p3-axis) L74:85
- [Panel 6, item 6 — reason-code label overlap {#p6-overlap}](#panel-6-item-6--reason-code-label-overlap-p6-overlap) L86:98
- [Verification {#verification}](#verification-verification) L99:113

## Panel 4, item 1 — row separators {#p4-separators}

Dean: "the horizontal lines should be at the bottom of each bar" — read as: each pod's heatmap row
needs a visible horizontal separator at its bottom edge. Today rows blend into their neighbors with
only antialiasing between adjacent cells, no deliberate border. Add a thin horizontal line (e.g.
`INK` at low alpha, or matching whatever separator convention this file uses elsewhere) at each row
boundary so all 15 rows are crisply distinguished at a glance.

[↑ TOC](#toc)

## Panel 4, item 2 — order rows by scale-up sequence {#p4-order}

Dean: "the pod numbering should be order of scaling — current order is confusing." Rows currently
use panel 3's existing `pod_num` assignment (whatever order that scheme assigns — not scale-up
order), so a pod's row position has no relationship to when it actually joined the fleet. Reorder
panel 4's rows by **first-appearance time** (the pod's own first sample's `t`, ascending) — pod
added earliest is row 1, most recently added is row 15 (or however many are in this run). **This
changes only panel 4's row order, not the `pod_num` values themselves** — panel 3 and the pod-number
legend line (`1=2qvfm 2=2vxwj ...`) stay on the existing scheme; do not resequence `pod_num`
globally, since that would break the two panels' shared numbering that Item 2's original spec
established. If panel 4 needs its own row label distinct from `pod_num`, use a separate label (e.g.
"row N" or keep showing the `pod_num` value but positioned by scale-up order) — coder's judgment on
the cleanest way to avoid two competing numbering schemes reading as one.

[↑ TOC](#toc)

## Panel 4, item 3 — outlier ticks read as clutter {#p4-outliers}

Dean: "what are the black vertical lines? not [good]" — confirmed by zooming into the render: two
different things are both rendering as black verticals on this panel. (a) The shared scale-up/down
decision `axvline`s every panel gets "for free" — those are fine, same convention as every other
panel, not what's being flagged. (b) The **outlier-marking ticks** from the first spec's provisional
rule (cell > 1 stdev above the live-pod mean) — these render as short solid black tick marks sitting
inside individual rows, and read as noise rather than a clear signal. Change the outlier marking to
something visually lighter/clearer — e.g. a thin colored border on the outlier cell itself (matching
the cell's own row, not a separate black mark), or a small marker shape distinct from the axvlines'
own black/ink styling so the two are never confused. Exact treatment at the coder's discretion; the
requirement is that it stops looking like the same thing as the decision-event lines.

[↑ TOC](#toc)

## Panel 3, item 4 — mean-running line color {#p3-color}

Dean: "the new line should be solid yellow or red." The running-count average line added by the
first spec is currently dotted black — change to solid, and either yellow or red (coder's choice
between the two, whichever reads better against the existing stacked-bar colors on this panel; check
by viewing the actual render before committing to one).

[↑ TOC](#toc)

## Panel 3, item 5 — secondary-axis zero alignment {#p3-axis}

Dean: "the 0 of the secondary axis should be aligned with main y-axis." The running-average line's
secondary axis (added via `twinx()`, same pattern as the existing KV-ceiling secondary axis) doesn't
currently have its zero-point aligned with the primary stacked-bar axis's zero — so the line's
baseline floats at a different height than the bars' own baseline, which makes the two axes read as
disconnected rather than sharing a common reference point. Set the secondary axis's y-limits so 0
lines up with the primary axis's 0 (e.g. `set_ylim(bottom=0)` on both, or compute the secondary
limit to match the primary's proportional zero position if the two ranges differ).

[↑ TOC](#toc)

## Panel 6, item 6 — reason-code label overlap {#p6-overlap}

Dean: "good labels, but some overlap." The first-occurrence reason-code annotations (Item T,
`autoscaling-viz-panel-review-20260815-fixes-plan.md`) collide with each other at some points —
visible on the `m-satta-dwell` render around t≈150-350 where several reason codes appear close
together in both time and replica-delta value. Adjust the annotation offset/placement (e.g. stagger
the `xytext` offset per label, or nudge overlapping ones apart) so labels remain readable when their
underlying points are close together. Exact collision-avoidance approach at the coder's discretion —
this doesn't need to be a general-purpose label-layout algorithm, just enough to fix the specific
overlaps visible on this run.

**A real infinite-loop bug, caught during verification, not by inspection (committed `f92d3c19`).**
The first implementation used `-min_label_gap` as the "empty slot" default in its collision-avoidance
`while` loop. A record timestamped before the bundle's own `t0` (`x=-116` against
`min_label_gap≈14`) made every slot's default compare as "still colliding," so the loop never
terminated. First symptom: a render that had taken ~5s suddenly hung past 3 minutes of pure CPU burn
with zero progress — not a crash, not a gradual slowdown. Root-caused methodically: confirmed the
prior commit still rendered in ~5s (ruling out environment/system slowness), then instrumented the
actual `render()` call with print-and-flush statements at each panel's start — all four panels'
drawing code completed in under 1 second combined, isolating the hang to code after panel 6's last
print, further instrumentation pinned to the exact `while` loop. Fixed with `float('-inf')` as the
sentinel, which no real `x - min_label_gap` value can ever exceed. Re-verified: `m-satta-dwell`
rendered in ~4s after the fix, matching the pre-regression baseline.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render `m-satta-dwell` fresh against the coder's own tip; confirm stamp match.
- Item 1: confirm all pod rows in panel 4 have a visible bottom separator.
- Item 2: confirm panel 4's row order now tracks scale-up sequence (earliest-added pod at row 1),
  and confirm panel 3 / the pod-number legend line are unaffected (still using the original
  `pod_num` scheme).
- Item 3: confirm outlier marks are visually distinct from the shared decision-event axvlines.
- Item 4: confirm the running-average line in panel 3 is solid and yellow or red.
- Item 5: confirm the secondary axis's 0 visually lines up with the primary axis's 0 in panel 3.
- Item 6: confirm no two reason-code labels overlap in panel 6 on this run's render.
- Report back via a `plan__` handoff with the exact render path and confirmed stamp, per the usual
  protocol — do not mark push-ready without Dean's review of the actual rendered output.

[↑ TOC](#toc)
