# ThroughputAnalyzer — ITL/Demand Test-Gap Follow-ups — Type 3 Task Plan

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-itl-demand-test-gaps`, cut from the current tip of
`main` (the moving ref — `git worktree add … main`, never a pinned SHA). Authored against
`main@6bfb73e1` (the PR F `#1503` merge commit); re-verify anchors against the branch's actual
base before coding.
**Size:** 3 small test-only commits, no production code changes expected · **Reviewer
session:** standard internal review per CODER-CONVENTIONS §5.4 before any push; low risk
(additive tests only).
**Depends on:** nothing. **Not scheduled for 0.9** — this is deferred, optional follow-up work
with no release deadline; do not open a PR or push to origin without Dean's explicit direction.

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L28:45
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L46:64
- [Background {#background}](#background-background) L65:102
- [Commit 1 — Inf B rejection in validITLModel {#commit-1}](#commit-1--inf-b-rejection-in-validitlmodel-commit-1) L103:120
- [Commit 2 — Tier-2 validITLModel rejection in resolveITLModel {#commit-2}](#commit-2--tier-2-validitlmodel-rejection-in-resolveitlmodel-commit-2) L121:173
- [Commit 3 — computeLocalDemand non-positive-capacity/negative-ITL skips {#commit-3}](#commit-3--computelocaldemand-non-positive-capacitynegative-itl-skips-commit-3) L174:210
- [If a gap reveals a real bug {#bug-found}](#if-a-gap-reveals-a-real-bug-bug-found) L211:224
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L225:241

## Overview {#overview}

During review of PR F `#1503` (`ta-correctness-guards`), ev-shindin flagged three test-coverage
gaps as **optional and non-blocking** — he chose not to add them himself and explicitly said so
in his approval:

> "Minor untouched test gaps if you want them here: Tier-2 `validITLModel` rejection,
> `validITLModel` with `Inf B`, and `computeLocalDemand`'s non-positive-capacity/negative-ITL
> skips."

All three guards already exist in shipped code (landed via F's commits `5dad3709` shared
`validITLModel`, and `9015bb06` the `computeLocalDemand` NaN/range guard). This plan is pure
test-coverage follow-up — no behavior is expected to change. If a new test fails against current
code, that means the guard doesn't actually work as documented and is a **real bug**, not a test
bug — see [§ If a gap reveals a real bug](#if-a-gap-reveals-a-real-bug-bug-found).

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope:**
- Three additive unit/Ginkgo test cases, one per gap ev-shindin named.
- No dev-guide changes expected — the guards are already documented (Type 4 doc already covers
  `computeLocalDemand`'s guards and the shared validator, added in F's `0c35d717`). Only touch
  the dev guide if a gap turns out to reveal an undocumented behavior.

**Non-goals:**
- No production code changes, unless a test exposes a real bug (see
  [§ If a gap reveals a real bug](#if-a-gap-reveals-a-real-bug-bug-found)).
- No new guards beyond the three named gaps. If you notice other coverage gaps while in this
  code, note them in your handoff rather than expanding scope.
- No PR, no push to origin. This work has no 0.9 deadline — implement, get an internal review,
  leave it committed locally, and write a status file. The planner will decide when/whether to
  push based on Dean's direction.

[↑ TOC](#toc)

## Background {#background}

- `internal/engines/analyzers/throughput/itl_model.go:33` — `validITLModel(a, b float64) bool`.
  Shared by the Tier-1 OLS fit (`FitITLModel`) and the Tier-2 constrained fit (`resolveITLModel`)
  per its doc comment. Existing tests: `internal/engines/analyzers/throughput/itl_model_test.go:114-139`
  (`Describe("validITLModel", ...)`) — covers valid-accept, NaN A, Inf A, flat slope, NaN B,
  non-positive-ITL-at-saturation. **Missing: Inf B** (the `math.IsInf(b, 0)` branch at
  `itl_model.go:48` is untested — symmetric with the already-tested Inf A case at line 36).

- `internal/engines/analyzers/throughput/analyzer.go:529` —
  `(*ThroughputAnalyzer) resolveITLModel(...)`. Tier-2 (constrained OLS, B pinned) computes
  `A = numerator/sumK2` from per-replica `(KvUsageInstant, AvgITL)` pairs, then calls
  `validITLModel(A, baselineB)` at line 570 before accepting the fit. Existing test: `analyzer_test.go:537`
  (`"resolveITLModel returns T2-failed when all replicas are idle"`) covers only the
  `n == 0` early-exit (no replica has `KvUsageInstant > 0`). **Missing:** the case where
  `n > 0 && sumK2 > 0` (a Tier-2 fit is actually computed) but the resulting `(A, baselineB)`
  fails `validITLModel` — e.g. `AvgITL` below the pinned baseline produces a negative `A`. This
  exercises `analyzer.go:576` (the `if validITLModel(...)` failing) and confirms the fallthrough
  to `itlReasonT2Failed` at line 578, distinct from the already-tested `n == 0` path.

- `internal/engines/analyzers/throughput/analyzer.go:635` —
  `computeLocalDemand(metrics []domain.ReplicaMetrics, shape WorkloadShape, model ITLModel) float64`.
  Per-replica skip conditions (lines 641–652):
  1. `math.IsNaN(m.KvUsageInstant) || m.KvUsageInstant <= 0 || m.TotalKvCapacityTokens <= 0` → skip
  2. `m.KvUsageInstant > 1` → skip
  3. `math.IsNaN(itlAtK) || itlAtK <= 0` → skip (`itlAtK := model.ITLAt(m.KvUsageInstant)`)

  Existing tests: `analyzer_test.go:2038-2075` (`Describe("computeLocalDemand", ...)`) — covers
  NaN `KvUsageInstant` (condition 1's NaN clause), `KvUsageInstant > 1` (condition 2), and NaN
  `itlAtK` via a NaN model `A` (condition 3's NaN clause). **Missing:**
  - condition 1's `TotalKvCapacityTokens <= 0` clause — a replica with valid, in-range
    `KvUsageInstant` but zero or negative `TotalKvCapacityTokens`.
  - condition 3's `itlAtK <= 0` clause when `itlAtK` is **finite and negative**, not NaN — e.g. a
    model with a negative `B` such that `A·k + B ≤ 0` at the test's chosen `k`, without either
    coefficient itself being NaN or Inf.

[↑ TOC](#toc)

## Commit 1 — Inf B rejection in validITLModel {#commit-1}

**File:** `internal/engines/analyzers/throughput/itl_model_test.go`

Add one `It(...)` alongside the existing `"rejects NaN B"` case (around line 131), following the
same shape:

```go
It("rejects Inf B", func() {
    Expect(validITLModel(0.073, math.Inf(1))).To(BeFalse())
})
```

Exercises `itl_model.go:48` (`math.IsInf(b, 0)`), symmetric with the already-tested Inf A case at
line 123.

[↑ TOC](#toc)

## Commit 2 — Tier-2 validITLModel rejection in resolveITLModel {#commit-2}

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`, in the `Describe` block
containing the existing Tier-2 tests (see the `tier2Replica` helper near line 460 and the
`"resolveITLModel returns T2-failed when all replicas are idle"` test at line 537).

Add a case where Tier-2 **computes** a fit (so `n > 0 && sumK2 > 0`, unlike the idle-only
existing case) but the fit is **rejected** by `validITLModel`. A single replica with `AvgITL`
below the pinned baseline `DefaultBaselineITLSec` (0.006s) produces a negative `A`:

```go
It("resolveITLModel returns T2-failed when the computed fit is rejected by validITLModel", func() {
    // AvgITL below the pinned baseline (DefaultBaselineITLSec = 0.006) at k=0.5 produces
    // numerator = (0.001 - 0.006) * 0.5 = -0.0025, sumK2 = 0.25 → A = -0.01 (negative,
    // inverted slope) — a real Tier-2 fit is computed (n=1, sumK2>0) but validITLModel
    // rejects it, unlike the existing "all idle" test which never reaches the fit at all.
    belowBaseline := domain.ReplicaMetrics{
        VariantName: "v1", KvUsageInstant: 0.5, KvCacheUsage: 0.5,
        AvgITL: 0.001, AvgInputTokens: 5000, AvgOutputTokens: 200,
        PrefixCacheHitRate: 0.1, TotalKvCapacityTokens: 1024000,
    }
    analyzer.Observe(ctx, time.Now(), modelID, namespace, []domain.ReplicaMetrics{belowBaseline})

    _, reason, ok := analyzer.resolveITLModel(ctx,
        func() *variantState {
            analyzer.mu.Lock()
            defer analyzer.mu.Unlock()
            return analyzer.variantStates[variantKey(namespace, modelID, "v1")]
        }(),
        []domain.ReplicaMetrics{belowBaseline},
        namespace, modelID, "v1",
    )
    Expect(ok).To(BeFalse())
    Expect(reason).To(Equal(itlReasonT2Failed))
})
```

Verify the arithmetic against the actual `resolveITLModel` numerator/denominator formula
(`analyzer.go:559-569`) before committing — recompute by hand or add a temporary `fmt.Println` in
a scratch test run, since a sign or magnitude slip here would make the test pass for the wrong
reason (e.g. hitting the `n==0` branch instead of the intended rejection branch). Confirm via a
debug run that `n == 1` and `sumK2 > 0` are actually reached (i.e. the test exercises line 570's
`if validITLModel(...)` and not an early return).

**Optional (NTH, not required):** a second case exercising the same rejection through the
`itlReasonT2Pinned` path (a prior Tier-1 fit sets `state.lastFittedB` to some positive value,
then a new replica set produces a fit that fails `validITLModel` against that pinned `B` instead
of the default). Only add if it's cheap given the existing `injectWindowObs` helper
(`analyzer_test.go:505`); skip otherwise — the default-B case above already exercises the
rejection branch.

[↑ TOC](#toc)

## Commit 3 — computeLocalDemand non-positive-capacity/negative-ITL skips {#commit-3}

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`, in the
`Describe("computeLocalDemand", ...)` block (line 2038), alongside the existing three `It(...)`
cases.

Add two cases, following the existing `replicaAt` helper's shape:

```go
It("skips a replica with non-positive TotalKvCapacityTokens", func() {
    noCapacity := replicaAt(0.5)
    noCapacity.TotalKvCapacityTokens = 0
    total := computeLocalDemand([]domain.ReplicaMetrics{noCapacity}, shape, model)
    Expect(total).To(Equal(0.0))
})

It("skips a replica whose model produces a finite non-positive ITL", func() {
    // B negative enough that A*k+B <= 0 at k=0.5 without A or B being NaN/Inf —
    // distinct from the existing NaN-ITL case, which uses a NaN model coefficient.
    negativeITLModel := ITLModel{A: 0.01, B: -0.1}
    Expect(negativeITLModel.ITLAt(0.5)).To(BeNumerically("<=", 0), "fixture sanity check")
    total := computeLocalDemand([]domain.ReplicaMetrics{replicaAt(0.5)}, shape, negativeITLModel)
    Expect(total).To(Equal(0.0))
})
```

The `Expect(...ITLAt(0.5)...)` sanity check in the second case guards against a future constant
change in `shape`/`replicaAt` silently making the fixture no longer exercise the intended branch.

**Optional (NTH, not required):** `computeLocalDemand`'s condition 1 also skips
`KvUsageInstant <= 0` for finite non-NaN values (e.g. exactly `0`, or negative) — untested with a
plain non-NaN boundary value today (only the NaN case is covered). Add
`It("skips a replica with zero KvUsageInstant", ...)` if convenient; not one of ev-shindin's
three named gaps, so skip if it doesn't fit cleanly with the existing fixtures.

[↑ TOC](#toc)

## If a gap reveals a real bug {#bug-found}

These guards already ship in production code and are expected to work — this plan is coverage,
not a bug hunt. If any new test in Commits 1–3 **fails against current code**, stop before
"fixing the test to match reality": that means the guard doesn't do what its comment/commit
message claims, which is a correctness bug, not a coverage gap. Do not silently patch the
production code to make the test pass — this is exactly the kind of judgment call
CODER-CONVENTIONS expects you to raise rather than resolve unilaterally. Write a status-file note
and a `plan__` handoff describing the mismatch (expected behavior per the guard's doc comment vs.
actual behavior observed) and pause that one commit; the other two are independent and can
proceed.

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Run in order (per CONVENTIONS pre-push checklist), but note the scope limit below:
1. `git branch --show-current` — confirm `ta-itl-demand-test-gaps`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (new tests plus full suite, no regressions).
4. `make lint` — clean.
5. DCO — every commit `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
6. `go build ./...` — clean.

**Do not push.** This branch has no PR and no 0.9 deadline. Once gates are green, write the
`review__ta-itl-demand-test-gaps-ready.md` trigger per CODER-CONVENTIONS §5.4 so an internal
review can happen, then stop — leave the branch committed locally and update your status file to
reflect "implemented, awaiting review," not "ready to push." The planner will fold the outcome
into CURRENT.md and decide the timeline for a PR with Dean.

[↑ TOC](#toc)
