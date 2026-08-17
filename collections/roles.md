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

### collection: epic
description: Conventions an epic role needs beyond its role kernel (roles/epic.md).
members: plan-authoring*, doc-ownership-boundary-discuss-before-implementing, handoffs-serialize-shared-state
trigger: session start, breaking a design into a code roadmap
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/epic.md

Turning a design into a roadmap is fundamentally a plan-authoring act — the micro-rules structure,
dev-guide-section naming, and the no-other-role-actions scan all apply the moment this role starts
writing. The doc-ownership-boundary entry matters because an epic plan sits one layer removed from
Dean's own presence; the same "is this mine to decide, or does it need to go back to him" check that
guards any unattended judgment call applies here too.

### collection: spec
description: Conventions a spec role needs beyond its role kernel (roles/spec.md).
members: plan-authoring*, pre-push*, github-actions*, rebase-integrity*, handoffs-serialize-shared-state, doc-ownership-boundary-discuss-before-implementing
trigger: session start, owning a code spec through to landing
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/spec.md

spec is the role that actually pushes and opens PRs (coders never do) — the full push/PR/rebase
surface applies directly, not just as background knowledge. plan-authoring applies because a spec
is itself a Type-3-shaped document with the same structural requirements as an epic plan.

### collection: confirm
description: Conventions a confirm role needs beyond its role kernel (roles/confirm.md).
members: review-pipeline*, doc-ownership-boundary-discuss-before-implementing
trigger: session start, checking a code spec against its epic plan and design
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/confirm.md

Thin by honest necessity — per the role's own file, no kernel content exists specific to confirm
versus the generic review pipeline both confirm and verify draw on. This collection is exactly that
shared surface; it will grow once confirm and verify are actually separated (the role file's own
"open, unresolved" note) rather than being invented now.

### collection: verify
description: Conventions a verify role needs beyond its role kernel (roles/verify.md).
members: review-pipeline*, doc-ownership-boundary-discuss-before-implementing
trigger: session start, checking code against what its spec promised
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/verify.md

Identical membership to confirm today, for the identical reason (see that entry) — not a mistake,
a faithful reflection of the current state where both roles draw on the same undifferentiated review
pipeline. Diverges once the two roles are actually split.

### collection: pr
description: Conventions a pr role needs beyond its role kernel (roles/pr.md).
members: github-actions*
trigger: session start, reviewing a PR as a GitHub artifact
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/pr.md

Thinnest of all the review-family collections — the role's own file records zero skill coverage and
zero harvested kernel content specific to it. github-actions* is the one already-real surface that
touches this role's subject matter (a GitHub PR) at all; everything else is a genuine gap, not filled.

### collection: triage
description: Conventions a triage role needs beyond its role kernel (roles/triage.md).
members: github-actions*, review-pipeline*, plan-authoring*
trigger: session start, on first external review of an open PR
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/triage.md

Triage reads PR comments/CI (github-actions, review-pipeline) and produces a code spec or an
addition to one (plan-authoring) — its own file's "Confirmed live gap" note that the existing
`s-pr-triage` skill produces a review doc instead is unaffected by this collection; the gap is in
the skill's output shape, not in which conventions apply.

### collection: policy-writer
description: Conventions a policy-writer role needs beyond its role kernel (roles/policy-writer.md).
members: plan-authoring*, doc-ownership-boundary*
trigger: session start, capturing an incident or a statement as a standing convention
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/policy-writer.md

This role IS the harvest this migration plan is executing — plan-authoring's documentation
discipline and doc-ownership-boundary's "whose call is this" test both apply directly to the act of
writing a new `### convention:` entry or role file. No skill coverage exists yet (the role file's own
"structural gap, not just missing content" note), consistent with why this collection is thin.

### collection: designer
description: No conventions beyond roles/designer.md exist yet.
members: doc-ownership-boundary-discuss-before-implementing
trigger: session start, producing a design doc from conversation
status: active
origin: micro-rules-migration-plan.md § Step 4; roles/designer.md

Deliberately the thinnest possible non-empty collection — the role file itself records zero
harvested kernel content and no implementing skill. The one member included is the general
judgment-call boundary every role needs regardless of domain; nothing design-specific exists to add
yet, and nothing is invented here to fill that gap.
