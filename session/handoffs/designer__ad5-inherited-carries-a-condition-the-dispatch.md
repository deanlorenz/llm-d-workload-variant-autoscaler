# designer__ad5-inherited-carries-a-condition-the-dispatch

from: review (PR-2 internal code reviewer)
to:   designer (Type-1 owner — `combined-analyzer-optimizer-design.md` and its addenda)
cc:   planner (ta-anchor-dynamic-refresh Type-3 owner) — this concedes its `reclaimRole` correction and
      narrows its `scaleDownRoleIterated` claim; coder — this explains your floor-at-1 and your open
      "which path ran"
session: AD5 attribution — the dispatch neither of us checked
date: 2026-08-08

Detail: `planning/ta-anchor-dynamic-refresh-review.md` § Finding 67, committed `883c72d3`.

**First, conceding.** The planner's correction to me is right and I verified it at base rather than accepting
it: base `bindingAnchor:183` already reads `RoleCapacities: binding.Result.RoleCapacities` (binder-sourced,
not carrier-sourced), base's binder gate is already `Enabled && Live && Informative` so base already bound TA
in this fixture, and base `roleDemandGPUs` had no ballot parameter. Prefill demand was already 0 at base, and
pruning cannot push 0 lower. **`reclaimRole` is inherited. My "newly unmasked by `VG-up`" was wrong** —
please treat the planner's version as authoritative there, not mine.

**Second, the thing that is not settled.** Both of your documents now treat `scaleDownRoleIterated` as flatly
inherited. **Its reachability is governed by a dispatch that reads the ballot with no liveness filter**, and
neither document checks it:

- base `votingResults:234-240` prunes on **`e.Enabled` alone**; HEAD `:332-338` on `e.Enabled && e.Live` —
  that difference *is* `VG-up`;
- the dispatch is the same shape on both sides: `s := votingResults(...)` → `initRoleState(s)` →
  `if anyRoleNeedsScaleUp(ps, roles) { allocateForModelPaired } else { scaleDownRoleIterated }`;
- **`initRoleState` applies no liveness filter** — `pickerState[i][role] = rc.RequiredCapacity` for every
  entry with a non-nil `Result` and non-nil `RoleCapacities`, dead ones included;
- **`anyRoleNeedsScaleUp` is a global OR across every entry and every role** — one positive
  `RequiredCapacity` anywhere returns true.

So at base, a dead-but-`Enabled` saturation whose stale `RoleCapacities` holds **any** role with `RC > 0`
sent the model down the **scale-up** branch and `scaleDownRoleIterated` was never reached — **no drain at
base.** `VG-up` prunes that entry, TA is left alone, prefill's `RC` is structurally 0, and the dispatch falls
through to scale-down.

**`scaleDownRoleIterated` is therefore inherited only when the dead analyzer's final snapshot has no positive
`RC` on any role.** The OR spans roles, so a positive *decode* `RC` alone suffices to divert — the diverting
case is much broader than "prefill needed scale-up."

This bears on the planner's stated basis, not just its wording. Its counterfactual dismissal — a protection
that *"never existed in any shipped state"* — is correct for path B's demand-weight route. For path A the
masking **did** ship, via the dispatch. Base's behavior there is its own bug (it scales up on stale data), so
this is bug-masking-bug again; the difference is that this one is in the shipped base. For a saturation that
dies holding any positive `RC`, PR-2 converts *"scales up on stale data"* into *"sheds prefill to one
replica."* Machinery inherited; reachability in that reconcile not.

**Third, closing two of the coder's open items** — they have one answer. `scaleDownVariantSet:157-161` is the
cheapest-at-1 positional rule (`#1237`'s): last/cheapest variant, `current-n < 1`, no more-expensive variant
still holding replicas → `n = current - 1`. A single prefill variant floors at **exactly 1 from any height in
one pass**, which is the measured table. `reclaimRole` has no such rule — pure GPU delta, would give **0**.
**So measuring 1 rather than 0 is itself the path instrumentation:** the confirmed runs took
`scaleDownRoleIterated`; path B was not executed. Which leaves the pairing worth stating plainly — **the path
whose attribution is unconditionally "inherited" is the one nobody has run, and the executed path is the one
whose attribution is conditional.**

**What settles it, cheaply.** Run the coder's fixture at **base** in two variants: stale saturation
`RoleCapacities` all-zero, and with any one role positive. Prediction: base drains in the first and **does
not** in the second; HEAD drains in both.

Severity is unchanged and I join the planner in not wanting it softened — with the coder's sharpening that
*"~1 replica"* understates it: starting size does not matter, so an 8-replica prefill tier sheds 7 in one
reconcile.

Disposition stays yours and Dean's, and defer remains defensible on either attribution. My only ask is that
if the Type 1 says "inherited," it carries the condition rather than dropping it — an unconditional
"pre-existing, not ours" is the one form of the sentence the code does not support.
