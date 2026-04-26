# PR-3: Throughput Analyzer State Management

> **Status: COMPLETED** — Implemented in #1052. All components below were delivered
> as planned. Part of #1005; does not close it.

## Context

The metrics collection layer (PR-1/PR-2, #1051) registered three Prometheus queries for
the Throughput Analyzer and wired them into `ReplicaMetrics`. PR-3 creates the internal
Go package that stores and manages the data those metrics produce — per-variant workload
shape tracking, ITL observation windows, and sanity diagnostics.

**Scope: μ_dec vs λ_dec only. No OLS fit. No scaling signal. No changes to existing code.**

The OLS fit and scaling signal are PR-4. PR-3 builds the stateful substrate that PR-4
will extend. `Analyze()` is stubbed to return zero RC/SC.

---

## Key Design Decisions

### State is tracked per variant, not per model

Different variants may run on different hardware with different ITL characteristics.
All replicas of the same variant share IL/OL/KV_max (same hardware), while k naturally
varies across replicas under uneven load — providing the k-spread needed for OLS.
The variant key is `"namespace|modelID|variantName"`.

### Shape change tolerance triggers window reset

When the fleet-average IL or OL shifts by more than 20%, the observation window is
cleared. A fitted model calibrated at one workload shape (e.g., OL=200) is not valid
at a different shape (e.g., OL=400) because `ITL(k)` depends on concurrency, which
depends on KVreq, which depends on IL and OL.

### Observation window filters k ∈ [0.15, 0.85]

Below 0.15: KV utilization is too low for reliable ITL slope estimation (ITL barely
changes, noise dominates). Above 0.85: the system is near saturation where ITL is
non-linear. The fit needs samples in the linear operating range.

### ILeff used for KVreq (cache-aware)

`KVreq = ILeff + OL/2` where `ILeff = IL × (1 − PrefixHitRate)`. With EPP prefix
routing, a new replica warms its cache quickly and operates near fleet-average ILeff.
Using cold-cache IL would over-estimate KV demand per request and lead to over-scaling.
When prefix caching is disabled, `PrefixHitRate = 0` and `ILeff = IL` automatically.

### Pattern mirrors saturation_v2's two-store design

`saturation_v2` uses a rolling observation history per workload bucket and a persistent
knowledge store. PR-3 implements the observation history layer (`ObservationWindow`).
PR-4 adds the knowledge store (`itlKnowledgeStore`) using the same injection pattern.

---

## Components

### Package `internal/engines/analyzers/throughput/`

**`constants.go`** — All tunable thresholds in one place: `AnalyzerName`, shape
tolerance (20%), window size (20 samples), max observation age (30 min), readiness
criteria (10 samples, 30% k-spread), k bounds (0.15–0.85), and minimum token counts
for sanity checks.

**`types.go`** — Core data types:
- `WorkloadShape` — fleet-average (IL, OL, PrefixHitRate) plus derived `ILeff` and
  `KVreq`. `Within()` checks whether two shapes are within tolerance; `IsZero()` tests
  for uninitialized state.
- `ITLObservation` — a single `(k, ITL_obs, timestamp)` data point for the window.
- `SanityIssue` / `SanityReport` — six diagnostic tags (`no_replicas`,
  `missing_kv_capacity`, `kv_utilization_out_of_range`, `itl_non_positive`,
  `missing_shape_metrics`, `stale_metrics`). `SanityReport.OK()` returns true when
  no issues were found.

**`shape_tracker.go`** — `ShapeTracker` holds the current `WorkloadShape` and a
tolerance parameter. `Observe(il, ol, hitRate)` returns `(currentShape, shapeChanged)`.
The first call always sets the shape without triggering a change (nothing to compare).
Subsequent calls compare with `Within()` and return `shapeChanged=true` when the shift
exceeds tolerance. Callers use `shapeChanged` to decide whether to call `window.Clear()`.

**`observation_window.go`** — `ObservationWindow` holds a bounded, time-limited slice
of `ITLObservation`. `Add(k, itl, ts)` appends if `k ∈ [minK, maxK]`; at capacity,
the oldest observation is evicted. `Prune(now)` removes observations older than
`maxAge`. `Ready()` returns true when `len >= minSamples` AND
`KSpread() >= minKSpread`. `Observations()` returns a copy for use by the OLS fitter.
`Clear()` resets the window on shape change.

**`sanity.go`** — `CheckModelMetrics([]ReplicaMetrics)` validates all replica metrics
for one reconcile cycle. Each of the six issue types is checked per pod; the report
aggregates issue types and affected pod names. Callers should skip `Observe` for
variants with `!report.OK()`.

**`analyzer.go`** — `ThroughputAnalyzer` holds a mutex-protected map of per-variant
state (`ShapeTracker` + `ObservationWindow` + last `SanityReport`). `Observe()` groups
replicas by variant, runs sanity checks, feeds shape and (k, ITL) observations, and
prunes stale window entries. `Analyze()` calls `Observe()` then returns zero RC/SC
(stub for PR-4). `VariantState()` returns a read-only snapshot used in tests.

---

## Data Flow (Observe)

```
metrics []ReplicaMetrics
    │
    ├── group by VariantName
    └── for each variant:
            CheckModelMetrics → SanityReport
            if !OK: skip
            │
            fleet-average IL, OL, hitRate
            │
            ShapeTracker.Observe → (shape, changed)
            if changed: ObservationWindow.Clear()
            │
            for each replica:
                ObservationWindow.Add(KvUtilization, AvgITL, now)
            ObservationWindow.Prune(now)
```

---

## Tests

78 Ginkgo specs across `shape_tracker_test.go`, `observation_window_test.go`,
`sanity_test.go`, and `analyzer_test.go`. Key scenarios:

- **shape_tracker**: first call sets shape (no change); same values → no change; 25% shift → changed; 15% shift → no change (within tolerance)
- **observation_window**: k-bound filtering; eviction at capacity (oldest first); `Prune` removes by age; `Ready()` false below minSamples, false below minKSpread, true when both met; `Clear()` resets all
- **sanity**: each of the six issue types triggered by the correct bad-value; clean metrics → `OK()`
- **analyzer**: shape change clears window; multi-cycle accumulation makes `Ready()` true; bad metrics trigger sanity short-circuit; `VariantState()` reflects accumulated data

---

## Bug Fix Applied in TA3 (not TA2)

`sanity.go` originally checked `KvCacheUsage` (the saturation peak field) for the
`kv_utilization_out_of_range` issue. PR-4 uses `KvUtilization` (the instantaneous
field registered in PR-1) as k* for the ITL model, so the sanity check should guard
that field. The fix — changing `KvCacheUsage` to `KvUtilization` in `CheckModelMetrics`
— was discovered when writing PR-4 and applied on the TA3 branch (not backported to
TA2, which was already submitted).

---

## Not in this PR

- OLS regression (ITL model A, B fit) — PR-4
- μ_dec / λ_dec computation — PR-4
- Scaling signal (RequiredCapacity / SpareCapacity) — PR-4
- Wiring into the engine's analyzer pipeline — PR-5
