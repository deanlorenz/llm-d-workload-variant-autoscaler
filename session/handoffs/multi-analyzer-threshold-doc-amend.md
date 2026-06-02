to: multi-analyzer-threshold agent
from: plan-agent
session: multi-analyzer-threshold doc amend (post-review clarifications)

## Trigger

Apply the addendum at `planning/multi-analyzer-threshold-plan.md` § "Addendum
(2026-06-02): post-review doc clarifications".

Two small text additions (no code change):
- Patch 1 — `internal/interfaces/analyzer.go` `SchedulerQueue` field doc-comment.
- Patch 2 — `docs/developer-guide/saturation-scaling-config.md` new "Analyzer
  inputs" subsection.

**Amend into commit 4** (`1ba3c978`). The branch is unpushed; amend is safe.

## Operational reminders

- Worktree scope: work only inside `multi-analyzer-threshold/`.
- After amend, verify: `gofmt`, `go vet`, `go build`, `make test`, DCO present
  on the amended commit.
- Do NOT push without explicit Dean confirmation per CONVENTIONS.
- Update your living handoff at
  `session/handoffs/multi-analyzer-threshold-status.md` with the new tip SHA
  after amend.
