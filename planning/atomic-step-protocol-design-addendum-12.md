# Addendum 12 — mid-turn note handling as a named, bounded procedure

**Status: raised by Dean 2026-08-17, not yet designed in detail. Not built.**

## At a glance

**Mission:** name and formalize what already works well in plain conversation — Dean drops one or
more notes mid-turn, the session parses, rephrases, addresses, and routes each to its right home — so
the same outcome holds regardless of session state or which session receives it, and without the
disruption of a mid-turn context switch inside whatever the session was already doing.

**Approach:** not designed yet. Candidate shape, not decided: a bounded, named procedure (closer to a
step's own `conventions:` fetch than to a full skill invocation) that a session drops into on
recognizing a note-shaped message, executes the same way regardless of session state/identity, and
returns from — without needing the full conversational context this session has been relying on today.

**Needs you:** the two problems below need separate answers, and neither is designed. This addendum
records the ask precisely; it does not propose a solution.

**Checklist:**
- [ ] Decide whether this is a skill (like the redesigned `/s-note`), a lighter always-on convention,
  or something else entirely.
- [ ] Design how a fresh/different session, with none of this conversation's accumulated context,
  produces the same routing outcome for the same note.
- [ ] Decide whether disruption to the main thread is solved by making the procedure synchronous-but-
  bounded (drop in, execute a fixed steps, drop out) or genuinely needs to run out-of-band (background,
  minimal disturbance) — Dean flagged this as a real, unresolved open question, not a decided direction.
- [ ] Relate to the Addendum 4 "pre-baked prompt template" idea — same shape (fixed procedure fetched on
  demand instead of re-derived from context every time), different trigger (a step reaching a risky
  action, vs. a mid-turn note arriving) — decide whether one design covers both or they stay separate.

---

## What prompted it

Dean, observing this session handle several mid-turn notes well over the course of one long
conversation: *"You seem to be doing very well when I just write notes in the session prompt — you
managed to capture all my items, rephrase them, address them, and capture them in the right place. I
just want to add some structure to this because it is a repeating pattern that could use a skill like
s-note."*

Asked what gap remains given that plain conversation already works, Dean's answer named two distinct
problems, neither designed against yet:

1. **Disruption to the main thread.** *"One thing that was not clear to me is how disturbing it was to
   the main conversation in the session. My notes came out of context and landed at random timing in
   your regular work. Maybe a skill will clean that (e.g., could run in background, minimal
   disturbance)."*
2. **Robustness across session state and identity.** *"Another consideration for using a skill is to
   make it more robust to the session's current context — it should be handled the same regardless of
   what is the state of the session (and maybe which session too)."*

Dean also placed this explicitly in the same family as the Addendum 4 "pre-baked prompt template"
idea — a repeating pattern that currently gets re-derived from scratch every time rather than following
a fixed procedure — while noting he wasn't sure this is the same mechanism, just the same *category*.

## Why this is genuinely open, not solved by the redesigned `/s-note`

The `/s-note` redesign from 2026-08-16/17 (`planning/state-commands-design.md` § 9.2) is adjacent but
answers a narrower question: given a note someone explicitly hands to the skill, split it and route
each piece. It does not address:

- **Disruption** — invoking a skill is itself a deliberate action; it does not by itself explain what
  should happen when a note arrives *unannounced*, mid-turn, inside an unrelated task.
- **Session-independence** — a skill's fixed procedure is *more likely* to produce a consistent outcome
  than an ad-hoc conversational read, but only if the procedure itself doesn't quietly depend on
  conversational memory — and today's good outcomes in this session came specifically from carrying full
  context (what was discussed an hour ago, who owns which doc), which a fresh session invoking the same
  skill would not have. This gap is not closed just by naming the pattern a skill; it needs its own
  design.

## Not attempted here

No skill written, no mechanism chosen, no answer to either of Dean's two questions. This addendum
exists to record the ask precisely enough that a later design pass starts from what was actually said,
not from a guess.
