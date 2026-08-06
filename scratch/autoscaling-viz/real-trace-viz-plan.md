# Real-trace visualization — input inventory + fetch/extraction plan

**Status:** DRAFT. **Rev 4** — retargeted onto **already-benchmarked** results (Dean, 2026-08-06:
*"we are talking about fetching already benchmarked results… We should look for actual results in
Ofer's fork. Mine were just test runs."*). Panel 4 still deferred until the input inventory is
done across several runs.

**Target corpus (§1.0):** Ofer's runs — 11 committed comparison studies in his fork (catalogue +
figures, raw data gitignored) and **9 runs with full raw detail still live on the `biran`
`workload-pvc`** on pokprod001. Two harness formats are in play (§1.2).

**Spec-validation reference only (NOT the trace to visualize):**
`benchmark/dean-20260803-052634-197/results/inference-perf-1785724033-d5lhav_1/` — a *test run*.
Its value is that every parsing rule, the capacity formula, and the ITL-window scan in §§3–8 were
validated against it twice. All claims from it are tagged **[ref]**. Local working copy at
`scratch/autoscaling-viz/real-trace/staircase-20260803/` (smalls + 217 raw scrapes; `metrics/raw/`
gitignored; 50-record `per_request_head.json` instead of the 4.2 GB file).

**⚠️ One trace of many.** The extractor's job is explicitly *not* to assume any run's properties —
§9 makes per-run capability a machine-emitted report rather than an assumption.

**Cold-resume entry point:** read §1.0 (what data exists and where), then §1.2 (which reader a run
needs), then §8 (extractor spec). §§2–7 are the derivations behind §8 and can be skipped on a
resume.

---

## 0. What changed

### 0.1 Rev 4 (2026-08-06/07) — retarget + a second harness reader

| # | Rev 3 said | Rev 4 |
|---|---|---|
| 1 | reference run = our `dean-*` staircase | that is a **test run**; target corpus is **Ofer's** runs (§1.0). `dean-*` demoted to spec-validation only |
| 2 | one extractor, inference-perf schema | **two readers** — `inference-perf` and `guidellm` (§1.2); the run dir declares which via `run_metadata.yaml: harness_name` |
| 3 | three-clock anchoring problem (§2) | **inference-perf only.** guidellm records carry `request_start_time`/`request_end_time` as **epoch floats on the same clock as the scrape filenames** → anchoring is a no-op there |
| 4 | client/server token inflation must be corrected (§3) | **inference-perf only.** guidellm runs use `ignore_eos:true` + `max_completion_tokens` → every successful request emits exactly the configured output length; no inflation factor exists or is needed |
| 5 | re-derive replicas/EPP/capacity ourselves | **use Ofer's preprocessing where present** (Dean's instruction). Verified: all of it except `dump_hpa_desired_timeseries.py` is already on our `upstream/main` (§1.1a) |
| 6 | drain/scale-down absent, a **[ref]** gap | **closed** — the surviving PVC runs contain scale-down and multi-step scale-up with measured boot lag (§1.0b) |
| 7 | viz dir is ours | must be **shareable** — Ofer clones Dean's fork and runs it on his own machine/data (§14), and bundles publish to a **result branch** (§15) |

### 0.2 Rev 3 (2026-08-05/06) — extraction plan finalized

| # | Rev 2 said | Rev 3 |
|---|---|---|
| 1 | one global queue = `Σ vllm:num_requests_waiting` | **three distinct queues** (§4); that sum is the *per-vLLM* queue, the router-artifact one |
| 2 | EPP `average_queue_size` independently corroborates it | **retracted** — same signal, averaged (§4.3) |
| 3 | ITL from `generation_tokens_total` gauge ratios, r²=0.393 | **direct histogram** `vllm:inter_token_latency_seconds` (§5) |
| 4 | saturation ≈ kv→1.00 | **kv ≥ 0.85** (Dean; = the sim's `sat_frac`) — §5.1 |
| 5 | single global `ITL = A·k + B` | **piecewise, with a validity window** `[y, 0.85]`; A, B change above it (§5.2) |
| 6 | no scale-down ⇒ near-structural | property of **[ref] only**; schema carries scale-down first-class (§8.3) |
| 7 | KV capacity assumed | **measured exactly** from `vllm:cache_config_info` (§6) |
| 8 | preemption unknown | **present and sustained** under load; breaks the ρ model at the top (§7.2) |
| 9 | panel-4 treatment shortlist | **deferred** (§11) |

---

## 1. Source artifacts

### 1.0 Target corpus — where already-benchmarked data actually is

Two disjoint pools. **(a) is the catalogue, (b) is the data.**

**(a) Ofer's fork — analysis committed, raw data gitignored.**
`biranofer/workload-variant-autoscaler`, branches `comparison-wva-keda-epp-20260722` and
`validate/rate-anchored-k2`. **11 comparison studies, 47 files, 6.8 MB — every one is
`comparison.md` + `img/*.png` only. Zero csv/json/yaml/log.** So the fork gives us the
experiment design, the run IDs, and Ofer's own conclusions — but **no trace to replay**.

| study | shape / question | legs |
|---|---|---|
| `comparison-wva-keda-epp-20260722` | WVA (Sat-2) vs KEDA-EPP, fair comparison | 10 |
| `comparison-two-variant-20260725` | two-variant WVA cost-aware vs KEDA-EPP | 2 |
| `comparison-single-variant-stepped-20260727` | multiplier 1 vs 2 vs KEDA-EPP, stepped ramp | 3 |
| `comparison-1000x250-16x20x24ext20-20260728` | 1000/250, sustained crossover rate | 7 |
| `comparison-1000x250-r10x16-20260728` | rates 10/12/14/16 | 2 |
| `comparison-1000x250-r16x40-20260728` | rates 16/24/32/40 | 2 |
| `comparison-single-variant-1000x250-20260728` | 1000/250 stepped ramp | 2 |
| `comparison-single-variant-2800x700-20260728` | 2800/700 stepped ramp | 2 |
| `comparison-100x1000-16x20x24ext20-20260729` | **decode-heavy 100/1000** | 2 |
| `comparison-1000x250-rateanchoredk2-20260731` | rate-anchored k2 (#1501) ON vs OFF | 7 |
| `comparison-symmetric1000x1000-pods1120s-20260801` | **symmetric 1000/1000**, k2 ON/OFF | 4 |

All are `inference-perf`, `unsloth/Meta-Llama-3.1-8B-Instruct`, namespace `biran`, TP=1, min 1 /
max 10, ~39,600 requests per leg. Run dirs are named exactly like ours
(`biran-20260728-162745-184/results/inference-perf-…_1/`). Corroboration worth keeping: **avg pod
startup 81–98 s across 7 legs**, matching our 92/95/96 s → boot lag ≈ 90 s is established across
~10 independent samples.

**Vocabulary caveat:** Ofer calls 1000/250 "prefill_heavy". At 4:1 out:in that is still
decode-dominated *in time*, so even his "prefill-heavy" runs likely do **not** probe the `y > 0`
ITL knee of §5.2. That gap stands for the whole corpus.

**(b) pokprod `biran` `workload-pvc` (20 Gi, Bound) — full raw detail, 9 runs.**
Read-only check 2026-08-06, authorized by Dean. Reachable via the already-running pod
`access-to-harness-data-workload-pvc` (image `ghcr.io/llm-d/llm-d-benchmark:v0.7.0`), which mounts
the PVC at `/requests`:

```bash
oc exec -n biran access-to-harness-data-workload-pvc -- ls -la /requests
```

**These are NOT the runs behind the 11 studies.** They are `guidellm`, `Qwen/Qwen3-0.6B`, dated
**Aug 3–4 2026** — later than, and a different harness from, the `inference-perf` studies (Jul 22 –
Aug 1). This confirms Dean's assumption that the detailed files for the comparison studies were
not kept. What *is* here is a clean 9-run ladder of autoscaling experiments:

| run | workload | dur | ready replicas | `results.json` | raw scrapes |
|---|---|---|---|---|---|
| `guidellm-1785761095-gqg3ie_1` | symmetrical | 678 s | *(no metrics collected)* | 116 MB | 0 |
| `guidellm-1785778282-mz6rr1_1` | symmetrical | 680 s | 1–1 (no scaling) | 116 MB | 86 |
| `guidellm-1785829403-9me38v_1` | symmetrical | 681 s | 1–1 (no scaling) | 116 MB | 86 |
| `guidellm-1785831797-d5nicr_1` | symmetrical | 707 s | 1–3, mean 2.2 | 157 MB | 150 |
| `guidellm-1785846558-7wyjik_1` | symmetrical | 702 s | 1–2, mean 1.7 | 157 MB | 123 |
| `guidellm-1785848460-9cn8su_1` | symmetrical | 748 s | 1–4, mean 2.8 | 157 MB | 190 |
| `guidellm-1785856861-71ay4b_1` | decode_heavy | 772 s | **1–9, mean 6.2** | 123 MB | 372 |
| `guidellm-1785858243-828dgl_1` | decode_heavy | 768 s | 3–7, mean 5.6 | 131 MB | 328 |
| `guidellm-1785859604-upf3j2_1` | decode_heavy | 803 s | **3–8, mean 6.6** | 154 MB | 402 |

**Recommended first target: `guidellm-1785856861-71ay4b_1`** — widest scaling range (1→9), starts
from a single replica, 372 scrapes, decode-heavy. **Second: `…-upf3j2_1`** — contains a genuine
**scale-down** (desired 4→3 at t≈32 s) before ramping 3→6→7→8, so it exercises the drain path that
was the hard FAIL in Rev 3 §9.

Verified from `…-upf3j2_1`'s `replica_status_timeseries.json` (`snapshots`, 51 × 16 s): desired
4→3→6→7→8, ready trailing by **64–79 s** per step — a directly measured boot lag, per step, on a
real trace.

Workload (from `results.json.args`): `prompt_tokens 1000`, `output_tokens 4000`, `poisson`,
`rate 20.0`, `max_seconds 600`, `ignore_eos true`. So **uniform 4000-token outputs** — 1:4 in:out,
the decode-heavy end the whole Ofer corpus lacks. 3945 successful / 572 **incomplete** / 0 errored
on the 71ay4b leg: the incompletes are requests still generating when `max_seconds` cut the run,
and must be accounted as truncated, not failed (§8.1 `outcome`).

⚠️ **This PVC is Ofer's and is not ours to write.** Everything above was obtained with `oc get`,
`oc get -o jsonpath`, and `oc exec -- ls/cat/python3` reads. Copying data out is a read too, but
any fetch should be pull-to-local (`oc cp` / `oc exec -- tar c`), never a write into `biran`.

### 1.1a Ofer's preprocessing is already ours — verified

Dean: *"If ofer alrady does some of the preprocessing, then you can use it. Verify that his script
are also in our benchmark harness."* Verified against `upstream/main:hack/benchmark/`:

| script | on our `main`? |
|---|---|
| `post_run_analyze.sh` (5-step driver, **defaults NS to `biran`**) | ✅ |
| `dump_wva_target_timeseries.py` | ✅ |
| `dump_capacity_demand_estimate.py` | ✅ |
| `dump_epp_throughput.py` | ✅ |
| `dump_wva_full_timeseries.py` | ✅ |
| `plot_two_variant_pipeline.py` | ✅ |
| `postprocess.py`, `add_variant.py` | ✅ |
| `dump_hpa_desired_timeseries.py` | ❌ **only Ofer has it** |

His other extras are KEDA scenario files (PR #1435 territory), not preprocessing. So: **reuse
`post_run_analyze.sh` output wherever it exists.** It writes
`metrics/processed/{wva_target_timeseries,capacity_demand_estimate,epp_throughput,wva_metrics_timeseries}.json`
plus `metrics/graphs/two_variant_v2_full_pipeline.png`, and `plot_two_variant_pipeline.py` proves
those small JSONs alone carry desired-vs-actual replicas, HPA target, EPP queue and throughput, and
capacity/demand — most of panels 2–4 at ~1 MB/run instead of 4 GB.

**Gap that matters:** `post_run_analyze.sh` was **not** run on any of the 9 PVC runs (each has only
`metrics_summary.json`, `pod_startup_times.json`, `replica_status.json`,
`replica_status_timeseries.json`), nor on our staircase test run. Its docstring says step 1 must run
*promptly* after the benchmark because kubectl rotates the controller log buffer — so for those runs
the WVA decision timeseries is **unrecoverable**. Actionable for the benchmark effort: make
`post_run_analyze.sh` part of the run, not a manual afterthought.

**Also do not mistake `metrics_summary.json` for a timeseries.** It is keyed by pod (plus
`_aggregated`) but each metric holds only `{mean, stddev, min, p25…p99, max, count}` — **no time
axis**. Time-resolved vLLM/EPP data comes only from `metrics/raw/*_metrics.log`.

### 1.2 Two harness formats — the reader is chosen by the run dir

`run_metadata.yaml: harness_name` declares it. Everything downstream of the reader is shared.

| | `inference-perf` | `guidellm` |
|---|---|---|
| where | Ofer's 11 studies; our `dean-*` staircase | the 9 PVC runs; our `dean-20260731-*` |
| per-request file | `per_request_lifecycle_metrics.json` (up to 4.2 GB) | `results.json` (116–157 MB) |
| record path | flat list | `benchmarks[0].requests.{successful,incomplete,errored}[]` |
| arrival / depart | monotonic seconds from run start → **needs the §2 anchor** | `request_start_time` / `request_end_time`, **epoch floats — same clock as scrape filenames, anchor is a no-op** |
| output tokens | client count inflated 1.5–2× vs `server_usage.completion_tokens` → §3 correction | `output_metrics.text_tokens`, exact (`ignore_eos` + `max_completion_tokens`) |
| TTFT | derive | `time_to_first_token_ms` |
| true ITL | `(end_time − output_token_times[0]) / completion_tokens` | `(last_token_iteration − first_token_iteration) / (token_iterations − 1)`; `inter_token_latency_ms` also given |
| truncation | n/a | `incomplete[]` — cut off by `max_seconds`, count as truncated |
| stage structure | scenario yaml stages | single `profile` + `rate` (no stages) |

Per-record timing dict (guidellm): `resolve_start`, `request_start`, `first_request_iteration`,
`first_token_iteration`, `last_token_iteration`, `last_request_iteration`, `request_end`,
`resolve_end`, `finalized`, `request_iterations`, `token_iterations`.

⚠️ Records embed the full prompt text — that is why the files are >100 MB for only ~4.5 k requests.
Stream them (`ijson`) or slice; never `json.load` the whole file on a laptop.

### 1.3 Reference-run artifacts (`inference-perf`, **[ref]**)

| Artifact | Gives | N / cadence |
|---|---|---|
| `per_request_lifecycle_metrics.json` (**4.2 GB**) | per-request arrival, depart, tokens, per-token times | 7920 |
| `metrics/raw/*_metrics.log` (20 MB, 217 files) | per-pod vLLM + EPP scrapes | 82/pod @ 15 s |
| `metrics/processed/replica_status_timeseries.json` | desired / ready / available (key: `snapshots`) | 82 @ 15 s |
| `run_metadata.yaml` | `harness_start 02:27:17Z` (epoch 1785724037), `harness_delta PT1286.4S` | — |
| `summary_lifecycle_metrics.json` | `benchmark_time_seconds 1107.80` | — |
| `pod_startup_times.json` | boot 95 s / 92 s | 2 pods |
| `output_token_correction.json` | `global_inflation_factor 1.7714` | — |
| scenario yaml (`ta_autoscale_staircase.yaml`) | stage rates + durations | — |

### 1.1 Signal completeness is not guaranteed

Dean: *"for various reasons we sometimes don't get all signals from all vLLMs. The EPP metrics
are usually there."* **[ref]** EPP 82 scrapes, `bvfqv` 82, `zxzlj` 49, plus a 31 s hole at
t=373→404 where a whole round is missing. So: **pod series are sparse**; never assume a pod has
a sample at a given `t`; prefer EPP for system-level series and treat per-pod vLLM as best-effort
enrichment.

---

## 2. Time anchor — three clocks

Demand trace = **monotonic** (≈1153688.x); replica snapshots = **ISO wall**; raw scrapes =
**epoch in the filename**.

`harness_delta` (1286 s) ≠ load duration (`benchmark_time_seconds` **1107.8 s**) — a 178 s gap,
almost entirely **post**-load teardown/collection, so δ ≈ 8–16 s. Do not anchor "first arrival at
`harness_start`".

**Pin δ by cross-correlation**, not arithmetic: the demand-derived arrival-rate step function
against the observed queue/gen-rate step function. The staircase edges are sharp — **[ref]** queue
onset 408, collapse 757. Independent landmarks: `zxzlj` created 450, ready 542, first traffic 549.

---

## 3. Token counts — the inflation is per-request, not a scale factor

Client `output_tokens` vs server `completion_tokens` differ **1.52–2.00× per request**. Server
counts cluster at 481–529 ≈ 512 (`ignore_eos`); the client's 221–3150 spread is a tokenizer
artifact.

1. **Use `server_usage.completion_tokens`.** `global_inflation_factor 1.7714` is an *aggregate*
   correction — never apply it per record.
2. `len(output_token_times) == client output_tokens` — the timing array is in **client**-token
   space. So `mean(diff(array))` is wrong; true per-request ITL is
   `(end_time − output_token_times[0]) / completion_tokens`. The array stays valid for TTFT and
   relative shape. *(Mostly moot now — `vllm:inter_token_latency_seconds` is authoritative, §5.)*
3. Aggregate check: `6496.4 / 1.7714 ≈ 3667 tok/s` = `7919 × 512.9 / 1107.8` ✓.

---

## 4. The three queues

Dean's taxonomy, mapped to metrics that actually exist in these scrapes:

| # | Queue | Meaning | Metric | Present? |
|---|---|---|---|---|
| **(a)** | **Global EPP flow-control** | admitted, not yet dispatched. **This is the PoC's global queue** | — | **ABSENT** |
| **(b)** | **Dispatch** | dispatched to a vLLM, unanswered. **Mixes waiting + serving** | `inference_objective_running_requests` | ✅ |
| **(c)** | **Per-vLLM waiting** | each engine's own backlog. 0 with a good router; 100+ on a thundering herd | `vllm:num_requests_waiting` | ✅ |

### 4.1 (b) ≡ Σ_pods vLLM(waiting + running) — verified

Across all 70 populated snapshots the two agree to **±9 (usually ±3)** — scrape skew only.
**[ref]** at t=624: EPP 783; pods 202+213 waiting + 186+182 running = 783. So (b) is exactly what
Dean described, and it is fully accounted for by the pods.

### 4.2 (a) is not exposed — recover it by subtraction

There is **no flow-control depth metric** in this EPP build (only
`inference_extension_scheduler_attempts_total` and `..._e2e_duration_seconds`, which are
pick-path latency, not depth). Therefore:

> **(a) = L(t)_demand − (b)_dispatch**, with `L(t) = arrivals(t) − departures(t)` from the
> per-request trace.

This is a **required** extraction step — the only route to the quantity the PoC models.
**[ref]** it looks small: peak latency decomposes as 74 s vLLM queue + 0.24 s prefill + 24 s
decode ≈ 98 s against an observed max of 114 s, leaving ≲15 s unaccounted. Nonzero but an order
of magnitude under (c). Must be measured per run, never assumed.

### 4.3 Retraction — EPP did not independently corroborate the queue

Rev 2 claimed `inference_pool_average_queue_size` (peak 588) was an independent check on the
summed vLLM waiting (peak 617). **It is the same signal**: `average_queue_size` = *mean over
ready pods* of `vllm:num_requests_waiting`; `inference_pool_per_pod_queue_size` is its per-pod
breakdown. EPP scrapes vLLM — there is no second measurement.

### 4.4 ⚠️ The averaging trap — `average_queue_size` falls on scale-up for free

| t | ready | per-pod queues | `average_queue_size` |
|---|---|---|---|
| 546 | 1 | bvfqv 588 | **588** |
| 561 | 2 | bvfqv **616**, zxzlj 0 | **318** |

Real backlog *rose* (588→616, still all on bvfqv, which had offloaded nothing) while the metric
fell 46%. **A scaler keyed on `inference_pool_average_queue_size` sees instant phantom relief the
moment a pod goes Ready, before any work moves.** A summed or max-based signal has no such
failure mode. → §12.4, worth raising outside this work.

### 4.5 Router oscillation — real per Dean, absent **[ref]**

`inference_pool_per_pod_queue_size` after `zxzlj` joins: `616/0 → 460/120 → 345/116 → 286/247 →
202/213 → 122/137 → 43/53`. A ~50 s equalization transient, then within ~10% for the rest of the
run. So collapsing per-pod into one global queue costs almost nothing **here** — a property of 2
pods under steady load, not of the router. *(This also corrects Rev 2's "bvfqv 69 vs zxzlj 31,
asymmetric" — an artifact of averaging over bvfqv's solo period.)*

The extractor must keep per-pod series and emit a **dispersion/oscillation statistic** (§9) so
this is detected rather than silently averaged away on runs where it does happen.

---

## 5. Saturation and the ITL validity window

### 5.1 Saturation = kv ≥ 0.85 (Dean; = the sim's lowering coefficient)

**[ref] the threshold is untestable on this run** — 0.80, 0.85 and 0.97 all select the *same* 34
intervals, because the utilization range has a hole in the middle:

| kv band | n | `run` | ITL | gen tok/s | prefill | preempt/s | pfx-hit |
|---|---|---|---|---|---|---|---|
| 0.00–0.05 | 28 | 3.4 | 12.2 ms | 389 | 52 ms | 0.00 | 59.8% |
| 0.05–0.15 | 47 | 16.6 | 13.1 ms | 1365 | 72 ms | 0.00 | 10.5% |
| 0.15–0.30 | 16 | 41.4 | 16.6 ms | 2585 | 61 ms | 0.00 | 29.2% |
| 0.30–0.50 | 3 | 64.0 | 31.6 ms | 1806 | 74 ms | 0.00 | 11.2% |
| 0.50–0.70 | **0** | — | — | — | — | — | — |
| 0.70–0.80 | 1 | 144.0 | 34.4 ms | 1565 | — | 0.00 | 16.9% |
| 0.80–0.85 | **0** | — | — | — | — | — | — |
| 0.85–0.95 | **0** | — | — | — | — | — | — |
| 0.95–1.01 | 34 | 182.0 | 48.4 ms | 3952 | 242 ms | **1.50** | 4.9% |

The 5→12 RPS step jumps kv≈0.3 → kv≈1.0. **Consequence: a replay of this run can never exercise
the sim's 0.85 ceiling** — it only ever sits at 30% or 100%. This is the single biggest input gap.

**Saturation-band values (kv ≥ 0.85, per pod, n=34)** — the scaling-relevant numbers:

| | sub-saturation (kv ≤ 0.40) | **saturated (kv ≥ 0.85)** |
|---|---|---|
| `num_running` | 24.7 | **182 mean / 195 max** |
| ITL | 14.6 ms | **48.4 ms** |
| gen tok/s | 1682 | **3952** |
| prompt tok/s | 6791 | **15368** |
| completed req/s | 3.44 | **7.27** |
| e2e latency | 7.5 s | **51.4 s** |
| prefill | 67.7 ms | **241.9 ms** |
| decode | 7.3 s | **24.1 s** |
| vLLM queue wait | 0.18 s | **27.1 s (max 74.1)** |
| preemptions/s | **0.00** | **1.50** |

### 5.2 The linear model has a *validity window* — `[y, 0.85]`

Dean: *`ITL = A·k + B` holds for kv < 0.85 and for kv > y, where y is a knee. Decode-heavy →
y=0, so it crosses at B. Prefill-heavier → y ≈ 0.2–0.4. A, B change.*

Fitting against `run` **[ref]**:

| window | n | A (ms/req) | B (ms) | r² |
|---|---|---|---|---|
| kv<0.85, all intervals | 74 | 0.200 | 9.73 | 0.401 |
| **kv<0.85, `\|Δrun\|≤25`** | 68 | **0.135** | **10.37** | **0.769** |
| kv≥0.85 (saturated) | 34 | **1.034** | **−139.8** | 0.620 |

Three things confirmed:

1. **y = 0 holds for this decode-heavy shape.** The fitted intercept **10.37 ms** lands on the
   independently measured empty-system ITL of **11.5 ms** (head sample, 50 requests, zero wait).
   The line does cross at B, as predicted.
2. **A and B change above the window.** The saturated segment is **7.7× steeper** with a
   **nonphysical B = −140 ms** — its intercept is not a B at all. Any single-line fit spanning
   both regimes is meaningless.
3. **The stability filter is load-bearing:** r² 0.401 → 0.769. A 15 s histogram delta straddling
   a ramp mixes regimes. **Excluding fast-changing intervals is mandatory, not cosmetic.**

**Where the break actually sits.** Extrapolating the `kv<0.85` line upward:

| `run` | kv | ITL pred | ITL obs | obs/pred |
|---|---|---|---|---|
| 156 | 0.87 | 31.5 | 36.6 | 1.16 |
| 174 | 0.99 | 33.8 | 39.4 | 1.16 |
| 185 | 1.00 | 35.3 | 50.3 | **1.42** |
| 192 | 0.99 | 36.3 | 60.1 | **1.65** |

A flat ~16% offset (the fit spans only run 3–64 and extrapolates 3× out), then it tears open at
run≈185 — **coincident with preemption switching on** from 0.00 to 1.5/s, not with kv=0.85 (kv is
already 1.00 by then). So the *upper* break is set by preemption on this run. The two middle rows
rest on few samples; treat the 1.16 as indicative.

**Net: this run yields a trustworthy B and a solid saturation band, but cannot calibrate A** — the
linear regime is sampled only below kv 0.3. Getting A needs a workload that *dwells* in kv 0.3–0.85.

> That is the same requirement already on the planner's plate for the TA-lead experiment
> (Phase-A sub-scale sweep of KV util 0.15→0.85, ≥10 OLS samples, `KSpread ≥ 0.30`), reached from
> the WVA side. Independently confirmed here from the metrics side; one sweep serves both.

### 5.3 Max concurrency ≠ max throughput

Run-binned **[ref]**: throughput peaks near `run≈169` at **4584 tok/s** and falls to **3641** by
`run≈185` — a ~20% loss. The ITL model cannot produce that: `tput = run/ITL` is monotone, and it
reproduces every bin up to 169 (predicted 4520 vs measured 4584). What breaks it is the
preemption confined to the top bin. So the KV-bound ceiling of ~187 (§6) is the **thrash** point;
the scaling-relevant ceiling is the knee below it.

Caveat: that comparison is n=9 vs n=26 and the run-bins mix ramp with drain. **Candidate, not
established** — confirming it needs a run that holds steady near the knee instead of overshooting.

---

## 6. Capacity model — `I + 0.5·O`, validated to <1%

Exact, no assumptions: `vllm:cache_config_info` gives `num_gpu_blocks="6426"`, `block_size="64"`,
`gpu_memory_utilization="0.85"`, `enable_prefix_caching="True"`.

**KV capacity = 6426 × 64 = 411,264 tokens.**

```
footprint/req = I·(1 − pfx_hit) + O/2 = 2049·0.95 + 256 = 2202 tok
411,264 / 2202                                          = 186.8 requests
```

**Observed [ref]: 182 mean / 195 max at kv 0.993–1.000.** Zero free parameters. Dean's
memory-bound model holds, and gives panels 5 / 1b an **exact** ceiling in place of the sim's
`⌊sat_frac·C⌋` heuristic:

> `max_concurrency = num_gpu_blocks × block_size / (I·(1−pfx_hit) + O/2)`

**Memory-bound vs compute-bound is a per-run classification, not a model** (Dean: *"we cannot
really estimate, can only observe"*). Discriminator: kv saturating at ~1.0 while concurrency
plateaus → memory-bound (**[ref]**). Concurrency plateauing with kv well below 1.0 →
compute-bound, and this formula will *over*-predict. `vllm:iteration_tokens_total` is the direct
probe for how much prefill rides in each engine step.

---

## 7. Prefill and preemption

### 7.1 Prefill is directly measured, and inflates ~4–5×

Rev 2 reconstructed service-time components. Unnecessary — vLLM exposes all of them as
histograms: `request_prefill_time_seconds`, `request_decode_time_seconds`,
`request_queue_time_seconds`, `inter_token_latency_seconds`, plus `time_to_first_token_seconds`,
`e2e_request_latency_seconds`, `request_inference_time_seconds`, `iteration_tokens_total`.

**[ref]** prefill 52–74 ms sub-saturation → **242 ms** saturated (peak 512 ms). Two separable
causes: prefix-cache hit rate collapsing (a 0%-hit 2048-token prefill costs ≈66 ms by FLOP count,
and the low-concurrency low-hit point measures 67 ms ✓), then contention with decode adding a
further ~3–4×. The reverse direction shows too: at fixed `run`≈185 and kv=1.00, ITL swings
38.7–70.9 ms — prefill chunks stealing decode steps. **That is the mechanism behind ρ being
shape-conditioned.**

Because `request_queue_time_seconds` is measured separately, **prefill = TTFT − queue_wait at any
load** — Dean's "TTFT captures prefill exactly when wait is 0" holds, and we don't need the wait≈0
restriction. Head-sample cross-check (queue=0): TTFT median 62 ms ≈ the 67 ms baseline ✓.

**[ref] is decode-dominated regardless:** 0.24 s prefill vs 24 s decode ≈ **1% of service time**,
even at 4–5× inflation. So ρ here is a *decode* number. Dean's prefill-heavy regime — *"not enough
decode rounds to absorb prefill; ITL becomes prefill time"* — needs **short outputs**, not just
long inputs. Ofer's `prefill_heavy_15rps_900s.yaml.in` (4K in / **1K** out) is still
decode-dominated by this arithmetic; the interesting regime wants something like 4K in / 64 out.
Worth saying before anyone runs "prefill heavy" and gets a decode-shaped result.

### 7.2 Preemption — a real mechanism the PoC does not model

`vllm:num_preemptions_total` runs **1.5/s sustained** through the saturated band (**0.00**
sub-saturation) — order 600 events over ~330 s, i.e. roughly **15% of the requests in that
window**. vLLM evicts a *running* request under KV pressure and re-queues it; its prefill is
recomputed, at a ~5% cache-hit rate.

Three consequences: it is a third contributor to §7.1's prefill inflation; it is the cause of
§5.3's throughput decline; and **the PoC assumes a request in service runs to completion** —
preemption discards completed work and returns the request to the queue. Same *class* of effect as
Dean's scale-down kill question, but it fires during ordinary congestion with no scaling event.
→ §12.2 decision: model it, or declare out of scope and note the resulting optimism.

---

## 8. Extraction script — **FINAL** (`extract_real_trace.py`)

Touch the 4.2 GB file once, offline; emit two small artifacts. Run-agnostic: everything
trace-specific is *measured and reported* (§9), never assumed.

```
usage: extract_real_trace.py --run <run-dir> [--out <dir>] [--no-per-request]
outputs: <out>/bundle.json      # the data
         <out>/coverage.json    # what this run can and cannot support (§9)
```

`--no-per-request` skips step 2 (the 4.2 GB pass) — yields everything except `requests[]`,
`L(t)`, and therefore queue (a). Useful for a fast capability sweep across many runs.

### 8.1 Bundle schema

```
meta:     {run, model, namespace, harness_start, delta_load_offset, load_duration_s,
           stages:[{rate, dur}], shape:{in_tok, out_tok},
           engine:{num_gpu_blocks, block_size, kv_tokens, gpu_mem_util, prefix_caching}}
requests: [{t_arr, t_dep, in_tok, out_tok, ttft, itl_true, outcome}]   # out_tok = SERVER
replicas: [{t, desired, ready, available}]
system:   [{t, q_flow, q_dispatch, q_engine, running, kv_mean, gen_rate, ready}]
          # q_flow = L(t) − q_dispatch (§4.2) ; q_dispatch = (b) ; q_engine = Σ (c)
pods:     {<pod>: {created_t, ready_t, setup_s,
                   series:[{t, running, waiting, waiting_by_reason, kv,
                            gen_rate, prompt_rate, ok_rate, itl_ms, prefill_ms,
                            decode_s, qwait_s, ttft_s, preempt_rate, pfx_hit,
                            stable}]}}                                  # SPARSE (§1.1)
derived:  {sat_band:{threshold:0.85, n, run_mean, run_max, itl_ms, gen_tok_s, req_s,
                     preempt_s, qwait_s, kv_mean},
           itl_fit:{y_lo, y_hi:0.85, A_ms_per_req, B_ms, r2, n, B_extrapolated:bool,
                    B_measured_ms, rho},
           itl_fit_sat:{A_ms_per_req, B_ms, r2, n},
           break_point:{run, kv, obs_over_pred},
           capacity:{kv_tokens, pfx_hit, footprint_tok, max_conc_pred, max_conc_obs,
                     regime:"memory-bound"|"compute-bound"},
           tput_knee:{run, gen_tok_s, confident:bool},
           lags:{decision_s, boot_s, drain_s},
           router:{disp_p50, disp_p95, oscillation_flag},
           preempt_total, scaledown_observed, inflation_factor}
```

### 8.2 Parsing rules (all three are load-bearing)

1. **Strict metric-name match.** Require the character *after* the name to be `{` or ` `:
   ```python
   def strict(line, name):
       return line.startswith(name) and len(line) > len(name) and line[len(name)] in '{ '
   ```
   This is the Rev-1 bug: `startswith('vllm:num_requests_waiting')` also matches
   `..._waiting_by_reason{reason="deferred"} 0.0`, which appears later and wins on last-match,
   silently zeroing the queue. Sum across label sets for counters that carry them
   (`request_success_total{finished_reason=…}`).
2. **Counter deltas within one pod only**, guarding `b < a` (restart) and `dt <= 0`. Reject
   intervals with `dt > 40 s` (spans a scrape gap — §1.1). Histograms: difference `_sum` and
   `_count` and divide, never read the cumulative ratio.
3. **Stability flag per interval.** `stable = |Δrunning| ≤ 25` between the bracketing snapshots
   **and** the interval does not straddle a stage boundary **and** no replica became Ready inside
   it. Only `stable` intervals feed any fit (§5.2).

### 8.3 Steps

1. `run_metadata.yaml` → `harness_start`; scenario yaml → stages; `summary_lifecycle_metrics.json`
   → `benchmark_time_seconds`; `vllm:cache_config_info` → `meta.engine`.
2. **Stream** the per-request file: `json.JSONDecoder().raw_decode` over a refilled buffer —
   **never** `json.load` (needs ~10 GB). Keep `start_time`, `end_time`, `input_tokens`,
   `server_usage.completion_tokens`, `output_token_times[0]` + its length, and the error/outcome
   marker. Drop `response`, `raw_response`, `response_chunks`, and the full timing array.
3. `replica_status_timeseries.json` → `replicas[]`, ISO → seconds. Detect **both** directions of
   `ready` change — scale-down is first-class even where absent.
4. Parse `metrics/raw/*_metrics.log`, epoch from filename, per §8.2. Pull the vLLM gauges
   (`num_requests_running`, `num_requests_waiting`, `num_requests_waiting_by_reason`,
   `kv_cache_usage_perc`), counters (`generation_tokens_total`, `prompt_tokens_total`,
   `request_success_total`, `num_preemptions_total`, `prefix_cache_hits_total`,
   `prefix_cache_queries_total`), histograms (`inter_token_latency_seconds`,
   `request_prefill_time_seconds`, `request_decode_time_seconds`, `request_queue_time_seconds`,
   `time_to_first_token_seconds`, `e2e_request_latency_seconds`, `iteration_tokens_total`), and
   from EPP `inference_objective_running_requests` + the `inference_pool_*` family (avg queue
   size, per-pod queue size, kv utilization, ready pods).
5. **Solve δ** by staircase-edge cross-correlation (§2) → `meta.delta_load_offset`; put all
   wall/epoch series on the load axis.
6. Build `system[]`: `q_engine = Σ` per-pod waiting; `q_dispatch` = EPP (b);
   **`q_flow = L(t) − q_dispatch`** (§4.2). **Never average a queue across pods** (§4.4).
7. Derive, in this order:
   a. `sat_band` = stable intervals with `kv ≥ 0.85` (§5.1).
   b. `itl_fit` — scan `y_lo ∈ {0, 0.1, 0.2, 0.3, 0.4}`, fit `ITL = A·run + B` on stable
      intervals in `[y_lo, 0.85]`, keep the best r² subject to `n ≥ 8`; record the chosen
      `y_lo` and set `B_extrapolated = (y_lo > 0)`. Cross-check `B` against `B_measured_ms`
      (mean ITL of stable intervals at `kv < 0.05`). `rho = (A·max_conc_pred + B)/B`.
   c. `itl_fit_sat` — same fit on `kv ≥ 0.85`, reported separately and never merged (§5.2).
   d. `break_point` — lowest `run` where `ITL_obs / ITL_pred > 1.25`.
   e. `capacity` (§6) + `regime` classification.
   f. `tput_knee` — `argmax` of `gen_rate` over stable run-bins; `confident` only if the bins
      either side have `n ≥ 8` (§5.3).
   g. `lags`, `router` dispersion (§4.5), `preempt_total`, `scaledown_observed`.

### 8.4 Self-checks (fail loudly)

- request count and `benchmark_time_seconds` match the summary (**[ref]** 7920/7919, 1107.8 s);
- `Σ completion_tokens / duration ≈ 3667 tok/s`; `requests_per_sec ≈ 7.148`;
- **(b) ≡ Σ_pods(waiting + running) within ±10** (§4.1) — the strongest structural check;
- `gen_rate ≈ running / ITL` per interval (**[ref]** 182/0.0484 = 3760 vs 3952 measured);
- Little's law `L ≈ λ·W` against measured `request_queue_time_seconds`;
- `B` vs `B_measured_ms` within ~15% when `y_lo = 0` (**[ref]** 10.37 vs 11.5);
- `max_conc_pred` vs `max_conc_obs` within a few % (**[ref]** 186.8 vs 182/195);
- **[ref]** decision lag 47 s, boot 94 s (`pod_startup_times` 92 s ✓).

---

## 9. Coverage report — what each run can support

`coverage.json` (+ a printable table) makes "fetch other runs and see where we are" mechanical.
One row per capability, computed not assumed:

| Capability | Test | **[ref] verdict** |
|---|---|---|
| Calibrate **A** | ≥8 stable intervals spanning ≥3 kv bands inside `[y_lo, 0.85]`, kv span ≥0.4 | **FAIL** — only kv<0.3 populated |
| Trust **B** | ≥5 stable intervals at kv<0.05 | **PASS** (n=28) |
| Characterize saturation | ≥10 stable intervals at kv≥0.85 | **PASS** (n=34) |
| Exercise the 0.85 ceiling | ≥3 intervals in kv 0.80–0.90 | **FAIL** — band empty |
| Locate the throughput knee | `tput_knee.confident` | **FAIL** — n=9 one side |
| Scale-**down** present | any `ready` decrease | **FAIL** |
| Drain-vs-kill measurable | scale-down **and** requests ending after it | **FAIL** |
| Queue (a) material | `max(q_flow)` vs `max(q_engine)` | **small** (≲15 s of budget) |
| Router oscillation | per-pod dispersion sign changes | **absent** (balanced after 50 s) |
| ρ model valid at top | preempt rate in sat band ≈ 0 | **FAIL** — 1.5/s |
| Regime | kv at concurrency plateau | **memory-bound** |
| Signal completeness | scrapes/pod, gap list | 82 / 49 / 82; one 31 s gap |
| Shape | `in_tok` / `out_tok` → predicted `y` | decode-heavy, y=0 ✓ |

**[ref] scores 4 PASS / 6 FAIL.** It is a good *panel* trace (the full lag→queue→boot→drain story
is there) and a poor *calibration* trace. That distinction is exactly what the report exists to
make visible per run.

### 9.1 What the target corpus is expected to fix (verify, don't assume)

Predictions to be replaced by real `coverage.json` output once the extractor runs:

| Rev-3 FAIL | expected to clear on | why |
|---|---|---|
| Scale-**down** present | `guidellm-…-upf3j2_1` | desired 4→3 observed directly (§1.0b) |
| Drain-vs-kill measurable | same | the scale-down is at t≈32 s, mid-load, so in-flight requests straddle it |
| Locate the throughput knee | `…-71ay4b_1` (1→9 replicas) | 9 distinct supply levels on one workload |
| Calibrate **A** / the 0.85 ceiling | **still at risk** | needs *dwell* in kv 0.3–0.85, which no run in either pool was designed for |
| Genuinely prefill-dominated | **no candidate** | Ofer's 4:1 "prefill_heavy" is decode-dominated in time; the PVC runs are 1:4 |

So the two structural gaps that survive the retarget are **(i) mid-band kv dwell** and **(ii) a
short-output shape**. Both are *workload-design* asks, not fetch problems — they belong to the next
capture, which is exactly Dean's *"he should be able to capture on the next test. So would I, if the
benchmark works."*

### 9.2 Minimum capture list for the next run (either machine)

Cheap to add, unrecoverable afterwards. This is the concrete answer to "capture on the next test":

1. **Run `post_run_analyze.sh <results_dir> <ns>` immediately after the run** — step 1 reads the
   controller log from a rotating kubectl buffer; minutes later it is gone (§1.1a).
2. **Keep `metrics/raw/`.** It is the only time-resolved source of KV / running / waiting / ITL /
   preemption (§1.1a). 12–35 MB/run, compresses ~10×.
3. **Keep the per-request file** (or run the extractor at the source and keep only `bundle.json`).
4. **Add a mid-band dwell stage** — hold an offered rate that parks kv in 0.3–0.85 for ≥3 min, so
   **A** becomes fittable. Open-loop RPS past the knee buys queue, not kv (§5.3 **[ref]**).
5. **Add one short-output leg** (e.g. 2000 in / 100 out) to probe the `y > 0` ITL knee (§5.2).
6. **Let the run outlive the cooldown** — ≥300 s of collection after load stops, or scale-down never
   lands in-window.

---

## 10. Replay plan (PoC `--observed` mode)

`sim.py`/`run.py` is a **synthetic clairvoyant simulator** — supply from a sizer, no trace input.
Add an **observed** path; leave the synthetic path untouched.

- **Demand ingestion (small):** `load["requests"] = [{"id", "arrival": t_arr, "size": out_tok}]`,
  `size` = server `completion_tokens`.
- **Observed supply:** sim `supply` is per-replica intervals (`start/up/stop/down`); observed data
  is a sampled step function. Births from `ready` transitions with the real `setup_s`;
  `decisions` from `desired` transitions. Represent "still up at window end" explicitly — **do
  not synthesize a scale-down** the trace doesn't contain.
- **Two modes, kept distinct:**
  - **Observed replay** — draw the measured series. "What happened."
  - **Simulated-on-real-trace** — real arrivals + real supply + this trace's true ρ, ITL, and the
    exact §6 ceiling through the sim's service model, against the observed curves. **Zero free
    parameters; divergence is the finding.** The high-value mode.
- Where the observed series live (extra series vs a 7th panel) is tied to §11.

---

## 11. Panel 4 — DEFERRED

Deferred by Dean until the input inventory is complete across several runs. When it opens, the
first question is *which* queue it draws — (a) flow-control (the PoC's semantic), (c) engine
backlog (which carries the dramatic 617 excursion), or both — since (b) ≡ panel 5's "in system".
Treatment options were sketched in Rev 2 §3.1 and are not carried forward here.

---

## 12. Open items

### 12.1 Next — concrete, in order

1. **Extract `guidellm-1785856861-71ay4b_1`** (1→9 replicas, decode-heavy) from the `biran` PVC.
   Pull-to-local, then run the extractor; diff its `coverage.json` against §9.
2. **Extract `guidellm-1785859604-upf3j2_1`** — the scale-down / drain case.
3. **Ask Ofer for the `inference-perf` raw dirs** behind the two most interesting studies:
   `comparison-100x1000-16x20x24ext20-20260729` (decode-heavy 100/1000) and
   `comparison-symmetric1000x1000-pods1120s-20260801` (symmetric, k2 A/B). These are the only
   route to an 8B-model trace; the 11 studies' data is not on the PVC and is presumed gone, so
   the realistic form of this ask is *"keep it next time"* (§9.2), not *"send me the old files"*.
4. **Still-unfilled by any existing run** (workload-design asks for the next capture, §9.2):
   mid-band kv 0.3–0.85 dwell → unlocks **A**, the 0.85 ceiling, and the knee; and a genuinely
   short-output shape → the `y > 0` ITL knee.
5. Router oscillation (§4.5) should finally be observable — the 71ay4b run reaches 9 pods vs the
   2 pods of **[ref]**.

### 12.2 Decisions for Dean
1. **Preemption** — model in the PoC, or out of scope with a noted optimism (§7.2)?
2. **First-cut scope** — extraction + observed replay only, or also simulated-on-real-trace (§10)?
3. **Commit `bundle.json` / `coverage.json`?** Small, and makes the deck reproducible without the
   4.2 GB run dir.

### 12.3 Settled
- ρ default stays **2**; measured ρ is a per-trace input (Dean). Mechanism in §7.1.
- Saturation threshold **kv ≥ 0.85**, matching the sim's `sat_frac` (Dean).
- Linear ITL holds on `[y, 0.85]`; y=0 for decode-heavy; A, B change above (Dean, confirmed §5.2).
- Queue modelled as **one global queue** — sourced deliberately (§4), never a per-pod average.
- Server token counts authoritative (§3).
- Prefill/decode: **observe, don't estimate** (Dean) — §6, §7.1.

### 12.4 Byproducts worth raising outside this work
- **§4.4 averaging trap** — `inference_pool_average_queue_size` gives phantom relief on scale-up.
  Relevant to WVA/KEDA signal choice.
- **§6 exact capacity model** — predicted the observed ceiling with zero free parameters. A
  candidate real capacity estimator, not just a viz input.
- **§7.2 preemption at ~15%** under congestion, and **§5.3 throughput falling past the knee** —
  both invisible in current dashboards.
- **§5.1 calibration gap** converges with the TA-lead Phase-A sweep requirement.

---

## 13. Caveats for a first render **[ref]**

- **Near-constant request size** (2048±50 in, ~512 out) — no size-driven head-of-line effects.
- **15 s pod-side granularity** vs a sub-second demand trace; and **sparse** pod rows (§1.1).
- **Single variant, decode-only** — no P/D split, no multi-variant cost story.
- **Scale-up only** — half of panel 2's story and all of the drain story absent.
- **Utilization hole 0.3→1.0** — the sim's 0.85 ceiling is never exercised (§5.1).
- **Decode-dominated** — prefill ~1% of service time despite inflating 4–5× (§7.1).
- **~15% of congested requests preempted**, which the PoC's service model does not represent.

---

## 14. Fetching, and making the viz dir shareable

Dean: *"Lets try to make the viz dir shareable — so Ofer can get it directly from my git fork into
his machine and run the fetch + see the visualization on his data. Should be easy to use."* and
*"No need to draft anything for Ofer. Just need clear instructions on how to use."*

So: no outreach draft. The deliverable is a **self-contained directory with a README** such that
`clone → one command → picture` works on a machine that has none of our context.

### 14.1 Constraint this places on the code

| Requirement | Consequence |
|---|---|
| Runs on someone else's machine | stdlib-only for fetch/extract; `matplotlib` only for render. No repo imports, no `plans/`-relative paths, no WVA Go build |
| Runs on someone else's data | zero hardcoded pod names, namespaces, model IDs, or run IDs; everything from the run dir + CLI flags |
| Runs on either harness | reader dispatch on `harness_name` (§1.2), never on directory naming |
| Runs on incomplete data | every optional artifact missing ⇒ a `coverage.json` FAIL row, never a traceback (§1.1) |
| Their EPP pod is named differently | accept `gaie-epp` **and** `router-epp` (the fix Ofer already made in `dump_capacity_demand_estimate.py`) |
| Big files stay put | extract at the source; only `bundle.json` (~5 MB) travels |

### 14.2 Directory shape

```
scratch/autoscaling-viz/
  README.md              ← the entry point: install, 3 commands, what each panel means
  fetch_run.sh           ← pull a run dir off a cluster PVC (oc/kubectl), read-only
  extract_real_trace.py  ← run dir → bundle.json + coverage.json   (§8)
  render_real_trace.py   ← bundle.json → panels PNG/HTML
  sim.py run.py plots.py … ← existing PoC (untouched synthetic path)
  real-trace/<label>/    ← per-run working copies (raw gitignored)
```

`fetch_run.sh` wraps exactly the read-only pattern used to inventory the PVC in §1.0b — parameters
are namespace, access-pod, remote run dir, local dest. It never writes to the source namespace.

### 14.3 The three commands the README documents

```bash
# 1. fetch (only if the data is on a cluster PVC; skip if it is already local)
./fetch_run.sh -n <ns> -p <access-pod> -r /requests/<run-dir> -o real-trace/<label>

# 2. extract  (add --no-per-request to skip the >100 MB file and still get panels 2-5)
python3 extract_real_trace.py --run real-trace/<label> --out real-trace/<label>

# 3. render
python3 render_real_trace.py --bundle real-trace/<label>/bundle.json
```

Plus a fourth, optional: `--publish` (§15).

The README must state up front the one thing a newcomer cannot guess: **`coverage.json` is the
point of step 2.** It says which panels and which calibrations this particular run can support, so
a FAIL row is information, not breakage.

### 14.4 Where it is shared from

`scratch/` currently lives on the **`plans` branch**, which is an orphan branch of internal state
and is not a sensible thing to hand anyone. Options, for Dean:

| | pros | cons |
|---|---|---|
| **A. keep on `plans`** | zero work | orphan branch full of unrelated internal planning; awkward to point someone at |
| **B. own branch on Dean's fork** (e.g. `viz-tools`) — recommended | clean clone target, nothing else in it, pairs naturally with the result branch (§15) | one more branch to keep alive |
| **C. upstream under `hack/`** | lives next to `post_run_analyze.sh`, which it complements | needs a PR and review; premature for a PoC |

**Decision needed (§12.2).** B is the smallest thing that satisfies "get it directly from my git
fork". C is the right end state *if* the tool proves useful, since §1.1a shows this is really the
missing back half of `post_run_analyze.sh`.

---

## 15. Result branch — publishing bundles

Dean: *"The fetch script can always push into result branch so we can reuse and share results."*

**Why it works:** a `bundle.json` is ~5 MB for ~40 k requests — three orders of magnitude smaller
than the 4 GB source, and it is the *complete* input to every panel. So the expensive, perishable,
cluster-bound step happens once, by whoever ran the benchmark, and everyone else gets a file.

### 15.1 Layout

```
results/<YYYYMMDD>-<label>/
  bundle.json        # the extract (§8.1)
  coverage.json      # capability report (§9)
  provenance.json    # run id, harness, model, ns, cluster, extractor git sha, extraction time
  panels.png         # rendered output, so the branch is browsable without running anything
```

Orphan branch (`git checkout --orphan viz-results`) so it never carries code history and can be
cloned shallow.

### 15.2 Rules

- **Bundles only — never raw.** Nothing >20 MB, no `metrics/raw/`, no per-request source files.
- **`provenance.json` is mandatory.** A bundle whose extractor version is unknown is not reusable;
  §8 parsing rules have already changed once (the Rev-1 prefix bug) and would silently invalidate
  older bundles.
- **Append-only.** Never rewrite an existing result dir; a re-extract lands as a new dated dir.
- **Check for prompt text.** guidellm records embed full prompts (§1.2). The extractor must not
  copy prompt text into the bundle — it is bulk, and on a real workload it could be sensitive.
- **`--publish` is opt-in and never automatic.** It stages the four files and commits locally;
  **the push is a separate, explicit human action** (project rule: no push without Dean's
  confirmation for that specific push). The script must not invoke `git push` itself.

### 15.3 Open

Which remote — Dean's fork only, or eventually upstream? Ties to §14.4. Until decided, `--publish`
writes to a local branch and stops.

---

## 16. Session log (for cold resume)

- **2026-08-06** — Retargeted per Dean off the `dean-*` test runs onto already-benchmarked data.
  Verified Ofer's preprocessing is already on our `upstream/main` (§1.1a). Read-only survey of the
  `biran` namespace and `workload-pvc` found 9 `guidellm` runs with full raw detail (§1.0b) — real
  scale-up **and** scale-down, but Qwen3-0.6B, not the 8B comparison studies. Established the
  guidellm record schema and that it removes the three-clock and token-inflation problems (§1.2).
  Rev 4 written.
- **Next actions:** write `extract_real_trace.py` (§8 spec, dual reader per §1.2), `fetch_run.sh`,
  `render_real_trace.py`, `README.md` (§14); then extract `…-71ay4b_1` and `…-upf3j2_1` (§12.1) and
  replace §9.1's predictions with measured `coverage.json` output.
- **Still deferred:** panel 4 (§11), by Dean, until the inventory is done across several runs.
- **Awaiting Dean:** §14.4 share location, §15.3 remote, and the §12.2 decisions.
