# WVA Position Summary

## Core Value of WVA

WVA's value builds in layers, each harder to dismiss as "just a metric source": a metric provider (exportable, and useful beyond autoscaling), then combined decision logic (a *decision*, not a scalar that a threshold can consume), then multi-deployment coordination (a joint decision no per-deployment scaler can make).

**1. Advanced Metric Provider**

* WVA can generate workload-aware metrics that go beyond raw infrastructure signals:

  * Estimation-based
  * SLO-based
  * Throughput-based
  * History-based
  * Workload-aware resource utilization
* These metrics enable better resource right-sizing (e.g., distinguishing prefill-heavy from decode-heavy workloads).
* Metrics can be exposed for use by any auto-scaler, dashboard, or eventing system — and are useful beyond autoscaling (capacity planning, batch scheduling, request routing). This is the consensus value-add of WVA to llm-d.
* Honest scope: WVA v1's *metrics* largely reuse existing signals, so this layer alone can often be reproduced without WVA; the richer metrics are future work. The combined logic and coordination below (Sections 2–4) are *not* reproducible in KEDA regardless.

**2. Combined Decision Logic**

* WVA combines multiple signals and policies into a single scaling decision.
* Supports non-linear, conditional (if-then-else) logic that KEDA/HPA cannot express: HPA combines multiple metrics only by taking the *max* of independently-computed per-trigger targets — it cannot branch or combine signals non-monotonically. A single PromQL query can encode some conditions, but it is one time-series expression, not multi-step policy.
* Examples:

  * Queue length + cache utilization + decode rate.
  * Avoid scale-up when resources are unavailable.
  * Enforce fair-share across tenants/models.
  * Interpret KV cache usage differently depending on workload state.
* WVA outputs a desired replica count — a *decision*, not a scalar that a threshold consumes — so it is the scaling decision engine, not just a metric source.

**3. Multi-Deployment Coordination**
The key differentiator. KEDA/HPA are per-deployment (per-ScaledObject): there is no joint decision across deployments and no constrained allocation of a shared resource. This is architectural, not a missing feature — no per-deployment scaler can make these decisions, whatever metrics it is fed.

**Correlated Deployments**

* Example: Prefill (P) and Decode (D) deployments.
* Need coordinated scaling because scaling one without the other provides little value.
* Independent scaling eventually converges but reacts more slowly.

**Shared Resources**

* Multiple deployments compete for the same GPU pool.
* WVA can enforce global resource-sharing policies:

  * Fair share
  * Quotas
  * Priorities
* Future work includes active resource reallocation between workloads.

**Deployment Variants**

* Multiple implementations of the same model behind one endpoint.
* WVA can optimize placement and scaling decisions across heterogeneous hardware (e.g., different GPU types).
* Supports resource optimization at the fleet level rather than deployment level.
* This is WVA's most novel capability — no autoscaler supports multi-variant scaling today — and correspondingly the most debated. The correlated-deployment and shared-resource cases carry the position on their own even if one sets variants aside. (Emerging llm-d inference-gateway work — dispatching a request to one of several candidate models by cost/complexity — would strengthen the multi-variant case further.)

**4. Cost Optimization**

* Not a capability provided by KEDA.
* WVA already supports cost-aware placement for pay-per-use environments.
* Cost is a distinct steering lever — separate from the resource-arbitration in Section 3. (E.g., cost can bias WVA toward cheaper variants such as L40; avoiding starvation of an A100-only workload is a *different* reason to steer the same way.)
* Future opportunities include broader cost optimization and revenue maximization under constrained resources.

---

## Implementation Direction

**1. KEDA-like User Experience**

* Installation and configuration should be no harder than KEDA.
* A higher-level configuration layer should automatically generate and configure WVA components.
* Current configuration is fragmented and remains too complex for users.

**2. Quality and Hardening**

* Significant improvements have been made:

  * New observability dashboard.
  * Better benchmarking.
  * Multi-variant testing.
* However, many code paths still lack true end-to-end validation.
* Reliability, testing, and operational confidence should be a major priority.

**3. WVA as the Auto-scaling Brain**

* WVA already performs the actual scaling decision and emits desired replica counts.
* HPA/KEDA are effectively actuators that execute WVA's decisions.
* Therefore, WVA should be viewed as the auto-scaler intelligence layer, not merely an analytics component.
* The user-facing experience should abstract away KEDA/HPA complexity.
* WVA uses KEDA/HPA the way the llm-d inference router uses a service-mesh proxy (e.g. istio): the proxy is the data plane that executes decisions, the router is the intelligence. Nobody calls the llm-d router "istio on steroids." KEDA/HPA are the actuation substrate; WVA is the decision engine.
* WVA should not be positioned as a KEDA extension or "HPA on steroids," but as the workload-aware auto-scaling system for llm-d.

**4. Coordinating Multiple KEDA Instances Must Remain in WVA**

* KEDA cannot coordinate scaling decisions across multiple deployments.
* Multi-deployment orchestration and global optimization are inherently WVA responsibilities.
* This capability is one of WVA's strongest differentiators and should remain a core part of its architecture.

---

## Bottom Line

The strongest long-term justification for WVA is **global, workload-aware optimization across multiple deployments and shared resources**, not merely exposing new metrics. Advanced metrics are useful, but they can often be consumed by other auto-scalers. The unique value lies in acting as the **auto-scaling decision engine ("brain")**, combining complex policies, coordinating multiple deployments, optimizing resource allocation, and ultimately driving scaling decisions through existing actuators such as KEDA or HPA.

# WVA Use Case Scenarios

The following examples assume KEDA has access to the best available llm-d and vLLM metrics. The differentiator is **not** metric quality, but WVA's ability to make coordinated, global scaling decisions.

| UC | Capability | Demonstrates |
|---|---|---|
| UC1 | Correlated Deployment | Coordinate scaling across correlated deployments (Prefill → Decode). |
| UC2 | Variant Selection | Choose the optimal deployment variant based on global resource optimization. |
| UC3 | Endpoint-Level Scaling | Coordinate scaling across equivalent deployment variants of the same endpoint. |
| UC4 | Shared Resources | Apply cluster-wide policies (fair share, quotas, admission control). |

---

## 1. Correlated Deployment

### Setup
- Pipeline: **Prefill → Decode**
- Current capacity: **4P, 4D**
- Maximum cluster capacity: **12P, 8D**

### Scenario A: Traffic doubles
**Demand:** 8P, 8D

#### KEDA
- Detects Prefill load first.
- Scales **4P → 8P**.
- Decode scales after new Prefill replicas become active.
- Result: **8P, 8D**.

#### WVA
- Recognizes both stages must scale together.
- Scales directly to **8P, 8D**.

#### Analysis
- Same final capacity.
- KEDA's two loops are *cascaded*: Decode's load only appears once new Prefill replicas are live, so Decode's warmup starts only after Prefill's finishes. Each vLLM warmup is >60 s, so KEDA converges in ~2× warmup (>120 s), with the queue building throughout.
- WVA scales both stages at once → a single warmup (~>60 s).
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

### Scenario B: Traffic triples
**Demand:** 12P, 12D (Decode limited to 8 replicas)

#### KEDA
- Scales Prefill to **12P**.
- Decode cannot grow beyond **8D**.
- Result: **12P, 8D**. (missing capacity)

#### WVA
- Recognizes Decode is the bottleneck.
- Suppresses additional Prefill scaling.
- Result: **8P, 8D**.

#### Analysis
- Extra Prefill replicas provide little benefit.
- Decode becomes overloaded, increasing latency for every request.
- Resources could be used by another workload.
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

---

## 2. Variant Selection

### Setup
- One *demand unit* = the serving capacity of one A100 replica.
- Endpoint **A**: **A100** (1 replica = 1 demand unit), OR **L40** (2 replicas = 1 demand unit, cheaper)
- Endpoint **B**: **A100 only**
- Current capacity: **A=4×L40, 2×A100** (4 demand units); **B=2×A100** (2 demand units)
- Maximum cluster capacity: **12×L40, 8×A100**

### Scenario
Demand grows for both endpoints: **A → 8 demand units**, **B → 6 demand units** (B is A100-only).

#### KEDA
- Scales each deployment independently on its own demand.
- A grows both its variants: **A=8×L40, 4×A100** (8 units).
- B wants **6×A100**, but A greedily took 4 of the 8 A100s, leaving only 4 → **B=4×A100** (starved: 4 units, needs 6).

#### WVA
- Reserves scarce A100 for the A100-only workload and steers A's growth onto L40.
- **A=12×L40, 2×A100** (8 units — A's 2×A100 unchanged; all growth went to L40); **B=6×A100** (6 units, fully served).
- A100 total = 2 + 6 = 8 = cluster cap.

#### Analysis
- WVA *reserves* scarce A100 for the workload that can only use A100 (B), steering A's growth to L40. This needs no reallocation — A's existing A100s are untouched; only new demand is placed.
- The point is preventing **B's starvation**, not cost. Cost is a separate lever that could further bias A toward L40 (see Core Value §4).
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

---

## 3. Endpoint-Level Scaling

### Setup
Same as UC2. Current: **A=4×L40, 2×A100**.

### Scenario
Small demand increase to endpoint A: **+0.5 demand units**.
The endpoint's demand is presented to *both* of A's variant deployments' scalers; each rounds up independently, because KEDA has no notion they serve the same endpoint.

#### KEDA
- L40: **4→5** (+0.5)
- A100: **2→3** (+1.0)
- Total added: **1.5 units**.

#### WVA
- L40: **4→5** (+0.5)
- A100: **unchanged**.
- Total added: **0.5 units**.

#### Analysis
- KEDA scales deployments; WVA scales the endpoint. Independent per-deployment rounding over-provisions (+1.5) where the endpoint needs only +0.5.
- Extension: had demand risen by **+1.0 unit**, WVA would add a single A100 (exactly one unit, one replica) rather than 2×L40 — it matches the *variant* to the increment, not just the replica count. KEDA cannot make this choice; each variant deployment scales on its own.
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

---

## 4. Shared Resources

### Setup
- Endpoint: **A, B**
- Current capacity: **A=4 GPUS**; **B=4 GPUs**
- Maximum cluster capacity: **16 GPUs** (8 GPUs available)

### Scenario
A spikes first. B spikes shortly afterward.

#### KEDA
- A scales to **12 GPUs**.
- B later **cannot scale**.
- Result: **A=12, B=4**.

#### WVA
- Applies fair-share policy.
- A scales to **8 GPUs**.
- B later scales to **8 GPUs**.
- Result: **A=8, B=8**.

#### Analysis
- WVA prevents starvation of B.
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

## Notes

- **UC4 status.** There is a customer with UC4 as a specific use case.
  * Ongoing work on a "Coordinator" component that balances resources between models (a PoC, currently seems independent of core WVA). Notably, this KEDA-oriented effort is itself discovering that KEDA cannot coordinate across deployments — indirect evidence for WVA's thesis.
  * Current WVA applies fair-share and limits at *scale-up* only; reallocation is not yet implemented.
  * A near-term path exists: have WVA emit a *desired end-state* — compute the target replica mix from scratch each cycle (or from ~50% of current) rather than an increment. KEDA/HPA then move gracefully between configurations, adding and removing replicas; this also covers intra-model reallocation (e.g. replacing 2×L40 with 1×A100). A more advanced version adds new replicas before removing old ones. This desired-end-state framing is also what makes UC2's variant reshaping expressible — a metric cannot encode a joint end-state across deployments.

- **Multi-variant status (UC2, UC3).**
  * We have seen clusters with heterogeneous GPUs and models deployable on different GPU types.
  * We do not yet have a concrete example of heterogeneous deployments behind one endpoint (though EPP supports it).
  * KEDA cannot support this, so we should not expect to find existing autoscale-enabled use cases — the absence is a consequence of the capability gap, not evidence against the need.
