last_update: 2026-07-30T18:30:00+03:00
state: blocked
current_step: First live standup RAN on dhl-wva-209 (Dean-authorized, 1-replica). Fork patches all confirmed working live (UWM reuse, thanos ClusterRole reuse, prometheus-adapter reuse). Two failures, both resolved/understood — (1) sudo-in-background blocker at benchmark-install → fixed with Makefile auto-detect guard (uncommitted); (2) step_03 WVA-controller 300s pod-Ready timeout caused by node pokprod-b93r44s0 going UNREACHABLE mid-standup (infra, not harness) → controller auto-rescheduled, now 1/1 Running on pokprod-b93r38s3, ta-0.9 image healthy, reconcile loop live. Steps 04/05/07/09 (incl. vLLM deploy) never ran. Ready to re-run (idempotent) once controller-up.
blocked_on: (1) Dean per-action confirmation to RE-RUN `make benchmark-standup-shared BENCHMARK_NAMESPACE=dhl-wva-209 BENCHMARK_KEDA_MAX_REPLICAS=1` now that the controller is healthy (step_03 helm is idempotent; pod-Ready wait should pass immediately → proceeds into 04/05/07/09 + vLLM deploy). Every cluster mutation still requires Dean's explicit per-action confirmation.

## First live standup on dhl-wva-209 — patches validated, 2 failures resolved, controller now healthy (2026-07-30 18:30)
Dean authorized the first live 1-replica standup ("proceed … limit everything to 1 replica"). Ran `make benchmark-standup-shared BENCHMARK_NAMESPACE=dhl-wva-209 BENCHMARK_KEDA_MAX_REPLICAS=1`.

**All three fork patches confirmed working against the live cluster:**
- step_03 UWM reuse — "User workload monitoring already enabled -- reusing" (no cluster-monitoring-config write).
- wva.py thanos ClusterRole reuse — "thanos-querier ClusterRole(s) already present -- reusing".
- prometheus-adapter reuse — found existing release in `workload-variant-autoscaler-monitoring`, reused (no reinstall).
- 1-replica override propagated through the sub-make: replicas/min/max all = 1. Capacity planner passed (decode 2 GPU/replica, 8B needs 14.96 GB, matched H100-80GB, 136 GB avail).

**Failure 1 — sudo hidden in background (FIXED).** `benchmark-standup` unconditionally called `@$(MAKE) benchmark-install` → `install.sh` → `sudo apt-get update` (unconditional on Ubuntu, install.sh:207-211), which died `sudo: a terminal is required` in the non-interactive shell. NO cluster mutation. Fix (Dean's Option-1, Makefile:392, UNCOMMITTED in worktree): auto-detect guard — probes helm/kubectl/oc/helmfile/yq/kustomize/jq/crane/skopeo + llmdbenchmark + clone; if all present → skip benchmark-install, sync clone only; if any missing → error with instructions to run `make benchmark-install` in a real terminal (sudo prompts there). Never hides sudo in the background.

**Failure 2 — step_03 300s WVA-controller timeout = INFRA, not harness (RESOLVED by auto-reschedule).** After the guard fix, re-ran; step_03 installed the WVA chart fine but the controller pod `…-r57kf` sat Pending 300s → `Timed out waiting for WVA controller … after 300s` → step_03 FAILED, make Error 2, steps 04/05/07/09 never ran. Root cause: node `pokprod-b93r44s0` (where that pod scheduled) went **unreachable** at 15:15:33 — all node conditions `Unknown`, taints `node.kubernetes.io/unreachable:NoSchedule`+`:NoExecute`. The NoExecute 300s eviction toleration coincided with wva.py's 300s pod-Ready wait, so the harness timed out at the same instant the pod got evicted+rescheduled. Replacement pod `…-89qv9` scheduled onto healthy `pokprod-b93r38s3`, **1/1 Running**: ta-0.9 pulled in 5.5s, all controllers started (scaledobject/configmap/inferencepool), metrics on :8443, reconcile loop live. Controller deployment 1/1 AVAILABLE. Harness behaved correctly (hard-failed rather than racing ahead).

**NEXT:** re-run is idempotent (step_03 is `helm upgrade --install`; controller already Running → pod-Ready wait passes immediately → proceeds into 04/05/07/09 incl. vLLM deploy). Awaiting Dean per-action confirmation before the re-run. Optional harness robustness follow-up: wva.py 300s wait vs. the 300s NoExecute toleration is a knife-edge on flaky nodes — consider a longer/again-retry wait or tolerating a single mid-wait reschedule.

## Fork patches committed + pushed; live command ready for final go (2026-07-30 16:15, no cluster mutation)
Per Dean "OK on all. proceed." — executed the Bucket-1/Bucket-2 split, committed, pushed.

**Two DCO-signed commits on `origin/wva-ta-benchmark`** (the branch the standup's `git reset --hard origin/wva-ta-benchmark` pulls from, so the live run gets patched code):
- `e88b882` — Bucket 1 (should-have gates, will eventually become upstream issues/PRs, NOT priority): step_07 gateway-provider apply now presence-gated on the istio CRD (mirrors step_02's own `_install_gateway_provider` gate — this is the ONE genuine live hazard, ungated it would upgrade/adopt shared istiod); wva.py thanos-querier ClusterRole apply gated on all-ClusterRoles-present (was already best-effort/non-fatal). Both no-op on a fresh cluster → original install behavior preserved.
- `963bb00` — Bucket 2 (fork-only safety net, will NEVER go upstream; the make target does NOT rely on it): step_03 skips the cluster-scoped `cluster-monitoring-config` apply when UWM is already enabled (probe = `openshift-user-workload-monitoring` ns exists). On pokprod this write was verified a no-op anyway; guard is defense-in-depth.

**Charts verified present (read-only OCI/registry queries, no cluster contact):** WVA `0.8.0-rc5` (appVersion v0.8.0-rc5, digest sha256:3067b7436f897aee4fde3db170f64da8f049b2e6b6447a4eaefa96a2a9c8e1b0); prometheus-adapter `5.2.0`.

**Makefile (Tier-B WVA code, uncommitted in benchmark worktree — make reads the working tree):** added `BENCHMARK_STEPS` passthrough (`--step`) + new `benchmark-standup-shared` target = `benchmark-standup BENCHMARK_STEPS=0,3,4,5,7,9` (skips step_02 admin CRDs/SCCs + step_08 GAIE router). Safety comes from step selection + the 2 should-have gates, NOT the safety-net patch.

**Full expanded live command captured via `make -n`.** Cluster-mutating actions the wrapper itself performs, all confirmed safe:
- ClusterRole stub block is **GATED OFF** — expands to `if [ "" = "true" ]` (BENCHMARK_SKIP_PROMETHEUS_ADAPTER unset) → does NOT run. No cluster-scoped ClusterRole write from the wrapper.
- `oc label namespace dhl-wva-209 openshift.io/user-workload-monitoring=enabled --overwrite` — our own namespace, safe.
- clone git ops (`git checkout wva-ta-benchmark` + `git reset --hard origin/wva-ta-benchmark`) — pull our patched code; scenario-file sed/awk edits are on clone files, reverted via .bak at end.
- CLI: `llmdbenchmark … standup -p dhl-wva-209 -m unsloth/Meta-Llama-3.1-8B-Instruct --step 0,3,4,5,7,9 --monitoring`.

Observation (not a blocker, pre-existing in .env): VLLM image resolves to `docker.io/vllm/vllm-openai:v0.14.0` — AGENTS.md discourages docker.io for e2e; this is a scenario default set in .env, flag for later cleanup.

NEXT: present the exact command to Dean for FINAL go; run only on explicit confirmation. NO live standup until then.

## Phase 4 prep — standup dry-run findings (2026-07-30, no cluster mutation)
`.env` filled (see hack/benchmark/.env). Ran `make -n benchmark-standup BENCHMARK_NAMESPACE=dhl-wva-209
BENCHMARK_SPEC=guides/two-variant-wva` (prints only) + read-only cluster recon. Findings:

1. **Clone-clobber risk (Tier B).** `.env`/`.env.sample` do NOT set BENCHMARK_REPO_URL/REF/SPEC, so
   they fall to upstream defaults (llm-d/llm-d-benchmark.git, v0.7.0, guides/workload-autoscaling).
   Dry-run confirms bare standup does, in the embedded clone: `git fetch --tags && git checkout v0.7.0`
   then `git reset --hard origin/v0.7.0 || true` → detaches the clone off Ofer's
   `feat/multi-variant-benchmark`. Our scenario YAML survives (re-copied from hack/benchmark), but
   fork-only harness code (add_variant.py, templates) would revert to v0.7.0. Runbook §3 passes
   REPO_URL/REF to benchmark-install; §6 standup does NOT re-pass them (standup's internal
   benchmark-install uses default v0.7.0). FIX OPTIONS: (a) add the 3 vars to .env (local, safe,
   makes bare standup correct); (b) always pass on the standup CLI; (c) change .env.sample/Makefile
   defaults (committed → Dean review). → Dean decision.

2. **prometheus-adapter already installed cluster-wide.** deploy `prometheus-adapter` 2/2 in ns
   `workload-variant-autoscaler-monitoring`, 64d old; ClusterRole `prometheus-adapter-resource-reader`
   exists, helm-owned by release `prometheus-adapter`/ns `workload-variant-autoscaler-monitoring`
   (== Makefile WVA_MONITORING_NAMESPACE default). Standup MUST NOT reinstall it. Two mitigations:
   the CLI's existing-PA probe should find it; `BENCHMARK_SKIP_PROMETHEUS_ADAPTER=true` stubs the probe
   and its annotate --overwrite is idempotent here (values already match owner → NOT a hijack). Exact
   safe flag needs the CLI `--dry-run` (requires venv/clone setup first). → Dean decision + biggest
   shared-cluster risk.

3. **KEDA present** — scaledobjects.keda.sh CRD + openshift-keda/keda-metrics-apiserver (21d,
   external.metrics.k8s.io True). No KEDA install needed. (Note: only external.metrics APIService, no
   custom.metrics — matches KEDA-driven ScaledObject path.)

4. **Namespace-scoped mutations the live standup performs** (all within dhl-wva-209, gated on Dean):
   - `llmdbenchmark standup -p dhl-wva-209 -m <model> --monitoring` — helm install WVA chart + vLLM
     deploy + KEDA ScaledObjects into our namespace.
   - `BENCHMARK_MONITORING ?= true` (default) → `oc label namespace dhl-wva-209
     openshift.io/user-workload-monitoring=enabled --overwrite`.
   - `dhl-wva-209` currently EMPTY (clean slate; no deploy/scaledobject).

5. **Cluster-scoped object** `kubectl create clusterrole prometheus-adapter-resource-reader` fires
   ONLY under BENCHMARK_SKIP_PROMETHEUS_ADAPTER=true (already exists → create is no-op, annotate
   idempotent). Not set in the tested command → does not fire.

NEXT: get Dean's decisions on 1+2, then a CLI `--dry-run` (needs venv/clone on Ofer's fork) to
enumerate the exact manifests before any live apply. NO live standup until Dean's explicit go-ahead.

## Dean redirection (2026-07-30) + investigation of Ofer's llmdbenchmark flow
Dean's directives: (1a) put REPO_URL/REF/SPEC in .env; (2) shared prom/operator + KEDA + router
control plane are cluster-shared — DO NOT TOUCH; our project only triggers collection for our-NS
metrics and consumes them (setup handles access keys); use KEDA in our NS only. (3) ALL llmdbenchmark
invocations must target our NS (it's notorious for default-NS overwrites). Use OUR fork
(deanlorenz/llm-d-benchmark), learn from Ofer's but patch our fork only if really needed. CONTROL the
setup ourselves (setup cluster + add WVA — their code can help, we own the outcome); use benchmark code
to RUN the scenario + collect results; clean up between runs, NO full teardown.

### Findings (read-only recon of embedded clone @ biranofer feat/multi-variant-benchmark)
- **We have our own fork:** deanlorenz/llm-d-benchmark (parent llm-d/llm-d-benchmark). No two-variant
  branch on it yet — the scenario/harness code currently lives only on Ofer's feat/multi-variant-branch.
- **PROM_RELEASE_LABEL** = `release:` label on the vLLM **PodMonitor** (monitoring.podmonitor.labels).
  Prometheus-operator convention: a Prometheus scrapes only PodMonitors matching its
  podMonitorSelector.matchLabels. Ofer hardcodes `release: llmd` (his comment: "what
  user-workload-monitoring keys on for discovery, matching the upstream WVA guide's example"). On OCP
  UWM the platform Prometheus selects by NAMESPACE (labeled user-workload-monitoring) with a permissive
  selector → the release value is typically irrelevant; harmless carryover from self-managed
  kube-prometheus-stack. `=llmd` is safe. TODO(read-only): confirm pokprod UWM podMonitorSelector is
  permissive to be 100% sure the value doesn't matter.
- **Ofer's standup = 11 steps; shared-cluster hazards (must SKIP):**
  - step_02_admin_prerequisites → installs cluster-scoped Gateway API CRDs + inference-extension CRDs +
    OpenShift SCCs (llmdbench-agentgateway) + optional Prom CRDs. ALL already present on pokprod (verified
    oc get crd: gateways/httproutes/inferencepools/podmonitors/servicemonitors/scaledobjects) → skip, safe.
  - step_08_deploy_gaie → GAIE = router control plane → skip (Dean).
  - step_00_ensure_infra = benign (validates deps, prints banner).
- **Teardown deletes cluster-scoped ClusterRoles/Bindings (step_04_clean_cluster_roles, "admin only")** →
  NEVER run full teardown on shared cluster. Use run-phase cleanup (run/step_01_cleanup_previous,
  step_11_cleanup_post — namespace-scoped) between runs.
- **Control knobs (own the outcome w/o forking):** `standup -s/--step` takes comma-list OR ranges
  (`0,1,5` or `1-7`); per-step `should_skip(context)`; `-p/--namespace` sets deploy+benchmark NS;
  `--no-monitoring` disables PodMonitor+GAIE ServiceMonitor; scenario config has `inferenceExtension:`,
  `monitoring.installPrometheusCrds`. → We can select exactly namespace+WVA+modelservice steps, `-p
  dhl-wva-209`, skip 02/08, and never teardown — no fork patch needed yet.

### Proposed controlled approach (for Dean's confirmation — NOT yet executed)
1. Point embedded clone at deanlorenz/llm-d-benchmark; create our two-variant branch from Ofer's (we own
   it). Put BENCHMARK_REPO_URL/REF/SPEC in .env (directive 1a).
2. Setup in our NS only: `standup -p dhl-wva-209 -s <namespace,WVA-deploy,modelservice steps>` — skip
   02 (admin/CRDs/SCCs) + 08 (gaie). Enable UWM on our NS (namespace-scoped). Reuse existing shared
   prom-adapter/UWM/KEDA — don't install/modify them.
3. Run: `run` executes scenario + collects results. Between runs: namespace-scoped cleanup, no teardown.
4. Never run teardown step_04 / full teardown.
OPEN: exact step numbers for namespace/WVA/modelservice; whether WVA-deploy step needs prom-adapter or
reads UWM directly; our-fork branch strategy; confirm every step honors -p (default-NS bug). All
read-only until Dean OKs. Methodology change → planning/ta-pokprod-testing-plan.md §6/§7 needs planner revision.

## Dean clarifications (2026-07-30, round 2)
- **Packaging resolved:** install is editable (`pip install -e .`) → our fork edits win; all risky
  applies are in editable clone steps; remote `llm-d-planner@v0.1.0` is validation-only (no cluster
  writes). Caveat: editable → keep clone on our branch (the v0.7.0 clobber would swap executing code too).
- **MECHANISM correction:** end-user **makefile target must NOT depend on our fork** — it lists the
  specific safe `--step`s and runs **standard PUBLIC** llm-d-benchmark. Our fork = **testing safety net
  only** (may patch to make skips fail-safe while we test). Deliverable = public-code + explicit step
  list. NOTE: two-variant scenario not in public llm-d-benchmark yet (on Ofer's branch) → public
  end-user path depends on Ofer's work landing upstream.
- **Longer-term goals:** (1) Ofer runs OUR image (already works via WVA_IMAGE_* .env seam); (2) end-user
  TA guide (spirit of llm-d/llm-d WVA guides); (3) makefile target + setup env for safe end-user TA test.
- **Fork setup (Dean-directed) — DONE 2026-07-30:** embedded clone (benchmark/llm-d-benchmark) remotes
  now `origin`=git@github.com:deanlorenz/llm-d-benchmark.git (SSH, our fork) + `ofer`=biranofer (HTTPS,
  fetch Ofer's updates). Branch renamed feat/multi-variant-benchmark → **wva-ta-benchmark** and PUSHED to
  origin (Dean-approved; new branch @ 6d5ff6b = Ofer's tip verbatim, 826 commits all Ofer/IBM, none ours
  yet); tracks origin/wva-ta-benchmark. `.env` REPO vars (directive 1a) still TODO: BENCHMARK_REPO_URL=
  our fork, BENCHMARK_REPO_REF=wva-ta-benchmark, BENCHMARK_SPEC=guides/two-variant-wva.
- **CONFIG-CONSOLIDATION goal (Dean):** aim for variant-count as a parameter and ALL needed config in ONE
  yaml, so reproducing = point the make target at that yaml. (design target for planner/config work.)
- **Planner handoff RAISED:** plan__benchmark-controlled-setup-pivot.md — revise
  planning/ta-pokprod-testing-plan.md §6/§7 + record long-term goals + public-code-not-fork clarification.

## Standup step-number map + step_03 crux RESOLVED (2026-07-30, all read-only)
`.env` directive 1a DONE — BENCHMARK_REPO_URL=git@github.com:deanlorenz/llm-d-benchmark.git /
BENCHMARK_REPO_REF=wva-ta-benchmark / BENCHMARK_SPEC=guides/two-variant-wva now in hack/benchmark/.env
(lines 10-12). Read the standup step code + the clone's scenario config (config/scenarios/guides/
two-variant-wva.yaml). Step files present: 00, 02, 03, 04, 05, 06_{fma,kustomize,standalone}, 07,
08, 09, 10, 11.

### Scenario deploy shape (config/scenarios/guides/two-variant-wva.yaml)
`modelservice.enabled: true` (L79-80) → deploy path is **step_09_deploy_modelservice** (the step_06_*
are alternate deploy methods, gated by should_skip on deployMethod — expect them to skip when
modelservice is the method; CONFIRM via --dry-run). `wva.enabled: true` (L88), `wva.namespace: ""`
(L91) → falls back to cfg.namespace.name = our `-p` NS ✓. `monitoring.podmonitor.enabled: true`,
`release: llmd` (L250-257). `inferenceExtension:` present (L143). NOTE L93 `repository:
ghcr.io/llm-d/...` is Ofer's default in the CLONE copy — our tokenized hack/benchmark scenario
(__WVA_IMAGE_REPO__ → quay.io/deanlorenz/...:ta-0.9) is cp'd over it at standup; CONFIRM the cp wins.

### step_03 CRUX — RESOLVED (the biggest shared-prom fear)
`_install_wva_if_enabled` (step_03 L496-573) does 4 things; PA install is the only one that self-skips:
1. **prometheus-adapter install** — wva.py `install_prometheus_adapter` probes the cluster-scoped
   `prometheus-adapter-resource-reader` ClusterRole's helm-ownership annotation
   (`_find_existing_prometheus_adapter_release`, L391). If a release owns it → logs "Reusing it" and
   does NOT reinstall (wva.py L259 `if existing_release:` / install only in the `else`). pokprod HAS
   that ClusterRole (release `prometheus-adapter`/ns `workload-variant-autoscaler-monitoring`, 64d) →
   **PA install SKIPPED. SAFE.** ✓
2. **thanos-querier ClusterRole apply** (`22_prometheus-rbac`) — wva.py L329-338 is at FUNCTION-BODY
   indent, OUTSIDE the if/else → runs UNCONDITIONALLY whenever install_prometheus_adapter is called
   (which is whenever the Prom CA cert is extractable; Dean has admin → it WILL be). `kubectl apply -f`,
   check=False, "non-fatal". **This is a cluster-scoped WRITE that fires even on the PA-reuse path.**
   ⚠️ RESIDUAL HAZARD #1. Mitigate: pre-diff what 22_prometheus-rbac renders vs the existing
   ClusterRole (if identical, apply is a no-op reconcile), OR patch our fork to skip when the CR exists.
   Gate: install_prometheus_adapter only runs if `extract_prometheus_ca_cert` succeeds (tries
   secret/thanos-querier-tls [admin], else cm/openshift-service-ca.crt [any user]).
3. **WVA namespace label** (`23_wva-namespace`, apply_wva_namespace_label) — Namespace + UWM label,
   scoped to our WVA ns. SAFE (our NS).
4. **WVA controller helm chart** (`install_wva_for_namespace`, wva.py L105) — `helm upgrade --install`
   into our NS, idempotent. SAFE (our NS).

### Other steps — namespace-scoped vs cluster-scoped/router hazards
- **00 ensure_infra** — benign (validate deps/banner). Safe.
- **02 admin_prerequisites** — cluster CRDs/SCCs, ALL present on pokprod → **SKIP** (safe, verified).
- **03 workload_monitoring** — NEEDED for WVA; carries HAZARD #1 (thanos ClusterRole apply). See above.
- **04 model_namespace** — uses `context.namespace` (our `-p` NS); PVCs/model ns; namespace-scoped. NEEDED.
- **05 harness_namespace** — harness_ns + model_ns, all `--namespace` scoped. NEEDED. Namespace-scoped.
- **06_fma_deploy** — ⚠️ HAZARD #2: applies a cluster-scoped **FMA ClusterRole** (`25_fma-clusterrole`,
  L243 `kubectl apply` NO check=False → FATAL on failure) BUT first lists existing clusterroles and
  skips if present (L227-237). Only runs if this deploy variant is active (should_skip on deployMethod).
- **06_kustomize_deploy** — ⚠️ HAZARD #3: issues `CommandPhase.ROUTER` commands (L144-150) → **router
  control plane** = Dean "do not touch". SKIP if this variant is active.
- **06_standalone_deploy** — namespace-scoped (`--namespace`). Safe if active.
- **07 deploy_setup** — ⚠️ HAZARD #4: "deploy **gateway infrastructure**" — runs a gateway-provider
  helmfile (`09_helmfile-gateway-provider`) + patches infra for OpenShift agentgateway. Uses
  `--namespace` (L98) but gateway-PROVIDER helmfiles commonly install cluster-scoped CRDs/controllers →
  possible shared router-infra touch. NEEDS --dry-run to see exactly what it renders before trusting it.
- **08 deploy_gaie** — GAIE router control plane → **SKIP** (Dean).
- **09 deploy_modelservice** — deploys vLLM modelservice + a Gateway + OpenShift Route in our NS
  (`--namespace` scoped, L86-284). Our data-plane, our NS. NEEDED.
- **10 smoketest / 11 inference_test** — validation; expected read-mostly. Confirm no cluster writes.

### Provisional safe step list (pending --dry-run confirmation)
NEEDED & namespace-scoped: **03, 04, 05, 09** (+ 00 benign). SKIP: **02** (present), **08** (router).
UNRESOLVED, must --dry-run first: **07** (gateway-provider — cluster-scoped?), which **06_*** variant (if
any) is active (fma=ClusterRole, kustomize=router → both hazardous; standalone=safe), and whether the
step_03 thanos ClusterRole apply is a no-op on pokprod. 4 cluster-scoped writes total to neutralize:
step_03 thanos CR (always), 06_fma CR (if active), 07 gateway CRDs (maybe), 08 (skipped anyway).

### Next (read-only, then STOP)
A CLI `--dry-run`/render is the only way to resolve 07 + the active 06 variant + the thanos-CR diff
precisely without mutating the cluster. That needs the editable install of our fork clone (venv, no
cluster writes) — will ask Dean before running it. NO live standup until Dean's explicit go-ahead AND
the 4 cluster-scoped writes are neutralized (fork-patch-to-skip vs verified-no-op). Fork = our safety
net (Dean OK'd patching it); end-user makefile path stays public-code + explicit `--step`s.

## DRY-RUN RESULTS + corrected hazard model (2026-07-30, read-only render, NO cluster writes)
Built a controlled uv venv in the gitignored clone (`.venv`, python3.12): `uv pip install -e .` +
`uv pip install git+https://github.com/llm-d-incubation/llm-d-planner.git@v0.1.0` (planner is a HARD
import dep — step_03 imports capacity_validator at module load). Ran:
`LLMDBENCH_DRY_RUN=1 .venv/bin/llmdbenchmark --spec guides/two-variant-wva --workspace /tmp/... --base-dir
<clone> --dry-run standup -p dhl-wva-209 -m unsloth/Meta-Llama-3.1-8B-Instruct --monitoring
--skip-smoketest` → exit 0, 11/11 passed, 3 skipped. (Ran against the CLONE's Ofer scenario, not our
tokenized one — fine for STRUCTURE; note it shows ghcr wva v0.6.0 + docker.io vllm, our .env tokens
override those live.)

### Deploy shape CONFIRMED
Method = **modelservice** → deploy is **step_09**. Gateway class = **istio**. The **3 skipped steps are
all three step_06 variants** (fma/standalone/kustomize) → **HAZARD #2 (fma ClusterRole) & #3 (kustomize
router) DO NOT FIRE** for this scenario. 

### CRITICAL — the dry-run OVER-reports cluster writes (presence-probes are stubbed)
In dry-run, every `oc get crd`/secret/cm probe returns empty, so steps show install commands a LIVE run
would SKIP. Verified in code: step_02 `_install_gateway_api_crds` (L248), `_install_gateway_api_extension_crds`
(L291), `_install_gateway_provider` istio (L338) ALL early-return "already installed" when the CRDs are
present. pokprod HAS these (verified earlier: gateways/httproutes/inferencepools + istio? TBD) → on a LIVE
run step_02's CRD+istio installs NO-OP. So the dry-run is a worst-case view, not live behavior.

### Genuinely-UNCONDITIONAL shared/cluster writes (NOT dry-run artifacts — confirmed in code)
1. **step_03 `_apply_monitoring` (L65-66, UNCONDITIONAL on OCP+modelservice)** — `oc apply -f
   03_cluster-monitoring-config.yaml` = ConfigMap `cluster-monitoring-config` in **openshift-monitoring**
   with `config.yaml: 'enableUserWorkload: true'`. NO "already-enabled?" gate. `oc apply` replaces the
   `config.yaml` key value → if pokprod admins put retention/storage/alertmanager settings in that same
   key, this **CLOBBERS them**. ⚠️ SCARIEST WRITE. Must skip/neutralize.
2. **step_03 thanos-querier ClusterRole apply** (wva.py L329, inside install_prometheus_adapter, OUTSIDE
   the PA-reuse if/else → fires whenever CA cert extractable; Dean=admin → fires live). Cluster-scoped
   `oc apply`. (Not shown in dry-run — CA extraction stubbed → PA path skipped in dry-run only.)
3. **step_02 SCC bindings** — `oc adm policy add-scc-to-user anyuid|privileged -z inference-perf-runner
   -n dhl-wva-209` (modifies cluster-scoped SCC user lists) + `oc apply 05_namespace_sa_rbac_secret` +
   helm repo-adds (local). step_02 is SKIPPED via --step anyway; SCCs are a run-phase/load-pod concern.
4. **step_07 gateway-provider re-apply** — `helmfile apply 09_helmfile-gateway-provider.yaml` installs
   **istio-base + istiod into istio-system** (Istio control plane, v1.29.2, cluster-wide) — applied in
   BOTH step_02 AND step_07. On pokprod (shared istio present) helmfile apply would reconcile/possibly
   version-bump the SHARED control plane. ⚠️ Router control plane = Dean "do not touch". step_07 ALSO
   does the namespace-scoped `infra-llmdbench` gateway release (our NS) which we DO need.

### Everything else is namespace-scoped to dhl-wva-209 ✓
step_04 (model ns/PVC), step_05 (harness ns/PVC), step_09 (modelservice helm + Gateway + OpenShift Route,
all `--namespace dhl-wva-209`), the WVA controller helm install + 23_wva-namespace label (our NS).

### REVISED plan — step-selection is NOT enough; needed writes are BUNDLED with shared writes
- **SKIP step_02 + step_08** via `--step` (CRD/istio installs no-op live anyway; GAIE=router).
- **PATCH our fork (Dean OK'd)**: step_03 → skip `_apply_monitoring` (reuse existing UWM) + skip the
  thanos ClusterRole apply (reuse existing); KEEP WVA install + ns label. step_07 → skip the
  gateway-provider helmfile (reuse existing istio); KEEP the namespace `infra-llmdbench` gateway.
- Provisional live step list: **03(patched), 04, 05, 07(patched), 09** (+00 benign). NEVER teardown.
- Public-code make-target path: needs config toggles OR the same skips upstreamed (Dean: depends on
  Ofer's work landing) — our fork patch is the testing safety net now.

### Cluster no-op verifications still needed (read-only; classifier was flaky mid-session)
(a) pokprod has istio CRDs + shared istiod in istio-system? (b) current content of
cm/cluster-monitoring-config in openshift-monitoring — is UWM already enabled & does config.yaml hold
other settings (clobber test)? (c) does pokprod use istio (vs kgateway/agentgateway) for its gateways —
i.e. is our scenario's gateway.className=istio correct? (d) does the thanos ClusterRole / SCC already
include what we'd apply? These confirm the public-code path is a no-op; the fork patch covers us regardless.

## Cluster no-op verifications DONE + fork patches APPLIED (2026-07-30, read-only checks + fork-only edits)

### Read-only pokprod checks (all confirmed — the public-code path is a no-op)
- (a) **istio present:** istio CRDs registered; **istiod Running 1/1** in `istio-system` (72d); gatewayclass
  **`istio` Accepted** (also agentgateway/kgateway present) → scenario `gateway.className=istio` is VALID on
  pokprod, and step_02/step_07's istio installs are no-ops on a live run.
- (b) **cluster-monitoring-config:** existing `data.config.yaml` is EXACTLY `enableUserWorkload: true`
  (no other keys) → the rendered file is identical → step_03 `_apply_monitoring` apply = **NO-OP, no clobber**.
  UWM namespace `openshift-user-workload-monitoring` present (enabled 240d).
- (c) gateway provider = istio (see (a)); our scenario matches the cluster.
- (d) **thanos ClusterRole** `allow-thanos-querier-api-access` already exists (99d, NOT helm-owned) →
  step_03's `22_prometheus-rbac` apply = reconcile no-op.
- **ONE genuine live hazard:** step_07 re-applies `09_helmfile-gateway-provider` (istio-base+istiod v1.29.2)
  with **NO presence gate** (unlike step_02) → a live run WOULD `helm upgrade --install` onto the shared
  72d istiod (unknown version) → possible adopt/version-bump. This is why the step_07 patch is ESSENTIAL,
  not merely belt-and-suspenders.

### Fork patches APPLIED (Dean OK'd "ok on both"; fork-only, uncommitted, no cluster contact, no push)
Design = fail-safe "skip only if already present", mirroring step_02's `_any_crds_missing` gate — an
upstreamable improvement (safe on ANY cluster; installs when absent, reuses when present), not a private flag.
Three files in the gitignored clone `benchmark/llm-d-benchmark/`:
1. **`llmdbenchmark/standup/steps/step_07_deploy_setup.py`** — added `_PROVIDER_PROBE_CRDS`
   (`{"istio": "gateways.networking.istio.io"}`) + `_gateway_provider_present()`; the gateway-provider
   helmfile apply now runs only when the provider's probe CRD is ABSENT. Namespace `infra-{release}` gateway
   apply unchanged. Unknown providers / dry-run → falls through to the original apply (no behavior change).
2. **`llmdbenchmark/standup/steps/step_03_workload_monitoring.py`** — added `_uwm_enabled()` (probes the
   `openshift-user-workload-monitoring` namespace); `_apply_monitoring` skips the cluster-monitoring-config
   apply when UWM is already enabled, then still runs `_install_wva_if_enabled` (WVA install + ns label) as before.
3. **`llmdbenchmark/standup/wva.py`** — added `_cluster_roles_present()` (parses the rendered
   `22_prometheus-rbac` for `kind: ClusterRole` names, `oc get clusterrole <name> --ignore-not-found`); the
   thanos ClusterRole apply now skips when EVERY declared ClusterRole already exists.
All three helpers return False in dry-run → original behavior preserved for dry-run/render.

### Verified after patching (read-only, no cluster contact)
- `py_compile` on all 3 files OK; importing the step registry OK; `_PROVIDER_PROBE_CRDS` wired.
- Re-ran the full `--dry-run standup` render (`/tmp/wva-dryrun-ws2`) → **exit 0, 11/11 passed, 3 skipped**,
  gateway=istio — identical to the pre-patch render (guards short-circuit in dry-run, as designed).

### Still STOPPED (no cluster mutation, no push)
- No live standup until Dean's explicit go-ahead. Provisional live step list unchanged: **03(patched),
  04, 05, 07(patched), 09** (+00 benign); SKIP **02, 08**; NEVER teardown; all `-p dhl-wva-209`.
- Patches are uncommitted in the gitignored clone (editable install → already active for our runs). If/when
  Dean wants them on origin/wva-ta-benchmark, that's a separate Dean-run push (coder never pushes).

## Phase 3 (cluster) — in progress
- Image confirmed on quay: quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9 = sha256:80da87a4… (pushed 2026-07-28).
  NOTE: predates the 2026-07-29 C/D force-push → built from earlier C/D tips (stale vs current PRs). Fine for harness
  validation per Dean; planner refreshes when C/D land. (CURRENT.md ta-testing row still says "NOT pushed / ce5fac61" — stale bookkeeping, leave for later per Dean.)
- 3a DONE (Dean-approved): `oc new-project dhl-wva-209` — created + context switched. Namespace empty, Active.
- 3b DONE (Dean-approved): `oc delete project dhl-wva` — old 45-day legacy VA+HPA stack fully nuked; project NotFound (terminated
  cleanly, no GPU pods were running). Namespace-scoped delete, no cluster-global impact.
- Cluster context now: dhl-wva-209/api-pokprod001-ete14-res-ibm-com:6443/DEAN@il.ibm.com. All commands still carry explicit -n.
- Every further cluster mutation still gated on Dean's explicit per-action confirmation.

## Branch
benchmark at /home/dean/.../benchmark worktree ; new tip 6505de62
  (6505de62 [this session] on top of 9bd53d7b [#1435 KEDA harness adoption] on top of the fresh 11d70a8a base)
archive/benchmark-ta3-legacy tag -> 892e1efa (VA+HPA legacy runbook + notes; recovery handle)

## This session — Phase 2 §5 (parametrize + runbook)
Commit 6505de62 (DCO signed): "benchmark(two-variant): parametrize env-specific values via .env; add pokprod KEDA runbook"
10 files, +586/-56. Tier B only, fork-only, no cluster contact.

### What was done
- hack/benchmark/.env.sample (NEW) — every §5.2 env-specific var, NO live defaults for env-specific keys.
- .gitignore — hack/benchmark/.env ignored.
- Makefile — `-include hack/benchmark/.env` BEFORE the `?=` defaults (.env wins; CLI still wins over .env);
  token-`sed` __VAR__ → .env value into the copied scenario at benchmark-standup AND benchmark-run,
  each with a residual-`__TOKEN__` guard that aborts + lists any unset var; benchmark-add-variant now
  requires ACCELERATOR_NAME/PRIMARY_COST/PRIMARY_MIN/PRIMARY_MAX and passes them + --prometheus-url.
- scenarios/guides/{two-variant-wva,wva-sat2-tp1}.yaml — tokenized image/chart/model/workdir/release.
- add_variant.py — --prometheus-url now required; added required --accelerator-name/--primary-cost/
  --primary-min/--primary-max; removed hardcoded NVIDIA-H100 / cost 10 / min 1 / max 10.
- post_run_analyze.sh — dropped hardcoded `biran` default namespace (now requires BENCHMARK_NAMESPACE
  or arg 2); genericized biran-* comment examples. plot_two_variant_pipeline.py + .j2 — biran/model
  literal comments genericized.  [NOTE: these 3 files are beyond the §5.2 table — small comment/default
  cleanups to satisfy §5.6; flagged to Dean below.]
- docs/two-variant-wva-pokprod-runbook.md (NEW) — Tier-B KEDA runbook ported from the archived VA+HPA
  runbook (§1 env / §2 host tools / §3 CLI / §4 .env / §5 Tier-A image / §6 standup / §7 add-variant /
  §8 enable-v2 / §9 verify TA / §10 load+signals / §11 troubleshooting / §12 compat / §13 fallback /
  §14 teardown). Reframed to `make benchmark-*` + .env; dropped :ta3-build/chart-0.6.0/manual-relabel/
  historical-findings.

### Verified (Step 5, no cluster contact)
- py_compile add_variant.py + plot_two_variant_pipeline.py OK; bash -n post_run_analyze.sh OK.
- make -n parses benchmark-standup / benchmark-run / benchmark-add-variant.
- Token-render simulation on BOTH guides with .env.sample values → residual __TOKEN__ = 0, valid YAML,
  correct image/chart/model render.
- §5.6 residual-hardcode grep: harness deploy files CLEAN; `\bbiran\b` fully gone from hack/ test/.
  Remaining grep hits are ALL out-of-scope pre-existing prose/fixtures (NOT env config, NOT harness):
  docs/developer-guide/prometheus.md (JSON output samples), docs/benchmark.md + benchmark-guide.md
  (prose), hack/vllm-benchmark-deployment.yaml:7 (generic <model-id> example comment),
  test/utils/unitutils.go:169 (Go test arg). Plus docs/developer-guide/two-variant-wva-benchmark.md
  (#1435's dev-guide — prose; reworked separately if Dean wants). Left untouched — scope call, see below.

## Decisions carried in (Dean, prior session) — reflected in the commit
- vllm registry: VLLM_IMAGE_REPO parametrized, docker.io default kept  (AGENTS.md docker.io conflict — FLAGGED, not resolved).
- chart: WVA_CHART_VERSION=0.8.0-rc5 (Ofer's) + our WVA_IMAGE_TAG=ta-0.9  (compat risk documented in runbook §12).
- prom url: existing Makefile default kept; .env overrides via being -include'd before the ?=.

## Reclone
Embedded gitignored llm-d-benchmark/ clone present and on Ofer's origin biranofer/llm-d-benchmark.git
@ feat/multi-variant-benchmark (tip 6d5ff6b) — reclone effectively current; not committed (gitignored).

## Not done (STOPPED — Dean's / later phases)
- No push (commit 6505de62 → origin/benchmark) — awaiting Dean's explicit OK. Fork only, never upstream.
- Phase 3 (clean stale pokprod) + live standup / any oc apply — cluster-side, Dean/Ofer, separate.
- Tier-A :ta-0.9 image build/push — deferred (Dean); stays a .env var.

## For Dean (review points)
1. §5.6 grep scope: I read it as "harness deploy files → zero"; the doc-prose/Go-test hits are legit
   examples left as-is. Confirm, or say if you want the docs/test scrubbed too.
2. 3 files touched beyond the §5.2 table (post_run_analyze.sh default + plot/.j2 comments) — OK?
3. Runbook filename: chose docs/two-variant-wva-pokprod-runbook.md (KEDA/ta-0.9 reality) instead of
   reusing the stale "ta3" name. Rename if you prefer.
4. AGENTS.md forbids docker.io in e2e; VLLM_IMAGE_REPO defaults to docker.io/vllm/vllm-openai per your
   call — reconcile the doc vs the default when convenient.

## Phase 0 (prior session, 2026-07-28) — resolved
Fresh benchmark created off main; old branch renamed benchmark-ta3-legacy (tip 892e1efa, docs-only,
results discarded per Dean); archive/benchmark-ta3-legacy tag -> 892e1efa. #1435 KEDA harness later
adopted (9bd53d7b). Local untracked reference-legacy/ (56K) retained: profiles/*.yaml.in,
two-variant-wva.patched.yaml, benchmark-settings.env, benchmark-s1-manual-run.md, README.md.
