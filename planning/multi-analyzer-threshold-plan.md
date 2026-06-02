# Multi-Analyzer Threshold — Architectural Rework Plan

> **Status: PLANNED** — Architectural rework of the `multi-analyzer-threshold` branch.
> Force-push replaces the current 3 commits (`c2f57c9f`, `06b9d236`, `be25890f`) with
> 4 fresh commits implementing the per-variant-canonical model.
> Branch base: `multi-analyzer-registration@66001d47` (PR #1225 head).

---

## Context

The current threshold branch (`be25890f`) implements Item 2 of `PR1113-review.md` correctly
in math but with architectural muddle:

- Engine post-step has a fallback walk over `VariantCapacities` to derive
  `TotalAnticipatedSupply` when the analyzer leaves it zero — creating a second source of
  truth for an analyzer-published value.
- Model-level fallback is 3-step (`TotalAnticipatedSupply → walk variants → TotalSupply`);
  per-role fallback is 2-step (`TotalAnticipatedSupply → TotalSupply`). Asymmetric paths
  invite future bugs.
- Sat_v2's Phase 4 still has the in-analyzer RC/SC formula even though the engine
  post-step overwrites it. Two implementations of the same math, deferred cleanup,
  documented but not fixed.

Discussion 2026-06-02 settled the architecture. This plan implements it.

---

## Architectural decisions (locked 2026-06-02)

### Per-variant data is canonical

`interfaces.VariantCapacity` (already on main, no struct change needed) is the single
source of truth for per-variant primitives:

```go
type VariantCapacity struct {
    VariantName        string
    AcceleratorName    string
    Cost               float64
    Role               string  // "prefill" | "decode" | "both" | ""
    ReplicaCount       int
    PendingReplicas    int
    PerReplicaCapacity float64  // analyzer-specific
    TotalCapacity      float64  // analyzer-published, == ReplicaCount × PRC
    TotalDemand        float64  // analyzer-published, per-variant aggregate demand
    Utilization        float64  // analyzer-published, == TotalDemand / TotalCapacity
}
```

### Responsibility split

| Field | Written by | Read by |
|---|---|---|
| Per-variant `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity`, `Cost`, `Role`, `AcceleratorName` | Analyzer | Optimizer (per-variant scaling math + picker) |
| Per-variant `TotalCapacity`, `TotalDemand`, `Utilization` | Analyzer | sat_v2 internal aggregation; `Utilization` also passed through to `VariantDecision.Utilization` for metric emission |
| Model-level `r.TotalSupply`, `r.TotalAnticipatedSupply`, `r.TotalDemand` | Analyzer (via shared helpers) | Engine post-step |
| Per-role `r.RoleCapacities[role].TotalSupply`/`TotalAnticipatedSupply`/`TotalDemand` | Analyzer (via shared helpers) | Engine post-step |
| Model-level `r.RequiredCapacity`, `r.SpareCapacity` | **Engine post-step only** (overwrites anything analyzer wrote) | Optimizer |
| Per-role `RoleCapacity.RequiredCapacity`, `RoleCapacity.SpareCapacity` | **Engine post-step only** (overwrites anything analyzer wrote) | Optimizer |

### Linearity invariant (the contract)

The optimizer's per-variant scaling math (`bottleneckReplicas`, `safeRemovalReplicas`,
`applyAllocation` on the `multi-analyzer-optimizer` branch) assumes that `n` replicas of
variant `v` reduce model-level RC by exactly `n × PRC[v]`. That is, `Total*` must equal the
canonical sum over variants:

```
r.TotalSupply              == Σ_v vc.ReplicaCount × vc.PerReplicaCapacity
r.TotalAnticipatedSupply   == Σ_v (vc.ReplicaCount + vc.PendingReplicas) × vc.PerReplicaCapacity
r.TotalDemand              == Σ_v vc.TotalDemand
r.RoleCapacities[role].*   == same sums filtered by vc.Role == role
```

Shared helpers compute these. An analyzer that doesn't use them takes responsibility for
producing identical math — otherwise the optimizer's per-variant allocation silently breaks.

### Engine post-step is pure formula

```go
func applyUniversalThreshold(r *interfaces.AnalyzerResult, scaleUp, scaleDown float64) {
    if r == nil { return }
    if scaleUp > 0 {
        r.RequiredCapacity = max(0, r.TotalDemand/scaleUp - r.TotalAnticipatedSupply)
    }
    if scaleDown > 0 {
        r.SpareCapacity = max(0, r.TotalSupply - r.TotalDemand/scaleDown)
    }
    for role, rc := range r.RoleCapacities {
        if scaleUp > 0 {
            rc.RequiredCapacity = max(0, rc.TotalDemand/scaleUp - rc.TotalAnticipatedSupply)
        }
        if scaleDown > 0 {
            rc.SpareCapacity = max(0, rc.TotalSupply - rc.TotalDemand/scaleDown)
        }
        r.RoleCapacities[role] = rc
    }
}
```

- **Strict no-fallback.** No `if anticipated == 0` branch. No `VariantCapacities` walk.
- `TotalAnticipatedSupply == 0` is a **literal value**, not a sentinel. For a scaled-to-zero
  variant with positive demand, RC = TotalDemand/scaleUp — the correct "this much capacity
  needed" answer.
- Model-level and per-role apply the same formula with the same `(scaleUp, scaleDown)`.
  No per-role threshold overrides.

### Per-analyzer threshold overrides

`resolveThresholds(name, cfg)` resolves `AnalyzerScoreConfig.ScaleUpThreshold` /
`ScaleDownBoundary` over the model-level `SaturationScalingConfig.ScaleUpThreshold` /
`ScaleDownBoundary`. The same resolved `(scaleUp, scaleDown)` pair is applied to model
and every role for that analyzer. No per-role overrides.

The saturation-only override-resolution loop ([engine_v2.go old:87-100](internal/engines/saturation/engine_v2.go))
that existed before #1113 stays deleted.

### Shared helpers — `internal/engines/aggregation/`

New package, sibling of `internal/engines/{analyzers,pipeline,saturation,common,executor}/`.
Pure functions over `interfaces.VariantCapacity`:

```go
package aggregation

import "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"

type ScopeTotals struct {
    TotalSupply            float64
    TotalAnticipatedSupply float64
    TotalDemand            float64
}

func SumTotalSupply(vcs []interfaces.VariantCapacity) float64
func SumTotalAnticipatedSupply(vcs []interfaces.VariantCapacity) float64
func SumTotalDemand(vcs []interfaces.VariantCapacity) float64
func AggregateByRole(vcs []interfaces.VariantCapacity) map[string]ScopeTotals
```

Imports: only `internal/interfaces`. No engine, no analyzer dependencies — analyzers can
import without cycles.

`AggregateByRole` canonicalizes empty role to `interfaces.RoleBoth` consistent with sat_v2's
existing normalization. Helpers do NOT compute per-variant `Utilization` (analyzer's
existing job).

---

## Commit plan (4 commits, fresh history)

Force-push the threshold branch. Drop `c2f57c9f`/`06b9d236`/`be25890f` and replace with
4 commits, each compiling + tests passing + DCO-signed.

### Commit 1 — `engines: universal threshold post-step — pure formula at every scope`

Files:
- `internal/engines/saturation/engine_v2.go`:
  - Add `applyUniversalThreshold(*AnalyzerResult, scaleUp, scaleDown float64)` — strict
    no-fallback, applies pure formula at model + each `RoleCapacities` entry.
  - Add `resolveThresholds(name string, cfg config.SaturationScalingConfig) (scaleUp, scaleDown float64)`.
  - In `runAnalyzersAndScore`: after `runV2AnalysisOnly`, call
    `applyUniversalThreshold(baseResult, satUp, satDown)` with
    `satUp, satDown := resolveThresholds(SaturationAnalyzerName, config)`.
  - Confirm the saturation-only override-resolution loop is gone (was at old `:87-100`).
  - `runRegisteredAnalyzers` takes config and calls `applyUniversalThreshold` per
    non-saturation analyzer with per-analyzer-resolved thresholds.
  - `runRegisteredAnalyzer` returns `*AnalyzerResult` so caller can apply post-step.
- `internal/engines/saturation/engine_register_test.go`: update the 3 `runRegisteredAnalyzers`
  call sites to pass `config.SaturationScalingConfig{}`.
- `internal/engines/saturation/engine_v2_threshold_test.go` (new):
  - Pure-formula specs at model level: scale-up, scale-down, hysteresis band, exact-boundary
    clamps, anticipated-vs-steady asymmetry, non-positive thresholds no-op, idempotency,
    nil-result safety.
  - Pure-formula specs at per-role: per-role calibration with anticipated supply, per-role
    with `TotalAnticipatedSupply == 0` (yields RC = TD/scaleUp; no fallback).
  - **Drop** any spec for the `VariantCapacities` walk — that fallback no longer exists.
- `internal/config/saturation_scaling.go`: doc-comment on `ScaleUpThreshold` /
  `ScaleDownBoundary` — universal post-step phrasing.
- `internal/interfaces/analyzer.go`: keep `AnalyzerResult.TotalAnticipatedSupply` and
  `RoleCapacity.TotalAnticipatedSupply` (already added by `c2f57c9f` / `be25890f`).
  Doc-comments: "analyzer-supplied; engine reads as-is for the threshold formula".
- Sat_v2 unchanged in this commit — still publishes `Total*` via its existing logic.
  The engine post-step is idempotent on sat_v2's pre-clamped output.

Verify after commit 1: `gofmt -l`, `go vet`, `go build`, `make test`,
`go test -race ./internal/engines/saturation/...`. All pass.

### Commit 2 — `engines/aggregation: shared helpers for analyzer aggregations`

Files:
- `internal/engines/aggregation/aggregation.go` (new): `ScopeTotals`, `SumTotalSupply`,
  `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole` — see § Shared helpers
  above.
- `internal/engines/aggregation/aggregation_test.go` (new): empty input, single variant,
  multiple variants, mixed roles, empty role canonicalized to `RoleBoth`, zero replicas,
  zero PRC.

Helpers not yet wired to any analyzer — pure addition, no behavior change.

Verify: `gofmt`, `go vet`, `go build`, `make test`. All pass.

### Commit 3 — `engines/saturation_v2: use shared helpers; drop in-analyzer RC/SC computation`

Files:
- `internal/engines/analyzers/saturation_v2/analyzer.go`:
  - **Phase 3** (model-level supply/demand/anticipated, ~lines 91-100): replace manual loop
    with helper calls:
    ```go
    r.TotalSupply = aggregation.SumTotalSupply(variantCapacities)
    r.TotalAnticipatedSupply = aggregation.SumTotalAnticipatedSupply(variantCapacities)
    r.TotalDemand = aggregation.SumTotalDemand(variantCapacities)
    ```
  - **Phase 4** (model-level RC/SC computation, ~lines 117-140): delete the entire block.
    Engine post-step recomputes from analyzer-published `Total*`. Delete the Phase 4 TODO
    comment that was added in `06b9d236`/`be25890f`.
  - **`aggregateByRole`** (per-role RC/SC, ~lines 493-500): delete the per-role threshold
    formula (`required = ra.demand/threshold − ra.anticipated`, etc.). Keep the per-role
    aggregation of supply/demand/anticipated (engine post-step needs `RoleCapacity.Total*`
    populated). Two implementation choices, equivalent behavior:
    - (a) Keep the existing inline aggregation; just remove the RC/SC lines.
    - (b) Replace the inline aggregation with `aggregation.AggregateByRole(variantCapacities)`.
    Pick whichever yields cleaner code.
- `internal/engines/analyzers/saturation_v2/analyzer_test.go`: adapt tests. Model-level +
  per-role RC/SC tests in sat_v2 likely become engine-level tests (covered in
  `engine_v2_threshold_test.go` from commit 1). Sat_v2 tests now assert: `VariantCapacity`
  populated correctly; `r.Total*` populated via helpers; `r.RoleCapacities[role].Total*`
  populated; sat_v2 does NOT write `r.RequiredCapacity` / `r.SpareCapacity` (engine
  overwrites; either don't write, or write 0 — pick one).

After commit 3: sat_v2's responsibility is "publish per-variant primitives + per-scope
`Total*`"; engine is the sole computer of RC/SC.

Verify: `gofmt`, `go vet`, `go build`, `make test`, `-race` for saturation pkg. All pass.

### Commit 4 — `docs: developer-guide — analyzer responsibilities + universal threshold post-step + helpers`

Files:
- `docs/developer-guide/saturation-scaling-config.md`: rewrite "Universal Threshold Post-Step"
  section. Cover:
  - Architecture: per-variant `VariantCapacity` is canonical; analyzer publishes per-variant
    primitives + per-scope `Total*`; engine post-step computes RC/SC at each scope from
    `Total*`.
  - Engine post-step formula (model + per-role; same threshold values; per-analyzer override
    resolved once per analyzer, applied at every scope for that analyzer).
  - Strict no-fallback: `TotalAnticipatedSupply == 0` is a literal value, not a sentinel.
  - Default helpers: pointer to `internal/engines/aggregation/` with examples of
    `SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`.
  - Linearity invariant: `r.TotalSupply == Σ_v rc × PRC`, etc. Required for the
    optimizer's per-variant scaling math; helpers enforce it.
  - Per-analyzer threshold overrides honored at every scope; no per-role overrides.
- Drop any prose that suggests engine has fallback walks or per-role fallback differs from
  model-level.
- (Optional) refactor sections that are now stale.

Verify: docs render OK; no broken links.

---

## Mechanics

Force-push policy per CONVENTIONS:

- Use `--force-with-lease`, not `--force`.
- State the reason explicitly to Dean before pushing
  ("rebuilding history per architectural rework plan").
- Don't push until all 4 commits land locally and are verified.

Rewrite approach:

```
git checkout multi-analyzer-threshold
git reset --soft 66001d47        # collapse 3 commits into the index; tree unchanged
git reset                         # mixed: unstage so commit boundaries are clean
# apply commit 1 edits → stage → commit
# apply commit 2 edits → stage → commit
# apply commit 3 edits → stage → commit
# apply commit 4 edits → stage → commit
```

After all 4 commits land:

```
gofmt -l ./internal/... ./pkg/... ./cmd/...
go vet ./internal/... ./pkg/... ./cmd/...
go build ./...
make test
go test -race ./internal/engines/...
git log 66001d47..HEAD --format='%h %s%n%b' | grep -E '^[0-9a-f]+|Signed-off-by'  # DCO check
```

The pre-rewrite tip `be25890f` and predecessors stay reachable via `git reflog` (~30 days)
for comparison during rebase.

---

## Verification gates

Each commit must satisfy:
- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty output.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- DCO sign-off (`Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`).

Final pre-push gate: `go test -race ./internal/engines/saturation/...` — clean.

---

## Coordination

- **PR #1225 (`multi-analyzer-registration`)** — base for this branch. Stable. CI in progress
  on review. Independent of this branch's rework.
- **`multi-analyzer-optimizer`** — depends on the linearity invariant this plan documents.
  Out of scope for this PR. The optimizer branch is mid-flight (commits 1.1 + 1.2 landed);
  no handoff between this branch and the optimizer branch is needed for this rework.
- **PR #1113** — stays open until Dean closes it post-discussion with ev-shindin.

---

## Open items

- Push of the rebuilt branch waits for explicit Dean confirmation per CONVENTIONS.
- A new PR for `multi-analyzer-threshold` is opened only after the rebuild is reviewed.
