from: multi-analyzer-optimizer
session: optimizer-rebase-1237-and-lint

## What changed

Rebased 16 commits from ee8bd815 onto upstream/main@badc48be (post-#1237 role-aware
scale-down). New tip: ad1a8e1e (17 commits = 16 rebased + 1 lint-fix on top).

Commits:
- 80670d04 through 2711bdc1 — the original 16 Phase 1–3 commits, rebased
- ad1a8e1e — pipeline: fix golangci-lint findings after rebase onto main@badc48be

All gates passed: make lint (0 issues), gofmt clean, go build clean, make test 136/136,
go test -race ./internal/engines/... clean, DCO 17/17, grep-to-zero clean.

Target end-state from plan § "CURRENT NEXT ACTION" implemented:
- scaleDownVariantSet generalized (injected callbacks, pre-sorted)
- sortVariantsForScaleDown new helper
- scaleDownRoleIterated thin iterator
- variantsForRole exact-match body
- sortByCostDesc deleted

## Update CURRENT.md

### PR Status table — multi-analyzer-optimizer row
Replace current content with:
  | multi-analyzer-optimizer | #1246 | **PR #1246 OPEN** (base `main`, ev-shindin). Rebase onto `main@badc48be` (#1237) complete; tip `ad1a8e1e`. All gates green (lint 0, test 136/136, DCO 17/17). Awaiting Dean review + force-with-lease push to origin (still at pre-rebase `ee8bd815`). | `ad1a8e1e` |

### Blocked on / Next steps
- Remove the PR #1246 lint-failure note from "Blocked on".
- Add under "Next steps":
  "**Optimizer rebase complete.** Tip `ad1a8e1e`, all gates green. Dean to review
  commits and force-with-lease push to origin (origin at pre-rebase `ee8bd815`),
  then PR #1246 diff updates automatically."

### Recent activity — add entry
"**2026-06-08 — Optimizer rebase onto main@badc48be complete.** Rebased 16 commits onto
upstream/main@badc48be (post-#1237 role-aware scale-down); target end-state from plan
(generalized scaleDownVariantSet, sortVariantsForScaleDown, thin scaleDownRoleIterated,
variantsForRole exact-match, sortByCostDesc deleted) implemented in conflict resolution.
Lint-fix commit (ad1a8e1e) fixes 5 golangci-lint findings (nakedret, 2× unparam,
2× captLocal) + test/gofmt cleanup. All gates green: lint 0, test 136/136, -race clean,
DCO 17/17. New tip ad1a8e1e; awaiting Dean review + force-with-lease push."

## Open questions / follow-ups

None. The branch is ready for Dean's review. After review and push, PR #1246 diff will
update to show the rebase + target end-state. The engine-queue-fix branch + worktree
can be closed once the PR is merged (unchanged from prior handoff).
