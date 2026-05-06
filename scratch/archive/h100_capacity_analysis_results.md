# H100 vLLM Capacity Analysis Results

## Executive Summary

This analysis estimates the maximal concurrency (N_max) and maximal RPS for different workload types on an H100 GPU running vLLM, based on KV cache utilization and measured performance metrics.

**Key Finding**: KV cache utilization above 80% indicates saturation. The analysis identifies stable operating points below this threshold.

## Methodology

1. **N_max Estimation**: The maximal concurrency is determined by finding the highest RPS point where KV cache utilization remains ≤80% (stable operation).

2. **Max RPS Estimation**: 
   - Theoretical: `N_max / E2E(N_max)`
   - Observed: The actual RPS measured at the N_max point

3. **Validation**: The formula `N ≈ GPS * ITL + Prefill / ITL` provides an independent estimate of concurrent requests.

## Detailed Results by Workload Type

### 1. Fixed Output Length (300 tokens), Varying Input Length

#### 1000 Input Tokens, 300 Output Tokens
- **N_max**: 6 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 2.052s
- **KV Cache at N_max**: 2.0%
- **Status**: Well below saturation, could handle more load

#### 3000 Input Tokens, 300 Output Tokens
- **N_max**: 64 concurrent requests
- **Max RPS**: 7.0 req/s
- **E2E Latency at N_max**: 7.264s
- **KV Cache at N_max**: 51.0%
- **Status**: Stable operation with good headroom

#### 5000 Input Tokens, 300 Output Tokens
- **N_max**: 49 concurrent requests
- **Max RPS**: 4.0 req/s
- **E2E Latency at N_max**: 8.156s
- **KV Cache at N_max**: 66.0%
- **Status**: Stable, approaching saturation at higher RPS
- **At Saturation (RPS=5.0)**: KV cache hits 100%, E2E increases to 14.908s

#### 7000 Input Tokens, 300 Output Tokens
- **N_max**: 14 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 4.318s
- **KV Cache at N_max**: 26.0%
- **Status**: Stable with good headroom

#### 9000 Input Tokens, 300 Output Tokens
- **N_max**: 25 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 7.512s
- **KV Cache at N_max**: 60.0%
- **Status**: Stable operation

#### 11000 Input Tokens, 300 Output Tokens
- **N_max**: 34 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 16.480s
- **KV Cache at N_max**: 99.0%
- **Status**: ⚠️ At saturation limit

### 2. Fixed Input Length (5000 tokens), Varying Output Length

#### 5000 Input, 100 Output Tokens
- **N_max**: 7 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 1.151s
- **KV Cache at N_max**: 9.0%
- **Status**: Well below saturation

#### 5000 Input, 200 Output Tokens
- **N_max**: 10 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 2.072s
- **KV Cache at N_max**: 13.0%
- **Status**: Well below saturation

#### 5000 Input, 300 Output Tokens
- **N_max**: 49 concurrent requests (at RPS=4.0)
- **Max RPS**: 4.0 req/s
- **E2E Latency at N_max**: 8.156s
- **KV Cache at N_max**: 66.0%
- **Status**: Stable operation

#### 5000 Input, 400 Output Tokens
- **N_max**: 16 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 4.936s
- **KV Cache at N_max**: 22.0%
- **Status**: Stable with good headroom

#### 5000 Input, 500 Output Tokens
- **N_max**: 25 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 7.182s
- **KV Cache at N_max**: 35.0%
- **Status**: Stable operation

#### 5000 Input, 600 Output Tokens
- **N_max**: 26 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 8.792s
- **KV Cache at N_max**: 36.0%
- **Status**: Stable operation

#### 5000 Input, 700 Output Tokens
- **N_max**: 45 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 11.090s
- **KV Cache at N_max**: 60.0%
- **Status**: Stable operation

#### 5000 Input, 800 Output Tokens
- **N_max**: 45 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 12.531s
- **KV Cache at N_max**: 60.0%
- **Status**: Stable operation

#### 5000 Input, 900 Output Tokens
- **N_max**: 45 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 16.762s
- **KV Cache at N_max**: 60.0%
- **Status**: Stable operation

#### 5000 Input, 1000 Output Tokens
- **N_max**: 51 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 19.400s
- **KV Cache at N_max**: 70.0%
- **Status**: Approaching saturation

#### 5000 Input, 1100 Output Tokens
- **N_max**: 50 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 23.159s
- **KV Cache at N_max**: 70.0%
- **Status**: Approaching saturation

#### 5000 Input, 1200 Output Tokens
- **N_max**: 58 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 24.184s
- **KV Cache at N_max**: 80.0%
- **Status**: At saturation threshold

#### 5000 Input, 1300 Output Tokens
- **N_max**: 58 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 27.416s
- **KV Cache at N_max**: 81.0%
- **Status**: ⚠️ Slightly over saturation threshold

#### 5000 Input, 1400 Output Tokens
- **N_max**: 67 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 35.469s
- **KV Cache at N_max**: 98.0%
- **Status**: ⚠️ At saturation limit

#### 5000 Input, 1500-1800 Output Tokens
- **N_max**: 66-69 concurrent requests
- **Max RPS**: 2.0 req/s
- **E2E Latency at N_max**: 40-47s
- **KV Cache at N_max**: 98-100%
- **Status**: ⚠️ At/beyond saturation limit

## Key Insights

### 1. Throughput vs Concurrency Trade-offs

| Workload Type | N_max | Max RPS | KV Cache % | Notes |
|---------------|-------|---------|------------|-------|
| 3000in/300out | 64 | 7.0 | 51% | **Highest throughput** |
| 5000in/300out | 49 | 4.0 | 66% | Good balance |
| 5000in/1200out | 58 | 2.0 | 80% | At saturation threshold |
| 5000in/1800out | 67 | 2.0 | 98% | **Highest concurrency** but saturated |

### 2. Impact of Input Length (Fixed 300 Output Tokens)

- **1000 tokens**: Very low utilization (2%), could handle much more
- **3000 tokens**: Optimal sweet spot - high RPS (7.0) with moderate KV cache (51%)
- **5000 tokens**: Good performance (4.0 RPS) at 66% KV cache
- **7000-9000 tokens**: Lower RPS (2.0) but stable
- **11000 tokens**: At saturation limit (99% KV cache)

**Pattern**: Longer inputs increase KV cache usage proportionally, reducing max RPS but allowing reasonable concurrency.

### 3. Impact of Output Length (Fixed 5000 Input Tokens)

- **100-600 tokens**: Low KV cache usage (9-36%), could handle more load
- **700-1100 tokens**: Moderate usage (60-70%), stable operation
- **1200 tokens**: At threshold (80% KV cache)
- **1300+ tokens**: Beyond saturation (81-100% KV cache)

**Pattern**: Output length has a strong impact on KV cache. Beyond ~1200 output tokens with 5000 input tokens, the system saturates.

### 4. Saturation Behavior

When KV cache exceeds 80%:
- E2E latency increases significantly (e.g., 8.156s → 14.908s for 5000in/300out)
- System becomes unstable
- Requests may start queuing

### 5. Capacity Planning Recommendations

For **stable operation** (KV cache ≤ 80%):

| Input Tokens | Output Tokens | Recommended N_max | Recommended Max RPS |
|--------------|---------------|-------------------|---------------------|
| 1000 | 300 | 6 | 2.0 |
| 3000 | 300 | 64 | 7.0 |
| 5000 | 100-300 | 10-49 | 2.0-4.0 |
| 5000 | 400-900 | 16-45 | 2.0 |
| 5000 | 1000-1200 | 50-58 | 2.0 |
| 7000 | 300 | 14 | 2.0 |
| 9000 | 300 | 25 | 2.0 |

**Critical Threshold**: For 5000 input tokens, output length should not exceed ~1200 tokens to maintain stable operation.

## Formulas and Validation

### Concurrency Estimation
The formula `N ≈ GPS * ITL + Prefill / ITL` provides a good estimate:
- For 5000in/300out at RPS=4.0: Estimated N = 42.8, Actual MaxRun = 49 (good match)
- For 5000in/1700out: Estimated N = 62.9, Actual MaxRun = 66 (good match)

### Max RPS Calculation
- **Theoretical**: `Max RPS = N_max / E2E(N_max)`
- **Observed**: Actual measured RPS at the N_max point
- The observed RPS is often lower than theoretical due to system overhead and batching effects

## Conclusions

1. **KV cache is the primary bottleneck** for this H100 configuration with 65K block size
2. **Optimal workload**: 3000 input / 300 output tokens achieves highest throughput (7.0 RPS)
3. **Concurrency limits**: Range from 6 to 67 depending on token counts
4. **Safe operating zone**: Keep KV cache utilization below 80% for stable performance
5. **Long context penalty**: Workloads with >1200 output tokens (at 5000 input) saturate the KV cache

## Recommendations for Autoscaling

1. **Monitor KV cache utilization** as the primary scaling signal
2. **Set scaling threshold at 70-75%** KV cache to maintain headroom
3. **Use workload-specific N_max values** for capacity planning
4. **Consider request routing** to separate short and long context requests
5. **Scale out before reaching 80%** KV cache utilization to avoid latency spikes