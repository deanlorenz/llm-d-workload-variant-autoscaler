# #1318 pre-merge fix — k2Source named type

**Branch:** `wva-saturation-cycle-log-r1` in worktree `wva-log-rewrite`
**Type:** Type 3 task plan
**Scope:** 2 files, 1 commit. No behavioral change.
**Trigger:** ev-shindin non-blocking review comment on `saturation_v2/analyzer.go:663` —
the 1–4 priority codes exist as bare int returns in `computeK2`, as a local
`map[int]string{1:"P1-obs",…}` in `k2SourceLabel`, and in the `K2Priority int` field
comment. Address before merge by introducing a named type and a single shared label map.

---

## Pre-action gate

Run before touching any file:

```bash
pwd && git branch --show-current   # must be wva-saturation-cycle-log-r1
git status                          # must be clean
```

---

## Change spec

Two files change. No new files. One commit.

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

**B.** Change the `K2Priority` field in `ReplicaCapacity`:

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

**D.** In `k2SourceLabel` (~lines 663–667): remove the local map literal and use `k2Labels`:

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

## Commit

```bash
pwd && git branch --show-current   # verify branch before commit
git add internal/engines/analyzers/saturation_v2/types.go \
        internal/engines/analyzers/saturation_v2/analyzer.go
git commit -s -m "saturation_v2: introduce k2Source named type for k2 priority levels

Replace bare int constants (1–4) with a named k2Source type and a
single shared k2Labels map. Removes three-way duplication in computeK2
return sites, the ReplicaCapacity field, and the k2SourceLabel lookup.
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
One commit on wva-saturation-cycle-log-r1: k2Source named type.
Files: internal/engines/analyzers/saturation_v2/types.go,
       internal/engines/analyzers/saturation_v2/analyzer.go
All gates pass (gofmt, go build, make test, make lint).

## Update CURRENT.md
PR #1318 tip: <new sha>
Add note: ev-shindin non-blocking comment addressed (k2Source named type).
State: in review — ready to merge.
```
