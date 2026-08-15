#!/usr/bin/env python3
"""Standalone sanity-check render of per_request_estimated.json.

Not part of the autoscaling-viz toolchain -- a one-off scratch check to see
whether the estimate (real Envoy arrival/duration + histogram-conditional
TTFT/output-token estimate) produces a sane-looking panel before investing
in a real extract_real_trace.py source-format branch.
"""
import json
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1]
d = json.load(open(path))
reqs = d["requests"]
t0 = min(r["arrival_epoch"] for r in reqs)

by_stage = defaultdict(list)
for r in reqs:
    by_stage[r["stage"]].append(r)

fig, axes = plt.subplots(3, 1, figsize=(14, 12))

# Panel-1a-ish: arrival rate over time (10s bins), colored by e2e latency band
ax = axes[0]
bins = defaultdict(lambda: defaultdict(int))
def band(ms):
    if ms < 2000: return "<2s"
    if ms < 15000: return "2-15s"
    if ms < 30000: return "15-30s"
    if ms < 45000: return "30-45s"
    if ms < 60000: return "45-60s"
    return ">60s"
colors = {"<2s": "darkgreen", "2-15s": "yellowgreen", "15-30s": "gold",
          "30-45s": "orange", "45-60s": "orangered", ">60s": "darkred"}
for r in reqs:
    b = int((r["arrival_epoch"] - t0) // 10) * 10
    bins[b][band(r["e2e_duration_ms"])] += 1
xs = sorted(bins)
bottom = [0] * len(xs)
for label in ["<2s", "2-15s", "15-30s", "30-45s", "45-60s", ">60s"]:
    ys = [bins[x].get(label, 0) for x in xs]
    ax.bar(xs, ys, bottom=bottom, width=10, color=colors[label], label=label)
    bottom = [b + y for b, y in zip(bottom, ys)]
ax.set_title("1a-ish: request arrivals (10s bins), colored by e2e duration -- REAL data (Envoy)")
ax.set_ylabel("requests / 10s")
ax.legend(loc="upper right", fontsize=8)

# Panel-1b-ish: estimated output tokens/s over time (10s bins) -- THIS is the estimated part
ax = axes[1]
tok_bins = defaultdict(float)
for r in reqs:
    b = int((r["arrival_epoch"] - t0) // 10) * 10
    tok_bins[b] += r["output_tokens_estimated"]
xs = sorted(tok_bins)
ys = [tok_bins[x] / 10.0 for x in xs]
ax.plot(xs, ys, color="steelblue", lw=1.5)
ax.set_title("1b-ish: ESTIMATED output tok/s (10s bins) -- output_tokens_estimated is a stage-histogram draw, not measured")
ax.set_ylabel("est. output tok/s")

# Panel-extra: estimated TTFT per request over time, by stage
ax = axes[2]
for stage in sorted(by_stage):
    rs = by_stage[stage]
    xs = [(r["arrival_epoch"] - t0) for r in rs]
    ys = [r["ttft_estimated_ms"] for r in rs]
    ax.scatter(xs, ys, s=4, label=f"stage {stage} (rate={rs[0]['stage_rate']})")
ax.set_title("ESTIMATED TTFT per request, by stage -- expect flat bands (bucket-conditional draw), not real variance")
ax.set_xlabel("seconds since first arrival")
ax.set_ylabel("est. TTFT (ms)")
ax.legend(loc="upper right", fontsize=7, ncol=2)

plt.tight_layout()
out = sys.argv[2] if len(sys.argv) > 2 else "estimate_check.png"
plt.savefig(out, dpi=110)
print(f"wrote {out}")
print(f"requests: {len(reqs)}  stages: {sorted(by_stage)}  "
      f"stage sizes: {[len(by_stage[s]) for s in sorted(by_stage)]}")
