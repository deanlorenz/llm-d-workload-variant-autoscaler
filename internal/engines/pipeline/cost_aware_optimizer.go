package pipeline

import (
	"context"
	"fmt"
	"math"
	"sort"

	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
)

// CostAwareOptimizer is a per-model optimizer that minimizes total cost while
// meeting capacity requirements. It processes each model independently:
//
//   - Scale-up: adds replicas to the most cost-efficient variant (lowest cost / perReplicaCapacity)
//   - Scale-down: removes replicas from the most expensive variant (highest absolute cost)
//   - Only the cheapest variant is protected at >=1 replica; others can scale to 0
//   - Variants with pending replicas are skipped for scale-up
//
// This optimizer ignores ResourceConstraints (unlimited mode). For GPU-limited
// environments, use GreedyByScoreOptimizer instead.
type CostAwareOptimizer struct{}

// NewCostAwareOptimizer creates a new CostAwareOptimizer.
func NewCostAwareOptimizer() *CostAwareOptimizer {
	return &CostAwareOptimizer{}
}

// Name returns the optimizer identifier.
func (o *CostAwareOptimizer) Name() string {
	return "cost-aware"
}

// Optimize produces VariantDecisions for all models.
// Constraints are ignored in unlimited mode (CostAwareOptimizer).
func (o *CostAwareOptimizer) Optimize(
	ctx context.Context,
	requests []ModelScalingRequest,
	constraints []*ResourceConstraints,
) []interfaces.VariantDecision {
	logger := ctrl.LoggerFrom(ctx).WithName(o.Name())
	var allDecisions []interfaces.VariantDecision

	for _, req := range requests {
		satEntry := saturationEntry(req.AnalyzerResults)
		if satEntry == nil {
			continue
		}

		stateMap := buildStateMap(req.VariantStates)
		vcMap := buildCapacityMap(satEntry.VariantCapacities)
		targets := initTargets(req.VariantStates)

		if req.Disaggregated {
			s := req.AnalyzerResults // engine guarantees a fresh slice per cycle
			initDisaggregatedRemaining(s)
			if needsScaleUp(s) {
				ps := InitRolePairedState(s)
				allocateForModelPairedB2(ctx, s, satEntry.VariantCapacities, stateMap, nil, targets,
					costGreedyPickPaired, ps, []string{"prefill", "decode"})
			} else {
				costAwareScaleDownRoleIterated(ctx, s, satEntry.VariantCapacities, targets, stateMap)
			}
		} else {
			if needsScaleUp(req.AnalyzerResults) {
				costAwareScaleUp(ctx, req.AnalyzerResults, satEntry.VariantCapacities, targets, stateMap)
			} else if needsScaleDown(req.AnalyzerResults) {
				costAwareScaleDown(ctx, req.AnalyzerResults, satEntry.VariantCapacities, targets, stateMap)
			}
		}

		decisions := buildDecisionsWithOptimizer(req, stateMap, vcMap, targets, "cost-aware")
		logger.V(logging.DEBUG).Info("Cost-aware optimizer decisions",
			"modelID", req.ModelID,
			"decisions", len(decisions))
		allDecisions = append(allDecisions, decisions...)
	}

	return allDecisions
}

// costAwareScaleUp adds replicas to the most cost-efficient variant using the
// per-analyzer slice helpers. Delegates to allocateForModel with costGreedyPick.
func costAwareScaleUp(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	targets map[string]int,
	stateMap map[string]interfaces.VariantReplicaState,
) {
	allocateForModel(ctx, s, variants, stateMap, nil, targets, costGreedyPick)
}

// costGreedyPick returns the cheapest-by-cost-efficiency variant that still has
// replica headroom. capN is the maxReplicas headroom (math.MaxInt when unlimited).
// Returns ("", 0) when all variants are at their cap or have no capacity.
func costGreedyPick(
	_ []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	_ map[string]int,
	targets map[string]int,
) (string, int) {
	sorted := sortByCostEfficiencyAsc(variants)
	for _, vc := range sorted {
		if vc.PerReplicaCapacity <= 0 {
			continue
		}
		state := stateMap[vc.VariantName]
		if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
			headroom := *state.MaxReplicas - targets[vc.VariantName]
			if headroom <= 0 {
				continue
			}
			return vc.VariantName, headroom
		}
		return vc.VariantName, math.MaxInt
	}
	return "", 0
}

// costAwareScaleDown removes replicas from the most expensive variant using the
// per-analyzer slice helpers. Iterates most-expensive-first while needsScaleDown
// holds. Cheapest-variant protection and minReplicas floor are preserved.
func costAwareScaleDown(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	targets map[string]int,
	stateMap ...map[string]interfaces.VariantReplicaState,
) {
	logger := ctrl.LoggerFrom(ctx)

	sorted := sortByCostDesc(variants)

	var states map[string]interfaces.VariantReplicaState
	if len(stateMap) > 0 {
		states = stateMap[0]
	}

	for needsScaleDown(s) {
		// removed prevents an infinite loop: needsScaleDown can hold (some Spare_i > 0)
		// while no variant has remaining capacity to give up (all at minReplicas, or
		// PRC mismatched). Break when a full sweep makes no progress.
		removed := false
		for i, vc := range sorted {
			if !needsScaleDown(s) {
				break
			}
			if vc.PerReplicaCapacity <= 0 {
				continue
			}

			current := targets[vc.VariantName]

			// Determine minReplicas: annotation floor takes priority, then cheapest-variant logic.
			minReplicas := 0
			if states != nil {
				if state, ok := states[vc.VariantName]; ok && state.MinReplicas != nil {
					minReplicas = *state.MinReplicas
				}
			}
			// Protect cheapest (last in cost-desc order) at 1 replica when it's
			// the last variant with replicas in the set.
			if i == len(sorted)-1 && !anyHasReplicas(sorted[:i], targets) && minReplicas < 1 {
				minReplicas = 1
			}

			removable := current - minReplicas
			if removable <= 0 {
				continue
			}

			n := min(safeRemovalReplicas(s, vc.VariantName), removable)
			if n <= 0 {
				continue
			}

			applyDeallocation(s, vc.VariantName, n)
			targets[vc.VariantName] = current - n
			removed = true

			logger.V(logging.DEBUG).Info("scale-down: removed replicas",
				"variant", vc.VariantName, "removed", n, "cost", vc.Cost)
		}
		if !removed {
			break
		}
	}
}

// scaleDownVariantSet removes replicas from the given variant set, most-expensive
// first, until `spare` capacity is shed or each variant's minReplicas floor is
// reached. The cheapest variant — last in the cost-descending order — is protected
// at one replica when it would otherwise be the last variant with replicas in the
// set, preventing a scale-to-zero deadlock.
func scaleDownVariantSet(
	ctx context.Context,
	variants []interfaces.VariantCapacity,
	spare float64,
	targets map[string]int,
	states map[string]interfaces.VariantReplicaState,
) {
	logger := ctrl.LoggerFrom(ctx)

	sorted := sortByCostDesc(variants)
	remaining := spare

	for i, vc := range sorted {
		if remaining <= 0 {
			break
		}
		if vc.PerReplicaCapacity <= 0 {
			continue
		}

		current := targets[vc.VariantName]

		// Annotation floor caps removal.
		minReplicas := 0
		if states != nil {
			if state, ok := states[vc.VariantName]; ok && state.MinReplicas != nil {
				minReplicas = *state.MinReplicas
			}
		}
		removable := current - minReplicas
		if removable <= 0 {
			continue
		}

		toRemove := int(math.Floor(remaining / vc.PerReplicaCapacity))
		if toRemove > removable {
			toRemove = removable
		}

		// Protect the cheapest variant (last in cost-descending order) at one
		// replica when removing toRemove would drop it below one and no
		// more-expensive variant still holds replicas — i.e. it is the last with
		// replicas in the set. When minReplicas >= 1, removable <= current-1 so
		// toRemove <= current-1 and current-toRemove >= 1 already, so this clause
		// never triggers.
		if i == len(sorted)-1 && current-toRemove < 1 && !anyHasReplicas(sorted[:i], targets) {
			toRemove = current - 1
		}
		if toRemove <= 0 {
			continue
		}

		targets[vc.VariantName] = current - toRemove
		remaining -= float64(toRemove) * vc.PerReplicaCapacity

		logger.V(logging.DEBUG).Info("Scale-down allocation",
			"variant", vc.VariantName,
			"removed", toRemove,
			"cost", vc.Cost)
	}
}

// anyHasReplicas reports whether any of the given variants has a positive target.
func anyHasReplicas(variants []interfaces.VariantCapacity, targets map[string]int) bool {
	for _, vc := range variants {
		if targets[vc.VariantName] > 0 {
			return true
		}
	}
	return false
}

// buildStateMap creates a lookup map from variant name to VariantReplicaState.
func buildStateMap(states []interfaces.VariantReplicaState) map[string]interfaces.VariantReplicaState {
	m := make(map[string]interfaces.VariantReplicaState, len(states))
	for _, s := range states {
		m[s.VariantName] = s
	}
	return m
}

// buildCapacityMap creates a lookup map from variant name to VariantCapacity.
func buildCapacityMap(capacities []interfaces.VariantCapacity) map[string]interfaces.VariantCapacity {
	m := make(map[string]interfaces.VariantCapacity, len(capacities))
	for _, vc := range capacities {
		m[vc.VariantName] = vc
	}
	return m
}

// initTargets creates initial targets from current replica counts.
func initTargets(states []interfaces.VariantReplicaState) map[string]int {
	targets := make(map[string]int, len(states))
	for _, s := range states {
		targets[s.VariantName] = s.CurrentReplicas
	}
	return targets
}

// sortByCostEfficiencyAsc returns variants sorted by cost/perReplicaCapacity ascending.
func sortByCostEfficiencyAsc(capacities []interfaces.VariantCapacity) []interfaces.VariantCapacity {
	sorted := make([]interfaces.VariantCapacity, len(capacities))
	copy(sorted, capacities)
	sort.Slice(sorted, func(i, j int) bool {
		return costEfficiency(sorted[i]) < costEfficiency(sorted[j])
	})
	return sorted
}

// sortByCostDesc returns variants sorted by absolute cost descending. Equal-cost
// variants are tie-broken by per-replica capacity ascending, so the highest-PRC
// variant at the cheapest cost tier lands last — the deterministic slot the
// scale-down protection keeps at one replica (prefer keeping the more capable
// replica among equal-cost variants).
func sortByCostDesc(capacities []interfaces.VariantCapacity) []interfaces.VariantCapacity {
	sorted := make([]interfaces.VariantCapacity, len(capacities))
	copy(sorted, capacities)
	sort.Slice(sorted, func(i, j int) bool {
		if sorted[i].Cost != sorted[j].Cost {
			return sorted[i].Cost > sorted[j].Cost
		}
		return sorted[i].PerReplicaCapacity < sorted[j].PerReplicaCapacity
	})
	return sorted
}

// costEfficiency returns the cost per unit of capacity.
func costEfficiency(vc interfaces.VariantCapacity) float64 {
	if vc.PerReplicaCapacity <= 0 {
		return math.MaxFloat64
	}
	return vc.Cost / vc.PerReplicaCapacity
}

// buildDecisionsWithOptimizer converts targets map into VariantDecision slice.
// optimizerName is included in reason strings for observability.
func buildDecisionsWithOptimizer(
	req ModelScalingRequest,
	stateMap map[string]interfaces.VariantReplicaState,
	vcMap map[string]interfaces.VariantCapacity,
	targets map[string]int,
	optimizerName string,
) []interfaces.VariantDecision {
	decisions := make([]interfaces.VariantDecision, 0, len(targets))
	for name, target := range targets {
		state := stateMap[name]
		vc := vcMap[name]

		var action interfaces.SaturationAction
		var reason string
		switch {
		case target > state.CurrentReplicas:
			action = interfaces.ActionScaleUp
			reason = fmt.Sprintf("V2 scale-up (optimizer: %s)", optimizerName)
		case target < state.CurrentReplicas:
			action = interfaces.ActionScaleDown
			reason = fmt.Sprintf("V2 scale-down (optimizer: %s)", optimizerName)
		default:
			action = interfaces.ActionNoChange
			reason = "V2 steady state"
		}

		decisions = append(decisions, interfaces.VariantDecision{
			VariantName:     name,
			ModelID:         req.ModelID,
			Namespace:       req.Namespace,
			AcceleratorName: vc.AcceleratorName,
			Cost:            vc.Cost,
			Role:            state.Role,
			CurrentReplicas: state.CurrentReplicas,
			TargetReplicas:  target,
			Action:          action,
			Reason:          reason,
			MinReplicas:     state.MinReplicas,
			MaxReplicas:     state.MaxReplicas,
		})
	}
	return decisions
}

// mergeConstraints combines GPU budget constraints from multiple providers.
// Used by GreedyByScoreOptimizer; lives here since CostAwareOptimizer owns the shared helpers.
func mergeConstraints(constraints []*ResourceConstraints) map[string]int {
	merged := make(map[string]int)
	for _, c := range constraints {
		if c == nil {
			continue
		}
		for accType, pool := range c.Pools {
			if existing, ok := merged[accType]; !ok || pool.Available() < existing {
				merged[accType] = pool.Available()
			}
		}
	}
	return merged
}

// costGreedyPickPaired selects the cheapest-by-cost-efficiency (vP, vD) pair for
// disaggregated models. Returns the cheapest eligible prefill variant and cheapest
// eligible decode variant independently, with their maxReplicas headroom as caps.
func costGreedyPickPaired(
	_ []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	_ map[string]int,
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
	pick := func(vcs []interfaces.VariantCapacity) (string, int) {
		for _, vc := range sortByCostEfficiencyAsc(vcs) {
			if vc.PerReplicaCapacity <= 0 {
				continue
			}
			state := stateMap[vc.VariantName]
			if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
				headroom := *state.MaxReplicas - targets[vc.VariantName]
				if headroom <= 0 {
					continue
				}
				return vc.VariantName, headroom
			}
			return vc.VariantName, math.MaxInt
		}
		return "", 0
	}
	vP, capNP = pick(pVCs)
	vD, capND = pick(dVCs)
	return
}

// costAwareScaleDownRoleIterated removes replicas from disaggregated models by
// iterating each role independently. P and D scale-down are independent — trimming
// one role's slack does not affect the other (each role's supply and demand are
// distinct). Per role: remove from most expensive variant first; cheapest-variant
// protection scoped to the role; minReplicas floor respected.
func costAwareScaleDownRoleIterated(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	targets map[string]int,
	stateMap ...map[string]interfaces.VariantReplicaState,
) {
	logger := ctrl.LoggerFrom(ctx)

	var states map[string]interfaces.VariantReplicaState
	if len(stateMap) > 0 {
		states = stateMap[0]
	}

	// Collect distinct roles from the variant set. Sorted for determinism (N4).
	rolesSet := make(map[string]struct{})
	for _, vc := range variants {
		role := vc.Role
		if role == "" {
			role = interfaces.RoleBoth
		}
		if role != interfaces.RoleBoth {
			rolesSet[role] = struct{}{}
		}
	}
	roles := make([]string, 0, len(rolesSet))
	for role := range rolesSet {
		roles = append(roles, role)
	}
	sort.Strings(roles)

	for _, role := range roles {
		roleVCs := variantsForRole(variants, role)
		if len(roleVCs) == 0 {
			continue
		}
		sorted := sortByCostDesc(roleVCs)

		for needsScaleDownForRole(s, role) {
			removed := false
			for i, vc := range sorted {
				if !needsScaleDownForRole(s, role) {
					break
				}
				if vc.PerReplicaCapacity <= 0 {
					continue
				}
				current := targets[vc.VariantName]
				minReplicas := 0
				if states != nil {
					if st, ok := states[vc.VariantName]; ok && st.MinReplicas != nil {
						minReplicas = *st.MinReplicas
					}
				}
				// Protect cheapest (last in cost-desc order) at 1 replica when
				// it's the last variant with replicas in the role.
				if i == len(sorted)-1 && !anyHasReplicas(sorted[:i], targets) && minReplicas < 1 {
					minReplicas = 1
				}
				removable := current - minReplicas
				if removable <= 0 {
					continue
				}
				n := min(safeRemovalReplicasForRole(s, vc.VariantName, role), removable)
				if n <= 0 {
					continue
				}
				applyDeallocationForRole(s, vc.VariantName, role, n)
				targets[vc.VariantName] -= n
				removed = true
				logger.V(logging.DEBUG).Info("scale-down role-iterated: removed replicas",
					"role", role, "variant", vc.VariantName, "removed", n, "cost", vc.Cost)
			}
			if !removed {
				break
			}
		}
	}
}

// Ensure CostAwareOptimizer implements ScalingOptimizer
var _ ScalingOptimizer = (*CostAwareOptimizer)(nil)
