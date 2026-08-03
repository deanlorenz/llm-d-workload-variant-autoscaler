---
name: s-sync-current
description: Apply all pending sync-handoff files (sync__*.md) to CURRENT.md, mark them .DONE, and commit. Run this as the dedicated sync session from the plans worktree when Dean says "sync state". Invoke with /sync-current.
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(git -C plans:*), Bash(mv:*), Bash(rm:*), Read, Edit, TodoWrite
---

# Sync CURRENT.md

Read all pending `sync__*.md` handoffs, apply their updates to CURRENT.md, mark each
consumed file `.DONE`, `git rm` the .DONE files, and commit. No arguments.

**Consume `sync__*.md` only — never `plan__*.md`.** `sync__` handoffs are CURRENT-update
requests addressed to this session; `plan__` handoffs are tasks/decisions for a **working
planner** (there are many concurrent planner sessions). Consuming a `plan__` handoff robs
the intended planner of their work item. If a handoff is *mixed* (planner-task plus a
"suggested CURRENT updates" subsection), leave the whole `plan__` file alone — the planner
re-emits a clean `sync__` after folding. (Incident 2026-08-03: 16 `plan__` handoffs wrongly
consumed as sync input.)

The flat-directory protocol with prefix routing (`<recipient>__<topic>.md`) is defined
in `plans/session/CONVENTIONS.md` "Inter-agent communication" section.

---

## Step 1: List pending sync-handoffs

```bash
ls plans/session/handoffs/sync__*.md 2>/dev/null || echo "(none)"
```

Match only files with the `sync__` prefix and `.md` suffix — never `.md.DONE` (already
processed), never `plan__*.md` (planner-tasks — see the warning above), and never
`<other>__*.md` (triggers addressed to other agents).

If nothing matches, report "No pending sync-handoffs" and stop.

---

## Step 2: Read each handoff

For each `sync__<topic>.md`, read the full file. Every handoff opens with three header
lines:

```
from: <branch or agent name>
to: sync
session: <short topic name>
```

The body is freeform prose describing what to update in CURRENT.md. Read it carefully;
you will apply exactly what it describes.

If a file is missing the `from:` header or has no body content (looks like a stray
trigger that landed in `sync__`), flag it as malformed and skip it. If a `sync__` file's
`to:` header is not `sync`, it is misfiled — flag it and leave it for its real recipient
rather than consuming it.

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

**Edit by targeted section edits, never a wholesale rewrite of CURRENT.md** — a full-file
rewrite reconstructs from memory and silently drops items. If you must rewrite, diff
old-vs-new and account for every removed line before continuing.

---

## Step 3a: Prune, reconcile, and ref-check (keep CURRENT.md bounded)

After folding in handoffs, restore CURRENT.md to its Type-5 bounded shape (CONVENTIONS
Type 5). Targeted edits only — no wholesale rewrite. **CURRENT.md holds live state only;
landed/closed history lives in the companion archive `session/history.md`** (TOC-indexed,
fetch-on-demand — see CONVENTIONS Type 5).

1. **Recent-activity window.** Keep ≈5 active-WIP abstracts in the head. When an item's work has
   landed (merged/closed) and its substance is in git or a permanent doc, **move it out of
   CURRENT.md into `session/history.md` → *Activity log*** (verify-or-copy-then-delete, step 5) —
   do not let a compressed tail accrete in CURRENT.md.
2. **Reconcile against PR Status.** Drop Blocked-on / Next-steps entries that PR Status shows
   as done or contradicts (e.g. "awaiting CI" after CI ran). PR Status is the source of truth
   for branch/PR state.
   - **Move merged/closed PR rows to `session/history.md` → *PR Status*.** CURRENT.md's PR-Status
     table keeps only open / in-flight / actionable rows. Likewise move landed multi-PR *mission*
     blocks to history.md → *Mission* sections, leaving at most a one-line pointer in CURRENT.md.
3. **Backlogs stay refs.** Issues-to-Open items are one-line title + `→ Fnn`/doc ref, not prose.
4. **Ref-check.** Scan CURRENT.md for `→ Fnn`/`→ Ann` and doc-section refs; for any doc
   changed in this sync, confirm the anchor still resolves and fix it if it renumbered.
5. **No-loss guard (verify-or-copy-then-delete).** Never remove a forward-looking TODO that
   has no home elsewhere. If a handoff or a prune would drop something with no permanent home,
   **stop and surface it** to the user rather than deleting. When moving items to
   `session/history.md`, copy + verify the content is present there **before** deleting from
   CURRENT.md, then run `bash plans/scripts/toc-refresh.sh session/history.md` to re-index.

---

## Step 4: Mark processed handoffs `.DONE`

For each handoff that was successfully applied, atomic-rename it:

```bash
mv plans/session/handoffs/sync__<topic>.md plans/session/handoffs/sync__<topic>.md.DONE
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
git -C plans ls-files --error-unmatch session/handoffs/sync__<topic>.md.DONE
```

- Exit 0 → tracked. Use `git -C plans rm session/handoffs/sync__<topic>.md.DONE`.
- Non-zero → untracked (was a new handoff that never got committed). Use
  `rm plans/session/handoffs/sync__<topic>.md.DONE`.

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

- **Invoked only from the dedicated sync session.** Per CONVENTIONS "single-writer model,"
  only one designated session runs this skill; every other session (planner instances and
  auto-mode included) submits handoffs instead of syncing. Handoffs need not be committed by
  their sender — this skill reads uncommitted handoff files directly, and Step 5 already
  removes untracked `.DONE` files via `rm` rather than `git rm`.
- Planner-tasks and triggers (`<recipient>__*.md` where recipient ≠ `sync` — i.e.
  `plan__*.md`, coder-branch triggers, `review__*.md`) are not the sync skill's business.
  Leave them alone; their recipients process them.
- Status files at `plans/session/status/<branch>.md` are not handoffs. Leave them
  alone; they are continuously rewritten by their owning coder.
- **Never rewrite CURRENT.md wholesale.** Edit section by section; a blind rewrite silently
  drops items. Keep it bounded per CONVENTIONS Type 5 (rolling-window recent activity,
  refs-not-prose backlogs, one source per task). The Step 3a prune is part of every sync,
  not a separate effort.
