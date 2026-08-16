# Addendum 1 — the halt rule, re-cut on reversibility

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10). The parent is **not edited**: this is the amendment channel it names. Additive; governs where
the two overlap.

**Status: APPROVED by Dean 2026-08-11.**

## At a glance

**Mission:** replace the halt rule's "never presume, never judge" line — too strict, unenforceable in
practice — with a rule based on reversibility.

**Approach:**
- Reversible ambiguity → proceed and mark (isolate the commit, tag it, log it, surface it immediately).
- Irreversible action (cluster mutation, destructive, published-history rewrite) → halt, as before.
- Already-forbidden actions (push, GitHub writes, etc.) are unchanged — never a judgment call.

**Needs you:** nothing — approved and closed. How the mark is verified was the one open item; also
resolved (see below).

**Checklist:**
- [x] Rule adopted.
- [x] Enforcement resolved: `step-check` (S3) and `plan-lint` (S6) in `step-gates-spec.md` — corrected
  2026-08-13, this doc previously said it was still open.

---

## What prompted it

The first auto-mode coder went 7/7 with all gates green, and made **four judgment calls where the rule in
force said halt**: it invented a checkable form for an undecidable `conv-lint` rule, resolved a
self-contradiction in the spec's S5 by picking one side, relocated ambiguity handling from S3 to S2, and
added three unlisted fixture directories. All four were reasonable and all four were documented.

**Dean's ruling, and it is not a retroactive blessing:**

> *"(d) is OK, however, it still overstepped given the current rule — I don't like it. Rules are there to
> obey. I accept rule change suggestions — that is fine. Everything coder did could have be proposed to me
> or to planner to fix or approve."*

So: the overstep was a violation. The channel for changing a rule is a **proposal to Dean or the spec
owner**, never a unilateral decision by the agent bound by it. That stands regardless of the amendment
below.

## The amendment

The parent design draws the line at *judgment*: never presume, never assume, never guess, never make a
judgment call. That proves too strict against an imperfect spec and too vague to enforce — an earlier
proposal to split "mechanical" from "behavioral" decisions was rejected because **that split is itself a
judgment call**, which is the thing being constrained.

Dean's cut replaces it:

> *"I am willing to let the coder act on some of these ambiguous items, provided that it is reversible.
> Given that coder commit their work anyway it may be OK to continue and not block; however, the
> assumption/presummption/guess/etc should be surfaced, documented, brought back to decision AND reverted
> when needs to be. … That said, distructive non revertable action should halt (eg run a change on the
> cluster)."*

**The axis is reversibility, not the nature of the judgment.** Reversibility is checkable against the
world; "mechanical" is an opinion.

| Situation | Action |
|---|---|
| Ambiguity whose resolution is **reversible** (code, tests, fixtures, layout, docs — anything a commit can undo) | **Proceed and mark.** Do not block. |
| Ambiguity whose resolution is **not reversible** — cluster mutation, anything outward-facing, deleting untracked data, rewriting published history | **Halt.** As before. |
| Anything already prohibited (push, GitHub writes, sibling worktrees, session state) | Unchanged: forbidden, not a judgment. |

**"Proceed" is not "decide".** The decision is still Dean's or the spec owner's. Proceeding buys time; it
does not transfer authority, and the mark is what keeps that true.

## Proceed-and-mark: the mechanism

Four obligations, all four required — three of four is a silent judgment call with extra steps.

1. **Isolate.** The judgment goes in **its own commit**, containing nothing else. A judgment entangled with
   required work cannot be reverted without losing the work.
2. **Tag.** A lightweight local tag on that commit: `judgment/<branch>/<step>-<slug>`. Local only — coders
   do not push. `git tag -l 'judgment/*'` is then the complete inventory, and
   `git revert <tag>` is the undo.
3. **Log.** In the step ledger: what was ambiguous · what was assumed · why · **how to revert** · whose
   decision it actually is.
4. **Surface, immediately.** A `spec__<topic>.md` handoff to the spec owner **at the step where it arose**,
   not bundled into the end-of-run report. The spec owner escalates to Dean via `ask__` if it is his.

## Two limits, stated rather than glossed

**Reversibility decays with depth.** Once a later step builds on a judgment, reverting it breaks that step
too — the tooling coder's S3 depended on its S2 ambiguity choice. Isolation preserves *surgical* revert only
while nothing depends on it, which is exactly why obligation 4 says immediately. A judgment surfaced at the
end of a seven-step run is, in practice, already load-bearing.

**This does not excuse a bad spec.** One of the four judgment calls existed only because the spec
contradicted itself (S5 step 1 said to read `scope`; step 2's output format omitted it). `plan-lint` cannot
catch that — a semantic contradiction is not a missing field. Amending the halt rule reduces the cost of
spec defects; it does not reduce the obligation to not write them.

## Resolved — how the mark is verified (2026-08-13, corrected: this was decided, not still open)

Split across two tools, per [`step-gates-spec.md`](step-gates-spec.md):

- **`step-check` (S3, judgment mark)** — enforced at execution time. Reads the step ledger for a
  judgment entry; requires a matching `judgment/<branch>/<step>-*` tag pointing at a commit; verifies
  isolation (the tagged commit touches only paths inside the step's `scope:` and is not the same commit
  as the step's ordinary work); requires a `session/handoffs/spec__*.md` naming the judgment (the one
  obligation checkable only by convention, not structure). Also checks the reverse: a `judgment/*` tag
  with no ledger entry is its own violation — an unlogged judgment is worse than an unmarked one.
- **`plan-lint` (S6, unresolved judgments)** — enforced before a spec is handed to a **new** coder run.
  A `judgment/*` tag counts as resolved once its commit is reverted, or a `decided:` line in the spec
  names the judgment's slug; anything else blocks the spec from being (re-)assigned, on the reasoning
  that a spec is not ready for a new run while a previous run's judgment about it is still unresolved.

So enforcement is no longer purely coder-compliance-based — both checks are speced with concrete cases,
`verify`/`done_when` criteria, and a throwaway-repo test harness using real git tags. **Still open:**
whether either tool is actually *built* yet (see `step-gates-spec.md`'s own build status) — the design
question this section originally flagged is answered; only the implementation-status question remains,
and that is a normal spec-build tracking matter, not a design gap.
