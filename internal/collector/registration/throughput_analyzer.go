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

// Package registration provides query registration for all analyzers.
package registration

import "github.com/llm-d/llm-d-workload-variant-autoscaler/internal/collector/source"

// Query name constants for the Throughput Analyzer.
const (
	// QueryRunningRequests is the number of requests currently being processed
	// (in-flight) on a pod. Used by the Throughput Analyzer as a direct N(v)
	// estimate, falling back to Little's Law when unavailable.
	// Source: vllm:num_requests_running
	QueryRunningRequests = "running_requests"
)

// RegisterThroughputAnalyzerQueries registers queries used by the Throughput Analyzer.
// Must be called from NewEngine() alongside the other Register*Queries calls.
func RegisterThroughputAnalyzerQueries(sourceRegistry *source.SourceRegistry) {
	registry := sourceRegistry.Get("prometheus").QueryList()

	// In-flight (running) requests per pod — direct N(v) without Little's Law.
	// Uses max to deduplicate when multiple series exist per pod.
	registry.MustRegister(source.QueryTemplate{
		Name:        QueryRunningRequests,
		Type:        source.QueryTypePromQL,
		Template:    `max by (pod) (vllm:num_requests_running{namespace="{{.namespace}}",model_name="{{.modelID}}"})`,
		Params:      []string{source.ParamNamespace, source.ParamModelID},
		Description: "Current in-flight requests per pod (direct N(v) estimate for Throughput Analyzer)",
	})
}
