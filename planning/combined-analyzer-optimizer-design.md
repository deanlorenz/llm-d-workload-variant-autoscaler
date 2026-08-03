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

- [Why this doc exists {#why}](#why-this-doc-exists-why) L28:69
- [The core abstraction: replica-demand & coverage {#abstraction}](#the-core-abstraction-replica-demand--coverage-abstraction) L70:116
- [The combining rule (binding analyzer) {#combine}](#the-combining-rule-binding-analyzer-combine) L117:149
- [The binding-analyzer anchor (renamed SatEntry) {#anchor}](#the-binding-analyzer-anchor-renamed-satentry-anchor) L150:305
- [Current code: the two-PRC split and every saturation-only site {#trace}](#current-code-the-two-prc-split-and-every-saturation-only-site-trace) L306:356
- [Latent bugs surfaced by the trace {#bugs}](#latent-bugs-surfaced-by-the-trace-bugs) L357:437
- [How the cost-efficiency sort changes {#sort}](#how-the-cost-efficiency-sort-changes-sort) L438:468
- [Rescale layer trace {#rescale}](#rescale-layer-trace-rescale) L469:502
- [Bottom-line invariants {#invariants}](#bottom-line-invariants-invariants) L503:570
- [Limited-mode (greedy fair-share) path {#limited}](#limited-mode-greedy-fair-share-path-limited) L571:631
- [Open questions {#open}](#open-questions-open) L632:671

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
(`max`/`min`). `fairShareValue` (`greedy_score_optimizer.go:61`) instead does `Σ_i Score_i·…` — a
Score-weighted **sum** across analyzers, which over-counts (3 analyzers each wanting 5 replicas ⇒
sum reflects 15, not the correct bottleneck 5). See [§ bugs](#bugs) #5 and [§ limited](#limited).

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

**Implementation note (coder-deferred).** The exact partition of the struct's fields into (a) vs (b),
and the precise copy mechanism, are lower-level decisions left to the coder — "it should be more cleanly
split, but not now" (Dean). Two equivalent mechanisms produce the same optimizer inputs: (i) put
sat-v2's (b) on the ballot only when sat-v2 is enabled, then copy the first entry's (b) onto the anchor;
or (ii) always full-copy sat-v2's (a)+(b) into the anchor, and copy the first entry's (b) only when
sat-v2 is *not* on the ballot (when it is, its (b) is already the anchor's and it is first). Both yield
the same end state: **anchor = (a) + (b, the binding analyzer's); ballot = (b) per analyzer.**

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
  are separate: TA-only disables sat-v2's vote yet still runs it. TA **consumes some of sat-v2's
  outputs for its own analyzer calculation**, *upstream* of anchor construction — so sat-v2 must run
  before TA in analyzer order, and TA-alone still relies on sat-v2 running. Consequence: F1
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

5. **`fairShareValue` sums across analyzers instead of maxing — TRACED 2026-08-03 to three
   lock-step sites** (limited/fair-share mode only; the cost-aware unlimited path does not use fsv).
   `fsv = priority × Σ_i Score_i × Σ_role ps[i][role]` (`greedy_score_optimizer.go:61-93`, the sum at
   `:73`) is a cross-analyzer combine that uses `Σ_i` where the binding rule uses `max_i`. Two
   independent errors: (a) `ps[i][role]` is per-analyzer native-unit RC → the `Σ_i` is dimensionally
   mixed (same root as #2); (b) even in common units, summing over-counts vs the binding `max_i` and
   misorders models. The error **propagates through the whole fair-share chain**, so a fix touches
   three sites in lock-step:
   - **(i) `fairShareValue:73`** — replace `Σ_i Score_i × Σ_role ps[i][role]` with a combined
     replica/GPU-space quantity: `Σ_role (max_i rd_i[role] − current[role])` (× priority, and × Score
     only if Score is meant to weight budget). *This is where the anchor helps* — the anchor already
     holds `max_i rd_i` per role, so the fix is to have `fsv` **read the anchor's combined per-role
     replica-demand instead of iterating per-analyzer `ps`**. Contrast the earlier note "anchor does
     not reach fsv": correct *as fsv is written today* (it walks `ps`), but the fix is precisely to
     re-point it at the anchor — so the anchor does cover the numerator once fsv is rewritten.
   - **(ii) `fairShareRolePick` → `fairShareCap` (`:421`)** — `ceil(target / vc.PerReplicaCapacity)`
     divides the fsv-unit `target` (`= w.remaining − mean`, `:271`) by topology PRC_sat. Once `target`
     becomes replica/GPU-space (fix i), this division is wrong (double-converts); the pick must convert
     GPUs→replicas via `gpusPerReplica`, or use replica-space `target` directly. Must change in the
     same commit as (i) or the units desync.
   - **(iii) scale-down tie-break `sortVariantsForScaleDown` (`cost_aware_optimizer.go:161-184`,
     weighted sum at `:168`)** — a **second** `Σ_i Score_i × PRC_i[v]` site (documented at `:156`).
     Lower severity: it only orders scale-down candidates within a role (a tie-break), never sizes;
     but it is the same wrong-operator/mixed-unit pattern and should be swept in the same fix (use the
     binding `max_i` PRC, or drop the cross-analyzer weight for a topology-only tie-break).

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

1. ~~Anchor refresh granularity / does the cost-sort need its own binding resolution?~~ — *Fully
   resolved 2026-08-03.* Refresh each allocation iteration (Dean); and the sort is already re-run
   once per (role, iteration) inside the pick closure, so per-iteration refresh feeds it directly —
   **no separate sort-time binding resolution needed** ([§ sort](#sort) "Sort cadence").
2. ~~**Relationship to F1 / Half-B.**~~ — *Resolved 2026-08-03.* This doc **is** the missing Half-B
   design; Half-B becomes a task plan derived from it (Dean's ship decision — [§ why](#why)). F1
   "pre-analysis extraction" is **not a prerequisite and not a cost saver**: sat-v2 always runs and
   always produces the metadata the anchor copies (TA even consumes some sat-v2 outputs for its own
   calculation), so the metadata is always present without extracting it ([§ anchor](#anchor) "always
   runs and always produces the metadata"). F1 is simply unnecessary for enabling TA.
3. ~~Anticipated-supply-in-denominator suspicion~~ — *Resolved 2026-08-03: TRACED, verdict
   DOWNGRADED.* Not an active sizing bug — RC correctly nets out current+pending; the only
   pending-blind quantity is the observability `Utilization`. Full trace in [§ bugs](#bugs) #4.
   Follow-up: update coordination-doc D1/#2 to match.
4. ~~Anchor demand per role vs per (role,variant)?~~ — *Resolved* (Dean, 2026-08-03): binding is
   per (role, variant) and the anchor holds it per-entry ([§ combine](#combine), [§ anchor](#anchor)).
   Store combined PRC + `rd`/coverage per variant entry; role demand once per role.
5. ~~Exact locations for the two anchor-external fixes~~ — *Resolved 2026-08-03 (traced).* Bug #4 is
   downgraded (no sizing fix needed; observability-only). Bug #5 (`fsv`) is pinned to three lock-step
   sites — `fairShareValue:73`, `fairShareCap:421`, and the scale-down tie-break
   `sortVariantsForScaleDown:168` ([§ bugs](#bugs) #5). Open decision: does the `fsv` rewrite land in
   the same task as the anchor (it re-points `fsv` at the anchor) or as a separate limited-mode commit?
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

[↑ TOC](#toc)
