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

// Package throughput provides the Throughput Analyzer, which computes a
// per-variant supply/demand ratio using a KV-cache capacity model and latency
// observations.
//
// # Algorithm overview
//
// For each variant v, the analyzer computes:
//
//	D_v = Σ_w  N(w,v) / E2E(w,v)   (latency-weighted demand)
//	S_v = Σ_w  N_max(w,v) / E2E(w,v) (latency-weighted supply)
//
// where:
//   - N(v)     = total in-flight requests (from vllm:num_requests_running, or
//     Little's Law fallback: ArrivalRate × E2E)
//   - N(w,v)   = N(v) × π_w  (mixture weight for workload bin w)
//   - N_max(w,v) = KV_max(v) / KV(w,v)
//   - KV(w,v)  = H%(v) × (IL(w) + 0.5 × OL(w))
//   - E2E(w,v) ≈ TTFT(v) × (IL(w)/avgIL(v)) + OL(w) × ITL(v)
//
// The recommended replica delta is:
//
//	Δ_v = ceil(D_v / S_v) - I_v
//
// Hysteresis and MaxDelta guards are applied before returning.
package throughput

import (
	"context"
	"fmt"
	"math"
	"time"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

// ThroughputAnalyzer implements interfaces.Analyzer using a throughput-based
// KV-cache capacity model.
type ThroughputAnalyzer struct{}

// NewThroughputAnalyzer creates a new ThroughputAnalyzer.
func NewThroughputAnalyzer() *ThroughputAnalyzer {
	return &ThroughputAnalyzer{}
}

// Name returns the analyzer identifier.
func (a *ThroughputAnalyzer) Name() string {
	return AnalyzerName
}

// Analyze computes capacity signals for a model across all its variants.
func (a *ThroughputAnalyzer) Analyze(ctx context.Context, input interfaces.AnalyzerInput) (*interfaces.AnalyzerResult, error) {
	cfg, ok := input.Config.(*Config)
	if !ok {
		return nil, fmt.Errorf("throughput analyzer: expected *throughput.Config, got %T", input.Config)
	}
	effective := cfg.WithDefaults()

	// Build current-replica lookup from variant states
	currentReplicas := make(map[string]int, len(input.VariantStates))
	pendingReplicas := make(map[string]int, len(input.VariantStates))
	for _, vs := range input.VariantStates {
		currentReplicas[vs.VariantName] = vs.CurrentReplicas
		pendingReplicas[vs.VariantName] = vs.PendingReplicas
	}

	// Group replica metrics by variant
	byVariant := groupByVariant(input.ReplicaMetrics)

	variantCapacities := make([]interfaces.VariantCapacity, 0, len(byVariant))
	var totalSupply, totalDemand float64

	for variantName, replicas := range byVariant {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		vc, err := a.analyzeVariant(variantName, replicas, effective)
		if err != nil {
			// Non-fatal: skip variants with insufficient data and continue
			continue
		}

		vc.ReplicaCount = currentReplicas[variantName]
		vc.PendingReplicas = pendingReplicas[variantName]
		variantCapacities = append(variantCapacities, *vc)
		totalSupply += vc.TotalCapacity
		totalDemand += vc.TotalDemand
	}

	// Account for EPP scheduler queue as additional demand (same pattern as
	// saturation_v2's estimateSchedulerQueueDemand).
	if input.SchedulerQueue != nil && input.SchedulerQueue.QueueSize > 0 && len(input.ReplicaMetrics) > 0 {
		avgE2E := averageE2E(input.ReplicaMetrics)
		if avgE2E > 0 {
			// QueueSize requests each taking avgE2E seconds represent a demand
			// contribution of QueueSize / avgE2E (as latency-weighted load).
			totalDemand += float64(input.SchedulerQueue.QueueSize) / avgE2E
		}
	}

	var utilization float64
	if totalSupply > 0 {
		utilization = totalDemand / totalSupply
	}

	// Model-level scaling signals
	var requiredCapacity, spareCapacity float64
	if effective.ScaleUpThreshold > 0 {
		requiredCapacity = totalDemand/effective.ScaleUpThreshold - totalSupply
		if requiredCapacity < 0 {
			requiredCapacity = 0
		}
	}
	if effective.ScaleDownBoundary > 0 {
		spareCapacity = totalSupply - totalDemand/effective.ScaleDownBoundary
		if spareCapacity < 0 {
			spareCapacity = 0
		}
	}

	result := &interfaces.AnalyzerResult{
		AnalyzerName:      a.Name(),
		ModelID:           input.ModelID,
		Namespace:         input.Namespace,
		AnalyzedAt:        time.Now(),
		VariantCapacities: variantCapacities,
		TotalSupply:       totalSupply,
		TotalDemand:       totalDemand,
		Utilization:       utilization,
		RequiredCapacity:  requiredCapacity,
		SpareCapacity:     spareCapacity,
	}

	return result, nil
}

// analyzeVariant computes supply/demand capacity signals for a single variant.
// Returns an error when the variant has insufficient data to produce a result.
func (a *ThroughputAnalyzer) analyzeVariant(
	variantName string,
	replicas []interfaces.ReplicaMetrics,
	cfg Config,
) (*interfaces.VariantCapacity, error) {
	// Aggregate variant-level statistics (weighted by arrival rate where possible)
	agg, ok := aggregateVariant(replicas)
	if !ok {
		return nil, fmt.Errorf("variant %q: insufficient data (no arrival rate or KV capacity)", variantName)
	}

	// Determine workload bins to use
	bins := cfg.WorkloadBins
	if len(bins) == 0 {
		// No bins configured: use a single bin representing the observed average
		bins = []WorkloadBin{{
			Name: "observed",
			IL:   agg.avgIL,
			OL:   agg.avgOL,
		}}
	}

	// Compute mixture weights by assigning all weight to the nearest bin
	piW := computeMixtureWeights(bins, agg.avgIL, agg.avgOL)

	// Compute D_v and S_v across bins
	var dv, sv float64
	for _, bin := range bins {
		pi := piW[bin.Name]
		if pi == 0 {
			continue
		}

		nWV := agg.nTotal * pi

		kvW := agg.hitRate * (bin.IL + 0.5*bin.OL)
		if kvW <= 0 {
			kvW = bin.IL + 0.5*bin.OL // no cache benefit
		}
		if kvW <= 0 {
			continue // degenerate bin
		}

		nMaxWV := agg.kvCapPerPod / kvW

		e2eWV := e2eForBin(bin, agg)
		if e2eWV < DefaultMinE2E {
			e2eWV = agg.avgE2E
		}
		if e2eWV < DefaultMinE2E {
			continue // no latency signal
		}

		dv += nWV / e2eWV
		sv += nMaxWV / e2eWV
	}

	if sv < DefaultMinSupply {
		return nil, fmt.Errorf("variant %q: supply signal too small (%.2e)", variantName, sv)
	}

	// S_v is per pod; scale to total by replica count
	replicaCount := len(replicas)
	totalSupply := sv * float64(replicaCount)
	// D_v is model-wide demand (all replicas contribute to N(v))
	totalDemand := dv

	var utilization float64
	if totalSupply > 0 {
		utilization = totalDemand / totalSupply
	}

	return &interfaces.VariantCapacity{
		VariantName:        variantName,
		AcceleratorName:    agg.acceleratorName,
		Cost:               agg.cost,
		PerReplicaCapacity: sv,
		TotalCapacity:      totalSupply,
		TotalDemand:        totalDemand,
		Utilization:        utilization,
	}, nil
}

// variantAgg holds weighted-average statistics for a single variant.
type variantAgg struct {
	// Arrival-rate-weighted averages
	avgE2E  float64 // seconds
	avgIL   float64 // tokens
	avgOL   float64 // tokens
	avgTTFT float64 // seconds
	avgITL  float64 // seconds
	hitRate float64 // 0..1, 1 = no cache benefit (conservative default)

	// Per-pod KV capacity (average across pods)
	kvCapPerPod float64 // tokens

	// Total in-flight requests for the variant
	nTotal float64

	// Metadata from the first non-empty replica
	acceleratorName string
	cost            float64
}

// aggregateVariant computes arrival-rate-weighted aggregates from replica metrics.
// Returns (agg, true) when the variant has sufficient signal, (_, false) otherwise.
func aggregateVariant(replicas []interfaces.ReplicaMetrics) (variantAgg, bool) {
	var (
		totalArrivalRate float64
		sumE2E           float64
		sumIL            float64
		sumOL            float64
		sumTTFT          float64
		sumITL           float64
		sumHitRate       float64
		sumKvCap         float64
		podCount         int
		totalRunning     int64
		accel            string
		cost             float64
	)

	for _, rm := range replicas {
		if accel == "" && rm.AcceleratorName != "" {
			accel = rm.AcceleratorName
		}
		if cost == 0 {
			cost = rm.Cost
		}

		totalRunning += rm.RunningRequests

		if rm.TotalKvCapacityTokens > 0 {
			sumKvCap += float64(rm.TotalKvCapacityTokens)
			podCount++
		}

		if rm.ArrivalRate <= 0 {
			continue
		}
		e2e := rm.AvgTTFT + rm.AvgOutputTokens*rm.AvgITL
		if e2e <= 0 {
			continue
		}

		totalArrivalRate += rm.ArrivalRate
		sumE2E += rm.ArrivalRate * e2e
		sumIL += rm.ArrivalRate * rm.AvgInputTokens
		sumOL += rm.ArrivalRate * rm.AvgOutputTokens
		sumTTFT += rm.ArrivalRate * rm.AvgTTFT
		sumITL += rm.ArrivalRate * rm.AvgITL
		sumHitRate += rm.ArrivalRate * rm.PrefixCacheHitRate
	}

	if podCount == 0 {
		// No KV capacity data at all
		return variantAgg{}, false
	}

	kvCapPerPod := sumKvCap / float64(podCount)

	// N(v): prefer running requests, fall back to Little's Law
	var nTotal float64
	if totalRunning > 0 {
		nTotal = float64(totalRunning)
	} else if totalArrivalRate > 0 && sumE2E > 0 {
		avgE2E := sumE2E / totalArrivalRate
		nTotal = totalArrivalRate * avgE2E
	}

	if nTotal == 0 && totalArrivalRate == 0 {
		// No load signal; cannot produce a meaningful result
		return variantAgg{}, false
	}

	var avgE2E, avgIL, avgOL, avgTTFT, avgITL, hitRate float64
	if totalArrivalRate > 0 {
		avgE2E = sumE2E / totalArrivalRate
		avgIL = sumIL / totalArrivalRate
		avgOL = sumOL / totalArrivalRate
		avgTTFT = sumTTFT / totalArrivalRate
		avgITL = sumITL / totalArrivalRate
		hitRate = sumHitRate / totalArrivalRate
	}

	// Conservative default when hit rate is zero: treat as 1.0 (no cache savings)
	if hitRate <= 0 {
		hitRate = 1.0
	}

	return variantAgg{
		avgE2E:          avgE2E,
		avgIL:           avgIL,
		avgOL:           avgOL,
		avgTTFT:         avgTTFT,
		avgITL:          avgITL,
		hitRate:         hitRate,
		kvCapPerPod:     kvCapPerPod,
		nTotal:          nTotal,
		acceleratorName: accel,
		cost:            cost,
	}, true
}

// computeMixtureWeights assigns all weight to the nearest bin by Euclidean
// distance in the (log IL, log OL) space.  All weight goes to a single bin;
// other bins receive zero.  This is a simple "nearest bin" assignment and
// produces correct results even when only one bin exists.
func computeMixtureWeights(bins []WorkloadBin, avgIL, avgOL float64) map[string]float64 {
	weights := make(map[string]float64, len(bins))
	if len(bins) == 0 {
		return weights
	}

	// Use log-scale distance so that bins with large token counts don't
	// dominate the distance metric.
	logIL := math.Log1p(avgIL)
	logOL := math.Log1p(avgOL)

	bestName := bins[0].Name
	bestDist := math.MaxFloat64

	for _, bin := range bins {
		dIL := math.Log1p(bin.IL) - logIL
		dOL := math.Log1p(bin.OL) - logOL
		dist := dIL*dIL + dOL*dOL
		if dist < bestDist {
			bestDist = dist
			bestName = bin.Name
		}
	}

	weights[bestName] = 1.0
	return weights
}

// e2eForBin estimates E2E latency (seconds) for a specific workload bin given
// variant-level aggregates.  Linear IL scaling is used for TTFT; ITL is
// assumed IL-independent.
func e2eForBin(bin WorkloadBin, agg variantAgg) float64 {
	if agg.avgTTFT <= 0 || agg.avgITL <= 0 {
		return agg.avgE2E
	}

	var ttft float64
	if agg.avgIL > 0 {
		ttft = agg.avgTTFT * (bin.IL / agg.avgIL)
	} else {
		ttft = agg.avgTTFT
	}

	return ttft + bin.OL*agg.avgITL
}

// groupByVariant partitions replica metrics by their VariantName.
func groupByVariant(replicas []interfaces.ReplicaMetrics) map[string][]interfaces.ReplicaMetrics {
	m := make(map[string][]interfaces.ReplicaMetrics)
	for _, rm := range replicas {
		m[rm.VariantName] = append(m[rm.VariantName], rm)
	}
	return m
}

// averageE2E computes the arrival-rate-weighted average E2E latency across all
// replicas.  Returns 0 when no latency signal is available.
func averageE2E(replicas []interfaces.ReplicaMetrics) float64 {
	var totalRate, sumE2E float64
	for _, rm := range replicas {
		if rm.ArrivalRate <= 0 {
			continue
		}
		e2e := rm.AvgTTFT + rm.AvgOutputTokens*rm.AvgITL
		if e2e <= 0 {
			continue
		}
		totalRate += rm.ArrivalRate
		sumE2E += rm.ArrivalRate * e2e
	}
	if totalRate <= 0 {
		return 0
	}
	return sumE2E / totalRate
}
