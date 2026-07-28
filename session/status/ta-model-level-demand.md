last_update: 2026-07-27T16:45:00Z
state: in-progress
current_step: review findings F1+F2 fixed (2 new commits), all gates re-verified green. Awaiting re-review.

## Branch
ta-model-level-demand at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-model-level-demand ; tip 4a816dde (base main@f5b7577c)

## Recent commits
- 4a816dde — docs(multi-analyzer-pipeline): add ArrivalRate to AnalyzerInput field table (review F2)
- e800ff87 — throughput: weight model-level avgOL by replica count (review F1)
- 6f161a5a — throughput: compute decode demand from model-level arrival rate  [Commit 2]
- 652307bd — collector: add model-level request arrival rate for the throughput analyzer  [Commit 1]

## Review findings addressed (planning/ta-model-level-demand-review.md, FINAL, both blocking)
- **F1 (avgOL weighting):** the first pass combined non-prefill variants' tracked OL with an
  unweighted mean (`totalDecodeOL / nDecodeVariants`) — every variant contributed equally
  regardless of replica count, diverging from the plan's specified RequestRate-weighted
  model-level average. Invisible with a single non-prefill variant (every existing fixture used
  exactly one), which is why review caught it and no test did. Fixed (e800ff87): weight by
  `nKV` (replica count, already in hand in the same loop) — `avgOL = Σ(nKV_v × OL_v) / Σ(nKV_v)`.
  Added a 2-variant regression test with different OL and different replica counts (1 @ OL=100,
  3 @ OL=300) that pins the weighted result (250) against the unweighted one (200) it must not
  regress to. Dev guide's avgOL formula and a new "Weighting" paragraph updated to match.
- **F2 (doc gap):** `multi-analyzer-pipeline.md`'s generic `AnalyzerInput` field table was
  missing the new `ArrivalRate` row (that doc wasn't in this PR's named dev-guide scope, so
  review called this a plan gap, not a coder process failure). One-row fix (4a816dde).

Review's "process point" on F1 — that a plan-specified formula's *semantics* (not just data
source) changed silently while fixing the warm-up bug, and should have been flagged as an
explicit open question rather than folded into a same-paragraph bug-fix note — is noted for the
CODER-CONVENTIONS gap Dean/planner may want to close; not something to self-fix further here.

## Tests added / moved
- internal/collector/replica_metrics_test.go: `TestCollectReplicaMetrics_ArrivalRatePerPodRetained`
  (plan §Tests item 5 — regression guard that per-pod ArrivalRate still populates via the
  existing scheduler_dispatch_rate merge, since queueingmodel/allocation depend on it).
- internal/engines/analyzers/throughput/analyzer_test.go:
  - Migrated ~10 existing tests to also set the new model-level `AnalyzerInput.ArrivalRate`
    (mechanical — sum of each test's per-pod values), plus 2 EPP-warm-up tests that needed it
    for the tracked-shape avgOL fix to take effect (see below).
  - Rewrote 3 tests whose premise assumed the old per-variant-summed invariant:
    - "k*-based local demand (no EPP)" → now asserts per-variant demand still populates
      (introspection) but model-level TotalDemand is 0 by design.
    - "scheduler queue demand" ("adds queue demand...") → bumped QueueSize so queue demand
      *alone* clears μ_sat, since k*-local no longer backfills model-level demand.
    - "aggregation-helper linearity invariants" ("TotalDemand equals...") → rewritten to
      assert the new invariant (`TotalDemand == input.ArrivalRate×avgOL + queueDemand`)
      instead of the retired one (`SumTotalDemand(VariantCapacities) + queueDemand`).
  - Added 4 new tests (plan §Tests items 1-4): model-level demand == R×L; orphan-merge
    regression backstop; queue+arrival combined exactly once with role-sum linearity;
    arrival→0 with no served-rate floor.
  - Added 1 more test for review finding F1 (replica-count-weighted avgOL, see above).

## Verified (re-run after F1+F2 fixes)
- go build ./... — clean
- gofmt -l $(find ./internal ./pkg ./cmd -name '*.go') — clean
- go vet ./... — clean
- make test — full suite green (all packages)
- make lint — 0 issues
- DCO sign-off present on all 4 commits (verified via git log)

## Developer guide
- docs/developer-guide/throughput-analyzer.md, Demand Estimation section (owned by this PR):
  rewritten around the model-level Λ_req×avgOL primary term (now correctly nKV-weighted across
  variants), a "Warm-Up Safety and Weighting" subsection, and a "Per-Variant Demand
  (Introspection Only)" subsection for the retained-but-decoupled priority chain.
- Also touched (same doc, outside the assigned ~L443-501 range, but restating formulas the
  Demand Estimation rewrite made stale): "Model-Level Aggregation" TotalDemand formula, the
  "Data Flow" ASCII diagram's model-level demand line, and "Role-Aware Aggregation"'s
  `distributeQueueDemandByRole` → `distributeDemandByRole` rename + prefill-role explanation.
- Did **not** touch Metrics/PromQL, Package, or Supply sections (PR A `ta-devguide-fixes`
  territory) — confirmed unaffected by review.
- `multi-analyzer-pipeline.md`'s `AnalyzerInput` field table: added `ArrivalRate` row (F2 fix,
  outside this PR's originally-named dev-guide scope, but a direct consequence of the struct
  change this PR makes).

## Open questions for Dean
(none — both findings were already ruled on before this fix pass)

## Not done / known limitations
- **Real behavior change, not a bug (unchanged from before, reviewed and accepted):** with EPP
  absent model-wide (`AnalyzerInput.ArrivalRate == 0`) and no scheduler queue, TA now reports
  model-level `TotalDemand == 0` where it previously derived a k*-based estimate from per-variant
  KV utilization. This is the plan's own documented deferral ("does not affect model-level
  demand... revisit when k_knee is implemented"); review's finding 8 confirmed this is exactly
  the plan's intended deferral, not a silent behavior change, and is not blocking.
- k_knee, the computeDemand per-replica fallback, and the per-instance arrival merge are all
  DEFERRED/DROPPED per the plan's own Deferred section — not revisited here.

## Notes
Internal review ran once (FINAL, 2 blocking findings F1+F2, both now fixed per above). NOT
pushed — awaiting re-review and Dean's explicit push confirmation
(git push -u origin ta-model-level-demand).

During this session, the coder incorrectly launched an unauthorized research subagent
(EPP-metric fact-find) before starting Commit 1 — caught and corrected by Dean; recorded as a
feedback memory (`feedback_coder_no_unauthorized_subagents`) and flagged via a separate handoff
(`plan__coder-conventions-subagent-gate.md`) for a CODER-CONVENTIONS gap. Unrelated to code
correctness on this branch — noted here only for continuity if this session is resumed.
