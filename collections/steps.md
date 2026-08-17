# Step collections

One `### collection:` entry per common action, named by the action rather than by role — the same
conventions apply whether a coder, planner, or reviewer is the one committing, pushing, or writing a
handoff. A role-collection (see `roles.md`) answers "what does this role need to know standing"; a
step-collection answers "what does anyone need to know right now, about to do this specific thing."

### collection: committing
description: Everything relevant the moment before running git commit.
members: worktree-scope-shared-git-index-pathspec-commit, worktree-scope-pre-action-gate, rebase-integrity-commit-message-vs-diff, doc-ownership-boundary-formula-fork-corollary
trigger: about to run git commit
status: active
origin: micro-rules-migration-plan.md § Step 4.2

The shared-index pathspec rule and the pre-action gate both fire before the commit itself; the
commit-message-vs-diff and formula-fork rules govern what the commit message may claim once written.

### collection: pushing
description: Everything relevant the moment before running git push or opening/updating a PR.
members: pre-push*, github-actions-no-action-without-confirmation, rebase-integrity-commit-message-vs-diff
trigger: about to run git push, or take any other GitHub-writing action
status: active
origin: micro-rules-migration-plan.md § Step 4.2

pre-push's own checklist (branch/gofmt/tests/lint/DCO/build) plus the confirmation gate, the
narrow-to-named-artifact scope rule, the active-PR warning, and the force-push rule all live under
the `pre-push*` prefix already — this collection exists so a caller doesn't have to know that.

### collection: writing-a-handoff
description: Everything relevant while drafting or naming a handoff or trigger file.
members: handoffs*, triggers-format-and-behavior
trigger: about to write, name, or process a handoff or trigger file
status: active
origin: micro-rules-migration-plan.md § Step 4.2

### collection: starting-a-session
description: What every session does at its own start, before anything else.
members: session-start, worktree-scope-coder-session-start-check, checkpoint-capture
trigger: session start, any role
status: active
origin: micro-rules-migration-plan.md § Step 4.2

worktree-scope-coder-session-start-check is coder-specific in name but the underlying discipline
(verify CWD/branch before doing anything) generalizes to every role that starts in a worktree —
included here rather than gated to the coder role-collection alone.

### collection: reviewing-code
description: Everything relevant while running or requesting a code review, internal or external.
members: review-pipeline*
trigger: about to review, or request a review of, a diff
status: active
origin: micro-rules-migration-plan.md § Step 4.2

### collection: deleting-code
description: Everything relevant when removing a function, struct, or significant code block.
members: code-deletion, plans-refs-in-code, dev-guide-updates-reflect-code
trigger: about to delete or substantially remove existing code
status: active
origin: micro-rules-migration-plan.md § Step 4.2

Deletion needs its own classification (deprecated vs. deferred, per code-deletion) plus a check that
nothing plans-branch-identifying leaked into the surrounding code (plans-refs-in-code) plus a check
that the dev guide still reflects what's actually there after the removal.

### collection: writing-a-plan
description: Everything relevant while authoring or updating a Type-3/code-spec plan document.
members: plan-authoring*, doc-ownership-boundary-discuss-before-implementing, semantic-pivot-grep
trigger: about to author or update a plan/code-spec doc
status: active
origin: micro-rules-migration-plan.md § Step 4.2

### collection: updating-current-md
description: Everything relevant for the sync session, the moment before editing CURRENT.md itself.
members: current-md-bounded-shape, current-md-per-task-sections, current-md-quick-rule, handoffs-serialize-shared-state
trigger: about to write to CURRENT.md (sync session only — every other role's equivalent moment is writing-a-handoff instead)
status: active
origin: micro-rules-migration-plan.md § Step 4.2
