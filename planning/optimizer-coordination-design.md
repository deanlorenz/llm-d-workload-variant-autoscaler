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
- **Phase 2 — clean logical & data flow:** DRAFTED (§ Clean design). **Awaiting Dean's review** of
  two questions posed at the end of the session:
  1. Does the Stage 1–4 clean design read as he'd write it (it's meant to stand alone for a reader)?
  2. **Framing decision:** the draft states the *intended* formula — `achieved =
     (existing + anticipated) / demand_target` — which is the *corrected* numerator, NOT the code's
     current behavior (code puts anticipated in the denominator). So the clean design describes the
     target and § Open issues #2 flags the code as lagging. Confirm that separation (clean = target,
     implementation section = where code lags) vs. clean = only-what's-true-today.
- **Phase 3 — implementation mapping & verification:** NOT STARTED (§ Implementation mapping — TODO).

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

5. **`min + delta` role margin.** Not in design or code — a noted extension point only (to slightly
   relax role coupling if ever wanted). Documented here so it isn't mistaken for existing behavior.

6. **Fair-share definition is not pinned.** The current code's `fairShareValue = priority × Σ(score
   × remaining_demand_per_role)` is a priority-weighted demand proxy, **not** pure utilization. Per
   the clean model, the only metric for comparing models should be **utilization** (`1.0 − achieved`)
   and the only unit for comparing resources should be **replicas** (with GPU cost derived from
   replicas, not used as the primary allocation unit). The open sub-question is the role of
   `priority`:
   - **A** — priority weights the utilization slice: high-priority models claim a proportionally
     larger share of the round's mean.
   - **B** — priority is a service-order: models served in priority order, each claiming the same
     utilization slice.
   - **C** — priority scales the utilization target: a priority-2 model aims for 2× the utilization
     of a priority-1 model from the same GPU pool.
   One of A/B/C must be chosen and made explicit. **Needs further discussion before Phase 3.**

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

8. **Limiter interface shape.** Follows from issue #7. `ComputeConstraints` today returns a
   cluster-level `Pools` map plus a namespace-level `NamespacePools` map; the optimizer
   recombines them via `effectiveAvailable`. In the two-phase model, the interface should instead
   expose **per-model capacity** (or a method `CapacityForModel(model, ns) map[type]int`), so
   the optimizer is completely limit-blind. The current `NamespaceAwareInventory` + `NamespacePools`
   path is a correct approximation; the interface redesign is a follow-on to issue #7. **Deferred**
   to the same milestone as issue #7.

---

## Implementation mapping & verification — TODO (Phase 3)

To be filled after the clean design above is confirmed. Plan:

- Map each clean concept to its code symbol (`analyzer_helpers.go`, `greedy_score_optimizer.go`,
  `cost_aware_optimizer.go`, engine post-step).
- Verify the code's behavior matches each numbered point; record any deviation.
- Call out accepted legacy artifacts explicitly (e.g., saturation V2 populating per-variant
  metadata for all analyzers) — kept, but labeled as artifacts, not design.
- Resolve open issues 1–5 (decide: fix now vs. file as follow-up). Issues 6 (fair-share
  definition), 7 (two-phase separation), and 8 (limiter interface shape) are design questions
  that must be answered before Phase 3 can verify the code against the clean model — pin
  those first, then verify.
