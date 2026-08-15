#!/usr/bin/env bash
# Keeps local main fast-forwarded to upstream/main. Polls with git ls-remote (ref query only)
# and does the real fetch/ff-merge/push only when the SHA moves. Started by the sync session,
# not run by hand. Guards: planning/atomic-step-protocol-design-addendum-7.md.
#
# Usage: sync-main-watch.sh --origin-pid <pid>
#   --origin-pid   pid of the Claude session that started this watcher. Required.
#                   Checked with `kill -0` each poll; when it is gone, sync once more and exit.
#
# Linux only: uses `date -r <file>` (GNU coreutils) for mtime. BSD/macOS `date -r` takes seconds.
set -uo pipefail

MAIN_WORKTREE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../Main" && pwd)"
STATUS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/session/status/main.md"
POLL_SECONDS=60
STALE_AFTER_SECONDS=150 # ~2.5x poll interval; used by callers checking last_check, not by this script
origin_pid=""

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --origin-pid) origin_pid="${2:-}"; [ -n "$origin_pid" ] || die "--origin-pid needs a value"; shift 2 ;;
    -h|--help)    sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "unknown argument: $1" ;;
  esac
done
[ -n "$origin_pid" ] || die "--origin-pid is required -- see -h"
case "$origin_pid" in ''|*[!0-9]*) die "--origin-pid must be a numeric pid" ;; esac

# Single-instance guards.
# Guard 1 (mkdir, atomic): are two instances starting at the same instant?
# Guard 2 (pgrep): is a fully-started watcher already running?
# Neither covers the other's window. Held only during startup, removed inline.
dedup_dir="${TMPDIR:-/tmp}/sync-main-watch.dedup.$origin_pid"

# Reclaim a guard abandoned by a process that died before its own rmdir (SIGKILL, OOM, sleep).
# 1 week: far longer than any startup, so age alone is a safe abandonment signal.
if [ -d "$dedup_dir" ] && [ "$(( $(date +%s) - $(date -r "$dedup_dir" +%s) ))" -gt 604800 ]; then
  rmdir "$dedup_dir" 2>/dev/null
fi

# Exit 0 when standing down: the caller starts this speculatively, so "already running" is success.
mkdir "$dedup_dir" 2>/dev/null || {
  echo "sync-main watcher already starting for --origin-pid $origin_pid -- this instance is exiting"
  exit 0
}

# $$ must be excluded: pgrep -f matches this script's own argv, which contains the pattern.
if pgrep -f "sync-main-watch[.]sh .*--origin-pid $origin_pid" 2>/dev/null | grep -qv "^$$\$"; then
  echo "sync-main watcher already running for --origin-pid $origin_pid -- this instance is exiting"
  rmdir "$dedup_dir" 2>/dev/null
  exit 0
fi
rmdir "$dedup_dir" 2>/dev/null   # startup done; guard no longer needed

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

sync_pass() {
  remote=$(git ls-remote upstream main 2>/dev/null | awk '{print $1}')
  # Compare against local main, not the upstream/main tracking ref or a cached baseline, so
  # "local main == live upstream tip" self-corrects whenever main lags for any reason.
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
}

write_status "idle" "watcher started"
echo "sync-main watcher started (pid $$), polling upstream/main every ${POLL_SECONDS}s"

while true; do
  # Origin gone: sync once more, THEN exit. write_status runs after, so the file says "stopped".
  if ! kill -0 "$origin_pid" 2>/dev/null; then
    echo "sync-main watcher (pid $$) exiting: origin pid $origin_pid is gone -- final sync first"
    sync_pass
    write_status "stopped" "origin pid $origin_pid is gone — ran final sync, exiting"
    exit 0
  fi
  sync_pass
  sleep "$POLL_SECONDS"
done
