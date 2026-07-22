# Optimizer Coordination — Clean Design & Discussion Capture

**Status:** DISCUSSION CAPTURE / DRAFT (2026-07-15). Working doc from a planner↔Dean design
session. Purpose: state the *intended* logic and data flow of analyzers + optimizers cleanly,
separated from implementation, so we can then verify the code follows it and restructure the Type 4
dev-guide (`docs/developer-guide/multi-analyzer-pipeline.md`) into a clean-design section +
an implementation section. **Not yet reflected in code or dev-guide.**

**Type:** Type 1 (design) — concepts and algorithm, plans-branch only.

**Scope note:** grew out of the `optimizer-pd-role-ceiling` fix, but the model here is general
(all analyzers/optimizers, not just P/D).

---

## Resume — where we stopped (2026-07-15)

Phased effort, driven by Dean, developing the algorithm's clean statement before touching more code:

- **Phase 1 — capture the discussion:** DONE (§ The agreed mental model, § Open issues).
- **Phase 2 — clean logical & data flow:** DONE. Principles in § Clean design; Dean's 2026-07-15
  review folded in (mental-model refinements: pos/neg-gap asymmetry, supply overloading, verify
  `remaining` vs. #1129; issues 1/5/6/7/8 updated — min+delta adopted, fair-share deferred to its
  own discussion, two-phase per-loop + no-cross-allocation-correlation, limiter shape flagged for
  verification).
- **Phase 2.5 — end-to-end design:** DRAFTED (new § End-to-end design — data flow & logic). Built
  on a **supply taxonomy** (current / anticipated / desired / available). **Awaiting Dean's
  confirmation of the four supply definitions + where each enters** — the whole flow rests on them.
- **Phase 3 — verify code vs. this model:** FIRST PASS DONE (scale-up), see § Implementation
  mapping. Found **D1 = the suspected bug, confirmed**: `achieved` drops booting/pending supply
  (numerator uses `TotalSupply`=current, should use `TotalAnticipatedSupply`=current+pending); the
  `RC≤0` clamp is a partial patch; one-field fix makes the clamp redundant. Also D2 (denom via
  clamped RC), D3 (pickerState dual-representation), D4 (limiter not on this branch — verify vs.
  #1129). **Still TODO:** scale-down path; limiter/#1129; and the **decision: fix D1 in this PR vs.
  follow-up.**

**Also uncommitted right now:** planner made edits directly to the Type 4 dev-guide
(`docs/developer-guide/multi-analyzer-pipeline.md`) in the `optimizer-pd-role-ceiling` worktree —
a worked example, an edge-case→behavior→test table, a "why roles are coupled" paragraph, and the
`saturationRoleView` single-source note. **These are UNCOMMITTED** (`git status` shows `M` on that
file, tip `0c33a3eb`). They are the *incremental* dev-guide improvements; the *structural* clean/
implementation split described in this doc is the larger follow-on, not yet applied to the dev-guide.

**Next action on resume:** get Dean's answer to the two Phase-2 questions, finish/lock the clean
design, then do Phase 3 (verify code vs. each numbered point; resolve open issues 1–4 as fix-now
vs. follow-up), then restructure the dev-guide into clean-design + implementation sections.

---

## Why this doc exists

The current dev-guide documents the code's *shape* faithfully, but it is hard to follow: the
algorithm reads as a pile of snapshots (`denom`, `trueRC`, `pickerState`, `roleBottleneckReplicas`)
with no clean statement of what is being computed or why. We want:

1. A **clean statement of the intended logic and data flow** — no implementation details.
2. **Then** an implementation section that maps the clean model onto the code and *verifies* the
   code follows it.
3. A **clear separation** between the two. Legacy implementation artifacts are acceptable (e.g.,
   saturation V2 computing per-variant metadata on behalf of all analyzers) *as long as* they are
   called out as artifacts, not presented as the design.

The reader should come away understanding the **scope and logic of analyzers vs. optimizers**
without reading the code: analyzers produce utilization (desired vs. achieved); optimizers
coordinate; there are two kinds of coordination (AND / OR); the optimizer solves toward a target
subject to constraints.

---

## The agreed mental model (rationale, developed step by step)

Captured from the 2026-07-15 discussion. Each point is agreed unless flagged in § Open issues.

1. **Analyzers are metric providers.** Each analyzer provides, per *item* — a combination of
   (namespace, model, role, variant, analyzer) — a **demand** and a **threshold (≈ PRC,
   per-replica capacity)**. Desired replica count is `demand / PRC`; the scaling gap is
   `(demand − supply) / PRC`. The threshold is just an adjustment to PRC (dividing demand by a
   utilization target is identical to multiplying PRC by it), so it does not change the bigger
   picture.
   *Sign of the gap matters:* a **positive** gap (`demand > supply`) is scale-**up**; a
   **negative** gap is scale-**down**. The two use different thresholds (`scaleUpThreshold` vs
   `scaleDownBoundary`, so a deliberate no-op dead-band exists between them) and — critically —
   different coordination: scale-**up** is jointly coupled across roles (this doc's focus), while
   scale-**down** is per-role independent. The clean design below is stated for scale-up; the
   scale-down path is noted where it diverges.

2. **Combining across analyzers, within a variant, is done in "replicas."** Different analyzers'
   desired replica counts for the same variant are on the same scale (replicas), so they combine
   as a **max** (satisfy the most-demanding analyzer). Thresholds are per-analyzer PRC
   adjustments and don't change this.

3. **Combining across variants and roles cannot be done in replicas — switch to utilization.**
   Normalize everything by total demand: `utilization = supply / total_demand`. Utilization is
   additive across variants (10% on A + 20% on B = 30% supplied) and comparable across roles.
   Convert any supply to `supply / total_demand`, and any PRC to `PRC / total_demand`, so every
   analyzer's contribution is expressed in the same unit and can be summed across variants and
   min-ed across roles.
   *Caveat — "supply" is overloaded.* It can mean **current** (existing running), **anticipated**
   (booting/pending), **desired** (the target we're solving for), or **available** (what limits
   permit us to allocate). These enter the math in different places and conflating them is the
   root of the anticipated-supply bug (§ Open issues #2). The end-to-end design pins each one —
   see § End-to-end design, "Supply taxonomy."

4. **Optimizers coordinate across scaled targets** (variant, role, model, …). Simplest form (no
   limits): each target grows independently until it reaches 100% utilization.
   - Across **variant alternatives** → **SUM** of utilizations (OR-logic: any alternative helps).
   - Across **roles** → **MIN** of utilizations (AND-logic: every role must be served).
   - (A margin `min(...) + delta` is a possible *extension point* to slightly relax role coupling
     — **not** in the design or the code today.)

5. **Achieved utilization is a stateless, pure function of the planned allocation.** At any point
   it can be recomputed directly from the current allocation: `supply / demand`, summed (OR) over
   variants, min-ed (AND) over roles. It is not something to store and mutate.

6. **Getting "stuck on a limit" is not a special case.** Each round takes an incremental step
   toward 100%. Whatever is allocated still translates to a utilization number. It does not matter
   *which* target is capped or *why* (fair-share, maxReplicas, quota). The rule is uniform: **a
   candidate step that does not increase achieved utilization is not taken.** Under AND-logic, more
   replicas on a role that don't raise the min are not taken; under OR-logic, a variant with no
   headroom is not taken. Same computation regardless of the reason.

7. **The stopping condition is orthogonal and per-demand.** Stop the loop for a *specific* demand
   (per model / per coordinated allocation) once no remaining alternative would increase its
   utilization. Do not stop other demands — they continue in later rounds as long as resources
   remain that would increase *their* utilization.

8. **Only the planned allocation is dynamic.** Everything else is fixed input, computed once by the
   analyzers and never changed: total demand, PRC, the conversion to utilization (with thresholds
   applied), and current supply (existing + anticipated). The only moving quantity is the concrete
   planned allocation so far; achieved utilization is derived deterministically from it.

9. **State during allocation should be named for what it is.** Three explicit quantities:
   - **budget** — how much this coordinated allocation is *allowed* to add this round (fair-share
     / quota / maxReplicas headroom);
   - **achieved** — utilization delivered by the planned allocation so far;
   - **remaining** — missing utilization, always exactly `1.0 − achieved`.
   These must not be conflated (see § Open issues — the numerator bug was a conflation of *budget*
   with *remaining*).
   *To verify against PR #1129 (quota-based limiter):* the identity `remaining = 1.0 − achieved`
   is defined purely by demand (`achieved = supply/demand_target`) and must stay independent of
   limits — a quota caps the **budget** (how much you may add), never the **remaining** (how much
   demand is unmet). Confirm the 1129 code doesn't let a quota shrink the remaining/achieved
   figures themselves (that would repeat the budget-vs-remaining conflation at the quota layer).

> **See also — external interface (2026-07-21).** The metric-based analyzer-interface proposal
> (`planning/analyzer-metric-interface-proposal.md` → `docs/proposals/analyzer-metric-interface.md`,
> PR [#1444](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1444)) is the *interface*
> counterpart to this *coordination* design: analyzers there emit `(demand, target)` per item, and
> this doc owns how the optimizer coordinates them. It reinforces the role model here — **per-role
> demands are not comparable in absolute terms** (prefill vs decode measure different things), so role
> coordination is done in **utilization** space with **no cross-role demand normalization**, which is
> exactly the *min over role utilizations* rule (point 4 / Stage 2).

---

## Clean design — logical & data flow (desired; NO implementation)

Frame: **Analyzer → utilization (desired & achieved). Optimizer → coordinate. Two coordination
logics (AND / OR). Constraints the optimizer solves against.**

### Item and scope

- **Item** = (namespace, model, role, variant, analyzer). The finest granularity of a metric.
- **Coordinated allocation** = per **demand**, i.e. per (namespace, model) utilization target. This
  is the unit the optimizer drives to 100%.
- **Role** is not a first-class actor — it is just the **AND aggregation signal**. Variant (and
  model, for fair-share) is the **OR aggregation signal**. Analyzer is a **max** within a variant.

### Stage 1 — Analyzers produce utilization

Per item, each analyzer emits fixed inputs: **demand**, **PRC** (threshold folded in), and
**current supply = existing + anticipated**. From these, two utilization quantities:

- **desired** = the target (1.0, or a threshold-adjusted target).
- **achieved** = `current_supply / demand_target` — how much of demand is already served, counting
  both existing and anticipated (booting) replicas.

Everything downstream is in utilization units, so it is additive across analyzers/variants and
comparable across roles.

### Stage 2 — Optimizer coordinates (AND / OR)

The optimizer raises **achieved** toward **desired**, combining item utilizations by two rules:

- **OR (sum)** — across variant alternatives (and across models, for fair-share). Total supplied
  utilization for a role = sum over its variants.
- **AND (min)** — across roles. A model's utilization = `min` over its roles. Raising a
  non-bottleneck role does nothing until the bottleneck moves.

### Stage 3 — Constraints the optimizer solves against

The optimizer maximizes achieved utilization subject to:

- **maxReplicas** per variant,
- **GPU budget / quota** per accelerator type (limited mode),
- **fair-share budget** per model per round (greedy, cross-model OR).

All constraints act identically: they cap how much a candidate step can add. A capped step whose
utilization increase is zero is simply not taken — **the constraint's identity is irrelevant to the
allocation math.**

### Stage 4 — Rounds and state

- **Only dynamic state:** the planned allocation (replicas per item).
- **Derived every round** (never stored/mutated): achieved utilization per role and per model;
  remaining = `1.0 − achieved`.
- **Each round:** propose candidate additions; compute the utilization increase they would yield
  under AND/OR logic and the constraints; commit only the increase that raises achieved. The AND
  (min) bound trims every role to the current bottleneck ceiling.
- **Stop** a model when no candidate raises its achieved; continue other models while resources
  remain that raise theirs.

---

## End-to-end design — data flow & logic (DRAFT 2026-07-15)

The § Clean design above states *principles*. This section is the *end-to-end* design: the concrete
data flow, stage by stage, that those principles imply — the material that should seed the
rewritten dev-guide once verified against code. Design-level only; code symbols appear only as
"verify" anchors.

> **Confirm-first:** the whole flow rests on the **supply taxonomy** below. Please confirm those
> four definitions and where each enters before we build on them — everything downstream inherits
> any error here.

### Supply taxonomy (the backbone)

"Supply" is four distinct quantities. Naming them apart is what dissolves the anticipated-supply
bug (§ Open issues #2) and the budget-vs-remaining conflation (§ Open issues #1).

| Term | Definition | Unit | Where it enters | Dynamic? |
|---|---|---|---|---|
| **current supply** | ready, running replicas × PRC | capacity | numerator of *achieved* | fixed input (per cycle) |
| **anticipated supply** | committed-but-not-ready (booting/pending) × PRC | capacity | numerator of *achieved* (it *will* serve demand) | fixed input (per cycle) |
| **desired supply** | `demand / threshold` — supply that meets demand at the target utilization | capacity | **denominator** (the demand target); *achieved = 1.0* means "fully provisioned at target" | fixed input (per cycle) |
| **available supply** | what limits permit us to *add* this round = `min(physical inventory remaining, quota remaining, maxReplicas headroom)` | replicas / capacity | the **budget** — caps how much a step may add; **never** touches achieved/remaining | dynamic — recomputed before each allocation (issue #7) |

From these:

```
demand_target_role   = demand_role / threshold          (= desired supply for the role)
achieved_role        = (current_supply_role + anticipated_supply_role + committed_so_far_role)
                       / demand_target_role
remaining_role       = 1.0 − achieved_role              (demand-defined; limit-independent)
```

The **only** dynamic term in `achieved` is `committed_so_far` (the planned allocation). Everything
else is a per-cycle constant. `available supply` is a *separate* dynamic quantity — the budget —
and it must never appear in `achieved`/`remaining`.

*Verify against code:* today `achieved` uses `current` in the numerator and folds `anticipated`
into the *denominator* (via `RC`), which is the suspected bug (#2). The clean form above puts
**both** current and anticipated in the numerator and uses `desired supply` as a fixed denominator.

### Stage-by-stage flow (scale-up)

1. **Analyzers → per-item metrics.** Each analyzer, per (ns, model, role, variant), emits: demand,
   PRC (threshold folded in), current supply, anticipated supply. *(Legacy artifact, kept: saturation
   V2 also fills per-variant metadata — Cost, accelerator, Role — on behalf of all analyzers. Labeled
   as an artifact, not design.)*
2. **Normalize → utilization.** Compute `demand_target`, `achieved`, `remaining` per item as above.
   Combine **across analyzers within a variant** by taking the *most-demanding* one (max desired
   replicas ⇔ min achieved) — still in replica space, because analyzers share the replica scale.
3. **Aggregate → role and model utilization.** **OR (sum)** achieved across a role's variant
   alternatives; **AND (min, + delta)** across roles to get the model's utilization. Model
   `remaining = 1 − min_role(achieved)`.
4. **Resolve limits → available-supply envelope** (two-phase, issue #7). *Before each allocation
   loop*, the limiter hands the optimizer one per-model envelope = `min(physical, quota, maxReplicas)`
   per accelerator type. The optimizer is otherwise limit-blind. The envelope caps *how much*, never
   *whether* a model gets a turn (issue #7 invariant).
5. **Allocate (per model, rounds).** Each round: size candidate additions per role (cheapest variant
   first = OR walk; sized by the step-2 max), cap each by the envelope + maxReplicas. Compute the
   **joint ceiling** = `min_role(achieved + addable_this_round) + delta`. Commit each role up to the
   ceiling. A step that raises no role's `achieved` is not taken — *regardless of which limit stopped
   it*. Recompute `achieved` from `committed_so_far` (pure function) and repeat until no role can
   raise the model's `achieved`, or the envelope is exhausted.
6. **Stop / continue.** Stop *this* model when step 5 can't raise its `min_role(achieved)`; other
   models continue while their envelopes still permit an `achieved`-raising step.
7. **Emit decisions.** Per-variant target replica counts.

### Scale-down (where it diverges)

Scale-down is the **negative gap** (`supply > demand/scaleDownBoundary`) and is **per-role
independent** — *not* jointly coupled. Each role sheds spare replicas on its own; there is no joint
`min` ceiling, no cross-role trim. The dead-band between `scaleUpThreshold` and `scaleDownBoundary`
is where neither fires. (Out of scope for the current fix; documented so the reader knows the
coupling is a scale-up-only property.)

### What's still open before this is final

- Supply-taxonomy definitions confirmed (this section's premise).
- Issue #2 verified/fixed (anticipated in numerator).
- Issue #7/#8 envelope-per-loop and limiter shape verified.
- Fair-share (issue #6) is deliberately *outside* this flow — it decides each model's turn/budget
  upstream of step 4; its definition is deferred.

---

## Open issues / divergences from the current code

Flagged during the discussion; to be resolved and reflected in the implementation section.

1. **`pickerState` is redundant mutable state that conflates two meanings.** The code carries a
   mutable per-role "remaining demand" counter and *also* (post-fix) derives achieved from the
   planned allocation. The mutable counter is additionally pre-shrunk by the fair-share *budget*
   before the paired loop — so it silently means "remaining demand OR budget, whichever is
   smaller." The numerator bug was exactly this collision (achieved read off the budget-capped
   counter). Per the clean model (points 8–9), the only dynamic state should be the planned
   allocation; **remaining, achieved, the loop gate, and fair-share pressure should all be derived**,
   and the **fair-share budget should be an explicit input**, not smuggled into a demand counter.
   The entry-time snapshots (`trueRC`, `denom`, `supply`) exist *only* to re-derive fixed inputs
   that the mutable counter obscures — they disappear in the clean model.
   *Caveat for the fix:* the "budget" that must become an explicit input is not a single scalar —
   limits can be scoped per-namespace, per-cluster, and per-accelerator-type (and may compose,
   e.g. `min(physical, quota)`). The explicit budget input must carry that structure, not collapse
   it to one number (ties to issues #7/#8).

2. **Anticipated supply is in the denominator — suspected bug.** The code puts existing supply in
   the numerator and anticipated supply in the denominator (via `RC = demand/scaleUp −
   anticipated`). Per the clean model (point 8), **existing + anticipated should both count toward
   achieved** (numerator), with the denominator being the fixed demand target. The `RC ≤ 0 →
   achieved = 1.0` clamp is likely a patch for this mismatch and should become unnecessary in the
   clean formulation. **Needs a concrete trace** of the interior case (RC > 0 with significant
   anticipated supply) to confirm whether the current code is merely awkward or actually wrong.

3. **Naming.** `denom`, `denom_role`, `trueRC`, `roleBottleneckReplicas`, `pickerState` are opaque.
   Names should reflect the *item* they belong to (ns/model/role/variant) and the utilization
   framing (achieved / remaining / budget / demand-target), not internal mechanics.

4. **Integer-rounding overshoot.** A role can exceed 100% by up to one replica (the fractional
   round-up-to-1). Corner case to state explicitly: **a role over 100% must never force its
   sibling over 100%.** Confirm the joint (min) bound handles this.

5. **`min + delta` role margin — ADOPTED (additive, default 0).** Include the margin in the
   design. It relaxes role coupling by a small slack so a role need not be held *exactly* to the
   bottleneck: `jointCap = min_role(achieved) + delta`, applied **in utilization space**
   (additive). Default `delta = 0` reproduces today's strict-min behavior; the knob is exposed but
   off by default. **A non-zero margin is only correct additively** — there is no multiplicative
   form: the margin is a utilization slack, not a scaling of a capacity quantity, so `min × (1+δ)`
   is not used.

6. **Fair-share definition is not pinned — DEFERRED (own discussion).** Two questions, and the
   *first* is the deeper one:
   - **(a) What is "share" measured in?** Before priority even enters, we must decide what quantity
     fair-share equalizes across models: **achieved** utilization, **remaining** utilization
     (`1.0 − achieved`), or something else entirely (e.g. marginal utilization-per-GPU, or a
     demand-weighted quantity). The current code's `fairShareValue = priority × Σ(score ×
     remaining_demand_per_role)` is a priority-weighted *demand* proxy — neither cleanly "achieved"
     nor cleanly "remaining utilization." This choice defines what "fair" means and must be settled
     first.
   - **(b) What does `priority` do,** once (a) is fixed — weights the slice (A), sets service order
     (B), or scales the target (C):
     - **A** — priority weights the slice: high-priority models claim a proportionally larger share
       of the round's mean.
     - **B** — priority is service-order: models served in priority order, each claiming the same
       slice.
     - **C** — priority scales the target: a priority-2 model aims for 2× the utilization of a
       priority-1 model from the same pool.
   **Deferred to its own discussion; do not resolve inside Phase 3.** Phase 3 verifies the
   *within-model* coordination against the clean model and treats the fair-share budget as an
   opaque per-round input (point 9), leaving (a)/(b) for later.

7. **Two-phase separation: capacity envelope vs. allocation algorithm.** The clean design requires
   that limits (physical inventory + quota + any future admin cap) be resolved into a per-model
   capacity envelope **before** the allocation algorithm runs. The allocation algorithm then sees
   only "here is what is allocatable for this model" — it never needs to know whether that came from
   inventory, quota, or a composition of both. Today, `greedy_score_optimizer.go` embeds quota
   awareness directly: `effectiveAvailable(available, nsBudget)` is computed inside
   `allocateForModel`, with `nsBudget` drawn from a namespace-keyed quota map passed through the
   optimizer. The clean interface would be: the limiter layer owns all of namespace lookup, quota
   logic, and `min(physical, quota)` composition; it hands the optimizer a single flat capacity map
   per model. **Deferred** — the natural forcing function is sub-issue #1003
   (physical + quota composition). Scoping this to PR #1129 would require a significant interface
   redesign of files that have already gone through multiple fix rounds; the current code is
   functionally correct.
   *Refinements (2026-07-15):* (i) the envelope must be **recomputed/updated before *each*
   allocation loop**, not once per cycle — as one model's allocation consumes shared inventory,
   the next model's envelope changes. (ii) **Verify the limits carry no cross-allocation
   correlation that would distort the *share decision itself*.** It is fine for model A's
   allocation to shrink model B's remaining envelope (that's just inventory being consumed); it is
   **not** fine for a limit to make B's *fair-share ranking* depend on A's allocation. The envelope
   caps *how much* B may take, never *whether B deserves a turn*. This is the invariant that keeps
   the two-phase split valid.

8. **Limiter interface shape — keep in the doc, but verify the proposed shape.** Follows from
   issue #7. `ComputeConstraints` today returns a cluster-level `Pools` map plus a namespace-level
   `NamespacePools` map; the optimizer recombines them via `effectiveAvailable`. In the two-phase
   model, the interface should instead expose **per-model capacity** (a method like
   `CapacityForModel(model, ns) map[type]int`), so the optimizer is completely limit-blind.
   *Open verification (2026-07-15):* a clean per-**demand** (per-model) cap is only precomputable
   if every limit is expressible per-model. Some limits are on **totals across demands** (a shared
   pool/quota consumed by many models) — those cannot be fully resolved to a static per-model
   number up front, because the true cap on model B depends on what A has already taken this round.
   The likely reconciliation: the limiter exposes a per-model capacity that is **recomputed before
   each allocation** (issue #7 refinement (i)) rather than precomputed once — i.e. a
   `CapacityForModel` *query* against live remaining inventory, not a frozen map. The proposed
   shape should work under that reading, **but must be verified** against the cross-demand-total
   cases before we commit to it. The current `NamespaceAwareInventory` + `NamespacePools` path is a
   correct approximation. **Deferred** to the same milestone as issue #7.

9. **Per-config analyzer selection — NEW (2026-07-22, from the #1442 review).** Today analyzer
   selection (V1 vs V2) is decided from the *global* `default` entry while thresholds are merged
   per-model/namespace, so a resolved entry's own fields can disagree with the analyzer it runs on
   (the source of #1442's `ApplyV2ThresholdDefaults` + inverted-pair reset machinery). An
   alternative is to key selection on the **resolved config's `IsV2()`**: a V1-style per-model/
   namespace override then means "this model runs V1" (the more intuitive operator model),
   `ApplyDefaults` handles thresholds via its existing `IsV2()` branch, and both the post-merge V2
   defaulting and the inverted-pair reset become unnecessary. Trade-off: it is a semantic change —
   a V1-style override would opt a model back to V1, which some existing overrides may not intend.
   **Noted as a future direction, out of scope for #1442.**

---

## Implementation mapping & verification — Phase 3

First pass done 2026-07-15 (scale-up path, on `optimizer-pd-role-ceiling` @ `0c33a3eb`). Still
TODO: scale-down path, and the `available`/limiter path (depends on where #1129 actually landed —
see D4). Line refs are to `internal/engines/pipeline/analyzer_helpers.go` unless noted.

### Supply taxonomy → code mapping

| Clean term | Code | Notes |
|---|---|---|
| **current supply** | `RoleCapacity.TotalSupply` = `Σ ReplicaCount × PRC` (`aggregation.go:40`, `AggregateByRole:80`) | existing running only |
| **anticipated supply** | `RoleCapacity.TotalAnticipatedSupply` = `Σ (ReplicaCount + PendingReplicas) × PRC` (`aggregation.go:52`, `:81`) | **current + booting** (the full total, not just the increment) |
| **desired supply** | `TotalDemand / scaleUp` — materializes as `denomByRole` (`:314`) `= RC + TotalAnticipatedSupply`, which algebraically `= TotalDemand/scaleUp` when RC is unclamped | the demand target / denominator |
| **available supply** | limiter path (`available` map, quota) — **not resolved on this branch**; see D4 | budget only |
| **committed (dynamic)** | `targets[v] − stateMap[v].CurrentReplicas` × PRC (`:349-351`) | the one dynamic term ✓ matches clean model |

### Deviations found

**D1 — `achieved` drops booting/pending supply (confirms Open issue #2; the suspected bug is real).**
`achieved := (supplyByRole[role] + committed) / denom` (`:353`), and `supplyByRole[role] =
rc.TotalSupply` (`:313`) = **current only**. Per the clean model the numerator should be
**anticipated** (current + pending) = `rc.TotalAnticipatedSupply`. So pending/booting replicas are
omitted from `achieved`; it under-reports by `pending×PRC / demand_target`.
- **`denom` is fine** (= desired supply) in the common case; the bug is purely the numerator.
- The **`RC ≤ 0 → achieved = 1.0` clamp (`:354`) is a partial patch**: it only fires when pending
  *fully* covers demand (RC≤0). In the interior (RC>0 with booting replicas) `achieved` is
  understated and **unpatched**.
- **Effect:** in the AND(`min`) coordination, a role with booting replicas looks more lagging than
  it truly is → it can bind `jointCap` too low and throttle its sibling. (It does *not* cause the
  role to over-provision itself — RC-based sizing/gating already accounts for pending — so the
  damage is specifically to the cross-role `min`.)
- **Fix (one field):** numerator → `rc.TotalAnticipatedSupply`. Then `achieved ≥ 1` exactly when
  `RC ≤ 0`, so the clamp (`:354`) becomes **redundant** — which is itself the proof that the clamp
  was compensating for this drop.

**D2 — `denom` routes through the clamped RC, so it ≠ desired supply when RC≤0 (minor).**
`denomByRole = RC + TotalAnticipatedSupply` (`:314`). When RC is clamped to 0, `denom =
TotalAnticipatedSupply`, not `TotalDemand/scaleUp`. Harmless today (achieved ≥ 1 either way once D1
is fixed), but the clean rewrite should set `denom = TotalDemand/scaleUp` directly rather than
reconstructing it from the clamped RC.

**D3 — two representations of "remaining" (confirms Open issue #1).** `achieved` is derived from
`targets`/`stateMap` (correct, clean), but the loop gate, replica sizing (`roleBottleneckReplicas`),
and fair-share pressure still read `pickerState` — a mutable RC-seeded counter that
`GreedyByScoreOptimizer` also pre-shrinks by the fair-share budget. The entry snapshots (`trueRC`,
`denomByRole`, `supplyByRole`, `:307-315`) exist only to re-derive fixed inputs the mutable counter
obscures. Clean model: only `committed` is dynamic; gate/sizing/pressure all derive from it +
fixed inputs, and the fair-share budget is a separate explicit input.

**D4 — `available`/limiter not verifiable on this branch.** `effectiveAvailable` (referenced in
Open issues #7/#8) does **not** exist at `6e3ceb3e`; it is presumably part of #1129, which is not
on this branch. The `available` map is threaded into `pick()` (limited mode) but the quota/envelope
composition can't be checked here. **Verify against wherever #1129 actually merged** before
finalizing the "available supply" row and issues #7/#8.

### Known-and-accepted (not deviations)

- Naming (Open issue #3) — cosmetic; fold into the rewrite.
- Integer-rounding overshoot (Open issue #4) — behavior is correct; document the corner case.
- Legacy artifact: saturation V2 populates per-variant metadata (Cost, accelerator, Role) for all
  analyzers. Kept; labeled as artifact, not design.

### Still TODO in Phase 3

- Scale-down path (`scaleDownRoleIterated`) — verify per-role-independent behavior matches the
  clean model's negative-gap description; confirm no accidental joint coupling.
- `available`/limiter (D4) against the real #1129 code.
- Decide fix-now vs. follow-up for D1 (the one behavioral bug), D2 (cleanup), D3 (refactor).
