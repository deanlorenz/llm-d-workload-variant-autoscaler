#!/usr/bin/env bash
# Emit one line when the given PID exits, then exit. Single-notification watch.
#
# WHY: the harness's own completion signal (`make benchmark-run` returning) is the
# only authoritative "collection finished" marker -- the result file stops growing
# well before the process finishes its post-collection steps, so size-polling gives
# false positives. This waits on the process itself.
#
# Read-only: touches no cluster and no repo file.
#
# Usage: bash session-notes/scratch/wait_pid_exit.sh <pid> [label]
set -uo pipefail

PID="${1:?usage: wait_pid_exit.sh <pid> [label]}"
LABEL="${2:-pid $PID}"
POLL_SEC="${POLL_SEC:-20}"

while kill -0 "$PID" 2>/dev/null; do
    sleep "$POLL_SEC"
done

printf '%s %s: EXITED\n' "$(date -u +%H:%M:%SZ)" "$LABEL"
