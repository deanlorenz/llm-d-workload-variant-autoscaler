---
to: scratch-poc
from: benchmark (ta-benchmark-coder, worktree `benchmark`)
date: 2026-08-08
subject: The 08-07 ladder run lost its per-request file to an OOM — but the gateway access log is a complete, better replacement
state: sent
---

# Ladder run 2026-08-07 — what survived, and what it is worth

A third run landed after the A/B pair covered in `scratch-poc__per-request-fetch-for-viz.md`:
an 8-stage ladder, 2 → 5 → 8 → 10 → 12 → 15 → 20 → 2 RPS, 22,200 requests, 0 failures, with
`maxReplicas` raised to 10. It exercised a real scale-up to 4 replicas and a full descent.

**The headline for you: this run's `per_request_lifecycle_metrics.json` is 0 bytes.** The harness
pod was OOMKilled while serialising it. So the §3/§4 fetch-and-stream recipe from the earlier
handoff does not apply here — there is nothing on the PVC to fetch.

**But a complete per-request trace exists anyway, in the istio-proxy access log**, and on three
counts it is *better* than the file that was lost. Everything below is verified against the actual
files; anything unverified is flagged as such.

I am the benchmark runner and cannot write outside my own worktree, so this was generated in
`benchmark/session-notes/handoffs/` for Dean to relay.

---

## 1. Run identifiers

| | |
|---|---|
| run dir | `dean-20260807-234050-328` |
| experiment | `inference-perf-1786135288-srzxlb_1` |
| namespace | `dhl-wva-209` |
| local copy | complete — 709 files, 465/465 decode metric scrapes, verified against the PVC |
| controller log | `session-notes/scratch/ladder-controller.log` (hand-captured; the harness does not capture it) |
| workload | `<run>/results/<exp>/ta_autoscale_ladder.yaml`, `base_seed: 42` |

Paths are relative to the benchmark worktree
(`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark`).

Note the harvest lesson: the harness's own post-run step had already populated the local run dir
**completely**, so the PVC fetch I also did was redundant. Check `<run>/results/<exp>/` before
reaching for the PVC.

## 2. The per-request trace, recovered from the gateway

`<run>/results/<exp>/logs/igw_pods.log` is the istio-proxy log for the inference gateway. The pod
is 8 days old, so the file spans a week — but inside the run window it holds **one access-log line
per request for all 22,200 requests**.

A parser and validator is at `session-notes/scratch/envoy_per_request.py`:

```bash
python3 session-notes/scratch/envoy_per_request.py --stage-grid   # boundaries + per-stage summary
python3 session-notes/scratch/envoy_per_request.py --csv          # one row per request
python3 session-notes/scratch/envoy_per_request.py --jsonl
python3 session-notes/scratch/envoy_per_request.py --by-pod       # routing attribution
```

Per request it yields: wall-clock arrival to the millisecond, e2e duration in ms, bytes in, bytes
out, HTTP status, envoy response flags, `x-request-id`, and the **decode pod that served it**.

### Why it beats the file that was lost

1. **No clock anchoring.** The lost file used a monotonic clock with an unknown origin, which is why
   the earlier handoff needed its whole §5 "clock trap" recipe. Envoy timestamps are wall-clock UTC,
   so per-request data joins directly to controller logs and HPA events with no arithmetic.
2. **Routing attribution.** `UPSTREAM_HOST` names the serving pod. The harness file never had this
   at any point, so per-replica analysis was previously impossible.
3. **Tokenizer-independent response size.** `bytes_sent` is bytes on the wire, so it is immune to the
   inference-perf output-token defect (§5).

### What it does not recover

Envoy sees one duration per request, not the token stream. **Per-request TTFT and per-request output
token counts are genuinely gone.** Both survive as distributions only, server-side (§4).

### Validation

| check | result |
|---|---|
| request count | 22,200 in-window POSTs vs 22,200 harness successes — exact |
| status / flags | all `200`, all envoy flags `-` — no truncation, no upstream resets |
| mean duration | 8817 ms vs 8850 ms predicted from the request-weighted stage means (0.37%) |
| per-stage mean | within 0.4% of the harness's own `lat_mean` at **every one** of the 8 stages |
| `bytes_sent` p50 | implies 511 output tokens at ~299 B/token vs a true mean of 512 (0.2%) |
| per-pod counts | envoy 8025 for `10.130.2.174` vs 8026 from that pod's own vLLM counter |

The last two rows are independent sources agreeing to ~1 request, which is why I am confident this
trace is the real thing rather than a plausible reconstruction.

## 3. Stage boundaries — and a 52 s error to not inherit

**The anchor recipe in the earlier handoff produces a wrong grid on this run.** Anchoring to the run
log's `All pods are running` gives a load start of 20:42:36. The first request actually arrives at
**20:41:44.330** — 52 s earlier, which is 17% of a 305 s stage.

The robust derivation, which `envoy_per_request.py` implements, is to partition the sorted arrival
series on the **cumulative per-stage request counts** (600, 1500, 2400, 3000, 3600, 4500, 6000, 600 —
these sum to exactly 22,200). The observed rate inside each derived window reproduces the configured
ladder, and it does here.

**But that rate check is a much weaker validation than it looks, so do not rely on it alone.**
Partitioning is positional, so a trace missing requests from the start does not lose the early
stages — it shifts *every* stage. I tested this by removing the first 499 requests (2.2%) and
re-deriving: stages 2–5 then report 8.07 / 10.01 / 11.90 / 15.04 RPS against a configured
8 / 10 / 12 / 15, i.e. they look perfectly healthy while being shifted by **62 seconds**. Only the
two endpoint stages give it away. And stage 5's `dur_p95` reads 15.192 s against a true 10.351 s —
a 47% error — because the shifted window absorbs requests from the 20 RPS stage.

The real gate is the **count identity**: in-window completion count must equal the request count the
harness independently reports. `assign_stages()` enforces it and exits non-zero on any mismatch;
`--allow-partial` overrides it and marks the grid unverified. Please do not bypass it without a
separate anchor.

| stg | RPS | n | start (UTC) | end (UTC) | obs RPS | dur_mean | dur_p95 | bytes_tx p50 |
|---|---|---|---|---|---|---|---|---|
| 0 | 2 | 600 | 20:41:44.330 | 20:46:52.023 | 1.95 | 5.390 | 6.419 | 152628 |
| 1 | 5 | 1500 | 20:46:52.023 | 20:51:59.728 | 4.87 | 5.678 | 6.204 | 152716 |
| 2 | 8 | 2400 | 20:51:59.728 | 20:57:08.826 | 7.76 | 7.679 | 8.658 | 152715 |
| 3 | 10 | 3000 | 20:57:08.826 | 21:02:18.428 | 9.69 | 7.117 | 7.983 | 152911 |
| 4 | 12 | 3600 | 21:02:18.428 | 21:07:27.225 | 11.66 | 7.755 | 8.628 | 152952 |
| 5 | 15 | 4500 | 21:07:27.225 | 21:12:37.229 | 14.52 | 9.139 | 10.351 | 152886 |
| 6 | 20 | 6000 | 21:12:37.229 | 21:17:47.823 | 19.32 | 11.974 | 15.824 | 152985 |
| 7 | 2 | 600 | 21:17:47.823 | 21:22:46.271 | 2.01 | 5.534 | 6.682 | 152631 |

Do not derive stage windows by accumulating `benchmark_time_seconds` from an anchor either — it
assumes zero gap between stages, and the drift reaches ~24 s by stage 7.

## 3a. Durability — this source is subject to log rotation

The access log is the gateway container's stdout, so it lives under kubelet log rotation
(`containerLogMaxSize` 10Mi × `containerLogMaxFiles` 5 by default ≈ 50Mi retained). Measured on this
log: **541 bytes per request**, so ~19,400 requests per 10Mi file.

```bash
python3 session-notes/scratch/envoy_per_request.py --rotation-budget
```

```
  size on disk              31.5 MB
  access lines              28.7 MB over 53071 requests (541 B/request)
  retention budget          52.4 MB (5 x 10Mi kubelet default)
  consumed                  60.1 %
  headroom                  20.9 MB = ~38619 more requests
```

**For this run nothing was evicted** — the log begins at container boot (istio startup lines at
`2026-07-30T16:48:43`, matching the pod's 8-day age) and the count identity holds exactly. Once
harvested to disk the trace is safe, and it is already harvested. So the analysis below stands.

The exposure is on *future* runs, and it is structural rather than incidental:

* The gateway is **shared, long-lived infra that accumulates every run** — 5,002 access lines on
  07-30, 15,081 on 08-03, 38,093 on 08-07. The budget is consumed monotonically across runs, not per
  run.
* **Eviction is oldest-first**, so overflow removes the *start* of the run window: the low-rate
  stages and the initial scale-up. That is the region autoscaling analysis cares most about, so the
  loss is biased against the signal rather than random.
* One more ladder-sized run (12.0 MB) takes this to ~83% of budget. A 20 RPS run for 30 minutes is
  ~36,000 requests ≈ 19.5 MB and would exceed the remaining headroom on its own.
* The harness captures these logs only *after* the run completes, so the window between last request
  and harvest is live exposure.

The 10Mi/5-file figures are kubelet defaults and I have **not** verified them against this cluster's
`KubeletConfig` — that is a cluster-scoped read outside my namespace, so I left it alone. If the
cluster narrows either value the real budget is smaller than the numbers above, so treat the headroom
as an upper bound.

## 4. Server-side metrics — where the lost distributions still live

`<run>/results/<exp>/metrics/raw/*_metrics.log` holds 649 Prometheus scrapes at a **~15.7 s
interval**, covering 5 decode pods plus the gaie-epp pod. These are cumulative per pod and reset to
zero on pod creation, so differencing consecutive scrapes gives **per-interval** values — i.e. time-
resolved distributions, not just run-wide ones.

Histograms present: `time_to_first_token_seconds`, `inter_token_latency_seconds`,
`e2e_request_latency_seconds`, `request_queue_time_seconds`, `request_prefill_time_seconds`,
`request_decode_time_seconds`, `request_inference_time_seconds`, `request_generation_tokens`,
`request_prompt_tokens`, `request_time_per_output_token_seconds`, `request_params_max_tokens`,
`iteration_tokens_total`.

Counters and gauges: `request_success_total`, `num_requests_running`, `num_requests_waiting`,
`num_requests_waiting_by_reason`, `num_preemptions_total`, `kv_cache_usage_perc`,
`generation_tokens_total`, `prompt_tokens_total`, prefix-cache hits/queries, NIXL transfer metrics.

**Bucket resolution varies, and it decides which of these are worth your time.** I checked the three
that matter:

* **TTFT — usable.** Boundaries at 0.02, 0.04, 0.06, 0.08, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5 s, and the
  actual values sit in 0.03–0.34 s, so 8 boundaries fall inside the live range. On pod `…97vw2`:
  median ≈ 0.098 s, p95 ≈ 0.25–0.3 s, p99 ≈ 0.5 s, nothing above 2.5 s. This is a genuine
  replacement for per-request TTFT at distribution level.
* **e2e latency — too coarse, do not use.** Boundaries jump 2.5 → 5 → 10 → 15 → 20 s, so the entire
  observed 5.4–12 s range spans three buckets. Envoy's exact per-request ms (§2) is strictly better.
* **generation_tokens — bounding only, but decisive.** Boundaries 200 → 500 → 1000. On `…97vw2`, all
  8026 requests land in (200, 1000] and 2333 of them ≤ 500. Too coarse to measure the shape, but
  see §5 for why that is still the most useful number in this file.

`request_queue_time_seconds` and `num_requests_waiting` are the direct measure of under-provisioning
harm and have no equivalent anywhere in the harness output.

## 5. The harness token defect, now proven rather than estimated

inference-perf re-tokenizes generated text and inflates the count. On this run the reported
`output_len` mean drifts 1.69× → 1.80× across stages, with per-stage min 3 and max 3186 — against a
profile that pins the true output to `N(512, 20)` truncated to **[480, 550]**.

Two independent server-side sources now settle what was previously a caveat:

* **The reported max is fabricated.** vLLM's own `request_generation_tokens` histogram puts every
  request in (200, 1000]; 3186 tokens would need a bucket that records zero. And 2333/8026 = 29.1%
  at ≤ 500 is what `N(512, 20)` truncated to [480, 550] predicts (~29%).
* **The per-stage "drift" is an artifact.** Envoy `bytes_sent` p50 is flat across all eight stages
  (152628 → 152985, a 0.23% spread). True output size does not vary with load, so a factor that
  drifts 1.69 → 1.80 by stage is measuring the harness, not the workload.

Consequence for plotting: **`output_len`, `time_per_output_token`, `inter_token_latency` and
`normalized_time_per_output_token` from this run's reports are unusable at any percentile**, and no
scalar correction fixes them — the error is per-request heterogeneous (reported values span 3 to
3186 against a true band of 70 tokens' width), so correcting a percentile by a mean factor is not
valid. Wall-clock latency columns are unaffected.

The one defensible aggregate per-token figure is `(lat_mean - ttft_mean) / 512`, computed in
`session-notes/scratch/stage_table.py`. It is a mean only; there is no percentile version.

## 6. Logs that look promising and are not

Two of the four captured logs are dead ends, so as not to spend time confirming it:

* **`logs/epp_pods.log`** (3732 lines) — has `x-request-id` and looks per-request, but contains only
  **13 unique request ids** across a 418 s window. It is a debug-level tail of the last few minutes,
  not the run.
* **`logs/modelserving_pods.log`** (828 lines) — spans **39 seconds** at 20:00:25–20:01:04 UTC, i.e.
  entirely *before* load started at 20:41:44. It is a startup tail.

`logs/pod_status.txt` is a post-run snapshot and lists only the one surviving decode pod, so it
cannot map the IPs on its own — the authoritative IP→pod mapping comes from the metrics collector's
own curl targets and is baked into `envoy_per_request.py`. IPs are recycled across pods
(`10.130.6.50` was a gpu-reservation pod), so that mapping is valid only for this run's window.

## 7. Recovery status, in one table

| quantity | recovered | source | fidelity |
|---|---|---|---|
| arrival time | **yes** | envoy `START_TIME` | exact, wall-clock, ms, all 22,200 |
| e2e latency | **yes** | envoy `DURATION` | exact ms; per-stage mean within 0.4% |
| serving pod | **yes** (new capability) | envoy `UPSTREAM_HOST` | exact |
| response size | proxy | envoy `bytes_sent` | p50 → 511 tok vs true 512 |
| output tokens | bounded only | `request_generation_tokens_bucket` | all in (200, 1000]; 29% ≤ 500 |
| TTFT | distribution only | `time_to_first_token_seconds_bucket` | 8 boundaries in range, ~15.7 s steps |
| per-token ITL | distribution only | `inter_token_latency_seconds_bucket` | no per-request version exists |
| queue time | distribution only | `request_queue_time_seconds_bucket` | no harness equivalent at all |

## 8. Per-pod routing, for the per-replica panel

Five decode pods served the run. Request share tracks pod lifetime monotonically, which is a useful
consistency check on any replica timeline you derive:

| pod | IP | envoy requests | share | scrapes |
|---|---|---|---|---|
| `…-97vw2` | 10.130.2.174 | 8025 | 36.1% | 184 |
| `…-db6cw` | 10.129.9.245 | 7351 | 33.1% | 133 |
| `…-qqbbn` | 10.130.6.54 | 5489 | 24.7% | 92 |
| `…-k9hkl` | 10.128.9.37 | 736 | 3.3% | 24 |
| `…-wf2rf` | 10.130.6.53 | 599 | 2.7% | 32 |

`--by-pod` breaks this down per stage, and the result **independently confirms the replica timeline
derived from the controller log** — which matters because those are two entirely unrelated sources:

```
stg  RPS    decode-97vw2   decode-db6cw   decode-k9hkl   decode-qqbbn   decode-wf2rf
  0    2             458             18              0              0            124
  1    5             510            515              0              0            475
  2    8            1193           1207              0              0              0
  3   10            1032           1023              0            945              0
  4   12            1184           1208              0           1208              0
  5   15            1499           1523              0           1478              0
  6   20            1792           1778            652           1778              0
  7    2             357             79             84             80              0
```

Stage 2 is served by exactly **2** pods, against a time-weighted 2.10 from the controller log. Stage 6
is served by 4, one of which joined mid-stage and took only 652 requests, against a time-weighted
3.61. Stages 3–5 are three pods splitting evenly. So the per-replica-load denominator in §9 is
corroborated by request routing, not just by the autoscaler's own account of itself.

**And on closer reading, routing does better than corroborate — it supersedes.** `UPSTREAM_HOST`
gives each pod's serving interval directly, so the replica count can be time-weighted from routing
alone, with no controller involvement and at per-request rather than 60 s resolution:

```
            pod         first          last   span_s      n
   decode-97vw2  20:41:44.330  21:22:46.271   2461.9   8025
   decode-wf2rf  20:44:27.832  20:51:34.146    426.3    599
   decode-db6cw  20:46:14.429  21:20:31.875   2057.4   7351
   decode-qqbbn  20:57:25.119  21:20:32.120   1387.0   5489
   decode-k9hkl  21:15:28.325  21:20:34.887    306.6    736
```

That is a better denominator than `curr` on the merits, not just a second opinion. `curr` is the
replica count the *workload object* carries, which includes pods that are Pending, pulling an image,
or loading the model — pods contributing to the count while supplying zero capacity. For explaining
latency that is backwards.

The two agree within 0.10 replicas on six of eight stages. They diverge exactly where the fleet was
in motion: stage 0 serving **1.59** vs `curr` 2.27 (the initial ramp — `curr` overstates by 43%,
because most counted replicas had not finished loading), and stage 6 serving **3.45** vs 3.61
(k9hkl counted from 21:14:39 but serving nothing until 21:15:28). Per-stage serving weights:
1.59, 2.92, 2.00, 2.95, 3.00, 3.00, 3.45, 2.66. `serving_replicas.py` computes this.

## 9. What the run found, so a chart has something to say

The engine's decision rule is now established and verified against **65/65 cycles** with zero
mismatches (37 load-window cycles plus 28 idle-tail cycles where `demand=0`):

```
rc = demand/0.85 - supply      if rc > 0:  tgt = curr + ceil(rc/prc)
sc = supply - demand/0.70      if sc > 0:  tgt = curr - floor(sc/prc)
                               else:       tgt = curr        (hold)
```

Re-runnable as a cross-image regression check via
`session-notes/scratch/verify_decision_rule.py`, which exits non-zero on any mismatch.

Two corrections worth carrying, because both were in my earlier drafts and both are wrong:
`ceil(demand/prc)` is **not** the rule and produced two phantom findings; and emitted changes are
**not** bounded to one replica per cycle (a 4→1 was emitted at 21:18:40).

**The client-side headline is that latency is monotone in load *per replica*, and non-monotone in
RPS.** The raw curve looks like noise — 8 RPS gives 7.68 s but 10 RPS gives 7.12 s — because stage 2
ran on 2.00 serving replicas while stage 3 ran on 2.95. Dividing by the replica count the stage
actually had makes it monotone, and the controlled comparison is as clean as this kind of data gets:
stages 2 and 4 land on **exactly the same 4.00 RPS/replica** (8/2.00 and 12/3.00) and their mean
latencies agree to **0.9%** — 7.711 s against 7.781 s — across a 1.5× difference in absolute load. No
interpolation, no "within 5%": same per-replica load, same latency. That is WVA's core abstraction
holding up on real data.

The full curve, sorted by per-replica load, with latency in seconds:

| RPS/rep | stage | RPS | serving reps | lat_mean | lat_p95 |
|---|---|---|---|---|---|
| 0.75 | 7 | 2 | 2.66 | 5.546 | 6.687 |
| 1.26 | 0 | 2 | 1.59 | 5.404 | 6.377 |
| 1.71 | 1 | 5 | 2.92 | 5.693 | 6.229 |
| 3.39 | 3 | 10 | 2.95 | 7.138 | 7.999 |
| 4.00 | 2 | 8 | 2.00 | 7.711 | 8.739 |
| 4.00 | 4 | 12 | 3.00 | 7.781 | 8.674 |
| 5.00 | 5 | 15 | 3.00 | 9.174 | 10.375 |
| 5.80 | 6 | 20 | 3.45 | 12.025 | 15.932 |

One caveat, at the bottom of the range: stage 0 carries 68% *more* per-replica load than stage 7
(1.26 vs 0.75) yet is 2.6% *faster* (5.404 vs 5.546). Both sit far below saturation, where latency is
per-token decode cost rather than queueing, so load barely registers — read the curve as flat below
~1.3 RPS/replica and monotone above it. The six points from stage 1 up are strictly ordered. The
stage-7 penalty is plausibly residual in-flight work inherited from the 20 RPS stage on a fleet still
shedding replicas, but this run cannot separate those two causes.

`stage_vs_replicas.py` computes the join and prints `curr` alongside the serving count as a
cross-check. Both it and the findings doc have been corrected for the 20:42:36 anchor error and now
derive their windows from the arrival series.

Full analysis: `session-notes/scratch/ladder-run-findings.md`.
Status: `session-notes/status/benchmark.md` §16.

## 10. Files, in one list

| path | what |
|---|---|
| `<run>/results/<exp>/logs/igw_pods.log` | **the per-request trace** — envoy access log, all 22,200 (rotation-exposed, §3a) |
| `<run>/results/<exp>/metrics/raw/*_metrics.log` | 649 scrapes, ~15.7 s, 5 decode pods + epp |
| `<run>/results/<exp>/per_request_lifecycle_metrics.json` | **0 bytes — the OOM casualty** |
| `<run>/results/<exp>/stage_N_lifecycle_metrics.json` | 8 surviving per-stage aggregates |
| `<run>/results/<exp>/benchmark_report*,_stage_N_*.yaml` | per-stage reports (observability block is run-wide, as before) |
| `<run>/results/<exp>/ta_autoscale_ladder.yaml` | the stimulus |
| `session-notes/scratch/ladder-controller.log` | per-cycle analyzer results + decisions, wall-clock UTC |
| `session-notes/scratch/envoy_per_request.py` | access-log → per-request CSV/JSONL + stage grid |
| `session-notes/scratch/verify_decision_rule.py` | decision-rule regression check, non-zero on mismatch |
| `session-notes/scratch/server_token_truth.py` | server-authoritative token totals from the scrapes |
| `session-notes/scratch/stage_table.py` | per-stage latency + the defect quantified |
| `session-notes/scratch/serving_replicas.py` | time-weighted **serving** replicas per stage + per-pod spans |
| `session-notes/scratch/stage_vs_replicas.py` | latency ÷ serving replicas, with `curr` as a cross-check |

The serving stack is still up in `dhl-wva-209` but the GPUs were released after the run, so
re-capture of anything cluster-side is cheap only while that lasts. Ask me for anything missing.
