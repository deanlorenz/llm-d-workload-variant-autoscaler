last_update: 2026-08-09
state: idle — plan frozen and current; one owned work item (`B2`) not started
current_step: Nothing in flight. Plan doc is verified current against PR #1523 @ `14a5d6cc`. Next action when resumed is to write the `B2` spec.
blocked_on: —

## Role — read this first on a cold resume

**`planner` for PR-2** — owner of the Type 3 `planning/ta-anchor-dynamic-refresh-plan.md`. Not the coder,
not the reviewer, not the designer, not sync.

| | |
|---|---|
| **Owns (may edit)** | `planning/ta-anchor-dynamic-refresh-plan.md` · own handoffs under `session/handoffs/` · this status file |
| **Must never write** | code or anything in a code worktree · `planning/combined-analyzer-optimizer-design*.md` (designer's; parent is FINAL/frozen) · `planning/*-review.md` (review agent's) · `session/CURRENT.md` and shared `session/` state (sync is the sole writer) · GitHub (no pushes, no comments, no PR edits) |
| **Communicates by** | handoff only — `sync__` for CURRENT updates, `designer__` to the Type-1 owner, `review__` to the reviewer, `ta-anchor-dynamic-refresh__` as a doorbell to the coder |

Other roles: `designer` (Type 1 + Addendum 1, status `session/status/designer-type1-addendum.md`) ·
`review` (internal reviewer, Findings 1–78 in `planning/ta-anchor-dynamic-refresh-review.md`) ·
`coder` on branch `ta-anchor-dynamic-refresh` (status `session/status/ta-anchor-dynamic-refresh.md`) ·
`sync` (sole CURRENT.md writer).

## Where the work stands — PR #1523 is OPEN, PUSHED, and fully GREEN

**Verified read-only 2026-08-09.** Authority for all of it is the Type 3 § *Where the branch actually is*
and § *Open items and next steps* — this file points, it does not duplicate.

- PR **#1523**, base `main`, head `ta-anchor-dynamic-refresh`, tip **`14a5d6cc`**, **28 commits** on
  `main@a6b39809`. Local ≡ origin ≡ PR head ⇒ **nothing outstanding to push.** `MERGEABLE`,
  `REVIEW_REQUIRED`.
- **CI green across the board**: `gate`, `DCO`, `signed-commits`, `lint-and-test`, `kustomize-build`,
  `check-code-changes`, `e2e-tests-full`, `e2e-tests-smoke`. All 28 commits DCO-signed *and*
  crypto-signed (`%G?` = `G` ×28).
- Internal review is **complete and clean**: Finding 76 (the freeze-point review), **77** (`C12`/`AD8` (b)
  matches §2g exactly), **78** (post-rebase check clean). No defects outstanding.

## The one thing I still owe

**`B2` — a discriminating spec for `fairShareRolePick`'s per-role budget.** Not started. Detail and the
reason it is non-urgent are in the Type 3 § *Open items and next steps* item 1. Short form: clamp-only
passes both shipped specs, so `committed0` / `reserved` / the per-draw holdback / the `firstDraw` floor are
pinned by nothing; the shipped behavior is correct but under-pinned, so this guards a future regression
rather than fixing a present defect. Technique exists in-tree (call the returned pick closure directly, as
`40d17878` does). Writing the spec is mine; landing it is a coder action afterwards.

## Armed footguns / things a resuming session must not undo

- ⚠️ **The PR carries a stale `github-actions` comment reading *"Unsigned commits detected!"*** — posted
  9 s after the PR opened, against the pre-re-sign push. `signed-commits` **passes** at current head. Do
  not "fix" signing; nothing is wrong.
- ⚠️ **§1.1.0's landed ledger holds PRE-REBASE SHAs.** The branch was rebased (`--onto main 075a208e`), so
  none of those SHAs resolve on the branch any more. The table is a historical record, deliberately kept.
- ⚠️ **Do not re-raise `AD8` (b)'s "third site" as a gap.** `CapGPUs`/`Demand` in `rescaleInputsForGroup`
  is reached *via* the abstain predicate at `votesFromTotalDemand`, which `C12` patches; `rescale.go` needs
  no direct tag reference. I raised this as a gap on 2026-08-09 and was wrong — §2g already scoped it, and
  names the residual rather than closing it, by design.
- ⚠️ **Do not re-open `ceil`/`floor`.** Retracted 2026-08-08 (`1cca5563`): two terms rounding in opposite
  directions on purpose; the Type 1's `floor` mandate covers the pool term only, which ships satisfied.
- ⚠️ **Do not re-quote §4's "22 of 25 commits carry a token".** The reword was executed during the rebase;
  every subject is clean. That prose is retained as history only.
- ⚠️ **PR-2's 0.9 inclusion is OPEN — Dean decides after merge.** Do not record it as in or out. The
  tag-is-freeze-marker / branch-is-actual-content distinction was about **PR-1**, not PR-2.

## Notes

- `planning/ta-anchor-dynamic-refresh-PENDING-EDITS.md` still exists and its § A rows are largely applied,
  but its **§ B/§ C rows are Dean-owned decisions and other roles' items**, not planner to-dos. Its own
  header says to delete it once the batch lands; that is a judgement call I have not made.
- Evidence discipline: every claim above was verified read-only at the current tip, via
  `git -C ../ta-anchor-dynamic-refresh` and `gh ... --json`. **Never `cd` into the coder's worktree** and
  never a git write-verb there.
