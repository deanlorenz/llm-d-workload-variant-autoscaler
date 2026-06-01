/*
Copyright 2025.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package saturation

import (
	"context"
	"errors"

	"github.com/go-logr/logr"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	logf "sigs.k8s.io/controller-runtime/pkg/log"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/config"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// spyAnalyzer is a minimal interfaces.Analyzer used in registration tests.
// Configurable to record calls, return an error, or panic.
type spyAnalyzer struct {
	name      string
	callCount int
	err       error
	panicMsg  string
}

func (s *spyAnalyzer) Name() string { return s.name }

func (s *spyAnalyzer) Analyze(_ context.Context, in interfaces.AnalyzerInput) (*interfaces.AnalyzerResult, error) {
	s.callCount++
	if s.panicMsg != "" {
		panic(s.panicMsg)
	}
	if s.err != nil {
		return nil, s.err
	}
	return &interfaces.AnalyzerResult{AnalyzerName: s.name, ModelID: in.ModelID}, nil
}

var _ = Describe("Engine analyzer registry", func() {

	Describe("NewEngine", func() {
		It("pre-registers the V2 saturation analyzer at slot 0", func() {
			sourceRegistry := source.NewSourceRegistry()
			Expect(sourceRegistry.Register("prometheus", source.NewNoOpSource())).To(Succeed())
			testConfig := config.NewTestConfig()
			engine := NewEngine(k8sClient, k8sClient.Scheme(), nil, sourceRegistry, testConfig)

			Expect(engine.analyzers).To(HaveLen(1))
			Expect(engine.analyzers[0].name).To(Equal(interfaces.SaturationAnalyzerName))
			Expect(engine.analyzers[0].analyzer).To(BeIdenticalTo(interfaces.Analyzer(engine.saturationV2Analyzer)))
		})
	})

	Describe("RegisterAnalyzer", func() {
		It("appends new analyzers in registration order", func() {
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
				},
			}

			e.RegisterAnalyzer("throughput", &spyAnalyzer{name: "throughput"})
			e.RegisterAnalyzer("slo", &spyAnalyzer{name: "slo"})

			Expect(e.analyzers).To(HaveLen(3))
			Expect(e.analyzers[0].name).To(Equal(interfaces.SaturationAnalyzerName))
			Expect(e.analyzers[1].name).To(Equal("throughput"))
			Expect(e.analyzers[2].name).To(Equal("slo"))
		})

		It("panics with a clear message when re-registering an existing name", func() {
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
					{name: "throughput", analyzer: &spyAnalyzer{name: "throughput"}},
				},
			}

			Expect(func() {
				e.RegisterAnalyzer("throughput", &spyAnalyzer{name: "throughput"})
			}).To(PanicWith(`RegisterAnalyzer: duplicate analyzer name "throughput"`))

			Expect(func() {
				e.RegisterAnalyzer(interfaces.SaturationAnalyzerName, &spyAnalyzer{name: "x"})
			}).To(PanicWith(ContainSubstring(`duplicate analyzer name`)))
		})
	})

	Describe("runRegisteredAnalyzers", func() {

		var (
			testCtx    context.Context
			testLogger logr.Logger
		)

		BeforeEach(func() {
			testCtx = context.Background()
			testLogger = logf.Log
		})

		It("calls Analyze on every registered non-saturation analyzer exactly once, in registration order", func() {
			sat := &spyAnalyzer{name: interfaces.SaturationAnalyzerName}
			ta := &spyAnalyzer{name: "throughput"}
			slo := &spyAnalyzer{name: "slo"}
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: sat},
					{name: "throughput", analyzer: ta},
					{name: "slo", analyzer: slo},
				},
			}

			e.runRegisteredAnalyzers(testCtx, testLogger, "model-1", interfaces.AnalyzerInput{ModelID: "model-1"})

			// Saturation entry is skipped — engine runs saturation via
			// runV2AnalysisOnly with full args. When a future PR unifies
			// saturation into the loop, this expectation flips and the
			// surrounding test description should be revised.
			Expect(sat.callCount).To(Equal(0))
			Expect(ta.callCount).To(Equal(1))
			Expect(slo.callCount).To(Equal(1))
		})

		It("logs and continues when a registered analyzer returns an error", func() {
			ta := &spyAnalyzer{name: "throughput", err: errors.New("boom")}
			slo := &spyAnalyzer{name: "slo"}
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
					{name: "throughput", analyzer: ta},
					{name: "slo", analyzer: slo},
				},
			}

			Expect(func() {
				e.runRegisteredAnalyzers(testCtx, testLogger, "model-1", interfaces.AnalyzerInput{ModelID: "model-1"})
			}).NotTo(Panic())

			// Both analyzers are still called even though throughput erred.
			Expect(ta.callCount).To(Equal(1))
			Expect(slo.callCount).To(Equal(1))
		})

		It("recovers from a panicking analyzer and continues with the rest", func() {
			ta := &spyAnalyzer{name: "throughput", panicMsg: "boom"}
			slo := &spyAnalyzer{name: "slo"}
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
					{name: "throughput", analyzer: ta},
					{name: "slo", analyzer: slo},
				},
			}

			Expect(func() {
				e.runRegisteredAnalyzers(testCtx, testLogger, "model-1", interfaces.AnalyzerInput{ModelID: "model-1"})
			}).NotTo(Panic())

			// throughput panicked but was recovered; slo still ran.
			Expect(ta.callCount).To(Equal(1))
			Expect(slo.callCount).To(Equal(1))
		})
	})
})
