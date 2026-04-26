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
// across reconcile cycles and computes a μ_dec supply vs λ_dec demand scaling signal.
// It implements interfaces.Analyzer.
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
	// role is the P/D disaggregation role ("prefill", "decode", "both", "").
	// Updated from VariantStates at the start of each Analyze call.
	role             string
	lastSanityReport SanityReport
	lastObservedAt   time.Time
	// set by Analyze() for VariantState() snapshots
	lastITLModel         ITLModel
	lastPerReplicaSupply float64
	lastTotalSupply      float64
	lastDemand           float64
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
	if err := ctx.Err(); err != nil {
		return nil
	}
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

		// Collect one (k*, ITL) observation per replica. Per-replica variation in k*
		// provides the k-spread needed for a reliable OLS fit.
		for _, m := range variantMetrics {
			state.observationWindow.Add(m.KvUtilization, m.AvgITL, now)
		}
		state.observationWindow.Prune(now)
	}

	return reports
}

// Analyze implements interfaces.Analyzer. It calls Observe to update internal
// state, then computes a supply vs demand scaling signal for each variant using
// a two-tier ITL model resolution strategy:
//
//   - Tier 1 (OLS): observation window Ready — fit ITL(k) = A·k + B via OLS.
//   - Tier 2 (constrained OLS): window not ready — fit A with B = DefaultBaselineITLSec
//     using all replica (k*, ITL_obs) points: A = Σ((ITL_i−B)·k_i) / Σ(k_i²).
//
// Demand per variant is estimated in priority order:
//  1. EPP primary: Σ ArrivalRate × AvgOutputTokens (when ArrivalRate > 0 on any replica).
//  2. vLLM fallback: VLLMRequestRate × avgOL (when EPP absent but vLLM rate is nonzero).
//  3. k*-based local: Σ k_r* × KV_max_r / KVreq / ITL(k_r*) (scale-up only; no EPP needed).
//
// Scheduler queue demand (QueueSize / (DefaultQueueDrainFactor × ITL(k_sat))) is added
// to model-level demand after all variants are processed (non-prefill roles only).
//
// RequiredCapacity and SpareCapacity are computed from model-level totals, not
// per-variant deficits. This prevents conflicting signals when one variant is
// overloaded while another has spare capacity. PendingReplicas is included in
// anticipated supply to suppress scale-up thrashing while pods are starting.
// SpareCapacity is only emitted when EPP is deployed (ArrivalRate > 0).
//
// For P/D disaggregated models, RoleCapacities provides per-role breakdowns.
// No role is excluded from supply/demand computation. RequiredCapacity is
// suppressed for the prefill role: decode rate is never the prefill bottleneck.
func (a *ThroughputAnalyzer) Analyze(
	ctx context.Context,
	input interfaces.AnalyzerInput,
) (*interfaces.AnalyzerResult, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	// Build lookup tables from VariantStates before taking any locks.
	pendingByVariant := make(map[string]int, len(input.VariantStates))
	for _, vs := range input.VariantStates {
		pendingByVariant[vs.VariantName] = vs.PendingReplicas
	}

	// Update variant roles so state.role is current when Observe() runs.
	a.mu.Lock()
	for _, vs := range input.VariantStates {
		key := variantKey(input.Namespace, input.ModelID, vs.VariantName)
		state := a.getOrCreateVariantState(key)
		state.role = vs.Role
	}
	a.mu.Unlock()

	// Observe updates internal state (acquires/releases a.mu internally).
	a.Observe(ctx, input.ModelID, input.Namespace, input.ReplicaMetrics)

	byVariant := groupByVariant(input.ReplicaMetrics)

	a.mu.Lock()
	defer a.mu.Unlock()

	var (
		totalSupply, totalDemand, totalAnticipated float64
		anyEPP                                     bool
		totalDecodeITLSat                          float64
		nDecodeVariants                            int
	)
	variantCapacities := make([]interfaces.VariantCapacity, 0, len(byVariant))
	isEPPByVariant := make(map[string]bool, len(byVariant))

	for variantName, variantMetrics := range byVariant {
		key := variantKey(input.Namespace, input.ModelID, variantName)
		state, ok := a.variantStates[key]
		if !ok {
			continue
		}

		shape, hasShape := state.shapeTracker.Current()
		if !hasShape || shape.KVreq <= 0 {
			continue
		}

		model, ok := a.resolveITLModel(state, variantMetrics)
		if !ok {
			ctrl.Log.V(logging.DEBUG).Info("throughput analyzer: no ITL model available, skipping variant",
				"namespace", input.Namespace,
				"modelID", input.ModelID,
				"variant", variantName,
			)
			continue
		}

		itlSat := model.ITLAt(DefaultKSat)
		if itlSat <= 0 {
			continue
		}

		supply, perReplicaSupply := computeVariantSupply(variantMetrics, shape, itlSat)
		if supply == 0 {
			continue
		}

		demand, isEPP := computeDemand(variantMetrics)
		// k*-based local demand: when EPP and vLLM rate are both absent, derive demand
		// from observed KV utilization. Enables scale-up signals without EPP deployed.
		if demand == 0 && !isEPP {
			demand = computeLocalDemand(variantMetrics, shape, model)
		}

		// Update state for VariantState() snapshots.
		state.lastITLModel = model
		state.lastPerReplicaSupply = perReplicaSupply
		state.lastTotalSupply = supply
		state.lastDemand = demand

		pending := pendingByVariant[variantName]
		totalSupply += supply
		totalDemand += demand
		totalAnticipated += float64(len(variantMetrics)+pending) * perReplicaSupply
		if isEPP {
			anyEPP = true
		}
		// Track ITL(k_sat) across non-prefill variants for queue demand estimation.
		if state.role != "prefill" {
			totalDecodeITLSat += itlSat
			nDecodeVariants++
		}

		isEPPByVariant[variantName] = isEPP
		variantCapacities = append(variantCapacities, interfaces.VariantCapacity{
			VariantName:        variantName,
			Role:               state.role,
			ReplicaCount:       len(variantMetrics),
			PendingReplicas:    pending,
			PerReplicaCapacity: perReplicaSupply,
			TotalCapacity:      supply,
			TotalDemand:        demand,
			Utilization:        safeDivide(demand, supply),
		})
	}

	// Add scheduler queue demand to model-level total (non-prefill roles only).
	// Queue demand is not attributed to a specific variant — it appears in TotalDemand
	// and the model-level RC/SC signals but not in individual VariantCapacity entries.
	if nDecodeVariants > 0 {
		avgDecodeITLSat := totalDecodeITLSat / float64(nDecodeVariants)
		totalDemand += estimateQueueDemand(input.SchedulerQueue, avgDecodeITLSat, DefaultQueueDrainFactor)
	}

	// Model-level RequiredCapacity and SpareCapacity from totals. Computing from
	// totals prevents simultaneous RC and SC signals when variants are imbalanced.
	var requiredCapacity, spareCapacity float64
	if totalDemand > totalAnticipated {
		requiredCapacity = totalDemand - totalAnticipated
	}
	// Scale-down only when EPP is deployed — without it the demand estimate may be
	// too noisy to trust for scale-down decisions.
	if anyEPP && totalSupply > totalDemand {
		spareCapacity = totalSupply - totalDemand
	}

	return &interfaces.AnalyzerResult{
		AnalyzerName:      AnalyzerName,
		ModelID:           input.ModelID,
		Namespace:         input.Namespace,
		AnalyzedAt:        time.Now(),
		VariantCapacities: variantCapacities,
		TotalSupply:       totalSupply,
		TotalDemand:       totalDemand,
		Utilization:       safeDivide(totalDemand, totalSupply),
		RequiredCapacity:  requiredCapacity,
		SpareCapacity:     spareCapacity,
		RoleCapacities:    aggregateRoleCapacities(variantCapacities, isEPPByVariant),
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
		ITLModel:         state.lastITLModel,
		PerReplicaSupply: state.lastPerReplicaSupply,
		TotalSupply:      state.lastTotalSupply,
		Demand:           state.lastDemand,
		Role:             state.role,
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

// resolveITLModel returns the ITL model to use for a variant using a two-tier strategy:
//
//   - Tier 1: OLS fit from the observation window (when Ready).
//   - Tier 2: single-point estimate from variant-average (k*, ITL_obs) with B = DefaultBaselineITLSec.
//     Only possible when at least one replica has k* > 0. Replicas with k* = 0 (idle) are excluded
//     from estimation — k* = 0 observations carry no ITL signal.
//
// When replicas are present but all are idle (k* = 0), both tiers fail and we return (zero, false).
// A future tier-3 (knowledge store) path for the scale-from-zero case will be added once Analyze()
// is extended to iterate variants with state but no current replica metrics.
//
// Must be called with a.mu held.
func (a *ThroughputAnalyzer) resolveITLModel(state *variantState, metrics []interfaces.ReplicaMetrics) (ITLModel, bool) {
	// Tier 1: OLS fit.
	if state.observationWindow.Ready() {
		obs := state.observationWindow.Observations()
		if model, ok := FitITLModel(obs); ok {
			return model, true
		}
	}

	// Tier 2: constrained OLS with B = DefaultBaselineITLSec fixed.
	// Minimize Σ(ITL_i − A·k_i − B)² → A = Σ((ITL_i − B)·k_i) / Σ(k_i²).
	// Using per-replica (k*, ITL) directly is better than collapsing to a centroid
	// when replicas have spread k* values — it is the same least-squares criterion
	// as tier-1 OLS but with B pinned instead of fitted.
	var numerator, sumK2 float64
	var n float64
	for _, m := range metrics {
		if m.KvUtilization > 0 && m.AvgITL > 0 {
			numerator += (m.AvgITL - DefaultBaselineITLSec) * m.KvUtilization
			sumK2 += m.KvUtilization * m.KvUtilization
			n++
		}
	}
	if n > 0 && sumK2 > 0 {
		A := numerator / sumK2
		if A > 0 {
			return ITLModel{A: A, B: DefaultBaselineITLSec}, true
		}
	}
	return ITLModel{}, false
}

// computeDemand aggregates λ_dec (decode token demand in tokens/sec) across replicas.
//
// Primary path (EPP deployed): Σ ArrivalRate_r × AvgOutputTokens_r.
// Fallback path (EPP absent): Σ VLLMRequestRate_r × AvgOutputTokens_r.
//
// Both paths use the per-replica product rather than sumRate × avgOL to avoid
// averaging-the-averages: replicas with higher throughput contribute proportionally
// more to λ_dec without requiring raw histogram sums.
//
// Returns (λ_dec, isEPP). isEPP is true when at least one replica reports ArrivalRate > 0.
// Callers should suppress scale-down signals when isEPP is false.
func computeDemand(metrics []interfaces.ReplicaMetrics) (float64, bool) {
	var lambdaDec float64
	var isEPP bool
	for _, m := range metrics {
		if m.ArrivalRate > 0 {
			isEPP = true
			lambdaDec += m.ArrivalRate * m.AvgOutputTokens
		}
	}
	if isEPP {
		return lambdaDec, true
	}

	// Fallback: EPP not deployed — use vLLM-side request rate as a proxy for λ_req.
	// Σ VLLMRequestRate_r × AvgOutputTokens_r mirrors the EPP formula structure and
	// correctly weights each replica's OL by its own throughput.
	var lambdaDecFallback float64
	for _, m := range metrics {
		if m.VLLMRequestRate > 0 && m.AvgOutputTokens > 0 {
			lambdaDecFallback += m.VLLMRequestRate * m.AvgOutputTokens
		}
	}
	return lambdaDecFallback, false
}

// computeLocalDemand estimates decode token demand from per-replica k* observations
// when the EPP ArrivalRate and vLLM request rate are both unavailable.
//
//	λ_local = Σ_r (k_r* × KV_max_r / KVreq) / ITL(k_r*)
//
// Each replica's in-flight request count N_r = k_r* × KV_max_r / KVreq is divided
// by ITL(k_r*) to approximate its current throughput. Replicas with k* = 0 or
// KV_max = 0 are excluded (no meaningful signal at idle).
// This estimate is used for scale-up only; SpareCapacity still requires EPP.
func computeLocalDemand(metrics []interfaces.ReplicaMetrics, shape WorkloadShape, model ITLModel) float64 {
	if shape.KVreq <= 0 {
		return 0
	}
	var total float64
	for _, m := range metrics {
		if m.KvUtilization <= 0 || m.TotalKvCapacityTokens <= 0 {
			continue
		}
		itlAtK := model.ITLAt(m.KvUtilization)
		if itlAtK <= 0 {
			continue
		}
		total += m.KvUtilization * float64(m.TotalKvCapacityTokens) / shape.KVreq / itlAtK
	}
	return total
}

// estimateQueueDemand converts the scheduler queue depth into an equivalent
// decode token demand rate (tokens/sec).
//
//	drain_time = QueueDrainFactor × ITL(k_sat) × avgOL
//	λ_queue    = QueueSize × avgOL / drain_time
//	           = QueueSize / (QueueDrainFactor × ITL(k_sat))   (avgOL cancels)
//
// ITL(k_sat) is used as the reference latency so that admitted queue demand
// bounds per-request queueing time to ≤ QueueDrainFactor × ITL(k_sat) × avgOL.
func estimateQueueDemand(sq *interfaces.SchedulerQueueMetrics, itlSat, drainFactor float64) float64 {
	if sq == nil || sq.QueueSize <= 0 || itlSat <= 0 || drainFactor <= 0 {
		return 0
	}
	return float64(sq.QueueSize) / (drainFactor * itlSat)
}

// computeVariantSupply computes the aggregate μ_dec_sat supply for a variant.
//
// Per replica: N_dec_sat = DefaultKSat × KV_max / KVreq; μ_dec_sat = N_dec_sat / itlSat.
// Returns (totalSupply Σμ_dec_sat, perReplicaSupply mean(μ_dec_sat)).
// Both are zero when no replica has KV capacity data.
func computeVariantSupply(metrics []interfaces.ReplicaMetrics, shape WorkloadShape, itlSat float64) (total, perReplica float64) {
	var sum float64
	var n float64
	for _, m := range metrics {
		if m.TotalKvCapacityTokens <= 0 {
			continue
		}
		kvMax := float64(m.TotalKvCapacityTokens)
		nSat := DefaultKSat * kvMax / shape.KVreq
		sum += nSat / itlSat
		n++
	}
	if n == 0 {
		return 0, 0
	}
	return sum, sum / n
}

// groupByVariant partitions a slice of ReplicaMetrics by VariantName.
func groupByVariant(metrics []interfaces.ReplicaMetrics) map[string][]interfaces.ReplicaMetrics {
	groups := make(map[string][]interfaces.ReplicaMetrics)
	for _, m := range metrics {
		groups[m.VariantName] = append(groups[m.VariantName], m)
	}
	return groups
}

// averageShapeMetrics computes the VLLMRequestRate-weighted mean IL, OL, and
// prefix hit rate across a slice of replica metrics. Replicas with zero or
// negative IL or OL are excluded. When all eligible replicas have zero
// VLLMRequestRate, falls back to an unweighted mean.
func averageShapeMetrics(metrics []interfaces.ReplicaMetrics) (il, ol, hitRate float64) {
	var sumIL, sumOL, sumHitRate float64 // weighted accumulators
	var sumILu, sumOLu, sumHRu float64   // unweighted fallback
	var totalWeight, count float64
	for _, m := range metrics {
		if m.AvgInputTokens <= 0 || m.AvgOutputTokens <= 0 {
			continue
		}
		count++
		sumILu += m.AvgInputTokens
		sumOLu += m.AvgOutputTokens
		sumHRu += m.PrefixCacheHitRate
		if m.VLLMRequestRate > 0 {
			sumIL += m.VLLMRequestRate * m.AvgInputTokens
			sumOL += m.VLLMRequestRate * m.AvgOutputTokens
			sumHitRate += m.VLLMRequestRate * m.PrefixCacheHitRate
			totalWeight += m.VLLMRequestRate
		}
	}
	if count == 0 {
		return 0, 0, 0
	}
	if totalWeight == 0 {
		return sumILu / count, sumOLu / count, sumHRu / count
	}
	return sumIL / totalWeight, sumOL / totalWeight, sumHitRate / totalWeight
}

// safeDivide returns num/denom, or 0 when denom is zero.
func safeDivide(num, denom float64) float64 {
	if denom == 0 {
		return 0
	}
	return num / denom
}

// aggregateRoleCapacities groups variant capacities by P/D role and computes
// per-role supply and demand signals. Returns nil when all variants have role ""
// or "both" (non-disaggregated model).
//
// The TA currently uses the decode-rate framework (ITL(k) = A·k + B, supply = μ_sat,
// demand = λ_dec) for all roles. A prefill-role variant fits its ITL model against its
// own observed (k*, ITL) data — which represents TTFT on the prefill pod, not decode
// ITL — and its supply measures decode-equivalent throughput. Because prefill pods are
// never the decode-rate bottleneck, RequiredCapacity is suppressed for the prefill
// role even if demand exceeds anticipated supply. SpareCapacity is still emitted when
// EPP confirms excess capacity.
//
// Role-specific rate models (e.g. prefill-rate supply and prefill-rate demand based on
// input token throughput) will be added in a later PR.
func aggregateRoleCapacities(vcs []interfaces.VariantCapacity, isEPPByVariant map[string]bool) map[string]interfaces.RoleCapacity {
	hasDisaggregation := false
	for _, vc := range vcs {
		if vc.Role != "" && vc.Role != interfaces.RoleBoth {
			hasDisaggregation = true
			break
		}
	}
	if !hasDisaggregation {
		return nil
	}

	type roleAccum struct {
		supply      float64
		anticipated float64
		demand      float64
		hasEPP      bool
	}
	accums := make(map[string]*roleAccum)
	for _, vc := range vcs {
		role := vc.Role
		if role == "" {
			role = interfaces.RoleBoth
		}
		ra, ok := accums[role]
		if !ok {
			ra = &roleAccum{}
			accums[role] = ra
		}
		ra.supply += vc.TotalCapacity
		ra.anticipated += float64(vc.ReplicaCount+vc.PendingReplicas) * vc.PerReplicaCapacity
		ra.demand += vc.TotalDemand
		if isEPPByVariant[vc.VariantName] {
			ra.hasEPP = true
		}
	}

	result := make(map[string]interfaces.RoleCapacity, len(accums))
	for role, ra := range accums {
		var required, spare float64
		// RequiredCapacity is only meaningful for decode/both roles: prefill pods are
		// never the decode-rate bottleneck so a scale-up signal would be incorrect.
		if role != "prefill" && ra.demand > ra.anticipated {
			required = ra.demand - ra.anticipated
		}
		if ra.hasEPP && ra.supply > ra.demand {
			spare = ra.supply - ra.demand
		}
		result[role] = interfaces.RoleCapacity{
			Role:             role,
			TotalSupply:      ra.supply,
			TotalDemand:      ra.demand,
			RequiredCapacity: required,
			SpareCapacity:    spare,
		}
	}
	return result
}
