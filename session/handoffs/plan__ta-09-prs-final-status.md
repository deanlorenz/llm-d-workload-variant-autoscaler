from: planner (auto-mode session)
session: ta-09-prs-final-status

## What changed (2026-07-28) — TA 0.9 PRs, post forward-rebase + merges

All four TA 0.9 PRs were rebased onto current upstream `main` and pushed; two have merged.

### Rebase + push
- The coder rebased A′/C/D from `ef28744b` **onto `827c8542`** (upstream tip at rebase time;
  A #1478 had merged, becoming that tip; #1452 rescale had merged as `31fd0f84`). A
  (`ta-devguide-fixes`) was already merged and untouched.
- D's only real conflict was `internal/engines/pipeline/analyzer_helpers.go` vs #1452 — both
  inserted new top-level decls at the same spot. Resolved by keeping **both** (#1452's
  `rolesOf` + D's `analyzerReasonNoData/Error` consts + `ResultIsInformative`). The 5 liveness
  commits then applied with zero further conflicts (#1452 never touched
  `needsScaleDownForRole` / `safeRemovalReplicasForRole` / `applyDeallocationForRole`). No
  semantic decision was forced; RC-2 gap confirmed pre-existing/unchanged.
- All three passed full gates (`make test`, gofmt, `make lint`, `go build`; `-race` on D) with
  complete DCO. Dean-confirmed `--force-with-lease` pushes landed:
  - A′ `ta-registration-safety` #1479 → tip `b706228d`
  - C  `ta-model-level-demand`  #1480 → tip `7aec2645`
  - D  `ta-veto-liveness`       #1481 → tip `19c9a122`

### CI / merges
- All three re-dispatched `lint-and-test` and went **green** (D finally got a merge ref once
  conflict-free — the earlier CI silence was the CONFLICTING state, not a dropped webhook).
- **#1478 (A) — MERGED.**
- **#1479 (A′) — MERGED by ev-shindin.** Release note added to body + stale #1477 caveat
  removed before merge; `/ok-to-test` triggered e2e (both e2e-tests-full/smoke SUCCESS).
  Upstream `main` tip is now `11d70a8a` (the #1479 merge commit).
- **#1480 (C)** and **#1481 (D)** — OPEN, MERGEABLE (no conflict from #1479's merge),
  release notes added + stale #1477 caveat removed. `BLOCKED` only on ev-shindin's review.

## Update CURRENT.md
- **PR Status table:** A #1478 already MERGED (no change). A′ #1479 → **MERGED** (`11d70a8a`
  on main). C #1480 → OPEN, rebased onto `827c8542` (tip `7aec2645`), release-noted, mergeable,
  awaiting review. D #1481 → OPEN, rebased onto `827c8542` (tip `19c9a122`), release-noted,
  mergeable, awaiting review. Drop the "#1477 / CI red" caveat from all rows — main compiles;
  fix landed as #1483 (and A/A′ have merged).
- **Recent activity head/tail:** the "all four PRs opened; CI red until #1477" abstract is now
  stale. Replace with: TA 0.9 — A + A′ merged (`11d70a8a`); C + D rebased onto current main,
  green, release-noted, awaiting ev-shindin review.
- **Next steps:** the "forward-rebase pending #1477" item is DONE — remove it. Remaining TA 0.9
  item is just "watch for ev-shindin review on C (#1480) + D (#1481)."

## Requested deletions (Type-3 ephemeral rebase docs — verified + pushed, safe to remove)
- `planning/ta-09-rebase-ef28744b.md`
- `planning/ta-09-rebase-827c8542.md`
(Both superseded; the rebase they describe is done, verified, and pushed. Deleting via the sync
session to keep planning/ writes serialized — see the sync-model handoff's open question.)

## Not done / notes
- No CURRENT.md edit made by this session (single-writer model — this is a handoff only).
- Consumed trigger: `ta-veto-liveness__rebase-827c8542-conflict.md.WIP` → the coder's
  push-ready handoff `plan__ta-veto-liveness-rebase-827c8542-done.md` (may still be open in
  the queue; contains the same rebase detail).
