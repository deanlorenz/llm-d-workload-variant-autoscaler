package registration

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source/prometheus"
)

var _ = Describe("RegisterThroughputAnalyzerQueries", func() {
	var (
		ctx       context.Context
		registry  *source.SourceRegistry
		mockAPI   *mockPrometheusAPI
		queryList *source.QueryList
	)

	BeforeEach(func() {
		ctx = context.Background()
		registry = source.NewSourceRegistry()
		mockAPI = &mockPrometheusAPI{}
	})

	Context("when prometheus source is registered", func() {
		BeforeEach(func() {
			metricsSource := prometheus.NewPrometheusSource(ctx, mockAPI, prometheus.DefaultPrometheusSourceConfig())
			err := registry.Register("prometheus", metricsSource)
			Expect(err).NotTo(HaveOccurred())
			RegisterThroughputAnalyzerQueries(registry)
			queryList = registry.Get("prometheus").QueryList()
		})

		It("should not panic during registration", func() {
			reg2 := source.NewSourceRegistry()
			metricsSource2 := prometheus.NewPrometheusSource(ctx, mockAPI, prometheus.DefaultPrometheusSourceConfig())
			Expect(reg2.Register("prometheus", metricsSource2)).To(Succeed())
			Expect(func() {
				RegisterThroughputAnalyzerQueries(reg2)
			}).NotTo(Panic())
		})

		It("should register all throughput analyzer queries with correct type", func() {
			expectedQueries := []string{
				QueryGenerationTokenRate,
				QueryKvTokensUsed,
				QueryKvTokensTotal,
				QueryTAAvgOutputTokens,
				QueryTAAvgInputTokens,
				QueryTAPrefixCacheHitRate,
				QueryTAAvgITL,
				QueryVLLMRequestRate,
				QueryDecodeTokenDemand,
			}
			for _, name := range expectedQueries {
				q := queryList.Get(name)
				Expect(q).NotTo(BeNil(), "expected query %q to be registered", name)
				Expect(q.Name).To(Equal(name))
				Expect(q.Type).To(Equal(source.QueryTypePromQL))
			}
		})

		It("should build QueryGenerationTokenRate with namespace and model substituted", func() {
			rendered, err := queryList.Build(QueryGenerationTokenRate, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`namespace="test-ns"`))
			Expect(rendered).To(ContainSubstring(`model_name="test-model"`))
			Expect(rendered).To(ContainSubstring(`[1m]`))
			Expect(rendered).To(ContainSubstring(`vllm:request_generation_tokens_sum`))
		})

		It("should build QueryKvTokensUsed without max_over_time", func() {
			rendered, err := queryList.Build(QueryKvTokensUsed, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:kv_cache_usage_perc`))
			Expect(rendered).NotTo(ContainSubstring(`max_over_time`))
		})

		It("should build QueryKvTokensTotal with block label dimensions", func() {
			rendered, err := queryList.Build(QueryKvTokensTotal, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:cache_config_info`))
			Expect(rendered).To(ContainSubstring(`num_gpu_blocks`))
			Expect(rendered).To(ContainSubstring(`block_size`))
		})

		It("should build QueryTAAvgITL with 1m window over ITL histogram", func() {
			rendered, err := queryList.Build(QueryTAAvgITL, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:time_per_output_token_seconds_sum`))
			Expect(rendered).To(ContainSubstring(`vllm:time_per_output_token_seconds_count`))
			Expect(rendered).To(ContainSubstring(`[1m]`))
		})

		It("should build QueryTAAvgOutputTokens with 5m window", func() {
			rendered, err := queryList.Build(QueryTAAvgOutputTokens, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:request_generation_tokens_sum`))
			Expect(rendered).To(ContainSubstring(`[5m]`))
		})

		It("should build QueryTAAvgInputTokens with 5m window", func() {
			rendered, err := queryList.Build(QueryTAAvgInputTokens, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:request_prompt_tokens_sum`))
			Expect(rendered).To(ContainSubstring(`[5m]`))
		})

		It("should build QueryTAPrefixCacheHitRate with 5m window", func() {
			rendered, err := queryList.Build(QueryTAPrefixCacheHitRate, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:prefix_cache_hits`))
			Expect(rendered).To(ContainSubstring(`vllm:prefix_cache_queries`))
			Expect(rendered).To(ContainSubstring(`[5m]`))
		})

		It("should build QueryVLLMRequestRate with 1m window over token count", func() {
			rendered, err := queryList.Build(QueryVLLMRequestRate, map[string]string{
				source.ParamNamespace: "test-ns",
				source.ParamModelID:   "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`vllm:request_generation_tokens_count`))
			Expect(rendered).To(ContainSubstring(`[1m]`))
		})

		It("should build QueryDecodeTokenDemand using scheduler attempts metric", func() {
			rendered, err := queryList.Build(QueryDecodeTokenDemand, map[string]string{
				source.ParamModelID: "test-model",
			})
			Expect(err).NotTo(HaveOccurred())
			Expect(rendered).To(ContainSubstring(`inference_extension_scheduler_attempts_total`))
			Expect(rendered).To(ContainSubstring(`test-model`))
			Expect(rendered).To(ContainSubstring(`status="success"`))
		})
	})

	Context("when prometheus source is not registered", func() {
		It("should not panic", func() {
			Expect(func() {
				RegisterThroughputAnalyzerQueries(registry)
			}).NotTo(Panic())
		})
	})
})
