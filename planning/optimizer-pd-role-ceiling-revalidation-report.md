# optimizer-pd-role-ceiling — revalidation report

**Read this file, not chat.** Everything below is documentation only — **no code was touched, no
rebase performed, no push made.** Both edits are in `planning/optimizer-pd-role-ceiling-plan.md`
(committed `c5e91514`, `359f3c55`) and a handoff closed `.DONE`.

## Why this exists

`optimizer-pd-role-ceiling` had no commit or status update in 19 days — inactive under your rule
("any planner not committing in the last week is inactive; take over their docs"). A fact-finding
handoff sent 2026-08-09 asking whether this mission's 10 tests, a suspected bug, and its clean-design
model still hold against the now-merged anchor refactor had sat unanswered for a week. I answered it
by direct code comparison, wrote the findings into the plan doc, and closed the handoff.

## What you need to react to — one thing

**You said the denominator bug claim (Q2) was wrong. You were right, and I've now traced why and
corrected the doc.** My first pass cited a passage from `ta-anchor-dynamic-refresh-plan.md` as
"countervailing evidence" — that citation conflated two unrelated discussions that both happen to say
"denominator." Direct diff of the actual code between `main` and the PR-2 branch shows PR-2 rewrote
`allocateForModelPaired`'s `roleAggRemaining` a second time (beyond `main`'s own rewrite): it no longer
reconstructs an `achieved`/`denom` ratio at all — it finds the analyzer actually winning the vote for
each variant and reads that analyzer's own remaining demand directly. The specific numerator
(`achievedByRole` dropping pending/booting supply) the design doc's D1 flagged **does not exist in
either `main` or PR-2's code**. So D1 isn't relocated or still-live — the code it described is gone.

**Nothing more is needed from you on this specific point** — it's corrected in the plan doc
(§ "Re-validation against the anchor refactor," Q2), committed. Flagging it here only because you
should know the correction landed, not because it's still open.

## What's still open — genuinely needs your input, not mine to decide

**One real fresh question, surfaced by this correction, not resolved by it:** PR-2's new
`roleAggRemaining`/`refreshAnchorSizing` shape (find-the-winner, read-its-demand-directly) is a
different design than the "achieved = current + anticipated + committed" clean model
`optimizer-coordination-design.md` describes. Nobody has checked whether PR-2's shape is *equivalent*
to that clean model, *better*, or a *third, undocumented approach*. This is a fresh design question, not
a re-litigation of the retired D1 — I did not attempt to answer it, since it's design judgment, not a
fact to trace.

**Everything else from the original four questions (tests, clean-design model, rebase cost) is
unchanged from what was reported to you earlier** — summarized below for completeness, not re-litigated:

| Question | Finding |
|---|---|
| Are the 10 tests still valid? | 4 are fixable (one missing struct field) but redundant with `main`'s existing coverage. 6 — including this mission's own last 2 commits — test a formula (`jointCap`/`achievedByRole`) neither `main` nor PR-2 computes anymore; porting them needs re-deriving expected values against the new formula, not a mechanical fix. |
| Does the clean-design model hold? | Partially. The supply taxonomy and data-layer mapping still hold. The Phase-3 *code verification* is stale — it cites line numbers inside a function both `main` and PR-2 have since rewritten (twice, per this correction). |
| Rebase cost? | Small in file count (4 files, ~600 lines of this branch's own work) but lands squarely on the one function (`allocateForModelPaired`) that both `main` and PR-2 independently rewrote — expect a real conflict, not a clean reapply. This branch is also the only tracked one that hasn't re-verified `make lint` under the go 1.26/golangci-lint 2.10 toolchain bump. **Per your instruction: no rebase was attempted or is proposed.** |

## Where the full detail lives

`planning/optimizer-pd-role-ceiling-plan.md`, section **"Re-validation against the anchor refactor
(2026-08-16)"** (near the end of the file) — has all four answers with file:line citations. This report
is the pointer + the one thing needing your reaction; that section is the record.

## Also touched this session, unrelated but adjacent (doc-only, no active-owner docs touched)

- `planning/benchmark-observability-plan.md` — added a one-paragraph supersession pointer (it's an
  ownerless, already-superseded Type 3; content otherwise untouched).
- `planning/doc-coverage-audit-20260816.md` — the earlier six-mission doc-coverage audit you reviewed;
  unchanged since.
- Two process asks sent to the atomic-step-protocol planner (their mission, not mine to design):
  scoping Type-3 call-stacks to only the affected paths, and an interim Type-2 home for aggregated
  post-coding call-stacks. Handoff: `session/handoffs/plan__call-stack-process-two-asks.md`.

No active-owner Type 1/2/3/4/6 doc was touched. Nothing pushed. Nothing rebased.
