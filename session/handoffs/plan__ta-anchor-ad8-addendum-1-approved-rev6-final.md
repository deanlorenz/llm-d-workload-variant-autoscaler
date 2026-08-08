from: designer (owner of Type-1 combined-analyzer-optimizer-design.md + Addendum 1)
to: planner (owner of Type-3 ta-anchor-dynamic-refresh-plan.md)
cc: review (PR-2 internal reviewer — § checklist is addressed to you too)
session: ad8-addendum-1-approved-rev6-final

## Status: APPROVED by Dean, 2026-08-08. This supersedes every earlier `designer__`/`plan__` AD5/AD8 handoff.

`planning/combined-analyzer-optimizer-design-addendum-1.md` is at **Rev 6**, committed on `plans` as
**`423eb2a8`**, and Dean has approved it. It is now consumable. The parent Type 1
(`combined-analyzer-optimizer-design.md`, FINAL @ `8c2a9b04`) is untouched and stays frozen.

Every prior handoff in this thread is `.DONE` and several carry premises this revision withdraws. If you
are reconciling notes, **read the addendum, not the handoff trail.**

## 1. Dean's rulings — final

- **Guard (his own proposal, confirmed as scoped):** on a **disaggregated model with TA and no
  saturation**, do nothing. It *enforces* `AD2` rather than documenting it.
- **Option (a), the liveness-aware refusal — REJECTED** (*"PD not SAT — DONT"*). The rule stays keyed on
  the **enabled** set; no second refusal predicate is wanted.
- **Option (b), the per-role pricing repair — APPROVED.** Three sites: per-role sizing; `CapGPUs`/`Demand`
  in `rescaleInputsForGroup:540-546` (fixing only the role split leaves the model hard-capped at its
  understated demand); `cost_aware_optimizer.go:350-367` observability.
- **Option (c), interim documentation — additive, not alternative.** Highlights are in the addendum's
  § AD8 operator note.
- **`MinReplicas` is not a fourth option.** It works on the drain (`cost_aware_optimizer.go:142-161`,
  per-variant) but is unset by default, fails correlated with the defect, **does not reach regime (i) at
  all** (it can preserve a scale-up, never originate one — `greedy_saturation_algorithm.go:52-63` +
  `:80-83`), and is not free: any variant with `minReplicas > 0` makes `applyScaleToZeroEnforcement` skip
  the enforcer **model-wide** (`saturation/engine.go:1362`). It survives only as a documented severity
  floor for regime (ii), cost attached.

**Label reconciliation, so nobody talks past anyone.** Your `A68`/`B15` round numbers the mitigations
**(i)** = the `MinReplicas` floor and **(ii)** = the per-role pricing repair. The addendum's letters are
**(a)** = liveness-aware refusal (rejected), **(b)** = pricing repair (approved), **(c)** = documentation.
**Planner-(ii) ≡ addendum-(b).** Planner-(i) is the `MinReplicas` lever, which is not one of the
addendum's three. The verdicts agree in substance.

## 2. Rev 6 changes the severity, not the ruling — and it opens a placement question

Rev 6 withdraws this author's Rev 5 claim that the `[sat, TA]`-with-saturation-non-live cell is reachable
by a cold start or by a sustained metrics gap. **That cell is closed.** Recorded as § withdrawn item 8.

The two memories live in the same process and have opposite time constants:

| | warmed by | evicted after |
|---|---|---|
| saturation's capacity store | **scale-target objects, every cycle** — step 1 of `RunAnalysis` (`saturation/engine_v2.go:38-53`), before the ballot is built | **7 days** (`CapacityEvictionTimeout`) |
| TA's `variantStates.lastPerReplicaSupply` | **observed live replica metrics only** (`throughput/analyzer.go:427-440` `continue`s without a prior observation) | **1 hour** (`2 × DefaultObservationMaxAge`) |

So **TA warm ⟹ saturation warm.** Neither Rev 5 route reaches the cell: a cold start leaves both cold, and
a gap long enough to push saturation past the 90 s liveness window (`3 × interval`) has already emptied TA.
The residual is a fresh process in which **every** variant's scale-target fetch also fails
(`saturation/engine.go:1500-1507` `continue`s without writing a record) — and TA is cold there too, so it
cannot be the surviving voter.

**What this does and does not move.**

- **Does not touch `[TA]`-only** — that configuration needs no saturation death at all (saturation simply
  is not on the ballot). It is the reachable one, and it is exactly what Dean's guard makes hold.
- **Does not touch the two regimes measured at HEAD** — those fixtures build the ballot directly and
  bypass both memories.
- **Does not touch the arithmetic**, and **does not touch Dean's decision** to repair the pricing.
- **Does drop severity**, because Dean set severity on Rev 5's premise.
- **Does open placement.** A defect confined to one configuration, in which the guard makes the model hold
  rather than act, is a weaker PR-2 candidate than Rev 5 implied. **Placement of the repair in PR-2 is now
  a live question for Dean — do not schedule it into PR-2 on the strength of the old severity, and do not
  retire it either.** Ask him.

## 3. Scope shape of the defect — two rows, not one

Your scoping ask is accepted. `AD8` is **two regimes from one cause**, and they must reach the Type-3 or
the backlog as **separate items**, because a fix verified on one says nothing about the other:

- **Regime (i), the freeze** — decode `RC > 0` ⇒ scale-up arm ⇒ prefill **freezes at its current count,
  including 0**. Has **no floor of any kind**; `MinReplicas` cannot reach it.
- **Regime (ii), the drain** — decode `RC == 0` ⇒ scale-down arm ⇒ prefill **drains to 1**.

Dispatch is a global OR (`analyzer_helpers.go:709-718`) with mutually exclusive arms
(`cost_aware_optimizer.go:62-67`), which is why one cause yields two outcomes.

## 4. Sequencing constraint — carries a coverage precondition

Verified with the coder and reviewer, and it **governs regime (ii) only**: everything it protects lives
inside `scaleDownVariantSet`, which regime (i) never enters.

> If #1237's positional rule is ever tidied, **floor every variant in the role first.** Tidy-first
> re-opens this at every height on both scale-down paths (measured — prefill → 0).

## 5. Premises to stop carrying

- **§ withdrawn item 6** — the drain as *"newly unmasked by `VG-up`"*. Wrong: base's binder gate was already
  `Live`-gated and base's `roleDemandGPUs` read demand off the anchor (`075a208e:rescale.go:545`), so base
  already bound TA and already read prefill `TotalDemand = 0`. Confirmed by execution at base, and the
  reviewer has conceded it (Finding 67). **This is the specific stale premise inside the consumed
  `plan__ta-anchor-ta-role-completeness-addendum.md`** — that file is `.DONE` and is not being edited, so the
  correction lands here instead. Route (A) *is* HEAD-reachable when the pruned entry carries a positive `RC`
  (arm-2 run), which is a narrower claim than the one withdrawn.
- **§ withdrawn item 7** — "the cell is reachable by the most ordinary path there is (a cold start)". Wrong.
- **§ withdrawn item 8** — "reachable by cold start or sustained metrics gap". Wrong; see §2 above.
- **Review finding V6's (b)-fallback domain** — inverted; superseded by `N1`.
- The seam the reviewer named (informativeness reads per-variant `Reason`, while the RC reaching the
  optimizer comes from `RoleCapacities`; `applyUniversalThreshold`, `saturation/engine_v2.go:476-513`,
  never mentions `VariantCapacities`) **is real and survives Rev 6 — but it is latent, not live.** Aligning
  the two predicates is a **Type-1 design question**, not PR-2 work, and **not** a revival of rejected
  option (a) (different site: the liveness computation, not a second refusal predicate in the optimizer).
  Recorded for a later round; no ask attached.

## 6. For the reviewer as well

The addendum's **§ verification checklist** is written for planner and reviewer jointly, and its
`ok == false` row now carries an explicit warning: verify that `ok == false` is reachable before relying on
it, **because Rev 6 concludes it is not.** The row also states the falsification test — *verify by
counter-example, not by re-deriving*: find any single-fault story in which saturation stamps `no-data` on
every variant while TA emits a `T-sfz` capacity.

## Asks

1. Put **regime (i)** and **regime (ii)** into the Type-3 or the backlog as **two** items, not one.
2. Take the **placement question in §2** to Dean before scheduling the pricing repair into PR-2.
3. Carry §4's precondition wherever the #1237 tidy-up is tracked.
4. Drop the §5 premises from any plan text that inherited them.
