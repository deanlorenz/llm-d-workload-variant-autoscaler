from: plan (viz-panels scope)
to: plan (benchmark scope)
session: viz-panels

## Proposal: add a short warm-up step before stage 1 of every workload run

**Motivation, two independent reasons, both Dean's:**

1. **Stage-0 Envoy-trace truncation.** `plan__per-request-estimation-built-two-findings.md`
   (2026-08-16, your own scope's finding on `dean-20260813-005321-943`) found the target run's Envoy
   trace missing 1,732 of 21,120 attempted requests, concentrated at the START of the window —
   "stage 0 (the 5rps entry rung) has ZERO requests in the estimate — entirely evicted." That
   handoff already flagged the gateway-log-follower as the fix for *capture*; a warm-up step is a
   separate, complementary mitigation on the *workload* side — if stage 0 is a genuine warm-up
   rather than a measured rung, losing its trace matters less.
2. **System stabilization, independent of the truncation issue.** Dean, directly: "let's add a
   short warmup step for every run. Good time to stabilize the system if we start from non-zero
   replicas. Good stabilization if we want a quiet period before the test." Several campaign runs
   start from a non-1 replica count left over from a prior run (per `session/status/benchmark.md`'s
   own recorded observations on run-to-run replica-count carryover) — a warm-up step gives the
   system a quiet interval to settle before the timed portion begins, independent of whether the
   Envoy-truncation issue is ever otherwise fixed.

**What's being proposed, as Dean stated it:** a warm-up step ahead of what's currently "stage 1" in
each workload profile. Stage numbering shifts by one (today's stage 1 becomes stage 2, etc.) —
Dean's own framing: "our 0 sec would start at stage 1," i.e. `t=0` marks the start of the
first *measured* stage, with the warm-up occupying negative time before it.

**Not decided, yours to scope:** warm-up duration, target rate/shape (a fixed low rate? ramping?),
whether it varies per workload profile or is a fixed prefix applied uniformly, and how the harness's
own stage/window bookkeeping (results.json, per-request estimation's stage assignment, etc.) should
represent negative-time data — whether it's captured at all, discarded, or kept and just excluded
from stage-1-onward statistics.

**Viz-side implication, flagged but explicitly not part of this ask:** Dean separately asked for
panel 6 (and implicitly others) to be able to show `t=0` scaling-decision markers without them
sitting at the left edge of the plot — "we can shift the y-axis [x-axis] to -10, so [we] can see 0
sec decisions markers." That's a `render_real_trace.py` change on my side, gated on this warm-up
step actually landing in the harness (there's no negative-time data to show until then). I'm holding
that as a viz-panels TODO, not asking you to build anything for it — just flagging so the two don't
get designed independently of each other if you land this.

## Not a request for immediate action

No urgency stated — flagging for whenever you're scoping harness/workload changes next, not asking
you to interrupt current work.
