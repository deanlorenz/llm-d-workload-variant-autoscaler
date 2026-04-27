## Analyzer K3 — Concurrency–Latency Signal per Workload Type

### 1. Entities and Observables

*   Backend variants $v \in \mathcal{V}$ (e.g., specific vLLM models/configs).
*   Workload types $w \in \mathcal{W}$ characterized by expected $IL(w)$ and $OL(w)$.
*   llm‑d metrics (router/scheduler level):
    *   $N(w)$: concurrent requests of workload type $w$ (system‑wide).
    *   $N(v)$: concurrent requests handled by variant $v$.
    *   $N(w,v)$: estimated concurrency of type $w$ on variant $v$.  
        Because routing is $w$‑aware but $v$‑oblivious:
        $$
        N(w,v) \approx N(v)\cdot \frac{N(w)}{\sum_{w'} N(w')}
        $$
*   vLLM metrics (per‑variant):
    *   Token throughputs (prefill and decode), batch sizes, GPU/memory pressure, queue/latency histograms, KV/page stats (details in §5).

### 2. KV Load per Workload and Variant

Let $H\text{\\\%}(v)$ be the observed KV hit‑rate on variant $v$ (not per $w$).  
Define expected KV cost per request of type $w$ on $v$:

$$
KV(w,v) = H\text{\\\%}(v)\cdot \big(IL(w) + \tfrac{1}{2}\,OL(w)\big)
$$

Let $KV_{\max}(v)$ denote the effective KV capacity available to the model on $v$ (respect paging/offload policy). Then the **concurrency ceiling** for $(w,v)$ under KV constraints is:

$$
N_{\max}(w,v) = \frac{KV_{\max}(v)}{KV(w,v)}
$$

> *Notes*:  
> • The $\tfrac{1}{2}$ factor captures amortized incremental KV growth during decoding.  
> • If you maintain separate “on‑GPU KV” and “offloaded KV,” use the tighter of the two capacities or a weighted capacity depending on offload bandwidth and observed hit‑rate tiers.

### 3. End‑to‑End Latency Model

We model

$$
E2E(w,v) \approx TTFT(w,v) + ITL(w,v)\cdot OL(w)
$$

and adopt **two practical estimation paths**:

#### 3.1 Direct, metrics‑driven $E2E$ (preferred)

Estimate $E2E(w,v)$ directly from vLLM **per‑request latency histograms** (see §5).  
Map each in‑flight/observed request to its workload bucket $w$ (by $(IL,OL)$ binning at llm‑d), then aggregate per variant $v$:

*   $E[TTFT\mid v, w]$ from “time‑to-first-token” histogram (if exposed) or from prefill time proxies.
*   $E[ITL\mid v, w]$ from “inter‑token latency” or $E[\text{decode-time}/\text{decode-tokens}\mid v,w]$.
*   Form $E2E(w,v)=E[TTFT\mid v, w] + OL(w)\cdot E[ITL\mid v, w]$.

This avoids fitting structural parameters and leverages real behavior, including kernel/runtime effects.

#### 3.2 Linear ITL model (fallback)

When per‑$w$ histograms are not available, use a linear ITL model **per $(v,w)$**:

$$
ITL(w,v) \approx a_{v,w}\cdot KV\text{\\\%}(v) + b_{v,w}
$$

with $(a_{v,w},b_{v,w})$ learned from periods dominated by a near‑uniform workload bucket $w$ or via regression on batches labeled by $w$ at the llm‑d level and joined to per‑variant vLLM utilization/KV% time series. Then

$$
E2E(w,v) \approx TTFT(w,v) + OL(w)\cdot \big(a_{v,w}\cdot KV\text{\\\%}(v)+b_{v,w}\big)
$$

where $TTFT(w,v)$ can be proxied by prefill time (see §5.2).

### 4. K3 Supply and Demand

**Demand** (concurrency normalized by latency):

$$
D_v = \sum_{w\in\mathcal{W}} \frac{N(w,v)}{E2E(w,v)}
$$

**Supply** (max sustainable concurrency normalized by latency):

$$
S_v = \sum_{w\in\mathcal{W}} \frac{N_{\max}(w,v)}{E2E(w,v)}
$$

**Scaling action** for variant $v$ with $I_v$ current instances:

$$
\Delta_v = \left\lceil \frac{D_v}{S_v} \right\rceil - I_v
$$

with standard dampening/hysteresis and min‑step policies applied by the controller loop.

### 5. vLLM Metrics — What to Use and How

Below are the **concrete vLLM signals** that make K3 robust without synthetic load. Metric names may vary by exporter; treat these as canonical categories.

#### 5.1 Concurrency, Batching, and Token Accounting

*   **Prefill tokens/sec** and **decode tokens/sec** ($\hat{T}_{\text{prefill}}(v)$, $\hat{T}_{\text{decode}}(v)$): time‑windowed rates.
    *   Use to sanity‑check $E[ITL\mid v,w] \approx 1/\hat{T}_{\text{decode}}(v)$ after correcting for batching effects.
*   **Batch size histograms** (prefill and decode): to detect when IL distributions push against max batch and inflate $TTFT$.
*   **Active sequences** / **requests in service**: proxy for $N(v)$.
*   **Generated tokens per request** histograms: join with llm‑d’s $w$ bins to refine $OL(w)$ if needed.

#### 5.2 Latency Decomposition

*   **TTFT histogram** (if available) or **prefill time** average/percentiles per batch:  
    $E[TTFT\mid v,w] \approx E[\text{prefill-time per req}\mid v,w]$, corrected by batch‑formation overhead if exposed.
*   **Per‑request E2E histogram** (start→finish):  
    Allows direct $E2E(w,v)$ if you can tag or probabilistically assign requests to $w$ (see §5.4).
*   **Decode time per token** or **ITL histogram**:  
    If not available per request, approximate $E[ITL\mid v,w]$ from $\text{decode-time}/\text{decode-tokens}$ statistics and adjust by batch size.

#### 5.3 KV / Paging / Memory Pressure

*   **KV cache utilization %** (on‑GPU and offloaded separately if possible).  
    Use for $KV\text{\\\%}(v)$ in the $ITL$ linear model and to define $KV_{\max}(v)$ (tight capacity).
*   **PagedAttention page usage** (used/evicted/misses):  
    If present, derive an effective $H\text{\\\%}(v)$ from page hit/miss counters, or else use llm‑d's cache‑aware scheduler's observed hit‑rate.
*   **Fragmentation indicators** (if any): even if llm‑d avoids fragmentation, these help diagnose unexpected $TTFT$/decode slowdowns.

#### 5.4 Mapping variant‑level histograms to workload types $w$

Because vLLM metrics are not per $w$:

*   Maintain **workload buckets** $w$ at the llm‑d level (e.g., 2D bins over $IL$ and $OL$).
*   For each sample window, compute the **mixture weights** $\pi_w = \frac{N(w)}{\sum_{w'}N(w')}$.
*   When only per‑variant histograms are available, recover **per‑$(v,w)$ expectations** by:
    *   If joinable via request IDs: **direct join** and aggregate per $w$.
    *   If not: **proportional deconvolution** using $\pi_w$, combined with structural constraints (e.g., $TTFT$ grows with $IL$, $ITL$ grows with $KV\text{\\\%}$) via a simple constrained least‑squares fit to split per‑variant moments into $w$‑components.

This yields workable $E[TTFT\mid v,w]$, $E[ITL\mid v,w]$, $H\text{\\\%}(v)$, and thus $E2E(w,v)$.

### 6. Practical Estimation Pipeline (Recommended)

1.  **Bucket workloads**: define $w$ bins (e.g., $IL$ log‑bins × $OL$ quantile bins).
2.  **Periodic aggregation (per variant $v$)**:
    *   Read vLLM histograms: $E[\text{TTFT}]$, $E[\text{ITL}]$, $E[\text{decode-tokens}]$, batch sizes, $KV\text{\\\%}(v)$, paging, GPU util.
    *   From llm‑d, read $N(w)$ and $N(v)$; compute $N(w,v)$ by proportional allocation.
3.  **Estimate $H\text{\\\%}(v)$**: from vLLM page hits/misses or llm‑d cache‑aware scheduler counters.
4.  **Compute $KV(w,v)$** and $N_{\max}(w,v)=KV_{\max}(v)/KV(w,v)$.
5.  **Estimate $E2E(w,v)$**:
    *   **Preferred**: join requests to per‑request vLLM latency; average per $(w,v)$.
    *   **Else**: deconvolve per‑variant histograms using mixture weights $\pi_w$.
    *   **Fallback**: $ITL(w,v)=a_{v,w},KV\text{\\\%}(v)+b_{v,w}$ (learned); $TTFT(w,v)$ from prefill time + batch overhead model.
6.  **Compute K3 signals**: $D_v=\sum_w N(w,v)/E2E(w,v)$ and $S_v=\sum_w N_{\max}(w,v)/E2E(w,v)$.
7.  **Scale**: $\Delta_v=\lceil D_v/S_v\rceil - I_v$, with hysteresis and cooldown.
8.  **Safeties**: clip outliers, apply EMA smoothing to $E2E$ and $H\text{\\\%}$, and guardrails on min/max instance deltas.

### 7. Notes on Robustness and Identifiability

*   $a_{v,w}, b_{v,w}$ should be **per $(v,w)$**, not per $v$ only. These can be learned online with recursive least squares using $(KV\text{\\\%}(v), ITL)$ pairs during windows where $w$ dominates traffic, or via joint regression with mixture weights.
*   If $OL(w)$ varies widely, use **online winsorized means** or **median‑of‑means** to stabilize $E2E(w,v)$.
*   When offloading is enabled, define $KV_{\max}(v)$ as the **effective** capacity at the target $ITL$ slope (e.g., the KV\text{\\\%} at which $ITL$ exceeds SLO slope), not just physical capacity.

***

## Minimal Pseudocode (controller-side)

```python
# Inputs per control window:
# from llm-d: N_w, N_v, IL_w, OL_w
# from vLLM: histograms & counters -> TTFT_v, ITL_v, KVpct_v, Hpct_v, KVmax_v
# config: workload bins W, variants V

for v in V:
    # mixture weights over workloads
    total_Nw = sum(N_w[w] for w in W)
    pi_w = {w: (N_w[w] / total_Nw) if total_Nw > 0 else 0.0 for w in W}

    # infer N(w,v) by proportional allocation
    N_wv = {w: N_v[v] * pi_w[w] for w in W}

    # estimate E2E(w,v)
    E2E_wv = {}
    for w in W:
        # preferred: direct per-(w,v) join → E2E_wv[w] = mean_e2e(w,v)
        # else: deconvolve from per-variant histograms (not shown)
        # fallback: linear ITL(w,v) model
        ITL_wv = a[v][w] * KVpct_v[v] + b[v][w]
        TTFT_wv = est_ttft_from_prefill(v, w)  # use prefill time + batch overhead model
        E2E_wv[w] = TTFT_wv + OL_w[w] * ITL_wv

    # KV-based concurrency ceiling
    S_v = 0.0
    D_v = 0.0
    for w in W:
        KV_wv = Hpct_v[v] * (IL_w[w] + 0.5 * OL_w[w])
        Nmax_wv = KVmax_v[v] / max(KV_wv, 1e-6)
        S_v += Nmax_wv / max(E2E_wv[w], 1e-3)
        D_v += N_wv[w]    / max(E2E_wv[w], 1e-3)

    target_instances = math.ceil(D_v / max(S_v, 1e-6))
    delta = apply_hysteresis(target_instances - current_instances[v])
    scale(v, delta)
```

***

## What You’ll Need From vLLM (Summary)

*   **Throughputs**: prefill tokens/sec, decode tokens/sec (windowed means).
*   **Latencies**: per‑request TTFT and E2E histograms (or at least per‑batch prefill times and decode time per token).
*   **Batching**: histograms for prefill/decode batch sizes.
*   **KV / Paging**: KV\text{\\\%} (GPU and offloaded), page hits/misses/evictions → derive $H\text{\\\%}(v)$.
*   **GPU util / SM occupancy**: optional for diagnostics and cross‑checks.

If some are missing, K3 still works with the fallback linear ITL model and prefill‑time TTFT proxy; it just converges a bit slower until the regressors stabilize.
