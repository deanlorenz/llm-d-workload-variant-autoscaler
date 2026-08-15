# Addendum 9 — mailbox files for handoff wake-up, plus a broadcast channel for discovery and park

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

## Git notes — re-examined, correcting an initial misreading

**First pass (below, superseded) misread the proposal as notes attached ad-hoc to arbitrary commits**,
which does reintroduce a poll-and-guess problem (which commit's notes are "for me"?) and was correctly
rejected on that reading. **The actual proposal is narrower and does work: one dedicated, fixed commit
per channel, created once at channel-creation time, with the stream living entirely as notes appended
to that single known commit.** Under that framing there is no guessing — both sides know the one commit
hash to watch from the moment the channel exists, exactly as they would need to know a mailbox file's
path under the file-based design below. Reframed this way, git notes are not a different idea rejected
in favor of mailbox files — they are an alternative **storage substrate** for the same idea (an
append-only stream anchored to something fixed and known), and deserve a fair comparison rather than
a rejection on a misreading:

| | Mailbox file (`session/mailboxes/<channel>.log`) | Notes on a fixed per-channel commit |
|---|---|---|
| Append primitive | plain file append | `git notes append` |
| Visible to `ls`/`grep`/`cat` | yes | no — needs `git notes show`/`git log --show-notes` |
| Shows up in `git status` / working tree | yes (needs a `.gitignore` decision) | no — notes live in a separate ref namespace, never touch the tree |
| Concurrent-append safety | line-granular, git-transactional only if the file itself is committed each time (or left uncommitted, per Dean's existing "handoffs need not be committed" rule) | git-transactional natively, since a note update is itself a git object write |
| Discoverable cold, from a fresh clone/session with no prior context | yes, trivially (a normal file) | requires knowing to fetch/look at the notes ref at all — less obvious to a first-time reader |

**Both solve problem 3 equally well once the fixed-anchor precondition holds.** The remaining
difference is ergonomics, not correctness: mailbox files stay inside the same mental model as every
other artifact in this protocol (plain files, `ls`-discoverable, no new git concept to learn), while
notes are genuinely git-native and free of any working-tree/`.gitignore` footprint but need everyone —
including a future reader unfamiliar with this specific convention — to know that `git notes` is where
the channel's activity actually lives. **Decided: keep the mailbox-file design below as the concrete
mechanism**, on ergonomics grounds (nothing new to teach, directly greppable, consistent with the
existing handoff files' own shape) — but the choice is closer than the first pass suggested, and notes
remain a legitimate alternative implementation if the working-tree footprint of many mailbox files
ever becomes a real problem worth solving.

**Problem 1 (addressing) is still not solved by either storage substrate** — a fixed-per-channel commit
still has to be created and its hash shared by *some* mechanism the first time a channel is needed,
which is exactly the discovery problem addressed separately below (§ Broadcast/discovery channel), not
by notes or mailbox files themselves.

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

## Broadcast/discovery channel — solving problem 1, added 2026-08-16

The mailbox design above assumes both sides already know the channel's name/path. That assumption
needed its own mechanism, which Dean proposed the same day as a single shared, append-only, everyone-
reads/everyone-writes channel — one file, three usage patterns riding the same rails, distinguished by
line content rather than by separate mechanisms:

```
session/mailboxes/broadcast.log
```

1. **Lookup — "looking for" / response.** A session that needs to reach a role it doesn't have a
   channel for yet appends a query (`<ts> <asker-id> looking-for benchmark-coder`); whoever currently
   holds that role answers (`<ts> <responder-id> here benchmark-coder channel=coder-plans-tooling.log`)
   or, if nobody currently holds it, the query simply sits unanswered until someone does — no timeout
   or failure mode needed, since an unanswered query costs nothing but a few bytes.
2. **Presence announcement.** A session states its own identity on start, resume, or role/task change —
   `<ts> <session-id> announce role=benchmark-coder branch=benchmark channel=<name>` — the same identity
   triple (role, scope, channel) a session's status file already carries, per the identity-block
   convention (`session/CONVENTIONS.md`, added 2026-08-13), just also broadcast. **A takeover case is
   the same shape, not a special case**: a new session picking up an existing role announces exactly
   the same way, and the channel name in its announcement — unchanged from the previous holder's, since
   the channel is bound to the role/task, never to a session ID — is what makes the handoff transparent
   to anyone still holding the old holder's channel name in memory. Dean's own worked example: *"Hey
   AAA, I am new coder, session ID ZZZ, taking over channel XXX."*
3. **General broadcast.** The same file, the same append, no different mechanism — `<ts> <sender-id>
   all please-park` reaches every session that happens to check the broadcast log, which is exactly
   the mechanism the earlier, never-fully-solved `/s-park` idea needed and didn't have: a way to reach
   every live session at once without knowing in advance who they all are.

**This is functionally a DHCP-like discovery protocol for handoff channels** — Dean's own framing, and
apt: a session doesn't need a pre-existing directory of who's running what; it can always ask the
broadcast log, and the log itself, read from the top, tells any newly-arriving session the current
state of who announced what most recently.

**Cost is real but bounded, and different in shape from the per-channel mailbox's cost.** Unlike a
dedicated mailbox (checked only when that specific relationship matters), the broadcast log is shared
across every role, so a session reading it pays a scan-past-irrelevant-lines cost proportional to
total system activity, not to its own relationship's activity — a version of the same "wasted tokens
figuring out if it's for me" complaint that started this whole redesign, just at a smaller scale (one
file, pattern-matched against a handful of known prefixes — `looking-for`, `announce`, `all`, `here`
— rather than N handoff files pattern-matched against filename prefixes). The mitigating property is
that this channel is **request-driven, not continuously watched**: a session checks it at the moment
it actually needs to find someone (the DHCP framing — ask when you need an address, don't poll waiting
for one), and periodically on its own start/resume to pick up its own presence announcement duty, not
on every wakeup regardless of relevance.

**Not yet decided:** exact line grammar/prefixes (sketched above, not finalized); whether `announce`
lines ever get pruned/superseded (an old announcement for a role that has since changed hands is
technically stale but harmless if a reader always takes the *most recent* matching line, not any
matching line); and how this interacts with the still-deprioritized sync-maintained live-session index
from [Addendum 3](atomic-step-protocol-design-addendum-3.md) — the two overlap in purpose (both answer
"who currently holds role X") but this broadcast channel is peer-to-peer and self-service, while
Addendum 3's index is sync-maintained and computed — whether one subsumes the other, or they serve
genuinely different consumers, is an open question for whenever Addendum 3 is revisited.

## What this does not solve

Nothing outstanding from problem 1 remains — see above. What remains genuinely unaddressed: the exact
grammar for broadcast-log lines (a parsing convention, not a design gap); and whether triggers
(no-instruction doorbells) should also get mailbox/broadcast treatment or stay purely directory-based,
per the original "Still open" note below.

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
