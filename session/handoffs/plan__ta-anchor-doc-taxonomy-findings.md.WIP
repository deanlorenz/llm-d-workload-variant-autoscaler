from: review
to: planner
session: ta-anchor doc-taxonomy findings (out of reviewer scope)

## Why this handoff

While answering a question from Dean about which Type 1 governs the anchor mission and which Type 3
is being implemented, I surfaced five doc-structure findings. Dean's ruling: these are **beyond the
reviewer's scope** — my job is code-vs-the-specific-Type-3. He asked that the findings not be lost,
so they are recorded here rather than in my review doc.

**Nothing here is a code finding and nothing here needs the coder.** All five are taxonomy /
doc-currency observations for you (and ultimately Dean) to accept, reject, or defer. I am not acting
on any of them.

All statements below were verified against files on the `plans` worktree at plan tip `e0aa9bad` and
branch tip `d9f3b97e`.

## T1 — the Type 1 named as design authority is DRAFT and unlocked

`planning/combined-analyzer-optimizer-design.md` header reads:

> **Type:** 1 (design) · **Status:** DRAFT (capture of a live design discussion, 2026-08-02; not yet locked)

Both `ta-anchor-refactor-v2-plan.md` (PR-1, FINAL) and `ta-anchor-dynamic-refresh-plan.md` (PR-2)
name it as **Design authority** in their headers. PR-1 is code-complete (5 commits) and PR-2 has 9
of 13 commits landed against it.

CONVENTIONS Type 1: *"Written and frozen before coding starts. Only reopen for architectural
replanning."* It is not frozen. This may be a deliberate call given the mission's pace — but if so,
the status line should say so explicitly (e.g. "DRAFT — knowingly unlocked; PR-1/PR-2 ship against
it") rather than "not yet locked," which reads like an oversight to anyone arriving cold.

## T2 — PR-2's stated correctness authority is a DRAFT code map, not the Type 1

PR-2 §0 states the correctness scope is **"§9 of the reviewer-owned
`multi-analyzer-dataflow-map.md` whole (the authoritative correctness scope; findings N1–N9)"**, and
the coding-start reading list repeats it.

That file's own header reads `**Status:** DRAFT — first pass, synthesized from six parallel
read-only code traces`, and self-caveats that the bulk of §3 *"was not yet independently re-verified
line-by-line and should be treated as 'high confidence, not adversarially checked.'"*

So PR-2's grounding is genuinely **split across two documents**: the Type 1 for the contract, and a
section of a DRAFT current-code map for the bug list it implements. The map is not a design doc and
has no type designation. Worth deciding whether N1–N9 should be promoted into the Type 1 (or into
PR-2 §2 verbatim) so the plan is self-sufficient, per the Type 3 rule that a plan should carry
enough state to resume cold.

## T3 — a Type 6 review doc is the Spec source for a Type 3

`ta-anchor-refactor-v2-plan.md` header:

> **Spec source:** [`ta-anchor-refactor-review.md`](ta-anchor-refactor-review.md) **Part 2**
> (§2.1–§2.7) — the corrected two-phase mechanism

`ta-anchor-refactor-review.md` is `**Status:** DRAFT` and carries four distinct payloads in one
file: Part 1 (review of the now-SUPERSEDED plan), Part 2 (the redesign spec PR-1 was built from),
Part 3 (review of the v2 plan), Round 2 (2026-08-05 re-review).

Net effect: the authoritative mechanism spec for **shipped PR-1 code** lives inside a draft review
document, in a part that is not itself a review. CONVENTIONS puts Type 6 as review *output*
consumed by the planner — not as a spec a Type 3 depends on. Two clean resolutions: fold Part 2 into
the Type 1 (or into PR-1 §2) and leave the review doc pointing at it, or split Part 2 out into its
own doc with a proper type. Either way PR-1's `Spec source:` line should end up pointing at a
non-DRAFT, single-purpose doc.

## T4 — grounding fan-out: four docs, nine-plus sections, for one commit

To implement C6c correctly the coder must hold simultaneously:

1. Type 1 § anchor / § combine / § bugs / § sort / § rescale — 5 sections, DRAFT
2. `multi-analyzer-dataflow-map.md` §9 (N1–N9) — DRAFT
3. PR-1 plan §2 / §3 / §12
4. PR-2 plan §2 #5 / §2d.4 / §2d.5 / §2d.6

Four documents, two of them DRAFT. This is the **structural** half of my review doc's Finding 21
(the coder's C6c handoff written against an 8h-stale plan); the trigger-polling gap is the other
half. Reducing the fan-out — even just inlining N1–N9 into PR-2 §2 — would shrink the surface on
which staleness can occur, independent of any change to how triggers are delivered.

## T5 — no doc carries a currency marker, so cached reads go stale invisibly

Neither the Type 1 nor either Type 3 records its own revision. Combined with the micro-rules
`Read offset:N limit:M` fetch pattern, a cached section is indistinguishable from a current one from
the inside, and a structural edit silently invalidates every downstream line range.

Concrete evidence this is already biting: you had to write a trigger literally named
`ta-anchor-dynamic-refresh__c6c-line-ranges-shifted.md` (09:24) — and it travels on the same
unpolled channel it is warning about. The PR-2 plan itself has **16 revisions**, 8 of them inside
one 8-hour window.

I had the identical defect in my own file: `ta-anchor-dynamic-refresh-review.md`'s header pinned
`plan tip 62c37c46`, stale by 8 commits. **I have fixed mine** and added per-finding plan-revision
attribution. Flagging the general pattern because a one-line `**Plan revision:** <sha>` in each
doc header (and in each Type 3 TOC block) would make staleness cheap to detect instead of
undetectable. Governance-flavoured, so it likely belongs in
`planning/governance-follow-ups.md` — which is not mine to write.

## Already handled, listed only so it is not re-raised

`analyzer_helpers.go:550` cites `combined-analyzer-optimizer-design.md` from **shipped code** — a
plans-branch doc invisible to a merged-code reader, i.e. a §4a violation. You already caught this
in PR-2 §7 and scoped it to C9 with the right call ("delete the citation rather than repointing
it"). No action needed; my §4a re-sweep after C9 will confirm it.

## What I am doing next

Nothing on any of the above. Returning to my actual scope: C6c/C6d/C10/C9 code review against
PR-2's Type 3 when the coder resumes. Per Dean, I sit still until then.
