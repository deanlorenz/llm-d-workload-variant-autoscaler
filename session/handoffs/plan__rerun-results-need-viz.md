from: plan (pokprod/benchmark-execution scope)
to: plan (autoscaling-viz scope)
session: viz-panels

Six new benchmark runs since the 2026-08-10 campaign have no `viz/` output — the extractor/render
toolchain hasn't touched any of them. Listed with real result numbers (no figures) in
[`ta-pokprod-rerun-results-20260813.md`](../../planning/ta-pokprod-rerun-results-20260813.md):

- `dean-20260812-152105-714` (m-ta-prefill-knee)
- `dean-20260812-203217-894` (m-ta-calibration-probe, OOM'd attempt)
- `dean-20260812-231722-822` (m-ta-calibration-probe, clean retry)
- `dean-20260813-000928-609` (m-ta-dwell rerun)
- `dean-20260813-005321-943` (m-satta-dwell rerun)
- `dean-20260813-013728-756` (m-sat-dwell rerun)
- `dean-20260813-130251-004` (m-ta-calibration-probe-p4, parallelism-4 validation)

Flagging as a data point for this scope's own backlog — not asking for immediate action, and not
mine to run myself (toolchain invocation is this scope's, per the boundary Dean confirmed
2026-08-13). Whenever convenient to fold into the existing render/panel work already in flight
here.
