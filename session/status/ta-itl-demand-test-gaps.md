last_update: 2026-08-03T00:00:00Z
state: in-progress
current_step: round-2 delta (Commit 2 NIT reword + new Commit 4) landed on top of round-1; all gates green; awaiting internal re-review before any push

## Branch
ta-itl-demand-test-gaps at ta-itl-demand-test-gaps/ ; tip 96263639 (cut from main@6bfb73e1, PR F #1503 merge)

## Recent commits
- 96263639 — test(throughput): add direct coverage for computeVariantSupply
- 3f770fd6 — test(throughput): reword Tier-2-rejection comment (round-1 review NIT)
- 39241065 — test(throughput): cover computeLocalDemand capacity/ITL skip guards
- 11b261ea — test(throughput): cover Tier-2 fit rejection in resolveITLModel
- d6c3c250 — test(throughput): cover Inf B rejection in validITLModel

## Tests added / moved
Round 1 (unchanged):
- itl_model_test.go:"validITLModel" — "rejects Inf B" (symmetric with existing "rejects Inf A")
- analyzer_test.go:"resolveITLModel — Tier-2" — "resolveITLModel returns T2-failed when the computed fit is rejected by validITLModel" (n=1, sumK2>0 path, distinct from existing idle-only n==0 test)
- analyzer_test.go:"computeLocalDemand" — "skips a replica with non-positive TotalKvCapacityTokens"
- analyzer_test.go:"computeLocalDemand" — "skips a replica whose model produces a finite non-positive ITL"

Round 2 (new):
- analyzer_test.go:"resolveITLModel — Tier-2" — comment reworded ("pinned" → "constant baseline B ... default path") per review NIT; test body/assertions unchanged.
- analyzer_test.go:"computeVariantSupply" (new Describe block) — "aggregates supply across KV-capable replicas" (non-vacuity) + "skips a replica with non-positive TotalKvCapacityTokens" (guard fires: total==0 && nKV==0). Surfaced during round-1 review — this function shares computeLocalDemand's capacity guard but on the supply path and had only indirect Analyze-level coverage before.

All exercise guards already shipped in production code — no production code changes were needed; none of the new tests failed against current code, so no real bug was uncovered.

## Verified (post round-2)
- make test — PASS (all packages, no regressions; throughput package coverage 93.2% → 93.4%)
- gofmt -l ./internal ./cmd — clean
- make lint — 0 issues
- go build ./... — clean
- go test ./internal/engines/analyzers/throughput/... -race — PASS
- DCO — all 5 commits carry Signed-off-by: Dean H Lorenz <dean@il.ibm.com>

## Developer guide
- No changes. computeVariantSupply's guard is already documented alongside computeLocalDemand's in the Type 4 doc (F's 0c35d717); this is coverage-only.

## Open questions for Dean
- None.

## Not done / known limitations
- checkVariantGPSMismatch's matching TotalKvCapacityTokens/itlAtK guards remain untested — explicitly deferred by the plan (round-2 addendum) as a separate future coverage task, not folded into this branch.
- The round-1 "Optional (NTH)" cases remain skipped, as the plan allows: (1) a second Tier-2-rejection case via itlReasonT2Pinned; (2) a computeLocalDemand zero-KvUsageInstant boundary case.

## Notes
Plan header/scope changed in round 2: this branch is now targeting 0.9 (code freeze 2026-08-06) and becomes a PR once round-2 + internal re-review are clean — still no push without Dean's explicit per-push confirmation (planner proposes the PR/push timing).

Verified computeVariantSupply's actual signature and TotalKvCapacityTokens field name against analyzer.go:679 before writing Commit 4 — matched the plan's draft exactly. Confirmed no pre-existing Describe("computeVariantSupply", ...) block existed (only indirect coverage via the "excludes booting (KV=0) replicas" test at analyzer_test.go:372).

Split the round-2 diff into two commits along its two non-overlapping hunks (comment reword vs. new additive block) rather than amending round-1 history, per git-safety default (prefer new commits over amend).

Review trigger re-written per CODER-CONVENTIONS §5.4 for the round-2 delta.
