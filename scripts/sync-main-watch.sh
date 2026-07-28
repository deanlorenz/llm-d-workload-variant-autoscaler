#!/usr/bin/env bash
# Background watcher for the s-sync-main skill's "watch mode".
# Polls upstream/main cheaply (git ls-remote — ref query only, no object
# transfer) and only does the real fetch/ff-merge/push when the SHA actually
# changes. Meant to be run via the Monitor tool with persistent:true, not
# invoked directly by a human.
set -uo pipefail

MAIN_WORKTREE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../Main" && pwd)"
STATUS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/session/status/main.md"
POLL_SECONDS=60
STALE_AFTER_SECONDS=150 # ~2.5x poll interval; used by callers checking last_check, not by this script

cd "$MAIN_WORKTREE"
last=$(git rev-parse upstream/main 2>/dev/null || echo "")
last_sync="never"

write_status() {
  local step="$1" notes="$2"
  local tip shortlog
  tip=$(git rev-parse --short=8 HEAD)
  shortlog=$(git log --oneline -5)
  {
    echo "last_check: $(date -Iseconds)"
    echo "last_sync: $last_sync"
    echo "watcher_pid: $$"
    echo "state: watching"
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

cleanup() {
  write_status "stopped" "watcher exited (pid $$)"
}
trap cleanup EXIT

write_status "idle" "watcher started"
echo "sync-main watcher started (pid $$), polling upstream/main every ${POLL_SECONDS}s"

while true; do
  remote=$(git ls-remote upstream main 2>/dev/null | awk '{print $1}')
  if [ -n "$remote" ] && [ "$remote" != "$last" ]; then
    if git fetch upstream >/tmp/main-sync-fetch.log 2>&1 && git merge --ff-only upstream/main >/tmp/main-sync-merge.log 2>&1; then
      pushout=$(git push origin main 2>&1)
      pushrc=$?
      prevshort=${last:0:8}
      tip=$(git rev-parse --short=8 HEAD)
      last_sync=$(date -Iseconds)
      if [ "$pushrc" -eq 0 ]; then
        write_status "idle" "push origin main: OK"
        echo "main synced: ${prevshort:-none} -> $tip, pushed to origin"
      else
        write_status "idle" "push origin main: FAILED — $pushout"
        echo "WARN: merged to $tip but push to origin FAILED — $pushout"
      fi
    else
      write_status "idle" "fetch/ff-only-merge FAILED for new-sha=${remote:0:8}"
      echo "WARN: fetch/ff-only-merge failed for upstream/main new-sha=${remote:0:8} — manual intervention needed (see /tmp/main-sync-fetch.log, /tmp/main-sync-merge.log)"
    fi
    last=$remote
  else
    write_status "idle" "no change"
  fi
  sleep "$POLL_SECONDS"
done
