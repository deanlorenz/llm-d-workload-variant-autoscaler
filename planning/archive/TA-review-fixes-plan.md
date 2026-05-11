# TA Review Fixes Plan

**Branch:** TA3  
**Scope:** `internal/engines/analyzers/throughput/`  
**Created:** 2026-05-10  
**Source:** TA-TA3-review-findings.md (Bug 1, Bug 2, Doc 1, Doc 2) + CURRENT.md GPS window-reset note  

---

## Overview

Five targeted fixes, each in its own commit. No logic changes to Fix 4 and Fix 5 (comment-only).

| # | Area | Type | File(s) |
|---|------|------|---------|
| 1 | `computeLocalDemand` OL guard | Logic + test | `constants.go`, `analyzer.go`, `analyzer_test.go` |
| 2 | Per-pod sanity filter | Logic + test | `analyzer.go`, `sanity.go`, `analyzer_test.go` |
| 3 | GPS mismatch clears window after N repeated cycles | Logic + test | `constants.go`, `analyzer.go`, `analyzer_test.go` |
| 4 | Comment: `totalAnticipated` KV=0 intent | Comment only | `analyzer.go` |
| 5 | Comment: prefill RC inclusion is harmless | Comment only | `analyzer.go` |

---

## Fix 1 — `computeLocalDemand` OL guard

**Problem:** The k*-based local demand formula  
`λ_local = Σ_r (k_r* × KV_max_r / KVreq) / ITL(k_r*)`  
is only valid in the decode-dominated regime (N_pre ≈ 1), which requires sufficiently long output length. When OL ≈ 0 (e.g., prefill-role pods in P/D disaggregation), the KV footprint is from prefill requests and the formula returns spurious non-zero demand. The EPP and vLLM paths are unaffected — they multiply by `AvgOutputTokens` and naturally return 0.

**Constant** (`constants.go`):
```go
// DefaultMinDecodeOLForLocalDemand is the minimum AvgOutputTokens required
// before the k*-based local demand estimator is applied. The estimator derives
// λ_dec = N_dec(k*) / ITL(k*) where N_dec is approximated from KV utilization
// as k* × KV_max / KVreq. This approximation only holds in the decode-dominated
// regime (N_pre ≈ 1, TA-supply.md §3.1), which requires sufficiently long OL.
// When OL ≈ 0, KV usage is from prefill rather than decode; the formula then
// produces spurious non-zero demand instead of the correct λ_dec = 0.
DefaultMinDecodeOLForLocalDemand = 20.0
```

**Guard** (`analyzer.go`, `computeLocalDemand`, replace existing `if shape.KVreq <= 0` guard):
```go
func computeLocalDemand(metrics []interfaces.ReplicaMetrics, shape WorkloadShape, model ITLModel) float64 {
    if shape.KVreq <= 0 || shape.AvgOutputTokens <= DefaultMinDecodeOLForLocalDemand {
        return 0
    }
    ...
}
```

**Test** (`analyzer_test.go`, inside `"Analyze — k*-based local demand (no EPP)"` Describe block):
```
It("emits zero RequiredCapacity when OL is below the decode-dominated threshold")
- Setup: OL=5.0 (< 20), KV=0.95, no ArrivalRate, no VLLMRequestRate
- Expect: RequiredCapacity == 0, SpareCapacity == 0
```

**Commit message:** `fix(throughput): guard computeLocalDemand against low OL (decode-dominated invariant)`

---

## Fix 2 — Per-pod sanity filter

**Problem:** `Observe()` calls `CheckModelMetrics()` which aggregates issues across all pods of a variant. When `!report.OK()`, the entire variant is skipped. A single cold-start replica with ITL=0 (triggering `SanityIssueITLNonPositive`) blocks all healthy pods from contributing shape observations and window entries.

**Building block available:** `checkReplicaMetrics(m interfaces.ReplicaMetrics) []SanityIssue` already exists in `sanity.go` as a per-pod checker.

**Correct semantics per issue type:**
- `SanityIssueNoReplicas` — skip variant (nothing to process)
- All other issues — exclude the affected pod from shape averaging; let healthy pods proceed

**Changes:**

1. Add `HasIssue(issue SanityIssue) bool` helper to `SanityReport` in `sanity.go`:
```go
func (r SanityReport) HasIssue(issue SanityIssue) bool {
    for _, i := range r.Issues {
        if i == issue {
            return true
        }
    }
    return false
}
```

2. Add `filterHealthyForShape(metrics []interfaces.ReplicaMetrics) []interfaces.ReplicaMetrics` helper in `analyzer.go`:
```go
func filterHealthyForShape(metrics []interfaces.ReplicaMetrics) []interfaces.ReplicaMetrics {
    healthy := make([]interfaces.ReplicaMetrics, 0, len(metrics))
    for _, m := range metrics {
        if len(checkReplicaMetrics(m)) == 0 {
            healthy = append(healthy, m)
        }
    }
    return healthy
}
```

3. In `Observe()`, change the variant-level skip to only hard-skip on `SanityIssueNoReplicas`; for all other issues, proceed with filtered metrics:
```go
if report.HasIssue(SanityIssueNoReplicas) {
    ctrl.Log.V(logging.DEBUG).Info("throughput analyzer: no replicas, skipping variant", ...)
    continue
}
if !report.OK() {
    ctrl.Log.V(logging.DEBUG).Info("throughput analyzer: sanity issues detected, some pods excluded",
        "namespace", namespace, "modelID", modelID, "variant", variantName,
        "issues", report.Issues, "affectedPods", report.AffectedPods,
    )
}
healthyMetrics := filterHealthyForShape(variantMetrics)
if len(healthyMetrics) == 0 {
    continue
}
il, ol, hitRate := averageShapeMetrics(healthyMetrics)
// ... shape tracker, then:
for _, m := range healthyMetrics {
    state.observationWindow.Add(m.KvUsageInstant, m.AvgITL, now)
}
```

**Test** (`analyzer_test.go`):
```
It("still observes shape and window entries when one pod has ITL=0 (cold start)")
- Variant with 2 replicas: one healthy (ITL>0, k>0), one with ITL=0
- After Observe: window has entries from the healthy pod only (Len()==1)
- State is non-zero (shape present, window not empty)
```

**Commit message:** `fix(throughput): exclude unhealthy pods per-replica instead of skipping entire variant`

---

## Fix 3 — GPS mismatch clears observation window after N repeated cycles

**Problem:** `checkVariantGPSMismatch` suppresses SpareCapacity but does not clear the observation window. Bad observations can accumulate for the full window age (up to 30 min), keeping SC suppressed indefinitely — a "calibration lock" state.

**Why not clear on every mismatch:** A single bad point-in-time GPS reading (transient noise) would wipe a healthy window.

**Mechanism:** Track `consecutiveGPSMismatches int` per variant in `variantState`. Clear the window when the count reaches `DefaultGPSMismatchClearThreshold`. Reset to zero on a clean cycle.

**Counter lifetime invariant:** `consecutiveGPSMismatches` must always be reset to 0 whenever `observationWindow.Clear()` is called, regardless of the caller. This ensures the counter is always bound to the current window's lifetime — mismatches from a previous window must not carry over after the window has been replaced.

There are two `observationWindow.Clear()` call sites:
1. `Observe()` shape-change path — **add `state.consecutiveGPSMismatches = 0` here**
2. `Analyze()` GPS threshold clear — reset to 0 after clearing (natural; we just cleared)

**Constant** (`constants.go`):
```go
// DefaultGPSMismatchClearThreshold is the number of consecutive reconcile cycles
// with a GPS mismatch before the observation window is cleared for recalibration.
// Requiring N consecutive mismatches filters transient GPS noise while still
// breaking persistent calibration lock. The counter resets to zero whenever the
// window is cleared (shape change or threshold reached) so it is always bound to
// the current window's lifetime.
DefaultGPSMismatchClearThreshold = 3
```

**State field** (`analyzer.go`, `variantState`):
```go
// consecutiveGPSMismatches counts how many consecutive Analyze cycles have
// produced a GPS mismatch for this variant. Cleared alongside observationWindow
// so it is always bound to the current window lifetime.
consecutiveGPSMismatches int
```

**`Observe()` shape-change block** (add reset alongside window clear):
```go
if changed {
    ctrl.Log.V(logging.DEBUG).Info(...)
    state.observationWindow.Clear()
    state.consecutiveGPSMismatches = 0
}
```

**Call site in `Analyze()`** (replace existing GPS mismatch block):
```go
if checkVariantGPSMismatch(variantMetrics, shape, model, input.Namespace, input.ModelID, variantName) {
    anyGPSMismatch = true
    state.consecutiveGPSMismatches++
    if state.consecutiveGPSMismatches >= DefaultGPSMismatchClearThreshold {
        state.observationWindow.Clear()
        state.consecutiveGPSMismatches = 0
        ctrl.Log.Info("throughput analyzer: GPS mismatch persisted, clearing observation window for recalibration",
            "namespace", input.Namespace, "modelID", input.ModelID, "variant", variantName,
            "threshold", DefaultGPSMismatchClearThreshold,
        )
    }
} else {
    state.consecutiveGPSMismatches = 0
}
```

Note: `lastFittedB` / `hasFittedB` are NOT cleared — same as the shape-change window clear.

Also update the log message inside `checkVariantGPSMismatch` — remove "suppressing SpareCapacity" (that is the call site's responsibility):
```go
// Old: ctrl.Log.Info("throughput analyzer: GPS mismatch, suppressing SpareCapacity", ...)
// New: ctrl.Log.Info("throughput analyzer: GPS mismatch detected", ...)
```

**Tests** (`analyzer_test.go`):
```
It("does not clear the observation window on a single GPS mismatch cycle")
- Pre-load window, inject mismatch once
- window.Len() still > 0

It("clears the observation window after N consecutive GPS mismatch cycles")
- Pre-load window (Tier-1 Ready), record lastFittedB
- Inject mismatch for DefaultGPSMismatchClearThreshold consecutive Analyze calls
- After Nth call: window.Len() == 0; lastFittedB preserved (hasFittedB true)

It("resets the consecutive counter on a clean cycle, requiring N mismatches again")
- Inject 2 mismatches, then 1 clean cycle (counter resets to 0), then 2 more mismatches
- Window intact (only 2 consecutive since last reset, < 3 threshold)

It("resets the consecutive counter when the window is cleared by a shape change")
- Inject 2 mismatches, then trigger shape change in Observe()
- Counter is 0; window was cleared by shape change; 1 further mismatch does not clear again
```

**Commit message:** `fix(throughput): clear observation window after repeated GPS mismatches to break calibration lock`

---

## Fix 4 — Comment: `totalAnticipated` counts KV=0 replicas intentionally

**File:** `analyzer.go`, `Analyze()`, immediately before `totalAnticipated +=` line.

```go
// len(variantMetrics) intentionally includes replicas with KV=0 (still booting).
// Counting them in anticipated supply suppresses RC while a scale-out is in progress,
// consistent with saturation_v2. perReplicaSupply is the mean over replicas that
// already reported capacity; new replicas are assumed to reach the same level.
totalAnticipated += float64(len(variantMetrics)+pending) * perReplicaSupply
```

**Commit message:** `docs(throughput): clarify that totalAnticipated includes booting replicas with KV=0`

---

## Fix 5 — Comment: prefill RC contribution is effectively zero

**File:** `analyzer.go`, `Analyze()`, immediately before the `requiredCapacity` / `spareCapacity` block.

```go
// RequiredCapacity is computed from model-level totals that include all roles.
// Prefill-role demand contribution is effectively zero after the OL guard in
// computeLocalDemand: the EPP and vLLM demand paths multiply by AvgOutputTokens
// (≈ 0 for prefill pods), and computeLocalDemand is gated on
// AvgOutputTokens > DefaultMinDecodeOLForLocalDemand. Per-role RC suppression
// is applied in RoleCapacities via aggregateRoleCapacities.
```

**Commit message:** `docs(throughput): note that prefill role RC contribution is negligible after OL guard`

---

## Deferred (not in this batch)

**Bob review 1.3 — staleness check in `computeDemand`**: Defer ArrivalRate staleness detection to a later observability PR. Track in CURRENT.md "Issues to Open".

---

## Test count

Current: 133 specs.

| Fix | Specs added | Running total |
|-----|-------------|---------------|
| 1   | 1           | 134           |
| 2   | 1           | 135           |
| 3   | 4           | 139           |
| 4   | 0           | 139           |
| 5   | 0           | 139           |

Expected total after all fixes: **139 specs**.

---

## Commit order

1. Fix 1 — OL guard (standalone)
2. Fix 2 — per-pod sanity (standalone)
3. Fix 3 — GPS window reset after N cycles (standalone)
4. Fix 4 — comment (order-independent)
5. Fix 5 — comment (logically after Fix 1; references the OL guard)
