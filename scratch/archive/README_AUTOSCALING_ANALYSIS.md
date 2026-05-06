# H100 vLLM Autoscaling Analysis - Complete Guide

## Overview

This directory contains a comprehensive analysis of H100 vLLM capacity and autoscaling strategies based on real measurement data. The analysis answers three critical questions for production deployment:

1. **How to estimate workload characteristics from vLLM metrics?**
2. **How to predict maximal capacity from lower utilization metrics?**
3. **When and how to scale vLLM instances?**

## Files in This Analysis

### 1. Data Files

- **`TA-H100_BS-65000__summary-W.csv`** - Raw measurement data from H100 vLLM experiments
  - Various workload types (input/output token combinations)
  - Performance metrics: TTFT, ITL, E2E latency, throughput
  - KV cache utilization measurements
  - Concurrency levels (MaxRun)

### 2. Analysis Scripts

- **`analyze_h100_capacity.py`** - Python script to analyze capacity data
  - Estimates N_max (maximal concurrency) for each workload type
  - Calculates maximal RPS at near-saturation
  - Identifies optimal operating points (KV cache ≤ 80%)
  - Usage: `python3 analyze_h100_capacity.py`

### 3. Analysis Results

- **`h100_capacity_analysis_results.md`** - Detailed capacity analysis results
  - N_max and max RPS for all workload types
  - Impact of input/output length on capacity
  - Saturation behavior analysis
  - Capacity planning recommendations

### 4. Operational Guides

- **`h100_runtime_monitoring_and_autoscaling.md`** - Complete operational guide
  - How to estimate In-Tok, Out-Tok, RPS from vLLM metrics
  - Capacity prediction algorithms from lower utilization
  - Autoscaling decision framework
  - Prometheus query examples

### 5. Implementation

- **`vllm_autoscaler_implementation.py`** - Production-ready autoscaler implementation
  - `VLLMMetrics` - Data structure for vLLM metrics
  - `WorkloadProfile` - Workload characterization
  - `H100CapacityTable` - Lookup table from analysis
  - `CapacityPredictor` - Predict max capacity from current metrics
  - `VLLMAutoscaler` - Complete autoscaling logic
  - Usage: `python3 vllm_autoscaler_implementation.py`

## Quick Start

### 1. Understanding Your Workload

```python
from vllm_autoscaler_implementation import VLLMMetrics, WorkloadProfile

# Get metrics from your vLLM instance
metrics = VLLMMetrics(
    kv_cache_usage_perc=0.60,
    num_requests_running=30,
    num_requests_waiting=0,
    e2e_latency_avg=5.0,
    e2e_latency_p50=4.8,
    e2e_latency_p95=6.5,
    rps=6.0,
    prompt_tokens_rate=30000,  # From Prometheus
    generation_tokens_rate=1800,  # From Prometheus
    timestamp=datetime.now()
)

# Estimate workload characteristics
workload = WorkloadProfile.from_metrics(metrics)
print(f"Avg Input: {workload.avg_input_tokens:.0f} tokens")
print(f"Avg Output: {workload.avg_output_tokens:.0f} tokens")
```

### 2. Predicting Maximum Capacity

```python
from vllm_autoscaler_implementation import VLLMAutoscaler

autoscaler = VLLMAutoscaler()

# Get capacity estimate
capacity = autoscaler.get_capacity_estimate(metrics, workload)
print(f"N_max: {capacity.N_max:.0f} concurrent requests")
print(f"Max RPS (safe): {capacity.RPS_max_safe:.2f}")
print(f"Current headroom: {capacity.headroom_pct:.1f}%")
```

### 3. Making Scaling Decisions

```python
# Make scaling decision
decision = autoscaler.make_scaling_decision(
    metrics=metrics,
    current_instances=1,
    workload_profile=workload
)

print(f"Action: {decision.action}")
print(f"Target Instances: {decision.target_instances}")
print(f"Reason: {decision.reason}")
```

## Key Findings Summary

### Capacity by Workload Type

| Input Tokens | Output Tokens | N_max | Max RPS | KV Cache @ N_max |
|--------------|---------------|-------|---------|------------------|
| 3000 | 300 | 64 | 7.0 | 51% ⭐ Best |
| 5000 | 300 | 49 | 4.0 | 66% |
| 5000 | 600 | 26 | 2.0 | 36% |
| 5000 | 1200 | 58 | 2.0 | 80% ⚠️ Threshold |
| 5000 | 1800 | 67 | 2.0 | 98% ⚠️ Saturated |

### Critical Thresholds

- **Saturation**: KV cache > 80%
- **Scale-out trigger**: KV cache ≥ 65%
- **Scale-in trigger**: KV cache ≤ 40%
- **Target utilization**: 60% KV cache

### Autoscaling Rules

1. **Scale Out When:**
   - KV cache ≥ 65% (proactive)
   - KV cache ≥ 75% (urgent)
   - Queue depth > 5 requests
   - P95 latency > 2× P50 latency

2. **Number of Instances to Add:**
   - Conservative: Add 1 instance
   - Calculated: `ceil(current_kv / target_kv) - current_instances`

3. **Scale In When:**
   - KV cache ≤ 40% for > 5 minutes
   - Projected utilization after scale-in ≤ 60%

## Prometheus Queries for Monitoring

```promql
# Current RPS
rate(vllm:request_success_total[1m])

# Average input tokens per request
rate(vllm:prompt_tokens_total[5m]) / rate(vllm:request_success_total[5m])

# Average output tokens per request
rate(vllm:generation_tokens_total[5m]) / rate(vllm:request_success_total[5m])

# KV cache utilization
vllm:kv_cache_usage_perc

# Concurrent requests
vllm:num_requests_running

# Queue depth
vllm:num_requests_waiting

# Time to saturation (minutes)
(0.80 - vllm:kv_cache_usage_perc) / deriv(vllm:kv_cache_usage_perc[5m]) / 60
```

## Integration with llm-d Workload Variant Autoscaler

This analysis provides the foundation for implementing saturation-based autoscaling in the llm-d controller:

### 1. Metrics Collection

The controller already collects vLLM metrics via:
- Pod scraping (`internal/collector/source/pod/`)
- Prometheus queries (`internal/collector/source/prometheus/`)

### 2. Saturation Detection

Implement in `internal/saturation/analyzer.go`:

```go
type SaturationAnalyzer struct {
    kvCacheThreshold float64  // 0.65 for scale-out
    queueThreshold   int      // 5 for urgent scale-out
}

func (a *SaturationAnalyzer) IsSaturated(metrics *Metrics) bool {
    return metrics.KVCacheUsage >= a.kvCacheThreshold ||
           metrics.QueueDepth > a.queueThreshold
}
```

### 3. Capacity Prediction

Implement capacity table lookup:

```go
type CapacityTable map[WorkloadKey]Capacity

func (t CapacityTable) GetCapacity(inputTokens, outputTokens int) Capacity {
    // Lookup from H100 analysis data
    // Return N_max and max_rps for workload type
}
```

### 4. Scaling Decision

Integrate with `internal/engines/pipeline/`:

```go
func (e *Engine) CalculateDesiredReplicas(
    current int,
    metrics *Metrics,
    workload *WorkloadProfile,
) int {
    if metrics.KVCacheUsage >= 0.65 {
        // Scale out
        return current + calculateScaleOutCount(metrics.KVCacheUsage)
    }
    if metrics.KVCacheUsage <= 0.40 {
        // Scale in (conservative)
        return max(minReplicas, current - 1)
    }
    return current
}
```

## Best Practices

### 1. Monitoring

- Monitor KV cache utilization as primary metric
- Track queue depth for early warning
- Alert on P95 latency degradation
- Log all scaling decisions

### 2. Scaling Strategy

- Use 5-minute cooldown between scaling actions
- Scale out aggressively (multiple instances if needed)
- Scale in conservatively (1 instance at a time)
- Maintain N+1 redundancy

### 3. Workload-Specific Tuning

- Adjust thresholds for long-context workloads
- Use capacity table for accurate predictions
- Monitor actual vs predicted capacity
- Update capacity table with production data

### 4. Safety Margins

- Keep 10-20% capacity headroom
- Never exceed 80% KV cache in steady state
- Set max_instances limit to prevent runaway scaling
- Implement circuit breakers for rapid scaling

## Future Work

1. **Dynamic Capacity Learning**
   - Collect production metrics to refine capacity table
   - Adapt to different GPU types (A100, H100, etc.)
   - Learn workload-specific patterns

2. **Predictive Scaling**
   - Use time-series forecasting for proactive scaling
   - Detect traffic patterns (daily, weekly cycles)
   - Pre-scale before expected load increases

3. **Cost Optimization**
   - Balance performance vs cost
   - Use spot instances for burst capacity
   - Implement scale-to-zero for idle periods

4. **Multi-Model Support**
   - Handle multiple models with different characteristics
   - Route requests to appropriate instance types
   - Optimize for mixed workloads

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [Gateway API Inference Extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)
- [llm-d Workload Variant Autoscaler](https://github.com/llm-d/llm-d-workload-variant-autoscaler)

## Contributing

To update this analysis with new data:

1. Add new measurements to `TA-H100_BS-65000__summary-W.csv`
2. Run `analyze_h100_capacity.py` to regenerate analysis
3. Update capacity table in `vllm_autoscaler_implementation.py`
4. Test with new workload profiles
5. Update documentation with findings

## License

This analysis is part of the llm-d project and follows the same license terms.