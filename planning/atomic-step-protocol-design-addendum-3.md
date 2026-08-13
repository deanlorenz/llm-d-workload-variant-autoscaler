# Addendum 3 — CURRENT.md becomes indexable; every session refreshes its own slice

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10), specifically § Addressing and fetch (the `sec`/`conv` mechanism) and the "Decided, do not
re-litigate" line *"Coders never read `CURRENT.md`"*. The parent is **not edited**: this is the amendment
channel it names. Additive; narrows scope for coders, extends it for every other role.

**Status: requirement stated by Dean 2026-08-13; not yet designed in detail, not built.**

---

## What prompted it

Two things landed in the same conversation as the shared-Tier-2 checkpoint work
([Addendum 2](atomic-step-protocol-design-addendum-2.md)):

1. Dean, on responsibility for keeping session state current: *"It should be every session's
   responsibility to grab its related state from CURRENT and make sure it is up to date. ONLY if this can
   be done without reading CURRENT. That is, after the refactor, CURRENT should be indexable and support
   a tool-based focused fetch."*
2. A live example of the cost of not having this: this planner session asked the sync session to start a
   loop "as part of a plan," and sync correctly read that as descriptive prose rather than an
   authorization to act — because the request lived inside a `sync__` handoff whose whole channel is for
   asking sync to *change* CURRENT.md, not for handing sync a decision to interpret. Related but
   distinct governance point, recorded separately below.

## The amendment

**CURRENT.md needs the same heading-addressed, name-fetched shape the parent design already gives
`conventions/` and code specs — `sec <file> <id>...` per § Addressing and fetch already lists
`CURRENT.md`-like documents ("any TOC'd document... `history.md`, `CONVENTIONS.md`") as fetchable by
section, but CURRENT.md itself is not currently TOC'd or sectioned that way.** Its actual shape today is
a handful of large prose headings (`## Recent activity`, `## PR Status`, `## Blocked on`, `## Next
steps`, `## Issues to Open`, `## Pending handoffs`) with per-mission content run together inside them,
not one heading per mission/topic. Making it indexable means restructuring toward one addressable section
per mission/topic (or a per-mission subsection under each of the current top-level headings), so
`sec session/CURRENT.md <mission-slug>` returns only that mission's rows across every relevant heading —
not the whole file.

**The responsibility this enables, once the structure exists:** any session — not just the sync session
that writes CURRENT.md — checks whether its own tracked mission's slice is current, and does so *only*
via the indexed fetch, never by reading the whole file. This is the flip side of the parent design's
existing "Coders never read `CURRENT.md`" decision: that rule is about coders specifically, and stands
unchanged (a coder's own spec is its complete input; it still has no reason to touch CURRENT.md at all).
This addendum is about every *other* role — planner, reviewer, designer, sync itself — which today either
read the whole file or, more often per the parent design's ownership table, don't read it proactively at
all and rely on a `sync__` handoff to push updates outward instead.

**Load-bearing constraint, stated exactly as given: "ONLY if this can be done without reading CURRENT."**
This is not "sessions should check CURRENT.md more"; it is the opposite — a session may only take on this
responsibility once the tool-based fetch exists, and never as a stopgap that means reading the full file
today. Until CURRENT.md is actually indexed, no session should start reading it whole in the name of this
requirement. The gate is the tooling, not the intent.

## Relationship to other open items

- **Overlaps with § Open and parked's "Writing protocol" item** (parent doc, not restated here) —
  reading CURRENT.md by section is the same category of problem as reading a plan by section
  (heading-addressed, `sec`-fetchable), but CURRENT.md is also **written** far more frequently and by a
  single dedicated writer (the sync session, per the existing single-writer model), so the writing side of
  this may inherit whatever the parent design's still-parked writing-protocol thread settles, rather than
  needing its own separate answer.
- **Overlaps with § Open and parked's "Halt discovery"** in spirit only — both are instances of "how does
  state reach a session that isn't watching for it," but halt discovery is about a coder's halt needing to
  surface to a closed spec-owner session, which is a push problem (something must notify), while this
  addendum is a pull problem (a session, at its own convenience, fetches its own slice). Different
  mechanism, same underlying theme; not merged into one item.
- **Governance note, recorded here rather than opened as a fourth addendum:** the same conversation
  surfaced that a `sync__` handoff is the wrong channel for asking sync to make a judgment call (start a
  loop, interpret a plan) — sync is a worker that executes described state changes, not a decision-maker;
  authorization to act is a planner/Dean-owned decision that must be given directly, never embedded as
  prose inside a `sync__` handoff for sync to infer. This is a protocol-clarity gap of the same shape as
  the two recorded in `governance-follow-ups.md`'s 2026-08-13 section (a doc's own shorthand being read
  as authorization it never granted) — logged there as its own incident rather than duplicated here.

## Session self-declared identity + sync-maintained live index

A second, related mechanism from the same conversation, tackling the handoff-misroute incident recorded
in `governance-follow-ups.md`'s 2026-08-13 section from the addressing side rather than CURRENT.md's.

**Landed already (2026-08-13), not held for this addendum:** `session/CONVENTIONS.md`'s status-file
section now mandates an identity block at the top of every session's `session/status/<branch>.md` —
name, id, role, branch, worktree, owned doc path, spec doc followed, current task, and the status file's
own path — restated whenever it changes (start, role/task change, resume, restart), not only once. This
was small and additive enough to apply directly rather than wait for the redesign.

**Still design/build work, tracked here:** a **sync-maintained live-session index**, built by scanning
every `session/status/*.md` identity block, as part of the same shared Tier-2 work
[Addendum 2](atomic-step-protocol-design-addendum-2.md) already centralizes under sync's ownership (Dean:
"maybe sync__ does that as part of its tier 2 work"). Three stated purposes, not mutually exclusive:

1. **Resolving a handoff's `to:` field.** Once handoffs default to role+task addressing (per
   CONVENTIONS.md's updated status-file text) rather than a bare topic name, the index is what a sender
   — or a future automated router — consults to turn "planner, autoscaling-viz-panel3-redesign" into a
   concrete session name/id to actually address.
2. **Detecting stale/dead sessions**, two distinct signals rather than one:
   - **Absolute age** — reuse [Addendum 2](atomic-step-protocol-design-addendum-2.md)'s existing 7-day
     mtime-based retirement threshold rather than invent a second number to keep in sync with it.
   - **Peer-comparison, sharper and faster** (Dean: *"a strong staleness indicator is that all other
     sessions recently resumed (including sync__ itself) — but some session did not"*) — if the cohort of
     live sessions has recently checked in and one specific session's identity block hasn't moved, that is
     evidence of a stuck or crashed session *now*, well before the 7-day mark would ever flag it. This
     needs no fixed age at all — it is relative to what the rest of the cohort is doing at scan time.
3. **A machine-optimized reference for "what's the state of things"** — not a human-readable roster; Dean
   reads it via a session summarizing it, the same way any other machine-oriented artifact in this system
   is consumed. Serves the same "roster" need without a separate hand-formatted document.

**Refresh cadence is not a separate problem to solve.** Because identity blocks are restated on
resume/restart, which is already common in practice for long-running sessions, the index's own accuracy
tracks how often sessions naturally checkpoint rather than needing a forced periodic re-scan design of
its own — the peer-comparison signal above is itself the detector for the case where that assumption
fails (a session that should have resumed by now and hasn't).

### Built and verified (2026-08-13)

`scripts/tick-live-index.sh` (new) — scans `session/status/*.md`, extracts each file's identity block
(graceful on files with none yet, since most existing status files predate this convention: empty fields
rather than a skip or an error), and computes both staleness signals. `--format json` (default) is the
machine-consumption shape the design calls for; `--format table` exists as a fallback, not the primary
consumer. `--stale-days` (default 7) is the same number `tick-shared-scan.sh` uses for retirement, per the
"one number, not two" note above; the peer-comparison threshold is derived from it (a quarter of the
absolute threshold) rather than being independently configurable, for the same reason.

Verified in a sandbox (three synthetic status files: two sessions with recent, close-together
timestamps and full identity blocks, one with a 6-day-old timestamp) that: the two recent sessions both
report `age_stale: false, peer_stale: false`; the 6-day-old session reports `age_stale: false` (6 < 7)
but **`peer_stale: true`** — exactly the case the design calls for, catching a session that has fallen
behind its cohort well before the coarse absolute-age threshold would. Also verified against the real,
current `session/status/` directory (23 files, none yet carrying an identity block since the convention
was only just added) that every file degrades to empty identity fields without error. One real bug found
and fixed during testing: the initial field-extraction `awk` left a leading space on every value (an
`OFS`-rebuild artifact of clearing `$1` after a `-F': '` split); fixed by extracting the substring after
the first literal `"key: "` match directly instead. `shellcheck` clean.

**Not yet wired into `tick-shared-scan.sh` or given to sync.** This script stands alone today, runnable by
hand; folding it into the shared Tier-2 loop's own pass (so the index refreshes on the same cadence as
consolidation, per Dean's "maybe sync__ does that as part of its tier 2 work") is follow-up wiring, not
done as part of this addendum.

## Still open

- **No section-granularity design yet.** Whether CURRENT.md becomes one heading per mission (flat), or
  keeps its current per-category headings (`Recent activity` / `PR Status` / etc.) with a per-mission
  subsection under each, or some other shape entirely, is undecided. This determines what `sec
  session/CURRENT.md <id>` actually returns — one mission's full cross-category slice, or one
  category's rows for that mission only.
- **Migration path for the existing prose-block CURRENT.md is undesigned.** Today's file is long-lived
  and actively edited by the sync session; converting it to a sectioned shape without losing content
  mid-conversion needs its own plan, likely following the same "verify-or-copy-then-delete, per item"
  discipline CONVENTIONS.md's Type-5 rules already require for CURRENT.md edits generally.
- **Whether `sec`/`conv`'s existing engine (§ Addressing and fetch) is reused as-is, or CURRENT.md needs
  a variant** (e.g. because CURRENT.md sections are expected to change more often than a convention's, or
  because multiple sessions each want a *different* named slice in a single fetch call — `sec` already
  supports multiple names per invocation, so this may already be sufficient; not yet confirmed against
  CURRENT.md's actual planned shape).
- **No target date or owner.** This is a stated requirement, not yet scheduled against the parent design's
  Migration 1 phases (M1.0–M1.4) — it plausibly belongs in M1.2's harvest (CURRENT.md's structure is
  "model / taxonomy prose," per that migration's residue-class table) but that placement is not confirmed.
