# Throughput Analyzer Design — Latency-Based Scaling with Learned E2E Model

## 1. Motivation

The saturation analyzers (K1/K2) detect capacity exhaustion reactively — they trigger scaling when KV cache or queue thresholds are breached. This works for preventing overload but cannot anticipate latency degradation that occurs *before* hard saturation.

The Throughput Analyzer models **end-to-end request latency** as a function of observable runtime metrics and uses the predicted latency to derive token-throughput-based supply and demand signals. The key insight: inter-token latency (ITL) is a **linear function** of KV cache utilization and the proportion of input to output tokens in the current workload mix. This relationship can be learned online from runtime metrics without offline profiling.

## 2. Notation

| Symbol | Description |
|--------|-------------|
| $v \in \mathcal{V}$ | Backend variant (GPU type, model config, quantization) |
| $w \in \mathcal{W}$ | Workload type (characterized by input/output length distribution) |
| $IL(w)$ | Expected input length in tokens for workload type $w$ |
| $OL(w)$ | Expected output length in tokens for workload type $w$ |
| $IL_{eff}(w)$ | Effective input length after KV cache hit adjustment: $IL_{eff} = IL \cdot (1 - H\%)$ |
| $H\%$ | KV cache (prefix) hit rate — fraction of input tokens served from cache |
| $KV\%(v)$ | Current KV cache utilization of variant $v$ (0.0–1.0) |
| $R(w)$ | Input-to-output token ratio: $R(w) = IL_{eff}(w) / OL(w)$ |
| $ITL(v)$ | Inter-token latency on variant $v$ (seconds per output token) |
| $P_{obs}(v)$ | Observed prefill computation time on variant $v$ (seconds), from `vllm:request_prefill_time_seconds` |
| $E2E(w,v)$ | End-to-end latency for workload $w$ on variant $v$ |
| $T_v^{max}$ | Maximum sustainable token throughput of a single replica of variant $v$ (tokens/sec) |
| $KV\%_{max}$ | Maximum allowable KV cache utilization (e.g., 0.9), operational ceiling |
| $ITL_{target}$ | Target inter-token latency from SLO or configuration (optional) |
| $P_{target}$ | Target prefill time from SLO or configuration (optional) |
| $\lambda_m$ | Request arrival rate for model $m$ (from inference scheduler) |

## 3. Effective Input Length and KV Cache Hit Rate

When prefix caching is enabled, a fraction of input tokens are served from the KV cache without recomputation. The **effective input length** adjusts for this:

$$
IL_{eff}(w) = IL(w) \cdot (1 - H\%)
$$

Where $H\%$ is the observed prefix cache hit rate from `vllm:prefix_cache_hit_rate` (0.0–1.0). At $H\% = 0$ (no caching), $IL_{eff} = IL$. At $H\% = 0.8$, only 20% of input tokens require prefill computation.

This adjustment propagates through the model:
- **Prefill time** is reduced (fewer tokens to process)
- **KV cache pressure** is reduced (cached tokens don't consume new KV blocks)
- **Input/output ratio** $R = IL_{eff} / OL$ reflects actual compute, not raw prompt size

## 4. E2E Latency Model

End-to-end latency decomposes into prefill and decode phases:

$$
E2E(w,v) = P_{obs}(v) + ITL(v) \cdot OL(w)
$$

### 4.1 Inter-Token Latency Model

ITL increases with KV cache pressure (more active sequences compete for memory bandwidth) and with longer effective input prompts (larger KV entries per sequence increase attention compute per decode step):

$$
ITL(v) = \alpha_v \cdot KV\%(v) + \beta_v \cdot R(w) + \gamma_v
$$

Where:
- $\alpha_v$ — sensitivity of ITL to KV cache utilization (memory bandwidth contention)
- $\beta_v$ — sensitivity of ITL to input/output ratio $R = IL_{eff}/OL$ (longer effective prompts → larger KV per sequence → slower attention)
- $\gamma_v$ — baseline ITL at zero load (hardware floor)

### 4.2 Prefill Time

Prefill time is **observed directly** from vLLM's prefill latency metric rather than modeled:

$$
P_{obs}(v) = \text{vllm:request\_prefill\_time\_seconds}
$$

This metric captures the actual prefill computation time — the GPU time spent processing input tokens before the first output token is generated. Unlike TTFT (which includes scheduling and queuing delays), prefill time isolates the compute cost and gives a cleaner signal for capacity modeling. Using the observed value avoids modeling prefill dynamics (which depend on chunked prefill strategies, batch scheduling, and prefix caching) and ensures accuracy across different vLLM configurations.

### 4.3 Combined Model

Substituting ITL into the E2E equation (with $R = IL_{eff} / OL$):

$$
E2E(w,v) = P_{obs}(v) + (\alpha_v \cdot KV\% + \beta_v \cdot \frac{IL_{eff}}{OL} + \gamma_v) \cdot OL
$$

The only learned component is the ITL model (3 parameters per variant). Prefill time, output length, and cache hit rate are observed directly.

## 5. Online Parameter Learning

### 5.1 Observable Metrics

All inputs are available from existing vLLM Prometheus metrics and llm-d inference scheduler telemetry:

**vLLM metrics (per pod):**

| Metric | Source | Description |
|--------|--------|-------------|
| $KV\%(v)$ | `vllm:kv_cache_usage_perc` | KV cache utilization per pod, aggregated per variant |
| $IL$, $OL$ | `vllm:request_prompt_tokens_sum/count`, `vllm:request_generation_tokens_sum/count` | Average input/output lengths via rate ratios |
| $H\%$ | `vllm:prefix_cache_hit_rate` | Prefix cache hit rate (0.0–1.0) |
| $P_{obs}(v)$ | `vllm:request_prefill_time_seconds` | Observed prefill computation time |
| $ITL_{obs}$ | `vllm:time_per_output_token_seconds` | Observed inter-token latency |

**llm-d inference scheduler metrics (per model):**

| Metric | Source | Description |
|--------|--------|-------------|
| $\lambda_m$ | `rate(inference_extension_request_total{model=m}[1m])` | Request arrival rate for model $m$ |
| $\bar{IL}_m$ | `inference_extension_input_tokens` (histogram) | Mean input tokens per request at the scheduler level |
| Queue depth | `inference_extension_flow_control_queue_size{model=m}` | Requests queued before routing to backends |

**Derived quantities:**

| Quantity | Derivation | Description |
|----------|-----------|-------------|
| $IL_{eff}$ | $IL \cdot (1 - H\%)$ | Effective input tokens after cache hit adjustment |
| $R(w)$ | $IL_{eff} / \bar{OL}$ | Effective input-to-output token ratio |
| $\bar{OL}$ | `rate(generation_tokens_sum) / rate(request_success_total)` per variant | Mean output tokens per request (from vLLM instance) |
| $D_m^{tokens}$ | $\lambda_m \cdot (\bar{IL}_{eff} + \bar{OL})$ | Total token demand for model (scheduler rate × mean tokens per request) |

### 5.2 Regression

For each variant $v$, maintain a running linear regression to fit $(\alpha_v, \beta_v, \gamma_v)$ from observations of $(KV\%, R, ITL_{observed})$.

Use **recursive least squares (RLS)** or **exponentially weighted moving average (EWMA) regression** for online updates. This avoids storing historical data and adapts to changing conditions (model warm-up, varying batch sizes).

The forgetting factor $\lambda \in (0, 1]$ controls the tradeoff between stability and responsiveness:
- $\lambda = 1.0$ — equal weight to all history (stable but slow to adapt)
- $\lambda = 0.95$ — exponential decay with ~20-sample effective window (responsive)

### 5.3 Parameter Store

```go
type ThroughputParameters struct {
    // ITL model: ITL = Alpha*KV% + Beta*R + Gamma
    Alpha float64
    Beta  float64
    Gamma float64

    // Regression state
    Covariance  [][]float64 // 3x3 covariance matrix for RLS
    LastUpdated time.Time
    SampleCount int64
}
```

Parameters are stored per variant and updated each reconciliation cycle when fresh metrics are available. A minimum sample count (e.g., 10) is required before the model is trusted for scaling decisions.

## 6. Supply and Demand (Total Token Throughput)

Supply and demand are expressed in **total tokens per second** (input + output) rather than requests per second. Total token throughput captures the full GPU work per request — both prefill (processing input tokens) and decode (generating output tokens). A request with 1000 input tokens and 100 output tokens consumes significantly more capacity than one with 50 input and 50 output, and total-token accounting reflects this without explicit workload classification.

### 6.1 Per-Variant Supply (Maximum Throughput per Replica)

Supply $T_v^{max}$ is the **maximum sustainable total token throughput** of a single replica of variant $v$. This is not the throughput at current load — it is the ceiling the replica can sustain before violating a constraint. The constraint is determined by whichever limit binds first:

**Constraint A — KV cache capacity.** At the maximum allowable KV cache utilization $KV\%_{max}$ (e.g., 0.9), the ITL model predicts the decode speed under full memory pressure:

$$
ITL^{max}(v) = \alpha_v \cdot KV\%_{max} + \beta_v \cdot \bar{R} + \gamma_v
$$

$$
T_v^{kv} = \frac{\bar{IL}_{eff} + \bar{OL}}{P_{obs}(v) + ITL^{max}(v) \cdot \bar{OL}}
$$

This is the throughput when KV cache is at its operational ceiling. Note that $\bar{IL}_{eff} = \bar{IL} \cdot (1 - H\%)$ reflects that cached input tokens do not consume prefill time or new KV blocks.

**Constraint B — Latency targets.** Given target latency requirements $ITL_{target}$ and $P_{target}$ (from SLO or configuration), the throughput is bounded by the latency budget:

$$
T_v^{lat} = \frac{\bar{IL}_{eff} + \bar{OL}}{P_{target} + ITL_{target} \cdot \bar{OL}}
$$

**Effective supply** is the tighter of the two constraints:

$$
T_v^{max} = \min(T_v^{kv}, T_v^{lat})
$$

When no latency targets are configured, only the KV cache constraint applies: $T_v^{max} = T_v^{kv}$.

This formulation ensures that supply reflects the actual capacity ceiling — not the current operating point — giving the scaling signal a forward-looking character. As load increases and $KV\%$ approaches $KV\%_{max}$, the current throughput approaches $T_v^{max}$ and the scaling signal fires before saturation occurs.

### 6.2 Per-Model Demand

Demand is computed **per model**, matching the WVA model-level scaling semantics. The primary demand signal comes from the **llm-d inference scheduler**, which observes the request arrival rate $\lambda_m$ and mean input token count $\bar{IL}_m$ before requests are routed to backend variants:

$$
D_m^{tokens} = \lambda_m \cdot (\bar{IL}_{eff,m} + \bar{OL}_m)
$$

Where:
- $\lambda_m$ — request arrival rate from the scheduler: `rate(inference_extension_request_total{model=m}[1m])`
- $\bar{IL}_{eff,m} = \bar{IL}_m \cdot (1 - H\%)$ — mean effective input tokens, adjusted for KV cache hit rate. $\bar{IL}_m$ is observed at the scheduler level from `inference_extension_input_tokens`
- $\bar{OL}_m$ — mean output tokens per request, derived from vLLM instances: `rate(generation_tokens_sum) / rate(request_success_total)` aggregated across variants serving model $m$

Using the scheduler as the demand source has two advantages over aggregating vLLM pod metrics:
1. **Includes queued requests** — the scheduler sees incoming demand that hasn't yet been dispatched to pods, providing a leading indicator
2. **Input length visibility** — the scheduler observes prompt size before routing, while vLLM metrics only report after processing

The per-variant share of demand is proportional to the variant's current replica count:

$$
D_v^{tokens} = D_m^{tokens} \cdot \frac{I_v}{\sum_{v' \in m} I_{v'}}
$$

**Fallback:** When scheduler metrics are unavailable, demand falls back to aggregated vLLM metrics:

$$
D_m^{tokens} = \sum_{\text{pods serving } m} \left[ \text{rate}(\text{vllm:request\_prompt\_tokens\_sum}[1m]) + \text{rate}(\text{vllm:request\_generation\_tokens\_sum}[1m]) \right]
$$

This captures served demand but misses queued requests.

### 6.3 Required Replicas

The number of replicas needed for variant $v$:

$$
R_v = \left\lceil \frac{D_v^{tokens}}{T_v^{max}} \right\rceil
$$

Scaling signal:

$$
\Delta_v = R_v - I_v
$$

Where $I_v$ is the current replica count. $\Delta_v > 0$ triggers scale-up, $\Delta_v < 0$ allows scale-down.

### 6.4 Why Total Token Throughput

| Aspect | Request throughput | Output token throughput | Total token throughput |
|--------|-------------------|------------------------|----------------------|
| Prefill cost | Invisible | Invisible | Captured via IL |
| Long-prompt requests | Underestimates | Underestimates | Accurately reflects GPU time |
| Long-generation requests | Underestimates | Captures decode cost | Captures decode cost |
| Mixed workloads | Requires classification | Partial | Natural aggregation |
| Observable | `rate(request_success_total)` | `rate(generation_tokens_sum)` | `rate(prompt_tokens_sum) + rate(generation_tokens_sum)` |

## 7. Prefill/Decode Disaggregation (P/D Mode)

In llm-d P/D split deployments, prefill and decode run on separate pod pools. The Throughput Analyzer models each role independently.

### 7.1 Architecture

```
Requests → Prefill pods (P-role) → KV transfer → Decode pods (D-role) → Response
```

WVA manages variants with `role: prefill` or `role: decode` labels. Each role has its own scaling signal.

### 7.2 Decode Variants

Decode pods perform iterative token generation. In P/D mode, input length does **not** affect decode ITL — the KV cache for the prompt is transferred from prefill pods as a pre-computed block, so the decode pod's attention compute per step depends only on KV cache pressure from concurrent sequences, not on individual prompt lengths. The ITL model simplifies to:

$$
ITL_{decode}(v) = \alpha_v \cdot KV\%(v) + \gamma_v
$$

(The $\beta_v \cdot R$ term is dropped — it is only relevant in unified mode where prefill and decode share the same GPU.)

Prefill time is zero for decode pods. The E2E from the decode pod's perspective is purely decode:

$$
E2E_{decode} = ITL(v) \cdot OL
$$

Maximum supply (output tokens/sec per decode replica) is determined by whichever constraint binds first:

**KV cache constraint** — ITL at maximum KV utilization:

$$
T_v^{decode,kv} = \frac{1}{ITL^{max}(v)} = \frac{1}{\alpha_v \cdot KV\%_{max} + \gamma_v}
$$

**Latency constraint** — ITL at target:

$$
T_v^{decode,lat} = \frac{1}{ITL_{target}}
$$

$$
T_v^{decode} = \min(T_v^{decode,kv}, T_v^{decode,lat})
$$

Demand for model $m$ on decode pods: output token rate from the scheduler, or `rate(generation_tokens_sum)` across decode replicas as fallback.

$$
D_m^{decode} = \lambda_m \cdot \bar{OL}_m
$$

$$
R_v^{decode} = \left\lceil \frac{D_m^{decode}}{T_v^{decode}} \right\rceil
$$

### 7.3 Prefill Variants

Prefill pods process input tokens and transfer KV cache to decode pods. Maximum supply (input tokens/sec per prefill replica):

**Latency constraint** — prefill time at target:

$$
T_v^{prefill,lat} = \frac{\bar{IL}}{P_{target} + KVT(v)}
$$

**Observed ceiling** — prefill time under current peak load:

$$
T_v^{prefill,obs} = \frac{\bar{IL}}{P_{obs,peak}(v) + KVT(v)}
$$

Where:
- $P_{obs,peak}(v)$ — peak observed prefill time from `max_over_time(vllm:request_prefill_time_seconds[1m])`
- $KVT(v)$ — KV cache transfer latency to decode pod (observed from `vllm:kv_cache_transfer_latency`)

$$
T_v^{prefill} = \min(T_v^{prefill,lat}, T_v^{prefill,obs})
$$

When no prefill latency target is configured, use $T_v^{prefill,obs}$ only.

Demand for model $m$ on prefill pods: effective input token rate from the scheduler, adjusted for cache hits:

$$
D_m^{prefill} = \lambda_m \cdot \bar{IL}_{eff,m} = \lambda_m \cdot \bar{IL}_m \cdot (1 - H\%)
$$

Fallback: `rate(prompt_tokens_sum)` across prefill replicas (captures served demand only).

$$
R_v^{prefill} = \left\lceil \frac{D_m^{prefill}}{T_v^{prefill}} \right\rceil
$$

Note: prefill supply is in input tokens/sec since prefill pods only process input tokens.

### 7.4 Separate Parameter Stores

P/D mode maintains independent parameters per role:

```go
// Decode variant: ITL regression (2 params in P/D mode, 3 in unified)
type DecodeParameters struct {
    Alpha, Gamma float64 // Beta omitted in P/D mode (no R dependency)
    Covariance         [][]float64
    LastUpdated        time.Time
    SampleCount        int64
}

// Prefill variant: no regression needed (observed directly)
// Supply computed from observed TTFT + KV transfer latency
```

### 7.5 Coordinated Scaling

Prefill and decode demands are coupled — scaling decode without scaling prefill creates a prefill bottleneck (and vice versa). The analyzer reports both roles' required replicas to the V2 pipeline, which coordinates via the optimizer:

```
ThroughputAnalyzer
  ├── Prefill variants → RequiredCapacity (prefill tokens/sec deficit)
  └── Decode variants  → RequiredCapacity (decode tokens/sec deficit)
        ↓
  ScalingOptimizer (handles both roles, respects GPU constraints per role)
```

The optimizer can apply different cost models per role (prefill pods may use cheaper GPUs) and respect per-role GPU constraints from the `ConstraintProvider`.

## 8. Integration with WVA Pipeline

The Throughput Analyzer implements the `Analyzer` interface:

```go
type ThroughputAnalyzer struct {
    paramStore *ParameterStore  // per-variant, per-role parameters
    regressor  *OnlineRegressor // RLS regression engine
}

func (a *ThroughputAnalyzer) Name() string { return "throughput" }

func (a *ThroughputAnalyzer) Analyze(ctx context.Context, input AnalyzerInput) (*AnalyzerResult, error) {
    // 1. Extract current KV%, R, OL, observed TTFT, observed ITL from ReplicaMetrics
    // 2. Update ITL regression with new observations
    // 3. Predict ITL for current conditions
    // 4. Compute token throughput supply per variant (with P/D role awareness)
    // 5. Compute token throughput demand per variant
    // 6. Return RequiredCapacity and VariantCapacities
}
```

Pipeline integration:

```
Prometheus metrics
    ↓
ThroughputAnalyzer.Analyze()
    ↓
AnalyzerResult {RequiredCapacity, VariantCapacities}
    ↓
ScalingOptimizer (CostAware or GreedyBySaturation)
    ↓
Enforcer → VariantDecisions
```

Configuration:

```yaml
saturationScalingConfig:
  analyzerName: throughput   # or "saturation" for V2, "saturation-v1" for V1
```

## 9. Assumptions and Limitations

1. **ITL linearity** — ITL is modeled as linear in KV% and R. Under extreme load (near 100% KV), the relationship may become non-linear. The model degrades gracefully (overestimates latency, biases toward conservative scaling).

2. **Workload stationarity** — The regression adapts via EWMA forgetting factor, but sudden workload shifts (e.g., prompt length distribution change) require several cycles to converge.

3. **Single-workload approximation** — When workload types are not classified, the analyzer uses aggregate $\bar{R}$ and $\bar{OL}$. This is accurate when the workload mix is relatively homogeneous but may underweight latency-sensitive minorities in bimodal distributions.

4. **Metric availability** — Requires `time_per_output_token_seconds` and `request_prefill_time_seconds` from vLLM. If unavailable, the analyzer falls back to the saturation analyzer.

5. **P/D coupling** — In disaggregated mode, prefill and decode scaling are reported independently. The optimizer must coordinate to avoid imbalanced scaling. If one role scales but the other doesn't, the bottleneck shifts rather than resolves.

## 10. Future Extensions

- **Per-workload-type tracking**: Classify requests by (IL, OL) bucket and maintain separate ITL models per workload type for mixed-traffic scenarios.
- **Non-linear ITL models**: Replace linear regression with piecewise-linear or polynomial models if linearity assumption breaks under specific hardware.
- **SLO integration**: Use the predicted E2E to check against user-defined SLO targets (e.g., P95 E2E < 2s) and scale proactively before SLO breach.
- **KV transfer optimization**: In P/D mode, model KV transfer latency as a function of sequence length and network conditions to improve prefill supply estimation.
