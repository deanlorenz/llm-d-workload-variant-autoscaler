#!/usr/bin/env bash
# Run the whole campaign, then free the GPUs.
#
# Cell order is deliberate. The baseline cell runs first while the cluster is
# already on the old image, so the campaign starts with the one image change it
# cannot avoid rather than two. After that every cell is on the latest image.
#
# The GPU release is in a trap, so it happens on success, on failure, and on
# interruption. Leaving H100s held on a shared cluster overnight is the one
# outcome worth protecting against unconditionally -- it is the reason the
# release does not simply sit at the end of the script.
set -uo pipefail

NS=dhl-wva-209
LOG=session-notes/campaign-runs/campaign.log
mkdir -p session-notes/campaign-runs

free_gpus() {
  echo "" | tee -a "$LOG"
  echo "=== FREEING GPUs $(date -u +%H:%M:%S)Z ===" | tee -a "$LOG"
  # Pause the autoscaler at 0 first: pausing is what stops KEDA from immediately
  # scaling the deployment back up after it is scaled down.
  kubectl annotate --overwrite scaledobject/unsloth--608e585a-instruct-decode-scaler \
    -n "$NS" autoscaling.keda.sh/paused-replicas=0 2>&1 | tee -a "$LOG"
  kubectl scale deploy/unsloth--608e585a-instruct-decode -n "$NS" --replicas=0 2>&1 | tee -a "$LOG"
  sleep 10
  echo "--- final state ---" | tee -a "$LOG"
  kubectl get scaledobject -n "$NS" \
    -o custom-columns='NAME:.metadata.name,PAUSED:.metadata.annotations.autoscaling\.keda\.sh/paused-replicas' 2>&1 | tee -a "$LOG"
  kubectl get deploy -n "$NS" unsloth--608e585a-instruct-decode \
    -o custom-columns='NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas' 2>&1 | tee -a "$LOG"
  kubectl get pods -n "$NS" -l llm-d.ai/inferenceServing=true 2>&1 | tee -a "$LOG"
  echo "=== GPUs FREED ===" | tee -a "$LOG"
}
trap free_gpus EXIT INT TERM

# Override with CELLS="a b c" to run a subset (e.g. to resume a campaign).
DEFAULT_CELLS="b-satta-staircase m-satta-staircase m-sat-staircase m-ta-staircase m-satta-dwell m-sat-dwell m-ta-dwell"
read -r -a CELLS <<< "${CELLS:-$DEFAULT_CELLS}"

echo "CAMPAIGN START $(date -u +%FT%TZ) -- ${#CELLS[@]} cells" | tee -a "$LOG"
n=0
for cell in "${CELLS[@]}"; do
  n=$((n+1))
  echo "" | tee -a "$LOG"
  bash hack/benchmark/campaign/run_cell.sh "$cell" 2>&1 | tee -a "$LOG"
  echo "--- cell $cell finished ($n/${#CELLS[@]}) ---" | tee -a "$LOG"

  # Fail fast on a systematic problem. A cell that produced no results directory
  # did not generate load, and whatever stopped it will almost certainly stop
  # every remaining cell too -- the first attempt burned all seven that way. One
  # bad cell aborts the campaign rather than repeating the same failure six more
  # times; the trap still frees the GPUs on the way out.
  if [ ! -s "session-notes/campaign-runs/$cell/results-dir.txt" ]; then
    echo "ABORT: cell $cell produced no results directory. Stopping the campaign" | tee -a "$LOG"
    echo "       rather than repeating a systematic failure across the remaining cells." | tee -a "$LOG"
    break
  fi
done
echo "" | tee -a "$LOG"
echo "CAMPAIGN END $(date -u +%FT%TZ)" | tee -a "$LOG"
