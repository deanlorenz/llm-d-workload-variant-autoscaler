---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. Spawns a background subagent — no interaction if the merge is fast-forward-able. Invoke with /s-sync-main.
allowed-tools: Bash(cd:*), Bash(pwd:*), Agent
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`. The work runs
in a background subagent so the planning session stays free.

`EnterWorktree` is not available in subagents spawned from `plans/` — use the approved
`cd + Agent` pattern: one `cd` call, then `Agent` immediately after, no Bash between them.

---

## Step 1 — cd into Main worktree

In a single Bash call:

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main
```

No other Bash calls before Step 2. The subagent inherits this CWD.

---

## Step 2 — Spawn background subagent

Immediately after the `cd`, call `Agent` with `run_in_background: true` and this brief:

> You are starting in `/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main`
> on branch `main`. Verify first:
>
> ```bash
> pwd && git branch --show-current
> ```
>
> Confirm CWD is `Main/` and branch is `main`. If either check fails, stop and report —
> do not touch any files.
>
> Then run in order:
>
> ```bash
> git fetch upstream
> git merge --ff-only upstream/main
> git push origin main
> ```
>
> Rules:
> - If `git merge --ff-only` fails (not fast-forward-able), stop — report the error,
>   do not push, do not force anything.
> - If all three succeed, report: which new commits were fetched (or "already up to
>   date"), and that the push succeeded.
> - No user interaction. Write scope: this worktree only.

---

## Step 3 — Restore CWD

After the Agent call, restore the session CWD:

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
```

Then tell Dean the sync agent is running in the background.
