# Supply Rate Estimation

This document defines the supply-side counterparts to the demand signals in
[TA-demand.md](TA-demand.md): the rates at which a single vLLM replica of
variant $v$ can sustain prefill computation, decode generation, and request
completions. These supply estimates are used in a later document to derive
stability conditions and autoscaling metrics.

---

## 1. Supply Signals

Each demand signal has a corresponding supply signal that the system must match
or exceed at steady state:

| Demand | Supply | Unit | Description |
|--------|--------|------|-------------|
| $\lambda_{pre}$ | $\mu_{pre}$ | tokens/s | Prefill tokens per second the replica can sustain (PPS). |
| $\lambda_{dec}$ | $\mu_{dec}$ | tokens/s | Decode (output) tokens per second the replica generates (GPS). |
| $\lambda$ = $\lambda_{req}$ | $\mu$ = $\mu_{RPS}$ | req/s | Request completions per second. |

At steady state with no queueing: $\mu_{pre} \geq \lambda_{pre}$,
$\mu_{dec} = \lambda_{dec}$, and $\mu = \lambda$.

These supply rates are **not constant**: they depend on the KV cache utilization
$KV\text{\\\%}$, which reflects how many requests are concurrently in flight.
The central goal of this document is to estimate each supply signal as a
function of $KV\text{\\\%}$.

---

## 2. The ITL Linear Model

### 2.1 Empirical observation

Empirical measurements on H100 hardware — **type-1 experiments** in which $IL$
and $OL$ are held fixed while RPS is increased to raise $KV\text{\\\%}$ — show
that below KV saturation ($KV\text{\\\%} \lesssim 80\text{\\\%}$), ITL is well
approximated by a **linear function of $KV\text{\\\%}$**:

$$\boxed{\text{ITL}(k) = A(w) \cdot k + B}$$

where $k = KV\text{\\\%} \in [0, 1]$, and:

- $B \approx 0.006\,\text{s}$ is the **hardware baseline**: the per-token decode
  latency at zero KV load. It is nearly independent of workload $w$ and reflects
  the minimum time to execute one decode iteration on the GPU (matrix multiply
  plus minimal attention over an empty cache).

- $A(w)$ is the **load sensitivity**: the additional ITL per unit of KV cache
  utilization. It depends on the workload $w$ and decreases as $OL$ increases
  (longer $OL$ → fewer concurrent requests at the same $KV\text{\\\%}$ → lower
  per-step attention cost):

| $IL$ | $OL$ | $A$ (s / KV fraction) | $B$ (s) | $R^2$ |
|------|------|----------------------|---------|-------|
| 5000 | 200  | 0.073                | 0.006   | 0.987 |
| 5000 | 300  | 0.060                | 0.006   | 0.988 |
| 5000 | 500  | 0.041                | 0.006   | 0.987 |
| 5000 | 1000 | 0.034                | 0.004   | 0.960 |
| 6000 | 100  | 0.121                | 0.007   | 0.993 |

Fits are computed only on unsaturated type-1 points ($KV\text{\\\%} < 80\%$,
RPS increasing at fixed $IL$/$OL$). Type-2 (increasing $IL$) and type-3
(increasing $OL$) experiments change the workload itself and produce different
apparent $A$ values; they are not used for supply calibration.

Empirical data shows the linear model continues to hold (or slightly
overestimates ITL) even above 80%: adding a $C \cdot k^2$ term to the fit
improves $R^2$ by less than 0.1% for all measured workloads. The quadratic
coefficient is negative or near zero ($C \in [-0.01, +0.01]$), so there is no
evidence of ITL accelerating beyond the linear trend at high load.

### 2.2 Mixed workloads

Under the steady-distribution assumption (TA-demand.md §2.2), the workload
mixture $\{\pi_w\}$ is stationary. The aggregate ITL observed on a replica
serving a mix of workloads is a weighted average of the per-bin ITLs. Since
each per-bin ITL is linear in $k$, the mixture average is also linear:

$$\text{ITL}(k) = \bar{A} \cdot k + B, \qquad
\bar{A} = \sum_{w \in \mathcal{W}} \pi_w \cdot A(w)$$

$B$ is shared across bins and drops out of the weighting. The linearity of
ITL in $KV\text{\\\%}$ therefore extends to mixed workloads as long as the
mixture is steady — the slope $\bar{A}$ shifts if $\{\pi_w\}$ shifts, but
at any fixed mixture the model holds.

### 2.3 Calibration from live observations

$A$ and $B$ are estimated from recent $(k, \text{ITL})$ observations at
**unsaturated** operating points ($k < 0.80$):

$$\hat{A}, \hat{B} = \arg\min_{A,B} \sum_i \bigl(\text{ITL}_i - A \cdot k_i - B\bigr)^2$$

**How many samples are needed?** KV% *spread* matters more than sample count.
Bootstrap experiments on H100 data (IL=5000, OL=200, 29 mid-range points):

| Points (random, spread ≥ 15%) | Mean \|ΔA\| | Mean \|ΔB\| | Expected GPS error at 75% |
|-------------------------------|------------|------------|--------------------------|
| 5  | 0.006 | 2.2 ms | ≈ 5–8% |
| 10 | 0.003 | 1.0 ms | ≈ 3–5% |
| 15 | 0.002 | 0.6 ms | ≈ 2–3% |
| 20 | 0.001 | 0.4 ms | ≈ 1–2% |

The critical requirement is **KV% spread ≥ 30–40%** (e.g., samples spanning
[20%, 60%]). Five well-spaced points covering that range achieve similar
accuracy to 15 randomly-drawn points. Samples clustered in a narrow KV% band
yield poor estimates of both $A$ and $B$ regardless of count.

**Practical rules for the rolling calibration window:**
- Keep the last 15–20 observations at $k < 0.80$.
- Require that the window spans at least 30% of KV% range before using the fit;
  otherwise fall back to the previous calibrated $A$ and the hardware default
  $B = 0.006\,\text{s}$.
- Exclude points at $k < 0.15$: the small $N_{dec}$ at low load makes ITL
  estimates noisy and they pull the intercept $B$ toward unreliable values.
- Trigger a full re-fit whenever $|\Delta\overline{OL}| > 20\%$ or
  $|\Delta\overline{IL}| > 20\%$ (workload shift changes $A$).

**Fallback (insufficient history):** fix $\hat{B} = 0.006\,\text{s}$ and
estimate $A$ from a single mid-range observation:
$\hat{A} = (\text{ITL}(k^*) - B) / k^*$.

---

## 3. Estimating $\mu_{dec}$ (GPS / Decode Supply)

### 3.1 $N_{dec}$ from KV% and workload averages

Instantaneous $N_{dec}$ is not exposed by any released vLLM version (see
TA-notation.md §3.2). For sufficiently long $OL$, the prefill phase is short
relative to the decode phase and at most one request is in prefill at any
time ($N_{pre} \approx 1$). In this regime $N_{dec} \approx N - 1 \approx N$
and the KV cache is dominated by decode-phase footprints.

Under these conditions, at steady state:

$$N_{dec}(k) \approx \frac{k \cdot KV_{max}}{\overline{KV}_{req}}$$

where $\overline{KV}_{req} = \overline{IL}_{eff} + \overline{OL}/2$ is the
time-averaged KV footprint per decode request (TA-notation.md §3.1),
$k = KV\text{\\\%}$, and $KV_{max}$ is
the total KV cache capacity in tokens.

This estimate is derived entirely from rate-averaged metrics — no instantaneous
counters are needed.

### 3.2 GPS as a function of $KV\text{\\\%}$

Substituting the linear ITL model (with coefficients $A$ and $B$ calibrated
in §2) and the KV%-derived $N_{dec}$:

$$\boxed{\mu_{dec}(k) = \frac{N_{dec}(k)}{\text{ITL}(k)}
= \frac{k \cdot KV_{max} / \overline{KV}_{req}}{A \cdot k + B}}$$

This is a **hyperbolic rational function** of $k$: GPS rises sub-linearly with
$KV\text{\\\%}$ across the full operating range and approaches an asymptotic
ceiling only at extreme load:

$$\mu_{dec}^{max} = \lim_{k \to \infty} \mu_{dec}(k) = \frac{KV_{max}}{A \cdot \overline{KV}_{req}}$$

At the practical saturation point $k = 0.80$, GPS reaches roughly 90–95% of
this ceiling (e.g., for $IL=5000$, $OL=200$: $\mu_{dec}(0.80) \approx 943\,\text{tok/s}$
vs. ceiling $\approx 1040\,\text{tok/s}$). GPS is therefore **still rising at 80%
KV%**, not flat — the increase is just decelerating. The curve is concave from
below throughout the operating range; there is no plateau within it.

The crossover $k \sim B/A \approx 0.006/0.06 = 10\%$ marks where the numerator's
linear growth begins to be noticeably limited by the denominator — not a plateau,
but the transition from near-linear to clearly sub-linear growth.

### 3.3 Supply at the target operating point $k_{sat}$

With the same calibrated $\hat{A}$ and $\hat{B}$ from §2, the expected GPS at
any target $KV\text{\\\%} = k_{sat}$ is:

$$\mu_{dec}^{sat} = \frac{k_{sat} \cdot KV_{max} / \overline{KV}_{req}}{\hat{A} \cdot k_{sat} + \hat{B}}$$

This is the **per-replica supply capacity** used by the autoscaler to estimate
how much decode demand a new replica can absorb at steady state.

### 3.4 Verification against observed GPS

When GPS is directly observable (as a Prometheus rate counter, §7.2), the model
can be verified at the current operating point $k^*$:

$$\text{GPS}_{obs}(k^*) \approx \mu_{dec}(k^*)$$

**At low load ($KV\text{\\\%} \lesssim 15\%$)**, errors of 10–20% are expected
even with a well-calibrated model. Two compounding causes:

1. **Small $N_{dec}$**: with only 4–7 requests in flight, the rate-window
   averages $\overline{OL}$ and $\overline{IL}$ are computed over a small sample
   and carry high variance, making the $kv\text{\_per\_req}$ estimate noisy.
2. **Small absolute ITL**: at low $k$, ITL $\approx B \approx 0.006\,\text{s}$.
   A small absolute error in $B$ (e.g., 0.001 s) is a large relative error
   ($\sim$15%) in ITL and therefore in GPS.

At moderate to high load ($KV\text{\\\%} \gtrsim 30\%$) the model consistently
tracks observed GPS within 5–10% on type-1 experiments (fixed $IL$/$OL$,
increasing RPS). Errors above 15% at higher load indicate either a workload
shift ($\overline{OL}$ or $\overline{IL}$ changed) or that the system is not
yet at steady state.

---

## 4. Estimating $\mu_{pre}$ (PPS / Prefill Supply)

### 4.1 Why $\mu_{pre}$ is not an independent constraint for long-output workloads

Unlike $\mu_{dec}$, prefill supply does not impose a separate bottleneck for
workloads with moderate-to-long output ($\overline{OL} \gtrsim 150$). In
vLLM's scheduler, one new request can be admitted per decode step — an
admission slot opens roughly once per $\text{ITL}(k)$ seconds. The resulting
admission-limited prefill capacity is:

$$\mu_{pre,cap}(k) \approx \frac{\overline{IL}_{eff}}{\text{ITL}(k)}
= \frac{\overline{IL}_{eff}}{A \cdot k + B}$$

Comparing to the actual prefill demand at steady state
($\lambda_{pre} = \lambda \cdot \overline{IL}_{eff}$,
$\lambda = N_{dec}(k) / (\overline{OL} \cdot \text{ITL}(k))$):

$$\frac{\mu_{pre,cap}(k)}{\lambda_{pre}(k)} = \frac{\overline{OL}}{N_{dec}(k)}
= \frac{\overline{OL} \cdot \overline{KV}_{req}}{k \cdot KV_{max}}$$

For $\overline{OL} \geq 200$ and $k \leq 1$ this ratio is well above 1 across
the operating range (e.g., $IL=5000$, $OL=200$: ratio $\approx 2.6/k$).
The prefill capacity constraint never binds before the KV / decode constraint.
$\mu_{pre}$ tracks $\lambda_{pre}$ in steady state, and both saturate at the
same KV% where $\mu_{dec}$ saturates.

### 4.2 The TTFT knee for short-output and heavy-prefill workloads

For short-output workloads ($\overline{OL} \lesssim 150$) or heavy-prefill
workloads (large $\overline{IL}$), TTFT degrades significantly **before** the
KV cache fills. This constitutes an independent supply-side saturation event
that the $\mu_{dec}$ model alone cannot capture.

**Mechanism.** TTFT decomposes into a hardware prefill cost, an admission wait,
and one decode step:

$$\text{TTFT} = T_{pre} + W_{vllm} + \text{ITL}$$

$T_{pre}$ is roughly $\overline{IL}_{eff} / \mu_{pre,cap}^{hw}$ — the hardware
prefill cost at low load (≈ 30–50 ns/token on H100, approximately constant
for $\overline{IL} \lesssim 10\text{K}$). $W_{vllm}$ is the time spent waiting
for an admission slot, which grows when the arrival rate approaches the
completion rate:

$$W_{vllm} \gg 0 \quad \Longleftrightarrow \quad \lambda \gtrsim \mu_{RPS}(k)
= \frac{k \cdot KV_{max}}{\overline{KV}_{req} \cdot \overline{OL} \cdot (A \cdot k + B)}$$

Because $\overline{OL}$ appears in the denominator of $\mu_{RPS}$, short-output
workloads saturate at lower KV%: fewer tokens per completion means fewer KV
slots freed per completion, so the system reaches $\lambda \approx \mu_{RPS}$
earlier.

**Empirical evidence (H100, type-1 experiments):**

| $\overline{IL}$ | $\overline{OL}$ | TTFT knee KV% | $N_{dec}$ at knee | Admission wait at knee |
|----------------|----------------|--------------|------------------|----------------------|
| 5000 | 500 | ≈ 67% | ≈ 49 | ≈ 11 decode steps |
| 5000 | 200 | ≈ 58% | ≈ 44 | ≈ 11 decode steps |
| 6000 | 100 | ≈ 23% | ≈ 15 | ≈ 11 decode steps |

The admission wait at the knee is consistent across workloads (≈ 10–11 decode
steps, ≈ 400–500 ms). At KV%=23% for OL=100, the KV cache is 77% empty —
space is not the constraint. The constraint is that completions arrive too
slowly to keep pace with new arrivals.

For heavy-prefill workloads in type-2 experiments (fixed low RPS, increasing
$IL$), a multiplicative instability appears above a threshold $IL$: large $IL$
increases $\overline{KV}_{req}$, which raises $N_{dec}$ per unit KV%, which slows
completions, which extends $W_{vllm}$, which further degrades TTFT. On H100
at RPS=2 with $OL=300$, TTFT is dominated by $W_{vllm}$ above $IL \approx 11\text{K}$,
where the effective $\mu_{pre}$ collapses from ≈ 20K tok/s to ≈ 4K tok/s.

**Predicting the knee.** Setting $\lambda = \mu_{RPS}(k)$ and solving for
$k_{knee}$:

$$k_{knee} = \frac{\lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot B}
{KV_{max} - \lambda \cdot \overline{KV}_{req} \cdot \overline{OL} \cdot A}$$

This gives the KV% at which TTFT begins to degrade. For short-output workloads,
$k_{knee}$ is the relevant scale-up threshold; it may be substantially lower
than the decode-saturation threshold $k_{sat}$.

### 4.3 Measuring $\mu_{pre,cap}$ when a small queue is present

When $W_{vllm}$ is small but non-zero (2–5 waiting requests), the system is
operating right at the rate-balance point $\lambda \approx \mu_{RPS}(k)$.
This is a valuable measurement opportunity: $W_{vllm}$ is still small, so
$\text{TTFT} \approx T_{pre} + \text{ITL}$ and the observed TTFT provides a
clean estimate of the hardware prefill cost:

$$\hat{T}_{pre} \approx \text{TTFT}_{obs} - \text{ITL} \quad \text{(when } W_{vllm} = 2\text{–}5\text{)}$$

$$\hat{\mu}_{pre,cap} = \frac{\overline{IL}_{eff}}{\hat{T}_{pre}}
\quad [\text{tokens/s}]$$

The portable quantity is $T_{pre} / \overline{IL}_{eff}$ (seconds per token,
or equivalently ns/token), which reflects the hardware prefill throughput and
is independent of $\lambda$ and $k$ as long as the queue is small. On H100,
$T_{pre} / \overline{IL}_{eff} \approx 30\text{–}50\,\text{ns/tok}$ for
$\overline{IL} \lesssim 10\text{K}$.

When a deployment with known hardware has been measured once at small-queue
conditions, $\hat{T}_{pre} / \overline{IL}_{eff}$ can be reused to predict
$k_{knee}$ for any new workload on the same hardware:

$$T_{pre}(w) \approx \frac{\hat{T}_{pre}}{\overline{IL}_{eff,ref}} \cdot \overline{IL}_{eff}(w)$$

$$k_{knee}(w) = \frac{\lambda \cdot \overline{KV}_{req}(w) \cdot \overline{OL}(w) \cdot B}
{KV_{max} - \lambda \cdot \overline{KV}_{req}(w) \cdot \overline{OL}(w) \cdot A}$$

If $T_{pre}$ is directly observable (`vllm:request_prefill_time_seconds`,
§8.2), these estimates can be updated continuously without waiting for a
small-queue event.

### 4.4 Observable $\mu_{pre}$ and what it signals

In steady state with no vLLM waiting queue ($W_{vllm} = 0$):
$\mu_{pre} = \lambda_{pre}$ — a balance condition, not a capacity measurement.

**Direct measurement (preferred, when collected):**

$$\mu_{pre,v} = \text{rate}(\texttt{vllm:request\_prompt\_tokens\_sum}[\Delta t]) \cdot (1 - H\text{\\\%}_v)$$

**From $N_{pre}$ and $T_{pre}$ (when $T_{pre}$ is collected):**

$$N_{pre,v} \approx N_v - N_{dec,v}, \qquad
\mu_{pre,v} \approx \frac{N_{pre,v} \cdot \overline{IL}_{eff,v}}{T_{pre,v}}$$

where $T_{pre}$ is available from `vllm:request_prefill_time_seconds` in
vLLM ≥ v0.7.3 with the V1 engine (TA-notation.md §8).

---

## 5. Estimating $\mu$ (RPS / Request Completion Rate)

### 5.1 Little's Law for the full system

The RPS supply is obtained by applying Little's Law to the full in-flight
population. At operating point $k$, with $N_{pre} \approx 1$ (non-chunked
prefill) and $N_{dec}(k)$ given by §3.1:

$$N(k) = N_{dec}(k) + 1 = \frac{k \cdot KV_{max}}{\overline{KV}_{req}} + 1$$

Each request spends $E2E(k) = T_{pre}(k) + \overline{OL} \cdot \text{ITL}(k)$
in the system (at steady state, $W_{epp} = W_{vllm} = 0$). The scheduler
concurrency limit $N_{max}$ caps the total in-flight count. Therefore:

$$\boxed{\mu_{RPS}(k) = \frac{\min\!\bigl(N(k),\; N_{max}\bigr)}{T_{pre}(k) + \overline{OL} \cdot (A \cdot k + B)}}$$

### 5.2 When this reduces to the decode-only formula

The ratio of $\mu_{RPS}$ to the decode-only estimate $\mu_{RPS}^{dec} = N_{dec}/T_{dec}$
(when $N(k) < N_{max}$) is:

$$\frac{\mu_{RPS}}{\mu_{RPS}^{dec}} = \frac{N_{dec}+1}{N_{dec}} \cdot \frac{T_{dec}}{T_{pre} + T_{dec}}
\approx \frac{T_{dec}}{T_{pre} + T_{dec}}
\quad \text{for large } N_{dec}$$

This correction is negligible when $T_{pre} \ll T_{dec}$, i.e., when:

$$T_{pre} \ll \text{ITL}(k) \cdot \frac{\overline{OL}}{N_{dec}(k)}$$

**Non-chunked prefill** ($B_{max} \gg \overline{IL}_{eff}$): $T_{pre} \approx
\overline{IL}_{eff} \cdot t_{pre/tok}$ is constant and small (≈ 0.2 ms for
$IL=5000$; threshold ≈ 200 ms). Correction $\approx 0.002\%$ — negligible.
$\mu_{RPS}$ reduces to $\mu_{RPS}^{dec}$.

**Chunked prefill** ($B_{max} < \overline{IL}_{eff}$): $T_{pre}(k) =
\lceil \overline{IL}_{eff}/B_{max} \rceil \cdot \text{ITL}(k)$ grows with $k$.
Once $\lceil \overline{IL}_{eff}/B_{max} \rceil > \overline{OL}/N_{dec}(k)$,
the E2E correction is substantial and the full formula is required.

**Operating above the knee** ($k > k_{knee}$): $W_{vllm} > 0$ inflates $E2E$
beyond $T_{pre} + T_{dec}$, reducing effective throughput. This signals an
ill-chosen operating point rather than a supply property — the autoscaler
should use $k_{threshold} = \min(k_{knee}, k_{sat})$ to avoid this regime.

### 5.3 The $N_{max}$ cap

The cap $N_{max}$ binds when the KV cache would otherwise sustain more
concurrent requests than the scheduler allows:

$$k_{N_{max}} = \frac{N_{max} \cdot \overline{KV}_{req}}{KV_{max}}$$

For $k < k_{N_{max}}$: KV cache fills before the batch saturates; the $N(k)/E2E$
formula applies and $\mu_{RPS} \approx \mu_{RPS}^{dec}$.
For $k \geq k_{N_{max}}$: $N_{max}$ is hit first; $\mu_{RPS} = N_{max}/E2E(k)$.

### 5.4 Supply at the target operating point

$$\mu^{sat}_{RPS} = \frac{\min\!\bigl(N(k_{sat}),\; N_{max}\bigr)}{T_{pre}(k_{sat}) + \overline{OL} \cdot (A \cdot k_{sat} + B)}$$

For the typical case ($N(k_{sat}) < N_{max}$, non-chunked prefill):

$$\mu^{sat}_{RPS} \approx \frac{\mu_{dec}^{sat}}{\overline{OL}}$$

When `vllm:request_success_total` or `vllm:request_decode_time_seconds` is
collected (not yet in WVA), RPS can be measured directly as a counter rate.

---

## 6. Calibration Procedure

The ITL model $\text{ITL}(k) = A \cdot k + B$ must be calibrated per variant $v$
and updated as the workload mix $\{\pi_w\}$ shifts. The procedure is:

1. **Collect** $(k_i, \text{ITL}_i)$ pairs from recent observations at
   $KV\text{\\\%} \in (0.15, 0.80)$ (at least 5 points spanning ≥ 30% KV% range;
   ideally 15–20 points spanning 20%–70%).
   Use the rate-averaged `AvgITL` and `KvCacheUsage` fields — no instantaneous
   metrics are needed.

2. **Fit** $\hat{A}$ and $\hat{B}$ by ordinary least squares (§2.3). If the
   window does not span ≥ 30% KV% range, retain the previous coefficients and
   refresh $\hat{B}$ from the hardware default only.

3. **Predict** $\text{ITL}(k_{sat})$ and $\mu_{dec}^{sat}$ using §3.3.

4. **Verify** the fit against observed GPS at the current $k^*$ using §3.4.
   Recalibrate if the error exceeds 15%.

5. **Cross-validate before deploying** (recommended for new deployments):
   follow the procedure in §7.2. If GPS predictions are within 10% at
   $k \in [0.70, 0.80]$, the calibration is reliable for extrapolating
   $\mu_{dec}^{sat}$ at $k_{sat} = 0.75\text{–}0.80$.

6. **Update** periodically (e.g., every 5–10 minutes) or whenever the workload
   mix shifts detectably (e.g., $|\Delta\overline{IL}| > 20\%$ or
   $|\Delta\overline{OL}| > 20\%$).

---

## 7. Model Validation

This section describes how to verify the supply estimation model as new
experimental data becomes available. Validation has two levels: **point-in-time
consistency** (does the current model agree with what is observable right now?)
and **predictive accuracy** (can unsaturated observations predict GPS at higher
load?). The second is the harder and more important test.

### 7.1 Point-in-time consistency check

At any operating point $k^*$ where the replica is not saturated, the GPS
predicted by the model should match the directly-observed GPS (when the
`vllm:request_generation_tokens_sum` rate counter is available):

$$\text{error}_{GPS} = \frac{\mu_{dec}(k^*) - \text{GPS}_{obs}(k^*)}{\text{GPS}_{obs}(k^*)}$$

**Expected thresholds** from H100 data:
- $k^* \in [0.15, 0.70]$: error within ±5–10%. Larger errors indicate stale
  $(A, B)$ or a workload shift.
- $k^* < 0.15$: errors of 10–20% are normal due to small $N_{dec}$ and noisy
  rate-window averages; do not recalibrate based on low-load observations alone.
- $k^* > 0.70$: errors up to ±6% are acceptable; see predictive test (§7.2).

### 7.2 Predictive accuracy test (cross-validation)

The autoscaler uses the model to predict supply at $k_{sat}$ from observations
at lower $k$ — a true out-of-sample prediction. To verify this capability:

**Test procedure:**

1. Collect a type-1 dataset: fix $IL$ and $OL$, sweep RPS to cover
   $KV\text{\\\%}$ from ≈20% to ≈85%.
2. **Split:** training set $k < 0.70$, test set $k \in [0.70, 0.85]$.
3. **Fit** $(A, B)$ on the training set only.
4. **Predict** $\mu_{dec}$ at each test point using the fitted model and the
   $N_{dec}(k)$ formula.
5. **Compare** to observed GPS at those points.

**Acceptance criterion:** GPS prediction error ≤ 10% at all test points
($k \in [0.70, 0.85]$). The model is then trustworthy for extrapolating
$\mu_{dec}^{sat}$ at $k_{sat} = 0.75\text{–}0.80$.

**Reference results from H100 experiments** (type-1 data, training on $k < 0.70$):

| Workload | $n_{train}$ | ITL mean error | GPS error at 80% | GPS max error |
|----------|------------|---------------|-----------------|--------------|
| IL=5000, OL=200 | 43 | +5.1% | −4.6% | −5.8% |
| IL=6000, OL=100 | 17 | −4.3% | −2.1% | −12.9% |

Both workloads pass the 10% criterion. ITL prediction bias of +5% for OL=200
(model slightly overestimates ITL at high load) causes a corresponding
−5% GPS bias — conservative, meaning the model predicts slightly less supply
than is actually available, which is the safe direction for autoscaling.

**Signs of a failing test:**

| Symptom | Likely cause |
|---------|-------------|
| GPS errors > 15% at all test points | Wrong $\overline{KV}_{req}$ (stale $\overline{OL}$ or $\overline{IL}$) |
| GPS over-predicted (model > obs by 20%+) | Mixed experiment types in training data; recollect type-1 only |
| ITL predictions good but GPS predictions bad | $KV_{max}$ estimate is wrong; verify via `cache_config_info` labels |
| Errors larger for OL=100 than OL=500 | $N_{pre} \approx 1$ assumption breaks for short OL; use $T_{pre}$ to correct |

### 7.3 What new experiments to run

As new hardware or model configurations are deployed, run these experiments
in priority order to validate and anchor the model:

1. **Type-1 sweep** (essential): fix $(IL, OL)$ representative of the target
   workload, sweep RPS from near-zero to saturation (KV% > 80%). Collect at
   least 15 stable operating points. This calibrates $(A, B)$ and enables the
   §7.2 cross-validation.

2. **Type-1 multi-workload** (validates $\bar{A}$ mixing): run the same RPS
   sweep for 3–4 $(IL, OL)$ combinations. Confirm that $B$ is consistent
   across workloads (should be ≤ 0.002 s apart on the same hardware) and that
   $A$ decreases with increasing $OL$ as the table in §2.1 shows.

3. **Mixed-workload type-1** (validates the $\pi_w$-weighted $\bar{A}$ formula):
   run with two workload types simultaneously at a known mixture. Compare the
   observed aggregate $A$ to $\sum_w \pi_w A(w)$ computed from the individual
   fits. The error should be < 10%.

4. **Linearity check above 80%** (validates caveat §9.2): push a type-1
   experiment to KV% > 85% if the hardware allows. Compare ITL residuals against
   the linear fit. If a systematic positive residual appears at high KV%, add a
   $C \cdot k^2$ term and report the workload and hardware where it was observed.

5. **Rolling calibration test** (validates §6 in production): log the rolling
   $(A, B)$ estimates over several hours of real traffic. Verify that (a) the
   coefficients are stable during steady workload, (b) they shift within 1–2
   calibration cycles when the workload mix changes, and (c) the GPS prediction
   error stays below 15% throughout.

---

## 8. Metric Sources

### 8.1 Currently collected (sufficient for full $\mu_{dec}$ model)

| Symbol | Go Field | Prometheus Metric |
|--------|----------|------------------|
| $KV\text{\\\%}_v$ | `KvCacheUsage` | `vllm:kv_cache_usage_perc` |
| $KV_{max,v}$ | `TotalKvCapacityTokens` | `num_gpu_blocks × block_size` |
| $N_v$ | `RunningRequests` | `vllm:num_requests_running` |
| $\overline{IL}_{eff,v}$ | `AvgInputTokens × (1 - PrefixCacheHitRate)` | derived |
| $\overline{OL}_v$ | `AvgOutputTokens` | `rate(generation_tokens_sum/count)` |
| $\text{ITL}_v$ | `AvgITL` | `rate(time_per_output_token_seconds_sum/count)` |
| $H\text{\\\%}_v$ | `PrefixCacheHitRate` | `rate(prefix_cache_hits/queries)` |

The full $\mu_{dec}(k)$ model (§3.2–§3.3) requires only these fields plus a
calibrated $(A, B)$ pair.

### 8.2 High-priority additions (enable direct verification and $\mu_{pre}$)

| Symbol | Prometheus Metric | Why needed |
|--------|------------------|------------|
| $\mu_{dec,v}$ (GPS rate) | `rate(vllm:request_generation_tokens_sum[5m])` | Direct GPS for model verification (§3.4, §7.1) |
| $\mu_{pre,v}$ (PPS rate) | `rate(vllm:request_prompt_tokens_sum[5m])` | Direct PPS without $N_{pre}$ estimate |
| $T_{pre,v}$ | `vllm:request_prefill_time_seconds` (vLLM ≥ v0.7.3, V1) | Separates prefill compute from queue wait |
| $T_{dec,v}$ | `vllm:request_decode_time_seconds` (vLLM ≥ v0.7.3, V1) | Direct RPS cross-check: $\mu_v = \text{rate}(T_{dec}\text{ count})$ |

All four are available in llm-d v0.5.0 (vLLM v0.14.1, V1 engine).

---

## 9. Summary

```
# ITL model calibration (per replica v, from rate-averaged history)
# Fit on unsaturated observations: kv_i < 0.80, itl_i = AvgITL at that time
A, B = lstsq_fit(kv_samples, itl_samples)   # ITL = A*k + B
# Fallback: B = 0.006, A = (AvgITL - B) / KvCacheUsage

# N_dec estimate (decode-dominated: N_pre ~ 1)
kv_per_req  = AvgInputTokens*(1 - PrefixCacheHitRate) + AvgOutputTokens/2  # = KV_req_bar
N_dec       = KvCacheUsage * TotalKvCapacityTokens / kv_per_req

# Current GPS estimate
μ_dec       = N_dec / AvgITL                    # [tokens/s]
μ           = μ_dec / AvgOutputTokens           # [req/s]

# Supply at target KV% = k_sat (e.g. 0.75)
N_dec_sat   = k_sat * TotalKvCapacityTokens / kv_per_req
ITL_sat     = A * k_sat + B
μ_dec_sat   = N_dec_sat / ITL_sat               # [tokens/s]
μ_sat       = μ_dec_sat / AvgOutputTokens       # [req/s]

# Maximum sustainable GPS (plateau value)
μ_dec_max   = TotalKvCapacityTokens / (A * kv_per_req)

# Verification (when GPS rate is collected)
gps_obs     = rate(vllm:request_generation_tokens_sum[5m])
gps_err_pct = abs(μ_dec - gps_obs) / gps_obs * 100  # recalibrate if > 15%

# TTFT knee for short-output / heavy-prefill workloads (§4.2)
# k_knee is the KV% where TTFT starts to degrade; may be << k_sat for short OL
denom = KV_max - ArrivalRate * kv_per_req * AvgOutputTokens * A
k_knee = (ArrivalRate * kv_per_req * AvgOutputTokens * B) / denom  # 0 if denom <= 0

# μ_pre_cap from small-queue measurement (§4.3)
# Measure when W_vllm = 2-5: TTFT ≈ T_pre + ITL (W_vllm still small)
T_pre_hat      = AvgTTFT - AvgITL                    # seconds, only valid when queue is small
t_pre_per_tok  = T_pre_hat / AvgInputTokens          # s/tok (portable hardware constant)
μ_pre_cap      = AvgInputTokens * (1 - PrefixCacheHitRate) / T_pre_hat  # [tokens/s]

# Effective scale-up threshold (use lower of TTFT knee and decode saturation)
k_threshold = min(k_knee, k_sat)  # if k_knee is valid (denom > 0)
```

---

## 10. Caveats and Limitations

1. **$N_{pre} \approx 1$ requires long $OL$.** For short-output workloads
   ($OL \lesssim 100$), multiple requests may be in prefill simultaneously and
   $N_{dec}$ is no longer a good approximation for $N$. In this regime, $T_{pre}$
   data is needed to separate $N_{pre}$ from $N_{dec}$.

2. **The linear ITL model holds at least to $KV\text{\\\%} \approx 85\%$.** Fitting
   a quadratic term $C \cdot k^2$ to H100 data improves $R^2$ by less than
   0.1% for all measured workloads (OL = 100, 200, 500), and the fitted $C$ is
   near zero or negative. Residuals at KV% > 70% are within ±2–6 ms of the
   linear prediction. The linear model is therefore sufficient through the
   practical operating range; there is no evidence it underestimates ITL near
   saturation. Extrapolation beyond $k = 0.90$ (very close to capacity) is
   untested and should be treated with caution.

3. **GPS rises throughout the operating range; there is no plateau.** The
   $\mu_{dec}(k)$ curve is concave from below and approaches its ceiling
   asymptotically. At 80% KV%, GPS is typically at 90–95% of the ceiling, so
   the increment from 60% to 80% is small but non-zero. Do not treat GPS as
   constant above any finite $KV\text{\\\%}$.

4. **Low-load GPS estimates are less reliable.** At $KV\text{\\\%} \lesssim 15\%$,
   $N_{dec} \approx 4\text{–}7$, making rate-window averages noisy and absolute
   ITL errors (in $B$) proportionally large. Use low-load observations only
   as soft sanity checks, not as primary calibration data.

5. **Only type-1 experiments (fixed $IL$/$OL$, increasing RPS) are relevant for
   supply calibration.** Type-2 (increasing $IL$) and type-3 (increasing $OL$)
   experiments change the workload itself and produce different apparent $A$
   values; they should not be mixed with type-1 data when fitting $A$ and $B$.

6. **$A$ depends on the workload mix $\{\pi_w\}$.** If the mix shifts (e.g.,
   a surge of long-batch requests), $\bar{A}$ changes and the calibrated model
   becomes stale. The update trigger in §6 step 6 guards against this.

7. **$KV_{max}$ is not in Prometheus metrics.** It is derived from
   `vllm:cache_config_info` labels (`num_gpu_blocks × block_size`), which are
   static labels collected by the WVA collector. The H100 reference value
   is approximately 390K tokens.

8. **All rate metrics are trailing averages.** ITL and $\overline{OL}$ are
   computed over 1–5 minute windows. Supply estimates lag actual conditions
   during rapid workload changes — a deliberate trade-off for stability.

9. **The TTFT knee is the relevant saturation threshold for short-output workloads.**
   For $\overline{OL} \lesssim 150$, $k_{knee}$ (§4.2) may be as low as 20–30%
   KV%, far below the decode-saturation threshold $k_{sat} \approx 75\text{–}80\%$.
   Using $k_{sat}$ as the scale-up trigger for these workloads means the
   autoscaler reacts too late — TTFT SLO violations occur well before GPS
   saturation. Scale-up decisions should use $\min(k_{knee}, k_{sat})$ as the
   effective threshold.

10. **$T_{pre}$ grows super-linearly for very large $\overline{IL}$.** For
    $\overline{IL} \gtrsim 10\text{K}$ (at low RPS), the admission wait dominates
    TTFT and the observed $\text{TTFT} / \overline{IL}_{eff}$ ratio grows rapidly
    rather than staying constant. The $\hat{T}_{pre}$ measurement (§4.3) is only
    a clean hardware-compute estimate when $W_{vllm}$ is small (2–5). If
    $W_{vllm}$ is already large, the observed TTFT over-estimates $T_{pre}$ and
    $\hat{\mu}_{pre,cap}$ will be under-estimated.

11. **Chunked prefill changes $T_{pre}$ under load.** With `max_num_batched_tokens`
    $= B_{max} < \overline{IL}_{eff}$, each request requires
    $\lceil \overline{IL}_{eff} / B_{max} \rceil$ prefill chunks, each interleaved
    with a decode step. The effective $T_{pre}(k) \approx \lceil IL/B_{max} \rceil
    \cdot \text{ITL}(k)$ grows with $k$, making $\mu_{pre,cap}(k)$ decrease faster
    than §4.1 predicts. The H100 data in this document used
    $B_{max} = 65\text{K} \gg IL$ (no chunking); deployments with smaller
    $B_{max}$ will see the TTFT knee at lower KV% and should re-measure
    $\hat{T}_{pre}$ accordingly.
