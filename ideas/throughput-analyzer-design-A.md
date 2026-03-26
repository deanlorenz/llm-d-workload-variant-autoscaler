# Detailed Design: Throughput Analyzer — Proactive Rate-Based Scaling

**Based on:** Proposal 2 — Proactive Throughput-Based Scaling, Proposal 4 — Multi-Analyzer Unification Framework
**Status:** Draft
**Date:** 2026-02-10

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Analysis](#2-problem-analysis)
3. [Design Goals and Non-Goals](#3-design-goals-and-non-goals)
4. [Metrics: Rate-Based Demand and Supply](#4-metrics-rate-based-demand-and-supply)
   - 4.1: Available Metrics for Rate Estimation
   - 4.2: New Metrics Required
   - 4.3: Rate Computation Methods
5. [Core Concepts](#5-core-concepts)
   - 5.1: Dual-Channel Architecture
   - 5.2: Prefill Channel: Demand and Supply
   - 5.3: Decode Channel: Demand and Supply
   - 5.4: Combined Utilization
   - 5.5: Rate Smoothing (EMA)
   - 5.6: Load-Dependent Timing
6. [Type Definitions](#6-type-definitions)
   - 6.1: ThroughputScalingConfig
   - 6.2: ReplicaMetrics Additions
   - 6.3: Throughput-Specific Internal Types
7. [Throughput Analyzer Design](#7-throughput-analyzer-design)
   - 7.1: Interface (common Analyzer)
   - 7.2: Implementation (ThroughputAnalyzer)
   - 7.3: Core Algorithm: `Analyze`
   - 7.4: Demand Rate Computation
   - 7.5: Supply Rate Estimation
   - 7.6: Per-Variant Aggregation
   - 7.7: P/D Disaggregation Integration
8. [Multi-Analyzer Integration](#8-multi-analyzer-integration)
   - 8.1: Signal Combination Logic
   - 8.2: OR Scale-Up / AND Scale-Down
   - 8.3: Engine Changes
9. [Configuration](#9-configuration)
10. [Rollout and Benchmarking Strategy](#10-rollout-and-benchmarking-strategy)
11. [Testing Strategy](#11-testing-strategy)
12. [Risks and Mitigations](#12-risks-and-mitigations)

---

## 1. Executive Summary

The Saturation Analyzer (V1 and V2) makes scaling decisions based on **instantaneous state** — current KV cache utilization and queue depth. It can only detect overload *after it has occurred*. This creates a fundamental detection lag: by the time saturation is observed, users are already experiencing degraded latency.

The **Throughput Analyzer** adds a complementary **rate-based** signal that measures the *velocity* of demand, not just the *level*. By tracking token arrival rate and comparing it to observed throughput capacity, the analyzer can detect when the current demand trajectory will exhaust capacity — before saturation occurs.

### How It Works

The Throughput Analyzer measures demand and supply in **tokens/sec**:

- **Demand rate**: How fast tokens are arriving (from request rate × average token count)
- **Supply rate**: How fast tokens can be processed (observed throughput per replica at saturation)

When demand rate exceeds supply rate, the analyzer produces a positive `RequiredCapacity` signal — even before the saturation analyzer detects any overload. This enables **anticipatory scaling** that starts provisioning capacity 20-40 seconds earlier than saturation-only detection.

### Relationship to Saturation Analyzer

| Aspect | Saturation Analyzer V2 | Throughput Analyzer |
|--------|----------------------|---------------------|
| Signal type | Instantaneous state (level) | Rate of change (velocity) |
| Units | Tokens (absolute capacity) | Tokens/sec (throughput) |
| Detects | Current overload | Approaching overload |
| Strength | Accurate when saturated | Early detection during ramps |
| Weakness | Reactive (detects after the fact) | May overshoot during transients |
| Scale-up | Based on demand vs capacity headroom | Based on demand rate vs throughput capacity |
| Scale-down | Based on spare capacity | Based on sustained low utilization rate |

The two analyzers run **in parallel** with OR logic for scale-up (either can trigger) and AND logic for scale-down (both must agree), following the Proposal 4 multi-analyzer framework.

---

## 2. Problem Analysis

### 2.1 The Detection Lag Problem

Consider a traffic ramp from 20 RPS to 60 RPS over 5 minutes with 4 replicas:

```
Time    RPS    KV Usage    Queue    Saturation Says    Throughput Says
t=0     20     40%         0        steady             steady
t=60    28     50%         0        steady             demand_rate rising
t=90    32     55%         0        steady             SCALE UP (rate > capacity)
t=120   40     65%         2        steady             scale up (continued)
t=150   48     78%         5        SCALE UP (now)     scale up (continued)
t=180   56     88%         12       SCALE UP           scale up
```

The saturation analyzer detects the problem at t=150 (2.5 minutes into the ramp). The throughput analyzer detects the trajectory at t=90 — **60 seconds earlier**. With a 3-5 minute pod startup time, this 60-second head start means replicas are ready 60 seconds sooner, reducing the window of degraded service.

### 2.2 Why Rate Matters

Rate-based detection is fundamentally about **derivatives** vs **levels**:

- **Saturation (level)**: "KV cache is at 78% — we're overloaded"
- **Throughput (rate)**: "Tokens are arriving at 15,000/sec but we can only process 12,000/sec — we will be overloaded in ~20 seconds"

The rate signal is especially valuable for:
- **Linear ramps**: Steady increase in traffic over minutes
- **Step changes**: Sudden traffic shifts (e.g., marketing campaign, model routing changes)
- **Diurnal patterns**: Predictable daily traffic curves where rate change is visible early

### 2.3 Where Rate Is Less Useful

The throughput analyzer adds less value when:
- **Traffic is stable**: No rate change to detect
- **Saturation is instantaneous**: Burst traffic that jumps directly to saturation (both analyzers detect at the same time)
- **Workload mix shifts**: Same RPS but different prompt/output lengths — this changes per-request cost without changing rate (saturation analyzer handles this via k1/k2)

---

## 3. Design Goals and Non-Goals

### Goals

- **G1**: Detect scaling need 30-60 seconds before the saturation analyzer during traffic ramps
- **G2**: Implement the `interfaces.Analyzer` interface (same as Saturation V2)
- **G3**: Use existing vLLM and scheduler metrics — no new metrics required from upstream
- **G4**: Integrate with the multi-analyzer framework (Proposal 4) for signal combination
- **G5**: Minimize false positives — avoid scaling up for transient rate spikes
- **G6**: Support heterogeneous GPU pools (different throughput capacity per variant)
- **G7**: Validate improvement via benchmarking before enabling by default

### Non-Goals

- Predicting future traffic patterns (forecasting, time-series models)
- Replacing the saturation analyzer (throughput is complementary, not a replacement)
- Adding new CRD fields (throughput uses the same `SaturationScalingConfig` with extended fields)
- Changing the reconciliation interval (throughput works within the existing 15s cycle)
- Per-request latency optimization (that's the SLO analyzer's domain — Proposal 3)

---

## 4. Metrics: Rate-Based Demand and Supply

### 4.1 Why Input and Output Tokens Must Be Measured Separately

Input tokens (prefill) and output tokens (decode) have fundamentally different computational costs in vLLM. In each continuous-batching scheduler step:

- **Decode**: Each active request consumes 1 token of the batch budget, generating 1 output token. Memory-bandwidth bound (KV cache reads).
- **Prefill**: Remaining batch budget processes input tokens in bulk. Compute-bound (matrix multiplications).

Processing 1000 input tokens takes ~1 scheduler step. Generating 1000 output tokens takes ~1000 steps. Treating them as equivalent produces meaningless throughput numbers. The throughput analyzer therefore uses a **dual-channel model** that tracks prefill and decode throughput independently.

### 4.2 Available Metrics

#### Timing metrics (primary — measure processing speed)

These measure processing speed per operation and work at any utilization level, not just at saturation.

| Metric | Type | vLLM Version | Collected? | Used For |
|--------|------|-------------|------------|----------|
| `vllm:request_prefill_time_seconds` | Histogram | v0.7+ | **No** (new) | Pure prefill computation time per request (excludes queue wait) |
| `vllm:request_decode_time_seconds` | Histogram | v0.7+ | **No** (new) | Pure decode computation time per request |
| `vllm:time_per_output_token_seconds` | Histogram | v0.6+ | **No** (new) | Inter-token latency (ITL) — decode speed per token |
| `vllm:time_to_first_token_seconds` | Histogram | v0.6+ | **No** (new) | TTFT — prefill + queue wait (fallback for prefill_time) |
| `vllm:num_requests_running` | Gauge | v0.6+ | **No** (new) | Active decode batch size (N) |

> **Note on prefill_time vs TTFT**: `request_prefill_time_seconds` measures the interval from `SCHEDULED` to first `NEW_TOKENS` — pure GPU computation. `time_to_first_token_seconds` measures from request arrival and includes queue wait time. Prefill time is preferred for supply estimation because it is not contaminated by queuing delays.

#### Token completion counters (secondary — measure throughput volume)

Already collected for saturation V2 (used to compute `AvgInputTokens` / `AvgOutputTokens`). The numerators of these existing queries provide token rates at zero additional cost.

| Metric | Type | Collected? | Used For |
|--------|------|------------|----------|
| `vllm:request_prompt_tokens_sum` | Counter | Yes (V2) | Input token completion rate (numerator of avg_input_tokens query) |
| `vllm:request_prompt_tokens_count` | Counter | Yes (V2) | Request completion rate |
| `vllm:request_generation_tokens_sum` | Counter | Yes (V2) | Output token completion rate (numerator of avg_output_tokens query) |
| `vllm:request_generation_tokens_count` | Counter | Yes (V2) | Request completion rate |
| `vllm:request_success_total` | Counter | Yes | Request completion rate (RPS) |

#### Saturation and queue metrics (already collected)

| Metric | Type | Used For |
|--------|------|----------|
| `vllm:kv_cache_usage_perc` | Gauge | KV cache utilization (saturation signal) |
| `vllm:num_requests_waiting` | Gauge | Queue depth (saturation signal) |
| `inference_extension_flow_control_queue_size` | Gauge | Scheduler queue depth (upstream demand) |
| `inference_extension_flow_control_queue_bytes` | Gauge | Scheduler queue bytes (upstream demand) |

### 4.3 New PromQL Queries

Five new queries, all per-pod:

```promql
# avg_prefill_time — Average prefill computation time per request (seconds)
# Pure GPU compute time, excludes queue wait (unlike TTFT)
max by (pod) (
    rate(vllm:request_prefill_time_seconds_sum{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
    /
    rate(vllm:request_prefill_time_seconds_count{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
)
```

```promql
# avg_itl — Average inter-token latency (seconds per output token)
# Measures decode speed: time between successive output tokens
max by (pod) (
    rate(vllm:time_per_output_token_seconds_sum{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
    /
    rate(vllm:time_per_output_token_seconds_count{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
)
```

```promql
# running_requests — Current number of active decode requests
max by (pod) (
    vllm:num_requests_running{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }
)
```

```promql
# avg_ttft — Fallback for prefill_time when request_prefill_time_seconds
# is unavailable (vLLM < 0.7). Includes queue wait.
max by (pod) (
    rate(vllm:time_to_first_token_seconds_sum{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
    /
    rate(vllm:time_to_first_token_seconds_count{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
)
```

```promql
# avg_decode_time — Average total decode time per request (seconds)
# Cross-validation: decode_time ≈ avg_output_tokens × ITL
max by (pod) (
    rate(vllm:request_decode_time_seconds_sum{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
    /
    rate(vllm:request_decode_time_seconds_count{
        namespace="{{.namespace}}", model_name="{{.modelID}}"
    }[5m])
)
```

> **Note on constants**: `VLLMTimeToFirstTokenSecondsSum`, `VLLMTimeToFirstTokenSecondsCount`, `VLLMTimePerOutputTokenSecondsSum`, and `VLLMTimePerOutputTokenSecondsCount` are already defined in `internal/constants/metrics.go`. New constants are needed for `request_prefill_time_seconds`, `request_decode_time_seconds`, and `num_requests_running`.

### 4.4 Rate Computation Methods

Rate signals come from two complementary sources:

**a) Timing-based rates (primary — measure processing speed):**

These derive throughput from per-operation latency measurements. They work at any utilization level and naturally decompose into prefill and decode channels:

```
prefill_throughput = (B - N) / prefill_time_per_token            (input tokens/sec)
decode_throughput  = N / ITL                                      (output tokens/sec)
```

Where `B = max_num_batched_tokens` (tokens), `N = num_requests_running` (requests; each consumes 1 token of budget per step, so `B - N` is in tokens — see §5.1), `N ≤ S = max_num_seqs`.

**b) Completion-based rates (secondary — cross-validation):**

```
input_token_rate  = rate(request_prompt_tokens_sum[5m])     ≈ prefill_throughput
output_token_rate = rate(request_generation_tokens_sum[5m]) ≈ decode_throughput
```

These should approximately match the timing-based rates. Divergence indicates metric staleness or workload shift.

**c) Arrival-based rates (from scheduler queue):**

The scheduler queue represents requests queued upstream before reaching any vLLM pod:

```
arrival_rate ≈ completion_rate + d(queue_size)/dt × avg_tokens_per_request
```

A growing queue indicates arrival rate > processing rate — the early warning signal.

---

## 5. Core Concepts

### 5.1 Dual-Channel Architecture

Input tokens and output tokens have fundamentally different costs in vLLM's continuous-batching scheduler.

#### Variables and Dimensional Analysis

| Variable | Unit | Source | Description |
|----------|------|--------|-------------|
| `B` | tokens | `--max-num-batched-tokens` (deployment arg) | Total token budget per scheduler step |
| `S` | requests | `--max-num-seqs` (deployment arg) | Max concurrent sequences (concurrency cap) |
| `N` | requests | `vllm:num_requests_running` (gauge) | Currently active decode requests, `N ≤ S` |
| `ITL` | seconds/token | `vllm:time_per_output_token_seconds` | Inter-token latency (time per output token) |
| `prefill_time` | seconds/request | `vllm:request_prefill_time_seconds` | Pure prefill compute time per request |

**Budget accounting per scheduler step:**

In each step, decode is autoregressive — each active request generates exactly **1 output token**, consuming 1 token of budget. Therefore:

```
decode_tokens_per_step  = N × 1 token/request = N tokens
prefill_tokens_per_step = B - N tokens         (remaining budget for chunked prefill)
```

The subtraction `B - N` is valid because each of the `N` decode requests uses exactly 1 token of the `B`-token budget. The concurrency limit `S = max_num_seqs` caps how large `N` can grow: `N ≤ S`.

```
┌──────────────────────────────────────────────────────────┐
│ Scheduler step budget: B tokens        Time: ~ITL        │
│                                                          │
│  ┌──────────────────────┐  ┌───────────────────────────┐ │
│  │ Decode: N tokens      │  │ Prefill: (B - N) tokens   │ │
│  │ N reqs × 1 tok/req    │  │ Chunked input processing  │ │
│  │ Memory-BW bound       │  │ Compute bound             │ │
│  │ N ≤ S (max_num_seqs)  │  │                           │ │
│  └──────────────────────┘  └───────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

The throughput analyzer models these as two independent **channels**:

| Property | Prefill Channel | Decode Channel |
|----------|-----------------|----------------|
| Token type | Input tokens | Output tokens |
| vLLM phase | Prefill (batched) | Decode (autoregressive) |
| Bottleneck | GPU compute (FLOPS) | Memory bandwidth + KV cache |
| Timing metric | `request_prefill_time_seconds` | `time_per_output_token_seconds` (ITL) |
| Budget per step | `B - N` tokens (residual after decode) | `N` tokens (`N` reqs × 1 tok/req) |
| Concurrency cap | N/A (limited by remaining budget) | `S = max_num_seqs` |
| Saturation V2 analog | k2 (compute-bound) | k1 (memory-bound) |

Both channels share the same total budget `B` per step, but consume it in different proportions depending on the workload mix.

### 5.2 Prefill Channel: Demand and Supply

**Prefill demand rate** (input tokens/sec) — how fast input tokens are arriving:

```
prefill_demand = rate(request_prompt_tokens_sum[5m])    (tokens being processed)
              + queue_growth_input_component             (unserved input demand)

queue_growth_input = max(0, Δ(scheduler_queue_tokens) / Δt) × input_fraction
input_fraction = avg_input_tokens / (avg_input_tokens + avg_output_tokens)
```

Under light load, `queue_growth ≈ 0` and demand ≈ observed throughput. Under overload, the queue component captures the unserved demand.

**Prefill supply rate** (input tokens/sec) — how fast input tokens can be processed:

```
prefill_tokens_per_step = B - N                                 (tokens, see §5.1)
steps_per_second        = 1 / ITL                               (scheduler step rate)
prefill_supply_per_replica = prefill_tokens_per_step / prefill_time_per_token

Equivalently:
  prefill_supply_per_replica = (B - N) / prefill_time_per_token  (input tokens/sec)

Where:
  B                     = max_num_batched_tokens (tokens, from deployment args)
  N                     = num_requests_running (requests; each uses 1 token → N tokens of budget)
  prefill_time          = avg request_prefill_time_seconds (seconds/request, pure GPU compute)
  prefill_time_per_token = prefill_time / avg_input_tokens (seconds/token)
  N ≤ S = max_num_seqs
```

**Dimensional check**: `(B - N)` is tokens (see §5.1), divided by `prefill_time_per_token` (seconds/token) = tokens/second.

**This is a capacity measure, not a throughput measure.** It gives the maximum rate at which input tokens *could* be processed at the current N, regardless of actual demand. If demand is lower, actual throughput is lower — but the channel *could* sustain this rate. Because both `B-N` and `prefill_time_per_token` reflect the current operating point, this capacity is inherently load-aware (see §5.6).

**Priority chain for prefill_time** (how to get the prefill computation time):

| Priority | Source | When Available | Notes |
|----------|--------|---------------|-------|
| 1 | `request_prefill_time_seconds` | vLLM v0.7+ | Pure prefill compute (SCHEDULED → first NEW_TOKENS) |
| 2 | `time_to_first_token_seconds` when `num_requests_waiting = 0` | vLLM v0.6+ | TTFT ≈ prefill_time when no queuing |
| 3 | min(TTFT) per input-length bucket | After sufficient observations | Minimum TTFT approximates pure compute |
| 4 | Derived from k2: `avg_input_tokens / ((B - N_avg) / step_rate)` | When saturation V2 has data | Theoretical estimate |

**Max prefill supply** (capacity ceiling):

```
max_prefill_supply = B / prefill_time_per_token
```

This is the supply when N = 0 (no decode competition, full budget for prefill). Used for P/D prefill-only replicas.

### 5.3 Decode Channel: Demand and Supply

**Decode demand rate** (output tokens/sec) — how fast output tokens are needed:

```
decode_demand = rate(request_generation_tokens_sum[5m])    (tokens being generated)
             + queue_growth_output_component                (requests waiting that will need decode)

queue_growth_output = max(0, Δ(scheduler_queue_tokens) / Δt) × output_fraction
output_fraction = avg_output_tokens / (avg_input_tokens + avg_output_tokens)
```

**Decode supply rate** (output tokens/sec) — how fast output tokens can be generated:

```
output_tokens_per_step = N × 1 token/request = N tokens          (each decode request → 1 output token)
step_time              = ITL                                       (seconds per step)
decode_supply_per_replica = output_tokens_per_step / step_time = N / ITL   (output tokens/sec)

Where:
  N   = num_requests_running (requests; produces N output tokens per step)
  ITL = avg time_per_output_token_seconds (seconds/token)
  N ≤ S = max_num_seqs
```

**Dimensional check**: `N` output tokens per step / `ITL` seconds per step = output tokens/second.

**This is a throughput measure, not a capacity measure.** Unlike prefill, decode cannot idle — each active request generates 1 output token per step unconditionally. So `N/ITL` is both the current throughput and the current capacity at this N. To estimate the **capacity ceiling** (max decode throughput), we need `N_max/ITL(N_max)` — but ITL(N_max) > ITL(current) due to load-dependent degradation (see §5.6).

This formula works at **any utilization level**: each active request generates 1 output token per ITL interval. No need to wait for saturation to observe this.

**Priority chain for ITL**:

| Priority | Source | When Available | Notes |
|----------|--------|---------------|-------|
| 1 | `time_per_output_token_seconds` | vLLM v0.6+ | Direct measurement, most accurate |
| 2 | `request_decode_time_seconds / avg_output_tokens` | vLLM v0.7+ | Derived from per-request decode time |
| 3 | From completion counters: `avg_output_tokens / (rate(generation_tokens_sum) / rate(generation_tokens_count))` | Always (V2 queries) | Less accurate, completion-time timing |

**Decode capacity ceiling** (bounded estimate):

Because ITL degrades with N (see §5.6), the true capacity ceiling `N_max/ITL(N_max)` cannot be computed from current ITL alone. The analyzer uses a **bounded ceiling** — the tighter of two estimates:

```
decode_capacity_per_replica = min(
    N_max / ITL_current,              // theoretical upper bound (overestimates: ITL at N_max > current ITL)
    max_observed(N / ITL),            // empirical ceiling (converges as system sees higher N)
)

N_max = min(S, ⌊k1 / avg_kv_tokens_per_request⌋)              (requests)

Where:
  S = max_num_seqs                                              (concurrency cap from deployment args)
  k1 = TotalKvCapacityTokens × KvCacheThreshold                (usable KV cache token slots)
  avg_kv_tokens_per_request = avg_input_tokens + avg_output_tokens/2
      (on average, a generating request holds its full input + half its output in KV cache)
```

- **Theoretical bound** (`N_max/ITL_current`): Uses current ITL, which is faster than ITL at N_max. Overestimates at low N, accurate at high N.
- **Empirical bound** (`max_observed(N/ITL)`): The highest decode throughput ever observed. Conservative at low N (peak is low because N was low), converges to true capacity as the system experiences higher load.
- **`min` of both**: At low N, the empirical bound is tighter (conservative). At high N, the theoretical bound is tighter (current ITL ≈ ITL at N_max). Either way, we get a reasonable estimate.

`N_max` is the smaller of the two bounds: the vLLM sequence slot limit (`S`) and the number of concurrent requests that fit in KV cache memory.

### 5.4 Combined Utilization

For replicas handling both prefill and decode (non-disaggregated):

```
prefill_utilization = prefill_demand / prefill_supply
decode_utilization  = decode_demand / decode_supply
effective_utilization = max(prefill_utilization, decode_utilization)
```

The system is bottlenecked on **whichever channel is more utilized**. Scaling decisions are based on the worse channel.

**Cross-validation**: The two channels share the total budget, so:

```
prefill_throughput + decode_throughput ≈ B / step_time
```

Where `step_time ≈ ITL` (each step generates 1 token per active request). If the observed rates violate this constraint, it indicates metric staleness.

### 5.5 Rate Smoothing (EMA)

Raw rate signals are noisy. The analyzer applies Exponential Moving Average (EMA) to smooth demand and supply rates per channel:

```
EMA_t = α × value_t + (1 - α) × EMA_{t-1}
```

Where α controls responsiveness vs stability:

| α value | Half-life (cycles) | Behavior |
|---------|-------------------|----------|
| 0.1 | ~7 cycles (~105s) | Very smooth, slow to react |
| 0.2 | ~3.5 cycles (~52s) | Moderate smoothing |
| 0.3 | ~2.3 cycles (~35s) | Default — responsive to ramps, filters spikes |
| 0.5 | ~1.4 cycles (~21s) | Fast reaction, limited smoothing |

Default: α = 0.3, which filters sub-30s transients while responding within 2-3 cycles to sustained changes.

**EMA per-variant per-channel**: Each variant tracks independent EMA for prefill and decode because different GPU types have different prefill speed vs decode speed trade-offs.

### 5.6 Load-Dependent Timing

ITL and prefill_time_per_token are **not constants** — they degrade as load increases:

```
Per-token time (seconds)
    ▲
    │                          ╱ prefill_time_per_token(N)
    │                        ╱   (memory BW contention from decode)
    │                 ╱────╱
    │         ╱─────╱
    │   ╱────╱
    │──╱ ← ITL(N)
    │╱   (more KV cache reads per step as N grows)
    └──────────────────────────────► N (concurrent decode requests)
    0                               S = max_num_seqs
```

**Why timing degrades with N:**

| Metric | Mechanism | Effect |
|--------|-----------|--------|
| ITL | More concurrent decode requests → more KV cache reads per step → memory bandwidth saturation | ITL increases sublinearly with N |
| prefill_tpt | Concurrent decode operations compete for memory bandwidth during prefill compute | prefill_tpt increases with N even though prefill is compute-bound |

**Consequences for supply estimation:**

The throughput formulas `(B-N)/prefill_tpt` and `N/ITL` use **instantaneous** timing values that already reflect the current load level. However, the two channels respond differently to load changes, creating an asymmetry in how supply should be estimated:

**Prefill capacity = `(B-N)/prefill_tpt`** — this is the **max processing rate** of the prefill channel at the current N. It's a capacity measure: if input tokens arrived at this rate, they would be processed without delay. The system may process fewer (if demand is lower), but cannot process more.

- At low N: high capacity (large budget B-N, fast timing) — but NOT achievable at high N
- At high N: low capacity (small budget, slow timing) — this is the realistic operating condition
- **Peak tracking overestimates**: a peak observed at low N would never be reached at high N

**Decode throughput = `N/ITL`** — this is the **actual generation rate**. Each active request produces 1 output token per step; you cannot idle decode slots. This IS the throughput.

- At low N: low throughput (few requests, even though ITL is fast)
- At high N: high throughput (many requests, despite slower ITL) — total N/ITL increases because N grows faster than ITL degrades
- **Peak tracking is safe**: the peak occurs at high N, which is the operating point near capacity

```
Channel throughput
    ▲
    │          ╭──── decode N/ITL(N): peak at high N ✓
    │        ╱      (safe for peak tracking)
    │      ╱
    │    ╱
    │  ╱
    │╱  prefill (B-N)/prefill_tpt(N): peak at low N ✗
    │ ╲     (peak tracking overestimates capacity at high N)
    │   ╲
    │     ╲────
    └──────────────────────────────► N
    0                               S = max_num_seqs
```

**Implication for supply estimation strategy:**

| Channel | Supply estimation | Rationale |
|---------|------------------|-----------|
| Prefill | **Current capacity**: `(B-N)/prefill_tpt` at current N | Formula gives correct capacity at current operating point. No peak tracking — peak at low N is misleading. |
| Decode | **Bounded ceiling**: `min(N_max/ITL, max_observed(N/ITL))` | Theoretical ceiling `N_max/ITL` may overestimate (ITL at N_max > current ITL). Empirical peak `max(N/ITL)` converges as system sees higher N. Take the tighter bound. |

**Timing baselines for degradation detection:**

Track the minimum observed per-token times as no-contention baselines:
```
ITL_baseline         = min observed ITL across all cycles         (fastest decode)
prefill_tpt_baseline = min observed prefill_tpt across all cycles (fastest prefill)

timing_degradation_decode  = ITL_current / ITL_baseline           (≥ 1.0)
timing_degradation_prefill = prefill_tpt_current / prefill_tpt_baseline  (≥ 1.0)
```

These ratios indicate how much timing has degraded from best-case. High ratios signal that the system is approaching capacity — a leading indicator that precedes queue growth.

**Connection to Saturation V2**: The peak of the `N/ITL(N)` curve corresponds approximately to saturation V2's k2 (compute-bound capacity). When saturation V2 has observed k2, it can serve as an independent capacity reference for cross-validation.

**P/D disaggregated replicas are unaffected** by the coupling issue:
- Prefill-only (N≈0): N is stable → timing is stable → current capacity is accurate
- Decode-only (N≈N_max): N is stable at ceiling → timing is stable → current throughput ≈ capacity

The load-dependency problem is specific to **non-disaggregated replicas** where N varies dynamically.

---

## 6. Type Definitions

### 6.1 ThroughputScalingConfig

The throughput analyzer is configured via additional fields on `SaturationScalingConfig` (extending, not replacing). This keeps a single config surface.

```go
// Additional fields on SaturationScalingConfig (or a separate ThroughputConfig embedded within):

type ThroughputScalingConfig struct {
    // EnableThroughput enables the throughput analyzer alongside the saturation analyzer.
    // When false (default), only saturation analysis is used.
    EnableThroughput bool `yaml:"enableThroughput,omitempty"`

    // ThroughputWeight is the relative weight of throughput signals vs saturation signals.
    // Used in multi-analyzer signal combination (Proposal 4).
    // Default: 0.8 (throughput is slightly less authoritative than saturation).
    ThroughputWeight float64 `yaml:"throughputWeight,omitempty"`

    // RateSmoothingAlpha is the EMA alpha for rate smoothing (0.0-1.0).
    // Higher values = more responsive, lower values = more stable.
    // Default: 0.3
    RateSmoothingAlpha float64 `yaml:"rateSmoothingAlpha,omitempty"`

    // RateLookbackWindow is the number of cycles to retain for rate history.
    // Default: 10 (covering ~150s at 15s cycle)
    RateLookbackWindow int `yaml:"rateLookbackWindow,omitempty"`

    // ThroughputScaleUpThreshold is the utilization threshold for the throughput analyzer.
    // Scale up when demand_rate / supply_rate > threshold.
    // Default: 0.85 (same as saturation default)
    ThroughputScaleUpThreshold float64 `yaml:"throughputScaleUpThreshold,omitempty"`

    // ThroughputScaleDownBoundary is the utilization boundary for the throughput analyzer.
    // Scale down when demand_rate / supply_rate < boundary.
    // Default: 0.70 (same as saturation default)
    ThroughputScaleDownBoundary float64 `yaml:"throughputScaleDownBoundary,omitempty"`
}
```

### 6.2 ReplicaMetrics Additions

New fields on the existing `ReplicaMetrics` struct (`internal/interfaces/saturation_analyzer.go`):

```go
// --- New fields for Throughput Analyzer ---

// RunningRequests is the number of requests currently in the decode phase.
// Sourced from vllm:num_requests_running gauge.
// This is the active decode batch size (N in the dual-channel model).
RunningRequests int

// AvgPrefillTime is the average prefill computation time per request (seconds).
// Sourced from rate(vllm:request_prefill_time_seconds_sum) / rate(..._count).
// Pure GPU compute time — excludes queue wait (unlike TTFT).
// Zero when metric is unavailable (vLLM < 0.7); falls back to TTFT.
AvgPrefillTime float64

// AvgITL is the average inter-token latency (seconds per output token).
// Sourced from rate(vllm:time_per_output_token_seconds_sum) / rate(..._count).
// Measures decode speed: time between successive output tokens.
AvgITL float64

// AvgTTFT is the average time to first token (seconds).
// Sourced from rate(vllm:time_to_first_token_seconds_sum) / rate(..._count).
// Includes queue wait + prefill time. Used as fallback when AvgPrefillTime is unavailable.
AvgTTFT float64

// AvgDecodeTime is the average total decode time per request (seconds).
// Sourced from rate(vllm:request_decode_time_seconds_sum) / rate(..._count).
// Cross-validation: AvgDecodeTime ≈ AvgOutputTokens × AvgITL.
AvgDecodeTime float64
```

### 6.3 Throughput-Specific Internal Types

```go
// File: internal/throughput/types.go

package throughput

// ChannelMetrics holds demand and supply for one channel (prefill or decode).
type ChannelMetrics struct {
    // DemandRate is the token arrival rate for this channel (tokens/sec).
    DemandRate float64

    // SupplyRate is the max token processing rate for this channel (tokens/sec).
    SupplyRate float64

    // Utilization is DemandRate / SupplyRate (0.0+).
    Utilization float64
}

// ReplicaThroughput holds per-replica rate metrics used by the throughput analyzer.
type ReplicaThroughput struct {
    PodName         string
    VariantName     string
    AcceleratorName string

    // Prefill channel metrics
    PrefillTimePerToken float64 // seconds per input token (prefill_time / avg_input_tokens)
    PrefillBudgetTokens int     // B - N tokens (residual budget for prefill per step; see §5.1)
    PrefillThroughput   float64 // PrefillBudgetTokens / prefill_time_per_token (input tokens/sec)

    // Decode channel metrics
    ITL              float64 // seconds per output token (ITL)
    RunningRequests  int     // N (active decode requests, N ≤ S = max_num_seqs)
    DecodeThroughput float64 // N output_tokens_per_step / ITL (output tokens/sec)

    // Request-level metrics
    RequestRate float64 // requests completed per second
}

// PrefillChannelHistory tracks smoothed rate signals for the prefill channel.
// Prefill supply uses current capacity (not peak tracking) — see §5.6.
type PrefillChannelHistory struct {
    // DemandEMA is the exponentially smoothed demand rate (input tokens/sec).
    DemandEMA float64

    // SupplyEMA is the exponentially smoothed supply rate (input tokens/sec).
    // Updated from current capacity: (B-N)/prefill_tpt at current N.
    SupplyEMA float64

    // TimingBaseline is the minimum observed prefill_time_per_token (seconds/token).
    // Represents no-contention prefill speed. Used for degradation detection.
    TimingBaseline float64
}

// DecodeChannelHistory tracks smoothed rate signals for the decode channel.
// Decode supply uses a bounded ceiling estimate — see §5.6.
type DecodeChannelHistory struct {
    // DemandEMA is the exponentially smoothed demand rate (output tokens/sec).
    DemandEMA float64

    // SupplyEMA is the exponentially smoothed supply rate (output tokens/sec).
    // Updated from bounded ceiling: min(N_max/ITL, MaxObservedThroughput).
    SupplyEMA float64

    // MaxObservedThroughput is the peak decode throughput (N/ITL) ever observed.
    // Safe for peak tracking because decode throughput peaks at high N (see §5.6).
    MaxObservedThroughput float64

    // TimingBaseline is the minimum observed ITL (seconds/token).
    // Represents no-contention decode speed. Used for degradation detection.
    TimingBaseline float64
}

// RateHistory tracks smoothed rate signals over time for a variant (both channels).
type RateHistory struct {
    Prefill PrefillChannelHistory
    Decode  DecodeChannelHistory

    // PreviousQueueTokens is the scheduler queue token count from the previous cycle.
    PreviousQueueTokens float64

    // CycleCount tracks how many cycles this history has been updated.
    CycleCount int
}
```

---

## 7. Throughput Analyzer Design

### 7.1 Interface

The Throughput Analyzer implements the same `interfaces.Analyzer` interface as the Saturation Analyzer V2:

```go
type Analyzer interface {
    Name() string
    Analyze(ctx context.Context, input AnalyzerInput) (*AnalyzerResult, error)
}
```

### 7.2 Implementation

```go
// File: internal/throughput/analyzer.go

package throughput

type ThroughputAnalyzer struct {
    // rateHistory tracks per-variant rate signals across cycles.
    // Key: "modelID|variantName"
    rateHistory map[string]*RateHistory

    // config holds throughput-specific configuration.
    config ThroughputScalingConfig

    // capacityStore is shared with the saturation analyzer for cross-referencing
    // capacity data (k2 values) when deriving throughput capacity.
    capacityStore *saturation_v2.CapacityKnowledgeStore
}

func NewThroughputAnalyzer(
    config ThroughputScalingConfig,
    store *saturation_v2.CapacityKnowledgeStore,
) *ThroughputAnalyzer {
    return &ThroughputAnalyzer{
        rateHistory:   make(map[string]*RateHistory),
        config:        config,
        capacityStore: store,
    }
}

func (a *ThroughputAnalyzer) Name() string {
    return "throughput"
}
```

### 7.3 Core Algorithm: `Analyze`

```
Analyze(ctx, input):
  config := input.Config (ThroughputScalingConfig fields)
  role := input.PDRole  // RolePrefill, RoleDecode, RoleBoth, or RoleUnknown

  1. PER-REPLICA THROUGHPUT COMPUTATION — For each replica in input.ReplicaMetrics:

     a. Determine prefill_time_per_token:
        If rm.AvgPrefillTime > 0 AND rm.AvgInputTokens > 0:
           prefill_time_per_token = rm.AvgPrefillTime / rm.AvgInputTokens
        Elif rm.AvgTTFT > 0 AND rm.QueueLength == 0 AND rm.AvgInputTokens > 0:
           prefill_time_per_token = rm.AvgTTFT / rm.AvgInputTokens  // TTFT ≈ prefill when no queue
        Else:
           prefill_time_per_token = 0  // unavailable

     b. Compute per-replica channel throughput:
        B := getMaxNumBatchedTokens(variant)  // tokens, from deployment args (VLLMEngineParams)
        S := getMaxNumSeqs(variant)            // requests, concurrency cap
        N := rm.RunningRequests                // requests (N ≤ S)

        // Prefill channel: budget = B - N tokens (N reqs × 1 tok/req = N tokens, see §5.1)
        If prefill_time_per_token > 0:
           prefillBudgetTokens = B - N         // tokens available for prefill
           prefillThroughput = float64(prefillBudgetTokens) / prefill_time_per_token
        Else:
           prefillThroughput = 0

        // Decode channel: N reqs produce N output tokens per step, step time = ITL
        If rm.AvgITL > 0 AND N > 0:
           decodeThroughput = float64(N) / rm.AvgITL   // N output tokens / ITL seconds
        Else:
           decodeThroughput = 0

     c. Update timing baselines:
        history.Prefill.TimingBaseline = min(existing, prefill_time_per_token)
        history.Decode.TimingBaseline  = min(existing, rm.AvgITL)

     d. Cross-validate with completion-rate counters:
        // rate(request_prompt_tokens_sum) should ≈ prefillThroughput
        // rate(request_generation_tokens_sum) should ≈ decodeThroughput
        // Log warning if divergence > 2x (metric staleness indicator)

     e. Build ReplicaThroughput struct

  2. PER-VARIANT DUAL-CHANNEL AGGREGATION — Group by variant:
     For each variant:

       a. Compute demand rates per channel:
          // Prefill demand = observed prefill throughput + queue growth (input portion)
          prefillDemand = Σ replica.PrefillThroughput
          decodeDemand  = Σ replica.DecodeThroughput

          // Add queue growth component (split by input/output ratio)
          If schedulerQueue != nil:
             queueTokens_t = schedulerQueue.QueueBytes / BytesPerToken
                           + schedulerQueue.QueueSize × avgOutputTokens
             queueGrowth = max(0, queueTokens_t - previousQueueTokens) / cycleDuration
             inputFraction = avgInputTokens / (avgInputTokens + avgOutputTokens)
             prefillDemand += queueGrowth × inputFraction
             decodeDemand  += queueGrowth × (1 - inputFraction)

       b. Compute supply rates per channel (see §5.6 for rationale):

          // PREFILL: Use current capacity (not peak tracking).
          // (B-N)/prefill_tpt is a capacity measure that's already load-aware.
          // Sum across replicas to get total prefill capacity at current operating point.
          prefillSupply = Σ replica.PrefillThroughput   // = Σ (B-N_i)/prefill_tpt_i

          // DECODE: Bounded ceiling estimate.
          // Update empirical peak from current observations (safe: peaks at high N).
          For each replica in this variant:
             history.Decode.MaxObservedThroughput = max(existing, replica.DecodeThroughput)

          // Theoretical bound: N_max / median(ITL) — overestimates at low N
          N_max = min(S, ⌊k1 / avg_kv_per_request⌋)
          medianITL = median(replica.ITL for ready replicas)
          theoreticalDecode = float64(N_max) / medianITL

          // Tighter bound: min(theoretical, empirical peak × readyReplicas)
          decodeCapacityPerReplica = min(theoreticalDecode, history.Decode.MaxObservedThroughput)
          decodeSupply = readyReplicas × decodeCapacityPerReplica

       c. Apply EMA smoothing per channel:
          history.Prefill.DemandEMA = α × prefillDemand + (1-α) × history.Prefill.DemandEMA
          history.Prefill.SupplyEMA = α × prefillSupply + (1-α) × history.Prefill.SupplyEMA
          history.Decode.DemandEMA  = α × decodeDemand  + (1-α) × history.Decode.DemandEMA
          history.Decode.SupplyEMA  = α × decodeSupply  + (1-α) × history.Decode.SupplyEMA

       d. Select active channel(s) based on P/D role:
          Switch role:
            case RolePrefill:
               effectiveDemand = history.Prefill.DemandEMA
               effectiveSupply = history.Prefill.SupplyEMA
            case RoleDecode:
               effectiveDemand = history.Decode.DemandEMA
               effectiveSupply = history.Decode.SupplyEMA
            default (RoleBoth / RoleUnknown):
               // Use the more constrained channel
               prefillUtil = history.Prefill.DemandEMA / history.Prefill.SupplyEMA
               decodeUtil  = history.Decode.DemandEMA  / history.Decode.SupplyEMA
               If prefillUtil >= decodeUtil:
                  effectiveDemand = history.Prefill.DemandEMA
                  effectiveSupply = history.Prefill.SupplyEMA
               Else:
                  effectiveDemand = history.Decode.DemandEMA
                  effectiveSupply = history.Decode.SupplyEMA

       e. Build VariantCapacity:
          // PerReplicaCapacity = supply / ready_replicas (in active channel's tokens/sec)
          vc = VariantCapacity{
              VariantName:        variant.Name,
              PerReplicaCapacity: effectiveSupply / readyReplicas,
              TotalCapacity:      effectiveSupply,
              TotalDemand:        effectiveDemand,
              Utilization:        effectiveDemand / effectiveSupply,
          }

  3. MODEL-LEVEL AGGREGATION:
     totalSupply = Σ variant.effectiveSupply
     totalDemand = Σ variant.effectiveDemand
     utilization = totalDemand / totalSupply
     anticipatedSupply = Σ ((readyReplicas + pendingReplicas) × perReplicaCapacity)

  4. SCALING SIGNAL COMPUTATION:
     requiredCapacity = totalDemand / scaleUpThreshold - anticipatedSupply
     spareCapacity = totalSupply - totalDemand / scaleDownBoundary

     If requiredCapacity < 0: requiredCapacity = 0
     If spareCapacity < 0:    spareCapacity = 0

     // Warmup guard: suppress signals until EMA stabilizes
     If minCycleCount < warmupCycles:
        requiredCapacity = 0
        spareCapacity = 0

  5. RETURN AnalyzerResult:
     return &AnalyzerResult{
         AnalyzerName:      "throughput",
         VariantCapacities: variantCapacities,
         TotalSupply:       totalSupply,
         TotalDemand:       totalDemand,
         Utilization:       utilization,
         RequiredCapacity:  requiredCapacity,
         SpareCapacity:     spareCapacity,
     }
```

### 7.4 Demand Rate Computation

Demand is computed separately for each channel:

**Prefill demand** (input tokens/sec):
```
prefill_demand = Σ(prefill_throughput_per_replica)      (observed processing rate)
               + queue_growth × input_fraction           (unserved input demand)
```

**Decode demand** (output tokens/sec):
```
decode_demand = Σ(decode_throughput_per_replica)         (observed generation rate)
              + queue_growth × output_fraction            (requests that will need decode)
```

**Queue growth computation**:
```
queue_tokens_t = scheduler_queue_bytes / 4 + scheduler_queue_size × avg_output_tokens
queue_growth = max(0, queue_tokens_t - queue_tokens_{t-1}) / cycle_duration
input_fraction  = avg_input_tokens / (avg_input_tokens + avg_output_tokens)
output_fraction = 1 - input_fraction
```

Only positive growth counts (negative = queue draining = supply exceeds demand).

### 7.5 Supply Rate Estimation

Supply is derived from timing metrics and works at **any utilization level** — no need to wait for saturation. The two channels use **different estimation strategies** because of load-dependent timing (see §5.6).

**Prefill supply — current capacity** (no peak tracking):
```
prefill_supply_per_replica = (B - N) / prefill_time_per_token    (input tokens/sec)
prefill_supply_total = Σ (B - N_i) / prefill_tpt_i              (summed across ready replicas)

Where:
  B = max_num_batched_tokens (tokens, from VLLMEngineParams)
  N = num_requests_running (requests; uses N tokens of budget, see §5.1)
  prefill_time_per_token = AvgPrefillTime / AvgInputTokens (seconds/token)
  N ≤ S = max_num_seqs
```

This is a **capacity** measure — the maximum rate the prefill channel can sustain at the current N. Both `B-N` and `prefill_tpt` reflect the current operating point, so the capacity is inherently load-aware. Peak tracking is NOT used because the prefill peak occurs at low N, which overestimates capacity at high N (see §5.6).

**Decode supply — bounded ceiling estimate**:
```
decode_throughput_per_replica = N / ITL                          (output tokens/sec, current)

decode_capacity_per_replica = min(
    N_max / median(ITL),                                        (theoretical upper bound)
    max_observed(N / ITL),                                      (empirical ceiling)
)

decode_supply_total = readyReplicas × decode_capacity_per_replica

Where:
  N   = num_requests_running (produces N output tokens per step)
  ITL = AvgITL (seconds/token, from time_per_output_token_seconds)
  N_max = min(S, ⌊k1 / avg_kv_tokens_per_request⌋) (max concurrent decode)
  N ≤ S = max_num_seqs
```

The theoretical bound (`N_max/ITL`) overestimates because ITL at N_max would be higher than current ITL. The empirical bound (`max_observed(N/ITL)`) converges as the system sees higher load — safe because decode throughput peaks at high N (see §5.6). Taking `min` gives the tighter bound at each stage.

**Timing baselines** (for degradation detection):
```
ITL_baseline         = min observed ITL         (fastest decode, no contention)
prefill_tpt_baseline = min observed prefill_tpt (fastest prefill, no contention)

decode_degradation  = ITL_current / ITL_baseline         (≥ 1.0)
prefill_degradation = prefill_tpt / prefill_tpt_baseline (≥ 1.0)
```

High degradation ratios signal approaching capacity before queue growth — a leading indicator for scale-up.

**Cross-validation with completion-rate counters**:
```
rate(request_prompt_tokens_sum)     ≈ Σ prefill_throughput_per_replica
rate(request_generation_tokens_sum) ≈ Σ decode_throughput_per_replica
```

### 7.6 Per-Variant Aggregation

The throughput analyzer produces `VariantCapacity` structs using the **active channel** determined by P/D role:

| Field | Saturation V2 (tokens) | Throughput — Prefill (input tok/s) | Throughput — Decode (output tok/s) |
|-------|------------------------|------------------------------------|------------------------------------|
| PerReplicaCapacity | median(min(k1, k2)) | median((B-N)/prefill_tpt) at current N | min(N_max/ITL, max_observed(N/ITL)) |
| TotalCapacity | replicas × per_replica | Σ (B-N_i)/prefill_tpt_i | replicas × per_replica |
| TotalDemand | Σ(tokens_in_use + queue) | EMA(prefill_demand) | EMA(decode_demand) |
| Utilization | demand/capacity | prefill_demand/prefill_supply | decode_demand/decode_supply |
| Supply strategy | Median of min(k1,k2) | Current capacity (load-aware, §5.6) | Bounded ceiling (peak tracking safe, §5.6) |

For non-disaggregated replicas (`RoleBoth`), the analyzer selects whichever channel has higher utilization — the bottleneck channel drives the scaling signal.

### 7.7 P/D Disaggregation Integration

The dual-channel model maps directly to P/D roles from the `pdrole` package:

```
┌───────────────────────────────────────────────────────────────────────┐
│              Non-disaggregated (RoleBoth / RoleUnknown)               │
│                                                                       │
│  Both channels active on same replicas:                               │
│  prefill_supply = (B - N) / prefill_time_per_token  (input tok/s)    │
│  decode_supply  = N / ITL                            (output tok/s)   │
│  utilization    = max(prefill_util, decode_util)                      │
│  Budget coupled: increasing N reduces prefill budget (B - N)          │
│  N ≤ S = max_num_seqs                                                │
└───────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐  ┌──────────────────────────────────┐
│  Prefill replica (RolePre)   │  │  Decode replica (RoleDecode)     │
│                              │  │                                  │
│  Prefill channel ONLY:       │  │  Decode channel ONLY:            │
│  N ≈ 0 (no active decode)    │  │  N ≈ N_max (max concurrency)     │
│  supply = B / prefill_tpt    │  │  N_max = min(S, ⌊k1/kv_per_req⌋)│
│  demand = input_arrival      │  │  supply = N_max / ITL            │
│                              │  │  demand = output_demand          │
│  KV cache: transient         │  │  KV cache: long-held             │
│  (produce → transfer)        │  │  (held for full generation)      │
│  Bottleneck: GPU compute     │  │  Bottleneck: mem bandwidth       │
└──────────────────────────────┘  └──────────────────────────────────┘
```

**Key simplifications for P/D replicas:**

- **Prefill-only**: `N ≈ 0` (no ongoing decode), so the full `B` tokens of budget go to prefill. Supply simplifies to `B / prefill_time_per_token`. KV cache metrics are less relevant (cache is transient, transferred to decode pods).

- **Decode-only**: `N ≈ N_max = min(S, ⌊k1 / avg_kv_tokens_per_request⌋)` — the maximum concurrent decode requests, limited by sequence slots (`S = max_num_seqs`) or KV cache memory (`k1`). Supply simplifies to `N_max / ITL`. Queue depth is less relevant (requests arrive already prefilled).

**Engine behavior**: The engine detects P/D role via `pdrole.GetDeploymentPDRole()` and passes `PDRole` through `AnalyzerInput`. The throughput analyzer uses the role to select the active channel. Each role group is analyzed independently (grouped by `modelID|namespace|PDRole` as described in the P/D disaggregation issue).

---

## 8. Multi-Analyzer Integration

### 8.1 Signal Combination Logic

The engine combines signals from the saturation and throughput analyzers using the Proposal 4 framework:

```
satResult = saturationAnalyzer.Analyze(ctx, input)    // tokens
thrResult = throughputAnalyzer.Analyze(ctx, input)     // tokens/sec

// OR logic for scale-up: either analyzer can trigger
shouldScaleUp = (satResult.RequiredCapacity > 0) OR (thrResult.RequiredCapacity > 0)

// AND logic for scale-down: both must agree
shouldScaleDown = (satResult.SpareCapacity > 0) AND (thrResult.SpareCapacity > 0)
```

**Scale-up target** (uses the more aggressive analyzer, weighted):

```
If shouldScaleUp:
    // Convert both to "replicas needed" for comparability
    sat_replicas_needed = satResult.RequiredCapacity / sat_per_replica_capacity
    thr_replicas_needed = thrResult.RequiredCapacity / thr_per_replica_capacity

    // Weighted maximum
    replicas_needed = max(
        w_sat × sat_replicas_needed,
        w_thr × thr_replicas_needed,
    )
```

**Scale-down target** (uses the more conservative analyzer, weighted):

```
If shouldScaleDown:
    sat_replicas_removable = satResult.SpareCapacity / sat_per_replica_capacity
    thr_replicas_removable = thrResult.SpareCapacity / thr_per_replica_capacity

    // Weighted minimum
    replicas_removable = min(
        sat_replicas_removable / w_sat,
        thr_replicas_removable / w_thr,
    )
```

### 8.2 OR Scale-Up / AND Scale-Down

The asymmetric logic is deliberate:

**OR for scale-up**: Failing to scale up when needed causes SLO violations. Either analyzer detecting a need is sufficient grounds to act. The throughput analyzer may detect it earlier (rate is rising), or the saturation analyzer may detect it when throughput has a false negative (e.g., stable rate but workload mix shift).

**AND for scale-down**: Scaling down prematurely causes unnecessary SLO violations when traffic returns. Both analyzers must agree that capacity is safe to remove. This prevents:
- Throughput sees low rate but saturation sees high utilization (workload is compute-heavy)
- Saturation sees spare capacity but throughput sees rising rate (ramp starting)

### 8.3 Engine Changes

The engine runs both analyzers and combines their results:

```go
// In engine.runWithMultiAnalyzer():

// Run analyzers in parallel (independent)
satResult, satErr := e.saturationAnalyzer.Analyze(ctx, input)
thrResult, thrErr := e.throughputAnalyzer.Analyze(ctx, input)

// Throughput failure is non-fatal (saturation alone is sufficient)
if thrErr != nil {
    log.Info("throughput analyzer failed, using saturation only", "error", thrErr)
    // Fall through with thrResult = nil
}

// Combine signals
combined := e.combineAnalyzerResults(satResult, thrResult, config)

// Build scaling plan from combined result
targets, plan := e.BuildScalingPlan(ctx, combined, variantStates, config)
```

The `combineAnalyzerResults` method applies the OR/AND logic and produces a unified `AnalyzerResult` with the most aggressive scale-up signal and most conservative scale-down signal.

---

## 9. Configuration

### 9.1 Example Configuration

```yaml
saturationScaling:
  kvCacheThreshold: 0.80
  queueLengthThreshold: 3
  analyzerName: "saturation"
  scaleUpThreshold: 0.85
  scaleDownBoundary: 0.70

  # Throughput analyzer (complementary to saturation)
  enableThroughput: true
  throughputWeight: 0.8
  rateSmoothingAlpha: 0.3
  throughputScaleUpThreshold: 0.85
  throughputScaleDownBoundary: 0.70
```

### 9.2 Default Values

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| enableThroughput | false | Opt-in until validated via benchmarking |
| throughputWeight | 0.8 | Slightly less authoritative than saturation (1.0) due to prediction uncertainty |
| rateSmoothingAlpha | 0.3 | Filters sub-30s transients, responsive to sustained changes within 2-3 cycles |
| rateLookbackWindow | 10 | ~150s of history at 15s cycle |
| throughputScaleUpThreshold | 0.85 | Same as saturation default for consistency |
| throughputScaleDownBoundary | 0.70 | Same as saturation default for consistency |
| warmupCycles | 4 | ~60s of data before making decisions (EMA needs initial samples) |

---

## 10. Rollout and Benchmarking Strategy

### 10.1 Phased Rollout

**Phase 1: Infrastructure** (metrics collection)
- Add timing metric queries (avg_prefill_time, avg_itl, running_requests, avg_ttft, avg_decode_time) to collector
- Add new constants for `request_prefill_time_seconds`, `request_decode_time_seconds` in `internal/constants/metrics.go`
- Add new fields to `ReplicaMetrics` (RunningRequests, AvgPrefillTime, AvgITL, AvgTTFT, AvgDecodeTime)
- No behavioral change — data collection only

**Phase 2: Analyzer Implementation**
- Implement `ThroughputAnalyzer` in `internal/throughput/` package
- Unit tests with simulated rate scenarios
- No integration with engine yet

**Phase 3: Engine Integration**
- Wire throughput analyzer into engine, gated by `enableThroughput: true`
- Implement `combineAnalyzerResults` for OR/AND signal combination
- Integration tests with both analyzers

**Phase 4: Benchmarking**
- Run benchmark scenario (Section 10.2) comparing saturation-only vs saturation+throughput
- Measure detection latency improvement and overshoot/false-positive rate
- If benchmarks confirm improvement, enable by default in a future release

### 10.2 Benchmark Scenario

From Proposal 2 Section 2:

**Load profile**: Linear ramp from 30% to 90% utilization over 5 minutes
- Start: 20 RPS with 4 replicas (40% utilization)
- Ramp: 20→60 RPS linearly over 5 minutes
- Sustained: 60 RPS for 10 minutes
- Ramp-down: 60→20 RPS over 5 minutes

**Hardware**: Homogeneous pool (4× A100-80G)

**Workload**: Fixed prompt size (512 input, 256 output) for predictable per-request load

**Measured metrics**:

| Metric | Target |
|--------|--------|
| Detection latency (time from ramp start to scale-up decision) | ≥30s earlier with throughput |
| P95 TTFT during ramp | ≥40% reduction with throughput |
| Overshoot (excess replicas after stabilization) | ≤1 replica overshoot |
| False positive rate (reversed scale-ups) | <5% of decisions |

**Variants** (A/B comparison):
- **Control**: `analyzerName: "saturation"` (V2 saturation only)
- **Treatment**: `analyzerName: "saturation"` + `enableThroughput: true`

---

## 11. Testing Strategy

### 11.1 Unit Tests

**Per-replica throughput computation:**
- `TestPrefillThroughput_FromPrefillTime` — prefill_supply = (B-N) / (prefill_time / avg_input_tokens)
- `TestPrefillThroughput_FallbackToTTFT` — uses TTFT when prefill_time unavailable and queue empty
- `TestPrefillThroughput_NoData` — returns 0 when neither prefill_time nor TTFT available
- `TestDecodeThroughput_FromITL` — decode_supply = N / ITL
- `TestDecodeThroughput_ZeroRunning` — returns 0 when N=0 (no active decode)

**Dual-channel demand:**
- `TestDemandRate_NoQueue` — demand = observed throughput when queue is empty (per channel)
- `TestDemandRate_GrowingQueue` — queue growth split by input_fraction / output_fraction
- `TestDemandRate_ShrinkingQueue` — queue_growth clamped to 0 (no negative contribution)

**EMA smoothing:**
- `TestEMA_StableRate` — EMA converges to stable value
- `TestEMA_RampUp` — EMA tracks rising rate with configurable lag
- `TestEMA_Spike` — EMA dampens transient spike (short spike doesn't trigger scaling)
- `TestEMA_AlphaEffect` — higher alpha = faster response, lower alpha = more stable
- `TestEMA_PerChannel` — prefill and decode channels smoothed independently

**Supply estimation (load-aware):**
- `TestPrefillSupply_CurrentCapacity` — prefill supply = Σ(B-N_i)/prefill_tpt_i (not peak tracked)
- `TestPrefillSupply_DecreasesWithN` — prefill supply drops as decode batch size N grows
- `TestDecodeSupply_BoundedCeiling` — min(N_max/ITL, max_observed(N/ITL))
- `TestDecodeSupply_EmpiricalConverges` — empirical peak converges as system sees higher N
- `TestTimingBaseline_TracksMinimum` — ITL_baseline and prefill_tpt_baseline track minimum observed values
- `TestSupply_NoTimingData` — throughput analyzer produces no signal when ITL/prefill_time unavailable

**Channel selection by P/D role:**
- `TestChannelSelection_RoleBoth` — uses max(prefill_util, decode_util) as bottleneck
- `TestChannelSelection_RolePrefill` — uses prefill channel only
- `TestChannelSelection_RoleDecode` — uses decode channel only
- `TestChannelSelection_RoleUnknown` — same as RoleBoth

**Scaling signals:**
- `TestAnalyze_ScaleUp_PrefillBottleneck` — prefill demand > supply → requiredCapacity > 0
- `TestAnalyze_ScaleUp_DecodeBottleneck` — decode demand > supply → requiredCapacity > 0
- `TestAnalyze_ScaleDown_BothChannelsLow` — both channels low → spareCapacity > 0
- `TestAnalyze_Steady_NoAction` — both channels within boundaries → no scaling signal
- `TestAnalyze_WarmupGuard` — signals suppressed during first N cycles

**Multi-variant:**
- `TestAnalyze_HeterogeneousGPUs` — different ITL / prefill_time per variant type
- `TestAnalyze_PendingReplicas` — pending replicas counted in anticipated supply

### 11.2 Integration Tests

**Multi-analyzer combination:**
- `TestMultiAnalyzer_OrScaleUp_SaturationOnly` — saturation triggers, throughput does not → scale up
- `TestMultiAnalyzer_OrScaleUp_ThroughputOnly` — throughput triggers, saturation does not → scale up
- `TestMultiAnalyzer_OrScaleUp_BothTrigger` — both trigger → use larger signal
- `TestMultiAnalyzer_AndScaleDown_BothAgree` — both agree on spare capacity → scale down
- `TestMultiAnalyzer_AndScaleDown_SaturationDisagrees` — saturation says no → no scale down
- `TestMultiAnalyzer_AndScaleDown_ThroughputDisagrees` — throughput says no → no scale down
- `TestMultiAnalyzer_ThroughputFailure_Fallback` — throughput error → saturation-only (graceful degradation)

**P/D disaggregation:**
- `TestThroughput_PrefillOnly_ScaleUp` — prefill replicas scale on input token demand
- `TestThroughput_DecodeOnly_ScaleUp` — decode replicas scale on output token demand
- `TestThroughput_NonDisaggregated_BottleneckChannel` — RoleBoth uses max(prefill_util, decode_util)
- `TestThroughput_PD_IndependentScaling` — prefill and decode groups scale independently

---

## 12. Risks and Mitigations

### 12.1 False Positives from Transient Spikes

**Risk**: A brief traffic spike (5-10 seconds) could cause the throughput analyzer to trigger scale-up unnecessarily, adding replicas that aren't needed.

**Mitigation**:
- EMA smoothing (α=0.3) naturally dampens spikes shorter than ~30 seconds
- Warmup guard suppresses signals for the first 4 cycles after startup
- The `throughputWeight` (0.8) means throughput needs a larger signal than saturation to dominate
- The reconciliation interval (15s) itself acts as a filter — sub-15s transients are invisible

### 12.2 Load-Dependent Timing and Supply Accuracy

**Risk**: ITL and prefill_time_per_token degrade with load (see §5.6). At low utilization, timing is faster than under heavy load, potentially leading to inaccurate supply estimation.

**Mitigation** (asymmetric strategy per channel):
- **Prefill supply** uses **current capacity** `(B-N)/prefill_tpt` — inherently load-aware because both budget and timing reflect the current operating point. No peak tracking (peak at low N would overestimate capacity at high N).
- **Decode supply** uses **bounded ceiling**: `min(N_max/ITL, max_observed(N/ITL))`. The theoretical bound overestimates at low N but the empirical bound is conservative, and `min` gives the tighter bound.
- **Timing baselines** (min observed ITL and prefill_tpt) track degradation ratios as a leading indicator of approaching capacity.
- Cross-reference with saturation analyzer's k2 for consistency checking
- Cross-validate timing-based throughput against completion-rate counters (divergence > 2x triggers warning)
- P/D disaggregated replicas are unaffected: N is stable (≈0 for prefill-only, ≈N_max for decode-only), so timing is approximately constant at the operating point.
- Conservative approach: if no timing data, the throughput analyzer returns zero signals (falls back to saturation-only)

### 12.3 Oscillation Between Analyzers

**Risk**: The two analyzers could fight — throughput scales up, which reduces demand rate, which causes throughput to suggest scale-down, but saturation disagrees (AND logic blocks), creating an unstable equilibrium.

**Mitigation**:
- AND logic for scale-down prevents premature removal
- EMA smoothing provides hysteresis (rate must sustain below boundary, not just dip momentarily)
- The saturation analyzer's spare capacity check is based on current state, providing a stable anchor

### 12.4 Metric Staleness and Clock Drift

**Risk**: Rate computation depends on Δt between cycles. If the reconciliation interval is inconsistent (jitter, backpressure), rate calculations may be inaccurate.

**Mitigation**:
- Use actual elapsed time between analyzer calls (not assumed 15s interval) for queue growth rate
- Prometheus `rate()` function handles irregular scrape intervals natively
- EMA smoothing reduces sensitivity to individual noisy measurements

### 12.5 Interaction with Scale-to-Zero

**Risk**: When replicas scale to zero, there is no throughput data. The throughput analyzer cannot detect demand arrival via completion rates (there are none). Only the scheduler queue signals demand.

**Mitigation**:
- Scale-from-zero is handled by the saturation analyzer (via CapacityKnowledgeStore)
- The throughput analyzer should explicitly yield to saturation for zero-replica variants
- Once replicas are running and processing requests, the throughput analyzer resumes

---

## Appendix A: Comparison with Kubernetes HPA Rate-Based Scaling

Kubernetes HPA supports custom metrics and can scale on request rate (`requests_per_second`). However:

1. HPA operates on a single metric at a time — it cannot combine rate AND saturation signals with OR/AND logic
2. HPA scales on raw metric value, not on utilization relative to observed capacity
3. HPA has no concept of "throughput at saturation" — it requires a manually configured target value
4. HPA cannot differentiate between GPU types (different throughput per accelerator)

The throughput analyzer addresses all four limitations by operating within the WVA framework.

## Appendix B: Key Formulas Summary

### Per-Replica Throughput (Dual-Channel)

**Prefill channel** (input tokens/sec per replica):
```
prefill_time_per_token = AvgPrefillTime / AvgInputTokens       (seconds per input token)
prefill_budget_tokens  = B - N                                  (tokens; N reqs × 1 tok = N tokens)
prefill_supply         = prefill_budget_tokens / prefill_time_per_token   (input tokens/sec)

Where:
  B = max_num_batched_tokens (tokens, from deployment args)
  S = max_num_seqs (requests, concurrency cap)
  N = num_requests_running (requests, N ≤ S; each uses 1 token of budget per step)
  AvgPrefillTime = rate(request_prefill_time_seconds_sum) / rate(..._count)
```

**Decode channel** (output tokens/sec per replica):
```
decode_supply = N / ITL                                          (output tokens/sec)

Where:
  N   = num_requests_running (produces N output tokens per step, N ≤ S)
  ITL = rate(time_per_output_token_seconds_sum) / rate(..._count)  (seconds/token)
```

### Demand Rate (per channel)

```
prefill_demand = Σ(prefill_throughput_per_replica) + queue_growth × input_fraction
decode_demand  = Σ(decode_throughput_per_replica)  + queue_growth × output_fraction

queue_growth    = max(0, Δ(queue_tokens) / Δt)
input_fraction  = avg_input_tokens / (avg_input_tokens + avg_output_tokens)
output_fraction = 1 - input_fraction
```

### Supply Rate (per channel — asymmetric strategies, see §5.6)

```
Prefill supply (current capacity, no peak tracking):
  prefill_supply = Σ (B - N_i) / prefill_tpt_i            (summed across ready replicas)

Decode supply (bounded ceiling):
  decode_capacity_per_replica = min(N_max / ITL, max_observed(N/ITL))
  decode_supply = ready_replicas × decode_capacity_per_replica
```

### P/D Disaggregation Simplifications

```
Prefill-only replicas (N ≈ 0):
  prefill_supply = B / prefill_time_per_token       (full B tokens to prefill)
  decode channel: inactive

Decode-only replicas (N ≈ N_max):
  N_max = min(S, ⌊k1 / avg_kv_tokens_per_request⌋) (max concurrent requests)
  decode_supply = N_max / ITL                        (N_max output tokens per step)
  prefill channel: inactive

Non-disaggregated replicas (RoleBoth):
  effective_utilization = max(prefill_util, decode_util)
```

### Combined Utilization

```
prefill_utilization = EMA(prefill_demand) / EMA(prefill_supply)
decode_utilization  = EMA(decode_demand)  / EMA(decode_supply)
effective_utilization = max(prefill_utilization, decode_utilization)
```

### Scaling Signals

```
required_capacity = total_demand / threshold - anticipated_supply
spare_capacity    = total_supply - total_demand / boundary

(computed on the effective/bottleneck channel)
```

### Multi-Analyzer Combination

```
Scale-up:   ANY(required_capacity_i > 0)
            target = max(w_i × replicas_needed_i)

Scale-down: ALL(spare_capacity_i > 0)
            target = min(replicas_removable_i / w_i)
```

### EMA Smoothing

```
EMA_t = α × value_t + (1 - α) × EMA_{t-1}
Default α = 0.3, warmup = 4 cycles

Applied per-variant per-channel (prefill and decode independently).
```
