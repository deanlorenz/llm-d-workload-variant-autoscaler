#!/bin/bash
# Sync local main from upstream and push to origin.
# Always runs inside the Main worktree — no arguments needed.
set -euo pipefail

MAIN=/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main

if [ ! -d "$MAIN" ]; then
    echo "ERROR: Main worktree not found at $MAIN" >&2
    exit 1
fi

cd "$MAIN"
echo "CWD:    $(pwd)"
echo "Branch: $(git branch --show-current)"

git fetch upstream

NEW=$(git log --oneline HEAD..upstream/main)
git merge --ff-only upstream/main

if [ -n "$NEW" ]; then
    echo "New commits merged:"
    echo "$NEW"
else
    echo "Already up to date."
fi

git push origin main
echo "Push to origin/main: OK"
