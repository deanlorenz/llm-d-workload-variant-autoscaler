package pipeline

import (
	"context"
	"math"
	"sort"

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

// initRoleState initialises picker-local role state for one model's allocation pass.
// It unifies disaggregated and non-disaggregated models into one (model, role) view:
//
//   - Disaggregated (RoleCapacities != nil): roles = sorted keys of RoleCapacities;
//     per-role RC → pickerState[i][role]; per-role SC → s[i].RoleSpare[role].
//   - Non-disaggregated (RoleCapacities == nil): one synthetic role "both" using
//     the engine-calibrated model-level RC/SC (Result.RequiredCapacity / SpareCapacity).
//     No re-aggregation — the engine already summed all variants into those scalars.
//
// Returns the list of active roles and the picker-local RolePairedState.
// Remaining/Spare scalars on NamedAnalyzerResult are read-only after this call;
// all dynamic bookkeeping moves to pickerState (scale-up) and RoleSpare (scale-down).
func initRoleState(s []NamedAnalyzerResult) (roles []string, pickerState RolePairedState) {
	pickerState = make(RolePairedState, len(s))
	roleSet := make(map[string]struct{})

	for i, e := range s {
		pickerState[i] = make(map[string]float64)
		if e.Result == nil {
			continue
		}
		if e.Result.RoleCapacities != nil {
			// Disaggregated: per-role RC/SC from engine-calibrated RoleCapacities.
			if s[i].RoleSpare == nil {
				s[i].RoleSpare = make(map[string]float64, len(e.Result.RoleCapacities))
			}
			for role, rc := range e.Result.RoleCapacities {
				pickerState[i][role] = rc.RequiredCapacity
				s[i].RoleSpare[role] = rc.SpareCapacity
				roleSet[role] = struct{}{}
			}
		} else {
			// Non-disaggregated: synthesize a single "both" role from model-level scalars.
			pickerState[i][interfaces.RoleBoth] = e.Remaining
			if s[i].RoleSpare == nil {
				s[i].RoleSpare = make(map[string]float64, 1)
			}
			s[i].RoleSpare[interfaces.RoleBoth] = e.Spare
			roleSet[interfaces.RoleBoth] = struct{}{}
		}
	}

	roles = make([]string, 0, len(roleSet))
	for role := range roleSet {
		roles = append(roles, role)
	}
	sort.Strings(roles)
	return
}

// initDisaggregatedRemaining is kept as a wrapper for call sites not yet
// migrated to initRoleState. Preserves the pre-Phase-3 behaviour of setting
// Remaining to the prefill RC (P-anchor). New code should call initRoleState.
func initDisaggregatedRemaining(s []NamedAnalyzerResult) {
	_, _ = initRoleState(s) // side-effect: populates RoleSpare
	// Preserve P-anchor: set Remaining from prefill RC so needsScaleUp(s) works
	// for callers that haven't moved to anyRoleNeedsScaleUp yet.
	for i := range s {
		if s[i].Result == nil || s[i].Result.RoleCapacities == nil {
			continue
		}
		s[i].Remaining = s[i].Result.RoleCapacities["prefill"].RequiredCapacity
	}
}

// =============================================================================
// B2 paired scale-up helpers (per-role independent sizing + joint-commit trim)
// =============================================================================
//
// Design § Architecture/D: (model, role) is the unit of allocation math.
// Per-role sizing uses the same bottleneck primitives as non-disaggregated
// allocation, scoped to one role. The joint-commit step bounds by the min-util
// role (the coupling constraint). α no longer appears in serve-math — only in
// picker sizing when one role's demand is derived from the other.
//
// RolePairedState holds picker-local per-role demand tracked during one
// model's allocation pass. Indexed as [analyzer-index][role] → remaining demand
// (in that role's own capacity units). Initialized from RoleCapacities[role].RC;
// decremented per joint commit. Lives only inside the allocation loop — not
// stored on NamedAnalyzerResult (per design A10).
type RolePairedState []map[string]float64

// InitRolePairedState is kept as a wrapper for call sites not yet migrated to
// initRoleState. New code should call initRoleState directly.
func InitRolePairedState(s []NamedAnalyzerResult) RolePairedState {
	_, ps := initRoleState(s)
	return ps
}

// roleBottleneckReplicas computes the cross-analyzer bottleneck replica count
// for variant v in a specific role. Returns max_i ceil(state[i][role] / PRC_i[v]).
func roleBottleneckReplicas(s []NamedAnalyzerResult, state RolePairedState, role, v string) int {
	max := 0
	for i, e := range s {
		if e.Result == nil {
			continue
		}
		prc := prcForVariant(e.Result, v)
		if prc <= 0 {
			continue
		}
		n := int(math.Ceil(state[i][role] / prc))
		if n > max {
			max = n
		}
	}
	return max
}

// roleAggRemaining returns max cross-analyzer remaining demand for role.
func roleAggRemaining(s []NamedAnalyzerResult, state RolePairedState, role string) float64 {
	max := 0.0
	for i := range s {
		if d := state[i][role]; d > max {
			max = d
		}
	}
	return max
}

// anyRoleNeedsScaleUp is the Phase-3 per-role scale-up gate used by the unified
// dispatcher. It replaces both needsScaleUp (model-level) and needsScaleUpPaired.
// Returns true when any role has aggregate remaining demand > 0.
func anyRoleNeedsScaleUp(state RolePairedState, roles []string) bool {
	for _, role := range roles {
		for _, m := range state {
			if m[role] > 0 {
				return true
			}
		}
	}
	return false
}

// needsScaleUpPaired reports whether any role still has aggregate remaining demand > 0.
func needsScaleUpPaired(s []NamedAnalyzerResult, state RolePairedState, roles []string) bool {
	for _, role := range roles {
		if roleAggRemaining(s, state, role) > 0 {
			return true
		}
	}
	return false
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

// PickPairFn is the optimizer-specific paired variant selector for disaggregated models.
// It returns the chosen (vP, vD) variants and per-side replica caps (GPU budget +
// maxReplicas headroom). Returning ("", "", 0, 0) signals no allocatable pair exists.
type PickPairFn func(
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
) (vP, vD string, capN_P, capN_D int)

// allocateForModelPairedB2 runs the B2 paired scale-up loop for one disaggregated
// model. Per-role sizing is independent (same bottleneck primitive as non-disag,
// scoped to each role's picker-local demand). Joint commit is bounded by
// min_role { util_role } to advance both roles by the same utilization delta.
//
// 0-cases (per design § Architecture/D):
//   - Demand_role = 0 → util_role = 1 (role drops from min).
//   - Demand_role > 0, no capacity → util_role = 0 → joint bound = 0.
func allocateForModelPairedB2(
	ctx context.Context,
	s []NamedAnalyzerResult,
	variants []interfaces.VariantCapacity,
	stateMap map[string]interfaces.VariantReplicaState,
	available map[string]int,
	targets map[string]int,
	pick PickPairFn,
	pickerState RolePairedState,
	roles []string,
) {
	logger := ctrl.LoggerFrom(ctx)
	for needsScaleUpPaired(s, pickerState, roles) {
		vP, vD, capNP, capND := pick(s, variants, stateMap, available, targets)
		if vP == "" || vD == "" {
			break
		}
		prcP := prcFromVCs(variants, vP)
		prcD := prcFromVCs(variants, vD)
		if prcP <= 0 || prcD <= 0 {
			break
		}

		// Per-role independent sizing capped by picker resource limits.
		nP := min(roleBottleneckReplicas(s, pickerState, "prefill", vP), capNP)
		nD := min(roleBottleneckReplicas(s, pickerState, "decode", vD), capND)

		// Aggregate demand per role for util computation.
		demandP := roleAggRemaining(s, pickerState, "prefill")
		demandD := roleAggRemaining(s, pickerState, "decode")

		// util_role = served / demand (0-case: demand=0 → util=1, drops from min).
		var utilP, utilD float64
		if demandP <= 0 {
			utilP = 1.0
		} else {
			utilP = float64(nP) * prcP / demandP
		}
		if demandD <= 0 {
			utilD = 1.0
		} else {
			utilD = float64(nD) * prcD / demandD
		}

		deltaUtil := math.Min(utilP, utilD)
		if deltaUtil <= 0 {
			break
		}

		// Trim over-allocated role to the joint util bound.
		// floor(Δ_util × demand / prc) trims integer replicas to the bottleneck util.
		// When demand < prc (one replica over-serves), floor rounds to 0 — use
		// min(1, n_role) as minimum so fractional demand still gets a replica.
		kP, kD := 0, 0
		if prcP > 0 && demandP > 0 {
			kP = max(int(math.Floor(deltaUtil*demandP/prcP)), min(1, nP))
		}
		if prcD > 0 && demandD > 0 {
			kD = max(int(math.Floor(deltaUtil*demandD/prcD)), min(1, nD))
		}
		if kP <= 0 && kD <= 0 {
			break
		}

		// Commit.
		targets[vP] += kP
		targets[vD] += kD
		for i := range pickerState {
			pickerState[i]["prefill"] = math.Max(0, pickerState[i]["prefill"]-float64(kP)*prcP)
			pickerState[i]["decode"] = math.Max(0, pickerState[i]["decode"]-float64(kD)*prcD)
		}
		applyAllocation(s, vP, kP) // decrement model-level Remaining (P-anchor)
		if available != nil {
			available[accFromVCs(variants, vP)] -= kP * gpusPerReplicaFromState(stateMap, vP)
			available[accFromVCs(variants, vD)] -= kD * gpusPerReplicaFromState(stateMap, vD)
		}

		logger.V(logging.DEBUG).Info("scale-up paired B2: joint commit",
			"vP", vP, "kP", kP, "vD", vD, "kD", kD, "deltaUtil", deltaUtil)
	}
}
