from: ta-veto-liveness
session: forward-rebase-ef28744b

## What changed
All four TA 0.9 branches forward-rebased from `55e24be9` onto `ef28744b`
(`git rebase --onto ef28744b 55e24be9`), one worktree at a time via
`EnterWorktree`, per `planning/ta-09-rebase-ef28744b.md`. All four rebased
clean — zero conflicts, matching the plan's `merge-tree` pre-check.

New tips (all now green on every gate):

| Br | Branch | PR | New tip | Base | make test | gofmt | make lint | go build | -race | DCO |
|----|--------|----|---------|------|---|---|---|---|---|---|
| A  | ta-devguide-fixes      | #1478 | `1aa099d0` | `ef28744b` | PASS | clean | 0 issues | clean | n/a (docs-only) | 4/4 |
| A′ | ta-registration-safety | #1479 | `2f07ca43` | `ef28744b` | PASS | clean | 0 issues | clean | — | 5/5 |
| C  | ta-model-level-demand  | #1480 | `60b93643` | `ef28744b` | PASS | clean | 0 issues | clean | — | 4/4 |
| D  | ta-veto-liveness       | #1481 | `832baa08` | `ef28744b` | PASS | clean | 0 issues | clean | PASS (pipeline+saturation) | 6/6 |

## Verification checklist — done per the plan, not just trusted from "Successfully rebased"
For each branch (all four, not just C/D), ran the plan's per-file diff inventory:
`git diff <pre-rebase-tip> HEAD -- <file>` vs. `git diff ef28744b <old-base> -- <file>`
compared with blob-index lines stripped, for every file the branch's commits
touch (not just the two the plan named as "expected to interact with the new
base"). Result: **zero dropped or altered hunks on any branch.**
- A: skipped per plan (docs-only).
- A′: `engine.go`, `engine_v2.go`, `cmd/main.go` — all three byte-identical
  diffs before/after (not even a line-number shift).
- C: 12 touched files — 11 byte-identical, `engine.go` line-number-shifted only
  (hunk headers moved ~15 lines; content of every hunk identical) — confirms
  #1470/#1483's own `engine.go` changes landed near but not inside our hunks.
  Also explicitly re-ran the throughput package's weighted-avgOL regression
  test by name (153/153 specs pass).
- D: 11 touched files — all byte-identical, including `engine.go` and
  `engine_v2.go` despite both being touched by #1470/#1483 on the new base.
  Explicitly re-ran the discriminating per-model-keying test
  (`engine_v2_liveness_test.go`) and the QM-always-live scale-down test
  (`engine_queueing_model_test.go`) as part of the full `-race` run on
  `internal/engines/saturation` and `internal/engines/pipeline` — both pass.

## Do NOT push
Not pushed, per coder rules and the plan — these are force-pushes; Dean runs
them with `--force-with-lease` after per-branch PR confirmation.

## Update CURRENT.md
- Bump each of the four branches' PR-Status-table tip SHA to the new tips above
  (superseding the `55e24be9`-based tips from the prior handoff).
- The stale "#1477 / CI red" caveat noted in the PR-Status rows and (per Dean)
  in the four PR bodies is now fully resolved — main compiles at `ef28744b`
  (fix merged as #1483; #1477 closed as superseded) and these branches are
  rebased onto it directly, not routing around it via `55e24be9` anymore.

## Not done (per plan's "Out of scope for the coder")
- No push.
- No PR-body edits (dropping the stale CI caveat) — planner/Dean territory.
- Did not delete `planning/ta-09-rebase-ef28744b.md` — plan says delete "once
  all four rebases are verified and force-pushed"; force-push hasn't happened
  yet.

## Open questions / follow-ups
- None — plan's verification checklist fully satisfied on all four branches.
