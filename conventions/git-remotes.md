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
