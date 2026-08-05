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
                 gen_supply_queue_aware_exp, gen_supply_static, run_closed_loop,
                 Simulator, sample, summarize)
from plots import (render, render_latency, render_cumulative,
                   render_wait_cdf, render_cost_quality)

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
SAT_FRAC = 0.85               # usable concurrency = floor(0.85*C); vLLM goodput ceiling
                              # (raised 0.70->0.85 2026-08-05: pack pods closer to the KV
                              # ceiling; raw-hw utilization ~= sat_frac/headroom, so this +
                              # the leaner headroom below lift utilization ~52%->~65%)
HEADROOM = 1.3               # unified static per-replica margin, used by EVERY sizer so the
                             # policies compare on a level field (cost is ~linear in headroom;
                             # picked at the steepest part of the headroom sweep — max marginal
                             # quality per unit margin, §8.1 item 10(b))
RHO = 2.0                     # empty/packed decode speedup: a lightly-loaded pod
                              # decodes ~RHO× faster than a packed one (batching-ITL,
                              # design §2.7). Sizer ignores this; only achieved
                              # latency reflects it. RHO=1 => fixed-rate model.
SIZING_RANGE = 60.0           # sizer's estimation range (Prom range-vector)
DECISION_INTERVAL = 15.0      # how often the sizer recomputes desired count
DRAIN_TIME = 20.0             # backlog-drain deadline — SHARED by BOTH Q sizers (queue-aware +
                              # Qexp), a standing rule (2026-08-05): the two always use the same
                              # drain_time so they compare on a level field. 20 is queue-aware's
                              # Pareto-frontier value; Qexp is held to it too even though its own
                              # optimum differs (level field beats Qexp's absolute numbers).
SETUP = 90.0                  # replica boot lag (setup-lag + queue-aware)
QEXP_PROJ_SETUP = 120.0       # Qexp-only: boot lead the PROJECTION assumes (true boot is SETUP=90;
                              # 120 deliberately over-anticipates). Swept-best at HEADROOM=1.3 —
                              # good% 70.7→78.0, wait_p90 30.7→17.6 for +3% cost vs the naive
                              # proj=setup value. Beyond ~135 the projection orders too early and
                              # flaps (proj=180 collapses to 35%). Re-derive if HEADROOM changes.
METRIC_WINDOW = 60.0          # HPA/KEDA metric avg_over_time window (trailing)
MAX_REPLICAS = 10             # KEDA maxReplicaCount (guide example: MAXPODS 10)
SAMPLE_INTERVAL = 0.25        # plot-grid resolution
REQ_RANGE = 15.0             # request-count averaging range (panels 1a/4-ish)
WORK_RANGE = 60.0            # work-rate averaging range (Prom-style, panel 1b)

# --------------------------------------------------------------------------
# Max-replica cap — enforced at ACTUATION (desired → committed), uniformly for
# EVERY sizer within a shape (Q and HPA share one ceiling). It is the
# "no-autoscaling provisioning level" — the maxReplicaCount an operator would
# pin if they didn't autoscale — NOT the clairvoyant ideal peak (~5 here).
# `scenario_static` runs pinned at exactly this value, so the static baseline
# and the shared ceiling are the same knob. Cap is 10 everywhere to start; a
# sustained-load shape whose Q sizers otherwise peg at 10 and become
# indistinguishable can be lifted to (at most) 15 via CAP_BY_SHAPE — the
# uncapped Q peaks (22/27) and HPA runaways (557–1766) are deliberately NOT the
# story per-shape; the cost-blowup lesson lives in the sweeps/tradeoffs.
CAP_DEFAULT = MAX_REPLICAS       # 10
CAP_BY_SHAPE: dict[str, int] = {}   # per-shape overrides; empty ⇒ 10 everywhere


def cap_for(shape: str) -> int:
    return CAP_BY_SHAPE.get(shape, CAP_DEFAULT)


# Demand shapes rendered into the deck. `bump` first (the calibration/reference
# shape); `spike` last (a teaching-only case — autoscaling is the wrong tool for
# a 6s burst; NOT calibrated on). rate_profile() in sim.py already defines all 5.
DEMO_SHAPES = [
    ("bump",      "Bump (triangular 0→peak→0)"),
    ("trapezoid", "Trapezoid (ramp → sustained plateau → ramp)"),
    ("stepup",    "Step up (lo → hi, stays)"),
    ("stepdown",  "Step down (hi → lo, stays)"),
    ("spike",     "Spike (6s burst to 3×peak — teaching case, NOT calibrated)"),
]


def _load(shape="bump"):
    return gen_load(pattern=shape, duration=DURATION, peak_rate=PEAK_RATE,
                    size_mean=SIZE_MEAN, size_dist="expo", seed=1)


def _headroom_point(sizer, hr, shape="bump"):
    """(prov·s, served≤15s%) for a Q sizer at an off-baseline headroom — feeds the
    cost-quality frontier's extra points. Mirrors the canonical scenario exactly;
    only `headroom` varies (qexp holds its operating QEXP_PROJ_SETUP). Capped at
    the shape's actuation ceiling like the baseline points, so it is apples-to-
    apples with them."""
    load = _load(shape)
    if sizer == "qaware":
        supply = gen_supply_queue_aware(load, C=C, service_rate=SERVICE_RATE,
                                        setup=SETUP, drain=0.0, headroom=hr,
                                        sizing_range=SIZING_RANGE, drain_time=DRAIN_TIME,
                                        decision_interval=DECISION_INTERVAL, sat_frac=SAT_FRAC,
                                        max_replicas=cap_for(shape))
    else:
        supply = gen_supply_queue_aware_exp(load, C=C, service_rate=SERVICE_RATE,
                                            setup=SETUP, drain=0.0, headroom=hr,
                                            sizing_range=SIZING_RANGE, drain_time=DRAIN_TIME,
                                            proj_setup=QEXP_PROJ_SETUP,
                                            decision_interval=DECISION_INTERVAL, sat_frac=SAT_FRAC,
                                            max_replicas=cap_for(shape))
    s = summarize(sample(Simulator(load, supply, rho=RHO).run(),
                         sample_interval=SAMPLE_INTERVAL, req_range=REQ_RANGE,
                         work_range=WORK_RANGE))
    return s["replicas"]["prov_seconds"], s["within_pct"][1]


def scenario_ideal(shape="bump"):
    load = _load(shape)
    supply = gen_supply_perfect(load, C=C, service_rate=SERVICE_RATE, setup=0.0,
                                drain=0.0, headroom=HEADROOM,
                                sizing_range=SIZING_RANGE,
                                decision_interval=DECISION_INTERVAL,
                                sat_frac=SAT_FRAC, max_replicas=cap_for(shape))
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(supply, open(f"{TR}/supply-perfect-{shape}.json", "w"))

    ts = sample(Simulator(load, supply, rho=RHO).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"Ideal baseline — near-perfect scaling (setup≈0, drain≈0) — {shape}",
           f"{OUT}/01-ideal-{shape}.png")
    render_latency(ts, f"Ideal baseline — per-request time in system — {shape}",
                   f"{OUT}/01-ideal-{shape}-latency.png")
    # Cumulative A(t)/D(t) deferred: only legible zoomed-in / at low N. Revisit as
    # an animated zoom that follows the other panels' timeline. (render_cumulative)
    _ = render_cumulative  # keep import alive for the deferred figure
    print(f"[ideal/{shape}] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_setup_lag(shape="bump"):
    """Same clairvoyant demand-tracking commands, but 90s (~1.5min) boot time:
    actual replicas lag desired, so the up-ramp runs under-provisioned."""
    load = _load(shape)
    supply = gen_supply_perfect(load, C=C, service_rate=SERVICE_RATE, setup=SETUP,
                                drain=0.0, headroom=HEADROOM,
                                sizing_range=SIZING_RANGE,
                                decision_interval=DECISION_INTERVAL,
                                sat_frac=SAT_FRAC, max_replicas=cap_for(shape))
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(supply, open(f"{TR}/supply-setup90-{shape}.json", "w"))

    ts = sample(Simulator(load, supply, rho=RHO).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"Setup lag — demand-tracking commands, 90s boot (reactive timing) — {shape}",
           f"{OUT}/02-setup-lag-{shape}.png")
    render_latency(ts, f"Setup lag — per-request time in system — {shape}",
                   f"{OUT}/02-setup-lag-{shape}-latency.png")
    print(f"[setup90/{shape}] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_queue_aware(shape="bump"):
    """Fix step 1: same 90s boot, but the sizer is QUEUE-AWARE (reactive, no
    look-ahead). It adds a backlog-drain term, so as the queue piles up during
    the boot window it over-provisions to clear it -- recovers within the run,
    but overshoots and stays late (motivates anticipation as the next step)."""
    load = _load(shape)
    supply = gen_supply_queue_aware(load, C=C, service_rate=SERVICE_RATE,
                                    setup=SETUP, drain=0.0, headroom=HEADROOM,
                                    sizing_range=SIZING_RANGE,
                                    drain_time=DRAIN_TIME,
                                    decision_interval=DECISION_INTERVAL,
                                    sat_frac=SAT_FRAC, max_replicas=cap_for(shape))
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(supply, open(f"{TR}/supply-qaware90-{shape}.json", "w"))

    ts = sample(Simulator(load, supply, rho=RHO).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"Queue-aware fix — 90s boot, size for backlog-drain (reactive) — {shape}",
           f"{OUT}/03-queue-aware-{shape}.png")
    render_latency(ts, f"Queue-aware fix — per-request time in system — {shape}",
                   f"{OUT}/03-queue-aware-{shape}-latency.png")
    print(f"[qaware90/{shape}] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_queue_aware_exp(shape="bump"):
    """Fix step 2: anticipatory QUEUE-aware sizing ("Qexp"), a periodic control
    loop. Same 90s boot and same backlog-drain idea as reactive queue-aware, but
    it sizes to the PEAK of the backlog it PROJECTS forward under the committed
    boot schedule (up now + pending at their estimated land-times), not the
    backlog measured now. It reads only the observable queue LEVEL each tick, so
    scale-down follows the real drain; the projection's constant-demand + boot
    assumptions are simplifications it self-corrects against, never depends on.
    Anticipating the queue that WILL pile up during the boot lets it order sooner
    and hold through the boot instead of chasing the backlog after the fact."""
    load = _load(shape)
    supply = gen_supply_queue_aware_exp(load, C=C, service_rate=SERVICE_RATE,
                                        setup=SETUP, drain=0.0, headroom=HEADROOM,
                                        sizing_range=SIZING_RANGE,
                                        drain_time=DRAIN_TIME,
                                        proj_setup=QEXP_PROJ_SETUP,
                                        decision_interval=DECISION_INTERVAL,
                                        sat_frac=SAT_FRAC, max_replicas=cap_for(shape))
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(supply, open(f"{TR}/supply-qexp90-{shape}.json", "w"))

    ts = sample(Simulator(load, supply, rho=RHO).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"Anticipatory queue-aware (Qexp) — 90s boot, size for projected peak — {shape}",
           f"{OUT}/08-queue-aware-exp-{shape}.png")
    render_latency(ts, f"Anticipatory queue-aware (Qexp) — per-request time in system — {shape}",
                   f"{OUT}/08-queue-aware-exp-{shape}-latency.png")
    print(f"[qexp90/{shape}] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_static(shape="bump"):
    """No autoscaling: a fixed fleet pinned at the ceiling for the whole run
    (the no-autoscaling provisioning level = the shared cap). Never scales, so on
    a bump it never queues — 100% prompt — but pays for the full fleet the entire
    time (the most expensive policy, and the lowest utilisation). On sustained
    shapes it may still queue if the peak exceeds the pinned count. The 'just
    provision for max' strawman."""
    load = _load(shape)
    supply = gen_supply_static(load, count=cap_for(shape), C=C,
                               service_rate=SERVICE_RATE, setup=0.0, drain=0.0,
                               sat_frac=SAT_FRAC)
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(supply, open(f"{TR}/supply-static-{shape}.json", "w"))

    ts = sample(Simulator(load, supply, rho=RHO).run(), sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"No scaling — fixed fleet pinned at max (always-on, no autoscaler) — {shape}",
           f"{OUT}/07-static-{shape}.png")
    render_latency(ts, f"No scaling — per-request time in system — {shape}",
                   f"{OUT}/07-static-{shape}-latency.png")
    print(f"[static/{shape}] reqs={len(load['requests'])} replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def _hpa_scenario(kind, num, slug, title, latency_title, shape="bump"):
    """Shared driver for the three HPA/KEDA closed-loop baselines. Each reads the
    ACTUAL simulated queue/running signal (trailing-avg over METRIC_WINDOW) every
    DECISION_INTERVAL and reconciles the live fleet — no foresight, 90s boot.
    The desired count is clamped to the shape's cap at reconcile time."""
    load = _load(shape)
    sim = run_closed_loop(load, kind, C=C, service_rate=SERVICE_RATE, setup=SETUP,
                          drain=0.0, sat_frac=SAT_FRAC,
                          decision_interval=DECISION_INTERVAL,
                          metric_window=METRIC_WINDOW, headroom=HEADROOM,
                          max_replicas=cap_for(shape), rho=RHO)
    json.dump(load, open(f"{TR}/load-{shape}.json", "w"))
    json.dump(sim.supply, open(f"{TR}/supply-hpa-{kind}-{shape}.json", "w"))

    ts = sample(sim, sample_interval=SAMPLE_INTERVAL,
                req_range=REQ_RANGE, work_range=WORK_RANGE)
    render(ts, f"{title} — {shape}", f"{OUT}/{num}-hpa-{slug}-{shape}.png")
    render_latency(ts, f"{latency_title} — {shape}", f"{OUT}/{num}-hpa-{slug}-{shape}-latency.png")
    print(f"[hpa-{kind}/{shape}] reqs={len(load['requests'])} replicas={len(sim.supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    return ts


def scenario_hpa_queue(shape="bump"):
    """HPA/KEDA on queue depth (AverageValue target=1 → desired=ceil(Q)). Blind
    to boot lag: during the 90s boot it sees the whole backlog and orders it as
    replicas, pinning at maxReplicaCount — completes, but over-provisions."""
    return _hpa_scenario(
        "queue", "04", "queue",
        "HPA/KEDA queue-depth — desired = ceil(Q), target 1/replica",
        "HPA/KEDA queue-depth — per-request time in system", shape=shape)


def scenario_hpa_concurrency(shape="bump"):
    """HPA/KEDA on running-request count (AverageValue target c<C →
    desired=ceil(R/c)). The signal is capacity-capped (R ≤ n·usable_C), so it
    cannot see the queue behind it: under 90s boot it under-provisions badly."""
    return _hpa_scenario(
        "concurrency", "05", "concurrency",
        "HPA/KEDA concurrency — desired = ceil(R/c), c≈58",
        "HPA/KEDA concurrency — per-request time in system", shape=shape)


def scenario_hpa_combined(shape="bump"):
    """HPA/KEDA with BOTH triggers (native KEDA max): scale up on either, down
    on both. The queue trigger rescues the concurrency signal's blind spot."""
    return _hpa_scenario(
        "combined", "06", "combined",
        "HPA/KEDA combined — max(queue, concurrency) triggers",
        "HPA/KEDA combined — per-request time in system", shape=shape)


# --------------------------------------------------------------------------
# Comparison report
# --------------------------------------------------------------------------
_ROWS = [
    ("offered",             lambda s: f"{s['offered']:d}"),
    ("completed",           lambda s: f"{s['completed']:d}"),
    ("completed %",         lambda s: f"{s['completed_pct']:.1f}"),
    ("unfinished",          lambda s: f"{s['unfinished']:d}"),
    # quality mix as the CUMULATIVE wait CDF sampled at each band edge: each row
    # is "% of OFFERED served within Ns", plus a derived "failed (>last-edge) %"
    # tail row. Inserted at render time so the labels/edges follow whatever
    # wait_edges the run used. (Exclusive per-band shares still live in the
    # panel-1a stacked figure.)
    ("__within__",          None),
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
    # total billed fleet-time incl. the boot window (start..up) and draining tail,
    # plus the boot-lag waste it adds over the usable replica·seconds above.
    ("provisioned·seconds", lambda s: f"{s['replicas']['prov_seconds']:.0f}"),
    ("boot-lag waste·s",    lambda s: f"{s['replicas']['boot_waste']:.0f}"),
    # delivered work ÷ usable throughput-capacity paid for. <1 = over-provisioned
    # (idle fleet); ~1 or above = fully packed (a small fleet kept busy — which can
    # still fail latency, cf. hpa-concurrency, so read it next to the % bands).
    ("utilization",         lambda s: f"{s['utilization']:.2f}"),
]


def _expand_rows(summaries: dict):
    """Materialise _ROWS, replacing the __within__ placeholder with one row per
    band edge: the cumulative "served within Ns" share (labels from the first
    summary's within_labels)."""
    first = next(iter(summaries.values()))
    within_rows = [
        (f"  {lbl} %", (lambda i: lambda s: f"{s['within_pct'][i]:.1f}")(i))
        for i, lbl in enumerate(first["within_labels"])
    ]
    # derived tail of the CDF: completed but slower than the last band edge.
    # failed = completed% − (served within last-edge %); unfinished is its own
    # row above, so this is the "finished, but too late" share on the OFFERED
    # denominator. Reported explicitly so the slow tail stays visible.
    last_edge = first["within_labels"][-1].lstrip("≤")           # e.g. "60s"
    within_rows.append(
        (f"  failed (>{last_edge}) %",
         lambda s: f"{s['completed_pct'] - s['within_pct'][-1]:.1f}"))
    rows = []
    for label, fn in _ROWS:
        if label == "__within__":
            rows.extend(within_rows)
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


def _run_all(shape):
    """Run all 8 policies for one demand shape. Keep each scenario's sampled
    timeseries (ts) around: the comparison table needs only the summaries, but
    the cross-policy CDF overlay needs the raw per-request waits, so run each
    scenario once and reuse the result."""
    return {
        "ideal": scenario_ideal(shape),
        "static": scenario_static(shape),
        "setup-lag": scenario_setup_lag(shape),
        "queue-aware": scenario_queue_aware(shape),
        "qexp": scenario_queue_aware_exp(shape),
        "hpa-queue": scenario_hpa_queue(shape),
        "hpa-concurrency": scenario_hpa_concurrency(shape),
        "hpa-combined": scenario_hpa_combined(shape),
    }


if __name__ == "__main__":
    for shape, label in DEMO_SHAPES:
        print(f"\n########## shape={shape} (cap={cap_for(shape)}) — {label} ##########")
        runs = _run_all(shape)
        sums = {k: summarize(v) for k, v in runs.items()}
        report(sums, f"{OUT}/summary-{shape}.md")
        if shape == "bump":
            # keep the unsuffixed summary.md as the bump alias for any consumer
            # that still reads the canonical reference table by its old name.
            report(sums, f"{OUT}/summary.md")

        # Cross-policy comparison figures (the per-scenario PNGs above can't show
        # policies on a shared axis). Cost is billed provisioned·seconds.
        costs = {k: s["replicas"]["prov_seconds"] for k, s in sums.items()}
        render_wait_cdf(runs, costs,
                        f"Waiting-time CDF — all policies (share of offered served within t) — {shape}",
                        f"{OUT}/09-wait-cdf-{shape}.png")
        # Extra frontier points: how much further up the cost-quality plane each Q
        # sizer climbs as static headroom grows past the 1.3 operating point (same
        # sizer colour, headroom in the label). Puts "how high can qaware go" right
        # on the frontier, not only in the sweep tables. Only headroom varies —
        # everything else (drain=20, sat_frac, qexp's proj_setup, the cap) is the
        # operating config, so these are apples-to-apples with the baseline (1.3).
        extra_pts = []
        for hr in (1.5, 2.0):
            c, q = _headroom_point("qaware", hr, shape)
            extra_pts.append((f"qaware({hr})", c, q, "queue-aware"))
            c, q = _headroom_point("qexp", hr, shape)
            extra_pts.append((f"qexp({hr})", c, q, "qexp"))
        render_cost_quality(sums,
                            f"Cost vs quality — fleet-time vs promptness (Pareto frontier) — {shape}",
                            f"{OUT}/10-cost-quality-{shape}.png",
                            extra_points=extra_pts,
                            label_overrides={"queue-aware": "qaware(1.3)",
                                             "qexp": "qexp(1.3)"})
