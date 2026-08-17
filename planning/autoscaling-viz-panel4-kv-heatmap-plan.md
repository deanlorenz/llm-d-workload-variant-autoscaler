# Panel 4 repurpose: per-pod KV% heatmap + panel 3 running-average line — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 2 / Item S. Source: live discussion 2026-08-16, following up on the panel-review-20260815
Item S feedback (panel 4 redesign). Retires panel 4's current queue-sources content; repurposes the
slot for per-pod KV% — the one already-extracted per-pod metric (`kv`, in every pod's `series`) that
no panel currently shows. Also folds in a small, separately-noted panel 3 gap (missing running-count
average line), per Dean's explicit fold-in decision.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Why panel 4 is being retired {#why-retire}](#why-panel-4-is-being-retired-why-retire) L21:43
- [New panel 4: per-pod KV% heatmap {#new-panel4}](#new-panel-4-per-pod-kv-heatmap-new-panel4) L44:91
- [Panel 3: add running-count average line {#panel3-avg}](#panel-3-add-running-count-average-line-panel3-avg) L92:102
- [What NOT to change {#not-to-change}](#what-not-to-change-not-to-change) L103:116
- [Verification {#verification}](#verification-verification) L117:136

## Why panel 4 is being retired {#why-retire}

Checked against real data before deciding, not just on feel:

- Panel 4's series (b) (EPP dispatch, "everything in the system") and panel 5's `L(t)` (requests in
  system) are the same underlying quantity, drawn twice — confirmed visually identical shape/peak on
  both the `m-satta-dwell` and `m-ta-prefill-knee` fresh renders.
- Panel 4's series (c) (engine `num_requests_waiting` summed across pods) duplicates panel 3's own
  per-pod waiting stack, just pre-summed.
- Panel 4's series (a) (derived flow-control, `in-system − dispatch`) is the one series unique to
  panel 4, and it can't carry real signal: **entirely absent** on `m-satta-dwell` (0 of 141 system
  samples have `in_system` populated at all — that run has no per-request trace) and **present but
  negligible** on `m-ta-prefill-knee`, the one run that does have per-request data (65 of 1041
  samples, max value 11, against a y-axis that runs to ~2000).
- Panel 5 already provides the useful context panel 4 lacked (a capacity ceiling, and the
  served/queued split as shading) — so nothing panel 4 uniquely contributed survives this check.

**Delete panel 4's current drawing code and INTERIM title/todo text entirely** — do not keep it
behind a flag or comment it out. This is a full retirement, not a deprecation-in-place; the new
content below takes the same axes slot.

[↑ TOC](#toc)

## New panel 4: per-pod KV% heatmap {#new-panel4}

**Data:** each pod's `series` already carries a `kv` field (fraction, 0.0-1.0) at every sample —
confirmed present in the bundle today (`extract_real_trace.py`'s `GAUGE['kv'] =
'vllm:kv_cache_usage_perc'`), nothing new to extract.

**Layout:** one horizontal row per pod, stacked in pod-number order (reuse the existing `pod_num`
numbering from panel 3, so pod 1 is the same physical pod in both panels). Each row is a heatmap
strip: color at time `t` = that pod's `kv` value via the color scale below. Use
`imshow`/`pcolormesh` (whichever fits this file's existing matplotlib usage better — check what's
already imported) rather than one `bar` call per sample; this is a genuinely different draw
primitive from every other panel in this file, not a variation on the existing per-pod bar-stack
pattern.

**Color scale, anchored at the saturation threshold, not a plain linear [0,1]:** this run's real KV%
distribution is heavily skewed low (median 0.08, p90 0.20 on `m-satta-dwell`) while the
scaling-relevant threshold sits at `sat.get('threshold')` (already computed by `extract_real_trace.py`
and available via `der.get('sat_band')` — see line 269's existing `sat = der.get('sat_band') or {}`,
default `SAT = 0.85`). Build a two-segment colormap: white → green over `[0, threshold)`, green →
red over `[threshold, 1.0]`, so pods crossing the actual scaling threshold visibly change color
character (not just get "more of the same" color), matching Dean's own "100% is red, 0% is white,
30% is green" framing but keyed to this run's real threshold rather than a fixed 30% waypoint — 30%
was illustrative, not a literal requirement (confirm this reading with Dean if in doubt, but the
explicit ask was to anchor at `k_sat`, and 30% was said before that decision was made).

**Latent bug found and fixed later, committed `0aade22f` (a separate follow-up session, caught via
internal review, not by this spec's own verification).** `render_real_trace.py:874`'s
`k_sat = sat.get('threshold') or SAT` referenced a name (`SAT`) never defined anywhere in the file —
found via an AST walk of top-level assignments, not just a grep. Never fired on any run tried so far
because `extract_real_trace.py`'s own `sat_band()` unconditionally sets `'threshold': SAT` (0.85) in
both return branches, so the `or SAT` branch was dead but not safely dead — any future bundle that
ever omits the key would crash. Fixed by adding `SAT = 0.85` as a local module constant in
`render_real_trace.py` (not an import of the extractor's own constant, since this file is designed to
run standalone against just a `bundle.json`). Verified both directions: reproduced the exact
`NameError` on the prior commit with a synthetically null-`threshold` bundle, then confirmed the same
input renders clean after the fix.

**Pods with no data at time `t`** (not yet live, or already dead — same ambiguity Item W already
established can't be resolved from this data): render as a distinct neutral fill (e.g. a light gray,
not white) so a dead/not-yet-live pod is visually distinguishable from a live pod at genuinely 0% KV.
Do not silently render these as white — that's already claimed by "0% KV, definitely live."

**Average line:** a thin overlaid line (not its own heatmap row) tracing the mean `kv` across
currently-live pods at each `t`, drawn in a neutral ink color (e.g. `INK`, consistent with this
file's convention elsewhere) on top of the heatmap. Needs its own small secondary y-axis or a
fixed-height overlay strip since the heatmap rows don't have a numeric y-axis in the traditional
sense — coder's judgment on the cleanest way to overlay a line plot on an `imshow` grid; a twin axes
(`ax.twinx()` is already used elsewhere in this file for panel 3's KV-ceiling secondary axis, per
Task 2 — reuse that pattern if it fits) is one reasonable approach.

**Outlier marking:** for now, mark any pod whose `kv` at time `t` exceeds the live-pod average by
more than one population stdev with a thin border/hatch on that cell. This exact rule is provisional
— Dean asked to "somehow mark outliers" without specifying the rule; implement this as a first pass,
flag it as tunable in a comment, and expect it may need adjusting once seen rendered.

**Colorbar:** include a colorbar or a compact scale legend so the white→green→red mapping and the
threshold anchor point are readable without cross-referencing this doc.

[↑ TOC](#toc)

## Panel 3: add running-count average line {#panel3-avg}

Separately noted gap, folded into this spec per Dean's explicit decision (small, related — both are
"per-pod average" additions). Panel 3 currently stacks per-pod running/draining/waiting bars but has
no line showing the average running-count across live pods at each `t`. Add one, in the same style
as whatever overlay convention panel 3 already uses for its other reference lines (e.g. the
KV-ceiling secondary-axis line from Task 2) — thin, clearly secondary to the stacked bars, not
competing with them visually.

[↑ TOC](#toc)

## What NOT to change {#not-to-change}

- Panel 5 — untouched; it's the reason panel 4's redundant content is being retired, not itself
  being modified.
- `pod_drain_windows()` / Item W's relabeled legend text — untouched, unrelated to this spec.
- Panel 3's existing running/draining/waiting stack, hatches, colors — unchanged; only a new average
  line is added on top.
- GPS/PPS per-pod — explicitly out of scope. No such metric is currently extracted anywhere in this
  codebase (confirmed: `benchmark/`'s own tooling only computes gateway-level, not per-pod,
  throughput). Building that extraction is a separate, unscoped future item if ever needed — this
  spec covers KV% only, which already exists in the bundle today.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render `m-satta-dwell` (15 pods, real KV activity ranging 0.0-1.0, good stress test for the
  color scale and outlier marking) and confirm the heatmap is readable at normal viewing size — not
  just correct in isolation.
- Confirm the color transition at `sat.get('threshold')` (0.85 on this run, unless the bundle's own
  `sat_band` says otherwise) is visually distinct from both the low-KV white/green region and the
  high-KV red region — view the actual render, don't just check the colormap function in isolation.
- Confirm dead/not-yet-live pods render distinguishably from genuinely-0%-KV live pods.
- Confirm the average line and at least one marked outlier (if this run has one) are both visible
  without obscuring the heatmap.
- Confirm panel 3's new running-average line doesn't visually compete with the existing stacked bars
  or the KV-ceiling secondary axis.
- Report back via a `plan__` handoff with exact render paths and confirmed stamps, per the usual
  protocol — do not mark push-ready without Dean's review of the actual rendered output. This is a
  genuinely new visual (no existing convention to fall back on, confirmed via a scope-boundary check
  against `benchmark/`'s own tooling before writing this spec) — expect it may need a visual-tuning
  follow-up round, the same way Task 8's hatch work did.

[↑ TOC](#toc)
