# Proposal: A Metric-Based Analyzer Interface for WVA

**Status:** DRAFT — for discussion.
**Audience:** WVA maintainers and contributors; readable without plans-branch context.

---

## Summary

Today a WVA *analyzer* is a Go component that observes the system, and — in the same
breath — aggregates its observations across variants, roles, and namespaces before handing a
structured result to the optimizer. This proposal splits those two jobs apart and collapses the
analyzer's *contract* to a small, uniform, metric-based shape:

> Every analyzer produces, per finest-grain item, exactly two numbers:
> a **demand** $D$ and a **target** $P$ (the per-replica capacity — KEDA's "threshold"), in a unit of
> the analyzer's own choosing, such that $D/P$ is a replica count. Nothing else.

Because that shape is deliberately the shape KEDA/HPA already use — a measured signal and a
per-replica target — the interface becomes **symmetric**, and two capabilities fall out of the
same contract:

1. **WVA's own analyzer results become metrics** that KEDA/HPA or any other consumer can read.
2. **External analyzers become definable as plain PromQL** — WVA can be extended with no code
   change, by describing an analyzer as a demand query and a target query.

The optimizer, the engine's aggregation, and the actuation path are unchanged in spirit; what
changes is that the analyzer stops being a bespoke computation and becomes a **data provider** with
a metric-shaped contract.

---

## Motivation

- **The analyzer contract is bespoke.** Each analyzer produces a rich, structured, analyzer-specific
  result. There is no uniform, minimal shape that a new signal — or an external tool — could speak.
- **Extending WVA requires writing Go.** A new signal — a custom SLO probe, a queue-depth source, a
  business metric — cannot be added without implementing and compiling a new analyzer.
- **WVA's intelligence is trapped.** The demand/capacity reasoning WVA computes every cycle is not
  exposed anywhere a standard autoscaler or dashboard can consume it.
- **Operators already think in `(signal, threshold)`.** KEDA's entire model is "here is a measured
  value; here is the per-replica target." Meeting operators in that vocabulary lowers the barrier to
  both understanding WVA and integrating it.

---

## The contract

### Granularity

WVA collects metrics **per pod**. The collection loop runs once per `(namespace, model, analyzer)`,
maps each pod to the **ScaledObject** $S$ it belongs to, and derives the rest of an item's labels
from $S$. So the reported grain is the ScaledObject:

```
target  = ScaledObject S                        # the unit that receives a replica count
item    = (namespace, model, role, analyzer)    # role and other labels are inferred from S
```

There is no separate `variant` label — a variant is effectively the target itself. An **analyzer** is
identified by a label $L$ that is **unique within a single WVA instance**.

### The two metrics

Per analyzer $L$:

| Metric | Scope | Meaning |
|---|---|---|
| **Demand** $D_L$ | per **model instance** — `(namespace, model)` | Total demand for the whole model instance, in analyzer $L$'s unit. **One value per model instance**, not per ScaledObject. Collected as `last()( Q_demand{model, namespace} )`. |
| **Target** $P_L(S)$ | per **ScaledObject** $S$ | The amount of demand (same unit as $D_L$) that a **single replica** of $S$ can supply — the per-replica capacity (PRC). Named **target** to match HPA's `target`/`averageValue`; KEDA's Prometheus scaler calls the analogous knob `threshold`. Collected **per pod** as `last() by (pod)( Q_target{model, namespace} )`, then reduced pod→$S$ (see [External analyzers](#external-analyzers)). |

The two share a unit *within an analyzer* so that $D_L / P_L(S)$ is a pure replica count. Different
analyzers may use entirely different units (KV-tokens, requests/s, ITL-seconds) — they never need
to agree, because each analyzer's contribution is reduced to replicas before anything is combined.
Units and normalization beyond this are **out of scope for this document** (see
[Out of scope](#out-of-scope)).

### Provenance label $E$

An optional **error/provenance hint** $E$ records *how* a value was obtained (e.g. `direct`,
`fallback`, `stale`, `fetch-failed`). $E$ is **observability only** — the engine and optimizer never
branch on it. It is **set inside WVA** — by an internal analyzer (in Go) or, for an external
analyzer, by the wrapper from collection state — and is **never read from an external query result**
(a PromQL result cannot carry it). It surfaces in two places: the engine's per-cycle **logs**, and as
a label on the metrics **WVA itself emits** for each analyzer (see
[Metric emission](#metric-emission-and-naming)).

### Tolerance and effective target

Per analyzer, two **tolerances** $T_u$, $T_d$ scale the target for the two directions, giving an
**effective target** in each:

$$P_{\text{up}} = T_u \cdot P \qquad\qquad P_{\text{down}} = T_d \cdot P$$

The gap between $T_u$ and $T_d$ is a deliberate no-op dead-band. This is WVA's current per-analyzer
scale-up / scale-down setting, re-expressed as a multiplier on the target rather than a divisor on
demand (algebraically identical). **The tolerances are applied by the engine, not the analyzer** —
the analyzer always emits the raw target $P$, and $T_u$, $T_d$ remain WVA configuration (so an
external source publishes an unadjusted target). There is no direct KEDA/HPA equivalent for
per-direction tolerances — the nearest are HPA's single symmetric `tolerance` and KEDA's
`activationThreshold`, both different.

### Three states: not-defined vs. missing vs. present

The absent-vs-zero distinction is a first-class part of the contract:

| State | Condition | Engine/optimizer treatment |
|---|---|---|
| **Not defined** | The analyzer's selector does not cover this model/$S$. | **Ignored** — contributes nothing; no penalty, no suppression. Distinct from "missing." |
| **Missing / degraded** | The analyzer applies, but data is absent or partial this cycle — empty/failed query, too few pods. | **External:** fall back if the definition lists one (records an `e` label), else produce nothing for that $S$. **Internal:** its explicit discrete reliability signal applies (e.g. suppress scale-down). The value is never fabricated as `0`. |
| **Present** | A value is returned, **including `0`**. | Used as-is. `0` is a real observation (zero demand, zero capacity), distinct from absent. |

---

## The single-ScaledObject case

When a model instance's entire demand is served by one ScaledObject $S$, the analyzer's two numbers
answer the scaling question directly:

$$N^{*} = \left\lceil \frac{D}{P} \right\rceil \qquad\qquad g = D - N \cdot P$$

using $P_{\text{up}}$ for scale-up and $P_{\text{down}}$ for scale-down; $N$ is the current replica
count and a negative gap $g$ means scale-down. This is exactly KEDA's `AverageValue` arithmetic
(`desired = ceil(total_metric / target)`) with $D$ as the total metric and $P$ as the target. It is
the clean base case, and all most simple deployments ever need.

---

## The multi-ScaledObject case

When a model instance's demand is split across several ScaledObjects — prefill/decode roles,
multiple variants, multiple accelerator types — $N = D/P$ no longer applies per $S$ in isolation,
because $D$ is one shared pool and the several $S$ jointly serve it. This is precisely the problem the
**optimizer already solves**, and this proposal does **not** change that:

- Across **variant alternatives** serving the same role, contributions combine as a **sum** of
  utilizations (any alternative helps).
- Across **roles**, they combine as a **min** of utilizations (every role must be served).

The interface simplification (analyzer emits $D$ and $P$) is orthogonal to the coordination logic
(the optimizer's AND/OR reasoning over utilizations). The single-$S$ formula above is the special
case of the coordinated problem when there is one $S$ per demand. Detailed coordination semantics
are the optimizer's concern and are documented separately.

---

## Metric emission and naming

WVA emits the results of **every** analyzer it knows — internal and external alike — as Prometheus
signals with a small, common label set. Metric names cannot contain dots, so the analyzer label is a
**label**, not part of the name:

```
wva_analyzer_demand{analyzer, namespace, model}                 # per model instance
wva_analyzer_target{analyzer, namespace, model, scaledobject}   # per ScaledObject
```

- The common labels are `(analyzer, namespace, model)`, plus `scaledobject` on the per-$S$ target.
  The **`scaledobject` identifier must be unique**, so a consumer can tell what a series points to.
- A ScaledObject name can be opaque, so an optional free-form **`description`** label (contents TBD —
  e.g. role, GPU count, inference-pool name) may be attached for dashboard readability. If it proves
  confusing it can be dropped; it is an easy later addition.
- **Absence is meaningful:** a missing series is *not* a zero; consumers must not coalesce absent
  to `0`.
- Anything beyond this common shape (extra labels, provenance, per-analyzer specifics) is out of
  scope for this proposal.

These series realize the symmetry: WVA emits them for its own analyzers (making its reasoning
observable), and reads the PromQL equivalents for external analyzers.

---

## External analyzers

An **external analyzer** is defined entirely as PromQL — no Go, no rebuild. A built-in
**external-analyzer wrapper** implements the internal analyzer interface, is initialized from a
definition, runs the queries each cycle, and reduces the per-pod results to per-ScaledObject targets.
Internal (Go) analyzers are unchanged.

### What the analyzer supplies vs. what WVA wraps

A definition supplies only the *inner* metric selector `Q`; WVA supplies the scoping and the
last-value/reduction wrapping. Schematically:

```
demand  →  last()         ( Q_demand{ model="{{model}}", namespace="{{ns}}" } )   # one value per (model, ns)
target  →  last() by(pod) ( Q_target{ model="{{model}}", namespace="{{ns}}" } )   # one value per pod
```

`{{model}}` and `{{ns}}` are templated by the collection loop. The demand query yields a single value
per model instance; the target query yields one value **per pod**, which the wrapper reduces to a
per-ScaledObject target.

### Pod → ScaledObject reduction

The wrapper maps each pod to its ScaledObject and reduces the per-pod targets to one value per $S$.
The **default reduction is the average** of the pods' per-replica capacities; the definition language
may extend this to `median` / `min` / `max`. (A constant target — a fixed per-replica capacity — is
just a degenerate query.) This pod→$S$ reduction is the wrapper's job; combining *across* ScaledObjects
to feed the optimizer happens as today (see [Roles](#roles-and-responsibilities)).

> A plain average is specific to the generic pluggable wrapper. A **complex internal analyzer** may
> legitimately combine pods **non-uniformly** and produce its own per-$S$ target. Both expose the
> identical Go interface — the difference is only in how the per-$S$ target is computed.

### Definition shape (analyzer-centric)

Because **demand is per model instance** while **target is per ScaledObject**, attaching queries to
individual ScaledObjects would force the demand query to be duplicated across every $S$ of a model —
redundant and drift-prone. Instead, a definition is **per analyzer** and selects its targets:

```
ExternalAnalyzer:
  label:    L                        # unique within the WVA instance
  selector:                          # simple list — modelID + namespace, no label matching
    - { namespace: ns-a, modelID: model-x }
    - { namespace: ns-b, modelID: model-y }
  demandQuery: Q_demand              # single inner selector; WVA wraps as last()( … {{model}},{{ns}} )
                                     # no fallback list for external analyzers
  target:                            # per pod; ordered fallbacks, first success wins
    - { query: Q_target_primary,  e: direct }
    - { query: Q_target_fallback, e: fallback }
  targetReduce: avg | median | min | max     # optional; default avg (pod → ScaledObject)
```

- One definition covers many models and ScaledObjects. Each query is written **once** and templated
  per matched `(namespace, model)` / per matched $S$. Different analyzers naturally have different
  queries — nothing is shared across analyzer labels.
- **Selector is a simple list** of `(namespace, modelID)` pairs — no label matching. If two
  definitions with the same label $L$ could match the same item, that is a **configuration error**
  (surfaced as an error or warning): one wins, the other is disabled.
- Where the selector does **not** match a model or $S$, the analyzer is **ignored** for that item
  (the "not defined" state) — not treated as missing.
- Provenance and units cannot come from a PromQL result, so any $E$/unit metadata for an external
  analyzer comes from the wrapper/definition, not the query.

> The definition is **implementation-agnostic**: *how* it reaches WVA — ConfigMap, CRD, API — is TBD
> and orthogonal to this proposal.

### Fallbacks and error handling

- The target may list **ordered fallback queries**; the wrapper uses the **first that succeeds** and
  records which one via an `e` label. For an external analyzer this is **observability only** — a used
  fallback is logged; it does **not** by itself change the scaling action.
- **All target queries fail / empty** → no target for that $S$ this cycle, so the analyzer produces
  no result for it (contributes nothing — never a fabricated `0`).
- **No definition covers the item** → **ignored**.

Internal analyzers, by contrast, carry an explicit **discrete** reliability signal — e.g. "do not
claim spare capacity" — that *is* actionable: the engine suppresses scale-down for that analyzer. A
continuous $[0,1]$ confidence is meaningful only when a **real metric** computes it (not a fallback
label), and users should not have to hand-pick cutoff values — so it is deliberately **not** part of
the external definition.

---

## Roles and responsibilities

The proposal draws a firm line between observation, decision, and actuation:

- **Analyzers are data providers, not decision makers.** They are an *observation of system state*.
  They may hold some internal state (fitted models, smoothing windows), but they never decide replica
  counts.
- **Optimizers make decisions.** They consume the collected analyzer data and make the
  **cross-ScaledObject** decisions — coordinating across variants, roles, and models — to compute
  desired replica counts per ScaledObject, as today.
- **KEDA/HPA actuate.** They apply the decision.
- **Each ScaledObject is owned by exactly one of {KEDA, WVA}** — never both. There is no contention
  over who scales a given $S$.

Two clarifications:

- **Metric collection vs. computation.** For an external analyzer the wrapper runs the queries and
  turns the results into the contract; internal analyzers produce the contract directly in Go. Either
  way, the optimizer receives already-processed per-$S$ data, as today.
- **Aggregation is not re-architected here.** Producing each $S$'s target from its pods, and combining
  across variants / roles / model to feed the optimizer, happens as it does today. For an **external**
  analyzer this aggregation is standard and the wrapper performs it; for internal analyzers it is
  whatever that analyzer already does. **Where** that aggregation ultimately lives — inside analyzers
  or lifted into the engine — is an internal cleanup unrelated to this proposal (noted for future,
  out of scope here).

---

## Relationship to KEDA

WVA should **look like** KEDA without **depending on** it.

- KEDA's Prometheus scaler is always scoped to a **single ScaledObject** (hence to a model/namespace,
  even a role), and its query is **almost identical** in shape to WVA's. The differences: KEDA's
  target is a **static** number, whereas WVA's $P$ is **itself a query** (per-replica capacity can be
  measured/dynamic); and WVA scopes **demand per model instance** rather than per ScaledObject, which
  is what makes multi-$S$ coordination expressible at all — something a per-trigger KEDA threshold
  cannot represent.
- Because the query shape is so close, a KEDA Prometheus-scaler definition can be **converted** into a
  WVA external analyzer with **no change to KEDA** — its query becomes the analyzer's inner selector.
- **No KEDA dependency** is introduced. WVA is KEDA-*shaped* but independent.

The two symmetrical goals, restated:

1. **Expose WVA's internal analyzer results as metrics** consumable by KEDA/HPA and other components.
2. **Consume external analyzers** defined as PromQL inside WVA.

Where both a WVA optimizer and KEDA exist, WVA owns multi-ScaledObject coordination; the exposed
metrics let KEDA/HPA drive simple single-$S$ cases or serve purely as observability. They never both
actuate the same $S$.

---

## Out of scope

- **Units and normalization.** The only common ground asserted here is: within a single ScaledObject
  the common unit is **replicas** ($D/P$); all cross-$S$ coordination is done in **utilization**
  (`supply/demand`, where supply may be current, anticipated, desired, …). That coordination — and
  the choice of units within it — is entirely the **optimizer's** concern and is documented
  elsewhere.
- **Tight KEDA integration.** WVA is KEDA-shaped but independent; deeper KEDA integration is not part
  of this proposal.

---

<!-- INTERNAL — plans-branch only. STRIP everything below before external publication. -->
## Open questions (internal — plans-branch only)

1. **`description` label.** Whether to add the optional free-form `description` label (role / GPU count
   / inference-pool name), or keep the label set minimal.
2. **Staleness (implementation detail).** The definition does **not** let a user set a staleness
   limit; each query implies its own period and the analyze-loop period is fixed here. Behavior when a
   query returns stale data is a wrapper implementation detail, TBD — noted, not specified.
3. **Reduction grammar.** Confirm the pod→$S$ reduction set: `avg` (default), plus `median`/`min`/`max`.
   No weighted reduction is planned.

## Internal cross-references (plans-branch only)

- `planning/optimizer-coordination-design.md` — the coordination model (analyzers as metric
  providers; optimizer AND/OR over utilizations; supply taxonomy). This proposal is the *interface*
  counterpart to that *coordination* design.
- `planning/multi-analyzer-design.md` — current analyzer/engine/optimizer architecture. Future
  directions there on analyzer-published demand and per-analyzer observability metrics are unified by
  this proposal. **Two things noted for future, deliberately out of scope here:** (a) relocating the
  cross-target aggregation from analyzers into the engine (the shared helpers already make this a
  call-site move); (b) the analyzer status-return / reliability mechanism, which is the internal-code
  form of the discrete scale-down suppression referenced above.
- `planning/error-paths-design.md` — the internal error-path handling for degraded/missing signals.
  Related, but its detail is deliberately **kept out of this external proposal**.
