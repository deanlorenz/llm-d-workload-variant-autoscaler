# WVA Position Summary

## Core Value of WVA

**1. Advanced Metric Provider**

* WVA can generate workload-aware metrics that go beyond raw infrastructure signals:

  * Estimation-based
  * SLO-based
  * Throughput-based
  * History-based
  * Workload-aware resource utilization
* These metrics enable better resource right-sizing (e.g., distinguishing prefill-heavy from decode-heavy workloads).
* Metrics can be exposed for use by any auto-scaler, dashboard, or eventing system.
* Current WVA v1 mostly relies on existing metrics, so similar behavior can often be reproduced without WVA; future value comes from richer metrics.

**2. Combined Decision Logic**

* WVA combines multiple signals and policies into a single scaling decision.
* Supports non-linear and context-aware logic that is difficult or impossible to express in Prometheus/KEDA alone.
* Examples:

  * Queue length + cache utilization + decode rate.
  * Avoid scale-up when resources are unavailable.
  * Enforce fair-share across tenants/models.
  * Interpret KV cache usage differently depending on workload state.
* WVA outputs a desired replica count, effectively acting as the scaling decision engine rather than just a metric source.

**3. Multi-Deployment Coordination**
A key differentiator from traditional auto-scalers, which scale deployments independently.

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

**4. Cost Optimization**

* Not a capability provided by KEDA.
* WVA already supports cost-aware placement for pay-per-use environments.
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
* WVA should not be positioned as a KEDA extension or "HPA on steroids," but as the workload-aware auto-scaling system for llm-d.

**4. Multi-KEDA Coordination Must Remain in WVA**

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
- KEDA requires two control loops (>60 s each). Queue builds up.
- WVA converges in one coordinated control loop.
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

### Scenario B: Traffic triples
**Demand:** 12P, 12D (Decode limited to 8 replicas)

#### KEDA
- Scales Prefill to **12P**.
- Decode cannot grow beyond **8D**.
- Result: **12P, 8D**. (missing cpacity)

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
- Endpoint **A**: **A100** (1 replica = 1 unit), OR **L40** (2 replicas = 1 unit, cheaper)
- Endpoint **B**: **A100 only**
- Current capacity: **A=4×L40,4×A100**; **B=2×A100**
- Maximum cluster capacity: **12×L40, 8×A100**

### Scenario
Demand increases for both A and B.

#### KEDA
- Scales all deployments independently.
- Result: **A=8×L40,4×A100**; **B=4×A100**.

#### WVA
- Optimizes the variant mix.
- Result: **A=12×L40,2×A100**; **B=6×A100**.

#### Analysis
- WVA preserves scarce A100 GPUs for workloads that require them.
- **KEDA makes the correct local decision; WVA makes the correct global decision.**

---

## 3. Endpoint-Level Scaling

### Setup
Same as UC2. Current: A=4×L40,4×A100.

### Scenario
Small demand increase: **+0.5 capacity units**.

#### KEDA
- L40: **4→5** (+0.5)
- A100: **4→5** (+1.0)
- Total added: **1.5 units**.

#### WVA
- L40: **4→5** (+0.5)
- A100: **unchanged**.
- Total added: **0.5 units**.

#### Analysis
- KEDA scales deployments; WVA scales the endpoint.
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

- There is a customer with UC4 as a specific use-Case
  * On going work to create an "Coordinator" component that will balance resources between models ("PoC", seems independent of main WVA)
  * Current WVA applies fair share and limits during scale-up only. Working on adding reallocation to WVA.
  
- For multi-variant use-cases (UC2, UC3)
  * We have seen clusters with heterogeneous GPUs and models that can be deployed on different GPU types.
  * We do not have a concrete example for heterogeneous deployments behind one end-point (although EPP supports this). 
  * KEDA cannot support this, so we should not expect to find existing auto-scale enabled use-cases. 
