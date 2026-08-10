from: review
to: sync
session: correction — the "941 uncommitted lines / finding V9" reading

## Purpose

A **correction**, not a state report. Do **not** record "941 uncommitted reviewer lines including
finding V9" — that reading is wrong on all three of its parts, and folding it into CURRENT.md would
leave a merged PR looking like it has an open correctness finding.

## 1. The reviewer docs are now COMMITTED

`fe372ce8` on `plans` — three reviewer-owned docs, 1237 insertions:

- `planning/ta-anchor-refactor-v2-code-review.md` (NEW, 825 lines) — PR-1 review incl. the
  definitive push-ready section at tip `075a208e` (verdict **APPROVE**).
- `planning/ta-anchor-refactor-review.md` (+370) — Part 3 / Round 2 (V8–V11).
- `planning/ta-anchor-refactor-v2-coder-checklist.md` (NEW, 47 lines).

**Both review docs remain `Status: DRAFT`** — Dean marks FINAL at his discretion; committed ≠ final.

**➡️ CURRENT.md edit:** PR-1 residual **(a)** currently reads that these are "**DRAFT and
uncommitted** — reviewer-owned, the **only copies**, flag before any worktree reset." The
sole-copy hazard is **gone**. Replace with: *review docs committed `fe372ce8`, still DRAFT pending
Dean's FINAL call.* Drop the worktree-reset warning.

This also supersedes the equivalent claim in my earlier
`sync__ta-anchor-refactor-v2-push-ready.md` § *Open questions* — that line is now stale.

## 2. The 941 figure was misattributed AND undercounted

`git diff --stat planning/` = 941 insertions across **two** modified tracked files:

| File | Ins. | Owner |
|---|---|---|
| `planning/multi-analyzer-dataflow-map.md` | 642 | **NOT the reviewer** |
| `planning/ta-anchor-refactor-review.md` | 370 | reviewer (now committed) |

- **642 of the 941 is the dataflow map** — it belongs to the deferred
  `plan__ta-anchor-dataflow-map-pr1-delta.md` thread and is **still uncommitted, still its owner's**.
  Do not attribute it to the review, and do not commit it on that owner's behalf.
- **941 also missed 872 untracked reviewer lines** (`git diff --stat` cannot see untracked files),
  including the doc carrying the APPROVE verdict. So the number simultaneously over-attributed and
  under-counted.

## 3. Finding V9 is CLOSED — in both plans and in code, all committed

V9 = the PR-1 plan describing the `bindingAnchor` **(b)-fallback** as *ungated* in §6 while §2 gates
it. Classified "should-fix before coding — executability", a **documentation** defect, never a
mechanism change. Its full lifecycle, all in git:

- `ta-anchor-refactor-v2-plan.md:3` — "Status: FINAL (Review Round 2 folded in 2026-08-05 —
  V8/**V9**/V10/V11; coder-ready)"
- `ta-anchor-refactor-v2-plan.md:1047` — V9 named, marked **superseded**
- `ta-anchor-dynamic-refresh-plan.md:1168` — "**revises PR-1 plan decision V9** (PR-1 ships the
  fallback as-is — see PR-1 §12)"
- **Shipped code verified gated:** `analyzer_helpers.go:169` (`satEnabled := satNR != nil &&
  satNR.Enabled`) + `:208` (`else if satEnabled`) — i.e. §2's gated form, not §6's wording.
  Recorded ✅ PASS / not-a-blocker in `ta-anchor-refactor-v2-code-review.md` (checklist row 3).

**➡️ Do not create a CURRENT.md item, Issues-to-Open entry, or open-finding note for V9.** The
uncommitted text sync saw was the *write-up* of resolved work, not a live finding.

## 4. PR-2's review docs were never uncommitted

`planning/ta-anchor-dynamic-refresh-review.md` (Findings 76/77/78) and
`ta-anchor-dynamic-refresh-plan.md` are **committed and clean** — the review doc last at `a8f9327f`
("post-rebase check clean, no hunks dropped (Finding 78)"); neither appears in `git status`. If the
941/V9 reading was suspected to concern the dynamic-refresh (PR-2) thread: it does not. No PR-2
review state is at risk, and CURRENT.md's PR-2 row needs no change from this handoff.

## Net CURRENT.md changes requested

1. PR-1 residual (a): "DRAFT and uncommitted / only copies / flag before worktree reset" →
   "committed `fe372ce8`, still DRAFT pending Dean's FINAL call."
2. § Next steps, anchor-refactor bullet, **Reviewer's** clause ("commit the still-uncommitted …
   then mark them FINAL") → the commit half is **DONE**; only Dean's FINAL call remains.
3. Nothing else. No V9 entry, no 941 figure, no PR-2 change.

## Still genuinely outstanding (not mine, unchanged)

- `planning/multi-analyzer-dataflow-map.md` — 642 uncommitted lines, owner's;
  `plan__ta-anchor-dataflow-map-pr1-delta.md` remains **OPEN and deferred by Dean — not sync's to
  consume.**
