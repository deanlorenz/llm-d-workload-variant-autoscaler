from: planner (PR-2 anchor plan session, ta-anchor-dynamic-refresh)
to: planner
session: TA-lead experiment — the feasibility question is answered (yes, but the framing in CURRENT.md is wrong)

**Partial answer to `plan__ta-sat-scaleup-lead-setup.md`, which I am leaving OPEN.** That handoff asks
for three things: (a) a two-phase calibration+trigger workload, (b) a "faster" methodology, and (c) an
open feasibility question that CURRENT.md says "the planner must answer before a cluster run." I am
answering **(c) only** — it is a factual code question, it gates the other two, and the benchmark coder
is HOLDING on it. I am deliberately **not** designing (a) or (b): different mission, and whoever Dean
assigns should not find them half-done by a session that isn't tracking that thread.

I picked this up because the PR-2 C10 work made me derive the constant semantics from source this week,
and the answer turns on exactly that.

## The question

> Does TA's `Analyze()` actually raise RequiredCapacity ahead of the KV threshold, or does it also key
> off `k* ≥ k_sat = 0.85` (`DefaultKSat = 0.85`, "mirrors" saturation) — if the latter, a lead is
> impossible by construction and the experiment needs reframing.

## Answer: a lead is feasible — but **not** for the reason the question supposes, and the premise in CURRENT.md is wrong twice

Traced on `ta-anchor-dynamic-refresh@d9f3b97e` (TA code here is unchanged from `main` in every respect
that matters below; C10 is not yet written).

**1. `DefaultKSat` is not a trigger at all.** Every non-test use is capacity *shaping* or diagnostics:

| Site | Use |
|---|---|
| `throughput/analyzer.go:295` | `itlSat := model.ITLAt(DefaultKSat)` — supply |
| `throughput/analyzer.go:719` | `nSat := DefaultKSat * kvMax / shape.KVreq` — supply |
| `throughput/analyzer.go:845` | GPS-mismatch **diagnostic** near-saturation gate (`k* < DefaultKSat − 0.10` ⇒ skip the *diagnostic*; does not touch RC) |
| `throughput/itl_model.go:53` | validity guard (`a·k_sat + b > 0`) |

There is no `k* ≥ threshold` gate on TA's RC anywhere. So the "impossible by construction" branch of
the question does not obtain.

**2. TA does not compute RC at all.** It leaves `RequiredCapacity` and `SpareCapacity` **zero** and
publishes raw `Total*` fields (`analyzer.go:194`, `:460`, `:922`). RC/SC are derived by the *engine*.

**3. Both analyzers then go through the *same* watermark.** `applyUniversalThreshold` is applied to
every analyzer — saturation at `engine_v2.go:123`, every other at `:179`:

```
RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)
SC = max(0, TotalSupply         − TotalDemand/scaleDown)
```

and `resolveThresholds` (`:392-400`) falls back to the global `cfg.ScaleUpThreshold` /
`cfg.ScaleDownBoundary` unless a per-analyzer override exists. **So by default TA and saturation share
0.85/0.70. TA has no lower trigger threshold.**

## So where does the lead come from?

**From the inputs, not the threshold.** The two analyzers feed *different* `TotalDemand`/`TotalSupply`
into the identical formula:

- **saturation**'s supply/demand are **occupancy**-derived — measured KV utilization against
  `KvCacheThreshold = 0.80`, which is what "full" means.
- **TA**'s supply is a **model-derived throughput ceiling** — `μ_sat = N_sat / ITL(k_sat)` from the
  fitted ITL model, with demand from arrival rate.

A throughput ceiling is reached before an occupancy ceiling under prefill-heavy or ITL-degrading
traffic, so TA's `demand/supply` ratio can cross 0.85 while measured KV util is still well under 0.80.
**That is the lead mechanism, and it has already been measured on the cluster**: the 2026-08-03 live
run recorded TA utilization at roughly **2× saturation's below saturation** (memory
`project_ta3_benchmark_pokprod`). The experiment is not looking for a new effect — it is looking to
time an effect already observed.

## Consequence for the experiment design — please reframe before building (a)/(b)

The hypothesis should **not** be *"TA triggers at a lower threshold."* It is:

> *TA's utilization estimate rises faster than saturation's for identical traffic, so it crosses the
> **shared** 0.85 scale-up watermark earlier.*

Two things follow that change what the workload has to do:

- **The workload must make the two estimates diverge**, not merely ramp. Traffic where throughput and
  occupancy saturate together produces no lead no matter how well TA is calibrated. Prefill-heavy /
  long-input traffic is where the ITL model's ceiling arrives first.
- **`resolveThresholds` gives you a per-analyzer override lever** (`EffectiveScaleUpThreshold`). Useful
  as a *control* — pinning both analyzers to the same value proves the lead is input-driven — and it
  would be a confound if a config under test sets it unequally without anyone noticing. Worth an
  explicit assertion in the run's config dump.

## One interaction with PR-2, sub-1%, flagged so it isn't discovered mid-run

PR-2's C10 changes TA's `k_sat` 0.85 → `KvCacheThreshold` (0.80). Because k_sat enters PRC **twice**,
that *lowers* TA's `μ_sat` by **0.548%** on the shipped fixture model — which slightly *raises* TA's
utilization and therefore marginally **increases** the lead. Realistic range 0.4%–2.5%, upper bound
5.88% and unreachable. It will not change the experiment's outcome, but the TA baseline shifts if PR-2
lands between an A and a B run, so pin the controller image per run. (Note for anyone who saw an
earlier figure: the "~6%" that circulated was a numerator-only error and is wrong.)

Also: `throughput/constants.go:53` currently says `DefaultKSat` *"Mirrors DefaultScaleUpThreshold in
saturation config"* — that comment is the origin of the confusion in the question, and C10 fixes it.
The three constants are distinct: `KvCacheThreshold = 0.80` is the definition of "full" and shapes
PerReplicaCapacity; `0.85`/`0.70` are HPA-style scale-up/scale-down **watermarks** that land on RC/SC
only. Whoever writes (a)/(b) should not treat 0.85 as a utilization target.

## Still open in the original handoff — not mine, not started

(a) the two-phase workload (Phase A sub-scale calibration sweeping KV util `[0.15, 0.85]` for ≥10 OLS
samples with `KSpread ≥ 0.30` to flip `T2-default → OLS-Ready` without itself scaling; `wva_sat2_short`
jumps straight to saturating rates and is unsuitable), and (b) the Δt-to-`desiredReplicas: 2`
methodology with repeats and a noise floor. Both unblocked by the above.

## Routing

No CURRENT.md request — **do not route to sync.** `plan__ta-sat-scaleup-lead-setup.md` stays **open**
(plain `.md`, not `.WIP`) because (a) and (b) are unanswered; whoever takes it should read this file
first. I have not rung the benchmark coder's bell — that's the assigned planner's call, and it depends
on (a)/(b), not on this.
