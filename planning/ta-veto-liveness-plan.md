# Analyzer Veto Liveness Gate — Type 3 Task Plan (PR D)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-veto-liveness` off `main` (`f5b7577c`)
**Size:** engine state + 2 aggregation-helper changes + tests · **Reviewer session:** yes (core scale-down semantics)

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L22:53
- [Design {#design}](#design-design) L54:104
- [Open decision — staleness threshold {#threshold}](#open-decision--staleness-threshold-threshold) L105:121
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L122:143
- [Commit 1 — liveness field + engine state {#commit-1}](#commit-1--liveness-field--engine-state-commit-1) L144:197
- [Commit 2 — gate the veto helpers {#commit-2}](#commit-2--gate-the-veto-helpers-commit-2) L198:241
- [Tests to add {#tests}](#tests-to-add-tests) L242:269
- [Developer guide {#devguide}](#developer-guide-devguide) L270:281
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L282:294

## Overview {#overview}

**The problem (Dean's point 1).** Scale-down requires *every* analyzer in the slice to
agree there is spare capacity — `needsScaleDownForRole`
([analyzer_helpers.go:237](../Main/internal/engines/pipeline/analyzer_helpers.go#L237))
returns false if **any** analyzer has `RoleSpare[role] ≤ 0` or nil `RoleSpare`. An
analyzer with no data produces `TotalSupply=0 → SpareCapacity=0 → RoleSpare=0`, so a
**non-informative analyzer silently vetoes scale-down** — whether it failed to register,
never received metrics, or is in an error state. The veto is meant for *transient
uncertainty* ("we're not sure, err on the side of not scaling down prematurely"), not for
an analyzer that is permanently or durably providing nothing.

**The principle.** Regardless of *how* an analyzer ended up with no information, it must
not hold veto power. A "last non-error analysis time" is sufficient: **never analyzed →
ignore; last good analysis is stale → ignore.** On recovery (a fresh good analysis) the
analyzer rejoins automatically — this is inherent to a per-cycle recompute (Dean's
point 3).

**Relationship to PR A′ (`ta-registration-safety`).** A′ fixes `effectiveEnabled` so a
config-*absent* analyzer is never added to the slice at all (opt-in hygiene; prevents it
running). PR D handles the analyzer that *is* in the slice but is uninformative this
cycle (never-had-metrics / error-state). They are complementary — keep both. PR D does
not depend on A′ and can land in either order.

**Relationship to #1261 (per-analyzer status).** This is the coarse, time-based version.
Once #1261 lands a proper per-analyzer status contract, the liveness signal can become
finer-grained (error rate, partial-info, suppress-SC vs suppress-RC). PR D is the
minimum that makes TA safe to enable now; it should be written so #1261 can refine it,
not fight it.

[↑ TOC](#toc)

## Design {#design}

**Saturation is NOT blanket-exempt (Dean's point 2).** Saturation does two jobs:
- **(a) shared collection** — vLLM cache size, replica cost, etc. — feeding *all*
  analyzers and the cost optimizer. This is upstream of the analyzer results (collector
  layer), not a vote. If (a) is broken, every analyzer gets no data → all become
  non-live → the safety floor below stops scale-down, and the cost optimizer fails
  independently. No special-casing needed.
- **(b) token-capacity analysis** — saturation_v2's own `AnalyzerResult`. This is *just
  another analyzer's opinion* and must be subject to the same liveness gate. In a
  TA-only configuration where (b) is not producing capacity, saturation (b) must **not**
  veto. Therefore the veto gate applies **uniformly, including saturation (b)** — no
  name-based exemption inside `needsScaleDownForRole` / `safeRemovalReplicasForRole`.

  (The existing `effectiveEnabled` name-exemption that keeps saturation *running*
  stays — saturation must run to perform collection (a) and to have the chance to be
  live. That is about participation, not veto.)

**Liveness definition.** An analyzer is **live** for the current cycle iff it produced a
non-error, informative result within the staleness window:
- The engine keeps `lastGoodAnalysis map[string]time.Time` on the `Engine` struct
  ([engine.go:132](../Main/internal/engines/saturation/engine.go#L132)), persisted across
  cycles (alongside `analyzers []analyzerEntry`).
- After analyzers run each cycle, for every analyzer whose result is **informative**, set
  `lastGoodAnalysis[name] = result.AnalyzedAt`.
- **Informative** = result non-nil, not an error, and carrying usable capacity: at least
  one `VariantCapacity` whose `Reason ∉ {"no-data", "error"}` (see the Reason enum on
  `domain.VariantCapacity`), and populated `RoleCapacities`/`RoleSpare`. Write a helper
  `resultIsInformative(nr NamedAnalyzerResult) bool`.
- An analyzer is **live** iff `lastGoodAnalysis[name]` exists AND
  `now − lastGoodAnalysis[name] ≤ stalenessThreshold`.

**The gate.** In `needsScaleDownForRole` and `safeRemovalReplicasForRole`, **skip
non-live analyzers** — they neither veto nor constrain the safe-removal minimum.

**Safety floor (critical).** If, after skipping non-live analyzers, **no live analyzer
remains** for the role, `needsScaleDownForRole` must return **false** (do not scale
down). Without this, an all-skipped slice would fall through the `for` loop and return
`true` — scaling down with zero basis. This also makes leader failover safe: in-memory
`lastGoodAnalysis` is empty after failover → all analyzers non-live → no scale-down until
at least one produces a fresh good result (which happens within a cycle or two). Erring
toward "don't scale down until we have current information" is the intended direction.

**Plumbing.** Compute liveness in the engine and expose it to the pure helpers rather
than giving them clock/state access. Add a `Live bool` field to
`pipeline.NamedAnalyzerResult`; the engine sets it before calling the role helpers. The
helpers then skip `!e.Live`. (Verify the exact definition site of `NamedAnalyzerResult`
in the pipeline package and add the field there.)

[↑ TOC](#toc)

## Open decision — staleness threshold {#threshold}

The threshold that separates "transient blip, keep trusting the last value" from "stale,
ignore" is a tuning decision for Dean. Options to present, not to pick unilaterally:
- **Fixed multiple of the reconcile interval** (e.g. `3 × cycle`) — simple, no config
  surface. Default recommendation.
- **Configurable** per-deployment (a new field in the saturation scaling config) —
  flexible but adds config + docs + validation.

Implement the fixed-multiple as a named constant (e.g. `analyzerLivenessStaleCycles = 3`)
with a clear comment, and leave a `// TODO: make configurable` if Dean wants the config
path later. **Confirm the multiple with Dean before finalizing** — this is a coding
judgment call with production consequences (too short → flaps ignore a slow-but-valid
analyzer; too long → a dead analyzer keeps vetoing).

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope:**
- `internal/engines/pipeline/analyzer_helpers.go` — `needsScaleDownForRole` (L237),
  `safeRemovalReplicasForRole` (L193), and the `NamedAnalyzerResult` type (add `Live`).
- `internal/engines/saturation/engine.go` — `Engine` struct field `lastGoodAnalysis`;
  update it and set `Live` on each result in the per-cycle path (find where
  `runAnalyzersAndScore` / the role helpers are invoked).
- Tests in the pipeline and saturation packages.
- `docs/developer-guide/multi-analyzer-pipeline.md` — the scale-down / all-agree section.

**Non-goals:**
- Do **not** implement the #1261 per-analyzer status contract here — this is the coarse
  time-based precursor.
- Do **not** change `effectiveEnabled` (that's A′) or add per-analyzer error-rate /
  partial-info signals.
- Do **not** touch the scale-*up* path — `RequiredCapacity` aggregation
  (`roleAggRemaining`, `anyRoleNeedsScaleUp`) uses max-across-analyzers, where a
  no-data analyzer contributes 0 and is harmless. This PR is scale-down only.

[↑ TOC](#toc)

## Commit 1 — liveness field + engine state {#commit-1}

1. **`NamedAnalyzerResult.Live`.** Find the type definition in the pipeline package
   (grep `type NamedAnalyzerResult`) and add:
   ```go
   // Live indicates the analyzer produced a non-error, informative result within the
   // staleness window. Set by the engine each cycle. Non-live analyzers are excluded
   // from the scale-down veto so a registered-but-uninformative analyzer (no metrics,
   // error state, never analyzed) cannot block scale-down. Recovery is automatic: a
   // fresh informative result makes it live again on the next cycle.
   Live bool
   ```

2. **Engine state.** In `Engine` struct (engine.go:132), add:
   ```go
   // lastGoodAnalysis records, per analyzer name, the AnalyzedAt of the most recent
   // informative (non-error, capacity-bearing) result. Used to gate the scale-down
   // veto: an analyzer whose last good analysis is absent or staler than
   // analyzerLivenessStaleCycles cycles does not participate. In-memory only; reset on
   // process restart / leader failover (safe: non-live → no scale-down until refreshed).
   lastGoodAnalysis map[string]time.Time
   ```
   Initialize it in the engine constructor (grep `NewEngine` / the struct literal).

3. **Helper `resultIsInformative`.** Add to the pipeline package (near the helpers):
   informative iff `nr.Result != nil`, no error was recorded for it, and at least one
   `VariantCapacity.Reason ∉ {"no-data","error"}` with populated role capacities. Read
   the current `domain.VariantCapacity.Reason` enum values first
   (`internal/domain/analyzer.go`) — transcribe the actual sentinel strings, do not
   assume.

4. **Per-cycle update + Live assignment.** Locate the per-cycle path where the analyzer
   slice is built and the role helpers are called (in engine_v2.go / engine.go). After
   results are produced:
   - for each result, if `resultIsInformative`, set `lastGoodAnalysis[name] =
     result.AnalyzedAt`;
   - set `nr.Live = lastGoodAnalysis[name] exists && now − it ≤ threshold` for each `nr`
     before invoking `needsScaleDownForRole` / `safeRemovalReplicasForRole`.

   `now` must come from the same clock the results use (`AnalyzedAt`'s source) — do not
   introduce a second time source.

**Commit message:**
```
saturation: track per-analyzer liveness (last informative analysis)

Add Engine.lastGoodAnalysis and NamedAnalyzerResult.Live. Each cycle, an
analyzer that produced a non-error, capacity-bearing result refreshes its
timestamp; Live reflects whether that timestamp is within the staleness window.
No behavior change yet — Commit 2 consumes Live in the scale-down veto.
```

[↑ TOC](#toc)

## Commit 2 — gate the veto helpers {#commit-2}

In `internal/engines/pipeline/analyzer_helpers.go`:

**`needsScaleDownForRole` (L237)** — skip non-live analyzers and add the safety floor:
```go
func needsScaleDownForRole(s []NamedAnalyzerResult, role string) bool {
    liveCount := 0
    for _, e := range s {
        if !e.Live {
            continue // non-live analyzers do not veto (no metrics / error / never analyzed)
        }
        if e.Result == nil || e.RoleSpare == nil || e.RoleSpare[role] <= 0 {
            return false
        }
        liveCount++
    }
    // Safety floor: with no live analyzer, we have no current basis to scale down.
    return liveCount > 0
}
```

**`safeRemovalReplicasForRole` (L193)** — skip non-live analyzers in the min loop:
add `if !e.Live { continue }` at the top of the range body (before the existing
`e.Result == nil || e.RoleSpare == nil` guard). The existing `found` flag already returns
0 when nothing contributes, which is the correct conservative result.

**Verify** no other caller of these helpers assumes the old "all entries vote"
semantics: grep `needsScaleDownForRole` / `safeRemovalReplicasForRole` across the
package.

**Commit message:**
```
saturation: exclude non-live analyzers from the scale-down veto

needsScaleDownForRole and safeRemovalReplicasForRole now skip analyzers whose
last informative analysis is absent or stale, so a registered-but-uninformative
analyzer no longer vetoes scale-down. Applies uniformly, including saturation's
token-capacity result. Safety floor: with no live analyzer, scale-down is
withheld (no current basis), which also makes leader failover safe.
```

[↑ TOC](#toc)

## Tests to add {#tests}

In the pipeline package (`analyzer_helpers_test.go` or sibling):
1. **Never-analyzed → no veto.** A slice with one live analyzer (RoleSpare>0) and one
   non-live analyzer (`Live=false`, RoleSpare nil/≤0) → `needsScaleDownForRole` returns
   **true** (the non-live one does not block).
2. **Stale → no veto.** Same as (1) but the non-live one is stale — asserted via
   `Live=false`. (Staleness computation itself is tested at the engine level.)
3. **Safety floor.** All analyzers `Live=false` → `needsScaleDownForRole` returns
   **false**.
4. **Live no-spare still vetoes.** A live analyzer with `RoleSpare[role] ≤ 0` → returns
   **false** (real veto preserved).
5. **safeRemoval skips non-live.** A non-live analyzer with a tiny RoleSpare does not
   drag the min to 0.
6. **Saturation not exempt.** A `Live=false` result named `SaturationAnalyzerName` is
   skipped like any other (no name-based special case).

In the saturation package (engine-level):
7. **Recovery.** Drive two cycles: cycle 1 the analyzer returns `Reason=no-data`
   (non-live, does not veto); cycle 2 it returns a capacity-bearing result → becomes live
   and, if RoleSpare≤0, now vetoes. Asserts the timestamp update + recompute.
8. **Staleness boundary.** An analyzer whose `lastGoodAnalysis` is exactly at / just past
   the threshold flips live→non-live.

Run with `-race` (the engine map is written per cycle).

[↑ TOC](#toc)

## Developer guide {#devguide}

**Target:** `docs/developer-guide/multi-analyzer-pipeline.md`, the scale-down / all-agree
section. Document: scale-down requires all **live** analyzers to agree there is spare;
an analyzer with no current informative result (never analyzed, error state, or stale)
is excluded from the vote and cannot block scale-down; with no live analyzer, scale-down
is withheld; saturation's token-capacity result is gated the same as any analyzer, while
its shared collection role is a separate upstream concern. Describe current code only
(Type 4). Do not reference #1261 or the plans branch.

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

1. `git branch --show-current` → `ta-veto-liveness`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (new pipeline + engine tests).
4. `make lint` — clean.
5. DCO sign-off on every commit (`git commit -s`).
6. `go build ./...` — clean.

When green, write `plans/session/handoffs/review__ta-veto-liveness-ready.md` and stop.
Do not push.

[↑ TOC](#toc)
