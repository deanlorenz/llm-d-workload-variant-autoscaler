to: benchmark
reason: re-read plan
refs:
  - planning/ta-pokprod-history.md [[D-41]] (root cause), [[D-42]] (this finding — LLMDBENCH_HARNESS_LOAD_PARALLELISM, confirmed real and current on upstream main, and why it must be paired with a rate-divided workload variant, not used as-is)
  - session/handoffs/plan__inference-perf-oom-root-cause-found-20260813.md (item 3's original "found nothing" answer — corrected by this handoff)
note: |
  Dean confirmed: divide the load across N parallel harness pods, not multiply it. The flag exists
  and is current — LLMDBENCH_HARNESS_LOAD_PARALLELISM, implemented in
  llmdbenchmark/run/steps/step_07_deploy_harness.py on upstream main (confirmed via GitHub code
  search + direct read of the implementation, read-only, not from the stale local llm-d-benchmark
  clone that missed it entirely first pass).

  Verified precisely what it does: spawns N pods (pod_name suffixed per-pod, results_dir suffixed
  "_1".."_N"), each running the SAME resolved workload profile unchanged — no rate-splitting logic
  anywhere in the implementation. So it multiplies aggregate offered load N×, it does not divide it.
  To actually divide the load (Dean's fix), the workload profile's own stage rates need dividing by N
  BEFORE setting the flag, so N pods' combined rate matches the original single-pod intent.

  Concrete first try for the stuck m-ta-calibration-probe cell, N=4: keep durations (90s/stage)
  unchanged, divide every stage's rate by 4 -- 2,4,6,8,10,13,16,20 -> 0.5,1,1.25(rounds from 1.0-1.75
  depending how 13/4 renders in inference-perf's config, use 3.25 exactly if the schema takes a
  float),2,2.5,3.25,4,5. Set LLMDBENCH_HARNESS_LOAD_PARALLELISM=4 for the run. Each pod's own
  MultiprocessRequestDataCollector only ever sees 1/4 the request volume, so the same 32Gi limit
  should tolerate the full 12-minute sweep without needing a memory bump. This is a genuine fix for
  D-41's mechanism, not a workaround -- each pod's accumulator stays smaller by construction.

  Verify against your own retry state before applying -- if the gzip/memory-bump fallback ladder
  already produced a completed run for this cell tonight, this is the next-cell or next-round
  improvement, not an urgent redo. If the cell is still stuck, this is the recommended next step
  ahead of a memory bump, since it addresses the actual mechanism rather than buying headroom against
  an unbounded-by-design accumulator.

  Not verified: whether the harness IMAGE currently in use (baked-in inference-perf + llm-d-benchmark,
  per hack/benchmark/.env:69) actually carries this feature -- it was merged to upstream main
  2025-11-21, so any image built before that date won't have it. Check the image's llm-d-benchmark
  version/build date before relying on this, not just the upstream source.
