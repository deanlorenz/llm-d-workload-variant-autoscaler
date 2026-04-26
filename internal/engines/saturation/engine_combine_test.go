package saturation

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// makeResult builds a minimal AnalyzerResult for combine tests.
// vcs is a list of (replicaCount, perReplicaCapacity) pairs; RC and SC are model-level signals.
func makeResult(RC, SC float64, vcs ...float64) *interfaces.AnalyzerResult {
	var caps []interfaces.VariantCapacity
	for i := 0; i+1 < len(vcs); i += 2 {
		replicas := int(vcs[i])
		prc := vcs[i+1]
		caps = append(caps, interfaces.VariantCapacity{
			VariantName:        "v",
			ReplicaCount:       replicas,
			PerReplicaCapacity: prc,
			TotalCapacity:      float64(replicas) * prc,
		})
	}
	return &interfaces.AnalyzerResult{
		RequiredCapacity:  RC,
		SpareCapacity:     SC,
		VariantCapacities: caps,
	}
}

var _ = Describe("combineAnalyzerResults", func() {

	const priority = 2.0

	// satResult is the metadata base (VariantCapacities carry Cost/AcceleratorName).
	// Two variants: 1 replica × 600 cap + 1 replica × 400 cap = satTotal 1000.
	satResult := func(RC, SC float64) *interfaces.AnalyzerResult {
		r := makeResult(RC, SC, 1, 600, 1, 400)
		r.VariantCapacities[0].VariantName = "cheap"
		r.VariantCapacities[0].Cost = 5.0
		r.VariantCapacities[1].VariantName = "expensive"
		r.VariantCapacities[1].Cost = 15.0
		return r
	}

	Describe("empty results", func() {
		It("returns zero RC/SC with saturation VariantCapacities preserved", func() {
			sat := satResult(200, 0)
			out := combineAnalyzerResults(sat, nil, priority)
			Expect(out.RequiredCapacity).To(Equal(0.0))
			Expect(out.SpareCapacity).To(Equal(0.0))
			Expect(out.Score).To(Equal(0.0))
			Expect(out.VariantCapacities).To(HaveLen(2))
		})
	})

	Describe("single analyzer (saturation only)", func() {
		It("passes through RC unchanged", func() {
			// util_excess = 200/1000 = 0.20 → combined.RC = 0.20 × 1000 = 200
			sat := satResult(200, 0)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 200.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})

		It("passes through SC unchanged", func() {
			// util_slack = 150/1000 = 0.15 → combined.SC = 0.15 × 1000 = 150
			sat := satResult(0, 150)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(Equal(0.0))
			Expect(out.SpareCapacity).To(BeNumerically("~", 150.0, 1e-9))
		})
	})

	Describe("two analyzers — any-up", func() {
		It("saturation has larger signal: sat wins", func() {
			// sat: RC=200, total=1000 → excess=0.20
			// ta:  RC=5,   total=50  → excess=0.10
			// max=0.20, combined.RC = 0.20 × 1000 = 200
			sat := satResult(200, 0)
			ta := makeResult(5, 0, 5, 10) // 5 replicas × 10 cap = total 50
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 200.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})

		It("non-sat analyzer has larger signal: non-sat wins", func() {
			// sat: RC=50,  total=1000 → excess=0.05
			// ta:  RC=30,  total=100  → excess=0.30
			// max=0.30, combined.RC = 0.30 × 1000 = 300
			sat := satResult(50, 0)
			ta := makeResult(30, 0, 10, 10) // 10 replicas × 10 = total 100
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 300.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})

		It("only non-sat triggers scale-up (saturation idle)", func() {
			// sat: RC=0, total=1000 → excess=0
			// ta:  RC=20, total=100  → excess=0.20
			// max=0.20, combined.RC = 0.20 × 1000 = 200
			sat := satResult(0, 0)
			ta := makeResult(20, 0, 10, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 200.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("two analyzers — all-down", func() {
		It("both agree on scale-down: min slack wins", func() {
			// sat: SC=100, total=1000 → slack=0.10
			// ta:  SC=30,  total=100  → slack=0.30
			// min=0.10, combined.SC = 0.10 × 1000 = 100
			sat := satResult(0, 100)
			ta := makeResult(0, 30, 10, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(Equal(0.0))
			Expect(out.SpareCapacity).To(BeNumerically("~", 100.0, 1e-9))
		})

		It("only saturation agrees on scale-down: blocked (all-down fails)", func() {
			// sat: SC=100, total=1000 → slack=0.10
			// ta:  SC=0,   total=100  → slack=0  (blocks scale-down)
			sat := satResult(0, 100)
			ta := makeResult(0, 0, 10, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.SpareCapacity).To(Equal(0.0))
		})

		It("only non-sat agrees on scale-down: blocked (all-down fails)", func() {
			sat := satResult(0, 0)
			ta := makeResult(0, 30, 10, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("saturation disabled (not in results)", func() {
		It("non-sat analyzer drives scale-up; saturation VariantCapacities preserved", func() {
			// Only TA in results; satResult still used as metadata base.
			// satTotal = 1000; ta excess = 20/100 = 0.20 → RC = 200
			sat := satResult(0, 0)
			ta := makeResult(20, 0, 10, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 200.0, 1e-9))
			Expect(out.VariantCapacities[0].Cost).To(Equal(5.0))  // from satResult
			Expect(out.VariantCapacities[1].Cost).To(Equal(15.0)) // from satResult
		})
	})

	Describe("cold start (TotalCapacity = 0)", func() {
		It("forwards saturation cold-start RC directly", func() {
			// satResult has no running replicas (TotalCapacity = 0) but RC > 0
			sat := makeResult(250, 0) // no VariantCapacities → satTotal = 0
			sat.VariantCapacities = []interfaces.VariantCapacity{
				{VariantName: "v", Cost: 5.0, AcceleratorName: "A100",
					ReplicaCount: 0, PerReplicaCapacity: 500, TotalCapacity: 0},
			}
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 250.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})

		It("falls back to 1.0 when saturation is also silent during cold start", func() {
			// Non-sat analyzer detects cold-start (TotalCapacity=0, RC>0)
			// Saturation's satResult.RC = 0
			sat := makeResult(0, 0, 0, 500) // sat: 0 replicas, RC=0
			ta := makeResult(5, 0)          // ta: no VariantCapacities → TotalCapacity=0, RC>0
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 1.0},
				{result: ta, score: 1.0},
			}, priority)
			Expect(out.RequiredCapacity).To(BeNumerically("~", 1.0, 1e-9))
			Expect(out.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("score computation", func() {
		It("score = priority × sum(RC_i × score_i)", func() {
			// sat: RC=200, score=0.5  → contribution = 100
			// ta:  RC=50,  score=2.0  → contribution = 100
			// totalWeighted = 200; Score = priority(2.0) × 200 = 400
			sat := satResult(200, 0)
			ta := makeResult(50, 0, 5, 10)
			out := combineAnalyzerResults(sat, []enabledAnalyzerResult{
				{result: sat, score: 0.5},
				{result: ta, score: 2.0},
			}, priority)
			Expect(out.Score).To(BeNumerically("~", 400.0, 1e-9))
		})
	})

	Describe("unknown analyzer silently skipped via caller", func() {
		It("unknown name in config is never passed to combineAnalyzerResults", func() {
			// runAnalyzersAndScore skips unknown names before calling combine.
			// This test verifies combine itself handles an empty results list gracefully.
			sat := satResult(100, 0)
			out := combineAnalyzerResults(sat, nil, priority)
			Expect(out.RequiredCapacity).To(Equal(0.0))
		})
	})
})
