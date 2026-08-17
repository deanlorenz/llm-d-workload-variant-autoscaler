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
