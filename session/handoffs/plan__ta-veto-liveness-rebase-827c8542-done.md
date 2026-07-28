from: ta-veto-liveness
session: rebase-827c8542-conflict

## What changed
A′, C, D rebased from `ef28744b` onto `827c8542` per
`planning/ta-09-rebase-827c8542.md`. **A (`ta-devguide-fixes`) was not touched**
— it's merged, per the handoff and plan.

| Br | Branch | PR | New tip | Result |
|----|--------|----|---------|--------|
| A′ | ta-registration-safety | #1479 | `b706228d` | clean rebase |
| C  | ta-model-level-demand  | #1480 | `7aec2645` | clean rebase; rebuild-critical case verified |
| D  | ta-veto-liveness       | #1481 | `19c9a122` | **1 real conflict, resolved** (see below) |

All three now green on every gate:

| Br | make test | gofmt | make lint | go build | -race | DCO |
|----|---|---|---|---|---|---|
| A′ | PASS | clean | 0 issues | clean | — | 5/5 |
| C  | PASS | clean | 0 issues | clean | — | 4/4 |
| D  | PASS | clean | 0 issues | clean | PASS (pipeline+saturation) | 6/6 |

## Verification detail (per-file diff inventory, not just trusting a clean rebase)
- A′: `throughput-analyzer.md`, `engine.go`, `engine_v2.go`, `cmd/main.go` — all
  four byte-identical diffs before/after.
- C: 12 touched files — 10 byte-identical; `throughput-analyzer.md` and
  `engine.go` had hunk-header line-number shifts only (from #1478/#1452 landing
  nearby), every hunk body identical. Explicitly re-ran the throughput package
  (weighted-avgOL regression test included) — clean. `go build`/`make test`
  confirmed green against #1452's `engine.go` (the flagged rebuild-critical
  case — textually-clean merges can still break the build; this one didn't).
- D: see conflict resolution below, plus 10 other touched files all
  byte-identical.

## D's conflict — `internal/engines/pipeline/analyzer_helpers.go`
Investigated first (as the plan directed) before touching the worktree:
`git log ef28744b..827c8542 -- analyzer_helpers.go` shows #1452 is the only
commit touching this file, and `git show 31fd0f84 -- analyzer_helpers.go` shows
its *entire* change to this file is the `maps`/`slices` imports + the `rolesOf`
helper, inserted at the same top-of-file location as D's own insertion
(`analyzerReasonNoData`/`analyzerReasonError` consts + `ResultIsInformative`).
**#1452 never touches `needsScaleDownForRole`, `safeRemovalReplicasForRole`, or
`applyDeallocationForRole`** — confirmed by that same `git show`, which is the
complete patch for the file (nothing else in it).

Conflict resolution: kept both insertions side by side (`rolesOf` first,
matching #1452/base order, then D's consts + `ResultIsInformative`). Continued
the rebase; the remaining 5 commits (which carry the actual Live-gating edits
to the three functions) applied with **zero further conflicts** — consistent
with the pre-check above, since those functions were untouched by #1452.

**No semantic decision was forced.** Confirmed by diffing our branch's net
change against the new base (`git diff 827c8542 HEAD -- analyzer_helpers.go`):
it is exactly D's original diff (Live field checks, safety floor, comments),
layered on top of #1452's `rolesOf` as unchanged context — nothing added,
dropped, or altered to make the merge work. Both `rolesOf` and D's liveness
gate are present and independently correct.

**RC-2 cross-check (from `planning/PR1452-review.md`):** that review flagged
#1452's reclaim path as bypassing the multi-analyzer scale-down gate. Checked
whether the merge changes this: `grep -n
"needsScaleDownForRole\|safeRemovalReplicasForRole\|applyDeallocationForRole"
internal/engines/pipeline/rescale.go` returns nothing — #1452's reclaim path
still doesn't call any of D's gated functions, exactly as before the rebase.
**This is the same pre-existing RC-2 gap, not newly introduced or newly fixed
by this merge** — flagging per the plan's "flag, don't fold" instruction, even
though nothing needed folding.

## Do NOT push
Not pushed. Dean force-pushes A′/C/D with `--force-with-lease` after per-branch
PR confirmation, per the plan.

## Update CURRENT.md
- Bump A′/C/D tips to `b706228d` / `7aec2645` / `19c9a122`.
- A (#1478) is MERGED — reflect that if not already.
- The prior tip-amend on D (`1df0f871`) is superseded by this rebase, per the
  plan ("the tip-amend on D is now moot").

## Not done
- No push, no PR-body edits, per plan's "Out of scope for the coder."
- Did not delete `planning/ta-09-rebase-827c8542.md` or the superseded
  `ta-09-rebase-ef28744b.md` — plan says delete once verified *and*
  force-pushed; force-push hasn't happened yet.

## Open questions / follow-ups
- None from this rebase itself. The RC-2 gap above is pre-existing and already
  tracked in `PR1452-review.md` — not a new follow-up, just confirmed unchanged.
