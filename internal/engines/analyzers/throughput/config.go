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

package throughput

// AnalyzerName is the canonical name for the Throughput Analyzer.
const AnalyzerName = "throughput"

// Default configuration values.
const (
	// DefaultEMAAlpha is the exponential moving average smoothing factor
	// for per-variant E2E latency and hit-rate observations.
	DefaultEMAAlpha = 0.3

	// DefaultHysteresisThreshold is the minimum relative change in
	// recommended replicas before a scaling action is emitted.
	// 0.1 means the recommended replica count must differ from the current
	// count by more than 10 % before a delta is returned.
	DefaultHysteresisThreshold = 0.1

	// DefaultMaxDelta caps the number of replicas added or removed per cycle.
	DefaultMaxDelta = 5

	// DefaultMinE2E is the minimum E2E latency (seconds) used as a guard
	// against near-zero denominators.
	DefaultMinE2E = 1e-3

	// DefaultMinSupply is the minimum per-variant supply signal used as a
	// guard against near-zero denominators.
	DefaultMinSupply = 1e-6
)

// WorkloadBin describes one workload category characterised by its
// representative input-length (IL) and output-length (OL) in tokens.
// The Throughput Analyzer uses bins to compute per-workload-type KV cost and
// latency estimates.
type WorkloadBin struct {
	// Name is a human-readable identifier (e.g. "short", "medium", "long").
	Name string `yaml:"name"`

	// IL is the representative input-token count for this bin.
	IL float64 `yaml:"il"`

	// OL is the representative output-token count for this bin.
	OL float64 `yaml:"ol"`
}

// Config holds configuration for the Throughput Analyzer.
// It implements interfaces.AnalyzerConfig.
type Config struct {
	// WorkloadBins defines the workload categories used to decompose
	// per-variant load into per-(workload,variant) demand/supply pairs.
	// When empty the analyzer falls back to a single bin that uses the
	// variant's own observed (avgIL, avgOL) averages (no decomposition).
	WorkloadBins []WorkloadBin `yaml:"workloadBins,omitempty"`

	// EMAAlpha is the smoothing factor for the exponential moving average
	// applied to per-variant E2E latency and H% estimates.
	// Must be in (0, 1]. Default: DefaultEMAAlpha.
	EMAAlpha float64 `yaml:"emaAlpha,omitempty"`

	// HysteresisThreshold suppresses small scaling deltas.
	// A raw delta whose absolute value is <= HysteresisThreshold × currentReplicas
	// is clamped to zero.
	// Default: DefaultHysteresisThreshold.
	HysteresisThreshold float64 `yaml:"hysteresisThreshold,omitempty"`

	// MaxDelta caps the per-cycle replica change in either direction.
	// 0 means no cap. Default: DefaultMaxDelta.
	MaxDelta int `yaml:"maxDelta,omitempty"`

	// ScaleUpThreshold is the D/S ratio above which scale-out is signalled
	// (RequiredCapacity > 0).  Default: 0.85.
	ScaleUpThreshold float64 `yaml:"scaleUpThreshold,omitempty"`

	// ScaleDownBoundary is the D/S ratio below which scale-in is safe
	// (SpareCapacity > 0).  Default: 0.70.
	ScaleDownBoundary float64 `yaml:"scaleDownBoundary,omitempty"`
}

// GetAnalyzerName implements interfaces.AnalyzerConfig.
func (c *Config) GetAnalyzerName() string {
	return AnalyzerName
}

// WithDefaults returns a copy of c with zero-valued fields replaced by
// their defaults.
func (c Config) WithDefaults() Config {
	if c.EMAAlpha <= 0 || c.EMAAlpha > 1 {
		c.EMAAlpha = DefaultEMAAlpha
	}
	if c.HysteresisThreshold < 0 {
		c.HysteresisThreshold = 0
	}
	if c.HysteresisThreshold == 0 {
		c.HysteresisThreshold = DefaultHysteresisThreshold
	}
	if c.MaxDelta == 0 {
		c.MaxDelta = DefaultMaxDelta
	}
	if c.ScaleUpThreshold == 0 {
		c.ScaleUpThreshold = 0.85
	}
	if c.ScaleDownBoundary == 0 {
		c.ScaleDownBoundary = 0.70
	}
	return c
}
