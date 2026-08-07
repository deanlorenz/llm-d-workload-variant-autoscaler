from: review (PR-2 internal code reviewer)
to: planner
session: ta-anchor C11 ranking correction — two refinements + one unnamed hazard

## Why this exists

`plan__ta-anchor-c11-ranking-claim-correction.md` (Type-1 owner → you) is **correct on its
dispositive claim** — I verified it independently at branch tip `330fcd26`. This handoff does not
dispute it. It adds two refinements that change what the Type-3 edits should *say*, plus one hazard
neither that handoff nor plan §2f names, which I would otherwise only be able to raise after C11 has
already been written the wrong way.

Full detail is in my review doc, § *C11 pre-review — Finding 27*
(`planning/ta-anchor-dynamic-refresh-review.md`). Nothing here needs a production-code change beyond
what C11 already does.

## Verified (so you can treat it as settled)

`Cost = 0` for a never-measured variant. Three reads:
`analyzer_helpers.go:202` (anchor copies `Cost` from the (a) carrier) →
`saturation_v2/analyzer.go:353-360` (`variantCost` built from `inputMetrics` only) →
`:373` `cost := variantCost[vs.VariantName]`, a **bare map index** that misses and yields `0`.

Same defect shape as Finding 25 (`votesFromRoleSpare`'s bare `e.RoleSpare[role]`). Two findings on
this branch now trace to a missing map key silently becoming a meaningful zero. If you want a
one-line invariant somewhere in the Type 3, that is the one worth having.

## Refinement 1 — "both halves false" overstates it, and the overstatement is costly

The handoff says both halves of the Type 1's rationale are false from one root cause. The condition
for the sentinel to rank behind a measured variant is

```
Cost_s  >  Cost_m / PRC_m
```

and since measured `PRC_m ≫ 1`, the right-hand side is *tiny* — so **almost any positive `Cost_s`
satisfies it**. The Type 1's `PRC ≫ 1` intuition is sound. It fails at exactly one value,
`Cost_s = 0`, which happens to be the production value.

Why this matters for the wording you choose: it means the intended guarantee is **recoverable the
moment the saturation zero-replica cost bug is fixed, with no change to C11**. A §2f row reading
"this rationale was never true" tells a future reader to redesign something that is fine. A row
reading "this holds for any positive cost; the zero-replica cost bug makes it exactly 0" tells them
the truth and points at the fix. It is also the strongest argument for the handoff's optional dormant
spec — I would take that option.

## Refinement 2 — C11 *introduces* the inversion; it is not a pre-existing mis-statement

Today the claimed property **holds**, by a mechanism the Type 1 never cites:

- `cost_aware_optimizer.go:267-270` — `costEfficiency` returns `math.MaxFloat64` when `PRC <= 0`, so
  a never-measured variant sorts **strictly last** in its role;
- `cost_aware_optimizer.go:95-97` — `costGreedyRolePick` then skips it on `PRC <= 0` anyway.

The population is guarded **twice** today. C11's `PRC = 1` lifts the variant out of the `MaxFloat64`
branch into `0/1 = 0` — **strictly first** — and clears the skip. Both guards fall to the same
one-line change, leaving the one-replica cap as the **sole** remaining guard where today there are
three.

So the accurate framing is *"C11 inverts a property that currently holds"*, not *"the Type 1
mis-stated a property that never held."* Same edit location, materially different meaning: it makes
your `:2065-2080` tag/cap-coupling grep load-bearing for a reason stronger than the handoff gives,
and it tells the reviewer of C11 what the single point of failure is.

## The hazard nobody named — where the cap has to sit

`cost_aware_optimizer.go:99-106`: the pick returns `headroom` when `MaxReplicas` is set and non-zero,
and **`math.MaxInt`** otherwise (`:106`).

> If C11 puts the one-replica ceiling only inside the `MaxReplicas != nil` headroom branch, the
> `MaxReplicas == nil` path bypasses it entirely and the sentinel — now sorting **first** — absorbs
> the whole grant.

Worth one line in §2f or the C11 step: the cap belongs at the granting site (or unconditionally in
the pick), never in the headroom branch. This is the failure the handoff's suggested assertion-2
shape catches; I am naming the exact line it must catch.

## Golden risk: zero, plus a grep trap to note

No golden can move through the ranking path — **none has a never-measured input variant**; every
input `VariantCapacity` across all eight scenarios carries `PerReplicaCapacity: 10000` and
`ReplicaCount >= 2`.

Trap worth a parenthetical wherever the plan discusses C11's golden exposure: grepping `Replicas: 0`
in `optimizer_characterization_test.go` hits `:342` (`"expensive-p": {Replicas: 0, ...}`) in B2,
which reads like a zero-replica input. It is inside the **`want`** map — the expected target after
`expensive-p` is fully removed. B2's actual input for that variant is
`ReplicaCount: 2, PerReplicaCapacity: 10000` (`:317`).

## What I am not asking for

- No change to the `FZ-admission` decision. `PRC = 1` sentinel + one-replica target ceiling +
  `Reason` tag stand, and I concur with the handoff that no sentinel *value* fixes the ranking.
- No Type-1 edit from you. `:1530-1533` is frozen at `8c2a9b04` and is Dean's to touch.
- No `N5` fix, and no fix to the empty-`AcceleratorName` half — both correctly out of PR-2.

## Scope

I hold four checklist items for C11 beyond the handoff's two (cap-at-granting-site;
`Cost = 0` produced the production way rather than rigged; no assertion on which never-measured peer
wins, since they tie under unstable `sort.Slice` at `:260-262`; and the greedy path is not a
substitute because `fairShareRolePick` gates on an empty `AcceleratorName`). They are recorded in the
review doc and will be applied when C11 lands. Type-3 wording is yours.
