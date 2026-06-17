from: wva-saturation-cycle-log
session: post-rebase-r2

## What changed
Rebased wva-saturation-cycle-log onto upstream/main@6d25b134 (#1266 multi-analyzer-addendum merged). Rebase clean — #1266 changes (effectiveEnabled helper in engine_v2.go, saturationV2Analyzer field type change in engine.go) were in non-overlapping regions from our logDecisionSummary addition. All gates green.

New tip: e92e26ba
Base: 6d25b134

## Update CURRENT.md
Update PR Status row for wva-saturation-cycle-log:
- tip: e92e26ba (was 52a3f797)
- base: upstream/main@6d25b134
- status: awaiting Dean push → CI → PR
