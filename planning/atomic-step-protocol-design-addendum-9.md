# Addendum 9 — per-channel mailbox files replace directory-watching for handoff wake-up

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (design, FINAL, frozen
2026-08-10) and [`session/CONVENTIONS.md`](../session/CONVENTIONS.md)'s "Inter-agent communication:
status files, handoffs, triggers" section, specifically the wake-up half of that mechanism. The parent
is not edited: this is the amendment channel it names. The handoff artifact itself (full-content `.md`
files, the `.md`/`.WIP`/`.DONE` state machine, atomic `mv` transitions) is **unchanged** — this
addendum replaces only how a session discovers that a new handoff exists.

**Status: designed 2026-08-16, following a live demonstration of the problem it fixes. Not built.**

---

## What prompted it

A concrete failure, not a hypothetical: a coder background agent was given a task, wrote a plan, and
correctly stopped to wait for review — exactly as designed. The planner reviewed and approved,
wrote the approval as a handoff file addressed to the coder... and the coder never saw it. It had no
standing watch loop; it only checked `session/handoffs/` at the one moment its own launch prompt told
it to, then finished (or was ended by its own session lifecycle) while the approval sat unread. This is
not a tooling bug — it is the directory-watching model's structural weakness surfacing on the very first
real multi-agent exchange it was tried on.

Dean, generalizing from this and a related governance discussion about `SendMessage`/agent teams
(confirmed by research to be architecturally out of reach for `claude --bg` background agents — a
separate, closed investigation, not revisited here): *"We has some concurrency issues and identity
issues I want to fix. Also, I don't like the overhead — every wakeup the model needs to figure out if
the message was for this session — this breaks the session's flow and wastes tokens."*

Three separate problems, not one, stated precisely:

1. **Addressing** — the existing `<recipient>__<topic>.md` prefix names a *role or task*, not a live
   session, which is correct by design (a new session taking over a task must inherit the same
   address — the prefix must never be session-ID-shaped) but means nothing today resolves "who
   currently holds this role" cheaply or reliably.
2. **Message content and durability** — full-content files, atomic `.md`/`.WIP`/`.DONE` transitions,
   traceable and persistent. **Already solved** — Dean's own words: "the WIP/DONE atomic renames are
   good enough." Not touched by this addendum.
3. **Wake-up** — how a session learns *that* something new exists, cheaply, without scanning a
   directory and pattern-matching filenames against its own identity every time it wakes.

## Git notes — considered and rejected

Git notes (`git notes add/show`) were raised as a git-native candidate specifically for problem 3,
since git is already available, transactional, and local. Examined against all three problems and
found not to help with any of them:

- **Problem 2 is already solved**; notes add nothing there.
- **Problem 1 (addressing) is a task-ownership registry problem**, not a transport problem — it needs
  something like the identity-block + sync-maintained live-session index already designed in
  [Addendum 3](atomic-step-protocol-design-addendum-3.md) (deprioritized by Dean as "not a priority,
  leave it for later" — still true; this addendum does not change that). Git notes cannot tell a
  session who currently owns a role.
- **Problem 3 is where notes looked most promising, and still don't fit.** A note is attached to a
  *commit* — reading it requires already knowing which commit to check, or scanning a commit range,
  which reintroduces exactly the poll-and-pattern-match cost this addendum exists to remove. Notes buy
  transactionality and locality that the existing atomic `mv` state machine already provides for free.

**Decided: drop git notes.** The one place a commit landing *is* a genuinely free, already-existing
signal — the reviewer checking `git log` on `plans-tooling` to see if the coder's work advanced — needs
no new mechanism; it already works today and is orthogonal to the handoff-wake-up problem this
addendum solves.

## The mechanism — per-channel mailbox files

```
session/mailboxes/<channel>.log
```

**One file per relationship** (e.g. `coder-plans-tooling.log`, shared by the coder-role-on-that-branch
and its planner), not one shared firehose all roles append to. Considered and rejected: a single
shared mailbox filtered by a tag field — it would mean every session pays the cost of scanning past
lines that aren't for it, and concentrates concurrent-write contention onto one file instead of
spreading it across many small ones. A dedicated file per channel means the check is trivial (this
one file's line count) and matches the existing `session/handoffs/`'s own pattern of one clear
location per relationship.

**Append-only, two event types, both directions:**

```
<ISO8601Z> <sender> new-handoff <path>
<ISO8601Z> <sender> consumed <path>
```

- `new-handoff` — written by whichever side just created a handoff file, pointing at its path.
- `consumed` — written by whichever side just marked a handoff `.DONE`, so the *other* side can
  passively learn its message was read without re-checking the handoffs directory. Symmetric: the
  mailbox becomes a complete, cheap summary of the channel's activity in both directions, decided
  explicitly over a minimal new-handoff-only design, since a sender being able to passively confirm
  "my last message was read" was judged worth the extra line.

**Why appends specifically solve the concurrency complaint.** An append is close to conflict-free
under concurrent writers: two sessions appending at the same moment interleave correctly at line
granularity (each write is its own line; neither corrupts the other's), and the rare true race (two
appends landing in a way that briefly confuses a reader mid-write) is trivially recoverable — both
sides notice and can simply re-append, per Dean's own framing, rather than needing a lock file or a
retry protocol. This is a materially different risk profile from the `flock`/`mkdir`-guard machinery
`atomic-step-protocol-design-addendum-7.md` needed for single-instance *process* ownership — that
problem (exactly one instance may run) is genuinely harder than this one (many appends may land in
any order, and order barely matters since each line is independently meaningful).

**Never truncated or rotated.** Preserves the ledger-like, full-history, cold-recoverable property
Dean explicitly wants kept: *"I like the ledger-like feeling of handoff files — we get the full history
of conversation and can recover easily from any session."* A mailbox file only ever grows.

**Tracking "what I've already seen" is the reader's job, not the mailbox's.** A session remembers its
own last-consumed line (byte offset or line count) in its own status file, the same file that already
carries its identity block and step log per earlier conventions. Checking for new mail is then `wc -l`
or a byte-length comparison against that remembered value — a few bytes read, no filename
pattern-matching, no identity-confusion risk, since the channel name is fixed and never encodes a
session ID (satisfying problem 1's constraint that a new session taking over a role must be able to
pick up the same channel without any renaming).

**First contact.** A channel file's absence is itself informative — nobody has written to this
relationship yet. The first append creates the file; no special-casing needed.

## What this does not solve

**Addressing (problem 1) is explicitly out of scope**, per Dean's own framing that this addendum
should "use git tools only if that solves any of the above" and his separate deprioritization of the
live-session-index work. A mailbox file's *name* still has to be agreed on by both sides somehow (the
launch prompt, today, states it explicitly) — this addendum makes checking for new mail cheap once both
sides know which file to watch; it does not yet solve how a session discovers which channel to watch
if it doesn't already know, or how a channel survives a role/task changing hands without a shared
convention for the channel's own name being re-derivable from the task rather than a session ID.

## Still open

- **Exact channel-naming convention** — `<role>-<branch>.log`, `<task-slug>.log`, or something else;
  not decided. Should be derivable the same way by both sides without negotiation, which argues for
  something computed from the task/branch rather than agreed upon per-instance.
- **Whether a session should also write a `new-handoff` line for a trigger (no-instruction doorbell),
  not just a `plan__`/`sync__` handoff** — the mailbox's value is highest exactly where directory
  polling is weakest, which includes triggers, not just handoffs; not explicitly resolved either way.
- **No skill or script built yet.** This is a design, following the same discipline as every prior
  addendum in this series — recorded before being built, not built first and rationalized after (the
  inverse of what happened with `atomic-step-protocol-design-addendum-7.md`, which was written
  retroactively after code came first).
- **Interaction with the planned watcher skill** (Dean's own point 5 from the 2026-08-15 session/task
  rule set: "all sessions should set up watchers for handoffs — we should plan a skill for that").
  Whether that skill's job becomes "watch your channel's mailbox file" rather than "watch the handoffs
  directory" once this addendum lands is the natural next question, not resolved here.
