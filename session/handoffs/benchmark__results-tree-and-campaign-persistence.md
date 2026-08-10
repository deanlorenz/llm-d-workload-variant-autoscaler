to: benchmark
reason: re-read plan
refs:
  - planning/ta-pokprod-campaign-20260810-results.md — the 7-cell results write-up; § "Where the figures live" carries the current (non-canonical) figure locations and the gitignore hazard; § "Provenance and durability" carries the owed-by-whom table
  - planning/ta-pokprod-campaign-20260810-results.md § "⚠️ Two hazards before anything else" — the live OpenShift bearer token in all seven cells' run/*.yaml, and the retracted sat-disable headline
  - planning/ta-pokprod-testing-plan.md §2b Two-fork contract — what lives in WVA vs the harness fork
  - planning/ta-pokprod-testing-plan.md §2c Configuration contract — the fail-closed per-context .env, which the config paths below interact with
  - planning/ta-pokprod-testing-plan.md §9.1 Tooling track — T1–T11 owners
note: Dean settled the results-persistence layout 2026-08-10 (single benchmark/ tree, tools symlinked not moved, BENCHMARK_WORKSPACE relocated, campaigns tracked). The decisions and their rationale are in the results doc and the plan sections above; this trigger carries no instructions. Figures for all seven cells currently exist at dean-*/results/*_1/viz/ (gitignored) with a committed mirror at plans/scratch/campaign-20260810-viz/ — the mirror is the planner's, not canonical.
