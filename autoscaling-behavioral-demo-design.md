# Autoscaling Behavioral Demo — Design

**Status:** Draft (POC). Captures the design as of the brainstorming
session that produced `sim.py` / `plots.py` / `run.py`. Not WVA code; lives on its own
orphan branch **`autoscaling-viz`** (until 2026-08-07, under `plans/scratch/autoscaling-viz/` —
see [`real-trace-viz-plan.md`](real-trace-viz-plan.md) §14.6).

> **Purpose of this doc.** The discussion outgrew the code. This captures the
> model, the decisions we made (and why), the current results, and the strategies
> still to build — so the work can resume cold without re-deriving intent from the
> transcript.

---

## 1. Vision

A short, animated presentation that explains **autoscaling tradeoffs** to a
**mixed / leadership audience** — the eventual deliverable is a **self-contained
HTML deck** (animation + HTML export). That final packaging is **deferred** until
the model and the visuals are right.

**Phase 1 (built):** a Python discrete-event simulator that produces static
matplotlib figures + a comparison table. It exists to get the *story* and the
*numbers* right before we invest in animation.

The teaching arc is deliberately three steps:

1. **Ideal** — scaling with zero boot lag. Everything is served promptly (100 %
   in ≤2 s), and on a smooth bump it never queues. Sets the "this is what good
   looks like" baseline.
2. **Setup lag** — the *same* demand-tracking scaling commands, but replicas take
   ~90 s (~1.5 min) to boot. Actual capacity lags desired through the entire
   up-ramp; the system runs under-provisioned. On a smooth bump nothing is
   *permanently* stranded (the bump recedes in time), but **only ~20 % of requests
   are served promptly** — the mass is pushed into 30–60 s waits. Quality, not
   completion, is what collapses.
3. **Queue-aware** — same 90 s boot, but the sizer adds a backlog-drain term. It's
   reactive: it front-loads capacity and roughly **halves the median wait**, but
   because it chases a backlog already being addressed by in-flight boots, the
   replica it orders late lands *after* the peak — so it **worsens the tail** (p90
   50.6 s vs 39.6). This motivates **anticipation** (feed-forward) as the next
   step.

The honest headline is: **on a smooth bump, the reactive backlog term is a modest
quality-mix shift, not a rescue.** All three teaching steps complete 100 %;
queue-aware barely moves the peak queue depth (~7 %) and actually worsens the tail — its only
real win is shifting some waits toward "good." The dramatic "recovers stranded
work" story requires a sharper or sustained overload, which the smooth bump does
not produce (see §6.3, §6.5).

**Two baselines frame the arc.** Alongside the three teaching steps the demo now
renders two reference points, used for cost/quality contrast rather than as steps
in the argument: a **no-scaling strawman** (a fixed fleet pinned at the max replica
count for the whole run — 100 % prompt on this bump, but the most expensive fleet
at the lowest utilisation) and the **KEDA/HPA family** (queue-depth, running-
concurrency, and their native `max` combination — the off-the-shelf closed-loop
controllers the arc is ultimately measured against). These are the well-lit path;
`Qexp` (§3(ii)) is what beats it. See §3 for the sizers and §6 for the numbers.

**Comparison UX (deck).** The deck contrasts any **two** scenarios
**side-by-side**, with a control to switch which two are shown. The
**all-options numeric comparison is a single table** — every strategy a column (as
in §6's results table). The table is the global picture; the swappable
side-by-side figures are the two scenarios being actively compared. (Phase-1 static
figures render one scenario each; the side-by-side pairing + swap control is a
deck-level feature — see §8.2.)

### 1.1 Design axioms (2026-08-03 discussion — do not lose)

Three constraints now govern the whole tool. They were agreed in discussion and
supersede any earlier framing they conflict with.

1. **Workload-independence.** Neither the sizing algorithms nor the visualization
   may depend on the workload shape *in any way*. A workload is pure input data (a
   trace). Shape logic is confined to the fixture generator
   (`rate_profile` / `gen_load`); every sizer keys off *measured* demand (DR) and
   *projected* backlog, and every plot renders whatever trace it is handed. Rule
   going forward: **a new workload is a new fixture or a loaded trace — never a
   special case in a sizer or a plot.** (Audited 2026-08-03: currently holds — the
   only `pattern`/shape references are inside the generator; the sizers' "peak" is
   the projected *backlog* peak, a computed property of the incoming trace, and
   `plots.py` reads neither `PEAK_RATE` nor `DURATION`.)

2. **Two traces in (long-run architecture).** The eventual input is two traces:
   **(a) a workload trace** (arrivals + sizes) and **(b) a scaling trace** (replica
   count over time). Both can come from a real benchmark. The tool visualizes the
   *actual* run following (b) and overlays **counterfactual** scaling traces from
   alternative algorithms run against the same (a). The code is already factored
   for this — policies are pure `load → supply`; `sample` / `summarize` are pure
   `supply → timeseries`. Two seams are missing: a **workload-trace loader**
   (replacing `gen_load` with a benchmark export) and a **replay supply mode** (a
   "policy" that just follows a given (b) instead of computing one). Deferred — see
   §8.2.

3. **Autoscaling solves two problems; right-sizing is the headline.**
   - **(i) Right-sizing** — the steady-state problem, and *the more important one*:
     over the long run the average is what matters, and paying 2–3× for capacity you
     don't need is the entire reason to autoscale. The realistic scenarios must
     therefore contain **steady states (plateaus)** — that is where right-sizing is
     even visible — and **cost** (`replica·s` / `provisioned·s` vs the static
     baseline) is the punchline, not a footnote.
   - **(ii) Handling change** — the transient problem, which the Phase-1 demos have
     mostly exercised. **Fast, small changes (bursts) cannot be autoscaled at a 90 s
     boot** — they are absorbed by the **queue** (surfacing as TTFT degradation) and
     **headroom**. **Slow, large changes are the autoscaler's job**, handled exactly
     as these experiments show: *overreact until stabilization, then relax to the
     right size.* Autoscaling runs on a slow timescale — large-but-slow changes are
     the controller's, small-high-variance changes are the queue's.

**Why TTFT-Pxx alone is not a valid autoscaling metric (time-scaling argument).**
Extend any run 3× (same transient structure, more steady-state volume): the
*absolute* penalty is unchanged — the same requests wait during the same
transitions — but goodput and cost both triple, and **P90 / P95 / P99 wait all
improve purely because the penalized requests become a smaller fraction of a larger
denominator.** No algorithm improved. Wait-percentiles are therefore *dilutable and
framing-dependent*. This is the design argument for the metric choices already in
the tool: the **offered denominator**, **absolute-wait attainment bands** ("% served
within Ns"), and **cost foregrounded** — not a TTFT-P90 headline number.

---

## 2. Simulator architecture

### 2.1 Trace-driven and clairvoyant

The simulator is driven by two traces:

- **Load trace** — a list of requests, each with an arrival time and a size
  (work units). Arrival patterns are meant to **mirror our benchmark settings** —
  **uniform, rising/ramp, Poisson** — via `gen_load(pattern=...)`. Only `bump` is
  exercised so far; the others are intended and cheap to add.
- **Supply trace** — a list of replica lifecycle events (start / up / stop /
  down times).

A scaling **policy** is *only* a way to generate the supply trace. Everything the
graphs show is derived from the **actual simulated execution** — the graphs are
clairvoyant (post-hoc): they always reflect what really happened, never a
prediction. Changing the policy changes the supply trace, the simulation replays,
and the same rendering code tells the truth about that run.

This separation is the core design decision: **sizing strategy ⟂ simulation ⟂
rendering.** You can drop in a new sizer without touching the engine or the plots.

### 2.2 Event-driven engine

`Simulator.run()` processes an event heap with five event kinds:

- **arrival** — a request enters the global queue.
- **up** — a replica finishes booting and starts accepting.
- **stop** — a replica is commanded down (stops accepting new work).
- **down** — a replica finishes draining and is gone.
- **completion** — a request finishes service.

### 2.3 Service model (Phase 1)

- One **global FIFO queue**. No load balancer.
- A backend accepts requests up to a **usable** concurrency ceiling
  `⌊sat_frac · C⌋` (< raw C), and each in-service request advances at a **fixed
  `service_rate`** (tokens/s), so completion = dispatch + size/`service_rate`.
  The service rate is **concurrency-independent** while the backend holds ≤ usable
  slots. Per-backend usable work rate = `⌊sat_frac · C⌋ · service_rate`.
- `_free_backend` picks the most-free accepting backend (free = `usable_C −
  in_service`); `_dispatch` pulls FIFO.

**Why `sat_frac` (usable ceiling).** Real vLLM goodput does not scale to the raw
concurrency limit — throughput per request degrades and effective goodput rolls
over well before `C` (the KV cache saturates around ~85 % occupancy, often lower).
Rather than model that curve (that is the §2.7 work, now designed & implemented),
Phase 1 uses a flat **usable ceiling** `⌊sat_frac · C⌋` with `sat_frac = 0.85`
(raised from 0.70 on 2026-08-05 to seat the cap at the real ~85 % KV knee and pack
pods closer to the ceiling) as a lightweight stand-in: it caps each replica's usable
slots so the fleet is provisioned at a realistic granularity (`⌊0.85·100⌋ = 85`
concurrent). The sizer, the dispatcher, and the panel-5 capacity line all use the
*usable* ceiling, so they stay consistent.

**`sat_frac` is a *soft* saturation indicator, not a hard limit.** It is the
utilization at which a real router stops sending *new* traffic to a pod — but the
pod does not fail above it; it just slows (roughly linearly up to ~85 % KV, then
sharply — "to a crawl" — beyond). The closed-loop dispatcher here **never
oversubscribes** (it caps `in_service` at `⌊sat_frac·C⌋`), so in-sim a pod never
runs above target and the crawl regime is unreachable. It becomes relevant only when
an **imported** request/scaling trace records real per-pod concurrency *above* target
(a real router making early or mistaken decisions, so queues also form at each vLLM)
— see §8.2. So `sat_frac` stays the **KV cap**, not a knee to be reinterpreted.

**§2.7 (implemented 2026-08-03):** a concurrency-dependent *decode* rate — a backend
serves *faster* when lightly loaded and converges to this nominal `service_rate` as it
packs. It is a **monotone** slowdown below the cap, **not** a full USL retrograde (which
needs oversubscription past the cap — unreachable here without an imported trace).
`sat_frac` is **not** replaced or reinterpreted as a knee: it stays the usable / KV cap
the dispatcher respects. Default `RHO = 2.0`; `RHO = 1` recovers this fixed-rate model.

### 2.4 Replica lifecycle

- **Desired**: `start ≤ t < stop`.
- **Actual / ready**: `up ≤ t < actual_down`. `setup = start → up` is the boot
  lag; `drain = stop → down`.
- **Draining**: `stop ≤ t < down` — still serving in-flight, not accepting.
- **Provisioned / billed**: `start ≤ t < actual_down` — the whole footprint you
  pay for (booting + accepting + draining). `provisioned·seconds` integrates this
  span; `replica·seconds` integrates only the ready (accepting) span; the
  difference, **`boot-lag waste` = provisioned − ready**, is capacity billed while
  booting or draining but never serving (zero when `setup = drain = 0`).
- **Deferred-down**: a replica commanded down while it still has in-service work
  goes `pending_down` and only truly leaves when it drains.
- **Resurrection guard**: a replica commanded up and then cancelled mid-boot
  stays gone — the `up` handler only revives if `actual_down is None`.

**Initial state — the measured window must START in steady state (2026-08-06).** There is no
history before t=0, and left unhandled that single fact produced **two coupled artifacts** that
silently rewrote every shape whose demand does not start at zero:

1. **Cold fleet.** The fleet booted from 0 replicas regardless of the t=0 demand, so `stepdown`
   (which starts at `hi = 24`) was really testing a near-instantaneous step **up** into a 90 s
   boot lag first — and the startup queue it built polluted the remainder of the run. The shape
   measured the wrong thing (see §8.1 item 8).
2. **Cold demand estimate.** Every trailing-window estimator — the sizers' input
   (`offered_work_rate`, `SIZING_RANGE`) *and* the plotted offered curves (`_windowed_rate`,
   `REQ_RANGE` / `WORK_RANGE`) — computes `(cum(t) − cum(t−window))/window`, which reads ~0 at
   t=0 and ramps over the window **no matter what the true starting rate is**. Demand appeared
   to ramp from zero on `trapezoid` / `stepup` / `stepdown` / `spike`, which is simply false.

Both share one root and one fix: **assume the t=0 rate held for all t<0.** The seed is
`W0 = rate_profile(shape, 0) × size_mean` (work/s); it self-zeroes for `bump` (which genuinely
starts idle), leaving that reference shape untouched. The fleet is warm-sized to `W0` with
`start = up = 0` — pre-booted, so there is no phantom pre-t=0 boot cost, and billing still
begins at t=0 on the `[0, duration]` grid (matching how `gen_supply_static` was already
modelled). Applies to **every** sizer including the closed-loop HPA/KEDA ones; a warm fleet with
an empty queue holds at `n0` rather than collapsing to `min`, because the controllers **hold on a
zero metric** (`return n if n>0 else 1`).

*Successor, in flight (§8.2):* a **burn-in prelude** — run arrivals at the constant t=0 rate for
`T_burn` before the measured window, with **autoscaling frozen** throughout — replaces the
analytic *estimator* seed with genuine pre-window history (the trailing windows just fill), and
additionally starts the **served-side** state (in-flight requests, in-system `L(t)`, served-work
bands) in steady state, which the analytic seed cannot do. The warm fleet stays: with the
autoscaler frozen, nothing else would ever create the first replica.

> **Real-trace caveat (§1.1(2), §8.2 ingestion).** None of this transfers as-is to an imported
> benchmark trace: you cannot synthesize a real run's starting state from a formula. For real
> traces the initial fleet/queue/in-flight state must be **captured directly** from the run, or
> the leading warm-up window must be **trimmed out** of the measured region. Reporting a real
> trace from t=0 with a cold model fleet reproduces exactly artifact (1) above.

**Utilization** (a derived cost/quality read, `summarize`): delivered work ÷ usable
throughput-capacity paid for (`∫ ready · ⌊sat_frac·C⌋ · service_rate dt`). `<1` = an
idle / over-provisioned fleet; `~1` or above = fully packed — but *packed can still
fail latency* (a starved small fleet reads ~1, cf. hpa-concurrency at 1.02 while 88 %
fail), so it must be read **next to the quality bands**, never alone. It can nudge
just past 1 as a boundary artifact when the delivered-work and ready-replica sample
windows don't align exactly.

### 2.5 Model limitations (what it does NOT capture)

Stated plainly, with bias direction, so results aren't over-read:

- **Decode rate vs. concurrency** — the per-request rate is now
  **concurrency-dependent** by default (§2.7, `RHO = 2.0`): a lightly-loaded pod
  decodes faster, converging down to `service_rate` as it packs. The `sat_frac`
  usable ceiling (§2.3) still caps *how many* slots a replica offers (provisioning
  granularity); §2.7 bends the *rate* below that cap. Two limits remain: (i) it is a
  **monotone slowdown**, not full USL retrograde — throughput never falls, since the
  in-sim router never oversubscribes past `usable_C` (§8.2); (ii) `RHO` is a single
  global speedup ratio, not a measured per-model/per-shape slope (§2.7 caveat). Set
  `RHO = 1` to recover the earlier fixed-rate model.
- **Clairvoyant rendering** — the plots are post-hoc truth, but the *sizer* still
  only sees windowed data; don't conflate the two.
- **One global FIFO queue, no load balancer** — head-of-line blocking is
  **accounted as failure, not engineered around** (§4).
- **Instant, unbounded scale within the trace** (beyond the boot lag) — recovery
  speed is **optimistic**; no per-step scale caps or node-pool limits.
- **Single request class, one arrival shape** — illustrative dynamics, **not a
  calibrated benchmark**.
- **No reneging / abandonment** — requests wait indefinitely and are always
  eventually served (or counted `unfinished` at trace end); none give up mid-wait.
  Real clients time out, so a deep queue's true cost is **under-stated** here (a
  request that waited 5 min and was abandoned still counts as served-late, not
  lost). Modelling client-side deadlines (drop after a wait threshold, re-count as
  failure) is a **deferred future test** — it would sharpen the failure accounting
  for the badly-under-provisioned scenarios (setup-lag, hpa-concurrency).

### 2.6 Parameters (names, roles, and the two vocabularies)

Every knob, grouped by what it governs. The names here are the code names as of
the current `sim.py` / `run.py` (renamed from earlier drafts for precision).

**Two measurement vocabularies — "range" vs "interval".** We borrow PromQL's
distinction and use it consistently:
- A **range** is a *lookback span* — how far back a windowed average reaches
  (PromQL `metric[5m]` → the `[5m]` is the range). All averaging spans are ranges.
- An **interval** is a *cadence* — how often something recomputes or is sampled.
  All "every N seconds" knobs are intervals.

So `sizing_range` is how much history the sizer averages; `decision_interval` is
how often it re-sizes. They are independent: you can average over 60 s but decide
every 15 s.

**"rate" is overloaded — three distinct meanings.** Guard against conflating them:
1. **`service_rate`** — a *backend property*: tokens/s that one in-service request
   advances at (fixed, Phase 1). Not a measured throughput.
2. **demand rate (DR)** — a *demand estimate*: `arrival_rate × E[size]` tokens/s
   (see §3). An estimate, not a measurement (per-request size isn't known at
   arrival). **DR** is the human-facing name (figures, report, glossary); the code
   identifier is `owr` (offered-work-rate), kept unchanged in `sim.py`/`run.py`.
3. **measured request throughput** — the *observed* arrival/departure counts per
   second (`arr_n` / `dep_n`), requests/s. This is a measurement.
   Only the identifiers that mean (3) keep the bare word "rate" in code.

*Workload (`gen_load`)*

| Param | Role |
|---|---|
| `pattern` | arrival shape: `uniform` / `rising` / `bump` / `step` / `spike` |
| `duration` | total simulated seconds |
| `peak_rate` | peak arrival rate (requests/s) the pattern scales to |
| `size_mean`, `size_dist` | mean request size (tokens) and distribution (`expo`) |
| `seed` | RNG seed (reproducible traces) |

*Backend / fleet*

| Param | Role |
|---|---|
| `C` | raw per-backend concurrency limit |
| `sat_frac` | usable fraction of C; usable ceiling = `⌊sat_frac·C⌋` (§2.3) |
| `service_rate` | tokens/s per in-service request (fixed) |
| `setup` | boot lag: `start → up` (dead time) |
| `drain` | drain time: `stop → down` |

*Open-loop sizer (`gen_supply_perfect`, `gen_supply_queue_aware`, `gen_supply_queue_aware_exp`)*

| Param | Role |
|---|---|
| `headroom` | scale-up utilization target (`1.3` ⇒ run at ~77 % of the usable ceiling; raw-hardware util ≈ sat_frac/headroom ≈ 0.85/1.3 ≈ 65 %) |
| `sizing_range` | lookback the sizer averages `owr` over |
| `decision_interval` | how often the sizer recomputes desired count |
| `drain_time` | (queue-aware / Qexp) deadline to drain the current / projected backlog. **Both Q sizers use the same `20` s** — a deliberate level-field rule (2026-08-05); do not split them |
| `proj_setup` | (Qexp only) boot lead the *projection* assumes; distinct from `setup` (the lag the sim applies). Defaults to `setup`; **the demo runs `120`** (over-anticipates the true 90 s boot — swept-best at hr 1.3). The conservatism dial — see §3(ii) |
| `boot_stagger` | (queue-aware / Qexp) within-batch cascade: replica `j` of a batch lands at `t + setup + j·boot_stagger`. `0` = all land together. Modelling nuance, deferred — see §3(ii) |

*Closed-loop KEDA/HPA baselines (`run_closed_loop` / `make_controller`)*

| Param | Role |
|---|---|
| `kind` | trigger: `queue` (`ceil(Q)`) / `concurrency` (`ceil(R/c)`) / `combined` (`max`) |
| `metric_window` | trailing `avg_over_time` window the trigger averages its signal over (60 s) |
| `decision_interval` | reconcile cadence (15 s) — same range/interval split as above |
| `max_replicas` | KEDA `maxReplicaCount` cap (10); `minReplicaCount` is 1 |
| `headroom` | reused as the per-replica target scale (e.g. concurrency target `c ≈ ⌊sat_frac·C⌋/headroom`) |

*Static / no-scaling baseline (`gen_supply_static`)*

| Param | Role |
|---|---|
| `count` | fixed replica count for the whole run (pinned at `max_replicas`) |
| `setup`, `drain` | boot/drain lags (0 here — the fleet is pre-warmed and never scales) |

*Sampling / rendering (`sample`)*

| Param | Role |
|---|---|
| `sample_interval` | plot-grid resolution (seconds per sample) |
| `req_range` | lookback for the request-count throughput average (panels 1a/5) |
| `work_range` | lookback for the work-rate average (Prom-style; panels 1b/3) |

### 2.7 Concurrency-dependent decode rate (designed & implemented 2026-08-03)

Phase 1's per-request rate was **fixed** (§2.3). This model makes the decode rate
**concurrency-dependent**: a lightly-loaded pod serves *faster* than a packed one,
converging down to the nominal `service_rate` as it fills. This is real vLLM behavior
and the single biggest fidelity gain. **Implemented 2026-08-03** in `sim.py` (the exact
event-driven mechanism below) with `RHO = 2.0` the default in `run.py`; `rho = 1`
recovers the fixed-rate model as a behaviour-preserving identity.

**Empirical form (decode-only).** Inter-token latency below KV saturation is **linear in KV%**:
`ITL(k) = A·k + B`, where `k = KV%`,
`B` is the near-constant hardware floor ("natural ITL" at zero load, ~6 ms) and `A` is
a load-sensitivity slope that depends on the model **and** the request-size shape (so
it may vary with the workload). **Prefill is ignored** — the sim has no prefill/decode
split and shows **wait time + decode-based e2e**, not TTFT. KV% is per-pod and
proportional to concurrency (`KV ≈ avg_size · in_service`), so it rides `b.in_service`
— the state the engine already tracks.

*Where the relation comes from:* it is the supply model behind WVA's ThroughputAnalyzer, stated in
that project's internal design notes (`TA-supply.md` §2.1) — **not part of this branch**, so treat
the form above as the citable statement. It also has a **validity window** the sim ignores: the
linearity holds for `y < KV% < 0.85`, where the lower knee `y` is 0 for decode-heavy shapes but rises
to ~0.2–0.4 when prefill dominates in time, and `A`/`B` change with it. The real-trace path measures
`A`, `B` and `y` per run rather than assuming them — see [`real-trace-viz-plan.md`](real-trace-viz-plan.md)
§5.2 and §6.

**One knob: ρ = rate(empty)/rate(packed) ≥ 1.** Anchor the *packed* pod at today's
nominal `service_rate` and parameterize the speedup by ρ. With load fraction
`k = in_service / usable_C ∈ [0,1]` (k=1 = packed):

```
ITL(k) = B + A·k,   ITL(1) = 1/nominal (packed),   ITL(0) = 1/(ρ·nominal) (empty)
⟹  B = 1/(ρ·nominal),   A = (1/nominal)(1 − 1/ρ),   rate(k) = 1/(B + A·k)
```

**Default ρ = 2 (gentle, and self-consistent).** The packed anchor is Ofer's
~83.3 tok/s ⇒ packed ITL ≈ 12 ms; ρ=2 puts the empty-pod ITL at ≈ 6 ms — exactly the
`TA-supply.md` §2.1 natural-ITL intercept (`B ≈ 0.006 s`). So the packed pod runs at
2× its physical floor, and the floor lands on measured hardware. Why *gentle* is right
here: §2.1's 7–10× ITL swing is measured against a genuinely saturated ~57 ms packed
ITL; our packed anchor is a much lighter 12 ms, so keeping the same 6 ms floor
mechanically gives ρ≈2 (ρ=9 against the 83.3 anchor would imply an unphysical ~1.3 ms
floor). **ρ stays a tunable knob; the real value is workload-dependent and must be
measured — do not over-read the default.**

**Monotone throughput (guaranteed by the form).** Pod throughput
`usable_C · k / (B + A·k)` has derivative ∝ `B/(B+A·k)² > 0` in `k` — strictly
increasing, saturating at the packed ceiling. So more load never *reduces* delivered
throughput within the operating band; the monotonicity guard is satisfied by
construction, no clamp needed. **Relationship to USL:** this is the *pre-retrograde*
branch only — a monotone slowdown up to the cap. Full USL **retrograde** (throughput
falling past a knee) needs concurrency *above* `usable_C`, which the closed-loop router
never produces (it caps at `usable_C`); it becomes reachable only with an imported
over-subscribing trace (§8.2). So §7.1's "USL retrograde" steal stays a separate, later
thing — this model does not produce it.

**Sizer ↔ engine split (the crux).** Two clean layers:
- **Sizer: unchanged — sizes on the fixed *saturated* rate.** `per_backend =
  ⌊sat_frac·C⌋ · service_rate` stays as-is. The sizer plans for the worst case and
  never gets credit for a lean pod being faster. This preserves workload-independence
  (§1.1(1)) and the "size for saturation" principle — the sizer stays simple, sees a
  fixed rate. (Dean: the achievable low-load speedup can't be tracked per-iteration and
  is workload-dependent, so the sizer can only rely on the worst case; saturation rate
  is the only number relevant for scaling.)
- **Engine: models the load-dependent rate.** The reward for slack shows up only in
  *achieved* e2e, never in the plan.

This gives a **virtuous cycle** that enriches the right-sizing story: a pod sized for
the saturated rate but running below it clears work *faster* than the sizer assumed →
queue drains faster → concurrency stays lower → faster still, converging to nominal as
it packs. So **headroom stops being pure idle cost — it buys *speed*, not just burst
slack.** That is the payoff that makes over-provisioning legible as a quality lever
(and couples directly to the headroom sweep, §8.1 item 7(b)).

**Engine mechanism: exact, event-driven (decided — not an estimate).** The thing to
avoid is per-*token* iteration; per-*event* integration is exact for a
piecewise-constant rate and cheap at our scale (~2× the request count in events).
Replace the set-once `req.done` (`_dispatch`, `sim.py`) with `req.remaining` (tokens
left). On any event that changes a pod's `in_service` (a dispatch or completion on that
pod): advance its in-service reqs by `Δt · rate(k_prev)`, recompute `rate` at the new
`k`, reschedule the imminent completion. This handles "survivors speed up when a
neighbor leaves" exactly and for free. **Bounded change:** confined to `_dispatch` /
the completion handler / `Backend`+`Req` state in `sim.py` — **no sizer or plot API
changes.** (The lighter weighted-average-concurrency *estimate* was considered and
rejected: it reintroduces approximation and the future-dependence problem — you don't
know a request's average concurrency at dispatch — which the event-driven method
avoids.)

---

## 3. Sizing strategies

The demo compares reactive queue-aware sizing against an ideal baseline, against
the off-the-shelf KEDA/HPA family (now built — §(iii)–(v)), and against a
no-scaling strawman (§(vi)). The anticipatory sizer (§(ii) `Qexp`) is **now built
too** — a periodic control loop; all six sizers are implemented. Sizers, in order
of the argument:

**What "clairvoyant" means — two independent prediction abilities.** Every sizer
in the demo estimates demand and turns it into a replica count. The strategies
differ along **two separate axes** of foresight, and it helps to keep them apart:

1. **Can it see future *arrivals*?** — window **centering**. A *centered* range
   `[t−r/2, t+r/2]` peeks ahead (it averages arrivals that haven't happened yet);
   a *trailing* range `[t−r, t]` sees only the past. The ideal sizer is centered
   (it knows the future load trace); a real reactive sizer is trailing.
2. **Does it compensate for *setup* (boot lead time)?** — a sizer that knows
   replicas take `setup` seconds to boot can order *now* for the demand it will
   face at `t + setup`, i.e. size against `arrival(t, t+setup)`. The ideal
   baseline sidesteps this by running with `setup=0`; the anticipatory sizer
   (§(ii)) is the one that actually does the lead-time projection.

These are orthogonal: "sees future arrivals" (axis 1) is about *estimating
demand*; "compensates for setup" (axis 2) is about *acting early enough for that
demand to be met*. A sizer can have either, both, or neither. The **ideal**
baseline bundles perfect axis-1 (centered) with axis-2-made-moot (`setup=0`).

**The demand rate (DR) is a demand *estimate*, not a measurement.** Every sizer's
rate term is the **demand rate** `DR(t) = arrival_rate(t) × E[size]` (tokens/s;
code identifier `owr`). The
arrival *count* is observable, but a request's *work* (its size in tokens) is
**not** known when it arrives — real serving knows the prefill/input length at
admission but not the decode/output length. Summing the in-window request sizes
is a valid proxy for DR only under the **stationary-shape assumption**: the
arrival *rate* varies over time, but the request-size *distribution* does not, so
the windowed size-sum equals `measured_arrival_rate × E[size]`. In WVA terms the
sim collapses prefill-known + decode-unknown into a single unknown `size`; a
later phase can split them and make `E[size]` time-varying.

**Thresholds (apply to every sizer).** Sizing is driven by *two* utilization
thresholds, not one:
- **Scale-up headroom** — target utilization on the way up (e.g. work the fleet at
  ~80 %, i.e. `headroom ≈ 1.25`). Currently the only threshold wired
  (`headroom=1.2`).
- **Scale-down threshold** — a *lower* utilization (e.g. 60 %) that must be crossed
  before removing a replica, giving a **hysteresis band** that prevents flapping.
  **Not yet implemented** — the sizers currently have no distinct scale-down
  threshold. Needed before the strategies are a fair analog of real HPA/KEDA
  behavior.

### (i) Current-Q — reactive backlog-drain *(built)*

`gen_supply_queue_aware`. Target rate:

```
target_rate = owr(t) + backlog / drain_time            # owr is TRAILING here
n_replicas  = ceil(headroom · target_rate / per_backend)
per_backend = ⌊sat_frac·C⌋ · service_rate              # usable, not raw C
```

`drain_time` is the time-to-clear dial: the controller sizes to drain the current
backlog over `drain_time` seconds. A fluid forward pass integrates the backlog
under the capacity *actually up* at `t` (replicas ordered now boot `setup` later):
`backlog += (owr − up_capacity) · decision_interval`.

This sizer is deliberately on the **trailing / no-setup-compensation** corner of
the two axes above: its `owr(t)` uses a trailing range `[t−sizing_range, t]` (it
cannot peek at future arrivals), and it does nothing about boot lead time except
react to the backlog that lead time causes. That is exactly what makes it a fair
analog of an off-the-shelf reactive controller — and what the anticipatory sizer
(§(ii)) improves on.

> **Why time-to-clear (option a).** The backlog dial could be framed three ways:
> **(a)** *time-to-clear* — drain the backlog over a fixed `drain_time` (adds a
> bounded fixed latency; chosen as the first step); **(b)** *rate-of-clear* —
> target a fixed drain *rate*; **(c)** *impact-of-not-clearing* — size to the
> *cost* of a standing queue (a longer queue means higher failure). `drain_time`
> may also need to **depend on queue size** rather than be a constant — open
> question, not yet resolved.

**The flaw this demo exposes — integral windup.** During the boot window the
controller re-orders the *same* backlog every tick, because it does **not credit
replicas already in-flight** (ordered but still booting). So it keeps commanding
more capacity for a backlog that is already being addressed by pending boots →
overshoot, then a late over-provisioned tail.

> **Note on the trailing rate term.** This sizer uses a **trailing** `owr` window
> *by design* — it is the reactive baseline, and a reactive controller cannot know
> future arrivals. (An earlier draft flagged this as a bug to fix by centering the
> window, per Dean's "rate is not supposed to lag — we know when requests arrive."
> That correction applies to the *ideal* sizer — `gen_supply_perfect`, which is
> centered — not here: the whole point of this strategy is to show what a sizer
> that *can't* peek does. Knowing arrivals ahead of time is axis 1 above, and it's
> precisely the ability the anticipatory sizer adds.)

### (ii) Qexp — anticipatory / dead-time-compensated *(built)*

`gen_supply_queue_aware_exp`. The fix "beyond what regular HPA-like autoscalers
do": a **periodic control loop**. Every `decision_interval` it re-reads the
observable state — backlog level `B`, up-capacity `U`, and the pending replicas
already ordered with their **estimated** land-times — projects the backlog forward
under that committed boot schedule, and sizes to the projected **peak**:

```
# roll B forward over the committed boot schedule; take the highest point reached
B_peak, t_peak = peak_backlog(t, owr, B_now)     # peak, not now, not residual
target_rate    = owr + B_peak / drain_time
desired        = ceil(headroom · target_rate / per_backend)
actuate        = desired − up − pending           # uniform: only the shortfall
```

Two design points make this work where the reactive sizer (i) windup-fails:

- **Size to the PEAK, not the endpoint.** An earlier attempt integrated the
  projection *to its endpoint* — but under the committed boots the endpoint backlog
  drains toward its residual (→ 0), which drops the drain term and makes the loop
  **cancel its own pending** (self-defeating oscillation). Sizing to the peak of
  the projection fixes this: the peak sits at a physical land-time, so the drain
  deadline doesn't re-clock every tick and the loop commits to a stable target and
  **holds through the boot** instead of chasing.
- **Credit in-flight boots at their estimated land-times.** Pending replicas are
  counted toward the projected capacity at `max(t, start + proj_setup)`, so the
  loop orders only the shortfall — exactly what kills the integral windup in (i).

**The observability wall (why this is a *loop*, not a schedule).** A real system
exposes only the queue **LEVEL** — depth right now — never per-request departures
or per-batch drain rates. So a deployable sizer *cannot* track cohorts through the
queue; it can only read the current level and react. Qexp respects this: the
projection is a within-tick *prediction* used to size, but scale-down is driven by
the **observed** backlog dropping, and every tick re-reads the true level. The
constant-demand and boot-lead assumptions the projection makes are simplifications
the loop **self-corrects against — it never depends on them being right.** This is
what keeps Qexp a deployable controller rather than a paper policy that assumes
information the system can't emit.

**`proj_setup` — the conservatism dial (finding, resynced 2026-08-05 to
sat_frac=0.85 / hr=1.3).** The projection's assumed boot lead (`proj_setup`) is a
*separate knob* from the boot lag the sim actually applies (`setup`). Sweeping it
(sim boots in 90 s regardless):

- **`proj_setup < setup`** (under-predict) → the loop anticipates less and drifts
  toward the reactive sizer; at `proj_setup ≤ 45` it collapses onto reactive's
  numbers exactly (good% 32.9 %, p90 40.2 s).
- **`proj_setup = setup`** (honest, 90) → good% 70.7 %, p90 30.7 s — already well
  above reactive, but **not** the peak.
- **`proj_setup > setup`** (over-predict) → good% *keeps climbing* and the tail
  keeps shrinking: **78 % prompt at 120–135** (p90 17.6 s) — a plateau, the demo's
  operating point. Push further and it **collapses**: at 180 good% drops to 35.4 %
  (decision-flap — the projection orders so far ahead that batches land, drain, and
  re-order out of phase), though the tail stays short (p90 16.8 s).

So the earlier "good% peaks at the honest value" reading no longer holds under the
0.85/1.3 calibration: good% is *maximized by moderate over-prediction* (~120–135),
tail latency improves monotonically with over-prediction until the flap, and
extreme over-prediction is unstable. `proj_setup` remains a genuine tuning dial
(promptness vs tail vs cost), not a correctness knob — the loop is self-correcting
across the useful range and only the far over-predict edge is pathological. **The
demo runs `proj_setup = 120`** (top of the good% plateau, best tail before the flap).

**`boot_stagger` — cascading boot (modelling nuance, deferred).** Both sizers accept
`boot_stagger`: replicas minted in one tick land staggered at `t + setup + j·u`
(`j` = within-batch index) rather than all at once. On loads that mint one replica
per tick (e.g. `bump`) this is a no-op; on `step`/`spike` (multi-replica batches) it
bites, and Qexp degrades more gracefully than reactive. **Open question, deferred at
Dean's direction:** whether the right model is this *within-batch* stagger or a
*global boot-concurrency pipeline* (a cap on how many replicas can boot at once
across the whole fleet). Not resolved here.

### (iii) HPA-queue — plain queue-ratio baseline *(built)*

`gen_supply` via `run_closed_loop(kind="queue")`. `desired = ceil(Q)` — KEDA
`AverageValue` target 1/replica, so the per-replica target makes the current
replica count cancel out (the sizer is stateless in `n`). Unlike the open-loop
sizers above these baselines are **closed-loop**: each `decision_interval` (15 s)
they read the *actual* simulated queue signal, trailing-averaged over a
`metric_window` (60 s `avg_over_time`), and reconcile the live fleet — no foresight,
purely reactive. Empty signal → hold at current `n` (cold start → 1); clamped to
`[minReplicaCount, maxReplicaCount] = [1, 10]`. This is the baseline that **does not
solve the problem**: no dead-time compensation. Under 90 s boot it sees the whole
cold-start backlog and orders it as replicas, pinning at the cap — completes and is
mostly prompt, but over-provisions (~2.5× the ideal fleet).

### (iv) HPA-concurrency — running-count baseline *(built)*

`run_closed_loop(kind="concurrency")`. `desired = ceil(R / c)` — KEDA `AverageValue`
target `c` running requests/replica. The catch: the running-count signal `R` is
**capacity-capped** (`R ≤ n · ⌊sat_frac·C⌋`), so it **cannot see the queue behind
it**. Under 90 s boot it under-provisions badly — it stalls at a few replicas while
a deep queue builds, and the bulk of requests wait over a minute. The teaching
point: concurrency alone cannot outrun boot lag, because the very signal it scales
on is bounded by the capacity it already has.

### (v) HPA-combined — `max(queue, concurrency)` *(built)*

`run_closed_loop(kind="combined")`. Both triggers, native KEDA **`max`** combine:
scale **up on either**, **down only when both** agree lower —
`desired = max(ceil(Q), ceil(R/c))`. The queue trigger rescues the concurrency
signal's capacity-capped blind spot, so it **matches HPA-queue** (same promptness,
same cost). This is exactly why the well-lit path pairs a saturation/queue trigger
with a running-count trigger — and the demo shows the pairing is dominated by the
queue term on this workload.

### (vi) Static — no-scaling strawman *(built)*

`gen_supply_static`: a **fixed** fleet of `count` replicas, pinned at
`max_replicas` and pre-warmed (`setup = 0`), up for the whole trace, never scaling.
On this bump it never queues → 100 % prompt, but it pays for peak capacity through
every valley: the **most expensive** fleet (~3× ideal) at the **lowest utilisation**.
The "just provision for max" answer, quantified — promptness bought with cost.

**Comparison approach:** the isolating case is the **ideal** (no boot lag) —
`setup=0` removes the dead time, so any difference is pure sizing math. The payoff
run is under the **90 s boot lag**, where Qexp's anticipation pre-orders capacity
before the queue builds. That is exactly where (ii) separates from (i): on the
canonical `bump` workload Qexp reaches **~35 % prompt vs reactive's ~28 %**, a
**shorter tail** (wait p90 43 s vs 51 s) and a **lower queue peak** (583 vs 704) —
at the **same fleet cost** (2130 vs 2169 prov·s). It orders sooner and holds
through the boot instead of chasing the backlog after it has already piled up.
Still no axis-1 foresight: Qexp only projects the *current* queue forward
(axis-2 dead-time compensation), it never sees future arrivals.

---

## 4. Failure accounting — the waiting-time model

How we score request quality. Decisions, all deliberate:

- **Absolute waiting time only — not slowdown ratio.** Quality bands split on the
  raw seconds a request waited before service *started*, not wait normalized by
  request size. **"0 is best."** A slowdown ratio would punish short requests
  unfairly.
- **FIFO / head-of-line is accounted, not fixed.** We put no mechanism in to push
  small requests ahead of large ones. Under FIFO a small request stuck behind a
  big one waits — and we **account** that as failure rather than engineering
  around it. Dean: "I don't want to fix it, just account failure assuming FIFO."
- **Bands** (edges `[2, 15, 30, 45, 60]` s): good (≤2) / almost (≤15) /
  mediocre (≤30) / meh (≤45) / bad (≤60) / failed (>60). `good` and `failed` are
  pinned; the 2–60s middle is an even quality ramp. Colored on an even green →
  red gradient. **Two presentations of the same bands:** the panel-1a stacked figure
  shows the *exclusive* per-band shares (departures colored by band); the comparison
  table (§6.3) and the CDF overlay (§5) show them *cumulatively* — "% served within
  Ns" = the wait CDF sampled at these edges. Same underlying model, two reads.
- **Survivorship bias is corrected.** Percentiles over completed-only requests
  flatter any policy that strands work, so:
  - **completion rate is a headline number** (offered / completed / completed % /
    unfinished).
  - band %s use the **offered** denominator, so the six bands + unfinished% sum
    to 100.
- **`time/work` rows are secondary, not the scored signal.** The comparison table
  still prints `time/work (s/u)` percentiles (the old slowdown-ratio metric). They
  are kept as *informational* context only — **waiting time is what the quality
  bands score.** Don't read the `time/work` rows as the failure model; they're a
  leftover diagnostic and can be dropped if they confuse the story.

---

## 5. Views (rendering)

Six stacked panels sharing one time axis, with common vertical guides so one
instant reads across all panels (`plots.render`):

1. **1a — request throughput + goodput quality**: departure rate stacked by
   waiting-time band; arrival rate overlaid (heavy line) so the gap is visible.
2. **1b — work throughput**: offered vs completed work rate + capacity ceiling
   (Prometheus-style windowed rates). The **purple fill** between the completed-work
   line and the ceiling is *unused capacity* — fleet you paid for that no work
   occupied (the visual twin of a low `utilization` number).
3. **2 — desired vs actual replicas**: stepped, with a draining band. Tiny y-
   offsets so equal desired/actual don't hide each other. Two "took-effect" marker
   sets make the boot/drain lag legible: **purple dotted** verticals where a boot
   completes (a replica's `start+setup` — the moment it joins the actual line), and
   **grey dash-dot** verticals where a drain completes (a stopped replica's
   `actual_down`). The gap between a desired step-up and its purple marker *is* the
   boot lag, drawn to scale.
4. **3 — work delivered per backend (stacked) vs demand & capacity**: each slot's
   band is its **instantaneous** delivered work `in_service × service_rate` —
   visible from the first dispatch, *not* a windowed completion rate — so the stack
   sums to `in_service_total × service_rate`. Overlaid: **work demand**
   `L(t) × service_rate` (work owed by requests *in system*, not by arrival) and the
   **capacity ceiling** `actual × ⌊sat_frac·C⌋ × service_rate` (panel-2 replicas
   expressed in usable work units). The stack rides under demand by exactly the
   queued (starved) work; demand poking above the ceiling marks under-provisioning.
   This is the work-space twin of panel 5 (request-space): panel 3 ≈ panel 5 ×
   `service_rate`. Identical backends read as one pool via a small cycling shade
   palette; slot-pool reuse (LIFO free list + min-heap) keeps the band set small and
   stable (fixed the "57 bands for ~11 backends" problem). A draining backend's
   in-flight work rides **above** the ceiling with a thin **dark solid outline**, so
   drain work reads as distinct from usable capacity (position, not just colour);
   a dotted vertical in the pod's shade marks the instant each pod began draining.
5. **4 — global queue depth.**
6. **5 — concurrency L(t)**: in-system vs being-served vs slot capacity. The
   **purple fill** between being-served and slot capacity is *unused slots* (idle
   capacity paid for — matches panel 1b's unused-capacity fill); the fill between
   in-service and in-system is the queued (waiting) count (Little's Law, L = λ·W).

Plus two standalone/auxiliary figures:

- `render_latency` — per-request time-in-system scatter, colored by request size.
- `render_cumulative` — cumulative A(t) vs D(t); vertical gap = L(t), horizontal
  gap = wait, area between = total time-in-system. **Deferred**: only legible
  zoomed-in / at low N. Revisit as an **animated zoom** that follows the other
  panels' timeline. (Kept in code, disabled.)

**Cross-policy comparison figures** (`plots.py`) — unlike the per-scenario panels
above, these put every policy on one shared axis; the report's *Tradeoffs* tab embeds
them:

- `render_wait_cdf` → **09-wait-cdf.png** — every policy's waiting-time CDF overlaid:
  y = % of *offered* served within *t* (a policy that strands work asymptotes below
  100 %). Vertical guides mark the band edges [2, 15, 30, 45, 60] s, and each legend
  entry carries the policy's billed `prov·s` cost, so promptness and cost read
  together. The continuous view of the §6.3 cumulative rows (same numbers, sampled at
  the edges).
- `render_cost_quality` → **10-cost-quality.png** — cost–quality **Pareto frontier**:
  x = billed fleet-time (`prov·s`), y = promptness (% served ≤15 s). One labelled
  point per policy; the clairvoyant **ideal** is a separate reference star (not
  deployable), and the dashed frontier is computed over the *deployable* policies — a
  point below-and-right of it is dominated. Where "same cost, better quality" (qexp vs
  queue-aware) becomes visible.
- `render_sweep` → **11-sweep-setuplag / 12-sweep-drain / 13-sweep-qexp.png** —
  two-panel parameter sweeps (Panel A: good % solid + wait p90 dashed on a twin axis;
  Panel B: `prov·s` cost), with a dotted baseline guide at the canonical knob value.
  Driven by `sweep.py`; tables mirror to `out/sweep.md`.

---

## 6. Current results

> **Recalibrated 2026-08-05** to the current calibration — `sat_frac=0.85`
> (raised from 0.70, §2.3), `headroom=1.3`, `drain_time=20` for **both** Q sizers
> (level-field rule), `proj_setup=120` for Qexp, `ρ=2.0` concurrency-dependent
> decode (§2.7). Every number in §6.1–§6.4 is re-read from the fresh `out/summary.md`
> and `traces/supply-*.json`; the **headline story shifted** under this calibration
> (see §6.3 "Reading it") — most notably: reactive queue-aware barely moves prompt
> service over plain setup-lag (it only helps the ≤15 s band and worsens the tail),
> Qexp is now the clear breakthrough (**78 % prompt** vs reactive's 33 %), and the
> two fleet-heavy HPA baselines **diverge** (hpa-combined now out-serves hpa-queue,
> which grew a real failed tail).
>
> *Earlier calibration notes (superseded):* 2026-07-31 first `sat_frac=0.7`
> recalibration; 2026-08-02 added the static + three HPA/KEDA baselines and the
> cost rows; 2026-08-03 added the anticipatory **Qexp** sizer and moved the
> quality-band edges to **[2, 15, 30, 45, 60] s**. The 8-scenario structure and
> band edges from those updates still hold; only the numbers changed.

### 6.1 Global parameters (held constant)

All eight scenarios share one workload and one fleet; only the per-scenario knobs
(setup, sizer/policy, `drain_time`, fleet size) vary — so any difference in the
figures is attributable to the policy, not the load. Provenance: anchored to a real
WVA decode-heavy benchmark (peak ~24 req/s, ~1000-token mean work, C=100,
`service_rate ≈ 1000/12` tokens/s, ~90 s boot).

- **Load:** `bump` pattern, duration **600 s**, peak **24 req/s**, mean size
  **1000 tokens** (expo), seed 1.
- **Backends:** **C=100** raw slots, **`sat_frac=0.85`** → usable ceiling **85**
  concurrent, `service_rate ≈ 83.3` tokens/s → usable per-backend ≈ **7083
  tokens/s** (≈ **7.08 req/s** at the 1000-token mean); scale-up headroom **1.3**
  (raw-hardware util target ≈ sat_frac/headroom ≈ 0.85/1.3 ≈ **65 %**). A
  concurrency-dependent decode rate (`ρ=2.0`, §2.7) lets under-full pods finish
  faster and converge to `service_rate` as they pack.
- **Sizer:** `sizing_range` 60 s, `decision_interval` 15 s, **`drain_time` 20 s for
  both queue-aware and Qexp** (the 2026-08-05 level-field rule — the two backlog-drain
  sizers share one deadline so the comparison isolates *anticipation*, not the drain
  knob). Qexp `proj_setup` = **120** (over-anticipates the true 90 s boot; swept-best
  at hr 1.3 — §3(ii)).
- **HPA/KEDA baselines:** `metric_window` **60 s** (trailing `avg_over_time`),
  `max_replicas` **10** (KEDA `maxReplicaCount`), same `decision_interval` 15 s.
- **Static baseline:** fixed fleet pinned at **10** (= `max_replicas`), pre-warmed
  (`setup = 0`).
- **Actuation cap:** since 2026-08-05 the `max_replicas` cap is enforced at actuation for
  **every** sizer, not just HPA/static — the WVA Q sizers are clamped to the same **10** ceiling
  (cap-only, no floor; they still scale to zero). The cap = the no-autoscaling provisioning level
  (= the static pin), *not* the ideal peak (≈5). Value 10 uniform; per-shape overridable to ≤15;
  measured to hold every lesson at 10 (no escalation). Full decision + eval: §8.1 item 11. The
  `bump` results below are byte-identical (WVA peaks at 5 < 10, so the cap never bites on bump).
- **Sampling:** dt 0.25 s, `req_range` 15 s, `work_range` 60 s.
- **Quality bands:** pre-service wait edges [2, 15, 30, 45, 60] s (§4).

### 6.2 Scenarios under test

> **Note (2026-08-03).** The eight rows below are all driven by a single **crafted**
> workload — the symmetric triangular `bump`. Per §1.1(3) these are being reframed
> as **teaching aids** (they isolate algorithm differences), *not* the focus. A
> **realistic** workload set (trapezoid + level-shift up/down, on a nonzero baseline)
> is planned to become the primary demo — see §8.1. The *scenarios* (policy columns)
> stay the same; only the *workload* driving them changes. Nothing here special-cases
> the workload shape (§1.1(1)).

|  | Assumptions | Policy | Settings | What it answers |
|---|---|---|---|---|
| **ideal** | supply materializes instantly | size to **centered** demand rate (DR) × headroom (clairvoyant) | setup=0, drain=0, sizing_range=60 | "what does good look like?" |
| **static** | no autoscaler | **fixed** fleet pinned at the ceiling, pre-warmed | count=10, setup=0 | what does "just provision for max" cost? (100% prompt, most expensive, lowest util) |
| **setup-lag** | 90 s boot lag | **same** demand-tracking commands as ideal | setup=90, sizing_range=60 | does a correct policy survive real boot lag? (no — quality collapses) |
| **queue-aware** | 90 s boot lag | demand-tracking **+ backlog/`drain_time`** drain term; reactive (trailing), no look-ahead | setup=90, sizing_range=60, drain_time=20 | can a reactive backlog term rescue quality? (barely — prompt service stays flat vs setup-lag; it only lifts the ≤15 s band and worsens the tail) |
| **qexp** | 90 s boot lag | anticipatory: **periodic loop** sizing to the projected backlog **peak** over the committed boot schedule; reads only queue LEVEL | setup=90, drain_time=20, proj_setup=120 | does anticipating the boot-window pile-up help? (yes — the breakthrough: 78 % prompt vs reactive's 33 %, far shorter tail, ~same cost) |
| **hpa-queue** | 90 s boot lag | closed-loop KEDA on queue depth, `desired = ceil(Q)` | setup=90, metric_window=60, cap=10 | what does off-the-shelf queue autoscaling do? (64 % prompt but a real failed tail — 6.6 % >60 s — at ~1.8× the ideal fleet) |
| **hpa-concurrency** | 90 s boot lag | closed-loop KEDA on running count, `desired = ceil(R/c)`; capacity-capped signal | setup=90, metric_window=60, cap=10 | can concurrency alone outrun boot lag? (no — 74 % fail; blind to the queue behind it) |
| **hpa-combined** | 90 s boot lag | closed-loop KEDA `max(queue, concurrency)`; up-on-either, down-on-both | setup=90, metric_window=60, cap=10 | does pairing the triggers help? (yes — now the best-served fleet-heavy option, 77 % prompt / 95 % ≤15 s, out-serving hpa-queue) |

### 6.3 Results table (`out/summary.md`)

| metric              | ideal | static | setup-lag | queue-aware |  qexp | hpa-queue | hpa-concurrency | hpa-combined |
|---------------------|------:|-------:|----------:|------------:|------:|----------:|----------------:|-------------:|
| offered             |  7159 |   7159 |      7159 |        7159 |  7159 |      7159 |            7159 |         7159 |
| completed           |  7159 |   7159 |      7159 |        7159 |  7159 |      7159 |            7159 |         7159 |
| completed %         | 100.0 |  100.0 |     100.0 |       100.0 | 100.0 |     100.0 |           100.0 |        100.0 |
| unfinished          |     0 |      0 |         0 |           0 |     0 |         0 |               0 |            0 |
| ≤2s %               | 100.0 |  100.0 |      36.2 |        32.9 |  78.0 |      64.1 |             2.7 |         76.9 |
| ≤15s %              | 100.0 |  100.0 |      54.9 |        72.1 |  88.9 |      70.4 |             4.2 |         95.4 |
| ≤30s %              | 100.0 |  100.0 |      87.2 |        84.5 |  93.1 |      78.0 |             6.3 |         96.8 |
| ≤45s %              | 100.0 |  100.0 |      98.9 |        92.2 |  95.4 |      86.5 |            18.1 |         98.9 |
| ≤60s %              | 100.0 |  100.0 |      99.6 |        98.9 |  98.9 |      93.4 |            26.2 |         99.6 |
| failed (>60s) %     |   0.0 |    0.0 |       0.4 |         1.1 |   1.1 |       6.6 |            73.8 |          0.4 |
| wait avg (s)        |   0.0 |    0.0 |      13.1 |        14.0 |   5.1 |      13.5 |            70.9 |          2.6 |
| wait p50 (s)        |   0.0 |    0.0 |       9.2 |        11.0 |   0.0 |       0.0 |            76.7 |          0.0 |
| wait p90 (s)        |   0.0 |    0.0 |      31.7 |        40.2 |  17.6 |      52.6 |            95.2 |          4.5 |
| wait p95 (s)        |   0.0 |    0.0 |      36.2 |        49.6 |  40.4 |      63.3 |            95.8 |         10.4 |
| wait p99 (s)        |   0.0 |    0.0 |      47.0 |        62.0 |  62.0 |      71.5 |            96.7 |         47.0 |
| replicas avg        |  2.86 |  10.00 |      2.18 |        2.29 |  2.40 |      5.26 |            1.96 |         5.40 |
| replicas max        |     5 |     10 |         4 |           4 |     4 |        10 |               4 |           10 |
| replica·seconds     |  1714 |   6001 |      1309 |        1376 |  1440 |      3159 |            1179 |         3242 |
| provisioned·seconds |  1714 |   6001 |      1714 |        1872 |  1920 |      4869 |            1599 |         4772 |
| boot-lag waste·s    |     0 |      0 |       405 |         495 |   480 |      1710 |             420 |         1530 |
| utilization         |  0.59 |   0.17 |      0.77 |        0.73 |  0.70 |      0.32 |            0.86 |         0.31 |

*(Quality rows are the **cumulative** wait CDF sampled at each band edge — "% of
offered served within Ns" — matching `out/summary.md`. `failed (>60s) %` = 100 − ≤60s
(unfinished = 0 here); it is shown for the headline even though `summary.md` derives
rather than prints it. Per-scenario replica lifecycles / peak-queue depths are read
from the traces, not `summary.md`; see §6.4. `time/work` percentiles are in the file
but omitted here — informational only, see §4.)*

**Metrics** (one line each): **offered** — arrival denominator (every request that
appeared; anti-survivorship). **completed / %** — did it finish at all.
**unfinished** — stranded, never served. **≤Ns %** — cumulative share of *offered*
served within N s (the wait CDF sampled at each band edge; monotonic down the rows) —
**this is the scored signal**; `failed (>60s) %` = 100 − ≤60s. (Exclusive per-band
shares still drive the panel-1a stacked figure, §5.)
**wait avg/pNN** — pre-service wait (dispatch − arrival) over completed requests.
**replicas avg/max** — ready count. **replica·seconds** — ∫ ready dt, a cost proxy.
**provisioned·seconds** — total *billed* fleet-time incl. the boot window
(start..up) and draining tail — the number the invoice reflects. **boot-lag waste·s**
— `provisioned − ready` = fleet-time paid for while replicas were still booting (not
yet serving). **utilization** — delivered work ÷ usable throughput-capacity paid
for; well below 1 = idle/over-provisioned, close to 1 = fully packed (which can
*still* fail latency — hpa-concurrency reads the **highest** util in the table, 0.86,
while failing 73.8 % — so read it next to the % bands, never alone).

**Reading it — the honest headline (this is the B1 story):**

Under this calibration the smooth bump is **gentle enough that every scenario
completes 100 %** — nobody is *permanently* stranded, even at 90 s boot. So the
story is **not** "completion rescue." Every difference lives in **when** work is
served (the waiting-quality mix), in the **tail**, and in the **price** paid for
promptness (cost + utilisation):

- **Ideal**: 100 % served in ≤2 s, peak queue **0**, at the smallest scaling fleet
  (peak 5, 1714 replica·s, util 0.59). The centered clairvoyant window provisions
  *ahead* of the ramp, so on a smooth bump it never queues. What good looks like.
- **Static (no scaling)**: also 100 % prompt — but it pins **10** replicas for the
  whole run, so it pays **6001 replica·s** (~3.5× ideal) at util **0.17** — the
  *most expensive, least efficient* way to be prompt. The "just provision for max"
  answer, quantified.
- **Setup-lag**: still 100 % complete, but the 90 s boot runs the up-ramp
  under-provisioned, so only **36.2 %** are served promptly (≤2 s) and **54.9 %
  within 15 s**; the mass clears later — **87.2 % by 30 s, 98.9 % by 45 s**, only
  **0.4 %** past 60 s (p90 31.7 s). Same commands as ideal, each landing 90 s late:
  **correct policy, fatal timing.**
- **Queue-aware**: the surprise of this calibration — the reactive backlog term
  **does not rescue prompt service**. ≤2 s actually dips to **32.9 %** (vs
  setup-lag's 36.2 %) and the median wait is no better (p50 11.0 vs 9.2 s); all it
  does is shift mass into the 2–15 s window (**≤15 s 72.1 %** vs 54.9 %) while
  **stretching the far tail** (p90 **40.2** vs 31.7, failed 1.1 % vs 0.4 %, peak
  queue 607 vs 523), at +67 replica·s. Reacting to a backlog you can only clear
  90 s later trades tail for mid-band and leaves promptness flat — **reacting isn't
  enough.**
- **qexp**: the anticipatory periodic loop — **the breakthrough.** Sizing to the
  *projected* backlog peak (and crediting in-flight boots) lets it order sooner and
  hold, so it beats reactive queue-aware on **every** axis at once: **78.0 % prompt**
  (≤2 s, vs 32.9 %), **88.9 % within 15 s** (vs 72.1 %), median wait **0.0 s** (vs
  11.0), **far shorter tail** (p90 **17.6** vs 40.2), and a **lower queue peak**
  (428 vs 607) — all at **essentially the same cost** (1440 replica·s / 1920 prov·s
  vs 1376 / 1872, +3 %, same peak-4 fleet). This is the payoff of dead-time
  compensation *without* foresight: it never sees future arrivals, it just stops
  chasing a backlog that its own pending boots are already about to clear.
- **hpa-queue**: off-the-shelf KEDA on queue depth. Reactive, no dead-time
  compensation — on a queue signal it sees the cold-start backlog and pins at the
  cap, but the late-landing fleet still leaves a **real failed tail**: **64.1 %
  prompt** but **6.6 % fail (>60 s)** and p90 **52.6 s**, all while burning **3159
  replica·s** (~1.8× ideal) at util **0.32**. Fleet-heavy *and* tail-heavy — the
  worst of both among the well-served options.
- **hpa-concurrency**: KEDA on running-count only. The signal is **capacity-capped**
  (`R ≤ n·usable_C`), so it cannot see the queue behind it — it stalls at **4**
  replicas while a **2004-deep** queue builds and **73.8 % of requests fail (>60 s)**,
  avg wait **70.9 s**. Its util reads **0.86** — the *highest in the table*, fully
  packed and still failing: the single sharpest lesson in the deck, **high
  utilisation is not success.** Concurrency alone cannot outrun boot lag.
- **hpa-combined**: `max(queue, concurrency)`. Under this calibration the two
  triggers **diverge** — the concurrency term front-loads capacity the queue signal
  alone wouldn't yet justify, so combined orders earlier, holds a **far shallower
  queue** (peak 327 vs hpa-queue's 1344), and becomes the **best-served fleet-heavy
  option**: **76.9 % prompt, 95.4 % ≤15 s, p90 4.5 s, 0.4 % fail** — out-serving
  hpa-queue on every quality axis for a hair more fleet (3242 vs 3159 replica·s,
  util 0.31). Pairing the triggers is no longer a tie with queue-alone; it is a
  genuine win here.

So the honest takeaway is a **two-axis** one: promptness and cost are separate
dials, and no *reactive* policy here gets both. Static buys promptness with ~3.5×
the ideal fleet; hpa-queue/combined buy it with ~1.8–1.9× (and hpa-queue still
leaves a 6.6 % failed tail); hpa-concurrency is cheap and catastrophic; queue-aware
barely moves promptness and worsens the tail. The dramatic "recovers stranded
work" story needs a sharper/sustained overload the smooth bump doesn't produce.
This is exactly what **anticipation** (Qexp, §3(ii)) delivers: it is the only sizer
here that is *both* prompt *and* lean — best-in-class quality among the lag-90
sizers at the leanest fleet, because it orders *before* the queue builds and stops
chasing once its pending boots are committed, instead of over-buying (static,
hpa-*) or chasing after the fact (queue-aware). It gets there **without foresight**
— axis-2 dead-time compensation alone. The one axis it still cannot cross is axis-1
(seeing future arrivals), which is why even Qexp trails the clairvoyant ideal.

**Why even the *ideal* sizer eventually fails (the §6.5 stress point).** Ideal's
peak queue is 0 here only because the bump varies *slowly relative to the sizing
range* — a 60 s centered window peeks ~30 s ahead and provisions before the ramp
arrives. That protection is an artifact of the smooth shape, not of clairvoyance
per se. See §6.5.

### 6.4 Decision-point walkthrough

Grounded in the actual supply traces (`traces/supply-*.json`; a distinct replica
start = a scale-up command, a distinct stop = a scale-down):

- **ideal** — 5 scale-ups (t=0…300), peak ordered **5** @ t=300, drains from
  t=345 as the bump recedes. setup=0 → actual == desired. The reference trace.
- **setup-lag** — the *identical* command sequence (same 5-replica peak, same
  down-schedule at t=345…600); the decisions were right, each replica just lands
  **90 s late**, so actual capacity lags demand through the entire ramp (peak
  *actual* only 4 — the 5th lands after the peak has passed). **Correct policy,
  fatal timing assumption.**
- **queue-aware** — **7** lifecycle replicas, scale-ups firing t=15…330; peak
  ordered is **still 5** (same as ideal), reached **earlier** (@ t≈165 vs 300) and
  held longer, plus **two** extra lifecycle replicas. The backlog term front-loads
  capacity while the boot window lets the queue build — and, because it does **not
  credit replicas already booting**, orders more than needed, which lands after the
  peak. This is the *residual* of the integral windup (much milder here than under a
  sharper load), and the visual motivation for Qexp: credit in-flight boots and that
  late-ordered overshoot moves to where it helps.
- **qexp** — **8** lifecycle replicas and peak ordered **5**, but the boots are
  **front-loaded** relative to queue-aware: scale-ups fire at t≈15/45/60/75/90 (vs
  queue-aware's 15/75/105/135/165), so capacity is committed *earlier* into the boot
  window. Because the loop **credits in-flight boots at their projected land-times**,
  it doesn't windup-order; instead it commits to the peak target, holds, and then
  **retires on the observed backlog clearing** (two early retires at t≈105 as the
  queue drains, the rest from t≈375). The visible payoff vs queue-aware is a **lower
  queue peak (428 vs 607)** for the same peak-ordered fleet — anticipation spends the
  same replicas *sooner*, where they suppress the pile-up instead of chasing it.
- **static** — **no** scale commands: 10 replicas up at t=0, down at end. Flat
  desired == actual == 10 across the whole trace (setup=0, pre-warmed). The panel-2
  line is a plateau — the visual "no autoscaler" contrast to every other panel's
  staircase.
- **hpa-queue** — closed-loop, decisions every 15 s off the trailing-60 s queue
  average. During the boot window the queue signal is large (nothing is serving
  yet), so it ramps hard and **pins at the cap (10)** through the ramp, then drains
  as the trailing average falls. Peak actual **10** vs ideal's 5 — the
  over-provisioning is visible as a panel-2 plateau twice ideal's height; yet the
  late-landing fleet still lets the queue crest at **1344** before it clears.
- **hpa-concurrency** — closed-loop off running-count. The signal saturates at
  `n·usable_C`, so `ceil(R/c)` never asks for more than a handful: peak actual
  **4** (scale-ups only at t=0/150/285/405/510), held flat while panel-4 shows a
  queue climbing past **2000** and panel-5 shows L far above the usable-slot ceiling.
  The panels make the capacity-capped blind spot literal — a small flat fleet under
  a mountain of backlog.
- **hpa-combined** — **no longer the same trace as hpa-queue** under this calibration.
  The `max(queue, concurrency)` lets the **concurrency term bind early** — it front-
  loads a burst of replicas in the first ~30 s (scale-ups clustered at t≈0/15/30)
  that the queue term alone wouldn't yet justify, so capacity is committed sooner and
  the queue crests at only **327** (vs hpa-queue's 1344). Same 10-replica cap, but a
  visibly earlier ramp on panel 2 and a far shallower panel-4 queue — the visual
  proof that pairing the triggers *helps* here rather than merely echoing the queue
  term.

### 6.5 Stress experiment — making even the ideal sizer queue (B2)

A separate, standalone experiment (`stress_ideal.py` → `out/stress-ideal-spike.png`),
**not wired into the multi-scenario report**. Its only job is to make one teaching point
that the smooth bump can't: *perfect future knowledge is not enough if you compress
it into a windowed average to size a fixed replica count.*

Same calibration as `ideal` (`setup=0`, centered window, headroom 1.3, sat_frac
0.85, `sizing_range=60`) — **only the demand shape changes**: instead of the slow
bump we drive the `spike` pattern (steady baseline at 0.4×peak with a **6 s burst to
3×peak** at mid-run). The burst is far shorter than the 60 s sizing range, so even a
perfectly clairvoyant *centered* window averages it into the window mean and sizes
for the mean, not the peak. With `setup=0` the replicas are up instantly — there
simply aren't enough of them for the burst.

Result: peak queue **170**, peak L **425** (well above the usable-slot ceiling),
and prompt service drops from ideal's 100 % to **95.1 %** good (p99 wait 7.0 s) —
the ideal sizer now visibly queues. The plot shows the queue spike in panel 4,
in-system L above the usable-slot capacity in panel 5, and work demand poking above
the ceiling in panel 3. The lesson for the deck: **windowed sizing of a fixed
replica count has a residual failure mode against sub-window bursts, independent of
setup and independent of how well you can see the future.**

**Distinct from the rendered `spike` shape (§8.1 item 11).** This standalone experiment is
*ideal-only* (`setup=0`) and isolates the windowed-sizing failure mode. The demo deck also carries
`spike` as a full first-class shape run through **all 8 policies** with realistic `setup=90` — which
makes a *different* point: for a burst shorter than the boot time the bottleneck is **boot lag, not
the sizing algorithm**, so every achievable autoscaler drops requests and only pre-warmed
`static`/no-scaling absorbs it. The two are complementary spike lessons, not duplicates.

---

## 7. Prior art

### 7.1 Visualization prior art — **COMPLETED** (2026-07-30 subagent scan)

A focused scan of *how others visualize* autoscaling / queueing tradeoffs. These
are real sources with reusable visuals — kept here so we don't re-run this search.
⭐ = highest-leverage ("steal first").

**1. Little's Law (L = λW)**
- ⭐ **rugu.dev — "A Little Explanation of Little's Law"**
  (https://rugu.dev/en/blog/littles-law/) — coffee-shop animation: inflow at λ,
  occupancy W, live "inside" counter. Cleanest way to make L = λW *felt*.
- ⭐ **Ward Whitt — cumulative-arrivals figure** — A(t) and D(t) as two staircases;
  **vertical gap = L(t), horizontal gap = W, area between = total customer-time.**
  One figure ties L, λ, W together geometrically. (This is our deferred
  `render_cumulative`.)
- **Dan Slimmon — "Using Little's Law to scale applications"** — concurrency =
  throughput × latency; good "why an operator cares" callout.

**2. Autoscaler comparison / evaluation**
- ⭐ **Judoscale "hug the line" charts** — required vs provisioned capacity;
  reactive scaling lags as a staircase leaving a **shaded shortfall gap (SLO
  breach)** on the way up and an **overshoot gap (waste)** on the way down. The
  shaded "gap = pain" area is the most reusable comparison visual.
- ⭐ **AWS predictive-scaling docs** — two stacked series: actual-vs-predicted
  *load*, then resulting *capacity*. Clean predictive-vs-reactive template.
- **Kedify / KEDA-vs-HPA** — architecture + scale-to-zero timelines.
- **Reactive-vs-proactive surveys (arXiv)** — replica-count-vs-time, SLO-violation
  %, cost/over-provisioning bars. Reference for *which* metrics belong on axes.

**3. Queueing simulators with visualization**
- ⭐ **QueueForge — interactive M/M/c** — sliders for λ, μ, c; live queue length
  overlaying **empirical vs theoretical** steady state (the "trust but verify"
  overlay).
- ⭐ **Joey Lynch — supermarket-queue sim** — shared vs per-server queue, latency
  as **box/violin distributions** to expose p99 ("show the whole distribution").
- **Wolfram — "Simulating a Multiple-Server Queue"** — static jobs-in-c-servers layout.

**4. LLM-inference-serving autoscaling**
- ⭐ **Anyscale continuous-batching animation** — grid: rows = sequences, cols =
  decode steps; static batching leaves rows idle, continuous batching backfills
  freed slots. The definitive "LLM throughput is non-classical" visual.
- ⭐ **DistServe / hao-ai-lab — throughput vs *goodput* under SLO** — goodput = req/s
  still meeting TTFT/TPOT SLO; throughput keeps rising while goodput collapses past
  a load point. "Throughput lies, goodput is the real capacity."
- **SLO-aware serving papers** — latency-vs-concurrency knees, SLO-attainment
  heatmaps over (load × replicas).
- **Runpod/Spheron vLLM benchmarks** — empirical tok/s rising-then-flattening vs
  batch size; real numbers to seed a curve.

**5. Throughput–latency–concurrency & USL**
- ⭐ **Neil Gunther — Universal Scalability Law** — throughput rises, saturates,
  then **retrogrades downward** past peak concurrency (coherency cost) — unlike
  Amdahl's plateau. The "more concurrency makes it worse" visual.
- **Graphium Labs USL charts** — linear-ideal vs contention-bounded vs
  coherency-regressive on one log-x axis.
- **Baron Schwartz / VividCortex USL** — fits USL to measured points, α/β sliders.

**Cross-cutting "steal" shortlist:**
1. Cumulative arrivals/departures with shaded area (Little's Law).
2. Demand-vs-provisioned capacity with shaded gap (autoscaler comparison).
3. Colored-cell batching animation (LLM).
4. Throughput-vs-goodput divergence (SLO).
5. USL retrograde curve.

**How it maps to what we have (validates the panel set, gives an ordering):**
- **Steal #2 (shaded demand-vs-provisioned gap)** = panel 2 (desired vs actual)
  the moment setup lag opens the gap — one parameter away, *the* leadership-legible
  picture. **Already realized** in the setup-lag scenario.
- **Steal #1 (cumulative A(t)/D(t))** = our `render_cumulative` (built, deferred as
  an animated zoom). We already log every arrival/departure, so it *derives* the
  queue/concurrency panels rather than asserting them.
- **Steal #4 (throughput vs goodput)** = a cheap SLO overlay on panel 1a; we have
  per-request latency. Sharpest scaling-signal argument for a WVA audience.
- **Steal #3 (continuous batching) & #5 (USL retrograde)** = **phase-2 only** — they
  need the concurrency-dependent service model (§2.7). Note #3 (batching speed-up)
  *is* the §2.7 model; #5 (retrograde) needs oversubscription past the cap, which
  §2.7 does not produce on its own — that stays a synthetic/imported-trace extension.

> Two interactive pages (an LLM-serving explainer at mbrenndoerfer.com and a couple
> vendor blogs) **403'd automated fetch** — described from snippets; worth a manual
> visit if we build the LLM-specific visuals.

### 7.2 Anticipation / control-theory prior art — **NOT YET RUN**

Distinct from §7.1. This is the search for the *sizing-math* regime behind Qexp —
dead-time compensation, feed-forward, anti-windup, and the exact KEDA/HPA queue
formula. **Not done** (Qexp is built from first principles; this validates the
*naming*, not the mechanism). Any control-theory framing (e.g. Smith predictor,
anti-windup, Erlang-C) is a **hypothesis to verify against a real source**, not an
established citation — do not write it up as fact until searched. This is
next-step (1) in §8.1.

### 7.3 Workload / benchmarking prior art — **NOT YET RUN** (2026-08-03)

Before implementing more workloads (§8.1), survey how the field actually drives
autoscaling evaluation, so our "realistic" shapes are grounded rather than invented:

1. **Inference-benchmarking workloads used for autoscaling evaluation** — what
   arrival patterns / traces does the literature and the llm-d / vLLM ecosystem use
   when they measure autoscaling (not just steady-state throughput)? Look for
   published traces, level-shift/diurnal profiles, and any standard "burst" fixtures.
2. **`guidellm` and `inference-perf` generation capabilities** — what arrival
   processes can each actually emit? Constant-rate, Poisson, ramps, traces-from-file?
3. **Known gap to confirm.** Most tools drive a **homogeneous Poisson process at a
   constant rate**, which produces **large traffic spikes** (high variance) rather
   than the *smooth mean signal + bounded noise* we want (§1.1(3): slow-large for the
   controller, small-high-variance for the queue). Confirm which tools — if any —
   support a controlled mean profile with separately-bounded noise, vs only raw
   Poisson. This shapes whether our realistic fixtures can be reproduced by a real
   benchmark tool later (the two-trace ingestion of §1.1(2)).

This is a prior-art investigation, deferred; do not block workload implementation's
*design* on it, but run it before finalizing the realistic fixtures.

---

## 8. Roadmap

### 8.1 Next steps (immediate — do in this order)

> ▶ **BATCH COMPLETE (2026-08-05) — committed `a8c763d2`.** Item 10 **(a)/(b)/(c)/(d) DONE**
> and **item 8 DONE**: `run.py` has a single shared `DRAIN_TIME=20`, `SAT_FRAC=0.85`,
> `HEADROOM=1.3`, `QEXP_PROJ_SETUP=120` (good% plateau 78 % at 120–135, best tail before the
> flap; §3(ii)); `sweep.py` unified `BASE_DRAIN`/`BASE_HR` **and memoizes table data to
> `out/.sweep-cache.json`** (item 10(d): ~22 s cold → ~1.6 s warm, source-hash invalidated,
> plots.py excluded); §2.3/§2.6/§3(ii)/§6 narrative + `report.py` all re-synced to the new
> calibration. **Item 8 verdict** (`stability.py` → `out/stability.md`): re-swept
> trapezoid/step-up/step-down (nonzero floor) — `proj_setup=120` and the headroom knee **HOLD**
> across all shapes; `drain=20` is FLAGGED only because it is the deliberate level-field
> constant, **not** re-tuned (shape-best is drain=3 by construction). So `(drain=20, hr=1.3,
> sat=0.85, proj=120)` is confirmed shape-robust, not a bump artefact. Also folded in: the
> cost-quality frontier now overlays both Q sizers at headroom 1.5/2.0 (hollow markers —
> anticipation dominates static margin). **Open (NOT live threads):** item 1 (control-theory
> prior-art search, §7.2/§7.3), item 6, item 7(b) framing. Prior viz commits: p1b polish
> `75f1f333`; item 7(a)/(b) sweeps `fcabd6ab`.

1. [ ] **Anticipation/control-theory prior-art search** (§7.2) — the visualization
   scan is already done (§7.1); this remaining one covers the *sizing math* only.
   Run it *before* writing any control-theory framing into §3. Verify or drop
   Smith-predictor / anti-windup / KEDA-HPA-formula / Erlang-C against real sources.
   **Still open** — Qexp is implemented from first principles; the control-theory
   *naming* of what it does (dead-time compensation, anti-windup) is unverified.
2. [x] **Pin down the Qexp logic precisely** (§3(ii)) — settled as a **periodic
   control loop** that sizes to the projected backlog **peak** and credits in-flight
   boots at their estimated land-times. The earlier "project to `t+setup`, size the
   shortfall" framing was refined: sizing to the *endpoint* self-cancels pending
   (windup in reverse), so the loop sizes to the peak instead. **Done.**
3. [x] **Implement Qexp sizer** (§3(ii)) — `gen_supply_queue_aware_exp`;
   periodic loop, credits in-flight boots, `proj_setup` conservatism dial + optional
   `boot_stagger`. **Done** — scenario `08-queue-aware-exp` in the report (§6).
4. [x] **Implement HPA baselines** (§3(iii)–(vi)) — closed-loop KEDA queue /
   concurrency / combined (`run_closed_loop`) plus the static no-scaling strawman
   (`gen_supply_static`). **Done** — all four are in the 8-scenario report (§6).
5. [x] **Qexp comparison** — under the 90 s boot lag Qexp separates cleanly from the
   reactive baselines: best quality among the lag-90 sizers at the leanest fleet
   (§6.3). The `proj_setup` sweep (`sweep.py`, Sweeps tab) shows it stays stable and
   self-correcting across the dial. **Done.**
6. [ ] **Resolve the cascade-boot model** (deferred at Dean's direction, §3(ii)) —
   decide whether the boot cascade is best modelled as the current *within-batch*
   `boot_stagger` (replica `j` lands at `t+setup+j·u`) or a *global boot-concurrency
   pipeline* (a cap on simultaneous boots across the whole fleet). Only the latter
   bites on loads that mint one replica per tick; the two differ on step/spike. Not
   yet decided.

   *(The earlier "centered-rate fix for `gen_supply_queue_aware`" item was
   removed: its trailing window is intentional — it's the reactive baseline, which
   by definition cannot peek at future arrivals. Centering is the ideal sizer's
   ability, and adding look-ahead is exactly what Qexp does. See §3(i) note.)*

7. [~] **Knob exploration (2026-08-03) — GATES item 8; (a) landed, (b) built (framing OPEN), (c) parked.**
   Dean wants to try more model capabilities/knobs before the realistic workloads.
   Three, in priority order:
   - **(a) Concurrency-dependent decode rate** → **IMPLEMENTED 2026-08-03** per **§2.7**
     (linear-ITL, `RHO = 2.0` default in `run.py`, sizer↔engine split, exact
     event-driven mechanism in `sim.py`; `rho = 1` = fixed-rate identity). *Observed at
     `headroom = 1.2`:* replica·seconds ↓ / utilization ↑ where pods have slack + drain
     (ideal, setup-lag, queue-aware, Qexp); wait tails ~unchanged (heavy queueing occurs
     while pods are packed, where ρ gives no speedup); static & hpa-concurrency unchanged
     (no drain to accelerate / packed at k≈1). This is why (b) is the payoff — more
     headroom lowers k and makes "headroom buys speed" visible.
   - **(b) Per-replica headroom sweep.** `headroom` is already the fleet-level sizing
     multiplier (§2.6) and the per-replica-slack dial; add it as a **sweep axis** in
     `sweep.py` (esp. alongside queue-aware and Qexp), plus a **2-D sweep**
     (`headroom × drain_time`, `headroom × proj_setup`) to show how much *dynamic*
     reaction can substitute for *static* margin. Richer once (a) lands: lean pods are
     then also *faster*, so headroom trades cost for both slack **and** speed (§2.7
     virtuous cycle).
     - **BUILT 2026-08-03** in `sweep.py`: RHO threaded through (fixes the stale ρ=1
       `sweep.md`); headroom 1-D sweep on queue-aware + Qexp (fig 14); 2-D
       `headroom × drain` (fig 15) and `headroom × proj_setup` (fig 16). The **capacity**
       role is strong and monotone (Qexp good% 23→80 % across headroom 1.0→2.0, `prov·s`
       1784→3050; the substitution surfaces show aggression/anticipation buying back
       *some* margin at their own boot-lag cost).
     - **⚠ OPEN — sleeping on it (2026-08-03; Dean's call, do not resolve unilaterally).**
       The "headroom buys speed" half of the claim above **does not appear on the
       wait-based quality metric**: `good%`/`wait_p90` are byte-identical at ρ=1 vs ρ=2
       for every headroom (only `prov·s` moves, via a shorter drain tail). Structural, not
       a bug — the bands key on *waiting* time, and a backlog keeps pods **packed at
       `usable_C` (k≈1)** where `rate = service_rate`; the ρ speed-up only fires
       *under-full* (k<1), exactly when wait≈0 already. So these sweeps isolate headroom's
       **capacity** role; ρ's benefit is a *service-latency* effect (in `time/work`, not
       plotted). Recorded as a "ρ note" at the foot of `out/sweep.md`.
       - *Dean's real-system connection (2026-08-03):* in production a pod is **probed
         while load is low** (so you observe the *fast* rate), and the **saturation rate
         is guesstimated** — which reframes ρ as a *sizing-uncertainty* source
         (probe-low-k → extrapolate the packed rate the sizer needs), not just a runtime
         speed-up. Possibly a stronger use of the ρ knob than the virtuous-cycle framing.
       - **Options to decide:** (1) accept as-is — sweeps = capacity role; amend §2.7 to
         say the speed benefit is service-latency-only / invisible under backlog; (2) add a
         `time/work`-p90 panel to `render_sweep` so ρ *does* show; (3) reframe §2.7 around
         sizing uncertainty (Dean's probe-at-low-load point). §2.7 / this item's
         virtuous-cycle wording left untouched pending the ruling.
   - **(c) Little's law (L = λ·W) — parked.** We already plot L(t) and title panel 5
     `L = λ·W` (§5), but do not *demonstrate* the identity. If surfaced, do it as a
     **steady-state annotation on a plateau** ("L ≈ X = λ(Y)·W(Z)"), never a
     per-instant `λ(t)·W̄` overlay (it diverges on transients — looks broken).
     Naturally downstream of the realistic plateaus (item 8). Note: with (a), W becomes
     load-dependent — a nice teaching point that Little assumes nothing about a constant
     service rate.
8. [x] **Realistic workload set** (§1.1(3), §6.2) — **DONE (2026-08-05): fixtures + stability
   sweep + per-shape demo figures + HTML integration all landed (see item 11).** Added
   `trapezoid` / `stepup` / `stepdown` to `sim.py`'s `rate_profile` (lo = peak/3 ≈ 8,
   hi = peak = 24 req/s, nonzero floor throughout) and a standalone `stability.py` that
   re-sweeps the tuned knobs on every shape. **Verdict (full table `out/stability.md`):**
   the calibration is **shape-robust — no re-tune needed.**
   - **`proj_setup = 120` HOLDS on all four shapes** — shape-best ∈ {120, 135, 180}, and
     120's good% is within 0.7 pp of every shape's own optimum. Anticipation lead is a
     property of the Qexp sizer, not of the bump.
   - **`headroom = 1.3` HOLDS** — the diminishing-returns knee stays at 1.1–1.3 across
     shapes; qexp raw-hw util at 1.3 = 0.59–0.72 (target ≈ 65 %).
   - **`drain = 20` — the one FLAG, and it is EXPECTED, not instability.** Queue-aware's
     own good%-optimum is the most-aggressive grid point (`drain = 3`) on *every* shape
     (a perfectly stable argmax), reachable only by over-provisioning. Holding `drain = 20`
     for both Q sizers is the deliberate **level-field constant** that isolates
     anticipation from aggression; Qexp still beats queue-aware on good% on **every** shape
     at drain=20. **Do NOT re-tune to 3** — the standing level-field rule holds.
   - **Secondary finding — `stepdown` is a pure scale-*down* test (REVISED 2026-08-06, warm
     start).** The original reading — *"cold-start-at-peak is the hardest shape: failed% 15.7 %
     (qexp) / 25.1 % (queue-aware) / 24.0 % (setup-lag), qexp peak fleet 15 replicas"* — was an
     **artifact of cold-booting the fleet from zero at t=0**, not a property of the shape. Any
     shape whose demand *starts* at `hi` was secretly testing a near-instantaneous step **up**
     first, and the startup queue that step built then contaminated the rest of the run. Both
     the fleet and the trailing-window demand estimators are now warm-started at the shape's
     t=0 steady state (§2.4), so `stepdown` finally measures what its name says: **does the
     fleet rescale down as demand falls.** Because scale-down has **zero actuation lag** —
     shedding needs no boot — it is the *honest* and structurally *easy* direction: every sizer
     but one clears the shape outright. The lone straggler is **`hpa-concurrency`**, whose
     running-count signal is capacity-capped and so cannot see the transient at all — a
     structural blind spot of that metric, not a startup artifact. **This also makes `stepdown`
     cap-inert** (it warm-starts at peak and only sheds), so it joins `bump`/`spike` in the
     cap-sweep's no-lesson group and no longer differentiates the Q sizers (item 11).
     *Exact figures are re-frozen in item 11 only after the burn-in prelude lands (§8.2);
     until then read `out/summary-stepdown.md` for the current run.*

   **Per-shape demo figures wired into the viewer — DONE (item 11, 2026-08-05):** all 5 shapes
   (the three above + `bump` reference + `spike` teaching case) now render across Compare / Browse
   / Table / Tradeoffs, and the actuation cap is enforced uniformly. Fixtures added; the crafted
   shapes (`bump`, `spike`) are kept as reference/teaching aids.

   *(original spec, retained:)* Add fixtures to `rate_profile` for shapes that contain
   steady states so right-sizing is visible:
   - **Trapezoid** — baseline → ramp → **hold peak** → ramp → baseline (full
     lifecycle: right-size at both plateaus; overreact-then-relax on each transition).
   - **Level-shift up** — hold `lo` → slow ramp → **hold `hi`** (purest right-sizing
     story: converge to `hi`, relax off the overreaction; static pays `hi` throughout).
   - **Level-shift down** — hold `hi` → slow ramp → **hold `lo`** (scale-down /
     stop-paying; minimal boot-lag waste).

   All on a **nonzero baseline** (prod is never idle); the existing Poisson thinning
   supplies the small high-variance noise the queue absorbs. **Levels decided:**
   `lo ≈ 8`, `hi = 24` req/s (a 3× surge; `hi` matches today's peak so the calibration
   and capacity numbers carry over). Crafted shapes (`bump`, `spike`, `step`) are kept
   but **demoted to teaching aids** (secondary), not removed. Must not special-case
   the workload in any sizer or plot (§1.1(1)).
9. [x] **Scenario chooser in the HTML** (decision-2, 2026-08-03) — **DONE (item 11, 2026-08-05),
   realized as a flat per-shape switcher, not the original two-level category→workload chooser.**
   The two-level design (first pick a category, then the workload) is **superseded**: with only 5
   shapes in one list, a single flat shape switcher across Compare / Browse / Table / Tradeoffs is
   simpler and the "teaching vs real" category naming problem disappears. Affects `out/index.html`
   construction in `report.py` only.

10. [ ] **ACTIVE (2026-08-05) — level-field Qaware/Qexp comparison + sweep caching + then
    demand shapes.** Dean's review of the 7(a)/7(b) sweeps: *"Qaware looks optimized, Qexp does
    not (same as Qaware now) — hard to compare the two as is."* Put both Q sizers on an even
    field, then run the realistic workloads. Four coupled sub-tasks — (a)/(b)/(c) all touch the
    same `run.py` constants and need one fresh sweep to settle the values:

    **DECIDED (2026-08-05) — Dean's rulings on all four:**

    - **(a) Unified `drain_time = 20` for BOTH Q sizers — PERMANENT.** *"20 for now, we can sweep
      later. Going forward we always use same for both Q algorithms."* This is a standing rule:
      the two Q sizers **always share one `drain_time`**. **REVERSES** the earlier split (Qexp was
      pinned at 30 because its own drain=20 regresses good%/cost). Level field beats Qexp's
      absolute numbers — do NOT re-apply the "Qexp regresses at 20" reasoning. Action: collapse
      `DRAIN_TIME`/`QAWARE_DRAIN_TIME` in `run.py` to one `DRAIN_TIME = 20`; both scenarios use
      it; collapse `sweep.py`'s `BASE_DRAIN`/`QAWARE_BASE_DRAIN` to one (both Q sizers star 20);
      drop the "two sizers differ" prose.
    - **(b) Unified knobs across ALL sizers: `SAT_FRAC = 0.85`, `HEADROOM = 1.3`.** Dean corrected
      the cost framing: **cost is ~linear in headroom** (replicas scale linearly with the sizing
      multiplier), so the "+11.6% for 1.2→1.35" I flagged was just the `1.35/1.2` ratio measured
      against the *old* 1.2 baseline — **not** an anomaly, and **a non-issue once the same headroom
      is used across the board** (the comparison stays fair). **The real cost of headroom is
      UTILIZATION:** at headroom `h` and saturation fraction `sat`, raw-hardware utilization ≈
      `sat / h` — old `0.70/1.35 ≈ 52%`. Dean's fix raises **both** levers: `sat_frac 0.70 → 0.85`
      (pack pods closer to the KV ceiling) **and** `headroom → ~1.3`, giving `0.85/1.30 ≈ 65%`.
      **Selection principle:** on the headroom sweep, *"the key is where the graph is most vertical
      — that is where you gain the most"* (max marginal quality per unit headroom/util). `~1.3`
      sits at that steep region. Projection (Qexp) does a *similar* util-vs-quality trade but *less
      linear*. Pick `1.3` — *"gives us enough across the board."* The `≤15s "almost"` second Pareto
      curve is **deferred** (*"we can always add the 'almost' curve later"*); the existing sweeps
      already show the cost/quality trade. **NOTE:** `sat_frac 0.70→0.85` is a **sim recalibration**
      — reinterprets the "KV cap" of §2.3 (line ~181) and shifts `k = in_service/usable_C` in the
      §2.7 decode-rate model; all figures/tables/narrative regenerate. Flag the §2 calibration prose
      for a follow-up pass.
    - **(c) Qexp main plot uses the BEST `proj_setup` from a FRESH sweep at drain=20** — *"yes, we
      need a new sweep for Qexp at 20s drain."* proj=90 was the honest value at the OLD
      drain=30/hr=1.2/sat=0.70 point; **invalid** after (a)/(b). Re-run the `proj_setup` sweep at
      the new operating point, pick best, then pass it explicitly from `run.py`'s Qexp scenario.
    - **(d) Cache the TABLE data ONLY — not graph data. DONE (2026-08-05).** *"these are good
      numbers, so no need to cache graph data — only the table data. Plots are easy to generate and
      a single run is fast enough to even generate on the fly."* **Measured (2026-08-05):** full
      `sweep.py` = **21.1s**; single run = **0.19s**. Implemented in `sweep.py`: each swept point's
      `_metrics` dict is memoized to `out/.sweep-cache.json`, keyed by the `run_*` call args and
      gated by a signature over the sim constants + `sim.py`/`sweep.py` source. **Verified:** cold
      run 22.0s (0/99 cached) → warm re-run 1.6s (99/99 cached) with all six figures still redrawn
      on the fly; a source/param change auto-invalidates the whole cache; `plots.py` is deliberately
      NOT in the signature (plot-only edits stay warm); the cache file is git-ignored. Per-run
      timeseries / plots are NOT cached.

    **Then item 8** (realistic demand shapes) — go-ahead given: *"we need to run those tests too."*
    Trapezoid / level-shift up / level-shift down, `lo ≈ 8` / `hi = 24` req/s — already fully
    specified in item 8 (this is the "is it captured anywhere" Dean asked about — **yes, §8.1
    item 8**). **New validation goal:** *"we need sweeps for more workload to see if the params we
    just picked above are stable"* — after each new workload lands, re-run the parameter sweeps on
    it and check whether the picked `(drain=20, headroom=1.3, sat=0.85, best-proj)` operating point
    holds. Add a **workload dimension** to the sweep validation. **DONE (2026-08-05):** the
    workload dimension is `stability.py` (fixtures in `sim.py`); it re-sweeps `proj_setup`, `drain`,
    and `headroom` on all three realistic shapes + bump and writes `out/stability.md`. **Result:
    the operating point HOLDS** — `proj=120` within 0.7 pp of every shape's optimum, `headroom=1.3`
    knee-stable (1.1–1.3), and the only FLAG (`drain`: shape-best is `3` everywhere) is the
    intentional level-field handicap, not shape-instability. See item 8 for the full verdict.

11. [x] **All demand shapes integrated into the HTML deck + uniform actuation cap (2026-08-05).**
    The realistic shapes from item 8 (plus `spike`) are now first-class rendered material in
    `out/index.html` and `REPORT.md`, and a max-replica cap is enforced at actuation for **every**
    sizer. Two coupled pieces:

    **(a) Uniform actuation cap — cap = the no-autoscaling provisioning level.** Every sizer's
    *desired* count is capped at actuation (`desired → committed`), the **same** ceiling for the WVA
    Q sizers as for the HPA/KEDA baselines (`run.py` now passes `max_replicas=cap_for(shape)` into all
    six WVA calls, `run_closed_loop`, and `gen_supply_static`'s `count`). The WVA cap is **cap-only, no
    floor** — they still scale to zero when demand drains. The cap is deliberately the **no-autoscaling
    provisioning level** an operator would pin if they didn't autoscale — **not** the ideal sizer's
    clairvoyant peak (≈5 on every sustained shape). Because `static` is pinned at exactly
    `cap_for(shape)`, the static baseline line and the shared ceiling are the **same knob**; the minimal
    sensible cap for a shape is whatever a no-autoscaling deployment needs to serve its peak (≈5–6 here),
    so 10 sits comfortably above the floor.
    - **Value: `CAP_DEFAULT = 10` for all shapes; `CAP_BY_SHAPE = {}` (empty ⇒ 10 everywhere).**
      Escalation rule (two triggers, either fires): raise **only the affected shape** to **15** (never
      higher) if (a) the Q-vs-HPA lesson collapses at 10 (qexp and qaware both peg and become
      indistinguishable) OR (b) 10 falls below that shape's no-autoscaling floor (static@10 can't serve
      its peak). `bump`/`spike` always stay 10.
    - **Cap-lesson evaluation (2026-08-05): NO escalation needed — 10 holds every lesson.** At cap=10
      qexp still visibly out-serves qaware on all three sustained shapes (trapezoid +11.3 pp, stepup
      +8.8 pp, stepdown +10.3 pp good%≤15 s, roughly halving failures — qexp reaches the ceiling
      *earlier*), the HPA sizers still peg at 10 and land dominated on the Pareto (≈1.8–2.5× qexp's
      replica·s), and static@10 serves every shape (100 % good, 0 failed — no floor breach). So
      `CAP_BY_SHAPE` stays empty. **`bump` is byte-identical** to pre-cap (WVA sizers peak at 5 < 10, so
      the cap never bites); the cap bites only on the sustained-load shapes. (Uncapped peak-*desired* for
      reference: qaware/qexp reach 14–27 on stepup/stepdown, HPA 557–1766 — the reason a cap is needed.)
    - **`stability.py` stays uncapped by design** — it measures each sizer's *knob response* across
      shapes; a cap there would confound the signal, so its `rep_max` column reports *pre-cap desired*
      (e.g. qexp 15 on stepdown), an intentional, informative difference from the actuated demo.

    **(b) Five shapes, every tab.** `run.py` loops `DEMO_SHAPES = [bump, trapezoid, stepup, stepdown,
    spike]` (bump = calibration/reference, first; spike = teaching-only, NOT calibrated, last), rendering
    all 8 scenarios × 5 shapes as `{stem}-{shape}.png` / `{stem}-{shape}-latency.png`, plus per-shape
    `summary-{shape}.md` and `09-wait-cdf-{shape}.png` / `10-cost-quality-{shape}.png` (`summary.md`
    kept as a bump alias; the old unsuffixed per-scenario/tradeoff PNGs are replaced and their orphans
    removed). `report.py` surfaces them: **Compare** gains a shape switcher (swaps both panes + banner);
    **Browse** shows a gallery of all 5 shapes (main + collapsible latency) for the chosen policy;
    **Table** renders a per-shape summary table behind a shape switcher; **Tradeoffs** renders each
    shape's cost-quality + wait-CDF as separate figures. `REPORT.md` keeps the bump reference figures and
    adds a **Demand shapes** section embedding all 5 shapes' cost-quality Pareto. This realizes item 8's
    deferred "per-shape demo figures wired into the viewer" and **supersedes item 9's *two-level*
    category→workload chooser with a simpler flat per-shape switcher** (no category layer — the 5 shapes
    sit in one list). Calibration constants unchanged (item 8 verdict: shape-robust). Out/ grows to
    ~20–25 MB (committed, accepted).

    **Spike as a rendered teaching shape (distinct from §6.5's standalone stress).** §6.5's
    `stress_ideal.py` is *ideal-only* and makes the sub-window-burst sizing point. The deck's `spike`
    shape runs **all 8 policies** and makes a different, measured point: for a ~6 s burst far shorter
    than the 90 s boot, the bottleneck is **boot lag, not the sizing algorithm** — every *achievable*
    policy that must spin up (reactive, anticipatory, both KEDA baselines) drops **7–57 %** of requests;
    the clairvoyant **ideal** survives (0 % failed) only because it boots instantly (a fiction); and the
    one real policy that absorbs the burst cleanly is **static/no-scaling** pinned at the cap
    (pre-warmed → 0 % failed) — bought with ~5× the steady-state resource-seconds and ~14 % utilisation
    the rest of the time. Lesson: **for a burst shorter than your boot time, autoscaling is the wrong
    tool — only standing pre-provisioned headroom absorbs it, and that headroom is exactly what you pay
    to be spike-proof.** (Exact numbers live in the per-shape Table; the `SHAPE_NOTES` banner in
    `report.py` carries this prose, tuned to the actual run.)

### 8.2 Later (deferred — do not start without direction)

**Model / sizing:**
- [x] Phase 2: concurrency-dependent **decode** rate — **designed & IMPLEMENTED
      2026-08-03 in §2.7** (§8.1 item 7(a)). Monotone below the cap, not full USL.
- [ ] **USL retrograde** (throughput *falling* past a knee) — a separate, later
      extension beyond §2.7: it requires concurrency *above* `usable_C`, which the
      closed-loop router never produces. Only reachable with an oversubscribing
      imported trace (below) — the path into the >85 % slowdown / "crawl" regime the
      in-sim dispatcher never enters (§2.3).
- [ ] Setup-time noise: boot lag is a **constant** now; add jitter/noise to
      `setup` (and later `drain`) to test robustness to non-uniform boot times.
- [ ] **Burn-in prelude — start the measured window in true steady state** (APPROVED
      2026-08-06, implementing; §2.4). Generate arrivals over `[0, T_burn + duration]` with the
      profile held at its t=0 rate for `t < T_burn`, take `t0 = T_burn` as the measurement
      origin, and **freeze autoscaling for `t < t0`** (no `decide` events; sizer pre-passes held
      at `n0`) so the warm-up is never itself a test of the controller and never bills boots into
      the measured window. `sample()` shifts its grid to `[t0, t0+duration]` and emits `t − t0`,
      so plots stay unaware of burn-in; `req_done` is filtered to `arrival ≥ t0`, so burn-in
      requests **occupy capacity** (the whole point) but never enter latency stats. This
      **supersedes the analytic estimator seed** of §2.4 — real pre-window history simply fills
      the trailing windows — and it is the only way to start the **served side** in steady state:
      in-flight requests, in-system `L(t)`, and the served-work bands currently fill from empty
      over ~60 s no matter what the fleet is doing. The warm fleet is *retained*, because with the
      autoscaler frozen nothing else would create the first replica. `T_burn = 120 s` ≈ 2× the
      longest *backward* window (`METRIC_WINDOW` / `WORK_RANGE` / `SIZING_RANGE` = 60) and ~10
      mean service times; `QEXP_PROJ_SETUP = 120` is forward-looking and does not constrain it.
      Measured cost: `run.py` 61 s → ~75 s; `sweep.py` needs one cold ~5 min pass (burn-in
      changes the cache key) then returns to ~3 s. **Every frozen number in §8.1 item 11 is
      re-frozen once, after this lands** — the warm-start already invalidated them, and burn-in
      will move them again, so they are updated in a single pass rather than twice.

**Right-sizing is the premise (Dean, 2026-08-06) — the next two directions follow from it.**
The deck has so far mostly investigated **transition-time** behavior, but **steady-state
right-sizing is the actual money-saver** in autoscaling; transition *speed* matters less. That
reframes the shape set rather than extending it: a plain ramp/step **down** is a genuinely good
test of whether the system rescales at all, and it is *honest* precisely because scale-down has
**zero actuation lag** (§8.1 item 8). What is not yet tested is how right-sizing holds up once
the signal gets harder:

- [ ] **Noise in the input signal.** The only demand-side variability today is Poisson thinning
      around a smooth `rate_profile`. Add controlled noise to the *rate itself* (burstiness,
      autocorrelated jitter, short excursions) and measure how each sizer's **steady-state**
      right-sizing degrades: does it chase the noise — churn, and the boot-lag waste that churn
      buys — or absorb it? This is the direct test of whether "trailing window + `headroom`" is
      the right filter, and the natural place to add a **churn/stability** metric (replica
      changes per unit time) beside the existing cost/quality pair.
- [ ] **Change in the request shape.** `size_mean` / `size_dist` are fixed for an entire run, so
      offered *work* only ever moves because the *arrival rate* moved. Let the size distribution
      shift mid-run (mean output length steps up; or the prefill/decode mix changes) at
      **constant request rate**: request-count-based sizers (`hpa-concurrency`, anything counting
      requests rather than work) should mis-size, while work-rate-based sizers should track it
      cleanly. That is a sharp, teachable separation the current shape set cannot show at all —
      the demand-side analogue of §2.7's concurrency-dependent decode rate.

**Two-trace / real-benchmark ingestion (§1.1(2), decision-3 = later):**
- [ ] **Workload-trace loader** — read arrivals + sizes from a real benchmark export
      (guidellm / inference-perf; see §7.3) instead of `gen_load`. The rest of the
      pipeline is unchanged (policies are pure `load → supply`). Such a trace may also
      record real **per-pod concurrency above `sat_frac`** (a real router making
      early/mistaken decisions, so queues form at each vLLM) — the only path into the
      above-target slowdown / >85 % crawl regime the closed-loop sim never reaches
      (§2.3), and the input that would make USL retrograde real rather than synthetic.
- [ ] **Replay supply mode** — a "policy" that *follows a given scaling trace (b)*
      rather than computing one, so the **actual** benchmark run renders beside the
      **counterfactual** algorithm traces on the same workload (a). This is the seam
      that turns the closed simulator into the two-trace comparator of §1.1(2).

**Visualization / delivery:**
- [x] **Static comparison viewer** (`report.py` → `out/index.html`) — self-contained
      vanilla HTML/CSS/JS over the rendered PNGs: **Compare** (two half-width panes,
      side-by-side, synchronized scroll, with a fit↔full-detail slider), **Browse**
      (one scenario wide + its latency scatter — later extended to an all-shapes
      gallery, §8.1 item 11), **Table** (all strategies as columns
      from `summary.md`, each row annotated with what it means; sticky header row),
      and a **Glossary** tab (the parameter/term definitions from §2.6/§3). The table
      and header carry shared narrative prose (intro / story / per-policy readings)
      rendered from single source constants in `report.py`. Realizes the §1
      comparison UX for the Phase-1 static figures. Open directly (`file://`); no
      server.
- [x] **Generated `REPORT.md`** — `report.py` also emits a standalone markdown
      report (`build` → `REPORT.md`) from the **same** sources as the HTML
      (`out/summary.md` + the scenario/glossary/prose constants), so it has
      **identical scope** to `index.html` — all 8 scenarios, all rows, the same
      narrative prose (later extended with a per-shape **Demand shapes** section,
      §8.1 item 11). Data-driven, not hand-maintained. *(A short/curated
      few-scenario report version is deferred until the full data set settles.)*
- [ ] **Fillable parameter form** (deferred): a form in the viewer that lets a user
      set the run.py GLOBALS (workload / fleet / sizer / sampling knobs) and
      re-generate the figures — turns the static viewer into an interactive
      what-if. Needs a compute backend (the sim is Python), so it is **not** a pure
      `file://` static page; deferred until the deck-export decision (below) settles
      whether we ship a served app or a frozen deck.
- [ ] Same-panel focus view: both scenarios overlaid on a *single* aspect (needs
      `plots.py` to emit per-panel crops).
- [ ] Animated cumulative A(t)/D(t) zoom that follows the timeline.
- [ ] Animation of the six-panel timeline.
- [ ] Self-contained HTML deck export (the eventual deliverable; the viewer is the
      static precursor).

---

## 9. Files

- `sim.py` — load/supply generators (`gen_supply_perfect`, `gen_supply_queue_aware`,
  `gen_supply_queue_aware_exp`, `gen_supply_static`, `run_closed_loop`), `Simulator` engine,
  `sample`, `summarize`. `rate_profile()` holds all 5 demand shapes; every `gen_supply_*` takes
  `max_replicas` and clamps `desired` at actuation (§8.1 item 11).
- `plots.py` — `render` (6 panels), `render_latency`, `render_cumulative`, `render_wait_cdf`,
  `render_cost_quality`; shape-agnostic (shape reaches them only via the caller's title string).
- `run.py` — **8** scenarios (ideal, static, setup-lag, queue-aware, **queue-aware-exp**,
  hpa-queue, hpa-concurrency, hpa-combined), looped over `DEMO_SHAPES` (5 shapes) with a uniform
  actuation cap (`cap_for(shape)`, default 10; §8.1 item 11). Emits `{stem}-{shape}.png` /
  `{stem}-{shape}-latency.png`, `09-wait-cdf-{shape}.png`, `10-cost-quality-{shape}.png`, and
  `summary-{shape}.md` (+ `summary.md` = bump alias).
- `report.py` — builds `out/index.html` (comparison viewer) **and** `REPORT.md`
  (standalone markdown) from the per-shape PNGs + `summary-{shape}.md` + shared narrative prose
  constants (`SHAPES`, `SHAPE_NOTES`); read-only over the sim. Compare / Browse / Table / Tradeoffs
  are all shape-aware (flat per-shape switcher; §8.1 item 11).
- `sweep.py` — bump-only calibration sweeps → figs `11`–`16` + `out/sweep.md`; read/calibrate tool.
- `stability.py` — workload-stability sweeps: do the calibration knobs (`proj_setup`/`drain`/
  `headroom`) hold across 4 shapes (bump/trapezoid/stepup/stepdown, spike excluded)? → `out/stability.md`.
  **Uncapped by design** (measures knob response, not actuated behaviour; §8.1 item 11).
- `stress_ideal.py` — standalone B2 stress experiment (§6.5); ideal-only, not in the report.
- `diag_decisions.py` — throwaway per-decision sizer-state dump for the queue-aware
  run (when/why `desired` changes); not wired into `run.py`.
- `traces/*.json` — generated load/supply traces.
- `out/*.png`, `out/summary-{shape}.md` (+ `summary.md` bump alias) — rendered figures + tables.
- `out/index.html` — self-contained comparison viewer (open with `file://`).
- `REPORT.md` — generated standalone markdown report (regenerated by `report.py`).

Run: `./.venv/bin/python run.py` then `./.venv/bin/python report.py` (python3.12
venv; prefer `uv` for new deps).
