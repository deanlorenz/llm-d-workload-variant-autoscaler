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

> **Status:** This document covers the metrics collection layer (PR-1, PR-2) and the internal
> state management package (PR-3). The ITL model fit, μ_dec supply estimation, and scaling
> signal are added in PR-4.

## Table of Contents

- [Overview](#overview)
- [Metrics](#metrics)
  - [Throughput Analyzer Queries](#throughput-analyzer-queries)
  - [Shared Fields from Collector](#shared-fields-from-collector)
  - [Query Design Decisions](#query-design-decisions)
- [Architecture](#architecture)
  - [Components](#components)
  - [Data Flow](#data-flow)
- [References](#references)

## Metrics

`RegisterThroughputAnalyzerQueries` (in `internal/collector/registration/throughput_analyzer.go`)
registers three queries that are genuinely new and not covered by other analyzer registrations.
All other TA inputs are read from `interfaces.ReplicaMetrics` fields populated by the saturation
and queueing model registrations.

### Throughput Analyzer Queries

#### QueryGenerationTokenRate (`generation_token_rate`)

```promql
sum by (pod) (rate(vllm:request_generation_tokens_sum{namespace="...",model_name="..."}[1m]))
```

**What it measures:** Observed generation (decode) token rate per pod in tokens/sec.

**TA notation:** μ_dec^obs — the directly observable supply proxy. Used both to calibrate the
ITL model and as a sanity check against the demand estimate (μ_dec^obs ≈ λ_dec at steady state
with no queueing).

**ReplicaMetrics field:** `GenerationTokenRate`

**Why `sum` not `max`:** `vllm:request_generation_tokens_sum` is a histogram `_sum` counter
(additive across histogram buckets per pod). Rate of the sum gives the true tokens/sec.

**Why 1m window:** Balances responsiveness to load changes with smoothing of request bursts.

---

#### QueryKvTokensUsed (`kv_tokens_used`)

```promql
max by (pod) (vllm:kv_cache_usage_perc{namespace="...",model_name="..."})
```

**What it measures:** Instantaneous KV cache utilization fraction per pod (0.0–1.0).

**TA notation:** k* — the current operating point in the ITL model `ITL(k) = A·k + B`.

**ReplicaMetrics field:** `KvUtilization`

**Why not `max_over_time`:** The Saturation Analyzer uses `max_over_time[1m]` to catch
worst-case peaks for conservative capacity guardrails (stored in `KvCacheUsage`). The
Throughput Analyzer needs the **current operating point** to evaluate `ITL(k*)` accurately —
using the peak would overestimate load and cause premature scale-up. These two fields coexist
on `ReplicaMetrics` for their respective purposes.

---

#### QueryVLLMRequestRate (`vllm_request_rate`)

```promql
sum by (pod) (rate(vllm:request_generation_tokens_count{namespace="...",model_name="..."}[1m]))
```

**What it measures:** vLLM-side request completion rate per pod (req/s), derived from the
generation tokens histogram `_count` counter (increments once per completed request).

**TA notation:** fallback λ_req — used when `ArrivalRate == 0` for all pods (EPP not deployed).
The analyzer computes `λ_dec_fallback = sum(VLLMRequestRate) × avg(AvgOutputTokens)`.

**ReplicaMetrics field:** `VLLMRequestRate`

**Important:** This measures *completed* (served) requests, not *arriving* requests. It
undercounts when requests are queued in the scheduler. Use `ArrivalRate` (primary) first;
fall back to this only when the EPP is not deployed.

---

### Shared Fields from Collector

The following TA inputs are already collected via other analyzer registrations and exposed
as `interfaces.ReplicaMetrics` fields. The TA reads these fields directly rather than
registering duplicate queries.

| TA notation | `ReplicaMetrics` field | Query | Registration |
|---|---|---|---|
| KV_max (token capacity) | `TotalKvCapacityTokens` | `QueryCacheConfigInfo` | `RegisterSaturationQueries` |
| ITL_obs (observed ITL) | `AvgITL` | `QueryAvgITL` | `RegisterQueueingModelQueries` |
| OL (avg output tokens) | `AvgOutputTokens` | `QueryAvgOutputTokens` | `RegisterSaturationQueries` |
| IL (avg input tokens) | `AvgInputTokens` | `QueryAvgInputTokens` | `RegisterSaturationQueries` |
| H% (prefix hit rate) | `PrefixCacheHitRate` | `QueryPrefixCacheHitRate` | `RegisterSaturationQueries` |
| λ_req (per-pod, req/s) | `ArrivalRate` | `QuerySchedulerDispatchRate` | `RegisterQueueingModelQueries` |

**λ_dec primary:** `sum(ArrivalRate_r × AvgOutputTokens_r)` across all replicas (EPP deployed).  
**λ_dec fallback:** `sum(VLLMRequestRate_r) × avg(AvgOutputTokens_r)` (EPP absent, all ArrivalRate == 0).

**Note on arrival rate:** `ArrivalRate` comes from `QuerySchedulerDispatchRate` which is per-pod,
namespaced, and model-scoped — correctly isolating traffic to a specific variant. The TA sums
per-replica λ_dec in the analyzer rather than using a model-level query, which avoids the
namespace filtering limitation of the scheduler metric (TODO #2309).

---

### Query Design Decisions

| Query / Field | Source | Aggregation | Window | Purpose in TA |
|---|---|---|---|---|
| `QueryGenerationTokenRate` | vLLM | `sum by (pod)` | 1m rate | μ_dec^obs per pod |
| `QueryKvTokensUsed` | vLLM | `max by (pod)` | instant | k* (no max_over_time) |
| `QueryVLLMRequestRate` | vLLM | `sum by (pod)` | 1m rate | Fallback λ_req per pod |
| `TotalKvCapacityTokens` | `KvCacheConfigInfo` labels | derived | static | KV_max = blocks × block_size |
| `AvgITL` | `QueryAvgITL` | `max by (pod)` | 1m rate | ITL_obs for OLS calibration |
| `AvgOutputTokens` | `QueryAvgOutputTokens` | `max by (pod)` | 5m rate | OL for KV_req and λ_dec |
| `AvgInputTokens` | `QueryAvgInputTokens` | `max by (pod)` | 5m rate | IL for IL_eff = IL × (1−H%) |
| `PrefixCacheHitRate` | `QueryPrefixCacheHitRate` | `max by (pod)` | 5m rate | H% for IL_eff |
| `ArrivalRate` | `QuerySchedulerDispatchRate` | `sum by (pod_name)` | 1m rate | λ_req per pod (primary) |

## Architecture

### Components

**Query Registration (`internal/collector/registration/throughput_analyzer.go`)**  
Registers three PromQL templates exclusive to the throughput analyzer:
`QueryGenerationTokenRate`, `QueryKvTokensUsed`, `QueryVLLMRequestRate`.
`RegisterThroughputAnalyzerQueries` must be called once at startup alongside
`RegisterSaturationQueries` and `RegisterQueueingModelQueries`.

**Metrics Collector (`internal/collector/replica_metrics.go`)**  
Populates all `interfaces.ReplicaMetrics` fields in a single `Refresh()` call covering all
12 registered queries. The three TA-exclusive fields are:
`GenerationTokenRate`, `KvUtilization`, `VLLMRequestRate`.
The remaining TA fields (`TotalKvCapacityTokens`, `AvgITL`, `AvgOutputTokens`, `AvgInputTokens`,
`PrefixCacheHitRate`, `ArrivalRate`) are populated by saturation and queueing model queries.

**Throughput Analyzer (`internal/engines/analyzers/throughput/`)**  
*(PR-3 complete; ITL model and scaling signal in PR-4)*

The PR-3 state management layer tracks per-variant calibration state across reconcile cycles:

- **`ShapeTracker`** — maintains the current workload shape bucket `(IL, OL, IL_eff, KV_req)`.
  Detects shape changes (>20% shift in IL or OL) and triggers observation window reset.
  `IL_eff = IL × (1 − PrefixCacheHitRate)`; `KV_req = IL_eff + OL/2`.

- **`ObservationWindow`** — rolling window of `(k*, ITL_obs)` pairs collected per replica per
  cycle. Filters observations to `k ∈ [0.15, 0.85]` (reliable linear-model range). Reports
  `Ready()` when ≥ 10 samples with ≥ 0.30 k-spread are accumulated.

- **`ThroughputAnalyzer`** — implements `interfaces.Analyzer`. Groups replicas by
  `VariantName`, runs sanity checks, updates the shape tracker and observation window per
  variant. Returns `RequiredCapacity=0 / SpareCapacity=0` until PR-4 adds the OLS fit.

The following remain pending for PR-4:
- OLS regression to fit ITL model parameters A and B: `ITL(k) = A·k + B`
- μ_dec supply estimation and λ_dec vs μ_dec scaling signal
- `ITLKnowledgeStore` for persisting fitted (A, B) across zero-replica periods

### Data Flow

```
┌─────────────┐
│  Prometheus │
└──────┬──────┘
       │ vllm:request_generation_tokens_sum      (QueryGenerationTokenRate   → GenerationTokenRate)
       │ vllm:kv_cache_usage_perc                (QueryKvTokensUsed          → KvUtilization)
       │ vllm:request_generation_tokens_count    (QueryVLLMRequestRate       → VLLMRequestRate)
       │ vllm:cache_config_info                  (QueryCacheConfigInfo       → TotalKvCapacityTokens)
       │ vllm:time_per_output_token_seconds_*    (QueryAvgITL               → AvgITL)
       │ vllm:request_generation_tokens_*        (QueryAvgOutputTokens       → AvgOutputTokens)
       │ vllm:request_prompt_tokens_*            (QueryAvgInputTokens        → AvgInputTokens)
       │ vllm:prefix_cache_hits/queries          (QueryPrefixCacheHitRate    → PrefixCacheHitRate)
       │ inference_extension_scheduler_*         (QuerySchedulerDispatchRate → ArrivalRate)
       ↓
┌────────────────────────────────┐
│ ReplicaMetricsCollector        │  ← internal/collector/replica_metrics.go
│ CollectReplicaMetrics()        │     single Refresh() call, 12 queries
└──────┬─────────────────────────┘
       │ []interfaces.ReplicaMetrics
       ↓
┌────────────────────┐
│ ThroughputAnalyzer │  ← internal/engines/analyzers/throughput/ (PR-3 ✓; OLS/signal: PR-4)
│  ITL(k) = A·k+B    │
│  μ_dec = N/ITL     │
│  λ_dec = R × OL    │
└────────┬───────────┘
         │ scale signal: λ_dec vs μ_dec
         ↓
┌──────────────────┐
│    Controller    │
└──────────────────┘
```

## References

- Related: [Saturation Analyzer](saturation-analyzer.md)
- Design: `ideas/TA-Plan.md`, `ideas/TA-supply.md`, `ideas/TA-demand.md`
