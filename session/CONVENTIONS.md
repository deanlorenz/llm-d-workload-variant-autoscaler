# AI Assistant Conventions — llm-d WVA Project

This document orients any AI assistant (Claude, Copilot, etc.) to the working structure of this
project. Read it alongside `CURRENT.md` at the start of every session.

---

## Repository Layout

The workspace uses a **bare repository + worktrees** layout. The bare repo at `repo/` holds all
git metadata; every branch lives as a named worktree at the top level:

```
llm-d-workload-variant-autoscaler/
├── repo/                    ← bare git repository (no working files)
├── main/                    ← worktree: main branch
├── TA1/                     ← worktree: TA1 branch (PR #1051)
├── TA2/                     ← worktree: TA2 branch (PR #1052)
├── TA3/                     ← worktree: TA3 branch (in progress)
├── engine-multi-analyzer/   ← worktree: engine-multi-analyzer branch (PR #1113)
├── engine-queue-fix/        ← worktree: engine-queue-fix branch (deferred)
└── plans/                   ← worktree: plans branch (orphan)
```

Code branches (`main`, `TA1`, `TA2`, `TA3`, `engine-multi-analyzer`, …) contain only WVA source
code, tests, and committed docs under `docs/`. The `plans` branch is an orphan with no shared
history with any code branch. Never let its files appear in a code PR diff.

Worktrees are added as needed (`git -C repo worktree add ../<name> <branch>`) and removed when
the corresponding PR merges. The `plans/` worktree is permanent.

### Skills layout

Personal workflow skills (`s-*`) are tracked exclusively in `plans/.claude/skills/` and are
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

Code branches contain only the upstream project skill `pr-review` under `.claude/skills/`.

When adding a new personal skill: create it in `plans/.claude/skills/`, commit to the plans
branch, then add a matching symlink in the container's `.claude/skills/`. Never commit `s-*`
skills to a code branch.

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

**Type 6 — Review docs** (`planning/*-review.md`, e.g. `TA-TA3-review.md`)
Output of the `/design-review` skill. Documents implementation correctness findings: bugs, doc
gaps, NTH items, and confirmed-correct items. Scoped to a branch or design doc. Carries a
`Status: DRAFT` header until the user finalizes the findings in discussion; only `Status: FINAL`
docs are ready for consumption by the plan agent. Never write to a `*-review.md` file unless you
are acting as the review agent.

### Agent roles and document ownership

Three distinct agent roles write to three non-overlapping doc domains:

| Role | Invoked by | Writes | Reads |
|---|---|---|---|
| **Review agent** | `/design-review` | `*-review.md` (Type 6) | Type 1, 3, code |
| **Plan agent** | explicit request | `*-plan.md` (Type 3) | Type 6 (FINAL only), Type 1 |
| **Coder** | explicit request | code, Type 4 | Type 3, Type 4 |

Never write into another agent's domain. A coder should not edit a `*-review.md`; a review agent
should not edit code or `*-plan.md` files.

### Quick rule

Before writing anything into CURRENT.md, ask: does this belong in a Type 1–4 doc instead? Only
keep it in CURRENT.md if it is not yet captured elsewhere. When it is captured, replace the
content with a link.

---

## Key Working Rules

**Worktree scope.**
Every agent or coding task operates exclusively within its assigned worktree. Never read from or
write to `repo/` (it is bare — no working files), and never touch a sibling worktree. This applies
even when paths in another worktree are visible from the filesystem. Never write code or edit
source files while the session CWD is the container directory — use `EnterWorktree` first.

**Switching worktrees — use `EnterWorktree`.**
To move work to a different branch, use the `EnterWorktree` tool with the `path` of the target
worktree (e.g. `path: ".../TA3"`). This is the only approved way to switch worktree context: it
updates CWD, reloads memory files and CLAUDE.md, and appears as an explicit tool call in the UI
so Dean can approve or deny it. Never use bare `cd` or `-C` flags as a substitute for a context
switch. `ExitWorktree(action: "keep")` returns to the previous worktree.

Prerequisite: `EnterWorktree` requires the session to already be inside a git repository (any
worktree). If the session starts in the container directory, `cd` into any worktree first.

**Discuss before implementing.**
Never begin a non-trivial implementation task based solely on what CURRENT.md says is the "next
step." The "Next step" field is a continuity note, not an authorization to proceed. After
resolving the last open task, summarize what was done and ask what to work on next. This applies
even when a detailed plan doc exists — the plan is background for the discussion, not a substitute
for it.

**Shared-state updates go through handoff files.**
`session/CURRENT.md` is a shared-state document that may be touched by multiple parallel agent
sessions (plan agent, review agent, coder). To avoid races and overwrites, updates to its
agent-output sections must be produced by **handoff files** at `session/handoffs/<name>.md`
and merged into CURRENT.md by the `/sync-current` skill — not by direct edits.

Create a handoff file whenever a session produces a document (plan, review, code change) that
another agent will consume, or whenever the existence of that document should be reflected in
CURRENT.md. This rule applies **regardless of the document's status** — DRAFT, READY, and FINAL
documents all use the same handoff flow. The handoff signals "this doc exists at this path with
this status"; `/sync-current` reconciles the set of handoffs into CURRENT.md's `## Pending
handoffs` table.

Handoff file format:

```
to: plan-agent | coder | reviewer
doc: <relative path from plans/ worktree root>
status: DRAFT | READY | FINAL
note: <one-line description>
```

Durable sections of CURRENT.md (PR Status, Blocked on, Next steps, long-running paused features
such as "TA3 Paused State") may be edited directly — they are project state, not agent-output
state, and do not race against parallel agents. If you are unsure whether a section is durable
or agent-output, ask.

See `plans/.claude/skills/s-sync-current/SKILL.md` for the sync merge rules.

**Type 4 docs reflect code, not plans.**
`docs/developer-guide/throughput-analyzer.md` (and any other Type 4 doc) must always reflect the
actual code state of the branch it is on. Do not include PR-schedule references ("pending PR-N")
or forward-looking implementation details. Use "not yet implemented" for features that are
genuinely absent from the current branch.

**Pre-push checklist (run in order before every `git push` or PR submission).**
1. **Check current branch** — `git branch --show-current`. Confirm you are on the intended branch before any commit, amend, or rebase.
2. **gofmt** — `gofmt -l ./internal/... ./pkg/... ./cmd/...`. No output means clean.
3. **Tests** — `go test ./internal/... ./pkg/... ./cmd/...`. All pass.
4. **DCO sign-off** — every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Use `git commit --signoff` or `git commit --amend --signoff`. Verify with `git log upstream/main..HEAD --format="%b" | grep Signed-off-by`. DCO failure blocks CI and requires a force-push after the PR is open.
5. **Build** — `go build ./...`. Clean.

**No push without explicit confirmation.**
Never run `git push` (or any variant) without Dean's explicit confirmation for that specific push.
State what branch will be pushed, the commit range, and whether it is a force push — then wait for
approval. Do not infer approval from earlier conversation context.

**Warn before pushing to an active PR branch.**
If the target branch has an open PR (check `gh pr view <branch>`), state the PR number and title
before pushing and wait for confirmation. This prevents accidental history rewrites or force-pushes
that would disrupt reviewers.

**No GitHub actions without explicit confirmation.**
Never post a comment on a PR or issue, create a PR, create an issue, request reviewers, or take
any other GitHub action that is visible to others without Dean's explicit instruction for that
specific action. Summarise the proposed text and wait for approval before running any `gh` command
that writes to GitHub.

**Force-push only after history rewrite, and explain why.**
Use `git push --force-with-lease` only after a rebase or amend — never for new commits on top of a
branch. Before force-pushing, state the reason (e.g., "rebased onto upstream/main", "amended to
add DCO sign-off") and wait for confirmation. Prefer `--force-with-lease` over `--force`.

**Merging upstream into main.**
Always use `git merge --ff-only upstream/main` when fast-forwarding main to upstream. Push to
origin after. Never use a merge commit for this operation.

---

## Active PRs

See `session/CURRENT.md` for current PR status, branch tips, and stacking order.
