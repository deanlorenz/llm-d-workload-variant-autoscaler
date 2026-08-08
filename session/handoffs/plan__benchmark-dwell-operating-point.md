# plan ← benchmark: the mid-band dwell may not be reachable by changing the offered rate

**to:** the benchmark/TA testing planner (owner of `plans/planning/ta-pokprod-testing-plan.md`)
**from:** the `benchmark` session (branch `benchmark`, worktree
`llm-d-workload-variant-autoscaler/benchmark`).
**date:** 2026-08-08
**state:** `.md` (unread)
**relates to:** `plan__benchmark-next-run-capture-list.md` §3.1. This is an **addendum**, not a
replacement — that file still stands. Sent separately because a sender does not edit a handoff it
has already delivered.
**asks for:** one decision that the workload profile cannot make for itself.

> Delivery note: same channel as the previous handoff — authored at
> `benchmark/session-notes/handoffs/plan__benchmark-dwell-operating-point.md` and `cp`'d here,
> because worktree isolation refuses the editor on shared paths. The two copies are identical. I
> cannot flip this to `.WIP`/`.DONE`; the recipient should.

---

## The problem

Dean approved the three scenario changes and I have implemented them
(`hack/benchmark/workloads/inference-perf/ta_autoscale_dwell.yaml.in` and
`ta_prefill_knee.yaml.in`, both new; `session-notes/status/benchmark.md` §17.12 has the full
record). Implementing §3.1 surfaced something the ask does not account for, and it is load-bearing
enough that I would rather raise it than let the run discover it.

**Raising the offered rate may not move steady-state KV utilisation at all.** Under a controller
that is tracking, replicas rise with load and per-replica KV is held near whatever the controller's
operating point implies. In steady state KV is therefore closer to rate-*invariant* than
rate-proportional — it is a **controlled** variable, and the controller is the thing that sets
where it sits.

That is the most economical explanation for the observation the capture list is built on — "no run
in any pool has ever dwelt in 0.3–0.85". On the 08-07 ladder the throughput analyzer dominated the
combine and provisioned ahead of saturation, which holds KV low **by construction**. Arm B reached
KV ≈ 0.99 not because its load was higher but because its ScaledObject was capped at 2 replicas.
Neither number is really a fact about the offered rate.

If that reading is right, then "hold an offered rate that parks KV in 0.3–0.85" is asking the
workload profile to do something only the controller configuration can do.

## The decision I need

The lever is the operating point. Two candidates:

**(a) Saturation analyzer alone, uncapped.** Throughput analyzer off, `maxReplicas` left at 10. The
saturation analyzer's own scale-up/scale-down watermarks are 0.85 / 0.70, so its steady state sits
*inside* the requested band by design — the band and the watermarks are nearly the same interval.
Arm B was already this configuration and missed only because of the replica cap. **This is the
cheapest and cleanest route to the dwell and it costs no extra requests.** It does change what the
run is a test of: it measures SAT's own right-sizing rather than the combined optimiser's.

**(b) A deliberate replica cap.** Guaranteed to park KV wherever you want it, but it measures the
cap. That is precisely why the ladder rejected a cap — every latency number at a binding cap is a
measurement of the cap, not of the controller. Legitimate as an instrument if chosen knowingly;
not legitimate as a default.

I have no standing to pick between these: both are analyzer/scenario changes, not workload changes.
My read is that **(a)** is right if the goal is "does the autoscaler hold the service at the right
size", which is how I understand Dean's stated forward direction (right-sizing and steady-state over
transition speed). **(b)** is right only if the goal is specifically to characterise engine
behaviour at a known KV level, with the autoscaler deliberately out of the loop.

## What I have done in the meantime, so the run is not blocked on the answer

`ta_autoscale_dwell.yaml.in` exploits replica **quantisation** instead, which needs no config
change. Replica count is an integer, so per-replica load — and hence KV — peaks at rates just below
the point where one more replica is warranted. The profile takes two long rungs 1.3× apart, **20 and
26 rps at 360 s each**, as two independent samples of that sawtooth; whichever lands on its high
side yields the dwell.

The 20 rps rung is **retained from the ladder as a control**, deliberately and not by inertia. If
both rungs come back at KV ≈ 0.67, that is a clean positive result for rate-invariance and settles
the question the other way — at which point (a) or (b) becomes necessary rather than optional. So
the run is informative either way; it just may not deliver the dwell itself.

## Two smaller things from the same implementation pass, for the plan's awareness

1. **A rung above 26 rps did not fit** and is a deliberate omission, not an oversight: 32 rps ×
   300 s is another ~9,600 requests ≈ 5.1 GB of per-request trace, and the 20Gi results PVC cannot
   hold it beside the two dwell rungs. It is the natural follow-up run if both rungs read low.
2. **The short-output leg has the same problem, more sharply.** A knee is a property of load per
   replica, and the autoscaler's job is to keep load per replica off the knee. Sweeping offered
   rate under an active controller samples the operating point, not the curve. Per-stage ITL against
   *measured* concurrency-per-replica is still a valid point at each rung, so `ta_prefill_knee` is
   not wasted — but the sharp instrument for a knee is a **fixed replica count with autoscaling
   off**, which is again a scenario decision.

## Not part of the ask

No cluster action is requested and no run is proposed. Dean's standing rule holds: **wait for his
approval before any run.** The configuration is staged and unlaunched; §17.12 lists its four
preconditions (PVC reclaim to ≥14 GB with `verify_pvc_vs_host.py` gating it, confirm the 96Gi
harness pod schedules, the 5-GPU footprint flag, and running `post_run_analyze.sh` immediately
after).
