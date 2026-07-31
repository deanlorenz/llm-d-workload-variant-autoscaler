"""Scenario driver: generate traces, simulate, render PNG.

Calibration (token work-unit) is anchored to a real WVA decode-heavy benchmark
(Ofer's comparison-100x1000-16x20x24ext20): peak ~24 req/s, ~1000-token mean
work, per-backend concurrency C=100, service_rate ~= 1000/12 tokens/s so one
backend clears ~8.3 req/s, and ~90s replica boot. Held-constant knobs live in
GLOBAL below; only setup and the sizer vary per scenario.
"""

import json
import os

from sim import (gen_load, gen_supply_perfect, gen_supply_queue_aware,
                 run_closed_loop, Simulator, sample, summarize)
from plots import render, render_latency, render_cumulative

OUT = "out"
TR = "traces"
os.makedirs(OUT, exist_ok=True)
os.makedirs(TR, exist_ok=True)

# Held-constant across every scenario (see module docstring for provenance).
DURATION = 600.0
PEAK_RATE = 24.0
SIZE_MEAN = 1000.0            # tokens per request (mean; expo)
C = 100                       # per-backend concurrency limit
SERVICE_RATE = 1000.0 / 12.0  # tokens/s per in-service request (~83.3)
SAT_FRAC = 0.7                # usable concurrency = floor(0.7*C); vLLM goodput ceiling
HEADROOM = 1.2
SIZING_RANGE = 60.0           # sizer's estimation range (Prom range-vector)
DECISION_INTERVAL = 15.0      # how often the sizer recomputes desired count
DRAIN_TIME = 30.0             # queue-aware backlog-drain deadline
SETUP = 90.0                  # replica boot lag (setup-lag + queue-aware)
METRIC_WINDOW = 60.0          # HPA/KEDA metric avg_over_time window (trailing)
MAX_REPLICAS = 10             # KEDA maxReplicaCount (guide example: MAXPODS 10)
SAMPLE_INTERVAL = 0.25        # plot-grid resolution
REQ_RANGE = 15.0             # request-count averaging range (panels 1a/4-ish)
WORK_RANGE = 60.0            # work-rate averaging range (Prom-style, panel 1b)


def _load():
    return gen_load(pattern="bump", duration=DURATION, peak_rate=PEAK_RATE,
                    size_mean=SIZE_MEAN, size_dist="expo", seed=1)


def scenario_ideal():
    load = _load()
    supply = gen_supply_perfect(load, C=C, service_rate=SERVICE_RATE, setup=0.0,
                                drain=0.0, headroom=HEADROOM,
                                sizing_range=SIZING_RANGE,
                                decision_interval=DECISION_INTERVAL,
                                sat_frac=SAT_FRAC)
    json.dump(load, open(f"{TR}/load-bump.json", "w"))
    json.dump(supply, open(f"{TR}/supply-perfect.json", "w"))

    ts = sample(Simulator(load, supply).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, "Ideal baseline — near-perfect scaling (setup≈0, drain≈0)",
           f"{OUT}/01-ideal.png")
    render_latency(ts, "Ideal baseline — per-request time in system",
                   f"{OUT}/01-ideal-latency.png")
    # Cumulative A(t)/D(t) deferred: only legible zoomed-in / at low N. Revisit as
    # an animated zoom that follows the other panels' timeline. (render_cumulative)
    _ = render_cumulative  # keep import alive for the deferred figure
    print(f"reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_setup_lag():
    """Same clairvoyant demand-tracking commands, but 90s (~1.5min) boot time:
    actual replicas lag desired, so the up-ramp runs under-provisioned."""
    load = _load()
    supply = gen_supply_perfect(load, C=C, service_rate=SERVICE_RATE, setup=SETUP,
                                drain=0.0, headroom=HEADROOM,
                                sizing_range=SIZING_RANGE,
                                decision_interval=DECISION_INTERVAL,
                                sat_frac=SAT_FRAC)
    json.dump(load, open(f"{TR}/load-bump.json", "w"))
    json.dump(supply, open(f"{TR}/supply-setup90.json", "w"))

    ts = sample(Simulator(load, supply).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, "Setup lag — demand-tracking commands, 90s boot (reactive timing)",
           f"{OUT}/02-setup-lag.png")
    render_latency(ts, "Setup lag — per-request time in system",
                   f"{OUT}/02-setup-lag-latency.png")
    print(f"[setup90] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_queue_aware():
    """Fix step 1: same 90s boot, but the sizer is QUEUE-AWARE (reactive, no
    look-ahead). It adds a backlog-drain term, so as the queue piles up during
    the boot window it over-provisions to clear it -- recovers within the run,
    but overshoots and stays late (motivates anticipation as the next step)."""
    load = _load()
    supply = gen_supply_queue_aware(load, C=C, service_rate=SERVICE_RATE,
                                    setup=SETUP, drain=0.0, headroom=HEADROOM,
                                    sizing_range=SIZING_RANGE,
                                    drain_time=DRAIN_TIME,
                                    decision_interval=DECISION_INTERVAL,
                                    sat_frac=SAT_FRAC)
    json.dump(load, open(f"{TR}/load-bump.json", "w"))
    json.dump(supply, open(f"{TR}/supply-qaware90.json", "w"))

    ts = sample(Simulator(load, supply).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, "Queue-aware fix — 90s boot, size for backlog-drain (reactive)",
           f"{OUT}/03-queue-aware.png")
    render_latency(ts, "Queue-aware fix — per-request time in system",
                   f"{OUT}/03-queue-aware-latency.png")
    print(f"[qaware90] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def _hpa_scenario(kind, num, slug, title, latency_title):
    """Shared driver for the three HPA/KEDA closed-loop baselines. Each reads the
    ACTUAL simulated queue/running signal (trailing-avg over METRIC_WINDOW) every
    DECISION_INTERVAL and reconciles the live fleet — no foresight, 90s boot."""
    load = _load()
    sim = run_closed_loop(load, kind, C=C, service_rate=SERVICE_RATE, setup=SETUP,
                          drain=0.0, sat_frac=SAT_FRAC,
                          decision_interval=DECISION_INTERVAL,
                          metric_window=METRIC_WINDOW, headroom=HEADROOM,
                          max_replicas=MAX_REPLICAS)
    json.dump(load, open(f"{TR}/load-bump.json", "w"))
    json.dump(sim.supply, open(f"{TR}/supply-hpa-{kind}.json", "w"))

    ts = sample(sim, sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, title, f"{OUT}/{num}-hpa-{slug}.png")
    render_latency(ts, latency_title, f"{OUT}/{num}-hpa-{slug}-latency.png")
    print(f"[hpa-{kind}] reqs={len(load['requests'])} replicas={len(sim.supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_hpa_queue():
    """HPA/KEDA on queue depth (AverageValue target=1 → desired=ceil(Q)). Blind
    to boot lag: during the 90s boot it sees the whole backlog and orders it as
    replicas, pinning at maxReplicaCount — completes, but over-provisions."""
    return _hpa_scenario(
        "queue", "04", "queue",
        "HPA/KEDA queue-depth — desired = ceil(Q), target 1/replica (cap 10)",
        "HPA/KEDA queue-depth — per-request time in system")


def scenario_hpa_concurrency():
    """HPA/KEDA on running-request count (AverageValue target c<C →
    desired=ceil(R/c)). The signal is capacity-capped (R ≤ n·usable_C), so it
    cannot see the queue behind it: under 90s boot it under-provisions badly."""
    return _hpa_scenario(
        "concurrency", "05", "concurrency",
        "HPA/KEDA concurrency — desired = ceil(R/c), c≈58 (cap 10)",
        "HPA/KEDA concurrency — per-request time in system")


def scenario_hpa_combined():
    """HPA/KEDA with BOTH triggers (native KEDA max): scale up on either, down
    on both. The queue trigger rescues the concurrency signal's blind spot."""
    return _hpa_scenario(
        "combined", "06", "combined",
        "HPA/KEDA combined — max(queue, concurrency) triggers (cap 10)",
        "HPA/KEDA combined — per-request time in system")


# --------------------------------------------------------------------------
# Comparison report
# --------------------------------------------------------------------------
_ROWS = [
    ("offered",             lambda s: f"{s['offered']:d}"),
    ("completed",           lambda s: f"{s['completed']:d}"),
    ("completed %",         lambda s: f"{s['completed_pct']:.1f}"),
    ("unfinished",          lambda s: f"{s['unfinished']:d}"),
    # quality mix (panel-1a colours): % of OFFERED per waiting-time band.
    # These five + (unfinished/offered) sum to 100. Inserted at render time so
    # the labels/edges follow whatever wait_edges the run used.
    ("__bands__",           None),
    ("wait avg (s)",        lambda s: f"{s['wait']['avg']:.1f}"),
    ("wait p50 (s)",        lambda s: f"{s['wait']['p50']:.1f}"),
    ("wait p75 (s)",        lambda s: f"{s['wait']['p75']:.1f}"),
    ("wait p90 (s)",        lambda s: f"{s['wait']['p90']:.1f}"),
    ("wait p95 (s)",        lambda s: f"{s['wait']['p95']:.1f}"),
    ("wait p99 (s)",        lambda s: f"{s['wait']['p99']:.1f}"),
    ("time/work avg (s/u)", lambda s: f"{s['tpw']['avg']:.2f}"),
    ("time/work p50 (s/u)", lambda s: f"{s['tpw']['p50']:.2f}"),
    ("time/work p90 (s/u)", lambda s: f"{s['tpw']['p90']:.2f}"),
    ("time/work p95 (s/u)", lambda s: f"{s['tpw']['p95']:.2f}"),
    ("time/work p99 (s/u)", lambda s: f"{s['tpw']['p99']:.2f}"),
    ("replicas avg",        lambda s: f"{s['replicas']['avg']:.2f}"),
    ("replicas std",        lambda s: f"{s['replicas']['std']:.2f}"),
    ("replicas max",        lambda s: f"{s['replicas']['max']:d}"),
    ("replica·seconds",     lambda s: f"{s['replicas']['rep_seconds']:.0f}"),
]


def _expand_rows(summaries: dict):
    """Materialise _ROWS, replacing the __bands__ placeholder with one row per
    waiting-time quality band (labels taken from the first summary)."""
    first = next(iter(summaries.values()))
    band_rows = [
        (f"  {lbl} %", (lambda i: lambda s: f"{s['band_pct'][i]:.1f}")(i))
        for i, lbl in enumerate(first["band_labels"])
    ]
    rows = []
    for label, fn in _ROWS:
        if label == "__bands__":
            rows.extend(band_rows)
        else:
            rows.append((label, fn))
    return rows


def report(summaries: dict, md_path=f"{OUT}/summary.md"):
    """Print an aligned comparison table and mirror it to a markdown file."""
    names = list(summaries)
    rows = _expand_rows(summaries)
    w0 = max(len(r[0]) for r in rows) + 1
    wc = max(12, max(len(n) for n in names) + 1)

    def line(cells):
        return cells[0].ljust(w0) + "".join(c.rjust(wc) for c in cells[1:])

    header = line(["metric", *names])
    print("\n" + header)
    print("-" * len(header))
    for label, fn in rows:
        print(line([label, *[fn(summaries[n]) for n in names]]))

    md = ["| metric | " + " | ".join(names) + " |",
          "|" + "---|" * (len(names) + 1)]
    for label, fn in rows:
        md.append("| " + label.strip() + " | "
                  + " | ".join(fn(summaries[n]) for n in names) + " |")
    with open(md_path, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"\n[wrote {md_path}]")


if __name__ == "__main__":
    sums = {
        "ideal": summarize(scenario_ideal()),
        "setup-lag": summarize(scenario_setup_lag()),
        "queue-aware": summarize(scenario_queue_aware()),
        "hpa-queue": summarize(scenario_hpa_queue()),
        "hpa-concurrency": summarize(scenario_hpa_concurrency()),
        "hpa-combined": summarize(scenario_hpa_combined()),
    }
    report(sums)
