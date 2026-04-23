# Throughput Analyzer

## Overview

The Throughput Analyzer is a **model-driven, proactive scaling analyzer** that estimates decode
token throughput supply (μ_dec) and compares it against decode token demand (λ_dec) to drive
scaling decisions.

Where the Saturation Analyzer reacts to observed capacity exhaustion, the Throughput Analyzer
predicts how much decode throughput the current replica fleet can sustain at a given KV cache
operating point, and scales before demand exceeds that supply.

**Key concepts:**
- **μ_dec** — decode token supply: how many tokens/sec the fleet can generate, estimated from
  KV cache occupancy and a calibrated inter-token latency (ITL) model
- **λ_dec** — decode token demand: how many tokens/sec the scheduler is dispatching to this model

> **Status:** This document covers the metrics collection layer (PR-1, PR-2). The ITL model,
> supply/demand calculation, and scaling signal are added in subsequent PRs.

## Table of Contents

- [Overview](#overview)
- [Metrics](#metrics)
  - [Supply Metrics (μ_dec)](#supply-metrics-μ_dec)
  - [Workload Shape Metrics](#workload-shape-metrics)
  - [Demand Metrics (λ_dec)](#demand-metrics-λ_dec)
  - [Query Design Decisions](#query-design-decisions)
- [Architecture](#architecture)
  - [Components](#components)
  - [Data Flow](#data-flow)
- [References](#references)

## Metrics

All queries are registered in `internal/collector/registration/throughput_analyzer.go` via
`RegisterThroughputAnalyzerQueries`.

### Supply Metrics (μ_dec)

Four queries provide the inputs for the μ_dec supply estimate and ITL model calibration.

#### QueryGenerationTokenRate (`generation_token_rate`)

```promql
sum by (pod) (rate(vllm:request_generation_tokens_sum{namespace="...",model_name="..."}[1m]))
```

**What it measures:** Observed generation (decode) token rate per pod in tokens/sec.

This is the direct observable proxy for μ_dec^obs — how many tokens each replica is
actually generating per second right now. Used both to calibrate the ITL model and
as a sanity check against the scheduler-side demand estimate.

**Why `sum` not `max`:** `vllm:request_generation_tokens_sum` is a histogram `_sum` counter
(additive across histogram buckets per pod). Rate of the sum gives the true tokens/sec.

**Why 1m window:** Balances responsiveness to load changes with smoothing of request bursts.

#### QueryKvTokensUsed (`kv_tokens_used`)

```promql
max by (pod) (vllm:kv_cache_usage_perc{namespace="...",model_name="..."})
```

**What it measures:** Instantaneous KV cache utilization fraction per pod (0.0–1.0).

This is **k\*** — the current operating point in the ITL model `ITL(k) = A·k + B`. The
actual token count in use is computed in the analyzer as:

```
kvTokensUsed = k* × (num_gpu_blocks × block_size)
```

where `num_gpu_blocks` and `block_size` come from `QueryKvTokensTotal`.

**Why not `max_over_time`:** The Saturation Analyzer uses `max_over_time[1m]` to catch
worst-case peaks for conservative capacity guardrails. The Throughput Analyzer needs
the **current operating point** to evaluate `ITL(k*)` accurately — using the peak would
overestimate load and cause premature scale-up.

#### QueryKvTokensTotal (`kv_tokens_total`)

```promql
max by (pod, num_gpu_blocks, block_size) (vllm:cache_config_info{namespace="...",model_name="..."})
```

**What it measures:** KV cache block configuration per pod. The metric value is static (1);
the useful data is in the labels `num_gpu_blocks` and `block_size`.

Total KV token capacity is computed in the analyzer as:

```
KV_max = num_gpu_blocks × block_size
```

**Why a separate query from the saturation analyzer's `QueryCacheConfigInfo`:** Both
queries use identical PromQL but are registered under different names so each analyzer
can independently request refresh and evolve its query without coupling.

#### QueryTAAvgITL (`ta_avg_itl`)

```promql
max by (pod) (rate(vllm:time_per_output_token_seconds_sum{namespace="...",model_name="..."}[1m])
              / rate(vllm:time_per_output_token_seconds_count{namespace="...",model_name="..."}[1m]))
```

**What it measures:** Observed average inter-token latency per pod in seconds/token, using a
1-minute rate window.

This is the primary observable for calibrating the ITL model parameters A and B:

```
ITL(k) = A·k + B
```

The analyzer maintains a rolling window of `(k*, ITL_obs)` pairs — where `k*` comes from
`QueryKvTokensUsed` and `ITL_obs` from this query — and fits A and B via OLS regression.
A minimum spread in k* values (≥ 0.30) is required before calibration is trusted.

**Why 1m window:** The same rate window as `QueryKvTokensUsed` ensures the ITL observation
and the KV utilization reading are temporally aligned for each calibration point.

**Why separate from `QueryAvgITL` (queueing model):** Uses identical PromQL but registered
independently under `ta_avg_itl` so the throughput analyzer engine does not depend on
`RegisterQueueingModelQueries` having been called.

---

### Workload Shape Metrics

Three queries characterize the workload to compute per-request KV token demand and effective
input length.

#### QueryTAAvgOutputTokens (`ta_avg_output_tokens`)

```promql
max by (pod) (rate(vllm:request_generation_tokens_sum{namespace="...",model_name="..."}[5m])
              / rate(vllm:request_generation_tokens_count{namespace="...",model_name="..."}[5m]))
```

**What it measures:** Average output (generation) tokens per completed request per pod
(tok/req), using a 5-minute rate window.

Used in two calculations:

```
KV_req = IL_eff + OL/2                     (token slots per in-flight request)
λ_dec  = QueryDecodeTokenDemand × OL       (decode token demand, tok/s)
```

**Why 5m window:** Output token length is relatively stable over time; a longer window
smooths per-request variance without introducing significant lag.

**Why separate from `QueryAvgOutputTokens` (saturation):** Uses identical PromQL but
registered independently for throughput analyzer isolation.

#### QueryTAAvgInputTokens (`ta_avg_input_tokens`)

```promql
max by (pod) (rate(vllm:request_prompt_tokens_sum{namespace="...",model_name="..."}[5m])
              / rate(vllm:request_prompt_tokens_count{namespace="...",model_name="..."}[5m]))
```

**What it measures:** Average input (prompt) tokens per completed request per pod (tok/req),
using a 5-minute rate window.

Used to compute the effective input length:

```
IL_eff = IL × (1 - prefix_hit_rate)
```

**Why separate from `QueryAvgInputTokens` (saturation):** Uses identical PromQL but
registered independently for throughput analyzer isolation.

#### QueryTAPrefixCacheHitRate (`ta_prefix_cache_hit_rate`)

```promql
max by (pod) (rate(vllm:prefix_cache_hits{namespace="...",model_name="..."}[5m])
              / rate(vllm:prefix_cache_queries{namespace="...",model_name="..."}[5m]))
```

**What it measures:** Prefix cache hit rate per pod (0.0–1.0), using a 5-minute rate window.

Used alongside `QueryTAAvgInputTokens` to reduce the effective prompt token count:

```
IL_eff = IL × (1 - prefix_hit_rate)
KV_req = IL_eff + OL/2
```

A hit rate of 0.3 means 30% of prompt tokens reuse existing KV blocks, reducing per-request
KV slot demand accordingly. Returns NaN when prefix caching is disabled; the analyzer treats
NaN as 0.0 (no cache benefit).

---

### Demand Metrics (λ_dec)

#### QueryDecodeTokenDemand (`decode_token_demand`)

```promql
sum(rate(inference_extension_scheduler_attempts_total{status="success",target_model_name="..."}[1m]))
or
sum(rate(inference_extension_scheduler_attempts_total{status="success",model_name="...",target_model_name=""}[1m]))
```

**What it measures:** Total request dispatch rate (req/s) across all replicas for this model,
as seen by the llm-d inference scheduler.

The full decode token demand in tok/s is computed in the analyzer as:

```
λ_dec = QueryDecodeTokenDemand (req/s) × avg(QueryTAAvgOutputTokens) (tok/req)
```

**Why scheduler-side, not vLLM-side:** `QueryGenerationTokenRate` measures *served* demand —
requests that are already being processed. Requests queued in the scheduler's flow control
layer have not yet reached any vLLM pod and are invisible to vLLM metrics.
`QueryDecodeTokenDemand` captures the full arrival rate including queued requests, giving
an earlier signal of impending overload.

**Sanity check:** At steady state with no queueing, `QueryDecodeTokenDemand × avg_OL`
should approximately equal `sum(QueryGenerationTokenRate)` across all pods. A gap > 10%
indicates active queueing:

| Condition | Meaning |
|-----------|---------|
| `λ_sched ≈ λ_vllm` | Low queue; served demand ≈ arriving demand |
| `λ_sched > 1.10 × λ_vllm` | >10% requests queued; scale more aggressively |
| `λ_sched < λ_vllm` | Metric lag or label mismatch; investigate |

**`target_model_name` fallback:** Uses `target_model_name` (resolved model after LoRA routing)
with fallback to `model_name` when `target_model_name` is not set. This follows the same
pattern as `QuerySchedulerQueueSize`.

> **Known limitation (TODO #2309):** The upstream EPP does not currently emit a namespace
> label on `inference_extension_scheduler_attempts_total`. This query therefore matches by
> model name only and will aggregate across all namespaces if the same model name is used
> in multiple namespaces.

#### QueryVLLMRequestRate (`vllm_request_rate`)

```promql
sum by (pod) (rate(vllm:request_generation_tokens_count{namespace="...",model_name="..."}[1m]))
```

**What it measures:** vLLM-side request completion rate per pod (req/s), derived from the
generation tokens histogram `_count` counter (increments once per completed request).

Used as a **fallback** for λ_dec estimation when `QueryDecodeTokenDemand` returns no data
(EPP/scheduler not deployed):

```
λ_dec_vllm = QueryVLLMRequestRate (req/s) × avg(QueryTAAvgOutputTokens) (tok/req)
```

**Important:** This measures *completed* (served) requests, not *arriving* requests. It
undercounts when requests are queued in the scheduler. Use `QueryDecodeTokenDemand` as the
primary demand source; fall back to this only when the EPP is not deployed.

### Query Design Decisions

| Query | Group | Aggregation | Window | Reason |
|-------|-------|-------------|--------|--------|
| `QueryGenerationTokenRate` | supply | `sum by (pod)` | 1m rate | Additive histogram counter; per-pod supply signal |
| `QueryKvTokensUsed` | supply | `max by (pod)` | instant | Current operating point k\* for ITL model; no max_over_time |
| `QueryKvTokensTotal` | supply | `max by (pod, ...)` | instant | Static config; dedup across duplicate series |
| `QueryTAAvgITL` | ITL cal. | `max by (pod)` | 1m rate | Observed ITL_obs for (k\*, ITL) calibration pairs |
| `QueryTAAvgOutputTokens` | shape | `max by (pod)` | 5m rate | OL for KV_req and λ_dec; stable over time |
| `QueryTAAvgInputTokens` | shape | `max by (pod)` | 5m rate | IL for IL_eff = IL × (1 − hit_rate) |
| `QueryTAPrefixCacheHitRate` | shape | `max by (pod)` | 5m rate | Hit rate for IL_eff reduction |
| `QueryDecodeTokenDemand` | demand | `sum` (model) | 1m rate | Total arrival rate including queued requests |
| `QueryVLLMRequestRate` | demand | `sum by (pod)` | 1m rate | EPP fallback; served demand only |

## Architecture

### Components

**Query Registration (`internal/collector/registration/throughput_analyzer.go`)**
- Registers PromQL templates for all throughput analyzer queries
- `RegisterThroughputAnalyzerQueries` must be called once at startup alongside
  `RegisterSaturationQueries` and `RegisterQueueingModelQueries`

**Metrics Collector (`internal/collector/replica_metrics.go`)**  
*(integration pending — PR-3)*  
Will add throughput-specific queries to the `Refresh` call and populate new fields
in `interfaces.ReplicaMetrics` for the throughput analyzer to consume.

**Throughput Analyzer (`internal/engines/analyzers/throughput/`)**  
*(not yet implemented — PR-3, PR-4)*  
Will implement the ITL model calibration, μ_dec supply estimation, and λ_dec vs μ_dec
scaling signal.

### Data Flow

```
┌─────────────┐
│  Prometheus │
└──────┬──────┘
       │ vllm:request_generation_tokens_sum      (QueryGenerationTokenRate)
       │ vllm:kv_cache_usage_perc               (QueryKvTokensUsed)
       │ vllm:cache_config_info                 (QueryKvTokensTotal)
       │ vllm:time_per_output_token_seconds_*   (QueryTAAvgITL)
       │ vllm:request_generation_tokens_*       (QueryTAAvgOutputTokens, QueryVLLMRequestRate)
       │ vllm:request_prompt_tokens_*           (QueryTAAvgInputTokens)
       │ vllm:prefix_cache_hits/queries         (QueryTAPrefixCacheHitRate)
       │ inference_extension_scheduler_*        (QueryDecodeTokenDemand)
       ↓
┌───────────────────────────────┐
│ RegisterThroughputAnalyzerQueries │  ← collector/registration/throughput_analyzer.go
└───────────────────────────────┘
       │ (PR-3: collector integration)
       ↓
┌──────────────────┐
│ ThroughputAnalyzer│  ← internal/engines/analyzers/throughput/ (PR-3, PR-4)
│  ITL(k) = A·k+B  │
│  μ_dec = N/ITL   │
│  λ_dec = R × OL  │
└────────┬─────────┘
         │ scale signal: λ_dec vs μ_dec
         ↓
┌──────────────────┐
│    Controller    │
└──────────────────┘
```

## References

- Related: [Saturation Analyzer](saturation-analyzer.md)
- Design: `ideas/TA-Plan.md`, `ideas/TA-supply.md`, `ideas/TA-demand.md`
