#!/usr/bin/env bash
# sync-main-once.sh — one-shot fetch / ff-only-merge / push of the tracked branch from upstream.
#
# The "sync" mode of the s-sync-main skill. Same work the watcher does on a SHA
# change, minus the polling loop — so the two are interchangeable and idempotent.
#
# Deliberately self-contained: it cds to the tracked-branch worktree itself, so callers
# never need a `cd` in the session shell (a bare `cd` would persist across every
# later Bash call and silently relocate subsequent git writes to the wrong
# worktree). Run it in the background; it does not need a model in the loop.
#
# WORKTREE/TRACKED_BRANCH/UPSTREAM_REMOTE come from session/sync-main.conf, not hardcoded here —
# see planning/sync-watchers-spec.md S5. An empty UPSTREAM_REMOTE is a supported "not configured
# yet" state, not an error: this script no-ops loudly rather than fetching from nothing.
#
# Usage:  bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-once.sh
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLANS="$(cd "$here/.." && pwd)"

# shellcheck source=lib/sync-main-config.sh
. "$here/lib/sync-main-config.sh"
sync_main_load_config "$PLANS/session/sync-main.conf" || exit 1

MAIN_WORKTREE="$WORKTREE"
STATUS="$PLANS/session/status/$TRACKED_BRANCH.md"

if [ -z "$UPSTREAM_REMOTE" ]; then
  echo "no upstream remote configured for '$TRACKED_BRANCH' -- nothing to sync from yet, exiting"
  exit 0
fi

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
    echo "$TRACKED_BRANCH at $(basename "$MAIN_WORKTREE") worktree ; tip $tip"
    echo ""
    echo "## Recent commits"
    echo "$shortlog" | sed 's/^/- /'
    echo ""
    echo "## Notes"
    echo "$notes"
  } > "$STATUS"
}

branch=$(git branch --show-current)
if [ "$branch" != "$TRACKED_BRANCH" ]; then
  echo "FAIL: $MAIN_WORKTREE is on '$branch', not '$TRACKED_BRANCH' — refusing to sync"
  write_status "aborted" "one-shot sync aborted: worktree on '$branch', not '$TRACKED_BRANCH'"
  exit 1
fi

before=$(git rev-parse --short=8 HEAD)

if ! git fetch "$UPSTREAM_REMOTE" >/tmp/main-sync-once-fetch.log 2>&1; then
  echo "FAIL: git fetch $UPSTREAM_REMOTE failed — see /tmp/main-sync-once-fetch.log"
  write_status "failed" "one-shot: fetch $UPSTREAM_REMOTE FAILED"
  exit 1
fi

# --ff-only: never create a merge commit on the tracked branch. A non-fast-forward here means
# it has diverged from upstream and needs a human, so stop before the push.
if ! git merge --ff-only "$UPSTREAM_REMOTE/$TRACKED_BRANCH" >/tmp/main-sync-once-merge.log 2>&1; then
  echo "FAIL: merge --ff-only failed ($TRACKED_BRANCH has diverged from $UPSTREAM_REMOTE/$TRACKED_BRANCH) — NOT pushing. See /tmp/main-sync-once-merge.log"
  write_status "failed" "one-shot: ff-only merge FAILED — $TRACKED_BRANCH diverged, push skipped"
  exit 1
fi

after=$(git rev-parse --short=8 HEAD)

if [ "$before" = "$after" ]; then
  write_status "idle" "one-shot: already up to date"
  echo "already up to date: $TRACKED_BRANCH at $after, nothing fetched, no push needed"
  exit 0
fi

last_sync=$(date -Iseconds)
# Capture rc on its own line: `if [ $? -eq 0 ]` after an assignment would test
# the assignment's status (always 0), not the push's.
pushout=$(git push origin "$TRACKED_BRANCH" 2>&1)
pushrc=$?
if [ "$pushrc" -eq 0 ]; then
  write_status "idle" "one-shot: push origin $TRACKED_BRANCH OK"
  echo "$TRACKED_BRANCH synced: $before -> $after, pushed to origin"
else
  write_status "idle" "one-shot: push origin $TRACKED_BRANCH FAILED — $pushout"
  echo "WARN: merged $before -> $after but push to origin FAILED — $pushout"
  exit 1
fi