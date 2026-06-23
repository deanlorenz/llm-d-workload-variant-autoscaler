---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. Spawns a background subagent in the Main worktree — no interaction if the merge is fast-forward-able. Invoke with /s-sync-main.
allowed-tools: Bash(cd:*), Agent
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`. The work runs
in a background subagent started in the Main worktree, which carries the pre-approved
permissions for these exact git commands.

Use the `cd + Agent` pattern: one `cd` call, then `Agent` immediately — no Bash between them.

---

## Step 1 — cd into Main worktree

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main
```

---

## Step 2 — Spawn background subagent

Call `Agent` with `run_in_background: true` and this brief:

> You are starting in `/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main`
> on branch `main`. Verify, then sync:
>
> ```bash
> pwd && git branch --show-current
> git fetch upstream
> git merge --ff-only upstream/main
> git push origin main
> ```
>
> If `git merge --ff-only` fails, stop and report — do not push.
> Report what was fetched (new commits or "already up to date") and whether the push succeeded.

---

## Step 3 — Restore CWD and report

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
```

Tell Dean the sync agent is running in the background.
