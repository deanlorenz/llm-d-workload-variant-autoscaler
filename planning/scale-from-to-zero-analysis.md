# Scale-From-Zero / Scale-To-Zero — Analysis

**Status:** DRAFT — first pass, synthesized from two parallel read-only investigations (one per
mechanism). Three load-bearing claims (the multi-variant TODO, the hardcoded `1`, the separate
`RunnableFunc` registration) independently re-verified against the live file; the actuation path
(§5) directly re-traced against `engine.go:1561-1770` on 2026-08-04 (was the doc's one open
reconciliation point — now resolved); the rest is high-confidence agent-trace output, not yet
adversarially re-checked line-by-line.

**Base code:** `main @ 9906dac5` (`Main/` worktree — same base as `multi-analyzer-dataflow-map.md`).

**Purpose.** Companion to `planning/multi-analyzer-dataflow-map.md`, split out because these two
"zero-boundary" mechanisms turned out to be **structurally separate** from the multi-analyzer
engine mapped there — not a variant of it. That doc's §F3/§D1/§H1 found that the "normal" engine
cannot bootstrap a model from zero (its `prepareModelData` gate discards EPP signals before any
analyzer runs) and flagged scale-from/to-zero as needing its own investigation. This is that
investigation.

**Headline findings (read this first):**

1. **Scale-from-zero is a fully independent engine** — `internal/engines/scalefromzero/`, not a
   code path inside `saturation`/`pipeline`. It polls every 100ms (its own `PollingExecutor`,
   unrelated to the saturation engine's tick), checks an EPP metric via **direct EPP-pod-scraping**
   (bypassing Prometheus/PromQL entirely — a third metrics-collection pipeline, distinct from the
   PromQL-based one the rest of the codebase uses), and sizes the new replica with a **hardcoded
   literal `1`** — zero involvement from saturation-v2's capacity store or any analyzer.
2. **Correction to the working mental model, not just a gap-fill:** it does not "start one pod from
   one variant." The EPP signal it checks is keyed **only by `ModelID`**, with no variant/role
   attribution, and the `optimize` loop iterates every inactive VA independently with no
   cross-variant coordination. There is an explicit, unresolved `TODO` in the code acknowledging
   this: *"Right now we are scaling all the VA for the same target model. We need to scale only the
   VA that has the lowest cost."* Today, every zero-replica variant **and every P/D role** of a
   model gets independently scaled to 1 replica, concurrently, on the same tick — not a single
   selected variant. This is a documented, known behavior (referenced in
   `docs/developer-guide/troubleshooting.md`), with no e2e coverage of the multi-variant or P/D case.
3. **Two fundamentally different actuation mechanisms coexist.** Scale-from-zero actuates
   **directly** — a synchronous PATCH of the Kubernetes scale subresource, bypassing HPA/KEDA
   entirely. The "normal" engine's decisions (and scale-to-zero, which mutates the same decision
   objects) actuate **indirectly** — by staging the target into `VariantAutoscaling.Status` and
   emitting a Prometheus replica-scaling metric that an external **HPA/KEDA** consumes and acts on
   (§5, resolved 2026-08-04 by a direct re-trace of `applySaturationDecisions`).
4. **Scale-to-zero is fully EPP-blind.** It only reads a *completed*-request Prometheus counter
   (`vllm:request_success_total`) over a retention window; it never sees EPP queue depth or arrival
   rate, even though `modelData` carries both. This is the mirror-image asymmetry to finding #1: the
   *up* direction is (supposed to be) EPP-aware, the *down* direction structurally cannot be.
5. **Scale-to-zero always moves all P/D roles of a model together**, by explicit design ("scaling
   prefill to zero while keeping decode makes the model non-functional") — the opposite of
   scale-from-zero's uncoordinated per-variant/per-role independence in finding #2.
6. **Scale-from-zero's trigger is scoped per-VA, not per-model — which means it already, today,
   incidentally covers "partial-zero" too** (a single variant/role at zero replicas while its model
   siblings are actively serving). `isInactive` (`internal/utils/variant.go:270-272`) checks only
   that specific VA's own replica count; there is no model-level pre-filter anywhere in
   `filterVariantsByScaleTargetAccessor`. So the *same* mechanism that revives a fully-zero model
   (finding #1/#2) will also revive one straggler variant in an otherwise-live model, with the same
   hardcoded `1` and the same complete independence from any analyzer's capacity math — see §2 for
   the full implication and §4 for how this compares to the multi-analyzer engine's own (much more
   fragile) path for the same scenario, traced in `ta-anchor-refactor-review.md`'s "Partial
   scale-from-zero under `[TA]`-alone" section.

---

## Reading Protocol

Read the TOC, then fetch sections on demand via `Read <file> offset:<n> limit:<m>`.

## TOC

- [§1 Two mechanisms, two actuation paths — orientation](#1-two-mechanisms-two-actuation-paths--orientation) L76:106
- [§2 Scale-from-zero: full trace](#2-scale-from-zero-full-trace) L107:146
- [§3 Scale-to-zero: full trace](#3-scale-to-zero-full-trace) L147:186
- [§4 The multi-variant/role gap](#4-the-multi-variantrole-gap) L187:243
- [§5 How the "normal" engine's decisions reach Kubernetes (RESOLVED — indirect, metrics-for-HPA/KEDA)](#5-how-the-normal-engines-decisions-reach-kubernetes-resolved--indirect-metrics-for-hpakeda) L244:290
- [§6 Cross-references to `multi-analyzer-dataflow-map.md`](#6-cross-references-to-multi-analyzer-dataflow-mapmd) L291:312
- [§7 Candidate follow-ups](#7-candidate-follow-ups) L313:348

## §1 Two mechanisms, two actuation paths — orientation

```
scalefromzero.Engine (internal/engines/scalefromzero/)          [cmd/main.go:524-533]
  own PollingExecutor, 100ms tick, own goroutine — NOT the saturation engine's loop
  │
  optimize() → for every inactive (0-replica) VA cluster-wide, independently:
    check EPP flow-control-queue metric (direct pod-scrape, model-ID-keyed only)
      → if pending: DirectActuator.ScaleTargetObject(..., 1)   ← hardcoded, no analyzer involved
      → writes to common.DecisionCache (read only by this package)

saturation.Engine (internal/engines/saturation/) — the "normal" engine, multi-analyzer-dataflow-map.md
  optimize() → V1 / V2 / QM dispatch → analyzers → optimizer → decisions
    → Stage 3: applyScaleToZeroEnforcement (shared by V1/V2/QM)
        Gate: vLLM-only engine type
        Gate: no variant/role has minReplicas > 0
        Signal: vllm:request_success_total over a retention window (NOT EPP — no queue/arrival awareness)
        If idle: zero every variant/role of the model together
        If not idle and total was already 0: float the cheapest variant back to 1
    → Stage 4+: decisions eventually reach K8s — see §5, not fully pinned down
```

Neither mechanism calls into the other. Scale-from-zero never touches saturation-v2 or any
analyzer; scale-to-zero never touches EPP. They meet only at the boundary they're named for — one
governs 0→1, the other governs 1→0 — and even that boundary isn't symmetric (see headline findings
#2 and #5, and #4/#5 above).

[↑ TOC](#toc)

---

## §2 Scale-from-zero: full trace

**Location:** `internal/engines/scalefromzero/engine.go` (package `scalefromzero`), registered as
its own `manager.RunnableFunc` at `cmd/main.go:524-533` — confirmed a separate registration, not
nested inside the saturation engine's own runnable (registered separately just above it,
`cmd/main.go:479-517`). Runs only on the leader.

| Stage | Data produced | Producing code / loop | Gates | Logic |
|---|---|---|---|---|
| 1. Scheduling | ticks every 100ms | `NewEngine` builds a `PollingExecutor` with `Interval: 100ms` (`engine.go:110-116`); `StartOptimizeLoop` (`:123-125`) calls `e.executor.Start(ctx)`, repeatedly invoking `e.optimize(ctx)` | none | independent cadence from the saturation engine's own tick |
| 2. Find candidates | `[]VariantAutoscaling` (every inactive VA cluster-wide) | `utils.InactiveVariantAutoscaling` (`engine.go:132`, `variant.go:91-93`) — VAs are *synthesized in-memory* from annotated HPAs/KEDA ScaledObjects (the CRD was removed) | `isInactive` = current replicas via `GetDesiredReplicas` == 0 (`variant.go:270-280`) | cluster-wide scan, not scoped to one model or namespace |
| 3. Fan-out | one goroutine per inactive VA, bounded by a semaphore | `optimize`, `engine.go:155-183` (verified) — `for _, va := range inactiveVAs { ... go func... }` | concurrency cap = `SCALE_FROM_ZERO_ENGINE_MAX_CONCURRENCY`, default 10 | **no grouping/dedup by model** — every VA processed fully independently |
| 4. Per-VA EPP check | `bool pendingRequestExist` | `processInactiveVariant`, `engine.go:204-416`; EPP source via `e.Datastore.PoolGetMetricsSource` → `PodScrapingSource.Refresh` (`internal/collector/source/pod/pod_scraping_source.go`) — **scrapes the EPP pod's `/metrics` HTTP endpoint directly**, bypassing Prometheus/PromQL | scans for `__name__ == "inference_extension_flow_control_queue_size"`, `value > 0`, label `target_model_name == va.Spec.ModelID` (`engine.go:295-306`, verified) — **keyed only by model ID, no variant/role attribution** | pool-datastore-not-synced → skip gracefully; no pending request → return `nil` (no-op) |
| 5. Trigger | direct K8s scale-subresource mutation | `e.Actuator.ScaleTargetObject(ctx, unstructuredObj, 1)` (`engine.go:319`, verified literal `1`) → `DirectActuator` (`internal/actuator/direct_actuator.go`) calls `client-go`'s `ScalesGetter`: `Get` the `Scale` object, then `Update` `Spec.Replicas` | none beyond stage 4's gate | **synchronous, direct PATCH of the real Deployment/LWS replica count** — bypasses HPA/KEDA/metrics-based actuation entirely; sizing is the hardcoded constant, no analyzer or capacity-store consulted |
| 6. Bookkeeping | `domain.VariantDecision` in `common.DecisionCache`; VA status/condition fields; k8s `ScaledUp` Event | `engine.go:326-406` | none | `common.DecisionCache` (`internal/engines/common/cache.go:14-42`) is written **and read only by this package** — the saturation engine never reads it; a comment at `saturation/engine.go:1679` referencing it as a "controller patch path" does not describe a real code path for the normal engine (flagged in §7) |

**The multi-variant/role TODO (verified verbatim, `engine.go:317-318`):**
```go
// 1.  Scale up from zero to one
// TODO: Right now we are scaling all the VA for the same target model. We need to scale only the VA that has the lowest cost.
```
Because stage 4's check is keyed only by `ModelID` and stage 3's fan-out has no cross-variant
coordination, **every** currently-inactive VA of a model — every accelerator variant, every P/D
role — independently passes the same check on the same tick and independently gets its own direct
scale-to-1 call. See §4.

**Q1 — does this touch saturation-v2 or any analyzer?** No. `grep` for
`saturation_v2|CapacityKnowledgeStore|estimateStoredCapacity|lookupCompatibleCapacity` across the
package returns nothing. Sizing is the hardcoded `1`, full stop.

**Q3 — is there a real mismatch with saturation-v2's zero-replica capacity fallback?** Yes,
confirmed. Saturation-v2's confirmed capability (estimating `PerReplicaCapacity` from its
persistent capacity store even at zero live replicas — `multi-analyzer-dataflow-map.md` §3.1 stages
0/13/14) is never invoked here. Whether it *could* matter depends entirely on the unresolved TODO
above — see §4.

[↑ TOC](#toc)

---

## §3 Scale-to-zero: full trace

**Location:** `applyScaleToZeroEnforcement` (`internal/engines/saturation/engine.go:1341-1376`), a
shared "Stage 3" step called from all three optimize paths.

| Path | Call site | Decisions scope |
|---|---|---|
| V1 | `engine.go:731-734`, inside `optimizeV1` | one model's decisions (all roles), from `analyzeRoleGroups` |
| V2 | `engine.go:1047-1052`, inside `optimizeV2`, once per model in a `for _, req := range requests` loop | full cross-model `allDecisions` slice — safe because the enforcer filters by `ModelID`+`Namespace` internally |
| QM | `engine_queueing_model.go:114-119` | same shape as V2 |

| Stage | Data produced | Producing code / loop | Gates | Logic |
|---|---|---|---|---|
| 0. Early-out | — | `engine.go:1348` | `len(decisions)==0` → return | — |
| 1. Engine-type veto | `bool` | `scaleToZeroSupportedForEngines` (`:1319-1326,1353`), via `inferenceengine.Present(scaleTargets)` | **any** non-vLLM engine present (SGLang, or mixed vLLM+SGLang) → skip the whole model | reason: the request-count query (stage 3) is hardcoded to `vllm:request_success_total`; a non-vLLM model would always read "0 requests" and be falsely zeroed |
| 2. Min-replicas floor | `bool` | `hasMinReplicasAboveZero` (`:1302-1309,1358`) — iterates **all** `VariantReplicaState` for the model together | any state with `MinReplicas != nil && *MinReplicas > 0` → skip the **entire model** | `MinReplicas` from the VA spec; nil means "not set, scale-to-zero allowed" |
| 3. Config resolution | `ScaleToZeroConfigData`, `SaturationScalingConfig` | `:1364,1367` | — | inline `saturationConfig.scaleToZero.enabled` overrides a separate `wva-model-scale-to-zero-config` ConfigMap |
| 4. Enablement precedence | `bool scaleToZeroEnabled` | `ResolveScaleToZeroEnabled`/`IsScaleToZeroEnabled` (`internal/config/scale_to_zero.go:68-86`) | inline override → per-model ConfigMap entry → ConfigMap `default` → `WVA_SCALE_TO_ZERO` env var → **system default `false`** | config-driven boolean gate, structurally analogous to `EnableRescale`/`EnableLimiter` but a *different* ConfigMap |
| 5a. If enabled, idle check | request count | `CollectModelRequestCount` (`internal/collector/registration/scale_to_zero.go:81-97`) — PromQL `sum(increase(vllm:request_success_total{...}[retentionPeriod]))` | query error → fail safe, keep current decisions (never falsely zero); `count > 0` → no change | **completed**-request counter — not EPP queue depth or arrival rate |
| 5b. If idle, zero everything | mutates `TargetReplicas=0` on every matching decision | `applyScaleToZeroOnDecisions` (`enforcer.go:78-124`) — loop matches `d.ModelID`+`d.Namespace` only, **`Role` not checked** | — | every variant/role of the model zeroed together in the same call — explicit design: "scaling prefill to zero while keeping decode makes the model non-functional" (`engine.go:727-730`) |
| 5c. If disabled and total already 0 | floats one variant back to `TargetReplicas=1` | `ensureMinimumReplicasOnDecisions` (`enforcer.go:129-180`) | triggered when the upstream optimizer already drove the model's replica total to 0 | picks the **cheapest** variant by `Cost` (tie-break: variant name) — this is the only "which one" selection logic anywhere in this mechanism, and it's the *opposite* operation |
| 6. Logging | — | `:1371-1374` | — | logs only if `scaledToZero==true` |

**Mutation scope.** Everything above only touches the in-memory `[]domain.VariantDecision` slice
(`TargetReplicas`, `Action`, reason fields) plus a Prometheus enforcer metric — never the Kubernetes
API directly. Downstream, `e.applySaturationDecisions` (`engine.go:1561+`, called once per reconcile
at `:571`) reads `decision.TargetReplicas` and writes it into `VariantAutoscaling.Status` (e.g.
`DesiredOptimizedAlloc.NumReplicas`) — see §5 for what happens after that.

**Answers, directly:**
1. **Optimizer-blind** — applies identically under CostAware or GreedyByScore; takes no optimizer-type argument, only a name string for logging.
2. **Config-gated, default off** — `EnableScaleToZero`/`WVA_SCALE_TO_ZERO`, precedence chain above.
3. **P/D: always together, never per-role** — confirmed by explicit code comment, not inferred.
4. **Variant selection: none on the zero-ing path** — every matching decision gets zeroed; the cheapest-variant selection only exists on the *opposite* (floor-to-1) path.
5. **EPP-blind, confirmed** — `modelData` carries `schedulerQueue`/`arrivalRate`, but this function's signature never receives them.

[↑ TOC](#toc)

---

## §4 The multi-variant/role gap

This is the sharpest finding in this doc and directly corrects the working assumption going in
("checks EPP queue at the model level and starts one pod from one of the variants").

**What actually happens today:** the EPP flow-control-queue check (§2 stage 4) is keyed *only* by
`ModelID`. The `optimize` loop (§2 stage 3) has no per-model grouping — it just fans out over every
currently-inactive VA cluster-wide. So if a model has, say, two accelerator variants and/or P/D
roles all at zero replicas, and the EPP shows a pending request for that model, **all of them**
pass the identical check on the same 100ms tick and **each independently** gets its own direct
scale-to-1 call (§2 stage 5) — concurrently, uncoordinated.

**This is a known, documented condition**, not a hidden bug: `docs/developer-guide/troubleshooting.md:69-71`
describes "many variants... scaled down to zero, causing the scale-from-zero engine to process
multiple scaling decisions simultaneously." The code carries its own acknowledgment
(`engine.go:317-318`, quoted in full in §2) that the intended behavior is to scale only the
lowest-cost variant, and that this is not yet implemented.

**Test coverage:** `test/e2e/scale_from_zero_test.go` only exercises single-deployment
(`-decode`-suffixed) scenarios. There is no e2e coverage of a multi-variant or multi-role
scale-from-zero interaction — the gap is untested as well as unresolved.

**What this means for the "does saturation-v2's capacity-store fallback ever get used for
scale-from-zero" question:** currently, no — it's moot, because scale-from-zero handles every
co-variant/role itself, directly, before the "normal" engine's zero-replica gate
(`prepareModelData`, `multi-analyzer-dataflow-map.md` §F3) would ever have a reason to re-engage for
that model. *If* the TODO above were fixed to scale only the cost-optimal variant, the remaining
co-variants would stay at zero replicas after that one variant starts — and at that point,
`prepareModelData`'s gate (keyed on aggregate `replicaMetrics` across the whole model, not
per-variant) would stop returning `nil` for the model as a whole, letting the normal analyzer
pipeline run and potentially size the remaining co-variants via saturation-v2's capacity-store
fallback (the exact mechanism flagged as unexercised-but-present in the main map's §F3 "partial"
case). That chain is structurally plausible but **not implemented or tested today** — it depends on
a fix to a TODO that doesn't exist yet.

**Addendum (2026-08-04) — the *other* partial-zero scenario, and why it's more robust than the
chain above.** The paragraph above reasons about *co-variants of a model that started at zero
together* (the multi-variant-role gap's own scenario). There's a structurally different case:
a variant that's individually at zero while its model siblings are *already, independently, live*
— e.g. a newly-added accelerator variant joining an already-serving model, or one variant that
organically drained to zero via the normal (non-enforcer) scale-down path while siblings stayed up.
For *this* case, scale-from-zero's per-VA-scoped trigger (§2 stage 2/4 — `isInactive` checks only
that VA's own replica count, no model-level pre-filter, confirmed in `filterVariantsByScaleTargetAccessor`)
means the engine reaches the *same* variant independently and revives it with the *same* hardcoded
`1` and EPP-queue check — **with zero dependence on any analyzer, capacity-store estimate, or the
TODO above being fixed.** This is a much more robust path than the multi-analyzer engine's own
attempt to handle the same scenario (which requires the binding analyzer to have — or fall back to
— a usable `PerReplicaCapacity` *estimate* for the zero-replica variant; see
`ta-anchor-refactor-review.md`'s "Partial scale-from-zero under `[TA]`-alone" section for the full
mechanism trace and the fragility that motivated relying on this engine as the near-term answer
instead). The one caveat carried over: this trigger is reactive (fires on actual EPP queueing), not
proactive like the analyzer path's `RequiredCapacity` signal would be.

[↑ TOC](#toc)

---

## §5 How the "normal" engine's decisions reach Kubernetes (RESOLVED — indirect, metrics-for-HPA/KEDA)

**Resolved 2026-08-04 by a direct re-trace of `applySaturationDecisions` (`engine.go:1561-1770`).**
The two framings that fed the DRAFT were never contradictory — they are two sequential legs of a
single *indirect* actuation path. The normal engine **never patches the Kubernetes scale
subresource itself** (that is scale-from-zero's exclusive mechanism, §2 stage 5). Instead:

1. **Stage the target into VA `.Status`.** `applySaturationDecisions` iterates **every** active VA
   in `vaMap` (`for vaName, va := range vaMap`, `:1576`), looks up its decision in an O(1)
   `decisionMap` keyed by `namespace/variantName` (`:1570-1573`), and writes the resolved target
   into an in-memory copy's `Status.DesiredOptimizedAlloc.{NumReplicas,Accelerator,LastRunTime}`
   (`:1687-1691`).
2. **Emit the external-scaler metric from that staged status.** `act.EmitMetrics(ctx, &updateVa)`
   (`:1747`) reads `Status.DesiredOptimizedAlloc.{NumReplicas,Accelerator}` and publishes the
   Prometheus replica-scaling signal that an external **HPA/KEDA** consumes and acts on
   (`:1725-1746`, "Always emit the replica scaling signal (the HPA/KEDA external metric)"). This is
   the genuinely *indirect* leg — WVA publishes a target; HPA/KEDA performs the actual scale
   mutation.
3. **Persist the CRD status separately.** CRD persistence of the same `.Status` happens later via
   the cache write (`DecisionCache.Set`) → controller patch path (comment `:1673-1679`), on a
   different track from the metric emission.

**Reconciliation:** VA.Status write + metric emission are **one pipeline, not two competing ones** —
the status is the durable target record, the emitted metric is how that target becomes a real
scaling action (via an external autoscaler), and the CRD patch persists the record. This is the
sharp contrast with scale-from-zero (§2 stage 5), which bypasses all of it with a synchronous
scale-subresource PATCH.

**Load-bearing do-nothing semantics (feeds the liveness/flapping discussion in §7 and the
anchor-refactor spec in `ta-anchor-refactor-review.md`).** When a VA has *no* decision on a tick,
`applySaturationDecisions` does **not** clear its target — it keeps the existing
`Status.DesiredOptimizedAlloc.NumReplicas` if `> 0`, else falls back to
`currentAllocations[vaName].NumReplicas`, else the live scale-target's replica count (`:1615-1650`),
under the explicit comment *"We effectively explicitly 'decide' to keep things as they are if no
decision was made."* Crucially it **still emits the metric** on that quiet tick (*"We should emit
metrics even if no decision changed, to keep HPA alive"*, `:1725-1726`). So a do-nothing
optimization cycle never drops the emitted target to zero — the previous target simply persists.
This confirms a do-nothing engine tick is **safe** (no spurious scale-down from a missing decision),
and it is precisely the mechanism the anchor-refactor's *"QM-as-error → do-nothing"* policy relies
on. The mirror-image error path is `emitSafetyNetMetrics` (`:1828+`, called at `:1001` before
`continue`), which on optimization *failure* emits "Strategy 1: previous desired replicas if
available", else current replicas — the same never-drop-to-zero-on-a-bad-tick guarantee.

[↑ TOC](#toc)

---

## §6 Cross-references to `multi-analyzer-dataflow-map.md`

- Directly resolves that doc's **§F3** ("the real mechanism, confirmed") — F3 correctly identified
  the `prepareModelData` EPP-blind gate as the reason the *normal* engine can't bootstrap a
  fully-zero model, and correctly separated the "partial" vs. "full" zero cases. This doc adds the
  missing piece: what *does* handle the full-zero case (a separate engine, §2), and shows it
  doesn't route through saturation-v2 at all — so F3's "if the full case needs to be in scope, the
  fix is at the `prepareModelData` gate" framing was answering the wrong question. The full case
  already has a handler; it just isn't the one F3 was looking at.
- Directly resolves that doc's **§D1** (TA has no scale-from-zero capability) and **§H1**
  (confirmation that the anchor/binding mechanism doesn't touch scale-from/to-zero) — both stand
  unchanged; this doc adds that scale-from-zero doesn't depend on *any* analyzer, TA or sat-v2, so
  D1's finding is in one sense moot for the *full*-zero case (§4) and only bites in the *partial*
  case, which is unaffected by anything in this doc.
- **§F4** (scale-to-zero, previously "not traced, Dean's own examination in progress") — now fully
  traced in §3 above; F4's placeholder in the other doc should be treated as superseded by this
  document rather than updated in place, to avoid duplicating content across two docs.

[↑ TOC](#toc)

---

## §7 Candidate follow-ups

- **The multi-variant/role scale-from-zero TODO (§4)** is the most consequential open item — it's a
  real, acknowledged gap with cluster-wide behavioral impact (every co-variant/role scaling
  independently on the same tick) and zero e2e coverage for the multi-variant/P/D case.
- **~~§5's actuation-path reconciliation~~ — RESOLVED 2026-08-04** (see §5). The normal engine's
  decisions reach Kubernetes *indirectly*: `applySaturationDecisions` stages the target into VA
  `.Status.DesiredOptimizedAlloc`, `act.EmitMetrics` emits the Prometheus replica-scaling metric an
  external HPA/KEDA acts on, and the CRD status is persisted separately via the cache→controller
  patch path. No direct scale-subresource patch (that's scale-from-zero only). No longer open.
- **No cooldown / debounce / stabilization anywhere in the scaling pipeline (confirmed gap,
  2026-08-04).** A targeted `grep -rn -i "cooldown\|grace.period\|stabiliz\|debounce\|flap"` across
  `internal/engines/saturation`, `internal/engines/pipeline`, and `internal/engines/scalefromzero`
  returns **zero hits** — none of the three engines implements any anti-flapping delay of its own.
  What *does* exist is passive, not active: (a) the normal engine's do-nothing tick preserves the
  previous target rather than dropping it (§5), so a *missing* decision never causes a scale-down;
  and (b) any real stabilization must come from the **external HPA/KEDA** the emitted metric feeds
  (HPA has its own `stabilizationWindowSeconds`), which is outside WVA's code. The two consequences
  worth recording: **scale-from-zero has no such external backstop** — it direct-patches the scale
  subresource on a 100ms tick with no cooldown and no reference to `PendingReplicas`/`ReadyReplicas`
  (confirmed: `scalefromzero` never reads either field), so a model whose EPP queue oscillates
  around the threshold can be re-triggered rapidly; and **the anchor-refactor introduces no new
  flapping risk** but also inherits no new protection — any oscillation concern for a TA-driven
  target still rides entirely on the downstream HPA/KEDA stabilization window. This is a documented
  known limitation, not a blocker for the refactor.
- **The stale `saturation/engine.go:1679` comment** referencing `common.DecisionCache` as a
  "controller patch path" for the normal engine (§2, stage 6) — appears to describe something that
  isn't real for that engine (the cache is scale-from-zero-only). Same flavor of doc-accuracy issue
  as the stale comment already found in `multi-analyzer-dataflow-map.md` §5 — a documentation bug,
  not something this doc's role should fix directly.
- Neither investigation was asked to check whether scale-from-zero and the "normal" engine could
  ever race — e.g. scale-from-zero direct-patching a Deployment to 1 replica at the same moment the
  normal engine's HPA/KEDA-facing metrics path is independently trying to set a different target.
  Not raised by either trace; flagging as an unasked question rather than a known-absent risk.

[↑ TOC](#toc)
