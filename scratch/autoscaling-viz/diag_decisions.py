"""Throwaway diagnostic: dump per-decision sizer state for the queue-aware run,
so we can see exactly WHEN and WHY desired changes. Not wired into run.py."""

import math
from sim import gen_load, offered_work_rate
import run

load = gen_load(pattern="bump", duration=run.DURATION, peak_rate=run.PEAK_RATE,
                size_mean=run.SIZE_MEAN, size_dist="expo", seed=1,
                burn_in=run.BURN_IN)

DI = run.DECISION_INTERVAL
grid = [i * DI for i in range(int(run.DURATION / DI) + 1)]
per_backend = int(run.SAT_FRAC * run.C) * run.SERVICE_RATE

print(f"per_backend usable = {per_backend:.0f} work/s ; headroom={run.HEADROOM} ; "
      f"decision_interval={DI}s ; sizing_range={run.SIZING_RANGE}s\n")


def dump(label, owr, setup, drain_time):
    print(f"=== {label} (setup={setup}, drain_time={drain_time}) ===")
    replicas, active = [], []
    backlog = 0.0

    def up_cap(t):
        return sum(per_backend for r in replicas
                   if r["up"] <= t and (r["stop"] is None or t < r["stop"]))

    prev_n = 0
    for t, w in zip(grid, owr):
        target = w + (backlog / drain_time if drain_time else 0.0)
        n = max(0, math.ceil(run.HEADROOM * target / per_backend))
        uc = up_cap(t)
        if n != prev_n and t <= 300:
            arrow = "UP  " if n > prev_n else "DOWN"
            print(f"  t={t:5.0f}  desired {prev_n}->{n}  {arrow}   "
                  f"owr={w:7.0f}  backlog={backlog:8.0f}  up_cap={uc:6.0f}  "
                  f"target={target:7.0f}")
        while len(active) < n:
            replicas.append({"id": len(replicas), "up": t + setup,
                             "stop": None, "down": None})
            active.append(len(replicas) - 1)
        while len(active) > n:
            rid = active.pop()
            replicas[rid]["stop"] = t
        backlog = max(0.0, backlog + (w - up_cap(t)) * DI)
        prev_n = n
    print()


# ideal uses a CENTERED window; queue-aware a TRAILING window.
half = run.SIZING_RANGE / 2.0
owr_centered = offered_work_rate(load, [t + half for t in grid], run.SIZING_RANGE)
owr_trailing = offered_work_rate(load, grid, run.SIZING_RANGE)

# ideal / setup-lag: no backlog term (drain_time term disabled)
dump("ideal (centered, no backlog term)", owr_centered, 0.0, None)
dump("setup-lag (centered, no backlog term)", owr_centered, run.SETUP, None)
dump("queue-aware (trailing + backlog)", owr_trailing, run.SETUP, run.DRAIN_TIME)
