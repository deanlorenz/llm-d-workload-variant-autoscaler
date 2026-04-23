// Package registration provides query registration for metrics sources.
// This file registers queries used by the throughput analyzer (ThroughputAnalyzer).
package registration

import (
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
)

// Query name constants for throughput analyzer metrics.
//
// These queries support the throughput analyzer's μ_dec supply and λ_dec demand
// computation. The analyzer estimates decode token throughput supply (μ_dec)
// from observed generation rates and KV cache occupancy, then compares it
// against decode token demand (λ_dec) derived from the scheduler.
const (
	// QueryGenerationTokenRate is the query name for the observed generation
	// (decode) token rate per pod (tokens/sec).
	// This is the primary observable proxy for μ_dec^obs per replica.
	// Source: vllm:request_generation_tokens_sum (counter)
	QueryGenerationTokenRate = "generation_token_rate"

	// QueryKvTokensUsed is the query name for the current KV cache utilization
	// fraction per pod (0.0–1.0), measured instantaneously.
	// Used as k* (current operating point) in the ITL model: ITL(k*) = A*k* + B.
	// The actual tokens-in-use is derived in the analyzer as:
	//   kvTokensUsed = QueryKvTokensUsed × (num_gpu_blocks × block_size)
	// where num_gpu_blocks and block_size are parsed from QueryKvTokensTotal labels.
	// Note: unlike QueryKvCacheUsage (saturation), this query does NOT use
	// max_over_time — the throughput analyzer needs the current operating point,
	// not the peak within the window.
	// Source: vllm:kv_cache_usage_perc (gauge)
	QueryKvTokensUsed = "kv_tokens_used"

	// QueryKvTokensTotal is the query name for the KV cache block configuration
	// per pod. Returns the vllm:cache_config_info series with num_gpu_blocks and
	// block_size as Prometheus labels.
	// Total token capacity per pod is computed in the analyzer as:
	//   kvTokensTotal = num_gpu_blocks × block_size
	// Source: vllm:cache_config_info (info-style gauge, static labels)
	QueryKvTokensTotal = "kv_tokens_total"

	// QueryDecodeTokenDemand is the query name for the model-level decode token
	// demand derived from the llm-d inference scheduler (λ_dec, tokens/sec).
	//
	// This query returns the total request dispatch rate (req/s) for the model.
	// The full λ_dec in tokens/sec is computed in the analyzer as:
	//   λ_dec = QueryDecodeTokenDemand × avg(QueryAvgOutputTokens)
	//
	// Approach: Option C from TA-Plan (scheduler-based demand, per-model aggregation).
	// The scheduler rate captures queued requests that have not yet reached any
	// vLLM pod, unlike the vLLM-side QueryGenerationTokenRate which only reflects
	// served (not queued) demand.
	//
	// Sanity check: compare against QueryGenerationTokenRate (model-level sum).
	// A gap > 10% between scheduler demand and vLLM-served rate indicates queueing:
	//   λ_dec_sched >> λ_dec_vllm → requests are accumulating in the scheduler queue
	//   λ_dec_sched <  λ_dec_vllm → metric lag or label mismatch; investigate
	//
	// TODO(#2309): The scheduler metric currently lacks a namespace label in the
	// upstream gateway-api-inference-extension EPP. Filtering by namespace is not
	// possible until the upstream adds it. Queries here filter by target_model_name
	// (or model_name fallback), matching the pattern in QuerySchedulerQueueSize.
	QueryDecodeTokenDemand = "decode_token_demand"
)

// RegisterThroughputAnalyzerQueries registers queries used by the throughput analyzer.
//
// These queries provide the raw metrics for computing:
//   - μ_dec (decode supply):  QueryGenerationTokenRate, QueryKvTokensUsed, QueryKvTokensTotal
//   - λ_dec (decode demand):  QueryDecodeTokenDemand (combined with QueryAvgOutputTokens)
//
// The throughput analyzer computes μ_dec using a linear ITL model:
//
//	ITL(k) = A*k + B
//	N_dec(k) = k × KV_max / KV_req
//	μ_dec    = N_dec(k*) / ITL(k*)
//
// where k* is the current KV utilization fraction and KV_max = num_gpu_blocks × block_size.
//
// λ_dec is computed as: QueryDecodeTokenDemand (req/s) × avg(QueryAvgOutputTokens) (tok/req).
func RegisterThroughputAnalyzerQueries(sourceRegistry *source.SourceRegistry) {
	registry := sourceRegistry.Get("prometheus").QueryList()

	// Per-pod observed generation (decode) token rate (tokens/sec).
	// Computed as the rate of the _sum histogram counter over 1m.
	// Uses sum by (pod) because request_generation_tokens_sum is an additive
	// counter — multiple histogram buckets per pod must be summed.
	// Rate window of 1m balances responsiveness with smoothing.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryGenerationTokenRate,
		Type:        source.QueryTypePromQL,
		Template:    `sum by (pod) (rate(vllm:request_generation_tokens_sum{namespace="{{.namespace}}",model_name="{{.modelID}}"}[1m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Observed generation (decode) token rate per pod (tokens/sec), proxy for μ_dec^obs",
	})

	// Per-pod instantaneous KV cache utilization (0.0–1.0).
	// Uses max by (pod) to consolidate any duplicate series (e.g., from multiple
	// label combinations) to a single per-pod value.
	// Does NOT use max_over_time: the throughput analyzer needs the current
	// operating point k*, not the worst-case peak used by the saturation analyzer.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryKvTokensUsed,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (vllm:kv_cache_usage_perc{namespace="{{.namespace}}",model_name="{{.modelID}}"})`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Instantaneous KV cache utilization per pod (0.0–1.0), used as k* in the ITL model",
	})

	// Per-pod KV cache block configuration (static info metric).
	// Returns vllm:cache_config_info with num_gpu_blocks and block_size as labels.
	// The analyzer computes total token capacity as: num_gpu_blocks × block_size.
	// Uses max to deduplicate when multiple series exist per pod.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryKvTokensTotal,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod, num_gpu_blocks, block_size) (vllm:cache_config_info{namespace="{{.namespace}}",model_name="{{.modelID}}"})`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "KV cache block configuration per pod (num_gpu_blocks and block_size as labels); total capacity = num_gpu_blocks × block_size",
	})

	// Model-level scheduler request dispatch rate (req/s).
	// Represents the rate of requests arriving at the llm-d inference scheduler
	// and being dispatched to vLLM replicas. Unlike QuerySchedulerDispatchRate
	// (per-pod, used by the queueing model), this query aggregates across all
	// replicas to give the total model-level demand rate.
	//
	// The full decode token demand is: λ_dec = QueryDecodeTokenDemand × avg(QueryAvgOutputTokens).
	//
	// Uses target_model_name (resolved model after routing) with fallback to
	// model_name when target_model_name is not set, following the same pattern
	// as QuerySchedulerQueueSize.
	registry.MustRegister(source.QueryTemplate{
		Name: QueryDecodeTokenDemand,
		Type: source.QueryTypePromQL,
		Template: `sum(rate(inference_extension_scheduler_attempts_total{status="success",target_model_name="{{.modelID}}"}[1m]))` +
			` or sum(rate(inference_extension_scheduler_attempts_total{status="success",model_name="{{.modelID}}",target_model_name=""}[1m]))`,
		Params:      []string{source.ParamModelID},
		Description: "Model-level scheduler request dispatch rate (req/s); multiply by avg output tokens to get λ_dec (decode token demand, tok/s)",
	})
}
