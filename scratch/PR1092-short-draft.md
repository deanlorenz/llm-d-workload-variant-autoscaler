# Short Draft — PR #1092 Review Comment

> Internal draft only. Do not post.

---

Thanks for the proposal — the Level 1 / Level 2 framing is a useful way to position WVA, and
worth capturing regardless of what we do with the CRD.

A few concerns before moving forward:

**Pluggability is independent of discovery mechanism.**  
Level 1 already works: teams that don't want WVA don't create VA CRDs. The CRD is opt-in; it
doesn't gate any other scaling approach. Level 2 (`RegisterAnalyzer`) is an engine interface
concern — it works identically whether variants are discovered via CRD or annotation. Neither
goal requires CRD removal.

**Operational burden is unchanged.**  
Users provide the same data either way (model ID, cost, min/max replicas). The CRD gives them
schema documentation, `kubectl get va -A` discoverability, and status feedback in return.
Annotations give them none of that for the same input cost.

**CRD semantics lost with no stated replacement.**  
Three specific losses worth calling out together:

- *Status*: `DesiredOptimizedAlloc`, `MetricsAvailable`, `OptimizationReady` — there is no
  Kubernetes object an operator can inspect to understand WVA's current decision state after
  Phase 3.
- *Validation*: `variantCost` pattern, `minReplicas ≤ maxReplicas` CEL rule, required `modelID`
  all move from admission-time enforcement to runtime failures. The error path for a malformed
  annotation needs a surface — currently there isn't one.
- *Lifecycle*: annotation removal has no deletion event for WVA to observe. A GitOps reconciler
  re-applying a ScaledObject from a stale template silently restores WVA management without
  operator intent. `kubectl delete va` produces a deterministic, observable event; removing an
  annotation does not.

**WVA config bleeds into KEDA objects.**  
`llm-d.ai/*` annotations on ScaledObjects are visible to all tooling and persist if WVA is
uninstalled. The CRD keeps WVA configuration on WVA-owned resources.

**KServe integration contract is broken.**  
`VariantAutoscalingConfigSpec` is an explicitly embeddable type for KServe (and potentially
other higher-level controllers) to inline without field duplication. CRD removal removes that
contract; the proposal doesn't address it.
