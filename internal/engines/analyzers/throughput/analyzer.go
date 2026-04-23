package throughput

import (
	"context"
	"fmt"
	"sync"
	"time"

	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
)

// ThroughputAnalyzer accumulates per-variant workload shape and ITL observations
// across reconcile cycles. It implements interfaces.Analyzer; in the current phase
// it produces no scaling signal (RequiredCapacity=0, SpareCapacity=0). The OLS fit,
// μ_dec supply estimation, and λ_dec vs μ_dec scaling signal are added in PR-4.
//
// State is tracked per variant (keyed by "namespace|modelID|variantName") because
// different variants may run on different hardware with different ITL coefficients,
// and all replicas of the same variant are expected to share OL, IL, and KV_max.
type ThroughputAnalyzer struct {
	mu            sync.Mutex
	variantStates map[string]*variantState
}

// variantState holds the cross-cycle calibration state for a single variant.
type variantState struct {
	shapeTracker      *ShapeTracker
	observationWindow *ObservationWindow
	lastSanityReport  SanityReport
	lastObservedAt    time.Time
}

// NewThroughputAnalyzer creates a ThroughputAnalyzer with default configuration.
func NewThroughputAnalyzer() *ThroughputAnalyzer {
	return &ThroughputAnalyzer{
		variantStates: make(map[string]*variantState),
	}
}

// Name returns the canonical name for this analyzer.
func (a *ThroughputAnalyzer) Name() string {
	return AnalyzerName
}

// Observe processes one reconcile cycle for a model. It groups metrics by
// VariantName and, for each variant:
//  1. Runs sanity checks; skips the variant if any issue is found.
//  2. Computes the variant-average IL, OL, and prefix hit rate.
//  3. Updates the shape tracker; clears the observation window on shape change.
//  4. Adds one (k, ITL) observation per replica to the window.
//  5. Prunes observations older than DefaultObservationMaxAge.
//
// Returns a map of variantName → SanityReport for logging. An empty SanityReport
// (report.OK() == true) means that variant's metrics were healthy this cycle.
func (a *ThroughputAnalyzer) Observe(
	ctx context.Context,
	modelID, namespace string,
	metrics []interfaces.ReplicaMetrics,
) map[string]SanityReport {
	now := time.Now()
	byVariant := groupByVariant(metrics)
	reports := make(map[string]SanityReport, len(byVariant))

	a.mu.Lock()
	defer a.mu.Unlock()

	for variantName, variantMetrics := range byVariant {
		report := CheckModelMetrics(variantMetrics)
		reports[variantName] = report

		key := variantKey(namespace, modelID, variantName)
		state := a.getOrCreateVariantState(key)
		state.lastSanityReport = report
		state.lastObservedAt = now

		if !report.OK() {
			ctrl.Log.V(logging.DEBUG).Info("throughput analyzer: sanity issues detected, skipping variant",
				"namespace", namespace,
				"modelID", modelID,
				"variant", variantName,
				"issues", report.Issues,
				"affectedPods", report.AffectedPods,
			)
			continue
		}

		// Compute variant-average shape metrics. All replicas of the same variant
		// are expected to have the same OL and IL (same model, same config); the
		// mean handles any minor per-pod variation.
		il, ol, hitRate := averageShapeMetrics(variantMetrics)

		shape, changed := state.shapeTracker.Observe(il, ol, hitRate)
		if changed {
			ctrl.Log.V(logging.DEBUG).Info("throughput analyzer: workload shape changed, clearing observation window",
				"namespace", namespace,
				"modelID", modelID,
				"variant", variantName,
				"newKVreq", shape.KVreq,
			)
			state.observationWindow.Clear()
		}

		// Collect one (k, ITL) observation per replica. Per-replica variation in k
		// provides the k-spread needed for a reliable OLS fit.
		for _, m := range variantMetrics {
			state.observationWindow.Add(m.KvCacheUsage, m.AvgITL, now)
		}
		state.observationWindow.Prune(now)
	}

	return reports
}

// Analyze implements interfaces.Analyzer. It calls Observe to update internal
// state and returns an AnalyzerResult with no scaling signal (PR-3 scope).
// The OLS fit and μ_dec vs λ_dec scaling signal are added in PR-4.
func (a *ThroughputAnalyzer) Analyze(
	ctx context.Context,
	input interfaces.AnalyzerInput,
) (*interfaces.AnalyzerResult, error) {
	a.Observe(ctx, input.ModelID, input.Namespace, input.ReplicaMetrics)

	return &interfaces.AnalyzerResult{
		AnalyzerName: AnalyzerName,
		ModelID:      input.ModelID,
		Namespace:    input.Namespace,
		AnalyzedAt:   time.Now(),
		// RequiredCapacity and SpareCapacity are zero until PR-4 adds the
		// ITL model fit and μ_dec vs λ_dec computation.
	}, nil
}

// VariantState returns a read-only snapshot of the per-variant calibration state.
// Returns (zero ThroughputVariantState, false) if no data has been observed yet
// for the given variant.
func (a *ThroughputAnalyzer) VariantState(modelID, namespace, variantName string) (ThroughputVariantState, bool) {
	a.mu.Lock()
	defer a.mu.Unlock()

	key := variantKey(namespace, modelID, variantName)
	state, ok := a.variantStates[key]
	if !ok {
		return ThroughputVariantState{}, false
	}

	shape, _ := state.shapeTracker.Current()
	return ThroughputVariantState{
		Shape:            shape,
		ObservationReady: state.observationWindow.Ready(),
		KSpread:          state.observationWindow.KSpread(),
		SampleCount:      state.observationWindow.Len(),
		LastSanityReport: state.lastSanityReport,
	}, true
}

// --- helpers ---

// variantKey builds the map key for a variant. The pipe delimiter is safe because
// Kubernetes resource names follow DNS rules and cannot contain "|".
func variantKey(namespace, modelID, variantName string) string {
	return fmt.Sprintf("%s|%s|%s", namespace, modelID, variantName)
}

// getOrCreateVariantState returns the variantState for the given key, creating
// it with default configuration if it does not exist yet.
// Must be called with a.mu held.
func (a *ThroughputAnalyzer) getOrCreateVariantState(key string) *variantState {
	if state, ok := a.variantStates[key]; ok {
		return state
	}
	state := &variantState{
		shapeTracker: newShapeTracker(DefaultShapeChangeTolerance),
		observationWindow: newObservationWindow(
			DefaultWindowMaxSize,
			DefaultObservationMaxAge,
			DefaultMinSamples,
			DefaultMinKSpread,
			DefaultMinObservableK,
			DefaultMaxObservableK,
		),
	}
	a.variantStates[key] = state
	return state
}

// groupByVariant partitions a slice of ReplicaMetrics by VariantName.
func groupByVariant(metrics []interfaces.ReplicaMetrics) map[string][]interfaces.ReplicaMetrics {
	groups := make(map[string][]interfaces.ReplicaMetrics)
	for _, m := range metrics {
		groups[m.VariantName] = append(groups[m.VariantName], m)
	}
	return groups
}

// averageShapeMetrics computes the mean IL, OL, and prefix hit rate across a
// slice of replica metrics. Replicas with zero OL or IL are excluded from the
// average (they lack workload data this cycle).
func averageShapeMetrics(metrics []interfaces.ReplicaMetrics) (il, ol, hitRate float64) {
	var sumIL, sumOL, sumHitRate float64
	var count float64
	for _, m := range metrics {
		if m.AvgInputTokens <= 0 || m.AvgOutputTokens <= 0 {
			continue
		}
		sumIL += m.AvgInputTokens
		sumOL += m.AvgOutputTokens
		sumHitRate += m.PrefixCacheHitRate
		count++
	}
	if count == 0 {
		return 0, 0, 0
	}
	return sumIL / count, sumOL / count, sumHitRate / count
}
