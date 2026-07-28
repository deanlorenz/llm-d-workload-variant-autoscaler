last_update: 2026-07-26T00:00:00+03:00
state: in-progress
current_step: Post-review follow-ups (F1, F2) landed; all gates re-verified green; fresh review-ready trigger written; awaiting Dean's final review.

## Branch
ta-registration-safety at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-registration-safety ; tip 7374be55, off main@f5b7577c

## Recent commits
- 7374be55 — docs: fix stale stopgap note in throughput-analyzer.md (review F1)
- 7b69a561 — saturation: add effectiveEnabled spec for other-analyzers-configured case (review F2)
- 44af05c6 — docs: document effectiveEnabled opt-in participation semantics
- 30bca98e — cmd: log when ThroughputAnalyzer is not registered
- 75f529b9 — saturation: make effectiveEnabled opt-in (absent entry → false)

## Tests added / moved
- internal/engines/saturation/engine_v2_population_test.go — flipped absent-entry `effectiveEnabled` assertion to `BeFalse()`; description updated to state opt-in. Added a new spec (review F2): "returns false when other analyzers are configured but the target is absent" — the fall-through path with a non-empty `Analyzers` slice, distinct from the empty-config case.
- internal/engines/saturation/engine_v2_test.go — "calls each enabled non-saturation analyzer exactly once in registration order": added explicit `Analyzers` entries for `throughput`/`slo` — this test's fixture relied on the old default-enabled-when-absent behavior and broke under the opt-in change; fixed to restore original intent (call-ordering, not enablement).
- internal/engines/saturation/engine_v2_population_test.go — "defaults Score to 1.0..." and "applies per-analyzer ScaleUpThreshold override..." (config-bridge block): same collateral fix — added an unscored `Analyzers` entry for "spy" so it still participates under opt-in semantics.
- cmd/main_test.go (new file) — TestThroughputAnalyzerEnabled table test: absent (empty config), absent (other analyzer present), enabled (explicit true), enabled (present/nil), disabled (explicit false).

## Verified (re-run after F1/F2 commits)
- make test — PASS (full suite, all packages)
- gofmt -l $(find ./internal ./pkg ./cmd -name '*.go') — clean
- make lint — 0 issues
- go build ./... — clean
- DCO: all 5 commits carry Signed-off-by: Dean H Lorenz <dean@il.ibm.com> (`git log main..HEAD --format="%b" | grep -c Signed-off-by` == 5)

## Developer guide
- docs/developer-guide/multi-analyzer-pipeline.md — `enabled` field default annotated "true (when the entry is present)"; new paragraph stating the opt-in participation rule, the scale-down-veto hazard it prevents, and the saturation exemption.
- docs/developer-guide/throughput-analyzer.md (review F1) — replaced the stale "this is a stopgap... will remove the restart requirement when it lands" claim (both halves were wrong: the fix landed on this branch, and it never touched registration freezing) with an accurate statement that the startup registration gate and the per-cycle effectiveEnabled gate are independent, cross-linked to multi-analyzer-pipeline.md.

## Review outcome (FINAL, no blocking findings)
planning/ta-registration-safety-review.md: verdict was no blocking findings, code OK to proceed
once F1 and F2 land. Both actioned in this session (commits 7b69a561, 7374be55). F3 (deferred
pipeline-package coverage gap) accepted as documented — no action, matches PR D
(ta-veto-liveness) scope more naturally than this PR.

## Open questions for Dean
None outstanding — both review follow-ups actioned.

## Not done / known limitations
- F3 (from the original handoff, accepted by review as-is, no action needed): no natural fixture
  in internal/engines/saturation/ exercises needsScaleDownForRole end-to-end (it lives in
  internal/engines/pipeline/, out of this PR's scope). The "unconfigured analyzer doesn't veto
  scale-down" claim is covered indirectly (effectiveEnabled unit tests + config-bridge tests
  confirming exclusion from the result slice), not via a pipeline-level fixture.

## Notes
Second pass after Dean's FINAL review (planning/ta-registration-safety-review.md). Processed via
trigger ta-registration-safety__review-followups.md (marked .WIP then .DONE). Both coder-actionable
findings (F1, F2) landed as new commits rather than amending the reviewed commits, per general
git-history-stability practice — the original 3 commits' content/messages are unchanged and match
what the review doc verified.