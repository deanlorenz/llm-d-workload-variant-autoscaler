---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. Runs claude -p in the Main worktree as a background Bash job — no interaction. Invoke with /s-sync-main.
allowed-tools: Bash(cd:*), Bash(claude -p:*)
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`.

Uses `claude -p` with `--allowed-tools` so the subprocess starts in the Main worktree
and has exactly the git commands it needs — no settings files required.

---

## Step 1 — cd into Main worktree

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main
```

---

## Step 2 — Run claude subprocess (blocking)

Run the following as a normal Bash call (not background):

```bash
claude -p "Run each as a separate Bash call in order: (1) git branch --show-current (2) git fetch upstream (3) git merge --ff-only upstream/main — if this fails stop and report, do not run step 4 (4) git push origin main. Report what was fetched (new commits or already up to date) and whether the push succeeded." --allowed-tools "Bash(git branch --show-current),Bash(git fetch upstream),Bash(git merge --ff-only upstream/main),Bash(git push origin main)" --no-session-persistence
```

---

## Step 3 — Report

Report the output from Step 2 to Dean.
