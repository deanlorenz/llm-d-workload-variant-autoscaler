# vLLM Performance Bottlenecks - Technical Discussion Summary

**Date:** April 16, 2026  
**Source:** ChatGPT conversation export (chatgpt-current-1776362574645.md)

---

## Problem Statement

Investigating why vLLM systems saturate before KV cache utilization (k) reaches typical thresholds like 0.8, particularly for workloads with **short output lengths (~150 tokens)**. The goal is to predict maximum sustainable request rates (RPS) from pre-saturation observations only.

---

## Key Concepts

### Performance Metrics
- **k**: KV cache utilization (percentage of cache memory used)
- **ITL**: Inter-Token Latency (time between consecutive tokens during decode)
- **TTFT**: Time To First Token (prefill time without wait)
- **E2E**: End-to-End latency (total request completion time)
- **N**: Number of running requests
- **W**: Number of waiting requests
- **λ**: Arrival rate (RPS)
- **IL**: Input Length (tokens)
- **OL**: Output Length (tokens)

### Little's Law
```
N + W = λ × E2E
```

---

## Three Performance Regimes

### 1. Decode-Limited (Traditional)
- **Characteristics**: Long OL, high k
- **Bottleneck**: Memory bandwidth
- **Behavior**: ITL grows linearly with k
- **Saturation**: k > 0.8 triggers instability

### 2. Prefill-Limited
- **Characteristics**: Large IL
- **Bottleneck**: GPU compute
- **Behavior**: Prefill dominates total time

### 3. Scheduler/Churn-Limited (Focus of Analysis)
- **Characteristics**: Short OL (~150), moderate IL
- **Bottleneck**: Prefill-decode interference
- **Behavior**: High request turnover, batch fragmentation
- **Saturation**: Occurs at k < 0.8

---

## The Instability Mechanism

### Core Formula: ITL Inflation
```
ITL(k,λ) ≈ X + Y×k + Δ_pref(λ)
```

Where:
- **X**: Base decode time (constant)
- **Y**: KV bandwidth coefficient (constant for given IL, OL)
- **Δ_pref(λ)**: Prefill interference term (grows with λ)

### Prefill Pressure
```
α ≈ λ×T_prefill/B
```

Where:
- **α**: Fraction of steps where prefill interferes
- **B**: Effective batch size (≈ N)
- **T_prefill**: Prefill time per request

### Why Short OL Matters
Each request contributes:
- 1 prefill phase
- OL decode steps

Prefill-to-decode ratio per unit time:
```
prefill_work/decode_work ∝ 1/OL
```

**As OL ↓, prefill pressure per token ↑**

### Positive Feedback Loop
```
λ↑ ⇒ ITL↑ ⇒ E2E↑ ⇒ N↑ ⇒ ITL↑
```

1. **λ increases** → More arrivals, more prefills per unit time
2. **Prefill steals cycles** → Decode steps delayed, ITL increases
3. **E2E latency increases** → By Little's Law: N+W grows
4. **Larger N increases contention** → More KV reads, more fragmentation
5. **ITL increases further** → Positive feedback

### Service Rate Collapse
```
μ_eff = B/ITL(λ)
```

Instability occurs when:
```
λ > μ_eff
```

This can happen at **any k**, not just k > 0.8.

---

## Empirical Relationships (Pre-Saturation)

### 1. ITL vs KV Load
```
ITL(k) ≈ X + Y×k
```
- Valid for medium/high KV load
- X, Y are constants (measurable from data)

### 2. Prefill Time vs KV Load
```
T_pref(k) ≈ Z×IL×k
```
- Z doesn't depend much on OL or IL

### 3. KV Usage
```
k ≈ N×(IL + 0.5×OL)/KV_max
```

### 4. Relationship Between N and λ
```
N ≈ λ×OL×ITL(k)
```

---

## Key Diagnostic: ρ = TTFT/ITL Ratio

### Definition
```
ρ(k) = TTFT(k)/ITL(k)
```

### Interpretation
- **TTFT ∼ T_pref**: Prefill time
- **ITL**: Per-token service time
- **ρ**: Prefill-to-decode ratio

### Regime Detection
```
ρ ≪ √OL  →  Decode-dominated (safe)
ρ ≈ √OL  →  Crossover point
ρ ≳ √OL  →  Prefill-dominated instability
```

### Why √OL?
- Mean effect scales as 1/OL
- Fluctuation/interference scales as 1/√OL
- System destabilizes when prefill variance dominates decode smoothing

### Practical Threshold
For OL ≈ 100-200:
- √OL ≈ 10-14
- But real systems with batching: threshold ≈ 2-5
- User's heuristic: **ρ < 3 indicates prefill bound**

---

## Predicting λ_max: The Algorithm

### Step 1: Compute Derived Metrics

For each data point in experiment (sorted by increasing load):

```python
# Queueing indicator
φ = E2E / (OL × ITL)

# Prefill pressure indicator  
ρ = TTFT / ITL

# ITL curvature (finite difference)
g = d(ITL)/dλ

# Prefill interference rate
h = dρ/dλ
```

### Step 2: Detect the "Knee"

Saturation point = first index where all three conditions hold:

**Condition A (Service Degradation):**
- g increases sharply (convexity in ITL)

**Condition B (Prefill Interference):**
- h > 0 and accelerating

**Condition C (Queueing Onset):**
- φ > 1.1 (or 1.2)

### Step 3: Define λ_max

```
λ_max = last point before all three conditions hold simultaneously
```

### Simplified Heuristic

```
λ_max ≈ first point where:
  (TTFT/ITL) starts accelerating AND
  (E2E/(OL×ITL)) > 1.1
```

### Alternative: Normalized Ratio

```python
ρ_normalized = TTFT / (ITL × √OL)

# Thresholds:
ρ_normalized ≪ 1  →  safe
ρ_normalized ∼ 1  →  near instability
```

---

## Why Saturation Happens at k < 0.8

1. **k measures capacity usage**, not bandwidth
2. **Bottleneck is often bandwidth**, not capacity
3. **Prefill-decode interference** causes ITL inflation before KV fills
4. **System instability** triggered by service rate collapse, not KV saturation
5. **Two distinct modes**:
   - **Mode A (KV-driven)**: N grows → k grows → ITL increases → k > 0.8
   - **Mode B (Prefill-driven)**: W grows rapidly → ITL increases → system collapses before k > 0.8

---

## Implementation Plan

### Data Requirements
- Experiments with varying load (RPS, IL, or OL)
- Metrics per data point: ITL, TTFT, E2E, Run (N), MaxRun, Kvcache (k)
- Data segmented by test-name/experiment

### Analysis Steps

1. **Load data** (WVA_data160426_short.csv)
2. **Segment by experiment** (test-name)
3. **For each experiment**:
   - Sort by increasing load parameter
   - Compute: φ, ρ, g, h
   - Detect knee using three conditions
   - Output predicted λ_max
4. **Validation**: Compare predicted vs actual saturation
5. **Visualization**: Plot ITL, TTFT/ITL, φ curves

### Output Format

```
Experiment | IL | OL | Predicted_λ_max | Actual_Saturation | k_at_saturation | Regime
-----------|----|----|-----------------|-------------------|-----------------|--------
test_1     | 2k | 150| 45.2 RPS        | 47.1 RPS          | 0.62            | Prefill
test_2     | 2k | 800| 12.3 RPS        | 12.8 RPS          | 0.81            | Decode
...
```

---

## Key Formulas Reference

### Stability Boundary (Theoretical)
```
λ_max ≈ min(
  B/(OL×T_dec),           # Decode-limited
  B/(√OL×T_prefill)       # Prefill-limited
)
```

### KV/Decode Ceiling
```
λ_KV(k) = k×KV_max / (OL×(IL + 0.5×OL)×(X + Y×k))
```

### Prefill Instability Point
Solve for k* where:
```
TTFT(k*)/ITL(k*) ≈ √OL
```

Then:
```
λ_max ≈ λ_KV(k*)
```

---

## Practical Takeaways

1. **For short-output workloads**: Max sustainable RPS is set by prefill-decode coupling instability, not KV cache limits

2. **Scaling law**: RPS ∝ 1/(√OL × T_prefill)

3. **Detection strategy**: Use pre-saturation metrics only (φ, ρ, and their derivatives)

4. **No model assumptions needed**: Algorithm works without knowing X, Y, Z constants

5. **Transferable thresholds**: Normalized ρ' = TTFT/(ITL×√OL) works across experiments

---

## Next Steps

1. Implement detection algorithm on WVA_data160426_short.csv
2. Validate predictions against actual saturation points
3. Generate plots for visualization
4. Create reusable script for future experiments
5. Refine thresholds based on empirical results

---

## References

- Source conversation: chatgpt-current-1776362574645.md
- Data files: WVA_data160426_short.csv, WVA_data160426_short.xlsx
- Analysis script: analyze_vllm_performance.py (to be created)