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

package throughput

import (
	"context"
	"math"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

var _ = Describe("ThroughputAnalyzer", func() {
	var (
		analyzer *ThroughputAnalyzer
		ctx      context.Context
	)

	BeforeEach(func() {
		analyzer = NewThroughputAnalyzer()
		ctx = context.Background()
	})

	Describe("Name", func() {
		It("should return 'throughput'", func() {
			Expect(analyzer.Name()).To(Equal("throughput"))
		})
	})

	Describe("Config type check", func() {
		It("should return an error when config is the wrong type", func() {
			input := interfaces.AnalyzerInput{
				ModelID:   "m",
				Namespace: "ns",
				Config:    &wrongConfig{},
			}
			_, err := analyzer.Analyze(ctx, input)
			Expect(err).To(HaveOccurred())
			Expect(err.Error()).To(ContainSubstring("expected *throughput.Config"))
		})
	})

	Describe("Analyze with no replicas", func() {
		It("should return an empty result with no variant capacities", func() {
			input := makeInput(nil, nil)
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(BeEmpty())
			Expect(result.TotalSupply).To(Equal(0.0))
			Expect(result.TotalDemand).To(Equal(0.0))
		})
	})

	Describe("Analyze with single variant — no bins", func() {
		It("should compute supply and demand using the observed average as the single bin", func() {
			//  Pod: arrivalRate=2, TTFT=0.1s, ITL=0.01s, OL=50, IL=100
			//  KV capacity = 16000 tokens, H% = 0.0 → 1.0 (conservative)
			//
			//  E2E = 0.1 + 50*0.01 = 0.6 s
			//  N(v) = 2 * 0.6 = 1.2  (Little's Law)
			//  KV(w) = 1.0 * (100 + 0.5*50) = 125
			//  N_max = 16000 / 125 = 128
			//  D_v = 1.2 / 0.6 = 2.0
			//  S_v = 128 / 0.6 = 213.3
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 0)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{
					{VariantName: "variant-a", CurrentReplicas: 1},
				})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(1))
			vc := result.VariantCapacities[0]
			Expect(vc.VariantName).To(Equal("variant-a"))

			// D_v ≈ 2.0
			Expect(vc.TotalDemand).To(BeNumerically("~", 2.0, 0.01))
			// S_v per replica ≈ 213.3, total = 1 × S_v
			Expect(vc.PerReplicaCapacity).To(BeNumerically("~", 213.3, 1.0))
		})

		It("should prefer RunningRequests over Little's Law for N(v)", func() {
			//  RunningRequests = 5 (direct observation wins over Little's Law which gives ~1.2)
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 5)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{
					{VariantName: "variant-a", CurrentReplicas: 1},
				})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(1))
			vc := result.VariantCapacities[0]

			// D_v = 5 / 0.6 ≈ 8.33  (NOT 2.0 from Little's Law)
			Expect(vc.TotalDemand).To(BeNumerically("~", 8.33, 0.1))
		})
	})

	Describe("Analyze with multiple replicas in the same variant", func() {
		It("should aggregate arrival rates and use per-pod KV capacity average", func() {
			//  Two identical pods, arrival rate 1.0 each → total 2.0
			//  N_total via RunningRequests: 3 + 3 = 6
			//  E2E = 0.1 + 50*0.01 = 0.6 s
			//  KV_cap per pod = 16000; KV(w) = 125; N_max = 128
			//  D_v = 6 / 0.6 = 10
			//  S_v per pod = 128 / 0.6 = 213.3; total = 2 × 213.3 = 426.7
			rm1 := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 3)
			rm2 := makeReplica("pod-2", "variant-a", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 3)
			input := makeInput(
				[]interfaces.ReplicaMetrics{rm1, rm2},
				[]interfaces.VariantReplicaState{
					{VariantName: "variant-a", CurrentReplicas: 2},
				},
			)

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(1))
			vc := result.VariantCapacities[0]

			Expect(vc.TotalDemand).To(BeNumerically("~", 10.0, 0.1))
			Expect(vc.TotalCapacity).To(BeNumerically("~", 426.7, 5.0))
		})
	})

	Describe("Analyze with multiple variants", func() {
		It("should produce a VariantCapacity entry for each variant", func() {
			rm1 := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 2)
			rm2 := makeReplica("pod-2", "variant-b", "A100", 8.0,
				0.0, 1.5, 0.12, 0.012, 120.0, 60.0, 0.0, 20000, 3)
			input := makeInput(
				[]interfaces.ReplicaMetrics{rm1, rm2},
				[]interfaces.VariantReplicaState{
					{VariantName: "variant-a", CurrentReplicas: 1},
					{VariantName: "variant-b", CurrentReplicas: 1},
				},
			)

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(2))
			Expect(result.TotalSupply).To(BeNumerically(">", 0))
			Expect(result.TotalDemand).To(BeNumerically(">", 0))
		})
	})

	Describe("Prefix cache hit rate (H%)", func() {
		It("should use H%=1 when hit rate is zero (conservative KV cost)", func() {
			// H% = 0 → use 1.0; KV(w) = 1.0 * (100 + 25) = 125
			rm := makeReplica("pod-1", "v", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 0)
			inputNoCache := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "v", CurrentReplicas: 1}})

			// H% = 0.5 → KV(w) = 0.5 * 125 = 62.5 → N_max = 16000/62.5 = 256
			rmCache := makeReplica("pod-1", "v", "H100", 10.0,
				0.5, 1.0, 0.1, 0.01, 100.0, 50.0, 0.5, 16000, 0)
			inputWithCache := makeInput([]interfaces.ReplicaMetrics{rmCache},
				[]interfaces.VariantReplicaState{{VariantName: "v", CurrentReplicas: 1}})

			resNoCache, err := analyzer.Analyze(ctx, inputNoCache)
			Expect(err).NotTo(HaveOccurred())

			resWithCache, err := analyzer.Analyze(ctx, inputWithCache)
			Expect(err).NotTo(HaveOccurred())

			// Higher hit rate → higher N_max → higher S_v
			Expect(resWithCache.VariantCapacities[0].PerReplicaCapacity).To(
				BeNumerically(">", resNoCache.VariantCapacities[0].PerReplicaCapacity))
		})
	})

	Describe("Workload bins", func() {
		It("should assign all weight to the nearest bin", func() {
			bins := []WorkloadBin{
				{Name: "short", IL: 128, OL: 64},
				{Name: "long", IL: 2048, OL: 512},
			}
			// avgIL=100, avgOL=50 → closer to "short" bin
			weights := computeMixtureWeights(bins, 100, 50)
			Expect(weights["short"]).To(Equal(1.0))
			Expect(weights["long"]).To(Equal(0.0))
		})

		It("should assign weight to long bin when observations match", func() {
			bins := []WorkloadBin{
				{Name: "short", IL: 128, OL: 64},
				{Name: "long", IL: 2048, OL: 512},
			}
			weights := computeMixtureWeights(bins, 1800, 450)
			Expect(weights["long"]).To(Equal(1.0))
			Expect(weights["short"]).To(Equal(0.0))
		})

		It("should return empty map for empty bins", func() {
			weights := computeMixtureWeights(nil, 100, 50)
			Expect(weights).To(BeEmpty())
		})
	})

	Describe("E2E latency per bin", func() {
		It("should scale TTFT linearly with IL bin size", func() {
			agg := variantAgg{
				avgTTFT: 0.1,
				avgITL:  0.01,
				avgIL:   100.0,
				avgOL:   50.0,
				avgE2E:  0.6,
			}
			bin := WorkloadBin{Name: "large", IL: 200.0, OL: 100.0}
			// TTFT(w) = 0.1 * (200/100) = 0.2; E2E = 0.2 + 100*0.01 = 1.2
			e2e := e2eForBin(bin, agg)
			Expect(e2e).To(BeNumerically("~", 1.2, 0.001))
		})

		It("should fall back to avgE2E when TTFT or ITL is zero", func() {
			agg := variantAgg{
				avgTTFT: 0.0,
				avgITL:  0.0,
				avgE2E:  0.6,
			}
			bin := WorkloadBin{Name: "any", IL: 200.0, OL: 100.0}
			e2e := e2eForBin(bin, agg)
			Expect(e2e).To(Equal(0.6))
		})
	})

	Describe("Scheduler queue demand", func() {
		It("should add queue demand to total demand via EPP queue", func() {
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 2)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})
			input.SchedulerQueue = &interfaces.SchedulerQueueMetrics{
				QueueSize: 100,
			}

			resultWithQueue, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())

			input.SchedulerQueue = nil
			resultNoQueue, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())

			Expect(resultWithQueue.TotalDemand).To(BeNumerically(">", resultNoQueue.TotalDemand))
		})

		It("should not add demand when QueueSize is zero", func() {
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 2)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})
			input.SchedulerQueue = &interfaces.SchedulerQueueMetrics{QueueSize: 0}

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())

			input.SchedulerQueue = nil
			resultNoQueue, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())

			Expect(result.TotalDemand).To(Equal(resultNoQueue.TotalDemand))
		})
	})

	Describe("Scaling signals", func() {
		It("should signal scale-up when demand exceeds ScaleUpThreshold", func() {
			// High RunningRequests → D_v >> S_v → scale-up
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 1000)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">", 0))
		})

		It("should signal scale-down when demand is well below ScaleDownBoundary", func() {
			// Very low RunningRequests → D_v << S_v → spare capacity
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 0.001, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 0)
			// No running requests, very low arrival rate → effectively zero demand
			// but we need Little's Law to give something non-zero for the variant
			// to pass the insufficient data check. Use running=1 and low value.
			rm.RunningRequests = 1
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			// Very low load with 1 replica → spare capacity should be positive
			Expect(result.SpareCapacity).To(BeNumerically(">", 0))
		})

		It("should have non-negative RequiredCapacity and SpareCapacity", func() {
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 5)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.RequiredCapacity).To(BeNumerically(">=", 0))
			Expect(result.SpareCapacity).To(BeNumerically(">=", 0))
		})
	})

	Describe("Variant with no KV capacity", func() {
		It("should skip variants with no TotalKvCapacityTokens", func() {
			// No cache config → TotalKvCapacityTokens = 0 → variant skipped
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 0, 0)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(BeEmpty())
		})
	})

	Describe("aggregateVariant", func() {
		It("should return false when all replicas lack KV capacity data", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", ArrivalRate: 1.0, AvgTTFT: 0.1, AvgITL: 0.01, AvgOutputTokens: 50, AvgInputTokens: 100},
			}
			_, ok := aggregateVariant(replicas)
			Expect(ok).To(BeFalse())
		})

		It("should return false when no arrival rate and no running requests", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", TotalKvCapacityTokens: 16000},
			}
			_, ok := aggregateVariant(replicas)
			Expect(ok).To(BeFalse())
		})

		It("should compute weighted averages correctly", func() {
			replicas := []interfaces.ReplicaMetrics{
				{
					PodName: "p1", TotalKvCapacityTokens: 16000,
					ArrivalRate: 2.0, AvgTTFT: 0.1, AvgITL: 0.01,
					AvgInputTokens: 100, AvgOutputTokens: 50, PrefixCacheHitRate: 0.4,
				},
				{
					PodName: "p2", TotalKvCapacityTokens: 20000,
					ArrivalRate: 2.0, AvgTTFT: 0.2, AvgITL: 0.02,
					AvgInputTokens: 200, AvgOutputTokens: 100, PrefixCacheHitRate: 0.6,
				},
			}
			agg, ok := aggregateVariant(replicas)
			Expect(ok).To(BeTrue())

			// Weighted averages: equal weights (both arrivalRate=2)
			Expect(agg.avgTTFT).To(BeNumerically("~", 0.15, 0.001))
			Expect(agg.avgITL).To(BeNumerically("~", 0.015, 0.001))
			Expect(agg.avgIL).To(BeNumerically("~", 150.0, 0.1))
			Expect(agg.avgOL).To(BeNumerically("~", 75.0, 0.1))
			Expect(agg.hitRate).To(BeNumerically("~", 0.5, 0.001))
			Expect(agg.kvCapPerPod).To(BeNumerically("~", 18000.0, 1.0))
		})

		It("should default H% to 1.0 when hit rate is zero", func() {
			replicas := []interfaces.ReplicaMetrics{
				{
					PodName: "p1", TotalKvCapacityTokens: 16000,
					ArrivalRate: 1.0, AvgTTFT: 0.1, AvgITL: 0.01,
					AvgInputTokens: 100, AvgOutputTokens: 50, PrefixCacheHitRate: 0.0,
				},
			}
			agg, ok := aggregateVariant(replicas)
			Expect(ok).To(BeTrue())
			Expect(agg.hitRate).To(Equal(1.0))
		})

		It("should use RunningRequests for N(v) when available", func() {
			replicas := []interfaces.ReplicaMetrics{
				{
					PodName: "p1", TotalKvCapacityTokens: 16000,
					ArrivalRate: 1.0, AvgTTFT: 0.1, AvgITL: 0.01,
					AvgInputTokens: 100, AvgOutputTokens: 50,
					RunningRequests: 7,
				},
			}
			agg, ok := aggregateVariant(replicas)
			Expect(ok).To(BeTrue())
			Expect(agg.nTotal).To(Equal(7.0))
		})
	})

	Describe("Config defaults", func() {
		It("should apply defaults to zero-valued fields", func() {
			cfg := Config{}
			c := cfg.WithDefaults()
			Expect(c.EMAAlpha).To(Equal(DefaultEMAAlpha))
			Expect(c.HysteresisThreshold).To(Equal(DefaultHysteresisThreshold))
			Expect(c.MaxDelta).To(Equal(DefaultMaxDelta))
			Expect(c.ScaleUpThreshold).To(Equal(0.85))
			Expect(c.ScaleDownBoundary).To(Equal(0.70))
		})

		It("should not overwrite explicitly set fields", func() {
			cfg := Config{
				EMAAlpha:            0.5,
				HysteresisThreshold: 0.2,
				MaxDelta:            10,
				ScaleUpThreshold:    0.9,
				ScaleDownBoundary:   0.6,
			}
			c := cfg.WithDefaults()
			Expect(c.EMAAlpha).To(Equal(0.5))
			Expect(c.HysteresisThreshold).To(Equal(0.2))
			Expect(c.MaxDelta).To(Equal(10))
			Expect(c.ScaleUpThreshold).To(Equal(0.9))
			Expect(c.ScaleDownBoundary).To(Equal(0.6))
		})

		It("should clamp negative HysteresisThreshold to default", func() {
			cfg := Config{HysteresisThreshold: -0.1}
			c := cfg.WithDefaults()
			Expect(c.HysteresisThreshold).To(Equal(DefaultHysteresisThreshold))
		})

		It("should reset out-of-range EMAAlpha to default", func() {
			cfg := Config{EMAAlpha: 1.5}
			c := cfg.WithDefaults()
			Expect(c.EMAAlpha).To(Equal(DefaultEMAAlpha))
		})
	})

	Describe("averageE2E", func() {
		It("should return 0 for empty slice", func() {
			Expect(averageE2E(nil)).To(Equal(0.0))
		})

		It("should return 0 when no replicas have arrival rate", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", AvgTTFT: 0.1, AvgITL: 0.01, AvgOutputTokens: 50},
			}
			Expect(averageE2E(replicas)).To(Equal(0.0))
		})

		It("should compute weighted average correctly", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", ArrivalRate: 1.0, AvgTTFT: 0.1, AvgITL: 0.01, AvgOutputTokens: 50},  // E2E=0.6
				{PodName: "p2", ArrivalRate: 3.0, AvgTTFT: 0.2, AvgITL: 0.02, AvgOutputTokens: 100}, // E2E=2.2
			}
			// weighted avg = (1*0.6 + 3*2.2) / 4 = 7.2 / 4 = 1.8
			Expect(averageE2E(replicas)).To(BeNumerically("~", 1.8, 0.001))
		})
	})

	Describe("groupByVariant", func() {
		It("should partition replicas by variant name", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", VariantName: "a"},
				{PodName: "p2", VariantName: "b"},
				{PodName: "p3", VariantName: "a"},
			}
			m := groupByVariant(replicas)
			Expect(m).To(HaveLen(2))
			Expect(m["a"]).To(HaveLen(2))
			Expect(m["b"]).To(HaveLen(1))
		})
	})

	Describe("utilization field", func() {
		It("should be D_v / TotalCapacity when supply > 0", func() {
			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 2.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 2)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.VariantCapacities).To(HaveLen(1))
			vc := result.VariantCapacities[0]

			if vc.TotalCapacity > 0 {
				expectedUtil := vc.TotalDemand / vc.TotalCapacity
				Expect(vc.Utilization).To(BeNumerically("~", expectedUtil, 1e-9))
			}

			// Model-level utilization is consistent
			if result.TotalSupply > 0 {
				expectedModelUtil := result.TotalDemand / result.TotalSupply
				Expect(result.Utilization).To(BeNumerically("~", expectedModelUtil, 1e-9))
			}
		})
	})

	Describe("context cancellation", func() {
		It("should return ctx.Err when context is cancelled", func() {
			cancelled, cancel := context.WithCancel(ctx)
			cancel() // cancel immediately

			rm := makeReplica("pod-1", "variant-a", "H100", 10.0,
				0.0, 1.0, 0.1, 0.01, 100.0, 50.0, 0.0, 16000, 2)
			input := makeInput([]interfaces.ReplicaMetrics{rm},
				[]interfaces.VariantReplicaState{{VariantName: "variant-a", CurrentReplicas: 1}})

			_, err := analyzer.Analyze(cancelled, input)
			Expect(err).To(MatchError(context.Canceled))
		})
	})

	Describe("result metadata", func() {
		It("should populate AnalyzerName, ModelID, Namespace, and AnalyzedAt", func() {
			input := makeInput(nil, nil)
			result, err := analyzer.Analyze(ctx, input)
			Expect(err).NotTo(HaveOccurred())
			Expect(result.AnalyzerName).To(Equal("throughput"))
			Expect(result.ModelID).To(Equal("test-model"))
			Expect(result.Namespace).To(Equal("test-ns"))
			Expect(result.AnalyzedAt.IsZero()).To(BeFalse())
		})
	})

	Describe("NaN/Inf guard in averageE2E", func() {
		It("should not produce NaN from zero ITL pod", func() {
			replicas := []interfaces.ReplicaMetrics{
				{PodName: "p1", ArrivalRate: 1.0, AvgTTFT: 0.1, AvgITL: 0.0, AvgOutputTokens: 50},
			}
			avg := averageE2E(replicas)
			// E2E = 0.1 + 0 = 0.1, but only if AvgITL=0 contributes a non-positive E2E
			// In averageE2E, e2e = 0.1 + 50*0 = 0.1, which is > 0.
			Expect(math.IsNaN(avg)).To(BeFalse())
			Expect(math.IsInf(avg, 0)).To(BeFalse())
		})
	})
})

// wrongConfig is a stub that satisfies interfaces.AnalyzerConfig but is
// not *throughput.Config, used to test the type-check error path.
type wrongConfig struct{}

func (w *wrongConfig) GetAnalyzerName() string { return "wrong" }

// makeInput builds a standard AnalyzerInput for the Throughput Analyzer.
func makeInput(
	replicas []interfaces.ReplicaMetrics,
	states []interfaces.VariantReplicaState,
) interfaces.AnalyzerInput {
	return interfaces.AnalyzerInput{
		ModelID:        "test-model",
		Namespace:      "test-ns",
		ReplicaMetrics: replicas,
		VariantStates:  states,
		Config:         &Config{},
	}
}

// makeReplica creates a ReplicaMetrics with latency and KV fields set.
// Parameters:
//   - podName, variantName, accelerator: identifying strings
//   - cost: per-replica cost
//   - kvUsage: KV cache usage fraction (0..1)
//   - arrivalRate: requests per second dispatched to this replica
//   - avgTTFT: average time-to-first-token in seconds
//   - avgITL: average inter-token latency in seconds
//   - avgIL: average input tokens per request
//   - avgOL: average output tokens per request
//   - prefixHitRate: prefix cache hit rate (0..1)
//   - kvCapacity: total KV capacity in tokens (TotalKvCapacityTokens)
//   - runningRequests: in-flight request count (0 = use Little's Law)
func makeReplica(
	podName, variantName, accelerator string,
	cost float64,
	kvUsage float64,
	arrivalRate float64,
	avgTTFT float64,
	avgITL float64,
	avgIL float64,
	avgOL float64,
	prefixHitRate float64,
	kvCapacity int64,
	runningRequests int64,
) interfaces.ReplicaMetrics {
	return interfaces.ReplicaMetrics{
		PodName:               podName,
		VariantName:           variantName,
		AcceleratorName:       accelerator,
		Cost:                  cost,
		ModelID:               "test-model",
		Namespace:             "test-ns",
		KvCacheUsage:          kvUsage,
		ArrivalRate:           arrivalRate,
		AvgTTFT:               avgTTFT,
		AvgITL:                avgITL,
		AvgInputTokens:        avgIL,
		AvgOutputTokens:       avgOL,
		PrefixCacheHitRate:    prefixHitRate,
		TotalKvCapacityTokens: kvCapacity,
		RunningRequests:       runningRequests,
	}
}
