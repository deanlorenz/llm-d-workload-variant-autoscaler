# Detailed Design: Throughput Analyzer — Proactive Rate-Based Scaling

**Based on:** Proposal 2 — Proactive Throughput-Based Scaling, Proposal 4 — Multi-Analyzer Unification Framework
**Status:** Draft
**Date:** 2026-02-10

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Analysis](#2-problem-analysis)
3. [Design Goals and Non-Goals](#3-design-goals-and-non-goals)
4. [Metrics: Rate-Based Demand and Supply](#4-rate-based-demand-and-supply)

---

## 1. Executive Summary

The Saturation Analyzer (V1 and V2) makes scaling decisions based on **instantaneous state** — current KV cache utilization and queue depth. It can only detect overload *after it has occurred*. This creates a fundamental detection lag: by the time saturation is observed, users are already experiencing degraded latency.

The **Throughput Analyzer** adds a complementary **rate-based** signal that measures the *velocity* of demand, not just the *level*. By tracking token arrival rate and comparing it to observed throughput capacity, the analyzer can detect when the current demand trajectory will exhaust capacity — before saturation occurs.

### How It Works

WVA Analyzers measure *demand* per model and *supply* per instance (variant). These allow WVA to estimate the number of instances needed to avoid overload. 

The Throughput Analyzer measures demand and supply in **tokens/sec**:

- **Demand rate**: How fast tokens are arriving (from request rate × average token count per request)
- **Supply rate**: How fast tokens can be processed (estimate throughput per replica at saturation)

When demand rate exceeds supply rate, the analyzer produces a positive `RequiredCapacity` signal — even before the saturation analyzer detects any overload. This enables **anticipatory scaling** that starts provisioning capacity 20-40 seconds earlier than saturation-only detection.

### Relationship to Saturation Analyzer

| Aspect | Saturation Analyzer V2 | Throughput Analyzer |
|--------|----------------------|---------------------|
| Signal type | Instantaneous state (level) | Rate of change (velocity) |
| Units | Tokens (absolute capacity) | Tokens/sec (throughput) |
| Detects | Current overload | Approaching overload |
| Strength | Accurate when saturated | Early detection during ramps |
| Weakness | Reactive (detects after the fact) | May overshoot during transient load |
| Scale-up | Based on demand vs capacity headroom | Based on demand rate vs throughput capacity |
| Scale-down | Based on spare capacity | Based on sustainable processing rate |

The two analyzers run **in parallel** with OR logic for scale-up (either can trigger) and AND logic for scale-down (both must agree), following the Proposal 4 multi-analyzer framework.

---

## 2. Problem Analysis

### 2.1 The Detection Lag Problem

Consider a traffic ramp from 20 RPS to 60 RPS over 5 minutes with 4 replicas:

```
Time    RPS    KV Usage    Queue    Saturation Says    Throughput Says
t=0     20     40%         0        steady             steady
t=60    28     50%         0        steady             demand_rate rising
t=90    32     55%         0        steady             SCALE UP (rate > capacity)
t=120   40     65%         2        steady             scale up (continued)
t=150   48     78%         5        SCALE UP (now)     scale up (continued)
t=180   56     88%         12       SCALE UP           scale up
```

The saturation analyzer detects the problem at t=150 (2.5 minutes into the ramp). The throughput analyzer detects the trajectory at t=90 — **60 seconds earlier**. With a 3-5 minute pod startup time, this 60-second head start means replicas are ready 60 seconds sooner, reducing the window of degraded service.

### 2.2 Why Rate Matters

Rate-based detection is fundamentally about **derivatives** vs **levels**:

- **Saturation (level)**: "KV cache is at 78% — we're overloaded"
- **Throughput (rate)**: "Tokens are arriving at 15,000/sec but we can only process 12,000/sec — we will be overloaded in ~20 seconds"

The rate signal is especially valuable for:
- **Linear ramps**: Steady increase in traffic over minutes
- **Step changes**: Sudden traffic shifts (e.g., marketing campaign, model routing changes)
- **Diurnal patterns**: Predictable daily traffic curves where rate change is visible early

### 2.3 Where Rate Is Less Useful

The throughput analyzer adds less value when:
- **Traffic is stable**: No rate change to detect
- **Saturation is instantaneous**: Burst traffic that jumps directly to saturation (both analyzers detect at the same time)
- **Workload mix shifts**: Same RPS but different prompt/output lengths — might not be able to detect the shift in demand rate before saturation

---

## 3. Design Goals and Non-Goals

### Goals

- **G1**: Detect scaling need 30-60 seconds before the saturation analyzer during traffic ramps
- **G2**: Implement the `interfaces.Analyzer` interface (same as Saturation V2)
- **G3**: Use existing vLLM and scheduler metrics
- **G4**: Integrate with the multi-analyzer framework (Proposal 4) for signal combination
- **G5**: Minimize false positives — avoid scaling up for transient rate spikes
- **G6**: Support heterogeneous GPU pools (different throughput capacity per variant)
- **G7**: Validate improvement via benchmarking before enabling by default

### Non-Goals

- Predicting future traffic patterns (forecasting, time-series models)
- Replacing the saturation analyzer (throughput is complementary, not a replacement)
- Adding new CRD fields (throughput uses the same `SaturationScalingConfig` with extended fields)
- Changing the reconciliation interval (throughput works within the existing 15s cycle)
- Per-request latency optimization (that's the SLO analyzer's domain — Proposal 3)

---

## 4. Rate-Based Demand and Supply

Input tokens (prefill) and output tokens (decode) have fundamentally different computational costs in vLLM. In each continuous-batching scheduler step:

- **Decode**: Each active request consumes 1 token of the batch budget, generating 1 output token. Memory-bandwidth bound (KV cache reads).
- **Prefill**: Remaining batch budget processes input tokens in bulk. Compute-bound (matrix multiplications).

Processing 1000 input tokens takes ~1 scheduler step. Generating 1000 output tokens takes ~1000 steps. Treating them as equivalent produces meaningless throughput numbers. 

The throughput analyzer therefore uses a **triple-channel model**, each tracking separate demand and supply rates:

T1. **Request rate**: Measured in Requests Per Second (RPS)
T2. **Prefill rate**: Measured in Prefill Tokens Per Second; supply (PPS) takes into account caching
T3. **Decode rate**: Measured in Prefill Tokens Per Second; supply (GPS) slows down with memory utilization

The **demand rates** can be readily estimated from the request rate, as long as the workload mix does not shift 
(i.e., the average input and output token counts per request remains stable).

The current per-instance **supply rates** can be obtained from existing vLLM metrics.
The challenge is estimating supply rates near saturation (whether it is dues to KV cache utilization or queue depth).
The Throughput Analyzer first estimates the near-saturation processing time (e.g., ITL, E2E) and near-saturation concurrency.
It then uses these estimates to estimate the maximal stable supply rates.

