#!/usr/bin/env bash
# sync-main-status.sh — read-only status of the sync-main watcher.
#
# First line is the gate verdict (RUNNING / STALE-NOT-RUNNING / NOT-RUNNING);
# the rest is the status file. The verdict's date math lives here (not on the
# interactive command line) so the caller runs a single allowlistable command
# with no $(...) substitution → no permission prompt.
#
# Usage:  bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-status.sh
set -uo pipefail

S=/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/status/main.md

if [ ! -f "$S" ]; then
  echo "NOT RUNNING (no status file — never started on this machine)"
  exit 0
fi

last_check=$(grep -m1 '^last_check:' "$S" | cut -d' ' -f2-)
# `date -d ""` succeeds (rc 0) and returns midnight-today, not an error -- so an empty/missing
# last_check must be caught explicitly before calling date, or the `|| echo 0` fallback below never
# fires and a genuinely dead watcher can read as "last check 0-149s ago" for ~2.5 minutes after
# midnight local time. Found 2026-08-16 (llm-scaler portability sweep); same bug class as the
# `stat -f %m` issue already fixed elsewhere (a command that succeeds on bad input defeats `||`).
if [ -n "$last_check" ]; then
  lc_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)
else
  lc_epoch=0
fi
age=$(( $(date +%s) - lc_epoch ))

# Watcher heartbeats every 60s; allow ~150s slack before calling it dead.
if [ "$lc_epoch" -gt 0 ] && [ "$age" -lt 150 ]; then
  echo "RUNNING (last check ${age}s ago)"
else
  echo "STALE / NOT RUNNING (last check ${age}s ago)"
fi

cat "$S"
