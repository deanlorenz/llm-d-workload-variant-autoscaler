# Rebase integrity

### convention: rebase-integrity-commit-message-vs-diff
description: Commit messages must reflect the diff, especially after a rebase; a hard reject if a message claims behavior the diff doesn't implement.
scope: anyone rebasing a multi-commit stack, or reviewing rebased commits
trigger: after any rebase that replays commits onto a base where touched files moved
status: active
origin: session/CONVENTIONS.md § Commit messages must reflect the diff — especially after rebase (C42)

**Commit messages must reflect the diff — especially after rebase.**
A commit message that describes behavior the diff doesn't implement is a hard reject. Each "Engine
populates X", "Adds Y", "Fixes Z" claim must correspond to a code hunk in the same commit.

After any rebase that replays a commit onto a base where the touched files have moved (e.g.
`git rebase --onto <new-base>`), git's three-way merge can silently drop hunks that no longer apply
cleanly — leaving the commit message intact while the behavior is gone. Procedure for non-trivial
rebases (multi-commit stack AND any touched file has been modified on the new base):

0. **Pre-rebase plan.** Before executing the rebase, write a short plan (Type 3-style, ephemeral
   — delete after the rebase is verified). Contents: ordered commit list with a one-line "behavior
   to preserve" per commit (mined from the commit message), files expected to conflict on the new
   base, and the post-rebase verification checklist (which diffs to run, which claimed behaviors to
   confirm). **Where it lives depends on your role's write scope** (per "Worktree scope" above):
   the **plan-agent** writes it at planning/<branch>-rebase-<target>.md; a **coder** has no write
   access to plans/planning/, so the coder instead records it in its own
   plans/session/status/<branch>.md (or a `plan__*.md` handoff) — never under `planning/`. The
   artifact is the same; only the sanctioned location differs by role. Skip the plan entirely for
   single-commit rebases or rebases that apply cleanly.
1. **Per-file diff inventory.** After the rebase, for each touched file, run
   `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` and confirm every behavior claimed in
   the rebased commits' messages is still present in the post-rebase code.
2. **Per-commit message-vs-diff check.** Read each post-rebase commit's diff against its own
   message — if the message says "Engine populates Score" and the engine_v2.go diff doesn't show
   the population, the commit is broken and must be fixed before the rebase is considered done.
3. **Backstop test.** Where feasible, add a test that asserts the claimed behavior **before** the
   rebase, so silent loss converts to a red test on the next run. This is the strongest backstop;
   (1) and (2) are eyeball checks that only work while the reviewer is paying attention.

The "Score field silently dropped during cross-rebase" incident on `multi-analyzer-optimizer` is
the load-bearing example — the commit message claimed "Engine populates Score from
AnalyzerScoreConfig.Score" across two commits while the diff showed neither populating it.

### convention: rebase-integrity-no-rebase-live-pr
description: Never rebase, amend, or otherwise rewrite the history of a branch that has an open PR without consulting Dean first, even when it seems needed for an adjacent task; merge un-rebased branches into a throwaway integration branch instead.
scope: planner or coder about to rebase, amend, or otherwise rewrite history on a branch
trigger: a task seems to require rewriting history on a branch that has an open PR
status: active
origin: feedback_no_rebase_live_pr_branches.md

Open PRs do **not** chase main — rebasing happens only at reviewer request or just before final
merge. Rewriting a live PR branch and/or pushing it confuses reviewers looking at the existing
diff. To assemble an integration/test branch from open-PR branches, merge them un-rebased into a
throwaway branch — never rebase the PR branches themselves. If a task genuinely seems to require
rewriting a live PR branch, stop and ask Dean before doing it.

**A plan doc asserting a rebase is "needed" does not itself authorize it.** This is the same
pre-action-gate principle as worktree scope: documents describe what should happen; standing
approval requirements govern who may do it and when. A written plan step, executed mechanically
as delegated work, does not trigger the standing approval requirement on its own — auto mode does
not relax this either. When a plan step would rewrite a live PR branch, treat that as a signal the
plan is wrong, not as authorization to proceed.

### convention: rebase-integrity-target-is-tip-not-sha
description: A rebase instruction must target the moving ref (e.g. upstream/main), never a pinned commit SHA; any SHA in a doc is informational-as-of-authoring only.
scope: planner writing a rebase instruction; coder executing one
trigger: writing or reading a rebase step in a plan or handoff
status: active
origin: feedback_rebase_target_is_tip_not_sha.md

When a plan or handoff tells a coder to rebase, the target must be the **moving ref**
(`git fetch upstream && git rebase upstream/main`), never a specific commit SHA. Any SHA in the
doc is informational-as-of-authoring only — say so explicitly and never present it as the literal
target: no "rebase onto `<sha>`," no enumerated "the N commits `base..<sha>`" list framed as the
destination. The tip advances between authoring and when the coder runs the rebase; a pinned SHA
goes stale and reads as "rebase onto exactly this one commit," so coders either rebase onto a
stale base or stall noticing the discrepancy. If churn context helps (renames, moved packages),
give it as a **non-exhaustive** "expect this during conflict resolution; diff against your actual
rebased base" note — never a definitive commit list.
