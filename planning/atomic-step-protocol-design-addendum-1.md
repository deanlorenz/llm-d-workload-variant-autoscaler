# Addendum 1 — the halt rule, re-cut on reversibility

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10). The parent is **not edited**: this is the amendment channel it names. Additive; governs where
the two overlap.

**Status: APPROVED by Dean 2026-08-11.**

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

## Still open

**How the mark is verified.** Nothing yet checks that a judgment commit was isolated, tagged, logged and
surfaced — today all four rest on the coder complying, which is the same trust that just failed. Candidates:
`step-check` refusing when the ledger records a judgment with no matching tag, or `plan-lint` cross-checking
tags against handoffs. Dean's phrasing was *"Not sure about the checkpoint mechanism, perhaps tags"* — tags
are adopted here as the marker; the enforcement around them is undecided.
