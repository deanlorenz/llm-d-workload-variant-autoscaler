# PR-3: Throughput Analyzer State Management

> **Status: COMPLETED** — Implemented in #1052. All components below were delivered as
> planned. Everything listed under "Not in this PR" is deferred to PR-4.
> This document serves as design rationale and reviewer context for #1052.

## Context

The metrics collection layer (PR-1/PR-2, #1051) registered 9 Prometheus queries for
the Throughput Analyzer. PR-3 creates the internal Go package that stores and manages
the data those metrics produce — per-model workload shape tracking, ITL observation
windows, and sanity diagnostics.

**Scope: μ_dec vs λ_dec only. No OLS fit. No scaling signal. No changes to existing code.**

The OLS fit and μ_dec/λ_dec computation are PR-4. PR-3 builds the stateful substrate
that PR-4 will extend.

---

## Key findings from codebase exploration

### `interfaces.ReplicaMetrics` already has everything PR-3 needs

| PR-3 need | Existing field |
|-----------|---------------|
| k* (KV utilization) | `KvCacheUsage float64` |
| KV_max | `TotalKvCapacityTokens int64` |
| OL | `AvgOutputTokens float64` |
| IL | `AvgInputTokens float64` |
| prefix hit rate | `PrefixCacheHitRate float64` |
| ITL_obs | `AvgITL float64` (1m rate, already collected) |

**No changes needed to `interfaces/`, `collector/`, or any existing analyzer.**

### Pattern: follow `saturation_v2` two-store design

`saturation_v2` uses two distinct cross-call state stores:

| saturation_v2 | role | throughput analogy |
|---------------|------|--------------------|
| `computeCapacityHistory map[string]*rollingAverage` | rolling observations per workload bucket (k2 history) | `ObservationWindow` per variant — rolling (k, ITL) pairs (PR-3) |
| `CapacityKnowledgeStore` (injected) | persists learned capacity beyond individual cycles; survives zero-replica periods; supports cross-variant matching | `ITLKnowledgeStore` — persists fitted (A, B) per variant; fallback for zero-replica / uncalibrated variants (PR-4) |

PR-3 implements only the **observation history** layer (`ObservationWindow` per variant).  
PR-4 adds the **knowledge store** layer (`ITLKnowledgeStore` with fitted A, B) following the same injection pattern as `CapacityKnowledgeStore`.

---

## New package: `internal/engines/analyzers/throughput/`

### File layout

```
internal/engines/analyzers/throughput/
├── constants.go               thresholds, window parameters, analyzer name
├── types.go                   WorkloadShape, ITLObservation, SanityIssue, SanityReport
├── shape_tracker.go           ShapeTracker: current (IL,OL) bucket + change detection
├── observation_window.go      ObservationWindow: rolling (k, ITL) pairs, ready flag
├── sanity.go                  CheckModelMetrics: missing/stale/out-of-range detection
├── analyzer.go                ThroughputAnalyzer struct + Observe() + Analyze() stub
├── suite_test.go              Ginkgo suite registration
├── shape_tracker_test.go      unit tests
├── observation_window_test.go unit tests
├── sanity_test.go             unit tests
└── analyzer_test.go           integration tests (multi-call state accumulation)
```

---

## constants.go

```go
const (
    AnalyzerName = "throughput"

    // Shape change tolerance: retriggers ITL window clear + refit
    DefaultShapeChangeTolerance = 0.20  // 20% change in IL or OL

    // Observation window
    DefaultWindowMaxSize      = 20
    DefaultObservationMaxAge  = 30 * time.Minute
    DefaultMinSamples         = 10
    DefaultMinKSpread         = 0.30
    DefaultMinObservableK     = 0.15   // below this, KV% unreliable for ITL fit
    DefaultMaxObservableK     = 0.85   // above this, near saturation — non-linear

    // Sanity thresholds
    DefaultMinTokensPerRequest = 1.0   // OL or IL below this is suspect
)
```

---

## types.go

```go
// WorkloadShape captures the stable (IL, OL) characterization for a calibration period.
//
// KVreq = ILeff + OL/2 is the time-averaged per-in-flight-request KV footprint.
// ILeff is used for both N(k*) (current fleet) and N(k_sat) (new replica capacity).
//
// Rationale for using ILeff for new replicas: with cache-aware scheduling (EPP
// prefix routing), a new replica warms up quickly and operates at approximately
// fleet-average ILeff in steady state. Using IL (cold-cache pessimism) would
// chronically over-estimate KV demand per request and lead to over-scaling.
// When prefix caching is disabled, PrefixHitRate=0 and ILeff=IL automatically,
// so the formula is correct in that case without special handling.
type WorkloadShape struct {
    AvgInputTokens  float64  // IL (tok/req)
    AvgOutputTokens float64  // OL (tok/req)
    PrefixHitRate   float64  // 0.0 when NaN (caching disabled)
    ILeff           float64  // IL × (1 − PrefixHitRate)
    KVreq           float64  // ILeff + OL/2
}

func newWorkloadShape(il, ol, hitRate float64) WorkloadShape
func (s WorkloadShape) IsZero() bool
// Within returns true if both IL and OL are within ±tolerance of other.
func (s WorkloadShape) Within(other WorkloadShape, tolerance float64) bool

// ITLObservation is a single (k, ITL_obs) data point.
type ITLObservation struct {
    K         float64
    ITLSec    float64
    Timestamp time.Time
}

// SanityIssue is a diagnostic tag for a metric quality problem.
type SanityIssue string
const (
    SanityIssueNoReplicas       SanityIssue = "no_replicas"
    SanityIssueMissingKV        SanityIssue = "missing_kv_capacity"
    SanityIssueKVOutOfRange     SanityIssue = "kv_utilization_out_of_range"
    SanityIssueITLNonPositive   SanityIssue = "itl_non_positive"
    SanityIssueMissingShape     SanityIssue = "missing_shape_metrics"
    SanityIssueStaleMetrics     SanityIssue = "stale_metrics"
)

// SanityReport summarises metric quality for one reconcile cycle.
type SanityReport struct {
    Issues      []SanityIssue
    AffectedPods []string  // pods with at least one issue
}
func (r SanityReport) OK() bool   // len(Issues) == 0
func (r SanityReport) Has(issue SanityIssue) bool
```

---

## shape_tracker.go

```go
type ShapeTracker struct {
    current   WorkloadShape
    hasShape  bool
    tolerance float64
}

func newShapeTracker(tolerance float64) *ShapeTracker

// Observe updates the tracker with the fleet-averaged (IL, OL, hitRate) for this cycle.
// Returns (currentShape, shapeChanged). shapeChanged=true means the window must be cleared.
// First call always sets the shape (shapeChanged=false — no prior shape to compare to).
func (t *ShapeTracker) Observe(il, ol, hitRate float64) (WorkloadShape, bool)

func (t *ShapeTracker) Current() (WorkloadShape, bool)
func (t *ShapeTracker) Reset()
```

**Shape change logic:** shapeChanged = hasShape && !new.Within(current, tolerance).
On first call (hasShape=false): sets shape, returns changed=false (nothing to refit yet).

---

## observation_window.go

```go
type ObservationWindow struct {
    observations []ITLObservation
    maxSize      int
    maxAge       time.Duration
    minSamples   int
    minKSpread   float64
    minK, maxK   float64
}

func newObservationWindow(maxSize int, maxAge time.Duration,
    minSamples int, minKSpread, minK, maxK float64) *ObservationWindow

// Add appends a (k, itl) pair if k ∈ [minK, maxK].
// When at capacity, the oldest observation is evicted first.
func (w *ObservationWindow) Add(k, itl float64, ts time.Time)

// Prune removes observations older than maxAge.
func (w *ObservationWindow) Prune(now time.Time)

// KSpread returns max_k - min_k over current observations (0 if empty).
func (w *ObservationWindow) KSpread() float64

// Ready returns true when len >= minSamples AND KSpread >= minKSpread.
func (w *ObservationWindow) Ready() bool

// Observations returns a copy of the current window contents (for OLS in PR-4).
func (w *ObservationWindow) Observations() []ITLObservation

// Clear discards all observations (called on shape change).
func (w *ObservationWindow) Clear()
```

---

## sanity.go

```go
// CheckModelMetrics validates replica metrics for one reconcile cycle.
// Returns a SanityReport; callers should log and skip Observe when !report.OK().
func CheckModelMetrics(metrics []interfaces.ReplicaMetrics) SanityReport
```

Checks (per pod, aggregated into report):
- No replicas → SanityIssueNoReplicas (model-level)
- `TotalKvCapacityTokens <= 0` → SanityIssueMissingKV
- `KvCacheUsage < 0 || KvCacheUsage > 1` → SanityIssueKVOutOfRange
- `AvgITL <= 0` → SanityIssueITLNonPositive (not NaN-safe; treat NaN as 0)
- `AvgOutputTokens <= DefaultMinTokensPerRequest || AvgInputTokens <= DefaultMinTokensPerRequest` → SanityIssueMissingShape
- `Metadata != nil && Metadata.FreshnessStatus == "stale"` → SanityIssueStaleMetrics

---

## analyzer.go

State is tracked **per variant** because:
- Different variants may run on different hardware → different ITL model A/B coefficients
- All replicas of the same variant share OL, IL, KV_max — so per-variant averaging is correct
- k naturally varies across replicas of the same variant under uneven load → provides k-spread

```go
type ThroughputAnalyzer struct {
    mu            sync.Mutex
    variantStates map[string]*variantState  // key: "namespace|modelID|variantName"
}

type variantState struct {
    shapeTracker      *ShapeTracker
    observationWindow *ObservationWindow
    lastSanityReport  SanityReport
    lastObservedAt    time.Time
}

func NewThroughputAnalyzer() *ThroughputAnalyzer
func (a *ThroughputAnalyzer) Name() string  // AnalyzerName

// Observe processes one reconcile cycle. Groups replicas by VariantName, then for each variant:
//   1. CheckModelMetrics(variantReplicas) → sanityReport; skip variant if !OK
//   2. Compute variant-average IL, OL, hitRate (expected uniform across replicas)
//   3. shapeTracker.Observe(il, ol, hitRate) → if changed, window.Clear()
//   4. For each replica in variant: window.Add(KvCacheUsage, AvgITL, now)
//   5. window.Prune(now)
// Returns a map of variant → SanityReport for logging.
func (a *ThroughputAnalyzer) Observe(
    ctx context.Context,
    modelID, namespace string,
    metrics []interfaces.ReplicaMetrics,
) map[string]SanityReport

// Analyze implements interfaces.Analyzer. In PR-3, calls Observe then returns
// RequiredCapacity=0 / SpareCapacity=0 (no scaling signal until PR-4).
func (a *ThroughputAnalyzer) Analyze(
    ctx context.Context,
    input interfaces.AnalyzerInput,
) (*interfaces.AnalyzerResult, error)

// VariantState returns a read-only snapshot for a specific variant. Used in tests and logging.
func (a *ThroughputAnalyzer) VariantState(modelID, namespace, variantName string) (ThroughputVariantState, bool)

// ThroughputVariantState is a read-only snapshot for tests and logging.
type ThroughputVariantState struct {
    Shape            WorkloadShape
    ObservationReady bool
    KSpread          float64
    SampleCount      int
    LastSanityReport SanityReport
}
```

---

## Data flow within Observe()

```
metrics []ReplicaMetrics
    │
    ├── group by VariantName → map[variantName][]ReplicaMetrics
    │
    └── for each variant:
            CheckModelMetrics(variantReplicas) → SanityReport
            if !OK: record, skip this variant
            │
            variant-average IL, OL, hitRate (expected uniform; mean handles noise)
            │
            shapeTracker.Observe(il, ol, hitRate)
            → (currentShape, changed)
            if changed: window.Clear()
            │
            for each replica in variant:
                window.Add(KvCacheUsage, AvgITL, now)
            window.Prune(now)
```

---

## Testing approach

Follow `internal/engines/analyzers/saturation_v2/` pattern: Ginkgo/Gomega, `BeforeEach`
constructs a fresh instance per test. Key test cases:

- **shape_tracker_test**: first call sets shape (no change); second call same values → no change; 25% change → changed; 15% change → no change (within tolerance)
- **observation_window_test**: Add respects k bounds; Prune evicts old entries; Ready() = false below minSamples, false below minKSpread, true when both met; Clear() resets all; Add at capacity evicts oldest
- **sanity_test**: each SanityIssue triggered by the right bad-value combination; clean metrics → OK()
- **analyzer_test**: shape change clears window; multi-cycle accumulation → Ready() becomes true; bad metrics → sanity short-circuit; State() reflects accumulated data

---

## Not in this PR

- OLS regression (ITL model A, B fit) — PR-4
- μ_dec / λ_dec computation — PR-4
- Scaling signal (RequiredCapacity / SpareCapacity) — PR-4
- New fields on `interfaces.ReplicaMetrics` (`GenerationTokenRate`, `DecodeTokenDemand`) — PR-4
- Wiring into the engine's analyzer pipeline — PR-4

---

## Verification

```
make test   # all tests pass including new package
go build ./...  # no compile errors
```
