# Anchor Refactor — Characterization Goldens — Type 3 Task Plan

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-anchor-goldens`, cut from the current tip of `main`
(the moving ref — `git worktree add -b ta-anchor-goldens … main`, never a pinned SHA). Authored
against `main@9906dac5` (`chore: correct make target … (#1507)`); re-verify anchors against the
branch's actual base before coding.
**Size:** 4 test-only commits (+ 1 optional secondary), no production code changes expected ·
**Reviewer session:** internal re-review per CODER-CONVENTIONS §5.4 before push; near-zero risk
(additive characterization tests only).
**Depends on:** nothing. **Runs in parallel** with the anchor-refactor PR (see
[§ Coordination](#coordination-coordination)). **Targeting 0.9** (code freeze 2026-08-06) — this is
the ship-gate mechanism for the anchor refactor and should land first (or its commit becomes the
base the anchor branch builds on). No push to origin without Dean's explicit per-push confirmation.

## Purpose in one paragraph

The anchor refactor ([`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md))
repoints the optimizer's sort/sizing/threshold reads from a saturation-only proxy to a combined
"binding-analyzer anchor." Its load-bearing risk control is design invariant #7: **when exactly one
analyzer votes, the pipeline must produce the same decisions as today** (the default config is
sat-v2-only, so this is the path every current user is on). This branch builds the deterministic,
unit-level baseline that *proves* that invariant — characterization goldens over the current
sat-v2-only optimizer behavior, captured from `main`, that the refactor branch must keep green.
There are no reproducible e2e goldens (Ofer's cluster runs reseed), so this unit-level baseline is
the only thing we *can* fully pin down — and it covers the exact path that reaches every non-opt-in
user.

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L48:68
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L69:94
- [Background — what we freeze and where it lives {#background}](#background--what-we-freeze-and-where-it-lives-background) L95:133
- [The determinism constraint (read before writing any assertion) {#determinism}](#the-determinism-constraint-read-before-writing-any-assertion-determinism) L134:156
- [Fixtures and scenarios {#fixtures}](#fixtures-and-scenarios-fixtures) L157:184
- [Commit 1 — harness + order-insensitive comparison helper {#commit-1}](#commit-1--harness--order-insensitive-comparison-helper-commit-1) L185:205
- [Commit 2 — aggregated (RoleBoth) optimizer goldens {#commit-2}](#commit-2--aggregated-roleboth-optimizer-goldens-commit-2) L206:223
- [Commit 3 — disaggregated (P/D) optimizer goldens {#commit-3}](#commit-3--disaggregated-pd-optimizer-goldens-commit-3) L224:242
- [Commit 4 — quota-constrained + both-optimizer goldens {#commit-4}](#commit-4--quota-constrained--both-optimizer-goldens-commit-4) L243:258
- [Commit 5 (secondary, optional) — rescale characterization {#commit-5}](#commit-5-secondary-optional--rescale-characterization-commit-5) L259:275
- [Coordination with the anchor-refactor branch {#coordination}](#coordination-with-the-anchor-refactor-branch-coordination) L276:296
- [If capture surprises you {#surprises}](#if-capture-surprises-you-surprises) L297:314
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L315:331

## Overview {#overview}

This branch adds **characterization tests** (a.k.a. golden/approval tests) to
`internal/engines/pipeline/`. A characterization test captures *whatever the current code does* as
the expected value — it is not derived from a spec. Its purpose is to detect *change*: if a later
refactor alters the output, the test goes red.

Concretely: hand-authored, frozen `ModelScalingRequest` inputs (single-analyzer, sat-v2-only) are
fed through `Optimize` (both optimizer implementations) and the resulting decision set is asserted
against expected values captured from the current `main`. The **same test file rides unchanged onto
the anchor-refactor branch**, where it becomes the gate: if the refactor preserves the default
(single-vote) behavior — which design invariant #7 requires — the tests stay green; if it drifts,
they catch it.

Because the expected values are captured from current code, **every test in this branch passes by
construction** against `main`. A red test here means the *fixture* is wrong (see
[§ If capture surprises you](#if-capture-surprises-you-surprises)), not that production code is
buggy. (This is the opposite of a spec-driven test-gap plan, where a red test flags a real bug.)

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope:**
- A new in-package test file (`package pipeline`) under `internal/engines/pipeline/` holding
  table-driven characterization cases for the optimizer decision path.
- An order-insensitive decision-set comparison helper (or reuse of the pattern already in
  `optimizer_equivalence_test.go`).
- Fixtures covering the scenarios in [§ Fixtures](#fixtures-and-scenarios-fixtures): aggregated
  (RoleBoth) scale-up/down/no-op, multi-variant cost tie-break, disaggregated (P/D) scale-up/down,
  quota-constrained allocation — each run through both `CostAwareOptimizer` and
  `GreedyByScoreOptimizer` where applicable.
- (Secondary, optional) rescale-path characterization (Commit 5).

**Non-goals:**
- **No production code changes.** If you feel one is needed, stop and write a handoff — this branch
  must stay purely additive so it can land ahead of (or merge cleanly into) the refactor.
- **No multi-analyzer / two-vote fixtures.** Throughput cannot be enabled today without breaking the
  math, so there is no current behavior to characterize for the two-vote path; that path is the
  opt-in future the refactor unlocks and is out of scope here.
- **No e2e / cluster tests.** Ofer's seeded runs are not reproducible; this baseline is deliberately
  unit-level and pure-function.
- **No dev-guide changes.** Test-only, no user-visible behavior; nothing in
  `docs/developer-guide/` changes on this branch.

[↑ TOC](#toc)

## Background — what we freeze and where it lives {#background}

Package: **`pipeline`** (`internal/engines/pipeline/`), Ginkgo-driven off `suite_test.go`. Tests use
`package pipeline` (internal), so unexported functions are reachable.

**Entry points to exercise:**
- `internal/engines/pipeline/cost_aware_optimizer.go:39` — `func (o *CostAwareOptimizer) Optimize(ctx, requests []ModelScalingRequest, constraints []*ResourceConstraints) []domain.VariantDecision`.
- `internal/engines/pipeline/greedy_score_optimizer.go:97` — `func (o *GreedyByScoreOptimizer) Optimize(...)` (same signature shape).
- Both funnel through `buildDecisionsWithOptimizer` (`cost_aware_optimizer.go:243`), which sets
  `decision.Utilization` at `:302` and `RequiredCapacity`/`SpareCapacity` from the saturation entry
  at `:303–314`.

**Fields to freeze per decision** (the ones the anchor refactor repoints — see design § bugs):
- target replica count (the decision's desired replicas),
- `RequiredCapacity`,
- `SpareCapacity`,
- `Utilization`.

**Existing test files to mine for fixture shape and helpers** (read these before authoring):
- `optimizer_equivalence_test.go` — 4 specs comparing `CostAware` vs `GreedyByScore`
  order-insensitively when GPUs are unconstrained. **This is the closest existing pattern** and the
  best template for the comparison helper.
- `cost_aware_optimizer_test.go` (~65 specs), `greedy_score_optimizer_test.go` (~69 specs) — fixture
  builders for `ModelScalingRequest`, `[]NamedAnalyzerResult`, `[]domain.VariantReplicaState`,
  `domain.VariantCapacity` (including `RoleCapacities` for P/D).
- `rescale_optimize_test.go` (~26 specs) — for Commit 5.

**Input types** (in `internal/engines/pipeline/optimizer_interfaces.go` and `internal/domain/`):
`ModelScalingRequest`, `NamedAnalyzerResult` (has `Name`, `Result`, `Score`, `Live`, `Remaining`,
`Spare`, `RoleSpare`), `domain.AnalyzerResult` (has `VariantCapacities`, `RequiredCapacity`,
`SpareCapacity`, `RoleCapacities`, `TotalSupply`, `TotalAnticipatedSupply`, `TotalDemand`),
`domain.VariantCapacity` (`VariantName`, `PerReplicaCapacity`, `Cost`, `AcceleratorName`, `Role`,
`ReplicaCount`, `PendingReplicas`, `Utilization`). The single-analyzer entry keys on
`domain.SaturationAnalyzerName` (this is the `saturationEntry()` helper at `analyzer_helpers.go:91`
that the refactor renames — you do not touch it here, but your fixtures must populate a sat-v2 entry
under that name so the current code path is exercised).

[↑ TOC](#toc)

## The determinism constraint (read before writing any assertion) {#determinism}

`Optimize`'s per-decision **content** is deterministic, but its output **slice order is not**:

- `buildDecisionsWithOptimizer` iterates `for name, target := range targets` (`cost_aware_optimizer.go:257`)
  — Go map iteration order is randomized, so the `[]domain.VariantDecision` slice comes out in a
  different order across runs.
- `sortByRemainingDesc` (`greedy_score_optimizer.go:462`) uses `sort.Slice` (unstable) with a
  `remaining >` comparator and **no tie-break**, so equal-`remaining` models can reorder — which can
  even shift allocation under exact ties.

**Therefore: never assert slice order or slice equality.** Compare the decision set as a map keyed by
`VariantName` (and, where a variant appears per-role, by `(VariantName, Role)`). Sort-before-compare
or build a `map[string]expectedDecision` and compare field-by-field with a float tolerance
(`BeNumerically("~", want, 1e-9)`) for the capacity/utilization floats.

Mirror the comparison approach already used in `optimizer_equivalence_test.go` — do not invent a new
one if that helper already keys by variant. If you must add tie-break determinism to make a fixture
stable, **do not** change production code — instead choose fixture inputs whose `remaining` values
are distinct so the unstable sort has nothing to reorder, and note the constraint in a comment.

[↑ TOC](#toc)

## Fixtures and scenarios {#fixtures}

All fixtures are **single-analyzer, sat-v2-only** (one `NamedAnalyzerResult` named
`domain.SaturationAnalyzerName`, `Score: 1.0`, `Live: true`). This is the default config and the
exact path invariant #7 must preserve. Each scenario is chosen to exercise a site the anchor refactor
repoints, so the golden pins the current (masked-correct) behavior at that site:

| # | Scenario | Exercises (refactor repoint site) |
|---|---|---|
| A1 | Aggregated (RoleBoth) single-variant **scale-up** | `allocateForModelPaired` util/k/subtraction `analyzer_helpers.go:366–414`; model-level RC/SC via `applyUniversalThreshold` `engine_v2.go:453/460` |
| A2 | Aggregated single-variant **scale-down** | `safeRemovalReplicasForRole` `:246`, `needsScaleDownForRole` veto `:301` |
| A3 | Aggregated **no-op / at-target** | end-to-end no-change path (guards against spurious churn) |
| A4 | **Multi-variant** cost tie-break, RoleBoth | `sortVariantsForScaleDown` Σ`Score·PRC` `cost_aware_optimizer.go:168`; `costEfficiency` `:234` |
| B1 | **Disaggregated** (P/D) scale-up (`RoleCapacities` prefill+decode) | per-role `initRoleState` `:127`, joint-commit min-util in `allocateForModelPaired` |
| B2 | Disaggregated scale-down | per-role `safeRemovalReplicasForRole` / veto across roles |
| C1 | **Quota-constrained** allocation (cluster and/or ns budget binding) | `effectiveAvailable` `greedy_score_optimizer.go:371`; `fairShareRolePick` cap `:421` |

Each scenario is run through **both** `CostAwareOptimizer` and `GreedyByScoreOptimizer` where the
inputs are meaningful for both (A1–A4, B1–B2). C1 is primarily a greedy-path fixture; run it through
whichever optimizer(s) the existing quota tests use as the model.

Capture the expected decision set for each `(scenario, optimizer)` pair from the current `main` code
and write it inline. Comment each golden block: *"captured from `main@<sha>`; encodes current
sat-v2-only behavior including any masked bugs #1/#2/#3/#5 — this is intentional: the refactor must
preserve the default path exactly."*

[↑ TOC](#toc)

## Commit 1 — harness + order-insensitive comparison helper {#commit-1}

**File:** new `internal/engines/pipeline/optimizer_characterization_test.go` (`package pipeline`).

Establish the scaffolding only (no goldens yet, or one trivial smoke golden):

1. A `type goldenDecision struct { Replicas int; RequiredCapacity, SpareCapacity, Utilization float64 }`
   (or reuse the fields directly).
2. A comparison helper `expectDecisionSet(got []domain.VariantDecision, want map[string]goldenDecision)`
   that keys `got` by `VariantName` (or `(VariantName, Role)` where roles split), asserts the key
   sets match, and compares each field with `BeNumerically("~", …, 1e-9)` for floats and exact for
   the replica count. **Reuse `optimizer_equivalence_test.go`'s keying if it already does this.**
3. A fixture-builder helper for a single sat-v2-only `ModelScalingRequest` given variant specs
   (name, PRC, cost, accel, role, current/pending replicas, demand/supply), mirroring the builders in
   `cost_aware_optimizer_test.go`.

Gate: `make test` green (the helper file compiles and any smoke case passes). No behavior asserted
yet beyond scaffolding.

[↑ TOC](#toc)

## Commit 2 — aggregated (RoleBoth) optimizer goldens {#commit-2}

Add scenarios **A1–A4** (see [§ Fixtures](#fixtures-and-scenarios-fixtures)) as table-driven cases,
each run through both optimizers.

**Non-vacuity guards** (mandatory — a golden that captures an early-return is worthless):
- A1 (scale-up): assert the target replica count is **strictly greater** than current for the scaled
  variant, so the golden proves the allocation loop actually ran.
- A2 (scale-down): assert at least one variant's target is **strictly less** than current.
- A3 (no-op): assert every target **equals** current (this one is *supposed* to be vacuous — that is
  the property being frozen).
- A4 (multi-variant): assert the decision set has **all** expected variants present.

Capture expected values from current `main`; comment per the [§ Fixtures](#fixtures-and-scenarios-fixtures)
convention. Gate: `make test` green.

[↑ TOC](#toc)

## Commit 3 — disaggregated (P/D) optimizer goldens {#commit-3}

Add scenarios **B1–B2**: fixtures whose sat-v2 entry populates `RoleCapacities` with `prefill` and
`decode` roles (per-role RC/SC), so `initRoleState` (`analyzer_helpers.go:127`) takes the
disaggregated branch (not the synthetic `RoleBoth`).

Mine `cost_aware_optimizer_test.go` / `greedy_score_optimizer_test.go` for an existing P/D fixture
builder before writing your own — the `RoleCapacities` map shape and the `RoleSpare` initialization
are fiddly and there is almost certainly a helper.

**Non-vacuity guards:**
- B1: assert the scale-up changed replica counts for the P/D variant, and that **both** roles were
  considered (the decision reflects the joint min-util commit, not a single-role bump).
- B2: assert a scale-down occurred and the per-role veto did not spuriously block it.

Capture from current `main`; comment. Gate: `make test` green.

[↑ TOC](#toc)

## Commit 4 — quota-constrained + both-optimizer goldens {#commit-4}

Add scenario **C1**: a fixture where the cluster and/or per-namespace GPU budget binds before demand
is satisfied, so `effectiveAvailable` (`greedy_score_optimizer.go:371`) and the `fairShareCap`
(`:421`) clamp the allocation. Model it on the existing quota tests
(`quota_limit_integration_test.go`, `default_limiter_namespace_test.go`) for the `ResourceConstraints`
/ budget shape.

**Non-vacuity guard:** assert the allocation is **strictly below** what unconstrained demand would
give (i.e. the budget actually bit), and that the golden differs from the same fixture run with an
unbounded budget. Otherwise the "constrained" golden proves nothing.

Capture from current `main`; comment. Gate: `make test` green (full suite, no regressions).

[↑ TOC](#toc)

## Commit 5 (secondary, optional) — rescale characterization {#commit-5}

**Only if time permits before freeze.** The rescale path (`rescale.go`) reads the saturation entry
for topology at `:225/:342/:465/:486/:589/:604`. The anchor refactor keeps the carrier always
present, so rescale's reads should be identity-preserving — lower byte-identity risk than the
optimizer sort/sizing path, which is why this is secondary.

If you take it: add a small characterization block modeled on `rescale_optimize_test.go` covering the
scale-down-after-load path, keyed order-insensitively like the optimizer goldens. Freeze the rescale
decision output for one aggregated and one P/D fixture.

If you **don't** take it: note in your handoff that rescale characterization is deferred, so the
planner records the residual gap (the anchor branch then relies on the existing `rescale_test.go` /
`rescale_optimize_test.go` for rescale coverage).

[↑ TOC](#toc)

## Coordination with the anchor-refactor branch {#coordination}

The value of these goldens is realized only when the **same test file runs on the anchor-refactor
branch** and stays green. Two ways to get it there; the planner will pick with Dean:

1. **Land goldens first (preferred).** This branch becomes a small, low-risk PR that merges to `main`
   ahead of the refactor; the anchor branch is then cut from (or rebased onto) that merge, inheriting
   the goldens as its ship gate.
2. **Cherry-pick.** If the refactor branch was already cut from an earlier `main`, the anchor coder
   cherry-picks this branch's test commit(s) onto their branch before starting the repoint work.

Either way, **the test file is authored once, here, and is not edited by the anchor coder** except to
split a `(VariantName)` key into `(VariantName, Role)` if the refactor legitimately changes the
decision *shape* (it should not for single-vote — flag loudly if it does). Record the branch tip in
your status file so the planner can point the anchor kickoff at the exact commit.

**Do not** assume the anchor branch exists yet; your job is to produce a green, self-contained
baseline on `ta-anchor-goldens`. The handoff to the planner is what triggers the coordination.

[↑ TOC](#toc)

## If capture surprises you {#surprises}

Because goldens capture current behavior, a test should never be red against `main`. If one is:

- **Most likely:** the fixture hits an early return (empty decisions, no scale change) and your
  non-vacuity guard fired — the fixture doesn't exercise the intended path. Fix the fixture inputs
  (e.g. make demand exceed supply for a scale-up), not the assertion.
- **Flaky across runs:** you asserted slice order, or an equal-`remaining` tie let the unstable sort
  reorder. Re-key the comparison by variant, or make `remaining` values distinct
  (see [§ determinism](#the-determinism-constraint-read-before-writing-any-assertion-determinism)).
- **Genuinely unexpected output** (a value that looks wrong even for current code): do **not** encode
  it silently and do **not** patch production code. Note it in your status file and a `plan__` handoff
  — it may be one of the masked bugs the refactor will fix, in which case the golden is still correct
  to freeze (the refactor changes it deliberately on the multi-vote path, not the single-vote path),
  but the planner needs to know which goldens are expected to move later.

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Run in order (per CONVENTIONS pre-push checklist), but note the scope limit below:
1. `git branch --show-current` — confirm `ta-anchor-goldens`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (new tests plus full suite, no regressions); run a few times to confirm no
   order-dependence flakiness.
4. `make lint` — clean.
5. DCO — every commit `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
6. `go build ./...` — clean.

**Do not push.** Once gates are green, write the `review__ta-anchor-goldens-ready.md` trigger per
CODER-CONVENTIONS §5.4 so an internal review can happen, then stop — leave the branch committed
locally and set your status file to "implemented, awaiting review," not "ready to push." The planner
folds the outcome into CURRENT.md and coordinates the land-first-vs-cherry-pick decision with Dean.

[↑ TOC](#toc)
