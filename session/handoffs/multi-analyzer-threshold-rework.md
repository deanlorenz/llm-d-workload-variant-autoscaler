to: multi-analyzer-threshold agent
from: plan-agent
session: multi-analyzer-threshold architectural rework

## Trigger

Apply the rework plan at `planning/multi-analyzer-threshold-plan.md`.

That doc is the canonical source for: architectural decisions, contract spec,
4-commit plan, file-level changes, mechanics, verification gates, coordination
notes, and open items. Read it end-to-end before touching any code.

## Operational reminders

- Worktree scope: work only inside `multi-analyzer-threshold/`. Read absolute
  paths cross-worktree as needed (CONVENTIONS allows); never `cd` or `git -C`
  into a sibling worktree.
- Force-push policy: `--force-with-lease` only, after all 4 commits land
  locally and verify clean. Do NOT push without explicit Dean confirmation
  per CONVENTIONS.
- DCO sign-off on every commit (`git commit -s`).
- Update your living handoff at
  `session/handoffs/multi-analyzer-threshold-status.md` (note: "status",
  not "rework" or "commit-2-1") with the 4 new SHAs, verification results,
  and ready-for-review status when done.
