reason: re-read plan
refs:
  - planning/multi-analyzer-optimizer-plan.md
note: Phase 3 commits 1–4 landed correctly (unification + D-only gate fixed + tests). The delete step was not done — see plan § Phase 3 "Commit 5 — cleanup pass": delete orphaned functions + their dead tests, collapse the scaleDownRoleIterated passthrough, fix stale comments. Follow wrap→verify→inline→delete to its last step; delete one at a time, make test green after each. Not push-ready until commit 5 lands.
