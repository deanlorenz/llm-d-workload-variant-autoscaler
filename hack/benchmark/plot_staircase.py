#!/usr/bin/env python3
"""Scratch plot for the TA staircase shakedown run.

Renders two panels:
  (top)    decode replicas (ready + desired) over time, with RPS load stages
           shaded behind, and the scale-up event marked.
  (bottom) per-stage client latency (request latency + TTFT means, log scale).

Run: uv run --with matplotlib --with pyyaml python plot_staircase.py <run_dir>
"""
import json
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

RUN = sys.argv[1] if len(sys.argv) > 1 else "."
RES = f"{RUN}/results/inference-perf-1785724033-d5lhav_1"
PROC = f"{RES}/metrics/processed"


def load(p):
    with open(p) as f:
        return json.load(f)


def parse_ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# ---- replica timeseries ----
ts = load(f"{PROC}/replica_status_timeseries.json")["snapshots"]
t0 = parse_ts(ts[0]["timestamp"])
secs, ready, desired = [], [], []
for s in ts:
    c = s["controllers"][0]
    secs.append((parse_ts(s["timestamp"]) - t0).total_seconds())
    ready.append(c["ready_replicas"])
    desired.append(c["desired_replicas"])

# ---- harness / stage timing (harness_start as stage t0) ----
# stages: 5 / 12 / 5 RPS, 360s each, back-to-back from harness_start.
meta = open(f"{RES}/run_metadata.yaml").read()
h_start = None
for line in meta.splitlines():
    if line.startswith("harness_start:"):
        h_start = parse_ts(line.split('"')[1].replace("+00:00", "Z").replace(" ", ""))
# harness_start is ~1s before first replica snapshot; offset in replica-plot seconds
hs_off = (h_start - t0).total_seconds() if h_start else 0.0
STAGES = [(5, 0, 360), (12, 360, 720), (5, 720, 1080)]

# ---- per-stage latency ----
stage_lat, stage_ttft, stage_rate = [], [], []
for i in range(3):
    d = load(f"{RES}/stage_{i}_lifecycle_metrics.json")
    lat = d["successes"]["latency"]
    stage_lat.append(lat["request_latency"]["mean"])
    stage_ttft.append(lat["time_to_first_token"]["mean"])
    stage_rate.append(d["load_summary"]["requested_rate"])

# ============ figure ============
fig, (ax0, ax1) = plt.subplots(
    2, 1, figsize=(11, 8), gridspec_kw={"height_ratios": [2, 1]}
)

# --- panel 0: replicas + load bands ---
band_colors = {5: "#e8f0fe", 12: "#fde8e8"}
for rate, a, b in STAGES:
    ax0.axvspan(a + hs_off, b + hs_off, color=band_colors[rate], zorder=0)
    ax0.text((a + b) / 2 + hs_off, 2.42, f"{rate} RPS",
             ha="center", va="center", fontsize=11, fontweight="bold", color="#333")

ax0.step(secs, desired, where="post", color="#c0392b", lw=2.2,
         label="desired replicas (WVA→KEDA)", zorder=3)
ax0.step(secs, ready, where="post", color="#1a6", lw=2.6,
         label="ready replicas", zorder=4)

# mark scale-up: first index where desired jumps to 2
for i in range(1, len(desired)):
    if desired[i] == 2 and desired[i - 1] == 1:
        ax0.annotate("scale-up decided\n(desired 1→2)",
                     xy=(secs[i], 2), xytext=(secs[i] - 250, 1.45),
                     fontsize=9, color="#c0392b",
                     arrowprops=dict(arrowstyle="->", color="#c0392b"))
        break
for i in range(1, len(ready)):
    if ready[i] == 2 and ready[i - 1] == 1:
        ax0.annotate("pod ready\n(~92 s startup)",
                     xy=(secs[i], 2), xytext=(secs[i] + 40, 1.35),
                     fontsize=9, color="#1a6",
                     arrowprops=dict(arrowstyle="->", color="#1a6"))
        break

ax0.set_ylim(0.8, 2.6)
ax0.set_yticks([1, 2])
ax0.set_ylabel("decode replicas")
ax0.set_xlim(0, max(secs))
ax0.set_title("TA staircase shakedown — decode autoscaling vs. load (dhl-wva-209, 2026-08-03)")
handles = ax0.get_legend_handles_labels()[0] + [
    Patch(color=band_colors[5], label="5 RPS stage"),
    Patch(color=band_colors[12], label="12 RPS stage"),
]
ax0.legend(handles=handles, loc="upper right", fontsize=8, ncol=2)
ax0.grid(axis="y", ls=":", alpha=0.5)
note = ("collection window ended before scale-down; 2→1 occurred later "
        "(HPA stabilization + controller anti-flap)")
ax0.text(0.01, -0.13, note, transform=ax0.transAxes, fontsize=8, style="italic", color="#666")

# --- panel 1: per-stage latency ---
x = range(3)
labels = [f"stage {i}\n{int(r)} RPS" for i, r in enumerate(stage_rate)]
w = 0.38
b1 = ax1.bar([i - w / 2 for i in x], stage_lat, w, label="request latency (mean)", color="#4c72b0")
b2 = ax1.bar([i + w / 2 for i in x], stage_ttft, w, label="TTFT (mean)", color="#dd8452")
ax1.set_yscale("log")
ax1.set_xticks(list(x))
ax1.set_xticklabels(labels)
ax1.set_ylabel("seconds (log)")
ax1.set_title("Per-stage client latency — TTFT spike at 12 RPS = single-replica queueing before scale-up")
ax1.legend(fontsize=8)
ax1.grid(axis="y", ls=":", alpha=0.5)
for bars in (b1, b2):
    for r in bars:
        ax1.annotate(f"{r.get_height():.1f}s", (r.get_x() + r.get_width() / 2, r.get_height()),
                     ha="center", va="bottom", fontsize=8)

fig.tight_layout()
out = f"{RUN}/staircase_shakedown.png"
fig.savefig(out, dpi=130, bbox_inches="tight")
print(f"wrote {out}")
