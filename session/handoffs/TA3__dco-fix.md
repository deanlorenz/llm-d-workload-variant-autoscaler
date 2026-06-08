reason: re-read plan
refs:
  - planning/TA-PR5-plan.md
note: make lint now 0 (good). But 6 of 21 commits above main are missing DCO sign-off — the CI DCO bot will reject the PR. Missing: 2d12b756, 27735c56, 96a789a4, 23f3ca70, ccb7c8f0, fd49ecee. These are older pre-rebase commits whose sign-off was stripped during the rebase. Fix: interactive rebase to add --signoff to each, or run `git rebase --signoff badc48be` (if git version supports it). Then verify ALL 21 commits have Signed-off-by: with `git log badc48be..HEAD --format='%h %b' | grep -c 'Signed-off-by'` — must equal 21. All other gates are green; DCO is the only blocker.
