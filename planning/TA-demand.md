# Demand Rate Estimation

This document defines four **rate-based demand signals** for an LLM inference
serving system and specifies how they should be computed from collected metrics.
Supply estimation (how much a single replica of each variant can handle) is
treated separately.

---

## 1. What Demand Means Here

A request of workload type $w \in \mathcal{W}$ places three distinct demands on
the system:

| Dimension | Unit | What it represents |
|-----------|------|--------------------|
| Request demand | req/s | Rate of new requests arriving — the system must route them and maintain sufficient concurrency. |
| Prefill demand | tokens/s | Input tokens that require GPU prefill computation, after prefix-cache adjustment. Drives TTFT and prefill GPU utilization. |
| Decode demand | tokens/s | Output tokens the system must generate. Each output token costs one decode step. Drives ITL and decode GPU utilization. |
| KV cache demand | tokens/s | Rate at which new KV cache memory is committed by incoming requests. Drives KV cache pressure. |

The autoscaler must ensure that the number of replicas of each variant is
sufficient to sustain these demand rates within SLO. This document focuses on
**measuring and estimating the demand**; matching demand to supply is discussed
separately.

---

## 2. Workload Model

### 2.1 Workload types and mixture weights

Requests are not homogeneous. Each distinct $(IL, OL)$ combination is treated as
a workload type $w \in \mathcal{W}$ with:

- $IL(w)$ — input (prompt) length in tokens
- $OL(w)$ — output (generation) length in tokens
- $\pi_w$ — mixture weight: fraction of requests belonging to type $w$

$$\pi_w = \frac{N_w}{\sum_{w' \in \mathcal{W}} N_{w'}} \geq 0, \qquad
\sum_{w \in \mathcal{W}} \pi_w = 1$$

### 2.2 Steady-distribution assumption

For the purpose of rate-based demand estimation, we assume the **distribution
$\{\pi_w\}$ is stationary or changes slowly** relative to the autoscaling
control loop period. This is typically satisfied: workload mix (e.g., short chat
vs. long batch) drifts on timescales of minutes to hours, while the autoscaler
acts on a 15–60 second period.

**This assumption does not fix the total request volume.** The total in-flight
count $N = \sum_w N_w$ can grow or shrink freely — that is precisely what the
autoscaler responds to. The steady-distribution assumption only says that when
$N$ doubles, each workload type $w$ approximately doubles its share:
$N_w \approx \pi_w \cdot N$.

### 2.3 Mixture weights from observable metrics

In the absence of per-workload-bin histograms, $\pi_w$ cannot be observed
directly. Two levels of approximation are available:

**Level 1 — Configured bins with observed averages (recommended).**
The operator configures a set of bins $w \in \mathcal{W}$ (e.g.,
short-chat: $IL=512, OL=256$; long-doc: $IL=8192, OL=1024$). Mixture weights
are derived by distributing the observed $(\overline{IL}_v, \overline{OL}_v)$
averages across bins via inverse-distance weighting or nearest-bin assignment.

**Level 2 — Single-bin fallback (default when no bins configured).**
Treat the entire workload as a single bin with $IL = \overline{IL}_v$ and
$OL = \overline{OL}_v$. Accurate for homogeneous traffic; degrades gracefully
for mixed workloads by operating on the distribution mean.

Per-workload-bin histograms (`vllm:request_prompt_tokens_bucket`,
`vllm:request_generation_tokens_bucket`) would enable direct measurement of
$\pi_w$ and are a high-priority metric addition per
[TA-notation.md §8](TA-notation.md).

---

## 3. Demand Rate Signals

All signals are **per-replica** (per vLLM instance of variant $v$) unless noted.
The prefix-cache hit rate $H％_v$ and the workload averages
$\overline{IL}_v$, $\overline{OL}_v$ are variant-specific (each replica of
variant $v$ reports its own values; these are then aggregated at the variant
level as described in §4).

### 3.1 Request arrival rate $\lambda_v$

$$\boxed{\lambda_v = \lambda_{req,v}} \quad [\text{req/s}]$$

The rate at which new requests are dispatched to this replica by the EPP
scheduler. This is the root signal from which all other demand rates derive.

### 3.2 Prefill demand $\lambda_{pre,v}$

$$\lambda_{pre,v} = \lambda_v \cdot \mathbb{E}_\pi\!\left[IL_{eff}\right]
= \lambda_v \cdot \sum_{w \in \mathcal{W}} \pi_w \cdot IL(w) \cdot (1 - H％_v)
\quad [\text{tokens/s}]$$

This is the rate of input tokens that require actual GPU prefill computation.
Prefix-cache hits ($H％_v$ fraction of input tokens) reuse existing KV
entries and do not consume prefill cycles; they are excluded.

**Single-bin simplification:**

$$\lambda_{pre,v} = \lambda_v \cdot \overline{IL}_v \cdot (1 - H％_v)$$

### 3.3 Decode demand $\lambda_{dec,v}$

$$\lambda_{dec,v} = \lambda_v \cdot \mathbb{E}_\pi\!\left[OL\right]
= \lambda_v \cdot \sum_{w \in \mathcal{W}} \pi_w \cdot OL(w)
\quad [\text{tokens/s}]$$

This is the expected output token generation rate demanded of the system: the
system must produce $\lambda_{dec,v}$ tokens per second to keep up with
$\lambda_v$ requests/s under the current workload distribution. Because $OL$ is
only observable post-completion, $\mathbb{E}_\pi[OL]$ is estimated from the
trailing average $\overline{OL}_v$.

**Single-bin simplification:**

$$\lambda_{dec,v} = \lambda_v \cdot \overline{OL}_v$$

### 3.4 KV cache demand $\lambda_{tok,v}$

$$\lambda_{tok,v} = \lambda_v \cdot \mathbb{E}_\pi\!\left[IL_{eff} + OL\right]
= \lambda_v \cdot \sum_{w \in \mathcal{W}} \pi_w \cdot \bigl(IL(w) \cdot (1 - H％_v) + OL(w)\bigr)
\quad [\text{tokens/s}]$$

This is the rate at which incoming requests commit new KV cache memory. When a
request of type $w$ arrives, it will occupy $IL_{eff}(w)$ KV slots immediately
at prefill and grow to $IL_{eff}(w) + OL(w)$ slots by the end of its decode
phase. The total KV footprint per request is therefore $IL_{eff}(w) + OL(w)$
tokens, and the rate of this KV commitment is $\lambda_{tok,v}$.

Note the relationship:

$$\lambda_{tok,v} = \lambda_{pre,v} + \lambda_{dec,v}$$

**Single-bin simplification:**

$$\lambda_{tok,v} = \lambda_v \cdot \bigl(\overline{IL}_v \cdot (1 - H％_v) + \overline{OL}_v\bigr)$$

---

## 4. Per-variant Demand Aggregation

For variant $v$ with $I_v$ replicas $r \in \mathcal{R}_v$, the variant-level
demand rates are the **sum across replicas**, because each replica handles a
disjoint share of the dispatched traffic:

$$\Lambda_{req,v} = \sum_{r} \lambda_{req,v,r} \quad [\text{req/s}]$$

$$\Lambda_{pre,v} = \sum_{r} \lambda_{pre,v,r} \quad [\text{tokens/s}]$$

$$\Lambda_{dec,v} = \sum_{r} \lambda_{dec,v,r} \quad [\text{tokens/s}]$$

$$\Lambda_{tok,v} = \Lambda_{pre,v} + \Lambda_{dec,v} \quad [\text{tokens/s}]$$

The **per-replica average demand** (representative load on a single replica,
used for supply-side comparison):

$$\lambda_{req,v}^{\text{avg}} = \frac{\Lambda_{req,v}}{I_v}, \qquad
\lambda_{tok,v}^{\text{avg}} = \frac{\Lambda_{tok,v}}{I_v}$$

### Scheduler queue contribution

Requests queued in the EPP flow control layer are not yet dispatched to any
replica and therefore not reflected in any replica's $\lambda_{v,r}$. A queue
of $Q$ requests represents additional latent demand that must be drained within
a bounded time to avoid compounding SLO violations.

**Drain time bound.** For the decode channel, the target queue drain time is:

$$W_{max} = \text{QueueDrainFactor} \times \text{ITL}(k_{sat}) \times \overline{OL}$$

This bounds per-request queueing time to $\leq \text{QueueDrainFactor}$ saturated
decode periods. $\text{ITL}(k_{sat})$ is used rather than the current average ITL
for stability: at high load $\text{ITL}(k^*)$ is noisy, while $\text{ITL}(k_{sat})$
is computed from the calibrated model. Default $\text{QueueDrainFactor} = 2.0$.

The queue decode demand rate is:

$$\Delta\lambda_{dec} = \frac{Q \cdot \overline{OL}}{W_{max}}
= \frac{Q}{\text{QueueDrainFactor} \times \text{ITL}(k_{sat})} \quad [\text{tokens/s}]$$

$\overline{OL}$ **cancels** — the result is independent of output length given the
drain-time framing. This is added to model-level decode demand only (prefill
demand contribution from the queue is deferred to a later PR when prefill-rate
supply/demand is added).

---

## 5. Metric Sources

All inputs required for demand computation are already collected:

| Symbol | Go Field (`ReplicaMetrics`) | Prometheus Metric | Collected? |
|--------|----------------------------|------------------|------------|
| $\lambda_v$ | `ArrivalRate` | `rate(inference_extension_scheduler_attempts_total{status="success"}[5m])` per pod | **Yes** |
| $\overline{IL}_v$ | `AvgInputTokens` | `rate(vllm:request_prompt_tokens_sum[5m]) / rate(..._count[5m])` per pod | **Yes** |
| $\overline{OL}_v$ | `AvgOutputTokens` | `rate(vllm:request_generation_tokens_sum[5m]) / rate(..._count[5m])` per pod | **Yes** |
| $H％_v$ | `PrefixCacheHitRate` | `rate(vllm:prefix_cache_hits[5m]) / rate(vllm:prefix_cache_queries[5m])` per pod | **Yes** |
| $Q$ | `SchedulerQueue.QueueSize` | `inference_extension_flow_control_queue_size` | **Yes** |

**All required inputs are already collected.** No new Prometheus scraping is
needed for the single-bin (Level 2) demand estimation.

### Direct rate alternatives (not yet collected)

The prefill and decode token rates can also be read directly from Prometheus as
raw counter rates, without requiring $\lambda_v$ and the workload averages:

$$\lambda_{pre,v}^{\text{direct}} = \text{rate}(\texttt{vllm:request\_prompt\_tokens\_sum}[\Delta t]) \cdot (1 - H％_v)$$

$$\lambda_{dec,v}^{\text{direct}} = \text{rate}(\texttt{vllm:request\_generation\_tokens\_sum}[\Delta t])$$

These are not currently stored as scalar fields in `ReplicaMetrics` (only the
per-request averages $\overline{IL}_v$ and $\overline{OL}_v$ are). They are
tagged Low priority in [TA-notation.md §8](TA-notation.md). When available, direct
rates are preferred over the $\lambda_v \cdot \overline{OL}_v$ approximation
because they do not require $\lambda_v$ and capture burst behavior that the
trailing average misses.

---

## 6. Computation Summary

```
# Per-replica demand (single-bin Level 2 fallback)
λ_req      = ArrivalRate
IL_eff     = AvgInputTokens * (1 - PrefixCacheHitRate)
λ_pre      = λ_req * IL_eff                          # prefill demand [tokens/s]
λ_dec      = λ_req * AvgOutputTokens                 # decode demand  [tokens/s]
λ_tok      = λ_pre + λ_dec                           # KV cache demand [tokens/s]

# Per-replica demand (multi-bin Level 1, bins w ∈ W with weights π_w)
λ_pre      = λ_req * Σ_w π_w * IL(w) * (1 - PrefixCacheHitRate)
λ_dec      = λ_req * Σ_w π_w * OL(w)
λ_tok      = λ_pre + λ_dec

# Variant-level aggregation (I_v replicas, r ∈ R_v)
Λ_req      = Σ_r λ_req_r
Λ_pre      = Σ_r λ_pre_r
Λ_dec      = Σ_r λ_dec_r
Λ_tok      = Λ_pre + Λ_dec

# Scheduler queue correction (model-level)
Λ_req     += Q / T_e2e
Λ_pre     += (Q / T_e2e) * IL_eff_model
Λ_dec     += (Q / T_e2e) * OL_model
Λ_tok      = Λ_pre + Λ_dec
```

When `PrefixCacheHitRate == 0` (prefix caching disabled or metric unavailable),
`IL_eff = AvgInputTokens` — a conservative (maximum-demand) assumption.

---

## 7. Caveats and Limitations

1. **$\lambda_v$ is dispatched rate, not arrival rate.** `ArrivalRate` reflects
   requests successfully dispatched to this replica. It equals the true arrival
   rate only when $W_{epp} = 0$ (no EPP queue backlog). During queue build-up,
   per-replica $\lambda_{v,r}$ understates true demand; the queue correction
   in §4 partially compensates at the model level.

2. **$\overline{OL}_v$ is a trailing average over completed requests.** It lags
   workload shifts: if output length suddenly increases, $\overline{OL}_v$
   catches up only as new completions accumulate in the rate window. This lag
   causes $\lambda_{dec,v}$ and $\lambda_{tok,v}$ to be temporarily understated
   during such shifts.

3. **$H％_v$ is applied uniformly across workload types.** In reality,
   prefix-cache hit rate can differ between short and long prompts. With per-bin
   hit rates the formula becomes $\lambda_{pre,v}(w) = \lambda_v \cdot \pi_w
   \cdot IL(w) \cdot (1 - H％_v(w))$. Without per-bin data, the uniform
   approximation is the best available.

4. **Steady-distribution assumption breaks during rapid workload shifts.**
   If the workload mix changes faster than the $\pi_w$ estimation window, the
   mixture weights lag. During a shift from short-chat to long-batch traffic,
   $\pi_w$ and $\overline{OL}_v$ both underestimate the emerging demand. The
   autoscaler's hysteresis and scale-up speed are the primary mitigations.
