/*
Copyright 2025 The llm-d Authors

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

package collector

import (
	"context"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	llmdVariantAutoscalingV1alpha1 "github.com/llm-d/llm-d-workload-variant-autoscaler/api/v1alpha1"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/attribution"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/constants"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/metrics"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/utils/scaletarget"
)

const attribTestNS = "test-ns"

// labeledPod builds a pod carrying the llm-d.ai/variant label — the source the
// default Attributor reads VA attribution from.
func labeledPod(name, vaName string) *corev1.Pod {
	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Namespace: attribTestNS,
			Name:      name,
			Labels:    map[string]string{constants.VariantLabelKey: vaName},
		},
	}
}

// attributorWithPods builds a fake client seeded with the given pods and the
// default label Attributor over attribTestNS. The same client is returned so
// callers can hand it to NewReplicaMetricsCollector.
func attributorWithPods(t *testing.T, pods ...*corev1.Pod) (attribution.Attributor, client.Client) {
	t.Helper()
	scheme := runtime.NewScheme()
	if err := llmdVariantAutoscalingV1alpha1.AddToScheme(scheme); err != nil {
		t.Fatalf("AddToScheme (VA): %v", err)
	}
	if err := corev1.AddToScheme(scheme); err != nil {
		t.Fatalf("AddToScheme (corev1): %v", err)
	}
	builder := fake.NewClientBuilder().WithScheme(scheme)
	for _, p := range pods {
		builder = builder.WithObjects(p)
	}
	c := builder.Build()
	a, err := attribution.BuildLabelAttributor(context.Background(), c, []string{attribTestNS})
	if err != nil {
		t.Fatalf("BuildLabelAttributor: %v", err)
	}
	return a, c
}

// attribTestCase drives a single KV-cache sample (replica identity only — the
// metric carries no variant label) through CollectReplicaMetrics together with
// an Attributor built from the seeded pods, then checks the resulting
// ReplicaMetrics carries the expected VariantName (or that the pod is skipped
// when attribution fails).
type attribTestCase struct {
	name        string
	labels      map[string]string // identity labels on the metric sample
	pods        []*corev1.Pod     // pods seeding the label attributor
	wantVAName  string
	wantSkipped bool
}

var attribTestCases = []attribTestCase{
	{
		name: "pod label present, pod attributed – VariantName from attributor",
		labels: map[string]string{
			"pod":      "pod-abc",
			"instance": "10.0.0.1:8000",
		},
		pods:       []*corev1.Pod{labeledPod("pod-abc", "my-va")},
		wantVAName: "my-va",
	},
	{
		name: "pod_name fallback, pod attributed – VariantName from attributor",
		labels: map[string]string{
			"pod_name": "pod-xyz",
			"instance": "10.0.0.2:8000",
		},
		pods:       []*corev1.Pod{labeledPod("pod-xyz", "other-va")},
		wantVAName: "other-va",
	},
	{
		// The metric resolves to a replica identity, but no pod with the variant
		// label backs it, so attribution yields nothing and the pod is skipped.
		name: "pod identity present but not attributed – pod skipped",
		labels: map[string]string{
			"pod":      "pod-unmapped",
			"instance": "10.0.0.3:8000",
		},
		pods:        nil,
		wantSkipped: true,
	},
	{
		name: "no pod identity labels – entry skipped before attribution",
		labels: map[string]string{
			"foo": "bar",
		},
		pods:        []*corev1.Pod{labeledPod("pod-abc", "my-va")},
		wantSkipped: true,
	},
	{
		// instance-only metrics carry no pod name, so there is no pod identity to
		// attribute against — the pod is skipped even though a labeled pod exists.
		name: "instance-only (no pod name) – not attributable, skipped",
		labels: map[string]string{
			"instance": "10.0.0.5:8000",
		},
		pods:        []*corev1.Pod{labeledPod("pod-abc", "my-va")},
		wantSkipped: true,
	},
}

func TestCollectReplicaMetrics_Attribution(t *testing.T) {
	for _, tc := range attribTestCases {
		t.Run(tc.name, func(t *testing.T) {
			registry := prometheus.NewRegistry()
			if err := metrics.InitMetrics(registry); err != nil {
				t.Fatalf("InitMetrics: %v", err)
			}

			attributor, k8sClient := attributorWithPods(t, tc.pods...)

			mockSource := &mockMetricsSource{
				refreshFunc: func(_ context.Context, _ source.RefreshSpec) (map[string]*source.MetricResult, error) {
					return map[string]*source.MetricResult{
						"kv_cache_usage": {
							Values: []source.MetricValue{
								{
									Labels:    tc.labels,
									Value:     0.5,
									Timestamp: time.Now(),
								},
							},
						},
					}, nil
				},
			}

			collector := NewReplicaMetricsCollector(mockSource, k8sClient, nil)
			results, err := collector.CollectReplicaMetrics(
				context.Background(),
				"test-model",
				attribTestNS,
				make(map[string]scaletarget.ScaleTargetAccessor),
				make(map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling),
				nil,
				make(map[string]float64),
				attributor,
			)
			if err != nil {
				t.Fatalf("CollectReplicaMetrics: %v", err)
			}

			if tc.wantSkipped {
				if len(results) != 0 {
					t.Errorf("expected no results for skipped entry, got %d", len(results))
				}
				return
			}

			if len(results) == 0 {
				t.Fatalf("expected at least one ReplicaMetrics result")
			}

			got := results[0].VariantName
			if got != tc.wantVAName {
				t.Errorf("VariantName: got %q, want %q", got, tc.wantVAName)
			}
		})
	}
}
