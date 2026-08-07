# Combined-Analyzer Optimizer Inputs — replica-demand / coverage contract — Type 1 Design

> **Reading protocol:** Read the TOC first. Fetch only the sections you need via
> `Read <file> offset:<start> limit:<end-start+1>`. Never read the whole file up front.

**Type:** 1 (design) · **Status:** **AUTHORITATIVE** for this mission — the single design authority
for the unit/currency contract ([§ units](#units)), the enablement vocabulary and supported configs
([§ configs](#configs)), the combine rule ([§ combine](#combine)), the anchor contract
([§ anchor](#anchor)), the fair-share metric ([§ limited](#limited)), and the bug/finding inventory
([§ bugs](#bugs), [§ findings](#findings), [§ unit-findings](#unit-findings)). **Design questions that
are still open are named explicitly in [§ open](#open)** — see the decision queue at the top of that
section, which indexes every open item with who decides it and what it blocks. As of **2026-08-07 the
queue is EMPTY**: the five `W` questions are all answered, the `N8` rationale is closed, and the last
item to open — `FZ-admission`, from Dean's own follow-up — is answered *and* decided (mechanism and cap
both, folded into PR-2). Anything *not* on that queue is settled and may be relied on by task plans
without re-deriving it. Task plans (Type 3) decide *how* and *when*, never *what* — a "what" question
surfaced mid-implementation belongs in [§ open](#open), not in the plan, and a design choice this doc
declines to make is a defect in this doc, not latitude for the coder (Dean 2026-08-07: *"don't leave
design decsions to coder."*).

**Ownership and freeze — ✅ FROZEN 2026-08-07.** Sole write ownership sat with the **plan-review session**
(Dean, 2026-08-07) while the [§ open](#open) queue was being drained; that queue is now **empty**, every
`W` question and every finding is dispositioned, and **ownership is released back to the mission
planner**, which may proceed with the Type-3 refresh. Post-freeze changes go through Dean, not through a
concurrent edit. Where this doc and the Type 3 disagree, **this doc governs and the task plan is refreshed
from it, not the reverse**. The delta the Type 3 does not yet reflect — the refresh's pick-up list:

1. The [§ bugs](#bugs) #5 currency pivot targets **GPU space, not replica space**.
2. Emitted series: **rename nothing, and add nothing now** — option (d)'s target shape is recorded but
   deferred ([§ units-observability](#units-observability)).
3. **`W1`** — one fair-share entitlement per **model**, spent **jointly** across its roles
   (`Σ_role spend ≤ budget`). Both current spend sites are defects, not just mis-united.
4. **`W2`** — **priority orders; it never scales an entitlement** (invariant 11). The claim is
   unweighted; `priority × claim` survives only as a sort key. **Deferred to a future TODO** — it is
   TA-neutral, and `W3` already works without it.
5. **`W3`** — explicit `priority: 0` = *last in line, takes the leftovers*; unset defaults to `1`.
   **No API change** — `0.00001` already expresses it and already behaves correctly
   ([§ open](#open) carries the trace); what is missing is documentation.
6. **`W4`** — **no conversion factor ⇒ no spend.** A voter that cannot price a variant abstains; it is
   not exempt from the budget.
7. **`W5`** — the per-site unit table ([§ open-what](#open-what)); `fairShareCap` becomes a
   whole-replica **`floor` fill**, not `ceil`-of-a-division.
8. **`FZ-admission`** — a never-seen variant is admitted only when saturation binds; under a TA binder it
   abstains at `PRC = 0` and only the reactive path can raise it ([§ findings](#findings)). **Folds into
   PR-2**, with the mechanism (a `Reason`-tagged `PRC = 1` sentinel) and the cap (a one-replica **target**
   ceiling at the three grant sites) both **decided in this doc**, not left to the task plan.

Items 3 and 4 are **behavior changes** and must not ride inside the status-quo-preserving currency
conversion. All placements are now settled — `W1` and item 8 into PR-2, `W2` (with `U4`) to a future TODO
as TA-neutral — so the [§ open](#open) queue is empty and the doc is freezable.

**Unit audit.** The six unit rules are stated in [§ units-rules](#units-rules) and the currency
lattice they range over in [§ units-lattice](#units-lattice). The audit of the shipped code against
them — verdict per rule at both the current tip and the PR-2 end state, plus the `U1`–`U6` residuals a
complete PR-2 does not fix — is [§ unit-findings](#unit-findings). The audit checked **coherence of
units only**, never whether the arithmetic is right.

**Code currency.** Math and mechanism claims re-verified against worktree
`ta-anchor-dynamic-refresh` @ `d9f3b97e` (PR-2 through C6b) on **2026-08-07**. **Function, field and
config names are authoritative; every `file.go:N` line number is as-of-authoring and drifts** —
resolve citations by name, not by line. [§ trace](#trace) and [§ rescale](#rescale) were written
against the pre-refactor tree and are retained as *inventories of sites*, not as current line maps.

**Sources that are not authorities.** Two documents fed this one and must not be cited as
authority in their own right:
[`multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md) (reviewer-owned code trace +
discussion summary — its §9 findings are migrated here as [§ findings](#findings)) and
[`ta-anchor-refactor-review.md`](ta-anchor-refactor-review.md) Part 2 (the 2026-08-05 mechanism
redesign — migrated here into [§ anchor](#anchor)). Both remain useful as *source traces* with
per-site line evidence; neither is the design of record.

**Scope:** the engine→optimizer→rescale contract for combining analyzer
signals, and the abstraction that makes **disabling saturation-v2** a clean change rather than a
coupled one. **Sibling docs:** [`multi-analyzer-design.md`](multi-analyzer-design.md) (F1
"pre-analysis extraction"), [`optimizer-coordination-design.md`](optimizer-coordination-design.md)
(P/D role-ceiling clean model), [`wva-analyzer-lifecycle-plan.md`](wva-analyzer-lifecycle-plan.md)
(Half-B = "genuinely disable saturation", currently unscoped — this doc is its missing design).

## TOC {#toc}

- [Why this doc exists {#why}](#why-this-doc-exists-why) L115:156
- [Units, currencies & legal conversions {#units}](#units-currencies--legal-conversions-units) L157:499
  - [The one contract {#units-contract}](#the-one-contract-units-contract) L164:175
  - [The six unit rules {#units-rules}](#the-six-unit-rules-units-rules) L176:229
  - [Per-analyzer currencies (concrete, today) {#units-currencies}](#per-analyzer-currencies-concrete-today-units-currencies) L230:264
  - [The currency lattice actually in the code {#units-lattice}](#the-currency-lattice-actually-in-the-code-units-lattice) L265:296
  - [The threshold-inflated quantities {#units-thresholds}](#the-threshold-inflated-quantities-units-thresholds) L297:326
  - [Legal conversions {#units-conversions}](#legal-conversions-units-conversions) L327:390
    - [Conversion discipline — `R6` made enforceable {#units-conversions-discipline}](#conversion-discipline--r6-made-enforceable-units-conversions-discipline) L359:390
  - [Roles are distinct voters {#units-roles}](#roles-are-distinct-voters-units-roles) L391:420
  - [Integral replicas at every commitment point {#units-integral}](#integral-replicas-at-every-commitment-point-units-integral) L421:459
  - [Emitted series and their units {#units-observability}](#emitted-series-and-their-units-units-observability) L460:499
- [Enablement vocabulary and the supported configs {#configs}](#enablement-vocabulary-and-the-supported-configs-configs) L500:548
- [The core abstraction: replica-demand & coverage {#abstraction}](#the-core-abstraction-replica-demand--coverage-abstraction) L549:603
- [The combining rule (binding analyzer) {#combine}](#the-combining-rule-binding-analyzer-combine) L604:682
  - [One vote is a pass-through, algebraically {#combine-onevote}](#one-vote-is-a-pass-through-algebraically-combine-onevote) L636:656
  - [Score is a belief weight, never a budget weight {#combine-score}](#score-is-a-belief-weight-never-a-budget-weight-combine-score) L657:682
- [The binding-analyzer anchor (renamed SatEntry) {#anchor}](#the-binding-analyzer-anchor-renamed-satentry-anchor) L683:951
  - [The two-phase mechanism {#anchor-twophase}](#the-two-phase-mechanism-anchor-twophase) L848:883
  - [What the anchor is a workaround for {#anchor-completeness}](#what-the-anchor-is-a-workaround-for-anchor-completeness) L884:921
  - [Multi-vote semantics that must be pinned down {#anchor-multivote}](#multi-vote-semantics-that-must-be-pinned-down-anchor-multivote) L922:951
- [Current code: the two-PRC split and every saturation-only site {#trace}](#current-code-the-two-prc-split-and-every-saturation-only-site-trace) L952:1010
- [Latent bugs surfaced by the trace {#bugs}](#latent-bugs-surfaced-by-the-trace-bugs) L1011:1307
- [Traced findings: liveness, binding and role coverage {#findings}](#traced-findings-liveness-binding-and-role-coverage-findings) L1308:1630
- [Unit-audit findings {#unit-findings}](#unit-audit-findings-unit-findings) L1631:1717
  - [Verdict per rule — at the tip and at PR-2 complete {#unit-findings-verdict}](#verdict-per-rule--at-the-tip-and-at-pr-2-complete-unit-findings-verdict) L1641:1664
  - [Residuals — what a complete PR-2 does not fix {#unit-findings-residuals}](#residuals--what-a-complete-pr-2-does-not-fix-unit-findings-residuals) L1665:1686
  - [TA exposure — which defects enabling TA creates, amplifies, or leaves alone {#unit-findings-exposure}](#ta-exposure--which-defects-enabling-ta-creates-amplifies-or-leaves-alone-unit-findings-exposure) L1687:1717
- [How the cost-efficiency sort changes {#sort}](#how-the-cost-efficiency-sort-changes-sort) L1718:1748
- [Rescale layer trace {#rescale}](#rescale-layer-trace-rescale) L1749:1782
- [Bottom-line invariants {#invariants}](#bottom-line-invariants-invariants) L1783:1924
- [Limited-mode (greedy fair-share) path {#limited}](#limited-mode-greedy-fair-share-path-limited) L1925:2034
- [Open questions {#open}](#open-questions-open) L2035:2536
  - [Design-level "what" questions surfaced by the currency fix (W1–W5) {#open-what}](#design-level-what-questions-surfaced-by-the-currency-fix-w1w5-open-what) L2172:2536

## Why this doc exists {#why}

Goal: make the saturation-v2 analyzer **disable-able** without special-casing. Today it can't be
cleanly turned off because it plays two unrelated roles that are conflated:

1. **Metadata carrier** — `saturationEntry()` (by-name lookup of `domain.SaturationAnalyzerName`)
   is the *sole* source of per-variant topology: accelerator name, cost, role, replica count,
   pending replicas. Every optimizer/rescale computation reads `satEntry.VariantCapacities` for
   this, for *any* analyzer.
2. **Analyzer vote** — saturation-v2 is also one analyzer among several, contributing its own
   per-replica-capacity (PRC) and utilization/coverage to the combined scaling decision.

Because (1) and (2) live in the same struct entry, "disable saturation" currently means "remove
the metadata carrier," which breaks everyone. Dean's reframing (2026-08-02): **separate the two
roles.** Keep the metadata carrier always present (fed even when sat-v2 is disabled); make the
sat-v2 *vote* a normal list entry that joins only when enabled. The optimizer's combine loop
already iterates all analyzers — it just must stop treating the carrier as a vote.

The deeper finding: the carrier's PRC/utilization that the optimizer uses for **sorting and
sizing** is *saturation-only data*, not combined-across-analyzers data. It is "probably wrong
today" in the multi-analyzer case — masked only because saturation is currently the sole running
analyzer. The genuinely-combined math (bottleneck / min-removal / veto) already exists and is
correct, but it sits *beside* the saturation-only proxy instead of *driving* the sizing and sort.

**Ship decision (2026-08-03).** This is not sizing polish — it is a ship-blocker. Because the
saturation-only proxy corrupts the shared allocation state the moment a second vote joins (bugs
#1/#2/#3/#5, [§ bugs](#bugs)), **ThroughputAnalyzer cannot be enabled today in any form** — not
alongside sat-v2, not replacing it, not even experimentally: turning it on destroys the allocation
math and takes sat-v2 down with it. The only 0.9 posture *without* this change is a docs warning
("TA must not be enabled by anyone"), which is an admission the feature isn't shipped at all. Dean's
call (2026-08-03): **do the anchor refactor** — the four bugs are four faces of the same conflation,
and the anchor dissolves them structurally rather than patching four hot-path sites. TA ships as an
*enable-able* second analyzer (default stays sat-v2-only; v2 is already default over v1). The
load-bearing risk control is the **exactly-one-active-vote byte-identity invariant**
([§ invariants](#invariants) #7): the default config must behave *exactly* as today — and that path
is the one we *can* fully pin down with deterministic tests, while the opt-in multi-vote path (which
we may not fully e2e-test) cannot reach anyone who doesn't opt in. Approach: **unified code path,
single-vote collapses to today by construction (option A)**, not a frozen legacy branch (option B
rejected — error-prone and silently rotted by any future optimizer PR).

[↑ TOC](#toc)

## Units, currencies & legal conversions {#units}

Every arithmetic bug in [§ bugs](#bugs) is a unit bug. This section is the authority on which
quantity is in which unit, and which conversions are legal. Verified against the two shipping
producers (`internal/engines/analyzers/saturation_v2/analyzer.go`,
`internal/engines/analyzers/throughput/analyzer.go`) at `d9f3b97e`.

### The one contract {#units-contract}

> **Within one analyzer, `TotalDemand` and `PerReplicaCapacity` share a unit, so `demand / PRC` is
> a replica count. Nothing else is guaranteed.** No two analyzers share a unit; no analyzer's
> capacity number means anything to another analyzer. **Cross-analyzer arithmetic is legal only
> after converting each side to replicas** (or, in rescale, to GPUs).

That is the whole contract. Bugs #1, #2, #3 and #5 are each one place that adds, maxes or divides
across analyzers *before* converting — mixing KV tokens with requests per second.

[↑ TOC](#toc)

### The six unit rules {#units-rules}

*(Dean, 2026-08-07 — stated as the audit criteria for the currency work, then verified against
worktree `ta-anchor-dynamic-refresh` @ `d9f3b97e` **and** against the PR-2 end state. Verdict per
rule in [§ unit-findings](#unit-findings).)*

**`R1` — Phase I may speak in the analyzer's own metric; nothing downstream may compute in it.**
The metric unit may be *carried* — observability depends on it ([§ invariants](#invariants) #3) —
but the unit of computation, of remainders, of bookkeeping and of comparison is never the
analyzer's metric. **This holds per role as well as per analyzer:** even for one analyzer, even
saturation, the prefill role's metric and the decode role's metric mean different things and may
not be compared or summed directly ([§ units-roles](#units-roles)).

**`R2` — actual allocation and cost-based scale up/down are in replicas.** The question an
allocation step asks is *"how many replicas does this allocation need to support this model under
this shared GPU limit"* — so the currency of a commitment is a replica count, and it is **integral
at the point of commitment** ([§ units-integral](#units-integral)).

**`R3` — combining across roles or across variants happens in a shared currency, and which one
depends on what is being combined.** Two sub-rules, because rates and footprints do not combine the
same way:

- **`R3a` — rates across roles or variants combine in coverage.** Coverage is dimensionless, so
  `min`/`max` across roles and variants is meaningful. A *sum* of rates across roles is not.
- **`R3b` — resource footprints across roles or variants combine in GPUs.** GPUs are the one
  currency in which `Σ_role` is legal, because the GPU pool is what is actually shared. A footprint
  sum is legal in GPU space and **illegal in metric space and in replica space**: replicas of
  different variants are not fungible against the pool (`GPUsPerReplica` varies), and metrics of
  different roles are not commensurable at all.

**`R4` — Score combines analyzers *within* one scaled object; priority combines *across* scaled
objects.** Score is a belief weight and belongs strictly inside the combine
([§ combine](#combine-score)); priority orders and rations *between* models. Neither may appear in
the other's place — a Score multiplying a budget, or a priority inside one model's per-iteration
cap, is a category error.

**`R5` — all of the above hold for fallback values.** A fallback is a value that enters the same
arithmetic, so a fallback in the wrong currency is the same bug as a primary in the wrong currency —
and harder to see, because it fires rarely.

**`R6` — values may still carry Phase-I units; the conversion must happen before (or in) any
computation.** R1–R5 are not claims about what is *stored*; they are claims about what is *computed
on*. A field may hold the analyzer's metric all the way to a consumer, provided the consumer
converts before it computes. This is the rule that makes the others enforceable mechanically
([§ units-conversions](#units-conversions) "Conversion discipline").

> **The mechanical form of `R6`** — the audit rule that located every violation in
> [§ unit-findings](#unit-findings): *a site that reads `RequiredCapacity`, `SpareCapacity`,
> `TotalDemand`, `RoleSpare` or `PerReplicaCapacity` and does **not** divide by that same entry's
> PRC is computing in the analyzer's metric.* Every site that routes through the cross-analyzer
> combine passes by construction; **every violation found was a site that bypasses the combine.**

[↑ TOC](#toc)

### Per-analyzer currencies (concrete, today) {#units-currencies}

| Analyzer | PRC unit | What demand counts |
|---|---|---|
| **saturation-v2** | **absolute KV-cache tokens per replica** — `EffectiveCapacity` (itself already `min(k1,k2)`) with `KvCacheThreshold` applied | KV tokens in use, plus a role-aware waiting-queue footprint (`waitingQueueDemand`) |
| **throughput (TA)** | **requests per second per replica** — `perReplicaSupply` from the fitted ITL/throughput model | arrival rate plus the scheduler-queue footprint (under-counted when `SchedulerQueue` is nil) |
| **queueing-model (QM)** | its own queueing-model currency | not a supported ballot peer — the QM optimize path is an **explicit error**, see [§ configs](#configs) |

Both shipping producers hold the same *structural* identities inside their own currency:

```
TotalCapacity = ReplicaCount × PerReplicaCapacity          (ReplicaCount = ready; pending is separate)
Utilization   = TotalDemand / TotalCapacity                (dimensionless, current-load — no pending)
```

**Who produces the identity fields.** sat-v2's `domain.VariantCapacity` literal sets
`AcceleratorName` and `Cost`; **TA's does not** (`VariantName, Role, ReplicaCount, PendingReplicas,
PerReplicaCapacity, TotalCapacity, TotalDemand, Utilization, Reason` only). That asymmetry — not a
policy choice — is *why* saturation is the (a)-identity carrier in [§ anchor](#anchor), and why a
`[TA]`-only config still runs sat-v2.

**Model-level demand differs by producer.** sat-v2 aggregates its per-variant demand into the
model-level `TotalDemand` (`aggregation.SumTotalDemand`). TA deliberately does **not**: its
per-variant demand is introspection-only and is not summed into the model-level field. Do not
assume model-level `TotalDemand` is comparable across analyzers — it is not even constructed the
same way.

**A known intra-analyzer unit bug exists and is *not* a combine bug.** sat-v2's deployment-derived
fallback record charges an absolute-KV-token queue addend against `EffectiveMaxBatchedTokens`, a
*per-step* token budget — documented in-code as pre-existing and tracked separately. It is listed
here so a reader does not mistake it for one of the combine bugs; it lives entirely inside one
analyzer.

[↑ TOC](#toc)

### The currency lattice actually in the code {#units-lattice}

**There are four currencies in the shipped code, not two.** Naming them together with their *actual
carriers* is what makes an audit mechanical: to classify a site, look up which currency its inputs
are in and whether it converted. Field and function names below are authoritative; line numbers are
deliberately omitted because they drift.

| Currency | What it measures | Carried by | `Σ` legal? |
|---|---|---|---|
| **analyzer metric** | the analyzer's private unit, **per role** | `RequiredCapacity`, `SpareCapacity`, `TotalDemand`, `PerReplicaCapacity`, `RoleCapacities[role].{Required,Spare,TotalDemand}`, `RoleSpare`, `pickerState[i][role]` | **no** — not across analyzers, not across roles |
| **replicas** | a commitment | `replicaVote.Value`, `roleBottleneckReplicas`, `safeRemovalReplicasForRole`, the paired-commit `k`, `targets[variant]`, `MinReplicas`/`MaxReplicas` | **no** — not across variants (not fungible against the pool) |
| **GPUs** | the shared, rationed resource | `available[accType]`, `rescaleInput.{Demand,FloorGPUs,CapGPUs}`, `roleDemandGPUs`, `modelDemandGPUs`, `distributeGPUsByWeight`, `gpusPerReplicaFromState` | **yes** — the only additive currency |
| **coverage** | dimensionless satisfaction | `utilByRole`, `deltaUtil`, `VariantCapacity.Utilization`, `cov = n / rd` | **no** (`min`/`max` yes, `Σ` no) |

Read it as a partial order of conversions, not a set of synonyms:

```
analyzer metric ──÷ PRC──▶ replicas ──× gpusPerReplica──▶ GPUs
        │                     │
        └──── n·PRC/demand ───┴──▶ coverage        (dimensionless; no way back)
```

Two consequences, stated because the code violates them in exactly the places the audit found:

- **metric → replicas is per `(analyzer, role, variant)`.** There is no model-wide or even role-wide
  PRC to divide by, so any conversion that picks *one* PRC for a whole role is an approximation and
  must say so ([§ units-integral](#units-integral)).
- **coverage is terminal.** Once a quantity is dimensionless you cannot recover a replica or GPU
  count from it without re-multiplying by a demand you name explicitly.

[↑ TOC](#toc)

### The threshold-inflated quantities {#units-thresholds}

`RequiredCapacity` (RC), `SpareCapacity` (SC) and `RoleCapacities[role].{Required,Spare}` are
produced by the **engine post-step** (`applyUniversalThreshold`), in the owning analyzer's
currency, and they are **margin-inflated**: they are not demand.

```
RC = max(0, TotalDemand / scaleUpThreshold − TotalAnticipatedSupply)      // anticipated = ready + pending
SC = spare measured against the scaleDownBoundary watermark
```

`initRoleState` seeds `pickerState[i][role]` from **`RequiredCapacity`**, so the picker's per-analyzer
state already carries the `/scaleUpThreshold` inflation. **Any formula that treats `pickerState` as
"demand" is treating a margin-inflated number as demand.**

**Three constants, three jobs — never substitute one for another.**

| Constant | Default | What it means | Lands on |
|---|---|---|---|
| `KvCacheThreshold` (**k_sat**) | **0.80** | the definition of "full" — the usable fraction of a replica's KV cache | **PRC** — it shapes capacity itself |
| `scaleUpThreshold` | **0.85** | scale-**up** watermark (a margin) | **RC only** |
| `scaleDownBoundary` | **0.70** | scale-**down** watermark (a margin) | **SC only** |

`0.85` / `0.70` form an **HPA-style no-op band** around the steady state. They are **margins, not
utilization targets**, and they never touch PRC. An analyzer that intends to "mirror saturation's
threshold" when shaping its own PRC must mirror **k_sat**, not a watermark — mirroring the wrong one
is a real (if small) capacity error, since k_sat enters PRC on two paths.

[↑ TOC](#toc)

### Legal conversions {#units-conversions}

These are the only sanctioned ways to cross a unit boundary:

| From → to | Formula | Notes |
|---|---|---|
| demand → replicas | `rd_i[role,v] = demand_i[role] / PRC_i[role,v]`, `ceil` at the point of sizing | per analyzer, per variant — the only cross-analyzer-comparable currency |
| replicas → coverage | `cov = n · PRC_i / demand_i = n / rd_i` | see [§ abstraction](#abstraction) |
| replicas → GPUs | `GPUs = replicas × gpusPerReplica` | `gpusPerReplicaFromState`, fallback 1; rescale's currency |
| cost ranking | `costEfficiency = Cost / PRC` | the **one** legitimate standalone use of PRC; valid because demand cancels within a role (single analyzer) or is the binding PRC (multi) |

> **Round-trip rule (the design-level form of the `prcRef` capture rule).** A quantity denominated
> by dividing by `PRC_x` must be converted back by multiplying by **the same** `PRC_x`. Denominate
> a budget with one variant's PRC and spend it against another's, and the budget is silently
> rescaled by `PRC_x / PRC_y`. This is why a per-role reference PRC used to build a budget must be
> **captured** at denomination time and carried, never re-derived at spend time: the anchor's
> sizing is refreshed in place between the two moments, so re-deriving can drift both in **value**
> (a different number for the same variant) and in **identity** (`costEfficiency = Cost/PRC`
> reorders the cost sort, so "the cheapest variant" is itself a function of PRC).

Anywhere PRC appears **standalone** in sizing or ordering — outside the four rows above — is a
smell; see the PRC = 1 mental experiment in [§ abstraction](#abstraction).

> **Caveat on the `costEfficiency` row.** "Demand cancels" holds within a role **for one analyzer**;
> under multi-vote it holds only while the variants being ranked share a binder. Two variants in one
> role can bind to *different* analyzers ([§ combine](#combine) — binding is per `(role, variant)`),
> and then `Cost / PRC` compares dollars-per-KV-token against dollars-per-request-per-second: a
> ratio of two different currencies. The **batch** form used in [§ sort](#sort)
> (`Cost × combinedDesiredReplicas`) is immune because it is denominated in replicas; the
> **marginal** form is the exposed one. Not wrong in any shipped config (one binder per role today),
> and not fixed here — recorded as [§ unit-findings](#unit-findings) `U3`.

#### Conversion discipline — `R6` made enforceable {#units-conversions-discipline}

*(Dean, 2026-08-07.)* Every function that computes on a value from another currency performs the
conversion **explicitly, at initialization**, and names it: `X.toReplicas()`, `X.toCoverage()`,
`X.toGPUs()`. Three reasons this is a rule and not a style preference:

- It moves the audit from "read the whole function and infer the units" to "find the conversion call
  at the top." A function with a foreign input and no conversion call is a violation on sight.
- It puts the **choice of divisor** on one visible line — which is the only place the round-trip rule
  above can actually be checked, because that is where the reference PRC (or `gpusPerReplica`) is
  captured, once.
- **The conversion functions already exist.** `analyzer_helpers.go`'s collectors are the sanctioned
  conversions: `roleBottleneckReplicas` (metric → replicas, `max_i`), `safeRemovalReplicasForRole`
  (metric → replicas, `min_i`), and the `utilByRole` / `deltaUtil` pair (metric → coverage). The
  discipline is to *route through them* rather than re-derive a division in place. Every `R1`
  violation the audit found is a site that did its own division — or none.

> **Coder-checklist invariant.** Any commit touching an allocation, budget, cap, clamp, sort key or
> remainder must answer, per site: **which currency is this in, where was it converted, and which
> factor was captured?** A site that cannot answer is a finding, not a style nit. This belongs in the
> reviewer checklist for *every* commit in this mission, not only the currency commits.

**Compile-time enforcement is available, and is the strongest form of this rule.** Go can carry the
lattice in the type system — `type Replicas float64`, `type Coverage float64`, `type GPUs float64`,
with conversion methods as the only way between them — at which point every violation in
[§ unit-findings](#unit-findings) becomes a build error instead of a review finding. This is **not**
proposed for this mission: it touches every signature in the pipeline. It is recorded because it is
the answer to "how do we stop this class of bug from coming back", and because a future refactor
that is already touching those signatures should take it.

[↑ TOC](#toc)

### Roles are distinct voters {#units-roles}

**RULE (Dean, 2026-08-07): treat different roles as different analyzers.** The units *look* the same
because they share a field name and a producer, but a prefill role's metric and a decode role's
metric are different quantities, produced by role-specific demand accounting; nothing makes them
commensurable. The correct key is **`(analyzer, role)`** — exactly what [§ abstraction](#abstraction)
already observes descriptively and [§ invariants](#invariants) #6 records. What is new is the
**disposition: this is a rule to be enforced, not a curiosity to be noted.**

**What the rule forbids, concretely** — any `Σ_role`, `max_role` or `min_role` over **metric-space**
or **replica-space** per-role quantities, and any silent fallback from a role-level number to a
model-level one:

| Site | The role-mixing step | Status under this rule |
|---|---|---|
| `fairShareValue` | `Σ_role pickerState[i][role]` — sums per-role metric-space remainders | **fixed by the currency pivot** *iff* it lands in GPU space ([§ limited](#limited)); a replica-space pivot converts the sum but leaves it illegal |
| `fairShareValue`'s zero-result fallback | `max_{i,role} pickerState[i][role]` — maxes across roles in metric space | same; `R5` makes this a first-class site, not an edge case |
| the fair-share role pick | a **scalar** cross-role budget caps a **single** role's pick | pre-existing; the *unit* half is fixed by GPU space, the *policy* half is [§ open](#open) `W1` |
| the `allocateForModel` clamp | each role clamped independently against that same cross-role scalar | as above — **and** the "sat-only is inert because `bound ≥ d_role`" argument *rests on the illegal sum* and does not survive this rule ([§ bugs](#bugs) #5 site (iv)) |
| emitted `decision.RequiredCapacity` / `SpareCapacity` | falls back from `RoleCapacities[role]` to the **model-level** RC/SC when the role key is missing | **open** — see [§ units-observability](#units-observability) / `U5` |

**Why GPU space is the resolution, and not a coincidence.** `R3b` says footprints sum legally in
GPUs. The roles of one model draw from the *same* GPU pool, so `Σ_role gpus[role]` is a real
quantity — the model's footprint — while `Σ_role tokens[role]` and `Σ_role replicas[role]` are not.
Denominating the cross-role budget in GPUs therefore **fixes the role-mixing and the analyzer-mixing
with one change**, instead of fixing the second and merely converting the first. That is the design
reason for [§ limited](#limited)'s GPU-space decision, over and above "GPUs are what is scarce."

[↑ TOC](#toc)

### Integral replicas at every commitment point {#units-integral}

`R3b` denominates the *budget* in GPUs; `R2` says the *commitment* is a replica count. Those are
consistent only if the quantization is done right — and the wrong way is seductive: divide a GPU
share by `GPUsPerReplica` and round. `ceil` over-commits GPUs that do not exist, `floor` silently
strands the remainder, and with heterogeneous `GPUsPerReplica` inside one role neither is a fair
split.

> **RULE: never round a GPU share into replicas.** Commit whole replicas while a whole replica's
> worth of the resource remains, and return the remainder to the pool.

The rescale layer already does exactly this, and it is the reference implementation for every future
commitment site:

- `fillRole` commits inside `for wantGPUs - spent >= g` — a replica is added only when a **whole**
  replica's GPUs fit, so `spent` is always a multiple of `g` and never exceeds the grant.
- the caller decrements the pool by **`spent`, not by `want`**, so the quantization remainder returns
  to the pool rather than being lost or double-spent.
- `shrinkRole`'s `maxRemovable` uses **integer division** of the remaining GPU delta by `g` — whole
  replicas in the shed direction too.
- `roleDemandGPUs` `ceil`s the **replica** count *first* and multiplies by `gpusPerReplica` *after* —
  the replica count is made integral **before** the currency changes, never after.

So the GPU-space prescription needs no new rounding policy; it needs new sites to adopt the one that
already ships. A commitment site computing `round(gpuShare / g)` is a finding even where the
arithmetic looks equivalent in the homogeneous case.

**The residual: the reference-variant approximation.** `roleDemandGPUs` — and any GPU-denominated
fair-share numerator — converts a whole role's demand through **one reference variant's**
`PerReplicaCapacity` and `GPUsPerReplica` (`roleDemandGPUs` uses the cheapest variant's). That is a
homogeneous-role approximation, and it is the *same* weakness as the reference-PRC choice in the
fair-share cap: **one class, two dimensions.** It is neither introduced nor fixed by the currency
work. What the currency work *does* change: in GPU space the spend-time factor is `GPUsPerReplica` —
**immutable deployment topology** — instead of the anchor's per-iteration-refreshed
`PerReplicaCapacity`, so the capture-vs-re-derive hazard of [§ invariants](#invariants) #9 **does not
arise for the cap at all**. The approximation survives; the drift hazard stops existing.

[↑ TOC](#toc)

### Emitted series and their units {#units-observability}

`R1` permits *carrying* the analyzer's metric to a consumer, and observability is such a consumer.
It is also the one place where "carried, never computed on" is not the end of the story: a human
comparing two points on a time series is performing a computation the code cannot type-check.

**The problem (traced 2026-08-07).** `buildDecisionsWithOptimizer` copies the binding analyzer's
`RequiredCapacity` and `SpareCapacity` onto the emitted decision, so the emitted series **inherits
the binder's unit**. Under multi-vote the binder can flip between cycles *and* between variants, so
one series silently changes unit mid-flight — KV tokens for one scrape, requests per second for the
next — with no label change to signal it. A dashboard plotting it, or an alert with a fixed
threshold on it, is wrong in a way nothing in the code can catch. The same site also falls back from
`RoleCapacities[role]` to **model-level** RC/SC when the role key is missing, mixing a role quantity
with a model quantity ([§ units-roles](#units-roles)).

**Decision (Dean, 2026-08-07) — option (d): emit both, and rename nothing.**

| Series | Unit | Disposition |
|---|---|---|
| the **existing** observer series | unchanged (binder-inherited) | **name and semantics preserved** — current dashboards keep working. A hard constraint, not a preference: a rename is a silent break for anyone plotting it. |
| **per-analyzer** raw series | that analyzer's own metric, carried on an analyzer label | **deferred** (see below). Unit-stable by construction: the unit becomes a property of the label, so no series ever changes unit. |
| **dimensionless / coverage** series | coverage | **deferred** (see below). Coverage is comparable across analyzers, roles and models, which is exactly what a dashboard or an alert threshold needs. |

> **Narrowed 2026-08-07 (Dean): *"no new series now."*** Option (d) stands, but only its
> **rename-nothing** half is in scope. The two additions above are the **recorded target shape**, not
> work in PR-2 — nothing is emitted, nothing is renamed, and no metric is redefined in place.
>
> What this leaves is a **documented limitation** rather than a fix, and the trade is deliberate: the
> defect is observability-only (it cannot missize or misgate a decision — [§ units-rules](#units-rules)
> `R1` permits carrying the metric to a consumer), whereas adding series is a permanent external
> contract that is far harder to withdraw than to postpone. Recorded as [§ unit-findings](#unit-findings)
> `U5`. When it is picked up, the table above is the specification; until then a dashboard author needs
> to know that the existing series' unit is binder-dependent, which is the point of writing it down.

*(Distinct from the `Utilization` gauge question in [§ open](#open) #6, which is about current-load
vs anticipated-coverage semantics on a **different** series and whose answer is "no code change, add
a doc note". Both are observability; neither is the other.)*

[↑ TOC](#toc)

## Enablement vocabulary and the supported configs {#configs}

Three independent predicates gate an analyzer's participation. Conflating them is the root of the
liveness findings in [§ findings](#findings).

| Predicate | Source | Means |
|---|---|---|
| **Enabled** | `effectiveEnabled(name, cfg)` over the `analyzers` config list | the operator asked for this analyzer |
| **Live** | the ballot entry's own `Live` flag | it produced a fresh, usable result **this cycle** |
| **Informative** | `ResultIsInformative` | the result carries a usable signal rather than a no-data/error placeholder |

**Enablement is opt-in, and membership is exact.** With an **empty** `analyzers` list, `ApplyDefaults`
supplies sat-v2's entry (so the default config is `[sat]`). Once the list is **customized**,
membership is exactly what it names — a name absent from a non-empty list is off. `analyzers: [TA]`
is therefore TA-only *by implication of opt-in*, not by a mutual-exclusion rule, and nothing
re-injects sat-v2 into a customized list. Opt-in governs only whether sat-v2's **(b) vote** joins the
ballot; sat-v2 the *analyzer* always runs, because it carries the anchor's (a) identity fields
([§ units](#units-currencies), [§ anchor](#anchor)).

**Which gate each combine actually reads.** This table is the current state, not the target; the
gaps are the `VG-*` findings.

| Combine | Gate today | Verdict |
|---|---|---|
| binder selection (`bindingIndexForRole` → `combineVotes`) | `Enabled && Live && Informative` | strictest — correct |
| `votingResults` prune (feeds `initRoleState` → `roleBottleneckReplicas`, i.e. **scale-up**) | `Enabled` **only** | **gap `VG-up`** — a stale-but-enabled analyzer's last `Result` can still force a scale-up |
| safe-removal `safeRemovalReplicasForRole` (**scale-down** sizing) | `Live` | enforced-safe |
| scale-down veto `needsScaleDownForRole` | `Live` | enforced-safe |
| the anchor's per-variant (b)-fallback | `Enabled` (sat) | **gap `VG-fallback`**, superseded by dropping the fallback (`N8`) |

The asymmetry is the thing to remember: **scale-down is enforced-safe by explicit `Live` guards;
scale-up is only *emergently* safe**, resting on "a dead analyzer's RC is 0." A future analyzer that
carries a stale-but-informative `RC > 0` forward breaks that, which is why `VG-up` is a real
hardening item rather than a theoretical one.

**The three supported configs.** Any other list content is out of contract.

| Config | Anchor (a) | Ballot | Anchor (b) | Per-iteration refresh |
|---|---|---|---|---|
| **`[sat]`** — the default | sat-v2's | `{sat}` | sat-v2's, as-is | **none** (one vote) |
| **`[sat, TA]`** — opt-in multi-vote | sat-v2's | `{sat, TA}` | the **binding** analyzer's, per `(role, variant)` | **yes** |
| **`[TA]`** — opt-in TA-only | sat-v2's (it still runs) | `{TA}` | TA's, as-is | **none** (one vote) |

**QM is not a ballot peer.** It is structurally a second V1 pipeline, and the QM optimize path is
refused by **explicit error** rather than silently falling through to sat-v2 — see
[§ findings](#findings) `N6`. Folding QM into the multi-analyzer engine is tracked separately.

[↑ TOC](#toc)

## The core abstraction: replica-demand & coverage {#abstraction}

Every analyzer already transforms its native metric into a per-replica capacity (PRC) and a
utilization — confirmed in each producer:
`saturation_v2/analyzer.go:135/451`, `queueingmodel/analyzer.go:146/395`,
`throughput/analyzer.go:380/449`. So the raw materials for a unit-free abstraction already exist.

Define, **per (analyzer `i`, role, variant `v`)**:

- **replica-demand** `rd_i[role,v] = demand_i[role] / PRC_i[role,v]`
  — how many replicas of `v` analyzer `i` needs to cover its demand.
- **coverage** `cov_i[role,v] = n · PRC_i[role,v] / demand_i[role] = n / rd_i[role,v]`
  — fraction of analyzer `i`'s demand covered by `n` replicas. Flip-side of utilization
  (coverage = 1/utilization in replica space).

Mental experiment that motivates this (Dean, 2026-08-02): calibrate every analyzer to `PRC = 1`
and fold the scale into demand. Then `desired_replicas = demand`, and PRC drops out of every loop
**except the cost-sort**. Coverage becomes the single key parameter of every gate. We do **not**
actually set PRC = 1 (see [§ invariants](#invariants)) — the point is that the *only* legitimate
role of PRC is the `demand/PRC` and `n·PRC/demand` conversions; anywhere PRC appears standalone in
sizing/sorting is a smell.

**Coverage is a family, not one number** (Dean, 2026-08-03). `coverage(n) = n·PRC / demand_target
= n / rd`. The **denominator is always demand** (threshold-folded `demand_target`); only the
**numerator `n` changes meaning** by call site:
- initially `n = actual + pending` (current provisioned supply),
- during allocation `n = achieved-so-far` (current + committed this pass),
- at the target `n = desired`.

This is the same quantity the coordination doc calls *achieved* (`achieved = supply/demand_target`,
`remaining = 1 − achieved`); see [`optimizer-coordination-design.md`](optimizer-coordination-design.md)
§ Supply taxonomy. The clean form keeps `pending` in the numerator `n`, never in the denominator —
this is the *conceptual* target for the coordination-doc rewrite and for reconciling the
observability `Utilization`, but note the suspected anticipated-in-denominator *scaling* bug did not
survive tracing ([§ bugs](#bugs) #4 — downgraded 2026-08-03; the decision path already accounts for
pending via RC).

Legacy-complexity note (Dean): `rd` is **not** a clean matrix. Each `(analyzer, role)` can be a
completely separate analyzer — the metric need not mean the same thing per role, and its
computation can differ. The role-combine (coordinated P/D scaling) math is solid and does **not**
require all roles to share the same analyzer set; **where it works in replicas and coverage it is
already correct**. Demand is already per-role, so logically it's equivalent to indexing demand per
`(analyzer, variant, role)` or per `(analyzer, scaled-object-target)`.

> **Escalated 2026-08-07 (Dean).** This stopped being a descriptive note and became a rule:
> *different roles are treated like different analyzers* — see
> [§ units-roles](#units-roles) for the rule and the list of sites that violate it. Two clarifications
> so the escalation is not over-read: **(1)** the *role model* itself — which analyzer serves which
> role, and how P/D coordination combines them — is **unchanged**; what changes is that per-role
> quantities may no longer be summed or compared outside GPU space. **(2)** the clause above holds
> only *where* the code is in replicas and coverage; the greedy fair-share path
> ([§ limited](#limited)) is **not**, which is precisely the finding.

[↑ TOC](#toc)

## The combining rule (binding analyzer) {#combine}

Per `(role, v)`, combine across the **active** analyzers:

- **scale-up / desired** `desired[role,v] = max_i ceil(rd_i[role,v]) = max_i ceil(demand_i/PRC_i)`
  — the bottleneck analyzer sets the target.
- **coverage** `coverage[role,v] = min_i cov_i[role,v] = n / desired[role,v]`
  — the binding (least-covered) analyzer.
- **scale-down (spare)** `safeRemoval[role,v] = min_i floor(spare_i/PRC_i)` over **live**
  analyzers — unanimous slack.
- **veto** — all live analyzers must agree there is spare (`RoleSpare_i > 0`).

The **binding analyzer** for `(role,v)` is `argmax_i rd_i[role,v]` — the one that determines both
`desired` and `coverage`. This already exists as the correct math in:
`roleBottleneckReplicas` (`analyzer_helpers.go:182`, the `max_i ceil` combine),
`safeRemovalReplicasForRole` (`:246`, the `min_i floor`), and
`needsScaleDownForRole` (`:301`, the all-live-agree veto).

**Binding is per (role, variant) — never model-global** (Dean, 2026-08-03). `demand_i[role]` is
per (analyzer, role) — the same across variants in a role — but `PRC_i[role,v]` varies by variant,
so `argmax_i (demand_i/PRC_i[v])` can pick a **different binding analyzer for each variant, and for
each role**. Prefill vs decode variants (different roles) are bound independently; even two variants
inside one role can bind to different analyzers. The anchor must therefore resolve binding
**per-entry** ([§ anchor](#anchor)); any code that assumes a single "binding analyzer" for the whole
model is wrong.

**⚠ FSV is the one place that sums instead of maxing.** Every combine above is bottleneck
(`max`/`min`). `fairShareValue` instead does `Σ_i Score_i·…` — a Score-weighted **sum** across
analyzers, which over-counts (3 analyzers each wanting 5 replicas ⇒ sum reflects 15, not the correct
bottleneck 5). Fixing it is a **five-site lock-step change**, not a one-liner — see
[§ bugs](#bugs) #5 and [§ limited](#limited).

### One vote is a pass-through, algebraically {#combine-onevote}

`combineVotes` on a **single-entry** ballot is an identity, and this is worth stating as arithmetic
rather than as a claim about a code path. With one vote:

```
b        = 0                    // the sole entry binds
e        = votes[0].Value
excess   = Score₀ − Score₀ = 0
result   = votes[0].Value,  binder 0
```

**Score cannot influence a one-analyzer ballot** — not through the combine, and not through any
weight applied inside it. This holds *before* any of the fair-share currency work, and it is the
structural reason the `[sat]`-only default is preserved by construction across every combine change
in this mission ([§ invariants](#invariants) #7 and #8). It also means "the goldens didn't move" is
weak evidence about multi-vote arithmetic and strong evidence about nothing else: a single-vote
fixture exercises the pass-through, not the combine.

[↑ TOC](#toc)

### Score is a belief weight, never a budget weight {#combine-score}

**Dean's semantics.** `Score` (from `AnalyzerScoreConfig`) expresses *how much we believe this
analyzer*, and belief **dominates**: a higher-Score analyzer's vote pulls the combined result toward
itself, so the outcome lies between the plain bottleneck and the Score-weighted blend. Consequences
that are design decisions, not implementation detail:

- **Score belongs in the combine, and only in the combine.** It weights *what number we believe*,
  never *how much we may spend*. Multiplying a budget, a fair-share metric, or a GPU allowance by
  Score is a category error — this is exactly bug #5(i), and the earlier hedge "× Score only if
  Score is meant to weight budget" is **withdrawn**.
- **A Score of 0 must not silently delete a vote's veto power.** Believing an analyzer's *number*
  not at all is different from removing it from the electorate; scale-down safety comes from the
  `Live` veto, which Score does not gate. See the abstain-vs-veto rule in [§ anchor](#anchor).
- **A `0` vote is not a veto once the combine weights by dominance.** Under the pre-refactor
  arithmetic a zero could be relied on to pull a result to zero; under dominance weighting it cannot.
  Any veto — notably the per-variant scale-down veto — must therefore be expressed **outside** the
  combine and return before it, never encoded as a zero-valued vote. Recorded so a later refactor
  does not "simplify" it back into the combine ([§ unit-findings](#unit-findings) `U6`).
- **One coercion site, not two.** Score currently reaches the arithmetic through two different
  coercions — the combine's own (`Score ≤ 0 → 1.0`) and a raw `e.Score` read in the fair-share
  metric. Removing Score from `fsv` collapses these to one, which is a real (if incidental)
  simplification: there is then exactly one place that decides what a missing or zero Score means.

[↑ TOC](#toc)

## The binding-analyzer anchor (renamed SatEntry) {#anchor}

**Dean's model (locked 2026-08-03).** The clean way to think about the entry the optimizer reads —
**renamed and repurposed from `SatEntry` as the "binding analyzer" anchor** — is a split into two data
categories, **(a)** and **(b)**:

- **(a) — common metadata.** Analyzer-independent topology/identity that only **sat-v2** produces
  (`AcceleratorName`, `Cost`, and the variant identity/state sat establishes). Everyone needs it — the
  other analyzers, the optimizer, and the engine's GPU accounting. It lives on the anchor, populated
  **from sat-v2's run**, and is **never overwritten** — not by the first-entry copy, not by any refresh.
- **(b) — per-analyzer fields.** Quantities that **every** enabled analyzer (sat included) computes for
  itself; each analyzer's (b) is one **ballot** entry. Two sub-kinds differ in whether they reach the
  anchor:
  - **sizing/sort** — `PerReplicaCapacity`, `TotalCapacity`, `TotalDemand`, `Utilization` — **mirrored
    onto the anchor** as the **binding analyzer's** (trivially the sole analyzer's when only one is
    enabled), so the many downstream sizing/sort/observability read sites need no change.
  - **RC/SC** — `RequiredCapacity`, `SpareCapacity`, `RoleCapacities` — **stay per-analyzer**: the
    cross-analyzer combine (safe-removal `min_i`, veto all-agree) reads them off **every** ballot entry;
    they are **never combined onto the anchor**.

There is **no special voting code**: the enabled-analyzer list *is* the ballot, every entry votes
uniformly, and the anchor is just the (a)+(b) carrier the optimizer reads.

**Engine (builds the inputs, in order):**
- Run **sat-v2**. Populate the anchor with sat-v2's **(a) and (b)**.
- Put sat-v2's **(b)** on the ballot **only if sat-v2 is enabled** (its vote may be disabled while the
  analyzer still runs — see the F1 note below).
- Run **every enabled analyzer, in any order**. Each produces its own **(b)**, and may read the common
  **(a)** through the known anchor.
- **Copy (b) from the first ballot entry onto the anchor.** Only the (b) fields; the anchor's (a) stays
  sat-v2's, unchanged.
- Call `optimize` with the anchor + the ballot (the enabled-analyzer list).

**Enablement contract — opt-in (Dean, 2026-08-03).** "sat-v2 enabled" resolves through the same
`effectiveEnabled` predicate as every analyzer: enabled by default **only when the `analyzers` list is
empty** (`ApplyDefaults` supplies sat-v2's entry); once the list is **customized**, membership is
exactly what it names — a name absent from a non-empty list is off. So a customized `analyzers: [TA]`
is TA-only ("TA in ⇒ sat-v2's vote out"), **implied by opt-in, not enforced by a mutual-exclusion
rule**. This is the PR-1 (static) contract; the both-enabled config (`[sat-v2, TA]`) becomes a real
multi-vote in PR-2. **No `ApplyDefaults` change** re-injects sat-v2 into a customized list (the rejected
"always-on unless explicitly disabled" option) — the anchor's **(a)** is preserved regardless because
sat-v2 always runs for the anchor; opt-in governs only whether sat-v2's **(b) vote** joins the ballot.

**Optimizer (only when `len(ballot) > 1`): refresh the anchor's (b).** For each `(role, v)` the refresh
finds the binding analyzer (`argmax_i rd_i`, [§ combine](#combine)) and **overwrites only the anchor's
(b) fields** with that analyzer's. **(a) is never touched.** The cross-analyzer combine — safe-removal
`min_i`, veto all-agree — reads (b) **per-analyzer off the ballot** ([§ combine](#combine),
[§ invariants](#invariants) #4), not off the anchor.

**Single vote ⇒ no refresh ⇒ the anchor's (b) is the sole analyzer's as-is.** sat-v2 only → anchor (b)
= sat-v2's (today's `SatEntry`, byte-identical). TA only → anchor (a) = sat-v2's (always), anchor (b) =
TA's. The `len(ballot) > 1` check is a **work-skip, not a code fork**: with one ballot entry the
anchor's (b) already equals that entry's, so the refresh would be a no-op and is simply not executed.
There is **one code path** — no separate one-vote path, and **no assumption** that only one analyzer is
ever enabled.

Because after the refresh the anchor carries the *binding* analyzer's (b) per `(role,v)`, **all the
existing optimizer read sites keep working as-is** — `costEfficiency`, `fairShareCap`, `roleDemandGPUs`,
the utilization write-back all read the anchor and now get the binding (b) instead of saturation-only
values. The anchor is **refreshed each iteration** of the allocation loop (multi-vote only) so it always
reflects the current binding analyzer (which can shift as replicas are added and coverage changes);
binding is state-dependent, so under multi-vote the anchor's (b) is recomputed, not computed once.

**Implementation note (materialization — corrected 2026-08-05).** There is **no stored anchor field**.
The anchor is **derived on demand** by a Phase-2 getter (`bindingAnchor`, successor to `saturationEntry`)
that builds a fresh `*AnalyzerResult` **merged per variant, keyed by `VariantName`** — (a) identity fields
from saturation's entry for that name, (b) sizing fields from the binding analyzer's entry for that same
name, with a per-variant fallback for a variant the binding analyzer omits: saturation's own (b) is
used as the fallback sizing source **only when saturation is enabled** (and it runs *before* any
non-voting entry is pruned from the combine ballot). Under `[TA]`-only, saturation is the (a)-identity
carrier but **not** a (b) source — a variant the binding analyzer omits, with no persisted TA
per-replica-capacity, therefore yields **PRC = 0** (not proactively selectable; the reactive
scale-from-zero engine covers genuine cold-start), keeping the (demand, PRC) pair single-sourced
(Dean, 2026-08-05 — see [`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md) §2). The end state is
unchanged — **anchor = (a) + (b, the binding analyzer's); ballot = (b) per analyzer** — only the
materialization differs: it is recomputed at each read site rather than stored on the request. (An earlier
draft of this note described two equivalent stored-field "copy mechanisms" (i)/(ii) plus a positional
"first enabled ballot entry" copy; that stored-field design was superseded — see
[`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md).) The exact partition of fields into (a)
vs (b) is the contract table below and is unchanged.

**Anchor field contract.** Per `(role, variant)` anchor entry:

| Category | Fields | On the anchor? | Refreshed when `len(ballot) > 1`? |
|---|---|---|---|
| (a) common metadata | `AcceleratorName`, `Cost`, variant identity/state | **yes — sat-v2's, always** | **no — never** |
| (b) sizing/sort | `PerReplicaCapacity`, `TotalCapacity`, `TotalDemand`, `Utilization` | **yes** — first ballot entry (1 vote) / binding analyzer per `(role,v)` (>1) | **yes** |
| (b) RC/SC | `RequiredCapacity`, `SpareCapacity`, `RoleCapacities` | **no** — read per-analyzer off the ballot (`Remaining`/`Spare`/`RoleSpare`) | n/a (the combine reads every vote) |

(Only the sizing/sort subset of (b) is mirrored onto the anchor — the single *binding* representative
the sizing/sort/observability sites read. RC/SC never reach the anchor: the cross-analyzer combine
reads them off every ballot entry directly.)

Further properties of the anchor:

- **The anchor is the *only* mutable cell — and that makes it clean** (Dean, 2026-08-03).
  **Everything the engine produces is immutable input** — every analyzer entry, *including the
  anchor's initial value*. The optimizer owns exactly one piece of mutable state: the anchor, which
  it **recomputes deterministically each iteration**. The bottleneck (binding PRC / demand /
  coverage per `(role,v)`) is a **pure function of three immutable-or-progress inputs**:
  1. the immutable analyzer entries (their `rd_i`, `PRC_i`, `demand_i`),
  2. the current + pending replica counts, and
  3. the ongoing allocation state (replicas committed so far this pass).
  Given those three, the anchor is fully determined — no hidden history, no order-dependence. This
  is why it's *clean*, not a hack: the mutation is a memoized projection of immutable data, not an
  accumulating side effect. Today `Result.VariantCapacities` (where PRC lives) is already treated as
  **immutable topology** ("The original Result values are never mutated," `optimizer_interfaces.go:20`);
  the anchor's combined PRC + coverage are **new mutable working fields** layered on top — do not
  overload the immutable topology PRC for them.
- **Refresh timing: multi-vote refreshes each iteration; single-vote populates once then disables the
  refresh** (Dean, 2026-08-03). When **more than one vote** is active the anchor is a pure function of
  allocation progress, so it must be refreshed *before* every role-pick iteration — and the first
  iteration is not special (its "progress so far" is just current+pending, the deterministic starting
  point). When **only one vote** is active the anchor is populated **once and the per-iteration refresh
  is disabled entirely** — the sole vote is trivially binding and never shifts, so there is nothing to
  recompute. This is stronger than a no-op: the refresh code is **not executed at all** in the default
  path ([§ invariants](#invariants) #7). Dean considered calling the refresh from *inside* the
  (renamed) `SatEntry` helper so every read is self-freshening, but that's **overkill** — refreshing
  once at the top of each iteration (multi-vote) is sufficient and cheaper (the helper can stay a plain
  getter).
- **Binding resolved per-entry** (Dean, 2026-08-03). The anchor is a *list* of per-variant entries,
  each with its own `Role` — so per (role, variant) binding ([§ combine](#combine)) drops in
  naturally: each entry independently holds its binding analyzer's PRC/coverage. No model-global
  binding assumption anywhere.
- **Anchor population by active-vote set** (Dean, 2026-08-03) — three cases, only one dynamic. In all
  three the anchor's **(a)** is sat-v2's, unchanged; the cases differ only in whose **(b)** lands on the
  anchor and whether the optimizer refreshes it:
  - **sat-v2 vote only (default, one vote):** anchor (a) = sat-v2, anchor (b) = sat-v2's; one ballot
    entry ⇒ no refresh. The anchor is **static** and equals today's `SatEntry` renamed → byte-identical
    by construction ([§ invariants](#invariants) #7).
  - **TA vote only (one vote, TA):** sat-v2's *vote* is disabled and off the ballot, so the first (and
    only) ballot entry is TA: anchor (b) = TA's, **as-is**; one entry ⇒ no refresh; **static all the
    way**. Anchor (a) is **still sat-v2's** — sat-v2 the *analyzer* always runs and always produces the
    common metadata (see the F1 note), so a TA-only anchor keeps full topology/cost; TA never needs to
    produce (a).
  - **both votes:** anchor (a) = sat-v2's, then the optimizer refreshes the anchor's **(b)**
    **dynamically** with `argmax_i rd_i` per (role, variant), each iteration. This is the only case that
    runs the per-iteration refresh.
  Consequence — **a clean risk gradient:** the dynamic per-iteration (b) refresh (the most novel code)
  is reached *only* when two votes are active; both single-vote configs set the anchor's (b) once and
  never refresh. Default = static = identical; TA-only = static + simple; both = dynamic + most opt-in.
- **sat-v2 always runs and always produces the metadata ⇒ F1 is not needed here** (Dean, 2026-08-03).
  You **always pay** to run sat-v2 the *analyzer* (it is never skipped) — but running it and *voting*
  are separate: TA-only disables sat-v2's vote yet still runs it. TA is an **independent producer**
  consuming the same raw `AnalyzerInput`; sat-v2 must still run because its `Result` is the **carrier**
  of the anchor's topology metadata (accel/cost/role/replica-count) — not because TA reads sat-v2's
  output. There is **no analyzer-ordering constraint**. Consequence: F1
  "pre-analysis extraction" (`multi-analyzer-design.md:506-511`) is **not a prerequisite and not a
  cost saver** here — the metadata is always present because sat-v2 always runs. Both "TA alongside"
  and "TA replacing the sat-v2 *vote*" are in scope; neither removes the sat-v2 *run*.

**Why this is attractive:** it localizes the change to the engine's one-line (b) copy onto the anchor
and the optimizer's multi-vote (b) refresh — the dozens of downstream read sites are untouched (they
just read the anchor). It also makes the (a) metadata-carrier / (b) vote split fall out naturally (the
anchor carries (a) plus the binding (b); every vote is an ordinary ballot entry contributing its (b)).

**Resolved risk (was: "resolve before locking"; closed [§ open](#open) #1).** "Always the binding
analyzer" is per `(role, v)` and per-iteration. A single scalar `PerReplicaCapacity` on one anchor
entry can only hold one variant's binding PRC at a time; the anchor is a *list* of `VariantCapacity`
(one per variant), so per-variant binding PRC fits — and the *cost-sort* needs the binding analyzer
that would apply *at that variant's marginal replica*, which is exactly what the per-iteration refresh
provides. **Resolved:** the sort is already re-run once per (role, iteration) inside the pick closure,
so the per-iteration refresh feeds it directly — no separate sort-time binding resolution is needed
([§ open](#open) #1, [§ sort](#sort) "Sort cadence").

### The two-phase mechanism {#anchor-twophase}

*(Migrated here from `ta-anchor-refactor-review.md` Part 2, which superseded the stored-`Anchor`-field
design on 2026-08-05. This is now the design of record; the review doc is the source trace.)*

**Phase 1 — the engine builds a ballot and makes no decisions.** `runAnalyzersAndScore` tags every
ballot entry with `Enabled` (alongside the existing `Live`) and stops there. It does not pick a
binder, does not merge anything, and does not prune. Its output is the full, uninterpreted
enabled-analyzer list plus every analyzer's own `Result`.

**Phase 2 — the anchor is derived on demand.** `bindingAnchor` (successor to `saturationEntry`)
builds a fresh `*AnalyzerResult` at each read site, by a **per-variant merge keyed by `VariantName`**:

1. **(a) identity** — from saturation's entry for that `VariantName`.
2. **(b) sizing** — from the **binding** analyzer's entry for that same `VariantName`.
3. **per-variant fallback** — for a variant the binding analyzer omits, saturation's own (b) is used
   as the sizing source, **only when saturation is enabled**. *(This gate is what `N8` recommends
   removing outright — see [§ findings](#findings).)*

`bindingAnchor` reads the **full** ballot, before any non-voting entry is pruned, because the (a)
identity carrier must survive even when saturation is non-voting. Nothing is stored on the request:
the anchor is recomputed at each read site rather than materialized once. The end state is unchanged
— **anchor = (a) + (b, the binding analyzer's); ballot = (b) per analyzer** — only the
materialization differs.

**Four bounded decisions that come with the mechanism:**

| Decision | Resolution |
|---|---|
| the QM optimize path | **explicit error**, never a silent sat-v2 fallthrough ([§ configs](#configs), [§ findings](#findings) `N6`) |
| liveness / failure policy | scale-down stays `Live`-gated; scale-up's `Enabled`-only prune is the `VG-up` gap |
| `AnalyzerName` validation | out of scope here — a separate change |
| scale-from-zero | does **not** go through the anchor; the reactive engine owns cold-start ([§ findings](#findings) `N9`) |

[↑ TOC](#toc)

### What the anchor is a workaround for {#anchor-completeness}

The anchor exists because a non-sat ballot entry is **not self-describing**: it carries (b) sizing but
neither (a) identity nor necessarily the full variant list. Two **completeness properties** would make
the merge unnecessary:

1. **(a)-completeness** — every voting analyzer emits its own `AcceleratorName` / `Cost` / `Role` /
   `ReplicaCount` per variant.
2. **variant-list completeness** — every voting analyzer emits a `VariantCapacity` for **every**
   variant of the model, even if only with a no-data reason.

**Two purposes, only one of which needs a PRC.** The anchor's `VariantCapacities` is the optimizer's
**roster** — iterated by scale-down (`safeRemovalReplicasForRole`, `needsScaleDownForRole`), by
current-GPU accounting (`modelCurrentGPUs` / `roleCurrentGPUs`), and by cost/replica bookkeeping. A
**currently-live** variant the binder does not size must still appear, with identity and
`ReplicaCount`, or the optimizer is blind to a running variant it may need to shed. **That purpose
needs no PRC — `PRC = 0` is fine.** Only the *sizing / proactive-from-zero* purpose needs a real PRC,
and that is exactly the (b)-fallback. So variant-list completeness is needed broadly for
identity/accounting while the (b)-fallback is the only from-zero-flavored part — which is why
dropping the fallback is safe for accounting and simultaneously fixes a metric-scale mix.

> **Design rule (Dean, 2026-08-06): when TA binds, every *sized* entry is TA's.** A binder-unknown
> variant keeps identity (a) but gets **`PRC = 0` (abstain)** — never saturation's rejected (b). This
> holds for the partial-from-zero case too: a partially-cold TA-bound model sizes only the variants TA
> can size; the rest abstain and are woken, if at all, by the reactive engine, not by borrowing
> saturation's sizing.

**What collapses once both properties hold.** The per-variant merge loop, the enablement-gated
fallback, and saturation's special-casing as (a)-carrier all disappear: `bindingAnchor` degenerates to
"take the binding analyzer's own result," identity is no longer single-sourced from saturation, and a
`[TA]`-only config needs no saturation entry at all.

**Anchor-deletion gate.** The anchor is deletable once both completeness properties are enforced
**and** `RoleCapacities` decomposition is uniform across voters. Until then it stays as the topology
carrier.

[↑ TOC](#toc)

### Multi-vote semantics that must be pinned down {#anchor-multivote}

Three properties are latent while at most one non-sat analyzer can vote, and become live the moment
multiple voters are admitted. The first two are **rules, not observations** — a task plan may build on
them:

- **Binder tie-break — RULE: lowest analyzer index.** *(Dean-confirmed 2026-08-07.)* The current
  "more than one qualifying non-sat binder ⇒ return nil ⇒ hold" behavior becomes a live hazard the
  moment two healthy voters can qualify: it would silently freeze the model every cycle. Anything
  deterministic suffices, and index order is deterministic — so no saturation-first special case is
  warranted. The rationale for keeping it that simple: **the tie is rare, its scope is a single
  analysis, and the ballot is fixed within an analysis** — per-iteration refresh re-reads each
  entry's spare/remaining values, not the analyzer list, so index order cannot shift mid-water-fill
  and the binding cannot oscillate. See [§ findings](#findings) `N2`.
- **Abstain, don't veto — RULE: a voter with no opinion on role `R` abstains on `R`** (excluded from
  that role's spare test), rather than vetoing it. Today a map-miss reads as `0.0` spare and therefore
  as a veto, so a live coarser-grained voter permanently blocks per-role scale-down for a P/D model.
  *(Dean-confirmed 2026-08-06.)* Note the residual: abstaining means the role's scale-down is decided
  by a **subset** of live voters, so "every live voter agrees there is spare" weakens to "every voter
  **with an opinion** agrees". That is the intended reading — a voter that cannot see a role has no
  standing to block it — but it is a genuine weakening of the veto and should be stated in the
  reference docs rather than left implicit. See [§ findings](#findings) `N7`.
- **Liveness symmetry.** Scale-up's prune must reach `Enabled && Live` parity with scale-down's
  explicit `Live` guards, establishing the invariant **"a non-nil anchor ⟹ a non-empty voting set"**
  (the binder itself satisfies `Enabled && Live && Informative`). Degradation is then correct by
  construction: an empty voting set ⇒ nil anchor ⇒ **hold**, never an unguarded scale-down. See
  [§ configs](#configs) and [§ findings](#findings) `VG-up` / `VG-fallback`.

[↑ TOC](#toc)

## Current code: the two-PRC split and every saturation-only site {#trace}

> **Currency caveat.** This section, [§ rescale](#rescale) and [§ limited](#limited) were written
> against the **pre-refactor** tree (2026-08-02/03). They are retained as an **inventory of sites and
> of the pattern**, which is still accurate; the `file.go:N` line numbers are **not** — several have moved by
> hundreds of lines and at least one function has been renamed or absorbed (`saturationEntry` →
> `bindingAnchor`, `bindingIndexForRole` → `combineVotes`). Resolve every citation **by function
> name**. Do not use these two sections as a current line map, and do not "fix" a number here without
> re-verifying the whole section against a named revision.

Two distinct "PRC" notions run through the code:

- **per-analyzer PRC_i[v]** — each analyzer's own `PerReplicaCapacity`, correctly combined by the
  bottleneck/min-removal helpers. **Right.**
- **topology PRC_sat[v]** — saturation's `PerReplicaCapacity`, read off the carrier and used
  **saturation-only** in sorting / sizing / utilization write-back. **Wrong under multi-analyzer.**

Enumerated saturation-only sites (each should read the **combined / binding** value via the anchor
per [§ anchor](#anchor)):

**Optimizer — `cost_aware_optimizer.go`:**
- `costEfficiency` (`:234`) = `Cost / PerReplicaCapacity` → uses PRC_sat. Should use binding PRC.
- `buildCapacityMap` (`:206`) / `sortByCostEfficiencyAsc` (`:224`) — feed the cost sort with PRC_sat.
- `decision.Utilization = vc.Utilization` (`:302`) — writes saturation's utilization. Should be
  combined coverage's flip-side (min-coverage / binding).
- `sortVariantsForScaleDown` (`:161`) — Cost-desc, tie-break `Σ_i Score_i·prcForVariant(Result,name)`
  is **per-analyzer** (`:` uses each entry's own Result) → **already OK**.

**Optimizer — `greedy_score_optimizer.go`:**
- `fairShareRolePick` (`:396`) `fairShareCap = ceil(target / vc.PerReplicaCapacity)` → PRC_sat.
  Limited-mode; see [§ limited](#limited).
- `prcFromVCs` (`:469`), `accFromVCs` (`:479`), `gpusPerReplicaFromState` (`:489`, returns 1
  fallback) — helpers that read carrier PRC.

**Optimizer — `analyzer_helpers.go`:**
- `saturationEntry` (`:91`) — the by-name carrier lookup. Becomes the renamed anchor.
- `applyAllocation` (`:71`) — decrements each analyzer's `Remaining` by `n·prcForVariant(s[i].Result, v)`
  = **per-analyzer PRC** → **already OK**.
- `initRoleState` (`:127`) — `pickerState[i][role]` = RC in analyzer's own units → **OK**.
- `roleBottleneckReplicas` (`:182`) — `max_i ceil(state[i][role]/PRC_i[v])` → **correct combine**.
- `roleAggRemaining` (`:201`) — `max_i state[i][role]` over **raw** RequiredCapacity in mixed units
  → **BUG** (see [§ bugs](#bugs)).
- `safeRemovalReplicasForRole` (`:246`) — `min_i floor(RoleSpare_i/PRC_i[v])` over live → **OK**.
- `needsScaleDownForRole` (`:301`) — all live analyzers `RoleSpare>0` → **OK**.
- `allocateForModelPaired` (`:333`) — the joint-commit loop; `utilByRole`, `k`, and the pickerState
  decrement use topology PRC_sat uniformly across all `i` → **latent unit-mismatch BUG** (masked
  today; see [§ bugs](#bugs)).

**Engine — `engine_v2.go`:**
- `computeCurrentGPUUsage` (`:489`) / `computeCurrentGPUUsageByNamespace` (`:523`) — find the
  saturation entry by name and read `VariantCapacities` for GPU accounting. This is *topology*
  (replica count × gpus/replica), legitimately carrier-scoped → stays on the anchor's topology
  fields, unaffected by the vote-split.
- `runAnalyzersAndScore` (`:150-177`) — saturation always prepended; non-sat analyzers appended
  only when `effectiveEnabled`. This is the site that builds the two copies under the new design:
  common-scope anchor always; sat-v2 vote entry only when enabled.

[↑ TOC](#toc)

## Latent bugs surfaced by the trace {#bugs}

All **masked today** because saturation is the only running analyzer (so PRC_sat == the only PRC,
and unit-mixing across analyzers can't manifest). They become real the moment a second analyzer is
active — i.e. exactly what enabling/disabling other analyzers will do.

1. **`allocateForModelPaired` unit-mismatch** (`analyzer_helpers.go:366-413`). The loop computes
   `utilByRole = n·prc/demand`, `deltaUtil = min_role`, `k = floor(deltaUtil·demand/prc)` and then
   `pickerState[i][role] -= k·prc` for **all** `i`, where `prc = prcFromVCs(variants, v)` = topology
   PRC_sat. But `roleBottleneckReplicas` reads `pickerState[i]/PRC_i`. Decrementing every analyzer's
   state by `k·PRC_sat` while later dividing by `PRC_i` mixes units for `i ≠ saturation`. Fix falls
   out of the abstraction: decrement in **replica units** (`k` replicas) or per-analyzer
   `k·PRC_i`, not `k·PRC_sat` uniformly.

2. **`roleAggRemaining` unit-mixing** (`:201`). `max_i state[i][role]` maxes raw `RequiredCapacity`
   across analyzers whose units differ (saturation = tokens, throughput = request-rate). Maxing
   tokens against req/s is meaningless. Fix: compare in replica space (`max_i rd_i`), i.e. this
   should be `roleBottleneckReplicas`-style, not raw-capacity max.

3. **Rescale water-fill weight incommensurability** (`rescale.go:521`, `Demand: satEntry.TotalDemand`).
   The weight `priority × demand` "unit cancels in the ratio" only when every model is bound by the
   *same* analyzer/unit. Across models bound by different analyzers, the weights are incommensurable.
   Fix: weight by combined demand-in-GPUs (or replicas). See [§ rescale](#rescale).

4. **Anticipated-supply in the denominator — TRACED 2026-08-03; NOT an active *sizing* bug** (the
   coordination doc's suspicion does **not** hold in the V2 paired path — corrected here after a
   full trace).
   - **The scale-up sizing is pending-correct.** `applyUniversalThreshold` computes
     `RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)` (`engine_v2.go:453`), and
     `TotalAnticipatedSupply = Σ_v (ReplicaCount + PendingReplicas)·PRC` = **current + pending**
     (`aggregation.go:81`). So `RC = demand_target − current − pending` — the correct *remaining*
     demand. The gate `anyRoleNeedsScaleUp(ps)` (`cost_aware_optimizer.go:61`) fires only when
     `RC > 0`; the loop covers `RC` with new replicas so `target = current + RC/PRC = desired − pending`.
     Pending is accounted for exactly once, in the right place.
   - **No code ever divides *by* RC/`Remaining`.** RC is an absolute remaining quantity, held in
     `pickerState` and decremented directly (`analyzer_helpers.go:142/148/413`); it is never a
     denominator. So the specific "`current / (demand − anticipated)`" shape the coordination doc
     hypothesized **does not exist** in code.
   - **What *is* pending-blind is the observability `Utilization`** — `TotalDemand/TotalSupply`
     model-level (`saturation_v2/analyzer.go:115`) and `totalDemand/totalCapacity` per-variant
     (`:438`), both `demand / current-supply` (no pending, and raw demand not `demand_target`). This
     is a *reporting* ratio only in the V2 path (feeds the three saturation gauges + `decision.Utilization`
     at `cost_aware_optimizer.go:302`); it does **not** gate or size scaling. Its symptom: the gauge
     can read "saturated" (`>threshold`) while `RC = 0` (pending covers it) → looks like the analyzer
     wants to scale while no scale is emitted. Cosmetic/observability inconsistency, not a scaling error.
   - **Net (Dean, 2026-08-03 asked to re-confirm):** the earlier "CONFIRMED bug" verdict is
     **downgraded**. The clean `achieved = (current+anticipated)/demand_target` model is still the
     right *conceptual* target for the coordination-doc rewrite, and the observability `Utilization`
     should be reconciled to it — but there is no anticipated-in-denominator *scaling* bug to fix in
     the paired pipeline. Coordination doc **D1 / Open-issue #2**
     ([`optimizer-coordination-design.md`](optimizer-coordination-design.md)) should be updated to
     reflect this trace (suspicion not borne out; residual is the observability metric).

5. **`fairShareValue` sums across analyzers instead of maxing — the fair-share currency pivot,
   FIVE lock-step sites** (limited/fair-share mode only; the cost-aware unlimited path does not use
   fsv). `fsv = priority × Σ_i Score_i × Σ_role ps[i][role]` is a cross-analyzer combine that uses
   `Σ_i` where the binding rule uses `max_i`. Two independent errors: (a) `ps[i][role]` is
   per-analyzer native-unit RC → the `Σ_i` is dimensionally mixed (same root as #2); (b) even in
   common units, summing over-counts vs the binding `max_i` and misorders models.

   **The currency pivot.** The fix is not local: it changes the unit `fsv` (and therefore `mean`,
   `target`, and every comparison built on them) is denominated in, away from *mixed analyzer-private
   capacity*. Because the unit changes, every site that produces or consumes that number must move in
   the **same commit** or the units desync silently — five sites, not one.

   > **DECIDED 2026-08-07 (Dean): the target currency is GPUs, not replicas.** The five-site
   > *structure* below is unchanged and remains the specification of *which* sites move together; the
   > *currency* is GPUs. Where a site's formula below names a replica count or a PRC-based factor,
   > read the GPU-space factor from this block.
   >
   > - **Why GPUs.** `Σ_role` is legal in GPU space and illegal in both metric and replica space
   >   ([§ units-rules](#units-rules) `R3b`). A replica-space pivot fixes the analyzer-mixing and
   >   **introduces** a role-mixing violation in its place; a GPU-space pivot fixes both at once
   >   ([§ units-roles](#units-roles)). GPUs are also what is actually rationed, so the budget finally
   >   denominates in the resource it is a share of.
   > - **What disappears.** The `prcRef` machinery of site (ii) — the copied value map, the
   >   capture-before-refresh requirement, the "do not re-derive in the closure" grep step — **stops
   >   existing** rather than getting solved: in GPU space the spend-time factor is `GPUsPerReplica`,
   >   immutable deployment topology, so [§ invariants](#invariants) #9's drift hazard cannot arise
   >   here. The cap becomes a whole-replica fill against `GPUsPerReplica`, per
   >   [§ units-integral](#units-integral) — **not** a division-and-round.
   > - **What survives.** The reference-variant approximation in the numerator (one role's demand
   >   converted through one variant's PRC and `GPUsPerReplica`), now the *same* approximation
   >   `roleDemandGPUs` already makes — one weakness in one class rather than two.
   > - **Sat-only exposure: no new class.** GPU space adds no sat-only risk beyond the ordering change
   >   [§ limited](#limited) already concedes; it adds a `GPUsPerReplica` factor to that same
   >   ordering. Dean's instruction is explicit: *"if sat-only needs fixing too we have to fix it
   >   now"* — so the sat-only path is fixed in this commit rather than deferred, and the sat-only
   >   fixture must **vary `GPUsPerReplica`** across the two models or it cannot detect the factor at
   >   all.
   > - **Not covered by this decision, but since ANSWERED separately:** whether one model should have a
   >   *single* cross-role budget at all ([§ open](#open) `W1`) and the `priority` leak (`W2` / `U4`).
   >   Both were answered by Dean on 2026-08-07 and both are **behavior changes that do not belong in
   >   this conversion commit** — `W1` makes role spend a joint debit against one model-level GPU
   >   balance, `W2` removes `priority` from the claim. This commit stays status-quo-preserving in both
   >   respects; the two changes land separately (queue in [§ open](#open)). Where a site's formula
   >   below still shows `priority ×` or a shared-`target` spend, that is **deliberately** today's
   >   behavior in the new currency, not a prescription for the end state.
   >
   > The task plan's per-site formulas are refreshed from this block, not the reverse.

   - **(i) `fairShareValue`** — replace `Σ_i Score_i × Σ_role ps[i][role]` with a combined
     replica-space quantity, `priority × Σ_role (max_i rd_i[role] − current[role])`. **Score leaves
     `fsv` entirely** — it is a belief weight, not a budget weight ([§ combine](#combine-score)); the
     earlier hedge "× Score only if Score is meant to weight budget" is **withdrawn**. Computing
     `rd_i` needs a per-role reference variant, which `fairShareValue` does not receive today, so the
     signature gains the variant list. *This is where the anchor helps* — it already holds
     `max_i rd_i` per role, so the numerator is a read rather than a re-derivation. Contrast the
     earlier note "the anchor does not reach fsv": true *as fsv is written today* (it walks `ps`), and
     the fix is precisely to re-point it.

     > **`priority` follows `Score` out — later, not here (`W2`, decided 2026-08-07).** The end-state
     > formula is `Σ_role (max_i rd_i[role] − current[role])` with **no leading `priority`**: the same
     > argument that evicted `Score` ("a belief weight is not a budget weight") applies verbatim to
     > `priority` ("a rank is not a budget weight"). The `priority ×` shown above is retained **only**
     > because removing it changes allocations, which this conversion commit must not do. Two numbers
     > exist in the end state — the unweighted **claim** (spent) and the ordering key `priority × claim`
     > (compared, never spent) — and only `sortByRemainingDesc` may read the second.

     > **Naming.** With `priority` gone from the quantity, "fair-share *value*" no longer describes
     > what this returns. It returns a **claim in GPUs**. Renaming is optional and cosmetic, but if the
     > coder does rename, the [§ units-rules](#units-rules) `R6` grep terms in the task plan move with
     > it — call it out in the handoff rather than doing it silently.
   - **(ii) `fairShareRolePick` → `fairShareCap`** — today `ceil(target / vc.PerReplicaCapacity)`
     divides the fsv-unit `target` (`= w.remaining − mean`) by the anchor's PRC. Once `target` is
     replicas this division is a **double conversion** — but the correct replacement is **not** a bare
     `ceil(target)`. `target` was denominated by dividing by *the role's reference* PRC, so converting
     it back for a *different* candidate must rescale through the same reference (the round-trip rule,
     [§ units](#units-conversions)):

     ```
     fairShareCap = ceil( target · PRC_ref[role] / PRC_vc )
     ```

     For the candidate that *is* the reference this reduces to `ceil(target)`; for any other candidate
     it rescales, and it is **exact per candidate** — `ceil((d/P_ref)·P_ref/P_vc) = ceil(d/P_vc)`.
     `PRC_ref[role]` must be **captured** as a copied value map at denomination time, never
     re-derived at spend time: the anchor's sizing is rewritten in place between the two moments, so
     re-derivation drifts in value *and* in identity (PRC feeds `costEfficiency`, which reorders the
     cost sort that chooses "the cheapest variant"). **A bare `ceil(target)` here silently rescales
     every non-reference candidate's cap by `PRC_ref/PRC_vc`.**

     > **⚠ SUPERSEDED by the GPU decision above — retained as the derivation only.** In GPU space the
     > entire formula, the `PRC_ref` value map, and the capture-before-refresh ordering rule **stop
     > existing**. What replaces them:
     >
     > ```
     > fairShareCap = floor( remaining_GPUs / GPUsPerReplica[vc] )     // whole-replica fill
     > capN         = min( fairShareCap, gpusAvail / GPUsPerReplica[vc] )
     > ```
     >
     > `GPUsPerReplica` is deployment topology and is never rewritten mid-cycle, so there is no
     > round-trip and no drift hazard — invariant #9 does not apply here at all. Note **`floor`, not
     > `ceil`**: this is a budget, and a partial replica is not affordable ([§ units-integral](#units-integral)).
     > `ceil` was the pre-existing rounding and over-grants by up to one replica at every boundary;
     > changing it is a **one-replica behavior change at the boundary** and needs a fixture that lands
     > mid-replica, or it will not be observed. Flag it in the commit message — it is the one place the
     > conversion is not value-neutral.
     >
     > `remaining_GPUs` is the model's balance, decremented as each role spends (`W1`) — not a fresh
     > copy of `target` per role. That decrement is the `W1` behavior change and lands separately; until
     > it does, this reads `target` per role exactly as today.
   - **(iii) scale-down tie-break `sortVariantsForScaleDown`** — a **second** `Σ_i Score_i × PRC_i[v]`
     site. Lower severity: it only orders scale-down candidates within a role (a tie-break), never
     sizes; but it is the same wrong-operator/mixed-unit pattern. Fix: tie-break on the *binder's* PRC
     (which requires the function to learn which role it is ordering), name-ascending as the final
     key, and give a variant with no scale-down ballot at all the same key today's weighted sum yields
     for that input, so that edge does not move.

     > **The unit of this key is dimensionless — coverage per GPU freed** ([§ open](#open) `W5` row 7).
     > Scale-down ordering asks "which removal costs the least coverage per GPU it returns to the pool",
     > which is a ratio of two like quantities and therefore has no unit. Two consequences: it is
     > **never spent** (it is a comparator input only, like the `W2` ordering key), and it must combine
     > across analyzers with **`max_i`, not `Σ_i`** — the current `Σ_i Score_i · prcForVariant(…)` sums
     > raw PRCs across analyzers, i.e. it adds KV tokens to req/s, which is the same defect as site (i)
     > in a place where it only misorders rather than missizes.
   - **(iv) the picker-state clamp in `allocateForModel`** — it clamps `ps[i][role]` (raw
     analyzer-private capacity) against `target` (now replicas). Clamping capacity against a replica
     count *is* the bug. The cheap correct shape converts the **bound** into each analyzer's own
     units rather than moving `ps` into replica space:

     ```
     if cap := target * PRC_i[v_role]; ps[i][role] > cap { ps[i][role] = cap }
     ```

     `ps` stays raw capacity, which is what every downstream consumer expects
     (`roleBottleneckReplicas` divides by `PRC_i`; `allocateForModelPaired` and
     `applyDeallocationForRole` decrement in capacity). Making `ps` itself replica-space would instead
     ripple through `initRoleState`, `roleBottleneckReplicas`, `allocateForModelPaired` and
     `applyDeallocationForRole`.

     > **✏️ CORRECTED 2026-08-07 (Dean, `W4`).** This site previously read: *"An analyzer with **no
     > PRC** for the reference variant is left **unclamped**: no conversion factor exists, zeroing it
     > would delete its vote, and it cannot participate in the picker for that variant anyway — so the
     > un-enforced budget is harmless."* That is **withdrawn**. Dean, verbatim: *"you should not be able
     > to exceed budget even if you don't know the price of an item."*
     >
     > The rule is **no conversion factor ⇒ no spend**: such an entry contributes nothing for that
     > variant — not to the claim, not to the pick. It abstains rather than being exempted. The
     > "harmless" reading rested on `votesFromPickerState`'s independent `prc <= 0` filter happening to
     > exclude the same entry; that made the outcome right and the reasoning wrong, and it would break
     > silently the moment either filter is edited. See [§ open](#open) `W4` for the rule and its test.
     >
     > Practically, the observable behavior today is close to what the rule prescribes, so this is
     > mostly a **statement** change — but it is the statement that a future edit gets checked against,
     > which is the entire point of writing it down once.

     > **Correction 2026-08-07 — the sat-only inertness argument does not hold.** The argument that
     > this clamp is inert in a `[sat]`-only config because the bound is `≥` the role's own demand
     > relies on `target` being a **sum over roles** of quantities that may be added — i.e. on exactly
     > the step [§ units-roles](#units-roles) now forbids. With one analyzer and one role the clamp is
     > inert for the trivial reason that the bound equals the demand; with **two roles** the
     > cross-role sum is what makes the bound comfortably large, and that sum is not a legal
     > quantity in metric or replica space. So: `[sat]`-only **single-role** inertness stands;
     > `[sat]`-only **P/D** inertness is not established by that argument and must not be asserted
     > on it. The conversion factor here is each analyzer's *own* `Result` PRC, which is never
     > rewritten in place, so this site has no round-trip hazard in either currency.
   - **(v) `fairShareValue`'s zero-result fallback** — when the weighted result is zero, `fsv`
     returns `max_{i,role} ps[i][role]`: raw remaining demand in an analyzer-private unit. Two things
     follow from the pivot. Its trigger **narrows** (with Score gone, only a non-positive `priority`
     can reach it); and left as-is it **defeats** the rule that fsv counts only demand it has a PRC to
     convert — a model whose demand is *entirely* unactionable computes `0`, drops into the fallback,
     and gets the raw inflated number back. Fix: return the unweighted **replica-space** demand, which
     is `0` when nothing participates. That preserves the fallback's real purpose — a mis-configured
     priority should not silently strand a model that genuinely needs replicas, since `fsv = 0`
     excludes it from the active set and it is then never allocated at all.

     > **✏️ SUPERSEDED 2026-08-07 (`W2` + `W3`): this fallback is DEAD CODE — delete it, do not
     > re-denominate it.** The prescription above ("return the unweighted demand") was written while
     > `W2` was open. With `W2` answered, `priority` is no longer a factor in the claim, so **no
     > priority value can drive the weighted result to zero** — and `Score` had already left (site (i)).
     > The branch's last remaining trigger is a genuinely zero claim, and for that case `0` is the
     > **correct answer**, not a condition to paper over: a model no analyzer can size claims nothing
     > and is properly excluded from the active set. The original worry — "a mis-configured priority
     > should not strand a model" — is answered upstream instead, by `W3`: explicit `priority: 0` means
     > *last in line*, not *claim nothing*, so such a model is never stranded in the first place.
     >
     > Sequencing: the deletion depends on `W2` having landed. Until then the branch is still reachable
     > and must keep working in the new currency, so the conversion commit converts it and the later
     > `W2` commit deletes it. Classification for the coder's handoff: **DEPRECATED** — *"priority-zero
     > fallback in `fairShareValue` — removed; `priority` no longer scales the claim, so the branch is
     > unreachable, and a zero claim is the correct output rather than a condition to substitute a
     > manufactured one for."*

   **Multi-role (P/D) divergence, made visible by the fix but not caused by it.** `target` is a
   **scalar** summed over roles, while the cap is applied **per role**. So the per-role cap is already
   cross-role contaminated: today it is `ceil((Σ_role' d_role') / PRC_vc)`, and after the fix
   `ceil((Σ_role' d_role' · PRC_ref[role] / PRC_ref[role']) / PRC_vc)`. The two agree **iff all
   per-role reference PRCs are equal**. How the fair-share budget should treat roles was `W1`, **now
   answered** (see the block below) — but the fix must still not be read as *implementing* that answer.
   Note that fixtures which give prefill and decode the *same* reference PRC cannot distinguish the two
   forms, so coverage there is coincidental, not deliberate.

   **In GPU space this paragraph changes character.** The cross-role sum stops being a *unit* error
   (GPUs are additive across roles, `R3b`) and becomes purely a **policy** question — and that question
   is now **answered**. The equal-reference-PRC caveat above becomes an equal-`GPUsPerReplica` caveat,
   and fixtures must vary it for the same reason.

   > **`W1` ANSWERED 2026-08-07 (Dean): one entitlement per model, spent jointly across its roles.**
   > Neither "a single scalar with role erased" (today) nor "one budget per role" — see [§ open](#open)
   > `W1` for the derivation. The consequence for this paragraph is that **both** current spend sites
   > are defects, not merely mis-united:
   >
   > | Site | Today | Under `W1` |
   > |---|---|---|
   > | (ii) cap | every role is handed the same whole-model `target` | each role sizes against the **remaining** balance |
   > | (iv) clamp | each `(analyzer, role)` clamps against the **full** `target` independently | `Σ_role spend ≤ target` — a **double-spend** today, in a P/D model |
   >
   > What currently prevents a real over-allocation is the downstream GPU-pool check
   > (`min(fairShareCap, gpusAvail/gpusPerReplica)`): the **pool** is enforced, the **fair share** is
   > not. Same shape as `W4` — safety by a second mechanism, not by the rule.
   >
   > This is a **behavior change** and is therefore **not** part of this conversion commit. It also
   > **requires** GPU space to state at all: `Σ_role spend ≤ budget` is well-formed only where roles
   > share a currency (invariant 10) — a third thing the pivot unlocks, alongside `R3` and `U1`. It
   > makes `fairShareRolePick`'s `_ = roles` placeholder live, though what it needs is a **sequenced
   > draw** against one balance, not the static per-role *split* that comment anticipates.

   **`priority` leaks into the cap, and the fix makes the leak newly misleading.** `target =
   remaining − mean` and `remaining = priority × demand`, so `ceil(target)` is a **priority-scaled**
   replica count, not a replica count. This is pre-existing and unchanged by the fix (today's
   `target / PRC` is equally priority-scaled, so the number moves identically) — but after the fix the
   expression *reads* like a replica count. The currency pivot does not touch this leak in either
   space, so within **this commit** naming it accurately remains the whole obligation: the honest
   description is "priority-scaled replicas" — or, in GPU space, "priority-scaled GPUs".

   > **`W2` ANSWERED 2026-08-07 (Dean): priority orders, it never scales an entitlement.** So the leak
   > is no longer something to name and live with — it is a **defect to remove**, in its own commit. The
   > claim becomes unweighted; `priority × claim` survives **only** as `sortByRemainingDesc`'s
   > comparator input, never as a quantity. Knock-ons: `computeMean` averages unweighted claims (today
   > one high-priority model shifts every other model's `target` — a scarcity signal leaking out of a
   > ranking); site (v)'s deliberate `priority` drop turns out to have been *right*, and then becomes
   > dead; and [§ unit-findings](#unit-findings) `U4` is **no longer a surviving `R4` violation** but a
   > scheduled fix. See [§ open](#open) `W2` and [§ invariants](#invariants) invariant 11.

[↑ TOC](#toc)

## Traced findings: liveness, binding and role coverage {#findings}

**Provenance.** These findings were produced by a code-level data-flow trace of the shipped anchor
mechanism (reviewer, 2026-08-06) and were **migrated here from that trace's §9**. The trace is a
*source of evidence* — a route back to the code paths and the reasoning — but it is **not the design of
record**: this section is. Where the two ever disagree, this section governs, and the disagreement is a
bug in one of them to be fixed rather than reconciled in the reader's head. Identifiers `N1`–`N9` are
kept because they are the trace's own labels and cheaper to keep than to renumber; `VG-up` and
`VG-fallback` are the two liveness gaps named in [§ configs](#configs).

The distinction that organizes the whole set: **scale-down is enforced-safe, scale-up is only
emergently safe.** Every scale-down path filters on `Live`. No scale-up path does — scale-up's safety
rests on the *empirical* property that a dead analyzer's `RequiredCapacity` is `0`, which is true of
both analyzers today and is not a contract. That asymmetry is the root of `VG-up`, and it is why "a
dead analyzer causes no spurious scaling today" is a correct statement about today and a fragile one
about tomorrow.

| ID | What it is | Class | Disposition |
|---|---|---|---|
| **`VG-up`** | The combine's vote prune keeps entries on `Enabled` **alone** — no `Live` filter — and the scale-up bottleneck count then maxes over raw results. A stale-but-`Enabled` analyzer carrying `RC > 0` can force scale-up. | Latent hazard (not live today: dead ⇒ `RC = 0`) | Fix in the dynamic-refresh task: prune on `Enabled && Live`. Not a fix in the anchor task — deliberately deferred (see below). |
| **`VG-fallback`** | The (b)-sizing fallback is gated on saturation being `Enabled`, without `Live`, so an untrustworthy saturation can still supply sizing. | Latent hazard | **Superseded by `N8`** — the fallback is removed rather than gated. |
| **`N1`** | The (b)-fallback fires in `[sat,TA]`, **not** in `[TA]`-only. | Correction (it corrects an earlier review finding that had the configuration backwards) | Dissolved by `N8`. |
| **`N2`** | More than one non-saturation binder ⇒ the anchor derivation returns `nil` ⇒ the model **holds, silently and permanently**. Harmless while only one non-sat analyzer can bind; the multi-vote combine makes it reachable. | Design gap — needs a rule | **Open.** Requires a deterministic tie-break ([§ anchor](#anchor-multivote)). Must be decided in the dynamic-refresh task, not discovered by it. |
| **`N3`** | One rescale-layer call site dereferences the anchor with no local nil-guard while every sibling site guards; it is safe only because an upstream pre-filter drops nil-anchor models first. | Fragility, not a defect | Add the guard opportunistically; do not build on the pre-filter. |
| **`N4`** | `VG-fallback` does **not** reach the scale-up bottleneck count — that path reads each analyzer's own result, not the anchor. | Blast-radius narrowing | Records *why* `VG-fallback` is sizing-only. No action. |
| **`N5`** | Saturation reports `Cost = 0` for a zero-replica variant; the (a) identity merge propagates it to **all three configs**, and `costEfficiency = Cost / PRC = 0` then ranks that variant cheapest. | Real defect, **not** an anchor defect | Root fix is a **separate saturation bug**. `N8` removes only the *fallback* half of the exposure. File separately. |
| **`N6`** | The queueing-model analyzer is refused with an explicit error rather than silently mis-handled. | Deliberate scope boundary | DEFERRED, by design ([§ anchor](#anchor-twophase)). |
| **`N7`** | Voters that decompose roles differently permanently veto per-role scale-down: the veto requires every live voter to report positive spare for the role, and a map-miss reads as `0.0` spare — so a non-disaggregated voter, seeded only with a both-roles entry, vetoes forever. | Design gap — needs a rule | **Open.** Needs abstain-vs-veto semantics ([§ anchor](#anchor-multivote)). Failure mode is **stuck-high, not unsafe** — which is why it is a correctness-of-model issue rather than a safety one. |
| **`N8`** | **Drop the (b)-sizing fallback entirely** rather than `Live`-gate it. The fallback fires exactly when saturation is untrustworthy, so gating it is nearly vacuous; and mixing saturation's sizing into a TA-bound anchor mixes metric scales, which is the very error this design exists to remove. Abstain (`PRC = 0`) instead. | Design decision | **Adopted and landed** (dynamic-refresh task, the liveness-hardening commit) — dissolves `N1` and the fallback half of `N5`, and **revises** the enablement-gated-fallback decision recorded in the anchor task's plan. ⚠ **Dean 2026-08-07: "discuss further later — not blocking now"**, and separately *"was not blocking PR-1. Can't remember the details."* The code ships this way; the *design rationale* is not closed. See the restatement below. |
| **`N9`** | The reactive from-zero engine is a separate controller runnable, takes no budget limiter, and wakes **every** inactive variant rather than the cheapest. It is the only mechanism that wakes a fully-cold model under the saturation-only default. | Pre-existing, out of scope | Out of anchor scope entirely; relevant to any future cost/budget layer over from-zero. Under a TA binder it becomes the *only* admission path at all — see `FZ-admission`. |
| **`FZ-admission`** | A variant nobody has ever measured is admitted only when **saturation binds** — saturation seeds a zero-replica PRC analytically from the deployment spec, TA can only replay its own measurement. Under a TA binder the variant sits in the anchor at `PRC = 0` and every eligibility gate skips it, leaving only the reactive path (`N9`), which is late (model-level trigger) and unranked. | Real gap, **TA-CREATED** | **Adopted — folds into PR-2** (Dean, 2026-08-07). Verified at his request; not a borrow. Fix: a `PRC = 1` **admission sentinel** in the binder's own currency at the anchor's no-variant branch, gated on `ReplicaCount == 0`, tagged by its own `Reason`, plus a **one-replica target ceiling** at the three grant sites (which is what keeps it legal under `W4`). Mechanism and cap are **decided in the block below** — not left to the task plan. Retires the deferred partial from-zero picker as a separate item; the `N9` residual stays out of scope. |

**Why `VG-up` was deferred rather than fixed in the anchor task** (Dean, 2026-08-06). As shipped, a dead
analyzer causes no spurious scale-up *or* scale-down: scale-down is `Live`-filtered at both gates, and
scale-up sees `RC = 0` from a dead analyzer (or skips it entirely on the nil-result guard). Full
from-zero is driven by a *live* analyzer by construction. So the `Live` filter is **hardening**, not a
correctness fix — and it belongs with the multi-vote work that makes the hazard reachable, where it can
be tested against a genuinely multi-vote ballot instead of asserted. The caveat that must travel with
the deferral: scale-up safety is *emergent*, resting on "dead ⇒ `RC = 0`". **A future analyzer that
carries forward a stale-but-informative `RC > 0` with an aged timestamp breaks it silently** — no test
fails, the system just scales on stale belief.

**`N8` restated (Dean 2026-08-07: *"was not blocking PR-1. Can't remember the details"*).** Both halves
of that are right, and here is the detail, compactly. Nothing below is a new decision.

- **What the (b)-sizing fallback was.** When `bindingAnchor` merged (a) identity from saturation with
  (b) sizing from the binding analyzer, a variant the **binder** did not size fell back to
  **saturation's** sizing — gated on saturation being `Enabled`.
- **The choice.** Two ways to handle a stale saturation reaching that path: `Live`-gate the fallback, or
  drop it. **`N8` = drop it.** Two reasons: gating is nearly vacuous (the fallback fires precisely when
  saturation is *not* binding, i.e. when it is already the less trustworthy voter), and using
  saturation's PRC to size a TA-bound anchor **mixes metric scales** — KV tokens sizing a req/s
  decision — which is the exact error this whole design exists to remove. The replacement is to
  **abstain**: `PRC = 0`, no sizing, no vote for that variant. Same rule `W4` states generally: no
  conversion factor ⇒ no spend.
- **Why it did not block PR-1.** PR-1 shipped **opt-in** and its default config is `[sat]`-only, where
  saturation *is* the binder, so the fallback never fires. Reachable only in `[sat,TA]` with saturation
  enabled-but-not-binding — a config PR-1 does not turn on by itself.
- **Status.** Adopted and **landed** in the dynamic-refresh liveness-hardening commit (`952d2fff`).
  Dissolves `N1` and the fallback half of `N5`, and revises the enablement-gated-fallback decision
  recorded in the anchor task's plan.
- **~~The live question, for the later discussion.~~** — **CLOSED 2026-08-07 (Dean). Abstain is the
  answer, on principle, and no legitimate borrow site exists.** See the block below.

**`N8` CLOSED 2026-08-07 — abstain, and the borrow has nowhere to live** *(Dean: "can't vote if you have
no info. The binding anchor is for the code that uses the old satEntry not for actual scale voting —
live+enabled needed to vote not a fallback. Demand is per the whole anchor so whatever units it holds
should also be for any PRC.")*

Three principles, each of which independently kills the fallback:

1. **No info ⇒ no vote.** Abstaining is not a degraded answer, it is *the* answer. A fallback value is
   not a vote; it is a guess wearing a vote's clothes.
2. **The anchor is a compatibility shim, not a voting mechanism.** It exists to feed the code that used
   to read `satEntry`. Voting requires `Enabled && Live` at the ballot, which a borrowed value by
   definition does not have — so a borrowed value must never reach a vote.
3. **Unit closure within one anchor.** The anchor's model-level demand (`TotalDemand`, `RequiredCapacity`,
   `SpareCapacity`, `RoleCapacities`) comes from the **binder**
   (`analyzer_helpers.go:176-188`).
   Any PRC in the same anchor is the divisor for that demand, so it must be in the binder's metric.
   A borrowed saturation PRC is a different currency in the same fraction — the R6 violation, inside one
   struct.

*Principle 3 also bounds where a borrow could ever be legal: only code that uses PRC and never divides
demand by it.* Dean's question — where is that, is it partial-scale-from-zero? — has a checkable answer.
The full inventory of **anchor**-PRC consumers, verified at `d9f3b97e`:

| Consumer | Uses demand ÷ PRC? | Site |
|---|---|---|
| `fairShareCap = ceil(target / PRC)` | **yes** — the fair-share budget divided by PRC | `greedy_score_optimizer.go:411-423` |
| `costEfficiency = Cost / PRC` (via `sortByCostEfficiencyAsc`, used by both `costGreedyRolePick` and rescale's fill) | **no** — pure ranking key | `cost_aware_optimizer.go:228-243`, `rescale.go:572` |
| `PRC <= 0 { continue }` eligibility gates | **no** — this *is* the abstain mechanism | `cost_aware_optimizer.go:95,125,239`; `greedy_score_optimizer.go:411`; `rescale.go:443,573` |
| scale-up replica count (`roleBottleneckReplicas` → `votesFromPickerState`) | yes, but reads the **raw ballot** `e.Result`, never the anchor | `analyzer_helpers.go:498-524` |

So a PRC-without-demand consumer does exist — the cost ranking — and Dean's instinct about where the
pressure comes from is right: it is the **selection** of a variant that has no demand-derived sizing of
its own, which is the partial-scale-from-zero shape (a zero-replica variant needs `PRC > 0` merely to
clear the gates and be rankable). **But it is not a place a borrow can be confined, for two reasons:**

- **The field is shared.** Ranking and sizing read the *same* `vc.PerReplicaCapacity`. A borrowed value
  that makes a variant rankable is the same value that then sizes it at
  `ceil(target / PRC)` — so the borrow cannot stay on the demand-free side of the line.
- **The case is already covered without borrowing.** The anchor task's TA scale-from-zero complement has
  the **binder itself** emit a PRC (and only a PRC) for its zero-replica variants. When TA binds, TA
  supplies the number, in TA's own metric — unit-closed, no borrow. What remains after that is only
  "the binder has no data for this variant at all", which is exactly principle 1: abstain.

**Consequence for the deferred item:** the **borrow** question has nothing left to decide, and `N8`
leaves the open queue on that axis. What remains is not a borrow and not the same question: **admitting a
variant nobody has ever measured.** Dean reopened exactly that axis and asked for it to be verified; the
verification follows, and it ends in a fix that folds into PR-2.

**`FZ-admission` — a never-seen variant cannot be admitted when TA binds** *(Dean 2026-08-07: "partial
from zero needs to work with TA. I want to verify it wll -- variants that where never seen before come up
and should be allowed in somehow.")*

Verified at `d9f3b97e`. **Admission of a never-seen variant is *saturation's* capability, and TA has no
equivalent** — the two analyzers reach a zero-replica PRC by structurally different means:

| | saturation | ThroughputAnalyzer |
|---|---|---|
| Zero-replica PRC is… | **analytic** — from the variant's own *spec* | **measured** — replayed from its own *history* |
| Source | `LoadFromScaleTarget` parses the scale target's engine args into `EngineParams` and stores a record tagged `LearnedFrom: "deployment"` (`capacity_store.go:88-131`) — called for **every** VA every cycle, inactive ones included (`saturation/engine_v2.go:39-53`) | `st.lastPerReplicaSupply`, persisted from a cycle in which the variant *was* live (`throughput/analyzer.go:400-414`) |
| Never-seen variant gets | **`PRC > 0`.** Ladder branch 2 fires (`saturation_v2/analyzer.go:421-425`): `estimateStoredCapacity` derives k2 from the spec plus model-level workload averages, bounded by its own k1 and by a compatible live sibling, falling back to raw `EffectiveMaxBatchedTokens` (`:530-563`) — which `resolveEffectiveMaxBatchedTokens` never leaves at zero (`deployment_parser.go:272-303`). Labeled `satReasonP0Store`. | **nothing** — `if !ok \|\| st.lastPerReplicaSupply <= 0 { continue }`, and the code says so: *"A never-seen variant (no persisted supply) gets nothing, so its per-replica capacity stays zero and it is not proactively selectable."* |

The spec is a source TA has no analogue for: a deployment manifest states a *token* budget; nothing in it
states a *request rate*. So this is not an omission in the anchor task's scale-from-zero complement —
there is no TA-side number it could have emitted.

Outcome per configuration:

| Config | Binder | Never-seen variant | Admitted? |
|---|---|---|---|
| `[sat]`-only (goldens-frozen default) | sat | identity **and** sizing from saturation → `PRC > 0` † | **yes** |
| `[sat,TA]`, saturation binding | sat | sizing from saturation → `PRC > 0` † | **yes** |
| `[sat,TA]`, TA binding (saturation enabled but dead / non-informative) | TA | identity from saturation (a), sizing from TA → **`PRC = 0`** | **no** |
| `[TA]`-only (saturation present but not voting) | TA | identity from saturation (a), sizing from TA → **`PRC = 0`** | **no** |

† Conditional on the deployment parse succeeding: with no scale target for the VA the pre-population is
skipped (`saturation/engine_v2.go:42-46`) and the ladder falls through to `satReasonNoData` with `PRC = 0`,
so even saturation-binding admission is not unconditional.

**The variant is never missing from the anchor — in any configuration.** The merge iterates the *identity
carrier's* variant list, and the identity carrier is **always saturation**: `runAnalyzersAndScore` appends
the saturation entry unconditionally (`Enabled: false` in `[TA]`-only, but present), and `bindingAnchor`
locates it **by name, not by vote** (`analyzer_helpers.go:133-139, 170-173`). Saturation's analyzer also
runs unconditionally — that is the known "saturation cannot be disabled" gap — so its ladder emits an entry
for **every** configured variant, never-seen ones included.

The consequence is sharper than "TA has no number": **saturation has already computed a positive PRC for
that variant, and it reaches nothing.** Precisely where that value lives and where it stops — it is not
"used, then discarded", it is **never consumed**:

| Stage | What happens to saturation's PRC for the never-seen variant |
|---|---|
| saturation's ladder | computed — `estimateStoredCapacity` off the deployment record, `PRC > 0`, `Reason: satReasonP0Store` |
| ballot packaging | **carried, intact.** `runAnalyzersAndScore` appends the whole result; nothing is stripped here, and the full ballot survives to both consumers |
| anchor merge | **not copied.** The merge takes identity fields from the (a) carrier — `VariantName`, `AcceleratorName`, `Cost`, `Role`, `ReplicaCount`, `PendingReplicas` (`analyzer_helpers.go:199-206`) — and takes `PerReplicaCapacity` *only* from `bByName`, the binder's map (`:207-212`). Saturation's number is simply never read; `out.PerReplicaCapacity` keeps its zero value |
| vote prune | **excluded.** `votingResults` keeps `Enabled && Live`, and in both failing configs saturation fails it — not enabled (`[TA]`-only) or not live (`[sat,TA]`, TA binding) — so the combine math does not see the number either |

So it is dropped twice over, on two independent paths, and neither drop is a bug: importing it into the
anchor is the borrow `N8` rejects (KV-tokens sizing a req/s anchor), and letting a dead or disabled
analyzer vote is what the liveness gates exist to prevent. **The value is correctly unused — the mistake is
only that its absence is spelled `PRC = 0`, which the pickers read as "not a candidate".** At
`PerReplicaCapacity == 0` every eligibility gate filters the variant out
(`cost_aware_optimizer.go:95,125,239`; `greedy_score_optimizer.go:411`; `rescale.go:443,573`). The gap is
that **abstain is the only vocabulary available for "new"**, and those are different states: *no opinion
about a variant we know* versus *a variant nobody has measured yet*. The sentinel replaces the missing
vocabulary; it does not revive the discarded number.

It also means the fix has a **slot to write into in every configuration** — the `else` branch at
`analyzer_helpers.go:213` — rather than needing the anchor's variant list to be completed first.

**What is left without proactive admission: the reactive path, and it is coarse.** The `scalefromzero`
engine tests inactivity **per variant** (`isInactive` = that VA's scale target at 0,
`utils/variant.go:91-93`) but **triggers per model** (EPP flow-control queue depth keyed by modelID,
`:265-280`), and on trigger brings up **every** inactive VA of that model at 1 replica — with an
acknowledged TODO that it should pick the cheapest instead (`scalefromzero/engine.go:293-324`, TODO at
`:318`). So under a TA binder a brand-new variant is admitted only *after the model backs up*, and then
unranked by cost. That is the honest answer to *"should be allowed in somehow"*: today, under a TA binder,
only late and only unranked. (That engine's coarseness is `N9` above; what is new here is that under a TA
binder it stops being a *backstop* and becomes the **only** admission path.)

**Why this is not the rejected borrow — and what unblocks it.** The borrow had nowhere to live because
ranking and sizing read the *same* field, so any value admitted to make a variant rankable is the same
value that then sizes it at `target / PRC`. Admission, however, does not need a capacity at all:

- **Eligibility** needs a *predicate* — "is this a candidate?" — for which `PRC > 0` is standing in as a
  proxy for "we know something". A never-seen variant is a candidate for a different reason.
- **Ranking** among never-seen candidates is well-defined *without* a capacity: they are all equally
  unmeasured, so cost per replica (equivalently per GPU, via `GPUsPerReplica`) totally orders them.
  `Cost / PRC` is only needed to rank a *measured* variant against another measured variant.
- **Sizing** at admission is **exactly 1 replica** — not a division. One replica is the minimum bite that
  produces the measurement; the next cycle sizes it properly from live data.

So proactive from-zero admission is expressible with no borrowed PRC and no currency mixing: *admit
never-seen variants as candidates, order them by cost, size them at 1*. This also makes saturation's
analytic path unremarkable rather than privileged — its last-resort seed is `EffectiveMaxBatchedTokens`,
a batch-size limit rather than a KV-cache capacity at threshold, so saturation's own never-seen number is
a proxy too. Admission was always a different question from sizing; saturation merely happens to own a
proxy it can dress up as one.

**The fix, as proposed** *(Dean 2026-08-07: "the anchor no-variant fallback sets PRC=1 for unknown never
seen if TA is binding? sat remains as is?")* — **confirmed as the right shape and the right site**: the
`else` branch at `analyzer_helpers.go:213`, the one place that currently decides "binder omitted this
variant ⇒ `PRC = 0`". Saturation is untouched — it keeps its analytic ladder, and when it binds nothing
changes at all. The sentinel is in **the binder's own currency**, so it is a declared minimum, not a
borrowed measurement; `N8` stays intact. Two refinements the one-liner needs:

1. **Guard on `ReplicaCount == 0`, not only on "TA is binding."** The binder also omits variants that *are*
   running but have no usable metric this cycle, and there abstain remains right: the variant is already
   up, so admission is moot and sizing must not be fabricated. Because TA's own scale-from-zero complement
   already covers *previously-live* zero-replica variants from persisted supply, "binder omitted it **and**
   `ReplicaCount == 0`" is precisely "never seen". `ReplicaCount` comes from the (a) identity, so it is
   already in hand at the merge site (`analyzer_helpers.go:204`).

2. **`PRC = 1` admits and ranks correctly but does *not* size — it needs a companion one-replica cap.** In
   the binder's currency `PRC = 1` reads as *"one replica serves 1 req/s"*, so any site that turns demand
   into replicas will buy roughly `demand` of them:
   - **eligibility** — clears every `PRC <= 0` gate. ✅ This is the whole point, and it rides the gates
     that already exist rather than adding a predicate at six sites.
   - **ranking** — `costEfficiency = Cost / PRC` degenerates to `Cost`, which totally orders the never-seen
     peers by cost, exactly as wanted. And because measured PRCs are ≫ 1, a never-seen variant ranks
     *behind* every measured option — conservative, and desirable: it wins only when nothing measured can
     absorb the load.
   - **sizing** — ⚠ `fairShareCap`-style `target / PRC`, and `fillRole`'s `targets[v]++` loop (bounded
     only by `MaxReplicas`), both read `1` as a real capacity. Unclamped, a single never-seen variant can
     absorb the whole budget one request-per-second at a time. **Admission must be explicitly capped at
     one replica**; the sentinel cannot be trusted to bound itself.

   The cap is not merely a safety belt — it is what makes the sentinel **legal under `W4`**. `W4` says a
   voter that cannot price a variant may not thereby escape the budget. Here the sentinel deliberately does
   *not* price capacity; the cap prices the **spend** — exactly one replica, `GPUsPerReplica` GPUs, charged
   to the budget like any other. Unpriced capacity, bounded spend.

   The self-clamping alternative — seed `PRC = TotalDemand` so that `ceil(demand / PRC) = 1` — is worse: it
   makes the never-seen variant rank *best* precisely when scale-up is needed. Prefer the explicit cap; it
   states the intent (*one bite, then measure*) instead of leaning on an arithmetic coincidence.

So the shape is: *when the binder is not saturation and the (a) identity shows `ReplicaCount == 0` and the
binder omitted the variant, set `PerReplicaCapacity = 1` as an admission sentinel* — plus a one-replica cap
wherever that sentinel can be spent. **Which cycle admits it is unchanged from today's abstain behavior for
one cycle only:** the variant becomes selectable immediately, and once it is up, TA's live measurement
replaces the sentinel on the next pass.

**Decision — mechanism and cap, decided here** *(Dean 2026-08-07: "don't leave design decsions to
coder.")*. Two things the task plan does not get to choose:

**(D-a) The sentinel lives in `PerReplicaCapacity`, tagged by its own `Reason`.** The alternative — leave
`PerReplicaCapacity` at `0` and add a separate *admissible* predicate — is **rejected**: it would have to
be threaded through six independent `PRC <= 0` gates (`cost_aware_optimizer.go:95`, `:125`, `:239`;
`greedy_score_optimizer.go:411`; `rescale.go:443`, `:573`), and it splits eligibility from ranking across
two fields that must then be kept in agreement. Writing the sentinel into the field those gates already
read costs one branch and keeps both properties on one value. The merge sets `Reason` to a dedicated
constant alongside it — a pipeline-side sibling of the `satReason*` family; the exact spelling is the
coder's, the *existence of the tag* is not. This reuses existing plumbing, so it adds no metric series
([§ units-observability](#units-observability)), and it is what the cap keys on.

The tag is safe to key on because `Reason` and `PerReplicaCapacity` move as a **set** at every site that
writes them — the build-time merge (`analyzer_helpers.go:207-212`) and the per-iteration refresh
(`refreshAnchorSizing:569-572`) both copy the pair together. So the tag cannot outlive the sentinel: the
first cycle a voting entry actually sizes the variant, the real PRC and the real reason replace both at
once. The refresh's two `continue` branches (`:562`, `:566`) leave the sentinel standing, which is right —
nothing has measured it yet.

**(D-b) The cap is a per-variant ceiling of *one replica*, expressed in replicas, at the three sites that
grant.** The bound is on the variant's **target**, not on a single iteration, so a repeated allocation
loop cannot buy a second replica by going round again. All three grant sites already contain the exact
mechanism to say it:

| Grant site | Grants by | Where the ceiling binds |
|---|---|---|
| `costGreedyRolePick` (`cost_aware_optimizer.go:85-109`) | returns `(variant, cap)`; `cap` = `MaxReplicas − targets[v]`, else `MaxInt` | fold into that same `headroom` computation (`:100-104`), **including its `headroom <= 0 → continue`** |
| `fairShareRolePick` (`greedy_score_optimizer.go:398-437`) | same `(variant, cap)` slot, `capN` clamped by `headroom` (`:425-431`) then `capN > 0` guard (`:432`) | same clamp, same skip |
| `fillRole` (`rescale.go:431-460`) | `targets[v]++` in a loop bounded only by `MaxReplicas` (`:452`) | add the ceiling to that same `break` condition |

The `→ continue` half is not decoration: a picker that *returns* `cap = 0` sets `n = 0` → `utilByRole = 0`
→ `deltaUtil = 0` → `break`, killing the whole allocation loop for the model instead of moving to the next
variant. The ceiling must skip the variant, exactly as `MaxReplicas` exhaustion already does.

Everything else that reads the anchor's PRC either cannot over-grant or never sees the sentinel, and needs
no change:

- `allocateForModelPaired`'s `k` (`analyzer_helpers.go:750`, `:766`, `:788`) inherits the bound instead of
  needing its own: with `prc = 1`, `deltaUtil ≤ n·1/demand`, so `k = floor(deltaUtil·demand/1) ≤ n`, and
  `n = min(bottleneck, cap)` is already capped by (D-b). **This is a consequence, not the mechanism** — do
  not implement the cap by leaning on it.
- `applyAllocation` (`analyzer_helpers.go:71-85`) decrements each analyzer's `Remaining` from
  `prcForVariant(s[i].Result, …)` — the **ballot**, never the anchor — so the sentinel never reaches it.
  (An earlier pass of this section named it as a hazard alongside `fairShareCap`; that was wrong, and the
  hazard there is `fillRole` instead.)
- `roleDemandGPUs` (`rescale.go:569-590`) takes only topology and the cost sort from the anchor; the
  replica count comes from `votesFromTotalDemand`, where no voter carries the variant ⇒ no binder ⇒ `0` ⇒
  hold. Safe by the same abstain rule that created the gap.
- every scale-down and reclaim path (`scaleDownVariantSet:125`, `reclaimRole`, `rescale.go:488`, `:511`)
  computes `removable = current − minReplicas`, which is `≤ 0` for a variant at zero replicas. Skipped.
- `TotalCapacity = ReplicaCount × PerReplicaCapacity` (`analyzer_helpers.go:220`, `:573`) is `0 × 1 = 0`,
  so the sentinel never inflates aggregate capacity — it moves eligibility and the cost ordering, nothing
  else.

Line numbers are as of `ta-anchor-dynamic-refresh@d9f3b97e`; the task plan re-verifies them against its
own tip.

**Disposition — folds into PR-2** *(Dean 2026-08-07: "everything folds into PR-2")*, consistent with
*"I lean towards folding everything in here… all are surfaced with TA is enabled so must be fixed"*. By
the [§ unit-findings-exposure](#unit-findings-exposure) test this is **TA-CREATED**: under `[sat]`-only it
cannot occur, because saturation always binds and always seeds, so the `[sat]`-only goldens cannot cover
it in either direction — deferring it would ship `[TA]`-only and TA-binding `[sat,TA]` with no proactive
from-zero admission at all. This also retires the deferred *partial* scale-from-zero picker as a separate
scope item: its trigger is now named (the abstain gate cannot express *new*) and its mechanism is decided
above. The dev-guide note beside the sibling `Cost = 0` limitation (`N5`) is no longer a substitute for the
fix, but the **`N9` residual stays** — the reactive path remains model-triggered and unranked, and that is
out of anchor scope.

**The invariant the liveness fixes must establish.** Once the vote prune is `Live`-filtered, the binder
set is a subset of the voting set, so: **a non-nil anchor implies a non-empty voting set.** The
contrapositive is the safety property worth naming — an empty voting set implies a nil anchor, which
implies **hold**, never an unguarded scale-down. Deriving the anchor from the **full** ballot (before
pruning) is what keeps identity available even when every voter is dead, so the two must not be
collapsed into one filtered pass.

[↑ TOC](#toc)

## Unit-audit findings {#unit-findings}

**Provenance.** A rule-by-rule audit of the shipped *and planned* math against
[§ units-rules](#units-rules), run by the plan reviewer (2026-08-07) against worktree
`ta-anchor-dynamic-refresh` @ `d9f3b97e` (PR-2 through the anchor-sizing commit) **and** against the
PR-2 end state. Dean's framing: *"I am not checking the full correct math, just the units."* Where
this section and the task plan disagree, this section governs. `U*` identifiers are local to this
section; the `N*` / `VG-*` labels in [§ findings](#findings) come from the code trace and are not
renumbered.

### Verdict per rule — at the tip and at PR-2 complete {#unit-findings-verdict}

Both columns matter: the tip tells us what is broken now, the end state tells us whether the planned
work actually fixes it. A rule that passes at the tip can be *broken by* a fix, which is exactly what
happened to `R3`.

| Rule | At the tip (`d9f3b97e`) | At PR-2 complete |
|---|---|---|
| `R6` convert before computing | **conforms at the combine boundary** — everything routed through the combine converts | **conforms, and the boundary widens** — the currency pivot routes the fair-share metric, the scale-down tie-break and the picker clamp through the same collectors |
| `R1` never compute in the metric | **4 violations**, every one a site that *bypasses* the combine: `fairShareValue`'s weighted sum, its zero-result fallback, `sortVariantsForScaleDown`'s tie-break, `allocateForModel`'s clamp | **all 4 fixed** — [§ bugs](#bugs) #5 sites (i)/(iii)/(iv)/(v) |
| `R4` Score inside, priority across | `fairShareValue` violates **both** directions — Score weights a budget, priority scales a within-model cap | **conforms in the Score direction** (Score leaves `fsv`); the priority direction survives → `U4` |
| `R5` fallbacks too | 1 latent violation — `fairShareValue`'s `max_{i,role}` fallback | **conforms** — site (v) |
| `R2` allocation in replicas | 1 violation — the cap's numerator is not a replica count | **fixed in the Score dimension**; still priority-scaled → `U4` |
| `R3` combine across roles/variants in a shared currency | honored in exactly **one** place (`deltaUtil = min_role utilByRole`) | **depends on the space**: GPU space conforms; a replica-space pivot would have *introduced* a new violation (`Σ_role` of replica counts). This is why [§ limited](#limited) resolves to GPUs. |

> **The single most useful observation from the audit.** Every `R1` violation is a site that
> **bypasses the cross-analyzer combine**, and no site that routes *through* the combine violates any
> rule. The combine is not merely correct — it is the *only* place the conversion happens. That is why
> widening its boundary is structurally right where patching four call sites would not be, and why
> the mechanical `R6` test in [§ units-rules](#units-rules) finds violations reliably rather than
> by luck.

[↑ TOC](#toc)

### Residuals — what a complete PR-2 does not fix {#unit-findings-residuals}

| ID | Finding | Class | Disposition |
|---|---|---|---|
| **`U1`** | **Roles are summed and compared in non-additive currencies.** Site list in [§ units-roles](#units-roles). | Escalated by Dean to a **rule**; needs a fix | **Fixed by the GPU-space pivot** — which is *why* GPU space is decided rather than optional. Not covered for the emitted series (→ `U5`). |
| **`U2`** | **PRC homogeneity within a role is assumed but never stated.** Three sites depend on a role's variants having commensurable PRCs: `costEfficiency`'s cross-variant ranking, the fair-share cap's reference-PRC round trip, and the scale-down tie-break's binder-PRC key. Per-variant sizing refresh makes the assumption false in principle. | Undocumented invariant | **Stated here; GPU space removes the *cap*'s dependence.** The tie-break's unit-cleanliness rests on an undocumented fact — the scale-down iteration never invokes the sizing refresh. **Dean 2026-08-07: pin it with a test — approved.** See the test note below. |
| **`U3`** | **`costEfficiency` is dollars-per-metric.** Immune in the batch form, exposed in the marginal form; harmless while one binder serves a whole role. | Acknowledged (Dean: "ok") | No fix now. Caveat recorded in [§ units-conversions](#units-conversions). |
| **`U4`** | **`priority` sits inside one model's per-iteration cap**, so the cap is priority-scaled replicas (or GPUs), not replicas. `R4` puts priority strictly *across* scaled objects. | Pre-existing `R4` violation | **`W2` decides the target state; the fix is a FUTURE TODO (Dean 2026-08-07).** Priority orders only, and the multiplication should go — but the defect is **TA-neutral** (see the exposure table below), so it does not meet the *"surfaced when TA is enabled ⇒ must be fixed now"* bar. Not a PR-2 blocker. |
| **`U5`** | **The emitted `RequiredCapacity` / `SpareCapacity` series inherits the binder's unit** and falls back from role level to model level. | Real, observability-only | **Documented limitation — no code change now.** Option (d)'s *"rename nothing"* half stands; its *"add series"* half is **deferred** (Dean 2026-08-07: *"no new series now"*). [§ units-observability](#units-observability). |
| **`U6`** | **A `0` vote is no longer absolute** once the combine weights by dominance, so a veto expressed as a zero value is not a veto. | Design consequence of the combine change | Correct as planned — the per-variant scale-down veto returns **before** the combine. Recorded in [§ combine](#combine-score) so a later refactor does not fold it back in. |

**`U2`'s test — approved 2026-08-07 (Dean: *"test U2 -- yes"*).** What it pins: **the scale-down
iteration never invokes the per-variant sizing refresh**, so every PRC the tie-break compares was
produced in one pass and the comparison is over commensurable values. The assertion is a *negative*
one — that a call does not happen — so a plain value check will not catch a regression: use a counting
or fake sizing hook and assert **zero invocations** across a multi-variant, multi-iteration scale-down.
Without it, a future refactor that adds a mid-iteration refresh silently reintroduces a mixed-basis
comparison in the one place that has no dimensional signal to give it away (the tie-break key is
dimensionless, per [§ bugs](#bugs) #5 site (iii)). Placement: alongside the site-(iii) commit.

[↑ TOC](#toc)

### TA exposure — which defects enabling TA creates, amplifies, or leaves alone {#unit-findings-exposure}

Dean's scoping criterion (2026-08-07) is *"all are surfaced with TA is enabled so must be fixed"*. That
is a sharp test, so it is worth applying it honestly per defect rather than to the group. The three
categories behave differently, and only the first is *created* by enabling TA.

| Defect | Category | Why | Fix now? |
|---|---|---|---|
| **Currency mixing** — `fairShareValue`'s `Σ_i Score_i × Σ_role ps[i][role]`, the scale-down tie-break's `Σ_i Score_i · prcForVariant`, the cross-analyzer clamp | **TA-CREATED** | Meaningless the instant a second *metric* votes: KV tokens added to req/s. With one analyzer there is only one currency and nothing to mix. | **Yes — this is the PR** |
| **Joint-role budget (`W1`)** — the per-`(analyzer, role)` clamp against the full `target`; `fairShareRolePick` sizing one role from the whole budget | **TA-AMPLIFIED** | Pre-existing: with `[sat]`-only + P/D there are already 2 independent full-budget draws. TA makes it `|analyzers| × |roles|` — 4 instead of 2 — but does not create it. | **Yes, and cheap** — it lives in the same expressions the currency conversion already rewrites, and it is why `_ = roles` exists |
| **`priority` in the claim (`W2`/`U4`)** | **TA-NEUTRAL** | Identical with one analyzer or five: `fairShareValue(req.Priority, …)` weights the claim regardless of how many vote. Enabling TA changes neither its presence nor its magnitude structurally. | **No — future TODO.** Verified not to block the one semantics that needed it ([§ open](#open) item 2) |

**The reason this classification is load-bearing rather than bookkeeping:** all three land in overlapping
expressions, so "fold everything" is *cheaper per-item* than deferring — but the three have **different
`[sat]`-only exposure**, which is what the characterization goldens gate. Currency conversion is
value-neutral in `[sat]`-only except at the `floor`/`ceil` cap boundary; `W1` changes `[sat]`-only P/D
allocation whenever the budget binds; `W2` changes `computeMean` for any multi-model contended cycle with
unequal priorities. Each landing as its **own commit** with the per-commit goldens already in the branch's
gate battery is what converts that difference from a risk into a signal — the goldens say which of the
three actually moves default-config behavior, before any of them is on top of the others.

**What the audit did *not* examine.** Whether the arithmetic is *right* — only whether the units are
coherent. A dimensionally-clean formula can still be the wrong formula. Three of the `W` items in
[§ open](#open) were exactly that kind of question, which is why they went to Dean rather than being
resolved here; all five are now answered, and the one residual that looked like it survived — `W5`'s
cross-model mean — turned out to be **already-settled design, not an open question**: it is a
water-fill approximation ([§ limited](#limited)), and the implementation is the
`fairShareScaleUp` loop.

[↑ TOC](#toc)

## How the cost-efficiency sort changes {#sort}

Resolved in discussion (2026-08-02):

- **Single analyzer:** demand is common across variants within a role, so it **cancels** — ranking
  by `Cost/PRC` is exactly ranking by `Cost × desired_replicas`. Today's `costEfficiency` is
  correct in this case.
- **Multi-analyzer:** the *binding* analyzer differs per variant, so demand no longer cancels. Rank
  by:
  - batch form: `C_v × combinedDesiredReplicas[v]`, or
  - marginal form: `C_v / PRC_binding(v)[v]`, where `binding(v) = argmax_i demand_i/PRC_i[v]`.
- **Backward-compatible:** for a single analyzer `PRC_binding = PRC_sat`, both forms collapse to
  today's `Cost/PRC`. Existing tests unaffected.

Under the [anchor design](#anchor), the anchor's per-variant PRC is already the binding PRC, so
`costEfficiency` reads it unchanged and gets the right ranking automatically — **provided** the
anchor is refreshed to the current binding analyzer before each sort. This is the one place the
per-iteration refresh granularity matters most (see [§ open](#open)).

**Sort cadence — verified 2026-08-03 (resolves open-Q #1).** The sort is already **re-run once per
(role, allocation iteration)**: both pick functions call `sortByCostEfficiencyAsc(roleVCs)` *inside*
the `RolePickFn` closure (`cost_aware_optimizer.go:90`, `greedy_score_optimizer.go:408`), and that
closure is invoked once per role on every turn of the `for anyRoleNeedsScaleUp` loop in
`allocateForModelPaired`. Today the key `Cost/PRC_sat` is immutable topology, so the re-sort yields
the identical order every iteration (redundant, harmless). This is exactly the seam the anchor uses:
once the key becomes the binding cost-efficiency (which shifts as allocation progresses), the
per-iteration re-sort is *already there* — the per-iteration anchor refresh feeds it with no new
loop. The sort therefore needs **no** separate binding resolution; per-iteration refresh suffices.

[↑ TOC](#toc)

## Rescale layer trace {#rescale}

Rescale operates in **GPU space**: budget → priority-weighted water-fill → per-model GPU target →
per-role GPU split → reclaim (shed expensive-first) / fill (add cheap-first) to hit the target. The
reclaim/fill **sizing** is GPU-budget-driven (`deltaGPUs / gpusPerReplica → replicas`) and stays.
The saturation-only leakage is in the **demand→GPU conversion** and the **sort order**:

- **`roleDemandGPUs` (`rescale.go:543`)** — the crux. `demand = satEntry.TotalDemand` (or
  `RoleCapacities[role].TotalDemand`), `best = cheapest variant's PerReplicaCapacity` (PRC_sat),
  `replicas = ceil(demand/best)`, `return replicas·bestGPUs`. This is the `i=saturation` term only.
  Should be combined: `desired_combined[role] = max_i ceil(demand_i[role]/PRC_i[role,v*])`. Keep
  `TotalDemand` for observability; compute per-analyzer `rd` to take the max.
  *(Orthogonal, not now: it converts the whole role via a single cheapest variant's PRC — a
  homogeneous-role approximation, a role-model choice separate from the analyzer-combine.)*
- **`rescaleInputsForGroup` (`:482`)** — water-fill inputs:
  - `Demand: satEntry.TotalDemand` (`:521`) — the weight; incommensurable under multi-analyzer
    (see [§ bugs](#bugs) #3). Should be combined demand-in-GPUs.
  - `CapGPUs = modelDemandGPUs(...)` (`:509`) — inherits `roleDemandGPUs`'s saturation-only
    projection.
- **`fillRole` (`:414`)** → `sortByCostEfficiencyAsc` (PRC_sat ordering). Direction (cheapest-first)
  correct; the efficiency PRC should be the binding analyzer's. Collapses to today for one analyzer.
- **`reclaimRole` (`:387`)** → `sortVariantsForScaleDown` (Cost-desc, per-analyzer weighted
  tie-break) → **already OK**.
- Topology iterators — `modelDemandGPUs` (`:532`), `modelCurrentGPUs` (`:464`), `roleCurrentGPUs`
  (`:588`), `roleFloorGPUs` (`:603`) — iterate `satEntry.VariantCapacities` for accel/replica-count
  (topology, OK); only their *demand* inputs route through the saturation-only `roleDemandGPUs`.

Conclusion: rescale exhibits the **same pattern** as the optimizer — everywhere `satEntry`'s
demand/PRC sizes or weights, it's the saturation-only projection, fixed by the same combined
replica-demand abstraction. Under the [anchor design](#anchor), `roleDemandGPUs` reading the anchor
gets combined demand automatically.

[↑ TOC](#toc)

## Bottom-line invariants {#invariants}

Confirmed against code (Dean, 2026-08-02):

1. **Do NOT set PRC = 1.** Keep real PRC; its only legitimate role is the `demand/PRC` and
   `n·PRC/demand` conversions.
2. **Ensure per (analyzer, variant, role) both are computable/propagated:** replica-demand
   `rd = demand/PRC` and coverage `cov = n·PRC/demand = n/rd`.
3. **Keep natural-unit demand** (`TotalDemand`, `RoleCapacities.TotalDemand`) — observability
   depends on it, and it's the numerator of `rd`. Propagate replica-count demand **alongside**, not
   replacing it. (Dean: "I do not want to fully remove the current demand in natural units.")
4. **Combine across analyzers** per `(role,v)`: `desired = max_i rd_i`, `coverage = min_i cov_i`
   (binding analyzer). This math already exists — it must **drive** sizing/sort/utilization, not sit
   beside a saturation-only proxy.
5. **Every saturation-only site** (enumerated in [§ trace](#trace) + [§ rescale](#rescale)) reads the
   combined/binding value — ideally via the [renamed anchor](#anchor), so downstream read sites are
   untouched.
6. **Role-combine (coordinated P/D) math is untouched** — already in replica/coverage space; each
   `(analyzer, role)` may be its own analyzer.
7. **Sat-v2-only ⇒ anchor is byte-for-byte identical to saturation. ALWAYS.** (Dean, 2026-08-03 —
   the load-bearing backward-compat invariant.) When saturation is the only active analyzer,
   `max_i`/`min_i`/`argmax_i` reduce to identity and introduce no rounding (`max` of a single
   `ceil` = that `ceil`), so every combined field must equal saturation's: binding PRC = PRC_sat,
   combined demand = sat demand, combined coverage = sat coverage, topology unchanged; and — stronger —
   the **per-iteration refresh is disabled** for a single vote (populate once, then off; [§ anchor](#anchor)),
   so there is no per-round recomputation that could drift (matching today, where VariantCapacities PRC
   is never mutated). This holds *by
   construction* — but **do not rely on the by-construction argument; test it directly** (Dean,
   2026-08-03). The risk is entirely in the anchor-building code applying a transform that isn't
   identity-for-n=1 (e.g. re-deriving coverage with a different numerator than sat-v2 emits today), and
   a by-construction claim is exactly the kind of thing a later refactor silently breaks. **Required
   direct test** (not an incidental assertion inside a larger scenario): with only saturation
   registered, assert `anchor == saturationEntry` field-for-field (PRC, demand, coverage, topology) —
   before, during, and after allocation iterations, and assert that with one vote the per-iteration
   refresh is **not invoked** (the anchor is not mutated after initial population). This is the single
   most important backward-compat guard in the whole change.

   **How we make it "absolutely sure" without e2e** (Dean, 2026-08-03). We have **no reproducible
   e2e goldens** — only Ofer's cluster runs, which vary with seed. The substitute is **deterministic
   unit-level characterization** of the optimizer: it is a pure function of (analyzer results,
   current/pending replicas, costs) — no seed, clock, or cluster — so on frozen inputs its outputs
   (targets, decisions, sort order, RC/SC) are fully reproducible. Capture today's outputs for a matrix
   of sat-v2-only scenarios (scale-up, scale-down, veto, P/D disagg, ties, pending) as a **first commit
   against untouched code** (green), then require **byte-equality after** the refactor. This is the
   ship gate. It beats a frozen legacy path (option B): a future optimizer PR that shifts behavior
   *trips* the characterization test (forcing intent) instead of silently rotting an unexercised
   branch. **Approach: option A** — one unified code path where the single-vote case collapses to today
   by construction (identity-short-circuited combine ops + a byte-copied, refresh-disabled anchor); the
   one-vote path performs the *same* float operations as today, so a 1-ULP drift can't flip a
   ceil/floor boundary. Option B (dual path, legacy verbatim) rejected: error-prone, ships the clean
   path cold, and any new PR could kill it.

   *(Numbering note: Dean referred to this as "invariant 6" on 2026-08-03 — the byte-identical-if-only-one
   property is this entry regardless of its position in the list.)*

   **Test-scaffolding note (Dean, 2026-08-03).** The characterization gate reuses the package-internal
   test helper `withSatEntry` (defined in `cost_aware_optimizer_test.go`) to build its fixtures. That
   reuse is acceptable **precisely because the helper is test-only code** — but the gate must never have
   a fragile *compile-time* dependency on scaffolding the refactor might churn. Rule: the refactor does
   **not** remove or re-signature `withSatEntry` out from under the gate; if it genuinely must change,
   the gate carries its **own copy** of the helper instead. Rationale: a gate that fails to *compile* on
   the refactor branch is a silent break of the byte-identity property — it reads as "build failure,"
   not "a decision moved" — so the helper's stability (or a self-contained copy) is part of the gate's
   contract, not an incidental detail. Dean: "I don't want to rely on `withSatEntry` if we remove it; if
   it is only test code, we can keep it in."

8. **A one-analyzer ballot is a pass-through *algebraically*, not by a special case.** With one vote
   the combine returns that vote's value and binder `0` for arithmetic reasons — no short-circuit,
   no `len(votes) == 1` branch, and **no dependence on Score** ([§ combine](#combine-onevote)). Three
   consequences that matter more than they look:
   - Invariant 7's byte-identity is *stronger* than "we short-circuit carefully": there is nothing to
     short-circuit. The residual risk is entirely **outside** the combine.
   - Therefore, when a saturation-only golden moves, **the combine is not the suspect.** Look at what
     else the commit changed: a currency pivot ([§ bugs](#bugs) #5), a threshold constant
     ([§ units](#units-thresholds)), a sort key ([§ sort](#sort)), or a rounding site that moved
     between callee and caller.
   - A single-vote fixture therefore exercises the **pass-through**, never the combine. The
     saturation-only characterization goldens are a *backward-compat* gate; combine coverage needs a
     genuinely multi-vote fixture, and claiming the goldens cover combine arithmetic is a category
     error.

9. **The currency round-trip rule: divide and multiply by the *same* PRC, and capture it rather than
   re-derive it.** Any quantity produced by dividing a demand by `PRC_x` must be converted back by
   multiplying by that same `PRC_x` ([§ units](#units-conversions)). Two distinct failure modes make
   "re-derive it at spend time" wrong, not merely inelegant:
   - **Value drift** — the anchor's per-iteration sizing refresh rewrites `PerReplicaCapacity` **in
     place** between denomination and spend, so a re-derived divisor is a *different number* than the
     one the budget was built from.
   - **Identity drift** — PRC feeds `costEfficiency = Cost / PRC`, which orders the cost sort; a
     changed PRC can change *which variant* "the cheapest sized variant for this role" names, so the
     re-derivation silently converts through a different variant.

   The reference must therefore be a **captured, copied value map** (per role), taken at denomination
   time. Note the shape of the hole this leaves in testing: the refresh no-ops when the ballot has a
   single vote, so **no saturation-only golden can catch a violation of this rule** — it only bites in
   a multi-analyzer configuration, which is exactly the configuration that has no golden.

   **The rule is general; one of its two instances is now designed away.** A round trip whose factor is
   **immutable** — `GPUsPerReplica`, read from deployment state and never rewritten — has neither
   failure mode. That is why the GPU-space fair-share decision ([§ limited](#limited)) makes the
   captured-value-map requirement *unnecessary* rather than *satisfied*. The rule still governs every
   PRC-denominated round trip that remains, and remains the thing to check first when a budget behaves
   as though it were scaled by an unexplained ratio.

10. **Roles are distinct voters: `Σ_role` is legal in GPUs and illegal in metric and replica space.**
    The full rule and its site list are in [§ units-roles](#units-roles). Stated here because it is the
    invariant most easily lost in a refactor: per-role fields share a name and a producer, so summing
    them *looks* like aggregating one quantity, and nothing in the type system objects. Corollaries
    worth keeping in view: a role-level number may never silently fall back to a model-level number;
    a fixture in which prefill and decode share the same PRC (or the same `GPUsPerReplica`) cannot
    distinguish a correct implementation from a role-mixing one, so such coverage is coincidental;
    and P/D is the only configuration in which the violation is observable at all, which is why it
    survived this long.

    **Corollary — the shared-pool corollary (`W1`, 2026-08-07).** The reason `Σ_role` must be *legal
    somewhere* is that roles genuinely share one resource: prefill and decode compete for the same
    GPUs. So a budget over a multi-role model is one balance with several withdrawers, and the
    constraint that binds it is **joint**: `Σ_role spend[role] ≤ budget`. Two failure modes follow, and
    the code contains one of each:
    - **Erasing role** — hand every role the same whole-model budget (today: `fairShareRolePick`'s
      shared `target`, `allocateForModel`'s per-role clamp against the full `target`). The sum is
      unbounded: a **double-spend**.
    - **Splitting role into independent entitlements** — give each role its own budget. The sum
      over-commits the pool by construction.
    Neither is a unit error; both are accounting errors that only a GPU-denominated joint constraint
    can even express. See [§ open](#open) `W1`.

11. **Priority orders; it never scales an entitlement.** `priority` (across models) and `Score`
    (across analyzers) are both **ranking weights**, and neither may multiply a quantity that is later
    spent. The general form: *a sort key is not a quantity.* Two numbers must exist wherever ranking
    and spending meet — the **claim** (unweighted, spent) and the **ordering key** (weighted, compared,
    never assigned to anything that reduces a budget). The mechanical check a reviewer can run: if a
    dimensionless weight appears in an expression that ends up on the left of a budget decrement, the
    invariant is broken. Decided 2026-08-07 ([§ open](#open) `W2`); the surviving violation is
    [§ unit-findings](#unit-findings) `U4`, whose **fix is a future TODO** — it is TA-neutral, so it does
    not meet this mission's *"surfaced when TA is enabled"* bar. Note the two levels were
    already inconsistent before this: `Score` was evicted from `fsv` early ([§ bugs](#bugs) #5 site
    (i)) while `priority` was left in, on no stated principle — this invariant is what makes them
    agree.

[↑ TOC](#toc)

## Limited-mode (greedy fair-share) path {#limited}

`GreedyByScoreOptimizer` (`greedy_score_optimizer.go`) fair-shares a scarce GPU budget across
competing models: each model gets a **priority metric** `remaining`, the loop repeatedly grants the
highest-`remaining` model enough replicas to pull it below the running mean, and stops when the
budget is spent. Trace under the lens:

**The fair-share metric itself is unit-mixed** (`fairShareValue`, `:61`):
```
fsv = priority × Σ_i Score_i × Σ_role pickerState[i][role]
```
`pickerState[i][role]` is `initRoleState`'s per-analyzer remaining **in analyzer `i`'s own units**
(saturation = tokens, throughput = req/s). So `fsv` sums tokens + req/s weighted by Score — the
**same unit-mixing as `roleAggRemaining`** ([§ bugs](#bugs) #2), but here it drives the *cross-model
fairness ordering* (`mean`, `sortByRemainingDesc`, `target = remaining − mean`). Two models with
different analyzer mixes get incomparable `remaining` values, so "who is furthest from satisfied"
is decided on a meaningless sum. Masked today (saturation-only ⇒ single unit).

**The sizing division is saturation-only** (`fairShareRolePick`, `:421`):
```
fairShareCap = ceil(target / vc.PerReplicaCapacity)   // vc from satEntry ⇒ PRC_sat
```
`target` is in `fsv` units (priority × weighted mixed-capacity); dividing by a single analyzer's
PRC_sat to get replicas is dimensionally inconsistent under multi-analyzer. This is the limited-mode
analog of `costEfficiency`/`fairShareCap` in [§ trace](#trace).

**Does the [binding anchor](#anchor) cover limited-mode?** *Partially.* `fairShareRolePick` reads
`vc.PerReplicaCapacity` off `satEntry.VariantCapacities`, so an anchor carrying binding PRC fixes the
**sizing** division automatically (`ceil(target/PRC_binding)`), and `sortByCostEfficiencyAsc` inside
the pick gets the right ordering — same free ride as unlimited-mode. **But the anchor does NOT fix
`fsv`:** `fairShareValue` is computed from `pickerState[i][role]` (per-analyzer, via `initRoleState`),
not from the anchor. So limited-mode needs a **second, separate change** the anchor-swap doesn't give
you: the fair-share metric must move to a **commensurable unit**.

**What the abstraction says the metric should be.** The scarce resource being fair-shared is GPUs, so
the consistent metric is **priority-weighted GPU-demand** (or replica-demand):
```
remaining = priority × Σ_role ( desired[role] − current[role] ) × gpusPerReplica
          where desired[role] = max_i ceil(demand_i/PRC_i)   (combined, binding)
```
In this form: `remaining`, `mean`, and `target` are all in GPU (or replica) units → comparable across
models; allocation spends GPUs directly; and PRC survives **only** in the `demand/PRC` conversion and
the cost-efficiency sort, exactly as the mental experiment predicts. This is the "simplifies
cross-analyzer math" half of the PRC=1 experiment made concrete.

> ✅ **DECIDED 2026-08-07 (Dean): GPU space. The prescription above is the shipped decision.** An
> earlier revision of this block said the opposite — that replica space ships and GPU space was the
> open option ([§ open](#open) `W5`). That is **superseded**; the reasoning that overturned it:
>
> - **A replica-space budget cannot be summed across roles.** `Σ_role` is legal only in GPUs
>   ([§ units-rules](#units-rules) `R3b`), and the fair-share numerator *is* a cross-role sum. Replica
>   space fixes the analyzer-mixing and leaves a role-mixing violation in its place; GPU space fixes
>   both with one change ([§ units-roles](#units-roles)).
> - **The round-trip hazard disappears instead of being managed.** In replica space the cap needs
>   `ceil(target · PRC_ref[role] / PRC_vc)` with `PRC_ref` captured as a copied value map before the
>   anchor's sizing is refreshed. In GPU space the spend-time factor is `GPUsPerReplica` — immutable
>   deployment topology — so [§ invariants](#invariants) #9's value- and identity-drift hazard cannot
>   arise here at all.
> - **`gpusPerReplica` being variant-dependent is an argument *for*, not against.** That is precisely
>   why replicas are not fungible against the pool. The consumer does have to learn `gpusPerReplica` —
>   and that is the honest cost of denominating a budget in the resource being rationed.
> - **The cap is still not a bare `ceil(target)`.** It is a **whole-replica fill** against
>   `GPUsPerReplica`, per [§ units-integral](#units-integral) — never a division-and-round. The
>   original prescription's "collapses to `target` replicas (no PRC division)" was wrong for that
>   reason, and remains wrong.
> - **Sat-only:** GPU space introduces no new *class* of sat-only exposure — only a `GPUsPerReplica`
>   factor on the ordering change already conceded below. Per Dean, if the sat-only path needs a fix it
>   is fixed **now**, not deferred; and the sat-only fixture must **vary `GPUsPerReplica`** or it
>   cannot detect that factor.
>
> **`W5` closed 2026-08-07.** The per-site half — "each site decides its own unit individually",
> Dean's standard rather than one global declaration — is now resolved as a **nine-row unit table**
> ([§ open-what](#open-what) `W5`). No residual: the cross-model mean, the one thing the audit had
> flagged as a possible policy gap, is **settled design** — Dean, 2026-08-07: *"cross-model mean is
> water fill approximation. already dsicussed. not here."* The table is agnostic to it either way.

> **✏️ Two amendments to the prescription above, from `W1` and `W2` (2026-08-07).**
>
> ```
> claim         = Σ_role ( desired[role] − current[role] ) × gpusPerReplica     // NO priority
>                 where desired[role] = max_i ceil(demand_i / PRC_i)
> ordering key  = priority × claim                                             // sort only, never spent
> spend         = Σ_role spend[role] ≤ claim − mean                            // one balance per model
> ```
>
> - **`priority` leaves the quantity** (invariant 11): it multiplies the *ordering key* only. The
>   `priority ×` in the block above is today's behavior, retained there because the currency conversion
>   must be value-neutral — it is **not** the end state.
> - **The cross-role `Σ` is a spend constraint, not just a numerator** (`W1`): the roles draw against
>   one balance and each draw decrements it, rather than each role receiving a copy of the whole
>   figure. This is the shape the current code gets wrong in two places, and it is expressible only
>   here, in GPU space.

**Verdict.** The replica-demand/coverage abstraction *does* cover limited-mode, and PRC drops out of
most of the fair-share loop the same way — but limited-mode has **two** leak sites, not one: (a) the
sizing PRC (fixed by the anchor, like unlimited-mode) and (b) the fair-share *metric* `fsv` (needs its
own move to a commensurable unit; the anchor does not reach it as `fsv` is written today — the fix
re-points it). Fixing (a) without (b) leaves the cross-model ordering unit-mixed. So limited-mode is a
strictly larger change than unlimited-mode — and larger still than "one metric": because the *unit*
of `fsv` changes, every producer and consumer of that number moves in lock-step, five sites
([§ bugs](#bugs) #5).

Other limited-mode sites checked and **OK**: `anyRoleNeedsScaleUp(ps, roles)` is a per-analyzer OR
(scale up if *any* analyzer wants more), which equals `max_i rd_i > current` — consistent with the
combined `desired`. `applyAllocation` decrements per-analyzer PRC. The paired-commit
`allocateForModelPaired` carries the same `k`/decrement unit-mismatch as unlimited-mode
([§ bugs](#bugs) #1) — it is shared code, so one fix covers both modes.

[↑ TOC](#toc)

## Open questions {#open}

**Decision queue as of 2026-08-07 (second pass).** Everything still open in this doc, in one place, so
the freeze is auditable.

✅ **The queue is EMPTY.** The last item — `FZ-admission`, opened by Dean's own follow-up — was answered
and then decided on 2026-08-07. *Can a never-seen variant be admitted when TA binds?* **Verified: no**
(full evidence in [§ findings](#findings)). Only saturation can seed a never-measured variant, analytically
from its deployment spec; TA's zero-replica PRC is replayed measurement, so under a TA binder a brand-new
variant sits in the anchor at `PRC = 0` and every eligibility gate skips it, leaving only the reactive
`scalefromzero` path — which fires once the *model* backs up and then raises **all** inactive variants,
unranked by cost. **Decided: the fix folds into PR-2**, with both design choices settled in this doc rather
than handed down — a `Reason`-tagged `PRC = 1` **admission sentinel** in the binder's own currency at the
anchor's no-variant branch (gated on `ReplicaCount == 0`), plus a **one-replica target ceiling** at the
three sites that grant replicas, which is what keeps unpriced capacity from escaping the `W4` budget rule.
No borrowed PRC, no new currency, no new metric series.

**Everything else is closed.** Not to be reopened: `W1`, `W2`, `W3`, `W4`, `W5` (all five —
[§ open-what](#open-what)), the observability scope call (*"no new series now"* —
[§ units-observability](#units-observability)), the `U2` test (approved), and the three items that were
still open at the first pass of this section — **now all three answered**:

| Was open | Decision (Dean, 2026-08-07) | Consequence |
|---|---|---|
| **Sequencing of the `W1` + `W2` behavior changes** — PR-2 or a follow-up? | **Fold into PR-2** — *"can fold it in PR-2. Too many things to track for next PRs."* Governing principle for this mission: *"I lean towards folding everything in here. Not as clean, but all are surfaced with TA is enabled so must be fixed."* | The task plan's commit map absorbs `W1` (and the currency pivot) as their own commits. C6c stops being purely status-quo-preserving **by decision, not by accident** — that must be explicit in the plan so a reviewer does not read a behavior change as a botched conversion. Exposure per defect: [§ unit-findings-exposure](#unit-findings-exposure). |
| **`priority` unset-vs-explicit-`0`** — needs an optional field to make explicit `0` expressible? | **No API change** — *"leave it. 0.00001 does the same. (verify)"* | **Verified — it does, and it already works today.** See the verification below. `W3`'s *"last in line, take the leftovers"* semantics are reachable **now**, with no CRD change; what they need is *documentation*, not code. |
| **`N8` rationale** — abstain, or inherit saturation's sizing? | **Abstain** — *"can't vote if you have no info… live+enabled needed to vote not a fallback."* | Closed with a checkable result: **no legitimate borrow site exists**. Full argument + the anchor-PRC consumer inventory in [§ findings](#findings). The *borrow* axis is closed; Dean's follow-up opened the distinct *admission* axis — `FZ-admission` — which is now answered and folded into PR-2 (see above), leaving nothing open on either. |

**What "everything folds into PR-2" means concretely** *(Dean 2026-08-07)* — the full fold-in list, so the
Type-3 refresh has one place to pick up from and nothing has to be re-derived from prose:

| Folds into PR-2 | Where the decision lives |
|---|---|
| The currency pivot itself (`W5`'s per-site unit table; `fairShareCap` → whole-replica GPU-space `floor` fill) | [§ open-what](#open-what) `W5`, [§ units-rules](#units-rules) |
| `W1` — one fair-share entitlement per **model**, spent jointly across roles | [§ open-what](#open-what) `W1`; both spend sites are defects |
| `W4` — "no conversion factor ⇒ no spend", as one stated rule rather than accidental safety | [§ open-what](#open-what) `W4` |
| `FZ-admission` — the `Reason`-tagged `PRC = 1` sentinel + the one-replica **target** ceiling at the three grant sites | [§ findings](#findings), decision block (D-a)/(D-b) |
| `VG-up` — prune the combine ballot on `Enabled && Live` | [§ findings](#findings) `VG-up` |
| The four arithmetic bugs and the per-iteration re-binding already in the task plan | [§ bugs](#bugs) |

**Not** in PR-2, and deliberately so: `W2`/`U4` (priority inside the claim) — **TA-neutral**, so it fails
this mission's own *"surfaced when TA is enabled ⇒ must be fixed now"* bar and becomes a future TODO;
`U5`'s new observability series (*"no new series now"*); `N9`'s reactive from-zero engine (model-triggered
and unranked, out of anchor scope); `AnalyzerName` validation (a separate change); and the saturation
`Cost = 0`-for-zero-replica bug (`N5`, a separate pre-existing fix). `W3` needs no work at all beyond
documentation.

**Verification of the `0.00001` idiom (asked for explicitly; traced at `d9f3b97e`).** It is expressible,
and it produces exactly the intended behavior — for a reason worth writing down, because it is not
obvious from the formula alone.

*Expressible:*

- `ApplyDefaults` rewrites **only exactly `0`** (`if c.Priority == 0 { c.Priority = DefaultPriority }`,
  `saturation_scaling.go:275-276`), so `0.00001` passes through untouched.
- Validation admits it: `if c.Priority < 0 { error }` (`:398-399`) — the bound is `>= 0`.
- The per-model override merge honors it: `if override.Priority != 0` (`:362-363`) — a `0.00001`
  override applies, where a `0` override would be silently ignored as "unset".

*And it behaves as "last in line, takes the leftovers"* — via the water-fill loop
`fairShareScaleUp` (`greedy_score_optimizer.go:202-261`), not via the claim formula:

1. The loop processes **only `active[0]`** per turn — the model with the largest `remaining` after
   `sortByRemainingDesc`. A `1e-5` priority puts the model at the tail, so it is never touched while any
   other model is active. → *last in line.*
2. Other models drain out: each is removed (`remaining = -1`) when it cannot allocate or is still above
   the mean after allocating.
3. Its near-zero `remaining` **lowers** `computeMean`, which **raises** `target = remaining − mean` for
   whoever is at the head. → *"take what you want."*
4. When it is the last one standing, `len(active) == 1` sets `allocationMean = 0`, so
   `target = remaining` — its budget unlocks in full, and `fairShareCap = ceil(target / PRC)` yields at
   least 1 replica for any positive target. It then keeps drawing, one turn at a time, until either its
   demand is served or `totalGPUs == 0` stops the loop. → *uses the leftovers.*

An explicit `0` would **not** do this today: `ApplyDefaults` turns it into `1.0`, i.e. normal priority —
the opposite of the intent. So `0.00001` is not a workaround for a missing feature; it is the *only*
expression of the feature, and the API gap is a documentation gap. **Worth noting for the future `W2`
fix:** it keeps working afterwards, but through a different mechanism — the tail position moves from the
claim to the ordering key, and step 3 disappears (an unweighted mean no longer reads the low-priority
model as ~0). The behavior a user sees is preserved; the reason changes.

Not on this queue, deliberately: the *arithmetic*. This doc's unit audit
([§ unit-findings](#unit-findings)) checked only that the currencies are coherent, never that the
formulas are right.

1. ~~Anchor refresh granularity / does the cost-sort need its own binding resolution?~~ — *Fully
   resolved 2026-08-03.* Refresh each allocation iteration (Dean); and the sort is already re-run
   once per (role, iteration) inside the pick closure, so per-iteration refresh feeds it directly —
   **no separate sort-time binding resolution needed** ([§ sort](#sort) "Sort cadence").
2. ~~**Relationship to F1 / Half-B.**~~ — *Resolved 2026-08-03.* This doc **is** the missing Half-B
   design; Half-B becomes a task plan derived from it (Dean's ship decision — [§ why](#why)). F1
   "pre-analysis extraction" is **not a prerequisite and not a cost saver**: sat-v2 always runs and
   always produces the metadata the anchor copies, so the metadata is always present without
   extracting it ([§ anchor](#anchor) "always
   runs and always produces the metadata"). F1 is simply unnecessary for enabling TA.
3. ~~Anticipated-supply-in-denominator suspicion~~ — *Resolved 2026-08-03: TRACED, verdict
   DOWNGRADED.* Not an active sizing bug — RC correctly nets out current+pending; the only
   pending-blind quantity is the observability `Utilization`. Full trace in [§ bugs](#bugs) #4.
   Follow-up: update coordination-doc D1/#2 to match.
4. ~~Anchor demand per role vs per (role,variant)?~~ — *Resolved* (Dean, 2026-08-03): binding is
   per (role, variant) and the anchor holds it per-entry ([§ combine](#combine), [§ anchor](#anchor)).
   Store combined PRC + `rd`/coverage per variant entry; role demand once per role.
5. ~~Exact locations for the two anchor-external fixes~~ — *Resolved 2026-08-03 (traced), scope
   corrected 2026-08-07.* Bug #4 is downgraded (no sizing fix needed; observability-only). Bug #5
   (`fsv`) is **five** lock-step sites, not three — `fairShareValue` (+ its signature), `fairShareCap`
   (a round-trip rescale, **not** a bare `ceil(target)`), the scale-down tie-break
   `sortVariantsForScaleDown`, the picker-state clamp in `allocateForModel`, and `fairShareValue`'s
   zero-result fallback ([§ bugs](#bugs) #5). The sequencing question is also resolved: the `fsv`
   rewrite lands in the **dynamic-refresh task, not the anchor task** — the anchor task ships the
   mechanism with zero combine-arithmetic change, and the currency pivot rides with the multi-vote
   combine that makes it observable.
6. **Should the observability `Utilization` be reconciled to the clean `achieved`?** — *Assessed
   2026-08-03: recommend NO code change.* The `Utilization` gauge (`demand/current`,
   `saturation_v2/analyzer.go:115/438`) is an **honest current-load** metric. The decision path uses
   `(current+anticipated)/demand_target` (via RC). They differ **during scale-out by design** — the
   gauge says "saturated now," the controller says "relief provisioning, no action"; both true.
   Folding `anticipated` into the gauge would make it read cool the moment replicas are *requested*
   (before Ready), which would **mask a genuine persisting saturation** if those pending replicas
   never become Ready (bad image, unschedulable). So current-only is the *safer* gauge. The
   small-and-clear action is a **doc/comment note** distinguishing "current-load gauge" from
   "anticipated-coverage decision signal" so a later reader doesn't "fix" the gauge and silently hide
   saturation; an anticipated-coverage signal, if wanted, belongs in a **separate** gauge, not
   overloading `Utilization`. (Dean 2026-08-03: "include the observability correction if small and
   clear" — on inspection it is neither a bug nor small-and-clear as a semantics change; the
   doc-note is the small-and-clear part.)

   *Reconciled with the 2026-08-07 emitted-series decision.* [§ units-observability](#units-observability)
   decides option (d) — **keep every existing series' name and semantics** — and, per Dean's *"no new
   series now"*, defers the additions. This item is the same decision reached independently for one
   specific gauge: do not redefine `Utilization`; a separate signal is the right shape *if* an
   anticipated-coverage view is ever wanted, but it is not being added now. The two do not conflict, and
   the reason is the same in both places: a redefinition-in-place is invisible to whoever is plotting the
   series, and a new series is a permanent external contract — easier to postpone than to withdraw. The
   one thing the newer section adds here is *which* new series to prefer **when the deferral lifts** — a
   dimensionless/coverage one, since that is the currency the pipeline's terminal comparisons are already
   in.

### Design-level "what" questions surfaced by the currency fix (W1–W5) {#open-what}

**Provenance.** These five were surfaced by a coder implementing the [§ bugs](#bugs) #5 currency pivot
(2026-08-07) and were **migrated here from the task plan**, which is the wrong instrument for them:
they are properties of the fair-share *model*, not of a commit.

> **✅ All five ANSWERED by Dean, 2026-08-07.** The question text is retained below because it is the
> derivation, but each now carries its answer. What the answers change, in one line each:
>
> | | Answer | Consequence |
> |---|---|---|
> | `W1` | One budget per **model**, spent **jointly across roles** | Role must appear in the *spend accounting*. Both current spend sites are wrong, not just mis-united. |
> | `W2` | Priority is **ordering only**; the assignment carries no priority | The claim and the ordering key split into two numbers. `U4` is the defect — but its **fix is deferred** (TA-neutral; see [§ unit-findings-exposure](#unit-findings-exposure)). |
> | `W3` | Explicit `0` = "last in line, I take the leftovers"; unset = `1` | **No API change** (Dean: *"leave it. 0.00001 does the same"*) — `0.00001` already spells it, and it **works today**, verified in [§ open-what](#open-what) `W3`. The gap is documentation, not API. |
> | `W4` | **No** — you cannot exceed the budget just because an item has no price | "No conversion factor ⇒ no spend." Today's accidental safety becomes one rule. |
> | `W5` | Answerable from the lattice; no further input needed | Resolved as a per-site unit table below. **No residual** — the cross-model mean is settled water-fill design, not an open policy question. |
>
> Two of these are **behavior changes beyond the currency pivot** (`W1`'s joint role accounting,
> `W2`'s de-prioritized spend), and their sequencing is now settled: `W1` folds **into PR-2**, `W2`
> becomes a future TODO, and `W3` needs no API work at all. See the (now-empty)
> [§ open](#open) decision queue for the reasoning, and
> [§ unit-findings-exposure](#unit-findings-exposure) for why the two split that way.

**The rule the currency fix followed while these were open** — retained because it explains the shape
of the landed commits: every W item was **status-quo-preserving**; the fix changed the *currency* and
nothing else. That rule is now spent. Where an answer above mandates a behavior change, the change is
deliberate and must be committed and tested as such, not smuggled in as part of a conversion.

**Resolution standard (Dean, 2026-08-07).** **Decide the correct unit at each place, individually** —
not one global "the budget is in replicas" declaration. `W5` is resolved that way below, site by site.
The task plan is refreshed **after** this section freezes, and coding resumes after that — see
[§ units](#units) for the vocabulary the refresh has to be written in.

---

**W1 — Is the fair-share budget one scalar per *model*, or one per *(model, role)*?**

Today it is a scalar: `fairShareValue` sums over roles and `target = remaining − mean` inherits that.
The scalar is then spent two ways that do not agree with each other:

- the cap (site (ii)) limits a **single role's** pick with the **whole model's** budget — a P/D model's
  prefill pick is sized by prefill *plus* decode demand;
- the clamp (site (iv)) limits **each** role independently against the same scalar, so both roles may
  separately draw up to the full budget.

Both are pre-existing. The observable consequence is the multi-role divergence in [§ bugs](#bugs) #5:
because the numerator is a cross-role sum, converting it changes the cap for a P/D model **iff** its
per-role reference PRCs differ. Neither form is *right* — they are two different over-caps of a
quantity that was never defined per role. The code already anticipates the question: `fairShareRolePick`
carries a `roles` parameter kept alive by a `_ =` assignment for "future per-role budget splitting".
Deciding W1 the per-role way makes that parameter live and makes the cap's numerator a single role's
demand, at which point the divergence disappears rather than being converted.

> **✅ RESOLVED 2026-08-07 (Dean).** Verbatim: *"two roles can compete on the same GPU. How can we not
> include role??"*
>
> The question as posed above is a **false dichotomy**, and that is the clarification. Both of its
> horns are wrong for the same reason — they each erase one half of what a role is:
>
> - *One budget per `(model, role)`* would give prefill and decode **independent entitlements**. But
>   they draw from **one shared GPU pool**, so two independent entitlements over-commit it by
>   construction: each role could be individually within budget while the model as a whole is over.
> - *One scalar per model, with role erased*, is what the code does today — and erasing role is
>   exactly how the double-spend happens (below).
>
> **The answer is neither: one entitlement per model, spent jointly across its roles.**
>
> | | Entitlement (how much the model may hold) | Spend accounting (who consumed it) |
> |---|---|---|
> | Granularity | **per model** — one number | **per role** — each role's draw is a separate debit |
> | Constraint | `budget` | `Σ_role spend[role] ≤ budget` |
> | Unit | **GPUs** (`W5`) | **GPUs** — the only space the sum is legal in |
>
> So role **is** included — it appears in the *accounting*, never as a second entitlement. Dean's
> premise is the derivation: because the roles compete for the same GPUs, the constraint that binds
> them is a **joint** one, and a joint constraint needs each role's spend to be visible and
> subtracted from a shared remainder as it is taken. The budget is a pool with one balance and
> several withdrawers, not several pools.
>
> **Both current spend sites violate this, and neither is merely mis-united:**
>
> | Site | Code | What it does | Why it is wrong |
> |---|---|---|---|
> | (ii) cap | `fairShareRolePick` — one `target` passed to every role; `_ = roles // … future per-role budget splitting` | Sizes **one** role's pick with the **whole** model's budget | A P/D model's prefill pick is sized by prefill *plus* decode demand |
> | (iv) clamp | `allocateForModel` — `ps[i][role] > target → target`, per `(i, role)` | Clamps **each** role independently against the **full** `target` | Both roles may separately draw the entire budget: a **double-spend**, not an over-cap |
>
> The only thing standing between that double-spend and a real over-allocation today is the
> downstream GPU-pool check (`min(fairShareCap, gpusAvail/gpusPerReplica)`) — the *pool* is enforced,
> the *fair share* is not. That is the same shape as `W4`: safety by a second mechanism happening to
> agree, rather than by the rule being stated once.
>
> **Two consequences worth stating explicitly.**
>
> 1. **The joint constraint is expressible only in GPU space.** `Σ_role` over metric or replicas is
>    forbidden by [§ invariants](#invariants) invariant 10 — prefill tokens and decode tokens are
>    different currencies, and a prefill replica and a decode replica are different goods. In GPUs
>    they are the same good, so `Σ_role spend ≤ budget` is a well-formed sentence. This is a third
>    thing the `W5` GPU pivot unlocks, alongside `R3` and `U1`.
> 2. **`fairShareRolePick`'s `roles` parameter becomes live.** The `_ =` placeholder was put there for
>    "future per-role budget splitting"; what it actually needs is not a *split* of the budget into
>    per-role shares but a *sequenced draw* against the shared balance — iterate the roles,
>    subtracting each role's GPU spend from the remainder before sizing the next. A static split
>    would under-serve whichever role is cheaper to satisfy.
>
> **Sequencing.** This is a **behavior change**, not a currency conversion: it changes allocations in
> any multi-role model even after units are fixed. It therefore does **not** belong inside the
> status-quo-preserving [§ bugs](#bugs) #5 conversion commit, and needs its own commit, its own
> multi-role test, and a call on whether it lands in PR-2 at all — see the [§ open](#open) decision
> queue.

**W2 — Should the budget be priority-scaled where it is *spent*, or only where models are *ordered*?**

`remaining = priority × …`, so `target` is priority-scaled and the cap lets a priority-10 model take up
to 10× the replicas its own demand justifies **in one iteration**. `priority` therefore does two jobs:
an *ordering* job (`sortByRemainingDesc` — who is served first when GPUs are scarce) and an
*entitlement* job (the cap — how much may be held). Only the first is what "priority" usually means in
a scheduler.

Two facts suggest the coupling is unconsidered rather than intended: the site-(v) fallback
**deliberately drops** `priority` (it returns unweighted demand, so the same model's budget is
priority-scaled on one path and not the other), and `computeMean` averages priority-scaled values
across models, so one high-priority model shifts every other model's `target`. Until this is decided,
the honest description of the cap is "**priority-scaled** replicas", not "replicas" — dividing
`priority` out is a behavior change beyond the currency fix.

> **✅ RESOLVED 2026-08-07 (Dean).** Verbatim: *"piority is ordering. decide what each get. acctual
> assign has no priority."*
>
> **Priority orders; it does not scale.** It decides *who is served first* — and therefore, when GPUs
> run out, who gets served at all — but the number a model may hold is its own demand, unmultiplied.
> The two jobs `priority` currently does are split into two numbers:
>
> | | Number | Definition | Where it may be read |
> |---|---|---|---|
> | Ordering key | `priority × claim` (or any monotone function of the pair) | ranks models against each other | `sortByRemainingDesc` **only** |
> | Claim | `claim`, **unweighted** | how many GPUs this model may hold | `computeMean`, `target`, the cap, the clamp |
>
> The ordering key is *never spent*. It is a comparator input and nothing else — which is exactly the
> [§ invariants](#invariants) formulation: **a sort key is not a quantity**.
>
> **What this decides downstream:**
>
> - **`computeMean` averages unweighted claims.** Today it means over priority-scaled values, so one
>   high-priority model shifts every other model's `target` — a scarcity signal leaking out of a
>   ranking. Gone.
> - **`U4` stops being a naming obligation and becomes a defect to fix.** The doc's previous position
>   was "until `W2` is decided, describe the cap honestly as *priority-scaled* replicas." `W2` is
>   decided: the multiplication is wrong, so the fix is to remove it, not to name it. See
>   [§ unit-findings](#unit-findings).
> - **The site-(v) fallback's `priority` drop turns out to be *correct*** — and then becomes moot.
>   It returns unweighted demand, which under this answer is simply what a claim is. But with
>   `priority` out of the claim, `priority = 0` can no longer zero `fsv`, so the branch that reaches
>   the fallback stops existing: it becomes **dead code to delete**, not a formula to re-denominate.
>   See `W3` and [§ bugs](#bugs) #5 site (v).
> - **Consistency with the existing model.** This is the same move the doc already makes one level
>   down for scores: *"`Score` leaves `fsv` entirely"* ([§ bugs](#bugs) #5 site (i)). Both weights —
>   `Score` across analyzers, `priority` across models — are ranking inputs, not multipliers on a
>   quantity. `W2` makes the two levels agree.
>
> **Sequencing.** Like `W1`, this changes allocations independently of units, so it is a separate
> commit from the currency conversion, with its own test asserting that a priority-10 model's single-
> iteration hold equals its own demand. Placement is on the [§ open](#open) queue.

**W3 — What does `priority: 0` mean?**

`ApplyDefaults` rewrites `Priority == 0 → 1.0`, so through the normal API this is unreachable — yet
`fairShareValue`'s fallback exists precisely for it, and a hand-built request reaches it. Three
readings, all defensible:

- *unweighted but eligible* — keep the fallback (in the new currency). This is the status-quo-preserving
  reading, and the alternative failure is worse: a model that genuinely needs replicas silently never
  scales, because `fsv = 0` excludes it from the active set.
- *sit this cycle out* — delete the fallback, treat `priority: 0` as a config error. A real behavior
  change for anyone running it, and it needs a DEPRECATED/DEFERRED classification.
- *unreachable by contract* — if `ApplyDefaults`' rewrite **is** the intended contract, the fallback is
  dead code and should be deleted **as dead**, not fixed.

Note the fallback has to be fixed either way, because [§ bugs](#bugs) #5's finding (b) depends on it: a
wholly-unactionable model computes `0` on the primary path and falls through.

> **✅ RESOLVED 2026-08-07 (Dean).** Verbatim: *"it is to compare competing model and decide who get
> more than fairshare. I'd say the explict 0 means I am last in line, take what you want, I will use
> the leftovers. This should be only if explicit. If default then all should be 1."*
>
> **`priority: 0` means "last in line" — lowest rank, still fully eligible, takes whatever is left
> over.** It is a *deprioritization*, not an opt-out and not an error:
>
> | | `priority: 0`, explicit | `priority` unset |
> |---|---|---|
> | Ordering | **last** — after every model with `priority > 0` | ranked at `1` |
> | Eligibility | **eligible** — stays in the active set | eligible |
> | What it gets | the **leftovers**: whatever GPUs remain after the ranked models are served | its fair share |
> | Claim | its own demand, unweighted (per `W2`) | its own demand, unweighted |
>
> Note this is coherent only *because* of `W2`. Once `priority` is out of the claim, "rank last" and
> "claim my full demand" are not in tension: a `priority: 0` model asks for exactly what it needs and
> simply waits its turn. Under the old coupling, `priority: 0` meant *claim nothing*, which is why the
> fallback had to exist at all. The framing in Dean's answer — priority *"is to compare competing
> model and decide who get more than fairshare"* — is the same statement from the pool's side: rank
> governs who gets served out of a scarce pool, not how large anyone's ask is.
>
> **`priority: 0` is unreachable through the public API — and that is now decided to be acceptable, not
> a defect to fix.** The semantics above are only expressible if *explicit `0`* and *unset* are
> distinguishable, and they are not: `ApplyDefaults` rewrites `Priority == 0 → 1.0` unconditionally
> (`saturation_scaling.go:275-276`), so a user who writes `priority: 0` gets `1.0`.
>
> **✏️ Dean 2026-08-07: no API change** — *"leave it. 0.00001 does the same. (verify)"* — **verified, and
> it works today.** `0.00001` survives `ApplyDefaults` (only exactly `0` is rewritten), passes validation
> (`>= 0`), applies as an override (`!= 0`), and reaches all four "last in line, takes the leftovers"
> behaviors through the `fairShareScaleUp` water-fill loop. The step-by-step trace is on the
> [§ open](#open) queue table, where the decision is recorded.
>
> Two consequences worth stating precisely, because they are easy to get backwards:
>
> - **`0.00001` is not a workaround for a missing feature — it is the feature's only spelling.** Explicit
>   `0` is the value that does *not* work (it becomes `1.0`, i.e. normal priority — the opposite of the
>   intent). So the gap is **documentation**, not API: the user-facing docs should name the idiom.
> - **It works today, before `W2`,** which is why nothing is blocked. Its mechanism *changes* when `W2`
>   lands — the tail position moves from the weighted claim to the ordering key — but the observable
>   behavior is preserved. That makes `W2`/`U4` safely deferrable
>   ([§ unit-findings-exposure](#unit-findings-exposure)).
>
> **Disposition of the site-(v) fallback: delete it as dead.** Of the three readings above, the third
> is what obtains, but for a different reason than that bullet gives. It is not dead because
> `ApplyDefaults` makes `priority: 0` unreachable — it is dead because `W2` removes `priority` from
> the claim, so no priority value can drive `fsv` to `0` any more. The remaining way to reach `fsv = 0`
> is a genuinely zero claim (a wholly-unactionable model), and for that case falling back to
> `max_{i,role} ps[i][role]` is wrong on its own terms: it manufactures a claim out of the same
> `pickerState` that just summed to nothing. That is [§ bugs](#bugs) #5's finding (b), and the correct
> answer there is `0` — an unactionable model claims nothing and is excluded from the active set, which
> is what "no analyzer can size me" should mean. The deletion needs a **DEPRECATED** classification in
> the coder's handoff ("priority-zero fallback — removed; `priority` no longer scales the claim, so the
> branch is unreachable, and a zero claim is now the correct output rather than a condition to
> paper over").

**W4 — Is a voter that cannot size the reference variant exempt from the budget?**

Site (iv) leaves an analyzer with no PRC for the reference variant **unclamped** — there is no
conversion factor, and clamping raw capacity against a replica number is the bug being removed. So the
budget is not enforced against that analyzer's `ps` entry. This is harmless *today* because the same
`prc <= 0` filter in `votesFromPickerState` already excludes it from the scale-up bottleneck count, so
it cannot drive allocation of that variant either.

But "harmless" rests on **two independent mechanisms happening to agree**, not on one rule. The design
question is which rule is wanted: (a) exempt from the budget (today), (b) excluded from the model's
demand altogether — finding (b)'s direction applied consistently, which would make the exemption
vacuous rather than harmless, or (c) clamped through some *other* variant the analyzer can size.

> **✅ RESOLVED 2026-08-07 (Dean).** Verbatim: *"no. you should not be able to exceed budget even if
> you don't know the price of an item."*
>
> **Option (b): no conversion factor ⇒ no spend.** Not exempt. A voter that cannot price the variant
> it wants is not thereby licensed to draw from the pool without being charged — it is simply unable
> to place an order:
>
> > **Rule.** A ballot entry with no usable conversion factor for a variant (`PRC ≤ 0`, or absent)
> > contributes **nothing** for that variant: it enters neither the model's claim nor the pick. It is
> > not clamped-then-spent, and it is not spent-unclamped. It abstains.
>
> This is the only one of the three options that keeps the budget an actual bound. Option (a) —
> today's exemption — makes "budget" mean "budget, except for entries we cannot measure", which is
> precisely the sentence Dean's answer rejects; and note that an unmeasurable entry is exactly the one
> most likely to be stale or wrong, so exempting it inverts the risk. Option (c) — clamp through some
> *other* variant — silently substitutes one variant's economics for another's and is a
> currency-mixing bug in a new place.
>
> **What changes in the code is smaller than what changes in the reasoning.** `votesFromPickerState`
> already filters `prc <= 0`, so the observable behavior today is largely what the rule prescribes.
> The change is that this stops being a coincidence: one rule now covers it, stated once, instead of
> the outcome depending on two filters in different functions happening to agree. Concretely:
>
> | | Before | After |
> |---|---|---|
> | Basis of safety | `votesFromPickerState`'s `prc <= 0` filter happens to exclude the same entry the clamp skipped | one rule, applied at claim construction |
> | If either filter is edited | silent over-allocation, no test fails | the rule is the invariant; the test asserts it |
> | Claim construction | entry contributes raw metric, unclamped | entry contributes nothing |
>
> **This corrects a statement elsewhere in this doc.** [§ bugs](#bugs) #5 site (iv) currently says such
> an analyzer "is left **unclamped** … so the un-enforced budget is harmless." Under this answer that
> is no longer the prescription — it is a description of a defect. That passage is amended in place;
> see the correction block there.
>
> **Test.** A `[sat,TA]` fixture where one analyzer has no PRC for the reference variant must produce
> the same allocation as the same fixture with that analyzer absent from the ballot. That equality is
> the rule, and it is what a future edit to either filter would break.

**W5 — Is the mean of models' fair-share values a meaningful reference, and in what unit?**

`computeMean` is a plain arithmetic mean over active models' `remaining`, and `sortByRemainingDesc`
orders by the same number. Today it averages tokens against req/s across models with unequal PRCs —
that is [§ bugs](#bugs) #5, and the currency fix repairs it.

> **✅ RESOLVED 2026-08-07.** Verbatim: *"why not clear from context. If you need my input I need more
> iformation."* — It is clear from context. Recorded here rather than escalated, and the units below
> are **derived**, not chosen: each follows from the lattice ([§ units-lattice](#units-lattice)) plus
> the four answers `W1`–`W4`. Nothing in this table is a preference.
>
> The *budget currency* half was already decided (**GPUs** — [§ bugs](#bugs) #5, [§ limited](#limited)).
> What that decision left open was Dean's own standard: **each site names its own unit**. Site by site:
>
> | # | Site | Quantity | Unit | Rule |
> |---|---|---|---|---|
> | 0 | ballot entry → claim | per-`(analyzer, variant, role)` demand | **GPUs** | convert **at entry**: `toGPUs() = (metric ÷ PRC) × GPUsPerReplica`. No `PRC` ⇒ contributes nothing (`W4`). |
> | 1 | across analyzers, one role | per-role claim | **GPUs** | `max_i` — dominance, matching the binding rule. Never `Σ_i` ([§ combine](#combine)). |
> | 2 | across roles, one model | model claim | **GPUs** | `Σ_role` — legal here and only here (invariant 10). |
> | 3 | `computeMean` | reference level across models | **GPUs** | mean of **unweighted** claims (`W2`). |
> | 4 | `target = claim − mean` | this model's entitlement | **GPUs** | **one** per model; roles debit a shared remainder, `Σ_role spend ≤ target` (`W1`). |
> | 5 | `sortByRemainingDesc` | ordering key | **none — dimensionless rank** | `priority × claim`; a comparator input that is **never spent** (`W2`). |
> | 6 | `fairShareCap` | how many replicas this variant may add | **replicas (integral)** | whole-replica **fill** of the remaining GPU budget: `floor(remaining_GPUs / GPUsPerReplica)`, then `min` with the real pool. Not a divide-and-round ([§ units-integral](#units-integral)). |
> | 7 | site (iii) tie-break | scale-down ordering | **none — coverage per GPU freed** | dimensionless ratio; `max_i`, not `Σ_i`. |
> | 8 | site (iv) clamp | per-analyzer bound | **that analyzer's own metric** | convert the GPU bound *down* into analyzer `i`'s metric through **its own** `PRC` and the variant's `GPUsPerReplica`; `ps` stays raw. No factor ⇒ no spend (`W4`). |
> | 9 | site (v) fallback | — | — | **dead** (`W2`/`W3`) — delete, do not re-denominate. |
>
> Three properties make this a closed system rather than nine independent choices:
>
> - **One conversion boundary.** Row 0 is the only place a `PRC` is applied on the way *in*; row 8 is
>   the only place one is applied on the way *back out*, and it converts a bound, never a quantity.
>   Everything between rows 1 and 6 is GPUs. This is what [§ units-conversions](#units-conversions)'
>   discipline asks for: convert once, at a named boundary, not incidentally mid-expression.
> - **The round-trip hazard is gone, not solved.** With the numerator in GPUs and the spend-time
>   factor `GPUsPerReplica` — immutable deployment topology — there is no captured-PRC value map, no
>   capture-before-refresh ordering requirement, and no [§ invariants](#invariants) #9 drift. Site
>   (ii)'s `prcRef` machinery simply has nothing to do.
> - **Only rows 5 and 7 are dimensionless, and neither is ever spent.** Both are ordering keys. That
>   is the invariant a reviewer can check mechanically: *if a number has no unit, it must not appear on
>   the left of an assignment that reduces a budget.*
>
> **No residual survives.** The one thing the audit had held back as a possible policy gap — the
> cross-model mean — is settled design; see immediately below.

**Residuals — none open. Both are recorded for their derivations:**

1. ~~**Is a cross-model mean the right reference at all?**~~ — **SETTLED DESIGN, never a residual.**
   Dean, 2026-08-07: *"cross-model mean is water fill approximation. already dsicussed. not here."*
   The audit flagged it because `target = remaining − mean` lets one model with a large claim raise the
   mean and *shrink every other model's* target, and because the `allocationMean` adjustment read like
   a symptom being managed rather than a model being applied. Both readings were local to one
   expression. Read as a whole, `fairShareScaleUp` (`greedy_score_optimizer.go:202-261`) is a
   **water-fill loop**, and the mean is the *water level*, not a quota:
   - each turn recomputes the mean over the still-active models only (`filterActive` keeps
     `remaining > 0`, `computeMean` averages them), so the level falls as claimants drain out;
   - `sortByRemainingDesc` then serves **only the head** — the largest outstanding claim — so filling
     proceeds top-down toward a common level;
   - `allocationMean` is the level adjustment, not a patch: when the head is already at or below the
     mean it lowers the bar by `remaining / len(active)` so the turn is not wasted, and when one model
     is left it drops the bar to `0` so that model takes the **whole** remaining pool;
   - the *approximation* in Dean's phrase is the one-bite rule: a model still above the mean after its
     turn is dropped (`remaining = -1`) rather than re-served, so the fill converges in one pass
     instead of iterating to an exact level.

   That same terminal step is what makes `priority: 0.00001` behave as "last in line, take the
   leftovers" — the full trace is in [§ open](#open)'s `W3` verification. **The unit table above is
   agnostic either way**: rows 3–4 are correct in GPUs whatever the reference level is. Nothing here is
   a decision-queue item and nothing here is a PR-2 item.
2. ~~**Replicas of different variants are not fungible.**~~ — **RESOLVED 2026-08-07 (Dean): the budget
   is GPUs.** This was the argument *for* the resolution, so it is recorded rather than deleted: a
   replica-denominated budget is blind to `GPUsPerReplica`, so one 1-GPU replica and one 8-GPU replica
   would draw identically against the pool. The pick already respects GPUs immediately afterward
   (`min(fairShareCap, gpusAvail/gpusPerReplica)`) and `roleDemandGPUs` already carries a
   GPU-denominated notion of demand — `fsv` simply did not use it. Non-fungibility of replicas is
   exactly why the pool cannot be denominated in them. See [§ bugs](#bugs) #5's decision block for what
   the pivot to GPU space does and does not change, and [§ limited](#limited) for the superseded
   replica-space prescription.

[↑ TOC](#toc)
