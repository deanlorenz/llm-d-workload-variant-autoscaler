# Evaluation Framework for Autoscaling and Provisioning Policies

**Status:** Draft — under discussion.

---

## 1. Motivation

Traditional autoscaling evaluation optimizes average utilization and uses average latency as the primary metric. For latency-sensitive services with bursty arrivals, heterogeneous request cost, and long provisioning delays — LLM inference, distributed search, query serving — this is systematically insufficient. Average latency hides tail behavior, average utilization hides queue collapse, and request count is a poor proxy for actual work when requests vary by orders of magnitude in cost.

This framework evaluates autoscaling policies against a well-characterized workload with explicit admissibility assumptions, judging the combined effect of autoscaling mechanism and reserve/headroom strategy by client-visible outcomes.

---

## 2. Core Principles

**Separate workload from policy.** Characterize the workload independently before evaluating any policy. This prevents circular measurement.

**Admissibility-aware.** No system can guarantee SLOs under arbitrary load. State the workload envelope explicitly; evaluate in-envelope and out-of-envelope behavior separately and with different standards.

**Tail over average.** P95/P99 latency and SLO violation duration are primary. Average latency is insufficient.

**Evaluate combined policy.** Autoscaling and reserve capacity are jointly evaluated as a single operational strategy. *Reserve capacity* is the pre-committed headroom above current demand — the standing buffer that absorbs demand spikes before new replicas start serving. Because provisioning delay (bringup lag plus autoscaler loop period) is typically 30–120 seconds, reactive scaling alone cannot protect short-timescale bursts. The two are inseparable: the optimal reserve size depends on the autoscaling policy and vice versa.

**Define the test subject.** Each combination of *autoscaling engine* and *policy configuration* is a distinct evaluation subject. The engine is the mechanism — the algorithm, the signals it watches, the scale decisions it makes. It is a gray box: its design is documented and its behavior is understood conceptually, but the framework does not require inspecting its internals to evaluate it. The policy is the configuration of that engine: thresholds, headroom, cooldown, scale-step size, or any tuning parameters. For each test subject, the policy is calibrated to the workload envelope and the engine's known capabilities (e.g., bringup lag), without access to the specific workload trace that will be used during evaluation.

---

## 3. Benchmark Construction

The benchmark is a *(workload trace, envelope)* pair produced independently of any autoscaling policy.

**Workload trace.** Run the workload against a heavily overprovisioned reference system that avoids saturation, queue buildup, and autoscaling lag. This approximates unconstrained service behavior and captures:
- request arrival trace,
- completed work over time (tokens processed or measured service time),
- latency distributions and burst structure.

Work is measured retrospectively on completed requests, so the characterization is valid even when evaluated systems later cannot fully serve the workload.

**Envelope derivation.** From the trace, derive (or define) the envelope that characterizes this class of workload. The envelope specifies what properties the autoscaler is being asked to handle. See § 5 for the model.

The *(trace, envelope)* pair is the benchmark. The trace is one concrete realization; the envelope defines the broader class of workloads the policy commits to serve.

---

## 4. Autoscaler Evaluation

Each test subject (engine + policy configuration) is given:
- the **envelope** (the contract it must honor), and
- its own **capabilities** (bringup lag, autoscaler loop period, scale-step size, etc.).

The test subject does **not** receive the workload trace in advance. It runs against the arriving trace in real time, using its policy calibrated to the envelope.

**Measurement.** SLO violations are measured from the client side — client-visible TTFT and completion outcomes only. Internal state (KV cache, scheduler queue, batching behavior) is not used in the evaluation. Envelope violations — determining whether arriving work stays within or exceeds the envelope bounds — are measured using the work data from benchmark construction, since the live system may not expose raw arriving work directly.

---

## 5. Workload Envelope

The envelope defines the class of workloads for which SLO guarantees are required. It is stated in work units (tokens or equivalent service time), so it can be evaluated directly against the trace from benchmark construction.

### 5.1 Envelope Constraint

Let W_t be the work arriving in discrete time window t (work units, t_ref = 1 window). Define the smooth baseline R(t) recursively:

```
R(0) = W(0)
R(t+1) = min(W(t+1),  R(t) + γ)
```

A workload is **in-envelope** if:

```
W(t)  ≤  R(t) + B    for all t
```

Two envelope parameters (both in work units):
- **γ** — maximum smooth growth per window. R grows at most γ per step; when W drops below R, R drops with it.
- **B** — burst headroom. The maximum by which W may exceed R(t) at any moment.

An optional third parameter:
- **ρ_max** — absolute cap on work per window: W_t ≤ ρ_max.

**Closed-form intuition.** R(t) equals the minimum over all past observations projected forward at slope γ:

```
R(t)  =  min_{0 ≤ s ≤ t}  [ W(s) + γ·(t − s) ]
```

Any dip in W pulls R down; between dips R rises at most γ per step. The in-envelope constraint W(t) ≤ R(t) + B is then the requirement that W stays below the upper of two parallel curves separated by B.

### 5.2 Two Curves and Burst Recovery

The envelope is two curves, both at slope γ, separated by B:

- **R(t):** lower curve — the smooth baseline
- **R(t) + B:** upper curve — the in-envelope ceiling

```
W_t
  |         R(t)+B · · · · · · ● · · · ·  (upper curve, slope γ)
  |                · · · ·    /
  |         W ────────────── /             W flat after burst
  |          ↑              /
  |         burst          /  R(t) ───────────────  (lower curve, slope γ)
  |         W→R(t_b)+B    /
  |        /             /
  |_______/             /
  +————————+————————————+——→ t
           t_b       t_b+B/γ
```

After a burst (W at the upper curve), both curves continue rising at γ while W stays flat. The gap W(t) − R(t) closes at rate γ. After B/γ windows R(t) has caught up to W(t) — full headroom B is available again. At the midpoint, B/2 headroom is available, allowing a follow-on burst of up to B/2.

When W drops below R(t): the recursive definition brings R down with W immediately, restoring the full headroom B at once. A traffic decrease never reduces burst availability.

### 5.3 Remark: Envelope and Autoscaler Capabilities

For any autoscaling engine, the envelope parameters (γ, B) constrain what can be guaranteed. Using Lionel's terminology: bringup lag T_cold, autoscaler loop interval Lag, and headroom — the standing excess supply above current demand.

To absorb a burst of size B **without any SLO violation**, the autoscaler must have excess supply equal to B already in place before the burst arrives. Reactive scaling cannot help: the burst arrives and resolves within T_cold + Lag. Headroom is the only defense for burst B.

For the smooth growth constraint γ, an autoscaler can track ramping load if its reaction time (T_cold + Lag) is short enough that headroom is not exhausted before new replicas arrive. A well-formed benchmark sets (γ, B) consistent with the capabilities it aims to stress-test.

---

## 6. Scoring Model

### 6.1 Graduated Violation Penalty

Rather than a binary pass/fail, each request carries a violation cost based on the severity of the SLO miss and the region of the envelope in which it falls.

**Region 1 — Smooth in-envelope.** The autoscaler had full headroom and lead time. SLO compliance is fully required. Violations are penalized at full weight.

**Region 2 — In-burst (burst ≤ B).** Reserve capacity is the only defense; reactive scaling cannot help. A relaxed target T_slo + ΔT_burst applies. Up to p% of requests during the burst may exceed T_slo (but must meet the relaxed target). Violations beyond this tolerance carry a reduced penalty.

The burst SLO relaxation and tolerance p% are benchmark-defined parameters and are part of the envelope specification. For example: "a burst of up to B tokens is allowed once per evaluation window; during the burst, up to 10% of requests may be served with TTFT ≤ T_slo + ΔT, until the growth rate returns to γ."

**Region 3 — Out-of-envelope.** No contractual SLO guarantee applies. The evaluation measures graceful degradation: how well the system handles excess load without collapsing. The effective SLO target extends further with the degree of excess. Violations carry a small, severity-proportional penalty.

### 6.2 Calibrated Combined Score

Rather than a separate (cost, SLO) Pareto frontier, the framework uses a single combined score. SLO violations are translated into equivalent resource cost using a calibration factor derived from the benchmark itself.

**Calibration factor:**
```
A  =  Total_flat_cost / Σ_r W(r)
```
where Total_flat_cost is the resource cost of the minimal flat-scale (optimal-static) solution, and Σ_r W(r) is the total work in the trace. A has units of resource-cost per work unit — the resource cost per unit of work served.

**Per-request violation cost** (in resource-cost units):
```
C_i  =  w_region(i) · max(0,  T_i − T_target(i))^α / T_slo · W(r_i) · A
```
where:
- w_region(1) > 1  (in-envelope violations are more costly than simply "not serving"),
- w_region(2) ∈ (0, 1)  (burst violations, partial credit),
- w_region(3) ∈ (0, w_region(2))  (out-of-envelope violations, graceful degradation),
- α ≥ 1  (super-linear to penalize severe violations more than marginal ones),
- T_target(i) is the applicable SLO target for the region.

**Combined score:**
```
Score  =  Resource_cost  +  Σ_i C_i
```

Lower is better. The calibration ensures the two terms are in the same units. The calibration factor A may not be known a priori in all settings, but it always exists and can be computed from the benchmark.

This is not a pure Pareto frontier. Combining cost and SLO into a single score requires a choice of relative weighting (encoded in A and the w_region weights), but it produces a comparable scalar across autoscaling strategies on the same benchmark.

---

## 7. Flow Control and Queueing Semantics

There is no admission control mechanism that enforces the workload envelope on arriving traffic. Instead, flow control (EPP-level backpressure) and queueing at the inference gateway shape the effective demand reaching the inference engines.

From the client's perspective:
```
TTFT_observed  =  EPP_queue_time  +  inference_TTFT
```

This is the correct quantity to use for SLO evaluation: it reflects the full latency the user experiences, including time spent waiting in the gateway queue.

Requests that are currently being served are not affected by requests queuing behind them (assuming the inference engine handles them independently). The EPP queue isolates the two groups: queued requests observe their TTFT growing as they wait; served requests complete at inference-TTFT.

**Client behavior and system recovery.** Client-side behavior (timeouts, retries, cancellations) affects the actual load on the system in ways that are difficult to account for cleanly. If clients time out early and abandon their requests, the effective arriving work drains faster and the system recovers sooner — but the measurement records SLO violations (timeouts), not completions. If clients retry on timeout, the load may increase during overload, creating a feedback loop.

How to incorporate client behavior into the overall system score is an open question. At minimum, the benchmark must specify a timeout policy and count timeouts as SLO violations with an appropriate penalty weight.

---

## 8. Response to Lionel's Proposal

Lionel's [Evaluating LLM Autoscaling Strategies](https://github.com/lionelvillard/llm-d-workload-variant-autoscaler/blob/eval-strategy/docs/blog/evaluating-autoscaling-strategies.md)
is a clear and well-crafted piece. The supply/demand framing is exactly the right lens. The distinction between KV-cache demand (a stock) and arrival rate (a flow) is a genuinely important insight, easy to miss and consequential for autoscaler design. The burstiness ceiling formula — Burst_max = Head / (T_cold + Lag) — is a crisp operational result, and the Pareto frontier framing of cost vs. SLO attainment is the right way to think about comparing policies.

The two frameworks are largely aligned. A few notes on how they relate:

**Violation cost vs. violation counting.** Lionel's attainment metric counts the fraction of requests meeting SLO — binary per request. This treats a 1ms miss the same as a 10-second collapse, and an out-of-envelope request the same as an in-envelope request. The graduated penalty model here distinguishes severity (how badly SLO was missed) and region (whether the miss was the autoscaler's fault or a consequence of load exceeding the envelope contract). This gives a fairer score and a richer picture of system behavior under stress.

**Envelope shape.** Lionel's optimal-static baseline implicitly assumes a fixed sustainable rate (the worst moment in the trace drives sizing). The envelope model here constrains the *growth rate* of arriving work — which reflects how autoscalers actually fail: not from sustained high load (they adapt) but from load that ramps faster than the provisioning lag allows.

**Combined score vs. Pareto frontier.** Lionel separates cost (capture ratio) from SLO attainment and plots a Pareto frontier. This framework combines them into a single score using a calibration factor derived from the benchmark itself. Both approaches are valid; the combined score requires a choice of weighting but produces a single comparable number.

**Admissibility.** Lionel's framework implicitly treats the trace as always in-envelope. This framework makes the admissibility region explicit and evaluates in-envelope and out-of-envelope behavior under different standards — important for real deployments where workloads occasionally exceed the design envelope.

**Work-based measurement.** Lionel's scoring uses request count. For LLM workloads with heterogeneous prompt and output lengths, request count introduces bias. This framework uses measured work (tokens or service time) as the primary unit throughout.

**Two-phase characterization.** Lionel's framework describes how to evaluate a policy given a trace but does not specify how to construct the trace. The benchmark construction step here produces the workload trace independently of any policy, preventing circular evaluation.

**Black-box principle.** Lionel correctly identifies KV utilization as the right autoscaler *signal*. This framework keeps internal metrics off the *evaluation* side — the evaluator uses only client-visible TTFT and work data from benchmark construction — keeping it portable to systems that don't expose internal KV state.

*Further discussion needed: how to compare the two frameworks on a concrete benchmark example.*
