# TA on pokprod — Open Scenarios (Type 3, live)

**Status:** LIVE — this is the actively-changing surface, kept separate from the settled execution plan
on purpose. **Scope:** workload-scenario design questions, the dwell mechanism, and the checklist of
what's decided vs. still needs Dean.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md) (Type 1) ·
[`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (Type 3, settled phases) ·
[`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger — `[[D-nn]]` fetchable by
`grep -n '^## D-nn'`) · [`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md)
(the 7-cell campaign this scenario work is informed by) ·
[`autoscaling-viz-design.md`](autoscaling-viz-design.md) (Type 1, viz-side capacity/estimation model —
owns the theory/simulation legs referenced below).

---

## Checklist — what still needs Dean, at a glance

| Item | Status | Ref |
|---|---|---|
| Confirm the three §1 scenario asks | ✅ **CLOSED 2026-08-12** | [[D-23]] |
| §2 operating-point fork, (a) vs (b) | ✅ **DECIDED 2026-08-11 — (a)** | [[D-19]] |
| T9 gateway log-follower | ✅ **DONE 2026-08-12 — wired into `benchmark-run`, not yet live-verified** | [[D-22]], [[D-27]] |
| §5.5-item-4 fold-vs-stub call for the pokprod runbook | ⬜ **OPEN, Dean's** | execution plan §7.1 T6 |
| Dwell forecast Type-1 scoping | ⬜ **OPEN, Dean's — explicitly deferred to him** | [[D-21]] |
| §2c: can one context map to multiple namespaces? | ⬜ **OPEN, unresolved** | architecture doc §5 |
| Any cluster run | ⬜ **always, per-run** | standing rule |

**Nothing else in this doc is waiting on Dean right now.** The dwell mechanism itself is being worked
in a dedicated session — see § 3 below — not blocked on anything here.

---

## 1. Scenario gaps — three asks, all confirmed

Source: the ladder-run cross-check, itself the product of an independent `autoscaling-viz` review.
**Status: DECIDED, all three — closed 2026-08-12.** [[D-23]]

**1.1 — A mid-band dwell stage.** Hold an offered rate that parks KV utilization inside the no-action
band for ≥3 min. No run had ever dwelt there as of the original ask; every run to date was either
sub-band or pinned above it by a replica cap, not by load. **Superseded mechanism, unchanged goal** —
see §2 below: raising the offered rate under a tracking controller doesn't reliably move steady-state
KV, so this is an analyzer-configuration question, not a workload one. [[D-18]]

**The exact no-action band, derived not guessed.** Not a separate calculation — it's the direct
definition of `saturation_v2`'s two universal thresholds
(`internal/config/saturation_scaling.go:54-64`): scale-up fires once `demand/supply > 0.85`,
scale-down once `demand/supply < 0.70`. **The band is exactly `[0.70, 0.85]`** — narrower than an
earlier `[0.3, 0.85]` guess. 0.67 (the original ladder run's reading) sits just below 0.70 — outside the
band on the low side, not inside it. [[D-20]]

**Not yet derived:** TA's own no-action band, and the TA+SAT combined band, are not necessarily this
same interval — deriving them is a prerequisite for testing those configurations against §2's decision.

**1.2 — A short-output leg** (e.g. 2000 in / 100 out), to probe the ITL lower knee. The current
"long-input" shapes are decode-dominated, not prefill-heavy — prefill-heavy needs short outputs, not
merely long inputs. Corroborating measurement: `itl ~ running` alone reaches r² 0.93–0.94 below the
band; adding a prefill term buys +0.001 there vs. +0.236 in-band. Same mechanism defect as §1.1 applies
here, more sharply — a knee is a property of load *per replica*, and the autoscaler's job is to keep
load per replica off it. Implemented (`ta_prefill_knee.yaml.in`) but its sharp instrument is a fixed
replica count with autoscaling off, a scenario decision not yet made.

**1.3 — Let the run outlive the cooldown.** ≥300 s of collection after load stops, or scale-down never
lands inside the measurement window. **Agreed with an addition:** any scenario starting above 0
replicas needs its analysis window to start after boot lag clears, matching the simulation convention
already used elsewhere — **not yet implemented in the extractor**, which currently analyzes from t=0
regardless of starting replica count.

**Measurement constraint, applies to all three.** A routing oscillation with a 6–11 s period is aliased
away by every gauge-derived series at the ~15.7 s scrape cadence (Nyquist ~31 s) — it was visible at all
only because the gateway access log records `UPSTREAM_HOST`. A finer scrape rate does not fix this and
neither does a per-pod gauge; the per-request trace is a requirement, not a nice-to-have.

**Two corrections to propagate wherever cited:** the decision rule is `rc = demand/0.85 − supply`, then
`curr + ceil(rc/prc)` applied to the residual — not `ceil(demand/prc)`. And `bytes_sent` is not a valid
per-request output-token weight (median calibrates, dispersion doesn't); `x-envoy-upstream-service-time`
is not TTFT (flat while harness TTFT climbs).

**Retention exception.** The multi-GB per-replica files go on cleanup; `metrics/raw/` stays (12–35
MB/run, the only time-resolved source of KV/running/waiting/ITL/preemption).

---

## 2. The dwell operating point — decided, generalized

**Decision: (a).** Saturation alone, uncapped. Generalizes to *any* analyzer combination under test —
not a SAT-specific answer. [[D-19]]

The goal itself was corrected first: not "manufacture a dwell so a slope is fittable," but "run long
enough, under whichever analyzer combination is under test, that eventual steady-state arrival is
observable at all." Transition time is a secondary measurement, not the target. [[D-18]]

| Option | Configuration | What it measures |
|---|---|---|
| **(a) — decided** | Saturation alone, uncapped (TA off, `maxReplicas` at 10) | SAT's own right-sizing, isolated from the combined optimizer |
| (b) — instrument only, not a default | A deliberate replica cap | the cap itself — every latency number at a binding cap describes the cap, not the controller |

**The sawtooth already ran — not a fallback still to try.** The staged quantization-sawtooth workload
(two 360 s rungs, 20 and 26 RPS) executed in the 2026-08-10 campaign as all three `*-dwell` cells.
Neither sat-voting cell reached steady state — both hit the replica cap of 10 twice (a limit cycle,
analyzer-independent). This does **not** confirm or refute (a) — it shows the runs were too short to
test steady-state arrival at all, which is exactly what the dwell deep-dive below is now investigating.

---

## 3. The dwell limit cycle — mechanism found, forecast gap open

**A dedicated deep-dive session answered "why does the limit cycle happen."** Full trace:
[`session/status/dwell-deep-dive.md`](../session/status/dwell-deep-dive.md); folded into
[`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md) Finding 2. [[D-21]]

- A single anomalous `P1-obs` sample triggers the excursion — real, by-design (unclamped demand/supply
  ratio), not a units bug.
- The dominant lag is created→ready, not ordered→created — physical (model load + GPU scheduling
  contention under concurrent boots), not a control-loop defect. The controller retreats from its own
  peak order before the last replica it asked for ever becomes ready.
- `TotalAnticipatedSupply` is confirmed correctly implemented — no double-booking.

**The actual gap, new Type-1 design surface, not a bug fix:** the demand side has no forecast that
already-ordered, already-created (not-yet-ready) replicas will relieve the queue once ready — so demand
is sized off an instantaneous snapshot that's already about to shrink. Shared between saturation and
TA. **Whether/how to scope this is explicitly Dean's call**, tracked at
`session/handoffs/plan__dwell-limit-cycle-forecast-todo.md.WIP` — not decided here.

**PVC ceiling, a deliberate omission:** a rung above 26 RPS doesn't fit the 20Gi results PVC beside the
two dwell rungs (~5.1 GB more) — the natural follow-up only if a longer dwell run still reads outside
`[0.70, 0.85]`.

---

## 4. Workload coverage matrix + theory/simulation/real baseline — not built

**Two asks, Dean, neither built yet.** [[D-13]] *(cross-referenced from the campaign doc, not a
standalone D-entry — folded here as it's scenario-design surface)*

**4.1 — A coverage matrix.** One table, every `ta_autoscale_*.yaml`/`ta_prefill_knee.yaml` workload
alongside its purpose and expected outcome. Nothing today lets a cold reader scan the whole workload
set at once or notice a coverage gap.

**4.2 — A three-artifact baseline, not just a table.** *"Theory based on simulation + viz, simulation
based on actual workload generated + viz — a synthetic baseline before we actually benchmark."* Three
artifacts per workload, in order: (1) a theoretical prediction from the analytical model alone, rendered
through the viz panel set on synthetic input; (2) a simulation driven by the actual generated workload
(not the analytical idealization), same panel set, still before touching a cluster; (3) the real
benchmark result, compared against both rather than read cold. Would likely have flagged the sawtooth
cells' actual problem (too short to reach steady state) before spending cluster time on them.

**Ownership split, not yet made.** The coverage matrix and the theory/simulation legs are viz-side, per
Dean's own scoping (viz owns synthetic simulation and simulation-following-a-test — see
[`autoscaling-viz-design.md`](autoscaling-viz-design.md)); the workload-spec-to-purpose mapping itself
may belong in a benchmark Type 1 instead, since it's about what benchmark *runs*, not what viz
*computes*. No benchmark Type 1 exists yet to receive it.

---

## 5. Cold-resume state for the staged dwell run

**Staged and unlaunched.** No cluster action has been taken and no run is proposed. Standing rule
holds: no run without Dean's explicit approval.

- **Config staged, not launched:** the dwell and prefill-knee workload files, local-only on `benchmark`.
- **Four preconditions before the run:** reclaim the results PVC to ≥14 GB with `verify_pvc_vs_host.py`
  gating it; confirm the 96Gi harness pod schedules; set the 5-GPU footprint flag; run
  `post_run_analyze.sh` immediately after — the ladder run's missing `metrics/processed/wva_*` came from
  skipping this step promptly while the controller log was still a rotating buffer.
- **Restart the controller before each run** — capacity history is bucket-keyed and was found
  contaminated across runs. Adopted protocol, not a suggestion.
- **GPU state:** the ladder run's GPUs are released; one GPU remains held by the decode replica's
  `minReplicas=1` steady state — separate open question, coder-tracked.
- **T9 is DONE** — the gateway log-follower is wired into `benchmark-run` automatically (commit
  `3ab8128a`, execution plan §7.1 T9, [[D-27]]). Structurally verified, not yet exercised live — the
  dwell run itself will be its first real exercise.

**Next steps, in order:**
1. Coder satisfies the four preconditions; restarts the controller.
2. Dean approves the run. Coder runs it, then `post_run_analyze.sh` immediately.
3. Dwell deep-dive session's own findings (§3 above) determine whether a longer run is the next
   experiment, or whether the forecast-gap work supersedes running more dwell attempts.
