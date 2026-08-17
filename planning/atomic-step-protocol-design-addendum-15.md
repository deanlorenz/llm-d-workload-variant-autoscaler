# Addendum 15 — the mission restated: roles are entry points into the same on-demand mechanism

**Status: Dean's own restatement of the mission, 2026-08-17. Corrects a framing drift in Addenda
13/14 — roles are not a separate design problem, they are one instance of the mission's single
mechanism.**

## At a glance

**Mission of the whole atomic-step-protocol effort, restated by Dean, verbatim intent:** break
`CONVENTIONS.md`, `CURRENT.md`, `CODER-CONVENTIONS.md`, and memories into manageable, load-on-demand
pieces. The total amount of content does not shrink — *"the list grows as more incidents and
clarifications are needed. That is why the list is so big now — it grew over time"* — what changes is
that nothing is pre-loaded wholesale. Everything is fetched by name, on demand, when actually needed.

**Correction this makes to Addenda 13/14:** those two treated "designing the 11 roles" as build work —
survey what exists, find gaps, propose a build order. That is not wrong as research, but it drifted
from the actual mission. **Roles are not a new thing to design. They are entry points into the same
on-demand mechanism `conv <name>` already is.** The real work is what it always was: harvest existing
content (mostly already correct) into that mechanism, and find gaps — not invent role content from
scratch.

**Needs you:** confirm this collapses Addendum 13's "build order" into "harvest order" — there is no
separate role-kernel-authoring step distinct from the harvest Phase 6 already names.

**Checklist:**
- [ ] Re-read Addendum 13's per-role table as a **harvest-coverage** table, not a build-readiness
  table — the "richest existing material" roles (sync, coder) are the ones closest to already being
  correctly harvested, not the ones to "build first."
- [ ] Treat every role-kernel "prompt" as the same shape as a convention: short, fetched on demand,
  triggered by something specific (a role starting, a role asking a specific question) — not preloaded
  prose.
- [ ] Confirm `scope:` on a convention (`atomic-step-protocol-design.md`'s own still-open question,
  line 929-931) is answered by this: scope names which role(s) may fetch a convention; it was never
  meant to gate a *standing kernel* vs *fetched* split, because roles preload almost nothing standing
  either.

---

## The mechanism, restated in Dean's own words

*"We have conventions that define everything. We have memories as extra conventions. The total[]
list will not change (maybe a few more or a few less) — the list grows as more incidents and
clarifications are needed. That is why the list is so big now — it grew over time."*

*"The idea behind the micro-rules is that instead of a big pre-loaded list we load it on demand. We
load specific rules and conventions when we need them."*

*"Roles are no different. They are just entry points. Any session loads global conventions. Roles
load role-specific conventions. Both these 'loads' are on demand. The key for each role is to know
what it needs to pre-load, what it needs to call on demand, what triggers it."*

**This is the load-bearing sentence for the whole role-design thread:** a role is defined by (a) the
small amount it pre-loads at entry, (b) the larger amount it can fetch on demand, and (c) what
triggers each fetch — not by a large standing document. The existing `conv <name>` mechanism
(`atomic-step-protocol-design.md` § Micro-conventions, § Addressing and fetch) already *is* this
mechanism. A role is not a new kind of thing needing a new mechanism; it is a **named entry point**
that determines which conventions get fetched and when.

## What a role-kernel "prompt" actually is

*"Since I treat the micro-rules as on demand pre-packed prompts, the rules for roles can be just
that — a short prompt that defines the session's context. That is how I started anyway ('you are a
coder in the XX worktree, working in YY, you should..., you should not...'). I don't want to preload
long prose. Just very clear short 'memories'. When a role asks how to commit it can load the commit
micro rules set. When it asks how to send a handoff it loads the handoff micro-rule set, etc."*

Concretely, per this framing:

- **A role's own kernel is short** — the "you are a coder in worktree X, working on Y, you should...,
  you should not..." shape Dean already used by hand before any of this tooling existed. Not a
  restatement of every coder convention; a pointer plus the few things that must be true *before*
  anything else loads (worktree, scope, what NOT to do without asking).
- **Everything else is the same `conv <name>` fetch other steps already use.** "When a role asks how
  to commit it can load the commit micro-rules set" is exactly `conv commit-dco` (or equivalent) —
  no role-specific fetch mechanism needed, the existing one already generalizes.
- **This directly answers `atomic-step-protocol-design.md`'s own open question** (line 929-931,
  "How `scope:` on a convention relates to the role kernels... `scope:` governs which roles may cite
  it"): scope was never meant to distinguish *standing* from *fetched* — under this framing, almost
  nothing is standing for any role, coder included. `scope:` just names which role(s) a convention
  applies to, so the right role fetches the right convention when its trigger fires. The
  standing-vs-fetched split Addendum 4 worried over (the "reaffirmed rule bundle" question) may
  collapse into the same answer: a bundle is just a named set of conventions a role's kernel fetches
  together at one trigger point, not a third category.

## What's actually left to do — harvest and gap-detection, not authoring

*"We already have the per-role conventions in place. The plan documents may not reflect what we have
100% accurately. We may have some mistakes too. We mainly need to harvest. Detect gaps."*

This directly corrects Addendum 13's framing. Addendum 13's per-role table ("kernel content exists?
skill exists? coverage") is still useful, but its implicit next step ("build a kernel for this role")
is wrong. The actual next steps, per this restatement:

1. **Harvest** — move each role's already-correct content (mostly already in `CONVENTIONS.md`/
   `CODER-CONVENTIONS.md`/memories) into the `conv <name>`-fetchable form. This is Phase 6, already
   named in the roadmap — not a new phase for roles specifically.
2. **Detect gaps** — Addendum 13's five findings (verify's step-order defect, sync's 0/302 token
   usage, triage's wrong output type, the two doc discrepancies) are exactly this kind of gap-detection
   work, and remain valid and useful. They are findings from doing the harvest carefully, not
   blockers to a "build."
3. **Correct mistakes found along the way** — the plan documents (`doc-and-session-model.md`,
   `role-skills-spec.md`, the addenda) may not 100% reflect what's actually true today; harvesting is
   also where those mistakes surface and get fixed, the same way Addendum 13's five findings did.

## The goal, restated plainly

*"Remember, the goal is not to define everything we need about roles upfront. The main goal is to
break CONVENTIONS, CURRENT, CODER_CONVENTIONS, memories, ... into manageable load-on-demand pieces."*

Roles are downstream of that goal, not parallel to it. Designing "all 11 roles" as a standalone
exercise (what Addenda 13/14 were drifting toward) risks defining role content upfront that the
harvest would otherwise have produced correctly and more cheaply by just moving what already exists.
The corrected sequence: **harvest first** (per role, as part of the same Phase-6 pass everything else
goes through), **let gaps surface during harvesting** (as Addendum 13's five findings already did),
**fix what's actually broken**, and only write new role content from scratch where the harvest finds a
genuine hole — which per Addendum 13's own table is realistically only `pr` and `policy-writer` (and
policy-writer's own gap is structural: it has no input until the harvest itself runs, so it is last by
necessity, not by a build-order preference).
