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

## Code currency — **corrected in Rev 2** {#currency}

**Baseline: worktree `ta-anchor-dynamic-refresh` @ `a9afb740` (PR-2, in flight), read 2026-08-08.**

**Rev 1 of this addendum was baselined on `Main @ a6b39809` and that was the wrong tree.** This
addendum's subject *is* PR-2's end state — role completeness under the multi-vote combine — and PR-2
replaces the very operators the analysis reasons about. Rev 1's citations were internally accurate
for `Main` and therefore misleading here. Every claim below has been re-read on `a9afb740`. What the
re-verification changed is recorded per-item in [§ checklist](#checklist) and in
[§ withdrawn](#withdrawn) item 3; the two substantive changes are **[`AD4`](#ad4)** (its
identity-element argument does not survive the score-weighted combine) and **[`AD5`](#ad5)** (its
mechanism sentence described the pre-PR-2 anchor read).

**Citation rule, applied strictly from Rev 2 on.** Function, field and struct names are
authoritative. A `file.go:N` line number appears **only where this author read that line on
`a9afb740`**; nothing is carried over from `Main` or from memory. Line numbers still drift with the
coder's commits — [§ checklist](#checklist) gives a re-verification command per item so drift is
detectable rather than silent.

Where a claim is genuinely about *merged, shipped* behaviour rather than PR-2's end state, the tree is
named inline (`Main @ a6b39809`, which contains PR-1 #1516 squash `57f3fe64`).

**Explicitly out of scope — held for a separate discussion.** The fair-share `ceil` → `floor`
conversion (parent [§ bugs](combined-analyzer-optimizer-design.md#bugs) #5 / `fairShareCap` / the
GPU-space unit table) is **not addressed here**. Dean, 2026-08-08: *"the ceil/floor we discuss
later."* Nothing in this addendum depends on that outcome, and nothing here should be read as
settling it.

**Provenance.** This addendum records the outcome of a design discussion held 2026-08-07/08 in which
Dean issued three rulings and rejected two of this author's proposals. His rulings are quoted where
they are load-bearing. Rulings are **unaffected by the Rev 2 re-baseline** — they are decisions, not
code readings. Three of the author's own framings were wrong and were withdrawn; they are recorded in
[§ withdrawn](#withdrawn) rather than deleted, because the corrected version is only legible against
them.

---

## TOC {#toc}

- [Why this addendum exists {#why}](#why-this-addendum-exists-why) L76:95
- [AD1 — the ThroughputAnalyzer is not a P/D-complete analyzer {#ad1}](#ad1--the-throughputanalyzer-is-not-a-pd-complete-analyzer-ad1) L96:171
- [AD2 — ruling: `[TA]`-only is unsupported on P/D models; both analyzers is the default {#ad2}](#ad2--ruling-ta-only-is-unsupported-on-pd-models-both-analyzers-is-the-default-ad2) L172:199
- [AD3 — the from-zero PRC work is scoped to `decode` and `both` roles only {#ad3}](#ad3--the-from-zero-prc-work-is-scoped-to-decode-and-both-roles-only-ad3) L200:253
- [AD4 — TA cannot veto saturation, but under PR-2 it can dilute it {#ad4}](#ad4--ta-cannot-veto-saturation-but-under-pr-2-it-can-dilute-it-ad4) L254:334
- [AD5 — the one real override is the binding path, not voting — OPEN {#ad5}](#ad5--the-one-real-override-is-the-binding-path-not-voting--open-ad5) L335:441
- [AD6 — rejected: TA cross-variant sibling pricing. Retained: the retention exception {#ad6}](#ad6--rejected-ta-cross-variant-sibling-pricing-retained-the-retention-exception-ad6) L442:491
- [AD7 — `N5` (saturation `Cost = 0` at zero replicas) is to be fixed {#ad7}](#ad7--n5-saturation-cost--0-at-zero-replicas-is-to-be-fixed-ad7) L492:514
- [AD8 — the prefill role is not merely starved, it is actively drained — OPEN {#ad8}](#ad8--the-prefill-role-is-not-merely-starved-it-is-actively-drained--open-ad8) L515:723
- [Residual band after the rulings {#residual}](#residual-band-after-the-rulings-residual) L724:770
- [Verification checklist — for the planner and reviewer {#checklist}](#verification-checklist--for-the-planner-and-reviewer-checklist) L771:805
- [Withdrawn framings {#withdrawn}](#withdrawn-framings-withdrawn) L806:875
- [Disposition summary {#disposition}](#disposition-summary-disposition) L876:904

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

**Status after the Rev 2 re-verification: HOLDS on `a9afb740`, unchanged.** Step 5's operator is
different on PR-2 and is re-cited below; the chain still terminates at zero.

**Evidence, in order** (all `a9afb740`).

1. **TA's demand is decode-rate-denominated and model-level.** `throughput/analyzer.go` computes
   `arrivalDecodeDemand = input.ArrivalRate * avgOL`, sets `totalDemand = arrivalDecodeDemand`, then
   adds `queueDemand` from `estimateQueueDemand(input.SchedulerQueue, avgDecodeITLSat,
   DefaultQueueDrainFactor)`. Its own comment states the model-level arrival term *replaced* the
   per-variant summation, and that per-variant `VariantCapacity.TotalDemand` is retained "for
   per-variant introspection".
2. **The split to roles excludes prefill by construction, and there is no second path.**
   `distributeDemandByRole` builds its role set with `if role != domain.RolePrefill`
   (`throughput/analyzer.go:928`) — prefill is never added to the map, so it gets no `share`. Both
   demand terms go through this one function and it has **exactly two call sites**, `:478`
   (`arrivalDemandByRole`) and `:483` (`queueDemandByRole`), which are also the sole sources of both
   maps (`git grep -n distributeDemandByRole a9afb740 -- internal` returns only those two plus the
   definition and two comments). ⚠️ **This makes the zero unconditional rather than data-dependent:**
   TA reports prefill `TotalDemand == 0` for *every* P/D model, at every arrival rate, in every
   configuration — there is no input that produces a non-zero. Any statement of this addendum's
   exposure as an "edge case" is therefore wrong; it is the only case.
3. **The exclusion is the only one of its kind in the file.** `grep RolePrefill` on
   `throughput/analyzer.go` @ `a9afb740` returns exactly two sites: `:364` (avgOL/ITL tracking) and
   `:928` (`distributeDemandByRole`). The per-variant capacity loop does **not** skip prefill — so TA
   emits prefill `VariantCapacity` entries carrying a real, **positive** `PerReplicaCapacity`. TA is
   not silent about prefill; it prices prefill and then assigns it no demand. *(This positivity is
   load-bearing for [`AD4`](#ad4) and [`AD5`](#ad5): it is why TA votes zero rather than abstaining.)*
4. **TA nevertheless emits a prefill `RoleCapacities` key.** `aggregateRoleCapacities` keys off
   `aggregation.AggregateByRole(vcs)` — the **variant capacities**, not `distributeDemandByRole`'s
   output — so on a P/D model the prefill bucket **exists**, with
   `TotalDemand = arrivalDemandByRole[prefill] + queueDemandByRole[prefill] = 0`. Its doc comment
   confirms `RequiredCapacity`/`SpareCapacity` are "left zero — the engine's universal threshold
   post-step writes them". **A present key carrying zero, not an absent key**, is what every
   downstream participation rule sees.
5. **Zero demand becomes zero required capacity.** The per-role threshold post-step
   (`saturation/engine_v2.go:502` writes `rc.RequiredCapacity`, `:509` writes `rc.SpareCapacity`)
   computes `RequiredCapacity = TotalDemand/scaleUp − TotalAnticipatedSupply` and
   `SpareCapacity = TotalSupply − TotalDemand/scaleDown`, both floored at 0. With `TotalDemand == 0`:
   **`RequiredCapacity(prefill) = 0`** and **`SpareCapacity(prefill) = TotalSupply`** — TA reports the
   entire prefill fleet as spare.
6. **Zero required capacity becomes zero replicas at the combine.** `initRoleState`
   (`pipeline/analyzer_helpers.go:369-397`) iterates `e.Result.RoleCapacities` and seeds
   `pickerState[i][role] = rc.RequiredCapacity` (`:384`) and `RoleSpare[role] = rc.SpareCapacity`
   (`:385`); `roleBottleneckReplicas` (`:624-633`) then takes
   `combineVotes(votesFromPickerState(s, state, role, v), true)` and `ceil`s it. `0 / prc = 0` for any
   positive PRC.

**Consequences — two, both structural.**

- **TA can never drive prefill scale-up.** Not "usually doesn't" — cannot, at any arrival rate.
- **TA always reports the whole prefill supply as spare.** `SpareCapacity = TotalSupply −
  TotalDemand/scaleDown` (`saturation/engine_v2.go:505-509`) with `TotalDemand = 0` yields exactly
  `TotalSupply`. ⚠️ **Rev 1 and Rev 2 both called this "harmless because TA cannot act alone." It is
  not harmless — it is an affirmative authorization to shed the entire prefill role**, and when TA is
  the only voter nothing contradicts it. See **[`AD8`](#ad8)**, which is the corrected form of that
  sentence and the most severe item in this addendum.

**Contract statement.** An analyzer is **role-complete** for a model iff it produces a demand model
for every role that model's variants declare. TA is role-complete for non-disaggregated models and
for the `decode`/`both` roles; **TA is not role-complete for a P/D model.** Saturation is: it
attributes queue demand to prefill explicitly — `estimateSchedulerQueueDemand`
(`analyzers/saturation_v2/analyzer.go:750`) switches on role and assigns `inputTokens` to prefill,
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
specs** (`domain.VariantReplicaState.Role`, `saturation_analyzer.go:402-403`, populated per
reconcile). At the moment the analyzer set is fixed, no role is known. Any real check would therefore
be a *per-model runtime warning* raised the first time a prefill-roled variant is observed under a
TA-only configuration — a different piece of work, not a config schema addition.

**Therefore the constraint ships unenforced.** That is an accepted cost, recorded here so nobody
later reads the absence of a check as an oversight. If it is ever to be enforced, the per-model
runtime warning above is the shape.

⚠️ **The mitigation this ruling relies on is weaker under PR-2 than Rev 1 assumed.** "Always run sat
alongside TA" protects prefill only while TA's configured vote `Score` does not exceed sat's — see
[`AD4`](#ad4). The ruling stands; its protective claim is now conditional and that condition belongs
in whatever doc carries the ruling.

[↑ TOC](#toc)

## AD3 — the from-zero PRC work is scoped to `decode` and `both` roles only {#ad3}

**The scoping conclusion follows from [`AD1`](#ad1).** Every candidate mechanism for pricing a
zero-replica variant — a retained last-known PRC, an inherited sibling price, a demand-model ratio,
or the `FZ-admission` `PRC = 1` sentinel — is a **denominator** intervention. The prefill blocker is
a **zero numerator**. `ceil(0 / anything) = 0`, so no pricing mechanism can make prefill *scale up*.
Pricing work aimed at prefill from-zero cannot achieve its goal.

⚠️ **Rev 1 and Rev 2 justified that with "all four mechanisms are exactly equally inert." That reason
is false, and it is false in the dangerous direction.** Correction raised by the planner
(`designer__ad3-rationale-false-…`, 2026-08-08) and verified here on `a9afb740`: **pricing a prefill
variant is not inert — it removes a guard.** Both scale-down consumers skip an unpriced variant —
`scaleDownVariantSet` at `cost_aware_optimizer.go:139-141` and the reference-variant scan at
`rescale.go:586-588` — on `if vc.PerReplicaCapacity <= 0 { continue }`. Give a prefill variant a
positive PRC and the demand stays 0 while **the skip stops firing**, so `removable` becomes
`current − minReplicas` (`cost_aware_optimizer.go:149`) and the role is shed. So a reader who
believes pricing is inert for prefill may relax this scoping as harmless — and that is precisely the
change that converts [`AD5`](#ad5)'s frozen role into an actively torn-down one ([`AD8`](#ad8)).

**Corrected rationale, no new mechanism:** prefill demand is zero for reasons *upstream of pricing*,
so pricing cannot make prefill scale up — **and** pricing a prefill variant is not neutral, because
it removes the unpriced-skip that currently declines part of the teardown. The scoping is therefore
load-bearing, not merely tidy.

**One refinement, which is this author's and narrows where the cancellation actually holds.** The
planner's framing — that `AD5` is frozen because two effects of `PerReplicaCapacity = 0` cancel — is
correct **only for a prefill variant at zero replicas**. For a prefill variant *with live replicas*
TA already emits a positive PRC (`throughput/analyzer.go:398-408` appends a `VariantCapacity` for
every live variant; the only role filter in that loop, `:364`, gates the decode ITL/OL aggregation,
not the append), and the retained-supply complement at `:435-437` extends that to a recently-live
variant at zero. **So in the live-replica case the skip is already not firing and the teardown is
already reachable today** — no `(D-a)` required. `(D-a)` would extend it to never-measured prefill
variants. That is the difference between a latent coupling and a live one, and [`AD8`](#ad8) is the
live one.

**Confirmed on `a9afb740`, and the sentinel's state is now citable.** `ReasonFromZeroAdmission` is
declared (`pipeline/analyzer_helpers.go:95`), documented (`:65`), and read by the one-replica clamp
(`:122`) — but **nothing outside `_test.go` files writes it**. `:187` and `:303` say so in prose
("the admitting write site is deferred"). So the parent's `(D-a)` deferral is confirmed in-tree, and
`AD3` is unaffected either way: a denominator device that is never written and a denominator device
that is written are equally inert against a zero numerator.

**And abstaining is the right answer, not a limitation.** Dean, 2026-08-07: *"Not scaling from zero
is the correct action."* A cold prefill variant on a P/D model under real traffic *will* queue, sat
*will* attribute `inputTokens` to prefill, and sat is mandatory on P/D by [`AD2`](#ad2) — so the case
is covered by the analyzer that models the role, on the cycle where the demand becomes real.

**Scope statement for implementers:** any from-zero pricing mechanism is specified over variants whose
`Role` is `decode` or `both` (including the empty-string default, which `distributeDemandByRole`
normalizes to `both`). Prefill variants are out of its domain — not by a guard that must be written,
but because the mechanism cannot reach them.

[↑ TOC](#toc)

## AD4 — TA cannot veto saturation, but under PR-2 it can dilute it {#ad4}

Dean, 2026-08-07: *"We should check TA does not veto sat in this p/d scenario."* Checked against both
combine operators **on `a9afb740`**.

⚠️ **Rev 1 answered this on `Main` and its argument does not survive.** Rev 1 said TA's structural
zero is the **identity element** of a plain cross-analyzer MAX. That was true of `Main`. PR-2 replaces
the plain MAX with a **score-weighted** combine, and a structural zero is not the identity element of
that. The verdict "no veto" survives; the reason changes, and a new bounded hazard appears.

**Scale-up — MAX binder plus a score-weighted correction.** `combineVotes`
(`pipeline/analyzer_helpers.go:456-494`) picks the extremum (`up=true` ⇒ max) as *binder*, then pulls
it toward every voter **more trusted than the binder**:
`result = e − Σ_j (e − v_j)·max(0, s_j − s_binder) / Σ_j s_j`.

- TA **participates rather than abstaining.** `votesFromPickerState` (`:522-534`) abstains only on
  `prc <= 0`; TA's prefill PRC is positive ([`AD1`](#ad1) step 3), so TA casts a real **zero** vote.
  The function's own comment at `:530-533` names exactly this hazard — *"a zero vote is an opinion
  that no replicas are needed, which is the opposite of having no opinion"* — but its guard keys on
  **unpriceable**, not on **role-incomplete**, so TA's well-priced prefill zero slips through it.
- **At default configuration there is no effect.** `voteScore` (`:512-517`) returns `1.0` whenever
  `e.Score <= 0`, so with both analyzers unscored `s_TA − s_sat = 0`, the correction is 0, and sat's
  prefill count stands. **`AD4`'s conclusion holds at defaults.**
- **With TA scored above sat, TA drags prefill down.** `s_TA > s_sat` makes the correction strictly
  positive and proportional to `(e − 0)`, i.e. to sat's entire prefill demand. TA cannot *veto* — the
  binder is still sat — but it can **dilute**, without ever modelling the role. This is the same
  principle `W4` applies to unpriced demand, unapplied in the role-incomplete direction.
- **The same mechanism reaches the rescale GPU budget**, via `votesFromTotalDemand` (whose abstain
  guard is likewise `prc <= 0`) inside `roleDemandGPUs` — see [`AD5`](#ad5). So the blast radius is
  both the scale-up replica count and the fair-share GPU split, not one of them.

**Scale-down — a new per-role veto gate, and TA does not trip it (except harmlessly).** PR-2 adds
`roleSpareVetoed` (`:758-771`): **any single live entry** with `RoleSpare[role] <= 0` vetoes the whole
role. It is consulted by both `needsScaleDownForRole` (`:891-909`, at `:892`) and
`safeRemovalReplicasForRole` (`:800-812`, at `:801`).

- TA's `RoleSpare[prefill] = TotalSupply − 0 > 0` whenever prefill has any supply ⇒ **no veto from
  TA**, and sat's veto still binds. TA cannot override sat. ⚠️ **But "no veto" is not a benign
  result here** — it is the absence of the only gate that could have declined a whole-role teardown,
  and TA's spare *is* that teardown's authorization. See [`AD8`](#ad8).
- When prefill supply is itself zero — precisely the partial-from-zero case — TA's spare is `0`, so
  **TA does veto** the prefill role's scale-down. This **fails safe**: it blocks removal from a role
  that has nothing to remove.
- When scale-down proceeds, `safeRemovalReplicasForRole` takes `combineVotes(votesFromRoleSpare,
  false)` — min binder, same correction, one `floor`. TA cannot enlarge a scale-down.

**`N7` — the disposition survives, but the mechanism Rev 2 gave for it was wrong.** ⚠️ Rev 2 wrote
that a missing role key *"routes a divergent key-set into `roleSpareVetoed`"*. **It does not.** Raised
by the planner (`designer__ad3-rationale-false-…`) and the reviewer (Finding 66) independently, and
verified here: **a missing key ABSTAINS, it never vetoes.** `roleSpareVetoed` (`:736-771`) requires
the key to be *present* — `if spare, ok := e.RoleSpare[role]; ok && spare <= 0` (`:766`) — and
`needsScaleDownForRole` skips the entry outright, `if _, ok := e.RoleSpare[role]; !ok { continue }`
(`:903-905`), under a comment that says *"abstain, not veto"*. That is the `N2`/`N7` abstain-vs-veto
resolution PR-2 already shipped, and it is the correct design.

The participation rules **are** asymmetric, and that part of Rev 2 stands: `votesFromTotalDemand`
(`:545-569`) and `votesFromPickerState` skip a missing key, while `votesFromRoleSpare` reads a live
entry's missing key as `0.0` **deliberately** (doc at `:583-593`). But that `0.0` enters the
**magnitude ballot**, not the veto — so the fail-safety comes from the zero *vote*, not from a veto.

**And that vote is not absolute.** `safeRemovalReplicasForRole`'s own doc says so at `:796-799`:
*"the dominance correction pulls the combined value positive whenever a higher-scored voter reports
spare … A zero vote is only absolute when no voter outscores it."* So `N7` is **score-conditional in
exactly the way [`AD4`](#ad4)'s scale-up half is** — one root, `combineVotes`'s dominance correction,
pointing in two directions. `N7` may be dispositioned fail-safe **at the shipped uniform scores**,
which is what makes the disposition survive; it is not fail-safe by construction.

Two corrections of the correction, both this author's, because the peer framings over-generalize in
the same place: (1) the route via `liveCount == 0` requires the analyzer to **abstain**, and **TA does
not abstain on prefill** — it emits the key ([`AD1`](#ad1) step 4), so for prefill `liveCount == 1`
and `needsScaleDownForRole` returns **true**; `N7`'s never-scales-down outcome is therefore *not* what
protects prefill. (2) Nothing here is a backstop for [`AD8`](#ad8): believing a missing key vetoes is
precisely what makes that teardown look impossible.

**Also checked:** the `anchor.RoleCapacities[role]` read in `pipeline/cost_aware_optimizer.go`
populates `decision.RequiredCapacity` / `SpareCapacity` for the `wva_required_capacity` /
`wva_spare_capacity` gauges only. It is observability, not a control path — though see [`AD5`](#ad5)
for what it means for the prefill gauge.

[↑ TOC](#toc)

## AD5 — the one real override is the binding path, not voting — OPEN {#ad5}

⚠️ **Rev 1's mechanism sentence was written against `Main` and is wrong for PR-2.** Rev 1 said
`roleDemandGPUs` reads `anchor.RoleCapacities[role].TotalDemand`. That is verbatim true on
`Main @ a6b39809` — where `combineVotes` and `votesFromTotalDemand` do not exist at all — and false on
`a9afb740`. **The conclusion below is unchanged; only the route to it is.** Traced end-to-end:

**PR-2's actual mechanism.** `roleDemandGPUs` (`pipeline/rescale.go:579`) now takes the ballot:
`roleDemandGPUs(anchor, s, stateMap, accType, role)`. The **anchor supplies only reference-variant
identity and pricing** — the cost-ascending scan picks `bestVariant`/`bestGPUs` and returns 0 if no
variant on the topology is priceable — and **demand comes from
`combineVotes(votesFromTotalDemand(s, role, bestVariant), true)`**. `s` is `votingResults(...)` at
both call sites (`:360` feeding `:371`, and `:518` feeding `:563`). PR-2 also adds
`refreshAnchorSizing` (`analyzer_helpers.go:646`), which overwrites the anchor's own
`VariantCapacities` with the per-`(role, variant)` binder over the same ballot — so the anchor's
sizing is itself ballot-derived, which **strengthens** this section's point rather than weakening it.

**The conclusion, re-derived on PR-2.** When TA is the sole voter on a P/D model, prefill still gets
nothing:

- TA emits a prefill `RoleCapacities` key ([`AD1`](#ad1) step 4), so `votesFromTotalDemand` does not
  skip it on the missing-key branch; TA's prefill PRC is positive, so it does not abstain on
  `prc <= 0` either. **TA casts a real zero vote.**
- `combineVotes([{Value: 0}], up=true)` returns `(0, binder=0)`; `ceil(0)` is not `> 0`; `replicas`
  stays `0`; the function returns `0 × bestGPUs`. **The prefill role is granted no fair-share
  budget** — via a zero vote rather than a zero anchor field. The single vote's own `excess` is 0, so
  the dominance correction is 0 and the value survives as **exactly** 0: `ceil` has no epsilon to lift.
- The prefill `wva_required_capacity` gauge reads `0` — so the symptom is invisible in exactly the
  series an operator would check. **Observability is a second, separate site:**
  `cost_aware_optimizer.go:350-367` still reads `anchor.RoleCapacities[role]` wholesale for
  `decision.RequiredCapacity`, because bug #3 moved *sizing* onto the ballot and left *reporting* on
  the anchor. A sizing-only fix leaves the gauge at 0 (reviewer, Finding 66).

**Three sub-regimes reach `0` by different routes, and only one of them is `AD5`'s.** Rev 2 said the
outcome is "insensitive to which branch fires". True of the *outcome*; **false of the fix**, because a
predicate can only key on a state that actually occurs. On `a9afb740`:

| # | state | route to 0 | does the combine run? |
|---|---|---|---|
| (i) | `[sat,TA]`, prefill **has live replicas** | TA prices it (`throughput/analyzer.go:398-408`), so the reference loop finds a candidate; TA casts a real zero vote | **yes**, `binder = 0` |
| (ii) | `[sat,TA]`, **every** prefill variant at zero replicas and unpriced | candidates exist on the topology but all fail `PerReplicaCapacity <= 0` (`rescale.go:586-588`) ⇒ `bestVariant == ""` | **no** — early return at `:593-594` |
| (iii) | `[TA]`-only | TA sets no `AcceleratorName`, so `variantsOnType` (`:606-614`) is empty ⇒ `bestVariant == ""` | **no** |

**`AD5` is regime (i).** ⚠️ Both peer reviews assert that `bestVariant == ""` "does not fire", on the
grounds that a stale saturation keeps carrying `AcceleratorName` so the reference loop finds a
candidate. That is right for regime (i) and **over-general as stated**: `AcceleratorName` survival only
makes the loop *iterate*: setting `bestVariant` still requires a positively-priced candidate, which is
exactly what regimes (ii) and (iii) lack. The distinction is not academic — it is which predicate can
see the state.

**Placement consequence, sharper than "not where `AD5` points".** A predicate keyed on `binder < 0`,
on an empty vote set, or on `bestVariant == ""` **misses regime (i) entirely** — the one this section
is about. Conversely a predicate placed only at the early return misses nothing else, because (ii) and
(iii) are the zero-replica and no-topology corners, not the role-incomplete one. So the hold predicate
belongs **where the ballot is assembled**, keyed on *who modelled the role*, not on any downstream
degenerate value.

> **Sub-decision, and it is this author's to make (raised by the coder, routed here by the planner and
> seconded by the reviewer).** A hold predicate must declare **which state triggers it**: *nobody
> priced this role* versus *the analyzers that model it agree it needs nothing*. These are the same
> abstain-versus-veto seam already settled for pricing and for `RoleSpare` — and today both return 0
> GPUs, which is why they have never had to be told apart. `AD5` is the **second**; regime (ii)/(iii)
> is the first. **They need different predicates, so this is a precondition for the fix existing, not a
> refinement to make afterwards.** Recorded here as owed Type-1 work; not decided in this revision,
> because deciding it is a new Type-1 increment and the parent is frozen.

**`VG-up` is already landed, not pending.** Rev 1 framed this as "a mask is about to be removed".
`votingResults` on `a9afb740` already reads `if e.Enabled && e.Live` (`analyzer_helpers.go:335`).
So the accidental protection Rev 1 described — a stale-but-enabled sat entry still reaching the
scale-up combine and *incidentally* supplying a nonzero prefill `RequiredCapacity` during a sat
outage — **is already gone in the coder's tree.** A `[sat,TA]` P/D model whose sat has gone stale now
runs prefill on TA's structural zero alone while decode continues to scale.

⚠️ **Rev 2 called that "a model that quietly stops scaling half of itself". That understates it and
the correction matters to the scope call below:** the same structural zero also *authorizes removal*,
so the model **sheds prefill toward one replica** while decode scales normally. [`AD8`](#ad8) carries
the two verified routes. A missed scale-up forgoes headroom; the real exposure is an active drain on a
role serving traffic. **The window is exactly as narrow as stated here; the consequence inside it is
not.**

Neither behaviour is correct: relying on a stale value is wrong, and sizing a role from an analyzer
that has no model of it is also wrong.

**Design position (this author's recommendation, not a decision):** when the binding analyzer is not
role-complete for a role, that role should be **held** — the same per-model hold the parent already
specifies for `bindingAnchor == nil` — rather than sized from a demand it does not model. A hold is
already an expressible outcome, so this is a predicate, not a new mechanism.

> **OPEN — needs a scope decision.** Whether this lands in PR-2 or is recorded as a known limitation
> of `[sat,TA]` under sat outage is the **planner's** call on scope and Dean's on priority. Both are
> defensible: the window is narrow (requires a sat outage on a P/D model), and PR-2 is already large.
> Rev 1 argued this as "do not ship `VG-up` without noticing" — that framing is spent, since `VG-up`
> has landed. The live form of the ask is: **decide it as a known limitation or a fix, on the record,
> rather than by default.**
>
> **Three inputs this author owes that decision, none of them a recommendation to reverse:**
> (1) the severity above and in [`AD8`](#ad8) — a teardown, not a missed grant; (2) the sub-decision
> boxed earlier is a **precondition** for any predicate, so "fix it in PR-2" means adding a Type-1
> increment to a finished branch, which under *"don't leave design decisions to coder"* is a real cost
> of the fix-now option, not an argument against deferring; (3) [`AD8`](#ad8) route **(A) is not fixed
> by this predicate at all** — it runs off `RoleSpare`, needs no sat outage, and is inherited from base
> `075a208e`, so deferring `AD5` leaves *more* on the table than `AD5` itself. The planner's stated
> lean — defer, with the coupling recorded unconditionally in the Type 3 — remains defensible on all
> three; it is simply deferring a larger item than the record previously showed.

[↑ TOC](#toc)

## AD6 — rejected: TA cross-variant sibling pricing. Retained: the retention exception {#ad6}

**Rejected — TA inheriting a price from a compatible sibling.** Dean, 2026-08-07: *"Good idea, but
skip unless really cheap."* Verified: it is not cheap. **Rejection stands after Rev 2**, with one
component re-costed downward — see the plumbing paragraph.

Saturation can do this because it has a three-tier ladder (live median → its own stored
`CapacityRecord`, which is spec-parsed and needs no pods → a compatible sibling matched on
accelerator **and** `GPUsPerReplica`). TA has one tier: its own retained `lastPerReplicaSupply`. To
add sat's third tier to TA needs (a) an accelerator identity TA cannot currently see, (b) a
compatibility predicate, and (c) a provenance decision about how an inherited price is labelled.
Without (a) the predicate is not merely incomplete — it would happily inherit an H100 price onto an
A100 variant, which is worse than abstaining.

**Retained and still available — Dean's own retention exception.** Carrying
`lastPerReplicaSupply` (plus `role` and `lastFittedB`) across TA's idle expiry is cheap and is
*his* proposal, not a substitute for it. The eviction at `throughput/analyzer.go:160` drops the whole
`variantState` after `2*DefaultObservationMaxAge`; its comment gives two motives — bounding memory,
and avoiding false shape-change signals on recreate — and **neither motive covers the price**. The
shape hazard lives in `observationWindow`/`shapeTracker`, and `lastFittedB` already has an explicit
"a shape change must not clear this" carve-out; idle expiry deserves the same carve-out.
Its limit is honest: it covers a **long-idle** variant, never a genuinely new one.
Residual hazard: the state key is `variantKey(ns, modelID, variantName)`, so a variant recreated on
different hardware inherits a stale price — the same accelerator-identity gap as above.

**One plumbing change would serve three items — and component (a) is cheaper than Rev 1 said.**
`domain.VariantReplicaState` (`saturation_analyzer.go:387-410`) is spec/deployment-derived — it exists
for a zero-replica variant and already carries `GPUsPerReplica`, `Role`, `MinReplicas`, `MaxReplicas`
— but it has **no `AcceleratorName` and no `Cost`** (verified unchanged on `a9afb740`). Both fields
exist on `domain.ReplicaMetrics` (`:58-59`), a *live-pod* type, which is precisely why a cold variant
cannot see them.

**Rev 2 correction:** the accelerator identity is **already derived pod-free elsewhere in the
system** — `saturation/engine_v2.go:48` calls `accelerator.GetAcceleratorNameFromScaleTarget(va,
scaleTarget)` and hands it to `capacityStore.LoadFromScaleTarget(...)` (`:50`), which stores it on the
`CapacityRecord` (`analyzers/saturation_v2/capacity_store.go:105`). So (a) is not a missing capability
but a missing *wire*: the value exists at spec level and needs surfacing onto the type TA reads.
**This does not reverse the rejection** — (b) the predicate and (c) the provenance decision remain,
and they were always the larger half — but it means the three items share one prerequisite and should
be scoped together if any of them is scoped at all.

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

**Root cause, stated precisely, re-verified on `a9afb740`.** Cost is a **spec** property
(`va.Spec.VariantCost` is the existing precedent) but the pipeline reads it from a
**live-pod-derived** type: `domain.ReplicaMetrics.Cost` (`saturation_analyzer.go:59`). Sat builds each
`domain.VariantCapacity` with `AcceleratorName`/`Cost` taken from its per-variant analysis
(`analyzers/saturation_v2/analyzer.go:441-444`), which is live-derived. A variant with zero replicas
has no `ReplicaMetrics` entry, so it has no cost, so it is free. **The bug is the sourcing, not the
arithmetic.**

**Shape of the fix:** source cost from the spec for every variant that has one, independent of pod
existence — which is the `Cost` half of the `VariantReplicaState` plumbing in [`AD6`](#ad6). Sizing,
placement and PR assignment are the planner's; this addendum records only that the fix is authorized
and where the field belongs.

[↑ TOC](#toc)

## AD8 — the prefill role is not merely starved, it is actively drained — OPEN {#ad8}

⚠️ **This section is a correction of this addendum, not of anyone else's document.** Rev 1 and Rev 2
both wrote that TA's whole-fleet prefill spare is *"harmless, because TA cannot act alone"*
([`AD4`](#ad4)). **That sentence is wrong, and it is the one error in this addendum whose consequence
is a running role losing replicas.** `SpareCapacity` is not an inert observation — it is the
**authorization to remove**, and TA authorizes removing all of it.

**The primitive link.** Per-role SC is `TotalSupply − TotalDemand/scaleDown`, clamped at 0
(`saturation/engine_v2.go:496-512`, the subtraction at `:509`). TA's prefill `TotalDemand` is
structurally 0 ([`AD1`](#ad1)), so TA's prefill SC is **exactly `TotalSupply`** — the entire live
prefill fleet, reported as removable. `initRoleState` copies it verbatim onto the ballot entry:
`s[i].RoleSpare[role] = rc.SpareCapacity` (`analyzer_helpers.go:385`). Nothing downstream
distinguishes "spare because measured idle" from "spare because unmodelled".

**Two independent routes consume it. Both verified on `a9afb740`; they differ in reachability and in
provenance, and that difference is the whole disposition.**

`scaleDownVariantSet` (`cost_aware_optimizer.go:124`) is a **primitive parameterised by a
`maxRemovable` callback**, and its exactly two callers differ precisely in whether they supply a role
gate:

| route | role gate consulted | reachability | provenance (**corrected — see below**) | evidence |
|---|---|---|---|---|
| **(A)** `scaleDownRoleIterated` → `scaleDownVariantSet` (`cost_aware_optimizer.go:474-505`) | **yes — both** (`needsScaleDownForRole` at `:488`; `safeRemovalReplicasForRole` as the callback at `:498`) | steady state — `else` branch of `if anyRoleNeedsScaleUp(ps, roles)` (`:61-66`). **No opt-in, no contention.** | **inherited** in magnitude; **`VG-up` makes it deterministic**. Base's mask was real but **conditional**: inherited *only if* the dead analyzer's last snapshot held **no positive `RequiredCapacity` on any role** | **CONFIRMED by execution** |
| **(B)** `reclaimRole` → `scaleDownVariantSet` (`rescale.go:404-427`, callback at `:415-421`) | **neither** — the callback is a pure GPU delta | rescale enabled for the scope **and** the group contended | **inherited from base `075a208e`** — `VG-up` cannot reach it | read-only |

**Route (A) — the gates are present and they pass rather than protect.** Under this addendum's own
preconditions every one of them is satisfied *in the permissive direction*:
`roleSpareVetoed(s, prefill)` (`analyzer_helpers.go:736-771`) needs some live entry with
`RoleSpare[prefill] <= 0`; TA's is `TotalSupply > 0`, so **no veto**. `needsScaleDownForRole`
(`:891-909`) then counts live entries carrying the key — TA carries it ([`AD1`](#ad1) step 4) — so
`liveCount == 1` and it returns **true**. The callback `safeRemovalReplicasForRole` (`:800-812`)
takes `combineVotes(votesFromRoleSpare(s, prefill, v), false)`, whose single vote is
`RoleSpare[prefill]/prc` ≈ **the whole prefill fleet in replicas**, and `floor` preserves it. Three
gates, three passes.

**Route (B) — no gate to pass.** `roleDemandGPUs` returns 0 for prefill ([`AD5`](#ad5)), so
`demByRole[prefill] = 0`; `distributeGPUsByWeight` (`rescale.go:670-705`) awards prefill only its
floor, and `roleFloorGPUs` (`:645-649`) is `minReplicas × GPUsPerReplica` — **0 whenever
`MinReplicas` is unset, which is the common case.** Hence `rt < rc`, `reclaimRole` fires, and its
`maxRemovable` callback is the pure GPU delta at `:415-421`. The `sum == 0` weight fallback at
`:685-690` does **not** rescue this: it fires only when *every* role's weight is zero, and decode's
is not.

**Provenance — corrected in this revision, and it inverts.** Rev 3's first draft of this section, and
the reviewer's Finding 66 that arrived at the same split independently, both wrote route (B) as *newly
unmasked by `VG-up`* and route (A) as plainly *inherited*. The planner contested the (B) half; this
author re-read base `075a208e` and **the planner is right, for a reason no document had used**:

- **Route (B) is inherited, and `VG-up` cannot reach it.** Base's reclaim path never read the ballot
  for demand. `roleDemandGPUs` at base took **no ballot parameter at all** —
  `roleDemandGPUs(anchor, stateMap, accType, role)` (`075a208e:rescale.go:545`), reading
  `anchor.TotalDemand` / `anchor.RoleCapacities[role]` at `:546-551`; the `s []NamedAnalyzerResult`
  argument is bug #3's addition. And base's binder gate was **already** `Enabled && Live &&
  ResultIsInformative` (`075a208e:analyzer_helpers.go:138`, `:147`) — so under this section's own
  fixture base already skipped the dead saturation, already bound TA, and already read prefill
  `TotalDemand = 0` **off the anchor**. Base `:356` → `:359` → `:367` then drained the role
  identically. The masking story required `demByRole` to come from the ballot; at base it did not.
  Pre-`VG-up` protection here never existed in any shipped state.
- **Route (A)'s magnitude is inherited but its *reachability* is not — and that half is real, not
  hypothetical.** The removal authorization is byte-equivalent at base: `safeRemovalReplicasForRole`
  (`075a208e:390`) and `needsScaleDownForRole` (`:445`) already carried `!e.Live` skips at `:394-396`
  and `:448-450`, so a dead saturation never constrained the spare min. What `VG-up` changed is the
  **dispatch**. Base `cost_aware_optimizer.go:60-66` is `s := votingResults(...)` →
  `initRoleState(s)` → `if anyRoleNeedsScaleUp(ps, roles)`, base `votingResults` gated **`Enabled`
  only** (`:237`), and base `initRoleState` (`:271`) ranges over `s` with no `.Live` guard. So at base
  a dead-but-`Enabled` saturation's **stale** `RoleCapacities` still entered `pickerState`, and
  whenever it registered any deficit the scale-up branch ran and the teardown was unreachable *that
  cycle*. Post-`VG-up` that entry is gone, prefill's only voter is TA's structural zero,
  `m[prefill] == 0` is guaranteed, and the `else` branch is taken **every** cycle.

  ⚠️ **State the condition, not just the direction — and it is broader than it first looks.**
  `anyRoleNeedsScaleUp` is a **global OR across every entry and every role**, not a prefill test:
  `for role … for _, m := range state { if m[role] > 0 { return true } }` (`a9afb740:709-718`). So a
  single positive `RequiredCapacity` **anywhere in the stale snapshot** diverted the whole model to
  scale-up — a positive *decode* `RC` alone sufficed, with prefill never consulted. Route (A) is
  therefore inherited **only in the narrow case where the dead analyzer died holding no positive `RC`
  on any role**; for a saturation that died mid-deficit — the ordinary way an analyzer dies — PR-2
  converts *"scales up on stale data"* into *"sheds prefill to one replica."* An unconditional
  "pre-existing, not ours" is the one form of this sentence the code does not support. (This precision
  is the reviewer's, Finding 67 `883c72d3`; it strictly sharpens the "stale-data-contingent" phrasing
  Rev 3 first used, and it is the reason the qualifier appears in the table cell above.)

**So the honest attribution is neither peer's.** `AD5`/`AD8` is a **pre-existing defect, not a PR-2
regression** — the planner's headline holds for both routes. But `VG-up` did convert route (A) from
*intermittent, masked by stale data* to *deterministic*, which is a real base-versus-HEAD difference
and not the hypothetical the planner scoped it to. The mask was a bug that happened to hide another
bug; removing it was still correct. **Recording both halves is what keeps a deferral honest:** PR-2
authored none of this, and PR-2 is nonetheless why it now fires on every reconcile.

**The corrected symptom — now measured, not predicted.** Not *"a model that quietly stops scaling half
of itself"* ([`AD5`](#ad5)'s wording, which understated it), and not even "sheds prefill to ~1
replica", which invites *loses a replica or two*. The coder built this section's falsifier fixture as a
scratch diagnostic, ran it, and deleted it (`git status` clean, tip unmoved at `a9afb740`):

| prefill start | cost-aware | greedy | decode (control) |
|---|---|---|---|
| 2 | **1** | **1** | 2 ✓ |
| 4 | **1** | **1** | 4 ✓ |
| 8 | **1** | **1** | 8 ✓ |

**Prefill collapses to 1 from any starting height, in a single pass, in both optimizers, while decode
holds at its starting count.** An 8-replica prefill tier sheds 7 replicas in one reconcile. The cost
of leaving this open is therefore **not proportional to fleet size** — it is the whole prefill tier
minus one, every time the window opens. Decode holding is the signature that this is role-selective
rather than a global scale-down, which is what makes it diagnostic rather than merely alarming.

**The floor at 1 is the `#1237` cheapest-at-1 rule, and it does *not* discriminate between the routes.**
`scaleDownVariantSet:156-160` protects one replica of the *last* variant in cost order when no earlier
variant still holds any (`if i == len(sortedVariants)-1 && current-n < 1 && !anyHasReplicas(...)`).
That clamp lives in the **shared primitive**, so it applies to both routes — the observed 1 is
therefore not evidence of which route ran. Route (A) remains the likely path on separate grounds: the
run was uncontended, and route (B) requires contention.

⚠️ **One inference to reject, because it is the tempting one.** Finding 67 reads the floor the opposite
way — *"`reclaimRole` has no such rule — pure GPU delta, would give 0, so measuring 1 rather than 0 is
itself the path instrumentation."* **It does not hold.** The pure-GPU-delta description is of
`reclaimRole`'s **callback**, and the clamp is applied by the primitive *after* the callback returns:
`n := maxRemovable(vc)` at `:153`, clamp at `:156-160`. Both functions say so in their own docstrings —
`scaleDownVariantSet`: *"minReplicas floor and cheapest-at-1 protection are enforced here"*;
`reclaimRole`: *"respecting minReplicas and the cheapest-at-1 protection, via scaleDownVariantSet."*
For a single-variant prefill role (`i == 0 == len-1`, `anyHasReplicas(empty) == false`) the clamp binds
on **either** route, so both would floor at 1 and route (B) would not give 0. **Consequence: the
coder's "which path ran" is still open, not closed** — and route (B)'s status stays PLAUSIBLE for
exactly the reason the coder gave, which is contention, not the floor.

> **Settled since, by the claim's own author.** Finding 68 (`a798dc87`) retracts the instrumentation
> inference on exactly these grounds, so this is a closed point rather than a live disagreement. It
> adds one fact this author did not have and has verified: **the clamp is present at base too**, same
> post-callback ordering (`075a208e:cost_aware_optimizer.go` — `n := maxRemovable(vc)` then the
> `#1237` positional rule), which is why the measured floor is 1 on **both sides at every height,
> whichever path ran**. Distinguishing the two routes now requires path instrumentation; no outcome
> value can do it.

The only other backstop is `minReplicas`, commonly unset. A missed scale-up forgoes headroom; this
removes capacity from a role serving traffic.

**Consequences for the rest of this addendum.**

- [`AD2`](#ad2) is escalated from guidance to a **hard requirement on P/D models**. "`[TA]`-only is
  unsupported on P/D" was argued on a missed scale-up. The real exposure is a teardown, and route (A)
  needs no outage at all — a P/D model configured `[TA]`-only sheds prefill in ordinary steady state.
- [`AD4`](#ad4)'s scale-down half needs the qualification carried in this section: TA's non-veto is
  not a benign result. It is the absence of the only thing that could have stopped route (A).
- [`AD5`](#ad5)'s hold predicate, if adopted, addresses route (B) only — it acts on demand. Route (A)
  runs off `RoleSpare` and needs its own predicate. **A fix for one is not a fix for the other**, and
  no document said so before this one.

> **OPEN — this is a disposition request, not a decision.** Scope, placement and whether any of it
> rides PR-2 are the planner's and Dean's. What this section asks is only that the record show the
> severity that actually follows, so that a deferral defers the real item. Convergent independent
> arrivals: the reviewer's Finding 66 (`26a229dd`, and handoff
> `plan__ta-anchor-ad5-mechanism-and-severity-verified`) reached the same two-route split and the same
> inherited-versus-unmasked provenance from its own reading.

**Evidence status — split, and precise about which half is which.**

- **Route (A): CONFIRMED by execution.** The fixture is the one the reviewer proposed and this author
  endorsed unchanged — P/D model, `[sat,TA]`, saturation `Enabled: true, Live: false` still carrying
  topology (`AcceleratorName`, `Cost`, `Role`, `ReplicaCount`), TA live and binding, prefill
  `TotalDemand: 0` with supply untouched, decode's demand set to exactly cover its own replicas as a
  control, no `MinReplicas`. It was predicted red and **ran red**, at three heights and in both
  optimizers. The pipeline suite stayed green at its unchanged 386 specs while the diagnostic was
  present.
- **Route (B): still PLAUSIBLE by reading, not confirmed.** The contended-rescale half was not
  exercised — the run used unlimited constraints, so it was almost certainly not contended and very
  likely never entered `reclaimRole`. Its links are source reads only. **The provenance claim above
  for route (B) is likewise a base-versus-HEAD source read**, not an executed base run.
- **The provenance falsifier is now half-run, and the executed half came out as predicted.** The test
  is the same fixture at base `075a208e` in two variants: stale saturation `RoleCapacities`
  **all-zero**, and with **any one role positive**. Prediction from the reading above: base **drains**
  in the first and **does not** in the second; HEAD drains in both. **Arm 1 ran, and base drains
  identically** — prefill → 1 from starts of 2, 4 and 8, both optimizers, decode holding as control,
  measured in a throwaway detached worktree at base (coder,
  `plan__ta-anchor-ad5-attribution-settled-base-drains-identically`, 2026-08-08). Calibration for
  cross-run comparison: the base pipeline suite is **308** specs against HEAD's **386**.
- **Arm 2 is still unrun — and that run's own refinement does not substitute for it.** The base run
  additionally carried a **non-zero stale prefill `TotalDemand`**, offered as a form of the inherited
  claim stronger than the argument needed. It is not: `TotalDemand` (`domain/analyzer.go:82`) and
  `RequiredCapacity` (`:88`) are **distinct fields of the same `RoleCapacity` struct**, and the
  dispatch reads only the latter — `pickerState[i][role] = rc.RequiredCapacity` in `initRoleState`,
  byte-identical at base and HEAD. Nor could the one derive the other in that fixture: the sole code
  computing per-role `RequiredCapacity` **from** per-role `TotalDemand` is `applyUniversalThreshold`
  (`saturation/engine_v2.go:496-512`, `rc.TotalDemand/scaleUp - rc.TotalAnticipatedSupply`), which
  lives in the **saturation engine** and so never runs on a hand-built `AnalyzerResult` handed
  straight to an optimizer. That variant therefore sharpens route (B)'s anchor-sourced-demand point
  and leaves route (A)'s dispatch untouched. **So the executed run *is* arm 1, on two independent
  grounds** — the fixture presented the dispatch with all-zero `RC` by construction, and by
  entailment: the dispatch is a strict either/or (`cost_aware_optimizer.go:61-65` —
  `anyRoleNeedsScaleUp` ⇒ `allocateForModelPaired`, `else` ⇒ `scaleDownRoleIterated`), so reaching the
  drain through route (A) requires `anyRoleNeedsScaleUp == false`, i.e. **no** entry-role pair holding
  `RequiredCapacity > 0` anywhere in the stale snapshot. A base run that drains **with** a positive
  `RC` present would falsify the dispatch-mask account and restore "unconditionally inherited"; that
  run has not happened. (Instrument: the reviewer's, Finding 67.)
- **Not instrumented either way:** which internal path each optimizer took (the table shows two
  *optimizers* reproducing it, not two *gates*) — **and the floor at 1 does not supply it**, per the
  rejected inference above — and the second observability site
  (`cost_aware_optimizer.go:350-367`, which still reads `anchor.RoleCapacities[role]` wholesale for
  `decision.RequiredCapacity`, so a sizing-only fix leaves the operator gauge at 0).

**The falsifier stands for the unconfirmed half.** Route (B)'s test is the same fixture with rescale
enabled and the group contended; it should be red today, **and red at base `075a208e` too** — that
second assertion is what the corrected provenance predicts, and it is the cheap way to check this
author's attribution rather than take it. **If route (B) is green at HEAD, that half of this section is
wrong and should be struck.**

[↑ TOC](#toc)

## Residual band after the rulings {#residual}

After [`AD2`](#ad2) and [`AD3`](#ad3), the partial-from-zero problem reduces to **one cell**:

> a **non-disaggregated** model, configured **`[TA]`-only**, with a **genuinely new** variant at zero
> replicas (no retained price to recover), under load **below the queueing threshold**.

Everything else is covered:

| case | covered by | Rev 2 status |
|---|---|---|
| P/D, any config | [`AD2`](#ad2) — sat is mandatory and is role-complete; the `satEnabled` (b)-fallback supplies the cold variant's PRC and role | **conditional, and weaker than Rev 2 said** — protective only while TA's vote `Score` ≤ sat's ([`AD4`](#ad4)) **and only while sat is live**: a stale or absent sat leaves prefill exposed to the [`AD8`](#ad8) teardown, and route (A) there needs no outage at all |
| prefill from zero, any config | [`AD3`](#ad3) — abstaining is the correct action | holds |
| non-disaggregated, `[sat]` or `[sat,TA]` | sat's pricing ladder — its own stored `CapacityRecord` needs no pods | **VERIFIED** (was soft in Rev 1) — see below |
| non-disaggregated, `[TA]`-only, **long-idle** variant | the retention exception in [`AD6`](#ad6), if scoped | holds |
| the residual cell above | `N8` (abstain, don't borrow) governs the decision; the reactive `scalefromzero` engine is the backstop | holds |

**The sat-pricing-ladder row is now verified, not assumed.** Rev 1 flagged two unverified
preconditions on saturation's tier-2 rung. Both were read on `a9afb740` and **both are benign — they
enable the rung rather than gate it**:

- the `scaleTarget == nil` skip (`saturation/engine_v2.go:41-44`) drops a VA whose **workload
  accessor is missing entirely**, not one at zero replicas — a zero-replica Deployment/LWS still
  yields an accessor, and `LoadFromScaleTarget` (`:50`) is spec-parsed;
- `analyzers/saturation_v2/capacity_store.go:126-128` is a **fallback filler, not a gate**:
  `if record.EffectiveCapacity <= 0 && params.EffectiveMaxBatchedTokens > 0 { record.EffectiveCapacity
  = params.EffectiveMaxBatchedTokens }`, commented *"so that brand-new variants with no live data or
  compatible siblings can still be considered for scale-up."*

One sharpening on that second bullet, from the reviewer's independent read and worth keeping because
it removes a conjunct rather than adding one: on a **freshly constructed** record
`EffectiveCapacity` is always `0`, so for the from-zero case the two-term condition reduces to
**`EffectiveMaxBatchedTokens > 0` alone**. The rung's entire precondition is therefore that single
engine-args field.

Which is also the residual risk, and it is narrow: if the engine args expose no
`EffectiveMaxBatchedTokens` (value `0`), `EffectiveCapacity` stays `0` and the rung yields nothing.
That is an engine-args gap, not a from-zero design gap.

**The backstop is real but narrower than "covered".** The reactive `scalefromzero` engine is per-VA
(not model-gated) and wakes on the EPP flow-control queue metric matched on `modelID` — so it does
reach a single cold variant of a warm model. But it is reactive **under queueing**: the uncovered band
is load that matters and has not queued yet. That band is the honest residual, and `N8` is the right
answer within it — an analyzer that cannot price a variant should abstain, not guess.

[↑ TOC](#toc)

## Verification checklist — for the planner and reviewer {#checklist}

Dean, 2026-08-08: *"verify all 6 points we had set before -- at least document them for the planner to
verify and to checklist."* Every claim in this addendum, its Rev 2 verdict, and the command that
re-checks it. Run from the `ta-anchor-dynamic-refresh` worktree; replace `a9afb740` with the current
tip to detect drift.

| # | Claim | Rev 2 verdict on `a9afb740` | Re-verify with |
|---|---|---|---|
| `AD1` | TA's prefill demand is structurally 0; prefill **key present**, value 0 | **HOLDS** — chain re-cited, step 6 operator changed | `git grep -n RolePrefill a9afb740 -- internal/engines/analyzers/throughput/analyzer.go` (expect exactly `:364`, `:928`); then read `aggregateRoleCapacities` + `initRoleState` |
| `AD2` | `[TA]`-only unsupported on P/D; unenforceable at startup | **HOLDS** — ruling; enforcement reason re-cited | `git show a9afb740:internal/domain/saturation_analyzer.go \| sed -n '387,410p'` (Role at `:402-403`) |
| `AD3` | Scoped to `decode`/`both` | **CONCLUSION HOLDS; RATIONALE REPLACED** — "all mechanisms equally inert" is **false**: pricing removes the unpriced-skip. Valid only for a **zero-replica** prefill variant; a live one is already priced | `git show a9afb740:internal/engines/pipeline/cost_aware_optimizer.go \| sed -n '139,141p'` (the skip) + `throughput/analyzer.go:398-408` (TA prices live prefill) |
| `AD4` | TA cannot veto sat | **CHANGED** — verdict holds, argument replaced; **new**: dilution when `Score_TA > Score_sat`; **and** "no veto" is not benign ([`AD8`](#ad8)) | read `combineVotes` `:456-494`, `voteScore` `:512-517`, `votesFromPickerState` `:522-534`, `roleSpareVetoed` `:736-771` |
| `AD5` | Prefill gets no fair-share GPU budget when TA is sole voter | **HOLDS** — mechanism restated (ballot combine, not anchor read); **three sub-regimes** distinguished, only (i) is `AD5` | read `roleDemandGPUs` `rescale.go:579-603`; confirm `s := votingResults(...)` at `:360` and `:518`; `variantsOnType` `:606-614` |
| `AD8` | TA's prefill spare **authorizes draining the role**; two routes, both **inherited from base**, with route (A) made **deterministic** by `VG-up` | **NEW in Rev 3 — corrects Rev 1/Rev 2's "harmless".** Route (A) **CONFIRMED by execution** (prefill → 1 from 2/4/8, both optimizers, decode holds); route (B) read-only | `grep -n "scaleDownVariantSet(" internal/engines/pipeline/*.go` (expect exactly 2 callers: `cost_aware_optimizer.go:496`, `rescale.go:415`); then `cost_aware_optimizer.go:488,498` vs `rescale.go:415-421`; `engine_v2.go:509`; `analyzer_helpers.go:385`; the `#1237` clamp at `cost_aware_optimizer.go:157-160`. **Provenance:** `git show 075a208e:…/rescale.go \| grep -n "func roleDemandGPUs"` (no `s` param ⇒ base read the anchor) + `075a208e:analyzer_helpers.go:138,147` (base binder already `Live`-gated) + `075a208e:analyzer_helpers.go:237` (base `votingResults` = `Enabled` only ⇒ route (A)'s mask was real). **Base run:** arm 1 (all-zero stale `RC`) executed 2026-08-08 — base drains identically at 2/4/8, both optimizers; **arm 2 (any one role's `RequiredCapacity` positive) is the discriminating test and is unrun.** Suites differ: base **308** specs, HEAD **386** |
| `AD5`b | `VG-up` status | **LANDED** (Rev 1 said pending) | `git show a9afb740:internal/engines/pipeline/analyzer_helpers.go \| sed -n '335p'` → `if e.Enabled && e.Live` |
| `AD6` | Sibling pricing not cheap; 2-field prerequisite | **HOLDS** — but (a) re-costed: identity already derived pod-free | `git show a9afb740:internal/engines/saturation/engine_v2.go \| sed -n '41,50p'` |
| `AD7` | `N5` root cause is sourcing, not arithmetic | **HOLDS** | `git show a9afb740:internal/domain/saturation_analyzer.go \| sed -n '58,59p'` |
| res-1 | sat tier-2 fires for a zero-replica variant | **VERIFIED** (was flagged unverified in Rev 1) | `git show a9afb740:internal/engines/analyzers/saturation_v2/capacity_store.go \| sed -n '120,131p'` |
| res-2 | `N7` fail-safe on scale-down; collectors disagree on missing keys | **CORRECTED** — the disposition survives but the routing was wrong. A **missing** role key **abstains**; it never vetoes: `roleSpareVetoed:766` and `needsScaleDownForRole:903-905` both `continue` on a map-miss, and only `votesFromRoleSpare:611` reads a miss as `0.0` (magnitude, not veto). And a **present** `0.0` is not absolute either — score-conditional per `:796-799` | compare `votesFromTotalDemand:545-569` / `votesFromPickerState:522-534` / `votesFromRoleSpare:597-620` participation rules; then read `roleSpareVetoed:736-771` and `needsScaleDownForRole:890-910` for the `continue`-on-miss, and `safeRemovalReplicasForRole:790-812` for the score-conditionality doc |

**Three items in this table are not verifications but requests**, and all three are the planner's:
[`AD5`](#ad5)'s scope decision; whether [`AD4`](#ad4)'s dilution finding warrants its own disposition
line rather than living only here; and [`AD8`](#ad8)'s disposition, which is the newest and the most
consequential — it is the one item here that is **read but not executed**, so the falsifier fixture
in `AD8` is the checklist entry that actually settles it.

**One caution on running this table.** Rows `AD8` and `AD5` cite `cost_aware_optimizer.go` and
`rescale.go` line numbers, and PR-2's remaining commits still touch both files. If a `sed -n` range
lands on unrelated code, the tip has moved — re-locate by symbol (`grep -n "func <name>"`) rather
than trusting the range, and treat the divergence as a signal to re-verify the claim, not as a
transcription slip.

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
3. **Rev 1's entire evidence baseline — `Main @ a6b39809`.** Withdrawn 2026-08-08. Dean: *"we are
   deep into coding PR-2, yet you rely on Main?"* The addendum's subject is PR-2's end state, and PR-2
   rewrites the combine operators the analysis reasons about, so `Main` was the wrong tree even though
   every Rev 1 citation was internally correct for it. Two claims were materially affected —
   [`AD4`](#ad4)'s identity-element argument (replaced) and [`AD5`](#ad5)'s mechanism sentence
   (restated) — and one status was stale ([`VG-up`](#ad5) had already landed). The rest re-verified
   unchanged. The [§ currency](#currency) citation rule exists to prevent a recurrence: line numbers
   only for lines actually read on the named tree.

4. **"TA's whole-fleet prefill `SpareCapacity` is harmless, because TA cannot act alone."** Rev 1 and
   Rev 2 both wrote it; it is the most consequential error this addendum has made, and
   [`AD8`](#ad8) exists to replace it. The mistake was categorial, not arithmetic: `SpareCapacity` was
   read as an *observation* ("this much looks idle") when it is an **authorization** ("this much may be
   removed"). Everything else followed — once the quantity is an authorization, "TA cannot act alone"
   stops being reassuring, because the scale-down path needs no second actor to *grant* removal, only
   the absence of one to *refuse* it ([`AD4`](#ad4)).
5. **`N7` routed as a veto.** Rev 2's [§ checklist](#checklist) `res-2` verdict described a missing role
   key as fail-safe *because it vetoes*. It abstains: `roleSpareVetoed:766` and
   `needsScaleDownForRole:903-905` both `continue` on a map-miss, and only `votesFromRoleSpare:611`
   reads a miss as `0.0` — a magnitude, not a refusal. The disposition survives, but the veto framing
   made `AD8`'s teardown look impossible, which is precisely why it took a separate section to find.
6. **Route (B)'s *"newly unmasked by `VG-up`"* attribution.** Written in Rev 3's own first draft of
   [`AD8`](#ad8), and arrived at independently in the reviewer's Finding 66 — so two readers reached it
   from the same wrong premise, that `demByRole` came from the ballot at base. It did not: base
   `roleDemandGPUs` took no ballot parameter and read demand **off the anchor**
   (`075a208e:rescale.go:545`), and base's binder gate was already `Live`-gated, so base already bound
   TA and already read prefill `TotalDemand = 0`. Withdrawn on the planner's challenge after this author
   re-read base rather than accepting either side; the reviewer has since conceded it too (Finding 67).
   **The lesson is the one the [§ currency](#currency) rule was written for:** a "PR-2 unmasked this"
   claim is a *base-versus-HEAD* claim, and it is only as good as an actual read of base.

**Formerly-unverified items, now closed.** Rev 1 flagged saturation's two tier-2 preconditions as
asserted-by-others rather than verified by this author. Both are now read and verified benign — see
[§ residual](#residual). Nothing in this addendum is now carried on someone else's unchecked claim.

**Claims from peers that this addendum declines rather than withdraws** — recorded so disagreement is
visible rather than silently resolved. **One of the two has since closed:** the floor at 1 as route
instrumentation (Finding 67) was rejected in [`AD8`](#ad8) on the clamp's position relative to the
callback, with both docstrings agreeing, and **its author retracted it on the same grounds** in
Finding 68 (`a798dc87`), adding that the clamp is present at base too. **One remains open:** route (A)
as *unconditionally* inherited (Finding 66 and the planner's handoff — narrowed in `AD8` to the case
where the dead analyzer held no positive `RC` on any role). It stays open on evidence, not on
opinion: the base run that has been executed is the all-zero-`RC` arm, which both sides predict
drains, and the discriminating arm is still unrun. Both are cited at the point of disagreement, not
only here.

> **A pattern worth naming, since it has now produced four corrections in this section alone.** Every
> one of them — the "harmless" reading, `reclaimRole` as newly-unmasked, the floor as instrumentation,
> and the `TotalDemand` refinement — was a claim about a *helper's* behavior inferred from its
> *caller's* description, or about a field inferred from a sibling field's name. In each case the
> disconfirming evidence was one `git show` away, and in two of them it was written in the docstring of
> the very function being reasoned about. The addendum's rule follows: **for any claim of the form "X
> does not do Y", read X**, and prefer a cheap executed arm over a confident reading.

[↑ TOC](#toc)

## Disposition summary {#disposition}

| # | Item | Status | Owner of what remains |
|---|---|---|---|
| `AD1` | TA is not role-complete for P/D; prefill demand is structurally 0 | **Verified fact** (re-verified on `a9afb740`) | — |
| `AD2` | `[TA]`-only unsupported on P/D; both-by-default; documented, unenforced | **DECIDED (Dean)** | doc placement — planner; note the conditional in `AD4` |
| `AD3` | From-zero PRC work scoped to `decode`/`both` only | **DECIDED (Dean)** — follows from `AD1` | — |
| `AD4` | TA cannot veto sat — **but can dilute it when scored above sat** | **Verified fact; argument replaced in Rev 2** | whether the dilution finding gets its own line — planner |
| `AD5` | Binding-path override; hold the role when the binder is not role-complete | **OPEN** | PR-2 scope — planner; priority — Dean. ⚠️ A fix here does **not** fix [`AD8`](#ad8) route (A): this predicate acts on *demand*, route (A) runs off `RoleSpare` |
| `AD8` | TA's prefill `SpareCapacity` **authorizes draining the role** — prefill collapses to 1 from any height while decode scales normally | **OPEN — the most consequential item here.** Route (A) **CONFIRMED by execution at HEAD *and* at base** (arm 1); route (B) PLAUSIBLE by reading. Pre-existing defect, *conditionally* so — the discriminating arm 2 is unrun, so the qualifier stays | PR-2 scope — planner; priority — Dean. Two sites if fixed (sizing + `cost_aware_optimizer.go:350-367` observability); route (A) needs a `RoleSpare`-side predicate that does not exist yet. **Cheapest next step is arm 2, one field in an existing fixture** |
| `AD6` | Sibling pricing rejected; retention exception retained; shared 2-field prerequisite | **DECIDED (Dean) to skip the lookup**; retention **OPEN** | retention scoping — planner |
| `AD7` | `N5` sat `Cost = 0` at zero replicas | **DECIDED (Dean): fix** | sizing/placement — planner |
| res-1 | sat tier-2 rung fires without pods | **VERIFIED in Rev 2** (was unverified) | — |
| — | fair-share `ceil` → `floor` | **NOT IN THIS ADDENDUM** — held | separate discussion (Dean) |

**Unchanged by this addendum:** the parent's `FZ-admission` decision (`Reason`-tagged `PRC = 1`
sentinel + one-replica target ceiling at the three grant sites), `(D-a)`'s deferral, the unit
contract, the combine rule, and the anchor contract. This addendum narrows the *domain* of the
from-zero pricing question; it does not reopen the mechanism chosen for it.

⚠️ **One thing "unchanged" must not be read to mean.** `(D-a)`'s deferral is unchanged as a *decision*,
but it is **not a protection** for a live prefill role. The `PerReplicaCapacity <= 0` skip
(`cost_aware_optimizer.go:139-141`) only declines the removal of a variant the binder **cannot price**
— i.e. one at zero replicas. TA prices a *running* prefill variant (`throughput/analyzer.go:398-408`,
outside the `:364` role guard), so the skip is already not firing there, and [`AD8`](#ad8) route (A)
proceeds. Reading the deferral as what keeps `AD5`/`AD8` benign inverts the actual behaviour on a live
P/D model: the from-zero case is the one the skip covers, and it is the only one.

[↑ TOC](#toc)
