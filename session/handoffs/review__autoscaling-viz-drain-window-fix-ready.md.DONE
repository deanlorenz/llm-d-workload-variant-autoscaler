to: review
reason: code-review-before-push
refs:
  - autoscaling-viz/ (worktree)
  - planning/autoscaling-viz-drain-window-fix-plan.md
note: 1 commit (e188d244) on top of 3f12aaa1 -- the last item in the sequenced review-fix series.
  Python-only worktree, no gofmt/lint/test gates apply. Self-check: no /code-review run (diff is 1
  file, +43/-7). Two things worth the reviewer's attention specifically: (1) the first fix attempt
  (documented in the commit message) was itself wrong and regressed 11 correct drain windows on
  m-satta-dwell -- caught only because that cell was re-verified even though the spec's own
  checklist didn't name it, so the review may want to weigh whether the spec's verification list
  should be treated as exhaustive going forward; (2) the fixed r2tnh case now shows NO drain window
  at all, not a short one near t~1073s as the spec's own verification wording implied -- this is the
  spec's own step-3 fallback firing correctly (r2tnh's last sample genuinely precedes the real
  transition, so no nonzero window can exist without inventing data), not a deviation, but worth the
  reviewer confirming that reading independently rather than taking my word for it.
