# plan__ — dwell run executed; it does not dwell, it limit-cycles. Mechanism identified.

to: benchmark / TA testing planner
from: ta-benchmark coder+runner (worktree `benchmark`)
date: 2026-08-08
run: `dean-20260808-051912-230` (profile `ta_autoscale_dwell.yaml`, ns `dhl-wva-209`)
status of this handoff: **sent, unread** — sender does not edit after sending

---

## 0. One-paragraph summary

The dwell run launched and completed its load window. It did **not** produce a dwell in
kv 0.3–0.85. What it produced is better: a clean, fully-instrumented **limit cycle** with a
period of ~9 minutes, and — from the controller's own log — a specific, named mechanism for it
that is not a tuning problem. Per-replica capacity (`prc`) is looked up from a rolling-average
history **keyed on a discretised bucket of average output length**. When the bucket flips, an
unrelated history is swapped in, `prc` collapses by 10–13×, `util` explodes, and the controller
slams to `maxReplicas` — which causes the churn that makes the observation path fail again. That
is positive feedback through a measurement path, not a gain that can be turned down.

**This supersedes the central hypothesis of my earlier, already-delivered
`plan__benchmark-dwell-operating-point.md`.** That handoff argued the dwell might be unreachable
because a *tracking* controller holds kv low by construction, making steady-state kv
rate-invariant. That framing is wrong for the observed system: at this step size the controller
does not track at all. Please read that handoff's §"rate-invariance" as **superseded by this
document**, not as a parallel hypothesis. Its two proposed levers (SAT-alone-uncapped, deliberate
replica cap) remain worth having, but they are no longer the first thing to try.

---

## 1. The decision trace (authoritative, captured live)

`session-notes/scratch/controller-decisions-20260808-dwell.log` — 33 analyzer ticks, retroactive
to run start via `--since-time`, followed live. This closes the §17.8 open item "add controller-log
capture to the harvest path" for this run, and it is the only reason any of the below is knowable:
the ladder run lost its equivalent to log rotation.

Target trajectory (`tgt` from `scaling-decision`), one tick per minute:

```
02:19–02:22  1  1  1  1        entry rungs, 5 rps
02:23–02:25  4  7  10          scale-up  (peak #1)
02:26        10
02:27–02:30  9  4  2  1        scale-down
02:31        2                 (trough #1)
02:32–02:34  6  9  10          scale-up  (peak #2)
02:35–02:38  6  4  1  2        scale-down
02:39        2                 (trough #2)
02:40        9                 scale-up  (peak #3)
02:41–02:43  9  9  9           held
02:44–02:45  1  1              scale-down
02:46–02:51  1                 floor (minReplicas)
```

Peak-to-peak 02:25 → 02:34 = **9m12s**. (An earlier verbal report of mine said "~5 min"; that was
the peak-to-*trough* half-period. The full period is ~9 min.)

---

## 2. The mechanism, in the order the evidence forces

### 2a. `prc` collapses at *both* peaks, and demand was *falling* at the second one

Saturation analyzer, per tick (`supply`, `demand`, `util`, `prc`, reason):

| time | supply | demand | util | prc | reason |
|---|---|---|---|---|---|
| 02:23 | 329,011 | 974,024 | 2.96 | 329,011 | P1-obs |
| 02:24 | 329,011 | 1,882,870 | 5.72 | 329,011 | P1-obs |
| **02:25** | 76,044 | 2,682,201 | **35.27** | **25,348** | **P2-hist** |
| 02:32 | 658,022 | 1,538,533 | 2.34 | 329,011 | P1-obs |
| 02:33 | 658,022 | 2,349,653 | 3.57 | 329,011 | P1-obs |
| **02:34** | 206,046 | 2,306,010 | **11.19** | **34,341** | **P2-hist** |

At 02:25, `demand` rose 42% but `util` rose **6.2×**. At 02:34, `demand` **fell** (2,349,653 →
2,306,010) while `util` rose **3.1×**. In both cases the jump is almost entirely `prc` collapsing
from 329,011 to a value 10–13× smaller. **Both excursions to `maxReplicas` are artifacts of
capacity estimation, and the second one scaled up 3× while real demand was decreasing.**

### 2b. Why `prc` collapses — bucket-keyed history

`internal/engines/analyzers/saturation_v2/analyzer.go:289-334` (`computeK2`):

- `historyKey = "modelID|accelerator|gpuCount|outputBucket"`, where
  `outputBucket = classifyOutputLength(avgOutput)` (`types.go:60-69`).
- Bucket edges (`constants.go:34-40`): `short` < 100, `medium` < 500, `long` ≥ 500.
- The rolling average is appended to **only under Priority 1** (`analyzer.go:302-312`), i.e. only
  from saturated observations. Priority 2 reads that same per-bucket average.

This run's output distribution is **mean 512, sd 20** — i.e. sitting **12 tokens above the 500
medium/long edge with sd 20**. As the completed-request mix shifts, `avgOutput` crosses 500 and the
key changes, so the analyzer reads a rolling average belonging to a *different bucket*, populated by
a different workload.

**Status of this claim: strong mechanism-level hypothesis, NOT confirmed from logs.** The analyzer
never logs `outputBucket` or `historyKey` (grep of `analyzer.go` confirms: they are computed and
used, never emitted). I can show the collapse and I can show the code path that produces it; I
cannot yet show the bucket label flipping. See ask #1.

Independent of this run's excitation, the design issue stands on its own: **keying a capacity
history on a discretised bucket of a continuous, noisy quantity makes `prc` discontinuous in
`avgOutput`.** Any workload whose mean output sits near 100 or 500 inherits a step change in
estimated capacity. That is worth filing regardless of what my profile did.

### 2c. Capacity history is contaminated across runs

The controller pod `workload-variant-autoscaler-controller-manager-75fd9f8d-hv9g4` started
**2026-08-07T20:20:17Z with 0 restarts** — ~6 h before this run, spanning the 08-07 ladder.
`computeCapacityHistory` is an in-process map with no time-based invalidation.

Direct evidence: the **very first tick of this run** (02:19:09Z) reports `prc = 25,348` with reason
**P2-hist**. P2 requires `histAvg > 0`, and P1 had not yet fired in this run — so that average is
left over from the previous benchmark run. 25,348 is also exactly the value that `prc` collapses
back to at 02:25.

Consequences, which matter for the campaign and not only for the code:

- **Successive benchmark runs are not independent samples** unless the controller is restarted
  between them. The 08-07 ladder and this dwell run share history state.
- **Runner protocol change I am adopting** (no decision needed from you): restart the WVA
  controller deployment in `dhl-wva-209` before each benchmark run, and record its start time in
  the run notes. Cheap, in-namespace, non-destructive.

### 2d. Dispatch rate was missing for 100% of ticks — likely why demand is backlog-shaped

`collector/replica_metrics.go:1035`:
`Pod has engine metrics but no dispatch rate — possible pod/pod_name label mismatch`

**157 occurrences across 33 ticks** (~4.75/tick, i.e. every decode pod on every tick), first at
02:19:09Z — the first tick. This was **not intermittent; it was total**. Every scaling decision in
this run was made with no dispatch-rate signal for any replica.

That is the most plausible upstream cause of the demand defect below: with no arrival-rate input,
demand must be derived from what is left, and what is left is queue-shaped.

### 2e. Demand is a backlog measure, not an arrival rate

The decisive pair — **identical offered load, 48× different demand**:

| time | offered | demand | note |
|---|---|---|---|
| 02:40 | **2 rps** | 2,247,803 | backlog still draining → **scaled 2 → 9** |
| 02:41 | **2 rps** | 2,184,613 | held 9 |
| 02:42 | **2 rps** | 53,639 | backlog drained |
| 02:46 | **2 rps** | 38,407 | |

**At 02:40:11Z the client was offering 2 rps and the controller provisioned 9 replicas.** The
descent rung had begun ~02:37. The controller spent 02:40–02:43 holding 9 replicas against a
draining queue that the load generator had already stopped feeding.

Corroborating: demand read **1,882,870 at 1 replica** (02:24, 14 rps) and **333,172 at 10 replicas**
(02:29, 20 rps) — a 5.6× *fall* while offered load *rose*. A quantity that collapses when capacity
is added is measuring queue depth.

### 2f. The two analyzers contradict each other outright

At **02:41:12Z**, same instant, same variant:

- saturation: `supply 658,022  demand 2,184,613  util 3.32` → scale **up** hard
- throughput: `supply 9,020  demand 0  util 0  sc 9,020` → scale **down** all the way

The optimizer resolved this as `no-change` at 9. That is not a tie-break between two noisy
estimates; it is two analyzers describing incompatible worlds. Throughput's `demand` went
13,401 → **0** in one 60 s tick, immediately after:

```
throughput/analyzer.go:351  GPS mismatch persisted, clearing observation window for recalibration
                            {"threshold": 3}
throughput/analyzer.go:841  GPS mismatch detected  GPSObs 7,921  muDecModel 4,736  gpsErrPct 40.2
```

So throughput's model of decode speed is **29–40% off observation**, it responds by discarding its
window, and the emptied window reports `demand 0` → a spurious scale-down vote. Same failure family
as 2b: a fallback path that fires exactly when the system is interesting, and returns a value that
is not merely imprecise but qualitatively wrong.

### 2g. `supply` lags the replica count by ~1 tick, in both directions

- 02:31: decision `current=2`, supply 1,316,044 = 329,011 × **4** → over-count on the way down
  (readyReplicas was 2, pods from the 4→2 step still terminating)
- 02:41: decision `current=9`, supply 658,022 = 329,011 × **2** → under-count on the way up

So `supply` tracks neither desired nor ready replicas reliably on the timescale the controller
decides on. Combined with ~90 s+ actuation latency for a pod to become ready, the loop has
delay > 0, a more-than-proportional correction, and no damping. Over-counting during scale-down
additionally suppresses the scale-up a real queue warrants — the same territory as the Live-flag
gating asymmetry (scale-down veto is Live-gated, scale-up is not).

### 2h. Real kv ≈ 1.00 while the analyzer reported util 0.36

Measured directly off a replica (`vllm:kv_cache_usage_perc = 0.9987`, `num_requests_running=170`,
`num_requests_waiting=289`, all reason `capacity`) at the same time saturation reported
`util 0.360` and chose no-change (02:31). `util` is demand/supply in token units and is not the
same quantity as kv — but if the analyzer's purpose is to hold kv near `k_sat` = 0.80, its supply
model over-estimates capacity by roughly **3×** at the moment the engine is completely full.

Also note for the collector: vLLM 0.20.2 emits **`vllm:kv_cache_usage_perc`**, not
`gpu_cache_usage_perc` (the latter returns nothing). Metrics port 8200, container `vllm`. Worth
checking which name the WVA collector queries.

### 2i. Reason-code distribution — the observed path was available 18% of the time

Of 33 ticks: `P1-obs` **6**, `P3-k2` 2, `P2-hist` **25**. The controller ran on historical or
derived capacity for **82%** of its decisions, with dispatch rate absent for 100% of them.

---

## 3. My own contribution to this, stated plainly

Two of this run's artifacts are workload-design errors I introduced, and they should not be
attributed to WVA:

1. **Entry rungs too sharp.** I compressed them to 5 rps × 120 s then 14 rps × 180 s, against the
   ladder's 300 s steps, and budgeted 90–120 s for the transient on the assumption of a 1-replica
   step. The actual 1 → 10 cold start took ~5.5 min. The 20 rps rung's first half is therefore
   transient, which weakens it as the control I intended it to be. Driven by a request-count budget.
2. **Output mean 512, sd 20, straddling the 500 bucket edge.** This is what excites 2b. The
   mechanism is a real WVA defect, but a corrected profile should put the mean *well clear* of both
   100 and 500 (e.g. 700, or 300) so the two questions — "is `prc` bucket-discontinuous?" and "where
   does the system dwell?" — are separated rather than confounded.

Neither changes 2c–2i, which are independent of the workload shape.

---

## 4. Asks, in priority order

1. **Log `outputBucket` (or the full `historyKey`) on the `analyzer-result` line.** One field. It
   is the difference between 2b being confirmed and 2b being a good hypothesis, and it makes the
   next run diagnosable rather than re-litigable. Smallest-possible change with the largest
   diagnostic return of anything on this list.
2. **Decide the intended lifetime of `computeCapacityHistory`** (2c). Options as I see them:
   invalidate on a time window; persist deliberately with the key including something run-scoped;
   or leave in-process and document that consecutive experiments are not independent. Any of the
   three is fine for the code; only the third is a problem for the benchmark, and I have a runner
   workaround for it either way.
3. **Fact-find the `pod`/`pod_name` label mismatch** (2d). 100% miss rate on dispatch rate for
   every pod on every tick looks like a plain label-name bug rather than a modelling choice, and it
   is plausibly upstream of 2e. If demand becomes rate-shaped once dispatch rate is present, most
   of §2 changes character.
4. **Confirm which kv metric name the collector queries** (2h) against vLLM 0.20.2's
   `vllm:kv_cache_usage_perc`.
5. **The fallback-path family** (2b + 2f): both analyzers have a degraded path that fires precisely
   during churn and returns a qualitatively wrong value (10–13× low `prc`; `demand = 0`). Worth
   treating as one design question — what should an analyzer emit when it *knows* it has no valid
   observation — rather than two separate patches. A "no confident estimate, abstain" signal would
   be more useful to the optimizer than a confidently wrong number.

## 5. What I am *not* asking for

I am not proposing analyzer code changes; that is TA-coder/planner territory and I have deliberately
stopped at diagnosis. Nothing in this handoff has been implemented. No pushes have been made —
`benchmark` is 11 ahead of `origin/benchmark` and the fork's `wva-ta-benchmark` is 1 ahead, both
awaiting Dean's explicit per-push confirmation.

## 6. Where the evidence lives

- `session-notes/scratch/controller-decisions-20260808-dwell.log` — the 33-tick decision trace.
  **Not yet committed; it is the irreplaceable artifact of this run.**
- `session-notes/status/benchmark.md` §18 — this run's record, written for cold resume.
- Run dir `dean-20260808-051912-230/` — harness output, images actually used.
- Harness memory measurement: peaked ~**29.5 GiB** during report serialization, i.e. the 32Gi limit
  that OOM-killed the ladder was genuinely the binding constraint; the 96Gi bump was load-bearing,
  not precautionary.
