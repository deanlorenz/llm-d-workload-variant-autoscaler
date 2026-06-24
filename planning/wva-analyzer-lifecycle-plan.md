> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L44:91
- [Design decisions {#design-decisions}](#design-decisions-design-decisions) L92:145
- [Scope {#scope}](#scope-scope) L146:167
- [Commit 1 — ManagedAnalyzer interface + stubs {#commit-1}](#commit-1--managedanalyzer-interface--stubs-commit-1) L168:289
  - [1a. New file: `internal/engines/saturation/managed_analyzer.go`](#1a-new-file-internalenginessaturationmanagedanalyzergo) L176:214
  - [1b. satv2: add stub lifecycle methods](#1b-satv2-add-stub-lifecycle-methods) L215:236
  - [1c. TA: add real (no-op) lifecycle methods](#1c-ta-add-real-no-op-lifecycle-methods) L237:258
  - [1d. Test stubs](#1d-test-stubs) L259:274
  - [Commit message](#commit-message) L275:289
- [Commit 2 — satv2 disabled-flag implementation {#commit-2}](#commit-2--satv2-disabled-flag-implementation-commit-2) L290:415
  - [2a. Add `disabled` field to `SaturationAnalyzer`](#2a-add-disabled-field-to-saturationanalyzer) L298:313
  - [2b. Implement lifecycle methods (replace stubs from Commit 1)](#2b-implement-lifecycle-methods-replace-stubs-from-commit-1) L314:334
  - [2c. Modify `Analyze()` for the disabled path](#2c-modify-analyze-for-the-disabled-path) L335:385
  - [Tests for Commit 2](#tests-for-commit-2) L386:399
  - [Commit message](#commit-message) L400:415
- [Commit 3 — Engine live-set refactor {#commit-3}](#commit-3--engine-live-set-refactor-commit-3) L416:677
  - [3a. New types in `engine.go`](#3a-new-types-in-enginego) L424:437
  - [3b. Engine struct changes](#3b-engine-struct-changes) L438:450
  - [3c. `NewEngine` signature change](#3c-newengine-signature-change) L451:478
  - [3d. Remove `RegisterAnalyzer` method](#3d-remove-registeranalyzer-method) L479:490
  - [3e. `StartOptimizeLoop` cleanup](#3e-startoptimizeloop-cleanup) L491:504
  - [3f. New method: `syncManagedAnalyzers`](#3f-new-method-syncmanagedanalyzers) L505:579
  - [3g. Fix `effectiveEnabled`](#3g-fix-effectiveenabled) L580:603
  - [3h. Update `runAnalyzersAndScore` to use `liveManaged`](#3h-update-runanalyzersandscore-to-use-livemanaged) L604:638
  - [3i. Call `syncManagedAnalyzers` in `optimize()`](#3i-call-syncmanagedanalyzers-in-optimize) L639:661
  - [Commit message](#commit-message) L662:677
- [Commit 4 — cmd/main.go: factory wiring + remove startup gate {#commit-4}](#commit-4--cmdmaingo-factory-wiring--remove-startup-gate-commit-4) L678:741
  - [4a. Remove `throughputAnalyzerEnabled`](#4a-remove-throughputanalyzerenabled) L685:703
  - [4b. Build factory slice and pass to `NewEngine`](#4b-build-factory-slice-and-pass-to-newengine) L704:719
  - [4c. Update `throughput.New()`](#4c-update-throughputnew) L720:727
  - [Commit message](#commit-message) L728:741
- [Commit 5 — Developer guide {#commit-5}](#commit-5--developer-guide-commit-5) L742:802
  - [Target file](#target-file) L749:756
  - [Sections to add or update](#sections-to-add-or-update) L757:789
  - [Commit message](#commit-message) L790:802
- [Testing summary {#testing-summary}](#testing-summary-testing-summary) L803:840

## Overview {#overview}

[↑ TOC](#toc)

**Type:** 3 (task plan) · **Branch:** `wva-analyzer-lifecycle` off `main`

**Problem.** Analyzer registration is code-driven (frozen at startup) and disconnected
from configuration. Five correctness gaps result:

1. `effectiveEnabled` returns `true` for absent config entries — unconfigured analyzers
   silently run and can veto scale-down.
2. `throughputAnalyzerEnabled` in `cmd/main.go` reads config at init-time before the
   ConfigMap reconciler has populated the store — throughput is never registered in a
   fresh cluster deployment.
3. Adding an analyzer to `cfg.Analyzers` at runtime has no effect — `analyzersSnapshot`
   is frozen at `StartOptimizeLoop` and never refreshed.
4. The startup gate and per-cycle gate are inconsistent, duplicated, and fragile.
5. Tests assert `effectiveEnabled` returns `true` for absent entries (wrong).

**Solution.** Make the active analyzer set config-driven, not code-driven:

- Introduce `ManagedAnalyzer` interface (in saturation package) extending
  `interfaces.Analyzer` with `Activate`, `Deactivate`, `Reactivate` lifecycle callbacks.
- Engine maintains a live set derived from config, refreshed at the start of each
  optimize cycle. Lifecycle callbacks fire synchronously (engine loop is blocked during
  transition — natural, since it is all one goroutine).
- `cmd/main.go` registers a static factory slice (no boolean gate); activation is
  config-driven per-cycle.
- satv2 is special: always in the live set; `Deactivate` sets an internal `disabled`
  flag that changes what `Analyze` returns (metadata only, no scaling signal).
- Fix `effectiveEnabled` absent-entry default from `true` to `false`.

**Files changed (high-level):**

| File | Change |
|---|---|
| `internal/engines/saturation/managed_analyzer.go` | NEW — `ManagedAnalyzer` interface |
| `internal/interfaces/analyzer.go` | No change (import-cycle constraint) |
| `internal/engines/analyzers/saturation_v2/analyzer.go` | Add `disabled` flag; implement lifecycle |
| `internal/engines/analyzers/throughput/analyzer.go` | Implement lifecycle (no-ops for now) |
| `internal/engines/analyzers/queueingmodel/analyzer.go` | No change (out of scope) |
| `internal/engines/saturation/engine.go` | Replace frozen snapshot with live set |
| `internal/engines/saturation/engine_v2.go` | Fix `effectiveEnabled`; iterate live set |
| `cmd/main.go` | Remove startup gate; pass factory slice to `NewEngine` |
| `docs/developer-guide/...` | Lifecycle protocol section |

---

## Design decisions {#design-decisions}

[↑ TOC](#toc)

These were settled in planning and must not be revisited in the implementation.
Surface any code-level blocker via a handoff.

**D1 — `ManagedAnalyzer` in saturation package, not `interfaces`.**
`config` already imports `interfaces`; adding `config.AnalyzerScoreConfig` to
`interfaces.Analyzer` would create a cycle. The lifecycle interface lives in
`internal/engines/saturation/managed_analyzer.go`. Verify: `grep -n "interfaces"
internal/config/config.go` should show the existing import.

**D2 — Three lifecycle callbacks, not two.**
`Activate(ctx, cfg)` — first entry into the live set (or re-entry after deactivate).
`Deactivate(ctx)` — removed from desired set.
`Reactivate(ctx, newCfg)` — still in live set, but its `AnalyzerScoreConfig` entry
changed (score, threshold overrides, etc.).
All three are called synchronously in the engine goroutine before `runAnalyzersAndScore`
runs. No goroutine, no channel, no extra mutex beyond what already exists.

**D3 — Global-default config drives lifecycle; per-model config drives per-cycle gate.**
The engine derives the desired set from `globalSatCfgMap["default"].Analyzers` (the
existing global default, used in the same `optimize()` call today at line ~406 of
`engine.go`). An analyzer in any per-model config override but absent from the global
default is not activated. This constraint is documented in the developer guide and can
be relaxed later. The per-cycle `effectiveEnabled` check per model still runs; it gates
whether the activated analyzer's result is included for that specific model.

**D4 — satv2 always retained; `Deactivate` sets `disabled` flag only.**
The engine adds satv2 to the live set at construction and never removes it. This is
required because `runV2AnalysisOnly` (which must always run for per-variant metadata)
calls `satV2.Analyze()`. When disabled: `Analyze()` still populates `VariantCapacities`
with metadata (AcceleratorName, Cost, Role, ReplicaCount) but sets `TotalDemand = 0`,
`TotalSupply = 0`, `TotalAnticipatedSupply = 0`. `applyUniversalThreshold` then
produces `RC = 0`, `SC = 0` — no scale-up, no scale-down from saturation. The optimizer
sees the per-variant metadata and makes no saturation-driven changes.

**D5 — `effectiveEnabled` absent-entry default changes from `true` to `false`.**
Registered-but-unconfigured analyzers must not run. Saturation is unaffected (it is
always retained by D4 and not gated by `effectiveEnabled`).

**D6 — Source registration (Prometheus query templates) is not dynamic in this PR.**
`RegisterSaturationQueries`, `RegisterThroughputAnalyzerQueries`, and
`RegisterQueueingModelQueries` stay in `NewEngine` as-is. When an analyzer needs
source registration tied to activation, implement it inside `Activate()`. Document this
as the convention in the developer guide. No runtime source-registry changes in this PR.

**D7 — QM is out of scope.**
`QueueingModelAnalyzer` uses a completely different engine path (`optimizeQueueingModel`)
and does not participate in the factory/live-set mechanism. Do not change it.

---

## Scope {#scope}

[↑ TOC](#toc)

**In scope (V2 saturation path only):**
- `ManagedAnalyzer` interface definition
- satv2 `disabled`-flag lifecycle
- TA lifecycle (no-ops)
- Engine live-set refactor (replaces `analyzers`/`analyzersSnapshot`/`started`/`RegisterAnalyzer`)
- `effectiveEnabled` default fix (absent → false)
- Remove `throughputAnalyzerEnabled` startup gate
- Factory wiring in `cmd/main.go`
- Developer guide section

**Out of scope (do not touch):**
- V1 path, QM path — no behavioral changes
- CRD fields, ConfigMap schema, annotation keys — no changes
- Source registry dynamic wiring — deferred (D6)
- satv2 internal refactor (separating common data-init from saturation analysis) — deferred

---

## Commit 1 — ManagedAnalyzer interface + stubs {#commit-1}

[↑ TOC](#toc)

**Purpose.** Introduce the lifecycle interface and add stub implementations to all
affected types. After this commit: compiles cleanly; all existing tests pass; stubs
return nil / no-op.

### 1a. New file: `internal/engines/saturation/managed_analyzer.go`

```go
package saturation

import (
    "context"

    "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/config"
    "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// ManagedAnalyzer extends interfaces.Analyzer with lifecycle callbacks driven
// by changes to the engine's active analyzer set. All callbacks are invoked
// synchronously in the engine's optimize goroutine before runAnalyzersAndScore
// runs; the loop is effectively blocked during any transition.
//
// Activate is called when the analyzer first enters the live set (or re-enters
// after a Deactivate). Deactivate is called when it leaves. Reactivate is called
// when the analyzer remains in the live set but its AnalyzerScoreConfig entry
// changed (score, threshold overrides, enabled flag). All three receive the
// config entry that is active at the moment of the call.
//
// Implementing an analyzer:
//   - Activate: initialize state, register Prometheus source templates if needed.
//   - Deactivate: release state that should not persist across a disable/re-enable.
//   - Reactivate: update any cached config; avoid tearing down state unnecessarily.
//   - Analyze: must tolerate being called only while Activated.
type ManagedAnalyzer interface {
    interfaces.Analyzer

    Activate(ctx context.Context, cfg config.AnalyzerScoreConfig) error
    Deactivate(ctx context.Context) error
    Reactivate(ctx context.Context, newCfg config.AnalyzerScoreConfig) error
}
```

[↑ TOC](#toc)

### 1b. satv2: add stub lifecycle methods

In `internal/engines/analyzers/saturation_v2/analyzer.go`, add three methods to
`SaturationAnalyzer`. These are stubs for Commit 1; real implementation follows in
Commit 2.

```go
func (a *SaturationAnalyzer) Activate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    return nil
}

func (a *SaturationAnalyzer) Deactivate(_ context.Context) error {
    return nil
}

func (a *SaturationAnalyzer) Reactivate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    return nil
}
```

[↑ TOC](#toc)

### 1c. TA: add real (no-op) lifecycle methods

In `internal/engines/analyzers/throughput/analyzer.go`. TA has no per-activation
state today, so the implementations are the permanent no-ops (not temporary stubs —
these are the final implementation for this PR):

```go
func (a *ThroughputAnalyzer) Activate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    return nil
}

func (a *ThroughputAnalyzer) Deactivate(_ context.Context) error {
    return nil
}

func (a *ThroughputAnalyzer) Reactivate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    return nil
}
```

[↑ TOC](#toc)

### 1d. Test stubs

Find every `interfaces.Analyzer` stub/fake in test files:

```bash
grep -rn "func.*Analyze(ctx\|interfaces\.Analyzer" internal/engines/saturation/ --include="*_test.go"
```

Files expected:
- `engine_register_test.go` — `spyAnalyzer`
- `engine_v2_population_test.go` — `fakeAnalyzerWithResult`

Add stub lifecycle methods to each test double (same no-op pattern as 1b).

[↑ TOC](#toc)

### Commit message

```
engines/saturation: introduce ManagedAnalyzer lifecycle interface

Add ManagedAnalyzer to the saturation package (not interfaces — config
imports interfaces, creating a cycle if lifecycle methods reference
config.AnalyzerScoreConfig there). Extend satv2 and ThroughputAnalyzer
with stub/no-op implementations; update test doubles. No behaviour change.
```

[↑ TOC](#toc)

---

## Commit 2 — satv2 disabled-flag implementation {#commit-2}

[↑ TOC](#toc)

**Purpose.** Implement the real lifecycle on satv2. After this commit: satv2 correctly
returns no-scaling-signal when deactivated, while still providing per-variant metadata
that the rest of the pipeline depends on.

### 2a. Add `disabled` field to `SaturationAnalyzer`

```go
type SaturationAnalyzer struct {
    mu                     sync.Mutex
    computeCapacityHistory map[string]*rollingAverage
    capacityStore          *CapacityKnowledgeStore
    disabled               bool  // set by Deactivate; cleared by Activate
}
```

`disabled` is written only during lifecycle callbacks, which fire in the engine's
single optimize goroutine. No separate mutex needed for this field.

[↑ TOC](#toc)

### 2b. Implement lifecycle methods (replace stubs from Commit 1)

```go
func (a *SaturationAnalyzer) Activate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    a.disabled = false
    return nil
}

func (a *SaturationAnalyzer) Deactivate(_ context.Context) error {
    a.disabled = true
    return nil
}

func (a *SaturationAnalyzer) Reactivate(_ context.Context, _ config.AnalyzerScoreConfig) error {
    // No persistent state to update for config changes.
    return nil
}
```

[↑ TOC](#toc)

### 2c. Modify `Analyze()` for the disabled path

At the **top** of `Analyze()` (after the satConfig type-assert), add:

```go
if a.disabled {
    return a.analyzeDisabled(input), nil
}
```

Add the helper:

```go
// analyzeDisabled returns per-variant metadata with zero scaling signal.
// Called when satv2 is deactivated. The engine always calls satv2.Analyze()
// (via runV2AnalysisOnly) regardless of enabled state; the caller
// depends on VariantCapacities for AcceleratorName/Cost/Role/ReplicaCount.
// TotalDemand = TotalSupply = 0 causes applyUniversalThreshold to produce
// RC = 0, SC = 0 — no scale-up, no scale-down from saturation.
func (a *SaturationAnalyzer) analyzeDisabled(input interfaces.AnalyzerInput) *interfaces.AnalyzerResult {
    result := &interfaces.AnalyzerResult{
        AnalyzerName: a.Name(),
        ModelID:      input.ModelID,
        Namespace:    input.Namespace,
        AnalyzedAt:   time.Now(),
    }
    for _, vs := range input.VariantStates {
        result.VariantCapacities = append(result.VariantCapacities, interfaces.VariantCapacity{
            VariantName:  vs.VariantName,
            Role:         vs.Role,
            ReplicaCount: vs.CurrentReplicas,
        })
    }
    // AcceleratorName and Cost come from the capacity store (pre-populated by the
    // engine before Analyze is called). Read them for each variant.
    for i, vc := range result.VariantCapacities {
        if entry := a.capacityStore.Get(input.Namespace, input.ModelID, vc.VariantName); entry != nil {
            result.VariantCapacities[i].AcceleratorName = entry.AcceleratorName
            result.VariantCapacities[i].Cost = entry.Cost
        }
    }
    return result
}
```

Verify the `CapacityKnowledgeStore.Get` signature in `capacity_store.go` and adjust
parameter names/types accordingly. If the store does not have a `Get` method, add one
(returns the stored entry for a namespace/modelID/variantName key, or nil).

[↑ TOC](#toc)

### Tests for Commit 2

In `internal/engines/analyzers/saturation_v2/analyzer_test.go`:

- `It("returns metadata-only result when disabled")`:
  - Call `Deactivate`, then `Analyze` with non-empty `VariantStates`.
  - Assert: `TotalDemand == 0`, `TotalSupply == 0`, `TotalAnticipatedSupply == 0`.
  - Assert: `VariantCapacities` has one entry per VariantState with correct VariantName.
- `It("returns full result when activated after deactivate")`:
  - Call `Deactivate`, then `Activate`, then `Analyze` with metrics.
  - Assert: `TotalDemand > 0` (normal computation resumes).

[↑ TOC](#toc)

### Commit message

```
engines/saturation_v2: implement disabled-flag lifecycle

Deactivate sets disabled=true; Analyze returns per-variant metadata
with TotalDemand=TotalSupply=0 when disabled, so applyUniversalThreshold
produces RC=SC=0 (no scaling signal). VariantCapacities is always
populated — the pipeline requires AcceleratorName/Cost/Role regardless
of saturation enabled state. Activate clears the flag.
```

[↑ TOC](#toc)

---

## Commit 3 — Engine live-set refactor {#commit-3}

[↑ TOC](#toc)

**Purpose.** Replace the frozen `analyzersSnapshot` pattern with a per-cycle live set
driven by config. Remove `RegisterAnalyzer`, `analyzers`, `analyzersSnapshot`, `started`.
Add `syncManagedAnalyzers` called once per optimize cycle.

### 3a. New types in `engine.go`

```go
// managedEntry tracks a live ManagedAnalyzer with its last-seen config snapshot.
// The config snapshot is used to detect Reactivate-worthy changes each cycle.
type managedEntry struct {
    name      string
    analyzer  ManagedAnalyzer
    activeCfg config.AnalyzerScoreConfig
}
```

[↑ TOC](#toc)

### 3b. Engine struct changes

**Remove** from `Engine`:
- `analyzers []analyzerEntry`
- `analyzersSnapshot []analyzerEntry`
- `started bool`

**Add** to `Engine`:
- `managedAnalyzers map[string]ManagedAnalyzer` — factory map, set at construction, never modified
- `liveManaged []managedEntry` — per-cycle live set, updated by `syncManagedAnalyzers`

[↑ TOC](#toc)

### 3c. `NewEngine` signature change

Accept an additional `managed []ManagedAnalyzer` parameter (placed after `cfg *config.Config`):

```go
func NewEngine(client client.Client, apiReader client.Reader, scheme *runtime.Scheme,
    recorder record.EventRecorder, metricsRegistry *source.SourceRegistry,
    cfg *config.Config, managed []ManagedAnalyzer) *Engine {
```

In the body, build the factory map:

```go
managedMap := make(map[string]ManagedAnalyzer, len(managed))
for _, a := range managed {
    managedMap[a.Name()] = a
}
```

Remove the `analyzers: []analyzerEntry{{...}}` initializer from the struct literal.
Add `managedAnalyzers: managedMap` to the struct literal.

Call `satV2.Activate(context.Background(), config.AnalyzerScoreConfig{})` immediately
after construction to establish the enabled state. (satv2 starts enabled; the config
entry passed here is empty — satv2 ignores it.)

[↑ TOC](#toc)

### 3d. Remove `RegisterAnalyzer` method

Delete the entire `RegisterAnalyzer` function from `engine.go`.

Behavioral-contract change grep — run and update all hits:
```bash
grep -rn "RegisterAnalyzer\|analyzersSnapshot\|\.started\b" \
    internal/engines/saturation/ --include="*.go"
```

[↑ TOC](#toc)

### 3e. `StartOptimizeLoop` cleanup

Remove the snapshot logic:
```go
// DELETE these two lines:
e.analyzersSnapshot = make([]analyzerEntry, len(e.analyzers))
copy(e.analyzersSnapshot, e.analyzers)
e.started = true
```

The method body now just records the optimizer and starts the executor.

[↑ TOC](#toc)

### 3f. New method: `syncManagedAnalyzers`

Add to `engine.go` (or `engine_v2.go`):

```go
// syncManagedAnalyzers reconciles the live managed analyzer set against
// the desired set derived from the global default saturation config.
// Called once at the start of each optimize cycle, before runAnalyzersAndScore.
// Desired set = {aw.Name : aw in globalCfg.Analyzers if effectiveEnabled(aw.Name, globalCfg)}.
// Names not found in managedAnalyzers are logged and skipped (config error).
// satv2 is handled separately and is never in liveManaged.
func (e *Engine) syncManagedAnalyzers(ctx context.Context, globalCfg config.SaturationScalingConfig) {
    // Build desired set
    desired := make(map[string]config.AnalyzerScoreConfig, len(globalCfg.Analyzers))
    for _, aw := range globalCfg.Analyzers {
        if aw.Name == interfaces.SaturationAnalyzerName {
            continue // satv2 managed separately
        }
        if effectiveEnabled(aw.Name, globalCfg) {
            desired[aw.Name] = aw
        }
    }

    // Activate new entries; reactivate changed ones
    liveByName := make(map[string]int, len(e.liveManaged))
    for i, entry := range e.liveManaged {
        liveByName[entry.name] = i
    }
    for name, cfg := range desired {
        impl, ok := e.managedAnalyzers[name]
        if !ok {
            ctrl.LoggerFrom(ctx).Error(nil, "analyzer in config not found in factory; skipping",
                "analyzer", name)
            continue
        }
        idx, live := liveByName[name]
        if !live {
            if err := impl.Activate(ctx, cfg); err != nil {
                ctrl.LoggerFrom(ctx).Error(err, "Activate failed; analyzer skipped", "analyzer", name)
                continue
            }
            e.liveManaged = append(e.liveManaged, managedEntry{name: name, analyzer: impl, activeCfg: cfg})
        } else if e.liveManaged[idx].activeCfg != cfg {
            if err := impl.Reactivate(ctx, cfg); err != nil {
                ctrl.LoggerFrom(ctx).Error(err, "Reactivate failed; keeping previous config", "analyzer", name)
                continue
            }
            e.liveManaged[idx].activeCfg = cfg
        }
    }

    // Deactivate entries no longer in desired set
    kept := e.liveManaged[:0]
    for _, entry := range e.liveManaged {
        if _, ok := desired[entry.name]; ok {
            kept = append(kept, entry)
        } else {
            if err := entry.analyzer.Deactivate(ctx); err != nil {
                ctrl.LoggerFrom(ctx).Error(err, "Deactivate failed", "analyzer", entry.name)
            }
        }
    }
    e.liveManaged = kept
}
```

Note: `config.AnalyzerScoreConfig` must be comparable (all fields comparable) for the
`!=` check. Verify: it contains `string`, `*bool`, `float64`, `*float64`. Pointer
comparison checks identity, not value — if the config store returns new structs each
cycle, two identical configs may not be `==`. If this is the case, replace the `!=`
comparison with a value-equality helper or always call `Reactivate` when the analyzer
is already live (simpler, safe for no-op `Reactivate` implementations).

[↑ TOC](#toc)

### 3g. Fix `effectiveEnabled`

In `engine_v2.go`, change the final `return true` to `return false` and update the
comment:

```go
// effectiveEnabled returns true only when the analyzer has an explicit
// entry in cfg.Analyzers that is enabled (nil Enabled → true; explicit
// false → false). Absent entries return false — analyzers are opt-in.
func effectiveEnabled(analyzerName string, cfg config.SaturationScalingConfig) bool {
    for _, aw := range cfg.Analyzers {
        if aw.Name == analyzerName {
            if aw.Enabled != nil {
                return *aw.Enabled
            }
            return true
        }
    }
    return false  // absent → opt-in default: do not run
}
```

[↑ TOC](#toc)

### 3h. Update `runAnalyzersAndScore` to use `liveManaged`

Replace the `analyzersSnapshot` loop (current lines 146–166 of `engine_v2.go`) with a
loop over `e.liveManaged`. The loop body is otherwise identical: check `effectiveEnabled`
per-model config, call `runRegisteredAnalyzer`, apply threshold post-step, append to
`namedResults`.

```go
for _, entry := range e.liveManaged {
    if !effectiveEnabled(entry.name, config) {
        continue
    }
    result := runRegisteredAnalyzer(ctx, logger, analyzerEntry{name: entry.name, analyzer: entry.analyzer}, modelID, input)
    if result == nil {
        continue
    }
    up, down := resolveThresholds(entry.name, config)
    applyUniversalThreshold(result, up, down)
    namedResults = append(namedResults, pipeline.NamedAnalyzerResult{
        Name:      entry.name,
        Result:    result,
        Score:     scoreForAnalyzer(entry.name, config),
        Remaining: result.RequiredCapacity,
        Spare:     result.SpareCapacity,
    })
}
```

Note: `runRegisteredAnalyzer` currently takes `analyzerEntry`. Either update its
signature to take `(name string, analyzer interfaces.Analyzer)` directly, or keep
the wrapper struct. Whichever is smaller. **Do not change** `runRegisteredAnalyzer`'s
recover/error-handling logic.

[↑ TOC](#toc)

### 3i. Call `syncManagedAnalyzers` in `optimize()`

In `engine.go`'s `optimize()`, after the global saturation config is resolved
(after line ~409: `if cfg, ok := globalSatCfgMap["default"]; ok { ... }`), add:

```go
e.syncManagedAnalyzers(ctx, globalCfgForSync)
```

where `globalCfgForSync` is the resolved default config. Handle the case where no
default entry exists (pass zero-value `config.SaturationScalingConfig{}`).

Also: handle satv2 lifecycle in `optimize()`. If satv2 is in the global Analyzers list
with `enabled:false`, call `satV2.Deactivate(ctx)`. If it was disabled and now
`enabled:true` or absent-with-opt-in: do NOT re-activate (D5 says absent → false, so
absent means satv2 stays in whatever state it is — typically enabled from construction).
For simplicity in this PR: call `satV2.Reactivate(ctx, satV2CfgEntry)` when the
saturation config changes and satv2 is in the Analyzers list; call `satV2.Deactivate`
only if explicitly `enabled:false`. A follow-up can tighten this once the refactor
separates satv2's common data-init from its analysis logic.

[↑ TOC](#toc)

### Commit message

```
engines/saturation: replace frozen analyzer snapshot with live config-driven set

Remove RegisterAnalyzer, analyzers slice, analyzersSnapshot, and started flag.
Engine now maintains liveManaged, reconciled each optimize cycle against the
global default saturation config via syncManagedAnalyzers. Lifecycle callbacks
(Activate/Deactivate/Reactivate) fire synchronously in the optimize goroutine.
Fix effectiveEnabled: absent config entries now return false (opt-in default).
```

[↑ TOC](#toc)

---

## Commit 4 — cmd/main.go: factory wiring + remove startup gate {#commit-4}

[↑ TOC](#toc)

**Purpose.** Wire the factory slice into `NewEngine`; remove the `throughputAnalyzerEnabled`
startup gate and `RegisterAnalyzer` call.

### 4a. Remove `throughputAnalyzerEnabled`

Delete the function `throughputAnalyzerEnabled` (lines ~98–115 of `cmd/main.go`).

Behavioral-contract change grep — run and update all hits:
```bash
grep -rn "throughputAnalyzerEnabled\|RegisterAnalyzer\|RegisterThroughputAnalyzerQueries" \
    cmd/ internal/ --include="*.go"
```

`RegisterThroughputAnalyzerQueries` is called from `cmd/main.go` only — delete that
call. The query templates remain registered in `NewEngine` via the existing
`registration.RegisterSaturationQueries(metricsRegistry)` call; throughput queries
are currently registered there too (verify: grep for `throughput` in
`internal/collector/registration/`). If not, move the throughput query registration
into `NewEngine` alongside the saturation registration.

[↑ TOC](#toc)

### 4b. Build factory slice and pass to `NewEngine`

```go
// All known managed analyzers. Activation is config-driven per-cycle;
// registration here is unconditional.
managedAnalyzers := []saturation.ManagedAnalyzer{
    throughput.New(),
}

engine := saturation.NewEngine(client, apiReader, scheme, recorder, metricsRegistry, cfg, managedAnalyzers)
```

Remove the old `engine.RegisterAnalyzer(...)` call that followed `NewEngine`.

[↑ TOC](#toc)

### 4c. Update `throughput.New()`

If `throughput.New()` currently has a signature incompatible with `ManagedAnalyzer`,
update it to return `*ThroughputAnalyzer` (which now implements `ManagedAnalyzer`).
No other changes to `throughput.New()`.

[↑ TOC](#toc)

### Commit message

```
cmd: wire managed analyzer factory; remove throughputAnalyzerEnabled startup gate

All analyzers are registered unconditionally at startup; activation is now
config-driven per-cycle via syncManagedAnalyzers. Remove the startup gate that
read config before the ConfigMap reconciler had populated the store.
```

[↑ TOC](#toc)

---

## Commit 5 — Developer guide {#commit-5}

[↑ TOC](#toc)

**Purpose.** Document the new lifecycle protocol so future analyzer implementors
have a clear contract.

### Target file

`docs/developer-guide/saturation-engine.md` (or the existing multi-analyzer doc
— check which file covers the analyzer registration and engine architecture).
Run: `ls docs/developer-guide/` to find the right file.

[↑ TOC](#toc)

### Sections to add or update

**Section: "Implementing a managed analyzer"** — add as a new section:
- Implement `saturation.ManagedAnalyzer` (which embeds `interfaces.Analyzer`).
- `Activate`: initialize state; if the analyzer uses Prometheus sources, call
  `RegisterSources` here (see `internal/collector/registration` for examples).
  Keep it fast — it runs in the optimize goroutine.
- `Deactivate`: release state that should not persist across disable/re-enable.
- `Reactivate`: update cached config; avoid teardown. Called when the analyzer
  remains enabled but its `AnalyzerScoreConfig` entry changed.
- `Analyze`: called every cycle while active; must not assume prior state if
  the analyzer was recently activated.
- Register the implementation in `cmd/main.go`'s factory slice.
- Add a named entry to `cfg.Analyzers` in the saturation ConfigMap to activate it.

**Section: "Config-driven activation"** — update/add:
- The global default saturation config (`wva-saturation-scaling-config`, key `"default"`)
  drives which analyzers are active engine-wide.
- An analyzer absent from the default config (or with `enabled: false`) is deactivated.
- Per-model config overrides can change thresholds and scores but do not activate an
  analyzer that is absent from the global default.
- Source: design constraint documented here; revisit if per-model-only activation is
  needed later.

**Section: "satv2 special behavior"** — update:
- satv2 is always in the live set; `Deactivate` sets a `disabled` flag rather than
  removing it, because the engine always calls `satV2.Analyze()` to populate per-variant
  metadata (AcceleratorName, Cost, Role) that the rest of the pipeline requires.
- When disabled: `VariantCapacities` is still populated; `TotalDemand = TotalSupply = 0`
  so `RC = SC = 0` after threshold post-step — no scaling signal from saturation.

[↑ TOC](#toc)

### Commit message

```
docs: document ManagedAnalyzer lifecycle protocol

Add implementation guide for Activate/Deactivate/Reactivate, config-driven
activation rules, and satv2 special behavior.
```

[↑ TOC](#toc)

---

## Testing summary {#testing-summary}

[↑ TOC](#toc)

Tests are distributed across commits as noted above. This section lists required
coverage; do not consider any commit done until its listed tests pass.

**Commit 1 (interface + stubs):** No new tests. All existing tests must pass.

**Commit 2 (satv2 disabled flag):**
- `saturation_v2/analyzer_test.go`:
  - `"returns metadata-only result when disabled"` — Deactivate, then Analyze;
    assert TotalDemand=0, TotalSupply=0, TotalAnticipatedSupply=0;
    VariantCapacities populated.
  - `"resumes full analysis after re-Activate"` — Deactivate, Activate, Analyze
    with real metrics; assert TotalDemand > 0.

**Commit 3 (engine live-set refactor):**
- `engine_v2_population_test.go`:
  - Update `effectiveEnabled` absent-entry spec from `BeTrue()` to `BeFalse()`.
  - Add spec: `"syncManagedAnalyzers activates analyzer when it appears in config"`.
  - Add spec: `"syncManagedAnalyzers deactivates analyzer removed from config"`.
  - Add spec: `"syncManagedAnalyzers calls Reactivate when config entry changes"`.
  - Add spec: `"analyzer in config but not in factory is logged and skipped"`.
- Delete (or update) `engine_register_test.go` — `RegisterAnalyzer` is gone;
  replace with equivalent coverage of `syncManagedAnalyzers`.
- All existing engine tests must pass after removing the RegisterAnalyzer API.

**Commit 4 (cmd/main.go):**
- No new unit tests required (cmd-level wiring is covered by existing integration
  / e2e tests if any exist). Verify `make test` passes.

**All commits: pre-commit gates (run before each commit):**
- `gofmt -l ./internal/... ./cmd/...` — empty output
- `make test` — all pass
- `make lint` — clean
- `go build ./...` — clean

