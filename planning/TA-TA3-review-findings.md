# TA Code Review Findings

**Branch reviewed:** TA3 (HEAD `44a96f0`, covers PR-1 through PR-5)  
**Reviewed:** 2026-05-07  
**Reviewer:** Dean H Lorenz (assisted by Claude)  
**Scope:** `internal/engines/analyzers/throughput/` — decode-only phase (μ_dec vs λ_dec)

---

## Summary

The implementation correctly encodes all algorithms from TA-supply.md, TA-demand.md, and
TA-PR4-plan.md. Supply, demand, OLS fit, queue demand, and RC/SC aggregation all match
the design documents. Two bugs and several documentation gaps were identified.

---

## Bugs (must fix before merge)

### Bug 1 — `computeLocalDemand` violates the λ_dec = 0 invariant when OL ≈ 0

**File:** `analyzer.go`, function `computeLocalDemand`

**Root cause:** The k*-based demand formula

```
λ_local = Σ_r (k_r* × KV_max_r / KVreq) / ITL(k_r*)
```

is derived from Little's Law: `N_dec(k*) / ITL(k*) = λ_req × OL = λ_dec`. The
identity holds only in the **decode-dominated regime** (N_pre ≈ 1, TA-supply.md §3.1),
which requires sufficiently long OL (the doc notes this assumption breaks below
OL ≈ 100–150).

When OL ≈ 0 — for example, a prefill-role pod in a P/D disaggregated cluster that
produces no output tokens — the entire KV usage is from prefill requests, not decode.
The formula then misinterprets prefill KV footprint as decode concurrency and returns a
large spurious demand value instead of the correct λ_dec = 0.

The EPP and vLLM fallback paths are unaffected: they multiply by `AvgOutputTokens`
directly and naturally return 0 when OL = 0. Only `computeLocalDemand` lacks this guard.

**Fix:** Add a new constant `DefaultMinDecodeOLForLocalDemand = 20.0` to `constants.go`
and guard the function on `shape.AvgOutputTokens`:

```go
// constants.go — add after DefaultQueueDrainFactor:

// DefaultMinDecodeOLForLocalDemand is the minimum AvgOutputTokens required before
// the k*-based local demand estimator is applied.
//
// The estimator derives λ_dec = N_dec(k*) / ITL(k*) where N_dec is approximated
// from KV utilization as k* × KV_max / KVreq. This is only valid in the
// decode-dominated regime (N_pre ≈ 1, TA-supply.md §3.1), which requires
// sufficiently long OL. When OL ≈ 0 (e.g., prefill-role pods in a P/D
// disaggregated cluster), all KV usage is from prefill rather than decode;
// the formula then produces a spurious non-zero signal instead of the correct
// λ_dec = 0. A floor of 20 tokens ensures the decode-dominated assumption holds
// and preserves the invariant λ_dec = λ_req × OL → 0 when OL → 0.
DefaultMinDecodeOLForLocalDemand = 20.0
```

```go
// analyzer.go — computeLocalDemand, replace the opening guard:

func computeLocalDemand(metrics []interfaces.ReplicaMetrics, shape WorkloadShape, model ITLModel) float64 {
    if shape.KVreq <= 0 || shape.AvgOutputTokens <= DefaultMinDecodeOLForLocalDemand {
        return 0
    }
    ...
}
```

**Test to add** in `analyzer_test.go`, inside the existing
`"Analyze — k*-based local demand (no EPP)"` Describe block:

```go
It("emits zero RequiredCapacity when OL is below the decode-dominated threshold", func() {
    injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, 5.0 /*OL*/, prefix, kvMax, A, B, kValues)

    // OL=5 < DefaultMinDecodeOLForLocalDemand → local demand formula must not fire.
    replica := interfaces.ReplicaMetrics{
        VariantName:           "v1",
        KvCacheUsage:          0.95,
        KvUsageInstant:        0.95,
        AvgITL:                A*0.95 + B,
        AvgInputTokens:        il,
        AvgOutputTokens:       5.0,
        PrefixCacheHitRate:    prefix,
        TotalKvCapacityTokens: kvMax,
        // ArrivalRate=0, VLLMRequestRate=0 → only local demand path available.
    }
    result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
        ModelID: modelID, Namespace: namespace,
        ReplicaMetrics: []interfaces.ReplicaMetrics{replica},
    })
    Expect(err).NotTo(HaveOccurred())
    Expect(result.RequiredCapacity).To(Equal(0.0))
    Expect(result.SpareCapacity).To(Equal(0.0))
})
```

Note: `injectWindowObs` injects observations with OL=5; the shape tracker will store
that OL, so the shape passed to `computeLocalDemand` correctly has `AvgOutputTokens=5`.

---

### Bug 2 — Sanity check skips the entire variant when any single pod fails

**File:** `analyzer.go`, function `Observe`

**Root cause:** `CheckModelMetrics` aggregates issues across all pods of a variant and
`Observe` skips the entire variant when `!report.OK()`. A single cold-start replica
with ITL=0 (triggering `SanityIssueITLNonPositive`) blocks all healthy pods in that
variant from contributing shape observations and window entries that cycle.

`ObservationWindow.Add` already filters bad k and ITL per-point. The all-or-nothing
skip at the variant level is therefore over-conservative.

**Correct behavior by issue type:**

| Issue | Correct scope | Notes |
|-------|---------------|-------|
| `SanityIssueNoReplicas` | Variant-level skip | Nothing to process |
| `SanityIssueStaleMetrics` | Pod-level: exclude from shape averaging and window | Stale IL/OL may still be valid but conservative to exclude |
| `SanityIssueMissingKV` | Pod-level: exclude from supply calc; still usable for shape | No KV_max → can't compute N_dec_sat |
| `SanityIssueKVOutOfRange` | Pod-level: `ObservationWindow.Add` already rejects; exclude from shape | |
| `SanityIssueITLNonPositive` | Pod-level: `ObservationWindow.Add` already rejects; exclude from shape | Common during cold start |
| `SanityIssueMissingShape` | Pod-level: `averageShapeMetrics` already skips IL/OL ≤ 0 | Defensive |

**Fix outline:**

1. Change `CheckModelMetrics` to return a `map[string]SanityReport` (per-pod) rather
   than a single variant-level report. Or keep the variant-level aggregate for logging
   but add a per-pod predicate.

2. In `Observe`, replace the `if !report.OK() { continue }` block with:
   - Still skip on `SanityIssueNoReplicas` (no pods).
   - Log the aggregate report for observability.
   - Pass a per-pod healthy predicate into `averageShapeMetrics` so stale/bad pods
     are excluded from IL/OL averaging.
   - Let `ObservationWindow.Add` continue handling per-observation k/ITL filtering.

3. `averageShapeMetrics` should accept a filter func (or an explicit exclude-list)
   to skip pods that are stale or have missing shape. It already skips pods with
   IL ≤ 0 / OL ≤ 0; the additional cases are stale metrics and missing KV.

**Test to add:** A variant with mixed-health pods (one stale, rest healthy) should
still produce shape observations and window entries from the healthy pods.

---

## Documentation gaps (comment-only fixes, no logic change)

### Doc 1 — `perReplicaSupply` denominator counts only valid-KV replicas

**File:** `analyzer.go`, `computeVariantSupply` and the `totalAnticipated` accumulation
in `Analyze`.

`perReplicaSupply = sum / n` where `n` counts only replicas with `TotalKvCapacityTokens > 0`.
But `totalAnticipated += float64(len(variantMetrics)+pending) * perReplicaSupply`
uses all current replicas (including KV=0 ones starting up).

This is **intentional**: a pod that hasn't reported KV capacity yet still counts against
anticipated supply to suppress spurious scale-up while a scale-out is in progress.
Matches the behaviour of saturation_v2. Should be documented with a comment at the
`totalAnticipated` accumulation line.

**Suggested comment:**
```go
// len(variantMetrics) intentionally includes replicas with KV=0 (still booting).
// Counting them in anticipated supply suppresses RC while a scale-out is in progress,
// consistent with saturation_v2. perReplicaSupply is the mean over replicas that
// already reported capacity; new replicas are assumed to reach the same level.
totalAnticipated += float64(len(variantMetrics)+pending) * perReplicaSupply
```

### Doc 2 — Model-level RC includes prefill role demand

**File:** `analyzer.go`, `Analyze`.

The top-level `RequiredCapacity` in `AnalyzerResult` is computed from model-level totals
that include all variants regardless of role. The prefill RC suppression in
`aggregateRoleCapacities` applies only to the `RoleCapacities` map.

In practice this is harmless after Bug 1 is fixed: the EPP and vLLM demand paths
multiply by `AvgOutputTokens` (≈ 0 for prefill pods), and `computeLocalDemand` is now
gated on `AvgOutputTokens > DefaultMinDecodeOLForLocalDemand`. So prefill demand
contribution to totalDemand is effectively zero.

Should be noted in a comment near the RC/SC computation or in the `Analyze` godoc.

---

## Low priority / nice to have

### NTH 1 — Log the fitted A value on Tier-1 OLS failure

**File:** `analyzer.go`, `resolveITLModel`

When `FitITLModel` returns `(zero, false)` (A ≤ 0 from the OLS fit), the existing log
says "tier-1 OLS fit failed, trying tier-2" but does not show the computed A. Knowing
the fitted A helps operators diagnose persistently noisy observation windows.

The simplest approach is to surface A from inside `FitITLModel`: either return it on
failure (change signature to `(ITLModel, float64, bool)`) or add a separate
`FitITLModelDebug` that returns the raw coefficients before rejection.

### NTH 2 — OLS residual / confidence in VariantState

**File:** `types.go`, `ThroughputVariantState`; `itl_model.go`, `FitITLModel`

`FitITLModel` already has all the data needed to compute the OLS residual
`σ² = Σ(ITL_i − A·k_i − B)² / (n−2)`. Exposing this in `ThroughputVariantState`
(e.g., as `ITLModelResidualSec`) would let operators detect when the linear ITL model
is a poor fit (high residual → possible non-linearity or data contamination).
This was discussed during review; deferred to a future observability PR.

### NTH 3 — k_sat from EPP (long-term)

`DefaultKSat = 0.85` is intentionally aligned with `DefaultScaleUpThreshold` in
saturation_v2. The long-term target is to receive k_sat from the EPP directly so all
components (EPP, saturation analyzer, throughput analyzer) share a single configured
value. Tracked as a TODO in `constants.go`.

---

## Items confirmed as correct (not issues)

- `DefaultKSat = 0.85` and `DefaultMaxObservableK = 0.85` coinciding: the linear ITL
  model holds empirically to k = 0.85 (TA-supply.md §10.2). Evaluating supply at k_sat
  gives the maximal stable decode rate, which is the correct quantity. Aligning with
  saturation_v2 is intentional.

- `lastFittedB` / `hasFittedB` carrying B across shape resets (design decision #7):
  implemented in commit `7733471`, verified present in HEAD. ✅

- Tier-3 knowledge store not wired: intentional, documented in PR-4-plan. ✅

- `resolveITLModel` extra logging params: already corrected in TA3 (`7733471`). ✅
