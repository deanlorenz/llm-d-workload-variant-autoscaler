# vLLM Performance Analysis Methodology

## Overview

This document describes the complete methodology used to analyze vLLM performance data, detect saturation points, and estimate instance requirements. The analysis is based on the theoretical framework from the technical discussion about vLLM performance bottlenecks.

---

## 1. Data Loading and Preparation

### Input Data
The analysis expects a CSV file with the following columns:
- **IL** (In-Tok): Input length in tokens
- **OL** (Out-Tok): Output length in tokens
- **RPS**: Requests per second (load)
- **test-name**: Experiment identifier
- **TTFT**: Time to first token (prefill time including wait)
- **ITL**: Inter-token latency (decode time per token)
- **E2E**: End-to-end latency (total request time)
- **Kvcache**: KV cache utilization (0-1)
- **MaxKvcache**: Maximum KV cache utilization observed (0-1)

### Data Cleaning
1. Remove BOM characters from column names
2. Convert numeric columns to float
3. Remove rows with missing critical metrics
4. Segment data by `test-name` for per-experiment analysis

---

## 2. Derived Metrics Computation

For each measurement, we compute:

### φ (Phi) - Queueing Indicator
```
φ = E2E / (OL × ITL)
```
- **Interpretation**: Ratio of actual E2E to ideal decode time
- **Threshold**: φ > 1.1 indicates queueing (requests waiting)
- **Ideal value**: φ ≈ 1.0 (no queueing)

### ρ (Rho) - Prefill Pressure Indicator
```
ρ = TTFT / ITL
```
- **Interpretation**: Ratio of prefill time to decode time per token
- **Usage**: Compared to √OL to determine performance regime
- **High ρ**: Prefill-dominated workload

### T_prefill - Actual Prefill Time
```
T_prefill = TTFT - ITL
```
- **Interpretation**: Pure prefill computation time (excluding first token decode)
- **Depends on**: Input length (IL) and KV cache pressure

### N - Concurrent Requests
```
N = RPS × E2E  (Little's Law)
```
- **Interpretation**: Average number of requests in the system
- **Usage**: Estimate KV cache occupancy

---

## 3. KV Cache Analysis

### 3.1 KV Cache Saturation Detection

Two indicators of KV cache saturation:

1. **High KV Utilization**: `Kvcache > 0.8`
   - System approaching KV cache capacity
   - Decode performance may degrade

2. **KV Cache Ceiling**: `MaxKvcache > 0.95`
   - System hitting KV cache limit
   - Clear sign of decode-limited saturation

### 3.2 KV Cache Size Estimation

We estimate total KV cache capacity from non-saturated measurements:

```
k = (N × tokens_per_request) / KV_total

Where:
- k = Kvcache (measured)
- N = concurrent requests
- tokens_per_request ≈ IL + OL/2
  (IL for prefill + average OL/2 for decode in progress)

Rearranging:
KV_total = (N × (IL + OL/2)) / k
```

**Method**:
1. Use only non-saturated points (k < 0.8)
2. Compute KV_total estimate for each point
3. Take median to reduce outlier impact
4. Confidence = 1 - coefficient_of_variation

**Typical values**: 400K-500K tokens for the analyzed systems

---

## 4. Performance Extrapolation

### 4.1 ITL(k) Extrapolation

Estimate ITL at k=0.8 using linear regression on non-saturated data:

```
ITL(k) = a + b×k
```

**Method**:
1. Filter non-saturated points: φ < 1.1 AND k < 0.8
2. Fit linear model using least squares
3. Extrapolate to k=0.8
4. Compute R² as confidence metric

**Why linear?**: Empirical observation shows ITL increases approximately linearly with k in the non-saturated regime.

### 4.2 T_prefill(k) Extrapolation

Similar approach for prefill time:

```
T_prefill(k) = a + b×k
```

**Method**: Same as ITL(k)

**Note**: T_prefill may show more variability (lower R²) in experiments with varying output lengths.

---

## 5. Derivative Computation

To detect service rate collapse, we compute derivatives:

### g = d(ITL)/dλ
Rate of ITL increase with load (λ = RPS)

**Method**: Centered differences
```
g[i] = (ITL[i+1] - ITL[i-1]) / (RPS[i+1] - RPS[i-1])
```

### h = dρ/dλ
Rate of prefill pressure increase with load

**Method**: Same as g

### Acceleration
Second derivatives to detect convexity:
```
g_accel[i] = g[i] - g[i-1]
h_accel[i] = h[i] - h[i-1]
```

---

## 6. Saturation Detection

### 6.1 Four Saturation Conditions

**Condition 1: Service Degradation**
```
g > 0 AND g_acceleration > 0
```
- ITL increasing with load
- Rate of increase accelerating (convexity)
- Indicates service rate collapse

**Condition 2: Prefill Interference**
```
h > 0 AND h_acceleration > 0
```
- Prefill pressure increasing with load
- Rate of increase accelerating
- Indicates prefill stealing decode cycles

**Condition 3: Queueing Onset**
```
φ > 1.1
```
- Requests waiting in queue
- E2E exceeds ideal decode time by >10%

**Condition 4: KV Cache Saturation**
```
Kvcache > 0.8 OR MaxKvcache > 0.95
```
- Approaching or hitting KV cache limit
- Decode-limited saturation

### 6.2 Saturation Types

**Prefill-Induced Saturation**:
- Conditions 1, 2, AND 3 all met
- Typical for short-output workloads
- Service rate collapse due to prefill interference

**KV Cache Ceiling**:
- Condition 4 met
- Typical for long-output or high-concurrency workloads
- Traditional decode-limited saturation

**Overall Saturation**:
```
is_saturated = prefill_saturated OR kv_saturated
```

---

## 7. Regime Classification

Based on ρ/√OL ratio:

```
rho_ratio = ρ / √OL
```

**Decode-Limited**: `rho_ratio < 0.5`
- Long output, high k
- KV cache capacity is the bottleneck
- Traditional saturation mechanism

**Scheduler-Limited**: `0.5 ≤ rho_ratio ≤ 2.0`
- Short output, transition zone
- Prefill-decode interference
- √OL scaling applies

**Prefill-Limited**: `rho_ratio > 2.0`
- Large input dominates
- Prefill time >> decode time
- Input processing is bottleneck

---

## 8. Maximum Sustainable RPS

### Definition
The **last non-saturated RPS value** before any saturation condition is met.

### Method
1. Sort measurements by RPS
2. Find first saturated point (is_saturated = True)
3. Max sustainable RPS = RPS at (first_saturated_index - 1)
4. If no saturation detected, use maximum observed RPS

### Saturation Type Identification
- If `cond4_kv_saturation` triggered: "KV cache ceiling"
- If `prefill_saturated` triggered: "Prefill-induced"
- Otherwise: "Unknown"

---

## 9. Instance Estimation

### 9.1 Core Logic

For a target workload (target_IL, target_OL, target_RPS):

```python
if target_RPS <= max_sustainable_rps:
    instances_needed = 1
else:
    instances_needed = ceil(target_RPS / max_sustainable_rps)

total_capacity = instances_needed × max_sustainable_rps
utilization = (target_RPS / total_capacity) × 100%
```

### 9.2 Configuration Matching

**Valid Estimates**: Only when `target_IL == experiment_IL AND target_OL == experiment_OL`

**Invalid Estimates**: When IL or OL differ
- Marked with `valid = False`
- Warning: "Different IL/OL - estimate assumes same performance characteristics"
- Use with caution - actual performance may differ

### 9.3 Assumptions

1. **Linear Scaling**: Instances scale linearly without coordination overhead
2. **Independent Instances**: No shared resources between instances
3. **Same Configuration**: Target workload matches experiment characteristics
4. **Homogeneous Hardware**: All instances have identical capacity

### 9.4 Scenario Generation

For each experiment, we generate estimates for:

**Scenario 1: Vary RPS** (VALID)
- Keep IL, OL constant
- Test RPS at: 0.5×, 1.0×, 1.5×, 2.0×, 3.0×, 5.0× max_sustainable_rps
- These estimates are reliable

**Scenario 2: Vary OL** (INVALID - for reference only)
- Keep IL, RPS constant
- Test OL at: 0.5×, 1.0×, 1.5×, 2.0× experiment_OL
- Estimates may not be accurate

**Scenario 3: Vary IL** (INVALID - for reference only)
- Keep OL, RPS constant
- Test IL at: 0.5×, 1.0×, 1.5×, 2.0× experiment_IL
- Estimates may not be accurate

---

## 10. Output Files

### 10.1 analysis_summary_v2.csv
Summary metrics for all experiments:
- Configuration (IL, OL)
- Max sustainable RPS
- Saturation point and type
- Extrapolated metrics (ITL, T_prefill at k=0.8)
- KV cache estimates
- Regime distribution
- Saturation counts

### 10.2 analysis_v2_<test_name>.csv
Detailed per-measurement metrics:
- All input metrics
- Derived metrics (φ, ρ, T_prefill, N)
- KV saturation flags
- Derivatives (g, h) and accelerations
- Saturation conditions (cond1-4)
- Regime classification
- Overall saturation flag

### 10.3 instance_estimates_v2.csv
Instance requirements for various scenarios:
- Target configuration (IL, OL, RPS)
- Experiment configuration
- Config match flag
- Max sustainable RPS
- Instances needed
- Total capacity
- Utilization percentage
- Validity flag and warnings

---

## 11. Key Formulas Reference

### Little's Law
```
N = λ × E2E
Where: N = concurrent requests, λ = RPS, E2E = latency
```

### Queueing Indicator
```
φ = E2E / (OL × ITL)
φ > 1.1 → queueing present
```

### Prefill Pressure
```
ρ = TTFT / ITL
Compare to √OL for regime classification
```

### Service Rate
```
μ = 1 / ITL  (tokens per second per request)
System capacity ≈ μ / OL  (requests per second)
```

### KV Cache Occupancy
```
k ≈ (N × (IL + OL/2)) / KV_total
```

### Stability Boundary (Prefill-Induced)
```
λ_max ≈ 1 / (√OL × T_prefill)
For short-output workloads
```

---

## 12. Interpretation Guidelines

### 12.1 High Confidence Indicators

**Good Extrapolation** (R² > 0.95):
- ITL(k) prediction reliable
- Can trust max sustainable RPS estimate

**High KV Confidence** (> 0.9):
- KV cache size estimate reliable
- Can predict decode-limited saturation

**Clear Saturation Signal**:
- All conditions met simultaneously
- Sharp transition in metrics
- Reliable saturation point

### 12.2 Low Confidence Indicators

**Poor Extrapolation** (R² < 0.7):
- High variability in measurements
- May need more data points
- Use estimates with caution

**Low KV Confidence** (< 0.7):
- Variable KV cache usage
- May have workload heterogeneity
- KV size estimate uncertain

**No Saturation Detected**:
- Max RPS = highest observed
- May be able to handle more load
- Conservative estimate

### 12.3 Saturation Type Implications

**KV Cache Ceiling** (most common):
- Decode-limited regime
- Need more KV cache capacity
- Or reduce concurrent requests (lower RPS)
- Or reduce output length

**Prefill-Induced** (rare, short outputs):
- Scheduler-limited regime
- Need better prefill-decode scheduling
- Or batch prefills separately
- Or reduce input length

---

## 13. Limitations and Caveats

### 13.1 Extrapolation Limits
- Linear models may not hold at extreme k values
- Predictions beyond k=0.8 increasingly uncertain
- Non-linear effects may emerge near saturation

### 13.2 Instance Scaling
- Assumes perfect linear scaling
- Real systems may have:
  - Load balancer overhead
  - Network latency
  - Coordination costs
- Add 10-20% safety margin in production

### 13.3 Workload Assumptions
- Assumes homogeneous workload (same IL, OL)
- Real workloads have distribution of IL, OL
- Use representative percentiles (p50, p95)

### 13.4 Hardware Differences
- Analysis specific to tested hardware
- Different GPUs may have different:
  - KV cache capacity
  - Compute throughput
  - Memory bandwidth
- Re-run analysis for different hardware

---

## 14. Best Practices

### 14.1 Data Collection
- Test multiple RPS values around expected saturation
- Include points both below and above saturation
- Ensure measurements reach steady state
- Collect at least 10-15 data points per experiment

### 14.2 Analysis
- Always check R² values for extrapolations
- Verify saturation type makes sense for workload
- Compare multiple experiments for consistency
- Look for outliers and investigate causes

### 14.3 Capacity Planning
- Use max sustainable RPS, not saturation RPS
- Add 20% safety margin for production
- Monitor actual φ, ρ metrics in production
- Re-analyze when workload characteristics change

### 14.4 Optimization
- For KV ceiling: Increase cache size or reduce OL
- For prefill saturation: Optimize scheduling or reduce IL
- Batch similar workloads together
- Consider chunked generation for long outputs

---

## 15. Example Walkthrough

### Experiment: 6K_100 (IL=6000, OL=100)

**Step 1: Load Data**
- 23 measurements from RPS=2.0 to RPS=6.8

**Step 2: Compute Derived Metrics**
- φ ranges from 1.18 to 1.66
- ρ ranges from 19.5 to 56.3
- N ranges from 2.6 to 16.6 concurrent requests

**Step 3: KV Analysis**
- Estimated KV_total = 467,657 tokens (confidence=0.83)
- 8 points with k > 0.8 (KV saturated)

**Step 4: Extrapolation**
- ITL(0.8) = 0.103 sec (R²=0.93)
- T_prefill(0.8) = 0.682 sec (R²=0.89)

**Step 5: Saturation Detection**
- First saturation at RPS=5.4
- Type: KV cache ceiling (k=0.85)
- Max sustainable RPS = 5.2

**Step 6: Regime Classification**
- Predominantly scheduler-limited (17/23 points)
- ρ/√OL ≈ 1.7 (in transition zone)

**Step 7: Instance Estimation**
- For 10 RPS: need 2 instances (5.2 × 2 = 10.4 capacity)
- For 15 RPS: need 3 instances (5.2 × 3 = 15.6 capacity)

**Interpretation**:
- Large input (6K) with short output (100) creates challenging workload
- KV cache fills quickly due to high IL
- System saturates at moderate RPS (5.2) due to KV ceiling
- Need multiple instances for higher loads

---

## Conclusion

This methodology provides a rigorous, data-driven approach to:
1. Detect saturation in vLLM systems
2. Understand performance bottlenecks
3. Estimate capacity requirements
4. Plan instance scaling

The analysis validates the theoretical framework and demonstrates that both prefill-induced and KV-cache-induced saturation mechanisms exist in real systems.