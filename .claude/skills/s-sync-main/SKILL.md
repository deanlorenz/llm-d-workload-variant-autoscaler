---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. Spawns a background subagent — no interaction if the merge is fast-forward-able. Invoke with /s-sync-main.
allowed-tools: Agent
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`. The work runs
in a background subagent so the planning session stays free.

The script `plans/scripts/sync-main.sh` is pre-approved in project settings — no
per-command prompts. The subagent just calls it.

---

## Step 1 — Spawn background subagent

Call `Agent` with `run_in_background: true` and this brief:

> Run this script and report its output:
>
> ```bash
> bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main.sh
> ```
>
> If the script exits non-zero (merge not fast-forward-able, push rejected, etc.),
> report the error. No other actions needed.

---

## Step 2 — Report

Tell Dean the sync agent is running in the background.
