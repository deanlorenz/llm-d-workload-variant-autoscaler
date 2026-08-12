# Autoscaling-viz — Type 1 Design

**Status:** DRAFT — awaiting Dean's review

> **Reading protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

**Why this doc exists, and why now.** The 2026-08-10 pokprod campaign
([`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md)) surfaced that
`tput_knee()` and `capacity()`/`max_conc_pred` — the two functions in `extract_real_trace.py` that turn
raw traces into the "capacity ceiling" lines drawn on panels 1b/5 and into the self-check that compares a
predicted concurrency ceiling against an observed one — were never actually reviewed by Dean. Both were
introduced in the toolchain's very first commit, `ca7f2c74` (2026-08-07, recorded under Dean's git
identity in the `autoscaling-viz` worktree — as every commit there is, regardless of whether it was Dean
typing directly or a coding session acting under that identity; the record does not distinguish the two,
and this doc does not claim to know which), and every "Dean approved" line on record about that worktree
is about the
**migration** (branch name, worktree move) — never about these two functions' design. There is also
currently **no Type 1 design doc for the viz component at all**: the nearest-sounding candidate,
[`benchmark-observability-plan.md`](benchmark-observability-plan.md), is a Type 3 for an unrelated effort
(WVA's own k2/saturation decision logging) and never mentions capacity or knee estimation. The only place
this design has lived is `autoscaling-viz/real-trace-viz-plan.md` §5–§9 and the code's own docstrings —
both Type-3-shaped or below, never frozen, never walked through with Dean.

**What this doc is, and is not.** Per [`session/CONVENTIONS.md`](../session/CONVENTIONS.md)'s Type 1
definition, this doc states what the design currently *is* and *why*, precisely enough for Dean's later
review to say "yes, that's right" or "no, change X." It is retroactive — the code already exists — which
is fine: freezing a design after the fact is exactly what makes a later review possible. It is **not** a
Type 3 (no task-plan, no step-by-step implementation content, no progress tracking) and **not** a Type 6
review (no verdict on whether the code is correct — that judgment is Dean's, once he reviews it against
this doc). Wherever a design choice is questionable, that is stated as an **open question**, not resolved
here, and not attributed to Dean as a decision he has not made. Tense matters throughout: "the design
currently does X," never "Dean decided X" unless a quote is present.

**Who asked for this and how it was scoped.** Dean, 2026-08-10 (recorded in the campaign doc's § *Type 1
homes*): two Type 1s, split by worktree responsibility, cross-referenced where they touch. This is the
**viz** one. His instruction for drafting it: *"can draft the type 1 in the background. There is enough
info. No need for my input. Can discuss it later."* Nothing here required or received his input before
writing; several sections below are exactly the design questions his review is expected to answer.

## TOC {#toc}

- [Scope and boundary](#scope) L53:75
- [The estimation model, as it exists in code today](#model) L76:164
  - [The ITL model — piecewise linear with a validity window](#itl-model) L81:99
  - [The capacity model — memory-bound KV-budget concurrency](#capacity-model) L100:125
  - [`tput_knee()` — an upper-envelope rate estimate, not a sizing number](#tput-knee) L126:138
  - [Two unrelated ceilings, no shared code path](#two-ceilings) L139:164
- [Known limitation — the regime-decomposition critique](#regimes) L165:212
- [Open design questions carried from the campaign doc](#open-questions) L213:236
- [A candidate signal, not yet designed in — EPP scorer debug logs](#epp-signal) L237:263
- [Coverage-check specification](#coverage) L264:299
- [Panel design](#panels) L300:331
- [Cross-references](#cross-refs) L332:355

## Scope and boundary {#scope}

Dean's split (2026-08-10, campaign doc § *Type 1 homes*), by worktree responsibility:

- **Viz Type 1 (this doc).** Visualization, post-test analysis, synthetic simulation, and
  simulation-following-a-test. Owns: the capacity/knee estimation model
  ([§ model](#model)), the coverage-check specification ([§ coverage](#coverage)), panel design
  including the missing scaling-decision panel ([§ panels](#panels)).
- **Benchmark Type 1 (not this doc — to be written separately, referenced here once it exists).**
  Setup, runs, workload preparation, collection, results management, and calling into viz. Owns: the
  `.env`/context contract, the results-persistence tree, per-request collection policy, the
  harness-credential mechanism. As of this writing that doc does not exist; see
  [§ cross-references](#cross-refs).

Everything downstream of a bundle (`bundle.json`, `coverage.json`) is viz's; everything that produces a
run directory for the extractor to read is benchmark's. The extractor and renderer (`extract_real_trace.py`,
`render_real_trace.py`) are read-only consumers of whatever the benchmark side collects — this doc does not
constrain collection policy, only what viz does with what it is given.

[↑ TOC](#toc)

---

## The estimation model, as it exists in code today {#model}

Three separate estimators live in `autoscaling-viz/extract_real_trace.py`. None of the three share a
code path with either of the others; each is documented here as it is written, not as a unified theory.

### The ITL model — piecewise linear with a validity window {#itl-model}

`itl_fit()` fits `ITL = A·k + B` (`k` = concurrent requests, `run` in the code) over stable intervals
whose KV utilization falls in a window `[y_lo, 0.85]`. `y_lo` is scanned over `{0, 0.1, 0.2, 0.3, 0.4}`
and the best-r² fit with `n ≥ 8` wins; the chosen `y_lo` is recorded, and `B_extrapolated = y_lo > 0`
flags when the intercept is not directly measured. A **separate** fit, `itl_fit_sat`, covers `kv ≥ 0.85`
and is never merged with the first — the plan doc's own measured example
(`real-trace-viz-plan.md` §5.2) shows the saturated segment 7.7× steeper with a nonphysical
`B = −140 ms`, so a single line spanning both regimes would be meaningless. `y_lo = 0` corresponds to a
decode-heavy shape (the knee sits at the origin); heavier prefill moves the knee up, per the plan's §5.2
theory (`Dean: ITL = A·k + B holds for kv < 0.85 and for kv > y, where y is a knee. Decode-heavy → y=0…
Prefill-heavier → y ≈ 0.2–0.4`). `itl_fit()`'s own docstring records that a prefill term was
deliberately measured and left out: below saturation, concurrency alone reaches r²=0.93–0.94 and adding a
prompt-token-rate term buys +0.001; in-band (kv≈0.99) the same term buys +0.236 and omitting it inflates
the slope `A` by 1.8×. The fit is therefore sound in the regime it is applied in (right-sized, sub-band)
and is not to be extrapolated into saturation.

[↑ TOC](#toc)

### The capacity model — memory-bound KV-budget concurrency {#capacity-model}

`capacity()` computes:

```
footprint_tok = I·(1 − pfx_hit) + O/2
max_conc_pred = kv_tokens / footprint_tok        where kv_tokens = num_gpu_blocks × block_size
```

`I`/`O` are the run's input/output token shape; `pfx_hit` is the run-aggregate prefix-cache hit rate
(total hits over the run divided by total queries — not per-request); `num_gpu_blocks`/`block_size` are
read directly from the `vllm:cache_config_info` gauge, never assumed. This is stated as a **memory-bound**
model: the KV cache, not compute, is the binding constraint on how many requests can run concurrently.
The code classifies which regime a given run's peak actually sat in — `regime = 'memory-bound' if
kv_at_peak_conc ≥ SAT else 'compute-bound-or-unsaturated'` — by checking whether KV utilization at the
observed concurrency peak reached the saturation threshold. If a run's concurrency plateaus while KV
utilization stays well below the threshold, the run is compute-bound and this formula is expected to
**over-predict**, because it assumes the memory budget is what stops the batch from growing. The plan
doc's own framing of this (§6): *"we cannot really estimate, can only observe"* — the regime is a
per-run classification made by inspecting the data, not a property the model derives independently. On the
one run this was checked against, the prediction matched the observed peak to <1% with zero free
parameters (186.8 predicted vs 182 mean / 195 max observed, both at kv 0.993–1.000, i.e. squarely in the
memory-bound regime the formula assumes).

[↑ TOC](#toc)

### `tput_knee()` — an upper-envelope rate estimate, not a sizing number {#tput-knee}

`tput_knee()` takes the `argmax` of measured generation throughput (`gen_rate`) over stable
concurrency-bins, and reports it `confident` only when there are at least 3 bins of data on both sides of
the peak. Its own docstring is explicit about what this is and is not: *"Read it as 'the best this
hardware was ever seen to do', not as a rate to size against."* Because it is a `max` over an oscillating
signal, it structurally selects the quietest instant in the batch — measured at +27% above the
saturated-band **mean** on one run (4994 vs 3943 tok/s). This is a known, documented property of the
estimator, not a defect discovered here; it is listed as open item 7 in the plan doc's §12.2 and repeated
verbatim as one of the three open questions below ([§ open-questions](#open-questions)).

[↑ TOC](#toc)

### Two unrelated ceilings, no shared code path {#two-ceilings}

This was a live point of confusion in the campaign write-up and is stated precisely here because it
recurs. `tput_knee()` and `capacity()`'s `max_conc_pred` are **two different quantities, computed by two
different functions, feeding two different places in the renderer**:

| | quantity | source | where it is drawn |
|---|---|---|---|
| **rate ceiling** | output tokens/s per pod | `tput_knee()` (falls back to `sat_band`'s mean generation rate if `tput_knee` is not confident) | panel **1b** — `render_real_trace.py`'s "capacity ceiling" dashed line, `ready × ceil_rate` |
| **concurrency ceiling** | requests in flight per pod | `capacity()`'s `max_conc_pred` | panel **5**'s "usable slot capacity" dashed line (`ready × max_conc_pred`), panel **3**'s "KV ceiling" step line, and the self-check `capacity model vs observed peak concurrency` |

Both ceilings get multiplied by `ready` replica count and drawn as step/dashed lines, and both are
visually labeled "capacity" in their respective panel — which is exactly why they read as the same model
from a glance at the figure. They are not: the rate ceiling is an **empirical maximum observed on the
same run it is drawn over** (calibrated from the curve it overlays, which is why it always tracks
visually convincing), while the concurrency ceiling is a **KV-budget model prediction**, checked once
against the run's own observed peak. A run can show a visually tight rate ceiling on panel 1b while its
concurrency-ceiling self-check fails by 60%+ — that is not a contradiction, because the two panels are not
testing the same thing. `m-ta-staircase` (campaign doc Finding 3's correction) is exactly this case: panel
1b tracked delivered load throughout with no visible pathology, while the self-check's `max_conc_pred`
was 212.4 against an observed 78.0 (63% error) on the same run.

[↑ TOC](#toc)

---

## Known limitation — the regime-decomposition critique {#regimes}

This is stated as the design's own open problem, per Dean's objection (campaign doc, § *`tput_knee()` and
`capacity()` were never reviewed*), not resolved here.

Real concurrency over time, `num_running(t)`, has at least three distinct behaviors:

- **(a) — the pre-saturation trajectory.** Not constant, not linear in offered load, and subject to
  jumps: replica boots, preemption events. This is the regime a right-sized, non-saturated deployment
  actually lives in most of the time.
- **(b) — the near-saturation value.** The quantity the capacity model is actually trying to predict.
  Harder to track precisely because it is not a fixed point — the system is still adjusting as it
  approaches the ceiling, not resting at it.
- **(c) — the fully-saturated ceiling.** A simple `max()` over the observed trace. Descriptive of "how
  high did it go," but says nothing about behavior below it — a ceiling, not a model of the regime under
  the ceiling.

`capacity()` as it exists today produces **one global number, checked once against one observed peak**
(`max_conc_obs = max(runs)`), with no time-windowing and no regime classification beyond the single
binary `memory-bound` / `compute-bound-or-unsaturated` split computed at the peak instant. This design is
closest to regime **(c)** — it is, in effect, a model of the ceiling, evaluated at the ceiling. Applying
it to a run that never approaches the ceiling is close to a category error: checking a saturated-regime
formula against a run that stayed in the (a)/(b) regime the whole time.

This is very likely why the self-check failed with 63% error on `m-ta-staircase`, a run that — per the
campaign doc's Finding 3 correction — stayed in the (a)/(b) regime throughout and never reached (c).
Panel 1b's rate ceiling (`tput_knee`, an empirical envelope) tracked that same run's delivered load with
no visible pathology, because it is not making the same claim the concurrency self-check is: it is not
predicting a ceiling from first principles, it is reporting what was actually observed. The concurrency
self-check, by contrast, is a from-first-principles prediction being checked outside the regime it
implicitly assumes.

The three findings this campaign produced independently point at the same underlying issue, restated from
the campaign doc: **static/global estimates get applied to a quantity that is actually piecewise or
regime-dependent, and nobody has yet computed how the error behaves as a function of time or regime.**
This applies beyond `capacity()` — both WVA's saturation and throughput analyzers make their own
demand/supply estimates, and Dean's point generalizes: demand estimates tend to be tractable, supply
estimates are multi-modal at best (exactly the (a)/(b)/(c) split above), and averaging across a run is not
expected to be accurate in either analyzer's actual operating regime.

**This section states the problem. It does not propose a fix.** Whether `capacity()` should be windowed,
regime-classified, or left as-is with a documented scope restriction is Dean's call — see the three open
questions below, carried verbatim from the campaign doc.

[↑ TOC](#toc)

---

## Open design questions carried from the campaign doc {#open-questions}

These are Dean's own three questions (campaign doc, § *`tput_knee()` and `capacity()` were never
reviewed*), preserved here exactly because they are the concrete target for his eventual review of this
section. Not answered here.

1. **Should `capacity()` report a windowed or regime-classified value instead of one global number?**
2. **What is the local error of `max_conc_pred` as a function of time/regime** (a(t) vs b vs c), **rather
   than one point-in-time comparison against `max_conc_obs`?**
3. **Is `tput_knee()`'s `argmax`-over-stable-bins approach the right quantity for the 1b/5 "capacity
   ceiling" line**, given it is now known to be visually convincing *because* it's calibrated from the
   same curve it overlays — which could mask exactly the kind of regime-dependent error being asked about
   in question 2?

(Question 3's "1b/5" phrasing is the campaign doc's own shorthand; per [§ two-ceilings](#two-ceilings)
above, panel 1b's line is `tput_knee`'s rate ceiling while panel 5's is `capacity()`'s concurrency
ceiling — so question 3, read precisely, is about `tput_knee()`'s panel-1b/panel-3-router-view line, and
a parallel version of the same self-calibration concern applies separately to `capacity()`'s panel-5/3
concurrency line, which is what question 1 and 2 are actually about.)

[↑ TOC](#toc)

---

## A candidate signal, not yet designed in — EPP scorer debug logs {#epp-signal}

Flagged as an unexploited direction, not a commitment. The EPP (endpoint picker) runs with a debug log
that, per request per candidate endpoint, emits `kv-cache-utilization-scorer` score plus that endpoint's
live `KVCacheUsagePercent`/`RunningRequestsSize`/`WaitingQueueSize`/`CacheNumBlocks`/`CacheBlockSize`,
`prefix-cache-scorer` score, and `queue-scorer` score — all keyed by `x-request-id`. Confirmed present in
`logs/epp_pods.log` (11 MB/cell) for every cell of the 2026-08-10 campaign.

This is a real, timestamped, per-request, per-pod signal that `capacity()` and the coverage checks
currently do not use. Two concrete ways it could feed the model, neither designed in yet:

- **A genuine per-request prefix-hit rate.** `capacity()`'s `pfx_hit` today is a single run-aggregate
  number (`Σ hits / Σ queries` over the whole run); the EPP's `prefix-cache-scorer` score is a per-request
  signal, which could replace that aggregate with something that varies over the run the way the true hit
  rate does.
- **A windowed or regime-aware capacity estimate.** Per-request, per-pod `KVCacheUsagePercent` and
  `RunningRequestsSize` at scheduling time is exactly the kind of local signal that open question 2
  above (§ open-questions) is asking for — the error of `max_conc_pred` as a function of time or regime,
  rather than one point-in-time comparison.

Neither direction is scoped further here. The signal exists and is confirmed on disk; deciding whether and
how to use it is future work, contingent on Dean's review of the open questions above.

[↑ TOC](#toc)

---

## Coverage-check specification {#coverage}

`coverage()` (`extract_real_trace.py`) emits 15 fixed rows plus one conditional 16th, each a
`{capability, verdict: PASS|FAIL, detail}` record. This section is authoritative — it describes existing
code, not proposed design. One row per check: what it asserts, its threshold/condition, and what a FAIL
should prompt next.

| # | capability | asserts | threshold / condition | on FAIL |
|---|---|---|---|---|
| 1 | **Calibrate A** | enough stable intervals span enough distinct KV bands to fit the ITL slope | `n ≥ MIN_FIT_N` and `≥3` distinct 0.1-wide KV bands within `[y_lo, 0.85]` and KV span `≥0.4` | the run did not dwell across a wide enough KV range; A is not trustworthy — do not cite the fitted slope for extrapolation |
| 2 | **Trust B** | the fitted intercept is either measured directly or agrees with directly-observed low-concurrency ITL | (`≥5` intervals at kv<0.05 and `y_lo=0`, i.e. not extrapolated) **or** (fitted B within 25% of the mean ITL measured at kv<0.05) | the intercept is an extrapolation with no independent check — treat B, and anything derived from it (e.g. ρ), as unverified |
| 3 | **Characterize saturation** | enough stable intervals sit in the saturated band to describe it | `n ≥ 10` at kv≥0.85 | saturated-band numbers (`sat_band`'s itl_ms/gen_tok_s/preempt_s/…) rest on too few samples to trust |
| 4 | **Exercise the 0.85 ceiling** | some intervals actually sit near the saturation threshold itself | `≥3` intervals with kv in `[0.80, 0.90]` | the run jumped over the threshold rather than dwelling near it — the boundary itself is unobserved, only "below" and "above" |
| 5 | **Locate the throughput knee** | `tput_knee()` had enough bins on both sides of its peak to be confident | `knee.confident` (≥3 bins each side, per its own gate) | the panel-1b rate ceiling is not a confident knee estimate — it silently falls back to the saturated-band mean instead |
| 6 | **Scale-down present** | the run actually contains a desired-replica decrease | `lag.scaledown_observed` | drain/scale-down behavior cannot be characterized from this run at all |
| 7 | **Drain-vs-kill measurable** | a scale-down happened *and* there is a per-request trace to see what happened to in-flight requests across it | check 6 passes **and** `requests` is non-empty | even if a scale-down occurred, whether in-flight requests were drained or killed cannot be determined without per-request data |
| 8 | **Queue (a) material** | the derived flow-control queue (`L(t) − dispatch`) is nonzero at a scale worth caring about | `p95(q_flow) > 1` | the flow-control queue this run measured is negligible — not necessarily that it doesn't exist, only that this run's demand never built one worth showing |
| 9 | **Queue (c) material** | the summed per-vLLM waiting queue is nonzero at a scale worth caring about | `max(q_engine) > 1` | the engine-side backlog never built up in this run — the queue panels will show near-zero, which is a fact about the run, not a code problem |
| 10 | **Router imbalance measurable** | there are at least 2 pods to compare | `len(pods) ≥ 2` | with a single pod, no imbalance statistic can be computed — the router panel's dispersion numbers are meaningless, not just absent |
| 11 | **rho model valid at top** | preemption is negligible in the saturated band, which the ρ model assumes | `sat_band.preempt_s < 0.05` | preemption is materially disrupting the saturated band; the ρ = (A·max_conc_pred + B)/B formula's implicit "requests run to completion" assumption is violated at the top of this run |
| 12 | **Capacity model checkable** | both a predicted and an observed concurrency ceiling exist to compare | `max_conc_pred` and `max_conc_obs` are both present | the self-check comparing predicted vs observed concurrency cannot run at all — usually missing KV-cache config or missing shape (`in_tok`/`out_tok`) |
| 13 | **Boot lag measured** | at least one replica-boot interval was captured | `lag.boot_s` non-empty | panel 2's boot-lag annotation has nothing to report; scale-up timing is unmeasured for this run |
| 14 | **Signal completeness** | every pod has at least a handful of scrape samples | every pod's series has `≥5` samples | at least one pod is too sparsely sampled to trust its per-pod series; treat that pod's contribution to any per-pod panel as best-effort only |
| 15 | **Per-request trace present** | a per-request file was found and parsed | `requests` non-empty | panels 1a and 4's demand-side view, and the derived flow-control queue (check 8), are all unavailable — this run can only support the scrape-derived panels (2, 3, 5) |
| 16 (conditional) | **Knee matches shape prediction** | the fitted ITL knee (`y_lo > 0` or `= 0`) agrees with what the run's input/output shape predicts (decode-heavy → `y=0`; prefill-heavier, `out/in < 0.5` → `y>0`) | only emitted when both `in_tok` and `out_tok` are known; `(y_lo > 0) == (out/in < 0.5)` | the fitted knee location does not match the shape-based prediction from §5.2's theory — worth a specific look at that run's fit before trusting `y_lo`, since it contradicts the model the fit is supposed to confirm |

`n_pass`/`n_fail` are the simple counts; `coverage.json` also carries the extractor's own runtime
`warnings` list (`WARN` global) alongside the row set. There is no single overall PASS/FAIL — the report
is designed to be read row-by-row, since which rows matter depends on what a given analysis is trying to
use the run for (a run can be a good *panel* trace and a poor *calibration* trace at the same time, per
`real-trace-viz-plan.md` §9's framing).

[↑ TOC](#toc)

---

## Panel design {#panels}

`render_real_trace.py` draws six panels from a `bundle.json`. Brief, current-state description of each;
none of this is proposed — all six exist today.

| panel | shows | primary data source |
|---|---|---|
| **1a** | Request throughput and "goodput" quality — stacked bars of completed requests binned by wait-before-first-token band (including a `>60s/failed` band), overlaid with sliding-window arrival and departure rate curves | per-request trace (`requests[]`) |
| **1b** | Work throughput in output-tokens/s — offered vs. delivered (stacked by request-size tercile) vs. the `tput_knee`/`sat_band` rate ceiling ([§ two-ceilings](#two-ceilings)) | per-request trace; `tput_knee`, `sat_band` |
| **2** | Autoscaling — desired vs. ready replica counts over time, with a boot-lag annotation and a drain-vs-usable-capacity hatch band when a scale-down occurs | `replica_status_timeseries.json` |
| **3** | Requests per pod — stacked running/waiting per pod, a router-side residual band, an overlaid total-in-system line, and the `capacity()` KV-ceiling step line; annotated with router imbalance (`disp_p95`, leader flips) with an explicit "not an oscillation test" caveat ([`real-trace-viz-plan.md`](../../autoscaling-viz/real-trace-viz-plan.md) §4.5) | `metrics/raw/*_metrics.log` scrapes |
| **4** | The three queue sources (a: derived flow-control, b: EPP dispatch, c: summed per-vLLM waiting) plotted together — explicitly titled `INTERIM: … which one panel 4 should draw is an open design question` in the renderer itself | scrapes + per-request trace |
| **5** | Concurrency — requests in system (`L(t)`) vs. requests being served vs. `capacity()`'s `max_conc_pred`-derived "usable slot capacity" ceiling, with queued (`L−served`) and unused-capacity bands shaded | scrapes; `capacity()` |

**Known gap: no scaling-decision-reason panel exists.** Per the campaign doc's § *Missing: a
scaling-decision panel* — Dean asked for a bottom panel showing WVA's logged scaling *reasons*, aligned
with panel 2's replica trace, rather than requiring a hand-grep of `controller.log` for each finding. The
data already exists to build this: `controller.log` carries per-tick `scaling-decision` lines, the
capacity-source reason codes `P1-obs`/`P2-hist`/`P3-k2`/`P4-k1` (`saturation_v2/types.go`'s
`k2SrcObserved`/`k2SrcHistorical`/`k2SrcDerived`/`k2SrcFallback`), and the explicit "analyzer absent from
configured list: will not vote" lines that this campaign used, by hand, to settle Finding 1. None of it is
plotted today — every citation of these codes in the campaign doc's own findings came from a manual log
grep, including the one that caught and corrected Finding 3's original misattribution. A dedicated
decision-reason-vs-time panel, aligned on the x-axis with panel 2's replica trace, would have made that
correction visible on the figure itself. **This section states the requirement and the gap; it does not
design the panel's implementation** — that is future work, and a well-scoped Type 3 task once someone
takes it on.

[↑ TOC](#toc)

---

## Cross-references {#cross-refs}

- **[`autoscaling-viz/real-trace-viz-plan.md`](../../autoscaling-viz/real-trace-viz-plan.md)** — the
  Type-3-shaped implementation doc this design was extracted from, primarily §5 (saturation and the ITL
  validity window), §6 (the capacity model, its <1% validation, the memory-bound/compute-bound
  discriminator), §7 (prefill and preemption), §8.3–8.4 (derivation order and self-checks), §9 (the
  coverage report and its capability table). **Superseded in part by this doc**: the frozen design
  concepts in [§ model](#model), [§ regimes](#regimes), and [§ coverage](#coverage) above now live here;
  `real-trace-viz-plan.md` keeps everything else — implementation history, the fetch/render/publish
  tooling, the Ofer/pokprod-PVC data inventory, the revision log, and the open items in its own §12 that
  are not the three carried into [§ open-questions](#open-questions). Whoever later migrates content out
  of that doc should treat this cross-reference as the map of what moved and what stayed; nothing in
  `real-trace-viz-plan.md` has been edited by this doc (different worktree, different task).
- **[`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md)** — the results
  doc that surfaced this gap; its § *`tput_knee()` and `capacity()` were never reviewed* and §
  *Type 1 homes* are the direct source of [§ regimes](#regimes), [§ open-questions](#open-questions), and
  [§ epp-signal](#epp-signal) above. Its § *Missing: a scaling-decision panel* and § *Coverage checks —
  undocumented* are the direct source of [§ panels](#panels) and [§ coverage](#coverage).
- **Benchmark Type 1 — does not exist yet.** Per the campaign doc's scoping decision, a sibling design
  doc covering setup/runs/workload-preparation/collection/results-management and calling into viz is
  owed, separately, by whoever picks up that side. This line is a placeholder to be turned into a real
  link once that doc exists.

[↑ TOC](#toc)
