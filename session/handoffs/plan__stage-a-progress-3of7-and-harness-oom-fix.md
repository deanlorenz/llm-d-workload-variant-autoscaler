to: plan
reason: Stage A clean-recapture campaign -- progress update at 3/7 cells (dwell-warmup trio complete), a real bug found+fixed along the way
refs:
  - planning/ta-pokprod-clean-recapture-plan.md
  - session/handoffs/benchmark__clean-recapture-stage-a-launch.md.WIP (the trigger this is reporting against; still WIP, not closing yet -- 4 cells remain)
note: |
  Progress update on Stage A, not a completion report -- campaign is still running, this is a
  substantial-partial-work checkpoint. Sending now rather than waiting for all 7 cells because a
  real (initially misdiagnosed) bug was found and fixed along the way and that's worth surfacing
  promptly rather than only at the end.

  **Done and committed (all on `benchmark` branch, DCO-signed):**

  1. Log-capture fix (D-63 option (a)): `capture_igw_from_follower()` added to the embedded
     llm-d-benchmark clone (`llmdbenchmark/utilities/kube_helpers.py`, commit `28f1ed3` on that
     clone's own history), reads the gateway-log-follower's durable PVC copy directly instead of
     the rotation-vulnerable `kubectl logs` path, with correct fallback to the old path if the
     window/metadata isn't available. Verified working on real campaign data (cell 1's IGW log
     has no `kubectl logs` pod-prefix).

  2. Warmup-stage profiles: 3 new files under `hack/benchmark/workloads/inference-perf/`
     (`ta_autoscale_dwell_warmup.yaml.in`, `ta_calibration_probe_warmup.yaml.in`,
     `ta_calibration_probe_p4_warmup.yaml.in`) -- new files, not in-place edits, per the
     established convention (in-place edit would have changed already-landed runs' own
     request-count identity; caught and reverted a first attempt that did this wrong). Committed
     `eb20ef53`. 7 new env files for the Stage A cells committed `e1b65272`.

  3. **Harness OOM root cause found and fixed** (this is the part worth flagging directly). The
     dwell-warmup workload's warmup stage adds ~7,020 extra requests; the harness's own baseline
     (non-per-request) memory footprint scales with total request count over the run's full
     duration, and the scenario's harness pod was silently rendering at the 32Gi *global default*
     instead of the 96Gi this workload has needed for months (documented in
     `ta_autoscale_dwell.yaml.in`'s own docstring, never actually wired into the scenario file).
     Caused 4 consecutive OOMKilled/failed harness pods before I found it.

     Two of those 4 failures were my own mistake, not the same bug repeating: I fixed the override
     twice in `llm-d-benchmark/config/scenarios/guides/two-variant-wva.yaml` (the embedded clone's
     copy) and verified it was on disk both times -- but `make benchmark-run`'s "Copying local
     scenario" Makefile step overwrites that file from
     `hack/benchmark/scenarios/guides/two-variant-wva.yaml` (the real source of truth, tracked on
     the `benchmark` branch itself) on every single invocation. So the fix was real and verified
     but got silently discarded before the very next run ever started, twice. Found this by
     tracing the Makefile rather than guessing a 5th time. Real fix now lives in the correct file,
     committed cleanly as `49ea6b42` (15-line diff, no unrelated drift since this file -- unlike
     its clone counterpart -- is fully owned by this branch).

     Flagging in case this same wrong-file trap is worth a note in the architecture doc's Stage-A
     section or the campaign runbook -- the embedded clone's scenario copy looking identical to
     the real source but being silently clobbered on every run is not obvious, and it cost real
     cluster time twice.

  **Stage A cell status (3 of 7 done, all clean):**
  - `m-sat-dwell-warmup` -- commit `1d6ba2c4` (after the 4 failed attempts above)
  - `m-ta-dwell-warmup` -- commit `73ceb160`
  - `m-satta-dwell-warmup` -- commit `4b67109a`
  - Dwell-warmup trio fully closed. All three: 96Gi confirmed rendered, harness pod `Completed`
    (no OOM), full analyzer-result coverage in `wva_target_timeseries.json`.

  **Running now:** `m-sat-calibration-probe-warmup` (cell 4). Calibration-probe's warmup is
  smaller (20rps×270s = 5,400 extra requests vs dwell's 7,020) so whether it also needed the 96Gi
  bump was an open question -- it inherits the fix automatically now (shared scenario file), so
  this run's outcome answers that question either way.

  **Remaining:** cells 5-6 (`m-ta-calibration-probe-warmup`, `m-satta-calibration-probe-warmup`),
  then cell 7 (`m-ta-calibration-probe-p4-warmup`, needs `--parallelism 4` passed manually, not
  wired into `run_cell.sh`).

  Continuing autonomously per Dean's "I permit the cluster run" authorization. Will send the
  Stage A completion handoff once all 7 cells are resolved (or flag sooner if something else
  needs planner input).

  Full blow-by-blow trace (including the two wrong-file mistakes) is in
  `session/status/benchmark.md` §20.46-20.53.
