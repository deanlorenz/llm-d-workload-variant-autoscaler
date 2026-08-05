# ta-anchor-goldens — Internal Review

**Type:** 6 (review) · **Status:** FINAL · **Branch:** `ta-anchor-goldens`, tip `a2f49ccf` (5
commits, cut from `main@9906dac5`) · **Reviewed against:**
[`planning/ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md) · **Reviewer:** internal (this
session) · **Date:** 2026-08-03 (finalized after Finding 1 fix, same day)

## Verdict

Implementation matches the plan closely and honestly. Purely additive — one new file, zero
production-code changes, confirmed via per-commit diff stats. All gates independently re-verified
green, including a 5x repeat run targeting the map-iteration / unstable-sort flakiness the plan
specifically warns about. No correctness defects found. Branch base is current (`main` has not
moved since the branch was cut — no rebase needed). **Finding 1 fixed and independently
re-verified (see § Resolution below); Finding 2 correctly left as a relayed coordination note for
the anchor-refactor branch, not fixed here.** Push-ready pending Dean's per-push confirmation and
the land-first-vs-cherry-pick coordination call.

## Resolution (2026-08-03, same day)

Coder commit `a2f49ccf` — "test: key A1/A2/B1 non-vacuity guards by variant name, not slice
index" — fixes Finding 1: `ca[0].TargetReplicas` in A1/A2/B1 replaced with name-keyed
`caTargets[name]` lookups, matching B2's existing pattern. B1's fix goes slightly further than the
finding asked: it now asserts `prefill-v` and `decode-v` individually (`>1` each) rather than one
combined index-0 check, which more precisely matches the plan's original requirement that "both
roles were considered."

Independently re-verified on tip `a2f49ccf` (not just trusting the coder's handoff):
- `git diff --stat cca44cf5 a2f49ccf` — touches only the test file (+16/−3), no scope creep
- `grep -nE '\b(ca|gs)\[[0-9]+\]' optimizer_characterization_test.go` — zero hits; the fix is
  complete, not just applied to the three cited call sites
- `gofmt -l`, `go build ./...` — clean
- `go test ./internal/engines/pipeline/... -race -count=1` — PASS
- Repeated the full package suite 5x with `-count=1` — stable every time
- `make lint` — 0 issues
- DCO — 5/5 commits `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`

Finding 2 was correctly **not** fixed on this branch — `withSatEntry` genuinely lives outside this
branch's diff, so there's nothing to change here. The coder relayed it via
`session/handoffs/plan__ta-anchor-goldens-review-finding1-fixed.md`, asking the planner to fold the
`withSatEntry`-stability check into whichever kickoff/plan doc launches the anchor-refactor branch.
Confirmed that framing is correct and sufficient — no further action needed on `ta-anchor-goldens`
itself for Finding 2.

## Change highlight

| Commit | What | Type |
|---|---|---|
| `7d5da941` | harness: `goldenDecision` type + order-insensitive `expectDecisionSet` (keyed by `VariantName`) + `unlimitedConstraints` helper + one smoke case | scaffolding |
| `7e4680fa` | A1-A4: aggregated (RoleBoth) scale-up / scale-down (cheapest-at-1 protection) / no-op / multi-variant cost tie-break, both optimizers | test |
| `8520d57d` | B1-B2: disaggregated (P/D) paired scale-up / role-scoped scale-down, both optimizers | test |
| `cca44cf5` | C1: namespace-quota-constrained scale-up, GreedyByScore-only (CostAware ignores `ResourceConstraints`) | test |

All 4 commits touch only the new file `internal/engines/pipeline/optimizer_characterization_test.go`
(verified via `git diff --stat <parent> <commit>` per commit) — no production code changes,
matching the plan's non-goal and each commit message's own claim.

## Independent verification (re-run this session, not just trusting the handoff)

- `gofmt -l` on the new file — clean
- `go build ./...` — clean
- `go test ./internal/engines/pipeline/... -race -count=1` — PASS
- Re-ran the full package suite 5x with `-count=1` (independent of the coder's own 10x run) —
  stable every time, no order-dependence flakiness
- `make lint` — 0 issues
- DCO — 4/4 commits `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`
- Branch staleness — `main` tip is still `9906dac5`, exactly the branch's cut point
  (`merge-base main ta-anchor-goldens` == `9906dac5`); no rebase needed before push
- §4a scan (`F[0-9]+|A[0-9]+|B[0-9]+|C[0-9]+|D[0-9]+|T[0-9]+|I-[0-9]+|planning/`) — only hits are
  the plan's own self-contained scenario labels (A1-A4/B1-B2/C1), each spelled out in the same
  `It(...)` string (e.g. `"A1: single-variant scale-up — demand exceeds capacity"`); no opaque
  cross-reference to another doc, so no §4a violation
- Hand-verified the arithmetic in every golden's "captured from `main@...`" comment against its
  asserted `goldenDecision` values (A1 `ceil(15000/10000)=2`→4; A2 `floor(30000/10000)=3` vs.
  protect-at-1→1; A4 cost-efficiency cheap<expensive→cheap absorbs; B1 alpha=1, n=2→3 both roles;
  B2 cost-desc shedding, expensive-p→0, decode `floor(10000/10000)`→2; C1 free-GPU room for exactly
  1 replica→2) — all self-consistent with the golden values, and (since the suite is green) with
  actual `main` behavior
- Confirmed every `Optimize` call pair is fed a **freshly-built** request set (`build()` invoked
  once per call, never shared) — correctly avoids the in-place `AnalyzerResult.Remaining` mutation
  trap documented in `optimizer_equivalence_test.go`'s header comment; checked all 7 scenarios
  (smoke, A1-A4, B1, B2, C1)

## Findings

### 1. (NTH, non-blocking) — **FIXED** in `a2f49ccf`. Three non-vacuity guards index `ca[0]` instead of keying by variant name

A1 (`:143`), A2 (`:174`), and B1 (`:282`) write their non-vacuity guard as
`Expect(ca[0].TargetReplicas)...` rather than looking the variant up by name. This is safe *today*
— A1/A2 have exactly one variant (index 0 is unambiguous), and B1's two variants move symmetrically
(1→3 each), so whichever one map iteration puts at index 0 still satisfies `>1`. But it's
inconsistent with B2's (`:339-340`) safer `caTargets[name]` pattern, and with the plan's own "never
assert slice order" guidance in spirit — if a future edit to these fixtures made B1's two roles
behave asymmetrically, `ca[0]` would silently pick whichever role landed first under Go's
randomized map iteration, and the guard could pass or fail non-deterministically depending on the
run. Recommend switching all three to the name-keyed style B2 already uses. Not blocking — the
immediately-following `expectDecisionSet` call already fully pins both roles' values in every one
of these cases, so there is no live bug, only a latent robustness gap in the standalone guard line.

### 2. (Coordination note, not a defect) — **RELAYED, not fixed here** (correctly out of scope for this branch). The goldens file has a soft dependency on `withSatEntry`, which lives outside this branch's diff

Every fixture builder calls `withSatEntry` (defined in the pre-existing `cost_aware_optimizer_test.go`,
untouched by this branch) rather than a self-contained helper. That's a reasonable, DRY reuse of an
existing package-internal helper, consistent with the plan's Commit 1 guidance to mirror
`cost_aware_optimizer_test.go`'s builders. But the plan's § Coordination section promises this file
"rides unchanged onto the anchor-refactor branch." If the anchor-refactor branch's repoint work
changes `withSatEntry`'s signature or behavior — plausible, since it lives in a file adjacent to the
saturation-entry/anchor plumbing the refactor targets — the golden file would fail to *compile* on
that branch: a silent break in the "unchanged ship gate" property that wouldn't show up as a red
golden, just a build failure. Worth a one-line flag in the handoff to whoever starts the
anchor-refactor branch: confirm `withSatEntry` is untouched (or copy it into the goldens file) before
relying on this file as a gate.

## Confirmed-correct (no action needed)

- Fixture matrix matches the plan exactly: A1-A4 and B1-B2 run through both `CostAwareOptimizer` and
  `GreedyByScoreOptimizer`; C1 is GreedyByScore-only with an explicit comment citing CostAware's
  documented unlimited-mode/`ResourceConstraints`-ignoring behavior as the reason.
- All four non-vacuity guard *intents* from the plan are actually enforced (A1 strictly-greater, A2
  strictly-less, A3 exact no-op, A4 full-name-set via `ConsistOf`, B1/B2 per-role movement, C1
  constrained-strictly-below-unconstrained) — verified that the guard lines plus the full
  `expectDecisionSet` check together satisfy each one, even where (Finding 1) the standalone guard
  line alone would not.
- B1's CostAware/GreedyByScore golden values are identical (`{prefill-v:3, decode-v:3}` both ways)
  — the code comment (`:285-287`) and the coder's status file both correctly flag this as an
  incidental convergence of two different algorithms on this particular 50/50-demand fixture, not
  an asserted general equivalence. Consistent with `optimizer_equivalence_test.go`'s own explicit
  scope disclaimer (equivalence is asserted only for the unconstrained scale-up path, not P/D).
- Commit 5 (rescale characterization) correctly and explicitly deferred per the plan's own "only if
  time permits" framing; zero code touched, so there is nothing to classify as a deletion — matches
  the plan's § Commit 5 fallback instruction.
- The coder's comments describe each golden's arithmetic in self-contained prose ("captured from
  `main@9906dac5`: `ceil(...)`...") rather than citing the design doc's plans-branch-only "masked
  bugs #1/#2/#3/#5" numbering that the plan's own example comment template used — better §4a
  hygiene than the plan's suggested template. Also confirmed moot substantively: per
  `combined-analyzer-optimizer-design.md` § Latent bugs (L291), bugs #1/#2/#3/#5 are explicitly
  masked *specifically because* saturation is the only active analyzer — exactly the single-vote
  condition every fixture in this file is built under — so none of them can actually manifest in
  any golden here.

## Judgment calls (from the coder's status file) — reviewed, no objection

- Commit 5 deferral — matches the plan's own optional framing, reasonable given the 0.9 freeze date.
- B1's GreedyByScore golden captured empirically rather than derived by hand — reasonable given no
  existing P/D fixture used this exact equal-demand shape; re-verified independently via the -race
  and 5x-repeat runs above, stable.

## Land-first-vs-cherry-pick coordination

Out of scope for this review — explicitly a planner+Dean decision per the plan's § Coordination —
not evaluated here.
