# Warmup-anchored x-axis + panel 3/4/6 polish round 2 — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 2. Source: Dean's direct review of the two real-campaign renders (`m-satta-dwell-tworuns-0aade22f.png`,
`m-sat-dwell-warmup-tworuns-0aade22f.png`), 2026-08-16. Two independent threads: (A) a real
correctness fix — the x-axis anchor should start at warmup-end, not run-start, for warmup-tagged
runs — and (B) a batch of panel 3/4/6 visual requests, all confirmed against current code before
writing this spec.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Item X — anchor x=0 at warmup-end, not run-start {#item-x-anchor}](#item-x--anchor-x0-at-warmup-end-not-run-start-item-x-anchor) L25:60
- [Item Y — panel 6: mild log scale with signed negatives {#item-y-panel6-log}](#item-y--panel-6-mild-log-scale-with-signed-negatives-item-y-panel6-log) L61:88
- [Item Z — panel 4: move mean-KV legend off the colorbar {#item-z-panel4-legend}](#item-z--panel-4-move-mean-kv-legend-off-the-colorbar-item-z-panel4-legend) L89:101
- [Item AA — panel 3: mean-running line color + secondary-axis direction {#item-aa-panel3-color}](#item-aa--panel-3-mean-running-line-color--secondary-axis-direction-item-aa-panel3-color) L102:119
- [Item AB — panel 3: sort pods by scale-up order {#item-ab-panel3-sort}](#item-ab--panel-3-sort-pods-by-scale-up-order-item-ab-panel3-sort) L120:148
- [Item AC — panel 3: add a per-pod color legend strip {#item-ac-panel3-colorlegend}](#item-ac--panel-3-add-a-per-pod-color-legend-strip-item-ac-panel3-colorlegend) L149:179
- [Item AD — extractor: fall back to `per_request_estimated.json` when the real trace is absent {#item-ad-estimated-fallback}](#item-ad--extractor-fall-back-to-perrequestestimatedjson-when-the-real-trace-is-absent-item-ad-estimated-fallback) L180:206
- [What NOT to change {#not-to-change}](#what-not-to-change-not-to-change) L207:218
- [Verification {#verification}](#verification-verification) L219:253

## Item X — anchor x=0 at warmup-end, not run-start {#item-x-anchor}

Dean: "seconds since start should be anchored on the end of the warmup (that is '0'), not start of
test." Confirmed mechanism: `*-warmup` workload profiles (e.g.
`hack/benchmark/workloads/inference-perf/ta_autoscale_dwell_warmup.yaml.in`) prepend a warmup stage
as `load.stages[0]` with a **fixed, known duration** (270s for the dwell-warmup profile, confirmed
in that file's own header and `load.stages[0].duration`). This is the "go with the YAML" option
Dean confirmed over inferring the boundary from per-request stage tags (which aren't available on
most runs anyway, since per-request collection stays disabled).

**Mechanism:** the extractor (`extract_real_trace.py`) needs to read the resolved workload YAML
(already copied into each run's results leaf, e.g.
`results/<leaf>/ta_autoscale_dwell_warmup.yaml`) and sum the `duration` of however many leading
stages are the warmup — for now, that's unambiguously **stage 0 only**, on **`*_warmup.yaml`-named
profiles only** (a run using the plain, non-warmup profile has no warmup stage and its anchor stays
at run-start, unchanged). Store the resulting offset (seconds) in the bundle's `meta` block, e.g.
`meta['warmup_offset_s']` — default `0` for non-warmup runs so `render_real_trace.py` doesn't need
a separate has-warmup branch, just always subtracts `meta.get('warmup_offset_s', 0)` in addition to
`t0` wherever it currently computes `rel(t, t0)`.

**Renderer side:** every panel's x-axis already computes elapsed time as `t - t0` (or via the
existing `rel()` helper) — locate every such site and route it through the new offset so `x=0`
lands at warmup-end consistently across all panels, not just some. The warmup interval itself
(`[t0, t0+warmup_offset_s]`, i.e. negative x) should still render — Dean's own framing was "so we
can see 0 sec decision markers," implying the pre-zero interval stays visible, just renumbered
negative, not clipped.

**Explicitly not required by this item** (per Dean's own TODOs, not scoped here):
- **TODO 1 (verify, not now):** whether 270s is actually enough for the system to stabilize before
  warmup ends — that's an empirical question for a future check, not something this spec resolves.
- **TODO 2 (design before doing):** forcing replica count up to an estimated target at the start of
  high-load-start workloads instead of warming up from 0 — a distinct, bigger design question,
  explicitly not scoped here.

**Real pre-existing bug found and fixed along the way, committed `deaf4886`.** `find_workload_yaml()`
was matching inference-perf's own `config.yaml` (a fixed harness-dumped filename, same `model_name`
and same `load.stages` content as the real profile) *before* the actual profile file, since
`config.yaml` sorts alphabetically first — silently defeating the new `_warmup` filename check on any
run where both files exist. Confirmed on `dean-20260816-121254-238`: returned `warmup_offset_s=0.0`
when it should have been `270.0`. Fixed by excluding `config.yaml` explicitly, same way
`run_metadata.yaml` was already excluded. Both `dean-20260816-121254-238` (warmup) and
`dean-20260813-005321-943` (non-warmup) re-extracted+re-rendered fresh against the fix; non-warmup
run's x-axis confirmed bit-for-bit unchanged (offset stays 0.0).

[↑ TOC](#toc)

## Item Y — panel 6: mild log scale with signed negatives {#item-y-panel6-log}

Dean: "panel 6 should use mild log scale (log 2?) + negatives as -log(|x|)." Panel 6
(`render_real_trace.py:1095`'s `g.plot(...)`) currently plots `replica-delta` on a plain linear
y-axis. Change to a **signed log transform**: for `y >= 0`, plot `log2(1 + y)` (the `+1` avoids
`log2(0)` blowing up at exactly zero); for `y < 0`, plot `-log2(1 + |y|)`. This compresses the large
excursions (e.g. the `+11` throughput spike seen in the `m-satta-dwell` render) without losing sign
or collapsing small values near zero to indistinguishable clutter. **Y-axis tick labels must show
the real (untransformed) replica-delta values**, not the transformed ones — use a custom
`FuncFormatter` (or matplotlib's own `symlog` scale with `linthresh` tuned to taste, if that reads
equivalently once rendered — coder's call which mechanism, but the requirement is real-valued tick
labels either way) so a reader sees "±2, ±4, ±8..." not "±1, ±2, ±3" (the log-space numbers).

**Addendum, folded in per Dean's fold-in decision:** the coder's own verification of the
extract-render-two-real-runs task (`plan__autoscaling-viz-extract-render-two-real-runs-done.md`)
flagged a fresh cosmetic defect on the `m-satta-dwell` render: a `T2-default` marker-legend
annotation lands directly on top of panel 6's own title text ("6 · signed replica-delta per
analyzer") near x≈0-50s, because the underlying data point is very early and the label's vertical
offset doesn't account for the title's position at that x-range. Fix as part of this same item
since it touches the same panel-6 annotation code the log-scale change already modifies — adjust
the offset/placement for labels landing in the title's x/y region, same general approach as the
existing overlap fix from the prior round (Item 6,
`autoscaling-viz-panel-review-20260815-fixes-plan.md`) staggered onto alternating positions when
two labels are close; extend that same logic (or a similar one) to also avoid the title's own
bounding box, not just other labels.

[↑ TOC](#toc)

## Item Z — panel 4: move mean-KV legend off the colorbar {#item-z-panel4-legend}

Dean: "need to move the legend so it is not hidden behind the heatmap indicator." Confirmed:
`e2.legend(loc='upper right', ...)` (~line 959) places the mean-KV-line legend box in the same
corner where the colorbar (added immediately after, `fig.colorbar(..., ax=e, ...)`) ends up sitting
— the two visually collide. Move the legend to a location that doesn't compete with the colorbar —
e.g. `loc='upper left'` if that's clear of the heatmap's own high-KV (red) region on typical runs,
or place it below the panel via `bbox_to_anchor`. Coder's judgment on exact placement; the
requirement is simply that the legend box and the colorbar don't overlap once rendered — verify by
viewing the actual PNG, not just by reading the code, per this file's own established practice.

[↑ TOC](#toc)

## Item AA — panel 3: mean-running line color + secondary-axis direction {#item-aa-panel3-color}

Two related requests on the running-count average line added in the prior follow-up round
(`autoscaling-viz-panel4-heatmap-followup-plan.md` Item 4, currently solid red):

1. **Color: yellow, not red/same-family as other panel-3 content.** Dean: "mean running should be
   yellow, not same color as total in system. confusing since using same units but different
   scale." Change the line's color to a yellow (e.g. `#eab308` or similar — coder's exact shade
   choice, avoid clashing with the gold/amber outlier-marker color already used on panel 4 if that
   would read as the same signal in a different panel).
2. **Consider reversing the secondary y-axis** so it draws top-down from 0. Dean: "may be reverse
   the secondary Y-axis -- draw line from top=0 down." This is explicitly floated as a "maybe," not
   a firm requirement — try it (`ax.invert_yaxis()` on the secondary axis) and judge by the actual
   render whether it reads more clearly than the current bottom-up orientation; if it doesn't
   obviously help, it's fine to leave the axis as-is and note that in the verification report.

**Outcome (committed `deaf4886`).** Tried and kept — reads more clearly against the stacked bars
than the original bottom-up orientation. This is a judgment call, not a settled design decision:
flagged for Dean to confirm rather than treated as final, per the "maybe" framing above.

[↑ TOC](#toc)

## Item AB — panel 3: sort pods by scale-up order {#item-ab-panel3-sort}

Dean: "pod sort order should be scale order (as in p4). older always on bottom." Panel 4 already
sorts pods by first-appearance time (`e_ordered = sorted(pods.items(), key=lambda kv: min(s['t']
for s in kv[1]['series'], default=float('inf')))`, ~line 864). **Apply the same ordering to panel
3's stacking order** — currently `ordered = sorted(pods.items())` (~line 623, alphabetical by pod
name). Change to the same first-appearance-time key panel 4 uses.

**"Older always on bottom"** — since panel 3 stacks bars (unlike panel 4's independent rows), this
means the earliest-appearing pod's band should be the bottom-most segment of the stack, and the
most-recently-appeared pod's band should be the top-most segment, at every x where multiple pods
are live. Implement by reordering the `ordered` list itself (earliest first), then building the
stack in that order — the existing `bottom` accumulator logic naturally puts whichever pod is
processed first at the bottom, so this should fall out of the reorder without restructuring the
stacking loop itself.

**This changes `pod_num` too** — since `pod_num` is currently derived from this same `ordered`
list (`pod_num = {pod: i + 1 for i, (pod, _p) in enumerate(ordered)}`, ~line 624), reordering
`ordered` automatically renumbers `pod_num` to match scale-up order. **This is a deliberate
consequence, not a side effect to avoid** — Dean's ask is consistency with panel 4's ordering, and
panel 4's row *labels* already show `pod_num` (per the prior round's spec, which said "keep
pod_num itself untouched" — that constraint was scoped to *that* round, when panel 3 was still
alphabetical; it does not survive once panel 3 itself moves to scale-up order, since at that point
there's only one ordering to be consistent with, not two). Confirm this reasoning holds once
rendered — if pod_num renumbering breaks some other reference to pod_num elsewhere in the file,
flag it rather than silently working around it.

[↑ TOC](#toc)

## Item AC — panel 3: add a per-pod color legend strip {#item-ac-panel3-colorlegend}

Dean: "can we have a color legend on the right (like we have for p4) — one 100% height bar, pods in
arrival scale up order, max/pod# area per pod." Add a vertical strip on panel 3's right edge (same
general position as panel 4's colorbar) showing one colored segment per pod, stacked in scale-up
order (top-to-bottom or bottom-to-top — match whatever Item AB establishes as panel 3's own stack
direction, for visual consistency between the main plot and this legend), each segment colored with
that pod's `BAND_SHADES` color (the same per-pod color already used in the stack itself) and sized
proportionally to that pod's own peak running-count. Label each segment with its `pod_num`.

**Correction, 2026-08-16 (post-implementation, amending the original spec — not a defect in the
first pass, which correctly implemented what was originally written).** Dean's exact correction:
"best number per pod is the maximal value ever seen on a not saturated pod (otherwise includes bad
pods that can look too big and the value itself does not have much meaning for over saturated
pods)." **Exclude any running-count sample taken while that pod's own `kv` (KV cache usage,
`vllm:kv_cache_usage_perc`, the same real, directly-scraped value — confirmed NOT an estimate or a
TA-derived calculation — already used by panel 4's heatmap) was at or above `k_sat`
(`sat.get('threshold')`, the same threshold panel 4's color scale already anchors on) when
computing `peak_run[pod]`.** A pod that spent time saturated should have its peak taken only from
its own non-saturated samples; if a pod has no non-saturated samples at all, its peak is 0 (coder's
call whether to render a zero-height segment or omit the pod from the strip entirely — either is
acceptable, just don't crash or silently substitute a saturated-sample value).

**Original commit's implementation is out of date against this correction** — the round-2 spec's
own `peak_run[pod] = max(run_ys)` (unconditional over all samples) needs to become conditional on
that same pod's `kv` at each sample's own timestamp. This is a follow-up amendment, not a re-review
of the already-verified original behavior (which correctly matched what this doc said before this
correction was added).

**Outcome, committed `a1a815a7`.** Reuses the same `sat.get('threshold') or SAT` fallback panel 4's
heatmap already anchors on, so both panels agree on one threshold value. **Measured real effect on
the warmup run: 5 pods' peaks drop substantially** once saturated samples are excluded (one pod
411→238, another 196→29) — confirms the correction addresses a real, not hypothetical, distortion.

[↑ TOC](#toc)

## Item AD — extractor: fall back to `per_request_estimated.json` when the real trace is absent {#item-ad-estimated-fallback}

Separately flagged by Dean while reviewing panels 1a/1b: both real-campaign renders show "no
per-request trace in this bundle" even though `dean-20260813-005321-943` actually has
`results/<leaf>/metrics/processed/per_request_estimated.json` — produced by `benchmark` scope's own
estimation tool (`hack/benchmark/estimate_per_request.py`, per
`plan__per-request-estimation-built-two-findings.md`). The extractor only checks for
`per_request_lifecycle_metrics.json` or `results.json` (`extract_real_trace.py:550-566`) — it has
no path that reads the estimated-fallback file at all.

**Add a third fallback tier:** if neither real-trace filename exists, check for
`metrics/processed/per_request_estimated.json` in the results leaf and use it if present. **Every
panel/field derived from this data must be visibly labeled as estimated, not measured** — e.g. the
existing "no per-request trace" placeholder text becomes something like "per-request data is
ESTIMATED (see docs), not measured" rather than either silently treating it as real or continuing
to say nothing is available. Do not remove the real-trace path or change its behavior when a real
trace exists — this is purely an additional fallback for when it's absent.

**Known caveats to carry into the labeling, not to re-litigate here:** the estimation tool's own
handoff documents two open findings on this exact file for this exact run — stage 0 has zero
requests (Envoy trace truncated at the window start) and stage 4 shows an unexplained 58%
rate-anomaly. Whatever label/caveat text this item adds should be able to accommodate those
per-run caveats if the bundle's own coverage checks want to surface them later — not scoped to
build that surfacing now, just don't paint yourself into a corner that makes it hard to add.

**Outcome, committed `deaf4886`.** `read_per_request_estimated()` maps the estimation tool's schema
(`arrival_epoch`/`e2e_duration_ms`/`outcome` real, `ttft_estimated_ms`/`output_tokens_estimated`
estimated) onto the same record shape `read_guidellm`/`read_inference_perf` already produce, so every
downstream panel needs no branching except a labeling flag (`meta.per_request_estimated`). Timestamps
are already real epoch (like guidellm), so the inference-perf monotonic-clock anchor step is correctly
skipped for this path too. **Measured impact on `dean-20260813-005321-943`: coverage jumped from
9 PASS/7 FAIL to 12 PASS/4 FAIL** — panels 1a/1b (previously blank "no per-request trace" placeholders)
and panel 3's TTFT title now show real content, all visibly labeled ESTIMATED (a corner annotation on
1a, a title suffix on 1b/panel 3's TTFT line) rather than either silently treated as measured or left
blank.

[↑ TOC](#toc)

## What NOT to change {#not-to-change}

- Panel 3's hatch styles (diagonal waiting, dotted draining) — Dean confirmed these are "now great,
  keep" — no changes.
- Panel 4's own row ordering, outlier marking, color scale anchor — untouched, already correct.
- `pod_drain_windows()` in `extract_real_trace.py` — unrelated to this spec.
- Item X's anchor logic must not affect non-warmup runs' x-axis at all — verify a non-warmup bundle
  (e.g. `m-satta-dwell`, no `_warmup` in its workload name) renders identically to before this
  change.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render `m-sat-dwell-warmup` (`dean-20260816-121254-238` or similar) fresh; confirm x=0 now
  lands ~270s after the old anchor, and negative-x data (the warmup interval) is visible, not
  clipped.
- Re-render a non-warmup run (e.g. `m-satta-dwell`) fresh; confirm its x-axis is unchanged from
  before this spec (anchor stays at run-start).
- Item Y: confirm panel 6's y-axis shows real replica-delta values on its ticks, and that a large
  excursion (if present in the test run) reads as visibly compressed relative to small values, not
  linearly scaled. Also confirm the `T2-default`-on-title collision from the two-real-runs render
  is fixed — re-render `m-satta-dwell` specifically (the run it was found on) and check the same
  x≈0-50s region.
- Item Z: confirm panel 4's mean-KV legend and colorbar no longer overlap.
- Item AA: confirm panel 3's mean-running line is yellow; note in the report whether the
  axis-reversal experiment was tried and whether it was kept.
- Item AB: confirm panel 3's stack order now matches panel 4's row order (same pod at the bottom of
  panel 3's stack as at the top row of panel 4, or whichever correspondence the "older always on
  bottom" + panel-4-row-0-is-earliest convention implies — check both panels side by side on the
  same render).
- Item AC: confirm the new per-pod legend strip renders on panel 3's right edge without colliding
  with the existing panel 3 legend box or KV-ceiling secondary axis.
- Item AD: re-extract `dean-20260813-005321-943` specifically (the run with the real
  `per_request_estimated.json` file) and confirm panels 1a/1b now show estimated data with a
  visible "estimated, not measured" label, rather than the "no per-request trace" placeholder.
  Also re-extract a run with genuinely no per-request data of any kind (e.g. most `*-dwell-warmup`
  runs) and confirm they still correctly show the placeholder — this fallback must not fire when
  there's truly nothing to fall back to.
- Report back via a `plan__` handoff with exact render paths and confirmed stamps, per the usual
  protocol — do not mark push-ready without Dean's review of the actual rendered output. This spec
  bundles a real anchor-logic change (Item X) and a real extractor-fallback change (Item AD) — both
  touch `extract_real_trace.py` — with pure rendering polish (Items Y/Z/AA/AB/AC) in
  `render_real_trace.py` only. Call out Items X and AD's verification separately in the report
  since they're the two items with actual correctness risk, not just visual tuning.

[↑ TOC](#toc)
