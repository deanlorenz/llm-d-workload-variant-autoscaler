# Addendum 12 — mid-turn note handling as a named, bounded procedure

**Status: raised by Dean 2026-08-17. A real candidate mechanism proposed same day (§ Candidate
mechanism below) — not yet designed in full or built.**

## At a glance

**Mission:** name and formalize what already works well in plain conversation — Dean drops one or
more notes mid-turn, the session parses, rephrases, addresses, and routes each to its right home — so
the same outcome holds regardless of session state or which session receives it, and without the
disruption of a mid-turn context switch inside whatever the session was already doing.

**Approach:** **candidate mechanism proposed (Dean, 2026-08-17): don't route at capture time at all.**
The capturing session appends a raw candidate to a maintained, plan-like file — cheap, bounded, and
crucially requires no judgment about where the note ultimately belongs, which is what closes both of
the questions below. The **policy-writer** role (one of the eleven roles in `doc-and-session-model.md`,
"missing entirely" — not yet built) periodically consolidates the candidates file, using the same
skill mechanism, adding its own insight/classification at that point rather than at capture time. This
reframes the design from "route correctly, immediately, regardless of session" (hard) to "capture
faithfully, immediately, regardless of session" (much easier) plus "consolidate correctly, periodically,
by one specific role" (already the policy-writer's documented job — its existing input sources already
include "Dean's statements, incidents, existing policy, `feedback_*` memories," and a candidates file
is a natural addition to that list, not a new kind of input).

**Needs you:** confirm this reframing before it's designed further — full detail in § Candidate
mechanism.

**Checklist:**
- [ ] Design the candidates-file format and location (plan-like, per Dean — presumably similar shape
  to a Type-3/code-spec doc's own structure, or `harvest-classification.md`'s row-per-item table).
- [ ] Decide whether capture is the redesigned `/s-note` itself (append-only mode, no routing), a
  distinct lighter mechanism, or the same skill with a flag.
- [ ] Design the policy-writer's periodic consolidation pass over the candidates file — likely the
  same skill invoked in a different mode, per Dean's own framing ("you can use the same skill for
  that").
- [ ] The disruption question is largely closed by this reframing (append is cheap/bounded, no need
  for background/async) — confirm this is actually true once the append mechanism is designed, not
  assumed.
- [ ] The session-independence question is substantially eased (capturing faithfully is a lower bar
  than routing correctly) but not fully closed — a candidate still needs *some* minimal context (which
  file, whose note) to be useful; design how much a capturing session actually needs to know.
- [ ] Relate to the Addendum 4 "pre-baked prompt template" idea — same shape (fixed procedure fetched
  on demand instead of re-derived from context every time), different trigger (a step reaching a risky
  action, vs. a mid-turn note arriving) — decide whether one design covers both or they stay separate.
  **Confirmed 2026-08-17: this is not a new idea Dean is raising twice — Addendum 4 (2026-08-13) is the
  original, verified by direct grep across all planning docs before this addendum was written; nothing
  predates it.**

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
**Confirmed 2026-08-17, checked directly rather than assumed: this is not a new idea repeated — it is
the same Addendum 4 raised 2026-08-13**, verified by grepping every `planning/*.md` file for "pre-baked"
before this addendum existed at all; the only hits were this addendum's own text quoting Addendum 4.

## Candidate mechanism — proposed 2026-08-17, not yet designed in full

Dean's own proposal, in response to being asked what gap remains given that plain conversation already
works well: *"one option is for the skill to save candidates instead of adding rules directly — we
already wanted a rules author role (can't remember the name now) — so it makes sense for that entity
to actually consolidate. If this is done via a known 'plan-like' file 'maintained' by the skill, then
you can periodically, when you have time, go over all the candidate rules and add your insights (you
can use the same skill for that)."*

The role Dean couldn't recall the name of is **policy-writer** — one of the eleven roles named in
`doc-and-session-model.md` § Roles, owning `conventions/`/`roles/`, currently "missing entirely" (no
skill built yet, per that doc's § Skill surface). Its documented input sources already include "Dean's
statements, incidents, existing policy, `feedback_*` memories" — a candidates file this addendum's
capture mechanism maintains is a natural fifth input, not a new kind of thing the role would need to
learn to consume.

**Why this reframing matters — it changes which problem is actually hard.** The original framing
("route each note to its final home, correctly, at capture time, regardless of session") bundles two
things that don't need to happen together: capturing faithfully, and judging correctly where something
belongs. Splitting them:

- **Capture** — append a raw candidate to a maintained file. Cheap, bounded, and requires no judgment
  about final placement at all — which is exactly what made session-independence and disruption hard
  under the original framing. A fresh session, or this session mid-unrelated-task, can do this reliably
  because there is nothing subtle to get right.
- **Consolidation** — the policy-writer, periodically, "when you have time" (Dean's words — not on
  every note, not urgently), reads the whole candidates file and adds judgment: where each item really
  belongs, whether it conflicts with something existing, whether it's actually new-articulated policy
  needing separate sign-off per `conventions-harvest-spec.md`'s own M1.2 distinction. Dean's own
  suggestion: the same skill mechanism, invoked in a different mode, does this pass too.

## Why this substantially eases, but does not fully close, either open question

The `/s-note` redesign from 2026-08-16/17 (`planning/state-commands-design.md` § 9.2) answers a
narrower question than either framing: given a note someone explicitly hands to the skill, split it and
route each piece. Against the candidate-mechanism reframing above:

- **Disruption** — substantially eased. An append is about as cheap and bounded as a mid-turn action
  gets; it does not obviously need to run out-of-band. **Not fully closed**: the capturing session still
  needs to notice a note-shaped message arrived and interrupt itself briefly to append it — the question
  is now "how cheap is that interruption," not "does this need to be async," but it is not zero.
- **Session-independence** — substantially eased. Capturing faithfully is a much lower bar than routing
  correctly, and does not obviously depend on this session's accumulated context the way routing did.
  **Not fully closed**: a candidate still needs *some* minimal context to be useful later (which
  file/topic it's about, roughly, even if not its final home) — how much a capturing session must know
  to write a usable candidate, versus how much can be deferred entirely to the policy-writer's
  consolidation pass, is not yet designed.

## Not attempted here

No skill written, no candidates-file format decided, no policy-writer role built. A real mechanism is
now proposed (§ Candidate mechanism) and substantially eases both of Dean's original questions without
fully closing either — the checklist above is what remains to actually design and build, not a blank
slate.
