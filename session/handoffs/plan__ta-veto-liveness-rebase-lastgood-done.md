from: ta-veto-liveness
session: rebase-lastgood-55e24be9

## What changed
All four TA 0.9 branches re-rebased via `git rebase --onto 55e24be9 aa86a2a9`
(one worktree at a time via `EnterWorktree`), moving them off the broken
`aa86a2a9` onto the last-known-compiling upstream commit `55e24be9` (#1469).
All four rebased clean — zero conflicts, exactly as predicted (`#1334`'s only
change, `modeLabelForAnalyzer` in `engine.go`, is a region none of the four
branches touch).

All gates are now runnable and **all green** on all four branches:

| Branch | New tip | Base | make test | gofmt | make lint | go build | DCO |
|---|---|---|---|---|---|---|---|
| ta-devguide-fixes (A) | `93742a52` | `55e24be9` | PASS | clean | 0 issues | clean | 4/4 |
| ta-registration-safety (A') | `89337622` | `55e24be9` | PASS | clean | 0 issues | clean | 5/5 |
| ta-model-level-demand (C) | `68681542` | `55e24be9` | PASS | clean | 0 issues | clean | 4/4 |
| ta-veto-liveness (D) | `faab066a` | `55e24be9` | PASS (+`-race` on pipeline/saturation) | clean | 0 issues | clean | 6/6 |

C's two reworded commit subjects (from the prior rebase round) carried through
unchanged — confirmed by inspection, not just by trust in the mechanical
`--onto` replay.

Base confirmed via `git rev-parse 55e24be9` == the commit directly below each
branch's own commits in `git log 55e24be9..HEAD --oneline` (all four show only
their own commits, nothing from `aa86a2a9`).

## Do NOT push
Not pushed, per coder rules — these are force-pushes; Dean runs them.

## Update CURRENT.md
- Bump each of the four branches' PR-Status-table tip SHA to the new tips above
  (superseding the `aa86a2a9`-based tips from the prior rebase round's handoff).
- The prior round's "upstream/main build break" note can be marked resolved-by-
  workaround: all four branches now build/test/lint green by basing on
  `55e24be9` instead of waiting for upstream PR #1477 (which fixes `aa86a2a9`'s
  `interfaces.`/`domain` regression but is not yet merged). Worth a one-line
  note that these branches are one upstream commit behind tip pending #1477.

## Not done
- No push (Dean's call).
- PR #1477 (upstream fix for the `aa86a2a9` build break) not tracked further by
  this session — these branches simply route around it via the `55e24be9` base.

## Open questions / follow-ups
- Once #1477 merges upstream, these four branches will want a further rebase
  onto the fixed tip (same mechanical `--onto` pattern) before or after PRs open
  — Dean's call on timing (before push now vs. after, as a routine follow-up).
