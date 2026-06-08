reason: re-read plan
refs:
  - planning/TA-PR5-plan.md
note: `make lint` is NOT clean — it exits non-zero on 4 `unparam` findings in internal/engines/analyzers/throughput/analyzer_test.go (injectWindowObs.itlA always 0.073; baseReplica.k always 0.5 ×2; muDecG.k always kStar). These are blocking failures, NOT "acceptable" — see TA-PR5-plan §5 (a golangci-lint finding is never an acceptable warning). Fix each (drop the constant-only param + inline, or vary call sites), re-run `make lint` to exit 0, then hand back. Rebase + H1 are verified good; lint is the only blocker to push.
