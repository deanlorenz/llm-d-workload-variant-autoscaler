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

package attribution

import (
	"context"
	"errors"
	"testing"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/client/interceptor"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/constants"
)

func pod(ns, name string, labels map[string]string) *corev1.Pod {
	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{Namespace: ns, Name: name, Labels: labels},
	}
}

func corev1Scheme(t *testing.T) *runtime.Scheme {
	t.Helper()
	s := runtime.NewScheme()
	if err := corev1.AddToScheme(s); err != nil {
		t.Fatalf("AddToScheme: %v", err)
	}
	return s
}

func TestBuildLabelAttributor(t *testing.T) {
	const ns = "team-a"

	c := fake.NewClientBuilder().WithScheme(corev1Scheme(t)).WithObjects(
		pod(ns, "labeled-1", map[string]string{constants.VariantLabelKey: "va-one"}),
		pod(ns, "labeled-2", map[string]string{constants.VariantLabelKey: "va-two"}),
		// Unlabeled pod: must not be attributed.
		pod(ns, "unlabeled", map[string]string{"app": "vllm"}),
		// Empty label value: treated as no attribution.
		pod(ns, "empty-label", map[string]string{constants.VariantLabelKey: ""}),
		// Different namespace: must not leak into ns's attributor.
		pod("other-ns", "elsewhere", map[string]string{constants.VariantLabelKey: "va-elsewhere"}),
	).Build()

	a, err := BuildLabelAttributor(context.Background(), c, []string{ns})
	if err != nil {
		t.Fatalf("BuildLabelAttributor: unexpected error: %v", err)
	}

	cases := []struct {
		name       string
		podName    string
		wantVAName string
		wantOK     bool
	}{
		{"labeled pod resolves", "labeled-1", "va-one", true},
		{"second labeled pod resolves", "labeled-2", "va-two", true},
		{"unlabeled pod not attributed", "unlabeled", "", false},
		{"empty label value not attributed", "empty-label", "", false},
		{"unknown pod not attributed", "ghost", "", false},
		{"pod from another namespace not attributed", "elsewhere", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			gotVA, gotOK := a.VAForPod(ns, tc.podName)
			if gotOK != tc.wantOK || gotVA != tc.wantVAName {
				t.Errorf("VAForPod(%q,%q) = (%q,%v), want (%q,%v)",
					ns, tc.podName, gotVA, gotOK, tc.wantVAName, tc.wantOK)
			}
		})
	}
}

// TestLabelAttributor_NilSafe asserts a zero-value / nil-map attributor never
// panics and always reports "not found".
func TestLabelAttributor_NilSafe(t *testing.T) {
	var a labelAttributor // byPod is nil
	if v, ok := a.VAForPod("ns", "pod"); ok || v != "" {
		t.Errorf("nil-map VAForPod = (%q,%v), want (\"\",false)", v, ok)
	}
}

// TestBuildLabelAttributor_EmptyNamespaces builds an attributor over no
// namespaces; every lookup reports "not found" without listing anything.
func TestBuildLabelAttributor_EmptyNamespaces(t *testing.T) {
	c := fake.NewClientBuilder().WithScheme(corev1Scheme(t)).Build()

	a, err := BuildLabelAttributor(context.Background(), c, nil)
	if err != nil {
		t.Fatalf("BuildLabelAttributor: unexpected error: %v", err)
	}
	if v, ok := a.VAForPod("ns", "pod"); ok || v != "" {
		t.Errorf("empty-namespaces VAForPod = (%q,%v), want (\"\",false)", v, ok)
	}
}

// TestBuildLabelAttributor_ListError verifies the partial-success contract:
// when a List fails for one namespace the builder returns a non-nil error but
// also a non-nil, query-safe (empty) Attributor so the caller can proceed.
// With multiple namespaces, entries from the namespaces that succeeded must
// still be present in the returned attributor.
func TestBuildLabelAttributor_ListError(t *testing.T) {
	t.Run("single namespace fails – error returned, attributor safe", func(t *testing.T) {
		listErr := errors.New("injected list failure")
		ic := interceptor.NewClient(
			fake.NewClientBuilder().WithScheme(corev1Scheme(t)).Build(),
			interceptor.Funcs{
				List: func(_ context.Context, _ client.WithWatch, _ client.ObjectList, _ ...client.ListOption) error {
					return listErr
				},
			},
		)

		a, err := BuildLabelAttributor(context.Background(), ic, []string{"ns-a"})
		if err == nil {
			t.Fatal("expected non-nil error, got nil")
		}
		if a == nil {
			t.Fatal("expected non-nil Attributor even on error, got nil")
		}
		// The attributor must be safe to query (no panic, returns ok=false).
		if v, ok := a.VAForPod("ns-a", "any-pod"); ok || v != "" {
			t.Errorf("VAForPod on error attributor = (%q,%v), want (\"\",false)", v, ok)
		}
	})

	t.Run("second namespace fails – first namespace entries still resolved", func(t *testing.T) {
		scheme := corev1Scheme(t)
		goodClient := fake.NewClientBuilder().WithScheme(scheme).WithObjects(
			pod("ns-good", "pod-ok", map[string]string{constants.VariantLabelKey: "va-ok"}),
		).Build()

		var callCount int
		ic := interceptor.NewClient(goodClient, interceptor.Funcs{
			List: func(ctx context.Context, c client.WithWatch, list client.ObjectList, opts ...client.ListOption) error {
				callCount++
				if callCount == 2 {
					return errors.New("injected failure on second namespace")
				}
				return c.List(ctx, list, opts...)
			},
		})

		a, err := BuildLabelAttributor(context.Background(), ic, []string{"ns-good", "ns-bad"})
		if err == nil {
			t.Fatal("expected non-nil error, got nil")
		}
		// ns-good succeeded on the first call — its pod must still resolve.
		if v, ok := a.VAForPod("ns-good", "pod-ok"); !ok || v != "va-ok" {
			t.Errorf("VAForPod(ns-good, pod-ok) = (%q,%v), want (\"va-ok\",true)", v, ok)
		}
	})
}
