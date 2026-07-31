# Autoscaling Behavioral Demo — Design

**Status:** Draft (scratch POC). Captures the design as of the brainstorming
session that produced `sim.py` / `plots.py` / `run.py`. Not WVA code; lives only
under `plans/scratch/autoscaling-viz/`.

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
quality-mix shift, not a rescue.** All three scenarios complete 100 %; queue-aware
barely moves the peak queue depth (~7 %) and actually worsens the tail — its only
real win is shifting some waits toward "good." The dramatic "recovers stranded
work" story requires a sharper or sustained overload, which the smooth bump does
not produce (see §6.3, §6.5).

**Comparison UX (deck).** The deck contrasts any **two** scenarios
**side-by-side**, with a control to switch which two are shown. The
**all-options numeric comparison is a single table** — every strategy a column (as
in §6's results table). The table is the global picture; the swappable
side-by-side figures are the two scenarios being actively compared. (Phase-1 static
figures render one scenario each; the side-by-side pairing + swap control is a
deck-level feature — see §8.2.)

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
over well before `C` (we saturate around ~70 concurrent, often lower). Rather
than model that curve (that is the deferred Phase-2 USL work), Phase 1 uses a
flat **usable ceiling** `⌊sat_frac · C⌋` with `sat_frac = 0.7` as a lightweight
stand-in: it caps each replica's usable slots so the fleet is provisioned at a
realistic granularity. The sizer, the dispatcher, and the panel-5 capacity line
all use the *usable* ceiling, so they stay consistent.

**Phase 2 (deferred):** the real concurrency-dependent service rate (USL-style) —
a backend slows *continuously* as it fills, and goodput retrogrades past the
knee. `sat_frac` is the flat approximation of that; Phase 2 replaces it with the
curve. Not modeled yet.

### 2.4 Replica lifecycle

- **Desired**: `start ≤ t < stop`.
- **Actual / ready**: `up ≤ t < actual_down`. `setup = start → up` is the boot
  lag; `drain = stop → down`.
- **Draining**: `stop ≤ t < down` — still serving in-flight, not accepting.
- **Deferred-down**: a replica commanded down while it still has in-service work
  goes `pending_down` and only truly leaves when it drains.
- **Resurrection guard**: a replica commanded up and then cancelled mid-boot
  stays gone — the `up` handler only revives if `actual_down is None`.

### 2.5 Model limitations (what it does NOT capture)

Stated plainly, with bias direction, so results aren't over-read:

- **Fixed per-request service rate** (Phase 1; no USL) — once served, latency is
  **optimistic**; a real backend slows as it fills. The `sat_frac` usable ceiling
  (§2.3) caps *how many* slots a replica offers (fixing provisioning granularity)
  but does **not** bend the per-request rate — a served request still runs at full
  `service_rate`. The latency curve itself is Phase-2 USL work.
- **Clairvoyant rendering** — the plots are post-hoc truth, but the *sizer* still
  only sees windowed data; don't conflate the two.
- **One global FIFO queue, no load balancer** — head-of-line blocking is
  **accounted as failure, not engineered around** (§4).
- **Instant, unbounded scale within the trace** (beyond the boot lag) — recovery
  speed is **optimistic**; no per-step scale caps or node-pool limits.
- **Single request class, one arrival shape** — illustrative dynamics, **not a
  calibrated benchmark**.

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
2. **offered-work-rate (`owr`)** — a *demand estimate*: `arrival_rate × E[size]`
   tokens/s (see §3). An estimate, not a measurement (per-request size isn't known
   at arrival).
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

*Sizer (both `gen_supply_perfect` and `gen_supply_queue_aware`)*

| Param | Role |
|---|---|
| `headroom` | scale-up utilization target (`1.2` ⇒ run at ~83 %) |
| `sizing_range` | lookback the sizer averages `owr` over |
| `decision_interval` | how often the sizer recomputes desired count |
| `drain_time` | (queue-aware only) deadline to drain current backlog |

*Sampling / rendering (`sample`)*

| Param | Role |
|---|---|
| `sample_interval` | plot-grid resolution (seconds per sample) |
| `req_range` | lookback for the request-count throughput average (panels 1a/5) |
| `work_range` | lookback for the work-rate average (Prom-style; panels 1b/3) |

---

## 3. Sizing strategies

The demo compares reactive queue-aware sizing against an ideal baseline, and
(planned) against a plain HPA-style baseline. Three strategies:

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

**`owr` is a demand *estimate*, not a measurement.** Every sizer's rate term is
the offered-work-rate `owr(t) = arrival_rate(t) × E[size]` (tokens/s). The
arrival *count* is observable, but a request's *work* (its size in tokens) is
**not** known when it arrives — real serving knows the prefill/input length at
admission but not the decode/output length. Summing the in-window request sizes
is a valid proxy for `owr` only under the **stationary-shape assumption**: the
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

### (ii) expQ — anticipatory / dead-time-compensated *(to build)*

The intended fix, "beyond what regular HPA-like autoscalers do." Verbatim
mechanism from the session:

> Estimate when replicas we order now will arrive; estimate the gap based on
> pending replicas and based on queue growth rate; order enough to kill that
> queue — taking into account the replicas gap at that point in time, namely
> consider the pending replica that will be ready by then.

Concretely: project the queue forward to `t + setup` using its growth rate,
**credit the in-flight replicas that will be ready by then**, and order only the
**shortfall**. Crediting pending boots is exactly what kills the windup in (i).

> Dean flagged the logic isn't fully pinned down yet ("Not sure I understand your
> Qexp logic") — treat the mechanism above as the spec to refine, not final.

### (iii) HPA-queue — plain queue-ratio baseline *(to build)*

`desired = ceil(queue_size / desired_per_replica)` — the standard HPA/KEDA queue
metric. This is the baseline that **does not solve the problem**: no dead-time
compensation, reacts to the current metric only. Included to show what off-the-
shelf autoscaling does under boot lag.

**Comparison approach:** first compare all three on the **ideal case** (no boot
lag) via **time-to-clear only**, with **T ≈ 30 s** — the ideal case isolates the
*sizer math* (no dead time to confound it, so any difference is pure sizing
policy). The payoff run is then under the **90 s boot lag**, where expQ's
anticipation is the only thing that can pre-order capacity before the queue
builds; that is where (ii) is expected to separate from (i) and (iii).

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
- **Bands** (edges `[2, 10, 30, 60]` s): good (≤2) / almost (≤10) / bad (≤30) /
  really bad (≤60) / failed (>60). Colored green → dark red.
- **Survivorship bias is corrected.** Percentiles over completed-only requests
  flatter any policy that strands work, so:
  - **completion rate is a headline number** (offered / completed / completed % /
    unfinished).
  - band %s use the **offered** denominator, so the five bands + unfinished% sum
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
   (Prometheus-style windowed rates).
3. **2 — desired vs actual replicas**: stepped, with a draining band. Tiny y-
   offsets so equal desired/actual don't hide each other.
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
   stable (fixed the "57 bands for ~11 backends" problem).
5. **4 — global queue depth.**
6. **5 — concurrency L(t)**: in-system vs being-served vs slot capacity; the
   shaded gap between them is the queued count (Little's Law, L = λ·W).

Plus two standalone/auxiliary figures:

- `render_latency` — per-request time-in-system scatter, colored by request size.
- `render_cumulative` — cumulative A(t) vs D(t); vertical gap = L(t), horizontal
  gap = wait, area between = total time-in-system. **Deferred**: only legible
  zoomed-in / at low N. Revisit as an **animated zoom** that follows the other
  panels' timeline. (Kept in code, disabled.)

---

## 6. Current results

> **Recalibrated 2026-07-31** against the current code (`sat_frac=0.7`, the WVA
> decode-heavy anchor in §6.1). The numbers below are read directly from
> `out/summary.md` and `traces/supply-*.json`; every claim is checked against that
> output, not carried over from an earlier draft. The headline **changed** under
> this calibration — see §6.3 "Reading it."

### 6.1 Global parameters (held constant)

All three scenarios share one workload and one fleet; only the per-scenario knobs
(setup, sizer, `drain_time`) vary — so any difference in the figures is
attributable to the policy, not the load. Provenance: anchored to a real WVA
decode-heavy benchmark (peak ~24 req/s, ~1000-token mean work, C=100,
`service_rate ≈ 1000/12` tokens/s, ~90 s boot).

- **Load:** `bump` pattern, duration **600 s**, peak **24 req/s**, mean size
  **1000 tokens** (expo), seed 1.
- **Backends:** **C=100** raw slots, **`sat_frac=0.7`** → usable ceiling **70**
  concurrent, `service_rate ≈ 83.3` tokens/s → usable per-backend ≈ **5833
  tokens/s** (≈ **5.83 req/s** at the 1000-token mean); scale-up headroom **1.2**.
- **Sizer:** `sizing_range` 60 s, `decision_interval` 15 s, `drain_time` 30 s
  (queue-aware only).
- **Boot:** `setup` 90 s (setup-lag + queue-aware; ideal uses 0).
- **Sampling:** dt 0.25 s, `req_range` 15 s, `work_range` 60 s.
- **Quality bands:** pre-service wait edges [2, 10, 30, 60] s.

### 6.2 Scenarios under test

|  | Assumptions | Policy | Settings | What it answers |
|---|---|---|---|---|
| **ideal** | supply materializes instantly | size to **centered** offered-work-rate × headroom | setup=0, drain=0, sizing_range=60 | "what does good look like?" |
| **setup-lag** | 90 s boot lag | **same** demand-tracking commands as ideal | setup=90, sizing_range=60 | does a correct policy survive real boot lag? (no — quality collapses) |
| **queue-aware** | 90 s boot lag | demand-tracking **+ backlog/`drain_time`** drain term; reactive (trailing), no look-ahead | setup=90, sizing_range=60, drain_time=30 | can a reactive backlog term rescue quality? (only modestly — and it worsens the tail) |

### 6.3 Results table (`out/summary.md`)

| metric              | ideal | setup-lag | queue-aware |
|---------------------|------:|----------:|------------:|
| offered             |  7159 |      7159 |        7159 |
| completed           |  7159 |      7159 |        7159 |
| completed %         | 100.0 |     100.0 |       100.0 |
| unfinished          |     0 |         0 |           0 |
| good (≤2s) %        | 100.0 |      19.7 |        28.1 |
| almost (≤10s) %     |   0.0 |       5.8 |         6.2 |
| bad (≤30s) %        |   0.0 |      31.3 |        43.1 |
| really bad (≤60s) % |   0.0 |      42.7 |        21.0 |
| failed (>60s) %     |   0.0 |       0.4 |         1.6 |
| wait p50 (s)        |   0.0 |      28.5 |        14.6 |
| wait p90 (s)        |   0.0 |      39.6 |        50.6 |
| wait p99 (s)        |   0.0 |      47.4 |        62.4 |
| replicas avg        |  3.30 |      2.56 |        2.71 |
| replicas max        |     5 |         5 |           5 |
| replica·seconds     |  1980 |      1536 |        1629 |
| peak queue depth    |     0 |       756 |         704 |

*(`peak queue depth` and per-scenario replica lifecycles are read from the traces,
not `summary.md`; see §6.4. `time/work` percentiles are in the file but omitted
here — informational only, see §4.)*

**Metrics** (one line each): **offered** — arrival denominator (every request that
appeared; anti-survivorship). **completed / %** — did it finish at all.
**unfinished** — stranded, never served. **good…failed %** — share of *offered* by
pre-service wait band (5 bands + unfinished% = 100) — **this is the scored signal.**
**wait pNN** — pre-service wait (dispatch − arrival) over completed requests.
**replicas avg/max** — ready count. **replica·seconds** — ∫ ready dt, a cost proxy.

**Reading it — the honest headline (this is the B1 story):**

Under this calibration the smooth bump is **gentle enough that all three complete
100 %** — nobody is *permanently* stranded, even at 90 s boot. So the story is
**not** "completion rescue" and it is **not** "peak-queue reduction." The whole
difference lives in **when** work is served (the waiting-quality mix) and in the
**tail**:

- **Ideal**: 100 % served in ≤2 s, peak queue **0**. The centered clairvoyant
  window provisions *ahead* of the ramp, so on a smooth bump it never queues. What
  good looks like.
- **Setup-lag**: still 100 % complete, but the 90 s boot runs the up-ramp
  under-provisioned, so only **19.7 %** are served promptly (≤2 s) and the mass
  falls into **bad (31.3 %) / really-bad (42.7 %)** — 30–60 s waits. The bump
  recedes before the backlog turns terminal, so only **0.4 %** cross 60 s. Same
  commands as ideal, each landing 90 s late: **correct policy, fatal timing.**
- **Queue-aware**: the backlog term pulls scale-ups **earlier** and holds an extra
  replica, which lifts prompt service to **28.1 %** and roughly **halves the median
  wait** (28.5 → 14.6 s). But the replica it orders late — reacting to a backlog
  that is *already* being addressed by in-flight boots — arrives *after* the peak
  has passed, so it **worsens the tail**: p90 **50.6** vs 39.6, p99 **62.4** vs
  47.4, failed **1.6 %** vs 0.4 %, at **+93 replica·seconds** (1629 vs 1536) and one
  extra lifecycle replica. **Peak queue barely moves (756 → 704, ~7 %).**

So the honest takeaway is subtle, and deliberately so: on a smooth bump a reactive
backlog term buys a **modest shift of the waiting-mix toward "good," paid for with
a heavier tail and a bit more cost** — not a dramatic rescue. The dramatic
"recovers stranded work" story needs a load where setup-lag actually strands work
(sharper or sustained overload); the smooth bump does not produce it. This is why
the demo does **not** claim queue-aware "fixes" the problem — it motivates
anticipation (expQ, §3(ii)), which is the sizer that can order *before* the queue
builds instead of chasing it.

**Why even the *ideal* sizer eventually fails (the §6.5 stress point).** Ideal's
peak queue is 0 here only because the bump varies *slowly relative to the sizing
range* — a 60 s centered window peeks ~30 s ahead and provisions before the ramp
arrives. That protection is an artifact of the smooth shape, not of clairvoyance
per se. See §6.5.

### 6.4 Decision-point walkthrough

Grounded in the actual supply traces (`traces/supply-*.json`; a distinct replica
start = a scale-up command, a distinct stop = a scale-down):

- **ideal** — 5 scale-ups (t=0…240), peak ordered **5** @ t=240, drains from
  t=360 as the bump recedes. setup=0 → actual == desired. The reference trace.
- **setup-lag** — the *identical* command sequence (same 5-replica peak, same
  down-schedule); the decisions were right, each replica just lands **90 s late**,
  so actual capacity lags demand through the entire ramp. **Correct policy, fatal
  timing assumption.**
- **queue-aware** — **6** scale-ups firing t=15…270; peak ordered is **still 5**
  (same as ideal), reached **earlier** (@ t=165 vs 240) and held longer, plus one
  extra lifecycle replica. The backlog term front-loads capacity while the boot
  window lets the queue build — and, because it does **not credit replicas already
  booting**, orders one replica more than needed, which lands after the peak. This
  is the *residual* of the integral windup (much milder here than under a sharper
  load), and the visual motivation for expQ: credit in-flight boots and even that
  one-replica overshoot disappears.

### 6.5 Stress experiment — making even the ideal sizer queue (B2)

A separate, standalone experiment (`stress_ideal.py` → `out/stress-ideal-spike.png`),
**not wired into the three-way report**. Its only job is to make one teaching point
that the smooth bump can't: *perfect future knowledge is not enough if you compress
it into a windowed average to size a fixed replica count.*

Same calibration as `ideal` (`setup=0`, centered window, headroom 1.2,
`sizing_range=60`) — **only the demand shape changes**: instead of the slow bump we
drive the `spike` pattern (steady baseline at 0.4×peak with a **6 s burst to
3×peak** at mid-run). The burst is far shorter than the 60 s sizing range, so even a
perfectly clairvoyant *centered* window averages it into the window mean and sizes
for the mean, not the peak. With `setup=0` the replicas are up instantly — there
simply aren't enough of them for the burst.

Result: peak queue **137**, peak L **417** (well above the usable-slot ceiling),
and prompt service drops from ideal's 100 % to **96.7 %** good (p99 wait 4.9 s) —
the ideal sizer now visibly queues. The plot shows the queue spike in panel 4,
in-system L above the usable-slot capacity in panel 5, and work demand poking above
the ceiling in panel 3. The lesson for the deck: **windowed sizing of a fixed
replica count has a residual failure mode against sub-window bursts, independent of
setup and independent of how well you can see the future.**

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
  need the concurrency-dependent service model (§2.3 deferred), which is exactly
  what makes the USL rollover real instead of synthetic.

> Two interactive pages (an LLM-serving explainer at mbrenndoerfer.com and a couple
> vendor blogs) **403'd automated fetch** — described from snippets; worth a manual
> visit if we build the LLM-specific visuals.

### 7.2 Anticipation / control-theory prior art — **NOT YET RUN**

Distinct from §7.1. This is the search for the *sizing-math* regime behind expQ —
dead-time compensation, feed-forward, anti-windup, and the exact KEDA/HPA queue
formula. **Not done.** Any control-theory framing (e.g. Smith predictor,
anti-windup, Erlang-C) is a **hypothesis to verify against a real source**, not an
established citation — do not write it up as fact until searched. This is
next-step (1) in §8.1.

---

## 8. Roadmap

### 8.1 Next steps (immediate — do in this order)

1. [ ] **Anticipation/control-theory prior-art search** (§7.2) — the visualization
   scan is already done (§7.1); this remaining one covers the *sizing math* only.
   Run it *before* writing any control-theory framing into §3. Verify or drop
   Smith-predictor / anti-windup / KEDA-HPA-formula / Erlang-C against real sources.
2. [ ] **Pin down the expQ logic precisely** (Dean's open question, §3(ii)) —
   agree the projection-to-`t+setup` + credit-in-flight-boots + size-the-shortfall
   formulation and confirm it with Dean **before** coding the sizer.
3. [ ] **Implement expQ sizer** (§3(ii)) — anticipatory, credits in-flight boots
   (approach (a): time-to-clear, T≈30 s).
4. [ ] **Implement HPA-queue sizer** (§3(iii)) — plain `ceil(queue/target)`
   baseline.
5. [ ] **Three-way comparison** — first on the ideal case (isolates sizer math),
   then under the 90 s boot lag (where expQ should separate). See §3 comparison
   approach.

   *(The earlier "centered-rate fix for `gen_supply_queue_aware`" item was
   removed: its trailing window is intentional — it's the reactive baseline, which
   by definition cannot peek at future arrivals. Centering is the ideal sizer's
   ability, and adding look-ahead is exactly what expQ does. See §3(i) note.)*

### 8.2 Later (deferred — do not start without direction)

**Model / sizing:**
- [ ] Phase 2: concurrency-dependent service rate (USL).
- [ ] Setup-time noise: boot lag is a **constant** now; add jitter/noise to
      `setup` (and later `drain`) to test robustness to non-uniform boot times.

**Visualization / delivery:**
- [x] **Static comparison viewer** (`report.py` → `out/index.html`) — self-contained
      vanilla HTML/CSS/JS over the rendered PNGs: **Compare** (two half-width panes,
      side-by-side, synchronized scroll, with a fit↔full-detail slider), **Browse**
      (one scenario wide + its latency scatter), **Table** (all strategies as columns
      from `summary.md`, each row annotated with what it means), and a **Glossary**
      tab (the parameter/term definitions from §2.6/§3). Realizes the §1 comparison
      UX for the Phase-1 static figures. Open directly (`file://`); no server.
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

- `sim.py` — load/supply generators, `Simulator` engine, `sample`, `summarize`.
- `plots.py` — `render` (6 panels), `render_latency`, `render_cumulative`.
- `run.py` — three scenarios + comparison `report` → `out/summary.md`.
- `report.py` — builds `out/index.html` (comparison viewer) from the PNGs +
  `summary.md`; read-only over the sim.
- `traces/*.json` — generated load/supply traces.
- `out/*.png`, `out/summary.md` — rendered figures + table.
- `out/index.html` — self-contained comparison viewer (open with `file://`).

Run: `./.venv/bin/python run.py` (python3.12 venv; prefer `uv` for new deps).
