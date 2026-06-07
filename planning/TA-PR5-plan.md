# TA PR-5: Wire ThroughputAnalyzer into the Multi-Analyzer Engine

> **Status: PLANNED (rework)** — Branch `TA3`, worktree `TA3/`, current tip `7506634b`.
> Replaces the prior PR-5 plan (which targeted the original combine-based
> engine-multi-analyzer PR #1113, since superseded by a 3-PR split).
> Part of #1005; does not close it.

---

## 0. Summary

TA3 was implemented (PR-4 logic at commit `85c8a0ff` + the PR-5 wiring commit
`b6e897c8`) against the original `engine-multi-analyzer` design that bundled
(a) analyzer registration, (b) a dimensionless any-up/all-down combine, and
(c) per-analyzer threshold handling into one PR (#1113). That design was
replaced — see `planning/PR1113-review.md` and the 2026-06-02 settled
architecture — and split into three independent PRs:

1. **#1225 `multi-analyzer-registration`** — race-safe registration plumbing
   (snapshot on `StartOptimizeLoop`, panic on late `RegisterAnalyzer`,
   duplicate-name detection, `RegisterAnalyzer` returns error). Open,
   ev-shindin assigned.
2. **#1228 `multi-analyzer-threshold`** — universal threshold post-step in the
   engine; analyzers publish raw `Total*` and the engine computes RC/SC. New
   `internal/engines/aggregation/` package with shared helpers. Per-analyzer
   threshold overrides (`AnalyzerScoreConfig.ScaleUpThreshold`/`ScaleDownBoundary`)
   resolved by the engine. Stacked on #1225. Open, ev-shindin assigned.
3. **`multi-analyzer-optimizer`** (no PR yet) — deletes the engine-side combine;
   the optimizer consumes `[]NamedAnalyzerResult` directly. Per-variant slice
   helpers (`needsScaleUp`, `needsScaleDown`, `bottleneckReplicas`,
   `safeRemovalReplicas`, `applyAllocation`, `allocateForModel`,
   `saturationEntry`) preserve the old any-up/all-down semantics as slice
   predicates. In-flight on a sibling worktree.

TA3 must rebase onto this new stack and adapt its `Analyze()` output to the new
contract (raw `Total*` published; engine writes RC/SC). The wiring itself
shrinks to a 2-line change in `cmd/main.go` plus error handling on
`RegisterAnalyzer`. The substantive work is in `analyzer.go` and its tests.

This plan is the only doc the coder needs to land PR-5; the broader TA roadmap
(`TA-Plan.md`, `TA-overview.md`) is deferred for a separate rewrite once the
multi-analyzer stack lands.

---

## 1. Dependencies and rebase target

| PR / branch | What it provides |
|---|---|
| #1225 `multi-analyzer-registration` | `analyzerEntry`, `analyzers []analyzerEntry`, `analyzersSnapshot`, `started bool`, `RegisterAnalyzer(name, analyzer) error`, snapshot-on-`StartOptimizeLoop`. |
| #1228 `multi-analyzer-threshold` (stacked on #1225) | `aggregation` package (`SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`, `ScopeTotals`); engine `applyUniversalThreshold` + `resolveThresholds`; `AnalyzerResult.TotalAnticipatedSupply` and `RoleCapacity.TotalAnticipatedSupply` fields; `runRegisteredAnalyzers` calling the post-step per analyzer. |
| `multi-analyzer-optimizer` (no PR) | `pipeline.NamedAnalyzerResult{Name, Result, Score, Remaining, Spare, RoleSpare map[string]float64}`; `ModelScalingRequest.AnalyzerResults []NamedAnalyzerResult`; per-variant slice helpers; CostAware + Greedy migrated to the slice. Saturation entry must be present (optimizer skips models without one — see §2.5). |
| `multi-analyzer-optimizer` (no PR, queue wiring included) | Absorbs `engine-queue-fix` (commit `01ed7d8d`) in its cross-rebase fixup commit `3fe287fe`. `CollectSchedulerQueueMetrics` is wired through `prepareModelData` → `modelData.schedulerQueue` → `runV2AnalysisOnly` / `runAnalyzers` → `AnalyzerInput.SchedulerQueue` for every registered analyzer. TA-PR5 makes no queue-related changes; TA's existing nil-tolerance covers the window before the optimizer PR merges. |

**Rebase order** (assuming the three PRs merge in dependency order):

1. Rebase TA3 onto `upstream/main` (already unblocked).
2. Rebase onto whichever multi-analyzer PR lands first (typically #1225).
3. Continue rebasing as #1228 and the optimizer branch land.

Until those PRs merge, the coder can rebase TA3 onto the local tips of the three
sibling worktrees by cherry-picking — but **the canonical rebase target is
upstream main after all three merge**, and the final commit history must reflect
that.

**Drop during rebase:** the `internal/engines/saturation/engine.go` portions of
`b6e897c8` (the registration plumbing in TA3's PR-5 wiring commit). Those are
obsolete — the same plumbing landed via #1225 with a different shape (slice +
snapshot, error-returning). The wiring commit shrinks to `cmd/main.go` only.

---

## 2. Contract TA must satisfy after rebase

Verbatim from `internal/interfaces/analyzer.go`, `internal/engines/aggregation/`,
and `internal/engines/saturation/engine_v2.go` on the threshold branch (#1228
head). No invention here — this is the agreed contract every analyzer must
satisfy.

### 2.1 Per-variant — TA writes, optimizer reads

```go
type VariantCapacity struct {
    VariantName        string
    AcceleratorName    string
    Cost               float64
    Role               string  // "prefill" | "decode" | "both" | ""
    ReplicaCount       int
    PendingReplicas    int
    PerReplicaCapacity float64
    TotalCapacity      float64  // == ReplicaCount × PerReplicaCapacity
    TotalDemand        float64
    Utilization        float64  // == TotalDemand / TotalCapacity
}
```

**Linearity invariant (mandatory):** `TotalCapacity == ReplicaCount ×
PerReplicaCapacity`. The optimizer's per-variant scaling math
(`bottleneckReplicas`, `safeRemovalReplicas`, `applyAllocation`) silently breaks
otherwise.

### 2.2 Model-level — TA writes raw totals; engine writes RC/SC

```go
type AnalyzerResult struct {
    AnalyzerName            string
    ModelID, Namespace      string
    AnalyzedAt              time.Time
    VariantCapacities       []VariantCapacity

    TotalSupply             float64  // analyzer-published
    TotalDemand             float64  // analyzer-published
    Utilization             float64  // analyzer-published, TotalDemand/TotalSupply
    TotalAnticipatedSupply  float64  // analyzer-published, used by engine for RC

    RequiredCapacity        float64  // engine-written; TA leaves zero
    SpareCapacity           float64  // engine-written; TA leaves zero
    Score                   float64  // legacy; not used by post-#1228 path

    RoleCapacities          map[string]RoleCapacity  // nil for non-disaggregated
}
```

TA must populate the **published** fields and leave RC/SC zero. The engine's
post-step overwrites RC/SC after `Analyze()` returns.

**Linearity invariant for supply (mandatory):**
```
TotalSupply            == aggregation.SumTotalSupply(VariantCapacities)
TotalAnticipatedSupply == aggregation.SumTotalAnticipatedSupply(VariantCapacities)
```

**Demand exemption (precedent set by sat_v2):** `TotalDemand` may exceed
`Σ VariantCapacities[].TotalDemand` by an analyzer-determined contribution from
`SchedulerQueue` (queue items are not variant-attributed in the input). The
analyzer is responsible for choosing how queue demand is split across roles for
`RoleCapacities[role].TotalDemand`. See §2.7 for TA's queue handling.

### 2.3 Per-role — TA writes raw totals; engine writes RC/SC

```go
type RoleCapacity struct {
    Role                   string
    TotalSupply            float64
    TotalDemand            float64
    TotalAnticipatedSupply float64
    RequiredCapacity       float64  // engine-written; TA leaves zero
    SpareCapacity          float64  // engine-written; TA leaves zero
}
```

`RoleCapacities` is `nil` for non-disaggregated models (all variants role
`"both"` or `""`); the engine still applies the post-step at model level.
For disaggregated models, the same shape and rules as model level apply per
role.

### 2.4 Engine post-step (informational — engine does this, not TA)

```go
RC = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)
SC = max(0, TotalSupply         − TotalDemand/scaleDown)
```

Applied at model scope and at every `RoleCapacities[role]` scope, with the same
`(scaleUp, scaleDown)` resolved per analyzer (see §2.6).

**Strict no-fallback:** `TotalAnticipatedSupply == 0` is a literal value, not a
sentinel. A scaled-to-zero variant with positive demand correctly yields
`RC = TotalDemand/scaleUp`.

**Behavior change for TA:** today TA's RC formula is effectively
`max(0, TotalDemand − TotalAnticipated)` (threshold = 1.0). Under the contract,
the engine applies the model's configured `scaleUpThreshold` (typically 0.85),
matching sat_v2's semantics. This is the *intended* behavior of the new design.

### 2.5 Saturation always runs

Verified on both branches; not TA's concern but load-bearing for TA's design:

- **Threshold branch** (`internal/engines/saturation/engine_v2.go:215-217`):
  saturation is invoked unconditionally before any registered analyzer.
- **Optimizer branch** (`internal/engines/pipeline/cost_aware_optimizer.go:48-49`,
  `greedy_score_optimizer.go:83-84`): both optimizers call
  `saturationEntry(req.AnalyzerResults)` and **skip the entire model** if it
  returns nil. A slice without a saturation entry yields no scaling decision.

Saturation's `enabled: false` flag does NOT remove its entry from the slice;
it only governs its `Remaining`/`Spare` counters (the optimizer's signal
inputs). Saturation's `VariantCapacities` (carrying `Cost`, `AcceleratorName`,
`Role`, `ReplicaCount`, `PendingReplicas`) are read by the optimizer regardless
of `enabled`.

Implication for TA: TA's `VariantCapacities` need not duplicate variant
metadata that saturation already provides — TA only needs `VariantName`, `Role`,
`ReplicaCount`, `PendingReplicas`, `PerReplicaCapacity`, `TotalCapacity`,
`TotalDemand`, `Utilization`. `AcceleratorName` and `Cost` may be left empty;
the optimizer reads them from saturation's entry. (TA today does set them when
known; harmless either way.)

### 2.6 Per-analyzer threshold overrides — already in place

The threshold branch's `resolveThresholds` (`engine_v2.go:154-163`) reads
`config.SaturationScalingConfig.Analyzers[]` (`AnalyzerScoreConfig`) and
returns the effective `(scaleUp, scaleDown)` for each analyzer:

```go
func resolveThresholds(analyzerName string, cfg config.SaturationScalingConfig) (scaleUp, scaleDown float64) {
    for _, aw := range cfg.Analyzers {
        if aw.Name == analyzerName {
            return aw.EffectiveScaleUpThreshold(cfg.ScaleUpThreshold),
                   aw.EffectiveScaleDownBoundary(cfg.ScaleDownBoundary)
        }
    }
    return cfg.ScaleUpThreshold, cfg.ScaleDownBoundary
}
```

`AnalyzerScoreConfig.{Enabled *bool, Score, ScaleUpThreshold *float64, ScaleDownBoundary *float64}`
fields exist on main today. Operators override TA's thresholds by adding an
`analyzers` list entry in the model's `SaturationScalingConfig`:

```yaml
scaleUpThreshold: 0.85         # global default
scaleDownBoundary: 0.70
analyzers:
  - name: saturation
    enabled: true
    score: 1.0
  - name: throughput
    enabled: true
    score: 1.0
    scaleUpThreshold: 0.85    # optional TA-specific override (nil = inherit)
    scaleDownBoundary: 0.70
```

**No TA work required for threshold overrides.** TA inherits the mechanism
once #1228 lands.

### 2.7 SchedulerQueue handling

`AnalyzerInput.SchedulerQueue *interfaces.SchedulerQueueMetrics` is shared
input for every analyzer (`internal/interfaces/analyzer.go`). Demand
extraction from it is per-analyzer (each analyzer chooses its unit and role
attribution).

TA today already handles `SchedulerQueue` correctly:
- `estimateQueueDemand(input.SchedulerQueue, itlSat, drainFactor)` returns 0
  when the input is nil — no nil-pointer risk.
- When the input is populated (after `engine-queue-fix` or its successor
  lands), TA derives `queueDemand = QueueSize / (DefaultQueueDrainFactor ×
  avgDecodeITLSat)` and adds it to model-level `totalDemand`.

**Engine wiring (resolved — absorbed into `multi-analyzer-optimizer`):**
`engine-queue-fix` (commit `01ed7d8d`) was absorbed in the optimizer branch's
cross-rebase fixup commit `3fe287fe`. `CollectSchedulerQueueMetrics` is wired
through `prepareModelData → modelData.schedulerQueue → AnalyzerInput.SchedulerQueue`
for every registered analyzer on that branch. The open-question trigger
(`session/handoffs/optimizer__ta-queue-wiring.md`) is answered.

This plan assumes:
- TA-PR5 makes **no** changes to the engine queue wiring.
- TA's existing nil-tolerance is sufficient: TA-PR5 ships safely on any
  merge ordering. When the optimizer branch lands, TA's per-cycle `Analyze()`
  receives real queue data without code change.
- TA's queue-demand contribution must be lifted into per-role attribution to
  preserve the per-role linearity invariant — see §3.3 (d).

### 2.8 TA-only and TA+sat_v2 dual-mode operation

Both modes work under the new design. The any-up/all-down combine semantics
from the old `combineAnalyzerResults` survive as slice predicates on the
optimizer branch (`internal/engines/pipeline/analyzer_helpers.go`):

```go
needsScaleUp(s)   = ∃ e ∈ s : e.Remaining > 0   // OR over Remaining
needsScaleDown(s) = ∀ e ∈ s : e.Spare > 0       // AND over Spare
```

`Remaining` is initialised from `Result.RequiredCapacity` (which the engine
post-step wrote); `Spare` from `Result.SpareCapacity`. Decremented in place by
the optimizer's allocation helpers.

**TA+sat_v2 (default):** both analyzers' results in the slice; optimizer
considers any-up across both, all-down requires both. Equivalent to the old
combine's `util_excess = max_i(...)` / `util_slack = min_i(...)` semantics —
same intent, slice-predicate mechanism.

**TA-only mode** (saturation `enabled: false`, but always present as slice
entry per §2.5): saturation's `Remaining`/`Spare` are zero (engine post-step
sees its `RC`/`SC` as zero from the analyzer's no-op output) → only TA
contributes signals. `needsScaleUp(s)` = TA's `Remaining > 0`;
`needsScaleDown(s)` requires TA's `Spare > 0` AND saturation's `Spare > 0` —
but saturation's `Spare = 0` would block all-down. **This means TA-only
scale-down is blocked.** Acceptable for the smoke test on TA3 (which only
exercises wiring health and TA-only scale-up, per
`test/e2e/throughput_analyzer_test.go`); revisit if a TA-only scale-down
e2e is added.

  Open follow-up issue (out of scope here): saturation `enabled:false` should
  arguably make its slice entry exempt from `needsScaleDown` rather than
  blocking. Tracked in §6.

Operator config (TA-only mode):
```yaml
analyzers:
  - name: saturation
    enabled: false           # zeroes saturation's signals
  - name: throughput
    enabled: true
    score: 1.0
```

---

## 3. Code changes on TA3

Concrete diff plan against today's TA3 tip (`7506634b`).

### 3.1 `cmd/main.go` — wiring update

Today (commit `b6e897c8`):
```go
registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer())
```

After rebase, `RegisterAnalyzer` returns an `error` (commit `6339e495` on
`multi-analyzer-registration`). Update to:
```go
registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
if err := engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer()); err != nil {
    return err
}
```

The exact return-handling matches sibling registration sites — match style on
the rebased main.

### 3.2 `internal/engines/saturation/engine.go` — drop the obsolete plumbing

The `engine.go` portions of `b6e897c8` (adding `analyzers map`,
`RegisterAnalyzer` method) are **obsolete** — equivalent plumbing landed via
#1225 with a different shape (slice + snapshot, error-returning). During the
rebase, drop those hunks. The wiring commit shrinks to `cmd/main.go` only.

### 3.3 `internal/engines/analyzers/throughput/analyzer.go` — adapt to the contract

Today's TA3 `Analyze()` (`analyzer.go`, ~341-352) writes RC/SC internally.
Migration:

**(a) Stop writing model-level RC/SC.** Lines `analyzer.go:331-339` (the
`requiredCapacity` and `spareCapacity` block) — delete. Result construction at
`:341-352`: leave `RequiredCapacity` and `SpareCapacity` zero (omit the
fields). Engine recomputes after `Analyze()` returns.

**(b) Replace local `totalSupply`/`totalDemand`/`totalAnticipated` accumulation
with `aggregation` helpers.** Today's per-variant loop accumulates these
locally (`:241-244`). Switch to sat_v2's pattern after the per-variant loop:
```go
totalSupply := aggregation.SumTotalSupply(variantCapacities)
totalAnticipatedSupply := aggregation.SumTotalAnticipatedSupply(variantCapacities)
totalDemand := aggregation.SumTotalDemand(variantCapacities)
```
The local accumulators in the per-variant loop go away. `anyEPP` /
`anyGPSMismatch` / `totalDecodeITLSat` / `nDecodeVariants` accumulators are
unrelated and stay.

**(c) Populate `TotalAnticipatedSupply` on the result.** Today TA computes
`totalAnticipated` and uses it inline for RC; under the contract it must be
published on `AnalyzerResult.TotalAnticipatedSupply` so the engine post-step
can read it. With (b) above, this is automatic.

**(d) Lift queue-demand attribution to per-role.** Today queue demand is added
to model-level `totalDemand` only (`:319-322`). Sat_v2 attributes queue demand
across active roles via `aggregateByRole(variantCapacities, queueDemand.byRole)`
so the per-role `TotalDemand` is correct. TA must do the same — pick whichever
role-attribution policy fits TA's semantics; the simplest is to mirror sat_v2:
split queue demand evenly across active non-prefill roles, since TA's queue
demand is decode-rate-denominated. Update `aggregateRoleCapacities` to take a
`queueDemandByRole map[string]float64` parameter.

**(e) Drop in-`aggregateRoleCapacities` RC/SC writes.** Lines `:789-803`:
the `required`, `spare`, `RequiredCapacity:`, `SpareCapacity:` writes —
delete. Keep the per-role `TotalSupply`/`TotalDemand`/`TotalAnticipatedSupply`
writes (engine reads these for the post-step). Add `TotalAnticipatedSupply:
ra.anticipated` to the `RoleCapacity` struct literal.

**(f) Drop the prefill-role RC suppression.** Lines `:789-797` ("RequiredCapacity
is only meaningful for decode/both roles…"): delete the `if vc.Role ==
"prefill"` branch. Per `7506634b` ("note that prefill role RC contribution is
negligible after OL guard"), prefill demand is ≈0 after the OL guard in
`computeLocalDemand`, so the engine's post-step formula yields RC≈0
naturally without an explicit suppression. **Verify with a test** (§3.4).

**(g) Drop the EPP/GPS-mismatch SpareCapacity gate.** Today TA suppresses SC
when `!anyEPP || anyGPSMismatch` (`:336-338`). The contract has no opt-out for
SC — engine post-step always computes both. The safety property the gate
protected (don't scale down on unreliable supply) is **lost in PR-5** and
restored in a follow-up (§6, item 1).

  Until that follow-up lands, document the regression in
  `docs/developer-guide/throughput-analyzer.md` and in the PR description.
  In practice, TA3 deployments with EPP-deployed clusters are unaffected;
  only EPP-absent or active-GPS-mismatch states see the regression.

**(h) Confirm `ReplicaCount` field.** Today
`VariantCapacities[].ReplicaCount` is set to `len(variantMetrics)`. Sat_v2
sets it to `readyCount` from `VariantStates`. Both intentionally exclude
pending/booting replicas. Verify they agree on TA3's e2e — if they diverge,
defer reconciliation to the "replica-count accounting" follow-up issue (§6,
item 2) and use whichever today's TA uses (`len(variantMetrics)`) as long as
the linearity invariant holds.

### 3.4 `internal/engines/analyzers/throughput/analyzer_test.go` — migrate assertions

55 RC/SC assertions across the test file. Three migration buckets:

**(i) RC>0 / SC>0 from totals.** Tests like `:296` "returns RequiredCapacity
> 0 when λ_dec exceeds μ_dec_total" are testing TA's *internal* RC computation.
Under the contract, the engine writes RC. Migration: assert on
`result.TotalDemand`, `result.TotalSupply`, `result.TotalAnticipatedSupply`
satisfying the inequality the engine's formula would interpret as RC>0
(`TotalDemand/scaleUp > TotalAnticipatedSupply` for a chosen `scaleUp`). The
engine's post-step is already covered by `engine_v2_threshold_test.go` on the
threshold branch — TA's tests don't need to re-test the formula.

**(ii) EPP-gated SC=0.** Tests like `:326` "returns zero SpareCapacity when
EPP is not deployed". With the gate dropped (§3.3 g), these assertions become
incorrect — TA will emit `TotalSupply > TotalDemand` and the engine will
compute SC>0. Recommendation: **delete and replace with a single spec** that
documents the intentional behavior change ("PR-5 drops the EPP/GPS SC gate;
restored in follow-up") so the regression is explicit in the test suite, not
silent.

**(iii) Prefill role RC=0.** Tests like `:636` "suppresses RequiredCapacity
for the prefill role". Under §3.3 (f), TA no longer suppresses; the OL guard
makes prefill `TotalDemand ≈ 0`. Migration: assert `prefillRC.TotalDemand ≈ 0`
(so the engine's formula yields RC≈0) and `decodeRC.TotalDemand > 0`. Drop
the direct `prefillRC.RequiredCapacity == 0` assertion since TA leaves it
zero anyway.

**New test specs to add:**
- `result.TotalSupply == aggregation.SumTotalSupply(result.VariantCapacities)`
- `result.TotalAnticipatedSupply == aggregation.SumTotalAnticipatedSupply(result.VariantCapacities)`
- `result.TotalDemand == aggregation.SumTotalDemand(result.VariantCapacities) + queueDemand` (where queue is configured)
- `result.RoleCapacities[role].TotalAnticipatedSupply` matches per-role aggregation
- `result.RoleCapacities[role].TotalDemand` includes the queue-demand share for that role
- `result.RequiredCapacity == 0` and `result.SpareCapacity == 0` on `Analyze` return (engine writes these later)

### 3.5 `docs/developer-guide/throughput-analyzer.md` — reflect the new contract

- Replace any prose that says "RequiredCapacity is computed model-level from
  totals" or "SpareCapacity is suppressed when EPP is absent" with: "TA
  publishes `Total*` fields; the engine's universal threshold post-step
  writes `RequiredCapacity` and `SpareCapacity`. See
  `docs/developer-guide/saturation-scaling-config.md` § Universal Threshold
  Post-Step for the formula."
- Drop prefill-suppression as a TA-internal feature; note it falls out of
  the OL guard naturally.
- Add a **Known regression** subsection: "PR-5 drops the EPP-presence and
  GPS-mismatch gates that previously suppressed SpareCapacity. Will be
  restored in a follow-up PR once the analyzer→engine contract supports an
  SC opt-out signal. Affects EPP-absent deployments and clusters where TA's
  GPS verification flags persistent mismatches."
- Document the operator-visible config: `analyzers:` list with
  `name: throughput`, `score`, optional per-analyzer threshold overrides
  (§2.6).
- Verify the doc reflects the actual code state of TA3 only — no
  forward-looking content.

---

## 4. E2E

`test/e2e/throughput_analyzer_test.go` already exists on TA3 (551 lines) with
three Describe blocks:

| Spec | Label | Status |
|---|---|---|
| "ThroughputAnalyzer wiring health check" — reconciles VA to steady state with both analyzers enabled | smoke + throughput | **PASSED** in Step 2e (2026-05-11), 210s |
| "ThroughputAnalyzer scale-up signal" — recommends scale-up under sustained load with both analyzers enabled | full + throughput | Not yet run (Step 2f pending Dean's discussion) |
| "ThroughputAnalyzer TA-only mode" — produces a positive desired allocation driven by TA; preserves accelerator info from VariantCapacities even with saturation disabled | full + throughput | Not yet run (Step 2f) |

**Contract-change impact on assertions:** the e2e specs assert on
VA-desired-allocation outcomes (`waitForPositiveDesiredAllocationAboveBaseline`,
preservation of accelerator info), not on `result.RequiredCapacity` /
`result.SpareCapacity` directly. The desired-allocation outcomes hold under
the new design — load → `TotalDemand/scaleUp > TotalAnticipatedSupply` → engine
emits RC>0 → optimizer scales → VA desired increases. **No e2e assertion
rewrites required.**

E2E stays in TA-PR5; no separate PR. Step 2f remains gated on Dean's
green-light (independent of this code rework). Future scenarios (cold-start,
multi-variant, etc.) deferred to a later PR — there are WVA benchmarking
changes in flight (see `planning/benchmark-wva-vs-keda-plan.md`); a future
TA PR will tap into those.

---

## 5. Verification gates

Each commit and the final tip must satisfy:

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- `go test -race ./internal/engines/analyzers/throughput/...` — clean.
- DCO sign-off (`Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`) on every
  commit.

E2E smoke (run from TA3 worktree once cluster is up):
- `make test-e2e-smoke ENVIRONMENT=kind-emulator` — Scenario 1 (TA wiring
  health check) passes; pre-existing failures unchanged (per
  `TA-e2e-plan.md`).

---

## 6. Commit shape (logical, for the review-ready history)

The coder is free to develop in whatever order and to rebase/squash before
opening the PR. The **final history** for review should land as roughly:

1. `engines/throughput: publish raw Total* fields; let engine compute RC/SC` —
   §3.3 a–c, e–g, the analyzer.go core change.
2. `engines/throughput: lift queue demand to per-role attribution` — §3.3 d.
3. `engines/throughput: tests migrated to engine-post-step contract` — §3.4.
4. `cmd: handle RegisterAnalyzer error return` — §3.1 (the wiring commit
   post-rebase; `engine.go` deltas from `b6e897c8` are dropped during
   rebase).
5. `docs/throughput-analyzer: reflect universal threshold post-step + SC
   gate regression` — §3.5.

Order is ergonomic, not load-bearing. Bundle however the diff reads cleanest.

### 6.1 Post-review follow-ups

After the initial PR-5 commits land and review completes (see
[`TA-PR5-review.md`](TA-PR5-review.md), Status: FINAL), three
small follow-up commits on TA3:

- **D1+D2 — analyzer.go doc-comment fixes.** Rewrite the `Analyze`
  function header (`analyzer.go:180-188`) and the
  `estimateQueueDemand` use-site comment (`:527`) to match the new
  contract. See review § D1, D2.
- **T1 — GPS-verification test renames.** Rename the
  `Describe("Analyze — GPS verification suppresses SpareCapacity",
  …)` block and its 4 sibling `It`s. **Preserve all scenario data
  and `SpareCapacity == 0` assertions verbatim** — they are
  fixtures for the future SC-gate-restoration PR (unified F3). Add
  one-line top-of-`Describe` comment noting fixtures preserved for
  future restoration. See review § T1.
- **T2 — aggregation-helper consistency specs.** Add the 5 missing
  specs from §3.4 ("New test specs to add" bullet list) that
  weren't included in the initial test migration. These lock the
  linearity invariant in TA's own test surface. See review § T2.

Don't-touch list (deliberate placeholders): the
`_ = anyEPP; _ = anyGPSMismatch` discards in `Analyze` stay; the
GPS-verification scenario data stays. See review § N1, T1.

H1 (RegisterAnalyzer error-return wiring) is tracked separately,
folded into the final rebase onto post-#1225 main.

---

## 7. Follow-up issues to open after PR-5

These belong in `session/CURRENT.md § Issues to Open`; cross-referenced here
so the coder confirms the PR description points at them.

1. **Restore the EPP/GPS-mismatch SC gate.** Either via an
   `AnalyzerResult.SuppressSpareCapacity` opt-out on the analyzer→engine
   contract, or via the deferred `ThresholdApplied` flag from
   `PR1113-review.md` Appendix B. PR-5 documents the regression in the
   developer-guide; the follow-up restores the safety property.
2. **Replica-count accounting consistency.** TA uses `len(variantMetrics)`
   for `VariantCapacity.ReplicaCount`; sat_v2 uses `readyCount` from
   `VariantStates`. Both intentionally exclude pending. Reconcile to a
   single source — likely the `VariantStates`-derived one, owned by the
   engine and passed through. Broader than TA; engine-side fix.
3. **`enabled:false` analyzer should be exempt from `needsScaleDown`.**
   Today (§2.8) saturation `enabled:false` zeroes its `Spare`, blocking
   all-down. TA-only scale-down therefore never fires. The slice predicate
   should treat disabled analyzers as "no opinion" rather than "vetoes".
   Fix on the optimizer branch.
4. **Prometheus gauges for ITL model coefficients** (already on the list
   from PR-4 Bob review, §3.1) — unchanged by this rework, listed for
   cross-ref.

---

## 8. Out of scope for PR-5

Preserved from the prior plan. Do not touch in PR-5:

- **Tier-3 `itlKnowledgeStore` wiring** — requires step-2 loop restructure
  (iterate all variant states, not just those with current metrics).
- **`DefaultKSat` unification** with EPP system-wide k_sat.
- **`ThresholdApplied` opt-out flag** (deferred per `PR1113-review.md`
  Appendix B).
- **Per-analyzer threshold override CRD plumbing** — already in place at the
  config level (§2.6); CRD-side surface deferred.
- **Prefill-specific rate signals** — prefill pods go through decode
  framework; RC≈0 falls out of the OL guard.
- **Saturation engine package rename** (`internal/engines/saturation/` →
  `…/engine/`) — long-term cleanup.
- **Engine-side `SchedulerQueue` wiring** — handled separately (see §1
  `engine-queue-fix` row and §2.7); a trigger has been sent to the
  optimizer coder.
- **Multi-analyzer optimizer coupling** — TA's result enters the slice
  alongside saturation; the Greedy fair-share picker handles the rest.
  No TA-side changes needed for that path.
- **Additional e2e scenarios** (cold-start, multi-variant, P/D
  disaggregated) — deferred to a later PR that taps into the in-flight
  WVA benchmarking work (`planning/benchmark-wva-vs-keda-plan.md`).

---

## 9. References

- `planning/multi-analyzer-threshold-plan.md` — base contract source
  (`Analyzer`, `AnalyzerResult`, `VariantCapacity`, `RoleCapacity`,
  `aggregation` package, engine post-step formula, `resolveThresholds`).
- `planning/multi-analyzer-optimizer-plan.md` — slice consumer
  (`NamedAnalyzerResult`, `ModelScalingRequest.AnalyzerResults`, picker
  helpers, saturation-always-runs invariant).
- `planning/PR1113-review.md` — design-settled rationale; Appendix B
  documents the deferred `ThresholdApplied` flag.
- `docs/developer-guide/saturation-scaling-config.md` (post-#1228) —
  formula authority and analyzer-responsibilities prose.
- `planning/TA-PR4-plan.md` — frozen retrospective on PR-4 internals
  (still accurate; not affected by this rework).
- `planning/TA-e2e-plan.md` — e2e infra and Scenario 1 wiring health
  check; Step 2f gated on Dean.
