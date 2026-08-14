# TA on pokprod — Workload Coverage Matrix (Type 3)

**Status:** current, live. **Scope:** every canonical workload template under
`benchmark/hack/benchmark/workloads/inference-perf/ta_*.yaml.in`, its purpose (from its own
docstring), and its actual run history. Answers `open-scenarios.md` §4.1's ask — one table, every
`ta_*` workload alongside purpose and expected outcome, so a cold reader can scan the whole set at
once and spot a coverage gap. **Owned here** (benchmark-execution scope), not viz-side — this is
about what the benchmark *runs*, not what viz *computes*. §4.2's theory/simulation/real baseline
legs remain viz-panels-planner's, separately.

**Companion docs:** [`ta-pokprod-campaign-report.md`](ta-pokprod-campaign-report.md) (all
results/findings) · [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) §4 (this
matrix's origin ask) · [`ta-pokprod-history.md`](ta-pokprod-history.md).

---

## Coverage matrix

| Workload template | Purpose (from its own docstring) | Shape | Runs in `runs/` | Outcome |
|---|---|---|---|---|
| `ta_autoscale_staircase.yaml.in` | Autoscaling harness shakedown, NOT a saturation sweep — short plateaus staying within replica-cap serviceable capacity, to exercise the scale-up/scale-down path itself without hitting the wall | 2048in/512out, staged low→high rps, capped replicas | 4 (2026-08-10 campaign, all `m-*-staircase` cells) | ✅ Done — original 7-cell campaign; findings folded into campaign results doc |
| `ta_autoscale_ladder.yaml.in` | Higher-load successor to staircase, multi-replica ladder sized to match Ofer's single-variant rate ladder — finds where a low replica cap starts binding | 2048in/512out, multi-stage ladder | 1 (2026-08-07, pre-`runs/` era, migrated in) | ✅ Done — the original 2-replica cap was found binding at 12 rps, motivating the dwell/staircase successors; superseded as the active shape, not rerun since |
| `ta_autoscale_dwell.yaml.in` | Mid-band dwell — successor to ladder, reshaped around steady-state right-sizing rather than transition speed; hold an offered rate inside the no-action band `[0.70, 0.85]` long enough to observe eventual steady-state arrival | 2048in/512out, sustained rate rungs | 6 (2026-08-10 campaign ×3 + 2026-08-13 reruns ×3) | ✅ Clean data exists (3 reruns), but the **limit-cycle mechanism means no run has produced a genuine steady-state dwell yet** — see D-21/D-28/D-45; this is a known, understood gap, not an unexplained one |
| `ta_calibration_probe.yaml.in` | Sweeps rate near-idle→above-saturating at fixed 4096in/1024out shape, so TA gets enough KSpread≥0.30 samples to leave its T2-default fallback — "does TA do anything at all" bar | 4096in/1024out, 8-stage sweep, ~12 min | 3 (1 OOM, 1 clean retry, both 2026-08-12; 1 more folds into the p4 line below) | ✅ Clean data via the retry (D-38/D-41); original OOM's partial data kept per Dean's "data from all cases" |
| `ta_calibration_probe_p4.yaml.in` | Rate-divided (÷4) variant of the probe above, for `LLMDBENCH_PARALLELISM=4` — validates the OOM fix by construction, not a new scenario | 4096in/1024out, ÷4 per pod, 4 parallel pods | 1 (2026-08-13, 4 parallel pods = 4 result dirs under one run) | ✅ Done — 0 errors across all 4 pods, P99 TTFT consistent to ~1% (D-42/D-43); fix validated |
| `ta_prefill_knee.yaml.in` | Short-output/prefill-dominated shape (~2000in/~100out) to probe the ITL lower knee — moves the *stimulus* (shape), not the rate, so it stays a clean axis separate from the dwell workload | 2000in/100out | 1 (2026-08-12, first live exercise of the results-tree pipeline) | ✅ First live run done, and it surfaced + fixed a real `postprocess.py` bug (D-38/D-39) as a side effect; not yet run at more than one rate/replica-cap combination |

---

## What this table answers, and what it doesn't

**Answers §4.1 in full** — every canonical workload, its purpose, and whether it's been run. No
`ta_*` template exists that has never been run at least once.

**Does not answer §4.2** — the theory/simulation/real three-artifact baseline per workload. That
remains viz-panels-planner's scope (synthetic prediction + simulation-from-generated-workload,
both before touching a cluster, compared against the real result above). Not started for any
workload in this table.

**Open, within this scope:**
- `ta_autoscale_dwell` — 6 clean runs exist, but none has escaped the limit cycle to produce an
  actual steady-state dwell. Whether that needs a longer run, a forecast fix (D-45 §2, deferred),
  or is simply not achievable under saturation-alone at this workload's shape is still open.
- `ta_prefill_knee` — **the config-grid gap is closed** — all 3 configs now have data (D-50). A
  separate, still-open item remains: the workload's own docstring flags a sharper
  fixed-replica/autoscaling-off instrument as a scenario decision never made — unrelated to the
  config grid, not addressed by the new runs.
- `ta_autoscale_ladder` — superseded by dwell/staircase; no plan to rerun it, listed here for
  completeness of the coverage picture, not as an open item.
- `ta_calibration_probe` — **the config-grid gap is closed** — all 3 configs now have data (D-50),
  including a second confirmed OOM (sat config, same mechanism as the earlier TA-only OOM,
  resolved the same way: an unmodified retry, not the p4 variant).

**All 6 workload templates now have every config their own design intends — closed 2026-08-14
(D-50).** `ta_autoscale_ladder` excepted (superseded, never intended for a 3-config comparison).
Two harness process gaps surfaced during the gap-fill runs, flagged not fixed — full detail in
[`ta-pokprod-campaign-report.md`](ta-pokprod-campaign-report.md) § *Two harness process gaps*.
