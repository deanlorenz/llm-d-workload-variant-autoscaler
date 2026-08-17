# Panel 3 visual scheme: consistent color, dots/dashes overlay, thin outlines — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 7 / Item K. Source: [`autoscaling-viz-panel-review-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md)
§ Item K. Was blocked on Item J (drain-window fix) landing first — **that landed** (`e188d244`,
reviewed push-ready) — this spec is now unblocked.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L18:28
- [The four changes {#changes}](#the-four-changes-changes) L29:61
- [What NOT to change {#not-to-change}](#what-not-to-change-not-to-change) L62:76
- [Verification {#verification}](#verification-verification) L77:88

## Goal {#goal}

Panel 3 (`render_real_trace.py`, the requests-per-pod stack) currently uses a shared color per pod
for its running band, with a dotted hatch for draining and a diagonal `////` hatch for waiting, plus
a thin outline on running bars only. Dean's direct feedback on the rendered figure, restated
precisely: keep one solid color per pod across all three bands (no code change needed here — this
is already true), but change how draining/waiting are visually distinguished on top of that color,
and extend the outline treatment uniformly.

[↑ TOC](#toc)

## The four changes {#changes}

1. **Draining overlay → dots, thinner.** Today's draining band already uses `hatch='....'` — keep
   the dot pattern, but the *weight* needs reducing: today's hatch density/linewidth reads as too
   heavy at a glance. Reduce matplotlib's hatch linewidth (`hatch.linewidth` rcParam, or a
   per-artist override if matplotlib's hatch API in this version supports one) and/or increase the
   spacing between dots, so the overlay reads as light texture on the pod's own color rather than a
   second competing fill. No exact numeric target given — tune by rendering and looking, the same
   way Task 1/2's hatch fix was tuned.
2. **Waiting overlay → dashed lines, not diagonal hatch.** Today's waiting band uses `hatch='////'`
   (diagonal lines). Change to a dashed-line-style hatch — matplotlib's hatch vocabulary includes
   `'--'`-family patterns (check current matplotlib version's supported hatch strings; if dashed
   hatch patterns aren't directly supported, an alternative is a custom low-density diagonal at a
   different angle/weight than draining's dots, but prefer an actual dash pattern if the version
   supports it) — the goal is that draining (dots) and waiting (dashes) are visually distinct from
   each other and both distinct from the solid running band, at a glance, without needing the
   legend to tell them apart.
3. **Overlay weight, both bands: thinner overall.** Same instruction as (1) applied to both
   draining and waiting — Dean's exact words: "needs to be much finer/thinner." Whatever numeric
   values are chosen for both hatches, they should read as noticeably lighter than what's shipped
   today, not just adjusted at the margin.
4. **Bar outline: extend uniformly, keep very thin.** Running bars already carry `edgecolor=INK,
   linewidth=0.4` (from Task 2). Extend the same treatment to draining and waiting bars if they
   don't already have it (check the current code — draining bars use `edgecolor=C_ACT` today per
   the draining-band comment, which may need to change to `INK` for consistency, or may be
   intentionally different to reinforce the color-coding; use judgment, but default to consistency
   with running bars' `INK` outline unless there's a clear reason draining should look different).
   Confirm `linewidth=0.4` actually reads as "very very thin" once rendered at the figure's own DPI
   (120, per the existing `fig.savefig(path, dpi=120)` call) — reduce further (e.g. `0.25`-`0.3`) if
   it still looks heavier than intended once viewed.

[↑ TOC](#toc)

## What NOT to change {#not-to-change}

- Per-pod color *assignment* (`BAND_SHADES`-by-sorted-order) — Dean confirmed this stays as-is; only
  how running/draining/waiting *reuse* the assigned color changes.
- The pod-number-to-hash legend key (Task 1's fix) — unrelated, don't touch.
- The KV-ceiling secondary-axis logic (Task 2's redesign) — confirmed working, unrelated to this
  spec, don't touch.
- Panel 3's on-figure title text — separately flagged as stale in
  [`autoscaling-viz-review-20260813.md`](autoscaling-viz-review-20260813.md) Finding 2 (still says
  "running, waiting, router-side," doesn't mention draining/EPP-queue); fold that one-line fix into
  this commit since it's cheap and touches the same panel, but don't expand scope beyond that plus
  the four items above.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render at least 2 cells with real draining AND waiting bands both present in the same run
  (e.g. `m-satta-dwell` or `m-ta-staircase`, both used to verify the drain-window fix) — confirm
  dots vs. dashes are visually distinguishable from each other and from the solid running fill at
  normal viewing size, not just at high zoom.
- Confirm a 15+-pod run (e.g. `m-satta-dwell`) still reads cleanly — the overlay thinning shouldn't
  make bands invisible at that pod density, only less visually heavy.
- Confirm the outline change doesn't regress legend legibility (Task 1/2's fixes) — view the full
  panel, not just a cropped bar.

[↑ TOC](#toc)

## Outcome (committed `b7920cd3`) {#outcome}

Four changes plus one stale-title fix, all in `render_real_trace.py` only:
- **Draining hatch color, not just weight.** The ask was "thinner"; thinning alone wasn't enough —
  the dotted hatch defaulted to a dark color with too little contrast against the darker end of
  `BAND_SHADES` to actually read as dots. Caught this on a real multi-pod render, not in an isolated
  single-color hatch test — the isolated test looked fine and would have shipped a fix that still
  didn't work on the actual figure. Set an explicit light hatch color (`#f5f5f5`, matching what
  waiting already used).
- **Waiting hatch: `/` → `-`.** Checked matplotlib 3.11.1's actual supported hatch strings first
  (`/,\,|,-,+,x,o,O,.,*` — no literal dash pattern exists) before picking `-` as the closest built-in
  to "dashed lines."
- **Uniform thin outlines, both mechanisms.** `linewidth=0.25` across all three bands for the bar's
  own border, plus `set_hatch_linewidth(0.3–0.4)` on the hatch pattern itself — two independent
  matplotlib mechanisms, both needed thinning; found the per-artist
  `set_hatch_linewidth()`/`set_hatchcolor()` API exists in this matplotlib version by checking
  `dir()` on a bar artist first rather than assuming only the global `rcParams['hatch.linewidth']`
  was available (which would have also thinned panel 2's unrelated hatch, out of scope).
- **Stale title fixed**: "running, waiting, router-side" → "running, draining, waiting, EPP queue".

**Verification**: `m-satta-dwell` (15 pods, real draining + waiting both present) at normal viewing
size and multiple zoom levels — the hatch-color fix's necessity was found precisely by this process
(isolated test passed, real render didn't, re-diagnosed, fixed, re-verified). `m-ta-staircase`
(3 pods, no draining/waiting in this run) as a smaller-scale regression check — no crash, thin
outlines apply uniformly, confirms the ≤6-pod per-pod-legend path is unaffected. `make
test`/`lint`/`gofmt` N/A.

[↑ TOC](#toc)
