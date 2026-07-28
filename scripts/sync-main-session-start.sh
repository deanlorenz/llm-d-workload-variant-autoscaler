#!/usr/bin/env bash
# SessionStart hook. Fires for every worktree's sessions (container-level
# settings.json is shared), but only produces output when cwd is the
# designated sync-main session worktree — everywhere else it's a silent no-op.
SYNC_WORKTREE="/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans"

input=$(cat)
cwd=$(printf '%s' "$input" | grep -o '"cwd"[^,}]*' | sed -E 's/.*: *"([^"]*)".*/\1/')

[ "$cwd" = "$SYNC_WORKTREE" ] || exit 0

status_file="$SYNC_WORKTREE/session/status/main.md"
if [ ! -f "$status_file" ]; then
  context="sync-main watcher status: no status file found — never started, or a fresh checkout. Run /s-sync-main to check/start it."
else
  last_check=$(grep '^last_check:' "$status_file" | cut -d' ' -f2-)
  last_check_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)
  now_epoch=$(date +%s)
  age=$(( now_epoch - last_check_epoch ))
  if [ "$age" -lt 150 ]; then
    context="sync-main watcher is RUNNING (last heartbeat ${age}s ago). No action needed unless you want to check tip/status — run /s-sync-main."
  else
    context="sync-main watcher is NOT running (stale or missing heartbeat). Consider running /s-sync-main to check status and start watch mode."
  fi
fi

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
