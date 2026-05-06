# PR-4: ITL Model Fit and Scaling Signal

> **Status: COMPLETE** — Implemented on branch TA3. Targets upstream `main` after
> PR-3 (#1052) merges. Part of #1005; does not close it — wiring into the engine
> pipeline (PR-5) is still required.

## Context

PR-3 built the stateful substrate: per-variant `ShapeTracker`, `ObservationWindow`,
`SanityReport`, and a no-signal `Analyze()` stub. PR-4 extends this with the full ITL
model calibration pipeline, per-replica supply estimation, three-priority demand
estimation, queue demand contribution, and the model-level scaling signal.

**Scope:** OLS ITL model fit, μ_dec supply vs λ_dec demand, RequiredCapacity /
SpareCapacity output. No changes to existing analyzers. No engine wiring.

---

## Key Design Decisions

### Two-tier ITL model resolution

The ITL model `ITL(k) = A·k + B` is fit from the observation window. Two tiers handle
the case where the window is not yet ready:

- **Tier 1 (OLS):** When the window has ≥10 samples spanning ≥30% k-range, standard
  OLS minimises `Σ(ITL_i − A·k_i − B)²`. Both A and B are free parameters.
  Accepted only when `A > 0` (physically required: higher concurrency → higher latency).

- **Tier 2 (constrained OLS):** When the window is not ready, B is pinned to
  `DefaultBaselineITLSec` (0.006 s — H100 baseline at near-zero load) and only A is
  fitted: `A = Σ((ITL_i − B)·k_i) / Σ(k_i²)`. For a single replica this reduces to
  the single-point formula `A = (ITL − B) / k*`. For multiple replicas it is strictly
  better (same OLS criterion, fewer degrees of freedom). Accepted only when `A > 0`.

- **Tier 3 (knowledge store):** The `itlKnowledgeStore` type is present in the package
  to persist the last tier-1 fit per variant, enabling supply estimates during
  zero-replica periods. Not wired yet — requires iterating all variant states in step-2
  of the engine loop, not just those with current replica metrics.

### Supply: saturation throughput per replica

Supply is the token throughput a replica can sustain at the KV saturation point
(`k_sat = DefaultKSat = 0.85`). Starting from the ITL model:

```
KVreq       = ILeff + OL/2            time-averaged KV footprint per decode request
N_dec_sat   = k_sat × KV_max / KVreq  in-flight requests a replica can hold at k_sat
μ_dec_sat   = N_dec_sat / ITL(k_sat)  tokens/sec per replica at saturation
```

`perReplicaSupply = totalSupply / n` is stored for use in anticipated-supply
computation. RC suppression for `"prefill"` role: decode rate is not the bottleneck
for a prefill-only pod.

### Demand: three-priority fallback chain

λ_dec is computed once per variant then summed at model level. Priority order:

1. **EPP primary** (`isEPP = true`): any replica has `ArrivalRate > 0`. Demand uses
   per-replica products `Σ ArrivalRate_r × AvgOutputTokens_r` to avoid distortion
   from replicas with different throughput.
2. **vLLM fallback** (`isEPP = false`): no EPP, but `VLLMRequestRate > 0`. Same
   per-replica product: `Σ VLLMRequestRate_r × AvgOutputTokens_r`.
3. **k\*-based local** (`isEPP = false`, scale-up only): both above are zero. Estimates
   demand from current KV utilization: `λ_local = Σ k_r* × KV_max_r / KVreq /
   ITL(k_r*)`. Used only for scale-up signals; `SpareCapacity` is suppressed without
   EPP to avoid false positives.

### Queue demand added at model level

After the per-variant loop, queued requests contribute additional demand:
`queueDemand = QueueSize / (QueueDrainFactor × avgDecodeITLSat)`. OL cancels in the
derivation (see TA-demand.md §4). `avgDecodeITLSat` is the mean `ITL(k_sat)` over
decode/both variants. Queue demand is model-level only — not attributed to any
specific variant.

### Model-level RC/SC prevents conflicting signals

RC and SC are computed from model-level totals, not accumulated per-variant. When
variant A is overloaded and variant B has spare capacity, per-variant accumulation
produces simultaneous RC and SC (conflicting). Model-level gives one coherent signal:
if total demand < total anticipated supply, no new replicas are needed regardless of
imbalance.

```
totalAnticipated = Σ (current_v + pending_v) × perReplicaSupply_v
RC = max(0, totalDemand − totalAnticipated)
SC = max(0, totalSupply − totalDemand)   [only if anyEPP]
```

`PendingReplicas` are included in `totalAnticipated` to suppress scale-up thrashing
while pods are starting.

### VLLMRequestRate-weighted shape averaging

`averageShapeMetrics` computes fleet-average IL, OL, and PrefixHitRate weighted by
`VLLMRequestRate` per replica. This prevents high-OL replicas from dominating when
they have low throughput. Falls back to unweighted mean when all rates are zero (e.g.,
cold start). Implemented as a one-pass accumulation of both weighted and unweighted
sums.

---

## Components

### New files in `internal/engines/analyzers/throughput/`

**`itl_model.go`** — `ITLModel{A, B float64}`. `FitITLModel(obs)` runs tier-1 OLS
over a slice of `ITLObservation`. `ITLAt(k)` evaluates the model. `IsZero()` tests
for an uninitialized model. All functions are pure (no state mutation).

**`itl_knowledge_store.go`** — `itlKnowledgeStore` — stores the last tier-1 fit per
variant key. Not wired into `ThroughputAnalyzer` in this PR. Present for tier-3
support once the step-2 loop restructure is done.

### Modified files

**`constants.go`** — Three new constants added: `DefaultKSat = 0.85` (KV saturation
operating point), `DefaultBaselineITLSec = 0.006` (tier-2 B pin), and
`DefaultQueueDrainFactor = 2.0` (queue demand denominator).

**`types.go`** — `ThroughputVariantState` extended with `ITLModel`, `PerReplicaSupply`,
`TotalSupply`, `Demand`, and `Role` fields for read-only inspection.

**`analyzer.go`** — Full `Analyze()` implementation. Key helpers: `computeVariantSupply`
(μ_dec_sat per variant), `computeDemand` (three-priority λ_dec), `aggregateRoleCapacities`
(role-aware RC/SC), `averageShapeMetrics` (VLLMRequestRate-weighted IL/OL/hitRate).

---

## Data Flow (Analyze)

```
AnalyzerInput.VariantStates + []ReplicaMetrics
    │
    ├── Observe() — shape tracking, window accumulation (same as PR-3)
    │
    └── per variant v:
            averageShapeMetrics → (IL, OL, hitRate, KVreq, ILeff)
            resolve ITL tier (1→2→3) → ITLModel{A, B}
            computeVariantSupply → (μ_dec_sat, perReplicaSupply)
            computeDemand → (λ_dec, isEPP)
            accumulate: totalSupply, totalDemand, totalAnticipated
    │
    model-level:
        queueDemand → totalDemand += queueDemand
        RC = max(0, totalDemand − totalAnticipated)
        SC = max(0, totalSupply − totalDemand)  if anyEPP
        aggregateRoleCapacities → RoleCapacities (nil if non-disaggregated)
    │
    return *AnalyzerResult{RequiredCapacity, SpareCapacity, RoleCapacities, ...}
```

---

## Tests

119 Ginkgo specs total: 40 (analyzer) + 12 (itl_model) + 23 (observation_window) +
24 (sanity) + 16 (shape_tracker) + 4 (itl_knowledge_store). All passing.

Key new scenarios in TA3 (beyond PR-3 baseline):
- Tier-1 and tier-2 OLS numerical accuracy
- Scale-up (RC > 0) and scale-down (SC > 0) with EPP
- k\*-based local demand emits RC; SC gated on EPP
- Pending replicas suppress RC during pod startup
- Queue demand adds to model-level totalDemand
- Mixed-load: SC only (no simultaneous RC+SC)
- `RoleCapacities` populated; prefill RC suppressed; nil for non-disaggregated
- `averageShapeMetrics`: weighted mean, unweighted fallback, mixed (zero-rate replicas excluded)

---

## Not in this PR

- Tier-3 knowledge store wiring — requires step-2 loop restructure (iterate all variant
  states, not just those with current metrics)
- Prefill-specific rate signals — prefill pods go through decode framework for now; RC
  suppressed for prefill role
- `DefaultKSat` unification — kept per-analyzer; needs alignment with EPP's system-wide k_sat
- Wiring into the engine's analyzer pipeline — PR-5
