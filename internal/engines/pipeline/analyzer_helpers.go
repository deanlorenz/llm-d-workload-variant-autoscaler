package pipeline

import (
	"context"
	"math"

	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
)

// needsScaleUp reports whether any analyzer in s signals a need for more capacity.
// Implements the any-up gate: scale-up proceeds if at least one analyzer has Remaining > 0.
func needsScaleUp(s []NamedAnalyzerResult) bool {
	for _, e := range s {
		if e.Result != nil && e.Remaining > 0 {
			return true
		}
	}
	return false
}

// needsScaleDown reports whether all analyzers in s permit capacity removal.
// Implements the all-down gate: scale-down is blocked unless every analyzer
// has Spare > 0. Returns false for an empty slice (no consensus).
func needsScaleDown(s []NamedAnalyzerResult) bool {
	if len(s) == 0 {
		return false
	}
	for _, e := range s {
		if e.Result == nil || e.Spare <= 0 {
			return false
		}
	}
	return true
}

// bottleneckReplicas returns the number of replicas of variant v needed to
// satisfy the most-demanding analyzer. It is the maximum of
// ceil(Remaining_i / PRC_i[v]) across analyzers that have variant v with PRC > 0.
// Returns 0 if no analyzer covers variant v or all PRCs are zero (cold-start guard).
func bottleneckReplicas(s []NamedAnalyzerResult, v string) int {
	max := 0
	for _, e := range s {
		if e.Result == nil {
			continue
		}
		prc := prcForVariant(e.Result, v)
		if prc <= 0 {
			continue
		}
		n := int(math.Ceil(e.Remaining / prc))
		if n > max {
			max = n
		}
	}
	return max
}

// safeRemovalReplicas returns the number of replicas of variant v that can be
// safely removed — the minimum of floor(Spare_i / PRC_i[v]) across analyzers
// that have variant v with PRC > 0. Returns 0 if any contributing analyzer has
// Spare ≤ 0 or if no analyzer covers v.
func safeRemovalReplicas(s []NamedAnalyzerResult, v string) int {
	smallest := math.MaxInt
	found := false
	for _, e := range s {
		if e.Result == nil {
			continue
		}
		prc := prcForVariant(e.Result, v)
		if prc <= 0 {
			continue
		}
		n := int(math.Floor(e.Spare / prc))
		if n < smallest {
			smallest = n
		}
		found = true
	}
	if !found || smallest < 0 {
		return 0
	}
	return smallest
}

// applyAllocation subtracts the capacity provided by n replicas of variant v
// from each analyzer's Remaining counter. Clamps to 0. The slice is the working
// allocation state; Result.RequiredCapacity is never mutated.
//
// Contract: Remaining/Spare are engine-calibrated on entry (via the universal
// threshold post-step). Helpers do not read or mutate PendingReplicas.
func applyAllocation(s []NamedAnalyzerResult, v string, n int) {
	for i := range s {
		if s[i].Result == nil {
			continue
		}
		prc := prcForVariant(s[i].Result, v)
		if prc <= 0 {
			continue
		}
		s[i].Remaining -= float64(n) * prc
		if s[i].Remaining < 0 {
			s[i].Remaining = 0
		}
	}
}

// applyDeallocation subtracts the capacity freed by removing n replicas of
// variant v from each analyzer's Spare counter. Clamps to 0. Mutates in place.
func applyDeallocation(s []NamedAnalyzerResult, v string, n int) {
	for i := range s {
		if s[i].Result == nil {
			continue
		}
		prc := prcForVariant(s[i].Result, v)
		if prc <= 0 {
			continue
		}
		s[i].Spare -= float64(n) * prc
		if s[i].Spare < 0 {
			s[i].Spare = 0
		}
	}
}

// PickVariantFn is the optimizer-specific variant selector used by allocateForModel.
// It receives the working slice, available variants, state, GPU budget, and current
// targets, and returns the next variant to allocate to and a replica cap
// (math.MaxInt for unlimited). Returning ("", 0) signals nothing can be allocated.
type PickVariantFn func(
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
) (variant string, capN int)

// allocateForModel runs the generic scale-up inner loop for one model.
// It calls pick to select a variant and cap, computes how many replicas to add
// (bottleneckReplicas capped by capN), applies the allocation, and updates targets.
// Loops until needsScaleUp is false or pick returns no selectable variant.
func allocateForModel(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
	pick PickVariantFn,
) {
	logger := ctrl.LoggerFrom(ctx)
	for needsScaleUp(s) {
		v, capN := pick(s, variants, stateMap, available, targets)
		if v == "" {
			break
		}
		n := min(bottleneckReplicas(s, v), capN)
		if n <= 0 {
			break
		}
		applyAllocation(s, v, n)
		targets[v] += n
		logger.V(logging.DEBUG).Info("scale-up: allocated replicas",
			"variant", v, "replicas", n)
	}
}

// saturationEntry returns the saturation analyzer's result from s, or nil if not present.
// The saturation entry is the keeper of per-variant metadata (Cost, AcceleratorName, Role,
// replica counts) that the optimizer uses for variant selection and GPU accounting.
// TODO: remove the sat_v2 special role once all analyzers populate variant metadata.
func saturationEntry(s []NamedAnalyzerResult) *interfaces.AnalyzerResult {
	for _, e := range s {
		if e.Name == interfaces.SaturationAnalyzerName {
			return e.Result
		}
	}
	return nil
}

// prcForVariant returns the PerReplicaCapacity for variant v in result r.
// Returns 0 if the variant is not present.
func prcForVariant(r *interfaces.AnalyzerResult, v string) float64 {
	for _, vc := range r.VariantCapacities {
		if vc.VariantName == v {
			return vc.PerReplicaCapacity
		}
	}
	return 0
}
