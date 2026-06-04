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
                                     ┌─────────────────────────────────────────┐
                                     │ Engine runs saturation V2 (always)      │
                                     │   → AnalyzerResult: VariantCapacities,  │
                                     │     RoleCapacities, Total*              │
                                     └────────────────┬────────────────────────┘
                                                      │
                                                      ▼
                                     ┌─────────────────────────────────────────┐
                                     │ For each registered non-saturation      │
                                     │ analyzer (registration order):          │
                                     │   • Build AnalyzerInput from common     │
                                     │     fields (replica metrics, variant    │
                                     │     states, scheduler queue, …)         │
                                     │   • Call Analyze(ctx, input)            │
                                     │   • Recover errors / panics per call    │
                                     └────────────────┬────────────────────────┘
                                                      │
                                                      ▼
                                     ┌─────────────────────────────────────────┐
                                     │ Engine post-step (universal threshold)  │
                                     │ For each analyzer, at every scope       │
                                     │ (model + each role):                    │
                                     │   RC = max(0, TD/scaleUp − Anticipated) │
                                     │   SC = max(0, TS  − TD/scaleDown)       │
                                     └────────────────┬────────────────────────┘
                                                      │
                                                      ▼
                                     ┌─────────────────────────────────────────┐
                                     │ Optimizer reads []NamedAnalyzerResult   │
                                     │   • Per-analyzer slice w/ working state │
                                     │   • Helpers: needsScaleUp, bottleneck-  │
                                     │     Replicas, applyAllocation, …        │
                                     │   • Picker: cost-greedy or fair-share   │
                                     │   • Disaggregated: paired scale-up +    │
                                     │     role-iterated scale-down            │
                                     └────────────────┬────────────────────────┘
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

A variant carries at most one role; the variant's underlying `scaleObject`
(deployment, etc.) is "painted" with that role. Roles partition variants cleanly.
Per current design assumption: **a model is either fully disaggregated (P+D both
present, no other variants) or non-disaggregated (no role-tagged variants)** —
not mixed.

**Demand coupling for P/D.** The same model demand `d` mapped to multiple roles
is *not* like the same demand mapped to multiple non-role variants. Roles are
linked: P(d) and D(d) both derive from the same underlying traffic; satisfying
one is partial progress on `d`, but `d` is fully served only when both are.
Each analyzer has its own α: sat_v2 (kv-tokens) typically has α ≪ 1; TA (RPS,
1:1 per request) has α = 1.

**Scale-up: paired allocation.** Allocate `(n_P, n_D)` together, sized so that
both sides serve the same `p_step` worth of demand: `n_P = ceil(p_step / PRC_P[vP])`,
`n_D = ceil(α × p_step / PRC_D[vD])`. Per-analyzer Remaining (in P-units)
decreases by `served_i = min(n_P × PRC_i[vP], n_D × PRC_i[vD] / α_i)`.

**Scale-down: role-iterated.** Scale-down does NOT pair. P and D are independent
at scale-down — analogous to how separate models are independent at scale-down.
Removing prefill replicas only affects P-side supply (D unchanged) and vice versa;
the underlying model demand `d` is unaffected. The optimizer iterates roles
independently, sheds within each role respecting that role's `SpareCapacity` and
`minReplicas` floor.

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

### F3. `ThresholdApplied` opt-out flag

For analyzers with non-universal calibration math (e.g., a future ITL-based
analyzer that computes RC/SC itself), an `AnalyzerResult.ThresholdApplied bool`
opt-out flag would let the engine post-step skip its calibration for that
analyzer. Captured in PR1113-review.md Appendix B; deferred from PR #1228 scope.

### F4. Per-analyzer observability metrics

Once `multi-analyzer-optimizer` merges and `[]NamedAnalyzerResult` flows to the
optimizers, expose each analyzer's per-VA demand/capacity as Prometheus gauges
labeled by `analyzer_name`. Suggested names:
`wva_analyzer_required_capacity{analyzer_name,...}`,
`wva_analyzer_spare_capacity{...}`, `wva_analyzer_utilization{...}`. Generalizes
the saturation-only PR #933 gauges. Coordinate with the freshness-gauge pattern
from PR #1190 (`wva_saturation_metrics_up`).

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

TA-PR5 drops the EPP-presence and GPS-mismatch gates that previously suppressed
`SpareCapacity` in TA's `Analyze()` (the new contract has no SC opt-out).
Engine post-step always computes SC, so EPP-absent or active-GPS-mismatch
states will emit SC where today they don't. Two restoration paths:
(a) `AnalyzerResult.SuppressSpareCapacity` opt-out on the analyzer→engine
contract; (b) implement the deferred `ThresholdApplied` flag (§ F3).
Tracked in TA-PR5-plan.md §7.

---

## References

- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md) — Item 3 / PR #1225
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) — Item 2 / PR #1228
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md) — Item 1 / not yet PR'd
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder agent rules
- [`PR1113-review.md`](PR1113-review.md) — historical review of original PR #1113 that decided the 3-PR split
- [`ENGINE-multi-analyzer-plan.md`](ENGINE-multi-analyzer-plan.md) — SUPERSEDED predecessor plan; full original combine spec preserved there
- TA-PR5-plan.md, TA-Plan.md — TA-side plans that consume this pipeline
