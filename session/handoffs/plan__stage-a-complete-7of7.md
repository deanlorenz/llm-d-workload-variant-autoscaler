to: plan
reason: Stage A clean-recapture campaign COMPLETE -- all 7 cells landed, GPUs freed
refs:
  - planning/ta-pokprod-clean-recapture-plan.md
  - session/handoffs/benchmark__clean-recapture-stage-a-launch.md.WIP (closing out, marking .DONE)
  - session/handoffs/benchmark__cell7-proceed-verify-after.md.WIP (closing out, marking .DONE)
  - session/handoffs/plan__stage-a-progress-3of7-and-harness-oom-fix.md (earlier progress checkpoint)
  - session/handoffs/plan__stage-a-6of7-cell7-p4-scope-question.md (cell 7 scope question, resolved)
note: |
  All 7 Stage A cells are landed, committed, and verified. GPUs freed (ScaledObject paused at 0,
  decode scaled to 0, confirmed 0 pods running). Marking both inbound handoffs .DONE with this
  reply.

  **Final commit list (all DCO-signed, on `benchmark` branch):**
  - `m-sat-dwell-warmup` — `1d6ba2c4` (after 4 failed attempts — see the misdiagnosis trail below)
  - `m-ta-dwell-warmup` — `73ceb160`
  - `m-satta-dwell-warmup` — `4b67109a`
  - `m-sat-calibration-probe-warmup` — `3650c0dc`
  - `m-ta-calibration-probe-warmup` — `4855702a`
  - `m-satta-calibration-probe-warmup` — `83f5abe3`
  - `m-ta-calibration-probe-p4-warmup` — `590e8b91`

  Plus underlying fixes: log-capture wiring / D-63 (`28f1ed3` on the embedded llm-d-benchmark
  clone), 3 new warmup-stage profile files (`eb20ef53`), 7 new env files (`e1b65272`), and the
  harness-memory root cause fix (`49ea6b42` on the real scenario source file).

  **What was found and fixed along the way (already reported at the 3/7 checkpoint, repeating
  briefly for completeness):** the dwell-warmup workload's extra request volume pushed the
  harness pod's own baseline memory footprint past the scenario's 32Gi default; the real
  requirement (96Gi) was documented in `ta_autoscale_dwell.yaml.in`'s own docstring for months but
  never wired into the scenario. Two of the four failed attempts were my own mistake (fixed the
  override in the embedded clone's copy of the scenario file, which `make benchmark-run` silently
  overwrites from the real source on every invocation) rather than the same bug recurring. Real
  fix landed on the actual source file, holds cleanly across all remaining cells (calibration-probe
  didn't strictly need it but inherits it harmlessly).

  **Cell 7 (`m-ta-calibration-probe-p4-warmup`) — resolved per Dean's direct reply, verified
  thoroughly:** Dean picked option (a) from the scope question (proceed with the manual
  `--parallelism 4` invocation) and asked for explicit verification that the flag produced real 4x
  fan-out rather than a silent no-op. Confirmed with actual numbers, not just pod count:
  `results/cross-treatment-comparison/treatment_comparison.csv` shows all 4 parallel leaves with
  IDENTICAL per-stage request counts and rate_qps values matching the profile's pre-divided-by-4
  schedule exactly — 3,127 requests per leaf, 12,508 total across all 4. A no-op would show one
  leaf carrying the full load and three empty; this is the opposite. Also confirmed via
  `llmdbenchmark`'s own log ("Running 1 treatment(s) x 4 parallel pod(s)", parallel=1/4..4/4, "All
  pods completed successfully"). First attempt was caught and aborted before touching the cluster
  (wrong workload profile inherited from bypassing `make benchmark-run`'s own substitution step);
  the working retry used a one-off wrapper script overriding the Makefile's `LLMDBENCHMARK`
  variable to inject `-j 4` — deleted after use, never committed, doesn't affect any other cell.

  **Mid-campaign note:** answered a live oc-context-switch safety question (`benchmark__oc-context-
  switch-safety-check.md`, already replied to and closed separately) — found my own planned
  verification/teardown commands had a real (not hypothetical) exposure to a shared-kubeconfig
  context switch, and pinned `--context` explicitly on all cluster calls for the rest of this
  wrap-up rather than relying on current-context.

  Full blow-by-blow trace including every root-cause investigation is in
  `session/status/benchmark.md` §20.46-20.59. Standing by for the next assignment.
