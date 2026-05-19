---
type: Type-1 (design)
status: Draft — awaiting review
date: 2026-05-19
scope: Benchmark approach — WVA vs KEDA across heterogeneous and homogeneous GPU pools
impl-refs:
  - planning/benchmark-wva-vs-keda-plan.md   (implementation reference — all details)
---

# WVA vs KEDA — Benchmark Approach

**Implementation details** are in [`benchmark-wva-vs-keda-plan.md`](benchmark-wva-vs-keda-plan.md).
This document covers the approach, structural argument, scenario design, expected behavior,
design decisions, and a high-level list of what needs to be built.

---

## 1. The Question

Can a well-tuned KEDA configuration match WVA on an LLM inference workload served by
a pool of variants? Or is there a structural gap that KEDA cannot close by tuning alone?

The hypothesis: KEDA's architecture — one ScaledObject per deployment — prevents it from
making globally optimal scaling decisions. WVA, which sees all variants as one pool, will
consistently reach a better cost-capacity trade-off at equal SLO compliance.

---

## 2. Why WVA Is Expected to Win

Three structural properties give WVA an advantage that KEDA cannot close by tuning.

### 2.1 The Simultaneous-Saturation Trap

llm-d's EPP routes requests to minimise KV pressure across backends. Over time, this
equalises KV% utilisation across all variants in the pool — variants serving the same
model always converge to the same utilisation percentage.

Consequence: **whenever one variant is saturated, all variants are saturated simultaneously.**
KEDA's independent ScaledObjects each see their own variant above the threshold and both
fire. Both variants scale up — even though adding capacity to just one would have been
sufficient.

WVA computes a single aggregate demand/supply ratio across all variants (saturation_v2).
Its optimizer adds capacity to the cheapest variant until the aggregate ratio drops below
the threshold, then stops. It never reaches the over-provisioned state that KEDA's
simultaneous firing creates.

This over-provisioned state is locally stable: after KEDA scales both variants up, each
is well below the threshold. Neither ScaledObject can justify scaling its own variant
down, because doing so would re-saturate it. KEDA is trapped; WVA was never there.

### 2.2 Cost-Ordered Allocation

WVA's optimizer fills the cheapest variant first whenever capacity needs to be added,
only moving to expensive variants after the cheap one is at its maximum.

KEDA has no cost model. Each ScaledObject responds to its own variant's metrics. By the
equalisation property, both variants are always saturated at the same time, so KEDA
always scales both — regardless of which is cheaper.

### 2.3 Pending-Replica Awareness and Cost-Ordered Scale-Down

When a replica is starting (pending, ~60–90 s startup), WVA includes it in the
anticipated supply and suppresses further scale-up until it comes online. KEDA's
ScaledObjects cannot see the other variant's pending replicas; they fire additional
scale-ups during the startup window.

On scale-down, WVA releases the most expensive variant's replicas first. KEDA scales
each variant down independently through its own stabilisation windows.

---

## 3. Scenarios

### 3.1 Scenario 1 — Cost-Optimal Ramp

**What it shows.** The simultaneous-saturation trap and cost-ordered allocation on a
two-variant pool with a significant cost-ratio gap (1:4.3).

**Setup.** One pool, two variants: L40 48 GB (cost=15, max 2 replicas) + H100 80 GB
(cost=65, max 3 replicas). Model: Llama-3.1-8B-Instruct, decode-heavy (1000 in / 4000
out), 30-minute staircase ramp from 3 → 35 RPS.

**Why 35 RPS peak.** At 35 RPS with 1L40+1H100 (32 RPS capacity), both variants are at
109% utilisation — both KEDA ScaledObjects fire simultaneously. After KEDA scales to
2L40+2H100 (64 RPS), utilisation is 55% — each variant is below its own scale-down
threshold, so neither can scale down independently. KEDA is trapped.

WVA's aggregate fires once, adds L40 only, and holds stably at 2L40+1H100 (44 RPS, 80%
utilisation — between the 70% scale-down and 85% scale-up boundaries).

**The claim.** WVA holds stably at 2L40+1H100 (cost 95/interval). KEDA is trapped at
2L40+2H100 (cost 160/interval). **~40% steady-state cost reduction** at equivalent p99 ITL.

**The picture.** Replica-count timeline at Phase 2 peak: WVA H100=1 (flat), KEDA H100=2
(over-provisioned). Same p99 ITL. The one extra H100 that KEDA holds unnecessarily costs
65 units per interval — persistent, steady-state waste.

### 3.2 Scenario 2 — Starvation Prevention

**What it shows.** WVA's cost gradient passively protects a premium-tenant workload from
being starved by a basic-tenant workload sharing the cluster, without any explicit
cross-tenant configuration.

**Setup.** Two pools in one namespace: Pool-A (premium tenant, constrained to premium GPU
partition, cost=65) + Pool-B (basic tenant, two variants: B-h100 on premium partition
cost=65, B-a100 on basic partition cost=40). Same model. Pool-B ramps first; Pool-A
joins 10 min later.

**The mechanism.** WVA's cost gradient steers Pool-B to B-a100 (cost=40) because it is
cheaper. Premium partition slots stay free for Pool-A when it scales. KEDA scales Pool-B
symmetrically across both partitions, consuming premium slots. Pool-A replica pods go
Pending when they try to scale.

`keda-tuned-capped` (hard cap B-h100 at maxReplicaCount=0) matches WVA on Pool-A
protection but sacrifices Pool-B's own ramp latency — a binary trade-off WVA avoids.

**The claim.** WVA Pool-A SLO violation rate < 5% during joint-load phase. KEDA-naive/
tuned: > 35%. keda-tuned-capped: ~8% but Pool-B p99 ITL is 20–30% higher than WVA's.

### 3.3 Scenario Variants

**No hardware cap.** The L40 hardware limit is not special. Setting `maxReplicas: 2` in
the VA spec achieves identical benchmark behaviour on any cluster with more than 2 L40
nodes. The cap forces H100 to carry meaningful load so the simultaneous-saturation trap
can manifest; it does not need to be physical.

**Homogeneous cluster.** Assign different cost weights to two logical variants backed by
identical physical GPUs. Example on all-A100: `cost=15` (default tier) + `cost=65`
(premium tier), identical throughput per replica. EPP equalization still holds; KEDA
still fires both; WVA still prefers the cheap tier.
At 35 RPS from 1+1 (24 RPS capacity): KEDA → 2+2 (cost 160), WVA → 3+1 (cost 110) —
**31% saving at steady state, no heterogeneous hardware required.**
The cost weights model any organisational tiering: quota pools, billing centres, SLA
classes. See implementation reference § 13.

**Three-tier extension (L40 + A100 + H100).** After Scenario 1 is published, a follow-up
run with a third A100 mid-tier variant shows WVA climbing the cost ladder: exhausts L40
before A100, A100 before H100. See implementation reference § 10.1.

---

## 4. Expected Behavior and Cost Estimates

### 4.1 Scenario 1 — Phase Table

| Phase | Load | WVA | KEDA | WVA cost | KEDA cost |
|---|---|---|---|---|---|
| P0 Baseline (5 min) | 3 RPS | 1+1, idle | 1+1, idle | 80 | 80 |
| P1 Ramp (7 min) | 3→35 RPS | L40 only scales at each step; H100=1 | L40 AND H100 scale at each step; H100 spikes to 2 | ~87 avg | ~120 avg |
| P2 Peak (10 min) | 35 RPS | **2L40+1H100, stable (80% util)** | **2L40+2H100, trapped (55% util)** | **95** | **~160** |
| P3 Drop (8 min) | 35→3 RPS | L40 scales down; H100 already at min=1 | H100 held at 2 for 3–5 min (stabilisation) | ~85 avg | ~120 avg |
| **Normalized total** | | | | **1.00** | **~1.44** |

| Outcome metric | WVA | KEDA-naive | KEDA-tuned |
|---|---|---|---|
| P99 ITL during ramp (ms) | ~55 | ~90 | ~65 |
| P99 ITL at peak (ms) | ~55 | ~58 | ~55 |
| H100 replicas at peak (steady state) | **1** | **2** | **2** |
| Cost-weighted GPU-hours (normalized) | **1.00** | 1.40–1.50 | 1.35–1.44 |
| SLO violation rate during ramp | ~2% | ~15% | ~4% |

### 4.2 Scenario 2 — Phase Table

| Phase | Pool-B RPS | Pool-A RPS | WVA | KEDA |
|---|---|---|---|---|
| P0 Idle (2 min) | 1 | 1 | Both at min | Both at min |
| P1 Pool-B ramp (5 min) | 1→20 | 1 | Pool-B scales on B-a100 (cheap) | Pool-B scales on both B-h100 and B-a100 |
| P2 Sustain + Pool-A join (8 min) | 20 | 1→8 | Pool-A scales into free premium slots | Pool-A pods go **Pending** — premium slots taken |
| P3 Cooldown (3 min) | 1 | 1 | Clean scale-down | Scale-down with stabilisation lag |

| Outcome metric | WVA | KEDA-naive | KEDA-tuned | keda-tuned-capped |
|---|---|---|---|---|
| Pool-A p99 ITL at P2 (ms) | ~55 | ≥180 | ≥150 | ~60 |
| Pool-A SLO violations (P2) | <5% | >40% | >35% | <8% |
| Pool-B p99 ITL ramp (ms) | ~60 | ~60 | ~55 | **~80** |

---

## 5. Key Assumptions

### 5.1 Hardware and Cost Model

Cluster inventory: 2×L40, 24×A100, 16×H100.

| Variant | GPU | Cost weight | Max replicas | Approx RPS capacity | Used in |
|---|---|---|---|---|---|
| `llama8b-l40` | NVIDIA L40 48 GB | 15 | 2 (hardware cap) | ~12 | S1 cheap tier |
| `llama8b-h100` | NVIDIA H100-80GB SXM | 65 | 3 | ~20 | S1 expensive tier |
| `pool-A-h100` | NVIDIA H100-80GB | 65 | 2 | ~20 | S2 premium tenant |
| `pool-B-h100` | NVIDIA H100-80GB | 65 | 2 | ~20 | S2 basic, premium partition |
| `pool-B-a100` | NVIDIA A100-80GB | 40 | 4 | ~12 | S2 basic, basic partition |

### 5.2 Workload

Model: `meta-llama/Llama-3.1-8B-Instruct` · Shape: decode-heavy, 1000 in / 4000 out,
Poisson · SLO: p99 ITL < 60 ms · llm-d: v0.6.0.

### 5.3 WVA Configuration

Single analyzer: **saturation_v2** (`analyzerName: "saturation"`).
`scaleUpThreshold=0.85`, `scaleDownBoundary=0.70`, `kvCacheThreshold=0.80`,
`queueLengthThreshold=5`. Full ConfigMap in implementation reference § 3.2.

### 5.4 KEDA Baselines

| Mode | Triggers | Purpose |
|---|---|---|
| `keda-naive` | vLLM queue depth | Strawman |
| `keda-tuned` | KV% (0.70) + queue + ITL p99 + token rate; 180–300 s stabilisation | Honest competitor |
| `keda-tuned-capped` | Same as tuned; B-h100 hard-capped at maxReplicaCount=0 | Scenario 2 only — manual workaround |

Full ScaledObject YAML in implementation reference § 4.

---

## 6. Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Analyzer | saturation_v2 alone | Isolates cost-variant mechanism; don't benchmark multi-analyzer |
| Peak RPS | 35 (not 25) | 25 RPS → 57% utilisation at 2+1, below both thresholds, no steady-state gap |
| S1 variants | L40 + H100 | Best available cost ratio (1:4.3) from cluster inventory |
| L40 max replicas | 2 (hardware cap, enforceable via VA spec) | Forces H100 to carry meaningful load; without a cap WVA never loads H100 |
| Traffic | Staircase ramp via chained GuideLLM jobs | No schema change; each step fires the simultaneous-saturation trap |
| KEDA-tuned KV threshold | 0.70 (vs WVA's 0.85 aggregate) | KEDA must be conservative; giving it a lower threshold is the honest concession |
| ThroughputAnalyzer | Disabled | TA3 not merged; re-run after merge to expose proactive-detection gap |
| S2 hardware | Homogeneous + label partition (Option P2) | Runs on any cluster; starvation mechanism is identical |
| QueueingModel analyzer | Follow-up run | Not ready; when available, re-run S1 — expected to show larger steady-state gap |

---

## 7. Missing Benchmarking Capabilities (High-Level)

The current `test/benchmark/` harness supports single-pool, single-variant, single-phase
benchmarks. Gaps to close before this benchmark can run:

**Both scenarios:**
1. Per-variant replica + metrics timelines (currently one aggregate)
2. Multi-phase chained GuideLLM orchestration
3. Cost-weighted GPU-hour aggregator
4. KEDA manifest apply/delete lifecycle hook
5. Mode-selectable test orchestration (`AUTOSCALER_MODE` env var)

**Scenario 2 only:**
6. Second EPP deployment fixture
7. Concurrent dual-pool phase driver (two GuideLLM chains, phase ends when both finish)
8. Node-partition labeling step
9. Pool-A pending-replica metric

**Lower priority (can be done manually for first run):**
10. Cross-mode comparison report (markdown + PNG charts)

Detailed implementation for each gap: implementation reference § 5.4 (both scenarios)
and § 12.11 (Scenario 2 incremental).

---

## 8. Implementation References

| Topic | Location |
|---|---|
| Full Scenario 1 design (traffic, configs, sizing, dry-run) | [`benchmark-wva-vs-keda-plan.md`](benchmark-wva-vs-keda-plan.md) § 2–9 |
| Coder implementation guide (file layout, Go types, Ginkgo skeleton, Makefile) | § 8 |
| Kind dry-run guide | § 6 |
| OpenShift sizing options | § 7.5 |
| Scenario 2 full design | § 12 |
| Three-tier optional extension | § 10.1 |
| Homogeneous cluster scenarios | § 13 |
| Harness gaps detail | § 5.4, § 12.11 |
| Team discussion doc (benchmarking team) | [`scratch/benchmark-team-discussion.md`](../scratch/benchmark-team-discussion.md) |

---

## 9. Approval Gate

Before any code is written:
1. Dean reviews this approach doc and the relevant sections of the implementation reference.
2. Open questions are resolved in discussion.
3. Dean gives an **explicit** instruction to begin implementation.
4. Frontmatter `status` in the implementation reference changes from "Draft — NOT AUTHORIZED"
   to "Approved — ready for implementation" and the STOP block is removed.
