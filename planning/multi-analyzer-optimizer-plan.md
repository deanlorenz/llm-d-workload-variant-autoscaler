# Multi-Analyzer Optimizer — Per-Variant Slice + Paired Allocation Plan

> **Status: IN PROGRESS** — Item 1 of `planning/PR1113-review.md`. Three commits landed
> on top of `a93bc5dc` (1.1 struct, 1.2 single-variant helpers, 1.3 CostAware
> non-disaggregated path). Three new commits pending: paired helpers + CostAware
> disaggregated path (1.4), Greedy migration (1.5), cleanup (1.6).
>
> **Plan rewritten 2026-06-03** after design discussion on disaggregated-model
> allocation. Earlier 1.4 work in `git stash` should be discarded — the role-budget
> split approach was wrong; new approach is paired (P, D) allocation. See § "Why
> the rewrite" and § "Considered and rejected: compound variant".
>
> Cross-rebase target: `multi-analyzer-threshold@b8b823b0` (PR #1228) after final
> commit lands.

---

## Context

The engine combines per-analyzer results into a single `*AnalyzerResult` via
`combineAnalyzerResults` (deleted upstream by PR #1225) and used to pass it to the
optimizer through `ModelScalingRequest.Result`. This PR replaces the engine-side
combine with a **per-analyzer slice flowing through to the optimizers**. Each
optimizer reads `[]NamedAnalyzerResult` and applies shared free functions over the
slice. No new public interface, no helper object, no `Combiner`. Slice mutated
in place during allocation. Pickers (cost-greedy for `CostAwareOptimizer`,
fair-share-bounded for `GreedyByScoreOptimizer`) are the only optimizer-specific
divergence.

Scale-down processes each model independently — no shared scarce resource exists
during scale-down (cluster GPU budget only grows), `SC_i ≥ 0` is local to each
model's slice, no per-(variant) cross-model `MinReplicas` floor.

---

## Why the rewrite (2026-06-03)

The original architecture treated allocation as per-role-independent: split the
target into role budgets, allocate each role separately. That broke for
disaggregated (P/D) models when the agent landed 1.4. Two failures surfaced:

1. **Allocating prefill replicas reduced model-level `Remaining` to 0**, blocking
   subsequent decode allocation via the `bottleneckReplicas` cap. (Specific failure
   case in `plan__optimizer-pd-design.md`.)

2. **Conceptual error.** The model-level "Remaining" as additive sum of role
   demands isn't actionable — model satisfaction is gated by the bottleneck role,
   not by an additive sum. 100% D + 0% P = 0% model, not 50%.

The corrected math:

- Each variant carries at most one role; variants partition cleanly by role.
- Per-variant `PerReplicaCapacity` and `TotalDemand` are role-aware (analyzer
  decides the mapping; sat_v2 counts only prefill tokens for P-variants, etc.).
- The **same model demand `d` mapped to multiple roles is not the same as mapped
  to multiple non-role variants**. Roles are linked through `d` (P(d) and D(d)
  both derive from the same underlying traffic), whereas non-role multi-variant
  splits the demand arbitrarily.
- Linearity invariant holds **at role scope** for any analyzer. It does NOT hold
  in general at model scope when roles are involved (sat_v2 happens to be additive
  but only in steady state; under partial allocation it breaks).
- **Allocation must commit `(n_P, n_D)` paired increments** — adding prefill
  capacity alone is fictional progress because the model still bottlenecks on
  decode. Each paired commit serves a `p_step` worth of P-side demand and the
  matching `α × p_step` of D-side demand (same underlying traffic).

This rewrite reflects that. The existing 1.1–1.3 commits are kept (they're correct
for non-disaggregated models, which is the only case any current test exercises).
New commits add the paired path for disaggregated models and complete the
migration.

---

## Architectural decisions (locked)

### Per-variant slice contract

`pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult` is the
per-model input the optimizer reads. Saturation is always the first entry
(keeper of variant identity until the future pre-analysis-extraction PR removes
that responsibility). Other enabled analyzers follow in registration order.

```go
type NamedAnalyzerResult struct {
    Name      string
    Result    *interfaces.AnalyzerResult  // engine-calibrated; never mutated
    Remaining float64                     // working RC counter (model-scope, or P-side for disaggregated)
    Spare     float64                     // working SC counter (model-scope; non-disaggregated only)
    RoleSpare map[string]float64          // working SC counter per role (disaggregated only)
    Score     float64                     // analyzer score weight (from AnalyzerScoreConfig)
}
```

**Working counter scope:**

- **Non-disaggregated models** (no roles, all variants are `""` or `"both"`):
  `Remaining`/`Spare` are at **model scope** in model-level units. Initialized
  from `Result.RequiredCapacity`/`Result.SpareCapacity`. `RoleSpare` is nil.
- **Disaggregated models** (variants partition into `prefill` / `decode`):
  - `Remaining` is at **P-side scope** in P-units. Initialized from
    `Result.RoleCapacities[prefill].RequiredCapacity`. D-side is implicit via
    α (see below). Paired scale-up steps decrement `Remaining` by `p_step`
    per commit.
  - `RoleSpare[role]` is per-role spare in role units. Initialized from
    `Result.RoleCapacities[role].SpareCapacity` for each role present.
    Role-iterated scale-down decrements `RoleSpare[role]` per role-scoped
    deallocation.
  - Model-level `Spare` is unused for disaggregated models.

The optimizer detects disaggregation by checking whether any variant in
`saturationEntry().VariantCapacities` has a role other than `""`/`"both"`.

### Linearity invariant (the contract the helpers depend on)

**At role scope** (or model scope for non-disaggregated): adding `n` replicas of
variant `v` reduces analyzer `i`'s `Remaining` by exactly `n × PerReplicaCapacity_i[v]`.
Symmetric for removal. Per-variant `Total*` fields are sums over per-variant
primitives (enforced by `internal/engines/aggregation/` helpers from PR #1228).
An analyzer that violates the invariant silently breaks the optimizer's
allocation — analyzers must use the helpers (or produce identical math).

**At model scope for disaggregated models**, the invariant does NOT hold: model
satisfaction is bottleneck-gated, not additive. The optimizer never operates at
model scope for disaggregated models — only at role-pair scope via the paired
helpers below.

### Per-analyzer α coupling

For disaggregated models, each analyzer's α is the D:P demand ratio derived from
its role-scope totals:

```
For each analyzer i:
    P_i = r_i.RoleCapacities[prefill].TotalDemand
    D_i = r_i.RoleCapacities[decode].TotalDemand

    if P_i > 0 and D_i > 0:                   # standard case
        α_i = D_i / P_i
        tracks_P, tracks_D = true, true
    elif P_i > 0 and D_i == 0:                # analyzer doesn't track decode demand
        α_i = 0
        tracks_P, tracks_D = true, false
    elif P_i == 0 and D_i > 0:                # analyzer doesn't track prefill demand
        α_i = 1                                # default fallback (Dean's rule)
        tracks_P, tracks_D = false, true       # PRC_P_i is broken; skip P-side
    else:                                      # analyzer doesn't track either
        skip this analyzer entirely from paired bottleneck calculations
```

α_i is computed once at the start of the optimizer's iteration (or on demand
inside helpers) and held constant during allocation. Per-iteration recompute is
not needed: the linearity at role scope guarantees that allocation maintains the
ratio.

**Future direction (out of scope):** analyzer publishes α (or `D(p)` as a
function) directly on `RoleCapacities`, supporting non-linear couplings or
vector demands. For now we derive scalar α from totals.

### Engine writes RC/SC; optimizer reads

After PR #1228 merges, the engine post-step (`applyUniversalThreshold`) is the
sole writer of `RC`/`SC` at every scope (model + per-role). Analyzer-written
values are discarded. The optimizer reads engine-calibrated values per analyzer;
per-analyzer threshold overrides are honored upstream, so the optimizer doesn't
re-resolve them.

### Pipeline helpers — `internal/engines/pipeline/analyzer_helpers.go`

**Single-variant helpers (non-disaggregated):**

- `needsScaleUp(s)` — any-up gate: `Remaining_i > 0` for at least one analyzer.
- `needsScaleDown(s)` — all-down gate: `Spare_i > 0` for every analyzer.
- `bottleneckReplicas(s, v)` — `max_i ceil(Remaining_i / PRC_i[v])`; cold-start
  guard for `PRC=0`.
- `safeRemovalReplicas(s, v)` — `min_i floor(Spare_i / PRC_i[v])`.
- `applyAllocation(s, v, n)` — subtracts `n × PRC_i[v]` from each analyzer's
  `Remaining`; clamps to 0. Does NOT touch `Result.RequiredCapacity`.
- `applyDeallocation(s, v, n)` — symmetric for `Spare`. Does NOT touch
  `Result.SpareCapacity`.
- `saturationEntry(s)` — looks up saturation by name (variant-metadata keeper).
- `PickVariantFn` — returns `(variant, capN)`.
- `allocateForModel(...)` — generic scale-up inner loop using `pick`.

**Paired scale-up helpers (disaggregated):**

- `analyzerAlpha(r)` — computes α per the rules above, returns `(α, tracksP, tracksD)`.
- `bottleneckReplicasPaired(s, vP, vD, p_step)` — given a candidate p_step,
  returns `(n_P, n_D)` such that:
  ```
  n_P = max_i over (i with tracks_P) of ceil(p_step / PRC_i[vP])
  n_D = max_i over (i with tracks_D) of ceil(α_i × p_step / PRC_i[vD])
  ```
  Cold-start guards on `PRC=0`. Returns `(0, 0)` if no analyzer tracks either side.
- `applyAllocationPaired(s, vP, n_P, vD, n_D)` — for each analyzer i:
  ```
  served_i = min(n_P × PRC_i[vP], n_D × PRC_i[vD] / α_i)   # in P-units
  Remaining_i -= served_i; clamp to 0
  ```
  (Skip analyzers that don't track both sides; their `Remaining` stays in role
  scope they do track.)
- `PickPairFn` — returns `(vP, vD, capN_P, capN_D)`. The `capN_*` are headroom
  caps (max-replicas, GPU budget, etc.); `bottleneckReplicasPaired` provides the
  per-analyzer demand-driven cap.
- `allocateForModelPaired(...)` — generic scale-up inner loop driving paired
  commits via `pick`.

**Role-iterated scale-down helpers (disaggregated):**

Scale-down does NOT pair. **P and D are independent at scale-down — analogous to
how separate models are independent at scale-down.** Under the assumption that a
disaggregated model has no role-independent variants alongside its P/D variants,
removing prefill replicas only affects P-side supply (D unchanged) and vice
versa. The underlying model demand `d` is set by the workload, not by replica
count, so trimming one role's slack doesn't reduce `d`. Each role's
`SpareCapacity > 0` invariant is the only constraint, enforced per role.

This matches PR #1237's upstream fix to `costAwareScaleDown` (see § "Upstream
interactions" below).

- `safeRemovalReplicasForRole(s, v, role)` — `min_i floor(s[i].RoleSpare[role] / PRC_i[v])`.
  Reads per-role working spare from the slice. Cold-start guards on `PRC=0`.
- `applyDeallocationForRole(s, v, role, n)` — for each analyzer i:
  `s[i].RoleSpare[role] -= n × PRC_i[v]`; clamp to 0.
- `variantsForRole([]VariantCapacity, role) []VariantCapacity` — exact-match
  filter (empty role canonicalized to `RoleBoth`).

Disaggregated scale-down loop (per optimizer):
```
for each role with any-analyzer RoleSpare[role] > 0 (gate per role):
    variants_role = variantsForRole(satEntry.VariantCapacities, role)
    sorted = sortByCostDesc(variants_role)
    cheapest = findCheapestVariant(variants_role)
    for vc in sorted:
        if no analyzer has RoleSpare[role] > 0: break
        # cheapest-variant protection scoped to this role
        # minReplicas floor enforced
        n = min(safeRemovalReplicasForRole(s, vc.VariantName, role), removable_in_role)
        if n <= 0: continue
        applyDeallocationForRole(s, vc.VariantName, role, n)
        targets[vc.VariantName] -= n
```

The all-down gate per role is "every analyzer's `RoleSpare[role]` > 0" (consistent
with `needsScaleDown` semantics for non-disaggregated). For the single-analyzer
case (current production: only sat_v2), this reduces to "this role's spare > 0",
exactly matching PR #1237's gate.

These operate on `[]NamedAnalyzerResult`. Distinct concern from
`internal/engines/aggregation/` (introduced by PR #1228) which operates on
`[]VariantCapacity` for analyzer authors.

### Pickers

**Single-variant (non-disaggregated):**

- **CostAware** (`costGreedyPick`): cheapest-first by cost-efficiency
  (`Cost / PRC`); cap is unlimited (`math.MaxInt`); GPU budget honored via
  `stateMap`/`available`. Already landed in 1.3.
- **Greedy** (`fairSharePick`): fair-share-bounded; cap is the analyzer's
  fair-share target ÷ `PRC[v]`. To land in 1.5.

**Paired (disaggregated):**

- **CostAware** (`costGreedyPickPaired`): cheapest combined cost-efficiency for
  the (vP, vD) pair. Sort P-variants by `Cost_P / PRC_P`, D-variants by
  `Cost_D / PRC_D`, pair cheapest-of-each. Caps from max-replicas headroom on
  each side.
- **Greedy** (`fairSharePickPaired`): fair-share-bounded for the pair. Fair-share
  target is in P-units; pair-cap derived from per-analyzer α. To land in 1.5.

### Optimizer dispatch

Each optimizer's per-request loop:

```go
for _, req := range requests {
    satEntry := saturationEntry(req.AnalyzerResults)
    if satEntry == nil { continue }
    // ...
    if isDisaggregated(satEntry.VariantCapacities) {
        // Use paired helpers + paired picker
        scaleUpDisaggregated(ctx, req, ...)
    } else {
        // Use single-variant helpers + single picker
        scaleUpStandard(ctx, req, ...)
    }
}
```

`isDisaggregated(vcs)` returns true if any `vc.Role` is non-empty and not `"both"`.

---

## Roadmap commits

Each commit compiles, passes `make test`, is DCO-signed.

### 1.1 ✅ `27a15e2e` — pipeline: NamedAnalyzerResult + AnalyzerResults field

Landed against `a93bc5dc`. Adds:

- `pipeline.NamedAnalyzerResult{Name, Result, Remaining, Spare, Score}`.
- `pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult`.
- Engine populates both `Result` (legacy combine, until 1.6 drops it) and
  `AnalyzerResults` (saturation-first, then enabled non-saturation analyzers in
  config order). `Remaining`/`Spare` initialized from `Result.RequiredCapacity`/
  `SpareCapacity` for now (model scope).

**Refinement needed in 1.4:** when disaggregation is detected at engine post-step,
`Remaining` and `Spare` initialize from `Result.RoleCapacities[prefill]` instead
of model-level. Either modify the engine init code or have the optimizer
re-initialize at the start of its dispatch (cleaner — the engine doesn't need
to know about the optimizer's working scope).

### 1.2 ✅ `3b21c347` — pipeline: single-variant helpers in `analyzer_helpers.go`

Landed against `a93bc5dc`. The 8 single-variant helpers + 21 specs. Helpers
operate on `Remaining`/`Spare`, never mutate `Result`. Helpers intentionally
unused by optimizers at this commit.

### 1.3 ✅ `d35aa532` — CostAware migration (non-disaggregated path)

Landed. `CostAwareOptimizer` reads `req.AnalyzerResults` via `saturationEntry()`;
gates via `needsScaleUp`/`needsScaleDown`; uses `allocateForModel` +
`costGreedyPick` for scale-up; `safeRemovalReplicas` + `applyDeallocation` loop
for scale-down. Greedy scale-down call site updated to new signature.
`req.Result` kept for `buildDecisionsWithOptimizer` reason strings (cleaned in
1.6).

**Latent gap surfaced by the rewrite:** 1.3 has no disaggregated path. For
disaggregated CostAware, allocations would interleave P and D randomly without
pairing. Tests don't exercise this case. Fixed in 1.4.

### 1.4 ⏳ — Disaggregation support: paired scale-up + role-iterated scale-down

Files:

- `internal/engines/pipeline/optimizer_interfaces.go`: add
  `RoleSpare map[string]float64` field to `NamedAnalyzerResult`.
- `internal/engines/pipeline/analyzer_helpers.go`: add
  - `isDisaggregated([]VariantCapacity) bool` utility.
  - `analyzerAlpha(r) → (α, tracksP, tracksD)`. **α is computed from
    `r.RoleCapacities[D].TotalDemand / r.RoleCapacities[P].TotalDemand`** — workload
    invariant, not derived from RC. RC is the gap relative to current supply;
    using it for α would tie α to allocation state.
  - Paired scale-up helpers: `bottleneckReplicasPaired`, `applyAllocationPaired`,
    `PickPairFn`, `allocateForModelPaired`.
  - Role-iterated scale-down helpers: `safeRemovalReplicasForRole`,
    `applyDeallocationForRole`, `variantsForRole`.
- `internal/engines/pipeline/analyzer_helpers_test.go`: ~25 specs covering
  α edge cases (P=0, D=0, both=0), paired bottleneck across multiple analyzers
  with different α, per-analyzer served accounting on paired allocation,
  role-iterated scale-down with all-down gate per role, equivalence with
  PR #1237's per-role end result for the single-analyzer case.
- `internal/engines/pipeline/cost_aware_optimizer.go`: dispatch on
  `isDisaggregated(satEntry.VariantCapacities)`.
  - Disaggregated scale-up: `costGreedyPickPaired` + `allocateForModelPaired`.
  - Disaggregated scale-down: per-role loop using `safeRemovalReplicasForRole`
    + `applyDeallocationForRole` (matches PR #1237's role-iteration pattern).
  - Non-disaggregated path unchanged.
- `internal/engines/pipeline/cost_aware_optimizer_test.go`: add disaggregated
  scale-up and scale-down specs.
- Engine `runAnalyzersAndScore` (or wherever the slice is initialized): when
  `RoleCapacities` is non-empty, initialize `Remaining` from
  `RoleCapacities[prefill].RequiredCapacity` and `RoleSpare[role]` from
  `RoleCapacities[role].SpareCapacity` for each role. Non-disaggregated init is
  unchanged. The optimizer can also do this at dispatch time — pick whichever
  is cleaner.

**Stashed 1.4 (Greedy) work is dropped.** The role-budget-split approach was
wrong; restart Greedy from scratch in 1.5 using paired scale-up + role-iterated
scale-down.

### 1.5 ⏳ — Greedy migration (both paths)

`GreedyByScoreOptimizer` migrated to per-analyzer slice using both single and
paired helpers based on disaggregation.

- Compute `fairShareValue(priority, s)` — analyzer-weighted demand. Used for
  both fair-share bounding (Greedy's per-model target) and scoring.
- Non-disaggregated: `fairSharePick` (existing single-variant picker, fair-share
  cap = `ceil(target / PRC[v])`) + `allocateForModel`.
- Disaggregated: `fairSharePickPaired` (per-pair fair-share cap) +
  `allocateForModelPaired`.
- The existing `allocateByRole` (role-budget split) is removed — paired path
  obsoletes it.
- Update `greedy_score_optimizer_test.go` fixtures with `withSatEntry`.

### 1.6 ⏳ — Cleanup (final)

| Item | Status post-rebase |
|---|---|
| Delete `combineAnalyzerResults` | Already done upstream (registration PR). |
| Delete `enabledAnalyzerResult` | Already done. |
| Delete `engine_combine_test.go` | Already done. |
| Drop `ModelScalingRequest.Result` field | Pending in 1.6. |
| Drop `AnalyzerResult.Score` field | Pending in 1.6. |
| Rename `runAnalyzersAndScore` → `runAnalyzers` | Pending in 1.6. |
| Drop saturation-only score-compute loop in engine | Pending in 1.6. |
| Final dev-guide commit | Pending. |

`buildDecisionsWithOptimizer` reason-strings that still reference
`req.Result.RequiredCapacity` / `SpareCapacity` cleaned up here.
`Utilization` plumbing for `VariantDecision` stays (reads `vc.Utilization` per
variant — unchanged).

**Code cleanup carried from 1.3 review:** add a comment on the `removed` flag
in `costAwareScaleDown`'s outer `for needsScaleDown(s)` loop. The flag breaks
the outer loop when a full inner sweep makes no progress, guarding against an
infinite loop where some analyzer's `Spare > 0` but no variant can give up
more replicas (all at `minReplicas` floor, or PRC mismatch makes
`safeRemovalReplicas` return 0 for every variant). The behavior is correct;
the comment makes the invariant explicit. Suggested wording:

```go
// removed flag prevents an infinite loop: needsScaleDown can hold
// (some Spare_i > 0) while no variant has remaining capacity to
// give up (all at minReplicas, or PRC mismatched). Break when a full
// sweep makes no progress.
```

---

## Considered and rejected: compound-variant approach

Concept: treat (vP, vD) as a single compound variant CV with derived `Cost`,
`PRC`, `MaxReplicas`. Existing single-variant helpers work unchanged.

**Drawbacks:**

1. **Fractional decode replicas.** 1 unit CV = 1 prefill + α decode. For α=0.3,
   allocating 5 CV units means 5 prefill + `ceil(5×0.3)=2` decode. Capacity
   served is `5 × min(PRC_P, PRC_D/α)` but cost paid is
   `5 × Cost_P + 2 × Cost_D` — rounding overhead distorts cost-greedy ordering.

2. **Compounds share underlying variants.** If vP has 5-replica max and
   CV1=(vP,vD1), CV2=(vP,vD2), allocating to CV1 reduces vP's pool for CV2.
   `CV.MaxReplicas` can't be a static field; it shrinks dynamically as
   allocations happen. Same for pending-replicas accounting.

3. **Per-analyzer PRC and α stay per-physical-variant.** `CV.PRC` isn't a single
   scalar — different analyzers see different PRC for vP and different α. The
   compound layer doesn't collapse this dimension; just hides it.

4. **Multiple-pair coexistence.** With 2 P-variants × 2 D-variants you have 4
   candidate CVs. Picking among them isn't independent — they share underlying
   replicas. Standard cost-sort over CVs gives wrong answers when allocations
   interfere.

The compound abstraction trades paired-helper complexity for compound-state
complexity, AND introduces rounding distortions that break cost-greedy ordering.
Net negative. Stuck with paired helpers.

---

## Cross-rebase mechanics (after 1.6 lands locally; before push)

### Target

Rebase the 1.1–1.6 stack onto `multi-analyzer-threshold@b8b823b0` (PR #1228 head).

That picks up in one hop:

- Registration plumbing (`66001d47`): `analyzers []analyzerEntry` +
  `analyzersSnapshot` + `started bool` + race-fix; `RegisterAnalyzer` panics on
  duplicate name and on late registration.
- Combine deletion (registration PR): `combineAnalyzerResults`,
  `enabledAnalyzerResult`, `sumTotalCapacity`, `engine_combine_test.go` —
  already gone upstream.
- Threshold post-step (`b8b823b0`): `applyUniversalThreshold` +
  `resolveThresholds`; engine writes RC/SC for saturation and every role;
  per-analyzer threshold overrides honored.
- Aggregation helpers (`internal/engines/aggregation/`).
- Sat_v2 simplification: drops in-analyzer RC/SC; uses aggregation helpers;
  populates `TotalAnticipatedSupply` and per-role `TotalAnticipatedSupply`.

### Expected conflicts

| File | Conflict scope |
|---|---|
| `internal/engines/saturation/engine_v2.go` | **Major.** 1.1's combine-and-collect rewrite collides with threshold's post-step-and-discard rewrite. Manual reshape — keep threshold's pattern, layer 1.1's slice collection on top. |
| `internal/engines/saturation/engine_combine_test.go` | Both delete; trivial. |
| `internal/engines/pipeline/optimizer_interfaces.go` | Clean. |
| `internal/engines/pipeline/analyzer_helpers.go` + test | Clean. |
| `internal/engines/pipeline/cost_aware_optimizer.go` | Likely clean. |
| `internal/engines/pipeline/greedy_score_optimizer.go` | Likely clean. |

### `runAnalyzersAndScore` reshape during rebase

The signature evolution:

```
optimizer 1.1 (today):  (...) ([]NamedAnalyzerResult, *AnalyzerResult, error)
threshold tip:          (...) (*AnalyzerResult, error)               // sat-only-calibrated
post-rebase target:     (...) ([]NamedAnalyzerResult, error)         // slice only; sat at slice[0]
```

Engine-side body (after rebase): run saturation via `runV2AnalysisOnly`, apply
threshold post-step to saturation, run other registered analyzers and **collect
results** (instead of threshold's discard) into `[]NamedAnalyzerResult`, apply
post-step per analyzer, return slice.

`req.Result` becomes a transitional pointer at `slice[0].Result` (saturation's
calibrated entry) until 1.6 drops the field.

### Rebase steps

```
git -C multi-analyzer-optimizer fetch origin multi-analyzer-threshold
git -C multi-analyzer-optimizer rebase b8b823b0
# Resolve engine_v2.go conflict per the reshape above.
git rebase --continue

# Verify after rebase:
gofmt -l ./internal/... ./pkg/... ./cmd/...
go vet ./...
go build ./...
make test
go test -race ./internal/engines/saturation/...
git log b8b823b0..HEAD --format='%h %s%n%b' | grep -E '^[0-9a-f]+|Signed-off-by'  # DCO
```

Force-push policy: `--force-with-lease`, only after all commits land locally
and verify clean. State reason. **Do NOT push without explicit Dean confirmation
per CONVENTIONS.**

---

## Verification gates

Each commit must satisfy:

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty output.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- DCO sign-off.

Final pre-push gate after cross-rebase: `go test -race ./internal/engines/saturation/...`
clean.

---

## Upstream interactions

### PR #1237 — `fix(optimizer): role-aware scale-down for disaggregated models`

Open PR by ev-shindin (2026-06-04). Targets current main; addresses the same
P/D scale-down problem we're solving but on the **legacy single-analyzer path**
(`req.Result`-based, before our slice migration).

Evgeny's approach for `costAwareScaleDown`:
- When `RoleCapacities` is non-empty, iterate roles independently. Per role:
  shed against `RoleCapacities[role].SpareCapacity`, using only variants whose
  `Role` matches exactly (`variantsForRole`). Skip saturated roles.
  Cheapest-variant protection scoped per role.
- When `RoleCapacities` is empty, model-level shed unchanged.

**End-result equivalence with our role-iterated scale-down (single-analyzer
case):** in current production only sat_v2 produces RC/SC, so the per-analyzer
slice has one entry. Both walks: per role, sort by cost desc, gate on positive
role spare, skip saturated, cheapest-variant-at-1 protection scoped per role,
`floor(spare / PRC)` removal cap, `minReplicas` floor. On Evgeny's canonical
example (prefill saturated, decode has 20000 spare, 1 GPU/replica, decode
PRC=10000): prefill stays at 2; decode sheds floor(20000/10000)=2 → decode
3→1. Same outcome.

**Multi-analyzer extension (future).** Our slice version extends the per-role
gate to "every analyzer agrees this role has spare" (all-down). The
single-analyzer case reduces to "this role has spare," matching his fix
exactly.

**No need to depend on his code.** We re-implement the concept on the
per-analyzer slice path. The `variantsForRole` utility (5 lines) is
straightforward to reproduce.

**Cross-rebase impact when PR #1237 lands on main:**
- Registration (PR #1225) rebases onto new main, picking up Evgeny's fix.
- Threshold (PR #1228) rebases onto new registration tip, transitively.
- Our cross-rebase target shifts; the `costAwareScaleDown` Evgeny modified
  was already migrated by our 1.3 to the slice path. Resolution: keep our
  slice migration, adopt the role-iteration pattern (1.4 adds it anyway).
- Net effect: 1.4's role-iteration work is the same regardless of merge order;
  only rebase mechanics differ.

### Engine model-level `SpareCapacity` for disaggregated models — known bug

Today's engine post-step ([`applyUniversalThreshold`](internal/engines/saturation/engine_v2.go))
computes `r.SpareCapacity = max(0, r.TotalSupply - r.TotalDemand/scaleDown)`
where `r.TotalSupply` and `r.TotalDemand` are model-level additive sums across
all roles (sat_v2's Phase 3 totals). **For disaggregated models this is wrong**
— prefill and decode tokens aren't fungible, so additive Spare conflates roles
that should be treated independently. The bug surfaces when any consumer reads
`r.SpareCapacity` for a disaggregated model: it looks like there's room to
shed when only one role has slack.

PR #1237 works around this by ignoring `r.SpareCapacity` for disaggregated
models and reading per-role spare from `r.RoleCapacities[role]` instead. Our
optimizer does the same.

**Once this PR (multi-analyzer-optimizer) ships**, no consumer reads
`r.SpareCapacity` for disaggregated models. The buggy additive computation
becomes latent. **It should be removed or replaced** at that point — either
zero it out for disaggregated, drop it entirely, or redefine to something
correct (e.g., `min(role spare)`). Tracked as a post-merge follow-up
(see § "Open items"). Same applies to model-level `r.RequiredCapacity` for
disaggregated; engine post-step `RC` is also additive and would be unread by
our optimizer.

---

## Coordination

- **PR #1225 (`multi-analyzer-registration`)** — base for cross-rebase.
  Stable. Awaiting reviewer.
- **PR #1228 (`multi-analyzer-threshold`)** — cross-rebase target. Awaiting
  reviewer.
- **PR #1237 (`fix/role-aware-scaledown`)** — see § "Upstream interactions"
  above. Cross-rebase will fold it in.
- **`engine-queue-fix`** — blocked on PR #1225 merging.
- **PR #1113** — superseded; will be closed.

This branch does **not** depend on any PR merging before continuing 1.4–1.6
locally.

---

## Open items

- **α from analyzer (future):** today the optimizer derives α per analyzer
  from `RoleCapacities` totals. Future direction: analyzer publishes α (or
  `D(p)` as a function) directly. Supports vector demands and non-linear
  couplings.
- **Pre-analysis extraction (future):** sat_v2 today carries variant identity
  (Cost, AcceleratorName, Role, replica counts) that any analyzer or the
  optimizer may need. The deferred future PR extracts that into a common
  pre-analysis stack so sat_v2 becomes one of N peers. Out of scope for this
  PR; `saturationEntry()` helper is a TODO marker.
- **Per-analyzer observability metrics** (Prometheus gauges labeled by
  `analyzer_name`): follow-up after this PR merges. Already noted in
  `session/CURRENT.md` "Issues to Open".
- **Mixed-disaggregation models:** today we assume either all variants have
  roles or none do. Mixed cases (some variants role-tagged, others "both") are
  not supported and `isDisaggregated` would treat them as disaggregated, which
  may yield wrong results. If mixed cases arise in practice, revisit.
- **Engine model-level RC/SC for disaggregated models — post-merge follow-up.**
  Today's engine post-step computes additive model-level `RequiredCapacity` /
  `SpareCapacity` over all roles (sat_v2 Phase 3 sums). For disaggregated
  models the additive value is meaningless: roles aren't fungible. Once this
  PR ships, no consumer reads model-level RC/SC for disaggregated models. The
  buggy additive computation becomes latent and should be removed or redefined
  (e.g., zero-out, or `min` over roles, or simply drop the model-level fields'
  meaning when `RoleCapacities` is non-empty). Open as a follow-up issue
  amending PR #1228's `applyUniversalThreshold` after multi-analyzer-optimizer
  merges. See § "Upstream interactions" → "Engine model-level …" for detail.
