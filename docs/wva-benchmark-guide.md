# WVA Autoscaling Benchmark — Our Guide

End-to-end guide for running the WVA autoscaling benchmark **as this branch actually does it**:
from a clean clone of the WVA repo to a completed run with analyzed results.

## Why this guide exists alongside the upstream one

`docs/developer-guide/two-variant-wva-benchmark.md` is the **upstream** guide, shared with the
llm-d project. It stays as upstream has it — we do not diverge from it, and this branch makes no
edits to it. This is a second, standalone guide, ours, that reflects the workflow we have
converged on. Where the two disagree, they are not in conflict: they describe different things.

What has drifted far enough to justify a separate document:

| Area | Upstream guide | This guide |
|---|---|---|
| Configuration | values passed on the command line / pinned in scenario yaml | a single fail-closed `.env`, keyed per kube context (§2) |
| Autoscaling path | KEDA `ScaledObject` throughout | WVA controller is the path under test; KEDA is present but see §8 |
| Analyzers | saturation V2 via configmap | saturation and throughput both live; explicit analyzer set (§5) |
| Cluster model | a cluster you own | a **shared** cluster, namespace-scoped, teardown gated (§1) |
| Post-run analysis | five dump/plot steps | the same steps plus a durable raw-log capture (§7) |
| Image under test | build from main | Tier-A image built elsewhere and pinned by tag (§3) |

The pokprod-specific operational detail — Dean's namespace, quay repo, Thanos URLs, the
`archive/benchmark-ta3-legacy` fallback — lives in
[`two-variant-wva-pokprod-runbook.md`](two-variant-wva-pokprod-runbook.md). That runbook is one
environment; this guide is the portable procedure. Read this first, then the runbook for the
environment you are on.

> **Status: NOT YET VERIFIED BY A CLEAN REFRESH.** Every step below was derived from a working
> setup, but the guide has never been executed from a clean clone start to finish. Until that test
> passes (§10), treat any step that fails as a **defect in this guide** first and a defect in your
> environment second.

---

## 1. Before you start — the constraints that are not negotiable

These come from the environment, not from preference. Violating them affects other people.

1. **The cluster is shared.** Every command carries an explicit `-n <namespace>`, including
   cluster-scoped reads. Never mutate cluster-global state (CRDs, SCCs, operators, quotas).
2. **Teardown is gated.** `make benchmark-teardown` and any delete of a shared object requires
   explicit per-action approval from the cluster owner. There is no "clean slate" reflex here.
3. **This cannot run on kind.** It deploys real `vllm-openai` on real GPUs and depends on
   `vllm:cache_config_info` reporting real KV memory. A GPU OpenShift cluster is required.
4. **The benchmark branch never carries WVA controller source edits.** The controller under test
   is always a pre-built image, pinned by tag (§3). If the controller must change, that change
   happens in a code worktree, is re-imaged, and arrives here as a new tag.

---

## 2. Configuration — one file, fail-closed

All environment-specific values live in `hack/benchmark/.env`. Nothing is hardcoded in the
scenario files, and nothing falls back to a default that would silently point at the wrong
cluster.

```bash
cp hack/benchmark/.env.sample hack/benchmark/.env
$EDITOR hack/benchmark/.env
```

The contract has two properties worth understanding before you edit it:

- **Fail-closed.** A missing required key aborts the target rather than substituting a default.
  This is deliberate: a default namespace or image tag on a shared cluster is how you deploy into
  someone else's space.
- **Keyed per kube context.** The `.env` records which cluster it is for, and the targets refuse
  to run if the current context does not match. Switching clusters means switching `.env`, not
  remembering to re-check.

`.env` is gitignored — it is per-operator, never committed.

Keys that decide what you are actually testing:

| Key | What it controls |
|---|---|
| `WVA_IMAGE_REPO` / `WVA_IMAGE_TAG` | the controller under test (§3) |
| `BENCHMARK_NAMESPACE` | your namespace — the blast radius of everything below |
| `BENCHMARK_MODEL_ID` | must be chat-template-bearing; see the note in §4 |
| `VLLM_IMAGE_REPO` / `VLLM_IMAGE_TAG` | vLLM version; older images do not emit the KV metric at all |
| `ACCELERATOR_NAME` | must match the GPUs actually in your nodes |
| `PROMETHEUS_URL` | where the signals are read from |

---

## 3. The image under test

The WVA controller image is built **outside this branch** and referenced here only by tag. Verify
what is actually running rather than trusting the pin:

```bash
make benchmark-record-images BENCHMARK_NAMESPACE=$NS   # read-only
```

This prints the images the live stack is running next to the `.env` pins, so a drifted deployment
is visible before you spend a run on it. Two failure modes it catches: a tag that was re-pushed
under you, and a stack still running the previous image because the rollout did not complete.

> **A new image is a new experiment.** When the controller image changes, the analyzer log format
> can change with it — which is exactly how the post-run extractor silently broke once (§7). After
> any image change, run §7's parse on a short run and confirm the analysis fields are populated
> before starting a long one.

---

## 4. Standup

```bash
make benchmark-install                                    # one-time: benchmark CLI
make benchmark-preflight  BENCHMARK_NAMESPACE=$NS         # read-only safety gate
make benchmark-standup-shared BENCHMARK_NAMESPACE=$NS     # shared-cluster-safe standup
```

Use `benchmark-standup-shared`, not `benchmark-standup`, on a shared cluster: it runs the
pre-flight gate first and skips the step that installs cluster-wide CRDs and SCCs. Plain
`benchmark-standup` assumes the cluster is yours.

`benchmark-preflight` is read-only and asserts every safety gate will hold. Run it first, always;
it is cheap and it is the only step that can tell you a run is unsafe *before* it starts.

> **The model must be chat-template-bearing.** Use an instruct/chat-tuned model. Current decode
> images ship transformers ≥ 4.44, which rejects a model whose tokenizer defines no chat template
> (i.e. base models) with `ChatTemplateResolutionError`, and every request errors.

---

## 5. Choose the analyzer set explicitly

Which analyzers are live determines what the run measures. Set it deliberately rather than
inheriting a default:

```bash
make benchmark-show-analyzers BENCHMARK_NAMESPACE=$NS
make benchmark-set-analyzers  BENCHMARK_NAMESPACE=$NS WVA_ANALYZERS=saturation,throughput
```

`benchmark-set-analyzers` edits only the analyzer list and leaves every other config key alone,
then restarts the controller.

> **Known limitation — saturation cannot currently be turned off by configuration.** Setting
> `saturation: {enabled: false}` is a silent no-op: the engine prepends the saturation result
> unconditionally. Any run described as "throughput alone" is really "throughput plus saturation".
> Design the comparison around that rather than around a switch that does not work.

---

## 6. Restart the controller before every run

```bash
make benchmark-restart-controller BENCHMARK_NAMESPACE=$NS
```

**This is a required step, not hygiene.** The controller keeps in-memory capacity history across
reconciles. Carried from a previous run, that history changes the per-replica-capacity the
optimizer computes, and the second run's decisions are then a function of the first run's load.
Two runs that differ only in leftover state are not an A/B comparison.

Also confirm the autoscaler is actually *armed*: if the `ScaledObject` was paused to release GPUs
between runs, un-pausing it is the first step. A paused autoscaler produces a flat replica trace,
which reads exactly like a legitimate "no scaling was needed" result and is very easy to
misinterpret as a finding.

---

## 7. Run, then capture the raw log before analyzing

```bash
make benchmark-run BENCHMARK_NAMESPACE=$NS
```

Then, **while the run window is still in the controller's log buffer**, save the raw log:

```bash
kubectl logs -n $NS -l app.kubernetes.io/name=workload-variant-autoscaler \
    --tail=200000 > controller-<run-id>.log
```

Do this before the analysis step, every time. Two independent things destroy this data otherwise:

- **Rotation** — `kubectl` only serves what the buffer still holds. Promptness handles this.
- **Format drift** — if the controller's log lines have changed shape, the extractor cannot parse
  them no matter how quickly you run it. Promptness does *not* handle this. A saved log can be
  re-parsed offline after the extractor is fixed; a lost window cannot be recovered at all.

Then analyze:

```bash
bash hack/benchmark/post_run_analyze.sh <results-dir> $NS
```

Check its step-1 output. If it prints `!!` warnings, the WVA timeseries is missing or carries no
analysis fields, and anything reading supply/demand/utilization is blind. Re-parse from the saved
log:

```bash
python3 hack/benchmark/dump_wva_target_timeseries.py <results-dir> \
    --log-file controller-<run-id>.log --no-window
```

The extractor exits non-zero and refuses to overwrite a good file when rows parse but carry no
analysis fields. That guard exists because this failure once wrote 41 healthy-looking rows with
every analysis field null, and the output was taken at face value.

Report and plot:

```bash
make benchmark-report          BENCHMARK_NAMESPACE=$NS
make benchmark-plot-two-variant BENCHMARK_NAMESPACE=$NS
```

---

## 8. The KEDA arm

The KEDA-only comparison arm exists in the harness but is **not currently runnable** — it has
known blockers recorded in the campaign plan. Do not schedule an A/B against it without checking
those first. The WVA path above is the one that works today.

---

## 9. What is worth capturing per run

So that a run is interpretable weeks later, and comparable against another:

- the `.env` used, and `make benchmark-record-images` output (what actually ran)
- the analyzer set (`make benchmark-show-analyzers`)
- the raw controller log (§7) — the single most recoverable artifact
- the offered load profile, and whether replicas were still lagging when it changed
- whether the `ScaledObject` was armed, and when the controller was last restarted

That last pair is not bookkeeping. A near-threshold dwell can be produced by replica *lag* rather
than by the offered rate, so a trace without the arming/restart context can support a conclusion
it does not actually license.

---

## 10. Clean-refresh test — how this guide gets verified

This guide's correctness claim is testable, and until the test passes the guide is provisional.

**The test:** from a clean clone of the WVA repo, on a GPU cluster, follow §2–§7 exactly as
written — no steps from memory, no commands not in this document — and reach an analyzed run.

Every stumble is a guide defect. Record each one and fix the guide, rather than working around it
in the shell:

- [ ] `.env.sample` copies to a working `.env` with no undocumented required key
- [ ] `make benchmark-install` succeeds on a clean clone
- [ ] `make benchmark-preflight` passes, and its failure message is actionable when it does not
- [ ] `make benchmark-standup-shared` brings up a serving stack
- [ ] a sanity request returns HTTP 200 and generated text
- [ ] the analyzer set can be read and set as §5 describes
- [ ] `make benchmark-run` completes and writes a results directory
- [ ] the raw controller log capture in §7 produces a parseable log
- [ ] `post_run_analyze.sh` reports step 1 populated, with **no** `!!` warnings
- [ ] `wva_target_timeseries.json` has analysis fields present, not null
- [ ] report and plot render

Two things this test is specifically looking for, because both have bitten us: a step that only
works because of state left behind by a previous run, and a step whose failure is reported as
success.
