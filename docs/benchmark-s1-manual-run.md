# Scenario 1 Manual Run — WVA vs KEDA Cost-Optimal Ramp

Manual instructions to run the benchmark on a real OpenShift cluster. The goal is to
observe the simultaneous-saturation trap across three autoscaler modes (WVA /
KEDA-naive / KEDA-tuned) and validate the expected cost gap before committing to full
automation.

Design reference: `plans/planning/benchmark-wva-vs-keda.md` (approach) and
`plans/planning/benchmark-wva-vs-keda-plan.md` § 2–4 (full details).

---

## Prerequisites

### Tools

```bash
oc version --client    # OpenShift CLI — includes kubectl
helm version --short
yq --version
jq --version
go version
uv --version           # preferred Python manager
                       # install: curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Access

- OpenShift cluster with GPU nodes (see § 1 for GPU label discovery)
- HuggingFace token with access to the model you plan to run
- KEDA operator installed on the cluster (coordinate with cluster admin if absent)

### This worktree

All commands below run from the **`benchmark/` worktree**:

```bash
cd /path/to/llm-d-workload-variant-autoscaler/benchmark
```

Verify the branch is current with upstream:

```bash
git branch --show-current          # benchmark
git fetch upstream
git log --oneline upstream/main ^HEAD | head -3   # empty = up to date
```

---

## 0. Connect to the cluster

### New login

```bash
# Get your login command from the OpenShift web console:
# username → Copy login command → Display Token
oc login --token=sha256~XXXX --server=https://api.your-cluster.example.com:6443
```

### Switch between existing contexts

```bash
oc config get-contexts              # list saved contexts
oc config use-context <name>        # switch
oc whoami && oc whoami --show-server   # confirm
```

---

## 1. Settings

Edit `benchmark-settings.env` and fill in the mandatory fields.

**Mandatory — you must set these:**

| Variable | What to set |
|---|---|
| `HF_TOKEN` | HuggingFace token (set in shell, never in the file) |
| `BENCHMARK_NS` | Namespace to create (default: `llmd-bench`) |
| `HF_MODEL_ID` | HuggingFace model path used to pull weights |
| `SERVED_MODEL_ID` | Name vLLM serves on the OpenAI API; must match WVA `modelID` and GuideLLM `--model` |
| `VARIANT_A_GPU_LABEL` | `nvidia.com/gpu.product` label on cheap-tier nodes |
| `VARIANT_B_GPU_LABEL` | `nvidia.com/gpu.product` label on expensive-tier nodes |

> **Two model IDs, not one.** `HF_MODEL_ID` is the HuggingFace repository for downloading
> weights (passed as `--model` to vLLM). `SERVED_MODEL_ID` is the name vLLM exposes on its
> OpenAI API (`--served-model-name`). If not set explicitly in the model server, vLLM
> defaults `served-model-name` to the HF path, so they can be identical — but they are
> conceptually different and need separate variables. WVA's `modelID` field in each VA
> resource must match `SERVED_MODEL_ID`.

**Variants are abstract.** VARIANT_A is the cheap tier, VARIANT_B is the expensive tier.
For heterogeneous hardware (e.g., L40 + H100) set different GPU labels. For a
homogeneous cluster (all A100) set the same GPU label — the cost weights still create
the cost-optimization story.

Discover GPU labels on your cluster:

```bash
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.nvidia\.com/gpu\.product}{"\n"}{end}' \
  | grep -v $'\t$'
```

Source once at the start of every terminal session:

```bash
export HF_TOKEN="hf_..."
source benchmark-settings.env
```

---

## 2. Install benchmark CLI

Run once per workspace. Uses `uv` for the Python environment:

```bash
make benchmark-install BENCHMARK_UV=true BENCHMARK_REPO_REF=$BENCHMARK_REPO_REF
```

This clones `llm-d-benchmark` at `./llm-d-benchmark/` (gitignored) and installs the
`llmdbenchmark` CLI inside a `uv`-managed virtualenv.

Verify:

```bash
./llm-d-benchmark/.venv/bin/llmdbenchmark --version
```

---

## 3. Stand up llm-d infrastructure (Variant B)

The standup deploys the full llm-d stack — EPP, gateway, Prometheus monitoring, WVA
controller — and **one** model server (Variant B, the expensive/default tier).

> **Helm vs Kustomize.** As of llm-d v0.7.0 the model server is deployed via a
> Kustomize overlay (`guides/<name>/modelserver/`). The EPP and gateway control plane
> still use helmfile. WVA itself is deployed via Helm chart. The standup handles all of
> this automatically.

```bash
oc new-project $BENCHMARK_NS 2>/dev/null || oc project $BENCHMARK_NS
oc label namespace $BENCHMARK_NS openshift.io/user-monitoring=true --overwrite

make benchmark-standup \
  BENCHMARK_NAMESPACE=$BENCHMARK_NS \
  MODEL_ID=$HF_MODEL_ID \
  LLM_D_RELEASE=$LLM_D_RELEASE
```

Wait for `✅ All smoketest steps complete.` (5–15 min).

### 3.1 Verify standup output

```bash
# Inspect what was deployed
oc get deployment -n $BENCHMARK_NS
oc get variantautoscaling -n $BENCHMARK_NS
oc get hpa -n $BENCHMARK_NS
```

Find the Variant B deployment name (it derives from the guide name set in standup):

```bash
B_DEPLOY=$(oc get deployment -n $BENCHMARK_NS -o jsonpath='{.items[0].metadata.name}')
echo "Variant B deployment: $B_DEPLOY"
# Update VARIANT_B_DEPLOY in benchmark-settings.env if it differs from the default, then:
source benchmark-settings.env
```

---

## 4. Scenario 1 manual additions

The standard standup creates one deployment, one VA, and one HPA. Scenario 1 needs:

| Component | Standard standup | Scenario 1 |
|---|---|---|
| Model deployments | 1 (Variant B) | **+1 Variant A** (same model, different GPU nodeSelector) |
| VariantAutoscaling | 1 (no explicit cost) | **2** (cost A < cost B, `maxReplicas` capped) |
| HPA | 1 | **2** (one per VA, targeting `wva_desired_replicas`) |
| Saturation ConfigMap | v1 defaults | **saturation_v2** (`analyzerName: saturation`) |
| Traffic | Single-phase fixed RPS | **4-phase staircase** via chained runs |

### 4.1 Create Variant A deployment

The standup deploys the model server via a Kustomize overlay. For this manual run, we
create Variant A as a standalone Deployment that mirrors Variant B but targets
different GPU nodes.

Export Variant B as a template and create Variant A:

```bash
oc get deployment $VARIANT_B_DEPLOY -n $BENCHMARK_NS -o yaml \
  | yq '
      .metadata.name = env(VARIANT_A_DEPLOY) |
      .metadata.namespace = env(BENCHMARK_NS) |
      del(.metadata.resourceVersion, .metadata.uid,
          .metadata.generation, .metadata.creationTimestamp,
          .status) |
      .spec.replicas = 1 |
      (.spec.template.spec.nodeSelector["nvidia.com/gpu.product"]) = env(VARIANT_A_GPU_LABEL)
    ' \
  | oc apply -f -
```

Wait for Variant A to load the model weights (~5–10 min):

```bash
oc rollout status deployment/$VARIANT_A_DEPLOY -n $BENCHMARK_NS
```

### 4.2 Patch saturation ConfigMap for saturation_v2

The standup creates the ConfigMap with v1 defaults. Override it:

```bash
oc patch configmap wva-saturation-scaling-config \
  -n $WVA_NS \
  --type merge \
  -p '{"data":{"default":"analyzerName: saturation\nkvCacheThreshold: 0.80\nqueueLengthThreshold: 5\nscaleUpThreshold: 0.85\nscaleDownBoundary: 0.70\n"}}'

oc rollout restart deployment/workload-variant-autoscaler-controller-manager -n $WVA_NS
oc rollout status  deployment/workload-variant-autoscaler-controller-manager -n $WVA_NS
```

### 4.3 Create VariantAutoscaling resources

The WVA `modelID` must equal `$SERVED_MODEL_ID` (the name vLLM advertises on the API).

```bash
# Remove any VA the standup created; we replace with cost-bearing ones
oc delete variantautoscaling --all -n $BENCHMARK_NS 2>/dev/null || true

cat <<EOF | oc apply -f -
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: ${VARIANT_A_NAME}
  namespace: ${BENCHMARK_NS}
spec:
  modelID: "${SERVED_MODEL_ID}"
  minReplicas: 1
  maxReplicas: ${VARIANT_A_MAX_REPLICAS}
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${VARIANT_A_DEPLOY}
  variantCost: "${VARIANT_A_COST}.0"
---
apiVersion: llmd.ai/v1alpha1
kind: VariantAutoscaling
metadata:
  name: ${VARIANT_B_NAME}
  namespace: ${BENCHMARK_NS}
spec:
  modelID: "${SERVED_MODEL_ID}"
  minReplicas: 1
  maxReplicas: ${VARIANT_B_MAX_REPLICAS}
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${VARIANT_B_DEPLOY}
  variantCost: "${VARIANT_B_COST}.0"
EOF
```

### 4.4 Create HPA resources (WVA pass-through)

WVA emits `wva_desired_replicas{variant_name=<VA-name>, namespace=<ns>, accelerator_type=<type>}`.
The HPA reads this metric via the Prometheus adapter and actuates the deployment.

Remove any HPA the standup created, then apply new ones:

```bash
oc delete hpa --all -n $BENCHMARK_NS 2>/dev/null || true

# Get the Prometheus cluster-local service URL
PROM_URL="https://kube-prometheus-stack-prometheus.${PROM_NS}.svc.cluster.local:9090"

cat <<EOF | oc apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: wva-hpa-${VARIANT_A_NAME}
  namespace: ${BENCHMARK_NS}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${VARIANT_A_DEPLOY}
  minReplicas: 1
  maxReplicas: ${VARIANT_A_MAX_REPLICAS}
  metrics:
  - type: External
    external:
      metric:
        name: wva_desired_replicas
        selector:
          matchLabels:
            variant_name: "${VARIANT_A_NAME}"
            namespace: "${BENCHMARK_NS}"
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
  name: wva-hpa-${VARIANT_B_NAME}
  namespace: ${BENCHMARK_NS}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${VARIANT_B_DEPLOY}
  minReplicas: 1
  maxReplicas: ${VARIANT_B_MAX_REPLICAS}
  metrics:
  - type: External
    external:
      metric:
        name: wva_desired_replicas
        selector:
          matchLabels:
            variant_name: "${VARIANT_B_NAME}"
            namespace: "${BENCHMARK_NS}"
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

> **Note on Prometheus adapter.** The HPA uses the Kubernetes external metrics API, which
> requires a Prometheus adapter to be installed and configured to expose `wva_desired_replicas`.
> Verify it is running: `oc get pods -n $PROM_NS | grep adapter`. If absent, the standup
> may have installed it — check with `oc get apiservice v1beta1.external.metrics.k8s.io`.

### 4.5 Verify WVA is managing both variants

```bash
oc get variantautoscaling -n $BENCHMARK_NS
oc logs -n $WVA_NS \
  deployment/workload-variant-autoscaler-controller-manager --tail=20 \
  | grep -i "variant\|${VARIANT_A_NAME}\|${VARIANT_B_NAME}"
```

### 4.6 Create phase scenario files

> **Why sequential runs, not a single multi-phase file?**
> Each `make benchmark-run` is one GuideLLM job. There is a ~30 s gap between phases
> (no traffic) while the next job starts. For observing **steady-state** autoscaler
> behaviour at each load level, this is acceptable — the gap even helps because the
> autoscaler settles before you move on.
>
> A continuous ramp without gaps would require the `inference-perf` harness
> (`make benchmark-run-bursty`), which supports multi-stage rate profiles via `bursty.yaml`.
> That is the right tool for a smooth ramp experiment. For this first manual run,
> sequential GuideLLM jobs are simpler and sufficient.

```bash
for spec in \
  "s1_p0_baseline.yaml:3:300" \
  "s1_p1a_ramp10.yaml:10:120" \
  "s1_p1b_ramp20.yaml:20:120" \
  "s1_p1c_ramp35.yaml:35:180" \
  "s1_p2_peak.yaml:35:600" \
  "s1_p3_drop.yaml:3:480"
do
  fname=$(echo $spec | cut -d: -f1)
  rate=$(echo $spec  | cut -d: -f2)
  secs=$(echo $spec  | cut -d: -f3)
  cat > test/benchmark/scenarios/$fname <<YAML
target: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
model: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
name: "S1 ${fname%.yaml}"
request_type: text_completions
profile: poisson
rate: ${rate}
max_seconds: ${secs}
data:
  prompt_tokens: 1000
  output_tokens: 4000
  seed: 42
YAML
done
echo "Created: $(ls test/benchmark/scenarios/s1_*.yaml)"
```

---

## 5. Run — WVA Mode

### Watch replica counts (second terminal)

```bash
source benchmark-settings.env
watch -n 10 "oc get deployment $VARIANT_A_DEPLOY $VARIANT_B_DEPLOY \
  -n $BENCHMARK_NS --no-headers \
  -o custom-columns='NAME:.metadata.name,READY:.status.readyReplicas,DESIRED:.spec.replicas'"
```

### Run

```bash
oc scale deployment/$VARIANT_A_DEPLOY $VARIANT_B_DEPLOY --replicas=1 -n $BENCHMARK_NS
sleep 30

for phase in s1_p0_baseline s1_p1a_ramp10 s1_p1b_ramp20 s1_p1c_ramp35; do
  echo "=== WVA — ${phase} ==="
  make benchmark-run BENCHMARK_NAMESPACE=$BENCHMARK_NS \
    BENCHMARK_WORKLOAD=${phase}.yaml \
    MODEL_ID=$SERVED_MODEL_ID
done

echo "--- Replicas after ramp ---"
oc get deployment $VARIANT_A_DEPLOY $VARIANT_B_DEPLOY -n $BENCHMARK_NS --no-headers

echo "=== WVA — Peak (35 RPS, 10 min) ==="
make benchmark-run BENCHMARK_NAMESPACE=$BENCHMARK_NS \
  BENCHMARK_WORKLOAD=s1_p2_peak.yaml MODEL_ID=$SERVED_MODEL_ID

echo "--- Replicas at peak ---"
oc get deployment $VARIANT_A_DEPLOY $VARIANT_B_DEPLOY -n $BENCHMARK_NS --no-headers

echo "=== WVA — Drop ==="
make benchmark-run BENCHMARK_NAMESPACE=$BENCHMARK_NS \
  BENCHMARK_WORKLOAD=s1_p3_drop.yaml MODEL_ID=$SERVED_MODEL_ID
```

Record results from the timestamped directory:

```bash
RESULTS_DIR=$(ls -td */ | head -1)
cat ${RESULTS_DIR}results/guidellm-*/results.json \
  | jq '{completed_request_rate, p99_itl: .benchmarks[0].p99_itl}'
```

---

## 6. Switch to KEDA-naive Mode

```bash
# Disable WVA
oc delete hpa --all -n $BENCHMARK_NS 2>/dev/null || true
oc scale deployment/workload-variant-autoscaler-controller-manager \
  -n $WVA_NS --replicas=0

# Apply naive ScaledObjects (queue depth only)
PROM_URL="https://kube-prometheus-stack-prometheus.${PROM_NS}.svc.cluster.local:9090"

for variant_name in $VARIANT_A_NAME $VARIANT_B_DEPLOY; do
  [[ "$variant_name" == "$VARIANT_A_NAME" ]] && max=$VARIANT_A_MAX_REPLICAS deploy=$VARIANT_A_DEPLOY \
    || max=$VARIANT_B_MAX_REPLICAS deploy=$VARIANT_B_DEPLOY

  cat <<EOF | oc apply -f -
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-naive-${variant_name}
  namespace: ${BENCHMARK_NS}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${deploy}
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: ${max}
  triggers:
  - type: prometheus
    name: vllm-queue
    metadata:
      serverAddress: ${PROM_URL}
      query: |
        sum(vllm:num_requests_waiting{exported_namespace="${BENCHMARK_NS}",
          deployment=~"${deploy}"})
      threshold: "5"
      metricType: AverageValue
      unsafeSsl: "true"
EOF
done

# Reset and run same phases
oc scale deployment/$VARIANT_A_DEPLOY $VARIANT_B_DEPLOY --replicas=1 -n $BENCHMARK_NS
sleep 30
for phase in s1_p0_baseline s1_p1a_ramp10 s1_p1b_ramp20 s1_p1c_ramp35 s1_p2_peak s1_p3_drop; do
  echo "=== KEDA-naive — ${phase} ==="
  make benchmark-run BENCHMARK_NAMESPACE=$BENCHMARK_NS \
    BENCHMARK_WORKLOAD=${phase}.yaml MODEL_ID=$SERVED_MODEL_ID
done
```

---

## 7. Switch to KEDA-tuned Mode

```bash
oc delete scaledobject -l "app.kubernetes.io/name=keda-naive" -n $BENCHMARK_NS 2>/dev/null || true
oc delete scaledobject keda-naive-$VARIANT_A_NAME keda-naive-$VARIANT_B_NAME \
  -n $BENCHMARK_NS 2>/dev/null || true

PROM_URL="https://kube-prometheus-stack-prometheus.${PROM_NS}.svc.cluster.local:9090"

for variant_name in $VARIANT_A_NAME $VARIANT_B_NAME; do
  [[ "$variant_name" == "$VARIANT_A_NAME" ]] \
    && max=$VARIANT_A_MAX_REPLICAS && deploy=$VARIANT_A_DEPLOY \
    || max=$VARIANT_B_MAX_REPLICAS && deploy=$VARIANT_B_DEPLOY

  cat <<EOF | oc apply -f -
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: keda-tuned-${variant_name}
  namespace: ${BENCHMARK_NS}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${deploy}
  pollingInterval: 15
  cooldownPeriod:  300
  minReplicaCount: 1
  maxReplicaCount: ${max}
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
      serverAddress: ${PROM_URL}
      query: avg(vllm:gpu_cache_usage_perc{exported_namespace="${BENCHMARK_NS}",deployment=~"${deploy}"})
      threshold: "0.70"
      metricType: AverageValue
      unsafeSsl: "true"
  - type: prometheus
    name: queue
    metadata:
      serverAddress: ${PROM_URL}
      query: sum(vllm:num_requests_waiting{exported_namespace="${BENCHMARK_NS}",deployment=~"${deploy}"})
      threshold: "3"
      metricType: AverageValue
      unsafeSsl: "true"
EOF
done

# Reset and run
oc scale deployment/$VARIANT_A_DEPLOY $VARIANT_B_DEPLOY --replicas=1 -n $BENCHMARK_NS
sleep 30
for phase in s1_p0_baseline s1_p1a_ramp10 s1_p1b_ramp20 s1_p1c_ramp35 s1_p2_peak s1_p3_drop; do
  echo "=== KEDA-tuned — ${phase} ==="
  make benchmark-run BENCHMARK_NAMESPACE=$BENCHMARK_NS \
    BENCHMARK_WORKLOAD=${phase}.yaml MODEL_ID=$SERVED_MODEL_ID
done
```

> **KEDA-tuned completeness.** Two triggers (KV% + queue) are enough to observe the
> simultaneous-saturation trap. The full four-trigger config (adds ITL p99 + token arrival
> rate) is in `plans/planning/benchmark-wva-vs-keda-plan.md` § 4.2 and can be added once
> the metric names are confirmed on your cluster.

---

## 8. Restore and teardown

```bash
oc scale deployment/workload-variant-autoscaler-controller-manager \
  -n $WVA_NS --replicas=1
oc delete scaledobject --all -n $BENCHMARK_NS 2>/dev/null || true
make benchmark-teardown BENCHMARK_NAMESPACE=$BENCHMARK_NS
```

---

## Observation record

Fill in at end of **Phase 2 peak (35 RPS)** for each mode:

| Mode | Variant A replicas | Variant B replicas | Cost/interval | Notes |
|---|---|---|---|---|
| WVA | | | | |
| KEDA-naive | | | | |
| KEDA-tuned | | | | |

Expected: WVA holds A=max, B=1 (cost A×`$VARIANT_A_COST` + 1×`$VARIANT_B_COST`).
KEDA scales both to max (trapped by simultaneous-saturation).

---

## Open items

### Scenario-specific (things we added manually that need automation)

| # | Item | What to automate |
|---|---|---|
| S1 | Second variant deployment | Kustomize overlay mirroring the standup's modelserver overlay, parameterised by GPU label |
| S2 | VA resources with cost | Helm chart values or Kustomize patch that sets `variantCost` per variant |
| S3 | Saturation ConfigMap patch | ConfigMap override committed to the benchmark worktree, applied alongside standup |
| S4 | Phase scenario files | Commit to `test/benchmark/scenarios/`; parameterize rate/duration |
| S5 | Mode switching (WVA↔KEDA) | Script that toggles VA+HPA vs ScaledObjects |

### General harness gaps (pre-existing, not scenario-specific)

| # | Item | Status |
|---|---|---|
| G1 | Prometheus service address discovery | Hardcoded; no helper in existing scripts |
| G2 | `wva_desired_replicas` metric availability via Prometheus adapter | Requires adapter install + SeriesQuery config; no existing automation |
| G3 | Per-variant result splitting | GuideLLM reports aggregate only; replica counts recorded manually |
| G4 | Prometheus metric label verification (`vllm:gpu_cache_usage_perc` label names) | Must be checked per cluster/vLLM version |
| G5 | KEDA-tuned full 4-trigger config (ITL p99 + token rate) | Histogram metric names need verification; deferred to follow-up |
| G6 | Cost-weighted GPU-hour aggregator | Not present; manual calculation from replica counts |
