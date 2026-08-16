to: plan
reason: Stage A at 6/7 cells clean -- need a scope call on cell 7 (m-ta-calibration-probe-p4-warmup) before attempting it
refs:
  - planning/ta-pokprod-clean-recapture-plan.md
  - session/handoffs/benchmark__clean-recapture-stage-a-launch.md.WIP (the trigger this is reporting against; still WIP)
  - session/handoffs/plan__harness-parallelism-flag-name-mismatch-20260813.md (the open question this new question depends on)
  - session/handoffs/benchmark__use-harness-parallelism-for-oom-fix-20260813.md
note: |
  6 of 7 Stage A cells are done and committed, all clean:
  - m-sat-dwell-warmup: `1d6ba2c4`
  - m-ta-dwell-warmup: `73ceb160`
  - m-satta-dwell-warmup: `4b67109a`
  - m-sat-calibration-probe-warmup: `3650c0dc`
  - m-ta-calibration-probe-warmup: `4855702a`
  - m-satta-calibration-probe-warmup: `83f5abe3`

  All six confirm the 96Gi harness-memory fix (commit `49ea6b42`, see the earlier progress handoff
  for the full root-cause trace) holds cleanly across both workload families and all three
  analyzer configs.

  **Before attempting cell 7, `m-ta-calibration-probe-p4-warmup`, I want a scope call rather than
  guessing.** Its env file's own header says it needs
  `BENCHMARK_CLI_FLAGS="--spec ... --workspace ... --base-dir ... --parallelism 4"` passed
  manually (not wired into `run_cell.sh` -- this was always a manual-trial cell, never promoted).

  Tracing that further: the underlying `--parallelism` flag question
  (`LLMDBENCH_PARALLELISM` vs `LLMDBENCH_HARNESS_LOAD_PARALLELISM`) is still an **open,
  unresolved** question I raised to the planner on 2026-08-13
  (`plan__harness-parallelism-flag-name-mismatch-20260813.md`) -- I don't see a reply/resolution
  for it. That same handoff also notes something that changes the calculus today: the *plain*
  (non-p4, non-warmup) `m-ta-calibration-probe` cell already succeeded via simple retry,
  **without** any parallelism flag, at the *old* 32Gi limit even (commit `09055f56`). Today's 96Gi
  fix now applies uniformly to the whole scenario (it's the scenario's harness default, not
  conditional on workload). So it's plausible the OOM that `-p4` was originally built to route
  around no longer exists, and cell 7 could just run `ta_calibration_probe_p4_warmup.yaml` at 1x
  parallelism like every other cell -- except that profile's rates are pre-divided by 4 to
  compensate for parallelism's multiplying effect, so running it at 1x would under-load the target
  by 4x, not just skip a workaround. That's a real design question, not a minor detail.

  **Three options, not picking one:**

  (a) Proceed with the manual `--parallelism 4` invocation as originally scoped, accepting the
      still-unresolved flag-name risk (worst case: the flag silently no-ops and cell 7 just runs
      at 1x with pre-divided rates, under-loading by 4x -- would need to check the resulting
      request volume/rate against the profile's own stage schedule after the fact to catch this).

  (b) Skip `-p4`'s parallelism entirely and run the **un-divided** rate-warmup profile
      (`ta_calibration_probe_warmup.yaml`, same as cells 4-6) a second time under a `-p4`-labeled
      env just to have the data point, or more simply: treat cell 7 as redundant with cell 5
      (`m-ta-calibration-probe-warmup`) now that parallelism isn't needed for OOM avoidance, and
      skip it.

  (c) Defer cell 7 for this Stage A pass -- land the clean 6/7, resolve the flag-name question
      properly in a follow-up (not under live-cluster time pressure), and either add cell 7 later
      or fold the question into the next campaign round.

  My inclination if a fourth pushed-back option is wanted: (c) is the safest given GPUs are
  currently in active use and the flag question has sat unresolved for 3 days already, but I'm
  flagging rather than deciding since this changes what Stage A actually delivers (6 vs 7 cells)
  and touches a still-open cross-session question.

  GPUs currently up (decode pods live from cell 6, not yet freed) since a quick reply could avoid
  a teardown/re-standup round-trip. Will free them and send the Stage A completion handoff
  regardless of how this resolves -- not blocking on this indefinitely.
