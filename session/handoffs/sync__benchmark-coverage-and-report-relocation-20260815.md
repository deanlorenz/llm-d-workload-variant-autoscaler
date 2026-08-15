from: benchmark
to: sync
session: benchmark

## What changed

Session spanned two arcs, both now parked cleanly. Full detail in
`session/status/benchmark.md` §20.34-39 — this is a pointer, not a restatement.

**Coverage-matrix gap-fill (§20.34-36).** 4 runs approved by Dean 2026-08-14 closed the last gap
in the workload×analyzer-config grid: `ta_prefill_knee` and `ta_calibration_probe` now each have
all 3 configs (TA-only, sat, satTA). Headline finding: analyzer informativeness depends on
workload shape, not a general ranking — satTA wins clearly on calibration-probe (~3.5x better P99
TTFT than sat-only) but TA-only wins on prefill-knee (satTA no better than sat-only there). One
recurring OOM on `m-sat-calibration-probe`, resolved both times by an unmodified retry, not by
switching to the p4/parallelism variant, per an explicit constraint in the coverage doc. Also
pulled up 18 runs' `viz/` output that a sibling coder had written one directory level too deep to
be git-trackable — fixed via pull-up (matching an existing precedent), not a gitignore change.

**Doc relocation (§20.39).** Dean-decided (D-53): moved `ta-pokprod-campaign-report.md` from
`plans/planning/` to `benchmark/docs/benchmark-reports/` — it's Type-6/PR-bound guide material, not
internal tracking. Fixed all 28 run-directory links (now same-worktree, resolve on GitHub/clone)
and turned companion-doc cross-references into plain-text pointers (those docs stay on `plans`, a
different repo/branch). Left a superseded-pointer stub at the old path so existing citations still
resolve. Also fixed a real staleness bug while moving it: three staircase-cell TTFT/ITL values had
been sitting as "pending re-postprocess" after the fix already landed — filled in the real numbers.

**Two harness process gaps found, flagged not fixed** (not this round's scope to patch):
`reset_run.py`'s reset step never actually unpauses a paused ScaledObject (prints the command,
doesn't run it); `run_cell.sh`'s failure path can fall through and silently overwrite an
already-committed different run's config files when a run fails before producing a results
directory. Both documented in the campaign report and `ta-pokprod-history.md`.

**Process note, self-reported:** caught and fixed a real handoff-protocol violation on my own part
mid-session — briefly marked my own outgoing reply handoff `.DONE` (only the recipient should).
Fixed immediately, captured as a feedback memory outside this repo.

Commits, most recent first: `4454865b`, `196045bc`, `d0ea3840`, `1db6e216`, `d682c82d`, `7fb3f124`,
`bd82645b`, `07988f6b`, `d3c7d5d8` — all local, DCO-signed, none pushed this session.

**GPUs freed and verified quiescent** (ScaledObject paused at 0, decode at 0 replicas, 0 pods in
`dhl-wva-209`). Worktree exited cleanly (`keep`), working tree clean, no uncommitted changes.

## Update CURRENT.md

Fold into the benchmark abstract: coverage-matrix gap now fully closed (all 6 canonical workloads
have every config their design intends); campaign report relocated to
`benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md` (update any CURRENT.md pointer
that still names the old `plans/planning/` path); two open harness-tooling gaps worth a planner's
attention if not already tracked (see §20.34/20.39 for exact mechanism).

## Open questions / follow-ups

None blocking. The two flagged harness process gaps and the dwell limit-cycle mechanism remain
open design questions, already tracked in `ta-pokprod-history.md`/`ta-pokprod-workload-
coverage.md` — not new asks from this handoff.
