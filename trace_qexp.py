"""Exploration harness for the periodic-loop Qexp sizer (throwaway / scratch).

Not part of the demo. It answers four questions while the policy is being
validated:
  1. FLAT sanity   — constant load: does Qexp mint to steady, HOLD through boot
                     (no self-cancel oscillation), then retire on the observed
                     backlog clearing?  (the failure mode of the old sizer)
  2. PATTERN A/B   — reactive vs Qexp summary metrics across all five demand
                     patterns (uniform/rising/bump/step/spike).
  3. CASCADE       — boot_stagger > 0: replicas land staggered; does the
                     projection still size sanely?
  4. DIVERGENCE    — proj_setup != setup: projection mis-predicts the boot lead;
                     does the loop self-correct on the next ticks?

Run:  ./.venv/bin/python trace_qexp.py
"""
import math

import run
from sim import (gen_load, gen_supply_queue_aware, gen_supply_queue_aware_exp,
                 Simulator, sample, summarize)

C, SR, SAT = run.C, run.SERVICE_RATE, run.SAT_FRAC
HR, SRANGE, DINT, DR = run.HEADROOM, run.SIZING_RANGE, run.DECISION_INTERVAL, run.DRAIN_TIME
SETUP = run.SETUP
SI, RR, WR = run.SAMPLE_INTERVAL, run.REQ_RANGE, run.WORK_RANGE
PB = int(SAT * C) * SR

print(f"per_backend={PB:.1f} tok/s  setup={SETUP}  drain_time={DR}  "
      f"dint={DINT}  headroom={HR}")


def qexp(load, **kw):
    return gen_supply_queue_aware_exp(
        load, C=C, service_rate=SR, setup=SETUP, drain=0.0, headroom=HR,
        sizing_range=SRANGE, drain_time=DR, decision_interval=DINT, sat_frac=SAT,
        **kw)


def react(load, **kw):
    return gen_supply_queue_aware(
        load, C=C, service_rate=SR, setup=SETUP, drain=0.0, headroom=HR,
        sizing_range=SRANGE, drain_time=DR, decision_interval=DINT, sat_frac=SAT,
        **kw)


def metrics(load, supply):
    ts = sample(Simulator(load, supply).run(), sample_interval=SI,
                req_range=RR, work_range=WR)
    s = summarize(ts)
    return (f"good={s['band_pct'][0]:5.1f}%  fail={s['band_pct'][-1]:4.1f}%  "
            f"wait_p90={s['wait']['p90']:6.1f}s  rep_max={s['replicas']['max']:2d}  "
            f"rep·s={s['replicas']['rep_seconds']:6.0f}  "
            f"prov·s={s['replicas']['prov_seconds']:6.0f}  "
            f"util={s['utilization']:.2f}")


def dump(tag, supply, field):
    print(f"\n== {tag} decisions ==")
    hdr = "   t   ->n     owr      B_now"
    if field:
        hdr += f"    {field:>8}   t_pk"
    print(hdr + "   target  desired")
    for d in supply["decisions"]:
        extra = d["owr"] + (d.get(field, 0.0) if field else d["backlog"]) / DR
        line = f"  {d['t']:4.0f}  {d['to']:3d}  {d['owr']:8.0f} {d['backlog']:9.0f}"
        if field:
            line += f" {d.get(field, 0.0):9.0f} {d.get('t_peak', 0.0):6.0f}"
        print(line + f" {extra:8.0f}  {d['to']:3d}")


# ---------------------------------------------------------------------------
# 1. FLAT sanity — constant load. The old sizer's failure was cancelling its
#    own pending at ~t=setup/3 (residual->0). This must NOT happen.
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("1. FLAT sanity (uniform load, duration 600) — expect: mint to steady, "
      "HOLD\n   through the whole boot, retire only after observed backlog clears")
flat = gen_load(pattern="uniform", duration=600, peak_rate=12,
                size_mean=1000, size_dist="expo", seed=1)
q = qexp(flat)
r = react(flat)
dump("REACTIVE flat", r, None)
dump("QEXP flat", q, "b_peak")
print(f"\n  reactive: {metrics(flat, r)}")
print(f"  qexp    : {metrics(flat, q)}")

# ---------------------------------------------------------------------------
# 2. PATTERN A/B — summary metrics across all five demand patterns.
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("2. PATTERN A/B — reactive vs Qexp across demand patterns")
for pat in ["uniform", "rising", "bump", "step", "spike"]:
    load = gen_load(pattern=pat, duration=600, peak_rate=24,
                    size_mean=1000, size_dist="expo", seed=1)
    print(f"\n  --- {pat} ---")
    print(f"  reactive: {metrics(load, react(load))}")
    print(f"  qexp    : {metrics(load, qexp(load))}")

# ---------------------------------------------------------------------------
# 3. CASCADE — boot_stagger. Replicas in a batch land every u seconds.
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print("3. CASCADE (boot_stagger sweep) — replicas in a batch land every u sec.\n"
      "   Uses step/spike: these mint MULTI-replica batches in one tick, so the\n"
      "   within-batch stagger actually bites (bump climbs 1-at-a-time -> no-op).")
for pat in ["step", "spike"]:
    load = gen_load(pattern=pat, duration=600, peak_rate=24,
                    size_mean=1000, size_dist="expo", seed=1)
    print(f"\n  --- {pat} ---")
    for u in [0.0, 15.0, 45.0]:
        print(f"    stagger={u:4.0f}  reactive: {metrics(load, react(load, boot_stagger=u))}")
        print(f"    stagger={u:4.0f}  qexp    : {metrics(load, qexp(load, boot_stagger=u))}")

# ---------------------------------------------------------------------------
# 4. DIVERGENCE — projection assumes proj_setup but sim applies setup=90.
#    Under-predict (proj_setup<90) and over-predict (proj_setup>90): the loop
#    should still land near reactive quality by self-correcting each tick.
# ---------------------------------------------------------------------------
print("\n" + "=" * 78)
print(f"4. DIVERGENCE (bump load, sim setup={SETUP}, projection assumes proj_setup)")
bump = run._load()
for ps in [45.0, 90.0, 135.0]:
    print(f"  proj_setup={ps:5.0f}: {metrics(bump, qexp(bump, proj_setup=ps))}")
