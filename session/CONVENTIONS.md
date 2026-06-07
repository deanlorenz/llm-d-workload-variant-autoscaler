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
├── Main/                    ← worktree: main branch
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

Dean uses six document types with distinct roles and lifecycles. Never mix them. Each type
has a short name (shown in **bold**) to use in conversation and commit messages; the number
stays authoritative for unambiguous reference.

**Type 1 — design** (`planning/TA-notation.md`, `TA-supply.md`, `TA-demand.md`, …)
Overall mission design — concepts, algorithms, goals. Written and frozen before coding starts.
Only reopen for architectural replanning. Lives on the `plans` branch, invisible to code PRs.

**Type 2 — roadmap** (`planning/TA-Plan.md`)
Mission-level living roadmap. Updated as the plan becomes concrete and implementation
progresses. Captures alternatives considered and decisions made. Transient — no longer needed
after the mission completes. Lives alongside Type 1 on the `plans` branch.

**Type 3 — task plan** (`planning/TA-PR1-plan.md` … `TA-PR5-plan.md`, etc.)
Detailed phase plan, one per PR or implementation step. Written before coding starts. Living
document: tracks progress, records decisions and failed paths, captures enough state to resume
cold from this doc alone. Lives alongside Types 1/2 on the `plans` branch.

Any step that changes a function's behavioral contract (rename, panic→error, sync→async,
etc.) must include a companion verification step: the exact `grep` search term and the files
to scan for stale cross-references in comments and docstrings. The coder executes this grep
and updates every hit before committing. If the plan omits this step, the coder writes a
handoff noting the gap rather than inferring scope.

**Type 4 — reference** (`docs/developer-guide/throughput-analyzer.md`, etc.)
Post-implementation reference, part of each code PR — appears in the diff. Reflects actual
current code only — never ahead of implementation. Must be self-sufficient for code review: a
reviewer reading only the PR diff should understand the design from the Type 4 doc alone.
Types 1/2/3 may be linked from the PR description for deeper context but are not required
reading.

**Type 5 — session state** (`session/CURRENT.md`)
Living work tracker. Enables any new session to resume without prior memory. Contains
per-task sections with work items, progress, open issues, and intermediate decisions.
References other docs rather than duplicating them; removes content once it lands in a
permanent doc. Updated continuously as work progresses — by the plan-agent directly, or
by coding agents via handoff files.

**Type 6 — review** (`planning/*-review.md`, e.g. `TA-TA3-review.md`)
Output of the `/design-review` skill. Documents implementation correctness findings: bugs, doc
gaps, NTH items, and confirmed-correct items. Scoped to a branch or design doc. Carries a
`Status: DRAFT` header until the user finalizes the findings in discussion; only `Status: FINAL`
docs are ready for consumption by the plan agent. Never write to a `*-review.md` file unless
you are acting as the review agent.

### Agent roles and document ownership

Three distinct agent roles write to three non-overlapping doc domains:

| Role | Invoked by | Writes | Reads |
|---|---|---|---|
| **Review agent** | `/design-review`, `/s-pr-triage`, etc. | reviews (Type 6), handoffs | designs (Type 1), task plans (Type 3), code |
| **Plan agent** | explicit request | task plans (Type 3), CURRENT.md directly, triggers | reviews (Type 6, FINAL only), designs (Type 1), handoffs, status files |
| **Coder** | explicit request | code, references (Type 4), status files, handoffs, triggers | task plans (Type 3), references (Type 4), status files |

Never write into another agent's domain. A coder should not edit a review; a review agent
should not edit code or task plans. **Only the plan agent writes CURRENT.md directly; all
other agents communicate changes via handoffs.** **Coders read only plan docs (Type 3) for
scope** — handoffs and triggers from siblings or the planner are signals to re-read the plan,
never new instructions in their own right.

### Quick rule

Before writing anything into the session state (Type 5, CURRENT.md), ask: does this belong in
a design, roadmap, task plan, or reference (Types 1–4) instead? Only keep it in session state
if it is not yet captured elsewhere. When it is captured, replace the content with a link.

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

**`cd` to a sibling worktree is always forbidden — for any agent, any purpose.**
This rule applies to all agents (plan-agent, coder, reviewer) without exception. Even for a
read-only query, never `cd` into a sibling worktree in a Bash call. Use `git -C
<absolute-path-to-sibling>` for read-only git queries from your own worktree. The distinction
matters because `cd` changes session CWD and persists across subsequent tool calls, silently
moving writes to the wrong tree. `git -C` leaves CWD untouched.

Prerequisite: `EnterWorktree` requires the session to already be inside a git repository (any
worktree). If the session starts in the container directory, `cd` into any worktree first.

**Discuss before implementing.**
Never begin a non-trivial implementation task based solely on what CURRENT.md says is the "next
step." The "Next step" field is a continuity note, not an authorization to proceed. After
resolving the last open task, summarize what was done and ask what to work on next. This applies
even when a detailed plan doc exists — the plan is background for the discussion, not a substitute
for it.

**Inter-agent communication: status files, handoffs, triggers.**

Three artifact types cover three distinct concerns. Each has one rule.

*Status files — broadcast liveness.* One file per active branch at
`session/status/<branch>.md`, overwritten in place by the coder (or any owning agent) at
meaningful checkpoints: session start, after each commit, when entering or leaving a
blocked state, at session end. Read-only for everyone else. Never absorbed into
CURRENT.md, never deleted by the planner — dropped when the worktree is removed. Status
is operational/ephemeral; CURRENT.md is canonical project state.

Suggested format (loose; expand as needed):
```
last_update: <ISO timestamp>
state: in-progress | blocked | idle | done
current_step: <one line>
blocked_on: <one line, only if state=blocked>
recent_commits:
  - <sha> <subject>
notes: <freeform, optional>
```

*Handoffs — serialize updates to shared state.* Coders and review agents do not edit
CURRENT.md, the PR Status table, or any other planner-owned shared file directly. They
write a handoff at `session/handoffs/plan__<topic>.md` describing what the planner
should fold in. The planner is the single writer; the handoff queue avoids edit conflicts.

When Dean says "sync state" (or equivalent), the plan-agent runs `/sync-current` from
the `plans` worktree. It reads every `plan__*.md`, applies the described updates to
CURRENT.md, marks each consumed file by renaming it to `<file>.md.DONE`, then `git rm`s
the .DONE files in its commit. Sync is a deliberate, explicit declaration — not a
background process.

Handoff format — two header lines plus freeform prose body:
```
from: <branch or agent name>
session: <short topic name>

<freeform: what was completed, what CURRENT should say, new/updated work items,
pending handoffs to add or remove, blockers to clear, next steps to record. Be
complete — the sync agent applies exactly what the handoff describes.>
```

*Triggers — "go re-read X" notifications.* When one agent (planner, coder, or review
agent) wants another to look at something, it writes a trigger at
`session/handoffs/<recipient>__<topic>.md`. The recipient short token is the agent or
branch name (`plan` is reserved for the planner; coder branches use the branch name).

**Triggers carry no instructions.** The body has only:
```
reason: <re-read plan | sibling-status-update | upstream-rebase | other>
refs:
  - <doc path 1>
  - <doc path 2>
note: <optional one-line context>
```

The recipient processes a trigger by **re-reading the referenced docs**, never by
executing the trigger body. A trigger is a doorbell, not a memo. If the planner wants a
coder to do something different, the planner edits the plan doc and rings the bell.
Coder→coder triggers can only point at the sender's status file or a doc — they cannot
direct work; only the recipient's own plan defines scope.

After processing, the recipient renames the trigger to `<file>.md.DONE`.

*File naming — flat directory, prefix encodes routing:*
```
session/handoffs/
  plan__threshold-coder-rules-gap.md       # to planner (prose body)
  optimizer__plan-resume.md                # to multi-analyzer-optimizer coder (no-body trigger)
  threshold__rebase-target-shift.md        # to multi-analyzer-threshold coder (no-body trigger)
```

`<recipient>__<topic>.md`. Filter by `ls session/handoffs/<recipient>__*.md`.
Recipient tokens: `plan` (planner), short branch nicknames for coders.

*State machine via mv (not rm).* Files transition `<file>.md` → `<file>.md.DONE` via a
single `mv`. The .DONE files are removed by the planner via `git rm` in the
`/sync-current` commit, or accumulate harmlessly until cleanup. Coders and the planner
may write and rename files under `plans/session/handoffs/` and `plans/session/status/`
from any worktree — this is the only sanctioned exception to "no edits outside your
worktree."

*Starting a new session without an existing CURRENT entry:* write a `plan__<topic>.md`
handoff that includes everything needed to create the section — session name, task,
scope, initial work items. A new session is not structurally different from any other
shared-state update.

*Coder-authored review docs are out of scope.* Coders ship Type 4 docs (reference
material under `docs/`) inside their worktree as part of the PR. They never write Type 6
review docs. If a coder learned something process-flavored, it goes in the handoff to
planner, not a Type 6 doc. Type 6 is exclusively external-lens (reviewer, triage,
conversation outcomes).

See `plans/.claude/skills/s-sync-current/SKILL.md` for sync mechanics.

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

**Commit messages must reflect the diff — especially after rebase.**
A commit message that describes behavior the diff doesn't implement is a hard reject. Each "Engine
populates X", "Adds Y", "Fixes Z" claim must correspond to a code hunk in the same commit.

After any rebase that replays a commit onto a base where the touched files have moved (e.g.
`git rebase --onto <new-base>`), git's three-way merge can silently drop hunks that no longer apply
cleanly — leaving the commit message intact while the behavior is gone. Procedure for non-trivial
rebases (multi-commit stack AND any touched file has been modified on the new base):

0. **Pre-rebase plan.** Before executing the rebase, write a short plan at
   `planning/<branch>-rebase-<target>.md` (Type 3-style, ephemeral — delete after the rebase is
   verified). Contents: ordered commit list with a one-line "behavior to preserve" per commit
   (mined from the commit message), files expected to conflict on the new base, and the
   post-rebase verification checklist (which diffs to run, which claimed behaviors to confirm).
   Skip the plan for single-commit rebases or rebases that apply cleanly.
1. **Per-file diff inventory.** After the rebase, for each touched file, run
   `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` and confirm every behavior claimed in
   the rebased commits' messages is still present in the post-rebase code.
2. **Per-commit message-vs-diff check.** Read each post-rebase commit's diff against its own
   message — if the message says "Engine populates Score" and the engine_v2.go diff doesn't show
   the population, the commit is broken and must be fixed before the rebase is considered done.
3. **Backstop test.** Where feasible, add a test that asserts the claimed behavior **before** the
   rebase, so silent loss converts to a red test on the next run. This is the strongest backstop;
   (1) and (2) are eyeball checks that only work while the reviewer is paying attention.

The "Score field silently dropped during cross-rebase" incident on `multi-analyzer-optimizer` is
the load-bearing example — the commit message claimed "Engine populates Score from
AnalyzerScoreConfig.Score" across two commits while the diff showed neither populating it.

**Merging upstream into main.**
Always use `git merge --ff-only upstream/main` when fast-forwarding main to upstream. Push to
origin after. Never use a merge commit for this operation.

**Never push to `upstream`.**
No branch ever pushes to the `upstream` remote (the llm-d project), `main` included. `upstream`
is pull-only. The flow for `main` is `upstream/main → local main (ff-only merge) → push to
origin/main`. Contributions reach upstream only through PRs. The bare repo is configured with
`remote.pushDefault = origin` so every `git push` targets origin regardless of the branch's
upstream tracking; do not override this, and never run `git push upstream <anything>`.

**Every code branch has a matching origin branch.**
Code branches — any branch where development happens, typically for a PR (including stacked or
deferred PRs) — must exist on origin (`deanlorenz/llm-d-workload-variant-autoscaler`). When
creating a new code branch, push it to origin with upstream tracking as part of initial setup:

```
git -C <worktree> push -u origin <new-branch>
```

Subject to the "No push without explicit confirmation" rule above — propose the push, get
confirmation, then run it. The `plans` branch counts as a code branch for this purpose.
Throwaway local experiments are fine local-only, but anything that will become a PR or is part
of the active PR stack must have an origin branch from the start.

---

## Active PRs

See `session/CURRENT.md` for current PR status, branch tips, and stacking order.
