last_update: 2026-07-27T12:00:00+03:00
state: in-progress
current_step: all commits landed, all gates green; review trigger sent; awaiting Dean's review before push

## Branch
ta-veto-liveness at ta-veto-liveness/ ; tip b3b7f762

## Recent commits
- b3b7f762 — docs: document the analyzer liveness gate in the multi-analyzer pipeline guide
- 77be65ca — saturation: exclude non-live analyzers from the scale-down veto
- 785b5350 — saturation: track per-analyzer liveness (last informative analysis)

## Tests added / moved
- internal/engines/pipeline/analyzer_helpers_test.go — ResultIsInformative: nil Result, all-no-data/error, empty VariantCapacities, mixed-with-usable-entry
- internal/engines/pipeline/analyzer_helpers_test.go — needsScaleDownForRole: never-analyzed does not veto, stale does not veto, safety floor (all non-live → false), live-no-spare still vetoes, saturation not exempt
- internal/engines/pipeline/analyzer_helpers_test.go — safeRemovalReplicasForRole: non-live analyzer's tiny spare does not drag the min to 0
- internal/engines/saturation/engine_v2_liveness_test.go (new) — recovery across two cycles, staleness boundary (just inside/past 90s), per-model liveness scoping (one model's fresh result does not make another model's stale entry live)

## Verified
- make test — PASS (full repo)
- gofmt -l ./internal/... ./pkg/... ./cmd/... — clean
- make lint — 0 issues
- go build ./... — clean
- go test ./internal/engines/pipeline/... ./internal/engines/saturation/... -race -count=1 — PASS

## Developer guide
- docs/developer-guide/multi-analyzer-pipeline.md — "How results combine" section rewritten to
  document Live, the liveness definition/staleness window, the safety floor, and that saturation
  is gated the same as any analyzer (no name-based exemption). Updated the two scale-down ASCII/
  text diagrams and the NamedAnalyzerResult field table + responsibility table to include Live.

## Design deviations from the plan doc (flagged to Dean via AskUserQuestion before coding, both confirmed)
1. **lastGoodAnalysis keyed per (namespace, modelID, analyzerName), not analyzer-name-only.**
   The plan's Engine.lastGoodAnalysis map[string]time.Time would have leaked liveness across
   models, since one Engine instance serves every model. Confirmed with Dean; implemented as
   map[string]map[string]time.Time keyed by utils.GetNamespacedKey(namespace, modelID) then name.
2. **Staleness threshold: fixed multiple = 3x cycle** (analyzerLivenessStaleCycles = 3 in
   engine_v2.go), computed against Config.OptimizationInterval() with a 30s fallback for unit
   tests that construct a minimal Engine without Config. Confirmed with Dean per the plan's
   explicit "confirm with Dean" flag.

## Open questions for Dean
- None outstanding.

## Not done / known limitations
- None beyond what the plan scoped out (no #1261 per-analyzer status contract; effectiveEnabled
  untouched; scale-up path untouched).

## Notes
Commits split to match the plan's two-commit structure (state-tracking, no behavior change /
then the veto-gate behavior change) by temporarily reverting the Commit-2-only hunks, committing
Commit 1, then re-applying and committing Commit 2 — done via the Edit tool to keep the two
diffs clean for review. A third commit covers the dev-guide update.

Widened the semantic-pivot grep beyond the plan's declared file list (per the 2026-07-26 A' review
note in CURRENT.md): found and fixed 5 additional pre-existing test fixtures across
cost_aware_optimizer_test.go and engine_v2_test.go that construct NamedAnalyzerResult directly and
exercise the scale-down path — these broke under the new Live-gating until given Live: true.

Not pushed. Review trigger sent: session/handoffs/review__ta-veto-liveness-ready.md.
