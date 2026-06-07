package pipeline

import (
	"context"
	"math"
	"sort"

	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
)

// GreedyByScoreOptimizer is a multi-model optimizer for GPU-constrained
// environments. It uses iterative mean-based fair-sharing to distribute scarce
// GPUs across competing models, ordered by fair-share priority value
// (priority × Σᵢ(Remainingᵢ × Scoreᵢ) across analyzers).
//
// Key differences from CostAwareOptimizer:
//   - Respects ResourceConstraints (GPU budgets per accelerator type)
//   - Fair-shares GPUs across models (highest-priority model gets GPUs first)
//   - Disaggregated models use paired (n_P, n_D) allocation via the paired helpers
//   - Scale-down reuses costAwareScaleDown / costAwareScaleDownPaired
type GreedyByScoreOptimizer struct{}

// NewGreedyByScoreOptimizer creates a new GreedyByScoreOptimizer.
func NewGreedyByScoreOptimizer() *GreedyByScoreOptimizer {
	return &GreedyByScoreOptimizer{}
}

// Name returns the optimizer identifier.
func (o *GreedyByScoreOptimizer) Name() string {
	return "greedy-by-score"
}

// modelWork tracks per-model allocation state during fair-share iteration.
type modelWork struct {
	req       ModelScalingRequest
	s         []NamedAnalyzerResult      // working slice; Remaining/Spare decremented in place
	satEntry  *interfaces.AnalyzerResult // variant metadata keeper (Cost, AcceleratorName, Role)
	remaining float64                    // fair-share priority metric (negative = fully satisfied)
	targets   map[string]int             // variant name → target replicas (ALL variants)
}

// fairShareValue computes the fair-share priority metric for one model from its
// per-analyzer working slice. Returns priority × Σᵢ(Remainingᵢ × Scoreᵢ).
// Falls back to max_i(Remainingᵢ) when the weighted result is zero (priority
// unset or no score weights), matching the original fallback to RequiredCapacity.
func fairShareValue(priority float64, s []NamedAnalyzerResult) float64 {
	weighted := 0.0
	for _, e := range s {
		if e.Result != nil {
			weighted += e.Remaining * e.Score
		}
	}
	if fsv := priority * weighted; fsv > 0 {
		return fsv
	}
	// Fallback: bottleneck remaining without priority scaling.
	maxRemaining := 0.0
	for _, e := range s {
		if e.Result != nil && e.Remaining > maxRemaining {
			maxRemaining = e.Remaining
		}
	}
	return maxRemaining
}

// Optimize produces VariantDecisions for all models, fair-sharing GPUs across
// models that need to scale up. Scale-down models are handled independently.
func (o *GreedyByScoreOptimizer) Optimize(
	ctx context.Context,
	requests []ModelScalingRequest,
	constraints []*ResourceConstraints,
) []interfaces.VariantDecision {
	logger := ctrl.LoggerFrom(ctx).WithName(o.Name())
	available := mergeConstraints(constraints)

	var scaleUpWork []*modelWork
	var otherRequests []ModelScalingRequest

	for _, req := range requests {
		satEntry := saturationEntry(req.AnalyzerResults)
		if satEntry == nil {
			continue
		}

		s := make([]NamedAnalyzerResult, len(req.AnalyzerResults))
		copy(s, req.AnalyzerResults)
		if isDisaggregated(satEntry.VariantCapacities) {
			initDisaggregatedRemaining(s)
		}

		fsv := fairShareValue(req.Priority, s)
		if needsScaleUp(s) || fsv > 0 {
			w := o.buildScaleUpWork(req, satEntry, s, fsv)
			if w != nil {
				scaleUpWork = append(scaleUpWork, w)
			}
		} else {
			otherRequests = append(otherRequests, req)
		}
	}

	o.fairShareScaleUp(ctx, scaleUpWork, available)

	allDecisions := make([]interfaces.VariantDecision, 0, len(scaleUpWork))

	for _, w := range scaleUpWork {
		stateMap := buildStateMap(w.req.VariantStates)
		vcMap := buildCapacityMap(w.satEntry.VariantCapacities)
		decisions := buildDecisionsWithOptimizer(w.req, stateMap, vcMap, w.targets, "greedy-by-score")
		logger.V(logging.DEBUG).Info("Greedy-by-score optimizer decisions (scale-up)",
			"modelID", w.req.ModelID,
			"decisions", len(decisions))
		allDecisions = append(allDecisions, decisions...)
	}

	for _, req := range otherRequests {
		satEntry := saturationEntry(req.AnalyzerResults)
		if satEntry == nil {
			continue
		}

		stateMap := buildStateMap(req.VariantStates)
		vcMap := buildCapacityMap(satEntry.VariantCapacities)
		targets := initTargets(req.VariantStates)

		if isDisaggregated(satEntry.VariantCapacities) {
			s := make([]NamedAnalyzerResult, len(req.AnalyzerResults))
			copy(s, req.AnalyzerResults)
			initDisaggregatedRemaining(s)
			costAwareScaleDownRoleIterated(ctx, s, satEntry.VariantCapacities, targets, stateMap)
		} else {
			if needsScaleDown(req.AnalyzerResults) {
				costAwareScaleDown(ctx, req.AnalyzerResults, satEntry.VariantCapacities, targets, stateMap)
			}
		}

		decisions := buildDecisionsWithOptimizer(req, stateMap, vcMap, targets, "greedy-by-score")
		logger.V(logging.DEBUG).Info("Greedy-by-score optimizer decisions (other)",
			"modelID", req.ModelID,
			"decisions", len(decisions))
		allDecisions = append(allDecisions, decisions...)
	}

	return allDecisions
}

// buildScaleUpWork creates a single work unit for a scale-up request.
func (o *GreedyByScoreOptimizer) buildScaleUpWork(req ModelScalingRequest, satEntry *interfaces.AnalyzerResult, s []NamedAnalyzerResult, fsv float64) *modelWork {
	if fsv <= 0 {
		return nil
	}
	return &modelWork{
		req:       req,
		s:         s,
		satEntry:  satEntry,
		remaining: fsv,
		targets:   initTargets(req.VariantStates),
	}
}

// fairShareScaleUp implements the iterative mean-based fair-sharing algorithm.
func (o *GreedyByScoreOptimizer) fairShareScaleUp(
	ctx context.Context,
	work []*modelWork,
	available map[string]int,
) {
	logger := ctrl.LoggerFrom(ctx)

	for {
		active := filterActive(work)
		if len(active) == 0 {
			break
		}

		totalGPUs := 0
		for _, v := range available {
			totalGPUs += v
		}
		if totalGPUs == 0 {
			logger.V(logging.DEBUG).Info("GreedyByScore: no GPUs remaining, stopping fair-share")
			break
		}

		mean := computeMean(active)
		logger.V(logging.DEBUG).Info("GreedyByScore: iteration",
			"activeModels", len(active), "meanRemaining", mean)

		sortByRemainingDesc(active)
		w := active[0]

		allocationMean := mean
		if len(active) == 1 {
			allocationMean = 0
		} else if w.remaining <= mean {
			allocationMean = mean - (w.remaining / float64(len(active)))
		}

		allocated := o.allocateForModel(ctx, w, allocationMean, available)

		if !allocated {
			w.remaining = -1
			logger.V(logging.DEBUG).Info("GreedyByScore: no GPUs available for model, removing",
				"model", w.req.ModelID)
			continue
		}

		if w.remaining > mean {
			logger.V(logging.DEBUG).Info("GreedyByScore: model still above mean, removing",
				"model", w.req.ModelID, "remaining", w.remaining, "mean", mean)
			w.remaining = -1
		}
	}
}

// allocateForModel allocates replicas to bring the model's remaining score below
// the mean. Dispatches to the paired path for disaggregated models.
// After allocation, w.remaining is recomputed from the working slice.
func (o *GreedyByScoreOptimizer) allocateForModel(
	ctx context.Context,
	w *modelWork,
	mean float64,
	available map[string]int,
) bool {
	target := w.remaining - mean
	if target <= 0 {
		return false
	}

	stateMap := buildStateMap(w.req.VariantStates)
	oldRemaining := w.remaining

	if isDisaggregated(w.satEntry.VariantCapacities) {
		ps := InitRolePairedState(w.s)
		pick := fairSharePickPaired(target, w.s)
		allocateForModelPairedB2(ctx, w.s, w.satEntry.VariantCapacities, stateMap, available,
			w.targets, pick, ps, []string{"prefill", "decode"})
		// GPU budget already decremented inside allocateForModelPairedB2.
	} else {
		pick := fairSharePick(target)
		o.allocateToVariants(ctx, w, target, w.satEntry.VariantCapacities, stateMap, available, pick)
	}

	// Recompute w.remaining from the slice state after allocation.
	w.remaining = fairShareValue(w.req.Priority, w.s)
	return w.remaining < oldRemaining
}

// allocateToVariants allocates replicas from the cheapest available variants,
// capped by the fair-share pick function, GPU budget, and maxReplicas.
// Stops when the per-iteration target budget is consumed or no more replicas
// can be allocated. Updates the working slice via applyAllocation.
func (o *GreedyByScoreOptimizer) allocateToVariants(
	ctx context.Context,
	w *modelWork,
	target float64,
	capacities []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	pick PickVariantFn,
) {
	logger := ctrl.LoggerFrom(ctx)
	consumed := 0.0
	for needsScaleUp(w.s) && consumed < target {
		v, capN := pick(w.s, capacities, stateMap, available, w.targets)
		if v == "" {
			break
		}
		// Also cap by remaining budget for this iteration.
		prc := prcFromVCs(capacities, v)
		if prc > 0 {
			budgetCap := int(math.Ceil((target - consumed) / prc))
			capN = min(capN, budgetCap)
		}
		n := min(bottleneckReplicas(w.s, v), capN)
		if n <= 0 {
			break
		}
		capacityAdded := float64(n) * prc
		applyAllocation(w.s, v, n)
		w.targets[v] += n
		consumed += capacityAdded
		available[accFromVCs(capacities, v)] -= n * gpusPerReplicaFromState(stateMap, v)
		logger.V(logging.DEBUG).Info("scale-up: allocated replicas",
			"model", w.req.ModelID, "variant", v, "replicas", n,
			"budgetConsumed", consumed, "budgetTarget", target)
	}
}

// allocateToVariantsPaired was the old α-based paired loop; retired in B2.
// Greedy's disaggregated scale-up now delegates to allocateForModelPairedB2.

// fairSharePick returns a PickVariantFn that caps allocation by the fair-share
// target and GPU budget. Cheapest-first within eligible variants.
func fairSharePick(target float64) PickVariantFn {
	return func(
		_ []NamedAnalyzerResult,
		variants []interfaces.VariantCapacity,
		stateMap map[string]interfaces.VariantReplicaState,
		available map[string]int,
		targets map[string]int,
	) (string, int) {
		for _, vc := range sortByCostEfficiencyAsc(variants) {
			if vc.PerReplicaCapacity <= 0 {
				continue
			}
			state := stateMap[vc.VariantName]
			gpusPerReplica := state.GPUsPerReplica
			if gpusPerReplica <= 0 {
				gpusPerReplica = 1
			}
			gpusAvail := available[vc.AcceleratorName]
			if gpusAvail < gpusPerReplica {
				continue
			}
			fairShareCap := int(math.Ceil(target / vc.PerReplicaCapacity))
			capN := min(fairShareCap, gpusAvail/gpusPerReplica)
			if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
				headroom := *state.MaxReplicas - targets[vc.VariantName]
				if headroom <= 0 {
					continue
				}
				capN = min(capN, headroom)
			}
			if capN > 0 {
				return vc.VariantName, capN
			}
		}
		return "", 0
	}
}

// fairSharePickPaired returns a PickPairFn for disaggregated models.
// Caps each side by the fair-share target scaled by α (D:P demand ratio).
// α is derived inline from RoleCapacities[*].TotalDemand (workload invariant).
func fairSharePickPaired(target float64, s []NamedAnalyzerResult) PickPairFn {
	// Derive α = D/P from the first analyzer that has both sides > 0.
	alpha := 1.0
	for _, e := range s {
		if e.Result == nil || e.Result.RoleCapacities == nil {
			continue
		}
		p := e.Result.RoleCapacities["prefill"].TotalDemand
		d := e.Result.RoleCapacities["decode"].TotalDemand
		if p > 0 && d > 0 {
			alpha = d / p
			break
		}
	}
	return func(
		_ []NamedAnalyzerResult,
		variants []interfaces.VariantCapacity,
		stateMap map[string]interfaces.VariantReplicaState,
		available map[string]int,
		targets map[string]int,
	) (vP, vD string, capNP, capND int) {
		var pVCs, dVCs []interfaces.VariantCapacity
		for _, vc := range variants {
			switch vc.Role {
			case "prefill":
				pVCs = append(pVCs, vc)
			case "decode":
				dVCs = append(dVCs, vc)
			}
		}
		pickSide := func(vcs []interfaces.VariantCapacity, scale float64) (string, int) {
			for _, vc := range sortByCostEfficiencyAsc(vcs) {
				if vc.PerReplicaCapacity <= 0 {
					continue
				}
				state := stateMap[vc.VariantName]
				gpusPerReplica := state.GPUsPerReplica
				if gpusPerReplica <= 0 {
					gpusPerReplica = 1
				}
				gpusAvail := available[vc.AcceleratorName]
				if gpusAvail < gpusPerReplica {
					continue
				}
				fairShareCap := int(math.Ceil(target * scale / vc.PerReplicaCapacity))
				capN := min(fairShareCap, gpusAvail/gpusPerReplica)
				if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
					headroom := *state.MaxReplicas - targets[vc.VariantName]
					if headroom <= 0 {
						continue
					}
					capN = min(capN, headroom)
				}
				if capN > 0 {
					return vc.VariantName, capN
				}
			}
			return "", 0
		}
		vP, capNP = pickSide(pVCs, 1.0)
		vD, capND = pickSide(dVCs, alpha)
		return
	}
}

// filterVariantCapacitiesByRole returns variant capacities matching the specified role.
// For role RoleBoth or empty, returns all capacities.
func filterVariantCapacitiesByRole(capacities []interfaces.VariantCapacity, role string) []interfaces.VariantCapacity {
	if role == interfaces.RoleBoth || role == "" {
		return capacities
	}
	var filtered []interfaces.VariantCapacity
	for _, vc := range capacities {
		vcRole := vc.Role
		if vcRole == "" {
			vcRole = interfaces.RoleBoth
		}
		if vcRole == role {
			filtered = append(filtered, vc)
		}
	}
	return filtered
}

// filterActive returns modelWork entries that still have remaining > 0.
func filterActive(work []*modelWork) []*modelWork {
	var active []*modelWork
	for _, w := range work {
		if w.remaining > 0 {
			active = append(active, w)
		}
	}
	return active
}

// computeMean returns the average remaining across active models.
func computeMean(active []*modelWork) float64 {
	if len(active) == 0 {
		return 0
	}
	total := 0.0
	for _, w := range active {
		total += w.remaining
	}
	return total / float64(len(active))
}

// sortByRemainingDesc sorts active models by remaining descending.
func sortByRemainingDesc(active []*modelWork) {
	sort.Slice(active, func(i, j int) bool {
		return active[i].remaining > active[j].remaining
	})
}

// prcFromVCs returns the PerReplicaCapacity for variant v from a slice of VCs.
func prcFromVCs(vcs []interfaces.VariantCapacity, v string) float64 {
	for _, vc := range vcs {
		if vc.VariantName == v {
			return vc.PerReplicaCapacity
		}
	}
	return 0
}

// accFromVCs returns the AcceleratorName for variant v from a slice of VCs.
func accFromVCs(vcs []interfaces.VariantCapacity, v string) string {
	for _, vc := range vcs {
		if vc.VariantName == v {
			return vc.AcceleratorName
		}
	}
	return ""
}

// gpusPerReplicaFromState returns GPUsPerReplica for variant v, defaulting to 1.
func gpusPerReplicaFromState(stateMap map[string]interfaces.VariantReplicaState, v string) int {
	if state, ok := stateMap[v]; ok && state.GPUsPerReplica > 0 {
		return state.GPUsPerReplica
	}
	return 1
}

// Ensure GreedyByScoreOptimizer implements ScalingOptimizer
var _ ScalingOptimizer = (*GreedyByScoreOptimizer)(nil)
