#!/usr/bin/env bash
# gpu-reservation-coupler.sh
#
# Couples the gpu-reservation deployment to the decode deployment so that a
# constant GPU footprint (decode replicas + reservation replicas == HOLD_TOTAL)
# is always held for our test. When KEDA scales decode UP, the reservation is
# scaled DOWN by the same amount within one poll -- freeing a pre-reserved GPU
# for the new decode pod instead of racing other tenants for a fresh one. When
# decode scales back DOWN, the reservation is scaled back UP to re-park the GPU.
#
# Scoped strictly to deploy/gpu-reservation in dhl-wva-209. Touches nothing else.
# Stop early:  touch /tmp/stop-gpu-coupler   (or TaskStop the background task)
set -uo pipefail
NS=dhl-wva-209
DECODE=unsloth--608e585a-instruct-decode
RES=gpu-reservation
HOLD_TOTAL=2
STOP=/tmp/stop-gpu-coupler
MAX_ITERS=560            # ~47 min safety cap at 5s poll
POLL=5

log(){ echo "$(date -u +%H:%M:%S) coupler | $*"; }
log "start: HOLD_TOTAL=$HOLD_TOTAL decode=$DECODE res=$RES poll=${POLL}s"
rm -f "$STOP"
for i in $(seq 1 "$MAX_ITERS"); do
  if [ -f "$STOP" ]; then log "stop sentinel present; exiting"; break; fi
  dd=$(kubectl get deploy "$DECODE" -n "$NS" -o jsonpath='{.spec.replicas}' 2>/dev/null)
  cur=$(kubectl get deploy "$RES" -n "$NS" -o jsonpath='{.spec.replicas}' 2>/dev/null)
  if [ -z "$dd" ]; then log "WARN decode replicas unreadable; skip"; sleep "$POLL"; continue; fi
  if [ -z "$cur" ]; then log "WARN reservation deploy missing; skip"; sleep "$POLL"; continue; fi
  target=$(( HOLD_TOTAL - dd )); [ "$target" -lt 0 ] && target=0
  if [ "$cur" != "$target" ]; then
    log "decode=$dd  reservation $cur -> $target  (scaling)"
    if kubectl scale deploy/"$RES" -n "$NS" --replicas="$target" >/dev/null 2>&1; then
      log "reservation scaled to $target"
    else
      log "ERR: scale failed"
    fi
  fi
  sleep "$POLL"
done
log "exit"
