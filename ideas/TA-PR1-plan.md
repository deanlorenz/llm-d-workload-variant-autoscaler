# PR-1: Register Core Rate Metrics (μ_dec Supply Signals)

> **Status: COMPLETED** — Implemented in #1051 (combined with PR-2).
> Part of #1005; does not close it.

## Context

PR-1 registers the Prometheus queries needed to observe the **supply side** of the
throughput analyzer: how fast each replica is currently generating decode tokens, and
at what KV utilization it is operating. These two signals feed the ITL model calibration
in PR-4 — `ObservationWindow` collects `(k*, ITL_obs)` pairs from them.

**Scope: query registration and collector wiring only. No analyzer logic.**

---

## Key Design Decisions

### TotalKvCapacityTokens is already collected — no new KV-capacity query needed

The original plan included a `QueryKvTokensTotal` to measure `KV_max`. During
implementation it was discovered that `RegisterSaturationQueries` already registers
`QueryCacheConfigInfo`, which parses `vllm:cache_config_info` labels to derive
`TotalKvCapacityTokens`. PR-1 reads this field directly.

### Two distinct KV utilization queries serve different purposes

The saturation analyzer registers `QueryKvCacheUsage` with `max_over_time[1m]` to
catch worst-case peaks for conservative guardrails (stored in `KvCacheUsage`). The
throughput analyzer evaluates `ITL(k*)` at the **current operating point** — using
a peak would systematically overestimate load. A separate `QueryKvTokensUsed` with
an instantaneous `max by (pod)` is required and stored in a distinct `KvUtilization`
field. Both fields coexist on `ReplicaMetrics` for their respective purposes.

---

## Components

### `internal/collector/registration/throughput_analyzer.go`

Two new query constants registered via `MustRegister`:

- **`QueryGenerationTokenRate`** (`generation_token_rate`) — `rate` of the histogram
  `_sum` counter for `vllm:request_generation_tokens_sum`, summed by pod over `[1m]`.
  This is the directly observed decode token rate per pod (tokens/sec), μ_dec^obs.
  `sum by (pod)` collapses histogram buckets; `rate(_sum)` gives true tokens/sec.

- **`QueryKvTokensUsed`** (`kv_tokens_used`) — `max by (pod)` of
  `vllm:kv_cache_usage_perc`. Instantaneous KV cache utilization fraction (0.0–1.0),
  used as k* in `ITL(k) = A·k + B`. Does not use `max_over_time`; the throughput
  analyzer needs the current operating point, not the worst-case peak.

### `internal/interfaces/saturation_analyzer.go`

Two new fields added to `ReplicaMetrics`:
- `GenerationTokenRate float64` — μ_dec^obs per pod (tok/s)
- `KvUtilization float64` — k* per pod (0.0–1.0), distinct from `KvCacheUsage`

### `internal/collector/replica_metrics.go`

`Refresh()` wired to populate `GenerationTokenRate` and `KvUtilization` from the
two new query results.

---

## Not Already Registered (these existed before PR-1)

| TA need | Existing field | Source |
|---|---|---|
| KV_max | `TotalKvCapacityTokens` | `RegisterSaturationQueries` (QueryCacheConfigInfo) |
| ITL_obs | `AvgITL` | `RegisterQueueingModelQueries` |
| OL | `AvgOutputTokens` | `RegisterSaturationQueries` |
| IL | `AvgInputTokens` | `RegisterSaturationQueries` |
| H% | `PrefixCacheHitRate` | `RegisterSaturationQueries` |

---

## Not in this PR

- λ_dec demand query (`QueryVLLMRequestRate`) and `RegisterThroughputAnalyzerQueries` function — PR-2
- Analyzer package — PR-3
- ITL model and scaling signal — PR-4
- Wiring into engine pipeline — PR-5
