# Analyzer K3 — Implementation Plan

## Overview

Analyzer K3 computes a per-variant **supply/demand ratio** that accounts for
workload composition, KV-cache capacity, and latency behavior.  It complements
the existing K1 (KV-saturation) and K2 (queueing-model) analyzers.

**Key idea**: normalize concurrency by end-to-end latency to obtain a
latency-weighted load index.  Scale variant $v$ so that
$D_v / S_v \approx 1$.

---

## 1. Entities

| Symbol | Meaning |
|--------|---------|
| $v \in \mathcal{V}$ | Backend variant (vLLM deployment/config) |
| $w \in \mathcal{W}$ | Workload type, characterized by $IL(w)$ and $OL(w)$ |
| $I_v$ | Current running instances of variant $v$ |
| $\Delta_v$ | Recommended replica delta (positive = scale out) |

---

## 2. Metric Sources

### 2.1 vLLM Prometheus Metrics (per-pod, already collected)

These correspond exactly to the constants in `internal/constants/metrics.go` and
the `ReplicaMetrics` struct in `internal/interfaces/saturation_analyzer.go`.

| Field in `ReplicaMetrics` | Prometheus metric | PromQL used by collector |
|---|---|---|
| `KvCacheUsage` | `vllm:kv_cache_usage_perc` | `max_over_time(...[1m])` |
| `TotalKvCapacityTokens` | `vllm:cache_config_info` | `max by (pod, num_gpu_blocks, block_size)` |
| `NumGpuBlocks` / `BlockSize` | `vllm:cache_config_info` labels | parsed from info metric labels |
| `AvgInputTokens` | `vllm:request_prompt_tokens_sum/count` | `rate(...[5m])` ratio |
| `AvgOutputTokens` | `vllm:request_generation_tokens_sum/count` | `rate(...[5m])` ratio |
| `PrefixCacheHitRate` | `vllm:prefix_cache_hits` / `vllm:prefix_cache_queries` | `rate(...[5m])` ratio |
| `ArrivalRate` | `vllm:request_success_total` (per pod) | `rate(...[5m])` |
| `AvgTTFT` | `vllm:time_to_first_token_seconds_sum/count` | `rate(...[1m])` ratio |
| `AvgITL` | `vllm:time_per_output_token_seconds_sum/count` | `rate(...[1m])` ratio |
| `QueueLength` | `vllm:num_requests_waiting` | `max_over_time(...[1m])` |

**Derived in-process (no new scrape needed)**:

```
TokensInUse          = KvCacheUsage × TotalKvCapacityTokens
KV_max(v)            = TotalKvCapacityTokens   (already in ReplicaMetrics)
H%(v)                = PrefixCacheHitRate       (already in ReplicaMetrics)
N(v)                 ≈ ArrivalRate × AvgTTFT    (Little's law proxy; or use
                        vllm:num_requests_running if exposed)
```

### 2.2 llm-d EPP / Scheduler Metrics (model-scoped)

| Constant | Prometheus metric | Description |
|---|---|---|
| `SchedulerFlowControlQueueSize` | `inference_extension_flow_control_queue_size` | Requests queued in EPP flow-control layer. Labels: `fairness_id`, `priority`, `inference_pool`, `model_name`, `target_model_name` |
| `SchedulerFlowControlQueueBytes` | `inference_extension_flow_control_queue_bytes` | Total bytes of bodies queued in EPP |

EPP metrics are **model-scoped**, not per-pod.  They are consumed today by the
scale-from-zero engine (`internal/engines/scalefromzero`) via the `eppSource`
registry entry.

### 2.3 Workload-Type Buckets (derived, not scraped)

Workload types $w$ are **not directly observable** from vLLM metrics.  They must
be **inferred** from per-pod aggregate statistics using the approach below.

---

## 3. Workload Bucketing Strategy

### 3.1 Bin definition

Define $W$ bins over $(IL, OL)$ space.  Recommended starting point:

```
IL bins (log-scale):  [0,128), [128,512), [512,2048), [2048,∞)
OL bins (quantile):   [0,64),  [64,256),  [256,1024), [1024,∞)
```

Each bin gives a workload type $w$ with representative values $IL(w)$, $OL(w)$
(e.g., bin midpoint).

### 3.2 Mixture weights

Per control window, from **per-pod** vLLM metrics (already in `ReplicaMetrics`):

```
avgIL(v)  ≈ AvgInputTokens       (weighted mean over in-flight requests)
avgOL(v)  ≈ AvgOutputTokens
```

Assign each pod's traffic to the nearest $(IL, OL)$ bin to compute system-wide
mixture weights:

```
π_w ≈ N(w) / Σ_{w'} N(w')
```

Because routing is $v$-oblivious (llm-d scheduler does not know variants when
routing), the workload mix is approximately uniform across variants:

```
N(w, v) ≈ N(v) · π_w
```

### 3.3 Estimating N(v)

Use Little's Law applied to the per-pod `ArrivalRate` and `AvgTTFT` fields
already collected:

```
N(v) ≈ ArrivalRate(v) × (AvgTTFT(v) + AvgOutputTokens(v) × AvgITL(v))
     = ArrivalRate(v) × E2E(v)
```

This is consistent with the existing queueing-model analyzer's
`avgArrivalRate` usage in
`internal/engines/analyzers/queueingmodel/analyzer.go`.

---

## 4. KV-Cache Load Model

Using existing `ReplicaMetrics` fields directly:

```
KV(w, v) = H%(v) · (IL(w) + 0.5 · OL(w))
         = PrefixCacheHitRate · (IL(w) + 0.5 · OL(w))

KV_max(v) = TotalKvCapacityTokens     [tokens]

N_max(w, v) = KV_max(v) / KV(w, v)
```

Edge cases:
- If `PrefixCacheHitRate == 0` (no prefix cache), use `H%(v) = 1.0` (full KV
  consumption, conservative estimate).
- If `TotalKvCapacityTokens == 0` (cache config info unavailable), fall back to
  `KV_max(v) = BlockSize × NumGpuBlocks` or skip K3 for that variant.

---

## 5. E2E Latency Model

### 5.1 Preferred path — direct observation (all data already in ReplicaMetrics)

```
E2E(v)   = AvgTTFT(v) + AvgOutputTokens(v) × AvgITL(v)   [seconds]
```

For per-$(w,v)$ decomposition, use the proportional approximation since
per-request tagging is not available from vLLM aggregate histograms:

```
TTFT(w, v) ≈ TTFT(v) · (IL(w) / AvgInputTokens(v))    [linear IL scaling]
ITL(w, v)  ≈ ITL(v)                                    [IL-independent fallback]

E2E(w, v) = TTFT(w, v) + OL(w) · ITL(w, v)
```

This reuses the same `AvgTTFT` and `AvgITL` fields consumed by the existing
queueing-model tuner (Kalman filter in `internal/engines/analyzers/queueingmodel/tuner/`).

### 5.2 Fallback path — linear ITL model

When `AvgTTFT` and `AvgITL` are unavailable (zero), use the structural model:

```
ITL(w, v) ≈ a_{v,w} · KV%(v) + b_{v,w}
```

where `KV%(v) = KvCacheUsage` and parameters $(a_{v,w}, b_{v,w})$ are learned
online via recursive least squares from windows where one workload type
dominates.  Default starting values (from `internal/engines/analyzers/queueingmodel/tuner/defaults.go`):

```go
DefaultExpectedTTFT = 50.0   // ms
DefaultExpectedITL  = 5.0    // ms
```

---

## 6. K3 Supply and Demand Signals

Using per-variant aggregates across all pods of variant $v$:

$$
D_v = \sum_{w \in \mathcal{W}} \frac{N(w,v)}{E2E(w,v)}
$$

$$
S_v = \sum_{w \in \mathcal{W}} \frac{N_{\max}(w,v)}{E2E(w,v)}
$$

$$
\Delta_v = \left\lceil \frac{D_v}{S_v} \right\rceil - I_v
$$

Standard dampening, hysteresis, and min/max replica guardrails apply (shared
with existing engines via `internal/actuator/`).

---

## 7. Concrete PromQL Queries Needed

All queries below use the **same label selectors** as the existing saturation
queries in `internal/collector/registration/saturation.go`.

New registrations required in a new file
`internal/collector/registration/k3.go`:

```go
// N(v): running concurrency proxy — not yet collected
// Query: max by (pod) (vllm:num_requests_running{namespace=...,model_name=...})
QueryRunningRequests = "running_requests"

// avg TTFT — already registered as QueryAvgTTFT in queueing_model.go
// avg ITL  — already registered as QueryAvgITL in queueing_model.go
// avg input tokens  — already registered as QueryAvgInputTokens in saturation.go
// avg output tokens — already registered as QueryAvgOutputTokens in saturation.go
// prefix cache hit rate — already registered as QueryPrefixCacheHitRate in saturation.go
// KV cache config — already registered as QueryCacheConfigInfo in saturation.go
// KV cache usage  — already registered as QueryKvCacheUsage in saturation.go
```

The only **new** query needed is `running_requests`:

```promql
max by (pod) (
  vllm:num_requests_running{namespace="{{.namespace}}",model_name="{{.modelID}}"}
)
```

This provides a direct $N(v)$ without relying on the Little's Law approximation.

### EPP queue metrics (already collected for scale-from-zero)

```
inference_extension_flow_control_queue_size{model_name=..., inference_pool=...}
```

These can supplement $N(v)$ as a leading indicator: if EPP queue is non-zero,
$D_v$ is underestimated by in-flight metrics alone.

---

## 8. Implementation Steps

### Step 1 — Add `running_requests` query registration

File: `internal/collector/registration/k3.go`

```go
package registration

const QueryRunningRequests = "running_requests"

func RegisterK3Queries(sourceRegistry *source.SourceRegistry) {
    registry := sourceRegistry.Get("prometheus").QueryList()
    registry.MustRegister(source.QueryTemplate{
        Name:     QueryRunningRequests,
        Type:     source.QueryTypePromQL,
        Template: `max by (pod) (vllm:num_requests_running` +
            `{namespace="{{.namespace}}",model_name="{{.modelID}}"})`,
        Params:      []string{source.ParamNamespace, source.ParamModelID},
        Description: "Current running (in-flight) requests per pod",
    })
}
```

### Step 2 — Extend `ReplicaMetrics` with `RunningRequests`

File: `internal/interfaces/saturation_analyzer.go`

```go
// RunningRequests is the number of requests currently being processed.
// Sourced from vllm:num_requests_running.
// Used by K3 as a direct N(v) estimate without Little's Law.
// Zero when metric is unavailable.
RunningRequests int64
```

### Step 3 — Populate `RunningRequests` in `replica_metrics.go`

In `internal/collector/replica_metrics.go`, follow the existing pattern for
`QueryKvCacheUsage` / `QueryAvgTTFT` to fetch and populate the new field.

### Step 4 — Implement the K3 analyzer

File: `internal/engines/analyzers/k3/analyzer.go`

Key inputs per control window (all from `[]interfaces.ReplicaMetrics` grouped by variant):

```go
type Input struct {
    Replicas        []interfaces.ReplicaMetrics   // all pods of variant v
    CurrentReplicas int                           // I_v
    WorkloadBins    []WorkloadBin                 // w bins (IL, OL midpoints)
}

type WorkloadBin struct {
    IL float64  // representative input length (tokens)
    OL float64  // representative output length (tokens)
    Pi float64  // mixture weight π_w (from system-wide N(w)/total)
}
```

Output:
```go
type Result struct {
    Demand  float64  // D_v
    Supply  float64  // S_v
    Ratio   float64  // D_v / S_v
    Delta   int      // recommended replica delta
}
```

### Step 5 — Wire K3 into the controller loop

Register as a new `AnalyzerEngine` in `internal/engines/` alongside the
existing saturation and queueing-model engines.  The `VariantAutoscaling` CRD
spec should include a field to select K3 (or combine signals, e.g., max of K1,
K2, K3 deltas).

### Step 6 — Workload bin configuration

Add a `k3` section to the existing `config.yaml` / `ConfigMap`:

```yaml
k3:
  enabled: false
  workloadBins:
    - name: short
      ilMin: 0
      ilMax: 512
      olMin: 0
      olMax: 256
    - name: medium
      ilMin: 512
      ilMax: 2048
      olMin: 256
      olMax: 1024
    - name: long
      ilMin: 2048
      ilMax: 0       # unbounded
      olMin: 1024
      olMax: 0
  emaAlpha: 0.3          # EMA smoothing factor for E2E and H%
  hysteresisThreshold: 0.1   # |Delta_v| must exceed this fraction before acting
  minDelta: 1
  maxDelta: 5
```

---

## 9. Robustness and Safety

| Concern | Mitigation |
|---|---|
| `E2E(w,v) ≈ 0` | Guard: `max(E2E, 1e-3)` in denominator |
| `S_v ≈ 0` (no capacity info) | Guard: `max(S_v, 1e-6)`; skip K3 and log |
| Stale metrics | Use existing `ReplicaMetricsMetadata.Age` freshness check; skip pods with stale data |
| Noisy `AvgITL` | Apply EMA: `AvgITL_smooth = α · AvgITL + (1-α) · prev` |
| $\pi_w$ degenerate (single workload type) | Works correctly; $D_v / S_v$ reduces to concurrency ratio |
| EPP metrics lack namespace label | Known issue (TODO #2309); filter by `inference_pool` + `model_name` as workaround |
| Missing `vllm:num_requests_running` | Fall back to Little's Law: `N(v) = ArrivalRate × E2E(v)` |

---

## 10. Metric Availability Summary

| Metric | Status | Source |
|---|---|---|
| `KvCacheUsage` | ✅ Already collected | `vllm:kv_cache_usage_perc` |
| `TotalKvCapacityTokens` | ✅ Already collected | `vllm:cache_config_info` |
| `PrefixCacheHitRate` (H%) | ✅ Already collected | `vllm:prefix_cache_hits/queries` |
| `AvgInputTokens` (IL proxy) | ✅ Already collected | `vllm:request_prompt_tokens_sum/count` |
| `AvgOutputTokens` (OL proxy) | ✅ Already collected | `vllm:request_generation_tokens_sum/count` |
| `AvgTTFT` | ✅ Already collected | `vllm:time_to_first_token_seconds_sum/count` |
| `AvgITL` | ✅ Already collected | `vllm:time_per_output_token_seconds_sum/count` |
| `ArrivalRate` | ✅ Already collected | `vllm:request_success_total` or scheduler attempts |
| `RunningRequests` N(v) | ⚠️ New query needed | `vllm:num_requests_running` |
| EPP flow-control queue | ✅ Used by scale-from-zero | `inference_extension_flow_control_queue_size` |
| Per-$(w,v)$ latency histograms | ❌ Not available | Would require vLLM per-request tagging |

The only new Prometheus query required is `vllm:num_requests_running`.
All other inputs reuse existing `ReplicaMetrics` fields.

---

## 11. Pseudocode (controller-side)

```go
func (k3 *K3Analyzer) Analyze(
    ctx context.Context,
    replicas []interfaces.ReplicaMetrics,
    currentInstances int,
    bins []WorkloadBin,
) (delta int, err error) {

    // 1. Compute per-variant aggregates
    var (
        totalArrivalRate float64
        totalE2E         float64
        avgIL            float64
        avgOL            float64
        kvCap            float64  // KV_max(v) in tokens
        kvHitRate        float64  // H%(v)
        kvUsage          float64  // KV%(v)
        nReplicas        int
    )
    for _, rm := range replicas {
        if rm.ArrivalRate <= 0 {
            continue
        }
        e2e := rm.AvgTTFT + rm.AvgOutputTokens*rm.AvgITL
        if e2e <= 0 {
            continue
        }
        totalArrivalRate += rm.ArrivalRate
        totalE2E         += rm.ArrivalRate * e2e
        avgIL            += rm.ArrivalRate * rm.AvgInputTokens
        avgOL            += rm.ArrivalRate * rm.AvgOutputTokens
        kvCap            += float64(rm.TotalKvCapacityTokens)
        kvHitRate        += rm.ArrivalRate * rm.PrefixCacheHitRate
        kvUsage           = rm.KvCacheUsage   // use last pod value; or average
        nReplicas++
    }
    if totalArrivalRate == 0 || nReplicas == 0 {
        return 0, nil  // no signal
    }

    // Weighted averages
    avgE2E    := totalE2E / totalArrivalRate
    avgIL      = avgIL / totalArrivalRate
    avgOL      = avgOL / totalArrivalRate
    kvCapPerPod := kvCap / float64(nReplicas)
    h          := kvHitRate / totalArrivalRate
    if h == 0 { h = 1.0 }  // conservative: full KV consumption

    // 2. Compute mixture weights from bin membership
    // Nearest-bin assignment based on (avgIL, avgOL) per variant
    // (simplified: use single observed mean to assign bin mixture)
    piW := assignBins(bins, avgIL, avgOL)

    // 3. Compute N(v) — use RunningRequests if available, else Little's Law
    nV := float64(totalRunning(replicas))
    if nV == 0 {
        nV = totalArrivalRate * avgE2E
    }

    // 4. Compute D_v and S_v
    var Dv, Sv float64
    for _, bin := range bins {
        pi := piW[bin.Name]
        if pi == 0 {
            continue
        }
        nWV := nV * pi
        kvW := h * (bin.IL + 0.5*bin.OL)
        if kvW <= 0 { kvW = 1 }
        nMaxWV := kvCapPerPod / kvW

        e2eWV := ttftForBin(replicas, bin) + bin.OL*avgITL(replicas)
        if e2eWV <= 0 { e2eWV = avgE2E }

        Dv += nWV   / e2eWV
        Sv += nMaxWV / e2eWV
    }

    if Sv <= 0 {
        return 0, fmt.Errorf("K3: S_v is zero, skipping scaling decision")
    }

    target := int(math.Ceil(Dv / Sv))
    raw    := target - currentInstances
    delta   = applyHysteresis(raw, k3.cfg.HysteresisThreshold)
    delta   = clamp(delta, -k3.cfg.MaxDelta, k3.cfg.MaxDelta)
    return delta, nil
}
```

---

## 12. Integration with Existing Engines

K3 should be **additive** to K1 and K2, not a replacement.  Recommended
combination in the controller reconciliation loop:

```
delta_final(v) = max(delta_K1(v), delta_K2(v), delta_K3(v))
```

This ensures the most conservative (largest scale-out / smallest scale-in) wins.

K3 is particularly valuable when:
- Workload mix shifts (long-context bursts that inflate KV cost)
- Prefix cache hit rate changes (warm vs cold cache transitions)
- Variants differ in GPU memory capacity (heterogeneous deployments)
