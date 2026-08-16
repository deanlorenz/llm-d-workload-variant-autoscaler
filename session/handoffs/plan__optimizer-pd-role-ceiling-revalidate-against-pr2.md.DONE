from: plan (context-cost-reduction session, 2026-08-09)
to: planner
session: re-validate optimizer-pd-role-ceiling against the anchor refactor now in place

## Why this exists

Dean's direction, 2026-08-09: *"role-ceiling planner should check what is still valid with PR-2 in
place."*

`optimizer-pd-role-ceiling` has been untouched for ~3½ weeks (tip `0c33a3eb`, 2026-07-15). In that
window the optimizer/pipeline it reasons about changed substantially:

- **PR-1 `ta-anchor-refactor-v2` MERGED** as `57f3fe64` on `main` (29 files, +2077/−166) — the anchor
  is now derived on demand by a per-variant merge in `bindingAnchor`, and analyzer enablement is
  explicit. `a38d7b73` additionally fixed a phantom `RoleBoth` bucket that suppressed **all** P/D
  scale-up when any variant sat at zero replicas — which is squarely role-ceiling territory.
- **PR-2 `ta-anchor-dynamic-refresh`** is code-complete and reviewed (tip `6d55fbd7`, 26 commits, not
  pushed): five lock-step arithmetic-bug sites, the fair-share currency pivot into GPU space
  (`fairShareCap` became a whole-replica `floor`), `fillRole` identified as the real unbounded grant,
  and `FZ-admission` as a `PRC = 1` sentinel.
- Toolchain moved on `main`: go 1.26.0 and golangci-lint v2.10.0 (PR #1512), so this branch's green
  `make lint` from before does **not** carry forward.

## What to check

1. **Do the 10 landed tests still assert something true and reachable** after the anchor refactor?
   Some fixtures may now construct states the merged code cannot reach.
2. **Is the suspected bug still live** — anticipated supply sitting in the denominator rather than
   counting toward achieved (`optimizer-coordination-design.md` § Open issues #2, never traced)? PR-1's
   `RoleBoth` fix and PR-2's `fillRole` work may have moved or fixed it.
3. **Does the clean-design model still hold?** Two Phase-2 framing questions are unanswered and Phase 3
   (verify code vs the clean model) never started; the model was drawn pre-refactor.
4. **Rebase cost onto current `main`**, plus a fresh `make lint` under 2.10.0.

## Hazard — read before touching the worktree

The planner made dev-guide edits **directly in the worktree and never committed them**
(`M docs/developer-guide/multi-analyzer-pipeline.md`). They are the only copy. Commit or capture them
before any rebase, checkout, stash, or reset.

## Not in scope for this handoff

Whether to revive or park the thread is Dean's triage call — this is the fact-finding that should
precede it. Nothing here authorizes code changes or a push.

Refs: `planning/optimizer-pd-role-ceiling-plan.md`, `planning/optimizer-coordination-design.md`,
`planning/ta-anchor-refactor-v2-plan.md`, `planning/ta-anchor-dynamic-refresh-plan.md` (FROZEN
@ `4fa91b7e`), `planning/combined-analyzer-optimizer-design.md` (FINAL @ `8c2a9b04`).
