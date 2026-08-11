to: benchmark
reason: re-read plan
refs:
  - planning/ta-pokprod-campaign-20260810-results.md § "`tput_knee()` and `capacity()` were never reviewed" — the three open design questions are Dean's to decide, not this trigger's to resolve; do not change either function's approach ahead of that review
  - planning/ta-pokprod-campaign-20260810-results.md § "Per-request data — disposition and discovery plan" — the exact field list and the four log sources to scan in full (not sampled)
  - planning/ta-pokprod-campaign-20260810-results.md § "Missing: a scaling-decision panel"
  - planning/ta-pokprod-campaign-20260810-results.md § "Coverage checks — undocumented"
  - planning/ta-pokprod-campaign-20260810-results.md § "Folder structure — where results live" — refines the tree in the prior trigger below (config/raw/viz coupled per run, not a separate campaigns-only split)
  - session/handoffs/benchmark__results-tree-and-campaign-persistence.md — the prior trigger this one refines, still open
note: EPP debug-log scorer output (kv-cache-utilization-scorer, prefix-cache-scorer, queue-scorer, per x-request-id, per candidate endpoint) was confirmed present in logs/epp_pods.log this session — a concrete, previously-unmined signal for the per-request discovery task and for question 2 in the capacity-model review section. Per-request collection in inference-perf is to be disabled going forward per Dean's decision; the discovery task is about finding fallback signal in logs already being collected, not adding new collection.
