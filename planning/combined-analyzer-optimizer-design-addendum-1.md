# Addendum 1 — analyzer role completeness and partial scale-from-zero — Type 1 Design

> **Reading protocol:** Read the TOC first. Fetch only the sections you need via
> `Read <file> offset:<start> limit:<end-start+1>`. Never read the whole file up front.

**Type:** 1 (design) · **addendum — additive only** · **Status: FINAL for the analysis;
[`AD8`](#ad8) decided by Dean 2026-08-08 (repair the pricing), [`AD5`](#ad5) still open, and what
remains on each is named** ([§ disposition](#disposition)).

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

- [Why this addendum exists {#why}](#why-this-addendum-exists-why) L78:97
- [AD1 — the ThroughputAnalyzer is not a P/D-complete analyzer {#ad1}](#ad1--the-throughputanalyzer-is-not-a-pd-complete-analyzer-ad1) L98:173
- [AD2 — ruling: `[TA]`-only is unsupported on P/D models; both analyzers is the default {#ad2}](#ad2--ruling-ta-only-is-unsupported-on-pd-models-both-analyzers-is-the-default-ad2) L174:201
- [AD3 — the from-zero PRC work is scoped to `decode` and `both` roles only {#ad3}](#ad3--the-from-zero-prc-work-is-scoped-to-decode-and-both-roles-only-ad3) L202:255
- [AD4 — TA cannot veto saturation, but under PR-2 it can dilute it {#ad4}](#ad4--ta-cannot-veto-saturation-but-under-pr-2-it-can-dilute-it-ad4) L256:336
- [AD5 — the one real override is the binding path, not voting — OPEN {#ad5}](#ad5--the-one-real-override-is-the-binding-path-not-voting--open-ad5) L337:443
- [AD6 — rejected: TA cross-variant sibling pricing. Retained: the retention exception {#ad6}](#ad6--rejected-ta-cross-variant-sibling-pricing-retained-the-retention-exception-ad6) L444:493
- [AD7 — `N5` (saturation `Cost = 0` at zero replicas) is to be fixed {#ad7}](#ad7--n5-saturation-cost--0-at-zero-replicas-is-to-be-fixed-ad7) L494:516
- [AD8 — the prefill role is not merely starved: it is frozen or drained — DECIDED: repair the pricing {#ad8}](#ad8--the-prefill-role-is-not-merely-starved-it-is-frozen-or-drained--decided-repair-the-pricing-ad8) L517:1019
  - [Interim operator note — the highlights, until the pricing repair lands {#ad8-operator-note}](#interim-operator-note--the-highlights-until-the-pricing-repair-lands-ad8-operator-note) L985:1019
- [Residual band after the rulings {#residual}](#residual-band-after-the-rulings-residual) L1020:1066
- [Verification checklist — for the planner and reviewer {#checklist}](#verification-checklist--for-the-planner-and-reviewer-checklist) L1067:1101
- [Withdrawn framings {#withdrawn}](#withdrawn-framings-withdrawn) L1102:1239
- [Disposition summary {#disposition}](#disposition-summary-disposition) L1240:1268

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

## AD8 — the prefill role is not merely starved: it is frozen or drained — DECIDED: repair the pricing {#ad8}

⚠️ **This section is a correction of this addendum, not of anyone else's document.** Rev 1 and Rev 2
both wrote that TA's whole-fleet prefill spare is *"harmless, because TA cannot act alone"*
([`AD4`](#ad4)). **That sentence is wrong, and it is the one error in this addendum whose consequence
is a running role losing replicas — or a newly-deployed one never being given any.**
`SpareCapacity` is not an inert observation — it is the **authorization to remove**, and TA
authorizes removing all of it. The structurally-zero demand behind that authorization is the same
fact that leaves a *rising* prefill role unsized, which is why one cause produces two opposite
symptoms (the two regimes below).

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
| **(B)** `reclaimRole` → `scaleDownVariantSet` (`rescale.go:404-427`, callback at `:415-421`) | **neither** — the callback is a pure GPU delta | rescale enabled for the scope **and** the group contended | **inherited from base `075a208e`** — `VG-up` cannot reach it | **CONFIRMED by execution — base ≡ HEAD, 12 configurations** |

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
  single positive `RequiredCapacity` **anywhere on the pruned entry** diverted the whole model to
  scale-up, with prefill never consulted. Route (A) is therefore inherited **only when the pruned
  entry carries no positive `RC` on any role** — and that is the *narrower* branch, not the wider
  one: a non-informative saturation result with queued demand carries positive `RC` on **every** role
  by construction ([above](#ad8-third-row)), so the ordinary shape of this state is the one where PR-2
  converts *"scales up on unusable data"* into *"sheds prefill to one replica."* An unconditional
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

**Which configurations this actually reaches — the bound, because "`[TA]`-only" is both too narrow and
too alarming.** The deciding line is `votesFromTotalDemand` (`analyzer_helpers.go:545-570`), which
distinguishes **abstaining** from **voting zero**: a missing role key abstains (`if !ok { continue }`,
`:552-555`) and an unpriceable variant abstains (`prc <= 0`, `:558-563`) — but **a role key that is
present carrying `TotalDemand == 0` votes a hard 0** (`:566`). TA always *creates* its prefill key and
then excludes prefill from filling it ([`AD1`](#ad1)), so TA votes zero on prefill rather than staying
silent. What saves the common case is the reduction: `combineVotes(…, up: true)` takes the **max**
(`:461-470`), so under the shipped **uniform** scores a live saturation's positive prefill vote wins and
TA's zero is inert. Three cells, therefore, and only two of them matter:

| configuration | prefill demand | drains? |
|---|---|---|
| `[sat, TA]`, both live, uniform scores (**the recommended default**) | sat's vote wins the max | **no — TA's zero is inert** |
| `[TA]`-only on P/D | TA is the sole voter; structural 0 | **yes** — already an unsupported config ([`AD2`](#ad2)) |
| `[sat, TA]`, sat non-live | `VG-up` prunes sat; TA would survive on its **own** persisted supply — see below | **no — closed in Rev 6** ([§ withdrawn](#withdrawn) item 8). Neither a cold start nor a sustained metrics gap gets here: saturation's capacity store is refilled from the scale targets every cycle and kept 7 days, while TA's persisted supply needs observed live metrics and expires in 1 hour, so **TA warm ⟹ sat warm**. Residual is a fresh process with every scale-target fetch failing — where TA is cold too |
| `[sat, TA]`, both live, **TA scored above sat** | dominance correction `(e−v_i)(s_i−s_e)+` pulls toward TA's 0 | **partially** — latent; shipped scores are uniform |

<a id="ad8-third-row"></a>
**The third row is reachable, and the separation is in the capacity store — not in the metrics.** An
earlier revision of this paragraph asserted the opposite twice, and both times for a bad reason: first
by inventing an EPP-side fault that took saturation non-live while TA stayed live, then — after that was
refuted — by concluding the row was *unreachable* because both analyzers consume the same queries. The
refutation was correct about the metrics and the conclusion drawn from it was still wrong. Saturation's
informativeness does not depend only on metrics; **it depends on a store TA does not read.**

The two failure conditions are different objects:

- **Saturation** needs, per variant, either live per-replica metrics or a capacity record. With
  `len(replicas) == 0` it falls through `capacityStore.Get` and then `lookupCompatibleCapacity`, and if
  both miss it stamps `satReasonNoData` (`saturation_v2/analyzer.go:389`, `:421-431`). If **every**
  variant lands there, `ResultIsInformative` is false (`analyzer_helpers.go:53-63`).

  ⚠️ **Non-informative is not the same thing as non-live — Dean's correction, 2026-08-08, and the code
  agrees.** `nr.Live = ok && now.Sub(lastGood) <= threshold` with `threshold = analyzerLivenessStaleCycles
  × interval` = 3 × 30 s = **90 s** by default (`saturation/engine_v2.go:233`, `:245-247`, const at
  `:84`). So there are two distinct routes, and only one of them waits:
  - **`ok == false` — never informative for this model ⇒ `Live = false` on the first cycle, no window at
    all.** No entry was ever written to `lastGoodAnalysis[modelKey]["saturation"]`, so the timestamp lookup
    misses.

    ⚠️ **An earlier revision offered "a controller restart or a fresh model against a cold capacity store"
    as the way in. That is wrong; the reviewer's Finding 74 is the correction**
    ([§ withdrawn](#withdrawn) item 8). The capacity store is not state that either survives a restart or
    doesn't — it is **re-derived from the scale targets at step 1 of every `RunAnalysis`, before `Analyze`
    is called** (`saturation/engine_v2.go:38-53`), and that path cannot yield a zero capacity:
    `LoadFromScaleTarget` sets `record.EffectiveCapacity = params.EffectiveMaxBatchedTokens` whenever the
    former is unset (`capacity_store.go:126-128`), and `resolveEffectiveMaxBatchedTokens` has no
    zero-yielding branch — explicit flag → that value, chunked V1 → 8192, chunked V0 → 2048, unchunked
    `MaxModelLen > 2048` → `MaxModelLen`, else an unconditional 2048 (`deployment_parser.go:281-303`) —
    and it is reached on **every** return path of **both** engine parsers (`deployment_parser.go:76,82,110`
    and `sglang_parser.go:48,54,65`, dispatched at `sglang_parser.go:14-19`). So a brand-new variant lands
    in the store branch with `Reason = "P0-store"` (`saturation_v2/analyzer.go:421-429`, `types.go:28`),
    and because `ResultIsInformative` returns true on the **first** non-sentinel variant anywhere in the
    result (`analyzer_helpers.go:53-63`), **one** priced variant makes the whole result informative. That
    rides on the *label*, not the number — the branch stamps `P0-store` regardless of what
    `estimateStoredCapacity` returns — so it is stronger than a capacity argument. What remains of this
    route is **every** variant's scale target missing or unresolvable (`scaleTarget == nil` skips
    pre-population, `engine_v2.go:41-49`; `lookupCompatibleCapacity` then also fails, since it needs that
    same record's `EngineParams`) — degenerate, and a louder problem in its own right than the starvation
    it would enable.
  - **`ok == true` — previously informative ⇒ still `Live` for 90 s**, then non-live if the gap persists.
    A single non-informative cycle changes nothing.

  The interim window matters in its own right: for those 90 s saturation is **non-informative but
  `Live`**, so `VG-up` does *not* prune it and its positive `RC` still counts as a live vote. The drain
  needs the entry pruned — and with the cold-start route closed, that means a gap sustained past 90 s
  **plus** the same degenerate precondition, since a variant whose scale target still resolves is priced
  from the store on every cycle and never stamps `NoData` at all.
- **TA**, handed the *same* empty metric set, does not go quiet. For every variant absent from
  `byVariant` it emits a PRC-only capacity from its own persisted `lastPerReplicaSupply`, stamped
  `Reason: itlReasonScaleFromZero` (`throughput/analyzer.go:427-440`) — which is neither `NoData` nor
  `Error`, so TA is **informative** and stays `Live`.

⚠️ **The asymmetry runs the other way, and that is what closes this cell** ([§ withdrawn](#withdrawn)
item 8). Saturation does not have to find its record the hard way: the store is refilled from the scale
targets every cycle and retained for **7 days** (`CapacityEvictionTimeout`, `saturation_v2/constants.go:19`).
TA's `lastPerReplicaSupply` is warmed **only** by observed live replica metrics and is evicted after **1
hour** of non-observation (`2 × DefaultObservationMaxAge`, `throughput/analyzer.go:157-162`,
`throughput/constants.go:24`). Both memories live in the same process, so **TA warm ⟹ saturation warm**: TA
can only hold a persisted supply for a variant it saw live, and that same cycle's metrics wrote saturation a
`learnedFromLive` record (`saturation_v2/analyzer.go:206`) which outlives TA's by 168×. There is no window
in which TA is the surviving voter *because saturation went quiet*.

**Demand does not go to zero with the metrics, which is what makes the pruned entry's `RC` positive.**
Per-variant demand accumulates only inside the live-replica branch, so every `NoData` variant reports
zero — but role demand has a **second source**: `estimateSchedulerQueueDemand`
(`saturation_v2/analyzer.go:750-795`) derives `inputTokens` from `sq.QueueBytes / BytesPerToken`, which
reads the scheduler queue and **not** `replicaMetrics`, and `aggregateByRole:485-491` adds it per role —
prefill `inputTokens`, decode `inputTokens + outputTokens`. With no replica metrics at all, `avgOutput`
and `avgHitRate` are zero and `QueueBytes` alone still yields **both roles positive**. The reviewer's
Finding 71 makes the same point structurally and more strongly: `applyUniversalThreshold`
(`saturation/engine_v2.go:476-513`) contains no reference to `VariantCapacities` anywhere, so
non-informativeness and positive per-role `RC` are orthogonal **by construction** — and every role is
positive, not one (coder's measurement: both roles `470.588`; its earlier fixture seeded decode only and
it flagged that against its own instrument).

**End to end, then — and this is where Rev 5 over-claimed.** The *shape* of the state is: saturation sees
every variant as no-data, is pruned by `VG-up` while still carrying positive `RC` on **both** roles, and TA —
live, on persisted supply — becomes the sole voter and the binder, so the anchor is **non-nil** and the
`anchor == nil` hold at `cost_aware_optimizer.go:48-51` never fires. Prefill's TA demand is structurally
zero ([`AD2`](#ad2)).

⚠️ **Both entry paths Rev 5 offered are closed** ([§ withdrawn](#withdrawn) item 8). The **cold start** is
closed by the store pre-population — a first deploy is priced `P0-store` on cycle one. The **sustained
metrics gap** is closed by the same store plus its 7-day retention — a scrape failure does not remove the
record that keeps saturation informative. What remains is a **fresh controller process in which every
variant's scale-target fetch also fails** (`saturation/engine.go:1500-1507` `continue`s on error, writing no
store entry) — and in that state TA is cold too, so it cannot be the surviving voter. **In `[sat, TA]` this
cell is not reachable by any operational fault we can name.**

What that does *not* close, and why the disposition below is unchanged: **`[TA]`-only needs no saturation
death at all** — saturation is not on the ballot, so `AD8` is reachable there directly with no liveness
argument. That is exactly the configuration [`AD2`](#ad2)'s guard addresses. The two regimes measured at
HEAD are likewise untouched: the coder's fixtures construct the ballot directly and bypass both memories.

Two refinements on that chain, both from the reviewer's independent verification (Finding 73) and both
narrowing it rather than widening it:

- **The route needs queue *bytes* specifically.** `QueueSize > 0` with `QueueBytes == 0` and no replica
  metrics admits past the guard but produces an all-zero demand (`tokensFromBytes = 0`, and
  `tokensFromCount = QueueSize × 0` because `computeModelWorkloadAverages` returns zeros), so the route
  does not open. State the precondition that narrowly: **`QueueBytes > 0`**.
- **The load-bearing line is a fall-through, not a lookup.** The `satReasonNoData` branch does **not**
  `continue` — it falls through to the append (`saturation_v2/analyzer.go:430-432`, then `:441-453`), so a
  variant nobody can price still contributes a `VariantCapacity` carrying its `Role`, `ReplicaCount` and
  `Reason`. Had it skipped, `activeRoles` would be empty, `hasDisaggregation` false, `aggregateByRole`
  would return nil at `:479-481`, and the whole route would close. Any regression fixture must preserve
  that fall-through, and any future "skip unpriceable variants" tidy-up would silently close the route —
  which is worth knowing in both directions.

**What happens next splits in two, and the split is the dispatch — measured, not reasoned** (coder,
2026-08-08, both optimizers, three heights, base `075a208e` vs HEAD `a9afb740`). `anyRoleNeedsScaleUp`
reads the **pruned** ballot, so what decides is whether the surviving live analyzer still wants decode
capacity:

- **(i) decode `RC > 0` — rising load.** The dispatch is a **per-model branch on
  an any-role predicate** (`anyRoleNeedsScaleUp` is a global OR over roles, `analyzer_helpers.go:709-718`),
  and the arms are mutually exclusive (`cost_aware_optimizer.go:62-67`), so one role's positive `RC`
  captures the whole model's dispatch: it takes the scale-up arm and `scaleDownRoleIterated` is **never
  entered**. Prefill gets nothing because its `RC` is 0, so it **freezes at its current count** — and where
  that count is **0** (a variant already at zero replicas; measured, `cur ∈ {0,1,2}`) decode scales to 4
  while prefill stays at 0, a P/D model with no prefill replicas at all. The scale-to-zero enforcer does not rescue it, and cannot: its
  minimum-replica preservation returns early on the model *total* (`enforcer.go:138-147`), which is 4 — and
  even at total zero the fallback that would set one variant to 1 selects by `Cost` with a `VariantName`
  tie-break and **contains no reference to `Role` at all** (`:150-174`), so it may well rescue a *decode*
  variant and leave prefill at 0. **Nothing in the pipeline establishes a per-role replica floor**, so
  there is no brake on this regime, accidental or otherwise.
- **(ii) decode `RC == 0` with spare — steady or falling load.** Dispatch takes scale-down. **Prefill
  sheds to one replica; decode is untouched.** The counts are real — `CurrentReplicas` comes from the
  scale target, not from the missing metrics — so a prefill tier running 8 pods loses 7 in a single
  reconcile *because its metrics disappeared*. The single survivor is the cheapest-at-1 accident, the only
  brake anywhere in `AD8`.

Regime (i) is the ordinary one and it is the one this addendum previously did not describe: *"prefill's
target collapses to 1"* is regime (ii) only. At base the pruned entry stayed on the ballot and its
positive `RC` bought prefill exactly **one** replica per cycle, so base is differently wrong rather than
right (§ *route (A), arm 2*); the per-cycle delta HEAD-vs-base is one prefill replica.

**Dean's mitigation — necessary, and it does not close this row.** His guard (2026-08-08): **if TA is
the only enabled analyzer on a disaggregated model, do nothing.** That is the right treatment for the
second row, and it is the stronger form of [`AD2`](#ad2) — an enforced precondition rather than
documented guidance, so a misconfiguration produces a hold and a diagnostic instead of a silent prefill
teardown. It should ship. But the third row is a **compliant** `[sat, TA]` configuration, so the guard
cannot see it: the model has two analyzers enabled, and only one of them is live this cycle.

**Dean's ruling on the remainder (2026-08-08): repair the pricing; do not add a second gate.** A
liveness-aware variant of the guard — *if pruning leaves a disaggregated model with no analyzer that
prices a role, hold that role* — was put to him and **rejected**: *"PD not SAT — DONT."* The refusal
predicate stays keyed on the **enabled** set, exactly as scoped, and the third row is closed by
[`AD1`](#ad1)'s repair instead. That is coherent, and it is the better of the two: prefill's `RC` being
structurally zero is the single cause of **both** regimes above, so pricing it per-role removes the
freeze and the drain together, whereas a hold predicate would only have suppressed the drain — regime
(i) never enters the scale-down path at all, so no refusal placed there could have seen it.

**Consequences for the rest of this addendum.**

- [`AD2`](#ad2) is escalated from guidance to a **hard requirement on P/D models** — but note it is **no
  longer sufficient**. "`[TA]`-only is unsupported on P/D" was argued on a missed scale-up; the real
  exposure is a teardown, and route (A) needs no outage at all, so a P/D model configured `[TA]`-only
  sheds prefill in ordinary steady state. **And per the table above, obeying `AD2` does not close the
  hole:** a compliant `[sat, TA]` P/D model drains the moment saturation goes non-live. Guidance can
  only address the first row; the third needs code.
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
- **Route (B): CONFIRMED by execution, and inherited — no longer a reading.** A twelve-configuration
  sweep (hog demand 1000/2000/4000/8000 × A100 limit 8/10/12), with contention held identical between
  the two columns so that the **only** difference is TA's prefill `TotalDemand` (0 versus `sup`),
  produced **byte-identical rows at base `075a208e` and at HEAD `a9afb740`** (coder,
  `plan__ta-anchor-ad5-contended-path-also-inherited-review-2b-refuted`, 2026-08-08; base 308 specs +
  1 diagnostic, HEAD 386 + 1 + 1 pending, throwaway detached worktree, both diagnostics deleted, tip
  unmoved). Ten of the twelve rows exercise the role split; one is crushed by contention and is
  labelled as proving nothing; one does not diverge. **Prefill is pinned at 1 across every contention
  level and every budget**, while the control's prefill tracks the budget 3 → 4 → 2 → 3. So route
  (B)'s provenance is now execution-backed on both sides rather than the base-versus-HEAD source read
  Rev 4 recorded, and the two routes are attributed the same way by the same method.
- **A second, larger harm that route (B) exposes and no document predicted: the model loses total
  budget, not just prefill's share.** In nine of the twelve rows the `AD5` shape retains **fewer total
  GPUs** than the control at equal contention (5 versus 7 or 8). This is not an inter-role
  redistribution — the model's whole allocation shrinks. **The mechanism is upstream of `reclaimRole`,
  and it is not the one the measuring author named** (*"prefill's zero weight makes the whole model
  cheaper to reclaim from"*). Verified: `modelDemandGPUs` **sums `roleDemandGPUs` across roles**
  (`rescale.go:560-566`), so prefill's structural 0 understates the model's demand-in-GPUs by exactly
  prefill's share; `rescaleInputsForGroup` (`:509-557`) then feeds that one understated number into
  **both** `Demand` (the cross-model weight, `weight_i = Priority_i × Demand_i`) **and**
  `CapGPUs = demandGPUs` (`:540-546`); and `computeRescaleTargets` (`:70-108`) caps each model's
  headroom at `CapGPUs - FloorGPUs`. **The table itself says which of the two binds:** the `AD5` shape
  holds a constant 5 GPUs across limits 8, 10 and 12, whereas a weight-driven share would grow with
  the pool — constant-across-budgets is the signature of a **cap**, not of a share, and the control's
  total does track the budget. The arithmetic closes exactly: cap = decode's 4 GPUs + prefill's 0, so
  decode takes 4, prefill's role target is 0, and the `#1237` clamp floors prefill at 1 → **total 5**.
  Consequence for any fix: correcting only the per-role split leaves the model **hard-capped at its
  understated demand**, so `CapGPUs` is a second, independent repair site.
- **The measuring author's "still unexplained: why the floor is 1 and not 0" is answered**, and by this
  section rather than by a new run — the `#1237` cheapest-at-1 clamp in the shared primitive, present
  at base, applied after the callback returns (see the rejected inference and the Finding 68 note
  above). Their `floorByRole[prefill] == 0` reading is correct and not in tension with it: the role
  target genuinely is 0, and the clamp fires downstream of the target.
- **What route (B)'s sweep does *not* establish, stated as its author stated it:** that `reclaimRole`
  specifically did the shedding. The fixture reaches it through `Optimize` with rescale enabled and a
  contended pool — the only route named — but the call was not instrumented, so a scale-down elsewhere
  in the same pass is not excluded. The attribution conclusion does not depend on it (identical-at-base
  is identical whichever function ran), but a **per-function** claim in the Type 1 or in a fix would
  need an instrumented run that has not been done. The observability half is likewise unmeasured.
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
  `RequiredCapacity > 0` anywhere on the pruned entry. A base run that drains **with** a positive
  `RC` present would falsify the dispatch-mask account and restore "unconditionally inherited".
  **That run has now happened, and it confirmed the dispatch-mask account** — see the arm-2 result
  below. (Instrument: the reviewer's, Finding 67.)
- **Not instrumented either way:** which internal path each optimizer took (the table shows two
  *optimizers* reproducing it, not two *gates*) — **and the floor at 1 does not supply it**, per the
  rejected inference above — and the second observability site
  (`cost_aware_optimizer.go:350-367`, which still reads `anchor.RoleCapacities[role]` wholesale for
  `decision.RequiredCapacity`, so a sizing-only fix leaves the operator gauge at 0).

**Route (B)'s falsifier is discharged, and it discharged in this section's favor.** The test named here
in Rev 4 was: the same fixture with rescale enabled and the group contended, *"red today, **and red at
base `075a208e` too**"*, with the explicit forfeit **"if route (B) is green at HEAD, that half of this
section is wrong and should be struck."** It was run as specified, twelve configurations wide, and came
back red on both sides — so the forfeit does not trigger and the corrected provenance is confirmed by
the method it asked for rather than by this author's reading.

**Route (A)'s arm 2 has also been run, and it went the other way — against "inherited in full."** The
test was: at base, set the pruned entry's `RoleCapacities[<any role>].RequiredCapacity` positive, leave
`TotalDemand` alone. Result, at starting heights 2/4/8 and on both optimizers: with the dead entry's
`RC` **all zero**, base and HEAD tie (prefill → 1 on both) — inherited, as claimed. With **any** role's
`RC` positive, **base does not drain** (prefill preserved, model scaled *up*) **and HEAD does** (prefill
→ 1). So the dispatch-mask account is confirmed by execution: base's `Enabled`-only pruning left the
non-live entry's `RC` on the ballot, `anyRoleNeedsScaleUp`'s global OR (`analyzer_helpers.go:709-718`,
seeded from `rc.RequiredCapacity` at `:384`) diverted the model to the scale-up branch, and
`scaleDownRoleIterated` was never reached. `VG-up` removes that entry and the fall-through becomes
reachable.

⚠️ **Say "non-live", never "stale" — the carry-forward that word implies does not exist.** The
measuring author justified the positive-`RC` regime as the realistic one on the ground that *"an
analyzer entry that has just gone stale carries its last computed values."* It does not:
`updateLivenessAndSetLive` (`saturation/engine_v2.go:209-251`) sets `Live` **in place** from
`lastGoodAnalysis`, so `Live` is derived from *history* while `Result` is *this cycle's* output, and
nothing copies a prior cycle's `RoleCapacities` forward. In production `Live == false` therefore implies
this cycle's result is **non-informative** — which is exactly the state described
[above](#ad8-third-row), where the positive `RC` is computed fresh from queued demand against no usable
capacity. The distinction is not pedantic: a regression test that fakes a **stale timestamp** lands in
the all-zero regime and will not reproduce this at all. (Reviewer Finding 70 `e38e7d22`, accepted by the
measuring author.)

**Two things follow, and neither is a revert argument.** First, the measuring author's earlier summary
— *"`AD5` is inherited in full. No part of it is a PR-2 regression"* — is right for route (B) and for
route (A)'s **magnitude**, but wrong for route (A)'s **reachability** in the positive-`RC` regime; that
regime's reachability is PR-2's, and they retracted the sentence themselves. Second, base is not correct
there either: it preserved prefill by scaling the whole model up on figures no analyzer stood behind,
which is precisely the defect `VG-up` exists to remove. `VG-up` traded *acting on unusable data* for
*exposing a pre-existing prefill-pricing hole*. Both states are wrong; the pricing hole is byte-identical
at base.

⚠️ **Rev 6 withdraws the sentence that followed here** ([§ withdrawn](#withdrawn) item 8). It claimed the
positive-`RC` regime is "not confined to `[TA]`-only — it is where a compliant `[sat, TA]` P/D model lands on
a cold start or a sustained metrics gap." Per [the third row](#ad8-third-row) that cell is closed, so in
production terms the regime **is** effectively confined to `[TA]`-only. This is a **severity** correction, not
a re-opening of the disposition: Dean decided the pricing repair (2026-08-08) with the guard already
confirmed as covering only its own case, and both regimes remain measured at HEAD. What it does make live
again is the *placement* question — a defect confined to one configuration, which the guard makes hold rather
than act, is a weaker candidate for PR-2 than one reachable on a compliant two-analyzer model. Flagged for
Dean; not decided here.

<a id="ad8-operator-note"></a>
### Interim operator note — the highlights, until the pricing repair lands {#ad8-operator-note}

Dean asked for the highlights of what documenting this would say. It is **additive** to the approved
repair, not an alternative to it, and it is four statements — all verified above, none of them advice to
change a supported configuration:

1. **On a disaggregated (P/D) model, run both analyzers.** TA alone cannot price the prefill role at all
   ([`AD1`](#ad1)/[`AD2`](#ad2)), and with Dean's guard in place that configuration will hold rather than
   act. This is the one item that is already being enforced in code.
2. **Whenever saturation is not voting on a P/D model, prefill is not being sized.** In practice that means
   `[TA]`-only, since [the third row](#ad8-third-row) closes the sat-non-live cell. Not "sized
   conservatively" — its required capacity is structurally zero, so the optimizer neither grants nor
   defends prefill replicas. Whatever prefill is at when saturation stops voting is where it stays, or lower.
3. **The two visible symptoms are opposite, and both are this.** On rising load, prefill
   **freezes** — worst case a model serving decode at 4 replicas with prefill still at 0. On steady or
   falling load, prefill **drains to a single replica** while decode is untouched. An operator who sees
   either on a P/D model should check saturation's liveness before treating it as a workload signal.
4. **The one knob that helps is `MinReplicas`, it helps only the drain, and it is not free.** A
   `MinReplicas >= 1` on the prefill variants makes the drain provably unreachable
   (`cost_aware_optimizer.go:142-161`, per-variant). It does **not** lift a frozen prefill. The floor that
   *raises* a target is real and it does run on V2 decisions — `GreedyBySaturation` is the GPU limiter's
   allocation algorithm, reached from `saturation/engine.go:761` → `default_limiter.go:101` → `Allocate`,
   not a separate optimizer — but it is unreachable in the frozen case twice over: `filterScaleUpCandidates`
   keeps a decision only `if TargetReplicas > CurrentReplicas`
   (`greedy_saturation_algorithm.go:52-63`), and `allocateForDecision` early-returns on
   `replicasNeeded <= 0` (`:80-83`) even if it were not filtered. So **`MinReplicas` can preserve a
   scale-up, never originate one.** And the cost, which must travel with any recommendation of it: a
   `minReplicas > 0` on **any** variant makes `applyScaleToZeroEnforcement` skip the scale-to-zero enforcer
   **model-wide** (`hasMinReplicasAboveZero`, `saturation/engine.go:1362`) — including the total-zero
   minimum-replica preservation. Not a realized harm in the measured shape, but it is a model-wide
   behavioral change bought for a half mitigation, so this is a documented severity floor for the drain
   regime, cost attached — not a substitute for the repair.

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
| `AD8` | TA's prefill spare **authorizes draining the role**; two routes, both **inherited from base**, with route (A) made **deterministic** by `VG-up` | **NEW in Rev 3 — corrects Rev 1/Rev 2's "harmless".** Route (A) **CONFIRMED by execution** (prefill → 1 from 2/4/8, both optimizers, decode holds); route (B) read-only | `grep -n "scaleDownVariantSet(" internal/engines/pipeline/*.go` (expect exactly 2 callers: `cost_aware_optimizer.go:496`, `rescale.go:415`); then `cost_aware_optimizer.go:488,498` vs `rescale.go:415-421`; `engine_v2.go:509`; `analyzer_helpers.go:385`; the `#1237` clamp at `cost_aware_optimizer.go:157-160`. **Provenance:** `git show 075a208e:…/rescale.go \| grep -n "func roleDemandGPUs"` (no `s` param ⇒ base read the anchor) + `075a208e:analyzer_helpers.go:138,147` (base binder already `Live`-gated) + `075a208e:analyzer_helpers.go:237` (base `votingResults` = `Enabled` only ⇒ route (A)'s mask was real). **Base run:** arm 1 (all-zero `RC` on the pruned entry) executed 2026-08-08 — base drains identically at 2/4/8, both optimizers. **Arm 2 also executed 2026-08-08 and split the attribution:** with any one role's `RequiredCapacity` positive, **base does not drain** (prefill preserved, model scaled up on data no analyzer stood behind) **and HEAD does** — so route (A) is inherited in the all-zero regime and **HEAD-reachable** in the positive regime. Suites differ: base **308** specs, HEAD **386**. **Reachability of the decisive cell — verify this whole chain, it replaces a withdrawn "unreachable" claim:** (i) saturation stamps `satReasonNoData` when a variant has no live replicas *and* both store lookups miss (`saturation_v2/analyzer.go:389`, `:421-431`); all variants there ⇒ `ResultIsInformative` false (`analyzer_helpers.go:53-63`). **Verify the liveness step in its two-route form — non-informative ≠ non-live** (Dean, 2026-08-08): `nr.Live = ok && now.Sub(lastGood) <= threshold`, `threshold = 3 × interval` = 90 s default (`saturation/engine_v2.go:233`, `:245-247`, const `:84`), so a *previously*-informative saturation stays `Live` — and unpruned, still voting — for 90 s, while a **never**-informative one (`ok == false`) is non-live on cycle one with no window at all — **but verify that `ok == false` is reachable before relying on it, because Rev 6 concluded it is not** (see the closing note on this row); (ii) **TA does not go quiet on the same input** — it emits PRC-only capacities from its own persisted `lastPerReplicaSupply` with `Reason: itlReasonScaleFromZero` (`throughput/analyzer.go:427-440`), which is not a no-data sentinel ⇒ TA informative and `Live`; (iii) role demand survives the metrics gap via `estimateSchedulerQueueDemand` (`saturation_v2/analyzer.go:750-795`, `inputTokens = QueueBytes / BytesPerToken`, no `replicaMetrics` dependence) added per role at `:485-491` ⇒ prefill and decode both positive — precondition is **`QueueBytes > 0` specifically** (`QueueSize > 0` with zero bytes yields an all-zero demand and does *not* open the route), and the load-bearing line is that the `satReasonNoData` branch **falls through to the append** rather than skipping the variant (`:430-432`, then `:441-453`); had it skipped, `activeRoles` would be empty and `aggregateByRole` would return nil at `:479-481`, closing the route — so preserve that fall-through in any fixture; (iv) `applyUniversalThreshold` (`saturation/engine_v2.go:476-513`) has **no reference to `VariantCapacities`**, so non-informative + positive role `RC` are orthogonal by construction and **every** role is positive, not one (measured `470.588` both roles). ⇒ compliant `[sat, TA]` P/D + missing replica metrics ⇒ prefill sheds to 1 with real pods running. ⚠️ **Rev 6 closes that last implication — the chain's links (ii)/(iii)/(iv) hold, link (i) does not** ([§ withdrawn](#withdrawn) item 8): saturation's capacity store is refilled from the scale targets at step 1 of **every** cycle before `Analyze` runs (`saturation/engine_v2.go:38-53`) on a path with no zero-yielding branch (`capacity_store.go:126-128` → `deployment_parser.go:281-303`, reached on every return of both parsers) and retained **7 days** (`saturation_v2/constants.go:19`), while TA's `lastPerReplicaSupply` needs observed live metrics and expires in **1 hour** (`throughput/analyzer.go:157-162`, `constants.go:24`) — same process, so **TA warm ⟹ sat warm** and there is no window with TA the sole voter. Residual: a fresh process with *every* variant's scale-target fetch failing (`saturation/engine.go:1500-1507`), where TA is cold too. **Verify by counter-example, not by re-deriving:** find any single-fault story in which saturation stamps `no-data` on every variant while TA emits a `T-sfz` capacity. If none exists, the `[sat, TA]` cell is closed and only `[TA]`-only remains. **Do not test this with a faked stale timestamp** — no carry-forward exists (`updateLivenessAndSetLive:209-251` sets `Live` in place; `Result` is this cycle's), so a stale-timestamp fixture lands in the all-zero regime. **Floor-at-1 confirmed by mutation:** disabling `cost_aware_optimizer.go:157-161` drains prefill to **0** on both paths at all three heights and fails 4 other specs — the surviving replica is an accident of a model-level guard applied per-role, not a designed floor. **Route (B) also CONFIRMED 2026-08-08** — 12 configurations (hog demand 1000/2000/4000/8000 × limit 8/10/12), byte-identical base ≡ HEAD, prefill pinned at 1 at every budget. **Reachability bound:** `votesFromTotalDemand:552-566` — absent key abstains, `prc <= 0` abstains, **present-key-zero votes 0** — plus `combineVotes` max at `:461-470`, so a live sat outvotes TA's zero under uniform scores; the exposed cells are `[TA]`-only and **`[sat,TA]` with sat non-live**. **`MinReplicas` is already the explicit floor** — read at `cost_aware_optimizer.go:143-149`, *before* the cheapest-at-1 clause, so it dominates it; measured pf=1/1/2 for unset/1/2 with the clause live and 0/1/2 with it disabled (coder, 2026-08-08). So it fully substitutes and is strictly more expressive, but it is an **operator-set per-variant field**, so relying on it is documentation, not a fix: every unconfigured P/D model stays exposed, and it fails correlated with `AD8` (the operators who did not price prefill are the ones who did not floor it). Reviewer Finding 71/72 add the proof (`:142-161`: `n <= current − minReplicas` at every route in, clause needs `n >= current`, so it requires `minReplicas <= 0`) and two narrowings: it is **per-variant**, and the `states == nil` route to `minReplicas == 0` is dead tree-wide, so the exposed population is exactly "operators who left the field unset." **And it only helps one of the two regimes — verify this.** `greedy_saturation_algorithm.go:112-115` is the only floor that *raises* a target, and it **does** run on V2 decisions (`saturation/engine.go:761` → `default_limiter.go:101` → `Allocate`; it is the limiter's allocation algorithm, not a separate optimizer — do not dismiss it on optimizer identity), but it is unreachable in the frozen case twice: `filterScaleUpCandidates` keeps only `TargetReplicas > CurrentReplicas` (`:52-63`) and `allocateForDecision` early-returns on `replicasNeeded <= 0` (`:80-83`). So `MinReplicas` can preserve a scale-up, never originate one. **And verify its cost:** `hasMinReplicasAboveZero` (`saturation/engine.go:1362`) makes a `minReplicas > 0` on *any* variant skip `applyScaleToZeroEnforcement` **model-wide**, including the total-zero minimum-replica preservation — so the lever is a documented severity floor with a model-wide side effect, not a free mitigation. **Two regimes, measured** (coder, 2026-08-08, both optimizers, `cur` ∈ {0,1,2}, base vs HEAD): with decode `RC > 0` the dispatch takes **scale-up**, `scaleDownRoleIterated` is never entered, and prefill **freezes** at `cur` — at `cur = 0`, decode reaches 4 with prefill still 0 (measured HEAD 0/1/2 vs base 1/2/3 across `cur` ∈ {0,1,2}), and the enforcer cannot rescue it: it returns early on the model *total* (`enforcer.go:138-147`), and its total-zero fallback selects by `Cost`/`VariantName` with **no `Role` reference at all** (`:150-174`), so it may set a decode variant to 1 and leave prefill at 0; with decode `RC == 0` prefill **drains to 1**. The dispatch predicate is a global OR over roles (`analyzer_helpers.go:709-718`) with mutually exclusive arms (`cost_aware_optimizer.go:62-67`) — that is why one role captures the model. Base bought prefill exactly one replica per cycle in the same state, so the HEAD-vs-base delta is one replica, not the whole tier. **The Type-1 phrasing *"prefill's target collapses to 1"* is the drain regime only and understates the freeze.** **New harm:** `modelDemandGPUs` sums roles (`rescale.go:560-566`) → `rescaleInputsForGroup:540-546` feeds the understated total into **both** `Demand` and `CapGPUs` → constant-5-across-budgets in the sweep is the **cap** signature, so `CapGPUs` is a second repair site |
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

7. **"The `[sat, TA]`-with-saturation-non-live cell is unreachable."** This author's, Rev 4, and it is an
   *over*correction — the second wrong answer given to the same question. Correction #6 was refuted by
   Dean pointing at the shared metric inputs (*"both read EPP queue. Both read KV-cache. Dead sat ⟹ dead
   WVA"*), which was correct; the error was **generalizing a refutation past its scope**. The refutation
   established that no *metrics* asymmetry exists. It did not establish that no asymmetry exists, and one
   does: saturation's informativeness additionally depends on a **capacity store TA does not read**, while
   TA re-publishes its own persisted `lastPerReplicaSupply`. So the same empty input silences one and not
   the other, and the cell is not only reachable but reachable by the most ordinary path there is — a cold
   start ([the third row](#ad8-third-row)). Two consequences worth stating plainly: **Dean set severity on
   a premise of mine that was wrong**, and the "unreachable" line had already been written into
   [§ disposition](#disposition) as a *defer*, where it would have retired a live defect.
   **The rule:** a refutation licenses withdrawing the claim it hits, and nothing further — before
   generalizing one into an impossibility, read what else the conclusion depends on.
   *Sub-slip in the same revision, caught by Dean the same day:* the chain was summarized as
   "non-informative ⟹ non-live". It is not — `Live` tolerates `3 × interval` (90 s) of
   non-informativeness, and only a never-informative analyzer is non-live at once. The corrected two-route
   form is in the third row; the loose form would have made the state sound continuous when it is gated.

8. **"The `[sat, TA]`-with-saturation-non-live cell is reachable by a cold start, or by a sustained
   metrics gap."** This author's, Rev 5 — the **third** answer given to the same question, after #6
   ("unreachable, TA cannot act alone") and #7 ("reachable, and by the most ordinary path there is").
   Withdrawn 2026-08-08 on Dean's question *"why would sat ever become dead — what is the condition? If
   no replica metric at all, how would TA still stay alive?"*, which is the one question that forces both
   halves of the asymmetry to be read instead of one.
   **What survives:** the asymmetry itself, and the seam it rests on. Saturation's informativeness does
   depend on a capacity store TA does not read (`saturation_v2/analyzer.go:389-431`), and `Live` still has
   no causal link to `RequiredCapacity` — `applyUniversalThreshold` (`saturation/engine_v2.go:476-513`)
   never touches a `VariantCapacity`, so the composite state is expressible. That is why the seam is
   recorded as **latent** rather than retired.
   **What is wrong:** the *direction*. Rev 5 read the store's warm-up (it fills from scale targets) and
   inferred that an empty one silences saturation while TA keeps talking. Reading the other side inverts
   the conclusion, because the two memories in the same process have opposite time constants:

   | | warmed by | evicted after |
   |---|---|---|
   | saturation's capacity store | **scale-target objects**, every cycle — step 1 of `RunAnalysis` (`saturation/engine_v2.go:38-53`), before the ballot is built | **7 days** (`CapacityEvictionTimeout`, `saturation_v2/constants.go:19`) |
   | TA's `variantStates.lastPerReplicaSupply` | **observed live replica metrics only** (`throughput/analyzer.go:427-440` — the `T-sfz` complement `continue`s unless a prior observation exists) | **1 hour** (`2 × DefaultObservationMaxAge`, `throughput/analyzer.go:157-162`) |

   So **TA warm ⟹ saturation warm**: TA can only republish a supply for a variant it once saw live, and
   that same cycle's metrics wrote saturation a `learnedFromLive` record outliving TA's by 168×. Neither
   Rev 5 route reaches the cell — a cold start leaves *both* cold, and a metrics gap long enough to make
   saturation non-live has already emptied TA. The residual is a fresh process in which **every** variant's
   scale-target fetch also fails (`saturation/engine.go:1500-1507` `continue`s without writing a record),
   and TA is cold there too, so it cannot be the surviving voter.
   **Blast radius of the correction — narrow, and it does not reach the ruling.** It moves one matrix cell
   from reachable to closed. It does **not** touch `[TA]`-only, which needs no saturation death at all
   (saturation simply is not on the ballot) and is the configuration [`AD2`](#ad2)'s guard addresses; nor
   the two regimes measured at HEAD, whose fixtures build the ballot directly and bypass both memories;
   nor the arithmetic. Dean set severity on #7's premise, so **severity drops** — but the decision he made
   (repair the per-role pricing) stands, and what becomes newly open is **placement**: a defect confined to
   one configuration, in which the guard makes the model hold rather than act, is a weaker candidate for
   PR-2 than #7 implied. That is flagged for him, not decided here.
   **The rule:** #7's lesson was that a refutation licenses withdrawing only the claim it hits. The
   reciprocal lesson is this one — **an asymmetry between two stores is a claim about both of them, and its
   existence does not imply its direction.** Rev 5 established that the stores differ, then read one and
   assumed the sign. Two reads, not one: warm-up *and* eviction, on *both* sides.

**Formerly-unverified items, now closed.** Rev 1 flagged saturation's two tier-2 preconditions as
asserted-by-others rather than verified by this author. Both are now read and verified benign — see
[§ residual](#residual). Nothing in this addendum is now carried on someone else's unchecked claim.

**Claims from peers that this addendum declines rather than withdraws** — recorded so disagreement is
visible rather than silently resolved. **One of the two has since closed:** the floor at 1 as route
instrumentation (Finding 67) was rejected in [`AD8`](#ad8) on the clamp's position relative to the
callback, with both docstrings agreeing, and **its author retracted it on the same grounds** in
Finding 68 (`a798dc87`), adding that the clamp is present at base too. **The second has now closed
too, in this addendum's favor and by its author's own hand:** route (A) as *unconditionally* inherited
(Finding 66 and the planner's handoff) was settled by the arm-2 run — base does not drain when the
pruned entry held a positive `RC`, so the narrowing `AD8` insisted on was correct, and the measuring
author retracted *"no part of it is a PR-2 regression"* against their own conclusion. Nothing in this
section is now open against a peer.

> **A pattern worth naming, since it has now produced seven corrections in this section alone.** The
> first four — the "harmless" reading, `reclaimRole` as newly-unmasked, the floor as instrumentation,
> and the `TotalDemand` refinement — were each a claim about a *helper's* behavior inferred from its
> *caller's* description, or about a field inferred from a sibling field's name. In each case the
> disconfirming evidence was one `git show` away, and in two of them it was written in the docstring of
> the very function being reasoned about. The fifth, *"prefill's zero weight makes the whole model
> cheaper to reclaim from"*, named a plausible mechanism without checking which input actually bound —
> the measuring author's own table discriminated it (constant across budgets ⇒ a cap, not a share).
> **The sixth was this author's, and it is the worst of the six because nothing was read at all:** the
> claim that an EPP-side fault could take saturation non-live while TA stayed live, invented to justify
> a severity, and refuted by Dean pointing at the shared inputs — which TA's own registration file
> lists explicitly. **The seventh is this author's too, and it is the sixth's mirror image:** having been
> refuted, it took the refutation as proof of an impossibility instead of proof that one mechanism was
> wrong — so the same cell was answered wrongly twice, in opposite directions, without either answer being
> read out of the code. The rule follows, now in three halves: **for any claim of the form "X does not do
> Y", read X**; **for any claim that two components can fail independently, read what they consume**; and
> **for any claim that a state is unreachable, enumerate what its reachability depends on — a refutation of
> one route is not a proof that there is no route.** Prefer a cheap executed arm over a confident reading.

[↑ TOC](#toc)

## Disposition summary {#disposition}

| # | Item | Status | Owner of what remains |
|---|---|---|---|
| `AD1` | TA is not role-complete for P/D; prefill demand is structurally 0 | **Verified fact** (re-verified on `a9afb740`) | — |
| `AD2` | `[TA]`-only unsupported on P/D; both-by-default; documented, unenforced | **DECIDED (Dean)** | doc placement — planner; note the conditional in `AD4` |
| `AD3` | From-zero PRC work scoped to `decode`/`both` only | **DECIDED (Dean)** — follows from `AD1` | — |
| `AD4` | TA cannot veto sat — **but can dilute it when scored above sat** | **Verified fact; argument replaced in Rev 2** | whether the dilution finding gets its own line — planner |
| `AD5` | Binding-path override; hold the role when the binder is not role-complete | **OPEN** | PR-2 scope — planner; priority — Dean. ⚠️ A fix here does **not** fix [`AD8`](#ad8) route (A): this predicate acts on *demand*, route (A) runs off `RoleSpare` |
| `AD8` | TA's prefill `SpareCapacity` **authorizes draining the role**, and the same structurally-zero demand **leaves a rising role unsized** — **two regimes from one cause**: prefill **frozen at its current count, including 0**, on the scale-up arm, or **drained to 1** on the scale-down arm, while decode scales normally; **and under contention the model loses total budget, not just prefill's share** | **DECIDED (Dean, 2026-08-08) — repair the pricing.** The previous revision's "defer, unreachable" is WITHDRAWN. Both routes confirmed by execution at HEAD *and* at base; arm 2 shows route (A) is HEAD-reachable when the pruned entry carries a positive `RC`. The withdrawn claim was that saturation cannot go non-live while TA lives. **It can, and the split is structural** ([chain verified](#ad8-third-row), four links): saturation needs a capacity record or live replica metrics and stamps `NoData` without both; TA on the *same* empty input emits persisted-supply capacities and stays informative; role demand survives on `QueueBytes`; and non-informative + positive role `RC` are orthogonal by construction. **Non-informative ≠ non-live** (Dean, 2026-08-08): a previously-informative saturation stays `Live` for `3 × interval` = 90 s and is not pruned in that window, so the pruned state needs either a never-informative saturation (`ok == false`, no window) or a gap sustained past 90 s — and **Rev 6 finds neither is reachable in `[sat, TA]`** ([§ withdrawn](#withdrawn) item 8): the capacity store is refilled from the scale targets every cycle and kept 7 days, TA's persisted supply needs live metrics and expires in 1 hour, same process ⇒ **TA warm ⟹ sat warm**. So the reachable configuration is **`[TA]`-only**, which the guard makes hold. This is a severity correction; the decision below stands as made, but **placement in PR-2 is now a live question for Dean**. With that, a **compliant `[sat, TA]` P/D model sheds prefill to 1** — real pods, no misconfiguration. Severity undiminished: prefill tier minus all-but-one, surviving replica an accident (mutation → 0) | **Dean, 2026-08-08 — decided: fix the pricing. The guard covers only its own case, and the liveness variant is rejected.** (1) **Guard, confirmed as scoped:** on a disaggregated model with TA and **no saturation**, do nothing. It enforces [`AD2`](#ad2) rather than documenting it. (2) **Option (a) — the liveness-aware refusal — REJECTED** (*"PD not SAT — DONT"*): the rule stays keyed on the *enabled* set, and no second refusal predicate is wanted. (3) **Option (b) — the pricing repair — APPROVED**, and it is what covers the metrics-gap cell: once TA prices prefill per-role, the pruned-entry state no longer authorizes removing the whole tier, so the cell closes without a new gate. Three sites: per-role sizing; `CapGPUs`/`Demand` in `rescaleInputsForGroup:540-546` (fixing only the role split leaves the model hard-capped at its understated demand); `cost_aware_optimizer.go:350-367` observability. (4) **Interim documentation (option (c)) is additive, not alternative** — the highlights are in [§ AD8 operator note](#ad8-operator-note). `MinReplicas` is **not** a fourth option: it works on the drain (proof at `cost_aware_optimizer.go:142-161`, per-variant) but is an unset-by-default operator field, fails correlated with the defect, **does not reach regime (i) at all** (it can preserve a scale-up, never originate one — `greedy_saturation_algorithm.go:52-63` + `:80-83`), and **is not free**: any variant with `minReplicas > 0` makes `applyScaleToZeroEnforcement` skip the enforcer **model-wide** (`saturation/engine.go:1362`). It survives only as a documented severity floor for regime (ii), cost attached. **Sequencing constraint on the repair** (coder + reviewer, verified — and it governs **regime (ii) only**, since everything it protects lives inside `scaleDownVariantSet`, which regime (i) never enters): if #1237's positional rule is ever tidied, floor **every variant in the role** first — tidy-first re-opens this at every height on both scale-down paths (measured, prefill → 0). **Two rows, not one** — the planner's scoping ask, accepted: the freeze and the drain must reach the Type-3/backlog as separate items, because a fix verified on one says nothing about the other. **Label collision, so nobody talks past anyone:** the planner's `A68`/`B15` round numbers the mitigations **(i)/(ii)** where (i) = the `MinReplicas` floor and (ii) = the per-role pricing repair; this addendum's letters are **(a)** = liveness-aware refusal (rejected), **(b)** = pricing repair (approved), **(c)** = interim documentation. Planner-(ii) ≡ addendum-(b); planner-(i) is the `MinReplicas` lever, which is not one of this addendum's three. Verdicts agree in substance. **Noted, explicitly not proposed:** the reviewer observes that the state is *constructible* because informativeness reads only per-variant `Reason` while the RC that reaches the optimizer comes from `RoleCapacities` — two predicates nothing in the code relates (`applyUniversalThreshold`, `saturation/engine_v2.go:476-513`, never mentions `VariantCapacities`). **That seam is real and survives Rev 6; what Rev 6 removes is the claim that production can reach it** — the capacity store keeps saturation informative, so the seam is **latent, not live**, and "no production data can retire it" overstates a gap no production data can open either. Aligning the two predicates (informativeness considering role demand, or the queue term marking the variants it speaks for) would close it. That is a Type-1 design question, it is **not** in PR-2, and it is **not** a revival of rejected option (a) (different site: the liveness computation, not a second refusal predicate in the optimizer). Recorded here for a later round; no ask attached. Scope/placement — planner |
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
