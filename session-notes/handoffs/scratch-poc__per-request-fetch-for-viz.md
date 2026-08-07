---
to: scratch-poc
from: benchmark (ta-benchmark-coder, worktree `benchmark`)
date: 2026-08-07
subject: How to fetch the per-request data from the 08-07 A/B runs, and plot it with viz
state: sent
---

# Per-request data from the 2026-08-07 A/B autoscaling runs

Two real staircase runs landed today on pokprod (`dhl-wva-209`), same stimulus, differing only in
whether the ThroughputAnalyzer was registered. This is the "our OWN runs, re-fetch full per-request"
path the viz plan wanted — the full per-request traces exist, with per-token timings.

I am the benchmark runner. I cannot write outside my own worktree, so this handoff was generated in
`benchmark/session-notes/handoffs/` and copied into place. Everything below is verified against the
actual files unless explicitly flagged as unverified.

---

## 1. TL;DR — Arm A needs no fetch at all

Arm A's per-request file is **already on this machine**:

```
dean-20260807-201009-695/results/inference-perf-1786122657-k0ezvy_1/per_request_lifecycle_metrics.json
4,234,888,579 bytes  (4.2 GB)
```

Paths are relative to the benchmark worktree
(`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark`).

**Do not delete this file.** Its PVC-side reclaim is an open decision escalated to Dean and
deliberately declined for now *because* viz wants the full trace. If it disappears, re-fetching costs
a 4.2 GB transfer (§3).

**Arm B is now also fully local** (its pipeline ran after this was first drafted):

```
dean-20260807-210058-612/results/inference-perf-1786125698-ptufog_1/per_request_lifecycle_metrics.json
4,208,275,298 bytes  (4.2 GB)
```

Both arms verified **byte-identical to the PVC** (242/242 and 281/284 files; Arm A's 3 "differing" files
are its v0.2 reports, which are *larger* on host because the token correction was applied locally — that
is the intended end state, not damage). So §3 is a recovery procedure you should not need.

## 2. Run identifiers

| | Arm A (TA on) | Arm B (TA off) |
|---|---|---|
| run dir | `dean-20260807-201009-695` | `dean-20260807-210058-612` |
| experiment | `inference-perf-1786122657-k0ezvy_1` | `inference-perf-1786125698-ptufog_1` |
| controller image | `@sha256:d6456071…` (anchor) | same |
| analyzers | saturation + **throughput** | saturation only |
| load window (UTC) | 17:14:20 → 17:32:2x | 18:02:19 → 18:20:19 |
| workload profile | `7e0935fee1789c6dd97fbaf213bbe86d` | **byte-identical**, `base_seed: 42` |

Both arms drew the same request stream — profile hashes match and the seed is fixed. That is what makes
an A/B overlay meaningful rather than suggestive.

Stages are 3 × 360 s: **5 RPS → 12 RPS → 5 RPS**. Arm A measured 4.94 / 11.74 / 4.93 with 0 failures
in 7920 requests.

## 3. Fetching from the PVC (only if you need Arm B, or lose the local copy)

Namespace is `dhl-wva-209` in every command. The PVC is reachable through a long-lived data-access pod:

| | |
|---|---|
| pod | `access-to-harness-data-workload-pvc` |
| container | `rsync` |
| mount | `/requests` |
| PVC path pattern | `/requests/<experiment>/per_request_lifecycle_metrics.json` |

### 3.1 Use `exec -- cat`, not `kubectl cp`

`kubectl cp` is tar-over-exec with **no resume and no verification** — on a 4.2 GB file over a shared
cluster a truncated transfer looks exactly like a successful one. Use the existing script, which streams
via `kubectl exec -- cat` and verifies the byte count against what the PVC reports, writing to a
`.partial` file and renaming only on an exact match:

```bash
python3 session-notes/scratch/fetch_missing_from_pvc.py --apply     # ns/pod/container are baked in
```

Its safety property, which matters if you re-run it: files whose sizes **differ** are reported and
skipped, never overwritten. `--overwrite-mismatched` exists but wants a stated reason.

The equivalent by hand, if you want one file and nothing else:

```bash
kubectl -n dhl-wva-209 exec access-to-harness-data-workload-pvc -c rsync -- \
  cat /requests/inference-perf-1786125698-ptufog_1/per_request_lifecycle_metrics.json \
  > per_request_lifecycle_metrics.json.partial
# then compare byte counts before renaming -- do not skip this
kubectl -n dhl-wva-209 exec access-to-harness-data-workload-pvc -c rsync -- \
  find /requests/inference-perf-1786125698-ptufog_1 -name per_request_lifecycle_metrics.json -printf '%s\n'
```

### 3.2 Check space first

PVC is 20 GB. As of 18:20Z: 4.2 GB used, 16 GB free. Arm A's trace is 4.0 GB of that; four older
experiments total only 194 MB (their big files were reclaimed in earlier passes). Projected steady state
with Arm B is ~8.2 GB (~41 %).

```bash
kubectl -n dhl-wva-209 exec access-to-harness-data-workload-pvc -- df -h /requests
```

## 4. Record schema — what is actually plottable

The file is a **pretty-printed JSON array**, one object per request, in submission order. Verified shape:

```json
{
  "start_time": 3288816.111055578,
  "end_time":   3288828.897207489,
  "request": "{\"model\": \"unsloth/Meta-Llama-3.1-8B-Instruct\", \"prompt\": \" ...2000 tokens... \"}",
  "info": {
    "input_tokens": 2042,
    "extra_info": {},
    "lora_adapter": null,
    "response_info": {
      "response_chunks": [],
      "chunk_times": [3288818.406480164, 3288818.40656677, ...],
      "server_usage": {"prompt_tokens": 2042, "total_tokens": 2522, "completion_tokens": 480}
    }
  },
  "error": null
}
```

Notes that will save you time:

* **`chunk_times` is the per-token arrival series** — ~480–550 entries per request. This is the real
  prize for viz: TTFT is `chunk_times[0] - start_time`, and inter-token latency is its diff series.
  Note the values repeat in runs of 2–3 identical timestamps (visible at the file tail), so treat
  equal-timestamp neighbours as one arrival event rather than zero-latency tokens.
* **`server_usage.completion_tokens` is the TRUE output length.** Do not use any `output_len` derived by
  inference-perf: it re-tokenizes generated text and inflates ~1.8× (§6).
* `response_chunks` is empty — the generated text is not retained per chunk.
* `error: null` on every record in Arm A (0 failures).
* The 4.2 GB is mostly escaped prompt text plus `chunk_times`; there is no compact subset already
  extracted. If you only need token counts, `hack/benchmark/completion_tokens_scan.py` streams them
  in constant memory and reduces 4 GB to ~40 KB — it is designed to run *in-pod* so only the vector
  crosses the wire.
* **Do not `json.load()` this file.** The existing `per_request_plots.py` does, and silently OOM-skips.
  Stream it (`ijson`, or chunked regex as `completion_tokens_scan.py` does).

## 5. The clock trap — read this before plotting anything against controller decisions

`start_time`, `end_time` and `chunk_times` are a **monotonic clock, not wall-clock epoch.** First record
`start_time` is `3288816.111` — roughly 38 days, i.e. node uptime in seconds. Wall-clock epoch would be
~1.786e9. Every autoscaling artifact you will overlay (controller logs, HPA events, `kubectl` timestamps)
is wall-clock UTC. They do not share an origin.

Anchor recipe, and I validated the arithmetic:

```
span = max(end_time) - min(start_time) = 3289918.904 - 3288816.111 = 1102.79 s
```

against 3 × 360 s = 1080 s of configured load. The 22.8 s excess is ramp plus the drain of in-flight
requests at the end — so the monotonic series really does cover exactly the load window, and:

```
wall(t) = load_start_utc + (t - min(start_time))
```

Take `load_start_utc` from the harness log's `All pods are running` line:

| | load start (UTC) | source |
|---|---|---|
| Arm A | **17:11:11Z** | run log, `All pods are running` |
| Arm B | **18:02:19Z** | run log, `All pods are running` |

For Arm A, `run_metadata.yaml`'s `harness_start` is 17:11:10Z — within **1 second** of actual load start,
so anchoring to it is fine in practice. The asymmetry is at the *other* end: `harness_stop` is 17:32:36Z,
i.e. `harness_delta` 1286 s against 1102.8 s of load, so **~3 minutes of report-writing sits after the
last request**. Anchor to the start, never to the stop or to the midpoint of the two.

Derived stage boundaries for Arm A: 5 RPS 17:11:11–17:17:11, 12 RPS 17:17:11–17:23:11, 5 RPS
17:23:11–17:29:11 (last request drains ~17:29:34).

Sanity check any anchor you derive by confirming the implied stage boundaries land where the request
rate actually steps (5→12 at +360 s, 12→5 at +720 s).

## 6. Token inflation — correct before plotting throughput

inference-perf's `output_len` is re-tokenized generated text and, with random prompts and `ignore_eos`,
inflates. Measured on Arm A across the three stages:

```
true_output_len_mean:      512.4  (from vllm usage.completion_tokens, 7920 values)
reported_output_len_mean:  917.1 / 921.7 / 933.5
inflation_factor:          1.790 / 1.799 / 1.822
```

Any output-token-derived metric inherits this — token rate, TPOT, normalized time per output token. The
corrected reports carry the provenance (`extracted_from: sidecar server_completion_tokens.json`). Per-run
extracted vector: `<run>/results/<experiment>/server_completion_tokens.json` (~32 KB).

Unverified, offered as a lead rather than a finding: the factor does **not** track load — stage 2 is
5 RPS like stage 0 yet has the highest factor — which points at something cumulative in the
re-tokenization path. An upstream inference-perf issue is planned; three points on one run is thin.

## 7. Autoscaling overlay — the controller trace is NOT in the harness output

Two things to know before you build the replica-vs-load panel.

**7.1 The harness does not capture controller logs.** I captured them by hand; they live under the
Arm A run dir for both arms:

```
dean-20260807-201009-695/wva-controller-arm-a.log            (646 lines, Arm A window)
dean-20260807-210058-612/wva-controller-arm-b.full.log       (917 lines, Arm B pod lifetime)
```

Use the `.full.log` for Arm B — it is the complete controller lifetime (pod restarted 17:58:48Z for the
TA-off config, so nothing is missing), 71 `analyzer-result` / 71 `scaling-decision` lines, 1:1. It
supersedes the earlier 278-line `wva-controller-arm-b.partial.log`, which sat under Arm A's run dir by
mistake and covers only the load window.

Per-cycle lines you want, one per ~60 s reconcile:

```
saturation/engine_v2.go:681  analyzer-result    {"analyzer":"saturation","supply":329011,"demand":416065,
                                                "util":1.2646,"scaleUpThreshold":0.85,"scaleDownBoundary":0.7,
                                                "variants":[{"name":"...-decode-scaler","prc":329011,"reason":"P3-k2"}]}
saturation/engine_v2.go:730  scaling-decision   {"decisions":[{"name":"...","curr":1,"tgt":2,"action":"scale-up"}]}
```

Timestamps here are wall-clock UTC, so this is the series you anchor the monotonic per-request data
against (§5).

**7.2 The `observability` block in the stage reports is run-wide, not per-stage.** This one will bite.
Lines 2–475 of all three `benchmark_report_v0.2,_stage_N_...yaml` files are byte-identical
(md5 `3535b5c182cfe8de0956f03aca817ce4`), and `replica_status.timestamp` inside is `17:32:23Z` — the end
of the run, with `count: 82` samples spanning the whole thing. So:

* `request_performance` **is** genuinely per-stage — latency and request rate differ correctly.
* `observability` (KV utilization, ready pods, queue size, `replica_status`) is a single end-of-run scrape
  copied into each stage file.

**Do not cite the stage reports for per-stage utilization or per-stage replica counts.** Sourcing a
"KV util during the 5 RPS stage" number from them would be wrong. That evidence exists only in the
controller log's per-cycle `util`. Run-wide values, for reference: KV util mean 0.1567 / p99 0.4412;
ready pods mean 1.854 (min 1, max 2, n=82); queue size mean 0.0061.

If you want a genuine replica timeline, derive it from `scaling-decision` transitions in the controller
log, and note HPA's scale-down stabilization window delays the actual deployment change relative to the
decision.

## 8. What the two arms show, so your plots have something to say

| | first scale-up | landed in |
|---|---|---|
| 08-03 baseline | ~95 s in | 12 RPS |
| **Arm A** (TA on) | 69 s in | **5 RPS** |
| **Arm B** (TA off) | 50 s in | 12 RPS |

Arm A scaled up a full stage earlier than Arm B on identical stimulus, so TA is the differentiator. The
mechanism: the engine computes `ceil(demand / prc)` with no smoothing (confirmed for both analyzers), and
TA's per-replica capacity swings **1694 → 3849 (2.3×)** cycle-to-cycle at steady load, while saturation's
is pinned at 329011 in every single cycle.

**Keep three levels distinct — I conflated them at first and the numbers differ at each:**

| level | Arm A behaviour | where to read it |
|---|---|---|
| TA's own per-cycle target | `2,1,1,2,2,1,2,2` — reverses **4×** at constant load | `analyzer-result` lines, `analyzer:"throughput"` |
| emitted combined decision | reverses **2×** (up 17:12:20 → down 17:14:20 → up 17:15:20) | `scaling-decision` lines |
| actual deployment replicas | **never flapped** — 1→2 at 17:12:42, held 2 until 17:34:22 | `kubectl` / HPA events |

HPA's scale-down stabilization window absorbed the emitted reversal, so the instability is real in the
controller but did **not** reach the workload on this run. Do not plot TA's internal target as if it were
the replica count, and do not claim observed replica flapping — there wasn't any. The honest framing is
"TA scaled up a stage early, against no measurable pressure", not "TA thrashed the deployment".

**The outcome comparison points the opposite way from "TA scaled up needlessly", so please do not build
that chart.** Arm B's corrected reports (fetched after this handoff was first drafted) show what happens
*without* the early scale-up, at the 12 RPS stage:

| stage-1 metric | Arm A (TA on) | Arm B (TA off) |
|---|---|---|
| request latency p95 | 12.41 s | **86.53 s** |
| TTFT p95 | 0.340 s | **61.24 s** |
| KV util p99 (run-wide) | 0.4412 | **1.000 — saturated** |
| queue depth (run-wide) | 0.0061 | **44.17** |
| ready replicas p25/p50/p75 | 2.0/2.0/2.0 | **1.0/1.0/2.0** |

Delivered throughput was identical (11.74 vs 11.75 RPS, ~6015 output tok/s, 0 failures in 7920 requests
both arms) — the whole cost of under-provisioning landed on latency. So TA's early scale-up was
**protective on this workload**, and my earlier "queue averaged 0.006, so there was no pressure" reasoning
was circular: the queue was 0.006 in Arm A *because* TA had already scaled up. Arm B is the counterfactual.

The chart actually worth building is the **A/B latency overlay through stage 1** — same offered load, same
seed, replicas differing — with the replica step function underneath. That shows both true things at once:
TA acted early, and the arm that didn't act early paid 7× p95. The instability finding (`prc` 2.3× spread)
stands on its own as a correctness concern about *how* TA decides, and does not need a harm narrative.

Caveat worth carrying into any chart caption: the 08-03 baseline's `prc` history is **unrecoverable** (its
controller log was never captured), so "TA got worse in the refactor" is not established. A third arm on
the pre-refactor image is proposed and pinnable by digest (`@sha256:80dec0e9…`), awaiting go-ahead.

## 9. Files, in one list

| path | what |
|---|---|
| `<run>/results/<exp>/per_request_lifecycle_metrics.json` | 4.2 GB full trace, per-token `chunk_times` |
| `<run>/results/<exp>/server_completion_tokens.json` | ~32 KB true output-token vector |
| `<run>/results/<exp>/benchmark_report_v0.2,_stage_N_*.yaml` | corrected reports; per-stage perf, run-wide observability |
| `<run>/results/<exp>/pvc-original/` | uncorrected originals, for provenance |
| `<run>/results/<exp>/run_metadata.yaml` | harness start/stop, version, model, endpoint |
| `<run>/workload/profiles/inference-perf/ta_autoscale_staircase.yaml` | the stimulus (hash it to prove A==B) |
| `dean-20260807-201009-695/wva-controller-arm-a.log` | Arm A per-cycle decisions (hand-captured) |
| `dean-20260807-210058-612/wva-controller-arm-b.full.log` | Arm B, full pod lifetime, 71 cycles |
| `<run>/results/<exp>/pvc-original/` | **authoritative** PVC reports; the host top-level v0.1 files are locally regenerated and have `model.name: unknown` |
| `session-notes/scratch/fetch_missing_from_pvc.py` | verified PVC→host fetch |
| `session-notes/scratch/verify_pvc_vs_host.py` | name+size comparison; run before any delete |
| `session-notes/scratch/sample_report.py` | dependency-free cross-stage report sampler |
| `hack/benchmark/completion_tokens_scan.py` | in-pod streaming token extractor |

Ask me for anything missing — I still have the cluster in this state, so re-capture is cheap while it
lasts.
