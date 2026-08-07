#!/usr/bin/env python3
"""Recover a per-request trace for the 2026-08-07 ladder run from istio-proxy access logs.

Why this exists: the harness was OOMKilled while serialising
`per_request_lifecycle_metrics.json`, which is 0 bytes. The usual per-request source for
this run is gone. But every request traversed the inference gateway, and istio-proxy's
access log was captured into `logs/igw_pods.log` as part of the normal harness log dump.
That log contains one line per request for all 22,200 requests, and it is a STRICTLY
BETTER trace than the lost file in three respects:

  1. Timestamps are wall-clock UTC with millisecond resolution. The harness file used a
     monotonic clock with an unknown origin, which had to be anchored by hand against the
     run log (see the earlier scratch-poc handoff, "the clock trap"). Envoy needs no anchor,
     so per-request data joins directly to controller logs and HPA events.
  2. It records UPSTREAM_HOST -- which decode pod actually served each request. The harness
     file never had routing attribution at all.
  3. `bytes_sent` is a tokenizer-independent proxy for response size, so it is immune to the
     inference-perf output-token defect that makes every reported `output_len`,
     `time_per_output_token`, `inter_token_latency` and `normalized_time_per_output_token`
     unusable for this run.

What it does NOT recover: per-request TTFT and an exact per-request output-token count.
Envoy sees one duration per request, not the token stream. Those survive only as
server-side histogram buckets in `metrics/raw/*_metrics.log`
(`vllm:time_to_first_token_seconds_bucket`, `vllm:request_generation_tokens_bucket`).

Validation performed against the surviving stage aggregates:
  * 22,200 in-window POSTs vs 22,200 harness successes -- exact.
  * mean duration 8817 ms vs 8850 ms predicted from the request-weighted stage means (0.37%).
  * bytes_sent p50 implies 511 output tokens at ~299 B/token vs a true mean of 512 (0.2%).

Stage boundaries are derived by partitioning the sorted arrival series on the CUMULATIVE
per-stage request counts, not by anchoring to a start time and accumulating durations. The
anchor approach was wrong by 52 s on this run: the run log implies load starts at 20:42:36
but the first request actually arrives at 20:41:44.330. Partitioning is self-validating --
the observed rate within each derived window reproduces the configured ladder
(1.95, 4.87, 7.76, 9.69, 11.66, 14.52, 19.32, 2.01 against 2, 5, 8, 10, 12, 15, 20, 2).

THE DURABILITY CAVEAT, which decides whether this source can be relied on at all: the access
log lives in the gateway container's stdout, subject to kubelet log rotation
(`containerLogMaxSize` 10Mi x `containerLogMaxFiles` 5 by default, so ~50Mi retained). Access
lines cost ~541 bytes each, i.e. ~19,400 requests per 10Mi file. The gateway pod is shared,
long-lived infra that accumulates EVERY run: 5,002 lines on 07-30, 15,081 on 08-03, 38,093 on
08-07, and it was already at 31.5 MB (~63% of retention) when this run was harvested.

Rotation evicts oldest-first, so what goes first is the START of the run window -- the low-rate
stages and the initial scale-up. `assign_stages` therefore hard-fails on the count identity
rather than warning: a truncated series produces a silently SHIFTED grid, not a partial one.

For this run the identity holds exactly (22,200 == 22,200) and the log begins at container boot,
so nothing was evicted. Once harvested to disk the trace is safe; the exposure is entirely on
future runs and on anything not yet copied off the cluster.

Usage:
    python3 envoy_per_request.py --stage-grid          # boundaries + per-stage summary
    python3 envoy_per_request.py --csv  > trace.csv
    python3 envoy_per_request.py --jsonl > trace.jsonl
    python3 envoy_per_request.py --by-pod              # routing attribution per stage
    python3 envoy_per_request.py --rotation-budget     # eviction headroom for the NEXT run
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

RUN = ("dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1")
LOG = f"{RUN}/logs/igw_pods.log"

# Configured ladder: (rate, request_count). Counts are rate * 300 s, and they sum to the
# 22,200 the harness reported, which is what makes the cumulative partition exact.
STAGES = [(2, 600), (5, 1500), (8, 2400), (10, 3000),
          (12, 3600), (15, 4500), (20, 6000), (2, 600)]

# Authoritative IP -> pod, from the metrics collector's own curl targets
# (metrics_collection.log / metrics/raw/collection_debug.log). pod_status.txt is a POST-RUN
# snapshot and lists only the one surviving decode pod, so it cannot supply this on its own.
# IPs are recycled across pods over time -- 10.130.6.50 was a gpu-reservation pod -- so this
# mapping is only valid for this run's window.
POD_BY_IP = {
    "10.130.2.174": "decode-97vw2",
    "10.129.9.245": "decode-db6cw",
    "10.130.6.54": "decode-qqbbn",
    "10.128.9.37": "decode-k9hkl",
    "10.130.6.53": "decode-wf2rf",
}

# Envoy's default access-log format. Anchored on the quoted groups rather than split on
# whitespace, because the user-agent field ("Python/3.12 aiohttp/3.13.5") contains a space
# and would shift every positional index after it.
LINE = re.compile(
    r"^\[pod/(?P<gw>[^/]+)/[^\]]+\]\s+"
    r"\[(?P<start>[^\]]+)\]\s+"
    r'"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<proto>[^"]*)"\s+'
    r"(?P<code>\d+)\s+(?P<flags>\S+)\s+(?P<details>\S+)\s+(?P<term>\S+)\s+"
    r'"(?P<transport_fail>[^"]*)"\s+'
    r"(?P<bytes_rx>\d+)\s+(?P<bytes_tx>\d+)\s+(?P<duration>\d+)\s+(?P<upstream_ms>\S+)\s+"
    r'"(?P<xff>[^"]*)"\s+"(?P<ua>[^"]*)"\s+"(?P<reqid>[^"]*)"\s+'
    r'"(?P<authority>[^"]*)"\s+"(?P<upstream>[^"]*)"'
)

# The gateway pod is 8 days old, so its log spans a week of unrelated traffic. Bound to the
# run. One stray /v1/completions at 20:02:12 (a pre-run probe) falls outside this and is
# excluded by the lower bound; keep the bound tight rather than filtering by hand.
WINDOW_LO = datetime(2026, 8, 7, 20, 30, tzinfo=timezone.utc)
WINDOW_HI = datetime(2026, 8, 7, 21, 30, tzinfo=timezone.utc)


def parse(path=LOG):
    """Yield one dict per completion request inside the run window, sorted by arrival."""
    recs = []
    for line in open(path, errors="replace"):
        m = LINE.match(line)
        if not m or m["path"] != "/v1/completions":
            continue
        t = datetime.strptime(m["start"], "%Y-%m-%dT%H:%M:%S.%f%z")
        if not (WINDOW_LO <= t <= WINDOW_HI):
            continue
        ip = m["upstream"].rsplit(":", 1)[0]
        recs.append({
            "arrival_utc": t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "arrival_epoch": t.timestamp(),
            "duration_ms": int(m["duration"]),
            "upstream_ms": m["upstream_ms"],
            "bytes_rx": int(m["bytes_rx"]),
            "bytes_tx": int(m["bytes_tx"]),
            "code": int(m["code"]),
            "flags": m["flags"],
            "request_id": m["reqid"],
            "upstream_ip": ip,
            "pod": POD_BY_IP.get(ip, ip),
        })
    recs.sort(key=lambda r: r["arrival_epoch"])
    return recs


def assign_stages(recs, allow_partial=False):
    """Tag each record with its stage by partitioning on cumulative per-stage counts.

    HARD GATE on the count identity, because a short series is not merely incomplete here --
    it is actively misleading. Partitioning is positional, so if container log rotation
    evicted the first N requests, every surviving request is assigned to a stage that is too
    early, and the grid silently shifts by N/rate seconds across the whole run. There is no
    local symptom: the per-stage rates still look plausible. A truncated trace must therefore
    fail loudly rather than produce a shifted grid.

    Rotation eats OLDEST first, so the losses land at the start of the run window -- the
    low-rate stages and the initial scale-up. That is the most valuable region for autoscaling
    analysis, so the bias is against exactly what we want to measure.

    The identity is a sound completeness test: the harness independently reports how many
    requests it issued, so in-window count == that number proves nothing was evicted.
    """
    want = sum(n for _, n in STAGES)
    if len(recs) != want and not allow_partial:
        raise SystemExit(
            f"REFUSING to assign stages: {len(recs)} requests in window, ladder configures "
            f"{want} (delta {len(recs) - want:+d}).\n"
            f"Stage assignment is positional, so a truncated trace yields a SHIFTED grid, not\n"
            f"a partial one. Likely cause is container log rotation evicting the start of the\n"
            f"window (see the module docstring). Re-run with --allow-partial only if you have\n"
            f"another way to anchor the stages, and treat the grid as unverified."
        )
    i = 0
    for s, (rate, n) in enumerate(STAGES):
        for r in recs[i:i + n]:
            r["stage"] = s
            r["stage_rate"] = rate
        i += n
    for r in recs[i:]:            # only reachable when the count check above failed
        r["stage"] = len(STAGES) - 1
        r["stage_rate"] = STAGES[-1][0]
    return recs


def stage_grid(recs):
    """[(stage, rate, n, t0, t1, observed_rps)] using each stage's own first/last arrival."""
    out = []
    by = defaultdict(list)
    for r in recs:
        by[r["stage"]].append(r)
    for s, (rate, _) in enumerate(STAGES):
        g = by.get(s)
        if not g:
            continue
        t0, t1 = g[0]["arrival_epoch"], g[-1]["arrival_epoch"]
        # End the window at the next stage's first arrival so the grid is gapless -- using
        # this stage's own last arrival would leave the inter-arrival gap unattributed.
        nxt = by.get(s + 1)
        t_end = nxt[0]["arrival_epoch"] if nxt else t1
        span = t_end - t0
        out.append((s, rate, len(g), t0, t_end, len(g) / span if span else float("nan")))
    return out


def fmt(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%H:%M:%S.%f")[:-3]


# Kubelet defaults. Worth re-checking against the cluster's KubeletConfig before trusting the
# headroom number -- if the cluster narrows either value, the real budget is smaller.
ROT_MAX_SIZE = 10 * 1024 * 1024
ROT_MAX_FILES = 5


def rotation_budget(path=LOG):
    """Report how many more requests fit before rotation starts evicting the run's start.

    Measures bytes-per-request from this log rather than assuming, since the access-log line
    width depends on the format and on header sizes.
    """
    import os
    total = os.path.getsize(path)
    n = acc = 0
    for line in open(path, errors="replace"):
        m = LINE.match(line)
        if m and m["path"] == "/v1/completions":
            n += 1
            acc += len(line)
    if not n:
        print(f"no completion requests in {path}", file=sys.stderr)
        return 1
    per = acc / n
    budget = ROT_MAX_SIZE * ROT_MAX_FILES
    print(f"{path}")
    print(f"  size on disk        {total / 1e6:>10.1f} MB")
    print(f"  access lines        {acc / 1e6:>10.1f} MB over {n} requests "
          f"({per:.0f} B/request)")
    print(f"  retention budget    {budget / 1e6:>10.1f} MB "
          f"({ROT_MAX_FILES} x {ROT_MAX_SIZE // (1024 * 1024)}Mi kubelet default)")
    print(f"  consumed            {100 * total / budget:>10.1f} %")
    head = max(0, budget - total)
    print(f"  headroom            {head / 1e6:>10.1f} MB "
          f"= ~{int(head / per)} more requests")
    print(f"\n  per 10Mi file       ~{int(ROT_MAX_SIZE / per)} requests")
    print("  Eviction is oldest-first, so overflow silently removes the START of the run\n"
          "  window (low-rate stages, initial scale-up). Verify the count identity after\n"
          "  every harvest; harvest promptly, and treat an un-copied log as at risk.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--jsonl", action="store_true")
    ap.add_argument("--stage-grid", action="store_true")
    ap.add_argument("--by-pod", action="store_true")
    ap.add_argument("--rotation-budget", action="store_true",
                    help="report container-log eviction headroom for the next run")
    ap.add_argument("--allow-partial", action="store_true",
                    help="proceed despite a failed count identity; grid becomes UNVERIFIED")
    a = ap.parse_args()

    if a.rotation_budget:
        return rotation_budget(a.log)

    recs = assign_stages(parse(a.log), allow_partial=a.allow_partial)
    if not recs:
        print(f"no completion requests parsed from {a.log}", file=sys.stderr)
        return 1

    if a.jsonl:
        for r in recs:
            print(json.dumps(r))
        return 0
    if a.csv:
        w = csv.DictWriter(sys.stdout, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)
        return 0

    if a.by_pod:
        print("Requests served per decode pod, per stage (routing attribution):")
        pods = sorted({r["pod"] for r in recs})
        print(f"{'stg':>3} {'RPS':>4} " + "".join(f"{p:>15}" for p in pods))
        for s, rate, _, _, _, _ in stage_grid(recs):
            c = Counter(r["pod"] for r in recs if r["stage"] == s)
            print(f"{s:>3} {rate:>4} " + "".join(f"{c.get(p, 0):>15}" for p in pods))
        return 0

    grid = stage_grid(recs)
    print(f"Per-request trace recovered from {a.log}")
    print(f"  requests {len(recs)}   "
          f"window {fmt(recs[0]['arrival_epoch'])} -> {fmt(recs[-1]['arrival_epoch'])}")
    codes = Counter(r["code"] for r in recs)
    flags = Counter(r["flags"] for r in recs)
    print(f"  codes {dict(codes)}   envoy flags {dict(flags)}")

    print(f"\n{'stg':>3} {'RPS':>4} {'n':>5} {'start':>13} {'end':>13} {'obs RPS':>8} "
          f"{'dur_mean':>9} {'dur_p95':>8} {'bytes_tx_p50':>13}")
    for s, rate, n, t0, t1, obs in grid:
        g = [r for r in recs if r["stage"] == s]
        d = sorted(r["duration_ms"] for r in g)
        bt = sorted(r["bytes_tx"] for r in g)
        print(f"{s:>3} {rate:>4} {n:>5} {fmt(t0):>13} {fmt(t1):>13} {obs:>8.2f} "
              f"{sum(d) / len(d) / 1000:>9.3f} {d[int(len(d) * .95)] / 1000:>8.3f} "
              f"{bt[len(bt) // 2]:>13}")

    print("\nGrid is self-validating: observed RPS must reproduce the configured ladder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
