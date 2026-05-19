# WVA-vs-KEDA Benchmark — Team Discussion

**Audience:** benchmarking team. **Length:** 5–10 min. **Goal:** agree on what the
benchmarking stack needs to support, identify gaps, decide who builds what.

Source plan: `plans/planning/benchmark-wva-vs-keda-plan.md` (full design, ~1700 lines).

---

## 1. The two scenarios

**Scenario 1 — Cost-optimal ramp.** One pool, two variants of the same model (A100 + H100).
A 30-minute staircase ramp (3 → 25 RPS) exposes whether WVA selects the cheap variant (A100)
while KEDA grows both in parallel. Metric: cost-weighted GPU-hours at equivalent p99 ITL.

**Scenario 2 — Starvation prevention.** Two pools sharing the cluster. Pool-B (basic
tenant) has two variants spanning two GPU partitions; Pool-A (premium tenant) is
constrained to the premium partition. Pool-B ramps first; Pool-A joins while Pool-B is at
peak. Does WVA's cost gradient steer Pool-B away from the premium partition before Pool-A
needs those slots? Metric: Pool-A SLO violation rate during the joint-load phase.

| | Scenario 1 | Scenario 2 |
|---|---|---|
| Pools | 1 | 2 (Pool-A, Pool-B) |
| llm-d stacks (EPPs) | 1 | 2 (one per pool) |
| Deployments / variants | 2 (A100 + H100, same pool) | 3 (pool-A-h100; pool-B-a100 + pool-B-h100) |
| Traffic drivers | 1 GuideLLM, 4 sequential phases | 2 GuideLLM jobs, concurrent, 3 phases each |
| Run length | 30 min × 3 modes | 18 min × 4 modes |
| Compared modes | wva / keda-naive / keda-tuned | wva / keda-naive / keda-tuned / keda-tuned-capped |

Both scenarios: model `Llama-3.1-8B-Instruct`, decode-heavy (1000 in / 4000 out),
Poisson, llm-d v0.6.0, existing Prom/Grafana stack.

---

## 2. What the benchmarking stack needs to support

### 2.1 Quick list

**Scenario 1:**
1. Deploy an llm-d pool backed by two deployments, selected by a shared label (modelID).
2. Deploy WVA managing those two deployments as variants of the same model.
3. Configure and apply KEDA policies (static manifests, 2 modes).
4. Drive a multi-phase staircase ramp with a single GuideLLM driver.
5. Collect per-variant metrics (replica count, KV%, queue depth) throughout the run.
6. Reserve GPU nodes for the benchmark — prevent other workloads from taking freed slots.
7. Run all three modes sequentially on the same cluster; produce comparable outputs.

**Scenario 2 adds:**
8. Deploy a second llm-d pool (second EPP) in the same namespace.
9. Partition GPU nodes (label-based or real heterogeneous hardware).
10. Drive two concurrent GuideLLM chains (one per pool), aligned on phase boundaries.
11. Capture Pool-A pending-replica events during the joint-load phase.
12. Support a fourth KEDA mode (`keda-tuned-capped`) that hard-limits pool-B's access to
    the premium partition.

### 2.2 llm-d pool + WVA setup (detail)

An llm-d pool selects its backends by label. For this benchmark, each deployment carries
a label identifying its pool (e.g., `benchmark/model-pool: llama8b-pool-b`); the pool's
selection criteria matches all deployments with that label. WVA's VariantAutoscaling
resources each target one deployment and carry the same `modelID` — that is how WVA
groups variants for cross-variant optimization.

**Scenario 1:** one pool label, two deployments (A100 cost=40, H100 cost=65), two VAs, one EPP.

**Scenario 2:** two pool labels.
- Pool-A: one deployment (H100/premium partition, cost=65), one VA.
- Pool-B: two deployments — pool-B-a100 (A100/basic partition, cost=40, preferred by WVA)
  and pool-B-h100 (H100/premium partition, cost=65, avoided by WVA) — two VAs sharing
  Pool-B's `modelID`. WVA's cross-variant optimization runs within Pool-B; Pool-A is a
  separate model.
- Two EPPs (one per pool), both in the same namespace.

### 2.3 KEDA configuration (detail)

KEDA ScaledObjects are static YAML manifests — benchmark code does not construct them.
Each mode is a directory of manifests applied before a run:

```
fixtures/keda/
  naive/           one ScaledObject per variant, queue-depth trigger only
  tuned/           four triggers (KV + queue + ITL p99 + token rate) + stabilisation
  tuned-capped/    Scenario 2 only — pool-B-h100 hard-capped at maxReplicaCount=0
```

Benchmark code applies the right directory before a run and deletes after. KEDA is
otherwise opaque to the harness. KEDA operator installation is a cluster prerequisite.

### 2.4 Traffic driving (detail)

Multi-phase ramp as chained GuideLLM jobs (one job per phase, different `--rate`).
No schema extension needed. Scenario 2 requires two job chains running concurrently,
one per pool. A phase completes when both pool jobs finish (see H1/H2 in § 4).

### 2.5 GPU reservation (detail)

Scale-down during a run frees GPU slots. Those slots must not be grabbed by other
workloads between scale cycles or between modes. Options:
- Taint benchmark nodes (`benchmark=reserved:NoSchedule`) with matching tolerations on
  benchmark deployments.
- Dedicated cluster.

Cluster setup prerequisite; needs an owner.

---

## 3. Gaps vs. the current harness

Source: § 5.4 and § 12.11 of the plan, mapped onto `test/benchmark/`.

### 3.1 Already works

GuideLLM JSON parsing; Prometheus range-query helper; pod→GPU mapping;
Grafana snapshot capture; deployment-listing in the monitor loop.

### 3.2 Missing — both scenarios

**G1 — Per-variant metrics split (primary gap)**

Today the monitor loop aggregates replica counts and vLLM metrics across all deployments.
We need the same data kept separate per deployment. The replacement structure carries, per
deployment: GPU type, cost weight, a replica snapshot every 15 s, and a metrics snapshot
every 15 s (KV%, vLLM queue depth, EPP queue depth). The monitor loop already queries
per-deployment data — it just aggregates it now. This split is required for cost-weighted
GPU-hour calculation and for the per-variant replica timeline charts.

| # | Gap | What's needed |
|---|---|---|
| G1 | Per-variant metrics split | Per-deployment replica + metrics timelines (see above) |
| G2 | Multi-phase segmentation | Phase boundary tracking + per-phase percentiles from each GuideLLM job |
| G3 | Cost-weighted GPU-hour aggregator | Sum `replicas × cost_weight × Δt` over all variants |
| G4 | KEDA manifest apply/delete hook | Test setup/teardown calls `kubectl apply/delete -f fixtures/keda/<mode>/` |
| G5 | Mode-selectable orchestration | `AUTOSCALER_MODE` env var selects which fixtures to apply and which WVA/KEDA resources to create |

### 3.3 Missing — Scenario 2 only

| # | Gap | What's needed |
|---|---|---|
| G6 | Second EPP fixture | Deploy + wait-for-ready for a second EPP in the same namespace |
| G7 | Concurrent dual-pool driver | Two GuideLLM job chains running in parallel; phase ends when both finish |
| G8 | Node-partition labeling | Label nodes `gpu.partition=premium\|basic` before test; revert on teardown |
| G9 | Per-variant `nodeSelector` | Selector field threaded through deployment fixtures |
| G10 | Pool-A pending-replica metric | `kube_deployment_status_replicas_unavailable` added to monitor loop |
| G11 | `keda-tuned-capped` mode | Separate manifest set; `maxReplicaCount: 0` on pool-B-h100 ScaledObject |

### 3.4 Lower priority — output analysis

Cross-mode comparison: markdown table + replica-stack PNGs + cost-vs-latency scatter.
Can be done manually for a first run; automate later if the benchmark becomes recurring.

---

## 4. Open questions for the team

1. **Pool label + llm-d selection:** does the pool CRD support label-based backend
   selection? What label key/value do we use?
2. **Two EPPs, same namespace (Scenario 2):** does llm-d support this? How is tenant
   routing (Pool-A vs Pool-B traffic) separated at the gateway?
3. **GPU reservation:** node taints or dedicated cluster? Who configures?
4. **Harness driver shape (Scenario 2):** H1 (single harness, both pools in one test,
   aligned phase boundaries) vs. H2 (two harness instances, external phase coordination)?
5. **KEDA manifests:** existing fixtures anywhere in the repo, or build from scratch?
6. **Sizing:** cluster has 2×L40, 24×A100, 16×H100. Scenario 1 needs ~6 A100 + 3 H100;
   Scenario 2 needs H100 nodes as premium partition + A100 nodes as basic partition.
   How many nodes to dedicate, and for how long?

---

## 5. Not in scope for this round

- ThroughputAnalyzer (TA3) — re-run after TA3 merges.
- Dynamic cross-tenant reallocation — needs WVA Limited mode (not yet implemented).
- Modifying WVA controller code. This work is driver-only: `test/benchmark/`, `hack/`,
  fixtures, cluster setup.
