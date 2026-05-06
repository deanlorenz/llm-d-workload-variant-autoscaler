# H100 vLLM Runtime Monitoring and Autoscaling Guide

## Overview

This guide explains how to use vLLM metrics in production to:
1. Estimate workload characteristics (In-Tok, Out-Tok, RPS) from runtime metrics
2. Predict maximal capacity at near-saturation from lower utilization metrics
3. Make autoscaling decisions based on real-time metrics

## 1. Estimating Workload Characteristics from vLLM Metrics

### Available vLLM Metrics

From the llm-d inference scheduler EPP CLI reference, the key metrics are:

```
vllm:num_requests_waiting    # Queued requests
vllm:num_requests_running    # Currently processing requests
vllm:kv_cache_usage_perc     # KV cache utilization (0-1)
vllm:lora_requests_info      # LoRA adapter info
vllm:cache_config_info       # Cache configuration
```

Additional metrics typically available:
- `vllm:prompt_tokens_total` - Total prompt tokens processed
- `vllm:generation_tokens_total` - Total generation tokens produced
- `vllm:request_success_total` - Completed requests
- `vllm:time_to_first_token_seconds` - TTFT histogram
- `vllm:time_per_output_token_seconds` - ITL histogram
- `vllm:e2e_request_latency_seconds` - E2E latency histogram

### Estimating Input Tokens (In-Tok)

**Method 1: From Prometheus Metrics (Preferred)**

```python
# Calculate average input tokens per request over time window
avg_input_tokens = (
    rate(vllm:prompt_tokens_total[5m]) / 
    rate(vllm:request_success_total[5m])
)
```

**Method 2: From Request Logs**

If you have access to request logs, parse the actual prompt lengths.

**Method 3: From TTFT and Prefill Time**

```python
# Approximate relationship (model-dependent)
# TTFT ≈ prefill_overhead + (input_tokens * prefill_time_per_token)
# From our data: prefill_time_per_token ≈ 0.03ms for H100

estimated_input_tokens = (TTFT - prefill_overhead) / 0.00003
```

### Estimating Output Tokens (Out-Tok)

**Method 1: From Prometheus Metrics (Preferred)**

```python
# Calculate average output tokens per request
avg_output_tokens = (
    rate(vllm:generation_tokens_total[5m]) / 
    rate(vllm:request_success_total[5m])
)
```

**Method 2: From ITL and E2E**

```python
# E2E ≈ TTFT + (output_tokens * ITL)
estimated_output_tokens = (E2E - TTFT) / ITL
```

**Method 3: From GPS (Generation Tokens Per Second)**

```python
# GPS = total_generation_tokens / time_period
# If you know RPS:
avg_output_tokens = GPS / RPS
```

### Estimating Current RPS

**Method 1: From Completed Requests (Preferred)**

```python
current_rps = rate(vllm:request_success_total[1m])
```

**Method 2: From Concurrent Requests and E2E**

```python
# Little's Law: N = λ × W
# Where N = concurrent requests, λ = arrival rate (RPS), W = service time (E2E)
current_rps = num_requests_running / avg_e2e_latency
```

**Method 3: From Token Throughput**

```python
# If you know average tokens per request
total_tokens_per_request = avg_input_tokens + avg_output_tokens
current_rps = (PPS + GPS) / total_tokens_per_request
```

### Real-Time Monitoring Query Examples

```promql
# Current RPS
rate(vllm:request_success_total[1m])

# Average input tokens per request (5min window)
rate(vllm:prompt_tokens_total[5m]) / rate(vllm:request_success_total[5m])

# Average output tokens per request (5min window)
rate(vllm:generation_tokens_total[5m]) / rate(vllm:request_success_total[5m])

# Current concurrency
vllm:num_requests_running

# KV cache utilization
vllm:kv_cache_usage_perc

# Queue depth
vllm:num_requests_waiting
```

## 2. Predicting Maximal RPS from Lower Utilization Metrics

### The Capacity Prediction Model

Based on our H100 analysis, we can predict maximal capacity using metrics at lower utilization.

#### Key Relationships Discovered

1. **KV Cache vs Concurrency**: Nearly linear until saturation
   ```
   N ≈ (KV_cache_pct / 100) × N_max_at_saturation
   ```

2. **Concurrency vs RPS**: Related by E2E latency
   ```
   RPS = N / E2E
   ```

3. **GPS and ITL Relationship**: Indicates concurrent generation
   ```
   N_generating ≈ GPS × ITL
   ```

#### Prediction Algorithm

**Step 1: Measure Current State at 60% KV Cache**

```python
# Current metrics at ~60% KV cache utilization
current_kv_pct = 0.60  # 60%
current_N = vllm:num_requests_running  # e.g., 30
current_E2E = avg(vllm:e2e_request_latency_seconds)  # e.g., 5.0s
current_RPS = rate(vllm:request_success_total[1m])  # e.g., 6.0
```

**Step 2: Estimate N_max at 80% Saturation Threshold**

```python
# Linear extrapolation (conservative)
saturation_threshold = 0.80
N_max_80pct = current_N × (saturation_threshold / current_kv_pct)

# Example: 30 × (0.80 / 0.60) = 40 concurrent requests
```

**Step 3: Estimate E2E at Higher Load**

From our data, E2E increases with load. Use a conservative factor:

```python
# E2E typically increases 10-30% from 60% to 80% utilization
# Use 20% as conservative estimate
load_factor = 1.20
E2E_at_80pct = current_E2E × load_factor

# Example: 5.0s × 1.20 = 6.0s
```

**Step 4: Calculate Max RPS**

```python
max_RPS_at_80pct = N_max_80pct / E2E_at_80pct

# Example: 40 / 6.0 = 6.67 RPS
```

#### Validation with Our Data

Let's validate with 5000in/300out workload:

**At 36% KV cache (actual data):**
- N = 26, E2E = 8.792s, RPS = 2.0

**Prediction for 80% KV cache:**
- N_max = 26 × (0.80 / 0.36) = 57.8 ≈ 58
- E2E_est = 8.792 × 1.20 = 10.55s
- Max RPS = 58 / 10.55 = 5.5 RPS

**Actual at 80% KV cache:**
- N = 58, E2E = 24.184s, RPS = 2.0

**Analysis**: Our N_max prediction is accurate (58), but E2E prediction is too optimistic. The actual E2E increased much more (2.75x instead of 1.2x). This suggests we should use a more conservative factor.

#### Improved Prediction Model

```python
def predict_max_capacity(current_kv_pct, current_N, current_E2E, current_RPS):
    """
    Predict maximum capacity at 80% KV cache utilization.
    
    Args:
        current_kv_pct: Current KV cache utilization (0.0-1.0)
        current_N: Current concurrent requests
        current_E2E: Current E2E latency (seconds)
        current_RPS: Current requests per second
    
    Returns:
        dict with predicted N_max, E2E_max, and RPS_max
    """
    saturation_threshold = 0.80
    
    # Predict N_max (linear extrapolation)
    N_max = current_N * (saturation_threshold / current_kv_pct)
    
    # Predict E2E increase (non-linear, conservative)
    # Use quadratic model based on utilization increase
    util_ratio = saturation_threshold / current_kv_pct
    if util_ratio < 1.5:
        # Small increase: linear
        E2E_factor = 1.0 + 0.2 * (util_ratio - 1.0)
    else:
        # Large increase: quadratic
        E2E_factor = 1.0 + 0.5 * (util_ratio - 1.0) ** 1.5
    
    E2E_max = current_E2E * E2E_factor
    
    # Calculate max RPS
    RPS_max = N_max / E2E_max
    
    # Safety margin: reduce by 10% for production
    RPS_max_safe = RPS_max * 0.9
    
    return {
        'N_max': N_max,
        'E2E_max': E2E_max,
        'RPS_max_theoretical': RPS_max,
        'RPS_max_safe': RPS_max_safe,
        'headroom_pct': ((RPS_max_safe / current_RPS) - 1.0) * 100
    }

# Example usage
result = predict_max_capacity(
    current_kv_pct=0.60,
    current_N=30,
    current_E2E=5.0,
    current_RPS=6.0
)

print(f"Predicted N_max: {result['N_max']:.0f}")
print(f"Predicted E2E at max: {result['E2E_max']:.2f}s")
print(f"Predicted max RPS (safe): {result['RPS_max_safe']:.2f}")
print(f"Current headroom: {result['headroom_pct']:.1f}%")
```

## 3. Autoscaling Decision Framework

### When to Scale Out

#### Primary Trigger: KV Cache Utilization

```python
# Scale-out thresholds
SCALE_OUT_URGENT = 0.75      # 75% - scale immediately
SCALE_OUT_PROACTIVE = 0.65   # 65% - scale proactively
SCALE_OUT_PREDICTIVE = 0.55  # 55% - scale if trend is increasing

def should_scale_out(metrics, trend_window='5m'):
    """
    Determine if scale-out is needed.
    
    Args:
        metrics: Current vLLM metrics
        trend_window: Time window for trend analysis
    
    Returns:
        tuple: (should_scale, urgency, reason)
    """
    kv_cache_pct = metrics['kv_cache_usage_perc']
    queue_depth = metrics['num_requests_waiting']
    
    # Urgent: High utilization or queue building
    if kv_cache_pct >= SCALE_OUT_URGENT:
        return (True, 'urgent', f'KV cache at {kv_cache_pct*100:.1f}%')
    
    if queue_depth > 10:
        return (True, 'urgent', f'Queue depth: {queue_depth}')
    
    # Proactive: Approaching saturation
    if kv_cache_pct >= SCALE_OUT_PROACTIVE:
        return (True, 'proactive', f'KV cache at {kv_cache_pct*100:.1f}%')
    
    # Predictive: Trend analysis
    if kv_cache_pct >= SCALE_OUT_PREDICTIVE:
        kv_trend = calculate_trend(metrics, 'kv_cache_usage_perc', trend_window)
        if kv_trend > 0.05:  # Increasing by >5% per minute
            return (True, 'predictive', f'KV cache trending up: {kv_trend*100:.1f}%/min')
    
    return (False, 'none', 'Within safe operating range')
```

#### Secondary Triggers

```python
# Additional scale-out conditions
def check_secondary_triggers(metrics):
    """Check secondary scaling triggers."""
    triggers = []
    
    # Latency degradation
    p95_latency = metrics['e2e_latency_p95']
    p50_latency = metrics['e2e_latency_p50']
    if p95_latency > p50_latency * 2.0:
        triggers.append('latency_degradation')
    
    # Queue building
    if metrics['num_requests_waiting'] > 5:
        triggers.append('queue_building')
    
    # High concurrency relative to historical baseline
    if metrics['num_requests_running'] > metrics['baseline_N'] * 0.9:
        triggers.append('high_concurrency')
    
    return triggers
```

### How Many Instances to Create

#### Method 1: Capacity-Based Calculation

```python
def calculate_required_instances(current_metrics, target_rps, workload_profile):
    """
    Calculate number of instances needed for target RPS.
    
    Args:
        current_metrics: Current vLLM metrics from one instance
        target_rps: Desired total RPS capacity
        workload_profile: Dict with avg_input_tokens, avg_output_tokens
    
    Returns:
        dict with scaling recommendation
    """
    # Get current capacity
    current_rps = current_metrics['rps']
    current_kv_pct = current_metrics['kv_cache_usage_perc']
    
    # Predict max capacity per instance
    capacity_pred = predict_max_capacity(
        current_kv_pct,
        current_metrics['num_requests_running'],
        current_metrics['e2e_latency_avg'],
        current_rps
    )
    
    max_rps_per_instance = capacity_pred['RPS_max_safe']
    
    # Calculate required instances
    required_instances = math.ceil(target_rps / max_rps_per_instance)
    
    # Add buffer for redundancy (N+1)
    recommended_instances = required_instances + 1
    
    return {
        'current_instances': 1,
        'required_instances': required_instances,
        'recommended_instances': recommended_instances,
        'instances_to_add': recommended_instances - 1,
        'capacity_per_instance': max_rps_per_instance,
        'total_capacity': recommended_instances * max_rps_per_instance,
        'utilization_at_target': target_rps / (recommended_instances * max_rps_per_instance)
    }
```

#### Method 2: Utilization-Based Scaling

```python
def calculate_scale_out_count(current_kv_pct, target_kv_pct=0.60):
    """
    Calculate how many instances to add based on current utilization.
    
    Args:
        current_kv_pct: Current KV cache utilization (0.0-1.0)
        target_kv_pct: Target utilization after scaling (default: 60%)
    
    Returns:
        Number of instances to add
    """
    if current_kv_pct <= target_kv_pct:
        return 0
    
    # Calculate load distribution
    # If we have 1 instance at 80%, we need 80/60 = 1.33 instances
    # So add 1 instance (ceil(1.33) - 1 = 1)
    required_instances = math.ceil(current_kv_pct / target_kv_pct)
    instances_to_add = required_instances - 1
    
    return max(1, instances_to_add)  # Add at least 1

# Example
current_kv = 0.75  # 75%
instances_to_add = calculate_scale_out_count(current_kv, target_kv_pct=0.60)
print(f"Add {instances_to_add} instance(s)")  # Output: Add 1 instance(s)
# New utilization: 75% / 2 = 37.5%
```

#### Method 3: Workload-Specific Scaling

```python
def workload_specific_scaling(workload_profile, current_metrics):
    """
    Scale based on workload characteristics from our H100 analysis.
    
    Args:
        workload_profile: Dict with avg_input_tokens, avg_output_tokens
        current_metrics: Current vLLM metrics
    
    Returns:
        Scaling recommendation
    """
    in_tok = workload_profile['avg_input_tokens']
    out_tok = workload_profile['avg_output_tokens']
    
    # Lookup table from our analysis (N_max at 80% KV cache)
    capacity_table = {
        (1000, 300): {'N_max': 6, 'max_rps': 2.0},
        (3000, 300): {'N_max': 64, 'max_rps': 7.0},
        (5000, 300): {'N_max': 49, 'max_rps': 4.0},
        (5000, 600): {'N_max': 26, 'max_rps': 2.0},
        (5000, 1200): {'N_max': 58, 'max_rps': 2.0},
        # ... more entries from analysis
    }
    
    # Find closest match
    closest_key = min(
        capacity_table.keys(),
        key=lambda k: abs(k[0] - in_tok) + abs(k[1] - out_tok)
    )
    
    capacity = capacity_table[closest_key]
    
    # Calculate scaling
    current_rps = current_metrics['rps']
    target_rps = current_rps * 1.5  # 50% headroom
    
    required_instances = math.ceil(target_rps / capacity['max_rps'])
    
    return {
        'workload_match': closest_key,
        'capacity_per_instance': capacity['max_rps'],
        'required_instances': required_instances,
        'instances_to_add': max(0, required_instances - 1)
    }
```

### Complete Autoscaling Algorithm

```python
class VLLMAutoscaler:
    def __init__(self, config):
        self.scale_out_threshold = config.get('scale_out_threshold', 0.65)
        self.scale_in_threshold = config.get('scale_in_threshold', 0.40)
        self.target_utilization = config.get('target_utilization', 0.60)
        self.min_instances = config.get('min_instances', 1)
        self.max_instances = config.get('max_instances', 10)
        self.cooldown_period = config.get('cooldown_period', 300)  # 5 minutes
        
    def make_scaling_decision(self, metrics, workload_profile):
        """
        Main autoscaling decision logic.
        
        Returns:
            dict: Scaling action and details
        """
        current_instances = metrics['current_instances']
        kv_cache_pct = metrics['kv_cache_usage_perc']
        
        # Check cooldown
        if self._in_cooldown():
            return {'action': 'none', 'reason': 'cooldown_period'}
        
        # Scale out decision
        if kv_cache_pct >= self.scale_out_threshold:
            instances_to_add = calculate_scale_out_count(
                kv_cache_pct,
                self.target_utilization
            )
            
            new_total = min(
                current_instances + instances_to_add,
                self.max_instances
            )
            
            return {
                'action': 'scale_out',
                'current_instances': current_instances,
                'target_instances': new_total,
                'instances_to_add': new_total - current_instances,
                'reason': f'KV cache at {kv_cache_pct*100:.1f}%',
                'urgency': 'high' if kv_cache_pct >= 0.75 else 'normal'
            }
        
        # Scale in decision
        if kv_cache_pct <= self.scale_in_threshold and current_instances > self.min_instances:
            # Conservative scale-in: remove 1 instance at a time
            # Check if we can maintain target utilization
            projected_kv = kv_cache_pct * (current_instances / (current_instances - 1))
            
            if projected_kv <= self.target_utilization:
                return {
                    'action': 'scale_in',
                    'current_instances': current_instances,
                    'target_instances': current_instances - 1,
                    'instances_to_remove': 1,
                    'reason': f'KV cache at {kv_cache_pct*100:.1f}%',
                    'projected_utilization': projected_kv
                }
        
        return {
            'action': 'none',
            'reason': 'within_target_range',
            'current_utilization': kv_cache_pct
        }
```

### Monitoring Dashboard Queries

```promql
# Current KV cache utilization (scale-out trigger)
vllm:kv_cache_usage_perc > 0.65

# Predicted time to saturation (minutes)
(0.80 - vllm:kv_cache_usage_perc) / 
  deriv(vllm:kv_cache_usage_perc[5m]) / 60

# Current capacity utilization (%)
(rate(vllm:request_success_total[1m]) / 
  <max_rps_from_analysis>) * 100

# Queue depth alert
vllm:num_requests_waiting > 5

# Latency degradation alert
histogram_quantile(0.95, vllm:e2e_request_latency_seconds) > 
  histogram_quantile(0.50, vllm:e2e_request_latency_seconds) * 2
```

## Summary: Practical Autoscaling Rules

### Rule 1: Scale Out When
- KV cache ≥ 65% (proactive)
- KV cache ≥ 75% (urgent)
- Queue depth > 5 requests
- P95 latency > 2× P50 latency

### Rule 2: Number of Instances to Add
- **Conservative**: Add 1 instance at a time
- **Aggressive**: `ceil(current_kv / target_kv) - current_instances`
- **Workload-based**: Use capacity table from analysis

### Rule 3: Scale In When
- KV cache ≤ 40% for > 10 minutes
- Projected utilization after scale-in ≤ 60%
- Remove 1 instance at a time (conservative)

### Rule 4: Safety Margins
- Always maintain N+1 redundancy
- Keep 10-20% capacity headroom
- Use 5-minute cooldown between scaling actions
- Never scale below min_instances (typically 1-2)

### Rule 5: Workload-Aware Scaling
- Monitor avg input/output tokens
- Use workload-specific capacity estimates
- Adjust thresholds for long-context workloads (lower threshold)