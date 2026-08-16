# autoscaling-viz — ongoing code review

**Status:** DRAFT
**Scope:** running log, one dated section per commit/trigger reviewed. Cross-reference
[`autoscaling-viz-review-20260813.md`](autoscaling-viz-review-20260813.md) for the earlier batch
(`037106f2`, `fbecfe26`+`08927557`) — not repeated here.
**Reviewer:** background review agent, this session.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [2026-08-13 — panel 6 redesign (`3f12aaa1`) {#session-2026-08-13-panel6}](#2026-08-13--panel-6-redesign-3f12aaa1-session-2026-08-13-panel6) L22:76
- [2026-08-13 — drain-window fix (`e188d244`) {#session-2026-08-13-drain}](#2026-08-13--drain-window-fix-e188d244-session-2026-08-13-drain) L77:134
- [2026-08-13 — backlog rerun (`cf76a238`, no trigger) {#session-2026-08-13-backlog}](#2026-08-13--backlog-rerun-cf76a238-no-trigger-session-2026-08-13-backlog) L135:147
- [2026-08-14 — version-stamp renders, Part 1/1b (`870fff6d`, no trigger yet) {#session-2026-08-14-stamp}](#2026-08-14--version-stamp-renders-part-11b-870fff6d-no-trigger-yet-session-2026-08-14-stamp) L148:209
- [2026-08-15 — per-panel corner-info allocation (`062c1071`) {#session-2026-08-15-corner}](#2026-08-15--per-panel-corner-info-allocation-062c1071-session-2026-08-15-corner) L210:276
- [2026-08-15 — panel 3 visual scheme (`b7920cd3`) {#session-2026-08-15-panel3-visual}](#2026-08-15--panel-3-visual-scheme-b7920cd3-session-2026-08-15-panel3-visual) L277:353
- [2026-08-16 — panel 4 KV%-heatmap repurpose + visual follow-up (`0a2be3be` + `f92d3c19`) {#session-2026-08-16-kv-heatmap}](#2026-08-16--panel-4-kv-heatmap-repurpose--visual-follow-up-0a2be3be--f92d3c19-session-2026-08-16-kv-heatmap) L354:472

## 2026-08-13 — panel 6 redesign (`3f12aaa1`) {#session-2026-08-13-panel6}

**Trigger:** `review__autoscaling-viz-panel6-redesign-ready.md`. **Plan:**
[`autoscaling-viz-panel6-redesign-plan.md`](autoscaling-viz-panel6-redesign-plan.md).

**Verdict: push-ready. No findings.**

Diff (`extract_real_trace.py` +11/−0, `render_real_trace.py` +96/−35) matches the plan's Goal,
Panel design, and Keep sections point for point:

- Extractor: `by_analyzer` records extended additively with `rc`/`sc`/`prc`, existing
  `t`/`reason`/`variant` fields untouched — matches § extractor-gap exactly (additive, not
  replacing).
- Delta formula `(rc − sc) / prc`, algebraically identical to the commit message's stated
  `rc/prc − sc/prc`. **Independently verified the clamping claim** the sign argument rests on: read
  `applyUniversalThreshold` in `Main/internal/engines/saturation/engine_v2.go:482-519` myself —
  confirmed both `RequiredCapacity` and `SpareCapacity` (top-level and per-role) are independently
  clamped to `max(0, ...)` before being returned, so the difference is never sign-ambiguous, exactly
  as claimed.
- **Independently re-derived the two hand-verification cases from raw data**, not by trusting the
  commit message: extracted the real ticks from
  `benchmark/session-notes/campaign-runs/m-satta-dwell/controller.log`.
  - Scale-up tick (21:55:29Z, immediately preceding the 21:55:29 `scale-up curr=1→tgt=5` decision):
    throughput analyzer `rc=1203.31, sc=0, prc=387.76` → delta `= +3.10`. Positive, matches.
  - Scale-down tick (21:57:30Z, immediately preceding the 21:57:30 `scale-down curr=5→tgt=3`
    decision): saturation analyzer `rc=0, sc=1,193,693.57, prc=329,011` → delta `≈ −3.63`. Negative,
    matches.
  - (Used different exact ticks than the commit message's own examples, which cites
    `dean-20260810-092644-320` — same conclusion from an independent sample.)
- Panel design: signed y-axis with `axhline(0, ...)` zero line ✓; one line per analyzer with a fixed,
  non-categorical color set (`ANALYZER_COLORS`, distinct from `GP_COLORS`) ✓, matching the plan's
  explicit instruction not to reuse the categorical palette for a per-series identity; reason code
  demoted to a marker overlay with a compact text key rather than a second legend column ✓, citing
  panel 3's own legend-density lesson as precedent (real prior finding, correctly generalized rather
  than rediscovered).
- Absent-vs-reporting handling: `is_absent_lane = absent_t is not None and name == 'saturation'` —
  confirmed this hardcoding is *correct*, not a shortcut: `saturation_absent_at` is itself a
  saturation-only signal in the extractor (`extract_real_trace.py:1378`, only key of that name, no
  generic per-analyzer equivalent exists), so the redesign is faithfully continuing the existing
  scope, not introducing a new limitation.
- Kept-unchanged items (analyzer-absent annotation, `empty()` degrade path, shared `axvline` loop,
  panel's grid slot) — diff shows the annotation logic simplified from two placement branches to one
  (correctly, per the commit message's own reasoning: no more per-analyzer lanes to distinguish
  between) and the `empty()` call and `axvline` reliance are untouched in the diff.

**Not independently re-rendered** — attempted to reproduce on the same `m-satta-dwell` campaign
data via `extract_real_trace.py --no-per-request --controller-log ...` + `render_real_trace.py`, but
the available copy of that run under `benchmark/session-notes/campaign-runs/` lacks the per-request
metrics needed for the renderer's earlier panels to build at all (`bundle has no time series at all`
— render aborts before reaching panel 6). Substituted a from-scratch hand-verification of the sign
against raw `controller.log` ticks (above), which is the same check the plan's own § Verification
asks for and is independent of trusting the coder's stated numbers.

[↑ TOC](#toc)

## 2026-08-13 — drain-window fix (`e188d244`) {#session-2026-08-13-drain}

**Trigger:** `review__autoscaling-viz-drain-window-fix-ready.md`. **Plan:**
[`autoscaling-viz-drain-window-fix-plan.md`](autoscaling-viz-drain-window-fix-plan.md).

**Verdict: push-ready. No findings.**

Diff (`extract_real_trace.py` +43/−7, one function: `pod_drain_windows`) traced line by line against
the final code:

- New `desired_drops` list (sorted timestamps of every `desired` step-down in `replicas`) is computed
  once, matches the plan's step 1 ("find the desired step-down...").
- Per-pod: `earlier_drops = [t for t in desired_drops if t <= last_t]` filters by the **pod's own**
  last sample, not the matched drain event's timestamp — this is the documented second-attempt fix,
  and the commit message's account of *why* the first attempt (filtering by `<=` the drain event
  instead) regressed 11 windows on `m-satta-dwell` is internally consistent with the code: the
  aggregate `ready`-poll cadence is coarser than the per-pod scrape (already documented in the
  function's pre-existing docstring, unchanged by this diff), so a drain event's own timestamp can
  sit up to `DRAIN_MATCH_WINDOW_S` after a pod's last sample — filtering by that timestamp instead of
  `last_t` would admit a desired-drop the pod's own data never lived to see, over-clipping short,
  correct windows to nothing. Traced this exactly; the fix's ordering (`<= last_t` vs `<= nearest`)
  is the load-bearing line and it is the one actually in the diff.
- Fallback: `bound = earlier_drops[-1] if earlier_drops else min(nearest, last_t)` — hand-traced the
  r2tnh case (the one the plan names as ground truth): `nearest` (matched drain event) lands *after*
  `last_t` there (drop at t≈1073s, pod's last sample at t≈1058s), so `earlier_drops` is empty,
  `bound = min(1073, 1058) = 1058 = last_t`, then `t_start = max(t_start, 1058) = 1058`, which trips
  the `if t_start >= last_t: continue` guard and drops the window entirely. This is exactly what the
  trigger note flags as "not a deviation, but worth confirming independently" — **confirmed
  independently from the code, not from the trigger's own characterization**: the spec's step-3
  fallback ("if the clipped window is empty or negative-length, drop it entirely") fires correctly
  here, and a nonzero window for r2tnh would require inventing data the pod's own samples don't
  contain. The plan's § Verification wording ("the fixed window should start close to t≈1073s") reads
  as if a nonzero window survives; it doesn't, for the reason above — this is the spec's own logic
  applied correctly to data that happens to make the fallback's zero-case fire, not the plan's
  literal wording being satisfied. Worth flagging to whoever owns the plan doc next: the verification
  wording is now slightly stale relative to what the fix actually produces on the named ground-truth
  case, though the *underlying* behavior is correct.
- Call site update (`pod_drain_windows(pods, lag.get('drain_events'), run_end_t, replicas)`) is a
  pure signature extension, no other call sites exist in this file.

**Not independently re-rendered.** Same data-availability gap as the panel-6 commit above: the
`m-ta-staircase` and `m-satta-dwell` copies under `benchmark/session-notes/campaign-runs/` carry only
`controller.log`, not the per-pod metrics scrape (`pods`/`replica_status_timeseries.json`) that
`pod_drain_windows` actually consumes; a fuller run directory located for `m-ta-staircase`
(`benchmark/runs/dean-20260810-084756-739`) turned out to be a *different* run (no analyzer-result
lines, no matching drain event) rather than the one the coder verified against. Substituted a
full line-by-line trace of the diff against the commit message's own claims (above), which resolved
cleanly with no discrepancy found — the code does exactly what the message says, including both the
first-attempt failure mode and the second version's fix.

**Not a finding, but noted for the plan's owner (not the coder, and not this defect list — this is a
plan-doc-wording accuracy note):** § Verification's phrasing ("the fixed window should start close to
t≈1073s") should be corrected to describe the actual outcome (no window at all for r2tnh, per the
step-3 fallback) next time that plan doc is touched, so a future reader doesn't read the current
wording as unmet.

[↑ TOC](#toc)

## 2026-08-13 — backlog rerun (`cf76a238`, no trigger) {#session-2026-08-13-backlog}

**No trigger filed** (consistent — this commit is pure toolchain invocation, no code changed).
**Plan:** [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md) § Item 8.

Data-only commit (30 files, all under `session-notes/review-samples/backlog-rerun-20260813/`,
`bundle.json`/`coverage.json`/`panels.png` per run, +915/−0). No source file touched — nothing to
review for code correctness. Scope-checked against Item 8's own description (7 runs, one with 4
parallel result leaves handled as 4 separate outputs) — matches. Not entered as a reviewed
code-correctness item; recorded here only so the commit isn't silently absent from this log.

[↑ TOC](#toc)

## 2026-08-14 — version-stamp renders, Part 1/1b (`870fff6d`, no trigger yet) {#session-2026-08-14-stamp}

**No `review__` trigger filed at review time** — reviewed anyway, at the coordinator's request
(Dean actively asking what's reviewable; the coder likely holds the trigger until Part 2, the
21-run regen batch, also lands, per the plan's own "do this only after Part 1 lands" framing for
Part 2, not necessarily for filing review triggers). **Plan:**
[`autoscaling-viz-version-stamp-and-regen-plan.md`](autoscaling-viz-version-stamp-and-regen-plan.md)
§ Part 1 / Part 1b — Part 2 (the 21-run regen) is explicitly out of scope for this commit and not
reviewed here; revisit once it lands.

**Verdict: push-ready. One minor finding (non-blocking).**

Diff (`extract_real_trace.py` +22/−0, `render_real_trace.py` +43/−3) matches Part 1/1b closely:

- `git_sha()` helper duplicated once per file (extractor, renderer) rather than shared — the plan's
  own wording ("same approach, its own short SHA") explicitly allows this, not a defect.
- **Independently verified, live, on a real bundle** (`benchmark/runs/dean-20260810-092644-320/…/
  inference-perf-1786343242-zr01gi_1`, extracted and rendered fresh via the actual toolchain, output
  to `/tmp/`):
  - `coverage.json`'s `extractor_sha` (`870fff6d`) matches `git -C autoscaling-viz rev-parse
    --short HEAD` exactly, and `extracted_at` is a well-formed UTC ISO-8601 timestamp — satisfies
    the plan's own sanity-check bullet in § Verification.
  - Footer text on the rendered PNG carries `rendered @ 870fff6d, bundle extracted @ 870fff6d` per
    the terse-one-line design.
  - **PNG-embedded metadata confirmed present and complete on an orphaned copy** (copied the PNG to
    a scratch dir with no `coverage.json` sidecar present, per the plan's own verification
    instruction): `PIL.Image.open(...).info` returns all four fields —
    `extractor_sha`/`render_sha`/`source_run`/`extracted_at` — correct values, matching the sidecar.
    This is the exact check the plan's § Verification asks for, run for real rather than trusted
    from the commit message.
  - **Git-unavailable fallback confirmed independently**, not just taking the commit message's word
    for it: copied `extract_real_trace.py` alone into a directory with no `.git` and called
    `git_sha()` directly — returned `'unknown'`, no exception, matching the claimed degrade path.

**Finding 3 — `tight_layout`'s bottom-margin reservation is now always active, a side effect not
mentioned in the commit message.** `render_real_trace.py`'s `foot` string used to stay `''` (and
`fig.text(...)` was skipped, and `fig.tight_layout(rect=(0, 0.022 if foot else 0, 1, 0.985))` used
the full-height `0` branch) whenever a run had **zero** coverage-warning caveats and **zero**
coverage-row FAILs — confirmed by reading the pre-commit code at `e188d244:render_real_trace.py`
lines 883-894, which gated `fig.text(...)` behind `if foot:`. This commit appends the version-stamp
line to `foot` **unconditionally**, so `foot` is now always truthy — `fig.text(...)` always fires
(intended: every render should show the stamp) but `tight_layout`'s `rect` branch is now
permanently on its `0.022`-margin side too, since the `if foot: fig.text(...)` guard that used to
gate that decision is gone and `foot`'s emptiness is no longer possible. Net effect: a
run with a genuinely clean coverage report (rare — none of this branch's sample cells hit it, all
have at least one FAIL row) would previously get the full figure height for its 7 panels and now
always loses a thin bottom strip to the mandatory stamp line. This is very likely the **correct**
behavior (the stamp needs the margin to be legible, so reserving it unconditionally is arguably
what Part 1 intends), but it's an incidental behavior change the commit message doesn't call out or
verify, and the plan's own § Verification list doesn't ask for a clean-coverage-report render to be
spot-checked — so nobody has actually looked at whether a genuinely clean run's panel 7 still reads
correctly with the smaller usable height. Low priority, cosmetic at worst; worth a to-whoever-next-
touches-panel-layout note rather than a re-open.

**Not independently checked:** whether `identify -verbose` (ImageMagick) reads the same metadata as
`PIL.Image.info` — the plan's § Verification names both as acceptable checks; only the PIL path was
exercised here since ImageMagick wasn't confirmed available in this environment. Low-value gap —
PIL's read already confirms the tEXt chunk round-trips correctly, which is the substance of the
claim; a second reader tool would only add redundant confirmation of the same PNG mechanism.

[↑ TOC](#toc)

## 2026-08-15 — per-panel corner-info allocation (`062c1071`) {#session-2026-08-15-corner}

**Trigger:** `review__autoscaling-viz-corner-info-ready.md`. **Plan:**
[`autoscaling-viz-corner-info-plan.md`](autoscaling-viz-corner-info-plan.md).

**Verdict: push-ready. No blocking findings; one narrow pre-existing edge case noted, not
introduced by this commit.**

Diff (`render_real_trace.py` +85/−16, six panels) checked against the plan's own final placement
table point by point — all six rows land where the table says: 1a (% good), 1b (time per work
unit), 2 (tightened boot/scale-down + new drain-duration), 3 (TTFT percentiles, router imbalance
moved OUT), 4 (router imbalance moved IN), 5 (cost/utilization). Traced the two "not-to-do" items
too: the figure title is untouched, and panel 6 gets nothing added — both confirmed clean in the
diff.

**Rendered on two real bundles, not just read the diff:**

1. `benchmark/runs/dean-20260810-092644-320/…/inference-perf-1786343242-zr01gi_1` (no per-request
   trace — `per_request_lifecycle_metrics.json` is genuinely 0 bytes on this run, a pre-existing
   harness-capture gap, not caused by this commit). Confirms the degrade paths: panel 1a shows no
   "% good" text (per-request-gated, correctly silent), panel 3 shows `TTFT percentiles: n/a (no
   per-request trace)`, panel 5 shows only `replica-seconds=9561` with **no** utilization figure —
   traced why: `slots_g` requires `cap.get('max_conc_pred')`, which this run's own coverage report
   already flags as unavailable (`Capacity model checkable: pred=None`) — the omission is the
   correct behavior the commit message claims, not a bug.
   - **Independently re-derived `replica-seconds=9561` from the raw bundle** (`Σ (t[i+1]-t[i]) ·
     ready[i]` over `bundle['replicas']`, not trusting the rendered number or the commit message):
     got exactly **9561**. Also independently reconstructed the commit's own "rough unweighted
     estimate" cross-check (`mean(ready) × total_duration`): got exactly **9480**, matching both
     numbers the commit message cites verbatim. This was flagged by the coordinator specifically as
     worth re-deriving rather than trusting — done, on real data, both figures confirmed.
2. `benchmark/runs/dean-20260812-152105-714/…/inference-perf-1786537304-51sczw_1` (real
   per-request data, extracted with `--head 5000` to keep the multi-GB source file tractable — full
   un-headed extraction of this run's 2GB+ per-request file was attempted first and timed out at
   90s under this review's time budget; a 5000-row sample is enough to exercise every corner-info
   code path, just not a claim about this run's full-run numbers). All six additions populate:
   panel 1a `100% good (<30s)`, panel 1b `0.62s per 1000 tokens`, panel 2 `boot 84s mean/3`, panel 3
   `TTFT p50/p75/p90/p95 (ms): 125/259/443/705`, panel 4's router-imbalance text sits cleanly above
   the INTERIM note with no visual overlap (the `1.10 vs 1.02` transAxes y-offset split, gated on
   `drawn`, works as designed), panel 5 `replica-seconds=3654 utilization=18%` (both present this
   time — this run's capacity model is a coverage PASS).
   - **Independently re-derived `replica-seconds=3654`** the same way as run 1 — exact match.
   - **Independently re-derived `100% good (<30s)`** directly from the 5000-row per-request sample
     (`wait_band(r) <= 2` reduces to `ttft is None or ttft < 30` for non-error requests) — exact
     match, and consistent with panel 3's own TTFT p95 of 705ms on the same sample, well under the
     30s threshold.

**Note, not a finding against this commit — pre-existing behavior, checked because the new "%
good" corner metric is the first place it gets aggregated into one number a reader might trust at
face value:** `wait_band()` (unchanged by this diff) returns band 0 (the *best* band, "good") when
`r.get('ttft') is None`, i.e. a request with no recorded TTFT counts as "good" rather than
"unknown." Checked whether this is live on real data: across the 5000-row sample above, **zero**
non-error requests had `ttft is None` — so on the data actually exercised, this doesn't inflate
anything. But it's a real path that would silently overstate "% good" if a future run had
non-error requests with missing TTFT (e.g. a partial-capture gap), since panel 1a's bars already
show band-0 as a visibly small sliver a viewer can sanity-check, while the new single-number corner
metric has no such visual cross-check. Not asking for a re-open — flagging for whoever next touches
`wait_band()` or panel 1a.

**Not independently re-derived:** the `utilization=18%` figure on run 2 — would require
reconstructing the full `grid`/`hold()`/`served_g`/`slots_g` pipeline standalone rather than a
one-line formula; the zero/nonzero gating logic (whether the number appears at all) was traced and
confirmed correct instead, which is the part most likely to be wrong. Low-priority gap, not
re-opening for it.

[↑ TOC](#toc)

## 2026-08-15 — panel 3 visual scheme (`b7920cd3`) {#session-2026-08-15-panel3-visual}

**Trigger:** `review__autoscaling-viz-panel3-visual-scheme-ready.md`. **Plan:**
[`autoscaling-viz-panel3-visual-scheme-plan.md`](autoscaling-viz-panel3-visual-scheme-plan.md).

**Verdict: push-ready. No findings.**

Diff (`render_real_trace.py` +45/−12, one panel-3 block) checked against the plan's four numbered
changes plus its title-fix fold-in, point by point:

1. **Draining hatch lighter, dots kept.** Confirmed in source: `hatch='....'` unchanged, but now
   pairs `edgecolor=INK, linewidth=0.25` (was `edgecolor=C_ACT, linewidth=0.4`) with an explicit
   `bar.set_hatch_linewidth(0.3)` and `bar.set_hatchcolor('#f5f5f5')` per bar — two independent
   mechanisms (border vs. hatch stroke), both thinned, matching the commit message's own claim that
   both needed adjusting.
2. **Waiting → dashed-style, not diagonal.** `hatch='////'` replaced with `hatch='--'`.
   **Independently checked the API claim rather than trusting the commit message:** ran matplotlib
   3.11.1's `_hatch_types` and read `HorizontalHatch.__init__` source directly —
   `self.num_lines = int((hatch.count('-') + hatch.count('+')) * density)`, confirming `'-'` is a
   real, parsed hatch character producing horizontal lines. Also confirmed matplotlib has no literal
   dash-pattern hatch: the full char vocabulary across all 8 `_hatch_types` classes is
   `-,+,|,/,\,x,X,o,O,.,*` (commit message says `/,\,|,-,+,x,o,O,.,*` — omits `X`, a harmless
   under-statement, not a false claim). So the commit's own framing — "closest built-in to dashed
   lines, not a literal dash glyph, but a genuinely different primitive from draining's dots" — holds
   exactly as stated, verified against the interpreter's actual parsing, not the docs prose.
3. **Both overlays thinner overall.** Same `linewidth=0.25`/`set_hatch_linewidth(0.3)` pair applies
   to both bands (draining L664, waiting L704 in the post-commit file) — no asymmetry between them.
4. **Outline uniform across all three bands.** Grepped the post-commit source directly:
   running (L641), draining (L664), and waiting (L704) all read `edgecolor=INK, linewidth=0.25`,
   character-for-character identical. Confirms the claimed running 0.4→0.25 tightening and the
   draining `C_ACT`→`INK` edgecolor switch both landed, and that no band was left inconsistent.
   (Two other `linewidth=` sites elsewhere in the file — L555 at `0.0`, L941 at `0.3` — belong to
   different panels/contexts, untouched by this diff and correctly out of the plan's scope.)
5. **Title fix.** Source now reads `'3 · requests per pod: running, draining, waiting, EPP queue'`
   (was "...running, waiting, router-side"), matching the plan's fold-in instruction citing the
   earlier review's Finding 2 verbatim.

**Verified by rendering, not just reading the diff** — extracted and re-rendered two real bundles
into a scratch tmp dir (not the tracked worktree), matching the commit message's own two cited
verification runs:

1. **`m-satta-dwell`** (`benchmark/runs/dean-20260810-092644-320/results/inference-perf-1786343242-
   zr01gi_1`) — 15 pods, `Router imbalance measurable pods=15`, `Scale-down present drain_events=7`,
   i.e. a real multi-pod run with both draining and waiting material, matching the commit's "15 pods,
   real draining + waiting bands both present" claim. Viewed the full 6-panel render and several
   tight crops of panel 3 at up to 8x magnification. Panel title reads correctly. Every stacked
   segment — running, draining, waiting — carries a visibly thin, uniform dark outline; no band reads
   heavier than another. Found and visually confirmed at least one bar with a clean, legible white
   dot-grid hatch (draining) with good contrast against its teal fill — the exact defect the commit
   message says was caught and fixed (dark hatch color invisible against darker `BAND_SHADES`) is
   absent on this render; the fix holds. Did not manage to isolate an unambiguous tall waiting-only
   segment at the crop scales tried to visually confirm the horizontal-line texture in isolation
   (waiting segments in this run's bars are mostly short, mixed with other bands, and read as solid
   fill at this resolution) — see gap note below.
2. **`m-ta-staircase`** (`benchmark/runs/dean-20260810-084756-739/results/inference-perf-1786340933-
   m9emm7_1`) — 3 pods, `Scale-down present drain_events=1`, matching the commit's smaller-scale
   regression-check run. Rendered clean, no crash, panel 3 shows the numbered 3-pod legend
   (`1=l4hqk 2=r2tnh 3=thggq`) with thin uniform outlines and no draining/waiting material visible at
   this run's scale — consistent with the plan's "no crash, thin outlines apply uniformly" bar for
   this run rather than a hatch-visibility check.

**Legend legibility (plan's 3rd verification bullet):** viewed the full panel on both renders — the
panel-3 legend box (run 1, 3-line key) and the numbered pod-color key text (run 2) both render
cleanly, no truncation or overlap with the new hatch/outline styling.

**Not independently confirmed:** a clean, high-zoom isolation of the waiting band's `'--'` hatch on
this review's own re-render — every crop attempted either missed the bar or landed on a segment too
short at this run's data to show the line texture unambiguously (dots were easy to isolate; dashes
were not, at the crop scales tried within this review's time budget). This is a verification gap on
the reviewer's side, not a defect claim — the source-level check (item 2 above) already confirms
`'-'` is genuinely parsed as `HorizontalHatch` and is a different code path from draining's `'.'`
scan, which is the part most likely to be wrong and was checked directly against the interpreter.
Low priority: worth a look next time this panel is touched with a run/crop that has a taller isolated
waiting segment, not worth a re-render cycle on its own.

[↑ TOC](#toc)

## 2026-08-16 — panel 4 KV%-heatmap repurpose + visual follow-up (`0a2be3be` + `f92d3c19`) {#session-2026-08-16-kv-heatmap}

**Reports:** `plan__autoscaling-viz-panel4-kv-heatmap-done.md` (for `0a2be3be`) +
`plan__autoscaling-viz-panel4-followup-done.md` (for `f92d3c19`) — no `review__` trigger was filed
for either; both were routed as `plan__` reports per the coder's own "not marking push-ready, needs
Dean's visual sign-off" instruction, and reviewed here as one combined unit per the planner's explicit
direction, since the second commit is execution-polish on the first with no design questions
reopened. **Plans:** [`autoscaling-viz-panel4-kv-heatmap-plan.md`](autoscaling-viz-panel4-kv-heatmap-plan.md)
(original spec) + [`autoscaling-viz-panel4-heatmap-followup-plan.md`](autoscaling-viz-panel4-heatmap-followup-plan.md)
(6-item visual follow-up).

**Verdict: functionally correct, all items from both specs verified present and working as
specified. One real (currently latent, not push-blocking) defect found: an undefined name that would
raise `NameError` if ever reached — see below. Not re-litigating the heatmap concept per the
planner's framing; this review checked execution against both specs only.**

**Original spec (`0a2be3be`) — verified point by point:**

- **Retirement is genuinely complete**, not deprecation-in-place: grepped the post-commit file for
  every symbol the old panel 4 used (`q_engine`, `q_dispatch`, `q_flow`, the `drawn` flag, the
  `'INTERIM...'` title string) — zero hits outside unrelated comment prose in other panels. The old
  three-series queue plot and its `empty(...)` message are both gone; the new empty-state message
  (`'no metrics/raw/ scrapes — per-pod KV% unavailable'`) replaces it correctly.
- **Layout/data source**: one `imshow` row per pod, `kv` field read directly from each pod's
  `series`, matching the spec's "nothing new to extract" claim — confirmed the field is populated
  end-to-end via `extract_real_trace.py`'s existing `GAUGE['kv']` mapping, not a new extractor commit.
- **Color scale anchored at `k_sat`, not linear [0,1]**: `LinearSegmentedColormap.from_list` called
  with `(0.0, white), (k_sat, green), (1.0, red)` — **independently checked the API against
  matplotlib's own docstring** (`inspect.signature`/`getdoc`) rather than trusting the code comment:
  `from_list` genuinely accepts `(value, color)` pairs with values increasing monotonically 0→1, so
  the three-tuple anchoring is valid, documented usage, not a lucky accident.
- **Dead/live distinction**: `None` cells render as an explicit `to_rgba('#d1d5db')` gray, distinct
  from a real 0.0's white — confirmed visually on both a 15-pod run (`m-satta-dwell`, re-rendered
  fresh at this review's own tip, see below) and an existing 2-pod bundle
  (`real-trace/staircase-20260803/bundle.json`) rendered fresh for this review as an independent
  backward-compat check (the coder's own claim, re-run rather than trusted) — no crash, gray/live
  distinction holds at both pod-count extremes.
- **Average line + colorbar**: `twinx()` overlay with ticks/label hidden (avoiding the collision the
  commit message describes catching by eye), colorbar present and labeled with the `k_sat` value
  baked into the label text. Both visible and legible on the full re-render.
- **Panel 3 average line**: added on its own `twinx()`, `run_tot`/`live_count` computed inline,
  reuses the existing per-pod loop rather than a second pass over the data — reasonable, no
  duplicate iteration introduced.
- **What NOT to change**: grepped the diff against panel 5's own code block and `pod_drain_windows()`
  — neither touched; the diff's insertions land entirely before panel 5's comment marker. Panel 3's
  existing stack/hatch/color calls are untouched by this commit (the line addition is a pure
  insertion after the existing waiting-band block, per the diff).

**Follow-up spec (`f92d3c19`) — all 6 items independently verified, mostly by re-rendering rather
than reading the diff:**

Re-extracted and re-rendered `m-satta-dwell` fresh against this review's own checkout of tip
`f92d3c19` (not reusing the coder's own render) — `coverage.json`'s `extractor_sha` confirmed
`f92d3c19`, matching `git rev-parse --short HEAD` at render time.

1. **Row separators**: confirmed at 2x-3x crop zoom — a visible thin horizontal line at every row
   boundary, all 15 rows crisply distinguished, not just antialiasing.
2. **Scale-up row ordering**: **independently recomputed the expected row-label sequence from the raw
   bundle**, not by eyeballing the render — read every pod's first-sample `t` out of
   `bundle.json['pods']`, sorted ascending, mapped through the same alphabetical `pod_num` scheme
   panel 3 uses (`sorted(pods.items())`, 1-indexed). Got
   `[10, 11, 13, 14, 3, 1, 7, 5, 4, 2, 12, 6, 8, 15, 9]` — **exact match** to the row labels read off
   the rendered heatmap, top to bottom. Confirmed panel 3's own legend line
   (`1=2qvfm 2=2vxwj ... 15=w2sm2`) is byte-identical to the pre-existing scheme, i.e. `pod_num` was
   not resequenced globally — only panel 4's row position changed, exactly as the spec required.
3. **Outlier styling**: confirmed at high zoom — solid gold/amber (`#eab308`) rectangle outlines, no
   hatch, clearly distinct from the shared ink/red/blue dashed `axvline`s and from every cell's own
   green/red/white/gray fill. Not confusable with a decision-event line at any zoom level tried.
4. **Panel 3 line color**: confirmed solid red (`#dc2626`), not dotted black.
5. **Secondary-axis zero alignment**: confirmed visually — panel 3's primary (0-800, "requests") and
   secondary (0-20+, "mean running/pod") axes both bottom out at the same height; the line correctly
   touches the shared zero baseline during the run's wind-down, matching `d3.set_ylim(bottom=0)` in
   the diff.
6. **Panel 6 label overlap**: confirmed on the exact region the plan cites (t≈150-350) — 4 labels
   (`T2-default`, `P3-k2`, `P1-obs`, `P2-hist`) land close together in time and are cleanly staggered
   onto different vertical offsets, no overlapping text at any zoom level tried.

**The infinite-loop bug fix (caught by the coder, not shipped) — spot-checked, not re-litigated**:
the diff's `float('-inf')` sentinel replacing a `-min_label_gap` default is correct reasoning (no real
`x - min_label_gap` can be more negative than negative infinity, whereas a record before the bundle's
own `t0` genuinely can be more negative than a finite `-min_label_gap`) — this matches the commit
message's own explanation exactly and needed no independent reproduction; the fix is narrow and
obviously sufficient, and the coder already root-caused it methodically (bisected against the prior
commit, instrumented per-panel timing) rather than guessing.

**Real finding — undefined name `SAT` at `render_real_trace.py:874`, in the new panel-4 code:**

```python
k_sat = sat.get('threshold') or SAT
```

`SAT` is never defined, imported, or assigned anywhere in `render_real_trace.py` — confirmed by an
AST walk of the module's top-level assignments and imports, not just a text grep (to rule out e.g. a
conditional or aliased definition). If `sat.get('threshold')` is ever falsy (`None`, missing key, or
literally `0`), this line raises `NameError: name 'SAT' is not defined`, crashing the render.

**Why this hasn't fired on any run tried so far, and won't on any bundle from the current
extractor**: `extract_real_trace.py` has its own `SAT = 0.85` module constant, and its `sat_band()`
function (line 963) **unconditionally** sets `'threshold': SAT` in both of its return branches — the
empty-band case (`{'threshold': SAT, 'n': 0}`) and the populated case. Confirmed on two independent
bundles, one fresh (`m-satta-dwell`, this review's own extract) and one pre-existing/older
(`real-trace/staircase-20260803/bundle.json`, extracted well before this commit) — both have
`sat_band.threshold == 0.85`, always present, always truthy. So on every bundle this codebase
currently produces, the `or SAT` branch is dead code that happens to never execute — a real defect,
but latent rather than live. It would surface the moment `sat_band()`'s own always-populate contract
ever changes (a future refactor, or a bundle produced by some other/older extractor version that
didn't guarantee a `threshold` key). Likely origin: `render_real_trace.py`'s own copy of this pattern
(`sat = der.get('sat_band') or {}` then reading `.get('threshold')`) elsewhere in the file probably
had a real local `SAT` fallback constant in mind, copied by analogy into the new panel-4 code without
carrying the constant itself along.

**Not independently re-derived:** the exact numeric outlier-marking threshold's tuning quality (the
spec's own "provisional, expect it may need adjusting" framing) — checked that the rule fires
correctly (population stdev, `>` not `>=`, skips when `sd <= 0` or fewer than 2 live pods) and that
its visual result is legible, but did not independently judge whether one-stdev is the "right" bar
for what counts as an outlier on this data — that's a Dean visual-call, matching the spec's own
framing, not a correctness question this review can settle.

**Update 2026-08-16 — the `SAT` finding above is FIXED, verified independently.** Commit `0aade22f`
adds `SAT = 0.85` as a local module constant at `render_real_trace.py:102`, ahead of its use at line
883 (line moved by the fix's own insertion). Value matches `extract_real_trace.py`'s own `SAT = 0.85`
exactly — no silent mismatch introduced. **Independently reproduced the crash on the pre-fix code**,
not just trusted the commit message's claim of having done so: obtained a read-only copy of `f92d3c19`
via `git show f92d3c19:render_real_trace.py` into an isolated `/tmp` directory (never touching the
shared worktree), fed it a bundle with `sat_band.threshold` synthetically set to `None`, and got the
exact predicted `NameError: name 'SAT' is not defined. Did you mean: 'sat'?` at line 874. Re-ran the
identical nulled-threshold bundle against the post-fix tip — renders clean, no crash. Both halves of
the fix (bug was real and reachable; fix resolves it with the correct fallback value) independently
confirmed. This finding is now CLOSED.

[↑ TOC](#toc)
