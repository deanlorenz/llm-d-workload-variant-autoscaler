package throughput

import (
	"context"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// makeMetrics builds a slice of healthy ReplicaMetrics for a single variant,
// each with a distinct KvCacheUsage/KvUtilization to provide k-spread.
func makeMetrics(variant string, count int, baseK float64, kStep float64) []interfaces.ReplicaMetrics {
	metrics := make([]interfaces.ReplicaMetrics, count)
	for i := range metrics {
		k := baseK + float64(i)*kStep
		metrics[i] = interfaces.ReplicaMetrics{
			PodName:               "pod-" + variant + "-" + string(rune('0'+i)),
			VariantName:           variant,
			KvCacheUsage:          k,
			KvUtilization:         k,
			TotalKvCapacityTokens: 65536,
			AvgInputTokens:        1024,
			AvgOutputTokens:       256,
			PrefixCacheHitRate:    0.0,
			AvgITL:                0.030 + k*0.05,
		}
	}
	return metrics
}

// injectWindowObs injects individual-replica observations to build an OLS-ready
// window. Each call to Observe adds one replica; kValues provides the k (and
// implicitly ITL = A·k + B) for each injection.
func injectWindowObs(a *ThroughputAnalyzer, ctx context.Context, modelID, namespace, variant string,
	il, ol, prefixRate float64, kvMax int64, A, B float64, kValues []float64) {
	for _, k := range kValues {
		m := interfaces.ReplicaMetrics{
			VariantName:           variant,
			KvCacheUsage:          k,
			KvUtilization:         k,
			AvgITL:                A*k + B,
			AvgInputTokens:        il,
			AvgOutputTokens:       ol,
			PrefixCacheHitRate:    prefixRate,
			TotalKvCapacityTokens: kvMax,
		}
		a.Observe(ctx, modelID, namespace, []interfaces.ReplicaMetrics{m})
	}
}

var _ = Describe("ThroughputAnalyzer", func() {
	var (
		analyzer  *ThroughputAnalyzer
		ctx       context.Context
		modelID   string
		namespace string
	)

	BeforeEach(func() {
		analyzer = NewThroughputAnalyzer()
		ctx = context.Background()
		modelID = "llama3-8b"
		namespace = "default"
	})

	Describe("Name", func() {
		It("returns the analyzer name", func() {
			Expect(analyzer.Name()).To(Equal(AnalyzerName))
		})
	})

	Describe("VariantState before any observations", func() {
		It("returns false when no data has been observed", func() {
			_, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeFalse())
		})
	})

	Describe("Observe — basic state creation", func() {
		It("creates variant state on first Observe", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.15)
			analyzer.Observe(ctx, modelID, namespace, metrics)

			_, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeTrue())
		})

		It("records shape from first call", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.15)
			analyzer.Observe(ctx, modelID, namespace, metrics)

			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.Shape.AvgInputTokens).To(BeNumerically("~", 1024.0, 0.01))
			Expect(state.Shape.AvgOutputTokens).To(BeNumerically("~", 256.0, 0.01))
		})

		It("adds observations to the window on each Observe call", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.15)
			analyzer.Observe(ctx, modelID, namespace, metrics)

			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.SampleCount).To(Equal(3))
		})
	})

	Describe("Observe — multi-cycle accumulation", func() {
		It("accumulates observations across multiple cycles until Ready", func() {
			// Each call adds 2 replicas with different k values.
			// After enough cycles the window should become Ready.
			for i := range 6 {
				baseK := 0.20 + float64(i)*0.10
				metrics := makeMetrics("v1", 2, baseK, 0.05)
				analyzer.Observe(ctx, modelID, namespace, metrics)
			}

			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.SampleCount).To(BeNumerically(">=", DefaultMinSamples))
			Expect(state.KSpread).To(BeNumerically(">=", DefaultMinKSpread))
			Expect(state.ObservationReady).To(BeTrue())
		})
	})

	Describe("Observe — shape change clears window", func() {
		It("clears the observation window when workload shape changes significantly", func() {
			// Build up some observations.
			for i := range 3 {
				metrics := makeMetrics("v1", 3, 0.20+float64(i)*0.10, 0.05)
				analyzer.Observe(ctx, modelID, namespace, metrics)
			}
			stateBefore, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(stateBefore.SampleCount).To(BeNumerically(">", 0))

			// Now shift IL by 50% — well beyond the 20% tolerance.
			shifted := makeMetrics("v1", 3, 0.20, 0.10)
			for i := range shifted {
				shifted[i].AvgInputTokens = 1024 * 1.5 // +50%
			}
			analyzer.Observe(ctx, modelID, namespace, shifted)

			stateAfter, _ := analyzer.VariantState(modelID, namespace, "v1")
			// The window was cleared on shape change, then one cycle of 3 observations was added.
			Expect(stateAfter.SampleCount).To(Equal(3))
		})
	})

	Describe("Observe — sanity short-circuit", func() {
		It("skips a variant entirely when sanity checks fail", func() {
			bad := makeMetrics("v1", 3, 0.20, 0.10)
			for i := range bad {
				bad[i].AvgITL = 0 // fails SanityIssueITLNonPositive
			}
			reports := analyzer.Observe(ctx, modelID, namespace, bad)

			Expect(reports["v1"].OK()).To(BeFalse())
			Expect(reports["v1"].Has(SanityIssueITLNonPositive)).To(BeTrue())

			// No state should be created when all metrics are bad.
			// (State IS created but window remains empty because we skipped after sanity fail.)
			state, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeTrue()) // state record was created
			Expect(state.SampleCount).To(Equal(0))
			Expect(state.ObservationReady).To(BeFalse())
		})

		It("returns an OK report for a healthy variant", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.10)
			reports := analyzer.Observe(ctx, modelID, namespace, metrics)
			Expect(reports["v1"].OK()).To(BeTrue())
		})
	})

	Describe("Observe — multi-variant isolation", func() {
		It("tracks variants independently", func() {
			metricsV1 := makeMetrics("v1", 3, 0.20, 0.10)
			metricsV2 := makeMetrics("v2", 3, 0.30, 0.10)
			metricsV2[0].AvgInputTokens = 2048 // different shape
			metricsV2[1].AvgInputTokens = 2048
			metricsV2[2].AvgInputTokens = 2048

			combined := append(metricsV1, metricsV2...)
			analyzer.Observe(ctx, modelID, namespace, combined)

			stateV1, okV1 := analyzer.VariantState(modelID, namespace, "v1")
			stateV2, okV2 := analyzer.VariantState(modelID, namespace, "v2")

			Expect(okV1).To(BeTrue())
			Expect(okV2).To(BeTrue())
			Expect(stateV1.Shape.AvgInputTokens).To(BeNumerically("~", 1024.0, 0.01))
			Expect(stateV2.Shape.AvgInputTokens).To(BeNumerically("~", 2048.0, 0.01))
			Expect(stateV1.SampleCount).To(Equal(3))
			Expect(stateV2.SampleCount).To(Equal(3))
		})
	})

	Describe("Analyze — basic behaviour", func() {
		It("returns an AnalyzerResult with the correct identifiers", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.10)
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: metrics,
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result).NotTo(BeNil())
			Expect(result.AnalyzerName).To(Equal(AnalyzerName))
			Expect(result.ModelID).To(Equal(modelID))
			Expect(result.Namespace).To(Equal(namespace))
		})

		It("returns zero signal when demand is zero (no ArrivalRate or VLLMRequestRate set)", func() {
			metrics := makeMetrics("v1", 3, 0.20, 0.10)
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: metrics,
			}
			result, _ := analyzer.Analyze(ctx, input)
			Expect(result.RequiredCapacity).To(Equal(0.0))
			Expect(result.SpareCapacity).To(Equal(0.0))
		})

		It("updates internal state on each Analyze call", func() {
			for i := range 4 {
				input := interfaces.AnalyzerInput{
					ModelID:        modelID,
					Namespace:      namespace,
					ReplicaMetrics: makeMetrics("v1", 3, 0.20+float64(i)*0.10, 0.05),
				}
				_, err := analyzer.Analyze(ctx, input)
				Expect(err).NotTo(HaveOccurred())
			}
			state, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeTrue())
			Expect(state.SampleCount).To(BeNumerically(">", 0))
		})

		It("sets AnalyzedAt to a recent timestamp", func() {
			before := time.Now()
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: makeMetrics("v1", 3, 0.20, 0.10),
			}
			result, _ := analyzer.Analyze(ctx, input)
			Expect(result.AnalyzedAt).To(BeTemporally(">=", before))
		})
	})

	Describe("Analyze — scaling signal (tier-1 OLS fit)", func() {
		// Scenario: IL=5000, OL=200, prefix=0.1, KV_max=1024000, A=0.073, B=0.006
		//   ILeff   = 5000 × 0.9 = 4500
		//   KVreq   = 4500 + 100 = 4600
		//   N_sat   = 0.85 × 1024000 / 4600 ≈ 189.2 in-flight at k_sat
		//   ITL_sat = 0.073×0.85 + 0.006 = 0.068 s/tok
		//   μ_sat   ≈ 189.2 / 0.068 ≈ 2782 tok/s per replica

		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
			muSat  = 2782.0 // approximate, used for order-of-magnitude assertions
		)

		// kValues: 10 points spanning [0.20, 0.65], spread = 0.45 ≥ DefaultMinKSpread
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		// baseReplica is a healthy replica for the signal-test variant.
		baseReplica := func(k, arrivalRate float64) interfaces.ReplicaMetrics {
			return interfaces.ReplicaMetrics{
				VariantName:           "v1",
				KvCacheUsage:          k,
				KvUtilization:         k,
				AvgITL:                A*k + B,
				AvgInputTokens:        il,
				AvgOutputTokens:       ol,
				PrefixCacheHitRate:    prefix,
				TotalKvCapacityTokens: kvMax,
				ArrivalRate:           arrivalRate,
			}
		}

		buildReadyWindow := func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)
			state, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeTrue())
			Expect(state.ObservationReady).To(BeTrue())
		}

		It("returns RequiredCapacity > 0 when λ_dec exceeds μ_dec_total (scale up)", func() {
			buildReadyWindow()

			// ArrivalRate=15 req/s, OL=200 → λ_dec = 3000 tok/s > μ_sat ≈ 2782 tok/s
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica(0.50, 15)},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
			Expect(result.SpareCapacity).To(Equal(0.0))
		})

		It("returns SpareCapacity > 0 when μ_dec_total exceeds λ_dec with EPP deployed (scale down)", func() {
			buildReadyWindow()

			// ArrivalRate=5 req/s, OL=200 → λ_dec = 1000 tok/s < μ_sat ≈ 2782 tok/s
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica(0.50, 5)},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.SpareCapacity).To(BeNumerically(">", 0))
			Expect(result.RequiredCapacity).To(Equal(0.0))
		})

		It("returns zero SpareCapacity when EPP is not deployed (ArrivalRate==0)", func() {
			buildReadyWindow()

			// ArrivalRate=0, VLLMRequestRate=0 → isEPP=false → no scale-down signal
			replica := baseReplica(0.50, 0)
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{replica},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.SpareCapacity).To(Equal(0.0))
		})

		It("populates VariantCapacities and TotalSupply/TotalDemand", func() {
			buildReadyWindow()

			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica(0.50, 5)},
			}
			result, _ := analyzer.Analyze(ctx, input)
			Expect(result.VariantCapacities).To(HaveLen(1))
			Expect(result.TotalSupply).To(BeNumerically("~", muSat, muSat*0.10))
			Expect(result.TotalDemand).To(BeNumerically("~", 1000.0, 1.0))
			Expect(result.Utilization).To(BeNumerically(">", 0))
		})

		It("exposes ITLModel and supply/demand in VariantState after Analyze", func() {
			buildReadyWindow()

			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica(0.50, 5)},
			}
			analyzer.Analyze(ctx, input) //nolint:errcheck

			state, ok := analyzer.VariantState(modelID, namespace, "v1")
			Expect(ok).To(BeTrue())
			Expect(state.ITLModel.IsZero()).To(BeFalse())
			Expect(state.ITLModel.A).To(BeNumerically("~", A, 1e-4))
			Expect(state.TotalSupply).To(BeNumerically("~", muSat, muSat*0.10))
			Expect(state.Demand).To(BeNumerically("~", 1000.0, 1.0))
		})
	})

	Describe("Analyze — tier-2 single-point estimation", func() {
		// Tier-2 triggers when the OLS window is not ready.
		// With A=0.073, B=0.006, k*=0.75:
		//   avgITL = 0.073×0.75 + 0.006 = 0.06075
		//   A_est  = (0.06075 - 0.006) / 0.75 = 0.073
		//   ITL_sat ≈ 0.068  →  μ_sat ≈ 2782 tok/s (same scenario as tier-1)

		tier2Replica := func(k, arrivalRate float64) interfaces.ReplicaMetrics {
			return interfaces.ReplicaMetrics{
				VariantName:           "v1",
				KvCacheUsage:          k,
				KvUtilization:         k,
				AvgITL:                0.073*k + 0.006,
				AvgInputTokens:        5000,
				AvgOutputTokens:       200,
				PrefixCacheHitRate:    0.1,
				TotalKvCapacityTokens: 1024000,
				ArrivalRate:           arrivalRate,
			}
		}

		It("resolves a supply signal without OLS window using tier-2 estimation", func() {
			// Single Observe cycle → only 1 observation → window NOT ready.
			analyzer.Observe(ctx, modelID, namespace, []interfaces.ReplicaMetrics{tier2Replica(0.75, 0)})

			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.ObservationReady).To(BeFalse())

			// Analyze with ArrivalRate=15 → λ_dec=3000 tok/s; tier-2 model → scale up.
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{tier2Replica(0.75, 15)},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
		})
	})

	Describe("Analyze — idle replicas produce no signal", func() {
		It("emits zero signal when all replicas have k*=0 and OLS window is not ready", func() {
			// Idle replicas (k*=0) cannot contribute to tier-1 (filtered by ObservationWindow)
			// or tier-2 (KvUtilization > 0 guard). The knowledge store must NOT be consulted
			// while replicas are running — a stale model could trigger incorrect scaling.
			idleReplica := interfaces.ReplicaMetrics{
				VariantName:           "v1",
				KvCacheUsage:          0.0,
				KvUtilization:         0.0,
				AvgITL:                0.006,
				AvgInputTokens:        5000,
				AvgOutputTokens:       200,
				PrefixCacheHitRate:    0.1,
				TotalKvCapacityTokens: 1024000,
				ArrivalRate:           15, // demand present, but no supply estimate possible
			}
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{idleReplica},
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(Equal(0.0))
			Expect(result.SpareCapacity).To(Equal(0.0))
		})

		It("still emits no signal after prior observations when OLS window is cleared by shape change and replicas go idle", func() {
			// Build an OLS-ready window.
			kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1",
				5000, 200, 0.1, 1024000, 0.073, 0.006, kValues)
			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.ObservationReady).To(BeTrue())

			// Trigger a shape change (+50% IL) to clear the OLS window.
			analyzer.Observe(ctx, modelID, namespace, []interfaces.ReplicaMetrics{{
				VariantName:           "v1",
				KvCacheUsage:          0.50,
				KvUtilization:         0.50,
				AvgITL:                0.073*0.50 + 0.006,
				AvgInputTokens:        7500, // +50% — exceeds 20% tolerance, clears window
				AvgOutputTokens:       200,
				PrefixCacheHitRate:    0.1,
				TotalKvCapacityTokens: 1024000,
			}})
			stateAfter, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(stateAfter.ObservationReady).To(BeFalse())

			// Variant goes idle with cleared window — neither tier-1 nor tier-2 can resolve.
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID:   modelID,
				Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{{
					VariantName:           "v1",
					KvCacheUsage:          0.0,
					KvUtilization:         0.0,
					AvgITL:                0.006,
					AvgInputTokens:        7500,
					AvgOutputTokens:       200,
					PrefixCacheHitRate:    0.1,
					TotalKvCapacityTokens: 1024000,
					ArrivalRate:           15,
				}},
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(Equal(0.0))
			Expect(result.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("Analyze — empty metrics list", func() {
		It("handles an empty metrics slice gracefully", func() {
			reports := analyzer.Observe(ctx, modelID, namespace, []interfaces.ReplicaMetrics{})
			Expect(reports).To(BeEmpty())
		})
	})

	Describe("Analyze — context cancellation", func() {
		It("returns an error immediately when the context is already cancelled", func() {
			cancelled, cancel := context.WithCancel(context.Background())
			cancel()

			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: makeMetrics("v1", 3, 0.20, 0.10),
			}
			result, err := analyzer.Analyze(cancelled, input)
			Expect(err).To(HaveOccurred())
			Expect(result).To(BeNil())
		})
	})

	Describe("Analyze — pending replicas suppress scale-up", func() {
		// Same scenario as the tier-1 scale-up test (λ_dec=3000 > μ_sat≈2782),
		// but with 1 pending replica. Anticipated supply = 2 × perReplicaSupply ≈ 5564 > 3000
		// so RequiredCapacity must be zero.
		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
		)
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		It("suppresses RequiredCapacity when pending replicas cover anticipated demand", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			replica := interfaces.ReplicaMetrics{
				VariantName:           "v1",
				KvCacheUsage:          0.50,
				KvUtilization:         0.50,
				AvgITL:                A*0.50 + B,
				AvgInputTokens:        il,
				AvgOutputTokens:       ol,
				PrefixCacheHitRate:    prefix,
				TotalKvCapacityTokens: kvMax,
				ArrivalRate:           15, // λ_dec = 3000 tok/s > 1 × μ_sat
			}
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{replica},
				VariantStates: []interfaces.VariantReplicaState{
					{VariantName: "v1", CurrentReplicas: 1, PendingReplicas: 1},
				},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			// anticipated = 2 × μ_sat ≈ 5564 > λ_dec = 3000 → no scale-up
			Expect(result.RequiredCapacity).To(Equal(0.0))
		})

		It("still emits RequiredCapacity when pending replicas are insufficient", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			// 3 replicas running, ArrivalRate=15 each → λ_dec = 3×3000 = 9000 tok/s
			// μ_sat ≈ 2782 tok/s per replica; anticipated = 3 × 2782 ≈ 8346 < 9000
			replicas := []interfaces.ReplicaMetrics{
				{VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50, AvgITL: A*0.50 + B,
					AvgInputTokens: il, AvgOutputTokens: ol, PrefixCacheHitRate: prefix,
					TotalKvCapacityTokens: kvMax, ArrivalRate: 15},
				{VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50, AvgITL: A*0.50 + B,
					AvgInputTokens: il, AvgOutputTokens: ol, PrefixCacheHitRate: prefix,
					TotalKvCapacityTokens: kvMax, ArrivalRate: 15},
				{VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50, AvgITL: A*0.50 + B,
					AvgInputTokens: il, AvgOutputTokens: ol, PrefixCacheHitRate: prefix,
					TotalKvCapacityTokens: kvMax, ArrivalRate: 15},
			}
			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: replicas,
				// No pending replicas — anticipated == current supply
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
		})
	})

	Describe("Analyze — role-aware aggregation", func() {
		// Two variants in a P/D disaggregated deployment:
		//   "v-decode" role="decode": standard decode ITL scenario
		//   "v-prefill" role="prefill": prefill pod with OL≈1
		// Both use the same OLS-ready window and arrive at the same perReplicaSupply
		// for simplicity; the role distinction controls which role gets RequiredCapacity.

		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
		)
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		buildVariantWindow := func(variant string) {
			injectWindowObs(analyzer, ctx, modelID, namespace, variant, il, ol, prefix, kvMax, A, B, kValues)
		}

		baseReplica := func(variant string, k, arrivalRate float64) interfaces.ReplicaMetrics {
			return interfaces.ReplicaMetrics{
				VariantName:           variant,
				KvCacheUsage:          k,
				KvUtilization:         k,
				AvgITL:                A*k + B,
				AvgInputTokens:        il,
				AvgOutputTokens:       ol,
				PrefixCacheHitRate:    prefix,
				TotalKvCapacityTokens: kvMax,
				ArrivalRate:           arrivalRate,
			}
		}

		It("populates RoleCapacities for disaggregated variants", func() {
			buildVariantWindow("v-decode")
			buildVariantWindow("v-prefill")

			input := interfaces.AnalyzerInput{
				ModelID:   modelID,
				Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{
					baseReplica("v-decode", 0.50, 5),
					baseReplica("v-prefill", 0.50, 5),
				},
				VariantStates: []interfaces.VariantReplicaState{
					{VariantName: "v-decode", Role: "decode"},
					{VariantName: "v-prefill", Role: "prefill"},
				},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RoleCapacities).NotTo(BeNil())
			Expect(result.RoleCapacities).To(HaveKey("decode"))
			Expect(result.RoleCapacities).To(HaveKey("prefill"))
		})

		It("suppresses RequiredCapacity for the prefill role even under load", func() {
			buildVariantWindow("v-decode")
			buildVariantWindow("v-prefill")

			// ArrivalRate=15 → λ_dec=3000 > μ_sat≈2782: scale-up signal for decode.
			input := interfaces.AnalyzerInput{
				ModelID:   modelID,
				Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{
					baseReplica("v-decode", 0.50, 15),
					baseReplica("v-prefill", 0.50, 15),
				},
				VariantStates: []interfaces.VariantReplicaState{
					{VariantName: "v-decode", Role: "decode"},
					{VariantName: "v-prefill", Role: "prefill"},
				},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())

			decodeRC := result.RoleCapacities["decode"]
			prefillRC := result.RoleCapacities["prefill"]

			Expect(decodeRC.RequiredCapacity).To(BeNumerically(">", 0))
			Expect(prefillRC.RequiredCapacity).To(Equal(0.0))
		})

		It("returns nil RoleCapacities when all variants are non-disaggregated", func() {
			buildVariantWindow("v1")

			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica("v1", 0.50, 5)},
				// No VariantStates → role is "" for all variants
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RoleCapacities).To(BeNil())
		})

		It("sets Role on VariantCapacity and ThroughputVariantState", func() {
			buildVariantWindow("v-decode")

			input := interfaces.AnalyzerInput{
				ModelID:        modelID,
				Namespace:      namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica("v-decode", 0.50, 5)},
				VariantStates: []interfaces.VariantReplicaState{
					{VariantName: "v-decode", Role: "decode"},
				},
			}
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities[0].Role).To(Equal("decode"))

			state, ok := analyzer.VariantState(modelID, namespace, "v-decode")
			Expect(ok).To(BeTrue())
			Expect(state.Role).To(Equal("decode"))
		})
	})

	Describe("Analyze — k*-based local demand (no EPP)", func() {
		// Two replicas at k*=0.95 with no EPP and no vLLM rate.
		// λ_local = Σ (k_r × KV_max_r / KVreq) / ITL(k_r)
		// For each replica: N = 0.95×1024000/4600 ≈ 211.4; ITL(0.95) = 0.073×0.95+0.006 = 0.07535
		// λ_local ≈ 2 × 211.4/0.07535 ≈ 5612 tok/s
		// μ_sat (per replica) ≈ 2782; totalAnticipated = 2 × 2782 = 5564 < 5612 → RC > 0
		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
		)
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		It("emits RequiredCapacity from k* when EPP is absent", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			replicas := []interfaces.ReplicaMetrics{
				{VariantName: "v1", KvCacheUsage: 0.95, KvUtilization: 0.95,
					AvgITL: A*0.95 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
					// ArrivalRate=0, VLLMRequestRate=0 → EPP absent
				},
				{VariantName: "v1", KvCacheUsage: 0.95, KvUtilization: 0.95,
					AvgITL: A*0.95 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
				},
			}
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace, ReplicaMetrics: replicas,
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
			// No EPP → SpareCapacity must be zero regardless.
			Expect(result.SpareCapacity).To(Equal(0.0))
		})

		It("emits no SpareCapacity from k* even when k* is low (scale-down requires EPP)", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			// Low k* → λ_local << μ_sat, but no EPP → no scale-down.
			replica := interfaces.ReplicaMetrics{
				VariantName: "v1", KvCacheUsage: 0.20, KvUtilization: 0.20,
				AvgITL: A*0.20 + B, AvgInputTokens: il, AvgOutputTokens: ol,
				PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
			}
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{replica},
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("Analyze — scheduler queue demand", func() {
		// OLS-ready window, single replica at k*=0.50 with no EPP and no vLLM rate.
		// λ_local = 0.50×1024000/4600 / ITL(0.50) ≈ 111.3/0.0425 ≈ 2618 tok/s
		// μ_sat ≈ 2782 → λ_local < μ_sat: no RC without queue.
		// Add QueueSize=200: λ_queue = 200 / (2.0×ITL(k_sat)) = 200/(2.0×0.06805) ≈ 1469 tok/s
		// totalDemand = 2618+1469 = 4087 > 2782 → RC ≈ 1305 > 0.
		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
		)
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		baseReplica := interfaces.ReplicaMetrics{
			VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50,
			AvgITL: A*0.50 + B, AvgInputTokens: il, AvgOutputTokens: ol,
			PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
			// ArrivalRate=0: no EPP
		}

		It("adds queue demand and emits RequiredCapacity when queue is large", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			withQueue := interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica},
				SchedulerQueue: &interfaces.SchedulerQueueMetrics{QueueSize: 200},
			}
			result, err := analyzer.Analyze(ctx, withQueue)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
		})

		It("emits no RequiredCapacity when SchedulerQueue is nil", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)

			noQueue := interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace,
				ReplicaMetrics: []interfaces.ReplicaMetrics{baseReplica},
				// SchedulerQueue: nil
			}
			result, err := analyzer.Analyze(ctx, noQueue)
			Expect(err).NotTo(HaveOccurred())
			// λ_local ≈ 2618 < μ_sat ≈ 2782 → no RC without queue
			Expect(result.RequiredCapacity).To(Equal(0.0))
		})
	})

	Describe("Analyze — model-level RC/SC aggregation", func() {
		// v1 overloaded (ArrivalRate=15 → λ=3000 > μ_sat≈2782),
		// v2 lightly loaded (ArrivalRate=1 → λ=200 << μ_sat).
		// Per-variant would emit both RC (v1) and SC (v2).
		// Model-level: totalDemand=3200 < totalAnticipated≈5564 → RC=0, SC=5564-3200>0.
		const (
			il     = 5000.0
			ol     = 200.0
			prefix = 0.1
			kvMax  = int64(1024000)
			A      = 0.073
			B      = 0.006
		)
		kValues := []float64{0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65}

		It("emits only SpareCapacity (not RequiredCapacity) when model has overall spare despite one hot variant", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)
			injectWindowObs(analyzer, ctx, modelID, namespace, "v2", il, ol, prefix, kvMax, A, B, kValues)

			replicas := []interfaces.ReplicaMetrics{
				{VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50,
					AvgITL: A*0.50 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
					ArrivalRate: 15}, // λ = 3000 > μ_sat per-variant
				{VariantName: "v2", KvCacheUsage: 0.50, KvUtilization: 0.50,
					AvgITL: A*0.50 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
					ArrivalRate: 1}, // λ = 200 << μ_sat per-variant
			}
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace, ReplicaMetrics: replicas,
			})
			Expect(err).NotTo(HaveOccurred())
			// Model-level: totalDemand=3200 < totalAnticipated≈5564 → no scale-up needed.
			Expect(result.RequiredCapacity).To(Equal(0.0))
			// EPP deployed (ArrivalRate>0) and totalSupply >> totalDemand → scale-down.
			Expect(result.SpareCapacity).To(BeNumerically(">", 0))
		})

		It("emits only RequiredCapacity (not SpareCapacity) when both variants are overloaded", func() {
			injectWindowObs(analyzer, ctx, modelID, namespace, "v1", il, ol, prefix, kvMax, A, B, kValues)
			injectWindowObs(analyzer, ctx, modelID, namespace, "v2", il, ol, prefix, kvMax, A, B, kValues)

			replicas := []interfaces.ReplicaMetrics{
				{VariantName: "v1", KvCacheUsage: 0.50, KvUtilization: 0.50,
					AvgITL: A*0.50 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
					ArrivalRate: 15},
				{VariantName: "v2", KvCacheUsage: 0.50, KvUtilization: 0.50,
					AvgITL: A*0.50 + B, AvgInputTokens: il, AvgOutputTokens: ol,
					PrefixCacheHitRate: prefix, TotalKvCapacityTokens: kvMax,
					ArrivalRate: 15},
			}
			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace, ReplicaMetrics: replicas,
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
			Expect(result.SpareCapacity).To(Equal(0.0))
		})
	})

	Describe("averageShapeMetrics — VLLMRequestRate-weighted averaging", func() {
		It("returns rate-weighted mean when replicas have different VLLMRequestRates", func() {
			// r1: rate=1, IL=1000, OL=200, hr=0.1
			// r2: rate=3, IL=3000, OL=600, hr=0.5
			// Weighted: IL=(1*1000+3*3000)/4=2500, OL=(1*200+3*600)/4=500, hr=(1*0.1+3*0.5)/4=0.4
			metrics := []interfaces.ReplicaMetrics{
				{AvgInputTokens: 1000, AvgOutputTokens: 200, PrefixCacheHitRate: 0.1, VLLMRequestRate: 1},
				{AvgInputTokens: 3000, AvgOutputTokens: 600, PrefixCacheHitRate: 0.5, VLLMRequestRate: 3},
			}
			il, ol, hr := averageShapeMetrics(metrics)
			Expect(il).To(BeNumerically("~", 2500.0, 1e-9))
			Expect(ol).To(BeNumerically("~", 500.0, 1e-9))
			Expect(hr).To(BeNumerically("~", 0.4, 1e-9))
		})

		It("falls back to unweighted mean when all VLLMRequestRates are zero", func() {
			metrics := []interfaces.ReplicaMetrics{
				{AvgInputTokens: 1000, AvgOutputTokens: 200, PrefixCacheHitRate: 0.1, VLLMRequestRate: 0},
				{AvgInputTokens: 3000, AvgOutputTokens: 600, PrefixCacheHitRate: 0.5, VLLMRequestRate: 0},
			}
			il, ol, hr := averageShapeMetrics(metrics)
			Expect(il).To(BeNumerically("~", 2000.0, 1e-9))
			Expect(ol).To(BeNumerically("~", 400.0, 1e-9))
			Expect(hr).To(BeNumerically("~", 0.3, 1e-9))
		})

		It("excludes zero-rate replicas from weighted sum when mixed rates are present", func() {
			// r1 has rate=0: contributes only to unweighted fallback
			// r2 has rate=2: drives the weighted result entirely
			metrics := []interfaces.ReplicaMetrics{
				{AvgInputTokens: 1000, AvgOutputTokens: 200, PrefixCacheHitRate: 0.1, VLLMRequestRate: 0},
				{AvgInputTokens: 3000, AvgOutputTokens: 600, PrefixCacheHitRate: 0.5, VLLMRequestRate: 2},
			}
			il, ol, hr := averageShapeMetrics(metrics)
			Expect(il).To(BeNumerically("~", 3000.0, 1e-9))
			Expect(ol).To(BeNumerically("~", 600.0, 1e-9))
			Expect(hr).To(BeNumerically("~", 0.5, 1e-9))
		})
	})

	Describe("Analyze — tier-2 constrained OLS with multiple replicas", func() {
		// Two replicas at different k* values — constrained OLS and single-point are
		// equivalent when points lie exactly on the true line (they give the same A),
		// but constrained OLS is strictly better under noise. Verify the formula
		// numerically for the noiseless case.
		It("recovers the correct A coefficient from two replicas at different k* values", func() {
			const wantA = 0.073
			const wantB = 0.006
			// Fresh analyzer: no OLS window → tier-2 fires.
			metrics := []interfaces.ReplicaMetrics{
				{
					VariantName: "v1", KvUtilization: 0.20, KvCacheUsage: 0.20,
					AvgITL: wantA*0.20 + wantB, AvgInputTokens: 5000, AvgOutputTokens: 200,
					PrefixCacheHitRate: 0.1, TotalKvCapacityTokens: 1024000, ArrivalRate: 5,
				},
				{
					VariantName: "v1", KvUtilization: 0.80, KvCacheUsage: 0.80,
					AvgITL: wantA*0.80 + wantB, AvgInputTokens: 5000, AvgOutputTokens: 200,
					PrefixCacheHitRate: 0.1, TotalKvCapacityTokens: 1024000, ArrivalRate: 5,
				},
			}
			// Seed the shape tracker with one prior Observe so shape is known.
			analyzer.Observe(ctx, modelID, namespace, metrics)

			result, err := analyzer.Analyze(ctx, interfaces.AnalyzerInput{
				ModelID: modelID, Namespace: namespace, ReplicaMetrics: metrics,
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(1))

			state, _ := analyzer.VariantState(modelID, namespace, "v1")
			Expect(state.ObservationReady).To(BeFalse()) // still tier-2
			// A = Σ((ITL_i−B)·k_i) / Σ(k_i²)
			//   = ((0.073×0.2+0.006−0.006)×0.2 + (0.073×0.8+0.006−0.006)×0.8) / (0.04+0.64)
			//   = (0.073×0.04 + 0.073×0.64) / 0.68
			//   = 0.073×0.68 / 0.68 = 0.073
			Expect(state.ITLModel.A).To(BeNumerically("~", wantA, 1e-6))
			Expect(state.ITLModel.B).To(BeNumerically("~", wantB, 1e-6))
		})
	})

	Describe("estimateQueueDemand — guard clauses", func() {
		It("returns 0 when sq is nil", func() {
			Expect(estimateQueueDemand(nil, 0.05, 2.0)).To(Equal(0.0))
		})
		It("returns 0 when QueueSize is zero", func() {
			sq := &interfaces.SchedulerQueueMetrics{QueueSize: 0}
			Expect(estimateQueueDemand(sq, 0.05, 2.0)).To(Equal(0.0))
		})
		It("returns 0 when itlSat is zero", func() {
			sq := &interfaces.SchedulerQueueMetrics{QueueSize: 10}
			Expect(estimateQueueDemand(sq, 0, 2.0)).To(Equal(0.0))
		})
		It("returns 0 when drainFactor is zero", func() {
			sq := &interfaces.SchedulerQueueMetrics{QueueSize: 10}
			Expect(estimateQueueDemand(sq, 0.05, 0)).To(Equal(0.0))
		})
		It("returns QueueSize / (drainFactor * itlSat) for valid inputs", func() {
			sq := &interfaces.SchedulerQueueMetrics{QueueSize: 100}
			// 100 / (2.0 × 0.05) = 1000
			Expect(estimateQueueDemand(sq, 0.05, 2.0)).To(BeNumerically("~", 1000.0, 1e-9))
		})
	})
})
