# Throughput Analyzer Implementation Plan

> **SUPERSEDED** — This document (2026-03-26) describes an early draft design based on
> Proposal 2 + 4 (EMA smoothing, dual prefill/decode channels, `RunningRequests`-based supply).
> The actual implementation diverged significantly. See the canonical references instead:
>
> - **`ideas/TA-Plan.md`** — PR-by-PR implementation roadmap (up to date)
> - **`ideas/TA-supply.md`** — supply estimation (μ_dec_sat via ITL(k) = A·k + B)
> - **`ideas/TA-demand.md`** — demand estimation (EPP primary, vLLM fallback, queue correction)
> - **`ideas/TA-PR4-plan.md`** — PR-4 design rationale and reviewer context
> - **`docs/developer-guide/throughput-analyzer.md`** — complete implementation reference

**Based on:** `throughput-analyzer-design-A.md` — Proposal 2 + 4 (Proactive Rate-Based Scaling with Multi-Analyzer Integration)
**Status:** SUPERSEDED (see above)
**Date:** 2026-03-26

---

## Summary

This plan implements the Throughput Analyzer from the detailed design document. The analyzer adds proactive, rate-based scaling signals (tokens/sec) that complement the saturation analyzer's instantaneous state signals (queue depth, KV utilization).

### Key Design Decisions

1. **Dual-Channel Architecture**: Separate prefill and decode channels with different supply estimation strategies
2. **Load-Aware Timing**: Current prefill capacity vs bounded decode ceiling (see §5.6 of design doc)
3. **EMA Smoothing**: Exponential moving average (α=0.3) for stable rate signals
4. **Multi-Analyzer Integration**: OR logic for scale-up, AND logic for scale-down with Saturation V2

---

## Metric Registration Reference

This section documents all metric registrations required for the Throughput Analyzer, organized by source file.

### Summary Table

| Query ID | Metric Source | vLLM Version | Purpose | Fallback Chain |
|----------|--------------|--------------|---------|----------------|
| `avg_prefill_time` | `vllm:request_prefill_time_seconds` | v0.7+ | Primary prefill timing | → `avg_ttft` if unavailable |
| `avg_itl` | `vllm:time_per_output_token_seconds` | v0.6+ | Decode speed (ITL) | None (required) |
| `running_requests` | `vllm:num_requests_running` | v0.6+ | Active decode batch size N | None (required) |
| `avg_ttft` | `vllm:time_to_first_token_seconds` | v0.6+ | Fallback prefill timing | Used when `avg_prefill_time` unavailable |
| `avg_decode_time` | `vllm:request_decode_time_seconds` | v0.7+ | Validation metric | Cross-check: `avg_output_tokens * avg_itl` |

### Registration File: `internal/collector/registration/throughput_analyzer.go`

```go
package registration

const (
	// QueryAvgPrefillTime measures pure prefill computation time (SCHEDULED → first NEW_TOKENS).
	// Excludes queue wait. Preferred over TTFT for supply estimation.
	// PromQL: rate(vllm:request_prefill_time_seconds_sum[5m]) / rate(vllm:request_prefill_time_seconds_count[5m])
	QueryAvgPrefillTime = "avg_prefill_time"

	// QueryAvgITL measures inter-token latency (time between output tokens).
	// Primary decode speed metric. Required for N/ITL throughput calculation.
	// PromQL: rate(vllm:time_per_output_token_seconds_sum[5m]) / rate(vllm:time_per_output_token_seconds_count[5m])
	QueryAvgITL = "avg_itl"

	// QueryRunningRequests is the current active decode batch size (N).
	// Gauge metric — no rate() function applied.
	// PromQL: vllm:num_requests_running
	QueryRunningRequests = "running_requests"

	// QueryAvgTTFT measures time to first token (arrival → first NEW_TOKENS).
	// Includes queue wait. Used as fallback when prefill_time unavailable.
	// PromQL: rate(vllm:time_to_first_token_seconds_sum[5m]) / rate(vllm:time_to_first_token_seconds_count[5m])
	QueryAvgTTFT = "avg_ttft"

	// QueryAvgDecodeTime measures total decode time per request.
	// Used for cross-validation: decode_time ≈ output_tokens * ITL.
	// PromQL: rate(vllm:request_decode_time_seconds_sum[5m]) / rate(vllm:request_decode_time_seconds_count[5m])
	QueryAvgDecodeTime = "avg_decode_time"
)

// RegisterThroughputAnalyzerQueries registers all throughput analyzer queries.
// Called once during engine initialization.
func RegisterThroughputAnalyzerQueries(r *Registry) {
	// Prefill timing - primary (vLLM v0.7+)
	r.Register(QueryAvgPrefillTime, NewQueryBuilder().
		Metric(metrics.VLLMRequestPrefillTimeSecondsSum).
		DivideBy(metrics.VLLMRequestPrefillTimeSecondsCount).
		Rate().
		Filter(LabelPod, LabelNamespace, LabelModelName).
		MaxBy(LabelPod).
		Build())

	// Decode timing - primary (vLLM v0.6+)
	r.Register(QueryAvgITL, NewQueryBuilder().
		Metric(metrics.VLLMTimePerOutputTokenSecondsSum).
		DivideBy(metrics.VLLMTimePerOutputTokenSecondsCount).
		Rate().
		Filter(LabelPod, LabelNamespace, LabelModelName).
		MaxBy(LabelPod).
		Build())

	// Active batch size - gauge (vLLM v0.6+)
	r.Register(QueryRunningRequests, NewQueryBuilder().
		Metric(metrics.VLLMNumRequestsRunning).
		Filter(LabelPod, LabelNamespace, LabelModelName).
		MaxBy(LabelPod).
		Build())

	// Prefill timing - fallback (vLLM v0.6+)
	r.Register(QueryAvgTTFT, NewQueryBuilder().
		Metric(metrics.VLLMTimeToFirstTokenSecondsSum).
		DivideBy(metrics.VLLMTimeToFirstTokenSecondsCount).
		Rate().
		Filter(LabelPod, LabelNamespace, LabelModelName).
		MaxBy(LabelPod).
		Build())

	// Decode validation (vLLM v0.7+)
	r.Register(QueryAvgDecodeTime, NewQueryBuilder().
		Metric(metrics.VLLMRequestDecodeTimeSecondsSum).
		DivideBy(metrics.VLLMRequestDecodeTimeSecondsCount).
		Rate().
		Filter(LabelPod, LabelNamespace, LabelModelName).
		MaxBy(LabelPod).
		Build())
}
```

### Constants File: `internal/constants/metrics.go`

New constants to add:

```go
const (
	// Throughput Analyzer metrics (vLLM v0.7+)
	// These metrics measure timing at the operation level, providing
	// per-token and per-request latency data for rate-based analysis.

	VLLMRequestPrefillTimeSecondsSum   = "vllm:request_prefill_time_seconds_sum"
	VLLMRequestPrefillTimeSecondsCount = "vllm:request_prefill_time_seconds_count"
	VLLMRequestDecodeTimeSecondsSum    = "vllm:request_decode_time_seconds_sum"
	VLLMRequestDecodeTimeSecondsCount  = "vllm:request_decode_time_seconds_count"
	VLLMNumRequestsRunning             = "vllm:num_requests_running"

	// Note: These constants already exist for Saturation V2:
	// VLLMTimePerOutputTokenSecondsSum   = "vllm:time_per_output_token_seconds_sum"
	// VLLMTimePerOutputTokenSecondsCount = "vllm:time_per_output_token_seconds_count"
	// VLLMTimeToFirstTokenSecondsSum     = "vllm:time_to_first_token_seconds_sum"
	// VLLMTimeToFirstTokenSecondsCount   = "vllm:time_to_first_token_seconds_count"
)
```

### Metric Usage in Throughput Formulas

| Formula Variable | Query ID | Calculation | Units |
|-----------------|----------|-------------|-------|
| `prefill_time_per_token` | `avg_prefill_time` or `avg_ttft` | `AvgPrefillTime / AvgInputTokens` | seconds/token |
| `N` (batch size) | `running_requests` | Direct value | requests |
| `B` (budget) | N/A | From variant config (`max_num_batched_tokens`) | tokens |
| `ITL` | `avg_itl` | Direct value | seconds/token |
| `prefill_throughput` | Derived | `(B - N) / prefill_time_per_token` | tokens/sec |
| `decode_throughput` | Derived | `N / ITL` | tokens/sec |

### Fallback Strategy

When `avg_prefill_time` is unavailable (vLLM < 0.7), the analyzer falls back to `avg_ttft`:

```go
func (a *ThroughputAnalyzer) getPrefillTimePerToken(rm ReplicaMetrics) float64 {
    // Priority 1: Direct prefill_time metric (vLLM v0.7+)
    if rm.AvgPrefillTime > 0 && rm.AvgInputTokens > 0 {
        return rm.AvgPrefillTime / rm.AvgInputTokens
    }

    // Priority 2: TTFT when queue is empty (queue wait ≈ 0)
    if rm.AvgTTFT > 0 && rm.QueueLength == 0 && rm.AvgInputTokens > 0 {
        return rm.AvgTTFT / rm.AvgInputTokens
    }

    // Priority 3: Minimum TTFT from history (approximates pure compute)
    // Implemented via timing baselines in RateHistory

    return 0 // Unavailable
}
```

---

## Phase 1: Metric Collection Implementation

### 1.1 New Prometheus Queries

Add 5 new queries to `internal/collector/registration/throughput_analyzer.go`:

```go
const (
    QueryAvgPrefillTime    = "avg_prefill_time"     // request_prefill_time_seconds
    QueryAvgITL            = "avg_itl"              // time_per_output_token_seconds
    QueryRunningRequests   = "running_requests"     // num_requests_running
    QueryAvgTTFT           = "avg_ttft"             // time_to_first_token_seconds (fallback)
    QueryAvgDecodeTime     = "avg_decode_time"      // request_decode_time_seconds (validation)
)

func RegisterThroughputAnalyzerQueries(r *registration.Registry) {
    // AvgPrefillTime: rate(vllm:request_prefill_time_seconds_sum) / rate(..._count)
    r.Register(QueryAvgPrefillTime, registration.NewQueryBuilder().
        Metric(metrics.VLLMRequestPrefillTimeSecondsSum).  // NEW constant
        DivideBy(metrics.VLLMRequestPrefillTimeSecondsCount). // NEW constant
        Rate().
        Filter(podLabel, namespaceLabel).
        MaxBy(podLabel).
        Build())

    // AvgITL: rate(vllm:time_per_output_token_seconds_sum) / rate(..._count)
    r.Register(QueryAvgITL, registration.NewQueryBuilder().
        Metric(metrics.VLLMTimePerOutputTokenSecondsSum).
        DivideBy(metrics.VLLMTimePerOutputTokenSecondsCount).
        Rate().
        Filter(podLabel, namespaceLabel).
        MaxBy(podLabel).
        Build())

    // RunningRequests: vllm:num_requests_running (gauge, no rate())
    r.Register(QueryRunningRequests, registration.NewQueryBuilder().
        Metric(metrics.VLLMNumRequestsRunning).  // NEW constant
        Filter(podLabel, namespaceLabel, modelNameLabel).
        MaxBy(podLabel).
        Build())

    // AvgTTFT: rate(vllm:time_to_first_token_seconds_sum) / rate(..._count)
    r.Register(QueryAvgTTFT, registration.NewQueryBuilder().
        Metric(metrics.VLLMTimeToFirstTokenSecondsSum).
        DivideBy(metrics.VLLMTimeToFirstTokenSecondsCount).
        Rate().
        Filter(podLabel, namespaceLabel).
        MaxBy(podLabel).
        Build())

    // AvgDecodeTime: rate(vllm:request_decode_time_seconds_sum) / rate(..._count)
    r.Register(QueryAvgDecodeTime, registration.NewQueryBuilder().
        Metric(metrics.VLLMRequestDecodeTimeSecondsSum).  // NEW constant
        DivideBy(metrics.VLLMRequestDecodeTimeSecondsCount). // NEW constant
        Rate().
        Filter(podLabel, namespaceLabel).
        MaxBy(podLabel).
        Build())
}
```

### 1.2 New Metric Constants

Add to `internal/constants/metrics.go`:

```go
// Throughput Analyzer metrics (vLLM v0.7+)
const (
    VLLMRequestPrefillTimeSecondsSum   = "vllm:request_prefill_time_seconds_sum"
    VLLMRequestPrefillTimeSecondsCount = "vllm:request_prefill_time_seconds_count"
    VLLMRequestDecodeTimeSecondsSum    = "vllm:request_decode_time_seconds_sum"
    VLLMRequestDecodeTimeSecondsCount  = "vllm:request_decode_time_seconds_count"
    VLLMNumRequestsRunning             = "vllm:num_requests_running"
    // Note: VLLMTimePerOutputTokenSecondsSum, VLLMTimeToFirstTokenSecondsSum already exist
)
```

### 1.3 ReplicaMetrics Extension

Extend `internal/interfaces/saturation_analyzer.go`:

```go
type ReplicaMetrics struct {
    // ... existing fields (PodName, VariantName, AcceleratorName, QueueLength, etc.) ...

    // --- New fields for Throughput Analyzer ---

    // RunningRequests is the number of requests currently in the decode phase.
    // Sourced from vllm:num_requests_running gauge.
    // This is N in the dual-channel model (N ≤ S = max_num_seqs).
    RunningRequests int

    // AvgPrefillTime is the average prefill computation time per request (seconds).
    // Sourced from rate(vllm:request_prefill_time_seconds_sum) / rate(..._count).
    // Pure GPU compute time — excludes queue wait (unlike TTFT).
    AvgPrefillTime float64

    // AvgITL is the average inter-token latency (seconds per output token).
    // Sourced from rate(vllm:time_per_output_token_seconds_sum) / rate(..._count).
    AvgITL float64

    // AvgTTFT is the average time to first token (seconds).
    // Sourced from rate(vllm:time_to_first_token_seconds_sum) / rate(..._count).
    // Includes queue wait + prefill time. Fallback when AvgPrefillTime unavailable.
    AvgTTFT float64

    // AvgDecodeTime is the average total decode time per request (seconds).
    // Sourced from rate(vllm:request_decode_time_seconds_sum) / rate(..._count).
    // Cross-validation: AvgDecodeTime ≈ AvgOutputTokens × AvgITL.
    AvgDecodeTime float64
}
```

### 1.4 Collector Integration

Modify `internal/collector/replica_metrics.go`:

1. Add new query IDs to the queries list in `FetchReplicaMetrics`
2. Process results and populate new `ReplicaMetrics` fields
3. Handle fallback from AvgPrefillTime to AvgTTFT when prefill_time unavailable

```go
// In FetchReplicaMetrics, add to metricQueries slice:
metricQueries := []metricQueryID{
    // ... existing queries ...
    {id: registration.QueryRunningRequests, resultType: promResultScalar},
    {id: registration.QueryAvgPrefillTime, resultType: promResultScalar},
    {id: registration.QueryAvgITL, resultType: promResultScalar},
    {id: registration.QueryAvgTTFT, resultType: promResultScalar},
}

// In podMetricData struct:
type podMetricData struct {
    // ... existing fields ...
    runningRequests  int64
    avgPrefillTime   float64
    avgITL           float64
    avgTTFT          float64
}

// In processing loop:
switch res.ID {
// ... existing cases ...
case registration.QueryRunningRequests:
    data.runningRequests = int64(res.Value)
case registration.QueryAvgPrefillTime:
    data.avgPrefillTime = res.Value
case registration.QueryAvgITL:
    data.avgITL = res.Value
case registration.QueryAvgTTFT:
    data.avgTTFT = res.Value
}

// In struct assignment (with fallback logic):
RunningRequests: data.runningRequests,
AvgPrefillTime: data.avgPrefillTime,
AvgITL: data.avgITL,
AvgTTFT: data.avgTTFT,
// Fallback: if AvgPrefillTime == 0 but AvgTTFT > 0 and QueueLength == 0,
// caller can use AvgTTFT as approximate prefill time
```

### 1.5 Engine Registration

Modify `internal/engines/saturation/engine.go`:

```go
func NewEngine(...) *Engine {
    // ... existing registrations ...

    // Register throughput analyzer queries
    registration.RegisterThroughputAnalyzerQueries(metricsRegistry)

    return &Engine{...}
}
```

---

## Phase 2: Throughput Analyzer Package

Create `internal/engines/analyzers/throughput/` package:

### 2.1 Config Types (`config.go`)

```go
package throughput

import "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"

const AnalyzerName = "throughput"

type Config struct {
    // EnableThroughput enables the throughput analyzer
    EnableThroughput bool `yaml:"enableThroughput,omitempty"`

    // ThroughputWeight is the relative weight of throughput signals vs saturation
    ThroughputWeight float64 `yaml:"throughputWeight,omitempty"`

    // RateSmoothingAlpha is the EMA alpha (0.0-1.0)
    RateSmoothingAlpha float64 `yaml:"rateSmoothingAlpha,omitempty"`

    // RateLookbackWindow is cycles to retain for rate history
    RateLookbackWindow int `yaml:"rateLookbackWindow,omitempty"`

    // ThroughputScaleUpThreshold triggers scale up when demand/supply > threshold
    ThroughputScaleUpThreshold float64 `yaml:"throughputScaleUpThreshold,omitempty"`

    // ThroughputScaleDownBoundary allows scale down when demand/supply < boundary
    ThroughputScaleDownBoundary float64 `yaml:"throughputScaleDownBoundary,omitempty"`
}

func (c *Config) WithDefaults() *Config {
    if c.ThroughputWeight == 0 {
        c.ThroughputWeight = 0.8
    }
    if c.RateSmoothingAlpha == 0 {
        c.RateSmoothingAlpha = 0.3
    }
    if c.RateLookbackWindow == 0 {
        c.RateLookbackWindow = 10
    }
    if c.ThroughputScaleUpThreshold == 0 {
        c.ThroughputScaleUpThreshold = 0.85
    }
    if c.ThroughputScaleDownBoundary == 0 {
        c.ThroughputScaleDownBoundary = 0.70
    }
    return c
}
```

### 2.2 Internal Types (`types.go`)

```go
package throughput

// ChannelMetrics holds demand and supply for one channel
type ChannelMetrics struct {
    DemandRate  float64 // tokens/sec arriving
    SupplyRate  float64 // tokens/sec capacity
    Utilization float64 // DemandRate / SupplyRate
}

// PrefillChannelHistory tracks smoothed prefill rates
type PrefillChannelHistory struct {
    DemandEMA      float64 // EMA of prefill demand
    SupplyEMA      float64 // EMA of prefill supply (current capacity)
    TimingBaseline float64 // Min observed prefill_time_per_token
}

// DecodeChannelHistory tracks smoothed decode rates
type DecodeChannelHistory struct {
    DemandEMA             float64 // EMA of decode demand
    SupplyEMA             float64 // EMA of decode supply (bounded ceiling)
    MaxObservedThroughput float64 // Peak N/ITL observed
    TimingBaseline        float64 // Min observed ITL
}

// RateHistory tracks smoothed rates for both channels per variant
type RateHistory struct {
    Prefill             PrefillChannelHistory
    Decode              DecodeChannelHistory
    PreviousQueueTokens float64
    CycleCount          int
}

// ReplicaThroughput holds per-replica computed metrics
type ReplicaThroughput struct {
    PodName             string
    VariantName         string
    AcceleratorName     string
    PrefillTimePerToken float64 // seconds per input token
    PrefillBudgetTokens int     // B - N tokens
    PrefillThroughput   float64 // (B-N) / prefill_time_per_token
    ITL                 float64 // seconds per output token
    RunningRequests     int     // N
    DecodeThroughput    float64 // N / ITL
}
```

### 2.3 Analyzer Implementation (`analyzer.go`)

```go
package throughput

import (
    "context"
    "fmt"
    "math"

    "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

type ThroughputAnalyzer struct {
    rateHistory map[string]*RateHistory // key: "modelID|variantName"
    config      *Config
}

func NewThroughputAnalyzer(config *Config) *ThroughputAnalyzer {
    return &ThroughputAnalyzer{
        rateHistory: make(map[string]*RateHistory),
        config:      config.WithDefaults(),
    }
}

func (a *ThroughputAnalyzer) Name() string {
    return AnalyzerName
}

func (a *ThroughputAnalyzer) Analyze(
    ctx context.Context,
    input interfaces.AnalyzerInput,
) (*interfaces.AnalyzerResult, error) {

    if !a.config.EnableThroughput {
        return &interfaces.AnalyzerResult{ // Return empty result if disabled
            ScalingSignals: make(map[string]interfaces.ScalingSignal),
        }, nil
    }

    // 1. Per-replica throughput computation
    replicaThroughputs := a.computeReplicaThroughputs(input.ReplicaMetrics, input.Variants)

    // 2. Per-variant dual-channel aggregation with EMA smoothing
    effectiveUtilizations := a.aggregateByVariant(
        replicaThroughputs,
        input.SchedulerQueues,
        input.Config,
        input.PDRole,
    )

    // 3. Build scaling signals
    signals := make(map[string]interfaces.ScalingSignal)
    for variantKey, util := range effectiveUtilizations {
        signals[variantKey] = interfaces.ScalingSignal{
            VariantName:       variantKey,
            RequiredCapacity:  a.computeRequiredCapacity(util, input.Config),
            Utilization:       util,
            Confidence:        a.computeConfidence(variantKey),
            Reason:            fmt.Sprintf("throughput utilization: %.2f", util),
        }
    }

    return &interfaces.AnalyzerResult{
        ScalingSignals: signals,
    }, nil
}

// computeReplicaThroughputs calculates per-replica prefill/decode throughput
func (a *ThroughputAnalyzer) computeReplicaThroughputs(
    replicas []interfaces.ReplicaMetrics,
    variants map[string]interfaces.VariantConfig,
) []ReplicaThroughput {
    // Implementation: §7.3 step 1 of design doc
    // For each replica:
    //   - Get B (max_num_batched_tokens) and S (max_num_seqs) from variant config
    //   - Compute prefill_time_per_token from AvgPrefillTime or AvgTTFT fallback
    //   - Compute pref illBudgetTokens = B - N (where N = RunningRequests)
    //   - Compute prefillThroughput = (B-N) / prefill_time_per_token
    //   - Compute decodeThroughput = N / AvgITL
    //   - Update timing baselines in history
    return nil // TODO
}

// aggregateByVariant groups replicas by variant and computes EMA-smoothed rates
func (a *ThroughputAnalyzer) aggregateByVariant(
    replicaThroughputs []ReplicaThroughput,
    schedulerQueues map[string]interfaces.SchedulerQueueMetrics,
    config *interfaces.SaturationScalingConfig,
    role interfaces.PDRole,
) map[string]float64 {
    // Implementation: §7.3 step 2 of design doc
    // For each variant:
    //   - Sum prefill throughput across replicas → prefillSupply
    //   - Sum decode throughput across replicas → decodeDemand (raw)
    //   - Compute bounded decode ceiling → decodeSupply
    //   - Add queue growth to demand (split by input/output fraction)
    //   - Apply EMA smoothing
    //   - Select active channel based on P/D role
    //   - Return effective utilization
    return nil // TODO
}

func (a *ThroughputAnalyzer) computeRequiredCapacity(
    utilization float64,
    config *interfaces.SaturationScalingConfig,
) int32 {
    if utilization > float64(a.config.ThroughputScaleUpThreshold) {
        // Scale up: return positive capacity
        return int32(math.Ceil(utilization * 10)) // Example scaling formula
    }
    if utilization < float64(a.config.ThroughputScaleDownBoundary) {
        // Scale down signal (negative or zero capacity)
        return 0
    }
    return 0 // Steady state
}

func (a *ThroughputAnalyzer) computeConfidence(variantKey string) float64 {
    // Based on history cycle count and metric availability
    history, exists := a.rateHistory[variantKey]
    if !exists || history.CycleCount < 3 {
        return 0.5 // Low confidence initially
    }
    if history.CycleCount < 10 {
        return 0.7 // Medium confidence after warm-up
    }
    return 0.9 // High confidence with sufficient history
}
```

### 2.4 Unit Tests (`analyzer_test.go`)

Comprehensive Ginkgo/Gomega tests:

```go
package throughput

import (
    "context"
    "testing"

    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"

    "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

func TestThroughputAnalyzer(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "Throughput Analyzer Suite")
}

var _ = Describe("ThroughputAnalyzer", func() {
    var (
        analyzer *ThroughputAnalyzer
        config   *Config
    )

    BeforeEach(func() {
        config = &Config{
            EnableThroughput:            true,
            RateSmoothingAlpha:          0.3,
            ThroughputScaleUpThreshold:  0.85,
            ThroughputScaleDownBoundary: 0.70,
        }
        analyzer = NewThroughputAnalyzer(config)
    })

    Describe("Name", func() {
        It("returns 'throughput'", func() {
            Expect(analyzer.Name()).To(Equal("throughput"))
        })
    })

    Describe("Analyze", func() {
        Context("when disabled", func() {
            It("returns empty signals", func() {
                disabledConfig := &Config{EnableThroughput: false}
                disabledAnalyzer := NewThroughputAnalyzer(disabledConfig)

                result, err := disabledAnalyzer.Analyze(context.Background(),
                    interfaces.AnalyzerInput{Config: &interfaces.SaturationScalingConfig{}})

                Expect(err).ToNot(HaveOccurred())
                Expect(result.ScalingSignals).To(BeEmpty())
            })
        })

        Context("with single replica", func() {
            It("computes prefill throughput correctly", func() {
                // Test (B-N)/prefill_tpt calculation
            })

            It("computes decode throughput correctly", func() {
                // Test N/ITL calculation
            })

            It("uses AvgPrefillTime when available", func() {
                // Verify AvgPrefillTime used directly
            })

            It("falls back to AvgTTFT when AvgPrefillTime is zero", func() {
                // Verify fallback logic
            })
        })

        Context("with multiple replicas", func() {
            It("aggregates demands across replicas", func() {
                // Sum of replica throughputs
            })

            It("computes bounded decode ceiling", func() {
                // min(theoretical, empirical) logic
            })
        })

        Context("with queue growth", func() {
            It("adds queue growth to demand", func() {
                // Scheduler queue growth component
            })

            It("splits queue growth by input/output ratio", func() {
                // inputFraction vs outputFraction
            })
        })

        Context("with EMA smoothing", func() {
            It("applies alpha to new demand values", func() {
                // EMA_t = α × value_t + (1-α) × EMA_{t-1}
            })

            It("converges over multiple cycles", func() {
                // Integration test over multiple Analyze calls
            })
        })

        Context("scale decisions", func() {
            It("triggers scale up when utilization > threshold", func() {
                // utilization = demand/supply > Threshold
            })

            It("allows scale down when utilization < boundary", func() {
                // utilization < ScaleDownBoundary
            })

            It("maintains steady state between boundaries", func() {
                // boundary < utilization < threshold
            })
        })

        Context("P/D role selection", func() {
            It("uses prefill channel for RolePrefill", func() {
                // effectiveUtil = prefillUtil
            })

            It("uses decode channel for RoleDecode", func() {
                // effectiveUtil = decodeUtil
            })

            It("uses max for RoleBoth", func() {
                // effectiveUtil = max(prefillUtil, decodeUtil)
            })
        })
    })
})
```

---

## Phase 3: Engine Integration

### 3.1 Multi-Analyzer Framework

Modify `internal/engines/saturation/engine.go`:

```go
type Engine struct {
    // ... existing fields ...
    analyzers []interfaces.Analyzer  // Multiple analyzers
}

func NewEngine(...) (*Engine, error) {
    // ... existing setup ...

    // Initialize analyzers
    analyzers := []interfaces.Analyzer{
        saturation_v2.NewAnalyzer(capacityStore),
    }

    // Add throughput analyzer if enabled in config
    if cfg.Throughput.EnableThroughput {
        analyzers = append(analyzers,
            throughput.NewThroughputAnalyzer(&cfg.Throughput))
    }

    return &Engine{
        analyzers: analyzers,
        // ... other fields ...
    }, nil
}

func (e *Engine) GenerateRecommendation(
    ctx context.Context,
    objective interfaces.InferenceObjective,
    modelID string,
) (*interfaces.ScalingRecommendation, error) {

    input := interfaces.AnalyzerInput{
        ReplicaMetrics:  e.collectReplicaMetrics(),
        SchedulerQueues: e.collectSchedulerQueues(),
        Variants:        e.variants,
        Config:          e.config,
        PDRole:          e.pdRole,
        ModelID:         modelID,
    }

    // Run all analyzers in parallel
    analyzerResults := make([]*interfaces.AnalyzerResult, len(e.analyzers))
    for i, analyzer := range e.analyzers {
        result, err := analyzer.Analyze(ctx, input)
        if err != nil {
            // Log error but continue with other analyzers
            continue
        }
        analyzerResults[i] = result
    }

    // Combine signals using multi-analyzer framework (§8.1 of design doc)
    combinedSignals := e.combineSignals(analyzerResults)

    // Apply decision policy
    recommendation := e.applyDecisionPolicy(combinedSignals)

    return recommendation, nil
}

// combineSignals implements OR logic for scale-up, weighted average otherwise
func (e *Engine) combineSignals(
    results []*interfaces.AnalyzerResult,
) map[string]interfaces.ScalingSignal {
    // Implementation: §8.1 of design doc
    // - Scale-up: OR logic (max of RequiredCapacity across analyzers)
    // - Utilization: confidence-weighted average
    // - Scale-down: AND logic (all analyzers must agree)
    return nil // TODO
}
```

### 3.2 Config Extension

Extend `internal/config/types.go`:

```go
type SaturationScalingConfig struct {
    // ... existing fields ...

    // Throughput contains the throughput analyzer configuration
    Throughput throughput.Config `yaml:"throughput,omitempty"`
}
```

---

## Phase 4: Testing and Validation

### 4.1 Unit Tests

| Test Category | Coverage |
|--------------|----------|
| Metric queries | Verify PromQL string generation |
| Replica throughput | (B-N)/prefill_tpt, N/ITL calculations |
| Channel aggregation | Demand summing, supply estimation |
| EMA smoothing | α values, convergence properties |
| Fallback logic | AvgTTFT when AvgPrefillTime unavailable |
| P/D role selection | RolePrefill, RoleDecode, RoleBoth |
| Scale boundaries | Threshold vs boundary behavior |
| Multi-analyzer | Signal combination logic |

**Target: 36+ test cases** (following saturation_v2 pattern)

### 4.2 Integration Tests

1. **Metrics collection**: Verify new queries return valid data from Prometheus
2. **End-to-end**: Deploy analyzer with simulator, verify rate signals
3. **Multi-analyzer**: Verify OR/AND logic with both saturation and throughput

### 4.3 Benchmark Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| Linear ramp (20→60 RPS) | Throughput detects 60s before saturation |
| Step change | Both analyzers detect, throughput has slight lead |
| Steady state | No false positives from rate noise |
| Burst traffic | Saturation may detect first (acceptable) |
| P/D disaggregated | P/D throughput isolation |

---

## Phase 5: Rollout

### 5.1 Configuration

Default `SaturationScalingConfig` with throughput disabled:

```yaml
spec:
  scalingStrategy:
    saturationScaling:
      # ... existing fields ...
      throughput:
        enableThroughput: false  # Disabled by default for safety
        throughputWeight: 0.8
        rateSmoothingAlpha: 0.3
        throughputScaleUpThreshold: 0.85
        throughputScaleDownBoundary: 0.70
```

### 5.2 Gradual Enablement

1. **Dev/Staging**: Enable by default, validate no regressions
2. **Production Pilot**: Enable for specific models, compare scale timing
3. **Production Default**: Enable globally after validation

---

## Appendix: Key Formulas Reference

### Per-Replica Calculations

```
prefill_time_per_token = AvgPrefillTime / AvgInputTokens  [fallback to TTFT if unavailable]
prefillBudgetTokens    = B - N                           [tokens]
prefillThroughput      = prefillBudgetTokens / prefill_time_per_token  [input tokens/sec]

decodeThroughput = N / AvgITL  [output tokens/sec]
Where: N = RunningRequests, N ≤ S = max_num_seqs
```

### Per-Variant Aggregation

```
prefillDemand = Σ prefillThroughput + queueGrowth × inputFraction
prefillSupply = Σ prefillThroughput  [current capacity]

decodeDemand  = Σ decodeThroughput + queueGrowth × outputFraction
decodeSupply  = readyReplicas × min(N_max/medianITL, maxObservedThroughput)

inputFraction  = avgInputTokens / (avgInputTokens + avgOutputTokens)
outputFraction = 1 - inputFraction
```

### EMA Smoothing

```
EMA_t = α × value_t + (1 - α) × EMA_{t-1}
Default α = 0.3
```

### Scale Decision

```
ScaleUp:   utilization > ThroughputScaleUpThreshold    (0.85 default)
ScaleDown: utilization < ThroughputScaleDownBoundary   (0.70 default)
utilization = max(prefillDemand/prefillSupply, decodeDemand/decodeSupply)  [for RoleBoth]
```

---

## References

1. `throughput-analyzer-design-A.md` — Detailed design document this plan implements
2. `internal/engines/saturation_v2/` — Reference implementation pattern
3. Proposal 2 — Proactive Throughput-Based Scaling (design rationale)
4. Proposal 4 — Multi-Analyzer Unification Framework (signal combination)
