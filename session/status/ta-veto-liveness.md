last_update: 2026-07-29
state: round-3-nth-complete
current_step: round-3 review NTH-1/2/3 folded into the D.2/D.3 commit (amended); gates green; NOT pushed

## Branch
ta-veto-liveness at .../ta-veto-liveness (PR #1481, OPEN). Rebased onto upstream/main dfc21e2c.
Tip: c32235be (was 5d324b36 — amended in place to fold the round-3 NTH items; still 8 commits
total from base dfc21e2c, unpushed). DCO 8/8. NOT pushed (planner force-pushes with
--force-with-lease; coder never pushes; warn-before-push applies).

## Round-3 review NTH follow-ups — DONE (review APPROVE; NTH non-blocking, applied since unpushed)
Review: plans/planning/ta-veto-liveness-review.md § Round-3 (verdict APPROVE, 3 NTH). All three
belonged to the former 5d324b36 (its D.2 code / its comment / its dev-guide prose / its message),
so they were folded into that commit via --amend (new tip c32235be) rather than stacked as a
separate "round-3 fixups" commit (which would itself have leaked a round token).
- NTH-1 — pruneLastGoodAnalysis now has a direct table test:
  internal/engines/saturation/engine_v2_prune_test.go (TestPruneLastGoodAnalysis) — evict-departed
  / keep-active (inner entry intact), empty-set no-op, nil-map no-panic.
- NTH-2a — engine_v2.go:286 comment "round-1's supply gate" → "the supply liveness gate"
  (removed the review-round process artifact per CODER-CONVENTIONS §4a).
- NTH-2b — commit body "Two round-2 follow-ups…" → "Two follow-ups…" (round token dropped;
  amend was safe as the branch is unpushed and c32235be is my own commit from this session).
- NTH-3 — dev-guide demand-liveness paragraph: "(`TotalDemand > 0`)" (the *healthy* predicate)
  → "(`TotalDemand == 0`)" so the parenthetical matches the stale/no-demand condition it annotates.
- grep confirms zero "round-1"/"round-2" tokens remain in internal/ or docs/ or the commit body.

## Round-2 folds — DONE (locked by Dean 2026-07-29, approved "ok" this session)

## Round-2 folds — DONE (locked by Dean 2026-07-29, approved "ok" this session)

### D.1 — single source of truth for no-data/error sentinels (commit 61060530)
Promoted to exported pipeline.ReasonNoData / pipeline.ReasonError (was unexported
analyzerReasonNoData/analyzerReasonError). Decision: PROMOTE, no pin test — verified no import
cycle (pipeline does not import saturation_v2; saturation_v2 did not import pipeline).
- pipeline/analyzer_helpers.go: exported the two consts + doc; ResultIsInformative uses them.
- saturation_v2/types.go: `satReasonNoData = pipeline.ReasonNoData` (const alias; added pipeline import).
- saturation_v2/analyzer.go: bare `return "error"` (k2SourceLabel, flows to VariantCapacity.Reason) → `pipeline.ReasonError`; added pipeline import.
- DEPRECATED note: the "no-data"/"error" string literals in saturation_v2 are gone, superseded by
  the shared pipeline constants (deletion-documentation rule).
- analyzer_test.go:1719 still asserts Equal("error") on the observable value — passes unchanged.

### D.2 — prune lastGoodAnalysis of departed models (commit 5d324b36)
- engine_v2.go: new `pruneLastGoodAnalysis(activeKeys map[string]bool)` — deletes outer modelKeys
  absent from the active set; guards empty set (skip prune → never wipes on a transient zero-model cycle).
- engine.go optimizeV2 (top): builds activeKeys via utils.GetNamespacedKey(namespace, modelID) per
  group (SAME keying as updateLivenessAndSetLive — NOT the raw groupKey), then calls prune.
  optimizeV2 is the only writer of lastGoodAnalysis (via collectV2ModelRequest→runAnalyzersAndScore),
  so pruning there is sufficient; V1/QM paths never touch the map.

### D.3 — demand-liveness warn-only detector (commit 5d324b36)
- engine_v2.go: `detectDemandLiveness(...)` called at end of updateLivenessAndSetLive.
  updateLivenessAndSetLive signature gained `ctx context.Context` (only caller runAnalyzersAndScore
  has ctx; tests drive via runAnalyzersAndScore so no test-signature churn).
- Two latches in the same per-model map: supply latch = perAnalyzer["throughput"] (maintained by
  round-1 loop); demand latch = perAnalyzer["throughput"+demandLatchSuffix], demandLatchSuffix =
  "\x00demand" (NUL-delimited synthetic key, cannot collide with a real analyzer name).
- WARN (logger.Info at V(0) — logr has no Warn level; codebase logs prominent signals at V(0))
  when supply live now AND (supplyTS - demandTS) >= threshold. Seeds demand latch to supplyTS on
  first live-supply so cold-start scrape lag does NOT false-positive (gap starts at 0).
- Never sets nr.Live, never touches RoleSpare, never gates a decision — rationale in code comment.
- DEFERRED (in code comment + here): per-pod demand latch — key extends with "\x00"+podID when
  demand becomes per-replica; not built (0.9 demand is model-level).
- Test: engine_v2_demand_liveness_test.go — 4 tests (healthy no-warn; supply-live+demand-stale warn
  + Live stays true; cold-start no-warn; synthetic-key-never-flips-Live). Uses zapObserverCtx +
  observer (plain testing.T, like engine_v2_log_test.go). ALL PASS.

### Dev guide round-2 (commit 5d324b36)
docs/developer-guide/multi-analyzer-pipeline.md liveness section: replaced the "demand out of
scope" paragraph with current-code prose describing the warn-only demand telemetry (no plans/PR refs).

## Gates (all green on committed content, re-run after the round-3 amend @ c32235be)
gofmt clean; go build ./... OK; go vet OK; make test NO FAILURES; make lint 0 issues;
-race PASS on saturation (pipeline+saturation_v2 untouched this round); DCO 8/8.
(NB: the round-2 D.1/D.2/D.3 sections below cite the pre-amend SHAs 61060530/5d324b36 as they
were when authored; D.2/D.3 content now lives in the amended c32235be — see the round-3 section.)

## Not done / next
- NOT pushed. Planner force-pushes #1481 when ready (tip is now c32235be, not 5d324b36).
- Nothing else outstanding on this branch for 0.9.
