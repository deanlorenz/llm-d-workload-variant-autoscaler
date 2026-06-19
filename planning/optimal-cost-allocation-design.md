# Optimal Cost-Aware Variant Allocation — Design (Type 1)

**Status:** DRAFT (brainstorm result, 2026-06-10)
**Origin:** review of PR #1252 / issue #1251 turned into a design discussion.
**Supersedes (conceptually):** the greedy `costAwareScaleUp` allocation and PR #1252's
one-level fallback patch. This is a *new* direction, to land as its own issue + PR (not part
of the #1252 review).

---

## 1. Motivation

The cost-aware optimizer allocates replicas to variants greedily by **cost efficiency**
(`cost / perReplicaCapacity`, ascending), then commits whole replicas to the most efficient
variant first. PR #1252 patches one symptom — when the last replica of the efficient variant is
mostly wasted, defer the overflow to the cheapest-by-absolute-cost variant.

Two findings from the discussion:

1. **PR #1252 is correct but only a heuristic.** Its one-level fallback always covers demand
   (the "A,B,C cascade" worry does *not* materialize — `remaining` is a single cumulative
   variable, and the fallback condition bounds it within the cheapest variant's headroom, so the
   cheapest variant is never over-subscribed). But it is not cost-optimal.

2. **Greedy-by-efficiency is fundamentally suboptimal** — this is the knapsack-cover integrality
   gap. Concrete witness (single demand `D = 10`):

   | variant | PRC | cost | efficiency |
   |---|---|---|---|
   | Y | 7  | 6 | 0.857 (best) |
   | Z | 10 | 9 | 0.900 |
   | X | 5  | 5 | 1.000 |

   | allocation | capacity | cost |
   |---|---|---|
   | **1×Z** | 10 | **9 ← optimal** |
   | 2×X | 10 | 10 |
   | 1×Y + 1×X | 12 | 11 ← greedy + #1252 both land here |
   | 2×Y | 14 | 12 |

   Greedy commits the most-efficient Y first and never reconsiders the whole allocation, so it
   misses `1×Z`. No amount of last-replica patching fixes a gap that lives in the *first*
   allocation decision.

We want an **exact minimum-cost allocation** that also generalizes cleanly to the
**multi-analyzer** case.

---

## 2. Problem statement

Minimize total cost subject to meeting **every** analyzer's required capacity (a hard
conjunction — a vector demand, not a scalarized aggregate):

```
minimize    Σ_i  n_i · cost_i
subject to  Σ_i  n_i · PRC_{i,a} ≥ D_a      for every analyzer a
            0 ≤ n_i ≤ max_i,   n_i ∈ ℤ
```

- `i` ranges over the candidate variants (for a model, or a model-role).
- `D_a` is analyzer `a`'s required capacity; `PRC_{i,a}` is variant `i`'s per-replica capacity
  *as seen by analyzer `a`*. Single-analyzer is the `A = 1` special case.
- `cost_i` is the per-replica cost; `max_i` is the variant's `maxReplicas` (may be unbounded).

**No score in the objective.** Analyzer scores are *not* part of cost minimization. They survive
only as a **tie-break among equal-cost optima** (to preserve today's behavior and keep the chosen
allocation deterministic — see §6).

This is a multi-constraint integer covering program — **weakly NP-hard** in general (knapsack's
cover sibling), solvable in pseudo-polynomial time. But real instances are tiny (2–4 variants per
model-role, small `max_i`), so an exact solver is cheap and worthwhile.

---

## 3. Intuition

Enumerate candidate allocations **in increasing total cost** and return the first one that
satisfies every analyzer's demand. The first feasible allocation in cost order is, by
definition, the minimum-cost feasible allocation.

Two structural facts make this efficient and reusable:

- **Cost order is independent of demand, PRC, and analyzer count.** An allocation's cost is
  `Σ n_i·cost_i` — a function of the counts and the per-variant costs *only*. Demand and
  per-replica capacities enter *only* the feasibility test. So the cost-sorted enumeration order
  depends on the **cost vector alone**. Costs change rarely (pricing); demand changes every
  reconcile. Therefore the order can be **precomputed once per price configuration** and replayed
  every reconcile — demand only moves the *stopping point*, never the order.

- **Canonical enumeration avoids permutation duplicates.** Fix a variant order and only ever add
  variants in non-decreasing index. Then each multiset of replicas (`i,i,j` ≡ `i,j,i`) is reached
  by exactly one path.

Feasibility is **not monotone** in cost (a cheap allocation can be infeasible, a costlier one
feasible, a still-costlier one infeasible again). That is fine: we return the *first* feasible in
cost order; we never rely on monotonicity to prune.

---

## 4. The canonical search tree

Node `(i, k)` = "variants `v_1..v_{i-1}` are frozen at chosen counts, currently holding `k`
replicas of `v_i`." Exactly two out-edges (this is what enforces canonical, duplicate-free paths):

- **add:** `(i, k) → (i, k+1)`, cost `+cost_i`, capacity `+PRC_{i,·}` — one more replica of `v_i`
  (only while `k+1 ≤ max_i`).
- **advance:** `(i, k) → (i+1, 0)`, cost `+0`, capacity `+0` — freeze `v_i` at `k`, open `v_{i+1}`.

The advance edge is zero-cost / zero-capacity; it only gates *which* variants remain addable.
It strictly increases the variant index, so there are at most `m` advances per allocation — no
zero-cost cycle, and the search terminates.

An allocation is the count vector realized when generation stops extending a path; its capacity
is `Σ_{j} n_j·PRC_{j,·}` over the variants actually used.

---

## 5. Algorithm

### 5.1 Online search (no precompute) — UCS over the tree

```
function allocate(variants, D, max, cost, score):
    # priority key: (cost asc, score-preference)  — score breaks cost ties
    heap ← { node (i=1, k=0), cost=0, capacity=0 }
    while heap not empty:
        node ← heap.pop_min()                      # min cost, then best score
        if node.capacity ≥ D  (componentwise):     # first feasible pop = optimal
            return node.allocation
        for child in successors(node):             # ≤ 2: add v_i (if k<max_i), advance
            child.cost     ← node.cost + edgeCost
            child.capacity ← node.capacity + edgePRC   # incremental, O(A)
            heap.push(child)
    return INFEASIBLE        # demand unreachable even at all max_i
```

- **First feasible pop is optimal** because edge costs are ≥ 0 (uniform-cost search), and the
  heap's secondary key (score) means that, within a cost level, the highest-score feasible node
  pops first → the score tie-break falls out automatically.
- **Complexity:** `O(N log N)` where `N` = nodes settled with cost ≤ the optimal cost `C*` — the
  *actual stop point*, not the full lattice (just as Dijkstra settles only nodes within the goal's
  distance). Never worse than exhaustive.

### 5.2 Precompute + replay (amortized across reconciles)

Because the order is demand-independent:

1. **Offline, once per cost config:** run the same tree expansion with cost-only ordering and no
   stop condition (to a cost bound), caching the cost-sorted allocation sequence. With finite
   `max_i` this is a finite list; with any unbounded `max_i` it is generated **lazily** via the
   heap and the cached prefix extended on demand.
2. **Online, every reconcile:** walk the cached order, lazily sum each allocation's capacity
   against this reconcile's `D`, stop at the first feasible.
3. **Score tie-break on the precompute path:** the cached order is cost-only (it must be, to stay
   demand/PRC/score-independent and reusable). So at the stop cost `C*`, **gather all feasible
   allocations with `cost == C*` and pick by score** — do not let the arbitrary cost-tie order
   choose silently. (Equal-cost ties are few, so this is cheap.)

### 5.3 Optional later speedup — Pareto dominance pruning

Pure efficiency optimization; never changes the answer. **Correctness rules:**

- Prune node `v` only if some `u` has `u.cost ≤ v.cost` **AND** `u.capacity ≥ v.capacity`
  (componentwise), at least one strict. Lower cost *alone* is not dominance.
- Dominance is valid **only between nodes in the same layer `(i, k)`** — i.e. identical remaining
  freedom (same `v_i` headroom `max_i − k`, same free `v_{i+1..m}`). **Never prune across `k`.**

  *Why cross-`k` pruning is unsound* (single demand `D=10`): `v_i` cheap (PRC=2, cost=0.1,
  max=4), `w` expensive (PRC=10, cost=100). Node `u=(i,4)` maxed: C=8, cost=0.4. Node `v=(i,0)`:
  C=7, cost=0.5. `u` looks dominant, but it is out of cheap-`v_i` headroom and must buy `w`
  (total 100.4); `v` still has 4 cheap replicas and completes at 0.7. Pruning `v` by `u` discards
  the optimum 100×. The headroom `u` spent is exactly what made `v` better — so headroom must be
  part of the dominance key.

The per-`(i,k)` Pareto frontier over `(cost, capacity-vector)` is exactly the float-exact form of
the underlying DP (no capacity grid, so no discretization error). Note PRC-dependence: the cost
*order* survives any PRC change, but a precomputed *dominance* frontier is only valid while PRC is
stable.

---

## 6. Key design decisions

- **Objective is pure min-cost subject to vector coverage.** Confirmed: satisfy every analyzer's
  demand; no scalarization.
- **Score is a tie-break only**, applied among equal-cost feasible optima (heap secondary key in
  the online path; explicit equal-cost gather on the precompute path). Preserves current behavior
  in the tie region. Overall behavior will differ from today's greedy *exactly where greedy was
  cost-suboptimal* (the Y/Z/X case) — that divergence is the intended improvement, not a
  regression.
- **Deterministic output required.** With score-only ties still possible, add a final
  deterministic key (e.g. fewest replicas, then lexicographic on counts) so the chosen allocation
  does not flap between equal-cost/equal-score optima across reconciles (pod thrash).

---

## 7. Multi-analyzer note / open items

- The vector demand `D = (D_a)` and PRC matrix `PRC_{i,a}` make `capacity` a vector; the search
  and dominance compare it componentwise. State-space / Pareto-frontier dimensionality grows with
  the analyzer count `A` (curse of dimensionality), but `A` and variant counts are small in
  practice.
- **Where do analyzer scores come from in the multi-analyzer engine, and is the conjunction the
  true model?** The current engine score-weights capacity as a heuristic; this design treats that
  weighting as *not* the objective. If a future requirement couples the per-analyzer constraints
  (rather than a pure AND), the formulation changes — revisit then.
- Disaggregated (P/D) models: allocation is per model-role today (`allocateForModelPaired` /
  `costGreedyRolePick`). The exact allocator replaces the per-role *scale-up* pick with an exact
  per-role cover; cross-role joint-utilization trimming is a separate concern (out of scope for
  the first cut — see the coding plan).

---

## 8. Correctness summary

- First feasible allocation in cost order = global min cost (edge costs ≥ 0).
- Canonical 2-hop tree enumerates each allocation exactly once; zero-cost advance edges terminate
  (index strictly increases, ≤ `m` per allocation).
- Score tie-break is a sound lexicographic secondary objective (cost ↑, then score-pref, then a
  deterministic key).
- Dominance pruning (if added) never removes the optimum when keyed to `(i,k)` with the two-part
  `(cost ≤, capacity ≥)` rule; cross-`k` pruning is unsound (§5.3).
- Bounded by exhaustive search in the worst case; typically far less via early stop (+ optional
  dominance).

---

## 9. Dynamic reallocation (extension)

The core solver allocates from scratch. In production the optimizer runs **every reconcile from a
current allocation `cur`** (feasible, `C_cur ≥ D`) against a possibly-changed demand `D` —
covering RequiredCapacity (RC, scale-up) or shedding SpareCapacity (SC, scale-down). This section
extends the solver to that setting.

> **Forward-looking.** The first implementation (see the coding plan) is the static solver only.
> The recommended first reallocation step is §9.3's two *monotone* presets; swaps and hysteresis
> (§9.4–9.5) come later.

### 9.1 The target is the static optimum — it does not depend on `cur`

The min-cost feasible allocation is a function of `(costs, PRC, D)` only. So "find a better
allocation if one exists" = "is the static optimum for the current `D` cheaper than `cur`?" The
global optimum **subsumes** any local "I drifted into several small cheap replicas, but one big
efficient replica is cheaper" improvement — that drift is exactly the integrality-gap miss the
solver corrects. No separate local-improvement / swap search is needed for correctness.

**Incumbent-bounded recompute.** Feed `cost(cur)` as an upper bound: scan the cost-ordered
sequence only up to `cost(cur)`; the first feasible allocation below it is the improvement (and is
globally optimal); if none exists below it, `cur` is already optimal. With the cached cost order:
`D↑` (componentwise) → resume the scan forward from the last stop; `D↓` or mixed → rescan from 0,
bounded by `cost(cur)`. Cheap either way — no heap rebuild.

### 9.2 One solver, three bound presets — `[lo_i, hi_i]` per variant

The static search ranges counts over `[0, max_i]`. Replace that with a per-variant lower/upper
bound and every operation falls out of the **same** cost-ordered search (counts simply range over
`[lo_i, hi_i]`):

| operation | `lo_i` | `hi_i` | migration shape |
|---|---|---|---|
| scale-up, cover RC (add-only) | `cur_i` | `max_i` | monotone **add** |
| scale-down, shed SC (remove-only) | `min_i` | `cur_i` | monotone **remove** |
| bounded modification (window) | `max(min_i, cur_i−n_i)` | `min(max_i, cur_i+n_i)` | window around `cur` |
| full reallocation | `min_i` | `max_i` | unrestricted (swaps) |

- **RC scale-up** works with no algorithm change beyond `lo_i = cur_i` (equivalently: cover the
  residual deficit with additions; result `new ≥ cur`).
- **SC scale-down** is the only "minor change": clamp `hi_i = cur_i`. The solver then returns the
  min-cost cover reachable without adding — the best pure-removal target.
- `minReplicas` is enforced by `lo_i = min_i`. The existing "keep the cheapest variant at ≥1"
  positional rule is a *separate* constraint on the solver, not automatic from the bounds.

### 9.3 Migration paths

- **Monotone presets (RC add-only, SC remove-only) — the recommended first step.** Both are
  trivially safe with **no transient over-provisioning**: add-only keeps `new ≥ cur` (capacity
  only grows, every intermediate ≥ D); remove-only keeps `new ≤ cur` (every intermediate ⊇ `new`
  ≥ D). They map exactly onto the engine's RC/SC signals and need no new transient-capacity
  machinery.
- **Swaps (windowed / full) — make-before-break.** Add every replica in `target \ cur` first
  (capacity grows → feasible), reaching `peak = componentwise-max(cur, target)`; then remove every
  replica in `cur \ target` (each intermediate ⊇ `target` ≥ D). All intermediates feasible; the
  cost transiently spikes to `cost(peak)` — the price of zero-downtime migration. A **greedy
  interleave** (remove a redundant replica whenever the result stays ≥ D, else add a needed one)
  lowers the peak, never deadlocks (once `target` is fully added, a safe removal always exists),
  and stays feasible throughout.
- **Irreducible churn = `|cur △ target|`** (symmetric difference). Ordering changes only the peak
  and feasibility, not the churn count; the only way to reduce churn is to choose a *closer*
  target (§9.4).

### 9.4 When to switch — switching cost is the new content

Static allocation had no notion of "where you were"; reallocation does (pod churn, warmup, KV-cache
loss, transient over-provisioning, and **thrashing** when `D` oscillates around a threshold and the
optimum flips between near-equal-cost allocations).

**Migration-penalty objective** (the principled form of hysteresis): instead of pure min-steady-
cost, pick the allocation maximizing net benefit
```
maximize   (cost(cur) − cost(a))  −  λ · penalty(cur, a)     over feasible a for D
```
where `penalty` is churn `|cur △ a|` or the transient peak. `λ = 0` → always chase the global
optimum; large `λ` → sticky / stay put. With a penalty term the *first* feasible-below-cur is no
longer automatically the answer (a slightly-less-cheap allocation closer to `cur` can net better),
so enumerate the cheaper-than-`cur` prefix and pick the best net benefit. Add a debounce /
persistence window on top. (This is exactly the `CS` "cost-save" threshold floated in issue #1251 /
PR #1252 discussion.)

### 9.5 The "deallocate 25%, reallocate back" heuristic

A churn-budgeted partial restart — the windowed solve (§9.2) sized to a ~25% churn budget rather
than a per-variant radius. Its value over a tiny window: it can escape a badly-drifted allocation
(free enough budget that the re-cover solver picks a genuinely different, better mix) without the
100% churn of a from-scratch restart. It is **target-finding only** — compute `target` via the
dealloc→realloc reasoning, then execute the `cur → target` transition with make-before-break; the
literal tear-down-then-rebuild order is not how it runs. Define "25%" as the window/churn budget,
not a separate deallocation rule, so it collapses back into the bounded-modification solver.

### 9.6 Scale-up / scale-down asymmetry

`D↑` can make `cur` infeasible → add-first (always safe, no SLO risk). `D↓` leaves `cur`
over-provisioned → pure remove, lowest risk. A *shape* change (one analyzer up, another down)
forces a variant **swap** — the one case where make-before-break's transient peak actually bites.

### 9.7 First-cut recommendation

Implement the two **monotone presets** (RC add-only via `lo=cur`; SC remove-only via `hi=cur`) on
top of the static solver. They cover the typical RC/SC reconcile, reuse the cost-ordered search
unchanged, and carry **no** transient-capacity risk. Defer windowed/swap reallocation,
migration-penalty hysteresis, and the 25% heuristic until the monotone path is proven.
