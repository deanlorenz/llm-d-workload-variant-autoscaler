# TA Demand → Model-Level Arrival Rate — Type 3 Task Plan (PR C)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-model-level-demand` off `main` (`f5b7577c`)
**Size:** 1 model-level query + plumbing + TA demand rewire · **Reviewer session:** yes (demand semantics)

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L21:50
- [Design decisions (resolved) {#decisions}](#design-decisions-resolved-decisions) L51:83
- [Deferred / out of scope {#deferred}](#deferred--out-of-scope-deferred) L84:108
- [Commit 1 — model-level arrival query + plumbing {#commit-1}](#commit-1--model-level-arrival-query--plumbing-commit-1) L109:150
- [Commit 2 — TA demand uses model-level arrival {#commit-2}](#commit-2--ta-demand-uses-model-level-arrival-commit-2) L151:187
- [Tests to add {#tests}](#tests-to-add-tests) L188:209
- [Developer guide {#devguide}](#developer-guide-devguide) L210:223
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L224:236

## Overview {#overview}

**TA's decode demand is a model-level quantity** and should be computed from the
**model-level arrival rate**, per the high-level design:

- TA-overview.md:26 — *"WVA Analyzers measure **demand per model** and supply per instance."*
- TA-demand.md §3.3 — `λ_dec,v = λ_v · avgOL_v`; §3.5 — `Λ_req,v = Σ_r λ_req,v,r`.

The code today computes decode demand by summing **per-pod** `ArrivalRate_r × AvgOutputTokens_r`
inside `computeDemand`
([throughput/analyzer.go:530](../Main/internal/engines/analyzers/throughput/analyzer.go#L530)).
That per-pod path depends on the EPP scheduler-dispatch metric being merged onto each vLLM
per-instance entry — a fragile cross-source key match (EPP `pod_name:port` vs vLLM
`instance`-derived `pod:port`) that orphans and drops the arrival rate when the ports differ.
That merge failure is the likely cause of the benchmark's **V2+TA running but no scale-up**.

**Fix:** fetch the arrival rate as a single **model-level** query
(`sum by (namespace) (rate(inference_extension_scheduler_attempts_total{…}))`), which has
**no `pod`/`port`/`instance` labels to reconcile** — the entire per-instance merge problem
disappears — and compute `TotalDemand`'s decode term as `Λ_req × avgOL` at the model level,
combined with the existing queue-drain term. This yields the same `Λ_req` the per-pod sum was
supposed to produce (TA-demand §3.5), just without the attribution fragility.

**Supply is not touched.** `computeVariantSupply`
([analyzer.go:606](../Main/internal/engines/analyzers/throughput/analyzer.go#L606)) derives
per-replica capacity from the fitted ITL model and measured KV at a fixed `DefaultKSat`
(`nSat/itlSat`); it never reads arrival rate. So arrival→0 does not affect supply/PRC.

[↑ TOC](#toc)

## Design decisions (resolved) {#decisions}

These were settled in review — treat as fixed constraints, not open choices:

1. **Model-level arrival, no witness.** A model-level `sum(rate(...))` cannot partially
   mis-attribute — it either matches the model filter (correct) or returns zero (filter/EPP
   absent). It is all-or-nothing, so **no `request_prompt_tokens_count` witness is needed.**
   (An earlier draft proposed one; it is unnecessary once demand is model-level.)

2. **Do NOT remove `ReplicaMetrics.ArrivalRate` or its per-pod collection loop.** The per-pod
   scheduler-dispatch loop and `ReplicaMetrics.ArrivalRate` are still consumed by
   `queueingmodel` ([queueingmodel/analyzer.go](../Main/internal/engines/analyzers/queueingmodel/analyzer.go))
   and `internal/utils/allocation.go`. Leave both in place. This PR only changes **what TA's
   demand reads** — TA stops using per-pod `ArrivalRate` and reads the new model-level value.

3. **Combine the EPP queue-drain term correctly at model level.** The queue term is not an
   RPS — `estimateQueueDemand` converts a queued-request *count* into a decode token rate via
   the drain-rate calc (`QueueSize / (drainFactor × ITL(k_sat))`,
   [analyzer.go:585](../Main/internal/engines/analyzers/throughput/analyzer.go#L585)). It is
   already added once at model level (`totalDemand += queueDemand`, L360) and role-distributed
   (`distributeQueueDemandByRole`, L361). The new model-level arrival decode term must be
   combined **alongside** it — not folded into it, not double-counted — preserving the
   per-role linearity invariant that the queue distribution maintains.

4. **No `max`, no served-rate floor.** Arrival is the signal (it lets TA preempt saturation);
   a draining engine keeps served rate > 0 after arrivals stop, and using that as a floor
   would wrongly hold demand up and block scale-down. Arrival→0 must be allowed to reduce
   demand.

5. **Supply / k\* / PRC untouched** (see Overview).

[↑ TOC](#toc)

## Deferred / out of scope {#deferred}

Document these in the handoff (do not silently drop — CONVENTIONS deletion/deferral rule):

- **DEFERRED — arrival-driven operating knee `k_knee` (TA-supply.md §5.5).** Not implemented
  today and **not** added here. Current code handles only `k_sat` (capacity = decode rate at
  the fixed `DefaultKSat`, via `ITL(k_sat)`). `k_knee` is the prefill-vs-decode limit (decode
  throughput insufficient to keep up with the prefill rate); it is a separate fix beyond
  first-phase TA, expected to matter only for prefill-heavy workloads and likely already
  covered by saturation_v2's K2 metric. Record as a future-phase item.

- **DEFERRED — `computeDemand` per-replica A→B→k\*local fallback.** Leave the existing fallback
  code ([analyzer.go:530-554](../Main/internal/engines/analyzers/throughput/analyzer.go#L530))
  **as-is** for now. After the move to model-level demand it may no longer be exercised on the
  primary path; it does not affect supply and does not affect model-level demand. Do **not**
  remove or redesign it in this PR — revisit when `k_knee` is implemented. If the model-level
  primary makes any of it dead, note that in the handoff rather than deleting.

- **DROPPED from TA scope — per-instance arrival merge (former I-1).** With demand model-level,
  TA no longer needs per-instance arrival attribution, so the collector per-instance merge fix
  is not part of TA's path. It remains relevant only to `queueingmodel` (separately
  half-broken) — track as a QM-scoped follow-up, not a TA blocker.

- **PARALLEL FACT-FIND (separate agent, run alongside coding — NOT a blocker).** Verify the
  semantics of `inference_extension_scheduler_attempts_total` against the EPP
  (gateway-api-inference-extension) source on GitHub before fully trusting it as the arrival
  signal. Key questions: (1) incremented **per request forwarded** or **per scheduling attempt**
  (retries → over-count)? (2) what `status` values exist; does `status="success"` == dispatched
  to a model endpoint? (3) are EPP-queued (not-yet-dispatched) requests excluded? (4) exact label
  set (`pod_name`/`port`/`target_model_name`/`model_name`/`namespace`/`instance`) and whether
  `pod_name`/`port` identify the target engine or the EPP; (5) any cleaner "requests forwarded"
  counter; (6) EPP version caveats. If it turns out to count per-attempt (not per-request), the
  model-level rate over-reads and the plan needs revisiting. Launch as a read-only research agent
  when coding starts.

[↑ TOC](#toc)

## Commit 1 — model-level arrival query + plumbing {#commit-1}

Mirror the existing model-level `SchedulerQueue` plumbing exactly.

1. **Register a model-level arrival query.** In the collector registration (near
   `QuerySchedulerDispatchRate`,
   [queueing_model.go](../Main/internal/collector/registration/queueing_model.go), or a
   saturation-scoped file if that is where model-level queries live), add e.g.
   `QueryModelArrivalRate` with template:
   ```
   sum by (namespace) (rate(inference_extension_scheduler_attempts_total{status="success",namespace="{{.namespace}}",target_model_name="{{.modelID}}"}[1m]))
     or sum by (namespace) (rate(inference_extension_scheduler_attempts_total{status="success",namespace="{{.namespace}}",model_name="{{.modelID}}",target_model_name=""}[1m]))
   ```
   Same `status="success"` filter and the same `target_model_name`/`model_name` `or` fallback
   as the per-pod query — only the groupby changes (drop `pod_name`, `port`).

2. **Collect it model-level.** Mirror `CollectSchedulerQueueMetrics`
   ([replica_metrics.go:1027](../Main/internal/collector/replica_metrics.go#L1027)) — either a
   sibling `CollectModelArrivalRate(ctx, modelID)` or fold it into the same model-level collect
   that already runs there. Return a scalar (req/s).

3. **Plumb onto `AnalyzerInput`.** Add a field to `AnalyzerInput`
   ([domain/analyzer.go:32](../Main/internal/domain/analyzer.go#L32)) — e.g.
   `ArrivalRate float64` (model-level, req/s; document units in the field comment). Populate it
   where `SchedulerQueue` is set for the analyzer input (engine.go ~L1408 collect;
   [engine_v2.go:58](../Main/internal/engines/saturation/engine_v2.go#L58) and :121 input
   construction). Both V1 and V2 input-construction sites must set it (grep `SchedulerQueue:`).

No behavior change to demand yet — Commit 2 consumes it.

**Commit message:**
```
collector: add model-level request arrival rate for the throughput analyzer

Add a model-level sum(rate(inference_extension_scheduler_attempts_total)) query
and plumb it onto AnalyzerInput alongside SchedulerQueue. Model-level arrival
has no per-pod/port labels to reconcile, unlike the per-pod dispatch-rate metric.
Not yet consumed — Commit 2 switches TA demand to it.
```

[↑ TOC](#toc)

## Commit 2 — TA demand uses model-level arrival {#commit-2}

Rewire TA's decode demand from the per-pod sum to the model-level value.

- **Decode demand (model level):** `λ_dec = input.ArrivalRate × avgOL`, where `avgOL` is the
  model-level average output length (the `averageShapeMetrics` OL,
  [analyzer.go:637](../Main/internal/engines/analyzers/throughput/analyzer.go#L637), already
  RequestRate-weighted). This replaces the per-variant `computeDemand(variantMetrics)` arrival
  contribution.
- **Combine with the queue term at model level** (decision #3): `TotalDemand = λ_dec +
  queueDemand`, distributing both across roles so the per-role linearity invariant holds. Reuse
  / generalize `distributeQueueDemandByRole` (L781) — do not invent a second distribution path.
- **Per-variant vs model-level attribution** is the key implementation decision: TA currently
  builds `TotalDemand` by summing per-variant `computeDemand` results (`SumTotalDemand`, L348).
  With model-level arrival there is one `Λ`; attribute it across roles/variants the same way the
  queue term is (a model-level quantity, role-distributed), so `SumTotalDemand(arrival) + queue`
  becomes `arrival_decode + queue`, both role-distributed. Preserve: model-level `TotalDemand`
  and per-role `RoleCapacities[*]` linearity.
- **Fallback (deferred):** keep `computeDemand`'s B/k\*local code as-is; if the model-level
  primary makes the per-replica arrival branch dead, note it in the handoff — do not delete in
  this PR.
- **`isEPP` / `anyEPP`:** derive "EPP present" from `input.ArrivalRate > 0` now (model-level)
  rather than per-replica; keep the existing downstream use intact.

**Commit message:**
```
throughput: compute decode demand from model-level arrival rate

TA decode demand is a model-level quantity (Λ_req × avgOL); compute it from the
model-level arrival rate instead of summing per-pod ArrivalRate, which depended
on a fragile EPP↔vLLM per-instance key merge. The scheduler-queue drain term is
combined at model level as before. ReplicaMetrics.ArrivalRate is retained for
queueingmodel/allocation. Supply is unchanged (arrival-independent).
```

[↑ TOC](#toc)

## Tests to add {#tests}

In the throughput analyzer test suite (match existing style; no cluster needed):
1. **Model-level demand.** Given `input.ArrivalRate = R` and a model with avgOL = L, assert
   `TotalDemand`'s decode component == `R × L` (plus queue term when present). Independent of
   how per-pod `ReplicaMetrics.ArrivalRate` is populated.
2. **Per-pod ArrivalRate no longer needed for TA demand.** With per-pod `ReplicaMetrics.ArrivalRate = 0`
   but `input.ArrivalRate > 0`, TA still produces demand (the old per-pod-orphan failure no
   longer zeroes TA). This is the regression backstop for the benchmark no-scale-up symptom.
3. **Queue term still added once, role-distributed.** With both `input.ArrivalRate` and a
   non-nil `SchedulerQueue`, `TotalDemand == λ_dec + queueDemand` and per-role sums are
   consistent (no double-count, linearity holds).
4. **Arrival→0 reduces demand.** `input.ArrivalRate = 0`, non-zero supply → decode demand from
   arrival is 0 (no served-rate floor); confirm no spurious demand.
5. **Regression guard for other consumers:** a collector test asserting
   `ReplicaMetrics.ArrivalRate` is still populated per-pod (queueingmodel/allocation depend on
   it) — so this PR doesn't silently break them.

Run with `-race` where maps are involved.

[↑ TOC](#toc)

## Developer guide {#devguide}

**Target:** `docs/developer-guide/throughput-analyzer.md`, **Demand Estimation section**
(~L443-501). PR A (`ta-devguide-fixes`) owns the Metrics/PromQL, Package, and Supply sections
in parallel — stay out of those.

Update the demand description to state: decode demand is model-level, `Λ_req × avgOL`, from a
model-level `sum(rate(scheduler_attempts))` (not per-pod), combined with the scheduler-queue
drain-rate term; note that `ReplicaMetrics.ArrivalRate` (per-pod) is retained for other
consumers but no longer drives TA demand; note `k_knee`/arrival-driven saturation is not
implemented (future phase). Describe current code only (Type 4).

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

1. `git branch --show-current` → `ta-model-level-demand`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (incl. the model-level demand + retained-field regression tests).
4. `make lint` — clean.
5. DCO sign-off on every commit (`git commit -s`).
6. `go build ./...` — clean.

When green, write `plans/session/handoffs/review__ta-model-level-demand-ready.md` and stop.
Do not push.

[↑ TOC](#toc)
