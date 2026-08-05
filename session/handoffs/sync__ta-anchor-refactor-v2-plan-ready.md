from: planner (ta-anchor-refactor-v2 plan authoring)
to: sync
session: ta-anchor-refactor-v2 plan ready + mission-row update

## What changed (all committed on plans branch)

- **New Type-3 plan** `planning/ta-anchor-refactor-v2-plan.md` (commit `b95b2e35`), toc-refreshed.
  Self-contained; implements the corrected no-stored-field two-phase anchor mechanism from
  `ta-anchor-refactor-review.md` Part 2. 5 commits (§5 Phase-1 generation + `Enabled` tag; §6
  Phase-2 `bindingAnchor` per-variant merge + `votingResults` prune + repoint all read sites; §7
  QM-as-error + liveness/do-nothing; §7b TA-side proactive complement; §8 dev-guide).
- **`ta-anchor-refactor-plan.md` marked `Status: SUPERSEDED`** (commit `9721b587`, header-only) —
  points to the v2 doc; it and the abandoned commit `34055d77` implemented the stored-`.Anchor`
  field design that the redesign replaces. Kept for history (Part-1 review subject).
- **`combined-analyzer-optimizer-design.md` § anchor Implementation-note corrected** + **PR-2 stub
  `ta-anchor-dynamic-refresh-plan.md` §3 forward-note added** (commit `99dc04c9`): anchor is derived
  on demand (per-variant merge keyed by VariantName), not a stored field; PR-2 "refresh per
  iteration" = re-run the Phase-2 getter.
- **Review-ready trigger dropped** at `session/handoffs/review__ta09-enablement-plan-ready.md` (the
  review agent's persistent monitor watches that exact path). Automatic review armed (Dean asleep).
- **Consumed handoffs marked `.DONE`:** `plan__ta-anchor-refactor-mechanism-redesign.md.WIP` →
  `.DONE` (folded into the v2 plan) and `plan__ta09-critical-enablement-plan-kickoff.md` → `.DONE`
  (kickoff fulfilled).

## Update CURRENT.md — anchor-refactor mission

The anchor-refactor mission has **pivoted to a no-stored-field redesign on a fresh branch.** Update
the Recent-activity abstract + the `ta-anchor-refactor` PR-Status row (and add a v2 row):

- **Mechanism redesign.** The stored-`ModelScalingRequest.Anchor` field design (commit `34055d77`
  + the Aug-4 fold-in `68bda1a1`/`192ae06b`) is **superseded** by a no-stored-field two-phase
  mechanism: Phase-1 `runAnalyzersAndScore` calls every analyzer, tags each ballot entry with a new
  `Enabled bool` (+ existing `Live bool`), makes no decisions; Phase-2 `bindingAnchor` (successor to
  `saturationEntry`) derives the anchor **on demand** by a per-variant merge keyed by `VariantName`
  ((a) identity from saturation, (b) sizing from the binding analyzer, per-variant fallback to sat's
  (b) before the combine-ballot prune). A new `votingResults` helper prunes the combine ballot to
  `Enabled` entries (differs from the raw ballot only in the `[TA]`-only config).
- **Plan doc.** `ta-anchor-refactor-plan.md` is now **SUPERSEDED**; the live PR-1 plan is
  **`ta-anchor-refactor-v2-plan.md`** (DRAFT, committed `b95b2e35`, awaiting the review agent's
  automatic review).
- **Branch decision.** Fresh branch **`ta-anchor-refactor-v2`** to be cut off the goldens tip
  `ta-anchor-goldens@a2f49ccf` (interim base; rebases onto `main` after #1513 merges). Old
  `ta-anchor-refactor@34055d77` left unpushed for Dean to archive with `git boidem` at his
  convenience — not urgent, no PR.
- **Scope.** PR-1 = static core (5 commits above), zero combine-arithmetic change, decision-set
  identity ship gate via #1513 goldens (green at every commit), opt-in enablement, TA-side complement
  bundled as its own commit. Deferred/out-of-scope (documented in §3/§12): §2.4 partial
  scale-from-zero picker, §2.3-3 AnalyzerName validation (separate PR), sat-v2 `aggregateByVariant`
  Cost/AcceleratorName bug (separate fix), QM path (DEFERRED — refused via explicit error, never a
  silent V1/sat-v2 fallback; open GitHub-issue question for Dean). 3 non-blocking follow-ups tracked
  in §7c (QM e2e sweep, NumReplicas persistence check, flapping risk).

## Next steps / operational asks (for Dean — capture in CURRENT.md § Next steps)

- **Worktree/branch creation (git op — outside planner write scope, Dean or coder to run):** create
  worktree `ta-anchor-refactor-v2` off `a2f49ccf`:
  `git -C repo worktree add ../ta-anchor-refactor-v2 -b ta-anchor-refactor-v2 a2f49ccf`, then
  `git -C ../ta-anchor-refactor-v2 push -u origin ta-anchor-refactor-v2` (subject to the no-push-
  without-confirmation rule). Do NOT start coding until (a) the review agent's review lands and Dean
  reviews it, and (b) Dean gives the go-ahead (discuss-before-implementing rule).
- **Mark the review FINAL** after the review agent completes and Dean signs off (review agent/Dean).
- **#1513 goldens** are the hard dependency — must be merged/green before this PR can ship.

## Open questions / follow-ups (none blocking)

- Whether to commit the restructured `ta-anchor-refactor-review.md` (still DRAFT) to plans — deferred
  to Dean / the review agent.
- File a GitHub issue for the queueing-model multi-analyzer-contract work (§12 DEFERRED)? Dean's call.
- Pre-existing sat-v2 `aggregateByVariant` Cost/AcceleratorName bug stays on the Issues-to-Open radar.
