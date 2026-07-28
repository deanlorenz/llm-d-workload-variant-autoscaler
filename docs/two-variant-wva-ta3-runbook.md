# Two-Variant WVA Benchmark on TA3 — Recreation Runbook

End-to-end runbook for reproducing the biranofer **two-variant-wva** cost-aware
benchmark
([llm-d-benchmark `feat/multi-variant-benchmark`](https://github.com/biranofer/llm-d-benchmark/blob/feat/multi-variant-benchmark/docs/multi-variant-benchmark.md))
against a **TA3** WVA build, on a real-GPU OpenShift cluster.

> Status: WIP — captured 2026-06-15 during a live bring-up. Records the exact
> sequence **plus every correction/patch** needed to get it working, because the
> stock scenario does **not** run as-is against a current-`main`/TA3 controller.
>
> **Where it stands:** stack is up, V2 cost-aware path verified on real KV, TA
> confirmed running alongside sat_v2, two variants deployed. **Not yet done:** a
> clean scale-up event under load (guidellm delivered 0 load — §10b). **Pick up in
> §14.** GPUs freed at session end (variants scaled to 0).

---

## 0. Why this isn't the stock recipe

The biranofer doc targets the **released v0.7.0 WVA chart + image**. We are testing
the **TA3** branch (current `main` + 27 TA3 commits + PR #1266), which has moved
past what the bundled scenario assumes. Three independent breakages had to be
corrected (details in §5). If you just follow the upstream doc with a TA3 image,
the controller **CrashLoopBackOffs** and, once that's fixed, the VA never gets
metrics (`METRICSREADY=False` forever).

This benchmark **cannot run on kind** — it deploys real `vllm-openai` on real GPUs
and depends on `vllm:cache_config_info` reporting real KV memory. Use a GPU
OpenShift cluster.

---

## 1. Environment (what we used)

| Thing | Value |
|---|---|
| Cluster | OpenShift `dhl-wva` context → `api.pokprod001.ete14.res.ibm.com` |
| GPUs | 13× nodes `NVIDIA-H100-80GB-HBM3`, ~100 GPUs allocatable |
| Namespace | `dhl-wva` (cluster-admin; can read `thanos-querier-tls`) |
| Model | `unsloth/Meta-Llama-3.1-8B` (ungated; ~15 GB weights) |
| vLLM image | `docker.io/vllm/vllm-openai:v0.20.2` (CLI default override; ≥v0.14.0 needed for `cache_config_info`) |
| WVA image | `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3` (built from `benchmark` branch = main + TA3 + #1266; **public**) |
| WVA chart | `oci://ghcr.io/llm-d/workload-variant-autoscaler` **0.7.0** (NOT the scenario default 0.6.0 — see §5.1) |
| Monitoring | OpenShift user-workload-monitoring + Thanos (`thanos-querier.openshift-monitoring`) |
| Benchmark CLI | `llmdbenchmark` 0.6.0 from biranofer `feat/multi-variant-benchmark`, in a `uv` venv |

The `benchmark` git branch = `main` + 27 TA3 commits + 6 PR #1266 commits + 2
benchmark-scaffolding commits. A backup tag of the pre-update tip exists:
`backup/benchmark-pre-update-20260615`.

---

## 2. Host tools (one-time)

The benchmark CLI installer (`llm-d-benchmark/install.sh`) pins tool versions and
will `sudo`-install any that are below pin — which fails in a no-sudo environment.
Pre-install these to satisfy the pins (user-space `crane`; the rest globally), so
the installer's tool phase is a no-op:

| Tool | Pinned | Note |
|---|---|---|
| helmfile | 1.5.1 | hard-fail in installer if below |
| yq | v4.53.2 | |
| kustomize | v5.8.1 | |
| jq | 1.8.1 | |
| skopeo | 1.20.1 | |
| crane | 0.21.6 | installed to `~/go/bin` (user-space) |

`curl` below-pin is treated non-critical (skipped). `pg_config` missing is fine on
amd64 (planner's `psycopg2-binary` wheel installs).

**Local patch to the cloned installer:** `llm-d-benchmark/install.sh` runs
`sudo apt-get update` unconditionally on Ubuntu (line ~209, gated by a var it
hard-sets to 0). Comment out that single `sudo apt-get update` line — all apt
tools are already present so the refresh is a no-op. (The clone is gitignored.)

---

## 3. Install the benchmark CLI

From the `benchmark/` worktree, pointed at biranofer's fork/branch (the upstream
default `v0.6.3` does NOT contain the two-variant scenario):

```bash
make benchmark-install \
  BENCHMARK_REPO_URL=https://github.com/biranofer/llm-d-benchmark.git \
  BENCHMARK_REPO_REF=feat/multi-variant-benchmark \
  BENCHMARK_UV=true
# if the sudo-apt line aborts it, apply the §2 patch then:
cd llm-d-benchmark && ./install.sh --uv
```

> The `make benchmark-standup/run/teardown` wrappers are hardcoded to the upstream
> `inference-scheduling-wva` scenario (they `sed`-patch a file absent in biranofer's
> branch and default `BENCHMARK_SPEC=guides/workload-autoscaling`). They do **not**
> drive `guides/two-variant-wva`. Use the venv CLI directly (below). A deferred TODO
> exists to generalize the Makefile target.

CLI binary: `llm-d-benchmark/.venv/bin/llmdbenchmark`.

---

## 4. Build & publish the TA3 image

```bash
make docker-build IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3
make docker-push  IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3
```

The cluster pulls anonymously, so the quay repo must be **public**
(`quay.io` → repo → Settings → Make Public; vulnerability flags are cosmetic).

---

## 5. Scenario patches (gitignored clone — re-apply after any re-clone)

All in `llm-d-benchmark/config/scenarios/guides/two-variant-wva.yaml`.

### 5.1 WVA image → TA3
```yaml
  wva:
    image:
      repository: quay.io/deanlorenz/llm-d-workload-variant-autoscaler
      tag: ta3
```
(The template `19_wva-values.yaml.j2` maps `wva.image.*` straight into chart
values with `imagePullPolicy: Always`.)

### 5.2 WVA chart 0.6.0 → 0.7.0  *(the CrashLoopBackOff fix)*
```yaml
  chartVersions:
    wva: 0.7.0
```
**Why:** the 0.6.0 chart's RBAC `Role` lacks `get/list/watch` on
`autoscaling/horizontalpodautoscalers` **and** `keda.sh/scaledobjects`. The
current-`main` controller watches both (KEDA CRDs are present cluster-wide on
pokprod, so it auto-starts a ScaledObject watch). Under 0.6.0 the manager caches
never sync → `failed to wait for scaledobject caches to sync` → crash loop. The
0.7.0 chart grants both. (`0.7.0` is published in the OCI registry.)

> If you already standup'd on 0.6.0, upgrade in place:
> `helm upgrade workload-variant-autoscaler oci://ghcr.io/llm-d/workload-variant-autoscaler --version 0.7.0 --reuse-values -n dhl-wva`
> then `oc rollout restart deploy/workload-variant-autoscaler-controller-manager -n dhl-wva` to re-pull `:ta3`.

---

## 6. Standup (direct CLI)

```bash
export HF_TOKEN=hf_...          # set in your shell (or ~/.profile, then source inline)
cd <benchmark-worktree>
source ~/.profile   # if HF_TOKEN lives there
llm-d-benchmark/.venv/bin/llmdbenchmark \
  --spec guides/two-variant-wva --workspace "$PWD" --base-dir "$PWD/llm-d-benchmark" \
  standup -p dhl-wva
```

Dry-run first with `--dry-run` (note: the dry-run "Could not extract Prometheus CA
cert" warning is an artifact — a real admin run extracts it fine; and
prometheus-adapter is reused if already installed cluster-wide).

Standup installs 4 helm releases (`infra-llmdbench`, `…-gaie`, `…-ms`,
`workload-variant-autoscaler`) + the decode vLLM pod, runs a smoketest, and ends
with `✅ All smoketest steps complete`. The Capacity Planner log confirms real KV
(~48 GB allocatable, ~48 concurrent reqs on H100) — the signal the cost-aware demo
needs.

**Verify the controller is healthy** (not crash-looping) and on the TA3 image:
```bash
oc get pods -n dhl-wva -l control-plane=controller-manager
oc get pods -n dhl-wva -l control-plane=controller-manager \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'   # must be the :ta3 digest
```

---

## 7. Enable V2 saturation (cost-aware path)

```bash
oc apply -n dhl-wva -f llm-d-benchmark/config/scenarios/guides/two-variant-wva-v2-config.yaml
oc rollout restart deploy/workload-variant-autoscaler-controller-manager -n dhl-wva
oc logs -n dhl-wva deploy/workload-variant-autoscaler-controller-manager --tail=50 | grep "Processing model (V2)"
```

---

## 8. Fix metric→VA mapping  *(the `METRICSREADY=False` fix)*

After V2 is on you will still see `No saturation metrics available` and
`Skipping pod that doesn't match any scale target`. Two distinct problems:

### 8.1 Scenario hash bug (variant label ≠ VA name)
The scenario hardcodes
`modelArtifacts.extraLabels."llm-d.ai/variant": "unsloth--1409d52c-a-3-1-8b-decode"`,
but the **actual model hash** (and thus the VA name) is
`unsloth--faee1c5b-a-3-1-8b-decode` (VA name = `<llm-d.ai/model>-decode`). The
controller keys metrics→VA on the `llm_d_ai_variant` label, which **must equal the
VA name**. The hardcoded `1409d52c` hash never matches `faee1c5b`. *(Report
upstream: the bundled `1409d52c` label is stale for this model.)*

### 8.2 No relabeling + multi-scrape collision
- The chart `vllmService` ServiceMonitor (which would propagate
  `llm-d.ai/variant` → `llm_d_ai_variant`) is **disabled** by the template
  (`19_wva-values.yaml.j2` hardcodes `vllmService.enabled: false`), so scraped
  metrics carry **no** `llm_d_ai_variant` at all.
- Even with it on, the modelservice podmonitor **also** scrapes the same pod
  `:8200` with an empty `llm_d_ai_variant`. The collector keys `podData` by
  `pod:port` (`replica_metrics.go` `buildInstanceKey`), so the empty-label series
  **collides** with and overwrites the labeled one → pod skipped.
  *(Potential WVA finding: the collector's last-write-wins on `vaName` across
  multiple scrape jobs for the same `pod:port` can drop a valid mapping. It should
  prefer a non-empty `llm_d_ai_variant`.)*

**Working correction** — one relabeled PodMonitor as the **sole** scrape of the
decode pod, deriving the label from the correct model hash:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: wva-variant-relabel-decode
  namespace: dhl-wva
spec:
  selector:
    matchLabels:
      llm-d.ai/role: decode
      llm-d.ai/model: unsloth--faee1c5b-a-3-1-8b
  podMetricsEndpoints:
    - port: metrics
      path: /metrics
      interval: 15s
      relabelings:                       # __meta_* only available here
        - sourceLabels: [__meta_kubernetes_pod_label_llm_d_ai_model]
          regex: (.+)
          targetLabel: llm_d_ai_variant
          replacement: ${1}-decode       # = the VariantAutoscaling name
```

```bash
oc apply -f wva-variant-relabel-decode.podmonitor.yaml
# remove the competing empty-label scrapes (collision source):
oc delete podmonitor unsloth--faee1c5b-a-3-1-8b-decode-podmonitor vllm-unsloth--faee1c5b-a-3-1-8b -n dhl-wva
```

> **Why not just fix the primary's pod label?** The wrong `…1409d52c…` hash is
> baked into the primary Deployment's **immutable `spec.selector`**, so it can't be
> patched post-standup (would require recreating the Deployment). Hence the
> model-hash-derived relabel for the primary. The **secondary** (added by
> `add_variant.py`) gets the correct `llm-d.ai/variant=<VA-name>` label, so its
> PodMonitor can relabel straight from it.
>
> Cleaner long-term fix (not yet done): correct the scenario's `llm-d.ai/variant`
> hash to match the model **before standup**, enable the `vllmService` SM as the
> **single** relabeled scrape, and suppress the modelservice podmonitor.

### 8.3 Per-variant PodMonitors (two-variant case)
The primary PodMonitor must **exclude** secondary pods (else it tags them
`…-decode`, colliding with the secondary's `…-decode-v2`). Scope it with a
`matchExpressions` `DoesNotExist` on `wva.llmd.ai/variant`, and add a second
PodMonitor for the secondary:

```yaml
# Primary: relabel <model>-decode, EXCLUDE secondary
spec:
  selector:
    matchLabels: { llm-d.ai/role: decode, llm-d.ai/model: unsloth--faee1c5b-a-3-1-8b }
    matchExpressions: [{ key: wva.llmd.ai/variant, operator: DoesNotExist }]
  podMetricsEndpoints:
    - { port: metrics, path: /metrics, interval: 15s,
        relabelings: [{ sourceLabels: [__meta_kubernetes_pod_label_llm_d_ai_model],
                        regex: (.+), targetLabel: llm_d_ai_variant, replacement: ${1}-decode }] }
---
# Secondary: relabel straight from its (correct) llm-d.ai/variant label
spec:
  selector:
    matchLabels: { wva.llmd.ai/variant: v2 }
  podMetricsEndpoints:
    - { port: metrics, path: /metrics, interval: 15s,
        relabelings: [{ sourceLabels: [__meta_kubernetes_pod_label_llm_d_ai_variant],
                        regex: (.+), targetLabel: llm_d_ai_variant, replacement: ${1} }] }
```

Verify the label is in Thanos and unique per pod:
```bash
TOK=$(oc whoami -t); THANOS=$(oc get route -n openshift-monitoring thanos-querier -o jsonpath='{.spec.host}')
curl -sk -H "Authorization: Bearer $TOK" "https://$THANOS/api/v1/query" \
  --data-urlencode 'query=vllm:kv_cache_usage_perc{namespace="dhl-wva"}'   # one series, llm_d_ai_variant=unsloth--faee1c5b-a-3-1-8b-decode
```
Then the VA should flip `METRICSREADY=True` within a reconcile (~60s) once the
stale empty-label series ages out of the `max_over_time[1m]` window.

---

## 9. Supplemental RBAC (only if you stayed on chart 0.6.0)

If you did NOT bump to chart 0.7.0, grant the missing perms manually:
```yaml
# Role wva-supplemental-hpa-keda + RoleBinding to SA
# workload-variant-autoscaler-controller-manager, granting:
#   autoscaling/horizontalpodautoscalers  get,list,watch,create,update,patch,delete
#   keda.sh/scaledobjects                 get,list,watch
```
With chart 0.7.0 this is unnecessary (the chart Role already grants read on both).

---

## 9a. Verify ThroughputAnalyzer (TA) runs alongside sat_v2

TA is registered unconditionally (`cmd/main.go` `RegisterAnalyzer(throughput…)`)
and invoked every cycle in `engine_v2.go runAnalyzersAndScore`, gated by
`effectiveEnabled("throughput", cfg)` which **defaults true** (no disabling entry
in our config). sat_v2 remains the decision-driving analyzer; TA's result is
scored into the cost-aware optimizer input.

TA's per-cycle logs are at verbosity 4. Enable with the **`--v=4`** arg (note:
double-dash `--v`, NOT `-v=4`, which crashes the manager with
`unknown shorthand flag: 'v'`):
```bash
oc patch deployment workload-variant-autoscaler-controller-manager -n dhl-wva --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--v=4"}]'
```
Confirm both analyzers active:
```
engine.go  Optimizer selected {analyzer: "saturation", optimizer: "cost-aware"}
throughput/analyzer.go  throughput analyzer: ... {variant: "…-decode"}    # primary
throughput/analyzer.go  throughput analyzer: ... {variant: "…-decode-v2"} # secondary
```
**At idle** TA reports sanity issues `["itl_non_positive","missing_shape_metrics"]`
— expected with no traffic (no generated tokens → no ITL; no request shape). These
clear under load, when TA fits its ITL model and emits real demand.

## 10. Add secondary variant *(done)*

```bash
python llm-d-benchmark/tools/add_variant.py -n dhl-wva \
  --config llm-d-benchmark/config/scenarios/guides/variants/v2-cost-only.yaml   # cost 5.0
```
Creates `…-decode-v2` Deployment/VA/HPA (cost 5.0) in the same InferencePool. It sets
the secondary pod's `llm-d.ai/variant=<VA-name>` **correctly** (so its PodMonitor in
§8.3 relabels straight from it). Goal under load: cheaper variant (cost 5) scales
first; expensive (cost 10) drops first. **Load run still pending — see §10b/§14.**

---

## 10b. Load experiment — findings & calibration (2026-06-15)

**guidellm did not deliver load.** Two `llmdbenchmark … run` invocations (guidellm,
constant rates) deployed the harness pod and reported it "running", but Thanos
showed **0** `num_requests_running/waiting`, 0 KV, 0 gen-token-rate on both vLLM
pods for the whole window — the load never reached vLLM. The harness pod sat in
"Waiting for pods to complete" with no requests emitted (suspect tokenizer/dataset
init or guidellm not starting the run). Root-caused by querying Thanos, **not** a
broken stack.

**The llm-d stack is healthy** (verified directly, bypassing guidellm):
- In-cluster `curl` to the gateway `/v1/completions` → **HTTP 200, 512 tokens in
  5.5 s** (~93 tok/s, ~10 ms/token single-request unloaded).
- **EPP flow control ON**: EPP runs `--config-file /config/wva-plugins.yaml`, which
  has `featureGates: [flowControl]`; `inference_extension_flow_control_queue_size`
  is present in Thanos.

**Custom load generator** (`Deployment/wva-loadgen`, fedora+curl, concurrency =
replicas × `CONCURRENCY` in-flight, decode-heavy `max_tokens=2048`, short prompt)
was used instead of guidellm — precise, observable, no harness mystery.

**Capacity calibration (decode-heavy, short prompt / 2048 output):**
- 40 in-flight → ~28–33 running, **0 waiting, KV only ~6–8%** on the serving pod.
- KV per running request ≈ 0.24% → ~**350 concurrent/pod** needed to reach the 85%
  `scaleUpThreshold`. So with these short-KV requests, the **queue**
  (`num_requests_waiting > queueLengthThreshold=5`, once concurrency exceeds vLLM's
  batch limit) trips **before** KV — pick RPS accordingly, or use larger
  prompts/outputs to bind on KV. **A clean scale-up event was not yet captured**
  (load never pushed high enough before wrap-up).

**Observed (9h + a reboot — confounded, treat as provisional):** the **expensive**
variant (primary, cost 10) ended at **0 replicas**; the **cheap** variant
(secondary, cost 5) held at 1 and served all ~33 in-flight requests. Direction is
consistent with cost-aware preference, but not a controlled observation.

**Bug candidate — expensive variant stuck at 0:** once primary reached 0 pods, the
controller repeats `scalefromzero/engine.go:176 Error Processing variant
{name: …-decode, error: "no matches for kind \"Deployment\" in version \"\""}`
(empty apiVersion in the scale-target ref) and the **primary HPA shows
`<unknown>/1`** (no pod → no `wva_desired_replicas` metric → HPA cannot scale from
zero). Net: the expensive variant cannot recover from 0. Worth filing — scale-from-
zero target resolution and/or the HPA external-metric-from-zero gap.

### Next-session plan to capture clean scaling + TA-vs-sat_v2
1. Reset both deploys to 1 replica; loadgen 0.
2. Stepped constant load, each step ≥6 min (autoscale lag ~2 min): e.g. loadgen
   replicas 0→ (low) → (high enough to push `num_requests_waiting>5` or KV>85%) →
   back to low. Watch which signal trips and whether **TA** RequiredCapacity goes
   positive **before** sat_v2 (the decode-heavy hypothesis). Capture at `--v=4`:
   grep `throughput/analyzer.go` RC/demand vs `engine_v2.go V2 saturation analysis
   completed` per cycle.
3. To make scale-up reachable at modest RPS, raise per-request KV (longer
   prompt+output) OR lower the pods' batch limit. Save per-step metrics + the
   analyzer scores at each scaling decision into `results/<ts>/`.

## 11. Findings summary (for upstream)

1. **Chart 0.6.0 RBAC gap** — missing HPA + ScaledObject read perms vs current
   `main` controller → CrashLoopBackOff. Fixed by chart 0.7.0.
2. **Scenario variant-label hash bug** — `modelArtifacts.extraLabels.llm-d.ai/variant`
   = `…1409d52c…` ≠ VA name `…faee1c5b…`; metrics can never map. Should be derived
   from the model hash, not hardcoded.
3. **`vllmService` disabled by template** — `19_wva-values.yaml.j2` forces
   `vllmService.enabled: false`, so no `llm_d_ai_variant` relabeling happens at all.
4. **Collector pod:port collision** — multiple scrape jobs for one pod, only one
   carrying `llm_d_ai_variant`, can let the empty-label series overwrite the valid
   mapping (last-write-wins on `vaName`). Candidate WVA hardening.
5. **make benchmark-* wrappers** don't fit `guides/two-variant-wva` (hardcoded to
   `inference-scheduling-wva`). Deferred TODO to generalize.
6. **guidellm `run` delivered 0 load** (harness pod ran but emitted no requests) —
   see §10b. Needs harness debugging; meanwhile a custom in-cluster curl load
   generator works.
7. **Expensive variant stuck at 0** — `scalefromzero` "no matches for kind
   Deployment in version \"\"" + HPA `<unknown>` external metric from zero (§10b).

---

## 12. Status checklist

- [x] **V2 cost-aware path on real KV confirmed.** Controller log:
      `V2 saturation analysis completed totalSupply=328960` (~329K KV tokens — real
      `cache_config_info`, not the ~6.5K batch-budget fallback),
      `V2 optimizer produced decisions {optimizer: cost-aware}`, idle
      `action: no-change target: 1 reason: "V2 steady state"`. TA3 + #1266 image
      (`:ta3` digest `sha256:9cbf1c84…`).
- [x] **TA enabled alongside sat_v2** (runtime, `--v=4`; §9a).
- [x] **Secondary variant (cost 5.0)** added via `add_variant.py`; both VAs
      `METRICSREADY=True`, both HPAs reading `wva_desired_replicas` (§8.3).
- [x] **Clean scale-up event CAPTURED 2026-06-15** — loadgen=35 (~350 in-flight) drove a
      sustained TA `joint role commit` → `wva_desired_replicas=2` → HPA `2/1` → decode-v2
      deployment actuated 1→2 pods (14:07:56Z). Full writeup +
      data: `results/20260615-122758-ta-scaleup-retest/RESULTS.md`. The basic scale-up is done.
- [x] **Cost-aware ordering confirmed** (both directions): cheap (cost 5) scales first;
      actuated steady state cheap=2/exp=1; on ramp-down cheap 2→1 to min.
- [x] **Driver = sat_v2 + cost-aware optimizer, NOT TA** — controlled Arm B (TA disabled)
      reproduced identical behavior; `joint role commit` is sat_v2's role pipeline. TA on vs off
      made no decision difference here. See `results/20260615-150601-armB-satv2-only/COMPARISON.md`.
      (Earlier "TA-before-sat_v2" claim retracted.)
- [ ] Teardown when fully done: `llmdbenchmark … teardown -p dhl-wva` (removes the
      helm releases + variants); then `oc delete podmonitor wva-variant-relabel-decode
      wva-variant-relabel-decode-v2 -n dhl-wva`, `oc delete deploy wva-loadgen -n dhl-wva`,
      `oc delete role/rolebinding wva-supplemental-hpa-keda -n dhl-wva` (if used).

### Current end-of-session state (2026-06-15 PM — scale-up retest done)
- **Scale-up retest SUCCESS** — see `results/20260615-122758-ta-scaleup-retest/RESULTS.md`
  (full writeup, CSVs, `plot.py`). Basic scale-up + cost-aware up/down + TA-before-sat_v2 all
  captured. `wva-loadgen` scaled back to **0**.
- After ramp-down both variants settled at **MIN=1 → 2 GPUs** still allocated (decode×1,
  decode-v2×1). Free with `oc scale deploy/<variant> -n dhl-wva --replicas=0` when done.
- Still deployed (no extra GPU): gateway, EPP, WVA controller (`:ta3`, `--v=4`), both VAs/HPAs,
  the two relabel PodMonitors, the supplemental RBAC role.
- Local-only changes: benchmark-branch commits (TA3 + #1266), gitignored
  `llm-d-benchmark/` clone patches (§2/§5/§7), this runbook, `results/`. Nothing pushed.

---

## 13. Reusable artifacts

### 13.1 In-cluster sanity request (proves gateway→EPP→vLLM path)
```bash
oc run sanity-curl-$RANDOM -n dhl-wva --rm -i --restart=Never --image=quay.io/curl/curl:latest --command -- \
  curl -s -m 90 -w '\nHTTP=%{http_code} total=%{time_total}s\n' \
  -X POST http://infra-llmdbench-inference-gateway-istio.dhl-wva.svc.cluster.local:80/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"unsloth/Meta-Llama-3.1-8B","prompt":"Tell me a long story:","max_tokens":512}'
# expect HTTP=200 and generated text
```

### 13.2 Custom load generator (when guidellm won't drive load)
`Deployment/wva-loadgen` — concurrency = `replicas × CONCURRENCY` in-flight. Scale
replicas to dial load up/down. Decode-heavy by default (short prompt, 2048 output).
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: wva-loadgen, namespace: dhl-wva, labels: { app: wva-loadgen } }
spec:
  replicas: 0
  selector: { matchLabels: { app: wva-loadgen } }
  template:
    metadata: { labels: { app: wva-loadgen } }
    spec:
      containers:
        - name: loadgen
          image: quay.io/curl/curl:latest
          env:
            - { name: URL,   value: "http://infra-llmdbench-inference-gateway-istio.dhl-wva.svc.cluster.local:80/v1/completions" }
            - { name: MODEL, value: "unsloth/Meta-Llama-3.1-8B" }
            - { name: CONCURRENCY, value: "10" }
            - { name: MAX_TOKENS,  value: "2048" }
          command: ["/bin/sh","-c"]
          args:
            - |
              BODY="{\"model\":\"$MODEL\",\"prompt\":\"Tell me a very long detailed story:\",\"max_tokens\":$MAX_TOKENS,\"temperature\":0.7}"
              while true; do seq 1 "$CONCURRENCY" | xargs -P "$CONCURRENCY" -I{} \
                curl -s -o /dev/null -m 300 -X POST "$URL" -H "Content-Type: application/json" -d "$BODY"; done
          resources: { requests: { cpu: "200m", memory: 128Mi }, limits: { cpu: "1", memory: 256Mi } }
```
`oc scale deploy/wva-loadgen -n dhl-wva --replicas=N` to drive ~N×10 in-flight.

### 13.3 Watch the signals (Thanos)
```bash
TOK=$(oc whoami -t); THANOS=$(oc get route -n openshift-monitoring thanos-querier -o jsonpath='{.spec.host}')
q(){ curl -sk -H "Authorization: Bearer $TOK" "https://$THANOS/api/v1/query" --data-urlencode "query=$1" \
     | python3 -c "import sys,json;r=json.load(sys.stdin)['data']['result'];print(r[0]['value'][1] if r else 'na')"; }
q 'sum(vllm:num_requests_running{namespace="dhl-wva"})'
q 'sum(vllm:num_requests_waiting{namespace="dhl-wva"})'           # queue → sat_v2 queue trigger (>5)
q 'max(vllm:kv_cache_usage_perc{namespace="dhl-wva"})'            # KV → sat_v2 KV trigger (>0.85)
q 'wva_desired_replicas'                                          # the metric WVA emits → HPA
q 'sum(inference_extension_flow_control_queue_size) by (model_name)'
```
WVA controller decisions: `oc logs -n dhl-wva deploy/workload-variant-autoscaler-controller-manager -f | grep -E "Optimizer selected|V2 saturation analysis completed|throughput/analyzer|Processing decision|desiredReplicas"`

---

## 14. NEXT SESSION — clear TA working test (start here)

Goal: a **clear, working** demonstration that TA drives scaling — we have **not**
yet seen a basic scale-up. Approach per Dean:

1. **Start from the e2e tests, not guidellm.** The WVA repo `test/e2e/` already has
   known-working load drivers and HPA-actuation assertions against the emulator;
   use them as the reference for *how* load is driven and *what* to assert
   (`wva_desired_replicas` → HPA → replicas). Mirror that load path on pokprod
   instead of fighting the guidellm harness. (guidellm delivered 0 load this
   session — §10b; **if it still won't drive load, use `inference-perf`** which the
   scenario also supports.)
2. **Simple workload, drive the rate up.** Reset both variants to 1 replica. Use a
   single constant rate, then step it up; hold each step ≥6 min (autoscale lag
   ~2 min) so WVA settles on an exact replica count. Custom loadgen (§13.2) is the
   reliable fallback — scale its replicas to ramp.
3. **See the metric sent to HPA.** The headline signal is `wva_desired_replicas`
   (emitted by WVA, consumed by the HPA external metric). Watch it rise with load
   and the HPA `REPLICAS` follow (§13.3). This is the "basic scenario" not yet seen.
4. **Make saturation reachable.** Decode-heavy short requests need ~350 conc/pod for
   KV>85% (§10b). Either drive enough concurrency to build the **queue**
   (`num_requests_waiting>5`) — which trips sat_v2 sooner — or use larger
   prompt+output so KV binds. For the **TA-before-sat_v2** hypothesis, decode-heavy
   + a *slow* RPS ramp should let TA's RequiredCapacity go positive before sat_v2's
   KV/queue gate.
5. **Collect results / use the dashboard.** Capture per-step metrics into
   `results/<ts>/` (§13.3 queries), and/or use the WVA Grafana dashboard if
   available on pokprod to visualize `wva_desired_replicas`, KV, queue, per-variant
   replicas. Summarize each scaling event with the **analyzer scores** that drove it
   (`--v=4`: throughput RC/demand vs sat_v2 `totalSupply/totalDemand/spareCapacity`).
6. **Watch the scale-from-zero bug** (§10b, finding 7): keep `minReplicas≥1` honored,
   or fix the `scalefromzero` "no matches for kind Deployment" / HPA-`<unknown>`
   recovery before expecting the expensive variant to come back from 0.

Everything needed to rebuild the environment from scratch is in §§1–9; the load
calibration and signals are in §10b/§13.
