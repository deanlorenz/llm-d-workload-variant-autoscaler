from: dwell-deep-dive (dedicated session per session/handoffs/dwell-deep-dive__handoff.md.DONE)
to: sync
session: dwell limit cycle — deep dive

## What to fold into CURRENT.md

This session answered the question the dedicated deep-dive was opened for: **why does the dwell
limit cycle happen** (§ Recent activity, the 2026-08-10 pokprod benchmark entry, Finding 2 in
`planning/ta-pokprod-campaign-20260810-results.md`). Add a new dated sub-item under that entry (or
a new bullet if the parent entry is being compressed) along these lines:

**2026-08-11 — dwell limit cycle root-caused: replica-readiness lag, not a bookkeeping bug.**
Traced `m-satta-dwell`'s and `m-sat-dwell`'s controller.log against the actual
saturation_v2/optimizer code (not just log inference). Findings, in order of how the session
converged:

1. The ramp-to-cap excursions are triggered by saturation's `P1-obs` (`k2SrcObserved`) priority
   reading a real, large `waitingQueueDemand` snapshot — `util>1` is by design (unclamped
   demand/supply ratio), not a bug. Reproduces in SAT-only worse than SAT+TA; TA-only doesn't
   drive it because saturation isn't voting there (config-confirmed).
2. Dean's abstract accounting model (ready supply is the only "real" supply; RC = demand/PRC −
   ready; allocator handles the delta; actuator nets out in-flight orders) was traced end-to-end
   against the code and **holds structurally** — `TotalAnticipatedSupply = (ReplicaCount +
   PendingReplicas) × PRC` is exactly this term, and the optimizer's `targets[v] += k` on top of
   `targets` initialized to `CurrentReplicas` confirms no double-counting.
3. Decomposed the actual lag into two hops using ground-truth Deployment status
   (`EmitReplicaMetrics`'s `currentReplicas`, confirmed to be `scaleTarget.GetStatusReplicas()`):
   **ordered→created is fast (~1 tick, ~60s, matches the 15s KEDA poll interval)** — not the
   bottleneck. **created→ready is slow and worsens with concurrent boot count** — in
   `m-satta-dwell`'s first excursion, ready peaked at 9 and never reached the ordered/created
   peak of 10; the controller began retreating from its own peak order before the last replica
   it asked for ever became ready. This is the dominant mechanism — physical (model load + GPU
   scheduling contention under concurrent boots), not a WVA control-loop defect.
4. **Dean's synthesis, the session's conclusion:** (a) the pending-vs-actual lag is real and
   can't be circumvented; (b) double-booking is correctly avoided today — the anticipated-supply
   term works; (c) the real gap is a missing forecast (detail + ownership in the companion
   `plan__` handoff to the planner, not repeated here).

**State/resume:** [`session/status/dwell-deep-dive.md`](../status/dwell-deep-dive.md) — full code
trace (file:line citations throughout), the two-hop lag table, and the synthesis. Do not delete —
it's the durable trace backing the Type-1 TODO tracked via the companion `plan__` handoff.

**Companion handoff:** `plan__dwell-limit-cycle-forecast-todo.md` carries the forward-work item
(the Type-1 forecast TODO) to a working planner — that item is a task/decision-request, not a
CURRENT-update, so it is deliberately NOT included here. If CURRENT.md's summary of this thread
wants a pointer to it, a one-line "see plan__dwell-limit-cycle-forecast-todo.md for the open
Type-1 item" is enough; do not restate its content here.

**Original results doc note (optional, if sync has bandwidth):**
`planning/ta-pokprod-campaign-20260810-results.md` Finding 2 currently frames the mechanism as
"replica lag" in general terms; this session's trace sharpens that into the specific
ordered→created (fast) vs created→ready (slow, dominant) decomposition and the retreat-before-
ready observation. Not urgent to edit that doc — the sharper account now lives in
session/status/dwell-deep-dive.md — but flagging in case sync or a future reader wants the
primary doc updated to match.

## Housekeeping already done by this session
- Marked the originating `session/handoffs/dwell-deep-dive__handoff.md` as `.DONE` (consumed).
- No other write-scope actions taken outside `session/status/` and `session/handoffs/`.
