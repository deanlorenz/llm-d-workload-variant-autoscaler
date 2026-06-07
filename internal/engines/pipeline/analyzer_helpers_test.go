package pipeline

import (
	"context"
	"math"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// makeNamed builds a NamedAnalyzerResult with the given RC, SC, and per-variant
// (variantName, perReplicaCapacity) pairs.
func makeNamed(name string, RC, SC float64, vcs ...any) NamedAnalyzerResult {
	var caps []interfaces.VariantCapacity
	for i := 0; i+1 < len(vcs); i += 2 {
		vName := vcs[i].(string)
		prc := vcs[i+1].(float64)
		caps = append(caps, interfaces.VariantCapacity{
			VariantName:        vName,
			PerReplicaCapacity: prc,
		})
	}
	return NamedAnalyzerResult{
		Name: name,
		Result: &interfaces.AnalyzerResult{
			RequiredCapacity:  RC,
			SpareCapacity:     SC,
			VariantCapacities: caps,
		},
		Remaining: RC,
		Spare:     SC,
	}
}

var _ = Describe("analyzer helpers", func() {

	Describe("needsScaleUp", func() {
		It("returns false for empty slice", func() {
			Expect(needsScaleUp(nil)).To(BeFalse())
		})

		It("returns false when all RC = 0", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 100, "v", 10.0),
				makeNamed("ta", 0, 50, "v", 10.0),
			}
			Expect(needsScaleUp(s)).To(BeFalse())
		})

		It("returns true when any analyzer has RC > 0 (any-up)", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 0, "v", 10.0),
				makeNamed("ta", 20, 0, "v", 10.0),
			}
			Expect(needsScaleUp(s)).To(BeTrue())
		})

		It("skips nil results", func() {
			s := []NamedAnalyzerResult{
				{Name: "sat", Result: nil},
			}
			Expect(needsScaleUp(s)).To(BeFalse())
		})
	})

	Describe("needsScaleDown", func() {
		It("returns false for empty slice (no consensus)", func() {
			Expect(needsScaleDown(nil)).To(BeFalse())
		})

		It("returns true when all analyzers have SC > 0 (all-down)", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 100, "v", 10.0),
				makeNamed("ta", 0, 30, "v", 10.0),
			}
			Expect(needsScaleDown(s)).To(BeTrue())
		})

		It("returns false when any analyzer has SC = 0 (all-down blocked)", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 100, "v", 10.0),
				makeNamed("ta", 0, 0, "v", 10.0),
			}
			Expect(needsScaleDown(s)).To(BeFalse())
		})

		It("returns false for nil result entry", func() {
			s := []NamedAnalyzerResult{
				{Name: "sat", Result: nil},
			}
			Expect(needsScaleDown(s)).To(BeFalse())
		})
	})

	Describe("bottleneckReplicas", func() {
		It("returns ceil(RC/PRC) for a single analyzer — pass-through", func() {
			// RC=200, PRC=600 → ceil(200/600) = 1
			s := []NamedAnalyzerResult{makeNamed("sat", 200, 0, "v", 600.0)}
			Expect(bottleneckReplicas(s, "v")).To(Equal(1))
		})

		It("returns the max across analyzers when sat has larger signal", func() {
			// sat: RC=200, PRC=600 → ceil(200/600)=1
			// ta:  RC=5,   PRC=10  → ceil(5/10)=1
			s := []NamedAnalyzerResult{
				makeNamed("sat", 200, 0, "v", 600.0),
				makeNamed("ta", 5, 0, "v", 10.0),
			}
			Expect(bottleneckReplicas(s, "v")).To(Equal(1))
		})

		It("returns the max across analyzers when non-sat has larger signal", func() {
			// sat: RC=50,  PRC=600 → ceil(50/600)=1
			// ta:  RC=30,  PRC=10  → ceil(30/10)=3
			s := []NamedAnalyzerResult{
				makeNamed("sat", 50, 0, "v", 600.0),
				makeNamed("ta", 30, 0, "v", 10.0),
			}
			Expect(bottleneckReplicas(s, "v")).To(Equal(3))
		})

		It("returns 0 when PRC = 0 (cold-start guard)", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 250, 0, "v", 0.0)}
			Expect(bottleneckReplicas(s, "v")).To(Equal(0))
		})

		It("returns 0 when variant is absent from all analyzers", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 200, 0, "other", 100.0)}
			Expect(bottleneckReplicas(s, "v")).To(Equal(0))
		})

		It("ignores nil result entries", func() {
			s := []NamedAnalyzerResult{
				{Name: "sat", Result: nil},
				makeNamed("ta", 20, 0, "v", 10.0),
			}
			Expect(bottleneckReplicas(s, "v")).To(Equal(2))
		})
	})

	Describe("safeRemovalReplicas", func() {
		It("returns floor(SC/PRC) for a single analyzer — pass-through", func() {
			// SC=150, PRC=100 → floor(150/100) = 1
			s := []NamedAnalyzerResult{makeNamed("sat", 0, 150, "v", 100.0)}
			Expect(safeRemovalReplicas(s, "v")).To(Equal(1))
		})

		It("returns the min when both analyzers agree on scale-down", func() {
			// sat: SC=100, PRC=100 → floor=1
			// ta:  SC=300, PRC=100 → floor=3; min=1
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 100, "v", 100.0),
				makeNamed("ta", 0, 300, "v", 100.0),
			}
			Expect(safeRemovalReplicas(s, "v")).To(Equal(1))
		})

		It("returns 0 when any analyzer has SC = 0 (all-down blocked)", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 100, "v", 100.0),
				makeNamed("ta", 0, 0, "v", 100.0),
			}
			Expect(safeRemovalReplicas(s, "v")).To(Equal(0))
		})

		It("returns 0 when variant is absent", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 0, 100, "other", 100.0)}
			Expect(safeRemovalReplicas(s, "v")).To(Equal(0))
		})
	})

	Describe("applyAllocation", func() {
		It("subtracts n×PRC from each analyzer's Remaining counter", func() {
			// PRC=100, n=2 → subtract 200 from each Remaining
			s := []NamedAnalyzerResult{
				makeNamed("sat", 500, 0, "v", 100.0),
				makeNamed("ta", 300, 0, "v", 100.0),
			}
			applyAllocation(s, "v", 2)
			Expect(s[0].Remaining).To(BeNumerically("~", 300.0, 1e-9))
			Expect(s[1].Remaining).To(BeNumerically("~", 100.0, 1e-9))
			// Result.RequiredCapacity is not mutated
			Expect(s[0].Result.RequiredCapacity).To(Equal(500.0))
		})

		It("clamps Remaining to 0", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 50, 0, "v", 100.0)}
			applyAllocation(s, "v", 2) // would subtract 200 from 50
			Expect(s[0].Remaining).To(Equal(0.0))
		})

		It("is a no-op for variants not in the result", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 200, 0, "other", 100.0)}
			applyAllocation(s, "v", 3)
			Expect(s[0].Remaining).To(Equal(200.0))
		})
	})

	Describe("applyDeallocation", func() {
		It("subtracts n×PRC from each analyzer's Spare counter", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 0, 500, "v", 100.0),
				makeNamed("ta", 0, 300, "v", 100.0),
			}
			applyDeallocation(s, "v", 2)
			Expect(s[0].Spare).To(BeNumerically("~", 300.0, 1e-9))
			Expect(s[1].Spare).To(BeNumerically("~", 100.0, 1e-9))
			// Result.SpareCapacity is not mutated
			Expect(s[0].Result.SpareCapacity).To(Equal(500.0))
		})

		It("clamps Spare to 0", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 0, 50, "v", 100.0)}
			applyDeallocation(s, "v", 2)
			Expect(s[0].Spare).To(Equal(0.0))
		})
	})

	Describe("allocateForModel", func() {
		It("allocates until needsScaleUp is false", func() {
			// Two variants: cheap (PRC=10) and expensive (PRC=20)
			// RC=30 from saturation only
			s := []NamedAnalyzerResult{
				makeNamed("sat", 30, 0, "cheap", 10.0, "expensive", 20.0),
			}
			variants := []interfaces.VariantCapacity{
				{VariantName: "cheap", PerReplicaCapacity: 10},
				{VariantName: "expensive", PerReplicaCapacity: 20},
			}
			targets := map[string]int{"cheap": 1, "expensive": 1}

			// Pick always returns "cheap" with unlimited cap
			pick := func(_ []NamedAnalyzerResult, _ []interfaces.VariantCapacity,
				_ map[string]interfaces.VariantReplicaState,
				_ map[string]int, _ map[string]int) (string, int) {
				return "cheap", math.MaxInt
			}
			allocateForModel(context.Background(), s, variants, nil, nil, targets, pick)

			// ceil(30/10) = 3 replicas should have been added to "cheap"
			Expect(targets["cheap"]).To(Equal(4)) // 1 initial + 3 allocated
			Expect(needsScaleUp(s)).To(BeFalse())
		})

		It("stops when pick returns empty string", func() {
			s := []NamedAnalyzerResult{
				makeNamed("sat", 100, 0, "v", 10.0),
			}
			targets := map[string]int{"v": 0}
			calls := 0
			pick := func(_ []NamedAnalyzerResult, _ []interfaces.VariantCapacity,
				_ map[string]interfaces.VariantReplicaState,
				_ map[string]int, _ map[string]int) (string, int) {
				calls++
				return "", 0
			}
			allocateForModel(context.Background(), s, nil, nil, nil, targets, pick)
			Expect(calls).To(Equal(1))
			Expect(targets["v"]).To(Equal(0))
		})
	})

	Describe("saturationEntry", func() {
		It("returns the saturation result from the slice", func() {
			satResult := &interfaces.AnalyzerResult{RequiredCapacity: 42}
			s := []NamedAnalyzerResult{
				{Name: interfaces.SaturationAnalyzerName, Result: satResult},
				makeNamed("ta", 10, 0),
			}
			Expect(saturationEntry(s)).To(BeIdenticalTo(satResult))
		})

		It("returns nil when saturation is absent", func() {
			s := []NamedAnalyzerResult{makeNamed("ta", 10, 0)}
			Expect(saturationEntry(s)).To(BeNil())
		})
	})
})

// makeNamedPD builds a NamedAnalyzerResult with RoleCapacities for P/D tests.
// RoleSpare is initialized from pSC/dSC (as initDisaggregatedRemaining would do).
func makeNamedPD(name string, pRC, dRC, pSC, dSC float64, pDemand, dDemand float64, vPName string, vPPRC float64, vDName string, vDPRC float64) NamedAnalyzerResult {
	return NamedAnalyzerResult{
		Name: name,
		Result: &interfaces.AnalyzerResult{
			VariantCapacities: []interfaces.VariantCapacity{
				{VariantName: vPName, Role: "prefill", PerReplicaCapacity: vPPRC},
				{VariantName: vDName, Role: "decode", PerReplicaCapacity: vDPRC},
			},
			RoleCapacities: map[string]interfaces.RoleCapacity{
				"prefill": {Role: "prefill", RequiredCapacity: pRC, SpareCapacity: pSC, TotalDemand: pDemand},
				"decode":  {Role: "decode", RequiredCapacity: dRC, SpareCapacity: dSC, TotalDemand: dDemand},
			},
		},
		Remaining: pRC, // P-scope after initDisaggregatedRemaining
		RoleSpare: map[string]float64{"prefill": pSC, "decode": dSC},
	}
}

var _ = Describe("paired helpers", func() {

	Describe("isDisaggregated", func() {
		It("returns true when any variant has a non-empty non-both role", func() {
			vcs := []interfaces.VariantCapacity{
				{VariantName: "pf", Role: "prefill"},
				{VariantName: "dc", Role: "decode"},
			}
			Expect(isDisaggregated(vcs)).To(BeTrue())
		})

		It("returns false when all variants have no role", func() {
			vcs := []interfaces.VariantCapacity{
				{VariantName: "v1", Role: ""},
				{VariantName: "v2", Role: "both"},
			}
			Expect(isDisaggregated(vcs)).To(BeFalse())
		})

		It("returns false for empty slice", func() {
			Expect(isDisaggregated(nil)).To(BeFalse())
		})
	})

	Describe("InitRolePairedState", func() {
		It("initializes per-role demand from RoleCapacities.RequiredCapacity", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 15000, 5000, 0, 0, 15000, 5000, "pf", 10000, "dc", 10000)}
			ps := InitRolePairedState(s)
			Expect(ps[0]["prefill"]).To(BeNumerically("~", 15000.0, 1e-9))
			Expect(ps[0]["decode"]).To(BeNumerically("~", 5000.0, 1e-9))
		})

		It("returns zero map for analyzer without RoleCapacities", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 20000, 0, "v", 10.0)}
			ps := InitRolePairedState(s)
			Expect(ps[0]["prefill"]).To(Equal(0.0))
			Expect(ps[0]["decode"]).To(Equal(0.0))
		})
	})

	Describe("initRoleState", func() {
		It("disaggregated: roles from RoleCapacities; picker-state from RC; RoleSpare from SC", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 15000, 5000, 20000, 10000, 15000, 5000, "pf", 10000, "dc", 10000)}
			roles, ps := initRoleState(s)
			Expect(roles).To(ConsistOf("prefill", "decode"))
			Expect(ps[0]["prefill"]).To(BeNumerically("~", 15000.0, 1e-9))
			Expect(ps[0]["decode"]).To(BeNumerically("~", 5000.0, 1e-9))
			Expect(s[0].RoleSpare["prefill"]).To(BeNumerically("~", 20000.0, 1e-9))
			Expect(s[0].RoleSpare["decode"]).To(BeNumerically("~", 10000.0, 1e-9))
		})

		It("non-disaggregated: synthetic 'both' role using model-level Remaining/Spare", func() {
			s := []NamedAnalyzerResult{makeNamed("sat", 20000, 5000, "v", 10.0)}
			roles, ps := initRoleState(s)
			Expect(roles).To(ConsistOf(interfaces.RoleBoth))
			Expect(ps[0][interfaces.RoleBoth]).To(BeNumerically("~", 20000.0, 1e-9))
			Expect(s[0].RoleSpare[interfaces.RoleBoth]).To(BeNumerically("~", 5000.0, 1e-9))
		})
	})

	Describe("roleBottleneckReplicas", func() {
		It("computes max cross-analyzer ceil(roleRemaining/PRC)", func() {
			// analyzer0: prefill remaining=10000, PRC=5000 → ceil(10000/5000)=2
			// analyzer1: prefill remaining=15000, PRC=5000 → ceil(15000/5000)=3 (max)
			s := []NamedAnalyzerResult{
				makeNamedPD("sat", 10000, 20000, 0, 0, 10000, 20000, "pf", 5000, "dc", 8000),
				makeNamedPD("ta", 15000, 15000, 0, 0, 15000, 15000, "pf", 5000, "dc", 8000),
			}
			ps := InitRolePairedState(s)
			Expect(roleBottleneckReplicas(s, ps, "prefill", "pf")).To(Equal(3))
			// decode: max(ceil(20000/8000)=3, ceil(15000/8000)=2) = 3
			Expect(roleBottleneckReplicas(s, ps, "decode", "dc")).To(Equal(3))
		})

		It("returns 0 when PRC=0 (cold-start guard)", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 10000, 20000, 0, 0, 10000, 20000, "pf", 0, "dc", 0)}
			ps := InitRolePairedState(s)
			Expect(roleBottleneckReplicas(s, ps, "prefill", "pf")).To(Equal(0))
		})
	})

	Describe("needsScaleUpPaired", func() {
		It("returns true when any role has aggregate remaining demand", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 10000, 5000, 0, 0, 10000, 5000, "pf", 10000, "dc", 10000)}
			ps := InitRolePairedState(s)
			Expect(needsScaleUpPaired(s, ps, []string{"prefill", "decode"})).To(BeTrue())
		})

		It("returns false when all roles have zero remaining demand", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 0, 0, 10000, 5000, "pf", 10000, "dc", 10000)}
			ps := InitRolePairedState(s)
			Expect(needsScaleUpPaired(s, ps, []string{"prefill", "decode"})).To(BeFalse())
		})
	})

	Describe("safeRemovalReplicasForRole", func() {
		It("computes removable replicas from RoleSpare for a given role", func() {
			// RoleSpare["prefill"]=20000, PRC_P=10000 → floor(20000/10000)=2
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 20000, 30000, 10000, 30000, "pf", 10000, "dc", 10000)}
			Expect(safeRemovalReplicasForRole(s, "pf", "prefill")).To(Equal(2))
			// RoleSpare["decode"]=30000, PRC_D=10000 → floor(30000/10000)=3
			Expect(safeRemovalReplicasForRole(s, "dc", "decode")).To(Equal(3))
		})

		It("returns 0 when RoleSpare for role is 0", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 0, 30000, 10000, 30000, "pf", 10000, "dc", 10000)}
			Expect(safeRemovalReplicasForRole(s, "pf", "prefill")).To(Equal(0))
		})

		It("returns 0 when RoleSpare is nil", func() {
			e := makeNamed("sat", 0, 100, "v", 10.0)
			e.RoleSpare = nil
			Expect(safeRemovalReplicasForRole([]NamedAnalyzerResult{e}, "v", "prefill")).To(Equal(0))
		})
	})

	Describe("applyDeallocationForRole", func() {
		It("decrements RoleSpare[role] by n×PRC", func() {
			// RoleSpare["prefill"]=20000, PRC=10000, n=2 → 20000-20000=0
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 20000, 30000, 10000, 30000, "pf", 10000, "dc", 10000)}
			applyDeallocationForRole(s, "pf", "prefill", 2)
			Expect(s[0].RoleSpare["prefill"]).To(Equal(0.0))
			// decode spare unchanged
			Expect(s[0].RoleSpare["decode"]).To(BeNumerically("~", 30000.0, 1e-9))
		})

		It("clamps RoleSpare to 0", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 5000, 0, 10000, 0, "pf", 10000, "dc", 10000)}
			applyDeallocationForRole(s, "pf", "prefill", 5) // would subtract 50000
			Expect(s[0].RoleSpare["prefill"]).To(Equal(0.0))
		})
	})

	Describe("needsScaleDownForRole", func() {
		It("returns true when all analyzers have RoleSpare[role] > 0", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 20000, 30000, 10000, 30000, "pf", 10000, "dc", 10000)}
			Expect(needsScaleDownForRole(s, "prefill")).To(BeTrue())
			Expect(needsScaleDownForRole(s, "decode")).To(BeTrue())
		})

		It("returns false when any analyzer has RoleSpare[role] = 0", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 0, 0, 0, 30000, 10000, 30000, "pf", 10000, "dc", 10000)}
			Expect(needsScaleDownForRole(s, "prefill")).To(BeFalse())
			Expect(needsScaleDownForRole(s, "decode")).To(BeTrue())
		})

		It("returns false for nil RoleSpare", func() {
			e := makeNamed("sat", 0, 100, "v", 10.0)
			e.RoleSpare = nil
			Expect(needsScaleDownForRole([]NamedAnalyzerResult{e}, "prefill")).To(BeFalse())
		})
	})

	Describe("variantsForRole", func() {
		It("filters variants by exact role match", func() {
			vcs := []interfaces.VariantCapacity{
				{VariantName: "pf", Role: "prefill"},
				{VariantName: "dc", Role: "decode"},
				{VariantName: "both", Role: "both"},
			}
			Expect(variantsForRole(vcs, "prefill")).To(HaveLen(1))
			Expect(variantsForRole(vcs, "prefill")[0].VariantName).To(Equal("pf"))
			Expect(variantsForRole(vcs, "decode")[0].VariantName).To(Equal("dc"))
		})

		It("returns all variants for role 'both' or empty", func() {
			vcs := []interfaces.VariantCapacity{
				{VariantName: "pf", Role: "prefill"},
				{VariantName: "dc", Role: "decode"},
			}
			Expect(variantsForRole(vcs, "both")).To(HaveLen(2))
			Expect(variantsForRole(vcs, "")).To(HaveLen(2))
		})
	})

	Describe("allocateForModelPairedB2", func() {
		// B2.1 — Joint-commit atomicity: one role exhausted.
		It("B2.1: commits only what both roles can satisfy (decode exhausted → kP=0, kD=0)", func() {
			// P-demand=10000, D-demand=0 (no decode demand) → decode drops from min (util=1).
			// Reduced to single-role P allocation.
			s := []NamedAnalyzerResult{makeNamedPD("sat", 10000, 0, 0, 0, 10000, 0, "pf", 5000, "dc", 8000)}
			variants := []interfaces.VariantCapacity{
				{VariantName: "pf", Role: "prefill", PerReplicaCapacity: 5000},
				{VariantName: "dc", Role: "decode", PerReplicaCapacity: 8000},
			}
			targets := map[string]int{"pf": 1, "dc": 3}
			ps := InitRolePairedState(s)
			pick := func(_ []NamedAnalyzerResult, _ []interfaces.VariantCapacity,
				_ map[string]interfaces.VariantReplicaState,
				_ map[string]int, _ map[string]int) (string, string, int, int) {
				return "pf", "dc", math.MaxInt, math.MaxInt
			}
			allocateForModelPairedB2(context.Background(), s, variants, nil, nil, targets, pick, ps, []string{"prefill", "decode"})
			// Only P has demand; decode drops from min → single-role P allocation
			// demandP=10000, prcP=5000: nP=2, util_P=2*5000/10000=1.0, util_D=1.0 (demand=0)
			// Δ_util=1.0, kP=floor(1.0*10000/5000)=2, kD=floor(1.0*0/8000)=0
			Expect(targets["pf"]).To(Equal(3)) // 1 + 2
			Expect(targets["dc"]).To(Equal(3)) // unchanged (kD=0)
		})

		// B2.2 — Util-bottleneck trim: ceil-rounded sizing over-allocates one role.
		// Step 1: nP=4 (ceil(10000/3000)), nD=1 (ceil(10000/10000)).
		//   util_P=1.2, util_D=1.0 → Δ_util=1.0 → kP=floor(3.33)=3 (trim!), kD=1.
		//   After step 1: P-remaining=10000-9000=1000, D-remaining=0.
		// Step 2: P still has demand; D has none → commits 1 more P replica.
		//   Final: kP=4, kD=1. The trim in step 1 prevented over-committing D.
		It("B2.2: util-bottleneck trim — each step advances both roles by same Δ_util", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 10000, 10000, 0, 0, 10000, 10000, "pf", 3000, "dc", 10000)}
			variants := []interfaces.VariantCapacity{
				{VariantName: "pf", Role: "prefill", PerReplicaCapacity: 3000},
				{VariantName: "dc", Role: "decode", PerReplicaCapacity: 10000},
			}
			targets := map[string]int{"pf": 0, "dc": 0}
			ps := InitRolePairedState(s)
			pick := func(_ []NamedAnalyzerResult, _ []interfaces.VariantCapacity,
				_ map[string]interfaces.VariantReplicaState,
				_ map[string]int, _ map[string]int) (string, string, int, int) {
				return "pf", "dc", math.MaxInt, math.MaxInt
			}
			allocateForModelPairedB2(context.Background(), s, variants, nil, nil, targets, pick, ps, []string{"prefill", "decode"})
			// Both roles fully served at end (no over-commitment beyond demand).
			Expect(needsScaleUpPaired(s, ps, []string{"prefill", "decode"})).To(BeFalse())
			// D satisfied in 1 replica (trim prevented committing decode beyond demand).
			Expect(targets["dc"]).To(Equal(1))
			// P served with ceil(10000/3000)=4 replicas (loop ran twice to cover residual).
			Expect(targets["pf"]).To(Equal(4))
		})

		It("stops when pick returns empty pair", func() {
			s := []NamedAnalyzerResult{makeNamedPD("sat", 10000, 10000, 0, 0, 10000, 10000, "pf", 5000, "dc", 10000)}
			ps := InitRolePairedState(s)
			targets := map[string]int{"pf": 0, "dc": 0}
			calls := 0
			pick := func(_ []NamedAnalyzerResult, _ []interfaces.VariantCapacity,
				_ map[string]interfaces.VariantReplicaState,
				_ map[string]int, _ map[string]int) (string, string, int, int) {
				calls++
				return "", "", 0, 0
			}
			allocateForModelPairedB2(context.Background(), s, nil, nil, nil, targets, pick, ps, []string{"prefill", "decode"})
			Expect(calls).To(Equal(1))
		})
	})
})
