#!/usr/bin/env bash
# Keeps the tracked branch fast-forwarded from the configured upstream remote. Polls with
# git ls-remote (ref query only) and does the real fetch/ff-merge/push only when the SHA moves.
# Started by the sync session, not run by hand.
#
# WORKTREE/TRACKED_BRANCH/UPSTREAM_REMOTE come from session/sync-main.conf, not hardcoded here --
# see planning/sync-watchers-spec.md S5. An empty UPSTREAM_REMOTE is a supported "not configured
# yet" state: the watcher still runs (status/guard/kill-switch all still make sense with nothing to
# sync), it just never has a SHA change to act on, so sync_pass becomes a permanent no-op rather
# than an error.
#
# Two independent mechanisms, deliberately kept separate (see lib/single-instance-guard.sh):
#   * single-instance guard -- keyed on the fixed role constant "sync", because this watcher
#     belongs to the sync ROLE, not to any one Claude session. Whichever session currently acts as
#     sync runs it, and a later one must recognize an instance an earlier one started.
#   * kill-switch -- --origin-pid plus `kill -0` each poll: is the session that started this
#     instance still alive. Nothing to do with the guard's identity.
#
# Usage: sync-main-watch.sh --origin-pid <pid>
#   --origin-pid   pid of the Claude session that started this watcher. Required (this script has
#                   no --once escape). Checked with `kill -0` each poll; when it is gone, sync once
#                   more and exit.
#
# Linux only: uses `date -r <file>` (GNU coreutils) for mtime. BSD/macOS `date -r` takes seconds.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLANS="$(cd "$here/.." && pwd)"

# shellcheck source=lib/sync-main-config.sh
. "$here/lib/sync-main-config.sh"
sync_main_load_config "$PLANS/session/sync-main.conf" || exit 1

MAIN_WORKTREE="$WORKTREE"
STATUS="$PLANS/session/status/$TRACKED_BRANCH.md"
POLL_SECONDS=60
STALE_AFTER_SECONDS=150 # ~2.5x poll interval; used by callers checking last_check, not by this script
origin_pid=""
guard_lib="$here/lib/single-instance-guard.sh"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --origin-pid) origin_pid="${2:-}"; [ -n "$origin_pid" ] || die "--origin-pid needs a value"; shift 2 ;;
    -h|--help)    sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "unknown argument: $1" ;;
  esac
done
[ -n "$origin_pid" ] || die "--origin-pid is required -- see -h"
case "$origin_pid" in ''|*[!0-9]*) die "--origin-pid must be a numeric pid" ;; esac

[ -r "$guard_lib" ] || die "cannot read $guard_lib"
# shellcheck source=lib/single-instance-guard.sh
. "$guard_lib"

# At most one watcher system-wide, keyed on the sync role rather than on --origin-pid: a pid-keyed
# guard made an instance started by one sync session invisible to the next one.
# Exit 0 when standing down: the caller starts this speculatively, so "already running" is success.
guard_acquire "sync-main-watch" "" "sync"
case $? in
  0) # Momentary by design: release now, before becoming the watcher, not on exit.
     guard_release "sync-main-watch" "sync" ;;
  1) echo "sync-main watcher already starting for the sync role -- this instance is exiting"
     exit 0 ;;
  2) echo "sync-main watcher already running for the sync role -- this instance is exiting"
     exit 0 ;;
  *) die "single-instance guard rejected its arguments -- see stderr above" ;;
esac

cd "$MAIN_WORKTREE"
last_sync="never"

# write_status <state> <step> <notes>
#
# <state> is the watcher's own liveness -- "watching" while the poll loop is alive, "stopped" once
# it is not. It used to be hardcoded to "watching" here while "stopped" was passed as <step> and
# landed in current_step, so the file claimed `state: watching` after every exit, clean or crashed.
# That is not cosmetic: sync-main-session-start.sh gates its auto-start success report on
# `grep -q '^state: watching'`, so it reported a healthy watcher for one that had already died.
#
# Still not a liveness proof on its own: an EXIT trap cannot run after SIGKILL, so a hard-killed
# watcher leaves the last line it wrote. Readers must keep pairing state with last_check's age --
# which sync-main-status.sh already does against its 150s threshold.
write_status() {
  local state="$1" step="$2" notes="$3"
  local tip shortlog
  tip=$(git rev-parse --short=8 HEAD)
  shortlog=$(git log --oneline -5)
  {
    echo "last_check: $(date -Iseconds)"
    echo "last_sync: $last_sync"
    echo "watcher_pid: $$"
    echo "state: $state"
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

cleanup() {
  write_status "stopped" "stopped" "watcher exited (pid $$)"
}
trap cleanup EXIT

sync_pass() {
  if [ -z "$UPSTREAM_REMOTE" ]; then
    write_status "watching" "idle" "no upstream remote configured for '$TRACKED_BRANCH' -- nothing to sync from"
    return 0
  fi
  remote=$(git ls-remote "$UPSTREAM_REMOTE" "$TRACKED_BRANCH" 2>/dev/null | awk '{print $1}')
  # Compare against the local tracked branch, not the remote-tracking ref or a cached baseline, so
  # "local == live upstream tip" self-corrects whenever it lags for any reason.
  localtip=$(git rev-parse "$TRACKED_BRANCH" 2>/dev/null || echo "")
  if [ -n "$remote" ] && [ "$remote" != "$localtip" ]; then
    if git fetch "$UPSTREAM_REMOTE" >/tmp/main-sync-fetch.log 2>&1 && git merge --ff-only "$UPSTREAM_REMOTE/$TRACKED_BRANCH" >/tmp/main-sync-merge.log 2>&1; then
      pushout=$(git push origin "$TRACKED_BRANCH" 2>&1)
      pushrc=$?
      prevshort=${localtip:0:8}
      tip=$(git rev-parse --short=8 HEAD)
      last_sync=$(date -Iseconds)
      if [ "$pushrc" -eq 0 ]; then
        write_status "watching" "idle" "push origin $TRACKED_BRANCH: OK"
        echo "$TRACKED_BRANCH synced: ${prevshort:-none} -> $tip, pushed to origin"
      else
        write_status "watching" "idle" "push origin $TRACKED_BRANCH: FAILED — $pushout"
        echo "WARN: merged to $tip but push to origin FAILED — $pushout"
      fi
    else
      write_status "watching" "idle" "fetch/ff-only-merge FAILED for new-sha=${remote:0:8}"
      echo "WARN: fetch/ff-only-merge failed for $UPSTREAM_REMOTE/$TRACKED_BRANCH new-sha=${remote:0:8} — manual intervention needed (see /tmp/main-sync-fetch.log, /tmp/main-sync-merge.log)"
    fi
  else
    write_status "watching" "idle" "no change"
  fi
}

write_status "watching" "idle" "watcher started"
if [ -n "$UPSTREAM_REMOTE" ]; then
  echo "sync-main watcher started (pid $$), polling $UPSTREAM_REMOTE/$TRACKED_BRANCH every ${POLL_SECONDS}s"
else
  echo "sync-main watcher started (pid $$), no upstream remote configured -- polling loop is a permanent no-op until sync-main.conf sets one"
fi

while true; do
  # Origin gone: sync once more, THEN exit. write_status runs after, so the file says "stopped".
  if ! kill -0 "$origin_pid" 2>/dev/null; then
    echo "sync-main watcher (pid $$) exiting: origin pid $origin_pid is gone -- final sync first"
    sync_pass
    write_status "stopped" "stopped" "origin pid $origin_pid is gone — ran final sync, exiting"
    exit 0
  fi
  sync_pass
  sleep "$POLL_SECONDS"
done
