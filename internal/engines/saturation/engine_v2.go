package saturation

import (
	"context"
	"fmt"
	"math"

	ctrl "sigs.k8s.io/controller-runtime"

	llmdVariantAutoscalingV1alpha1 "github.com/llm-d/llm-d-workload-variant-autoscaler/api/v1alpha1"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/config"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/engines/pipeline"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/utils"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/utils/scaletarget"
)

// runV2AnalysisOnly runs the V2 saturation analyzer and returns the raw AnalyzerResult
// without building targets or converting to V1 types. The optimizer will handle
// target building across all models.
func (e *Engine) runV2AnalysisOnly(
	ctx context.Context,
	modelID, namespace string,
	replicaMetrics []interfaces.ReplicaMetrics,
	config config.SaturationScalingConfig,
	variantStates []interfaces.VariantReplicaState,
	scaleTargets map[string]scaletarget.ScaleTargetAccessor,
	variantAutoscalings map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling,
) (*interfaces.AnalyzerResult, error) {
	logger := ctrl.LoggerFrom(ctx)

	// 1. Pre-populate capacity store with scale target-derived params
	for _, va := range variantAutoscalings {
		key := utils.GetNamespacedKey(va.Namespace, va.GetScaleTargetName())
		scaleTarget := scaleTargets[key]
		if scaleTarget == nil {
			logger.V(logging.DEBUG).Info("No scale target found for VA, skipping capacity store pre-population",
				"variant", va.Name, "scaleTargetKey", key)
			continue
		}
		// Get accelerator name from scale target nodeSelector/nodeAffinity or VA label
		accelerator := utils.GetAcceleratorNameFromScaleTarget(va, scaleTarget)
		gpuCount := scaleTarget.GetTotalGPUsPerReplica()
		e.capacityStore.LoadFromScaleTarget(namespace, modelID, va.Name, accelerator, gpuCount, scaleTarget)
		logger.V(logging.DEBUG).Info("Pre-populated capacity store from scale target",
			"variant", va.Name, "accelerator", accelerator, "gpuCount", gpuCount)
	}

	// 2. Build AnalyzerInput
	input := interfaces.AnalyzerInput{
		ModelID:        modelID,
		Namespace:      namespace,
		ReplicaMetrics: replicaMetrics,
		VariantStates:  variantStates,
		Config:         &config,
		// TODO: populate SchedulerQueue when flow control metrics are collected
	}

	// 3. Run V2 analyzer
	result, err := e.saturationV2Analyzer.Analyze(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("V2 saturation analysis failed: %w", err)
	}

	logger.Info("V2 saturation analysis completed",
		"modelID", modelID,
		"totalSupply", result.TotalSupply,
		"totalDemand", result.TotalDemand,
		"utilization", result.Utilization,
		"requiredCapacity", result.RequiredCapacity,
		"spareCapacity", result.SpareCapacity)

	return result, nil
}

// enabledAnalyzerResult pairs an enabled analyzer's result with its configured score weight.
type enabledAnalyzerResult struct {
	result *interfaces.AnalyzerResult
	score  float64
}

// sumTotalCapacity returns the sum of TotalCapacity across all variant capacities.
func sumTotalCapacity(vcs []interfaces.VariantCapacity) float64 {
	total := 0.0
	for _, vc := range vcs {
		total += vc.TotalCapacity
	}
	return total
}

// combineAnalyzerResults merges multiple enabled analyzer results into a single
// AnalyzerResult for the optimizer. satResult is always used as the metadata base —
// its VariantCapacities carry Cost and AcceleratorName required for variant selection
// and GPU accounting.
//
// The combine is performed in dimensionless utilisation space so that analyzers using
// different capacity units (tokens, tok/s, …) can be compared safely:
//
//	utilExcess_i = RC_i / sum(TotalCapacity_i)   — fraction demand exceeds supply
//	utilSlack_i  = SC_i / sum(TotalCapacity_i)   — fraction of supply that is spare
//
// Any-up:  scale up when any enabled analyzer has utilExcess > 0.
// All-down: scale down only when every analyzer with valid data has utilSlack > 0.
// Results are denormalised back into saturation's capacity units for the optimizer.
func combineAnalyzerResults(
	satResult *interfaces.AnalyzerResult,
	results []enabledAnalyzerResult,
	priority float64,
) *interfaces.AnalyzerResult {
	combined := *satResult // copy; VariantCapacities from saturation are always the base

	if len(results) == 0 {
		combined.RequiredCapacity = 0
		combined.SpareCapacity = 0
		combined.Score = 0
		return &combined
	}

	satTotal := sumTotalCapacity(satResult.VariantCapacities)

	var excessFracs []float64 // util_excess per analyzer with valid data
	var slackFracs []float64  // util_slack  per analyzer with valid data
	validCount := 0           // analyzers that provided a signal (t>0, or cold-start)
	scaleUpColdStart := false
	totalWeighted := 0.0

	for _, er := range results {
		t := sumTotalCapacity(er.result.VariantCapacities)
		if t > 0 {
			validCount++
			excessFracs = append(excessFracs, er.result.RequiredCapacity/t)
			slackFracs = append(slackFracs, er.result.SpareCapacity/t)
		} else if er.result.RequiredCapacity > 0 {
			// Cold start: demand detected but no replicas running yet.
			scaleUpColdStart = true
			validCount++
		}
		// t == 0 and RC == 0: no signal from this analyzer; skip.
		totalWeighted += er.result.RequiredCapacity * er.score
	}

	// Any-up: scale up if any analyzer's normalised excess > 0.
	maxExcess := 0.0
	for _, ex := range excessFracs {
		if ex > maxExcess {
			maxExcess = ex
		}
	}

	// All-down: scale down only when every analyzer with valid data agrees (slack > 0).
	// Cold-start entries unconditionally block scale-down.
	allDown := !scaleUpColdStart && len(slackFracs) == validCount && validCount > 0
	minSlack := math.MaxFloat64
	if allDown {
		for _, sl := range slackFracs {
			if sl <= 0 {
				allDown = false
				break
			}
			if sl < minSlack {
				minSlack = sl
			}
		}
	}

	switch {
	case scaleUpColdStart:
		// satTotal == 0: denormalisation is not possible.
		// Forward saturation's cold-start RC directly; fall back to 1.0 so the
		// optimizer adds at least one replica.
		if satResult.RequiredCapacity > 0 {
			combined.RequiredCapacity = satResult.RequiredCapacity
		} else {
			combined.RequiredCapacity = 1.0
		}
		combined.SpareCapacity = 0
	default:
		combined.RequiredCapacity = maxExcess * satTotal
		if allDown && minSlack < math.MaxFloat64 {
			combined.SpareCapacity = minSlack * satTotal
		} else {
			combined.SpareCapacity = 0
		}
	}

	combined.Score = priority * totalWeighted
	return &combined
}

// runAnalyzersAndScore runs all enabled analyzers and combines their results into a
// single AnalyzerResult for the optimizer. Saturation always runs first to populate
// VariantCapacities (Cost, AcceleratorName, Role) that the optimizer requires.
func (e *Engine) runAnalyzersAndScore(
	ctx context.Context,
	modelID, namespace string,
	replicaMetrics []interfaces.ReplicaMetrics,
	config config.SaturationScalingConfig,
	variantStates []interfaces.VariantReplicaState,
	scaleTargets map[string]scaletarget.ScaleTargetAccessor,
	variantAutoscalings map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling,
) (*interfaces.AnalyzerResult, error) {
	logger := ctrl.LoggerFrom(ctx)

	// Apply per-analyzer saturation threshold overrides before running the analyzer.
	for _, aw := range config.Analyzers {
		if aw.Name == interfaces.SaturationAnalyzerName && (aw.Enabled == nil || *aw.Enabled) {
			if aw.ScaleUpThreshold != nil {
				config.ScaleUpThreshold = *aw.ScaleUpThreshold
			}
			if aw.ScaleDownBoundary != nil {
				config.ScaleDownBoundary = *aw.ScaleDownBoundary
			}
			break
		}
	}

	// Saturation always runs — its VariantCapacities carry Cost and AcceleratorName
	// that the optimizer needs for variant selection and GPU accounting.
	satResult, err := e.runV2AnalysisOnly(ctx, modelID, namespace, replicaMetrics, config,
		variantStates, scaleTargets, variantAutoscalings)
	if err != nil {
		return nil, err
	}

	// Build AnalyzerInput once; shared by all non-saturation analyzers.
	input := interfaces.AnalyzerInput{
		ModelID:        modelID,
		Namespace:      namespace,
		ReplicaMetrics: replicaMetrics,
		VariantStates:  variantStates,
		Config:         &config,
		// SchedulerQueue: nil — wired in a later PR
	}

	// Collect results from all enabled analyzers.
	var results []enabledAnalyzerResult
	for _, aw := range config.Analyzers {
		if aw.Enabled != nil && !*aw.Enabled {
			continue
		}
		a, ok := e.analyzers[aw.Name]
		if !ok {
			logger.V(logging.DEBUG).Info("unknown analyzer in config, skipping", "name", aw.Name)
			continue
		}
		if aw.Name == interfaces.SaturationAnalyzerName {
			// Saturation already ran above; reuse its result.
			results = append(results, enabledAnalyzerResult{result: satResult, score: aw.Score})
			continue
		}
		r, err := a.Analyze(ctx, input)
		if err != nil {
			logger.Error(err, "analyzer failed, skipping", "name", aw.Name, "modelID", modelID)
			continue
		}
		results = append(results, enabledAnalyzerResult{result: r, score: aw.Score})
	}

	return combineAnalyzerResults(satResult, results, config.Priority), nil
}

// computeCurrentGPUUsage iterates over model scaling requests to compute the
// current GPU usage per accelerator type. Used to provide current usage to
// the ConstraintProvider when building GPU constraints for the optimizer.
func computeCurrentGPUUsage(requests []pipeline.ModelScalingRequest) map[string]int {
	usage := make(map[string]int)
	for _, req := range requests {
		if req.Result == nil {
			continue
		}
		stateMap := make(map[string]interfaces.VariantReplicaState, len(req.VariantStates))
		for _, s := range req.VariantStates {
			stateMap[s.VariantName] = s
		}
		for _, vc := range req.Result.VariantCapacities {
			state := stateMap[vc.VariantName]
			gpusPerReplica := state.GPUsPerReplica
			if gpusPerReplica <= 0 {
				gpusPerReplica = 1
			}
			usage[vc.AcceleratorName] += state.CurrentReplicas * gpusPerReplica
		}
	}
	return usage
}

// collectV2ModelRequest performs V2 analysis for a single model and returns
// a ModelScalingRequest for the optimizer, or nil if analysis should be skipped.
func (e *Engine) collectV2ModelRequest(
	ctx context.Context,
	modelID, namespace string,
	replicaMetrics []interfaces.ReplicaMetrics,
	config config.SaturationScalingConfig,
	variantStates []interfaces.VariantReplicaState,
	scaleTargets map[string]scaletarget.ScaleTargetAccessor,
	variantAutoscalings map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling,
) (*pipeline.ModelScalingRequest, error) {
	result, err := e.runAnalyzersAndScore(ctx, modelID, namespace, replicaMetrics, config,
		variantStates, scaleTargets, variantAutoscalings)
	if err != nil {
		return nil, fmt.Errorf("collecting V2 model request for %s/%s: %w", namespace, modelID, err)
	}

	// Detect P/D disaggregation: true when any variant has role != interfaces.RoleBoth
	disaggregated := false
	for _, vs := range variantStates {
		if vs.Role != "" && vs.Role != interfaces.RoleBoth {
			disaggregated = true
			break
		}
	}

	return &pipeline.ModelScalingRequest{
		ModelID:       modelID,
		Namespace:     namespace,
		Result:        result,
		VariantStates: variantStates,
		Priority:      config.Priority,
		Disaggregated: disaggregated,
	}, nil
}
