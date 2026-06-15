# WVA Saturation Cycle Summary Log — Task Plan

**Branch:** new branch off `main` (e.g. `wva-saturation-cycle-log`)
**Type:** Type 3 task plan
**Scope:** Logging only. No behavioral change. No interface change that affects callers.
**Status:** Ready for implementation

---

## What this PR adds

One structured `logger.Info("saturation cycle summary", ...)` line per model per
reconcile cycle, emitted after the optimizer has produced decisions. Single log
entry; all per-variant fields in one place. Permanent instrument — keep schema
stable.

**Nothing else.** No new metrics, no config changes, no behavioral logic.

---

## Log line spec

Message: `"saturation cycle summary"` (fixed string — grep target for benchmark tooling).

**Model-level fields:**

| Key | Type | Source |
|---|---|---|
| `model` | string | `"namespace/modelID"` |
| `totalSupply` | float64 | `AnalyzerResult.TotalSupply` |
| `totalDemand` | float64 | `AnalyzerResult.TotalDemand` |
| `utilization` | float64 | `AnalyzerResult.Utilization` |

**Per-variant slice** (`variants` key, one entry per variant):

| Field | Type | Source |
|---|---|---|
| `name` | string | `VariantCapacity.VariantName` |
| `k1` | int64 | `VariantCapacity.MedianK1` (new) |
| `k2` | int64 | `VariantCapacity.MedianK2` (new) |
| `k2Source` | string | `VariantCapacity.K2SourceLabel` (new): `"P1-obs"`, `"P2-hist"`, `"P3-deriv"`, `"P4-k1"` |
| `cost` | float64 | `VariantCapacity.Cost` |
| `prc` | float64 | `VariantCapacity.PerReplicaCapacity` |
| `eff` | float64 | `cost / prc` (computed inline) |
| `currReplicas` | int | `VariantDecision.CurrentReplicas` |
| `tgtReplicas` | int | `VariantDecision.TargetReplicas` |
| `action` | string | `VariantDecision.Action` |

**Logging library:** controller-runtime logr/zap — match the existing
`logger.Info(msg, keysAndValues...)` style used throughout the engine.
Do NOT use stdlib `slog`.

**Format example** (zap JSON output, single line):
```
{"level":"info","msg":"saturation cycle summary","model":"ns/m",
"totalSupply":658534,"totalDemand":1041047,"utilization":1.58,
"variants":[
  {"name":"primary","k1":751820,"k2":1152000,"k2Source":"P3-deriv","cost":10,
   "prc":1152000,"eff":8.68e-06,"currReplicas":1,"tgtReplicas":2,"action":"ScaleUp"},
  {"name":"v2","k1":329574,"k2":403391,"k2Source":"P1-obs","cost":5,
   "prc":403391,"eff":1.24e-05,"currReplicas":1,"tgtReplicas":1,"action":"NoChange"}
]}
```

---

## Code changes — step by step

All code is on `main`. Verify current line numbers yourself; function names
are stable.

### Step 1 — `internal/engines/analyzers/saturation_v2/types.go`

Add one field to `ReplicaCapacity` (package-private struct):

```go
K2Priority int // 1=observed, 2=history, 3=derived, 4=fallback
```

Place it alongside `MemoryBoundCapacity` / `ComputeBoundCapacity`.

### Step 2 — `internal/engines/analyzers/saturation_v2/analyzer.go`

**2a.** Change `computeK2` return type from `int64` to `(int64, int)`.
Return `(k2value, priority)` at each of the four exit points:

| Exit point | k2 | priority |
|---|---|---|
| Priority 1 — observed | `tokensInUse` | 1 |
| Priority 2 — historical | `int64(histAvg)` | 2 |
| Priority 3 — derived | `k2Derived` | 3 |
| Priority 4 — fallback | `k1` | 4 |

**2b.** In `computeReplicaCapacity` (the one call site of `computeK2`),
capture both return values:

```go
k2, k2Priority := a.computeK2(...)
```

Store `k2Priority` in the returned `ReplicaCapacity`:

```go
return &ReplicaCapacity{
    ...
    ComputeBoundCapacity: k2,
    K2Priority:           k2Priority,   // ADD
    ...
}
```

**2c.** In `aggregateByVariant`, after building `replicas []ReplicaCapacity` for
the variant, compute and set the three new `VariantCapacity` fields before
appending the `vc`:

```go
vc.MedianK1      = median64(k1Slice(replicas))      // median of MemoryBoundCapacity
vc.MedianK2      = median64(k2Slice(replicas))      // median of ComputeBoundCapacity
vc.K2SourceLabel = k2SourceLabel(replicas)          // from the representative replica
```

Helper `k2SourceLabel(replicas []ReplicaCapacity) string`: find the replica
whose `EffectiveCapacity` equals `median(EffectiveCapacity)` (i.e., the same
replica that determined `PerReplicaCapacity`); return its K2Priority mapped
through `map[int]string{1:"P1-obs",2:"P2-hist",3:"P3-deriv",4:"P4-k1"}`.
On tie, take the first match. If `replicas` is empty, return `""`.

Note: `median` is already implemented in the package — reuse it instead of
reimplementing.

### Step 3 — `internal/interfaces/analyzer.go`

Add three fields to `VariantCapacity`. Place them after `PerReplicaCapacity`:

```go
// Per-variant capacity detail set by the saturation V2 analyzer.
// Zero for all other analyzers.
MedianK1      int64  // median memory-bound capacity per replica (tokens)
MedianK2      int64  // median compute-bound capacity per replica (tokens)
K2SourceLabel string // how k2 was computed: "P1-obs","P2-hist","P3-deriv","P4-k1"
```

No existing callers read these fields, so adding them is backward compatible.

### Step 4 — `internal/engines/saturation/engine_v2.go`

Add a new package-level helper (not a method; does not need the engine):

```go
// logDecisionSummary emits one "saturation cycle summary" INFO line per model,
// combining per-variant capacity data from the saturation analyzer result with
// the optimizer's per-variant decisions.
func logDecisionSummary(
    ctx context.Context,
    modelRequests []pipeline.ModelScalingRequest,
    decisions []interfaces.VariantDecision,
) {
    logger := ctrl.LoggerFrom(ctx)

    // Index decisions by "namespace/modelID/variantName" for O(1) lookup.
    type decKey struct{ ns, model, variant string }
    decMap := make(map[decKey]interfaces.VariantDecision, len(decisions))
    for _, d := range decisions {
        decMap[decKey{d.Namespace, d.ModelID, d.VariantName}] = d
    }

    for _, req := range modelRequests {
        // Find the saturation analyzer result (always first, but search defensively).
        var satResult *interfaces.AnalyzerResult
        for _, nr := range req.AnalyzerResults {
            if nr.Name == interfaces.SaturationAnalyzerName {
                satResult = nr.Result
                break
            }
        }
        if satResult == nil {
            continue
        }

        type variantSummary struct {
            Name         string  `json:"name"`
            K1           int64   `json:"k1"`
            K2           int64   `json:"k2"`
            K2Source     string  `json:"k2Source"`
            Cost         float64 `json:"cost"`
            PRC          float64 `json:"prc"`
            Eff          float64 `json:"eff"`
            CurrReplicas int     `json:"currReplicas"`
            TgtReplicas  int     `json:"tgtReplicas"`
            Action       string  `json:"action"`
        }

        summaries := make([]variantSummary, 0, len(satResult.VariantCapacities))
        for _, vc := range satResult.VariantCapacities {
            d := decMap[decKey{req.Namespace, req.ModelID, vc.VariantName}]
            var eff float64
            if vc.PerReplicaCapacity > 0 {
                eff = vc.Cost / vc.PerReplicaCapacity
            }
            summaries = append(summaries, variantSummary{
                Name:         vc.VariantName,
                K1:           vc.MedianK1,
                K2:           vc.MedianK2,
                K2Source:     vc.K2SourceLabel,
                Cost:         vc.Cost,
                PRC:          vc.PerReplicaCapacity,
                Eff:          eff,
                CurrReplicas: d.CurrentReplicas,
                TgtReplicas:  d.TargetReplicas,
                Action:       string(d.Action),
            })
        }

        logger.Info("saturation cycle summary",
            "model", req.Namespace+"/"+req.ModelID,
            "totalSupply", satResult.TotalSupply,
            "totalDemand", satResult.TotalDemand,
            "utilization", satResult.Utilization,
            "variants", summaries,
        )
    }
}
```

### Step 5 — `internal/engines/saturation/engine.go`

Call `logDecisionSummary` immediately after `optimizeV2` returns, before
`applySaturationDecisions`. Find the `case interfaces.SaturationAnalyzerName:` branch:

```go
case interfaces.SaturationAnalyzerName:
    allDecisions = e.optimizeV2(ctx, modelGroups, currentAllocations)
    logDecisionSummary(ctx, modelGroups, allDecisions)   // ADD THIS LINE
```

No other changes to `engine.go`.

### Step 6 — Unit test

Add to `internal/engines/saturation/engine_v2_test.go` (or a new
`engine_v2_log_test.go` in the same package).

Use `go.uber.org/zap/zaptest/observer` to capture log output:

```go
func TestLogDecisionSummary_EmitsRequiredFields(t *testing.T) {
    core, logs := observer.New(zap.InfoLevel)
    logger := zapr.NewLogger(zap.New(core))
    ctx := logr.NewContext(context.Background(), logger)

    // Build a minimal ModelScalingRequest with one variant.
    req := pipeline.ModelScalingRequest{
        ModelID:   "mymodel",
        Namespace: "ns",
        AnalyzerResults: []pipeline.NamedAnalyzerResult{{
            Name: interfaces.SaturationAnalyzerName,
            Result: &interfaces.AnalyzerResult{
                TotalSupply:  100000,
                TotalDemand:  80000,
                Utilization:  0.8,
                VariantCapacities: []interfaces.VariantCapacity{{
                    VariantName:        "primary",
                    Cost:               10,
                    PerReplicaCapacity: 50000,
                    MedianK1:           60000,
                    MedianK2:           50000,
                    K2SourceLabel:      "P2-hist",
                    ReplicaCount:       1,
                }},
            },
        }},
    }
    decisions := []interfaces.VariantDecision{{
        ModelID:         "mymodel",
        Namespace:       "ns",
        VariantName:     "primary",
        CurrentReplicas: 1,
        TargetReplicas:  2,
        Action:          interfaces.ActionScaleUp,
    }}

    logDecisionSummary(ctx, []pipeline.ModelScalingRequest{req}, decisions)

    require.Equal(t, 1, logs.Len(), "expected one log line")
    entry := logs.All()[0]
    require.Equal(t, "saturation cycle summary", entry.Message)

    fields := entry.ContextMap()
    assert.Equal(t, "ns/mymodel", fields["model"])
    assert.NotNil(t, fields["variants"])
    // Spot-check one variant field via the rendered output.
    variants := entry.Context // zap fields
    _ = variants
    // Assert all required top-level keys are present.
    for _, key := range []string{"model","totalSupply","totalDemand","utilization","variants"} {
        assert.Contains(t, fields, key, "missing key %q", key)
    }
}
```

Adjust imports to match what the project already uses. The key assertion is
that the line is emitted and contains all required keys.

---

## Files changed

| File | Change |
|---|---|
| `internal/engines/analyzers/saturation_v2/types.go` | Add `K2Priority int` to `ReplicaCapacity` |
| `internal/engines/analyzers/saturation_v2/analyzer.go` | `computeK2` returns `(int64, int)`; populate `K2Priority`, `MedianK1`, `MedianK2`, `K2SourceLabel` |
| `internal/interfaces/analyzer.go` | Add `MedianK1`, `MedianK2`, `K2SourceLabel` to `VariantCapacity` |
| `internal/engines/saturation/engine_v2.go` | Add `logDecisionSummary` helper |
| `internal/engines/saturation/engine.go` | Call `logDecisionSummary` after `optimizeV2` |
| `internal/engines/saturation/engine_v2_test.go` (or new) | Unit test for `logDecisionSummary` |

---

## Pre-push checklist

Run in order from the repo root (in the new branch worktree):

1. `gofmt -l ./internal/...` — must be empty
2. `make test` — all pass
3. `make lint` — clean
4. `go build ./...` — clean
5. Every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`

---

## What NOT to do

- Do not change any scaling logic.
- Do not add Prometheus metrics (that is a separate follow-up).
- Do not remove or modify the existing `"V2 saturation analysis completed"` or
  `"Applied saturation decision"` log lines.
- Do not add config flags or feature gates.
- Do not add comments that reference plans-branch documents (`F3`, `A10`, etc.).
