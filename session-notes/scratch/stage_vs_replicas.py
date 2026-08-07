#!/usr/bin/env python3
"""Join per-stage client latency to the replica count the stage actually ran on.

Why this exists: the raw latency-vs-RPS curve from the 2026-08-07 ladder run is
NON-MONOTONIC (8 RPS -> 7.71 s but 10 RPS -> 7.14 s), which looks like measurement noise
and is not. It is the autoscaler's fingerprint: stage 2 ran on 2 replicas because the
cold-`prc` defect had just scaled the fleet DOWN, while stage 3 ran on 3. Latency tracks
load PER REPLICA, not absolute load, so the comparison has to divide by the replica count
the stage actually had -- time-weighted, because the count changes mid-stage.

TWO CORRECTIONS relative to the first version of this script, both of which changed every
number in its output:

  1. Stage windows were anchored on the run log's `All pods are running` (20:42:36) and grown
     by each stage's own `benchmark_time_seconds`. That anchor is 52 s late -- the gateway's
     first request arrives at 20:41:44.330 -- so every window was shifted. Windows now come
     from `envoy_per_request.stage_grid`, which partitions the actual arrival series on the
     configured per-stage counts and needs no anchor at all.
  2. Replica counts came from the controller's `curr`, sampled once per 60 s cycle. That
     counts replicas the workload OBJECT has, including pods still pulling or loading the
     model, which supply no capacity -- backwards for explaining latency. The primary count
     is now routing-derived (`serving_replicas.weighted`): a replica is serving when the
     gateway is actually sending it requests. `curr` is kept as a cross-check column; the
     two agree within 0.10 replicas on six of eight stages and diverge exactly where the
     fleet was in motion (stage 0's initial ramp, stage 6's scale-up).

Latency still comes from the harness's per-stage aggregates, which are sound. Only the
harness's OUTPUT-TOKEN metrics are unusable for this run (see stage_table.py), which is why
`itl_true_ms` is recomputed here from the profile's true mean rather than read off the report.

Usage: python3 stage_vs_replicas.py [--csv]
"""
import json
import re
import sys
from datetime import datetime, timezone

from envoy_per_request import assign_stages, parse
from serving_replicas import weighted

RATES = [2, 5, 8, 10, 12, 15, 20, 2]
TRUE_MEAN = 512.0
DIR = "session-notes/scratch/ladder-run"
LOG = "session-notes/scratch/ladder-controller.log"

TS = re.compile(r"^(?:\S+\s+)?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
PAYLOAD = re.compile(r'\{"modelID".*\}\s*$')


def observed_replicas():
    """[(timestamp, curr)] from emitted decisions, sorted."""
    pts = []
    for line in open(LOG, errors="replace"):
        mts, mpl = TS.match(line), PAYLOAD.search(line)
        if not (mts and mpl):
            continue
        try:
            d = json.loads(mpl.group(0))
        except json.JSONDecodeError:
            continue
        if d.get("decisions"):
            t = datetime.strptime(mts.group(1), "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc)
            pts.append((t, d["decisions"][0]["curr"]))
    return sorted(set(pts))


def weighted_curr(pts, t0, t1):
    """Time-weighted mean of the piecewise-constant `curr` over [t0, t1), epochs in."""
    total = span = 0.0
    for i, (t, curr) in enumerate(pts):
        nxt = pts[i + 1][0].timestamp() if i + 1 < len(pts) else t1
        lo, hi = max(t.timestamp(), t0), min(nxt, t1)
        if hi <= lo:
            continue
        total += curr * (hi - lo)
        span += hi - lo
    return (total / span) if span else float("nan")


def fmt(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%H:%M:%S")


def main():
    pts = observed_replicas()
    if not pts:
        print(f"no decisions parsed from {LOG}", file=sys.stderr)
        return 1

    # Windows and serving counts both come from the access log; no clock anchor is involved.
    # assign_stages hard-fails if the trace is short, so a rotated log cannot silently
    # produce a shifted grid here.
    grid = weighted(assign_stages(parse()))

    rows = []
    for s, rate, t0, t1, span, reps, _ in grid:
        d = json.load(open(f"{DIR}/stage_{s}.json"))
        lat = d["successes"]["latency"]
        rows.append({
            "stage": s, "rate": rate, "t0": fmt(t0), "t1": fmt(t1),
            "span_s": round(span, 1),
            "reps": reps, "reps_curr": weighted_curr(pts, t0, t1),
            "rps_per_rep": rate / reps,
            "tok_per_rep": rate * TRUE_MEAN / reps,
            "lat_mean": lat["request_latency"]["mean"],
            "lat_p95": lat["request_latency"]["p95"],
            "ttft_mean": lat["time_to_first_token"]["mean"],
            "itl_true_ms": 1000 * (lat["request_latency"]["mean"]
                                   - lat["time_to_first_token"]["mean"]) / TRUE_MEAN,
        })

    if "--csv" in sys.argv:
        keys = list(rows[0])
        print(",".join(keys))
        for r in rows:
            print(",".join(str(r[k]) for k in keys))
        return 0

    print(f"{'stg':>3} {'RPS':>4} {'window':>18} {'reps':>5} {'curr':>5} {'RPS/rep':>8} "
          f"{'tok/s/rep':>10} {'lat_mean':>9} {'lat_p95':>8} {'ttft':>7} {'itl_ms':>7}")
    for r in rows:
        print(f"{r['stage']:>3} {r['rate']:>4} {r['t0']}-{r['t1']} {r['reps']:>5.2f} "
              f"{r['reps_curr']:>5.2f} "
              f"{r['rps_per_rep']:>8.2f} {r['tok_per_rep']:>10.0f} {r['lat_mean']:>9.3f} "
              f"{r['lat_p95']:>8.3f} {r['ttft_mean']:>7.4f} {r['itl_true_ms']:>7.2f}")

    # The controlled comparisons: stages at (nearly) equal per-replica load. If latency is
    # governed by per-replica load, these must agree despite different absolute load --
    # and where they DON'T, the residual is the cost of a mid-stage provisioning lag.
    print("\nEqual-per-replica-load comparisons (sorted by RPS/rep):")
    print(f"{'RPS/rep':>8} {'stg':>4} {'RPS':>4} {'reps':>5} {'lat_mean':>9} {'lat_p95':>8}")
    for r in sorted(rows, key=lambda x: x["rps_per_rep"]):
        print(f"{r['rps_per_rep']:>8.2f} {r['stage']:>4} {r['rate']:>4} {r['reps']:>5.2f} "
              f"{r['lat_mean']:>9.3f} {r['lat_p95']:>8.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
