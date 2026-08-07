#!/usr/bin/env python3
"""Time-weighted SERVING replica count per stage, derived from routing rather than the controller.

Why this exists: the obvious source for "how many replicas did stage N run on" is the
controller log's `curr` field, sampled once per 60 s optimisation cycle. That number is
wrong for a latency model in two ways.

  1. Resolution. `curr` changes at 60 s granularity, so a replica that became Ready at
     21:15:54 is first observed at 21:16:40 -- or, worse, is credited from 21:14:39 if the
     deployment's replica count moved before the pod could serve.
  2. Meaning. `curr` is what the controller reads off the workload object. A pod counted
     there may be Pending, pulling an image, or loading the model. It contributes to the
     count without contributing any capacity, which is exactly backwards for explaining
     latency.

The gateway access log settles it directly: a replica is serving when the gateway is sending
it requests. `UPSTREAM_HOST` gives that per request, so each pod's serving interval is
[first arrival, last arrival] and the time-weighted count over a stage window is the sum of
per-pod overlaps divided by the window span. Fully independent of the controller.

Caveat on the interval definition: a pod that is up but transiently receives nothing (the
scheduler preferring warmer peers) still counts as serving between its first and last
arrival, which is the behaviour we want -- it has capacity even when idle. But a pod
draining at the end of a scale-down is credited until its final request, so the count lags
termination slightly. At 2 RPS with 5 requests/s/pod that is worth a couple of seconds.

Usage:
    python3 serving_replicas.py            # per-stage table, both estimates side by side
    python3 serving_replicas.py --spans    # per-pod serving intervals
"""
import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone

from envoy_per_request import STAGES, assign_stages, fmt, parse

# Time-weighted replica counts from the controller log's `curr` field, for comparison.
# Derived by sampling `curr` at each 60 s optimisation cycle and weighting by the portion of
# each stage window the sample covers. Kept here as a literal because reproducing it needs
# the controller log, which is a separate artefact.
CURR_WEIGHTED = [2.27, 2.93, 2.10, 3.00, 3.00, 3.00, 3.61, 2.73]


def spans(recs):
    """pod -> (first_arrival_epoch, last_arrival_epoch) over the whole run."""
    out = {}
    for r in recs:
        p = r["pod"]
        t = r["arrival_epoch"]
        if p not in out:
            out[p] = [t, t]
        else:
            out[p][1] = t
    return {p: tuple(v) for p, v in out.items()}


def weighted(recs):
    """[(stage, rate, t0, t1, span, serving_weight, per_pod_overlap)]"""
    by = defaultdict(list)
    for r in recs:
        by[r["stage"]].append(r)
    sp = spans(recs)
    out = []
    for s, (rate, _) in enumerate(STAGES):
        g = by.get(s)
        if not g:
            continue
        t0 = g[0]["arrival_epoch"]
        nxt = by.get(s + 1)
        t1 = nxt[0]["arrival_epoch"] if nxt else g[-1]["arrival_epoch"]
        span = t1 - t0
        per = {}
        for p, (a, b) in sp.items():
            ov = max(0.0, min(b, t1) - max(a, t0))
            if ov > 0:
                per[p] = ov
        out.append((s, rate, t0, t1, span,
                    sum(per.values()) / span if span else float("nan"), per))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spans", action="store_true")
    a = ap.parse_args()

    recs = assign_stages(parse())
    if a.spans:
        print(f"{'pod':>15} {'first':>13} {'last':>13} {'span_s':>8} {'n':>6}")
        n = defaultdict(int)
        for r in recs:
            n[r["pod"]] += 1
        for p, (x, y) in sorted(spans(recs).items(), key=lambda kv: kv[1][0]):
            print(f"{p:>15} {fmt(x):>13} {fmt(y):>13} {y - x:>8.1f} {n[p]:>6}")
        return 0

    rows = weighted(recs)
    print("Time-weighted replica count per stage: routing-derived vs controller `curr`")
    print(f"\n{'stg':>3} {'RPS':>4} {'span_s':>7} {'serving':>8} {'curr':>6} {'delta':>7} "
          f"{'RPS/rep (serving)':>18} {'RPS/rep (curr)':>15}")
    for s, rate, _, _, span, w, _ in rows:
        c = CURR_WEIGHTED[s]
        print(f"{s:>3} {rate:>4} {span:>7.1f} {w:>8.2f} {c:>6.2f} {w - c:>+7.2f} "
              f"{rate / w:>18.2f} {rate / c:>15.2f}")

    print("\nPer-pod seconds of serving overlap inside each stage window:")
    pods = sorted({r["pod"] for r in recs})
    print(f"{'stg':>3} " + "".join(f"{p:>15}" for p in pods))
    for s, _, _, _, _, _, per in rows:
        print(f"{s:>3} " + "".join(f"{per.get(p, 0):>15.0f}" for p in pods))
    return 0


if __name__ == "__main__":
    sys.exit(main())
