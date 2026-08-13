# Drain-window bound fix — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 7. Source finding: [`autoscaling-viz-panel-review-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md)
§ Item J.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L18:27
- [Confirmed root cause {#root-cause}](#confirmed-root-cause-root-cause) L28:51
- [Fix {#fix}](#fix-fix) L52:75
- [Explicitly out of scope {#out-of-scope}](#explicitly-out-of-scope-out-of-scope) L76:87
- [Verification {#verification}](#verification-verification) L88:105

## Goal {#goal}

Fix `extract_real_trace.py`'s `pod_drain_windows()` (introduced in Task 2, commit `fbecfe26`):
today it can mark a pod as "draining" for a window that starts long before the replica set actually
stopped wanting it — sometimes covering most of the pod's serving history. Confirmed on real data
(`m-ta-staircase`): a pod is shown draining from t≈615s, when `desired=ready=3` (fully wanted) the
entire time until the real drain event at t≈1073s.

[↑ TOC](#toc)

## Confirmed root cause {#root-cause}

`pod_drain_windows()` (`extract_real_trace.py:825-869`):

1. Matches a pod's **last sample** against the nearest aggregate `drain_events` timestamp, within
   `DRAIN_MATCH_WINDOW_S` (120s). **This half is correct** — verified on `m-ta-staircase`, pod
   `r2tnh`'s last sample (t≈1058s) correctly matches the run's one real drain event (t≈1073s, 15s
   apart, within tolerance).
2. Computes the window's **start** by scanning backward through the pod's own samples while
   `run > 0` holds continuously (lines 863-868), with **no bound tied to the replica set's own
   `desired` transition**. On `m-ta-staircase`, this pod had `run > 0` continuously since t≈615s
   (443s of real, fully-desired serving), so the backward scan walks all the way back there,
   producing a window that includes that entire span — not just the brief tail after the pod
   actually stopped being desired.

Confirmed via direct inspection this session:
- `derived.lags.drain_events` for this run: exactly one entry, t≈1073s (relative).
- Replica timeseries: `desired=3, ready=3` continuously from t≈615s to t≈1057s; drops to
  `desired=2, ready=2` at t≈1073s.
- `pods['...r2tnh'].drain_windows`: `[[615s, 1058s]]` (relative) — should be a short tail near
  1073s, not this whole span.

[↑ TOC](#toc)

## Fix {#fix}

Bound the backward scan by the replica set's own `desired` transition, not just by trailing
`run > 0`. Concretely: `pod_drain_windows()` needs access to the replica timeseries (`reps`, already
available in the extractor's main flow — check the call site at `extract_real_trace.py:1320` for
what's already in scope) to determine the actual instant `desired` dropped below the pod's replica
set's `ready` count, and clip the backward scan to not extend earlier than that instant (plus
whatever propagation lag is appropriate — use judgment, but do not default to "no bound" as today's
code effectively does).

Concrete approach (one option, not mandated — the coder may find a cleaner formulation once looking
at the actual data shapes in scope at that call site):
1. Find the `desired` step-down nearest this pod's matched drain event (same event already matched
   in step 1 above — reuse it, don't re-derive).
2. Clip `t_start` (the backward-scan result) to `max(t_start, that step-down's timestamp)`.
3. If the clipped window is empty or negative-length, this pod's drain window should be dropped
   entirely (it means the naive backward scan found nothing between the real transition and the
   pod's last sample — not an error, just no drain window to report for that pod).

Verify against `m-ta-staircase`'s `r2tnh` specifically: the fixed window should start close to
t≈1073s (the real `desired` transition), not t≈615s.

[↑ TOC](#toc)

## Explicitly out of scope {#out-of-scope}

- Panel 3's visual scheme changes (dots/dashes, outline weight, consistent per-pod color) —
  separate item (§ Item K of the follow-up review), explicitly blocked on this fix landing first.
  Do not combine into one commit; land this fix, verify it, then let the visual-scheme work follow
  once the underlying windows are correct.
- The figure-title issue on `m-satta-staircase`/`m-sat-staircase` (§ Item I) — not yet root-caused,
  separate investigation.
- The per-panel corner-info allocation (§ Item L) — not yet a scoped Type 3.

[↑ TOC](#toc)

## Verification {#verification}

- Re-extract and re-render `m-ta-staircase` after the fix; confirm no draining band appears before
  the real `desired` transition (t≈1073s relative) for pod `r2tnh` or any other pod. **Corrected
  2026-08-13, post-implementation** (flagged independently by both the coder and the review agent):
  for `r2tnh` specifically, the real transition (t≈1073s) lands *after* the pod's own last sample
  (t≈1058s), so the correct outcome is **no drain window at all** for that pod, not a short window
  near t≈1073s — the fix's own step-3 fallback (drop the window if clipping collapses it to
  nothing) fires correctly here. The check that matters is "no draining band before the pod's own
  last observed instant," not "a window survives near the real event" — the latter doesn't hold for
  every pod and was never guaranteed to.
- Spot-check at least 2 other cells with real scale-downs (e.g. `m-satta-dwell`, `m-sat-dwell`) to
  confirm the fix doesn't regress cases where the drain window was already correct (short tail near
  the real event).
- Confirm the "stack ≡ total in-system" invariant still holds after the fix (running + draining +
  waiting + EPP-queue should still sum to total-in-system, per Task 2's own original invariant).

[↑ TOC](#toc)
