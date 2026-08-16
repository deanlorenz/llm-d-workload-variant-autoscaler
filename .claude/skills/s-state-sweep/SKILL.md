---
name: s-state-sweep
description: Reconcile the source of truth against every file backing an open item — by re-opening those files, not from memory. Medium depth; run after finishing a batch of work or when a document is supposed to be current. Dean-invoked only. Invoke with /s-state-sweep [scope].
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(pwd), Bash(git branch --show-current), Bash(git status:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git show:*), Bash(git diff:*), Read, Write, Edit, TodoWrite, AskUserQuestion
---

<!-- user-approved-settings-change: grants reviewed and narrowed by Dean 2026-08-15.
     Design: planning/state-commands-design.md (§ 5 write scope, § 8 grants).

     Plain CWD git, no `-C`: a planner is already in `plans`; a coder sweeping its own status file
     operates in its own worktree. `git -C plans` is a RELATIVE path that only resolves from the
     container directory, so it silently fails for a coder — that was an earlier draft's bug.

     Deliberately absent, do not re-add:
       - git wildcards, rm / checkout / stash / reset / push — read-only history verbs plus add/commit only.
         (git show / log / diff are the read-only way to reach historical content; never checkout.)
       - mv — renaming a handoff to .WIP/.DONE is a session ACCEPTING and FINISHING a task.
         A state command reports what looks consumable; the accepting is a session's own act. -->

# state-sweep

**Depth:** medium. **Question answered:** *"Does the source of truth actually reflect every open item?"*

**Dean-invoked only.** A sweep reads broadly and may restructure; its whole value is being an accountable
checkpoint a human asked for. You may *suggest* it whenever you suspect drift — and should — but never run
it unasked.

**A sweep that reads zero files is a park. Label it honestly.**

**Arguments:** `$ARGUMENTS` — optional scope (a topic, a branch, a doc name). Default: the current task.
Sweep is scoped to the **current task**, not the whole artifact — that is `/s-state-consolidate`.

---

## Why the re-read is the whole command

An agent asked to "fold everything into the doc" once produced a confident, well-organized document written
**from its live context and memory**, without re-opening the files that held the content. It read one file,
wrote, and reported the job done. A later pass that actually read all nine source files found whole
decisions missing — not nuances.

**Only the source list distinguishes a real sweep from a well-written summary of what you happen to
remember.** Memory and conversational context are not sources.

"I wrote this an hour ago so I know what's in it" is the specific thought this command exists to override.
Another session may have edited it since; your own earlier write may have been partial; and after a
compaction your recollection of it is a summary of a summary.

---

## Step 1 — identity, scope, and the editing lock

<!-- user-approved-settings-change: relative `git -C plans` replaced with plain CWD git 2026-08-15.
     Grants already updated to match; see the frontmatter note. -->

```bash
pwd; git branch --show-current
git status --short
```

Determine your **role** and **owned_doc** (see `/s-state-park` Step 1 — the write-scope split between
planner/reviewer and coder applies identically here).

**Check the lock before planning any shared-state write:**

```bash
ls plans/session/handoffs/current__editing.md.WIP 2>/dev/null
```

If that sentinel exists, the sync session is mid-write on CURRENT.md. Do not plan any CURRENT.md change —
route everything through a `sync__` handoff and note the lock in your report.

## Step 2 — enumerate every open item

List every open item in scope, from the durable record rather than recollection:

- threads and TODOs in your own plan doc
- unresolved questions and parked decisions
- open handoffs addressed to you: `ls plans/session/handoffs/<your-token>__*.md`
- your own status file's `blocked_on` / `current_step`
- what CURRENT.md currently claims about this scope

Write the list down before reading anything. It is the checklist the source report is scored against.

## Step 3 — re-read every backing file

**Open the files.** Not summaries, not memory, not your own earlier writes trusted from recall.

For each item from Step 2, read the file that backs it. For a large Type 3, use its own Reading Protocol —
fetch by the TOC's line ranges rather than reading whole. For historical content use read-only git:

```bash
git show <rev>:<path>        # never git checkout
git log -p -- <path>
```

If a file in scope is genuinely unchanged and you can show it (`git log -1 --format=%H -- <path>` matching
what your last sweep recorded), you may skip it — but it goes in the report's **Not read** section with
that reason. A skip you cannot justify is a gap you are hiding.

## Step 4 — reconcile, in both directions

For each item, two distinct questions:

1. **In the file but missing from the source of truth** — content that exists on disk but the doc never
   absorbed. The common case, and the one Step 3 exists to find.
2. **In the source of truth but stale relative to the file** — a claim the doc still makes that the file
   has since contradicted. Counts, inventories, tips, SHAs, "nothing pushed", "no PR open", "unclaimed".
   These read as authoritative and are the most damaging when wrong.

Direction 2 deserves particular care with **refs**: a `sync__` handoff is true as of authoring, not
consumption, and design-doc `Fnn`/`Ann` anchors renumber. Re-validate any ref you touch, and check the
branch's newer commits before trusting a "tip" or a "nothing pushed" claim.

## Step 5 — fix the gaps, within your write scope

**The ordering is strictly one-way: state must already exist in its permanent home before any text
elsewhere is reduced.** Verify-or-copy-then-delete, per item. Never trim to hit a length — a length target
rewards deleting state that has nowhere to go.

| Gap | Action |
|---|---|
| Missing from **your own** plan doc / status file | Fix it directly. |
| Missing from or stale in **CURRENT.md** / PR Status / shared `session/` state | ⛔ Do not edit. Emit `sync__<topic>.md` describing exactly what should change. |
| Missing from **another owner's** plan doc | ⛔ Do not edit — the owner may be editing it now, and their uncommitted work is invisible to you. Emit `plan__<topic>.md`. |
| A detail in CURRENT.md with **no permanent home yet** | Leave the CURRENT.md text uncompressed. Do **not** write it into someone else's plan doc to make room. Emit `plan__` asking the owner to fold it in; compression waits for them. |
| A handoff that looks consumable | Report it. Do **not** rename it — accepting work is a session's act, not a state command's. |
| Something needing a decision | `AskUserQuestion`, or record it as an open question. Never resolve it in passing. |

`session/history.md` is sync-owned; a sweep does not move landed items into it.

## Step 6 — commit

<!-- user-approved-settings-change: relative `git -C plans` replaced with plain CWD git 2026-08-15. -->

```bash
git status --short
```

Read that output first. If it shows modifications you did not make, another session is in this tree — stage
only your own files and say so. Explicit per-file pathspecs; never `add -A`, never `add .`, never a bare
directory.

```bash
git add <explicit paths>
git commit -m "state(sweep): <scope> — <what was reconciled>"
```

## Step 7 — emit the source report (MANDATORY)

**Without this, the command has not been performed — it has only been claimed.**

```
state-sweep — <scope>

Open items enumerated: <n>
Sources read this pass:
  - <path> — <item it backs> — <what reconciling it changed, or "consistent">
Not read (and why):
  - <path> — <unchanged since <sha> / out of scope / owned by another session / lock held>
Gaps found and fixed:
  - <doc> — <what was missing or stale, and what it now says>
Gaps found, NOT fixed (out of my write scope):
  - <doc> — <what is wrong> → handoff session/handoffs/<sync|plan>__<topic>.md
Refs re-validated:
  - <ref> — <resolves | fixed to X | dead, flagged>
Handoffs emitted:
  - <path> — <one line>
Consumable handoffs noticed (NOT renamed — accepting is a session's act):
  - <path>
Open questions raised:
  - <question> — <where recorded>
Committed:
  - <sha> <subject>
```

If you read zero files, the report must say so, and you must label the pass a park rather than a sweep.

<!-- user-approved-settings-change: note added 2026-08-17 (Dean, correcting an earlier draft of this
     step that required committing the full report) -- sweep's job is fixing drift in the docs it
     touches, and that fix already lands durably wherever Step 5 wrote it. The report is a receipt, not
     a second copy of state. Grants unchanged. -->

**Receipt, not a second copy of state (Dean, 2026-08-17).** Sweep's job is fixing drift in the docs it
touches — that fix already lands durably wherever Step 5 wrote it. The report itself is a short
confirmation that the pass ran, not state needing its own permanent home the way park's report does
(park's whole job *is* persisting state, so its own report is the record of what got flushed). One line
in your status file — `swept <scope>, <n> gaps fixed, see commit <sha>` — is enough; do not duplicate the
full report there.

---

## Notes

- A sweep reconciles **files against files**. Content discussed in conversation but never filed anywhere is
  the class of gap sweeps miss by construction — that is `/s-state-consolidate` Step 1.
- A sweep never closes a thread and never marks a handoff `.WIP`/`.DONE`. Closing needs Dean's explicit
  confirmation.
- Tidy by targeted edits, never a blind wholesale rewrite. A full-file rewrite reconstructs from memory and
  silently loses whatever does not fit the template — the same failure as writing from recollection. If you
  must rewrite, diff old against new and account for every removed line before committing.
- CURRENT.md is updated **last** (by sync, via your handoff), after the docs it references are correct.
