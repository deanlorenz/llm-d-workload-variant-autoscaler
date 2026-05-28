# PR #1113 Review Summary

**Status: DRAFT**

**PR:** [engines/saturation: generic multi-analyzer pipeline with any-up/all-down combine](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1113)
**Head:** `a93bc5d`
**Reviewed:** 2026-05-20
**Re-validated:** 2026-05-29 against main `589646d7` (post fast-forward, 33 upstream commits since the original review base `cf649c84`). No item-level redesign needed; line numbers in `engine.go` shift slightly post-rebase. See per-item notes below.

---

## CI

- ✅ `e2e-tests-smoke` — pass (18m13s)
- ✅ `lint-and-test` — pass (2m28s)
- ✅ `DCO` — pass
- ✅ `check-code-changes` — pass
- ✅ `check-full-tests` — pass
- ✅ `gate` — pass
- ⏭ `build-image` — skipping
- ⏭ `e2e-openshift` — skipping
- ⏭ `e2e-tests-full` — skipping

---

## Review Status

CHANGES_REQUESTED by **ev-shindin** (2026-05-19). No other reviews yet.

---

## Comment Threads

### ev-shindin — CHANGES_REQUESTED

**1. `engine_v2.go:140` — RC normalization (open, unanswered)**
Reviewer says `RequiredCapacity` should be normalized w.r.t. the analyzer's own `TotalCapacity`,
not used raw. This relates directly to the dimensionless combine algorithm — RC from two analyzers
with different capacity scales aren't comparable without normalization.

**2. `engine_v2.go:206` — `AnalyzerScoreConfig` thresholds silently dropped for non-saturation analyzers (open, unanswered)**
`AnalyzerScoreConfig` exposes `ScaleUpThreshold`/`ScaleDownBoundary` for all analyzers,
`Validate()` checks both fields for all entries, and the doc says they "override global" — but
the engine only applies them to saturation. Per-entry thresholds for throughput, SLO, etc. are
silently ignored. Reviewer flags the API-behaviour mismatch.

**3. `engine.go:231` — `RegisterAnalyzer` concurrent map access (open, unanswered)**
The map is written by `RegisterAnalyzer` and read concurrently in `runAnalyzersAndScore`. The
doc comment states a "before StartOptimizeLoop" contract but nothing enforces it — a late call
would cause a data race that silently corrupts rather than panics.

---

## Pending Actions

- [ ] **Item 1 — delete combine; optimizers consume per-analyzer slice.** Bug: `totalWeighted`
      mixes raw RC values across analyzers with different unit scales. **Fix:** delete
      `combineAnalyzerResults`; pass `[]NamedAnalyzerResult` to optimizers; each computes
      gates / fair-share / allocation directly against per-analyzer state. Audit finds no
      combine output is shared (CostAware uses only RC/SC gates as one-line slice
      traversals; Greedy is sole `Score` consumer and recomputes its fair-share metric
      against current state at every allocation step anyway; v1 path bypasses combine).
      A minimal `totalWeighted` normalization fix is documented in the Discussion as an
      alternative if the deeper refactor's scope is unacceptable. See Discussion,
      Migration audit, Caveats, and Appendix A.
- [ ] **Item 2 — engine applies universal threshold formula to all analyzers.**
      Thresholds are universally meaningful as utilization fractions; the current
      engine routes them only to saturation — bug. Fix: engine post-processes RC/SC
      after each analyzer returns using the universal formula
      `RC = max(0, TotalDemand/scaleUp − TotalSupply)` and
      `SC = max(0, TotalSupply − TotalDemand/scaleDown)` with the model's global
      thresholds. Delete the saturation-only override block at
      `engine_v2.go:206–214`. Per-analyzer override resolution and the
      `ThresholdApplied` opt-out flag for non-universal analyzers are deferred to
      follow-up PRs — see Discussion and Appendix B.
- [ ] **Item 3 — `RegisterAnalyzer` race.** Snapshot `analyzers` to a frozen slice
      in `StartOptimizeLoop` before the goroutine launches; `started` bool causes
      late `RegisterAnalyzer` to panic. The snapshot step is the natural place to
      call any future per-analyzer `Init(ctx)`.

---

## Discussion

### Item 1 — fair-share metric, combine, and recalibration

**The bug.** Line 140 accumulates raw `RequiredCapacity * score` across analyzers.
Saturation outputs RC in tokens (~50 000); a future non-saturation analyzer (e.g.,
ThroughputAnalyzer) outputs in different units. The weighted sum is dimensionally
inconsistent — the larger-magnitude analyzer dominates regardless of its score weight.
`totalWeighted` flows directly into `combined.Score`, so the greedy optimizer's
fair-share ordering across models is broken once a non-saturation analyzer is enabled.

**The fix: delete engine-side combine; per-analyzer slice flows to optimizers.**
`combineAnalyzerResults` is removed. `runAnalyzersAndScore` becomes `runAnalyzers`,
returning `[]NamedAnalyzerResult` per model. `ModelScalingRequest` carries the slice
instead of a single combined `Result`. `AnalyzerResult.Score` (only ever populated by
combine) is removed.

The engine does not aggregate. It hands ownership of the
`[]NamedAnalyzerResult` slice to the optimizer via `ModelScalingRequest`; nothing
else reads the slice once `Optimize` is called. The slice already carries
everything the optimizer needs — per-analyzer RC, SC, TotalSupply, and per-variant
`PerReplicaCapacity` (inside each `Result.VariantCapacities`). The optimizer
mutates the slice in place during allocation — `RequiredCapacity`,
`SpareCapacity`, and `TotalSupply` decay arithmetically as variants are added —
and reads PRC directly from the variant entries. No second structure, no derived
index.

Note: `RC_i` and `SC_i` are the analyzer's **already-calibrated** outputs — the
threshold from Item 2 is baked in before the optimizer sees the value. The
engine post-processes RC/SC with the universal formula on each analyzer's raw
`TotalDemand` / `TotalSupply` using the model's global thresholds (Item 2). The
optimizer treats RC/SC as the calibrated demand gap and removable surplus.

Shared pure functions over `[]NamedAnalyzerResult`:

- `needsScaleUp(s)`, `needsScaleDown(s)` — gate predicates.
- `bottleneckReplicas(s, v)` = `max_i(ceil(RC_i / PRC[i][v]))` — replicas of
  variant `v` needed to close the worst-stressed analyzer's *calibrated* gap.
  PRC is read directly from `s[i].Result.VariantCapacities[v].PerReplicaCapacity`.
- `safeRemovalReplicas(s, v)` = `min_i(floor(SC_i / PRC[i][v]))` — most
  replicas of `v` we can remove while keeping every analyzer's `SC_i ≥ 0`
  (scale-down companion to `bottleneckReplicas`).
- `applyAllocation(s, v, n)` — mutate the slice for the addition of n
  replicas of `v` (`TotalSupply`, `RequiredCapacity`, `SpareCapacity`
  arithmetic per analyzer).
- `applyDeallocation(s, v, n)` — mutate the slice for the removal of n
  replicas of `v` (symmetric companion to `applyAllocation`; decreases
  `TotalSupply` and `SpareCapacity` by `n × PRC` per analyzer).

The inner allocation loop is itself shared: pick a variant, compute n, cap by
`maxReplicas` and other constraints, mutate the slice, repeat until the gate
predicate or viability fails. Each optimizer differs only in *which* variant the
picker selects:

- `CostAwareOptimizer` runs each model independently. Picker: cheapest viable
  variant first; spill to the next variant when capped. Pulls variant identity
  (Cost, AcceleratorName, Role) from one designated analyzer's slice entry
  (variant-identity caveat — see Caveats section).
- `GreedyByScoreOptimizer` adds an outer inter-model fair-share loop. It computes
  a fair-share metric `priority × Σ((RC_i / T_i) × analyzerScore_i)` from the
  working copy on demand (no stored Score field), orders models by that metric,
  and runs the shared inner loop on the most-starved model with a fair-share-bounded
  picker.

Engine collapses to "run analyzers, return slice." All allocation-time logic lives
in the pipeline package as free functions over the per-analyzer slice — no new
public interface, no helper object, no engine-side state. See Migration audit for
dependents to update and Appendix A for the sketch.

**Why this design.** Two arguments support deletion over fixing the combine:

*There is no combine to share.* The combine output is consumed only by optimizers; the
engine itself never reads combined RC / SC / Score for any of its own decisions. Among
optimizers:
- `CostAwareOptimizer` reads only `Result.RequiredCapacity` / `Result.SpareCapacity`,
  and only as scale-up / scale-down gates (plus an RC magnitude in a reason-string
  log line). It does **not** read `Result.Score`.
- `GreedyByScoreOptimizer` is the only `Score` consumer. Score is its private
  fair-share metric.
- v1 path (`engine.go:553`, `optimizeV1`) bypasses combine entirely.

The any-up / all-down gate semantics are universally meaningful but the implementation
is a one-line slice traversal — not worth a shared helper. The fair-share metric is
greedy-specific.

*Recalibration after partial allocation requires per-analyzer state.* Per-analyzer gaps
shift unequally — a variant might fully close one analyzer's gap while barely moving
another's; the bottleneck shifts. The fair-share metric must be recomputed against the
new state at each allocation step. Whether that state lives in an engine-side
aggregation or in greedy's `modelWork` makes no functional difference — the math is
the same. But the latter has fewer moving parts: no Combiner interface, no shared
helper, no engine-side aggregation that has to be queried and refreshed. The optimizer
holds per-analyzer state directly, recomputes its fair-share metric and gates on
demand, and updates state arithmetically using per-variant `PerReplicaCapacity`
already available from each analyzer's `VariantCapacities`.

**Scope.** This PR exists specifically to unblock TA (a non-saturation analyzer) — TA
is the next PR. The structural gap left by a `totalWeighted`-only fix would bite
immediately on that PR. Deleting the combine now removes that gap.

TA's analyzer package landed on main via PR #1052 (TA2, merged 2026-05-19); only
the engine-side wiring (TA3 PR-5: `RegisterAnalyzer` + `RegisterThroughputAnalyzerQueries`
calls in `main.go`) remains. The combine bug becomes a production concern as soon
as #1113 *and* TA3 PR-5 both land on main, which makes the per-analyzer-slice fix
the right scope for #1113 itself rather than a follow-up.

**Alternative considered: minimal `totalWeighted` fix.** Normalize `totalWeighted`
inside the `t > 0` branch with `(RC_i / T_i) * score_i`; keep
`Score = priority * totalWeighted * satTotal` for backward compat with the existing
optimizer math. Document that with multiple analyzers enabled, replica sizing is
approximated against saturation's capacity scale; per-analyzer-aware allocation
becomes a follow-up PR. Saturation-only behavior is unchanged; current tests pass.
Documented as a fallback if the deeper refactor's scope is unacceptable for the
reviewer.

---

### Item 2 — `AnalyzerScoreConfig` thresholds: keep, but apply to all analyzers

**Why threshold is a universal config knob.** The threshold captures a universal
scaling-policy concern: how conservative to be, how much slack to keep, how to avoid
oscillations. HPA and KEDA expose the same concept for raw metrics. Even when "demand"
exactly equals "supply" at some level S, you want to scale up *earlier* (before
utilization hits S) and scale down *later* (so the system doesn't immediately bounce
back). Two distinct values — one each for scale-up and scale-down — encode this
hysteresis directly. The threshold's *value* is universal in this sense, regardless of
analyzer.

**Application math is analyzer-specific.** The way an analyzer translates the threshold
value into its own RC/SC depends on the analyzer's underlying model. Saturation's
`RC = totalDemand/threshold − supply` is one realization. A future ITL-based or
queueing-model analyzer may translate "target utilization" through a non-linear fit
between replicas and latency. The analyzer encapsulates *how* to apply the threshold;
the engine just owns the *value*.

**The bug.** The same anti-pattern exists in two places. On main today
(`engine_v2.go:87–100`, predating #1113) a per-analyzer threshold-override
**resolution** loop walks `config.Analyzers` and only honors entries whose
`Name == interfaces.SaturationAnalyzerName` — saturation overrides take
effect, every other analyzer's overrides are silently dropped at resolution
time. PR #1113 then layers a multi-analyzer wrapper that applies the resolved
threshold (`engine_v2.go:206–214`) only to the saturation result, again
saturation-only. Net effect: `Validate()` checks both fields for all entries
and the doc table claims they "override global," but the engine never
honors them for any analyzer except saturation, neither at resolution nor
at application.

**The fix (this PR) — engine applies the universal formula to all analyzers
using global thresholds.** After each analyzer returns, the engine post-processes
RC/SC using the model's global threshold values from `SaturationScalingConfig`
and the universal formula on the analyzer's raw signals:
`RC = max(0, TotalDemand/scaleUp − TotalSupply)`,
`SC = max(0, TotalSupply − TotalDemand/scaleDown)`. Both inputs are already on
`AnalyzerResult`. Every analyzer's RC/SC is now calibrated by the engine using
the same logic that saturation_v2 currently applies in-analyzer, applied
universally. Both saturation-only blocks are deleted: the override-resolution
loop at `engine_v2.go:87–100` (precursor on main) and the override-application
wrapper at `engine_v2.go:206–214` (added by #1113). Saturation_v2's in-analyzer
formula becomes redundant under the engine post-step (same inputs, same output)
and can be simplified out in a follow-up.

**Implementation note.** Verify that `SaturationScalingConfig.ScaleUpThreshold` /
`ScaleDownBoundary` are intended as model-level globals (apply to all analyzers
analyzing this model), not saturation-specific items. The struct name is a
historical artifact from when saturation was the only analyzer; the threshold
semantics are universal. Confirm during implementation; rename or move the fields
if needed.

**Deferred to follow-up PRs.** The following are deferred from this PR's scope but
captured in Appendix B for context:

- *Per-analyzer threshold override resolution.* `AnalyzerScoreConfig.ScaleUpThreshold` /
  `ScaleDownBoundary` exist as optional per-analyzer overrides (similar in shape
  to the `Enabled` field). Saturation may want bigger margins than TA, etc.
  Engine logic to resolve and apply these overrides is deferred. This PR uses
  global thresholds for all analyzers; non-saturation overrides remain
  unhonored — same as today, but consistent across analyzers rather than
  only-saturation-honored.
- *`ThresholdApplied` opt-out flag for non-universal analyzers.* Future analyzers
  with non-universal math (ITL-based, queueing-model) will need to compute
  calibrated RC/SC themselves rather than rely on the universal formula. The
  flag mechanism + threading sketches are in Appendix B for when the first such
  analyzer arrives.

---

### Item 3 — `RegisterAnalyzer` concurrent map access (`engine.go:231`)

**The race.** `StartOptimizeLoop` calls `e.executor.Start(ctx)`, which launches the
goroutine that runs `optimize()` → `runAnalyzersAndScore()`. That function iterates
`e.analyzers`. If `RegisterAnalyzer` is ever called after `Start`, the unsynchronized
map write races with the concurrent read — silently corrupting the map rather than
panicking. In practice `main.go` is sequential (New → Register → Start), so there is
no real race today. But the Go race detector will flag it, and it is one wrong call
site away from production corruption.

**The fix: snapshot `analyzers` on `StartOptimizeLoop`.** `StartOptimizeLoop` copies
the registered analyzers to an immutable `[]analyzerEntry` slice before launching the
goroutine; the loop reads only from the frozen slice. A `started` bool on the Engine
causes any subsequent `RegisterAnalyzer` call to panic with
`"RegisterAnalyzer called after StartOptimizeLoop"`. The "before Start" contract is
enforced, not just documented. `RegisterAnalyzer` continues to exist for callers that
build the registry incrementally during setup — it just must complete before `Start`.

**Why this design.** Three properties:
- Keeps the registration API intact — `main.go` builds the analyzer set the same way.
- Goroutine reads from a frozen copy — no read-time locking needed in the hot path.
- Misuse panics loudly rather than silently corrupting state.

The snapshot step in `StartOptimizeLoop` is also the natural place to call any
per-analyzer `Init(ctx)` method in the future (treating registration as a one-time
initialization event), cleanly separating "setup" from "steady-state."

**Alternatives considered.**

*`sync.RWMutex` — defensive, minimal change.* Add `analyzersMu sync.RWMutex` to the
Engine struct; `RegisterAnalyzer` takes a write lock, `runAnalyzersAndScore` takes a
read lock while iterating. Standard idiom; allows dynamic registration at runtime —
which is neither intended nor needed. Adds read-time lock cost in the hot path.
Rejected.

*Constructor injection — cleanest design.* Add an `analyzers []NamedAnalyzer`
parameter to `NewEngine`; populate at construction time before any goroutine exists;
remove `RegisterAnalyzer` entirely. Zero race risk. Rejected because it forces a
`main.go` refactor for marginal benefit over the snapshot pattern, and removes the
registration step that's a natural extension point.

---

## Migration audit — dependents to update before deleting combine

Before deleting `combineAnalyzerResults` and the `Result *AnalyzerResult` field on
`ModelScalingRequest`, each of the following must be migrated (or confirmed
unaffected). Move tests; do not remove until parity coverage exists at the new layer.

- **`pipeline/` shared helpers (new file).** Free functions over the
  `[]NamedAnalyzerResult` slice the engine hands to the optimizer:
  - Gate predicates: `needsScaleUp(s)`, `needsScaleDown(s)`.
  - Scale-up: `bottleneckReplicas(s, v)`, `applyAllocation(s, v, n)`.
  - Scale-down: `safeRemovalReplicas(s, v)`, `applyDeallocation(s, v, n)`
    (symmetric companions).
  - Shared inner allocation loop parameterized by a `pickVariant` callback
    (used for both directions; the picker selects the variant and direction-
    appropriate cap on n).

  Private to the pipeline package. Mutation is in-place on the slice's
  `AnalyzerResult` fields (`RequiredCapacity`, `SpareCapacity`,
  `TotalSupply`); the engine hands ownership to the optimizer and no other
  reader exists. PRC is read directly from
  `Result.VariantCapacities[v].PerReplicaCapacity`. RC/SC come from the
  analyzer already calibrated by the engine universal post-step (Item 2).
- **`saturation/engine_v2.go` — engine universal post-step.** After each
  analyzer's `Analyze()` returns, post-process `Result.RequiredCapacity` and
  `Result.SpareCapacity` using the universal formula and the model's global
  threshold values from `SaturationScalingConfig`. Delete **both**
  saturation-only blocks: the override-resolution loop at lines 87–100
  (precursor on main today) and the override-application wrapper at lines
  206–214 (added by #1113). Verify `SaturationScalingConfig.ScaleUpThreshold` /
  `ScaleDownBoundary` are model-level globals (not saturation-specific) and
  rename / move the fields if needed.
- **`pipeline/greedy_score_optimizer.go`** — primary `Score` consumer today.
  Replace `req.Result.{Score,RequiredCapacity,SpareCapacity,RoleCapacities}` reads
  with the working-copy slice + shared helpers. Outer inter-model fair-share loop
  computes the fair-share metric on demand from the working copy
  (`priority × Σ((RC_i / T_i) × analyzerScore_i)`) — no stored Score field.
  Provides a fair-share-bounded `pickVariant` to the shared inner loop.
- **`pipeline/greedy_score_optimizer_test.go`** — gain optimizer-level tests
  covering scenarios currently in `engine_combine_test.go` (any-up, all-down,
  cold-start, weighted scoring, dimensionless cross-analyzer comparisons).
- **`pipeline/cost_aware_optimizer.go`** — replace `req.Result.{RequiredCapacity,
  SpareCapacity,VariantCapacities}` reads with the working-copy slice + shared
  helpers. Provides a "cheapest viable variant" `pickVariant` to the shared inner
  loop. RC/SC magnitudes in reason strings (lines 285, 288) — pull from saturation's
  entry by convention or drop from the message. (Note: `TryAllocate` now takes
  `ctx context.Context` as first param as of PR #1026 — mechanical pass-through,
  not part of the redesign itself.)
- **`pipeline/cost_aware_optimizer_test.go`** — add tests covering scale-up sizing
  and scale-down behavior over the per-analyzer slice; gate-rule coverage.
- **`engine_combine_test.go`** — delete only after parity coverage exists at
  the optimizer level. Move, don't remove.
- **`saturation/engine_v2.go`** — delete `combineAnalyzerResults`; rename
  `runAnalyzersAndScore` → `runAnalyzers`; adjust `collectV2ModelRequest` to
  package the slice into `ModelScalingRequest`.
- **`interfaces.AnalyzerResult.Score` field** — remove the field and its doc
  comment. Saturation analyzer doesn't set it; combine was the only writer. No
  other consumer.
- **`pipeline.ModelScalingRequest`** — replace `Result *AnalyzerResult` with
  `AnalyzerResults []NamedAnalyzerResult` (or chosen field name). Slice element
  type defined during implementation; sketch in Appendix A.
- **v1 path (`engine.go:553`, `optimizeV1`, `v1AnalyzerFactory`)** — confirmed
  bypass; no change.
- **`engine-queue-fix` branch** — extends `runAnalyzersAndScore` with
  SchedulerQueue threading. The rename + signature change in this PR lands on
  top of #1113; coordinate the rebase before submitting that PR.

---

## Implementation roadmap

Three PRs total — split by item, processed in reverse order (simplest first).
Each PR's commits are small enough that the reviewer can read them
independently and confirm each does exactly what its message says. Each
commit compiles cleanly and tests pass.

**Three Multi-Analyzer support PRs:**

- **Race-safe registration PR** — Item 3. Fresh PR, 1 commit. Closes
  ev-shindin's `engine.go:231` thread. Smallest scope; can merge quickly.
  Independent of the others.
  Suggested title: `engines: race-safe analyzer registration (snapshot on Start)`.
- **Universal threshold calibration PR** — Item 2. Fresh PR, 1 commit. Closes
  ev-shindin's `engine_v2.go:206` thread. Small. Independent of the others.
  Suggested title: `engines: universal threshold calibration for all analyzers`.
- **Optimizer redesign PR** — Item 1. Retitle and force-push #1113. 5 commits.
  Closes ev-shindin's `engine_v2.go:140` thread; supersedes the original
  combine implementation. Steps:
  1. Create the tracking issue (draft in Appendix C).
  2. Force-push the 5 Item 1 commits onto `engine-multi-analyzer`.
  3. Retitle #1113 and update its description to reference the tracking
     issue and this design doc.
  Suggested title: `engines/pipeline: per-analyzer signals through to optimizer`.

The race-safe registration and universal threshold PRs can land in parallel;
they don't gate the optimizer redesign PR and aren't gated by it. The
optimizer redesign's force-push should rebase over whatever has merged at
the time.

### Item 3 — `RegisterAnalyzer` race fix (race-safe registration PR: 1 commit, self-contained)

**Commit 3.1 — snapshot `analyzers` on `StartOptimizeLoop`; panic on late
`RegisterAnalyzer`.**

- Add `started bool` and `analyzersSnapshot []analyzerEntry` fields to
  `Engine`. `analyzerEntry` is a small unexported struct binding name and
  analyzer instance: `struct { name string; a interfaces.Analyzer }` (or
  similar — pick what fits the existing iteration pattern in
  `runAnalyzersAndScore`).
- In `StartOptimizeLoop`: build `e.analyzersSnapshot` from `e.analyzers`
  before launching the goroutine; set `started = true`. The optimize
  goroutine and `runAnalyzersAndScore` iterate `e.analyzersSnapshot`,
  never `e.analyzers`.
- `RegisterAnalyzer` checks `started` and panics with a clear message on
  a late call (e.g., `"RegisterAnalyzer called after StartOptimizeLoop"`).
- Tests: panic on late call; analyzers registered before `Start` work as
  before.

Independent of Items 1 and 2.

---

### Item 2 — engine universal threshold post-step (universal threshold calibration PR: 1 commit, self-contained)

**Commit 2.1 — engine applies the universal formula post-analyzer; delete
the saturation-only override block.**

- Verify `SaturationScalingConfig.ScaleUpThreshold` / `ScaleDownBoundary` are
  intended as model-level globals; rename the struct or move the fields if
  needed (mechanical; only one in-codebase consumer today).
- After each analyzer's `Analyze()` returns, recompute `RC` and `SC` from
  the analyzer's own `TotalDemand` / `TotalSupply` and the model's global
  thresholds:
  `RC = max(0, TotalDemand/scaleUp − TotalSupply)`,
  `SC = max(0, TotalSupply − TotalDemand/scaleDown)`.
- Saturation_v2's in-analyzer formula yields the same value under the same
  inputs; behavior preserved. The in-analyzer formula can be simplified out
  in a follow-up.
- Delete **both** saturation-only blocks: the override-resolution loop at
  `engine_v2.go:87–100` (precursor on main, predates #1113) and the
  override-application wrapper at `engine_v2.go:206–214` (added by #1113).
  Once the engine resolves and applies thresholds universally, both are
  dead code.
- Tests: post-step formula produces the expected RC/SC for representative
  inputs; saturation_v2's effective output unchanged; non-saturation analyzers
  now get calibrated RC/SC.

Per-analyzer override resolution and the `ThresholdApplied` opt-out flag are
deferred — see Future directions and Appendix B.

Independent of Items 1 and 3.

---

### Item 1 — delete combine; per-analyzer slice flows to optimizers (optimizer redesign PR: 5 commits, force-push to #1113)

The largest item. Broken into smaller commits so each can be confirmed in
isolation. Each commit compiles and tests pass. Tracking issue draft in
Appendix C.

**Scale-down handling.** Goal: remove as much cost as possible. Constraint:
after scale-down, every analyzer must stay below its scale-down threshold —
equivalently, `SC_i ≥ 0` for every analyzer (since `SC_i = T_i − TotalDemand_i / scaleDownBoundary`, and `SC_i = 0` means utilization is exactly at the
boundary, the limit we don't want to cross). The 0-boundary mirrors the
non-negative variant capacity itself.

Math: removing `n` replicas of variant `v` decreases each analyzer's `T_i`
and `SC_i` by `n × PRC[i][v]`. To keep `SC_i ≥ 0` for all analyzers,
`n ≤ min_i(floor(SC_i / PRC[i][v]))` — the analyzer for which `SC_i / PRC[i][v]`
is smallest sets the cap (it would hit its scale-down boundary first).

Structurally symmetric to scale-up: the same shared inner loop pattern
operates over the per-analyzer slice, with companion helpers — the picker
chooses which variant; `safeRemovalReplicas(s, v) = min_i(floor(SC_i / PRC[i][v]))`
is the per-variant cap; `applyDeallocation(s, v, n)` decreases
`TotalSupply` and `SpareCapacity` by `n × PRC` per analyzer. Per-analyzer
recalibration applies during partial scale-down: the bottleneck analyzer
(now: which has the smallest `SC_i / PRC` for the next variant being
considered) can shift after each variant's removal.

What differs from scale-up: scale-down processes **each model
independently**. Scale-up models compete for a shared scarce resource (the
cluster GPU budget) — the optimizer must order and bound contributions
across models. Scale-down has no such shared resource: removing a replica
from model A's variant `v` does not constrain model B's scale-down options,
and vice versa. The `SC_i ≥ 0` constraint is local to a model's own
per-analyzer slice; the cluster GPU budget only grows as replicas are
removed, never shrinks. There is no per-(variant) cross-model `MinReplicas`
floor to coordinate around either. So no inter-model fair-share, no
ordering across models, no cross-model prioritization — each model's
scale-down decision runs in isolation against its own slice.

Both optimizers take the same path; they differ only in the picker:

- `CostAwareOptimizer` — most-expensive viable variant first (drains cost
  fastest); spill to next when that variant's `safeRemovalReplicas` reaches 0.
- `GreedyByScoreOptimizer` — same most-expensive picker for now. A future
  enhancement could let Greedy choose scale-down variants to maximize future
  scale-up opportunity across competing models (free up scarce accelerators
  that other models could use) — the one place where a cross-model view
  would matter for scale-down. Noted in Future directions.

**Commit 1.1 — add `NamedAnalyzerResult` type and parallel `AnalyzerResults`
field on `ModelScalingRequest`.**

- Define `NamedAnalyzerResult { Name, Score, Result *AnalyzerResult }` in
  the `pipeline` package alongside `ModelScalingRequest` (the only consumer).
- Add `ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult` alongside
  the existing `Result *AnalyzerResult`.
- Engine populates both fields: `Result` via the existing
  `combineAnalyzerResults`; `AnalyzerResults` by transforming the
  `[]enabledAnalyzerResult` slice the engine already collects internally
  in `runAnalyzersAndScore` (mechanical: each `enabledAnalyzerResult` →
  `NamedAnalyzerResult { Name: aw.Name, Score: aw.Score, Result: ar.result }`).
- Optimizers continue to read `Result`. No behavior change. Plumbing only.

**Commit 1.2 — add shared helpers in `pipeline/`.**

- New file (e.g. `pipeline/analyzer_helpers.go`): scale-up
  (`needsScaleUp`, `bottleneckReplicas`, `applyAllocation`), scale-down
  (`needsScaleDown`, `safeRemovalReplicas`, `applyDeallocation`),
  `pickVariantFn`, `allocateForModel`. Sketches in Appendix A.
- Unit tests for each helper. Test parity target: the 31 Ginkgo specs in
  `engine_combine_test.go`. Migrate spec-by-spec at the right layer:
  - **Helper-level tests (this commit)** — gate predicates (any-up /
    all-down), replica sizing under multi-analyzer (`bottleneckReplicas` /
    `safeRemovalReplicas`), arithmetic mutation (`applyAllocation` /
    `applyDeallocation`), cold-start handling, cross-analyzer
    dimensionless comparisons.
  - **Optimizer-level tests (deferred to 1.4)** — specs that assert
    `Score` values move there, since the helpers don't produce a Score.
  Keep `engine_combine_test.go` intact through this commit; deleted in 1.5
  once parity is in place.
- Helpers are unused by optimizers at this commit. Just landing the
  building blocks.

**Commit 1.3 — migrate `CostAwareOptimizer` to per-analyzer slice + helpers.**

- Switch `CostAwareOptimizer` to read `req.AnalyzerResults`.
- Provide a cost-greedy `pickVariantFn`.
- Replace `costAwareScaleUp` / `costAwareScaleDown` body with calls to
  `allocateForModel`.
- Update `cost_aware_optimizer_test.go`: gate-rule and replica-sizing
  coverage over the per-analyzer slice. Pre-existing CostAware tests still
  pass (they exercised the same outputs).
- Greedy still uses the old `req.Result` path; both optimizers coexist on
  the new+old fields.

**Commit 1.4 — migrate `GreedyByScoreOptimizer` to per-analyzer slice +
helpers.**

- Switch `GreedyByScoreOptimizer` to read `req.AnalyzerResults`.
- Add `fairShareValue(priority, s)` helper (private to the optimizer).
- Provide a fair-share-bounded `pickVariantFn`.
- Replace `fairShareScaleUp` / `allocateToVariants` with the shared inner
  loop.
- Update `greedy_score_optimizer_test.go`: gain optimizer-level tests
  covering scenarios still in `engine_combine_test.go` (so that file can be
  removed in 1.5 without losing coverage). Specs that assert fair-share
  `Score` values land here (see Commit 1.2 note on test layer placement).
- **P/D disaggregation handling.** Greedy's existing `allocateByRole`
  distributes replicas between roles using `req.Result.RoleCapacities`. In
  the new design (no combined `Result`): when `req.Disaggregated == true`,
  the picker reads `RoleCapacities` from the analyzer that populates it.
  `RoleCapacities` is on every `AnalyzerResult` by interface, but **today
  only saturation_v2 fills it in** — TA and other analyzers leave it empty.
  So in this PR the optimizer finds `RoleCapacities` on the saturation
  entry of `s` as a matter of fact, not design choice. Once another
  analyzer begins populating its own `RoleCapacities`, a cross-analyzer
  aggregation strategy is needed (deferred — see Caveats).
- Both optimizers now use the new path; the old combined `Result` is no
  longer read.

**Commit 1.5 — delete combine; rename `runAnalyzersAndScore` →
`runAnalyzers`; remove the old fields and tests.**

- Delete `combineAnalyzerResults` and `engine_combine_test.go` (parity
  coverage now lives in 1.2 helper tests + 1.3 / 1.4 optimizer tests).
- Rename `runAnalyzersAndScore` → `runAnalyzers`; engine no longer aggregates.
- Drop `ModelScalingRequest.Result *AnalyzerResult`.
- Drop `AnalyzerResult.Score` (no consumers left after 1.3 / 1.4).
- Adjust `collectV2ModelRequest` to only populate `AnalyzerResults`.
- Coordinate with the `engine-queue-fix` branch — the rename + signature
  change here lands on top of #1113.

---

**Totals: 3 PRs / 7 commits** (race-safe registration: 1, universal threshold
calibration: 1, optimizer redesign: 5). The first two land independently;
the optimizer redesign is a force-push to #1113 once the tracking issue
is filed.

---

## Caveats (flagged, not fixed in this PR)

- **Variant identity from saturation's `VariantCapacities`.** Cost,
  AcceleratorName, and Role flow through saturation's analyzer result by
  convention; the optimizer reads them from a designated analyzer's slice
  entry. These are properties of the cluster and the variant, not of any
  analyzer; ideally they live in a separate cluster-state source. Pre-existing
  coupling, not introduced by this refactor. Note in the docs and leave for follow-up.
  *Sentinel handling:* as of PR #1026, `AcceleratorName` may carry the
  `"unknown"` sentinel rather than a real type when the cluster cannot resolve
  the variant's accelerator at decision time. The optimizer should pass it
  through verbatim; resolution happens later in
  `DefaultLimiter.resolveUnknownAccelerators` (homogeneous: pick the only
  type; heterogeneous: log + skip). No change to the redesign.
- **`RoleCapacities` aggregation across analyzers.** Currently per-analyzer
  (saturation produces it via `aggregateByRole`). Greedy's P/D logic in
  `allocateByRole` consumes it. With multiple analyzers enabled, the
  aggregation strategy across analyzers (max RC per role? saturation only?) is
  undefined. For this PR: optimizer reads `RoleCapacities` from saturation's
  entry by convention. Multi-analyzer P/D semantics are a follow-up.

---

## Future directions (out of scope for this PR)

- **Per-analyzer threshold override resolution.** The
  `AnalyzerScoreConfig.ScaleUpThreshold` / `ScaleDownBoundary` fields exist
  in the API but the engine doesn't yet resolve them per analyzer. Follow-up
  PR adds the override-resolution logic (per-entry override over global
  default) and applies it in the engine's universal post-step. See Appendix B
  for the design discussion.
- **`ThresholdApplied` opt-out flag for non-universal analyzers.** Future
  analyzers with non-universal math (ITL-based, queueing-model, SLO-based)
  will need to compute calibrated RC/SC themselves rather than rely on the
  engine's universal formula. Add an `AnalyzerResult.ThresholdApplied bool`
  field; engine skips the post-step when true. See Appendix B.
- **Threading thresholds via `AnalyzerInput`.** Once per-analyzer overrides
  are honored or analyzers opt out of the universal post-step, the resolved
  per-analyzer threshold value needs to be available to the analyzer for
  in-analyzer calibration or logging. See Appendix B.
- **Threshold abstraction.** The two values (scale-up threshold, scale-down
  boundary) tie cleanly to a demand/supply model but are hard for operators
  to set correctly without understanding the underlying math. Two longer-term
  improvements worth considering: (a) automatically derive threshold values
  from observed demand/supply variance and rate of change per analyzer;
  (b) expose a higher-level "target utilization" concept to operators and
  translate it internally into the per-analyzer threshold values appropriate
  for that analyzer's math. Captured here so the present "two numbers per
  analyzer" choice is understood as a starting point, not the final answer.
- **Smart Greedy scale-down (multi-model foresight).** This PR has both
  optimizers use the same most-expensive-first picker for scale-down.
  Greedy could be smarter: choose scale-down variants to maximize future
  scale-up opportunity across competing models — i.e., free up scarce
  accelerators that other models are likely to need. This is the one
  place where a cross-model view would matter for scale-down (otherwise
  models scale down independently — see Item 1 scale-down handling).
  Requires looking beyond the single model being scaled down and
  considering the cluster's pending demand profile.

---

## Appendix A — Optimizer-side sketch

Sketch — to be refined during implementation. Shape, not final API.

**`ModelScalingRequest` carries the per-analyzer slice (no engine-side combine):**

```go
type ModelScalingRequest struct {
    ModelID         string
    Namespace       string
    Priority        float64
    AnalyzerResults []NamedAnalyzerResult     // replaces Result *AnalyzerResult
    VariantStates   []VariantReplicaState
    Disaggregated   bool
}

type NamedAnalyzerResult struct {
    Name   string                              // analyzer name, e.g. "saturation"
    Score  float64                              // weight from AnalyzerScoreConfig
    Result *interfaces.AnalyzerResult           // per-analyzer RC, SC, T,
                                                // VariantCapacities (incl. PerReplicaCapacity),
                                                // RoleCapacities, etc.
}
```

**Shared helpers — pure functions over the slice the engine hands the optimizer:**

The engine hands ownership of `[]NamedAnalyzerResult` to the optimizer; helpers
mutate `Result.RequiredCapacity`, `Result.SpareCapacity`, `Result.TotalSupply`
in place. PRC is read directly from
`Result.VariantCapacities[v].PerReplicaCapacity`. RC/SC are calibrated
(post-threshold) by the time the optimizer sees them — either by the analyzer
itself or by the engine fallback (Item 2 / `ThresholdApplied` flag).

```go
// Gate predicates.
func needsScaleUp(s []NamedAnalyzerResult) bool       // any RC_i > 0
func needsScaleDown(s []NamedAnalyzerResult) bool     // every analyzer with data has SC_i > 0

// Scale-up sizing & mutation.
//
// bottleneckReplicas: replicas of variant v needed to close the worst-stressed
// analyzer's calibrated gap.   max_i ceil(RC_i / PRC[i][v]).
// PRC is read from s[i].Result.VariantCapacities[v].PerReplicaCapacity.
func bottleneckReplicas(s []NamedAnalyzerResult, v string) int

// applyAllocation: update s in place for the addition of n replicas of variant v.
// For each analyzer i, with p = PerReplicaCapacity for v:
//   Result.TotalSupply       += n × p
//   Result.RequiredCapacity   = max(0, RequiredCapacity − n × p)
//   Result.SpareCapacity     += n × p
func applyAllocation(s []NamedAnalyzerResult, v string, n int)

// Scale-down sizing & mutation (symmetric companions).
//
// safeRemovalReplicas: most replicas of variant v we can remove while
// keeping every analyzer's SC_i ≥ 0.   min_i floor(SC_i / PRC[i][v]).
func safeRemovalReplicas(s []NamedAnalyzerResult, v string) int

// applyDeallocation: update s in place for the removal of n replicas of v.
// For each analyzer i, with p = PerReplicaCapacity for v:
//   Result.TotalSupply       -= n × p
//   Result.SpareCapacity     -= n × p
//   Result.RequiredCapacity   = max(0, recompute via universal formula)
// (RC stays 0 by construction when n ≤ safeRemovalReplicas; the
// max(0, ...) is defensive against picker bugs.)
func applyDeallocation(s []NamedAnalyzerResult, v string, n int)
```

**Shared inner allocation loop — picker is the only optimizer-specific bit:**

```go
// pickVariant returns the next variant to allocate and a cap on n for that
// variant (e.g. fair-share target, or just maxReplicas headroom). Returns
// "" when no variant is viable (loop exits).
type pickVariantFn func(
    s []NamedAnalyzerResult,
    variantStates map[string]VariantReplicaState,
    taken map[string]int,
    available map[string]int,                 // GPU budget per accelerator
) (variant string, capN int)

// allocateForModel runs the inner loop, mutating s in place (calibrated RC/SC
// and TotalSupply decay arithmetically as variants are added). Decrements
// available. Returns targets (variant → replicas added).
func allocateForModel(
    s []NamedAnalyzerResult,
    variantStates map[string]VariantReplicaState,
    available map[string]int,
    pick pickVariantFn,
) map[string]int
```

**`CostAwareOptimizer` — runs each model independently with a cost-greedy picker:**

```go
func (o *CostAwareOptimizer) Optimize(requests []ModelScalingRequest, ...) []VariantDecision {
    for _, req := range requests {
        s := req.AnalyzerResults    // owned; mutated below
        switch {
        case needsScaleUp(s):
            targets := allocateForModel(s, stateMap, available, costAwareCheapestPicker)
            // build decisions from targets
        case needsScaleDown(s):
            // similar, with a remove-most-expensive picker
        }
    }
}
```

**`GreedyByScoreOptimizer` — outer inter-model fair-share, shared inner loop:**

```go
// fairShareValue computes priority × Σ_i (RC_i / T_i) × analyzerScore_i from
// the current state. Recomputed on demand from s; no stored Score field.
func fairShareValue(priority float64, s []NamedAnalyzerResult) float64

func (o *GreedyByScoreOptimizer) Optimize(requests []ModelScalingRequest, constraints) []VariantDecision {
    // Each request's AnalyzerResults is mutated in place during allocation.
    work := for each req: { req, targets }
    available := mergeConstraints(constraints)

    for any w in work has needsScaleUp(w.req.AnalyzerResults) && available.totalGPUs > 0:
        mean := mean of fairShareValue(w.req.Priority, w.req.AnalyzerResults) across active work
        sort active by fairShareValue desc
        w := most starved
        // Inner loop bounded by fair-share target
        added := allocateForModel(w.req.AnalyzerResults, stateMap, available,
                                  fairShareBoundedPicker(w, mean))
        w.targets += added
        // active set updated by needsScaleUp / fair-share threshold
}
```

The two pickers are the only meaningful divergence between optimizers. Everything
else — gate predicates, replica sizing under multi-analyzer, allocation-time
mutation — is shared as free functions on `[]NamedAnalyzerResult`.

---

## Appendix B — Item 2: deferred future work for threshold logic

This appendix captures threshold-related design that is **deferred** to
follow-up PRs. The immediate PR (#1113) scope is described in Item 2 above:
engine applies the universal formula with the model's global thresholds to
all analyzers. The work below builds on that foundation when a use case lands
that requires it.

**Per-analyzer threshold override resolution (deferred).** The
`AnalyzerScoreConfig.ScaleUpThreshold` / `ScaleDownBoundary` fields exist as
optional per-analyzer overrides, similar in shape to the `Enabled` field.
Saturation may want bigger margins than TA (or vice versa) because of
different noise characteristics, recovery dynamics, sensitivity to traffic
spikes — configuring the threshold per analyzer entry is reasonable
expressiveness; the global default keeps simple cases simple.

The engine should resolve the effective threshold per analyzer (per-entry
override over global default) and use that resolved value in its universal
post-step. Follow-up PR to add the resolution logic.

**Threading thresholds via `AnalyzerInput` (deferred until needed).** Once
per-analyzer overrides are honored, or once an analyzer opts out of the
universal post-step (see flag below), the resolved per-analyzer threshold
value needs to be available to the analyzer itself — for in-analyzer
calibration or for logging / non-calibration uses. Sketch:

```go
type AnalyzerInput struct {
    ModelID        string
    Namespace      string
    ReplicaMetrics []ReplicaMetrics
    VariantStates  []VariantReplicaState
    Config         AnalyzerConfig
    SchedulerQueue *SchedulerQueueMetrics

    // New: effective thresholds resolved by the engine — per-analyzer override
    // from AnalyzerScoreConfig applied over the global default.
    ScaleUpThreshold  float64
    ScaleDownBoundary float64
}
```

Engine resolves per-analyzer thresholds in `runAnalyzers` and writes them
into each analyzer's input. Saturation's `Analyze()` reads from
`input.ScaleUpThreshold` instead of `config.ScaleUpThreshold`. Minimal API
surface, no new interfaces, easy to back out if the design shifts.

**`ThresholdApplied` opt-out flag — analyzer optionality (deferred).**
Future analyzers with non-universal math (ITL-based, queueing-model,
SLO-based) need to compute calibrated RC/SC themselves rather than rely
on the engine's universal formula. Add an
`AnalyzerResult.ThresholdApplied bool` field (default false):

- If `false`, engine post-processes with the universal formula
  (the behavior in this PR).
- If `true`, engine takes RC/SC as the analyzer left them.

Saturation_v2 and TA both fit the universal formula and would leave this
flag false. The `true` path activates when a non-universal analyzer is
added. This decouples "value lives in config" (engine) from "math lives
where" (centralized in the engine for the universal case; per-analyzer
for special cases).

**Alternative considered: generalize `AnalyzerConfig`.** `AnalyzerInput.Config`
is currently `*SaturationScalingConfig` — saturation-specific. Threading
per-analyzer thresholds cleanly could also be done by generalizing
`AnalyzerConfig` to expose `EffectiveThresholds() (up, down float64)`. Larger
interface change, keeps thresholds co-located with config rather than
splitting them across two fields. Rejected in favor of the common-fields
approach above — additional abstraction isn't justified when threshold
threading is a one-time, mechanical change with one current in-analyzer
consumer.

**Alternatives considered (and rejected) for the threshold fields on
`AnalyzerScoreConfig`.**

*Remove the threshold fields entirely; keep saturation's thresholds at the
global `SaturationScalingConfig` level only.* Clean — no silent-drop, no
broken promises — but rejected: the threshold is universally meaningful (see
Item 2 "Why threshold is a universal config knob"), and other analyzers
will benefit from per-analyzer overrides once the resolution logic is added.
Removing the fields would force re-adding them later.

*Keep the fields but restrict them to saturation in the doc and `Validate()`.*
Honest API, no code restructuring, but rejected: a config field that
explicitly lies for some entries (saturation-only behavior on a struct
shared by all analyzers) is bad API shape when a clean implementation is
achievable with small interface changes.

---

## Appendix C — Tracking issue draft for the optimizer redesign PR

To be filed before force-pushing the optimizer redesign onto #1113.
Captures the problem and proposed solution at a level a project maintainer
or contributor can understand without reading the full design doc. The PR
description points back at the issue.

**Suggested title:** `engines/saturation: support multi-analyzer signals end-to-end in the optimizer pipeline`

**Suggested labels:** `area/engine`, `area/optimizer`, `kind/design`.

**Body:**

> ## Problem
>
> #1113 introduces the multi-analyzer pipeline, letting the engine collect
> outputs from multiple analyzers (saturation, ThroughputAnalyzer, …) per
> model. The current engine combines those outputs into a single
> `AnalyzerResult` (combined `RequiredCapacity`, `SpareCapacity`, `Score`)
> before handing it to the optimizer. Two problems with that:
>
> 1. **The combine is dimensionally broken for multi-analyzer.** Raw RC
>    values from analyzers with different unit scales (saturation in tokens,
>    a future throughput analyzer in tok/s, etc.) are summed in a weighted
>    fashion; the larger-magnitude analyzer dominates regardless of its
>    score weight.
> 2. **A single scalar `remaining` cannot model partial allocation under
>    multi-analyzer.** A given variant might fully close one analyzer's gap
>    while barely moving another's; the bottleneck shifts. The optimizer's
>    current `remaining -= n × PerReplicaCapacity` math treats RC as one
>    scalar in saturation units and has no way to recompute which analyzer
>    is now the bottleneck after each allocation step.
>
> Audit findings sharpen the picture:
>
> - The combined result is consumed only by optimizers; the engine itself
>   never reads combined RC / SC / Score for any of its own decisions.
> - `CostAwareOptimizer` reads only RC / SC, used as scale-up / scale-down
>   gates. It does not read `Score`.
> - `GreedyByScoreOptimizer` is the only `Score` consumer. `Score` is its
>   private fair-share metric, and must be recomputed against current
>   per-analyzer state at every allocation step regardless — so a stored
>   combined value adds no value over computing it on demand.
> - The v1 saturation path (`engine.go:553`, `optimizeV1`) bypasses combine
>   entirely; unaffected by this change.
>
> ## Proposed solution
>
> Delete the engine-side combine. Pass the per-analyzer slice through to
> the optimizers; let each optimizer apply its own decision logic over a
> working copy of the slice.
>
> - `ModelScalingRequest` carries `[]NamedAnalyzerResult` (one entry per
>   enabled analyzer) instead of a single combined `Result`.
> - `pipeline/` gets a small set of shared free functions over the slice:
>   `needsScaleUp`, `needsScaleDown`, `bottleneckReplicas(s, v)`,
>   `applyAllocation(s, v, n)`. Plus a shared inner allocation loop
>   parameterized by a `pickVariant` callback.
> - `CostAwareOptimizer` and `GreedyByScoreOptimizer` differ only in the
>   variant-picker (cost-greedy vs fair-share-bounded) and Greedy's outer
>   inter-model fair-share loop.
> - Helpers mutate the slice in place during allocation; the engine hands
>   ownership at `Optimize` and no other reader exists.
>
> The engine collapses to "run analyzers, return slice." All allocation-time
> logic lives in the pipeline package as free functions over the per-analyzer
> slice — no new public interface, no helper object.
>
> Per-analyzer per-variant `PerReplicaCapacity` is already on the existing
> analyzer API (`AnalyzerResult.VariantCapacities[].PerReplicaCapacity`),
> so the redesign uses what's already there.
>
> ## Out of scope (deferred to follow-up issues / PRs)
>
> - Per-analyzer threshold override resolution.
> - `ThresholdApplied` opt-out flag for analyzers with non-universal
>   calibration math (ITL-based, queueing-model).
> - Variant-identity decoupling — `Cost` / `AcceleratorName` / `Role`
>   currently flow through saturation's analyzer result by convention; ideally
>   they live in a separate cluster-state source.
> - Multi-analyzer `RoleCapacities` aggregation strategy for P/D
>   disaggregation.
>
> ## References
>
> - PR #1113 — combine pipeline; will be force-pushed with the redesign.
> - Sibling fixes from the same review: race-safe registration PR
>   (`RegisterAnalyzer` race) and universal threshold calibration PR (engine universal
>   threshold post-step) addressing the other two review threads from #1113.
