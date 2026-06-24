from: wva-saturation-cycle-log
session: redesign-rewrite-done

## What changed

Full redesign committed as a single clean commit on branch wva-saturation-cycle-log-r1
(worktree wva-log-rewrite), base upstream/main@02d06eb2.

Tip: 6474e655

Old stack on wva-saturation-cycle-log (e92e26ba, 01bfe940) is superseded and should
not be used.

## Files changed (6)
- internal/engines/analyzers/saturation_v2/types.go — K2Priority int on ReplicaCapacity
- internal/engines/analyzers/saturation_v2/analyzer.go — computeK2 (int64,int); K2Priority both paths; k2SourceLabel (sort+index, "P3-k2"); CapacityLabel in aggregateByVariant
- internal/interfaces/analyzer.go — CapacityLabel string on VariantCapacity only
- internal/engines/saturation/engine_v2.go — logAnalyzerResult + logScalingDecisions; log loop in runAnalyzersAndScore
- internal/engines/saturation/engine.go — logScalingDecisions after optimizer in optimizeV2
- internal/engines/saturation/engine_v2_log_test.go — 5 new tests

## Update CURRENT.md

Update PR Status row for wva-saturation-cycle-log:
- Branch: wva-saturation-cycle-log-r1 (worktree: wva-log-rewrite)
- Tip: 6474e655 on upstream/main@02d06eb2
- Status: awaiting Dean force-push → CI → PR #1277 update

## Action for Dean
Force-push wva-saturation-cycle-log-r1 to origin/wva-saturation-cycle-log:
  git -C wva-log-rewrite push --force-with-lease origin wva-saturation-cycle-log-r1:wva-saturation-cycle-log
