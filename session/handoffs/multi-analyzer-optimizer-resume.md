to: multi-analyzer-optimizer agent
from: plan-agent
session: multi-analyzer-optimizer resume — 1.3 onward + cross-rebase context

## Trigger

Resume Item 1 work per `planning/multi-analyzer-optimizer-plan.md`.

That doc is the canonical source for: per-analyzer-slice contract, linearity invariant,
helper API, picker design, the 1.3 / 1.4 / 1.5 commit plan, the cross-rebase mechanics
onto `multi-analyzer-threshold@b8b823b0` (PR #1228), the `runAnalyzersAndScore` signature
reshape during rebase, and verification gates.

## What's changed since you paused

You paused after `956e60b6` (1.2) on top of `a93bc5dc`. While you were paused:

- **Registration** moved to a new branch `multi-analyzer-registration` (PR #1225), now
  on `main@eb327cc2`. New SHAs `3a0dff86` / `6b4f2b8f` / `66001d47`. Combine code,
  `enabledAnalyzerResult`, `engine_combine_test.go` all deleted there.
- **Threshold** moved to `multi-analyzer-threshold@b8b823b0` (PR #1228) — architectural
  rework: engine post-step is sole writer of RC/SC; new `internal/engines/aggregation/`
  helpers package; sat_v2 simplified (drops in-analyzer RC/SC); strict no-fallback
  formula at every scope; per-analyzer threshold overrides honored.

Your branch tip `956e60b6` is still on the **old** `a93bc5dc` base (combine present,
map-based registration). The cross-rebase target shifts to `b8b823b0` (was planned for
`51d7e7fa`, that branch was force-pushed away).

## Immediate next step

Commit 1.3 — migrate `CostAwareOptimizer` to per-analyzer slice. Detailed plan in
the Type 3 plan doc (§ "Roadmap commits → 1.3"). Key points:

- Gate via `needsScaleUp` / `needsScaleDown` over `req.AnalyzerResults`.
- Cost-greedy `PickVariantFn` (cheapest cost-efficiency; `capN = math.MaxInt`).
- Scale-down: `safeRemovalReplicas` + `applyDeallocation` loop; cheapest-variant
  protection retained.
- Variant metadata via `saturationEntry(req.AnalyzerResults).VariantCapacities`.
- Greedy unchanged in 1.3.
- `buildDecisionsWithOptimizer` reason-strings still touch `req.Result` — leave for 1.5.

Continue with 1.4 (Greedy) and 1.5 (cleanup; simplified — combine deletion already
done upstream). Then perform the cross-rebase per § "Cross-rebase mechanics".

## Operational reminders

- Worktree scope: work only inside `multi-analyzer-optimizer/`. Read absolute paths
  cross-worktree as needed (CONVENTIONS allows); never `cd` or `git -C` into a sibling
  worktree.
- Each commit: compile, `make test`, gofmt clean, DCO-signed.
- Don't push without explicit Dean confirmation.
- Update your living handoff at `session/handoffs/multi-analyzer-optimizer-status.md`
  (note the filename — "status" not "resume" or "slice-redesign") with each checkpoint.
