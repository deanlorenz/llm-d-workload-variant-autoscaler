#!/usr/bin/env bash
# SessionStart hook. Fires for every worktree's sessions (container-level
# settings.json is shared), but only produces output when cwd is the
# designated sync-main session worktree — everywhere else it's a silent no-op.
SYNC_WORKTREE="/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans"

input=$(cat)
cwd=$(printf '%s' "$input" | grep -o '"cwd"[^,}]*' | sed -E 's/.*: *"([^"]*)".*/\1/')

[ "$cwd" = "$SYNC_WORKTREE" ] || exit 0

status_file="$SYNC_WORKTREE/session/status/main.md"
watch_script="$SYNC_WORKTREE/scripts/sync-main-watch.sh"

# Is a watcher alive right now? Heartbeat under 150s (~2.5x the 60s poll) = yes.
alive=0
if [ -f "$status_file" ]; then
  last_check=$(grep -m1 '^last_check:' "$status_file" | cut -d' ' -f2-)
  last_check_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)
  age=$(( $(date +%s) - last_check_epoch ))
  [ "$last_check_epoch" -gt 0 ] && [ "$age" -lt 150 ] && alive=1
fi

if [ "$alive" -eq 1 ]; then
  context="sync-main watcher is already RUNNING (last heartbeat ${age}s ago) — not started again. Check tip/status with /s-sync-main status."
else
  # Auto-start, no prompt: this worktree IS the designated sync-main session, so
  # a live watcher is its normal steady state. Detached with setsid + nohup so it
  # outlives this hook process and is not killed when the hook returns.
  #
  # The heartbeat check above is only a cheap early-out, NOT the duplicate guard —
  # it is racy (60s heartbeat vs 150s threshold, so a session starting in that
  # window reads "stale" and launches a second poller, which then shares the same
  # status file and hides the duplication; observed 2026-08-10 with two live
  # watchers). The authoritative single-instance guard is an flock inside
  # sync-main-watch.sh itself, so it is safe to reach this line spuriously: a
  # redundant instance refuses the lock and exits 0 without touching the status
  # file. Do not "optimize" by removing either check.
  #
  # Note the tradeoff vs the Monitor-tool path (/s-sync-main watch): a watcher
  # started here is NOT a harness-tracked task, so TaskStop cannot reach it and
  # sync events do NOT arrive as conversation notifications. Stop it via the PID
  # in the status file (/s-sync-main stop handles this), and read the status file
  # for what it has done.
  setsid nohup bash "$watch_script" >/tmp/sync-main-watch-autostart.log 2>&1 &
  disown 2>/dev/null || true
  sleep 2   # let it write its first heartbeat so the report below is truthful
  if [ -f "$status_file" ] && grep -q '^state: watching' "$status_file" 2>/dev/null; then
    newpid=$(grep -m1 '^watcher_pid:' "$status_file" | cut -d' ' -f2-)
    context="sync-main watcher was not running; AUTO-STARTED it (pid ${newpid}) — no action needed. It polls upstream/main every 60s and pushes to origin/main on change. It is detached, not a harness task: sync events will NOT appear as notifications, so read session/status/main.md (or /s-sync-main status) to see what it has done; stop it with /s-sync-main stop."
  else
    context="sync-main watcher was not running and the auto-start did NOT come up cleanly — check /tmp/sync-main-watch-autostart.log, then run /s-sync-main watch to start it in-session."
  fi
fi

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
