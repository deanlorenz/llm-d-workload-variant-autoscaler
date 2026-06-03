---
name: s-sync-current
description: Apply all pending plan-handoff files to CURRENT.md, mark them .DONE, and commit. Run this as plan-agent from the plans worktree when Dean says "sync state". Invoke with /sync-current.
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(git -C plans:*), Bash(mv:*), Bash(rm:*), Read, Edit, TodoWrite
---

# Sync CURRENT.md

Read all pending `plan__*.md` handoffs, apply their updates to CURRENT.md, mark each
consumed file `.DONE`, `git rm` the .DONE files, and commit. No arguments.

The flat-directory protocol with prefix routing (`<recipient>__<topic>.md`) is defined
in `plans/session/CONVENTIONS.md` "Inter-agent communication" section.

---

## Step 1: List pending plan-handoffs

```bash
ls plans/session/handoffs/plan__*.md 2>/dev/null || echo "(none)"
```

Match only files with the `plan__` prefix and `.md` suffix — never `.md.DONE` (already
processed) and never `<other>__*.md` (triggers addressed to other agents).

If nothing matches, report "No pending plan-handoffs" and stop.

---

## Step 2: Read each handoff

For each `plan__<topic>.md`, read the full file. Every handoff opens with two header
lines:

```
from: <branch or agent name>
session: <short topic name>
```

The body is freeform prose describing what to update in CURRENT.md. Read it carefully;
you will apply exactly what it describes.

If a file is missing the `from:` header or has no body content (looks like a stray
trigger that landed in `plan__`), flag it as malformed and skip it.

---

## Step 3: Apply updates to CURRENT.md

For each valid handoff, edit `plans/session/CURRENT.md` to apply what the handoff
describes. This may include any combination of:

- Creating or updating a "Last session" / "Session in progress" header
- Adding, updating, or removing rows in the PR Status table
- Adding or removing items in Blocked on / Next steps
- Adding, updating, or removing entries in the `## Pending handoffs` table
- Adding or updating a per-task section with work items and progress
- Any other CURRENT.md change the handoff specifies

Apply updates from all handoffs before moving to cleanup. If two handoffs affect the
same section, apply them in file-system order and note any conflicts to the user.

CURRENT.md has per-task sections — never overwrite a sibling task's state unless the
handoff explicitly says to.

---

## Step 4: Mark processed handoffs `.DONE`

For each handoff that was successfully applied, atomic-rename it:

```bash
mv plans/session/handoffs/plan__<topic>.md plans/session/handoffs/plan__<topic>.md.DONE
```

The .DONE marker indicates the file has been consumed; it stays on disk until the
commit step removes it.

---

## Step 5: Stage CURRENT.md and remove .DONE files

```bash
git -C plans add session/CURRENT.md
```

For each `.md.DONE` produced this run, remove it from the working tree and the index.
Determine whether the file is currently tracked:

```bash
git -C plans ls-files --error-unmatch session/handoffs/plan__<topic>.md.DONE
```

- Exit 0 → tracked. Use `git -C plans rm session/handoffs/plan__<topic>.md.DONE`.
- Non-zero → untracked (was a new handoff that never got committed). Use
  `rm plans/session/handoffs/plan__<topic>.md.DONE`.

Tracked source files (the originals before the rename) are removed automatically by
`git rm` since the path no longer exists.

---

## Step 6: Commit

```bash
git -C plans commit -m "session: sync CURRENT.md pending handoffs"
```

If CURRENT.md has no changes and no handoffs were processed, report "CURRENT.md
already up to date" and skip the commit.

Print the commit SHA or the up-to-date message when done.

---

## Notes

- Triggers (`<recipient>__*.md` where recipient ≠ `plan`) are not the sync skill's
  business. Leave them alone; their recipients process them.
- Status files at `plans/session/status/<branch>.md` are not handoffs. Leave them
  alone; they are continuously rewritten by their owning coder.
