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

1. **Ideal** — scaling with zero boot lag. Everything is served promptly. Sets
   the "this is what good looks like" baseline.
2. **Setup lag** — the *same* demand-tracking scaling commands, but replicas take
   ~90 s (~1.5 min) to boot. Actual capacity lags desired through the entire
   up-ramp; the system runs under-provisioned and **strands ~28 % of the work**.
   This is the catastrophe the demo is built around.
3. **Queue-aware** — same 90 s boot, but the sizer adds a backlog-drain term. It
   **recovers to 100 % completion**, but it's reactive: it only starts over-
   provisioning *after* the queue has already piled up, so latency stays bad for
   a long stretch. This motivates **anticipation** (feed-forward) as the next
   step.

The honest headline is: **the real win is completion + recovery, not peak-queue
reduction.** Queue-aware barely improves the peak queue depth vs. setup-lag; what
it fixes is that work no longer gets permanently stranded.

---

## 2. Simulator architecture

### 2.1 Trace-driven and clairvoyant

The simulator is driven by two traces:

- **Load trace** — a list of requests, each with an arrival time and a size
  (work units).
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
- A backend accepts requests while under its max concurrency **C**. Per-request
  service is a **fixed rate** (`rate`), so completion = dispatch + size/rate, and
  the rate is **concurrency-independent** as long as the backend holds ≤ C
  requests. Per-backend work rate = `C · rate`.
- `_free_backend` picks the most-free accepting backend; `_dispatch` pulls FIFO.

**Phase 2 (deferred):** concurrency-dependent service rate (USL-style) — a
backend slows as it fills. Not modeled yet.

### 2.4 Replica lifecycle

- **Desired**: `start ≤ t < stop`.
- **Actual / ready**: `up ≤ t < actual_down`. `setup = start → up` is the boot
  lag; `drain = stop → down`.
- **Draining**: `stop ≤ t < down` — still serving in-flight, not accepting.
- **Deferred-down**: a replica commanded down while it still has in-service work
  goes `pending_down` and only truly leaves when it drains.
- **Resurrection guard**: a replica commanded up and then cancelled mid-boot
  stays gone — the `up` handler only revives if `actual_down is None`.

---

## 3. Sizing strategies

The demo compares reactive queue-aware sizing against an ideal baseline, and
(planned) against a plain HPA-style baseline. Three strategies:

### (i) Current-Q — reactive backlog-drain *(built)*

`gen_supply_queue_aware`. Target rate:

```
target_rate = offered_work_rate + backlog / horizon
n_replicas  = ceil(headroom · target_rate / per_backend)
```

`horizon` is the time-to-clear dial: the controller sizes to drain the current
backlog over `horizon` seconds. Fluid backlog integrates
`backlog += (offered − up_capacity) · dt`.

**The flaw this demo exposes — integral windup.** During the boot window the
controller re-orders the *same* backlog every tick, because it does **not credit
replicas already in-flight** (ordered but still booting). So it keeps commanding
more capacity for a backlog that is already being addressed by pending boots →
overshoot, then a late over-provisioned tail.

> **Known code gap:** this sizer still uses a **trailing** `offered_work_rate`
> window for its rate term. Dean's correction: "Rate is not supposed to lag — we
> know when requests arrive." The rate term should use a **centered** window (as
> `gen_supply_perfect` already does). **Not yet applied.**

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

**Comparison approach:** compare all three on the **ideal case** (no boot lag) via
**time-to-clear only**, with **T ≈ 30 s**.

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
4. **3 — per-backend work (stacked) vs required**: identical backends read as one
   pool via a small cycling shade palette; slot-pool reuse (LIFO free list +
   min-heap) keeps the band set small and stable (fixed the "57 bands for ~11
   backends" problem).
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

Common load: `bump` pattern, duration 300 s, peak 10 req/s, mean size 4 (expo),
seed 1. Backends C=4, rate=2. Three scenarios (`out/summary.md`):

| metric              | ideal | setup-lag | queue-aware |
|---------------------|------:|----------:|------------:|
| offered             |  1472 |      1472 |        1472 |
| completed           |  1472 |      1054 |        1472 |
| completed %         | 100.0 |      71.6 |       100.0 |
| unfinished          |     0 |       418 |           0 |
| good (≤2s) %        |  99.9 |       0.0 |         4.8 |
| almost (≤10s) %     |   0.1 |       0.0 |         5.1 |
| bad (≤30s) %        |   0.0 |       0.0 |        17.9 |
| really bad (≤60s) % |   0.0 |       0.0 |        46.5 |
| failed (>60s) %     |   0.0 |      71.6 |        25.7 |
| wait p50 (s)        |   0.0 |      69.9 |        43.8 |
| wait p99 (s)        |   1.8 |     110.8 |        78.0 |
| replicas avg        |  3.45 |      1.73 |        2.61 |
| replicas max        |     7 |         4 |           9 |
| replica·seconds     |  1036 |       519 |         783 |

**Reading it:**

- **Ideal**: 99.9 % served in ≤2 s. What good looks like.
- **Setup-lag**: 71.6 % completed, and *every* completed request is in the
  "failed" band (>60 s wait) — the 90 s boot means nobody gets served promptly and
  28 % never finishes at all. `replicas max 4` shows it never even caught up to
  demand.
- **Queue-aware**: 100 % completion (the strand is gone), but the quality mix is
  spread across all bands and 25.7 % still land in "failed." `replicas max 9` and
  the higher replica·seconds show the **overshoot** — it over-provisions late.
  This is the windup, and the visual motivation for expQ.

---

## 7. Roadmap

**Model / sizing:**
- [ ] Centered-rate fix in `gen_supply_queue_aware` (known gap, §3(i)).
- [ ] Implement **expQ** sizer (§3(ii)) — anticipatory, credits in-flight boots.
- [ ] Implement **HPA-queue** sizer (§3(iii)) — plain baseline.
- [ ] Three-way comparison on the ideal case, time-to-clear, T≈30 s.
- [ ] Phase 2: concurrency-dependent service rate (USL).

**Visualization / delivery:**
- [ ] Animated cumulative A(t)/D(t) zoom that follows the timeline.
- [ ] Animation of the six-panel timeline.
- [ ] Self-contained HTML deck export.

**Open items:**
- [ ] **Check prior art** for the anticipatory / dead-time regime — the session
  flagged this as worth doing but **did not do it**. Any control-theory framing
  (e.g. dead-time compensation) is a *hypothesis to verify against a real source*,
  not an established citation. Do not write it up as fact until searched.
- [ ] Pin down the expQ logic precisely (Dean's open question on §3(ii)).

---

## 8. Files

- `sim.py` — load/supply generators, `Simulator` engine, `sample`, `summarize`.
- `plots.py` — `render` (6 panels), `render_latency`, `render_cumulative`.
- `run.py` — three scenarios + comparison `report` → `out/summary.md`.
- `traces/*.json` — generated load/supply traces.
- `out/*.png`, `out/summary.md` — rendered figures + table.

Run: `./.venv/bin/python run.py` (python3.12 venv; prefer `uv` for new deps).
