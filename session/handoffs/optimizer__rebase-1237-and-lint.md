reason: re-read plan
refs:
  - planning/multi-analyzer-optimizer-plan.md
note: PR #1246 CI lint-and-test failed (3 golangci-lint findings) AND #1237 merged to main (badc48be), touching the same scale-down code. See plan § "CURRENT NEXT ACTION: rebase onto main@badc48be (#1237) + fix lint" — complete single-pass spec: rebase command, #1237 conflict resolution principle (our slice-based scaleDownRoleIterated supersedes #1237's legacy helpers; keep one variantsForRole; keep findCheapestVariant), the 3 lint fixes, and the full gate set including `make lint`. Do not write to plans/planning/. Do not push (PR #1246 open; Dean force-with-lease after review).
