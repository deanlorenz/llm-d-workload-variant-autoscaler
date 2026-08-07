# staircase-20260807-armB — findings

What this run actually showed, separated from what the panels can display. Everything below is
measured off the bundle or the raw scrapes; nothing is inferred from the plan's model. Where a
claim is an association with a plausible mechanism rather than a demonstrated cause, it says so.

**Source.** `benchmark/dean-20260807-210058-612/results/inference-perf-1786125698-ptufog_1`
→ `real-trace/staircase-20260807-armB/{bundle.json,coverage.json,panels.png}`.
7920 requests, 0 failures, 7919 with complete per-request timing. Two pods maximum. Coverage
13 PASS / 3 FAIL (the three failures are `Trust B`, `Exercise the 0.85 ceiling`,
`rho model valid at top` — all "not supported by this run", not defects).

**Reproduce:** `./.venv/bin/python render_real_trace.py --bundle real-trace/staircase-20260807-armB/bundle.json`

**Windows used throughout.** Chosen to give a clean 2×2 of {1 pod, 2 pods} × {saturated, not}:

| window | t (s, engine-relative) | pods | median `kv` |
|---|---|---|---|
| low 1 | 60–330 | 1 | 0.211 |
| mid-A | 378–532 | 1 | 0.998 (max 1.000) |
| mid-B | 545–700 | 2 | 0.995 / 0.992 |
| low 2 | 760–1050 | 2 | 0.090 / 0.097 |

Pod `…7p7mt`: 83 scrapes, t+0…1287. Pod `…s948g`: 28 scrapes, t+502…927, first `run > 0` at
t+534. **Median scrape cadence is 16.0 s for both**, so Nyquist puts a floor of 32 s on anything
resolvable from the per-pod gauges — the 24 s structure below is only visible in the per-request
trace, never in the scrapes.

---

## 1. A 24 s oscillation in departures, admissions and ITL — saturation-gated

Peak autocorrelation of **departure counts** on 2 s bins:

| window | pods | saturated | peak autocorr | CV |
|---|---|---|---|---|
| low 1 | 1 | no | +0.14 @ 28 s | 0.34 |
| **mid-A** | **1** | **yes** | **+0.56 @ 24 s** | **0.81** |
| **mid-B** | **2** | **yes** | **+0.66 @ 24 s** | **0.63** |
| low 2 | 2 | no | +0.24 @ 26 s | 0.32 |

The wave tracks `kv`, not pod count. It is present at full strength in the **single-pod** window,
where routing has no degrees of freedom — so **routing is not the cause.** (Dean's initial
hypothesis; ruled out here.)

It is born at **admission**, not arrival. Arrivals stay Poisson-ish in every window (r ≈ +0.05 at
20 s, CV 0.19–0.25). Admissions (`t_arr + ttft`) reach +0.80 @ 24 s in the saturated windows only.
The engine's admission scheduler creates the clustering; the load generator does not deliver it.

**Mean ITL oscillates at the same period.** Detrending mean `itl_true` per 2 s bin against a 40 s
moving mean:

| window | residual sd | peak autocorr |
|---|---|---|
| low 1 | 6.1 % | +0.16 @ 28 s |
| **mid-A** | **9.5 %** | **+0.52 @ 24 s** (+0.73 @ 46 s, the harmonic) |
| **mid-B** | **12.3 %** | **+0.52 @ 24 s** |
| low 2 | 5.6 % | +0.17 @ 38 s |

**The period equals the decode duration.** Mid-stage median decode duration is **23.6 s** against a
24 s period — a 2 % match.

### The loop

1. A cohort of KV slots frees together.
2. The freed slots admit the next cohort together → a **burst of prefills**.
3. The prefill burst steals decode steps (§2), so ITL rises ~40 % **for the whole in-flight batch
   at once** and decode throughput drops.
4. Because every in-flight request slows by the same factor, their finish times are pushed out
   *together* — which re-tightens the cohort.
5. → 1.

Step 3–4 is the part that matters: cohort recycling alone would decay, because any jitter spreads
the cohort. Prefill contention supplies a **restoring force** that re-phase-locks it each cycle.

### What the workload contributes

`out_tok` CV is 0.036–0.046 in **every** window, saturated or not, so near-monodisperse output
cannot by itself produce the wave — saturation is the gate. What monodispersity does is let the
wave *survive* a decode pass: a period-`T` wave through a Gaussian kernel of width σ retains
`exp(−2π²σ²/T²)`.

| σ_decode | retained at T = 24 s |
|---|---|
| 0.84 s (measured, mid) | **96.6 %** |
| CV 0.25 | 18.6 % |
| CV 0.5 (mixed chat) | 0.12 % |

Measured σ_decode by window: 0.38 s (low 1), 1.64 s (mid), 0.33 s (low 2); median ITL 16.0 / 45.6 /
13.6 ms.

> **Caveat on the counterfactual.** That table is a *passive smearing* calculation — it assumes
> nothing re-synchronizes the cohort. The loop above says something does. So the defensible claim
> is that a mixed-length workload would **attenuate** this, not that it would erase it. Earlier
> drafts of this analysis said "a real workload would flatten it out"; that overstated the
> evidence. What is safe to write in a deck: *this run's near-monodisperse workload amplifies the
> oscillation, so read the amplitude as a property of the workload rather than of vLLM.*

---

## 2. Inside saturation, prefill contention — not concurrency — is the dominant ITL term

Dean's mechanism: a burst of traffic triggers prefill saturation, which degrades ITL for everyone
until the prefills drain, then ITL recovers. Confirmed on the engine's own histogram deltas.

Twenty stable intervals sit at `run` 170–198 with `kv ≈ 0.99` — same concurrency, same saturation.
Sorted by decode throughput, the ordering tracks prompt-token rate almost monotonically:

```
run=172 kv=0.991 gen=4994  prompt= 5631  itl=38.1  preempt=2.25
run=173 kv=0.998 gen=4922  prompt=11214  itl=39.8
run=182 kv=0.999 gen=4645  prompt= 7950  itl=38.8
run=183 kv=0.997 gen=3970  prompt=20755  itl=49.5
run=185 kv=0.999 gen=3575  prompt=23604  itl=55.2
run=195 kv=0.999 gen=2915  prompt=23177  itl=63.4
run=198 kv=0.995 gen=2590  prompt=23197  itl=71.2  preempt=0.44
```

Decode throughput spans **1.93×** and ITL spans 38 → 71 ms **at fixed concurrency.**

Regressions on the stable intervals (`itl_ms`, OLS with intercept, `prompt` in 1000 tok/s):

| interval set | n | concurrency only | + prompt rate | Δr² |
|---|---|---|---|---|
| all | 81 | r² 0.922 | r² 0.944 | +0.022 |
| **kv ≥ 0.85** | **21** | **r² 0.642** | **r² 0.878** | **+0.236** |
| kv < 0.85 | 60 | r² 0.859 | r² 0.879 | +0.020 |

- In-band coefficient **+1.087 ms per 1000 prompt tok/s** → **+19.5 ms** across the observed
  5 631–23 604 tok/s range, on a 48.5 ms base. A ~40 % ITL swing from prefill pressure alone.
- Below the band the coefficient goes slightly **negative** (−0.343) and Δr² collapses to +0.02.
  **The effect is saturation-specific**, exactly as described.
- Omitting the prefill term **inflates the apparent concurrency slope 1.8×** in-band:
  0.716 → 0.403 ms/req.

This is the same mechanism the plan already names in §7.1 ("prefill chunks stealing decode steps"),
now quantified and shown to be periodic.

---

## 3. Correction: preemption is **not** what makes throughput fall past the knee

Plan §5.3 attributes the post-knee throughput decline to preemption, and §7.2 lists that as one of
preemption's three consequences. On the [ref] run those were binned by `run`, where preemption and
concurrency co-move. Arm B separates them, and the sign is wrong for preemption.

Matched-concurrency subset (`run` 170–198, `kv ≥ 0.85`, n=20; `preempt/s` spans 0.44–2.88):

| | corr with `gen_tok_s` |
|---|---|
| prompt tok/s | **−0.876** |
| `run` | −0.896 |
| **preempt/s** | **+0.766** ← wrong sign |
| corr(prompt, preempt) | −0.607 |

Nested fits of `gen_tok_s`:

| model | r² |
|---|---|
| `run` | 0.802 |
| `run` + preempt | 0.808 (**+0.006**) |
| **`run` + prompt** | **0.908 (+0.106)** |
| `run` + prompt + preempt | 0.912 |

Same picture for ITL: `run` 0.732 → +preempt 0.744 → **+prompt 0.875**.

Throughput is *higher* when preemption is higher, because preemption peaks in the decode-heavy half
of the cycle (batch full of decoding requests, KV tightest) and is lowest in the prefill-heavy half.
Preemption still destroys work — a preempted request's prefill is recomputed at a ~5 % cache-hit
rate — but on this run it is not the variable that moves throughput, and the negative
corr(prompt, preempt) says the prefill bursts are dominated by **new admissions**, not recompute.

**The clinching datapoint is the knee sample itself:** `gen = 4994` (the run maximum) occurs at
`preempt = 2.25/s`, near the *top* of the preemption range, and at `prompt = 5631` — the *lowest*
prefill rate in the entire band.

> Any earlier statement in this thread that the 4994 → 3941 tok/s gap "is preemption, costing ~21 %
> of generation throughput" is refuted by that row. The gap is prefill phase.

---

## 4. The drain overshot best-case capacity math — revised mechanism

| quantity | value |
|---|---|
| offered | 11.98 req/s × 512 tok = **6135 tok/s** |
| one pod at the knee | 4994 tok/s → **real deficit** |
| two pods at the knee | 9988 tok/s → surplus |
| backlog at pod B ready (t+534) | `run` 181 + `wait` 473 = **654 requests ≈ 335 000 tokens** |
| predicted drain at knee surplus (3853 tok/s) | **87 s** |
| predicted drain at band surplus (1746 tok/s) | **192 s** |
| **observed** (`kv` < 0.85 at t+659) | **125 s** — 44 % over best case, between the two bounds |

The observation stands; the mechanism is §2, not preemption. During a drain the queue is never
empty, so **every freed slot is refilled immediately** and prefill pressure stays pinned at maximum
— which is precisely the condition that holds decode throughput down at the band mean (3941)
instead of the knee (4994). The drain is slow *because* it is a drain.

Peak TTFT in that window reached **70 494 ms** (queue wait folded in).

---

## 5. What this does to our own estimators

Not defects in the code — the code computes what it says it computes. These are limits on what the
numbers mean, and they are the reason "true capacity" is hard to read off a live engine.

**5a. `tput_knee` is phase-selecting.** It takes the max over intervals
([extract_real_trace.py:801](../../extract_real_trace.py#L801)), so it structurally selects the
prefill-quietest moment of the cycle: **4994 vs a band mean of 3943, +27 %.** As a per-replica
capacity that is an upper envelope, not a sustainable rate. "Peak throughput at concurrency X" is
not well defined on a saturated engine — the same concurrency yields 2590–4994 tok/s depending on
phase.

**5b. `itl_fit` has no prefill term.** `itl = A·run + B` is fit below the band (where the prefill
coefficient is negligible) and extrapolated in. It predicts **52.43 ms** at
`max_conc_pred = 198.41` against an observed band mean of **48.54 ms** (+8.0 %) — so the *mean*
survives, but the model is structurally blind to the 38 → 71 ms swing, and `rho = 8.003` inherits
that blindness.

**5c. `B_measured` rests on three samples, two of them boot.** `B_measured_n = 3`; two are pod A's
first two scrapes (ages −16 s and 0 s relative to first serving), one of which is a diluted interval
(`gen = 227.6 tok/s`, because the pod served for only part of the window). The value barely moves
(10.83 → 10.86 ms excluding boot) — that is luck, not robustness. Wants a minimum-n guard, or a
flag when every low-`kv` sample comes from a pod's first minute.

**5d. The `y_lo` scan is sensitive to the interval set.** Dropping intervals in the first 128 s of a
pod's serving life flips the winning knee 0.2 → 0.0 and moves A 0.2312 → 0.1977 (−14 %) and B
6.55 → 8.99 (+37 %). The shipped fit has `B_extrapolated: true`, i.e. its B = 6.55 ms is an
extrapolation while `B_measured = 10.83 ms`.

**Shipped values, for reference:**

```
tput_knee = {run 172, gen_tok_s 4994.125, n 81, n_left 61, n_right 18, confident true}
sat_band  = {threshold 0.85, n 21, run_mean 181.67, run_max 198, itl_ms 48.538,
             gen_tok_s 3940.665, req_s 7.546, preempt_s 1.4629, qwait_s 20758.86,
             kv_mean 0.98915}
itl_fit   = {y_lo 0.2, y_hi 0.85, A_ms_per_req 0.23123, B_ms 6.5512, r2 0.9184, n 24,
             B_measured_ms 10.829, B_measured_n 3, B_extrapolated true, rho 8.0032}
```

**5e. Same hazard applies to WVA's SAT and TA in production.** A scrape landing in the prefill-heavy
half of the cycle sees 71 ms ITL / 2590 tok/s; one landing in the decode-heavy half sees 38 ms /
4994 — a 1.9× swing in apparent per-replica capacity with **no change in load and no change in
replica count**, at a period (24 s) shorter than a typical scrape interval. *Not verified against
the Go analyzers — this is a flagged concern, not a finding.*

---

## 6. Boot transients: real, but they do not move the capacity numbers

Booting pods do emit metrics before they serve. `scan_raw`
([extract_real_trace.py:579](../../extract_real_trace.py#L579)) drops *empty* scrapes, but a
booted-engine-not-yet-serving pod emits a full set of zeros and survives: pod B has 32 s of
`run=0, kv=0, gen=0, itl=None` scrapes, and two stable intervals sit entirely before their pod ever
served.

Dropping every stable interval that starts within N seconds of its pod's first serving sample:

| N | dropped | knee | `sat_band` gen | `itl_fit` A / B / r² |
|---|---|---|---|---|
| — | 0 | 4994.1 @ run 172 | 3940.7 | 0.2312 / 6.55 / 0.918 |
| 16 s | 5 | 4994.1 | 3906.2 | identical |
| 32 s | 7 | 4994.1 | 3947.5 | identical |
| 64 s | 12 | 4994.1 | 3904.6 | identical |
| 128 s | 19 | 4922.1 @ run 173 | 3901.3 | 0.1977 / 8.99 / 0.930 |

`STABLE_DRUN` plus the `kv ≥ 0.85` filter already do the work: the 0→18→37 ramp has |Δrun| inside
tolerance but `kv ≈ 0.02`, so it never reaches `sat_band`, and `tput_knee` filters on truthy
`gen_rate`. **Contamination of the knee, band and slope is under 1 %.** The residual exposure is
§5c and §5d, plus §7.

Worth noting the shipped knee sample comes from the **newly booted** pod at age 94 s
(t+628…644, `run` 197→172, `kv` 0.991). Not a boot transient — a phase transient (§5a).

---

## 7. `router_stats.oscillation_flag: true` is a false positive — **open decision**

Shipped: `disp_p50 0.066, disp_p95 1.000, leader_flips 15, n 28, oscillation_flag true`. Panel 3
annotates this as `OSCILLATING`.

`router_stats` ([extract_real_trace.py:809](../../extract_real_trace.py#L809)) computes
`disp = (hi − lo) / tot` over every timestamp with ≥2 pods reporting `run`, and fires on
`disp_p95 > 0.5 and flips >= 3`. The p95 comes **entirely** from the samples where pod B is
booting (`run = 0` → `disp` = 1.0) — the same boot artifact as §6. Restricted to samples where both
pods are live:

| | shipped | live-only |
|---|---|---|
| `disp_p95` | **1.000** | **0.143** |
| `disp_p50` | 0.066 | 0.065 |

And "15 leader flips in 27 transitions" at ~6.5 % median imbalance is what *well-balanced* pods look
like — the leader label is noise, not oscillation.

**Not applied.** The bug fix (exclude non-live pods from the dispersion series) would silently ride
a semantic decision — what "oscillating" should mean, and whether `flips >= 3` belongs in the
predicate at all. Those belong to Dean. Until then, **nothing from this bundle should be shown as
evidence about the router.**

---

## 8. Queues are near-symmetric across pods

Per-pod `wait` through the two-pod window: 392/91, 197/143, 155/155, 176/148, 71/110, 67/65, 84/82,
0/24. Summed |waitA − waitB| is **23 %** of total queued, and most of that is the first sample after
pod B goes ready. So "one pod holding a long queue while the other idles" is not what happened here.

The one genuinely long queue (`wait` 473–530) is in the **single-pod** window, where it is a
capacity deficit, not a placement error.

Related trap, worth keeping: **when testing "is a pod starved", score against `kv`, not free
request slots.** At `kv ≈ 1.0` a pod cannot admit regardless of how many of its 198 nominal slots
are free. An early version of this test compared queues against `max_conc_pred = 198.41` and flagged
11 of 28 samples; scored against `kv`, only t+659 shows genuine headroom beside a queue (A: run 148,
kv 0.75, wait 0; B: run 185, kv 1.00, wait 24).

---

## 9. Not a defect: `out_tok` vs `out_tok_client`

They disagree on all 7919 requests (median diff +358; client median 876 vs server 512; client CV
0.252 vs server 0.036). This is the known inference-perf client-side chunk double-counting, recorded
as `meta.inflation_factor = 1.7847`. Server `completion_tokens` is authoritative and is what panel
1b measures. See plan §3.

---

## 10. What the next run would have to do to settle the open questions

1. **Dwell in `kv` 0.3–0.85** — still the single biggest gap (plan §5.1/§5.2); this run jumps 0.3 →
   1.0 with nothing in between, so A remains uncalibrated and the 0.85 ceiling is never exercised.
2. **Scrape faster than 8 s** so the 24 s structure is resolvable from the gauges, not only from the
   per-request trace. At 16 s the engine-side view of the wave is aliased away entirely.
3. **A mixed-length workload at the same offered load** — the direct test of §1's counterfactual, and
   the only way to separate "attenuates" from "erases".
4. **Short outputs with long inputs** (≈4K in / 64 out) for a genuinely prefill-dominated regime;
   4K/1K is still decode-dominated by the arithmetic in plan §7.1.
5. **`vllm:iteration_tokens_total`**, if it can be captured — it measures directly how much prefill
   rides in each engine step, which is the quantity §2 currently infers from `prompt_tokens_total`.
