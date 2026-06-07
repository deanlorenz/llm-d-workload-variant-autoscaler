# Multi-Analyzer Pipeline — Design

> **Status: ACTIVE** — Cross-cutting design doc for the multi-analyzer mission.
> Three implementation PRs in flight; per-PR detailed plans live alongside.
> See § Tasks below.

---

## Mission

Today's WVA engine has a hardcoded saturation-only path. Adding a second analyzer
requires name-dispatch in `runAnalyzersAndScore` (`if aw.Name == "throughput"…`).
The mission is to replace that with a **generic multi-analyzer pipeline** so any
number of analyzers (saturation, throughput, SLO, queueing-model, …) can plug in
without engine code changes:

1. Engine carries an analyzer **registry**; `cmd/main.go` registers the active set
   at startup.
2. Each cycle, the engine runs every registered analyzer and applies a **universal
   threshold post-step** that calibrates `RequiredCapacity` / `SpareCapacity` per
   analyzer.
3. The **optimizer** receives a per-analyzer slice (`[]NamedAnalyzerResult`) and
   makes scaling decisions over it via shared free functions, with optimizer-
   specific picker logic.

The pipeline must support P/D disaggregated models (per-role aggregation +
paired-allocation scale-up + role-iterated scale-down), keep the linearity
invariant the optimizer's per-variant scaling math depends on, and remain
extensible without engine package changes.

---

## Overview

### Data flow per optimize cycle

```
┌──────────────────────────────────────────────────────────┐
│ Config (SaturationScalingConfig per model/namespace)     │
│   Priority, Analyzers[]:                                 │
│     name, Score, ScaleUpThreshold, ScaleDownBoundary, …  │
└──────────────────────────┬───────────────────────────────┘
                           │ engine reads per cycle
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: per-model preparation                            │
│   • BuildVariantStates (incl. GPUsPerReplica per         │
│     variant; from ScaleTarget / VA labels)               │
│   • CollectSchedulerQueueMetrics (shared across          │
│     analyzers)                                           │
│   • resolveThresholds(name, cfg) per analyzer            │
│     (per-analyzer override over model-level globals)     │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: run analyzers and build per-analyzer slice       │
│ For saturation V2 (always), then each registered         │
│ non-saturation analyzer in registration order:           │
│   • Analyze(ctx, input)                                  │
│   • applyUniversalThreshold(result, scaleUp, scaleDown)  │
│     → RC/SC at model + each role scope                   │
│   • Append NamedAnalyzerResult{                          │
│       Name, Result,                                      │
│       Score     ← config.Analyzers[name].Score,          │
│       Remaining ← RC,  Spare ← SC,                       │
│     } to []NamedAnalyzerResult                           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: build ModelScalingRequest                        │
│   AnalyzerResults  ← per-analyzer slice                  │
│   VariantStates    ← prepared above                      │
│   Priority         ← config.Priority                     │
│   Disaggregated    ← any variant has a non-"both" Role   │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Optimizer reads ModelScalingRequest                      │
│   • Per-analyzer slice w/ working state                  │
│   • Helpers: needsScaleUp, bottleneckReplicas,           │
│     applyAllocation, …                                   │
│   • Picker: cost-greedy or fair-share                    │
│   • Disaggregated: paired scale-up +                     │
│     role-iterated scale-down                             │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
                       VariantDecisions
```

### Key concepts

| Concept | Definition |
|---|---|
| **Analyzer** | Implementation of `interfaces.Analyzer` (Name + Analyze). Examples: saturation V2 (kv-tokens), throughput (RPS / ITL-derived), queueing-model, future SLO. |
| **`VariantCapacity`** | Per-variant primitives: `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity` (analyzer-specific units), `Cost`, `AcceleratorName`, `Role`, `TotalDemand`, `TotalCapacity`, `Utilization`. |
| **`AnalyzerResult`** | Per-(model, analyzer) output: `VariantCapacities[]`, model-level `Total*`, `RoleCapacities[role]`, `RequiredCapacity` / `SpareCapacity` (engine-written by post-step). |
| **`RoleCapacity`** | Per-role aggregate within an `AnalyzerResult`: `TotalSupply`, `TotalDemand`, `TotalAnticipatedSupply`, `RequiredCapacity` / `SpareCapacity` (engine-written). For P/D disaggregated models. |
| **`NamedAnalyzerResult`** | Optimizer-side wrapper: `{Name, Result, Remaining, Spare, RoleSpare, Score}`. Working `Remaining`/`Spare`/`RoleSpare` mutated by helpers; `Result` never mutated. |
| **Linearity invariant** | Adding *n* replicas of variant *v* reduces analyzer *i*'s working `Remaining` by exactly *n × PRC_i[v]* — at the appropriate scope (model for non-disaggregated, role for disaggregated). |
| **α (alpha)** | Per-analyzer P:D demand ratio for disaggregated models, derived from `r.RoleCapacities[D].TotalDemand / r.RoleCapacities[P].TotalDemand`. Workload invariant; held constant during optimizer iteration. |

---

## Architecture

### Responsibility split — who writes / who reads each field

| Field | Written by | Read by |
|---|---|---|
| Per-variant `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity`, `Cost`, `Role`, `AcceleratorName` | Analyzer | Optimizer (per-variant scaling math + picker) |
| Per-variant `TotalCapacity`, `TotalDemand`, `Utilization` | Analyzer | sat_v2 internal aggregation; `Utilization` also passed through to `VariantDecision.Utilization` for metric emission |
| Model-level `r.TotalSupply`, `r.TotalAnticipatedSupply`, `r.TotalDemand` | Analyzer (via shared aggregation helpers) | Engine post-step |
| Per-role `r.RoleCapacities[role].TotalSupply` / `TotalAnticipatedSupply` / `TotalDemand` | Analyzer (via shared aggregation helpers) | Engine post-step |
| Model-level `r.RequiredCapacity`, `r.SpareCapacity` | **Engine post-step only** (overwrites anything analyzer wrote) | Optimizer |
| Per-role `RoleCapacity.RequiredCapacity`, `SpareCapacity` | **Engine post-step only** (overwrites anything analyzer wrote) | Optimizer |
| `NamedAnalyzerResult.Remaining`, `Spare`, `RoleSpare` | Optimizer's working state during allocation; initialized from engine-calibrated values | Optimizer's helpers |

### A. Per-variant data is canonical

`interfaces.VariantCapacity` is the single source of truth for per-variant primitives.
Analyzers populate it; the engine's universal threshold post-step and the optimizer's
helpers read it. Per-variant fields cover identity (`VariantName`, `AcceleratorName`,
`Cost`, `Role`), state (`ReplicaCount`, `PendingReplicas`), and analyzer-specific
quantities (`PerReplicaCapacity`, `TotalDemand`, `TotalCapacity`, `Utilization`).

**Aggregation responsibility: analyzer.** Each analyzer publishes per-scope
`Total*` (model + per-role) so the engine post-step can compute RC/SC at any
scope without re-deriving sums. Shared helpers in `internal/engines/aggregation/`
provide canonical sum-over-variants functions; analyzers that don't use them must
produce identical math, otherwise the optimizer's per-variant scaling math
silently breaks.

### B. Engine writes RC/SC; optimizer reads

The engine post-step (`applyUniversalThreshold` from PR #1228) is the **sole writer**
of `RequiredCapacity` / `SpareCapacity` at every scope. Analyzer-written values are
discarded. This decouples calibration (engine concern) from analyzer specialization
(per-analyzer concern: PRC + TotalDemand) and lets per-analyzer threshold overrides
flow through uniformly.

**Strict no-fallback.** The post-step is a pure formula:
```
RC = max(0, TotalDemand / scaleUp − TotalAnticipatedSupply)
SC = max(0, TotalSupply         − TotalDemand / scaleDown)
```
`TotalAnticipatedSupply == 0` is a literal value, not a sentinel — for a
scaled-to-zero variant with positive demand, RC = TotalDemand/scaleUp (the
correct "this much capacity needed" answer). The engine does not walk
`VariantCapacities` to derive anticipated supply; analyzers must populate it.

### C. Per-analyzer threshold overrides

`AnalyzerScoreConfig.ScaleUpThreshold` / `ScaleDownBoundary` are resolved per
analyzer (override over model-level global) and applied uniformly at every scope
for that analyzer. **No per-role overrides.** The same `(scaleUp, scaleDown)` pair
applies to model-level RC/SC and every `RoleCapacity` entry for that analyzer.

### D. Roles and disaggregation

A variant carries at most one role; the variant's underlying `scaleObject` is
"painted" with that role. Roles partition variants cleanly. Per current design
assumption: a model is either fully disaggregated (P+D both present, no other
variants) or non-disaggregated (no role-tagged variants) — not mixed.

**(model, role) is the unit of allocation math.** Each (model, role) carries
its own per-analyzer Demand (`r.RoleCapacities[role].TotalDemand`) and
Capacity (`r.RoleCapacities[role].TotalSupply`). Adding `n` replicas of a
variant `v` (where `v.Role = role`) reduces analyzer-i's (model, role) demand
by exactly `n × PRC_i[v]` — the same primitive as non-disaggregated
allocation, scoped to one role. The set of (model, role) pairs across all
models behaves like a set of independent "mini-models" for purposes of
per-role allocation math.

**Coupling lives only at request-level satisfaction.** The same user request
drives demand on every role of the model, so the model's served portion is
bounded by the role with the lowest util:

    util(model, role) = served^role / Demand^role
    util(model)       = min_role util(model, role)

The model is fully served when `util(model) = 1`. Allocation is committed
jointly: a candidate (n_P, n_D) is sized per-role independently, then the
larger-util role is trimmed so both roles advance by the same util delta —
the matched-pair commitment respects the bottleneck. Excess on the
over-allocated role is not committed; its capacity remains available for the
picker's next iteration, including for other models with demand on that role.

**Same calculus as cross-analyzer aggregation.** The optimizer already
aggregates along the analyzer axis using bottleneck operations:
`bottleneckReplicas(s, v) = max_i ceil(Remaining_i / PRC_i[v])` for scale-up
sizing, `safeRemovalReplicas(s, v) = min_i floor(Spare_i / PRC_i[v])` for
scale-down, plus slice predicates `any-up` (∃ analyzer needing scale-up) and
`all-down` (∀ analyzers have spare). The role axis is the same shape:
`min_role util(model, role)` is to roles what `min_i ... (across analyzers)`
is to analyzers. Working state can be viewed as an (analyzer × role) grid;
allocation math aggregates along each axis with the same bottleneck-style
operations — `max` along the analyzer axis at sizing time (need to satisfy
the most-demanding analyzer), `min` along the role axis at commit time
(joint-pair constraint). Both generalize to higher arities — more analyzers,
more roles, future joint-allocation legs — without introducing new operators.

**0-cases.** If `Demand_role = 0`, that role drops from the min (no
constraint, util = 1 by convention). If `Capacity_role = 0` and
`Demand_role > 0`, then `util_role = 0` and the joint bound is 0 until some
allocation lands in that role. Cold-start (both capacities zero, both demands
positive) reduces to the same continuous case — the min pulls allocation
toward whichever role is currently lagging.

**Picker layering.** The picker is two-level. (1) Per variant, compute the
fair-share / cost-greedy allocation against that variant's (model, role)
bucket — same competition rules as non-disaggregated. (model, P) variants
compete with other (?, P) variants on the P demand axis; (model, D) variants
compete on the D axis. Within a model, (model, P) and (model, D) never
compete — they're complementary, not substitutes. (2) For models with role
tuples, take the matched-pair min across the per-role allocations and trim
the over-allocated role to match — joint commit, atomic.

**α relocates from serve-math to picker-sizing.** α (per-analyzer P:D demand
ratio from `RoleCapacities`) is used by the picker to *size* a candidate
joint allocation when demand on one role is known. α does not appear in the
served-amount math — that math is per-(model, role) in each role's own
units, and the joint min folds the cross-role coupling at commit time
without appealing to α.

**Scale-down: role-iterated, unchanged.** Scale-down does NOT pair. P and D
are independent at scale-down — removing prefill replicas only affects
P-side supply (D unchanged) and vice versa. The optimizer iterates roles
independently, sheds within each role respecting that role's `SpareCapacity`
and `minReplicas` floor.

**Generalization.** Joint allocation across a role tuple is one instance of
"cross-variant dependency required to satisfy demand." See Future direction
F11 for the roadmap (>2 roles, mixed role/non-role within a model,
multi-model joint demand, multi-location replication). Today's
implementation handles 2-role P/D only; the architecture treats this as the
simplest case of a more general primitive.

**Implementation note: keeping signatures stable.** `NamedAnalyzerResult`
carries scalar `Remaining` (P-anchored in disag mode today) plus
`RoleSpare map[string]float64`. The (model, role) per-role demand
bookkeeping the math above requires can be tracked locally inside the
picker for the duration of one model's allocation pass — no new field on
`NamedAnalyzerResult`. The model-level `Remaining` continues to track joint
progress in P-units; per-role local tracking exists only inside the picker.
Promoting to a `RoleRemaining` field is a future option (see A10).

### E. SchedulerQueue handling

`AnalyzerInput.SchedulerQueue` represents requests queued upstream of any pod
(in the llm-d flow control layer). Queue items are model-scoped and **not
attributed to any variant or role**. Any analyzer with a demand model may use it;
sat_v2 does today (sums into prefill role's demand); the throughput analyzer will
when it lands.

**Demand extraction is per-analyzer.** Each analyzer converts queue depth/bytes
into demand in its own unit (sat_v2: kv-tokens; TA: tokens/sec). Each analyzer
also decides how to attribute that demand across roles or variants — sat_v2
splits across active roles.

### F. Aggregation helpers (canonical sums)

`internal/engines/aggregation/` (added by PR #1228) provides pure functions over
`[]VariantCapacity`:
- `SumTotalSupply(vcs)` = `Σ_v ReplicaCount × PRC`
- `SumTotalAnticipatedSupply(vcs)` = `Σ_v (ReplicaCount + PendingReplicas) × PRC`
- `SumTotalDemand(vcs)` = `Σ_v TotalDemand`
- `AggregateByRole(vcs)` returns role → `ScopeTotals{TotalSupply, TotalAnticipatedSupply, TotalDemand}`

Analyzers call these to populate `r.Total*` and `r.RoleCapacities[role].Total*`.
Using the helpers enforces the linearity invariant.

### G. Optimizer slice flow

`pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult` is the
per-model input the optimizer reads. Saturation is always the first entry
(keeper of variant identity until the future pre-analysis-extraction PR removes
that responsibility). Other enabled analyzers follow in registration order.
Helpers in `internal/engines/pipeline/analyzer_helpers.go` operate on the slice:
gates (`needsScaleUp` / `needsScaleDown`), sizing (`bottleneckReplicas` /
`safeRemovalReplicas`), and mutation (`applyAllocation` / `applyDeallocation`).
Pickers are optimizer-specific (`costGreedyPick` for CostAware,
`fairSharePick` for Greedy).

### H. Engine as configuration and parameter broker

The engine is responsible for populating all configuration and general
parameters that analyzers and optimizers consume. This includes:

- **Scores** — per-analyzer fair-share weights from
  `AnalyzerScoreConfig.Score`, written into `NamedAnalyzerResult.Score`
  for the optimizer's fair-share ordering.
- **Thresholds** — `ScaleUpThreshold` / `ScaleDownBoundary`, resolved
  per analyzer and applied via `applyUniversalThreshold` (engine
  post-step).
- **Disaggregation flag** — set on `ModelScalingRequest.Disaggregated`;
  today optimizers re-derive from `VariantCapacity.Role` (duplication,
  not yet rationalized).
- **GPU capacities** — `BuildVariantStates` populates `GPUsPerReplica`
  per variant; `computeCurrentGPUUsage` aggregates for the limiter.
- **Per-model priority** — `ModelScalingRequest.Priority` from
  `SaturationScalingConfig.Priority`.

**The engine bridges producer (config loader) and consumer (analyzer /
optimizer).** A regression where the producer publishes the value and
the consumer reads the field but the engine fails to plumb is silent —
config defaults stay correct, analyzer/optimizer code runs without
error, only behavior degrades. Tests that exercise producer + consumer
in isolation do not catch the engine-level gap; end-to-end assertions
that "what the engine populates matches what the config says" are the
only reliable backstop. The "Score field silently dropped during
cross-rebase" incident on `multi-analyzer-optimizer` is the load-bearing
example — see the optimizer review (B1).

**Sat_v2 collects some of this metadata today (legacy).** Per-variant
`Cost`, `AcceleratorName`, and `Role` flow through the saturation
analyzer's output as a transitional arrangement — this is why
saturation is always the first entry in the slice and is always run,
even when `enabled: false` for optimization purposes. Future direction
F1 (pre-analysis extraction) moves this metadata collection out of the
analyzer and into the engine proper, eliminating the saturation-first
ordering requirement.

---

## Tasks (the 3-PR split)

The mission is split into three PRs that can land in any order. The first two
(registration, threshold) are stacked at the branch level for development
convenience; the optimizer cross-rebases at the end.

| Task | Branch / PR | Status | Detailed plan |
|---|---|---|---|
| **Item 3 — Race-safe analyzer registry** | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) | **OPEN, in review** (ev-shindin assigned) | [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md) |
| **Item 2 — Universal threshold post-step + aggregation helpers** | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) | **OPEN, in review** (ev-shindin assigned). Stacked on #1225. | [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) |
| **Item 1 — Delete combine; per-analyzer slice → optimizers** | `multi-analyzer-optimizer` / not yet open | In progress (1.1+1.2+1.3 landed; 1.4 paused on plan rewrite) | [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) |

The three PRs together replace the engine-side combine + name-dispatch in
`runAnalyzersAndScore` with the architecture above.

---

## Alternatives considered

### A1. Combine in engine — dimensionless normalization

**Original design (Item 1, ENGINE-multi-analyzer-plan.md):** engine combines
multiple analyzer results into a single `*AnalyzerResult` via
`combineAnalyzerResults` using dimensionless normalization:

```
sat_total      = Σ_v VariantCapacities_sat_v.TotalCapacity
util_excess_i  = RC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)   # if > 0 → analyzer wants more
util_slack_i   = SC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)   # if > 0 → analyzer says spare

cold_start_i   = (TotalCapacity_i == 0 AND RC_i > 0)

scale_up   = any_i(util_excess_i > 0 OR cold_start_i)
scale_down = all_i(util_slack_i > 0)

combined.RC = max_i(util_excess_i) × sat_total   # any-up; back to saturation units
combined.SC = min_i(util_slack_i)  × sat_total   # all-down; 0 if any analyzer disagrees
```

**Why rejected:** the optimizer fundamentally needs per-analyzer data anyway
(per-variant `PerReplicaCapacity` per analyzer for the bottleneck math).
Combining into a single scalar throws away that per-analyzer dimension and
forces the optimizer to receive less information. Also the dimensionless
normalization, while unit-safe, introduces an indirection that wasn't paying off.

**Replacement:** delete combine; pass `[]NamedAnalyzerResult` to optimizers.
Helpers (`needsScaleUp`, `needsScaleDown`, `bottleneckReplicas` etc.) implement
the same any-up / all-down / cold-start semantics directly on the slice.

Full original spec preserved in `ENGINE-multi-analyzer-plan.md` (SUPERSEDED).

### A2. Constructor injection vs `RegisterAnalyzer`

**Considered:** add `analyzers []NamedAnalyzer` parameter to `NewEngine`; populate
at construction time before any goroutine exists; remove `RegisterAnalyzer` entirely.

**Why rejected:** forces a `main.go` refactor for marginal benefit over the
snapshot pattern, and removes the registration step that's a natural extension
point for cmd-side wiring. Keeping `RegisterAnalyzer` with a snapshot-on-Start
race-fix retains flexibility while still enforcing the "before Start" contract.

### A3. `RegisterAnalyzer` panic vs error-return

**Evolution:** initial implementation panicked on misuse (duplicate name,
post-Start call). Reviewer (ev-shindin) preferred `Must`-prefix per Go convention
(`prometheus.MustRegister` / `regexp.MustCompile`). Implemented as
`MustRegisterAnalyzer`; then revised again to **error-return semantics** (no panic)
matching the broader repo convention for setup-time misuse — callers that ignore
the error get a clear message at registration time and the engine doesn't bring
itself down.

Final API: `RegisterAnalyzer(name, a) error`. See registration-plan § "API
evolution summary" for the commit-by-commit history.

### A4. Compound-variant for P/D

**Considered:** treat (vP, vD) as a single compound variant CV with derived `Cost`,
`PRC`, `MaxReplicas`. Existing single-variant helpers work unchanged.

**Why rejected:**
1. **Fractional decode replicas.** 1 unit CV = 1 prefill + α decode. For α=0.3,
   allocating 5 CV units means 5 prefill + `ceil(5×0.3)=2` decode. Capacity
   served is `5 × min(PRC_P, PRC_D/α)` but cost paid is
   `5 × Cost_P + 2 × Cost_D` — rounding overhead distorts cost-greedy ordering.
2. **Compounds share underlying variants.** If vP has 5-replica max and
   CV1=(vP,vD1), CV2=(vP,vD2), allocating to CV1 reduces vP's pool for CV2.
   `CV.MaxReplicas` can't be a static field; it shrinks dynamically as
   allocations happen.
3. **Per-analyzer PRC and α stay per-physical-variant.** The compound layer
   doesn't collapse this dimension; just hides it.
4. **Multiple-pair coexistence.** With 2 P-variants × 2 D-variants you have 4
   candidate CVs. Standard cost-sort over CVs gives wrong answers when
   allocations interfere.

**Replacement:** explicit paired allocation with helper API
(`bottleneckReplicasPaired`, `applyAllocationPaired`, `PickPairFn`). Per-analyzer
α derived from role demands. Plus role-iterated scale-down.

### A5. Engine derives `Total*` from `VariantCapacities` (fallback walk)

**Original (PR #1228 first iteration):** engine post-step had a fallback walk —
if `r.TotalAnticipatedSupply == 0`, walk `VariantCapacities` and sum
`(replicas + pending) × PRC`. Asymmetric: model-level had 3-step fallback
(TotalAnticipatedSupply → walk → TotalSupply); per-role had 2-step (no walk).

**Why rejected:** two sources of truth for the same value — the analyzer
publishes `Total*`, but the engine could compute its own version from
`VariantCapacities`. Inconsistent fallback paths invite future bugs. And it
doesn't help: the optimizer needs per-variant data anyway, so an analyzer
"hiding" Total* doesn't simplify anything downstream.

**Replacement:** strict no-fallback engine post-step. Analyzer is the sole
publisher of `Total*` (model + per-role); analyzers use shared aggregation
helpers to enforce the linearity invariant. Engine reads `Total*` as-is,
including literal `0` values.

### A6. α from `RC` vs `TotalDemand`

**Considered:** derive α from per-role `RequiredCapacity` (`r.RoleCapacities[D].RC /
r.RoleCapacities[P].RC`).

**Why rejected:** RC is the *gap* relative to current supply. `P_RC=200, D_RC=0`
doesn't mean α=0; it means the allocation is currently asymmetric. Using RC for
α would tie α to allocation state, which is wrong.

**Replacement:** α derived from `TotalDemand` ratio per analyzer — the workload's
actual P:D split, an invariant of the traffic shape.

### A7. Per-role threshold overrides

**Considered:** `AnalyzerScoreConfig` could carry per-role overrides
(`{prefill: {scaleUp: 0.85}, decode: {scaleUp: 0.90}}`).

**Why deferred:** no use case yet. The same `(scaleUp, scaleDown)` pair applies
uniformly at model scope and every role for a given analyzer. Per-analyzer
override (one pair) is supported; per-role-per-analyzer is a follow-up if
needed.

### A8. `enabled: false` analyzer veto on scale-down

**Surfaced during TA-PR5 plan rewrite.** The slice predicate
`needsScaleDown(s) = ∀ e ∈ s : e.Spare > 0` (`pipeline/analyzer_helpers.go`) treats
a disabled analyzer (`Spare=0`) as a veto. This breaks TA-only scale-down with
saturation `enabled:false`: saturation's `Spare=0` blocks all-down even when TA
wants to scale down.

**Resolution:** predicate should treat disabled analyzers as "no opinion" rather
than "vetoes". Fix on the optimizer branch (multi-analyzer-optimizer-plan.md
follow-up). Tracked in TA-PR5-plan.md §7.

### A9. Engine package rename (`internal/engines/saturation/` → `internal/engines/`)

**Considered:** the engine package is named `saturation` for historical reasons,
even though the engine handles all analyzers. Rename for clarity.

**Why deferred:** mechanical-but-disruptive (every import changes). Not in scope
for any of the three multi-analyzer PRs. Tracked as a future cleanup.

### A10. Per-role `RoleRemaining` field on `NamedAnalyzerResult`

**Considered:** add `RoleRemaining map[string]float64` symmetric to
`RoleSpare`, so per-(model, role) demand bookkeeping is first-class on the
slice entry rather than ephemeral picker state.

**Rejected for now.** The per-role demand math from § D can be performed
with picker-local state for the duration of one model's allocation pass
without changing the slice contract. Keeping `NamedAnalyzerResult` stable
avoids a wider downstream impact (engine populates it, optimizer consumes
it, helpers walk it). Future PR can promote to a field if it becomes
load-bearing for observability metrics, helper reuse, or multi-arity
joint-allocation generalization (F11). The trade-off is local complexity
inside the paired picker vs. structural complexity on the contract.

---

## Future direction

### F1. Pre-analysis extraction

Today saturation V2 carries variant identity (Cost, AcceleratorName, Role,
replica counts) that any analyzer or the optimizer may need. The future PR
extracts this into a common pre-analysis stack so saturation V2 becomes one of
N peers — no longer special, no longer "always first." The optimizer's
`saturationEntry()` helper becomes obsolete.

### F2. Vector α / analyzer-published `D(p)`

Today the optimizer derives a scalar α per analyzer. Future direction: the
analyzer publishes `α` directly on `RoleCapacities`, or even `D(p)` as a
function. Supports vector demands (multi-dimensional analyzer outputs) and
non-linear couplings (where `D` is not strictly proportional to `P`).

### F3. Per-analyzer status return state (analyzer→engine contract)

Today's `AnalyzerResult` is a pure data record — analyzers publish raw
`Total*` and the engine post-step writes RC/SC unconditionally.
Analyzers have no way to signal "my output is degraded — engine should
adjust." A small return-state field lets each analyzer communicate
that, applicable to **any** analyzer (sat_v2, TA, QM, future):

    type AnalyzerStatus int
    const (
        AnalyzerOK AnalyzerStatus = iota
        AnalyzerSuppressSpareCapacity   // supply estimate unreliable; don't claim spare
        AnalyzerSuppressRequiredCapacity // demand estimate unreliable; don't claim need
        AnalyzerSuppressBoth            // both unreliable; engine holds all scaling decisions
        AnalyzerFail                    // analyzer cannot produce a result for this cycle
    )

The engine post-step honors the status: skip SC write when
`SuppressSpareCapacity` (or `SuppressBoth`); skip RC write when
`SuppressRequiredCapacity` (or `SuppressBoth`); skip the analyzer's
result entry from the slice entirely on `Fail`. `Total*` fields stay
raw under all states so observability is preserved.

Subsumes the narrower `ThresholdApplied` flag captured in
PR1113-review.md Appendix B (deferred from PR #1228 scope).

#### TA's failure modes (the load-bearing example)

TA's pre-PR-5 gate dropped SC when `!anyEPP || anyGPSMismatch`. The
two underlying conditions are different, and only one of them
genuinely needs gating:

- **Per-replica EPP arrival rate missing** — `ReplicaMetrics.ArrivalRate
  == 0` for all replicas. **Has a fallback**: TA falls back to vLLM
  `RequestsRate × AvgOutputTokens`. The fallback is acceptable; SC
  needs no suppression for this case alone. The pre-PR-5 `anyEPP`
  proxy was over-conservative — it suppressed SC in the legitimately
  quiet case.

- **EPP scheduler queue signal missing** — `AnalyzerInput.SchedulerQueue
  == nil`. **No fallback**: queue depth is orchestration-layer state
  vLLM can't see. Queued-but-not-yet-on-pod demand contributes 0 to
  `TotalDemand` → engine's `SC = TS − TD/scaleDown` is over-estimated
  → unsafe scale-down. This is the case that genuinely needs SC
  suppression (`AnalyzerSuppressSpareCapacity`).

- **GPS mismatch** — measured `GenerationTokenRate` deviates from the
  ITL model's predicted `μ_dec` by > 15% at `k* ≥ 0.30`. Already
  triggers observation-window-clear (TA recovers via re-fit); SC
  suppression during the mismatch window is additional safety since
  the supply estimate is wrong until the new fit lands. Maps to
  `AnalyzerSuppressSpareCapacity` for the affected window.

Refined gate: `Suppress = (input.SchedulerQueue == nil) ||
anyGPSMismatch`. Strictly more accurate than the old `anyEPP` proxy
(see TA-PR5-review for the full truth table).

#### Engine-side signal hygiene

`AnalyzerInput.SchedulerQueue` should distinguish three legitimate
states so analyzers can act correctly:

- **Flow control disabled** (operator config) — analyzers don't
  suppress; queue contribution to demand is correctly zero.
- **Queue present, empty** — analyzers don't suppress; queue
  contribution is zero because there's nothing waiting.
- **Queue signal genuinely missing** (collection failed) — analyzers
  suppress (or return `AnalyzerFail`).

Today the engine collector returns nil in all three states, so
analyzers can't distinguish them from inputs. Operators detect the
"genuinely missing" state externally via EPP's own queue-depth
metric, which is exported to Prometheus by the EPP layer (the metric
goes absent/stale when EPP is broken). That out-of-band observability
is sufficient for *detection* but not for *correct gating* — the
analyzer still over-claims spare during a missing-signal incident.

The fix lives on the analyzer-input side: `*SchedulerQueueMetrics`
either gains a `Disabled bool` / `Missing bool` discriminator, or
becomes a sum type with explicit cases. The engine's
`CollectSchedulerQueueMetrics` is updated to populate the
discriminators correctly. Then analyzers can gate.

#### Scope

This is one PR's worth of work: contract field on `AnalyzerResult`
(plus per-role `RoleCapacity` if per-role suppression is wanted),
engine post-step honoring the status, engine collector signal
hygiene for SchedulerQueueMetrics, and analyzer-side adoption
(TA first, others as needed). Replaces the narrower F9 entry below.

### F4. Per-analyzer observability metrics

Once `multi-analyzer-optimizer` merges and `[]NamedAnalyzerResult` flows to the
optimizers, expose each analyzer's per-VA demand/capacity as Prometheus gauges
labeled by `analyzer_name`. Suggested names:
`wva_analyzer_required_capacity{analyzer_name,...}`,
`wva_analyzer_spare_capacity{...}`, `wva_analyzer_utilization{...}`. Generalizes
the saturation-only PR #933 gauges. Coordinate with the freshness-gauge pattern
from PR #1190 (`wva_saturation_metrics_up`).

Adjacent: today's `enrichDecisionsWithKvTokenData` (engine.go) attaches
KV-cache token usage to `VariantDecision` post-optimizer — a sat_v2-specific
observability hook that runs only on the V2 path (not on QM, not on V1). Each
analyzer surfaces different relevant computed metrics (KV tokens for sat_v2;
ITL coefficients for TA; queue depth / arrival rate for QM). The
generalization of F4 is to move per-analyzer "decision enrichment" into a
per-analyzer hook (or onto `NamedAnalyzerResult` itself) so any analyzer can
publish its own observability fields without engine-side special casing.

### F5. Engine model-level RC/SC for disaggregated models — known bug

The engine post-step (`applyUniversalThreshold`) computes additive model-level
`RequiredCapacity` / `SpareCapacity` over all roles for disaggregated models.
The additive value conflates roles that aren't fungible (the bug Evgeny's
PR #1237 works around in the optimizer; our optimizer also bypasses model-level
for disaggregated). Once the optimizer PR ships, no consumer reads model-level
RC/SC for disaggregated; the buggy computation becomes latent.

**Follow-up:** remove or redefine — zero out, or `min(role)` semantics, or drop
model-level meaning when `RoleCapacities` is non-empty. Amends `applyUniversalThreshold`
from PR #1228.

### F6. Saturation V2 in-analyzer formula simplification

Saturation V2's Phase 4 RC/SC computation is redundant with the engine post-step
(both produce the same values for the same inputs). Already removed by
PR #1228's commit 3 (`a8147e8c`); listed here for completeness.

### F7. `enabled: false` analyzer veto fix

See § Alternatives → A8. Surface follow-up on the optimizer branch.

### F8. Replica-count accounting consistency

TA uses `len(variantMetrics)` for `VariantCapacity.ReplicaCount`; sat_v2 uses
`readyCount` from `VariantStates`. Both intentionally exclude pending replicas,
but the sources differ. Reconcile to a single canonical source — likely
`VariantStates`-derived, owned by the engine and passed through. Broader than
TA; engine-side fix. Tracked in TA-PR5-plan.md §7.

### F9. Restore TA's EPP/GPS-mismatch SC gate

Folded into F3 above. PR-5 dropped the gate; restoration happens as
part of the broader per-analyzer status-return state. See F3 for the
distinctions between EPP arrival-rate (fallback), EPP queue (no
fallback), and GPS-mismatch failure modes, and for the engine-side
signal hygiene needed on `SchedulerQueueMetrics`.

### F10. Fold queueing-model into the V2 multi-analyzer engine

Item 1 (`multi-analyzer-optimizer`) made V2 the multi-analyzer path
(slice contract, threshold post-step, registered-analyzer loop, paired/
role-iterated allocation). Queueing-model (`engine_queueing_model.go`)
remained a parallel sibling that:

- builds a single-entry `[]NamedAnalyzerResult` by hand at
  `optimizeQueueingModel`, naming it `SaturationAnalyzerName` so
  optimizer's `saturationEntry()` lookup matches;
- bypasses `runAnalyzersAndScore` entirely;
- runs no other registered analyzer (TA can't post-process QM output).

The optimizer PR did NOT consolidate the two engines; that was deliberate
out-of-scope deferral (the Item 1 scope is the optimizer-side slice
contract, not engine consolidation). Today QM works as before, modulo the
mechanical slice-shape adapter in `engine_queueing_model.go`. The
follow-up is to fold QM into V2 so there is one upstream slice-builder.

**Two paths:**

- **Option A — register QM as the saturation-slot analyzer** (recommended).
  When `wva-queueing-model-config` ConfigMap is present, register QM under
  `SaturationAnalyzerName` (replacing sat_v2 in that slot for the model)
  and route through `optimizeV2`. QM gets the threshold post-step,
  SchedulerQueue threading, disaggregation dispatch, and GPU limiter
  constraints "for free." Registered TA can post-process QM output. Needs
  a way to swap the saturation-slot analyzer at runtime; current registry
  assumes a single saturation analyzer.

- **Option B — give QM a distinct analyzer name and run alongside.**
  `e.queueingModelAnalyzer` becomes a regular registered analyzer with its
  own `Name()`. Selection between sat_v2 and QM happens via config
  enabling/disabling. Lower coupling but two analyzers running per cycle
  is wasted work when QM is the active mode.

**Pre-existing oversights to fix at merge** (all predate Item 1, none
introduced here):

- **Threshold post-step skipped on QM path.** Today QM's analyzer writes
  RC/SC directly (`RC = max(0, TD−TS)`); the universal post-step never
  runs. Under the merged engine, QM should either: (a) participate in the
  post-step like every other analyzer (and have its in-analyzer formula
  reframed to populate `Total*` fields only, letting the engine derive
  RC/SC), or (b) explicitly opt out via `ThresholdApplied` (§ F3). Option
  A is cleaner — fits the per-variant canonical contract.
- **`SchedulerQueue` field not threaded** into QM's `AnalyzerInput`. QM
  doesn't currently use it (demand comes from per-replica `ArrivalRate`),
  but in the merged engine the field flows uniformly; QM would have it
  available if/when it wants. (Note: `prepareModelData` already collects
  `SchedulerQueue` for all paths today — wasted work on the QM path. Folding
  in addresses both ends of the asymmetry.)
- **Disaggregation dispatch.** QM's `VariantCapacity` entries never set
  `Role`, so `isDisaggregated()` returns false for QM-scaled models.
  Implication: a P/D model under QM is treated as single-role. Folding
  into V2 requires QM to set `Role` on its `VariantCapacity` (or accept
  the same engine-side role-derivation sat_v2 uses).
- **GPU limiter not enforced.** When `enableLimiter=true`, both V2 and QM
  pick `GreedyByScoreOptimizer`, but only V2 computes and passes
  `constraints` to `Optimize`. QM calls `Optimize(ctx, requests, nil)` —
  Greedy is selected but limiter is not enforced. Folding QM into V2 fixes
  this automatically (one call site, one constraint computation).

**KV-token enrichment** (`enrichDecisionsWithKvTokenData`) is sat_v2-
specific observability that runs only on V2; QM-scaled VAs expose zero/
empty KV fields in their status. This is a per-analyzer observability gap
rather than a QM-merge concern — see § F4 above for the broader
generalization (per-analyzer decision-enrichment hook).

**Constraint:** V1 stays as-is (legacy single-analyzer path) until the
deprecation lands. F10 is V2 ↔ QM consolidation only.

**Recommendation:** open the QM-merge issue **after** the optimizer PR
merges (so it can reference the merged code). Title shape: *"Fold
queueing-model into the V2 multi-analyzer engine (Option A: register QM
as saturation-slot analyzer)"*. Body lists the four oversights above as
sub-items.

### F11. Joint-allocation generalization beyond P/D roles

Today's paired-allocation primitive handles 2-role P/D models. The
underlying abstraction — joint allocation across a tuple of variants
required to satisfy demand jointly — generalizes to:

- **More than 2 roles.** `min` over k role-utils; otherwise unchanged.
- **Mixed role and non-role variants in the same model.** Untagged
  variants behave as a single-role tuple; min over arity 1 is the
  identity. Removes today's "fully disaggregated XOR non-disaggregated"
  model assumption.
- **Multi-model joint demand.** Two distinct models serving the same
  user requests — allocating one without the other doesn't progress
  the joint demand. Same min-of-utils framework, with the tuple
  spanning models rather than roles.
- **Multi-location replication.** Two variants of identical config in
  different physical locations, both required for geo-redundant demand.

In all cases the picker sizes per-tuple-leg independently and commits the
matched-pair amount bounded by `min_leg util_leg`. The engine declares
the tuple shape per model — today implicit via `Role` + α-derivation;
generalization makes it explicit. Per-leg coupling ratios (today's α as
P:D) become per-leg-pair.

Implementation-side: `RoleSpare map[string]float64` (and a future
`RoleRemaining`, see A10) extend to arbitrary leg keys; the joint commit
math generalizes by replacing `min(util_P, util_D)` with `min over legs`.

### F12. Per-role RC/SC canonical end-to-end (drop the optimizer synthesis)

The optimizer-PR Phase 3 unification (see
[`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md)
§ Phase 3) treats `(model, role)` as the single allocation unit, with
non-disaggregated models flowing through a synthetic `"both"` role. Today
that synthesis is **option (b)** — the optimizer aliases the analyzer's
model-level RC/SC as the `"both"` role when `RoleCapacities == nil`,
because the engine only populates `RoleCapacities` for disaggregated
models.

**Option (a), the canonical future form:** the engine (or analyzer) always
populates `RoleCapacities`, including a `"both"` entry for non-disaggregated
models. Then:

- Per-role RC/SC is the single source of truth at every scope; the
  optimizer reads `RoleCapacities` uniformly and the synthesis branch
  disappears.
- The model-level `AnalyzerResult.RequiredCapacity` / `SpareCapacity`
  scalars can be **dropped** (or redefined) — they are currently the
  real value for non-disaggregated models and the meaningless
  additive-over-non-fungible-roles value for disaggregated models (F5).
  Making per-role canonical resolves F5 and the scalar's dual meaning in
  one move.
- `NamedAnalyzerResult.Remaining` / `Spare` scalars (kept read-only in
  Phase 3) also drop, since all working state is role-keyed.

Deferred because it ripples into #1228's analyzer→engine contract and the
TA analyzer (TA would need to emit a `"both"` `RoleCapacity`). Option (b)
keeps the change contained to the optimizer while the upstream PRs are
open. Open this after the optimizer PR merges, coordinated with the F5
cleanup.

### F13. Cost picker — integer-rounding suboptimality

`CostAwareOptimizer` ranks variants by `cost / PerReplicaCapacity` and
allocates `ceil(RC / PRC)` of the most-efficient variant. Under integer
rounding this is not always the cheapest *actual* allocation: when
`RC < PRC`, a high-PRC variant overshoots and can cost more than a cheaper
low-PRC variant that still covers RC. Example: A(cost 10, PRC 10,
efficiency 1.0), B(cost 4, PRC 3, efficiency 1.33), RC=3 → efficiency-greedy
picks A (cost 10) but B alone covers RC at cost 4. The cheapest actual
allocation ranks by `ceil(RC/PRC) × cost`, not `cost/PRC`.

Pre-existing behaviour inherited from the legacy cost optimizer; unchanged
by the multi-analyzer slice migration or the Phase 3 unification. Low
practical impact (production PRC ≫ RC residuals), surfaces at the tail.
Tracked in CURRENT § Issues to Open.

**Solution shape.** With N analyzers this is a multi-dimensional bounded
covering knapsack (NP-hard in general): each analyzer is a dimension, a
variant's replica provides a vector of per-analyzer capacities, and the goal
is to minimise cost subject to covering RC in every dimension. In practice the
instance is tiny (few variants, 1–3 analyzers), so **brute force** over
allocation combinations is tractable and gives the exact optimum.

Pragmatic compromise short of brute force: keep cheapest-efficiency for the
bulk allocation; when the **last** replica of the chosen variant lands below a
utilisation threshold X, recompute the **tail** decision by direct cost — for
the residual RC, rank candidates by `ceil(residual/PRC) × cost` and pick the
cheapest actual cost rather than the cheapest efficiency. Leaves the common
RC ≫ PRC path unchanged; fixes the A/B/RC=3 tail above.

---

## References

- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md) — Item 3 / PR #1225
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) — Item 2 / PR #1228
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) — Item 1 / not yet PR'd
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder agent rules
- [`PR1113-review.md`](PR1113-review.md) — historical review of original PR #1113 that decided the 3-PR split
- [`ENGINE-multi-analyzer-plan.md`](ENGINE-multi-analyzer-plan.md) — SUPERSEDED predecessor plan; full original combine spec preserved there
- TA-PR5-plan.md, TA-Plan.md — TA-side plans that consume this pipeline
