"""Standalone stress experiment: make even the IDEAL sizer queue.

This is deliberately NOT part of the three-way comparison (run.py). Its only
job is to make one pedagogical point: a perfectly-clairvoyant, setup-free sizer
with headroom still achieves ~zero queue on a *smoothly*-varying bump — but the
moment demand rises faster than the headroom slack can absorb within one
decision interval, even ideal queues.

We keep every calibration knob identical to run.py's ideal scenario and change
ONE thing: the demand shape. Instead of the slow triangular bump we drive a
short, tall burst ("spike" pattern: steady baseline + a 6s jump to 3x peak).
The burst is far shorter than the sizer's 60s estimation window, so even a
perfectly clairvoyant *centered* window averages it away and sizes for the
window mean, not the burst peak. With setup=0 the replicas are instantly up —
yet there simply aren't enough of them for the burst, so ideal queues. The
point: knowing the future perfectly is not enough if you compress it into a
windowed average to size a fixed replica count.

Output: out/stress-ideal-spike.png (single figure, saved on its own).

Run:  ./.venv/bin/python stress_ideal.py
"""

import json

from sim import gen_load, gen_supply_perfect, Simulator, sample, summarize
from plots import render
import run  # reuse the exact calibration constants (single source of truth)

OUT, TR = run.OUT, run.TR


def stress_ideal():
    # Same calibration as run.scenario_ideal(); ONLY the demand shape changes:
    # a sharp step instead of the smooth triangular bump.
    load = gen_load(pattern="spike", duration=run.DURATION, peak_rate=run.PEAK_RATE,
                    size_mean=run.SIZE_MEAN, size_dist="expo", seed=1,
                    burn_in=run.BURN_IN)
    supply = gen_supply_perfect(load, C=run.C, service_rate=run.SERVICE_RATE,
                                setup=0.0, drain=0.0, headroom=run.HEADROOM,
                                sizing_range=run.SIZING_RANGE,
                                decision_interval=run.DECISION_INTERVAL,
                                sat_frac=run.SAT_FRAC)
    json.dump(load, open(f"{TR}/load-spike.json", "w"))
    json.dump(supply, open(f"{TR}/supply-perfect-spike.json", "w"))

    ts = sample(Simulator(load, supply).run(),
                sample_interval=run.SAMPLE_INTERVAL,
                req_range=run.REQ_RANGE, work_range=run.WORK_RANGE)
    render(ts, "STRESS: ideal sizer, sub-window spike — even clairvoyance queues "
               f"(setup=0, headroom={run.HEADROOM:g})", f"{OUT}/stress-ideal-spike.png")
    s = summarize(ts)
    print(f"[stress-ideal] reqs={len(load['requests'])} "
          f"replicas={len(supply['replicas'])} "
          f"peak_desired={max(ts['desired'])} peak_actual={max(ts['actual'])} "
          f"peak_qlen={max(ts['qlen'])} peak_L={max(ts['nsys'])}")
    print(f"[stress-ideal] good%={s['band_pct'][0]:.1f} "
          f"wait avg={s['wait']['avg']:.1f}s p90={s['wait']['p90']:.1f}s "
          f"p99={s['wait']['p99']:.1f}s")
    return ts


if __name__ == "__main__":
    stress_ideal()
