from: benchmark
to: plan
session: benchmark

## What happened

`m-ta-calibration-probe`'s harness pod (`inference-perf-2z4j84hn`) got `OOMKilled` after ~16 min,
first attempt, at a 32Gi pod memory limit. Profile: `ta_calibration_probe.yaml.in` — ~4096in/~1024out
tokens, load ramping 2→20 req/s across 8 stages (~12 min total), `per_request: false` (already
disabled per the standing per-request-collection decision).

I initially misattributed this to the per-replica `kubectl logs --tail=-1` capture
(`capture_label_logs` in `llm-d-benchmark/llmdbenchmark/utilities/kube_helpers.py`, buffers the
full log history of every decode replica as one Python string before writing). Dean corrected this:
the total across all three per-replica log files was ~33MB — far too small to explain a 32Gi OOM on
its own. **The k8s log capture is very likely not the cause.** Dean's own suspicion: inference-perf
itself can't handle this workload shape/rate, and its scaling behavior generally is a concern worth
investigating properly rather than working around per-incident.

## What I've done (benchmark-tooling side, already committed/in progress — not what I'm asking you to redo)

- Kept per-replica k8s log collection running (per Dean's explicit instruction — "if it is not
  blocking then keep collecting and gzipping") but gzip-compressed it
  (`capture_label_logs` now writes `<name>.gz` via `gzip.open`, bounded to `--tail=20000`/pod as
  cheap hygiene, not claimed as an OOM fix). Updated `process_epp_logs.py`'s two read sites and its
  file-discovery logic to transparently handle `.gz`. Both files compile; not yet verified against a
  fresh completed run.
- Retrying the cell now with the gzip fix in place (the current in-flight attempt actually started
  *before* the fix landed, so it's not yet a real test of anything). Per Dean's fallback ladder: run
  with zipped logs → if it fails, bump harness pod memory → if that doesn't help either, move on to
  the next queued cell and report.
- Did NOT re-add a 32Gi→64Gi memory bump I'd tentatively added and then backed out — it was tied to
  the (wrong) log-capture root-cause theory, not to independent evidence, so it shouldn't carry
  forward without a better basis.

## What Dean wants investigated (this handoff — please look at the code, not just the docs)

1. **How does inference-perf itself scale under load, and does it fit what we're asking of it?**
   `num_workers: 224`, `worker_max_concurrency: 100`, `worker_max_tcp_connections: 2500` are the
   harness's own concurrency knobs (seen in this run's rendered config — `stdout.log` in the run
   dir). At ~4096in/~1024out tokens and rate ramping to 20 req/s, is inference-perf buffering
   full request/response payloads per in-flight request in a way that scales badly with token
   length × concurrency? Worth reading inference-perf's own source (upstream project, wherever it's
   vendored/installed in the harness image) for how it holds request/response state, not just
   inferring from symptoms.
2. **Vital-signs monitoring while it runs.** Dean wants to actually watch the harness pod's
   resource usage live during a run (not just infer from a post-mortem `OOMKilled` status), so a
   memory/CPU trend can be correlated with load-ramp stage transitions. Is there already a hook for
   this (the existing `collect_metrics.sh`/Prometheus scrape only covers vLLM pods, not the harness
   pod itself, as far as I've seen) or does something need adding to the harness-pod side of the
   toolchain?
3. **Multi-harness-pod flags.** Dean recalls the benchmark tooling (llm-d-benchmark, not our
   scenario file) has flags to start more than one harness pod for a run, not fully coordinated
   with each other. Worth finding what that actually does (parallelism? independent load
   generators hitting the same target?) and whether it's relevant here — e.g. spreading load
   generation across multiple smaller pods instead of one big one, which might sidestep a
   single-process memory ceiling regardless of root cause.
4. **Whether our own playbook should generate load directly**, for more control over the request
   mix (e.g. genuinely mixed request shapes within one run, not just picking one profile) instead
   of going through inference-perf's config surface at all. This is a bigger direction question,
   not a quick code read — flag it as open rather than trying to resolve it in this handoff.

## Not mine to resolve

This needs actual code reading (inference-perf's memory model, the harness-pod resource-monitoring
gap, the multi-pod flags) and probably a design opinion on (4) — outside a live coder session's
scope, especially with Dean going to sleep. I'm continuing to run the queued cells in the meantime
per Dean's fallback ladder (gzip → memory bump → move on and report), so whatever you find can
inform tuning for the *next* round of runs rather than blocking tonight's.

## References

- `session/status/benchmark.md` §20.29-30 for the postprocess.py/GPU-idle work earlier today.
- `hack/benchmark/m-ta-calibration-probe.env`, `llm-d-benchmark/workload/profiles/inference-perf/ta_calibration_probe.yaml.in`
  for the exact load shape.
- `runs/dean-20260812-203217-894/` — the first (OOM'd) attempt's full artifacts, including
  `stdout.log` (rendered inference-perf config with the concurrency knobs) and
  `logs/pod_status.txt` (the `OOMKilled` status line).
