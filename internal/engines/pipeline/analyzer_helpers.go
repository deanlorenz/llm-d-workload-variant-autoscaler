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

// =============================================================================
// Paired helpers — disaggregated (P/D) models
// =============================================================================

// isDisaggregated reports whether the variant set contains any role-tagged variant
// (role other than "" or "both"). Used to dispatch to the paired allocation path.
func isDisaggregated(vcs []interfaces.VariantCapacity) bool {
	for _, vc := range vcs {
		if vc.Role != "" && vc.Role != "both" {
			return true
		}
	}
	return false
}

// initDisaggregatedRemaining re-initializes the working counters in s for
// disaggregated (P/D) models before the paired allocation path:
//   - Remaining ← prefill RC (P-scope)
//   - RoleSpare[role] ← SpareCapacity for each role in RoleCapacities
//   - Model-level Spare is left unchanged (unused for disaggregated)
//
// Analyzers without RoleCapacities are left unchanged.
func initDisaggregatedRemaining(s []NamedAnalyzerResult) {
	for i := range s {
		if s[i].Result == nil || s[i].Result.RoleCapacities == nil {
			continue
		}
		s[i].Remaining = s[i].Result.RoleCapacities["prefill"].RequiredCapacity
		s[i].RoleSpare = make(map[string]float64, len(s[i].Result.RoleCapacities))
		for role, rc := range s[i].Result.RoleCapacities {
			s[i].RoleSpare[role] = rc.SpareCapacity
		}
	}
}

// analyzerAlpha computes the D:P demand coupling ratio α for one analyzer result.
// α is derived from TotalDemand — a workload invariant, not from RequiredCapacity
// (which tracks the gap relative to current supply and would tie α to allocation state).
// Returns (α, tracksP, tracksD).
//
//   - Both sides: P>0, D>0 → α = D/P; tracksP, tracksD = true
//   - P only:     P>0, D=0 → α = 0;   tracksP = true,  tracksD = false
//   - D only:     P=0, D>0 → α = 1 (Dean's default); tracksP = false, tracksD = true
//   - Neither:    P=0, D=0 → tracksP, tracksD = false
func analyzerAlpha(r *interfaces.AnalyzerResult) (alpha float64, tracksP, tracksD bool) {
	if r == nil || r.RoleCapacities == nil {
		return 0, false, false
	}
	p := r.RoleCapacities["prefill"].TotalDemand
	d := r.RoleCapacities["decode"].TotalDemand
	switch {
	case p > 0 && d > 0:
		return d / p, true, true
	case p > 0:
		return 0, true, false
	case d > 0:
		return 1, false, true
	default:
		return 0, false, false
	}
}

// bottleneckReplicasPaired computes the (n_P, n_D) replica pair needed to serve
// the current P-side remaining demand across all analyzers.
//
//	n_P = max_i (tracksP) of ceil(Remaining_i / PRC_i[vP])
//	n_D = max_i (tracksD) of ceil(α_i × Remaining_i / PRC_i[vD])
//
// Returns (0, 0) if no analyzer covers the requested sides or all PRCs are zero.
func bottleneckReplicasPaired(s []NamedAnalyzerResult, vP, vD string) (n_P, n_D int) {
	for _, e := range s {
		if e.Result == nil {
			continue
		}
		alpha, tracksP, tracksD := analyzerAlpha(e.Result)
		if tracksP {
			prc := prcForVariant(e.Result, vP)
			if prc > 0 {
				n := int(math.Ceil(e.Remaining / prc))
				if n > n_P {
					n_P = n
				}
			}
		}
		if tracksD {
			prc := prcForVariant(e.Result, vD)
			if prc > 0 {
				dRemaining := alpha * e.Remaining
				n := int(math.Ceil(dRemaining / prc))
				if n > n_D {
					n_D = n
				}
			}
		}
	}
	return
}

// variantsForRole returns variant capacities whose Role exactly matches role.
// An empty variant Role is canonicalized to interfaces.RoleBoth.
func variantsForRole(vcs []interfaces.VariantCapacity, role string) []interfaces.VariantCapacity {
	if role == "" || role == interfaces.RoleBoth {
		return vcs
	}
	var out []interfaces.VariantCapacity
	for _, vc := range vcs {
		vcRole := vc.Role
		if vcRole == "" {
			vcRole = interfaces.RoleBoth
		}
		if vcRole == role {
			out = append(out, vc)
		}
	}
	return out
}

// safeRemovalReplicasForRole returns the number of replicas of variant v that
// can safely be removed — the minimum of floor(RoleSpare[role]_i / PRC_i[v])
// across analyzers that have variant v and a non-zero PRC. Returns 0 if any
// contributing analyzer has RoleSpare[role] ≤ 0 or RoleSpare is nil.
func safeRemovalReplicasForRole(s []NamedAnalyzerResult, v, role string) int {
	smallest := math.MaxInt
	found := false
	for _, e := range s {
		if e.Result == nil || e.RoleSpare == nil {
			continue
		}
		prc := prcForVariant(e.Result, v)
		if prc <= 0 {
			continue
		}
		n := int(math.Floor(e.RoleSpare[role] / prc))
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

// applyDeallocationForRole decrements each analyzer's RoleSpare[role] by
// n × PRC_i[v]. Clamps to 0. Never mutates Result.
func applyDeallocationForRole(s []NamedAnalyzerResult, v, role string, n int) {
	for i := range s {
		if s[i].Result == nil || s[i].RoleSpare == nil {
			continue
		}
		prc := prcForVariant(s[i].Result, v)
		if prc <= 0 {
			continue
		}
		s[i].RoleSpare[role] -= float64(n) * prc
		if s[i].RoleSpare[role] < 0 {
			s[i].RoleSpare[role] = 0
		}
	}
}

// needsScaleDownForRole reports whether every analyzer agrees this role has
// spare capacity (all-down gate, scoped to one role). Returns false if any
// analyzer's RoleSpare[role] ≤ 0 or RoleSpare is nil.
func needsScaleDownForRole(s []NamedAnalyzerResult, role string) bool {
	if len(s) == 0 {
		return false
	}
	for _, e := range s {
		if e.Result == nil || e.RoleSpare == nil {
			return false
		}
		if e.RoleSpare[role] <= 0 {
			return false
		}
	}
	return true
}

// applyAllocationPaired updates each analyzer's Remaining after committing a
// paired (n_P, n_D) allocation. The capacity served in P-units is the minimum
// of what the P-side and D-side contribute (bottleneck of the pair).
// Clamps Remaining to 0. Never mutates Result.
func applyAllocationPaired(s []NamedAnalyzerResult, vP string, nP int, vD string, nD int) {
	for i := range s {
		e := &s[i]
		if e.Result == nil {
			continue
		}
		alpha, tracksP, tracksD := analyzerAlpha(e.Result)
		prcP := prcForVariant(e.Result, vP)
		prcD := prcForVariant(e.Result, vD)

		var served float64
		switch {
		case tracksP && tracksD && prcP > 0 && prcD > 0 && alpha > 0:
			// Both sides: served = min(P-capacity, D-capacity-in-P-units)
			servedP := float64(nP) * prcP
			servedD := float64(nD) * prcD / alpha
			served = math.Min(servedP, servedD)
		case tracksP && prcP > 0:
			served = float64(nP) * prcP
		case tracksD && prcD > 0 && alpha > 0:
			served = float64(nD) * prcD / alpha
		default:
			continue
		}
		e.Remaining -= served
		if e.Remaining < 0 {
			e.Remaining = 0
		}
	}
}

// PickPairFn is the optimizer-specific paired variant selector for disaggregated models.
// It returns the chosen (vP, vD) variants and per-side replica caps.
// Returning ("", "", 0, 0) signals no allocatable pair exists.
type PickPairFn func(
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
) (vP, vD string, capN_P, capN_D int)

// allocateForModelPaired runs the generic paired scale-up loop for one
// disaggregated model. Loops while needsScaleUp(s) is true and the picker
// returns a valid (vP, vD) pair. Each iteration commits one (n_P, n_D) step.
func allocateForModelPaired(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
	pick PickPairFn,
) {
	logger := ctrl.LoggerFrom(ctx)
	for needsScaleUp(s) {
		vP, vD, capNP, capND := pick(s, variants, stateMap, available, targets)
		if vP == "" || vD == "" {
			break
		}
		nP, nD := bottleneckReplicasPaired(s, vP, vD)
		nP = min(nP, capNP)
		nD = min(nD, capND)
		if nP <= 0 && nD <= 0 {
			break
		}
		applyAllocationPaired(s, vP, nP, vD, nD)
		targets[vP] += nP
		targets[vD] += nD
		logger.V(logging.DEBUG).Info("scale-up paired: allocated replicas",
			"prefill-variant", vP, "prefill-replicas", nP,
			"decode-variant", vD, "decode-replicas", nD)
	}
}
