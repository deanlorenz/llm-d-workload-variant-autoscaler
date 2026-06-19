# Coding Plan — Exact Min-Cost Variant Allocator (Type 3)

**Status:** DRAFT — not yet handed to a coder.
**Branch / worktree:** TBD — new issue + PR, base `main`. Assigned at handoff.
**Scope:** add a standalone, pure, exact allocator function + unit tests. **Integration into the
cost-aware optimizer is a separate follow-up — out of scope for this plan.**

This plan is self-contained. Implement exactly what is written here; you do not need any other
document.

---

## 1. Goal

Implement a function that, given a set of candidate variants and a per-analyzer demand, returns
the **minimum-cost** integer replica allocation that meets **every** analyzer's demand. Ties in
cost are broken by score, then deterministically.

---

## 2. Files

- New: `internal/engines/pipeline/cost_optimal_allocator.go`
- New: `internal/engines/pipeline/cost_optimal_allocator_test.go`

Package `pipeline`. Do not modify existing files in this plan.

---

## 3. Public surface

```go
// AllocCandidate is one variant's per-replica cost and capacity contribution.
type AllocCandidate struct {
    Name  string    // variant name
    Cost  float64   // per-replica cost (> 0)
    PRC   []float64 // per-replica capacity, one entry per analyzer (len == len(demand))
    Max   int       // maxReplicas cap; use Max < 0 for "unbounded"
    Score float64   // tie-break only; higher is preferred
}

// SolveMinCostAllocation returns the minimum-cost integer replica counts (keyed by
// candidate Name) such that, for every analyzer index a,
//   Σ_i counts[name_i] * candidates[i].PRC[a]  >=  demand[a].
// ok is false if the demand cannot be met under the Max caps.
//
// Among equal-cost feasible allocations the result is chosen by, in order:
//   1. highest total Score (Σ counts_i * Score_i),
//   2. fewest total replicas,
//   3. lexicographic by counts over candidates sorted by Name (full determinism).
func SolveMinCostAllocation(candidates []AllocCandidate, demand []float64) (counts map[string]int, ok bool)
```

Keep the function pure and deterministic: no logging, no clock, no globals.

---

## 4. Algorithm (uniform-cost search over a canonical tree)

Search allocations in increasing total cost; the first one that meets every demand is optimal.

**State (a search node):** `(idx, counts, cost, cap)` where
- `idx` = the candidate currently being filled (0-based),
- `counts` = replica count per candidate so far,
- `cost`  = `Σ counts_i * Cost_i`,
- `cap`   = capacity vector so far (`cap[a] = Σ counts_i * PRC_i[a]`).

**Successors of a node** (at most two — this keeps every allocation reachable by exactly one path):
1. **add** — if `counts[idx] < Max[idx]` (or `Max[idx] < 0`): increment `counts[idx]`, add
   `Cost[idx]` to cost and `PRC[idx]` to cap. Stay at `idx`.
2. **advance** — if `idx < len(candidates)-1`: move to `idx+1`, counts/cost/cap unchanged.

**Driver:**
```
precheck feasibility (§5); if infeasible return (nil, false)
heap ← min-priority-queue keyed by (cost asc, -totalScore, totalReplicas asc, lexCounts asc)
push start node (idx=0, counts=all-zero, cost=0, cap=0)
loop:
    node ← heap.pop_min()
    if node.cap >= demand (every component):     # first feasible pop is optimal
        return (node.counts, true)
    for succ in successors(node):
        push succ
    # heap cannot empty before feasibility once the precheck passed
```

Notes:
- Copy `counts` (and `cap`) when creating each successor — do not alias the parent's slice.
- The priority key's secondary fields make the first feasible pop already the tie-break winner;
  you do **not** need a separate equal-cost gather.
- Capacity is accumulated incrementally along edges (`O(A)` per successor).

---

## 5. Edge cases (must handle)

1. **Infeasibility precheck (required — prevents non-termination with unbounded `Max`).**
   For each analyzer `a`, compute the max reachable capacity:
   `reach[a] = Σ_i (Max_i < 0 && PRC_i[a] > 0 ? +∞ : max(Max_i,0) * PRC_i[a])`.
   If `reach[a] < demand[a]` for any `a`, return `(nil, false)` immediately.
2. **Useless add-edge.** Do not generate the **add** successor for candidate `idx` if its `PRC`
   is `0` for *every* analyzer whose demand is not yet met by `node.cap` — adding it only raises
   cost without progress (and, if `Max < 0`, would never terminate). The **advance** edge is
   still generated.
3. **Zero / already-met demand.** If `demand[a] <= 0` for all `a` (or the start node already
   meets demand), return an all-zero `counts` map with `ok = true`.
4. **`Cost <= 0` or `PRC` length mismatch.** Treat as a programming error: it is acceptable to
   document the precondition (`Cost > 0`, `len(PRC) == len(demand)`) and not defend against it,
   but do not panic on empty `candidates` — return `(nil, false)` if `candidates` is empty and
   demand is positive.

---

## 6. Tests (`cost_optimal_allocator_test.go`)

Use the project's existing test style (table-driven Go tests or Ginkgo — match the sibling files
in the package). Cover at minimum:

1. **Optimality witness (single analyzer).** Candidates `Y{PRC:[7],Cost:6}`, `Z{PRC:[10],Cost:9}`,
   `X{PRC:[5],Cost:5}`, all `Max` large; `demand=[10]`. Expect `{Z:1}`, total cost 9 (NOT
   `{Y:1,X:1}`).
2. **Trivial cover.** One candidate `{PRC:[100],Cost:10}`, `demand=[250]`, `Max:10` → `{:3}`.
3. **Max cap forces spillover.** Cheapest-efficiency variant capped below demand; assert the
   remainder is covered by the next variant at min cost.
4. **Infeasible.** Demand exceeds the sum of all `Max*PRC` → `ok == false`.
5. **Multi-analyzer (A=2).** One candidate strong on analyzer 0 / weak on 1, another the reverse;
   `demand` needs both → assert the min-cost combination that meets both components.
6. **Score tie-break.** Two equal-cost feasible allocations with different total Score → the
   higher-Score one is returned.
7. **Determinism.** Equal cost and equal score → result is stable across repeated calls (assert
   the documented fewest-replicas / lexicographic tie-break).
8. **Zero demand** → empty/all-zero allocation, `ok == true`.
9. **Unbounded `Max` (`Max < 0`).** Terminates and returns the correct finite count.

---

## 7. Gates (run before declaring work done)

- `make test` — all pass.
- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
- `make lint` — clean (required; CI blocks on it).
- `go build ./...` — clean.

---

## 8. Out of scope (do NOT do in this PR)

- Integrating the allocator into `costAwareScaleUp` / `costGreedyRolePick` /
  `allocateForModelPaired`, or changing any existing optimizer behavior.
- Precompute/caching of the cost order, Pareto-dominance pruning, cross-role joint-utilization
  trimming. These are deliberate follow-ups; build the correct standalone solver first.
- Developer-guide doc updates (no user-visible behavior changes until integration).
