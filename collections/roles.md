# Role collections

One `### collection:` entry per role with real harvested convention content beyond its thin
`roles/<role>.md` kernel. A role with no entry here has no conventions beyond its kernel yet —
absence is a gap to fill later, not a claim the role needs nothing.

### collection: coder
description: Conventions a coder session needs beyond its role kernel (roles/coder.md).
members: worktree-scope*, handoffs*, triggers-format-and-behavior, status-files*, pre-push*, code-deletion, dev-guide-updates*, go-test-gates, plans-refs-in-code, review-pipeline*, semantic-pivot-grep, session-start, github-actions-no-action-without-confirmation, rebase-integrity-commit-message-vs-diff, git-remotes*
trigger: session start, as a coder
status: active
origin: micro-rules-migration-plan.md § Step 4; every member topic's own conventions/*.md file

Every one of these fires during ordinary coder work: worktree-scope on every write, handoffs/triggers/
status-files for inter-agent communication, pre-push/github-actions/rebase-integrity/git-remotes before
any push, code-deletion/dev-guide-updates/semantic-pivot-grep while editing code, go-test-gates before
declaring push-ready, plans-refs-in-code as a standing constraint on what a coder writes into code-side
artifacts, review-pipeline when requesting or running a self-check, session-start once at launch.

### collection: sync
description: Conventions the sync session needs beyond its role kernel (roles/sync.md).
members: handoffs*, current-md-bounded-shape, current-md-quick-rule, status-files*, triggers-format-and-behavior
trigger: session start, as the sync session
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/sync.md

sync's whole job is CURRENT.md-format compliance and handoff/trigger/status-file consumption — these
four are its entire working surface beyond the /sync-current mechanics already in its role kernel.
