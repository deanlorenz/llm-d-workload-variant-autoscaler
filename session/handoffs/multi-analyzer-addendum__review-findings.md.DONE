from: reviewer
session: multi-analyzer-addendum code review

## Review status

Branch `multi-analyzer-addendum` reviewed against plan
`planning/multi-analyzer-addendum-plan.md`. All gates green (make test, make
lint, gofmt, go build, DCO). 4 commits on upstream/main.

Two findings require action before push. Both are in non-Go files or test
strings — no production logic changes needed.

---

## Finding F1 — REQUIRED: Strip plan identifiers from test Describe/It labels

**Files:** `internal/engines/saturation/engine_v2_test.go`

Per CODER-CONVENTIONS §4a, plans-branch identifiers must not appear in
code-side artifacts. These are currently in test string labels:

- Line 283: `Describe("runAnalyzersAndScore enabled gate (MA-F7)", ...)`
- Line 285: `It("MA-F7: disabled analyzer is not appended and its Analyze is never called", ...)`
- Line 316: `Describe("collectV2ModelRequest Disaggregated flag (MA-H-1)", ...)`

Replace with descriptive prose, e.g.:
- `Describe("runAnalyzersAndScore disabled-analyzer gate", ...)`
- `It("disabled analyzer is not appended and its Analyze is never called", ...)`
- `Describe("collectV2ModelRequest Disaggregated flag", ...)`

`T1.4` in `greedy_score_optimizer_test.go:764` follows the existing T1.x
convention already in that file — leave it unchanged.

---

## Finding F2 — REQUIRED: Expand dev guide with architecture, data flow, and optimizer internals

**File:** `docs/developer-guide/multi-analyzer-pipeline.md`

The current doc (commit 3 / `a91c7513`) is missing the architecture-level
content that makes the pipeline understandable to contributors. Add the
following three sections as a new commit (doc-only; no code changes; all
gates expected clean).

Suggested commit message:
`docs: add architecture, data flow, and optimizer internals to pipeline guide`

### Section 1 — insert before `## Components`

```markdown
---

## Architecture

### Data flow per optimize cycle

```
┌──────────────────────────────────────────────────────────┐
│ Config (SaturationScalingConfig per model/namespace)     │
│   Priority, Analyzers[]:                                 │
│     name, enabled, Score,                                │
│     ScaleUpThreshold, ScaleDownBoundary                  │
└──────────────────────────┬───────────────────────────────┘
                           │ engine reads per cycle
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: per-model preparation                            │
│   • BuildVariantStates (GPUsPerReplica per variant       │
│     from ScaleTarget / VA labels)                        │
│   • CollectSchedulerQueueMetrics (shared across          │
│     analyzers)                                           │
│   • resolveThresholds(name, cfg) per analyzer            │
│     (per-analyzer override over model-level globals)     │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: run analyzers, build per-analyzer slice          │
│ Saturation V2 (always first), then each registered       │
│ non-saturation analyzer in registration order:           │
│   • skip if Enabled:false                                │
│   • Analyze(ctx, input) → *AnalyzerResult                │
│   • applyUniversalThreshold(result, scaleUp, scaleDown)  │
│     → writes RC/SC at model scope + each role scope      │
│   • append NamedAnalyzerResult{                          │
│       Name, Result,                                      │
│       Score     ← config.Analyzers[name].Score,          │
│       Remaining ← RC,   Spare ← SC,                      │
│     } to []NamedAnalyzerResult                           │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Engine: build ModelScalingRequest                        │
│   AnalyzerResults  ← per-analyzer slice (above)          │
│   VariantStates    ← prepared above                      │
│   Priority         ← config.Priority                     │
│   Disaggregated    ← any variant has a non-"both" Role   │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│ Optimizer (CostAware or GreedyByScore)                   │
│   • initRoleState → RolePairedState + RoleSpare          │
│   • Scale-up: allocateForModelPaired                     │
│       pick(role) → variant; joint Δ_util commit          │
│       applyAllocation → decrement Remaining              │
│   • Scale-down: scaleDownRoleIterated                    │
│       needsScaleDownForRole → veto gate (ALL must agree) │
│       safeRemovalReplicasForRole → min across analyzers  │
│       applyDeallocationForRole → decrement RoleSpare     │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
                       VariantDecisions
```

### Key concepts

| Concept | Definition |
|---|---|
| **Analyzer** | Implementation of `interfaces.Analyzer`. Examples: saturation V2 (kv-token capacity), throughput (RPS/ITL-derived), queueing-model. |
| **`VariantCapacity`** | Per-variant primitives: `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity` (analyzer-specific units), `Cost`, `AcceleratorName`, `Role`, `TotalDemand`. |
| **`AnalyzerResult`** | Per-(model, analyzer) output: `VariantCapacities[]`, model-level `Total*`, `RoleCapacities[role]` (P/D only), `RequiredCapacity` / `SpareCapacity` (engine-written by post-step; analyzers must not populate these). |
| **`RoleCapacity`** | Per-role aggregate within an `AnalyzerResult`: `TotalSupply`, `TotalDemand`, `TotalAnticipatedSupply`, `RequiredCapacity` / `SpareCapacity` (engine-written). Used for P/D disaggregated models only. |
| **`NamedAnalyzerResult`** | Optimizer-side wrapper: `{Name, Result, Score, Remaining, Spare, RoleSpare}`. Working `Remaining`/`Spare`/`RoleSpare` are decremented by helpers during allocation; `Result` is never mutated. |
| **Linearity invariant** | Adding *n* replicas of variant *v* reduces analyzer *i*'s working `Remaining` by exactly *n × PRC_i[v]*. Holds at model scope (non-disaggregated) and at role scope (disaggregated). |

### Responsibility table

| Field | Written by | Read by |
|---|---|---|
| Per-variant `ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity`, `Cost`, `Role`, `AcceleratorName` | Analyzer | Optimizer (picker + scaling math) |
| Model-level `TotalSupply`, `TotalAnticipatedSupply`, `TotalDemand` | Analyzer (via aggregation helpers) | Engine post-step |
| Per-role `RoleCapacities[role].Total*` | Analyzer (via aggregation helpers) | Engine post-step |
| `RequiredCapacity`, `SpareCapacity` (model + role scope) | **Engine post-step only** — analyzer-written values are overwritten | Optimizer |
| `NamedAnalyzerResult.Remaining`, `Spare`, `RoleSpare` | Optimizer helpers (`applyAllocation`, `applyDeallocationForRole`) | Optimizer allocation loop |

---
```

### Section 2 — insert after `## How results combine` (after its closing `---`)

```markdown
## Data model: AnalyzerResult → NamedAnalyzerResult

Understanding what transforms where prevents the most common mistake: treating
`Result.*` counters as live state during allocation.

**`interfaces.AnalyzerResult`** is the immutable record an analyzer returns.
The engine owns its calibration:

1. The analyzer populates `VariantCapacities[]`, `TotalSupply`, `TotalDemand`,
   `TotalAnticipatedSupply` (and `RoleCapacities` for P/D models). It must NOT
   populate `RequiredCapacity` or `SpareCapacity`.
2. `applyUniversalThreshold` overwrites `RequiredCapacity` / `SpareCapacity` at
   model scope, and each `RoleCapacities[role].RequiredCapacity` /
   `SpareCapacity`. The analyzer's view of supply and demand is fixed here.
3. The engine wraps the calibrated result in a `NamedAnalyzerResult` and never
   mutates `Result` again. `Result.*` values are stable read-only data for the
   rest of the cycle.

**`pipeline.NamedAnalyzerResult`** is the working unit the optimizer operates on.
Its fields fall into three categories:

| Field | Category | Description |
|---|---|---|
| `Name`, `Score`, `Result` | Immutable | Set by engine; never written by optimizer |
| `Remaining`, `Spare` | Mutable scalars | Model-scope working counters; decremented by `applyAllocation` during scale-up |
| `RoleSpare` | Mutable per-role map | Populated by `initRoleState`; decremented by `applyDeallocationForRole` during scale-down |

`Remaining` and `Spare` are seeded from `Result.RequiredCapacity` and
`Result.SpareCapacity`. `RoleSpare` is seeded from
`Result.RoleCapacities[role].SpareCapacity`. None of this flows back into
`Result`.

**`RolePairedState`** (`[]map[string]float64`, indexed as
`[analyzer-index][role]`) is picker-local demand created per call to
`initRoleState`. It holds per-role required capacity for the scale-up loop and
is decremented by the joint-commit step inside `allocateForModelPaired`. It is
not stored on `NamedAnalyzerResult` and is discarded after each model's
allocation pass.

---

## Optimizer internals and helper composition

Both optimizers share the same allocation and scale-down primitives from
`internal/engines/pipeline/analyzer_helpers.go` and
`internal/engines/pipeline/cost_aware_optimizer.go`. The optimizers own the
*when* and *which model*; the helpers own the *how*.

### Scale-up path

All scale-up goes through `allocateForModelPaired`:

```
initRoleState(s)               → roles, RolePairedState (per-role demand + RoleSpare)
anyRoleNeedsScaleUp(ps, roles) → loop gate: any role still has demand?
  pick(role, ...)              → (variant, capN): optimizer-specific variant selector
  roleBottleneckReplicas       → max_i ceil(state[i][role] / PRC_i[v]): cross-analyzer replica sizing
  roleAggRemaining             → max demand across analyzers for this role
  Δ_util = min_role util_role  → joint commit bound: trim to the least-served role
  applyAllocation(s, v, k)     → decrement Remaining on all NamedAnalyzerResults
```

`pick` is a `RolePickFn` — the only part that differs between optimizers:

- `costGreedyRolePick`: picks the cheapest cost-efficient variant; no GPU budget
  cap (unlimited mode).
- `fairShareRolePick`: picks the cheapest variant within available GPU budget;
  caps `capN` to the fair-share target (limited mode).

For non-disaggregated models, `initRoleState` synthesizes a single `"both"` role
from the model-level scalars, so `allocateForModelPaired` handles both the
disaggregated and non-disaggregated cases through the same loop.

### Scale-down path

Both optimizers call `scaleDownRoleIterated`, which handles both disaggregated
and non-disaggregated models through the same role loop (`"both"` is the
synthetic role for non-disaggregated):

```
for each role (sorted for determinism):
  needsScaleDownForRole(s, role)           → gate: ALL analyzers have RoleSpare > 0
  sortVariantsForScaleDown(s, vcs)         → cost-desc; tie-break: Score-weighted PRC asc
  scaleDownVariantSet(...)
    safeRemovalReplicasForRole(s, v, role) → min_i floor(RoleSpare[i][role] / PRC_i[v])
    applyDeallocationForRole(s, v, role, n)→ decrement RoleSpare on all entries
```

`sortVariantsForScaleDown` uses a Score-weighted PRC tie-break. With a single
analyzer (Score=1) this reduces to plain cost-descending / PRC-ascending order.

### Fair-share iteration (GreedyByScoreOptimizer only)

`fairShareScaleUp` uses iterative mean equalization rather than fixed fractions:

1. Compute `mean` = average `remaining` (fair-share priority value) across active
   models.
2. Sort by `remaining` descending; take the highest.
3. Call `allocateForModel` with budget `target = remaining − mean`: allocates
   replicas via `allocateForModelPaired` until the model's priority value drops
   to or below `mean`.
4. Recompute `remaining = fairShareValue(priority, s, ps, roles)` from the
   post-allocation working state.
5. Repeat until no active models remain or no GPUs are left.

`fairShareValue = priority × Σᵢ Score_i × Σ_role pickerState[i][role]`.
A higher `Score` on a high-demand analyzer increases a model's priority value
and therefore how many GPUs it attracts in a constrained environment.

---
```

---

## Finding F3 — NTH (not blocking): optimizers.md consolidation

PR #1223 (ev-shindin, `docs: add scaling optimizers developer guide`) is OPEN.
When it merges, the "Optimizer consumption" section of `multi-analyzer-pipeline.md`
will overlap with it. File a follow-up issue to consolidate (replace the
self-contained paragraph with a link to `optimizers.md`) after #1223 lands.
Not required before this PR merges.

---

## Confirmed correct (no action needed)

- MA-F7 bug fix: `effectiveEnabled` helper correct; skip-the-run (not just
  skip-the-append) confirmed. All 4 unit specs + integration spec cover the
  right behaviors.
- `saturationV2Analyzer` interface widening in `engine.go` is clean; commit 4
  correctly removes the now-redundant type conversion in `engine_register_test.go`.
- MA-H-1 config-bridge specs: Score, Score-default, ScaleUpThreshold override
  all covered. Disaggregated true/false specs correct.
- MA-OPT-4 T1.4: non-uniform Score spec is correct; fsv math matches actual
  `greedy_score_optimizer.go` formula.
- Commit messages match their diffs.
- DCO: all 4 commits signed.
