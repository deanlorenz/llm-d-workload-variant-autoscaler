from: planner (llm-scaler workspace bootstrap design)
to: plan (atomic-step-protocol-brainstorm — you own these scripts and have a coder on them)
session: sync-main must be generalized over (repo, container, branch) — new repo has no `main`

## Why this is coming to you

Dean's instruction: any plan-tools change goes to you, because you are actively working these
files and have a working coder to implement them. He also said specifically: **incorporate this
requirement into the Type 3 and fix it.** So this is a requirement to fold in, not a suggestion.

Context: I'm drafting `planning/llm-scaler-workspace-bootstrap-design.md` (DRAFT, uncommitted) —
standing up a second VSCode workspace for `git@github.com:deanlorenz/llm-scaler.git`, same
construction as this one (bare repo + worktrees + plans branch + conventions + skills + session
protocol). A hardcoding sweep of the tooling found `sync-main` to be the one script family that
does not port, and Dean ruled it must be **generalized, not path-fixed**.

## ⚠️ Coordination — there is already a `.WIP` handoff on this exact file

`plan__sync-main-hook-silent-noop-and-tier1-tier2-boundary.md.WIP` (from sync) reports a
**different** defect in the same script: `sync-main-session-start.sh:10`'s
`[ "$cwd" = "$SYNC_WORKTREE" ] || exit 0` silently no-ops when the cwd string-match fails, with
no log on the no-op path.

**These two are the same root cause seen from two sides, and fixing them together is cheaper than
fixing either alone.** That handoff's bug *is* the hardcoded-single-container assumption:
`SYNC_WORKTREE` is a hardcoded absolute path (line 5) compared by exact string equality, so the
script cannot express "this is one of several valid containers" — the only outcomes are exact
match or silent exit. Generalizing the identity resolution replaces the comparison that is
silently failing. I am **not** asking you to re-open that item; I'm asking that whoever picks it
up knows both asks land on the same lines, so the fix is designed once.

## The requirement

Three things are baked in, and **only one is a path** — this is why `dirname $0` derivation (my
own first suggestion, and too weak) does not solve it:

| Baked-in | Site | Why it breaks on `llm-scaler` |
|---|---|---|
| **Container path** | `sync-main-session-start.sh:5` `SYNC_WORKTREE="/home/dean/.../plans"`; `sync-main-status.sh:12` `S=/home/dean/.../session/status/main.md` | different container — the easy half |
| **Repo identity** | assumes an `upstream` remote distinct from `origin` (fork-of-upstream topology) | `llm-scaler` is Dean's own repo. There may be **no `upstream` at all**, so "fast-forward from upstream" has no referent |
| **Branch identity** | `main` as *the* tracked branch, in name and concept — `Main/` worktree, `status/main.md`, the skill's whole vocabulary | **the new repo does not use `main` yet.** Not a rename — there is currently no branch to track |

That third row is the load-bearing one. A script parameterized only over paths would still be
asserting that a `main` exists to sync.

**What generalization means concretely** (shape, not a design — the design is yours):

1. Parameterize on `(container_root, tracked_branch, upstream_remote)`, resolved from **config,
   not inference**. Config over auto-detection for the same reason `feedback_tools_take_explicit_paths`
   gives — the caller knows, the script shouldn't guess. This also gives the sync-hook bug a real
   fix: an explicit identity can be *reported* when it doesn't match, instead of exiting 0.
2. Make **"no upstream remote"** and **"no tracked branch"** first-class supported states, not
   errors. On day one in the new repo both are the truth. The script should no-op *loudly* and say
   which precondition is absent — which is exactly what the `.WIP` handoff asks for on the other path.
3. Status file becomes `status/<tracked-branch>.md`, not `status/main.md`.
4. The `Main/` worktree name is a convention, not a requirement — keep it as a default, but don't
   assume directory name equals branch name.

## Affected sites (from the sweep, 2026-08-16)

- `scripts/sync-main-session-start.sh:5` — hardcoded `SYNC_WORKTREE`
- `scripts/sync-main-status.sh:12` — hardcoded status path; also `:9` usage comment
- `scripts/sync-main-once.sh:12` — usage comment
- `scripts/sync-main-watch.sh` — inherits the same assumptions
- `.claude/skills/s-sync-main/SKILL.md` — **6 absolute paths, one in the `allowed-tools:`
  frontmatter.** That one is load-bearing, not cosmetic: grants are matched literally, so a
  relative path there does not work. Two ways out — per-container skill copies, or a wrapper
  script at a fixed relative location with the grant on the wrapper. I lean wrapper (N pinned
  grants → 1), and note the checkpoint work already needed an on-disk wrapper for a different
  reason (the `pgrep` self-match, per CURRENT.md 2026-08-15/16). Your call — it's your spec.

## Sequencing note, not a request

This is **not** blocking the new repo. Dean gated the whole bootstrap on the new plans tooling and
atomic-step rules completing (they're WIP), and separately D5 of my doc defers `s-sync-main` off day
one — with a cleaner reason than "too many absolute paths": *there is nothing for it to sync yet.*

The useful ordering, if it helps you schedule: generalizing it **here**, where a real `main` exists
to test against, is strictly better than generalizing it in a repo that has no tracked branch. This
workspace can be the first consumer of the generalized version rather than the reference
implementation of the old one.

## Not mine to do

I have not touched any script, the spec, or the `.WIP` handoff. My doc is DRAFT and uncommitted.
If you want the sweep re-run or the full findings, the doc's § 2.2a has this in detail and § 8 lists
exactly what was read.
