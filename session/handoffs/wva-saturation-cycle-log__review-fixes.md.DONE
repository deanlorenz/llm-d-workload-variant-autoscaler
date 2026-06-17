from: planner
session: review-fixes

## Two fixes required before PR #1277 can merge

ev-shindin review on PR #1277. Both must be addressed in a single fixup commit.

---

### Fix 1 — Interface pollution: move saturation-specific fields out of VariantCapacity

**Problem:** `MedianK1`, `MedianK2`, `K2SourceLabel` were added to
`interfaces.VariantCapacity`, which is shared by every analyzer. ev-shindin
correctly flags this: these fields are saturation-specific and zero-valued for
all other analyzers.

**Fix:** Remove the three fields from `interfaces.VariantCapacity`. Add a new
struct and field to `interfaces.AnalyzerResult` instead:

In `internal/interfaces/analyzer.go`:

```go
// SaturationVariantCapacity carries per-variant k1/k2/k2Source detail
// produced by the saturation V2 analyzer. Nil for all other analyzers.
type SaturationVariantCapacity struct {
    VariantName   string
    MedianK1      int64
    MedianK2      int64
    K2SourceLabel string
}
```

Add one field to `AnalyzerResult`:
```go
// Set by saturation V2 only; nil for all other analyzers.
SaturationVariantCapacities []SaturationVariantCapacity
```

Populate it in `aggregateByVariant` in `saturation_v2/analyzer.go`:
- Build one `SaturationVariantCapacity` per variant using the same
  `medianK1`, `medianK2`, `k2Source` locals already computed there.
- Attach the slice to the `AnalyzerResult` returned by `Analyze()`.

In `logDecisionSummary` (engine_v2.go): read from
`satResult.SaturationVariantCapacities` (keyed by `VariantName`) instead of
from `vc.MedianK1` etc. Build a lookup map by variant name before the summary
loop.

Remove `MedianK1`, `MedianK2`, `K2SourceLabel` from `interfaces.VariantCapacity`
and all code that writes to those fields.

---

### Fix 2 — Even-replica bug in k2SourceLabel

**Problem:** `k2SourceLabel` calls `median(effs)` which for even-length slices
returns the **average** of the two middle values (e.g. `[100, 200]` → `150`).
No replica has `EffectiveCapacity == 150`, so the equality match falls through
and the function silently returns `""`. K2Source is blank for any variant with
an even number of ready replicas.

**Fix:** Replace the `median()`-then-equality-match approach with a
sort-and-index approach that always resolves to an actual replica:

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
    medIdx := (len(sorted) - 1) / 2  // lower-median index, always valid
    k2PriorityLabels := map[int]string{1: "P1-obs", 2: "P2-hist", 3: "P3-deriv", 4: "P4-k1"}
    if label, ok := k2PriorityLabels[sorted[medIdx].K2Priority]; ok {
        return label
    }
    return ""
}
```

Also update the comment on `K2SourceLabel` in the new
`SaturationVariantCapacity` struct to say "k2 priority of the lower-median
replica by EffectiveCapacity" rather than "same replica that determines
PerReplicaCapacity" (which is only true for odd replica counts).

---

### Commit structure

One fixup commit on top of the existing `e92e26ba`:

```
engine: fix review findings — saturation k2 fields out of VariantCapacity; k2SourceLabel even-replica bug
```

### After the commit

- Run all gates (make test, gofmt, make lint, go build)
- Force-push to origin/wva-saturation-cycle-log (--force-with-lease)
- Write review__wva-saturation-cycle-log-ready.md trigger
