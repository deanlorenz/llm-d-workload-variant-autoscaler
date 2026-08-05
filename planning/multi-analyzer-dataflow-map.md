# Multi-Analyzer Data-Flow Map

**Status:** DRAFT — first pass, synthesized from six parallel read-only code traces. Load-bearing
claims (§5's combine functions, the stale doc-comment) were independently re-verified against the
live file; the bulk of the per-analyzer step detail (§3) was not yet independently re-verified
line-by-line and should be treated as "high confidence, not adversarially checked."

**Base code:** `main @ 9906dac5` (`Main/` worktree; also happens to be the ta-anchor-refactor
plan's stated base, so this doc and that plan are describing the same code).

**Purpose.** This is a *retrospective/descriptive* map of how the multi-analyzer engine works
**today** — not a design doc, not a review of a plan. It exists to answer, with file:line
precision: when multiple analyzers exist, what data gets generated, by what code, behind what
gates, and what happens to it in the optimizer. It is a new document category (not Type 1-6 per
`session/CONVENTIONS.md`); it lives in `planning/` at Dean's direction and may get formalized into
the taxonomy later.

**Headline finding (read this first).** The premise "we did not add new logic, just trying to
allow multiple analyzers which were already supposed to be" is **correct, and more true than it
might feel from inside the anchor-refactor plan's complexity.** The optimizer already has a real,
wired-in cross-analyzer combine mechanism for the *quantity* math (how many replicas to add or
remove) — `roleBottleneckReplicas` (max across analyzers), `needsScaleDownForRole` +
`safeRemovalReplicasForRole` (unanimous-live-veto + min across analyzers), `fairShareValue`
(score-weighted sum) — all confirmed live in `internal/engines/pipeline/analyzer_helpers.go` and
wired into both optimizers today (§5). What is **not** combined, and is genuinely single-sourced
from saturation-v2 only, is *identity/metadata*: which variants exist, their `Cost`,
`AcceleratorName`, `Role`. That narrower gap — not a missing combine engine — is the real shape of
what any anchor/binding-refactor work needs to solve. A stale code comment
(`engine.go:208-213`, quoted in §5) currently describes the old, pre-combine state and should be
corrected independent of any refactor.

---

## Reading Protocol

Don't read this file top-to-bottom in one sitting. Read the **TOC** below, then fetch one section
at a time via `Read <file> offset:<n> limit:<m>` (limit = end−start+1). §0 and §5 are the two
sections worth reading even for a five-minute skim.

---

## TOC

- [§0 Orientation — the big picture](#0-orientation--the-big-picture) L111:152
- [§1 Call-stack sketch](#1-call-stack-sketch) L153:199
- [§2 Dispatch — V1 / V2 / QM are mutually exclusive](#2-dispatch--v1--v2--qm-are-mutually-exclusive) L200:226
- [§3 Phase 1 — Generation](#3-phase-1--generation) L227:377
  - [§3.1 Saturation-v2 (sat-v2)](#31-saturation-v2-sat-v2) L233:276
  - [§3.2 Throughput analyzer (TA)](#32-throughput-analyzer-ta) L277:328
  - [§3.3 Queueing-model analyzer (QM)](#33-queueing-model-analyzer-qm) L329:347
  - [§3.4 Engine orchestration — assembling the ballot](#34-engine-orchestration--assembling-the-ballot) L348:377
- [§4 Phase 2 — Optimizer consumption](#4-phase-2--optimizer-consumption) L378:508
  - [§4.1 Optimizer selection](#41-optimizer-selection) L385:392
  - [§4.2 Binding-entry resolution (`saturationEntry`)](#42-binding-entry-resolution-saturationentry) L393:420
  - [§4.3 Role-state init — where multi-analyzer data first mixes](#43-role-state-init--where-multi-analyzer-data-first-mixes) L421:431
  - [§4.4 Scale-up core loop](#44-scale-up-core-loop) L432:447
  - [§4.5 Scale-down core loop](#45-scale-down-core-loop) L448:461
  - [§4.6 Rescale pre-pass (GreedyByScore only)](#46-rescale-pre-pass-greedybyscore-only) L462:490
  - [§4.7 Final `VariantDecision` assembly](#47-final-variantdecision-assembly) L491:508
- [§5 The core question — where does multi-analyzer combine actually happen today?](#5-the-core-question--where-does-multi-analyzer-combine-actually-happen-today) L509:570
- [§6 QM in one paragraph](#6-qm-in-one-paragraph) L571:586
- [§7 Loose ends / candidate follow-ups](#7-loose-ends--candidate-follow-ups) L587:623
- [§8 Dean's review annotations (live, in progress)](#8-deans-review-annotations-live-in-progress) L624:1418
  - [A1 — REVISED: QM must not affect the anchor/multi-analyzer work now; properly fixing QM is a separate, later concern](#a1--revised-qm-must-not-affect-the-anchormulti-analyzer-work-now-properly-fixing-qm-is-a-separate-later-concern) L631:678
  - [A2 — Phase 1 should be a uniform analyzer loop; anchor resolution belongs only in Phase 2 (re: §3.4)](#a2--phase-1-should-be-a-uniform-analyzer-loop-anchor-resolution-belongs-only-in-phase-2-re-34) L679:701
  - [A3 — QM's ConfigMap-presence override should not exist (re: §2) — deferred](#a3--qms-configmap-presence-override-should-not-exist-re-2--deferred) L702:712
  - [A4 — Optimizer/limiter selection is wrongly gated on analyzer name (re: §2, §4.1) — real design bug](#a4--optimizerlimiter-selection-is-wrongly-gated-on-analyzer-name-re-2-41--real-design-bug) L713:732
  - [A5 — Three mutually-exclusive code paths (re: §1/§2)](#a5--three-mutually-exclusive-code-paths-re-12) L733:738
  - [A6 — corrected — see revised A1](#a6--corrected--see-revised-a1) L739:752
  - [Comments on §3.1 (saturation-v2)](#comments-on-31-saturation-v2) L753:756
  - [B1 — Is sat-v2 the only analyzer that supports SGLang? — checked: no](#b1--is-sat-v2-the-only-analyzer-that-supports-sglang--checked-no) L757:780
  - [B2 — Role math needs revisiting (re: §3.1) — future discussion, beyond 0.9 scope](#b2--role-math-needs-revisiting-re-31--future-discussion-beyond-09-scope) L781:791
  - [B3 — Variant math needs revisiting (re: §3.1) — future discussion, beyond 0.9 scope](#b3--variant-math-needs-revisiting-re-31--future-discussion-beyond-09-scope) L792:802
  - [B4 — Final assembly should be per scaled object (re: §3.1) — future discussion, beyond 0.9 scope](#b4--final-assembly-should-be-per-scaled-object-re-31--future-discussion-beyond-09-scope) L803:810
  - [Comments on §3.2 (throughput analyzer / TA)](#comments-on-32-throughput-analyzer--ta) L811:816
  - [C1 — Why does changing TA registration require a controller restart? (re: §3.2) — revisit later](#c1--why-does-changing-ta-registration-require-a-controller-restart-re-32--revisit-later) L817:830
  - [C2 — Shape-change tolerance / ready-gate values (re: §3.2 stages 2, 4) — beyond scope, two distinct asks](#c2--shape-change-tolerance--ready-gate-values-re-32-stages-2-4--beyond-scope-two-distinct-asks) L831:843
  - [C3 — GPS-mismatch: document the reason (re: §3.2 stage 6) — beyond scope, precise mechanism below](#c3--gps-mismatch-document-the-reason-re-32-stage-6--beyond-scope-precise-mechanism-below) L844:859
  - [C4 — TA's final assembly gets the same per-scaled-object critique as sat-v2's (re: §3.2 stage 8)](#c4--tas-final-assembly-gets-the-same-per-scaled-object-critique-as-sat-v2s-re-32-stage-8) L860:868
  - [C5 — Calibration-state persistence should be one common mechanism, not per-analyzer (re: §3.2 "Calibration-state storage")](#c5--calibration-state-persistence-should-be-one-common-mechanism-not-per-analyzer-re-32-calibration-state-storage) L869:880
  - [C6 — Issue #1261 (`anyEPP`/`anyGPSMismatch` discarded, §3.2 stage 7) needs deeper investigation — understand the risk in current code](#c6--issue-1261-anyeppanygpsmismatch-discarded-32-stage-7-needs-deeper-investigation--understand-the-risk-in-current-code) L881:896
  - [D1 — Does scale-from-zero work with TA alone? — checked: no, it depends entirely on sat-v2](#d1--does-scale-from-zero-work-with-ta-alone--checked-no-it-depends-entirely-on-sat-v2) L897:927
  - [Comments on §3.4 (engine orchestration — assembling the ballot)](#comments-on-34-engine-orchestration--assembling-the-ballot) L928:931
  - [E1 — `baseResult`: what breaks if sat is never called? "Every analyzer should have base." (re: §3.4 stage 1)](#e1--baseresult-what-breaks-if-sat-is-never-called-every-analyzer-should-have-base-re-34-stage-1) L932:942
  - [E2 — Ballot literal: do we need to treat sat differently at packaging time? (re: §3.4 stage 2)](#e2--ballot-literal-do-we-need-to-treat-sat-differently-at-packaging-time-re-34-stage-2) L943:952
  - [E3 — Analyzer loop: unclear gate, failure handling, and the universal/local threshold question (re: §3.4 stage 3)](#e3--analyzer-loop-unclear-gate-failure-handling-and-the-universallocal-threshold-question-re-34-stage-3) L953:981
  - [E4 — Liveness needs to be uniform, for every analyzer (re: §3.4 stage 5)](#e4--liveness-needs-to-be-uniform-for-every-analyzer-re-34-stage-5) L982:996
  - [E5 — Packaging: current design is BROKEN relative to intent — no anchor yet, and binding should be positional, not name-based (re: §3.4 stage 6)](#e5--packaging-current-design-is-broken-relative-to-intent--no-anchor-yet-and-binding-should-be-positional-not-name-based-re-34-stage-6) L997:1031
  - [E6 — 0.9 wiring requirement: must support `[sat]`, `[TA]`, `[sat, TA]` (re: §3.4, cross-cutting)](#e6--09-wiring-requirement-must-support-sat-ta-sat-ta-re-34-cross-cutting) L1032:1051
  - [F1 — CORRECTION to E1: "base" needs a definition; my conclusion overreached](#f1--correction-to-e1-base-needs-a-definition-my-conclusion-overreached) L1052:1079
  - [F2 — CORRECTION to E3: the universal/local threshold mechanism is simple and already matches your description](#f2--correction-to-e3-the-universallocal-threshold-mechanism-is-simple-and-already-matches-your-description) L1080:1099
  - [F3 — Scale-from-zero: SUPERSEDED — see `planning/scale-from-to-zero-analysis.md`](#f3--scale-from-zero-superseded--see-planningscale-from-to-zero-analysismd) L1100:1114
  - [F4 — Scale-to-zero: SUPERSEDED — see `planning/scale-from-to-zero-analysis.md`](#f4--scale-to-zero-superseded--see-planningscale-from-to-zero-analysismd) L1115:1125
  - [Comments on §4.2 / §4.3 (binding-entry resolution, role-state init)](#comments-on-42--43-binding-entry-resolution-role-state-init) L1126:1129
  - [G1 — §4.2 IS the main locus of the anchor-refactor change; functional spec for the new function (re: §4.2)](#g1--42-is-the-main-locus-of-the-anchor-refactor-change-functional-spec-for-the-new-function-re-42) L1130:1160
  - [G2 — §4.3: binding-analyzer identification is independent of role-state init — checked, confirmed safe](#g2--43-binding-analyzer-identification-is-independent-of-role-state-init--checked-confirmed-safe) L1161:1184
  - [H1 — Confirmed: scale-from/to-zero is untouched by the anchor/binding mechanism, and needs its own separate fix](#h1--confirmed-scale-fromto-zero-is-untouched-by-the-anchorbinding-mechanism-and-needs-its-own-separate-fix) L1185:1204
  - [H2 — Correcting confusion: "ballot[0]" was not proposing a reserved anchor slot separate from the real ballot (re: E5, G1)](#h2--correcting-confusion-ballot0-was-not-proposing-a-reserved-anchor-slot-separate-from-the-real-ballot-re-e5-g1) L1205:1225
  - [H3 — The real concern behind the §4.3 question: what does "binding analyzer" mean once role exists? (re: §4.2/§4.3, ties directly to B2/B3)](#h3--the-real-concern-behind-the-43-question-what-does-binding-analyzer-mean-once-role-exists-re-4243-ties-directly-to-b2b3) L1226:1262
  - [Comments on §4.5 / §4.6 (scale-down core loop, rescale pre-pass)](#comments-on-45--46-scale-down-core-loop-rescale-pre-pass) L1263:1266
  - [I1 — §4.5 NIT: two distinct gates, not one (re: §4.5)](#i1--45-nit-two-distinct-gates-not-one-re-45) L1267:1291
  - [I2 — §4.5 "remove count": confirmed safe against rescale, for a stronger reason than ordering (re: §4.5, §4.6)](#i2--45-remove-count-confirmed-safe-against-rescale-for-a-stronger-reason-than-ordering-re-45-46) L1292:1303
  - [I3 — §4.6: replica count per accelerator type is derived from `TotalDemand`, not `RequiredCapacity` (re: §4.6)](#i3--46-replica-count-per-accelerator-type-is-derived-from-totaldemand-not-requiredcapacity-re-46) L1304:1319
  - [I4 — CORRECTED: rescale must read from the merged anchor, not from a raw analyzer's own result (re: §4.6)](#i4--corrected-rescale-must-read-from-the-merged-anchor-not-from-a-raw-analyzers-own-result-re-46) L1320:1350
  - [I5 — CORRECTED: the failure mode only exists if a read site bypasses the anchor merge (re: §4.6, ties to E1, I4)](#i5--corrected-the-failure-mode-only-exists-if-a-read-site-bypasses-the-anchor-merge-re-46-ties-to-e1-i4) L1351:1380
  - [I6 — §4.6: role accounting confirmed — already model-level-binding, role-aware-reading (re: §4.6, ties to H3)](#i6--46-role-accounting-confirmed--already-model-level-binding-role-aware-reading-re-46-ties-to-h3) L1381:1391
  - [I7 — Scope note](#i7--scope-note) L1392:1401
  - [Comments on §5 / §6 / §7](#comments-on-5--6--7) L1402:1405
  - [K1 — QM is conceptually closer to a second V1 than to "another analyzer" (re: §6, confirms A1)](#k1--qm-is-conceptually-closer-to-a-second-v1-than-to-another-analyzer-re-6-confirms-a1) L1406:1418

## §0 Orientation — the big picture

Three analyzer implementations exist in the codebase:

| Analyzer | Package | Enablement | Runs today in practice |
|---|---|---|---|
| **saturation-v2 (sat-v2)** | `internal/engines/analyzers/saturation_v2` | Always, unconditionally, on the V2 path | Yes — every model, every cycle |
| **throughput (TA)** | `internal/engines/analyzers/throughput` | Registered at startup only if configured (`cmd/main.go:504-513`); per-model opt-in via `effectiveEnabled` | Yes, where configured |
| **queueing-model (QM)** | `internal/engines/analyzers/queueingmodel` | Presence-gated on a `wva-queueing-model-config` ConfigMap | No — not referenced by any shipped kustomization/Helm default; opt-in manifest only |

**The one fact that reframes everything else:** these three do **not** all feed one combined
decision. `engine.go`'s top-level dispatch (§2) picks **exactly one** of three mutually exclusive
modes per reconcile cycle — V1, V2, or QM. QM is not "sat-v2 + TA + QM combined"; it is a
completely separate code path that runs *instead of* V2 whenever its ConfigMap is present, sharing
only two helper functions with V2 (`prepareModelData`, `applyScaleToZeroEnforcement`) and
otherwise duplicating (with different behavior) everything else — its own request-builder, no
threshold recalibration, no liveness tracking, always-`nil` GPU constraints. So "multi-analyzer" in
the sense of *N analyzer results feeding one decision* today means, concretely, **sat-v2 + TA
under the V2 path** — QM is a parallel, effectively-unused third mode.

Within the V2 path, the flow is two phases:

- **Phase 1 — Generation** (§3): each enabled analyzer independently computes a
  `domain.AnalyzerResult` for a model, with zero awareness of any other analyzer. Sat-v2 always
  runs; TA runs if registered+configured. Their two results are packaged into an ordered slice,
  `[]pipeline.NamedAnalyzerResult` — the "ballot" — with sat-v2's entry always first.
- **Phase 2 — Optimizer consumption** (§4): the optimizer receives the ballot (all analyzers'
  results for one model) and produces `[]domain.VariantDecision`. This is where the split noted in
  the headline finding lives: **identity/metadata is single-sourced** from whichever ballot entry
  is named `"saturation"` (the "binding entry," via `saturationEntry`), but **the actual
  replica-count math already iterates every entry in the ballot** — this is the existing combine
  engine (§5).

Rescale (fill/reclaim GPU redistribution across models) turned out, on tracing, to be a **pre-pass
inside Phase 2's `GreedyByScoreOptimizer.Optimize()`**, not an independent third phase — it mutates
the same GPU-budget maps the rest of that call reads, and the engine never touches it separately.
It's documented as §4.6, inside Phase 2, not as its own top-level phase.

[↑ TOC](#toc)

---

## §1 Call-stack sketch

```
Engine.optimize()                                        [engine.go:433-559]
  │
  ├─ resolve analyzerName + enableLimiter from saturation-scaling config   [engine.go:507-512]
  ├─ if QM ConfigMap has a "default" entry → analyzerName = "queueing-model" (OVERRIDES)  [:523-525]
  ├─ select e.optimizer: GreedyByScoreOptimizer (enableLimiter) or CostAwareOptimizer      [:527-540]
  │
  └─ switch analyzerName:                                                  [engine.go:552-558]
       │
       ├─ case "saturation" (V2, default) ──► optimizeV2(...)              [engine.go:951-1038]
       │     for each (model, namespace) group:
       │       ├─ prepareModelData(...)                    [shared helper, engine.go:1477-1556]
       │       └─ collectV2ModelRequest(...)                              [engine_v2.go:581-615]
       │             └─ runAnalyzersAndScore(...)  ◄── PHASE 1            [engine_v2.go:96-178]
       │                   ├─ baseResult := saturationV2Analyzer.Analyze()  (always)
       │                   ├─ applyUniversalThreshold(baseResult)
       │                   ├─ ballot[0] = {Name:"saturation", Result:baseResult, ...}
       │                   └─ for entry in analyzersSnapshot (e.g. throughput):
       │                         if entry.name=="saturation" → skip (belt-and-suspenders)
       │                         if effectiveEnabled(entry.name, config):
       │                            result := entry.Analyze()
       │                            applyUniversalThreshold(result)
       │                            ballot[i] = {Name: entry.name, Result: result, ...}
       │                   updateLivenessAndSetLive(ballot)   (sets .Live on every entry)
       │       optimizer.Optimize(ctx, allRequests, constraints)  ◄── PHASE 2
       │             (GreedyByScoreOptimizer.Optimize also runs applyRescale as a pre-pass, §4.6)
       │       applyScaleToZeroEnforcement(...)
       │       enrichDecisionsWithKvTokenData(...)
       │
       ├─ case "queueing-model" (QM) ──► optimizeQueueingModel(...)   [engine_queueing_model.go:23-123]
       │     for each (model) group:
       │       ├─ prepareModelData(...)                        (shared with V2)
       │       ├─ runQueueingModelAnalysis(...) → QM.Analyze()  ◄── separate Phase-1 equivalent
       │       └─ requests[i] = {AnalyzerResults: [{Name:"saturation", Result:qmResult,
       │                                             Score:1.0, Live:true (hardcoded)}]}
       │     optimizer.Optimize(ctx, requests, nil)   ← constraints ALWAYS nil, even if limiter on
       │     applyScaleToZeroEnforcement(...)          (no enrichment stage)
       │
       └─ case V1 (legacy) ──► optimizeV1(...)   [not traced in this pass — out of scope]
```

[↑ TOC](#toc)

---

## §2 Dispatch — V1 / V2 / QM are mutually exclusive

| Data produced | Producing code / loop | Gates | Logic |
|---|---|---|---|
| `analyzerName string`, `enableLimiter bool` | `Engine.optimize`, `engine.go:507-512`; reads `SaturationScalingConfig` `"default"` entry | none yet | `cfg.ApplyDefaults(); analyzerName = cfg.GetAnalyzerName(); enableLimiter = cfg.EnableLimiter` |
| override of `analyzerName` | `engine.go:509-510, 523-525` | `qmConfigMap := e.Config.QMAnalyzerConfig(); _, hasQMAnalyzerConfig := qmConfigMap["default"]` | if the QM ConfigMap (`wva-queueing-model-config`) has a `"default"` key that parsed+validated, **unconditionally overrides** `analyzerName` to `"queueing-model"` — regardless of what the saturation config said |
| `e.optimizer` (CostAware or GreedyByScore) | `engine.go:527-540` | `analyzerName ∈ {"saturation","queueing-model"}` then branch on `enableLimiter` | selects the optimizer implementation; `enableLimiter` defaults `false` (`saturation_scaling.go:34`) ⇒ CostAware is the practical default |
| dispatch to one of 3 code paths | `switch analyzerName` — `engine.go:552-558` | exhaustive match | `optimizeV2` / `optimizeQueueingModel` / `optimizeV1` — **exactly one runs per cycle**, never a blend |

**How the QM ConfigMap gets populated.** `parseQMAnalyzerConfig` (`internal/controller/configmap_helpers.go:77-98`)
YAML-unmarshals each key of the `wva-queueing-model-config` ConfigMap into a
`domain.QueueingModelScalingConfig` at controller startup (`configmap_bootstrap.go:121-144`) or on
watch events (`configmap_reconciler.go:257-271`); an absent ConfigMap leaves `hasQMAnalyzerConfig`
false and the saturation config's own `analyzerName` (V2, in every shipped default) takes over.
**No shipped kustomization/Helm/install-script default applies this ConfigMap** — `deploy/configmap-queueing-model.yaml`
is a standalone opt-in manifest whose own header comment says "Delete this ConfigMap to fall back
to V1/V2." QM is therefore off in every default deployment.

A second, per-cycle gate can still override the *optimizer* choice even when V2/QM select
GreedyByScore: `selectV2Optimizer` (`engine.go:883-921`) falls back to `CostAwareOptimizer` if no
GPU-constraint provider is available that cycle (GreedyByScore treats absent constraints as
deny-all, not unlimited — so this fallback exists to avoid silently blocking all scale-up).

[↑ TOC](#toc)

---

## §3 Phase 1 — Generation

Each analyzer below runs with **zero knowledge of any other analyzer** — `Analyze()` takes a
`domain.AnalyzerInput` (raw metrics + variant states + that analyzer's own config) and returns a
`*domain.AnalyzerResult`. All cross-analyzer awareness happens later, in §3.4/§4.

### §3.1 Saturation-v2 (sat-v2)

Package: `internal/engines/analyzers/saturation_v2`. Entry: `Analyze()`, `analyzer.go:64-140`.

**Distinguishing responsibility.** The only analyzer with a **token-unit, two-constraint capacity
model**: for every replica it derives a memory-bound ceiling `k1 = TotalKvCapacityTokens ×
KvCacheThreshold` and a compute-bound ceiling `k2` via a 4-tier priority chain (live-observed →
rolling-average-historical → analytically-derived from parsed vLLM/SGLang engine flags → `k1`
fallback), takes `effectiveCapacity = min(k1,k2)`, and tags every value with a provenance label
(`P1-obs`…`P4-k1`, `P0-store`, `no-data`) that survives into `VariantCapacity.Reason`. It is the
only analyzer that maintains a **persistent, cross-namespace `CapacityKnowledgeStore`**, populated
by parsing container `Command`/`Args`/env for vLLM/SGLang flags, used to estimate capacity for
variants with zero live replicas (scale-from-zero) by borrowing a hardware/engine-config-compatible
sibling's numbers.

| Stage | Data produced | Producing code / loop | Key gates | Logic |
|---|---|---|---|---|
| 0. Capacity-store pre-population *(runs earlier, in the calling engine — precondition)* | `CapacityRecord` per variant in `*CapacityKnowledgeStore` | `Engine.runV2AnalysisOnly` → `LoadFromScaleTarget`, `capacity_store.go:88-131`; parses container args via `deployment_parser.go`/`sglang_parser.go` | `scaleTarget==nil` skip; existing live-learned record not overwritten | Parses vLLM/SGLang flags into `EngineParams`; resolves `EffectiveMaxBatchedTokens` (chunked-prefill defaults) |
| 1. Per-replica capacity — main path | `ReplicaCapacity{k1,k2,EffectiveCapacity,IsSaturated,ReplicaDemand}` | `computeReplicaCapacity`, `analyzer.go:147-221`; loop over `input.ReplicaMetrics` | branch gate `TotalKvCapacityTokens<=0` → fallback path instead (row 2) | `demand = TokensInUse + waitingQueueDemand` (role-aware: prefill charges input tokens only, decode/both charges input+output); `k1 = TotalKvCapacityTokens×threshold`; `k2` via the 4-tier chain (§ full detail below); `effectiveCapacity=min(k1,k2)` |
| 2. Per-replica capacity — fallback path | `ReplicaCapacity` (synthetic units) | `computeReplicaCapacityFallback`, `analyzer.go:229-281` | `capacityStore` record missing/≤0 → drop replica entirely | store-derived `effectiveCapacity`, coarse KV-usage-fraction demand estimate; always tagged `k2SrcFallback` |
| 3. Per-variant aggregation | `perReplicaCapacity, totalDemand, replicaCount, capacityLabel` per variant | `aggregateByVariant`, `analyzer.go:339-453`; loop over `variantStates` | **P0-P4 priority chain**: live replicas this cycle → median capacity; else own stored record → `estimateStoredCapacity`; else compatible sibling's record → borrow; else `no-data` (label ties directly into the engine's liveness gate, `pipeline.ResultIsInformative`) | `replicaCount` = live engine instances (DP ranks), not pods; `totalCapacity = replicaCount×perReplicaCapacity`; `utilization = totalDemand/totalCapacity` |
| 4. Model-level supply/demand + scheduler-queue demand | `TotalSupply, TotalAnticipatedSupply, TotalDemand, Utilization` | `aggregation.SumTotalSupply/SumTotalDemand` + `estimateSchedulerQueueDemand`, `analyzer.go:99-116, 750-794` | `SchedulerQueue==nil` → 0 added | `TotalAnticipatedSupply` counts `PendingReplicas` too (suppresses `RequiredCapacity` while a scale-up is already in flight); queue demand = `max(bytes-derived, count-derived)` input estimate × (1−cache-hit-rate) + output estimate, no cache discount on output |
| 5. Per-role aggregation (P/D) | `map[string]domain.RoleCapacity` or `nil` | `aggregateByRole`, `analyzer.go:467-504` | short-circuits to `nil` entirely if no variant has a role other than `""`/`"both"` | sums supply/demand per role; **`RequiredCapacity`/`SpareCapacity` deliberately left zero** — computed later by the engine, not here |
| 6. Final assembly | `domain.AnalyzerResult{AnalyzerName:"saturation-token-based", VariantCapacities, TotalSupply, TotalDemand, TotalAnticipatedSupply, Utilization, RoleCapacities}` | `Analyze`, `analyzer.go:126-139` | none | straight struct literal from stages 1-5; `RequiredCapacity`/`SpareCapacity` are the engine's job (§3.4), not sat-v2's |

**k2's 4-tier priority chain** (`computeK2`, `analyzer.go:290-335`) — the single most important
gate chain in this analyzer, worth calling out on its own: (1) **Observed** — if the local queue is
saturated (`queueLen ≥ 5`) and tokens are in use, treat currently-resident tokens as the observed
ceiling and feed a 10-sample rolling average keyed by `modelID|accelerator|gpuCount|outputBucket`;
(2) **Historical** — reuse that rolling average if populated; (3) **Derived** — analytically from
parsed engine flags (`N_steady = min(B·O/(I+O), S)`, `k2 = N_steady·(I+O/2)`); (4) **Fallback** —
`k1` (memory-bound only, no compute signal at all).

**SGLang support is not sat-v2-exclusive.** Metric *collection* supports SGLang for all three
analyzers (`internal/collector/registration/` has a `registerSGLang*Queries` function for
saturation, throughput, and queueing-model alike) — they all consume the same
engine-normalized `domain.ReplicaMetrics` fields regardless of engine. What genuinely is
sat-v2-exclusive is stage 0 above: parsing raw container `Command`/`Args` (deployment-spec
introspection, not metric collection) to bootstrap the `CapacityKnowledgeStore` — a different
capability, needed for scale-from-zero estimation, that TA and QM never needed because they only
consume already-normalized metrics.

[↑ TOC](#toc)

### §3.2 Throughput analyzer (TA)

Package: `internal/engines/analyzers/throughput`. Entry: `Analyze()`, `analyzer.go:204-452`, which
calls `Observe()` (`analyzer.go:77-166`) first.

**Registration gate (frozen for process lifetime).** TA is only ever registered at all if
`cfg.ThroughputAnalyzerEnabled()` at controller startup (`cmd/main.go:391,504-511`) — checks that
some saturation-config entry lists a `throughput` analyzer with `Enabled` nil-or-true. Registration
never changes after `StartOptimizeLoop` starts.

**Distinguishing responsibility.** The only analyzer that fits a **regression-based physical
latency model** — `ITL(k) = A·k + B` via OLS, converting KV-utilization signal into a tokens/sec
throughput supply/demand pair — with a persistent, in-memory, per-variant rolling observation
window and a GPS-cross-check that forces self-recalibration after persistent model/observation
disagreement.

| Stage | Data produced | Producing code / loop | Key gates | Logic |
|---|---|---|---|---|
| 1. `Observe` — sanity + shape tracking | `state.shapeTracker`, `state.observationWindow` mutated per variant | `Observe`, `analyzer.go:77-166`; `CheckModelMetrics`/`checkReplicaMetrics`, `sanity.go:18-80` | **staleness gate**: `Metadata.FreshnessStatus=="stale"` excludes a replica; `SanityIssueNoReplicas` skips the whole variant this cycle; healthy-filter (`filterHealthyForShape`) excludes any replica with *any* sanity issue from shape/window updates | computes `RequestRate`-weighted mean `AvgInputTokens/AvgOutputTokens/PrefixCacheHitRate`; `ILeff = IL×(1−hitRate)`, `KVreq = ILeff + OL/2` |
| 2. Shape-change → window reset | `WorkloadShape`; possible `observationWindow.Clear()` | `ShapeTracker.Observe`, `shape_tracker.go:30-42` | `changed = !next.Within(current, 0.20)` (≥20% swing in IL or OL) | a shape change clears the rolling ITL window and resets the GPS-mismatch counter — ITL(k) is workload-shape-dependent |
| 3. Rolling-window observation collection | `[]ITLObservation` (FIFO, max 20, max age 30 min) | `ObservationWindow.Add/Prune`, `observation_window.go:41-63` | drops `k` outside `[0.15,0.85]`, drops `itl<=0`/NaN | one `(k*, ITL)` sample per healthy replica per cycle |
| 4. ITL-model resolution — Tier 1 (OLS) → Tier 2 (B-pinned) | `ITLModel{A,B}`, `state.lastFittedB` | `resolveITLModel`, `analyzer.go:529-578`; `FitITLModel`, `itl_model.go:66-93` | **Ready-gate**: `len(observations)≥10 AND KSpread≥0.30`; degenerate-slope/NaN/non-positive-at-`k_sat` validity checks (`validITLModel`); both tiers can fail → variant skipped this cycle | Tier 1 closed-form OLS over the window; Tier 2 constrained least-squares with `B` pinned to the last fitted value (or a `0.006s` default if never fitted) |
| 5. Supply/demand computation | `supply, perReplicaSupply, nKV`; `demand` (3-tier fallback) | `computeVariantSupply`, `analyzer.go:679-695`; `computeDemand`/`computeLocalDemand`, `:598-656` | `itlSat<=0` skip; supply `==0` skip; demand priority: EPP arrival-rate → engine-completion-rate → k*-based local (scale-up-only, no EPP needed) | `N_dec_sat = k_sat×KV_max/KVreq`; `μ_dec_sat = N_dec_sat/ITL(k_sat)` |
| 6. GPS-mismatch verification | `anyGPSMismatch`; `state.consecutiveGPSMismatches` | `checkVariantGPSMismatch`, `analyzer.go:769-849` | mismatch fires at `>15%` residual between model-predicted and observed `GenerationTokenRate`; **3 consecutive mismatched cycles force `observationWindow.Clear()`** | self-correcting recalibration trigger, independent of shape change. **Both sides of the comparison are evaluated at the *same*, currently-observed `k`** (`model.ITLAt(m.KvUsageInstant)` vs. the also-current `m.GenerationTokenRate`) — not current-k vs. `k_sat`. The reason this same-k check matters: the identical fitted model is later evaluated at `k_sat` (stage 5's `itlSat`) for capacity, a point usually far from live traffic and never directly checkable — a model that already disagrees with ground truth where it *can* be checked cannot be trusted at the point that actually drives capacity |
| 7. Model-level arrival-driven demand | `totalDemand` (feeds the model-level `AnalyzerResult`, not the per-variant `VariantCapacity`) | `Analyze`, `analyzer.go:401-427` | **gated on `nDecodeVariants>0`** — zero if no non-prefill variant resolved a model this cycle; `SchedulerQueue==nil` → queue term is 0 | `arrivalDecodeDemand = ArrivalRate × avgOL`; `queueDemand` derived so admitted queue wait ≤ `2×ITL(k_sat)×avgOL` |
| 8. Final assembly | `domain.VariantCapacity{..., AcceleratorName:"", Cost:0}`; `domain.AnalyzerResult{AnalyzerName:"throughput", ...}` | `Analyze`, `analyzer.go:362-382, 440-451` | none | **`AcceleratorName`/`Cost` are left at zero value** — TA reads `rm.AcceleratorName`/`rm.Cost` from raw metrics but never copies them into its own result. This is the concrete fact behind "TA needs the anchor for accelerator/cost" |

**Calibration persistence.** All state lives in-process memory on the single `*ThroughputAnalyzer`
instance (`variantStates map[string]*variantState`, keyed by `namespace\x00modelID\x00variantName`,
guarded by one `sync.Mutex`). **Nothing survives a controller restart** — a fresh process starts
every variant at Tier 2 with the default baseline `B`. Idle variants (>60 min unobserved) are
garbage-collected.

**Documented non-gate (issue #1261).** `anyEPP`/`anyGPSMismatch` are fully computed (Steps 1/6
above) but currently **discarded** (`analyzer.go:437-438`, assigned to `_`) — a prior
`SpareCapacity`-suppression gate on these signals was removed because it risked an incorrect
scale-down when a queue metric was merely missing; restoring a different gate is tracked as #1261,
pending a per-analyzer status-opt-out addition to the engine contract.

**Scale-from-zero limitation.** TA's per-variant loop (stage 8, and the `Observe`/`Analyze` loops
generally) is keyed off `groupByVariant(input.ReplicaMetrics)` — a variant with zero live replicas
contributes zero `ReplicaMetrics` entries and is never visited at all, in either method. TA's own
authors document the gap verbatim (`analyzer.go:524-526`): a future tier-3 knowledge-store path for
scale-from-zero "will be added once `Analyze()` is extended to iterate variants with state but no
current replica metrics." Today, any scale-from-zero capability for a variant TA alone can see
comes from elsewhere — see `planning/scale-from-to-zero-analysis.md` for the full mechanism (a
separate, independent engine that doesn't consult TA, sat-v2, or any analyzer at all for the
*full*-zero case; sat-v2's `CapacityKnowledgeStore`, §3.1 stage 0, covers the *partial*-zero case
where a sibling variant of the same model has live replicas).

[↑ TOC](#toc)

### §3.3 Queueing-model analyzer (QM)

Package: `internal/engines/analyzers/queueingmodel`. Runs only inside `optimizeQueueingModel`
(§2), never through the shared `runAnalyzersAndScore` loop that sat-v2/TA use.

| Stage | Data produced | Producing code / loop | Key gates | Logic |
|---|---|---|---|---|
| 1. Per-model config resolution | per-model `QMConfig` | `buildQMConfig`, `engine_queueing_model.go:160-215` | `"default"` entry's `sloMultiplier`/`tuningEnabled` overridable per-model by name+namespace match | — |
| 2. `Analyze()` | `domain.AnalyzerResult{RequiredCapacity, SpareCapacity, ...}` — **QM sets these directly**, unlike sat-v2/TA | `queueingmodel/analyzer.go:92-150` | `SLO target == nil` → error (skips model); `len(variantCapacities)==0` → error | optional Kalman-filter online tuning of `alpha/beta/gamma`; builds a `QueueAnalyzer` and calls `.Size(targetPerf)` for max sustainable rate; `desiredNumReplicas = ceil(arrivalRate/maxRequestRate)`; `RequiredCapacity = max(0, TotalDemand−TotalSupply)` — a **raw difference**, not the engine's threshold-divided formula used elsewhere |
| 3. Ballot construction | single-entry `[]pipeline.NamedAnalyzerResult{{Name:"saturation", ..., Live:true}}` | `engine_queueing_model.go:77-95` | none | **misnamed** `"saturation"` even though a different analyzer produced it (in-line comment acknowledges this, `:81`); `Live` **hardcoded true** — QM never runs through `updateLivenessAndSetLive`, so it's exempt from staleness-veto tracking rather than participating in it; no `applyUniversalThreshold` call at all |
| 4. Optimize call | `[]domain.VariantDecision` | `engine_queueing_model.go:103` | `constraints` passed as `nil` **unconditionally**, even if the limiter/GreedyByScore was selected | same `optimizer.Optimize` interface call as V2, but GPU-budget-blind |

QM shares only `prepareModelData` (metrics prep) and `applyScaleToZeroEnforcement` (Stage-3
enforcer) with the V2 path — no threshold recalibration, no liveness tracking, no
`selectV2Optimizer` GPU-constraint resolution, no KV-token enrichment stage. See §6 for the
one-paragraph summary.

[↑ TOC](#toc)

### §3.4 Engine orchestration — assembling the ballot

This is the connective tissue between "each analyzer ran" and "the optimizer gets a request" —
the actual multi-analyzer *generation-side* mechanism, all inside `internal/engines/saturation/engine_v2.go`.

| Stage | Data produced | Producing code / loop | Gates | Logic |
|---|---|---|---|---|
| 1. `baseResult` (always sat-v2) | `*domain.AnalyzerResult` | `runV2AnalysisOnly`, `engine_v2.go:25-77`, called from `runAnalyzersAndScore:110-111` | none — unconditional ("always needed for PerReplicaCapacity," `:109`) | calls `saturationV2Analyzer.Analyze()`; immediately calibrated via `applyUniversalThreshold(baseResult, satUp, satDown)`, `:118-119` |
| 2. Ballot literal — sat-v2 entry | `NamedAnalyzerResult{Name:"saturation", Result:baseResult, Score, Remaining:baseResult.RequiredCapacity, Spare:baseResult.SpareCapacity, ScaleUpThreshold, ScaleDownBoundary}` | `engine_v2.go:140-148` | none | hand-written literal, always index 0 |
| 3. Non-saturation analyzer loop | additional `NamedAnalyzerResult` entries | `for entry := range e.analyzersSnapshot`, `engine_v2.go:149-171` | `entry.name=="saturation"` → skip (belt-and-suspenders, sat-v2 is never actually placed in `analyzersSnapshot` in practice, `:150-152`); `effectiveEnabled(entry.name, config)` → participation gate, `:153,378-396` (opt-in: absent from `cfg.Analyzers` ⇒ excluded — prevents an unconfigured registered analyzer from silently vetoing scale-down with `SpareCapacity=0`); `runRegisteredAnalyzer` recovers panics/errors and returns `nil` on failure, `:156,402-428` | per-analyzer threshold resolution (`resolveThresholds`, override-over-global) + `applyUniversalThreshold` calibration, then append |
| 4. Scoring | `.Score` field per entry | `scoreForAnalyzer`, `engine_v2.go:356-366` | linear scan for a config entry matching by name | config's `Score` if `>0`, else default `1.0` — a pure weight, does not gate participation |
| 5. Liveness | `.Live` field on **every** entry (no name exemption) | `updateLivenessAndSetLive`, `engine_v2.go:172, 187-229` | staleness-window check against `e.lastGoodAnalysis` | this is what §4.3/§4.5's scale-down veto/min logic actually reads |
| 6. Packaging | `*pipeline.ModelScalingRequest{ModelID, Namespace, AnalyzerResults, VariantStates, Priority, Disaggregated}` | `collectV2ModelRequest`, `engine_v2.go:581-615` | `Disaggregated` set true if any variant's `Role∉{"","both"}`, `:600-604` | pure packaging — no further per-analyzer combination happens here |

**In current production wiring**, the only analyzer that ever joins sat-v2 in step 3's loop is
`throughput` (the only one `cmd/main.go` ever registers) — so "the ballot" is, in practice today,
at most a 2-entry slice: `[sat-v2, TA]` or `[sat-v2]` alone.

**Stage 1's failure mode is uniquely catastrophic relative to every other analyzer.** "Unconditional"
above describes participation, not error-handling: if sat-v2's own `Analyze()` errors (e.g. the
config type-assertion at `saturation_v2/analyzer.go:65-68`), `runV2AnalysisOnly` returns the error
and `runAnalyzersAndScore` returns immediately (`engine_v2.go:112-113`) — **before stage 3's loop
ever runs.** TA doesn't just lose its ballot position; it never executes that cycle at all. There is
no panic-recovery wrapper around `runV2AnalysisOnly` — the only `recover()` in this file is inside
`runRegisteredAnalyzer` (stage 3), used only for non-sat analyzers.

[↑ TOC](#toc)

---

## §4 Phase 2 — Optimizer consumption

Both optimizer implementations (`CostAwareOptimizer` — default; `GreedyByScoreOptimizer` — GPU-
constrained "limited mode," selected via `EnableLimiter`) share the helpers described below
(`internal/engines/pipeline/analyzer_helpers.go`, `cost_aware_optimizer.go`). Both consume the same
`pipeline.ModelScalingRequest` shape.

### §4.1 Optimizer selection

See §2 — `EnableLimiter` (default `false`) picks `GreedyByScoreOptimizer` vs `CostAwareOptimizer`;
`selectV2Optimizer` (`engine.go:883-921`) can fall back to CostAware per-cycle if no GPU-constraint
provider is available.

[↑ TOC](#toc)

### §4.2 Binding-entry resolution (`saturationEntry`)

```go
// analyzer_helpers.go:91-98
func saturationEntry(s []NamedAnalyzerResult) *domain.AnalyzerResult {
	for _, e := range s {
		if e.Name == domain.SaturationAnalyzerName {
			return e.Result
		}
	}
	return nil
}
```

| Data produced | Producing code / loop | Gates | Logic |
|---|---|---|---|
| `*domain.AnalyzerResult` (or `nil`) | `saturationEntry`, called once per request at `cost_aware_optimizer.go:48` / `greedy_score_optimizer.go:125,158` | **nil-guard at call site**: `if satEntry == nil { continue }` — the whole model gets **zero decisions** this cycle | linear by-name scan; first (and only) match on the literal name `"saturation"` |

This one function is the entire single-binding mechanism. It is the sole source of `VariantCapacities`
(`Cost`, `AcceleratorName`, `Role`, `PerReplicaCapacity`, `ReplicaCount`) used to build `vcMap`, to
enumerate which variants/roles exist to allocate across, and to populate `AcceleratorName`/`Cost`/
`Utilization`/`RequiredCapacity`/`SpareCapacity` on the final decision (§4.7). The in-code doc
comment (`analyzer_helpers.go:87-90`) already names this a "keeper of per-variant metadata" and
flags a `TODO: remove the sat_v2 special role once all analyzers populate variant metadata" — i.e.
the code's own authors already knew this was the gap, well before the anchor-refactor plan.

[↑ TOC](#toc)

### §4.3 Role-state init — where multi-analyzer data first mixes

`initRoleState(s []NamedAnalyzerResult)` (`analyzer_helpers.go:127-163`) builds `RolePairedState`,
a `[]map[string]float64` indexed `[analyzer-index][role] → remaining demand` — **iterating every
entry in the ballot**, not just the binding one. Disaggregated models pull real per-role
`RequiredCapacity`/`SpareCapacity` from `RoleCapacities`; non-disaggregated models synthesize a
single role `"both"` from the model-level `Remaining`/`Spare` scalars. This table is what every
combine function in §5 actually reduces over.

[↑ TOC](#toc)

### §4.4 Scale-up core loop

`allocateForModelPaired` + a pick function (`costGreedyRolePick` / `fairShareRolePick`),
`analyzer_helpers.go:333-430`. Dispatch gate: `anyRoleNeedsScaleUp(pickerState, roles)` — **any**
analyzer/role pair with positive remaining demand triggers scale-up for the whole model
(`analyzer_helpers.go:213-222`).

| Stage | Data produced | Gates | Logic |
|---|---|---|---|
| Variant pick | candidate variant `v` for a role | `PerReplicaCapacity<=0` skip; `MaxReplicas` headroom check | binding entry's `VariantCapacities`, filtered to the role, sorted cost-efficiency ascending (CostAware) or additionally GPU-budget-capped (GreedyByScore) |
| Bottleneck sizing | `n = min(roleBottleneckReplicas(...), capN)` | joint-commit abort if any role fails to pick (`analyzer_helpers.go:352-354`); progress-stop when `deltaUtil<=0` | `roleBottleneckReplicas` = **max across every analyzer** with nonzero PRC for that variant (§5) |
| Joint P/D coupling | `deltaUtil = min_role(util_role)` | — | the least-satisfied role bounds the whole joint replica commit (no-op for non-disaggregated) |
| Commit | `targets[v] += k`; `pickerState[i][role] -= k×PRC` for every analyzer | clamped to 0 | `applyAllocation` then syncs `s[i].Remaining` down for **every** analyzer entry with that variant |

[↑ TOC](#toc)

### §4.5 Scale-down core loop

`scaleDownRoleIterated` + `scaleDownVariantSet`, `cost_aware_optimizer.go:111-152, 421-452`.
Reached only when no role needs scale-up.

| Stage | Data produced | Gates | Logic |
|---|---|---|---|
| Per-role veto | whether scale-down proceeds at all for a role | `needsScaleDownForRole` — **every live analyzer** must report `RoleSpare[role]>0`; non-live analyzers don't veto; zero live analyzers ⇒ no scale-down | unanimous-live-agreement gate (§5) |
| Variant ordering | most-expensive-first walk order | — | `sortVariantsForScaleDown`: Cost desc, tie-break by score-weighted PRC asc across **all** analyzers, then name |
| Removable count | `n = safeRemovalReplicasForRole(...)` | `minReplicas` floor; "cheapest-at-1" protection (the single cheapest variant isn't zeroed while a pricier sibling still holds replicas) | **min across live analyzers** of `floor(RoleSpare[role]/PRC)` (§5) |
| Commit | `targets[v] -= n`; `RoleSpare[role]` decremented on every analyzer | — | subsequent variants in the same pass see the reduced spare |

[↑ TOC](#toc)

### §4.6 Rescale pre-pass (GreedyByScore only)

**Verdict from tracing: tightly coupled into the same call as the core optimizer — not an
independent post-processing phase.** `applyRescale` is invoked at
`greedy_score_optimizer.go:115`, at the very top of `GreedyByScoreOptimizer.Optimize()`, *before*
the scale-up/scale-down logic above runs. It mutates the same GPU-budget maps
(`available`/`availableByNS`) that the rest of `Optimize()` subsequently reads, and its output
(`handled map[string]bool`) causes the rest of `Optimize()` to `continue`-skip any model it already
decided. `CostAwareOptimizer.Optimize` has no rescale call at all. The engine's own call into the
optimizer (`engine.go:1037`) is a single opaque `optimizer.Optimize(...)` — there is no separate
engine-level rescale stage.

| Gate | Condition |
|---|---|
| Optimizer-type gate | only `GreedyByScoreOptimizer` calls it |
| Enable gate | `o.Rescale.any()` — cluster-wide or per-namespace `EnableRescale` config flag |
| Per-request gates | must have a binding `saturationEntry`; all variants must share one `AcceleratorName` (multi-accelerator models are deferred entirely); must be enabled for that request's scope |
| Contention gate | a group's models must collectively want *more* GPUs than the free budget, else rescale does nothing and defers to the additive scale-up/down path above |

**Logic when triggered:** priority×demand-weighted water-filling (`computeRescaleTargets`) across
contended models sharing an accelerator type, floored at each model's `minReplicas`-derived GPU
count and capped at its `maxReplicas`-derived count; per model, the target is further split across
its own roles (`distributeGPUsByWeight`) and executed via `reclaimRole`/`fillRole`, which reuse the
same `scaleDownVariantSet`/cost-efficiency-sort helpers as §4.4/§4.5. Uses the identical
`saturationEntry` single-binding lookup as everywhere else in Phase 2 — no independent per-analyzer
access.

[↑ TOC](#toc)

### §4.7 Final `VariantDecision` assembly

`buildDecisionsWithOptimizer`, `cost_aware_optimizer.go:243-319` — one decision **per variant**.

| Field | Source |
|---|---|
| `VariantName` | `targets` map key |
| `ModelID`, `Namespace` | the request |
| `AcceleratorName`, `Cost`, `Utilization` | **binding entry's** `VariantCapacities` (`vcMap`) — never a non-saturation analyzer |
| `Role`, `CurrentReplicas`, `MinReplicas`, `MaxReplicas` | `VariantReplicaState` (from the VA spec/status, not any analyzer) |
| `TargetReplicas` | `targets` map — computed by §4.4/§4.5's cross-analyzer combine math |
| `RequiredCapacity`/`SpareCapacity` | binding entry's model-level or per-role (`RoleCapacities[role]`) figures — again binding-entry-only |
| `Action` | `target` vs `CurrentReplicas` comparison, done in this function |

[↑ TOC](#toc)

---

## §5 The core question — where does multi-analyzer combine actually happen today?

**Both — split cleanly along identity vs. quantity.**

**Identity/metadata is single-sourced** (confirmed, `analyzer_helpers.go:87-98`):

```go
// saturationEntry returns the saturation analyzer's result from s, or nil if not present.
// The saturation entry is the keeper of per-variant metadata (Cost, AcceleratorName, Role,
// replica counts) that the optimizer uses for variant selection and GPU accounting.
// TODO: remove the sat_v2 special role once all analyzers populate variant metadata.
```

**Quantity math genuinely combines every analyzer in the ballot already** — confirmed live in
`internal/engines/pipeline/analyzer_helpers.go`:

- **Scale-up bottleneck** (`:181-196`): `roleBottleneckReplicas` = `max_i ceil(state[i][role] / PRC_i[v])`
  across every analyzer `i` with nonzero PRC for that variant — a non-saturation analyzer (TA) can
  force a *larger* scale-up than saturation alone would.
- **Scale-down veto** (`:301-313`): `needsScaleDownForRole` requires **every live analyzer** to
  report `RoleSpare[role] > 0` — one live analyzer with no spare blocks scale-down for that role,
  full stop, with the doc comment explicitly noting "there is no name-based exemption" — saturation
  gets no special treatment here.
- **Scale-down sizing** (`:246-270`): `safeRemovalReplicasForRole` = **min across live analyzers**
  of `floor(RoleSpare[role]/PRC)` — the most conservative analyzer bounds how many replicas can go.
- **Fair-share priority** (GreedyByScore only, `greedy_score_optimizer.go:58-92`): `fairShareValue`
  sums `Score_i × remaining-demand_i` across every analyzer, i.e. the priority metric itself is
  already a weighted multi-analyzer aggregate.

**A stale doc comment currently misdescribes this**, confirmed verbatim at
`internal/engines/saturation/engine.go:208-213`:

> `analyzersSnapshot` is the frozen, registration-ordered view that `runAnalyzersAndScore`
> iterates. Built from `analyzers` in `StartOptimizeLoop` before the goroutine launches. **Saturation
> always runs and drives scaling decisions; other registered analyzers are invoked but their results
> are not consumed yet — combine and per-analyzer threshold logic lands in follow-up PRs.**

This describes an earlier state of the codebase. The combine logic it says is deferred
(`roleBottleneckReplicas`, `needsScaleDownForRole`, `safeRemovalReplicasForRole`, `fairShareValue`)
is present and wired into both optimizers today, and per-analyzer threshold logic
(`resolveThresholds`/`applyUniversalThreshold`, §3.4 stage 3) also already exists. This comment is
a documentation bug independent of any refactor — worth fixing on its own (see §7).

**Confirmed stale by Dean (2026-08-04), with one part specifically called out as still true and
worth keeping:** the structural claim underneath the comment — that the ballot's analyzer results
are populated exclusively by the **engine** (Phase 1) and read exclusively by the **optimizer**
(Phase 2), a strict one-way data flow with no read-back — remains accurate today and isn't part of
what's stale. Only the substantive claim ("other registered analyzers' results are not consumed
yet — combine logic lands in follow-up PRs") is the wrong part; the engine-populates /
optimizer-consumes shape itself should survive whatever the comment eventually gets corrected to.

**What this means for the anchor-refactor motivation:** the actual gap that any binding/anchor
mechanism needs to close is narrow — it's the `saturationEntry` single-source-of-identity function
and its handful of call sites (`vcMap` construction, `variantsForRole`/`rolesOf` enumeration,
`AcceleratorName`/`Cost`/`Utilization` field population on the final decision), not a missing
combine engine. The combine engine for quantity already exists, is already multi-analyzer, and
predates this whole design thread.

[↑ TOC](#toc)

---

## §6 QM in one paragraph

QM is architecturally parallel to, not integrated with, V2's sat-v2+TA combine. It has its own
three-stage optimize function (`optimizeQueueingModel`) dispatched from the same top-level switch
but sharing only `prepareModelData` and `applyScaleToZeroEnforcement` with V2 — no
`applyUniversalThreshold`, no `updateLivenessAndSetLive` (Live is hardcoded `true`), no
`selectV2Optimizer` GPU-constraint resolution (constraints are always `nil`), no KV-token
enrichment. It builds a single-entry ballot misnamed `"saturation"` regardless of which analyzer
actually produced it. It is presence-gated on an opt-in ConfigMap that no shipped deployment
applies, so in practice it does not run anywhere today — any statement about "multi-analyzer" in
production currently means sat-v2 (+ TA where configured), full stop.

[↑ TOC](#toc)

---

## §7 Loose ends / candidate follow-ups

- **Stale doc comment** — `engine.go:208-213` (§5) describes a combine mechanism as deferred to
  "follow-up PRs" that has since landed. A one-line doc-comment fix, independent of any other work;
  raise with whichever role owns `internal/engines/saturation/engine.go` on its current branch (not
  this doc's role to fix — it's a code change).
- **QM's misnamed ballot entry** (`engine_queueing_model.go:81`, §3.3) — cosmetic today (QM's ballot
  is always single-entry, so nothing reads the name to disambiguate), but would misbehave if QM's
  request were ever combined with anything else under the current `saturationEntry`-by-name lookup.
- **TA's `anyEPP`/`anyGPSMismatch` values are discarded in code** (`_ = anyEPP` etc., §3.2) — that's
  an accurate description of the code (`analyzer.go:437-438`), but per Dean: **issue #1261 itself is
  not discarded** — it's actively tracked and, per C6, flagged for deeper investigation into the
  current-code risk, not dropped. Noted here only because the code-level fact surfaced again
  independently during this trace.
- This doc has not yet been adversarially re-verified line-by-line for §3's per-analyzer detail
  (only §5's headline combine functions and the stale comment were independently re-checked). If
  this doc is going to be relied on for future design decisions, a verification pass matching the
  review-doc convention (file:line spot-check by an independent reader) would be worth doing before
  treating it as settled.
- **Actuation path — RESOLVED 2026-08-04 (added after the fact-finding pass).** The question "how do
  the analyzer pipeline's decisions actually reach Kubernetes" is now answered by a direct re-trace
  of `applySaturationDecisions` (`engine.go:1561-1770`), written up in full in
  `scale-from-to-zero-analysis.md` §5. Summary for this doc: the normal engine actuates *indirectly*
  — it iterates every active VA, stages the resolved target into
  `Status.DesiredOptimizedAlloc.{NumReplicas,Accelerator}`, and `act.EmitMetrics` publishes the
  Prometheus replica-scaling metric an external **HPA/KEDA** consumes and acts on (the CRD status is
  persisted separately via the cache→controller patch path). It never patches the scale subresource
  directly — that is scale-from-zero's exclusive mechanism. **Load-bearing corollary reused in A1
  and in the anchor-refactor liveness spec:** a do-nothing tick (no decision for a VA) *preserves*
  the previous target and still emits the metric — it never zeroes anything — so "emit no decisions"
  degrades to "hold", not "scale down." The error path (`emitSafetyNetMetrics`, `:1828+`) gives the
  same never-drop-on-a-bad-tick guarantee.

[↑ TOC](#toc)

---

## §8 Dean's review annotations (live, in progress)

**These are forward-looking decisions/reactions, not part of the descriptive map.** §0-§7 above
describe current code only and should stay that way; this section captures what Dean is deciding
as he reads, kept separate so the two don't get conflated. Not yet folded into any plan — capture
only, at his request, while review is ongoing.

### A1 — REVISED: QM must not affect the anchor/multi-analyzer work now; properly fixing QM is a separate, later concern

*(Original draft below conflated two different things — corrected per Dean, 2026-08-04. Original
text kept struck through for traceability rather than silently rewritten.)*

Two distinct decisions, on two different timelines:

1. **Near-term, NOT deferred, open — needs further discussion.** The mechanism to ensure QM does
   not get broken by, or interfere with, the anchor/multi-analyzer refactor work. At least two
   candidate options (more may exist, not yet chosen between):
   - **(a) Leave QM's path as-is** — keep `optimizeQueueingModel` working independently. Since it
     currently reuses a couple of pieces of shared code with the V2 path (`prepareModelData`,
     `applyScaleToZeroEnforcement` — §3.3), this option likely means giving QM its own private copy
     of whatever shared code the refactor changes, so it keeps working unmodified.
   - **(b) Make it an error to enable QM** under the new code — simpler: if the QM ConfigMap is
     present, refuse to run rather than try to keep the two paths compatible.
2. **Deferred (genuinely out of scope near-term).** Actually fixing QM so it works *properly* as a
   first-class multi-analyzer participant — real design/implementation work, separate from
   decision 1.

~~QM should not continue as a separate, hardcoded, mutually-exclusive path once any anchor/binding
redesign lands — the current `optimizeQueueingModel` "cannot work with new code." Two options on
the table, not yet chosen between: (1) Fail closed — if the QM ConfigMap is present, return an
explicit error rather than letting the old QM path run under a design it wasn't built for (no
silent fallback). (2) Migrate — port whatever is reusable from QM's implementation into the new
unified analyzer tree so QM becomes a first-class participant (like TA) instead of keeping its own
hardcoded `optimizeQueueingModel` path. Either way, the current standalone QM path is heading
toward DEPRECATED.~~

**Fact-finding (2026-08-04) — decision 1's option (b) "make QM an error" is confirmed low-risk on
both fronts it touched:**

- **QM has no functional e2e coverage to break.** A repo-wide search for `queueing-model` /
  `queueingmodel` references in `test/e2e/` returns exactly one hit — a `TODO(cleanup)` *comment* in
  `test/e2e/saturation_analyzer_path_test.go`, not a functional test that exercises the QM path. So
  turning "QM ConfigMap present" into an explicit dispatch error removes no tested behavior; there is
  no e2e scenario asserting QM works today. (Unit-level QM coverage under `internal/` is unaffected —
  this finding is specifically about end-to-end scenarios.)
- **Refusing QM and doing nothing is safe** — a dispatch error that produces no decisions does **not**
  scale anything to zero. Confirmed by re-tracing `applySaturationDecisions` (see §7 loose-ends
  addendum below and `scale-from-to-zero-analysis.md` §5): on a tick where a VA has no decision, the
  engine *preserves* the previous target (`Status.DesiredOptimizedAlloc.NumReplicas` if `>0`, else
  current allocation) and still emits the HPA/KEDA metric "to keep HPA alive" — it never drops the
  emitted target to zero. This is the load-bearing property behind choosing option (b): "refuse QM →
  emit no decisions" degrades to "hold current replicas", not "scale everything down."

[↑ TOC](#toc)

### A2 — Phase 1 should be a uniform analyzer loop; anchor resolution belongs only in Phase 2 (re: §3.4)

Premise checked against this doc's own trace and confirmed: TA's `Analyze()`/`Observe()` take only
`domain.AnalyzerInput` (raw metrics, variant states, its own config) — §3.4 stage 1 confirms
`runAnalyzersAndScore` builds **one shared** `AnalyzerInput` and hands the identical thing to every
analyzer, sat-v2 included. No analyzer reads another analyzer's result to run. So TA does not need
`(a)` (sat-v2's anchor/metadata fields) to execute.

Given that, the sat-v2-first-literal + `entry.name=="saturation" { continue }` skip in
`runAnalyzersAndScore` (§3.4 stages 2-3) is unnecessary complexity carried into Phase 1 for no
functional reason. Proposed restructuring: run **all** enabled analyzers (sat-v2 included) through
one uniform loop with no special-casing in Phase 1. The anchor/binding-entry concept is needed only
in Phase 2 (the optimizer) — resolve it there, on demand, via a single "get Sat Entry" call or a
dedicated helper, rather than building it into the Phase-1 generation loop at all.

*Cross-reference:* this would dissolve the sharpest executability blocker (`M-A`) found in the
coder-executability pass on `ta-anchor-refactor-plan.md` — `runAnalyzersAndScore` has no `req` in
scope, so `req.Anchor = copy(baseResult)` can't be written there as currently drafted. If anchor
resolution moves entirely into Phase 2, that problem doesn't exist — Phase 2 already has `req` and
already has `saturationEntry`.

[↑ TOC](#toc)

### A3 — QM's ConfigMap-presence override should not exist (re: §2) — deferred

Current behavior (§2): a `wva-queueing-model-config` ConfigMap with a `"default"` key
**unconditionally overrides** `analyzerName` to `"queueing-model"`, regardless of what the
saturation config's own `analyzerName` field says (`engine.go:523-525`). Dean's call: this
implicit, presence-triggered override is not wanted — QM selection should require an **explicit**
name in config, not "ConfigMap merely exists ⇒ takes over." Fix is deferred — see A6, the whole QM
path is deferred, so this doesn't block anything right now.

[↑ TOC](#toc)

### A4 — Optimizer/limiter selection is wrongly gated on analyzer name (re: §2, §4.1) — real design bug

§2's dispatch table shows the GreedyByScore-vs-CostAware branch only runs at all when
`analyzerName ∈ {"saturation", "queueing-model"}` (`engine.go:527-540`) — optimizer/limiter
selection is conditioned on which named analyzer is active. Dean's critique: this coupling is
wrong. The limiter is a resource-allocation-constraint concern (GPU budget), not an analyzer
concern — it should be on by default for every real (non-V1) path, or off, independent of which
analyzer(s) produced the ballot.

**Nuance worth keeping distinct from this bug (already established in §5):** once GreedyByScore
*is* selected, its combine math (`roleBottleneckReplicas`, `needsScaleDownForRole`,
`safeRemovalReplicasForRole`, `fairShareValue`) already iterates every entry in the ballot
regardless of analyzer name — that part already "considers all analyzer results" correctly. The
bug is one level up: the *gate deciding whether the limiter mechanism engages at all* is what's
improperly keyed on analyzer name, not the combine math once it's running. Same family of issue as
A2 — special-casing by analyzer identity where the logic doesn't actually need to know which
analyzer it's looking at.

[↑ TOC](#toc)

### A5 — Three mutually-exclusive code paths (re: §1/§2)

Confirmed understood from §1 — no open question, no action.

[↑ TOC](#toc)

### A6 — corrected — see revised A1

~~The entire QM path is deferred (supersedes A1's open fork). Simplifies A1: no need to choose
between "fail closed" and "migrate reusable code" right now — the whole QM path, including A3's
override fix, is deferred wholesale.~~ This was the same over-read as A1's original draft. Only
decision 2 in the revised A1 (properly fixing QM) is deferred; decision 1 (the isolation
mechanism — keeping QM from being broken by the refactor) is open and needs discussion now, not
later. A3 (the ConfigMap-presence override) is a separate, smaller UX cleanup that stays deferred
regardless of which decision-1 option is chosen.

[↑ TOC](#toc)

---

### Comments on §3.1 (saturation-v2)

[↑ TOC](#toc)

### B1 — Is sat-v2 the only analyzer that supports SGLang? — checked: no

Verified directly against `internal/collector/registration/`: **metric collection supports SGLang
for all three analyzers**, not just sat-v2. `saturation.go`, `throughput_analyzer.go`, and
`queueing_model.go` each register their own SGLang-query function
(`registerSGLangSaturationQueries`, `registerSGLangThroughputAnalyzerQueries`,
`registerSGLangQueueingModelQueries`) — SGLang-specific PromQL templates that populate the same
`domain.ReplicaMetrics` fields (`TotalKvCapacityTokens`, `KvUsageInstant`, `AvgITL`, etc.) the
engine-agnostic analyzer logic already reads. TA and QM never needed their own SGLang-aware
*parsing* code because they only ever consume already-normalized `ReplicaMetrics` — the
engine-awareness lives entirely in the collector/registration layer, not in the analyzer packages.

**What actually is sat-v2-exclusive:** parsing raw container `Command`/`Args` (via
`deployment_parser.go` for vLLM, `sglang_parser.go` for SGLang) to bootstrap the
`CapacityKnowledgeStore` for scale-from-zero estimation (§3.1 stage 0) — deployment-spec
introspection, a different capability from metric collection, that only sat-v2's package has. Even
this gets reused by *name* elsewhere: `queueing_model.go:78-80`'s registration comment states "The
collector populates `ReplicaMetrics.MaxBatchSize` from `--max-num-seqs` (vLLM) or
`--max-running-requests` (SGLang)" using "the engine-aware deployment parser (see
`saturation_v2.ParseEngineArgs`)" — QM's own metric collection already leans on sat-v2's parser for
one field.

[↑ TOC](#toc)

### B2 — Role math needs revisiting (re: §3.1) — future discussion, beyond 0.9 scope

Dean's corrected mental model: each **(analyzer, role)** pairing should be treated as its own
analyzer working on its own separately-scaled object — only the **optimizer** should combine math
across roles. Current code does not work this way: sat-v2/TA each aggregate `RoleCapacities` as a
sub-structure of one model-level `AnalyzerResult` (§3.1 stage 5, §3.2 stage 8), and the optimizer's
per-role combine (§4.3-§4.5) operates over that shape, not over independent per-role analyzer
instances. Explicitly flagged as a future discussion, out of scope for 0.9.

[↑ TOC](#toc)

### B3 — Variant math needs revisiting (re: §3.1) — future discussion, beyond 0.9 scope

Mental picture: each variant is independent; data should be kept **per scaled object** (i.e., per
variant+role — the actual K8s scale-target unit). Math and optimization should run **first per
scaled object**, and only **then** aggregate per model, applying the correct cross-variant and
cross-role combine math at that aggregation step — not compute model-level aggregates the way
`aggregateByVariant`/`aggregateByRole` (§3.1 stages 3/5) and the optimizer's per-model loop (§4) do
today. Beyond scope for 0.9.

[↑ TOC](#toc)

### B4 — Final assembly should be per scaled object (re: §3.1) — future discussion, beyond 0.9 scope

Same critique applied to §3.1 stage 6 (and by extension §3.2 stage 8's analogous TA assembly): the
final `AnalyzerResult` is assembled at the model level; it should be assembled per scaled object
instead, per B3. Beyond scope for 0.9.

[↑ TOC](#toc)

### Comments on §3.2 (throughput analyzer / TA)

*(§3.3 (QM) comments: skipped for now, per Dean.)*

[↑ TOC](#toc)

### C1 — Why does changing TA registration require a controller restart? (re: §3.2) — revisit later

Not clear why registration must be frozen for the process lifetime. Working hypothesis, not yet
confirmed: avoiding runtime locking — the in-code comment on `analyzersSnapshot`
(`engine.go:208-213`, quoted in §5) states the optimize goroutine reads the frozen
`analyzersSnapshot`, never the mutable `analyzers` slice, "so iteration is race-free without
runtime locking." If that's the actual reason, dynamic registration would need to introduce
synchronization (a mutex or atomic swap) that the current design deliberately avoids. Revisit
later — this overlaps with the existing backlog item on config-driven runtime enable/disable
(`wva-analyzer-lifecycle-plan.md` Half A; also flagged as a "do NOT implement stopgap" item in
prior memory on analyzer dynamic registration) — worth reading together rather than solving twice.

[↑ TOC](#toc)

### C2 — Shape-change tolerance / ready-gate values (re: §3.2 stages 2, 4) — beyond scope, two distinct asks

1. **Already resolved, good to confirm:** these are already named constants with rationale
   comments, not hardcoded literals — `DefaultShapeChangeTolerance = 0.20`, `DefaultMinSamples =
   10`, `DefaultMinKSpread = 0.30` (`internal/engines/analyzers/throughput/constants.go:9-35`),
   each with a doc comment explaining what it's for (though not *why that specific number*).
2. **Still open, beyond scope:** a methodology to verify/validate whether 0.20/10/0.30 are the
   *right* values — e.g. against real workload traces or a calibration experiment — as opposed to
   engineering judgment at authoring time. Naming them didn't answer this; it's a distinct
   follow-up.

[↑ TOC](#toc)

### C3 — GPS-mismatch: document the reason (re: §3.2 stage 6) — beyond scope, precise mechanism below

See the precise mechanism above (this response) rather than duplicating it here — summary for the
doc: `checkVariantGPSMismatch` evaluates the fitted `ITL(k)=A·k+B` model at the **current**,
directly-observed `k` (`model.ITLAt(m.KvUsageInstant)`) and compares the resulting predicted decode
rate against the also-currently-observed `GenerationTokenRate` — same operating point on both
sides, not current-k-vs-k*. The reason this same-k validity check matters: the identical fitted
model is later evaluated at `k_sat=0.85` (§3.2 stage 5, `itlSat`) for capacity/supply — a point
usually far from live traffic and never directly checkable. A model that already disagrees with
ground truth where it *can* be checked (current k) cannot be trusted at the point that actually
drives capacity (k*). This is the precise version of "the model's GPS(k) error is an indicator of
drift" — worth writing into the dev-guide/code comments as the documented rationale when this is
revisited (beyond scope for 0.9).

[↑ TOC](#toc)

### C4 — TA's final assembly gets the same per-scaled-object critique as sat-v2's (re: §3.2 stage 8)

Confirms/extends B4: §3.2 stage 8's `VariantCapacity`/`AnalyzerResult` assembly is at the model
level today; same future-discussion critique as B3/B4 — should be per scaled object. Beyond scope
for 0.9. (Already noted parenthetically under B4; called out here as its own point since Dean
raised it independently for TA specifically.)

[↑ TOC](#toc)

### C5 — Calibration-state persistence should be one common mechanism, not per-analyzer (re: §3.2 "Calibration-state storage")

Today each analyzer rolls its own bespoke in-memory state independently: TA's `variantStates` map
+ mutex (§3.2), sat-v2's `CapacityKnowledgeStore` (§3.1 stage 0), and (per §3.3) QM's own
`modelsParameterStore`. Dean's point: there should be **one shared persistence mechanism** that
analyzers plug into, not N independent ad hoc implementations. Beyond scope for 0.9, but worth
tracking as a design item — connects to the existing D-1 "ITL knowledge store" deferred-feature
entry and the broader F1 "pre-analysis extraction" direction already in the design doc's Future
Direction list.

[↑ TOC](#toc)

### C6 — Issue #1261 (`anyEPP`/`anyGPSMismatch` discarded, §3.2 stage 7) needs deeper investigation — understand the risk in current code

Flagged as needing more than a doc note: a dedicated investigation into what can actually go wrong
*today* because these two fully-computed signals are discarded (`analyzer.go:437-438`), not just a
restatement that the gate was removed. This reads as a candidate for its own research pass rather
than something to resolve inline while reading — flagging here now, will scope it properly once
the read-through of this doc is done rather than forking off mid-review.

**B1 — confirmed by Dean, closed.**

**C3 — confirmed by Dean, closed.** Restated back precisely: model exists to compute at `k_sat`;
GPS can only ever be measured at whatever the current `k` is; the mismatch check itself compares
model-at-current-k against measured-at-current-k. Matches the traced mechanism exactly.

[↑ TOC](#toc)

### D1 — Does scale-from-zero work with TA alone? — checked: no, it depends entirely on sat-v2

Verified against code: **no.** If only TA were enabled (hypothetically — sat-v2 currently always
runs regardless of what else is enabled, §3.4 stage 1), a variant with zero live replicas would get
**no `VariantCapacity` from TA at all**. TA's `Analyze()` builds its per-variant loop from
`groupByVariant(input.ReplicaMetrics)` (`analyzer.go:697-703`) — a variant with zero replicas
contributes zero `ReplicaMetrics` entries, so it never appears in that map and the loop never
visits it, in either `Observe()` or `Analyze()`. TA's own authors document this as a known gap,
verbatim (`analyzer.go:524-526`): "A future tier-3 (knowledge store) path for the scale-from-zero
case will be added once `Analyze()` is extended to iterate variants with state but no current
replica metrics." Even a *previously*-observed variant that scales to zero only keeps its stale
`variantState` for up to 60 minutes (`2×DefaultObservationMaxAge` eviction, §3.2) before being
garbage-collected — it is never re-populated while at zero replicas.

Scale-from-zero today works **only** because sat-v2's `CapacityKnowledgeStore` (§3.1 stages 0, 13,
14 — populated by parsing deployment/LWS container args, or borrowed from a compatible sibling
variant) can estimate `PerReplicaCapacity` with zero live replicas, and sat-v2 always runs
regardless of what else is enabled. This sharpens the existing "sat-v2 cannot be disabled" gap
(F1, prior review thread on `wva-analyzer-lifecycle-plan.md`) beyond "loses `PerReplicaCapacity`
sourcing in general" — specifically, disabling sat-v2 while running TA-only would lose
scale-from-zero *entirely*, not just degrade it.

**Doesn't contradict A2.** A2 proposes removing *artificial* special-casing in the Phase-1 loop
*mechanics* (the sat-first-literal + name-skip dance in `runAnalyzersAndScore`). This finding is a
*genuine* functional asymmetry between analyzers — TA cannot size a zero-replica variant, sat-v2
can — that would persist even under a fully uniform loop. A2's uniform-loop proposal and this real
capability gap are two different things; worth keeping them distinct so a future implementer
doesn't read A2 as implying they're equivalent.

[↑ TOC](#toc)

### Comments on §3.4 (engine orchestration — assembling the ballot)

[↑ TOC](#toc)

### E1 — `baseResult`: what breaks if sat is never called? "Every analyzer should have base." (re: §3.4 stage 1)

Checked, and it's worse than one failure mode:

1. **If sat-v2's own `Analyze()` errors** (e.g. the config type-assertion at `saturation_v2/analyzer.go:65-68`), `runV2AnalysisOnly` returns the error and `runAnalyzersAndScore` returns immediately (`engine_v2.go:112-113`, `if err != nil { return nil, err }`) — **before the non-saturation analyzer loop ever runs.** TA doesn't just lose its ballot position; it never executes that cycle at all. Confirmed no panic-recovery wrapper exists around `runV2AnalysisOnly` (the only `recover()` in `engine_v2.go` is inside `runRegisteredAnalyzer`, used only for non-sat analyzers).
2. **Even if sat's entry were simply absent** (not erroring, just not present), `saturationEntry()`'s by-name scan (§4.2) finds nothing → the nil-guard fires → zero decisions for the whole model, regardless of how good TA's data is.

**Dean's design principle: every analyzer should have its own "base"** — not be structurally dependent on sat-v2 having run. This is achievable without new data sources: `domain.ReplicaMetrics` (the raw input every analyzer receives) already carries `AcceleratorName` and `Cost` per replica (`internal/domain/saturation_analyzer.go:58-59`) — TA reads `rm.AcceleratorName`/`rm.Cost` today (per §3.2) but never copies them into its own `VariantCapacity`. The gap is an omission in TA's assembly step, not a missing capability.

[↑ TOC](#toc)

### E2 — Ballot literal: do we need to treat sat differently at packaging time? (re: §3.4 stage 2)

Open question as posed — effectively answered by E5 below: no. Once binding-analyzer selection is
positional (first-in-ballot) rather than name-based (E5), there is no remaining reason for the
ballot-construction step itself to special-case saturation by name — consistent with A2/A4's
general principle (don't special-case by analyzer identity where the logic doesn't need to know
which analyzer it's looking at).

[↑ TOC](#toc)

### E3 — Analyzer loop: unclear gate, failure handling, and the universal/local threshold question (re: §3.4 stage 3)

Confirmed: sat-v2's failure mode today is uniquely catastrophic relative to every other analyzer —
see E1.1. `runRegisteredAnalyzer` (non-sat path) recovers panics and returns `nil` on error/panic,
letting the loop continue for other analyzers (`engine_v2.go:402-428`); `runV2AnalysisOnly` (sat
path) has no such wrapper and aborts the whole call on any error. **Dean's principle: a broken
analyzer is a broken analyzer — this should not depend on which analyzer it is.** Should be
detected where possible, and a broken analyzer disabled/ignored for that round (ties to liveness,
E4) rather than aborting everyone else. If **no** analyzer is left (all broken/disabled), that
condition should be treated as fatal (or at least loudly surfaced) — not silently skipped.

**Threshold application:** confirmed already true and should stay an invariant — `applyUniversalThreshold`
runs for every analyzer's result today, sat included (§3.4 stage 3), calibrating
RequiredCapacity/SpareCapacity via the resolved scale-up/scale-down thresholds. No gap here to fix,
just a rule to preserve under any restructuring.

**Why both a universal (global) and a local (per-analyzer) threshold?** Checked `resolveThresholds`/
`scoreForAnalyzer`/`effectiveEnabled` (`engine_v2.go:356-396`) — all three share the identical
shape: look for a per-analyzer config entry; if found (and it has an override set), use it;
otherwise fall back to the `cfg`-level default. This is a standard override-over-default config
pattern, but **no comment anywhere documents why the design calls for two levels** rather than,
say, requiring every analyzer to always specify its own value. Best inference (not confirmed by any
doc/comment, flagged as inference): it lets most analyzers share one common threshold via the
global default, reserving per-analyzer override for the specific case where an analyzer's capacity
semantics genuinely differ. Worth asking directly rather than trusting this inference if it matters
for design decisions.

[↑ TOC](#toc)

### E4 — Liveness needs to be uniform, for every analyzer (re: §3.4 stage 5)

Proposed rule set, as stated: liveness is a simple, binary safety signal — "for any reason, analysis
couldn't happen this round" (config error, panic, bad data, staleness — no need to distinguish
which). "Never alive" is the clearest failure state; no partial-credit semantics needed. **If not
live, the analyzer should not be in the ballot at all** — not merely present with `.Live=false` (a
change from today: currently every entry stays in the ballot regardless of liveness, and §5's
combine functions check `.Live` per-entry rather than the ballot being pre-filtered). If the
resulting ballot is empty, the model is de-facto not scaled this round (consistent with today's
nil-guard-skip outcome, just reframed as "empty ballot," not "missing a specific name"). If **no**
analyzer is live for a model, that may even warrant being treated as fatal/surfaced loudly (see E3)
rather than a silent no-op every cycle.

[↑ TOC](#toc)

### E5 — Packaging: current design is BROKEN relative to intent — no anchor yet, and binding should be positional, not name-based (re: §3.4 stage 6)

**Confirmed: no anchor field exists anywhere in current code** (re-confirmed during the QM trace —
`pipeline.ModelScalingRequest`/`NamedAnalyzerResult` have no such field). Today's packaging just
produces one flat ballot, sat-v2's entry first by construction, everything else name-scanned later.

**Dean's stated original design, which current code does not match:** the request should carry
**two distinct things** — sat's `(a)` fields (identity/topology metadata) packaged separately, plus
**a ballot containing every live analyzer's full result** (their `(b)` sizing/demand data). Sat
being first in the ballot is a construction-order artifact and **should not matter to optimizer
logic** — the optimizer should never need to know or care which entry is "saturation" by name.

**Binding-analyzer selection should be positional, not name-based.** Whoever builds the anchor later
takes `(b)` from "the binding analyzer," which **defaults to first-in-ballot** — this replaces
today's `saturationEntry()` by-name scan (§4.2) with a positional convention. This is a genuine,
concrete simplification: today's single point of failure ("is there an entry literally named
`saturation`?") goes away entirely.

**Why `(a)` must be packaged here, not derived later:** `(a)` needs to be available **even if sat
is not in the final ballot** — whether because a config genuinely excludes it (per E6's `[TA]`-only
requirement) or because liveness filtering (E4) drops it for a given cycle. If `(a)` were only ever
derived from "whichever analyzer ends up binding" in Phase 2, and sat happened to be the one that
dropped out, `(a)` would be lost entirely. So it must be captured/packaged at generation time,
decoupled from whether sat's own result ultimately survives into the ballot handed to the optimizer.

**Two implementation options on the table, not yet chosen between:**
1. Package `(a)` as an explicit, separate field alongside the ballot: `{sat_a: <identity fields>,
   ballot: [...]}` — the ballot then only ever carries `(b)`-type sizing data uniformly.
2. **"Alternative" (Dean's phrasing):** keep one flat ballot as today, with `ballot[0]` a
   "throwaway" entry that carries both `(a)` and its own `(b)`. Anchor-creation logic later copies
   `(a)` out of `ballot[0]`, takes `(b)` from whichever entry is binding (defaulting to
   `ballot[0]` itself), and removes entry 0 from the ballot before handing it to the combine math.

[↑ TOC](#toc)

### E6 — 0.9 wiring requirement: must support `[sat]`, `[TA]`, `[sat, TA]` (re: §3.4, cross-cutting)

Concrete scope statement. This makes **D1's scale-from-zero finding a live blocker, not a
curiosity** — `[TA]` alone is explicitly in scope for 0.9. Three distinct gaps currently block
`[TA]`-alone, and it's worth being precise about which ones E1/E5's proposed design actually fixes
and which one it does **not**:

- **Fixed by E1 + E5:** TA lacks `(a)` identity/metadata (AcceleratorName/Cost) → E1 shows the raw
  data is already available, just not copied out. TA is invisible to `saturationEntry()`'s by-name
  lookup when sat isn't present → E5's positional-binding proposal removes the name dependency
  entirely (first-in-ballot binds, regardless of name).
- **NOT fixed by ballot restructuring — still open:** D1's scale-from-zero gap. TA has no
  capability today to size a variant with zero live replicas, regardless of how `(a)`-packaging or
  binding-selection changes — that requires either a TA-side equivalent of sat-v2's
  `CapacityKnowledgeStore`, some other fallback estimate, or an explicitly documented limitation for
  `[TA]`-only mode. This is the one piece of the 0.9 wiring requirement that the packaging redesign
  in E5 does not, by itself, resolve.

[↑ TOC](#toc)

### F1 — CORRECTION to E1: "base" needs a definition; my conclusion overreached

*(Dean, 2026-08-04: "you might be reading too much into my comment on 'base' — always clarify
first if term not well defined." Correcting per that instruction, not silently.)*

**What "base" actually is, precisely:** in code, `baseResult` (§3.4 stage 1) is simply sat-v2's
raw, whole `*domain.AnalyzerResult` — nothing more than the output of one `Analyze()` call. It is
**not** synonymous with `(a)` — today's code has no `(a)`/`(b)` split at all (that split is a
design-doc distinction, not something separated in `baseResult` itself); `(a)` is a design-level
*subset* of fields within it.

**If "base" means `(a)` specifically:** then yes, only sat has it today (confirmed — TA leaves
`AcceleratorName`/`Cost` zero, per B1/E1). But my E1 conclusion ("every analyzer should have its
own base... not be structurally dependent on sat-v2 having run") overreached — it should **not**
be read as "we don't need to call sat (or some source) to populate `(a)` at all." Corrected, per
Dean's own stated rules:
- **If `(a)` is genuinely missing** (no source can supply it), skipping the entire round is
  **correct behavior**, not a bug — there's nothing coherent to do without identity/topology data.
- **The actual bug is narrower:** if `(a)` is available, but `(b)` is missing/failing *specifically
  from sat*, that should **not** cause TA's `(b)` to be skipped too. This is exactly what E1
  finding #1 already demonstrated (a sat-v2 `Analyze()` error aborts the whole analyzer loop before
  TA ever runs) — that finding stands, but the fix it points to is "isolate sat's `(b)`-failure from
  TA's `(b)`-contribution," not "make every analyzer self-sufficient on `(a)`." E5's design (package
  `(a)` once, decoupled from whether sat's full entry survives into the ballot) is already aligned
  with this corrected framing and does not need to change.

[↑ TOC](#toc)

### F2 — CORRECTION to E3: the universal/local threshold mechanism is simple and already matches your description

*(Dean's mental model, stated directly: thresholds are the standard autoscaler margin-of-operation
mechanism around target PRC — the same concept HPA has under a different name. Global default is
the norm; per-analyzer override makes sense because analyzers measure different metric types.
Mechanism should just be: (i) look up the threshold value, falling back to a default if missing;
(ii) apply it. Nothing more complex than that.)*

Confirmed: that is exactly how the code works, and E3's framing of this as an open/undocumented
question was an overstatement — there's no hidden complexity to explain. `resolveThresholds`
(`engine_v2.go:367-375`) is step (i): scan `cfg.Analyzers` for the named analyzer's entry; if found
and it has an override, use it; otherwise fall back to `cfg.ScaleUpThreshold`/`cfg.ScaleDownBoundary`.
`applyUniversalThreshold` (called right after, once per analyzer per cycle) is step (ii). Two calls,
in that order, nothing else in between. Retracting E3's "no comment documents why two levels
exist... best inference" paragraph — the why was never actually unclear; I mischaracterized a
simple, correctly-designed mechanism as an open question when the only real thing to confirm was
"does the code match the description," and it does.

[↑ TOC](#toc)

### F3 — Scale-from-zero: SUPERSEDED — see `planning/scale-from-to-zero-analysis.md`

*(Originally a same-session writeup of the `prepareModelData` gate; fully superseded once the
dedicated investigation landed. Kept as a one-line pointer rather than duplicated content, to avoid
drift between two documents describing the same mechanism.)*

Confirmed there: the real scale-from-zero trigger is a **fully independent engine**
(`internal/engines/scalefromzero/`), not a path through `prepareModelData`/the analyzers mapped in
this doc at all. See that document's §2 for the full trace and headline findings #1/#2/#3, and §4
for the multi-variant/role gap. `prepareModelData`'s gate (§3.4 above) remains accurate as a
description of why the *analyzer* pipeline can't bootstrap a fully-zero model on its own — it just
turns out a different, separate mechanism owns that job instead.

[↑ TOC](#toc)

### F4 — Scale-to-zero: SUPERSEDED — see `planning/scale-from-to-zero-analysis.md`

*(Originally "Dean's own examination in progress, not yet traced"; now fully traced.)*

Full mechanism, gates, and answers to the analyzer-agnosticism tension raised here are in that
document's §3. Headline: `applyScaleToZeroEnforcement` is fully EPP-blind (only reads a completed-
request Prometheus counter) and always moves every role of a P/D model together, by explicit
design — the mirror-image asymmetry to F3's finding #2.

[↑ TOC](#toc)

### Comments on §4.2 / §4.3 (binding-entry resolution, role-state init)

[↑ TOC](#toc)

### G1 — §4.2 IS the main locus of the anchor-refactor change; functional spec for the new function (re: §4.2)

Confirmed: yes — per A2/E5, anchor resolution belongs entirely in Phase 2, and this function
(`saturationEntry` today, its successor tomorrow) is where it should live. **"Ideal world, all
changes are in this function"** directly supersedes the current `ta-anchor-refactor-plan.md` draft,
which tries to build the anchor in Phase 1 (`runAnalyzersAndScore`) — exactly the site the
executability pass (`M-A`) showed has no `req` in scope. Confining the change to this one function
(plus small helpers it calls) removes that blocker entirely, consistent with everything since A2.

**Functional spec, as given:**
- The function returns the anchor: `(a)` populated from sat, `(b)` populated from the binding
  analyzer.
- **First call** (may be its own helper function): creates the anchor, populates `(a)` from sat,
  populates a **default** `(b)`.
- **Subsequent calls: refresh binding** — re-determine which analyzer is currently binding and
  update `(b)` if it changed.
- **Single-analyzer ballot:** skip the refresh entirely — no ambiguity, nothing to do.
- **Multi-analyzer ballot:** find the binding analyzer, replace `(b)`.
- **Invariant:** `PerReplicaCapacity`, `RequiredCapacity`, `SpareCapacity` are always specific to
  the binding analyzer — never blended. Confirms `(b)` is genuinely single-sourced, matching
  everything established since E1/E5.

**Cross-reference worth flagging:** "first call creates" vs. "other calls refresh binding" maps
cleanly onto the *existing* PR-1 (`ta-anchor-refactor-plan.md`, static core) vs. PR-2
(`ta-anchor-dynamic-refresh-plan.md`, per-iteration dynamic refresh) split already in the plan-doc
structure — PR-1 would build the "create" path, PR-2 the "refresh" path. This spec is a much more
precise version of what those two plans were already conceptually reaching for; it isn't a new
split, it's a correction of how PR-1's half should actually be implemented.

[↑ TOC](#toc)

### G2 — §4.3: binding-analyzer identification is independent of role-state init — checked, confirmed safe

Checked precisely, because a wrong answer here would matter: **yes**, the binding analyzer can be
identified correctly without `initRoleState`, and there is no sort-order risk.

- Both optimizers already call `saturationEntry(req.AnalyzerResults)` (today's binding lookup)
  **before** `initRoleState(s)` — confirmed exact line order in `CostAwareOptimizer.Optimize`
  (`cost_aware_optimizer.go:48` then `:59`) and `GreedyByScoreOptimizer.Optimize`
  (`greedy_score_optimizer.go:125` then `:130`).
- A repo-wide check for anything that sorts or reassigns `req.AnalyzerResults` itself (as opposed to
  the per-variant lists, which genuinely do get sorted — `sortByCostEfficiencyAsc`,
  `sortVariantsForScaleDown`) found **zero** hits. The ballot slice is set once at packaging time
  (§3.4) and never reordered anywhere in the pipeline.
- `initRoleState`'s `for i, e := range s` (`analyzer_helpers.go:131`) iterates that same
  unreordered slice by index, so `s[0]`/`ps[0]` refer to the same entry whether checked before,
  during, or after role-state init.

**Conclusion:** switching binding-analyzer identification from name-based (`saturationEntry`
scanning for `Name=="saturation"`) to positional (`ballot[0]`, per E5/G1) is safe with respect to
`initRoleState` — the two mechanisms are independent today, and nothing in the current code
reorders the ballot in a way that could make "first in ballot" ambiguous.

[↑ TOC](#toc)

### H1 — Confirmed: scale-from/to-zero is untouched by the anchor/binding mechanism, and needs its own separate fix

Your understanding is correct. The anchor/binding refactor (G1/G2, E5, A2) operates entirely on the
ballot *after* analyzers have already run — it changes how `(a)`/`(b)` get assembled from whatever
results exist, not whether an analyzer runs or what it can see. Neither the full-zero case (F3's
`prepareModelData` gate, which fires upstream of `runAnalyzersAndScore`/`collectV2ModelRequest`
entirely — the anchor code never even gets invoked) nor the partial-zero case (D1's finding that
TA's own per-variant loop can't see a zero-replica variant regardless of who's binding) is affected
by *how* binding-analyzer selection works. If either is broken today, it stays exactly as broken
under any version of the binding mechanism discussed so far — this needs its own fix, at its own
code location (`prepareModelData` for the full case; something TA-side for the partial case), not
something the anchor work resolves as a side effect.

**Scoping implication worth flagging:** this puts a real dependency on E6's `[TA]`-alone
requirement for 0.9 — if `[TA]`-alone needs to ship without a separate scale-from/to-zero fix
landing first, it ships with a known limitation (no scale-from-zero support, and scale-to-zero
behavior TBD pending F4) rather than that gap being incidentally closed by the anchor work.

[↑ TOC](#toc)

### H2 — Correcting confusion: "ballot[0]" was not proposing a reserved anchor slot separate from the real ballot (re: E5, G1)

Retracting the ambiguity — this was my inconsistency across two earlier comments, not a real design
question. There is no proposal for a two-tier structure where index 0 is "the anchor slot" and
indices 1+ are "the real voting ballot." The ballot is simply the flat list of enabled/live
analyzer entries — for 0.9, `[sat]`, `[TA]`, or `[sat, TA]`: 1 or 2 entries, nothing reserved. **The
anchor is a separate, derived structure**, built by reading `(a)` from sat's entry (wherever it sits
in that list) and `(b)` from whichever entry is binding (wherever *that* sits) — it does not
require removing or reserving any ballot position. This matches G1's own spec exactly: binding is
found *within* the list of "analyzers in play," not by splitting the list into a special slot plus
a remainder.

Where the confusion came from: E5 floated two implementation options without distinguishing them
clearly. E5's option 1 (package `(a)` as an explicit separate field; the ballot itself carries only
`(b)`-type data uniformly) is what matches G1 and is the one to carry forward. E5's option 2 (the
"Alternative" — `ballot[0]` holds both `(a)` and `(b)`, gets copied-from, then removed) *does*
describe a reserved-slot structure — that's the one you were asking about, and on reflection it's
an unnecessary complication that doesn't match G1's cleaner model. Retracting it.

[↑ TOC](#toc)

### H3 — The real concern behind the §4.3 question: what does "binding analyzer" mean once role exists? (re: §4.2/§4.3, ties directly to B2/B3)

G2 answered a narrower mechanical question than the one actually being asked (whether
`initRoleState` reorders anything and breaks positional lookup — it doesn't, confirmed). The real
question is conceptual: **"binding" should mean whichever analyzer matters for fair-share,
cost-efficiency, and rebalance logic — but which analyzer that *is* can differ by role**, and there
are two structurally different ways to define it once role exists:

1. **Per-role binding.** Treat each `(analyzer, role)` pairing as its own unit; find the binding
   analyzer separately per role. This is exactly B2's already-flagged principle ("each
   (analyzer, role) pairing... its own analyzer working on its own separately-scaled object")
   applied specifically to binding-selection, rather than deferred wholesale.
2. **Model-level binding (role-blind).** Pick one binding analyzer for the whole model, used
   uniformly across every role — matching what today's code actually does (`saturationEntry`
   returns one `*domain.AnalyzerResult`; its `RoleCapacities[role]` map is read per-role, but the
   *analyzer* selection itself never varies by role).

**The subtlety you're pointing at with option 2:** if the single chosen analyzer's own internal math
couples roles together (one role's effective demand adjusted/capped based on another role's state),
then "this analyzer is binding for the whole model" silently imports that cross-role coupling into
the binding decision in a way option 1's per-role independence never would. (The closest concrete
example traced so far is TA's `distributeDemandByRole`, §3.2 stage 22, which splits total demand
evenly across active non-prefill roles — a real cross-role coupling, though I don't have a specific
"50% coverage" cap traced anywhere; read your example as illustrative rather than a cited mechanism
— flag if you meant something specific.)

**This is genuinely unresolved, and I'm not going to pick for you.** One thing worth weighing:
`ta-anchor-refactor-plan.md`'s stated PR-1 scope is "ZERO combine arithmetic change" — preserve
today's behavior exactly. Today's behavior *is* option 2 (model-level, role-blind binding). Under
that existing scope constraint, PR-1 likely has to replicate option 2 as-is for 0.9, with option
1's role-aware redesign deferred alongside B2/B3's already-flagged future work. That would resolve
this cleanly *for PR-1's stated scope* — but "which one is actually correct" and "which one PR-1 is
scoped to preserve" are different questions, and only you can say whether the cross-role-coupling
concern under option 2 is a live correctness risk worth pulling into 0.9, or genuinely deferrable.

[↑ TOC](#toc)

### Comments on §4.5 / §4.6 (scale-down core loop, rescale pre-pass)

[↑ TOC](#toc)

### I1 — §4.5 NIT: two distinct gates, not one (re: §4.5)

Checked precisely because the two phrasings ("no role needs scale-up" vs. "all roles have spare")
describe **different gates**, not the same thing reworded:

- **Outer, function-entry dispatch** (`anyRoleNeedsScaleUp`, checked before §4.5 is even entered):
  based on `Remaining`, which derives from `RequiredCapacity`. §4.5 is entered whenever **no**
  analyzer/role pair has positive remaining demand.
- **Inner, per-role veto** (`needsScaleDownForRole`, checked *inside* §4.5, per role): based on
  `Spare`/`RoleSpare` — requires **every live analyzer** to show `>0` spare for that role before
  any variant of that role actually gets shrunk.

These are not equivalent, because `applyUniversalThreshold` (`engine_v2.go:447-472`) computes RC
and SC **independently** — `rc = max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)`,
`sc = max(0, TotalSupply − TotalDemand/scaleDown)` — and confirmed there **is** a real dead zone
where both are simultaneously zero (demand sits between the two thresholds: not high enough to need
more capacity, not low enough relative to supply to free any up). So §4.5 can be *entered* (outer
gate: "no scale-up needed") and still do **nothing at all** for a given role, if that role is
sitting in the dead zone rather than genuinely having spare. Your phrasing — "reached when all
roles need scale down (have >0 spare)" — precisely and correctly describes the **inner** veto gate
(when a role's variants actually get shrunk), not the outer one (when the function is entered at
all). Worth keeping both phrasings distinct rather than treating them as interchangeable glosses.

[↑ TOC](#toc)

### I2 — §4.5 "remove count": confirmed safe against rescale, for a stronger reason than ordering (re: §4.5, §4.6)

Checked: `reclaimRole` (`rescale.go:387-410`) does not implement its own reduction logic — it
**calls the identical `scaleDownVariantSet` function** (`cost_aware_optimizer.go:111-146`) that the
core §4.5 path uses, passing rescale-specific pick/apply closures but going through the same
cheapest-at-1 protection rule. So this isn't merely "safe because §4.6 runs first and the `handled`
map prevents double-processing" (true, and also holds) — it's safe because there is **one shared
implementation** of the cheapest-at-1 rule, invoked from both call sites. There's no separate
reclaim mechanism that could bypass it.

[↑ TOC](#toc)

### I3 — §4.6: replica count per accelerator type is derived from `TotalDemand`, not `RequiredCapacity` (re: §4.6)

Checked precisely, because the question assumed RC and the code reads something else.
`roleDemandGPUs` (`rescale.go:543-568`) reads **`satEntry.TotalDemand`** (model-level, synthetic
`"both"` role) or **`satEntry.RoleCapacities[role].TotalDemand`** (P/D role) — the *raw* demand
figure, **not** the threshold-adjusted `RequiredCapacity` that `applyUniversalThreshold` computes
and that the core allocation loop's `Remaining`/`roleBottleneckReplicas` (§4.3/§4.4) are built from.
It divides that raw demand by the role's most cost-efficient variant's `PerReplicaCapacity`,
ceil-rounds to a replica count, then multiplies by that variant's GPUs-per-replica. **Worth
flagging as its own fact, independent of the binding question:** rescale's sizing math and the core
optimizer's sizing math use two different source quantities (raw `TotalDemand` vs.
threshold-derived `Remaining`) to arrive at target counts. Not editorializing on whether that's
intentional — just noting it's a real, confirmed difference, not something I've resolved.

[↑ TOC](#toc)

### I4 — CORRECTED: rescale must read from the merged anchor, not from a raw analyzer's own result (re: §4.6)

*(Dean, 2026-08-04: "I thought all optimizer code uses anchor instead of TA entry directly... this
contradicts my previous understanding." Correct — the original text below stated the wrong thing
as if it were the design's consequence rather than an implementation pitfall to avoid. Struck
through, not deleted, per this doc's correction convention.)*

~~Confirmed (already documented in §4.6's own text, restating for directness): every read in
rescale that touches an `AnalyzerResult`... goes through the identical
`saturationEntry(req.AnalyzerResults)` lookup used by the core optimizer (§4.2). So **yes** — under
the binding refactor, if TA becomes the binding analyzer, all of rescale's GPU-demand math shifts
to reading from TA's result instead of sat's, with no separate rescale-specific override.~~

**Corrected.** `AcceleratorName`/`Cost` are squarely `(a)` — they should never be read from TA, and
nothing gets copied *into* TA's stored result. `AcceleratorName`/`Cost` live on
`domain.VariantCapacity`, not on `AnalyzerResult` — `AnalyzerResult.VariantCapacities` is a *slice*
of these, one per variant. So the anchor can't be built as "(a) from sat's whole `AnalyzerResult` +
(b) from binding's whole `AnalyzerResult`" — the merge has to happen **per variant, matched by
`VariantName`**: for each variant, `AcceleratorName`/`Cost`/`Role`/`ReplicaCount`/`PendingReplicas`
come from **sat's** `VariantCapacity` entry for that name; `PerReplicaCapacity`/`TotalCapacity`/
`TotalDemand`/`Utilization`/`Reason` come from the **binding analyzer's** `VariantCapacity` entry
for that same name — producing one new, merged `VariantCapacity` per variant in the anchor. Every
consumer, rescale.go included, reads from this merged list — never from a raw per-analyzer result
directly, regardless of who is binding.

Under this corrected design, `singleAccType` (I5, below) always sees `AcceleratorName` sourced from
sat via the anchor merge, whether TA, sat, or both are in the ballot — TA becoming binding for `(b)`
has no bearing on where `(a)` fields come from.

[↑ TOC](#toc)

### I5 — CORRECTED: the failure mode only exists if a read site bypasses the anchor merge (re: §4.6, ties to E1, I4)

*(Also corrected alongside I4 — same misreading.)*

~~This is the specific slice worth being precise about. `singleAccType` (`rescale.go:447-460`)
skips every variant with `vc.AcceleratorName == ""`... TA's `VariantCapacities` currently leave
`AcceleratorName` at zero value for every entry (E1, confirmed). So if TA is binding: `singleAccType`
returns `("", false)`... `applyRescale`'s `if !ok { continue }` silently defers that model out of
rescale entirely.~~

**Corrected framing:** this failure mode is real *only if* an implementation bypasses the anchor and
lets `singleAccType` (or any other `(a)`-reading site) see a raw, unmerged analyzer result directly
— which per I4 is not what the design calls for. Reframed as a **test case to verify once this is
built**, not a design gap to solve differently: confirm `singleAccType` (and every other rescale
read of an `(a)`-type field) operates on the anchor's merged `VariantCapacities`, so that TA-binding
never produces an empty `AcceleratorName` in the first place. E1 and E5/G1's per-variant merge (I4)
are what prevents this — the earlier framing ("fixing E1 alone or E5 alone might not be enough")
still correctly flagged that rescale's specific read sites need auditing against the anchor, that
part of the original note stands; what was wrong was implying the design itself routes through raw
TA data.

**One thread this ties together cleanly:** if TA is binding and TA's `VariantCapacities` has no
entry at all for a variant that sat's list does have (D1/F3's scale-from-zero gap — TA's per-variant
loop never visits a zero-replica variant), the per-variant merge hits a variant with `(a)` available
from sat but no `(b)` from the binding side for that name. This is exactly where G1's "first
call... populate a default `(b)`" language becomes load-bearing, not an edge case outside the
design.

[↑ TOC](#toc)

### I6 — §4.6: role accounting confirmed — already model-level-binding, role-aware-reading (re: §4.6, ties to H3)

Confirmed: rescale already reads `satEntry.RoleCapacities[role]` (per role) off the **single**
binding entry (I4) — i.e., it already implements H3's "option 2" (one binding analyzer selected at
the model level, that analyzer's own internal per-role data read out afterward) rather than option
1 (a separate binding analyzer chosen per role). This is existing, already-shipped behavior, not
something introduced by the refactor — consistent with the H3 resolution I floated (PR-1's "zero
combine arithmetic" scope likely commits it to preserving exactly this model-level-binding shape).

[↑ TOC](#toc)

### I7 — Scope note

I2–I6 are scoped exactly to what was flagged as in-scope ("the part where TA can become the binding
analyzer"). I have not attempted the broader analysis of whether rescale's overall water-filling
formula (§4.6's `computeRescaleTargets`/`apportionLeftover` priority-weighted allocation) is itself
correct or desirable — that's the part explicitly marked out of scope, left for your own deeper
look.

[↑ TOC](#toc)

### Comments on §5 / §6 / §7

[↑ TOC](#toc)

### K1 — QM is conceptually closer to a second V1 than to "another analyzer" (re: §6, confirms A1)

Dean's reframing, not a change of decision: QM has its own self-contained logic (Kalman-filter
tuning, its own SLO-based sizing, its own `RequiredCapacity`/`SpareCapacity` formula — a raw
`max(0, demand−supply)` rather than `applyUniversalThreshold`'s threshold-adjusted version) and
"seems like it cannot have the new optimizer logic" — i.e. QM isn't a peer of sat-v2/TA that could
plug into the anchor/binding combine machinery at all; it's structurally more like a second V1: its
own complete, parallel mode, not a participant in the shared analyzer-combine system. This sharpens
the mental model already captured in A1/A6 (QM must not affect the anchor work; the mechanism is
still open, properly fixing QM is deferred) without changing that disposition — it explains *why*
QM was never going to be "just another entry in the ballot" even before A1/A6 were decided.

[↑ TOC](#toc)
