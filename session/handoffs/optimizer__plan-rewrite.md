reason: re-read plan after architectural rework
refs:
  - planning/multi-analyzer-optimizer-plan.md
  - session/handoffs/plan__optimizer-pd-design.md
note: P/D design discussion settled on paired allocation (commit (n_P, n_D) per step) rather than role-budget split. Stashed 1.4 work should be `git stash drop`-ed; new 1.4 is paired helpers + CostAware disaggregated path. 1.5 is fresh Greedy migration (both paths). 1.6 is cleanup. Existing 1.1/1.2/1.3 commits stay.
