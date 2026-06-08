reason: re-read plan
refs:
  - planning/TA-PR5-plan.md
note: Planner verified the optimizer/#1237 churn's impact on TA3 — see TA-PR5-plan § "Re-rebase impact analysis (verified 2026-06-09)" + §3.1. Summary: contract (interfaces) + aggregation are byte-identical to TA3's base, so analyzer.go needs no adaptation; #1237 is invisible to TA3; conflict surface is cmd/main.go only. H1 (RegisterAnalyzer error-return) is now CI-lint-blocking (errcheck under make lint, a required gate) and must be applied as part of the re-rebase — it won't compile standalone on the current void-signature base. Timing: do NOT rebase while #1246 is mid-rebase; prefer rebasing onto main after #1246 merges (single clean rebase). This is a heads-up + plan update, not a "start now" — wait for the optimizer to settle.
