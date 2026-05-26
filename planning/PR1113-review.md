# PR #1113 Review Summary

**Status: DRAFT**

**PR:** [engines/saturation: generic multi-analyzer pipeline with any-up/all-down combine](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1113)
**Head:** `a93bc5d`
**Reviewed:** 2026-05-20

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

- [ ] **Item 1 — combine + optimizer fix.** Bug: `totalWeighted` mixes raw RC values
      across analyzers with different unit scales. Combine-level fix (agreed): normalize
      inside the `t > 0` branch with `(RC_i / T_i) * score_i`. Two paths for `Score`'s
      scale and how the optimizer consumes it; **Path B preferred** — engine owns
      recalibration, optimizer queries a Combiner after each allocation. Path A (minimal:
      keep `Score × satTotal`, defer recalibration to a follow-up) noted as fallback.
      See Discussion below and Appendix A.
- [ ] **Item 2 — per-analyzer threshold overrides (Option C).** Reversed from earlier
      Option A. Thresholds are universally meaningful as utilization fractions; per-analyzer
      overrides are legitimate. The current engine routes them only to saturation — bug.
      Thread the effective threshold (per-analyzer override or global default) into each
      analyzer's `AnalyzerInput`; remove the saturation-only block at `engine_v2.go:206–214`.
      Interface change required. See Discussion below and Appendix B.
- [ ] **Item 3 — `RegisterAnalyzer` race (Option C, unchanged).** Snapshot `analyzers`
      to a frozen slice in `StartOptimizeLoop` before the goroutine launches; `started`
      bool causes late `RegisterAnalyzer` to panic. The snapshot step is the natural
      place to call any future per-analyzer `Init(ctx)`.

---

## Discussion

### Item 1 — RC normalization, combine output, and recalibration

**The bug.** Line 140 accumulates raw `RequiredCapacity * score` across analyzers.
Saturation outputs RC in tokens (~50 000), TA in tok/s (~100). The weighted sum is
dimensionally inconsistent — the larger-magnitude analyzer dominates regardless of
its score weight. `totalWeighted` flows directly into `combined.Score`, so fair-share
ordering across models is broken once a non-saturation analyzer is enabled.

**The combine-level fix (agreed).** Move accumulation inside the `t > 0` branch and
normalize: `totalWeighted += (RC_i / T_i) * score_i`. Each term is now a dimensionless
utilization-excess fraction, comparable across analyzers regardless of unit scale.

**The harder question — what does `Score` mean and how does the optimizer consume it?**
The reviewer's comment is satisfied by the normalization above, but it leaves the output
scale ambiguous: what to multiply `totalWeighted` by? Two competing requirements pull in
opposite directions:
- Score should be analyzer-independent (no `× satTotal` baked in — that's saturation-specific).
- The existing optimizer's `n = ceil(target / vc.PerReplicaCapacity)` math assumes saturation
  token units for `target` (since `vc.PerReplicaCapacity` is saturation's).

**Recalibration is the real issue.** After partial allocation, per-analyzer gaps shift
unequally. A specific variant might fully close one analyzer's gap while barely moving
another's; the bottleneck shifts. The current optimizer's single-scalar `remaining`,
decremented by `n × PRC` after each allocation, cannot model this — it tracks one number
in saturation tokens and has no way to recompute which analyzer is now the bottleneck.

The clean architecture: optimizer allocates → engine recalibrates → optimizer queries the
new combined state. The engine has the per-analyzer per-variant `PerReplicaCapacity` it
needs already — every analyzer fills its own `AnalyzerResult.VariantCapacities[].PerReplicaCapacity`,
so the engine can build a `PRC[analyzer][variant]` matrix from the existing analyzer outputs.
Recalibration is then pure arithmetic on the combined state: `T_i' = T_i + n × PRC[i][v]`,
`RC_i' = max(0, RC_i − n × PRC[i][v])`, `SC_i' = SC_i + n × PRC[i][v]`. No analyzer
re-invocation needed.

**Path A — minimal fix, defer recalibration.** Normalize `totalWeighted` as agreed, keep
`Score = priority * totalWeighted * satTotal` for backward compatibility with the existing
optimizer math. Document that with multiple analyzers enabled, replica sizing is
approximated against saturation's capacity scale; per-analyzer-aware allocation requires
the recalibration architecture, deferred to a follow-up PR. Backward-compatible for
saturation-only — current tests pass unchanged.

**Path B — implement recalibration in this PR (preferred).** `combineAnalyzerResults`
returns a `Combiner` (or equivalent state object) holding per-analyzer state and the
per-variant PRC matrix. The Combiner exposes a fair-share `Score()`, scale-up / scale-down
gates, and an `AfterAllocation(variant, n)` method that returns an updated Combiner.
Score and gates are dimensionless. The optimizer's `fairShareScaleUp` and
`allocateToVariants` change to call Combiner methods instead of decrementing a scalar
`remaining`. See Appendix A for the interface sketch and the optimizer's revised flow.

**Recommendation: Path B.** This PR exists specifically to unblock TA (a non-saturation
analyzer) — TA is the next PR. Path A leaves a structural gap that bites the moment TA is
added to `config.Analyzers`. Per-analyzer per-variant `PerReplicaCapacity` is already part
of the analyzer API, so Path B has the data it needs. The optimizer simplifies (no PRC
division). Path A is documented as a fallback if Path B's scope is unacceptable for the
reviewer.

---

### Item 2 — `AnalyzerScoreConfig` thresholds: keep, but apply to all analyzers

**Earlier draft recommended Option A (remove the threshold fields). That is reversed.**

**Why thresholds belong on `AnalyzerScoreConfig`.** The threshold is universally meaningful
as a utilization fraction. Every analyzer reduces to a "demand vs supply" comparison in its
own units, and "scale up at 0.8 / scale down at 0.6" applies to all of them. Per-analyzer
overrides are legitimate: saturation may want bigger margins than TA (or vice versa)
because each analyzer has different noise characteristics and different recovery dynamics.

**The bug is in the engine, not the API.** The current code at `engine_v2.go:206–214` only
applies overrides to the saturation entry; non-saturation entries' overrides are silently
dropped. `Validate()` checks both fields for all entries and the doc table claims they
"override global" — so the API promises something the engine doesn't deliver.

**The fix (Option C).** The engine resolves the effective threshold per analyzer (per-entry
override or global default) and threads it into each analyzer's `AnalyzerInput` before
invocation. Each analyzer applies the threshold inside its own formula — saturation's
`RC = demand/threshold − supply`, TA's ITL-degradation comparison, etc. The threshold's
semantic meaning is "scale up at this utilization fraction," and each analyzer is responsible
for honouring that intent in whatever math it does. The saturation-only block at lines
206–214 disappears; saturation becomes just another analyzer entry.

**Interface implication.** `AnalyzerInput.Config` is currently `*SaturationScalingConfig` —
saturation-specific. Threading per-analyzer thresholds cleanly requires either generalizing
that field or extracting a common threshold field at the input level. See Appendix B for
two concrete sketches.

---

### Item 3 — `RegisterAnalyzer` concurrent map access (`engine.go:231`)

**The "before StartOptimizeLoop" comment:** `StartOptimizeLoop` calls
`e.executor.Start(ctx)`, which launches the goroutine that runs `optimize()` →
`runAnalyzersAndScore()`. That function iterates `e.analyzers`. If `RegisterAnalyzer`
is ever called after `Start`, the unsynchronized map write races with the concurrent
read — silently corrupting the map rather than panicking.

In practice `main.go` is sequential (New → Register → Start), so there is no real race
today. But the Go race detector will flag it, and it is one wrong call site away from
production corruption.

**Dean's observation — "initiate the operation while registering":**
If we treat registration as a one-time initialization event, we can call any per-analyzer
setup (register metric queries, allocate state, etc.) inside `RegisterAnalyzer` rather
than lazily on first `Analyze()` call. Doing this requires that registration happens in
the right context (e.g., after metrics sources are wired up) — which is already satisfied
by the `main.go` sequence.

**Options:**

**Option A — `sync.RWMutex` (defensive, minimal change).**
Add `analyzersMu sync.RWMutex` to the Engine struct. `RegisterAnalyzer` takes a write
lock; `runAnalyzersAndScore` takes a read lock while iterating. Allows dynamic
registration at runtime (which is not intended but now safe). Standard idiom.

**Option B — Constructor injection (cleanest design).**
Add an `analyzers []NamedAnalyzer` parameter to `NewEngine`. Map is populated at
construction time before any goroutine exists; `RegisterAnalyzer` is removed. Zero race
risk. Makes the API contract explicit: "you configure analyzers at construction time."
Downside: breaks current call site in `main.go` — minor refactor.

**Option C — Snapshot on Start (enforce the contract).**
`StartOptimizeLoop` copies `analyzers` to an immutable `[]analyzerEntry` slice before
launching the goroutine. `RegisterAnalyzer` checks an `started` bool and panics on
late calls: `"RegisterAnalyzer called after StartOptimizeLoop"`. The contract is
enforced rather than documented. `RegisterAnalyzer` continues to exist for callers who
want to build the map incrementally during setup.

**Recommendation:** Option C hits the right balance — keeps the registration API, makes
the goroutine loop read from a frozen copy (no lock needed at read time), and panics
loudly if someone registers late. Combined with Dean's observation: the frozen snapshot
step in `StartOptimizeLoop` is also the natural place to call any `Init(ctx)` method on
registered analyzers before the loop runs, cleanly separating "setup" from "steady-state".

If a full refactor is in scope, Option B (constructor) is the gold standard. For a
minimal fix that satisfies the reviewer, Option A (RWMutex) is fine.

---

## Appendix A — Combiner interface (Path B)

Sketch — to be refined during implementation. The shape, not the final API.

```go
// Combiner holds per-analyzer state for a single model and exposes the scalars the
// optimizer needs, plus a method to project state forward after a hypothetical
// allocation. Returned by combineAnalyzerResults; consumed by the optimizer.
type Combiner interface {
    // Score returns the dimensionless fair-share metric for this model:
    //   priority * Σ_i (RC_i / T_i) * analyzerScore_i
    Score() float64

    // NeedsScaleUp returns true when at least one analyzer's utilization excess
    // is positive (any-up rule).
    NeedsScaleUp() bool

    // NeedsScaleDown returns true when every enabled analyzer with valid data
    // has positive utilization slack (all-down rule).
    NeedsScaleDown() bool

    // VariantCapacities returns the saturation-derived per-variant data
    // (Cost, AcceleratorName, Role) the optimizer uses for variant selection.
    // Per-analyzer per-variant PerReplicaCapacity is held internally for
    // AfterAllocation arithmetic.
    VariantCapacities() []interfaces.VariantCapacity

    // AfterAllocation returns a new Combiner reflecting the addition of n
    // replicas of variant v. Pure arithmetic on cached state — no analyzer
    // re-invocation. For each analyzer i:
    //   T_i'  = T_i + n × PRC[i][v]
    //   RC_i' = max(0, RC_i − n × PRC[i][v])
    //   SC_i' = SC_i + n × PRC[i][v]
    AfterAllocation(variant string, n int) Combiner
}
```

**Optimizer flow with Combiner:**

```
for each model:
    c := req.Combiner
    if !c.NeedsScaleUp() { continue }
    while c.NeedsScaleUp() && availableGPUs > 0:
        v := pickCheapestViable(c.VariantCapacities(), availableGPUs)
        n := decideAllocation(c, v)         // smallest unit, or batch
        targets[v] += n
        availableGPUs -= n × gpusPerReplica(v)
        c = c.AfterAllocation(v, n)         // engine recomputes
```

Fair-share ordering across models uses `c.Score()` directly. After each model's inner
loop, the outer fair-share loop re-evaluates ordering using the updated scores. The
optimizer never sees per-analyzer state — it just queries scalars and asks the engine
to project.

**Construction.** `combineAnalyzerResults` builds the Combiner by iterating the per-analyzer
results and copying out per-variant `PerReplicaCapacity` into the internal matrix. Saturation's
`VariantCapacities` are also stashed for cost/accelerator-name lookup.

---

## Appendix B — Item 2: passing thresholds to analyzers

Two sketches for threading per-analyzer thresholds into `AnalyzerInput`.

**Option B.1 — extract a common threshold field on `AnalyzerInput` (smallest change).**

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

Engine resolves per-analyzer thresholds in `runAnalyzersAndScore` and writes them into
each analyzer's input. Saturation's `Analyze()` reads from `input.ScaleUpThreshold` instead
of `config.ScaleUpThreshold`. Other analyzers may apply or ignore them as appropriate. No
change to `AnalyzerConfig`.

**Option B.2 — generalize `AnalyzerConfig`.**

`AnalyzerInput.Config` becomes a generic config object exposing
`EffectiveThresholds() (up, down float64)`. Larger interface change, but keeps thresholds
co-located with config rather than splitting them across two fields.

**Recommendation:** Option B.1 — minimal API surface, no new interfaces, easy to back out
if the design shifts. Saturation_v2 is the only current consumer; the change is mechanical.
