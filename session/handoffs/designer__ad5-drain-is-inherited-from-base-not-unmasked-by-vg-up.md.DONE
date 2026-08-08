# designer__ad5-drain-is-inherited-from-base-not-unmasked-by-vg-up

from: planner (ta-anchor-dynamic-refresh Type-3 owner)
to:   designer (Type-1 owner — `combined-analyzer-optimizer-design.md` and its addenda)
cc:   review (PR-2 internal code reviewer) — this narrows §2 of its
      `designer__ad3-substitute-rationale-scope-and-ad5-is-not-a-freeze.md`
session: AD5 attribution — base `075a208e` vs PR-2 HEAD
date: 2026-08-08

Short and single-purpose. The reviewer's two corrections to my earlier handoff
(`designer__ad3-rationale-false-ad5-mechanism-and-n7-inverted.md`, now `.WIP` with you) are
**accepted in full** — I re-verified both on the decisive links and have corrected my own Type-3
manifest rows accordingly. You do not need me to re-argue either:

- **§1 narrowing — accepted.** TA prices live prefill variants (`analyzer.go:364` gates only the
  decode ITL/OL averaging; `perReplicaSupply` is not role-gated), so the unpriced-skip is not what
  protects a running prefill role. My "the only thing declining the prefill reclaim" was a
  blanket claim on a from-zero-only property. The substitute rationale for `AD3` stands **inside
  `AD3`'s own domain** and should carry the live/zero-replica split, exactly as the reviewer put it.
- **§2 inversion — accepted.** `scaleDownVariantSet` is parameterised by its caller's callback;
  `scaleDownRoleIterated` does consult both gates and they *pass rather than protect*, while
  `reclaimRole` consults neither. My statement was scoped to the wrong function.

**The one thing I am writing to correct is an attribution claim in the reviewer's §2**, because it
is the half that decides whether this is PR-2's to fix, and you are about to fold it into the Type 1.

## The claim

Reviewer's §2, second bullet: `reclaimRole`'s path has *"narrower reachability, but this half **is**
newly unmasked by `VG-up`."* (Its first bullet correctly marks the `scaleDownRoleIterated` path as
inherited from base.)

## Why it does not hold for the fixture as scoped

Three facts at base `075a208e`, each read-only, each independently checkable:

1. **`distributeDemandByRole`'s prefill exclusion is byte-identical at base.** Same
   `if role != domain.RolePrefill` guard, same `share = demand / len(roles)` over a map prefill was
   never added to. Prefill role demand is zero by construction on both sides.
2. **Base `roleDemandGPUs` had no ballot parameter at all** — `roleDemandGPUs(anchor, stateMap,
   accType, role)` at `rescale.go:545`, reading demand off the **anchor**. The `s` argument is bug
   #3's addition (`07b8fdb7` + `3c9d45bb`).
3. **Base `bindingAnchor`'s binder gate is already `Enabled && Live && ResultIsInformative`.**

Compose against the reviewer's own fixture (sat `Enabled: true, Live: false`, TA live and binding,
prefill ≥ 2 replicas, no `MinReplicas`): base already fell through the saturation branch and
**already bound TA**; base already read prefill `TotalDemand = 0` off that anchor; base's
`distributeGPUsByWeight` already gave prefill weight 0, collapsing its target to
`floorByRole[prefill]` = 0; `rt < rc` already fired; and base `rescale.go:367` already called
`reclaimRole` for the role's entire allocation. **The drain reproduces at base unchanged.**

`VG-up` reaches `reclaimRole` only as (a) `sortVariantsForScaleDown` **ordering** — and base
`rescale.go:367` already passed `votingResults(req.AnalyzerResults)` there — and (b) bug #3's new
`s` argument to `roleDemandGPUs`. Neither can push prefill's demand below the 0 it already held.

## The one counterfactual where `VG-up` does matter, stated so I am not shading this

Compare **HEAD-with-`VG-up`** against **a hypothetical bug-#3-without-`VG-up`**: there, a stale but
`Enabled` saturation entry would still be in `s`, and if its prefill `TotalDemand` were non-zero it
would give prefill positive weight and avert the drain. So `VG-up` does remove a protection — but
one that (i) never existed in any shipped state, and (ii) is stale-data-derived, i.e. a bug that
happened to mask another bug. The comparison that settles regression-vs-inherited is base-vs-HEAD,
and base drains.

## What follows, for your disposition (not a request for a particular amendment)

`AD5` is a **pre-existing defect of the opt-in TA path on P/D models under saturation outage**, not
a PR-2 regression — both of its paths, not just `scaleDownRoleIterated`'s. Severity is unchanged
from the reviewer's account and I do not want it softened: prefill is actively shed to its floor
while decode scales normally, with the prefill series reading 0.

If that attribution holds for you, `AD5`'s wording is a known limitation of `[sat,TA]` plus a filed
follow-up, rather than a PR-2 scope item. My B15 recommendation is still *defer*, but its basis has
moved from "the window is narrow" to "this is not PR-2's bug", and I have made the deferral
conditional on the follow-up actually being **recorded** — inherited is only an acceptable answer
if the defect outlives this round in writing. Filing is Dean's call, not mine.

Also carrying forward, already agreed with the reviewer and recorded on my side: the invisibility
half is a **second site** (`cost_aware_optimizer.go:350-367` still reads `anchor.RoleCapacities[role]`
for `decision.RequiredCapacity`), so any `AD5` fix has two sites and only one is on the sizing path.

## Evidence status

**Source reading, not execution.** I do not build or test in the coder's worktree and did not. Every
link above is a `git show` / `git grep` at `a9afb740` and `075a208e`. The fixture the reviewer
specifies is the right instrument and should be written when the fix is scoped; if it is written
today it should be expected red at **base** too, which is the assertion this handoff really makes.
