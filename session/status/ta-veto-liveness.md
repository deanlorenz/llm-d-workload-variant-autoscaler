last_update: 2026-07-27T21:30:00+03:00
state: in-progress
current_step: review round-1 follow-ups applied, all gates green; review trigger re-sent; awaiting Dean's review before push

## Branch
ta-veto-liveness at ta-veto-liveness/ ; tip 7e931ccf

## Recent commits
- 7e931ccf — docs: clarify liveness persistence-window, demand scope, and QM exception
- 5fd0a958 — test: make the per-model liveness keying test actually discriminate
- 2b0c715c — saturation: keep the queueing-model path always-live under the new gate
- b3b7f762 — docs: document the analyzer liveness gate in the multi-analyzer pipeline guide
- 77be65ca — saturation: exclude non-live analyzers from the scale-down veto
- 785b5350 — saturation: track per-analyzer liveness (last informative analysis)

## Round-1 review follow-ups applied (all locked decisions per the plan's Review follow-ups section)
- **F-B1 (code + test, regression fix)**: optimizeQueueingModel's inline NamedAnalyzerResult
  never set Live, so the new safety floor silently disabled QM scale-down entirely. Fixed with a
  static `Live: true` at that construction site (QM is not yet a liveness participant) + new
  `engine_queueing_model_test.go` (previously zero coverage on this path). Note: this test mirrors
  the QM request shape and calls the real optimizer — it does not call `optimizeQueueingModel`
  end-to-end (that needs a full prepareModelData fake-client fixture), so it would not by itself
  catch a future deletion of the `Live: true` line. Raised to Dean via AskUserQuestion; he chose
  to keep the lighter test as-is rather than build the heavier fixture.
- **F-T1a (test fix)**: the "scopes liveness per model" spec didn't actually discriminate
  correct per-tuple keying from a buggy name-only keying, because model-a's own step used an
  informative (if stale) result that overwrote its own timestamp regardless of keying. Fixed by
  making model-a's own result non-informative (no-data) so it never self-writes. Verified by
  temporarily simulating name-only keying in engine_v2.go — confirmed the test now fails under
  the buggy keying and passes under the correct one — then reverted (working tree diff-clean
  before committing).
- **F-T1b, F-Demand, F-NTH (doc/comment only)**: dev-guide paragraph on no-data persistence-window
  semantics (never-had-data vs transient-blip vs aged-out); one sentence on the liveness/demand
  boundary (capacity-only, not demand robustness); reworded the "applies uniformly" claim to scope
  it to the multi-analyzer path and note the QM static-live exception; comment on
  `lastGoodAnalysis`'s single-writer assumption (mirrors `vaEventTracker`); comment on
  `applyDeallocationForRole`'s intentional non-gating.
- **F-Conc**: comment-only, folded into the same commit as F-T1b/F-Demand/F-NTH.

## Tests added / moved (cumulative, including round-1 follow-ups)
- internal/engines/pipeline/analyzer_helpers_test.go — ResultIsInformative: nil Result, all-no-data/error, empty VariantCapacities, mixed-with-usable-entry
- internal/engines/pipeline/analyzer_helpers_test.go — needsScaleDownForRole: never-analyzed does not veto, stale does not veto, safety floor (all non-live → false), live-no-spare still vetoes, saturation not exempt
- internal/engines/pipeline/analyzer_helpers_test.go — safeRemovalReplicasForRole: non-live analyzer's tiny spare does not drag the min to 0
- internal/engines/saturation/engine_v2_liveness_test.go — recovery across two cycles, staleness boundary (just inside/past 90s), per-model liveness scoping (now discriminating, per F-T1a)
- internal/engines/saturation/engine_queueing_model_test.go (new, F-B1) — QM-shaped Live:true result still scales down under the gate

## Verified
- make test — PASS (full repo)
- gofmt -l ./internal/... ./pkg/... ./cmd/... — clean
- make lint — 0 issues
- go build ./... — clean
- go test ./internal/engines/pipeline/... ./internal/engines/saturation/... -race -count=1 — PASS
- DCO sign-off present on all 6 commits (f5b7577c..HEAD)

## Developer guide
- docs/developer-guide/multi-analyzer-pipeline.md — "How results combine" section documents Live,
  the liveness definition/staleness window, the no-data persistence-window semantics, the
  liveness/demand boundary, the safety floor, and the QM static-live exception (no longer claims
  blanket uniformity). Updated the two scale-down diagrams and the NamedAnalyzerResult field/
  responsibility tables to include Live.

## Design deviations from the plan doc (flagged to Dean via AskUserQuestion before coding, both confirmed — from the original 3-commit round)
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
- F-B1's test does not call optimizeQueueingModel end-to-end (see above) — accepted by Dean.
- None beyond what the plan scoped out (no #1261 per-analyzer status contract; effectiveEnabled
  untouched; scale-up path untouched).

## Notes
Original 3 commits split to match the plan's two-commit structure (state-tracking / veto-gate
behavior change) by temporarily reverting the Commit-2-only hunks, committing Commit 1, then
re-applying and committing Commit 2 via the Edit tool. Round-1 follow-ups added as 3 more commits,
grouped by kind (QM code+test fix / test-only fix / doc+comment only).

Not pushed. Review trigger re-sent: session/handoffs/review__ta-veto-liveness-ready.md.
