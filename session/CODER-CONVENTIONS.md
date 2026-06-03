# Coder Agent Conventions

Loaded automatically via `@session/CODER-CONVENTIONS.md` from `plans/CLAUDE.md`.
Extends `session/CONVENTIONS.md` with rules specific to the **coder agent role**.

A coder agent receives a plan doc and a worktree, produces code changes within
that worktree, and reports state via the protocols below. Coders are
interactive on coding judgment calls (genuine ambiguity); everything else
runs without prompting.

If anything here conflicts with `CONVENTIONS.md`, CONVENTIONS wins.

> Items marked `(WVA-specific)` are project-specific to the llm-d WVA
> codebase. They will eventually move to a project-specific conventions
> layer when that split happens — keep the markers visible.

---

## 1. Worktree scope — only edit inside your branch

You operate exclusively within one worktree (your assigned branch).
**Edit operations** — `Write`, `Edit`, file creation/deletion, `git
commit`, `git rebase`, `git checkout` to switch branch, `git branch -D`,
and any other state-changing command — are limited to files inside your
worktree directory. Never edit, write to, or change the state of a
sibling worktree from your session.

**Reads are unrestricted.** You may read any file in the workspace root
or the `plans/` tree (CURRENT.md, CONVENTIONS.md, design docs, sibling
status files, sibling-branch source code) for context. Read-only `git`
commands targeting a sibling — `git -C <sibling> log`, `git -C <sibling>
diff`, `git -C <sibling> show`, `git -C <sibling> status`, `git -C
<sibling> branch` listing — are fine; use them when you need committed
code or history from another branch. The hard rule is no `git -C
<sibling>` for edit operations (commit, rebase, checkout-with-side-
effects, branch -D, etc.).

**Default to your own worktree.** `-C <sibling>` and absolute paths to
sibling worktrees are *exceptions*, not the default. Reach for them only
when you genuinely need committed state from another branch.

**Single sanctioned write exception outside your worktree:** you may
write and `mv` files under `plans/session/handoffs/` (your handoffs to
the planner, triggers to siblings) and write your own status file at
`plans/session/status/<your-branch>.md`. These are the only paths
outside your worktree where edits are allowed. See §5.

If a task seems to require touching anything else outside your worktree,
stop and write a handoff describing why — do not edit.

**To work on another branch**, use `EnterWorktree` per CONVENTIONS — not
`cd`, not `git checkout` from your current worktree.

---

## 2. Local changes only — no pushes, no PRs, no GitHub actions

- Never run `git push` (with or without flags).
- Never run `gh pr create`, `gh pr edit`, `gh pr comment`, `gh issue create`,
  or any other `gh` command that writes to GitHub.
- Never use `git push --force-with-lease` or `git push --force`.
- Commits stay local on your branch. Dean reviews and pushes manually after
  approval.

You may run all read-only `gh` commands (`gh pr view`, `gh pr checks`,
`gh api ...` for reads) and all local `git` operations (commit, rebase,
log, diff, status, branch listing) from your own worktree.

---

## 3. Tests — write and run

- Add unit tests for every new behavior. Migrate or move existing tests
  when the plan doc says to.
- Run the project's test suite after each substantial change. All tests
  must pass before you call work done.
  - `make test` (WVA-specific) is the canonical entry point. It wraps
    `go test ./internal/... ./pkg/... ./cmd/...` plus any project-
    specific flags. Use `make test` rather than invoking `go test`
    directly.
- Run `gofmt -l ./internal/... ./pkg/... ./cmd/...` (WVA-specific) — must
  be empty.
- Run `go build ./...` — must be clean.
- Use `-race` when relevant (especially for concurrency-sensitive code).

If a test fails for reasons outside your scope (pre-existing breakage on
main), note it in your status file and continue — do not fix unrelated
tests.

---

## 4. Developer-guide updates on your branch

Every code change that affects user-visible or architecturally-visible
behavior gets reflected in `docs/developer-guide/` on your branch
(WVA-specific path; the principle is general — Type 4 reference docs
ship in the PR). Per `CONVENTIONS.md` Type 4: must reflect the actual
code state of your branch, no forward-looking content, no "pending
PR-X" references.

Either update an existing file or add a new one if the topic has no
home. Self-sufficient for code review: a reviewer reading only your PR
diff should understand the design from the developer-guide doc alone.

The specific files relevant to your mission are listed in your mission
doc (e.g., `multi-analyzer-coder-rules.md`).

---

## 5. Status file (living) and handoffs (one-shot)

Two separate artifacts under `plans/session/`. Don't conflate them.

### 5.1 Status file — living progress log

Your status file is your continuous heartbeat. One file per branch,
fixed path, overwritten in place at every meaningful checkpoint:

```
plans/session/status/<branch>.md
```

A monitoring agent or Dean reads it to see where you are without
interrupting your session. Stale status looks like a crashed session.

**Format** — see §9.1 template. Suggested fields per CONVENTIONS:

```
last_update: <ISO timestamp>
state: in-progress | blocked | idle | done
current_step: <one line>
blocked_on: <one line, only if state=blocked>
recent_commits:
  - <sha> <subject>
notes: <freeform, optional>
```

Status starts as `in-progress` and stays that way until Dean reviews.
Never write `state: done` yourself.

**When to rewrite** (full snapshot each time; not append-only):

- Session start: initial entry with your understanding of scope and
  what you plan to land.
- After each commit: update `recent_commits` and `current_step`.
- After each test run / build / verification: reflect in `notes` if
  something noteworthy.
- When you hit a question, blocker, or judgment call: flip
  `state: blocked` and fill `blocked_on`; keep working if you can on a
  different track, or stop and wait if it gates everything.
- Before pausing for any reason (end of session, waiting on review): one
  final write reflecting current state.

The status file is **broadcast, not directive.** Other agents may read
it to inform their own actions, but they never absorb it into CURRENT.md
or take instructions from it. If a sibling needs your output, the
sibling's own plan tells them what to do — your status is just a hint
that something moved.

### 5.2 Handoff to planner — when shared state should change

When work reaches a point where CURRENT.md / the PR Status table /
pending handoffs / blockers / next steps need to change, write a handoff
at:

```
plans/session/handoffs/plan__<topic>.md
```

Format — two header lines plus freeform prose; see §9.2 template.

Write a handoff at meaningful gates: when you finish a commit you want
reflected in CURRENT, when you pause and want the project state
captured, when you raise a question that should be visible across
sessions. Do not write a handoff per checkpoint — that's what the status
file is for.

The plan-agent processes pending handoffs via `/sync-current` when Dean
asks. Your handoff is then renamed to `<file>.md.DONE` and `git rm`-ed
in the sync commit.

### 5.3 Triggers to siblings — only when needed

If your work changes something a sibling coder needs to react to (your
tip moved, an interface you both touched changed shape, etc.), write a
trigger at:

```
plans/session/handoffs/<sibling>__<topic>.md
```

Triggers carry **no instructions**. The body has only `reason`, `refs`
(docs the sibling should re-read), and an optional one-line `note`. See
§9.3 and CONVENTIONS for the exact format. The sibling re-reads the
referenced docs and lets their own plan decide how to react.

**Do not edit CURRENT.md directly.** Coder writes are limited to your
worktree, `plans/session/handoffs/`, and
`plans/session/status/<your-branch>.md` (per §1). The planner is the
only writer of CURRENT.md.

---

## 6. WIP until Dean reviews — don't mark work "complete"

Until Dean reviews and approves the code, the work is WIP. Convey this
explicitly:

- In your status file: `state: in-progress` until Dean reviews. Never
  `state: done` yourself.
- In any plan-handoff: list every reviewable artifact (commit hashes,
  files touched, dev-guide sections added/changed, test specs added) and
  describe the section update for CURRENT.md as "in review", not
  "complete" or "ready to merge".
- The session-state update in CURRENT.md (applied by the plan-agent
  later) reflects "in review", not "complete".

---

## 7. Things you may do without asking

- Read any file in the workspace, including sibling worktrees.
- Run read-only `git` commands from your own worktree (`status`, `diff`,
  `log`, `branch` listing, `show`).
- Run read-only `git -C <sibling>` commands (`log`, `diff`, `show`,
  `status`, `branch` listing) when you need committed code or history
  from another branch.
- Run write `git` commands from your own worktree only: `commit`,
  `rebase` (within your branch), `add`, `mv`, etc.
- Run `make test`, `go test`, `go build`, `gofmt`, `go vet`,
  `golangci-lint` (the first is WVA-specific; the rest are project-
  agnostic).
- Run read-only `gh` commands.
- Edit / write / delete files inside your worktree.
- Move tests within your branch.
- Add new files in your worktree (source, tests, dev-guide).
- Write your own status file at
  `plans/session/status/<your-branch>.md`.
- Write your own `plan__*.md` handoffs and `<sibling>__*.md` triggers
  under `plans/session/handoffs/`.
- `mv <file>.md <file>.md.DONE` for any handoff or trigger addressed to
  you (in `plans/session/handoffs/`).

## 8. Things you may NOT do without asking

- Edit, write, or delete files in a sibling worktree.
- Run any state-changing `git -C <sibling>` command (`commit`, `rebase`,
  `checkout` with side effects, `branch -D`, etc.). Read-only `-C` is
  fine; writes are not.
- Edit any other agent's status file.
- Edit, `mv`, or `rm` someone else's pending handoff or trigger
  (anything not addressed to you).
- Edit CURRENT.md directly (the planner is the only writer).
- `rm` consumed handoffs or triggers — use `mv <file>.md <file>.md.DONE`.
- Run `git push` of any kind.
- Run any GitHub-mutating `gh` command.
- Skip pre-commit hooks (`--no-verify`).
- Force-push (even within your branch).
- Run destructive operations (`git reset --hard`, `rm -rf` outside
  scratch paths, `git branch -D`).
- Create commits without DCO sign-off (each commit must carry
  `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` per
  `CONVENTIONS.md` Pre-push checklist) (WVA-specific identity; DCO
  discipline is general for upstream contributions).

---

## 9. Templates

### 9.1 Status file (`plans/session/status/<branch>.md`)

Rewrite this file in place at every checkpoint (see §5.1). `state` stays
`in-progress` until Dean reviews; never write `state: done` yourself.

```
last_update: <ISO timestamp>
state: in-progress | blocked
current_step: <one line — what you are doing right now>
blocked_on: <one line, only if state=blocked>

## Branch
<branch> at <worktree path> ; tip <commit-sha-short>

## Recent commits
- <sha> — <message>
- ...

## Tests added / moved
- <test file>:<spec> — <one-line description>
- ...

## Verified
- make test — PASS                                      # WVA-specific
- gofmt -l ./internal/... ./pkg/... ./cmd/... — clean   # WVA-specific
- go build ./... — clean
- (any -race or scenario-specific runs)

## Developer guide
- <path> — <what was added/changed>

## Open questions for Dean
- <question 1>
- ...

## Not done / known limitations
- <item>
- ...

## Notes
<freeform>
```

### 9.2 Handoff to planner (`plans/session/handoffs/plan__<topic>.md`)

Written when shared state (CURRENT.md, PR Status table, blockers, next
steps) needs to change (see §5.2). One-shot — not a living file.

```
from: <your branch>
session: <short topic name>

## What changed
<commit shas, files touched, gates passed>

## Update CURRENT.md
<what the per-task section / PR Status row / blockers / next steps
should say>

## Open questions / follow-ups
<things to surface across sessions>
```

### 9.3 Trigger to a sibling (`plans/session/handoffs/<sibling>__<topic>.md`)

Zero instructions in the body — only refs (see §5.3 and CONVENTIONS).

```
reason: <re-read plan | sibling-status-update | upstream-rebase | other>
refs:
  - <doc path 1>
  - <doc path 2>
note: <optional one line>
```
