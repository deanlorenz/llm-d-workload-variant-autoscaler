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
