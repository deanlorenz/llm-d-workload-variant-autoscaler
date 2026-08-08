# Status — `benchmark` branch (ta-benchmark coder/runner)

**Written in the benchmark worktree, untracked**, because this session is harness-isolated and
cannot write to `plans/session/status/`. Dean's direction 2026-08-07: *"generate your status,
steps, etc. in your own tree. I will inform the planner and it can fetch/copy these files to the
right places."* Target path when relocated: `plans/session/status/benchmark.md`.

Last session: 2026-08-07. **No cluster run has been performed.** Everything below is either a
local code change or a read-only cluster verification, except one write that Dean explicitly
asked for (freeing the GPUs — see §5).

---

## 0. Cold resume — read these four first

1. **Role:** ta-benchmark coder/runner, confined to the `benchmark` worktree
   (`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark`). Write scope = this worktree
   only. Never `cd` to a sibling. Never push to the `ofer` remote (its push URL is deliberately
   `READ-ONLY-MIRROR-DO-NOT-PUSH-TO-OFER`); `origin` on the clone is
   `git@github.com:deanlorenz/llm-d-benchmark.git`.
2. **Standing constraint: no run starts without Dean's explicit approval**, and no `git push` without
   a per-push confirmation for that specific push. Always pass an explicit `-n <namespace>`, including
   for cluster-scoped reads. Namespace is `dhl-wva-209`.
3. **Two things must happen before any arm, in this order** and neither has been done:
   free PVC space (§11.5 — the gate exits 1 today) and un-pause the ScaledObject (§5 — still `0`).
4. **Uncommitted work exists in two repos.** This worktree: 4 new `hack/benchmark/` scripts + a
   `Makefile` target, and 2 unpushed commits. The `llm-d-benchmark` clone: a modified
   `output_token_correction.py`. See §6.

---

## 1. Scope of this round

Goal (Dean, 2026-08-07): re-run the pokprod standup — which helm-upgrades the WVA controller onto
`ta-0.9-anchor-20260806`, making it a **regression check of the anchor refactor** — then repeat the
08-03 single-variant staircase with TA on (Arm A), then an identical arm with TA off (Arm B) to
confirm the system still functions.

Standing constraint: **no run starts without Dean's explicit approval.**

---

## 2. Correctness fix: the vLLM pin was inert

The scenario pinned `images.vllmOpenai`, which **no template reads** — upstream's own docs call it
"Not currently used by any template (reserved)" (`llm-d-benchmark/config/README.md:1339`). The
load-bearing key is `images.vllm`, read at `config/templates/jinja/13_ms-values.yaml.j2:382`
(decode) and `:785` (prefill). So every deploy since this scenario was written silently fell
through to `llm-d-benchmark/config/templates/values/defaults.yaml:104`,
`vllm-openai_version: v0.20.2`.

**Confirmed live, not inferred:** the currently-deployed decode runs
`docker.io/vllm/vllm-openai:v0.20.2`.

Fixed in `hack/benchmark/scenarios/guides/wva-sat2-tp1.yaml` — both keys are now set, so the pin
survives if a future template switches keys. Merge path verified end to end:
`render_plans.py:1167` deep-merges `shared:` over `defaults.yaml`, and
`version_resolver.py::_resolve_image_tags` only rewrites tags equal to the literal `"auto"`, so
`v0.25.0` passes through untouched.

`VLLM_IMAGE_TAG` stays **v0.25.0**, not v0.25.1 (2026-07-13) or v0.26.0 (2026-07-25): `.env`'s own
comment documents this pin as matching what the llm-d guides pin. Matching the guides is the
intent; chasing the newest tag is not.

**Why the pin exists at all** — WVA Sat-2 needs `vllm:cache_config_info` for real KV capacity.
Verified against the actual v0.25.0 source: `CacheConfig.metrics_info()` is
`{key: str(value) for key, value in self.__dict__.items()}` — no filter list, so both
`num_gpu_blocks` and `block_size` are emitted. (Note `compute_hash` *does* exclude
`num_gpu_blocks`; `metrics_info` does not — that was the thing worth checking.)
**Caveat for the post-standup assertion:** `num_gpu_blocks` is declared `init=False, default=None`
and is populated only after profiling, so it stringifies to `"None"` until then. Assert on the
*value*, not merely on the series existing.

### Open decision for Dean
`hack/benchmark/scenarios/guides/two-variant-wva.yaml` has the **same latent bug**. Left unfixed
deliberately: fixing it silently changes which vLLM image a future two-variant run gets, and that
is Dean's call, not a drive-by.

---

## 3. The clone is no longer reset out from under us

Upstream's standup forced the `llm-d-benchmark` clone back to origin in two places
(`git checkout -- config/{scenarios,specification,templates}` and `git reset --hard
origin/<ref>`). For us that clone is a checkout of **our fork**, carrying the shared-cluster
safety patches plus unpushed local work — so a blind reset both destroys local commits and can
silently run the standup with the guards missing.

Both destructive steps are gone. `benchmark-standup` now:
- **hard-fails** if the clone's branch != `BENCHMARK_REPO_REF` (refuses to switch branches itself,
  since that changes which code runs against the cluster);
- otherwise **fetches and reports only** — branch, short SHA, ahead/behind, dirty count — and
  continues;
- force-syncs only under the explicit opt-in `BENCHMARK_CLONE_FORCE_SYNC=true` (default `false`).

---

## 4. Three-level safety net, and the gate that was missing

- **L1** operator discipline — explicit `-n <ns>` on every call, read-only until approved.
- **L2** this repo's Makefile/scripts — namespace required, step_02 excluded, clone never
  force-synced.
- **L3** our llm-d-benchmark fork — presence-gates every cluster-scoped operation the upstream
  standup would perform.

**The structural weakness:** every L3 gate is a *presence* gate. It skips the dangerous operation
**because the shared object already exists**. That is fail-safe while the object is there and
fail-**dangerous** the moment it is not, because absence reads as *"not installed yet, go install
it."* Nothing asserted those preconditions before a run.

Worst case, concretely: our clone skips installing prometheus-adapter only because the
cluster-scoped ClusterRole `prometheus-adapter-resource-reader` exists — and on pokprod that is a
hand-made stub with no real helm release behind it. Delete the stub and the standup performs a
genuine `helm install prometheus-adapter`, which registers
`v1beta1.external.metrics.k8s.io`. That APIService is a cluster-wide singleton **currently owned by
KEDA** (`openshift-keda/keda-metrics-apiserver`, keda-operator 2.19.0), so taking it over would
break every KEDA-driven autoscaler on pokprod — other tenants' included.

### New: `hack/benchmark/preflight_shared_cluster.py` + `make benchmark-preflight`
Read-only, no writes. Turns "silently take the destructive path" into "refuse to start". Wired so
`benchmark-standup-shared` runs it **first** and aborts the standup on any gating failure. Not
wired into the generic `benchmark-standup`, which may legitimately run against kind/non-OpenShift
clusters where these preconditions don't hold.

Checks: target namespace; UWM namespace (step_03 gate); istio CRD (step_07 gate);
prometheus-adapter stub **with both helm annotations readable**, not mere existence, because the
gate reads the annotations; thanos-querier ClusterRole; external-metrics APIService ownership; both
SCC `.users` lists clean of our service accounts; fork clone branch; all four L3 guard symbols
present in the source that will execute; and that step_09 still grants SCCs with the
namespace-scoped `-z SA -n NS` form.

**Validated both directions:**
- live: **14 gating PASS, 1 WARN, exit 0**
- negative, against a synthetic `/tmp/fake-fork`: **6 FAIL, exit 1** — correctly reporting
  `cluster-wide form -- would append our SA to the shared SCC's .users list` and all four missing
  guards. Fixture removed.
- bogus namespace: FAIL, exit 1.

The one WARN is real and still open: the fork clone is **ahead 1 commit with 9 modified/untracked
paths**, so this run would not be reproducible from origin alone. See §6.

### L2 gaps found and closed
1. `kubectl get crd scaledobjects.keda.sh` was the last read missing `-n` — added.
2. `benchmark-standup-shared` didn't forward `BENCHMARK_NAMESPACE` to the sub-make — now explicit.
3. The `BENCHMARK_SKIP_PROMETHEUS_ADAPTER` block did unconditional `annotate --overwrite` /
   `label --overwrite` on that shared cluster-scoped ClusterRole. Now presence-aware: writes
   nothing when the stub is already ours; **hard-fails rather than re-annotating** if it is
   helm-owned by another release (which would hijack helm ownership of another tenant's object);
   creates it only when genuinely absent. Two deliberate behaviour changes: `--overwrite` dropped
   from both calls, and `create`'s `2>/dev/null || true` became `|| exit 1` — a swallowed create
   failure used to leave us believing the gate would fire when it would not, the fail-dangerous
   direction.

Verified: `make -n` expands cleanly, `bash -n` passes, and the jsonpath resolves live to
`workload-variant-autoscaler-monitoring` — equal to `WVA_MONITORING_NAMESPACE`, so on pokprod the
block takes the leave-untouched path and writes nothing.

### `BENCHMARK_SKIP_PROMETHEUS_ADAPTER` promoted into `.env`
Dean asked why it wasn't there. It had exactly **two** references in the whole repo: the Makefile
block, and a command-line incantation in the `wva-sat2-tp1.yaml` header comment. No `?=` default,
absent from `.env` **and** `.env.sample` — so when `.env` was filled from the sample on 2026-07-30
there was nothing to fill in, and the flag has been dormant ever since. The precondition guarding
the worst-case install was held by nothing but the stub happening to still exist.

Now `BENCHMARK_SKIP_PROMETHEUS_ADAPTER=true` in both `.env` and `.env.sample`. Defaulting it true
is only safe *because* of the presence-aware rewrite above — before that, true meant an
unconditional overwrite of a shared cluster-scoped object on every standup, which is plausibly why
it was left out.

**Ordering caveat, stated honestly:** under `benchmark-standup-shared` the preflight runs first and
FAILs on a missing stub, so the flag can never *self-heal* one on pokprod — the standup won't get
that far. That is the intended behaviour (a vanished stub means something changed cluster-wide and
a human should look at why before we recreate an object claiming helm ownership). The flag does
real work on a fresh namespace or via plain `make benchmark-standup`, where preflight isn't in the
path.

---

## 5. Cluster state as left tonight — GPUs freed

Dean, 2026-08-07: *"I am going to sleep. make sure you free up the GPUs on the cluster."*

Exactly one GPU was held: `unsloth--608e585a-instruct-decode-5b4d6bcb88-ss7sh`, 1× H100 on node
`pokprod-b93r44s0`. `gpu-reservation` was already at 0 desired with no pods.

Freed by **pausing KEDA at zero** rather than deleting anything:

```
kubectl annotate scaledobject unsloth--608e585a-instruct-decode-scaler -n dhl-wva-209 \
  autoscaling.keda.sh/paused-replicas="0" --overwrite
```

`autoscaling.keda.sh/paused-replicas` is the documented KEDA annotation (verified against the KEDA
2.19 scaling-deployments docs): it scales the workload to the given count, then halts autoscaling.
Scaling the Deployment directly would not have worked — the ScaledObject has `minReplicas: 1`, so
KEDA would have restored it within seconds.

Verified after: decode Deployment `spec.replicas=0`, and **no GPU-requesting pods remain** in
`dhl-wva-209`.

> **⚠️ Un-pause is a required first step of the next run.** Remove the annotation:
> `kubectl annotate scaledobject unsloth--608e585a-instruct-decode-scaler -n dhl-wva-209 \`
> `autoscaling.keda.sh/paused-replicas- ` — the deployment will not scale at all while it is set,
> and a staircase run against a paused ScaledObject would silently produce a flat 0-replica trace.

Everything else was left running (all CPU-only): istio gateway, gaie-epp, the WVA controller, the
harness-data PVC pod.

### The controller currently deployed is NOT the anchor image
Live: `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9`.
`.env` pins `WVA_IMAGE_TAG=ta-0.9-anchor-20260806`.

So the anchor refactor is **not yet on the cluster** — the standup is what puts it there, and that
is precisely what makes this round a regression check. Do not read the currently-healthy
controller as evidence about the anchor build.

Also live: ScaledObject min 1 / max 2 (age 7d4h), KEDA-generated HPA
`wva-keda-hpa-unsloth--608e585a-instruct-decode` (age 3d23h), and a deprecation warning on every
`get` — `VariantAutoscaling is deprecated ... migrate to the annotation-based path
(llm-d.ai/managed=true)`. Worth a planner decision, not a runner one.

---

## 6. Blocked on Dean

1. ~~Push the fork.~~ **DONE** — `cfe6088..7a1b478 wva-ta-benchmark` pushed. The preflight WARN
   now reads *ahead 0*; its remaining 7 dirty paths are all regenerable cache (see §9).
2. **Push the WVA branch.** `d5f753c9` is now on origin; **ahead 2** — `c3c5aa20` (workload profiles
   in-repo, harness from spec, `--analyze`) and `361cfe77` (image recording + harness pin). Clean
   fast-forward, 0 behind, awaiting a per-push confirmation.
   Not yet committed at all: the four `hack/benchmark/` data-pipeline scripts and the
   `benchmark-reset-run` Makefile target (§11–§12), and `session-notes/` (untracked by design).
3. **Push the fork again.** `llmdbenchmark/analysis/output_token_correction.py` is **modified and
   uncommitted** in the clone (sidecar fallback, §11.3). Tested 9/9 but not committed or pushed.
4. **`uv.lock` in the fork** — deliberately not committed; Dean's call whether it should be.
5. **`two-variant-wva.yaml`** — same inert-image bug, §2. Flagged, not edited.
6. **Approval for the run plan itself** (§7). Nothing starts without it.

---

## 7. Run plan, pending approval

Not yet executed. Sequence, with the gates that must pass between steps:

**-2. ~~The results PVC BLOCKS a run.~~ CLEARED 2026-08-07** by `harvest_run.py --apply` (§14):
   11.0 GB reclaimed, 8.8 GB → **19.8 GB available vs 9.6 GB required, exit 0**. Note the estimate
   is still 7.1 GB even though both per-request files are gone — it now comes from the sidecar's
   recorded `bytes_scanned`, which is the one mechanism a reclaim could have broken and did not.
**-1. `python3 hack/benchmark/reset_run.py -n dhl-wva-209 --workspace . --apply`** — still never run
   with `--apply`; needs Dean's go-ahead. Does **not** un-pause KEDA (deliberately).
   **Dry run verified 2026-08-07** and the PVC deletes it plans are now genuinely safe — but only
   after fixing a gap it would have made permanent; see §14.2. Its controller restart is redundant
   with the standup's helm upgrade, so ordering it before step 2 costs one extra rollout.
0. `make benchmark-preflight` — must be 0 FAIL. **Verified 2026-08-07: 15 ok, 0 FAIL, 1 warn**
   (fork clone dirty — §14.4).
1. Un-pause the ScaledObject (§5) — otherwise every arm traces flat at 0.
   **Still paused at 0 as of 2026-08-07**, re-verified:
   `kubectl -n dhl-wva-209 get scaledobject unsloth--608e585a-instruct-decode-scaler
   -o jsonpath='{.metadata.annotations.autoscaling\.keda\.sh/paused-replicas}'` → `0`.
2. `make benchmark-standup-shared BENCHMARK_NAMESPACE=dhl-wva-209
   BENCHMARK_SPEC=guides/wva-sat2-tp1` (steps 0,3,4,5,7,8,9 — only step_02's admin CRDs/SCCs
   excluded).
3. **Gate:** controller reports image `ta-0.9-anchor-20260806` and reconciles without error.
   `make benchmark-record-images` now answers the image half of this mechanically (read-only,
   always exits 0). As of 2026-08-07 it reports `wva-controller ... :ta-0.9 [differs]` — the
   standup is what closes that.
4. **Gate:** decode pod runs `vllm-openai:v0.20.2`, and Prometheus has `vllm:cache_config_info`
   with `num_gpu_blocks` set to a real number (not `"None"`, per §2).
   Note the pin was **held at v0.20.2 on 2026-08-07** (was v0.25.0): the pin only became
   load-bearing on 08-06, so letting it take effect now would change vLLM *and* the controller
   image in the same run and leave any throughput delta unattributable — besides a ~10GB pull.
   Dean's framing: pins are minimum versions, not a cross-run comparison device; what matters is
   that the run records actual versions, which §10 now does.
5. Re-assert the analyzer set — `make benchmark-set-analyzers WVA_ANALYZERS=saturation,throughput`
   (edits only the `analyzers:` block, unlike `benchmark-enable-v2-saturation`, which rewrites the
   whole payload including thresholds and so cannot be used for an A/B arm switch).
6. Verify/recreate the ScaledObject via `make benchmark-configure-variants
   VARIANT_CONFIG=hack/benchmark/scenarios/guides/variants/sat2-tp1.yaml`.
7. Re-arm GPU pre-reservation + decode-coupler (`gpu-reservation-coupler.sh`, `HOLD_TOTAL=2`).
   `MAX_ITERS=560` ≈ 47 min and **will likely need extending per arm**; stop via
   `touch /tmp/stop-gpu-coupler`.
8. **Arm A (TA on)** — staircase 5→12→5 RPS, `-l inference-perf`, `--monitoring
   --wait-timeout 2400`.
9. Cool down to 1 replica, then **Arm B** — identical, `WVA_ANALYZERS=saturation`.

Open question carried from 08-03, for the planner: that run suggested adding a ~8 RPS step and
raising `maxReplicas` (currently 2, which caps the staircase's headroom).

---

## 8. Also open

Stale trigger `benchmark__observability-plan.md` still needs a keep-or-supersede call.

Upstream issues for the re-tokenization bug and the step_09 truncation are **captured but not
filed** — see §13.

The three profiles now in `hack/benchmark/workloads/` are **duplicated** on the fork branch
(committed at `cfe6088`). Removing them there is a delete on a pushed branch — proposing, not
doing.

`BENCHMARK_CLONE_FORCE_SYNC` could now default to `true`, since no load-bearing input lives only
in the clone (§9). Holding off only because a force-sync would also wipe `uv.lock`, which is
itself an open question (§6.3).

---

## 9. Workload profiles now live in this repo (commit `c3c5aa20`)

**The hole:** the 08-03 staircase ran a profile that existed *only* in the llm-d-benchmark clone's
working tree, placed there by hand. The Makefile's `BENCHMARK_WORKLOAD` copy block never fired —
`head -20 ta-staircase-run.log` shows the run passed no `-w` at all. The scenario names the profile
via `harness.experimentProfile` and llmdbenchmark resolves it from the clone. A fresh checkout could
not reproduce that run.

**Closed by** `hack/benchmark/workloads/<harness>/` (source of truth) plus
`hack/benchmark/sync_workloads.py`, called from `benchmark-run` after the scenario copy. It copies
our `*.yaml.in` templates in, then asserts the named profile is either one we synced or **tracked**
in the clone's index — an untracked clone-only profile is a hard failure naming the path and where
to move it, because that is exactly the 08-03 state.

Two subtleties worth keeping:

- **step_05 prefers `<name>.yaml` over `<name>.yaml.in`.** A stale rendered sibling from an earlier
  run silently shadows an edited template. The sync removes an untracked one (verified live) and
  warns rather than deleting a tracked one.
- **The harness is now derived from the scenario**, not hardcoded. `BENCHMARK_HARNESS` defaulted to
  `guidellm`, and it becomes llmdbenchmark's `-l`, which *overrides* `harness.name` — so the
  Makefile was silently overriding the spec. Per Dean: *"harness is tied to a specific test … just
  an input to the spec of each run."* Precedence via `$(origin)`: command line > `.env` > scenario >
  llmdbenchmark's own default. The sync hard-fails if `-l` and `harness.name` disagree.

**Also fixed: analysis never ran.** `benchmark-run` passed neither `--analyze` nor
`LLMDBENCH_RUN_EXPERIMENT_ANALYZE_LOCALLY=1`, and step_12 is OFF by default — so the Benchmark
Report v0.2 YAMLs only ever came from a manual pass (08-03 run ended 06:00; reports stamped 07:26).
`BENCHMARK_ANALYZE ?= true` now, plus `make benchmark-analyze` for older results (idempotent).
step_12 is **host-side** (`run_analysis` over the results copied back by step_07), which is why none
of this needs a change to `ghcr.io/llm-d/llm-d-benchmark:v0.6.7`, an image we do not control.

---

## 10. Runs now record actual images (commit `361cfe77`)

**The hole:** a run could not say what it ran on. `plan/*/helm/modelservice.yaml` holds the
*rendered* (desired) images; `environment/context.ctx` is just the kubeconfig; and the **WVA
controller image — the subject of the whole benchmark — appeared nowhere in the 08-03 artifacts**,
because our Makefile deploys the controller, not llmdbenchmark. 08-03's results cannot be attributed
to a controller build after the fact.

`hack/benchmark/record_images.py` observes the live namespace and writes
`<run-dir>/environment/images.yaml`, capturing `spec.image` **and** the kubelet's resolved
`status.image`/`imageID` — a floating tag makes those disagree and the digest is the only durable
identity. Explicit `-n` on every kubectl, read-only, per `preflight_shared_cluster.py`'s convention.

Design points:

- **Observed before load is applied.** That is the honest answer to "what did this run run on", and
  unlike a post-run reading it does not depend on pods surviving (harness pod deleted, decode scales
  down). Staged to `.images-pending.yaml`, filed once the run completes — and it **refuses to
  overwrite an existing record**, so a run that creates no directory of its own (a dry run, where
  `ls -td` would return the *previous* run) cannot clobber an earlier run's.
- **Flags, never gates** (Dean, 2026-08-07: *"do not refuse run on EPP or vLLM images — raise a flag
  but run"*). Comparison is `actual >= pin` since pins are minimums; build-label tags (the
  controller's) are compared for inequality only and said to be such. EPP is deliberately unpinned
  and reports as `unpinned`.
- The harness image is checkable even between runs: `downloader` and `rsync` run the same
  `images.benchmark` image and persist, so the pin is verified without a harness pod present.

**Harness image pinned** via `HARNESS_IMAGE_REPO`/`TAG` → scenario `images.benchmark`. The existing
unsubstituted-`__PLACEHOLDER__` guard makes the pin mandatory for free.

⚠️ **Correction for the record:** the harness image pin does **not** force our fork onto the
cluster. Verified mechanism: the fork arrives via `BENCHMARK_REPO_REF`, which supplies both the
host-side code and the `llmdbench-harness-scripts` ConfigMap built from the clone's
`workload/harnesses/` (`step_06_create_profile_configmap.py:143`). The image only carries baked-in
inference-perf and its deps. This matters because if the image pin were believed to cover it,
dropping the clone-ref check later would silently remove every L3 safety gate. The pin is still
needed — our output-token correction is written against a specific in-pod inference-perf behaviour.

**Output-token inflation, quantified.** The correction annotation on the 08-03 reports gives
`true_output_len_mean: 512.1002651849981` vs `reported_output_len_mean: 905.481` → **global inflation
factor 1.7714** (per-stage 1.7682 / 1.7815 / 1.7645 — 1.7682 is stage 1, not the run). Output token
rate and total token rate are ~77% HIGH; TPOT, ITL and normalized TPOT are ~77% LOW (inflated
denominator). Both directions flatter the system under test. `postprocess.py` reads `results.json` /
`replica_status_timeseries.json` / `pod_startup_times.json`, not the v0.2 reports, so there is no
ordering dependency between `benchmark-analyze` and `benchmark-report`.

---

## 11. Results data pipeline — design C (2026-08-07, NOT yet wired into the Makefile)

Dean's direction: *"Part of the standard benchmark run is to fetch results to local machine -- we
still do it, but we don't fetch the multi GB file. Instead we run the viz fetch script and fetch its
results… BEFORE running a new benchmark, always make sure PVC has enough space with margin. Delete
the per-replica multi GB data for prior benchmarks we ran. can optionally keep the local disk copy
for 14 days."* Then: *"C is good. The correction can't run afterwards on the fetched results? seems
easier to run there."* → yes, and it now does.

Four new **untracked** scripts in `hack/benchmark/`. All are dry-run by default and require
`--apply` to mutate anything; all carry explicit `-n <namespace>` on every kubectl call.

### 11.1 `completion_tokens_scan.py`
Streams the multi-GB per-request file **inside the pod** and emits a ~31 KB
`server_completion_tokens.json` holding the `completion_tokens` vector plus `bytes_scanned` (the size
of the file it read). Invoked as `kubectl exec -i <pod> -- python3 - <args> < script.py`, so nothing
is ever written into the pod. Pod verified: **GNU tar 1.34, python3 3.12.9**.

`bytes_scanned` turned out to be the load-bearing field for two other purposes: it is the durable
**size history** for the gate's estimate after the file it measured is gone, and it is the
**provenance check** proving a vector came from the whole file rather than a partial copy.

### 11.2 `harvest_run.py` — replaces step_09 for the large file
**The stage order IS the safety property: scan pod-side → fetch → VERIFY → only then delete.**
Fetch uses tar-over-exec with `--exclude` (`kubectl cp` has no `--exclude`, and it *is* tar-over-exec
underneath). Discovers the data pod by label **`role=llm-d-benchmark-data-access`** (what step_09
itself uses), container `rsync`, results at `/requests`. Matches experiment dirs to run dirs by the
epoch embedded in `<harness>-<epoch>-<rand>_<n>` vs `<user>-<YYYYmmdd>-<HHMMSS>-<ms>`.
`--fetch-per-request` opts INTO moving the gigabytes; default is not to.

### 11.3 Fork: `output_token_correction.py` prefers the sidecar
Modified in the clone, **uncommitted**. Prefers `server_completion_tokens.json` → falls back to the
raw per-request file → distinguishes "no usage data at all" (`None`, not an error) from "sidecar
refused with no fallback" (error string). Records `extracted_from` provenance in the marker block and
`reports_request_total` in the audit. Refuses a vector with MORE values than the reports' request
total ("not this run") or under 90% ("truncated"); accepts slightly fewer, since a request can
legitimately lack server usage.

**Validated 9/9** by `/tmp/test_sidecar.py` (ephemeral — recreate from the transcript if needed). The
decisive result: the sidecar path and the raw-file path produce **identical** per-stage inflation
1.7682 / 1.7815 / 1.7645, mean 1.7714 — the 31 KB vector exactly reproduces the 4.2 GB scan.
Audit `n_requests = 7919`, `reports_request_total = 7920`.

Fixture trap worth remembering: the shipped v0.2 reports were corrected **in place**, so a
de-markered copy still carries the true means and reports inflation 1.0 — passing the test while
exercising nothing. Fixtures must be regenerated from the native stage JSON, choosing the converter
the way production does (`_is_session_lifecycle_file` → `import_inference_perf_session` emits
`session_performance`, not `request_performance`).

### 11.4 `pvc_gate.py` — refuse to start a run the PVC cannot hold
The per-request file is written at the **end** of a run, so a full PVC does not fail fast — it fails
after all the GPU time is spent. `df -kP`, never `df -h` (rounding a margin check defeats it).
Estimate = largest prior size on the PVC **or** any host sidecar's `bytes_scanned`, else a
`DEFAULT_PER_REQUEST_GB = 5.0` that is reported *as* a default so an unpinned guess never looks like
a measurement. Default `--margin 2.0` GB.

### ⚠️ A real safety bug I introduced and fixed before any apply
`classify()` and `harvest_run.reclaim()` originally checked only that a host copy **existed**. Chasing
an unrelated size discrepancy in the gate's output surfaced this:

| experiment | PVC bytes | host bytes | |
|---|---|---|---|
| `inference-perf-1785720119-41gfxn_1` | 7,570,490,291 | 3,967,763,968 | **truncated 52.4%** |
| `inference-perf-1785724033-d5lhav_1` | 4,204,290,876 | 4,204,290,876 | exact |

The gate said `FREE` for the truncated one and would have destroyed the only complete copy. **Every
reclaim guard now compares SIZES, not existence**, plus the `bytes_scanned` provenance check. Both
docstrings cite `session-notes/issues/llm-d-benchmark-step09-silent-truncation.md` so the check does
not get "simplified" back into an existence test. Reclaimable dropped from a mis-reported 11.0 GB to
a true 3.9 GB — which is why §7 now blocks.

### 11.5 Current PVC state (verified 2026-08-07, read-only)
```
size 20.0 GB / available 8.8 GB / required 9.6 GB  -> BLOCKED, short 723.8 MB
KEEP 7.1 GB  inference-perf-1785720119-41gfxn_1  local copy TRUNCATED 3.7 of 7.1 GB
FREE 3.9 GB  inference-perf-1785724033-d5lhav_1  server_completion_tokens.json scanned from all 3.9 GB
```

**Ephemeral state made durable (2026-08-07)**, so a cold resume is not missing evidence:
- The scanned vector was moved out of `/tmp` and filed where production expects it:
  `dean-20260803-052634-197/results/inference-perf-1785724033-d5lhav_1/server_completion_tokens.json`.
  Its `bytes_scanned = 4,204,290,876` equals both the PVC and host file sizes exactly, so the gate now
  clears that experiment on **provenance** rather than on the raw copy — re-verified in the block
  above. No behaviour change (it was already FREE by the raw-copy path); the point is that the 31 KB
  vector now survives deletion of the 3.9 GB file.
- `session-notes/scratch/test_sidecar.py` (the 9/9 suite, `VECTOR` repointed at the durable sidecar)
  and `session-notes/scratch/probe_first_record.py` (the ITL-timeline evidence) copied in from `/tmp`.

**The probe experiment `…41gfxn_1` has no vector at all** — it is the 7.1 GB KEEP, and the PVC holds
its only complete copy. Scanning it is the single action that unblocks the run.

**Recommended unblock, in order:** harvest **scan-only** for BOTH experiments (~31 KB each, no
gigabytes moved) → that makes both reclaimable on provenance → reclaim frees **11.0 GB** → available
~19.8 GB. This is strictly better than the status quo for the probe run, whose host copy is missing
48% of its requests while the PVC still holds a complete file.

### ⚠️ 11.5a `harvest_run.py` is NOT yet validated against a live cluster
First real invocation was attempted 2026-08-07 and it **had never worked**. Two bugs, both fixed:

1. **`kubectl()` never captured stdout.** It defaulted `stdout=None` and passed that straight to
   `subprocess.run`, where `None` means *inherit the parent's stdout* — so every read returned `None`
   while printing the answer to the terminal. Fixed: `stdout=None` now explicitly means capture-as-text,
   and a caller passing a file object still gets untouched binary (which the tar and in-pod-scanner
   paths need). `pvc_gate.py` was unaffected — it uses `capture_output=True`.
2. **An expired token was reported as "no Running pod with label …".** `get pods -l …` returns an
   **empty item list** with the real error on stderr, so absence and unauthorized are indistinguishable
   from the result alone — the same fail-dangerous shape as §4's presence gates. Both scripts now call
   a new `require_cluster()` **before** any presence check, which prints
   `cannot reach namespace <ns>: … You must be logged in …` and, for the gate, says explicitly
   *"The PVC was NOT checked -- this is not a pass."* Verified in both.

`require_cluster()` probes reachability/authorization only and says so; it deliberately does not assert
the namespace exists, since `get pods` in a missing namespace can still exit 0 — that check belongs to
`preflight_shared_cluster.py`. It is duplicated in both scripts, consistent with the other duplicated
helpers (`kubectl`, `human`, `find_data_access_pod`, `sidecar_bytes_scanned`); factoring them into a
shared module is a reasonable follow-up but was not worth doing mid-session.

**Consequence for a cold resume: treat `harvest_run.py` as untested.** `pvc_gate.py` has run
successfully against the live cluster many times; `harvest_run.py` has never completed a single
operation. Validate it in stages — dry run, then `--apply` scan-only on the probe experiment, checking
`bytes_scanned` equals 7,570,490,291 — before letting it near a reclaim.

### 11.6 Still to do for design C
- `Makefile`: `benchmark-harvest` + `benchmark-pvc-gate` targets, gate as a prerequisite of
  `benchmark-run`, and the `llmdbenchmark run -s 0-8` → harvest → `-s 10-12` split. **Show the diff
  before applying** (existing file, substantial edit).
- `hack/benchmark/.env.sample`: `BENCHMARK_FETCH_PER_REQUEST`, `VIZ_EXTRACTOR`, margin knobs.
- `.gitignore` for the sidecars/partials.
- Optional plot-script hook (*"We can also run the viz plot script"*).
- 14-day tombstone sweep. **Must not sweep the two existing host per-request files** until viz
  extraction has run against them; and the probe run's host copy is truncated, so the PVC holds its
  only complete copy.
- Two belt-and-suspenders facts: step_09's `should_skip` returns True when the results dir is
  non-empty, so a harvest that pre-populates it makes step_09 a no-op; step_10's `should_skip`
  returns True when `harness_output == "local"`, which is our case, so it is already a no-op.

---

## 12. `reset_run.py` + `make benchmark-reset-run` (uncommitted)
Lowest rung of the cleanup ladder: **run-scoped only**. Does not rebuild the stack, change the
namespace's shape, or touch anything cluster-scoped. Deliberately does **not** un-pause KEDA — that
is a decision about starting a run, so it reports the pause and leaves it. `BENCHMARK_RESET_APPLY`
defaults to `false`. **Never yet run with `--apply`.**

---

## 13. Two upstream defect captures written (`session-notes/issues/`)
Dean, 2026-08-07: *"we will need to acpture the root cause and exact behavior, so we can open an
inference-perf issue later."* Two files, deliberately **separate** because only one is
inference-perf's:

- **`inference-perf-output-token-inflation.md`** — pinned to the commit that actually ran,
  `e250731ce8944f8ab76ece860e0960c6fa39b606` (`harness_version` in `run_metadata.yaml`; **all five
  local inference-perf clones are older** and lack `server_usage`/`token_count_mismatches`, so do not
  read source from them). Root cause: `output_len = tokenizer.count_tokens(output_text)` — a
  detokenize→re-tokenize round-trip, lossy for `data.type: random` + `ignore_eos: true`.
  inference-perf requests usage, receives it, stores it, reads `completion_tokens`, finds a mismatch
  on **7919 of 7919** requests, publishes the count as `token_count_mismatches`, then still computes
  every metric from the re-tokenized value. Non-obvious finding: `len(output_token_times) ==
  output_tokens` **exactly**, so the ITL timeline is over-sampled in lockstep and cannot be repaired
  downstream — only upstream.
- **`llm-d-benchmark-step09-silent-truncation.md`** — **different target (llm-d-benchmark).** Four
  links, all in `step_09_collect_results.py`: the copy is silent for ~10 min on a 7 GB file so it
  reads as a hang; `check=False` + `file_count > 0` is the only verification (a count, not a byte
  comparison); `should_skip` returns True on a non-empty dir so a retry cannot repair it; downstream,
  "exists locally" reads as "we have the data".
  **Corrects an earlier hypothesis of mine** — step_08 did *not* race the harness. The log shows
  `All pods completed successfully` at 04:56:03, all small files landed by 04:56:15, then 9m33s of
  silence, and the per-request file's mtime is 05:05:48 with
  `make: *** [Makefile:504: benchmark-run] Terminated` as the last line. The truncated size is an
  exact multiple of 512 (7,749,539 blocks) — an interrupted tar stream. The next run copied
  byte-exact through the same path, so this is an unguarded interruption, not systematic corruption.

---

## 14. Pre-run data pipeline executed and validated (2026-08-07)

Dean authorized *"feel free to delete in my NS's PVC"*. Everything below is done; nothing here is
the benchmark run itself, which still waits on the §7 approval.

### 14.1 `harvest_run.py --apply` — validated end-to-end, first time ever

Ran clean against all four experiments. **11.0 GB reclaimed**, `/requests` 8.9 GB free → 20 GB
(196 MB used). Every path the three bug-fixes touched was exercised on real data:

- **scan-on-demand** past a truncated local copy → the probe's 7.1 GB was scanned in-pod to a 34 KB
  vector. **`bytes_scanned` = 7,570,490,291, exactly the PVC size** — a complete scan, which is the
  gate that authorizes the delete. 7110 values, mean 1024.02, min 950 / max 1100, 148 distinct: a
  real distribution, not a degenerate artifact that would pass a size check while carrying nothing.
- **size-verified reclaim** on both files.
- **the truncated-fragment refusal** — the 3.7 GB local remnant was reported as superseded and left
  in place rather than silently trusted or silently deleted.

Before allowing `--apply` to trust a freshly-written sidecar I re-read
`completion_tokens_scan.py` to confirm `bytes_scanned` cannot over-report: it accumulates only
`len(chunk)` from actual `fh.read()` returns, and an empty result exits 1 rather than writing a
valid-looking empty vector. So `reclaim()`'s size guard is not vacuous.

**Then the gate re-run passed on exactly the mechanism a reclaim could have broken:** it still
estimates 7.1 GB for the next per-request file, sourced from the sidecar's recorded `bytes_scanned`
now that both files are deleted. Without that, the estimate would have collapsed to the 5.0 GB
default on the first run after a successful reclaim — under-estimating, which is the wrong direction.

### 14.2 `reset_run.py` reclaims PVC directories on an existence check — DEFECT, unfixed

`reset_pvc_results()` asks `if d in on_host` — the directory **name** exists under
`<workspace>/*/results/` — and then `rm -rf`s the PVC directory. That is an existence check standing
in for a completeness check: **the fourth instance of this exact substitution today**, after the
step_09 truncation, both scripts' expired-token misreport, and the pre-scan guard in `harvest_run.py`.

It is not hypothetical. Comparing names and sizes file-by-file before letting it run found **all four**
host copies incomplete, and `--apply` would have made the loss permanent:

| experiment | PVC files | gap |
|---|---|---|
| `guidellm-…6pckwk_1` | 105 | `analysis/summary.txt` |
| `guidellm-…i6x2vj_1` | 110 | `analysis/summary.txt` |
| `inference-perf-…41gfxn_1` | 424 | `benchmark_report,_stage_4_lifecycle_metrics.json.yaml` |
| `inference-perf-…d5lhav_1` | 260 | 3 × `analysis/*.png` |

**Root cause is a second, distinct step_09 defect:** the copy runs once, and `analysis/` is written
into the experiment directory *afterwards* — it does not exist on the host for **any** of the four
runs. Nothing re-syncs, and nothing notices, because "the experiment directory exists locally" reads
as "we have the results" (the D4 link in the step_09 issue). Belongs in that issue as a second
finding, not a separate report.

**Closed for now** by fetching the 6 missing files (264.6 KB) with size verification. Re-verified:
three of four experiments byte-identical, `SAFE to delete the PVC dir`.

The fourth still reports `NOT SAFE` on 3 files, and **that is correct behaviour I deliberately did
not loosen.** `benchmark_report_v0.2,_stage_{0,1,2}` differ because the host copies are the ones we
**corrected in place**; `diff` confirms the delta is exactly the correction — `output_len` mean
905.481 → 512.100, `inter_token_latency` mean 0.008998 → 0.015910 (×1.768, i.e. rescaled *up*, the
deflated direction from §10), plus the `output_token_correction` provenance block. The PVC holds the
uncorrected originals; the host copy is the one to keep. An understood exception, not a passing check.

Two new tools, both in `session-notes/scratch/` because they are one-offs that should be folded into
the §11 design rather than shipped as-is:
- `verify_pvc_vs_host.py` — the completeness check `reset_run.py` should be doing.
- `fetch_missing_from_pvc.py` — re-syncs PVC-only files. Uses `kubectl exec -- cat` with a byte-count
  check, **not `kubectl cp`**, whose unverified tar is what truncated 3.4 GB on 08-03; it also
  refuses to overwrite a size-mismatched host file, which is what protects the corrected reports.

### 14.3 Read-only staging for §7, all green

- `make benchmark-preflight BENCHMARK_NAMESPACE=dhl-wva-209` → **15 ok, 0 FAIL, 1 warn**. All five
  L3 presence-gates hold and all four fork patches are in place.
- `make benchmark-record-images BENCHMARK_NAMESPACE=dhl-wva-209` → the expected pre-standup picture:
  `wva-controller … :ta-0.9 [differs]` from the pinned `ta-0.9-anchor-20260806` (the standup is what
  closes it, per §7.3) and *"vllm: pinned … v0.20.2 but no running container found"* (decode is
  paused at 0). Harness `v0.6.7 [match]`. EPP and istio-proxy unpinned, as agreed.
- `reset_run.py` dry run re-confirms the ScaledObject is **still paused at 0** and says so unprompted.

### 14.4 The one warn, stated plainly

The fork clone is `ahead 0` but dirty: `M llmdbenchmark/analysis/output_token_correction.py` plus 7
untracked. Six of the seven are regenerable cache (scenario copies the Makefile writes, profiles
`sync_workloads.py` writes) and `uv.lock` is §6.4.

The modified file **is** load-bearing — `llmdbenchmark/analysis/__init__.py:126` imports it, and that
import is committed, so `BENCHMARK_ANALYZE=true` will invoke the working-tree version during step_12.
This run is not actually compromised: the raw per-request file will be present on the host at analysis
time, and the uncommitted change only adds the *sidecar fallback* used when it is absent, so committed
and modified behave identically here. But it is the same shape as the §9 hole — a load-bearing input
living only in a working tree — and it stops being harmless the moment the §11 design deletes the raw
file before analysis. Push the fork (§6.3) before that lands.

### 14.5 Still not done, deliberately

The §11 design's Makefile changes (gate as a `benchmark-run` prerequisite, the `-s 0-8` → harvest →
`-s 10-12` split, `.env.sample` knobs, `.gitignore`). Restated judgment call: not before this run.
The consequence is that this run keeps the current single-pass ordering, so its per-request file
arrives via the same unverified `kubectl cp` that truncated 08-03's — **`verify_pvc_vs_host.py` should
be run against the new experiment before anything deletes it.**

## 15. Anchor regression run executed (2026-08-07, Dean approved "Go with the regression test")

Purpose: the pokprod standup upgraded the controller to `ta-0.9-anchor-20260806`, so this doubles as a
**regression check of the anchor refactor**. Arm A = TA on, Arm B = identical staircase with TA off.

### 15.1 Pre-run gates — all cleared

| gate | result |
|---|---|
| controller image | `quay.io/deanlorenz/...:ta-0.9-anchor-20260806` **[match]**, pod Running 1/1, 0 restarts |
| decode vLLM | `docker.io/vllm/vllm-openai:v0.20.2` **[match]** — pin held despite crane resolving 0.25.1 |
| harness image | `ghcr.io/llm-d/llm-d-benchmark:v0.6.7` [match] |
| `num_gpu_blocks` | **6426**, block_size 64 — a real number, not `"None"`; ≈411k tokens ÷ 8192 ≈ 50 concurrent, consistent with the planner's 48.09 GB KV |
| PVC headroom | `OK: 19.8 GB available >= 9.6 GB required` (2 GB margin) |
| shared-cluster preflight | **15/15 ok**, 1 warn (fork dirty, §14.4) — all five L3 presence-gates confirmed to hold |
| free H100s | ~35+ free cluster-wide (`b93r43s2` 8, `b93r43s0` 7); our footprint is 2 |

### 15.2 The empty VariantAutoscaling status was NOT a regression

The standup's VA CRD object sat with **no `status` block** (blank `OPTIMIZED`/`METRICSREADY`). Resolved
as expected behaviour, not an anchor defect:

- `cmd/main.go:197` — "KEDA ScaledObject CRD detected - annotation-based ScaledObject discovery enabled"
- the ScaledObject carries `llm-d.ai/managed=true`, so **it** is the managed object; the CRD path is
  deprecated and simply not reconciled. The controller's `variant` field in every log line is
  `unsloth--608e585a-instruct-decode-scaler` — the **ScaledObject** name, not the CRD's.
- engine reported `variantCount: 1`, so the dangling CRD object was never double-counted
- decisive check: `configure_variants.py` **deleted** the VA CRD object, and the next reconcile still
  showed `variantCount: 1` with saturation enumerating the variant. Enumeration does not depend on it.

### 15.3 Two-HPA conflict resolved by design, no manual deletion

Standup step_09 created `hpa/unsloth--608e585a-instruct-decode` (min 1 **max 16**, no ownerReferences)
alongside KEDA's `wva-keda-hpa-...` (min 1 max 2). Both wrote `spec.replicas` on one Deployment.
`configure_variants.py --dry-run` planned exactly two precise, namespaced deletes (the VA CRD + that
HPA) and nothing else; applying it left a single HPA owned by the ScaledObject, SO `Ready=True
Active=True`, unpaused, 1–2. Nothing recreates the deleted HPA (no ownerReferences).

### 15.4 Analyzer set re-asserted — thresholds provably untouched

The helm install had left the saturation ConfigMap with **no `analyzers:` block at all** (only the four
thresholds), hence `cmd/main.go:537 ThroughputAnalyzer NOT registered`. `set_analyzers.py` handles the
missing-block case correctly (`build_payload` prepends unconditionally; `strip_analyzers_block` no-ops),
and its before/after print showed `kvCacheThreshold: 0.8 / queueLengthThreshold: 5 / kvSpareTrigger:
0.1 / queueSpareTrigger: 3` **byte-identical** — only the block was added. That is the property the A/B
arm switch depends on. After restart: `cmd/main.go:535 ThroughputAnalyzer registered`, and the engine
moved from `Processing model (V1)` to **`(V2)`** / `engine_v2.go`.

### 15.5 OPEN: TA reports `variants: []` at idle — early-abort checkpoint armed

At zero load the two analyzers disagree:

| analyzer | supply | demand | util | sc | variants |
|---|---|---|---|---|---|
| saturation | 329011 | 0 | 0 | 329011 | 1 (`prc 329011`, `reason P4-k1`) |
| throughput | 0 | 0 | 0 | 0 | **`[]`** |

There is no `throughput/` log site at all — TA registers and then says nothing. Two readings, not
separable at idle: **H1 benign** (TA contributes nothing until a measurable arrival rate) vs
**H2 regression** (the anchor refactor broke TA's variant enumeration). Ruled out as causes: TA's config
inputs are all present and loaded (`service-classes-config` exists, saturation config `oldEntries: 0 →
newEntries: 1`, Prometheus validated against thanos-querier, GPU limiter constructed).

Upstream suspect worth carrying forward: `collector/replica_metrics.go:1035` *"Pod has engine metrics
but no dispatch rate — possible pod/pod_name label mismatch"* fires **every** cycle, before and after
the restart, and dispatch rate is upstream of TA's demand.

Decision: not a blocker at idle. The discriminating test is load, so it is an **early-abort checkpoint**
at Arm A's first staircase step — if TA is still `variants: []` once load flows, that is a regression
(the 08-03 baseline had TA util ≈2× SAT sub-saturation) and the run stops rather than burning an hour
of H100.

**RESOLVED 2026-08-07 17:12:20Z — H1 was correct, NOT a regression.** TA populated on the first cycle
after load arrived. `variants: []` at idle is benign: with no arrival rate there is no demand and TA
contributes nothing. The anchor build's TA enumeration works.

### 15.5a First real result: TA drove the scale-up, SAT could not have

Same cycle, 5 RPS (stage 1), one replica:

| analyzer | supply | demand | util | rc | sc | reason |
|---|---|---|---|---|---|---|
| saturation | 329011 | 38918 | **0.118** | 0 | 273413.9 | `P3-k2` (was `P4-k1` at idle) |
| throughput | 2318.26 | 2355.61 | **1.016** | 453.05 | 0 | `T2-default` |

SAT's util 0.118 is nowhere near the 0.85 scale-up threshold; TA's 1.016 is over it. The combined
decision at 17:12:20 was `curr 1 → tgt 2, scale-up`, so **TA is what triggered it**. At this token shape
TA judges one replica to be exactly at capacity at ~5 RPS, where SAT's estimate is the profile's
~8–12 RPS. That is the A/B hypothesis in concrete numbers, and it predicts **Arm B holds at 1 replica
through stage 1** — which is the thing to check first when Arm B lands.

Consequence for this run's shape: because scale-up happens in stage 1 rather than stage 2, the run sits
at the `maxReplicas=2` ceiling for most of its length. Expect the interesting dynamics at the stage-3
drop back to 5 RPS (2 replicas ⇒ supply ≈4636 vs demand ≈2356 ⇒ TA util ≈0.51, below the 0.70
scale-down boundary ⇒ scale-down), not at the 12 RPS step. **This strengthens the case for raising
`maxReplicas` and lowering stage 1 in the follow-up science run** (§15.6).

Coupler validated end-to-end: `17:12:42 decode=2 reservation 1 -> 0`, freeing the pre-reserved GPU for
the new decode pod within one 5s poll instead of racing other tenants.

### 15.5b CANDIDATE REGRESSION: TA scales up a full stage earlier than the 08-03 baseline

This is the real output of the regression check, and it is **not** what §15.5 was watching for.

Baseline, from `dean-20260803-052634-197/staircase_shakedown.png` (x-axis = seconds from load start,
stage boundaries 0 / 360 / 720 / 1080):

- scale-up decided at **t ≈ 455s**, i.e. ~95s **into stage 2 (12 RPS)**
- TA held 1 replica through the **whole** 5 RPS stage
- per-stage latency says that was correct: 5 RPS → TTFT 0.1s (comfortable); 12 RPS on one replica →
  TTFT 25.9s / request latency 49.3s (genuine single-replica queueing)

Anchor build today: load pods Running 17:11:11, first non-zero-demand cycle and scale-up both at
**17:12:20 — ~69s into stage 1 (5 RPS)**.

So **5 RPS did not trigger scale-up before the refactor and does now** — one full staircase step earlier.

### 15.5c The actual mechanism: `prc` is unstable, and the target is `ceil(demand/prc)`

Nine consecutive cycles of controller log, `analyzer` = throughput, at only **two** load levels:

| time     | reps in supply | prc     | demand  | util  | ceil(d/prc) | decision   |
|----------|----------------|---------|---------|-------|-------------|------------|
| 17:12:20 | 1              | 2318.26 | 2355.61 | 1.016 | 2           | scale-up   |
| 17:13:20 | 1              | 3155.85 | 2542.77 | 0.806 | 1           | no-change  |
| 17:14:20 | 2              | 3444.06 | 2375.97 | 0.345 | 1           | scale-down |
| 17:15:20 | 2              | 2480.32 | 2957.45 | 0.596 | 2           | no-change  |
| 17:16:20 | 2              | 1693.83 | 2139.96 | 0.632 | 2           | no-change  |
| 17:17:21 | 2              | 2648.99 | 2539.15 | 0.479 | 1           | no-change  |
| 17:18:21 | 2              | 3848.63 | 5430.74 | 0.706 | 2           | no-change  |
| 17:19:21 | 2              | 3197.72 | 5838.34 | 0.913 | 2           | no-change  |

Two facts fall out, and they matter more than the timing delta in 15.5b:

1. **`prc` is not a stable capacity ceiling.** It swings **1693.83 → 3848.63 (2.3×)** cycle-to-cycle at
   steady load. `supply` is exactly `replicas × prc` in every row, so the instability is in the
   per-replica figure itself, not in the replica count.
2. **The replica target is `ceil(demand / prc)`** — reproduced in all eight decided cycles. The 0.85 /
   0.70 watermarks gate *whether to act*, they do not smooth the target. So a denominator with 2.3×
   spread feeds directly into the replica target, and **TA's own per-cycle target** chatters:
   2, 1, 1, 2, 2, 1, 2, 2. Read that as TA's internal vote only — the *emitted* combined decision
   reversed twice and the deployment never flapped at all (§15.13).

**This supersedes 15.5b's leading explanation.** The 17:12:20 scale-up was `prc` 2318.26 vs `demand`
2355.61 — a **1.6% margin** on a quantity whose own spread is 2.3×, computed from a measurement window
only ~69s deep (load pods Running 17:11:11). That is a cold-window transient landing on a hair-trigger
ratio, *not* demonstrated evidence that the refactor moved a capacity constant. The baseline's
t≈455s scale-up remains the load-driven one.

What is *not* retracted from 15.5b: the timing difference vs 08-03 is real and recorded, and SAT's
view genuinely did not move (util 0.118 at 5 RPS, `prc` pinned at 329011 in every row vs TA's swing).
What is retracted: attributing it to TA's capacity estimate having shifted downward in the refactor.

**Why Arm B cannot settle the regression question.** Arm B runs with TA off, so it measures SAT-only
behaviour — a useful control for "does 5 RPS scale up at all without TA", but silent on `prc`. Settling
regression-vs-not needs a **third arm on the pre-refactor WVA image** with TA on, same staircase. The
08-03 controller logs are gone, so `prc` history for the baseline cannot be recovered after the fact.
Propose that third arm to Dean; do not add it unasked.

Verified 2026-08-07, not assumed: searched `dean-20260803-052634-197/` and `dean-20260803-042120-916/`
(logs/, setup/commands/, analysis/) plus `ta-staircase-run.log` and `ta-probe-run.log` for
`analyzer-result` / `T2-default`. Zero real hits — the only `T2-default` matches are comments in one of
our own scripts. **The benchmark harness does not capture WVA controller logs into the run dir.** That is
a concrete gap: without it, every future run is un-auditable for analyzer internals the moment the pod
recycles. Worth adding a controller-log capture step to the harvest path (§15.8 pipeline) so the next
comparison does not hit this wall.

Captured manually for Arm A as insurance: `dean-20260807-201009-695/wva-controller-arm-a.partial.log`
(333 lines, `--since-time=17:00:00Z`, taken mid-run). Re-capture the full window at completion.

Second reproducibility gap found while staging the §15.8 pipeline: **two of its three scripts are not in
`hack/benchmark/`** — `verify_pvc_vs_host.py` and `fetch_missing_from_pvc.py` are still in
`session-notes/scratch/`. Only `harvest_run.py` was promoted. So the post-run data path is currently
half scratch, i.e. not reproducible from the repo the way §15.8 implies. Promote both (they are the step
that protects the multi-GB reclaim decision from acting on unverified data). Note `plot_staircase.py`
*is* in `hack/benchmark/` — the stale root-level copy in the old git-status snapshot is gone.

### 15.9 Arm A collected; the reclaim gate caught real host-side data loss

`make benchmark-run` exited 0. Harness summary: **0 errors**, avg primary replicas **1.85** / max **2**,
avg pod startup **94 s**, avg KV cache utilization **15.9 %**. Missing `P99 TTFT` / `P99 ITL` /
`queue depth` in that table are the known `analysis/` gap, closed below.

Avg 1.85 of a max 2 means decode sat at 2 replicas for ~85 % of the 18-minute window — consistent with
the 17:12:20 scale-up ~69 s in and no effective scale-down until after load. And **15.9 % average KV
utilization** is the independent check on §15.5c: one replica had large headroom for the whole run, so
the scale-up was not warranted on saturation grounds. TA's `prc` instability, not real pressure.

**`verify_pvc_vs_host.py` returned 2 of 5 experiments NOT SAFE, and it was right both times — for
opposite reasons.** This is the first time the gate has earned its keep.

- 08-03 baseline (`...d5lhav_1`): host files *larger* than PVC (20831 vs 20391) and they **do** contain
  the observability section. That is `correct_output_tokens.py` run manually after fetch, against a
  complete report: full file + correction metadata. Benign; the gate cannot distinguish, so it blocks.
- Arm A (`...k0ezvy_1`): host files *smaller* — `pvc=20223 host=4880`, and `grep -c observability` on
  every host file returned **0**. The section existed only on the PVC.

Cause is ordering, not corruption, and not a script-version difference — there is exactly one
`correct_output_tokens.py` (`hack/benchmark/`, Aug 3; the root-level copy in the stale git-status
snapshot no longer exists). On 08-03 the correction ran manually *after* the report was final. For Arm A
it ran inside collection via `--analyze`, against a report the harness had not finished writing; the
observability section the harness appended afterwards never reached the host, and the corrected file
overwrote what was there. **`--analyze` during collection races the harness's own report writer.**

Why this mattered more than a size mismatch: the dropped section holds `replica_status`,
`epp_pool_ready_pods`, `pod_startup_times`, `epp_pool_avg_queue_size`, `epp_pool_avg_running_requests`,
`vllm_kv_cache_usage_perc`. **That is the replica trace the A/B comparison is built on.** Had the PVC dir
been reclaimed on a directory-name check, the Arm A replica trace would have been permanently lost while
every host-side signal said "results collected, 0 errors".

Actions taken (all non-destructive — **nothing deleted; PVC at 16 GB free / 21 % used, no reclaim
needed this cycle**):

1. `fetch_missing_from_pvc.py --apply` — fetched the 3 missing `analysis/*.png`, size-verified. Its
   default keeps size-mismatched files rather than overwriting, so all 9 corrected reports survived.
2. Recovered the 3 complete v0.2 reports via `kubectl exec -- cat` into
   `results/inference-perf-1786122657-k0ezvy_1/pvc-original/`, byte-verified (20223 / 20223 / 20229).
   Kept alongside the corrected copies so both the observability data and the correction metadata exist
   on host. Did **not** overwrite — the corrected copies carry `inflation_factor` and are not
   reproducible from the PVC original alone.
3. Full controller log captured to `dean-20260807-201009-695/wva-controller-arm-a.log` (646 lines).

Only the 3 v0.2 files were recovered, deliberately: the non-v0.2 reports differ by ~188 B, the same
correction-metadata delta as the baseline's +440 B, and carry no observability section.

### 15.9a Correction to 15.9 — harvest overwrote the corrected copies, and step_09 had already
### fetched the 4 GB file

Two things in 15.9's action list did not survive the next step, and the sequence matters more than the
tidy version:

1. **`harvest_run.py --apply --no-reclaim` re-copied the whole experiment (315 files) and overwrote the
   corrected reports with the PVC originals.** So the `inflation_factor` metadata 15.9 said was preserved
   was in fact replaced. Not data loss — the correction is re-runnable — but 15.9's claim as written was
   wrong within ten minutes of being written. The `pvc-original/` copies are now redundant duplicates of
   the main copies; kept as evidence of the original divergence, harmless.
2. **The 4.2 GB `per_request_lifecycle_metrics.json` was fetched to the host by step_09 during
   collection**, not by harvest. Timestamps settle it: big file `20:45:20` (collection), vector
   `20:55:22` (harvest). The first `verify_pvc_vs_host.py` run also already showed it byte-matching on
   host before harvest ran. So harvest's `--exclude` is working as designed but is **structurally unable
   to save the copy** — it runs *after* the step that does the expensive fetch. That is the §11 design-C
   Makefile change (skip step_09's blanket copy) still being deferred; until it lands, every run pays the
   multi-GB local copy regardless of harvest.

Final Arm A state, verified: `make benchmark-analyze` re-applied the correction onto the now-complete
report. Host v0.2 stage 0 is **20722 B** = PVC original 20223 B + correction metadata, with
`observability` present **and** `inflation_factor: 1.79` / `true_output_len_mean: 512.356` — and
`extracted_from: sidecar server_completion_tokens.json (7920 values)`, i.e. it used the 31 KB vector, not
the 4 GB file. That is the same shape as the 08-03 baseline (host slightly larger than PVC, both sections
present), so the `--analyze`-races-the-report-writer problem is resolved for this run.

**Nothing was deleted anywhere.** PVC unchanged at 4.2 GB used / 16 GB free / 21 %. The 4 GB reclaim was
deliberately *not* taken: no space pressure, the delete is irreversible, and the autoscaling-viz near
path wants full per-request traces from our own runs. `server_completion_tokens.json` is now on host, so
the reclaim remains available later without losing re-runnability of the correction. **Flag for Dean —
this is his call, not the harness's.**

Cool-down happened on its own: HPA dropped decode to 1 at ~17:34 after three consecutive `tgt:1`
decisions (17:32:22 / 17:33:22 / 17:34:22), and the coupler re-parked the GPU at 17:34:24. Both
deployments back to 1/1, HOLD_TOTAL=2 intact — the coupler is validated in **both** directions now.

### 15.11 Arm B launched (TA off) — 2026-08-07 ~17:59Z

Switched with `make benchmark-set-analyzers BENCHMARK_NAMESPACE=dhl-wva-209 WVA_ANALYZERS=saturation`.
All four thresholds byte-identical across the switch (`kvCacheThreshold: 0.8`, `queueLengthThreshold: 5`,
`kvSpareTrigger: 0.1`, `queueSpareTrigger: 3`) — the arm switch changed the analyzer set and nothing
else, which is the whole reason `set_analyzers.py` exists instead of `benchmark-enable-v2-saturation`.

TA de-registration confirmed **positively**, not by absence:

```
17:59:08  cmd/main.go:537  ThroughputAnalyzer NOT registered — no saturation config entry
                           enables 'throughput'.
```

plus 0 `"analyzer": "throughput"` lines against 1 `"analyzer": "saturation"` on the new pod
(`...-6687cbf65d-4dk9w`). Startup-gated registration behaved as documented.

Pre-launch invariants re-checked (all namespaced to `dhl-wva-209`):

| check | state |
|---|---|
| ScaledObject | `Ready=True Active=True`, min 1 / max 2 |
| HPAs on the decode deployment | exactly **1**, `ownerReferences[0].kind=ScaledObject` |
| decode / gpu-reservation | 1/1 and 1/1, HOLD_TOTAL=2 satisfied |
| PVC | 4.2 GB used / 16 GB free / 21 % — Arm B's ~4.2 GB fits with margin, no reclaim |
| coupler | re-armed `MAX_ITERS=700` (~58 min; Arm A's cap would have expired ~18:07) |

Command is byte-identical to Arm A, so `base_seed: 42` gives the same request stream:
`make benchmark-run BENCHMARK_NAMESPACE=dhl-wva-209 BENCHMARK_SPEC=guides/wva-sat2-tp1 BENCHMARK_WAIT_TIMEOUT=2400`

**Arm B run identifiers** (for the post-run pipeline — the pipeline scripts need these by name):

| | value |
|---|---|
| run dir | `dean-20260807-210058-612` |
| experiment | `inference-perf-1786125698-ptufog` |
| harness pod | `inference-perf-982esfhe` |
| load window | 18:02:19Z → 18:20:19Z (stage1 5 RPS / stage2 12 RPS / stage3 5 RPS, 360 s each) |
| controller log | `dean-20260807-201009-695/wva-controller-arm-b.partial.log` — note it lives under the **Arm A** run dir, since it was captured by hand outside the harness (§15.13) |

Arm A for comparison: run dir `dean-20260807-201009-695`, experiment `inference-perf-1786122657-k0ezvy_1`.

**Identical-stimulus check — verified, not assumed.** The claim "only the analyzer set differs" is what
the whole A/B rests on, so the *rendered* profiles were compared rather than just the invoking command:

```
7e0935fee1789c6dd97fbaf213bbe86d  dean-20260807-201009-695/.../ta_autoscale_staircase.yaml  (3152 B)
7e0935fee1789c6dd97fbaf213bbe86d  dean-20260807-210058-612/.../ta_autoscale_staircase.yaml  (3152 B)
```

Byte-identical, and the profile carries `base_seed: 42`, so both arms drew the same request stream.

**PVC state at Arm B's end of load (18:20Z), `dhl-wva-209`:** 4.2 G used / 16 G avail / 21 %.

| experiment | size | note |
|---|---|---|
| `inference-perf-1786122657-k0ezvy_1` | **4.0 G** | Arm A — the per-request trace, reclaim escalated to Dean, still intact |
| `inference-perf-1786125698-ptufog_1` | 29 M → ~4 G | Arm B, still being written at this point |
| 4 older experiments (2 guidellm, 2 inference-perf) | 194 M total | their multi-GB files were reclaimed in earlier passes |

Projected steady state ~8.2 G of 20 G (~41 %). **There is no space pressure**, which is the concrete
basis for declining the Arm A reclaim rather than a preference: the reclaim is irreversible, autoscaling-viz
wants full per-request traces, and nothing needs the room. The `--no-reclaim` vector keeps it available
later.

**First thing to read off Arm B:** does it hold at 1 replica through stage 1 (5 RPS)? SAT's Arm A util
there was 0.118 with `prc` pinned at 329011, so it should. If Arm B *also* scales up at 5 RPS, the cause
is not TA and §15.5b/15.5c both need rethinking. The monitor additionally flags any `throughput`
analyzer line as `TA-LEAK(BUG)` — none should ever appear this arm.

Repeat of the §15.9a lesson for this arm: `--analyze` will again race the report writer, so expect the
same observability-dropped host copies. Run `verify_pvc_vs_host.py` **before** anything deletes, then
`make benchmark-analyze` after harvest, not before.

### 15.12 Arm B answers the question: the difference IS attributable to TA

Arm B load start 18:02:19Z, so stage 1 (5 RPS) = 18:02:19–18:08:19, stage 2 (12 RPS) = 18:08:19–18:14:19.

Saturation-only, every cycle of stage 1:

| time | prc | demand | util | decision |
|---|---|---|---|---|
| 18:04:08 | 329011 | 79756 | 0.242 | no-change |
| 18:05:08 | 329011 | 125203 | 0.381 | no-change |
| 18:06:08 | 329011 | 123859 | 0.376 | no-change |
| 18:07:09 | 329011 | 133397 | 0.405 | no-change |
| 18:08:09 | 329011 | 96143 | 0.292 | no-change |
| 18:09:09 | 329011 | 416065 | **1.265** | **scale-up** (50 s into 12 RPS) |

Two clean results:

1. **Arm B held 1 replica through all of 5 RPS and scaled 50 s into 12 RPS** — which reproduces the
   08-03 baseline (~95 s into 12 RPS). Arm A scaled 69 s into *5* RPS. Same image, same workload, same
   seed, same cap; the only difference between A and B is whether TA is registered. **So the earlier
   scale-up is attributable to TA.**
2. **SAT's `prc` is rock-stable: 329011 in all six rows**, and its util tracks load monotonically-ish
   (0.24–0.41 at 5 RPS, 1.265 at 12 RPS). Contrast TA's 1694–3849 swing in §15.5c. This kills the
   alternative explanation that `prc` volatility is an artifact of the metrics pipeline or the
   measurement window — SAT reads the same cluster over the same windows and is stable. **The
   instability is inside TA's capacity computation.**

Also: 0 `TA-LEAK(BUG)` events, confirming de-registration held for the whole arm.

**Revised conclusion, superseding both 15.5b and 15.5c's framing.** The defect is not "TA's capacity
constant moved in the refactor". It is that **TA's per-replica capacity estimate is unstable (2.3×
cycle-to-cycle) and biased low enough at 5 RPS to cross a 0.85 threshold**, while the load is genuinely
at ~15.9 % KV utilization and SAT correctly reports ~0.3 util. When TA participates it dominates the
combined decision and produces both premature scale-up and target chatter.

> **The word "premature" in the paragraph above does not survive the outcome data. See §15.16.** Arm B's
> corrected reports show the run *without* TA suffered 7× worse p95 latency and a 44-deep queue. TA's
> early scale-up was protective, not gratuitous. The instability finding (unstable `prc`) stands
> unchanged; the value judgement attached to the scale-up does not.

**What changed since 08-03 is most likely that TA now *participates*.** §15.5 recorded "TA `variants:
[]`" as an open pre-run concern, resolved today when TA populated the instant load arrived — i.e. there
was a prior state where TA enumerated nothing and therefore could not drive a decision. Earlier notes
also record baseline "TA util ~2× SAT sub-saturation", which at SAT's 0.4 would put TA near 0.8 —
*just under* the 0.85 threshold, versus 1.016 today. Flagging the strength of that inference honestly:
the 0.8 figure comes from our own earlier notes, **not** from recovered baseline data (verified
unrecoverable, §15.5c). So "TA went from just-under to just-over" is consistent with everything observed
but is not independently confirmed.

That nuance is why the third arm (§10 / pre-refactor image, TA on) is still the right way to settle
*whether the refactor changed TA's numbers* — but it is no longer needed to establish *that TA is the
cause of the 5 RPS scale-up*. Arm B settled that.

**The finding worth taking to the anchor-refactor review is the instability itself**, independent of
before/after: a decision rule of `ceil(demand/prc)` on a `prc` with 2.3× spread cannot be stable, and
only HPA's stabilization window is currently hiding it.

### 15.13 Arm B full trace — `ceil(demand/prc)` is the *engine's* rule, not a TA quirk

Complete 18-cycle saturation trace, captured to `dean-20260807-201009-695/wva-controller-arm-b.partial.log`
(278 lines; the harness does not capture controller logs, so this is hand-collected — see §15.11).

`prc` = **329011 in all 18 rows**, zero drift. `supply` = replicas × prc exactly (329011 at 1 replica,
658022 from 18:11:09 once the second replica was ready).

| time | demand | util | reason | tgt | `ceil(demand/prc)` |
|---|---|---|---|---|---|
| 17:59:08–18:02:08 | 0 | 0 | P4-k1 | 1 | idle, pre-load |
| 18:03:08 | 12994 | 0.039 | P3-k2 | 1 | 1 ✓ |
| 18:04:08 | 79756 | 0.242 | P3-k2 | 1 | 1 ✓ |
| 18:05:08 | 125203 | 0.381 | P3-k2 | 1 | 1 ✓ |
| 18:06:08 | 123859 | 0.376 | P3-k2 | 1 | 1 ✓ |
| 18:07:09 | 133397 | 0.405 | P3-k2 | 1 | 1 ✓ |
| 18:08:09 | 96143 | 0.292 | P3-k2 | 1 | 1 ✓ |
| 18:09:09 | 416065 | 1.265 | P3-k2 | **2** | 2 ✓ **scale-up** |
| 18:10:09 | 1253374 | 3.810 | P1-obs | 2 | **4**, clamped by maxReplicas |
| 18:11:09 | 1798806 | 2.734 | P4-k1 | 2 | 3, clamped |
| 18:12:09 | 2545089 | 3.868 | P1-obs | 2 | **4**, clamped |
| 18:13:09 | 1646657 | 2.502 | P1-obs | 2 | 3, clamped |
| 18:14:09 | 981159 | 1.491 | P1-obs | 2 | 2 ✓ |
| 18:15:09 | 356087 | 0.541 | P2-hist | 2 | 2 ✓ (util<0.70 but ceil=2) |
| 18:16:09 | 96975 | 0.147 | P2-hist | **1** | 1 ✓ **scale-down** |

**`ceil(demand/prc)` reproduces at every unclamped point for saturation as well as for TA.** This
promotes §15.5c's finding from "TA behaves this way" to "**the engine divides by whatever `prc` the
analyzer reports and ceilings it, with no smoothing anywhere in the path**". An analyzer with an
unstable `prc` therefore has that instability amplified directly into replica counts. That is the
architectural point for the review: the hair-trigger is structural, and TA's noisy `prc` merely walks
into it.

Note on the 18:15:09 row: `util` 0.541 is below the 0.70 scale-down boundary, yet `tgt` stayed 2.
Consistent with §15.5c — the watermarks gate *whether to act*, the target itself is `ceil(demand/prc)`
= ceil(1.082) = 2. The boundary and the target are computed from different quantities (util is vs.
current *supply*, the target is vs. *per-replica* capacity). Worth confirming that is intended.

**Two side findings, both pre-existing rather than anchor-related:**

1. **SAT's `P1-obs` path overshoots hard under saturation** — 3.810× and 3.868× supply at 12 RPS,
   i.e. it asked for 4 replicas and only `maxReplicas=2` held it. This reproduces the "SAT P1-obs
   overshoots ~5×" observation recorded from the 08-03 run, so it is not a regression. It does mean
   the 12 RPS stage was **capped, not converged** — relevant when raising `maxReplicas` later, as
   §15.5 planned: SAT will immediately take 12 RPS to 4 replicas.
2. Reason-code progression is orderly: `P4-k1` (idle) → `P3-k2` (ramp) → `P1-obs` (saturated) →
   `P2-hist` (decay). No unexpected codes.

**De-registration verified positively, not by absence:** exactly one throughput mention in the whole
window, and it is the proof line —
`cmd/main.go:537 ThroughputAnalyzer NOT registered — no saturation config entry enables 'throughput'` —
against 18 saturation `analyzer-result` rows and 0 throughput rows. 0 `TA-LEAK(BUG)` monitor events.

**Chatter comparison, the cleanest A/B signal available.** Three distinct levels — an earlier draft of
this table blurred them, and the reversal count differs at each, so they are separated here:

| level | Arm A (SAT+TA) | Arm B (SAT only) |
|---|---|---|
| analyzer's own per-cycle target | `2,1,1,2,2,1,2,2` — reverses **4×** at constant load | `1×8, 2×7, 1` — monotone |
| **emitted** combined decision | reverses **2×**: up 17:12:20 → down 17:14:20 → up 17:15:20 | 1 scale-up, 1 scale-down (re-emitted 18:17:09) |
| actual deployment replicas | **never flapped**: 1→2 at 17:12:42, held 2 until 17:34:22 | 1→2, 2→1; no reversal |

Arm B's repeat at 18:17:09 is the *same* target re-emitted because HPA's stabilization window had not yet
acted; that is not oscillation. The `2,1,1,2,2,1,2,2` sequence is **TA's internal target**, not the
emitted decision and not the replica count — the combined decision reversed twice, and the deployment
not at all, because HPA scale-down stabilization absorbed the down-vote (see §15.15 "Flap is currently
masked, not absent"). So the defensible claim is *premature scale-up plus decision-level instability*,
**not** observed replica thrash.

### 15.14 Arm C proposal — the baseline image survives, and it is pinnable by digest

**This is a proposal for review, not a scheduled run.** Nothing below has been executed.

**The prerequisite I expected to block this turns out to be clear.** The 08-03 baseline recorded its
controller image as `tag: ta-0.9` with `imagePullPolicy: Always` — a *mutable* tag with no digest, which
is exactly the reproducibility hole the 08-07 pass closed going forward but could not close
retroactively. So the question was whether that tag still points at the 08-03 bits. Registry says yes:

| tag | digest | last pushed |
|---|---|---|
| `ta-0.9` | `sha256:80dec0e9728f4e7d1d06a952f43330e8b1ac5f09592284f87c0e9981c05e19ca` | **2026-07-30 16:21 UTC** |
| `ta-0.9-anchor-20260806` | `sha256:d64560713ec4783550b49d7b405ed26edd4334828f5f7befcd5b8d1efb28f93a` | 2026-08-06 16:08 UTC |

The anchor build went to a **separate tag**, so it never clobbered `ta-0.9`, and `ta-0.9` has had no push
since 07-30 — before the 08-03 run. Therefore the 08-03 run pulled `80dec0e9`, and that image is still
retrievable. Arm C can be pinned **by digest**, which is strictly better than what the baseline itself had.

Currently running, verified against the registry (`dhl-wva-209`):
`...controller-manager` spec `:ta-0.9-anchor-20260806`, resolved `imageID` `sha256:d6456071…`. So Arms A
and B are both confirmed on the anchor digest, and the A/B/C image story is fully pinned.

**Proposed Arm C:** identical to Arm A in every respect except the controller image.

| | Arm A | Arm B | **Arm C (proposed)** |
|---|---|---|---|
| controller | `@sha256:d6456071` (anchor) | `@sha256:d6456071` (anchor) | **`@sha256:80dec0e9`** (pre-refactor) |
| analyzers | saturation,throughput | saturation | saturation,throughput |
| profile | `7e0935fe…`, seed 42 | same | same |
| decode image / maxReplicas / coupler | unchanged | unchanged | unchanged |

**The one thing Arm C must do that 08-03 did not: capture the controller log.** That omission is why
baseline `prc` is unrecoverable (§15.5c) and why this arm is needed at all rather than a re-read. Capture
by hand as in §15.13 — the harness still does not collect controller logs (open follow-up).

**Pre-declared read-off, so the result cannot be rationalized after the fact.** Read TA's `prc` series and
its `util` during stage 1 (5 RPS). Three outcomes, all informative:

1. **TA `prc` stable and `util` < 0.85 at 5 RPS** → the anchor refactor introduced the instability.
   Regression confirmed, and it belongs in the PR-1/PR-2 review before merge.
2. **TA `prc` swings comparably (~2×) and `util` straddles 0.85** → the instability is pre-existing, and
   Arm A's early scale-up was luck-of-the-cycle rather than a new defect. *Not* a regression — but the
   instability is still a real bug worth filing on its own merits, because §15.13 shows the engine
   ceilings `demand/prc` with no smoothing anywhere.
3. **TA reports `variants: []`** → TA was inert pre-refactor, and the refactor made it actually
   participate. That is an improvement in participation which *exposed* a latent capacity bug rather
   than creating one. Framing for the review changes accordingly.

§15.12's inference favors outcome 3, which is precisely why it should not be assumed — the pre-declaration
above exists to keep outcome 3 from being read into an ambiguous trace.

**Cost / risk.** ~30 min of cluster time, one controller image swap and swap-back, no changes outside
`dhl-wva-209`. The swap-back target is pinned above, so restoring the anchor build is exact. Risks: the
image swap restarts the controller (fine, registration is startup-gated anyway, §15.11 already exercised
this path twice); and the pre-refactor build's CRD expectations should be sanity-checked against the
currently-installed CRDs before the swap, since a week of main may have moved them — **that check is a
gate on Arm C, not an assumption.**

**Awaiting Dean's go/no-go.** Not run.

### 15.15 Results sample (Arm A) — and a trap in the stage reports

Sampled with `session-notes/scratch/sample_report.py <results-dir>` (new, dependency-free — a results
*sample* should not require a package install; it walks the reports' stable two-space indentation).

| metric | stage 0 (5 RPS) | stage 1 (12 RPS) | stage 2 (5 RPS) |
|---|---|---|---|
| requests total | 1800 | 4320 | 1800 |
| **failures** | **0** | **0** | **0** |
| request rate | 4.94 | 11.74 | 4.93 |
| req latency mean / p95 | 6.92 / 8.43 s | 10.96 / 12.41 s | 6.48 / 7.13 s |
| TTFT mean / p95 | 0.165 / 0.153 s | 0.192 / 0.340 s | 0.100 / 0.154 s |
| TPOT mean | 0.0135 s | 0.0217 s | 0.0128 s |
| output tok/s | 2531 | 6016 | 2526 |
| total tok/s | 12650 | 30070 | 12620 |
| output_len mean (corrected) | 512.4 | 512.4 | 512.4 |

The staircase was **delivered as specified** — 4.94 / 11.74 / 4.93 measured against 5 / 12 / 5 requested —
with zero failures in 7920 requests, and latency responds monotonically to load (TPOT 1.6× at 12 RPS).
Stage 2 comes back slightly *faster* than stage 0 (6.48 vs 6.92 s) because it runs on 2 replicas for most
of its duration while stage 0 started on 1.

**The trap: the `observability` block is run-wide, not per-stage.** Lines 2–475 of all three stage reports
are byte-identical, md5 `3535b5c182cfe8de0956f03aca817ce4` in each. Inside it,
`replica_status.timestamp: 2026-08-07T17:32:23Z` is the *end* of the run (`harness_stop` 17:32:36) and
`aggregate_ready_replicas.count: 82` spans the entire run. So it is a single end-of-run scrape replicated
into each stage file:

| run-wide observability value | |
|---|---|
| `epp_pool_avg_kv_cache_utilization` mean / p99 | **0.1567** / 0.4412 |
| `epp_pool_ready_pods` mean | 1.854 |
| `epp_pool_avg_running_requests` mean | 29.26 |
| `epp_pool_avg_queue_size` mean | 0.0061 |
| `replica_status.aggregate_ready_replicas` | min 1, max 2, mean 1.854, stddev 0.356, n=82 |

**Consequence for the A/B writeup.** The 15.7 % KV-utilization figure quoted earlier is a whole-run mean,
which is how it was stated ("for the entire Arm A run") — that stands. But the *sharper* claim, that
utilization was low **specifically during the 5 RPS stage where TA scaled up**, cannot be sourced from
these reports at all. It has to come from the controller log's per-cycle `util`, which is exactly what
§15.5c (TA) and §15.13 (SAT: 0.242–0.405 through stage 1) provide. So the per-stage evidence exists — but
its only source is the hand-captured controller log, which reinforces the open follow-up to add
controller-log capture to the harvest path. **Do not cite the stage reports for per-stage utilization.**

Also visible: `epp_pool_avg_queue_size` mean 0.0061 and `p99` 0.095 run-wide. Queueing was essentially
nil even at 12 RPS, which is independent corroboration that neither stage was capacity-limited in the way
TA's `prc` implied.

**Token-correction provenance**, carried in each report:

```
source:          vllm usage.completion_tokens
extracted_from:  sidecar server_completion_tokens.json (7920 values)
true_output_len_mean:      512.4  (all three stages)
reported_output_len_mean:  917.1 / 921.7 / 933.5   (per stage)
inflation_factor:          1.790 / 1.799 / 1.822   (per stage)
```

Two things worth noting for the planned upstream inference-perf issue. The inflation is ~1.8× and it is
**not constant across stages** — and notably stage 2 (5 RPS) has the *highest* factor (1.822) despite
being the same rate as stage 0 (1.790), so it does not track load. That argues against a
saturation-related explanation and toward something cumulative or drift-like in the re-tokenization path.
Flagging the strength of that honestly: three points on one run is thin, so it is a hypothesis to test in
the issue, not a claim to file.

Second: post-correction `output_len` mean is **512.4 in all three stages** — the correction applies one
run-wide true mean to every stage while using per-stage inflation factors. If per-stage true means ever
genuinely differ, that would flatten real variation. Here it is benign, because the profile draws output
length from one fixed distribution (observed range 480–550), so the true per-stage means really should be
near-identical. Worth confirming as intended rather than incidental before the correction is folded into
the benchmark code.

### 15.16 Arm B outcome data REVERSES the "premature scale-up" reading

Arm B's pipeline (§15.17) produced its corrected reports, and the A/B *outcome* comparison says the
opposite of what §15.12 and §15.13 concluded about the value of TA's early scale-up. Recording the
reversal explicitly rather than quietly restating it.

**Stage 1 (12 RPS), per-stage `request_performance` — genuinely per-stage, so this comparison is valid:**

| metric | Arm A (TA on) | Arm B (TA off) | ratio |
|---|---|---|---|
| request latency mean | 10.96 s | **39.4 s** | 3.6× |
| request latency p95 | 12.41 s | **86.53 s** | 7.0× |
| TTFT mean | 0.192 s | **17.95 s** | 93× |
| TTFT p95 | 0.340 s | **61.24 s** | 180× |
| TPOT mean | 0.0217 | 0.0431 | 2.0× |
| request rate delivered | 11.74 | 11.75 | — |
| output tok/s | 6016 | 6013 | — |

**Run-wide `observability` (single end-of-run scrape both arms — 82 vs 83 samples, so comparable):**

| metric | Arm A | Arm B |
|---|---|---|
| KV util mean | 0.1567 | 0.3411 |
| KV util p99 | 0.4412 | **1.000 — fully saturated** |
| queue size mean | 0.0061 | **44.17** |
| running requests mean | 29.26 | 63.60 |
| ready replicas mean | 1.854 | 1.313 |
| ready replicas p25/p50/p75 | 2.0 / 2.0 / 2.0 | **1.0 / 1.0 / 2.0** |

The quartile row is the cleanest single statement of the difference and needs no derivation: Arm A sat at
2 replicas for ≥75 % of the run, Arm B at 1 replica for ≥50 %.

**What this means, and what it costs my earlier reading.**

1. **Throughput was identical** (11.74 vs 11.75 RPS delivered, ~6015 output tok/s, 0 failures in 7920
   requests both arms). Nothing was dropped. The entire cost of running under-provisioned showed up as
   latency, which is exactly why a throughput-only readout would have missed it.
2. **§15.13's supporting argument was circular.** I wrote "queue size averaged 0.006 run-wide, so there
   was no queueing to justify the scale-up." The queue was 0.006 in Arm A *because TA had already scaled
   up*. Using the post-intervention state to argue the intervention was unnecessary is the error; Arm B is
   the counterfactual and it queues 44 deep.
3. **12 RPS is over-capacity for 2 replicas in both arms.** SAT's `P1-obs` wanted 4 replicas (util 3.81)
   and was clamped by `maxReplicas=2`. So neither arm was adequately provisioned for stage 1 — the
   difference is that Arm A *entered* the stage already at 2, while Arm B spent ~50 s plus HPA delay at 1
   and built a backlog that dominated the remaining ~5 minutes. Standard queueing behaviour at offered
   load above service rate: the backlog does not drain until load drops (and Arm B's stage 2 recovers to
   7.76 s mean, confirming it drained only when load fell back to 5 RPS).
4. **What survives unchanged:** TA's `prc` is unstable (1694→3849, 2.3×); the engine rule is
   `ceil(demand/prc)` with no smoothing; SAT's `prc` is pinned at 329011. Those are measurements. What
   does *not* survive is the value judgement — "premature", "against no real pressure", "scaled up against
   no measurable pressure". On this workload TA's early scale-up was **protective**.
5. **The honest framing for the anchor review**: TA reaches a defensible decision by an undefensible
   route. An unstable denominator that happens to bias toward early scale-up is still a correctness
   problem — it would bias toward late scale-up on a different workload, and the 2.3× spread is not
   something to rely on. Do not, however, present the 5 RPS scale-up as evidence of harm; the data shows
   the opposite on this staircase.

**Unresolved and not to be asserted either way:** whether 2 replicas at 5 RPS is itself justified. Arm A's
stage 0 latency (6.92 s mean) is better than Arm B's (8.17 s), but ready-replica counts are only available
run-wide, so per-stage attribution is not available from these reports. Answering it needs the per-cycle
controller log cross-referenced against the per-request trace (§5 of the viz handoff).

### 15.17 Arm B post-run pipeline — and a new step_09 defect

Ran in the §15.11 order: PVC listing → verify → fetch gaps → harvest `--no-reclaim` → `benchmark-analyze`
last. Nothing was deleted; PVC unchanged at 8.1 G / 20 G (41 %) before and after, `0 B reclaimed`.

**The verify-before-delete gate earned its place again.** Initial verdict on Arm B was `NOT SAFE`,
233/242 byte-identical, with 3 files missing and 6 differing. Final state after remediation: **242/242
byte-identical**.

**New defect, distinct from the §15.9a `--analyze` race: step_09 does not copy the reports, it
regenerates them locally.** Diff of the PVC's v0.1 stage-0 report against the host copy step_09 left:

```
< metadata:  eid: inference-perf-1786125698-ptufog      PVC only
< host:      accelerator: [] / type: []                 PVC only
< platform:  engine / metadata: inferenceScheduler      PVC only
< model:     name: unsloth/Meta-Llama-3.1-8B-Instruct
> model:     name: unknown                              host
```

Tested for truncation first and ruled it out — the host file is **not** a prefix of the PVC file (differs
at byte 4, line 1), so this is regeneration without cluster context, not an interrupted copy. Consequences:

* `model.name` degrades to **`unknown`** — an archived run silently loses which model it ran.
* The entire `observability` block is absent (host v0.2 4.9 KB vs PVC 20.4 KB), so **the PVC held the only
  copy of Arm B's KV-utilization, queue-depth and replica-count evidence** — precisely the data §15.16
  rests on. A reclaim-before-verify flow would have destroyed it.
* Arm A only *looks* correct because its post-run pipeline replaced these files with the PVC's.

Remediation applied to Arm B: PVC reports fetched to `pvc-original/` (6 files, byte-exact), 3 analysis
PNGs fetched and validated as real 2100×600 PNGs (`file`), token vector extracted, correction applied.

**Independent cross-check of the token vector:** extracted twice by different code paths — locally from
the host copy, and in-pod by harvest — both returning **7920 values, mean 511.8**, against the profile's
requested mean of 512. Also 7920 = Arm A's request count, one more confirmation the stimulus matched.

Follow-ups this adds: step_09's local report regeneration should be suppressed or its output treated as
non-authoritative (the PVC reports are the real ones); `verify_pvc_vs_host.py` should gate every harvest,
not just be available to it.

### 15.10 inference-perf output-token inflation: concrete evidence for the upstream issue

The corrected host report now states the root cause and magnitude in machine-readable form — this is the
evidence to attach to an inference-perf issue:

```
source: vllm usage.completion_tokens
extracted_from: per_request_lifecycle_metrics.json (streamed, 7920 values)
reason: inference-perf output_len re-tokenizes generated text; inflated with random
true_output_len_mean: 512.356
reported_output_len_mean: 917.097
inflation_factor: 1.79
n_requests: 7920
fields_rescaled: [output_token_rate, total_token_rate,
                  normalized_time_per_output_token, time_per_output_token,
                  inter_token_latency, output_length (recomputed)]
```

`true_output_len_mean` 512.356 against the profile's requested mean of 512 is the correctness check on
the correction itself. The inflation is ~1.79× on random-token data, and it propagates into every
throughput and per-token latency field — which is why the uncorrected numbers cannot be compared across
runs. Not yet filed upstream.

**Flap is currently masked, not absent.** The 17:14:20 `tgt:1` did not take effect — decode read
`SPEC 2 / READY 2 / AVAIL 2` well after that cycle. HPA's scale-down stabilization window is absorbing
the chatter. That is worth stating plainly: the controller's *decisions* flap at steady load and only
downstream damping hides it.

**maxReplicas=2 is binding at 12 RPS as designed** — 17:19:21 shows `rc 473.19` with the target already
at the cap, i.e. TA wants more and is held. Expected, not a defect; noted so the cap is not
misread as a plateau in the plot.

Not treated as an abort: the run is harmless and the complete trace is the evidence. Do **not** attribute
any of this to a specific commit yet — in particular PR-2's C10 (`DefaultKSat` mirroring the wrong
constant) is recorded as sub-1% in effect and does not explain a 2.3× `prc` swing.

### 15.6 Run parameters — deliberate deltas from the 08-03 baseline

- **`maxReplicas` kept at 2.** Dean's 08-03 note said raise it and add a ~8 RPS step; that is the next
  *science* run. This run's value is being comparable to the baseline, which ran 5→12→5 against max 2
  and produced the clean 1→2→1. Raising it would make the anchor trace differ for a reason that is not
  the refactor, and would need more reserved H100s on a shared cluster. Both arms share the cap, so the
  A/B is internally consistent. **Raise it for the follow-up run, not here.**
- **`--wait-timeout 2400`** pinned explicitly (default is now 7200). Matches the baseline and bounds the
  blast radius — a long hang is how 08-03's truncation started.
- **`--analyze` now on** (`BENCHMARK_ANALYZE=true` default, absent on 08-03). Kept: post-processing
  only, does not touch workload or scaling trace. Side effect: it writes `analysis/` *after* collection,
  which is exactly §13's second finding, so **run `fetch_missing_from_pvc.py` after each arm**.
- Workload `ta_autoscale_staircase.yaml.in`: 3 stages × 360s = **18 min of load**, `base_seed: 42` fixed
  → both arms generate a byte-identical request stream. Selected via the scenario's
  `harness.experimentProfile`, so **no `-w` flag** (matches 08-03's blank `-w` slot).
- `sync_workloads.py` is why the clone holds only `ta_autoscale_staircase.yaml.in` and no rendered
  `.yaml`: step_05 prefers `.yaml`, so a stale rendered sibling would silently shadow an edited
  template and is deleted. It also *asserts* the named profile resolves — fails fast, not 18 min in.

### 15.7 GPU pre-reservation

`hack/benchmark/gpu-reservation.yaml` applied (`registry.k8s.io/pause:3.9`, 1 GPU, H100 nodeSelector,
namespace hardcoded to `dhl-wva-209`); holder Running on `pokprod-b93r44s0`. Coupler started with
`MAX_ITERS=700` (~58 min, sized for one arm). Small edit to `gpu-reservation-coupler.sh`: `HOLD_TOTAL` /
`MAX_ITERS` / `POLL` are now `${VAR:-default}` so an arm can raise the cap without editing the file —
**`NS` and `DECODE` left hardcoded on purpose, they are the blast-radius guard, not a knob.** Script is
not chmod +x; invoke as `bash gpu-reservation-coupler.sh`. Stop via `touch /tmp/stop-gpu-coupler`.

### 15.8 Arm A in flight

Run dir `dean-20260807-201009-695`. Invocation:
`make benchmark-run BENCHMARK_NAMESPACE=dhl-wva-209 BENCHMARK_SPEC=guides/wva-sat2-tp1
BENCHMARK_WAIT_TIMEOUT=2400`.

Cold-resume order after Arm A: (1) `verify_pvc_vs_host.py` **before anything deletes**, (2)
`fetch_missing_from_pvc.py` for the `analysis/` gap, (3) `harvest_run.py`, (4) cool to 1 replica, (5)
Arm B = `make benchmark-set-analyzers WVA_ANALYZERS=saturation` (restarts the controller, de-registers
TA) then the identical run command.

## §16 Ladder run 2026-08-07 — 8-stage ladder with the replica cap raised to 10

Full analysis lives in `session-notes/scratch/ladder-run-findings.md`. This section records
what was run, what the run produced, and what is still open. **It is the first run in this
campaign to observe the complete scale-up *and* scale-down path with a non-binding cap.**

### 16.1 What ran

| | |
|---|---|
| run dir | `dean-20260807-234050-328` (local 23:40 = 20:40 UTC) |
| profile | `ta_autoscale_ladder` — 8 x 300 s at 2, 5, 8, 10, 12, 15, 20, 2 RPS |
| controller | `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9-anchor-20260807` |
| running digest | `sha256:ab4c8503df58fb20b7c17c735af2d452f64208fdd2a7b9d354efd73f66c87a13` |
| analyzers | `saturation` + `throughput` |
| replica cap | **1..10** (raised from 1..2, which bound on the 08-07 A/B pair) |
| namespace | `dhl-wva-209` |
| load window | 20:42:36Z -> 21:22:36Z (41:09), 22,200 requests, **zero failures** |

`300 x (2+5+8+10+12+15+20+2) = 22,200` — the request count reconciles exactly, so no stage
was dropped or truncated.

### 16.2 Outcome

Scaling: 1 -> 3 (spurious, cold `prc`) -> 2 -> 3 -> 4 -> 1. The engine's decision rule was
reconstructed from the analyzer payloads and **verified against 65/65 cycles** (37 of them
inside the load window; the other 28 are the post-run idle tail and are trivially satisfied) by
`verify_decision_rule.py`, which exits non-zero on mismatch and is therefore reusable as a
regression check on the decision arithmetic across controller images:

    rc = demand/0.85 - supply    if rc > 0:  tgt = curr + ceil (rc/prc)
    sc = supply - demand/0.70    if sc > 0:  tgt = curr - floor(sc/prc)
                                 else:       tgt = curr
    combine: max over analyzers, clamped to [minReplicas, maxReplicas]

Headline result, client side: **latency is monotone in per-replica load and non-monotone in
RPS** (8 RPS was slower than 10 RPS). Dividing by the time-weighted replica count each
stage actually ran on removes every exception. Two stages at equal per-replica load
(3.57 vs 4.00) land 0.9% apart in mean latency despite 1.5x different absolute load — the
per-replica capacity model WVA is built on is empirically sound, and the non-monotonicity
is entirely attributable to replica allocation.

Costs quantified:

* cold-`prc` spurious scale-down cost stage 2 **~18% mean latency for a full 5 minutes**
* scale-up lag at 20 RPS cost **31% mean / 53% p95** for the 90 s the fleet was short
* of that 90 s, **only ~30 s is WVA's** (control interval); ~60 s is pod startup

### 16.3 Two defects that need a decision (neither acted on)

1. **Harness OOM — reproducible.** The harness pod was OOMKilled at 21:30:09Z (exit 137,
   32Gi limit) *after* all load completed, while serialising
   `per_request_lifecycle_metrics.json`. File is 0 bytes. This will recur on any long run
   with `report.request_lifecycle.per_request: true` — 22,200 records exceeded 32Gi. Needs
   a memory bump or per-request capture disabled for long runs. **Run-config change, not
   made unilaterally.**
2. **PVC has no buffer in front of it.** The harness writes its report *directly* to the
   20 Gi PVC (`/requests/<run>_1`), not to node ephemeral storage with a later copy. A
   successful run of this size needs ~11.9 GB of PVC headroom. The PVC stayed at 308 M
   here only because the file was never written. The pre-run space check is therefore
   load-bearing, not advisory.

Recovery: no measurement was lost, only per-request resolution. All 8 stage aggregates and
the summary survived, and server-side token truth was recovered from 650 vLLM scrapes
(`server_token_truth.py`).

> **SUPERSEDED by §17.** This section originally called per-request distributions/CDFs and
> per-request correlation unrecoverable. They are not: the inference gateway's access log
> yields a complete per-request trace for all 22,200 requests, with arrival, duration,
> response size and the serving pod. Per-request TTFT and exact per-request token counts
> remain lost. The two defects above still need the same decisions regardless — the gateway
> log is a fallback, not a reason to leave the OOM in place.

### 16.4 inference-perf output-token defect — now bounded, supersedes §15.10

§15.10 recorded the inflation as a ~1.78x factor. The per-stage data shows the error is
**per-request heterogeneous**, not a scalar. The profile pins output length to `[480, 550]`,
yet reported `output_len` minima/maxima run from **3 to 3186** — a per-request error
spanning ~0.006x to ~6.2x — and the mean factor drifts 1.69–1.80 across stages.

Server-side control: harness *input* accounting is accurate to **0.06%** (18,421.77 vs
18,411.0 tok/s), so the defect is specific to counting generated tokens. Server output
511.5 tok/req vs the profile's 512 confirms `ignore_eos` works.

Consequence for every past and future run on this harness: `time_per_output_token`,
`inter_token_latency`, `normalized_time_per_output_token` and `output_len` are **unusable at
any percentile**. `request_latency`, TTFT, `requests_per_sec` and input-side throughput are
unaffected. The only defensible per-token figure is the aggregate
`(mean latency - mean TTFT) / true tokens`, mean only.

### 16.5 Post-run state (as left)

* **GPUs released.** Coupler stopped; `gpu-reservation` scaled to 0 at ~21:46Z, freeing 4
  GPUs — ~16 min after the harness died, per the 15-minute idle rule. Only the decode
  replica's 1 GPU remains, which is the stack's `minReplicas=1` steady state, not an
  idle-hold artifact. **Tearing the serving stack down was deliberately NOT done.**
* Background monitors stopped: PVC space guard, controller log tail.
* **Harvest was already complete before I touched it.** The harness post-run step had
  pulled `dean-20260807-234050-328/results/<run>_1/` — 709 files, all 465 decode scrapes,
  count-verified equal to the PVC. My hand-harvest into
  `session-notes/scratch/ladder-run/` was therefore redundant (and 2 scrape files short,
  because `kubectl cp` of the whole run dir fails partway on this PVC with
  `unexpected EOF`). Both produce byte-identical token totals; prefer the run dir. Lesson
  for the harvest path: **check the local run dir before fetching from the PVC.**
* PVC **not** cleaned; nothing deleted. PVC at 296M used / 20G avail — enough headroom for
  the next run, which needs ~11.9 GB if per-request capture stays on. `verify_pvc_vs_host.py`
  has not been run. Note the usual `correct_output_tokens.py` path cannot run on this run —
  its input is the 0-byte file.
* New analysis tools, all in `session-notes/scratch/`: `verify_decision_rule.py`,
  `server_token_truth.py`, `stage_table.py`, `stage_vs_replicas.py`, `watch_pvc_space.sh`.
  Candidates for promotion into `hack/benchmark/`.
* **Nothing pushed.** WVA branch still ahead 2 (`c3c5aa20`, `361cfe77`); the fork's
  modified `output_token_correction.py`, the `Makefile`, `.env`,
  `ta_autoscale_ladder.yaml.in`, coupler edits, `hack/benchmark/` scripts and all
  `session-notes/` work from this run are uncommitted or unpushed, awaiting per-push
  confirmation.

## §17 Per-request trace recovered from the gateway; two analysis errors of mine corrected (2026-08-08)

§16.4 recorded `per_request_lifecycle_metrics.json` as a 0-byte OOM casualty and the
per-request layer as lost. **It is not lost.** Every request traversed the inference gateway,
and istio-proxy's access log was captured into `logs/igw_pods.log` by the normal harness log
dump. It holds one line per request for all 22,200, and it is a *better* trace than the file
that died:

* **Wall-clock UTC, millisecond resolution.** The lost file used a monotonic clock with an
  unknown origin that had to be hand-anchored against the run log. Envoy needs no anchor, so
  per-request data joins directly to controller logs and HPA events.
* **`UPSTREAM_HOST`** — which decode pod served each request. The harness file never had
  routing attribution at all.
* **`bytes_sent`**, a tokenizer-independent response-size proxy, immune to the output-token
  defect in §16.4.

Not recovered: per-request TTFT and exact per-request output-token counts. Envoy sees one
duration per request, not the token stream. Those survive only as server-side histogram
buckets in `metrics/raw/*_metrics.log`.

Validated six independent ways: exact count identity (22,200 in-window POSTs vs 22,200
harness successes); aggregate mean duration 8817 ms vs 8850 predicted from the surviving
stage aggregates (0.37%); per-stage means within 0.4% at all eight stages; `bytes_sent` p50
implying 511 output tokens against a true mean of 512 (0.2%); envoy's 8025 requests for
decode-97vw2 against vLLM's own 8026 for the same pod; and per-stage routing counts
reproducing the fleet timeline derived from the controller log.

Tool: `session-notes/scratch/envoy_per_request.py`
(`--stage-grid` / `--csv` / `--jsonl` / `--by-pod` / `--rotation-budget`).

### 17.1 Durability: this source is subject to kubelet log rotation

Raised by Dean, and it turned out to matter. The access log is the gateway container's
stdout, so it is bounded by kubelet log rotation.

> **CORRECTED 2026-08-08 (Dean asked whether we can process before rotation).** This section
> originally said the budget was `containerLogMaxSize` × `containerLogMaxFiles` ≈ 52 MB at the
> kubelet defaults, unverified. Both factors were wrong, and **they cancelled exactly**, so the
> number came out right while the model behind it did not. Now verified, read-only, from
> `kubectl get --raw /api/v1/nodes/<node>/proxy/configz`:
>
> | | as recorded | verified |
> |---|---|---|
> | `containerLogMaxSize` | 10Mi (assumed default) | **50Mi** |
> | files reachable via `kubectl logs` | 5 | **1** |
> | budget | 52.4 MB | **52.4 MB** |
>
> The single-file limit is documented, not inferred — the Logging Architecture page states
> *"Only the contents of the latest log file are available through `kubectl logs`"*, with the
> worked example that a pod writing 40 MiB under a 10 MiB rotation yields at most 10 MiB.
> `containerLogMaxFiles: 5` governs what survives **on disk**, which we cannot reach without
> node filesystem access we do not have and should not take. Also verified:
> `containerLogMonitorInterval: 10s`, `containerLogMaxWorkers: 1`.
>
> Two other claims in this section were wrong and are fixed below: the gateway pod is **in our
> own namespace**, not shared cluster infra; and eviction is a **cliff, not a slope**.

The gateway pod — `infra-llmdbench-inference-gateway-istio-…`, in **`dhl-wva-209`**, 8d old
with 0 restarts — is long-lived and accumulates *every* run: 5,002 access lines on 07-30,
15,081 on 08-03, 38,093 on 08-07. Being in our own namespace matters for the fix: a follower
needs only a namespace-scoped Role here, no cluster-scoped grant and nothing outside our NS.
(The harness reads it with `kubectl logs -l app.kubernetes.io/component=inference-gateway
--namespace <ours>`, `kube_helpers.capture_label_logs`.)

Measured 2026-08-08: **27.1 MB / 58,479 lines** reachable, oldest line the pod's own boot at
`2026-07-30T16:48:43` — so **nothing has rotated yet**. `kubectl logs` strips the CRI wrapper
(~40 B/line: RFC3339Nano timestamp + ` stdout F `) that does count against the on-disk cap, so
the file is near **29.5 MB, ~56%** of 52.4 MB. At ~506 B/request on disk (the 541 B/line
recorded earlier was measured on the harvested file, which carries a 75 B `--prefix` string
that is *not* on disk) that leaves roughly **45,000 requests — about two more ladder runs**.

**Eviction is a cliff, not a slope**, and the original wording understated it badly. Rotation
does not trim the oldest lines from a single growing file; it starts a new file, and
`kubectl logs` can only see that one. So at the instant of rotation the retrievable log drops
discontinuously to a nearly-empty file. A rotation landing mid-run leaves only the run's
**tail**; one landing just after a run leaves essentially **nothing**. The bias is still
against the start of the window — the low-rate stages and the initial scale-up, the most
valuable region for autoscaling analysis — but the loss is total, not marginal.

Worse, the failure is silent. Stage assignment partitions the sorted arrival series on
cumulative per-stage counts, which is *positional*, so a truncated series does not lose the
early stages — it **shifts all of them**. Deleting 2.2% of requests from the front and
re-partitioning gives stages 2–5 at 8.07/10.01/11.90/15.04 RPS against a configured
8/10/12/15 — entirely plausible — while sitting 62 s off, with stage 5's `dur_p95` reading
15.192 s against a true 10.351 s. A 47% error with no local symptom.

So `assign_stages` **hard-fails** on the count identity rather than warning. The identity is
a sound completeness test because the harness independently reports how many requests it
issued. `--rotation-budget` measures bytes/request from the log itself and reports headroom.

One thing the cliff does *not* threaten: the harvested copies. Each `igw_pods.log` is a
cumulative snapshot of the whole growing log, so the 31.5 MB one from 08-08 00:30 is a superset
containing every run to date. The history is already safe on local disk under the 14-day
retention rule; the exposure is entirely about *future* runs.

**Operational consequences.** Item 3 is now done (see the correction above); 1 and 2 remain.
1. Run `--rotation-budget` *before* every run, alongside the PVC space check. Its arithmetic
   should be updated to the verified single-file 50Mi budget and the on-disk wrapper.
2. Capture the access log continuously *during* the run instead of relying on the post-run
   dump. Three shapes, in preference order:
   * **Follower** — `kubectl logs -f --timestamps` started before the run, streaming to the
     PVC. Must run **in-cluster**, not from the client, per Dean's standing rule for the
     GPU-release process (*"it should free them even our client is down"*). Caveat kept
     explicit: whether a `-f` stream survives a rotation is **not documented** — the kubectl
     reference is silent and the Logging Architecture page does not address it. The supervisor
     makes it moot: on exit, restart with `--since-time=<last line seen>`. `--timestamps` is
     what supplies that watermark, so rotation-survival stops being load-bearing.
   * **Polling** — periodic `--since-time` snapshots with overlap and dedup. Robust by
     construction: at 20 RPS the log grows ~10 KB/s, so a fresh 50Mi file takes ~84 min to
     fill; a 60 s poll can lose at most 60 s, and only if a rotation lands in that window.
   * **Zero-code mitigation** — delete the gateway pod well *before* a run (ours, our NS) to
     reset the log to zero, buying a full 52.4 MB ≈ 100k requests. Disruptive (brief data-plane
     gap), so never during a run, and it needs Dean's OK.

   Either way the count-identity gate stays as the acceptance test — it is what converts a
   silent truncation into a hard failure.

   **Rejected:** reconfiguring istio access logging or the `Telemetry` API to ship to a sink.
   Architecturally the clean answer, but `istiod` lives in shared `istio-system` and it changes
   the behaviour of a component we did not author, mid-experiment.
3. ~~Verify `containerLogMaxSize` / `containerLogMaxFiles`~~ — **DONE 2026-08-08**, see the
   correction block above. Method note: this was a read-only cluster-scoped GET on
   `nodes/<node>/proxy/configz`, which an earlier revision of this section had declined. Judged
   worth doing once Dean asked specifically about rotation limits; it turned two assumptions
   into numbers. No writes outside `dhl-wva-209`.

### 17.2 My 52-second anchor error, and what it cost

The §16 headline table joined per-stage latency to a time-weighted replica count. I anchored
the stage windows on the run log's `All pods are running` at 20:42:36. **The first request
actually arrives at 20:41:44.330** — the anchor was 52 s late, and every boundary was shifted
by up to 17% of a stage's length. The replica weights, and therefore every per-replica load
figure in the headline, were wrong.

The correct derivation needs no anchor: partition the sorted arrival series on the configured
cumulative counts. Observed rates then reproduce the ladder — 1.95, 4.87, 7.76, 9.69, 11.66,
14.52, 19.32, 2.01 against 2, 5, 8, 10, 12, 15, 20, 2.

Corrected in `ladder-run-findings.md` and in `stage_vs_replicas.py`, which now imports the
grid instead of carrying an anchor constant. Run duration also corrected: **41:02**
(20:41:44.330 → 21:22:46.271), previously reported as 41:09.

### 17.3 The replica denominator was also wrong, for a second and independent reason

`curr` from the controller log is the wrong denominator for a latency model, and not only
because it is sampled at 60 s. It is the replica count the **workload object** carries, which
includes pods that are Pending, pulling an image, or loading the model — pods contributing to
the count while supplying zero capacity. Backwards for explaining latency.

Routing settles it without the controller: a replica is serving when the gateway is sending
it requests, and `UPSTREAM_HOST` records that per request. `serving_replicas.py` derives each
pod's serving interval and time-weights it per stage:

| pod | first request | last request | requests |
|---|---|---|---|
| decode-97vw2 | 20:41:44.330 | 21:22:46.271 | 8025 |
| decode-wf2rf | 20:44:27.832 | 20:51:34.146 | 599 |
| decode-db6cw | 20:46:14.429 | 21:20:31.875 | 7351 |
| decode-qqbbn | 20:57:25.119 | 21:20:32.120 | 5489 |
| decode-k9hkl | 21:15:28.325 | 21:20:34.887 | 736 |

The two estimates agree within 0.10 replicas on six of eight stages — the cross-check that
matters. They diverge where the fleet was in motion: stage 0 serving **1.59** vs `curr` 2.27
(the initial ramp; `curr` overstates by 43% because most counted replicas had not finished
loading) and stage 6 serving **3.45** vs 3.61 (k9hkl counted from 21:14:39, serving nothing
until 21:15:28). Note wf2rf — the replica the cold-`prc` cascade killed — served only 599
requests in its entire 426 s life, corroboration from a third direction that it never carried
a fair share.

### 17.4 What the corrections did to the findings

Two of the three §16 client-side conclusions got **stronger**; one gained a genuine exception;
one supporting mechanism was replaced.

* **Per-replica capacity model — stronger, and now assumption-free.** Under the corrected
  weights stage 2 (8 RPS ÷ 2.00) and stage 4 (12 RPS ÷ 3.00) land on *exactly the same*
  4.00 RPS/replica, with mean latencies 0.9% apart (7.711 vs 7.781) across a 1.5× difference
  in absolute load. Previously this was "within 5% on per-replica load". No interpolation is
  involved now. That the two came out equal to three digits is luck, but it makes the
  comparison clean.
* **Non-monotonicity in RPS is the autoscaler's doing — unchanged.**
* **Monotonicity in per-replica load — now has one real exception.** Stage 0 carries 68%
  *more* per-replica load than stage 7 (1.26 vs 0.75) yet is 2.6% *faster* (5.404 vs 5.546).
  Both sit far below saturation where latency is per-token decode cost rather than queueing.
  Read the curve as flat below ~1.3 RPS/replica and monotone above it; the six points from
  stage 1 up are strictly ordered. The wrong grid had concealed this.
* **Scale-up lag decomposition — replaced.** §16 reported a ~90 s stage-6 window of which
  ~30 s was WVA's, that 30 s being half the 60 s optimisation interval. Measured properly:

  | component | measured | duration | owner |
  |---|---|---|---|
  | load steps 15 → 20 RPS | 21:12:37.229 | — | workload |
  | controller emits `scale-up` 3 → 4 | 21:13:39 | **61.8 s** | WVA |
  | new pod serves its first request | 21:15:28.325 | **109.3 s** | HPA + scheduler + vLLM load |
  | | | **171.1 s** | |

  The conclusion "about a third is WVA's" survives (62 of 171 s) — but the mechanism does
  not, and the difference matters for tuning. **A cycle ran at 21:12:39, 1.8 s after the load
  step, and did not detect it**: it reported throughput demand of 6597 tok/s, *below* the 7793
  the previous cycle saw at stage 5's steady state. The next cycle at 21:13:39 saw 10918 and
  fired immediately. So halving `GLOBAL_OPT_INTERVAL` would have recovered **nothing** here —
  a cycle 1.8 s after the step already existed and was blind. The binding constraint is
  upstream of the optimiser, in scrape lag and rate-window width. This is a sharper form of
  the same conclusion: the `prc` fix is the larger lever.

  **Open question, not a finding:** whether that blindness is scrape lag, the collector's
  rate-window width, or sampling noise. The 6597 reading is low enough that noise is likely
  part of it. Separating them needs a run with the scrape interval and rate window recorded
  and varied.

The `prc` mechanism findings in §16.1–16.3, the 65/65 decision-rule verification, and the
output-token defect in §16.4 are all untouched by this — none of them depend on stage windows.
The ~18% cold-`prc` latency penalty also survives unchanged: the counterfactual recomputes to
~6.5 s on the corrected curve.

### 17.5 Which vLLM histograms are worth using (reusable, not run-specific)

Triaged before promising anything to the viz work, because bucket resolution decides whether
a server-side histogram can substitute for a lost per-request field. Boundaries are fixed by
vLLM, so this carries to every run on this image:

| metric | boundaries | verdict |
|---|---|---|
| `vllm:time_to_first_token_seconds` | 0.02, 0.04, 0.06, 0.08, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5 s | **usable** — 8 boundaries inside the observed 0.03–0.34 s range; a genuine distribution-level replacement for per-request TTFT |
| `vllm:e2e_request_latency_seconds` | … 2.5, 5, 10, 15, 20 s | **too coarse** — the whole observed 5.4–12 s range spans three buckets; envoy's exact per-request ms is strictly better |
| `vllm:request_generation_tokens` | 200, 500, 1000 | **bounding only** — cannot show shape, but decisive for §16.4: every request lands in (200, 1000], refuting the harness's reported max of 3186 |

`vllm:request_queue_time_seconds` and `vllm:num_requests_waiting` are the direct measure of
under-provisioning harm and have **no equivalent anywhere in the harness output** — worth
capturing deliberately rather than incidentally.

Two logs were eliminated as per-request sources, with evidence, so nobody re-checks them:
the EPP log carries only 13 `x-request-id` lines across 418 s (note the field is
`x-request-id`, hyphenated — a bare `request_id` grep returns nothing and looks like absence),
and the modelserving log covers 39 s, entirely before load started.

### 17.6 Handoffs delivered

Both now relayed to `plans/session/handoffs/` (verified byte-identical to the worktree
copies). The earlier one had `state: sent` in its frontmatter but had **never actually been
copied** — zero `scratch-poc__` files among 225 in that directory. Worth remembering as a
failure mode: frontmatter is not delivery.

* `scratch-poc__per-request-fetch-for-viz.md` — the pre-existing fetch recipe. Its §5 "clock
  trap" section is the anchor recipe that §17.2 corrects.
* `scratch-poc__ladder-run-surviving-data.md` — what survives, how to parse it, the rotation
  caveat, and the corrected per-replica curve.

### 17.7 State as left

* New tools in `session-notes/scratch/`: `envoy_per_request.py`, `serving_replicas.py`;
  `stage_vs_replicas.py` corrected. Promotion candidates for `hack/benchmark/` alongside the
  §16.5 list.
* **No cluster writes this session.** Four read-only lookups when Dean asked about rotation:
  `get pods -l …inference-gateway -n dhl-wva-209`, two `kubectl logs` reads of that pod, and one
  cluster-scoped `get --raw …/proxy/configz`. Everything else was already-harvested local data.
  Serving stack still up in `dhl-wva-209`, GPUs still released, decode at `minReplicas=1`.
* PVC still not cleaned (296M / 20G); `verify_pvc_vs_host.py` still not run.
* **`session-notes/` is now committed** — `9e360b18` (37 files, +13783) and `4157dce2` (§16.3
  pointer + §17.5). Two `.gitignore` gaps had to be closed first, one of them latent and
  expensive: the existing `*-*-*-*-*-*/` pattern needs **five** hyphens, and our run directories
  are `dean-<date>-<time>-<pid>/` with **three**, so they were never ignored. A future
  `git add -A` would have committed 100+ MB per run. Now `dean-*/`, plus
  `session-notes/scratch/ladder-run/` (harvested copies, 14-day local retention) and
  `__pycache__/`.
* **Nothing pushed.** Branch `benchmark` is **4 ahead** of `origin/benchmark`: `c3c5aa20`,
  `361cfe77`, `9e360b18`, `4157dce2`. Each needs its own explicit confirmation from Dean.

### 17.8 Open items carried forward (consolidated — this is the resume list)

Needs Dean's decision:

1. **The harness OOM** (§16.3) — memory bump vs `per_request: false`. Should be filed as a
   reproducible defect. The gateway trace removes the *analysis* dependency but not the bug.
2. **How to capture the gateway access log during runs** (§17.1) — in-cluster follower with a
   `--since-time` watermark supervisor (preferred), periodic polling, or the zero-code
   pod-delete reset. **More urgent than it looked yesterday:** rotation is a cliff rather than a
   slope, and the measured headroom is ~45,000 requests — about **two more ladder runs**. Today
   the trace survives only because no rotation has fired since the pod booted on 07-30; that is
   luck, not a design. The pod-delete reset also needs Dean's OK in its own right (brief
   data-plane gap, ours and in-NS, never during a run).
3. **Scale the decode replica to 0?** Its 1 GPU is still held as the `minReplicas=1` steady
   state (§16.5). The serving stack was deliberately left up.
4. **The unpushed commits above.**

Doable without a decision, not yet done:

5. ~~Verify `containerLogMaxSize` / `containerLogMaxFiles`~~ — **DONE 2026-08-08**: 50Mi × 5,
   and the reachable budget is ONE file. See the correction block in §17.1;
   `--rotation-budget` now implements the verified model and its byte accounting.
6. Clean the PVC per the retention rule, and run `verify_pvc_vs_host.py` (never yet run) —
   §16.5 wants it gating **every** harvest, not run ad hoc.
7. File the inference-perf output-token inflation upstream (§16.4), now with server-side proof.
8. Promote the `session-notes/scratch/` tools into `hack/benchmark/` (list in §16.5 + §17.7).
9. Suppress step_09's local report regeneration (§15.17); add controller-log capture to the
   harvest path; fix `reset_run.py`'s existence-check defect; §11 design-C Makefile change; the
   `variant.VariantAutoscaling` event-recorder issue.
10. Fix `verify_decision_rule.py`'s last-wins overwrite of same-second analyzer payloads
    (§17.9). Latent — it does not change this run's 65/0/22 — but it is the defect I just fixed
    in `analyzer_presence.py`, and the next run may not be as lucky about arrival order.

Open questions the data cannot settle:

11. Which of scrape lag / rate-window width / sampling noise makes the optimiser blind 1.8 s
    after a load step (§17.4). This is the one that decides whether the 62 s WVA share of the
    171 s lag is reducible at all.

### 17.9 Were BOTH analyzers enabled and actually deciding? Yes — and here is the census

Dean asked this directly, and it is worth more than a yes: every conclusion in §15–§17 rests on
the run being a genuine two-analyzer run. Two separate things have to hold, and they are
answered by two different pieces of evidence.

**(a) Configured and registered.** The controller log carries the startup gate's positive
branch verbatim:

```
20:20:34.826  INFO setup cmd/main.go:535  ThroughputAnalyzer registered (enabled in saturation config)
```

`cmd/main.go:throughputAnalyzerEnabled` gates registration on a saturation-config entry naming
`throughput` with `enabled != false`, and the negative branch logs a *distinct* message
("ThroughputAnalyzer NOT registered — no saturation config entry enables 'throughput'"). That
string appears **0 times** in the log, so this is a positive identification, not an absence of
evidence. Saturation needs no such line: it is intrinsic to `saturation.NewEngine` and exempt
from the gate (`engine_v2.go:196`), so a running engine *is* a running saturation analyzer.

I initially reported there was no registration line. That was a grep error on my part —
I searched for `analyzers`, and the line says `ThroughputAnalyzer`. The line was there all
along, on line 34 of the log.

**(b) Actually deciding, per cycle.** Registration is necessary but not sufficient: the engine
also applies a per-cycle `effectiveEnabled` opt-in per namespace/model, and separately an
analyzer can emit a payload it cannot act on. `session-notes/scratch/analyzer_presence.py`
censuses this from the controller log. **"Logged a payload" is weaker than "was
decision-capable"** — a payload with `variants: []` carries no `prc`, so it cannot produce a
replica claim and cannot influence the max-over-analyzers combine, even while plainly enabled:

```
95 cycles

window payload from             prc from                  dec    n  first -> last
idle   -                        -                          no    5  20:23:34 -> 21:45:42
idle   saturation+throughput    saturation                yes   22  20:20:34 -> 20:41:36
idle   saturation+throughput    saturation+throughput     yes   24  21:23:41 -> 21:46:43
load   -                        -                          no    3  20:44:36 -> 21:15:39
load   saturation+throughput    saturation+throughput     yes   41  20:42:36 -> 21:22:40

  saturation   payloads   87   with prc   87   of those in load window   41
  throughput   payloads   87   with prc   65   of those in load window   41
  BOTH         decision-capable in the same cycle   65
```

The load window is the gateway trace's own first→last arrival (20:41:44 → 21:22:46), not the
run log's 20:42:36 — see §17.2. Reading:

- **In the load window both analyzers were decision-capable in 41 of 41 payload-bearing
  cycles.** No cycle under load had only one analyzer able to claim replicas.
- TA's 22 `prc`-less cycles are **all** in the cold prelude, 20:20:34 → 20:41:36, i.e. before
  the first request at 20:41:44.330. That is the known idle-TA shape: with no traffic there is
  no throughput observation to build a `prc` from. It is the same cold-`prc` effect as the ~18%
  latency finding, seen from the config side.
- 65 both-capable cycles = 41 load + 24 idle tail, which reconciles exactly with
  `verify_decision_rule.py`'s **65 matched / 0 mismatched / 22 skipped** (it skips a cycle
  unless *both* analyzers have a `prc`). So the verified decision rule was validated on the
  both-capable set specifically, and the 22 skips are accounted for rather than unexplained.
- 8 cycles (5 idle, 3 load) carry only an empty-`decisions` payload — no analyzer output at all.
  Not investigated; they are not gaps in the two-analyzer claim, since no decision was made.

**A defect in my own census, found and fixed.** The raw log has 108 `"analyzer": "throughput"`
payloads but only 87 cycle slots. Keying by `(timestamp, analyzer)` and assigning therefore
silently kept whichever payload arrived *last* — an analyzer can emit more than one payload
inside the same one-second timestamp, and TA does so in **21** cycles (all in the post-load
idle tail 21:26:41 → 21:46:43, each a `variants: 0` payload beside a `variants: 1` one). The
first answer I computed was correct only by ordering luck; a `variants: []` payload arriving
second would have masked a real one and *understated* TA's participation. The tool now retains
every payload for audit and prefers the decision-capable one explicitly.

`verify_decision_rule.py` has the identical last-wins overwrite. It is unaffected here — the
duplicates all sit in the idle tail where the real payload happens to arrive second — but it is
the same latent defect and wants the same three-line fix. Carried as an open item.
