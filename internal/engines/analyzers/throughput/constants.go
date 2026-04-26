package throughput

import "time"

const (
	// AnalyzerName is the canonical name for the throughput analyzer.
	AnalyzerName = "throughput"

	// DefaultShapeChangeTolerance is the fractional change in IL or OL that
	// triggers a shape bucket change, clearing the observation window and
	// scheduling a new ITL model fit.
	// A value of 0.20 means a 20% shift in either dimension resets calibration.
	DefaultShapeChangeTolerance = 0.20

	// DefaultWindowMaxSize is the maximum number of (k, ITL) observations
	// retained in the rolling window. When the window is full, the oldest
	// observation is evicted on each new Add call.
	DefaultWindowMaxSize = 20

	// DefaultObservationMaxAge is the maximum age of an observation in the
	// window. Observations older than this are pruned regardless of window
	// fullness, ensuring that stale data from a previous load pattern does
	// not contaminate the current fit.
	DefaultObservationMaxAge = 30 * time.Minute

	// DefaultMinSamples is the minimum number of valid observations required
	// before the window is considered Ready for OLS fitting.
	DefaultMinSamples = 10

	// DefaultMinKSpread is the minimum required spread (max_k - min_k) across
	// observations in the window before the window is considered Ready.
	// A spread of at least 0.30 ensures the linear fit spans a meaningful
	// portion of the KV utilization range and is not extrapolating from a
	// single operating point.
	DefaultMinKSpread = 0.30

	// DefaultMinObservableK is the lower bound on KV utilization for accepted
	// observations. Below this threshold the ITL signal is noisy (few
	// concurrent requests, high variance) and unreliable for fitting.
	DefaultMinObservableK = 0.15

	// DefaultMaxObservableK is the upper bound on KV utilization for accepted
	// observations. Above this threshold the system approaches saturation and
	// the linear ITL model may no longer hold.
	DefaultMaxObservableK = 0.85

	// DefaultMinTokensPerRequest is the minimum plausible value for AvgOutputTokens
	// or AvgInputTokens. Values at or below this threshold indicate the metric
	// is unavailable or zero-padded and are flagged as a sanity issue.
	DefaultMinTokensPerRequest = 1.0

	// DefaultKSat is the KV utilization fraction at which per-replica capacity is
	// evaluated. Mirrors DefaultScaleUpThreshold in saturation config so that the
	// throughput analyzer and saturation analyzer agree on the definition of "full".
	// TODO: unify with the system-wide k_sat used by the EPP and saturation analyzer.
	DefaultKSat = 0.85

	// DefaultBaselineITLSec is the hardware baseline inter-token latency (seconds/token)
	// used in tier-2 estimation when the OLS window is not yet ready.
	// Derived from H100 SXM5 measurements at near-zero KV load; workload-independent.
	DefaultBaselineITLSec = 0.006

	// DefaultQueueDrainFactor controls how aggressively queued requests count as
	// decode demand. The assumed drain time is QueueDrainFactor × ITL(k_sat) × avgOL;
	// after avgOL cancels, queue demand = QueueSize / (QueueDrainFactor × ITL(k_sat)).
	// A factor of 2.0 bounds per-request queueing time to ≤ 2 × ITL(k_sat) × avgOL.
	DefaultQueueDrainFactor = 2.0
)
