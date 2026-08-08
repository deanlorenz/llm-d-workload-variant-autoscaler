# plan__ — the dwell decision rule is answerable, and reading it literally would mislead

to: benchmark / TA testing planner
from: ta-benchmark coder+runner (worktree `benchmark`)
date: 2026-08-08
run: `dean-20260808-051912-230`
re: doorbell `benchmark__dwell-operating-point-in-plan.md` (marked `.WIP`, then `.DONE`)
supersedes: nothing — this is an **addendum** to `plan__benchmark-dwell-run-findings.md`, which is
still **unconsumed** in the handoffs dir. Sent as a separate file because a sender does not edit a
handoff it has already sent.

---

## 0. Why you are getting a second file

Your doorbell asked me to re-read §7.6 / §7.6.1 / §9.1 T11. I did. Two things follow that the
findings handoff does not contain, because I only established them after sending it:

1. **§7.6's decision rule is now answerable from real data — and the literal reading sends the plan
   the wrong way.** This is the important one.
2. **§7.6.1's own open question about the last held GPU has a concrete operational answer**, and
   acting on it has left a trap that the next run must clear.

Also, for calibration: **§7.6.1 records the run as "staged and unlaunched."** It has executed — Dean
approved with "run". That is expected staleness, not a complaint; you wrote §7.6 before my findings
handoff landed, and it is still queued for you.

## 1. Your headline is right. Your instrument is not.

§7.6 says the mid-band dwell is *"a controller-configuration lever, not a workload lever."* **This run
supports that**, and more sharply than §7.6 argues it. But the specific test §7.6 staged to prove it —
two rungs 1.3× apart, expect KV ≈ 0.67 on both — **fails on its own terms**, and the failure is not
informative in the direction the rule assumes.

First, the rungs land exactly where designed. Anchored at harness start 02:19:56Z:

| Stage | Rate | Window (UTC) |
|---|---|---|
| entry | 5 | 02:19:56–02:21:56 |
| entry | 14 | 02:21:56–02:24:56 |
| **rung A** (ladder control) | **20** | **02:24:56–02:30:56** |
| **rung B** (quantization sample) | **26** | **02:30:56–02:36:56** |
| descent | 2 | 02:36:56–02:48:56 |

**KV had to come from the engine, not the controller.** The analyzer's `util` is *not* kv-cache
utilisation — this run has real kv **0.9987** against a reported `util` **0.360**. Reading `util` would
have answered a different question while looking like it answered yours. Source used:
per-pod vLLM scrapes in `metrics/raw/`, metric `vllm:kv_cache_usage_perc` (**not**
`gpu_cache_usage_perc` — vLLM 0.20.2 renamed it). Extractor:
`session-notes/scratch/kv_per_rung.py`, read-only.

| Rate | n | kv_mean | kv_p50 | kv_p90 | kv_max | mean running | mean waiting |
|---|---|---|---|---|---|---|---|
| 5 | 8 | 0.084 | 0.084 | 0.186 | 0.186 | 25.5 | 0.0 |
| **14** (entry) | 16 | **0.623** | **0.990** | 0.999 | 0.999 | 122.3 | **266.4** |
| **20 — rung A** | 153 | **0.127** | **0.066** | 0.265 | 1.000 | 23.0 | 22.3 |
| **26 — rung B** | 119 | **0.248** | **0.098** | **0.994** | 1.000 | 44.9 | 27.0 |
| 2 (descent) | 229 | 0.120 | 0.011 | 0.409 | 1.000 | 21.4 | 8.6 |

Coverage reconciled rather than asserted: **803** scrapes = **569** usable decode + **80**
`503 ServiceUnavailable` (pods still starting) + **153** EPP-endpoint scrapes (carry no vLLM kv by
design — not a loss) + **1** `Failed to collect` at 02:31:11Z mid-collapse. Real decode loss is
81/650 = **12.5%**, and it **clusters in the scale-up transients** — the hot moments — so every mean
above is biased **downward**. Stating the direction because it does not rescue the numbers.

### 1a. What step 5 would actually return

> §7.6.1 step 5: *"Both ≈ 0.67 ⇒ rate-invariance confirmed ⇒ (a)/(b) becomes necessary; either rung
> in-band ⇒ the dwell is had."*

Executed literally: rung A **0.127**, rung B **0.248**. Neither ≈ 0.67, neither in-band. So step 5
returns **"rate-invariance refuted"** and hands off to step 6 — the 32 RPS follow-up that needs PVC
headroom first. **I believe that is the wrong move, and it is the one concrete risk in leaving the rule
as written.**

### 1b. Why the rule cannot work as posed

**The mean of a limit cycle is not a steady state.** Rung B is the proof: mean **0.248** but p90
**0.994** and max **1.000**. The distribution is bimodal — saturated when replica count is low,
near-empty at 10 — because the run traverses 1↔10 replicas *inside each rung* (§18.1 trajectory;
during rung A alone the target went 10,10,9,4,2,1,2 **at a constant 20 RPS**). No single number
describes an operating point here. **"Steady-state KV" is not a well-defined quantity for this system
at these settings**, so the two-rung comparison is malformed regardless of which numbers come back —
including the case where one *had* read 0.67, which would have been a coincidence of averaging, not a
dwell. Fixing the §18.2 `prc` oscillation is a **precondition** for the rule to mean anything, not a
follow-up to it.

### 1c. The one real dwell in the run was an accident, and it tells you the mechanism

The only stage that parked KV in-band was the **14 RPS entry rung**: mean **0.623**, p50 **0.990**,
mean waiting **266**. That is the stage I criticised in my own findings (§18.11) as too short and too
sharp — I had written it off as a design error of mine.

It dwelt because **the replica count was lagging the load** (1→4 while 14 RPS was already offered), not
because of anything about the rate. So: **the dwell is produced by replica lag, not by offered rate.**
That is a stronger version of your §7.6 claim — it is not merely that rate is the wrong lever, it is
that the *response speed and ceiling of the controller* are the whole story. It also reframes the
(a)/(b) fork: (b) a cap works because a cap **is** enforced lag; (a) works only if SAT's watermarks
actually bind, which §18.7 shows they did not here (SAT and TP contradicted each other outright and
the optimizer resolved to no-change).

**I am not choosing (a) or (b).** Still yours and Dean's, per §7.6.

## 2. §7.6.1's GPU open question — answered, with a trap you must clear

§7.6.1: *"one GPU remains held by the decode replica's `minReplicas=1` steady state — a separate open
question (coder's §17.8 item 3)."*

**Answered.** Pausing the ScaledObject releases it; `minReplicas` is not a floor you have to live with
between runs. Done on Dean's instruction, ~16 min after the load phase ended:

```
kubectl annotate scaledobject unsloth--608e585a-instruct-decode-scaler -n dhl-wva-209 \
  autoscaling.keda.sh/paused-replicas="0" --overwrite
```

`dhl-wva-209` now holds **0 GPUs**, verified by enumerating every container's
`limits."nvidia.com/gpu"` in the namespace. Scaling the Deployment directly does **not** work — KEDA
restores it within seconds.

🚨 **The trap:** it is *paused*, not scaled down. KEDA holds it at 0 indefinitely. **A run launched
without un-pausing produces a flat 0-replica trace that reads as a legitimate no-scaling result** —
silent, not loud. Restore with the trailing `-`:
`kubectl annotate scaledobject unsloth--608e585a-instruct-decode-scaler -n dhl-wva-209 autoscaling.keda.sh/paused-replicas-`
then confirm `PAUSED` reads `<none>`. **This should become a fifth precondition in §7.6.1** alongside
the four already there.

## 3. §7.6.1 precondition 4 is necessary but not sufficient — the extractor is silently broken

> §7.6.1: *"run `post_run_analyze.sh` **immediately** after the run — the ladder run has no
> `metrics/processed/wva_*` precisely because that step was not run promptly and the controller log is
> read from a rotating buffer."*

I ran the rotation-sensitive step first, before touching anything, and **rotation was not the problem
this time** — the controller log still reached back to 2026-08-07T23:12:51Z, far before run start.

It still produced a broken file. `dump_wva_target_timeseries.py` reported **"41 snapshots"** and looked
healthy, but **0 of 41** rows had `utilization`, `totalSupply`, `totalDemand`, `requiredCapacity` or
`spareCapacity`. Cause is **log-format drift**, not timing: its `ANALYSIS_PAT` matches
`saturation/engine_v2.go:\d+ V2 saturation analysis completed`, which this controller build **never
emits** (0 occurrences in 872 lines). It now logs `analyzer-result` (`engine_v2.go:695`, 108 lines =
2 per tick, one per analyzer) and `scaling-decision` (`engine_v2.go:744`, 54). The fields exist under
**renamed keys** — `supply`, `demand`, `util`, `rc`, `sc` — plus per-variant `prc` / `reason` and
`scaleUpThreshold` / `scaleDownBoundary` that the tool does not know about. `DECISION_PAT` still
matches, which is why `primary` populated and the failure **looked like success**.

Two consequences:

- The end-of-script anti-clobber guard only fires when `samples` is **empty**. Here it was 41
  non-empty rows, so **a partial parse will overwrite a good earlier file.** The guard defends against
  rotation, not against drift.
- Promptness cannot fix a pattern that no longer matches, so **precondition 4 does not achieve what it
  is written to achieve.** Part of the ladder's missing `metrics/processed/wva_*` may be this, not
  rotation — worth re-examining before the story is settled.

**Not fixed.** It is a focused single-file change (add the `analyzer-result` pattern, map the five
renamed keys, key on `analyzer == "saturation"`, capture `prc`/`reason`), but it is outside the scope
Dean set for this round and needs his approval per the substantial-single-file-edit rule.
**No data is at risk:** the raw controller log is committed at
`session-notes/scratch/controller-decisions-20260808-dwell.log`, so the timeseries can be regenerated
offline at any time — no cluster, no rotation dependency.

## 4. Asks

1. **Do not execute §7.6.1 step 5 as written.** Replace the "≈ 0.67 on both rungs" test with something
   that survives a limit cycle — at minimum report the **distribution** (p50/p90/max), not a mean, and
   gate the whole question on the §18.2 oscillation being fixed first.
2. **Add un-pausing the ScaledObject as a fifth §7.6.1 precondition** (§2 above). It is the one that
   fails silently.
3. **Re-mark §7.6.1's "staged and unlaunched" as executed**, and note that §7.6's headline survives
   while its test does not (§1c).
4. **Decide whether precondition 4 should also require verifying the extractor's output is populated**,
   not merely that the script ran. "41 snapshots" was a green light for a file with no data in it.
5. Route the tool fix in §3 to Dean for approval, or tell me to raise it with him directly.

## 5. Explicitly not asking for

No (a)/(b) choice from me. No push — `benchmark` is 12 ahead of `origin/benchmark`, fork
`wva-ta-benchmark` 1 ahead, both awaiting Dean's explicit per-push confirmation. No change to any
already-delivered handoff.

## 6. Where the evidence lives

- `session-notes/status/benchmark.md` **§18.16** — this material, with the scrape reconciliation.
  **§18.15** — GPU release and the un-pause path. §18 is the live section; §17.12 is historical.
- `session-notes/scratch/controller-decisions-20260808-dwell.log` — 872 lines, 54 `scaling-decision`
  records, 02:19:09Z→03:12:15Z. The 33-tick analysis window is 02:19–02:51 (the load phase); later
  ticks are idle at 1 replica.
- `session-notes/scratch/kv_per_rung.py` — the per-rung KV extractor, with its reasoning in the
  docstring.
- `dean-20260808-051912-230/results/inference-perf-1786155590-ogc71v_1/metrics/raw/` — 803 scrapes.
