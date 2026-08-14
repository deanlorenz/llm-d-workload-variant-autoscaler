# TA on pokprod — Campaign Report

**Status:** current, live. Replaces `ta-pokprod-campaign-20260810-results.md` and
`ta-pokprod-rerun-results-20260813.md` (both superseded, content folded in below, kept on disk
for old section-number citations). **Scope:** cross-cutting conclusions and current data across
every pokprod run to date. No benchmark history/narrative — see
[`ta-pokprod-history.md`](ta-pokprod-history.md) for how any of this came to be.

**Companion docs:** [`ta-pokprod-workload-coverage.md`](ta-pokprod-workload-coverage.md) (which
workloads exist, why) · [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md)
(Type 1) · [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (Type 3, phased history)
· [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) (Type 3, live checklist) ·
[`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger, `[[D-nn]]` fetchable by
`grep -n '^## D-nn'`).

**⚠️ No viz output exists for any run since 2026-08-10.** Every panel cell below is a placeholder
until the autoscaling-viz scope generates figures — handed off, not run by this scope. Placeholder
text is used explicitly; there is no broken link anywhere in this doc.

---

## Section 1 — Workload × WVA-config results

Three WVA configurations appear across this campaign: **sat** (saturation analyzer only), **TA**
(throughput analyzer only), **satTA** (both, saturation+throughput). Cells below are sparse where
a workload hasn't run under every config — see
[`ta-pokprod-workload-coverage.md`](ta-pokprod-workload-coverage.md) for the 4 runs in flight to
close the two remaining gaps (prefill-knee, calibration-probe × {sat, satTA}).

### ta_autoscale_staircase.yaml.in

**Load:** 2048 in / 512 out tokens, short plateaus staged low→high rps (5/12/18 rps, ~2 min per
stage), sized to stay within a 2-replica decode cap's serviceable capacity — an autoscaling
harness shakedown, deliberately not a saturation sweep (climbing past capacity would hang the
harness on an unbounded backlog).

| Metric | sat | TA | satTA |
|---|---|---|---|
| Run | `dean-20260810-080708-371` | `dean-20260810-084756-739` | `dean-20260810-064736-555` |
| P99 TTFT (ms) | pending re-postprocess | pending re-postprocess | pending re-postprocess |
| P99 ITL (ms/tok) | pending re-postprocess | pending re-postprocess | pending re-postprocess |
| Avg / max replicas | 2.24 / 8 | 2.24 / 3 | 2.10 / 3 |
| Avg KV% | 16.2% | 11.7% | 12.8% |
| Avg pod startup (s) | 76 | 65 | 85 |
| Errors | 0 | 0 | 0 |
| Report | [REPORT.md](../../benchmark/runs/dean-20260810-080708-371/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260810-084756-739/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260810-064736-555/REPORT.md) |
| Panels | *pending viz generation* | *pending viz generation* | *pending viz generation* |

*TTFT/ITL/queue-depth show `?` in these runs' REPORT.md — they predate the D-39 postprocess.py
fix (2026-08-12) and have never been re-extracted from the raw per-request data still on disk.
Re-extraction handed to the benchmark coder
(`benchmark__reprocess-staircase-runs-predate-postprocess-fix.md`); this table updates once done.*

**Cross-config comparison.** sat-only over-provisions AND delivers worse latency: 8 max replicas
vs 3 for both TA-voting configs, on identical offered load/image/request count. Both TA-voting
configs (TA-only, satTA) land at the same 3-replica ceiling with visually all-green latency in the
source panels — saturation-voting is not a logging artifact, it changes the replica trajectory 3×
and (per the original panel read) the user-visible latency band from all-green to failed.

### ta_autoscale_dwell.yaml.in

**Load:** 2048 in / 512 out tokens, sustained rate rungs inside the no-action band `[0.70, 0.85]`
kv%, meant to hold long enough to observe eventual steady-state right-sizing rather than measure
transition speed.

| Metric | sat | TA | satTA |
|---|---|---|---|
| Run (2026-08-10 / rerun 2026-08-13) | `...100827-539` / `...013728-756` | `...105211-685` / `...000928-609` | `...092644-320` / `...005321-943` |
| P99 TTFT (ms), rerun | 91,712 | 3,568 | 3,392 |
| P99 ITL (ms/tok), rerun | 151.97 | 64.90 | 65.98 |
| Avg / max replicas, rerun | 2.93 / 10 | 4.13 / 10 | 3.62 / 6 |
| Avg queue depth, rerun | **32.4** | 0.0 | 0.0 |
| Errors, rerun | 1 | 0 | 1 |
| Report (rerun) | [REPORT.md](../../benchmark/runs/dean-20260813-013728-756/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260813-000928-609/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260813-005321-943/REPORT.md) |
| Panels | *pending viz generation* | *pending viz generation* | *pending viz generation* |

*Original 2026-08-10 runs and the 2026-08-13 clean reruns both exist; the rerun row above is the
authoritative one — the original `m-ta-dwell` was truncated (r²=0.11 ITL fit) and superseded, the
original sat/satTA cells hit the limit cycle described below and remain valid evidence for that
mechanism even though they're not a clean steady-state reading.*

**Cross-config comparison.** `m-sat-dwell`'s tail latency is roughly 25× worse than either
TA-analyzer dwell cell on an otherwise-comparable clean run (P99 TTFT 91,712ms and queue depth
32.4 vs single digits) — the sharpest confirmation yet of saturation-lags-demand (§ *Analysis by
topic* below). **No config has escaped the dwell limit cycle to produce a genuine steady-state
reading** — the original satTA and sat cells both rode to the replica cap (10) and collapsed
twice; this is a known, understood mechanism (§ *Analysis by topic*), not resolved by any config
choice tested so far.

### ta_calibration_probe.yaml.in / ta_calibration_probe_p4.yaml.in

**Load:** 4096 in / 1024 out tokens, 8-stage sweep near-idle→above-saturating (~12 min), meant to
give the throughput analyzer enough KSpread≥0.30 samples to leave its T2-default fallback — "does
TA do anything at all." The p4 variant divides each stage's rate by 4 for use with 4 parallel
harness pods (the OOM fix, D-42).

| Metric | TA (attempt 1, OOM) | TA (retry, clean) | TA-p4 (4 pods) | sat | satTA |
|---|---|---|---|---|---|
| Run | `...203217-894` | `...231722-822` | `...130251-004` | *pending* | *pending* |
| P99 TTFT (ms) | ? (OOM before postprocess) | 20,088 | 19,053 avg | — | — |
| P99 ITL (ms/tok) | ? | 136.79 | 139.93 avg | — | — |
| Avg / max replicas | 6.00 / 9 | 6.25 / 10 | 4.50 / 9 | — | — |
| Errors | 0 (partial data, OOM before completion) | 0 | 0 (all 4 pods) | — | — |
| Report | [REPORT.md](../../benchmark/runs/dean-20260812-203217-894/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260812-231722-822/REPORT.md) | [REPORT.md](../../benchmark/runs/dean-20260813-130251-004/REPORT.md) | — | — |
| Panels | *pending viz generation* | *pending viz generation* | *pending viz generation* | — | — |

*sat/satTA columns: 2 new runs approved 2026-08-14, in flight — see
`ta-pokprod-workload-coverage.md`.*

**Cross-config comparison:** not yet possible — only TA config has run for this workload. Deferred
until the sat/satTA runs land.

### ta_prefill_knee.yaml.in

**Load:** ~2000 in / ~100 out tokens, prefill-dominated shape, to probe the ITL lower knee — moves
the stimulus (shape), not the rate, kept as a separate run from the dwell workload for a clean
comparison axis.

| Metric | TA |
|---|---|
| Run | `dean-20260812-152105-714` |
| P99 TTFT (ms) | 40,657 |
| P99 ITL (ms/tok) | 422.06 |
| Avg / max replicas | 3.21 / 10 |
| Avg queue depth | 49.2 |
| Errors | 1 |
| Report | [REPORT.md](../../benchmark/runs/dean-20260812-152105-714/REPORT.md) |
| Panels | *pending viz generation* |

*sat/satTA columns: 2 new runs approved 2026-08-14, in flight.* Ran under TA config with live
autoscaling (controller on) — a separate, still-unmade scenario decision exists on whether a
sharper fixed-replica/autoscaling-off variant is worth building (see coverage doc).

### ta_autoscale_ladder.yaml.in

Superseded by staircase/dwell; 1 run (2026-08-07, pre-`runs/` era), not rerun, no plan to rerun.
Listed for completeness only.

---

## Section 2 — Analysis by topic

### The dwell limit cycle

`m-satta-dwell` and `m-sat-dwell` (original 2026-08-10 run) show the same envelope: ride to the
replica cap of 10, collapse to 2, climb again — two full excursions each, indistinguishable
between analyzer configurations. The dwell is a property of the **controller/workload
interaction**, not the analyzer configuration — steady-state KV under a tracking controller is a
*controlled* variable, so the dwell is a configuration lever, not an offered-rate one.

**Mechanism, traced end-to-end against the actual controller code** (full trace:
`session/status/dwell-deep-dive.md`):
1. **The excursion's trigger is a single anomalous `P1-obs` sample, not accumulated demand.** The
   2→10 replica jump coincides exactly with saturation's `P1-obs` (`k2SrcObserved`) reason code
   reporting `util=3.89` — `util>1` is by design (an unclamped demand/supply ratio), not a units
   bug. Reproduced worse in sat-only than sat+TA — saturation drives the excursion regardless of
   whether TA is also configured.
2. **The lag decomposes into two hops; only one is the bottleneck.** Ordered→created is fast (~1
   tick, ~60s, matching the KEDA poll interval). Created→ready is slow and worsens with concurrent
   boot count (model load + GPU scheduling contention) — the dominant mechanism, physical, not a
   control-loop defect. In the first excursion, `ready` peaked at 9 and never reached the
   ordered/created peak of 10 — the controller retreated from its own peak order before the last
   requested replica ever became ready.
3. **`TotalAnticipatedSupply` is confirmed correctly implemented** — replicas already
   ordered+created are correctly netted out; no double-booking.

**The real gap: no forecast of the queue's own resolution.** `P1-obs` sizes demand off the
*instantaneous* queue snapshot, with no model that already-ordered, already-created (not-yet-
ready) replicas will relieve that queue once they come online. Shared between saturation and TA,
not saturation-specific — new Type-1 design surface, not a bug fix. Scoping deferred by Dean
2026-08-14 — not critical path for tooling/runs.

**A second, additive mechanism (original 2026-08-08 dwell run, not superseded by the above):**
saturation's capacity history (`prc`) keys on a discretized bucket of average output length; this
workload's mean output (512, sd 20) sits 12 tokens above the 500-token bucket edge, so ordinary
sampling noise can flip the bucket key mid-run and swap in a stale or cross-workload history.
Status: strong, code-located hypothesis, not confirmed from logs. Deprioritized 2026-08-14 —
workaround is shifting the workload's output length off the bucket edge; a real WVA fix would be
a separate, lower-priority issue.

**No run has escaped this limit cycle to produce a genuine steady-state dwell** — true across
both campaigns, all three configs. A limit cycle has no well-defined mean; any dwell-cell KV
number should be read as a distribution (p50/p90/max), not a mean.

### Saturation lags demand

Consistent finding across both campaigns: sat-only configuration delivers markedly worse tail
latency than any TA-voting configuration, on otherwise-comparable runs. Staircase: sat-only
reaches 8 max replicas (both TA-voting configs stay at 3) on identical load. Dwell rerun:
sat-only shows P99 TTFT 91,712ms and queue depth 32.4, roughly 25× worse than either TA-analyzer
cell on the same metric. Saturation-voting changes real replica trajectory and user-visible
latency — not a logging artifact (the engine computes-and-logs-always but votes-conditionally, so
raw log-line counts alone cannot answer the disable question — traced independently via replica
count and latency instead).

**Open, uninvestigated:** why TA-only (saturation non-voting) still drove a live replica path
(2→3→2→3→2, 19 scaling decisions) on the staircase cell — what TA alone is actually doing to
produce that trajectory. The data can answer this; nobody has looked yet.

### The knee / piecewise ITL model

TA is a pure rate analyzer, not an SLO enforcer — it asks one question: at `kv% = k_sat` (default
0.85), what is the decode rate? The estimation path is ITL, not rate directly: TA fits ITL vs.
concurrency, converts to rate. The fit is genuinely two-segment piecewise, split at `k_knee`, with
a much steeper slope above the knee — mechanistically real, not a fitting artifact. Past the knee,
there are no longer enough decodes per prefill to amortize prefill cost, so the per-iteration cost
ratio flips toward `prefill_time >> single_token_decode_time`, driving concurrency (and therefore
ITL) up rapidly. If `k_sat` falls above `k_knee` for a workload's shape, the fit must extrapolate
from the post-knee segment, not the pre-knee one, or it badly misestimates `decode-rate(k_sat)`.
(Full correction, viz-panels-planner scope: `session/handoffs/plan__sim-from-benchmark-item6-correction.md`.)

### Queue / drain behavior — what's measured, what isn't

Per-stage latency/failure/token-rate data survives for every stage of every dwell cell even
without a per-request trace (`stage_N_lifecycle_metrics.json` — real numbers, not lost).
Genuinely and only lost without a per-request trace: within-stage latency-distribution shape as
load ramps inside a single rung, per-request identity (router pod, exact arrival instant), and
router-oscillation detection (a 6–11s period is below the ~15.7s scrape cadence's Nyquist limit —
only a per-request trace carrying `UPSTREAM_HOST` can see it). Per-request collection is disabled
by standing policy (its own OOM risk, D-41) — fallback signals are the current direction, not yet
built.

### Controller-restart hold-at-current-replicas policy

A controller restart left decode pinned at 10/10 replicas for 15+ minutes with zero active load
(`demand=0, util=0, rc=0`), never trending down. Read-only source investigation
(`internal/engines/saturation/engine.go`, `applySaturationDecisions`, ~L1601-1701) found a
plausible mechanism: when the optimizer has no fresh decision this cycle, the code deliberately
holds at the current replica count — falls back through persisted CR status, `currentAllocations`,
then the live Deployment's actual replica count — explicitly to avoid unintentionally scaling to
zero on a transient uninformative cycle (stated in the code's own comments). This is a **designed
hold-on-no-decision policy, not a computation bug**. Not confirmed live (static read only); the
open question is whether "hold" is the right policy for a *sustained* window, a policy question,
not a defect report. Possibly the same mechanism family as the still-open replica-oscillation
thread above (both trace through the same hold/current-replicas fallback logic), not proven to be
one single bug.

### The OOM fix (inference-perf's own memory model)

Root cause, source-confirmed at `inference_perf/client/modelserver/openai_client.py` and
`multiprocess.py`: every request's full JSON body and every response's full text are held in one
unbounded Python list for the entire run, never flushed until the run ends. Any sufficiently
long/high-rate profile hits this eventually — not fixable from this side (upstream code). Fix:
`LLMDBENCH_HARNESS_LOAD_PARALLELISM=4` (or `--parallelism`) spawns N harness pods running the
*same* profile unchanged — this multiplies aggregate load, it does not divide it, so the workload's
own rates must be divided by N first to keep the original offered-load intent while dividing each
pod's accumulator share by N. Validated by a real run: 4 parallel pods, 0 errors across all four,
P99 TTFT consistent to within ~1% (18,524–19,320ms).

---

## Section 3 — Run index

One row per run, one experiment per row. **Completed** = the harness ran to full completion
without crashing/OOMing (independent of whether the run's *measurement goal* was achieved — see
Section 1 for measurement outcomes).

| Run ID | Date/time (UTC-ish, from run ID) | Workload | Config | Completed? | Results dir |
|---|---|---|---|---|---|
| `dean-20260810-064736-555` | 2026-08-10 06:47 | staircase | satTA (main image) | ✅ | [runs/dean-20260810-064736-555](../../benchmark/runs/dean-20260810-064736-555) |
| `dean-20260810-072736-888` | 2026-08-10 07:27 | staircase | satTA (baseline image) | ✅ | [runs/dean-20260810-072736-888](../../benchmark/runs/dean-20260810-072736-888) |
| `dean-20260810-080708-371` | 2026-08-10 08:07 | staircase | sat | ✅ | [runs/dean-20260810-080708-371](../../benchmark/runs/dean-20260810-080708-371) |
| `dean-20260810-084756-739` | 2026-08-10 08:47 | staircase | TA | ✅ | [runs/dean-20260810-084756-739](../../benchmark/runs/dean-20260810-084756-739) |
| `dean-20260810-092644-320` | 2026-08-10 09:26 | dwell | satTA | ✅ (limit-cycled, not steady-state) | [runs/dean-20260810-092644-320](../../benchmark/runs/dean-20260810-092644-320) |
| `dean-20260810-100827-539` | 2026-08-10 10:08 | dwell | sat | ✅ (limit-cycled, not steady-state) | [runs/dean-20260810-100827-539](../../benchmark/runs/dean-20260810-100827-539) |
| `dean-20260810-105211-685` | 2026-08-10 10:52 | dwell | TA | ⚠️ truncated (campaign paused mid-run) | [runs/dean-20260810-105211-685](../../benchmark/runs/dean-20260810-105211-685) |
| `dean-20260812-152105-714` | 2026-08-12 15:21 | prefill-knee | TA | ✅ | [runs/dean-20260812-152105-714](../../benchmark/runs/dean-20260812-152105-714) |
| `dean-20260812-154829-365` | 2026-08-12 15:48 | calibration-probe | TA | ❌ interrupted, no REPORT.md, not a distinct result | [runs/dean-20260812-154829-365](../../benchmark/runs/dean-20260812-154829-365) |
| `dean-20260812-203217-894` | 2026-08-12 20:32 | calibration-probe | TA | ❌ OOMKilled at 32Gi, 16 min in | [runs/dean-20260812-203217-894](../../benchmark/runs/dean-20260812-203217-894) |
| `dean-20260812-231722-822` | 2026-08-12 23:17 | calibration-probe | TA | ✅ (unmodified retry, same 32Gi) | [runs/dean-20260812-231722-822](../../benchmark/runs/dean-20260812-231722-822) |
| `dean-20260813-000928-609` | 2026-08-13 00:09 | dwell (rerun) | TA | ✅ | [runs/dean-20260813-000928-609](../../benchmark/runs/dean-20260813-000928-609) |
| `dean-20260813-005321-943` | 2026-08-13 00:53 | dwell (rerun) | satTA | ✅ | [runs/dean-20260813-005321-943](../../benchmark/runs/dean-20260813-005321-943) |
| `dean-20260813-013728-756` | 2026-08-13 01:37 | dwell (rerun) | sat | ✅ | [runs/dean-20260813-013728-756](../../benchmark/runs/dean-20260813-013728-756) |
| `dean-20260813-130251-004` | 2026-08-13 13:02 | calibration-probe-p4 | TA (÷4, 4 pods) | ✅ (all 4 pods, 0 errors) | [runs/dean-20260813-130251-004](../../benchmark/runs/dean-20260813-130251-004) |

**4 runs pending, not yet in this table** (approved 2026-08-14, in flight): prefill-knee × {sat,
satTA}, calibration-probe × {sat, satTA} — see `ta-pokprod-workload-coverage.md`.

---

## What the figures do not license (carried forward, still applies)

1. **One run per cell (except the 3 dwell reruns and the p4 4-pod validation). No repeats, no
   noise floor.** Most numbers above are mechanism observations, not statistically-controlled
   benchmark comparisons.
2. **The dwell workload has never produced a genuine steady-state reading, in any config.** Any
   dwell-cell KV/latency number describes a limit-cycling system's transient behavior, not a
   settled operating point — read the mechanism sections above before citing a dwell number as a
   steady-state fact.
3. **`tput_knee()` and `capacity()` (viz toolchain internals cited implicitly via any future panel
   link) have never been formally reviewed by Dean** — treat their outputs as "what the code
   currently does," not "a reviewed and agreed method," until that review happens.
4. **Router-oscillation claims need a per-request trace** — scrape-cadence-derived panels cannot
   see sub-Nyquist oscillation by construction.
