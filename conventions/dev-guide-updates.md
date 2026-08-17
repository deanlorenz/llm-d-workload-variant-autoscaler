# Dev guide updates

### convention: dev-guide-updates-reflect-code
description: Type 4 developer-guide docs must always reflect actual current code, never pending-PR or forward-looking content.
scope: anyone writing or updating a Type 4 developer-guide doc
trigger: writing or updating docs/developer-guide/ content
status: active
origin: session/CONVENTIONS.md § Type 4 docs reflect code, not plans (C34)

**Type 4 docs reflect code, not plans.**
docs/developer-guide/throughput-analyzer.md (and any other Type 4 doc) must always reflect the
actual code state of the branch it is on. Do not include PR-schedule references ("pending PR-N")
or forward-looking implementation details. Use "not yet implemented" for features that are
genuinely absent from the current branch.

### convention: dev-guide-updates-coder-branch
description: Every code change with user- or architecturally-visible behavior gets reflected in docs/developer-guide/ on the coder's branch, self-sufficient for code review.
scope: coder agent
trigger: a code change affects user-visible or architecturally-visible behavior
status: active
origin: session/CODER-CONVENTIONS.md §4 Developer-guide updates on your branch (CC9)

**4. Developer-guide updates on your branch.**

Every code change that affects user-visible or architecturally-visible
behavior gets reflected in docs/developer-guide/ on your branch
(WVA-specific path; the principle is general — Type 4 reference docs
ship in the PR). Per CONVENTIONS.md Type 4: must reflect the actual
code state of your branch, no forward-looking content, no "pending
PR-X" references.

Either update an existing file or add a new one if the topic has no
home. Self-sufficient for code review: a reviewer reading only your PR
diff should understand the design from the developer-guide doc alone.

The specific files relevant to your mission are listed in your mission
doc (e.g., multi-analyzer-coder-rules.md).
