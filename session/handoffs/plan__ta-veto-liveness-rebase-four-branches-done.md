from: ta-veto-liveness
session: rebase-four-branches

## What changed
All four TA 0.9 branches rebased onto upstream/main (`aa86a2a9`), one worktree at a
time via `EnterWorktree`. All four rebased clean — zero conflicts, matching the
handoff's `git merge-tree` prediction.

New tips:
- `ta-devguide-fixes` → `771d5ad4` (4 commits)
- `ta-registration-safety` → `3c2e77af` (5 commits)
- `ta-model-level-demand` → `45307ecc` (4 commits, 2 reworded — see below)
- `ta-veto-liveness` → `bb6ee84f` (6 commits)

DCO sign-off verified present on every commit on every branch (`git log
upstream/main..HEAD --format="%b" | grep Signed-off-by` count matches commit
count on all four: 4/4, 5/5, 4/4, 6/6).

`ta-model-level-demand` reword (done non-interactively via `git filter-branch
--msg-filter`, not `git rebase -i` — that flag is disallowed for this session):
- `throughput: weight model-level avgOL by replica count (review F1)` →
  `throughput: weight model-level avgOL by replica count`
- `docs(multi-analyzer-pipeline): add ArrivalRate to AnalyzerInput field table (review F2)` →
  `docs(multi-analyzer-pipeline): add ArrivalRate to AnalyzerInput field table`
Verified both commits' trees are byte-identical before/after (only the message
changed): `git rev-parse <old>^{tree}` == `git rev-parse <new>^{tree}` for both.

## Gates — build/test/lint SKIPPED, out of scope per Dean's direction
`go build ./...` fails on **upstream/main itself** (`aa86a2a9`), independent of
any of these branches or this rebase:

```
internal/engines/saturation/engine.go:509:7: undefined: interfaces
internal/engines/saturation/engine.go:510:10: undefined: interfaces
internal/engines/saturation/engine.go:511:7: undefined: interfaces
internal/engines/saturation/engine.go:512:10: undefined: interfaces
```

Root cause: PR #1449 (`chore: rename internal/interfaces to internal/domain`,
already an ancestor of `aa86a2a9`) missed 4 usages in `engine.go` —
`interfaces.QueueingModelAnalyzerName` / `interfaces.SaturationAnalyzerName` at
lines 509-512 still reference the old package name, but the file's import block
only imports `domain`, not `interfaces`. Confirmed pre-existing (not introduced by
any of the four branches' commits) via `git diff aa86a2a9 HEAD -- .../engine.go`
(zero diff on `ta-devguide-fixes`, whose commits are docs-only and never touch
this file) and by building an isolated detached worktree checked out directly at
`aa86a2a9` (since removed).

Per Dean's direction this turn, `make test` / `gofmt` / `make lint` / `go build`
were skipped for all four branches — out of scope for this rebase task. Only
`gofmt -l` was run (clean on all four; it doesn't need the code to compile) and
the DCO check above. **No branch's own build/test status was otherwise verified
post-rebase.**

This upstream build break is not yet tracked as an issue — flagging here for
visibility; filing it is Dean's call, not decided this turn.

## Update CURRENT.md
- Bump each of the four branches' PR-Status-table tip SHA to the new post-rebase
  tip listed above.
- Note the upstream/main pre-existing build break (undefined `interfaces` in
  `engine.go:509-512`, PR #1449 fallout) somewhere visible — e.g. a new "Blocked
  on" or "Issues to Open" entry — since it blocks the build/test/lint gate for
  every branch based on upstream/main until fixed upstream or worked around.
- Do NOT mark any of the four branches "pushed" or "ready" from this — only the
  rebase + (for C) the reword happened. Gates are unverified pending the upstream
  fix.

## Not done
- Build/test/lint gates not run on any of the four branches (see above).
- No push — per coder rules and the handoff, Dean force-pushes after reviewing.

## Open questions / follow-ups
- Should the upstream `interfaces`/`domain` build break be filed as an issue
  (upstream, since it's PR #1449's fallout) or fixed locally first? Not decided —
  surfacing for Dean.
- Once that's resolved (upstream fix, or explicit go-ahead to patch it locally),
  the build/test/lint/-race gates still need to run on all four branches before
  Dean's force-push.
