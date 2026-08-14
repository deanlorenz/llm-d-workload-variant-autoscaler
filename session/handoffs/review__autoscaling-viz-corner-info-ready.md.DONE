to: review
reason: code-review-before-push
refs:
  - autoscaling-viz/ (worktree)
  - planning/autoscaling-viz-corner-info-plan.md
note: 1 commit (062c1071) on top of 870fff6d. Python-only worktree, no
  gofmt/lint/test gates apply. Self-check: no /code-review run (diff is 1 file, +85/-16, additive
  text/title changes to 6 panels, no structural changes to any existing series/computation).
  Verified against a full-per-request run and a no-per-request run (clean degrade on all three
  affected panels), plus a golden pre-panel-6 bundle for backward compat. Sanity-checked the two new
  derived numbers (replica-seconds, utilization) by hand against a rough estimate and the panel's
  own visible shading respectively.
