# Addendum 1 — decisions: one owner, a lifecycle, and a scoped defer

**Amends** [`doc-and-session-model.md`](doc-and-session-model.md) (**design**, FINAL, frozen 2026-08-10).
The parent is **not edited**: this is its amendment channel. Additive; governs where the two overlap.

**Status: APPROVED by Dean 2026-08-12.**

---

## What prompted it

> *"decisions I made in a planner keep surfacing back up. Seems like the open issue and decision made on
> them are stored in multiple places. We need a clear owner for every decision (in terms of which document,
> not which session)."*

Measured, not assumed. **200 documents** carry decision language. The "Dean's call / awaiting Dean" phrasing
alone spans 82 files across five kinds — and the largest carrier is the **transport layer**:

| | files |
|---|---|
| `session/handoffs/` | **46** |
| `planning/` | 22 |
| `session/status/` | 11 |
| `session/`, digests | 3 |

And the scar tissue is countable: `retracted` in **21** files, plus "do not re-raise" ×2, "not an open
question" ×2, "no longer open" ×4, "settled-deferred", "settled, not open". Those phrases exist *only*
because something resurfaced and had to be nailed down in prose.

**Two mechanisms.** A handoff is a channel — a `.DONE` handoff is a delivery receipt, not a record — so a
decision riding in one either got copied into a real home or evaporated. And `CURRENT.md` is **auto-loaded**,
so when it says "open" it wins by volume every session even if a design says decided.

## Ownership

**Exactly one document owns a decision: the one whose scope it constrains, at the highest level it binds.**

| Binds | Owner |
|---|---|
| the design | the design — its addendum, if frozen |
| one unit of work | the code spec |
| how agents work | policy: `conventions/`, `roles/` |

**Never an owner — always a ref:** `CURRENT.md`, `history.md`, handoffs, status files, session digests,
reviews, memory, commit messages.

A ref states the id and, at most, a one-line gloss. **It never states the decision's state**, because two
statements of state are exactly how they diverge.

**The rule that closes the handoff hole:** a decision must land in its owning document **before** the
handoff carrying it is renamed `.DONE`. Consuming a handoff without rehoming its decision is the loss event.

## Lifecycle

**States:** `raised` → `todo` | `wip` → `decided` | `rejected` → `closed`

**Fields:** `owner` · `why` · `alternatives-rejected` · `decided-by` · `decided-on` · `refs`
· `defer` (see below) · `parent` (see below)

### `decided` ≠ `closed`

Decided means the call was made. Closed means its consequences have landed. `AD8` option (b) is approved
with its placement still open — as one item that reads as "open" and comes back.

### Split, never "partial"

*Dean: "split rather than partial is correct."* A half-made decision becomes **two decisions with a
`parent` link**. `partial` hides *which half* is open, and the hidden half is what resurfaces.

### `defer` takes a horizon — and is usually not about the subject

Dean's correction, and it is the crux:

> *"defer needs scope — sometimes I don't want to handle something in a particular session or just want to
> push it down the backlog. I say defer when I mean later. Not always meaning that I decide to not do it."*

So **defer is a decision about attention, not about the subject.** It is a *field on an open item*, not a
terminal state. Deciding against the subject is `rejected`, which is terminal and different.

| `defer:` | Means | May be raised again |
|---|---|---|
| `session` | not in this session; still open, still to do | next session — freely |
| `mission` | not in this mission or PR; still to do | when that mission closes |
| `backlog` | priority call made: later, not now | only if its criticality changes |
| *(absent)* | no deferral | any time |

The state stays `todo`. What defer changes is **who may raise it and when** — nothing else.

This is the ambiguity that caused the reported problem. Both resurfacing classes were defer collapsing:
`defer:session` items re-raised inside the same session, and `defer:backlog` items re-raised as though the
question were still open. `W2`/`U4` was the latter — answered, then deferred on Dean's own criticality test,
which is `state: todo, defer: backlog`, and needed the phrase "settled-deferred" invented because the model
had no way to say it.

## Storage — per-document, index computed

*Dean: "storage — sound ok. lets see if it works."* Adopted on the same principle as `conv-list`: **no
stored index.** A stored index drifts, and then two places disagree, which *is* the disease.

- Each owning document carries a `## Decisions` section; each entry is `### decision: <id>` plus fields.
- **IDs are owner-scoped** — `anchor-design/D-07`, not a global counter. Self-describing in a ref, and no
  cross-session coordination to allocate one. Reversible if it proves awkward.
- `decision-list` scans owning documents and prints id · state · defer · owner · one line.
- `decision-lint` fails on:
  1. the same id in two documents with **conflicting state** — the check that would have caught this
  2. a ref to an **unknown** id
  3. a decision **stated** in a non-owning document, rather than referenced
  4. `state: decided` with no `why`, or `rejected` with no `alternatives-rejected`

## Retrofit — active work only

*Dean: "retrofit only active work."* Closed decisions do not resurface; only live ones do. So: adopt going
forward, and backfill only decisions belonging to currently-active missions. Not the 200 documents.

The first backfill target is uncomfortable and should be named: **this session's digest is itself the
anti-pattern.** Its `## Dean's decisions` section is ~40 entries in a document that the rule above makes a
*ref, never an owner*. Those decisions need rehoming into the designs, addenda and specs they actually bind,
leaving the digest with ids and one-line glosses.

## Not yet enforced

`decision-list` and `decision-lint` do not exist. Until they do, ownership and the no-state-in-refs rule rest
on discipline — the same footing that produced the 46 handoffs. They belong with `plan-lint` and `step-check`
in [`step-gates-spec.md`](step-gates-spec.md), which is still DRAFT.
