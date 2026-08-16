#!/usr/bin/env bash
# Background watcher for pending sync__*.md handoffs against CURRENT.md.
#
# This watcher does NOT apply handoffs itself — folding prose into CURRENT.md
# needs judgment (which section, how to phrase it, what to prune), so that step
# stays with the model. What this script does mechanically:
#
#   1. Poll for session/handoffs/sync__*.md files.
#   2. When any exist, check whether session/CURRENT.md has moved since the
#      last commit THIS sync session made to it (recorded in the status file
#      below, updated by the model after every /s-sync-current run — see
#      .claude/skills/s-sync-current/SKILL.md Step 7).
#   3. Emit exactly one of two distinct stdout lines, meant to be read by the
#      Monitor tool so the model gets notified and can act:
#        - unchanged  -> safe to auto-run /s-sync-current, no need to ask Dean
#        - changed    -> someone else committed to CURRENT.md since the last
#                         known-good tip (a different session, possibly another
#                         sync session running concurrently) — RAISE, do not
#                         auto-sync. The model surfaces this to Dean and lets
#                         him decide; the watcher never resolves it on its own.
#
# Single-instance guard migrated 2026-08-16 to lib/single-instance-guard.sh,
# keyed on the fixed role constant "sync" -- same reasoning as
# sync-main-watch.sh/tick-shared-scan.sh: this watcher belongs to whichever
# session currently acts as sync, not to one Claude session or pid. Replaces
# the previous flock (this was the one script in the family never migrated
# in the earlier guard-rework pass). Kill-switch also migrated from the old
# "any VS Code/Claude process anywhere in this WSL instance" anchor_alive()
# check to --origin-pid + kill -0, matching every other script in this
# family -- the old anchor was found (2026-08-16) to be a real behavioral
# difference, not just stale wording like sync-main-watch.sh's comment was:
# this script had NO --origin-pid at all, so it actually self-exited on ANY
# Claude/VS Code process disappearing, not the one that started it. Meant to
# be run via the Monitor tool with persistent:true, not invoked directly by
# a human.
#
# Note (Dean, 2026-08-16): this 30s poll loop is exactly the "bad monitor"
# shape flagged in atomic-step-protocol-design-addendum-11.md -- its own
# per-pass work is cheap shell (ls, git log), no model call, so it is not a
# live token-budget violation, but it is the concrete example that rule was
# written against. Left unchanged here (out of scope for this migration);
# worth revisiting if addendum-11's "no general bound yet" gap is ever closed.
#
# Usage: sync-current-watch.sh --origin-pid <pid>
#   --origin-pid   pid of the Claude session that started this watcher. Required
#                   (no --once escape, matching sync-main-watch.sh). Checked with
#                   `kill -0` each poll; when it is gone, this watcher exits.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLANS="$(cd "$here/.." && pwd)"
STATUS="$PLANS/session/status/sync-current-watch.md"
POLL_SECONDS=30
origin_pid=""
guard_lib="$here/lib/single-instance-guard.sh"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --origin-pid) origin_pid="${2:-}"; [ -n "$origin_pid" ] || die "--origin-pid needs a value"; shift 2 ;;
    -h|--help)    sed -n '2,42p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "unknown argument: $1" ;;
  esac
done
[ -n "$origin_pid" ] || die "--origin-pid is required -- see -h"
case "$origin_pid" in ''|*[!0-9]*) die "--origin-pid must be a numeric pid" ;; esac

cd "$PLANS" || { echo "FAIL: cannot cd to $PLANS"; exit 1; }

[ -r "$guard_lib" ] || die "cannot read $guard_lib"
# shellcheck source=lib/single-instance-guard.sh
. "$guard_lib"

guard_acquire "sync-current-watch" "" "sync"
case $? in
  0) # Momentary by design: release now, before becoming the watcher, not on exit.
     guard_release "sync-current-watch" "sync" ;;
  1) echo "sync-current watcher already starting for the sync role -- this instance is exiting"
     exit 0 ;;
  2) echo "sync-current watcher already running for the sync role -- this instance is exiting"
     exit 0 ;;
  *) die "single-instance guard rejected its arguments -- see stderr above" ;;
esac

# Baseline: the last commit that touched CURRENT.md, as of last known-good
# sync. Seed from the status file if present; otherwise assume the CURRENT tip
# right now is already known-good (first run after this watcher is introduced).
baseline=""
if [ -f "$STATUS" ]; then
  baseline=$(grep -m1 '^last_known_current_sha:' "$STATUS" 2>/dev/null | awk '{print $2}')
fi
if [ -z "$baseline" ]; then
  baseline=$(git log -1 --format=%H -- session/CURRENT.md)
fi

# write_status <state> <step> <notes> <known>
#
# <state> is the watcher's own liveness ("watching" while the poll loop is alive, "stopped" once
# it is not) -- fixed 2026-08-16 to match sync-main-watch.sh's Defect C fix: this function used to
# hardcode "watching" unconditionally, so the file claimed a live watcher after every exit, clean
# or crashed. Still not a liveness proof on its own (an EXIT trap cannot run after SIGKILL) --
# readers should pair state with last_check's age, same caveat as sync-main-watch.sh.
write_status() {
  local state="$1" step="$2" notes="$3" known="$4"
  {
    echo "last_check: $(date -Iseconds)"
    echo "watcher_pid: $$"
    echo "state: $state"
    echo "current_step: $step"
    echo "last_known_current_sha: $known"
    echo ""
    echo "## Notes"
    echo "$notes"
  } > "$STATUS"
}

cleanup() {
  write_status "stopped" "stopped" "watcher exited (pid $$)" "$baseline"
}
trap cleanup EXIT

write_status "watching" "idle" "watcher started, baseline $baseline" "$baseline"
echo "sync-current watcher started (pid $$), baseline $baseline, polling every ${POLL_SECONDS}s"

last_signature=""

while true; do
  if ! kill -0 "$origin_pid" 2>/dev/null; then
    echo "sync-current watcher (pid $$) exiting: origin pid $origin_pid is gone"
    write_status "stopped" "stopped" "origin pid $origin_pid is gone -- exiting" "$baseline"
    exit 0
  fi
  handoffs=$(ls session/handoffs/sync__*.md 2>/dev/null || true)
  count=0
  [ -n "$handoffs" ] && count=$(printf '%s\n' "$handoffs" | grep -c .)

  if [ "$count" -eq 0 ]; then
    write_status "watching" "idle" "no pending sync__ handoffs" "$baseline"
    last_signature=""
    sleep "$POLL_SECONDS"
    continue
  fi

  current_sha=$(git log -1 --format=%H -- session/CURRENT.md 2>/dev/null || echo "")
  names=$(printf '%s\n' "$handoffs" | xargs -n1 basename | sort | tr '\n' ',')

  if [ "$current_sha" = "$baseline" ]; then
    signature="safe:${names}"
    if [ "$signature" != "$last_signature" ]; then
      echo "SAFE: ${count} sync__ handoff(s) pending (${names%,}) and CURRENT.md unchanged since last known sync (tip ${baseline:0:8}) — safe to run /s-sync-current"
      last_signature="$signature"
    fi
    write_status "watching" "waiting-safe" "${count} handoff(s) pending, baseline unchanged" "$baseline"
  else
    signature="conflict:${current_sha}:${names}"
    if [ "$signature" != "$last_signature" ]; then
      echo "CONFLICT: ${count} sync__ handoff(s) pending (${names%,}) but CURRENT.md moved since last known sync — was ${baseline:0:8}, now ${current_sha:0:8}. Another session may be editing/syncing CURRENT.md concurrently. NOT auto-syncing — raise this, do not resolve it here."
      last_signature="$signature"
    fi
    write_status "watching" "alert-conflict" "CURRENT.md moved: ${baseline:0:8} -> ${current_sha:0:8}; ${count} handoff(s) pending" "$baseline"
  fi

  sleep "$POLL_SECONDS"
done
