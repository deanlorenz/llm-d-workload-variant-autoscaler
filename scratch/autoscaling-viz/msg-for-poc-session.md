# Message for the POC ("scratch poc") session

A separate planning session captured our brainstorming into a design doc and
committed it on the `plans` branch:

- **`scratch/autoscaling-viz/autoscaling-behavioral-demo-design.md`** (commit `6ac65d2a`)

We then reviewed Ofer's empirical benchmark writeup for presentational lessons:

- https://github.com/biranofer/workload-variant-autoscaler/blob/comparison-wva-keda-epp-20260722/comparison-100x1000-16x20x24ext20-20260729/comparison.md

His doc is a point-in-time WVA-vs-KEDA-EPP result (decode-heavy, real hardware);
ours is a design doc for the simulator/demo. His structure is sound but
HTML-figure-oriented and single-pair. The lessons below adapt his *rigor*, not
his shape. **Please fold these into the design doc.**

---

## Agreed changes (Dean's decisions)

**NEW — comparison UX (add to Vision + roadmap).** The deck shows any **two**
scenarios **side-by-side**, with a control to switch which two are contrasted.
The **all-options numeric comparison is a single table** (every strategy a
column, as in the results table). Table = global picture; swappable side-by-side
figures = the two being actively compared.

**1 — Per-test explanation (accepted).** Each scenario gets a short header:
Assumptions / Policy / Settings / What it answers.

| | Assumptions | Policy | Settings | Answers |
|---|---|---|---|---|
| **ideal** | supply materializes instantly | size to centered offered-work-rate × headroom | setup=0, drain=0, window=30 | "what does good look like?" |
| **setup-lag** | 90 s boot lag | **same** demand-tracking commands as ideal | setup=90 | does a correct policy survive real boot lag? (no) |
| **queue-aware** | 90 s boot lag | demand-tracking **+ backlog/horizon** drain term; reactive, no look-ahead | setup=90, horizon=30 | can a backlog term recover completion? (yes, but overshoots) |

**2 — Global parameters block (accepted).** State the held-constant values in one
place: Load `bump`, duration 300 s, peak 10 req/s, mean size 4 (expo), seed 1;
backends C=4, rate 2.0 u/s → per-backend 8 u/s; headroom 1.2; sampling dt 0.25 s,
req-window 15 s, work-window 60 s; band edges [2, 10, 30, 60] s. Only per-scenario
knobs (setup, horizon, sizer) vary.

**3 — Model limitations section (accepted).** What the model does NOT capture and
its bias direction: fixed per-request service rate (Phase 1, no USL → optimistic
latency once served); clairvoyant rendering (plots are post-hoc truth; the sizer
still only sees windowed data); one global FIFO queue, no load balancer (HoL
accounted as failure, not fixed); instant unbounded scale within the trace beyond
boot lag (optimistic recovery speed); single request class / one arrival shape
(illustrative dynamics, not a calibrated benchmark).

**4 — Decision-point walkthrough (accepted; replaces generic figure refs).**
Grounded in the actual supply traces:
- **ideal** — 11 scale-ups (t=0…148), peak desired **7** @ t=145, drains from
  t=120 as the bump recedes. setup=0 → actual == desired. Reference trace.
- **setup-lag** — *identical* command sequence (same 7-peak @145, same
  down-schedule); the decisions were right, each replica just lands **90 s late**,
  so actual stays ≈4 through the ramp. **Correct policy, fatal timing assumption.**
- **queue-aware** — commands **balloon to 16 scale-ups firing continuously
  t=1→166, peak desired 15** (>2× ideal). Cause: the backlog term re-sizes for the
  current queue every tick **without crediting replicas already booting** →
  re-orders the same backlog = **integral windup**. Scale-down cascade t=179→215
  unwinds the overshoot. This is the visual proof that motivates expQ (credit
  in-flight boots → the t=53–166 pile-on collapses to the true shortfall).

**6 — Per-row metric descriptions under the results table (accepted; not a
separate glossary).** One line each: offered (arrival denominator); completed/%
(anti-survivorship headline); unfinished (stranded); good…failed % (share of
offered by pre-service wait band; 5 bands + unfinished% = 100); wait pNN
(pre-service wait = dispatch − arrival, completed reqs); time/work pNN (s/u =
time-in-system ÷ size, slowdown proxy — NOT the banding metric); replicas
avg/std/max (ready count); replica·seconds (∫ ready dt = cost proxy).

**7 — Keep the roadmap / living-doc nature (accepted, no change).**

## Rejected

**5 — Inline figure references in scenario prose — NO.** All figures share one
request trace and show the actual autoscale trace; generic referencing is
low-value. The decision-point walkthrough (#4) carries the "why" instead.

## Data source for #4

Scale up/down decision times were pulled from `traces/supply-*.json`
(distinct start = scale-up command, distinct stop = scale-down). Re-derivable via
a short read of those JSON traces.
