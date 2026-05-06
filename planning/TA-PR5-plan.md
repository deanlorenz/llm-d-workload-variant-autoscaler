# TA PR-5: Register ThroughputAnalyzer in the Engine

> **Status: PLANNED** — Target branch TA3 (or TA4 if scope grows).
> Depends on: TA1 (#1051), TA2 (#1052), TA3/PR-4, and the ENGINE multi-analyzer PR.
> Part of #1005; does not close it.

---

## Context

The ENGINE multi-analyzer PR (see `ideas/ENGINE-multi-analyzer-plan.md`) generalizes
`runAnalyzersAndScore()` into a generic map-based loop and implements the correct
combine algorithm. That PR adds the `analyzers map[string]interfaces.Analyzer` field
to the `Engine` struct and calls `RegisterThroughputAnalyzerQueries()`.

**This PR (TA PR-5) registers the ThroughputAnalyzer into that map** and validates
the end-to-end TA signal path with targeted tests.

**Scope:** TA registration and TA-specific e2e scenarios. No changes to the ENGINE
combine logic, no changes to the analyzer package, no changes to the optimizer.

---

## What Is Already in Place After ENGINE PR Merges

- `Engine.analyzers` map — generic name → `interfaces.Analyzer` registry
- `runAnalyzersAndScore()` — generic loop, dimensionless combine, any-up/all-down
- `registration.RegisterThroughputAnalyzerQueries()` — called from `NewEngine()`
- `replica_metrics.go` — populates `GenerationTokenRate`, `KvUtilization`, `VLLMRequestRate`
  on every cycle

---

## What TA PR-5 Does

### Size assessment

The ENGINE PR has already done the heavy lifting: map registration pattern, query
registration call, and combine logic. TA PR-5 only needs to verify that
`ThroughputAnalyzer` is correctly in the map and add TA-specific e2e scenarios.

**If the ENGINE PR adds the throughput entry to `NewEngine()` as a code example** (as
described in `ENGINE-multi-analyzer-plan.md`), TA PR-5 may be trivially small — just
the e2e tests and any config-level documentation. In that case, merge into TA3.

**If ENGINE PR leaves the map empty** (just the infrastructure), TA PR-5 adds:

```go
// in NewEngine(), alongside the saturation entry:
throughput.AnalyzerName: throughput.NewThroughputAnalyzer(),
```

Either way, the net code change is tiny. Merge into TA3.

---

## Key Design Decisions (from ENGINE plan, applied here)

### Saturation always runs

Even when `saturation: enabled: false`, saturation's `VariantCapacities` carry `Cost`
and `AcceleratorName` that the optimizer needs. The `enabled` flag only controls whether
saturation's RC/SC enter the combine.

### TA-only mode with CostAwareOptimizer

When testing TA in isolation (`saturation: enabled: false`):
- Saturation RC/SC = 0 (excluded from combine)
- Saturation's VariantCapacities still flow to the optimizer (Cost, AcceleratorName)
- Use `CostAwareOptimizer` (no GPU limiting) — this is already the default
- `GreedyByScoreOptimizer` (GPU-limiting mode) works too because saturation's
  VariantCapacities still have correct AcceleratorName

### No TA-specific config

`ThroughputAnalyzer.Analyze()` uses internal constants; ignores `input.Config`.
No new ConfigMap type needed.

### SchedulerQueue stays nil

`AnalyzerInput.SchedulerQueue` = nil. `estimateQueueDemand` returns 0 gracefully.

---

## E2E Tests (TA-specific)

These complement the ENGINE PR's e2e tests which verify the combine logic itself.

| Scenario | Config | Expected |
|---|---|---|
| **TA-only scale-up** | `saturation: enabled:false`, `throughput: enabled:true, score:1.0`; simulator with high RPS relative to single-replica tok/s supply | TA RC > 0 → replica added |
| **TA-only scale-down** | Same config; load drops, EPP deployed | TA SC > 0 → replica removed |
| **Dual-analyzer scale-up** | Both enabled; saturation idle, TA detects overload | Combined RC > 0, replica added |
| **Dual-analyzer scale-down blocked** | Saturation says idle, TA still sees load | Combined SC = 0 (all-down requires agreement), no scale-down |
| **Cold-start** | 0 replicas, TA RC > 0 | Scale-up to 1 replica triggered |

Simulator parameters used: `--inter-token-latency`, `--max-num-seqs`, `--kv-cache-size`,
`--block-size`.

---

## Files to Change (TA PR-5)

| File | Change |
|---|---|
| `internal/engines/saturation/engine.go` | Add `throughput.AnalyzerName: throughput.NewThroughputAnalyzer()` to `engine.analyzers` (if not done in ENGINE PR) |
| `test/e2e/...` | TA-specific e2e scenarios above |

If the ENGINE PR already added the map entry, TA PR-5 is e2e tests only.

---

## Not in This PR

- SchedulerQueue wiring (flow control metrics)
- Tier-3 `itlKnowledgeStore` wiring
- `DefaultKSat` unification with EPP system-wide k_sat
- Prefill-specific rate signals
- Renaming `saturation` engine package
