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
