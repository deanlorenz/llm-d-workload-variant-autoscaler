# WVA Saturation Cycle Summary Log — Task Plan

**Branch:** `wva-saturation-cycle-log-r1` in worktree `wva-log-rewrite`
**Type:** Type 3 task plan
**Scope:** Logging only. No behavioral change. Generic interface extension (one new field).
**Status:** R2 — label fixups (2026-06-22); Steps 1–7 already implemented at `69ba4d8b`

---

## Prerequisites — read before touching any code

The engine uses **controller-runtime logr/zap**, not stdlib `slog`.
- `ctrl.LoggerFrom(ctx)` returns the logger.
- Emit structured fields as `logger.Info(msg, key1, val1, key2, val2, ...)`.
- Do NOT import or use `log/slog`.
- `go.uber.org/zap/zaptest/observer` is the correct tool for capturing log
  output in unit tests.

---

## What this PR adds

Two structured INFO log lines per reconcile cycle per model:

1. **`"analyzer-result"`** — one per analyzer that ran, emitted in the engine
   immediately after `runAnalyzersAndScore` returns (post-threshold values).
2. **`"scaling-decision"`** — one per model, emitted after the optimizer
   produces decisions.

One generic field added to the shared interface: `Reason string` on
`VariantCapacity`. Every analyzer can set it to a free-text string describing
how it computed the variant's capacity; saturation V2 sets it to one of
`"P1-obs"`, `"P2-hist"`, `"P3-k2"`, `"P4-k1"`.

**Nothing else.** No new metrics, no config changes, no behavioral logic.
Log B (optimizer-internal reasoning log) is deferred to a follow-up — it
requires understanding optimizer internals for a schema that works across
all optimizers.

---

## Log line specs

**Logging library:** controller-runtime logr/zap — `logger.Info(msg, keysAndValues...)`.

### Log A — `"analyzer-result"`

Emitted once per named analyzer result in `runAnalyzersAndScore`, before
returning. Fields:

| Key | Type | Source |
|---|---|---|
| `modelID` | string | `modelID` parameter |
| `namespace` | string | `namespace` parameter |
| `analyzer` | string | `NamedAnalyzerResult.Name` |
| `supply` | float64 | `AnalyzerResult.TotalSupply` |
| `demand` | float64 | `AnalyzerResult.TotalDemand` |
| `util` | float64 | `AnalyzerResult.Utilization` |
| `rc` | float64 | `AnalyzerResult.RequiredCapacity` (post-threshold) |
| `sc` | float64 | `AnalyzerResult.SpareCapacity` (post-threshold) |
| `variants` | []variantEntry | one per `VariantCapacity` in the result |

`variantEntry` fields:

| Field | Type | Source |
|---|---|---|
| `name` | string | `VariantCapacity.VariantName` |
| `prc` | float64 | `VariantCapacity.PerReplicaCapacity` |
| `reason` | string | `VariantCapacity.Reason` (new; omitted if empty) |

Every analyzer emits this line. If an analyzer does not compute per-variant
capacity, `variants` is an empty slice. Do NOT compute any derived values
(e.g. `eff = cost/prc`) in the logger.

**Format example:**
```
{"level":"info","msg":"analyzer-result","modelID":"m","namespace":"ns",
 "analyzer":"saturation","supply":658534,"demand":1041047,"util":1.58,
 "rc":0,"sc":50000,
 "variants":[
   {"name":"primary","prc":1152000,"reason":"P3-k2"},
   {"name":"v2","prc":403391,"reason":"P1-obs"}
 ]}

{"level":"info","msg":"analyzer-result","modelID":"m","namespace":"ns",
 "analyzer":"throughput","supply":0,"demand":0,"util":0,
 "rc":15000,"sc":0,"variants":[]}
```

### Log C — `"scaling-decision"`

Emitted once per model after the optimizer returns. Fields:

| Key | Type | Source |
|---|---|---|
| `modelID` | string | `ModelScalingRequest.ModelID` |
| `namespace` | string | `ModelScalingRequest.Namespace` |
| `decisions` | []decisionEntry | one per variant decision for this model |

`decisionEntry` fields:

| Field | Type | Source |
|---|---|---|
| `name` | string | `VariantDecision.VariantName` |
| `curr` | int | `VariantDecision.CurrentReplicas` |
| `tgt` | int | `VariantDecision.TargetReplicas` |
| `action` | string | `VariantDecision.Action` |

**Format example:**
```
{"level":"info","msg":"scaling-decision","modelID":"m","namespace":"ns",
 "decisions":[
   {"name":"primary","curr":1,"tgt":2,"action":"ScaleUp"},
   {"name":"v2","curr":1,"tgt":1,"action":"NoChange"}
 ]}
```

---

## Code changes — step by step

Start from a clean worktree at `upstream/main`. Do NOT try to layer these
changes on the old 2-commit stack; rewrite from scratch.

### Step 1 — `internal/engines/analyzers/saturation_v2/types.go`

Add one field to `ReplicaCapacity` (package-private struct):

```go
K2Priority int // how k2 was computed: 1=observed, 2=history, 3=derived, 4=fallback
```

Place it after `ComputeBoundCapacity`.

### Step 2 — `internal/engines/analyzers/saturation_v2/analyzer.go`

**2a.** Change `computeK2` return type from `int64` to `(int64, int)`.
Return `(k2value, priority)` at each of the four exit points:

| Exit point | priority |
|---|---|
| Priority 1 — observed (`tokensInUse`) | 1 |
| Priority 2 — historical (`int64(histAvg)`) | 2 |
| Priority 3 — derived (`k2Derived`) | 3 |
| Priority 4 — fallback (`k1`) | 4 |

**2b.** In `computeReplicaCapacity`, capture both return values and store
`K2Priority` in the returned struct:

```go
k2, k2Priority := a.computeK2(...)
return &ReplicaCapacity{
    ...
    ComputeBoundCapacity: k2,
    K2Priority:          k2Priority,
    ...
}
```

**2c.** In `computeReplicaCapacityFallback` (the path that sets both
`MemoryBoundCapacity` and `ComputeBoundCapacity` to the same fallback value),
add `K2Priority: 4`. Without this, fallback replicas have priority 0 and the
label function returns `""` instead of `"P4-k1"`.

**2d.** In `aggregateByVariant`, after building `replicas []ReplicaCapacity`
for the variant, set `Reason` before appending `vc`:

```go
vc.Reason = k2SourceLabel(replicas)
```

**2e.** Add/keep the `k2SourceLabel` helper. It returns the K2Priority label
of the replica whose `EffectiveCapacity` is the median (the same replica that
determined `PerReplicaCapacity`). Use a sort+copy approach to handle even
replica counts correctly — do NOT equality-match against a computed median
average:

```go
func k2SourceLabel(replicas []ReplicaCapacity) string {
    if len(replicas) == 0 {
        return ""
    }
    sorted := make([]ReplicaCapacity, len(replicas))
    copy(sorted, replicas)
    sort.Slice(sorted, func(i, j int) bool {
        return sorted[i].EffectiveCapacity < sorted[j].EffectiveCapacity
    })
    medIdx := (len(sorted) - 1) / 2
    labels := map[int]string{1: "P1-obs", 2: "P2-hist", 3: "P3-k2", 4: "P4-k1"}
    if reason, ok := labels[sorted[medIdx].K2Priority]; ok {
        return reason
    }
    return ""
}
```

Note: the label for P3 is `"P3-k2"` (not `"P3-deriv"` as in the old plan).

**Do NOT add** `k1Slice`, `k2Slice`, `MedianK1`, `MedianK2`, or any other
sat-specific fields. `Reason` on `VariantCapacity` is the only outward-facing addition.

### Step 3 — `internal/interfaces/analyzer.go`

Add exactly **one** field to `VariantCapacity`, after `PerReplicaCapacity`:

```go
// Reason is a free-text string set by the analyzer to describe how the
// variant's per-replica capacity was computed. Empty for analyzers that
// do not set it. Saturation V2 uses "P1-obs", "P2-hist", "P3-k2", "P4-k1".
Reason string
```

Do NOT add `MedianK1`, `MedianK2`, `K2SourceLabel`, or `SaturationVariantCapacity`.
Do NOT add `SaturationVariantCapacities` to `AnalyzerResult`.

### Step 4 — `internal/engines/saturation/engine_v2.go`

Add two package-level helpers. Replace the old `logDecisionSummary` entirely.

**Helper A — `logAnalyzerResult`:**

```go
// logAnalyzerResult emits one INFO "analyzer-result" line for a single named
// analyzer result. Called for every analyzer that ran in a model's reconcile
// cycle, after the universal threshold post-step has been applied.
func logAnalyzerResult(ctx context.Context, modelID, namespace string, nr pipeline.NamedAnalyzerResult) {
    if nr.Result == nil {
        return
    }
    logger := ctrl.LoggerFrom(ctx)

    type variantEntry struct {
        Name   string  `json:"name"`
        PRC    float64 `json:"prc"`
        Reason string  `json:"reason,omitempty"`
    }
    variants := make([]variantEntry, 0, len(nr.Result.VariantCapacities))
    for _, vc := range nr.Result.VariantCapacities {
        variants = append(variants, variantEntry{
            Name:   vc.VariantName,
            PRC:    vc.PerReplicaCapacity,
            Reason: vc.Reason,
        })
    }

    logger.Info("analyzer-result",
        "modelID", modelID,
        "namespace", namespace,
        "analyzer", nr.Name,
        "supply", nr.Result.TotalSupply,
        "demand", nr.Result.TotalDemand,
        "util", nr.Result.Utilization,
        "rc", nr.Result.RequiredCapacity,
        "sc", nr.Result.SpareCapacity,
        "variants", variants,
    )
}
```

**Helper B — `logScalingDecisions`:**

```go
// logScalingDecisions emits one INFO "scaling-decision" line per model after
// the optimizer has produced per-variant decisions.
func logScalingDecisions(
    ctx context.Context,
    modelRequests []pipeline.ModelScalingRequest,
    decisions []interfaces.VariantDecision,
) {
    logger := ctrl.LoggerFrom(ctx)

    type modelKey struct{ ns, modelID string }
    type decisionEntry struct {
        Name   string `json:"name"`
        Curr   int    `json:"curr"`
        Tgt    int    `json:"tgt"`
        Action string `json:"action"`
    }

    grouped := make(map[modelKey][]decisionEntry, len(modelRequests))
    for _, d := range decisions {
        k := modelKey{d.Namespace, d.ModelID}
        grouped[k] = append(grouped[k], decisionEntry{
            Name:   d.VariantName,
            Curr:   d.CurrentReplicas,
            Tgt:    d.TargetReplicas,
            Action: string(d.Action),
        })
    }

    for _, req := range modelRequests {
        k := modelKey{req.Namespace, req.ModelID}
        entries := grouped[k]
        if len(entries) == 0 {
            continue
        }
        logger.Info("scaling-decision",
            "modelID", req.ModelID,
            "namespace", req.Namespace,
            "decisions", entries,
        )
    }
}
```

### Step 5 — `internal/engines/saturation/engine_v2.go` (`runAnalyzersAndScore`)

In `runAnalyzersAndScore`, immediately before `return namedResults, nil`, add:

```go
for _, nr := range namedResults {
    logAnalyzerResult(ctx, modelID, namespace, nr)
}
return namedResults, nil
```

No other changes to `runAnalyzersAndScore`.

### Step 6 — `internal/engines/saturation/engine.go`

Replace the `logDecisionSummary` call with `logScalingDecisions`:

```go
case interfaces.SaturationAnalyzerName:
    allDecisions = e.optimizeV2(ctx, modelGroups, currentAllocations)
    logScalingDecisions(ctx, modelGroups, allDecisions)  // replaces logDecisionSummary
```

No other changes to `engine.go`.

### Step 7 — Unit tests (`engine_v2_log_test.go`)

Use `go.uber.org/zap/zaptest/observer` + `go.uber.org/zapr` to capture logs.
Add tests in `internal/engines/saturation/engine_v2_log_test.go` (new file,
same package `saturation`).

**Required tests:**

1. `TestLogAnalyzerResult_EmitsRequiredFields` — one analyzer result with one
   variant; assert `"analyzer-result"` line emitted with keys `modelID`,
   `namespace`, `analyzer`, `supply`, `demand`, `util`, `rc`, `sc`, `variants`;
   assert variant entry has `name`, `prc`, `reason` (no `cost`).

2. `TestLogAnalyzerResult_NilResultSkipped` — pass a `NamedAnalyzerResult`
   with `Result == nil`; assert no log line emitted.

3. `TestLogAnalyzerResult_EmptyVariants` — result with zero `VariantCapacities`;
   assert `"analyzer-result"` line emitted with `variants == []` (not nil).

4. `TestLogScalingDecisions_EmitsPerModel` — two models, three decisions total
   (2+1); assert two `"scaling-decision"` lines, correct `decisions` grouping.

5. `TestLogScalingDecisions_NoDecisionsSkipsModel` — a model in `modelRequests`
   with no corresponding decision; assert no log line for that model.

---

## Files changed

| File | Change |
|---|---|
| `internal/engines/analyzers/saturation_v2/types.go` | Add `K2Priority int` to `ReplicaCapacity` |
| `internal/engines/analyzers/saturation_v2/analyzer.go` | `computeK2` returns `(int64, int)`; set `K2Priority` in both capacity paths; set `vc.Reason` in `aggregateByVariant`; add/keep `k2SourceLabel`; **R2: add `"P0-store"` label for store-path variants** |
| `internal/interfaces/analyzer.go` | Add `Reason string` to `VariantCapacity` only |
| `internal/engines/saturation/engine_v2.go` | Replace `logDecisionSummary` with `logAnalyzerResult` + `logScalingDecisions`; add log loop in `runAnalyzersAndScore`; **R2: drop `cost` from `variantEntry`** |
| `internal/engines/saturation/engine.go` | Replace `logDecisionSummary` call with `logScalingDecisions` |
| `internal/engines/analyzers/throughput/analyzer.go` | **R2: `resolveITLModel` returns tier label; `VariantCapacity` gets `Reason`** |
| `internal/engines/saturation/engine_v2_log_test.go` (new) | 5 unit tests; **R2: remove `cost` assertions, update label assertions** |

---

## R2 amendments — label fixups (implement after Steps 1–7 are in place)

Steps 1–7 are already implemented on the branch at `69ba4d8b`. These three
additional steps correct label gaps found during review. Implement as a
single additional commit on top of `69ba4d8b`.

### Step 8 — Drop `cost` from `variantEntry` (`engine_v2.go`)

File: `internal/engines/saturation/engine_v2.go`, function `logAnalyzerResult`.

**8a.** Remove `Cost` from the `variantEntry` struct and rename `Label` → `Reason`:

```go
// BEFORE
type variantEntry struct {
    Name   string  `json:"name"`
    PRC    float64 `json:"prc"`
    Cost   float64 `json:"cost"`
    Label  string  `json:"label,omitempty"`
}

// AFTER
type variantEntry struct {
    Name   string  `json:"name"`
    PRC    float64 `json:"prc"`
    Reason string  `json:"reason,omitempty"`
}
```

**8b.** Update the struct literal in the for loop:

```go
// BEFORE
variants = append(variants, variantEntry{
    Name:  vc.VariantName,
    PRC:   vc.PerReplicaCapacity,
    Cost:  vc.Cost,
    Label: vc.CapacityLabel,
})

// AFTER
variants = append(variants, variantEntry{
    Name:   vc.VariantName,
    PRC:    vc.PerReplicaCapacity,
    Reason: vc.Reason,
})
```

**8c.** In `engine_v2_log_test.go`, remove any assertion on `cost` from
`TestLogAnalyzerResult_EmitsRequiredFields` and any fixture that sets `Cost`.
Also remove `"cost"` from the required-keys list if present.

### Step 9 — Sat_v2 store-path label `"P0-store"` (`saturation_v2/analyzer.go`)

File: `internal/engines/analyzers/saturation_v2/analyzer.go`, function `aggregateByVariant`.

The current code sets `Reason: k2SourceLabel(replicas)` on every
variant unconditionally. `k2SourceLabel([])` returns `""` when there are no
live replicas — but the capacity store is then used to derive `PerReplicaCapacity`.
Operators cannot tell store-derived from missing data.

**9a.** Introduce a `reason` local variable and set it in each branch
of the `if len(replicas) > 0 / else if capacityStore ... / else if lookupCompatible ...`
block:

```go
var reason string
if len(replicas) > 0 {
    // existing: compute perReplicaCapacity from median
    ...
    reason = k2SourceLabel(replicas)
} else if rec := a.capacityStore.Get(namespace, modelID, vs.VariantName); rec != nil && rec.EffectiveCapacity > 0 {
    // existing: derive from stored record
    perReplicaCapacity = a.estimateStoredCapacity(rec, modelID, kvCacheThreshold, modelAvgInput, modelAvgOutput)
    reason = "P0-store"
} else if rec := a.lookupCompatibleCapacity(namespace, modelID, vs.VariantName, accelerator, vs.GPUsPerReplica); rec != nil {
    // existing: cross-variant estimation
    perReplicaCapacity = float64(rec.EffectiveCapacity)
    reason = "P0-store"
}
```

**9b.** In the `vc` struct literal further down, replace `k2SourceLabel(replicas)`
with `reason`:

```go
// BEFORE
vc := interfaces.VariantCapacity{
    ...
    Reason: k2SourceLabel(replicas),
}

// AFTER
vc := interfaces.VariantCapacity{
    ...
    Reason: reason,
}
```

**9c.** Add a test in `saturation_v2/analyzer_test.go` (or a new
`saturation_v2/capacity_label_test.go`) verifying that when no replica
metrics are present but a capacity store record exists, the returned
`VariantCapacity.Reason` equals `"P0-store"`.

### Step 10 — Throughput analyzer tier labels (`throughput/analyzer.go`)

File: `internal/engines/analyzers/throughput/analyzer.go`.

**10a.** Change `resolveITLModel` signature from `(ITLModel, bool)` to
`(ITLModel, string, bool)`. The string is the tier reason.

Return the reason at each exit point:

```go
// Tier 1 — OLS fit succeeds
return model, "T1-ols", true

// Tier 2 — constrained OLS succeeds
// Determine reason before returning:
reason := "T2-default"
if state.hasFittedB {
    reason = "T2-pinned"
}
return ITLModel{A: A, B: baselineB}, reason, true

// Failure
return ITLModel{}, "", false
```

**10b.** Update the call site in `Analyze()` to capture all three return values:

```go
// BEFORE
model, ok := a.resolveITLModel(ctx, state, healthyMetrics, input.Namespace, input.ModelID, variantName)

// AFTER
model, reason, ok := a.resolveITLModel(ctx, state, healthyMetrics, input.Namespace, input.ModelID, variantName)
```

**10c.** Add `Reason: reason` to the `interfaces.VariantCapacity`
struct literal where the TA builds its per-variant results (the `append` call
around line 331):

```go
variantCapacities = append(variantCapacities, interfaces.VariantCapacity{
    VariantName:        variantName,
    Role:               state.role,
    ReplicaCount:       nKV,
    PendingReplicas:    pending,
    PerReplicaCapacity: perReplicaSupply,
    TotalCapacity:      totalCapacity,
    TotalDemand:        demand,
    Utilization:        safeDivide(demand, totalCapacity),
    Reason:      reason,   // ADD
})
```

**10d.** Add tests in `throughput/analyzer_test.go` asserting that:
- A variant resolved via Tier 1 returns `Reason == "T1-ols"`.
- A variant resolved via Tier 2 with a prior fit returns `"T2-pinned"`.
- A variant resolved via Tier 2 cold-start returns `"T2-default"`.

### After all R2 steps

- Run all gates: `gofmt -l internal/`, `make test`, `make lint`, `go build ./...`
- One commit for all three changes, DCO sign-off required:
  `git commit -s -m "engine: fix variant reason field — drop cost from log, add store/TA tier reasons"`
- Write `plan__wva-log-label-fixes-done.md` handoff.
- Do NOT push.

---

## Rewrite strategy

**Do NOT rebase the old 2-commit stack** (`e92e26ba`, `01bfe940`). The design
has changed completely. Procedure:

1. Create a fresh worktree from `upstream/main` (tip `02d06eb2` as of 2026-06-19):
   ```
   git -C repo fetch upstream
   git -C repo worktree add ../wva-log-rewrite upstream/main
   ```
   (Use a temporary worktree name like `wva-log-rewrite`; rename or push to
   `origin/wva-saturation-cycle-log` when done.)

2. Implement Steps 1–7 above.

3. Run all gates (pre-push checklist).

4. Write a `plan__wva-log-rewrite-ready.md` handoff. Dean will force-push to
   `origin/wva-saturation-cycle-log` to update PR #1277 (coders never push).

---

## Pre-push checklist

Run in order from the worktree root:

1. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — must be empty
2. `make test` — all pass
3. `make lint` — clean
4. `go build ./...` — clean
5. Every commit: `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`

---

## What NOT to do

- Do not change any scaling logic.
- Do not add Prometheus metrics (separate follow-up).
- Do not remove or modify the existing `"V2 saturation analysis completed"` or
  `"Applied saturation decision"` log lines.
- Do not add config flags or feature gates.
- Do not add comments that reference plans-branch documents.
- Do not add `MedianK1`, `MedianK2`, `K2SourceLabel`, `SaturationVariantCapacity`,
  or `SaturationVariantCapacities` — these belonged to the old design.
- Do not use `K2Priority` outside the `saturation_v2` package.
- Do not compute derived values (`eff`, `cost/prc`, etc.) inside the log helpers.
- Do not add `cost` to `variantEntry` — cost is variant metadata logged separately.
- Do not add optimizer-internal logging (Log B deferred).
- Do not touch the QM analyzer path (known gap, separate work).
