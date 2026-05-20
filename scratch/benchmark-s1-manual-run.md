# Scenario 1 — Manual Run Instructions

**Goal:** Run the WVA-vs-KEDA cost-optimal ramp benchmark manually against a real OpenShift
cluster, observing autoscaler behavior across three modes (WVA / KEDA-naive / KEDA-tuned).

**What this document is not:** a full automation plan. It is a step-by-step human procedure
to run the benchmark once so we can observe real behavior and identify what to automate next.

Design reference: `planning/benchmark-wva-vs-keda.md` (approach) and
`planning/benchmark-wva-vs-keda-plan.md` § 2–4 (full details).

---

## Prerequisites

- OpenShift cluster access with L40 and H100 GPU nodes
- `oc`, `helm`, `yq`, `jq`, `go` installed locally
- HuggingFace token with access to `meta-llama/Llama-3.1-8B-Instruct`
- KEDA operator installed on the cluster (or arrange with cluster admin)
- Repository cloned and on `main` branch

```bash
git clone https://github.com/llm-d/llm-d-workload-variant-autoscaler.git
cd llm-d-workload-variant-autoscaler
oc login --token=<token> --server=<url>
export HF_TOKEN="hf_..."
export NS="llmd-bench"   # namespace to use throughout
```

Check GPU node availability:
```bash
oc get nodes -o jsonpath='{range .items[?(@.status.allocatable.nvidia\.com/gpu)]}{.metadata.name}{"\t"}{.metadata.labels.nvidia\.com/gpu\.product}{"\n"}{end}'
```
Confirm you have nodes with `NVIDIA-L40` and `NVIDIA-H100` labels.

---

## Part 1: Infrastructure Setup (once for all three modes)

### 1.1 Install benchmark CLI

```bash
make benchmark-install
```

### 1.2 Stand up llm-d infrastructure

This deploys the EPP, gateway, Prometheus monitoring, and one default model deployment
(`meta-llama/Llama-3.1-8B-Instruct` on H100). We will extend it with the L40 variant
manually.

```bash
oc new-project $NS 2>/dev/null || oc project $NS
oc label namespace $NS openshift.io/user-monitoring=true --overwrite
make benchmark-standup \
  BENCHMARK_NAMESPACE=$NS \
  MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
```

Wait for `✅ All smoketest steps complete.`

### 1.3 Inspect what standup created

```bash
oc get deployment -n $NS
oc get variantautoscaling -n $NS
oc get hpa -n $NS
oc get configmap -n $NS | grep saturation
```

Make note of:
- The H100 deployment name (likely `ms-inference-scheduling-llm-d-modelservice` or similar)
- Whether a VA and HPA already exist for it
- The exact accelerator label on the H100 node: `oc get node <h100-node> -o jsonpath='{.metadata.labels.nvidia\.com/gpu\.product}'`
- The exact accelerator label on the L40 node: same command

### 1.4 Create the L40 deployment

Export the H100 deployment as a base:
```bash
oc get deployment <h100-deployment-name> -n $NS -o yaml > /tmp/deploy-h100.yaml
```

Create the L40 deployment by editing the exported YAML:
- Change `metadata.name` to `ms-bench-llama8b-l40`
- Change `spec.template.spec.nodeSelector["nvidia.com/gpu.product"]` to the L40 label
- Remove `metadata.resourceVersion`, `metadata.uid`, `metadata.generation`,
  `metadata.creationTimestamp`, `status`
- Set `spec.replicas: 1`

```bash
# Edit /tmp/deploy-h100.yaml as above, then:
oc apply -f /tmp/deploy-l40.yaml
```

Also rename the H100 deployment for clarity (or just note its name):
```bash
# H100 deployment: <original-name>   (keep as-is)
# L40 deployment:  ms-bench-llama8b-l40   (just created)
H100_DEPLOY=<original-h100-deployment-name>
L40_DEPLOY=ms-bench-llama8b-l40
```

Wait for the L40 model server to be Ready (model load takes 5–10 min):
```bash
oc rollout status deployment/$L40_DEPLOY -n $NS
```

---

## Part 2: WVA Mode Setup

### 2.1 Patch saturation ConfigMap to use saturation_v2

The standup creates a saturation ConfigMap with v1 defaults. Override it for the benchmark:

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: wva-saturation-scaling-config
  namespace: workload-variant-autoscaler-system
data:
  default: |
    analyzerName:         saturation
    kvCacheThreshold:     0.80
    queueLengthThreshold: 5
    scaleUpThreshold:     0.85
    scaleDownBoundary:    0.70
EOF
```

Restart the WVA controller to pick up the new config:
```bash
oc rollout restart deployment/workload-variant-autoscaler-controller-manager \
  -n workload-variant-autoscaler-system
oc rollout status deployment/workload-variant-autoscaler-controller-manager \
  -n workload-variant-autoscaler-system
```

### 2.2 Create VariantAutoscaling resources

If standup already created a VA for the H100 deployment, delete it and recreate with correct
cost weights. If not, create both from scratch.

```bash
# Replace <h100-accelerator-label> with the exact value from step 1.3
cat <<EOF | oc apply -f -
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: llama8b-h100
  namespace: $NS
spec:
  modelID: "meta-llama/Llama-3.1-8B-Instruct"
  minReplicas: 1
  maxReplicas: 3
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $H100_DEPLOY
  variantCost: "65.0"
---
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: llama8b-l40
  namespace: $NS
spec:
  modelID: "meta-llama/Llama-3.1-8B-Instruct"
  minReplicas: 1
  maxReplicas: 2
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $L40_DEPLOY
  variantCost: "15.0"
EOF
```

### 2.3 Create HPA resources for WVA pass-through

One HPA per variant, targeting the `wva_desired_replicas` metric (WVA writes this; HPA
acts as the actuator). Copy the pattern from `config/samples/keda/scaledobject.yaml`
but use HPA instead.

```bash
# Get the Prometheus server address:
PROM_ADDR=$(oc get svc -n workload-variant-autoscaler-monitoring \
  kube-prometheus-stack-prometheus \
  -o jsonpath='https://{.spec.clusterIP}:9090')

cat <<EOF | oc apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wva-hpa-h100
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $H100_DEPLOY
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: External
    external:
      metric:
        name: wva_desired_replicas
        selector:
          matchLabels:
            variant_name: "$H100_DEPLOY"
            exported_namespace: "$NS"
      target:
        type: AverageValue
        averageValue: "1"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 0
    scaleUp:
      stabilizationWindowSeconds: 0
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wva-hpa-l40
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $L40_DEPLOY
  minReplicas: 1
  maxReplicas: 2
  metrics:
  - type: External
    external:
      metric:
        name: wva_desired_replicas
        selector:
          matchLabels:
            variant_name: "$L40_DEPLOY"
            exported_namespace: "$NS"
      target:
        type: AverageValue
        averageValue: "1"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 0
    scaleUp:
      stabilizationWindowSeconds: 0
EOF
```

> **Note:** The exact metric labels (`variant_name`, `exported_namespace`) depend on what WVA
> emits in your version. Check with:
> `oc exec -n workload-variant-autoscaler-monitoring <prometheus-pod> -- \
>   wget -qO- 'http://localhost:9090/api/v1/label/variant_name/values'`
> Adjust labels accordingly.

### 2.4 Verify WVA is watching both variants

```bash
oc get variantautoscaling -n $NS
oc logs -n workload-variant-autoscaler-system \
  deployment/workload-variant-autoscaler-controller-manager --tail=30 | grep -i "llama8b"
```

Expect to see both `llama8b-l40` and `llama8b-h100` variants registered.

---

## Part 3: Create Phase Scenario Files

The existing `decode_heavy.yaml` runs at a fixed 20 RPS for 600s. We need one file per
phase. Create them in `test/benchmark/scenarios/`:

```bash
# Phase 0: Baseline — 3 RPS for 5 min
cat <<EOF > test/benchmark/scenarios/s1_p0_baseline.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P0 Baseline"
request_type: text_completions
profile: poisson
rate: 3
max_seconds: 300
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF

# Phase 1a: Ramp step 1 — 10 RPS for 2 min
cat <<EOF > test/benchmark/scenarios/s1_p1a_ramp10.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P1a Ramp 10 RPS"
request_type: text_completions
profile: poisson
rate: 10
max_seconds: 120
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF

# Phase 1b: Ramp step 2 — 20 RPS for 2 min
cat <<EOF > test/benchmark/scenarios/s1_p1b_ramp20.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P1b Ramp 20 RPS"
request_type: text_completions
profile: poisson
rate: 20
max_seconds: 120
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF

# Phase 1c: Ramp step 3 — 35 RPS for 3 min (let autoscalers respond)
cat <<EOF > test/benchmark/scenarios/s1_p1c_ramp35.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P1c Ramp 35 RPS"
request_type: text_completions
profile: poisson
rate: 35
max_seconds: 180
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF

# Phase 2: Peak — 35 RPS for 10 min
cat <<EOF > test/benchmark/scenarios/s1_p2_peak.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P2 Peak 35 RPS"
request_type: text_completions
profile: poisson
rate: 35
max_seconds: 600
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF

# Phase 3: Drop — 3 RPS for 8 min
cat <<EOF > test/benchmark/scenarios/s1_p3_drop.yaml
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 P3 Drop 3 RPS"
request_type: text_completions
profile: poisson
rate: 3
max_seconds: 480
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
EOF
```

---

## Part 4: Run — WVA Mode

### 4.1 Reset replica counts

```bash
oc scale deployment/$H100_DEPLOY $L40_DEPLOY --replicas=1 -n $NS
sleep 30
oc get pods -n $NS
```

### 4.2 Run the phases

Open a second terminal and start watching replica counts:
```bash
watch -n 10 "oc get deployment -n $NS -o wide | grep -E 'llama|NAME'"
```

Run each phase in sequence. Between phases, note the replica counts.

```bash
echo "=== WVA Mode — Phase 0: Baseline (3 RPS, 5 min) ==="
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p0_baseline.yaml \
  MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "=== WVA Mode — Phase 1: Ramp (3 steps over ~7 min) ==="
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p1a_ramp10.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p1b_ramp20.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p1c_ramp35.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "--- Replica counts after ramp: ---"
oc get deployment $H100_DEPLOY $L40_DEPLOY -n $NS

echo "=== WVA Mode — Phase 2: Peak (35 RPS, 10 min) ==="
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p2_peak.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "--- Replica counts at peak: ---"
oc get deployment $H100_DEPLOY $L40_DEPLOY -n $NS

echo "=== WVA Mode — Phase 3: Drop (3 RPS, 8 min) ==="
make benchmark-run BENCHMARK_NAMESPACE=$NS \
  BENCHMARK_WORKLOAD=s1_p3_drop.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "--- Replica counts after drop: ---"
oc get deployment $H100_DEPLOY $L40_DEPLOY -n $NS
```

### 4.3 Record results

At minimum, record replica counts at end of each phase. Ideally also record:
```bash
# ITL / TTFT from the GuideLLM JSON output (in the timestamped results dir at repo root)
ls -t | head -1   # find the latest results dir
cat <results-dir>/results/guidellm-*/results.json | jq '.benchmarks[0] | {p99_itl, p99_ttft}'
```

---

## Part 5: Switch to KEDA-naive Mode

### 5.1 Disable WVA

```bash
# Scale down VA-based HPAs
oc delete hpa wva-hpa-h100 wva-hpa-l40 -n $NS

# Scale WVA controller to 0 (stops generating wva_desired_replicas metrics)
oc scale deployment/workload-variant-autoscaler-controller-manager \
  -n workload-variant-autoscaler-system --replicas=0
```

### 5.2 Create KEDA ScaledObjects — naive mode (queue depth only)

```bash
PROM_NS=workload-variant-autoscaler-monitoring
cat <<EOF | oc apply -f -
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-naive-h100
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $H100_DEPLOY
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: 3
  triggers:
  - type: prometheus
    name: vllm-queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: |
        sum(vllm:num_requests_waiting{exported_namespace="$NS",
          deployment=~"$H100_DEPLOY"})
      threshold: '5'
      activationThreshold: '0'
      metricType: AverageValue
      unsafeSsl: "true"
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-naive-l40
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $L40_DEPLOY
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: 2
  triggers:
  - type: prometheus
    name: vllm-queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: |
        sum(vllm:num_requests_waiting{exported_namespace="$NS",
          deployment=~"$L40_DEPLOY"})
      threshold: '5'
      activationThreshold: '0'
      metricType: AverageValue
      unsafeSsl: "true"
EOF
```

### 5.3 Reset and run same phases

```bash
oc scale deployment/$H100_DEPLOY $L40_DEPLOY --replicas=1 -n $NS
sleep 30

echo "=== KEDA-naive Mode — running all phases ==="
make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p0_baseline.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p1a_ramp10.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p1b_ramp20.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p1c_ramp35.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "--- Replica counts after ramp (KEDA-naive): ---"
oc get deployment $H100_DEPLOY $L40_DEPLOY -n $NS

make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p2_peak.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct

echo "--- Replica counts at peak (KEDA-naive): ---"
oc get deployment $H100_DEPLOY $L40_DEPLOY -n $NS

make benchmark-run BENCHMARK_NAMESPACE=$NS BENCHMARK_WORKLOAD=s1_p3_drop.yaml MODEL_ID=meta-llama/Llama-3.1-8B-Instruct
```

---

## Part 6: Switch to KEDA-tuned Mode

### 6.1 Delete naive ScaledObjects

```bash
oc delete scaledobject keda-naive-h100 keda-naive-l40 -n $NS
```

### 6.2 Create KEDA-tuned ScaledObjects (4 triggers, KV threshold 0.70)

```bash
PROM_NS=workload-variant-autoscaler-monitoring
cat <<EOF | oc apply -f -
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-tuned-h100
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $H100_DEPLOY
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: 3
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 180
        scaleUp:
          stabilizationWindowSeconds: 30
  triggers:
  - type: prometheus
    name: kv-cache
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: avg(vllm:gpu_cache_usage_perc{exported_namespace="$NS",deployment=~"$H100_DEPLOY"})
      threshold: '0.70'
      metricType: AverageValue
      unsafeSsl: "true"
  - type: prometheus
    name: queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: sum(vllm:num_requests_waiting{exported_namespace="$NS",deployment=~"$H100_DEPLOY"})
      threshold: '3'
      metricType: AverageValue
      unsafeSsl: "true"
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-tuned-l40
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $L40_DEPLOY
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: 2
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 180
        scaleUp:
          stabilizationWindowSeconds: 30
  triggers:
  - type: prometheus
    name: kv-cache
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: avg(vllm:gpu_cache_usage_perc{exported_namespace="$NS",deployment=~"$L40_DEPLOY"})
      threshold: '0.70'
      metricType: AverageValue
      unsafeSsl: "true"
  - type: prometheus
    name: queue-depth
    metadata:
      serverAddress: https://kube-prometheus-stack-prometheus.$PROM_NS.svc.cluster.local:9090
      query: sum(vllm:num_requests_waiting{exported_namespace="$NS",deployment=~"$L40_DEPLOY"})
      threshold: '3'
      metricType: AverageValue
      unsafeSsl: "true"
EOF
```

> **Note:** The full KEDA-tuned config (ITL p99 + token rate triggers) requires histogram
> metrics from Prometheus, which need longer warm-up to be meaningful. For the first manual
> run, two triggers (KV% + queue) is sufficient to observe the simultaneous-saturation trap.
> Add ITL and token-rate triggers in a follow-up run.

### 6.3 Reset and run same phases

```bash
oc scale deployment/$H100_DEPLOY $L40_DEPLOY --replicas=1 -n $NS
sleep 30

echo "=== KEDA-tuned Mode — running all phases ==="
# (same sequence as KEDA-naive above)
```

---

## Part 7: Restore WVA and Teardown

```bash
# Scale WVA back up
oc scale deployment/workload-variant-autoscaler-controller-manager \
  -n workload-variant-autoscaler-system --replicas=1

# Delete KEDA ScaledObjects
oc delete scaledobject keda-tuned-h100 keda-tuned-l40 -n $NS 2>/dev/null || true

# Teardown llm-d infra
make benchmark-teardown BENCHMARK_NAMESPACE=$NS
```

---

## Observation Checklist

Record these values at the **end of Phase 2 (peak, 35 RPS)** for each mode:

| Mode | L40 replicas | H100 replicas | Cost/interval |
|---|---|---|---|
| WVA | ? | ? | ? × 15 + ? × 65 |
| KEDA-naive | ? | ? | ? |
| KEDA-tuned | ? | ? | ? |

**Expected outcome (from design):**
- WVA: L40=2, H100=1 (cost 95) — stable
- KEDA: L40=2, H100=2 (cost 160) — trapped or oscillating

Also record:
- GuideLLM p99 ITL at peak (from results JSON)
- Any SLO violations during ramp

---

## Known Gaps (to address in full automation)

1. **Second deployment creation** — manual YAML editing; should be automated via test fixtures
2. **HPA metric label discovery** — need to verify exact `variant_name` label values WVA emits
3. **VA field name** — plan uses `variantCost`, sample file uses `variantCost`; verify matches CRD
4. **Phase scenario files** — created manually here; should be committed to `test/benchmark/scenarios/`
5. **Prometheus server address** — hardcoded; should be discovered dynamically
6. **Per-variant results** — GuideLLM reports aggregate metrics; per-variant split requires harness changes (§ 5.4 of implementation reference)
7. **KEDA-tuned ITL + token-rate triggers** — only 2 of 4 triggers applied here; full 4-trigger config needs histogram metrics warm-up
8. **Cost tracking** — replica counts recorded manually; full automation needs the cost-weighted GPU-hour aggregator (G3 in team discussion doc)
