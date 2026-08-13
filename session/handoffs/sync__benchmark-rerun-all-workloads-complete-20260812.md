from: benchmark
to: sync
session: benchmark

**Ref:** `session/status/benchmark.md` §20.31 (full detail).

**Resume prose:**

Processed the planner's `benchmark__rerun-all-workloads-fill-panel-gaps-20260812.md` handoff (now
`.DONE`): reran the 4 workload cells with real panel gaps. All landed, GPUs freed at the end.

- **`m-ta-calibration-probe`** — first attempt OOMKilled at 32Gi after 16 min. Root cause NOT
  confirmed (I initially guessed the per-replica k8s log capture; Dean caught that the actual
  per-replica log total was only ~33MB, far too small to explain a 32Gi OOM — corrected per his
  direction to keep collecting but gzip, not disable). Retry succeeded unmodified (same 32Gi) —
  P99 TTFT 20,088ms, ITL 136.79ms/token, 0 errors. Both attempts committed as separate data points
  (`fbc42741` OOM, `09055f56` success) per "I want data from all cases." Filed a planner handoff
  (`plan__inference-perf-scaling-and-oom-investigation-20260812.md`) on the real open question:
  inference-perf's own memory behavior under this token volume/rate, live vital-signs monitoring
  for the harness pod, and the multi-harness-pod / direct-load-generation questions Dean raised.
- **`m-ta-dwell`** (`5cb8eb97`) — full 40-min rerun, clean, replaces a previously truncated/unusable
  attempt.
- **`m-satta-dwell`** (`e1fdf31f`) and **`m-sat-dwell`** (`f1a39bc5`) — both completed cleanly, no
  retries needed. `m-sat-dwell` shows notably worse tail latency than the TA cells (P99 TTFT
  91,712ms, queue depth 32.4) — confirms, doesn't newly discover, the campaign's known
  saturation-only-analyzer-lags-demand finding.

**Side fixes, in a separate git repo (not this branch — flagging so it isn't missed):** the nested
`llm-d-benchmark` clone's `kube_helpers.py`/`process_epp_logs.py` now gzip-compress and transparently
read per-replica pod logs; not committed there this session, just edited on disk.

GPUs freed and verified at the end (ScaledObject paused at 0, decode at 0 replicas, 0 pods). 5 new
commits on `benchmark`, all local, DCO-signed, **not pushed** this round (last push was earlier
tonight, before this round started).

**Owed by Dean:** whether/when to push this round's 5 commits; whether to act on the
inference-perf-scaling planner handoff now or later (not urgent — GPUs aren't blocked on it).

**CURRENT.md update suggested:** note the 4-cell rerun completed, the calibration-probe OOM (cause
unconfirmed, forwarded to a planner handoff), and point at §20.31 rather than restating detail.
