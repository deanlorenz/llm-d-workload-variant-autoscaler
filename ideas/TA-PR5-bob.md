# PR-5 Plan Review - Bob's Recommendations

**Review Date:** 2026-04-26  
**Document:** TA-PR5-plan.md  
**Reviewer:** Bob Shell  
**Status:** Plan Review - Pre-Implementation

---

## Executive Summary

The PR-5 plan is **well-structured and appropriately scoped**. After validating against the ENGINE multi-analyzer plan (branch `engine-multi-analyzer`), all key assumptions are confirmed correct.

**ENGINE Plan Validation:** ✅ PASSED
- Generic analyzer map infrastructure: Confirmed
- Combine algorithm (any-up / all-down): Confirmed  
- Saturation always runs: Confirmed
- TA registration ownership: Clarified (PR-5 owns it)

**Recommendation:** Approve plan after addressing documentation gaps (config schema, rollback plan, observability).

**Key Finding:** The ENGINE plan explicitly states "ThroughputAnalyzer registration in the engine — separate TA wiring PR" in its "Not in This PR" section, confirming that PR-5 owns the registration despite the ENGINE plan showing it as a code example.

---

## Strengths

### 1. **Clear Dependency Management**
- Correctly identifies ENGINE PR as prerequisite
- Acknowledges that ENGINE PR does the heavy lifting (combine logic, map infrastructure)
- Scopes PR-5 to just registration + validation

### 2. **Appropriate Scope**
- No changes to analyzer package (already complete in PR-4)
- No changes to optimizer (already handles multiple analyzers)
- No changes to combine logic (handled by ENGINE PR)
- Focus on integration validation only

### 3. **Good E2E Test Coverage**
- 5 scenarios cover key integration points
- Tests verify both TA-only and dual-analyzer modes
- Cold-start scenario included

### 4. **Realistic Assessment**
- Acknowledges SchedulerQueue is nil (deferred)
- Acknowledges tier-3 knowledge store not wired (deferred)
- No scope creep

---

## Critical Issues

### Issue 1: ENGINE Plan Validation - ✅ RESOLVED

**Status:** ENGINE multi-analyzer plan found on branch `engine-multi-analyzer`.

**Validation Results:**
- ✅ ENGINE plan defines `analyzers map[string]interfaces.Analyzer` in Engine struct
- ✅ ENGINE plan implements generic loop in `runAnalyzersAndScore()`
- ✅ ENGINE plan implements combine algorithm (D4: dimensionless normalization)
- ✅ ENGINE plan includes example registration: `throughput.AnalyzerName: throughput.NewThroughputAnalyzer()`
- ✅ ENGINE plan calls `registration.RegisterThroughputAnalyzerQueries()` in `NewEngine()`

**Key Alignment:**
- PR-5 assumption: "ENGINE PR adds the throughput entry as a code example" → **CONFIRMED** in ENGINE plan section "engine.go Changes"
- PR-5 assumption: "any-up / all-down" combine → **CONFIRMED** in ENGINE plan D4 algorithm
- PR-5 assumption: "Saturation always runs" → **CONFIRMED** in ENGINE plan D2

**Dependency Status:**
```markdown
## Dependencies

- ✅ TA1 (#1051) - Merged
- ✅ TA2 (#1052) - Merged  
- ✅ TA3/PR-4 (branch TA3) - Ready for merge
- ✅ ENGINE multi-analyzer (branch engine-multi-analyzer) - Plan complete, implementation status unknown

**Action Required:** Verify ENGINE branch implementation status before starting PR-5.
```

---

### Issue 2: Registration Ownership - ✅ CLARIFIED by ENGINE Plan

**ENGINE Plan Says:** In section "engine.go Changes", the ENGINE plan includes this example:

```go
engine.analyzers = map[string]interfaces.Analyzer{
    interfaces.SaturationAnalyzerName: saturation_v2.NewSaturationAnalyzer(capacityStore),
    throughput.AnalyzerName:           throughput.NewThroughputAnalyzer(),
}
```

**Interpretation:** The ENGINE plan shows the TA registration as a **code example** to demonstrate the pattern, but the "Not in This PR" section explicitly states:

> "ThroughputAnalyzer registration in the engine — separate TA wiring PR"

**Conclusion:** 
- ENGINE PR provides the **infrastructure** (map, loop, combine)
- PR-5 provides the **registration** (adding ThroughputAnalyzer to the map)
- The ENGINE plan's code example is for illustration only

**Recommendation for PR-5:** Own the registration explicitly:

```markdown
## Registration Ownership

**Decision:** The ENGINE PR provides the *infrastructure* (map, loop, combine).
The TA PR-5 provides the *registration* (adding ThroughputAnalyzer to the map).

**Rationale:** Each analyzer PR owns its own registration. This keeps analyzer
changes self-contained and avoids cross-PR dependencies.

**Code location:** `internal/engines/saturation/engine.go`, `NewEngine()`:

```go
func NewEngine(...) *Engine {
    // ... existing code ...
    
    e.analyzers = map[string]interfaces.Analyzer{
        interfaces.SaturationAnalyzerName: saturation_v2.NewSaturationAnalyzer(capacityStore),
        throughput.AnalyzerName:           throughput.NewThroughputAnalyzer(), // ← TA PR-5 adds this
    }
    
    // ... rest of function ...
}
```
```

---

### Issue 3: Missing Config Schema Documentation

**Problem:** The plan says "No TA-specific config" but doesn't document how users enable/disable the TA or set its score.

**Impact:** Users won't know how to configure the TA.

**Recommendation:** Add a config section:

```markdown
## Configuration

Users enable the ThroughputAnalyzer via the `analyzers` list in the WVA ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: workload-variant-autoscaler-config
  namespace: llm-d-system
data:
  config.yaml: |
    analyzers:
      - name: saturation
        enabled: true
        score: 1.0
      - name: throughput      # ← TA PR-5 documents this
        enabled: true
        score: 1.0
```

**Default behavior when `throughput` entry is absent:**
- Analyzer is **disabled** (not in the map → not executed)
- No error; saturation-only mode continues to work

**TA-only mode (for testing):**
```yaml
analyzers:
  - name: saturation
    enabled: false    # RC/SC excluded from combine, but VariantCapacities still flow
  - name: throughput
    enabled: true
    score: 1.0
```

**No TA-specific thresholds:** The TA uses internal constants (`DefaultKSat`, etc.).
Future PRs may add per-analyzer threshold overrides.
```

---

## ENGINE Plan Validation

After reviewing the ENGINE multi-analyzer plan on branch `engine-multi-analyzer`, here's how it aligns with PR-5 assumptions:

### ✅ Confirmed Assumptions

| PR-5 Assumption | ENGINE Plan Reality | Status |
|-----------------|---------------------|--------|
| ENGINE provides `analyzers` map | ✅ Defined in Engine struct | Confirmed |
| Generic loop in `runAnalyzersAndScore()` | ✅ Iterates `config.Analyzers`, looks up in map | Confirmed |
| Combine algorithm: any-up / all-down | ✅ D4: dimensionless normalization, max/min combine | Confirmed |
| Saturation always runs | ✅ D2: Pre-population step always executes | Confirmed |
| `RegisterThroughputAnalyzerQueries()` called | ✅ In `NewEngine()` alongside other registrations | Confirmed |
| TA registration shown as example | ✅ In "engine.go Changes" section | Confirmed |
| TA registration NOT in ENGINE PR scope | ✅ "Not in This PR" section explicitly states this | Confirmed |

### 🔍 Key ENGINE Design Decisions Affecting PR-5

**D4 - Combine Algorithm (Critical for PR-5 tests):**
```
util_excess_i = RC_i / Σ_v(TotalCapacity_i_v)  # dimensionless
util_slack_i  = SC_i / Σ_v(TotalCapacity_i_v)

combined.RC = max_i(util_excess_i) × sat_total
combined.SC = min_i(util_slack_i) × sat_total
```

**Implication for PR-5:** E2E tests must verify that:
- When TA says RC=200 tok/s and saturation says RC=0, combined RC > 0 (any-up fires)
- When TA says SC=100 tok/s and saturation says SC=0, combined SC = 0 (all-down blocks)

**D2 - Saturation Always Runs:**
Even when `saturation: enabled: false`, saturation's `VariantCapacities` (with `Cost`, `AcceleratorName`) flow to the optimizer. Only RC/SC are excluded from combine.

**Implication for PR-5:** TA-only tests must verify that:
- Saturation RC/SC = 0 in combine
- Optimizer still receives `Cost` and `AcceleratorName` from saturation's VariantCapacities

**OQ1 - Cold Start (sat_total = 0):**
ENGINE plan asks: "What happens when sat_total = 0?" and proposes: "if any analyzer has RC > 0, return unit RC (e.g., 1.0) to trigger optimizer."

**Implication for PR-5:** Cold-start test (0→1 replica) must verify this edge case works.

### ⚠️ Open Questions from ENGINE Plan

The ENGINE plan has two open questions that affect PR-5:

**OQ1:** What happens when `sat_total = 0` in `combineResults`?
- **PR-5 Impact:** Cold-start test must verify the mitigation works
- **Recommendation:** Add assertion that combined.RC > 0 when any analyzer has RC > 0 and sat_total = 0

**OQ2:** Score formula when saturation is disabled.
- **PR-5 Impact:** TA-only tests must verify Score = priority × (RC_tp × tp_score)
- **Recommendation:** Add assertion on Score value in TA-only scale-up test

---

## Important Clarifications Needed

### Clarification 1: What Happens When Both Analyzers Disagree on Scale Direction?

**Scenario:** Saturation says "scale up" (RC > 0), TA says "scale down" (SC > 0).

**Current plan says:** "any-up / all-down" → scale up wins.

**Question:** Is this the intended behavior? Should we add a "conflict resolution" log message?

**Recommendation:**
```markdown
## Conflict Resolution

When analyzers disagree on scale direction:
- **Scale-up wins** (any-up rule): If *any* analyzer has RC > 0, scale up
- **Scale-down blocked** (all-down rule): If *any* analyzer has RC > 0, SC = 0

**Logging:** Add a warning when this occurs:
```go
if combinedRC > 0 && anySC > 0 {
    ctrl.Log.V(logging.INFO).Info("analyzer conflict: scale-up and scale-down signals present, scale-up wins",
        "modelID", modelID,
        "namespace", namespace,
        "requiredCapacity", combinedRC,
        "spareCapacityIgnored", anySC,
    )
}
```

**Rationale:** Prevents oscillation. Scale-up is safer than premature scale-down.
```

---

### Clarification 2: How Are Analyzer Scores Used?

**Current plan says:** "Score = priority × Σ(RC_i × score_i)"

**Question:** What is `priority`? Is it per-model or global?

**Recommendation:** Add a scoring section:

```markdown
## Scoring Algorithm

The combined `Score` field in `AnalyzerResult` is used by the optimizer for
cross-model prioritization when GPU resources are limited.

**Formula:**
```
Score = modelPriority × Σ_i (RC_i × analyzerScore_i)
```

Where:
- `modelPriority` = from WVA CRD `spec.priority` (default 1.0)
- `RC_i` = RequiredCapacity from analyzer `i` (in analyzer's native units)
- `analyzerScore_i` = from config `analyzers[i].score` (default 1.0)

**Example:**
- Model A: saturation RC=100 (score=1.0), throughput RC=200 (score=1.0), priority=1.0
  → Score = 1.0 × (100×1.0 + 200×1.0) = 300
- Model B: saturation RC=150 (score=1.0), throughput RC=0 (score=1.0), priority=2.0
  → Score = 2.0 × (150×1.0 + 0×1.0) = 300

Both models have equal priority for GPU allocation.

**Note:** Scores are only used for cross-model prioritization. Within a model,
the combine algorithm uses dimensionless replica counts (any-up / all-down).
```

---

### Clarification 3: What Happens When TA Has No ITL Model?

**Scenario:** Cold start, no OLS window, all replicas idle (k* = 0).

**Current plan says:** "Cold-start scenario included" in e2e tests.

**Question:** What does the TA return in this case? RC=0, SC=0?

**Recommendation:**
```markdown
## Cold-Start Behavior

When the TA cannot resolve an ITL model (no OLS window, all replicas idle):
- `resolveITLModel()` returns `(zero ITLModel, false)`
- Variant is skipped in the per-variant loop
- No contribution to `totalSupply`, `totalDemand`, or `VariantCapacities`
- **Result:** TA returns RC=0, SC=0 (no signal)

**Implication:** During cold start, saturation analyzer drives scaling decisions.
Once replicas start serving traffic and k* > 0, the TA begins contributing.

**E2E test:** Verify that a 0→1 replica scale-up triggered by saturation allows
the TA to calibrate on the first replica, then TA can drive 1→2 scale-up.
```

---

## Missing Sections

### Missing 1: Rollback Plan

**Problem:** No rollback strategy if TA causes issues in production.

**Recommendation:**
```markdown
## Rollback Plan

If the ThroughputAnalyzer causes unexpected scaling behavior:

**Option 1: Disable via config (no restart required)**
```yaml
analyzers:
  - name: throughput
    enabled: false  # ← set to false, apply ConfigMap
```
The controller picks up the config change within 1 reconcile cycle (~30s).

**Option 2: Remove from engine (requires restart)**
Comment out the registration in `NewEngine()`:
```go
e.analyzers = map[string]interfaces.Analyzer{
    interfaces.SaturationAnalyzerName: saturation_v2.NewSaturationAnalyzer(capacityStore),
    // throughput.AnalyzerName:           throughput.NewThroughputAnalyzer(), // ← comment out
}
```
Rebuild and redeploy the controller.

**Option 3: Revert the PR**
```bash
git revert <PR-5-commit-sha>
git push origin main
```

**Monitoring:** Watch for:
- Unexpected scale-up/down events (check controller logs for "throughput analyzer" entries)
- RC/SC values in AnalyzerResult (should be reasonable relative to saturation)
- ITL model coefficients (A should be positive, B should be ~0.006 for H100)
```

---

### Missing 2: Observability Plan

**Problem:** No guidance on how operators monitor TA health.

**Recommendation:**
```markdown
## Observability

### Metrics to Monitor

**TA-specific (if exported in future PR):**
- `wva_throughput_analyzer_itl_model_a{namespace, model_id, variant, tier}`
- `wva_throughput_analyzer_itl_model_b{namespace, model_id, variant, tier}`
- `wva_throughput_analyzer_observation_window_size{namespace, model_id, variant}`
- `wva_throughput_analyzer_observation_window_ready{namespace, model_id, variant}`

**Existing metrics to correlate:**
- `vllm:kv_cache_usage_perc` (k* — should correlate with TA scale-up signals)
- `vllm:request_generation_tokens_sum` (μ_dec^obs — should match TA supply estimates)
- `inference_extension_scheduler_attempts_total` (λ_req — should match TA demand estimates)

### Logs to Watch

**INFO level:**
- "throughput analyzer: tier-1 OLS fit successful" (A, B, samples)
- "throughput analyzer: tier-2 constrained OLS successful" (A, B, replicas)
- "analyzer conflict: scale-up and scale-down signals present" (when TA and saturation disagree)

**DEBUG level:**
- "throughput analyzer: workload shape changed, clearing observation window"
- "throughput analyzer: sanity issues detected, skipping variant"
- "throughput analyzer: no ITL model available, skipping variant"

### Grafana Dashboard

Add panels for:
1. **ITL Model Coefficients** (A, B over time per variant)
2. **Supply vs Demand** (μ_dec_sat vs λ_dec per variant)
3. **Observation Window Status** (Ready flag, sample count, k-spread)
4. **Scaling Decisions** (RC, SC over time, color-coded by analyzer)
```

---

### Missing 3: Upgrade Path

**Problem:** No guidance on upgrading from saturation-only to dual-analyzer mode.

**Recommendation:**
```markdown
## Upgrade Path

### From Saturation-Only to Dual-Analyzer

**Step 1: Deploy PR-5 with TA disabled**
```yaml
analyzers:
  - name: saturation
    enabled: true
    score: 1.0
  - name: throughput
    enabled: false  # ← start disabled
    score: 1.0
```
Verify no regressions in saturation-only mode.

**Step 2: Enable TA in canary namespace**
```yaml
# In canary namespace ConfigMap only
analyzers:
  - name: saturation
    enabled: true
    score: 1.0
  - name: throughput
    enabled: true   # ← enable in canary
    score: 0.5      # ← lower score initially
```
Monitor for 24-48 hours. Verify:
- No unexpected scale-up/down events
- ITL model coefficients are reasonable (A > 0, B ≈ 0.006)
- Supply/demand estimates match observed metrics

**Step 3: Increase TA score gradually**
```yaml
analyzers:
  - name: throughput
    enabled: true
    score: 1.0  # ← equal weight with saturation
```

**Step 4: Roll out to production namespaces**
One namespace at a time, with 24-hour soak between each.

### Rollback at Any Step
Set `enabled: false` in the ConfigMap. No restart required.
```

---

## E2E Test Recommendations

### Test 1: TA-Only Scale-Up (Existing)
**Status:** ✅ Good as-is

**Enhancement:** Add assertion that saturation RC=0, SC=0 (excluded from combine).

---

### Test 2: TA-Only Scale-Down (Existing)
**Status:** ✅ Good as-is

**Enhancement:** Verify that EPP is deployed (ArrivalRate > 0) before expecting SC > 0.

---

### Test 3: Dual-Analyzer Scale-Up (Existing)
**Status:** ✅ Good as-is

**Enhancement:** Add a variant where saturation says "scale up" and TA says "no change" → verify scale-up still happens (any-up rule).

---

### Test 4: Dual-Analyzer Scale-Down Blocked (Existing)
**Status:** ✅ Good as-is

**Enhancement:** Add logging assertion to verify "analyzer conflict" warning is emitted.

---

### Test 5: Cold-Start (Existing)
**Status:** ⚠️ Needs clarification

**Question:** Does "cold-start" mean 0→1 replica (saturation-driven) or 1→2 replica (TA-driven after calibration)?

**Recommendation:** Split into two tests:
- **Test 5a:** 0→1 replica scale-up (saturation-driven, TA has no signal)
- **Test 5b:** 1→2 replica scale-up (TA-driven after tier-2 calibration on first replica)

---

### Missing Test 6: TA Tier-2 Fallback
**Scenario:** Single replica at k*=0.75, no OLS window → tier-2 constrained OLS → RC > 0

**Why:** Validates that tier-2 works in practice, not just in unit tests.

---

### Missing Test 7: Shape Change Clears Window
**Scenario:** Build OLS window, then shift IL by 50% → window clears → tier-2 fallback → still produces signal

**Why:** Validates that shape change detection works end-to-end.

---

### Missing Test 8: Pending Replicas Suppress Scale-Up
**Scenario:** 1 replica saturated, 1 pending → TA RC=0 (anticipated supply covers demand)

**Why:** Validates that pending replica logic prevents cascade scaling.

---

### Missing Test 9: Queue Demand Contribution
**Scenario:** 1 replica at k*=0.50, QueueSize=200 → TA RC > 0 (queue demand pushes over threshold)

**Why:** Validates queue demand integration (when SchedulerQueue is wired).

**Note:** Defer to later PR if SchedulerQueue wiring is not in PR-5 scope.

---

### Missing Test 10: Role-Aware Aggregation
**Scenario:** P/D disaggregated model, prefill variant overloaded → prefill RC=0 (suppressed), decode RC > 0

**Why:** Validates that prefill RC suppression works in the engine pipeline.

---

## Implementation Checklist

Based on the plan, here's what PR-5 needs to deliver:

### Code Changes
- [ ] Add `throughput.AnalyzerName: throughput.NewThroughputAnalyzer()` to `Engine.analyzers` map
- [ ] Verify `RegisterThroughputAnalyzerQueries()` is called in `NewEngine()` (should be done by ENGINE PR)
- [ ] Add config schema documentation (ConfigMap example)
- [ ] Add conflict resolution logging (when RC > 0 and SC > 0 simultaneously)

### Tests
- [ ] E2E Test 1: TA-only scale-up
- [ ] E2E Test 2: TA-only scale-down
- [ ] E2E Test 3: Dual-analyzer scale-up
- [ ] E2E Test 4: Dual-analyzer scale-down blocked
- [ ] E2E Test 5a: Cold-start 0→1 (saturation-driven)
- [ ] E2E Test 5b: Cold-start 1→2 (TA-driven)
- [ ] E2E Test 6: Tier-2 fallback
- [ ] E2E Test 7: Shape change clears window
- [ ] E2E Test 8: Pending replicas suppress scale-up
- [ ] E2E Test 10: Role-aware aggregation

### Documentation
- [ ] Update `docs/user-guide/throughput-analyzer.md` with config examples
- [ ] Add observability section (metrics, logs, Grafana panels)
- [ ] Add rollback plan
- [ ] Add upgrade path (saturation-only → dual-analyzer)
- [ ] Update CHANGELOG.md

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ENGINE PR not ready | Medium | High | **Blocker** — verify ENGINE PR status before starting |
| TA and saturation conflict | Low | Medium | Add conflict resolution logging |
| TA produces wrong signal | Low | High | Comprehensive e2e tests + canary rollout |
| Config schema unclear | Medium | Low | Add config documentation section |
| No rollback plan | Low | Medium | Add rollback section to plan |

---

## Questions for PR Author

1. **ENGINE PR Status:** What is the status of the ENGINE multi-analyzer PR? Is it merged, in progress, or not started?
2. **Registration Ownership:** Should ENGINE PR add the TA registration as an example, or should PR-5 own it?
3. **Config Defaults:** What happens when the `analyzers` list is empty? Does saturation run by default?
4. **Conflict Logging:** Should we add INFO-level logging when analyzers disagree, or is DEBUG sufficient?
5. **E2E Test Scope:** Should PR-5 include queue demand tests, or defer until SchedulerQueue is wired?
6. **Rollout Strategy:** Is there a preferred canary namespace for initial TA deployment?

---

## Final Recommendation

**APPROVE PLAN** after addressing:

### Blockers (Must Fix Before Implementation)
1. Clarify ENGINE PR status and dependency
2. Document config schema (how users enable/disable TA)
3. Add rollback plan

### Important (Should Fix Before Merge)
4. Add observability section (metrics, logs)
5. Add upgrade path documentation
6. Expand e2e test coverage (tests 6-10)
7. Add conflict resolution logging

### Nice-to-Have (Can Defer)
8. Grafana dashboard examples
9. Canary rollout guide

---

**End of Review**
