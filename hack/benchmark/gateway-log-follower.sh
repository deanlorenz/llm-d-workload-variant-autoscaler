#!/usr/bin/env bash
# Continuously mirror the inference gateway's istio-proxy access log onto the PVC.
#
# WHY THIS EXISTS
# ---------------
# The gateway access log is the only surviving per-request trace for a benchmark run when the
# harness fails to write per_request_lifecycle_metrics.json (it was OOMKilled on 2026-08-07).
# It lives in the container's stdout, which the kubelet rotates. On pokprod that rotation is
# containerLogMaxSize=50Mi with containerLogMaxFiles=5 -- but only the LATEST file is reachable
# through `kubectl logs`, so the usable budget is ONE file, ~100k requests.
#
# Rotation is a CLIFF, not a slope: it starts a NEW file rather than trimming the old one. At
# the instant it fires, the retrievable log drops to nearly nothing. A rotation mid-run leaves
# only the run's tail; one just after a run leaves essentially nothing. Harvesting after the
# run is therefore a bet that rotation did not fire in the meantime. This follower removes the
# bet by copying the bytes to durable storage as they are produced.
#
# It runs in-cluster and writes to the PVC, so it keeps working when the operator's laptop is
# closed -- the same requirement the GPU release process has.
#
# AT-LEAST-ONCE, BY DESIGN
# ------------------------
# The restart watermark is `--since-time`, whose granularity is ONE SECOND while this log
# carries 20+ lines/second. Exactly-once is therefore not available, and trying for it would
# risk silent loss. So the watermark is deliberately rewound (WATERMARK_LAG_SEC) and duplicates
# are removed at parse time by Envoy's x-request-id -- see envoy_per_request.py --dedup, which
# is not optional for files this produces.
#
# Rewinding also sidesteps a documented ambiguity: the kubectl reference says --since-time
# returns logs "after" a date, without specifying whether the boundary second is inclusive. If
# it is exclusive we would lose up to a full second on every restart. Rewinding makes the
# question moot.
#
# TWO UNDOCUMENTED BEHAVIOURS THIS GUARDS AGAINST
# -----------------------------------------------
# Neither the kubectl reference nor the Logging Architecture page says what a `-f` stream does
# when (a) the log rotates underneath it, or (b) a NEW pod starts matching the selector. Both
# would fail SILENTLY -- the stream simply stops producing while the process stays alive, which
# is indistinguishable from an idle gateway. So this script does not trust a long-lived stream:
#
#   * a pod-set watcher kills the stream when the matching pod UIDs change, which is the case
#     that matters after a gateway restart (the pod name changes, so a name-based follower would
#     silently follow nothing);
#   * STREAM_MAX_SEC caps any single stream's lifetime as a backstop for anything else;
#   * --ignore-errors is deliberately NOT used. A dying stream should exit so the loop restarts
#     it with an advanced watermark; making errors non-fatal would hide exactly what we need to
#     react to.
#
# What no follower can protect against is a rotation firing inside the sub-second restart gap;
# that loses the previous file's tail. It is bounded and detectable -- envoy_per_request.py
# hard-fails on the request-count identity rather than producing a silently shifted stage grid.
#
# THE --tail TRAP
# ---------------
# `--tail` defaults to -1 (everything) with no selector but to 10 WHEN A SELECTOR IS GIVEN
# (kubectl reference, verbatim). We use a selector, so --tail=-1 is passed explicitly. Without
# it, every stream restart would silently begin 10 lines back instead of at the watermark.
#
# USAGE
#   Normally deployed by gateway-log-follower.yaml, which mounts this from a ConfigMap.
#   Standalone (reads your kubeconfig):
#     NAMESPACE=dhl-wva-209 OUT_DIR=/tmp/igw ./hack/benchmark/gateway-log-follower.sh
set -uo pipefail

NAMESPACE="${NAMESPACE:?NAMESPACE must be set -- never let this default to a namespace}"
SELECTOR="${SELECTOR:-app.kubernetes.io/component=inference-gateway}"
OUT_DIR="${OUT_DIR:-/requests/gateway-logs}"
OUT="${OUT:-$OUT_DIR/igw-access.log}"

# Cap the single output file. At ~506 B/request on disk and ~100k requests per ladder run, a
# 2 GB cap is roughly 40 runs. Refusing to start is the right failure: silently rolling would
# break the watermark resume, and silently growing would fill a PVC shared with run results.
MAX_FILE_MB="${MAX_FILE_MB:-2000}"

# How far to rewind the watermark on each restart. 2 s at 20 lines/s is ~40 duplicate lines per
# restart -- trivial next to the cost of a gap, and dedup removes them.
WATERMARK_LAG_SEC="${WATERMARK_LAG_SEC:-2}"

STREAM_MAX_SEC="${STREAM_MAX_SEC:-3600}"   # backstop; the pod watcher is the real trigger
POLL_SEC="${POLL_SEC:-15}"                 # pod-set poll interval
RETRY_SEC="${RETRY_SEC:-5}"                # pause between stream attempts
MAX_LOG_REQUESTS="${MAX_LOG_REQUESTS:-10}" # kubectl default is 5; we expect 1 gateway pod

KUBECTL="${KUBECTL:-kubectl}"

log() { printf '%s [follower] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

pod_uids() {
    # Sorted so the comparison is order-independent; kubectl does not guarantee ordering.
    $KUBECTL get pods -n "$NAMESPACE" -l "$SELECTOR" \
        -o 'jsonpath={range .items[*]}{.metadata.uid}{"\n"}{end}' 2>/dev/null | sort | tr '\n' ','
}

# Last kubectl timestamp already captured, rewound by WATERMARK_LAG_SEC and floored to the
# second. Empty output means "start from the beginning of the current log file".
watermark() {
    [ -s "$OUT" ] || return 0
    local last
    last=$(tail -n 1 "$OUT" | cut -d' ' -f1 | cut -c1-19)
    # Guard against a torn final line: a partial write can leave something that is not a
    # timestamp, and feeding that to --since-time would make kubectl reject the whole request.
    case "$last" in
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]) ;;
        *) log "WARNING last line of $OUT has no parsable timestamp; restarting without a" \
               "watermark, which re-reads the whole current file (dedup will absorb it)"
           return 0 ;;
    esac
    # date -d is GNU-only, which holds for the OCP cli image; fall back to the un-rewound
    # value rather than losing the watermark entirely.
    date -u -d "${last}Z -${WATERMARK_LAG_SEC} seconds" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
        || printf '%sZ\n' "$last"
}

watch_pods() {   # $1 = pid to kill when the matching pod set changes
    local target="$1" baseline current
    baseline=$(pod_uids)
    while kill -0 "$target" 2>/dev/null; do
        sleep "$POLL_SEC"
        current=$(pod_uids)
        if [ -n "$current" ] && [ "$current" != "$baseline" ]; then
            log "gateway pod set changed ($baseline -> $current); cycling the stream so we" \
                "follow the new pod instead of silently following nothing"
            kill "$target" 2>/dev/null
            return 0
        fi
    done
}

stream_once() {
    local since args=()
    since=$(watermark)
    args=(logs -f -n "$NAMESPACE" -l "$SELECTOR" --all-containers=true
          --timestamps=true --tail=-1 --max-log-requests="$MAX_LOG_REQUESTS")
    if [ -n "$since" ]; then
        args+=(--since-time="$since")
        log "streaming from $since (at-least-once; dedup on x-request-id at parse time)"
    else
        log "streaming from the start of the current log file (no watermark yet)"
    fi

    timeout --signal=TERM "$STREAM_MAX_SEC" "$KUBECTL" "${args[@]}" >>"$OUT" &
    local kpid=$!
    watch_pods "$kpid" &
    local wpid=$!
    wait "$kpid"
    local rc=$?
    kill "$wpid" 2>/dev/null
    wait "$wpid" 2>/dev/null
    return "$rc"
}

mkdir -p "$OUT_DIR" || { log "FATAL cannot create $OUT_DIR"; exit 1; }
touch "$OUT" || { log "FATAL cannot write $OUT"; exit 1; }

log "namespace=$NAMESPACE selector=$SELECTOR out=$OUT"
log "stream_max=${STREAM_MAX_SEC}s poll=${POLL_SEC}s watermark_lag=${WATERMARK_LAG_SEC}s" \
    "max_file=${MAX_FILE_MB}MB"

while :; do
    size_mb=$(( $(wc -c <"$OUT") / 1000000 ))
    if [ "$size_mb" -ge "$MAX_FILE_MB" ]; then
        log "FATAL $OUT is ${size_mb}MB, at the ${MAX_FILE_MB}MB cap. Refusing to continue:" \
            "growing without bound would fill a PVC shared with run results. Archive or" \
            "truncate $OUT, then restart this deployment."
        exit 1
    fi
    stream_once
    rc=$?   # captured before anything else runs; $? inline would be fragile to reorder
    log "stream ended (rc=$rc, $(wc -l <"$OUT") lines captured); retrying in ${RETRY_SEC}s"
    sleep "$RETRY_SEC"
done
