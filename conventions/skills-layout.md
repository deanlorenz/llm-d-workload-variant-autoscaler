# Skills layout

### convention: skills-layout
description: Personal s-* skills live only on the plans branch, symlinked into the container for discoverability from every worktree.
scope: adding, editing, or referencing a personal workflow skill
trigger: adding a new skill, or wondering why a code branch does not see it
status: active
origin: session/CONVENTIONS.md § Skills layout (C4)

**Skills layout.**

Personal workflow skills (`s-*`) are tracked exclusively in plans/.claude/skills/ and are
never committed to code branches. The container directory holds symlinks so they are discoverable
from every worktree via the directory walk-up:

```
llm-d-workload-variant-autoscaler/.claude/skills/
  s-design-review → ../../plans/.claude/skills/s-design-review
  s-note          → ../../plans/.claude/skills/s-note
  s-plan          → ../../plans/.claude/skills/s-plan
  s-pr-triage     → ../../plans/.claude/skills/s-pr-triage
  s-pre-push      → ../../plans/.claude/skills/s-pre-push
  s-sync-current  → ../../plans/.claude/skills/s-sync-current
```

Code branches contain only the upstream project skill `pr-review` under .claude/skills/.

When adding a new personal skill: create it in plans/.claude/skills/, commit to the plans
branch, then add a matching symlink in the container's .claude/skills/. Never commit `s-*`
skills to a code branch.
