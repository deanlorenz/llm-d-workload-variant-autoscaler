Here’s a structured markdown document capturing our discussion so far, with a summary at the end:

---

# Autoscaling LLM and Video Services with Multiple SLOs

## 1. Problem Setting

We are considering two types of workloads with multiple SLO targets:

1. **Video Serving**

   * Long requests: preprocessing + download
   * Multiple backend flavors (different hardware)
   * SLOs:

     * **TTFB / TTFT**: maximal time to first byte
     * **Rate / TPOT**: minimal sustained rate
   * Observations:

     * Queueing, processing, and serving stages have different bottlenecks
     * Processing time may vary by hardware and concurrency
     * Serving time bounded by bandwidth

2. **LLM Inference**

   * Requests for the same model but multiple implementations (GPUs)
   * Each pod performs:

     * **Prefill** (preprocessing): depends on input tokens, caching
     * **Decode** (generation): depends on output tokens and concurrency
   * SLOs:

     * **TTFT**: time to first token
     * **TPOT**: token throughput per request
   * Observations:

     * Maximum concurrency limited by KV memory (total tokens)
     * Prefill can also limit concurrency depending on input length
     * Continuous batching (vLLM) introduces dynamic chunked scheduling

---

## 2. Video Serving Autoscaling Principles

* **Pipeline separation**: `[Queue] → [Encoder Tier] → [Object Store/Cache] → [Serving Tier]`
* **Processing tier (encoder)**

  * Dominates TTFB
  * Scale on:

    * Queue depth
    * Active prefill tokens
    * Safe concurrency per flavor
* **Serving tier (download)**

  * Dominates sustained rate SLO
  * Scale on:

    * Active downloads
    * Per-instance bandwidth
* **Scaling formula per flavor**

  ```
  replicas = max(
      ceil((active_processing + queued_requests) / Cp_safe),
      ceil(active_downloads / Cs_safe)
  )
  ```
* **Scale-down considerations**

  * Drain active requests before shutdown
  * Use slow scale-down to avoid violating SLOs
  * Maintain minimum replica floor for cold-start buffer
* **Key insights**

  * TTFT depends on queueing + prefill
  * Rate SLO depends on serving bandwidth
  * Avoid scaling on RPS, average CPU, or latency

---

## 3. LLM Inference Autoscaling Principles

* **Signals available from vLLM**

  * KV cache utilization
  * Number of running requests
  * ITL (inter-token latency)
  * Number of waiting requests
* **Request data**

  * Input tokens (IL)
  * Expected output tokens (OL_est)
* **SLOs**

  * TTFT: time to first token
  * TPOT: token throughput
* **Two main constraints**

  1. **Prefill load** (TTFT pressure)

     * `PLR = arrival_prefill_tokens / (replicas × prefill_capacity_per_gpu)`
     * Maintain PLR ≤ 0.7–0.8
  2. **Decode load** (TPOT pressure)

     * `DLR ≈ KV_cache_utilization`
     * Maintain DLR ≤ 0.7–0.8
* **Replica calculation**

  ```
  replicas = max(
      ceil(prefill_token_load / prefill_capacity),
      ceil(active_sequences / C_safe)
  )
  ```
* **Observations from workload examples**

  | Workload | IL   | OL   | Notes                                                                 |
  | -------- | ---- | ---- | --------------------------------------------------------------------- |
  | W1       | 5000 | 1200 | Long decode tail → higher decode concurrency pressure → max RPS lower |
  | W2       | 6000 | 200  | Long prefill → prefill pressure → TTFT higher, decode rarely limiting |
* **Insights**

  * ITL can remain similar if scaling maintains constant active sequences per GPU
  * TTFT depends on prefill and may differ between workloads
  * Max sustainable request rate lower for workloads with long decode tails (OL high)

---

## 4. Why Production LLM Autoscalers Break

1. **Wrong scaling signal**

   * GPU utilization, RPS, or average latency are insufficient
2. **Treating tokens as homogeneous**

   * Number of active sequences matters more than total tokens
3. **Ignoring decode tail effects**

   * Long outputs increase steady-state concurrency → service time grows → SLO violated
4. **Ignoring prefill/decode interference**

   * Prefill-heavy workloads can block decode → TTFT/ITL increase
5. **Slow scale-up vs scale-down**

   * Feedback lag causes oscillation
6. **KV memory as a hard constraint**

   * Ignored in naive scaling → OOMs or performance collapse
7. **Heterogeneous GPUs**

   * Static replica count misallocates capacity
8. **Continuous batching metrics lag**

   * Metric averaging hides rapid changes
9. **Coupled loops**

   * Prefill + decode interact → jitter or instability
10. **Workload mix changes**

    * Assumptions of stationary workload fail

---

## 5. Mathematical Stability Analysis (Decode Loop)

* **System dynamics**

  ```
  n = active sequences per GPU
  TPOT ≈ T_0 / n
  W ≈ OL × n / T_0
  L = λ × W
  ```
* **Stability condition**

  ```
  ρ = λ × OL / (R × T_0) < 1
  ```

  * ρ → 1 → service time grows nonlinearly → positive feedback → collapse
* **Discrete-time feedback control**

  ```
  R(t+1) = R(t) + k × (U(t-Δ) - U*)
  ```

  * Measurement + provisioning delay Δ introduces oscillation
  * Slope near saturation a → amplification of error
* **Oscillation mechanism**

  * Under-provision → utilization rises → ITL ↑ → scale-up → utilization drops → scale-down → repeat
* **Prefill loop adds second coupled dimension**

  * Queue growth triggers scaling → interacts with decode loop → possible replica jitter
* **Stability rules**

  1. Operate at ρ* ≤ 0.7 (stay in quasi-linear region)
  2. Scale-up fast, scale-down slow
  3. Use feedforward control: replicas ≈ λ × OL / (ρ* × T_0)
  4. Use KV utilization as safety correction

---

## 6. Summary

* Multi-SLO workloads (TTFT + TPOT) require **multi-dimensional scaling**.
* **Video serving**

  * Separate pre-processing and serving tiers
  * Scale each independently using queue depth, bandwidth, and concurrency
* **LLM inference**

  * Scale on **prefill token load** and **decode concurrency / KV utilization**
  * Maintain headroom in both dimensions
  * Continuous batching requires proactive scaling; reactive metrics alone are insufficient
* **Workload characteristics**

  * Decode tail (OL) dominates max sustainable rate
  * Prefill length (IL) dominates TTFT
  * Max token-based RPS depends on sequence length distribution
* **Stability**

  * Nonlinear decode time creates a positive feedback loop near saturation
  * Oscillation occurs if controller gain, delay, or workload assumptions are misaligned
  * Stable autoscaling requires conservative target utilization, feedforward planning, and slow scale-down

---

This document captures the theory, observations, scaling rules, and mathematical stability analysis discussed so far.

---

If you want, I can **add a diagram showing the two-dimensional autoscaling loops** for vLLM (prefill vs decode) and illustrate where instability arises. That makes it very visual for production design.
