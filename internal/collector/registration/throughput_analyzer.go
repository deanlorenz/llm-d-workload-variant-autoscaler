// Package registration provides query registration for metrics sources.
// This file registers queries used by the throughput analyzer (ThroughputAnalyzer).
package registration

import (
	ctrl "sigs.k8s.io/controller-runtime"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/logging"
)

// Query name constants for throughput analyzer metrics.
//
// All queries the throughput analyzer needs are registered here so that the
// analyzer engine has no dependency on registrations from other analyzers.
// Where the PromQL duplicates a saturation or queueing-model query, the
// duplication is intentional and noted in the constant's doc comment.
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
	// Note: uses identical PromQL to QueryCacheConfigInfo (saturation.go).
	// Registered independently so the throughput analyzer engine does not depend
	// on RegisterSaturationQueries having been called.
	// Source: vllm:cache_config_info (info-style gauge, static labels)
	QueryKvTokensTotal = "kv_tokens_total"

	// QueryTAAvgOutputTokens is the query name for the average output (generation)
	// tokens per completed request per pod (tok/req), using a 5-minute rate window.
	// Used to compute:
	//   KV_req   = IL_eff + OL/2   (token slots per in-flight request)
	//   λ_dec    = RPS × OL        (decode token demand when EPP unavailable)
	// Note: uses identical PromQL to QueryAvgOutputTokens (saturation.go).
	// Registered independently for throughput analyzer isolation.
	// Source: vllm:request_generation_tokens_sum/count (histogram)
	QueryTAAvgOutputTokens = "ta_avg_output_tokens"

	// QueryTAAvgInputTokens is the query name for the average input (prompt)
	// tokens per completed request per pod (tok/req), using a 5-minute rate window.
	// Used to compute IL_eff = IL × (1 - prefix_hit_rate) in the KV demand formula:
	//   KV_req = IL_eff + OL/2
	// Note: uses identical PromQL to QueryAvgInputTokens (saturation.go).
	// Registered independently for throughput analyzer isolation.
	// Source: vllm:request_prompt_tokens_sum/count (histogram)
	QueryTAAvgInputTokens = "ta_avg_input_tokens"

	// QueryTAPrefixCacheHitRate is the query name for the prefix cache hit rate
	// per pod (0.0–1.0), using a 5-minute rate window.
	// Used to compute the effective input length:
	//   IL_eff = IL × (1 - prefix_hit_rate)
	// A hit rate of 0.3 means 30% of prompt tokens reuse existing KV blocks,
	// reducing per-request KV demand accordingly.
	// Returns NaN when prefix caching is disabled (no queries); the analyzer
	// treats NaN as 0.0 (no cache benefit).
	// Note: uses identical PromQL to QueryPrefixCacheHitRate (saturation.go).
	// Registered independently for throughput analyzer isolation.
	// Source: vllm:prefix_cache_hits / vllm:prefix_cache_queries (counters)
	QueryTAPrefixCacheHitRate = "ta_prefix_cache_hit_rate"

	// QueryVLLMRequestRate is the query name for the vLLM-side request completion
	// rate per pod (requests/sec), derived from the generation tokens histogram count.
	//
	// Used as a fallback for λ_dec estimation when EPP/scheduler metrics are
	// unavailable (QueryDecodeTokenDemand returns no data). The vLLM-side
	// decode token demand is:
	//   λ_dec_vllm = QueryVLLMRequestRate × avg(QueryTAAvgOutputTokens)
	//
	// Note: measures *completed* requests (served demand), not arriving requests.
	// It undercounts when requests are queued in the scheduler. Use
	// QueryDecodeTokenDemand as the primary source and fall back to this only
	// when the EPP is not deployed.
	// Source: vllm:request_generation_tokens_count (histogram _count counter)
	QueryVLLMRequestRate = "vllm_request_rate"

	// QueryTAAvgITL is the query name for the observed average inter-token latency
	// (ITL) per pod (seconds/token), using a 1-minute rate window.
	//
	// This is the primary observable for calibrating the ITL model:
	//   ITL(k) = A×k + B
	// Calibration fits A and B from a rolling window of (k*, ITL_observed) pairs
	// collected across different KV cache utilization operating points.
	//
	// Note: uses identical PromQL to QueryAvgITL (queueing_model.go).
	// Registered independently so the throughput analyzer engine does not depend
	// on RegisterQueueingModelQueries having been called.
	// Source: vllm:time_per_output_token_seconds histogram (sum/count)
	QueryTAAvgITL = "ta_avg_itl"

	// QueryDecodeTokenDemand is the query name for the model-level decode token
	// demand derived from the llm-d inference scheduler (λ_dec, req/s).
	//
	// This query returns the total request dispatch rate (req/s) for the model.
	// The full λ_dec in tokens/sec is computed in the analyzer as:
	//   λ_dec = QueryDecodeTokenDemand × avg(QueryTAAvgOutputTokens)
	//
	// Primary over QueryVLLMRequestRate because the scheduler rate captures
	// queued requests that have not yet reached any vLLM pod.
	//
	// Sanity check: compare against QueryVLLMRequestRate (model-level sum).
	// A gap > 10% between scheduler and vLLM rates indicates active queueing:
	//   λ_dec_sched >> λ_dec_vllm → requests accumulating in scheduler queue
	//   λ_dec_sched <  λ_dec_vllm → metric lag or label mismatch; investigate
	//
	// TODO(#2309): The scheduler metric currently lacks a namespace label in the
	// upstream gateway-api-inference-extension EPP. Filtering by namespace is not
	// possible until the upstream adds it. Queries here filter by target_model_name
	// (or model_name fallback), matching the pattern in QuerySchedulerQueueSize.
	QueryDecodeTokenDemand = "decode_token_demand"
)

// RegisterThroughputAnalyzerQueries registers all queries used by the throughput analyzer.
// It must be called once at engine startup alongside any other analyzer registrations.
//
// Queries registered here cover:
//   - μ_dec supply:    QueryGenerationTokenRate, QueryKvTokensUsed, QueryKvTokensTotal
//   - ITL calibration: QueryTAAvgITL (observed ITL for fitting A, B in ITL(k) = A*k + B)
//   - workload shape:  QueryTAAvgOutputTokens (OL), QueryTAAvgInputTokens (IL),
//     QueryTAPrefixCacheHitRate (prefix hit rate for IL_eff)
//   - λ_dec demand:    QueryDecodeTokenDemand (primary), QueryVLLMRequestRate (EPP fallback)
//
// μ_dec is computed using a linear ITL model:
//
//	ITL(k)   = A*k + B            (calibrated from QueryTAAvgITL × QueryKvTokensUsed pairs)
//	IL_eff   = IL × (1 - prefix_hit_rate)
//	KV_req   = IL_eff + OL/2
//	N_dec(k) = k × KV_max / KV_req
//	μ_dec    = N_dec(k*) / ITL(k*)
//
// λ_dec primary:  QueryDecodeTokenDemand (req/s) × avg(QueryTAAvgOutputTokens) (tok/req)
// λ_dec fallback: QueryVLLMRequestRate   (req/s) × avg(QueryTAAvgOutputTokens) (tok/req)
func RegisterThroughputAnalyzerQueries(sourceRegistry *source.SourceRegistry) {
	metricsSource := sourceRegistry.Get("prometheus")
	if metricsSource == nil {
		ctrl.Log.V(logging.DEBUG).Info("Prometheus source not registered, skipping throughput analyzer query registration")
		return
	}
	registry := metricsSource.QueryList()

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

	// Average output tokens per completed request per pod (tok/req), 5m rate window.
	// Duplicates QueryAvgOutputTokens (saturation.go) — registered independently
	// so the throughput analyzer engine has no dependency on RegisterSaturationQueries.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryTAAvgOutputTokens,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (rate(vllm:request_generation_tokens_sum{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]) / rate(vllm:request_generation_tokens_count{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Average output tokens per completed request per pod (tok/req, 5m rate); used for KV_req and λ_dec calculation",
	})

	// Average input tokens per completed request per pod (tok/req), 5m rate window.
	// Duplicates QueryAvgInputTokens (saturation.go) — registered independently
	// so the throughput analyzer engine has no dependency on RegisterSaturationQueries.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryTAAvgInputTokens,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (rate(vllm:request_prompt_tokens_sum{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]) / rate(vllm:request_prompt_tokens_count{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Average input tokens per completed request per pod (tok/req, 5m rate); used for KV_req = IL_eff + OL/2",
	})

	// Prefix cache hit rate per pod (0.0–1.0), 5m rate window.
	// Used to compute IL_eff = IL × (1 - prefix_hit_rate).
	// Returns NaN when prefix caching is disabled; treated as 0.0 in the analyzer.
	// Duplicates QueryPrefixCacheHitRate (saturation.go) — registered independently.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryTAPrefixCacheHitRate,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (rate(vllm:prefix_cache_hits{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]) / rate(vllm:prefix_cache_queries{namespace="{{.namespace}}",model_name="{{.modelID}}"}[5m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Prefix cache hit rate per pod (0.0-1.0, 5m rate); used for IL_eff = IL × (1 - hit_rate)",
	})

	// Per-pod observed average inter-token latency (seconds/token), 1m rate window.
	// Used as the observable ITL_obs to calibrate the linear ITL model:
	//   ITL(k) = A*k + B
	// The analyzer fits A and B from a rolling window of (k*, ITL_obs) pairs
	// collected as QueryKvTokensUsed and QueryTAAvgITL are sampled over time.
	// Duplicates QueryAvgITL (queueing_model.go) — registered independently
	// so the throughput analyzer engine has no dependency on RegisterQueueingModelQueries.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryTAAvgITL,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (rate(vllm:time_per_output_token_seconds_sum{namespace="{{.namespace}}",model_name="{{.modelID}}"}[1m]) / rate(vllm:time_per_output_token_seconds_count{namespace="{{.namespace}}",model_name="{{.modelID}}"}[1m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Observed average inter-token latency per pod (seconds/token, 1m rate); used as ITL_obs for calibrating ITL(k) = A*k + B",
	})

	// Per-pod vLLM request completion rate (req/s).
	// Derived from the generation tokens histogram _count (increments once per
	// completed request). Used as a fallback for λ_dec when EPP/scheduler metrics
	// are unavailable; the analyzer falls back to:
	//   λ_dec_vllm = QueryVLLMRequestRate × avg(QueryTAAvgOutputTokens)
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryVLLMRequestRate,
		Type:        source.QueryTypePromQL,
		Template:    `sum by (pod) (rate(vllm:request_generation_tokens_count{namespace="{{.namespace}}",model_name="{{.modelID}}"}[1m]))`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "vLLM request completion rate per pod (req/s); fallback for λ_dec when EPP metrics are unavailable",
	})

	// Model-level scheduler request dispatch rate (req/s).
	// Aggregates across all replicas to give the total model-level arrival rate,
	// including requests queued in the scheduler that have not yet reached vLLM.
	// Unlike QuerySchedulerDispatchRate (per-pod, queueing model), this sums
	// across all replicas. Full decode demand: λ_dec = this × avg(QueryTAAvgOutputTokens).
	// Uses target_model_name (resolved after routing) with fallback to model_name,
	// following the same pattern as QuerySchedulerQueueSize.
	registry.MustRegister(source.QueryTemplate{
		Name: QueryDecodeTokenDemand,
		Type: source.QueryTypePromQL,
		Template: `sum(rate(inference_extension_scheduler_attempts_total{status="success",target_model_name="{{.modelID}}"}[1m]))` +
			` or sum(rate(inference_extension_scheduler_attempts_total{status="success",model_name="{{.modelID}}",target_model_name=""}[1m]))`,
		Params:      []string{source.ParamModelID},
		Description: "Model-level scheduler request dispatch rate (req/s); multiply by avg output tokens to get λ_dec (tok/s)",
	})
}
