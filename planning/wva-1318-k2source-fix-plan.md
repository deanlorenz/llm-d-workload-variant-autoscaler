# #1318 pre-merge fix — named constants for analyzer reason strings

**Branch:** `wva-saturation-cycle-log-r1` in worktree `wva-log-rewrite`
**Type:** Type 3 task plan
**Scope:** 5 files, 1 commit. No behavioral change.
**Trigger:** ev-shindin non-blocking review comment on `saturation_v2/analyzer.go:663` —
the 1–4 priority codes exist as bare int returns in `computeK2`, as a local
`map[int]string{1:"P1-obs",…}` in `k2SourceLabel`, and in the `K2Priority int` field
comment. Address before merge by introducing a named type and a single shared label map.
While here: apply the same principle to TA — its 4 reason strings ("T1-ols", "T2-default",
"T2-pinned", "T2-failed") appear as literals in both production code and test assertions,
making named constants the right fix.

---

## Pre-action gate

Run before touching any file:

```bash
pwd && git branch --show-current   # must be wva-saturation-cycle-log-r1
git status                          # must be clean
```

---

## Change spec

Seven files change. No new files. One commit.

---

### File 1 — `internal/engines/analyzers/saturation_v2/types.go`

**A.** Before the `ReplicaCapacity` struct, add the type, constants, and label map:

```go
// k2Source identifies which priority level produced the compute-bound capacity
// estimate for a replica.
type k2Source int

const (
	k2SrcObserved  k2Source = iota + 1 // queue saturated: tokensInUse
	k2SrcHistorical                     // rolling average from prior observations
	k2SrcDerived                        // estimated from deployment args
	k2SrcFallback                       // fallback to k1 (memory-bound)
)

var k2Labels = map[k2Source]string{
	k2SrcObserved:   "P1-obs",
	k2SrcHistorical: "P2-hist",
	k2SrcDerived:    "P3-k2",
	k2SrcFallback:   "P4-k1",
}
```

**B.** After the `k2Labels` var, add two string constants for the no-live-replica paths in `aggregateByVariant`:

```go
const (
	satReasonP0Store = "P0-store" // capacity from store or compatible-variant record; no live replicas
	satReasonNoData  = "no-data"  // no live replicas and no store record
)
```

**C.** Change the `K2Priority` field in `ReplicaCapacity`:

Old:
```go
K2Priority            int   // how k2 was computed: 1=observed, 2=history, 3=derived, 4=fallback
```

New:
```go
K2Priority            k2Source // how k2 was computed
```

---

### File 2 — `internal/engines/analyzers/saturation_v2/analyzer.go`

All changes are type-only or constant substitutions; no logic changes.

**A.** Change `computeK2` return type (line ~284):

Old: `func (a *SaturationAnalyzer) computeK2(...) (int64, int)`
New: `func (a *SaturationAnalyzer) computeK2(...) (int64, k2Source)`

**B.** Replace bare int returns inside `computeK2`:

| Location | Old | New |
|---|---|---|
| Priority 1 return (~line 299) | `return k2Observed, 1` | `return k2Observed, k2SrcObserved` |
| Priority 2 return (~line 311) | `return int64(histAvg), 2` | `return int64(histAvg), k2SrcHistorical` |
| Priority 3 return (~line 316) | `return k2Derived, 3` | `return k2Derived, k2SrcDerived` |
| Priority 4 return (~line 320) | `return k1, 4` | `return k1, k2SrcFallback` |

**C.** In `computeReplicaCapacityFallback` struct literal (~line 263):

Old: `K2Priority: 4,`
New: `K2Priority: k2SrcFallback,`

**D.** In `aggregateByVariant` (~lines 383–389): replace the two `"P0-store"` and one `"no-data"` literals:

| Location | Old | New |
|---|---|---|
| ~line 383 | `capacityLabel = "P0-store"` | `capacityLabel = satReasonP0Store` |
| ~line 387 | `capacityLabel = "P0-store"` | `capacityLabel = satReasonP0Store` |
| ~line 389 | `capacityLabel = "no-data"` | `capacityLabel = satReasonNoData` |

**E.** In `k2SourceLabel` (~lines 663–667): remove the local map literal and use `k2Labels`:

Old:
```go
labels := map[int]string{1: "P1-obs", 2: "P2-hist", 3: "P3-k2", 4: "P4-k1"}
if label, ok := labels[sorted[medIdx].K2Priority]; ok {
    return label
}
return "error"
```

New:
```go
if label, ok := k2Labels[sorted[medIdx].K2Priority]; ok {
    return label
}
return "error"
```

---

### File 3 — `internal/engines/analyzers/saturation_v2/analyzer_test.go`

Replace the 2 string literal assertions with the named constants:

| Location | Old | New |
|---|---|---|
| ~line 1387 | `Equal("P0-store")` | `Equal(satReasonP0Store)` |
| ~line 1406 | `Equal("no-data")` | `Equal(satReasonNoData)` |

---

### File 4 — `internal/engines/analyzers/throughput/constants.go`

Add four string constants at the end of the existing `const (...)` block:

```go
// itlReason* are the values set on VariantCapacity.Reason by resolveITLModel.
// They appear in the "analyzer-result" structured log line.
itlReasonT1OLS     = "T1-ols"     // tier-1: OLS fit from live observations
itlReasonT2Default = "T2-default" // tier-2: constrained OLS with default B baseline
itlReasonT2Pinned  = "T2-pinned"  // tier-2: constrained OLS with previously fitted B
itlReasonT2Failed  = "T2-failed"  // all paths exhausted; no model for this cycle
```

---

### File 5 — `internal/engines/analyzers/throughput/analyzer.go`

Replace the 4 string literals in `resolveITLModel` with the named constants:

| Location | Old | New |
|---|---|---|
| Tier-1 return (~line 475) | `return model, "T1-ols", true` | `return model, itlReasonT1OLS, true` |
| Tier-2 label init (~line 489) | `tier2Label := "T2-default"` | `tier2Label := itlReasonT2Default` |
| Tier-2 label reassign (~line 492) | `tier2Label = "T2-pinned"` | `tier2Label = itlReasonT2Pinned` |
| Tier-2 failure return (~line 513) | `return ITLModel{}, "T2-failed", false` | `return ITLModel{}, itlReasonT2Failed, false` |

---

### File 5 — `internal/engines/analyzers/throughput/analyzer_test.go`

Replace the 4 matching string literal assertions with the named constants (same package, so unexported constants are accessible):

| Location | Old | New |
|---|---|---|
| ~line 436 | `Equal("T1-ols")` | `Equal(itlReasonT1OLS)` |
| ~line 493 | `Equal("T2-default")` | `Equal(itlReasonT2Default)` |
| ~line 529 | `Equal("T2-pinned")` | `Equal(itlReasonT2Pinned)` |
| ~line 552 | `Equal("T2-failed")` | `Equal(itlReasonT2Failed)` |

---

## Commit

```bash
pwd && git branch --show-current   # verify branch before commit
git add internal/engines/analyzers/saturation_v2/types.go \
        internal/engines/analyzers/saturation_v2/analyzer.go \
        internal/engines/analyzers/saturation_v2/analyzer_test.go \
        internal/engines/analyzers/throughput/constants.go \
        internal/engines/analyzers/throughput/analyzer.go \
        internal/engines/analyzers/throughput/analyzer_test.go
git commit -s -m "analyzers: introduce named constants for analyzer reason strings

saturation_v2: replace bare int constants (1-4) with a named k2Source type
and a single shared k2Labels map. Removes three-way duplication across
computeK2 return sites, the ReplicaCapacity field, and k2SourceLabel.
Add satReasonP0Store/satReasonNoData string constants for the no-live-replica
paths in aggregateByVariant; update test assertions to match.

throughput: replace 'T1-ols'/'T2-*' string literals with named itlReason*
constants in production code and test assertions. Removes duplication
between the single production definition and four test assertion sites.

No behavioral change."
```

---

## Gates (run in order, all must pass)

```bash
gofmt -l ./internal/... ./pkg/... ./cmd/...   # must be empty
go build ./...                                  # must be clean
make test                                       # all pass
make lint                                       # clean
```

---

## Done criteria

All four gates pass. Write status file; write handoff to planner.

---

## Post-fix: write plan handoff

After commit + gates pass, write `plans/session/handoffs/plan__1318-k2source-done.md`:

```
from: wva-saturation-cycle-log-r1
session: 1318-k2source-fix

## What changed
One commit on wva-saturation-cycle-log-r1: named constants for analyzer reason strings.
Files: saturation_v2/types.go, saturation_v2/analyzer.go, saturation_v2/analyzer_test.go,
       throughput/constants.go, throughput/analyzer.go, throughput/analyzer_test.go
All gates pass (gofmt, go build, make test, make lint).

## Update CURRENT.md
PR #1318 tip: <new sha>
Add note: ev-shindin non-blocking comment addressed (k2Source, satReason*, itlReason* constants).
State: in review — ready to merge.
```
