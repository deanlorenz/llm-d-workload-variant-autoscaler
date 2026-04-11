# Notation, Parameters, and Metrics Reference

This document defines the canonical notation used across the throughput analyzer design documents,
maps each symbol to its source metric(s), and describes relationships, aggregation rules, and
per-$(IL, OL)$ requirements without simplifying assumptions.

---

## 1. Request / Workload Characterization Symbols

| Symbol | Name | Unit | Description |
|--------|------|------|-------------|
| $IL$ | Input Length | tokens | Prompt (input) tokens per request. Observable before or at dispatch time. Characterized by its distribution across requests. |
| $OL$ | Output Length | tokens | Generated (output) tokens per request. Only observable after request completion. Characterized by its distribution. |
| $TL$ | Total Length | tokens | $TL = IL + OL$. |
| $TL^{max}$ | Max Context Length | tokens | Model's maximum context window: $IL + OL \leq TL^{max}$. Configured via `--max-model-len`. |
| $IL_{eff}$ | Effective Input Length | tokens | Input tokens requiring actual prefill computation after prefix cache adjustment: $IL_{eff} = IL \cdot (1 - H\text{\\\%})$. |
| $H\text{\\\%}$ | Prefix Cache Hit Rate | 0–1 | Fraction of input token lookups served from the KV prefix cache, avoiding recomputation. |
| $w$ | Workload Type | — | A workload category characterized by representative $(IL, OL)$ values. Used to bucket requests with similar compute profiles. |

### 1.1 Workload Relationships

$$IL_{eff} = IL \cdot (1 - H\text{\\\%})$$

$$TL = IL + OL$$

**KV cost per request** (tokens consumed from $KV^{max}$):

$$\overline{KV}_{req} = IL_{eff} + \frac{OL}{2} \quad \text{(time-averaged over request lifetime)}$$

$$KV_{req}^{peak} = IL_{eff} + OL \quad \text{(at end of decode phase)}$$

**Prefill time dependency** (proportional model):

$$T_{pre} \approx \frac{IL_{eff}}{\text{prefill tokens per second at current batch size}}$$

The denominator depends on the batch of other requests co-scheduled in the same prefill iteration.
$T_{pre}$ is linear in $IL_{eff}$ in isolation, but non-linear under heavy batching.

**$T_{tft}$ dependency on workload:**

$$T_{tft} \approx W_{epp} + W_{vllm} + T_{pre} \propto IL_{eff} \quad \text{(in isolation)}$$

Under batched prefill, $T_{tft}$ also depends on other requests in the same prefill batch, so the
linear approximation holds only for per-$(IL, OL)$ bin analysis, not across a mixed workload.

**ITL dependency on workload** (longer-$IL$ requests have larger KV footprints):

$$\text{ITL} = f\!\left(N_{dec},\ \sum_r KV_r,\ \text{hardware}\right)$$

For fixed $N_{dec}$, longer-$IL$ requests increase the aggregate KV size and thus attention memory
bandwidth requirements, raising ITL for all co-scheduled requests.


---

## 2. Delay Symbols ($T$ and ITL)

All delays are measured in **seconds**.

| Symbol | Name | Description |
|--------|------|-------------|
| $T_{tft}$ | Time To First Token (TTFT) | Wall-clock time from when a request is submitted to the system until the first output token is returned to the caller. Includes: EPP scheduler queue wait $W_{epp}$, vLLM internal queue wait $W_{vllm}$, prefill computation (all chunks), and the time to complete the first decode step. This is what the end user observes. |
| $T_{pre}$ | Request Prefill Time | GPU computation time for the prefill phase only — the time vLLM spends processing all input tokens to build the initial KV cache entries. Does **not** include queue waits. With chunked prefill, $T_{pre}$ is the sum of all chunk compute times. |
| ITL | Inter-Token Latency | Time between consecutive generated output tokens. With continuous batching, each decode iteration processes a batch of $N_{dec}$ sequences; ITL for a request is the wall time of one iteration. ITL increases with $N_{dec}$ and total KV memory pressure. |
| $T_{dec}$ | Request Decode Time | Total decode phase duration for one request: elapsed time from the first output token to the last. $T_{dec} = \text{ITL} \cdot (OL - 1) \approx \text{ITL} \cdot OL$ for large $OL$. |
| $T_{e2e}$ | End-to-End Latency | Total elapsed time from request submission to the final output token. |

### 2.1 Wait Times ($W$)

| Symbol | Name | Description |
|--------|------|-------------|
| $W_{epp}$ | EPP Queue Wait | Time a request spends waiting in the llm-d EPP flow control queue before being dispatched to a backend pod. |
| $W_{vllm}$ | vLLM Admission Wait | Time a request spends in vLLM's internal waiting queue after being dispatched but before being admitted to the running batch (i.e., before a free KV slot is granted). Also referred to as $W_{admit}$ in supply-side analysis when $W_{epp} = 0$ is assumed. |

### 2.2 Delay Relationships (General — No Simplifying Assumptions)

$$T_{tft} = W_{epp} + W_{vllm} + T_{pre} + \text{ITL}$$

where the final ITL term is the time to produce the first output token (one decode step).

$$T_{e2e} = T_{tft} + \text{ITL} \cdot (OL - 1) \approx W_{epp} + W_{vllm} + T_{pre} + \text{ITL} \cdot OL \quad \text{for } OL \gg 1$$

$$T_{dec} = \text{ITL} \cdot OL$$

**Chunked prefill note.** When chunked prefill is enabled, vLLM breaks a long-$IL$ request into
chunks of at most `--max-num-batched-tokens` tokens. Each chunk occupies one scheduler cycle,
interleaved with decode iterations. $T_{tft}$ grows proportionally to the number of chunks.
$T_{pre}$ (total prefill compute) is unchanged, but the wall-clock $T_{tft}$ increases by
$W_{vllm}$ multiplied by the number of additional scheduling rounds. The metric
`vllm:request_prefill_time_seconds` reports accumulated compute time, not wall-clock $T_{tft}$.

**Small-queue $T_{pre}$ measurement.** When $N_{wait}$ is small (2–5 requests), $W_{vllm}$ has
not yet accumulated significantly: $T_{tft} \approx T_{pre} + \text{ITL}$. This provides a clean
estimate of the hardware prefill cost: $\hat{T}_{pre} \approx T_{tft} - \text{ITL}$, without
requiring the `vllm:request_prefill_time_seconds` metric. The ratio
$\hat{T}_{pre} / \overline{IL}_{eff}$ (seconds per token) is approximately constant for a given
hardware configuration and $IL \lesssim 10\text{K}$, and can be reused to predict
$T_{pre}$ for new workloads on the same hardware (TA-supply.md §4.3).

**Continuous batching note.** Because vLLM batches decode steps across all $N_{dec}$ concurrent
requests, ITL experienced by a single request is the wall time of one decode iteration for
the whole batch. As $N_{dec}$ increases or the aggregate KV footprint grows, ITL rises.


---

## 3. Rate Symbols ($\lambda$, $\mu$)

All rates are measured in **units per second**.

| Symbol | Name | Unit | Description |
|--------|------|------|-------------|
| $\lambda$ | Request Arrival Rate | req/s | Rate at which new requests enter the system at the EPP. Upstream of any queueing. Also written $\lambda_{req}$, $\lambda_m$ per model, or $\lambda_v$ per variant (dispatched rate). |
| $\lambda_{pre}$ | Prefill Demand Rate | tokens/s | Input tokens per second that require actual GPU prefill computation, after prefix-cache adjustment: $\lambda_{pre} = \lambda \cdot \overline{IL}_{eff} = \lambda \cdot \overline{IL} \cdot (1 - H\text{\\\%})$. |
| $\lambda_{dec}$ | Decode Demand Rate | tokens/s | Output tokens per second the system must generate to sustain the arrival rate: $\lambda_{dec} = \lambda \cdot \overline{OL}$. |
| $\lambda_{tok}$ | KV Cache Demand Rate | tokens/s | Rate at which incoming requests commit new KV cache memory: $\lambda_{tok} = \lambda_{pre} + \lambda_{dec} = \lambda \cdot (\overline{IL}_{eff} + \overline{OL})$. Equals the peak KV footprint per request times the arrival rate. |
| $\mu$ | Successful Completion Rate | req/s | Rate of requests that complete successfully (last output token delivered). $\mu \leq \lambda$ at steady state (due to queueing); $\mu = \lambda$ when the system is not dropping requests. Used in supply analysis. |
| $\mu_{err}$ | Error Rate | req/s | Rate of requests that fail (context-length exceeded, OOM, model error, etc.). |
| $\mu_{tok}$ | Output Token Throughput | tokens/s | Output (decode) tokens generated per second, as observed from vLLM counters. Also called GPS (Generated Tokens Per Second). Supply-side metric; equals $\lambda_{dec}$ at steady state. |
| $\mu_{pre}^{cap}$ | Prefill Admission Capacity | tokens/s | Hardware-limited rate at which a replica can sustain prefill: $\mu_{pre}^{cap}(k) \approx \overline{IL}_{eff} / \text{ITL}(k) = \overline{IL}_{eff} / (A \cdot k + B)$. Not a Prometheus metric; estimated from $\hat{T}_{pre}$ at small-queue conditions (see §2.2 and TA-supply.md §4.3). |
| $\mu_{RPS}$ | Request Completion Rate | req/s | Little's Law for the full system: $\min(N(k), N^{max}) / E2E(k)$, where $N(k) = N_{dec}(k) + 1$ and $E2E(k) = T_{pre}(k) + \overline{OL} \cdot \text{ITL}(k)$. Reduces to $\mu_{dec} / \overline{OL}$ when $T_{pre} \ll T_{dec}$ and $N(k) < N^{max}$ (typical non-chunked case). See TA-supply.md §5. |

### 3.1 Rate Relationships

**Demand-side rates** (what the arrival stream requires from the system):

$$\lambda_{pre} = \lambda \cdot \overline{IL}_{eff} = \lambda \cdot \overline{IL} \cdot (1 - H\text{\\\%})$$

$$\lambda_{dec} = \lambda \cdot \overline{OL}$$

$$\lambda_{tok} = \lambda_{pre} + \lambda_{dec} = \lambda \cdot \bigl(\overline{IL} \cdot (1 - H\text{\\\%}) + \overline{OL}\bigr)$$

**Supply-side / observed rates** (what vLLM is currently producing):

$$\mu_{tok} = \mu \cdot \overline{OL} = \text{rate}(\texttt{vllm:request\_generation\_tokens\_sum}[\Delta t]) \approx \frac{N_{dec}}{\text{ITL}}$$

At steady state with no queueing: $\mu_{tok} = \lambda_{dec}$ and $\mu = \lambda$.

$$\mu_{err} = \lambda - \mu \quad \text{(at steady state, ignoring in-flight requests)}$$

**Multi-workload form** (workload types $w \in \mathcal{W}$ with mixture weights $\pi_w$):

$$\lambda_{pre} = \lambda \cdot \sum_{w} \pi_w \cdot IL(w) \cdot (1 - H\text{\\\%}), \qquad
\lambda_{dec} = \lambda \cdot \sum_{w} \pi_w \cdot OL(w)$$

**Source for $\lambda_v$ (dispatched rate per pod).** The EPP scheduler dispatches requests to
individual pods; use `inference_extension_scheduler_attempts_total{status="success"}` per pod. This
is dispatched rate, equal to arrival rate when the EPP has no queue ($W_{epp} = 0$).


---

## 4. vLLM Runtime State Symbols

| Symbol | Name | Unit | Description |
|--------|------|------|-------------|
| $N$ | Running Requests | count | Total requests currently being processed by vLLM (in either prefill or decode phase). $N = N_{pre} + N_{dec}$. |
| $N_{pre}$ | Prefill Requests | count | Requests currently in the prefill phase (computing KV cache from prompt tokens). **Not available as a Prometheus metric in any released vLLM version** (see §4.2). |
| $N_{dec}$ | Decode Requests | count | Requests currently in the decode phase (generating output tokens). **Not available as a Prometheus metric in any released vLLM version** (see §4.2). |
| $N_{wait}$ | Waiting Requests | count | Requests accepted by vLLM but queued waiting for a free KV memory slot. Distinct from $W_{epp}$ (EPP queue), which is upstream of vLLM. |
| $N^{max}$ | Max Concurrent Sequences | count | Maximum sequences vLLM will process concurrently. Configured via `--max-num-seqs`. When $N = N^{max}$, new requests enter $N_{wait}$. |
| $KV$ | KV Cache Tokens In Use | tokens | Current KV cache token slots occupied across all running requests. $KV = KV\text{\\\%} \cdot KV^{max}$. |
| $KV^{max}$ | KV Cache Capacity | tokens | Total KV token slots available on GPU. $KV^{max} = \texttt{num\_gpu\_blocks} \times \texttt{block\_size}$. |
| $KV\text{\\\%}$ | KV Cache Utilization | 0–1 | Fraction of KV cache currently occupied. $KV\text{\\\%} = KV / KV^{max}$. |
| $\overline{KV}_{req}$ | Mean KV Footprint per Request | tokens | Time-averaged KV token slots occupied by a single request over its lifetime: $\overline{KV}_{req} = \overline{IL}_{eff} + \overline{OL}/2$. The $\overline{OL}/2$ term reflects that decode tokens accumulate from 0 to $OL$ uniformly. Also written `kv_per_req` in pseudocode. Used in $N_{dec}$ estimation and the $k_{knee}$ formula. **Not** the peak footprint $\overline{IL}_{eff} + \overline{OL}$, which is only reached at the final decode step. |

### 4.1 vLLM State Relationships

$$N = N_{pre} + N_{dec}$$

$$KV^{max} = \texttt{num\_gpu\_blocks} \times \texttt{block\_size}$$

$$KV = KV\text{\\\%} \cdot KV^{max}$$

**KV occupancy of a single request $r$ at time $t$** (decode tokens produced so far = $k_r(t) \in [0, OL_r]$):

$$KV_r(t) = IL_{eff,r} + k_r(t)$$

**Aggregate KV at time $t$:**

$$KV(t) = \sum_{r \in N_{pre}} IL_{eff,r} + \sum_{r \in N_{dec}} \bigl(IL_{eff,r} + k_r(t)\bigr)$$

**Time-averaged KV per request** (averaging $k_r(t)$ uniformly over $[0, OL]$):

$$\overline{KV}_{req} = \overline{IL}_{eff} + \frac{\overline{OL}}{2}$$

**Aggregate KV at steady state** (single-workload):

$$KV \approx N \cdot \overline{KV}_{req}$$

**Multi-workload generalization** (workload types $w \in \mathcal{W}$, $N_w$ requests of type $w$):

$$KV \approx \sum_{w \in \mathcal{W}} N_w \cdot \overline{KV}_{req}(w), \qquad
\overline{KV}_{req}(w) = IL_{eff}(w) + \frac{OL(w)}{2}$$

**Little's Law** (for vLLM as a service, at steady state, no queue):

$$N = \mu \cdot T_{e2e}$$

$$N_{wait} = \lambda \cdot W_{vllm}$$

**Binding constraint** ($N^{max}$ vs $KV^{max}$):
- Long-context workloads: $KV^{max}$ binds first (large KV footprint per request)
- Short-context workloads: $N^{max}$ often binds first

### 4.2 Availability of $N_{pre}$ and $N_{dec}$ in vLLM

As of **vLLM v0.14.1** (the version bundled in llm-d v0.5.0), the Prometheus metrics
`vllm:num_requests_prefill` and `vllm:num_requests_decode` **do not exist** in any released vLLM
version. They are tracked in open PR #33845 ("[Core] Expose detailed scheduler stats") which is
not yet merged. Until that PR lands, these counts must be estimated:

- $N_{dec} \approx \mu_{tok} \cdot \text{ITL}$ (from GPS and ITL: each decode request contributes $1/\text{ITL}$ tokens/sec)
- $N_{pre} = N - N_{dec}$ (residual)
- Or: treat $N \approx N_{dec}$ when the system is not under heavy prefill load (decode-dominated)

### 4.3 Autoscaler KV% Operating-Point Parameters

These are not Prometheus metrics but derived thresholds used by the autoscaler
to determine when to scale up.

| Symbol | Name | Description |
|--------|------|-------------|
| $k_{sat}$ | Decode Saturation Threshold | Target KV% at which the autoscaler aims to operate. Above this point, $\mu_{dec}$ grows negligibly and TTFT/GPS SLOs are at risk. Typical value: 0.75–0.80. Used to compute per-replica supply capacity $\mu_{dec}^{sat}$ (TA-supply.md §3.3). |
| $N_{dec}^{sat}$ | Decode Concurrency at $k_{sat}$ | Number of decode-phase requests at the saturation operating point: $N_{dec}^{sat} = k_{sat} \cdot KV^{max} / \overline{KV}_{req}$. Used in the $\mu^{sat}_{RPS}$ formula (TA-supply.md §5.4). Pseudocode: `N_dec_sat`. |
| $k_{knee}$ | TTFT Knee KV% | KV% at which admission wait $W_{vllm}$ begins to dominate TTFT, causing TTFT SLO violations before KV cache fills. Derived from the rate-balance condition $\lambda = \mu_{RPS}(k)$: $k_{knee} = \lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot B \; / \; (KV^{max} - \lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot A)$. Per-workload: short-OL workloads ($\overline{OL} \lesssim 150$) have $k_{knee} \ll k_{sat}$. |
| $k_{N^{max}}$ | Batch Concurrency KV% Cap | KV% at which the number of decode-phase requests $N_{dec}$ would equal the scheduler concurrency limit $N^{max}$. $k_{N^{max}} = N^{max} \cdot \overline{KV}_{req} / KV^{max}$. For $k < k_{N^{max}}$, the KV cache fills before the batch saturates ($\mu_{RPS}^{dec}$ is binding). For $k > k_{N^{max}}$, $N^{max}$ is hit first and $\mu_{RPS}^{N^{max}}$ caps throughput. |
| $k_{threshold}$ | Effective Scale-Up Threshold | $k_{threshold} = \min(k_{knee},\, k_{sat})$. The KV% at which the autoscaler should trigger scale-up. For long-output workloads $k_{threshold} \approx k_{sat}$; for short-output workloads $k_{threshold}$ may be substantially lower. |

**Relationship between $k_{knee}$ and workload output length.** Because $\overline{OL}$ appears in
the denominator of $\mu_{RPS}(k) = k \cdot KV^{max} / (\overline{KV}_{req} \cdot \overline{OL} \cdot (Ak+B))$,
short-output workloads saturate at lower $KV\text{\%}$:

| $\overline{IL}$ | $\overline{OL}$ | Observed $k_{knee}$ (H100) |
|----------------|----------------|--------------------------|
| 5000 | 500 | ≈ 67% |
| 5000 | 200 | ≈ 58% |
| 6000 | 100 | ≈ 23% |

At $k_{knee}$, $W_{vllm}$ is approximately 10–11 decode steps regardless of workload, and
$N_{wait}$ is typically 2–5. See TA-supply.md §4.2 for derivation and empirical data.


---

## 5. vLLM Prometheus Metrics and Derivations

### 5.1 Delay Metrics

| Symbol | Prometheus Metric | PromQL Pattern | vLLM Version | Currently Collected? | Notes |
|--------|------------------|---------------|--------------|----------------------|-------|
| $T_{tft}$ (avg) | `vllm:time_to_first_token_seconds` | `rate(_sum[1m]) / rate(_count[1m])` per pod | All | Yes (`AvgTTFT`) | Histogram. Includes $W_{vllm}$. |
| $T_{tft}$ (pctile) | `vllm:time_to_first_token_seconds_bucket` | `histogram_quantile(p, rate(_bucket[5m]))` | All | No | Requires histogram scrape. |
| $T_{pre}$ (avg) | `vllm:request_prefill_time_seconds` | `rate(_sum[1m]) / rate(_count[1m])` per pod | **≥ v0.7.3** | **No** | Compute-only; does not include $W_{vllm}$. V1 engine only. |
| $T_{dec}$ (avg) | `vllm:request_decode_time_seconds` | `rate(_sum[1m]) / rate(_count[1m])` per pod | **≥ v0.7.3** | **No** | Total decode phase per request. V1 engine only. Cross-check: $T_{dec} \approx \text{ITL} \cdot \overline{OL}$. |
| ITL (avg) | `vllm:time_per_output_token_seconds` | `rate(_sum[1m]) / rate(_count[1m])` per pod | All | Yes (`AvgITL`) | Histogram. |
| $T_{e2e}$ (avg) | derived | $T_{tft} + \text{ITL} \cdot \overline{OL}$ | — | Derived | Approximate; assumes independence. |
| $T_{e2e}$ (direct) | `vllm:e2e_request_latency_seconds` | `rate(_sum[1m]) / rate(_count[1m])` | All | No | Direct histogram; useful for validation. |

**Both $T_{pre}$ and $T_{dec}$ are available in llm-d v0.5.0** (which bundles vLLM v0.14.1 ≫ v0.7.3)
and require the **V1 engine** (`VLLM_USE_V1=1` or vLLM's default when V1 is stable). These are
high-priority metrics to add to the WVA collector.

### 5.2 Rate Metrics

| Symbol | Prometheus Metric | PromQL Pattern | Currently Collected? | Notes |
|--------|------------------|---------------|----------------------|-------|
| $\lambda_v$ (dispatched, per pod) | `inference_extension_scheduler_attempts_total{status="success"}` | `sum by (pod_name) (rate([1m]))` | Yes (`ArrivalRate`) | EPP metric. Equal to $\lambda_v$ when $W_{epp} = 0$. |
| $\lambda$ (arrival, model) | `inference_extension_request_total` | `rate({model=m}[1m])` | No | Total requests arriving at EPP before queueing. |
| $\mu$ (SRPS, per pod) | `vllm:request_success_total` | `rate([1m])` per pod | No | Successful completions. Token counters serve as proxy. |
| $\mu_{err}$ (ERPS) | derived | $\lambda - \mu$ | No | Or from `vllm:request_failure_total` if available. |
| $\lambda_{pre}$ (prefill demand) | `vllm:request_prompt_tokens_sum` | `rate([1m]) × (1-H%) per pod` | No (rate) | Demand-side. Derived: $\lambda_v \cdot \overline{IL} \cdot (1 - H\text{\\\%})$ from collected scalars. Direct rate not yet stored. |
| $\lambda_{dec}$ (decode demand) | `vllm:request_generation_tokens_sum` | `rate([1m])` per pod | No (rate) | Demand-side. Derived: $\lambda_v \cdot \overline{OL}$ from collected scalars. Direct rate not yet stored. |
| $\lambda_{tok}$ (KV demand) | derived | $\lambda_{pre} + \lambda_{dec}$ | Derived | KV cache commitment rate per pod. |
| $\mu_{tok}$ (GPS, supply) | `vllm:request_generation_tokens_sum` | `rate([1m])` per pod | No (rate) | Supply-side observed throughput. Token averages are collected; raw rate is not. Equals $\lambda_{dec}$ at steady state. |

### 5.3 vLLM State Metrics

| Symbol | Prometheus Metric | PromQL Pattern | Currently Collected? | Notes |
|--------|------------------|---------------|----------------------|-------|
| $N$ | `vllm:num_requests_running` | instant value per pod | Yes (`RunningRequests`) | Total in-flight ($N_{pre} + N_{dec}$). |
| $N_{pre}$ | — | — | **N/A** | **Does not exist in any released vLLM version.** See §4.2. |
| $N_{dec}$ | — | — | **N/A** | **Does not exist in any released vLLM version.** Estimate: $N_{dec} \approx \mu_{tok} \cdot \text{ITL}$. See §4.2. |
| $N_{wait}$ | `vllm:num_requests_waiting` | `max_over_time([1m])` per pod | Yes (`QueueLength`) | vLLM internal queue; distinct from $W_{epp}$. |
| $N^{max}$ | (not a Prometheus metric) | Parsed from `--max-num-seqs` in Deployment args | Yes (`MaxBatchSize`) | Default 256 in vLLM v0.8+. |
| $KV\text{\\\%}$ | `vllm:kv_cache_usage_perc` | `max_over_time([1m])` per pod | Yes (`KvCacheUsage`) | 0.0–1.0. |
| $KV^{max}$ | `vllm:cache_config_info{num_gpu_blocks, block_size}` | static labels | Yes (`TotalKvCapacityTokens`) | $KV^{max} = \texttt{num\_gpu\_blocks} \times \texttt{block\_size}$. |
| $KV$ | derived | $KV\text{\\\%} \cdot KV^{max}$ | Yes (`TokensInUse`) | Derived by collector. |

### 5.4 Workload / Request Metrics

| Symbol | Prometheus Metric | PromQL Pattern | Currently Collected? | Notes |
|--------|------------------|---------------|----------------------|-------|
| $\overline{IL}$ (avg) | `vllm:request_prompt_tokens_sum/count` | `rate(_sum[5m]) / rate(_count[5m])` per pod | Yes (`AvgInputTokens`) | Mean prompt length over completed requests. |
| $\overline{OL}$ (avg) | `vllm:request_generation_tokens_sum/count` | `rate(_sum[5m]) / rate(_count[5m])` per pod | Yes (`AvgOutputTokens`) | Mean generation length over completed requests. |
| $IL$ (distribution) | `vllm:request_prompt_tokens_bucket` | histogram | No | Required for per-bin workload analysis. High priority to add. |
| $OL$ (distribution) | `vllm:request_generation_tokens_bucket` | histogram | No | Required for per-bin workload analysis. High priority to add. |
| $H\text{\\\%}$ | `vllm:prefix_cache_hits`, `vllm:prefix_cache_queries` | `rate(hits[5m]) / rate(queries[5m])` per pod | Yes (`PrefixCacheHitRate`) | Ratio from counters. |
| $TL^{max}$ | (not a Prometheus metric) | Parsed from `--max-model-len` in Deployment args | No | Static; useful for rejection rate estimation. |

---

## 6. llm-d EPP (Inference Scheduler) Metrics

| Symbol | Prometheus Metric | PromQL Pattern | Currently Collected? | Notes |
|--------|------------------|---------------|----------------------|-------|
| $\lambda_v$ (dispatched per pod) | `inference_extension_scheduler_attempts_total{status="success"}` | `sum by (pod_name) (rate([1m]))` | Yes (`ArrivalRate`) | Per-pod dispatch rate. |
| $N_{epp,wait}$ | `inference_extension_flow_control_queue_size` | `sum({model=m})` | Yes (`SchedulerQueue.QueueSize`) | EPP-level queue, upstream of all vLLM pods. |
| EPP queue bytes | `inference_extension_flow_control_queue_bytes` | `sum({model=m})` | Yes (`SchedulerQueue.QueueBytes`) | Proxy for queued request body size. |
| $\overline{IL}$ at EPP | `inference_extension_input_tokens` | histogram per model | No | Mean input tokens observed before routing — includes queued requests. Preferred over vLLM-side $\overline{IL}$ for demand estimation. High priority to add. |

---

## 7. Aggregation Rules and Per-$(IL, OL)$ Requirements

### 7.1 Metrics That Aggregate Safely Across All Requests

These can be computed as pod-level or model-level averages without losing accuracy for capacity modeling:

| Metric | Aggregation | Rationale |
|--------|------------|-----------|
| $KV\text{\\\%}$ | Average or max across pods | Directly observable; max is meaningful for saturation detection |
| $KV^{max}$ | Sum across pods (model capacity) or per-pod (per-replica) | Static hardware property |
| $N$, $N_{wait}$ | Sum across pods | Additive; model-level $N = \sum N_{\text{pod}}$ |
| $\lambda_{pre}$, $\lambda_{dec}$, $\lambda_{tok}$ | Sum across pods | Demand rates are additive |
| $\mu_{tok}$ | Sum across pods | Supply throughput is additive |
| $\lambda$, $\mu$ | Sum across pods | Request rate is additive |
| $H\text{\\\%}$ | Volume-weighted mean across pods | Arithmetic mean is biased; use $\sum_{v}(\lambda_v \cdot H\text{\\\%}(v)) / \sum_{v} \lambda_v$ |

### 7.2 Metrics That Require Per-$(IL, OL)$ Collection for Accuracy

These metrics have workload-type-dependent values. Aggregating across $(IL, OL)$ combinations
produces a mean that is only accurate when the workload distribution is **unimodal and stationary**.
With bimodal or heterogeneous traffic (e.g., short chat mixed with long batch/RAG), the aggregate
misleads:

| Metric | Why per-$(IL, OL)$ matters | What aggregate loses |
|--------|--------------------------|----------------------|
| $T_{tft}$ | $T_{tft} \propto IL_{eff}$; also affected by co-scheduled requests | Bimodal $IL$ → $\overline{T_{tft}}$ misrepresents both modes |
| $T_{pre}$ | $T_{pre} \propto IL_{eff}$ directly | Same as $T_{tft}$: aggregate underestimates for long-$IL$, overestimates for short-$IL$ |
| ITL | Depends on $N_{dec}$ and total KV size; long-$IL$ requests occupy more KV per sequence → higher ITL at same $N_{dec}$ | Aggregate ITL is only valid when $IL$ distribution is stable |
| $T_{e2e}$ | Derived from $T_{tft}$ and $\text{ITL} \cdot OL$; both components depend on $(IL, OL)$ | Aggregate $T_{e2e}$ weights short (fast) requests more than long (slow) ones; underestimates long-tail latency |
| $\overline{KV}_{req}$ | $\overline{KV}_{req} = IL_{eff} + OL/2$; proportional to both $IL$ and $OL$ | Aggregate gives correct $N^{max}$ only when workload mix is stable; a shift to longer requests tightens $KV^{max}$-derived capacity unexpectedly |
| $k_{knee}$ | Derived from $(IL, OL, \lambda, A, B)$ via rate-balance formula (§4.3); $\overline{OL}$ in denominator of $\mu_{RPS}$ means short-output workloads hit the knee at much lower KV% | Aggregate $\overline{OL}$ produces a single $k_{knee}$ that is too optimistic for short-OL traffic and too conservative for long-OL traffic in a mixed workload; per-bin $k_{knee}$ is required to correctly set $k_{threshold}$ |

### 7.3 How to Obtain Per-$(IL, OL)$ Data

Current vLLM Prometheus metrics do not provide per-$(IL, OL)$ labeled histograms for $T_{tft}$ or
ITL. Strategies in decreasing order of accuracy:

1. **Direct per-request join** (preferred): If the EPP tags each request with its workload bin
   label before routing, and vLLM propagates that label to its histograms, histogram queries with a
   workload label directly yield per-bin $T_{tft}$ and ITL. Requires EPP and vLLM changes not
   yet in place.

2. **Proportional deconvolution** (K3 approach): Observe workload mixture weights
   $\pi_w = N_w / \sum_{w'} N_{w'}$ from EPP-side request counts. Use structural constraints
   ($T_{tft}$ increases with $IL_{eff}$, ITL increases with $KV\text{\\\%}$) to solve for per-bin
   expectations via constrained least-squares fit to per-pod histogram moments.

3. **Aggregate with mixture correction**: Use aggregate $\overline{T_{tft}}$
   and $\overline{\text{ITL}}$, but scale $T_{tft}$ linearly by $IL(w) / \overline{IL}$ and ITL by
   the bin's expected KV pressure relative to average.

4. **Single-bin aggregate** (default fallback): When no workload bins are configured, use a single
   bin with observed $(\overline{IL}, \overline{OL})$. Accurate for homogeneous traffic; degrades
   gracefully for heterogeneous traffic.

### 7.4 Preferred Source for Each Parameter

| Parameter | Preferred Source | Fallback | Reason |
|-----------|-----------------|---------|--------|
| $N$ | `vllm:num_requests_running` (direct) | Little's Law: $\lambda_v \cdot T_{e2e}$ | Direct measurement avoids $T_{e2e}$ estimation error |
| $KV\text{\\\%}$ | `vllm:kv_cache_usage_perc` | — | Direct; no alternative |
| $H\text{\\\%}$ | `rate(prefix_cache_hits) / rate(prefix_cache_queries)` | 0 (conservative: no caching) | Ratio from counters; 0 is safe default |
| $T_{tft}$ | `vllm:time_to_first_token_seconds` histogram | $T_{pre}$ (no-queue proxy, lower bound) | Histogram captures distribution; scalar proxy omits $W_{vllm}$ |
| $T_{pre}$ | `vllm:request_prefill_time_seconds` (≥ v0.7.3, V1 engine) | $T_{tft} \cdot IL_{eff}/IL$ (queue-adjusted heuristic) | Compute-only signal; not yet collected in WVA |
| ITL | `vllm:time_per_output_token_seconds` histogram | $\mu_{tok} / N_{dec}$ (supply GPS-derived) | Histogram is direct; GPS-derived requires $N_{dec}$ estimate |
| $\overline{IL}$ | EPP `inference_extension_input_tokens` histogram | vLLM `rate(prompt_tokens_sum/count)` | EPP sees queued requests; vLLM only reports completed ones |
| $\overline{OL}$ | vLLM `rate(generation_tokens_sum/count)` | — | Only observable post-completion; EPP does not have this |
| $\lambda$ (arrival) | `inference_extension_request_total` (EPP, model-level) | $\sum_v \lambda_v$ (sum of dispatched rates) | EPP arrival rate is pre-queue; sum of dispatched rates underestimates during queue build-up |

---

## 8. Symbols Not Yet Collected in WVA

| Symbol | Prometheus Metric | Priority | Notes |
|--------|------------------|---------|-------|
| $T_{pre}$ | `vllm:request_prefill_time_seconds` | **High** | Available in llm-d (vLLM v0.14.1 ≥ v0.7.3, V1 engine). Critical for separating compute from queue wait in $T_{tft}$. |
| $T_{dec}$ | `vllm:request_decode_time_seconds` | **High** | Available in llm-d (same version requirement). Cross-check: $T_{dec} \approx \text{ITL} \cdot \overline{OL}$. |
| $\mu$ (SRPS) | `vllm:request_success_total` | Low | Currently proxied via token rate counters. |
| $\mu_{tok}$ (GPS, supply rate) | `rate(vllm:request_generation_tokens_sum[1m])` | Low | Supply-side observed throughput. Token averages collected; raw rate is not. Equals $\lambda_{dec}$ at steady state. |
| $\lambda_{pre}$ (prefill demand, direct) | `rate(vllm:request_prompt_tokens_sum[1m])` | Low | Demand-side direct rate. Currently derived from $\lambda_v \cdot \overline{IL} \cdot (1 - H\text{\\\%})$ using collected scalars. |
| $TL^{max}$ | `--max-model-len` Deployment arg | Low | Static; useful for rejection rate estimation. |
| $N_{pre}$, $N_{dec}$ | — | **N/A** | **Do not exist in any released vLLM version** (as of v0.14.1). Tracked in open PR #33845. Estimate $N_{dec} \approx \mu_{tok} \cdot \text{ITL}$ (supply-side, using observed GPS). |
| $IL$ distribution | `vllm:request_prompt_tokens_bucket` | **High** | Needed for per-$(IL, OL)$ bin workload analysis. |
| $OL$ distribution | `vllm:request_generation_tokens_bucket` | **High** | Same. |
| $\overline{IL}$ at EPP | `inference_extension_input_tokens` histogram | **High** | Demand estimation including queued requests. |
| $\lambda$ (arrival, model) | `inference_extension_request_total` | Medium | Pre-queue arrival rate; currently only dispatched $\lambda_v$ is collected. |
| $T_{pre}$ / $\overline{IL}_{eff}$ (hardware constant) | `vllm:request_prefill_time_seconds` | **High** | Portable prefill cost per token; estimated from `AvgTTFT / AvgInputTokens` at small-queue conditions when metric unavailable. Required for $k_{knee}$ and $\mu_{pre}^{cap}$ computation. |
| $k_{sat}$ | — (operator config) | **High** | Target KV% operating point; should be a first-class autoscaler config field. Default 0.75. |
| $k_{knee}$ | — (derived) | **High** | Computed from current $(\lambda, \overline{IL}, \overline{OL}, A, B)$; needs to be tracked per variant and per workload bin. |

---

## 9. WVA Go Field Name Mapping

The following maps mathematical symbols to their corresponding field names in
`interfaces.ReplicaMetrics` and the collector, for use in code and pseudocode:

| Symbol | Go Field / Derived Name | Source |
|--------|------------------------|--------|
| $KV\text{\\\%}$ | `KvCacheUsage` | `vllm:kv_cache_usage_perc` |
| $KV^{max}$ | `TotalKvCapacityTokens` | `num_gpu_blocks × block_size` |
| $KV$ | `TokensInUse` | `KvCacheUsage × TotalKvCapacityTokens` |
| $N_{wait}$ | `QueueLength` | `vllm:num_requests_waiting` |
| $N^{max}$ | `MaxBatchSize` | `--max-num-seqs` arg |
| $N$ | `RunningRequests` | `vllm:num_requests_running` |
| $\lambda_v$ = $\lambda_{req,v}$ | `ArrivalRate` | `inference_extension_scheduler_attempts_total` |
| $\overline{IL}$ | `AvgInputTokens` | `rate(prompt_tokens_sum/count)` |
| $\overline{OL}$ | `AvgOutputTokens` | `rate(generation_tokens_sum/count)` |
| $H\text{\\\%}$ | `PrefixCacheHitRate` | `rate(prefix_cache_hits/queries)` |
| $\lambda_{pre,v}$ | `ArrivalRate × AvgInputTokens × (1 - PrefixCacheHitRate)` | derived |
| $\lambda_{dec,v}$ | `ArrivalRate × AvgOutputTokens` | derived |
| $\lambda_{tok,v}$ | `λ_pre_v + λ_dec_v` | derived |
| $T_{tft}$ | `AvgTTFT` | `rate(time_to_first_token_seconds_sum/count)` |
| ITL | `AvgITL` | `rate(time_per_output_token_seconds_sum/count)` |
| $N_{epp,wait}$ | `SchedulerQueue.QueueSize` | `inference_extension_flow_control_queue_size` |
| $k_{sat}$ | `KSat` (config, default 0.75) | operator-configured KV% target |
| $k_{knee}$ | `KKnee` (derived) | $\lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot B \;/\; (KV^{max} - \lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot A)$ |
| $k_{N^{max}}$ | `KNMax` (derived) | $N^{max} \cdot \overline{KV}_{req} / KV^{max}$ |
| $k_{threshold}$ | `KThreshold` (derived) | $\min(k_{knee},\, k_{sat})$ |
| $\mu_{pre}^{cap}$ | `MuPreCap` (derived) | `AvgInputTokens × (1-PrefixCacheHitRate) / AvgTTFT` (valid only when `QueueLength` = 2–5) |
| $T_{pre} / \overline{IL}_{eff}$ | `TPre_per_tok` (derived, hardware constant) | `AvgTTFT / AvgInputTokens` at small-queue conditions |
