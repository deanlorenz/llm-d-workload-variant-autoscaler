# ta-itl-demand-test-gaps — Internal Review (Type 6)

**Status:** FINAL (finalized by Dean 2026-08-03)
**Reviewer:** internal (plan-vs-diff, pre-push). No GitHub actions.
**Date:** 2026-08-02 (round 1) · 2026-08-03 (round 2)
**Branch:** `ta-itl-demand-test-gaps`, tip `96263639` (round 2; round-1 tip was `39241065`), base `main@6bfb73e1` (PR F #1503 merge).
**Plan:** [`planning/ta-itl-demand-test-gaps-plan.md`](ta-itl-demand-test-gaps-plan.md)
**Trigger:** `session/handoffs/review__ta-itl-demand-test-gaps-ready.md`

## Round 2 (2026-08-03) — delta review

**APPROVE — no blocking findings.** Two new commits on top of round-1's unchanged 3 (same SHAs;
no history rewrite):

- **`3f770fd6` — Commit-2 comment NIT fix.** Reworded the Tier-2 test comment from "pinned
  baseline" → "constant baseline B (DefaultBaselineITLSec = 0.006, default path)". Comment-only,
  no code change. Resolves the round-1 NIT exactly. ✓
- **`96263639` — Commit 4: direct `computeVariantSupply` coverage** ([analyzer_test.go:2118](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer_test.go#L2118), new `Describe`).
  - *aggregates supply* — `cap=65536, itlSat=0.05` → `nSat = 0.85·65536/1024 = 54.4`,
    `total = 54.4/0.05 = 1088 > 0`, `nKV=1`, `perReplica==total` (single replica). ✓
  - *skips non-positive capacity* — `cap=0` → skip at [analyzer.go:683](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L683) → `(0,0,0)`; asserts `nKV==0`, `total==0`, `perReplica==0`. ✓
  - Non-vacuous: the aggregate case proves a capable replica yields `total>0`, so the skip case's
    `total==0` + `nKV==0` genuinely prove the guard fired. Mirrors the `computeLocalDemand`
    `Describe` shape, as the plan's Commit-4 § specifies.
- Both commits atomic (comment-only / new-Describe-only), both DCO-signed.
- Gates (reviewer-run): `go test ./…/throughput/...` PASS, `gofmt -l` clean.
- **Minor observation (NTH, not raised as a finding):** the capacity skip is tested at `cap=0`;
  a strictly-negative `TotalKvCapacityTokens` still isn't directly exercised. Same `<= 0` branch,
  and negative capacity isn't a physically meaningful value, so `== 0` is the meaningful boundary
  — low value, noted only for completeness.
- **`checkVariantGPSMismatch` correctly deferred** (per plan Commit-4 §): still uncovered, now the
  sole remaining item in the coverage-gap section below.

Round-1 findings unchanged and still valid; they are recorded verbatim below.

## Verdict (round 1)

**APPROVE — no blocking findings.** Three test-only commits, each exactly matching a plan
commit. All three new specs genuinely exercise their intended guard branches (verified by
control-flow + arithmetic analysis, not just a green suite), and all three are non-vacuous
(they would fail if the guard were removed). One optional wording NIT on Commit 2. Ready to
push at Dean's discretion — but note the plan says "no PR, no push without Dean's direction."

## Scope of what was reviewed

Full diff `6bfb73e1..39241065` — 2 files, +45 lines, all test code:
- `internal/engines/analyzers/throughput/itl_model_test.go` (+4)
- `internal/engines/analyzers/throughput/analyzer_test.go` (+41)

No production code, no dev-guide changes. Matches the plan's non-goals (§Scope) exactly.

## Bugs

None found.

## Confirmed correct

### Commit `d6c3c250` — Inf B rejection in `validITLModel`
- `validITLModel(0.073, math.Inf(1))`: `a=0.073` passes the NaN/Inf-`a` and slope-epsilon
  checks; then `math.IsInf(b, 0)` at `itl_model.go:48` fires → `false`. Exercises exactly the
  named branch, symmetric with the pre-existing Inf-A case. ✓
- Placed alongside the existing `"rejects NaN B"` case, same shape. Matches plan Commit 1
  verbatim.

### Commit `11b261ea` — Tier-2 `validITLModel` rejection in `resolveITLModel`
This was the plan's flagged-risk commit ("a sign or magnitude slip would make the test pass
for the wrong reason — e.g. the `n==0` branch instead of the rejection branch"). Verified the
concern is cleared:
- `BeforeEach` (`analyzer_test.go:67`) creates a fresh `NewThroughputAnalyzer()` per spec, so
  no residual observations leak in. A single `Observe` of one replica leaves the OLS window
  **not ready** (confirmed against the sibling tier-2 tests' own comments), so Tier-1 is
  skipped and control reaches Tier-2. Even if the window *were* ready, `FitITLModel` returns
  `false` for `n<2` observations — Tier-1 cannot preempt.
- The replica has `KvUsageInstant=0.5 > 0` and `AvgITL=0.001 > 0`, so the Tier-2 loop body
  executes: `n=1`, `sumK2 = 0.25`. This is the **distinguishing difference** from the existing
  "all idle" test (`KvUsageInstant=0` → `n=0`), so the test provably reaches the
  `n>0 && sumK2>0` fit path, not the early fallthrough.
- Arithmetic: `hasFittedB=false` → `baselineB = DefaultBaselineITLSec = 0.006`.
  `numerator = (0.001−0.006)·0.5 = −0.0025`; `A = −0.0025/0.25 = −0.01`.
  `validITLModel(−0.01, 0.006)`: `a=−0.01 <= itlSlopeEpsilon(1e-12)` → rejected at the
  slope guard → `resolveITLModel` returns `(zero, itlReasonT2Failed, false)`. ✓
- Asserts `ok==false` and `reason==itlReasonT2Failed` — both hold. (The reason label alone does
  not distinguish this path from the idle path, but the control-flow analysis above shows the
  intended branch is the one actually taken.)

### Commit `39241065` — `computeLocalDemand` capacity / negative-ITL skips
- Both new cases are **non-vacuous**. The `computeLocalDemand` shape guard
  (`KVreq=1024`, `AvgOutputTokens=50 > DefaultMinDecodeOLForLocalDemand`) does not early-return
  0 — the pre-existing NaN test proves a healthy `replicaAt(0.5)` yields `total > 0`. So
  `total == 0` genuinely proves a per-replica skip fired.
- **Non-positive capacity:** `replicaAt(0.5)` with `TotalKvCapacityTokens=0`. `KvUsageInstant=0.5`
  is valid and `model.ITLAt(0.5)=0.0425 > 0`, so the *only* skip trigger is
  `m.TotalKvCapacityTokens <= 0` (condition-1's capacity clause at `analyzer.go:641`). ✓
- **Finite non-positive ITL:** `ITLModel{A:0.01, B:−0.1}` → `ITLAt(0.5) = −0.095`, finite and
  negative (distinct from the existing NaN-coefficient case). Skips at `itlAtK <= 0`
  (`analyzer.go:652`). Even stronger non-vacuity: without the guard, a negative `itlAtK` makes
  `total` *negative*, not 0 — so `total == 0` uniquely identifies the skip. ✓
- The `Expect(...ITLAt(0.5)...).To(BeNumerically("<=", 0), "fixture sanity check")` guards
  against future `shape`/`replicaAt` constant drift silently defeating the fixture. Good
  practice; matches plan.

## NIT (non-blocking)

- **Commit 2 comment wording — "pinned baseline".** The inline comment
  (`analyzer_test.go:561`) says *"AvgITL below the pinned baseline (DefaultBaselineITLSec =
  0.006)"*. This case actually runs the **default-baseline** path (`hasFittedB=false` →
  `tier2Label = itlReasonT2Default`), not the pinned path (`itlReasonT2Pinned`). "Pinned" is
  defensible in the sense that `B` is held constant during the Tier-2 fit, but it collides with
  the `itlReasonT2Pinned` label name and could mislead a future reader into thinking this test
  exercises the pinned-`B` branch. Optional reword: *"…below the constant baseline B
  (DefaultBaselineITLSec = 0.006, default path)…"*. Text-only; no behavioral impact.

## Plan adherence / deliberate omissions (all acceptable)

- Both NTH extras were correctly **skipped** per the plan's "only if convenient" guidance:
  Commit 2's `itlReasonT2Pinned`-path rejection case, and Commit 3's zero-`KvUsageInstant`
  boundary case. Within scope; no expansion of scope. ✓
- No dev-guide edits — correct, the guards are already documented (plan §Scope). ✓
- Each commit is atomic (one file / one concern) and its message matches its diff. ✓
- All 3 commits carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. ✓

## Gates

- `go test ./internal/engines/analyzers/throughput/...` — **PASS** (reviewer-run).
- `gofmt -l` on both touched files — **clean** (reviewer-run).
- `make test` (full), `make lint`, `go build ./...`, `-race` — **relied on the coder's
  push-ready trigger claim** ("all gates green incl. -race on the touched package"); not
  independently re-run at full-repo scope in this review. Diff is additive test-only, so lint
  risk is minimal, but the planner may want the coder's full-suite run confirmed before push.

## Coverage gap surfaced while reviewing (out of this plan's scope — for a follow-up task)

The `TotalKvCapacityTokens <= 0` and `itlAtK <= 0` defensive guards that Commit 3 covers in
`computeLocalDemand` are duplicated in two sibling functions in the same file. This plan
correctly scoped to ev-shindin's three named gaps only, so these are **not** a defect in this
work — but Dean asked to address them, so recording for a new coverage task:

- **`computeVariantSupply`** ([analyzer.go:679](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L679)) — supply-path aggregation.
  - Guard [analyzer.go:683](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L683): `TotalKvCapacityTokens <= 0`.
  - ~~Coverage: partial/indirect.~~ **RESOLVED in round 2 (Commit 4, `96263639`)** — direct
    `Describe` added (aggregate → `total>0`; `cap=0` → skip → `(0,0,0)`). See the round-2 section
    above. (Strictly-negative capacity still not directly exercised — same `<= 0` branch, low
    value.)
- **`checkVariantGPSMismatch`** ([analyzer.go:770](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L770)) — GPS-mismatch **diagnostic** (bool drives root-cause logging).
  - Guards [analyzer.go:784](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L784) `TotalKvCapacityTokens <= 0` and [analyzer.go:788](../ta-itl-demand-test-gaps/internal/engines/analyzers/throughput/analyzer.go#L788) `itlAtK <= 0`
    (plus `GenerationTokenRate <= 0`, `KvUsageInstant < DefaultGPSMinKForVerification`, `muDecModel <= 0`).
  - Coverage: **none dedicated** — no `Describe`/`It` targets this function; skip clauses appear untested.
  - Value: diagnostic-only → lower-stakes than a supply/demand path.

Suggested handling: `computeVariantSupply` is now done (round-2 Commit 4). The remaining
`checkVariantGPSMismatch` coverage is a small **future** test-coverage task (diagnostic-only,
lower value; 4 earlier skip guards to satisfy first, no existing test block) — deferred by the
planner per the round-2 scoping handoff, not folded into this branch.

## Follow-ups for the planner

- **Commit-2 NIT — FIXED** in round 2 (`3f770fd6`). No further action.
- **`computeVariantSupply` coverage — DONE** in round 2 (`96263639`).
- **`checkVariantGPSMismatch` coverage — deferred** as a separate future test task (recorded here
  and in the round-2 scoping handoff). Backlog ref only; no branch cut.
- Push decision is Dean's per the plan. Branch is now **targeting 0.9 (freeze 2026-08-06)** per the
  round-2 scoping handoff; PR/push once Dean confirms. Round-2 gates re-run at package scope only —
  planner may want the coder's full `make test`/`make lint`/`-race` reconfirmed before push.
