/*
Copyright 2026 The llm-d Authors

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
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	appsv1 "k8s.io/api/apps/v1"
	autoscalingv2 "k8s.io/api/autoscaling/v2"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/tools/record"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	llmdVariantAutoscalingV1alpha1 "github.com/llm-d/llm-d-workload-variant-autoscaler/api/v1alpha1"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/registration"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/constants"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/metrics"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/utils"
	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/utils/scaletarget"
)

// mockMetricsSource is a mock implementation of source.MetricsSource for testing
type mockMetricsSource struct {
	refreshFunc  func(ctx context.Context, spec source.RefreshSpec) (map[string]*source.MetricResult, error)
	refreshError error
	results      map[string]*source.MetricResult
}

func (m *mockMetricsSource) QueryList() *source.QueryList {
	return source.NewQueryList()
}

func (m *mockMetricsSource) Refresh(ctx context.Context, spec source.RefreshSpec) (map[string]*source.MetricResult, error) {
	// If refreshFunc is set, use it (takes precedence)
	if m.refreshFunc != nil {
		return m.refreshFunc(ctx, spec)
	}
	// Otherwise use the error/results fields
	if m.refreshError != nil {
		return nil, m.refreshError
	}
	if m.results != nil {
		return m.results, nil
	}
	// Return empty results by default
	emptyResults := make(map[string]*source.MetricResult)
	for _, query := range spec.Queries {
		emptyResults[query] = &source.MetricResult{
			QueryName: query,
			Values:    []source.MetricValue{},
		}
	}
	return emptyResults, nil
}

func (m *mockMetricsSource) Get(queryName string, params map[string]string) *source.CachedValue {
	return nil
}

func TestRecordMetricsUnavailableEvent(t *testing.T) {
	tests := []struct {
		name         string
		numVAs       int
		expectedEvts int
	}{
		{
			name:         "records event for single VA",
			numVAs:       1,
			expectedEvts: 1,
		},
		{
			name:         "records event for multiple VAs",
			numVAs:       3,
			expectedEvts: 3,
		},
		{
			name:         "handles empty VA map",
			numVAs:       0,
			expectedEvts: 0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fakeRecorder := record.NewFakeRecorder(100)
			mockSource := &mockMetricsSource{}
			collector := NewReplicaMetricsCollector(mockSource, nil, fakeRecorder)

			variantAutoscalings := make(map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling)
			for i := 0; i < tt.numVAs; i++ {
				vaName := "test-va"
				if i > 0 {
					vaName = "test-va-" + string(rune('a'+i))
				}
				variantAutoscalings["default/"+vaName] = &llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
					ObjectMeta: metav1.ObjectMeta{
						Name:      vaName,
						Namespace: "default",
					},
					Spec: llmdVariantAutoscalingV1alpha1.VariantAutoscalingSpec{
						ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{
							Kind: "Deployment",
							Name: vaName + "-deployment",
						},
						ModelID:     "test-model",
						MaxReplicas: 5,
					},
				}
			}

			collector.recordMetricsUnavailableEvent(variantAutoscalings, nil, "Test metrics unavailable")

			// Count recorded events
			eventCount := 0
			for {
				select {
				case event := <-fakeRecorder.Events:
					assert.Contains(t, event, constants.K8SEventMetricsUnavailable,
						"Event should contain K8SEventMetricsUnavailable constant")
					assert.Contains(t, event, "Test metrics unavailable",
						"Event should contain the reason message")
					eventCount++
				default:
					goto done
				}
			}
		done:
			assert.Equal(t, tt.expectedEvts, eventCount,
				"Should record correct number of events")
		})
	}
}

func TestCollectReplicaMetrics_ErrorRecordsEvent(t *testing.T) {
	// This test verifies edge-triggered event emission for metrics collection errors.
	// Note: Without actual pod data in the k8s client, replicaMetrics is always empty,
	// so we can't test the full "available → error" transition. This test focuses on
	// verifying that repeated errors don't flood the event stream.

	ctx := context.Background()
	fakeRecorder := record.NewFakeRecorder(100)

	variantAutoscalings := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		"default/test-va": {
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-va",
				Namespace: "default",
			},
			Spec: llmdVariantAutoscalingV1alpha1.VariantAutoscalingSpec{
				ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{
					Kind: "Deployment",
					Name: "test-deployment",
				},
				ModelID:     "test-model",
				MaxReplicas: 5,
			},
		},
	}

	scaleTargets := make(map[string]scaletarget.ScaleTargetAccessor)
	variantCosts := make(map[string]float64)

	// Simulate metrics collection failure
	mockSource := &mockMetricsSource{
		refreshError: errors.New("prometheus connection failed"),
	}
	collector := NewReplicaMetricsCollector(mockSource, nil, fakeRecorder)

	// First call with error: no event (first observation, unknown previous state)
	metrics, err := collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.Error(t, err, "Should return error when refresh fails")
	require.Nil(t, metrics, "Should return nil metrics on error")

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("No event expected on first observation: %s", event)
	default:
		// Expected: no event
	}

	// Second call: metrics still fail, should NOT emit event (no state transition)
	_, err = collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.Error(t, err, "Should still return error")

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("No event expected when metrics remain unavailable: %s", event)
	default:
		// Expected: no event
	}
}

func TestCollectReplicaMetrics_NoMetricsRecordsEvent(t *testing.T) {
	// This test verifies edge-triggered event emission when no metrics are available.
	// Simulates a VA scaled to zero (no pods = no metrics) to verify that repeated
	// "no metrics" states don't flood the event stream.

	ctx := context.Background()
	fakeRecorder := record.NewFakeRecorder(100)

	variantAutoscalings := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		"default/test-va": {
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-va",
				Namespace: "default",
			},
			Spec: llmdVariantAutoscalingV1alpha1.VariantAutoscalingSpec{
				ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{
					Kind: "Deployment",
					Name: "test-deployment",
				},
				ModelID:     "test-model",
				MaxReplicas: 5,
			},
		},
	}

	scaleTargets := make(map[string]scaletarget.ScaleTargetAccessor)
	variantCosts := make(map[string]float64)

	// Mock source with no metrics (e.g., VA scaled to zero)
	mockSource := &mockMetricsSource{
		results: make(map[string]*source.MetricResult),
	}
	collector := NewReplicaMetricsCollector(mockSource, nil, fakeRecorder)

	// First call: no metrics, should NOT emit event (first observation, unknown previous state)
	metrics, err := collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err, "Should not return error when no metrics available")
	require.Empty(t, metrics, "Should return empty metrics slice")

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("No event expected on first observation: %s", event)
	default:
		// Expected: no event
	}

	// Second call: still no metrics, should NOT emit event (no state transition)
	_, err = collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err, "Should not return error")

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("No event expected when metrics remain unavailable: %s", event)
	default:
		// Expected: no event
	}

	// Third call: still no metrics, should NOT emit event (no state transition)
	_, err = collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err, "Should not return error")

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("No event expected when metrics remain unavailable: %s", event)
	default:
		// Expected: no event
	}
}

func TestK8SEventMetricsUnavailableConstant(t *testing.T) {
	// Verify the constant is correctly defined
	assert.Equal(t, "MetricsUnavailable", constants.K8SEventMetricsUnavailable,
		"K8SEventMetricsUnavailable constant should match expected value")
}

func TestCollectReplicaMetrics_EdgeTriggeredEvents(t *testing.T) {
	// This test verifies the core edge-triggered behavior: events are emitted only on
	// state transitions, not on every cycle with unavailable metrics. This prevents
	// event flooding when a VA is legitimately scaled to zero.

	ctx := context.Background()
	fakeRecorder := record.NewFakeRecorder(100)

	variantAutoscalings := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		"default/test-va": {
			ObjectMeta: metav1.ObjectMeta{
				Name:      "test-va",
				Namespace: "default",
			},
			Spec: llmdVariantAutoscalingV1alpha1.VariantAutoscalingSpec{
				ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{
					Kind: "Deployment",
					Name: "test-deployment",
				},
				ModelID:     "test-model",
				MaxReplicas: 5,
			},
		},
	}

	scaleTargets := make(map[string]scaletarget.ScaleTargetAccessor)
	variantCosts := make(map[string]float64)

	// Mock source that starts with no metrics (simulates VA scaled to zero)
	mockSource := &mockMetricsSource{
		results: make(map[string]*source.MetricResult),
	}
	collector := NewReplicaMetricsCollector(mockSource, nil, fakeRecorder)

	// First call: metrics unavailable, should NOT emit event (first observation, unknown previous state)
	_, err := collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err)

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("First call should not emit event (unknown previous state): %s", event)
	default:
		// Expected: no event - prevents false positive for VAs that start at zero
	}

	// Second call: metrics still unavailable, should NOT emit event (no state transition)
	_, err = collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err)

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("Second call should not emit event when metrics remain unavailable: %s", event)
	default:
		// Expected: no event - prevents flooding on every optimization cycle
	}

	// Third call: still unavailable, should NOT emit event
	_, err = collector.CollectReplicaMetrics(ctx, "test-model", "default", scaleTargets, variantAutoscalings, nil, variantCosts, nil)
	require.NoError(t, err)

	select {
	case event := <-fakeRecorder.Events:
		t.Errorf("Third call should not emit event when metrics remain unavailable: %s", event)
	default:
		// Expected: no event
	}
}

func TestCollectReplicaMetrics_MetricsObservation(t *testing.T) {
	// Initialize metrics with a fresh registry
	registry := prometheus.NewRegistry()
	if err := metrics.InitMetrics(registry); err != nil {
		t.Fatalf("Failed to initialize metrics: %v", err)
	}

	// Create a mock source that returns empty results
	mockSource := &mockMetricsSource{
		refreshFunc: func(ctx context.Context, spec source.RefreshSpec) (map[string]*source.MetricResult, error) {
			// Simulate some query latency
			time.Sleep(10 * time.Millisecond)
			// Return empty results
			return make(map[string]*source.MetricResult), nil
		},
	}

	// Create test dependencies
	scheme := runtime.NewScheme()
	err := llmdVariantAutoscalingV1alpha1.AddToScheme(scheme)
	if err != nil {
		t.Fatalf("Failed to add scheme: %v", err)
	}
	k8sClient := fake.NewClientBuilder().WithScheme(scheme).Build()
	fakeRecorder := record.NewFakeRecorder(100)
	collector := NewReplicaMetricsCollector(mockSource, k8sClient, fakeRecorder)

	// Call the function
	_, err = collector.CollectReplicaMetrics(
		context.Background(),
		"test-model",
		"test-namespace",
		make(map[string]scaletarget.ScaleTargetAccessor),
		make(map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling),
		nil,
		make(map[string]float64),
		nil,
	)
	if err != nil {
		t.Fatalf("CollectReplicaMetrics failed: %v", err)
	}

	// Gather metrics from the registry
	metricFamilies, err := registry.Gather()
	if err != nil {
		t.Fatalf("Failed to gather metrics: %v", err)
	}

	// Verify ObserveMetricsCollectionDuration was called for all query types
	var foundDurationMetric bool
	expectedQueryTypes := map[string]bool{
		constants.QueryTypeKVCache:     false,
		constants.QueryTypeQueueLength: false,
		constants.QueryTypeCacheConfig: false,
	}

	for _, mf := range metricFamilies {
		if mf.GetName() == constants.WVAMetricsCollectionDurationSeconds {
			foundDurationMetric = true

			// Check each metric series
			for _, m := range mf.GetMetric() {
				// Find query_type label
				for _, label := range m.GetLabel() {
					if label.GetName() == constants.LabelQueryType {
						queryType := label.GetValue()
						if _, exists := expectedQueryTypes[queryType]; exists {
							expectedQueryTypes[queryType] = true
							histogram := m.GetHistogram()
							if histogram == nil {
								t.Errorf("Expected histogram for query_type=%s", queryType)
								continue
							}
							if histogram.GetSampleCount() == 0 {
								t.Errorf("Expected at least one observation for query_type=%s", queryType)
							}
							if histogram.GetSampleSum() <= 0 {
								t.Errorf("Expected positive duration for query_type=%s", queryType)
							}
						}
					}
				}
			}
		}
	}

	if !foundDurationMetric {
		t.Errorf("Metric %s not found", constants.WVAMetricsCollectionDurationSeconds)
	}

	// Verify all expected query types were recorded
	for queryType, found := range expectedQueryTypes {
		if !found {
			t.Errorf("Expected duration metric for query_type=%s but was not found", queryType)
		}
	}

	// Verify SetMetricsPodsDiscovered was called
	var foundPodsMetric bool
	for _, mf := range metricFamilies {
		if mf.GetName() == constants.WVAMetricsPodsDiscovered {
			foundPodsMetric = true
			// Should have at least one metric (for test-namespace)
			if len(mf.GetMetric()) == 0 {
				t.Error("Expected at least one pods discovered metric")
			}
		}
	}

	if !foundPodsMetric {
		t.Errorf("Metric %s not found", constants.WVAMetricsPodsDiscovered)
	}
}

func TestCollectReplicaMetrics_ErrorMetrics(t *testing.T) {
	// Initialize metrics with a fresh registry
	registry := prometheus.NewRegistry()
	if err := metrics.InitMetrics(registry); err != nil {
		t.Fatalf("Failed to initialize metrics: %v", err)
	}

	// Create a mock source that returns an error
	testErr := context.DeadlineExceeded
	mockSource := &mockMetricsSource{
		refreshFunc: func(ctx context.Context, spec source.RefreshSpec) (map[string]*source.MetricResult, error) {
			return nil, testErr
		},
	}

	// Create test dependencies
	scheme := runtime.NewScheme()
	err := llmdVariantAutoscalingV1alpha1.AddToScheme(scheme)
	if err != nil {
		t.Fatalf("Failed to add scheme: %v", err)
	}
	k8sClient := fake.NewClientBuilder().WithScheme(scheme).Build()
	fakeRecorder := record.NewFakeRecorder(100)
	collector := NewReplicaMetricsCollector(mockSource, k8sClient, fakeRecorder)

	// Call the function - should return error
	_, err = collector.CollectReplicaMetrics(
		context.Background(),
		"test-model",
		"test-namespace",
		make(map[string]scaletarget.ScaleTargetAccessor),
		make(map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling),
		nil,
		make(map[string]float64),
		nil,
	)
	if err == nil {
		t.Fatal("Expected error but got nil")
	}

	// Gather metrics from the registry
	metricFamilies, err := registry.Gather()
	if err != nil {
		t.Fatalf("Failed to gather metrics: %v", err)
	}

	// Verify IncMetricsCollectionErrors was called for all query types
	var foundErrorMetric bool
	expectedQueryTypes := map[string]bool{
		constants.QueryTypeKVCache:     false,
		constants.QueryTypeQueueLength: false,
		constants.QueryTypeCacheConfig: false,
	}

	for _, mf := range metricFamilies {
		if mf.GetName() == constants.WVAMetricsCollectionErrorsTotal {
			foundErrorMetric = true

			// Check each metric series
			for _, m := range mf.GetMetric() {
				// Find query_type label
				var queryType string
				for _, label := range m.GetLabel() {
					if label.GetName() == constants.LabelQueryType {
						queryType = label.GetValue()
						break
					}
				}

				if _, exists := expectedQueryTypes[queryType]; exists {
					expectedQueryTypes[queryType] = true
					counter := m.GetCounter()
					if counter == nil {
						t.Errorf("Expected counter for query_type=%s", queryType)
						continue
					}
					if counter.GetValue() != 1.0 {
						t.Errorf("Expected error count 1 for query_type=%s, got %f", queryType, counter.GetValue())
					}
				}
			}
		}
	}

	if !foundErrorMetric {
		t.Errorf("Metric %s not found", constants.WVAMetricsCollectionErrorsTotal)
	}

	// Verify all expected query types were recorded
	for queryType, found := range expectedQueryTypes {
		if !found {
			t.Errorf("Expected error metric for query_type=%s but was not found", queryType)
		}
	}
}

// TestCollectReplicaMetrics_ThroughputKeyMerge is the regression guard for the
// latent key-mismatch where the throughput-analyzer loops keyed podData by the
// bare pod name while every other query keyed by the instance key (pod:port).
// A KV-cache sample and a generation-token-rate sample for the same replica
// (same instance + pod labels) must now merge into a single ReplicaMetrics
// entry carrying both KvCacheUsage and GenerationTokenRate.
func TestCollectReplicaMetrics_ThroughputKeyMerge(t *testing.T) {
	registry := prometheus.NewRegistry()
	if err := metrics.InitMetrics(registry); err != nil {
		t.Fatalf("InitMetrics: %v", err)
	}

	// Same replica identity on both samples → same instance key (pod-merge:8000).
	identity := map[string]string{
		"pod":      "pod-merge",
		"instance": "10.0.0.7:8000",
	}

	attributor, k8sClient := attributorWithPods(t, labeledPod("pod-merge", "merge-va"))

	mockSource := &mockMetricsSource{
		refreshFunc: func(_ context.Context, _ source.RefreshSpec) (map[string]*source.MetricResult, error) {
			return map[string]*source.MetricResult{
				registration.QueryKvCacheUsage: {
					Values: []source.MetricValue{
						{Labels: identity, Value: 0.42, Timestamp: time.Now()},
					},
				},
				registration.QueryGenerationTokenRate: {
					Values: []source.MetricValue{
						{Labels: identity, Value: 123.0, Timestamp: time.Now()},
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

	require.Len(t, results, 1, "KV and generation-token-rate samples for the same replica must merge into one entry")
	got := results[0]
	assert.Equal(t, "merge-va", got.VariantName)
	assert.Greater(t, got.KvCacheUsage, 0.0, "KvCacheUsage should be populated from the KV sample")
	assert.Equal(t, 123.0, got.GenerationTokenRate, "GenerationTokenRate should be populated from the throughput sample on the merged entry")
}

// deploymentWithReady builds a minimal Deployment accessor with the given
// ReadyReplicas count — sufficient for GetStatusReadyReplicas() in tests.
func deploymentWithReady(name string, ready int32) scaletarget.ScaleTargetAccessor {
	return scaletarget.NewDeploymentAccessor(&appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{Name: name, Namespace: attribTestNS},
		Status:     appsv1.DeploymentStatus{ReadyReplicas: ready},
	})
}

// vaWithDeployment builds a minimal VariantAutoscaling pointing at the named
// Deployment in attribTestNS.
func vaWithDeployment(vaName, deployName string) *llmdVariantAutoscalingV1alpha1.VariantAutoscaling {
	return &llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		ObjectMeta: metav1.ObjectMeta{Name: vaName, Namespace: attribTestNS},
		Spec: llmdVariantAutoscalingV1alpha1.VariantAutoscalingSpec{
			ScaleTargetRef: autoscalingv2.CrossVersionObjectReference{Kind: "Deployment", Name: deployName},
			ModelID:        "test-model",
		},
	}
}

// TestCollectReplicaMetrics_UnattributedReadyPods verifies the R2 warning path:
// when a VA has Ready pods but none are attributed to it this cycle (while
// another VA did get attributed replicas), a K8s Warning Event with reason
// UnattributedReadyPods is emitted for the unattributed VA and not for the
// attributed one.
func TestCollectReplicaMetrics_UnattributedReadyPods(t *testing.T) {
	const (
		ns          = attribTestNS
		vaAName     = "va-a"
		vaBName     = "va-b"
		deployAName = "deploy-a"
		deployBName = "deploy-b"
	)

	registry := prometheus.NewRegistry()
	require.NoError(t, metrics.InitMetrics(registry))

	// VA-A has a ready pod that IS attributed (pod-a labeled with va-a).
	// VA-B has a ready pod that is NOT attributed (no pod carries va-b label).
	vaA := vaWithDeployment(vaAName, deployAName)
	vaB := vaWithDeployment(vaBName, deployBName)

	variantAutoscalings := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		utils.GetNamespacedKey(ns, vaAName): vaA,
		utils.GetNamespacedKey(ns, vaBName): vaB,
	}
	scaleTargets := map[string]scaletarget.ScaleTargetAccessor{
		utils.GetNamespacedKey(ns, deployAName): deploymentWithReady(deployAName, 1),
		utils.GetNamespacedKey(ns, deployBName): deploymentWithReady(deployBName, 1),
	}

	// Source returns a KV-cache sample attributed to VA-A only.
	attributor, k8sClient := attributorWithPods(t, labeledPod("pod-a", vaAName))
	mockSource := &mockMetricsSource{
		refreshFunc: func(_ context.Context, _ source.RefreshSpec) (map[string]*source.MetricResult, error) {
			return map[string]*source.MetricResult{
				registration.QueryKvCacheUsage: {
					Values: []source.MetricValue{
						{
							Labels:    map[string]string{"pod": "pod-a", "instance": "10.0.0.1:8000"},
							Value:     0.5,
							Timestamp: time.Now(),
						},
					},
				},
			}, nil
		},
	}

	fakeRecorder := record.NewFakeRecorder(10)
	collector := NewReplicaMetricsCollector(mockSource, k8sClient, fakeRecorder)

	results, err := collector.CollectReplicaMetrics(
		context.Background(), "test-model", ns,
		scaleTargets, variantAutoscalings, make(map[string]bool),
		make(map[string]float64), attributor,
	)
	require.NoError(t, err)
	require.NotEmpty(t, results, "expected at least one attributed replica")

	// Drain the event channel and look for UnattributedReadyPods events.
	var gotEvents []string
	for {
		select {
		case e := <-fakeRecorder.Events:
			gotEvents = append(gotEvents, e)
		default:
			goto done
		}
	}
done:

	var unattribEvents []string
	for _, e := range gotEvents {
		if strings.Contains(e, constants.K8SEventUnattributedReadyPods) {
			unattribEvents = append(unattribEvents, e)
		}
	}
	require.Len(t, unattribEvents, 1, "expected exactly one UnattributedReadyPods event (for VA-B)")
	assert.Contains(t, unattribEvents[0], vaBName, "event should name VA-B")
	for _, e := range gotEvents {
		if strings.Contains(e, constants.K8SEventUnattributedReadyPods) {
			assert.NotContains(t, e, vaAName, "no UnattributedReadyPods event expected for attributed VA-A")
		}
	}
}

// TestCollectReplicaMetrics_UnattributedReadyPods_Negatives covers the two
// gate conditions that suppress the event.
func TestCollectReplicaMetrics_UnattributedReadyPods_Negatives(t *testing.T) {
	const (
		ns          = attribTestNS
		vaBName     = "va-b"
		deployBName = "deploy-b"
	)

	vaB := vaWithDeployment(vaBName, deployBName)
	variantAutoscalings := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
		utils.GetNamespacedKey(ns, vaBName): vaB,
	}

	t.Run("ready==0, no event", func(t *testing.T) {
		registry := prometheus.NewRegistry()
		require.NoError(t, metrics.InitMetrics(registry))

		// VA-A attributed so len(replicaMetrics)>0, but VA-B has ready=0.
		vaA := vaWithDeployment("va-a", "deploy-a")
		vas := map[string]*llmdVariantAutoscalingV1alpha1.VariantAutoscaling{
			utils.GetNamespacedKey(ns, "va-a"):  vaA,
			utils.GetNamespacedKey(ns, vaBName): vaB,
		}
		sts := map[string]scaletarget.ScaleTargetAccessor{
			utils.GetNamespacedKey(ns, "deploy-a"):  deploymentWithReady("deploy-a", 1),
			utils.GetNamespacedKey(ns, deployBName): deploymentWithReady(deployBName, 0), // ready=0
		}
		attributor, k8sClient := attributorWithPods(t, labeledPod("pod-a", "va-a"))
		mockSource := &mockMetricsSource{
			refreshFunc: func(_ context.Context, _ source.RefreshSpec) (map[string]*source.MetricResult, error) {
				return map[string]*source.MetricResult{
					registration.QueryKvCacheUsage: {Values: []source.MetricValue{
						{Labels: map[string]string{"pod": "pod-a", "instance": "10.0.0.1:8000"}, Value: 0.5, Timestamp: time.Now()},
					}},
				}, nil
			},
		}
		fakeRecorder := record.NewFakeRecorder(10)
		col := NewReplicaMetricsCollector(mockSource, k8sClient, fakeRecorder)
		_, err := col.CollectReplicaMetrics(context.Background(), "test-model", ns,
			sts, vas, make(map[string]bool), make(map[string]float64), attributor)
		require.NoError(t, err)
		select {
		case e := <-fakeRecorder.Events:
			assert.NotContains(t, e, constants.K8SEventUnattributedReadyPods,
				"ready=0 must not emit UnattributedReadyPods")
		default:
		}
	})

	t.Run("model-wide no metrics, no event", func(t *testing.T) {
		registry := prometheus.NewRegistry()
		require.NoError(t, metrics.InitMetrics(registry))

		sts := map[string]scaletarget.ScaleTargetAccessor{
			utils.GetNamespacedKey(ns, deployBName): deploymentWithReady(deployBName, 2),
		}
		attributor, k8sClient := attributorWithPods(t) // no pods → no attributions
		mockSource := &mockMetricsSource{
			refreshFunc: func(_ context.Context, _ source.RefreshSpec) (map[string]*source.MetricResult, error) {
				return make(map[string]*source.MetricResult), nil // empty → len==0
			},
		}
		fakeRecorder := record.NewFakeRecorder(10)
		col := NewReplicaMetricsCollector(mockSource, k8sClient, fakeRecorder)
		_, err := col.CollectReplicaMetrics(context.Background(), "test-model", ns,
			sts, variantAutoscalings, make(map[string]bool), make(map[string]float64), attributor)
		require.NoError(t, err)
		select {
		case e := <-fakeRecorder.Events:
			assert.NotContains(t, e, constants.K8SEventUnattributedReadyPods,
				"model-wide empty metrics must not emit UnattributedReadyPods")
		default:
		}
	})
}
