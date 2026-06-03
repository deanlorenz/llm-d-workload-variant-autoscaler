to: sync-current
session: multi-analyzer-threshold-coder-rules-gap

## Observation
A parallel coder agent (different worktree) violated the worktree-scope rule by `cd`-ing into another worktree before running git to check on a different branch. Reported by Dean during the multi-analyzer-threshold session on 2026-05-31.

## Where the rule lives today
- **`session/CONVENTIONS.md` "Key Working Rules":**
  - "Worktree scope. Every agent or coding task operates exclusively within its assigned worktree. … never touch a sibling worktree."
  - "Switching worktrees — use `EnterWorktree`. … Never use bare `cd` or `-C` flags as a substitute for a context switch."
- **`planning/multi-analyzer-coder-rules.md`:**
  - §1 "Worktree scope — only edit inside your branch" — focuses on edits/writes/file creations/deletions. Does not restate the git-specific implication.
  - §7 lists `git status / diff / log / branch / show / rebase (within your branch) / commit` as allowed without asking, but does not say "from your own worktree only" / "no `cd` or `-C`".

So the constraint exists in CONVENTIONS as a general scope rule + an explicit `cd`/`-C` prohibition, but a coder agent reading only `multi-analyzer-coder-rules.md` (the doc whose required-reading order puts it last and is the most operational) will not see the git-specific form spelled out. CONVENTIONS is required reading first per §0/§1 of the coder-rules, so the rule is technically present — just not in the operational doc the agent is most likely to refer back to mid-session.

## Suggested options (plan-agent to decide)
1. **One-liner add to `multi-analyzer-coder-rules.md` §1:** something like "All git operations run from your own worktree only. No `cd` to a sibling worktree before `git`, no `git -C <sibling>`. To work on another branch, use `EnterWorktree` per CONVENTIONS." — restates a CONVENTIONS rule in the operational doc the agent reads on every entry.
2. **Add the same line to §7/§8** (Things you may / may NOT do) — "may NOT: `cd` to a sibling worktree, pass `-C <sibling>` to git, run any git command targeting another worktree's HEAD."
3. **Both** — §1 frames it conceptually, §7/§8 makes it operationally enforceable.
4. **Leave coder-rules unchanged**, strengthen CONVENTIONS phrasing instead — e.g., add "git operations are bound by this rule too; never `cd` or `git -C` to a sibling for any git command."

## Self-check from this session
The multi-analyzer-threshold coder did not violate the rule: every `git` invocation ran from `multi-analyzer-threshold/` after `pwd` confirmation; no `cd` or `-C` to a sibling worktree. Reads of files under `plans/` used the `Read` tool with absolute paths (which CONVENTIONS allows for context); the handoff was written via `Write` to `plans/session/handoffs/`, which the coder rules explicitly authorize.

## Not a coder action
Coder agents do not write to `multi-analyzer-coder-rules.md` or `CONVENTIONS.md`. This handoff is a flag for the plan-agent; the plan-agent decides whether and how to apply.
