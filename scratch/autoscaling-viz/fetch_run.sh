#!/usr/bin/env bash
# Pull one benchmark run directory off a cluster PVC into a local working copy.
#
# READ-ONLY on the cluster. This script only ever runs `get`, `exec ... ls|cat|tar`
# and `cp` FROM the pod. It never creates, patches, labels or deletes anything, and
# it refuses to run if you hand it a subcommand that would.
#
# It needs a pod that already mounts the results PVC. If you do not have one, ask
# whoever owns the namespace to point you at theirs -- do NOT create one yourself
# in a namespace you do not own.
#
#   ./fetch_run.sh -n <namespace> -p <pod> -r <remote-run-dir> -o <local-dir>
#
# By default the multi-GB per-request file is SKIPPED (panels 2-5 still work, and
# extract_real_trace.py degrades gracefully). Add -f to take everything.
#
# Examples
#   # what runs exist?
#   ./fetch_run.sh -n biran -p access-to-harness-data-workload-pvc -l
#
#   # fetch one, without the huge file
#   ./fetch_run.sh -n biran -p access-to-harness-data-workload-pvc \
#                  -r /requests/guidellm-1785859604-upf3j2_1 \
#                  -o real-trace/upf3j2
#
#   # fetch everything including per-request detail (can be GBs)
#   ./fetch_run.sh -n biran -p ... -r ... -o ... -f

set -euo pipefail

NS=""; POD=""; REMOTE=""; OUT=""; FULL=0; LIST=0; ROOT="/requests"
KC="${KUBECTL:-}"

usage() { sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while getopts 'n:p:r:o:R:flh' opt; do
  case "$opt" in
    n) NS="$OPTARG" ;;
    p) POD="$OPTARG" ;;
    r) REMOTE="$OPTARG" ;;
    o) OUT="$OPTARG" ;;
    R) ROOT="$OPTARG" ;;
    f) FULL=1 ;;
    l) LIST=1 ;;
    h) usage 0 ;;
    *) usage 2 ;;
  esac
done

if [[ -z "$KC" ]]; then
  if command -v oc >/dev/null 2>&1; then KC=oc
  elif command -v kubectl >/dev/null 2>&1; then KC=kubectl
  else echo "error: neither oc nor kubectl found on PATH" >&2; exit 1; fi
fi

[[ -n "$NS" ]] || { echo "error: -n <namespace> is required" >&2; usage 2; }

# --- discovery -------------------------------------------------------------- #

if [[ -z "$POD" ]]; then
  echo "# pods in $NS that mount a PVC (candidates for -p):"
  $KC get pods -n "$NS" \
     -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.volumes[*]}{.persistentVolumeClaim.claimName}{" "}{end}{"\n"}{end}' \
     2>/dev/null | awk -F'\t' '$2 ~ /[a-z]/ {print "  " $1 "  <- " $2}'
  echo
  echo "# then re-run with -p <pod> -l to list runs"
  exit 0
fi

if [[ "$LIST" == 1 ]]; then
  echo "# runs under $ROOT in $NS/$POD:"
  $KC exec -n "$NS" "$POD" -- sh -c \
    "for d in $ROOT/*/; do [ -d \"\$d\" ] || continue;
       printf '%s\t%s\n' \"\$(du -sh \"\$d\" 2>/dev/null | cut -f1)\" \"\$d\"; done" \
    2>/dev/null | sed 's/^/  /'
  exit 0
fi

[[ -n "$REMOTE" ]] || { echo "error: -r <remote-run-dir> is required (or use -l)" >&2; exit 2; }
[[ -n "$OUT"    ]] || { echo "error: -o <local-dir> is required" >&2; exit 2; }

# --- fetch ------------------------------------------------------------------ #

mkdir -p "$OUT"
echo "# source: $NS/$POD:$REMOTE"
echo "# dest:   $OUT"

# The small artifacts: metadata, config, and everything under metrics/.
# metrics/raw/ is the only time-resolved source, so it is never optional.
SMALL='run_metadata.yaml config.yaml *.yaml metrics'
for item in $SMALL; do
  if $KC exec -n "$NS" "$POD" -- sh -c "ls -d '$REMOTE'/$item >/dev/null 2>&1"; then
    echo "  fetching $item ..."
    $KC cp -n "$NS" "$POD:$REMOTE/$item" "$OUT/$(basename "$item")" 2>/dev/null || \
      echo "    (skipped $item)"
  fi
done

# Summary-sized lifecycle files (KBs, safe to always take).
for f in summary_lifecycle_metrics.json stage_0_lifecycle_metrics.json \
         stage_1_lifecycle_metrics.json stage_2_lifecycle_metrics.json \
         stage_3_lifecycle_metrics.json; do
  $KC exec -n "$NS" "$POD" -- test -f "$REMOTE/$f" 2>/dev/null && {
    echo "  fetching $f ..."
    $KC cp -n "$NS" "$POD:$REMOTE/$f" "$OUT/$f" 2>/dev/null || true
  }
done

# The big one. guidellm calls it results.json (100-200 MB); inference-perf calls it
# per_request_lifecycle_metrics.json (can be several GB).
for big in results.json per_request_lifecycle_metrics.json; do
  size=$($KC exec -n "$NS" "$POD" -- sh -c \
         "du -m '$REMOTE/$big' 2>/dev/null | cut -f1" 2>/dev/null || true)
  [[ -n "${size:-}" ]] || continue
  if [[ "$FULL" == 1 ]]; then
    echo "  fetching $big (${size} MB) ..."
    $KC cp -n "$NS" "$POD:$REMOTE/$big" "$OUT/$big"
  else
    echo "  SKIPPING $big (${size} MB) -- pass -f to include it."
    echo "  cutting a 50-record head sample instead ..."
    # Extract at the source: streaming the head avoids moving GBs for a sample.
    $KC exec -n "$NS" "$POD" -- python3 -c "
import json,sys
p='$REMOTE/$big'
try:
    d=json.load(open(p))
except Exception as e:
    sys.exit(0)
if isinstance(d,list): head=d[:50]
else:
    b=(d.get('benchmarks') or [{}])[0]
    head=((b.get('requests') or {}).get('successful') or [])[:50]
json.dump(head,sys.stdout)
" > "$OUT/per_request_head.json" 2>/dev/null || rm -f "$OUT/per_request_head.json"
    [[ -s "$OUT/per_request_head.json" ]] && echo "  wrote per_request_head.json"
  fi
done

echo
echo "# fetched:"
du -sh "$OUT"
find "$OUT" -maxdepth 1 -mindepth 1 | sed 's|^|  |'
echo
echo "# next:"
echo "  python3 extract_real_trace.py --run $OUT --out $OUT"
