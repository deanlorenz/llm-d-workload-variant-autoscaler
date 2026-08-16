to: benchmark
reason: pull up + commit viz output stuck at results/<leaf>/viz/
refs:
  - session/handoffs/plan__benchmark-viz-output-needs-pullup-and-commit.md
  - planning/ta-pokprod-history.md
note: Dean-approved 2026-08-14 -- pull-up + commit, matching commit 02793145's existing
  precedent (not a gitignore-pattern change). Verified directly against the benchmark worktree:
  the 7 stale-regen runs (dean-20260810-*) already have a TOP-LEVEL runs/<id>/viz/panels.png
  (tracked, but it's the STALE 2026-08-12 file) alongside the FRESH nested
  results/<leaf>/viz/panels.png (2026-08-14, version-stamped) -- the fresh nested copy needs to
  overwrite the stale top-level one, not just get added alongside it. The 11 never-rendered runs
  (12 dirs -- dean-20260813-130251-004 has 4 leaves) have only the nested copy, no top-level
  location exists yet -- straightforward pull-up. 19 run IDs total, listed in the referenced
  handoff. Once pulled up: verify future regens land directly at runs/<id>/viz/ per the existing
  convention, not nested under results/<leaf>/, so this doesn't recur.
