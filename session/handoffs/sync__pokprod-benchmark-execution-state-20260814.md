from: plan (pokprod/benchmark-execution scope)
to: sync
session: pokprod-benchmark-execution

## Ref

Full state lives in `planning/ta-pokprod-open-scenarios.md`'s checklist table (§"what still
needs Dean, at a glance") and `planning/ta-pokprod-history.md` (D-1 through D-53, append-only
ledger). This handoff is the pointer + resume prose CURRENT.md needs; it doesn't restate the
detail.

## Resume prose

The pokprod TA benchmark campaign has run 21 experiments across 6 workload shapes; the workload×
config coverage matrix is closed (every workload has every config its own design calls for).
Current authoritative results doc is `planning/ta-pokprod-campaign-report.md` (leads with
cross-cutting conclusions, not narrative — replaces the two older results docs, both marked
superseded with pointer headers). All 19 affected runs now have real, version-stamped viz panels,
linked directly from the report.

**Two items genuinely open, unrouted, actionable by a next session:**
1. **Move `ta-pokprod-campaign-report.md` to `benchmark/docs/benchmark-reports/`** — Dean decided
   this in conversation 2026-08-14 (D-53); a handoff already exists
   (`benchmark__relocate-campaign-report-to-docs.md`, currently `.WIP` — the benchmark coder has
   it) so this is in flight, not stalled.
2. **Doc-coverage cleanup for 5 more undocumented scratch tools** (`verify_decision_rule.py`,
   `server_token_truth.py`, `stage_table.py`, `stage_vs_replicas.py`, `watch_pvc_space.sh`) —
   flagged (D-51), not yet scoped. Dean asked for a draft cleanup plan; not started as of this
   handoff.

**Deliberately deferred, not forgotten (Dean's explicit calls, not urgent):**
- Pokprod runbook fold-vs-stub decision (execution plan §7.1 T6).
- Dwell-forecast Type-1 design (the queue-load-forecast mechanism shared by saturation and TA) —
  scoped for "later," not now; critical path is tooling/runs.
- Controller-restart hold-at-current-replicas policy question (D-46) — mechanism found, is
  "hold" the right policy for a sustained window is Dean's call, not urgent.
- Bucket-keyed `prc` collapse bug — lower priority, WVA issue later.
- Controlled-run/timestamped-replay capability — real community work exists, catch up eventually,
  not now.

**No armed footguns.** GPUs freed, no cluster action pending, no uncommitted state on this
scope's side (verified via `git status` before writing this handoff).

## Handoff hygiene note, since it's relevant to trust in this handoff

A live self-audit this session (Dean's instruction, prompted by "did you mess up the handoff
signals for others") found my own state was clean — no mishandled routing, no self-marked-DONE
violations — but did find 3 real gaps in doc content (two pieces of detail dropped during a
report rewrite, one genuinely un-recorded decision) and one stale claim (a report banner saying
viz output didn't exist after it had already landed). All fixed and committed
(D-52, D-53). Mentioning this so a resuming session knows this scope's docs were just verified,
not merely assumed current.
