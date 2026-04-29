# PR-2: Register Decode Demand Metric (λ_dec Demand Signal)

> **Status: COMPLETED** — Implemented in #1051 (combined with PR-1).
> Part of #1005; does not close it.

## Context

PR-2 registers the one remaining Prometheus query needed for the demand side of the
throughput analyzer — a fallback λ_dec estimate when EPP/scheduler metrics are absent —
and writes the `RegisterThroughputAnalyzerQueries` function that packages all three
TA-exclusive queries together.

The primary λ_dec source (`ArrivalRate` via `QuerySchedulerDispatchRate`) was already
registered by `RegisterQueueingModelQueries`. PR-2 adds only the vLLM-side fallback.

**Scope: query registration and collector wiring only. No analyzer logic.**

---

## Key Design Decisions

### Six of nine planned TA queries already existed

The original design called for nine queries. During implementation, six were found to
already be registered and exposed on `interfaces.ReplicaMetrics` (see table below).
Only three new queries were needed — two supply signals (PR-1) and one demand fallback
(PR-2). All three are registered together in `RegisterThroughputAnalyzerQueries`.

### Primary λ_dec uses existing ArrivalRate — no new scheduler query needed

Options A/B/C from the original plan proposed registering a new scheduler-side PromQL.
The existing `QuerySchedulerDispatchRate` already provides the per-pod arrival rate in
`ArrivalRate float64`. The analyzer computes `λ_dec = ArrivalRate × AvgOutputTokens`
directly — no additional registration needed for the EPP path.

### Option D (vLLM fallback) — measures served demand, not arriving demand

`QueryVLLMRequestRate` uses the histogram `_count` counter (one increment per
completed request) to measure completion rate. This is **served demand** — it
undercounts when requests are queued in the scheduler. The analyzer uses it only when
`ArrivalRate == 0` for all pods (`isEPP = false`). When both are present, the gap
between `ArrivalRate` and `VLLMRequestRate` signals queuing depth.

---

## Components

### `internal/collector/registration/throughput_analyzer.go`

- **`QueryVLLMRequestRate`** (`vllm_request_rate`) — `rate` of the histogram `_count`
  counter for `vllm:request_generation_tokens_count`, summed by pod over `[1m]`.
  Gives the request completion rate per pod (req/s) as a fallback for λ_dec.

- **`RegisterThroughputAnalyzerQueries(sourceRegistry)`** — registers all three
  TA-exclusive queries in one call. Skips quietly if the Prometheus source is absent.
  The function doc comment includes the full TA notation → `ReplicaMetrics` field
  mapping as a reference for the analyzer implementation.

### `internal/collector/registration/throughput_analyzer_test.go`

6 specs: panic-on-double-registration (MustRegister panics when called twice on the
same registry), three query presence checks (one per query), one template-rendering
check per query (namespace/modelID substitution), and a no-prometheus-source guard
(no panic).

### `internal/interfaces/saturation_analyzer.go`

`VLLMRequestRate float64` added to `ReplicaMetrics` — per-pod request completion rate.

### `internal/collector/replica_metrics.go`

`Refresh()` wired to populate `VLLMRequestRate` from `QueryVLLMRequestRate` results.

---

## Already Registered (not re-registered by PR-2)

| TA need | Existing field | Source |
|---|---|---|
| KV_max | `TotalKvCapacityTokens` | `RegisterSaturationQueries` |
| ITL_obs | `AvgITL` | `RegisterQueueingModelQueries` |
| OL | `AvgOutputTokens` | `RegisterSaturationQueries` |
| IL | `AvgInputTokens` | `RegisterSaturationQueries` |
| H% | `PrefixCacheHitRate` | `RegisterSaturationQueries` |
| λ_req (primary) | `ArrivalRate` | `RegisterQueueingModelQueries` |

---

## Not in this PR

- Supply queries (`QueryGenerationTokenRate`, `QueryKvUsageInstant`) — PR-1
- Analyzer package — PR-3
- ITL model and scaling signal — PR-4
- Wiring into engine pipeline — PR-5
