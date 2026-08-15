# Panel review 2026-08-15/16 fixes: Items Q/R/T/U/W — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 12. Source: [`autoscaling-viz-panel-review-20260815.md`](autoscaling-viz-panel-review-20260815.md)
— every item below is resolved with Dean's exact wording; nothing here is exploratory. All target
`render_real_trace.py` only — no extractor changes.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Item Q — panel 1b text: mean±std {#item-q}](#item-q--panel-1b-text-meanstd-item-q) L21:31
- [Item R — panel 3 waiting hatch: diagonal, white, thinnest {#item-r}](#item-r--panel-3-waiting-hatch-diagonal-white-thinnest-item-r) L32:50
- [Item T — panel 6: y-label + marker-label-on-first-occurrence {#item-t}](#item-t--panel-6-y-label--marker-label-on-first-occurrence-item-t) L51:69
- [Item U — WEAK TIME ANCHOR: move to footer {#item-u}](#item-u--weak-time-anchor-move-to-footer-item-u) L70:88
- [Item W — drain-window relabel {#item-w}](#item-w--drain-window-relabel-item-w) L89:109
- [What NOT to change {#not-to-change}](#what-not-to-change-not-to-change) L110:121
- [Verification {#verification}](#verification-verification) L122:138

## Item Q — panel 1b text: mean±std {#item-q}

`render_real_trace.py:528` — current: `b.set_title(f'{s_per_1000:.2f}s per 1000 tokens (mean,
delivered)', ...)`. The `s_per_1000` mean is already computed from the delivered-work series
immediately above this line — add that same series' standard deviation and change the text to
`f'{s_per_1000:.2f}±{std_per_1000:.2f}s per 1000 tokens (mean±std, delivered)'` (exact format
string at the coder's discretion, but must show both numbers and label them mean±std, not mean
alone).

[↑ TOC](#toc)

## Item R — panel 3 waiting hatch: diagonal, white, thinnest {#item-r}

`render_real_trace.py:704-708` — current: `hatch='--', edgecolor=INK, linewidth=0.25`, then
`bar.set_hatch_linewidth(0.3)`, `bar.set_hatchcolor('#f5f5f5')`. **Change only the hatch character**,
from `'--'` to `'/'` (or `'////'`, whichever this codebase's existing convention prefers — draining
elsewhere in this file and the pre-Task-8 waiting band both used repeated characters like `'....'`;
match that convention). Do **not** change `edgecolor`, `linewidth`, `hatch_linewidth`, or
`hatchcolor` — those are already correct per Dean's own confirmation ("line width and color is
good") and match Item R's requirements (white via `#f5f5f5`, thinnest already tuned via
`set_hatch_linewidth(0.3)`).

Also update the comment block at lines 690-697, which currently justifies the horizontal choice —
that justification is retracted; replace with a short note that diagonal is what Dean asked for,
citing this spec, not a restatement of the old (wrong) reasoning.

Draining's own hatch (`'....'`, line 664) is unchanged — not part of this item.

[↑ TOC](#toc)

## Item T — panel 6: y-label + marker-label-on-first-occurrence {#item-t}

Two changes, both in the panel 6 block (`render_real_trace.py:898-980`):

1. **Y-axis label** (line 976): change `'replicas\n(signed)'` to `'replica-delta'`.
2. **Annotate each marker's reason-code label at its first occurrence.** Today (lines 927-942) every
   scatter point for a reason code is drawn with `label='_nolegend_'`, and the shape-to-reason
   mapping is only documented via the compact text key at lines 959-967 (`markers: o=P1-obs
   s=P2-hist ...`). Keep that text key (Dean didn't ask to remove it, only to make it easier to
   follow) and additionally: the first time a given `reason` is plotted for a given analyzer line,
   call `g.annotate(reason, (x, y), ...)` near that point (small font, e.g. `fontsize=6`, offset a
   few points up/right so it doesn't sit on top of the marker) instead of leaving it unlabeled.
   Track "first occurrence" per reason code globally across the whole panel (not per-analyzer-line),
   matching how `reason_markers` already dedups shape assignment at lines 931-933 — reuse that same
   dict's insertion order, or a parallel `set()`, to know when a reason is being plotted for the
   first time.

[↑ TOC](#toc)

## Item U — WEAK TIME ANCHOR: move to footer {#item-u}

`render_real_trace.py:302-315` — current: the suptitle (`head`) gets `'   [WEAK TIME ANCHOR —
arrival-time panels unreliable]'` appended at line 314 when `weak` is true. **Remove that append
from `head`/`fig.suptitle`.** Instead, when `weak` is true, add a short marker to the footer
(`foot`, built starting at line 1003) — e.g. prepend `'WEAK TIME ANCHOR — arrival-time panels
unreliable. '` to the existing `foot` string before the `caveats:`/`not exercised by this run:`
lines, so it reads as the first thing in the footer rather than competing with those. The existing
detailed explanation (the `warns` entry that produces "engine occupancy exceeds request-derived
in-system count on 7% of scrapes despite corr=0.9995...") already flows into `foot` via the
`caveats:` join at lines 1004-1006 — do not duplicate that text, just add the short marker phrase
so a reader sees *that* something is weak before reading why.

Per Dean: this placement is explicitly provisional ("place U in footer text for now... we discuss
details of what it means later") — do not treat the exact footer wording as final, just get the
suptitle clean of it.

[↑ TOC](#toc)

## Item W — drain-window relabel {#item-w}

No change to `pod_drain_windows()` itself (`extract_real_trace.py`) — the window's start/end
computation is not being changed, only what the rendered legend/label claims about it, in
`render_real_trace.py`.

`render_real_trace.py:665-666` — current legend label: `'draining (ready, not desired -- finishing
in-flight work)'`. This claims a graceful wind-down that the investigation disproved (the pod is
fully live, `run` climbing/spiking, right up to its last sample — see the review doc Item W).
**Change the label to describe what the signal actually is:** something like `'pod removed near a
scale-down event (not necessarily draining -- see docs)'` or equally accurate wording — must not
use "finishing in-flight work" or otherwise imply an observed decay. Exact phrasing at the coder's
discretion as long as it doesn't overclaim.

Also update the comment at lines 646-661, which currently frames this as "finishing in-flight
work" — replace with a short note (or a pointer to the review doc) that this is a proximity heuristic
between a fleet-level `desired`-drop and this pod's own last sample, not a verified per-pod drain
signal.

[↑ TOC](#toc)

## What NOT to change {#not-to-change}

- `pod_drain_windows()` in `extract_real_trace.py` — window boundaries are unchanged; only the
  rendered label/comment changes (Item W).
- Draining's own hatch (`'....'`) and color treatment — unchanged, only waiting's hatch character
  changes (Item R).
- The detailed weak-time-anchor explanation text already in `warns`/`foot` — unchanged content,
  only the suptitle placement moves (Item U).
- Panel 4, panel 5 — untouched, not part of this spec (Item S remains parked, no code here).

[↑ TOC](#toc)

## Verification {#verification}

- Re-render `m-satta-dwell` (has both drain windows and waiting bands) and `m-ta-prefill-knee` (the
  weak-time-anchor sample) fresh against the coder's own tip; confirm stamp match (`coverage.json`
  `extractor_sha`/`render_sha` and the PNG's own embedded metadata) before reporting ready.
- Item R: confirm waiting's hatch reads as diagonal lines, visually distinct from draining's dots,
  at normal viewing size on the `m-satta-dwell` render.
- Item T: confirm panel 6's y-axis reads "replica-delta" and at least one reason-code label (e.g.
  P1-obs) appears annotated directly on the plot at its first occurrence, not only in the text key.
- Item U: confirm the suptitle no longer contains "WEAK TIME ANCHOR" on the `m-ta-prefill-knee`
  render, and the footer's first line does.
- Item W: confirm the panel 3 legend no longer says "finishing in-flight work" anywhere.
- Item Q: confirm panel 1b's corner text shows two numbers (mean and std), not one.
- Report back via a `plan__` handoff with the exact render paths and confirmed stamps, per the usual
  protocol — do not mark anything push-ready without Dean's review of the actual rendered output.

[↑ TOC](#toc)
