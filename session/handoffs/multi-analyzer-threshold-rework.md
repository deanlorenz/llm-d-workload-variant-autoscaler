to: multi-analyzer-threshold agent
from: plan-agent
session: multi-analyzer-threshold architectural rework

## TL;DR

Force-push the threshold branch. Drop the existing 3 commits (`c2f57c9f`, `06b9d236`, `be25890f`) and replace with a clean 4-commit structure that locks in the architectural decisions Dean settled in design discussion 2026-06-02. The current commits are correct in math but architecturally muddled (engine has fallback walks, two sources of truth for `Total*`, redundant in-analyzer RC/SC math). The rework consolidates this into:

- **Engine post-step = pure formula, no fallbacks.**
- **Analyzer = sole publisher of per-variant primitives + per-scope `Total*`.** Uses shared helpers for the canonical aggregation.
- **No per-variant or per-role override semantics.** Per-analyzer threshold overrides only.

Tip after rework will be a new SHA on top of `multi-analyzer-registration@66001d47`. Branch is **not pushed yet**; PR not yet opened.

---

## Architectural decisions (locked)

### Data model

`interfaces.VariantCapacity` (already on main, no change needed):

```go
type VariantCapacity struct {
    VariantName        string
    AcceleratorName    string
    Cost               float64
    Role               string  // "prefill" | "decode" | "both" | "" — already there
    ReplicaCount       int
    PendingReplicas    int
    PerReplicaCapacity float64  // analyzer-specific
    TotalCapacity      float64  // analyzer-published, == ReplicaCount × PRC
    TotalDemand        float64  // analyzer-published, per-variant aggregate demand
    Utilization        float64  // analyzer-published, == TotalDemand / TotalCapacity
}
```

Per-variant fields stay as they are. Role is already populated by sat_v2 (no change in this PR).

`interfaces.AnalyzerResult` and `interfaces.RoleCapacity` keep `Total*` fields:

```go
type AnalyzerResult struct {
    // ... existing ...
    TotalSupply              float64
    TotalDemand              float64
    TotalAnticipatedSupply   float64
    Utilization              float64
    RequiredCapacity         float64  // engine writes (post-step)
    SpareCapacity            float64  // engine writes (post-step)
    VariantCapacities        []VariantCapacity
    RoleCapacities           map[string]RoleCapacity
}

type RoleCapacity struct {
    Role                     string
    TotalSupply              float64
    TotalDemand              float64
    TotalAnticipatedSupply   float64
    RequiredCapacity         float64  // engine writes
    SpareCapacity            float64  // engine writes
}
```

No new fields; no removed fields. The contract changes, not the struct.

### Responsibility split (the contract)

| Field | Written by | Read by |
|---|---|---|
| Per-variant `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity`, `Cost`, `Role`, `AcceleratorName` | Analyzer | Optimizer (per-variant scaling math + picker) |
| Per-variant `TotalCapacity`, `TotalDemand`, `Utilization` | Analyzer | sat_v2 internal aggregation; `Utilization` also read by optimizer for `VariantDecision.Utilization` metric |
| Model-level `r.TotalSupply`, `r.TotalAnticipatedSupply`, `r.TotalDemand` | Analyzer (via shared helpers) | Engine post-step |
| Per-role `r.RoleCapacities[role].TotalSupply`/`TotalAnticipatedSupply`/`TotalDemand` | Analyzer (via shared helpers) | Engine post-step |
| Model-level `r.RequiredCapacity`, `r.SpareCapacity` | Engine post-step (overwrites anything analyzer wrote) | Optimizer |
| Per-role `RoleCapacity.RequiredCapacity`, `RoleCapacity.SpareCapacity` | Engine post-step (overwrites anything analyzer wrote) | Optimizer |

**Implicit invariant** (worth a doc line): `r.TotalSupply == Σ_v vc.ReplicaCount × vc.PerReplicaCapacity`, `r.TotalAnticipatedSupply == Σ_v (vc.ReplicaCount + vc.PendingReplicas) × vc.PerReplicaCapacity`, etc. Per-role versions filter by `vc.Role`. The shared helpers compute these. An analyzer that doesn't use the helpers takes responsibility for producing identical math, otherwise the optimizer's per-variant scaling (`bottleneckReplicas` etc., on the `multi-analyzer-optimizer` branch) silently breaks because it assumes `n` replicas of variant `v` reduce RC by `n × PRC[v]`.

### Engine post-step

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

Strict no-fallback. No `if anticipated == 0` branch. No `VariantCapacities` walk. `TotalAnticipatedSupply == 0` is a literal value — for a scaled-to-zero variant with positive demand, RC = TotalDemand/scaleUp, which is the correct "this much capacity needed" answer.

`resolveThresholds(name, cfg)` stays — resolves per-analyzer override over global. Same code as commit `06b9d236`.

`runAnalyzersAndScore` calls `applyUniversalThreshold(baseResult, satUp, satDown)` after `runV2AnalysisOnly` — same as today.

`runRegisteredAnalyzers(ctx, logger, modelID, input, cfg)` calls `applyUniversalThreshold` per non-saturation analyzer — same as today.

### Shared helpers package — `internal/engines/aggregation/`

New package, sibling of `internal/engines/{analyzers,pipeline,saturation,common,executor}/`. Pure functions over `interfaces.VariantCapacity`:

```go
package aggregation

import "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"

// ScopeTotals holds the three per-scope aggregates produced by helpers.
type ScopeTotals struct {
    TotalSupply            float64
    TotalAnticipatedSupply float64
    TotalDemand            float64
}

// SumTotalSupply returns Σ vc.ReplicaCount × vc.PerReplicaCapacity.
func SumTotalSupply(vcs []interfaces.VariantCapacity) float64 { ... }

// SumTotalAnticipatedSupply returns Σ (vc.ReplicaCount + vc.PendingReplicas) × vc.PerReplicaCapacity.
func SumTotalAnticipatedSupply(vcs []interfaces.VariantCapacity) float64 { ... }

// SumTotalDemand returns Σ vc.TotalDemand.
func SumTotalDemand(vcs []interfaces.VariantCapacity) float64 { ... }

// AggregateByRole returns role → ScopeTotals over the variants of that role.
// Only includes roles that have at least one variant. Empty role and "both" are
// canonicalized via the same normalization sat_v2 uses today (refer to
// internal/engines/saturation/engine.go normalizeRole / interfaces.RoleBoth).
func AggregateByRole(vcs []interfaces.VariantCapacity) map[string]ScopeTotals { ... }
```

Imports: only `internal/interfaces`. No engine, no analyzer dependencies — analyzer packages can import it without cycles.

Open question on `Utilization` derivation: helpers do NOT compute `Utilization` (it's per-variant convenience field; `TotalDemand/TotalCapacity` is the analyzer's job to set, and it's already done in sat_v2). Don't add it to helpers unless a use case appears.

### sat_v2 changes (commit 3)

Sat_v2 currently has three blocks of redundant computation that the engine post-step now owns:

1. **Phase 4 RC/SC at model level** ([analyzer.go:117-140 area](internal/engines/analyzers/saturation_v2/analyzer.go)) — compute `requiredCapacity`/`spareCapacity` from `totalDemand/threshold − totalAnticipatedSupply` etc., then write to `result.RequiredCapacity`/`SpareCapacity`. **Delete this block.** Engine post-step recomputes.

2. **`aggregateByRole`'s RC/SC computation** ([analyzer.go:493-500 area](internal/engines/analyzers/saturation_v2/analyzer.go)) — `required = ra.demand/threshold − ra.anticipated` etc. **Delete the per-role RC/SC computation.** Keep the per-role supply/demand/anticipated aggregation (engine post-step needs `RoleCapacity.Total*` populated to compute RC/SC). Or replace with `aggregation.AggregateByRole` if the helper covers it.

3. **Phase 3 model-level totals** ([analyzer.go:91-100 area](internal/engines/analyzers/saturation_v2/analyzer.go)) — `totalSupply += vc.TotalCapacity`, `totalDemand += vc.TotalDemand`, plus `totalAnticipatedSupply` walk. **Replace with helper calls:**

   ```go
   r.TotalSupply = aggregation.SumTotalSupply(variantCapacities)
   r.TotalAnticipatedSupply = aggregation.SumTotalAnticipatedSupply(variantCapacities)
   r.TotalDemand = aggregation.SumTotalDemand(variantCapacities)
   ```

After commit 3, sat_v2's responsibility is:
- Build `[]VariantCapacity` (Phase 1-2: replica metrics → per-variant primitives + analyzer-specific PRC).
- Populate per-variant `TotalCapacity`, `TotalDemand`, `Utilization` (existing logic).
- Populate `r.Total*` via helpers.
- Populate `r.RoleCapacities[role].Total*` via helpers (or call helpers per-role internally).
- Populate `r.Utilization` (model-level, existing).
- **Stop** — RC/SC come from the engine post-step.

The Phase 4 TODO that you added in commit `06b9d236`/`be25890f` is no longer a TODO — it's done in commit 3. Delete the TODO comment.

### Configurable threshold values (no change from current commits)

`SaturationScalingConfig.ScaleUpThreshold` (default 0.85) and `ScaleDownBoundary` (default 0.70) at model-level. `AnalyzerScoreConfig.ScaleUpThreshold` and `ScaleDownBoundary` per-entry overrides.

`resolveThresholds` resolution: per-analyzer override > model-level global. Resolved once per analyzer; the same `(scaleUp, scaleDown)` pair is passed to `applyUniversalThreshold` and applied to model + every role for that analyzer.

No per-role threshold overrides — the same threshold values apply to every role of a given analyzer.

The saturation-only override-resolution loop deletion stays (already done in `c2f57c9f`).

---

## Commit plan (4 commits, fresh history)

Force-push the threshold branch. Drop `c2f57c9f`/`06b9d236`/`be25890f` and replace with these 4 commits, each compiling + tests passing.

### Commit 1 — `engines: universal threshold post-step — pure formula at every scope`

Files:
- `internal/engines/saturation/engine_v2.go`:
  - Add `applyUniversalThreshold(*AnalyzerResult, scaleUp, scaleDown float64)` — strict no-fallback, applies pure formula at model + each `RoleCapacities` entry. Spec above.
  - Add `resolveThresholds(name string, cfg config.SaturationScalingConfig) (scaleUp, scaleDown float64)` — same as commit `06b9d236`'s.
  - In `runAnalyzersAndScore`: after `runV2AnalysisOnly`, call `applyUniversalThreshold(baseResult, satUp, satDown)` with `satUp, satDown := resolveThresholds(SaturationAnalyzerName, config)`.
  - Delete the saturation-only override-resolution loop ([engine_v2.go old:87-100](internal/engines/saturation/engine_v2.go) — was already deleted in `c2f57c9f`; just don't re-add it).
  - `runRegisteredAnalyzers` takes config and calls `applyUniversalThreshold` per non-saturation analyzer with per-analyzer-resolved thresholds. (Same as `06b9d236`'s.)
  - `runRegisteredAnalyzer` returns `*AnalyzerResult` so caller can apply post-step. (Same as `06b9d236`'s.)
- `internal/engines/saturation/engine_register_test.go`: update the 3 `runRegisteredAnalyzers` call sites to pass `config.SaturationScalingConfig{}` (zero-value config makes `applyUniversalThreshold` a no-op for unrelated tests). (Same as `06b9d236`'s.)
- `internal/engines/saturation/engine_v2_threshold_test.go` (new):
  - Pure-formula specs at model level: scale-up, scale-down, hysteresis band, exact-boundary clamps, anticipated-vs-steady asymmetry, non-positive thresholds no-op, idempotency, nil-result safety.
  - Pure-formula specs at per-role: per-role calibration with anticipated supply, per-role with `TotalAnticipatedSupply == 0` (yields RC = TD/scaleUp, no fallback).
  - **Drop** the spec "computes anticipated supply from VariantCapacities when TotalAnticipatedSupply is zero" — that fallback no longer exists.
- `internal/config/saturation_scaling.go`: doc-comment update on `ScaleUpThreshold` / `ScaleDownBoundary` to reflect engine-post-step application universally. (Same as commit `c2f57c9f`'s.)
- `docs/developer-guide/saturation-scaling-config.md`: minimal additions in this commit — parameters table rows + a stub "Universal Threshold Post-Step" subsection with TODO marker for full rewrite in commit 4. Or leave docs entirely for commit 4; either is fine.

`interfaces/analyzer.go` changes from commits `c2f57c9f` and `be25890f`:
- `AnalyzerResult.TotalAnticipatedSupply` field — keep. Doc-comment: analyzer-supplied; engine reads as-is for the threshold formula.
- `RoleCapacity.TotalAnticipatedSupply` field — keep. Same doc.

In sat_v2, keep the population of `TotalAnticipatedSupply` (Phase 3) and `RoleCapacity.TotalAnticipatedSupply` (in `aggregateByRole`) — these are analyzer outputs the engine consumes. Only the per-variant Phase 3 supply totals + Phase 4 RC/SC + per-role RC/SC will be replaced in commit 3.

Verify after commit 1: `gofmt`, `go vet`, `go build`, `make test`, `go test -race ./internal/engines/saturation/...`. All pass.

### Commit 2 — `engines/aggregation: shared helpers for analyzer aggregations`

Files:
- `internal/engines/aggregation/aggregation.go` (new):
  - `ScopeTotals` struct
  - `SumTotalSupply([]interfaces.VariantCapacity) float64`
  - `SumTotalAnticipatedSupply([]interfaces.VariantCapacity) float64`
  - `SumTotalDemand([]interfaces.VariantCapacity) float64`
  - `AggregateByRole([]interfaces.VariantCapacity) map[string]ScopeTotals`
- `internal/engines/aggregation/aggregation_test.go` (new):
  - Specs covering: empty input, single variant, multiple variants, mixed roles, empty role canonicalized to `interfaces.RoleBoth`, zero replicas, zero PRC.

Imports: only `internal/interfaces`. Pure functions, no state.

The helpers are not yet wired to any analyzer in this commit — pure addition, doesn't change behavior anywhere.

Verify: `gofmt`, `go vet`, `go build`, `make test`. All pass. (Helpers tested in isolation; nothing else changed.)

### Commit 3 — `engines/saturation_v2: use shared helpers; drop in-analyzer RC/SC computation`

Files:
- `internal/engines/analyzers/saturation_v2/analyzer.go`:
  - **Phase 3** (model-level supply/demand/anticipated): replace the manual loop with helper calls:
    ```go
    r.TotalSupply = aggregation.SumTotalSupply(variantCapacities)
    r.TotalAnticipatedSupply = aggregation.SumTotalAnticipatedSupply(variantCapacities)
    r.TotalDemand = aggregation.SumTotalDemand(variantCapacities)
    ```
  - **Phase 4** (model-level RC/SC computation): delete the entire block. Engine post-step recomputes from analyzer-published `Total*`. Delete the Phase 4 TODO comment that was added in `06b9d236`/`be25890f`.
  - **`aggregateByRole`** (per-role RC/SC computation): delete the per-role threshold formula. Keep the per-role aggregation of supply/demand/anticipated (it produces `RoleCapacity.Total*` fields the engine post-step needs). Either:
    - (a) keep the existing inline aggregation, just remove the RC/SC formula lines, OR
    - (b) replace the inline aggregation with `aggregation.AggregateByRole(variantCapacities)` (cleaner if the helper signature matches).
  - Pick whichever yields cleaner code; behaviorally equivalent.
- `internal/engines/analyzers/saturation_v2/analyzer_test.go`: adapt tests. The model-level + per-role RC/SC tests in sat_v2 likely become engine-level tests (covered in `engine_v2_threshold_test.go` from commit 1). Sat_v2 tests should now assert: per-variant `VariantCapacity` correctly populated; `r.Total*` fields correctly populated via helpers; `r.RoleCapacities[role].Total*` correctly populated; sat_v2 does NOT write `r.RequiredCapacity`/`r.SpareCapacity` (or writes 0; engine overwrites).

Verify: `gofmt`, `go vet`, `go build`, `make test`, `-race` for saturation pkg. All pass.

After commit 3: sat_v2 is purely "publish per-variant primitives + per-scope `Total*`"; engine is the sole computer of RC/SC.

### Commit 4 — `docs: developer-guide — analyzer responsibilities + universal threshold post-step + helpers`

Files:
- `docs/developer-guide/saturation-scaling-config.md`: comprehensive rewrite of "Universal Threshold Post-Step" section. Cover:
  - Architecture: per-variant `VariantCapacity` is canonical; analyzer publishes per-variant primitives + per-scope `Total*`; engine post-step computes RC/SC at each scope from `Total*`.
  - Engine post-step formula (model + per-role; same threshold values; per-analyzer override resolved once and applied at every scope for that analyzer).
  - Strict no-fallback: `TotalAnticipatedSupply == 0` is a literal value, not a sentinel.
  - Default helpers: pointer to `internal/engines/aggregation/` with examples of `SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`.
  - Implicit linearity invariant: `r.TotalSupply == Σ_v rc × PRC`, etc. Required for the optimizer's per-variant scaling math to work; helpers enforce it.
  - Per-analyzer threshold overrides honored at every scope; no per-role overrides.
  - Drop any prose that suggests engine has fallback walks or per-role fallback differs from model-level.

- (Optional) Move/refactor any sections that are now stale.

Verify: docs render OK; no broken links.

---

## Mechanics

You're going to **force-push** the threshold branch (replacing `c2f57c9f`, `06b9d236`, `be25890f` with 4 fresh commits). Per CONVENTIONS:

- Don't `git push --force` — use `--force-with-lease` after the rebase. State the reason explicitly to Dean before pushing ("rebuilding history per architectural rework handoff").
- Branch base stays `multi-analyzer-registration@66001d47`.
- Each new commit must compile, pass `make test`, pass gofmt, vet, build, and DCO-sign.
- Do not push until all 4 commits land locally and are verified.

Approach for the rewrite:
1. `git checkout multi-analyzer-threshold`
2. `git reset --soft 66001d47` — collapse the 3 commits into the index. Working tree unchanged.
3. `git reset` (mixed) — unstage so the 4-commit boundaries are clean.
4. Apply per-file edits for commit 1 (engine post-step, tests, config doc-comment, optional doc stub). Stage. Commit 1.
5. Apply per-file edits for commit 2 (new aggregation package, tests). Stage. Commit 2.
6. Apply per-file edits for commit 3 (sat_v2 simplification). Stage. Commit 3.
7. Apply per-file edits for commit 4 (full doc rewrite). Stage. Commit 4.
8. Verify: `gofmt -l`, `go vet`, `go build`, `make test`, `go test -race ./internal/engines/...`. All pass.
9. DCO check: `git log 66001d47..HEAD --format='%h %s%n%b' | grep -E '^[0-9a-f]+|Signed-off-by'` — every commit signed.
10. Update your living handoff at `session/handoffs/multi-analyzer-threshold-status.md` (new filename — "status" not "commit-2-1") with the 4 new SHAs, test results, and "ready for review — not pushed" status. Do not touch the `commit-2-1.md` handoff (it's been consumed by `/sync-current`).

The pre-rewrite tip `be25890f` and its predecessors stay reachable via `git reflog` for ~30 days — useful if you need to compare against the previous architecture mid-rebase.

---

## Open questions answered

From your last handoff:

> Push all 3 commits to `origin/multi-analyzer-threshold`?

**No** — branch is being rebuilt; existing 3 commits will be force-pushed away. Don't push the old ones.

> Confirm saturation_v2 Phase 4 cleanup (redundant RC/SC block) is correctly deferred to a separate follow-up PR.

**No** — Phase 4 cleanup is now in scope, landing as commit 3 of the new plan. The deferral was based on the old architectural framing; the new framing requires sat_v2 simplification to complete the per-variant-canonical story.

---

## Reference

- `planning/PR1113-review.md` — Item 2 design + Appendix B (deferred work, much of which is now in scope).
- `planning/multi-analyzer-coder-rules.md` — operational rules; re-read.
- `session/CONVENTIONS.md` — worktree scope, force-push policy, DCO.
- `session/CURRENT.md` § "ENGINE PRs > multi-analyzer-threshold" — reflects this rework plan.
- Engine-side reference: `internal/engines/saturation/engine_v2.go` on the current `be25890f` tip — `applyUniversalThreshold` and `resolveThresholds` are mostly correct; commit 1 of the rework keeps them after stripping the fallback walk.
- Sat_v2-side reference: `internal/engines/analyzers/saturation_v2/analyzer.go` Phases 1-5 + `aggregateByRole` — commit 3 simplifies these.
- Optimizer-side context (out of scope for this PR): `multi-analyzer-optimizer` branch's `pipeline/analyzer_helpers.go` (`bottleneckReplicas`, `safeRemovalReplicas`, etc.) is the consumer that depends on the linearity invariant. Don't touch the optimizer branch from here.

When you finish, write `session/handoffs/multi-analyzer-threshold-status.md` with the new tip + verification results + ready-for-review status. Dean reviews, then approves the force-push to origin.
