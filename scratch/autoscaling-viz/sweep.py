"""Parameter sweeps — read trends + calibrate (pre-render only, no server).

Re-runs the sim across parameter grids and reports SUMMARY METRICS only (it does
NOT touch the 7 canonical scenario figures). Prints trend tables to stdout and
mirrors them to out/sweep.md. Shares the canonical calibration by importing the
held-constant knobs + load generator from run.py, so a sweep point at the
baseline knobs reproduces the matching scenario's summary row exactly.

Grids (baselines are the canonical run's values, marked * in the tables):
  1. setup-lag   : setup ∈ {30, 60, 90*}   — cost of boot lag (context; setup=90 is
                   the real vLLM boot time and stays the demo baseline)
  2. queue-aware : setup ∈ {60, 90*} × drain_time ∈ {3,5,8,10,15,20*,30}
                   — aggression curve. Shorter drain_time = size for MORE replicas
                   to clear the backlog faster (the one quality lever we can push
                   without foresight). Two setups show the coupling to boot lag.
                   NOTE: queue-aware's canonical drain (20, near-free Pareto win)
                   now differs from Qexp's (30, tested — Qexp's own drain=20 is a
                   regression). The two sizers do NOT share one drain_time baseline.
  3. qexp        : proj_setup ∈ {45..180} — assumed boot lead (self-correcting).
  4. headroom    : headroom ∈ {1.0..2.0} on queue-aware AND Qexp — the STATIC
                   per-replica margin dial (§2.6). More margin = more slots = less
                   queue = less wait, at higher cost. (Its §2.7 SPEED benefit does
                   NOT show here — see the ρ note at the foot of sweep.md.)
  5. headroom × drain_time (queue-aware) and headroom × proj_setup (Qexp) — the
                   substitution surface: how much STATIC margin a more aggressive /
                   more anticipatory DYNAMIC reaction can buy back.

hpa-concurrency is intentionally omitted: it is broken by design (capacity-capped
signal, blind to the queue), so no conc_target rescues it — nothing to calibrate.

Run:  ./.venv/bin/python sweep.py
"""

import run  # reuse the canonical calibration constants + _load()
from sim import (gen_supply_perfect, gen_supply_queue_aware,
                 gen_supply_queue_aware_exp, run_closed_loop,
                 Simulator, sample, summarize)
from plots import render_sweep

# Held-constant calibration, pulled straight from run.py (single source of truth).
C, SR, SAT = run.C, run.SERVICE_RATE, run.SAT_FRAC
HR, SRANGE, DINT = run.HEADROOM, run.SIZING_RANGE, run.DECISION_INTERVAL
MW, MAXR = run.METRIC_WINDOW, run.MAX_REPLICAS
SI, RR, WR = run.SAMPLE_INTERVAL, run.REQ_RANGE, run.WORK_RANGE
RHO = run.RHO                    # concurrency-dependent decode speedup (§2.7); the
                                 # sizer ignores it, so the replica schedule is
                                 # unchanged — only achieved service time (and thus
                                 # the drain-tail cost) reflects it. See the ρ note
                                 # at the foot of sweep.md.

# Canonical baselines (the values the 7 scenarios use) — flagged in the tables.
BASE_SETUP = run.SETUP            # 90
BASE_DRAIN = run.DRAIN_TIME       # 30 — Qexp's canonical drain (unchanged)
QAWARE_BASE_DRAIN = run.QAWARE_DRAIN_TIME   # 20 — queue-aware's own tuned drain; NOTE this now
                                            # differs from Qexp's BASE_DRAIN (30) — don't assume
                                            # the two sizers share one canonical drain_time.
BASE_HR = HR                      # headroom baseline (1.2)
BASE_CONC = max(1.0, int(SAT * C) / HR)   # run_closed_loop's default (~58)

# Headroom palette for the 2-D sweeps (one line per headroom value); baseline blue.
HR_COLORS = {1.0: "#94a3b8", 1.2: "#2563eb", 1.5: "#16a34a", 2.0: "#dc2626"}

METRIC_COLS = ["good%", "failed%", "wait_p90", "rep_max", "rep·s", "prov·s", "util"]


def _metrics(ts) -> dict:
    """The trend signals: pinned good/failed bands, tail wait, peak fleet, cost.
    Formatted strings feed the tables; the `_`-prefixed raw floats feed the sweep
    figures (ignored by _emit, which reads only METRIC_COLS)."""
    s = summarize(ts)
    return {
        "good%": f"{s['band_pct'][0]:.1f}",
        "failed%": f"{s['band_pct'][-1]:.1f}",
        "wait_p90": f"{s['wait']['p90']:.1f}",
        "rep_max": f"{s['replicas']['max']:d}",
        "rep·s": f"{s['replicas']['rep_seconds']:.0f}",
        "prov·s": f"{s['replicas']['prov_seconds']:.0f}",
        "util": f"{s['utilization']:.2f}",
        "_good": s["band_pct"][0],
        "_p90": s["wait"]["p90"],
        "_prov": s["replicas"]["prov_seconds"],
    }


def _sample_open(supply, load, rho=RHO) -> dict:
    return sample(Simulator(load, supply, rho=rho).run(), sample_interval=SI,
                  req_range=RR, work_range=WR)


def run_setup_lag(setup) -> dict:
    load = run._load()
    supply = gen_supply_perfect(load, C=C, service_rate=SR, setup=setup, drain=0.0,
                                headroom=HR, sizing_range=SRANGE,
                                decision_interval=DINT, sat_frac=SAT)
    return _metrics(_sample_open(supply, load))


def run_qaware(setup, drain_time, headroom=HR) -> dict:
    load = run._load()
    supply = gen_supply_queue_aware(load, C=C, service_rate=SR, setup=setup,
                                    drain=0.0, headroom=headroom, sizing_range=SRANGE,
                                    drain_time=drain_time, decision_interval=DINT,
                                    sat_frac=SAT)
    return _metrics(_sample_open(supply, load))


def run_qexp(proj_setup, headroom=HR) -> dict:
    load = run._load()
    supply = gen_supply_queue_aware_exp(load, C=C, service_rate=SR, setup=BASE_SETUP,
                                        drain=0.0, headroom=headroom, sizing_range=SRANGE,
                                        drain_time=BASE_DRAIN, decision_interval=DINT,
                                        sat_frac=SAT, proj_setup=proj_setup)
    return _metrics(_sample_open(supply, load))


def run_hpa_conc(setup, conc_target) -> dict:
    load = run._load()
    sim = run_closed_loop(load, "concurrency", C=C, service_rate=SR, setup=setup,
                          drain=0.0, sat_frac=SAT, decision_interval=DINT,
                          metric_window=MW, headroom=HR, max_replicas=MAXR,
                          conc_target=conc_target, rho=RHO)
    return _metrics(sample(sim, sample_interval=SI, req_range=RR, work_range=WR))


# --------------------------------------------------------------------------
# table emit (stdout + markdown), same look as run.py's report()
# --------------------------------------------------------------------------
def _emit(title, note, param_cols, rows, md):
    """rows: list of (param_values_list, metrics_dict). Aligns to a text table
    and appends the same table to the markdown accumulator `md`."""
    headers = param_cols + METRIC_COLS
    cells = [[*pv, *(m[c] for c in METRIC_COLS)] for pv, m in rows]
    widths = [max(len(headers[i]), max(len(r[i]) for r in cells)) + 2
              for i in range(len(headers))]

    def line(vals):
        return "".join(str(v).rjust(widths[i]) for i, v in enumerate(vals))

    print(f"\n### {title}\n{note}")
    print(line(headers))
    print("-" * sum(widths))
    for r in cells:
        print(line(r))

    md.append(f"### {title}\n")
    md.append(f"{note}\n")
    md.append("| " + " | ".join(headers) + " |")
    md.append("|" + "---|" * len(headers))
    for r in cells:
        md.append("| " + " | ".join(str(v) for v in r) + " |")
    md.append("")


def _star(val, base):
    return f"{val}*" if val == base else str(val)


def _group(label, color, metrics):
    """Pack a list of _metrics() dicts (one per swept point, in x-order) into the
    render_sweep group shape: parallel good%/wait-p90/prov·s arrays."""
    return {
        "label": label,
        "color": color,
        "good": [m["_good"] for m in metrics],
        "p90": [m["_p90"] for m in metrics],
        "prov": [m["_prov"] for m in metrics],
    }


def main():
    setups = [30, 60, 90]
    q_setups = [60, 90]
    drains = [3, 5, 8, 10, 15, 20, 30]
    md = ["# Parameter sweeps — trends & calibration\n",
          "Metrics per run: `good%` (≤2s, pinned), `failed%` (>60s, pinned), "
          "`wait_p90` (s), `rep_max` (peak fleet), `rep·s` (usable replica-seconds), "
          "`prov·s` (billed incl. boot/drain), `util` (delivered ÷ usable capacity "
          "paid for). `*` = each section's own canonical baseline (setup=90; drain=20 "
          "for queue-aware, drain=30 for Qexp — the two sizers do NOT share one "
          "canonical drain_time, see the queue-aware section's own note).\n"]

    # 1 — setup-lag: pure cost of boot lag on the clairvoyant demand-tracker.
    # Context only — setup=90 is the real vLLM boot time and stays the baseline.
    sl_metrics = [run_setup_lag(s) for s in setups]
    rows = [([_star(s, BASE_SETUP)], m) for s, m in zip(setups, sl_metrics)]
    _emit("setup-lag — setup (boot lag) sweep",
          "Clairvoyant demand-tracking commands landing `setup` s late. Isolates "
          "boot lag alone (no backlog term). Context: setup=90 is the real boot "
          "time; the point is that it is where quality collapses.", ["setup"],
          rows, md)
    render_sweep("Setup-lag sweep — quality collapse & cost vs boot time",
                 "replica boot time, setup (s)", setups,
                 [_group("setup-lag", "#dc2626", sl_metrics)],
                 f"{run.OUT}/11-sweep-setuplag.png", xmark=BASE_SETUP,
                 mark_label="baseline (real boot)")

    # 2 — queue-aware aggression curve: shorter drain_time → size for more replicas.
    # setup fixed at the real values (60 for coupling context, 90 the baseline).
    qa_rows, qa_groups = [], []
    qa_colors = {60: "#2563eb", 90: "#dc2626"}
    for s in q_setups:
        metrics = [run_qaware(s, d) for d in drains]
        qa_rows.extend(([_star(s, BASE_SETUP), _star(d, QAWARE_BASE_DRAIN)], m)
                       for d, m in zip(drains, metrics))
        qa_groups.append(_group(f"setup={s}", qa_colors.get(s, "#6b7280"), metrics))
    _emit("queue-aware — drain_time aggression curve (setup 60 vs 90)",
          "Reactive backlog-drain sizer, NO upper cap. `drain_time` is the deadline "
          "to clear the current queue; shorter → size for more replicas. But it has "
          "no dead-time compensation, so replicas ordered still boot `setup` s late "
          "— watch whether aggression buys good% or just prov·s (boot-lag waste).",
          ["setup", "drain"], qa_rows, md)
    render_sweep("Queue-aware sweep — aggression (shorter drain) vs quality & cost",
                 "backlog-drain deadline, drain_time (s)  — shorter = more aggressive",
                 drains, qa_groups, f"{run.OUT}/12-sweep-drain.png",
                 xmark=QAWARE_BASE_DRAIN, mark_label="baseline")

    # 3 — Qexp proj_setup dial: how much boot lead the ANTICIPATORY sizer assumes,
    # while the sim always boots in BASE_SETUP (90). proj_setup < 90 under-predicts
    # the lag (anticipates less -> toward reactive); > 90 over-predicts (orders
    # earlier/more -> better tail, a little more cost). The loop stays stable and
    # self-corrects across the whole range — the point is it does NOT depend on the
    # assumption being right. proj_setup = 90 (= true setup) is the honest baseline.
    proj_setups = [45, 60, 75, 90, 105, 120, 135, 180]
    qx_metrics = [run_qexp(ps) for ps in proj_setups]
    rows = [([_star(ps, BASE_SETUP)], m) for ps, m in zip(proj_setups, qx_metrics)]
    _emit("qexp — proj_setup dial (sim boots in 90s regardless)",
          "Anticipatory Qexp sizing to the projected backlog peak. `proj_setup` is "
          "the boot lead the projection ASSUMES; the sim always applies setup=90. "
          "Under-predict (<90) → anticipates less, drifts toward reactive; "
          "over-predict (>90) → orders earlier, trades a little cost for tail "
          "latency. Stable and self-correcting across the range. `*` = true setup.",
          ["proj_setup"], rows, md)
    render_sweep("Qexp sweep — assumed boot lead vs quality & cost (self-correcting)",
                 "assumed boot lead, proj_setup (s)  — sim always boots in 90s",
                 proj_setups, [_group("qexp", "#16a34a", qx_metrics)],
                 f"{run.OUT}/13-sweep-qexp.png", xmark=BASE_SETUP,
                 mark_label="true setup (honest)")

    # 4 — headroom dial on the two GOOD sizers (queue-aware, Qexp). headroom is the
    # static per-replica margin (§2.6): more margin → more slots → less queue → less
    # wait, monotonically, at rising cost. Its §2.7 SPEED benefit is invisible on
    # this WAIT metric (backlog keeps pods packed at k≈1, rate=service_rate); see the
    # ρ note appended below. This isolates headroom's pure CAPACITY role.
    headrooms = [1.0, 1.1, 1.2, 1.35, 1.5, 1.75, 2.0]
    hr_qa = [run_qaware(BASE_SETUP, QAWARE_BASE_DRAIN, hr) for hr in headrooms]
    hr_qx = [run_qexp(BASE_SETUP, hr) for hr in headrooms]
    hr_rows = ([(["qaware", _star(hr, BASE_HR)], m) for hr, m in zip(headrooms, hr_qa)]
               + [(["qexp", _star(hr, BASE_HR)], m) for hr, m in zip(headrooms, hr_qx)])
    _emit("headroom — static per-replica margin (queue-aware vs Qexp)",
          "Static margin dial (§2.6) at the real 90s boot (qaware at its own tuned "
          "drain=20; qexp at drain=30 — see the module note on why they differ). "
          "More headroom "
          "= more replicas = fewer requests per pod = shorter queue = less wait, "
          "monotonically, for more prov·s. This is headroom's CAPACITY role; its §2.7 "
          "speed role does not appear on the wait metric (see ρ note below). `*` = "
          "canonical baseline (1.2).", ["sizer", "headroom"], hr_rows, md)
    render_sweep("Headroom sweep — static margin vs quality & cost (queue-aware, Qexp)",
                 "per-replica headroom (sizing multiplier)  — more = more static margin",
                 headrooms,
                 [_group("queue-aware", "#dc2626", hr_qa),
                  _group("qexp", "#16a34a", hr_qx)],
                 f"{run.OUT}/14-sweep-headroom.png", xmark=BASE_HR,
                 mark_label="baseline")

    # 5 — substitution surface I: headroom × drain_time (queue-aware). One line per
    # headroom over the aggression axis. Reads as "how much STATIC margin can a more
    # aggressive DYNAMIC drain buy back?" — where a low-headroom line meets a
    # higher-headroom line's good%, aggression has substituted for margin.
    hrs2d = [1.0, 1.2, 1.5, 2.0]
    hd_groups, hd_rows = [], []
    for hr in hrs2d:
        metrics = [run_qaware(BASE_SETUP, d, hr) for d in drains]
        hd_rows.extend(([_star(hr, BASE_HR), _star(d, QAWARE_BASE_DRAIN)], m)
                       for d, m in zip(drains, metrics))
        hd_groups.append(_group(f"hr={hr}", HR_COLORS.get(hr, "#6b7280"), metrics))
    _emit("headroom × drain_time (queue-aware) — static margin vs dynamic aggression",
          "2-D: static per-replica margin (headroom) against the reactive backlog "
          "aggression lever (shorter drain_time = order more to clear faster). Where "
          "a leaner (low-headroom) line reaches a fatter line's good%, aggression has "
          "substituted for static margin — at its own boot-lag cost. setup=90.",
          ["headroom", "drain"], hd_rows, md)
    render_sweep("Headroom × drain — can aggressive reaction replace static margin? (queue-aware)",
                 "backlog-drain deadline, drain_time (s)  — shorter = more aggressive",
                 drains, hd_groups, f"{run.OUT}/15-sweep-headroom-drain.png",
                 xmark=QAWARE_BASE_DRAIN, mark_label="baseline")

    # 6 — substitution surface II: headroom × proj_setup (Qexp). One line per
    # headroom over the anticipation axis. "How much STATIC margin can more
    # ANTICIPATION (assumed boot lead) buy back?" — anticipation orders sooner, so a
    # lean fleet can hold quality a fatter reactive fleet would need margin for.
    hp_groups, hp_rows = [], []
    for hr in hrs2d:
        metrics = [run_qexp(ps, hr) for ps in proj_setups]
        hp_rows.extend(([_star(hr, BASE_HR), _star(ps, BASE_SETUP)], m)
                       for ps, m in zip(proj_setups, metrics))
        hp_groups.append(_group(f"hr={hr}", HR_COLORS.get(hr, "#6b7280"), metrics))
    _emit("headroom × proj_setup (Qexp) — static margin vs dynamic anticipation",
          "2-D: static per-replica margin (headroom) against anticipation (assumed "
          "boot lead; sim always boots in 90s). More anticipation orders earlier, so "
          "a lean fleet can hold a fatter fleet's quality — anticipation substituting "
          "for margin. `*` proj_setup = true 90s setup.",
          ["headroom", "proj_setup"], hp_rows, md)
    render_sweep("Headroom × anticipation — can look-ahead replace static margin? (Qexp)",
                 "assumed boot lead, proj_setup (s)  — sim always boots in 90s",
                 proj_setups, hp_groups, f"{run.OUT}/16-sweep-headroom-proj.png",
                 xmark=BASE_SETUP, mark_label="true setup")

    # Finding worth recording: on this WAIT-based quality metric the §2.7 decode
    # speedup (ρ) is invisible in every queueing scenario, so these headroom sweeps
    # measure only its CAPACITY role, not the promised speed role.
    md.append(
        "### ρ note — why the §2.7 speed-up does not show in these sweeps\n")
    md.append(
        f"All sweeps run at the canonical `RHO = {RHO:g}` (empty pods decode ~{RHO:g}× "
        "faster than packed ones, §2.7). Yet `good%` / `wait_p90` are **identical** to "
        "a `RHO = 1` run at every headroom, and only `prov·s` shifts (a slightly shorter "
        "drain tail). The reason is structural: the quality bands key on **waiting time** "
        "(arrival→service-start), and whenever a backlog exists the router keeps every "
        "pod **packed at `usable_C` (k≈1)**, where `rate = service_rate` — exactly the "
        "fixed-rate value. The decode speed-up only fires when a pod is *under-full* "
        "(k<1), which is precisely when there is no queue and wait≈0 already. So on the "
        "wait metric, headroom buys **capacity/slack**, not speed; the §2.7 speed benefit "
        "is a *service-latency* effect (visible in `time/work`, not plotted here). This "
        "refines the 7(b) framing — see the design doc §2.7 / §8.1(7b).\n")

    path = f"{run.OUT}/sweep.md"
    with open(path, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"\n[wrote {path}]")
    print(f"[wrote {run.OUT}/11-sweep-setuplag.png, 12-sweep-drain.png, "
          f"13-sweep-qexp.png, 14-sweep-headroom.png, "
          f"15-sweep-headroom-drain.png, 16-sweep-headroom-proj.png]")


if __name__ == "__main__":
    main()
