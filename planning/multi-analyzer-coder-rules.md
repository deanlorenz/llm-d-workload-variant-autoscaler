# Multi-Analyzer Split — Coder Rules

Hard rules for the three coding agents working in parallel on the multi-analyzer
PR split. Read these before any edit. They are agent-invariant: same rules
apply to all three branches.

## Required reading (in order, before any edit)

1. **`plans/session/CONVENTIONS.md`** — project conventions: worktree layout,
   document taxonomy (Type 1-6), agent roles and doc ownership, key working
   rules (worktree scope, no-push-without-confirmation, etc.). Authoritative
   source for everything below; if anything in this file conflicts with
   CONVENTIONS, CONVENTIONS wins.
2. **`plans/session/CURRENT.md`** — session state, PR status, and the
   "Multi-Analyzer Split — coder sessions" section that lists the three
   branches and their roadmap mapping.
3. **`plans/planning/PR1113-review.md`** — the fix design. The Implementation
   roadmap section is your per-branch scope source.
4. This document — *how* you work (the rules below).

---

## 1. Worktree scope — only edit inside your branch

You operate exclusively within one worktree (your assigned branch). Edits,
writes, file creations, and file deletions are limited to files inside your
worktree directory. Never touch a sibling worktree (`engine-multi-analyzer/`,
`multi-analyzer-threshold/`, `multi-analyzer-optimizer/`, `main/`, `TA*/`,
`plans/`, etc.) from your session, even if their files are visible.

Reads are unrestricted: you may read any file in the workspace root or the
`plans/` tree (CURRENT.md, CONVENTIONS.md, PR1113-review.md, design docs,
sibling-branch source code) for context. Reading is not editing.

If a task seems to require touching a sibling worktree's files, stop and write
a handoff describing why — do not edit.

---

## 2. Local changes only — no pushes, no PRs, no GitHub actions

- Never run `git push` (with or without flags).
- Never run `gh pr create`, `gh pr edit`, `gh pr comment`, `gh issue create`,
  or any other `gh` command that writes to GitHub.
- Never use `git push --force-with-lease` or `git push --force`.
- Commits stay local on your branch. Dean reviews and pushes manually after
  approval.

You may run all read-only `gh` commands (`gh pr view`, `gh pr checks`,
`gh api ...` for reads) and all local `git` operations (commit, rebase, log,
diff, status, branch listing).

---

## 3. Tests — write and run

- Add unit tests for every new behavior. Migrate or move existing tests when
  the design doc says to (see Migration audit in PR1113-review.md).
- Run `go test ./internal/... ./pkg/... ./cmd/...` after each substantial
  change. All tests must pass before you call work done.
- Run `gofmt -l ./internal/... ./pkg/... ./cmd/...` — must be empty.
- Run `go build ./...` — must be clean.
- Use `-race` when relevant (especially for the registration race fix).

If a test fails for reasons outside your scope (pre-existing breakage on main),
note it in the handoff and continue — do not fix unrelated tests.

---

## 4. Developer-guide updates on your branch

Every code change that affects user-visible or architecturally-visible
behavior gets reflected in `docs/developer-guide/` on your branch. This is a
Type 4 doc per `plans/session/CONVENTIONS.md`: must reflect the actual code
state of your branch, no forward-looking content, no "pending PR-X" references.

Existing developer-guide files relevant to the multi-analyzer split:
- `docs/developer-guide/saturation-scaling-config.md` (Multi-Analyzer Pipeline section)
- `docs/developer-guide/saturation-analyzer.md`
- `docs/developer-guide/throughput-analyzer.md`

Either update an existing file or add a new one if the topic has no home.
Self-sufficient for code review: a reviewer reading only your PR diff should
understand the design from the developer-guide doc alone.

---

## 5. Handoff files — living progress log, updated as you work

Your handoff file is a **living progress log**, not an end-of-session
artifact. Update it at every meaningful checkpoint so a monitoring agent
(or Dean) can tail it and know where you are without interrupting the
session.

**File path** — one file per session, fixed for the whole session:
`plans/session/handoffs/<branch>-<topic>.md` (e.g.
`multi-analyzer-threshold-commit-2-1.md`,
`multi-analyzer-optimizer-slice-redesign.md`).

**Format** — open with the two header lines required by
`plans/session/CONVENTIONS.md` "Shared-state updates go through handoff
files":

```
to: sync-current
session: <short session name>
```

The body uses the section template in §9 below. Status starts as `WIP —
in progress` and stays that way until Dean reviews. Never write a final
"done" status yourself.

**When to update** (rewrite the file in place each time, full snapshot;
this is not append-only — the latest write is the current state):

- After reading the design and before any edit: write the initial handoff
  with your understanding of scope, the commits you plan to land, and any
  questions you'd flag *before* coding.
- After each commit: update "Implemented" with the new commit, update
  "Verified" with the latest test/build output.
- After each test run, build, or other verification: update "Verified".
- When you hit a question, blocker, or judgment call: add it to "Open
  questions for Dean" or "Not done / known limitations" and keep working
  if you can, or stop and wait if it gates further work.
- Before pausing for any reason (end of session, blocker, waiting on
  review): one final update reflecting current state.

**A monitoring agent may read your handoff at any time.** It will not
write to it. Keep the format stable and the latest snapshot accurate —
the monitor's only signal that you are alive and on track is the file's
mtime + content. Stale handoffs look like crashed sessions.

**Do not edit CURRENT.md directly.** The plan-agent applies your handoff
via `/sync-current` after Dean reviews. Coder agents writing to
`plans/session/handoffs/` is explicitly allowed by CONVENTIONS.

---

## 6. WIP until Dean reviews — don't mark work "complete"

Until Dean reviews and approves the code, the work is WIP. Convey this
explicitly:

- In your handoff: status reads "WIP — pending Dean review"; list every
  reviewable artifact (commit hashes, files touched, dev-guide sections
  added/changed, test specs added).
- The session-state update in CURRENT.md (applied by the plan-agent later)
  reflects "in review", not "complete".
- Don't write a handoff that says "done" or "ready to merge". Even if all
  tests pass, your work is not done until Dean confirms it.

---

## 7. Things you may do without asking

- Read any file in the workspace.
- Run `git status`, `git diff`, `git log`, `git branch`, `git show`,
  `git rebase` (within your branch), `git commit`.
- Run `go test`, `go build`, `gofmt`, `go vet`, `golangci-lint` (if
  configured).
- Run read-only `gh` commands.
- Edit / write / delete files inside your worktree.
- Move tests within your branch.
- Add new files in your worktree (source, tests, dev-guide).

## 8. Things you may NOT do without asking

- Edit anything outside your worktree.
- Run `git push` of any kind.
- Run any GitHub-mutating `gh` command.
- Skip pre-commit hooks (`--no-verify`).
- Force-push (even within your branch).
- Run destructive operations (`git reset --hard`, `rm -rf` outside scratch
  paths, `git branch -D`).
- Create commits without DCO sign-off (each commit must carry
  `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` per
  `plans/session/CONVENTIONS.md` Pre-push checklist).

---

## 9. Handoff template — living progress log

Rewrite this file in place at every checkpoint (see §5). Status stays WIP
until Dean reviews; never mark complete yourself.

```
to: sync-current
session: <branch>-<short-session-id>

## Status
WIP — <current phase>. Last updated: <ISO timestamp>.

## Branch / worktree
<branch> at <worktree path> ; tip <commit-sha-short>

## Implemented
- <commit sha> — <message>
- ...

## Tests added / moved
- <test file>:<spec> — <one-line description>
- ...

## Verified
- go test ./internal/... ./pkg/... ./cmd/... — PASS
- gofmt -l ... — clean
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
```
