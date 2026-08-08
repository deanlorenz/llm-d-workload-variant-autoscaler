#!/usr/bin/env python3
"""Aggregate real vLLM KV-cache utilisation per workload rung.

WHY THIS EXISTS
---------------
The planning doc's dwell-run decision rule ("both rungs read kv ~0.67 => rate
invariance is confirmed") needs *real* engine KV per rung. It cannot be answered
from the controller log: the analyzer's `util` field is NOT kv-cache utilisation
(this run had real kv 0.9987 while the saturation analyzer reported util 0.360),
so reading `util` would answer a different question and look like it answered
this one.

The only true source is the per-pod vLLM /metrics scrapes under
`metrics/raw/<pod>_<epoch>_metrics.log`. Note the metric name: vLLM 0.20.2 emits
`vllm:kv_cache_usage_perc`, NOT `gpu_cache_usage_perc`.

Not every scrape is usable. Pods that are still starting return a 503
`ServiceUnavailable` JSON body instead of a metrics page, and those must be
counted and reported rather than silently skipped -- during a scale-up burst the
unusable fraction is exactly the interesting period, so a silent skip would bias
every rung's mean toward its calm end.

Rung boundaries are derived from the harness start time plus the profile's own
stage durations, so this stays correct if the profile changes.

Read-only: reads the results dir, writes nothing.

Usage: python3 kv_per_rung.py <results_dir> [--stages 5:120,14:180,20:360,26:360,2:720]
"""
import argparse
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

FNAME_PAT = re.compile(r"^(?P<pod>.+)_(?P<epoch>\d{10})_metrics\.log$")
# Prometheus text format: `vllm:kv_cache_usage_perc{labels...} <float>`
KV_PAT = re.compile(r"^vllm:kv_cache_usage_perc\{[^}]*\}\s+(?P<val>[0-9.eE+-]+)\s*$")
RUNNING_PAT = re.compile(r"^vllm:num_requests_running\{[^}]*\}\s+(?P<val>[0-9.eE+-]+)\s*$")
WAITING_PAT = re.compile(r"^vllm:num_requests_waiting\{[^}]*\}\s+(?P<val>[0-9.eE+-]+)\s*$")


def parse_stages(spec):
    out = []
    for part in spec.split(","):
        rate, dur = part.split(":")
        out.append((float(rate), int(dur)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--stages", default="5:120,14:180,20:360,26:360,2:720")
    args = ap.parse_args()

    rd = Path(args.results_dir).resolve()
    raw = rd / "metrics" / "raw"
    if not raw.is_dir():
        print(f"ERROR: {raw} not found", file=sys.stderr)
        return 1

    samples = []          # (epoch, pod, kv, running, waiting)
    unavailable = []      # epoch of 503 scrapes
    other = []            # scrapes with neither kv nor a 503 marker

    for f in raw.iterdir():
        m = FNAME_PAT.match(f.name)
        if not m:
            continue
        epoch = int(m.group("epoch"))
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        if "ServiceUnavailable" in text:
            unavailable.append(epoch)
            continue
        kv = running = waiting = None
        for line in text.splitlines():
            mm = KV_PAT.match(line)
            if mm:
                kv = float(mm.group("val"))
                continue
            mm = RUNNING_PAT.match(line)
            if mm:
                running = float(mm.group("val"))
                continue
            mm = WAITING_PAT.match(line)
            if mm:
                waiting = float(mm.group("val"))
        if kv is None:
            other.append(epoch)
            continue
        samples.append((epoch, m.group("pod"), kv, running, waiting))

    if not samples:
        print("ERROR: no usable kv samples", file=sys.stderr)
        return 1

    samples.sort()
    # Harness start: earliest scrape is the closest available proxy and is within
    # one scrape interval of the true start.
    t0 = min(e for e, *_ in samples + [(x,) for x in unavailable] if True)

    stages = parse_stages(args.stages)
    bounds = []
    acc = t0
    for rate, dur in stages:
        bounds.append((rate, acc, acc + dur))
        acc += dur

    def fmt(e):
        return datetime.fromtimestamp(e, timezone.utc).strftime("%H:%M:%S")

    print(f"usable kv scrapes: {len(samples)}   "
          f"503-unavailable: {len(unavailable)}   no-kv-other: {len(other)}")
    print(f"scrape span: {fmt(samples[0][0])} -> {fmt(samples[-1][0])}  (t0={fmt(t0)})")
    print()
    hdr = (f"{'rate':>5} {'window':>19} {'n':>4} {'pods':>5} "
           f"{'kv_mean':>8} {'kv_p50':>7} {'kv_p90':>7} {'kv_max':>7} "
           f"{'run':>6} {'wait':>7} {'503':>4}")
    print(hdr)
    print("-" * len(hdr))

    for rate, lo, hi in bounds:
        kvs = [kv for e, p, kv, r, w in samples if lo <= e < hi]
        pods = {p for e, p, kv, r, w in samples if lo <= e < hi}
        runs = [r for e, p, kv, r, w in samples if lo <= e < hi and r is not None]
        waits = [w for e, p, kv, r, w in samples if lo <= e < hi and w is not None]
        n503 = sum(1 for e in unavailable if lo <= e < hi)
        win = f"{fmt(lo)}-{fmt(hi)}"
        if not kvs:
            print(f"{rate:>5g} {win:>19} {0:>4} {0:>5} {'-':>8} {'-':>7} "
                  f"{'-':>7} {'-':>7} {'-':>6} {'-':>7} {n503:>4}")
            continue
        kvs_sorted = sorted(kvs)
        p90 = kvs_sorted[min(len(kvs_sorted) - 1, int(0.9 * len(kvs_sorted)))]
        print(f"{rate:>5g} {win:>19} {len(kvs):>4} {len(pods):>5} "
              f"{statistics.fmean(kvs):>8.3f} {statistics.median(kvs):>7.3f} "
              f"{p90:>7.3f} {max(kvs):>7.3f} "
              f"{(statistics.fmean(runs) if runs else 0):>6.1f} "
              f"{(statistics.fmean(waits) if waits else 0):>7.1f} {n503:>4}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
