last_update: 2026-07-28T18:50:00+03:00
state: in-progress
current_step: Integration branch assembled, all gates green, local tag created. Awaiting Dean's push + image build.

## Branch
ta-testing at .../ta-testing ; tip db530eed (integration HEAD)
Base: upstream/main 11d70a8a

## Merges (git merge --no-ff, DCO-signed)
- C merge: 1904306c — Merge branch 'ta-model-level-demand' (PR C #1480, tip 25f09a87). Clean auto-merge.
- D merge: db530eed — Merge branch 'ta-veto-liveness' (PR D #1481, tip b3f75650). Auto-merged textually (no reported conflicts), but a SEMANTIC conflict surfaced at `go vet`: PR C added an `arrivalRate float64` parameter to `runAnalyzersAndScore`; PR D's new file `engine_v2_liveness_test.go` (added whole → no textual conflict) called the pre-C signature. Fix folded into the D merge commit: added trailing `, 0` (arrivalRate) to all 6 call sites in that test. No production-code change beyond the two parents. Documented in the merge commit message.

## Local tag
ta-0.9-test-20260728 (annotated, on db530eed) — "TA 0.9 integration test build: main(11d70a8a) + C #1480 + D #1481". NOT pushed.

## Verification (both feature sets present — no silent hunk drop)
- C: AnalyzerInput.ArrivalRate field (domain/analyzer.go) ✓ ; CollectModelArrivalRate (collector) ✓ ; QueryModelArrivalRate (registration, 5 refs) ✓ ; nKV-weighted avgOL / totalDecodeKV (throughput/analyzer.go, 5 refs) ✓
- D: updateLivenessAndSetLive (engine_v2.go) ✓ ; lastGoodAnalysis (engine.go, 3 refs incl. field+init) ✓ ; two `if !e.Live` veto sites (pipeline/analyzer_helpers.go L241,L295 + safety-floor prose) ✓ ; QM `Live: true` carve-out (engine_queueing_model.go) ✓
- `git diff 11d70a8a HEAD -- internal/engines/saturation/engine_v2.go`: 7 C arrival-rate lines + 13 D liveness lines added — BOTH feature families folded in.

## Verified (gates)
- make test — PASS (all packages ok; saturation 5.3s, pipeline ok)
- gofmt -l ./internal/ ./pkg/ ./cmd/ — clean (empty)
- make lint — 0 issues
- go build ./... — clean
- go test -race ./internal/engines/saturation/... ./internal/engines/pipeline/... — PASS

## Not done / Dean-only next steps
- Push branch ta-testing + tag ta-0.9-test-20260728 to origin fork (NOT done — needs Dean).
- Build + push image quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9 (NOT done — Dean's step).

## Notes
This is a TEST-ONLY integration branch — never an upstream PR. Merge mechanic per Dean: `git merge --no-ff` to preserve each PR's commit provenance.

## Image build (2026-07-28)
Built locally from db530eed (tag ta-0.9-test-20260728) via `make docker-build IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` — native x86_64 build (no buildx). Build succeeded, all stages green.
- IMG ref: `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9`
- Image ID: `sha256:ce5fac61202d8a3e626bc399222d38c092e2cf59c75e77c0206c417313e21880`
- os/arch: `linux/amd64` (Dockerfile builds `CGO_ENABLED=0 GOOS=linux GOARCH=amd64`)
- NOT pushed. `make docker-push` is Dean's step (needs quay creds).
