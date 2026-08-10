#!/usr/bin/env bash
# Sample the autoscaling signals during a run, one line per change. This is the
# live view of the thing under test: whether the controller raises the replica
# target, and which analyzer speaks for it.
NS=dhl-wva-209
DEADLINE=$(( SECONDS + 2400 ))
last=""
while [ $SECONDS -lt $DEADLINE ]; do
  hpa=$(kubectl get hpa -n $NS -o jsonpath='{.items[0].status.desiredReplicas}' 2>/dev/null)
  cur=$(kubectl get hpa -n $NS -o jsonpath='{.items[0].status.currentReplicas}' 2>/dev/null)
  rdy=$(kubectl get deploy -n $NS unsloth--608e585a-instruct-decode -o jsonpath='{.status.readyReplicas}' 2>/dev/null)
  state="desired=$hpa current=$cur ready=${rdy:-0}"
  if [ "$state" != "$last" ]; then
    echo "$(date -u +%H:%M:%S) $state"
    last="$state"
  fi
  # Stop once the harness pod is gone: the run is over.
  if ! kubectl get pods -n $NS 2>/dev/null | grep -q "inference-perf.*Running"; then
    echo "$(date -u +%H:%M:%S) harness no longer running; stopping watch"
    exit 0
  fi
  sleep 20
done
echo "watch deadline reached"
