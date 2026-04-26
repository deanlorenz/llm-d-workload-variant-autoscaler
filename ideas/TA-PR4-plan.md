# PR-4: Throughput Analyzer ITL Model and Scaling Signal

> **Status: COMPLETE** — Implemented on branch TA3. Targets upstream `main` after
> PR-3 (#1052) merges. This document is the design rationale and reviewer context.

## Context

PR-3 (#1052, branch TA2) built the stateful substrate: per-variant
`ShapeTracker`, `ObservationWindow`, `SanityReport`, and a no-signal `Analyze()`
stub. PR-4 extends this with the full ITL model calibration pipeline, supply and
demand computation, and the model-level scaling signal.

**Scope of PR-4:**

- Two-tier ITL model resolution (OLS + constrained OLS fallback)
- Per-replica supply estimation: `μ_dec_sat = k_sat × KV_max / (KVreq × ITL(k_sat))`
- Demand estimation with three-priority fallback chain
- Scheduler queue demand contribution
- Anticipated supply (pending replicas) to suppress scale-up thrashing
- Role-aware aggregation: per-role RoleCapacities, RC suppressed for "prefill" role
- Model-level RC/SC from totals (not per-variant accumulation)
- ctx.Err() guards in Observe() and Analyze()

**Not in this PR (later PRs):**

- Tier-3 knowledge store (zero-replica fallback): type `itlKnowledgeStore` is
  kept in the package but not wired — see step-2 note in `analyzer.go`.
- Prefill-rate supply and demand: prefill pods go through the decode-rate
  framework in this PR; prefill-specific rate signals are deferred.
- k_sat constant unification: `DefaultKSat = 0.85` is per-analyzer for now;
  needs alignment with the EPP system-wide k_sat.
- Wiring into the engine's analyzer pipeline.

---

## New files

| File | Purpose |
|------|---------|
| `itl_model.go` | `ITLModel{A,B}`, `FitITLModel(obs)` (OLS), `ITLAt(k)`, `IsZero()` |
| `itl_model_test.go` | OLS fit (happy path, degenerate inputs, prediction accuracy) |
| `itl_knowledge_store.go` | `itlKnowledgeStore` — tier-3 skeleton, not wired |
| `itl_knowledge_store_test.go` | Store/load/overwrite/isolation tests |

## Modified files

| File | Key changes |
|------|-------------|
| `constants.go` | `DefaultKSat=0.85`, `DefaultBaselineITLSec=0.006`, `DefaultQueueDrainFactor=2.0` |
| `types.go` | `ThroughputVariantState` + `ITLModel`, `PerReplicaSupply`, `TotalSupply`, `Demand`, `Role` |
| `analyzer.go` | Full `Analyze()`, helpers, `VariantState()` with new fields; VLLMRequestRate-weighted `averageShapeMetrics` |
| `analyzer_test.go` | Signal tests: tier-1/2, scale-up/down, no-EPP, pending replicas, roles, k* demand, queue demand, model-level aggregation |

---

## ITL model resolution (two tiers)

### Tier 1 — OLS fit (window Ready)

When `ObservationWindow.Ready()` is true (≥10 samples spanning ≥30% KV%),
`FitITLModel(obs)` fits ITL(k) = A·k + B by OLS. The fit is accepted only when
A > 0 (physically required: more concurrent requests → higher latency).

On success, the fitted model is used for both supply and demand estimation this
cycle.

### Tier 2 — Constrained OLS (window not ready)

When the window is not ready, A is estimated with B pinned to `DefaultBaselineITLSec`
(0.006 s — H100 hardware baseline at near-zero load):

```
A = Σ((ITL_i − B) · k_i) / Σ(k_i²)
```

This is least-squares with B fixed, applied to all replicas with k* > 0. For a
single replica it reduces to the single-point formula `A = (ITL − B) / k*` from
TA-supply.md §2.3 Fallback. For multiple replicas it is strictly better —
same criterion as tier-1 but with fewer degrees of freedom.

Accepted only when A > 0.

### Tier 3 — Knowledge store (not wired in this PR)

The `itlKnowledgeStore` type is present in the package for future tier-3
support (zero-replica fallback using the last tier-1 fit). It is not wired into
`ThroughputAnalyzer` because `byVariant` only contains variants with active
replica metrics, so tier-3 is unreachable in the current loop structure. Step 2
will extend `Analyze()` to iterate all variant states, not just those with
current metrics.

---

## Supply estimation

Per replica `r`:

```
N_dec_sat = DefaultKSat × KV_max_r / KVreq
μ_dec_sat = N_dec_sat / ITL(k_sat)
```

`KVreq = ILeff + OL/2` — time-averaged KV footprint per decode request.
`ILeff = IL × (1 − PrefixHitRate)` — effective input length after prefix cache.

Per-variant totals: `totalSupply = Σ μ_dec_sat`, `perReplicaSupply = totalSupply / n`.

---

## Demand estimation (priority order)

1. **EPP primary**: when any replica has `ArrivalRate > 0`, demand = `Σ ArrivalRate_r × AvgOutputTokens_r`. `isEPP = true`.
2. **vLLM fallback**: when EPP absent but `VLLMRequestRate > 0`, demand = `sumRate × avgOL`. `isEPP = false`.
3. **k\*-based local** (new in TA3): when both above are zero, `λ_local = Σ k_r* × KV_max_r / KVreq / ITL(k_r*)`. `isEPP = false`.

The k\*-based path enables scale-up signals even when EPP is not deployed.
Scale-down (SpareCapacity) is still gated on `isEPP` to avoid false positives
from the local estimate.

---

## Scheduler queue demand

Added to model-level `totalDemand` after the per-variant loop, for non-prefill
roles only:

```
avgDecodeITLSat = mean(ITL(k_sat)) over decode/both variants
queueDemand     = QueueSize / (DefaultQueueDrainFactor × avgDecodeITLSat)
```

`DefaultQueueDrainFactor = 2.0` — bounds per-request queueing time to
≤ 2 × ITL(k_sat) × avgOL. OL cancels in the derivation (see TA-demand.md §4).

Queue demand is model-level only: it is not attributed to any specific
`VariantCapacity` entry (so `Σ VariantCapacity.TotalDemand ≤ result.TotalDemand`
when a queue is present).

---

## Model-level RC/SC aggregation

RC/SC are computed from model-level totals, not accumulated per-variant:

```
totalAnticipated = Σ_v (current_replicas_v + pending_replicas_v) × perReplicaSupply_v
requiredCapacity = max(0, totalDemand − totalAnticipated)
spareCapacity    = max(0, totalSupply − totalDemand)  if anyEPP else 0
```

**Why totals, not per-variant accumulation:** when variant A is overloaded and
variant B has spare, per-variant gives simultaneous RC and SC signals (conflicting).
Model-level gives a single coherent signal: if total demand < total anticipated
supply, the model does not need more replicas regardless of imbalance.

`PendingReplicas` counts replicas that have been provisioned but not yet in
service. Including them in `totalAnticipated` prevents issuing new scale-up
requests while pods are already starting.

---

## Role-aware aggregation

Roles are populated from `AnalyzerInput.VariantStates` at the start of each
`Analyze()` call and stored in `variantState.role`. Supported values:
`"decode"`, `"prefill"`, `"both"`, `""` (non-disaggregated).

All roles go through the same decode-rate framework (supply = μ_dec_sat, demand
= λ_dec). No role is excluded from supply/demand computation.

`RequiredCapacity` is **suppressed for the prefill role** in `aggregateRoleCapacities`:
decode rate is never the bottleneck for a prefill-only pod. A prefill pod's
decode-rate demand represents decode work it observes, not work it is
responsible for. Prefill-specific rate signals (based on prefill token
throughput) will be added in a later PR.

`SpareCapacity` for a role requires EPP on at least one variant of that role.

`RoleCapacities` is nil when all variants are role `""` or `"both"`
(non-disaggregated model).

---

## Test count

**119 specs**, all passing (40 analyzer + 12 ITL model + 23 observation window + 24 sanity + 16 shape tracker + 4 knowledge store).

New specs in TA3 (beyond PR-3 baseline):
- Context cancellation
- Pending replicas suppress/emit RC
- RoleCapacities populated; prefill RC suppressed; nil for non-disaggregated
- Role set on VariantCapacity and ThroughputVariantState
- Tier-2 constrained OLS numerical verification
- k\*-based local demand (RC emitted; SC gated on EPP)
- Scheduler queue demand (nil vs large queue)
- Model-level aggregation (mixed load → SC only, not both RC and SC)
- `averageShapeMetrics` VLLMRequestRate-weighted averaging (3 specs: weighted, unweighted fallback, mixed)

---

## Branch and PR dependencies

- TA3 branch stacks on TA2
- Submit PR-4 after #1051 (TA1) and #1052 (TA2) have merged into main
- PR-4 closes #1005 (throughput analyzer tracking issue)
