# PR #1501 review — rate-anchored k2 for saturation-v2

**Status: FINAL** — reviewed 2026-07-30; **COMMENTED review posted** by deanlorenz (15:54:47Z). Two asks raised (F1 gate registration on the switch; F2 rebase onto current main); NTHs noted as minor/non-blocking. Draft body: `scratch/pr-1501-review-body.md`.

**Scope:** internal review, local only. No `/code-review` skill, no GitHub posting.
**PR:** #1501 — rate-anchored compute-capacity (`k2`) estimator for the V2 saturation analyzer, behind a build-time switch.
**Reviewed ref:** `refs/review/pr-1501`.
**True base (merge-base with `upstream/main`):** `f5261c8e`. **All diffs below are against that base**, not the moving `upstream/main` tip — see F2.

---

## What the PR does

Fixes #1500: occupancy-based `k2` records `tokensInUse` (a KV *stock*) as a stand-in for a rate limit. On prefill-heavy traffic the engine queues at ~16% KV utilization, so `demand/supply` mis-reads as abundant headroom → controller sheds to one replica and cycles.

The fix adds a **rate-anchored** `k2` estimator: a replica is "at its limit" when queue ≥ `QueueLengthThreshold` **or** arrival rate λ reaches measured service rate μ. At that moment the resident token count is stored **per workload bucket** (`model|accelerator|role|gpuCount|inputBucket|outputBucket`) as a running MINIMUM ceiling; every replica of a bucket reads the same value so `aggregateByVariant`'s median becomes a no-op (prevents an idle sibling from lifting variant capacity and re-introducing shed-to-one).

Gated by `const EnableRateAnchoredK2 = false` (build-time, deliberately not a ConfigMap key). With it false the stores are never allocated and the estimator returns immediately.

**Files (against base `f5261c8e`):** 9 files, +1486/−54.
- `docs/plans/engine/rate-anchored-k2.md` (+220, new) — design doc.
- `internal/engines/analyzers/saturation_v2/rate_capacity.go` (+500, new) — estimator + stores.
- `internal/engines/analyzers/saturation_v2/{analyzer.go,types.go}` — wiring + two new `k2Source` labels.
- `internal/engines/analyzers/saturation_v2/rate_capacity{_test,_integration_test}.go` (+590) — tests.
- `internal/collector/registration/rate_capacity.go` (+106, new) — shared query registrar.
- `internal/collector/registration/throughput_analyzer.go` (+7/−44) — moves two query defs to the shared registrar.
- `internal/engines/saturation/engine.go` (+5) — calls `RegisterRateCapacityQueries` unconditionally in `NewEngine`.

---

## Highlights — key code changes

### Per-commit change map (7 commits, iterative on-branch development)

| Commit | What | Type |
|---|---|---|
| `f6839808` | feat: scaffold the whole feature — shared query registrar, `EnableRateAnchoredK2` switch, first `rateAnchoredK2()`, `computeK2` wiring, two `k2Source` labels, design doc, first tests | logic + doc + test |
| `4e98e5d1` | fix: require a *sustained* backlog before μ counts as a ceiling (don't anchor on a single transient queue spike) | logic + test |
| `e5a374c3` | fix: put λ and μ on the same time base — smooth λ over residence time `W` so instantaneous arrivals and completion-derived service rate are comparable | logic + test |
| `4fdf5cb9` | fix: scale rate-anchored `k2` by the same occupancy `demand` uses (`TokensInUse`), so estimator and demand share units | logic + test |
| `e3a57562` | fix: answer only at/past saturation, never while there is headroom (net −285 within own new code — replaced an earlier over-eager path) | logic + test |
| `5ac3d95f` | refactor: learn a per-**bucket** running-min ceiling instead of a per-cycle value (net −680 within own new code — the change that makes the variant median a no-op) | logic + test |
| `f4856bb1` | fix: bound both stores (prune-on-insert + eviction) and correct the plan doc | logic + doc + test |

No commit claims behavior in a file it does not touch. Intermediate commits revise each other's just-added code → **squash-merge**; commit-by-commit review would mislead.

### Out of scope (deliberately not in this PR)

- **No ConfigMap toggle** — the switch is a build-time `const` on purpose (estimator is under evaluation vs. the incumbent; not something to flip on a running cluster).
- **No demand-side change** — `demand` still reads `TokensInUse`; only the `k2` *supply* ceiling changes, and only when the flag is on.
- **No new PromQL** — reuses `QueryRequestRate`/`QueryKvUsageInstant` (moved to a shared registrar; see F1 for the execution-frequency side effect).
- **No incumbent removal** — the occupancy-based `computeK2` chain stays; the rate anchor is consulted *first* and falls through when it declines.

### Critical section — the one region that carries the PR's behavior

Everything else (stores, smoothing, eviction, labels) exists to feed these two blocks. With `EnableRateAnchoredK2 == false`, `a.serviceRates` is nil and the method returns at the first `if`, so the incumbent path is untouched.

**Wiring** — `analyzer.go` `computeReplicaCapacity`, immediately after `computeK2`:

```go
// Rate-anchored estimate takes precedence when enabled and answerable. It runs
// after computeK2 so the occupancy history keeps being maintained ...
if rateK2, rateSrc, ok := a.rateAnchoredK2(rm, modelID, role, gpuCount, k1, config.QueueLengthThreshold, time.Now()); ok {
    k2, k2Priority = rateK2, rateSrc
}
```

**Estimator** — `rate_capacity.go` `rateAnchoredK2` (detector decides *when*, measurement records *what*):

```go
if a.serviceRates == nil {           // flag off → whole feature dark
    return 0, 0, false
}
key := serviceRateKey(modelID, rm.AcceleratorName, role, gpuCount, rm.AvgInputTokens, rm.AvgOutputTokens)

// Detector: rates decide whether this replica is at its limit.
backlogged := float64(rm.QueueLength) >= queueThreshold
if backlogged && rm.RequestRate > 0 {
    a.serviceRates.ObserveRate(key, rm.RequestRate, now)
}
atLimit := backlogged || a.arrivalsReachedServiceRate(rm, key, now)

_, hadCeiling := a.serviceRates.Ceiling(key, now)   // label-only: fresh vs carried-over

// Measurement: at the limit, resident tokens are what the limit is worth.
occupancy := float64(rm.TokensInUse)
if atLimit && occupancy > 0 {
    a.serviceRates.ObserveCeiling(key, occupancy, now)   // running MIN per bucket
}

ceiling, ok := a.serviceRates.Ceiling(key, now)
if !ok {
    return 0, 0, false               // no measurement yet → decline, fall through to incumbent
}
src := k2SrcRateAnchored
if !hadCeiling {
    src = k2SrcRateBacklog
}
return clampCeiling(ceiling, k1), src, true   // floor-clamped; k2 = min(k1, k2) still applies
```

**Why the verdict follows from this:** the ceiling is stored per *bucket* as a running minimum and read identically by every replica of the bucket, so `aggregateByVariant`'s median collapses to that one value — which is exactly why an idle sibling can no longer lift variant capacity and re-trigger the shed-to-one loop #1500 describes. The two `if` guards (`serviceRates == nil`, and `!ok`) are the entire flag-off / not-yet-measured safety story.

---

## Findings

### F1 — Unconditional query registration adds real per-cycle Prometheus load in the DEFAULT (TA-off) config — LOW/MEDIUM (operational, not correctness)

**Mechanism (verified end-to-end):**
- `engine.go` `NewEngine` calls `RegisterRateCapacityQueries(...)` **unconditionally** (not gated by `EnableRateAnchoredK2`).
- `RegisterRateCapacityQueries` (`registration/rate_capacity.go:31-34`) registers `QueryKvUsageInstant` and `QueryRequestRate` (vLLM + SGLang) via `registerIfAbsent`.
- Both names are already in the **always-executed** `engineSpecificReplicaQueries` list (`engine_queries.go:31-32`, unchanged by the PR).
- `PrometheusSource.Refresh` runs `executeQuery` for every name in that list. `executeQuery` calls `registry.Build(name)`, which returns `"query %q not found"` for an **unregistered** name — and returns a `MetricResult` with `Error` set *before* any Prometheus HTTP call (`prometheus_source.go:127`). Downstream readers gate on `!result.HasError()`, so the fields stayed zero and **no HTTP query was sent**.

**Consequence:**
- **Pre-PR, TA off:** `Build` fails → the two queries never hit Prometheus.
- **Post-PR, TA off, flag off:** the two names are now registered → `Build` succeeds → **both queries execute every replica-collection cycle** and populate `podData[].kvUsageInstant`/`.requestRate`.
- With **TA on**, no change either way: TA registered them pre-PR; `registerIfAbsent` is a no-op post-PR (idempotent/order-independent — matches the doc's "either order works and neither panics").

So the only delta is **TA off**, which is the **default** deployment (TA is opt-in / off by default per the TA 0.9 work). Every default WVA deployment now issues two extra Prometheus queries per replica per collection cycle.

**Correctness impact: none.** No always-on consumer reads `rm.RequestRate`/`kvUsageInstant` when both TA and the flag are off:
- `rate_capacity.go` readers (`:431,:432,:478`) are gated by `a.serviceRates == nil` (stores allocated only when `EnableRateAnchoredK2`).
- `throughput/analyzer.go` readers (`:550,:649-653`) only run when TA is registered.
- The V2 demand path uses `TokensInUse` (from `QueryKvCacheUsage`, `max_over_time`), not these two fields.

So it is populated-but-unread fields + added Prometheus load, not a behavior/correctness bug.

**Tension with the PR's framing.** Work-item #2 says the switch is deliberately build-time and "with it false the service-rate store is never allocated and every path in the file returns immediately." That is true of the *estimator* but not of the *collector*: registration is unconditional and independent of `EnableRateAnchoredK2`. The doc discloses the unconditional **move** (metrics table "Today: throughput-analyzer only", and "removes [TA] as a dependency") and correctly says "No new PromQL," but does not state the operational **consequence** — extra query execution on the default config. `QueryKvUsageInstant` in particular is pure collateral here: neither the estimator (which reads `TokensInUse`, not instant-KV) nor anything else consumes it with TA off + flag off; it rides along only because the shared registrar bundles it with `QueryRequestRate`.

**Suggestion (discuss).** Gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` so the collector is also dark until the flag flips — matching the doc's own "returns immediately" promise and shipping *zero* query-load change in the default config. Trivial: the flag is build-time and registration happens at engine construction. If instead there is an intent to always collect μ (e.g. for future observability) regardless of the flag, state that explicitly in the doc and accept the cost as intentional.

### F2 — Branch is 3 commits behind `upstream/main`; rebase needed before merge — MEDIUM (merge hygiene)

Merge-base is `f5261c8e`; current `upstream/main` is 3 commits ahead:
- `1d5553ee` (#1502), `da58c0e0` (#1486 — ScalingPolicy schema Phase 1), `f9f04d81` (#1480).

**#1486 (`da58c0e0`) adds the `SetLimiterBuilder`/`refreshLimiter`/limiter-signature machinery to `internal/engines/saturation/engine.go`** — the same file the PR touches (`+5` in `NewEngine`). Diffing the PR against the moving tip (instead of the merge-base) shows a spurious "removal" of that machinery; it is an artifact of the stale base, **not** something the PR removes. On rebase, the PR's `RegisterRateCapacityQueries` call must land alongside #1486's limiter setup in `NewEngine`. Likely a clean adjacency (both append into `NewEngine`) but must be verified, and gates re-run, after rebase.

**Reviewer note for future PRs:** diff against `git merge-base upstream/main <ref>`, never the moving tip, or engine.go changes read as large phantom deletions.

---

## Confirmed correct / good

- **`k2Source` label semantics consistent** across `types.go`, `rateAnchoredK2`, and the design doc: `hadCeiling` false → `k2SrcRateBacklog` / `"RATE-now"` (measured this cycle); true → `k2SrcRateAnchored` / `"RATE-learned"` (carried over).
- **Estimator flag-off inertness verified:** `a.serviceRates == nil` early-return; stores allocated only when `EnableRateAnchoredK2 == true`. The estimator path is genuinely dead when the flag is off.
- **`registerIfAbsent` idempotency:** no double-registration and no panic regardless of TA/saturation registration order — matches doc claim.
- **Per-bucket running-MIN ceiling** read identically by all replicas of a bucket → variant-level median is a no-op → closes the idle-sibling shed-to-one regression. Design intent sound; a dedicated regression test asserts idle-sibling-equal-capacity.
- **Bounded growth:** prune-on-insert at `BucketPruneThreshold` + staleness eviction; test present.
- **Damping-by-construction constants** match the doc (`SaturationEnterRatio=0.95`, `ServiceRateDecayPerWindow=0.75`, `CeilingRelaxPerWindow=1.25`).
- **Commit messages match their diffs.** The 7 commits are iterative on-branch development (heavy rewriting — e.g. `e3a57562` −285, `5ac3d95f` −680 within the branch's own new code). No commit claims behavior in a file it does not touch. **Squash-merge is appropriate**; commit-by-commit review would mislead (intermediate commits revise each other).
- **Test coverage is thorough:** store rate/ceiling semantics, arrival smoothing, residence bounds, role/input isolation, oscillation stability, bounded growth, flag-off equivalence, post-drain divergence, floor clamp, NaN/negative survival, prefill-no-completions.

---

## NTH / minor

- **N1** — `QueryKvUsageInstant` is collateral in the shared registrar (no consumer with TA off + flag off). Dissolves if F1 is addressed by flag-gating registration; otherwise worth a one-line note in the doc that it rides along for the shared registrar's sake.
- **N2** — "No new PromQL" is accurate, but the metrics table's "Today" column would be clearer if it flagged that the TA-only rows change *execution frequency* (become unconditional per-cycle), not just registration location — the same point as F1, surfaced in the doc.
- **N3** — `computeReplicaCapacity` calls `rateAnchoredK2(..., time.Now())` at the call site rather than injecting a clock. Harmless (flag off in prod), but tests inject time into the stores directly while the wiring uses wall-clock — a seam that a future clock-injection refactor would want to close for end-to-end determinism.

---

## Open items for discussion

1. **F1 disposition** — flag-gate `RegisterRateCapacityQueries` (ship zero default-config change), or accept the added query load as intentional and document it? This is the one finding that could warrant a code change before merge.
2. **F2** — confirm the rebase onto current `upstream/main` reconciles `engine.go` `NewEngine` with #1486's limiter machinery cleanly; re-run gates.
3. Otherwise the PR looks sound: correct fix for #1500, genuinely inert estimator when the flag is off, strong tests. No correctness blockers found.
