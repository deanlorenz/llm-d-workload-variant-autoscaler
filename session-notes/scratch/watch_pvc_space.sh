#!/usr/bin/env bash
# Silent guard: emit a line ONLY when workload-pvc free space falls below a floor.
#
# Why this exists: on the 2026-08-07 ladder run, inference-perf was found to write its
# report DIRECTLY to the PVC (/requests/<run>_1), not to node ephemeral storage with a
# later copy. So the 20 Gi PVC is the single destination for the ~11.9 GB per-request
# trace, with no large buffer in front of it. A full PVC truncates or loses the run's
# results, and the trace cannot be regenerated without re-running the whole ladder.
#
# NS and PVC-access pod are hardcoded on purpose: this is a blast-radius guard, not a
# knob. Never point it at another namespace.
set -uo pipefail

NS=dhl-wva-209
POD=access-to-harness-data-workload-pvc
FLOOR_GB=${FLOOR_GB:-5}
POLL=${POLL:-45}

while true; do
    avail=$(kubectl -n "$NS" exec "$POD" -- df -BG /requests 2>/dev/null \
            | awk 'NR==2 { gsub("G", "", $4); print $4 }')
    # A failed exec must not kill the watch (pod restart, transient API error).
    if [ -n "${avail:-}" ] && [ "$avail" -lt "$FLOOR_GB" ] 2>/dev/null; then
        echo "WARN ${NS} workload-pvc free=${avail}G below floor ${FLOOR_GB}G"
    fi
    sleep "$POLL"
done
