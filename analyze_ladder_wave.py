"""Per-pod arrival/departure oscillation on the 08-07 ladder run. Backs FINDINGS.md s11.1.

Started as a falsification test of the arm-B claim that saturation GATES the ~24 s departure wave:
arm B (kv~1.0) found peak departure-count autocorrelation +0.56 at lag 24 s in its single-pod
saturated window vs +0.14 unsaturated, so it predicts no wave on the ladder run, which never
exceeds kv 0.67. Pooled across pods that prediction holds. Resolved per pod it does not -- and
because the ladder has per-request pod attribution (arm B has none), arrivals can be separated
from departures, which is what identifies the mechanism as routing rather than cohort recycling.

Reads the inference gateway's istio-proxy access log, since this run's
per_request_lifecycle_metrics.json is 0 bytes (harness OOMKilled during serialisation).
Arrival = START_TIME; departure = START_TIME + DURATION_ms. No clock anchoring needed: envoy
timestamps are wall-clock UTC.

Read-only. No output files. Usage: ./.venv/bin/python analyze_ladder_wave.py
"""
import datetime as dt
import re
import sys

LOG = ("/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark/"
       "dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1/logs/igw_pods.log")

# [2026-08-07T20:41:44.330Z] "POST /v1/chat/completions HTTP/1.1" 200 - via_upstream - "-"
#   <bytes_rx> <bytes_tx> <duration_ms> <upstream_service_time> "<xff>" "<ua>" "<req-id>"
#   "<authority>" "<upstream_host>" ...
LINE = re.compile(
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)Z\] "POST /v1/(?:chat/)?completions [^"]*" '
    r'(\d{3}) (\S+) \S+ \S+ "[^"]*" (\d+) (\d+) (\d+) (\S+) '
    r'"[^"]*" "[^"]*" "[^"]*" "[^"]*" "([^"]*)"')

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def to_epoch(s):
    d = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=dt.timezone.utc)
    return (d - EPOCH).total_seconds()


# Handoff s3: the run's load starts at 20:41:44.330 UTC on 08-07 and the last stage ends
# 21:22:46.271. Take a generous window and let the count identity confirm it.
WIN_LO = to_epoch("2026-08-07T20:41:00.000")
WIN_HI = to_epoch("2026-08-07T21:25:00.000")

recs = []
n_line = n_win = n_non200 = 0
with open(LOG, errors="replace") as fh:
    for ln in fh:
        m = LINE.search(ln)
        if not m:
            continue
        n_line += 1
        t = to_epoch(m.group(1))
        if not (WIN_LO <= t <= WIN_HI):
            continue
        n_win += 1
        if m.group(2) != "200":
            n_non200 += 1
            continue
        recs.append(dict(
            t_arr=t,
            flags=m.group(3),
            bytes_rx=int(m.group(4)),
            bytes_tx=int(m.group(5)),
            dur_ms=int(m.group(6)),
            host=m.group(8),
        ))

recs.sort(key=lambda r: r["t_arr"])
for r in recs:
    r["t_dep"] = r["t_arr"] + r["dur_ms"] / 1000.0

print(f"parsed access lines: {n_line:,}   in-window: {n_win:,}   non-200 in-window: {n_non200}")
print(f"usable requests: {len(recs):,}   (handoff claims 22,200)")
if not recs:
    sys.exit("no records — check the regex against the log format")
print(f"arrival span: {recs[0]['t_arr']:.3f} .. {recs[-1]['t_arr']:.3f} "
      f"({recs[-1]['t_arr'] - recs[0]['t_arr']:.1f} s)")
flags = {}
for r in recs:
    flags[r["flags"]] = flags.get(r["flags"], 0) + 1
print(f"response flags: {flags}")

# --- stage grid by cumulative count (handoff s3: positional partition, NOT an anchor)
COUNTS = [600, 1500, 2400, 3000, 3600, 4500, 6000, 600]
RPS = [2, 5, 8, 10, 12, 15, 20, 2]
assert sum(COUNTS) == 22200
if len(recs) != 22200:
    print(f"\n!! COUNT IDENTITY FAILS: {len(recs)} != 22200 — grid is UNVERIFIED, "
          f"treat every stage number below as suspect")

stages = []
i = 0
for k, (n, rps) in enumerate(zip(COUNTS, RPS)):
    chunk = recs[i:i + n]
    if not chunk:
        break
    stages.append(dict(k=k, rps=rps, n=len(chunk), recs=chunk,
                       t0=chunk[0]["t_arr"], t1=chunk[-1]["t_arr"]))
    i += n


def autocorr(series, max_lag):
    n = len(series)
    m = sum(series) / n
    dev = [x - m for x in series]
    den = sum(d * d for d in dev)
    out = []
    for lag in range(1, max_lag + 1):
        if n - lag < 10:
            break
        num = sum(dev[j] * dev[j + lag] for j in range(n - lag))
        out.append((lag, num / den if den > 0 else 0.0))
    return out


def binned(times, t0, t1, w=1.0):
    nb = int((t1 - t0) / w) + 1
    b = [0] * nb
    for t in times:
        j = int((t - t0) / w)
        if 0 <= j < nb:
            b[j] += 1
    return b


def peak(ac, lo=5, hi=60):
    cand = [(l, v) for l, v in ac if lo <= l <= hi]
    return max(cand, key=lambda p: p[1]) if cand else (None, None)


MAXLAG = 60
print("\n=== departure-count autocorrelation, 1 s bins, per stage (all pods pooled) ===")
print("stg  RPS      n   dur_s   obs_rps   dep/s   peak_lag  peak_r   r@24s   arr peak_lag  arr_r")
for s in stages:
    deps = [r["t_dep"] for r in s["recs"]]
    t0, t1 = min(deps), max(deps)
    db = binned(deps, t0, t1)
    ac = autocorr(db, MAXLAG)
    pl, pr = peak(ac)
    r24 = dict(ac).get(24)
    ab = binned([r["t_arr"] for r in s["recs"]], s["t0"], s["t1"])
    aac = autocorr(ab, MAXLAG)
    apl, apr = peak(aac)
    dur = s["t1"] - s["t0"]
    print(f"{s['k']:3d} {s['rps']:4d} {s['n']:6d} {dur:7.1f} {s['n']/dur:9.2f} "
          f"{len(deps)/(t1-t0):7.2f} {pl:10d} {pr:+7.3f} "
          f"{(f'{r24:+.3f}' if r24 is not None else '   n/a'):>7} "
          f"{apl:12d} {apr:+6.3f}")

# --- per-pod within the two heaviest stages: the routing discriminator
print("\n=== per-pod departure autocorr, heaviest stages (routing vs recycling) ===")
for s in stages:
    hosts = {}
    for r in s["recs"]:
        hosts.setdefault(r["host"], []).append(r["t_dep"])
    print(f"\n  stage {s['k']} @ {s['rps']} RPS, {s['n']} requests, {len(hosts)} pods")
    print(f"    {'pod':22} {'n':>5}  {'DEPARTURES':>22}   {'ARRIVALS':>22}")
    print(f"    {'':22} {'':>5}  {'lag':>5}{'r':>8}{'r@24':>9}   "
          f"{'lag':>5}{'r':>8}{'r@24':>9}")
    arrs_by_host = {}
    for r in s["recs"]:
        arrs_by_host.setdefault(r["host"], []).append(r["t_arr"])
    for h, deps in sorted(hosts.items(), key=lambda kv: -len(kv[1])):
        if len(deps) < 200:
            print(f"    {h:22} {len(deps):5d}   (too few, skipped)")
            continue
        t0, t1 = min(deps), max(deps)
        ac = autocorr(binned(deps, t0, t1), MAXLAG)
        pl, pr = peak(ac)
        r24 = dict(ac).get(24)
        arrs = arrs_by_host[h]
        a0, a1 = min(arrs), max(arrs)
        aac = autocorr(binned(arrs, a0, a1), MAXLAG)
        apl, apr = peak(aac)
        ar24 = dict(aac).get(24)
        print(f"    {h:22} {len(deps):5d}  {pl:5d}{pr:+8.3f}"
              f"{(f'{r24:+.3f}' if r24 is not None else 'n/a'):>9}   "
              f"{apl:5d}{apr:+8.3f}"
              f"{(f'{ar24:+.3f}' if ar24 is not None else 'n/a'):>9}")

# --- the arm-B comparison needs the same instrument on a matched bin width.
# arm B used 1 s bins over ~155 s windows; ladder stages are ~305 s. Re-run the
# heaviest stage on a 155 s half-window so window length is not the difference.
print("\n=== window-length control: heaviest stage, first 155 s only ===")
for s in stages:
    if s["rps"] != 20:
        continue
    deps = sorted(r["t_dep"] for r in s["recs"])
    t0 = deps[0]
    half = [t for t in deps if t <= t0 + 155.0]
    ac = autocorr(binned(half, t0, t0 + 155.0), MAXLAG)
    pl, pr = peak(ac)
    r24 = dict(ac).get(24)
    print(f"  n={len(half)}  peak lag {pl} s  r={pr:+.3f}   "
          f"r@24s={(f'{r24:+.3f}' if r24 is not None else 'n/a')}")

# --- what a wave would need to beat: the noise floor of Poisson departures.
print("\n=== reference: |r| distribution over lags 5..60 s, heaviest stage ===")
for s in stages:
    if s["rps"] != 20:
        continue
    deps = [r["t_dep"] for r in s["recs"]]
    t0, t1 = min(deps), max(deps)
    ac = [v for l, v in autocorr(binned(deps, t0, t1), MAXLAG) if 5 <= l <= 60]
    ac_s = sorted(ac)
    n = len(ac)
    print(f"  n_lags={n}  min={ac_s[0]:+.3f}  p50={ac_s[n//2]:+.3f}  "
          f"p95={ac_s[int(0.95*n)]:+.3f}  max={ac_s[-1]:+.3f}")
    print(f"  1/sqrt(n_bins) white-noise scale = {(1.0/((t1-t0)**0.5)):.3f}")
