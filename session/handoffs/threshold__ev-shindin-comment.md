reason: re-read plan
refs:
  - multi-analyzer-threshold/ (worktree)
note: one unresolved ev-shindin inline comment on PR #1228 — fix before push-ready trigger. File: internal/engines/analyzers/saturation_v2/analyzer.go lines 404-406. Two duplicate opening comment lines on aggregateByRole; keep only the second ("groups variant capacities by role and returns per-role / Total* aggregates..."), drop the first ("groups variant capacities by P/D role and computes per-role"). One-line delete, commit, push.
