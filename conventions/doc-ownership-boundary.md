# Doc ownership boundary

### convention: doc-ownership-boundary-discuss-before-implementing
description: CURRENT.md's 'next step' is a continuity note, not authorization to proceed unattended on a non-trivial implementation task.
scope: any session, especially unattended, deciding whether to act on what a shared doc says
trigger: about to begin a non-trivial implementation task based on CURRENT.md's stated next step
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Discuss before implementing (C20)

**Discuss before implementing.**
Never begin a non-trivial implementation task based solely on what CURRENT.md says is the "next
step." The "Next step" field is a continuity note, not an authorization to proceed. After
resolving the last open task, summarize what was done and ask what to work on next. This applies
even when a detailed plan doc exists — the plan is background for the discussion, not a substitute
for it.

### convention: doc-ownership-boundary-coder-review-docs
description: Coder-authored review docs are out of scope; process-flavored findings go in the handoff to the planner, not a Type 6 doc.
scope: coder agent
trigger: coder learns something process-flavored during its work
status: active
origin: session/CONVENTIONS.md § Handoffs section, Coder-authored review docs are out of scope (C33)

*Coder-authored review docs are out of scope.* Coders ship Type 4 docs (reference
material under docs/) inside their worktree as part of the PR. They never write Type 6
review docs. If a coder learned something process-flavored, it goes in the handoff to
planner, not a Type 6 doc. Type 6 is exclusively external-lens (reviewer, triage,
conversation outcomes).
