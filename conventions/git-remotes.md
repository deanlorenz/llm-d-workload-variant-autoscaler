# Git remotes

### convention: git-remotes-merge-upstream-main
description: Fast-forwarding main to upstream always uses a fast-forward-only merge; never a merge commit for this operation.
scope: anyone syncing main from upstream
trigger: merging upstream/main into local main
status: active
origin: session/CONVENTIONS.md § Merging upstream into main (C43)

**Merging upstream into main.**
Always use `git merge --ff-only upstream/main` when fast-forwarding main to upstream. Push to
origin after. Never use a merge commit for this operation.

### convention: git-remotes-origin-branch-required
description: Every code branch (including plans) must exist on origin; push a new branch with upstream tracking as part of initial setup, subject to the no-push-without-confirmation rule.
scope: anyone creating a new code branch
trigger: creating a new branch intended to become a PR or join the active PR stack
status: active
origin: session/CONVENTIONS.md § Every code branch has a matching origin branch (C45)

**Every code branch has a matching origin branch.**
Code branches — any branch where development happens, typically for a PR (including stacked or
deferred PRs) — must exist on origin (deanlorenz/llm-d-workload-variant-autoscaler). When
creating a new code branch, push it to origin with upstream tracking as part of initial setup:

```
git -C <worktree> push -u origin <new-branch>
```

Subject to the "No push without explicit confirmation" rule above — propose the push, get
confirmation, then run it. The `plans` branch counts as a code branch for this purpose.
Throwaway local experiments are fine local-only, but anything that will become a PR or is part
of the active PR stack must have an origin branch from the start.

### convention: git-remotes-never-push-upstream
description: No branch, including main, ever pushes to the upstream remote -- it is pull-only; configure pushDefault=origin so a stray push can't reach it.
scope: anyone pushing on this repo
trigger: before any git push, especially from a branch tracking an upstream remote
status: active
origin: feedback_git_remote_rules.md sec Rule 1

**Never push to `upstream`.** No branch, including `main`, ever pushes to the `upstream` remote
(the llm-d project). `upstream` is a pull-only remote — Dean is a contributor, not a maintainer
with push access on default branches, and contributions reach upstream only via PRs. `main`
flows: upstream/main → local `main` (ff-only merge) → push to origin/main. Configure
`remote.pushDefault = origin` in the bare repo so every `git push` defaults to origin regardless
of the branch's upstream tracking — `main` still tracks upstream/main for fetch/ff-merge, but
pushes go to origin. Never run `git push upstream <anything>`; check the push target before any
push.

### convention: git-remotes-mirror-third-party
description: Third-party remotes (e.g. a collaborator's fork) are read-only -- never push to them; mirror any branch worth keeping into our own fork under a mirror prefix instead.
scope: anyone working with a third-party remote/fork
trigger: wanting to keep or build on a branch that lives on a third-party remote
status: active
origin: feedback_git_remote_rules.md sec Rule 1b

**Third-party remotes are read-only, and that includes a collaborator's fork.** Never work on
the third-party branch directly and never make it a push target. The pattern for keeping a
third-party branch: **mirror it into our own fork** under a mirror/ prefix, never work on the
mirror, and branch off it onto our own fork branch if anything needs to change. Belt and braces:
`git remote set-url --push <remote> "READ-ONLY-...-DO-NOT-PUSH"` so a push fails immediately and
the intent is visible in `git remote -v` (the resulting error is a generic "Could not read from
remote repository" — the sentinel string in `git remote -v` is where the reason lives, not the
error), plus `git config remote.pushDefault origin` in that clone. Push a mirror straight from
the remote-tracking ref, no local branch needed:
`git push origin refs/remotes/<remote>/<branch>:refs/heads/mirror/<name>`.

### convention: git-remotes-archive-not-delete
description: Never force-remove a branch; archive it instead via the git boidem alias, which tags the tip and pushes the tag before removing the local branch.
scope: anyone about to remove a branch that is absorbed, superseded, or cleaned up
trigger: considering a forced local branch removal or a remote branch delete
status: active
origin: feedback_git_archive_alias.md

Dean's convention is to archive branches, not delete them, preserving history and a recovery
point while keeping the branch list clean. Alias: `git boidem <branch>` — creates tag
archive/<branch> at the branch tip, deletes the local branch, and pushes the tag to origin.
Any time a branch is done (absorbed, superseded, or cleaned up), propose `git boidem <branch>`
instead of a plain delete. Applies to every branch, including scratch/backup-style ones.
