# Combined-Analyzer Optimizer Inputs — replica-demand / coverage contract — Type 1 Design

> **Reading protocol:** Read the TOC first. Fetch only the sections you need via
> `Read <file> offset:<start> limit:<end-start+1>`. Never read the whole file up front.

**Type:** 1 (design) · **Status:** DRAFT (capture of a live design discussion, 2026-08-02;
not yet locked). **Scope:** the engine→optimizer→rescale contract for combining analyzer
signals, and the abstraction that makes **disabling saturation-v2** a clean change rather than a
coupled one. **Sibling docs:** [`multi-analyzer-design.md`](multi-analyzer-design.md) (F1
"pre-analysis extraction"), [`optimizer-coordination-design.md`](optimizer-coordination-design.md)
(P/D role-ceiling clean model), [`wva-analyzer-lifecycle-plan.md`](wva-analyzer-lifecycle-plan.md)
(Half-B = "genuinely disable saturation", currently unscoped — this doc is its missing design).

## TOC {#toc}

- [Why this doc exists {#why}](#why-this-doc-exists-why) L28:53
- [The core abstraction: replica-demand & coverage {#abstraction}](#the-core-abstraction-replica-demand--coverage-abstraction) L54:97
- [The combining rule (binding analyzer) {#combine}](#the-combining-rule-binding-analyzer-combine) L98:130
- [The binding-analyzer anchor (renamed SatEntry) {#anchor}](#the-binding-analyzer-anchor-renamed-satentry-anchor) L131:176
- [Current code: the two-PRC split and every saturation-only site {#trace}](#current-code-the-two-prc-split-and-every-saturation-only-site-trace) L177:227
- [Latent bugs surfaced by the trace {#bugs}](#latent-bugs-surfaced-by-the-trace-bugs) L228:273
- [How the cost-efficiency sort changes {#sort}](#how-the-cost-efficiency-sort-changes-sort) L274:294
- [Rescale layer trace {#rescale}](#rescale-layer-trace-rescale) L295:328
- [Bottom-line invariants {#invariants}](#bottom-line-invariants-invariants) L329:362
- [Limited-mode (greedy fair-share) path {#limited}](#limited-mode-greedy-fair-share-path-limited) L363:423
- [Open questions {#open}](#open-questions-open) L424:443

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
§ Supply taxonomy. The **anticipated-supply bug** ([§ bugs](#bugs) #4, CONFIRMED) is exactly a
numerator that drops `pending` — pending belongs in `n`, never in the denominator.

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
(`max`/`min`). `fairShareValue` (`greedy_score_optimizer.go:61`) instead does `Σ_i Score_i·…` — a
Score-weighted **sum** across analyzers, which over-counts (3 analyzers each wanting 5 replicas ⇒
sum reflects 15, not the correct bottleneck 5). See [§ bugs](#bugs) #5 and [§ limited](#limited).

[↑ TOC](#toc)

## The binding-analyzer anchor (renamed SatEntry) {#anchor}

**Dean's proposal (2026-08-02), still under consideration.** Instead of scattering combined-PRC /
combined-demand through every call site, keep the special entry — but **rename it and repurpose it
as the "binding analyzer" anchor**:

- The engine creates **two copies** before the veto / scale-up/down code:
  - a **common-scope** entry — always populated (even when sat-v2 disabled) — holding topology
    (accel, cost, role, replica count) **plus** the *combined* PRC and *combined* demand/coverage
    per `(role, v)`, i.e. always representing the **binding analyzer's** values. Returned by the
    (renamed) `SatEntry` helper. It is **not** part of the analyzer voting list.
  - a **sat-v2-scope** entry — created and populated **only when sat-v2 is enabled** — the actual
    saturation vote, appended to the voting list like any other analyzer.
- Because the anchor always carries the *binding* analyzer's PRC/demand per `(role,v)`, **all the
  existing single-analyzer optimizer logic keeps working as-is** — `costEfficiency`,
  `fairShareCap`, `roleDemandGPUs`, the utilization write-back all read the anchor and now get the
  correct combined values instead of saturation-only ones.
- The anchor is **updated each iteration** of the allocation loop so it always reflects the
  current binding analyzer (the binding analyzer can change as replicas are added and coverage
  shifts). This is the key subtlety: binding is state-dependent, so the anchor is recomputed, not
  computed once.
- **Mutability is new state, not the existing struct** (Dean, 2026-08-03). Today the working
  *counters* (`Remaining`/`Spare`/`RoleSpare`) are mutable, but `Result.VariantCapacities` — where
  PRC lives — is treated as **immutable topology** ("The original Result values are never mutated,"
  `optimizer_interfaces.go:20`). The anchor's combined PRC + coverage are **new mutable working
  fields** refreshed each round; do not overload the immutable topology PRC for this.
- **Binding resolved per-entry** (Dean, 2026-08-03). The anchor is a *list* of per-variant entries,
  each with its own `Role` — so per (role, variant) binding ([§ combine](#combine)) drops in
  naturally: each entry independently holds its binding analyzer's PRC/coverage. No model-global
  binding assumption anywhere.

**Why this is attractive:** it localizes the change to (a) how the engine builds the anchor and
(b) keeping it refreshed in the loop — the dozens of downstream read sites are untouched. It also
makes the metadata-carrier/vote split fall out naturally (the anchor is the carrier; the vote is a
list entry).

**Open risk to resolve before locking:** "always the binding analyzer" is per `(role, v)` and
per-iteration. A single scalar `PerReplicaCapacity` on one anchor entry can only hold one variant's
binding PRC at a time; the anchor is a *list* of `VariantCapacity` (one per variant), so per-variant
binding PRC fits — but the *cost-sort* needs the binding analyzer that would apply *at that
variant's marginal replica*, which is exactly what the per-iteration refresh provides. Confirm the
refresh granularity (per role-pick iteration) is enough, or whether the sort needs its own binding
resolution. See [§ sort](#sort) and [§ open](#open).

[↑ TOC](#toc)

## Current code: the two-PRC split and every saturation-only site {#trace}

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

4. **Anticipated-supply in the denominator — CONFIRMED** (not masked-by-single-analyzer; a genuine
   bug today). `achieved`/coverage puts `current` supply in the numerator but folds `anticipated`
   (booting/pending) into the **denominator** via RC, so pending replicas *raise* apparent demand
   instead of counting as already-serving supply. Per [§ abstraction](#abstraction), pending belongs
   in the numerator `n = actual+pending`. This is the coordination doc's **D1 / Open-issue #2**
   ([`optimizer-coordination-design.md`](optimizer-coordination-design.md)): fix = numerator
   `current + anticipated + committed_so_far`, denominator `desired = demand/threshold` (fixed).
   Dean (2026-08-03): confirmed, must be solved. Needs the exact call-site trace (where RC folds
   pending) before we size the fix.

5. **`fairShareValue` sums across analyzers instead of maxing** (`greedy_score_optimizer.go:61`).
   `fsv = priority × Σ_i Score_i × Σ_role ps[i][role]` is the **only** cross-analyzer combine in the
   codebase that uses `Σ_i`; every other site uses the bottleneck `max_i`/`min_i`. Two independent
   errors: (a) `ps[i]` is per-analyzer native units → the sum is dimensionally mixed (same as #2);
   (b) even in common units, summing over-counts vs the binding `max_i` and misorders models
   ([§ limited](#limited)). Fix: `remaining = priority × Σ_role (desired[role] − current[role])`
   with `desired = max_i rd_i`. Note the anchor swap does **not** reach this — `fsv` reads
   `pickerState`, not the anchor. (Contrast `roleAggRemaining` #2, which already uses `max_i` — only
   its units are wrong; `fsv` has *both* the wrong operator and wrong units.)

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
   combined demand = sat demand, combined coverage = sat coverage, topology unchanged; and the
   per-iteration refresh must be a **no-op** (single analyzer ⇒ binding never shifts ⇒ PRC constant
   across rounds, matching today where VariantCapacities PRC is never mutated). This holds *by
   construction* but must be **guaranteed and tested** — the risk is entirely in the anchor-building
   code applying a transform that isn't identity-for-n=1 (e.g. re-deriving coverage with a different
   numerator than sat-v2 emits today). **Required test:** with only saturation registered, assert
   `anchor == saturationEntry` field-for-field (PRC, demand, coverage, topology) — before, during,
   and after allocation iterations.

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
models; allocation spends GPUs directly; and `fairShareCap` collapses to `target` replicas (no PRC
division) — PRC survives **only** in the `demand/PRC` conversion and the cost-efficiency sort, exactly
as the mental experiment predicts. This is the "simplifies cross-analyzer math" half of the PRC=1
experiment made concrete.

**Verdict.** The replica-demand/coverage abstraction *does* cover limited-mode, and PRC drops out of
the fair-share loop the same way — but limited-mode has **two** leak sites, not one: (a) the sizing
PRC (fixed by the anchor, like unlimited-mode) and (b) the fair-share *metric* `fsv` (needs its own
move to GPU/replica units; the anchor does not reach it). Fixing (a) without (b) leaves the
cross-model ordering unit-mixed. So limited-mode is a strictly larger change than unlimited-mode —
worth calling out for scoping.

Other limited-mode sites checked and **OK**: `anyRoleNeedsScaleUp(ps, roles)` is a per-analyzer OR
(scale up if *any* analyzer wants more), which equals `max_i rd_i > current` — consistent with the
combined `desired`. `applyAllocation` decrements per-analyzer PRC. The paired-commit
`allocateForModelPaired` carries the same `k`/decrement unit-mismatch as unlimited-mode
([§ bugs](#bugs) #1) — it is shared code, so one fix covers both modes.

[↑ TOC](#toc)

## Open questions {#open}

1. **Anchor refresh granularity.** *Resolved: refresh each allocation iteration* (Dean, 2026-08-03).
   Remaining sub-question: does per-role-pick-iteration refresh suffice for the **cost-sort**, or
   does the sort need its own binding resolution at sort time? ([§ anchor](#anchor), [§ sort](#sort)).
2. **Relationship to F1 / Half-B.** `wva-analyzer-lifecycle-plan.md` Half-B ("genuinely disable
   saturation") was rejected as unscoped and pointed at F1 "pre-analysis extraction"
   (`multi-analyzer-design.md:506-511`). This doc *is* that missing design. Decide whether Half-B
   becomes a task plan derived from this doc.
3. ~~Anticipated-supply-in-denominator suspicion~~ — *Resolved: CONFIRMED bug* (Dean, 2026-08-03);
   moved to [§ bugs](#bugs) #4. Still needs the exact call-site trace (where RC folds pending)
   before sizing the fix.
4. ~~Anchor demand per role vs per (role,variant)?~~ — *Resolved* (Dean, 2026-08-03): binding is
   per (role, variant) and the anchor holds it per-entry ([§ combine](#combine), [§ anchor](#anchor)).
   Store combined PRC + `rd`/coverage per variant entry; role demand once per role.
5. **Exact locations for the two fixes the anchor does NOT cover.** Bug #4 (RC folds pending) and
   bug #5 (`fsv` sum) both live outside the anchor's read path. Trace both to precise call sites and
   decide whether they land in the same task as the anchor or as separate commits.

[↑ TOC](#toc)
