to: plan
reason: closing out a 3-day-old open question (plan__harness-parallelism-flag-name-mismatch-20260813.md) -- resolved as a side effect of today's Stage A cell 7
refs:
  - session/handoffs/plan__harness-parallelism-flag-name-mismatch-20260813.md (the old ask this answers)
  - session/handoffs/plan__stage-a-complete-7of7.md (where the answer was actually found, in passing)
note: |
  This is an old ask, from 2026-08-13, not something new. Flagging that explicitly since it's easy
  to mistake for a fresh question if read out of order.

  The original handoff asked whether `LLMDBENCH_PARALLELISM` and `LLMDBENCH_HARNESS_LOAD_PARALLELISM`
  were the same flag under two names, or a genuine mismatch -- unresolved for 3 days, blocking
  nothing at the time (the fallback ladder had already produced a completed run), so it sat.

  **Resolved today, incidentally, while building Stage A cell 7** (`m-ta-calibration-probe-p4-warmup`,
  a manual `--parallelism 4` trial -- see `plan__stage-a-complete-7of7.md` for that cell's full
  writeup). Needed to actually invoke the flag for real this time, so checked directly rather than
  trusting the 2026-08-13 code-reading alone:

  - `llmdbenchmark run --help` shows `-j PARALLELISM, --parallelism PARALLELISM` as a real, live
    flag on the `run` subcommand.
  - `cli.py:822`: `harness_parallelism=int(getattr(args, "parallelism", 1) or 1)` -- confirms
    `--parallelism`/`-j` is what actually reaches `context.harness_parallelism`, which
    `step_07_deploy_harness.py` uses to spawn N pods.
  - Used it live: passed `-j 4` (via a one-off wrapper overriding the Makefile's `LLMDBENCHMARK`
    variable, since the recipe has no extra-args slot), got 4 real harness pods, each with
    identical per-stage request counts confirmed via
    `results/cross-treatment-comparison/treatment_comparison.csv` (12,508 total requests, 3,127 per
    leaf, matching the profile's own pre-divided-by-4 rate schedule exactly). Not a no-op.

  So: **no mismatch. `LLMDBENCH_PARALLELISM` → `--parallelism`/`-j` is the correct, working flag,**
  confirmed by both static code reading and a real cluster run today, not just the earlier
  code-only pass. `LLMDBENCH_HARNESS_LOAD_PARALLELISM` remains a separate, report-layer-only value
  (read out of already-run metadata in `native_to_br0_1.py`/`native_to_br0_2.py`) — a different
  thing with a similar name, not the same value under two names, and not the flag that controls
  spawning.

  No further action needed on the original ask. Not proposing any new wiring into `run_cell.sh` or
  a `.env` convention for this — cell 7 used a one-off wrapper deliberately, per Dean's own
  direct scope call on whether to invest in that (see `plan__stage-a-6of7-cell7-p4-scope-question.md`
  and its reply) -- if a future cell wants `--parallelism` as a first-class, wired-in option, that's
  a separate ask, not implied by this closing note.
