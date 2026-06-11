# multi-analyzer-addendum — Task Plan

**Type:** 3 (task plan)
**Branch:** `multi-analyzer-addendum` (new worktree; base `main@2a0c3a7c`)
**Goal:** Land the addendum to the three-PR multi-analyzer stack (#1225/#1228/#1246): pipeline dev guide, test coverage gaps, and the disabled-analyzer veto bug fix. Target: merged before TA3 (#1250).

---

## Context

Three multi-analyzer PRs (#1225 registration, #1228 threshold, #1246 optimizer) are all on main at
`2a0c3a7c`. This PR-A addresses four items that did not fit inside any of those PRs:

- **MA-F7** — runtime bug: disabled analyzer still vetoes scale-down.
- **MA-H-1 + MA-OPT-4** — test gap: no spec asserts config-bridge population or non-uniform Score.
- **MA-OPT-1 + MA-OPT-2** — developer guide: the pipeline doc is a stub with a stale fork URL.
- **MA-1225-A** — stale panic docstrings: already fixed on main. Scope reduced to zero for this
  item; the grep confirms all four fixes from the original handoff are present on main as of
  `2a0c3a7c`. No work needed.

**Upstream race:** PR #1252 (biranofer) touches `cost_aware_optimizer.go`. If it merges before
PR-A is pushed, rebase onto updated main before pushing. PR #1223 (ev-shindin) adds
`docs/developer-guide/optimizers.md`; if it merges first, link to it from the pipeline doc
instead of duplicating optimizer-specific content.

---

## Pre-implementation: create the worktree

```bash
git -C /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/repo \
    worktree add ../multi-analyzer-addendum -b multi-analyzer-addendum main
```

Verify:
```bash
git -C /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/multi-analyzer-addendum \
    branch --show-current   # must be: multi-analyzer-addendum
```

Then `EnterWorktree path: .../multi-analyzer-addendum` before any edits.

---

## Item 1 — MA-F7: Skip disabled analyzers in `runAnalyzersAndScore`

### The bug

`AnalyzerScoreConfig.Enabled *bool` is parsed and defaulted at config load (`ApplyDefaults` in
`internal/config/saturation_scaling.go`, lines 161–169: when `nil`, sets `true`). At runtime,
`runAnalyzersAndScore` in `internal/engines/saturation/engine_v2.go` iterates
`e.analyzersSnapshot` (lines 137–154) and appends every non-saturation analyzer's result
unconditionally — no `Enabled` check. Downstream, `needsScaleDownForRole` requires all analyzers
in the slice to have `SpareCapacity > 0` before scale-down proceeds; a disabled analyzer with zero
spare vetoes it.

### Fix

In `runAnalyzersAndScore` (file `internal/engines/saturation/engine_v2.go`), inside the
`for _, entry := range e.analyzersSnapshot` loop (line 137), add an `Enabled` check before
calling `runRegisteredAnalyzer`:

```go
// Skip disabled analyzers entirely — do not run and do not append.
if !effectiveEnabled(entry.name, config) {
    continue
}
```

Add a package-private helper alongside `scoreForAnalyzer` and `resolveThresholds` in the same
file:

```go
// effectiveEnabled returns false only when the analyzer has an explicit
// Enabled:false entry in cfg.Analyzers. Absent entries and nil pointers
// default to true (consistent with ApplyDefaults).
func effectiveEnabled(analyzerName string, cfg config.SaturationScalingConfig) bool {
    for _, aw := range cfg.Analyzers {
        if aw.Name == analyzerName {
            if aw.Enabled != nil {
                return *aw.Enabled
            }
            return true
        }
    }
    return true
}
```

Design rationale: skip-the-run, not just skip-the-append. Running a disabled analyzer wastes one
full `Analyze` call per cycle per model. The `Enabled` field is a user-visible knob to "turn off"
an analyzer; running it silently discards the result and is confusing.

Saturation is not subject to this check. The existing `if entry.name ==
interfaces.SaturationAnalyzerName { continue }` guard on line 138 already excludes it from the
loop, and saturation is unconditionally run via `runV2AnalysisOnly` at line 101–105.

### Tests (add to `engine_v2_population_test.go`)

File: `internal/engines/saturation/engine_v2_population_test.go`
The file currently covers only `scoreForAnalyzer`. Extend the `Describe` with a new block:

```
Describe("effectiveEnabled", func() {

    It("returns true when the analyzer is absent from config", ...)
    It("returns true when Enabled is nil for the matching entry", ...)
    It("returns false when Enabled is explicitly false", ...)
    It("returns true when Enabled is explicitly true", ...)
})
```

And a higher-level integration spec in `engine_v2_test.go` (new `Describe` or inside
`"V2 Engine Integration"`):

```
It("MA-F7: disabled analyzer is not appended to AnalyzerResults and does not veto scale-down", func() {
    // Setup: register a spy analyzer that returns SpareCapacity=0 (would normally veto).
    // Config: Analyzers: [{Name:"spy", Enabled: false}].
    // Call runAnalyzersAndScore directly (as in engine_register_test.go pattern):
    //   construct an Engine with analyzersSnapshot=[saturation, spy], started=true.
    //   provide a saturation result with SpareCapacity>0.
    // Assert: returned []NamedAnalyzerResult has length 1 (saturation only).
    // Assert: spy.callCount == 0 (not called at all).
})
```

Note: `runAnalyzersAndScore` requires a live saturation analyzer call (it calls
`runV2AnalysisOnly`). To test just the enabled-gate logic without a full V2 analyzer, extract
`effectiveEnabled` into a unit spec (it is pure and stateless) and test the loop behavior
through the `runAnalyzersAndScore` integration path by constructing a minimal `Engine` with a
fake saturation analyzer (implement `interfaces.Analyzer` with a canned result) — same pattern
as `spyAnalyzer` in `engine_register_test.go`.

---

## Item 2 — MA-H-1 + MA-OPT-4: Config-bridge population tests + non-uniform Score

### MA-H-1: Config-bridge tests

File: `internal/engines/saturation/engine_v2_population_test.go`

The current file only covers `scoreForAnalyzer` (4 specs). Add a `Describe("runAnalyzersAndScore
config-bridge")` block that calls `runAnalyzersAndScore` on a minimal engine (fake saturation
analyzer, one or two registered spies) and asserts the per-entry population:

**Spec 1 — Score populated from config.Analyzers:**
```
It("populates Score from AnalyzerScoreConfig.Score into the returned slice", func() {
    // cfg.Analyzers = [{Name:"saturation", Score:2.0}, {Name:"spy", Score:0.5}]
    // result[0].Score == 2.0 (saturation entry)
    // result[1].Score == 0.5 (spy entry)
})
```

**Spec 2 — Score defaults to 1.0 when not configured:**
```
It("defaults Score to 1.0 when the analyzer has no Analyzers entry", func() {
    // cfg.Analyzers = [] (empty), spy registered but no config entry
    // result[0].Score == 1.0, result[1].Score == 1.0
})
```

**Spec 3 — Per-analyzer ScaleUpThreshold override applied:**
```
It("applies per-analyzer ScaleUpThreshold override into RC", func() {
    // spy result has TotalDemand=100, TotalSupply=100, TotalAnticipatedSupply=0.
    // global ScaleUpThreshold=0.85 → RC=max(0, 100/0.85-0)=117.6; RC>0.
    // per-analyzer override ScaleUpThreshold=1.10 → RC=max(0, 100/1.10-0)=90.9; RC>0.
    // The RC difference confirms the override is applied via resolveThresholds.
})
```

**Spec 4 — Disaggregated flag set by collectV2ModelRequest:**
`collectV2ModelRequest` (line 332–365 in `engine_v2.go`) sets `Disaggregated` based on whether
any `variantState.Role != "" && != "both"`. This is on the `collectV2ModelRequest` call, not
inside `runAnalyzersAndScore` itself. The test for this lives in `engine_v2_test.go`:
```
It("MA-H-1 Disaggregated: sets Disaggregated=true when any variant has non-both role", func() {
    // Construct variantStates with one "prefill" role.
    // Verify returned ModelScalingRequest.Disaggregated == true.
})
It("MA-H-1 Disaggregated: sets Disaggregated=false for all-both variants", func() {
    // Verify ModelScalingRequest.Disaggregated == false.
})
```

Implementation note: testing `runAnalyzersAndScore` directly requires a fake saturation analyzer
that implements `interfaces.Analyzer`. Define `fakeAnalyzer` in the test file (or reuse
`spyAnalyzer` imported from the same package since all these are `package saturation`):

```go
type fakeAnalyzer struct {
    result *interfaces.AnalyzerResult
}
func (f *fakeAnalyzer) Name() string { return "fake-saturation" }
func (f *fakeAnalyzer) Analyze(_ context.Context, _ interfaces.AnalyzerInput) (*interfaces.AnalyzerResult, error) {
    return f.result, nil
}
```

Since `runAnalyzersAndScore` calls `e.runV2AnalysisOnly` (not the registered saturation analyzer
directly), the fake must replace `e.saturationV2Analyzer`. `saturationV2Analyzer` is typed as
`*saturation_v2.SaturationAnalyzer` (concrete type, line 147 of `engine.go`), not an interface.
This means the clean path for testing `runAnalyzersAndScore` without a real saturation analyzer is
to call it via an integration approach (with a real `SaturationAnalyzer` that returns a canned
result) — or to expose the saturation analyzer as a field of interface type.

**Preferred approach for MA-H-1:** Test the config-bridge properties through `runAnalyzersAndScore`
using a real `saturation_v2.SaturationAnalyzer` with zero-value inputs (it returns a
zero `AnalyzerResult` without panicking), plus one registered `spyAnalyzer` with a canned
result from `Analyze`. The Score/threshold assertions are stable regardless of what saturation
computes — they depend only on the config + the spy's result.

If that proves brittle (saturation panics on empty input), add a thin interface wrapper:
```go
// internal/engines/saturation/engine.go — modify saturationV2Analyzer field
saturationV2Analyzer interfaces.Analyzer  // instead of *saturation_v2.SaturationAnalyzer
```
This is a one-line change that makes the field injectable. Check whether the saturation analyzer
tests still compile; the concrete type still satisfies the interface. If this touches too many
files, defer and just test `scoreForAnalyzer`/`resolveThresholds`/`effectiveEnabled` as unit specs
plus the Disaggregated specs via `collectV2ModelRequest`.

### MA-OPT-4: Non-uniform Score integration test

File: `internal/engines/pipeline/greedy_score_optimizer_test.go`

T1.3 (line 697–762) already covers uniform Score=1.0. Add one new `It` block inside the existing
`"Score-Based Priority"` context:

```
It("T1.4: non-uniform Score across two analyzers drives fair-share ordering", func() {
    // Two models, A and B. Both have Priority=1.0 and equal RequiredCapacity=20000.
    // Model A has two AnalyzerResults: saturation (Score=1.0, Remaining=20000)
    //   + throughput (Score=2.0, Remaining=20000).
    //   fairShareValue = Priority × Σ(Remaining × Score)
    //                  = 1.0 × (20000×1.0 + 20000×2.0) = 60000
    // Model B has one AnalyzerResult: saturation (Score=1.0, Remaining=20000).
    //   fairShareValue = 1.0 × (20000×1.0) = 20000
    // With 4 A100 GPUs (2 GPUs/replica), A should be served first.
    // Assert: A gets both available replicas; B gets none.
})
```

The actual formula in `fairShareValue` (`greedy_score_optimizer.go`, lines 55–87) is:

```
fsv = priority × Σᵢ Scoreᵢ × Σ_role pickerState[i][role]
```

where `pickerState` comes from `initRoleState(s)` and is seeded from `Remaining` per
`NamedAnalyzerResult` entry. The accumulation IS across all entries in `AnalyzerResults`, weighted
by each entry's `Score`. The T1.4 scenario below is valid.

File path: `internal/engines/pipeline/greedy_score_optimizer.go`

---

## Item 3 — MA-OPT-1 + MA-OPT-2: Developer guide expansion

### MA-OPT-2: Fix fork URL (do this first, it is one line)

File: `docs/developer-guide/multi-analyzer-pipeline.md`, line 46.

Current:
```
https://github.com/deanlorenz/llm-d-workload-variant-autoscaler/blob/plans/planning/multi-analyzer-design.md
```

Replace with a note that the design doc lives on the `plans` branch (orphan; not on upstream) and
cannot be linked directly. Options:
- Remove the URL entirely and replace with: "See the `plans` branch design doc
  `planning/multi-analyzer-design.md` for detailed architecture, alternatives, and future direction.
  It is not part of the code history and is not linked here."
- Or link the upstream repo's main branch README if a stable anchor exists there. Do not link the
  personal fork.

### MA-OPT-1: Expand the stub

Rewrite `docs/developer-guide/multi-analyzer-pipeline.md`. The doc must be self-sufficient for a
code reviewer reading only the PR diff. Do not remove the existing accurate paragraph
(the Components list and engine-post-step formula); expand around it.

**Required sections:**

**1. User configuration** — `SaturationScalingConfig.Analyzers[]` (YAML key `analyzers`).
Fields: `name` (string), `enabled` (bool, default true), `score` (float64, default 1.0),
`scaleUpThreshold` (float64, overrides global), `scaleDownBoundary` (float64, overrides global).
Source of truth: `internal/config/saturation_scaling.go` `AnalyzerScoreConfig` struct (lines
68–74). Include a minimal YAML example:

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

**2. Analyzer implementor guide** — `interfaces.Analyzer` interface
(`internal/interfaces/analyzer.go`): `Name() string` and
`Analyze(ctx, AnalyzerInput) (*AnalyzerResult, error)`. Key `AnalyzerInput` fields: `ModelID`,
`Namespace`, `ReplicaMetrics []ReplicaMetrics`, `VariantStates []VariantReplicaState`,
`Config AnalyzerConfig`, `SchedulerQueue *SchedulerQueueMetrics` (nil when flow control off).

Linearity invariant: `TotalSupply = Σ_v PerReplicaCapacity × ReplicaCount`. Analyzers must
populate `VariantCapacities[]`, `TotalSupply`, `TotalDemand`, `TotalAnticipatedSupply`. Use the
aggregation helpers in `internal/engines/aggregation/` (`SumTotalSupply`,
`SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`) rather than re-implementing.

For P/D disaggregated models, populate `RoleCapacities map[string]RoleCapacity` using
`AggregateByRole`. The engine applies `applyUniversalThreshold` to every role entry.

Do NOT populate `RequiredCapacity` or `SpareCapacity` in `AnalyzerResult` — the engine overwrites
them in `applyUniversalThreshold`. Analyzer-written values are discarded.

**3. Pipeline flow** (prose + ordered list):
1. `cmd/main.go` calls `engine.RegisterAnalyzer(name, a)` before `StartOptimizeLoop`.
   Saturation V2 is pre-registered at slot 0.
2. `StartOptimizeLoop` snapshots the registry into `analyzersSnapshot` (frozen, race-safe).
3. Per cycle: `runAnalyzersAndScore` calls `runV2AnalysisOnly` for saturation, then iterates
   `analyzersSnapshot` in registration order for non-saturation analyzers.
4. Disabled analyzers (`Enabled: false`) are skipped entirely.
5. `applyUniversalThreshold` is applied to each analyzer's result before it is appended:
   `RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)`,
   `SC = max(0, TotalSupply − TotalDemand/scaleDown)`.
   Per-analyzer threshold overrides (`ScaleUpThreshold`/`ScaleDownBoundary` in
   `AnalyzerScoreConfig`) take precedence over the global model-level thresholds.
6. Each result is wrapped in a `NamedAnalyzerResult{Name, Result, Score, Remaining, Spare}` and
   appended to the `[]NamedAnalyzerResult` slice.
7. Saturation is always first; its `VariantCapacities` entries carry `Cost`, `AcceleratorName`, and
   `Role` used downstream by the optimizer and enforcer.

**4. How results combine** (veto semantics):
- Scale-down gate (`needsScaleDownForRole`): ALL non-disabled analyzers in the slice must have
  `Spare > 0` for a role to scale down. One non-zero `RequiredCapacity` blocks scale-down.
- Scale-up gate (`anyRoleNeedsScaleUp`): ANY analyzer having `Remaining > 0` triggers scale-up
  for the corresponding role.
- The saturation entry in the slice also acts as the keeper of per-variant metadata
  (`Cost`, `AcceleratorName`, `Role`) that the optimizer reads from `VariantCapacities`. This is
  a known interim design; future work (`F3` in the design doc) will extract per-analyzer metadata
  collection out of the saturation result.

**5. Optimizer pointer** — note that the `[]NamedAnalyzerResult` slice is passed to
`CostAwareOptimizer` (unlimited mode) or `GreedyByScoreOptimizer` (limited mode with GPU inventory).
If `docs/developer-guide/optimizers.md` exists at write time (PR #1223 merged), add: "See
[optimizers.md](optimizers.md) for the optimizer algorithms." Otherwise include one paragraph
summarizing how the slice is consumed: the optimizer iterates the saturation entry's
`VariantCapacities` for cost/role data and uses `Remaining`/`Score`/`Spare` from each
`NamedAnalyzerResult` entry for the allocation loop.

**Formatting rules:** No forward-looking content. Do not reference plan-branch identifiers
(`F3`, `A8`, etc.) — these are invisible to code reviewers. Write descriptive prose instead.
The doc should not duplicate content already in `optimizers.md` if that doc exists.

---

## MA-1225-A: Stale panic docstrings

**No work required.** Verified on `main@2a0c3a7c`: all four stale panic docstring fixes from the
handoff (`c3ef6e66`) are already present. The exact grep command:

```bash
grep -n "calls panic\|post-Start RegisterAnalyzer panic" \
    internal/engines/saturation/engine.go \
    internal/engines/saturation/engine_register_test.go
```

produces no output. Confirmed: engine.go line 158 says "return an error", line 172 says "returns
an error", line 285 says "return an error"; test line 142 says "returns an error before mutating
anything". Item closed before PR-A opens.

---

## Commit structure

**Commit 1:** `engines/saturation: skip disabled analyzers in runAnalyzersAndScore`
- `internal/engines/saturation/engine_v2.go` — add `effectiveEnabled` helper; add enabled check
  in `runAnalyzersAndScore` loop.
- `internal/engines/saturation/engine_v2_population_test.go` — add `effectiveEnabled` unit specs.
- `internal/engines/saturation/engine_v2_test.go` — add MA-F7 integration spec.

**Commit 2:** `engines/saturation: add config-bridge population and non-uniform Score tests`
- `internal/engines/saturation/engine_v2_population_test.go` — MA-H-1 specs
  (Score, ScaleUpThreshold override).
- `internal/engines/saturation/engine_v2_test.go` — MA-H-1 Disaggregated specs.
- `internal/engines/pipeline/greedy_score_optimizer_test.go` — MA-OPT-4 T1.4 non-uniform Score
  spec.

**Commit 3:** `docs: expand multi-analyzer pipeline developer guide; fix fork URL`
- `docs/developer-guide/multi-analyzer-pipeline.md` — full rewrite (MA-OPT-1 + MA-OPT-2).

Sign-off each commit: `--signoff` (Signed-off-by: Dean H Lorenz <dean@il.ibm.com>).

---

## Pre-push checklist (per CONVENTIONS.md)

Run in order from the `multi-analyzer-addendum` worktree:

1. `git branch --show-current` → must be `multi-analyzer-addendum`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` → empty output.
3. `make test` → all pass.
4. `make lint` → clean.
5. DCO: `git log upstream/main..HEAD --format="%b" | grep Signed-off-by` → one per commit.
6. `go build ./...` → clean.

---

## Open questions

1. **MA-H-1 injection path:** `saturationV2Analyzer` is typed as
   `*saturation_v2.SaturationAnalyzer` (concrete). If writing config-bridge specs that call
   `runAnalyzersAndScore` directly is blocked by inability to inject a fake, decide between:
   (a) changing the field type to `interfaces.Analyzer` (one-line change to `engine.go`, low risk),
   (b) testing only `scoreForAnalyzer` / `resolveThresholds` / `effectiveEnabled` as pure unit
       specs + Disaggregated via `collectV2ModelRequest`, and defer the
       full `runAnalyzersAndScore` integration test to a later PR.
   Read `greedy_score_optimizer.go` to confirm MA-OPT-4 accumulation assumption before writing the
   T1.4 spec.

2. **PR #1223 status at write time:** check `gh pr view 1223 --json state` before writing the
   optimizer pointer section. If merged, link `optimizers.md`. If not, write a self-contained
   paragraph.

3. **PR #1252 status at write time:** check `gh pr view 1252 --json state` before pushing. If
   merged, rebase `multi-analyzer-addendum` onto updated main before pushing.

---

## Progress tracking

| Item | Status |
|---|---|
| Worktree created | [ ] |
| MA-F7 fix + unit tests (engine_v2_population_test.go) | [ ] |
| MA-F7 integration test (engine_v2_test.go) | [ ] |
| MA-H-1 config-bridge specs | [ ] |
| MA-OPT-4 non-uniform Score spec (greedy_score_optimizer_test.go) | [ ] |
| MA-OPT-2 fork URL fix | [ ] |
| MA-OPT-1 dev guide expansion | [ ] |
| All gates green (gofmt, make test, make lint, go build) | [ ] |
| DCO verified on all commits | [ ] |
| Review trigger written | [ ] |
| Push-ready handoff to planner | [ ] |
