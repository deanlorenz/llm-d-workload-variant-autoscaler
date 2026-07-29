# Analyzer Veto Liveness Gate — Type 3 Task Plan (PR D)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-veto-liveness` off `main` (`f5b7577c`; round-2 rebases onto the **current tip** of `upstream/main` — the moving ref, never a pinned SHA — see [D.0 {#d0}](#d0--rebase-onto-current-upstreammain-first-d0))
**Size:** engine state + 2 aggregation-helper changes + tests · **Reviewer session:** yes (core scale-down semantics)

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L35:66
- [Design {#design}](#design-design) L67:117
- [Open decision — staleness threshold {#threshold}](#open-decision--staleness-threshold-threshold) L118:134
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L135:163
- [Commit 1 — liveness field + engine state {#commit-1}](#commit-1--liveness-field--engine-state-commit-1) L164:217
- [Commit 2 — gate the veto helpers {#commit-2}](#commit-2--gate-the-veto-helpers-commit-2) L218:261
- [Tests to add {#tests}](#tests-to-add-tests) L262:289
- [Developer guide {#devguide}](#developer-guide-devguide) L290:301
- [Review follow-ups (round 1) {#followups}](#review-follow-ups-round-1-followups) L302:417
  - [F-B1 — QM path must stay always-live (code + test) {#f-b1}](#f-b1--qm-path-must-stay-always-live-code--test-f-b1) L310:334
  - [F-T1b — no-data → non-live is correct; document the persistence-window semantics (doc only) {#f-t1b}](#f-t1b--no-data--non-live-is-correct-document-the-persistence-window-semantics-doc-only-f-t1b) L335:361
  - [F-T1a — make the per-model keying test discriminate (test) {#f-t1a}](#f-t1a--make-the-per-model-keying-test-discriminate-test-f-t1a) L362:377
  - [F-Conc — document the single-writer assumption on lastGoodAnalysis (comment only) {#f-conc}](#f-conc--document-the-single-writer-assumption-on-lastgoodanalysis-comment-only-f-conc) L378:389
  - [F-Demand — liveness is supply/capacity currency; demand robustness is separate (doc only) {#f-demand}](#f-demand--liveness-is-supplycapacity-currency-demand-robustness-is-separate-doc-only-f-demand) L390:405
  - [F-NTH — two minor doc/comment touch-ups {#f-nth}](#f-nth--two-minor-doccomment-touch-ups-f-nth) L406:417
- [Review follow-ups (round 2 — ev-shindin PR #1481 comments) {#followups2}](#review-follow-ups-round-2--ev-shindin-pr-1481-comments-followups2) L418:620
  - [D.0 — Rebase onto current upstream/main FIRST {#d0}](#d0--rebase-onto-current-upstreammain-first-d0) L426:486
  - [D.1 — de-duplicate the no-data/error sentinel strings across packages {#d1}](#d1--de-duplicate-the-no-dataerror-sentinel-strings-across-packages-d1) L487:515
  - [D.2 — prune `lastGoodAnalysis` of departed models (code) {#d2}](#d2--prune-lastgoodanalysis-of-departed-models-code-d2) L516:541
  - [D.3 — demand-liveness detector: warn when supply is live but demand never is (code + comment + doc) {#d3}](#d3--demand-liveness-detector-warn-when-supply-is-live-but-demand-never-is-code--comment--doc-d3) L542:608
  - [Dev guide (round-2) {#devguide2}](#dev-guide-round-2-devguide2) L609:620
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L621:633

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
- `internal/engines/saturation/engine_queueing_model.go` — QM `NamedAnalyzerResult`
  construction (add static `Live: true`; review follow-up [F-B1](#f-b1)).
- New QM engine test (`engine_queueing_model_test.go` or sibling) — QM scale-down
  coverage ([F-B1](#f-b1)).
- Tests in the pipeline and saturation packages.
- `docs/developer-guide/multi-analyzer-pipeline.md` — the scale-down / all-agree section.

**Round-1 review follow-ups** ([§followups](#followups)) add the QM file/test above and a
set of doc/comment touch-ups on already-landed code; see that section for the exact changes.

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

## Review follow-ups (round 1) {#followups}

The internal review found the core mechanics correct (the `Live` field, the two gated
helpers, the safety floor, per-tuple keying, the fixtures, the dev-guide). The items below
are the agreed fixes — **all decisions locked by Dean 2026-07-27**. Apply them on top of the
existing three commits (`785b5350`, `77be65ca`, `b3b7f762`); group into commits as convenient,
all DCO-signed. Only **F-B1** and **F-T1a** touch code logic; the rest are doc/comment.

### F-B1 — QM path must stay always-live (code + test) {#f-b1}

**Problem.** The queueing-model optimize path builds its `NamedAnalyzerResult` inline in
`internal/engines/saturation/engine_queueing_model.go` (~L80-86,
`Name: domain.SaturationAnalyzerName`) and calls the shared `e.optimizer.Optimize`, but
**never sets `Live`**. With `Live == false`, the new safety floor in `needsScaleDownForRole`
skips every QM entry, `liveCount` stays 0, and QM **can never scale down** — a regression
(pre-PR, a QM result with `Spare > 0` scaled down normally via `initRoleState` →
`RoleSpare["both"]`).

**Fix (decision: static always-live).** At the QM `NamedAnalyzerResult` construction site,
set `Live: true` statically. Add a comment — plain prose, **no plans-branch identifiers**
(§4a) — explaining that the queueing-model path is intentionally always-live because it is
not yet a per-analyzer-liveness participant; its own liveness will be built when it becomes a
first-class multi-analyzer participant in future work. Do **not** wire QM into
`updateLivenessAndSetLive`, and do **not** touch any other QM code (the coder correctly left
QM byte-identical to `main` — keep it that way except this one field).

**Test (new coverage — the QM optimize path has none today).** Add a minimal engine-level
test (new `engine_queueing_model_test.go` or sibling) asserting a QM result with spare
capacity still scales down under the new gate. This pins the static-live guarantee against
future regressions and closes the coverage blind spot that let the regression pass green.

[↑ TOC](#toc)

### F-T1b — no-data → non-live is correct; document the persistence-window semantics (doc only) {#f-t1b}

**Resolution (locked): keep the mechanism unchanged — no code change to the liveness
definition.** The review asked whether liveness should derive from a uniform engine-level
nil/error signal instead of saturation's `no-data`/`error` reason strings. It should **not**
change: a mislabelled/broken Prometheus query does not make the analyzer *error* — it returns
a well-formed result with `no-data` (ready replicas + broken query → per-replica capacities
drop to nil → empty → `no-data`). The engine-level error/nil signal never fires for that case,
so the reason-based `resultIsInformative` check is **load-bearing** for detecting a
durably-broken analyzer. The staleness window is what correctly separates the two "no-data"
situations:

- **never had good data** (config bug / wrong label at startup) → `lastGoodAnalysis` never set
  → non-live → no veto ✓
- **had good data, transient no-data now** (blip, brief no-ready-replicas) → timestamp still
  fresh → live → still vetoes ("uncertain, err toward not scaling down") ✓
- **had good data, now stale > window** → aged out → non-live → no veto ✓

**Coder action (doc only):** in `docs/developer-guide/multi-analyzer-pipeline.md` (liveness /
scale-down section) add a short paragraph stating this — an analyzer reporting no usable
capacity (`no-data`) becomes non-live *only after* its last informative result ages out of the
staleness window; a transient no-data with a recent good result still participates; a
never-informative analyzer (e.g. a mislabelled query) never becomes live and cannot veto.
Current-code prose only, no plans-branch refs.

[↑ TOC](#toc)

### F-T1a — make the per-model keying test discriminate (test) {#f-t1a}

**Problem.** The `"scopes liveness per model"` spec in `engine_v2_liveness_test.go` does not
exercise per-tuple keying: its model-a step-2 result is *informative*, so it writes its own
`T_a` timestamp and yields `false` regardless of whether the map is correctly per-tuple
`(name, model, ns)` or the buggy name-only. Both keyings pass → it guards nothing.

**Fix.** Make model-a's step-2 result **non-informative** (`Reason: "no-data"`) so it does
**not** write `T_a`. Then:
- correct per-tuple map → `T_a` never written → `Live == false` ✓
- (would-be) name-only map → step-1's model-b write to the shared `"saturation"` key reads
  back as live → `Live == true` — the test now *fails* under name-only keying, which is the
  property a regression guard for the deliberate per-tuple choice must have.

[↑ TOC](#toc)

### F-Conc — document the single-writer assumption on lastGoodAnalysis (comment only) {#f-conc}

**Resolution (locked): comment only, no lock.** `lastGoodAnalysis` is safe today because the
`PollingExecutor` runs cycles sequentially in one goroutine and models are processed serially
— the same single-writer assumption the unguarded `vaEventTracker` already relies on. Add a
field comment on `lastGoodAnalysis` (mirroring `vaEventTracker`'s) noting that safety depends
on non-overlapping single-goroutine cycles, and that parallelizing model processing would
require synchronizing this map (its top-level insert would race first). No `sync.Mutex` /
`sync.Map`.

[↑ TOC](#toc)

### F-Demand — liveness is supply/capacity currency; demand robustness is separate (doc only) {#f-demand}

**Decision (Dean, option 1):** PR D's liveness gates on **supply/capacity** informativeness
only; it does **not** attempt to detect broken *demand*. That is correct and intentional — a
false-low demand biases toward scale-down (never toward a spurious veto), and demand
robustness is handled by other mechanisms: the metric sanity filter on calibration inputs, the
request-rate / local-demand backstops, the model-level arrival rewire (removes the per-pod
EPP-merge false-0 class), and the future per-analyzer status contract.

**Coder action (doc only):** add one sentence to the dev-guide liveness section stating the
boundary — liveness reflects whether an analyzer has a *current capacity* signal; robustness
of the *demand* signal is out of scope for the veto gate and handled upstream (metric sanity +
demand fallbacks). Current-code prose only.

[↑ TOC](#toc)

### F-NTH — two minor doc/comment touch-ups {#f-nth}

1. Dev-guide responsibility table: it attributes `Live` to the engine "applying uniformly to
   every analyzer." With the QM static-live fix that is no longer literally uniform — reword to
   note the multi-analyzer path is liveness-gated while the queueing-model path is statically
   live (prose, no plans-branch refs).
2. `analyzer_helpers.go`: add a one-line comment on `applyDeallocationForRole` noting it is
   intentionally **not** `Live`-gated — harmless, because non-live entries are excluded from the
   veto and the safe-removal min, so mutating their `RoleSpare` affects nothing that is read.

[↑ TOC](#toc)

## Review follow-ups (round 2 — ev-shindin PR #1481 comments) {#followups2}

Three folds land on top of the round-1 commits, **all decisions locked by Dean 2026-07-29**.
Two are ev-shindin's PR comments (D.1, D.2); the third (D.3) is the demand-liveness detector
Dean designed in response to the C-side "never-live demand" review point (folded into D because
it lives at the same engine liveness site). Group into commits as convenient, all DCO-signed.
D.1 is a refactor/test; D.2 is code; D.3 is code + comment + doc.

### D.0 — Rebase onto current upstream/main FIRST {#d0}

**Dean explicitly authorized this rebase (2026-07-29).** Normally an open-PR branch does not
chase `main`; here Dean directed it because `main` advanced materially since this branch's base
and the round-2 folds must land on current code. This authorization is specific to the C/D
round-2 work — it does not generalize to other open PRs.

**Target — always the live tip, never a pinned SHA.** Rebase `ta-veto-liveness` onto the current
tip of `upstream/main`:

```
git fetch upstream
git rebase upstream/main
```

`upstream/main` is a **moving ref** — rebase onto whatever it points to at the moment you run this.
Do **not** substitute a specific commit SHA for `upstream/main`: the tip advances, a pinned SHA goes
stale, and it misreads as "rebase onto exactly this one commit." Any SHA named below is
informational context as of authoring only — the rebase target is the ref, full stop.

**Churn to expect during conflict resolution** (as of authoring, `upstream/main` had advanced past
this branch's merge-base `11d70a8a`, the #1479 merge, with — among others — a
`internal/saturation → internal/saturationv1` rename, a `pkg/ → internal/queueing` move, and a
change wiring the optimize-loop interval via an env var; **more may have landed since — diff against
your actual rebased base, do not treat this list as complete**):

- The renames/moves do **not** relocate D's three core files:
  `internal/engines/saturation/engine_v2.go`, `internal/engines/pipeline/analyzer_helpers.go`,
  `internal/domain/analyzer.go`. But any *import* of a renamed/moved package inside files this branch
  touches (or their tests) needs the new path. Import-path churn, not a logic change — fix and move on.
- **Re-verify the optimize-loop-interval interaction by hand.** D's staleness threshold is
  `analyzerLivenessStaleCycles × OptimizationInterval` (Commit 1). If a main change relocated or
  renamed how the optimize loop obtains its interval, confirm the interval value D reads for the
  threshold still resolves from the same source and the threshold semantics are intact; update D's
  reference **and** its test if it moved.

**Procedure** (CONVENTIONS non-trivial-rebase rule applies — multi-commit stack, and touched files
may import moved packages):

1. Before rebasing, write the pre-rebase plan in **your status file**
   (`plans/session/status/ta-veto-liveness.md`) — you have no write access to `planning/`. List the
   round-1 + round-2 commits with a one-line "behavior to preserve" each, the files you expect to
   conflict (import-path churn from #1450/#1448; the #1487 interval site), and the post-rebase
   checklist.
2. After the rebase: per-file `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` for every
   touched file; confirm every claimed behavior survived (git's three-way merge can silently drop a
   hunk that no longer applies cleanly).
3. Per-commit message-vs-diff check.
4. **Re-verify every anchor this plan cites** (line numbers in `engine_v2.go`,
   `analyzer_helpers.go:35-38/44/237/292`, `domain/analyzer.go` `TotalDemand`) — line numbers shift
   under rebase; re-grep before editing.

Rebasing rewrites this branch's history, so the eventual push is `--force-with-lease` — **Dean
confirms that separately at push time; do not push.** If a conflict looks like it would drop
behavior and you cannot resolve it cleanly, hand it back in your status file rather than forcing it.

Note: after #1448 the `./pkg/...` path in the pre-push `gofmt` line may no longer exist — expected;
`./internal/...` now covers the moved packages.

[↑ TOC](#toc)

### D.1 — de-duplicate the no-data/error sentinel strings across packages {#d1}

**Problem (ev-shindin).** The `"no-data"` / `"error"` `VariantCapacity.Reason` sentinels are
declared as literals in **two** packages: `pipeline/analyzer_helpers.go:35-38`
(`analyzerReasonNoData` / `analyzerReasonError`, consumed by `ResultIsInformative`) and the
saturation_v2 analyzer package that **produces** them (grep for `"no-data"` / `"error"` reason
assignments — e.g. `satReason*` constants). Two independent literals for the same wire contract
can silently drift; a rename on one side breaks liveness detection with no compile error.

**Fix (decision: single source if layering allows, else a pin test).** First map the import
graph between the producer package and `pipeline`:

- **If one package can import the other without a cycle** (`pipeline` is the lower layer — the
  saturation engine already imports it), promote the sentinels to the lower layer, export them
  (`pipeline.ReasonNoData` / `pipeline.ReasonError`), and have the producer reference the
  exported constants. One definition, no drift possible. Confirm with `go build ./...`.
- **If a shared constant would introduce an import cycle** (producer is a sibling that neither
  imports nor is imported by `pipeline`), do **not** force a new shared low-level package for two
  strings. Instead add a **cross-package pin test** (in the `pipeline` test package, which may
  import both) asserting the producer's constants equal `pipeline`'s — so a future drift fails a
  test rather than silently disabling the liveness gate. State in the test comment why a shared
  constant was not used (the layering reason).

Pick based on the **actual** import graph — do not guess. Classify nothing as deleted unless a
literal is actually removed (then note it DEPRECATED-superseded-by-the-shared-constant in the
handoff).

[↑ TOC](#toc)

### D.2 — prune `lastGoodAnalysis` of departed models (code) {#d2}

**Problem (ev-shindin).** `e.lastGoodAnalysis` gains an outer `modelKey` entry for every model
ever analyzed (`updateLivenessAndSetLive`, engine_v2.go:186-189) and **never evicts** one. A
model that is deleted from the cluster leaves its entry resident for the controller's lifetime.
It does not persist across a controller restart (in-memory only), so the leak is bounded by
uptime, not unbounded forever — but it is still a real per-model accumulation that should be
pruned.

**Fix — selective eviction, NOT a per-cycle reset.** The latch's whole purpose is cross-cycle
persistence (round-1 F-T1b), so it must **not** be cleared each cycle like `vaEventTracker`.
Instead, at the **per-cycle boundary where the full set of models being optimized this cycle is
known** (the caller that loops models and invokes the per-model analyze path — find the
enumeration site above `updateLivenessAndSetLive`, one call layer up), prune outer `modelKey`s
of `lastGoodAnalysis` that are **absent** from the current active-model set. Keep every key that
is still active (preserving its supply/demand timestamps). This is a set-difference delete on the
outer map only; inner per-analyzer maps for surviving models are untouched.

If the active-model set is not cleanly available at a single call site, hand that back in the
handoff rather than reaching across scope — but it should be: the loop that produced the model
list this cycle is the natural owner. Guard against the empty-set case (a cycle that legitimately
sees zero models must not wipe the whole map — only prune when the active set is the authoritative
current set, not a transient empty read).

[↑ TOC](#toc)

### D.3 — demand-liveness detector: warn when supply is live but demand never is (code + comment + doc) {#d3}

**Origin.** The C-side review surfaced a "never-live demand" concern: if the EPP arrival query is
broken or EPP is absent, the throughput analyzer's model-level demand (`Result.TotalDemand`,
`domain.AnalyzerResult.TotalDemand`) stays **0** every cycle, yet the analyzer remains **live**
because its liveness is *supply*-driven (its ITL/KV per-replica capacities resolve and emit
non-sentinel reasons regardless of arrival). So "supply live, demand always zero" is invisible to
the round-1 liveness gate. Dean's decision: detect it as an **observability signal only** — a WARN
log — never a veto.

**Why warn-only is sufficient and a veto would be wrong (this rationale MUST appear as a code
comment at the detector, plain prose, no plans-branch refs per §4a):**
- Zero demand is a **legitimate** state, not necessarily a fault: with no served-rate floor,
  arrival→0 correctly drives `TotalDemand→0`, which only *permits* scale-down and never forces a
  scale action — a missing or zero arrival signal can therefore never cause a spurious scale-up
  or a spurious veto. Vetoing on "demand looks absent" would defeat the very scale-down the
  round-1 gate exists to enable.
- The veto path is already handled by the **supply/capacity** liveness gate (round-1): an
  analyzer with no *capacity* signal is excluded from the scale-down vote. The demand detector is
  strictly additive telemetry pointing a human at a likely-broken arrival query.
- **Mechanically it cannot veto even by accident:** the demand latch is stored in the same
  `lastGoodAnalysis[modelKey]` map under a **synthetic inner key** that is not any real analyzer
  name, and the Live/veto path only ever reads that map via **keyed lookups on real analyzer
  names** (`perAnalyzer[nr.Name]` in `updateLivenessAndSetLive`; the helpers read `e.Live`, never
  the map). The map is never ranged over in the decision path, so a synthetic key can never flip
  any `nr.Live`.

**Design — two latches, one map, timestamp delta is the signal:**
- **Supply latch (existing):** `perAnalyzer[throughputName]` — the throughput analyzer's
  last-informative timestamp, already maintained by round-1 (`ResultIsInformative` → supply
  resolved). This is the "supply ever/recently live" signal.
- **Demand latch (new):** stamp `perAnalyzer[demandKey] = now` (or `nr.Result.AnalyzedAt`) each
  cycle the throughput entry has `Result.TotalDemand > 0`, where `demandKey` is derived from the
  throughput analyzer name plus a suffix that **cannot collide with any real analyzer name**
  (e.g. `throughputName + "\x00demand"` — a NUL-delimited sentinel; document the choice). Same
  map, so it is pruned by D.2 for free and shares the single-writer assumption (round-1 F-Conc).
- **Signal (WARN):** in `updateLivenessAndSetLive` (it already has `now`, `perAnalyzer`,
  `threshold`, and the interval), after the liveness loop, for the throughput entry: if its
  supply latch is live now (present and within `threshold`) **AND** the demand latch is either
  never set or its timestamp lags the supply latch by **≥ the staleness window** (`threshold`),
  log a WARN via the engine logger. Use a timestamp gap (not a bool) precisely so a **cold-start
  EPP scrape lag** — supply comes up a cycle or two before the first arrival scrape — does **not**
  false-positive: the gap is still `< threshold` during warm-up and only trips once demand has
  been absent for a full staleness window. Message (prose, no plans refs): the throughput
  analyzer has a live capacity/supply signal but has reported **no demand for ≥ the staleness
  window**, which usually means the request-arrival query is misconfigured or EPP is not
  reporting arrivals; scale-up will not trigger until arrivals are observed. Do **not** set
  `nr.Live`, do **not** touch any `RoleSpare`, do **not** gate any decision on this.
- Scope for 0.9: the detector pairs the **throughput** analyzer's supply and demand (it is the
  arrival-driven demand consumer that can silently zero). Generalizing to other analyzers'
  demand is out of scope.

**DEFERRED — per-pod demand latch (future).** When demand becomes per-pod/per-replica, the
demand latch inner key extends with a pod component (`throughputName + "\x00demand" + "\x00" +
podID`), and a per-replica demand latch is added alongside. Not built now (0.9 demand is
model-level). Record in the handoff as DEFERRED with this intent so it is recoverable.

**Test.** Engine-level test asserting: (1) throughput supply informative + `TotalDemand > 0`
every cycle → no warn (demand latch keeps pace); (2) throughput supply informative but
`TotalDemand == 0` for `> threshold` → warn fired (capture via a test logger sink), and crucially
`nr.Live` for throughput stays **true** and scale-down/veto behavior is unchanged (the detector
did not affect the decision); (3) cold-start: supply live one cycle, demand zero that cycle only
→ **no** warn (gap `< threshold`). Assert the synthetic demand key never appears in a keyed
`nr.Name` lookup (or simply that a model with only the synthetic key present cannot become live).

[↑ TOC](#toc)

### Dev guide (round-2) {#devguide2}

`docs/developer-guide/multi-analyzer-pipeline.md`, liveness/scale-down section (the one round-1
edits): add a short paragraph describing the demand-liveness telemetry — the engine logs a
warning when an analyzer has a live capacity signal but no observed demand for the staleness
window (typically a broken arrival query / EPP not reporting), and that this is **observability
only**: it never changes liveness or the scale-down vote, because zero demand is a legitimate
state that only permits (never forces) scale actions. Current-code prose only; no plans-branch
refs; no "PR C/D" cross-references.

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
