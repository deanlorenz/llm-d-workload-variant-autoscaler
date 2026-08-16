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
  # a live watcher is its normal steady state.
  #
  # Deliberately stateless (Dean, 2026-08-12): NOT setsid/nohup-detached from
  # /init. A fully detached process outlives everything — a VS Code quit, a
  # session that's never resumed — leaving a stray script nobody can find
  # without knowing to look. Backgrounded plainly instead: sync-main-watch.sh
  # carries its own dead man's switch, keyed on --origin-pid (checked with
  # `kill -0` each poll) and self-exits once that one specific Claude session
  # process is gone — corrected 2026-08-16: not "any Claude process anywhere in
  # this WSL instance," which was never actually what the kill-switch checked
  # and predates this comment. So the watcher's actual lifetime is bounded by
  # "the session that started it is still alive" — restart-on-entry, no manual
  # cleanup ever needed. `disown` only detaches it from this hook's own subshell
  # exit, not from the kill-switch.
  #
  # The heartbeat check above is only a cheap early-out, NOT the duplicate guard —
  # it is racy (60s heartbeat vs 150s threshold, so a session starting in that
  # window reads "stale" and launches a second poller, which then shares the same
  # status file and hides the duplication; observed 2026-08-10 with two live
  # watchers). **Corrected 2026-08-16**: the authoritative single-instance guard
  # is NOT an flock — that predates the Addendum-7/10 migration. It is
  # lib/single-instance-guard.sh's momentary mkdir+pgrep dedup, keyed on the
  # fixed role constant "sync" (not on any session or pid — see that file's own
  # header and sync-watchers-spec.md S2 for why). It is still safe to reach this
  # line spuriously: a redundant instance refuses the guard and exits 0 without
  # touching the status file. Do not "optimize" by removing either check.
  #
  # Note the tradeoff vs the Monitor-tool path (/s-sync-main watch): a watcher
  # started here is NOT a harness-tracked task, so TaskStop cannot reach it and
  # sync events do NOT arrive as conversation notifications. Stop it via the PID
  # in the status file (/s-sync-main stop handles this — or just close VS Code
  # and quit every Claude session; it stops itself within one poll interval).
  # --origin-pid must be the Claude session process, not this hook's own subshell. $PPID here is
  # this script's parent -- the process that invoked the hook -- which is the Claude session per
  # every other SessionStart hook in this family (tier1-session-start.sh assumes the same thing).
  # Not independently verifiable without a real SessionStart firing (no pid field exists in the
  # hook's own JSON payload to cross-check against), but confirmed consistent in practice: the
  # currently-running watcher (started by hand before this fix existed) carries the real long-lived
  # Claude session pid as its --origin-pid, the same value class this line now captures
  # automatically. sync-main-watch.sh only uses this for its kill-switch (kill -0 each poll) since
  # the 2026-08-16 guard migration, not for single-instance identity -- so a wrong pid here leaks or
  # exits early, it does not create a duplicate watcher or corrupt state.
  nohup bash "$watch_script" --origin-pid "$PPID" >/tmp/sync-main-watch-autostart.log 2>&1 &
  disown 2>/dev/null || true
  sleep 2   # let it write its first heartbeat so the report below is truthful
  if [ -f "$status_file" ] && grep -q '^state: watching' "$status_file" 2>/dev/null; then
    newpid=$(grep -m1 '^watcher_pid:' "$status_file" | cut -d' ' -f2-)
    context="sync-main watcher was not running; AUTO-STARTED it (pid ${newpid}) — no action needed. It polls upstream/main every 60s and pushes to origin/main on change, and self-exits once no VS Code/Claude process remains (stateless by design). Sync events will NOT appear as notifications, so read session/status/main.md (or /s-sync-main status) to see what it has done; stop it early with /s-sync-main stop."
  else
    context="sync-main watcher was not running and the auto-start did NOT come up cleanly — check /tmp/sync-main-watch-autostart.log, then run /s-sync-main watch to start it in-session."
  fi
fi

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
