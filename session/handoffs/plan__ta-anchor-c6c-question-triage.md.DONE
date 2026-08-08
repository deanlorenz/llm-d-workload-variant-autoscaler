from: review
to: planner
session: ta-anchor-dynamic-refresh PR-2 review — C6c question triage

## Why you are getting this

The coder is holding C6c on six design questions
(`ta-anchor-dynamic-refresh/plans-handoff-outbox/plan__ta-anchor-c6c-fairshare-currency.md`, 08-07
10:54). I triaged the premises before you spend a round answering them. **Three are genuinely open and
worth your time. Two you have already answered — in the coder's own preferred direction. One rests on a
premise §2d.4 (c) explicitly forbids.**

Full detail: review doc Finding 21 (`28a7ac09`).

## The cause is mechanical, not judgment

The handoff quotes plan text that changed at `ffb945c1` (08-07 **05:01**) — five hours fifty-three
minutes before it was written. Four independent pre-`ffb945c1` quotations:

| Handoff says | Current plan |
|---|---|
| "the plan's **four-site** list" | **Five** (L239) |
| "The plan does not mention the fallback at all" | site **(v)**, L305-321, + fixture L1047 + sweep L1275 |
| (iii) note: "coordinate all **three** edits" | "coordinate **both** edits" (L295) |
| `quota-limiter.md`: "§5 never lists this file" | C6c row has listed it, with the two-copies count, since `ffb945c1` (L186) |

**Seven** of your triggers sit unconsumed as `.md` in `session/handoffs/` — including
`c6c-prcref-and-token-sweep`, `c6c-fixture-level`, `c6c-fsv-copy-count`,
`c6c-source-citations-reverified` and `c6c-c6d-c10-plan-updates`. Each points at exactly the text a
question re-asks. The coder has `kickoff` and `c6-answered-plus-c10` at `.WIP`. Routing, not
comprehension — how you handle that is yours; I am flagging the state, not prescribing.

## Triage

| Q | Verdict |
|---|---|
| **Q1** signature | **settled** L249-253 = its lean (a), with a reason it did not state (identical `v_role` on both sides). Its *scope* half is new and **would do damage if folded** — below |
| **Q2** fallback ("a plan gap") | **not a gap.** Site (v) prescribes its (a) and forbids its (b). One-sentence residual |
| **Q3** site (iv) shape | **genuinely open** — L301 offers two shapes, chooses neither. Its third shape looks better; I have mechanism input |
| **Q4** priority in the cap | **confirmed gap, credit the coder** — "priority-scaled" appears nowhere in the plan |
| **Q5** move (iii) to C6d | **premise wrong** — the plan forbids the coupling it assumes. (iii) can land in C6c |
| **Q6** T1.4 shape | **agree** — and it independently re-derived `70c985b9`'s unit-level conclusion without having read it |

## Q1's scope half — the one to be careful with

It proposes extracting `cheapestSizedVariantForRole` so fsv, `fairShareRolePick` and `roleDemandGPUs`
"converge", because *"if they disagree, fsv is denominated in a variant the allocator never picks, which
is the same class of bug C6c exists to fix."*

**They are allowed to disagree, and site (ii) is the compensation.** L259-263 exists precisely because
the picker falls through past `v_role` on `gpusAvail < gpusPR` (`:420`) and `headroom <= 0` (`:427`),
and the `prcRef` ratio rescales the cap for whichever candidate it lands on. Forcing agreement is not
possible — the picker *must* fall through. My concern is narrow and specific: folding "make all three
agree" invites the reading that the ratio is redundant, which is the `prcRef` correction undone.

The count is also off. At `d9f3b97e` there are **four** such loops, not three — `fairShareRolePick`
(`greedy_score_optimizer.go:410`), `costGreedyRolePick` (`cost_aware_optimizer.go:85`, loop `:94`),
`fillRole` (`rescale.go:431`, loop `:439`), `roleDemandGPUs` (`rescale.go:569`, loop `:572`) — and
**none is a cheapest-sized-variant selector.** All four take the first *feasible* candidate;
`roleDemandGPUs` also scopes to one accelerator via `variantsOnType`, so its "cheapest" differs by
construction. A helper as specified would have exactly **one** consumer in C6c's design — fsv's
`v_role`, which is `prcRef`'s reference by definition.

## Q5 — the premise is what §2d.4 (c) forbids

It defers (iii) because "C6d changes the abstain/veto shape of `votesFromRoleSpare`". Both halves fail:

- §2d.4 (c) states the fix as a per-variant re-check **in `safeRemovalReplicasForRole`** and says: *"Do
  **not** express this as a synthetic 0-vote inside `votesFromRoleSpare`."* C6d gates that function's
  *return*; the ballot is untouched, so the binder `sortVariantsForScaleDown` reads is untouched.
  (`safeRemovalReplicasForRole` calls `combineVotes(votesFromRoleSpare(s, role, v), false)` at
  `analyzer_helpers.go:633`; `sortVariantsForScaleDown` is a separate consumer of the same ballot.)
- N7 abstain is **C7**, landed at `952d2fff`. The shape (iii) reads is already final.

Your revision of (iii)'s note is **correct** and Q5 is answered by reading it. Worth keeping from Q5:
its two mechanical notes are right and are **not** in the plan — `sortVariantsForScaleDown(s, roleVCs)`
takes no `role` (`cost_aware_optimizer.go:165`) and both callers have one in scope (`:446`,
`rescale.go:414`), verified; and mapping a no-ballot variant's binder `-1` to tie-break key 0 preserves
today's `weighted` result for the same input.

## Q3 — my input, which the coder could not have

Its third shape converts the *bound* into each analyzer's units and leaves `ps` in raw capacity. My C6c
checklist carries "measure whether converting site (iv) to replica space preserves the loop
compensation, since `k = floor(deltaUtil·demand/prc)` (`analyzer_helpers.go:788`) reads demand against
PRC." Under the coder's shape `ps` stays commensurable with `prc`, so **that question dissolves**; it
arises only under the plan's first phrasing. Independent evidence for its shape.

Its sub-question (an analyzer with no PRC for `v_role` left unclamped) is sound for the reason given —
it cannot participate in `votesFromPickerState` for `v_role` either, so it cannot drive allocation of
`v_role`.

## Q4 — confirmed, plus one extension

`priority-scaled` appears nowhere in the plan; L255 says "the fsv-unit `target`" without saying that
unit carries `priority`. Extension: site (v)'s fix **deliberately drops** `priority` from the fallback
(L310) — necessary, since including it would make the fallback ≤ 0 whenever it fires — so post-C6c the
primary is priority-scaled and the fallback is not. Site (v)'s "fixes the currency" should be read as
*fixes the demand→replica conversion*, not *makes the two paths equal*. The residual cross-model
incomparability in `computeMean` / `sortByRemainingDesc` is **pre-existing and narrowed, not
introduced**, and unreachable in production for the reason you already give at L316-318.

## Q2's residual

The fix is fully specified, so the code lands right regardless. The ask itself is fair and cheap: (b)'s
"falls out of the participation filter" holds only because the *fixed* fallback also carries that
filter. One cross-reference in (b)'s text closes it. Note their stated motivation for keeping the
fallback ("the only thing standing between `priority: 0` and a model that never scales") is undercut by
`ApplyDefaults`; your reachability paragraph is the better reason for the same conclusion.

## Boundaries

Answering Q1's extraction, Q3's shape and Q4's comment is yours. Whether C10 jumps §1.1's git order
(offered at the end of the coder's handoff) is Dean's. I am reporting on *premises*, which is
checkable, and leaving the forks alone.

**No action needed from the coder on this handoff** — it is a triage note for you, and the coder's own
handoff is still yours to answer.
