# Multi-Analyzer Optimizer — Plan (DRAFT slim, not yet active)

> **DRAFT** — Slimmed candidate for `multi-analyzer-optimizer-plan.md`. The
> active plan currently lives at `multi-analyzer-optimizer-plan.md` (full
> ~750 lines, the coder is iterating against it). This draft is the
> per-PR-only successor to be swapped in once the active coder reaches a
> safe checkpoint (post-1.5 or post-1.6). Do **not** delete the active plan
> until the swap is approved.
>
> **Cross-cutting design context:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
> (mission, architecture including paired allocation + role-iterated scale-down,
> alternatives including compound-variant rejection, future direction). This
> draft is per-PR implementation only.

---

## Scope

Item 1 of the design split (see `multi-analyzer-design.md` § Tasks): **delete
the engine-side combine; per-analyzer slice flows to the optimizers**. Both
optimizers (`CostAwareOptimizer`, `GreedyByScoreOptimizer`) consume the slice
via shared free functions in `pipeline/analyzer_helpers.go`. Disaggregated
models use paired (P, D) scale-up allocation + role-iterated scale-down (no
pairing on scale-down — roles are independent at scale-down).

For the **architectural decisions** (per-variant canonical model; linearity
invariant; α from `TotalDemand`; paired-allocation math; role-iterated
scale-down rationale; alternatives considered), see
[`multi-analyzer-design.md`](multi-analyzer-design.md) §§ Architecture +
Alternatives considered.

---

## Branch state

- **Branch:** `multi-analyzer-optimizer` in worktree `multi-analyzer-optimizer/`.
- **Base:** `a93bc5dc` (pre-rewrite engine-multi-analyzer tip; combine still
  present locally).
- **Tip:** *(updated by agent as commits land)*.
- **Origin:** pushed `a93bc5dc` initially; not yet PR'd.
- **Cross-rebase target:** `multi-analyzer-threshold@b8b823b0` (PR #1228 head)
  after the last commit lands locally. Picks up registration plumbing + threshold
  post-step + sat_v2 simplification + aggregation helpers in one hop.

---

## Roadmap commits

Each commit compiles, passes `make test`, is DCO-signed.

### 1.1 ✅ — pipeline: NamedAnalyzerResult + AnalyzerResults field

`pipeline.NamedAnalyzerResult{Name, Result, Remaining, Spare, RoleSpare, Score}`
+ `pipeline.ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult`. Engine
populates both `Result` (legacy combine, until cleanup commit drops it) and
`AnalyzerResults` (saturation-first, then enabled non-saturation analyzers in
config order). Working `Remaining` / `Spare` / `RoleSpare` initialized from
engine-calibrated values; helpers mutate the working state and never touch
`Result`.

### 1.2 ✅ — pipeline: single-variant helpers in `analyzer_helpers.go`

Helpers (operate on slice, mutate `Remaining`/`Spare`, never `Result`):

- `needsScaleUp(s)` — any-up gate.
- `needsScaleDown(s)` — all-down gate.
- `bottleneckReplicas(s, v)` — `max_i ceil(Remaining_i / PRC_i[v])`.
- `safeRemovalReplicas(s, v)` — `min_i floor(Spare_i / PRC_i[v])`.
- `applyAllocation(s, v, n)`, `applyDeallocation(s, v, n)` — mutate
  `Remaining`/`Spare`; clamp to 0.
- `saturationEntry(s)` — variant-metadata keeper (TODO: remove after future
  pre-analysis-extraction PR).
- `PickVariantFn` — optimizer-specific picker.
- `allocateForModel` — generic scale-up loop.

Specs: `analyzer_helpers_test.go`.

### 1.3 ✅ — CostAware migration (non-disaggregated path)

`CostAwareOptimizer` reads `req.AnalyzerResults` via `saturationEntry()`.
Gates via `needsScaleUp` / `needsScaleDown`. `costGreedyPick` (cheapest by
cost-efficiency) + `allocateForModel` for scale-up. `safeRemovalReplicas` +
`applyDeallocation` for scale-down. Greedy scale-down call site updated to the
new signature. `req.Result` retained transitionally (cleaned in 1.6).

### 1.4 ⏳ — Disaggregation support: paired scale-up + role-iterated scale-down

Adds:

- `RoleSpare map[string]float64` field on `NamedAnalyzerResult` (per-role
  working spare for disaggregated models).
- `analyzerAlpha(r) → (α, tracksP, tracksD)` — α from `RoleCapacities[D].TotalDemand
  / RoleCapacities[P].TotalDemand`. Edge cases: `P=0 ∧ D=0` skip; `P=0 ∧ D>0`
  set α=1 and skip P-side; `D=0 ∧ P>0` skip D-side.
- Paired scale-up helpers: `bottleneckReplicasPaired(s, vP, vD, p_step)`,
  `applyAllocationPaired(s, vP, n_P, vD, n_D)`, `PickPairFn`,
  `allocateForModelPaired`.
- Role-iterated scale-down helpers: `safeRemovalReplicasForRole(s, v, role)`,
  `applyDeallocationForRole(s, v, role, n)`, `variantsForRole`.
- `isDisaggregated([]VariantCapacity) bool` utility.
- `CostAwareOptimizer` dispatches on `isDisaggregated` — paired scale-up via
  `costGreedyPickPaired` + `allocateForModelPaired`; per-role scale-down loop
  using the role helpers.
- Engine init (or optimizer dispatch entry): when `RoleCapacities` is non-empty,
  initialize `Remaining` from `RoleCapacities[prefill].RequiredCapacity` and
  `RoleSpare[role]` from `RoleCapacities[role].SpareCapacity` per role.

### 1.5 ⏳ — Greedy migration (both paths)

`GreedyByScoreOptimizer` migrated to per-analyzer slice. `fairShareValue(priority, s)`
computed on demand. Non-disaggregated: `fairSharePick` (single-variant). Disaggregated:
`fairSharePickPaired`. Scale-down via `safeRemovalReplicasForRole` / per-role loop.
Existing `allocateByRole` (role-budget split) removed — paired path obsoletes it.

### 1.6 ⏳ — Cleanup (final)

Drop `ModelScalingRequest.Result` and `AnalyzerResult.Score` fields. Rename
`runAnalyzersAndScore` → `runAnalyzers`. Drop saturation-only score-compute
loop in engine. `buildDecisionsWithOptimizer` reason-strings cleaned to read
from the slice. Final dev-guide commit (small additions; threshold's dev-guide
already covers most architecture).

**Code cleanup carried from 1.3 review:** add comment on the `removed` flag in
`costAwareScaleDown`'s outer `for needsScaleDown(s)` loop documenting why the
flag is needed (guards against infinite loop when some `Spare_i > 0` but no
variant has remaining capacity to give up).

---

## Cross-rebase mechanics (after 1.6 lands locally; before push)

Rebase 1.1–1.6 stack onto `multi-analyzer-threshold@b8b823b0` (PR #1228 head).
Picks up registration plumbing + threshold post-step + aggregation helpers +
sat_v2 simplification.

**Expected conflict:** `internal/engines/saturation/engine_v2.go` major.
1.1's combine-and-collect rewrite of `runAnalyzersAndScore` collides with
threshold's post-step-and-discard rewrite. Manual reshape — keep threshold's
post-step pattern, layer 1.1's slice collection on top. The `runRegisteredAnalyzers`
loop body changes from "calibrate then discard" to "calibrate then append to
named slice". Caller-side `req.Result` becomes a transitional pointer at
`slice[0].Result` until 1.6 drops the field.

`runAnalyzersAndScore` signature evolution: from `(...) ([]NamedAnalyzerResult,
*AnalyzerResult, error)` (1.1's shape) to `(...) ([]NamedAnalyzerResult, error)`
post-rebase. Combined-result return drops because combine is gone in
threshold's tree.

Other files (pipeline helpers + tests, optimizers) likely clean — threshold
doesn't touch them. Sat_v2 — threshold's tree is the merged version; we don't
touch sat_v2 from this branch.

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

## Coordination

- **PR #1225 (`multi-analyzer-registration`)** — base for cross-rebase
  (transitively, via threshold). Stable. Awaiting reviewer.
- **PR #1228 (`multi-analyzer-threshold`)** — direct cross-rebase target.
  Awaiting reviewer.
- **PR #1237 (`fix/role-aware-scaledown`)** — independent upstream fix on the
  legacy single-analyzer path. End-result equivalent to our role-iterated
  scale-down for the single-analyzer case. See
  [`multi-analyzer-design.md`](multi-analyzer-design.md) § Alternatives → A
  for the equivalence reasoning.
- **`engine-queue-fix`** — blocked on PR #1225 merging.
- **PR #1113** — superseded; will be closed.

This branch does **not** depend on any PR merging before continuing 1.4–1.6
locally. Cross-rebase happens after 1.6 lands.

---

## Open items

- **Q4 — picker contract / cap responsibility (1.4 / 1.5).** `allocateForModel`
  / `allocateForModelPaired` take `min(capN, bottleneckReplicas)`. For Greedy,
  `capN` comes from the fair-share target ÷ PRC. Defaulting to this; flag for
  review when 1.5 is ready.
- **Q5 — test layer placement.** Catalog migrated combine specs from
  `engine_combine_test.go` (already deleted upstream); migrated to helper
  layer (1.2 — done) vs optimizer layer (1.5). Will list catalog in next
  status handoff.
- **`TryAllocate(ctx, ...)` signature change** from PR #1026: appears at
  rebase time; mechanical pass-through.
- **Per-analyzer threshold overrides:** honored upstream by PR #1228. Optimizer
  reads engine-calibrated values; no further work on this front.
- **Future direction:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
  § Future direction (pre-analysis extraction; vector α; per-analyzer
  observability metrics; engine model-level RC/SC bug for disaggregated;
  enabled-false veto fix; replica-count accounting consistency).

---

## References

- [`multi-analyzer-design.md`](multi-analyzer-design.md) — cross-cutting design
  doc.
- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md)
  — Item 3 (PR #1225) sibling plan.
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md) —
  Item 2 (PR #1228) sibling plan and direct cross-rebase target.
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder
  agent rules.
- [`PR1113-review.md`](PR1113-review.md) — historical review of original
  PR #1113 that decided the 3-PR split.
