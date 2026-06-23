from: wva-saturation-cycle-log
session: r3-thresholds-rebase-done

## What changed

Two new commits on wva-saturation-cycle-log-r1 (wva-log-rewrite), then rebased onto upstream/main@2b736049.

Tip: cc3d069f

## Commit cc3d069f — Steps 11–16

- Fixed stale comment in engine_v2_log_test.go ("label" → "reason")
- Added ScaleUpThreshold/ScaleDownBoundary fields to pipeline.NamedAnalyzerResult
- Populated those fields from satUp/satDown (sat) and up/down (registered analyzers) in runAnalyzersAndScore
- logAnalyzerResult now emits "scaleUpThreshold" and "scaleDownBoundary" after "sc"
- Test fixture gets ScaleUpThreshold:1.2/ScaleDownBoundary:0.7; required-keys list updated
- cycle-log.md: added threshold fields to table + example JSON; renamed "Capacity label values (label field)" → "Reason values (reason field)"; added P0-store row; added T1-ols/T2-pinned/T2-default TA tier reasons; removed cost from tables/example; removed stale reference to "V2 saturation analysis completed" line

## Rebase (Step 17)

Conflict in engine.go: upstream #1306 refactored optimizer selection into selectV2Optimizer().
Resolution: kept selectV2Optimizer call, kept our logScalingDecisions call after it.

Deleted "V2 saturation analysis completed" logger.Info block from engine_v2.go — superseded by logAnalyzerResult loop which now emits the same fields plus variants, reason, and thresholds.

## Update CURRENT.md

Update PR Status row for wva-saturation-cycle-log:
- tip: cc3d069f on wva-saturation-cycle-log-r1 (wva-log-rewrite)
- base: upstream/main@2b736049
- status: awaiting Dean push to origin/wva-saturation-cycle-log
