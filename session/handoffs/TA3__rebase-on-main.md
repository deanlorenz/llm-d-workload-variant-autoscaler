reason: re-read plan
refs:
  - planning/TA-PR5-plan.md
note: CLEARED to rebase TA3 onto main@badc48be NOW (sibling of #1246, not dependent). See TA-PR5-plan § "Re-rebase timing" for the verified rationale + exact command (`git rebase --onto main 4bfac2fa TA3`). Apply H1 (§3.1) as part of it. Run the FULL gate set incl. `make lint` (§5) and fix any TA-specific lint findings — TA3 predates the lint gate, so expect some; all gates (incl. lint) must be green before hand-back so the PR review isn't blocked. Caveat (not a blocker): TA's signal is discarded on main until #1246 merges, so full e2e needs #1246 — but that's comment-triggered, not the blocking gate. Hand back when green; Dean opens the PR (base main).
