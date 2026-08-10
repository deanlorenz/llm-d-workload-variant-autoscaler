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
LOCK="/tmp/sync-main-watch.lock"

# Single-instance guard, enforced HERE rather than in the callers.
#
# Callers previously inferred "is one already running?" from the last_check
# timestamp in the status file. That is racy: the heartbeat is 60s and the
# staleness threshold 150s, so a session starting inside that window reads
# "stale" and launches a duplicate — and because both instances then write the
# same status file, the heartbeat looks healthy and neither notices the other.
# (Observed 2026-08-10: two live watchers, pids 91394 and 124820.)
#
# flock on a dedicated file is authoritative: the lock is held by the kernel for
# as long as the process lives and is released automatically if it is killed, so
# no stale-pidfile cleanup is needed. Every start path — hook auto-start, the
# Monitor tool, a manual run — funnels through this same check.
# Read the incumbent's pid BEFORE opening fd 9: `>` truncates on open, so
# reading after would always report an empty file ("pid unknown").
holder=$(cat "$LOCK" 2>/dev/null | tr -d '[:space:]')
exec 9>>"$LOCK" || { echo "FAIL: cannot open $LOCK"; exit 1; }
if ! flock -n 9; then
  echo "sync-main watcher already running (pid ${holder:-unknown}) — this instance is exiting, not starting a second poller"
  # Exit 0: "one is already running" is success from the caller's point of view,
  # and a nonzero here would surface as a spurious failure in the hook output.
  exit 0
fi
# Record our pid in the lock file for diagnostics.
#
# Do NOT truncate via a second redirection (`: >"$LOCK"`): that opens a separate
# fd with its own offset, so fd 9's subsequent write lands past the truncation
# point and the file reads back empty. Truncate fd 9 in place instead, then write
# through the same fd.
truncate -s 0 /dev/fd/9 2>/dev/null || truncate -s 0 "$LOCK" 2>/dev/null || true
printf '%s\n' "$$" >&9

# NOTE: the EXIT trap that rewrites the status file to "stopped" is installed
# further down, deliberately AFTER this guard — so a duplicate instance exiting
# here never touches the status file of the watcher that actually holds the lock.

cd "$MAIN_WORKTREE"
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
  # Compare the live remote against the branch we actually maintain (local main),
  # not a cached baseline or the upstream/main tracking ref. This keeps the
  # invariant "local main == live upstream tip" self-correcting: if main lags for
  # any reason (tracking ref advanced without a merge, a prior push failed, etc.),
  # the next poll notices and re-syncs.
  localmain=$(git rev-parse main 2>/dev/null || echo "")
  if [ -n "$remote" ] && [ "$remote" != "$localmain" ]; then
    if git fetch upstream >/tmp/main-sync-fetch.log 2>&1 && git merge --ff-only upstream/main >/tmp/main-sync-merge.log 2>&1; then
      pushout=$(git push origin main 2>&1)
      pushrc=$?
      prevshort=${localmain:0:8}
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
  else
    write_status "idle" "no change"
  fi
  sleep "$POLL_SECONDS"
done
