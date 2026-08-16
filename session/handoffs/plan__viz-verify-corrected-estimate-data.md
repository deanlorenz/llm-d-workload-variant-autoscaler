from: plan (pokprod/benchmark-execution scope)
to: plan (autoscaling-viz scope, viz-panels session)
session: viz-panels

## Ask

Per Dean's direct request — please check the corrected per-request estimate data for
`dean-20260813-005321-943` yourselves, through your own toolchain (not my standalone scratch
render, which is a rough sanity check only, not the real panel pipeline).

File: `runs/dean-20260813-005321-943/results/inference-perf-1786571670-2sxaiq_1/metrics/processed/per_request_estimated.json`
— regenerated 2026-08-16 after the boundary-spike bug fix (`c0f4d5f3`, D-62). Field shapes and the
design rationale are in `envoy-per-request-recovery-tool-plan.md`'s "Per-request data
extraction/estimation for panels 1a/1b" section.

## Context, so you're not starting cold

Three things Dean flagged directly from my own rough render, worth checking properly through your
pipeline:
1. **Stage 0 (the 5rps entry rung) has zero requests** — a real source-data gap (kubelet log
   rotation evicted it from the post-run harvest), not a code defect. **Update since that finding:**
   the complete trace actually exists on the cluster (the gateway-log-follower's PVC copy) — a
   one-off re-harvest for this specific run is in progress on my side now, separate from this ask.
   Worth waiting for that before final panel judgment on stage 0 specifically.
2. **Stage 4 shows an unexplained rate anomaly** (58% above configured) — still open,
   unresolved, not blocking.
3. **Dean's own observation from viewing my rough render:** "red density [in the TTFT scatter]
   -- need to check" — I haven't investigated this myself; flagging verbatim so you can look at
   it through the real toolchain rather than my rough one.

Not asking you to fix anything — just to verify through your actual pipeline whether the
corrected estimate is usable for panels 1a/1b's purposes, now that the known code bug (D-62) is
fixed.
