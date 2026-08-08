#!/usr/bin/env bash
# Emit one line when the named harness pod leaves Running, then exit.
#
# WHY: `make benchmark-run` exiting is the authoritative completion signal, but it
# also tears the pod down, so by the time it fires the pod's terminal phase is no
# longer readable. Watching the pod directly captures Succeeded vs Failed while it
# still exists -- the difference between "collect the results" and "diagnose an
# OOM". One line, then exit: this is a single-notification watch, not a stream.
#
# NS is hardcoded as the blast-radius guard, not a knob (shared cluster).
#
# Usage: bash session-notes/scratch/wait_harness_done.sh <pod-name>
set -uo pipefail

NS=dhl-wva-209
POD="${1:?usage: wait_harness_done.sh <pod-name>}"
POLL_SEC="${POLL_SEC:-15}"

while true; do
    # Missing pod (deleted by the reaper or the harness) counts as done, not as an
    # error -- an empty phase must not spin this loop forever.
    phase=$(kubectl -n "$NS" get pod "$POD" -o jsonpath='{.status.phase}' 2>/dev/null || echo '')
    case "$phase" in
        Running|Pending) ;;
        '')  printf '%s harness %s: GONE (deleted)\n' "$(date -u +%H:%M:%SZ)" "$POD"; exit 0 ;;
        *)   printf '%s harness %s: %s\n' "$(date -u +%H:%M:%SZ)" "$POD" "$phase"; exit 0 ;;
    esac
    sleep "$POLL_SEC"
done
