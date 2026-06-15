# collector-va-attribution — Move VA attribution behind a seam, decouple from the query

**Type:** 3 (task plan) · **Issue:** #1263 · **Branch:** `collector-va-attribution`
(new, off latest `main` @ `526ce851`) · **PR:** new, base `main`
**Independent of #1260 (closed) / #1267 (`feat/pod-locator`, open).** This PR must
land and function on its own; #1267's locator later plugs in behind the seam this
PR introduces, touching only the attribution package.

---

## Goal

Stop carrying `llm_d_ai_variant` in PromQL queries and stop reading it from the
metric result. Instead:

1. Per-replica queries carry **replica identity only** (`instance`, `pod`).
2. `buildInstanceKey` builds the identity key and nothing else.
3. VA attribution is resolved **once per pod**, after the query, through an
   `Attributor` interface (the seam).
4. The default `Attributor` reads the `llm-d.ai/variant` label **from the pod
   object** (bounded labeled LIST per namespace via the uncached API reader) —
   same label as today, different source. Coverage preserved; the
   ServiceMonitor relabel rule is no longer required for attribution.

The seam is the isolation: #1267 (owner-walk locator) and any future mechanism
become alternative `Attributor` implementations. Queries, the collector hot
path, and all analyzers never change for attribution again.

---

## Baseline facts (latest main `526ce851`) — verify before starting

- 11 per-replica queries carry the label:
  - `internal/collector/registration/saturation.go`: L34, L45, L68 (has extra
    `num_gpu_blocks, block_size`), L79, L90, L102 — all `max by (instance, pod, llm_d_ai_variant…)`
  - `internal/collector/registration/queueing_model.go`: L56, L69 — `max by (instance, pod, llm_d_ai_variant)`
  - `internal/collector/registration/throughput_analyzer.go`: L109, L122, L136 —
    `sum/max by (pod, llm_d_ai_variant)` **(note: no `instance`)**
- `internal/collector/replica_metrics.go`:
  - `buildInstanceKey` (≈L312) returns `(instanceKey, podName, vaName)`; reads the
    label at ≈L319.
  - 8 call sites use `buildInstanceKey`; the 3 throughput loops (≈L643, L664,
    L685) key `podData` by **bare `podName`** — latent A1 key-mismatch.
  - `podMetricData` has a `vaName` field; assembly reads `vaName := data.vaName`
    (≈L724) and skips empty vaName (≈L754).
- `CollectReplicaMetrics` signature (≈L136):
  `(ctx, modelID, namespace, scaleTargets, variantAutoscalings, vaEventTracker, variantCosts)`.
- `prepareModelData` (≈L1206) builds `scaleTargets`/`variantAutoscalings`, has a
  `k8sClient client.Client`, and calls `CollectReplicaMetrics` (≈L1255).
- `cmd/main.go` has `mgr.GetAPIReader()` available (already used ≈L378).
- Constants: `VariantLabelKey = "llm-d.ai/variant"` (pod label),
  `VariantLabelPrometheusKey = "llm_d_ai_variant"` (metric label).

> If any line number drifted, search by symbol — do not trust the numbers blindly.

---

## Step 1 — New attribution package: `internal/collector/attribution`

Create `internal/collector/attribution/attribution.go`:

```go
package attribution

// Attributor resolves a pod (namespace + name) to the VariantAutoscaling that
// owns it. Implementations are built once per optimization cycle and queried
// O(1) on the metrics assembly path.
type Attributor interface {
    VAForPod(namespace, podName string) (vaName string, ok bool)
}
```

Default implementation — label read from the pod object:

```go
// labelAttributor resolves via the llm-d.ai/variant label stamped on the pod.
type labelAttributor struct {
    byPod map[string]string // "<ns>/<pod>" -> VA name
}

func (a labelAttributor) VAForPod(ns, pod string) (string, bool) {
    if a.byPod == nil {
        return "", false
    }
    v, ok := a.byPod[ns+"/"+pod]
    return v, ok
}

// BuildLabelAttributor lists pods carrying the variant label — one bounded
// labeled LIST per namespace via the uncached reader — and maps them to their
// VA name. reader should be mgr.GetAPIReader() so no Pod informer is started.
func BuildLabelAttributor(ctx context.Context, reader client.Reader, namespaces []string) Attributor {
    logger := ctrl.LoggerFrom(ctx)
    byPod := make(map[string]string)
    for _, ns := range namespaces {
        pods := &corev1.PodList{}
        if err := reader.List(ctx, pods,
            client.InNamespace(ns),
            client.HasLabels{constants.VariantLabelKey},
        ); err != nil {
            logger.V(logging.DEBUG).Info("attribution: failed to list variant-labeled pods",
                "namespace", ns, "error", err)
            continue
        }
        for i := range pods.Items {
            p := &pods.Items[i]
            if v := p.Labels[constants.VariantLabelKey]; v != "" {
                byPod[p.Namespace+"/"+p.Name] = v
            }
        }
    }
    return labelAttributor{byPod: byPod}
}
```

Notes for the coder:
- `client.HasLabels` is a real controller-runtime ListOption (selects objects
  having the key, any value).
- Keep the package free of any podMap/locator concept — those are future
  implementations that will live alongside this one.

## Step 2 — Drop `llm_d_ai_variant` from all 11 queries

Mechanical edits (drop the label term; for the 3 throughput queries also **add
`instance`** so they match the others):

`saturation.go` — 6 queries: `max by (instance, pod, llm_d_ai_variant[, X]) → max by (instance, pod[, X])`
(L68 keeps `num_gpu_blocks, block_size`).

`queueing_model.go` — 2 queries: same drop.

`throughput_analyzer.go` — 3 queries:
`sum by (pod, llm_d_ai_variant) → sum by (instance, pod)`,
`max by (pod, llm_d_ai_variant) → max by (instance, pod)`.

Update the comment lines above each template that mention
`llm_d_ai_variant`/"direct pod-to-VA mapping": note attribution is resolved at
the collector layer after the query, not carried in the metric labels.

Not touched: model-level queries (`scheduler_queue_*`, `model_request_count`) —
they intentionally aggregate across pods and carry no per-replica attribution.

## Step 3 — `replica_metrics.go`: identity-only key + single attribution

3a. `buildInstanceKey` → `(instanceKey, podName)`; delete the
`vaName := labels[constants.VariantLabelPrometheusKey]` line and the third return.

3b. Update the 8 existing call sites to the 2-value form; drop `vaName` from
every `podMetricData{…}` initializer.

3c. The 3 throughput loops (≈L633–L690): replace the bare-`podName` keying with
`buildInstanceKey`:
```go
instanceKey, podName := buildInstanceKey(value.Labels)
if instanceKey == "" { continue }
if podData[instanceKey] == nil { podData[instanceKey] = &podMetricData{podName: podName} }
podData[instanceKey].generationTokenRate = value.Value   // / kvUsageInstant / vllmRequestRate
```

3d. Remove the `vaName` field from `podMetricData`.

3e. Thread an `attribution.Attributor` through:
- `collectReplicaMetrics(...)` gains a trailing `attributor attribution.Attributor` param.
- `CollectReplicaMetrics(...)` gains the same param and passes it down.
- In the assembly loop, replace `vaName := data.vaName` with:
  ```go
  vaName := ""
  if attributor != nil {
      if v, ok := attributor.VAForPod(namespace, data.podName); ok { vaName = v }
  }
  ```
  Keep the existing empty-vaName skip + log unchanged. (No new metrics here —
  the unavailable-vs-zero work is #1264; the miss counter is #1260/#1267 turf.)

## Step 4 — Engine wiring + APIReader

4a. `internal/engines/saturation/engine.go`: add an exported field
```go
// APIReader is an uncached reader (mgr.GetAPIReader()) used for the per-cycle
// variant-label pod LIST in attribution, so it starts no Pod informer/cache.
// Falls back to the cached client when nil (unit tests).
APIReader client.Reader
```

4b. In `prepareModelData` (≈L1206), before the `CollectReplicaMetrics` call,
build the attributor and pass it:
```go
var reader client.Reader = k8sClient
if e.APIReader != nil { reader = e.APIReader }
attributor := attribution.BuildLabelAttributor(ctx, reader, []string{namespace})
…
replicaMetrics, err := e.ReplicaMetricsCollector.CollectReplicaMetrics(
    ctx, modelID, namespace, scaleTargets, variantAutoscalings, e.vaEventTracker, variantCosts, attributor)
```
(`prepareModelData` is per-model; the labeled LIST is per-namespace. Acceptable;
if two models share a namespace this re-lists. Optional optimization noted below
— do not implement now.)

4c. `cmd/main.go`: set `engine.APIReader = mgr.GetAPIReader()` where the engine
is constructed (mirror how the configmap reconciler already takes
`mgr.GetAPIReader()`).

## Step 5 — RBAC

The labeled pod LIST needs `pods` `list` permission. Confirm the manager
ClusterRole already grants it (`make manifests` should produce no diff). If a
marker is missing, add `+kubebuilder:rbac:groups="",resources=pods,verbs=list`
and regenerate. Record the result.

## Step 6 — Tests

- `attribution/attribution_test.go`: fake client with labeled + unlabeled pods;
  assert `VAForPod` resolves labeled pods, returns `ok=false` for unlabeled, and
  a nil/empty Attributor is safe.
- `replica_metrics_test.go`: update call sites to the new `CollectReplicaMetrics`
  signature (pass a built attributor or `nil`). The existing
  "label absent → pod skipped" semantics now means "no metric label is normal;
  attribution comes from the attributor" — update the case + comment.
- Add a merge test: KV-cache result + generation-token-rate result for the same
  pod (matching `instance`+`pod`) now land in **one** `ReplicaMetrics` entry with
  both `KvCacheUsage > 0` and `GenerationTokenRate > 0` (was two entries, the
  throughput one dropped). This is the A1 regression guard.
- A test that a pod with no metric variant label but present in the attributor
  gets `VariantName` set in the output.

## Semantic-pivot cross-reference check

`buildInstanceKey` changes its return arity and `podMetricData` loses a field;
the metric label is no longer read in the collector. After implementing, run:
```
grep -rn "VariantLabelPrometheusKey" internal/ cmd/
grep -rn "data.vaName\|\.vaName" internal/collector/
grep -rn "llm_d_ai_variant" internal/collector/registration/
```
Update every stale hit (comments/docstrings included). The only remaining
`VariantLabelPrometheusKey` use after this PR should be the constant definition
itself (keep it — the relabel rule and metric label still exist for
back-compat); confirm nothing in the collector still reads it.

## Pre-push checklist

1. `git branch --show-current` → `collector-va-attribution`
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` → empty
3. `make test` → all pass
4. `make lint` → clean (the new package + signature change must pass nakedret/unparam/gocritic)
5. `go build ./...` → clean
6. `make manifests` → no diff (or RBAC marker added intentionally, Step 5)
7. DCO on every commit: `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`

## Developer-guide (Type 4) update

Update `docs/developer-guide/` (the pod-scraping / metrics-collection doc, or
add a short section): per-replica queries select by `{namespace, model_name}`
and group by `(instance, pod)`; VA attribution is a separate collector step via
the `Attributor` seam; the default reads `llm-d.ai/variant` from the pod object
(ServiceMonitor relabel rule no longer required for attribution). Reflect code
state only — no "pending #1267" forward references.

## Out of scope (do not implement)

- The owner-walk locator (#1267) and any podMap — they are future `Attributor`
  implementations behind this seam.
- Unavailable-vs-zero `*float64` semantics → #1264.
- Per-pod miss metrics / status conditions.
- Hoisting the attributor build to once-per-cycle across namespaces (optimization
  noted in 4b) — leave the per-model labeled LIST.

## Coordination note (for the planner, not the coder)

This normalizes the 3 throughput queries on main and fixes their latent A1
key-mismatch. TA3/#1250 carries its own A1 fix on its branch; when #1250 rebases
onto a main containing this PR, that fix is already present — the rebase adapts
(TA3 also drops the label and uses the attributor). Flag to the #1250 owner so
they don't double-apply.
