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
# Single-instance guarded by flock, same pattern as sync-main-watch.sh (which
# is where a heartbeat-only guard was found to allow duplicates — see that
# script's comments). Meant to be run via the Monitor tool with persistent:true,
# not invoked directly by a human.
set -uo pipefail

PLANS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS="$PLANS/session/status/sync-current-watch.md"
LOCK="/tmp/sync-current-watch.lock"
POLL_SECONDS=30

# Dead man's switch — same requirement and mechanism as sync-main-watch.sh
# (Dean, 2026-08-12): stateless, restart-on-entry, never left running with
# nobody around to want it. Checked once per poll, cheap (pgrep only).
anchor_alive() {
  pgrep -u "$(id -u)" -f '\.vscode-server/.*code-server' >/dev/null 2>&1 && return 0
  pgrep -x claude >/dev/null 2>&1 && return 0
  return 1
}

cd "$PLANS" || { echo "FAIL: cannot cd to $PLANS"; exit 1; }

holder=$(cat "$LOCK" 2>/dev/null | tr -d '[:space:]')
exec 9>>"$LOCK" || { echo "FAIL: cannot open $LOCK"; exit 1; }
if ! flock -n 9; then
  echo "sync-current watcher already running (pid ${holder:-unknown}) — this instance is exiting, not starting a second poller"
  exit 0
fi
truncate -s 0 /dev/fd/9 2>/dev/null || truncate -s 0 "$LOCK" 2>/dev/null || true
printf '%s\n' "$$" >&9

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

write_status() {
  local step="$1" notes="$2" known="$3"
  {
    echo "last_check: $(date -Iseconds)"
    echo "watcher_pid: $$"
    echo "state: watching"
    echo "current_step: $step"
    echo "last_known_current_sha: $known"
    echo ""
    echo "## Notes"
    echo "$notes"
  } > "$STATUS"
}

cleanup() {
  write_status "stopped" "watcher exited (pid $$)" "$baseline"
}
trap cleanup EXIT

write_status "idle" "watcher started, baseline $baseline" "$baseline"
echo "sync-current watcher started (pid $$), baseline $baseline, polling every ${POLL_SECONDS}s"

last_signature=""

while true; do
  if ! anchor_alive; then
    write_status "stopped" "no VS Code / Claude anchor process found — self-exiting (stateless by design, not a crash)" "$baseline"
    echo "sync-current watcher (pid $$) exiting: no VS Code or Claude process left to run for"
    exit 0
  fi
  handoffs=$(ls session/handoffs/sync__*.md 2>/dev/null || true)
  count=0
  [ -n "$handoffs" ] && count=$(printf '%s\n' "$handoffs" | grep -c .)

  if [ "$count" -eq 0 ]; then
    write_status "idle" "no pending sync__ handoffs" "$baseline"
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
    write_status "waiting-safe" "${count} handoff(s) pending, baseline unchanged" "$baseline"
  else
    signature="conflict:${current_sha}:${names}"
    if [ "$signature" != "$last_signature" ]; then
      echo "CONFLICT: ${count} sync__ handoff(s) pending (${names%,}) but CURRENT.md moved since last known sync — was ${baseline:0:8}, now ${current_sha:0:8}. Another session may be editing/syncing CURRENT.md concurrently. NOT auto-syncing — raise this, do not resolve it here."
      last_signature="$signature"
    fi
    write_status "alert-conflict" "CURRENT.md moved: ${baseline:0:8} -> ${current_sha:0:8}; ${count} handoff(s) pending" "$baseline"
  fi

  sleep "$POLL_SECONDS"
done
