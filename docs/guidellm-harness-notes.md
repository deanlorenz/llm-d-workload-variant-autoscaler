# guidellm / load-harness notes

## RESOLVED — run the benchmark via the `llmdbenchmark` CLI (NOT the hack script)

The 0-load failure (runbook §10b) had one cause: **`HF_TOKEN` was not forwarded to the harness
pod**, so guidellm got a 401 fetching the gated-model tokenizer and emitted no load while the pod
looked "running". Fix = pass `-g HF_TOKEN`. Canonical run command:

```bash
# GPUs first: oc scale deploy/unsloth--faee1c5b-a-3-1-8b-decode{,-v2} -n dhl-wva --replicas=1
llm-d-benchmark/.venv/bin/llmdbenchmark \
  --spec guides/two-variant-wva --workspace "$PWD" --base-dir "$PWD/llm-d-benchmark" \
  run -p dhl-wva -l guidellm -w wva_decode_steps.yaml -g HF_TOKEN
```

Note `-w` needs the **`.yaml` suffix** (`wva_decode_steps.yaml`, not `wva_decode_steps`) — step 05
`render_profiles` looks for `<name>` then `<name>.in`, and the file is `wva_decode_steps.yaml.in`.

`-g HF_TOKEN` verified: secret `llm-d-hf-token` → `HF_TOKEN` in process env → `harness_envvars_to_pod`
(cli.py:831) → injected into pod (`step_07_deploy_harness.py:278`); gated tokenizer then loads (no 401).

### ✅ WORKAROUND APPLIED — pin harness image to v0.6.1 (guidellm 0.5.4)
Root cause (below): guidellm **0.6.0** (harness image v0.6.3+) defaults to `/v1/chat/completions`
and ignores the scenario's `request_type` → 400 on the base model (no chat template) → 0 load.
guidellm **0.5.x** honors `request_type: text_completions` → `/v1/completions` → works.

Image→guidellm map (from upstream `build/Dockerfile` ARG GUIDELLM_BRANCH):
`v0.6.1`→guidellm v0.5.4 ✓ (last 0.5.x) · `v0.6.2`/`v0.6.3`+→guidellm v0.6.0 ✗ · current default `v0.6.7`→0.6.0 ✗.

**Fix (in `config/scenarios/guides/two-variant-wva.yaml`, `shared.images.benchmark.tag`):**
```yaml
  images:
    benchmark:
      tag: v0.6.1
```
Verified via `run --dry-run`: harness pod renders `ghcr.io/llm-d/llm-d-benchmark:v0.6.1`.
Editing the harness *script* / ConfigMap does NOT work — the guidellm invocation is baked into
the image (see below); only the image tag matters.

**TODO — open an upstream llm-d-benchmark issue:** the harness's `guidellm-llm-d-benchmark.sh`
does not pass `--request-format` on guidellm 0.6.0, and the profiles still use the legacy
`request_type` field that 0.6.0 ignores → any fresh install (guidellm 0.6.0) silently delivers 0
load on text-completion (base) models. Fix options upstream: pass `--request-format` derived from
the profile's `request_type`, or pin guidellm, or document.

### ⚠️ Original 0-LOAD analysis — second blocker inside guidellm (2026-06-15 verify)
With `-g HF_TOKEN` + correct `-w`, guidellm fully initializes (tokenizer loads, backend /health
validated, logs "starting benchmarks") but **delivers 0 requests** (vLLM running=0,
request_success_total=0). The stack is NOT at fault — verified healthy:
- gateway `/v1/completions` → HTTP 200 + generated tokens; DIRECT to vLLM `:8000` → HTTP 200 too;
  namespace `dhl-wva` correct, no cross-ns dupes.
So the 0-load is guidellm's request dispatch in this harness build. To root-cause: re-run WITHOUT
`--disable-progress` to see where it stalls, or try `-l inference-perf` (the scenario's default
harness). Evidence: `results/20260615-172902-hftoken-verify/`.

**Two-variant guidellm workload profiles** (`llm-d-benchmark/workload/profiles/guidellm/`):
- `wva_decode_steps` — open-loop `rate:[4,16,4]` RPS, 360s, prompt 256±64 (64–512), output
  2048±256. Stepped + *varied* prompts (diverse prefixes) — the proper benchmark.
- `wva_gentle` — constant 16 RPS, prompt 4096±2048, output 1024±512 (large prompts → KV pressure).

These have real RPS + IL/OL distributions — use them instead of the custom curl loadgen, which
had none and maximized prefix-cache hits (skewed KV low; see RESULTS.md / COMPARISON.md).

**Do NOT use `hack/benchmark/run/run_ci_benchmark.sh`** — it targets the old `setup/standup.sh`
+ `run.sh` llm-d-benchmark layout, which biranofer's `feat/multi-variant-benchmark` branch
replaced with the `llmdbenchmark` CLI. It cannot run against the current clone.

Permanent option: bake `HF_TOKEN` into the scenario's harness env-forward list so `-g` isn't
needed each time (key maps to `harness_envvars_to_pod` / `LLMDBENCH_HARNESS_ENVVARS_TO_YAML`).

---

## Original investigation notes (kept for reference)

Context: two `llmdbenchmark … run` invocations with guidellm deployed the harness pod, reported
"running", but Thanos showed **0** requests/KV/gen-tokens on both vLLM pods (runbook §10b).

## How the harness is selected and run
CLI: `llm-d-benchmark/.venv/bin/llmdbenchmark --spec guides/two-variant-wva --workspace $PWD --base-dir $PWD/llm-d-benchmark run -p dhl-wva [flags]`

Relevant `run` flags (`llmdbenchmark run --help`):
- `-l, --harness {inference-perf, guidellm, vllm-benchmark, inferencemax, nop}`
- `-w, --workload <profile>.yaml`     — load profile (IL/OL/rate/prefix); e.g. `sanity_random.yaml`
- `-e, --experiments <file>`          — overlay that sweeps a profile parameter (e.g. concurrency)
- `-o, --overrides`                    — comma-separated profile param overrides
- `--dataset-url`                      — dataset to replay
- parallel harness pods, completion-wait seconds, etc.

**The two-variant-wva scenario's default harness is `inference-perf`** (`two-variant-wva.yaml`
line ~267: `harness: { name: inference-perf }`). guidellm is the alternate (`-l guidellm`).

## Where load shapes (IL/OL/prefix/rate) are defined
- Per-harness profiles: `llm-d-benchmark/workload/profiles/{guidellm,inference-perf,vllm-benchmark,inferencemax,nop}/`
- Experiment overlays (sweeps): `llm-d-benchmark/workload/experiments/` —
  `max-concurrency-sweep.yaml`, `precise-prefix-cache-aware.yaml`, `tiered-prefix-cache.yaml`,
  `optimized-baseline.yaml`, `pd-disaggregation.yaml`.
  These are exactly the **IL/OL distribution + prefix-cache + concurrency/rate** knobs we want
  (e.g. `precise-prefix-cache-aware` / `tiered-prefix-cache` control prefix reuse; the sweep
  files step concurrency). The custom curl loadgen has none of these — see RESULTS.md.
- Harness driver scripts: `llm-d-benchmark/workload/harnesses/` —
  `guidellm-llm-d-benchmark.sh`, `inference-perf-llm-d-benchmark.sh`,
  `vllm-benchmark-llm-d-benchmark.sh`, `collect_metrics.sh`, `process_metrics.py`,
  `process_epp_logs.py`. **`guidellm-llm-d-benchmark.sh` is the script that actually launches
  guidellm inside the harness pod — start here for the 0-load root cause.**

## What to check for the 0-load failure (hypotheses)
1. **Target URL / model name mismatch** — does the harness point at the gateway
   (`infra-llmdbench-inference-gateway-istio.dhl-wva.svc:80/v1/...`) with model
   `unsloth/Meta-Llama-3.1-8B`? A wrong base-URL or model id → guidellm starts but every
   request 404/connection-refused (and may swallow errors while looking "running"). Compare to
   the working in-cluster curl in runbook §13.1.
2. **Tokenizer / dataset init stall** — §10b suspected guidellm hung in tokenizer or dataset
   download (HF). Check the harness pod logs for a tokenizer/`datasets` download step that never
   completes; confirm `HF_TOKEN` is present in the harness pod env.
3. **Rate/profile producing ~0 RPS** — a constant-rate profile with a tiny rate, or a
   max-seconds=0, would emit ~nothing. Inspect the rendered profile the harness used.
4. **Harness pod readiness vs run start** — §10b: pod sat in "Waiting for pods to complete".
   Check whether the run phase actually started (guidellm process spawned) vs just the pod
   scheduled.
5. **Try `inference-perf` instead** — it's the scenario default and may avoid the guidellm
   path entirely. `-l inference-perf -w <profile>`.

## Concrete commands to investigate
```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark
BIN=llm-d-benchmark/.venv/bin/llmdbenchmark
# 1. dry-run to see the rendered harness/workload without launching
$BIN --spec guides/two-variant-wva --workspace "$PWD" --base-dir "$PWD/llm-d-benchmark" \
   run -p dhl-wva -l guidellm -w sanity_random.yaml --dry-run
# 2. inspect the guidellm launcher + a profile
sed -n '1,120p' llm-d-benchmark/workload/harnesses/guidellm-llm-d-benchmark.sh
ls llm-d-benchmark/workload/profiles/guidellm/
# 3. when a real run is going, tail the harness pod
oc logs -n dhl-wva -l <harness-pod-label> -f      # find label via: oc get pods -n dhl-wva | grep -i harness
# 4. sanity: the stack itself serves (bypass harness) — runbook §13.1 in-cluster curl → HTTP 200
```

## Recommendation
Don't reimplement guidellm with curl (the custom loadgen lacks RPS/IL/OL/prefix control and its
identical-prompt traffic maximizes prefix-cache hits, skewing KV low — see RESULTS.md
limitations). Fix `guidellm-llm-d-benchmark.sh` / the profile, or switch to `inference-perf`,
so we get controlled IL/OL distributions, prefix-reuse, true RPS, and per-request latency
metrics — the inputs needed for analyzer-score-vs-load studies.
