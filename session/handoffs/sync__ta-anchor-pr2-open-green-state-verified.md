from: plan (PR-2 Type-3 owner)
to: sync
session: PR-2 / #1523 — state verified 2026-08-09; supersedes my two earlier PR-2 sync handoffs

## Refs — point CURRENT at these, do not restate them

- **My own state file (new, authoritative for this role's cold resume):**
  [`session/status/planner-ta-anchor-pr2.md`](../status/planner-ta-anchor-pr2.md)
- Type 3: `planning/ta-anchor-dynamic-refresh-plan.md` — § *Where the branch actually is* (current state)
  and § *Open items and next steps* (`{#open-next}`, the owner table).
- Review doc: `planning/ta-anchor-dynamic-refresh-review.md` — Findings **76**, **77**, **78**.

## Supersedes

**Both of my earlier PR-2 sync handoffs are now stale — prefer this one where they conflict:**
`sync__ta-anchor-pr2-code-complete-reviewed-no-defects.md` and
`sync__ta-anchor-pr2-rounding-retraction.md`. They describe an unpushed 26-commit branch with no PR open.

CURRENT.md's own ⚠️ note (added by sync) is correct that the PR-2 facts were stale, and this handoff is the
rewrite it says it is waiting for.

## Resume prose — enough to triage without opening the plan

**PR [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) is OPEN, PUSHED, and
fully GREEN. Nothing is blocked and nothing is outstanding to push.** Tip **`14a5d6cc`**, **28 commits** on
`main@a6b39809`; local ≡ origin ≡ PR head. `MERGEABLE`, `REVIEW_REQUIRED` (no *external* review submitted;
internal review is complete). CI: `gate`, `DCO`, `signed-commits`, `lint-and-test`, `kustomize-build`,
`check-code-changes`, `e2e-tests-full`, `e2e-tests-smoke` — **all pass**; all 28 commits DCO-signed and
crypto-signed. `lint-and-test` green also retires the golangci-lint 2.8.0→2.10.0 concern CURRENT carries
under § Next steps.

**Every decision that was open is now closed.** `AD8` (b) placement → **in this PR**, landed as `C12`
(`4e5bbf12`, pre-rebase `136a214a`), reviewed defect-free (Finding 77). The `ceil`/`floor` question →
**retracted, never a fork** (`1cca5563`). The §4a commit-message reword → **executed** during the rebase,
all subjects clean. The plan freeze → **done**. The branch was rebased onto `main` and the rebase was
reviewed clean (Finding 78) plus independently re-verified for dropped hunks (none).

**One open work item, mine: `B2`** — a discriminating spec for `fairShareRolePick`'s per-role budget. Not
started, **not blocking merge**: clamp-only passes both shipped specs, so `committed0`/`reserved`/the
per-draw holdback/`firstDraw` are pinned by nothing — the shipped behavior is correct but under-pinned, so
it guards a future regression rather than fixing a present defect.

**Dean's, none blocking merge:** (a) two PR-*body* claims run ahead of the code — "partial proactive
from-zero admission" is **built-not-enabled** (C11 (D-a) deferred), and the body omits that regime (i), the
freeze, survives (`C12` closes only the drain); (b) **PR-2's 0.9 inclusion is deliberately OPEN — he
decides after merge**; (c) requesting an external review on #1523.

## Armed footguns to carry verbatim into CURRENT

- ⚠️ **The PR shows a stale `github-actions` comment *"Unsigned commits detected!"*** — posted 9 s after the
  PR opened, against the pre-re-sign push; the bot never retracts. `signed-commits` **passes**. Nothing to
  fix; do not let it read as a live failure.
- ⚠️ **Do NOT record PR-2 as in-or-out of 0.9.** Undecided until after merge. The
  tag-is-a-freeze-marker / `release-0.9`-branch-is-the-actual-content distinction (branch cut later,
  probably pre-RC1) was about **PR-1**, not PR-2.
- ⚠️ **§1.1.0's ledger SHAs are pre-rebase and no longer resolve** — kept deliberately as history.
- ⚠️ **`AD8` (b)'s "third site" is not a gap** — I raised it as one and was wrong; it is reached via the
  same abstain predicate at `votesFromTotalDemand`. Do not schedule it.

## CURRENT edits requested

1. Rewrite the PR-2 half of the anchor-mission entry from the resume prose above, and **replace the ⚠️
   stale-facts note** — it has served its purpose.
2. PR Status: `ta-anchor-dynamic-refresh` row → **PR [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) OPEN, tip `14a5d6cc`, 28 commits, CI all-green, internal review clean (Findings 76/77/78); awaiting external review. Open: `B2` (planner), PR-body accuracy + 0.9 call + review request (Dean).** Point detail at my status file, not at prose here.
3. § Next steps, anchor-mission bullet: drop the now-closed items (`AD8` (b) placement, the push
   authorization, `ceil`/`floor`) and keep only what is live per the owner table in the plan's
   § *Open items and next steps*.
4. § Next steps, toolchain bullet: PR-2 no longer needs a post-rebase `make lint` re-run — CI's
   `lint-and-test` is green under 2.10.0. `optimizer-pd-role-ceiling` is unaffected by this and still does.
5. Mark my two superseded `sync__` handoffs consumed alongside this one.
