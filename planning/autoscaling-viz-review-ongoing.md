# autoscaling-viz — ongoing code review

**Status:** DRAFT
**Scope:** running log, one dated section per commit/trigger reviewed. Cross-reference
[`autoscaling-viz-review-20260813.md`](autoscaling-viz-review-20260813.md) for the earlier batch
(`037106f2`, `fbecfe26`+`08927557`) — not repeated here.
**Reviewer:** background review agent, this session.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [2026-08-13 — panel 6 redesign (`3f12aaa1`) {#session-2026-08-13-panel6}](#2026-08-13--panel-6-redesign-3f12aaa1-session-2026-08-13-panel6) L27:71
- [2026-08-13 — drain-window fix (`e188d244`) {#session-2026-08-13-drain}](#2026-08-13--drain-window-fix-e188d244-session-2026-08-13-drain) L72:110
- [2026-08-13 — backlog rerun (`cf76a238`, no trigger) {#session-2026-08-13-backlog}](#2026-08-13--backlog-rerun-cf76a238-no-trigger-session-2026-08-13-backlog) L111:120

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
