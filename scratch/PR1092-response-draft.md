# Draft Response: PR #1092 — va removal proposal

> Internal draft only. Do not post.

---

Thank you for this proposal. The Level 1 / Level 2 pluggability framework is a valuable way to
articulate where WVA fits in the broader scaling ecosystem, and reducing operational complexity
for users is a goal we share. We have some concerns about whether the proposed mechanism achieves
those goals, and a counter-proposal that we believe addresses them more directly.

---

## Concerns

### 1. The pluggability goals are independent of the CRD

The proposal frames CRD removal as enabling the Level 1 and Level 2 pluggability described in the
design philosophy section. We don't think this connection holds.

**Level 1** (teams using plain Prometheus triggers on ScaledObjects without WVA) works today,
without any changes to WVA. A team that does not want WVA simply does not create a VA CRD. Those
workloads are invisible to WVA — no gating, no required integration. The CRD does not prevent any
team from building their own scaling pipeline alongside a WVA-managed deployment.

**Level 2** (registering custom analyzers via `RegisterAnalyzer`) is an engine interface concern,
independent of how variants are discovered. A custom analyzer works whether discovery is CRD-based
or annotation-based. CRD removal is not required to enable pluggable analyzers.

The Level 1 / Level 2 framework is valuable on its own terms, but it is not a consequence of CRD
removal.

### 2. Loss of operational observability

The VA CRD's status subresource is the only place an operator can inspect WVA's decisions today:

- `status.desiredOptimizedAlloc.numReplicas` — what WVA computed as the target replica count
- `status.desiredOptimizedAlloc.lastRunTime` — when WVA last ran for this variant
- `status.conditions[MetricsAvailable]` — whether vLLM metrics are reachable
- `status.conditions[OptimizationReady]` — whether the optimization step succeeded
- `kubectl get va -A` — a cluster-wide table of all managed variants and their state

After Phase 3, none of this would exist. The proposal removes status management as a motivation
for CRD removal but does not address where this observability goes. Without a replacement, an
operator debugging a scaling problem has no Kubernetes object to inspect.

### 3. Validation regression

The VA CRD enforces invariants at admission time:

- `variantCost` is validated against `^\d+(\.\d+)?$` and defaults to `"10.0"`
- `minReplicas <= maxReplicas` is enforced as a CEL cross-field validation rule
- `modelID` is required with a minimum length of 1

Annotations are unvalidated free strings. `llm-d.ai/variant-cost: "not-a-number"` is accepted
silently by the API server and fails at runtime. WVA would need to implement its own error
reporting path for malformed annotations, with no standard Kubernetes surface to surface those
errors to the user.

### 4. WVA configuration leaks into KEDA/HPA objects

Placing WVA-specific annotations on ScaledObjects or HPAs makes WVA's configuration visible in
any Kubernetes tooling (dashboards, operators, auditing, GitOps) regardless of whether WVA is
deployed. `kubectl describe scaledobject` would show `llm-d.ai/model-id`, `llm-d.ai/variant-cost`,
etc. — configuration that is meaningful only to WVA and meaningless to KEDA.

If WVA is uninstalled, these annotations remain as permanent dead metadata on KEDA objects. The
VA CRD keeps WVA configuration on WVA-owned resources, with a clean boundary between what WVA
knows about and what KEDA knows about.

### 5. Lifecycle semantics are lost

With the VA CRD, lifecycle is explicit: `kubectl delete va` produces a deletion event that WVA
reacts to, cleaning up its internal state. Owner references, finalizers, and reconciler watches
work as expected.

Annotations have no lifecycle semantics. There is no deletion event for WVA to observe when an
annotation is removed. "Stop managing this variant" requires manually editing a KEDA/HPA object
rather than deleting a WVA-owned resource, and there is no guarantee that the annotation is
removed if a GitOps tool re-applies the ScaledObject from a stale template.

### 6. The KServe integration contract is removed

`VariantAutoscalingConfigSpec` is explicitly designed as an embeddable type so that higher-level
controllers (e.g., KServe) can inline it without duplicating field definitions. CRD removal
eliminates this formalized integration contract. The proposal does not address this.

### 7. The operational burden is unchanged

The proposal describes the transition from 3 objects to 2 objects as an operational win. However,
a user configuring WVA must provide the same information either way: model ID, cost, min/max
replicas. The data moves from a dedicated, validated, discoverable CRD with status feedback to
annotations on a KEDA object with no validation, no status, and no standardized cluster-wide
view. For an operator new to WVA, encountering `llm-d.ai/model-id: "granite-13b"` on a
ScaledObject is less self-explanatory than a VA CRD with an explicit documented schema.

---

## Counter-Proposal: WVA Owns the KEDA ScaledObject

The goal of reducing objects-per-variant is achievable through an inverted ownership model: **the
user creates a VA CRD; WVA creates and manages the KEDA ScaledObject as a child resource using
owner references.** The user touches exactly one object. WVA handles the rest.

### Ownership comparison

| Aspect | Current state | PR #1092 | Counter-proposal |
|---|---|---|---|
| Objects user creates | VA CRD + ScaledObject | Annotated ScaledObject | VA CRD only |
| Objects WVA manages | VA CRD (reconciler) | Annotations on ScaledObject | VA CRD + ScaledObject (child) |
| KEDA trigger configuration | User writes manually | User writes manually | WVA auto-generates |
| Status / observability | VA CRD status subresource | None | VA CRD status (unchanged) |
| Admission-time validation | API server enforces | None | API server enforces (unchanged) |
| WVA config location | WVA-owned CRD | KEDA/HPA object | WVA-owned CRD (unchanged) |
| Lifecycle semantics | Delete VA CRD → WVA reacts | Remove annotation manually | Delete VA CRD → cascades to ScaledObject |
| KServe embed point | `VariantAutoscalingConfigSpec` | None | `VariantAutoscalingConfigSpec` (unchanged) |
| Misconfiguration risk | User must write correct trigger | User must write correct trigger | Eliminated — trigger is auto-generated |

### What WVA would manage in the ScaledObject

| Category | ScaledObject fields | Source in VA CRD |
|---|---|---|
| Auto-generated | `triggers[0]` (query, threshold, metricType, serverAddress) | Derived from `spec.modelID` + namespace + WVA's Prometheus address |
| Mapped from existing VA spec | `scaleTargetRef.name/kind/apiVersion`, `minReplicaCount`, `maxReplicaCount` | Direct mapping, no new fields |
| Optional tuning (new VA spec fields) | `pollingInterval`, `cooldownPeriod`, `idleReplicaCount`, `fallback.{failureThreshold, replicas, behavior}`, `advanced.horizontalPodAutoscalerConfig.behavior` | New optional fields with safe defaults |

The auto-generated category eliminates the main friction in the current user flow: the user must
today write a KEDA Prometheus trigger that correctly references `wva_desired_replicas` with the
right labels, threshold, and metric type. This is error-prone and WVA-specific knowledge. Under
this model, WVA generates that trigger from first principles — the user cannot get it wrong.

The optional tuning fields represent the maximum footprint of WVA's ScaledObject ownership with
respect to the KEDA API. All have safe defaults; omitting them produces a correct ScaledObject.
The full design of these fields is a separate discussion.

---

We are very supportive of the pluggability direction described in this proposal and would be glad
to discuss both the Level 1 / Level 2 framing and the ownership model further.
