# Github actions

### convention: github-actions-no-action-without-confirmation
description: No GitHub-writing action (comment, PR, issue, reviewer request) runs without Dean's explicit instruction for that specific action.
scope: anyone about to take a GitHub-visible action
trigger: about to comment on, create, or otherwise write to GitHub
status: active
origin: session/CONVENTIONS.md § No GitHub actions without explicit confirmation (C40)

**No GitHub actions without explicit confirmation.**
Never post a comment on a PR or issue, create a PR, create an issue, request reviewers, or take
any other GitHub action that is visible to others without Dean's explicit instruction for that
specific action. Summarise the proposed text and wait for approval before running any `gh` command
that writes to GitHub.

### convention: github-actions-pr-edit-workaround
description: gh pr edit fails on this repo with a projects-classic GraphQL deprecation error; use gh api -X PATCH on pulls/<n> instead for body/title/draft edits.
scope: anyone editing a PR's body/title/draft on this repo
trigger: about to run gh pr edit
status: active
origin: feedback_gh_pr_edit_workaround.md

`gh pr edit <n> --body-file ...` against this repo exits non-zero with
`GraphQL: Projects (classic) is being deprecated ... (repository.pullRequest.projectCards)` — the
repo still has projectCards on PRs (or did at some point), and `gh pr edit`'s GraphQL query fans
out into that subgraph; the deprecation message lands in `errors[]` and `gh` treats any `errors[]`
entry as fatal, even though the mutation itself is unrelated to projects. The body update does
**not** apply. Use the REST API directly instead, which avoids GraphQL entirely:

```
jq -Rs '{body: .}' /tmp/pr<n>-body.md > /tmp/pr<n>-payload.json
gh api -X PATCH repos/llm-d/llm-d-workload-variant-autoscaler/pulls/<n> --input /tmp/pr<n>-payload.json
```

Same approach for `--title` (`{title: "..."}` in the JSON) or `--draft` (`{draft: true}`).
Read-only `gh pr view` is unaffected — it doesn't mutate. If `gh pr edit` ever stops failing on
this repo (the deprecation lands or the projectCards reference is removed), the REST workaround
still works; this note can be dropped then. Until then, default to REST PATCH for any PR
body/title/draft edit on this repo. This is a *how*, not a *whether* — the no-GitHub-action-
without-confirmation rule above still governs whether the edit happens at all.

### convention: github-actions-pr-assignee
description: Always ask Dean who to assign a new PR to, before or immediately after creating it; never leave it unassigned or assume.
scope: anyone creating a PR
trigger: about to run gh pr create, or just ran it
status: active
origin: feedback_pr_creation_checklist.md

When creating a PR, always ask Dean who to assign it to — do not leave it unassigned and do not
assume. Dean assigns PRs to specific reviewers based on context (area ownership, availability,
relationship); this is not something to infer. After proposing the PR text and before (or
immediately after) running `gh pr create`, ask: "Who should I assign this to?"

### convention: github-actions-check-mergeable-first
description: When a PR's pull_request-triggered CI workflow doesn't dispatch, check mergeable/mergeStateStatus FIRST — a conflicting PR can't build a merge ref, and that looks identical to a dropped webhook.
scope: anyone investigating a PR whose merge-ref CI job hasn't dispatched
trigger: a PR's lint-and-test (or equivalent pull_request-triggered) job is missing or not dispatching
status: active
origin: feedback_pr_workflow_not_dispatching_check_mergeable.md

When a PR's `pull_request`-triggered workflow (e.g. the merge-ref `lint-and-test` job) does not
dispatch — while `pull_request_target` jobs (e.g. signed-commits) still run — the **first**
diagnostic is `gh pr view <n> --json mergeable,mergeStateStatus,state` and `gh pr checks <n>`,
run before proposing any re-trigger (reopen, empty commit, amend). GitHub tests the PR's merge
ref; if the PR is `CONFLICTING`/`DIRTY` there is no clean merge commit to check out, so GitHub
silently skips the merge-ref workflow — which looks identical to a dropped webhook but is not.
If `CONFLICTING`/`DIRTY`, the fix is a rebase onto the current base plus conflict resolution, not
a re-trigger. Also re-fetch upstream and check whether the base branch moved — a set of PRs
against a moving main is the common cause (e.g. one PR in a stack merging and rewriting a file
another PR in the same stack also touches).
