last_update: 2026-08-03T04:30:00Z
state: in-progress
current_step: DRAFT review's Finding 1 fixed (ca[0] -> name-keyed guards); Finding 2 relayed to planner as a coordination note; awaiting review to go FINAL

## Branch
ta-anchor-goldens at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-anchor-goldens ; tip a2f49ccf (cut from main@9906dac5)

## Recent commits
- a2f49ccf — test: key A1/A2/B1 non-vacuity guards by variant name, not slice index (review Finding 1 fix)
- cca44cf5 — test: add quota-constrained characterization golden C1
- 8520d57d — test: add disaggregated (P/D) characterization goldens B1-B2
- 7e4680fa — test: add aggregated (RoleBoth) characterization goldens A1-A4
- 7d5da941 — test: add characterization-golden harness for anchor refactor

## Tests added / moved
All in new file `internal/engines/pipeline/optimizer_characterization_test.go` (package `pipeline`, Ginkgo):
- harness smoke test — trivial no-op decision, proves expectDecisionSet/unlimitedConstraints plumbing
- A1 — single-variant scale-up (both optimizers)
- A2 — single-variant scale-down, cheapest/only-variant protected at 1 (both optimizers)
- A3 — no-op / at-target, multi-variant (both optimizers)
- A4 — multi-variant cost tie-break (both optimizers)
- B1 — disaggregated paired scale-up (both optimizers; CostAware's joint paired-commit vs GreedyByScore's proportional split happened to land on the same numbers for this fixture — see Notes)
- B2 — disaggregated role-scoped scale-down, expensive-prefill fully removed / cheap-prefill protected (both optimizers)
- C1 — namespace-quota-constrained scale-up (GreedyByScore only — CostAware ignores ResourceConstraints entirely, ship-documented in its doc comment)

Commit 5 (optional rescale characterization) — **not taken**, see Not done section below.

## Verified
- make test — PASS (full suite, no regressions)
- gofmt -l ./internal ./cmd — clean
- make lint — 0 issues
- go build ./... — clean
- go test ./internal/engines/pipeline/... -race — PASS
- Ran the new suite 10x with -count=1 (map-iteration / unstable-sort nondeterminism check) — stable every time, re-verified after the Finding-1 fix
- DCO: all 5 commits carry Signed-off-by: Dean H Lorenz <dean@il.ibm.com> (verified via git log main..HEAD)
- grep confirms zero remaining `ca[0]`/`gs[0]`-style indexed guards in the file

## Developer guide
- None — plan's non-goals explicitly exclude dev-guide changes (test-only, no user-visible behavior).

## Open questions for Dean
- None blocking. Land-first-vs-cherry-pick coordination with the anchor-refactor branch is a planner-level decision per the plan's § Coordination — not mine to resolve.
- Review Finding 2 (coordination note, not a defect on this branch): `withSatEntry` — the fixture
  helper every golden in this file calls — lives in the pre-existing `cost_aware_optimizer_test.go`,
  untouched by this branch. If the anchor-refactor branch's repoint work changes that helper's
  signature/behavior, this goldens file would fail to *compile* there rather than go red, silently
  breaking the "rides unchanged as the ship gate" property. Relayed to the planner via handoff for
  whoever starts the anchor-refactor branch — not something to fix on ta-anchor-goldens itself.

## Not done / known limitations
- **Commit 5 (rescale characterization) — DEFERRED**, per plan's explicit "only if time permits" framing. The anchor branch relies on existing `rescale_test.go` / `rescale_optimize_test.go` for rescale coverage in the meantime (plan's own fallback framing). No code was touched for this — pure omission, nothing to classify as removed.
- B1's GreedyByScore golden was captured empirically (ran the fixture, read the actual result) rather than derived by hand from an existing mined test, since no existing GreedyByScore P/D fixture used this exact equal-demand shape. Confirmed stable across repeated runs; flagged here per the plan's "if capture surprises you" guidance even though nothing here was actually surprising — the values matched CostAware's numbers for this particular 50/50-demand fixture, an incidental convergence of the two different algorithms at this input, not an asserted general equivalence.

## Notes
Not pushed. Per CODER-CONVENTIONS §5.4, review trigger written (`review__ta-anchor-goldens-ready.md`) before any push-ready handoff to the planner.
