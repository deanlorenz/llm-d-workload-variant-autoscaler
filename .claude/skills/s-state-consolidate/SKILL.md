---
name: s-state-consolidate
description: Deepest state command — everything a sweep does, plus re-reading the conversation itself, verifying claims against reality, hunting staleness and contradiction, and deciding placement deliberately (archiving is a valid outcome). Scoped to the whole artifact, not just the current task. Run at milestones, before long breaks, or when an artifact is about to be handed to someone else. Dean-invoked only. Invoke with /s-state-consolidate [scope].
disable-model-invocation: true
allowed-tools: Bash(ls:*), Bash(find:*), Bash(grep:*), Bash(pwd), Bash(git branch --show-current), Bash(git status:*), Bash(git add:*), Bash(git commit:*), Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git ls-remote:*), Read, Write, Edit, TodoWrite, AskUserQuestion, WebFetch
---

<!-- user-approved-settings-change: grants reviewed and narrowed by Dean 2026-08-15.
     Design: planning/state-commands-design.md (§ 4 consolidate, § 5 write scope, § 8 grants).

     WebFetch is here and NOT on park/sweep: consolidate's verify-claims step checks an API/flag/package
     against its own official documentation rather than recollection (per Dean's global rule).

     Plain CWD git, no `-C`: `git -C plans` is a RELATIVE path that only resolves from the container
     directory, so it silently fails from a worktree — that was an earlier draft's bug.

     Deliberately absent, do not re-add:
       - git wildcards, rm / checkout / stash / reset / push — read-only history verbs plus add/commit only.
       - mv — renaming a handoff to .WIP/.DONE is a session ACCEPTING and FINISHING a task.
         "Archiving is a valid outcome" here means moving TEXT between docs this session owns and
         reporting the rest. Consolidate cannot delete or rename a file. -->

# state-consolidate

**Depth:** deepest. **Question answered:** *"Is everything captured, correct, in the right place, and free
of cruft?"* Housekeeping, not just capture.

**Dean-invoked only.** It reads broadly and restructures. You may *suggest* it — and should, at a milestone
or when you smell drift — but never run it unasked.

**Scope is the whole artifact**, and may legitimately touch things the current task never mentioned. That
is the difference from `/s-state-sweep`.

**Arguments:** `$ARGUMENTS` — optional scope (an artifact, a mission, a doc set). Default: the artifact your
current task belongs to.

---

## Relationship to the other two

Everything in `/s-state-sweep` (enumerate open items → re-open every backing file → reconcile both
directions → fix within write scope → source report), **plus** Steps A–E below.

Read `/s-state-sweep` and perform it first. Its rules carry over unchanged: the re-read is mandatory,
memory is not a source, write scope is bounded by role, CURRENT.md and other owners' docs are handoffs
rather than edits, verify-or-copy-then-delete per item, targeted edits over wholesale rewrite.

---

## Step A — re-read the conversation itself

A sweep reconciles **files against files**. Content discussed but never filed anywhere is invisible to it by
construction. That is this step's entire job.

Walk the conversation (including compaction summaries, and the tool results of any spawned agent) for
content with no home on disk: decisions, corrections and retractions, rejected approaches, Dean's rulings,
armed footguns, TODOs. Route each per `/s-state-park` Step 4.

If a compaction happened, treat everything before it with suspicion — you are reading a summary, and the
summarizer drops exactly the kind of detail this step hunts. Where a pre-compaction claim matters, verify it
against a file rather than the summary.

## Step B — verify claims against reality

Recollection is not verification. For each load-bearing claim in the artifact:

- **Does that file still exist?** `ls` it. Does that line range still contain what the ref says?
- **Does that function, flag, field, or config key still exist?** `grep` for it. Renames and refactors
  silently invalidate prose.
- **Does that API / package / CLI flag actually exist?** Check its **official public documentation** via
  `WebFetch` — not inference, not training knowledge. This is a standing rule, not a consolidate-specific one.
- **Is that SHA / tip / PR state still current?** A "tip is X", "nothing pushed", "no PR open", "unclaimed"
  claim is true as of authoring, not as of now. `git log`, `git ls-remote --tags`, and the branch's newer
  commits are the check.
- **Do those counts and inventories still hold?** "16 rows", "28 commits", "7 cells", "three findings" —
  re-count. Inventories that were true once are a recurring class of quiet error.

Correct or remove anything that cannot be verified, and **name in the report which claims you checked**. A
claim you did not check must not be reported as verified.

## Step C — hunt staleness, duplication, and contradiction

- **Two statements of the same rule that have drifted apart.** The dangerous shape: both read as
  authoritative, and a reader follows whichever they hit first. When you find one, determine which is
  actually load-bearing (which is corroborated by mechanism, other docs, or a dated decision) and fix the
  other — do not silently pick.
- **A "resolved" item whose resolution was later reversed.** Reversals often land as new prose elsewhere
  while the original "resolved" line survives untouched.
- **A retraction that did not propagate.** The retracted claim gets re-cited from wherever it still stands.
- **Duplicated state with no declared authority.** Two copies where neither says which leads. Declare one
  canonical and make the other a pointer.
- **Dead refs.** Renumbered anchors, moved sections, superseded docs still linked as live.

For anything you fix, say what it said before. A silent correction is indistinguishable from having missed it.

## Step D — decide placement deliberately

For each piece of content, ask where it belongs — **and "nowhere" is a legitimate answer.**

| Destination | When |
|---|---|
| the source of truth | live state a reader needs now |
| a history / trace file | landed, closed, superseded — substance already in git or a permanent doc |
| memory | a durable fact about Dean, the project, or a preference |
| nowhere | already captured elsewhere, or genuinely irrelevant now |

**Consolidation that only ever adds is hoarding.** Removing text is expected. But the ordering is one-way
and absolute: **the content must already exist in its permanent home before the text here is reduced.**
Verify it is there — by reading the target, not by remembering putting it there.

Two hard limits on "archiving" in this workspace:

- **This command cannot delete or rename a file.** Archiving means moving *text* between docs this session
  owns, and reporting the rest. Retiring a file is a separate, human-directed act.
- **`session/history.md` is sync-owned.** Moving a landed item into it is a `sync__` handoff, not an edit.

## Step E — state what remains genuinely unresolved

An open question recorded as open is captured. An open question quietly dropped is not — and it reads
exactly like a resolved one.

List every item that is still open, with **who owns it** and **what would close it**. Include:

- questions awaiting Dean's decision
- work released but unclaimed (name it unclaimed, so nobody reads it as abandoned)
- armed footguns still armed
- anything you found in Steps A–C that needs a decision rather than filing

**A thread with no session running is still WIP** — so long as its docs and memories live, it is fully
resumable. Never let a reduced entry imply an abandoned thread.

---

## Source report (MANDATORY, extends the sweep report)

**Without this, the command has not been performed — it has only been claimed.**

Emit the full `/s-state-sweep` report, plus:

```
state-consolidate — <artifact>

Conversation re-read: <yes — including N compaction summaries | no, and why>
Content found only in conversation:
  - <item> → <where filed>

Claims verified:
  - <claim> — <verified how: ls / grep / git / WebFetch <url>> — <holds | corrected to X | removed>
Claims NOT verified (and why):
  - <claim> — <no way to check / out of scope> — left as-is, flagged

Staleness / duplication / contradiction found:
  - <what it said> → <what it says now> — <why this version is the load-bearing one>

Removed or archived (and why):
  - <text> — from <doc> — verified present in <permanent home> — <how verified>
  - (or: nothing removed — and whether that is correct or hoarding)
Could not archive (no permanent home yet):
  - <text> — left uncompressed in place → handoff to <owner>
File-level retirement suggested (NOT performed — this command cannot delete or rename):
  - <path> — <why it looks retirable>

Genuinely unresolved:
  - <item> — owner: <who> — closes when: <what>
```

---

## Notes

- Never closes a thread, never marks a handoff `.WIP`/`.DONE`. Closing needs Dean's explicit confirmation;
  accepting work is a session's own act.
- Tidy by targeted edits. A wholesale rewrite reconstructs from memory — the exact failure this whole family
  of commands exists to prevent. If you must rewrite, diff old against new and account for every removed
  line before committing.
- If consolidate surfaces something needing a decision, it becomes an open question or a new thread. It does
  not get resolved silently in passing.
- CURRENT.md is updated last, by sync, via your handoff — after the docs it references are correct.
