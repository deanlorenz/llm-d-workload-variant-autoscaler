last_update: 2026-08-03T23:00:00Z
state: in-progress
current_step: Commit 1 landed (34055d77). Commit 2 plan drafted and approved by Dean; not yet
  implemented — pausing for the day. Resume by implementing the Commit 2 diff below.

## Branch
ta-anchor-refactor at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-anchor-refactor ; tip 34055d77 (clean, nothing uncommitted)

## Recent commits
- 34055d77 — engine: build binding-analyzer anchor and gate saturation via effectiveEnabled (Commit 1)

## Tests added / moved
- No new tests this commit (Commit 1 is engine plumbing only; TA-only + field-classification
  tests land in Commit 3 per plan §7). Existing tests updated to reflect opt-in enablement:
  - engine_v2_liveness_test.go — shared cfg now lists an explicit saturation entry
  - engine_v2_population_test.go — "defaults Score to 1.0" case now lists saturation explicitly
  - engine_v2_test.go — "call ordering" and "disabled-analyzer gate" cases now list saturation
    explicitly; stale "skipped by the name guard" comment rewritten to describe the reuse branch
  - engine_v2_quota_test.go — satReq test helper now also populates ModelScalingRequest.Anchor
    (computeCurrentGPUUsageByNamespace reads topology off the anchor now, not a ballot scan)
  - engine_v2_demand_liveness_test.go — signature-only fix, no fixture change needed

## Verified (as of Commit 1, 34055d77)
- make test — PASS (full suite; only ./pkg/... fails, pre-existing — no pkg/ dir on this branch)
- gofmt -l ./internal/ ./cmd/ — clean
- make lint — 0 issues
- go build ./... — clean
- goldens (internal/engines/pipeline, optimizer_characterization_test.go) — green, untouched by
  Commit 1 (Commit 1 doesn't touch the pipeline package's read sites — that's Commit 2)

## Developer guide
- Not started — Commit 4.

## Open questions for Dean
- None currently open. Two Commit-1 design questions (load-bearing skip → reuse branch; sat-v2
  opt-in enablement, no ApplyDefaults change) were escalated and resolved by the planner on
  plans@500f08d8. A third gap I found while scoping Commit 2 — engine_queueing_model.go's
  ModelScalingRequest never sets Anchor, and isn't in either commit's file list — Dean approved
  folding the (mechanical) fix into Commit 2 directly, no planner round-trip needed.

## Not done / known limitations — RESUME HERE
- **Commit 2 is planned and approved but NOT YET IMPLEMENTED.** Full concrete diff (already
  presented to and approved by Dean, ready to code on resume):
  - `analyzer_helpers.go`: rename `saturationEntry(s []NamedAnalyzerResult) *domain.AnalyzerResult`
    → `bindingAnchor(req ModelScalingRequest) *domain.AnalyzerResult { return req.Anchor }`; drop
    the by-name scan, the "keeper of per-variant metadata" comment, and the stale
    `TODO: remove the sat_v2 special role`; new docstring per plan §6 2a.
  - `cost_aware_optimizer.go`: `Optimize`'s `satEntry := saturationEntry(req.AnalyzerResults)` →
    `anchor := bindingAnchor(req)`; `vcMap`/`allocateForModelPaired`/`scaleDownRoleIterated` read
    `anchor.VariantCapacities`. `buildDecisionsWithOptimizer`'s internal RC/SC fetch changes from
    the anchor to `req.AnalyzerResults[0].Result` (guarded on non-empty) — RC/SC must come off the
    ballot, never the anchor, per plan §6 2c.
  - `greedy_score_optimizer.go`: `modelWork.satEntry` field → `anchor` (comment drops "keeper");
    both `Optimize` loops (scale-up and "other") and `buildScaleUpWork` switch to `bindingAnchor(req)`;
    `allocateForModel`'s `w.satEntry.VariantCapacities` → `w.anchor.VariantCapacities`.
  - `rescale.go`: all 6 `saturationEntry(req.AnalyzerResults)` call sites → `bindingAnchor(req)`;
    rename local vars/params `satEntry`→`anchor` throughout (`modelDemandGPUs`, `roleDemandGPUs`, etc.).
  - `analyzer_helpers_test.go`: `Describe("saturationEntry", ...)` → `Describe("bindingAnchor", ...)`,
    rebuilt around `ModelScalingRequest{Anchor: ...}`.
  - Test-fixture fallout (mechanical — add `Anchor: r`/`Anchor: result` alongside each
    `AnalyzerResults` assignment): `withSatEntry` + all three local `withSatEntryPD` closures in
    `cost_aware_optimizer_test.go` (lines ~16, ~740, ~833, ~882), `withSatEntryV2` in
    `engine_v2_test.go`, `withQMEntry` in `engine_queueing_model_test.go`. **This is the §11
    withSatEntry hazard — do not remove/re-signature these helpers, only add the Anchor field.**
  - QM-path fix (approved to fold into Commit 2): `engine_queueing_model.go:77` — add
    `Anchor: result,` to the `ModelScalingRequest` literal.
  - Not touched: `applyAllocation`, `roleBottleneckReplicas`, `roleAggRemaining`, `fairShareValue`,
    `initRoleState`, `sortVariantsForScaleDown`'s tie-break combine — unchanged, still read the
    per-analyzer ballot slice `s`.
  - Gate: goldens green, `make test`, `gofmt`, `make lint`, `go build`.
- Commits 3, 4 not started (TA-only enablement + tests, dev-guide).
- §9 semantic-pivot grep run scoped to Commit 1's two touched files only (clean, one stale
  docstring sentence fixed) — full repo-wide grep still pending, do after Commit 2 lands.

## Notes
Design gap raised during Commit 1 (sat-v2 default-off under opt-in) was escalated via handoff and
resolved by Dean/planner as "accept as designed." Commit 1 landed exactly as re-specified in
plans@500f08d8. Commit 2's plan is fully drafted and Dean approved it verbally in-session; pausing
before implementation since Dean asked to break for the day. Next session: implement the Commit 2
diff above directly (no need to re-derive or re-confirm — just re-verify branch/CWD per the
mandatory pre-edit gate, then code it), run gates, commit, then move to Commit 3.
