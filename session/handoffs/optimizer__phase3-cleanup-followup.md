reason: re-read plan
refs:
  - planning/multi-analyzer-optimizer-plan.md
note: Cleanup commit 2a3b5c40 review found two leftovers — see plan § Phase 3 "Commit 5 follow-up": delete applyDeallocation (+ its test block + trim the optimizer_interfaces.go comment), reword 2 stale costAwareScaleDown test descriptions. Then run the grep-to-zero verification step in the plan and paste the (empty) output. Fold into 2a3b5c40 (amend). Not push-ready until the grep is empty.
