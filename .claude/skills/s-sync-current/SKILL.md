---
name: s-sync-current
description: Apply all pending handoff files to CURRENT.md, then delete the processed files and commit. Run this as plan-agent from the plans worktree when Dean says "sync state". Invoke with /sync-current.
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(git -C plans:*), Bash(rm:*), Read, Edit, TodoWrite
---

# Sync CURRENT.md

Read all handoff files, apply their updates to CURRENT.md, delete the processed files, and commit. No arguments.

---

## Step 1: List handoff files

```bash
ls plans/session/handoffs/ 2>/dev/null || echo "(none)"
```

If the directory is empty or does not exist, report "No pending handoffs" and stop.

---

## Step 2: Read each handoff file

For each `.md` file found, read its full contents. Every handoff opens with two header lines:

```
to: sync-current
session: <session name>
```

The body is freeform — prose, lists, or structured content describing what to update in
CURRENT.md. Read it carefully; you will apply exactly what it describes.

If a file is missing the `to: sync-current` header, flag it as malformed and skip it.

---

## Step 3: Apply updates to CURRENT.md

For each valid handoff, edit `plans/session/CURRENT.md` to apply what the handoff describes.
This may include any combination of:

- Creating or updating a `## Session in progress:` header
- Adding, updating, or removing rows in the PR Status table
- Adding or removing items in Blocked on or Next steps
- Adding, updating, or removing entries in the `## Pending handoffs` table
- Adding or updating a per-task section with work items and progress
- Any other CURRENT.md change the handoff specifies

Apply updates from all handoffs before moving to cleanup. If two handoffs affect the same
section, apply them in file-system order and note any conflicts to the user.

---

## Step 4: Delete processed handoff files

For each handoff that was successfully applied:

```bash
# tracked files:
git -C plans rm session/handoffs/<name>.md

# untracked files (never committed):
rm plans/session/handoffs/<name>.md
```

Determine whether each file is tracked:
```bash
git -C plans ls-files --error-unmatch session/handoffs/<name>.md
```
Exit 0 → tracked, use `git rm`. Non-zero → untracked, use plain `rm`.

---

## Step 5: Commit

```bash
git -C plans add session/CURRENT.md
git -C plans commit -m "session: sync CURRENT.md pending handoffs"
```

If CURRENT.md has no changes and no handoff files were deleted, report
"CURRENT.md already up to date" and skip the commit.

Print the commit SHA or the up-to-date message when done.
