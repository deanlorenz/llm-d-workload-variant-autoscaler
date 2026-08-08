# sync__ — CURRENT.md update request: benchmark dwell run executed

to: sync
from: ta-benchmark coder+runner (worktree `benchmark`)
date: 2026-08-08
request: **update CURRENT.md's benchmark task section only** — do not touch sibling task sections

---

## What changed

The dwell run that CURRENT.md records as **staged and unlaunched** has been **launched, run to
completion, and analysed**. Dean approved the launch ("run"). That is the one fact in CURRENT.md
that is now false and needs correcting.

## Proposed replacement text for the benchmark task's state line

> **Dwell run `dean-20260808-051912-230` EXECUTED 2026-08-08** (Dean-approved). It did **not**
> produce the intended dwell in kv 0.3–0.85 — the system **limit-cycles** with a ~9 min period
> (replica target `1→4→7→10→…→1→2→6→9→10→…→2→9`, two full cycles then floor). The run identified a
> specific mechanism from the controller's own 33-tick decision trace: per-replica capacity `prc` is
> read from a rolling-average history **keyed on a discretised output-length bucket**, and both
> excursions to `maxReplicas` are `prc` collapsing 10–13× rather than real demand — at the second
> peak `util` rose 3.1× while demand was *falling*. Also found: dispatch rate missing for **100%** of
> ticks (`pod`/`pod_name` label mismatch), demand is backlog-shaped not rate-shaped (**2 rps offered
> → 9 replicas provisioned** at 02:40), the two analyzers contradicting each other outright at
> 02:41, and capacity history **contaminated across runs** (controller up 6 h, in-process history,
> never invalidated). Full findings + 5 prioritised asks sent to the planner as
> `plan__benchmark-dwell-run-findings.md`; this **supersedes** the rate-invariance hypothesis in the
> earlier `plan__benchmark-dwell-operating-point.md`. Cold-resume record is
> `benchmark/session-notes/status/benchmark.md` **§18** (§17.12 is now historical). GPUs released
> after the run per Dean's standing rule. **Nothing pushed** — `benchmark` is 11 ahead of
> `origin/benchmark`, fork `wva-ta-benchmark` 1 ahead, both awaiting Dean's explicit per-push
> confirmation.

## Pointers that should survive into CURRENT.md

- Authoritative resume handle is unchanged: `benchmark/session-notes/status/benchmark.md`
  (committed). **The live section is now §18, not §17.12.**
- `session-notes/scratch/controller-decisions-20260808-dwell.log` is the irreplaceable artifact of
  this run (the 08-07 ladder lost its equivalent to log rotation).

## Explicitly not asking for

No changes to any other task's section, and no push. This handoff requests a CURRENT.md edit and
nothing else.
