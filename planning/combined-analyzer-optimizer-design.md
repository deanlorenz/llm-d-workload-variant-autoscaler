# Combined-Analyzer Optimizer Inputs — replica-demand / coverage contract — Type 1 Design

> **Reading protocol:** Read the TOC first. Fetch only the sections you need via
> `Read <file> offset:<start> limit:<end-start+1>`. Never read the whole file up front.

**Type:** 1 (design) · **Status:** **AUTHORITATIVE** for this mission — the single design authority
for the unit/currency contract ([§ units](#units)), the enablement vocabulary and supported configs
([§ configs](#configs)), the combine rule ([§ combine](#combine)), the anchor contract
([§ anchor](#anchor)), the fair-share metric ([§ limited](#limited)), and the bug/finding inventory
([§ bugs](#bugs), [§ findings](#findings)). **Design questions that are still open are named
explicitly in [§ open](#open)** (numbered `W1`–`W5`); anything *not* listed there is settled and may
be relied on by task plans without re-deriving it. Task plans (Type 3) decide *how* and *when*, never
*what* — a "what" question surfaced mid-implementation belongs in [§ open](#open), not in the plan.

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

- [Why this doc exists {#why}](#why-this-doc-exists-why) L63:104
- [Units, currencies & legal conversions {#units}](#units-currencies--legal-conversions-units) L105:213
  - [The one contract {#units-contract}](#the-one-contract-units-contract) L112:123
  - [Per-analyzer currencies (concrete, today) {#units-currencies}](#per-analyzer-currencies-concrete-today-units-currencies) L124:158
  - [The threshold-inflated quantities {#units-thresholds}](#the-threshold-inflated-quantities-units-thresholds) L159:188
  - [Legal conversions {#units-conversions}](#legal-conversions-units-conversions) L189:213
- [Enablement vocabulary and the supported configs {#configs}](#enablement-vocabulary-and-the-supported-configs-configs) L214:262
- [The core abstraction: replica-demand & coverage {#abstraction}](#the-core-abstraction-replica-demand--coverage-abstraction) L263:309
- [The combining rule (binding analyzer) {#combine}](#the-combining-rule-binding-analyzer-combine) L310:379
  - [One vote is a pass-through, algebraically {#combine-onevote}](#one-vote-is-a-pass-through-algebraically-combine-onevote) L342:362
  - [Score is a belief weight, never a budget weight {#combine-score}](#score-is-a-belief-weight-never-a-budget-weight-combine-score) L363:379
- [The binding-analyzer anchor (renamed SatEntry) {#anchor}](#the-binding-analyzer-anchor-renamed-satentry-anchor) L380:650
  - [The two-phase mechanism {#anchor-twophase}](#the-two-phase-mechanism-anchor-twophase) L545:580
  - [What the anchor is a workaround for {#anchor-completeness}](#what-the-anchor-is-a-workaround-for-anchor-completeness) L581:618
  - [Multi-vote semantics that must be pinned down {#anchor-multivote}](#multi-vote-semantics-that-must-be-pinned-down-anchor-multivote) L619:650
- [Current code: the two-PRC split and every saturation-only site {#trace}](#current-code-the-two-prc-split-and-every-saturation-only-site-trace) L651:709
- [Latent bugs surfaced by the trace {#bugs}](#latent-bugs-surfaced-by-the-trace-bugs) L710:852
- [Traced findings: liveness, binding and role coverage {#findings}](#traced-findings-liveness-binding-and-role-coverage-findings) L853:902
- [How the cost-efficiency sort changes {#sort}](#how-the-cost-efficiency-sort-changes-sort) L903:933
- [Rescale layer trace {#rescale}](#rescale-layer-trace-rescale) L934:967
- [Bottom-line invariants {#invariants}](#bottom-line-invariants-invariants) L968:1066
- [Limited-mode (greedy fair-share) path {#limited}](#limited-mode-greedy-fair-share-path-limited) L1067:1140
- [Open questions {#open}](#open-questions-open) L1141:1282
  - [Design-level "what" questions surfaced by the currency fix (W1–W5) {#open-what}](#design-level-what-questions-surfaced-by-the-currency-fix-w1w5-open-what) L1184:1282

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
require all roles to share the same analyzer set; it works entirely in replicas and coverage.
Demand is already per-role, so logically it's equivalent to indexing demand per
`(analyzer, variant, role)` or per `(analyzer, scaled-object-target)`. We are **not** changing the
role model now.

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

- **Binder tie-break — RULE: saturation binds if present, else lowest analyzer index.** The current
  "more than one qualifying non-sat binder ⇒ return nil ⇒ hold" behavior becomes a live hazard the
  moment two healthy voters can qualify: it would silently freeze the model every cycle. The rule must
  be **deterministic and stable across allocation iterations** — an unstable tie-break combined with
  per-iteration refresh would let the binding oscillate mid-water-fill, which is worse than either
  choice. Lowest-index is the cheap stable key; saturation-first keeps the identity carrier and the
  sizing source aligned in the common case. *(Recorded here as the design rule because the
  dynamic-refresh task plan already builds on it and cited this section for it; Dean to confirm on
  review — I cannot source a prior explicit confirmation of the tie-break itself, only of the
  abstain rule below.)* See [§ findings](#findings) `N2`.
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
   `target`, and every comparison built on them) is denominated in, from *mixed analyzer-private
   capacity* to **replicas**. Because the unit changes, every site that produces or consumes that
   number must move in the **same commit** or the units desync silently — five sites, not one:

   - **(i) `fairShareValue`** — replace `Σ_i Score_i × Σ_role ps[i][role]` with a combined
     replica-space quantity, `priority × Σ_role (max_i rd_i[role] − current[role])`. **Score leaves
     `fsv` entirely** — it is a belief weight, not a budget weight ([§ combine](#combine-score)); the
     earlier hedge "× Score only if Score is meant to weight budget" is **withdrawn**. Computing
     `rd_i` needs a per-role reference variant, which `fairShareValue` does not receive today, so the
     signature gains the variant list. *This is where the anchor helps* — it already holds
     `max_i rd_i` per role, so the numerator is a read rather than a re-derivation. Contrast the
     earlier note "the anchor does not reach fsv": true *as fsv is written today* (it walks `ps`), and
     the fix is precisely to re-point it.
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
   - **(iii) scale-down tie-break `sortVariantsForScaleDown`** — a **second** `Σ_i Score_i × PRC_i[v]`
     site. Lower severity: it only orders scale-down candidates within a role (a tie-break), never
     sizes; but it is the same wrong-operator/mixed-unit pattern. Fix: tie-break on the *binder's* PRC
     (which requires the function to learn which role it is ordering), name-ascending as the final
     key, and give a variant with no scale-down ballot at all the same key today's weighted sum yields
     for that input, so that edge does not move.
   - **(iv) the picker-state clamp in `allocateForModel`** — it clamps `ps[i][role]` (raw
     analyzer-private capacity) against `target` (now replicas). Clamping capacity against a replica
     count *is* the bug. The cheap correct shape converts the **bound** into each analyzer's own
     units rather than moving `ps` into replica space:

     ```
     if cap := target * PRC_i[v_role]; ps[i][role] > cap { ps[i][role] = cap }
     ```

     `ps` stays raw capacity, which is what every downstream consumer expects
     (`roleBottleneckReplicas` divides by `PRC_i`; `allocateForModelPaired` and
     `applyDeallocationForRole` decrement in capacity). An analyzer with **no PRC** for the reference
     variant is left **unclamped**: no conversion factor exists, zeroing it would delete its vote, and
     it cannot participate in the picker for that variant anyway — so the un-enforced budget is
     harmless. Making `ps` itself replica-space would instead ripple through `initRoleState`,
     `roleBottleneckReplicas`, `allocateForModelPaired` and `applyDeallocationForRole`.
   - **(v) `fairShareValue`'s zero-result fallback** — when the weighted result is zero, `fsv`
     returns `max_{i,role} ps[i][role]`: raw remaining demand in an analyzer-private unit. Two things
     follow from the pivot. Its trigger **narrows** (with Score gone, only a non-positive `priority`
     can reach it); and left as-is it **defeats** the rule that fsv counts only demand it has a PRC to
     convert — a model whose demand is *entirely* unactionable computes `0`, drops into the fallback,
     and gets the raw inflated number back. Fix: return the unweighted **replica-space** demand, which
     is `0` when nothing participates. That preserves the fallback's real purpose — a mis-configured
     priority should not silently strand a model that genuinely needs replicas, since `fsv = 0`
     excludes it from the active set and it is then never allocated at all.

   **Multi-role (P/D) divergence, made visible by the fix but not caused by it.** `target` is a
   **scalar** summed over roles, while the cap is applied **per role**. So the per-role cap is already
   cross-role contaminated: today it is `ceil((Σ_role' d_role') / PRC_vc)`, and after the fix
   `ceil((Σ_role' d_role' · PRC_ref[role] / PRC_ref[role']) / PRC_vc)`. The two agree **iff all
   per-role reference PRCs are equal**. Whether the fair-share budget should be per-role at all is an
   open design question ([§ open](#open) `W1`) — the fix must not be read as answering it. Note that
   fixtures which give prefill and decode the *same* reference PRC cannot distinguish the two forms,
   so coverage there is coincidental, not deliberate.

   **`priority` leaks into the cap, and the fix makes the leak newly misleading.** `target =
   remaining − mean` and `remaining = priority × demand`, so `ceil(target)` is a **priority-scaled**
   replica count, not a replica count. This is pre-existing and unchanged by the fix (today's
   `target / PRC` is equally priority-scaled, so the number moves identically) — but after the fix the
   expression *reads* like a replica count. Whether priority belongs at the spend or only in the
   ordering is [§ open](#open) `W2`; until that is answered the honest description is
   "priority-scaled replicas."

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
| **`N8`** | **Drop the (b)-sizing fallback entirely** rather than `Live`-gate it. The fallback fires exactly when saturation is untrustworthy, so gating it is nearly vacuous; and mixing saturation's sizing into a TA-bound anchor mixes metric scales, which is the very error this design exists to remove. Abstain (`PRC = 0`) instead. | Design decision | **Adopted.** Dissolves `N1` and the fallback half of `N5`, and **revises** the enablement-gated-fallback decision recorded in the anchor task's plan. Lands in the dynamic-refresh task. |
| **`N9`** | The reactive from-zero engine is a separate controller runnable, takes no budget limiter, and wakes **every** inactive variant rather than the cheapest. It is the only mechanism that wakes a fully-cold model under the saturation-only default. | Pre-existing, out of scope | Out of anchor scope entirely; relevant to any future cost/budget layer over from-zero. |

**Why `VG-up` was deferred rather than fixed in the anchor task** (Dean, 2026-08-06). As shipped, a dead
analyzer causes no spurious scale-up *or* scale-down: scale-down is `Live`-filtered at both gates, and
scale-up sees `RC = 0` from a dead analyzer (or skips it entirely on the nil-result guard). Full
from-zero is driven by a *live* analyzer by construction. So the `Live` filter is **hardening**, not a
correctness fix — and it belongs with the multi-vote work that makes the hazard reachable, where it can
be tested against a genuinely multi-vote ballot instead of asserted. The caveat that must travel with
the deferral: scale-up safety is *emergent*, resting on "dead ⇒ `RC = 0`". **A future analyzer that
carries forward a stale-but-informative `RC > 0` with an aged timestamp breaks it silently** — no test
fails, the system just scales on stale belief.

**The invariant the liveness fixes must establish.** Once the vote prune is `Live`-filtered, the binder
set is a subset of the voting set, so: **a non-nil anchor implies a non-empty voting set.** The
contrapositive is the safety property worth naming — an empty voting set implies a nil anchor, which
implies **hold**, never an unguarded scale-down. Deriving the anchor from the **full** ballot (before
pruning) is what keeps identity available even when every voter is dead, so the two must not be
collapsed into one filtered pass.

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

> ⚠️ **GPU space vs replica space — this prescription is not the shipped decision.** The paragraph
> above was written before the fix was scoped, and it asserts two things the implementation does not
> do: (1) the metric is denominated in **GPUs** (`× gpusPerReplica`); (2) therefore
> `fairShareCap` "collapses to `target` replicas (no PRC division)". The fix denominates in
> **replicas**, not GPUs, and the cap is **not** a bare `ceil(target)` — it is a round-trip rescale
> `ceil(target · PRC_ref[role] / PRC_vc)` ([§ bugs](#bugs) #5 site (ii)). Replica space is the
> smaller change: GPU space would require every fair-share consumer to learn `gpusPerReplica`, and
> heterogeneous-accelerator roles make `gpusPerReplica` variant-dependent — so the two spaces are
> *not* interchangeable by a constant factor. **Which space the fair-share budget should ultimately
> live in is open** ([§ open](#open) `W5`); replica space is what ships, and the GPU-space argument
> is retained because it is the one that connects the budget to the resource actually being rationed.

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

### Design-level "what" questions surfaced by the currency fix (W1–W5) {#open-what}

**Provenance and status.** These five were surfaced by a coder implementing the [§ bugs](#bugs) #5
currency pivot (2026-08-07) and were **migrated here from the task plan**, which is the wrong
instrument for them: they are properties of the fair-share *model*, not of a commit. They are **open**
— nothing below is decided. They are recorded so that the fix's silence on them is not read as a
decision.

**The rule the currency fix follows:** every W item is **status-quo-preserving**. The fix changes the
*currency* of the fair-share budget and nothing else; wherever a W question is live it reproduces
whatever today's code answers, in the new units. A coder must not resolve a W item while implementing
— a site that cannot be converted without picking a side is a handoff, not a judgment call.

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

**W5 — Is the mean of models' fair-share values a meaningful reference, and in what unit?**

`computeMean` is a plain arithmetic mean over active models' `remaining`, and `sortByRemainingDesc`
orders by the same number. Today it averages tokens against req/s across models with unequal PRCs —
that is [§ bugs](#bugs) #5, and the currency fix repairs it. Two questions survive the fix:

1. **Is a cross-model mean the right reference at all?** `target = remaining − mean` means one model
   with a large claim raises the mean and *shrinks every other model's* target. The `allocationMean`
   adjustment patches the case where that would zero out the leader, which reads like a symptom being
   managed rather than a model being applied. A pool- or accelerator-scoped reference is the obvious
   alternative and is not what the code does.
2. **Replicas of different variants are not fungible.** The cap yields a replica count blind to
   `GPUsPerReplica`, so one 1-GPU replica and one 8-GPU replica draw identically against the budget.
   The pick *does* respect GPUs immediately afterward (`min(fairShareCap, gpusAvail/gpusPerReplica)`)
   and `roleDemandGPUs` shows the codebase already has a GPU-denominated notion of demand — `fsv`
   simply does not use it. **A replica-space budget is more coherent than a tokens-vs-req/s one and
   still is not a resource-space one.** This is also the open half of [§ limited](#limited)'s GPU-space
   prescription: saying so here keeps "we fixed the currency" from being read as "the currency is now
   right".

[↑ TOC](#toc)
