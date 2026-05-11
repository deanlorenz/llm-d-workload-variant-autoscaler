# PR #1051 Code Review

**PR:** [collector/registration: register throughput analyzer queries (PR-1, PR-2)](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1051)  
**Head SHA:** `900c94c`  
**Reviewed:** 2026-05-11  
**Reviewer:** Claude Code (go-reviewer, test-analyzer, security-auditor, go-reuse-checker)

---

## Summary

Go code quality: **no issues**. Three findings across test coverage, security, and code reuse.

---

## Test Coverage

### TC-1 — New collector processing blocks have no unit tests [confidence 92]

**File:** `internal/collector/replica_metrics.go` lines 489–549

The three new processing blocks (`QueryGenerationTokenRate`, `QueryKvUsageInstant`, `QueryVLLMRequestRate`) are not covered by any test. The existing `replica_metrics_test.go` exercises only Prometheus observation counters; it has no tests that drive `Refresh()` results through the processing loop and assert `ReplicaMetrics` fields are populated. This is a pre-existing gap for older blocks, but those blocks were not introduced by this PR.

**Suggested tests** in `internal/collector/replica_metrics_test.go`:
- Happy path: inject a `MetricResult` with `{value: 250.0, labels: {"pod": "pod-0"}}` for each query; assert `GenerationTokenRate`, `KvUsageInstant`, and `VLLMRequestRate` are populated on the returned `ReplicaMetrics`.
- `pod_name` fallback: labels carry only `{"pod_name": "pod-0"}` (no `"pod"` key); assert field is still populated (see TC-3).
- Invalid values: assert NaN, `+Inf`, and negative inputs are rejected (see TC-2).

---

### TC-2 — NaN / Inf / out-of-range filtering is untested [confidence 88]

**File:** `internal/collector/replica_metrics.go` lines 502, 523, 544

Each new block guards against NaN, Inf, and negative values before storing. `KvUsageInstant` additionally rejects values > 1.0 (correct, since it's a fraction). None of these filter paths are tested. A NaN or > 1.0 `KvUsageInstant` silently propagating to the ITL model calibration (`k*`) would produce incorrect OLS points downstream.

**Suggested tests:** pass `math.NaN()`, `math.Inf(1)`, `-0.5`, and (for `KvUsageInstant`) `1.01`; assert the corresponding field remains `0.0` on the returned struct.

---

### TC-3 — `pod_name` label fallback is untested [confidence 85]

**File:** `internal/collector/replica_metrics.go` lines 493–496, 513–516, 534–537

The `pod` → `pod_name` fallback is documented at the package level (added in this PR) but is unexercised by any test for any block — pre-existing gap, but the three new blocks are this PR's contribution. A scrape config that emits `pod_name` instead of `pod` will produce zero-valued TA fields with no error or warning.

**Suggested test:** pass a `MetricResult` with only `{"pod_name": "pod-0"}` and assert the field is populated.

---

## Security

### SEC-1 — `EscapePromQLValue` does not escape `\n` / `\t` [confidence 82]

**File:** `internal/collector/source/query_template.go` (existing file, not changed by this PR — but the three new templates use the same substitution path)

`EscapePromQLValue` escapes `"` and `\`, which prevents label-value injection. However it does not escape raw newline or tab characters. A `modelID` containing a newline terminates the PromQL double-quoted string early, producing a malformed query. Prometheus returns a parse error; the collector logs it and returns zero metrics for that model. An attacker who can write `VariantAutoscaling` objects can trigger a targeted metrics-collection DoS for a chosen model.

**Fix options (either):**
1. Add newline/tab escaping to `EscapePromQLValue`: replace `\n` → `\\n` and `\t` → `\\t`.
2. Add `+kubebuilder:validation:Pattern=^[a-zA-Z0-9._/:@-]+$` to the `ModelID` field in the CRD, rejecting control characters at admission time. This is the better long-term fix.

> Note: this is a pre-existing issue in the existing templates; this PR introduces three additional templates that hit the same code path.

---

## Library / Code Reuse

### RU-1 — Pod-label fallback + nil-guard pattern duplicated 12× in one function [confidence 92]

**File:** `internal/collector/replica_metrics.go` lines 488–549

This PR adds three more copies of the 8-line pod-extraction idiom that already appears nine times in `CollectReplicaMetrics`. The PR also adds a package-level doc comment explaining the pattern — the right instinct, but the natural follow-on is extraction to a helper. No external library can supply this; it is an intra-project refactor opportunity.

**Suggested helpers:**

```go
func podNameFromLabels(labels map[string]string) string {
    if name := labels["pod"]; name != "" {
        return name
    }
    return labels["pod_name"]
}
```

With this, each block's preamble shrinks from 8 lines to 3. A future block has one correct place to look rather than copying from a neighbor.

> This is a refactor finding — the new code is not wrong. Defer to a post-TA cleanup PR if preferred (see [collector deferred improvements](../session/../planning/../../../plans/session/CURRENT.md) note in memory).

---

## Items confirmed correct

- All exported identifiers carry doc comments starting with the identifier name ✅
- `VLLM` all-caps matches codebase convention (`VLLMEngineParams`, `ParseVLLMArgs`) ✅
- `ctrl.Log` used for structured logging ✅
- Error message updated from `"failed to refresh saturation metrics"` → `"failed to refresh replica metrics"` ✅
- `KvUsageInstant` upper-bound clamp (`<= 1`) consistent with `QueryPrefixCacheHitRate` block ✅
- PromQL label-value escaping: `EscapePromQLValue` covers `"` and `\`; sufficient for the injection class (SEC-1 is a control-character / DoS class) ✅

---

## Checklist before merge

- [ ] TC-1: Add happy-path tests for new `ReplicaMetrics` field population in `replica_metrics_test.go`
- [ ] TC-2: Add invalid-value filter tests (NaN, Inf, negative, `KvUsageInstant > 1.0`)
- [ ] TC-3: Add `pod_name`-only label fallback test
- [ ] SEC-1: Fix `EscapePromQLValue` or add `ModelID` pattern validation (can be separate PR since pre-existing)
- [ ] RU-1: Extract `podNameFromLabels` helper (can defer to post-TA cleanup PR)
