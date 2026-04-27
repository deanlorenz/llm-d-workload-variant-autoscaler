# Throughput Analyzer — Code Review Guide

> **For:** Face-to-face code review of the TA work (PRs 1–5 + ENGINE)  
> **Branch:** TA3 (+ `engine-multi-analyzer`)  
> **Audience:** Engineers familiar with the autoscaler codebase  
> **Use:** Pre-read or presenter's talking guide (one `##` section per topic)

---

## 1. Why a Throughput Analyzer?

The saturation analyzer (V2) detects overload from **instantaneous KV cache state** —
a level signal. It can only trigger *after* utilization has risen.

The throughput analyzer adds a **rate signal**: it measures how fast tokens are
arriving and compares that to the throughput each replica can sustain. It detects
when the current demand *trajectory* will exhaust capacity — before saturation fires.

| | Saturation V2 | Throughput Analyzer |
|---|---|---|
| Signal type | Level (KV%) | Rate (tok/s) |
| Detects | Current overload | Approaching overload |
| Strength | Accurate when saturated | 20–40 s earlier on ramps |
| Weakness | Reactive | May overshoot on spikes |
| Scale-down | Spare KV capacity | EPP arrival rate required |

The two run **in parallel**: scale-up if either signals, scale-down only if both agree.  
Reference: [`ideas/TA-overview.md`](TA-overview.md)

---

## 2. The Core Model: ITL(k) = A·k + B

Inter-token latency grows linearly with KV utilization `k` (empirically validated on H100):

```
ITL(k) = A·k + B
```

- `B` ≈ 0.006 s — hardware baseline at near-zero load (H100 SXM5)
- `A` — workload/hardware slope, fitted from observed (k*, ITL) pairs

**Per-replica supply at k_sat:**
```
N_dec_sat = k_sat × KV_max / KV_req         # concurrent requests at saturation
μ_dec_sat = N_dec_sat / ITL(k_sat)           # decode tokens/sec per replica
```

**Model-level demand** (three-priority chain, EPP → vLLM → k*-based):
```
λ_dec = Σ_r ArrivalRate_r × AvgOutputTokens_r    # EPP primary
      = Σ_r VLLMRequestRate_r × AvgOutputTokens_r # vLLM fallback
```

Scale-up when `λ_dec > anticipated_supply`. Scale-down when `supply > λ_dec` **and EPP is deployed**.

Reference: [`ideas/TA-notation.md`](TA-notation.md), [`ideas/TA-supply.md`](TA-supply.md), [`ideas/TA-demand.md`](TA-demand.md)

---

## 3. PR Structure (6 PRs in Dependency Order)

```
main
  └── ENGINE PR (engine-multi-analyzer)
        └── TA PR-5 (TA3)
              └── TA PR-4 (TA3) [c68210a]
                    └── TA PR-3 (#1052)
                          └── TA PR-1 + PR-2 (#1051)
```

| PR | Branch | What it adds |
|---|---|---|
| **PR-1** | TA1 | 9 Prometheus query registrations in `collector/registration/` |
| **PR-2** | TA1 | Collector wiring: `ReplicaMetrics` gains `ArrivalRate`, `AvgITL`, `VLLMRequestRate`, `KvUtilization` |
| **PR-3** | TA2 | `ShapeTracker`, `ObservationWindow`, `SanityReport`, analyzer stub |
| **PR-4** | TA3 | Full `ThroughputAnalyzer.Analyze()` — ITL model, supply/demand, RC/SC |
| **ENGINE** | engine-multi-analyzer | Generic `analyzers` map + `combineAnalyzerResults()` + `RegisterAnalyzer` |
| **PR-5** | TA3 | Two lines in `main.go` wiring TA into the engine |

PRs 1–3 are upstream (#1051, #1052). ENGINE PR and PR-4/5 are on separate branches, ready to submit.

---

## 4. ITL Model: Two-Tier Estimation

**Problem:** OLS needs spread across k* values. A fresh replica or steady-load replica
may not have enough diversity in the observation window.

**Tier 1 — OLS fit** (when window is Ready: ≥ 10 samples, k-spread ≥ 0.30):
```
FitITLModel(observations) → (A, B) via ordinary least-squares
```

**Tier 2 — Constrained OLS** (B pinned to `DefaultBaselineITLSec = 0.006`):
```
A = Σ((ITL_i − B)·k_i) / Σ(k_i²)     # per-replica points, B fixed
```
Works with a single cycle of data; less accurate but avoids blocking scale-up.

**Logging** (added per Bob's review) — operators can see which tier fired:
```
"throughput analyzer: tier-1 OLS fit"        A=0.073 B=0.006 samples=14
"throughput analyzer: tier-2 constrained OLS fit"  A=0.068 replicas=3
```

Files: [`itl_model.go`](../internal/engines/analyzers/throughput/itl_model.go),
[`analyzer.go:resolveITLModel`](../internal/engines/analyzers/throughput/analyzer.go)

---

## 5. Workload Shape Tracking

The ITL model fit is only valid for a fixed workload shape `(IL, OL, prefix hit rate)`.
When the workload mix shifts, the old observations are stale.

**ShapeTracker** detects a >20% change in `KV_req = IL_eff + OL/2` and clears the observation window:
```go
shape, changed := state.shapeTracker.Observe(il, ol, hitRate)
if changed { state.observationWindow.Clear() }
```

**ObservationWindow** keeps a rolling 30-minute, 20-sample window of `(k*, ITL)` pairs,
filtered to the `[0.15, 0.85]` k-range where the linear model holds.

`Ready()` = ≥ 10 samples AND k-spread ≥ 0.30 — ensures the fit spans a real range
rather than clustering around a single operating point.

Files: [`shape_tracker.go`](../internal/engines/analyzers/throughput/shape_tracker.go),
[`observation_window.go`](../internal/engines/analyzers/throughput/observation_window.go)

---

## 6. Demand Estimation

Three-priority fallback chain per variant:

```
1. EPP primary:      Σ_r ArrivalRate_r × AvgOutputTokens_r
                     (ArrivalRate = EPP dispatch rate per pod)

2. vLLM fallback:    Σ_r VLLMRequestRate_r × AvgOutputTokens_r
                     (when no EPP deployed)

3. k*-based local:   Σ_r k_r* × KV_max_r / KV_req / ITL(k_r*)
                     (scale-up only; no EPP needed, never drives scale-down)
```

**VLLMRequestRate-weighted shape averaging** — replicas with higher throughput
weight proportionally more in the shape estimate. Without this, a hot replica at
OL=100 and a cold one at OL=1000 would average to OL=550 instead of the correct ~190.

**Queue demand** (non-prefill only):
```
λ_queue = QueueSize / (QueueDrainFactor × ITL(k_sat))    # avgOL cancels
```

**Scale-down gate:** `SpareCapacity` is only emitted when `anyEPP = true`. The vLLM
rate and k*-local paths are too noisy to trust for scale-down decisions.

File: [`analyzer.go:computeDemand`](../internal/engines/analyzers/throughput/analyzer.go)

---

## 7. Model-Level RC/SC Aggregation

RC and SC are computed from **model-level totals**, not per-variant deficits.

**Why:** Per-variant would produce simultaneous RC from an overloaded variant and SC
from an underloaded one — contradictory signals to the optimizer.

```go
if totalDemand > totalAnticipated { requiredCapacity = totalDemand - totalAnticipated }
if anyEPP && totalSupply > totalDemand { spareCapacity = totalSupply - totalDemand }
```

**Pending replicas** are included in `totalAnticipated` to suppress scale-up thrashing
while new pods are starting.

**P/D disaggregation:** `RequiredCapacity` is suppressed for prefill-role variants —
the decode-rate model isn't meaningful for prefill pods. `RoleCapacities` provides
per-role breakdowns for the optimizer.

---

## 8. The ENGINE PR: Generic Multi-Analyzer Pipeline

Before this PR, `runAnalyzersAndScore()` had a hardcoded saturation-only path.
Adding a second analyzer required a `switch` case in engine code.

**After ENGINE PR:**

```go
// Engine struct
analyzers map[string]interfaces.Analyzer  // name → implementation

// NewEngine populates it
engine.analyzers = map[string]interfaces.Analyzer{
    interfaces.SaturationAnalyzerName: satV2,
}

// runAnalyzersAndScore iterates config
for _, aw := range config.Analyzers {
    analyzer := e.analyzers[aw.Name]
    result, _ := analyzer.Analyze(ctx, input)
    results = append(results, result)
}
combined := combineAnalyzerResults(satResult, results)
```

**`RegisterAnalyzer`** — callers inject plugins from `main.go` without coupling `engine.go`
to concrete types:
```go
engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer())
```

File: [`engine.go`](../internal/engines/saturation/engine.go),
[`engine_v2.go`](../internal/engines/saturation/engine_v2.go)

---

## 9. The Combine Algorithm

**Problem:** Saturation uses tokens (absolute capacity); throughput uses tok/s.
RC/SC cannot be added directly.

**Solution — dimensionless normalization:**

```
sat_total = Σ_v VariantCapacities_sat_v.TotalCapacity   # current saturation supply

util_excess_i = RC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)   # fraction
util_slack_i  = SC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)

combined.RC = max_i(util_excess_i) × sat_total   # any-up
combined.SC = min_i(util_slack_i)  × sat_total   # all-down; 0 if any analyzer disagrees
```

**Why max/min:**
- Scale-up if **any** analyzer says supply is insufficient (OR logic)
- Scale-down only if **all** analyzers agree (AND logic)

**Saturation always runs** (even when `enabled: false`) — it provides `Cost`,
`AcceleratorName`, and `Role` fields that the optimizer needs for variant selection
and GPU accounting. No other analyzer has CRD access.

File: [`engine_v2.go:combineAnalyzerResults`](../internal/engines/saturation/engine_v2.go),
[`engine_combine_test.go`](../internal/engines/saturation/engine_combine_test.go) (31 specs, 8 scenarios)

---

## 10. PR-5: Wiring (Two Lines)

After ENGINE PR merges into main and TA3 is rebased:

```go
// cmd/main.go — after saturation.NewEngine(...)
registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer())
```

`engine.go` never imports the `throughput` package. The concrete type is injected
from `main.go`. `throughput.AnalyzerName = "throughput"` stays in the `throughput`
package — it's not added to `interfaces` (unlike `SaturationAnalyzerName`, which the
engine uses internally for config-override logic).

---

## 11. Test Coverage

| File | Specs | What's covered |
|---|---|---|
| `analyzer_test.go` | 124 | Scaling signal, tier-1/tier-2, idle, pending, role-aware, RC/SC aggregation, queue demand, guard clauses |
| `itl_model_test.go` | ~12 | OLS math, degenerate inputs |
| `observation_window_test.go` | ~15 | Ready logic, k-range filter, pruning, clear-on-shape-change |
| `shape_tracker_test.go` | ~8 | Tolerance detection, first-call edge case |
| `sanity_test.go` | ~10 | 6 issue types, deduplication |
| `engine_combine_test.go` | 31 | All combine scenarios (8 types) |

Total: **~200 specs** across TA and ENGINE PRs.

Notable: tests use a deterministic `injectWindowObs` helper that seeds the observation window
with exact (k, ITL) pairs computed from known A/B — allows verifying the full
OLS → supply → RC/SC pipeline without randomness.

---

## 12. Key Design Decisions

**D1 — engine.go is decoupled from concrete analyzer types.**  
`analyzers` is `map[string]interfaces.Analyzer`. Engine never imports `throughput`.  
*Rejected:* Adding `case "throughput":` in `runAnalyzersAndScore` — grows unboundedly.

**D2 — Saturation always runs.**  
`Cost`, `AcceleratorName`, `Role` come from the CRD via the capacity store. Only saturation
has this. Making these available without saturation requires extending `VariantReplicaState`.  
*Future:* Deferred to a later cleanup PR.

**D3 — Model-level RC/SC, not per-variant.**  
Prevents contradictory simultaneous scale-up + scale-down signals.

**D4 — Dimensionless combine.**  
Unit-safe normalization across tok/s and tokens. `max`/`min` with re-scaling to
saturation units gives the optimizer a consistent magnitude.

**D5 — Analyzer name constants are package-local.**  
`throughput.AnalyzerName` lives in `throughput`. `interfaces.SaturationAnalyzerName` is
the exception because the saturation engine uses it for internal threshold-override logic.

**D6 — Scale-down requires EPP.**  
vLLM-side request rate and k*-local demand are too noisy for scale-down decisions.
`SpareCapacity` is gated on `anyEPP = true`.

---

## 13. What's Deferred

| Item | Where tracked |
|---|---|
| `DefaultKSat` alignment with EPP system-wide k_sat | TODO in `constants.go` + memory note |
| Stale-metrics gate in `Analyze()` variant loop (check `lastSanityReport`) | TODO in `analyzer.go:204` |
| Prometheus gauges for ITL model A/B coefficients | `CURRENT.md` — issue to open |
| SchedulerQueue wiring (flow-control metrics) | TODO in `engine.go` |
| Tier-3 knowledge store (scale-from-zero ITL lookup) | Skeleton in `itl_knowledge_store.go` |
| Prefill-role rate model (prefill-specific supply/demand) | `aggregateRoleCapacities` comment |
| Engine package rename (`saturation/` → `multianalyzer/`) | PR-3 design doc note |

---

## 14. Discussion Topics

1. **k_sat = 0.85** — does this match what the EPP uses? Should it be a config field
   shared by both, or can each tune independently?

2. **Tier-2 cold-start accuracy** — the constrained OLS pins B at 0.006 (H100 baseline).
   How far off is this on A100 or other hardware? Is a hardware-config override needed?

3. **Scale-down conservatism** — requiring EPP + all analyzers to agree means scale-down
   is slow. Is that the right tradeoff, or do we want a time-based relaxation?

4. **Workload shape stability assumption** — the 20% tolerance on shape change is
   heuristic. For mixed workloads (chat + RAG on the same pool), is this too coarse?

5. **PR submission order** — ENGINE PR targets `main` directly (no TA dependency).
   Submit ENGINE first, wait for merge, then rebase TA3 and submit PR-5.

---

## References

| Document | Location | Purpose |
|---|---|---|
| Overview + motivation | [`ideas/TA-overview.md`](TA-overview.md) | Why this exists |
| Notation + math | [`ideas/TA-notation.md`](TA-notation.md) | Symbol definitions, metric mapping |
| Supply model | [`ideas/TA-supply.md`](TA-supply.md) | ITL model derivation |
| Demand model | [`ideas/TA-demand.md`](TA-demand.md) | Demand chain derivation |
| User guide | [`docs/user-guide/throughput-analyzer.md`](../docs/user-guide/throughput-analyzer.md) | Operator-facing reference |
| Config reference | [`docs/user-guide/saturation-scaling-config.md`](../docs/user-guide/saturation-scaling-config.md) | Multi-analyzer YAML examples |
| Bob's review | [`ideas/TA-PR4-bob.md`](TA-PR4-bob.md) | Independent review of PR-4 |
| PR-4 plan | [`ideas/TA-PR4-plan.md`](TA-PR4-plan.md) | ITL model + scaling signal spec |
| ENGINE plan | [`ideas/ENGINE-multi-analyzer-plan.md`](ENGINE-multi-analyzer-plan.md) | Multi-analyzer pipeline spec |
| PR-5 plan | [`ideas/TA-PR5-plan.md`](TA-PR5-plan.md) | Wiring spec + component ownership |
