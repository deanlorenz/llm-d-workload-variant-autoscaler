# Addendum 4 — reaffirmed rule bundles: standing rules re-surfaced at the moment they apply

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10), specifically § The step (the `conventions:` step field) and § Open and parked (adds a new
"still open" item, does not resolve one). The parent is **not edited**: this is the amendment channel it
names. Additive; records an open question, not a decision.

**Status: raised by Dean 2026-08-13 as an open question during the `harvest-classification.md` review, not
designed, explicitly uncertain ("we shall see"). Confirmed "ok for now" 2026-08-15 — stays parked as a
question, not escalated to a decision.**

## At a glance

**Mission:** record an open question, not answer it — should some standing rules be re-surfaced at
the specific moment a risky action becomes plausible, instead of only living in a role kernel or being
cited per-step?

**Approach:** no mechanism proposed. Named as a real gap in today's two-category scheme
(per-step convention vs. standing role kernel) — some rules are absolute but only matter at a
specific moment (e.g. "never push," relevant only near a commit).

**Needs you:** nothing right now — explicitly "we shall see."

**Checklist:** none — this is a parked question, not a task.

---

## What prompted it

While reviewing a first-pass classification of `CONVENTIONS.md`/`CODER-CONVENTIONS.md` rules into
per-step conventions vs. standing role kernels
([`harvest-classification.md`](harvest-classification.md)), several rules resisted a clean either/or:
absolute, always-true rules ("never push to `upstream`," "coder may never push without confirmation")
that nonetheless only become *actionable* at a specific moment (the point of committing, the point of
being tempted to push). Classified purely as role-kernel content, they're standing but easy to forget in
the moment because nothing re-surfaces them when it matters. Classified purely as a per-step convention,
they'd need to be cited on every step where the risk exists, which is exactly the duplication-by-another-
name the design exists to avoid.

Dean's framing, verbatim: *"The whole idea of the per-step atomic-rules is to make sure they are not
skipped/forgotten — when a coder gets to a point where it commits then it might be tempted to push — the
step itself should make it load the micro-rule and do the pre/post-commit checks and remind it (in the
specific context of that step) that it should not push. A gate in place when the (violating) action is
plausible."* And: *"there are some core rules / kernel rules that apply to all roles. And some that
should be stated upfront to any coder. They remain a MUST read for any coder start/resume. I would even
go further than that — coder needs to be reminded of the core rules when it matters — this could be the
mechanism for the step's micro-rule. Instead of writing another rule the step could ask to refresh a set
of known rules."*

## The question, not yet an answer

**Is there a third category, distinct from both a per-step convention and a standing role kernel: a named
bundle of already-existing rules (core kernel content, or specific conventions) that a step can cite to
*reaffirm*, without re-stating or duplicating them?** If so:

- How does a step "ask to refresh a set of known rules" mechanically — is this just today's `conventions:`
  field already supporting multiple names in one citation (already true, per § The step — no new
  machinery needed if that's sufficient), or does it need a distinct bundle concept with its own name and
  membership list, separate from a single convention?
- Is the re-affirmation itself a hook-enforced gate (Dean's own question: *"Is this something that needs
  to be tied to hooks? Do we need 'rule bundles' that are reaffirmed on specific hooks?"*), or is citing
  the bundle in the step's `conventions:` field (read as part of the step's own detail-layer fetch, per
  § The step's two-layer split) sufficient on its own?
- If hook-enforced: this would extend, not duplicate, the already-planned **"two stateless hooks (DCO,
  push-block)"** (§ Migration, M1.1) — those are exactly the shape of a mechanically-enforced reaffirmation
  at the moment a specific action (a commit, a push) is attempted. Whether a general "rule bundle" concept
  generalizes those two into a named, extensible mechanism, or whether DCO/push-block simply stay as two
  one-off hooks and this stays an unrelated idea, is undecided.

**Explicitly not decided even in direction.** Dean's own words: *"I am not sure... We shall see."* This
addendum exists to record the question precisely, with its origin and the concrete examples that raised
it, so it is not lost — not to propose or bias toward a resolution.

## Relationship to other open items

- **§ Open and parked's existing "Whether the `scope:` hook... is worth its complexity"** (parent doc) is
  a narrower, already-scoped question about one specific hook. This addendum's question is broader —
  whether a *general* reaffirmation mechanism is needed at all, of which a `scope:` hook would be one
  instance among several.
- **§ Migration M1.1's "two stateless hooks (DCO, push-block)"** (parent doc) are the existing,
  already-planned instances closest in shape to what Dean is describing. Confirming whether they
  generalize, or stay as two independent one-offs, is part of answering this addendum's question — but
  that confirmation is not done here.
- **Interacts with, but does not resolve, the borderline classification calls in
  `harvest-classification.md`** (rows C38/C44/C45 vs. CC6, and others noted during this review) — those
  rows currently sit in a `conv:` destination for lack of a better place; if a bundle mechanism is adopted,
  some of them may be better expressed as bundle membership than as a single convention or role-kernel
  placement. The classification table is not blocked on this — per its own framing, placement is
  correctable later at no cost — but a future re-pass should check rules classified as "borderline
  posture-vs-checklist" against whatever this addendum eventually decides.

## Still open

Everything. This addendum records a question, not a design. No mechanism, no naming, no hook design, and
no timeline are decided. The next step, whenever it happens, is Dean revisiting this with a firmer sense
of direction — not a coder or planner building anything against it.
