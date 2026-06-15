# Variant Attribution

This document describes how the metrics collector associates per-replica metrics
with the `VariantAutoscaling` (VA) that owns each replica, and the seam that keeps
that association decoupled from the Prometheus queries.

## Two separate concerns

Collecting per-replica metrics and deciding which VA a replica belongs to are
deliberately kept apart:

1. **Per-replica queries carry replica identity only.** Every per-replica PromQL
   template (saturation, queueing-model, and throughput-analyzer queries under
   `internal/collector/registration/`) selects by `{namespace, model_name}` and
   groups by `(instance, pod)`. They do **not** carry a `llm_d_ai_variant` label.
   `buildInstanceKey` (in `replica_metrics.go`) turns those labels into a single
   replica identity key (`pod:port`, falling back to `instance`), and nothing
   else.

2. **VA attribution is resolved once per pod, after the query**, through the
   `Attributor` seam.

This separation means a per-pod metric for the same replica from any query
(KV-cache usage, generation-token rate, …) merges into a single
`ReplicaMetrics` entry keyed by replica identity, and the question "which VA owns
this pod?" is answered in exactly one place.

## The `Attributor` seam

`internal/collector/attribution` defines:

```go
type Attributor interface {
    VAForPod(namespace, podName string) (vaName string, ok bool)
}
```

An `Attributor` is built once per optimization cycle and queried `O(1)` for each
pod on the metrics-assembly path. `CollectReplicaMetrics` takes an `Attributor`
and, for each discovered replica, sets `VariantName` from `VAForPod`; replicas
that resolve to no VA are skipped (same behavior as before, different source).

### Default implementation: the label attributor

`BuildLabelAttributor` is the default. It performs one bounded, labeled `List`
per namespace — `client.HasLabels{"llm-d.ai/variant"}` — via an **uncached API
reader** (`mgr.GetAPIReader()`), so it starts no Pod informer/cache. It maps each
labeled pod to the VA named by its `llm-d.ai/variant` label value. The
`ServiceMonitor`/`PodMonitor` relabeling rule that used to copy the pod label
into the metric series is **no longer required for attribution** — the label is
read from the pod object directly.

The engine wires the reader in `prepareModelData`: it uses
`Engine.APIReader` when set (production, from `mgr.GetAPIReader()`) and falls back
to the cached client when nil (unit tests).

## Adding a new attribution mechanism

Alternative resolution strategies (for example, an owner-reference walk from pod
to its controlling workload to the VA) become additional `Attributor`
implementations in this package. They plug in behind the same interface — the
queries, the collector hot path, and every analyzer are untouched.
