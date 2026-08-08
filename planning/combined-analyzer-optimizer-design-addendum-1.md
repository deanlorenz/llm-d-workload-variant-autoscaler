# Addendum 1 — analyzer role completeness and partial scale-from-zero — Type 1 Design

> **Reading protocol:** Read the TOC first. Fetch only the sections you need via
> `Read <file> offset:<start> limit:<end-start+1>`. Never read the whole file up front.

**Type:** 1 (design) · **addendum — additive only** · **Status: FINAL for the analysis; two
dispositions are open and named** ([§ disposition](#disposition)).

**Parent:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) —
**Status: FINAL, frozen 2026-08-07 @ `8c2a9b04`**. **The parent is deliberately unedited.** Dean,
2026-08-08: *"no editing"* — so this addendum does not amend the parent's body, its TOC, its
[§ open](combined-analyzer-optimizer-design.md#open) queue, or its finding inventory. Where the two
overlap, **this addendum is later and governs**; everything the parent settles and this addendum does
not mention stands unchanged.

⚠️ **Discoverability is the cost of not editing the parent.** The parent declares itself
AUTHORITATIVE and says *"anything not on that queue is settled"* — a reader who follows only the
parent will not learn this file exists. The two documents that could carry a pointer are the Type-3
plan and `session/CURRENT.md`, and **neither is this role's write scope**; both are requested via
`plan__ta-anchor-ta-role-completeness-addendum.md`. Until one of them links here, this addendum is
reachable only by name.

**Code currency.** Every claim below re-verified by direct read against worktree `Main` @ `a6b39809`
— the post-merge baseline (contains PR-1 #1516 squash `57f3fe64` and the #1512 toolchain bump) — on
**2026-08-08**. **Function, field and struct names are authoritative; every `file.go:N` line number
is as-of-authoring and drifts.** No claim here rests on the coder's in-flight tree.

**Explicitly out of scope — held for a separate discussion.** The fair-share `ceil` → `floor`
conversion (parent [§ bugs](combined-analyzer-optimizer-design.md#bugs) #5 / `fairShareCap` / the
GPU-space unit table) is **not addressed here**. Dean, 2026-08-08: *"the ceil/floor we discuss
later."* Nothing in this addendum depends on that outcome, and nothing here should be read as
settling it.

**Provenance.** This addendum records the outcome of a design discussion held 2026-08-07/08 in which
Dean issued three rulings and rejected two of this author's proposals. His rulings are quoted where
they are load-bearing. Two of the author's own framings were wrong and were withdrawn; they are
recorded in [§ withdrawn](#withdrawn) rather than deleted, because the corrected version is only
legible against them.

---

## TOC {#toc}

- [Why this addendum exists {#why}](#why-this-addendum-exists-why) L56:75
- [AD1 — the ThroughputAnalyzer is not a P/D-complete analyzer {#ad1}](#ad1--the-throughputanalyzer-is-not-a-pd-complete-analyzer-ad1) L76:127
- [AD2 — ruling: `[TA]`-only is unsupported on P/D models; both analyzers is the default {#ad2}](#ad2--ruling-ta-only-is-unsupported-on-pd-models-both-analyzers-is-the-default-ad2) L128:150
- [AD3 — the from-zero PRC work is scoped to `decode` and `both` roles only {#ad3}](#ad3--the-from-zero-prc-work-is-scoped-to-decode-and-both-roles-only-ad3) L151:173
- [AD4 — verified: TA does not veto saturation, in either direction {#ad4}](#ad4--verified-ta-does-not-veto-saturation-in-either-direction-ad4) L174:202
- [AD5 — the one real override is the binding path, not voting — OPEN {#ad5}](#ad5--the-one-real-override-is-the-binding-path-not-voting--open-ad5) L203:237
- [AD6 — rejected: TA cross-variant sibling pricing. Retained: the retention exception {#ad6}](#ad6--rejected-ta-cross-variant-sibling-pricing-retained-the-retention-exception-ad6) L238:281
- [AD7 — `N5` (saturation `Cost = 0` at zero replicas) is to be fixed {#ad7}](#ad7--n5-saturation-cost--0-at-zero-replicas-is-to-be-fixed-ad7) L282:301
- [Residual band after the rulings {#residual}](#residual-band-after-the-rulings-residual) L302:326
- [Withdrawn framings {#withdrawn}](#withdrawn-framings-withdrawn) L327:351
- [Disposition summary {#disposition}](#disposition-summary-disposition) L352:370

## Why this addendum exists {#why}

**Partial scale-from-zero is a supported use case, not an edge case.** Dean, 2026-08-07: *"two
variants, min=1, min is on the model. one variant goes to 0. This is a real use case by design."*
The model stays warm — the model-level minimum is satisfied by a **sibling** variant — while one
variant sits at zero replicas. That variant has no pods, therefore no live metrics, therefore no
measured per-replica capacity.

The parent doc's `FZ-admission` item ([§ findings](combined-analyzer-optimizer-design.md#findings))
answers the *whole-model* cold-start question: a never-seen variant is admitted only when saturation
binds, via a `Reason`-tagged `PRC = 1` sentinel capped at a one-replica target. That decision stands.
It does **not** answer the partial case, because in the partial case the question is not "may this
variant be admitted at all" but "what does each analyzer know about a variant whose siblings are hot".

Working that question through the three supported configs
([§ configs](combined-analyzer-optimizer-design.md#configs)) produced one structural finding that
changes the scope of the whole problem, and it is `AD1`.

[↑ TOC](#toc)

## AD1 — the ThroughputAnalyzer is not a P/D-complete analyzer {#ad1}

**Claim.** TA's role demand for the **prefill** role is structurally zero — always, on every model,
regardless of traffic, regardless of whether any variant is cold. This is by construction, not a bug
in a fallback path.

**Evidence, in order.**

1. **TA's demand is decode-rate-denominated and model-level.**
   `analyzer.go:428-465` computes `arrivalDecodeDemand = input.ArrivalRate * avgOL`, sets
   `totalDemand = arrivalDecodeDemand`, then adds `queueDemand` from
   `estimateQueueDemand(input.SchedulerQueue, avgDecodeITLSat, DefaultQueueDrainFactor)`. Its own
   comment states the model-level arrival term *replaced* the per-variant summation, and that the
   per-variant `VariantCapacity.TotalDemand` is retained "for per-variant introspection".
2. **The split to roles excludes prefill by construction.**
   `distributeDemandByRole` (`analyzer.go:897`) builds its role set with `if role !=
   domain.RolePrefill`, and its doc comment at `:895` says so outright: *"prefill roles are
   excluded."* Both demand terms — arrival and queue — go through this one function.
3. **The exclusion is the only one of its kind in the file.** A grep for prefill handling in
   `analyzer.go` returns exactly two sites: `:338` (avgOL/ITL tracking) and `:897`
   (`distributeDemandByRole`). The per-variant capacity loop does **not** skip prefill — so TA does
   emit prefill `VariantCapacity` entries carrying a real, positive `PerReplicaCapacity`. TA is not
   silent about prefill; it prices prefill and then assigns it no demand.
4. **Zero demand becomes zero required capacity.** The threshold post-step
   `engine_v2.go:502-516` computes `RequiredCapacity = TotalDemand/scaleUp − TotalAnticipatedSupply`
   (floored at 0) and `SpareCapacity = TotalSupply − TotalDemand/scaleDown` (floored at 0), per role.
   With `TotalDemand == 0`: **`RequiredCapacity(prefill) = 0`** and **`SpareCapacity(prefill) =
   TotalSupply`** — TA reports the entire prefill fleet as spare.
5. **Zero required capacity becomes zero replicas at the combine.**
   `initRoleState` (`analyzer_helpers.go:268`) seeds `pickerState[i][role] = rc.RequiredCapacity`;
   `roleBottleneckReplicas` (`:323`) then divides by the variant's PRC. `ceil(0 / prc) = 0` for any
   positive PRC.

**Consequences — two, both structural.**

- **TA can never drive prefill scale-up.** Not "usually doesn't" — cannot, at any arrival rate.
- **TA always reports the whole prefill supply as spare.** Harmless only because it cannot act
  alone; see [`AD4`](#ad4) for why, and [`AD5`](#ad5) for the one path where it is not harmless.

**Contract statement.** An analyzer is **role-complete** for a model iff it produces a demand model
for every role that model's variants declare. TA is role-complete for non-disaggregated models and
for the `decode`/`both` roles; **TA is not role-complete for a P/D model.** Saturation is: it
attributes queue demand to prefill explicitly — `estimateSchedulerQueueDemand`
(`saturation_v2/analyzer.go:750-793`) switches on role and assigns `inputTokens` to prefill,
`inputTokens + outputTokens` to decode. The two analyzers are not merely differently calibrated here;
one models the role and the other declines to.

This is unfixable within TA as it exists. It is fixed by adding a TA-prefill analyzer — Dean,
2026-08-07: *"This will not be solved until we have TA-prefill added in."*

[↑ TOC](#toc)

## AD2 — ruling: `[TA]`-only is unsupported on P/D models; both analyzers is the default {#ad2}

**Decided (Dean, 2026-08-07), verbatim:** *"you should not use TA only on P/D. The default should be
to use both. This can be documented -- as long as we only have TAdec we cannot use it as the ONLY
analyzer."*

This promotes a constraint the parent's [§ configs](combined-analyzer-optimizer-design.md#configs)
did not state: `[TA]`-only remains a supported config **for non-disaggregated models only**. On a
P/D model it is unsupported, because by [`AD1`](#ad1) it leaves an entire role with no demand model.

**Documentation, not enforcement — and the reason is structural.** A startup-time validation is not
available: analyzer enablement comes from controller config, while **roles arrive at runtime from VA
specs** (`VariantReplicaState.Role`, `saturation_analyzer.go:403`, populated per reconcile). At the
moment the analyzer set is fixed, no role is known. Any real check would therefore be a *per-model
runtime warning* raised the first time a prefill-roled variant is observed under a TA-only
configuration — a different piece of work, not a config schema addition.

**Therefore the constraint ships unenforced.** That is an accepted cost, recorded here so nobody
later reads the absence of a check as an oversight. If it is ever to be enforced, the per-model
runtime warning above is the shape.

[↑ TOC](#toc)

## AD3 — the from-zero PRC work is scoped to `decode` and `both` roles only {#ad3}

**Follows from [`AD1`](#ad1) with no further argument.** Every candidate mechanism for pricing a
zero-replica variant — a retained last-known PRC, an inherited sibling price, a demand-model ratio,
or the `FZ-admission` `PRC = 1` sentinel — is a **denominator** intervention. The prefill blocker is
a **zero numerator**. `ceil(0 / anything) = 0`.

So for a prefill variant at zero replicas, **all four mechanisms are exactly equally inert**, and no
future refinement of any of them changes that. Pricing work that targets prefill from-zero is wasted
by construction.

**And abstaining is the right answer, not a limitation.** Dean, 2026-08-07: *"Not scaling from zero
is the correct action."* A cold prefill variant on a P/D model under real traffic *will* queue, sat
*will* attribute `inputTokens` to prefill, and sat is mandatory on P/D by [`AD2`](#ad2) — so the case
is covered by the analyzer that models the role, on the cycle where the demand becomes real.

**Scope statement for implementers:** any from-zero pricing mechanism is specified over variants whose
`Role` is `decode` or `both` (including the empty-string default, which `distributeDemandByRole`
normalizes to `both`). Prefill variants are out of its domain — not by a guard that must be written,
but because the mechanism cannot reach them.

[↑ TOC](#toc)

## AD4 — verified: TA does not veto saturation, in either direction {#ad4}

Dean, 2026-08-07: *"We should check TA does not veto sat in this p/d scenario."* Checked against both
combine operators. **Answer: no veto, and no ability to force a move either.**

**Scale-up is a cross-analyzer MAX.** `roleBottleneckReplicas` (`analyzer_helpers.go:323`) takes the
maximum over analyzers. TA contributes `ceil(0/prc) = 0` for prefill — with a *valid positive* PRC,
so it is not skipped as unpriced, it genuinely votes zero. `MAX(sat_n, 0) = sat_n`. TA's structural
zero is the **identity element** of this operator: it cannot lower sat's number.

**Scale-down requires unanimity among live analyzers.** `needsScaleDownForRole`
(`analyzer_helpers.go:442`) returns `false` the moment any live analyzer reports
`RoleSpare[role] <= 0`; so sat can veto TA, and TA's "the whole prefill fleet is spare" cannot
override sat. When sat *does* agree, `safeRemovalReplicasForRole` (`:387`) takes the **min** over live
analyzers of `floor(RoleSpare / prc)` — so the smaller, sat-derived count wins. TA cannot enlarge a
scale-down.

**Incidental confirmation — `N7` fails safe on scale-down.** A role key present in one live analyzer's
`RoleCapacities` and absent from another's reads as zero spare in `needsScaleDownForRole`, hits the
`<= 0` branch, and vetoes. Divergent role key-sets therefore cause a role to *never scale down*, never
a spurious one. The parent's `N7` can be dispositioned as fail-safe in this direction.

**Also checked and cleared:** the `anchor.RoleCapacities[role]` read in
`cost_aware_optimizer.go:290-320` populates `decision.RequiredCapacity` / `SpareCapacity` for the
`wva_required_capacity` / `wva_spare_capacity` gauges only. It is observability, not a control path
— though see [`AD5`](#ad5) for what it means for the prefill gauge.

[↑ TOC](#toc)

## AD5 — the one real override is the binding path, not voting — OPEN {#ad5}

**The combine is safe ([`AD4`](#ad4)); the anchor is not.** The anchor takes `RoleCapacities`
**wholesale from the binding analyzer** (parent
[§ anchor](combined-analyzer-optimizer-design.md#anchor)). So when TA binds — sat `Enabled` but not
live/informative, on a model where TA is the sole live binder — the anchor's
`RoleCapacities[prefill].TotalDemand` is `0`, and:

- `roleDemandGPUs` (`rescale.go:554-570`) reads `demand = rc.TotalDemand` for the role and returns
  `ceil(0 / best) = 0` GPUs → **the prefill role is granted no fair-share budget**;
- the prefill `wva_required_capacity` gauge reads `0` — so the symptom is invisible in exactly the
  series an operator would check.

**PR-2 interaction — a mask is about to be removed.** Today `votingResults` prunes the ballot on
`Enabled` only, so a stale-but-enabled sat entry still reaches the scale-up MAX and *accidentally*
supplies a nonzero prefill `RequiredCapacity` during a sat outage. PR-2's `VG-up` hardening
(`Enabled && Live`) removes that entry. After PR-2, a `[sat,TA]` P/D model whose sat has gone stale
runs prefill scale-up on TA's structural zero alone, while decode continues to scale normally — a
model that quietly stops scaling half of itself.

Neither behaviour is correct: relying on a stale value is wrong, and sizing a role from an analyzer
that has no model of it is also wrong.

**Design position (this author's recommendation, not a decision):** when the binding analyzer is not
role-complete for a role, that role should be **held** — the same per-model hold the parent already
specifies for `bindingAnchor == nil` — rather than sized from a demand it does not model. A hold is
already an expressible outcome, so this is a predicate, not a new mechanism.

> **OPEN — needs a scope decision.** Whether this lands in PR-2 or is recorded as a known limitation
> of `[sat,TA]` under sat outage is the **planner's** call on scope and Dean's on priority. Both are
> defensible: the window is narrow (requires a sat outage on a P/D model), and PR-2 is already large.
> What is *not* defensible is shipping `VG-up` with nobody having noticed it unmasks this.

[↑ TOC](#toc)

## AD6 — rejected: TA cross-variant sibling pricing. Retained: the retention exception {#ad6}

**Rejected — TA inheriting a price from a compatible sibling.** Dean, 2026-08-07: *"Good idea, but
skip unless really cheap."* Verified: it is not cheap.

Saturation can do this because it has a three-tier ladder (live median → its own stored
`CapacityRecord`, which is spec-parsed and needs no pods → a compatible sibling matched on
accelerator **and** `GPUsPerReplica`). TA has one tier: its own retained `lastPerReplicaSupply`. To
add sat's third tier to TA needs (a) an accelerator identity TA does not have, (b) a compatibility
predicate, and (c) a provenance decision about how an inherited price is labelled. Without (a) the
predicate is not merely incomplete — it would happily inherit an H100 price onto an A100 variant,
which is worse than abstaining.

**Retained and still available — Dean's own retention exception.** Carrying
`lastPerReplicaSupply` (plus `role` and `lastFittedB`) across TA's idle expiry is cheap and is
*his* proposal, not a substitute for it. The eviction at `throughput/analyzer.go:158-163` drops the
whole `variantState` after `2*DefaultObservationMaxAge`; its comment gives two motives — bounding
memory, and avoiding false shape-change signals on recreate — and **neither motive covers the
price**. The shape hazard lives in `observationWindow`/`shapeTracker`, and `lastFittedB` already has
an explicit "a shape change must not clear this" carve-out; idle expiry deserves the same carve-out.
Its limit is honest: it covers a **long-idle** variant, never a genuinely new one.
Residual hazard: the state key is `variantKey(ns, modelID, variantName)`, so a variant recreated on
different hardware inherits a stale price — the same accelerator-identity gap as above.

**One plumbing change would serve three items.** `VariantReplicaState`
(`saturation_analyzer.go:386-409`) is spec/deployment-derived — it exists for a zero-replica variant
and already carries `GPUsPerReplica`, `Role`, `MinReplicas`, `MaxReplicas` — but it has **no
`AcceleratorName` and no `Cost`**. Both fields exist on `ReplicaMetrics` (`:58-59`), a *live-pod*
type, which is precisely why a cold variant cannot see them. Adding those two spec-sourced fields to
`VariantReplicaState` would supply the accelerator identity the sibling lookup needs, the accelerator
identity the retention hazard needs, and the cost [`AD7`](#ad7) needs. **This does not reverse the
rejection** — the sibling lookup still needs the predicate and the provenance decision on top — but
it means the three items share one prerequisite and should be scoped together if any of them is
scoped at all.

**Also rejected — the demand-model ratio** (`TA_PRC = sat_PRC × TA_demand / sat_demand`). Dead twice
per role: the prefill numerator is zero ([`AD1`](#ad1)), and the two analyzers' role demands are not
proportional — TA even-splits a model total across non-prefill roles (so the denominator changes when
a `both` variant appears) while sat sums over that role's live variants plus a role-specific queue
split. There is no stable per-role exchange rate to be had. The model-level form survives
dimensionally but is unnecessary once [`AD2`](#ad2) makes sat mandatory wherever roles exist.

[↑ TOC](#toc)

## AD7 — `N5` (saturation `Cost = 0` at zero replicas) is to be fixed {#ad7}

**Decided (Dean, 2026-08-07):** *"2.cost: should be fixed."*

The parent records `N5` as a known limitation reaching all three configs: sat's entry for a
zero-replica variant carries `Cost = 0`, so `costEfficiency = 0` and the variant sorts **cheapest**
— a variant with no measured capacity outranks every real one.

**Root cause, stated precisely.** Cost is a **spec** property (`va.Spec.VariantCost` is the existing
precedent) but the pipeline reads it from a **live-pod-derived** type: `ReplicaMetrics.Cost`
(`saturation_analyzer.go:59`). A variant with zero replicas has no `ReplicaMetrics` entry, so it has
no cost, so it is free. The bug is the sourcing, not the arithmetic.

**Shape of the fix:** source cost from the spec for every variant that has one, independent of pod
existence — which is the `Cost` half of the `VariantReplicaState` plumbing in [`AD6`](#ad6). Sizing,
placement and PR assignment are the planner's; this addendum records only that the fix is authorized
and where the field belongs.

[↑ TOC](#toc)

## Residual band after the rulings {#residual}

After [`AD2`](#ad2) and [`AD3`](#ad3), the partial-from-zero problem reduces to **one cell**:

> a **non-disaggregated** model, configured **`[TA]`-only**, with a **genuinely new** variant at zero
> replicas (no retained price to recover), under load **below the queueing threshold**.

Everything else is covered:

| case | covered by |
|---|---|
| P/D, any config | [`AD2`](#ad2) — sat is mandatory and is role-complete; the `satEnabled` (b)-fallback supplies the cold variant's PRC and role |
| prefill from zero, any config | [`AD3`](#ad3) — abstaining is the correct action |
| non-disaggregated, `[sat]` or `[sat,TA]` | sat's pricing ladder — its own stored `CapacityRecord` needs no pods |
| non-disaggregated, `[TA]`-only, **long-idle** variant | the retention exception in [`AD6`](#ad6), if scoped |
| the residual cell above | `N8` (abstain, don't borrow) governs the decision; the reactive `scalefromzero` engine is the backstop |

**The backstop is real but narrower than "covered".** The reactive `scalefromzero` engine is per-VA
(not model-gated) and wakes on the EPP flow-control queue metric matched on `modelID` — so it does
reach a single cold variant of a warm model. But it is reactive **under queueing**: the uncovered band
is load that matters and has not queued yet. That band is the honest residual, and `N8` is the right
answer within it — an analyzer that cannot price a variant should abstain, not guess.

[↑ TOC](#toc)

## Withdrawn framings {#withdrawn}

Recorded because the corrected claims above are only legible against them.

1. **"Zero role demand means the denominator vanishes."** Wrong side of the fraction. Dean:
   *"why vanish. if there is no EPP queue then there is no demand on the role."* He was right — zero
   role demand from absent traffic is *correct* behaviour, and on P/D it self-corrects because a cold
   prefill under real traffic does queue and sat does attribute `inputTokens` to it. The real defect
   is the **numerator**, and it is [`AD1`](#ad1).
2. **"A zero per-variant `TotalDemand` means the variant has no demand."** Wrong scope. Dean:
   *"demand is per model not per variant. it just means it does not count tokens from that variant not
   that totalDemand is zero."* Verified, and stronger than stated: per-variant `TotalDemand` is
   introspection-only on **both** analyzers, so a zero there is a correct attribution of *observed*
   traffic and says nothing about whether the variant should run.

**Not verified by this author — flagged rather than asserted.** The two preconditions the internal
reviewer attaches to saturation's tier-2 (own-`CapacityRecord`) rung — the `engine_v2.go`
`scaleTarget == nil` skip, and the `capacity_store.go:126-128` `EffectiveCapacity <= 0 &&
EffectiveMaxBatchedTokens > 0` condition. The [§ residual](#residual) table's "sat's pricing ladder"
row depends on that rung actually firing for a zero-replica variant. If either precondition blocks
it, that row weakens and the residual cell widens to include `[sat]`-only. Worth one read before the
table is relied on.

[↑ TOC](#toc)

## Disposition summary {#disposition}

| # | Item | Status | Owner of what remains |
|---|---|---|---|
| `AD1` | TA is not role-complete for P/D; prefill demand is structurally 0 | **Verified fact** — no decision needed | — |
| `AD2` | `[TA]`-only unsupported on P/D; both-by-default; documented, unenforced | **DECIDED (Dean)** | doc placement — planner |
| `AD3` | From-zero PRC work scoped to `decode`/`both` only | **DECIDED (Dean)** — follows from `AD1` | — |
| `AD4` | TA does not veto sat either way; `N7` fails safe on scale-down | **Verified fact** | `N7` disposition line — planner |
| `AD5` | Binding-path override; hold the role when the binder is not role-complete | **OPEN** | PR-2 scope — planner; priority — Dean |
| `AD6` | Sibling pricing rejected; retention exception retained; shared 2-field prerequisite | **DECIDED (Dean) to skip the lookup**; retention **OPEN** | retention scoping — planner |
| `AD7` | `N5` sat `Cost = 0` at zero replicas | **DECIDED (Dean): fix** | sizing/placement — planner |
| — | fair-share `ceil` → `floor` | **NOT IN THIS ADDENDUM** — held | separate discussion (Dean) |

**Unchanged by this addendum:** the parent's `FZ-admission` decision (`Reason`-tagged `PRC = 1`
sentinel + one-replica target ceiling at the three grant sites), `(D-a)`'s deferral, the unit
contract, the combine rule, and the anchor contract. This addendum narrows the *domain* of the
from-zero pricing question; it does not reopen the mechanism chosen for it.

[↑ TOC](#toc)
