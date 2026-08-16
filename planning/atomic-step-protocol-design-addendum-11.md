# Addendum 11 — every auto-tool records token spend; mechanical model calls stay on the cheapest tier

**addendum** · **Status: FINAL — standing requirement, 2026-08-16.**

## At a glance

**Mission:** state, as a cross-cutting requirement on the whole checkpoint/handoff/sync-watcher
family, two rules Dean called critical: (1) every auto-tool (Tier-1, Tier-2, handoff-watching,
handoff-processing) must record the tokens it spends; (2) any mechanical/tool-invoked model call
defaults to the simplest model, and if a tool ever calls the current (expensive) session model
instead, that spend must be watched, not silently absorbed.

**Approach:** audit found no live violation — `tick-shared-scan.sh`/`tick-consolidate.sh` already do
both correctly (`.tier2-usage.log` + `--daily-cap`, default model `aws/claude-haiku-4-5`). The gap is
that nothing states this as a *requirement* binding future tools in this family, and Tier-1 /
handoff-watching / handoff-processing currently spend no tokens at all (pure shell) so have nothing to
record yet — but the rule must be written down now, before any of them grows a model call, not
discovered as a regression later.

**Needs you:** nothing blocking. This addendum states the rule; no code changes it, since nothing
currently violates it.

**Checklist:**
- [x] State the rule (this addendum).
- [ ] When any of Tier-1 / handoff-watching / handoff-processing grows a model call for the first
  time, that change must land with token accounting in the same commit, not after.
- [ ] Add a cross-reference from `checkpoint-capture-spec.md` and `sync-watchers-spec.md` (both
  govern tools this rule binds) — not yet done, do at next touch of either.

---

## The rule

**1. Every auto-tool records token spend.** "Auto-tool" means any script in this family that runs
without a human watching each invocation: Tier-1 (`session-snapshot.sh`), Tier-2
(`tick-consolidate.sh`, `tick-shared-scan.sh`), handoff-watching (`sync-current-watch.sh`), and
handoff-processing (whatever eventually automates folding a `sync__` handoff into CURRENT.md, if that
ever stops being a model-driven skill invocation). A script with no model call has zero tokens to
record and that is a valid, correct state — but the *moment* a model call is added, a record of its
cost must be added in the same change, not as a follow-up.

**2. Mechanical model work defaults to the simplest model available.** `tick-consolidate.sh`'s own
choice (`aws/claude-haiku-4-5`, a small model, invoked from a neutral `cd /tmp` so it inherits no
project context) is the reference shape: text-in/text-out classification only, no tool use, minimum
viable context. Any new mechanical tool doing model-driven work follows the same shape by default.

**3. If a tool ever calls the CURRENT (session) model instead of a cheap one, that spend must be
watched — this is the critical half, not a formality.** The failure mode this guards against: a
mechanical tool that quietly escalates to the expensive model (because it's easier to reuse the
calling session's own model, or a future change defaults to it) burns cost silently, at the exact
"nobody is watching" moment auto-tools are designed to run in. If this ever happens, it needs its own
visible tracking (not folded anonymously into a generic token count) so it can be caught and
questioned, not discovered months later in a bill.

## Why this is Final, not Open

Dean's framing was explicit and direct ("this is critical"), and the two halves are simple enough to
state without a design pass: record what's spent, default cheap, watch any escalation. What's
genuinely open is narrower than the rule itself — see below.

## What's still open, not resolved here

- **No shared token-accounting mechanism exists outside Tier-2's own `.tier2-usage.log`.** If Tier-1
  or handoff-watching ever needs one, whether they get their own ledger or share Tier-2's is a design
  choice for whenever that need actually arises — premature to design a shared ledger for a token
  spend that doesn't exist yet.
- **No enforcement mechanism** (lint, review-time check) verifies a new tool actually follows this
  rule before it ships — this addendum states the requirement; catching a future violation is still
  manual (code review) unless a future addendum adds a real check.

## Provenance

Dean, 2026-08-16, mid-turn note during the `sync-main` generalization (S6/B6) work: *"every auto tool
(tier 1, tier 2, handoffs watch, handoff process) should record token used for those tools. any
mechanical model work for all those tools should be in a simplest model. If tools calls current model
then tokens must be watched. this is critical."* Audited against current code before writing this
addendum — confirmed no live violation, confirmed the gap is the absence of a stated rule, not a bug.
