to: review
reason: code-review-before-push
refs:
  - autoscaling-viz/ (worktree)
  - planning/autoscaling-viz-panel6-redesign-plan.md
note: 1 commit (3f12aaa1) on top of 08927557 -- Task 3, the last queued task in the sequenced series.
  Python-only worktree, no gofmt/lint/test gates apply. Self-check: no /code-review run (diff is
  2 files, +96/-35, one new extractor field extension and one panel rewrite). The delta formula's
  sign was derived from the saturation engine's actual Go source (not assumed from the design doc's
  own suggested starting point, which had it backwards) and hand-verified against 2 real
  controller.log ticks with independently known scale-up/scale-down outcomes, per the spec's own
  required check. Manually verified against 4 cases: a 15-pod SAT+TA run, a TA-only run (absent-
  analyzer dashed/faded treatment confirmed), a no-controller.log degrade path, and the golden
  pre-panel-6 bundle for backward compat. One self-caught layout collision (marker key vs. the
  figure's x-axis label) fixed before commit, same class of defect as fix-round 1's Issue 2 -- this
  time avoided by design (fixed-legend key placed inside the axes from the start) rather than
  needing correction after landing, then still caught once during verification and adjusted.
