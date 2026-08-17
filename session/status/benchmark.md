# Status — `benchmark` branch (ta-benchmark coder/runner)

```
name: ta-benchmark coder/runner
id: (set by the coder session on next start)
role: coder
branch: benchmark
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark
owned_doc: planning/ta-pokprod-clean-recapture-plan.md (current campaign) — mission entry point is planning/ta-pokprod-roadmap.md
task: IDLE — Stage A closed 7/7, standing by for the next assignment
status_file: plans/session/status/benchmark.md
```

```
last_update: 2026-08-17 (compressed by the benchmark planner; last coder write 2026-08-17 §20.62)
state: idle
current_step: none — awaiting assignment
blocked_on: n/a
recent_commits:
  - 590e8b91 benchmark: land m-ta-calibration-probe-p4-warmup Stage A -- closes Stage A at 7/7, real 4x parallelism confirmed
  - 83f5abe3 benchmark: land m-satta-calibration-probe-warmup Stage A -- clean success
  - 4855702a benchmark: land m-ta-calibration-probe-warmup Stage A -- clean success
notes: see § Armed footguns before any run. Prior 5411-line narrative is in plans git history before the D-77 cleanup commit.
```

**Authoritative copy.** This file is the authoritative copy and the coder maintains it directly
(Dean's direction 2026-08-09). The coder edits an untracked scratch copy at
`benchmark/session-notes/local/benchmark.md` and `cp`s it here on save, because worktree isolation
blocks `Write`/`Edit` on the shared-checkout path while Bash `cp`/`mv` reach it. The coder has **no
git write access to `plans/`** — file-sync only; the planner commits this file.

**Compressed 2026-08-17 by the benchmark planner** ([[D-77]]). It was 5411 lines of 62 chronological
session-log sections. Every landed round's substance now lives in the decision ledger
[`planning/ta-pokprod-history.md`](../../planning/ta-pokprod-history.md) (`D-1`…`D-77`, grep
`'^## D-'`) and the campaign report. Facts that had **no other home** were written to the ledger
**before** anything was deleted: `D-74` (design-C tooling inventory + the live `reset_run.py`
defect), `D-75` (branch unpushed + uncommitted viz refresh), `D-76` (two upstream defect captures).
The old § 0 "cold resume — read these four first" was **actively wrong** (it claimed freeing PVC
space and un-pausing the ScaledObject were both still undone — Stage A has since run 7/7 clean) and
is replaced by the § Cold resume below.

---

## Cold resume — read in this order

1. **Role and scope.** ta-benchmark coder/runner, confined to the `benchmark` worktree. Write scope =
   that worktree, plus `plans/session/handoffs/` and this file (via `cp`). Never `cd` to a sibling.
   Never push to the `ofer` remote (its push URL is deliberately
   `READ-ONLY-MIRROR-DO-NOT-PUSH-TO-OFER`); `origin` on the embedded clone is
   `git@github.com:deanlorenz/llm-d-benchmark.git`.
2. **Standing constraints.** No run starts without Dean's explicit approval. No `git push` without a
   per-push confirmation for that specific push. Always pass an explicit `-n dhl-wva-209`, including
   for cluster-scoped reads, and pin `--context` on every `kubectl`/`oc` call.
3. **Mission state.** [`planning/ta-pokprod-roadmap.md`](../../planning/ta-pokprod-roadmap.md) —
   start there; then [`ta-pokprod-open-scenarios.md`](../../planning/ta-pokprod-open-scenarios.md)
   § Priority triage for what is open and who owns it.
4. **§ Armed footguns below, before touching the cluster.**

## Where things stand

**Stage A of the clean-recapture campaign is CLOSED at 7/7** (2026-08-16, `D-65`–`D-69`). All seven
cells landed with real verified data; GPUs freed and confirmed quiescent. The harness-memory bug that
blocked 4 of the first 5 attempts is fixed at its actual source (96Gi, not the scenario's 32Gi
default, commit `49ea6b42`) — including the compounding trap where a fix to the embedded
`llm-d-benchmark` clone was silently overwritten by `make benchmark-run`'s own copy step on every
invocation. Cell 7's 4× parallelism is confirmed by hard numbers, not assumption.

**Stage B (the full campaign) is scoped but NOT launched** —
[`ta-pokprod-clean-recapture-plan.md`](../../planning/ta-pokprod-clean-recapture-plan.md) § Stage B,
tracked as triage item 12. Needs Dean's run approval.

**Branch state:** local tip `590e8b91`, **34 commits ahead of `origin/benchmark`, 0 behind — all
unpushed** (`D-75`). Committed work is durable; origin is a month stale. No push proposed or approved.

**Tooling:** the design-C data pipeline shipped — `harvest_run.py`, `pvc_gate.py`,
`completion_tokens_scan.py`, `reset_run.py` are all tracked under `hack/benchmark/`, and
`make benchmark-reset-run` is in the Makefile (`D-74`; the old status text calling these "not yet
committed at all" was stale). Per-request estimation is built and generalized to 18/21 run-leaves
(`D-62`, `D-64`, `D-66`).

## Armed footguns — read before any run

1. **⚠️ The ScaledObject is left PAUSED at 0.** Stage A wrap-up freed GPUs via
   `autoscaling.keda.sh/paused-replicas="0"` plus `scale --replicas=0`. KEDA holds a paused
   ScaledObject at 0 **indefinitely**, and scaling the Deployment directly does **not** override the
   pause. A run launched without first un-pausing
   (`kubectl annotate scaledobject unsloth--608e585a-instruct-decode-scaler -n dhl-wva-209
   autoscaling.keda.sh/paused-replicas- --overwrite`, then confirm `PAUSED` reads `<none>`) produces
   a flat 0-replica trace **that reads as a legitimate no-scaling result.** This is precondition 5 in
   [`ta-pokprod-open-scenarios.md`](../../planning/ta-pokprod-open-scenarios.md) § 5.
2. **⚠️ `reset_run.py` can permanently delete incomplete PVC data.** `hack/benchmark/reset_run.py:270-272`
   gates `rm -rf` on a directory **name** match (`if d in on_host`) with no size or count comparison —
   an existence check standing in for a completeness check. Live and unfixed as of 2026-08-17.
   **Always run `session-notes/scratch/verify_pvc_vs_host.py` first.** It once found all four host
   copies incomplete, where `--apply` would have made the loss permanent. Full detail + the
   deliberately-not-loosened `NOT SAFE` exception: `D-74`.
3. **⚠️ `make benchmark-run` re-copies the embedded `llm-d-benchmark` clone**, silently overwriting
   local fixes to it on every invocation. Fix the real source, not the clone (`D-68`).
4. **Restart the controller before each run** — capacity history is bucket-keyed and was found
   contaminated across runs. Adopted protocol, not a suggestion.
5. **Verify *populated* extractor output, not just a clean exit** — `dump_wva_target_timeseries.py`
   can report a plausible snapshot count with every field unpopulated on log-format drift (`D-29`;
   the drift bug itself was fixed 2026-08-10 `add1d400`, but the verify-the-output discipline stands).

## Owed by this scope

- **Commit the 83 uncommitted viz-refresh entries** on the worktree (57 modified, 10 new `viz/` dirs,
  16 `good-panels.png` symlinks) — handed over by the autoscaling-viz scope, non-blocking. The commit
  is the **planner's** to shape; the coder has no git access to `plans/` but does own the `benchmark`
  worktree's history. Triage item 13, `D-75`.
- **Two upstream defect captures written but never filed** —
  `session-notes/issues/inference-perf-output-token-inflation.md` and
  `…/llm-d-benchmark-step09-silent-truncation.md`. Filing is Dean's call, no GitHub writes. `D-76`.
- **Stale trigger `session/handoffs/benchmark__observability-plan.md`** (2026-06-15) still needs a
  keep-or-supersede call — it points at `planning/benchmark-observability-plan.md` and predates the
  entire pokprod campaign.

## Resolved, kept only as pointers

- TA reporting `variants: []` at idle — **not a regression** (H1 confirmed 2026-08-07 17:12:20Z; TA
  populated on the first cycle after load arrived).
- Saturation-disable **does** work — an earlier "still not disableable" finding was **overstated and
  corrected** by the coder itself; see `D-*` entries for the staircase row set and the correction.
- The dwell limit cycle — mechanism found (`D-21`): a real `P1-obs` sample plus created→ready replica
  lag, physical, **not** a control-loop defect. Full trace:
  [`session/status/dwell-deep-dive.md`](dwell-deep-dive.md).
- inference-perf OOM — root-caused, fixed, and validated by a real 4-pod run, 0 errors
  (`D-41`–`D-43`).
- `postprocess.py` missing-field bug — fixed 2026-08-12, supports both harness formats (`D-39`).
- Reply-routing misaddressing — root cause is a **trigger-format gap** (triggers carry no `from:`
  field), forwarded to the protocol-design owner; not a habit fix (`D-73`).
