#!/usr/bin/env bash
# Wait for the decode pod to become ready. Emits one line per state change so a
# monitor sees progress, and gives up rather than hanging forever.
NS=dhl-wva-209
SEL=llm-d.ai/inferenceServing=true
DEADLINE=$(( SECONDS + 1500 ))
last=""
while [ $SECONDS -lt $DEADLINE ]; do
  ready=$(kubectl get pods -n $NS -l $SEL -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null)
  phase=$(kubectl get pods -n $NS -l $SEL -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
  state="phase=$phase ready=$ready"
  if [ "$state" != "$last" ]; then
    echo "$(date -u +%H:%M:%S) $state"
    last="$state"
  fi
  if [ "$ready" = "true" ]; then
    echo "DECODE POD READY"
    exit 0
  fi
  sleep 15
done
echo "TIMEOUT waiting for decode pod ready"
exit 1
