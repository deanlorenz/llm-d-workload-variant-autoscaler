# TA Demand → Model-Level Arrival Rate — Type 3 Task Plan (PR C)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-model-level-demand` off `main` (`f5b7577c`; round-2 rebases onto `upstream/main` `28a58b77` — see [C.0 {#c0}](#c0--rebase-onto-current-upstreammain-first-c0))
**Size:** 1 model-level query + plumbing + TA demand rewire · **Reviewer session:** yes (demand semantics)

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L25:54
- [Design decisions (resolved) {#decisions}](#design-decisions-resolved-decisions) L55:94
- [Deferred / out of scope {#deferred}](#deferred--out-of-scope-deferred) L95:138
- [Commit 1 — model-level arrival query + plumbing {#commit-1}](#commit-1--model-level-arrival-query--plumbing-commit-1) L139:190
- [Commit 2 — TA demand uses model-level arrival {#commit-2}](#commit-2--ta-demand-uses-model-level-arrival-commit-2) L191:227
- [Tests to add {#tests}](#tests-to-add-tests) L228:249
- [Developer guide {#devguide}](#developer-guide-devguide) L250:263
- [Review follow-ups (ev-shindin PR #1480 comments) {#followups}](#review-follow-ups-ev-shindin-pr-1480-comments-followups) L264:370
  - [C.0 — Rebase onto current upstream/main FIRST {#c0}](#c0--rebase-onto-current-upstreammain-first-c0) L274:325
  - [C.1 — document why a zero/absent arrival signal is safe (comment) {#c1}](#c1--document-why-a-zeroabsent-arrival-signal-is-safe-comment-c1) L326:345
  - [C.2 — document why RequestRate is not used as a broken-arrival cross-check (comment) {#c2}](#c2--document-why-requestrate-is-not-used-as-a-broken-arrival-cross-check-comment-c2) L346:370
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L371:383

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

2a. **Do NOT touch QM's registration file (`queueing_model.go`) at all.** This PR adds a new,
   TA-exclusive query — it must be registered through TA's own registration file
   (`throughput_analyzer.go`, see Commit 1), never inside `queueing_model.go`, even though both
   queries read the same underlying source metric. QM's registration is QM's to own; TA needing
   a new metric is not a reason to add to or modify QM's file. This is a boundary rule, not a
   functional-safety one — QM's own query/collection path is covered by decision 2 above.

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

- **RESOLVED — EPP-metric fact-find complete (2026-07-26, planner-run, read-only).** The
  semantics of `inference_extension_scheduler_attempts_total` were verified against the EPP 0.9
  source (llm-d-router's own fork, `LLM_D_ROUTER_VERSION=v0.9.0`). Headline: **the metric is
  deprecated in 0.9**, renamed to `llm_d_epp_scheduler_attempts_total` — both are dual-written
  today, so this plan's query works unchanged; migrating to the new name is tracked as a
  separate, not-yet-filed "0.9 EPP metric rename" issue, out of scope for this PR. Signal
  confirmed sound: counted **per request**, not per retry (`Schedule()` runs once per request,
  no retry loop); `status="success"` means dispatched to a target pod; EPP-queued/rejected
  requests are correctly excluded (admission runs before scheduling). The model-level
  `sum by (namespace)` query is unaffected by 0.9's `pod_name`→`endpoint_name` rename (this
  query carries no pod label). One concrete fix landed in Commit 1 below: this metric has **no
  `model_name` label** on any EPP version examined, so the `model_name` fallback clause in the
  original template was inert (matched zero series) — removed. Known limitation, not a
  blocker: `status="success"` measures dispatched/served arrivals, so under hard queue-capacity
  shedding the signal plateaus and can understate true demand; the queue-drain term partially
  compensates, but requests rejected at queue capacity are invisible to both. Full findings in
  the consumed handoff (`session/handoffs/plan__epp-metric-factfind.md`, folded in here and in
  `CURRENT.md`).

[↑ TOC](#toc)

## Commit 1 — model-level arrival query + plumbing {#commit-1}

Mirror the existing model-level `SchedulerQueue` plumbing exactly.

1. **Register a model-level arrival query — in TA's own registration file, not QM's.**
   Add it to
   [throughput_analyzer.go](../Main/internal/collector/registration/throughput_analyzer.go)'s
   `RegisterThroughputAnalyzerQueries`, alongside `QueryGenerationTokenRate`/`QueryKvUsageInstant`/
   `QueryRequestRate`. **Do not add it to `queueing_model.go`**, even though the underlying source
   metric (`inference_extension_scheduler_attempts_total`) is the same one
   `QuerySchedulerDispatchRate` reads there — this query is TA-exclusive (no other analyzer
   consumes it), and `throughput_analyzer.go`'s own header comment states the file's purpose
   exactly: "queries that are genuinely new and not provided by other analyzer registrations."
   Splicing a TA-only query into QM's registration file entangles ownership even though it would
   be functionally harmless (additive, doesn't touch `QuerySchedulerDispatchRate` or QM's
   per-pod `ArrivalRate` path). Add e.g. `QueryModelArrivalRate` with template:
   ```
   sum by (namespace) (rate(inference_extension_scheduler_attempts_total{status="success",namespace="{{.namespace}}",target_model_name="{{.modelID}}"}[1m]))
   ```
   Same `status="success"` filter as the per-pod query; groupby drops `pod_name`/`port`. **No
   `model_name` fallback clause** — the EPP-metric fact-find verified against the EPP 0.9 source
   that `inference_extension_scheduler_attempts_total` has never carried a `model_name` label
   (only `target_model_name`), so a `model_name=...` filter on this metric matches zero series.
   Do not copy the `model_name`/`target_model_name` `or` pattern from other queries (e.g. the
   flow-control queue metric, which does carry `model_name`) onto this one.

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

## Review follow-ups (ev-shindin PR #1480 comments) {#followups}

Locked by Dean 2026-07-29. ev-shindin raised two points about the no-EPP / zero-arrival case.
**Both resolve to comment-only additions on C** — the behavior is already correct by design; the
comments make the intent legible at the code so a future reader (or reviewer) does not
re-litigate it. No logic change on C. The active broken-arrival *detection* lives in the
throughput analyzer's engine liveness path (the demand-liveness detector), authored as a separate
fold on the `ta-veto-liveness` branch — **do not implement any detector here**, and do not
reference other branches/PRs by identifier in the code comment (§4a); describe behavior in prose.

### C.0 — Rebase onto current upstream/main FIRST {#c0}

**Dean explicitly authorized this rebase (2026-07-29).** Normally an open-PR branch does not chase
`main`; here Dean directed it because `main` advanced materially since this branch's base and the
comment folds must land on current code. This authorization is specific to the C/D round-2 work —
it does not generalize.

**Target.** Rebase `ta-model-level-demand` onto `upstream/main` (currently `28a58b77`). The branch's
merge-base is `11d70a8a` (the #1479 merge); the replayed base gains the four commits in
`11d70a8a..upstream/main`:

- `2fd5fa53` (#1473) — Makefile `BENCHMARK_WORKLOAD` default; no code impact.
- `6436f2b1` (#1450) — **rename `internal/saturation` → `internal/saturationv1`**.
- `bf8fd8d9` (#1448) — **move surviving `pkg/` packages → `internal/queueing`**.
- `28a58b77` (#1487) — **wire `GLOBAL_OPT_INTERVAL` into the optimize loop**.

**What this branch's edit targets do / don't hit** (verified live against `upstream/main`):

- C's core edit site `internal/engines/analyzers/throughput/analyzer.go` is **unchanged in path**;
  `internal/domain/analyzer.go` and `internal/engines/saturation/engine_v2.go` likewise. So the
  #1450/#1448 renames do **not** move C's edit sites — but if C's model-level arrival query or its
  plumbing imports anything that lived under `pkg/` (now `internal/queueing`) or under
  `internal/saturation` (now `internal/saturationv1`), those imports need the new path. Import-path
  churn, not a logic change.
- The two round-2 additions are **comment-only** (C.1, C.2) — no behavior to re-verify against
  #1487 beyond a clean `go build ./...` after the rebase. Still run the full per-file diff /
  per-commit checks below for the *pre-existing* C commits, since git's three-way merge can drop a
  hunk under conflict.

**Procedure** (CONVENTIONS non-trivial-rebase rule applies — multi-commit stack, touched files may
import moved packages):

1. Before rebasing, write the pre-rebase plan in **your status file**
   (`plans/session/status/ta-model-level-demand.md`) — you have no write access to `planning/`.
   List the existing C commits with a one-line "behavior to preserve" each, the files you expect to
   conflict (import-path churn from #1450/#1448), and the post-rebase checklist.
2. After the rebase: per-file `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` for every
   touched file; confirm every claimed behavior survived.
3. Per-commit message-vs-diff check.
4. **Re-verify every anchor this plan cites** (`throughput/analyzer.go` line numbers, the Commit 2
   demand-assembly site, the `anyEPP := input.ArrivalRate > 0` derivation) — line numbers shift
   under rebase; re-grep before adding the comments.

Rebasing rewrites this branch's history, so the eventual push is `--force-with-lease` — **Dean
confirms that separately at push time; do not push.** Hand back in your status file rather than
forcing a conflict you cannot resolve cleanly.

Note: after #1448 the `./pkg/...` path in the pre-push `gofmt` line may no longer exist — expected;
`./internal/...` now covers the moved packages.

[↑ TOC](#toc)

### C.1 — document why a zero/absent arrival signal is safe (comment) {#c1}

**Point.** ev-shindin flagged that with no EPP (arrival = 0), TA could look like it wants to scale
down spuriously. **Resolution (Dean): harmless, no code change** — this is the intended behavior
already analyzed when demand moved per-pod → model-level:

- With no served-rate floor (decision #4), `ArrivalRate = 0 → TotalDemand = 0`. Zero demand only
  ever *permits* scale-down; it never *forces* a scale action and never triggers scale-up. So a
  missing or zero arrival signal cannot cause a spurious scale-up, and cannot by itself force a
  scale-down (the multi-analyzer all-live-agree gate still governs that).

**Coder action (comment only).** Near the model-level demand assembly (Commit 2 site, where
`TotalDemand` is composed from `input.ArrivalRate × avgOL + queueDemand`), add a short prose
comment stating: arrival rate is the demand signal; when it is zero (e.g. EPP absent or not yet
scraped) demand is legitimately zero, which permits but never forces scale-down and never drives
scale-up — so a zero/absent arrival signal is safe here and is intentionally **not** floored to a
served-rate proxy. Current-code prose; no plans-branch refs.

[↑ TOC](#toc)

### C.2 — document why RequestRate is not used as a broken-arrival cross-check (comment) {#c2}

**Point.** ev-shindin proposed warning when `ArrivalRate == 0` while some other signal
(`ΣRequestRate`, KV, waiting) is non-zero — "then arrival is broken." **Resolution (Dean): do
NOT add that cross-check on C**, because the naive form produces false positives:

- `domain.ReplicaMetrics.RequestRate` is a request **completion / processed** rate (req/s served),
  **not** an arrival rate. A draining engine keeps `RequestRate > 0` after arrivals have legitimately
  gone to zero, so `ArrivalRate == 0 && ΣRequestRate > 0` is a **normal drain state**, not a fault
  — warning on it would fire constantly during ramp-down. (RequestRate sourced from EPP is also not
  validated for this use.)
- The correct broken-arrival signal is **temporal, not instantaneous**: "supply has been live but
  demand has never been observed for a full staleness window." That is detected as an
  observability-only warning in the throughput analyzer's engine liveness path (the demand-liveness
  latch), not in the per-cycle demand math here.

**Coder action (comment only).** At the `anyEPP := input.ArrivalRate > 0` derivation (Commit 2),
add a short prose comment: EPP-presence is derived from the model-level arrival rate; the per-pod
`ReplicaMetrics.RequestRate` (a completion rate, non-zero during drain) is deliberately **not**
used as a cross-check here because it would false-positive on legitimate drain — durable
"live supply, never-seen demand" is surfaced as a warning in the engine liveness path instead.
Current-code prose; no plans-branch/PR refs.

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
