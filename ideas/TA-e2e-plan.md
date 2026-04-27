# E2E Test Plan — TA3 (ThroughputAnalyzer)

## Status
**Phase:** Step 1 COMPLETE — Task 2 (TA3 test scenarios) is the next action  
**Branch:** TA3  
**Last updated:** 2026-04-27 (rev 6 — Step 1a + 1b results; EPP image bug; E2E_TESTS_ENABLED requirement; quay.io registry)

---

## Context

TA3 is the wiring PR (PR-5) that registers the ThroughputAnalyzer into the WVA engine. The analyzer logic (ITL model, OLS fitting, scaling signal) was built in PR-4 (TA3 branch). This plan covers e2e tests that validate the full integration: config → analyzer wiring → Prometheus metrics → scale signal → VA desired allocation.

Depends on the ENGINE multi-analyzer PR (`engine-multi-analyzer` branch) for the `analyzers` map and combine logic.

---

## Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Start with kind-emulator + simulator | No real GPUs needed; simulator produces Prometheus-compatible metrics |
| D2 | SCALER_BACKEND=prometheus-adapter | Default in install.sh; used on both OpenShift and kind. KEDA is kind-only — not the right choice for establishing a portable baseline |
| D3 | First step: run existing smoke tests on `main` | Establish that kind setup works before touching TA3 code |
| D4 | Two-task split: (1) how to run, (2) test scenarios | Keeps execution instructions separate from scenario design |
| D5 | Three scenarios: smoke health check + two full tests | Smoke = wiring only (fast); full = signal + TA-only mode (slow) |
| D6 | New file: `test/e2e/throughput_analyzer_test.go` | Keeps TA tests isolated; follows existing file-per-feature pattern |
| D7 | Labels: `Label("smoke","throughput")` and `Label("full","throughput")` | Auto-included in existing make targets; filterable with `FOCUS=ThroughputAnalyzer` |
| D8 | Defer shape-change, pending-replica, queue-demand, P/D scenarios | Unit tests cover shape/pending; scheduler queue not wired; P/D needs disaggregated cluster |
| D9 | Always undeploy WVA before redeploy | Clean state prevents stale helm/namespace state from hiding failures |
| D10 | DECODE_REPLICAS=1 for all TA test deployments | Start with 1 replica so scale-up from 1→2 is observable; matches Slack benchmark pattern |
| D11 | LLM_D_RELEASE=v0.6.0 | Pin llm-d version for reproducibility; matches current stable release used on OpenShift |
| D12 | NAMESPACE_SCOPED=false for kind | Hardcoded in `deploy-wva-emulated-on-kind`; kind uses cluster-scoped install |
| D13 | No separate `kind create cluster` or `kind load docker-image` | Both handled automatically by `install.sh`: CREATE_CLUSTER=true triggers cluster creation; load_image() in kind-emulator/install.sh loads WVA image into kind after build |
| D14 | IMG_TAG=main-local / ta3-dev for local builds | Expands to full `IMG` ref; `WVA_IMAGE_PULL_POLICY=IfNotPresent` set by deploy-e2e-infra triggers local-image path in install.sh |
| D15 | llm-d stack persists across WVA test iterations | llm-d (simulator + EPP) is expensive to redeploy; only tear down when switching model topology. Between runs: scale to 0 and back instead |

---

## Cluster Lifecycle and Layers

The kind cluster has **four independent layers** with different lifecycles. Deploy them in order; only redeploy the layers that changed.

### Layer 1 — Kind cluster
The bare kind cluster (Kubernetes control plane + GPU-emulated node config).

- **Create once.** Use `CREATE_CLUSTER=true` on first run. Do not delete between test runs.
- **Delete** only when you want a completely clean environment: `make undeploy-wva-emulated-on-kind DELETE_CLUSTER=true`.
- **Cluster name:** `kind-wva-gpu-cluster` (hardcoded in `deploy/kind-emulator/install.sh`).

### Layer 2 — Gateway control plane (idempotent)
Kubernetes Gateway / Istio control plane, Prometheus stack, llm-d CRDs.

- **On kind:** `deploy-e2e-infra` always passes `INSTALL_GATEWAY_CTRLPLANE=true`, but the underlying `helmfile apply` is idempotent — safe to re-run (no-op if already installed).
- **On OpenShift: NEVER set `INSTALL_GATEWAY_CTRLPLANE=true`.** The OpenShift CI hardcodes `"false"` at every deploy step. The existing control plane must never be touched.

### Layer 3 — llm-d model service (deploy once; persist across WVA test runs)
The llm-d simulator pod (`ms-sim-llm-d-modelservice-decode`) and EPP (`gaie-sim-epp`) in the `llm-d-sim` namespace.

- **Deploy once per cluster.** No need to redeploy between WVA test iterations.
- **Redeploy only** when switching between single-model and multi-model setups, or after a namespace wipe.
- **Between WVA runs:** scale backends to zero and back instead of redeploying (see [Between WVA test runs](#between-wva-test-runs) below).
- Deploy with: `DEPLOY_WVA=false make deploy-e2e-infra ...`

### Layer 4 — WVA controller (deploy/redeploy for each test iteration)
The WVA Helm release in `workload-variant-autoscaler-system` namespace.

- **Redeploy** each time you change WVA code or config.
- **Undeploy** before redeploy to ensure clean state (D9).
- Undeploy with: `DEPLOY_LLM_D=false make undeploy-wva-emulated-on-kind ...`
- Deploy with: `DEPLOY_LLM_D=false make deploy-e2e-infra ...`

---

## llm-d stack health check (curl)

Run this after deploying llm-d and after each between-run reset to confirm the inference gateway and simulator are serving requests. Requires only `curl` on the local machine.

```bash
# Port-forward the inference gateway (run in background; kill when done)
kubectl port-forward -n llm-d-sim svc/infra-sim-inference-gateway 8000:80 &
PF_PID=$!

# Wait for port-forward to be ready
sleep 3

# Check available models (should list the deployed model)
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Send a single inference request and check HTTP status
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth/Meta-Llama-3.1-8B","prompt":"Hello","max_tokens":5}')

echo "Inference HTTP status: $HTTP_CODE"
[ "$HTTP_CODE" = "200" ] && echo "PASS — llm-d stack is healthy" || echo "FAIL — expected 200, got $HTTP_CODE"

# Tear down port-forward
kill $PF_PID 2>/dev/null
```

**Pass condition:** `/v1/models` returns the model list; inference returns HTTP 200.

> If `MODEL_ID` was set to a different value during deploy, replace `unsloth/Meta-Llama-3.1-8B` with that value.  
> If the service name is uncertain: `kubectl get svc -n llm-d-sim | grep inference-gateway`

---

## Between WVA test runs

When llm-d is already deployed (Layer 3 in place), reset it to a clean state before each WVA test run by scaling all backends to zero and back. This evicts in-memory state (queued requests, KV cache) without a full reinstall.

```bash
LLMD_NS=llm-d-sim

# Scale to zero (clear in-memory state)
kubectl scale deployment ms-sim-llm-d-modelservice-decode gaie-sim-epp \
  -n $LLMD_NS --replicas=0

# Scale back up (match DECODE_REPLICAS from the original deploy — typically 1)
kubectl scale deployment ms-sim-llm-d-modelservice-decode gaie-sim-epp \
  -n $LLMD_NS --replicas=1

# Wait for ready
kubectl rollout status deployment/ms-sim-llm-d-modelservice-decode \
  -n $LLMD_NS --timeout=120s
kubectl rollout status deployment/gaie-sim-epp \
  -n $LLMD_NS --timeout=120s
```

Then run the **llm-d stack health check** above before proceeding to WVA tests.

> Verify deployment names if the namespace state is uncertain:
> `kubectl get deployments -n llm-d-sim`

---

## Grafana

Grafana is optional but recommended for visualising WVA metrics and capturing test results as screenshots.

### Deploying Grafana

Add `INSTALL_GRAFANA=true` to the `deploy-e2e-infra` command (Layer 2/3 deploy). Grafana deploys into the `workload-variant-autoscaler-monitoring` namespace.

Grafana runs with anonymous admin access (no login required). The benchmark dashboard (`deploy/grafana/benchmark-dashboard.json`) is auto-loaded as a ConfigMap.

### Accessing Grafana locally (kind)

```bash
kubectl port-forward -n workload-variant-autoscaler-monitoring svc/benchmark-grafana 3000:3000
```

Then open **http://localhost:3000** in a browser.

### Capturing test results (CI-style snapshots)

Set these env vars before running tests to save Grafana output as artifacts:

```bash
export BENCHMARK_GRAFANA_ENABLED=true
export BENCHMARK_GRAFANA_SNAPSHOT_FILE=/tmp/benchmark-grafana-snapshot.txt
export BENCHMARK_GRAFANA_SNAPSHOT_JSON=/tmp/benchmark-grafana-snapshot.json
export BENCHMARK_GRAFANA_PANEL_DIR=/tmp/benchmark-panels
```

After the test run, the snapshot files and panel screenshots are in the paths above. These match the artifact paths in `.github/workflows/ci-benchmark.yaml`.

---

## Task 1: How to Run the E2E Tests — Focus: `main` Branch Baseline

The goal is to get the existing smoke tests passing on a local kind cluster before writing any TA-specific test code.

Split into two sub-steps: (1a) run with the default registry image, (1b) run with a locally built image.

Do not proceed to TA3 test development until both sub-steps pass.

---

### Infrastructure notes (verified against actual runs — 2026-04-27)

- **Cluster creation**: `CREATE_CLUSTER=true` in `deploy-e2e-infra` triggers `kind-emulator/install.sh` to create the cluster — no separate `kind create cluster` needed.
- **Image loading into kind**: Handled automatically by `install.sh`'s `load_image()`. When `WVA_IMAGE_PULL_POLICY=IfNotPresent` (set by `deploy-e2e-infra` when IMG is supplied), it skips pulling and loads the local Docker image into kind. When IMG is not set, it pulls `latest` from the registry and loads it.
- **Prometheus-adapter**: Default scaler backend. After deploy, the e2e suite's `BeforeSuite` probes adapter readiness (`RESTART_PROMETHEUS_ADAPTER=auto`) and restarts adapter pods if the external metrics API is not yet registered.
- **Cluster name**: Defaults to `kind-wva-gpu-cluster` (set in `kind-emulator/install.sh`).
- **`E2E_TESTS_ENABLED=true` is required** for non-interactive deploys. Without it, `install_core.sh` calls `prompt_gateway_installation()` even when `INSTALL_GATEWAY_CTRLPLANE=true` is set; the interactive `read` gets EOF and the script exits with error 1. Set it as a shell env var prefix: `E2E_TESTS_ENABLED=true make deploy-e2e-infra ...`.
- **`CREATE_CLUSTER` and `INSTALL_GRAFANA`**: NOT forwarded explicitly by the `deploy-e2e-infra` Makefile recipe — must be set as shell environment variables (prefix before `make`), not Make variable arguments.
- **`LLM_D_RELEASE`**: Only controls the initial git clone of llm-d. If `./llm-d` already exists, the clone is skipped regardless of the value. Local llm-d checkout is v0.5.0 with local model configuration patches (model ID, simulator latency args) — do not overwrite.
- **kubectl context**: If kubectl is pointing at an OpenShift cluster, undeploy will fail with TLS timeout. This is benign — the deploy will auto-switch context to `kind-kind-wva-gpu-cluster` after cluster creation.
- **ndots DNS fix**: On IBM workstations with 9 corporate search domains, load-generator pods (Alpine/musl) fail DNS with ndots:5. Fix is in `test/e2e/fixtures/workload_builder.go` (commit `c03cdc7` on TA3). Run all steps from the TA3 branch.
- **EPP image version mismatch (known bug)**: `deploy/install.sh` defaults `LLM_D_INFERENCE_SCHEDULER_IMG=ghcr.io/llm-d/llm-d-inference-scheduler:v0.7.0` and patches the EPP deployment to that image after helmfile. But `v0.7.0` uses `gateway-api-inference-extension v1.4.0` which rejects `--kv-cache-usage-percentage-metric` as fatal. The local llm-d checkout (`v0.5.0`) sets that flag in `gaie-sim/values.yaml`. **Workaround:** After `deploy-e2e-infra`, patch the EPP image back to `v0.5.0`: `kubectl set image deployment/gaie-sim-epp -n llm-d-sim epp=ghcr.io/llm-d/llm-d-inference-scheduler:v0.5.0`. This is a separate infra bug to be fixed in a standalone PR.
- **Makefile IMG always set**: `IMG ?= $(IMG_REPO):$(IMG_TAG)` always expands, so the `else` branch in `deploy-e2e-infra` (registry pull, no local build) is unreachable. The deploy always builds/loads a local image. Workaround: pass `IMG=` (empty) as an explicit Make var to force the registry path. This is a separate Makefile bug to be fixed.
- **Local image registry**: Use `quay.io/dlorenz/llm-d-workload-variant-autoscaler:<tag>` for local builds on this machine (not ghcr.io/llm-d/).
- **Tests create their own model service fixtures**: In e2e mode (`E2E_TESTS_ENABLED=true`), tests do not use the pre-deployed llm-d modelservice. Each test creates and deletes its own VA/deployment/service/HPA. The "Between WVA test runs" reset is only relevant when using the persistent modelservice from a non-e2e deploy.

### Prerequisites for building an image
- Docker installed and running (Docker Desktop or Docker Engine on WSL2)
- Go toolchain available (already needed for `make test`)
- `make docker-build` invokes `$(CONTAINER_TOOL) build -t ${IMG} .` — a standard Docker build from the repo root `Dockerfile`

---

### Step 1a — Baseline with registry image (run from TA3 branch)

**RESULT: PASSED 2026-04-27 — 31/31 smoke tests in 536s**

Uses `ghcr.io/llm-d/llm-d-workload-variant-autoscaler:latest` pulled from the registry. No local build needed.

This step deploys all four layers at once (first-time setup). Run from the **TA3 branch** (not main) so the ndots DNS fix is present in test code.

```bash
git checkout TA3

# Undeploy any stale state (no-op if cluster doesn't exist; ignore kubectl context errors)
make undeploy-wva-emulated-on-kind \
  DELETE_NAMESPACES=false \
  DELETE_CLUSTER=false || true

# Create cluster + deploy Layers 2/3/4: gateway + llm-d + WVA
# CREATE_CLUSTER, INSTALL_GRAFANA, and E2E_TESTS_ENABLED are shell env vars (not Make vars)
CREATE_CLUSTER=true INSTALL_GRAFANA=true E2E_TESTS_ENABLED=true make deploy-e2e-infra \
  ENVIRONMENT=kind-emulator \
  DECODE_REPLICAS=1
```

**After deploy, patch the EPP image** (known version mismatch bug — see Infrastructure notes):

```bash
kubectl set image deployment/gaie-sim-epp -n llm-d-sim \
  epp=ghcr.io/llm-d/llm-d-inference-scheduler:v0.5.0
kubectl rollout status deployment/gaie-sim-epp -n llm-d-sim --timeout=60s
```

**Run smoke tests:**

```bash
make test-e2e-smoke ENVIRONMENT=kind-emulator
```

**Pass condition:** 31/31 `Label("smoke")` tests green. Prometheus-adapter external metrics API available.

**If the adapter is not ready**: Set `RESTART_PROMETHEUS_ADAPTER=true` on the `test-e2e-smoke` invocation to force a pod restart.

**(Optional) Access Grafana:**

```bash
kubectl port-forward -n workload-variant-autoscaler-monitoring svc/benchmark-grafana 3000:3000
# Open http://localhost:3000
```

---

### Step 1b — Baseline with locally built image

**RESULT: PASSED 2026-04-27 — 31/31 smoke tests in 544s**

Builds the controller binary + Docker image locally, then redeploys WVA only (Layer 4). The llm-d stack from Step 1a stays in place (tests create their own fixtures — no reset needed between steps).

```bash
git checkout TA3

# Build WVA image locally (use quay.io/dlorenz repo on this machine)
make docker-build IMG=quay.io/dlorenz/llm-d-workload-variant-autoscaler:ta3-dev

# Redeploy WVA only — DEPLOY_LLM_D=false keeps llm-d in place
# SKIP_BUILD=true skips docker-build since we already built above
# E2E_TESTS_ENABLED=true bypasses gateway interactive prompt
DEPLOY_LLM_D=false E2E_TESTS_ENABLED=true make deploy-e2e-infra \
  ENVIRONMENT=kind-emulator \
  IMG=quay.io/dlorenz/llm-d-workload-variant-autoscaler:ta3-dev \
  SKIP_BUILD=true \
  DECODE_REPLICAS=1

# Run smoke tests
make test-e2e-smoke ENVIRONMENT=kind-emulator
```

**Pass condition:** 31/31 smoke tests pass, using the locally built TA3 binary.

---

### Step 2 — TA3 tests (deferred — do not start until Step 1 passes)

After the test file `test/e2e/throughput_analyzer_test.go` is written:

```bash
git checkout TA3

# Build TA3 image
make docker-build IMG_TAG=ta3-dev

# Reset llm-d state
LLMD_NS=llm-d-sim
kubectl scale deployment ms-sim-llm-d-modelservice-decode gaie-sim-epp \
  -n $LLMD_NS --replicas=0
kubectl scale deployment ms-sim-llm-d-modelservice-decode gaie-sim-epp \
  -n $LLMD_NS --replicas=1
kubectl rollout status deployment/ms-sim-llm-d-modelservice-decode \
  -n $LLMD_NS --timeout=120s
kubectl rollout status deployment/gaie-sim-epp \
  -n $LLMD_NS --timeout=120s

# Undeploy WVA only, redeploy with TA3 image
DEPLOY_LLM_D=false make undeploy-wva-emulated-on-kind \
  DELETE_NAMESPACES=false \
  DELETE_CLUSTER=false

DEPLOY_LLM_D=false make deploy-e2e-infra \
  ENVIRONMENT=kind-emulator \
  IMG_TAG=ta3-dev \
  SKIP_BUILD=true \
  DECODE_REPLICAS=1 \
  LLM_D_RELEASE=v0.6.0 \
  CREATE_CLUSTER=false

# Run smoke (includes TA smoke via Label("smoke","throughput"))
make test-e2e-smoke ENVIRONMENT=kind-emulator

# Run full TA scenarios only
make test-e2e-full \
  ENVIRONMENT=kind-emulator \
  FOCUS="ThroughputAnalyzer"
```

---

### When to reinstall the full llm-d stack (Layer 3)

The llm-d stack only needs to be reinstalled when:
- Switching from single-model to multi-model setup (or vice versa)
- After a namespace or cluster wipe
- After a llm-d Helm chart version change (`LLM_D_RELEASE`)

To reinstall llm-d only (skip WVA):

```bash
DEPLOY_WVA=false make deploy-e2e-infra \
  ENVIRONMENT=kind-emulator \
  DECODE_REPLICAS=1 \
  LLM_D_RELEASE=v0.6.0 \
  CREATE_CLUSTER=false
```

---

### OpenShift rules (for reference)

These apply when running on OpenShift instead of kind. Do not apply on kind.

- **Never** set `INSTALL_GATEWAY_CTRLPLANE=true` on OpenShift. The control plane already exists and must not be modified.
- Always use `NAMESPACE_SCOPED=true` on OpenShift.
- The CI workflow (`ci-e2e-openshift.yaml`) hardcodes `INSTALL_GATEWAY_CTRLPLANE: "false"` at every deploy step.

---

### Key variables reference

| Variable | Full first-time deploy | WVA-only redeploy | llm-d-only redeploy | Notes |
|---|---|---|---|---|
| `ENVIRONMENT` | `kind-emulator` | `kind-emulator` | `kind-emulator` | |
| `DEPLOY_WVA` | *(default true)* | *(default true)* | `false` | `false` to skip WVA |
| `DEPLOY_LLM_D` | *(default true)* | `false` | *(default true)* | `false` to skip llm-d |
| `CREATE_CLUSTER` | `true` | `false` | `false` | `true` only on first run |
| `IMG_TAG` | *(unset = registry)* | `main-local` / `ta3-dev` | *(unset = registry)* | |
| `SKIP_BUILD` | *(unset)* | `true` | *(unset)* | `true` when image already built |
| `DECODE_REPLICAS` | `1` | `1` | `1` | start with 1; scale-up observable |
| `LLM_D_RELEASE` | `v0.6.0` | `v0.6.0` | `v0.6.0` | pin llm-d version |
| `INSTALL_GRAFANA` | `true` | *(not needed)* | *(not needed)* | deploy once with llm-d/monitoring |
| `E2E_TESTS_ENABLED` | *(not needed for smoke)* | *(not needed for smoke)* | — | `true` for full (EPP flow control) |
| `RESTART_PROMETHEUS_ADAPTER` | `auto` (default) | `auto` (default) | — | set `true` to force restart |
| `DELETE_CLUSTER` | `false` | `false` | `false` | `true` only for full wipe |
| `DELETE_NAMESPACES` | `false` | `false` | `false` | `true` only for full wipe |

---

## Task 2: E2E Scenario Design

### New file
`test/e2e/throughput_analyzer_test.go`

### ConfigMap configuration for TA
Written via the existing `upsertSaturationConfigEntry` helper (see [saturation_analyzer_path_test.go:651](test/e2e/saturation_analyzer_path_test.go#L651)):

```yaml
# Both analyzers enabled (Scenarios 1 and 2)
analyzers:
  - name: saturation
    enabled: true
    score: 1.0
  - name: throughput
    enabled: true
    score: 1.0

# TA-only mode (Scenario 3)
analyzers:
  - name: saturation
    enabled: false
  - name: throughput
    enabled: true
    score: 1.0
```

### Simulator configuration for TA tests
To reliably drive k* > `DefaultKSat` (0.85) with minimal traffic:
- `--max-num-seqs=2` — 2 concurrent requests fill kv-cache fast
- `--inter-token-latency=50ms` — keeps requests in-flight longer
- `--time-to-first-token=200ms` — realistic TTFT

---

### Scenario 1 — TA Wiring Health Check
**Label:** `Label("smoke", "throughput")`  
**File:** `throughput_analyzer_test.go`  
**Expected duration:** ~5 minutes

**Intent:** Verify PR-5 wiring is correct — controller starts, TA is active, VA reaches healthy steady state. Does not wait for a scale-up signal.

**Steps:**
1. `upsertSaturationConfigEntry` — both analyzers enabled
2. `fixtures.CreateModelService` — simulator with `max-num-seqs=2`, ITL=20ms
3. `fixtures.EnsureVariantAutoscalingWithDefaults`
4. Wait: `MetricsAvailable=true` and `DesiredOptimizedAlloc.NumReplicas` is non-nil
5. Scan controller logs: "throughput analyzer" entries present, no panic/fatal

**Pass condition:** VA reconciles to steady state with TA enabled.

---

### Scenario 2 — TA Tier-2 Calibration → Positive Scale-Up Signal
**Label:** `Label("full", "throughput")`  
**Expected duration:** ~15 minutes

**Intent:** Verify the full pipeline: traffic → k* > `DefaultKSat` (0.85) → tier-2 OLS → RC > 0 → DesiredAlloc increases.

**OLS window timing:**  
`DefaultMinSamples = 10`, one observation per reconcile cycle (~30s) → tier-1 needs ~5 min.  
Tier-2 fires after 1 observation at k* > 0 — test asserts on whichever fires first.

**Steps:**
1. Config: both analyzers enabled
2. Send sustained load job — continuous requests that keep 2 concurrent requests in-flight for 10+ minutes
3. `waitForPositiveDesiredAllocation` (timeout: `EventuallyExtendedSec` ~15 min)
4. **Assert:** `DesiredOptimizedAlloc.NumReplicas > baseline`
5. **Assert:** Controller logs contain "tier-2" or "tier-1 OLS fit"

---

### Scenario 3 — TA-Only Mode (Saturation Disabled)
**Label:** `Label("full", "throughput")`  
**Expected duration:** ~15 minutes

**Intent:** Verify `saturation.enabled=false` correctly routes: TA alone drives the scale decision; optimizer still receives `Cost`/`AcceleratorName` from saturation VariantCapacities (D2 from ENGINE design: saturation always runs).

**Steps:**
1. Config: `saturation.enabled=false`, `throughput.enabled=true, score=1.0`
2. Same sustained load pattern as Scenario 2
3. **Assert:** `DesiredOptimizedAlloc.NumReplicas > 0` (TA drives it)
4. **Assert:** Controller logs show saturation RC=0 in combine, throughput RC > 0
5. **Assert:** `DesiredOptimizedAlloc.Accelerator` is non-empty (VariantCapacities flowed from saturation, providing `AcceleratorName` even with saturation disabled)

---

### Deferred scenarios

| Scenario | Reason |
|---|---|
| Shape change clears window | Covered by unit tests (PR-4) |
| Pending replicas suppress scale-up | SchedulerQueue not wired yet |
| Queue demand contribution | SchedulerQueue not wired yet |
| Cold-start 0→1 (saturation-only) | Already covered by `scale_from_zero_test.go` |
| P/D role-aware aggregation | Requires P/D disaggregated cluster setup |

---

## Timing Summary

| Scenario | Label | Expected duration |
|---|---|---|
| 1: Wiring health check | smoke | ~5 min |
| 2: Tier-2 scale-up signal | full | ~15 min |
| 3: TA-only mode | full | ~15 min |
| Full suite (all 3) | | ~35 min (within existing 35m timeout) |

---

## Current Step

**→ Step 1 complete. Next: write `test/e2e/throughput_analyzer_test.go` (Task 2).**

Completed:
1. ✓ **Step 1a** — 31/31 smoke tests passed with kind cluster + all layers (2026-04-27)
2. ✓ **Step 1b** — 31/31 smoke tests passed with local TA3 image + WVA-only redeploy (2026-04-27)

Next: write `test/e2e/throughput_analyzer_test.go` with the three scenarios in Task 2. Deploy with TA3 image before running TA-specific tests (same commands as Step 1b — cluster is already up).
