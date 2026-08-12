to: benchmark
reason: re-read plan
refs:
  - planning/ta-pokprod-campaign-20260810-results.md — the 7-cell matrix table (§ "The matrix"), and
    § "Per-request data — disposition and discovery plan" for why per-request collection is disabled
    going forward (do NOT re-enable it — see below)
  - planning/ta-pokprod-open-scenarios.md — the checklist at the top for what's still open, and §5
    (cold-resume state, 6 preconditions) for the dwell-run-specific setup
  - planning/ta-pokprod-history.md [[D-9]], [[D-27]] (bearer-token hazard — rotate/verify before any
    new run leaves fresh `environment/context.ctx` files on disk), [[D-38]], [[D-39]] (the
    postprocess.py fix — now supports both harness formats, verified; no action needed but a rerun is
    the first live exercise of it at scale), [[D-40]] (an unrouted, unresolved controller-restart
    incident — if a rerun exhibits stuck replicas with rc=0/util=0 and no load, that's this bug
    recurring, not a new one; capture and report, don't debug live)
note: |
  Dean wants all six workload profiles rerun — panels have real, known gaps:

  - `m-ta-dwell`: truncated ~10 of a planned 40 min (campaign stopped early) — ITL fit r²=0.11, not
    usable. Needs a clean full-length rerun.
  - `m-satta-dwell`, `m-sat-dwell`, `m-ta-dwell` (all three dwell cells): per-request data is 0 bytes
    in every one — the campaign doc's own finding is this is very likely the per-request collector
    OOMing against the harness pod's memory limit at this workload's token volume, not a bug to fix
    live. Per-stage summaries (rate/latency/failure/token-throughput) are real and usable even when
    per-request is empty — that's a known, accepted limitation, not something to chase.
  - `ta_calibration_probe.yaml.in` (the calibration-probe cell): per a separate 2026-08-12 incident,
    has never produced usable data at all (run was orphaned/killed by a session interruption last
    time) — needs a first clean run, not just a rerun.
  - `ta_prefill_knee.yaml.in`: exists, referenced as an ITL-knee probe, but no completed run/panel set
    has been confirmed for it in the matrix — worth confirming its status before assuming a gap.

  Per Dean's own decision, do NOT re-enable per-request collection to fill the per-request gap —
  that's explicitly disabled going forward (unreliable, disk-heavy, per-packet not per-request). Rely
  on per-stage summaries for those three cells; per-request stays a known, accepted gap unless a
  fallback signal (the EPP-scorer-log discovery task, still open, unrouted) changes that later.

  Image under test: confirm which `WVA_IMAGE_TAG` is current before running — `ta-0.9-anchor-pr2-20260809`
  per the most recent record, but re-verify against the `.env` in the worktree rather than trust this
  note, since it may have moved. A tag change can shift the analyzer log format and re-break the
  extractor the same way it did before ([[D-29]], [[D-36]]) — the fix is loud-not-silent now, but still
  worth a short run → confirm fields populate → then the long run, per [[D-36]]'s standing
  recommendation, especially for any cell not yet run against the current image.

  Standard preconditions apply: un-pause the ScaledObject first (§5 precondition 5), restart the
  controller before each run (precondition 4, prevents cross-run capacity-history contamination —
  [[D-32]]-era finding, still the adopted protocol), save the raw controller log during each run
  (precondition 6, [[D-31]]), run `post_run_analyze.sh` promptly after each one.
