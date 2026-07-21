# Proposal: A Metric-Based Analyzer Interface for WVA

**Authors:** Dean Lorenz
**Status:** Draft
**Created:** 2026-07-21
**Last Updated:** 2026-07-21

---

## Problem Statement

WVA's *analyzers* are bespoke Go components: each observes the system and produces a rich,
analyzer-specific structured result that the optimizer consumes. This carries three costs:

- **The analyzer contract is bespoke.** There is no uniform, minimal shape that a new signal — or an
  external tool — could speak.
- **Extending WVA requires writing Go.** A custom SLO probe, a queue-depth source, or a business
  metric cannot be added without implementing and compiling a new analyzer.
- **WVA's reasoning is trapped.** The demand/capacity computation WVA performs every cycle is not
  exposed anywhere a standard autoscaler or dashboard can consume it.

Meanwhile, operators already reason in KEDA/HPA's vocabulary: a measured signal and a per-replica
target. Meeting them in that vocabulary lowers the barrier both to understanding WVA and to
integrating with it.

## Goals

- Collapse the analyzer contract to **two numbers per finest-grain item** — a **demand** $D$ and a
  **target** $P$ (per-replica capacity) — in a unit of the analyzer's own choosing, such that $D/P$
  is a replica count.
- **Expose every analyzer's results** (internal and external alike) as Prometheus metrics with a
  small common label set, so KEDA/HPA and dashboards can consume WVA's reasoning.
- **Allow external analyzers to be defined as PromQL**, so WVA can be extended with no code change.
- Keep the contract **symmetric with KEDA/HPA** so the two interoperate naturally.

## Non-Goals

- **Units and normalization** beyond "$D/P$ is replicas within a single ScaledObject." Cross-target
  coordination is done in utilization space and remains entirely the optimizer's concern.
- **Tight KEDA integration or dependency.** WVA is KEDA-*shaped* but independent.
- **Re-architecting where aggregation lives** (inside analyzers vs. lifted into the engine) — an
  internal cleanup unrelated to this contract.
- **Changing the optimizer's coordination logic or the actuation path.**

## Background: KEDA / HPA vocabulary

KEDA's Prometheus scaler is a `(query, threshold)` pair scoped to a single ScaledObject; HPA then
computes `desired = ceil(total_metric / target)`. WVA's `(demand, target)` maps onto this directly,
with two deliberate generalizations:

- the **target is itself a query** (per-replica capacity can be measured/dynamic, not a static
  constant), and
- **demand is per model instance** rather than per ScaledObject, which is what makes multi-target
  coordination expressible at all.

## Design

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
analyzers may use entirely different units (KV-tokens, requests/s, ITL-seconds) — they never need to
agree, because each analyzer's contribution is reduced to replicas before anything is combined.

### Provenance label $E$

An optional **error/provenance hint** $E$ records *how* a value was obtained (e.g. `direct`,
`fallback`, `stale`, `fetch-failed`). $E$ is **observability only** — the engine and optimizer never
branch on it. It is **set inside WVA** — by an internal analyzer (in Go) or, for an external analyzer,
by the wrapper from collection state — and is **never read from an external query result** (a PromQL
result cannot carry it). It surfaces in the engine's per-cycle logs and as a label on the metrics WVA
itself emits.

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

### The single-ScaledObject case

When a model instance's entire demand is served by one ScaledObject $S$, the analyzer's two numbers
answer the scaling question directly:

$$N^{*} = \left\lceil \frac{D}{P} \right\rceil \qquad\qquad g = D - N \cdot P$$

using $P_{\text{up}}$ for scale-up and $P_{\text{down}}$ for scale-down; $N$ is the current replica
count and a negative gap $g$ means scale-down. This is exactly KEDA's `AverageValue` arithmetic
(`desired = ceil(total_metric / target)`) with $D$ as the total metric and $P$ as the target — the
clean base case that covers most simple deployments.

### The multi-ScaledObject case

When a model instance's demand is split across several ScaledObjects — prefill/decode roles, multiple
variants, multiple accelerator types — $N = D/P$ no longer applies per $S$ in isolation, because $D$
is one shared pool and the several $S$ jointly serve it. This is precisely the problem the
**optimizer already solves**, and this proposal does **not** change that:

- Across **variant alternatives** serving the same role, contributions combine as a **sum** of
  utilizations (any alternative helps).
- Across **roles**, they combine as a **min** of utilizations (every role must be served).

The interface simplification (analyzer emits $D$ and $P$) is orthogonal to the coordination logic
(the optimizer's AND/OR reasoning over utilizations). The single-$S$ formula above is the special
case when there is one $S$ per demand.

### Metric emission

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
  e.g. role, GPU count, inference-pool name) may be attached for dashboard readability.
- **Absence is meaningful:** a missing series is *not* a zero; consumers must not coalesce absent to
  `0`.

These series realize the symmetry: WVA emits them for its own analyzers (making its reasoning
observable), and reads the PromQL equivalents for external analyzers.

### External analyzers

An **external analyzer** is defined entirely as PromQL — no Go, no rebuild. A built-in
**external-analyzer wrapper** implements the internal analyzer interface, is initialized from a
definition, runs the queries each cycle, and reduces the per-pod results to per-ScaledObject targets.
Internal (Go) analyzers are unchanged.

**What the analyzer supplies vs. what WVA wraps.** A definition supplies only the *inner* metric
selector $Q$; WVA supplies the scoping and the last-value/reduction wrapping. Schematically:

```
demand  →  last()         ( Q_demand{ model="{{model}}", namespace="{{ns}}" } )   # one value per (model, ns)
target  →  last() by(pod) ( Q_target{ model="{{model}}", namespace="{{ns}}" } )   # one value per pod
```

`{{model}}` and `{{ns}}` are templated by the collection loop. The demand query yields a single value
per model instance; the target query yields one value **per pod**.

**Pod → ScaledObject reduction.** The wrapper maps each pod to its ScaledObject and reduces the
per-pod targets to one value per $S$. The **default reduction is the average** of the pods'
per-replica capacities; the definition language may extend this to `median` / `min` / `max`. (A
constant target is just a degenerate query.) Combining *across* ScaledObjects to feed the optimizer
happens as today. A complex **internal** analyzer may instead combine pods non-uniformly and produce
its own per-$S$ target; both expose the identical Go interface.

**Definition shape (analyzer-centric).** Because demand is per model instance while the target is per
ScaledObject, attaching queries to individual ScaledObjects would force the demand query to be
duplicated across every $S$ of a model. Instead, a definition is **per analyzer** and selects its
targets:

```
ExternalAnalyzer:
  label:    L                        # unique within the WVA instance
  selector:                          # simple list — modelID + namespace, no label matching
    - { namespace: ns-a, modelID: model-x }
    - { namespace: ns-b, modelID: model-y }
  demandQuery: Q_demand              # single inner selector; WVA wraps as last()( … {{model}},{{ns}} )
  target:                            # per pod; ordered fallbacks, first success wins
    - { query: Q_target_primary,  e: direct }
    - { query: Q_target_fallback, e: fallback }
  targetReduce: avg | median | min | max     # optional; default avg (pod → ScaledObject)
```

- One definition covers many models and ScaledObjects; each query is written **once** and templated
  per matched `(namespace, model)` / per matched $S$. Different analyzers have different queries —
  nothing is shared across analyzer labels.
- The **selector is a simple list** of `(namespace, modelID)` pairs — no label matching. If two
  definitions with the same label $L$ could match the same item, that is a **configuration error**
  (surfaced as an error or warning): one wins, the other is disabled.
- Where the selector does **not** match a model or $S$, the analyzer is **ignored** for that item —
  not treated as missing.
- The definition is **implementation-agnostic**: *how* it reaches WVA — ConfigMap, CRD, API — is TBD
  and orthogonal to this proposal.

**Fallbacks and error handling.** The target may list **ordered fallback queries**; the wrapper uses
the **first that succeeds** and records which one via an `e` label. For an external analyzer this is
**observability only** — a used fallback is logged; it does not by itself change the scaling action.
If **all target queries fail/empty**, the analyzer produces no result for that $S$ this cycle (never
a fabricated `0`). Internal analyzers, by contrast, carry an explicit **discrete** reliability signal
(e.g. "do not claim spare capacity") that *is* actionable.

### Roles and responsibilities

The proposal draws a firm line between observation, decision, and actuation:

- **Analyzers are data providers, not decision makers.** They are an *observation of system state*.
  They may hold internal state (fitted models, smoothing windows) but never decide replica counts.
- **Optimizers make decisions.** They consume the collected analyzer data and make the
  **cross-ScaledObject** decisions — coordinating across variants, roles, and models — to compute
  desired replica counts per ScaledObject.
- **KEDA/HPA actuate.** They apply the decision.
- **Each ScaledObject is owned by exactly one of {KEDA, WVA}** — never both. There is no contention
  over who scales a given $S$.

For an external analyzer the wrapper runs the queries and turns the results into the contract; for
internal analyzers the Go implementation produces it directly. Either way, the optimizer receives
already-processed per-$S$ data.

### Relationship to KEDA

WVA should **look like** KEDA without **depending on** it. Because the query shape is so close, a KEDA
Prometheus-scaler definition can be **converted** into a WVA external analyzer with **no change to
KEDA** — its query becomes the analyzer's inner selector. Where both a WVA optimizer and KEDA exist,
WVA owns multi-ScaledObject coordination; the exposed metrics let KEDA/HPA drive simple single-$S$
cases or serve purely as observability. They never both actuate the same $S$.

## Implementation phases

1. **Internal contract + metric exposure.** Define the `(demand, target)` contract internally and emit
   `wva_analyzer_*` metrics for the existing internal analyzers with the common label set. Pure
   observability — no behavior change.
2. **External-analyzer wrapper.** Add the analyzer-centric PromQL definition and the wrapper that
   implements the internal analyzer interface (query templating, pod→$S$ reduction, selector, ordered
   fallbacks with `e` labels), feeding results to the optimizer.
3. **Polish.** Provenance/`description` labels, reduction-function grammar, and hardening of the
   wrapper's error handling.

## Alternatives considered

- **Object-centric external definitions** (queries attached per ScaledObject). Rejected: demand is
  per model instance, so this duplicates the demand query across every ScaledObject of a model —
  redundant and drift-prone.
- **Normalize to utilization at the source** (analyzers emit `supply/demand` directly). Rejected for
  the contract: replica-space $D/P$ is the natural single-$S$ answer and the KEDA-compatible one;
  utilization is the optimizer's cross-target currency, not the analyzer's output.

## Backward compatibility

- **Internal analyzers are unchanged**; they keep producing their results in Go.
- **Metrics are additive** — new `wva_analyzer_*` series, no change to existing emission.
- **Each ScaledObject is owned by exactly one of {KEDA, WVA}**, so there is no dual-actuation risk.
- The **optimizer coordination logic and the actuation path are unchanged.**

## References

- KEDA Prometheus scaler — https://keda.sh/docs/latest/scalers/prometheus/
- Kubernetes Horizontal Pod Autoscaler — https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
