# AI Assistant Conventions — llm-d WVA Project

This document orients any AI assistant (Claude, Copilot, etc.) to the working structure of this
project. Read it alongside `CURRENT.md` at the start of every session.

---

## Repository Layout

The main repo is `llm-d/llm-d-workload-variant-autoscaler`. Code branches (`main`, `TA1`, `TA2`,
`TA3`, `engine-multi-analyzer`, …) contain only WVA source code, tests, and committed docs under
`docs/`.

Two additional worktrees live inside the repo directory and are untracked on code branches:

| Path | Branch | Contents |
|---|---|---|
| `./plans` | `plans` (orphan) | Session state, planning docs, scratch/research |
| `./session-notes` | *(retired)* | *(merged into `plans/session/` — do not use)* |

The `plans` branch has no shared history with any code branch. Never let its files appear in a
code PR diff.

### plans/ structure

```
plans/
  session/    — CURRENT.md + this file (transient session state)
  planning/   — design docs and PR plans (TA-Plan.md, TA-PR*-plan.md, etc.)
  scratch/    — archive/, data/, scripts/, try/ (research, experiments, raw data)
```

Commits to the plans branch: `git -C plans add <file> && git -C plans commit -m "..."`.

---

## Document Taxonomy

Dean uses five document types with distinct roles and lifecycles. Never mix them.

**Type 1 — Overall design** (`planning/TA-notation.md`, `TA-supply.md`, `TA-demand.md`, …)
Concepts, algorithms, and goals of the overall mission. Written and frozen before coding starts.
Only reopen for architectural replanning. Lives on the `plans` branch, invisible to code PRs.

**Type 2 — Overall plan** (`planning/TA-Plan.md`)
Mission-level living doc. Updated as the plan becomes concrete and implementation progresses.
Captures alternatives considered and decisions made. Transient — no longer needed after mission
completes. Lives alongside Type 1 on the `plans` branch.

**Type 3 — Detailed phase plans** (`planning/TA-PR1-plan.md` … `TA-PR5-plan.md`, etc.)
One per PR or implementation step. Written before coding starts. Living documents: track progress,
record decisions and failed paths, capture enough state to resume cold from this doc alone.
Lives alongside Type 1/2 on the `plans` branch.

**Type 4 — Post-implementation docs** (`docs/developer-guide/throughput-analyzer.md`, etc.)
Part of each code PR — appears in the diff. Reflects actual current code only — never ahead of
implementation. Must be self-sufficient for code review: a reviewer reading only the PR diff
should understand the design from the Type 4 doc alone. Types 1/2/3 may be linked from the PR
description for deeper context but are not required reading.

**Type 5 — CURRENT.md** (`session/CURRENT.md`)
Transient session state. Enables any new session to resume without prior memory. References other
docs rather than duplicating them. Holds decisions/insights not yet captured elsewhere and removes
them once they land in a permanent doc.

### Quick rule

Before writing anything into CURRENT.md, ask: does this belong in a Type 1–4 doc instead? Only
keep it in CURRENT.md if it is not yet captured elsewhere. When it is captured, replace the
content with a link.

---

## Key Working Rules

**Discuss before implementing.**
Never begin a non-trivial implementation task based solely on what CURRENT.md says is the "next
step." The "Next step" field is a continuity note, not an authorization to proceed. After
resolving the last open task, summarize what was done and ask what to work on next. This applies
even when a detailed plan doc exists — the plan is background for the discussion, not a substitute
for it.

**Type 4 docs reflect code, not plans.**
`docs/developer-guide/throughput-analyzer.md` (and any other Type 4 doc) must always reflect the
actual code state of the branch it is on. Do not include PR-schedule references ("pending PR-N")
or forward-looking implementation details. Use "not yet implemented" for features that are
genuinely absent from the current branch.

**Pre-push checklist.**
Before any `git push` or PR submission on a code branch: `gofmt -l` on changed Go files,
`go test ./internal/... ./pkg/... ./cmd/...`, and `make lint` (golangci-lint). Fix any failure
before pushing.

**Force-push only after history rewrite.**
Use `git push --force-with-lease` only after a rebase or amend. Use plain `git push` for new
commits on top of a branch.

---

## Active PRs (as of 2026-05-06)

See `session/CURRENT.md` for current PR status and branch tips.

Current chain: `main ← TA1 (#1051) ← TA2 (#1052) ← TA3 (not yet submitted)`
