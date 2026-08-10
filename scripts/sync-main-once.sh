#!/usr/bin/env bash
# sync-main-once.sh — one-shot fetch / ff-only-merge / push of main from upstream.
#
# The "sync" mode of the s-sync-main skill. Same work the watcher does on a SHA
# change, minus the polling loop — so the two are interchangeable and idempotent.
#
# Deliberately self-contained: it cds to the Main worktree itself, so callers
# never need a `cd` in the session shell (a bare `cd` would persist across every
# later Bash call and silently relocate subsequent git writes to the wrong
# worktree). Run it in the background; it does not need a model in the loop.
#
# Usage:  bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-once.sh
set -uo pipefail

MAIN_WORKTREE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../Main" && pwd)"
PLANS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS="$PLANS/session/status/main.md"

cd "$MAIN_WORKTREE" || { echo "FAIL: cannot cd to $MAIN_WORKTREE"; exit 1; }

# Preserve the watcher's last_sync if it is already recorded — a one-shot run
# that finds nothing to do must not erase when the last real sync happened.
prev_sync=$(grep -m1 '^last_sync:' "$STATUS" 2>/dev/null | cut -d' ' -f2- || true)
last_sync="${prev_sync:-never}"

write_status() {
  local step="$1" notes="$2"
  local tip shortlog
  tip=$(git rev-parse --short=8 HEAD)
  shortlog=$(git log --oneline -5)
  {
    echo "last_check: $(date -Iseconds)"
    echo "last_sync: $last_sync"
    echo "watcher_pid: none (one-shot sync)"
    echo "state: one-shot"
    echo "current_step: $step"
    echo ""
    echo "## Branch"
    echo "main at Main worktree ; tip $tip"
    echo ""
    echo "## Recent commits"
    echo "$shortlog" | sed 's/^/- /'
    echo ""
    echo "## Notes"
    echo "$notes"
  } > "$STATUS"
}

branch=$(git branch --show-current)
if [ "$branch" != "main" ]; then
  echo "FAIL: $MAIN_WORKTREE is on '$branch', not 'main' — refusing to sync"
  write_status "aborted" "one-shot sync aborted: worktree on '$branch', not 'main'"
  exit 1
fi

before=$(git rev-parse --short=8 HEAD)

if ! git fetch upstream >/tmp/main-sync-once-fetch.log 2>&1; then
  echo "FAIL: git fetch upstream failed — see /tmp/main-sync-once-fetch.log"
  write_status "failed" "one-shot: fetch upstream FAILED"
  exit 1
fi

# --ff-only: never create a merge commit on main. A non-fast-forward here means
# main has diverged from upstream and needs a human, so stop before the push.
if ! git merge --ff-only upstream/main >/tmp/main-sync-once-merge.log 2>&1; then
  echo "FAIL: merge --ff-only failed (main has diverged from upstream/main) — NOT pushing. See /tmp/main-sync-once-merge.log"
  write_status "failed" "one-shot: ff-only merge FAILED — main diverged, push skipped"
  exit 1
fi

after=$(git rev-parse --short=8 HEAD)

if [ "$before" = "$after" ]; then
  write_status "idle" "one-shot: already up to date"
  echo "already up to date: main at $after, nothing fetched, no push needed"
  exit 0
fi

last_sync=$(date -Iseconds)
# Capture rc on its own line: `if [ $? -eq 0 ]` after an assignment would test
# the assignment's status (always 0), not the push's.
pushout=$(git push origin main 2>&1)
pushrc=$?
if [ "$pushrc" -eq 0 ]; then
  write_status "idle" "one-shot: push origin main OK"
  echo "main synced: $before -> $after, pushed to origin"
else
  write_status "idle" "one-shot: push origin main FAILED — $pushout"
  echo "WARN: merged $before -> $after but push to origin FAILED — $pushout"
  exit 1
fi