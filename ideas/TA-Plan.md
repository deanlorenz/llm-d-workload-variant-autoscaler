# TA-Plan: Supply Estimation Implementation

Implementation roadmap from TA-supply.md theory to production autoscaler.

**Architecture**: New `ThroughputAnalyzer` under `internal/engines/analyzers/throughput/`  
**Metrics**: Registered under `internal/collector/registration/throughput_analyzer.go`  
**Scope**: First 4 PRs focus on μ_dec supply vs λ_dec demand (decode token rate only)

---

## Phase 1: Decode Supply Foundation (μ_dec)

### PR-1: Register Core Rate Metrics
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

### PR-2: Register Decode Demand Metric (λ_dec)
**What**: Register query for decode token demand from scheduler (total tokens dispatched × average OL).

**New query to register**:
| Query Name | PromQL | Purpose |
|------------|--------|---------|
| `QueryDecodeTokenDemand` | `rate(inference_extension_scheduler_attempts_total[1m]) * avg(output_tokens)` | λ_dec = demand in tok/s |

**Approach options**:
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

**Recommendation**: **Option C + Option D as sanity check**:
- Primary: `λ_dec_sched = QuerySchedulerDispatchRate × QueryAvgOutputTokens`
- Sanity: `λ_dec_vllm = sum(rate(vllm:request_generation_tokens_sum[1m]))`
- Alert if `|λ_dec_sched - λ_dec_vllm| / λ_dec_sched > 0.10` (indicates >10% queueing)

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

### PR-3: ThroughputAnalyzer Skeleton + ITL Calibration
**What**: Create new analyzer under `engines/analyzers/throughput/` with ITL model (A, B) fitting.

**Files to create**:
```
internal/engines/analyzers/throughput/
├── analyzer.go           # ThroughputAnalyzer struct, Analyze() method
├── itl_model.go          # ITLModel with OLS fit for A, B
├── itl_model_test.go     # Unit tests
└── types.go              # ThroughputMetrics, ScaleRecommendation types
```

**ITL Calibration Logic**:
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

**Dependencies**: PR-1, PR-2

**Test Plan**:
1. Inject 5 type-1 points: k = 0.20, 0.35, 0.50, 0.65, 0.75; ITL = 0.021, 0.031, 0.043, 0.055, 0.061
2. Verify fitted A ≈ 0.073, B ≈ 0.006 within 10%
3. Verify recalibration triggers on |ΔOL| > 20%

---

### PR-4: μ_dec Supply vs λ_dec Demand Calculation
**What**: Compute μ_dec supply estimate and compare to λ_dec demand.

**Files to modify**:
- `internal/engines/analyzers/throughput/analyzer.go` - add Analyze() implementation

**Supply calculation (μ_dec)**:
```
Inputs: k*, IL_eff, OL, KV_max, A, B
KV_req    = IL_eff + OL/2
N_dec(k*) = k* × KV_max / KV_req
ITL(k*)   = A × k* + B
μ_dec     = N_dec(k*) / ITL(k*)    # tok/s
```

**Demand calculation (λ_dec)**:
```
Inputs: λ (from QuerySchedulerDispatchRate), OL
λ_dec = λ × OL    # tok/s
```

**Scale signal**:
```
if λ_dec > μ_dec × safety_factor:
    recommendation = SCALE_UP
    reason = "decode_demand_exceeds_supply"
else if λ_dec < μ_dec × down_threshold:
    recommendation = SCALE_DOWN
    reason = "decode_supply_exceeds_demand"
else:
    recommendation = HOLD
```

**Output metrics** (exported via `ThroughputMetrics`):
| Metric | Description |
|--------|-------------|
| `μ_dec_current` | Current decode supply (tok/s) |
| `μ_dec_sat` | Target decode supply at k_sat (tok/s) |
| `λ_dec` | Current decode demand (tok/s) |
| `saturation_ratio` | λ_dec / μ_dec |

**Dependencies**: PR-3

**Test Plan**:
1. Run at k* = 0.75 with known A=0.073, B=0.006, IL=5000, OL=200
   - KV_max = 1024000 (1024 blocks × 16 × 16)
   - KV_req = 5000 × (1-0.1) + 100 = 4600
   - N_dec = 0.75 × 1024000 / 4600 ≈ 167
   - ITL = 0.073 × 0.75 + 0.006 = 0.061
   - μ_dec = 167 / 0.061 ≈ 2738 tok/s
2. Set λ = 10 req/s, OL = 200 → λ_dec = 2000 tok/s
3. Verify saturation_ratio = 2000/2738 ≈ 0.73 → HOLD
4. Set λ = 15 req/s → λ_dec = 3000 tok/s → SCALE_UP

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
PR-1 (Register Queries)
    └── PR-2 (Decode Demand Query)
            └── PR-3 (ITL Model + Analyzer Skeleton)
                    └── PR-4 (μ_dec vs λ_dec Scale Logic)
```

**Phase 1 scope**: PR-1 through PR-4 only — μ_dec supply vs λ_dec demand

**Isolation principles**:
- New analyzer only touches `engines/analyzers/throughput/` and `collector/registration/`
- No changes to existing saturation/queueing analyzers
- No API changes unless absolutely required (moved to PR-Z)
- Look at existing analyzers for inspiration, but don't share code

**Estimated Timeline**: ~2 weeks for PR-1 through PR-4