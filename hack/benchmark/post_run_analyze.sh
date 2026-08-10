#!/usr/bin/env bash
# Post-run analyzer for two-variant WVA benchmarks.
# Wraps the five steps that should always run after `make benchmark-run`:
#   1. dump WVA controller decisions + saturation analyzer numbers from logs
#      (must run while the controller pod's log buffer still covers the run
#       window — kubectl rotates, so do this promptly after the benchmark).
#      Promptness is necessary but not sufficient: if the controller's log format
#      has drifted, step 1 fails no matter how quickly it runs. Saving the raw
#      controller log during the run and re-parsing it with --log-file is the
#      durable answer, since it survives both rotation and drift.
#   2. compute capacity & 3-component demand estimate from raw vLLM/EPP scrapes
#   3. render the pipeline plot
#
# Usage:
#   ./hack/benchmark/post_run_analyze.sh <results_dir> [namespace] [suffix]
#
# Where:
#   <results_dir> is e.g. <workspace>-20260531-130812-164/results/guidellm-1780222131-3ew5uw_1
#   [namespace]   defaults to $BENCHMARK_NAMESPACE (required if arg omitted)
#   [suffix]      optional title suffix for the plot
set -euo pipefail

RESULTS_DIR="${1:?usage: $0 <results_dir> [namespace] [suffix]}"
NS="${2:-${BENCHMARK_NAMESPACE:?namespace required: pass as arg 2 or set BENCHMARK_NAMESPACE}}"
SUFFIX="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/5] dump_wva_target_timeseries.py (decisions + saturation analyzer numbers)"
# Deliberately non-fatal: the remaining steps read raw scrapes and are still
# useful without the controller-log timeseries. But do not let the failure pass
# quietly -- a stale log pattern here once produced an all-null file that read as
# a success, so flag it in a way an operator scanning this output will notice.
WVA_DUMP_RC=0
python3 "$SCRIPT_DIR/dump_wva_target_timeseries.py" "$RESULTS_DIR" -n "$NS" || WVA_DUMP_RC=$?
if [ "$WVA_DUMP_RC" -ne 0 ]; then
    echo "  !! WVA timeseries dump FAILED (rc=$WVA_DUMP_RC) -- wva_target_timeseries.json"
    echo "  !! is missing or carries no analysis fields. Later steps still render from"
    echo "  !! raw scrapes, but anything reading supply/demand/utilization/prc is BLIND."
    echo "  !! If the run window has passed, re-parse a saved controller log offline:"
    echo "  !!   python3 hack/benchmark/dump_wva_target_timeseries.py $RESULTS_DIR \\"
    echo "  !!       --log-file <saved-controller.log> --no-window"
fi

echo "[2/5] dump_capacity_demand_estimate.py (raw scrape estimate)"
python3 "$SCRIPT_DIR/dump_capacity_demand_estimate.py" "$RESULTS_DIR"

echo "[3/5] dump_epp_throughput.py (request rate from EPP counters)"
python3 "$SCRIPT_DIR/dump_epp_throughput.py" "$RESULTS_DIR" || true

echo "[4/5] dump_wva_full_timeseries.py (WVA Prometheus metrics — empty if collect_metrics.sh predates the WVA scrape patch)"
python3 "$SCRIPT_DIR/dump_wva_full_timeseries.py" "$RESULTS_DIR" || true

echo "[5/5] plot_two_variant_pipeline.py"
if [ -n "$SUFFIX" ]; then
    python3 "$SCRIPT_DIR/plot_two_variant_pipeline.py" "$RESULTS_DIR" --suffix "$SUFFIX"
else
    python3 "$SCRIPT_DIR/plot_two_variant_pipeline.py" "$RESULTS_DIR"
fi

echo "Done. Outputs:"
echo "  $RESULTS_DIR/metrics/processed/wva_target_timeseries.json"
echo "  $RESULTS_DIR/metrics/processed/capacity_demand_estimate.json"
echo "  $RESULTS_DIR/metrics/processed/epp_throughput.json"
echo "  $RESULTS_DIR/metrics/processed/wva_metrics_timeseries.json"
echo "  $RESULTS_DIR/metrics/graphs/two_variant_v2_full_pipeline.png"
