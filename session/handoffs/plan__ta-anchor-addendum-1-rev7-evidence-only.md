from: designer (owner of Type-1 combined-analyzer-optimizer-design.md + Addendum 1)
to: planner (the PR-2 Type-3 owner — `ta-anchor-dynamic-refresh-plan.md`)
session: type1-addendum-1-rev7-evidence-only
cc: review (Finding 75's author), coder on `ta-anchor-dynamic-refresh` — both getting refs-only doorbells

## Read this line first, then decide whether to read the rest

**Addendum 1 is now Rev 7 (`43f20c65`). Nothing you were told to do has changed.** No ruling moved, no
severity moved, no disposition moved, and the one open question is still the same one: **`AD8` option
(b)'s placement in PR-2 vs a follow-up, which is Dean's.** If you are mid-edit on the Type 3 against
Rev 6, keep going — Rev 7 does not invalidate a single line you would have written.

What Rev 7 does is repair the *evidence* under a conclusion that stands. If you never cite the
mechanism, you can stop here.

## What changed, and why it needed a revision at all

Rev 6 closed the `[sat, TA]`-with-saturation-non-live cell, and Dean approved that revision. The
reviewer then verified the closure independently and **confirmed it** — by counter-example search rather
than by re-deriving: four candidate single-fault stories, all four fail. So the cell is closed, twice
over, on independent grounds.

But Rev 6's *argument* was wrong. It closed the cell via a **retention asymmetry** — saturation's
capacity records kept 7 days, TA's persisted supply expiring in 1 hour, therefore `TA warm ⟹ sat warm`.
Three of the mechanisms that argument cites do not hold, and I re-verified each one against PR-2 HEAD
`a9afb740` before accepting the finding:

- **(a) The retention numbers describe dead code.** `EvictStale` (`capacity_store.go:137`) and
  `EvictStaleHistory` (`saturation_v2/analyzer.go:50`) have **zero callers tree-wide, tests included**;
  `CapacityEvictionTimeout` and `HistoryEvictionTimeout` appear only at their own declarations. Records
  live for the process lifetime. The conclusion is therefore *stronger* than Rev 6 claimed — and the
  mechanism Rev 6 named for it never runs, so the "7 days" and the "168×" were arithmetic over two
  constants nothing reads.
- **(b) The TA side conflated two fields.** `lastObservedAt` (`throughput/analyzer.go:99`) is assigned
  inside the `groupByVariant` loop, *before* the `SanityIssueNoReplicas` `continue` (`:101-108`) and
  before `!report.OK()` (`:109`) — so the 1-hour eviction clock keys on a variant merely **appearing**
  in the metrics slice, not on its rows being usable. `lastPerReplicaSupply`, the field the cell
  actually depends on, is the one that needs usable rows. Two fields, two conditions.
- **(c) The `NoData` stamp is governed by row count.** `saturation_v2/analyzer.go:390` branches on
  `len(replicas) > 0` — a variant with any row gets a non-`NoData` reason whatever its arithmetic
  yields.

**The replacement needs no time constant at all.** The only thing that can leave TA holding a positive
`lastPerReplicaSupply` for a variant is having processed a usable replica-metric row for it — and
processing that same row writes saturation a `learnedFromLive` capacity record keyed on the same
`rm.VariantName`, in the same key space, on the same cycle (`saturation_v2/analyzer.go:198-207`), which
`capacity_store.go:98-101` then protects from being overwritten by a weaker source. Saturation is warm
over a **strictly broader** set, because the store is *also* pre-populated from scale-target objects on
step 1 of every cycle (`saturation/engine_v2.go:38-53`), reaching variants with no metric rows at all.
Containment, not a race — instantaneous, per variant.

## Two things this retires, one thing it adds

**Retired — Rev 6's residual.** Rev 6 said the remaining way in was "a fresh process where every
variant's scale-target fetch fails." Two closures Rev 6 did not cite kill it: a failed
`FetchScaleTarget` `continue`s at `saturation/engine.go:1506` *before* `scaleTargets[key] = …` (`:1520`)
and `variantAutoscalings[…] = va` (`:1523`), so the model reaches `RunAnalysis` with empty maps; and
`:1540-1545` returns early on `len(replicaMetrics) == 0`, skipping the model before `BuildVariantStates`
(`:1547`) and before any analyzer runs. That state is **no model on the ballot**, not an all-`NoData`
model — there is nothing for TA to be the sole voter on.

**Retired — the checklist's counter-example ask.** Rev 6's `AD8` checklist row asked whoever ran it to
find a single-fault story reaching the cell. **Answered; do not spend time on it.** Model-wide metric
loss and all-scale-target-fetch failure both hit the closures above (and take TA blind too); unparseable
engine args have no such path (`resolveEffectiveMaxBatchedTokens` precedes every return of both parsers);
and a collector-vs-`BuildVariantStates` name mismatch fails because TA's *emission* also keys off
`input.VariantStates` (`throughput/analyzer.go:426`) and misses its own memory (`:430-431`). Three of the
four fail for the same structural reason — the faults that starve saturation starve TA through the same
door.

**Added — one narrower residual, recorded as a band, not a closure.** Given (c), entry requires: on the
last cycle with rows, `min(k1, k2) ≤ 0` (`saturation_v2/analyzer.go:185-188`) for **every** variant of
the model, while TA computed a positive `perReplicaSupply` from those same rows, **and**
`lookupCompatibleCapacity` missed for every variant too. Not claimed reachable, not claimed unreachable.
**It is a `k1`/`k2` arithmetic question, not a liveness question** — so if anyone ever probes it, it
needs a k1/k2 fixture; a stale-timestamp or metrics-gap fixture lands somewhere else entirely. **No
ruling, severity, or disposition in the addendum depends on which way it goes**, and the reachable
configuration for `AD8` stays `[TA]`-only either way.

## What you should actually do with this

1. **Nothing, if the Type 3 does not repeat the mechanism.** Check with
   `grep -n "7 day\|1 hour\|168\|CapacityEvictionTimeout" planning/ta-anchor-dynamic-refresh-plan.md`.
   If that is empty, Rev 7 is a no-op for you.
2. **If it does repeat it** — replace with the same-event sentence above, or just cite
   `[§ withdrawn](combined-analyzer-optimizer-design-addendum-1.md#withdrawn)` item 9 and let the
   addendum carry it. Per Dean's *"we do not correct until coder lands"*, this is not urgent and is not
   a reason to touch the plan mid-flight; fold it when you are next in the file for another reason.
3. **Do not re-open severity or placement.** They were set on Rev 6's *conclusion*, which is intact.

## One backlog item, explicitly NOT a PR-2 ask

Correction (a) surfaced dead code: the unreferenced `EvictStale` / `EvictStaleHistory` pair, two
constants read nowhere but their own declarations, and `capacity_store.go:135`'s comment citing an
`EvictionTimeout = 24h` that does not exist (the real 24 h constant is the k2 history's). **Backlog, at
Dean's direction — do not schedule it into PR-2.** Dead code that never ran cannot have been doing
anything, so there is no behavior to fix and adding it to PR-2 would be scope creep. Recorded here only
so it is not re-discovered as a bug later.

## Where it lives

- `planning/combined-analyzer-optimizer-design-addendum-1.md` — **Rev 7**, commit **`43f20c65`** on
  `plans`. New `§ withdrawn` **item 9** carries the whole correction; `§ residual` carries the new band;
  a header note tells Rev 6 consumers that nothing they were told to do has changed.
- Parent Type 1 (`combined-analyzer-optimizer-design.md`, FINAL @ `8c2a9b04`) **untouched**, as always.
- Inbound `designer__rev6-closure-verified-with-three-evidence-corrections.md` is `.DONE`.
- Cold-resume record: `session/status/designer-type1-addendum.md`.

## Still open — and it is still the same single item

**`AD8` option (b)'s placement: PR-2 or a follow-up. Dean's call.** Rev 7 gives no new argument either
way; it neither strengthens nor weakens the case, because it changed no severity. The reason to mention
it is only that this is the third handoff in a row to end on it, and it is still the thing the plan
freeze and the coder's finish-line both wait on.
