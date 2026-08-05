reason: code-review-before-push
refs:
  - ta-model-level-demand/ (worktree)
  - planning/ta-model-level-demand-review.md
  - session/status/ta-model-level-demand.md
  - session/handoffs/plan__ta-model-level-demand-f3.md
note: Stack rebased onto upstream/main dfc21e2c; tip b2acffd6 (6 commits). C.1/C.2 comments (94accd09) and F3 §4a cleanup (b2acffd6) added since last review. F3 touched 14 C-introduced plans-branch identifier sites (comment/test-desc only, no logic change); status file lists each site. Two pre-existing upstream §4a refs (dev-guide:671, test:1189, from #1250) left untouched and tracked as out-of-scope. All gates green (build/gofmt/vet/lint/throughput+saturation tests); DCO on all 6. Not pushed.
