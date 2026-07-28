---
type: review
pr: 1392
title: "Bug fix: Calculate missing V1 saturation utilization metric"
author: shuynh2017
status: FINAL — comment posted 2026-07-13
date: 2026-07-13
---

# PR #1392 Review — V1 saturation utilization fix

**PR:** [#1392](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1392)
**Author:** shuynh2017
**Base:** main | **Head:** `shuynh_v1_saturation_util_fix` | **State:** open
**Scale:** 5 files, +170/−1 lines, 1 commit (`dc2c1ffe`)
**CI:** all green (lint-and-test, e2e-tests-smoke, e2e-tests-smoke-keda, DCO, etc.)
**Reviewed:** 2026-07-13

---

## What it does

V1's saturation engine never populated `decision.Utilization`, so `wva_saturation_utilization`
always read 0 for V1 variants — visible in the PR's own "before" screenshot (scaling happens, but
the Saturation Utilization panel shows 0). Fix: `analyzeVariant` (`internal/saturation/analyzer.go`)
now accumulates `totalKvUsage` across all replica metrics and computes
`AvgKvCacheUsage = totalKvUsage / len(metrics)`, a new field on `VariantSaturationAnalysis`
(`internal/interfaces/saturation_analyzer.go`). `convertSaturationTargetsToDecisions`
(`internal/engines/saturation/engine.go`) wires it into `decision.Utilization`.

This is the V1 analog of #1368 (`e7a9ca1e`, merged 2026-07-03), which fixed the identical bug
shape on the V2 path (`buildDecisionsWithOptimizer` never copied `Utilization` onto the decision).

---

## Confirmed correct

- The fix matches the formula already specified in `VariantDecision.Utilization`'s own doc
  comment (`internal/interfaces/saturation_analyzer.go:244-252`): "V1: mean of per-replica
  KvCacheUsage fractions." The PR implements the spec that was already written down — no design
  judgment call needed here.
- `AvgKvCacheUsage` averages over *all* replicas (saturated or not), while the neighboring
  `AvgSpareKvCapacity` averages only over *non-saturated* replicas. Checked this isn't an
  inconsistency: they're different metrics serving different consumers — `Utilization` is the
  "current overall load" figure for the observability gauge (matches V1's per-replica threshold
  check, which looks at all replicas), while `AvgSpareKvCapacity` is "headroom among replicas that
  have any," used by the limiter, where saturated replicas contributing 0 spare would just dilute
  the signal. Both match their respective pre-existing field comments.
- Audited every path that sets `Utilization` / calls `RecordSaturationMetrics` across the whole
  engine (V1, both V2 optimizers, scale-from-zero) to confirm this PR doesn't leave a sibling gap.
  V2 (fixed by #1368) has complete per-variant coverage (`aggregateByVariant` iterates all
  `variantStates`, no silent map-miss). Scale-from-zero correctly never emits this gauge (uses a
  different actuator with no `RecordSaturationMetrics`, and there's no live KV usage to report at
  zero replicas anyway). One pre-existing, out-of-scope gap found (throughput-only-driven models
  never get this gauge at all, by design per #1368's own commit message) — filed as a backlog note
  for TA forward-plan (I-26 candidate), not a finding against this PR.
- CI green, no logic touches outside the stated scope.

---

## Findings

### D1 — Doc example now shows the exact bug this PR fixes

`docs/developer-guide/prometheus.md:511-542` documents `wva_saturation_utilization`. The formula
description (line 513) is accurate and needs no change. But the example JSON payload (line 539)
shows `"value": [1778846184.925, "0"]` — a live capture from a cluster hitting the pre-fix bug.
Post-fix, a reader who doesn't know the history will read that "0" as a normal example value
rather than a symptom of the bug this PR resolves. Not something the PR broke (doc predates it),
but since the PR is specifically "this used to read 0, now it doesn't," it's a natural place to
also swap in a realistic non-zero example.

### D2 — (out of scope, found in passing) stale metric name in the same doc

`docs/developer-guide/prometheus.md:941` PromQL example still references
`wva_kv_cache_tokens_total`, which #1368 renamed to `wva_kv_cache_tokens_capacity`. Unrelated to
#1392 — leftover from a different PR. Not raising against this PR; noting so it doesn't get lost.

### T1 — New tests use exact float equality on computed values

Both new test files compare a runtime `float64` division result with `!=` against a literal
(`internal/saturation/analyzer_test.go`'s `TestAnalyzeVariant_AvgKvCacheUsage`;
`internal/engines/saturation/engine_v1_utilization_test.go`). Verified directly: the chosen test
values (0.30+0.60+0.90)/3, (0.85+0.40+0.55)/3, etc. happen to round-trip to the same float64 bit
pattern as the literal `0.60`, so the tests pass — but that's a coincidence of the specific inputs
chosen, not a property of the code under test. The pattern is fragile as a template for future
float tests in this area.

Neither file currently imports testify (both plain `"testing"`), so the fix that matches existing
style is a tolerance check rather than pulling in an assertion library:

```go
const epsilon = 1e-9
if diff := analysis.AvgKvCacheUsage - tt.expectedAvgKvUsage; diff > epsilon || diff < -epsilon {
    t.Errorf("expected AvgKvCacheUsage=%.2f, got %.2f", tt.expectedAvgKvUsage, analysis.AvgKvCacheUsage)
}
```

(testify's `assert.InDelta` is already a dependency and used elsewhere in
`internal/engines/saturation`, e.g. `event_deduplication_test.go` — a legitimate alternative if
the author prefers it, but it would be a new import into files that are currently stdlib-only.)

---

## PR Comment Draft

> **Posted** — [issuecomment-4958365615](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1392#issuecomment-4958365615) — 2026-07-13
> **Approved** — Dean formally approved the PR on GitHub — 2026-07-13

---

Nice fix — matches the formula already documented on `VariantDecision.Utilization`. Two
non-blocking notes:

**1. (non-blocking) Doc example now shows the exact bug this fixes**

`docs/developer-guide/prometheus.md`'s example for `wva_saturation_utilization` shows
`"value": [..., "0"]` — looks captured while hitting this bug. Worth swapping in a non-zero
example now that it's fixed.

**2. (non-blocking) New tests use exact float equality**

`TestAnalyzeVariant_AvgKvCacheUsage` and `engine_v1_utilization_test.go` compare a computed
average with `!=` against a literal. Passes here by luck of float rounding — an epsilon check
(`math.Abs(got-want) > 1e-9`) would be safer for future additions to this test.

---

## Backlog (not for this PR)

- **I-26 candidate** (`TA-forward-plan.md`): `wva_saturation_utilization` and sibling gauges never
  fire for throughput-only-driven models (both V2 optimizers skip when no saturation-analyzer
  entry exists). Pre-existing, acknowledged in #1368's commit message, not a regression. Handoff
  filed: `session/handoffs/plan__ta-utilization-gauge-gap.md`.
