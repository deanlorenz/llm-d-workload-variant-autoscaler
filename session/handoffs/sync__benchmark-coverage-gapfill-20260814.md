from: benchmark
to: sync
session: benchmark

**Ref:** `session/status/benchmark.md` §20.34 (full detail).

## What changed

Processed `benchmark__fill-grid-gaps-prefill-knee-calibration-probe.md` (now `.DONE`): 4 runs
approved by Dean 2026-08-14, filling the coverage-matrix gap for `ta_prefill_knee` and
`ta_calibration_probe` (both had only ever run TA-only). Six commits, all local, DCO-signed, not
pushed: `d3c7d5d8` (4 new sat/satTA env files), `07988f6b` (m-sat-prefill-knee), `bd82645b`
(m-satta-prefill-knee), `7fb3f124` (m-sat-calibration-probe, OOM'd, partial data kept), `d682c82d`
(m-sat-calibration-probe, clean retry), `1db6e216` (m-satta-calibration-probe).

**Results:**
- `m-sat-prefill-knee`: P99 TTFT 59,990ms, queue depth 67.5 — far worse than TA-only, consistent
  with the established saturation-lags-demand pattern.
- `m-satta-prefill-knee`: P99 TTFT 61,201ms, queue depth 71.1 — nearly identical to sat-only;
  throughput analyzer doesn't help this workload's short-output shape.
- `m-sat-calibration-probe`: OOM'd once (same mechanism as the earlier TA-only OOM), succeeded
  clean on an unmodified retry — P99 TTFT 17,105ms, close to the TA-only result (20,088ms). Per the
  coverage-matrix doc's explicit constraint, did NOT switch to the p4/rate-divided variant.
- `m-satta-calibration-probe`: P99 TTFT 4,798ms — ~3.5x better than sat-only, queue depth 0.0 vs
  3.5. Unlike prefill-knee, satTA clearly helps this workload's shape.

Coverage-matrix gap now closed: both workloads have all 3 configs (TA-only, sat, satTA) landed.

GPUs freed at the end (ScaledObject paused at 0, decode scaled to 0, 0 pods verified).

## Two process/tooling gaps found — for a planner, not fixed in code

1. **`reset_run.py`'s `benchmark-reset-run` step does not actually unpause KEDA** — its own code
   comment says so ("does NOT un-pause KEDA... the script reports the pause and leaves it"). The
   log line that looks like an unpause action (`autoscaling.keda.sh/paused-replicas-`) is a printed
   suggested command, not an executed one. Every run implicitly depends on someone having unpaused
   the ScaledObject manually beforehand — caused today's first failure (`verify_model: no pods
   available`). Worth a planner's decision: is print-not-do intentional (a deliberate safety gate
   requiring a human decision to start scaling), or should `--apply` also unpause?

2. **`run_cell.sh`'s failure path can fall through to analyzing/overwriting an already-committed,
   different run's config files.** When step [4/6] `run` fails before producing a fresh results
   directory, step [6/6] `analyse` falls through to the most recent existing `runs/*/results/*`
   directory instead of failing cleanly. Caught 3 times today via unexpected `git status`
   modifications to files from earlier, unrelated cells; restored each time with `git checkout --
   <path>`. One partial staleness guard exists (skips overwriting a timeseries JSON if the new parse
   has fewer snapshots than the existing file) but it's incomplete — the config files still get
   clobbered around it. This is a real correctness gap in the failure path, not something I patched
   mid-cycle given the time-sensitive gap-fill in progress.

## Update CURRENT.md

Fold into the benchmark abstract: the 4-run coverage-matrix gap-fill is done (both workloads now
have all 3 analyzer configs), and flag the two process gaps above as open items for a planner to
scope — pointing at §20.34 rather than restating detail.
