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

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// spyAnalyzer is a minimal interfaces.Analyzer used in registration tests.
type spyAnalyzer struct {
	name string
}

func (s *spyAnalyzer) Name() string { return s.name }

func (s *spyAnalyzer) Analyze(_ context.Context, in interfaces.AnalyzerInput) (*interfaces.AnalyzerResult, error) {
	return &interfaces.AnalyzerResult{AnalyzerName: s.name, ModelID: in.ModelID}, nil
}

var _ = Describe("Engine analyzer registry", func() {

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

		It("replaces in place when re-registering an existing name", func() {
			first := &spyAnalyzer{name: "throughput"}
			second := &spyAnalyzer{name: "throughput"}
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
					{name: "throughput", analyzer: first},
					{name: "slo", analyzer: &spyAnalyzer{name: "slo"}},
				},
			}

			e.RegisterAnalyzer("throughput", second)

			Expect(e.analyzers).To(HaveLen(3))
			Expect(e.analyzers[1].name).To(Equal("throughput"))
			Expect(e.analyzers[1].analyzer).To(BeIdenticalTo(interfaces.Analyzer(second)))
			Expect(e.analyzers[1].analyzer).NotTo(BeIdenticalTo(interfaces.Analyzer(first)))
			// position of subsequent entries is preserved
			Expect(e.analyzers[2].name).To(Equal("slo"))
		})

		It("panics when called after StartOptimizeLoop has frozen the registry", func() {
			e := &Engine{
				analyzers: []analyzerEntry{
					{name: interfaces.SaturationAnalyzerName, analyzer: &spyAnalyzer{name: interfaces.SaturationAnalyzerName}},
				},
				started: true,
			}

			Expect(func() {
				e.RegisterAnalyzer("throughput", &spyAnalyzer{name: "throughput"})
			}).To(PanicWith("RegisterAnalyzer called after StartOptimizeLoop"))
		})
	})

})
