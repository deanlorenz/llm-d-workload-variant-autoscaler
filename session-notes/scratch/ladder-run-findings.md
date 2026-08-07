# Ladder run 2026-08-07 — TA per-replica-capacity instability drives a 9-minute overprovision and an ~18% latency penalty

**STATUS: analysis COMPLETE**, behavioural and client-side (all 8 stages observed,
descent included; decision rule reconstructed and verified 65/65 cycles; per-stage
latency joined to time-weighted replica counts).

**One data loss:** the harness was OOMKilled while serialising the per-request trace, so
`per_request_lifecycle_metrics.json` is 0 bytes and no per-request distribution exists.
All 8 per-stage aggregates and the summary survived, and server-side token truth was
recovered from the vLLM scrapes, so every conclusion below stands on measured data. What
is genuinely unrecoverable is listed under "What the OOM cost".

Two early claims in this document were **wrong and have been corrected in place**, both
traceable to modelling the engine as `ceil(demand/prc)`: a phantom third "internal
target" level, and a phantom one-step-per-cycle limit. See the rule section immediately
below and the retractions under Open items.

## Setup

| | |
|---|---|
| run dir | `dean-20260807-234050-328` (local 23:40 = 20:40 UTC) |
| launched | 2026-08-07T20:39:54Z; **first request 20:41:44.330Z** (gateway access log) |
| | the run log's `All pods are running` implies 20:42:36 — 52 s late, see "Stage windows" |
| controller | `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9-anchor-20260807` |
| running digest | `sha256:ab4c8503df58fb20b7c17c735af2d452f64208fdd2a7b9d354efd73f66c87a13` |
| | (verified against quay's own manifest, not just the local RepoDigest) |
| analyzers | `saturation` + `throughput` |
| profile | `ta_autoscale_ladder` — 8 x 300 s, rates 2,5,8,10,12,15,20,2 |
| replica cap | 1..10 (raised from 1..2, which BOUND on the 08-07 A/B pair) |
| namespace | `dhl-wva-209` |
| controller log | `session-notes/scratch/ladder-controller.log` (captured live, `--timestamps`) |
| analysis tool | `session-notes/scratch/decision_timeline.py` |

## How the engine actually computes a target (established, 65/65 cycles)

> Cycle count, stated precisely: `verify_decision_rule.py` matches **65 of 65** cycles in
> the captured log with zero mismatches. **37** of those fall inside the load window and
> are the ones carrying signal; the remaining 28 are the post-run idle tail (`demand = 0`,
> `1 -> 1` hold), which the rule satisfies trivially and which should not be counted as
> independent evidence. Earlier drafts of this document quoted 30/30 and 32/32 — those
> were snapshots taken while the log was still being tailed, not different results.

**Read this before the tables.** An earlier draft of this doc asserted the engine
computes `ceil(demand/prc)`. It does not. That wrong model is what made `tgt=1` at
20:51:37 look anomalous. The real rule, per analyzer, is a *delta* against the
watermark-relative capacity gap:

```
rc = demand/scaleUpThreshold  - supply      if rc > 0:  tgt_a = curr + ceil (rc/prc)
sc = supply - demand/scaleDownBoundary      if sc > 0:  tgt_a = curr - floor(sc/prc)
                                            otherwise: tgt_a = curr        (hold)

tgt = max over analyzers, clamped to [minReplicas, maxReplicas]
```

with `scaleUpThreshold = 0.85`, `scaleDownBoundary = 0.70`. `supply` is the analyzer's
total capacity estimate; note it is NOT always `curr x prc` — the analyzer's replica
basis can lag the observed count by a cycle (at 20:51:37 the basis was 3 while `curr`
was 2). The rule is basis-independent because `rc`/`sc` are already relative to
`supply` and the delta is applied to `curr`.

Verified by reconstruction against every cycle in the captured log:
**30 matched, 0 mismatched** (`session-notes/scratch/verify_decision_rule.py`). This was
derived from the logged payloads, not read off the source tree — the `benchmark` branch
here is not the commit the deployed image was built from.

Three consequences:

1. **`ceil` on scale-up means an arbitrarily small watermark breach costs a whole
   replica.** At 20:55:38 `rc` was **137 tokens** — 3% of one replica's capacity — and
   `ceil(137/2239) = 1`. This is the real amplifier, and it compounds with
   `scaleUp.stabilizationWindowSeconds: 0`.
2. **The fleet is sized to 85% of estimated capacity, not 100%.** The effective target is
   `demand/(0.85 x prc)` — a built-in 1.18x headroom multiplier stacked on a noisy `prc`.
3. **SAT votes to shrink on nearly every cycle** (`-1` or `-2`), because its `prc` is a
   KV-cache token capacity (329,011) that dwarfs demand. It is TA's more conservative
   claim winning the `max` that holds the fleet up. The combine is working as designed;
   SAT never blocked or drove a single decision in this run.

The rounding asymmetry (`ceil` up, `floor` down) is *correct* — conservative in both
directions. The defect is not the rounding; it is that a 3% breach suffices to trigger
it, unfiltered.

## The measurement

Per-cycle, from the captured controller log. `prc` is TA's estimate of one replica's
token capacity, computed from observed throughput and unsmoothed.

```
time         TA prc   TA dem  TA util   TA rc  SAT util | decision
20:42:36      343.1      859    2.504     668    0.0179 | 1->3 scale-up    <<<
20:43:36      655.8      890    1.357       0    0.0195 | 3->3 no-change    prc x1.91
20:44:37     1739.7      895    0.257       0    0.0363 | 3->2 scale-down  <<<  prc x2.65
20:45:37     1461.1     1257    0.430       0    0.0691 | 3->3 no-change
20:46:37      692.6     1056    0.508       0    0.0547 | 3->3 no-change    prc x0.47
20:47:37     1705.4     1952    0.382       0    0.0921 | 3->2 scale-down  <<<  prc x2.46
20:48:37     1685.4     2781    0.550       0    0.1064 | 3->3 no-change
20:49:37     2024.9     2553    0.420       0    0.0959 | 3->2 scale-down  <<<
20:50:37     1991.9     2464    0.412       0    0.0961 | 3->2 scale-down  <<<
20:51:37     2062.2     2669    0.431       0    0.0831 | 2->1 scale-down  <<<
```

Two things to read off this table:

1. **Saturation never asked for anything.** `SAT util` peaks at 0.106 against a 0.85
   scale-up watermark. Every decision here is TA's.
2. **`prc` moved 5.1x while demand moved 4%.** At 20:42:36 demand was 859 and
   `prc` 343; two minutes later demand was 895 (+4%) and `prc` was 1739.7 (+407%).
   The replica target tracked the estimator, not the workload.

## Mechanism (established, not inferred)

### Step 1 — cold `prc` overprovisions immediately

TA emits no `prc` at all for the 22 cycles before traffic arrives (`prc = -`), because
it estimates capacity *from observed throughput*. Its first real estimate is therefore
its coldest: 343 tok/s, against a converged value of ~2000 (5.9x low). One replica had
not yet demonstrated its capacity.

Applying the real rule: `rc = 859.33/0.85 - 343.13 = 667.9`, and
`tgt = 1 + ceil(667.9/343.13) = 1 + 2 = 3` — exactly the target emitted. At the ladder's
*lowest* rate (2 RPS) the fleet was set to 3.

(An earlier draft wrote this as `ceil(859.33/343.13) = ceil(2.504) = 3`. That happens to
land on the same answer here but is the wrong formula — it omits the 0.85 divisor, and
it does not reproduce other cycles. Corrected above.)

The HPA has `scaleUp.stabilizationWindowSeconds: 0`, so this actuated with no damping.

### Step 2 — oscillation makes the correction unreachable

`prc` then oscillated between a ~350-700 band and a ~1450-1740 band, period 60-180 s.
Kubernetes HPA scale-down stabilization takes the **maximum** recommendation over the
trailing window (deliberately, to resist eager shrinking). The KEDA-generated HPA here:

```
scaleUp:   {stabilizationWindowSeconds: 0,   policies: [{Percent 100, 15s}]}
scaleDown: {stabilizationWindowSeconds: 120, policies: [{Percent 100, 15s}]}
```

With a target alternating high/low every 60-180 s, **every 120 s window retains a high
sample**, so the max never falls:

```
window ending 20:47:37  ->  tgt 3, 3, 2  ->  max 3
window ending 20:48:37  ->  tgt 3, 2, 3  ->  max 3
```

Scale-down was therefore not merely delayed but *unreachable while the oscillation
persisted*. Requests at 20:44:37 and 20:47:37 both had no effect; the deployment stayed
3/3.

### Step 3 — convergence releases it

Once sustained load gave the estimator something to measure, `prc` settled into a
stable band (1685, 2025, 1992, 2062) and the scale-down requests became consecutive
rather than alternating. Three in a row dropped the window max to 2 and the fleet
actuated down at 20:51:37.

This was recorded as a **falsifiable prediction before it happened** (predicted: if the
next cycle also emits tgt=2 the window becomes {2,2,2} and the fleet drops shortly
after ~20:51:37; predicted failure mode: if it stayed at 3 past ~20:52 with sustained
tgt=2, the max-over-window reading would be wrong). It landed on the predicted cycle.

### Net effect

**The overprovision persisted ~9 minutes** (20:42:36 -> 20:51:37), covering the whole
2 RPS stage and most of 5 RPS. The fleet size was set by the single worst `prc` sample
of the run and no subsequent correct reading could undo it until the noise itself
stopped.

## The same defect at steady state, with flat demand (stronger evidence)

The cold-start case above invites the dismissal "add a warm-up guard and it's fixed."
It is not confined to startup. At 20:55:38, under sustained load:

```
20:54:38     2937.5     3929    0.669       0    0.2454 | 2->2 no-change
20:55:38     2238.6     3922    0.876     137    0.2337 | 2->3 scale-up  <<<
20:56:38     3146.4     4280    0.680       0    0.2752 | 3->3 no-change
```

Demand was **flat and in fact slightly falling** (3929 -> 3922, -0.2%). `prc` dipped 24%
for exactly one cycle, carrying `util` from 0.669 across the **0.85 scale-up watermark**
to 0.876. `scaleUp.stabilizationWindowSeconds: 0` actuated it immediately. One cycle
later `prc` had recovered to 3146 and `util` was back to 0.680 — well under the
watermark, i.e. 2 replicas were adequate throughout.

How small the trigger was, precisely: the breach amounted to `rc = 137` tokens/s —
**3% of one replica's capacity** — and `ceil(137/2238.6) = 1` turned it into a whole
replica. The magnitude of the shortfall carries no information at all; only its sign
does.

**A single-cycle estimator excursion permanently added a replica.** Permanently, because
the scale-down path needs ~120 s of sustained low recommendations and the ongoing noise
keeps refilling the window with high samples.

Amplitude at high load is smaller (2238 <-> 3545, ~1.6x, vs ~2.5x at low load) but that
does not make it benign: once `util` sits in the 0.67-0.69 band, a routine 24% dip in
the denominator is sufficient to trip the watermark.

### `util` is measured against a moving yardstick

`prc` **trends with load** — ~2000 tok/s at 5 RPS, ~3000-3500 at 8-10 RPS. Since
`util = demand / (replicas x prc)`, rising demand partially cancels itself in the ratio.
That is why `util` stays pinned in a narrow band (0.38-0.88) while demand nearly doubles
(2464 -> 4280). The watermark comparison is therefore much weaker than it appears: it is
not "how loaded is the fleet" but "how loaded is the fleet relative to a capacity
estimate that is itself moving and noisy."

## The real defect is the stabilisation ASYMMETRY, not the window length

An earlier reading of this run (recorded here for honesty) held that the 120 s window
was the problem because it made correction "structurally unreachable". Watching the
sustained-load cycles falsified that framing.

Under sustained load `prc` is well behaved — 2928, 3009, 2891, 2983, 2975 over five
consecutive cycles is +/-2%. The instability is concentrated at load onset, at low
rates, and in isolated single-cycle excursions. Two such excursions produced *spurious
scale-DOWN* requests:

```
21:01:38     2974.8     5089    0.570       0    0.1864 | 3->3 no-change
21:02:38     3858.6     4804    0.415       0    0.2645 | 3->2 scale-down  <<<
21:03:38     3288.2     6215    0.630       0    0.2536 | 3->3 no-change
```

`prc` spiked +30% for one cycle, `util` fell below the 0.70 boundary, and a scale-down
was requested. It was correctly **rejected** by the 120 s window. The fleet held at 3
from 20:55 onward precisely because isolated dips cannot sustain a 120 s window.

So noise generates bogus requests in BOTH directions, and the window is the only
component filtering any of them:

| direction | filter | single-cycle noise |
|---|---|---|
| scale-up | `stabilizationWindowSeconds: 0` | passes straight through |
| scale-down | `stabilizationWindowSeconds: 120` | correctly rejected |

**Identical noise is rejected downward and actuated upward.** That asymmetry, not the
window length, is what produces the net upward bias. The window is doing its job; the
missing scale-up filter is the defect.

### Fix implications

1. **Primary: smooth `prc`** (EWMA or similar) and add a warm-up guard so the first
   post-onset estimate cannot drive a decision. This addresses the root cause and both
   failure directions.
2. **Independent mitigation: a symmetric scale-up stabilisation window.** Even 30-60 s
   would have killed both observed spurious scale-ups (each was a single cycle), at the
   cost of up to one control interval of latency on genuine ramps.
3. Do NOT shorten the scale-down window — it is currently the only thing suppressing
   the spurious scale-down requests.

### `util` is measured against a moving yardstick

Confirmed against the data: `util = demand / (replicas x prc)`, e.g.
`6215 / (3 x 3288.2) = 0.630`. Because `prc` itself trends with load (~2000 tok/s at
5 RPS, ~3000-3500 at 8-12 RPS), rising demand partially cancels in the ratio. `util`
therefore stays in a narrow band (0.41-0.88) while demand nearly triples
(2464 -> 6215). The watermark comparison is weaker than it appears: it measures load
relative to a moving, noisy capacity estimate rather than absolute headroom.

Demand tracks the profile correctly (6215 ~= 12 x 512 at the 12 RPS stage), so the load
generator is not implicated in any of the above.

## Severity is inverted relative to where you'd want it

`prc` is noisiest when there is least traffic to estimate from, and converges under
sustained load. So the estimator is least reliable exactly when the fleet is smallest,
where a bad sample costs the largest *relative* overprovision: 3x at 2 RPS here. The
same 2.5x noise at 20 RPS would be a rounding error on a fleet of ~5. The
1694 <-> 3849 swing recorded on earlier runs is very likely this same phenomenon
sampled at a different absolute level.

## Why the raised cap was a precondition for seeing any of this

Under `maxReplicas=2` the cold-`prc` target of 3 would have been clipped to 2 and
been indistinguishable from a legitimate scale-up. The instability was not absent from
the 08-07 A/B pair — it was **clamped and therefore invisible**. This also means the
7x p95 gap attributed to TA in that pair cannot be read as TA being protective; see
the correction recorded in the status file.

## The TA/SAT divergence is load-dependent and vanishes at saturation

The single most useful result of the run. Same instants, both analyzers:

| stage | TA util | SAT util | ratio |
|---|---|---|---|
| 2 RPS | 2.504 | 0.0179 | ~140x |
| 8 RPS | 0.669 | 0.2454 | 2.7x |
| 12 RPS | 0.630 | 0.2536 | 2.5x |
| 15 RPS | 0.743 | 0.3664 | 2.0x |
| 20 RPS | 0.900 | 0.8106 | **1.11x** |

At 20 RPS SAT engaged for the first time (util 0.81, just under its 0.85 watermark) and
emitted `hold` instead of its habitual `-1`/`-2`. The ratio collapses **monotonically
toward 1** as load rises.

So TA's disagreement with saturation is **not a fixed calibration offset — it is a
load-dependent bias that disappears at true saturation.** That is precisely the
signature of a `prc` estimated from observed throughput: with little traffic there is
little evidence, the estimate reads low, and `demand/(0.85 x prc)` inflates. With
abundant evidence the two measures converge. This localises the fix to the estimator
rather than to the thresholds, the combine, or the HPA.

Corollary for earlier runs: the "TA util ~2x SAT" summary from the 2026-08-03 staircase
was a sample of this curve at one load level, not a constant.

## A 15 RPS control regime that behaves correctly (positive control)

Worth recording as clearly as the defects, because it bounds them:

```
21:08:39     3275.8     7334    0.746       0    0.3276 | 3->3 no-change
21:09:39     3477.9     7455    0.715       0    0.3289 | 3->3 no-change
21:10:39     3666.1     7865    0.715       0    0.3857 | 3->3 no-change
21:11:39     3497.1     7793    0.743       0    0.3664 | 3->3 no-change
```

Demand 7793 ~= 15 x 512. `util` 0.715-0.746 sits inside the 0.70-0.85 dead band, and TA
emitted `rc=0, sc=0` — a genuine **hold**, not a suppressed request. Four consecutive
quiet cycles at 3 replicas. When `prc` is stable and load lands in the band, the
controller is quiet and correct. The failures elsewhere are noise-driven watermark
crossings, not a broken design.

The 20 RPS scale-up (3 -> 4 at 21:13:39) was likewise predicted in advance and clean.

## The descent: a controlled comparison that settles where the defect lives

The closing 2 RPS stage is the decisive measurement of the run, because it exercises the
scale-down path with a *stable* estimator and an unambiguous demand drop.

```
21:17:40     4178.7    10427    0.624       0    0.3959 | 4->4 no-change
21:18:40     4178.2      912    0.055       0    0.0501 | 4->1 scale-down  <<<
```

Demand collapsed 11x in one cycle (10427 -> 912) while `prc` stayed put
(4178.7 -> 4178.2). Both analyzers independently claimed -3
(`floor(15410/4178) = 3`, `floor(1221860/329011) = 3`), so the emitted target was 1.

Actuation:

```
21:18:40   first tgt=1 emitted
21:19:40   second tgt=1, deployment still 4/4
21:20:30   deployment still 4/4
21:21:18   deployment 1/1     <- actuated, 4 -> 1 in a SINGLE move
```

Latency ~120-125 s = **exactly the stabilisation window**, followed by a full-magnitude
release (the `Percent 100 / 15s` policy imposes no per-step limit). The GPU coupler
reclaimed in step: decode 1 + reservation 4 = 5 GPUs held, constant.

### The comparison

With the HPA configuration held fixed across both episodes:

| condition | scale-down outcome |
|---|---|
| genuine sustained demand drop, **stable** `prc` | actuated in 120 s, full 4 -> 1 |
| flat demand, **noisy** `prc` (20:44-20:51) | blocked ~9 minutes |

Same 120 s window, same policy, opposite outcomes. The only variable is the estimator's
stability. This **retires the original framing** in which the window was blamed for
making correction "structurally unreachable": the window behaves exactly as designed the
moment it is fed a stable signal. The 9-minute block was caused by `prc` oscillation
refilling the window with high samples — a defect in the input, not in the filter.

Net: every scaling pathology observed in this run is downstream of `prc`. The thresholds,
the combine, and the HPA all behaved correctly whenever `prc` was stable.

## Client-side result: latency is monotone in per-replica load, not in RPS

This is the strongest single result of the run, and it is what makes the scaling
behaviour above matter to a user.

### Stage windows, and the 52 s error an earlier revision of this section had

Everything below joins latency to a replica count, so it depends entirely on knowing when
each stage began. An earlier revision got that wrong and the error propagated into every
number in the headline table, so the derivation is recorded here rather than assumed.

The tempting anchor is the run log's `All pods are running`, at 20:42:36. It is **52 seconds
late** — the gateway's first `/v1/completions` arrives at 20:41:44.330. Anchoring there and
accumulating per-stage durations shifted every boundary by up to 17% of a stage's length.

The correct derivation needs no anchor. The ladder configures 8 stages whose request counts
(rate x 300 s) sum to 22,200, and the harness independently reports 22,200 successes, so
sorting the arrival series and partitioning it on the cumulative counts recovers the
boundaries exactly. Observed rates then reproduce the configured ladder: 1.95, 4.87, 7.76,
9.69, 11.66, 14.52, 19.32, 2.01 against 2, 5, 8, 10, 12, 15, 20, 2.

The count identity is the gate, not the rate check. Partitioning is *positional*, so a
truncated arrival series does not lose the early stages — it shifts all of them. Deleting
2.2% of the requests from the front and re-partitioning yields stages 2–5 reporting 8.07,
10.01, 11.90 and 15.04 RPS, entirely plausible, while sitting 62 s off and reporting a stage-5
`dur_p95` of 15.192 s against a true 10.351 s — a 47% error with no local symptom.
`envoy_per_request.py` therefore hard-fails unless the count matches, rather than warning.
This matters because the access log is subject to kubelet rotation, which evicts oldest-first
and so would silently remove the *start* of a run window.

Raw latency against offered load is **non-monotonic** — 8 RPS was *slower* than 10 RPS:

| stage | RPS | mean latency | p95 |
|---|---|---|---|
| 2 | 8 | **7.711 s** | 8.739 |
| 3 | 10 | **7.138 s** | 7.999 |

That looks like measurement noise. It is not. Dividing by the replica count each stage
actually ran on — time-weighted, because the count changes mid-stage — the ordering
becomes monotone everywhere except at the two lowest-load points:

| RPS/replica | stage | RPS | replicas (t-wtd) | mean latency | p95 | ITL |
|---|---|---|---|---|---|---|
| 0.75 | 7 | 2 | 2.66 | 5.546 | 6.687 | 10.67 ms |
| 1.26 | 0 | 2 | 1.59 | 5.404 | 6.377 | 10.40 ms |
| 1.71 | 1 | 5 | 2.92 | 5.693 | 6.229 | 10.92 ms |
| 3.39 | 3 | 10 | 2.95 | 7.138 | 7.999 | 13.67 ms |
| 4.00 | 2 | 8 | 2.00 | 7.711 | 8.739 | 14.80 ms |
| 4.00 | 4 | 12 | 3.00 | 7.781 | 8.674 | 14.90 ms |
| 5.00 | 5 | 15 | 3.00 | 9.174 | 10.375 | 17.53 ms |
| 5.80 | 6 | 20 | 3.45 | 12.025 | 15.932 | 22.96 ms |

Both axes of this table are derived from the gateway access log, not from the run log or the
controller (`serving_replicas.py`; see "Stage windows" and "Which replica count" below for
why each earlier source was wrong).

Three things follow:

1. **The per-replica capacity model WVA is built on is empirically sound.** Stage 2 (8 RPS
   on 2.00 replicas) and stage 4 (12 RPS on 3.00 replicas) land at *exactly the same*
   4.00 RPS/replica, and their mean latencies differ by 0.9% (7.711 vs 7.781) despite a
   1.5x difference in absolute load. Two stages, half again as much traffic, same
   per-replica load, same latency. Latency is a function of per-replica load; the
   abstraction holds. That the two figures came out equal to three digits is luck, but it
   makes the comparison assumption-free — no interpolation is involved.
2. **Therefore the non-monotonicity is entirely the autoscaler's doing.** Nothing about
   the server got slower between stage 2 and stage 3. Stage 2 was slow because the
   cold-`prc` defect had just taken a replica away from it.
3. **The exception is at the bottom of the curve, where latency is not load-bound.**
   Stage 0 carries 68% *more* per-replica load than stage 7 (1.26 vs 0.75) yet is 2.6%
   *faster* (5.404 vs 5.546). Both sit far below saturation, where latency is dominated by
   per-token decode cost rather than queueing, so load barely registers. Read the curve as
   flat below ~1.3 RPS/replica and monotone above it — the six points from stage 1 upward
   are strictly ordered. The stage-7 penalty is plausibly the residue of draining the
   20 RPS backlog it inherited, on a fleet still shedding replicas underneath it; this run
   cannot separate those two.

### Which replica count, and why the controller's is the wrong one

There are two candidate sources for "how many replicas did stage N run on" and they
disagree. The controller log's `curr`, sampled once per 60 s optimisation cycle, is the
obvious one and the one an earlier revision of this table used. It is wrong twice over: its
resolution is 60 s, and it counts replicas the *workload object* has, which includes pods
that are Pending, pulling, or loading the model and therefore supplying no capacity at all.
For explaining latency that is exactly backwards.

The access log settles it without the controller: a replica is serving when the gateway is
routing to it, and `UPSTREAM_HOST` records that per request. Per-pod serving intervals:

| pod | first request | last request | requests |
|---|---|---|---|
| decode-97vw2 | 20:41:44.330 | 21:22:46.271 | 8025 |
| decode-wf2rf | 20:44:27.832 | 20:51:34.146 | 599 |
| decode-db6cw | 20:46:14.429 | 21:20:31.875 | 7351 |
| decode-qqbbn | 20:57:25.119 | 21:20:32.120 | 5489 |
| decode-k9hkl | 21:15:28.325 | 21:20:34.887 | 736 |

The two estimates agree to within 0.10 replicas (≤3%) on six of eight stages, which is the
cross-check that matters — two independent sources, same answer. They diverge exactly where
the fleet was in motion:

| stage | serving | `curr` | why |
|---|---|---|---|
| 0 | 1.59 | 2.27 | initial ramp: 97vw2 alone, wf2rf from 20:44:28, db6cw only for the last 38 s |
| 6 | 3.45 | 3.61 | k9hkl counted by the controller from 21:14:39 but served nothing until 21:15:28 |

Stage 0 is the significant one: `curr` overstates the fleet by 43%, because during the first
five minutes most of the counted replicas had not finished loading the model. Note too that
wf2rf — the replica the cold-`prc` cascade killed — served only 599 requests across its
entire 426 s life, which is corroboration from a third direction that it never carried a
fair share.

### Cost of the cold-`prc` scale-down, in user-visible latency

Stage 2 ran on 2.00 replicas because of the spurious scale-down cascade at 20:49–20:51.
Had it held the 3 replicas it entered stage 1 with, it would have run at 8/3 = 2.67
RPS/replica. Interpolating the monotone curve between stage 1 (1.71 -> 5.693) and stage 3
(3.39 -> 7.138) puts the counterfactual at **~6.5 s**.

    measured 7.711 s  vs  counterfactual ~6.5 s   ->  ~18% mean latency penalty

sustained for a full 5-minute stage. That is the price of the estimator defect expressed
in the only currency a user cares about. The interpolation is linear over a region where
the curve is close to linear, so treat it as an estimate, not a measurement.

### Cost of the scale-up lag, and how little of it is WVA's to fix

Stage 6 sat at only 16% higher per-replica load than stage 5 (5.80 vs 5.00) but showed
**31% higher mean latency** (12.025 vs 9.174) and **53% higher p95** (15.932 vs 10.375).
The excess is the window at the start of the stage during which the fleet was still 3
replicas and therefore at 6.67 RPS/replica — well past the near-linear region, so a queue
built and then had to drain.

That window is **171 seconds**, more than half the stage. Every timestamp below is measured,
the first from the arrival series and the last from `UPSTREAM_HOST`:

| component | measured | duration | who owns it |
|---|---|---|---|
| load steps 15 -> 20 RPS | 21:12:37.229 | — | the workload |
| controller emits `scale-up` 3 -> 4 | 21:13:39 | **61.8 s** | WVA |
| new pod serves its first request | 21:15:28.325 | **109.3 s** | HPA + scheduler + vLLM model load |
| | | **171.1 s total** | |

**About a third of the lag is WVA's** (62 of 171 s), which is the same fraction the earlier
anchor-error revision of this section reported, for entirely different numbers.

But the mechanism is not what that revision assumed, and the difference matters for tuning.
The 62 s is not phase delay waiting for the next cycle. A cycle ran at 21:12:39 — **1.8 s
after the load step** — and did not detect it: it reported throughput demand of 6597 tok/s,
*below* the 7793 the previous cycle saw at stage 5's steady state. The next cycle, at
21:13:39, saw 10918 tok/s and fired immediately. So the cycle that had the opportunity to
catch the step could not see it in its metrics, and the one that could see it acted with no
hesitation at all.

**Halving `GLOBAL_OPT_INTERVAL` would have recovered nothing here.** A cycle 1.8 s after the
step already existed and was blind. The binding constraint is upstream of the optimiser — in
scrape lag and rate-window width — not in how often the optimiser runs. This is a sharper
version of the same conclusion: tuning `GLOBAL_OPT_INTERVAL` is the *lesser* lever, and the
`prc` fix is worth more (an 18% penalty for a full 5 minutes). The remaining two thirds live
in pod startup, which only pre-warming or predictive scaling can touch.

What this run does *not* determine is whether the 21:12:39 blindness is scrape lag, the
collector's rate-window width, or sampling noise — the 6597 reading is low enough to suggest
noise is part of it. Separating those needs a run with the scrape interval and rate window
recorded and varied. Filed as an open question, not a finding.

### At 20 RPS the fleet sits exactly on the 0.85 watermark

Worth recording because it explains the 3->4 as something other than waste. At the
observed steady demand (~10,400 tok/s) on 3 replicas:

| `prc` used | util on 3 replicas | verdict |
|---|---|---|
| 4042 (the value at 21:13:39) | 0.858 | above 0.85 -> scale up |
| 4179 (the value 3 minutes later) | 0.830 | below 0.85 -> hold |

Both `prc` values are from the same run, minutes apart, within the estimator's own ±3%
steady-state noise. So **whether 20 RPS needs 3 or 4 replicas was decided by estimator
noise rather than by load.** This is the practical consequence of leaving `prc` unsmoothed
even after it converges: near a watermark, the noise *is* the decision. It also means the
4th replica was not obviously wrong — the run genuinely straddled the boundary.

## The harness output-token defect is per-request heterogeneous, not a scalar

Previously flagged as a ~1.78x inflation with the caveat that correcting percentiles by a
mean factor assumes uniform per-request error, "unverifiable without the lost file". The
per-stage data settles it **without** that file, and the assumption is false.

The scenario pins output length to `N(512, 20)` truncated to **[480, 550]**. So any
reported `output_len` outside that band is a harness artifact, not workload variation:

| stage | RPS | reported mean | inflation | reported min | reported max |
|---|---|---|---|---|---|
| 0 | 2 | 866.1 | 1.692 | **8** | **2898** |
| 1 | 5 | 890.8 | 1.740 | 55 | 3098 |
| 2 | 8 | 905.9 | 1.769 | 707 | 3115 |
| 3 | 10 | 899.9 | 1.758 | 683 | 3151 |
| 4 | 12 | 917.2 | 1.791 | 687 | 3128 |
| 5 | 15 | 910.1 | 1.778 | 533 | 3186 |
| 6 | 20 | 920.1 | 1.797 | **3** | 3125 |
| 7 | 2 | 898.0 | 1.754 | 249 | 3068 |

Every stage reports minima and maxima far outside `[480, 550]` — as low as **3** and as
high as **3186** where the true value cannot leave a 70-token band. The per-request error
therefore spans at least **0.006x to 6.2x**. A single scalar correction is invalid for any
percentile, and the mean factor itself drifts stage to stage (1.69–1.80).

### Server-side truth, and what it validates

Recovered from 650 vLLM `/metrics` scrapes (`server_token_truth.py`), summing per-pod
`max - min` across the 5 decode pods that existed during the run:

| | server (truth) | harness | ratio |
|---|---|---|---|
| input tok/s | 18,411.0 | 18,421.77 | **1.0006** |
| output tok/s | 4,602.1 | 8,181.66 | **1.778** |
| output tok/req | 511.5 | 866 (mean) | — |

The input row is the control: the harness's *input* accounting is accurate to **0.06%**,
which proves the pipeline is sound and the defect is specific to counting *generated*
tokens. Server output of 511.5 tok/req against the profile's 512 confirms `ignore_eos` is
working and the sampled-length distribution was honoured.

Method check: server total 11,354,715 vs expected `22,200 x 512 = 11,366,400` — the
scrape-gap undercount is **0.10%**, and the local harvest reproduced the totals *exactly*
despite missing 2 scrapes, because they fell mid-sequence rather than on a min or max.

### Which reported metrics are usable

| status | metrics |
|---|---|
| **usable as-is** | `request_latency` (all percentiles), `time_to_first_token`, `requests_per_sec`, `input_tokens_per_sec`, `prompt_len`, `benchmark_time_seconds` — all wall-clock or input-side |
| **wrong by ~1.78x, means only** | `output_tokens_per_sec`, `total_tokens_per_sec` — correct by substituting the server totals |
| **unusable** | `time_per_output_token`, `inter_token_latency`, `normalized_time_per_output_token`, `output_len` — every percentile divides by a per-request denominator that is wrong by a factor spanning three orders of magnitude |

The one defensible per-token figure is an **aggregate** that never divides per request:

    ITL = (mean request_latency - mean TTFT) / 512 true tokens

This is the `ITL` column in the stage table above (10.40 ms at 2 RPS rising to 22.96 ms at
20 RPS — a 2.2x degradation across the ladder). It is a mean; **no percentile version of
it exists** for this run. Cross-check: the reported ITL means track these values at
exactly the per-stage inflation factor (stage 0: 10.40/6.13 = 1.696 vs `output_len`
inflation 1.692; stage 6: 22.96/12.77 = 1.798 vs 1.797), which confirms the mechanism is
precisely a wrong denominator and nothing else.

## What the OOM cost

The harness pod was **OOMKilled at 21:30:09Z** (exit 137, 32Gi limit) while serialising
`per_request_lifecycle_metrics.json`, which is why that file is 0 bytes. Load had already
completed all 8 stages successfully, so **no measurement was lost, only its per-request
resolution**.

Unaffected: all scaling analysis (controller log captured independently), all 22,200
requests succeeded with **zero failures**, all 8 per-stage aggregates, the run summary,
and the server-side token truth.

Genuinely lost, and not recoverable without a re-run:

* per-request latency/TTFT distributions and CDFs (only the pre-computed percentiles survive)
* per-request output-token correction — hence the aggregate-only ITL above
* any per-request correlation, e.g. tagging requests served during the 90 s
  under-provisioned window at the start of stage 6

**This will recur on any long run with `report.request_lifecycle.per_request: true`.** It
is a run-configuration defect, not a one-off: 22,200 request records at this verbosity
exceeded 32Gi during serialisation. Needs either a memory bump or per-request capture
disabled for long runs — flagged for decision, not changed.

A second, unrelated hazard was ruled out along the way: the harness writes its report
**directly to the 20 Gi PVC** (`/requests/<run>_1`), with no node-ephemeral buffer in
front of it. The PVC never exceeded 308 M here only because the file was never written.
A successful run of this size would have needed ~11.9 GB of PVC headroom.

## Open items flagged during the run

* **RESOLVED — `tgt=1` at 20:51:37.** An earlier draft called this unexplained because
  `ceil(2669/2062) = 2`. That formula is not what the engine uses. Under the real rule
  TA's spare capacity (2374 tokens) exceeded one replica's capacity (2062), so TA itself
  claimed `2 - floor(2374/2062) = 1`. No external floor, no anomaly — the wrong model
  was mine. See the rule section at the top; verified 65/65 cycles (37 load-window).
* **Event recorder cannot emit Events for `VariantAutoscaling`** (10+ occurrences, fires
  on every scaling decision):
  `Could not construct reference, will not report event`
  `err="no kind is registered for the type variant.VariantAutoscaling in scheme"`
  Scaling is unaffected, but users get **no Kubernetes Events** explaining autoscaling
  actions. Independent of everything else here; worth its own issue.
* **RETRACTED — the "three levels" framing.** An earlier draft warned that three levels
  disagreed at 20:44:37 (TA internal target 1 / emitted decision 2 / actual replicas 3).
  Under the real rule TA claimed `3 - floor(2201/1740) = 2` and SAT also claimed 2, so
  the emitted 2 *was* the analyzers' claim. The "internal target 1" was
  `ceil(895/1739.7) = 1` — the same discarded formula. There are only **two** levels:
  emitted decision vs actual replicas (the latter set by HPA stabilisation).
* **RETRACTED — "one step per cycle".** The engine emits `curr - floor(sc/prc)`, which is
  unbounded. At 21:18:40 it emitted `4 -> 1`, a three-replica drop in one cycle. Earlier
  changes were single-step only because `floor(sc/prc)` happened to equal 1; this is not
  a structural property and must not be relied on.
* Stage 0 is **not** a clean 1-replica baseline in this run (TA left the fleet at 3
  before real load arrived), so the ~6 RPS/replica wall cannot be re-derived from it.
  A SAT-only ladder would be the cleaner run for capacity numbers. Partially superseded:
  the monotone per-replica curve now brackets the wall between **5.0 and 5.4
  RPS/replica** (latency 9.17 s -> 12.03 s across that gap), without needing a
  1-replica baseline. A SAT-only ladder would still pin it more precisely.
* **RESOLVED — the "~5 replicas at 20 RPS" sanity check.** That estimate used the
  early `prc` of ~2062 tok/s, which had not converged. Converged `prc` is **~4180
  tok/s** (~8 RPS/replica of raw token capacity), so 20 RPS needed **4** replicas, not
  5, and the cap of 10 never came close to binding. The general point stands — demand
  does track output tok/s (2669 at 5 RPS vs 5 x 512 = 2560, within 4%) — but any
  capacity arithmetic must use a converged `prc`, which is exactly the quantity this
  run shows is unreliable early.
* **`prc` remains unsmoothed even after convergence**, and the 20 RPS watermark analysis
  above shows that is not merely cosmetic: within its own steady-state noise band the
  estimator flips the replica decision. A smoothing/hysteresis fix should be evaluated
  against steady-state boundary behaviour, not only against the cold-start transient.

## Reproduction

```bash
make benchmark-run BENCHMARK_NAMESPACE=dhl-wva-209 \
  BENCHMARK_SPEC=guides/wva-sat2-tp1 BENCHMARK_HARNESS=inference-perf
# profile comes from the scenario's experimentProfile, so BENCHMARK_WORKLOAD is unset

# capture the controller log for the whole run -- the analysis is impossible without it
kubectl -n dhl-wva-209 logs -f --timestamps \
  deploy/workload-variant-autoscaler-controller-manager > ladder-controller.log

# per-cycle table (prc / demand / util / decision, with prc-jump flags)
python3 session-notes/scratch/decision_timeline.py [logfile]

# reconstruct every emitted decision from the analyzer payloads and assert the rule.
# Exits non-zero on any mismatch, so it doubles as a regression check that the
# engine's decision arithmetic has not changed between controller images.
python3 session-notes/scratch/verify_decision_rule.py [logfile] --minr 1 --maxr 10 -v
```

Client-side analysis. **The harness's own post-run step already pulls a complete local
copy** to `dean-<ts>/results/<run>_1/` — 709 files including all 465 raw decode scrapes,
verified equal to the PVC. Use that; no manual harvest is needed:

```bash
RUN=dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1

# server-authoritative tokens, because the harness's output counts are unusable
grep -H -E '^vllm:(generation|prompt)_tokens_total' $RUN/metrics/raw/*decode*_metrics.log \
  > vllm_tokens_complete.txt
python3 session-notes/scratch/server_token_truth.py vllm_tokens_complete.txt

# per-stage latency + the output-token defect quantified against the profile's true band
python3 session-notes/scratch/stage_table.py [--csv]

# per-request trace recovered from the gateway access log after the OOM destroyed the
# harness's own. --stage-grid derives the stage boundaries with no clock anchor and
# hard-fails if the request count does not match the configured ladder.
python3 session-notes/scratch/envoy_per_request.py --stage-grid
python3 session-notes/scratch/envoy_per_request.py --by-pod
python3 session-notes/scratch/envoy_per_request.py --csv > trace.csv

# check rotation headroom BEFORE the next run -- the gateway log accumulates across runs
python3 session-notes/scratch/envoy_per_request.py --rotation-budget

# time-weighted SERVING replica count per stage, routing-derived; --spans shows each pod's
# first/last request, which is the fleet timeline without the controller in the loop
python3 session-notes/scratch/serving_replicas.py [--spans]

# THE key table: latency joined to the serving replica count, plus the equal-load
# comparisons. Prints the controller's `curr` alongside as a cross-check.
python3 session-notes/scratch/stage_vs_replicas.py [--csv]
```

Run completed all 8 stages in **41:02** (load 20:41:44.330 -> 21:22:46.271), 22,200 requests,
**zero failures**. Harness then OOMKilled at 21:30:09Z during report serialisation; see
"What the OOM cost".

Canonical local copy: `dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1/`
(709 files, all 465 decode scrapes, verified complete against the PVC). There is also a
partial hand-harvest in `session-notes/scratch/ladder-run/` from before that was noticed —
**redundant and 2 scrape files short**; it reproduces every total identically because the
missing scrapes fell mid-sequence rather than on a per-pod min or max, but prefer the run
dir. `kubectl cp` of the whole run dir fails partway on this PVC (`unexpected EOF`), which
is why the hand-harvest fetched files individually.
