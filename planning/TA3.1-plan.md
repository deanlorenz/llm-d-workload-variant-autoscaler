# TA3.1 — Post-Review Follow-Up PR (PR-B)

> **Status: STANDBY** — All four review items (D1, D2, T1, T2) from the
> TA-PR5 review are **already committed on the TA3 branch** and included
> in PR #1250. No separate PR-B is needed for those items unless ev-shindin
> requests substantive rework. This plan serves as a decision tree and
> reference for the post-#1250-merge residue and any new items that emerge
> from ev-shindin's review.

---

## 0. Background

PR #1250 (branch `TA3`, assignee ev-shindin) carries 24 commits above
`main@badc48be`. The final coder session added the follow-up items from
the TA-PR5 review before the PR was opened:

| Item | Commit | Status |
|---|---|---|
| D1 — Rewrite `Analyze` doc-comment | `26394354` | **IN PR #1250** |
| D2 — Drop/rewrite stale comment on `computeLocalDemand` | `26394354` | **IN PR #1250** |
| T1 — Rename GPS-suppression test `Describe`/`It` blocks | `ea218f6d` | **IN PR #1250** |
| T2 — Add 5 aggregation-helper linearity specs | `ea218f6d` | **IN PR #1250** |
| ndots fix (e2e) | `3c838547` | **IN PR #1250** (should become own PR — see §4) |

Because these items are in-band with #1250, a separate PR-B is only needed
if (a) ev-shindin requests changes that cannot be squashed into #1250 during
review, or (b) additional items surface from ev-shindin's review that are
clearly out of scope for #1250.

Reference docs: [`TA-PR5-plan.md`](TA-PR5-plan.md) §6.1,
[`TA-PR5-review.md`](TA-PR5-review.md) §§ D1, D2, T1, T2.

---

## 1. What was done (verification record)

### D1 — Stale `Analyze` doc-comment (commit `26394354`)

**File:** `internal/engines/analyzers/throughput/analyzer.go`

**Old text (lines 180-188 in the reviewed version):**
```
// RequiredCapacity and SpareCapacity are computed from model-level totals, not
// per-variant deficits. This prevents conflicting signals when one variant is
// overloaded while another has spare capacity. PendingReplicas is included in
// anticipated supply to suppress scale-up thrashing while pods are starting.
// SpareCapacity is only emitted when EPP is deployed (ArrivalRate > 0).
//
// For P/D disaggregated models, RoleCapacities provides per-role breakdowns.
// No role is excluded from supply/demand computation. RequiredCapacity is
// suppressed for the prefill role: decode rate is never the prefill bottleneck.
```

**New text (as committed):**
```
// TA publishes TotalSupply, TotalAnticipatedSupply, and TotalDemand on the
// returned AnalyzerResult; RequiredCapacity and SpareCapacity are left zero.
// The engine's universal threshold post-step writes RC/SC after Analyze returns.
// PendingReplicas are included in TotalAnticipatedSupply to suppress redundant
// scale-up while pods are starting. Scheduler queue demand is split across
// non-prefill roles via distributeQueueDemandByRole.
//
// For P/D disaggregated models, RoleCapacities carries per-role Total* fields
// (TotalSupply, TotalAnticipatedSupply, TotalDemand); RC/SC per role are also
// left zero for the engine post-step. Prefill TotalDemand is negligible after
// the OL guard in computeLocalDemand.
```

The new text accurately describes the post-PR-5 contract: TA publishes raw
`Total*`; RC/SC are the engine post-step's responsibility.

### D2 — Stale comment on `computeLocalDemand` (commit `26394354`)

**File:** `internal/engines/analyzers/throughput/analyzer.go` (around
the `computeLocalDemand` function, previously described as line 527 in
the reviewed version).

**Old text:**
```
// This estimate is used for scale-up only; SpareCapacity still requires EPP.
```

**New text (as committed):**
```
// This path is scale-up only: k*-based demand may undercount arriving load
// without EPP. The engine post-step determines SC from the published totals.
```

The "SpareCapacity still requires EPP" claim was stale after the EPP/GPS
SC gate was dropped in PR-5. The replacement accurately describes the
current behavior: SC is determined by the engine post-step from the
published totals.

### T1 — GPS-suppression test block rename (commit `ea218f6d`)

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`

The `Describe` and all five `It` strings were renamed from the pre-PR-5
framing ("GPS verification suppresses SpareCapacity") to reflect the
current state (preserved fixtures for a future SC-gate PR). A block
comment was added at the top of the `Describe` explaining the deferral.

Renamed strings (current, as of commit `ea218f6d` + `24917288`):

| Location | New string |
|---|---|
| `Describe` | `"Analyze — GPS-mismatch scenarios (preserved fixtures for future SC gate)"` |
| L1361 `It` | `"GPS within 15% of model prediction — fixture for future SC pass-through"` |
| L1377 `It` | `"GPS deviates > 15% at k* ≥ DefaultGPSMinKForVerification — fixture for future SC suppression"` |
| L1390 `It` | `"GPS deviates but k* < DefaultGPSMinKForVerification — fixture for future SC pass-through"` |
| L1406 `It` | `"GenerationTokenRate is zero (metric absent) — fixture for future SC pass-through"` |
| L1421 `It` | `"RC remains nonzero under GPS mismatch — fixture for future SC suppression"` |

All scenario data, input coefficients, and `SpareCapacity == 0` assertions
were preserved verbatim. The block comment does not reference plans-branch
identifiers per CODER-CONVENTIONS §4a.

Follow-up commit `24917288` stripped a plans-branch reference (`F3`) from
the block comment that slipped through in the initial rename commit.

### T2 — Aggregation-helper linearity specs (commit `ea218f6d`)

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`

Five specs were added under the existing `Describe("Analyze — aggregation
helper consistency", …)` block (lines 960-1106 in the current file):

1. `TotalSupply == aggregation.SumTotalSupply(VariantCapacities)` — two
   variants with OLS-ready windows; verifies model-level sum is exactly
   the variant-slice sum.
2. `TotalAnticipatedSupply == aggregation.SumTotalAnticipatedSupply(VariantCapacities)`
   — one variant with one pending replica; verifies pending-replica
   anticipation carries through the sum.
3. `TotalDemand == aggregation.SumTotalDemand(VariantCapacities) + queue demand`
   — one variant with non-empty scheduler queue; verifies queue demand
   was added on top of the variant-slice sum.
4. `RoleCapacities[role].TotalAnticipatedSupply` matches per-role aggregation
   via `aggregation.AggregateByRole(result.VariantCapacities)` — P/D
   disaggregated fixture.
5. `RoleCapacities[decode].TotalDemand` includes the queue-demand share;
   `RoleCapacities[prefill].TotalDemand` is unchanged (queue skips prefill).

These lock the linearity invariant the engine post-step depends on. Before
these specs, a future refactor that double-counted a variant or skipped a
role would only surface downstream (wrong RC/SC from the engine), not in
TA's own test suite.

---

## 2. Nothing remaining for D1, D2, T1, T2

All four items are in PR #1250. When #1250 merges, these items land on
`main` as part of the TA3 commit set. No separate PR-B action is needed
for them.

---

## 3. Decision tree: when is PR-B needed?

### 3.1 ev-shindin requests changes to existing D1/D2/T1/T2 commits

If the review requests minor rewording or corrections to the doc-comment
or test renames, those can be addressed as fixup commits on TA3 before
merge — no separate PR-B.

If the review requests substantive behavioral changes to the GPS test
block or the aggregation specs, those are in scope for a targeted commit
on TA3.

A separate PR-B is only needed if #1250 merges before all review items are
addressed (e.g., if the review finds a new correctness bug requiring a
companion fix after merge).

### 3.2 New items from ev-shindin's review

Items that are doc-only, test-only, or doc+test with no behavior change
are candidates for PR-B. Behavioral fixes to `analyzer.go` should be
evaluated against scope: small isolated fixes can go in PR-B; larger
changes warranting their own commit history should become their own
named PR.

### 3.3 ndots standalone PR (see §4)

The ndots fix (`3c838547`) is in PR #1250 but was noted in CURRENT.md as
needing its own standalone PR. This is resolved by the fact that the fix
is already in #1250 — it either merges with #1250 or is extracted before
merge. See §4.

### 3.4 PR-1052 deferred fixes (separate scope)

The 10 items in [`PR1052-deferred-fixes.md`](PR1052-deferred-fixes.md) are
from the TA2 review (PR #1052, merged 2026-05-19). They are independent of
TA3 and do not belong in PR-B unless Dean decides to group them for
convenience. They have their own plan doc and should be tracked separately.

---

## 4. ndots fix: resolution

`test/e2e/fixtures/workload_builder.go` commit `3c838547` sets `ndots:2`
on load-generator pods to fix musl DNS on corporate networks. This fix is
a standalone e2e infrastructure fix, not part of the TA3 contract changes.
CURRENT.md notes it "needs its own PR before/with TA3 merge."

**Options:**

A. **Leave in #1250.** The fix is small, e2e-scoped, and unrelated to
   analyzer logic. ev-shindin can review it as part of #1250. This is the
   path of least friction.

B. **Extract as a standalone PR.** If ev-shindin objects to the scope
   conflation, or if there are CI concerns, extract `3c838547` as a
   separate PR with base `main`, get it merged first, then rebase #1250
   onto the updated `main`.

**Decision:** defer to Dean. If no objection, leave in #1250 (option A).
If asked to extract, the coder should:

1. Identify the diff: `git show 3c838547 -- test/e2e/fixtures/workload_builder.go`
2. Create a new branch from `main`
3. Cherry-pick `3c838547` onto the new branch
4. Open a standalone PR (base `main`, one commit, no other changes)
5. Once merged, rebase TA3 onto the updated `main` (single-commit rebase,
   expect no conflicts since only e2e/fixtures/ was touched)

---

## 5. If PR-B is needed: commit structure

If a separate PR-B is needed (see §3), the intended commit structure is:

**Commit 1 (doc+rename only, no behavior change):**
```
engines/analyzers/throughput: fix stale doc-comments and rename GPS-suppression test blocks
```
- `internal/engines/analyzers/throughput/analyzer.go`: D1 + D2 fixes
- `internal/engines/analyzers/throughput/analyzer_test.go`: T1 renames

This commit is a clean separation: all naming/prose changes, zero logic
changes, reviewers can confirm by inspection that nothing behavioral
changed.

**Commit 2 (test coverage only, no behavior change):**
```
engines/analyzers/throughput: add aggregation-helper linearity specs
```
- `internal/engines/analyzers/throughput/analyzer_test.go`: T2 specs

Separate commit so the diff is a clean additive set of test specs with
no interleaving with rename changes.

In practice these two commits are already on the TA3 branch; PR-B would
cherry-pick them (or equivalent patches) onto a branch off of the
post-#1250-merge `main`.

---

## 6. Pre-push checklist (if PR-B is opened)

Per CONVENTIONS.md pre-push checklist, in order:

1. `git branch --show-current` — confirm branch is the PR-B branch (not `TA3`, not `main`).
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — must produce no output.
3. `make test` — all tests pass.
4. `make lint` — clean. This runs golangci-lint with the repo's `.golangci.yml`; it is a required gate and catches findings that `gofmt`/`go build`/`make test` do not.
5. DCO sign-off — every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Verify with `git log upstream/main..HEAD --format="%b" | grep Signed-off-by`.
6. `go build ./...` — clean.

---

## 7. Key file paths

All paths are relative to the TA3 worktree
(`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/TA3/`):

| Path | Role |
|---|---|
| `internal/engines/analyzers/throughput/analyzer.go` | D1, D2 — doc-comments |
| `internal/engines/analyzers/throughput/analyzer_test.go` | T1, T2 — test renames and new specs |
| `internal/engines/aggregation/aggregation.go` | Aggregation helpers T2 specs call (`SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`) |
| `test/e2e/fixtures/workload_builder.go` | ndots fix — see §4 |

---

## 8. Out of scope

- **ndots standalone PR** (see §4 — decision pending, currently in #1250).
- **PR-1052 deferred fixes** — independent scope, own plan doc at [`PR1052-deferred-fixes.md`](PR1052-deferred-fixes.md).
- **`anyEPP` / `anyGPSMismatch` computed-and-discarded placeholders** (`_ = anyEPP; _ = anyGPSMismatch` in `analyzer.go`) — deliberate placeholders for the future per-analyzer status-return PR. Leave as-is; do not remove.
- **SC gate restoration** — deferred to a broader future PR that adds per-analyzer status-return state. Tracked in the multi-analyzer design doc under "Future direction." The GPS test fixtures in the renamed block are preserved precisely for this future PR.
- **`RegisterAnalyzer` error-return wiring** (H1 from the TA-PR5 review) — already landed in commit `a1343d6a` on TA3. In PR #1250.
