# optimizer-pd-role-ceiling — Review

**Status:** DRAFT
**Scope:** `a694012a`, `911e13b7`, `4fdd1123`, `2e3f023d`, `69c759a1`, `0c33a3eb` on branch
`optimizer-pd-role-ceiling`. Reviewed against
[`planning/optimizer-pd-role-ceiling-plan.md`](optimizer-pd-role-ceiling-plan.md). All three
planned commits (1–3) are landed, plus two additional test-only commits (`69c759a1`, `0c33a3eb`)
covering scenarios found during self- and planner-review, beyond the plan's original test list.
Working tree is clean.

**Verification, final HEAD (`2e3f023d`), independently re-run (not just taking the coder's
`review__optimizer-pd-role-ceiling-ready.md` trigger claims on faith):**
- `gofmt -l` — clean.
- `go build ./...` — clean.
- `go test ./internal/engines/pipeline/... -count=1` — **150/150 specs pass**.
- `golangci-lint run` scoped to `internal/engines/pipeline/...` (the touched package) —
  **0 issues**.
- DCO — all 4 commits (`a694012a`, `911e13b7`, `4fdd1123`, `2e3f023d`) carry
  `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` — confirmed via `git log --format=%b | grep`.

All five gates match the coder's trigger note exactly.

**Verification, final HEAD (`0c33a3eb`), independently re-run:**
- `gofmt -l` on the touched file — clean.
- `go build ./...` — clean.
- `go vet ./internal/engines/pipeline/...` — clean.
- `go test ./internal/engines/pipeline/... -count=1` — **154/154 specs pass** (150 + 2 from
  `69c759a1` + 2 from `0c33a3eb`, consistent with the running total).
- `golangci-lint run` scoped to `internal/engines/pipeline/...` — **0 issues**.
- DCO — `0c33a3eb` carries `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
- `git diff` confirms `0c33a3eb` touches only `cost_aware_optimizer_test.go` (84 insertions,
  0 deletions) — test-only, no production-code change, matching the coder's status-file note.

## Update — Finding 1 resolved

Commit `911e13b7` ("fix(optimizer): compute achieved-so-far from actual commits, not
pickerState") directly fixes Finding 1 from the first pass of this review (below, kept for the
record). It replaces the `pickerState`-delta read with a sum of `targets[v] - CurrentReplicas`
per variant in the role — exact regardless of any external fair-share cap, since `targets[]`
persists and accumulates across the whole optimizer pass rather than being re-derived and capped
per call. The commit message states the mechanism correctly and matches this review's analysis.
The new FairShare-pressure invariant test in the same commit exercises exactly the 2-model,
constrained-GPU-pool scenario this bug needed to surface in — confirmed failing before the fix
(this review observed it red) and passing after. This closes the test-coverage gap this review
flagged as well: that scenario is no longer untested.

One residual note: the plan doc's § Design formula section still states the original
`pickerState[satIdx][role]`-based wording (§ Design, "Resolved during implementation," point 1) —
worth a follow-up edit to the plan doc to describe the `targets[]`/`stateMap`-delta approach that
was actually shipped, so the plan doc stays accurate for anyone reading it after the fact. Not a
code defect — a doc-fidelity note for the planner.

---

## Findings

### 1. [CONFIRMED, high severity — RESOLVED in `911e13b7`] `originalRC_role` sourced from the wrong value — reintroduces the exact bug class design-resolution #1 exists to prevent

**Plan says** (§ Design — corrected algorithm, "Resolved during implementation," point 1):
`originalRC_role` must be a **local snapshot of `pickerState[satIdx][role]` taken at the top of
`allocateForModelPaired`** — explicitly *not* the analyzer's raw, uncapped `RequiredCapacity` —
because `GreedyByScoreOptimizer.allocateForModel` externally caps `pickerState` down to that
call's fair-share budget (`target`) *before* calling `allocateForModelPaired`
(`greedy_score_optimizer.go:250-257`). The plan's own words: "snapshotting inside `initRoleState`
would capture the pre-cap value and miscompute `achievedSoFar` whenever that cap bites."

**What commit 1 actually does** (`analyzer_helpers.go`, top of `allocateForModelPaired`):
```go
satIdx, roleCaps := saturationRoleView(s)
trueRC[role] = rc.RequiredCapacity   // rc := roleCaps[role]
```
`roleCaps[role].RequiredCapacity` is read straight from the saturation analyzer's
`RoleCapacities` map — bit-for-bit the same "pre-cap value" the plan explicitly names as wrong
(`initRoleState` populates `pickerState[i][role] = rc.RequiredCapacity` from that same source,
and `applyAllocation`'s own doc comment confirms `Result.RequiredCapacity` is never mutated
across the reconcile cycle — this value is fixed regardless of any fair-share cap).

Then: `achieved := (supplyByRole[role] + (trueRC[role] - pickerState[satIdx][role])) / denom`.

**Concrete failure mechanism:** In `GreedyByScoreOptimizer.allocateForModel` (only reachable
when >1 model is fair-share-active, the normal multi-model case), `ps[i][role]` is capped to
`target < trueRC[role]` *before* `allocateForModelPaired` is ever called. At the top of the very
first loop iteration, `pickerState[satIdx][role] == target` (nothing committed yet), so
`trueRC[role] - pickerState[satIdx][role] == trueRC[role] - target`, a large positive number
that has nothing to do with actual progress — it's purely the size of the external cap. This
inflates `achieved` toward 1.0 for every role whose fair-share budget this round is smaller than
its true demand, i.e. the *normal* multi-model case, not an edge case. `CostAwareOptimizer` does
**not** apply this external cap (`cost_aware_optimizer.go:60-62` passes `initRoleState`'s
pickerState straight through), so it's unaffected.

**Why this passed:** every new test in this commit (and the pre-existing recalibrated
`greedy_score_optimizer_test.go:997` test) exercises either `CostAwareOptimizer` or a
single-active-model `GreedyByScoreOptimizer` scenario. In `fairShareScaleUp`, a single active
model gets `allocationMean = 0` (`greedy_score_optimizer.go:207-208`), so `target = w.remaining`
— the cap never actually binds (`target ≈ trueRC`), and the bug is invisible. No test exercises
≥2 competing models going through the P/D paired path, so this gap is untested, not just unfixed.

**Note for the planner:** as of the last observed state before this review paused, the coder's
next (uncommitted) working-tree edit had already replaced this with a
`targets[]`/`stateMap.CurrentReplicas`-delta ("committed") calculation instead of the
`pickerState`-delta approach — which sidesteps the external-cap contamination entirely (it reads
actual committed replicas, not a value that can be pre-capped by the caller). That looks like a
credible fix on inspection, but it is a further deviation from the plan's literal written formula
and was not captured in the plan doc's "Resolved during implementation" section. Recommend: once
that (or an equivalent) fix lands in a commit, update the plan doc's formula section to match
what was actually implemented, and add a regression test that exercises the ≥2-active-model
`GreedyByScoreOptimizer` path with a binding fair-share cap — the one scenario this whole class
of bug requires to surface, and the one scenario no current test (old or new) covers.

**Failure scenario:** 2 active P/D models under `GreedyByScoreOptimizer` fair share, GPU pool
constrained enough that each model's per-iteration `target` budget is well below its full
`RequiredCapacity`. Every fair-share iteration for both models computes an artificially inflated
`achievedSoFar`, which corrupts `jointCap` and can cause a role to be judged "already near its
ceiling" and denied replicas it should get — silently, every reconcile cycle, for any workload
with more than one disaggregated model competing for the same GPU pool.

---

### 2. [Minor, NTH] `if !anyBinding { break }` is an early-exit the plan didn't ask for

Plan § Design point 3 states both old early exits are removed and "the existing `anyPositive`
check is sufficient... No new stopping logic needed." Commit 1 adds one anyway
(`analyzer_helpers.go`, inside the per-role loop, guarding on `denom <= 0` for every role).

On inspection this is functionally harmless: if `anyBinding` is false, every role's `denom <= 0`,
so the k-computation loop's `denom > 0` guard would produce `k = 0` for every role regardless,
and the existing `if !anyPositive { break }` at the bottom would fire anyway with the identical
net effect (function returns, no commit). It just skips some redundant zero-work computation.
Not a correctness issue — flagging only because it's a literal deviation from "no new stopping
logic needed." Low priority; fine to leave as a minor optimization or remove for plan fidelity,
coder's call.

---

### 3. [Confirmed correct] Core formula matches the plan

- `candidateCeiling_role = achievedSoFar_role + n_role×PRC_role/denom_role` — matches exactly.
- `jointCap = min_role(candidateCeiling_role)` over roles with `denom_role > 0` only — matches;
  roles with `denom <= 0` are correctly excluded from the min and forced to `k=0`.
- Rounding: `k = 0` if `denom<=0 || n==0 || raw<=0`, else `clamp(max(floor(raw),1), 0, n)` where
  `raw = (jointCap - achievedSoFar_role) × denom_role / PRC_role` — matches the plan's formula
  and the asymmetric-demand worked example verbatim.
- `achievedSoFar` clamp to `max(computed, 1.0)` when `trueRC[role] <= 0` — matches the planner's
  amendment (resolution point 3), modulo Finding 1's concern about which snapshot feeds it.

### 4. [Confirmed correct] Recalibrated test matches the plan's specified repro shape exactly

`greedy_score_optimizer_test.go:997`'s new fixture (`prefill-v`: PRC=100, 2 replicas,
supply=200, demand=300; `decode-v`: PRC=100, 1 replica, supply=100, demand=300) is a verbatim
match for the plan's Test Plan § "Must change" item, including the expected outcome (decode
advances +1 toward the 0.667 ceiling, prefill unchanged) and the required comment rewrite (no
longer states the old hard-abort behavior as intentional).

### 5. [Confirmed correct] `roleAggRemaining` deletion, classified correctly

Removed as dead code, superseded by the achieved-fraction formula — matches plan's Deletion
classification section, and the commit message states the "why removed now" rationale per
CONVENTIONS' deletion-documentation rule. No other caller references it (build is clean).

### 6. [Confirmed correct] Anchor-variant guard fix is a necessary, correct consequence of removing the hard abort

`for _, anchor := range []string{"prefill", RoleBoth} { if v, ok := variantByRole[anchor]; ok &&
v != "" { applyAllocation(...) } }` — the added `&& v != ""` correctly prevents passing an empty
variant name to `applyAllocation` now that a failed `pick()` no longer aborts the loop
(`variantByRole[role]` can legitimately be `""` for a capped role while a sibling role still
commits). Correct and necessary.

### 7. [Confirmed correct] Test-plan coverage now complete (items 1–6)

All six § Test plan scenarios are now present across commits 1–2:

| # | Scenario | Commit | Test |
|---|---|---|---|
| 1 | Capped-with-unmet-demand | `a694012a` | recalibrated `greedy_score_optimizer_test.go:997` + `cost_aware_optimizer_test.go` maxReplicas variant |
| 2 | Satisfied-but-capped | `a694012a` | `cost_aware_optimizer_test.go` "already satisfied" test |
| 3 | Cold-start regression guard | `a694012a` | `cost_aware_optimizer_test.go` cold-start test |
| 4 | Multi-variant-per-role | `4fdd1123` | "next-cheapest variant" test |
| 5 | Synthetic 3-role sanity check | `4fdd1123` | "three synthetic roles" test |
| 6 | FairShare-pressure invariant | `911e13b7` | "non-binding maxReplicas" test |

No gaps against the plan's test list.

### 8. [Confirmed correct] FairShare-pressure invariant test compares the right fields

The test compares only `TargetReplicas`/`Action` per variant between the baseline and
non-binding-maxReplicas scenarios, not the full decision struct — correctly avoids a
false-negative from `MaxReplicas` legitimately differing between the two scenarios (it's expected
to echo straight through into the decision) while still locking in the actual invariant under
test (fair-share ranking must not be affected by a non-binding cap).

### 9. [Confirmed correct] Commit 3 — dev-guide update matches the plan's instruction and reflects the *actual shipped* formula

`2e3f023d` replaces the stale `Δ_util = min_role util_role` / `roleAggRemaining` description in
`docs/developer-guide/multi-analyzer-pipeline.md` with the `achievedSoFar`/`candidateCeiling`/
`jointCap` formula, per the plan's Dev-guide impact section. Checked field-by-field against the
code as it exists at `2e3f023d` (not against the plan's original wording):

- `denom_role = RequiredCapacity_role + TotalAnticipatedSupply_role` — matches `denomByRole`.
- `committed_role = Σ (targets[v] − CurrentReplicas_v) × PerReplicaCapacity_v` — matches the
  `911e13b7` formula exactly, **not** the plan doc's original `pickerState`-snapshot wording.
  This is the right call — Type 4 docs must reflect actual code, not the plan — and it
  incidentally means the dev-guide is *more* current than the plan doc right now (see the
  residual note under Finding 1: the plan doc itself still needs the planner's follow-up edit).
- `achievedSoFar` clamp and `candidateCeiling`/`jointCap` — match code exactly.
- Explicitly states a capped role contributes its achieved (not zero) util to the min — the
  sentence the plan asked for.

Grepped the full doc file for residual stale terms (`Δ_util`, `deltaUtil`, `utilByRole`,
`roleAggRemaining`, `allPicked`) per the CONVENTIONS semantic-pivot cross-reference rule — no
hits outside the newly-added correct text. No stale references left elsewhere in the file.

**Trivial wording nit (optional, not blocking):** the ASCII diagram at the top of the doc now
reads "joint jointCap commit" (added in this commit) — slightly awkward repetition of "joint."
Consider "joint jointCap-bounded commit" or similar if touching this file again; not worth a
commit on its own.

### 10. [Confirmed correct] `69c759a1` — multi-analyzer `RoleCapacities` disagreement, test-only, no code change

Not part of the plan's original test list — the coder identified this gap independently while
reviewing the joint-allocation fix (per the commit message). Two tests, both re-derived by hand
and confirmed correct:

1. **achievedSoFar/denom must read only the saturation entry.** Two analyzers (`saturation`,
   `throughput`) both populate `RoleCapacities["prefill"]` with disagreeing `RequiredCapacity`
   (200 vs 500). Prefill is capped at `MaxReplicas=1`, decoupling its own ceiling from `n_role`
   sizing so the *denom* choice alone drives the outcome. Hand-traced through
   `allocateForModelPaired`: `saturationRoleView` returns on the first
   `e.Name == SaturationAnalyzerName` match and never merges in other analyzers, so
   `denom["prefill"] = 200` (not 500) → `ceiling_prefill = 0 + 1×100/200 = 0.5` →
   `jointCap = 0.5` → `k_decode = floor(0.5×3000/100) = 15`. Matches the test's expectation
   exactly (and the test's own comment that mixing in throughput's 500 would wrongly give 6).
   Confirms `saturationEntry`'s existing single-canonical-source convention
   (`cost_aware_optimizer.go:303-311`, cited in the plan) extends correctly to the new
   achieved-fraction formula.
2. **`roleBottleneckReplicas` must still aggregate `n_role` sizing across *all* analyzers.**
   Companion single-role test: saturation RC=200, throughput RC=500, no cap. Hand-traced:
   `roleBottleneckReplicas` takes `max(ceil(200/100), ceil(500/100)) = 5` regardless of the
   narrower saturation-only denom used above — target lands on 5, not saturation's 2. Confirms
   the two computations (sizing vs. achieved-fraction) were correctly decoupled to different
   data sources, not accidentally narrowed together.

Both tests pass; independently re-verified gofmt/build/lint/test/DCO on this HEAD (`69c759a1`) —
all clean, 5/5 commits signed off.

### 11. [Confirmed correct] `0c33a3eb` — fractional round-up and mid-call cap transition, test-only, no code change

Closes § Test plan items 9/10, found during a planner corner-case audit (per
`plan__optimizer-pd-role-ceiling-multi-analyzer-tests.md.WIP` and the coder's status file): every
prior test's `raw = (jointCap - achievedSoFar) * denom / prc` happened to land on an exact
integer, and every prior "capped" test started already at its cap from iteration 1 — neither
range was exercised. Two tests added, both hand-traced against the current
`allocateForModelPaired` independently of the coder's own stated verification:

1. **Fractional round-up-to-1** (`"should round a fractional replica gap up to 1, not floor it to
   0"`). Prefill capped at `MaxReplicas=1`, cold start: iteration 1 gives `n_prefill=1`,
   `ceiling_prefill = 0 + 1×100/100 = 1.0` → `jointCap = 1.0`. Decode (uncapped,
   `CurrentReplicas=1`, `supply=100`, `denom=150`): `achieved_decode = 100/150 = 0.667`, `raw =
   (1.0-0.667)×150/100 = 0.5`. `k = min(max(floor(0.5)=0, 1), n=2) = 1` — the `max(...,1)` clamp
   is what turns this into `+1`; a plain `floor` would silently give `0`. Iteration 2:
   `achieved_decode` recomputes to `(100+100)/150 = 1.333`, `raw` goes negative, loop halts.
   Final: `prefill=1`, `decode=2` — matches the test's expectation exactly.
2. **Mid-call headroom→capped transition** (`"should freeze a role's contribution correctly
   after it becomes capped mid-call..."`). Prefill starts with real headroom
   (`MaxReplicas=2`, `CurrentReplicas=0`) and *defines* `jointCap` in iteration 1
   (`ceiling_prefill = 0 + 2×100/500 = 0.4` vs. decode's `1.0`) — the same commit that sets
   `jointCap` also exhausts prefill's `MaxReplicas` (`k_prefill=2`), transitioning it from
   headroom to capped as a side effect of its own commit. Iteration 2: `pick("prefill")` now
   returns `("", 0)` (headroom `2-2=0`), so `prcByRole["prefill"]=0` and `k_prefill` is forced to
   `0` via the `prc>0` guard regardless of `n`/`capN` — the role's contribution freezes at its
   iteration-1 `achieved=0.4`, matching the frozen `jointCap`, rather than either re-granting
   headroom (stale `capN`) or losing its committed share (stale `achieved`). Decode's
   iteration-2 `achieved` (0.5) already exceeds the frozen `jointCap` (0.4), so `raw` goes
   negative and it correctly stops instead of over-committing to its own higher ceiling. Final:
   `prefill=2`, `decode=1` — matches the test's expectation exactly.

Both hand-traces independently confirm the coder's own stated verification (drop `max(...,1)` →
test 1 floors to 0 and fails; hoist `pick()` out of the loop → test 2 sees stale `capN`/variant
across iterations and fails). No production code touched — `git diff` on `0c33a3eb` shows only
`cost_aware_optimizer_test.go`, 84 insertions, 0 deletions.

---

## Summary for the coder

All three planned commits are landed and match the plan, plus two additional test-only commits
(`69c759a1`, `0c33a3eb`) covering a multi-analyzer `RoleCapacities` disagreement scenario and the
two corner cases (fractional round-up, mid-call cap transition) found during self- and
planner-review — both correct and well-targeted, independently hand-traced and confirmed. Finding
1 (high-severity, from the first review pass) is resolved in `911e13b7`. Test-plan coverage is
now complete: all 6 original scenarios plus items 9/10 found post-hoc. Dev-guide update is
accurate and matches the actual shipped formula, not the plan doc's original wording — correct
per Type 4 rules. Independently re-verified on final `HEAD` (`0c33a3eb`): gofmt/build/vet/lint
clean, all 154 tests pass, DCO 6/6.

**Open items, none blocking:**
- §2 — redundant early-exit (`!anyBinding`), low-priority NTH, coder's call whether to clean up.
- §9 — trivial ASCII-diagram wording nit, optional.
- **For the planner, not the coder:** the plan doc's § Design formula (`originalRC_role`/
  `pickerState[satIdx][role]`) is now stale relative to what shipped (`targets[]`/`stateMap`-delta
  `committed_role`, per `911e13b7` and now the dev-guide), and its § Test plan / § Implementation
  phases still show items 9/10 and Commit 7 as pending though both are now landed in `0c33a3eb`.
  Recommend a follow-up edit to `planning/optimizer-pd-role-ceiling-plan.md` covering both.

No correctness blockers found in any of the 6 commits reviewed to date.
