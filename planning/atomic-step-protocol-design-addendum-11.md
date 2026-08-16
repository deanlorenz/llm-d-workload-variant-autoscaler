# Addendum 11 — every auto-tool tracks tokens spent; a session bounds what its own protocols consume

**addendum** · **Status: FINAL — standing requirement, corrected 2026-08-16.**

## At a glance

**Mission:** state, as a cross-cutting requirement on the whole checkpoint/handoff/sync-watcher
family, two rules Dean called critical: (1) every auto-tool (Tier-1, Tier-2, handoff-watching,
handoff-processing) must record the tokens it spends; (2) mechanical model work defaults to the
simplest model where possible, but a tool using the current session's own model is fine — the
critical concern is **total consumption**: a session must bound how many tokens its own automatic
protocols burn, so a busy handoff cycle or a bad monitor loop can't quietly eat the session's whole
budget the way it has before.

**Approach:** audit found no live violation — `tick-shared-scan.sh`/`tick-consolidate.sh` already
record spend (`.tier2-usage.log` + `--daily-cap`) and default to a small model
(`aws/claude-haiku-4-5`). The gap is that nothing states either rule as binding on future tools in
this family, and Tier-1/handoff-watching currently spend no tokens at all (pure shell) so have
nothing to record yet — the rule must be written down now, before any of them grows a model call or
a chatty loop, not discovered as a regression later.

**Needs you:** nothing blocking. This addendum states the rule; no code changes it, since nothing
currently violates it.

**Checklist:**
- [x] State the rule (this addendum; corrected once already — see Correction below).
- [ ] When any of Tier-1 / handoff-watching / handoff-processing grows a model call for the first
  time, that change must land with token accounting in the same commit, not after.
- [ ] When any auto-tool's *cadence* changes (a new monitor loop, a tighter poll interval, a new
  handoff-triggered action), check it against a bound on total consumption before shipping, not after
  a session discovers its context is gone.
- [ ] Add a cross-reference from `checkpoint-capture-spec.md` and `sync-watchers-spec.md` (both
  govern tools this rule binds) — not yet done, do at next touch of either.

---

## ⚠️ Correction (2026-08-16, same day) — an earlier draft of this addendum misstated rule 2

The first version of this addendum wrote a "watch for escalation to the expensive model" rule that
Dean never said — an invented embellishment, not a restatement. Dean's correction, verbatim: *"Some
actions use the current session's model and that is OK. I only asked to track the AMOUNT of tokens
used -- if there is excessive automatic tooling activity (eg a handoff cycle) then I don't want it to
consume all my tokens. This already happened before. Agents became too chatty sending multiple
handoff and using a lot of tokens OR agents setting bad monitors and having to analyze text every 30
sec."* The rule below is corrected to match; the concern is total consumption from automatic
activity, not which model a tool happens to call.

## The rule

**1. Every auto-tool records token spend.** "Auto-tool" means any script or automatic protocol in
this family that runs without a human watching each invocation: Tier-1 (`session-snapshot.sh`),
Tier-2 (`tick-consolidate.sh`, `tick-shared-scan.sh`), handoff-watching (`sync-current-watch.sh`), and
handoff-processing (whatever eventually automates folding a `sync__` handoff into CURRENT.md, if that
ever stops being a model-driven skill invocation). A script with no model call has zero tokens to
record and that is a valid, correct state — but the *moment* a model call is added, a record of its
cost must be added in the same change, not as a follow-up.

**2. Mechanical model work uses the simplest model where possible — but using the current session's
own model is fine when that's the natural shape of the action.** `tick-consolidate.sh`'s choice
(`aws/claude-haiku-4-5`, invoked from a neutral `cd /tmp`) is the reference shape for genuinely
mechanical, tool-free classification work. Not every auto-tool is that shape — some legitimately act
through the current session (a handoff read/reply, a monitor's analysis) and there is nothing wrong
with that on its own.

**3. The critical concern is bounding total consumption from automatic activity — this is the half
that actually matters.** A session's own protocols (handoff cycles, checkpoint loops, monitors) must
not be allowed to consume an unbounded share of that session's tokens. **This has happened before,
twice, in two different shapes**: agents grew too chatty, sending multiple handoffs back and forth
and burning tokens on the exchange itself; and agents set up monitors that re-analyzed text every
~30s, paying the cost of a fresh read on every tick rather than reacting only to real change. Either
shape can quietly consume a session's whole working budget through activity the session didn't
consciously choose to spend on. Every automatic protocol needs a bound — a cap, a rate limit, or a
design that only spends on genuine state change — appropriate to what it does; the specific bound is
a per-tool design choice, not fixed here.

## Why this is Final, not Open

Dean's framing was explicit and direct ("this is critical"), and both halves are simple enough to
state without a full design pass: record what's spent, and make sure nothing automatic can burn an
unbounded share of it. What's genuinely open is narrower than the rule itself — see below.

## What's still open, not resolved here

- **No shared token-accounting mechanism exists outside Tier-2's own `.tier2-usage.log`.** If Tier-1
  or handoff-watching ever needs one, whether they get their own ledger or share Tier-2's is a design
  choice for whenever that need actually arises — premature to design a shared ledger for a token
  spend that doesn't exist yet.
- **No general bound exists yet on handoff-cycle chatter or monitor cadence** — Tier-2's
  `--daily-cap` is the one concrete precedent for what a bound looks like, but nothing generalizes it
  to handoffs or Monitor-tool usage. A future addendum could design this; not attempted here.
- **No enforcement mechanism** (lint, review-time check) verifies a new tool actually follows either
  half of this rule before it ships — this addendum states the requirement; catching a future
  violation is still manual (code review) unless a future addendum adds a real check.

## Provenance

Dean, 2026-08-16, mid-turn note during the `sync-main` generalization (B6) work: *"every auto tool
(tier 1, tier 2, handoffs watch, handoff process) should record token used for those tools. any
mechanical model work for all those tools should be in a simplest model. If tools calls current model
then tokens must be watched. this is critical."* First draft of this addendum overread that into a
"watch for model escalation" rule; corrected same day per Dean's direct pushback (quoted above) —
the actual concern is bounding total automatic-activity consumption, with two concrete prior
incidents (chatty handoff cycles, 30s-cadence monitors) as the evidence. Audited against current code
before writing either version — confirmed no live violation in either reading.
