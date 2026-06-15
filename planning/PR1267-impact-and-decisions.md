# #1267 impact on collector attribution + decisions (for the #1250 rebase)

**Type:** reference / coordination note · **Date:** 2026-06-15 · **Status:** FINAL

Input for the agent planning the #1250 (TA3) rebase onto `upstream/main`. Captures
what #1267 changed in the collector, the decisions taken in the
collector-va-attribution discussion, and exactly how TA3's A1 fix must be
replayed onto the new base.

---

## New base: `upstream/main` now has three PRs on top of `526ce851`

- `c55906a4` **#1267** — `feat(locator): make llm-d.ai/variant optional via ownerReference walk`
- `4bbb15fa` **#1270** — VA deprecation phase 2 (CRD marker, reconciler warning, samples, migration guide)
- `04f95779` **#1271** — default to V2 token-based saturation analyzer

Only **#1267** overlaps the collector/attribution path. #1270 (VA controller / api
types / samples) and #1271 (config templates / configmap_reconciler_test /
suite_test) do not touch the collector — but the rebase agent should still run its
own per-file inventory, since TA3 touches e2e suite + configmap areas that #1271
brushes.

## What #1267 did to the collector (the collision surface)

1. **`buildInstanceKey` is now a method, not a closure.** On `526ce851` it was a
   local closure `func(labels) (instanceKey, podName, vaName string)` reading the
   `llm_d_ai_variant` label. #1267 promoted it to
   `func (c *ReplicaMetricsCollector) buildInstanceKey(ctx, namespace, labels) (instanceKey, podName, vaName string)`:
   - reads `llm_d_ai_variant` as the **fast path**;
   - when empty *and* a pod label is present, falls back to
     `c.locator.Locate(ctx, ns, podName)` → managed HPA/ScaledObject, `vaName = scaler.Name`.
   - All 8 standard call sites changed to `c.buildInstanceKey(ctx, namespace, value.Labels)`.
2. **`NewReplicaMetricsCollector` gained a `podLocator locator.PodLocator` param.**
3. **The label is KEPT in all 11 queries** (registration/*.go untouched by #1267).
   It is now "optional for Deployment/LWS (owner-walk resolves), **required for
   shadow pods**" — shadow-pod attribution rides entirely on the retained metric
   label (the collector does not call `LocateByVariant`).
4. New packages: `internal/collector/locator/` (PodLocator: owner-walk + LRU cache)
   and `internal/controller/indexers/` (HPA/SO/VA field indexes). Engine
   (`NewEngine`) threads `mgr.GetAPIReader()` and constructs the locator;
   `cmd/main.go` registers indexers + `locator.SetKEDAEnabled`.
5. **The 3 throughput loops were NOT touched by #1267** — `generationTokenRate`,
   `kvUsageInstant`, `vllmRequestRate` still key `podData[podName]` by bare pod
   name (`replica_metrics.go` ~L646/667/688 on the new main), and the 3 throughput
   queries still `sum/max by (pod, llm_d_ai_variant)` with **no `instance`**. The
   A1 key-mismatch is therefore **still latent on the new main**.

## Decisions taken (collector-va-attribution discussion)

- **#1275 (`collector-va-attribution`) is dropped / closed.** Its core (Attributor
  seam + dropping the label from queries + pod-object label read) is **superseded
  by #1267**. Forcing the label-drop onto #1267 would kill the fast path **and
  regress shadow-pod attribution** (which depends on the retained metric label).
- **#1263 is closed** — its premise ("remove `llm_d_ai_variant` from groupbys") is
  resolved differently by #1267 (label made optional via owner-walk, retained for
  shadow pods).
- **The A1 throughput fix is delivered by #1250**, which already carries it (queries
  + loops + `ThroughputKeyMerge` test), in the label-retained form that composes
  with #1267.

## How TA3's A1 fix must be replayed onto #1267's main

TA3 currently (base `526ce851`) has `buildInstanceKey` as the **3-return closure**
and the A1 fix built on it. After rebasing onto #1267's main, the closure no longer
exists — it is a method. So the A1 fix must be re-expressed on the method form:

1. Keep #1267's method `c.buildInstanceKey(ctx, namespace, labels)` and its
   label-fast-path + locator fallback **as-is** — do not reintroduce the closure.
2. **Add `instance`** to the 3 throughput queries in `throughput_analyzer.go`
   (`sum/max by (pod, llm_d_ai_variant)` → `sum/max by (instance, pod, llm_d_ai_variant)`).
   This composes cleanly (#1267 didn't touch registration). Keep the label.
3. **Re-key the 3 throughput loops** to call `c.buildInstanceKey(ctx, namespace, value.Labels)`
   and store under `podData[instanceKey]` instead of `podData[podName]` (mirror how
   #1267 converted the other 8 call sites).
4. **Re-adapt `TestCollectReplicaMetrics_ThroughputKeyMerge`** to the #1267 collector
   signature — `NewReplicaMetricsCollector(source, k8sClient, recorder, podLocator)`
   (pass `nil` locator; the metric label supplies vaName in the test).
5. Behavior-preservation check (conventions): after rebase, diff TA3's
   `replica_metrics.go` against the pre-rebase tip and confirm the KV+throughput
   merge still holds (one `ReplicaMetrics` entry with both `KvCacheUsage` and
   `GenerationTokenRate`), and that the `ThroughputKeyMerge` test passes.

## UnattributedReadyPods event (orphan from #1275) — recommended home: #1250

#1275's only non-superseded, non-redundant piece is a per-VA K8s Warning event
`UnattributedReadyPods` (fired when a scale target has Ready pods but none are
attributed this cycle; scrape-lag-gated; deduped per cycle via `vaEventTracker`).
It lives in the `CollectReplicaMetrics` wrapper in `replica_metrics.go`.

- **Not #1266** — that PR is optimizer/pipeline layer (`engines/saturation/`), no
  collector files; wrong layer for a collector event.
- **Recommended: fold into the #1250 rebase** — same file, same layer, and the
  rebase already reworks `CollectReplicaMetrics`. Mechanism-agnostic: under #1267,
  "attributed" comes from the label/locator; the "ready but unattributed" signal is
  still valid. Reference implementation (from #1275, commit history on
  `collector-va-attribution`): `K8SEventUnattributedReadyPods` constant +
  `recordUnattributedReadyPodsEvent` helper + gated check
  (`len(replicaMetrics) > 0 && GetStatusReadyReplicas() > 0 && attributed == 0`).
- Fallback if it would delay #1250: file a standalone follow-up issue.
