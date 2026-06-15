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

// Package attribution resolves which VariantAutoscaling owns a given pod.
//
// VA attribution is deliberately decoupled from the per-replica Prometheus
// queries: the queries carry replica identity only (instance, pod), and the
// owning VariantAutoscaling is resolved once per pod, after the query, through
// the Attributor seam. Alternative resolution mechanisms (e.g. an owner-walk
// pod locator) plug in as additional Attributor implementations without
// touching the queries, the collector hot path, or any analyzer.
package attribution

import (
	"context"
	"errors"
	"fmt"

	corev1 "k8s.io/api/core/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"

	"github.com/llm-d/llm-d-workload-variant-autoscaler/internal/constants"
)

// Attributor resolves a pod (namespace + name) to the VariantAutoscaling that
// owns it. Implementations are built once per optimization cycle and queried
// O(1) on the metrics assembly path.
type Attributor interface {
	VAForPod(namespace, podName string) (vaName string, ok bool)
}

// labelAttributor resolves via the llm-d.ai/variant label stamped on the pod.
type labelAttributor struct {
	byPod map[string]string // "<ns>/<pod>" -> VA name
}

func (a labelAttributor) VAForPod(ns, pod string) (string, bool) {
	if a.byPod == nil {
		return "", false
	}
	v, ok := a.byPod[ns+"/"+pod]
	return v, ok
}

// BuildLabelAttributor lists pods carrying the variant label — one bounded
// labeled LIST per namespace via the uncached reader — and maps them to their
// VA name. reader should be mgr.GetAPIReader() so no Pod informer is started.
//
// On a List failure it keeps the entries from namespaces that succeeded and
// returns the partial attributor together with a joined error, so the caller
// can surface the degradation (warn once per cycle) while still using whatever
// resolved. A nil error means every namespace listed cleanly.
//
// No factory for now: construction is specific to this label strategy, and a
// free constructor is sufficient while the label attributor is the only impl.
// A future second mechanism (e.g. the owner-walk locator) gets its own builder;
// if more than one ever needs to coexist behind engine config, introduce a
// builder/factory interface at that point.
func BuildLabelAttributor(ctx context.Context, reader client.Reader, namespaces []string) (Attributor, error) {
	byPod := make(map[string]string)
	var errs []error
	for _, ns := range namespaces {
		pods := &corev1.PodList{}
		if err := reader.List(ctx, pods,
			client.InNamespace(ns),
			client.HasLabels{constants.VariantLabelKey},
		); err != nil {
			errs = append(errs, fmt.Errorf("listing variant-labeled pods in namespace %q: %w", ns, err))
			continue
		}
		for i := range pods.Items {
			p := &pods.Items[i]
			if v := p.Labels[constants.VariantLabelKey]; v != "" {
				byPod[p.Namespace+"/"+p.Name] = v
			}
		}
	}
	return labelAttributor{byPod: byPod}, errors.Join(errs...)
}
