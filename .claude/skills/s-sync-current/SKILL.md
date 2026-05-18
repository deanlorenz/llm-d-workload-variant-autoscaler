---
name: s-sync-current
description: Read all pending handoff files in plans/session/handoffs/ and update the Pending handoffs section in CURRENT.md to reflect current agent pipeline state. Run this whenever you want CURRENT.md to reflect completed agent work. Invoke with /sync-current.
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(git -C plans:*), Read, TodoWrite
---

# Sync CURRENT.md

Read all handoff files and update CURRENT.md. No arguments.

---

## Step 1: List handoff files

```bash
ls plans/session/handoffs/ 2>/dev/null || echo "(none)"
```

If the directory is empty or does not exist, report "No pending handoffs" and stop — nothing to sync.

---

## Step 2: Read each handoff file

For each `.md` file found, read it and extract the four fields:

```
to: <agent>       # plan-agent | coder | reviewer
doc: <path>       # relative path to the output doc
status: <status>  # FINAL | READY
note: <text>      # one-line description
```

Also verify that the referenced `doc` exists in the `plans` worktree:

```bash
ls plans/<doc>
```

If the doc does not exist, flag that handoff as broken (the producing agent may not have committed yet).

---

## Step 3: Build the pending handoffs summary

Group valid handoffs by target agent. Produce a table like:

```
| Agent | Doc | Status | Note |
|---|---|---|---|
| plan-agent | planning/TA-TA3-review.md | FINAL | TA3 code review complete — 2 bugs, ready for planning |
| coder | planning/engine-PR6-plan.md | READY | Engine PR-6 implementation plan |
```

Report broken handoffs separately (doc missing), so the user knows an agent may not have finished committing.

---

## Step 4: Update CURRENT.md

In `plans/session/CURRENT.md`, find the `## Pending handoffs` section (note plural — rename from `## Pending handoff` if the old singular form exists). Replace its contents with the current table from Step 3, or add the section at the end of the file if it does not exist.

If there are no valid handoffs, write:

```
## Pending handoffs

None.
```

---

## Step 5: Delete processed handoff files

For each handoff file that was successfully merged (doc existed, no errors):

```bash
# tracked files:
git -C plans rm session/handoffs/<name>.md

# untracked files (never committed — just delete):
rm plans/session/handoffs/<name>.md
```

Determine whether each file is tracked with `git -C plans ls-files --error-unmatch session/handoffs/<name>.md`.
If the command exits 0 the file is tracked; use `git rm`. If it exits non-zero, use plain `rm`.

---

## Step 6: Commit

```bash
git -C plans add session/CURRENT.md
git -C plans commit -m "session: sync CURRENT.md pending handoffs"
```

If CURRENT.md has no changes and no handoff files were deleted, report "CURRENT.md already up to date" and skip the commit.

Print the commit SHA or the up-to-date message when done.
