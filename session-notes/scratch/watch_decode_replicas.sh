#!/usr/bin/env bash
# Emit one line per CHANGE in the decode deployment's replica count.
#
# WHY A SCRIPT AND NOT A ONE-LINER: the replica trace is the science of an
# autoscaling run, and the console log is silent for the whole load window
# (harness progress goes to the harness pod's stdout, not to `make` output). This
# turns "did it scale" into events instead of something you discover afterwards.
#
# Emits on change only -- a steady count produces nothing, so this is quiet by
# construction and safe to leave armed for a whole run.
#
# NS is hardcoded on purpose. It is the blast-radius guard, not a knob: this is a
# shared cluster and a read-only watch pointed at the wrong namespace is still a
# watch pointed at someone else's workload.
#
# Usage: bash session-notes/scratch/watch_decode_replicas.sh
set -uo pipefail

NS=dhl-wva-209
DEPLOY=unsloth--608e585a-instruct-decode
POLL_SEC="${POLL_SEC:-20}"

prev=""
while true; do
    # `|| echo` so a transient API error is reported as "?" rather than killing
    # the watch -- a dropped kubectl call must not look like a scale event.
    cur=$(kubectl -n "$NS" get deploy "$DEPLOY" \
        -o jsonpath='{.spec.replicas}/{.status.readyReplicas}' 2>/dev/null || echo '?')
    [ -n "$cur" ] || cur='?'
    if [ "$cur" != "$prev" ]; then
        printf '%s decode desired/ready = %s\n' "$(date -u +%H:%M:%SZ)" "$cur"
        prev="$cur"
    fi
    sleep "$POLL_SEC"
done
