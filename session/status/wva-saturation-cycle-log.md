last_update: 2026-06-19T00:00:00Z
state: in-progress
current_step: redesign committed (6474e655) on wva-log-rewrite/wva-saturation-cycle-log-r1; awaiting Dean push to origin/wva-saturation-cycle-log

## Branch
wva-saturation-cycle-log-r1 at ../wva-log-rewrite ; tip 6474e655
Base: upstream/main@02d06eb2

## Recent commits
- 6474e655 — engine: add structured cycle log lines (analyzer-result, scaling-decision)

## Files changed
- internal/engines/analyzers/saturation_v2/types.go — K2Priority int added to ReplicaCapacity
- internal/engines/analyzers/saturation_v2/analyzer.go — computeK2 returns (int64,int); K2Priority set in main + fallback paths; k2SourceLabel helper (sort+index, P3 label is "P3-k2"); CapacityLabel set in aggregateByVariant
- internal/interfaces/analyzer.go — CapacityLabel string added to VariantCapacity (only field change)
- internal/engines/saturation/engine_v2.go — logAnalyzerResult + logScalingDecisions helpers; log loop wired into runAnalyzersAndScore
- internal/engines/saturation/engine.go — logScalingDecisions called after optimizer in optimizeV2
- internal/engines/saturation/engine_v2_log_test.go — 5 unit tests (new file)

## Tests added
- TestLogAnalyzerResult_EmitsRequiredFields
- TestLogAnalyzerResult_NilResultSkipped
- TestLogAnalyzerResult_EmptyVariants
- TestLogScalingDecisions_EmitsPerModel
- TestLogScalingDecisions_NoDecisionsSkipsModel

## Verified
- go build ./... — clean
- make test — all pass
- gofmt — clean
- make lint — 0 issues

## What NOT in this PR (per plan)
- No SaturationVariantCapacity, no MedianK1/K2/K2SourceLabel on interfaces
- No K2Priority outside saturation_v2 package
- No optimizer-internal logging (Log B deferred)
- No derived values (eff=cost/prc) inside log helpers

## Notes
Dean should force-push wva-saturation-cycle-log-r1 to origin/wva-saturation-cycle-log to update PR #1277.
Old commits e92e26ba / 01bfe940 on the old branch are superseded.
