from: collector-va-attribution
session: R2 fixup applied (unattributed-ready-pods warning)

## What changed
Processed trigger `collector-va-attribution__plan-revised-r2.md` (plan gained R2 + Step 7).
Applied Step 7 in commit `59e9990d` (fixup on `85bd65de`).

Changes:
- constants.go: K8SEventUnattributedReadyPods = "UnattributedReadyPods"
- replica_metrics.go: recordUnattributedReadyPodsEvent helper + per-VA check in
  CollectReplicaMetrics (after availability block; only when len>0; deduped via
  vaEventTracker; DEBUG log per pod, Event per VA).
- replica_metrics_test.go: TestCollectReplicaMetrics_UnattributedReadyPods (positive)
  + TestCollectReplicaMetrics_UnattributedReadyPods_Negatives (ready==0 + model-wide).
- docs/design/controller-behavior.md: troubleshooting section updated.

All gates green (gofmt/test/lint/build). 3 commits total on branch.

## Update CURRENT.md
- Update collector-va-attribution entry: 3 commits (7157c7d2 + 85bd65de + 59e9990d);
  R2 fixup applied; all gates green; still "in review" / WIP.
