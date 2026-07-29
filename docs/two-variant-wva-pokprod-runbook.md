# Two-Variant WVA Benchmark on pokprod — KEDA Runbook (Tier B)

End-to-end runbook for standing up the **two-variant-wva** cost-aware benchmark on
the pokprod real-GPU OpenShift cluster, driving load, and reading the autoscaling
signals — against the **KEDA ScaledObject** autoscaling path (Ofer's
[`biranofer/llm-d-benchmark @ feat/multi-variant-benchmark`](https://github.com/biranofer/llm-d-benchmark)
harness, adopted into this repo's `hack/benchmark` in #1435).

> **Tier separation (read first).**
> - **Tier A — the code under test.** The WVA controller image
>   (`quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9`) is built from a
>   code worktree (main + the TA PR branches) and pushed to Dean's fork/quay. It is
>   pinned here **only** as the `.env` value `WVA_IMAGE_TAG`. The build/push is
>   **Dean's** — it is not part of this branch and this runbook never rebuilds it.
> - **Tier B — this benchmark harness.** Everything in this runbook (the scenario
>   guides, `.env`, `make benchmark-*` targets, this file, `results/`) lives on the
>   `benchmark` branch and is pushed to **Dean's fork only — never `upstream`.**
>
> **Separation invariant.** The controller under test is always the Tier-A
> image/tag. If it must change, the change is made in a code worktree (PR branch) →
> re-tag → re-image → update `WVA_IMAGE_TAG` here. The benchmark branch never
> carries WVA controller source edits.

> **Cluster safety (pokprod is shared).** All cluster actions are scoped to Dean's
> namespace with an explicit `-n <ns>`; never mutate cluster-global state. Teardown
> requires Dean's explicit approval on that specific action.

> **This benchmark cannot run on kind** — it deploys real `vllm-openai` on real
> GPUs and depends on `vllm:cache_config_info` reporting real KV memory. Use a GPU
> OpenShift cluster.

> **History / VA+HPA legacy.** The earlier VA+HPA recipe (chart-0.6.0/0.7.0 RBAC
> fixes, manual PodMonitor relabeling, the `:ta3` image, and the 2026-06-15 load
> findings) is preserved on the archived branch **`archive/benchmark-ta3-legacy`**
> (`docs/two-variant-wva-ta3-runbook.md`). It is the proven fallback if the KEDA
> path here fails — see §13.

---

## 1. Environment

Set every environment-specific value in `hack/benchmark/.env` (see §4); nothing
below is hardcoded in the scenario files.

| Thing | Value (this campaign) | `.env` key |
|---|---|---|
| Cluster | OpenShift pokprod → `api.pokprod001.ete14.res.ibm.com` | — |
| Namespace | `dhl-wva-209` (Dean's; can read `thanos-querier-tls`) | `BENCHMARK_NAMESPACE` |
| GPUs | nodes `NVIDIA-H100-80GB-HBM3` | `ACCELERATOR_NAME` |
| Model | `unsloth/Meta-Llama-3.1-8B-Instruct` (ungated, chat-templated) | `BENCHMARK_MODEL_ID` / `BENCHMARK_MODEL_SHORTNAME` |
| vLLM image | `docker.io/vllm/vllm-openai:v0.14.0` (≥ v0.14.0 needed for `cache_config_info`) | `VLLM_IMAGE_REPO` / `VLLM_IMAGE_TAG` |
| WVA image (**Tier A**) | `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (**public**) | `WVA_IMAGE_REPO` / `WVA_IMAGE_TAG` |
| WVA chart | `0.8.0-rc5` (Ofer's) — see the compat note in §12 | `WVA_CHART_VERSION` |
| prometheus-adapter chart | `5.2.0` | `PROMETHEUS_ADAPTER_CHART_VERSION` |
| Prometheus (Thanos) | `thanos-querier.openshift-monitoring` | `PROMETHEUS_URL` |
| PodMonitor release label | `llmd` | `PROM_RELEASE_LABEL` |
| Benchmark CLI | `llmdbenchmark` from Ofer's `feat/multi-variant-benchmark`, in a `uv` venv | — |

Model note: the default is an **INSTRUCT** (chat-templated) model. On
llm-d-benchmark ≥ v0.7.0 the decode image ships transformers ≥ 4.44, which rejects
a base model (no chat template) with `ChatTemplateResolutionError`. Override
`BENCHMARK_MODEL_ID` only with another chat-templated model (or supply
`--chat-template`).

---

## 2. Host tools (one-time)

The benchmark CLI installer (`llm-d-benchmark/install.sh`) pins tool versions and
`sudo`-installs any below pin — which fails in a no-sudo environment. Pre-install
these to satisfy the pins (user-space `crane`; the rest globally) so the
installer's tool phase is a no-op:

| Tool | Pinned | Note |
|---|---|---|
| helmfile | 1.5.1 | hard-fail in installer if below |
| yq | v4.53.2 | |
| kustomize | v5.8.1 | |
| jq | 1.8.1 | |
| skopeo | 1.20.1 | |
| crane | 0.21.6 | installed to `~/go/bin` (user-space) |

`curl` below-pin is non-critical (skipped). `pg_config` missing is fine on amd64
(the `psycopg2-binary` wheel installs).

**Local patch to the cloned installer:** `llm-d-benchmark/install.sh` runs
`sudo apt-get update` unconditionally on Ubuntu (gated by a var it hard-sets to 0).
Comment out that single line — all apt tools are already present, so the refresh is
a no-op. (The clone is gitignored.)

---

## 3. Install the benchmark CLI

From the `benchmark/` worktree, pointed at Ofer's fork/branch (the upstream default
does **not** contain the two-variant scenario):

```bash
make benchmark-install \
  BENCHMARK_REPO_URL=https://github.com/biranofer/llm-d-benchmark.git \
  BENCHMARK_REPO_REF=feat/multi-variant-benchmark \
  BENCHMARK_UV=true
# if the sudo-apt line aborts it, apply the §2 patch then:
cd llm-d-benchmark && ./install.sh --uv
```

CLI binary: `llm-d-benchmark/.venv/bin/llmdbenchmark`.

> Keep the embedded `llm-d-benchmark` clone on Ofer's `feat/multi-variant-benchmark`
> so Dean and Ofer run the same scenario definition. That clone's own
> `docs/multi-variant-benchmark.md` guide is the **pre-KEDA VA+HPA** recipe — the
> KEDA path lives only in this repo's `hack/benchmark` scenario files, which
> `make benchmark-standup` copies into the clone (Makefile ~L379–421; the `awk`
> block rewrites `scaledObject:` bounds from `BENCHMARK_KEDA_*`, then a token-`sed`
> substitutes every `.env` value — §4).

---

## 4. Configure `hack/benchmark/.env`

All environment-specific values are parametrized. Copy the sample, fill in every
value (there are **no defaults** for env-specific keys — standup fails loudly if any
placeholder token survives):

```bash
cp hack/benchmark/.env.sample hack/benchmark/.env
$EDITOR hack/benchmark/.env        # set NAMESPACE, ACCELERATOR, model, images, chart versions…
```

`hack/benchmark/.env` is gitignored. The Makefile `-include`s it before its `?=`
defaults, so `.env` wins over defaults and a CLI `VAR=…` still wins over `.env`.
At `make benchmark-standup` / `benchmark-run` time, the committed scenario guide
(which carries `__VAR__` placeholder tokens) is copied into the clone and each token
is substituted from the corresponding `.env` value; a residual-token guard aborts
the run if any variable is unset.

Keys (see `hack/benchmark/.env.sample` for the annotated list): `WVA_IMAGE_REPO`,
`WVA_IMAGE_TAG`, `BENCHMARK_NAMESPACE`, `ACCELERATOR_NAME`, `PROMETHEUS_URL`,
`BENCHMARK_MODEL_ID`, `BENCHMARK_MODEL_SHORTNAME`, `PROM_RELEASE_LABEL`,
`WVA_WORKDIR`, `VLLM_IMAGE_REPO`, `VLLM_IMAGE_TAG`, `WVA_CHART_VERSION`,
`PROMETHEUS_ADAPTER_CHART_VERSION`, `PRIMARY_COST`, `PRIMARY_MIN`, `PRIMARY_MAX`.

---

## 5. Tier-A controller image

The controller image is **not built by this branch**. It is pinned as a `.env`
value and pulled by the cluster:

```
WVA_IMAGE_REPO=quay.io/deanlorenz/llm-d-workload-variant-autoscaler
WVA_IMAGE_TAG=ta-0.9
```

Build/push is Dean's (in a code worktree). The cluster pulls anonymously, so the
quay repo must be **public** (`quay.io` → repo → Settings → Make Public;
vulnerability flags are cosmetic). Record the pushed digest here at deploy time.

---

## 6. Standup

```bash
export HF_TOKEN=hf_...            # in your shell (or ~/.profile, then source it)
make benchmark-standup BENCHMARK_NAMESPACE=<ns> BENCHMARK_SPEC=guides/two-variant-wva
```

Dry-run first with the CLI `--dry-run` if you want to inspect manifests (note: the
dry-run "Could not extract Prometheus CA cert" warning is an artifact — a real admin
run extracts it fine; prometheus-adapter is reused if already installed
cluster-wide).

Standup installs the helm releases (`infra-llmdbench`, `…-gaie`, `…-ms`,
`workload-variant-autoscaler`) + the decode vLLM pod, runs a smoketest, and ends
with `✅ All smoketest steps complete`. The Capacity Planner log confirms real KV —
the signal the cost-aware demo needs.

**Verify the controller is healthy and on the Tier-A image:**
```bash
oc get pods -n <ns> -l control-plane=controller-manager
oc get pods -n <ns> -l control-plane=controller-manager \
  -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'   # must be the :ta-0.9 digest
```
If it CrashLoopBackOffs on missing KEDA/HPA RBAC, that is the chart-vs-image compat
failure mode — see §12.

---

## 7. Add the second variant (KEDA ScaledObject)

```bash
make benchmark-add-variant BENCHMARK_NAMESPACE=<ns>
```

This runs `hack/benchmark/add_variant.py`, which:
- creates a **KEDA ScaledObject** for the primary (on first run) and for the added
  secondary variant (default cost 5.0), both carrying `llm-d.ai/managed` so WVA
  discovers them and drives them via `wva_desired_replicas`;
- creates the secondary Deployment sharing the same InferencePool / EPP, keeping the
  camelCase + model-hash pod labels (so the pool picks it up) but omitting the
  primary's kebab discriminator;
- sets the secondary pod's `llm-d.ai/variant=<VA-name>` **correctly** post-standup
  (`fix_variant_pod_label()`), so the WVA collector maps its metrics to the right
  variant (this is the automated replacement for the manual PodMonitor relabeling
  the legacy VA+HPA runbook needed — see §11).

Required `.env`-backed flags are passed automatically by the make target:
`--accelerator-name`, `--prometheus-url`, `--primary-cost`, `--primary-min`,
`--primary-max` (all required, no defaults).

---

## 8. Enable V2 saturation (cost-aware path)

```bash
make benchmark-enable-v2-saturation BENCHMARK_NAMESPACE=<ns>
```

Patches the saturation-scaling ConfigMap to enable the V2 analyzer and restarts the
controller. Confirm:
```bash
oc logs -n <ns> deploy/workload-variant-autoscaler-controller-manager --tail=50 \
  | grep "Processing model (V2)"
```

---

## 9. Verify ThroughputAnalyzer (TA) runs alongside sat_v2

TA is registered unconditionally and invoked every cycle, gated by
`effectiveEnabled("throughput", cfg)` which **defaults true**. sat_v2 remains the
decision-driving analyzer; TA's result is scored into the cost-aware optimizer
input.

TA's per-cycle logs are at verbosity 4. Enable with the **`--v=4`** arg (note:
double-dash `--v`, NOT `-v=4`, which crashes the manager with
`unknown shorthand flag: 'v'`):
```bash
oc patch deployment workload-variant-autoscaler-controller-manager -n <ns> --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--v=4"}]'
```
Confirm both analyzers active:
```
engine.go  Optimizer selected {analyzer: "saturation", optimizer: "cost-aware"}
throughput/analyzer.go  throughput analyzer: ... {variant: "…-decode"}      # primary
throughput/analyzer.go  throughput analyzer: ... {variant: "…-decode-v2"}   # secondary
```
**At idle** TA reports sanity issues `["itl_non_positive","missing_shape_metrics"]`
— expected with no traffic. These clear under load, when TA fits its ITL model and
emits real demand.

---

## 10. Drive load & watch the signals

Preferred: `make benchmark-run` (guidellm or inference-perf). If guidellm delivers
no load (a known failure mode from the legacy campaign — the harness pod runs but
emits no requests), use `inference-perf`, or the custom in-cluster load generator
below (reliable, precise, observable).

### 10.1 In-cluster sanity request (proves gateway→EPP→vLLM path)
```bash
oc run sanity-curl-$RANDOM -n <ns> --rm -i --restart=Never --image=quay.io/curl/curl:latest --command -- \
  curl -s -m 90 -w '\nHTTP=%{http_code} total=%{time_total}s\n' \
  -X POST http://infra-llmdbench-inference-gateway-istio.<ns>.svc.cluster.local:80/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"<BENCHMARK_MODEL_ID>","prompt":"Tell me a long story:","max_tokens":512}'
# expect HTTP=200 and generated text
```

### 10.2 Custom load generator (fallback when the harness won't drive load)
`Deployment/wva-loadgen` — concurrency = `replicas × CONCURRENCY` in-flight. Scale
replicas to dial load up/down. Decode-heavy by default (short prompt, 2048 output).
```yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: wva-loadgen, namespace: <ns>, labels: { app: wva-loadgen } }
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
            - { name: URL,   value: "http://infra-llmdbench-inference-gateway-istio.<ns>.svc.cluster.local:80/v1/completions" }
            - { name: MODEL, value: "<BENCHMARK_MODEL_ID>" }
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
`oc scale deploy/wva-loadgen -n <ns> --replicas=N` to drive ~N×10 in-flight.

Calibration note (decode-heavy, short prompt / 2048 output, H100): KV per running
request ≈ 0.24% → ~350 concurrent/pod to reach an 85% KV `scaleUpThreshold`. With
short-KV requests the **queue** (`num_requests_waiting > queueLengthThreshold`) trips
before KV — pick RPS accordingly, or use larger prompts/outputs to bind on KV. Hold
each load step ≥ 6 min (autoscale lag ~2 min) so the controller settles on an exact
replica count.

### 10.3 Watch the signals (Thanos)
```bash
TOK=$(oc whoami -t); THANOS=$(oc get route -n openshift-monitoring thanos-querier -o jsonpath='{.spec.host}')
q(){ curl -sk -H "Authorization: Bearer $TOK" "https://$THANOS/api/v1/query" --data-urlencode "query=$1" \
     | python3 -c "import sys,json;r=json.load(sys.stdin)['data']['result'];print(r[0]['value'][1] if r else 'na')"; }
q 'sum(vllm:num_requests_running{namespace="<ns>"})'
q 'sum(vllm:num_requests_waiting{namespace="<ns>"})'           # queue → sat_v2 queue trigger
q 'max(vllm:kv_cache_usage_perc{namespace="<ns>"})'            # KV → sat_v2 KV trigger (>0.85)
q 'wva_desired_replicas'                                       # the metric WVA emits → KEDA ScaledObject
q 'sum(inference_extension_flow_control_queue_size) by (model_name)'
```
WVA controller decisions:
```bash
oc logs -n <ns> deploy/workload-variant-autoscaler-controller-manager -f \
  | grep -E "Optimizer selected|V2 saturation analysis completed|throughput/analyzer|Processing decision|desiredReplicas"
```

The headline signal is `wva_desired_replicas` (emitted by WVA, consumed by the KEDA
ScaledObject). Watch it rise with load and the ScaledObject's replica count follow.
Capture per-step metrics + the analyzer scores at each scaling decision into
`results/<ts>/` (Tier B, fork-only).

---

## 11. Troubleshooting

**`METRICSREADY=False` / `TotalKvCapacityTokens=0` / "No saturation metrics
available".** The WVA collector keys metrics to a variant on the `llm_d_ai_variant`
label, which must equal the VariantAutoscaling name. On the KEDA path this is
handled for you: the scenario sets `wva.vllmService.enabled: true` (the WVA
ServiceMonitor propagates the pod's `llm-d.ai/variant` → `llm_d_ai_variant`), and
`make benchmark-add-variant` sets the correct variant label post-standup. If the VA
still won't flip `METRICSREADY=True`:
- confirm the ServiceMonitor is present and the metric carries a non-empty
  `llm_d_ai_variant`:
  ```bash
  q 'vllm:cache_config_info{namespace="<ns>"}'     # should carry llm_d_ai_variant=<VA-name>
  ```
- confirm no *second* scrape job hits the same `pod:port` with an empty
  `llm_d_ai_variant` (the collector keys `podData` by `pod:port`; an empty-label
  series can collide with and overwrite the labeled one). If it does, remove the
  competing scrape.
- the VA flips within a reconcile (~60s) once the correct series is the only one in
  the `max_over_time[1m]` window.

For the deep VA+HPA-era history of this failure (the stale scenario hash, the
manual PodMonitor relabeling, the collector last-write-wins collision), see
`archive/benchmark-ta3-legacy` §8.

**Controller CrashLoopBackOff at standup** — usually a chart-vs-image RBAC gap; see
§12.

---

## 12. Compatibility risk — `:ta-0.9` image + `0.8.0-rc5` chart

The benchmark installs the WVA helm chart pinned by `WVA_CHART_VERSION` (currently
Ofer's **`0.8.0-rc5`**) with the controller image overridden to the Tier-A
`WVA_IMAGE_TAG` (**`:ta-0.9`**). These two were not cut together, so there is a
compat risk:

- The chart's bundled RBAC `Role` must grant everything the `ta-0.9` controller
  watches — including `keda.sh/scaledobjects` and (on the KEDA path) any HPA perms
  KEDA creates. In the legacy campaign an older chart's missing KEDA/HPA read perms
  caused the manager caches to never sync → `failed to wait for scaledobject caches
  to sync` → CrashLoopBackOff. `ta-0.9` carries the KEDA RBAC in its own kustomize
  config (PR #1341), but the *chart-installed* RBAC is what governs the deployed
  Role here.
- **If the controller CrashLoopBackOffs on missing RBAC:** bump `WVA_CHART_VERSION`
  to a chart that grants the needed perms, or apply a supplemental Role/RoleBinding
  in `<ns>` granting the controller SA read on `keda.sh/scaledobjects` (and HPA
  perms if the failure names them). Record whatever was needed here.
- Verify at standup: controller healthy (§6) **and** on the `:ta-0.9` digest.

---

## 13. Fallback — legacy VA+HPA path

If the KEDA path cannot be made to work, the proven recovery path is the archived
VA+HPA runbook on **`archive/benchmark-ta3-legacy`**
(`docs/two-variant-wva-ta3-runbook.md`): chart-0.7.0 RBAC, the `:ta3` image, manual
PodMonitor relabeling (§8 there), and the captured 2026-06-15 scale-up results. That
branch is read-only reference; do not merge it forward.

---

## 14. Teardown

**Requires Dean's explicit approval on that specific action** (shared cluster).
Namespace-scoped only; never touches cluster-global state.

```bash
make benchmark-teardown BENCHMARK_NAMESPACE=<ns>
# then, if created manually:
oc delete deploy/wva-loadgen -n <ns> --ignore-not-found
oc scale deploy/<variant> -n <ns> --replicas=0     # free GPUs before full teardown
```
