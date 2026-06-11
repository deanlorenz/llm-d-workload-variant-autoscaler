# collector-va-attribution — Separate VA attribution from the metric query

**Primary path:** suggested into PR #1260 directly — the snippets are posted on
#1263 (`feat/pod-mapping-derivation`, tip `2cb75d84` as of 2026-06-11) for
ev-shindin to fold in. If accepted there, no separate coder work is needed —
but **this doc stays live as the review reference for the updated #1260**: the
three steps below are the checklist for verifying the folded-in change (queries
cleaned, `buildInstanceKey` attribution-free, override via labeled LIST, tests).

**Fallback path:** if ev-shindin prefers to keep #1260 focused, A2 lands as its
own PR on `main` **after #1260 merges**. In that case the coder's job is almost
entirely mechanical — **copy the three code blocks from the #1263 comment** into
the merged #1260 code, wire up the call-site edits, add the tests. No new design
decisions; the snippets are the spec.

Either way, the same content drives it: a review checklist on the primary path, a
coder spec on the fallback.

**Issue:** #1263 (carries the authoritative snippets)  
**Depends on:** the podMap machinery from #1260 — on its branch (primary) or on
`main` once merged (fallback).

---

## Principle

Two orthogonal concerns are currently tangled in the metric query:

1. **Replica identity** — which scrape target a metric series belongs to.
   Built from vLLM-native labels (`instance`, `pod`) only.
2. **VA attribution** — which `VariantAutoscaling` owns that replica. A
   collector-layer decision, resolved *after* the query from the podMap
   (selector-derived) and/or the `llm-d.ai/variant` label.

The query should carry only concern (1). Attribution (2) is a separate step.
The query form is then identical regardless of whether attribution comes from
the podMap, a pod label, or both — which is the whole point.

`buildInstanceKey` builds the replica-identity key and nothing else. It does
not read `llm_d_ai_variant`.

> **Selection vs. grouping (background).** Per-replica queries *select* by
> `{namespace, model_name}` (returns all pods of that model in the namespace)
> and *group* `by (instance, pod)` (one series per scrape target). `llm_d_ai_variant`
> in the `by (...)` clause never filtered anything — it only carried the label
> into the result so Go code could read it. Removing it changes nothing about
> which pods are selected; it only stops smuggling attribution through the query.

---

## Step 1 — registration: drop `llm_d_ai_variant` from per-replica `max by`

### `internal/collector/registration/saturation.go` (6 queries)

| Query | Before | After |
|---|---|---|
| `QueryKvCacheUsage` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |
| `QueryQueueLength` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |
| `QueryCacheConfigInfo` | `max by (instance, pod, llm_d_ai_variant, num_gpu_blocks, block_size)` | `max by (instance, pod, num_gpu_blocks, block_size)` |
| `QueryAvgOutputTokens` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |
| `QueryAvgInputTokens` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |
| `QueryPrefixCacheHitRate` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |

### `internal/collector/registration/queueing_model.go` (2 queries)

| Query | Before | After |
|---|---|---|
| `QueryAvgTTFT` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |
| `QueryAvgITL` | `max by (instance, pod, llm_d_ai_variant)` | `max by (instance, pod)` |

Update the comment above each template: drop the
`"llm_d_ai_variant (for direct pod-to-VA mapping)"` clause; note that VA
attribution is resolved at the collector layer after the query, not carried
in the metric labels.

**Not touched:** the three model-level queries (`QuerySchedulerQueueSize`,
`QuerySchedulerQueueBytes`, `QueryModelRequestCount`) — they intentionally
aggregate across pods and carry no per-replica attribution. (Model-level
scoping is correct for these: the EPP queue is model-level demand, distributed
across all variants of the model; the only known gap is the upstream
no-namespace-label issue tracked in #2309, out of scope here.)

**Not touched:** throughput registration (`throughput_analyzer.go`) — its key
fix is handled in PR #1250 (A1). After both land, all per-replica queries share
the `max by (instance, pod)` form.

---

## Step 2 — `replica_metrics.go`: make `buildInstanceKey` attribution-free

### 2a. `buildInstanceKey` returns `(instanceKey, podName)` only

Remove the `vaName := labels[constants.VariantLabelPrometheusKey]` read and the
third return value:

```go
// Before:
buildInstanceKey := func(labels map[string]string) (string, string, string)
// After:
buildInstanceKey := func(labels map[string]string) (string, string)
```

### 2b. Update every call site

All processing loops destructure three values today
(`instanceKey, podName, vaName := buildInstanceKey(...)` or `..., _ := ...`).
Change to two (`instanceKey, podName := buildInstanceKey(...)`). Drop `vaName`
from every `podMetricData{...}` initializer.

### 2c. Remove `vaName` from `podMetricData`

Delete the `vaName string` field. Attribution is no longer carried per metric
series.

### 2d. Single attribution step in the final assembly loop

The final assembly loop (~line 724 on the #1260 branch) currently reads
`vaName := data.vaName`. Replace with one attribution call per pod entry:

```go
vaName := attributeVA(namespace, data.podName, value-labels-if-retained, podMap)
```

Attribution precedence (preserves #1260 semantics), all resolved from the
podMap (see Step 3 — the override is captured into the podMap, not read from
the Prometheus result):
1. `llm-d.ai/variant` override if present on the pod
2. selector-derived VA otherwise

The existing `if vaName == "" { IncPodMappingMiss(...); skip }` block and the
`trackMetricFreshness(vaName, ...)` call stay where they are — they already sit
in this loop and pick up the resolved value.

### 2e. Remove the per-metric podMap fallback #1260 added inside `buildInstanceKey`

#1260 added a `vaName == "" && podMap != nil` fallback at the first call site.
After 2a–2d, attribution happens once in the assembly loop, so this inline
fallback is dead — remove it to keep a single attribution point.

---

## Step 3 — fold the `llm-d.ai/variant` override into the podMap

Once the label is out of the query result, the override (for custom kinds /
non-standard owner chains, and back-compat) must be read from the **K8s pod
object**, not the Prometheus result.

**Important:** `podvamap.Build` lists pods only via each VA's `scaleTargetRef`
**selector**. A custom-kind pod that no selector matches is never listed —
which is exactly the case the override exists for. So capturing the label off
the existing per-VA LISTs is insufficient; it would only catch pods that already
match a selector.

`Build` therefore adds **one bounded labeled LIST per namespace**
(`client.HasLabels{constants.VariantLabelKey}`) after the selector candidates
resolve into `byPod`, and writes those results into `byPod` as overrides.
The `Map` struct is unchanged — overrides land in the same `byPod` map.

```go
// after selector candidates resolve into byPod:
seenNS := make(map[string]struct{})
for _, va := range variantAutoscalings {
    if va == nil { continue }
    if _, done := seenNS[va.Namespace]; done { continue }
    seenNS[va.Namespace] = struct{}{}
    overridePods := &corev1.PodList{}
    if err := reader.List(ctx, overridePods,
        client.InNamespace(va.Namespace),
        client.HasLabels{constants.VariantLabelKey},
    ); err != nil {
        logger.V(logging.DEBUG).Info("pod-VA derivation: failed to list override-labeled pods",
            "namespace", va.Namespace, "error", err)
        continue
    }
    for i := range overridePods.Items {
        p := &overridePods.Items[i]
        if name := p.Labels[constants.VariantLabelKey]; name != "" {
            byPod[p.Namespace+"/"+p.Name] = name   // override wins
        }
    }
}
```

Attribution precedence matches #1260's current label-wins semantics: **label
override beats the selector-derived mapping**. This also drops the ServiceMonitor
relabel-rule requirement for the override path (which the metric-label approach
still needs). Cost: one labeled LIST per namespace (bounded), not zero.

---

## Step 4 — tests

- Update `build_instance_key_test.go` and `replica_metrics_test.go` call sites
  to the 2-value `buildInstanceKey` signature.
- Add a test: pod with **no** `llm_d_ai_variant` in its metric labels, resolved
  to a VA via a non-nil podMap → `ReplicaMetrics.VariantName` is set.
- The existing "label absent → pod skipped" case changes meaning: absent label
  is now the normal path, not a skip. Update the case and its comment.
- Add a podMap test asserting the captured label override wins over the
  selector-derived VA when the two differ (Step 3).

---

## Pre-push checklist

1. Confirm working on top of the #1260 branch (or main after #1260 merges).
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` → empty
3. `make test` → all pass
4. `make lint` → clean
5. `go build ./...` → clean
6. DCO on every commit: `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`

## Out of scope

- Throughput query key fix → PR #1250 (A1)
- `*float64` nil-vs-zero cleanup → issue #1264
- Scheduler-queue signal scoping → model-level scoping is correct (EPP queue is
  model-level demand); only the upstream no-namespace-label gap (#2309) remains,
  not ours to fix here
