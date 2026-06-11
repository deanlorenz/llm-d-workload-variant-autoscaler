from: reviewer
session: multi-analyzer-addendum code review

## Review status

Branch `multi-analyzer-addendum` reviewed against plan
`planning/multi-analyzer-addendum-plan.md`. All gates green (make test, make
lint, gofmt, go build, DCO). 4 commits on upstream/main.

Two findings require action before push. Both are in non-Go files or test
strings — no production logic changes needed.

---

## Finding F1 — REQUIRED: Strip plan identifiers from test Describe/It labels

**Files:** `internal/engines/saturation/engine_v2_test.go`

Per CODER-CONVENTIONS §4a, plans-branch identifiers must not appear in
code-side artifacts. These are currently in test string labels:

- Line 283: `Describe("runAnalyzersAndScore enabled gate (MA-F7)", ...)`
- Line 285: `It("MA-F7: disabled analyzer is not appended and its Analyze is never called", ...)`
- Line 316: `Describe("collectV2ModelRequest Disaggregated flag (MA-H-1)", ...)`

Replace with descriptive prose, e.g.:
- `Describe("runAnalyzersAndScore disabled-analyzer gate", ...)`
- `It("disabled analyzer is not appended and its Analyze is never called", ...)`
- `Describe("collectV2ModelRequest Disaggregated flag", ...)`

`T1.4` in `greedy_score_optimizer_test.go:764` follows the existing T1.x
convention already in that file — leave it unchanged.

---

## Finding F2 — REQUIRED: Expand dev guide with architecture, data flow, and optimizer internals

**File:** `docs/developer-guide/multi-analyzer-pipeline.md`

The current doc (commit 3 / `a91c7513`) is missing the architecture-level
content that makes the pipeline understandable to contributors. This is the
content that would have prevented the #1252 reviewer confusion about the data
flow.

The full draft of the expanded doc is at:
`plans/scratch/multi-analyzer-pipeline-doc-draft.md`

Apply it as-is as a new commit (doc-only; no code changes; gates expected clean).

The draft adds:
1. **`## Architecture`** section (before `## Components`) with:
   - ASCII data-flow diagram: Config → Engine prep → run analyzers + post-step
     → ModelScalingRequest → Optimizer → VariantDecisions
   - Key concepts table (Analyzer, VariantCapacity, AnalyzerResult,
     RoleCapacity, NamedAnalyzerResult, Linearity invariant)
   - Responsibility table (who writes / reads each field)
2. **`## Data model: AnalyzerResult → NamedAnalyzerResult`** section (after
   `## How results combine`) explaining immutable vs mutable fields and
   RolePairedState lifecycle.
3. **`## Optimizer internals and helper composition`** section with:
   - Scale-up path: allocateForModelPaired call chain, RolePickFn split
   - Scale-down path: scaleDownRoleIterated (same loop for both and role)
   - Fair-share iteration algorithm (GreedyByScoreOptimizer)

Suggested commit message:
`docs: add architecture, data flow, and optimizer internals to pipeline guide`

---

## Finding F3 — NTH (not blocking): optimizers.md consolidation

PR #1223 (ev-shindin, `docs: add scaling optimizers developer guide`) is OPEN.
When it merges, the "Optimizer consumption" section of `multi-analyzer-pipeline.md`
will overlap with it. File a follow-up issue to consolidate (replace the
self-contained paragraph with a link to `optimizers.md`) after #1223 lands.
Not required before this PR merges.

---

## Confirmed correct (no action needed)

- MA-F7 bug fix: `effectiveEnabled` helper correct; skip-the-run (not just
  skip-the-append) confirmed. All 4 unit specs + integration spec cover the
  right behaviors.
- `saturationV2Analyzer` interface widening in `engine.go` is clean; commit 4
  correctly removes the now-redundant type conversion in `engine_register_test.go`.
- MA-H-1 config-bridge specs: Score, Score-default, ScaleUpThreshold override
  all covered. Disaggregated true/false specs correct.
- MA-OPT-4 T1.4: non-uniform Score spec is correct; fsv math matches actual
  `greedy_score_optimizer.go` formula.
- Commit messages match their diffs.
- DCO: all 4 commits signed.
