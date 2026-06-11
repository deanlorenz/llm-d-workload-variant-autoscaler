# Multi-Analyzer Pipeline (developer reference)

The Workload Variant Autoscaler's scaling engine runs multiple **analyzers**
in series each cycle. Each analyzer consumes the same per-replica metrics
and produces an `*interfaces.AnalyzerResult` carrying per-variant capacity,
model-level totals, and (for P/D disaggregated models) per-role capacity.
The engine post-step calibrates `RequiredCapacity` / `SpareCapacity` at
every scope using a uniform threshold formula. The optimizer reads a
per-analyzer slice (`[]NamedAnalyzerResult`) and decides scaling actions
over it via shared free functions in `internal/engines/pipeline/`.

---

## Components

- **Registration** — `internal/engines/saturation/engine.go`:
  `RegisterAnalyzer(name, analyzer) error`. `cmd/main.go` registers external
  analyzers (e.g., throughput) before `StartOptimizeLoop`. Saturation V2 is
  pre-registered at slot 0. The registry is snapshotted at `StartOptimizeLoop`;
  late registration returns an error.
- **Engine post-step** — `internal/engines/saturation/engine_v2.go`:
  `applyUniversalThreshold(*AnalyzerResult, scaleUp, scaleDown)` applies the
  formula `RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)` /
  `SC = max(0, TotalSupply − TotalDemand/scaleDown)` at model scope and
  each role in `RoleCapacities`.
- **Aggregation helpers** — `internal/engines/aggregation/`:
  `SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`,
  `AggregateByRole` over `[]VariantCapacity`. Analyzer authors use these to
  populate per-scope `Total*` fields without reimplementing the math.
- **Optimizer slice flow** — `internal/engines/pipeline/`:
  `NamedAnalyzerResult` slice carries each analyzer's calibrated result plus
  working scratch state for the allocation loop. `CostAwareOptimizer` and
  `GreedyByScoreOptimizer` consume the slice via shared free functions
  (single-variant, paired P/D, and role-iterated helpers).

---

## User configuration

Analyzers are configured via `SaturationScalingConfig.Analyzers` (YAML key
`analyzers`). Each entry is an `AnalyzerScoreConfig` struct
(`internal/config/saturation_scaling.go`):

| Field | Type | Default | Purpose |
|---|---|---|---|
| `name` | string | required | Must match the name returned by `Analyzer.Name()` |
| `enabled` | bool | true | Set false to disable without removing the analyzer |
| `score` | float64 | 1.0 | Weight in the fair-share priority formula |
| `scaleUpThreshold` | float64 | global | Overrides the model-level `scaleUpThreshold` for this analyzer |
| `scaleDownBoundary` | float64 | global | Overrides the model-level `scaleDownBoundary` for this analyzer |

Minimal YAML example:

```yaml
analyzers:
  - name: saturation
    score: 1.0
    scaleUpThreshold: 0.85
    scaleDownBoundary: 0.70
  - name: throughput
    enabled: false   # disable without removing
    score: 2.0
```

When `enabled` is false the analyzer is neither called nor included in the
result slice, so it cannot veto scale-down decisions.

---

## Analyzer implementor guide

Implement `interfaces.Analyzer` (`internal/interfaces/analyzer.go`):

```go
type Analyzer interface {
    Name() string
    Analyze(ctx context.Context, input AnalyzerInput) (*AnalyzerResult, error)
}
```

### Input

Key `AnalyzerInput` fields:

| Field | Type | Description |
|---|---|---|
| `ModelID` | string | Model being analyzed |
| `Namespace` | string | Kubernetes namespace |
| `ReplicaMetrics` | `[]ReplicaMetrics` | Per-replica metric snapshots |
| `VariantStates` | `[]VariantReplicaState` | Current/desired/pending replica counts per variant |
| `Config` | `AnalyzerConfig` | Resolved config (cast to your config type as needed) |
| `SchedulerQueue` | `*SchedulerQueueMetrics` | Scheduler queue metrics; nil when flow control is off |

### Output invariants

The **linearity invariant**: `TotalSupply = Σ_v PerReplicaCapacity × ReplicaCount`
across all entries in `VariantCapacities`. Use the aggregation helpers to
populate `VariantCapacities[]`, then call:

```go
result.TotalSupply             = aggregation.SumTotalSupply(result.VariantCapacities)
result.TotalDemand             = aggregation.SumTotalDemand(result.VariantCapacities)
result.TotalAnticipatedSupply  = aggregation.SumTotalAnticipatedSupply(result.VariantCapacities)
```

For P/D disaggregated models, also populate `RoleCapacities` using
`aggregation.AggregateByRole(result.VariantCapacities)`. The engine applies
`applyUniversalThreshold` to every role entry.

**Do NOT populate `RequiredCapacity` or `SpareCapacity`** in the returned
`AnalyzerResult`. The engine overwrites both fields in the post-step; any
analyzer-written values are discarded.

---

## Pipeline flow

1. `cmd/main.go` calls `engine.RegisterAnalyzer(name, a)` for each external
   analyzer before `StartOptimizeLoop`. Saturation V2 is pre-registered at
   slot 0.
2. `StartOptimizeLoop` snapshots the registry into `analyzersSnapshot`
   (frozen, race-safe). The snapshot is the ordered set of analyzers that
   every optimize cycle iterates.
3. Per cycle, for each model: `runAnalyzersAndScore` runs the saturation V2
   analyzer unconditionally (it drives variant metadata), then iterates
   `analyzersSnapshot` in registration order for non-saturation analyzers.
4. Analyzers with `Enabled: false` are skipped entirely — neither called nor
   appended to the result slice.
5. For each analyzer that runs, `applyUniversalThreshold` is applied to its
   result using resolved thresholds (per-analyzer override beats global):
   `RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)`,
   `SC = max(0, TotalSupply − TotalDemand/scaleDown)`.
6. Each result is wrapped in a `NamedAnalyzerResult{Name, Result, Score,
   Remaining, Spare}` and appended to the `[]NamedAnalyzerResult` slice.
   `Remaining = RC` and `Spare = SC` after the post-step.
7. Saturation is always first. Its `VariantCapacities` entries carry `Cost`,
   `AcceleratorName`, and `Role` used downstream by the optimizer and
   enforcer.

---

## How results combine

**Scale-down gate** (`needsScaleDownForRole`): ALL non-disabled analyzers in
the slice must have `Spare > 0` for a role to scale down. One analyzer with
`RequiredCapacity > 0` (i.e., `Spare == 0`) blocks scale-down for that role.

**Scale-up gate** (`anyRoleNeedsScaleUp`): ANY analyzer having `Remaining > 0`
triggers scale-up for the corresponding role.

The saturation entry in the slice is also the keeper of per-variant metadata
(`Cost`, `AcceleratorName`, `Role`) that the optimizer reads from
`VariantCapacities`. Future work will extract per-variant metadata collection
out of the saturation result so each analyzer owns only its own signals.

---

## Optimizer consumption

The `[]NamedAnalyzerResult` slice is passed to one of two optimizers depending
on the `enableLimiter` flag in `SaturationScalingConfig`:

- **`CostAwareOptimizer`** (unlimited mode, `enableLimiter: false`): operates
  on the saturation entry's `VariantCapacities` for cost and role data; scales
  up the cheapest variant that covers the required capacity, scales down the
  most expensive variant with spare capacity.
- **`GreedyByScoreOptimizer`** (limited mode, `enableLimiter: true`): respects
  `ResourceConstraints` (GPU budgets per accelerator type). Models are ordered
  by fair-share priority value:
  `fsv = Priority × Σᵢ Score_i × Σ_role pickerState[i][role]`,
  where the sum over `i` runs across all `NamedAnalyzerResult` entries and
  `pickerState` is seeded from each entry's `Remaining`. Higher `Score` on a
  high-demand analyzer increases a model's allocation priority in constrained
  environments.

Both optimizers are stateless and selected per-cycle from the engine's
`optimizer` field.
