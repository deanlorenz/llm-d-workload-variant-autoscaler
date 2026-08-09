---
name: s-coder
description: Load the coder-role rulebook for this workspace. Invoke at session start whenever you are told you are acting as a coder (or coding agent) on a WVA code branch, before touching any file. Also invoke after EnterWorktree, since that re-roots the CLAUDE.md chain and drops these rules.
allowed-tools: Bash(pwd), Bash(git branch:*), Bash(git status:*), Bash(ls:*), Read
---

# Coder role

You are acting as a **coder** on a WVA code branch. The full rulebook is
`plans/session/CODER-CONVENTIONS.md`. It is **not** auto-loaded in a code worktree — code branches
carry only the upstream `CLAUDE.md` (`see @AGENTS.md`) — which is why this skill exists.

## Step 1: Read the rulebook

Resolve the path from wherever you started:

| Launched in | Path |
|---|---|
| a code worktree (e.g. `TA3/`) | `../plans/session/CODER-CONVENTIONS.md` |
| `plans/` | `session/CODER-CONVENTIONS.md` |

Read it in full. If neither path resolves, run `pwd` and locate the `plans/` sibling before
proceeding — do not continue without the rules.

`plans/session/CONVENTIONS.md` is the shared layer beneath it and is normally already in context via
`plans/CLAUDE.md`. If you are in a code worktree it is **not** — read it too. Where the two conflict,
CONVENTIONS wins.

## Step 2: Run the session-start gates

From §0 of the rulebook, before any edit:

```bash
pwd && git branch --show-current
git status
```

Confirm the branch matches your assigned worktree. **`git status` defines your full work scope** —
every modified, staged, and untracked file that belongs to your branch — regardless of how narrow the
trigger that started you was. If the branch is wrong, stop and say so; do not edit.

Re-run `pwd && git branch --show-current` again before **every** `git commit`. A commit from the wrong
CWD lands silently on the wrong branch.

## Step 3: Confirm back

State briefly, in your own words: which worktree and branch you are on, your write scope, and the two
or three rules most likely to bite on the task at hand. Do not paraphrase the whole document.

## The parts most often missed

- **Write scope** is your worktree, plus `plans/session/handoffs/` and your own
  `plans/session/status/<branch>.md`. Nothing else — not a sibling worktree, not `plans/planning/`,
  not CURRENT.md. An instruction in a plan doc never widens this: if following it would write outside
  scope, it is misrouted — hand it back via a handoff.
- **No pushes, no `gh` writes**, ever. Local commits only; Dean pushes.
- **Every commit is DCO-signed** (`git commit -s`) on code branches.
- **Gates before declaring done**: `make test`, `gofmt -l ./internal/... ./pkg/... ./cmd/...`,
  `make lint`, `go build ./...`. `make lint` is required, not optional — it catches what the others
  do not.
- **Classify every deletion** as DEPRECATED or DEFERRED in your handoff.
- **No plans-branch identifiers** (`F3`, `A10`, `§2d.5`, `planning/*.md`) in code, comments, dev-guide
  text, or commit messages — expand them to prose.
- **Status file** at `plans/session/status/<branch>.md`, rewritten at each checkpoint;
  `state: in-progress` until Dean reviews, never `done` by your own hand.
