last_update: 2026-07-29
state: in-progress
current_step: F3 §4a cleanup COMPLETE (b2acffd6) on top of C.0 rebase + C.1/C.2. All gates green. Push-ready pending Dean's force-push.

## F3 — §4a plans-branch identifier cleanup (round 3, commit b2acffd6)
Review's F3 flagged 7 leaks; a full working-tree re-scan found 14 C-INTRODUCED leaks total
(review undercounted by 7). Dean authorized folding all in (2026-07-29). All 14 fixed in one
comment/test-description-only commit b2acffd6 (no logic change):
- 7 review F3 sites: decision #1 (x3 analyzer.go), review finding F1 (x2 analyzer.go + x1 test It),
  Decision #4 (test comment).
- 3 TA-demand §3.3/§3.5: analyzer.go x2 + throughput-analyzer.md.
- 4 additional found in re-scan: TA-supply.md §5.5 (throughput-analyzer.md), plan §Deferred (x2 test),
  plan §Tests 1-4 (test Describe string).
Each expanded to self-contained descriptive prose. Commit message itself §4a-clean.
DELIBERATELY NOT TOUCHED (pre-existing upstream, from #1250 efca1b4c — out of scope for C):
- throughput-analyzer.md:671 `plans/planning/TA-Plan.md, TA-PR4-plan.md` (Design: line)
- analyzer_test.go:1189 `Specs 1-5 from plan §3.4`
These are a pre-existing upstream §4a leak worth a separate upstream issue; NOT PR C's to fix.

## Branch
ta-model-level-demand at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-model-level-demand
pre-rebase tip: 25f09a87 (base 11d70a8a)
tip: b2acffd6 (was 94accd09 before F3 cleanup)
base: dfc21e2c (upstream/main; Dean chose this over the plan's stale 28a58b77 — it adds #1491 utils-split)

## C.0 rebase result (11d70a8a -> dfc21e2c)
`git rebase dfc21e2c` succeeded CLEANLY (no manual conflict resolution). Upstream gap picked up:
#1473 (Makefile, no code), #1450 (saturation->saturationv1), #1448 (pkg->internal/queueing),
#1487 (GLOBAL_OPT_INTERVAL), #1491 (split internal/utils). My hunks touch no import lines, so the
#1450/#1491 path churn resolved automatically — go build clean confirms it.

## Post-rebase commit stack (dfc21e2c..HEAD)
- b2acffd6 — throughput: replace internal-planning references with self-contained prose (F3 §4a, 14 sites, comment/test-desc only, no logic change)
- 94accd09 — throughput: document zero-arrival safety + why RequestRate is not an arrival cross-check (C.1+C.2, comment-only, +16 lines, no logic change)
- 4fb1b659 — docs(multi-analyzer-pipeline): add ArrivalRate to AnalyzerInput field table
- b0257e59 — throughput: weight model-level avgOL by replica count
- 55b0507f — throughput: compute decode demand from model-level arrival rate
- a1446aa8 — collector: add model-level request arrival rate for the throughput analyzer
(old->new SHA map: 7851cb33->a1446aa8, 66fde352->55b0507f, 0eb46e77->b0257e59, 25f09a87->4fb1b659; C.1/C.2 = new 94accd09)

## Per-commit / per-file verification (silent-hunk-drop discipline) — all 4 behaviors survive
- a1446aa8: QueryModelArrivalRate registered in throughput_analyzer.go (sum(rate(
  inference_extension_scheduler_attempts_total{status="success"}))), CollectModelArrivalRate in
  replica_metrics.go, ArrivalRate float64 on domain.AnalyzerInput — PRESENT (stat 8 files, matches pre-rebase).
- 55b0507f: decode demand = input.ArrivalRate x avgOL; distributeQueueDemandByRole ->
  distributeDemandByRole reused for arrival+queue; avgOL from tracked WorkloadShape.AvgOutputTokens
  (warm-up safe); anyEPP := input.ArrivalRate > 0 — PRESENT (stat 3 files, matches).
- b0257e59: nKV-weighted avgOL (totalDecodeOL += nKV*OL; avgOL = totalDecodeOL/totalDecodeKV);
  regression test (1 rep OL=100, 3 reps OL=300 -> 250 not 200) — PRESENT (stat 3 files, matches).
- 4fb1b659: ArrivalRate row in multi-analyzer-pipeline.md — PRESENT.

## C.1 / C.2 (94accd09) — both comment-only, plan §followups
- C.1: at the demand-composition site (avgOL / arrivalDecodeDemand block) — zero/absent arrival is
  legitimately zero demand: only permits scale-down (all-live-agree gate still governs), never forces
  a scale action, never drives scale-up; intentionally not floored to a served-rate proxy.
- C.2: at anyEPP := input.ArrivalRate > 0 — RequestRate is a completion rate (non-zero during drain),
  deliberately NOT a broken-arrival cross-check (false-positives on ramp-down); durable
  live-supply/never-seen-demand is an observability warning in the engine liveness path instead.
- Both current-code prose, no plans-branch/PR identifiers (§4a compliant).

## Verified (all gates re-run after rebase + comment commit)
- go build ./... — clean
- go vet ./internal/engines/analyzers/throughput/ — clean
- gofmt -l on internal/ + cmd/ — clean (empty)
- make test — full suite green (throughput 92.1%, saturation 67.4%; new saturationv1 + queueing layout resolves)
- make lint — 0 issues
- DCO sign-off present on all 5 commits (dfc21e2c..HEAD)

## Not done / known limitations
- NOT pushed. PR #1480 is OPEN — force-push to origin requires Dean's explicit confirmation at push
  time (history rewrite; --force-with-lease; warn-before-push on active PR branch).

## Notes
Review FINAL, no outstanding findings; F1 (nKV-weighted avgOL) + F2 (doc row) already in commits;
C.1/C.2 close out ev-shindin's two PR #1480 comments as comment-only per Dean's 2026-07-29 lock.
The broken-arrival *detector* is deliberately not on C — it lives in the engine liveness path
(ta-veto-liveness work), per plan §followups.
