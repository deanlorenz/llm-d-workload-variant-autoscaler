# Evaluation Framework for Autoscaling and Provisioning Policies in Latency-Sensitive Services

## Status
Draft design proposal.

---

# 1. Motivation

Modern latency-sensitive services increasingly exhibit:
- highly variable request cost,
- bursty traffic,
- nonlinear queueing behavior,
- long provisioning delays,
- tail-latency sensitivity.

Examples include:
- LLM inference,
- distributed search,
- SQL/query serving,
- RPC microservice backends,
- serverless execution platforms.

Traditional autoscaling evaluation methodologies are often insufficient because they:
- optimize average utilization instead of user-visible SLOs,
- evaluate using average latency instead of tail behavior,
- assume request count approximates workload,
- ignore provisioning lag,
- fail to distinguish admissible overload from pathological overload.

This document proposes a workload-aware evaluation framework for comparing:
- autoscaling policies,
- reserve/headroom policies,
- scaling configurations,
- overload behavior,
- cost-efficiency tradeoffs.

The framework intentionally treats the system as a black box from the user perspective.

Internal implementation details such as:
- KV cache pressure,
- batching internals,
- scheduler state,
- routing heuristics,
are not required for evaluation.

---

# 2. Prior-Art Foundations

The framework builds on ideas from several established research and operational domains.

## 2.1 Tail-Latency-Aware Systems

Large-scale search and cloud systems established that:
- average latency is insufficient,
- tail latency dominates user experience,
- queue collapse and transient overload matter more than steady-state averages.

The framework therefore emphasizes:
- P95/P99 latency,
- SLO violation rates,
- overload duration,
- recovery behavior.

---

## 2.2 SLA-Aware Resource Provisioning

Cloud provisioning literature shifted from:
- maximizing utilization,

toward:
- minimizing cost under SLO constraints.

This framework follows the same principle.

---

## 2.3 Queueing and Provisioning Delay

Reactive autoscaling has repeatedly been shown to be too slow for short-timescale burst handling.

Provisioning delays of:
- VMs,
- containers,
- GPU workloads,
- model loading,
can be significantly longer than burst timescales.

Therefore:
- standing reserve capacity dominates short-term burst handling,
- autoscaling primarily tracks medium-timescale demand changes.

The framework explicitly evaluates burst absorption capability.

---

## 2.4 QoS and Admissible Workloads

Networking and QoS systems commonly define guarantees only for traffic satisfying admissibility constraints.

This framework adopts the same principle:
- SLO guarantees apply only to workloads within a defined admissible envelope.

However, systems are still evaluated on graceful degradation behavior outside the envelope.

---

## 2.5 Heterogeneous-Cost Requests

Prior systems such as:
- distributed search,
- SQL/query serving,
- serverless platforms,
observed that request count is often a poor proxy for actual work.

This framework therefore evaluates workloads using measured work rather than raw request count.

---

# 3. Design Principles

The framework is built around the following principles.

## P1. Black-box evaluation

Evaluation should depend only on externally observable behavior.

No assumptions are made regarding:
- routing,
- admission control,
- batching,
- scheduling,
- internal metrics.

---

## P2. Separation of workload characterization and policy evaluation

The workload itself must be characterized independently of the autoscaling policy being evaluated.

This avoids circular evaluation.

---

## P3. Explicit admissibility assumptions

No finite provisioning system can guarantee SLOs under arbitrary workloads.

Evaluation therefore requires explicit workload admissibility assumptions.

---

## P4. Graceful overload behavior matters

Out-of-envelope traffic should not be ignored entirely.

The framework evaluates:
- overload containment,
- recovery behavior,
- collapse resistance,
- client-visible failure semantics.

---

## P5. Tail behavior dominates averages

Tail latency and violation duration are primary metrics.

Average latency alone is insufficient.

---

# 4. Two-Phase Evaluation Methodology

The framework separates:
1. workload characterization,
2. policy evaluation.

---

# 5. Phase 1 — Workload Characterization

## 5.1 Goal

Construct a workload model independent of autoscaling behavior.

---

## 5.2 Reference System

The workload is first executed against a heavily overprovisioned reference system.

The reference system should:
- avoid saturation,
- avoid queue buildup,
- avoid autoscaling lag,
- avoid admission control effects,
- minimize client-visible overload.

The purpose is not operational efficiency.

The purpose is to approximate unconstrained service behavior.

---

## 5.3 Measured Data

The reference execution captures:
- request arrival trace,
- actual completed work over time,
- latency distributions,
- burst structure,
- service-time distributions,
- time-varying workload intensity.

Importantly:
- actual work is measured retrospectively using completed requests.

This enables workload characterization even when later evaluated systems cannot fully serve the workload.

---

## 5.4 Work Definition

The framework intentionally avoids relying on implementation-specific internal metrics.

Possible work units include:
- total processed tokens,
- measured service time,
- normalized request cost.

The framework avoids:
- CPU utilization,
- GPU utilization,
- scheduler internals,
- KV-cache metrics,
for evaluation.

---

# 6. Envelope Construction

## 6.1 Motivation

The workload envelope defines the region in which SLO guarantees are expected to hold.

This avoids the unrealistic assumption that systems must satisfy SLOs under arbitrary overload.

---

## 6.2 Envelope Model

The framework adopts a token-bucket-style admissibility model.

Example formulation:

\[
W(t+\Delta)-W(t) \leq \sigma + \rho \Delta
\]

Where:
- \(W(t)\) is cumulative admitted work,
- \(\rho\) is sustainable work rate,
- \(\sigma\) is admissible burst budget.

The envelope constrains work, not request count.

---

## 6.3 Trace-Derived Envelopes

In many practical systems:
- the admissible envelope is not known a priori.

The framework therefore allows:
- deriving envelopes from reference traces.

This supports:
- real production traces,
- exploratory benchmarking,
- workload-driven calibration.

---

## 6.4 Standardized Benchmark Classes

Long-term benchmarking should define:
- standardized workload classes,
- standardized envelopes,
- reusable traces.

Examples may include:
- low-burst workloads,
- high-burst workloads,
- heavy-tail request distributions,
- adversarial burst patterns.

This is analogous to:
- TPC-style database benchmarks,
- network QoS traffic classes.

---

# 7. Phase 2 — Policy Evaluation

Policies are evaluated using:
- the same workload trace,
- the same admissible envelope,
- the same cost model.

Policies may differ in:
- autoscaling algorithms,
- reserve/headroom strategies,
- scaling configurations,
- queue policies,
- overload behavior.

The framework intentionally does not assume control over:
- routing,
- admission control,
- request scheduling.

The benchmark must remain meaningful even when these components are absent or poorly implemented.

---

# 8. Client-Side Failure Semantics

Because the benchmark does not assume correct admission control behavior, the framework relies on client-visible outcomes.

This includes:
- successful completion,
- timeout,
- explicit rejection,
- cancellation,
- dropped connection.

Client-side timeout policies are therefore part of benchmark configuration.

Timeouts serve as a black-box mechanism for:
- bounding queue growth,
- detecting collapse behavior,
- measuring graceful degradation.

---

# 9. Evaluation Metrics

# 9.1 Cost Metrics

Examples:
- GPU-hours,
- active replica-hours,
- peak allocation,
- energy cost.

These metrics are straightforward.

---

# 9.2 In-Envelope SLO Compliance

Primary metric:

\[
SLOScore =
\frac{
\text{admissible work completed within SLO}
}{
\text{total admissible work}
}
\]

Possible SLOs include:
- TTFT,
- end-to-end latency,
- deadline completion,
- throughput guarantees.

The framework evaluates work, not merely request count.

This avoids bias caused by heterogeneous request cost.

---

# 9.3 Out-of-Envelope Behavior

Out-of-envelope behavior is evaluated separately.

The framework does not require systems to satisfy strict SLO guarantees under arbitrary overload.

Instead, evaluation focuses on:
- graceful degradation,
- overload containment,
- recovery behavior,
- collapse resistance,
- fairness,
- client-visible failure quality.

Examples:
- timeout rate,
- queue explosion duration,
- recovery latency after overload,
- work successfully completed during overload.

This area intentionally remains flexible and may evolve as benchmark methodology matures.

---

# 9.4 Burst Absorption Capability

Burst handling remains a first-class evaluation criterion.

Even when dominated by reserve capacity, burst handling directly affects:
- operational cost,
- required headroom,
- user-visible latency.

Possible metrics:
- maximum admissible burst absorbed without SLO violation,
- violation severity versus burst size,
- recovery time after burst arrival.

This enables comparison against:
- static overprovisioning baselines,
- alternative autoscaling strategies.

---

# 10. Relationship Between Autoscaling and Reserve Capacity

The framework explicitly recognizes:
- provisioning delay fundamentally limits reactive autoscaling.

Therefore:
- reserve/headroom policies are part of the effective scaling strategy.

The benchmark intentionally evaluates:
- the combined operational policy,
not merely the autoscaling controller in isolation.

---

# 11. Intended Outcomes

The framework aims to enable rigorous comparison of:
- autoscaling policies,
- reserve strategies,
- provisioning configurations,
- overload handling approaches,
under realistic bursty heterogeneous-cost workloads.

The framework intentionally avoids:
- implementation-specific metrics,
- average-only evaluation,
- unrealistic assumptions regarding infinite elasticity.

Instead, it emphasizes:
- workload-aware evaluation,
- admissibility-aware guarantees,
- tail-latency behavior,
- graceful degradation,
- operational cost.

---

# 12. Open Questions

Several areas require additional research and refinement.

## 12.1 Envelope Inference

How should admissible envelopes be inferred from traces?

Questions include:
- statistical fitting,
- worst-case bounds,
- percentile-based envelopes,
- workload class generalization.

---

## 12.2 Out-of-Envelope Scoring

How should overload behavior be weighted?

Open issues include:
- binary versus continuous penalty models,
- fairness weighting,
- timeout semantics,
- recovery weighting.

---

## 12.3 Work Normalization

What is the most portable work unit across systems?

Candidates include:
- tokens,
- measured service time,
- normalized compute estimates.

---

## 12.4 Standardized Workload Suites

How should reusable workload classes be defined and shared?

Potential directions:
- trace repositories,
- synthetic generators,
- standardized envelope families.

---

# 13. Summary

This framework proposes:
- trace-based workload characterization,
- admissibility-aware evaluation,
- black-box system evaluation,
- tail-latency-centric metrics,
- explicit overload semantics,
- combined evaluation of autoscaling and reserve policies.

The framework is designed for systems exhibiting:
- heterogeneous request cost,
- bursty arrivals,
- nonlinear queueing behavior,
- long provisioning delay,
- latency-sensitive user-visible SLOs.

The approach draws heavily from:
- tail-at-scale systems,
- SLA-aware provisioning,
- distributed search,
- SQL/query serving,
- queueing systems,
- QoS and admission-control literature.
