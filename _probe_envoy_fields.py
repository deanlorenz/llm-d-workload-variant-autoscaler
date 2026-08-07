"""Throwaway probe: what can an envoy-only ladder bundle actually support?

Dean's question: per_request_lifecycle_metrics.json is 0 bytes (harness OOM), so what can
we still build? Three calibrations decide it.

  1. Does envoy DURATION agree with the harness's own request_latency, per stage? If yes,
     the envoy trace is a drop-in for arrival/departure/L(t).
  2. Can BYTES_SENT stand in for per-request output tokens? Test per stage against the
     harness's output_len distribution -- not pooled, which mixes 8 different load levels.
  3. TTFT is gone per request but present per stage as 14 quantiles. Inverting those gives
     the wait-quality band FRACTIONS panel 1a needs, without per-request tags. Check that
     the quantile grid is dense enough at the band edges to invert honestly.

Read-only. No output files. Usage: ./.venv/bin/python _probe_envoy_fields.py
"""
import datetime as dt
import json
import re

RUN = ("/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark/"
       "dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1")
LOG = RUN + "/logs/igw_pods.log"

LINE = re.compile(
    r'\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)Z\] "POST /v1/(?:chat/)?completions [^"]*" '
    r'(\d{3}) (\S+) \S+ \S+ "[^"]*" (\d+) (\d+) (\d+) (\S+) '
    r'"[^"]*" "[^"]*" "[^"]*" "[^"]*" "([^"]*)"')

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
COUNTS = [600, 1500, 2400, 3000, 3600, 4500, 6000, 600]
RPS = [2, 5, 8, 10, 12, 15, 20, 2]
# render_real_trace.WAIT_EDGES -- the wait-quality bands panel 1a stacks.
WAIT_EDGES = [1.0, 5.0, 15.0, 60.0]


def to_epoch(s):
    d = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=dt.timezone.utc)
    return (d - EPOCH).total_seconds()


def pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


recs = []
with open(LOG, errors="replace") as fh:
    for ln in fh:
        m = LINE.search(ln)
        if not m:
            continue
        t = to_epoch(m.group(1))
        if not (to_epoch("2026-08-07T20:41:00.000") <= t
                <= to_epoch("2026-08-07T21:25:00.000")):
            continue
        if m.group(2) != "200":
            continue
        recs.append(dict(t_arr=t, tx=int(m.group(5)), dur=int(m.group(6)),
                         usts=int(m.group(7)), host=m.group(8)))
recs.sort(key=lambda r: r["t_arr"])
assert len(recs) == sum(COUNTS), f"count identity fails: {len(recs)}"

stages, i = [], 0
for k, n in enumerate(COUNTS):
    stages.append(recs[i:i + n])
    i += n

harness = [json.load(open(f"{RUN}/stage_{k}_lifecycle_metrics.json")) for k in range(8)]

# --- 1. envoy DURATION vs the harness's own request_latency, per stage
print("=== 1. envoy DURATION vs harness request_latency (s), per stage ===")
print("stg RPS      n   envoy_mean  harness_mean   delta%   envoy_p95  harness_p95  delta%")
for k, st in enumerate(stages):
    lat = harness[k]["successes"]["latency"]["request_latency"]
    em = sum(r["dur"] for r in st) / len(st) / 1000.0
    ep = pct([r["dur"] for r in st], 0.95) / 1000.0
    hm, hp = lat["mean"], lat["p95"]
    print(f"{k:3d} {RPS[k]:4d} {len(st):6d} {em:11.3f} {hm:13.3f} "
          f"{100*(em-hm)/hm:+8.2f} {ep:11.3f} {hp:12.3f} {100*(ep-hp)/hp:+8.2f}")

# --- 2. BYTES_SENT as an output-token proxy, per stage
print("\n=== 2. bytes_sent vs harness output_len, per stage ===")
print("       ---- bytes_sent ----   ---- output_len (harness) ----   implied B/tok")
print("stg    p05     p50     p95    p05    p50    p95   p95/p05     at p50   spread_ratio")
for k, st in enumerate(stages):
    ol = harness[k]["successes"]["output_len"]
    b5, b50, b95 = (pct([r["tx"] for r in st], q) for q in (0.05, 0.5, 0.95))
    o5, o50, o95 = ol["p5"], ol["median"], ol["p95"]
    b_spread = b95 / b5
    o_spread = o95 / o5
    print(f"{k:3d} {b5:7d} {b50:7d} {b95:7d} {o5:6.0f} {o50:6.0f} {o95:6.0f} "
          f"{o_spread:9.3f} {b50/o50:10.1f} {b_spread/o_spread:13.3f}")
print("\n  spread_ratio ~ 1.0 => bytes_sent tracks output tokens request-by-request.")
print("  spread_ratio << 1.0 => bytes_sent is compressed relative to token count, so it")
print("  cannot rank requests by size and is only usable as a stage-level total.")

# --- 3. Can we invert the per-stage TTFT quantiles onto panel 1a's band edges?
print("\n=== 3. per-stage TTFT quantiles vs panel 1a band edges ===")
QG = [("min", 0.0), ("p0.1", 0.001), ("p1", 0.01), ("p5", 0.05), ("p10", 0.10),
      ("p25", 0.25), ("median", 0.50), ("p75", 0.75), ("p90", 0.90),
      ("p95", 0.95), ("p99", 0.99), ("p99.9", 0.999), ("max", 1.0)]
print(f"band edges (s): {WAIT_EDGES}")
print("stg RPS   ttft_p50   ttft_p95   ttft_max   inferred band fractions "
      "(<1s, <5s, <15s, <60s, >=60s)")
for k in range(8):
    tt = harness[k]["successes"]["latency"]["time_to_first_token"]
    pts = [(tt[name], q) for name, q in QG if tt.get(name) is not None]
    pts.sort()
    fr, prev = [], 0.0
    for e in WAIT_EDGES:
        below = [q for v, q in pts if v <= e]
        cum = max(below) if below else 0.0
        fr.append(cum - prev)
        prev = cum
    fr.append(1.0 - prev)
    print(f"{k:3d} {RPS[k]:4d} {tt['median']:9.3f} {tt['p95']:10.3f} {tt['max']:10.3f}   "
          + "  ".join(f"{x:5.1%}" for x in fr))
print("\n  Fractions are read off a 13-point quantile grid, so each is quantized to the")
print("  grid: exact where an edge falls between two published quantiles, coarse where a")
print("  whole band sits inside one gap (e.g. everything between p95 and p99).")

# --- bonus: usts, now that we know it is not TTFT
print("\n=== 4. what usts (x-envoy-upstream-service-time) actually is ===")
u = [r["usts"] for r in recs]
print(f"usts p05={pct(u,0.05)} p50={pct(u,0.5)} p95={pct(u,0.95)} max={max(u)} ms")
for k, st in enumerate(stages):
    tt = harness[k]["successes"]["latency"]["time_to_first_token"]
    print(f"  stg {k} @ {RPS[k]:2d} RPS: usts p50={pct([r['usts'] for r in st],0.5):5d} ms "
          f"vs harness TTFT p50={1000*tt['median']:8.1f} ms  "
          f"ratio={pct([r['usts'] for r in st],0.5)/(1000*tt['median']):.4f}")
