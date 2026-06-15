package saturation

import (
	"context"
	"testing"

	"github.com/go-logr/logr"
	"github.com/go-logr/zapr"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"go.uber.org/zap/zaptest/observer"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/engines/pipeline"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/interfaces"
)

func TestLogDecisionSummary_EmitsRequiredFields(t *testing.T) {
	core, logs := observer.New(zapcore.InfoLevel)
	logger := zapr.NewLogger(zap.New(core))
	ctx := logr.NewContext(context.Background(), logger)

	req := pipeline.ModelScalingRequest{
		ModelID:   "mymodel",
		Namespace: "ns",
		AnalyzerResults: []pipeline.NamedAnalyzerResult{
			{
				Name: interfaces.SaturationAnalyzerName,
				Result: &interfaces.AnalyzerResult{
					TotalSupply:      100000,
					TotalDemand:      80000,
					Utilization:      0.8,
					RequiredCapacity: 0,
					SpareCapacity:    20000,
					VariantCapacities: []interfaces.VariantCapacity{
						{
							VariantName:        "primary",
							Cost:               10,
							PerReplicaCapacity: 50000,
							ReplicaCount:       1,
						},
					},
					SaturationVariantCapacities: []interfaces.SaturationVariantCapacity{
						{
							VariantName:   "primary",
							MedianK1:      60000,
							MedianK2:      50000,
							K2SourceLabel: "P2-hist",
						},
					},
				},
			},
		},
	}
	decisions := []interfaces.VariantDecision{
		{
			ModelID:         "mymodel",
			Namespace:       "ns",
			VariantName:     "primary",
			CurrentReplicas: 1,
			TargetReplicas:  2,
			Action:          interfaces.ActionScaleUp,
		},
	}

	logDecisionSummary(ctx, []pipeline.ModelScalingRequest{req}, decisions)

	require.Equal(t, 1, logs.Len(), "expected one log line")
	entry := logs.All()[0]
	require.Equal(t, "saturation cycle summary", entry.Message)

	fields := entry.ContextMap()
	for _, key := range []string{"model", "totalSupply", "totalDemand", "utilization", "analyzerSignals", "variants"} {
		assert.Contains(t, fields, key, "missing key %q", key)
	}
	assert.Equal(t, "ns/mymodel", fields["model"])
}

func TestLogDecisionSummary_SkipsModelWithNoSatResult(t *testing.T) {
	core, logs := observer.New(zapcore.InfoLevel)
	logger := zapr.NewLogger(zap.New(core))
	ctx := logr.NewContext(context.Background(), logger)

	req := pipeline.ModelScalingRequest{
		ModelID:   "mymodel",
		Namespace: "ns",
		AnalyzerResults: []pipeline.NamedAnalyzerResult{
			{Name: "throughput", Result: &interfaces.AnalyzerResult{}},
		},
	}

	logDecisionSummary(ctx, []pipeline.ModelScalingRequest{req}, nil)

	assert.Equal(t, 0, logs.Len(), "expected no log line when saturation result absent")
}

func TestLogDecisionSummary_MultipleAnalyzerSignals(t *testing.T) {
	core, logs := observer.New(zapcore.InfoLevel)
	logger := zapr.NewLogger(zap.New(core))
	ctx := logr.NewContext(context.Background(), logger)

	req := pipeline.ModelScalingRequest{
		ModelID:   "m",
		Namespace: "ns",
		AnalyzerResults: []pipeline.NamedAnalyzerResult{
			{
				Name: interfaces.SaturationAnalyzerName,
				Result: &interfaces.AnalyzerResult{
					TotalSupply:       200000,
					TotalDemand:       150000,
					Utilization:       0.75,
					RequiredCapacity:  0,
					SpareCapacity:     50000,
					VariantCapacities: []interfaces.VariantCapacity{},
				},
			},
			{
				Name: "throughput",
				Result: &interfaces.AnalyzerResult{
					RequiredCapacity: 15000,
					SpareCapacity:    0,
				},
			},
		},
	}

	logDecisionSummary(ctx, []pipeline.ModelScalingRequest{req}, nil)

	require.Equal(t, 1, logs.Len())
	fields := logs.All()[0].ContextMap()
	assert.Contains(t, fields, "analyzerSignals")
}
