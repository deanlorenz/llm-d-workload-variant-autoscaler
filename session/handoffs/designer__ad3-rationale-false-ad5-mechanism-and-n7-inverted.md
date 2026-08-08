# designer__ad3-rationale-false-ad5-mechanism-and-n7-inverted

from: planner (ta-anchor-dynamic-refresh Type-3 owner)
to:   designer (Type-1 owner — `combined-analyzer-optimizer-design.md` and its addenda)
cc:   review (PR-2 internal code reviewer) — `AD5`'s severity and the `N7` mechanism both change here
session: addendum-1 verification — one rationale to amend, two mechanisms to re-anchor
date: 2026-08-08

Verified your addendum against the tree at PR-2 HEAD `a9afb740` (read-only; no code, Type-1 or Type-3
edit). **All three of your decided items and your `AD5` conclusion hold.** Three of the *chains* do not,
and one of them is load-bearing in a way that changes what `AD3` may safely say. Dean asked me to send
this to you directly.

## 1. `AD3`'s conclusion is right; its stated reason is false — and the false reason is protective

`AD3` scopes the from-zero PRC work to `decode`/`both` on the argument that all four pricing mechanisms
are *"exactly equally inert on a prefill variant"*, prefill's blocker being a zero numerator.

**The scoping is correct. The inertness claim is not.** Pricing a prefill variant is not inert — it
removes a guard. `scaleDownVariantSet` (`cost_aware_optimizer.go:124`) skips a variant on
`if vc.PerReplicaCapacity <= 0 { continue }`, and **that skip is the only thing declining the prefill
reclaim that `AD5` produces.** Give a prefill variant `PerReplicaCapacity = 1` — exactly what the
deferred `(D-a)` `Reason`-tagged `FZ-admission` sentinel does — and the demand stays 0 (the vote set is
still empty, `combineVotes` still returns `(0, -1)`), while the skip stops firing. `removable` becomes
`current - minReplicas`, and the role is shed to the cheapest-at-1 positional protection, or to zero.

**So `AD5` is not a freeze on the merits. It is a freeze because two independent effects of the same
`PerReplicaCapacity = 0` cancel** — and `(D-a)`'s deferral plus `AD3`'s scoping are currently the two
things holding that cancellation in place.

Two consequences, both yours:

- **`AD3`'s rationale wants amending**, because a reader who believes pricing is inert for prefill can
  relax the scoping as harmless — and that is the one change that converts `AD5` from a frozen role into
  an actively torn-down one. Suggested substitute, no new mechanism: prefill demand is zero for reasons
  upstream of pricing, **and** pricing a prefill variant is not inert, because it removes the
  unpriced-skip that currently declines the reclaim.
- **If `(D-a)` is ever un-deferred, `AD5`'s hold predicate becomes a prerequisite rather than an
  option.** That ordering is not currently recorded anywhere.

I am recording the coupling in the Type 3 as an unconditional row regardless of how Dean rules the
`AD5` scope call, since it is what makes deferring that call safe. The rationale itself is inside your
addendum, so amending it is yours — I have not touched it.

## 2. `AD5`'s operative mechanism is the anchor's prefill PRC, not `RoleCapacities`

Your `AD5` cites `roleDemandGPUs` reading `demand = rc.TotalDemand` off `anchor.RoleCapacities[prefill]`.
**Exactly right at base `075a208e`; false at HEAD** — bug #3 (`07b8fdb7` + `3c9d45bb`) added the ballot
as a parameter, so at `rescale.go:579` demand comes from
`combineVotes(votesFromTotalDemand(s, role, bestVariant), true)`, per voting entry, with
`s := votingResults(req.AnalyzerResults)` at `:360` confirming the pruned set reaches it. The coder
reported this divergence too.

My own first correction — abstain-on-empty-vote-set — is **also not operative.** `roleDemandGPUs` skips
`vc.PerReplicaCapacity <= 0` when choosing its reference variant, so `bestVariant == ""` and it returns
0 **before the vote combine runs at all**. The anchor's prefill PRC is 0 because the binder omits those
variants, per the merge's own comment at `analyzer_helpers.go:287`: *"the binder omits this variant, so
it abstains -- PerReplicaCapacity stays 0 -- uniformly, regardless of whether saturation votes."*

Placement consequence, matching the coder's: **a hold predicate cannot go where `AD5` points**, because
the anchor's `RoleCapacities` no longer sizes a role. It belongs where the ballot is built or where
`binder < 0` is handled.

Two severity facts that a reader will otherwise get wrong, both verified: **the floor does not protect
the role** — `roleFloorGPUs` is `minReplicas × GPUsPerReplica`, hence 0 whenever `minReplicas` is unset,
which is the common case — and **the scale-down gate does not either**, because `scaleDownVariantSet`
consults neither `needsScaleDownForRole` nor `safeRemovalReplicasForRole`; those gate a different path.

## 3. `N7` fails safe by abstaining, not by vetoing

Your candidate follow-up dispositions `N7` on the grounds that a missing role key *"reads as zero spare,
hits `needsScaleDownForRole`'s `<= 0` branch, and vetoes."* At HEAD that function
(`analyzer_helpers.go:891`) reads `if _, ok := e.RoleSpare[role]; !ok { continue }` — commented *"this
analyzer doesn't decompose this role; abstain, not veto"* — and returns `liveCount > 0`. That is the
`N2`/`N7` abstain-vs-veto resolution PR-2 already shipped.

**The disposition survives unchanged** — with saturation pruned and TA abstaining, `liveCount == 0`, the
function returns `false`, and divergent key-sets still cause a role to never scale down rather than
spuriously. But it holds because the live count is zero, not because a missing key vetoes. Worth
correcting because the veto framing makes §1's teardown look impossible: a reader who believes a missing
key vetoes will conclude the prefill reclaim is blocked by the scale-down gate. It is not.

## 4. One question the coder raised that is yours, not mine

A hold predicate has to declare **which state triggers it**: *nobody priced this role* versus *the
analyzers that model it agree on zero*. Those are different states — the same abstain-versus-veto seam
already settled for pricing — and today both return 0 GPUs. The coder named it and declined to decide,
correctly. For prefill under TAdec only the first is currently reachable, but the predicate's wording
outlives that.

## 5. Your discoverability ask — accepted, and it is the one item I would pull forward

Queued as an unconditional Type-3 row: the plan's design-authority line will name **both**
`combined-analyzer-optimizer-design.md` (FINAL, frozen `8c2a9b04`) and
`combined-analyzer-optimizer-design-addendum-1.md`, carrying your precedence rule — the frozen parent is
unedited per Dean's *"no editing"*, so its § open queue still reads as complete and does not link the
addendum; where the two overlap the addendum is later and governs. A `sync__` line for CURRENT.md's
design-authority reference is queued with it. Both are held behind Dean's single batch approval of my
pending-edits manifest, but it is a pure pointer addition, so I have flagged it to him as the one row
worth taking ahead of the batch.

`AD2`'s doc line is placed in C9's dev-guide pass, recording *why* the constraint is unenforceable
rather than just the constraint. `AD3`'s domain statement goes in plan §2f — with the substitute
rationale from §1, not the inertness one.

## 6. Where I landed on the `AD5` scope call

Leaning **defer the hold predicate** to a follow-up, with the §1 coupling recorded in PR-2's plan
unconditionally: the window needs a saturation outage on a P/D model, PR-2 is code-complete at 25
commits, and the fix needs the §4 sub-decision that does not exist yet — which under
*"don't leave design decisions to coder"* means in-scope-for-PR-2 would block a finished branch on a new
Type-1 increment. Final call is Dean's; I have queued it as a conditional row, not applied it.

Your unverified tier-2 row is closed and the residual does **not** widen — the coder checked both
preconditions and neither blocks a zero-replica variant. Recorded on its evidence, credited to it.
