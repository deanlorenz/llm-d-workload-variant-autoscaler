from: planner (auto-mode session)
session: sync-single-writer-model

## What Dean decided (2026-07-28) — new sync governance model

Too many planner instances were running concurrently, creating risk of inconsistent
CURRENT.md edits. Dean established a single-writer model. The **dedicated sync session**
should encode this into the canonical docs (this is a doc-update task for the sync session,
per Dean's "let the dedicated sync session handle the doc updates").

### The rule
1. **One dedicated sync session is the only writer of CURRENT.md** (and other canonical
   `plans/session/` shared state). Dean invokes `/sync-current` from that one session.
2. **Every other session — including other planner instances — only submits handoffs.**
   They never edit CURRENT.md directly.
3. **Auto-mode plan sessions must NOT invoke `/sync-current`** (nor should any other session
   type). Only the designated sync session runs it. If Dean manually invokes sync elsewhere,
   that is his call.
4. **The existing `current__editing.md.WIP` sentinel is the gate** — no new mechanism needed.
   The sync session holds it while writing CURRENT.md; any session that sees `.WIP` refuses to
   sync and writes a handoff instead.
5. **Handoffs no longer need to be committed by the submitting session.** All sessions share
   the same `plans/` worktree filesystem, so the sync session sees uncommitted handoff files
   directly. Just drop the file in `plans/session/handoffs/`; the sync session reads, applies,
   and commits/consumes them (rename to `.DONE`, `git rm` in the sync commit) in its batch.
6. **Handoff naming stays simple:** keep `plan__<topic>.md` / `<recipient>__<topic>.md`. No
   timestamps or random suffixes (a timestamp would fork a sender's in-place revision into a
   new file and lose its identity). Descriptive topics + the rename state machine are the
   mechanism. Extend the rename states only if a real concurrent-processing collision ever
   appears — there has been none to date.

### Docs the sync session should update to encode this
- **`session/CONVENTIONS.md`** — the "Inter-agent communication" and Type-5 editing-discipline
  sections: state that only the dedicated sync session writes CURRENT.md; all other sessions
  (planners included) only submit handoffs; auto-mode/non-sync sessions must not invoke
  `/sync-current`; handoffs need not be committed by the sender.
- **`.claude/skills/s-sync-current/SKILL.md`** — note it is invoked only from the dedicated
  sync session; document the uncommitted-handoff pickup + batch-commit behavior.
- Consider whether the open "who owns CONVENTIONS.md edits" governance question (CURRENT.md
  § Next steps) is now partly answered: the sync session owns canonical `plans/session/` state.

## Open question for Dean (surface, don't assume)
- Does "canonical shared state, sync-session-only" extend to `planning/` Type-3 docs and the
  PR Status table, or only to CURRENT.md? (This handoff assumes CURRENT.md + session state;
  planning/ doc deletions are requested via handoff below to be safe.)
