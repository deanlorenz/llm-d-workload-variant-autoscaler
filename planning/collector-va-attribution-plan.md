# collector-va-attribution — Move VA attribution behind a seam, decouple from the query

**Type:** 3 (task plan) · **Issue:** #1263 · **Branch:** `collector-va-attribution`
(new, off latest `main` @ `526ce851`) · **PR:** new, base `main`
**Independent of #1260 (closed) / #1267 (`feat/pod-locator`, open).** This PR must
land and function on its own; #1267's locator later plugs in behind the seam this
PR introduces, touching only the attribution package.

---

## Revision R1 — error & log handling (post-review, 2026-06-15)

v1 of this plan (implemented in commit `7157c7d2`, in review) is correct but
swallowed the attributor's pod-LIST failure at DEBUG and logged an `Info` per
unattributed pod every cycle, conflating two distinct conditions. R1 separates
them:

- **Not part of WVA** (pod carries no variant label) — normal; `VAForPod`
  returns `ok=false`; the per-pod skip logs at **DEBUG**, never per-pod-Info.
- **Attribution degraded** (the labeled LIST failed) — surfaced as an **error
  once per cycle** at the build site, not once per skipped pod.

Decisions taken (settled with Dean):

- **No factory.** `BuildLabelAttributor` stays a free constructor; it only gains
  an `error` return. A builder/factory interface is deferred until a second
  `Attributor` impl needs to coexist — captured as a **code comment**, not built.
- The query seam stays `VAForPod(ns, pod) (vaName, ok)`. The missing piece was an
  **error return on the builder**, not a change to the query interface — once
  build errors are surfaced separately, `ok=false` unambiguously means "not a WVA
  pod." (Attribution is **pod-scoped**: the `llm-d.ai/variant` label lives on the
  pod, so two vLLM instances in one pod always share a VA — keying by pod name is
  correct and the v1 "instance-only, no pod label" drop is immaterial.)

Steps 1, 3e, 4b, and 6 below are updated for R1; everything else in v1 stands.

---

## Revision R2 — "ready pods but none attributed" warning (post-review, 2026-06-15)

This PR moves attribution from the metric label to the **pod object**, so a
missing/wrong `llm-d.ai/variant` pod label now makes a VA's Ready pods invisible
to WVA — silently. R2 adds the runtime counterpart to the dev-guide
troubleshooting section: a per-VA **K8s Warning Event** when a VA has Ready pods
but none are attributed to it.

Decisions (settled with Dean):

- **Discriminator is `GetStatusReadyReplicas()`, not desired replicas** — grounds
  "not pending" in observable state: `ready == 0` ⇒ scaling in flight or
  scaled-to-zero (quiet); `ready > 0 && attributed == 0` ⇒ real pods WVA cannot
  see.
- **Scrape-lag gate:** only fire when the model produced *some* attributed
  replicas (`len(replicaMetrics) > 0`) but *this* VA got zero. Model-wide
  emptiness stays the existing `recordMetricsUnavailableEvent` path, so a normal
  scale-up scrape-lag window does not false-alarm.
- **Dedup = the existing `vaEventTracker`** (item 2, "cache the decision"): one
  Event per VA per cycle; K8s aggregates duplicate counts. The accompanying log
  stays at DEBUG to avoid per-cycle log spam — the Event is the operator-facing
  warning.
- **Not done (agreed):** per-pod cross-cycle DEBUG suppression (over-engineering
  for an off-by-default line) and attribution change-detection / a stateful-cached
  `Attributor` (backlog, tied to #1267 and the deliberate no-informer choice).

New work is **Step 7** below; Steps 6/dev-guide/out-of-scope extended for R2.

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
//
// On a List failure it keeps the entries from namespaces that succeeded and
// returns the partial attributor together with a joined error, so the caller can
// surface the degradation (warn once per cycle) while still using whatever
// resolved. A nil error means every namespace listed cleanly.
//
// No factory for now: construction is specific to this label strategy, but a
// free constructor is enough while the label attributor is the only impl. A
// future second mechanism (e.g. the owner-walk locator) gets its own builder; if
// more than one ever needs to coexist behind engine config, introduce a
// builder/factory interface at that point.
func BuildLabelAttributor(ctx context.Context, reader client.Reader, namespaces []string) (Attributor, error) {
    byPod := make(map[string]string)
    var errs []error
    for _, ns := range namespaces {
        pods := &corev1.PodList{}
        if err := reader.List(ctx, pods,
            client.InNamespace(ns),
            client.HasLabels{constants.VariantLabelKey},
        ); err != nil {
            errs = append(errs, fmt.Errorf("listing variant-labeled pods in namespace %q: %w", ns, err))
            continue
        }
        for i := range pods.Items {
            p := &pods.Items[i]
            if v := p.Labels[constants.VariantLabelKey]; v != "" {
                byPod[p.Namespace+"/"+p.Name] = v
            }
        }
    }
    return labelAttributor{byPod: byPod}, errors.Join(errs...)
}
```

Notes for the coder:
- `client.HasLabels` is a real controller-runtime ListOption (selects objects
  having the key, any value).
- Keep the package free of any podMap/locator concept — those are future
  implementations that will live alongside this one.
- **(R1) Imports:** the builder no longer logs, so drop `ctrl`
  (`sigs.k8s.io/controller-runtime`) and `internal/logging` from the package;
  add `errors` and `fmt`. `ctx` stays used (it is still passed to `reader.List`),
  so it is not an unused param — no lint concern.
- **(R1)** A nil/empty `labelAttributor` is still valid and `VAForPod`-safe, so
  callers may use the returned attributor even when the error is non-nil.

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
  **(R1)** Lower the existing empty-vaName skip log from `logger.Info` to
  `logger.V(logging.DEBUG).Info` and reword it — with build errors surfaced
  separately (Step 4b), `vaName == ""` here means "pod is not managed by any
  VariantAutoscaling," a normal condition that must not log per-pod every cycle:
  ```go
  if vaName == "" {
      logger.V(logging.DEBUG).Info("Skipping pod with no variant attribution (not managed by any VariantAutoscaling)",
          "pod", podName,
          "instance", instanceKey,
          "scale targets", getScaleTargetNames(scaleTargets))
      continue
  }
  ```
  Keep the `scale targets` field — it keeps `getScaleTargetNames` in use (its
  only caller) and is useful debug context. No new metrics here — the
  unavailable-vs-zero work is #1264; the miss counter is #1267 turf.

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
attributor, err := attribution.BuildLabelAttributor(ctx, reader, []string{namespace})
if err != nil {
    // Attribution is degraded this cycle: pods we cannot resolve are skipped
    // downstream, so no scaling decisions are made for them. Surface once per
    // cycle here rather than once per skipped pod.
    logger.Error(err, "VA attribution degraded: failed to list variant-labeled pods; affected pods will be skipped this cycle",
        "namespace", namespace)
}
// Proceed even on error: BuildLabelAttributor returns a usable (possibly empty
// or partial) attributor, and the downstream empty-vaName skip handles the
// unresolved pods. Do not abort the model's data prep on attribution failure.
…
replicaMetrics, err := e.ReplicaMetricsCollector.CollectReplicaMetrics(
    ctx, modelID, namespace, scaleTargets, variantAutoscalings, e.vaEventTracker, variantCosts, attributor)
```
(`prepareModelData` is per-model; the labeled LIST is per-namespace. Acceptable;
if two models share a namespace this re-lists — and on failure logs the error
once per model, not once per pod. **(R1)** `attributor, err :=` introduces `err`;
the later `replicaMetrics, err :=` reuses it (each `:=` has a new LHS var, so it
compiles; CollectReplicaMetrics' own error path is unchanged). True
edge-triggered dedup of the degraded-attribution warning, and the cross-namespace
hoist noted below, are future niceties — do not implement now.)

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
- **(R1)** `BuildLabelAttributor` now returns `(Attributor, error)`. Update the
  `attributorWithPods` test helper in `build_instance_key_test.go` and any other
  call site to consume the 2-value return (`a, err := …; if err != nil { t.Fatalf }`),
  then return `a`.
- **(R1)** Add a builder-error case in `attribution_test.go`: force the reader's
  `List` to fail (controller-runtime fake client with
  `interceptor.Funcs{List: func(...) error { return … }}`), assert
  `BuildLabelAttributor` returns a non-nil error **and** a non-nil, query-safe
  (empty) `Attributor`. With more than one namespace, assert the partial map from
  the namespaces that succeeded is still populated (`errors.Join` semantics).

## Step 7 — (R2) Unattributed-ready-pods warning

**Where:** the `CollectReplicaMetrics` wrapper (`replica_metrics.go`), right after
`collectReplicaMetrics` returns, beside the existing metrics-availability event
logic. **No signature change** — the wrapper already has `scaleTargets`,
`variantAutoscalings`, the returned `replicaMetrics`, `vaEventTracker`, and
`c.recorder`. (`fmt` is already imported.)

7a. New event reason constant in `internal/constants/constants.go`, alongside the
existing `K8SEvent*`:
```go
K8SEventUnattributedReadyPods = "UnattributedReadyPods"
```

7b. New helper mirroring `recordMetricsUnavailableEvent` (same `recorder == nil`
guard + `vaEventTracker` dedup keyed by `GetNamespacedKey(va.Namespace, va.Name)`):
```go
func (c *ReplicaMetricsCollector) recordUnattributedReadyPodsEvent(
    va *llmdVariantAutoscalingV1alpha1.VariantAutoscaling,
    readyCount int32,
    vaEventTracker map[string]bool,
) {
    if c.recorder == nil {
        return
    }
    key := utils.GetNamespacedKey(va.Namespace, va.Name)
    if vaEventTracker != nil {
        if _, ok := vaEventTracker[key]; ok { // one event per VA per cycle
            return
        }
    }
    c.recorder.Event(va, corev1.EventTypeWarning, constants.K8SEventUnattributedReadyPods,
        fmt.Sprintf("%d ready pod(s) but none attributed to this VariantAutoscaling; "+
            "verify the llm-d.ai/variant pod label equals the VA name", readyCount))
    if vaEventTracker != nil {
        vaEventTracker[key] = true
    }
}
```

7c. In `CollectReplicaMetrics`, **after** `collectReplicaMetrics` returns and after
the existing availability-event block, run the per-VA check. Skip entirely when
`len(replicaMetrics) == 0` (model-wide emptiness is the availability path's turf —
this is the scrape-lag gate):
```go
if err == nil && len(replicaMetrics) > 0 {
    attributed := make(map[string]int, len(variantAutoscalings))
    for i := range replicaMetrics {
        attributed[replicaMetrics[i].VariantName]++
    }
    for _, va := range variantAutoscalings {
        if attributed[va.Name] > 0 {
            continue
        }
        stKey := utils.GetNamespacedKey(va.Namespace, va.GetScaleTargetName())
        st, ok := scaleTargets[stKey]
        if !ok || st == nil {
            continue
        }
        if ready := st.GetStatusReadyReplicas(); ready > 0 {
            logger.V(logging.DEBUG).Info("VA has ready pods but none attributed",
                "va", va.Name, "namespace", va.Namespace, "readyReplicas", ready)
            c.recordUnattributedReadyPodsEvent(va, ready, vaEventTracker)
        }
    }
}
```
Notes:
- `attributed` is keyed by `VariantName` (= VA name, set from the attributor);
  within one call `namespace` is fixed so VA names are unique — keying by
  `va.Name` is correct.
- R2 requires `len > 0`; the availability path emits only on `len == 0` —
  disjoint, so sharing `vaEventTracker` never double-counts a VA in one cycle.
  Placing R2 after the availability block keeps that ordering explicit.

7d. **Tests** (`replica_metrics_test.go`):
- Seed `scaleTargets` with a real accessor — no new mock: build an
  `*appsv1.Deployment` with `Status.ReadyReplicas = N`, wrap via
  `scaletarget.NewDeploymentAccessor`, key by
  `GetNamespacedKey(ns, va.GetScaleTargetName())`.
- Two VAs on one model: source returns an attributed replica for VA-A only; VA-B
  has `ReadyReplicas > 0` and zero attributed → assert a `record.FakeRecorder`
  event with reason `UnattributedReadyPods` for **VA-B** and **none** for VA-A
  (drain `fakeRecorder.Events`, match the reason substring).
- Negatives: (i) VA-B `ReadyReplicas == 0` → no event (pending); (ii) model
  returns no metrics (`len == 0`) → no `UnattributedReadyPods` event (availability
  path owns it).

7e. **Dev-guide:** in `docs/design/controller-behavior.md` troubleshooting (the
"no scaling decisions for a variant" symptom), note WVA now emits an
`UnattributedReadyPods` Warning Event on the VA when the scale target has Ready
pods but the pod label does not resolve — so `kubectl describe va <name>` surfaces
the misconfiguration directly. Reflect code state only.

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

## Finalization — squash to one commit before the PR (R1/R2 fixups)

The branch was pushed with two `fixup!` commits (R1 `85bd65de`, R2 `59e9990d`)
on top of `7157c7d2`. This project lands commits as-is (not squash-merged), so
collapse them to one clean commit before the PR is opened:

1. Revert the spurious RBAC drift so the tree is clean for rebase:
   `git checkout -- config/base/rbac/manager-clusterrole.yaml` → `git status` clean.
2. Autosquash: `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash 526ce851`;
   confirm `git log --oneline 526ce851..HEAD` shows **one** commit.
3. Amend the commit body so it reflects the full diff (autosquash keeps the v1
   message and drops the fixup messages): add R1 (builder error-return + per-pod
   skip demoted to DEBUG) and R2 (`UnattributedReadyPods` warning event).
   `git commit --amend`.
4. Re-run gates (gofmt / `make test` / `make lint` / `go build` / `make manifests`
   → no diff; re-revert RBAC if it re-dirties) and verify DCO on the single
   commit: `git log 526ce851..HEAD --format=%b | grep Signed-off-by`.
5. **Do not push.** The branch is already on origin at the 3-commit tip, so
   landing the squash needs a `--force-with-lease` — that is Dean's action
   (coders never push or force-push). Write a `plan__*.md` handoff that the
   squash + amend is done and the branch is ready for Dean's force-push; stop
   there.

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
- **(R1)** A builder/factory interface for `Attributor` — keep the free
  `BuildLabelAttributor` constructor; defer the factory until a second impl
  exists (a code comment marks the future seam).
- **(R1)** Edge-triggered dedup of the degraded-attribution warning — a plain
  once-per-model `logger.Error` is sufficient now.
- **(R2)** Per-pod *cross-cycle* suppression of the not-WVA DEBUG skip — the line
  is off by default; a persistent pod-keyed set + pruning is not worth it here.
  (R2's VA-level warning, where suppression matters, is deduped per cycle.)
- **(R2)** Attribution change-detection / a stateful-cached `Attributor` (skip the
  per-cycle LIST when nothing changed) — backlog. Collides with the deliberate
  no-Pod-informer choice (uncached `APIReader`); the seam already permits a
  stateful impl, so this most naturally arrives with #1267. File as a follow-up.

## Coordination note (for the planner, not the coder)

This normalizes the 3 throughput queries on main and fixes their latent A1
key-mismatch. TA3/#1250 carries its own A1 fix on its branch; when #1250 rebases
onto a main containing this PR, that fix is already present — the rebase adapts
(TA3 also drops the label and uses the attributor). Flag to the #1250 owner so
they don't double-apply.
