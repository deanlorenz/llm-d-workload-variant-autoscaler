---
name: s-sync-current
description: Apply all pending sync-handoff files (sync__*.md) to CURRENT.md, mark them .DONE, and commit. Run this as the dedicated sync session from the plans worktree when Dean says "sync state". Invoke with /sync-current.
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(git -C plans:*), Bash(mv:*), Bash(rm:*), Read, Write, Edit, TodoWrite
---

# Sync CURRENT.md

Read all pending `sync__*.md` handoffs, apply their updates to CURRENT.md, mark each
consumed file `.DONE`, remove them, and commit. **Preserve the batch first (Step 1a) — a
handoff may exist only in the working tree, and consuming one that was never committed
destroys it permanently.** No arguments.

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

## Step 1a: Preserve the batch as received, before touching anything

Senders are permitted to leave handoffs uncommitted (CONVENTIONS: *"Handoffs need not be
committed by the submitting session"*), so a handoff may exist **only** in the working tree.
Commit the batch before reading or applying any of it:

```bash
git -C plans add session/handoffs/sync__*.md
git -C plans commit -m "session: preserve sync handoff batch as received"
```

This must be its **own commit, strictly earlier than the commit that removes the files.** A
single commit that both adds and deletes a path leaves the content in no tree at all, so the
handoff would be exactly as unrecoverable as before. With this commit in place, recovery is:

```bash
git -C plans log --diff-filter=D -- session/handoffs/     # find the removing commit
git -C plans show <commit>^:session/handoffs/sync__<topic>.md
```

Preserving at intake rather than at consume time also means a session that dies mid-sync
loses nothing. If `git add` finds nothing to stage, every handoff in the batch was already
committed by its sender — proceed.

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
6. **Plan docs are validate-only — never edit them from here.** Every in-flight Type 3 / Type 1 has
   an owner who may be editing it at this moment, so this skill may only *check* that content is
   present in that doc. If an item's detail has no home yet, **do not add it to the plan doc**:
   leave the CURRENT.md text uncompressed and write a `plan__<topic>.md` handoff asking the owner to
   fold it in, then move on. Compression of that item waits for the owner. `session/history.md` is
   the sole exception, being sync-owned. The underlying model: the planner captures state in the
   Type 3 as the work proceeds, and **CURRENT.md points back to the plan rather than storing state.**

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

The `.DONE` suffix is a signalling marker for concurrent sessions, not an artifact worth
keeping. Its content is already preserved by Step 1a's commit, so remove it and stage the
deletion of the original path:

```bash
rm plans/session/handoffs/sync__<topic>.md.DONE
git -C plans add -A session/handoffs/
```

`git add -A` stages the deletion of each original tracked path, which Step 4 renamed away.
Removing the `.DONE` copy first is what keeps it from being staged as a new file.

**Never resolve an untracked handoff with a bare `rm`.** That was this skill's previous
behavior and it destroyed content that had never entered git — the "handoff deleted, we no
longer know what happened and cannot recover" failure. Step 1a exists precisely so that no
handoff is still untracked by the time you reach this step; if one is, go back and preserve
it rather than deleting it.

---

## Step 6: Commit

```bash
git -C plans commit -m "session: sync CURRENT.md pending handoffs"
```

If CURRENT.md has no changes and no handoffs were processed, report "CURRENT.md
already up to date" and skip the commit.

Print the commit SHA or the up-to-date message when done.

---

## Step 6a: Push `plans` to origin, only if it is a clean fast-forward

Dean's standing instruction (2026-08-12): push after every sync, but **only** when it is a
plain fast-forward with no divergence — a fast-forward push is harmless and reversible from
every other session's point of view (nothing is rewritten, nobody's history changes under
them), so it needs no per-push confirmation the way a force-push or a rewrite would.

```bash
git -C plans rev-list --left-right --count origin/plans...plans
```

Read the two numbers as `<behind> <ahead>`. Push **only if `<behind>` is 0** — i.e. `origin/plans`
has nothing this branch lacks. If `<behind>` is nonzero, `plans` has diverged from `origin/plans`
(someone force-pushed, or this branch's local history was rewritten) — do **not** push; that
is exactly the "no push without explicit confirmation" case from CONVENTIONS, and a divergence
here is itself worth surfacing to Dean rather than silently skipping.

```bash
git -C plans push origin plans
```

This is a plain `push`, never `--force` / `--force-with-lease` — if the fast-forward check
above ever fails to prevent a rejected push for some other reason, stop and report rather than
retrying with force.

Report the resulting SHA range (e.g. `abc1234..def5678`) or "already up to date" if there was
nothing to push (this sync made no commits, or `plans` was already level with origin).

---

## Step 7: Record the sync baseline for the concurrent-sync watcher

`scripts/sync-current-watch.sh` (started via the Monitor tool) polls for pending `sync__*.md`
handoffs and checks whether `CURRENT.md` has moved since this skill's last known-good commit —
if unchanged, it signals "safe to auto-run this skill"; if changed by someone else, it signals
a possible concurrent sync session and does **not** auto-anything. That check depends on this
skill recording its own tip after every successful run:

```bash
current_sha=$(git -C plans log -1 --format=%H -- session/CURRENT.md)
```

```
{
  echo "last_check: <ISO timestamp>"
  echo "watcher_pid: <unchanged from the file, or 0 if the watcher isn't running>"
  echo "state: watching"
  echo "current_step: idle"
  echo "last_known_current_sha: $current_sha"
  echo ""
  echo "## Notes"
  echo "baseline updated by /s-sync-current after its own commit"
} > plans/session/status/sync-current-watch.md
```

Skip this step if Step 6 made no commit (nothing changed, so the baseline is already correct).

<!-- user-approved-settings-change: doc-only correction, 2026-08-12, no permission/allowed-tools touched -->
**If the watcher is running, restart it after writing the new baseline.** It reads
`last_known_current_sha` from the status file only once, at its own startup, and holds that
value in memory for its entire process lifetime — every poll after that just rewrites the
in-memory value back into the file. Editing the file while the process is still running does
NOT update what it's actually checking against; the next poll silently overwrites your edit with
the stale value (observed 2026-08-12: this stomped the baseline update immediately after this
step, because the old process outlived the edit). Kill it (`pgrep -f 'sync-current-watch[.]sh$'`
→ `kill`), then start a fresh one via the Monitor tool so it re-reads the file on its own startup.

---

## Notes

- **Invoked only from the dedicated sync session.** Per CONVENTIONS "single-writer model,"
  only one designated session runs this skill; every other session (planner instances and
  auto-mode included) submits handoffs instead of syncing. Handoffs need not be committed by
  their sender — this skill reads uncommitted handoff files directly, which is exactly why
  **Step 1a commits the batch as received before anything else touches it.**
- Planner-tasks and triggers (`<recipient>__*.md` where recipient ≠ `sync` — i.e.
  `plan__*.md`, coder-branch triggers, `review__*.md`) are not the sync skill's business.
  Leave them alone; their recipients process them.
- Status files at `plans/session/status/<branch>.md` are not handoffs. Leave them
  alone; they are continuously rewritten by their owning coder.
- **Never rewrite CURRENT.md wholesale.** Edit section by section; a blind rewrite silently
  drops items. Keep it bounded per CONVENTIONS Type 5 (rolling-window recent activity,
  refs-not-prose backlogs, one source per task). The Step 3a prune is part of every sync,
  not a separate effort.
