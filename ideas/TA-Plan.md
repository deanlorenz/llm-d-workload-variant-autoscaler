# TA-Plan: Supply Estimation Implementation

Implementation roadmap from TA-supply.md theory to production autoscaler.

**Architecture**: New `ThroughputAnalyzer` under `internal/engines/analyzers/throughput/`  
**Metrics**: Registered under `internal/collector/registration/throughput_analyzer.go`  
**Scope**: First 4 PRs focus on μ_dec supply vs λ_dec demand (decode token rate only)

---

## Phase 1: Decode Supply Foundation (μ_dec)

### PR-1: Register Core Rate Metrics — ✅ COMPLETED (#1051, combined with PR-2)

**What**: Register additional queries in `collector/registration/throughput_analyzer.go` for μ_dec calculation.

**New queries to register** (μ_dec foundation):
| Query Name | PromQL | Purpose |
|------------|--------|---------|
| `QueryGenerationTokenRate` | `rate(vllm:request_generation_tokens_sum[1m])` | Observed decode token rate (μ_dec^obs) |
| `QueryKvTokensUsed` | `vllm:kv_cache_usage_perc * num_gpu_blocks * block_size` | Current KV tokens allocated |
| `QueryKvTokensTotal` | `num_gpu_blocks * block_size` (from labels) | Total KV cache capacity |

**Files to modify**:
- `internal/collector/registration/throughput_analyzer.go` - add query registrations

**Files to create**:
- None (extend existing registration file)

**Dependencies**: None

**Test Plan**:
1. Register queries, verify templates execute without error
2. Deploy simulator with known IL=5000, OL=200
3. Verify `QueryGenerationTokenRate` ≈ RPS × 200 tok/s within 5%
4. Verify `QueryKvTokensTotal` matches simulator's `--kv-cache-size`

---

### PR-2: Register Decode Demand Metric (λ_dec) — ✅ COMPLETED (#1051, combined with PR-1)

**What**: Register query for decode token demand from scheduler (total tokens dispatched × average OL).

> **Note**: PR-1 and PR-2 were combined into a single PR (#1051) since the full 9-query set
> is cohesive and there is no useful intermediate state. The final registered set is:
>
> | Query | Metric | Purpose |
> |-------|--------|---------|
> | `generation_token_rate` | `vllm:request_generation_tokens_sum` | μ_dec^obs per pod (1m rate) |
> | `kv_tokens_used` | `vllm:kv_cache_usage_perc` | k* — current KV utilization (instantaneous) |
> | `kv_tokens_total` | `vllm:cache_config_info` | KV_max = num_gpu_blocks × block_size |
> | `ta_avg_itl` | `vllm:time_per_output_token_seconds` | ITL_obs for ITL(k) = A·k + B calibration |
> | `ta_avg_output_tokens` | `vllm:request_generation_tokens` | OL — for KV_req and λ_dec |
> | `ta_avg_input_tokens` | `vllm:request_prompt_tokens` | IL — for IL_eff = IL × (1 − hit_rate) |
> | `ta_prefix_cache_hit_rate` | `vllm:prefix_cache_hits/queries` | Prefix hit rate for IL_eff reduction |
> | `decode_token_demand` | `inference_extension_scheduler_attempts_total` | λ_dec primary (scheduler) |
> | `vllm_request_rate` | `vllm:request_generation_tokens_count` | λ_dec fallback (EPP not deployed) |

**Original plan — Approach options for λ_dec**:
| Option | Source | PromQL | Pros | Cons |
|--------|--------|--------|------|------|
| A | Scheduler | `sum(rate(inference_extension_scheduler_attempts[1m])) * avg_over_time(pod:OL[5m])` | Captures queued demand | May lack pod label for variant tracking |
| B | Scheduler | `sum(rate(scheduler_attempts[1m]) * request_output_tokens)` | Accurate if OL at dispatch | Requires upstream enhancement |
| C | Scheduler | Use existing `QuerySchedulerDispatchRate` × `QueryAvgOutputTokens` | Reuses queries | See Option A cons |
| **D** | **vLLM (weighted)** | `sum(rate(vllm:request_generation_tokens_sum[1m]))` | **Served demand** per variant; always available | Misses queued requests (meets served ≠ demand) |

**Additional vLLM demand option**:
| Option | Formula | Purpose |
|--------|---------|---------|
| D1 | `sum(rate(vllm:request_success_total[1m]))` | λ_served (req/s) |
| D2 | `sum(rate(vllm:request_generation_tokens_sum[1m]))` | λ_dec_served (tok/s) — **same as μ_dec_obs** |
| D3 | ` weighted_avg(OL_pod, weight=req_rate_pod) ` | OL demand profile |

**Decision**: Option C (scheduler dispatch rate) as primary + Option D (vLLM request rate) as fallback.

**Interpretation of gap**:
| Condition | Meaning | Action |
|-----------|---------|--------|
| `λ_sched ≈ λ_vllm` | Low queue, served ≈ demand | Use λ_sched |
| `λ_sched > 1.10 × λ_vllm` | >10% requests queued | Trust λ_sched, scale more aggressively |
| `λ_sched < λ_vllm` | Metric lag or mislabeling | Investigate, fallback to λ_vllm |

**Files to modify**:
- `internal/collector/registration/throughput_analyzer.go` - document decode demand calculation

**Dependencies**: PR-1

**Test Plan**:
1. Run workload: λ = 5 req/s, OL = 200 tok/req
2. Verify `QuerySchedulerDispatchRate` ≈ 5 req/s
3. Verify `QueryAvgOutputTokens` ≈ 200 tok/req
4. Compute λ_dec = 5 × 200 = 1000 tok/s, verify matches expectation

---

## Phase 2: Decode Supply Analyzer (§3)

### PR-3: ThroughputAnalyzer State Management — ✅ COMPLETED (#1052)

**What**: Create new package `internal/engines/analyzers/throughput/` with per-variant
workload shape tracking, ITL observation windows, and sanity diagnostics.

> **Scope change from original plan**: The original PR-3 plan (see below) combined state
> management with the OLS ITL fit in one PR. After design review, state management was
> separated from the fit so each PR is independently reviewable. The OLS fit moves to PR-4.

**Files created**:
```
internal/engines/analyzers/throughput/
├── constants.go               thresholds, window parameters, analyzer name
├── types.go                   WorkloadShape, ITLObservation, SanityIssue, SanityReport
├── shape_tracker.go           ShapeTracker: current (IL,OL) bucket + change detection
├── observation_window.go      ObservationWindow: rolling (k, ITL) pairs, Ready flag
├── sanity.go                  CheckModelMetrics: missing/stale/out-of-range detection
├── analyzer.go                ThroughputAnalyzer: Observe() + Analyze() stub
├── suite_test.go              Ginkgo suite registration
├── shape_tracker_test.go      unit tests
├── observation_window_test.go unit tests
├── sanity_test.go             unit tests
└── analyzer_test.go           integration tests (multi-call state accumulation)
```

**Key design decisions** (see TA-PR3-plan.md for full details):
- State tracked **per variant** (namespace|modelID|variantName) — different hardware → different A/B
- Shape change tolerance: 20% shift in IL or OL triggers ObservationWindow.Clear()
- `ILeff = IL × (1 − PrefixHitRate)` used for both N(k*) and N(k_sat) — cache-aware scheduling
  makes IL_eff the right proxy for new replicas too (EPP prefix routing warms cache quickly)
- ObservationWindow filters k ∈ [0.15, 0.85]; Ready when ≥10 samples with ≥0.30 k-spread
- `Analyze()` returns RequiredCapacity=0 / SpareCapacity=0 until PR-4

**Tests**: 78 Ginkgo tests across all components.

**Dependencies**: PR-1, PR-2 (#1051)

---

#### Original PR-3 Plan (Alternative: state + OLS combined) — kept for reference

The original plan combined state management and ITL model fit in a single PR:

```go
// Rolling window of observations (k, ITL) pairs
type ITLModel struct {
    A, B          float64  // ITL(k) = A*k + B
    window        []Observation  // last 20 points with k ∈ [0.15, 0.80]
    lastFitTime   time.Time
}

// Fit criteria:
// - Min 10 valid observations
// - KV% spread ≥ 0.30 (max_k - min_k)
// - OLS: minimize Σ(ITL_observed - (A*k + B))²
```

**Fallback values**: B = 0.006, A = (ITL_current - B) / k_current

**Recalibration trigger**: `|ΔOL| > 20%` or `|ΔIL| > 20%` or manually via API

**Original file layout**:
```
internal/engines/analyzers/throughput/
├── analyzer.go           # ThroughputAnalyzer struct, Analyze() method
├── itl_model.go          # ITLModel with OLS fit for A, B
├── itl_model_test.go     # Unit tests
└── types.go              # ThroughputMetrics, ScaleRecommendation types
```

**Original Test Plan**:
1. Inject 5 type-1 points: k = 0.20, 0.35, 0.50, 0.65, 0.75; ITL = 0.021, 0.031, 0.043, 0.055, 0.061
2. Verify fitted A ≈ 0.073, B ≈ 0.006 within 10%
3. Verify recalibration triggers on |ΔOL| > 20%

---

### PR-4: ITL Model Fit + μ_dec vs λ_dec Scaling Signal — ✅ COMPLETED (branch TA3)

**What**: Add OLS regression to fit A, B per variant from the observation window, compute
μ_dec supply and λ_dec demand, and produce the RequiredCapacity / SpareCapacity scaling signal.

> **Scope expansion from original plan**: The original PR-4 assumed A, B were already fitted
> by PR-3. Since the fit was deferred, PR-4 now covers both the OLS calibration and the
> supply/demand signal.

**Files added/modified**:
| File | Change |
|---|---|
| `itl_model.go` | New — `ITLModel{A,B}`, `FitITLModel(obs)`, `ITLAt(k)`, `IsZero()` |
| `itl_knowledge_store.go` | New — `itlKnowledgeStore` skeleton for tier-3 (not yet wired) |
| `constants.go` | Added `DefaultKSat=0.85`, `DefaultBaselineITLSec=0.006`, `DefaultQueueDrainFactor=2.0` |
| `types.go` | `ThroughputVariantState` extended with `ITLModel`, `PerReplicaSupply`, `TotalSupply`, `Demand`, `Role` |
| `analyzer.go` | Full `Analyze()`: two-tier ITL, supply/demand, roles, model-level RC/SC, queue demand, k*-based demand fallback, VLLMRequestRate-weighted shape averaging |

**Two-tier ITL model**:
```
Tier 1 (OLS, window Ready):   minimize Σ(ITL_i − A·k_i − B)²
Tier 2 (constrained OLS):     A = Σ((ITL_i − B)·k_i) / Σ(k_i²),  B = DefaultBaselineITLSec
Tier 3 (knowledge store):     present in package, not yet wired (needs step-2 loop restructure)
```

**Supply calculation (μ_dec_sat)**:
```
KVreq     = IL_eff + OL/2                    # time-averaged KV footprint per request
N_dec_sat = DefaultKSat × KV_max / KVreq     # in-flight requests at saturation point
μ_dec_sat = N_dec_sat / ITL(DefaultKSat)     # tokens/sec per replica
```

**Demand calculation (λ_dec), priority order**:
```
1. EPP primary:      Σ ArrivalRate_r × AvgOutputTokens_r        (isEPP = true)
2. vLLM fallback:    Σ VLLMRequestRate_r × AvgOutputTokens_r    (isEPP = false)
3. k*-based local:   Σ k_r* × KV_max_r / KVreq / ITL(k_r*)     (scale-up only)
```

**Queue demand** (added to model-level totalDemand after per-variant loop):
```
queueDemand = QueueSize / (DefaultQueueDrainFactor × avgDecodeITLSat)   (OL cancels)
```

**Scale signal** (model-level totals, not per-variant):
```
totalAnticipated = Σ_v (current_v + pending_v) × perReplicaSupply_v
requiredCapacity = max(0, totalDemand − totalAnticipated)
spareCapacity    = max(0, totalSupply − totalDemand)  if anyEPP else 0
```

**Tests**: 119 Ginkgo specs across all files, all passing.

**Dependencies**: PR-3 (#1052)

---

## Design Alternatives Considered

Key decisions where we explicitly chose one approach over another.

### PR-1: KV capacity query

**Chosen:** Read `TotalKvCapacityTokens` (already collected by `RegisterSaturationQueries` via `QueryCacheConfigInfo` labels).  
**Alternative:** Register a new `QueryKvTokensTotal` (`num_gpu_blocks × block_size`).  
**Why not:** Duplicate registration of the same underlying data; adds query overhead without new information.

### PR-1: KV utilization for ITL model input

**Chosen:** `QueryKvTokensUsed` — instantaneous `max by (pod)` stored in `KvUtilization`.  
**Alternative:** Reuse `QueryKvCacheUsage` — `max_over_time[1m]` (saturation analyzer's `KvCacheUsage`).  
**Why not:** The saturation analyzer needs the worst-case peak for conservative guardrails. The ITL model needs the **current operating point** k*. Using the peak systematically overestimates load and produces premature scale-up.

### PR-2: λ_dec primary source

**Chosen:** Existing `ArrivalRate` from `QuerySchedulerDispatchRate` (already registered). Compute `λ_dec = ArrivalRate × AvgOutputTokens`.  
**Alternatives considered:**
- Option A/B: New scheduler PromQL `rate(scheduler_attempts[1m])` — not needed, `ArrivalRate` already provides this.
- Option D (vLLM-only): Use `VLLMRequestRate` as primary — measures served demand, undercounts under queuing.

`VLLMRequestRate` is registered as a **fallback** for when EPP/scheduler is absent.

### PR-3: State granularity

**Chosen:** Per-variant (`namespace|modelID|variantName`) state.  
**Alternative:** Per-model state.  
**Why not:** Different variants may run on different hardware → different ITL coefficients A/B. Per-model averaging loses this distinction and produces wrong supply estimates for mixed hardware deployments.

### PR-4: RC/SC aggregation

**Chosen:** Model-level totals — `RC = max(0, totalDemand − totalAnticipated)`.  
**Alternative:** Per-variant accumulation — `RC += max(0, demand_v − supply_v)`.  
**Why not:** With per-variant accumulation, when variant A is overloaded and variant B has spare, the result is simultaneous RC and SC (conflicting signals). Model-level aggregation gives one coherent signal.

### PR-4: Shape averaging method

**Chosen:** `averageShapeMetrics` — VLLMRequestRate-weighted mean for IL, OL, PrefixHitRate.  
**Alternative:** Unweighted mean.  
**Why not:** Cold replicas (rate ≈ 0) don't represent the actual served workload. Rate-weighting gives the mean shape that actual traffic sees; unweighted mean dilutes it toward cold-start conditions.

### PR-4: Demand formula (EPP and vLLM paths)

**Chosen:** Per-replica products: `Σ ArrivalRate_r × AvgOutputTokens_r`.  
**Alternative:** `sum(ArrivalRate) × avg(AvgOutputTokens)`.  
**Why not:** When replicas serve different OL distributions, `sumRate × avgOL` over- or under-estimates demand. Per-replica products correctly account for the correlation between request mix and throughput.

### PR-4: Tier-3 knowledge store wiring

**Chosen:** `itlKnowledgeStore` present in package but not wired.  
**Alternative:** Wire tier-3 immediately for zero-replica fallback.  
**Why not:** The current `Analyze()` loop only iterates variants with active replica metrics. Zero-replica variants are invisible. Wiring tier-3 requires a step-2 loop restructure — deferred to avoid scope expansion.

---

## Phase 3: Future Extensions (Post-PR-4)

### PR-5: Mixed Workload Support
**What**: Handle multiple workload bins via weighted average of A.

**Status**: PENDING — defer until single-workload case validated

---

### PR-X Request Rate Model (§4 μ_RPS)
**What**: Extend to request-rate-based supply (μ_RPS) vs demand (λ).

**Status**: PENDING — requires §3 μ_dec working first

---

### PR-Y: Saturation Detection (§5)
**What**: Add TTFT knee prediction and N-based indicators.

**Status**: PENDING — depends on PR-3, PR-4 stable

---

### PR-Z: API Extension (If Needed)
**What**: Extend Analyzer interface or add new API types.

**Principle**: Only if absolutely required by PR-1 through PR-4. Move to standalone PR.

**Potential changes**:
- Add `ThroughputAnalyzerConfig` to `values.yaml`
- Extend `SaturationMetrics` with μ_dec fields
- Add new gRPC/REST endpoints for manual recalibration

**Files potentially affected** (if PR-Z needed):
- `api/v1alpha1/throughput_analyzer_types.go` (new)
- `internal/interfaces/saturation_analyzer.go` (extend)
- `internal/controller/values_types.go` (extend config)

---

## Summary: PR Dependency Graph

```
PR-1/PR-2 (#1051 ✅)  Register all 9 Prometheus queries
    └── PR-3 (#1052 ✅)  State management: ShapeTracker, ObservationWindow, sanity, analyzer skeleton
            └── PR-4 (TA3 ✅)  Two-tier ITL model + μ_dec supply + λ_dec demand + model-level RC/SC
                    └── PR-5 (pending)  Wire analyzer into engine pipeline
```

**Phase 1 scope**: PR-1 through PR-4 only — μ_dec supply vs λ_dec demand

**Isolation principles**:
- New analyzer only touches `engines/analyzers/throughput/` and `collector/registration/`
- No changes to existing saturation/queueing analyzers
- No API changes unless absolutely required (moved to PR-Z)
- Look at existing analyzers for inspiration, but don't share code
