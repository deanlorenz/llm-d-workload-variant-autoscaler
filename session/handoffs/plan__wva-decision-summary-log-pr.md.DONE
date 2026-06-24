from: benchmark
session: wva-decision-summary-log-pr

## Suggestion: small standalone PR — permanent WVA "decision summary" INFO log line

This scopes **Part 1** of `planning/benchmark-observability-plan.md` as its own small PR, off
`main` (NOT the `benchmark` experiment branch — this is a permanent WVA observability feature
and should land independently). Motivated by the TA benchmark this session: there is currently
**no way to read per-cycle analyzer/optimizer outputs** without scraping `--v=4` debug lines,
and per-analyzer SC/RC/PRC aren't emitted at all (the gap that blocked analyzer-score-vs-load
analysis).

### What the PR adds
One structured **INFO** line per reconcile cycle per model, message `"saturation cycle summary"`,
emitted after the optimizer produces per-variant decisions. Fields (model-level): `model`,
`analyzer`, `totalSupply`, `totalDemand`, `utilization`; plus a `variants[]` array with per
variant: `name, k1, k2, k2Source, cost, perReplicaCapacity, efficiency(=cost/perReplicaCapacity),
currentReplicas, targetReplicas, action`. Single-line JSON (survives `kubectl logs` truncation +
line-buffered grep). Full field spec + format example already in the plan (Part 1).

### Code paths (verified on the `benchmark` branch this session — please re-confirm on `main`)
- Model-level supply/demand/util are logged today at
  `internal/engines/saturation/engine_v2.go:67` (`"V2 saturation analysis completed"`).
- Per-variant action/target are logged at
  `internal/engines/saturation/engine.go:1591` (`"Applied saturation decision"`).
- `perReplicaCapacity` **is already in the analyzer result struct**
  (`internal/engines/analyzers/saturation_v2/analyzer.go:~397 PerReplicaCapacity:`).
- **Implementation fork (Part 1's open question, now sharpened):** `k2`/`k2Source` appear to be
  **analyzer-internal** — not currently returned to the engine. So either
  (a) emit the summary line **inside the analyzer** (has k2/k2Source, but may not have the final
  optimizer `targetReplicas`/`action`), or
  (b) **extend the analyzer result struct** with `k1/k2/k2Source` and emit the single INFO line
  **in the engine** after decisions (has action/target). (b) is cleaner — one emission at one
  scope with all fields — but costs a struct change. Coder should read both sites and pick.

### Two corrections to bake in (from this session's Arm A/B comparison — see
`benchmark/results/20260615-150601-armB-satv2-only/COMPARISON.md`)
1. **Logging lib is controller-runtime logr/zap, not slog.** The plan's Part 1 says "JSON via
   slog" in one place but its prereq reading correctly says logr/zap. Match the existing
   `logger.Info(...)` structured-field style; do not introduce slog.
2. **The `analyzer` field ("which analyzer drove the decision") must reflect reality.** The
   scale-up driver in practice is **sat_v2's role-aware pipeline** (`pipeline/analyzer_helpers.go`
   `"joint role commit"`), confirmed reproducible with the throughput analyzer fully disabled.
   The field must not over-credit `throughput`/TA. If "driver" is hard to attribute cleanly,
   prefer naming the pipeline/optimizer rather than guessing an analyzer.

### Test + scope
- Unit test: marshal the emitted log line to JSON, assert all required keys present (per plan).
- Scope: ~1 code file + 1 test (+ possibly the analyzer result-struct field). Small, reviewable.
- Permanent line, stable schema; do not remove existing LEVEL(-4) lines.

## Also relevant to Parts 2/5/6 — reframe around the CLI, drop the hack script (Dean's call)
**Decision (Dean, this session): the benchmark is run only via the `llmdbenchmark` CLI, not via
`hack/benchmark/run/run_ci_benchmark.sh`.** That script targets the old `setup/standup.sh` +
`run.sh` llm-d-benchmark layout, which biranofer's `feat/multi-variant-benchmark` branch replaced
with the `llmdbenchmark` CLI — it cannot run against the current clone. So Parts 2/5/6, which were
written to extend that script, should be **re-scoped to the CLI** (or to thin wrappers around it),
not to `run_ci_benchmark.sh`. (My earlier hack-script edit was reverted; the script is untouched.)

**Part 6 (0-load) is fully resolved at the CLI level — no code/script change needed:**
add `-g HF_TOKEN` to the run call. Verified path: secret `llm-d-hf-token` → `HF_TOKEN` in process
env → `-g/--envvarspod` → `harness_envvars_to_pod` (cli.py:831) → injected by
`step_07_deploy_harness.py:278`. Canonical command + the two-variant guidellm profiles
(`wva_decode_steps`, `wva_gentle`, with real RPS + IL/OL distributions) are documented in
`benchmark/docs/guidellm-harness-notes.md`. Permanent option: add `HF_TOKEN` to the scenario's
harness env-forward list so the flag isn't needed each run.

So for the observability plan: **Part 6 = done (CLI flag, documented)**; **Parts 2/5 (in-flight
log capture + workload-validation gate) should target the CLI run flow**, not the hack script;
**Part 1 (this PR) is unaffected** — it's a WVA code change independent of how load is driven.

## Pointers
- Plan: `planning/benchmark-observability-plan.md` (Part 1 = this PR).
- Benchmark evidence motivating it: `benchmark/results/20260615-122758-ta-scaleup-retest/RESULTS.md`
  + `.../20260615-150601-armB-satv2-only/COMPARISON.md`.
