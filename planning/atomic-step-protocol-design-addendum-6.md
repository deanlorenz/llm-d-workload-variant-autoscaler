# Addendum 6 — `/s-park`: a broadcast signal for safe machine sleep/restart

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10) by adding a new artifact class — a broadcast, not a handoff or a trigger — to
§ Handoffs/Triggers' existing model. The parent is **not edited**: this is the amendment channel it
names. Additive; introduces one new mechanism, reuses everything else as-is.

**Status: designed 2026-08-14, not yet built. No skill exists yet. Superseded in part by
[Addendum 9](atomic-step-protocol-design-addendum-9.md)'s broadcast channel, which solves the same
"reach every live session" need via a different, more general mechanism — see that doc.**

## At a glance

**Mission:** `/s-park` — a signal every live session can act on before laptop sleep/VS Code close/
restart, so nothing is left mid-edit and everything is cold-resumable.

**Approach:** each session finishes its current unit of work, reports ready, coders exit their
worktrees (preserves session history in plans), all hand off to sync or sync collects state.

**Needs you:** nothing right now. Note: Addendum 9's broadcast log may make this simpler to build than
originally scoped here — worth checking before building `/s-park` as its own thing.

**Checklist:**
- [ ] Not started — no skill exists.
- [ ] Reconcile with Addendum 9 before building (may be largely the same mechanism).

---

## What prompted it

Dean, watching this session re-arm its own Tier-1 loop after a computer restart, and separately
discovering that the checkpoint-tick's own status was ambiguous across sessions: *"I am thinking that if
all sessions watch handoffs then perhaps I need broadcast handoff too — e.g., /s-park — I run this to
notify all of imminent laptop sleep / VSC close / computer restart / ... — all would finish what they
do, stop, and report ready for parking. Will be ready for cold resume. coders then exit their worktrees
(this ensures their session history is preserved in plans). All can then handoff to sync__ (or sync can
collect their state) so I can safely park the work."*

## Why this needs a new mechanism, not a bigger handoff

The existing handoff/trigger model (§ Inter-agent communication, parent doc) is **one file, one
recipient, one state machine** — `<recipient>__<topic>.md`, `.md → .WIP → .DONE`, the recipient owns
every transition. A broadcast breaks this by construction: it is addressed to *every* live session at
once, so a single `.WIP` rename by whichever session notices first would incorrectly signal "already
being handled" to everyone else. **A broadcast file must be read-only and never renamed** — closer to a
trigger's "doorbell, not a memo" shape (§ Handoffs, parent doc) than to a handoff.

**No session can enumerate "all live sessions" to check acks against.** Dean's own correction: *"the
sender cannot scan if it does not know which session exist. The maximum it can do is track the ones it
knows about (from its tier 2 runs or from sync__ messages)."* This is the same gap
[Addendum 3](atomic-step-protocol-design-addendum-3.md)'s live-session index exists to close, and that
addendum is explicitly deprioritized ("not a priority, leave it for later"). `/s-park` is therefore
designed to work **without** a completeness guarantee — Dean is the actual completeness check, by
watching each session's own chat respond, not by any session scanning a roster.

**No reliable "push right now" mechanism exists.** `SendMessage`/cross-session addressing was tried and
found unreliable (memory `feedback_sendmessage_vs_file_handoffs`); the existing file-based
handoff/trigger protocol is pull/poll-based, and only coders are told to poll `session/handoffs/`
regularly today (memory `feedback_check_handoffs_between_commits` — coder-specific). **Decided: accept
imperfect timeliness.** A session that happens to poll or touch a file soon after the broadcast responds
promptly; one that's deep in thought may not notice until its next natural checkpoint. Dean manually
nudges any session he needs to stop *right now* — `/s-park` is not a substitute for that, it is the
standing instruction every session should already be primed to recognize.

## The mechanism

**One broadcast file, written once by Dean's `/s-park` invocation:**

```
session/handoffs/park__all.md
```

Read-only — no `.WIP`, no `.DONE`, never renamed, never `git rm`-ed as "consumed." It is a point-in-time
announcement, not a per-recipient work item; it can be deleted manually by Dean once he's satisfied
enough sessions have responded, or simply left in place (a session resuming later and finding it still
present should treat it as still meaning "finish and report," not as stale).

Body — same shape as a trigger (`to:` / `reason:` / `note:`), since it carries no per-recipient
instructions beyond the single standing one:

```
to: all
reason: imminent laptop sleep / VS Code close / computer restart
note: <optional context, e.g. "restarting for a Windows update">
```

## What each session does on seeing it — reusing existing mechanisms, not inventing new ones

Dean's correction here matters as much as the broadcast itself: **no new ack artifact.** Every session
already has three channels it uses routinely, and `/s-park` just tells every session to use them *now*,
at this specific checkpoint, with an explicit park-ready line:

1. **Say so in its own chat.** The most direct channel — Dean is watching each session's conversation,
   not a dashboard. This is the primary signal, not a fallback.
2. **Write its normal `sync__` handoff now**, even if not otherwise due, with an explicit ready-to-park
   line in it. Sessions already send these at meaningful checkpoints (§ Handoffs, parent doc) — being
   told to park is exactly such a checkpoint.
3. **Update its own status file** (`session/status/<branch>.md`), which it already rewrites at
   checkpoints per its identity block (`session/CONVENTIONS.md`, added 2026-08-13) — the natural place
   to record `state: <whatever fits>` reflecting "finished and parked" alongside its existing fields.

**Finishing "what they do" before stopping** means reaching the next safe point in whatever unit of work
is in flight — not abandoning mid-edit, mid-commit, or mid-multi-file-change. What counts as safe is
role-specific and not enumerated here (a coder mid-commit finishes that commit; a planner mid-edit
finishes or reverts the edit) — this addendum does not attempt to define a universal "safe point," since
the existing role conventions already govern what a mid-task pause looks like for each role.

## Coder-specific step — `ExitWorktree`, and the real reason it matters

Dean's own empirical finding, not documentable from the code/docs alone, given here in full because it
is the single most concrete and load-bearing part of this whole mechanism:

> Most sessions launch from `plans` — the VS Code Claude Code extension uses the workspace's default
> worktree as the entry point for every editor. When a coder calls `EnterWorktree`, Claude Code migrates
> that session's transcript JSON into the target worktree's own project directory. While the session
> stays alive, this is invisible — everything works fine. **But the side-panel session history only
> shows sessions associated with `plans`** (unlike the CLI's own `--resume`, which can list sessions
> from every worktree). If the editor or the session itself dies while the transcript lives inside a
> worktree it migrated into, the side panel loses all memory that this session ever existed under a
> different path — it cannot be resumed from the normal VS Code flow. The only recovery is a manual
> terminal, `cd` into that specific worktree, and `claude --resume` from the CLI — which works, but loses
> IDE integration (no inline diffs in the editor, the CLI steals focus, and at most one such terminal
> can integrate with the IDE at a time regardless).

**So the instruction is: before parking, a coder must call `ExitWorktree` and send one more prompt.**
`ExitWorktree` migrates the transcript back toward `plans`'s project directory while the session is
still alive and can do so cleanly; the follow-up prompt is needed because the migration itself is not
free-standing — per the empirical note, this is Dean's best current understanding of the mechanism, not
independently verified against Claude Code's own documentation (unlike Addendum 5's CLAUDE.md/memory
findings, which were sourced). If it turns out `ExitWorktree` alone is insufficient or the extra prompt
isn't actually needed, that would be a correction to this addendum, not a silent assumption carried
forward.

**Note per `EnterWorktree`'s own tool description:** entering a worktree already requires Dean's manual
approval even under auto mode — described as deliberate, part of the isolation/sandboxing model, "much
safer than just `cd`." `ExitWorktree` is the symmetric, expected step back; nothing about `/s-park`
changes that approval requirement.

## What Dean gets back

Not a scan, not a completeness guarantee — the natural trail already produced by the three channels
above: each session's own chat response (primary), accumulated `sync__` handoffs in
`session/handoffs/` (processed whenever Dean next says "sync state," per the existing explicit-trigger
model — `/s-park` does not change when or whether `/sync-current` runs), and updated status files
readable at a glance. Cold resume after sleep/restart means: each session's transcript is safely
findable (coders, via the `ExitWorktree` step above; non-coders, already anchored to `plans` by
default), its last status file reflects a clean stop rather than mid-task, and any state it wanted
preserved already reached a `sync__` handoff or its own committed status file — nothing relies on the
session itself surviving the sleep/restart to carry information forward.

## Still open

- **No skill built yet.** `/s-park` does not exist as an invocable command; this addendum is the design
  it would be built from.
- **No enumeration of what "safe point" means per role** — deliberately left to each role's existing
  conventions rather than defined fresh here.
- **The `ExitWorktree`-migrates-the-transcript mechanism is Dean's empirical understanding, not verified
  against Claude Code's own documentation.** Worth confirming with the same sourced-research approach
  Addendum 5 used, before this becomes a standing instruction coders are expected to follow without
  understanding why.
- **Interaction with the tick loops (Addenda 2/3) on sleep/restart is not addressed.** A parked session's
  own Tier-1 loop dies with the process either way (restart kills everything); whether `/s-park` should
  also say anything about the shared Tier-2 loop or the live-session index is not designed here — those
  addenda's own lifecycle sections already cover restart behavior independently.
- **Whether Dean deletes `park__all.md` manually, or it is left in place indefinitely as a standing
  "last time we parked" marker**, is unresolved — either is workable; not decided.
