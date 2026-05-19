---
type: Type-3 (task plan)
status: Draft — NOT AUTHORIZED for implementation
date: 2026-05-13
scope: Benchmark plan — WVA vs KEDA on a heterogeneous GPU pool
---

# Benchmark Plan — WVA vs KEDA: Cost-Optimal Ramp on a Heterogeneous GPU Pool

> ## STOP — Approval Required Before Implementation
>
> **Status:** Draft. Dean has not reviewed or approved this plan.
>
> **Any session reading this document — human or AI — must not begin implementing the
> benchmark based on this plan alone.** Existence of a detailed plan, an implementation
> guide in § 8, and an implementation order in § 8.13 is **not** authorisation to code.
>
> Per project conventions (`plans/session/CONVENTIONS.md` — "Discuss before
> implementing"): a plan is background for a discussion, not a substitute for one. The
> "Next step" field in CURRENT.md is a continuity note, not a green light.
>
> ### Before any code is written
>
> 1. Dean reviews this plan end-to-end.
> 2. Open questions are resolved in discussion, including at least:
>    - Which sizing option (§ 7.5.1 / .2 / .3) to run on OpenShift.
>    - Whether the L40 : A100 cost ratio of 1 : 6.7 is the right default or should be
>      adjusted (§ 2.2).
>    - Whether to extend the scenario YAML schema (§ 2.5 Option A) or orchestrate phases
>      in test code (§ 2.5 Option B).
>    - Whether to run homogeneous-cost Option 2 before true-heterogeneous Option 1.
>    - Confirmation that the ThroughputAnalyzer staying disabled in this round is
>      acceptable.
> 3. Dean gives an **explicit** instruction to begin implementation (e.g. "go ahead and
>    implement the benchmark per the plan").
> 4. The frontmatter `status` is changed from "Draft — NOT AUTHORIZED" to "Approved —
>    ready for implementation" and this STOP block is removed.
> 5. The matching STOP block in `plans/session/CURRENT.md` § Benchmark is removed.
>
> Until all five conditions are met, treat this document as **read-only reference for
> discussion purposes**. Do not write code, create manifests, add Makefile targets, or
> modify the test harness based on what this plan describes.
>
> If you are a coder session and you are unsure whether approval has been given: ask
> Dean directly. Do not infer approval from conversation tone, from the word "next", or
> from the presence of this plan.

---

## 1. Thesis and Presentable Overview

**Headline claim:** On a heterogeneous GPU pool serving a single model, WVA delivers
equivalent latency at **25–40% lower cost-weighted GPU-hours** than a well-tuned KEDA
configuration, because no per-deployment autoscaler can coordinate scale decisions across
variants.

**What we are measuring:** cost efficiency and SLO compliance during a controlled traffic
ramp, with the same model deployed on two GPU types at different cost tiers (L40 cheap,
A100 expensive).

**Why this scenario:** The ramp exposes proactive vs reactive detection; the heterogeneous
pool exposes cross-variant cost optimization; the scale-down phase exposes variant
selection for cost removal. These three dimensions are the full story of what WVA does
that HPA/KEDA cannot.

**Why this comparison:** Naive KEDA (one queue-depth trigger) is a strawman. The defensible
comparison is KEDA with the same rich vLLM metrics WVA consumes — KV%, queue depth, ITL
p99, token arrival rate — with tuned stabilization windows. Three systems are compared:
WVA, KEDA-naive, KEDA-tuned.

**Headline metric:** `cost_weighted_gpu_hours × slo_violation_multiplier`. Secondary:
p99 ITL during ramp, time-to-first-new-replica-Ready, peak replica count.

**One-line result (hypothesis):** WVA uses 25–40% fewer cost-weighted GPU-hours at
equivalent or better p99 ITL. The gap against KEDA-naive is larger (40–60%) and driven by
both cost and latency. The gap against KEDA-tuned is dominated by cost, with only a small
latency edge during the ramp.

**Second dimension — multi-tenant coordination (Scenario 2, § 12).** Under a partitioned
GPU pool with a premium tenant constrained to one partition, WVA's cost-optimal scaling
steers a basic tenant's workload away from the premium partition — preventing starvation
structurally, without cross-autoscaler coordination. KEDA's best countermeasure
(hard-capping basic-tenant replicas on the premium partition) protects the premium tenant
but hurts the basic tenant's own scale-up latency. WVA achieves both.

**This document covers two benchmark scenarios.** § 2–9 describe **Scenario 1** (the cost
argument). § 12 describes **Scenario 2** (the starvation / multi-tenant argument). They
share the implementation infrastructure (§ 8) but have distinct traffic patterns, variant
topologies, and expected results.

---

## 2. Scenario 1 — Cost-Optimal Ramp (design)

### 2.1 Infrastructure

| Item | Value |
|---|---|
| Cluster | OpenShift with H100/A100/L40 nodes (same cluster already used for `docs/developer-guide/benchmark-guide.md`) |
| Model | `meta-llama/Llama-3.1-8B-Instruct` |
| llm-d release | v0.6.0 |
| Gateway / EPP | `gaie-inference-scheduling-epp` (same as existing benchmark) |
| Prometheus / Grafana | existing `workload-variant-autoscaler-monitoring` stack |

### 2.2 Variants and Pricing

Two deployments of the same model, one per GPU type:

| Variant | GPU | cost-weight | min–max replicas | Rationale |
|---|---|---|---|---|
| `llama8b-l40` | NVIDIA L40 (48 GB) | 15 | 1–2 | Cheap; hardware-capped at 2 nodes; barely covers peak alone |
| `llama8b-h100` | NVIDIA H100-80GB | 65 | 1–3 | Expensive; overflow only; WVA minimises its use |

**Cost-weight rationale (retail pricing).** The cost-weight is arbitrary integer units
used by WVA's optimizer; only the ratio between variants matters. Values chosen to
approximate retail on-demand cloud pricing in 2026:

| GPU | Retail on-demand ($/hr, approx) | cost-weight used | Memory BW |
|---|---|---|---|
| NVIDIA L40 (48 GB) | ~$1.50 | 15 | ~864 GB/s GDDR6 |
| NVIDIA H100-80GB SXM | ~$6.50 | 65 | ~3,350 GB/s HBM3 |

Cost ratio L40:H100 = 15:65 = **1:4.3**. This is the ratio that determines the
headline cost advantage; higher ratios produce wider gaps. A sensitivity run with
different weights is not needed — the hardware cost differential is already large.

**Per-replica decode throughput (Llama-3.1-8B, 1000 in / 4000 out, target ITL < 60 ms).**
Throughput in decode-heavy workloads scales roughly with memory bandwidth:

| GPU | Approx tokens/sec | Approx RPS at SLO |
|---|---|---|
| NVIDIA L40 | ~14,000 | ~12 RPS |
| NVIDIA H100-80GB | ~24,000 | ~20 RPS |

These are conservative estimates; actual values depend on batch size and KV pressure.
They feed the KEDA-tuned arrival-rate trigger thresholds (§ 4.2) and set the "barely
absorbs peak" constraint below.

**The pool is hardware-constrained so L40 alone barely covers peak.**
Peak = 25 RPS. With max_L40 = 2 (only 2 L40 nodes in the cluster):
  2 replicas × 12 RPS = 24 RPS ≈ 25 RPS target.

At peak the L40 pool operates at ~100% utilisation — KV cache fills, ITL approaches the
SLO boundary. A single H100 replica (min=1) provides the overflow headroom:
  2 L40 + 1 H100 = 24 + 20 = 44 RPS effective capacity at the SLO target.

This constraint is **hardware-imposed**, not an artificial `maxReplicas` cap. The
"barely covers peak" property is what makes the WVA-vs-KEDA cost difference visible: at
peak load the L40 KV% exceeds KEDA's trigger threshold, causing KEDA to defensively
scale up H100 even though the SLO is already met. WVA's queueing model knows the SLO
is satisfied and holds H100 at minimum.

### 2.2a Per-Phase Behavior: WVA (saturation_v2) vs KEDA with L40 + H100

This section traces each phase with the accurate saturation_v2 mechanism. All systems
start at L40=1, H100=1 (min replicas).

**How saturation_v2 differs from KEDA's per-variant thresholds**

saturation_v2 computes an **aggregate** demand/supply ratio across ALL variants:
```
totalDemand         = Σ (TokensInUse + QueueLength × AvgInputTokens) across all replicas
totalAnticipatedSupply = Σ (ReadyReplicas + PendingReplicas) × PerReplicaCapacity
```
Scale-up fires when `totalDemand / totalAnticipatedSupply > 0.85`. Critically,
**pending replicas count in the supply estimate** — a replica being started is already
factored into the anticipated capacity. The optimizer then distributes required capacity
to the cheapest variant (L40=15) before the expensive one (H100=65).

KEDA has two independent ScaledObjects. Each fires on its own variant's KV% > 0.70,
with no visibility into the other variant's state or pending replicas.

---

**Phase 0 — Baseline (3 RPS, 5 min)**

Both systems idle at L40=1, H100=1. Token demand is low (~25% utilization). v2 begins
accumulating k2 observations but does not act. No difference.

---

**Phase 1 — Ramp (3 → 25 RPS staircase, 7 min)**

*Step: L40 hits capacity (~12 RPS with 1 replica):*

L40 replica queue fills (`queueLength ≥ 5`). EPP starts routing overflow to H100.

- **WVA (v2):** `totalDemand / totalAnticipatedSupply > 0.85` → fires. Optimizer adds
  capacity to L40 first (cost=15). L40 scales 1→2 (pending, ~90s startup). v2 includes
  the pending L40 replica in `totalAnticipatedSupply` → aggregate drops below 0.85 →
  **H100 stays at 1** ✓
- **KEDA-naive:** L40 queue depth fires the L40 ScaledObject → L40 scales 1→2. H100
  ScaledObject also sees rising KV% (EPP routed overflow there) → **H100 scales 1→2**
  during the ~90s L40 startup window.
- **KEDA-tuned:** Same as naive for H100: L40 ScaledObject fires; H100 ScaledObject
  fires independently because H100 KV% > 0.70 while L40 is pending → **H100 scales
  1→2** prematurely. After L40 comes online, H100 is over-provisioned but the 180s
  stabilisation window prevents immediate scale-down.

*This pattern repeats at each staircase step.* KEDA fires H100 at every transition
where L40 is pending; WVA suppresses it each time.

---

**Phase 2 — Peak (25 RPS, 10 min)**

With L40=2, H100=1 and capacity-proportional EPP routing:
- Pool utilization = 25/44 = **57%** → well below both v2's 0.85 and KEDA's 0.70
- **Both WVA and KEDA-tuned stabilise at L40=2, H100=1**

The steady-state replica count at 25 RPS peak is the same for all three systems. The
cost difference at Phase 2 steady state is **zero** — it all occurs at ramp and drop.

| | L40 | H100 | Cost/interval (steady state) |
|---|---|---|---|
| **WVA** | 2 | 1 | 2×15 + 1×65 = **95** |
| **KEDA-naive** | 2 | 1–2 | **95–160** (settling after ramp spike) |
| **KEDA-tuned** | 2 | 1–2 | **95–160** (settling after ramp spike) |

KEDA reaches H100=1 eventually (180s stabilisation window after each premature spike),
but pays the extra H100-hours during the transition.

---

**Phase 3 — Drop (25 → 3 RPS, 8 min)**

- **WVA:** `spareCapacity = totalSupply − totalDemand / 0.70 > 0` signals immediately
  as load falls. Optimizer releases H100 first (cost-ordered), then L40 once spare
  capacity covers both.
- **KEDA-naive/tuned:** H100 ScaledObject has a 180 s stabilisation window → holds
  H100 at its current count for 3 min after load drops.

---

**Cost summary (cost-units × minutes, normalized to WVA=1.00)**

The cost gap comes from two sources: (A) KEDA H100 spikes during each ramp transition
(~90s premature H100=2 + 180s stabilisation to scale back), and (B) scale-down lag.

| Phase | WVA | KEDA-naive | KEDA-tuned |
|---|---|---|---|
| P0 Baseline (5 min) | 1×15+1×65=80 | 80 | 80 |
| P1 Ramp — per step transient | H100=1 throughout | H100=2 for ~4–5 min | H100=2 for ~4–5 min |
| P2 Peak (10 min) | 95 | ~95 (settled) | ~95 (settled) |
| P3 Drop — lag | scale-down immediate | H100 holds 3 min extra | H100 holds 3 min extra |

Estimated cost advantage (directional): **~15–25%** over the full run. The gap is
real but modest at 25 RPS because steady-state is the same; it is larger at higher
peak loads where the ramp transitions are more frequent or deeper.

**What this benchmark demonstrates:** WVA's pending-replica awareness prevents
KEDA's "fire first, correct later" pattern at each ramp step. Combined with cost-ordered
scale-down, WVA accumulates significantly fewer expensive H100 GPU-hours over a
multi-phase run, despite reaching the same steady-state allocation at peak.

---

### 2.3 Traffic Pattern — Multi-Phase Ramp

```
  RPS
   25 |         .------------.
      |        /              \
   15 |       /                \
      |      /                  \
    3 |-----'                    '------
      |
      0     5    12      22    30 (min)
           ^ramp  ^peak   ^drop
```

| Phase | Duration | RPS | Purpose |
|---|---|---|---|
| P0 Baseline | 5 min (300s) | 3 | Warm up; VA registers metrics; let both autoscalers settle |
| P1 Ramp | 7 min (420s) | linear 3 → 25 | Exposes proactive vs reactive detection |
| P2 Peak | 10 min (600s) | 25 | Exposes variant selection — WVA picks L40 |
| P3 Drop | 8 min (480s) | 3 | Exposes scale-down variant selection (A100 first for WVA) |

**Total run time:** 30 min per system × 3 systems = 90 min experiment time, plus ~15 min
per-system setup. Realistic half-day benchmark.

### 2.4 Workload Shape

**Decode-heavy**, matching the existing `scenarios/decode_heavy.yaml`:

| Parameter | Value |
|---|---|
| `promptTokens` | 1000 |
| `outputTokens` | 4000 |
| `profile` | poisson |
| `requestType` | text_completions |
| `maxSeconds` | see per-phase above |

Decode-heavy is chosen because (a) it stresses ITL, which is the WVA-modeled SLO
dimension, (b) KV cache fills gradually so the ramp window is long enough for proactive
detection to show an edge, (c) it is already an established scenario in the harness.

### 2.5 GuideLLM Workload Definition

The existing `WorkloadScenario` struct in `test/benchmark/workload.go` supports a **single**
phase (one `Rate`, one `MaxSeconds`). We need multi-phase. Two options; recommend option B.

**Option A — extend the schema** (more invasive, preferred long-term):

```yaml
# test/benchmark/scenarios/cost_optimal_ramp.yaml
name: "Cost-Optimal Ramp"
description: "Decode-heavy traffic ramp for WVA-vs-KEDA cost comparison"
promptTokens: 1000
outputTokens: 4000
profile: poisson
requestType: text_completions
phases:
  - { name: baseline, rate: 3,  maxSeconds: 300 }
  - { name: ramp,     rate: 15, maxSeconds: 420 }   # staircase midpoint
  - { name: peak,     rate: 25, maxSeconds: 600 }
  - { name: drop,     rate: 3,  maxSeconds: 480 }
```

**Option B — orchestrate in the Ginkgo test** (recommended for this PR):

Reuse the existing `Baseline → Spike → Sustained → Cooldown` phase scaffolding from
`scale_up_latency_benchmark_test.go`. Launch **four sequential GuideLLM jobs** with
different `rate` values. This is a staircase, not a linear ramp, but it is equally good
for exposing the proactive-vs-reactive difference — each step change is a mini-spike.
Advantage: no schema change, no harness refactor.

A staircase of four steps `(3, 10, 18, 25)` across the ramp phase is smoother than the
four-phase pattern above; choose based on fidelity needs. Baseline implementation:
three-step staircase (3 → 15 → 25 → 3) mapping directly onto the existing four phases.

**Guidellm invocation (per phase):** identical to `workload.go:CreateGuideLLMJobWithArgs`
but with `--max-seconds` set to the phase duration and `--rate` set to the phase RPS.
`--random-seed 42` is kept across phases for determinism.

### 2.6 One Open Question — Ramp vs Step Function

GuideLLM does not emit a linear ramp natively; the `sweep` profile sweeps
synchronous→throughput rates which is not what we want. The staircase approximation is
adequate for showing the **cost** difference (which is a steady-state argument across
Phase 2). It slightly understates the **latency** difference during P1 (a true linear
ramp would give reactive autoscalers more time to fall behind). If the latency story
turns out to be weaker than expected, file a follow-up to extend GuideLLM or chain more
step levels.

---

## 3. WVA Configuration

### 3.1 Analyzer Selection

Use **saturation_v2** (`analyzerName: "saturation"`) — the single, fully-ready analyzer
for this benchmark. Do not mix analyzers; this is not a multi-analyzer benchmark.

saturation_v2 is a token-based dual-capacity model:
- **k1** (memory-bound) = `TotalKvCapacityTokens × kvCacheThreshold` — the KV cache
  capacity in tokens up to the configured fraction.
- **k2** (compute-bound) = learned from queue-saturated observations: when
  `queueLength ≥ queueLengthThreshold`, the current `tokensInUse` is recorded as the
  compute limit. A rolling average per workload bucket (short/medium/long output) is
  maintained across observations and survives scale-down cycles.
- **effectiveCapacity = min(k1, k2)** — whichever bound is active for the current
  workload shape. This makes the analyzer correct for both decode-heavy (memory-bound,
  k1 dominates) and prefill-heavy (compute-bound, k2 dominates) traffic.
- **demand** = `TokensInUse + QueueLength × AvgInputTokens` (actual token pressure on
  a replica, not a percentage).
- **Scale-up** fires when `totalDemand / totalAnticipatedSupply > scaleUpThreshold`.
  **`totalAnticipatedSupply` includes pending (not yet Ready) replicas.** When L40
  replicas are starting up (60–90 s startup), v2 already counts their capacity in the
  supply estimate and suppresses premature H100 scale-up.
- **Scale-down** fires when `totalSupply − totalDemand / scaleDownBoundary > 0`.

The aggregate demand and supply are summed **across all variants** of the model.
The optimizer then distributes any required capacity to the cheapest variant first.

**Why saturation_v2 rather than v1:**
v1 uses KV% as a percentage threshold per replica and scales one replica at a time.
v2 uses absolute token counts and can scale by N replicas in one decision. It separates
memory-bound from compute-bound constraints via k1/k2, making it robust across workload
shapes. The pending-replica awareness in `totalAnticipatedSupply` is the key structural
property that prevents KEDA-like over-provisioning at ramp transitions.

Do **not** enable the ThroughputAnalyzer (TA) — TA3 has not merged. Re-run this
benchmark with TA enabled once PR-5 lands; the proactive ramp advantage will widen.

**Follow-up:** Once the QueueingModel analyzer is ready, re-run Scenario 1. The
QueueingModel knows exactly how many replicas meet the target SLO — it will hold H100
at minimum even at steady-state peak, producing a larger and more principled cost gap.

### 3.2 ConfigMap: `wva-saturation-scaling-config`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: wva-saturation-scaling-config
  namespace: workload-variant-autoscaler-system
data:
  default: |
    analyzerName:         saturation   # selects saturation_v2 token-based analyzer
    kvCacheThreshold:     0.80         # k1 = TotalKvCapacityTokens × 0.80
    queueLengthThreshold: 5            # queue depth above which k2 is observed
    scaleUpThreshold:     0.85         # scale up when demand/anticipatedSupply > 0.85
    scaleDownBoundary:    0.70         # scale down when demand/supply < 0.70
```

**Rationale:**
- `scaleUpThreshold: 0.85` means scale up when token demand exceeds 85% of anticipated
  token supply. At equilibrium without queue pressure, this corresponds to approximately
  KV% > 68% — slightly below KEDA-tuned's 70% KV threshold. The key difference is not
  the threshold level but the aggregate cross-variant view and pending-replica awareness.
- `scaleDownBoundary: 0.70` matches the scale-down boundary so the optimizer can release
  H100 replicas promptly once the load drops (cost-ordered release).
- `kvCacheThreshold: 0.80` is the fraction of the KV buffer treated as usable capacity
  (k1). Keeps a 20% headroom for burst requests.
- `queueLengthThreshold: 5` triggers k2 observation when the replica queue is non-trivial,
  updating the rolling average of compute-bound capacity for the decode-heavy workload bucket.

### 3.4 VariantAutoscaling Resources

Two VA resources, one per variant. Both target the same `modelID` so WVA sees them as
variants of one model and runs cross-variant optimization.

```yaml
# va-llama8b-l40.yaml
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: llama8b-l40
  namespace: llmd-bench
spec:
  modelID: "meta-llama/Llama-3.1-8B-Instruct"
  minReplicas: 1
  maxReplicas: 6
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ms-bench-llama8b-l40-decode
  accelerator:
    type: NVIDIA-L40-48GB
    cost: 15
---
# va-llama8b-h100.yaml
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: llama8b-h100
  namespace: llmd-bench
spec:
  modelID: "meta-llama/Llama-3.1-8B-Instruct"
  minReplicas: 1
  maxReplicas: 3
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ms-bench-llama8b-h100-decode
  accelerator:
    type: NVIDIA-H100-80GB-SXM
    cost: 65
```

### 3.5 HPA Integration

Per the existing pattern in `docs/user-guide/hpa-integration.md`: one HPA per variant
deployment, targeting `wva_desired_replicas` with `AverageValue: "1"`. HPA is a
pass-through; WVA makes the decision.

Use production behavior defaults from the Helm chart:
- `scaleUp.stabilizationWindowSeconds: 0` (WVA already smooths)
- `scaleDown.stabilizationWindowSeconds: 0` (WVA already smooths)

This is the standard integration; no experimental tuning here.

---

## 4. KEDA Baselines

### 4.1 Baseline A — KEDA-Naive (Strawman)

**Purpose:** Show what a team deploying KEDA with the first trigger they find does.

**Configuration per variant:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: llama8b-l40-scaler
  namespace: llmd-bench
spec:
  scaleTargetRef:
    kind: Deployment
    name: ms-bench-llama8b-l40-decode
  pollingInterval: 15          # KEDA default
  cooldownPeriod:  300         # KEDA default
  minReplicaCount: 1
  maxReplicaCount: 6
  triggers:
  - type: prometheus
    name: vllm-queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.workload-variant-autoscaler-monitoring.svc.cluster.local:9090
      query: |
        avg(vllm:num_requests_waiting{
          model_name="meta-llama/Llama-3.1-8B-Instruct",
          deployment="ms-bench-llama8b-l40-decode"
        })
      threshold: "3"
      metricType: AverageValue
      unsafeSsl: "true"
```

Same shape for `llama8b-a100-scaler` (different `deployment=` label, different
`maxReplicaCount: 3`).

**Why this is naive:**
- Single trigger on queue depth — the most obvious choice.
- No stabilization window → will oscillate during pod startup.
- No awareness of KV% or ITL.
- Critically, the two `ScaledObject`s are **completely independent** — both fire when load
  arrives, scaling in parallel.

### 4.2 Baseline B — KEDA-Tuned (Honest Competitor)

**Purpose:** Show what a careful operator tuning KEDA with the same vLLM metrics WVA uses
can achieve.

**Configuration per variant:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: llama8b-l40-scaler-tuned
  namespace: llmd-bench
spec:
  scaleTargetRef:
    kind: Deployment
    name: ms-bench-llama8b-l40-decode
  pollingInterval:        5
  cooldownPeriod:       120
  initialCooldownPeriod: 60
  minReplicaCount: 1
  maxReplicaCount: 6
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleUp:
          stabilizationWindowSeconds:  30   # light smoothing — preserve ramp responsiveness
          selectPolicy: Max
          policies:
          - { type: Pods, value: 2, periodSeconds: 60 }
        scaleDown:
          stabilizationWindowSeconds: 180   # protect against scaling-down during pod startup
          selectPolicy: Min
          policies:
          - { type: Pods, value: 1, periodSeconds: 120 }
  triggers:
  # KV cache headroom — primary reactive signal
  - type: prometheus
    name: vllm-kv-cache
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.workload-variant-autoscaler-monitoring.svc.cluster.local:9090
      query: |
        avg(vllm:gpu_cache_usage_perc{deployment="ms-bench-llama8b-l40-decode"})
      threshold: "0.70"
      metricType: AverageValue
      unsafeSsl: "true"
  # Queue depth — corroborating reactive signal
  - type: prometheus
    name: vllm-queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.workload-variant-autoscaler-monitoring.svc.cluster.local:9090
      query: |
        avg(vllm:num_requests_waiting{deployment="ms-bench-llama8b-l40-decode"})
      threshold: "3"
      metricType: AverageValue
      unsafeSsl: "true"
  # ITL p99 — SLO-facing signal (scales up when approaching SLO breach)
  - type: prometheus
    name: vllm-itl-p99
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.workload-variant-autoscaler-monitoring.svc.cluster.local:9090
      query: |
        histogram_quantile(0.99,
          sum by (le, deployment) (
            rate(vllm:time_per_output_token_seconds_bucket{
              deployment="ms-bench-llama8b-l40-decode"
            }[1m])
          )
        )
      threshold: "0.054"        # 54 ms — 90% of 60 ms SLO target
      metricType: Value
      unsafeSsl: "true"
  # Token arrival rate — proactive signal (approximates TA)
  - type: prometheus
    name: vllm-token-arrival-rate
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.workload-variant-autoscaler-monitoring.svc.cluster.local:9090
      query: |
        sum(rate(vllm:prompt_tokens_total{
          deployment="ms-bench-llama8b-l40-decode"
        }[30s]))
        /
        count(kube_pod_info{
          pod=~"ms-bench-llama8b-l40-decode-.*",
          pod_ip!=""
        })
      threshold: "4000"         # tokens/sec/replica — hand-tuned near per-replica capacity
      metricType: AverageValue
      unsafeSsl: "true"
```

**Per-variant differences:**
- L40 variant: `threshold: "4000"` on arrival rate (L40 per-replica capacity).
- A100 variant: `threshold: "12000"` on arrival rate (A100 is ~3× throughput).
- ITL threshold is the same (it's an SLO, not a capacity).
- `maxReplicaCount`: 6 on L40, 3 on A100.

**KEDA trigger combination semantics:** KEDA takes the **maximum** scale target across
triggers (any-up logic). This matches WVA's combine algorithm for scale-up. That is
intentional — we're giving KEDA the same composition WVA uses internally.

### 4.3 Discussion — Why These Configurations

**Why KEDA-naive uses only queue depth:**
`vllm:num_requests_waiting` is the canonical KEDA trigger for LLM workloads in online
docs and community posts. Operators reach for it first. The threshold `3` matches the
WVA saturation default `queueLengthThreshold: 5` (with a bit of headroom). This is a fair
representation of "what a team would try first."

**Why KEDA-tuned uses four triggers:**
The four triggers map to the four signals WVA's analyzers internally consider:
- KV cache utilization ↔ saturation analyzer KV signal
- Queue depth          ↔ saturation analyzer queue signal
- ITL p99              ↔ queueing model SLO target
- Token arrival rate   ↔ throughput analyzer demand rate

By giving KEDA access to the same information, we isolate WVA's remaining advantages to
**cross-variant coordination** and **prospective sizing** — the architectural claims, not
the metric-access claims.

**Why the tuned stabilization windows are asymmetric (30s up, 180s down):**
Scale-up needs responsiveness to keep p99 ITL bounded during the ramp. Scale-down needs
patience to avoid flapping during pod startup (model-load time is 2–7 min on real
hardware). 180s on scale-down closes most of the cascade-prevention gap vs WVA's
transition blocking — this is an honest concession and should be documented as such.

**Why `threshold: "0.70"` on KV cache (not `0.80` like WVA saturation):**
KEDA-tuned's KV threshold is intentionally *tighter* than WVA's saturation threshold
(0.70 vs 0.80). This gives KEDA-tuned an earlier scale-up signal to compensate for the
lack of proactive rate detection. It is a tuning concession in KEDA's favor. If the
numbers still favor WVA at 0.70, the story is even stronger at 0.80.

**Why `histogram_quantile` is risky:**
ITL p99 from histogram buckets is noisy over 1-minute windows at low RPS. Expect
KEDA-tuned to have some flap during the Baseline phase (3 RPS) where the histogram is
sparse. This is a real operational cost of reactive SLO targeting — include it in the
narrative.

**Where KEDA still cannot match WVA:**
- **Cross-variant cost selection.** Both `ScaledObject`s will scale their deployments in
  parallel because they see the same signals rising. No KEDA configuration changes this.
  The only workaround is artificially detuning the A100 scaler (e.g., threshold 0.90 on
  KV), but this also delays A100 scale-up when it is genuinely needed for traffic L40
  cannot handle — a manual, brittle trade-off.
- **Scale-down cost selection.** When traffic drops, KEDA-tuned will scale down whichever
  variant's metrics drop below threshold first. There is no "prefer to remove A100"
  primitive. WVA removes the most expensive variant first by construction.

### 4.4 Not Testing — Naive HPA on CPU

We do not include a baseline HPA on CPU/memory. vLLM inference is GPU-bound; host CPU
stays near idle regardless of load. This baseline would fail trivially and is not
instructive. Mention in the report as a footnote.

---

## 5. Metrics and Data Capture

All metrics are collected at 15-second resolution for the full 30-minute run per system.

### 5.1 What the Existing Harness Already Produces

Mapping of the existing `PrefillResult` struct (`test/benchmark/hpa_helpers.go`) and
harness plumbing onto what this benchmark needs:

| Field / capability | Source | Applies as-is? |
|---|---|---|
| `ReplicaTimeline []ReplicaSnap` (15s spec+ready counts) | `prefill_heavy_benchmark_test.go` monitor loop | **Needs per-variant split** (currently one aggregate) |
| `MetricsTimeline []MetricSnap` (15s KV%, vLLM queue, EPP queue) | Prometheus `vllm:kv_cache_usage_perc`, `vllm:num_requests_waiting`, `inference_extension_flow_control_queue_size` | **Needs per-variant split** |
| `TTFT`, `ITL`, `Throughput` as `{p50, p90, p99}` JSON | Extracted from GuideLLM's output JSON | Yes, direct |
| `AvgReplicas`, `MaxReplicas`, `AvgKVCache`, `AvgQueueDepth`, `AvgEPPQueueDepth` | Prometheus range queries in `QueryRangeAvg` | Yes; need per-phase versions |
| `AchievedRPS`, `ErrorCount`, `IncompleteCount` | GuideLLM output JSON | Yes, direct |
| `Pods []PodInfo{Name, Node, GPU, StartupSec}` | Pod status + node labels (`nvidia.com/gpu.product`) | Yes — already splits by GPU type via the `GPU` field |
| Grafana snapshot URL + full JSON + per-panel PNGs | `grafana.go::GrafanaClient` + `BENCHMARK_GRAFANA_ENABLED=true` | Yes, direct (can import snapshot later) |
| Output file `/tmp/prefill-benchmark-results.json` | `captureResultsAndGrafana` | Yes; rename output per-run |

**What already works out-of-the-box:** all headline measurements (replica counts, vLLM
metrics, TTFT/ITL/throughput percentiles, GPU mapping per pod, Grafana capture) are
captured by the existing harness. The only thing fundamentally missing is **per-variant
separation** — the harness assumes one deployment, one variant.

### 5.2 Primary Headline Metrics (this benchmark)

| Metric | Formula | What it shows |
|---|---|---|
| **Cost-weighted GPU-hours** | `Σ_t Σ_v replicas_v(t) × cost_v × Δt / 3600` | Headline cost number |
| **P99 ITL (ms)** per phase | `histogram_quantile(0.99, vllm:time_per_output_token_seconds)` | SLO compliance |
| **SLO violation rate** | fraction of requests with `ITL > 60ms` | Quality impact |

### 5.3 Diagnostic Metrics

| Metric | What it shows |
|---|---|
| P50/P90 TTFT and ITL per phase | Distribution shape |
| Time-to-first-new-replica-Ready from Phase 1 start | Proactive vs reactive detection |
| Peak replica count per variant | Over-provisioning indicator |
| Replica timeline per variant (L40 + A100 count vs time) | **Key visual** — the cost-optimization story |
| KV cache utilization per variant | Shows which variant is actually loaded |
| Error count and incomplete-request count | Correctness |
| Achieved RPS vs offered RPS | Load-generator health check |

### 5.4 Harness Changes Needed for Results Collection

Four additions to the existing `test/benchmark/` package:

1. **Per-variant timeline split** — replace the single `ReplicaTimeline` /
   `MetricsTimeline` with a map keyed by deployment name:

   ```go
   type VariantTimeline struct {
       DeploymentName  string          `json:"deployment_name"`
       GPUType         string          `json:"gpu_type"`
       CostWeight      float64         `json:"cost_weight"`
       ReplicaTimeline []ReplicaSnap   `json:"replica_timeline"`
       MetricsTimeline []MetricSnap    `json:"metrics_timeline"`
   }

   type RampResult struct {
       AutoscalerMode       string             `json:"autoscaler_mode"` // wva|keda-naive|keda-tuned
       Variants             []VariantTimeline  `json:"variants"`
       Phases               []PhaseResult      `json:"phases"`         // one per benchmark phase
       CostWeightedGPUHours float64            `json:"cost_weighted_gpu_hours"`
       // ... TTFT / ITL / Throughput carried over from PrefillResult
   }
   ```

   The monitor loop in `prefill_heavy_benchmark_test.go:509–608` already lists
   deployments and samples per-deployment — the change is to segregate timelines by
   deployment name, not aggregate them.

2. **Per-phase segmentation** — the harness already knows phase start/end times (it
   controls them). Add a helper `segmentByPhase(snaps []MetricSnap, phases []Phase)
   []PhaseResult` that slices the full timeline and computes p50/p90/p99 per phase from
   the GuideLLM output of that phase's job.

3. **Cost-weighted GPU-hour aggregator** — compute from per-variant `ReplicaTimeline`
   and `cost_weight`:

   ```go
   func CostWeightedGPUHours(variants []VariantTimeline) float64 {
       var total float64
       for _, v := range variants {
           for i := 1; i < len(v.ReplicaTimeline); i++ {
               dt := v.ReplicaTimeline[i].ElapsedSec - v.ReplicaTimeline[i-1].ElapsedSec
               total += float64(v.ReplicaTimeline[i-1].SpecReplicas) * v.CostWeight * dt / 3600.0
           }
       }
       return total
   }
   ```

4. **Cross-system comparison report generator** — new file `hack/compare-ramp-results.py`
   that reads three JSON files and emits:
   - a markdown summary table (per-phase p99 ITL, SLO violation rate, cost-weighted
     GPU-hours, peak replicas per variant);
   - three replica-timeline stacked-area PNGs (one per system);
   - one cost-vs-latency scatter PNG;
   - one overlay p99-ITL-vs-time PNG.
   Uses matplotlib; no Go required. ~150 LOC.

**What to keep unchanged:** Grafana snapshot capture, GuideLLM JSON parsing, Prometheus
range-query wrapper, pod→GPU mapping. These work as-is across variants.

### 5.5 Visualizations to Produce

1. **Replica timeline stacked chart** — L40 replicas (green) + A100 replicas (red) on a
   shared time axis, one subplot per system (WVA, KEDA-naive, KEDA-tuned). This is the
   money shot: WVA should show a flat A100=1 across the peak, with L40 climbing to 5–6;
   KEDA-tuned will show both climbing in parallel.
2. **Cost-weighted replica-hours bar chart** — one bar per system, stacked by variant.
3. **P99 ITL time series** — three overlay lines, one per system. Expect WVA and
   KEDA-tuned close; KEDA-naive visibly higher during Phase 1 ramp.
4. **Cost vs Latency scatter** — one point per system. The Pareto frontier point is the
   claim.

### 5.6 Data Flow End-to-End

```
 GuideLLM (per phase)         Monitor loop (every 15s)          Phase boundaries
       │                              │                                │
       ▼                              ▼                                ▼
  JSON output      Prometheus range queries + deployment list    timestamps
       │                              │                                │
       └──────────┬───────────────────┴────────────────┬───────────────┘
                  ▼                                    ▼
           PrefillResult per phase          VariantTimeline[] (one per deployment)
                          │                          │
                          └────────────┬─────────────┘
                                       ▼
                              segmentByPhase + CostWeightedGPUHours
                                       ▼
                  /tmp/ramp-results-{wva,keda-naive,keda-tuned}.json
                                       │
                                       ▼
                       hack/compare-ramp-results.py → markdown + PNGs
```

Every system run reuses the same harness path; only `AUTOSCALER_MODE=...` changes which
scaler resources get created in the `SetupTwoVariantScenario` fixture.

---

## 6. Kind-Emulator Dry-Run (Run This First)

Before burning OpenShift GPU time, run the full three-system suite on the kind-emulator.
Purpose: **verify the pipeline, not produce publishable numbers.** The emulated vLLM pods
return synthetic metrics, so absolute latency numbers are meaningless; the **relative
behaviour of autoscalers and the per-variant replica counts are valid.**

### 6.1 Kind Environment

Kind-emulator is already used for e2e tests. Setup via `deploy/kind-emulator/setup.sh`
with two worker nodes configured with different simulated GPU labels:

```bash
# Bring up a two-worker kind cluster; each worker simulates a different GPU type
ENABLE_SCALE_TO_ZERO=false \
  ./deploy/kind-emulator/setup.sh

# Label workers so the Gaudi / A100 / MI300X emulator set matches our two-variant test.
# The kind-emulator install already registers A100 and MI300X accelerators — we repurpose:
#   worker  → A100  (expensive)
#   worker2 → labeled as L40 (cheap)
kubectl label node kind-inferno-gpu-cluster-worker  nvidia.com/gpu.product=NVIDIA-A100-PCIE-80GB --overwrite
kubectl label node kind-inferno-gpu-cluster-worker2 nvidia.com/gpu.product=NVIDIA-L40-48GB --overwrite
```

### 6.2 What the Kind Run Validates

| Check | Pass criterion |
|---|---|
| Two VAs with same `modelID` are both registered by WVA | `kubectl get va -n llm-d-sim` shows both; optimizer log prints two variants |
| WVA optimizer makes **cross-variant** decisions | Optimizer log shows `accelerator: L40` in cheapest-variant selection when both variants have capacity |
| KEDA ScaledObjects (both flavours) reach `READY=True` | `kubectl get scaledobject -n llm-d-sim` |
| Multi-phase GuideLLM orchestration works end-to-end | Four sequential jobs complete without error; timeline has four distinct rate regimes |
| Per-variant timeline split captures both deployments | Result JSON contains 2 entries in `variants[]`, each with its own `replica_timeline` |
| Cost-weighted GPU-hours aggregator produces sane numbers | Three systems produce distinct values; `wva < keda-tuned < keda-naive` |
| Grafana snapshot is captured for each system run | Three snapshot URLs saved to `/tmp/benchmark-grafana-snapshot-*.txt` |

### 6.3 Kind Compressed Timeline

Kind runs faster than OpenShift because pod startup is ~30s (emulator) vs 2–7 min (real
vLLM). Use a compressed version of the traffic pattern:

| Phase | Kind duration | OpenShift duration |
|---|---|---|
| P0 Baseline | 60s | 300s |
| P1 Ramp | 180s | 420s |
| P2 Peak | 240s | 600s |
| P3 Drop | 180s | 480s |
| **Total per system** | **~11 min** | **~30 min** |

Three systems on kind = ~35 min wall time total. Fits in a single development cycle.

### 6.4 Kind-Specific Caveats

- **Latency numbers are synthetic.** The emulator returns fabricated TTFT/ITL values.
  Use kind to validate the orchestration and **relative replica counts**; do not report
  kind latency numbers.
- **EPP metrics may not populate.** Flow control and some EPP queue metrics are gated on
  real llm-d EPP v0.5.0+ being present. Run with `E2E_TESTS_ENABLED=true` and the EPP
  v0.5.0 patch per `CURRENT.md § Known infra issues` to keep them alive.
- **Cost-weight behaviour is real.** The WVA optimizer runs the same code path on kind
  as on OpenShift. If WVA correctly picks L40 on kind, it will correctly pick L40 on the
  real cluster. This is the main reason the kind dry-run is valuable.
- **KEDA needs to be installed in the kind cluster.** `helm install keda kedacore/keda
  -n keda-system --create-namespace` — the same command as OpenShift.

### 6.5 Kind Makefile Target

Add a new target that runs the same Ginkgo suite with kind-specific overrides:

```makefile
.PHONY: test-cost-optimal-ramp-kind
test-cost-optimal-ramp-kind: manifests generate fmt vet
	BENCHMARK_BASELINE_DURATION=60 \
	BENCHMARK_SPIKE_DURATION=180 \
	BENCHMARK_SUSTAINED_DURATION=240 \
	BENCHMARK_COOLDOWN_DURATION=180 \
	ENVIRONMENT=kind-emulator \
	LLMD_NS=llm-d-sim WVA_NS=workload-variant-autoscaler-system \
	go test ./test/benchmark/ -run TestCostOptimalRamp -timeout 90m -v
```

### 6.6 Kind Success Criteria (Go/No-Go for OpenShift)

Only proceed to the OpenShift run if **all** of the following hold on kind:

1. All three systems complete their full phase sequence without timeout or pod crashes.
2. The per-variant replica timeline clearly differs between WVA and KEDA-tuned — WVA
   should show lopsided L40-heavy allocation, KEDA-tuned should show roughly proportional
   scaling.
3. Cost-weighted GPU-hours strictly orders `wva < keda-tuned < keda-naive`.
4. The comparison script produces the four PNGs without manual intervention.

If any of these fails, fix the harness / WVA config before spending OpenShift budget.

---

## 7. Execution Plan

### 7.1 Code Changes Required

Estimated effort in parentheses.

1. **New scenario file** `test/benchmark/scenarios/cost_optimal_ramp.yaml` with multi-phase
   rates. Optionally extend `WorkloadScenario` struct; otherwise orchestrate in test code. (S)

2. **New test file** `test/benchmark/cost_optimal_ramp_benchmark_test.go` modeled on
   `scale_up_latency_benchmark_test.go` with four phases (Baseline / Ramp / Peak / Drop)
   and a per-phase GuideLLM invocation. (M)

3. **Variant setup helpers** — a `SetupTwoVariantScenario` fixture that creates both
   deployments (L40 and A100 flavors of `meta-llama/Llama-3.1-8B-Instruct`), both VAs, both
   HPAs, and both KEDA ScaledObjects. Mode is switched via env var
   `AUTOSCALER_MODE=wva|keda-naive|keda-tuned`. (M)

4. **KEDA manifests** in `config/samples/keda/benchmark-ramp/`:
   - `scaledobject-naive-l40.yaml`, `scaledobject-naive-a100.yaml`
   - `scaledobject-tuned-l40.yaml`, `scaledobject-tuned-a100.yaml`
   - `README.md` explaining both configurations and the tuning rationale. (S)

5. **Cost-weighted metric aggregation** — extend `hpa_helpers.go::PrefillResult` with
   per-variant breakdown and `CostWeightedGPUHours` field. Sum in `results.go`. (S)

6. **New Makefile targets**:
   - `test-cost-optimal-ramp-kind` — compressed-duration dry-run on kind (see § 6.5)
   - `test-cost-optimal-ramp` — full-duration run on OpenShift, three systems sequential (S)

7. **Comparison report generator** — shell or Python script that reads the three JSON
   outputs and emits a markdown summary + PNG plots. Lives in `hack/`. (M)

Total: estimate **1–2 engineer-days** for code, plus experiment time.

### 7.2 Experimental Protocol

One half-day run per system, sequential (not parallel — shared cluster):

1. Day -1: **run the kind dry-run** (§ 6) and confirm all four Go/No-Go criteria pass.
2. Morning: full WVA run on OpenShift (30 min + 15 min setup).
3. Midday: full KEDA-naive run.
4. Afternoon: full KEDA-tuned run.
5. Next day: generate comparison report, write results into `docs/benchmark.md`.

**Run each system twice** and pick the median on the primary metric (cost-weighted
GPU-hours). LLM serving benchmarks are noisy; one run is not enough for publishable
numbers.

### 7.3 Prerequisites (Software)

- KEDA installed (`helm install keda kedacore/keda -n keda-system --create-namespace`).
- Prometheus stack already running (`workload-variant-autoscaler-monitoring` namespace).
- Prometheus Adapter configured to expose `wva_desired_replicas` — required for the WVA
  run; not needed for the KEDA modes (they target raw vLLM metrics).
- `cost: 6` (L40) and `cost: 40` (A100) values registered in WVA's accelerator-cost
  ConfigMap. A100 is already present; L40 needs to be added.
- HuggingFace token with access to `meta-llama/Llama-3.1-8B-Instruct`.
- EPP v0.5.0 patch applied per `CURRENT.md § Known infra issues`.

### 7.4 Platform Support — Kind and OpenShift

The benchmark is designed to run on **both** environments from the same Go source. Kind
is used for pipeline validation; OpenShift is used for publishable numbers. Toggle with
the `ENVIRONMENT` env var (`kind-emulator` or `openshift`) consumed by
`testconfig.LoadSharedConfig`.

| Aspect | Kind dry-run | OpenShift real run |
|---|---|---|
| Ginkgo suite | same file, `test-cost-optimal-ramp-kind` target | `test-cost-optimal-ramp` target |
| Phase durations | compressed (60 / 180 / 240 / 180s) | full (300 / 420 / 600 / 480s) |
| Model server | vLLM simulator pod (emulator) | real vLLM with real Llama-3.1-8B |
| GPU allocation | simulated via node labels only | real GPU scheduling |
| Latency numbers | **synthetic — do not publish** | **real — measurable in ms** |
| Replica-count behaviour | **real** (same optimizer path) | **real** |
| Cost-weighted GPU-hours | **real** (arithmetic on replica counts) | **real** |
| Autoscaler verification | all three modes | all three modes |
| Runtime per system | ~11 min | ~30 min |
| Total runtime (3 systems × 2 repeats) | ~70 min | ~3.5 hr |

The Go source is identical across environments; only env vars and actual GPU availability
differ.

### 7.5 OpenShift Resource Sizing

Three sizing options, in increasing order of realism and cost.

#### 7.5.1 Option 1 — True Heterogeneous GPUs (publishable headline numbers)

GPU worst-case occurs during Phase 2 peak under KEDA-naive (the over-provisioner).

| Resource | Minimum | Headroom target | Notes |
|---|---|---|---|
| **NVIDIA L40 GPUs** | 6 | 7–8 | One per L40 replica at `maxReplicas=6` |
| **NVIDIA A100-80GB GPUs** | 3 | 4 | One per A100 replica at `maxReplicas=3` |
| CPU (total worker capacity) | ~50 cores | 64 cores | 4–8 per vLLM pod × up to 9 pods + overhead |
| RAM (total worker capacity) | ~200 GB | 256 GB | ~24 GB per vLLM pod + system |
| Ephemeral / PVC storage | 100 GB | 200 GB | Model weights cache + image pulls |
| Control-plane / infra | standard OpenShift | — | WVA, Prometheus, EPP, Gateway, KEDA all fit on existing infra |

Cloud-equivalent: roughly 6× AWS `g6.xlarge` (1 L40 each) + 1× `p4de.24xlarge` (8
A100-80GB, only 3 used). On-premise equivalent: 2–3 worker nodes each with 3–4 L4s, and
1 node with 3–4 A100-80GBs.

Phase-0 baseline uses 2 GPUs (1 per variant, min replicas). Peak Phase 2 ramps to up to
9 GPUs under KEDA-naive, 7 under KEDA-tuned, 6 under WVA. Averaged across the 30-min
run ≈ 4–5 GPUs; the 9-GPU headroom is only momentary during Phase 2.

Approximate on-demand cost per full run (3 modes × 2 repeats, AWS list price):
**$120–180**.

#### 7.5.2 Option 2 — Homogeneous GPUs with Simulated Cost (cheaper, still defensible)

If only one GPU type is available, the benchmark still runs. The `cost` field lives in
the VA spec — it does **not** need to match physical hardware. Deploy two identical
variants with `cost: 6` and `cost: 40`; WVA's cost-optimization code path is identical.

| Resource | Minimum |
|---|---|
| GPUs of one type (all L40, all A10, or all A100) | **6** |
| CPU / RAM / storage | same as Option 1 |

**What remains accurately measured:**
- Cost-weighted GPU-hours (arithmetic on replica counts × assigned cost)
- Replica distribution across variants
- Scale-up and scale-down ordering
- SLO compliance (same GPUs → same latency regardless of which variant is used)

**What weakens:**
- Realistic per-GPU throughput differentials. Since both variants have identical real
  capacity, the KEDA-tuned `threshold: "4000"` (L40) vs `"12000"` (A100) split does not
  match reality — tune both triggers to the true capacity of the underlying GPU.
- The "KEDA-tuned picks the wrong variant because L40 ITL is higher" story is weaker.

**Bottom line:** the cost argument stands; the latency-differential argument narrows.
Recommend Option 2 for early iteration and budget-constrained runs; Option 1 for
publication.

#### 7.5.3 Option 3 — Absolute Minimum Viable (smoke only)

For validating the pipeline end-to-end on real OpenShift before committing to a full run.

| Resource | Minimum |
|---|---|
| GPUs (any type) | 3 |
| `maxReplicas` per variant | 2 (L40), 1 (A100) or single-variant with 3 |
| Phase durations | kind-compressed (60 / 180 / 240 / 180s) |
| Total runtime | ~35 min for all three modes |

This does **not** produce interesting comparison numbers — with `max=2+1` there is not
enough room for WVA and KEDA to diverge — but it validates real vLLM pod startup, image
pulls, EPP routing, and Prometheus scraping on the actual target cluster.

#### 7.5.4 Recommended Progression

Run these in order; each step reduces risk for the next.

1. **Kind dry-run** (free, ~70 min) — validates orchestration, cleanup, comparison
   script. Pass § 6.6 Go/No-Go gates before proceeding.
2. **Option 3 on OpenShift** (~3 GPU-hours) — validates real-vLLM path, image pulls,
   cluster-specific quirks.
3. **Option 2 on OpenShift** (~18 GPU-hours, homogeneous) — produces the cost-argument
   numbers at reduced infrastructure cost.
4. **Option 1 on OpenShift** (~18 L40-hours + 9 A100-hours) — produces the publishable
   headline numbers with real per-GPU latency differentials.

Steps 3 and 4 each produce a complete result set; you can stop at step 3 if the
homogeneous-cost numbers are sufficient for the intended audience.

---

## 8. Implementation Guide for the Coder Agent

This section is the concrete recipe to implement the benchmark. It assumes the reader is
working inside the `main/` worktree and has read § 2–7.

### 8.1 File Layout (all paths relative to repo root)

**New files:**

```
test/benchmark/
  cost_optimal_ramp_benchmark_test.go   # Ginkgo suite — 3 systems × 4 phases
  cost_optimal_ramp_types.go            # VariantTimeline, RampResult, PhaseResult
  cost_optimal_ramp_results.go          # CostWeightedGPUHours, segmentByPhase, per-variant sampler
  scenarios/cost_optimal_ramp.yaml      # shared prompt/output shape + phase rates

config/samples/keda/benchmark-ramp/
  scaledobject-naive-l40.yaml
  scaledobject-naive-a100.yaml
  scaledobject-tuned-l40.yaml
  scaledobject-tuned-a100.yaml
  README.md

test/e2e/fixtures/
  scaled_object_triggers_builder.go     # new fixture: CreateScaledObjectWithTriggers

hack/
  compare-ramp-results.py               # ~150 LOC; reads 3 JSONs, emits md + PNGs
  compare-ramp-results-requirements.txt # matplotlib, pandas, numpy
```

**Modified files:**

```
Makefile                                 # add test-cost-optimal-ramp, test-cost-optimal-ramp-kind
test/benchmark/config.go                 # add CostRampL4Cost, CostRampA100Cost, RampMode env vars
```

### 8.2 Go Types — Copy-Paste Ready

In `cost_optimal_ramp_types.go`:

```go
package benchmark

import "encoding/json"

// RampMode selects which autoscaler drives the experiment.
type RampMode string

const (
    RampModeWVA       RampMode = "wva"         // WVA + HPA pass-through
    RampModeKEDANaive RampMode = "keda-naive"  // Single queue-depth trigger
    RampModeKEDATuned RampMode = "keda-tuned"  // Four triggers: KV + queue + ITL + token-rate
)

// Variant describes one of the two deployments participating in the ramp.
type Variant struct {
    Name            string  // e.g. "llama8b-l40"
    DeploymentName  string  // e.g. "ms-bench-llama8b-l40-decode"
    GPULabel        string  // e.g. "NVIDIA-L40-48GB" — must match nvidia.com/gpu.product
    CostWeight      float64 // e.g. 6.0
    MinReplicas     int32
    MaxReplicas     int32
}

// VariantTimeline holds per-deployment sampling data across the full run.
type VariantTimeline struct {
    Name            string        `json:"name"`
    DeploymentName  string        `json:"deployment_name"`
    GPULabel        string        `json:"gpu_label"`
    CostWeight      float64       `json:"cost_weight"`
    ReplicaTimeline []ReplicaSnap `json:"replica_timeline"`
    MetricsTimeline []MetricSnap  `json:"metrics_timeline"`
}

// PhaseResult captures per-phase aggregate metrics.
type PhaseResult struct {
    Name         string          `json:"name"`          // baseline | ramp | peak | drop
    StartSec     float64         `json:"start_sec"`
    EndSec       float64         `json:"end_sec"`
    TargetRPS    int             `json:"target_rps"`
    AchievedRPS  float64         `json:"achieved_rps"`
    TTFT         json.RawMessage `json:"ttft"`           // {p50,p90,p99}
    ITL          json.RawMessage `json:"itl"`
    Throughput   json.RawMessage `json:"throughput"`
    ErrorCount   int             `json:"error_count"`
    IncompleteCount int          `json:"incomplete_count"`
    GuideLLMRaw  json.RawMessage `json:"guidellm_raw"`
}

// RampResult is the single JSON document emitted per (system-run).
type RampResult struct {
    Mode                 RampMode           `json:"mode"`
    ModelID              string             `json:"model_id"`
    Variants             []VariantTimeline  `json:"variants"`
    Phases               []PhaseResult      `json:"phases"`
    CostWeightedGPUHours float64            `json:"cost_weighted_gpu_hours"`
    SLOViolationRate     float64            `json:"slo_violation_rate"` // ITL > targetITL
    TargetITLms          float64            `json:"target_itl_ms"`
    DurationSec          float64            `json:"duration_sec"`
    GrafanaSnapshotURL   string             `json:"grafana_snapshot_url,omitempty"`
    Pods                 []PodInfo          `json:"pods,omitempty"`
}
```

Reuse existing types from `hpa_helpers.go`: `ReplicaSnap`, `MetricSnap`, `PodInfo`.

### 8.3 Cost-Weighted GPU-Hours and Phase Segmentation

In `cost_optimal_ramp_results.go`:

```go
// CostWeightedGPUHours sums replicas × cost × dt across all variants.
// Uses left-Riemann: replica count at sample i-1 applies over interval (i-1)→i.
func CostWeightedGPUHours(variants []VariantTimeline) float64 {
    var total float64
    for _, v := range variants {
        for i := 1; i < len(v.ReplicaTimeline); i++ {
            dt := v.ReplicaTimeline[i].ElapsedSec - v.ReplicaTimeline[i-1].ElapsedSec
            total += float64(v.ReplicaTimeline[i-1].SpecReplicas) * v.CostWeight * dt / 3600.0
        }
    }
    return total
}

// SegmentByPhase slices a metrics timeline by phase boundaries.
// Phase boundaries are expressed in seconds relative to run start.
func SegmentByPhase(snaps []MetricSnap, startSec, endSec float64) []MetricSnap {
    out := make([]MetricSnap, 0, len(snaps))
    for _, s := range snaps {
        if s.ElapsedSec >= startSec && s.ElapsedSec < endSec {
            out = append(out, s)
        }
    }
    return out
}
```

### 8.4 New Fixture — KEDA ScaledObject with Arbitrary Triggers

The existing `fixtures.EnsureScaledObject` is hardcoded to the `wva_desired_replicas`
trigger — good for the WVA path, wrong for KEDA-naive and KEDA-tuned (which target raw
vLLM metrics). Add a parallel builder:

```go
// test/e2e/fixtures/scaled_object_triggers_builder.go
package fixtures

import (
    "context"
    "fmt"
    "time"

    kedav1alpha1 "github.com/kedacore/keda/v2/apis/keda/v1alpha1"
    autoscalingv2 "k8s.io/api/autoscaling/v2"
    "k8s.io/apimachinery/pkg/api/errors"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/util/wait"
    "k8s.io/utils/ptr"
    "sigs.k8s.io/controller-runtime/pkg/client"
)

// EnsureScaledObjectWithTriggers creates (or replaces) a ScaledObject with
// caller-supplied triggers and optional HPA behavior.
func EnsureScaledObjectWithTriggers(
    ctx context.Context,
    crClient client.Client,
    namespace, name, scaleTargetName string,
    minReplicas, maxReplicas int32,
    pollingInterval, cooldownPeriod int32,
    triggers []kedav1alpha1.ScaleTriggers,
    hpaBehavior *autoscalingv2.HorizontalPodAutoscalerBehavior,
) error {
    objName := name + scaledObjectSuffix

    so := &kedav1alpha1.ScaledObject{
        ObjectMeta: metav1.ObjectMeta{
            Name:      objName,
            Namespace: namespace,
            Labels:    map[string]string{"test-resource": "true"},
        },
        Spec: kedav1alpha1.ScaledObjectSpec{
            ScaleTargetRef: &kedav1alpha1.ScaleTarget{
                APIVersion: apiVersionAppsV1,
                Kind:       kindDeployment,
                Name:       scaleTargetName,
            },
            PollingInterval: ptr.To(pollingInterval),
            CooldownPeriod:  ptr.To(cooldownPeriod),
            MinReplicaCount: ptr.To(minReplicas),
            MaxReplicaCount: ptr.To(maxReplicas),
            Triggers:        triggers,
        },
    }
    if hpaBehavior != nil {
        so.Spec.Advanced = &kedav1alpha1.AdvancedConfig{
            HorizontalPodAutoscalerConfig: &kedav1alpha1.HorizontalPodAutoscalerConfig{
                Behavior: hpaBehavior,
            },
        }
    }

    // Delete existing first (idempotent)
    existing := scaledObjectRef(namespace, name)
    if err := crClient.Get(ctx, client.ObjectKeyFromObject(existing), existing); err == nil {
        if delErr := crClient.Delete(ctx, existing); delErr != nil && !errors.IsNotFound(delErr) {
            return fmt.Errorf("delete existing ScaledObject %s: %w", objName, delErr)
        }
        if err := wait.PollUntilContextTimeout(ctx, time.Second, 10*time.Second, true, func(ctx context.Context) (bool, error) {
            getErr := crClient.Get(ctx, client.ObjectKeyFromObject(existing), existing)
            return errors.IsNotFound(getErr), nil
        }); err != nil {
            return fmt.Errorf("timeout waiting for ScaledObject %s deletion: %w", objName, err)
        }
    }
    return crClient.Create(ctx, so)
}

// BuildNaiveTriggers returns the single-trigger (queue-depth only) KEDA config.
func BuildNaiveTriggers(deploymentName, monitoringNS string) []kedav1alpha1.ScaleTriggers {
    prom := fmt.Sprintf("https://kube-prometheus-stack-prometheus.%s.svc.cluster.local:9090", monitoringNS)
    return []kedav1alpha1.ScaleTriggers{{
        Type: "prometheus",
        Name: "vllm-queue-depth",
        Metadata: map[string]string{
            "serverAddress": prom,
            "query":         fmt.Sprintf(`avg(vllm:num_requests_waiting{deployment=%q})`, deploymentName),
            "threshold":     "3",
            "metricType":    "AverageValue",
            "unsafeSsl":     "true",
        },
    }}
}

// BuildTunedTriggers returns the four-trigger (KV + queue + ITL + token-rate) KEDA config.
// perReplicaTokenCapacity is hand-tuned per GPU type (L40≈4000, A100≈12000 tokens/sec).
func BuildTunedTriggers(deploymentName, monitoringNS string, perReplicaTokenCapacity int) []kedav1alpha1.ScaleTriggers {
    prom := fmt.Sprintf("https://kube-prometheus-stack-prometheus.%s.svc.cluster.local:9090", monitoringNS)
    return []kedav1alpha1.ScaleTriggers{
        {
            Type: "prometheus", Name: "vllm-kv-cache",
            Metadata: map[string]string{
                "serverAddress": prom,
                "query":         fmt.Sprintf(`avg(vllm:gpu_cache_usage_perc{deployment=%q})`, deploymentName),
                "threshold":     "0.70",
                "metricType":    "AverageValue",
                "unsafeSsl":     "true",
            },
        },
        {
            Type: "prometheus", Name: "vllm-queue-depth",
            Metadata: map[string]string{
                "serverAddress": prom,
                "query":         fmt.Sprintf(`avg(vllm:num_requests_waiting{deployment=%q})`, deploymentName),
                "threshold":     "3",
                "metricType":    "AverageValue",
                "unsafeSsl":     "true",
            },
        },
        {
            Type: "prometheus", Name: "vllm-itl-p99",
            Metadata: map[string]string{
                "serverAddress": prom,
                "query": fmt.Sprintf(
                    `histogram_quantile(0.99, sum by (le, deployment) (rate(vllm:time_per_output_token_seconds_bucket{deployment=%q}[1m])))`,
                    deploymentName),
                "threshold":  "0.054", // 54ms (90% of 60ms SLO)
                "metricType": "Value",
                "unsafeSsl":  "true",
            },
        },
        {
            Type: "prometheus", Name: "vllm-token-arrival-rate",
            Metadata: map[string]string{
                "serverAddress": prom,
                "query": fmt.Sprintf(
                    `sum(rate(vllm:prompt_tokens_total{deployment=%q}[30s])) / count(kube_pod_info{pod=~%q, pod_ip!=""})`,
                    deploymentName, deploymentName+"-.*"),
                "threshold":  fmt.Sprintf("%d", perReplicaTokenCapacity),
                "metricType": "AverageValue",
                "unsafeSsl":  "true",
            },
        },
    }
}

// BuildTunedHPABehavior returns the 30s-up / 180s-down stabilization config.
func BuildTunedHPABehavior() *autoscalingv2.HorizontalPodAutoscalerBehavior {
    return &autoscalingv2.HorizontalPodAutoscalerBehavior{
        ScaleUp: &autoscalingv2.HPAScalingRules{
            StabilizationWindowSeconds: ptr.To(int32(30)),
            SelectPolicy:               ptr.To(autoscalingv2.MaxChangePolicySelect),
            Policies: []autoscalingv2.HPAScalingPolicy{
                {Type: autoscalingv2.PodsScalingPolicy, Value: 2, PeriodSeconds: 60},
            },
        },
        ScaleDown: &autoscalingv2.HPAScalingRules{
            StabilizationWindowSeconds: ptr.To(int32(180)),
            SelectPolicy:               ptr.To(autoscalingv2.MinChangePolicySelect),
            Policies: []autoscalingv2.HPAScalingPolicy{
                {Type: autoscalingv2.PodsScalingPolicy, Value: 1, PeriodSeconds: 120},
            },
        },
    }
}
```

### 8.5 Test Orchestration — Ginkgo Skeleton

`test/benchmark/cost_optimal_ramp_benchmark_test.go` structure:

```go
var _ = Describe("Cost-Optimal Ramp Benchmark", Ordered, Label("benchmark", "cost-ramp"), func() {
    var (
        testCtx    context.Context
        testCancel context.CancelFunc
        mode       RampMode
        variants   []Variant
        result     RampResult
        runStart   time.Time
    )

    BeforeAll(func() {
        testCtx, testCancel = context.WithCancel(context.Background())
        mode = RampMode(testconfig.GetEnv("AUTOSCALER_MODE", string(RampModeWVA)))
        variants = []Variant{
            {Name: "llama8b-l40",   DeploymentName: "ms-bench-llama8b-l40-decode",   GPULabel: "NVIDIA-L40-48GB",        CostWeight: benchCfg.CostRampL4Cost,  MinReplicas: 1, MaxReplicas: 6},
            {Name: "llama8b-a100", DeploymentName: "ms-bench-llama8b-a100-decode", GPULabel: "NVIDIA-A100-PCIE-80GB", CostWeight: benchCfg.CostRampA100Cost, MinReplicas: 1, MaxReplicas: 3},
        }
        result = RampResult{Mode: mode, ModelID: benchCfg.ModelID, TargetITLms: 60.0}
    })

    AfterAll(func() {
        // Write result JSON + Grafana snapshot URL.
        result.CostWeightedGPUHours = CostWeightedGPUHours(result.Variants)
        result.DurationSec = time.Since(runStart).Seconds()
        writeRampResult(&result, rampOutputPath(mode))
        testCancel()
    })

    It("sets up two variant deployments and selected autoscaler", func() {
        ensureTwoVariantDeployments(testCtx, variants)
        switch mode {
        case RampModeWVA:        setupWVAForBothVariants(testCtx, variants)
        case RampModeKEDANaive:  setupKEDAForBothVariants(testCtx, variants, false)
        case RampModeKEDATuned:  setupKEDAForBothVariants(testCtx, variants, true)
        }
        patchAllEPPConfigs(testCtx)
        waitForDeploymentsReady(testCtx, variants)
        runStart = time.Now()
    })

    // Each phase: launch one GuideLLM job at the phase's rate, monitor both variants
    // every 15s, collect timeline + phase GuideLLM output, append to result.
    It("Phase 0: baseline (3 RPS)",  func() { runPhase(testCtx, &result, variants, "baseline", 3,  benchCfg.BaselineDurationSec,  runStart) })
    It("Phase 1: ramp (15 RPS)",     func() { runPhase(testCtx, &result, variants, "ramp",     15, benchCfg.SpikeDurationSec,     runStart) })
    It("Phase 2: peak (25 RPS)",     func() { runPhase(testCtx, &result, variants, "peak",     25, benchCfg.SustainedDurationSec, runStart) })
    It("Phase 3: drop (3 RPS)",      func() { runPhase(testCtx, &result, variants, "drop",     3,  benchCfg.CooldownDurationSec,  runStart) })
})
```

**`runPhase` responsibilities (pseudocode):**

```
runPhase(ctx, result, variants, phaseName, rateRPS, durationSec, runStart):
    scenario := WorkloadScenario{
        Name: phaseName,
        PromptTokens: 1000, OutputTokens: 4000,
        Rate: rateRPS, MaxSeconds: durationSec,
        Profile: "poisson", RequestType: "text_completions",
    }

    // Unique job name per phase so they don't collide.
    jobName := "cost-ramp-" + phaseName
    CreateGuideLLMJobWithArgs(ctx, jobName, scenario)

    phase := PhaseResult{Name: phaseName, StartSec: time.Since(runStart).Seconds(), TargetRPS: rateRPS}
    done := make(chan error, 1)
    go func() { done <- WaitForJobCompletion(ctx, jobName, durationSec+5min) }()

    ticker := 15 * time.Second
    for !jobDone:
        select done: break
        select ticker.C:
            elapsed := time.Since(runStart).Seconds()
            for each variant in variants:
                sample deployment replicas (spec+ready) → ReplicaSnap
                query per-deployment Prometheus metrics → MetricSnap:
                    vllm:kv_cache_usage_perc{deployment=v.DeploymentName}
                    vllm:num_requests_waiting{deployment=v.DeploymentName}
                    inference_extension_flow_control_queue_size{...}
                append to result.Variants[v.Name].{Replica,Metrics}Timeline

    phase.EndSec = time.Since(runStart).Seconds()
    phase.GuideLLMRaw, phase.TTFT, phase.ITL, phase.Throughput = ExtractGuideLLMMetrics(jobName)
    phase.AchievedRPS, phase.ErrorCount, phase.IncompleteCount = ExtractCounters(phase.GuideLLMRaw)
    result.Phases = append(result.Phases, phase)
```

**Reuse existing helpers verbatim:** `CreateGuideLLMJobWithArgs`, `WaitForJobCompletion`,
`GetJobPodLogs`, `PatchEPPConfigMap`, `QueryRangeAvg`, Grafana snapshot capture.

### 8.6 Setup Functions — What Each Mode Creates

```
setupWVAForBothVariants(ctx, variants):
    for v in variants:
        fixtures.EnsureVariantAutoscaling(
            ctx, crClient, ns, "va-"+v.Name, v.DeploymentName, modelID,
            v.GPULabel, v.CostWeight, controllerInstance,
            fixtures.WithMinReplicas(v.MinReplicas),
            fixtures.WithMaxReplicas(v.MaxReplicas),
        )
        fixtures.EnsureHPA(ctx, k8s, ns, "hpa-"+v.Name, v.DeploymentName, "va-"+v.Name, v.MinReplicas, v.MaxReplicas)
    // No KEDA for WVA mode.

setupKEDAForBothVariants(ctx, variants, tuned bool):
    // NOTE: NO VAs and NO HPAs in KEDA modes.
    // KEDA directly scales deployments without going through WVA's desired-replicas metric.
    for v in variants:
        var triggers []kedav1alpha1.ScaleTriggers
        var behavior *autoscalingv2.HorizontalPodAutoscalerBehavior
        if tuned:
            perReplicaTokens := 4000
            if strings.Contains(v.GPULabel, "A100") { perReplicaTokens = 12000 }
            triggers = fixtures.BuildTunedTriggers(v.DeploymentName, monitoringNS, perReplicaTokens)
            behavior = fixtures.BuildTunedHPABehavior()
        else:
            triggers = fixtures.BuildNaiveTriggers(v.DeploymentName, monitoringNS)
            behavior = nil
        fixtures.EnsureScaledObjectWithTriggers(
            ctx, crClient, ns, "so-"+v.Name, v.DeploymentName,
            v.MinReplicas, v.MaxReplicas,
            tunedPollingInterval(tuned), tunedCooldownPeriod(tuned),
            triggers, behavior,
        )
```

**CleanUp between runs.** `DeferCleanup` (or AfterAll) must remove VAs, HPAs, **and**
ScaledObjects so a follow-up run with a different `AUTOSCALER_MODE` starts clean:

```
for v in variants:
    fixtures.DeleteVariantAutoscaling(ctx, crClient, ns, "va-"+v.Name)
    k8s.AutoscalingV2().HorizontalPodAutoscalers(ns).Delete(ctx, "hpa-"+v.Name+"-hpa", ...)
    fixtures.DeleteScaledObject(ctx, crClient, ns, "so-"+v.Name)
```

### 8.7 Per-Variant Deployment Creation

The existing `fixtures.EnsureModelService` creates a single decode deployment. For two
variants of the same model we need **two** deployments distinguished by `GPULabel`.
Options (in order of preference):

**Option A — reuse `EnsureModelService` twice with nodeSelector:** extend the fixture to
accept an optional `nodeSelector` parameter `map[string]string{"nvidia.com/gpu.product": v.GPULabel}`
and emit a different deployment name per variant. Preferred; minimal change.

**Option B — wrap existing Helm-deployed decode with a `kubectl patch`:** copy the one
existing deployment, rename, and patch its `nodeSelector`. Simpler but fragile.

**Option C — pre-deploy both variants via Helm** (`llm-d-modelservice` supports
multi-variant): matches how multi-model benchmark works today. Cleanest but requires
Helm chart changes outside this PR's scope.

**Recommended: Option A.** Implementation:

```go
// In test/e2e/fixtures/model_service_builder.go — add variant:
func EnsureModelServiceWithSelector(
    ctx, k8s, ns, name, pool, modelID string,
    useSimulator bool, maxNumSeqs int,
    nodeSelector map[string]string,
) error { ... }  // Existing function + injection of nodeSelector into pod template
```

### 8.8 WVA Analyzer Configuration

Apply these ConfigMaps before running WVA mode. One-shot; they apply to all three runs
but are ignored by KEDA modes.

```bash
# Already in deploy/ — verify and apply:
kubectl apply -f deploy/configmap-queueing-model.yaml
kubectl apply -f deploy/configmap-saturation-scaling.yaml

# Patch with benchmark-specific overrides (per § 3.2):
kubectl patch configmap wva-queueing-model-config \
  -n workload-variant-autoscaler-system \
  --type merge \
  -p '{"data":{"llama8b-bench":"model_id: \"meta-llama/Llama-3.1-8B-Instruct\"\nnamespace: \"llmd-bench\"\ntargetTTFT: 500.0\ntargetITL: 60.0\nsloMultiplier: 3.0\n"}}'
```

### 8.9 Comparison Script — `hack/compare-ramp-results.py`

**Input:** three JSON files (one per mode) matching the `RampResult` schema.

**Output:**
- `/tmp/ramp-comparison-report.md` — side-by-side summary table
- `/tmp/ramp-replica-timelines.png` — 3 subplots (one per mode), each a stacked-area chart
- `/tmp/ramp-itl-p99-overlay.png` — three overlaid p99-ITL lines
- `/tmp/ramp-cost-vs-latency.png` — scatter, one point per mode

**Skeleton:**

```python
#!/usr/bin/env python3
"""Compare RampResult JSON outputs from WVA, KEDA-naive, KEDA-tuned runs."""
import json, sys, pathlib
import matplotlib.pyplot as plt

def load(path):
    with open(path) as f:
        return json.load(f)

def write_markdown_table(results, out):
    lines = ["| Metric | WVA | KEDA-naive | KEDA-tuned |", "|---|---|---|---|"]
    rows = [
        ("Cost-weighted GPU-hours", "cost_weighted_gpu_hours", "%.2f"),
        ("SLO violation rate (%)", "slo_violation_rate", "%.2f"),
        ("Total duration (s)",    "duration_sec",         "%.0f"),
    ]
    for label, key, fmt in rows:
        vals = [fmt % r[key] for r in results]
        lines.append(f"| {label} | {' | '.join(vals)} |")
    # Per-phase p99 ITL rows:
    for phase_idx, phase_name in enumerate(["baseline", "ramp", "peak", "drop"]):
        vals = [_get_p99_itl(r, phase_idx) for r in results]
        lines.append(f"| P99 ITL — {phase_name} (ms) | {' | '.join(f'{v:.1f}' for v in vals)} |")
    with open(out, "w") as f:
        f.write("\n".join(lines))

def plot_replica_timelines(results, out):
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    for ax, r in zip(axes, results):
        elapsed = [s["elapsed_sec"] for s in r["variants"][0]["replica_timeline"]]
        l40      = [s["spec_replicas"] for s in r["variants"][0]["replica_timeline"]]
        a100    = [s["spec_replicas"] for s in r["variants"][1]["replica_timeline"]]
        ax.stackplot(elapsed, l40, a100, labels=["L40", "A100"], colors=["#4caf50", "#f44336"])
        ax.set_title(r["mode"])
        ax.set_ylabel("Replicas")
        ax.legend(loc="upper left")
    axes[-1].set_xlabel("Time (s)")
    fig.tight_layout()
    fig.savefig(out, dpi=120)

# ... plot_itl_overlay, plot_cost_vs_latency similar ...

if __name__ == "__main__":
    paths = ["/tmp/ramp-results-wva.json", "/tmp/ramp-results-keda-naive.json", "/tmp/ramp-results-keda-tuned.json"]
    results = [load(p) for p in paths]
    write_markdown_table(results, "/tmp/ramp-comparison-report.md")
    plot_replica_timelines(results, "/tmp/ramp-replica-timelines.png")
    # plot_itl_overlay(results, "/tmp/ramp-itl-p99-overlay.png")
    # plot_cost_vs_latency(results, "/tmp/ramp-cost-vs-latency.png")
    print("Comparison report written to /tmp/ramp-comparison-report.md")
```

### 8.10 Makefile Targets

```makefile
# Run a single system; select via AUTOSCALER_MODE={wva,keda-naive,keda-tuned}.
# BENCHMARK_RESULTS_FILE sets the output JSON path; default includes the mode.
.PHONY: test-cost-optimal-ramp-single
test-cost-optimal-ramp-single: manifests generate fmt vet
	@echo "Running cost-optimal ramp: mode=$(AUTOSCALER_MODE)"
	AUTOSCALER_MODE=$(AUTOSCALER_MODE) \
	BENCHMARK_RESULTS_FILE=/tmp/ramp-results-$(AUTOSCALER_MODE).json \
	BENCHMARK_SCENARIO=cost_optimal_ramp \
	ENVIRONMENT=$(ENVIRONMENT) \
	LLMD_NS=$(LLMD_NS) WVA_NS=$(WVA_NS) \
	COST_RAMP_L4_COST=$(COST_RAMP_L4_COST) \
	COST_RAMP_A100_COST=$(COST_RAMP_A100_COST) \
	go test ./test/benchmark/ -run TestCostOptimalRamp \
	    -ginkgo.focus "Cost-Optimal Ramp Benchmark" \
	    -timeout 90m -v

# Full sequence: all three systems back-to-back, then comparison report.
.PHONY: test-cost-optimal-ramp
test-cost-optimal-ramp:
	$(MAKE) test-cost-optimal-ramp-single AUTOSCALER_MODE=wva
	$(MAKE) test-cost-optimal-ramp-single AUTOSCALER_MODE=keda-naive
	$(MAKE) test-cost-optimal-ramp-single AUTOSCALER_MODE=keda-tuned
	python3 hack/compare-ramp-results.py
	@echo "Comparison report: /tmp/ramp-comparison-report.md"

# Kind dry-run: same sequence but with compressed durations.
.PHONY: test-cost-optimal-ramp-kind
test-cost-optimal-ramp-kind:
	BENCHMARK_BASELINE_DURATION=60 \
	BENCHMARK_SPIKE_DURATION=180 \
	BENCHMARK_SUSTAINED_DURATION=240 \
	BENCHMARK_COOLDOWN_DURATION=180 \
	ENVIRONMENT=kind-emulator \
	LLMD_NS=llm-d-sim WVA_NS=workload-variant-autoscaler-system \
	COST_RAMP_L4_COST=6 COST_RAMP_A100_COST=40 \
	$(MAKE) test-cost-optimal-ramp
```

### 8.11 Env Var Contract

| Variable | Default | Purpose |
|---|---|---|
| `AUTOSCALER_MODE` | `wva` | `wva` / `keda-naive` / `keda-tuned` |
| `BENCHMARK_RESULTS_FILE` | `/tmp/ramp-results-<mode>.json` | Output JSON path |
| `BENCHMARK_BASELINE_DURATION` | 300 | Phase 0 seconds (60 on kind) |
| `BENCHMARK_SPIKE_DURATION` | 420 | Phase 1 seconds (180 on kind) |
| `BENCHMARK_SUSTAINED_DURATION` | 600 | Phase 2 seconds (240 on kind) |
| `BENCHMARK_COOLDOWN_DURATION` | 480 | Phase 3 seconds (180 on kind) |
| `COST_RAMP_L4_COST` | 6 | L40 cost weight |
| `COST_RAMP_A100_COST` | 40 | A100 cost weight |
| `COST_RAMP_MODEL_ID` | `meta-llama/Llama-3.1-8B-Instruct` | Model ID for both variants |
| `BENCHMARK_GRAFANA_ENABLED` | true | Capture Grafana snapshot |
| `ENVIRONMENT` | `openshift` | `openshift` / `kind-emulator` |
| `LLMD_NS` | `llmd-bench` | Namespace for deployments |

Wire these into `test/benchmark/config.go::BenchmarkConfig` — only the three new
`COST_RAMP_*` vars are new; the rest already exist.

### 8.12 Verification / Debugging Checklist

Before declaring each run successful, the test should self-check:

1. **Both deployments exist and are ready.**
   `kubectl get deploy -n $LLMD_NS | grep -c decode` → 2
2. **Mode-specific resources are present.**
   - WVA mode: 2 VAs + 2 HPAs; 0 ScaledObjects.
   - KEDA modes: 0 VAs + 0 HPAs; 2 ScaledObjects.
3. **Per-variant metrics are flowing.** Prometheus range query for
   `vllm:kv_cache_usage_perc{deployment="ms-bench-llama8b-l40-decode"}` returns non-empty
   for the last 2 minutes. Same for A100.
4. **Phase boundaries align.** Total duration = sum of four phase durations ± 30s.
5. **Result JSON is valid.** `jq '.cost_weighted_gpu_hours' /tmp/ramp-results-$MODE.json`
   returns a positive float.
6. **Replica timeline per variant is non-empty.** Each `variants[].replica_timeline`
   has ≥ `(duration / 15)` entries.

### 8.13 Implementation Order (Recommended)

The coder should implement in this order; each step is independently testable.

1. **Types + cost calculator** (§ 8.2, § 8.3). Pure code, no deps. Add unit test in
   `cost_optimal_ramp_results_test.go` for `CostWeightedGPUHours` with a two-variant fixture.
2. **ScaledObject fixture** (§ 8.4). Add a unit test that builds a ScaledObject and
   asserts the trigger set.
3. **Per-variant deployment fixture** (§ 8.7 Option A). Verify in kind that both
   variants can come up.
4. **WVA setup path** (§ 8.6 `setupWVAForBothVariants`). Run a single-phase
   60s smoke at 3 RPS in kind; verify both VAs appear and produce `wva_desired_replicas`.
5. **KEDA-naive setup path**. Same smoke; verify `ScaledObject` goes `READY=True`.
6. **KEDA-tuned setup path**. Same smoke; verify all four triggers resolve.
7. **Multi-phase orchestration** (§ 8.5 `runPhase`). Full 4-phase run in kind for
   `AUTOSCALER_MODE=wva`. Verify result JSON has four `phases[]` entries and two
   `variants[]` entries with non-empty timelines.
8. **Cleanup between modes.** Run all three modes back-to-back in kind. Verify
   between runs: no leftover VAs/HPAs/ScaledObjects, deployments scaled back to 1.
9. **Comparison script** (§ 8.9). Feed it three JSON files; verify the four outputs land
   in `/tmp/`.
10. **Kind Go/No-Go criteria** (§ 6.6). All four green → OpenShift runs authorized.

### 8.14 Do NOT Do

- **Do not** modify WVA controller code — this benchmark is driver-only.
- **Do not** write to the plans branch from the code worktree.
- **Do not** hardcode pod IPs or node IPs; everything must go through service/gateway
  DNS names.
- **Do not** reuse Grafana snapshot URL across modes — capture one per run.
- **Do not** assume kind timing matches OpenShift timing. Compressed phase durations
  exist specifically because emulator response is fast.
- **Do not** commit `/tmp/ramp-results-*.json` — these are ephemeral artifacts.

---

## 9. Expected Results — Scenario 1

Numbers below are directional predictions, not committed targets.
Analyzer: saturation_v2. L40 capacity ~12 RPS/replica, H100 ~20 RPS/replica, cost L40=15, H100=65.

| Metric | WVA | KEDA-naive | KEDA-tuned |
|---|---|---|---|
| P99 ITL during Phase 1 Ramp (ms) | ~55 | ~85 | ~62 |
| P99 ITL during Phase 2 Peak (ms) | ~55 | ~55 | ~55 |
| Time-to-first-new-replica-Ready (s) | ~75 | ~110 | ~80 |
| L40 replicas at Phase 2 steady state | 2 | 2 | 2 |
| H100 replicas at Phase 2 steady state | 1 | 1 | 1 |
| Peak H100 replicas during ramp transitions | 1 | 2 | 2 |
| Cost-weighted GPU-hours (normalized) | 1.00 | 1.20–1.30 | 1.15–1.25 |
| SLO violation rate (ITL > 60ms) | ~2% | ~12% | ~3% |

**Derived claims for the write-up:**
- WVA vs KEDA-tuned: **~15–25% cost reduction** over the full run, driven by
  suppression of premature H100 scale-up during ramp transitions (pending-replica
  awareness) and faster cost-ordered scale-down after load drops.
- WVA vs KEDA-naive: same cost advantage plus **~5× fewer SLO violations** during ramp.
- **At Phase 2 steady state all three systems converge to L40=2, H100=1.** The cost
  gap is entirely in transient behavior: KEDA fires H100 prematurely at each ramp step
  (while L40 replicas are pending) and holds H100 for an extra 180s on scale-down.
- The latency gap is modest and limited to the ramp phase. Don't lead with latency.

**Note on expected cost advantage magnitude:**
The 15–25% range assumes saturation_v2 with the pending-replica mechanism. This is
smaller than the 32–47% estimate in § 2.2a (which assumed QueueingModel-level
SLO-aware behavior). The QueueingModel follow-up run (once ready) is expected to widen
the gap by holding H100=1 at peak through SLO math rather than relying on thresholds.

---

## 10. Risks and Caveats

1. **Staircase vs linear ramp** may understate WVA's latency advantage during Phase 1.
   Acceptable for this round; file a follow-up to extend GuideLLM for a true linear ramp
   if the p99 gap is smaller than predicted.

2. **ThroughputAnalyzer not yet merged.** This benchmark uses saturation + queueing
   model only. Re-run after TA3 merges; expect Phase 1 latency gap to widen.

3. **Histogram quantile noise at low RPS.** KEDA-tuned's ITL p99 trigger may flap during
   Phase 0 Baseline. Document as-is; do not hide it.

4. **Per-replica capacity estimation for KEDA-tuned arrival-rate trigger** is
   hand-tuned. If L40 per-replica capacity drifts from 4000 tokens/sec, the trigger
   becomes inaccurate. This is **exactly** the manual-tuning fragility WVA avoids — call
   this out in the narrative rather than hide it.

5. **Cluster heterogeneity.** If the cluster only has one GPU type available, run with
   simulated cost variants (same GPU, different assigned `cost` values) — the cost
   optimization logic still exercises; only the latency story weakens.

6. **Single-model focus.** This benchmark does not exercise multi-model contention. That
   is a separate experiment for Limited mode (future WVA feature) and not yet
   scheduleable.

7. **EPP image version mismatch** still present per `CURRENT.md § Known infra issues`.
   Apply the v0.5.0 patch before runs.

---

## 10.1 Optional Extension — Three-Tier Scenario (L40 + A100 + H100)

The cluster has 2×L40, 24×A100, and 16×H100. Scenario 1 uses only L40 and H100 to
maximise the cost ratio (1:4.3). A follow-up run can add A100 as a mid-tier variant,
demonstrating WVA's ability to exhaust the cheapest GPU tier first before climbing the
cost ladder.

**Setup delta from Scenario 1:**
- Third variant `llama8b-a100`: cost=40, min=0, max=6.
- WVA sees three variants per `modelID`; optimizer picks cheapest available first:
  L40 (15) → A100 (40) → H100 (65).
- KEDA adds a third ScaledObject for A100 with the same trigger logic as the other two.

**Expected WVA behavior at 25 RPS peak:**
- 2 L40 (24 RPS) + 1 A100 (~12 RPS): total 36 RPS — covers peak with A100 as mid tier.
  H100 stays at min=1, unused.
- KEDA-tuned: L40=2 KV fills → scales A100 to 2–3, and H100 ScaledObject also fires
  if H100 KV is elevated → both A100 and H100 grow unnecessarily.

**Headline:** WVA uses zero H100 replicas beyond minimum during peak; KEDA provisions
both A100 and H100 defensively. The three-tier story shows WVA climbing the cost ladder
only as far as needed, which is the core value proposition for heterogeneous GPU fleets.

**Why this is a follow-up, not the first run:**
- Three ScaledObjects increase KEDA baseline complexity; harder to make the "honest
  competitor" argument for KEDA-tuned with three independent triggers.
- Two-variant Scenario 1 isolates the core mechanism cleanly. Run it first, establish
  the baseline, then extend to three tiers in a second paper/report section.

---

## 11. Presentable Overview (Condensed)

For use in decks / proposals.

### The question
Can a well-tuned KEDA configuration match WVA on an LLM inference workload with
heterogeneous GPUs? Or is there a structural gap?

### The experiment
- Model: Llama-3.1-8B-Instruct
- Pool: two variants — L40 48 GB (cost=15, max 2 replicas, hardware cap) + H100 80 GB
  (cost=65, max 3 replicas); 1:4.3 cost ratio; L40 pool barely covers 25 RPS peak
- Autoscaler: WVA with saturation_v2 (token-based, aggregate cross-variant, pending-replica-aware)
- Traffic: 30-min staircase ramp, 3 → 25 RPS decode-heavy (1000 in / 4000 out), Poisson
- Compared: WVA vs KEDA-naive (queue-depth) vs KEDA-tuned (KV + queue + ITL p99 + token rate)
- Metric: cost-weighted GPU-hours at equivalent SLO
- Validation path: kind-emulator dry-run first (~35 min total), then OpenShift (half day)

### The claim
WVA uses **~15–25% fewer cost-weighted GPU-hours** than KEDA-tuned at equivalent p99 ITL.
The gap comes from two structural properties of saturation_v2: (1) pending-replica
awareness prevents premature H100 scale-up at each ramp step while L40 replicas are
starting, and (2) cost-ordered scale-down releases H100 immediately after load drops
while KEDA's stabilisation windows hold it for 3 additional minutes.
All three systems converge to the same steady-state replica count at peak (L40=2, H100=1).
The cost gap is in ramp transitions and drop — not steady state.

### The picture
A replica-count timeline showing H100 replicas spiking to 2 during each ramp step for
KEDA (both naive and tuned), while WVA holds H100 flat at 1 throughout. After peak,
KEDA holds H100=2 for 3 extra minutes; WVA releases it immediately. Same p99 ITL at
steady state, different ramp and drop cost.

### What this is and is not
- **Is:** a defensible cost argument for operators with heterogeneous accelerator pools.
- **Is not:** an argument that WVA is strictly better at latency — with careful KEDA
  tuning the latency gap is small. Don't lead with latency.

### What comes next
Re-run with the Throughput Analyzer enabled (after TA3 merges) to expose the
proactive-detection advantage on rapid ramps. Extend to dynamic cross-tenant
reallocation once WVA's Limited mode lands.

---

### Scenario 2 — Starvation Prevention (one-pager)

**The question.** Can a per-deployment autoscaler like KEDA protect a premium-tenant
workload from being starved of GPU slots by a basic tenant that shares the cluster?

**The experiment.** Two tenants in the same cluster. Partition GPU nodes with labels:
2 nodes = premium, 4 nodes = basic. Pool-A (premium tenant) constrained to the premium
partition; Pool-B (basic tenant) can use either. Same model, same cluster, same
hardware — only labels + cost weights differ. Traffic: Pool-B ramps first, Pool-A
joins 10 min later.

**The claim.** WVA's cost-gradient (pool-B-gpu2=30 < pool-B-gpu1=40) makes pool-B scale
up on the basic partition, leaving premium slots free for Pool-A. KEDA (any config) scales
pool-B symmetrically across both partitions, consuming premium slots; Pool-A starves when
it tries to scale. The only KEDA fix (hard-capping pool-B-gpu1 at 0) protects Pool-A but
penalizes Pool-B's own ramp latency — a trade-off WVA avoids.

**The picture.** A replica-count timeline showing Pool-B on WVA climbing only on gpu2
while gpu1 stays at 0; and on KEDA-tuned, Pool-B filling both partitions. Then Pool-A
tries to scale: under WVA it succeeds immediately; under KEDA it sits Pending.

**What this is and is not.**
- **Is:** a defensible multi-tenancy argument — structural cross-variant preference works
  for tenancy protection without any priority scheduling.
- **Is not:** a claim about dynamic cross-tenant reallocation. WVA's preventive
  mechanism is *static* (cost gradient steers Pool-B's first choice). Dynamic
  reallocation under a Pool-A spike after Pool-B is already on gpu1 requires Limited
  mode and is out of scope for this round.

**What comes next.** Dynamic cross-tenant reallocation once Limited mode is available.

---

### 11.1 Suggested Presentation Flow

Which sections of this document to use when, depending on audience and time budget.

**Lightning talk — Scenario 1 only (≤ 5 min):** § 11 up to § 11.1. Question, experiment,
claim, picture, caveats, next step. Skip everything else.

**Lightning talk — both scenarios (~8 min):** § 11 Scenario 1 one-pager + § 11 Scenario 2
one-pager. Two slides, two claims, two pictures. Good for a short conference pitch.

**Approval discussion — Scenario 1 only (~15 min):**

| Min | Section | Purpose |
|---|---|---|
| 0–2  | § 11 Scenario 1    | Open with the one-pager — state question, claim, picture |
| 2–4  | § 2.2              | Confirm cost ratio and variant choices |
| 4–9  | § 4.3              | Walk through "what KEDA can and cannot do" — intellectual core |
| 9–12 | § 7.5              | Decide which sizing option to run on OpenShift |
| 12–14| § 9                | Expected-results table — "here's what we'd learn" |
| 14–15| STOP block (top)   | Confirm explicit approval |

**Approval discussion — both scenarios (~25 min):**

| Min | Section | Purpose |
|---|---|---|
| 0–3   | § 11 Scenario 1   | One-pager for cost argument |
| 3–6   | § 11 Scenario 2   | One-pager for starvation argument |
| 6–10  | § 4.3             | Why KEDA-tuned cannot solve cross-variant coordination |
| 10–13 | § 12.8            | Why `keda-tuned-capped` is the honest competitor and still loses |
| 13–17 | § 9 + § 12.10     | Expected results for both |
| 17–22 | § 7.5             | Sizing decision covering both scenarios |
| 22–25 | STOP block (top)  | Confirm explicit approval |

§ 8 (implementation guide) is appendix. § 12.11 (Scenario 2 delta) is also appendix.
Only open them if someone asks about implementability or the coder walks through file
layout.

**External / wider-audience talk (~20 min):** both one-pagers from § 11 → § 2 → § 4 →
§ 9. Add § 12.1 + § 12.6 + § 12.10 if time. Skip sizing (§ 7.5) and implementation (§ 8)
— those are internal concerns.

**Written circulation for async review:** link the whole document. The STOP block at
the top and the two one-pagers in § 11 bookend each argument; reviewers navigate the
rest by section heading.

**Rule of thumb:** If you find yourself presenting § 8 or § 12.11, you have the wrong
audience — those sections are for the coder after approval, not for decision-makers.

---

## 12. Scenario 2 — Starvation Prevention (Multi-Tenant Coordination)

### 12.1 Thesis

Under a fixed cluster budget with a higher-priority tenant constrained to a specific GPU
partition, WVA's cost-optimal cross-variant scaling naturally steers a lower-priority
tenant's workload *away* from the constrained partition — preventing starvation **without
any cross-autoscaler coordination, priority-scheduling extension, or manual cross-tenant
configuration**. KEDA cannot replicate this because its per-deployment `ScaledObject`s
have no visibility into another tenant's demand.

**Headline:** Under simultaneous load on both pools, WVA holds Pool-A's SLO while KEDA
(naive or tuned) causes Pool-A replica starvation and SLO violation. The only KEDA
countermeasure that matches WVA on Pool-A protection (hard-capping pool-B on the premium
partition) simultaneously hurts pool-B's own latency during its ramp phase — a trade-off
WVA avoids by construction.

### 12.2 Topology

Two tenants, shared cluster, partitioned GPU pool:

| Pool | Namespace | EPP | Variants |
|---|---|---|---|
| Pool-A (premium tenant) | `tenant-premium` | `gaie-premium-epp` | 1 variant: constrained to GPU1 partition |
| Pool-B (basic tenant) | `tenant-basic` | `gaie-basic-epp` | 2 variants: GPU1 partition OR GPU2 partition |

Both pools serve the **same model** (`meta-llama/Llama-3.1-8B-Instruct`). Same-model
choice removes model-capability as a confound: any Pool-A latency difference across
systems is attributable to resource availability, not model differences.

Pool-A's constraint to GPU1 simulates a real production pattern (VRAM requirement for a
larger model). In this benchmark it is enforced via `nodeSelector`.

### 12.3 Physical Realization — Two Options

The GPU1/GPU2 partition is logical, not physical. Two options depending on cluster
hardware availability.

#### Option P1 — True heterogeneous GPUs (reality-matching)

| Partition | GPU | Count |
|---|---|---|
| GPU1 (premium) | A100-80GB | 2 |
| GPU2 (basic) | L40 | 4 |

Matches the production pattern. Use for publication-quality numbers on clusters that
have both GPU types.

#### Option P2 — Homogeneous hardware with label partitioning (benchmark-friendly, DEFAULT)

All workers use the same GPU (any type — L40, A10, A100). Label them artificially to
create the partition:

```bash
# 2 nodes → premium partition
kubectl label node worker-0 worker-1 gpu.partition=premium --overwrite

# 4 nodes → basic partition
kubectl label node worker-2 worker-3 worker-4 worker-5 gpu.partition=basic --overwrite
```

Deployments use `nodeSelector: gpu.partition=<label>`. Both partitions target the same
hardware; the barrier is purely a label.

**Why this works:** the starvation effect comes from GPU-slot contention (Pool-B on the
premium partition consumes slots; Pool-A then finds no free slots to scale into). The
effect is identical whether the partitions are physically different GPUs or the same GPU
type behind different labels.

**Why this is the default:** clusters with only one GPU type are common (most test
clusters, many academic labs). Option P2 makes Scenario 2 universally runnable. Cost
weights still drive WVA's cross-variant choice, independent of the underlying hardware.

**When to prefer Option P1:** only when publishing externally and realism matters more
than portability.

### 12.4 Cost Assignment

| Variant | Partition | Cost weight | Purpose |
|---|---|---|---|
| `pool-A-gpu1` | premium | 40 | Only variant — cost is informational |
| `pool-B-gpu1` | premium | 40 | Same cost as Pool-A on same partition |
| `pool-B-gpu2` | basic | 30 | Cheaper; WVA's scale-up picks this first |

The 40 → 30 delta (25%) is intentionally modest. A larger delta would make WVA's
preference overwhelming and the result trivial; a modest delta proves the mechanism
works at realistic price gradients.

Cost ordering `pool-B-gpu2 < pool-B-gpu1` is the *only* configuration WVA sees that
differs from Scenario 1. No priority classes, no cluster-level policy, no Limited mode.

### 12.5 Capacity Budget and Replica Caps

```
cluster budget (Option P2 example):
  premium partition: 2 GPU slots  (2 labeled nodes × 1 GPU)
  basic partition:   4 GPU slots  (4 labeled nodes × 1 GPU)

min / max replicas per variant:
  pool-A-gpu1: min=1, max=2    # Pool-A never exceeds 2; premium partition can hold it
  pool-B-gpu1: min=0, max=2    # KEDA may fill this, WVA should leave it at 0
  pool-B-gpu2: min=0, max=4    # WVA-preferred target for Pool-B scale-up
```

`min=0` on both Pool-B variants means Pool-B holds zero premium slots when Pool-B is
idle. At peak Pool-B load (5 replicas needed), `pool-B-gpu2` alone can provide 4 — one
short of ideal, exposing whether the autoscaler is willing to borrow 1 premium slot even
when it causes Pool-A contention.

### 12.6 Traffic Pattern

Three-phase trace, 18 minutes total:

```
Pool-B RPS                           Pool-A RPS
  20 |    _________________            8 |           __________
     |   /                 \             |          /          \
   1 |---                   ---       1 |---------              -----
        0    5   10  13   18  min          0    5  10 13     18  min
            ^rampB          ^end            ^idle ^join   ^end
```

| Phase | Duration | Pool-B RPS | Pool-A RPS | Purpose |
|---|---|---|---|---|
| P0 Idle | 2 min | 1 | 1 | Baseline; both at min replicas (Pool-A=1, Pool-B=0+0) |
| P1 Pool-B ramp | 5 min | 1 → 20 staircase | 1 | Pool-B scales up; WVA picks gpu2, KEDA may pick both |
| P2 Sustain + Pool-A join | 8 min | 20 | 1 → 8 staircase, sustain | **Critical phase** — Pool-A demands premium slots KEDA has already given to Pool-B |
| P3 Cooldown | 3 min | 1 | 1 | Both drop |

Both pools run GuideLLM concurrently throughout (separate jobs, same gateway target but
different model/pool labels routed via EPP).

Pool-A's ramp in P2 is the instrumented moment: KEDA has Pool-A sitting at 1 replica
trying to scale to 2, but premium partition is already full — Pool-A pod goes Pending.

### 12.7 WVA Configuration

Three VA resources across two namespaces. All share the same `modelID`, but Pool-A's VA
is in a different namespace — so WVA's cross-variant optimization runs **within Pool-B
only**. The starvation prevention is a side-effect of Pool-B choosing gpu2 for its own
cost-optimal scale-up. No cross-tenant coordination needed.

```yaml
# tenant-premium namespace
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata: { name: pool-A-gpu1, namespace: tenant-premium }
spec:
  modelID: meta-llama/Llama-3.1-8B-Instruct
  minReplicas: 1
  maxReplicas: 2
  targetRef: { apiVersion: apps/v1, kind: Deployment, name: pool-A-decode }
  accelerator: { type: ..., cost: 40 }
---
# tenant-basic namespace
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata: { name: pool-B-gpu1, namespace: tenant-basic }
spec:
  modelID: meta-llama/Llama-3.1-8B-Instruct
  minReplicas: 0
  maxReplicas: 2
  targetRef: { apiVersion: apps/v1, kind: Deployment, name: pool-B-gpu1-decode }
  accelerator: { type: ..., cost: 40 }
---
# tenant-basic namespace
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata: { name: pool-B-gpu2, namespace: tenant-basic }
spec:
  modelID: meta-llama/Llama-3.1-8B-Instruct
  minReplicas: 0
  maxReplicas: 4
  targetRef: { apiVersion: apps/v1, kind: Deployment, name: pool-B-gpu2-decode }
  accelerator: { type: ..., cost: 30 }
```

Analyzer configuration: identical to Scenario 1 (QueueingModel with explicit SLO 60ms,
Saturation v1 as guardrail). No Scenario-2-specific WVA tuning.

### 12.8 KEDA Baselines — Scenario 2

Three ScaledObjects (one per variant). Same tuning philosophy as § 4, but now with a
fourth mode that represents the honest best-effort KEDA countermeasure.

| Mode | Configuration |
|---|---|
| `keda-naive` | Single `vllm:num_requests_waiting > 3` trigger per ScaledObject. Symmetric on both Pool-B variants → scales both equally. |
| `keda-tuned` | Four triggers per ScaledObject (KV + queue + ITL p99 + token rate), 30s/180s stabilization. Still symmetric → still starves Pool-A. |
| `keda-tuned-capped` | Same as `keda-tuned`, but `pool-B-gpu1` ScaledObject has `maxReplicaCount: 0` — hard disables the premium-partition variant. Operator hand-applied based on knowledge of Pool-A's topology. |

**Why `keda-tuned-capped` is instructive, not a cheat:** it is what a careful operator
would *actually* do after being burned by starvation. It demonstrates the operational
cost of KEDA's lack of cross-variant awareness — you have to hand-configure limits based
on external knowledge. WVA solves this structurally via cost gradient.

### 12.9 Metrics — Scenario 2 Specific

Shared with Scenario 1: replica timelines per variant, KV%, queue depth, TTFT/ITL
percentiles, cost-weighted GPU-hours.

New metrics for Scenario 2:

| Metric | Formula / Source | What it shows |
|---|---|---|
| **Pool-A p99 ITL during P2** | `histogram_quantile(0.99, vllm:time_per_output_token_seconds_bucket{namespace="tenant-premium"})` | Primary SLO compliance for the premium tenant |
| **Pool-A pending replicas during P2** | `kube_deployment_status_replicas_unavailable{deployment="pool-A-decode"}` | Direct starvation indicator |
| **Pool-A pod scheduling latency** | time-to-Ready from Pending observed during P2 | How long Pool-A waits for a premium slot |
| **GPU1 partition occupancy by pool** | count pods where `nodeSelector.gpu.partition=premium`, grouped by owner namespace | Who is holding premium slots and when |
| **Pool-B variant split** | `replicas(pool-B-gpu2) / (replicas(pool-B-gpu1) + replicas(pool-B-gpu2))` | Visual of where Pool-B landed |
| **Pool-B p99 ITL during P1 and P2** | per-namespace ITL | Secondary — ensures the starvation protection didn't accidentally starve Pool-B |

### 12.10 Expected Results

Directional predictions; not committed targets.

| Metric | WVA | KEDA-naive | KEDA-tuned | KEDA-tuned-capped |
|---|---|---|---|---|
| Pool-A p99 ITL during P2 (ms) | ~55 | ≥180 or timeout | ≥150 | ~60 |
| Pool-A pending-replica-seconds during P2 | 0 | 200+ | 200+ | 0 |
| Pool-A SLO violation rate (P2) | <5% | >40% | >35% | <8% |
| Pool-B p99 ITL during P1 ramp (ms) | ~60 | ~60 | ~55 | **~80** |
| Pool-B gpu1 replicas at P1 peak | 0 | 2 | 2 | 0 |
| Pool-B gpu2 replicas at P1 peak | 4 | 3 | 3 | 4 |
| Total cost-weighted GPU-hours | 1.00 | 1.15 | 1.15 | 1.00 |

**Headline takeaways:**

1. **WVA vs KEDA-naive / KEDA-tuned:** Pool-A starvation is structural. ~40% Pool-A SLO
   violations vs WVA's <5%. Tuning KEDA's metrics does not fix this because no per-variant
   metric sees Pool-A's pressure.
2. **WVA vs KEDA-tuned-capped:** Pool-A parity, but Pool-B pays the price — its P1
   ramp is slower because one of its two variants is hard-capped. KEDA forces a **binary**
   trade-off (always cap or never cap); WVA's cost gradient gives **graceful** preference
   that still allows gpu1 usage when gpu2 alone is insufficient.
3. **The capped mode is the most honest KEDA competitor**, and it still loses on Pool-B
   latency. Lead the Scenario 2 story with the WVA vs capped-KEDA comparison.

### 12.11 Implementation Notes (Relative to § 8)

Scenario 2 reuses most of § 8 infrastructure. Incremental additions:

1. **Three variants (not two).** The `Variant` struct from § 8.2 is unchanged; the
   `variants []Variant` slice simply has three entries. `CostWeightedGPUHours`,
   `VariantTimeline[]`, per-variant timeline sampling all handle N variants.

2. **Two namespaces.** The harness currently assumes one `LLMDNamespace`. Add
   `LLMDNamespaceA` (`tenant-premium`) and `LLMDNamespaceB` (`tenant-basic`) env vars and
   plumb through fixtures. Two EPP instances deployed, one per namespace.

3. **Concurrent dual-pool GuideLLM orchestration.** Phase orchestration launches one
   GuideLLM job per pool per phase, running in parallel. `runPhase` becomes
   `runPhaseTwoPools` taking two `(poolName, rate, duration)` tuples. A phase completes
   only when both jobs finish.

4. **New mode: `keda-tuned-capped`.** Adds a `RampMode` constant; the ScaledObject builder
   applies `MaxReplicaCount: 0` specifically on `pool-B-gpu1`. Otherwise identical to
   `keda-tuned`.

5. **Node-partition labeling.** Precondition step that labels worker nodes
   `gpu.partition=premium|basic` before the test begins. Add
   `labelNodesForStarvationScenario(ctx, k8sClient, premiumCount, basicCount)` helper.

6. **Pool-A pending-replica metric.** Add a Prometheus query for
   `kube_deployment_status_replicas_unavailable` to the monitor loop.

**Estimated incremental effort over Scenario 1: 0.5–1 engineer-day.** Most of § 8 is
shared; only orchestration and labeling are new.

### 12.12 Kind Dry-Run Notes — Scenario 2

Default kind-emulator has 2 worker nodes, which is exactly enough to label one premium,
one basic. Adjust replica caps for the smaller cluster:

- `pool-A-gpu1`: max=1 (premium partition has 1 node × 1 GPU slot simulated)
- `pool-B-gpu1`: max=1
- `pool-B-gpu2`: max=2 (basic partition has 1 node; simulated 2-slot via deployment resource requests)

Compress phase durations to 60 / 180 / 240 / 90s (baseline/rampB/sustain+joinA/cooldown).

Starvation effect on kind is smaller (max=1 on each constrained variant), but the
pattern (WVA leaves pool-B-gpu1 at 0; KEDA scales it to 1 and blocks Pool-A) is
observable. Good for pipeline validation, not for publication numbers.

### 12.13 Risks and Caveats — Scenario 2

1. **Same-model assumption.** Using the same model for both pools in Option P2 removes
   model-capability confounds but makes the "Pool-A requires VRAM" rationale artificial.
   Document as a benchmark simplification; the production case uses different models.
   Option P1 fixes this if real heterogeneous GPUs are available.

2. **Pool-A never exceeds 2 replicas.** The demo needs only 1→2 scaling on Pool-A to
   expose the starvation; larger scale-up would need a bigger premium partition.

3. **WVA does not react to Pool-A pressure.** The prevention is entirely **static** —
   cost gradient steers Pool-B away from gpu1 before Pool-A's spike occurs. If Pool-B
   were already at full gpu1 capacity before Pool-A existed, WVA would not actively
   migrate Pool-B off gpu1. Phase 0 (both at 1 RPS) seeds Pool-B's first scale-up
   during P1, which is when the cost gradient takes effect. This initial-condition
   design is deliberate.

4. **Dynamic cross-tenant reallocation is out of scope for this round.** Active
   migration under a sudden Pool-A spike requires cross-model capacity accounting that
   lives in WVA's Limited mode. See `session/CURRENT.md § Benchmark future directions`.

5. **`keda-tuned-capped` is not portable.** It requires the operator to know in advance
   which tenant is constrained to which partition. In a real multi-tenant cluster with
   frequent tenant turnover this is unmaintainable. WVA's cost-gradient approach is
   self-maintaining — new tenants get cost assignments and the structural preference
   falls out automatically.

---

## 13. Benchmark Possibilities on a Uniform Cluster

On a cluster where all GPUs are the same type (e.g., all A100 or all H100), WVA's
heterogeneous cost-variant selection does not apply directly — every replica carries the
same cost weight. This section explores which WVA advantages remain demonstrable and
which require heterogeneous hardware.

---

### 13.1 What WVA Still Demonstrates on Uniform Hardware

**Scenario 2 (Starvation Prevention) works unchanged.**
Scenario 2 uses label-based partitioning (Option P2 — the default). GPU nodes are
labeled `gpu.partition=premium|basic` and cost weights reflect labels, not hardware.
On a cluster of identical GPUs, Pool-B's cost gradient (pool-B-a100=40 < pool-B-h100=65
in heterogeneous terms; on uniform hardware the labels take those roles) still steers
Pool-B away from the premium partition. The starvation-prevention argument is fully
demonstrable on homogeneous hardware. This is already the recommended default for
Scenario 2 in § 12.3.

**SLO-aware replica efficiency (Scenario U1).**
WVA's queueing model provisions exactly the number of replicas needed to meet the target
p99 ITL. KEDA-tuned defends aggressively by setting a conservative KV threshold (e.g.,
70%) and scaling up before the SLO is actually at risk. This over-provisioning is
measurable even on uniform hardware.

- Setup: single pool, single model, uniform GPU type, same 30-min ramp.
- Metric: total replica-hours at equivalent p99 ITL compliance.
- Expected advantage: WVA ~10–20% fewer replica-hours than KEDA-tuned; KEDA-naive
  has better utilization but worse SLO compliance during the ramp.
- Limitation: without a cost-weight multiplier (all replicas cost the same), the
  absolute dollar difference is smaller than in Scenario 1. The story is "efficiency"
  rather than "cost".

---

### 13.2 Scenario U1 — SLO-Efficient Scaling (Uniform Hardware)

**The question.** Does WVA provision fewer total replicas than KEDA at equivalent p99
ITL, even when all GPUs cost the same?

**The experiment.**
- Same model, single GPU type (e.g., all A100), single pool, two VAs (or one VA with
  uniform cost weights).
- Same 30-min staircase ramp (3 → 25 RPS).
- WVA (QueueingModel, `targetITL=60ms`) vs KEDA-naive vs KEDA-tuned.
- Metric: total replica-hours (= replica count integrated over time) at equivalent SLO.

**Why KEDA over-provisions.**
KEDA-tuned fires a scale-up when KV% exceeds the threshold (e.g., 70%). But the
relationship between KV% and p99 ITL is non-linear — at 70% KV a well-batched vLLM
instance can still meet 60 ms ITL. KEDA does not know this; WVA's queueing model does.
Result: KEDA-tuned adds replicas before they are needed and holds them through the
stabilisation window.

**Expected results.**

| Metric | WVA | KEDA-naive | KEDA-tuned |
|---|---|---|---|
| P99 ITL during ramp (ms) | ~55 | ~80 | ~60 |
| Replicas at peak | 3 | 3 | 4 |
| Total replica-hours (normalized) | 1.00 | 0.95 | 1.18 |
| SLO violation rate | ~2% | ~10% | ~3% |

WVA sits on the Pareto frontier: fewer replica-hours than KEDA-tuned, fewer SLO
violations than KEDA-naive.

**Limitation vs Scenario 1.** Without the L40:H100 cost ratio (1:4.3), the replica-hour
difference (~18%) is modest. The narrative must shift from "cost" to "SLO-precision" —
defensible but less dramatic. Scenario 1 on heterogeneous hardware is the stronger
headline; Scenario U1 is a supporting argument or a fallback for teams without mixed
GPU inventory.

---

### 13.3 Scenario U3 — Proactive Detection on Rapid Ramps (Requires TA3)

**When ThroughputAnalyzer (TA3) is available**, a uniform cluster can demonstrate WVA's
proactive-detection advantage on sharp demand spikes.

**The question.** Does WVA's rate-based early warning (token-arrival acceleration in the
scheduler queue) allow faster scale-up than KEDA's threshold-based triggers, reducing
p99 ITL spikes during sudden load increases?

**The experiment.**
- Single pool, uniform GPUs.
- Traffic: sharp step increase (+3× in under 60 s), not a gradual ramp.
- WVA (QueueingModel + ThroughputAnalyzer) vs KEDA-tuned.
- Metric: time-to-first-new-replica-Ready from step onset; p99 ITL peak and duration
  during the step.

**Why this works on uniform hardware.** The ThroughputAnalyzer detects demand
acceleration in the scheduler queue before KV pressure builds. KEDA cannot act until a
metric threshold is breached. The faster response is measurable regardless of GPU type.

**Status.** Requires TA3 (PR-4 + PR-5) to merge. Intended as a follow-up run after the
main Scenario 1 results are published.

---

### 13.4 Summary: Uniform vs Heterogeneous Cluster

| Scenario | Uniform cluster | Heterogeneous cluster | Primary metric |
|---|---|---|---|
| Scenario 1 — Cost-optimal ramp | ✗ Weak (no cost multiplier) | ✅ **Strong** | Cost-weighted GPU-hours |
| Scenario 2 — Starvation prevention | ✅ Works (Option P2) | ✅ Works (Option P1 or P2) | Pool-A SLO violations |
| Scenario U1 — SLO efficiency | ✅ Moderate | ✅ Included in Scenario 1 | Total replica-hours |
| Scenario U3 — Proactive detection | ✅ Strong (post-TA3) | ✅ Also demonstrable | Scale-up latency, ITL spike |

For teams with a uniform cluster: **run Scenario 2 first** (same code, label-partitioned
nodes, directly demonstrates the structural starvation-prevention argument). Add Scenario
U1 as a secondary result. Defer Scenario U3 until TA3 merges.
