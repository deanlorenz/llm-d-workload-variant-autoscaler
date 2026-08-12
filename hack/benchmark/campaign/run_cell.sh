#!/usr/bin/env bash
# Run one matrix cell end to end, capturing the artifacts that make it
# interpretable afterwards.
#
# Order matters and is deliberate:
#   1. set the analyzer set (this restarts the controller, flushing the
#      in-memory capacity history so this run is not a function of the last one)
#   2. reset per-run state
#   3. record the analyzer config and images actually live -- staged here because
#      the run directory the harness will create doesn't exist yet; moved into
#      runs/<run-id>/config/ at step 6 once it does, not duplicated
#   4. run
#   5. save the raw controller log BEFORE analysis -- it survives both log
#      rotation and any future log-format drift, which a parsed file does not
#   6. analyse
#
# session-notes/campaign-runs/<cell>/ is cell-keyed, campaign-scoped bookkeeping
# (run.log, results-dir.txt for run_all.sh's abort check, and a copy of
# controller.log) -- distinct from runs/<run-id>/config/, which is per-run and
# holds the actual reproducible config set. Nothing here is duplicated there
# by design; see step 3/6 for the analyzer-config/images/scaledobject handoff.
#
# Usage: run_cell.sh <env-name>
set -uo pipefail

ENV_NAME="${1:?usage: run_cell.sh <env-name>}"
OUT="session-notes/campaign-runs/${ENV_NAME}"
mkdir -p "$OUT"

NS=$(grep -E '^BENCHMARK_NAMESPACE=' "hack/benchmark/${ENV_NAME}.env" | cut -d= -f2)
ANALYZERS=$(grep -E '^WVA_ANALYZERS=' "hack/benchmark/${ENV_NAME}.env" | cut -d= -f2)

echo "=============================================================="
echo "CELL $ENV_NAME  (analyzers=$ANALYZERS)  $(date -u +%H:%M:%S)Z"
echo "=============================================================="

echo "--- [0/6] ensure the controller is on this cell's pinned image ---"
# Each cell declares its own image. Applying it here is what makes the image a
# real axis of the experiment rather than whatever happened to be deployed.
make benchmark-apply-images BENCHMARK_ENV="$ENV_NAME" BENCHMARK_APPLY=true </dev/null 2>&1 | tail -6

if [ -n "$ANALYZERS" ]; then
  echo "--- [1/6] set analyzers to '$ANALYZERS' (also restarts the controller) ---"
  make benchmark-set-analyzers BENCHMARK_ENV="$ENV_NAME" WVA_ANALYZERS="$ANALYZERS" </dev/null 2>&1 | tail -6
else
  # No analyzer set declared: leave the live config alone rather than passing an
  # empty list, which set_analyzers.py rightly rejects. Still restart, because a
  # run must not inherit the previous run's in-memory capacity history.
  echo "--- [1/6] no WVA_ANALYZERS in env; leaving analyzer config as-is, restarting only ---"
  make benchmark-restart-controller BENCHMARK_ENV="$ENV_NAME" </dev/null 2>&1 | tail -4
fi

echo "--- [2/6] reset per-run state ---"
make benchmark-reset-run BENCHMARK_ENV="$ENV_NAME" BENCHMARK_RESET_APPLY=true </dev/null 2>&1 | tail -3

echo "--- [3/6] record live config + images ---"
python3 hack/benchmark/set_analyzers.py -n "$NS" --show > "$OUT/analyzer-config.txt" 2>&1
make benchmark-record-images BENCHMARK_ENV="$ENV_NAME" </dev/null > "$OUT/images.txt" 2>&1
kubectl get scaledobject -n "$NS" -o yaml > "$OUT/scaledobject.yaml" 2>&1

echo "--- [4/6] run ---"
START=$(date -u +%s)
make benchmark-run BENCHMARK_ENV="$ENV_NAME" </dev/null > "$OUT/run.log" 2>&1
RC=$?
END=$(date -u +%s)
echo "run exited rc=$RC after $(( (END-START)/60 )) min"
tail -15 "$OUT/run.log"

echo "--- [5/6] save raw controller log (before analysis, on purpose) ---"
kubectl logs -n "$NS" -l app.kubernetes.io/name=workload-variant-autoscaler \
  --tail=200000 > "$OUT/controller.log" 2>&1
echo "controller log: $(wc -l < "$OUT/controller.log") lines"
grep -c "analyzer-result" "$OUT/controller.log" | sed 's/^/  analyzer-result lines: /'
echo "  analyzers seen in the log:"
grep -o '"analyzer": "[a-z]*"' "$OUT/controller.log" | sort | uniq -c | sed 's/^/    /'

echo "--- [6/6] analyse ---"
# BENCHMARK_WORKSPACE defaults to runs/ (Makefile), so the harness writes its
# own $USER-<date>-<time>-<pid>/ directory there natively -- no copy or move.
# Newest first, since each cell creates one.
RESULTS=$(ls -dt runs/*/results/*_1 2>/dev/null | head -1)
if [ -z "$RESULTS" ]; then
  # Fall back to the configured workdir in case a future harness honours it.
  RESULTS=$(ls -dt "$HOME"/data/wva-benchmark/*/results/*_1 2>/dev/null | head -1)
fi
if [ -n "$RESULTS" ]; then
  echo "results dir: $RESULTS"
  bash hack/benchmark/post_run_analyze.sh "$RESULTS" "$NS" 2>&1 | tail -25
  cp "$OUT/controller.log" "$RESULTS/controller.log" 2>/dev/null

  # Drop the reproducible/durable set (.env, analyzer config, image record,
  # ScaledObject snapshot) into config/, a sibling of results/ inside the same
  # run directory the harness already created -- tracked in git; everything
  # else the harness wrote (results/, logs/, setup/, plan/, environment/)
  # stays untracked via a .gitignore allowlist rather than a raw/ subfolder,
  # so nothing here needs to move. RESULTS is runs/<run-id>/results/<leaf>, so
  # the run directory is the first TWO path segments, not one.
  RUN_DIR=$(echo "$RESULTS" | cut -d/ -f1-2)
  mkdir -p "$RUN_DIR/config"
  cp "hack/benchmark/${ENV_NAME}.env" "$RUN_DIR/config/" 2>/dev/null
  # mv, not cp: analyzer-config.txt/images.txt/scaledobject.yaml were staged in
  # $OUT (step 3, before RUN_DIR was known) -- move them into config/ rather
  # than duplicating, since runs/<id>/config/ is now their real home.
  mv "$OUT/analyzer-config.txt" "$OUT/images.txt" "$OUT/scaledobject.yaml" "$RUN_DIR/config/" 2>/dev/null
  echo "$RUN_DIR" > "$OUT/results-dir.txt"
  echo "config recorded at $RUN_DIR/config/ (harness output stays in place under $RUN_DIR)"

  echo "--- writing REPORT.md ---"
  python3 hack/benchmark/campaign/write_report.py "$RUN_DIR" --scenario "$ENV_NAME" 2>&1 | tail -5
else
  echo "WARNING: no results directory found; skipping analysis"
fi
echo "CELL $ENV_NAME DONE $(date -u +%H:%M:%S)Z"
