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
                   NOTE: both Q sizers (queue-aware AND Qexp) share one canonical
                   drain_time = 20 — a standing rule so they compare on a level field.
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

Table-data caching (design §8.1 item 10(d)): each swept point's numeric `_metrics`
is memoized to `out/.sweep-cache.json`, keyed by the run_* call args and gated by a
signature over the sim constants + sim.py/sweep.py source. A re-run after a
plot-only or narrative-only edit is served entirely from cache (~1.6s vs ~22s) and
still redraws every figure on the fly; any sim-param or engine change invalidates
the whole cache automatically. plots.py is NOT in the signature (plot edits stay
warm). The cache file is git-ignored.

Run:  ./.venv/bin/python sweep.py
"""

import hashlib
import json
import os

import run  # reuse the canonical calibration constants + _load()
from sim import (gen_supply_perfect, gen_supply_queue_aware,
                 gen_supply_queue_aware_exp, gen_supply_static, run_closed_loop,
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
BASE_DRAIN = run.DRAIN_TIME       # 20 — SHARED by both Q sizers (queue-aware + Qexp): a standing
                                  # rule that the two always use the same drain_time (2026-08-05).
BASE_HR = HR                      # headroom baseline (1.3)
BASE_CONC = max(1.0, int(SAT * C) / HR)   # run_closed_loop's default

# Headroom palette for the 2-D sweeps (one line per headroom value); baseline blue.
HR_COLORS = {1.0: "#94a3b8", 1.3: "#2563eb", 1.5: "#16a34a", 2.0: "#dc2626"}

METRIC_COLS = ["good%", "failed%", "wait_p90", "rep_max", "rep·s", "prov·s", "util"]

# Cap sweep (design §8.1 item 11 follow-up): the actuation ceiling `max_replicas`
# is a fixed constant everywhere else (MAXR=10). Here it is the swept axis, to
# separate the CEILING knob from HPA-queue's per-replica q_target AGGRESSION knob
# (swept, capped@10, in stability.md). Five teaching policies span the two cost
# families. Observed on the three sustained shapes: hpa-queue and static grow
# cost ∝ cap (HPA's raw desired = ceil of the whole backlog ≫ any sane cap, so it
# pins to the ceiling; static's fleet IS the ceiling). The work-rate Q sizers keep
# a low USABLE peak (~6–15 here, under any swept cap); raising the ceiling past
# that only adds a small, quality-neutral cost creep (speculative boot orders that
# never become usable) before flattening. So a looser cap barely grows Q-sizer
# cost and never in the ∝cap way. bump/spike keep the Q sizers even lower (~5) —
# noted in the section. Range stays bounded (5→30) — no log axis.
CAPS = [5, 8, 10, 12, 15, 20, 30]
CAP_POLICIES = [
    ("ideal",       "#111827"),   # reference — flat, usable peak ~5, cap never binds
    ("queue-aware", "#dc2626"),   # Q sizer — low usable peak; small boot-waste creep then flat
    ("qexp",        "#16a34a"),   # Q sizer — same, anticipatory
    ("hpa-queue",   "#2563eb"),   # desired ≫ cap ⇒ pins to the cap ⇒ cost ∝ cap
    ("static",      "#a855f7"),   # fixed fleet = the cap ⇒ cost ∝ cap by construction
]
CAP_SHAPES = ["trapezoid", "stepup", "stepdown"]


# --------------------------------------------------------------------------
# Sweep-TABLE cache (design §8.1 item 10(d)): persist each swept point's
# `_metrics` dict keyed by the run_* call args, so re-running the sweep after a
# plot-only / narrative-only edit skips the recompute. Deliberately caches ONLY
# the numeric table data — NOT per-run timeseries or figures (a single run is
# ~0.19s; plots regenerate on the fly). The whole cache is invalidated whenever
# any held-constant sim knob, the load recipe, or the sim/sweep source changes
# (plots.py is NOT in the signature, so plot-only edits keep the cache warm).
# --------------------------------------------------------------------------
_CACHE_PATH = f"{run.OUT}/.sweep-cache.json"


def _sim_signature() -> str:
    consts = [C, SR, SAT, HR, SRANGE, DINT, MW, MAXR, SI, RR, WR, RHO,
              BASE_SETUP, BASE_DRAIN, BASE_HR, BASE_CONC,
              run.DURATION, run.PEAK_RATE, run.SIZE_MEAN]
    h = hashlib.sha256(repr(consts).encode())
    for src in ("sim.py", "sweep.py"):
        with open(src, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


_SIG = _sim_signature()
if os.path.exists(_CACHE_PATH):
    try:
        _blob = json.load(open(_CACHE_PATH))
    except (ValueError, OSError):
        _blob = {}
    _CACHE = _blob.get("entries", {}) if _blob.get("sig") == _SIG else {}
    if _blob.get("sig") != _SIG:
        print("[sweep-cache] sim signature changed → cache invalidated (recomputing all)")
else:
    _CACHE = {}
_CACHE_STATS = {"hit": 0, "miss": 0}


def _memo(fn):
    """Cache a run_* function's returned `_metrics` dict by (fn name, args)."""
    def wrapper(*args, **kwargs):
        key = f"{fn.__name__}|{args!r}|{sorted(kwargs.items())!r}"
        if key in _CACHE:
            _CACHE_STATS["hit"] += 1
            return _CACHE[key]
        _CACHE_STATS["miss"] += 1
        val = fn(*args, **kwargs)
        _CACHE[key] = val
        return val
    return wrapper


def _save_cache():
    with open(_CACHE_PATH, "w") as f:
        json.dump({"sig": _SIG, "entries": _CACHE}, f)
    n = _CACHE_STATS["hit"] + _CACHE_STATS["miss"]
    print(f"[sweep-cache] {_CACHE_STATS['hit']}/{n} points served from cache "
          f"({_CACHE_STATS['miss']} recomputed); {len(_CACHE)} entries in {_CACHE_PATH}")


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
        "_good15": s["within_pct"][1],      # cumulative served ≤15s (Dean's "works" bar)
        "_p90": s["wait"]["p90"],
        "_prov": s["replicas"]["prov_seconds"],
    }


def _sample_open(supply, load, rho=RHO) -> dict:
    return sample(Simulator(load, supply, rho=rho).run(), sample_interval=SI,
                  req_range=RR, work_range=WR)


@_memo
def run_setup_lag(setup) -> dict:
    load = run._load()
    supply = gen_supply_perfect(load, C=C, service_rate=SR, setup=setup, drain=0.0,
                                headroom=HR, sizing_range=SRANGE,
                                decision_interval=DINT, sat_frac=SAT)
    return _metrics(_sample_open(supply, load))


@_memo
def run_qaware(setup, drain_time, headroom=HR) -> dict:
    load = run._load()
    supply = gen_supply_queue_aware(load, C=C, service_rate=SR, setup=setup,
                                    drain=0.0, headroom=headroom, sizing_range=SRANGE,
                                    drain_time=drain_time, decision_interval=DINT,
                                    sat_frac=SAT)
    return _metrics(_sample_open(supply, load))


@_memo
def run_qexp(proj_setup, headroom=HR) -> dict:
    load = run._load()
    supply = gen_supply_queue_aware_exp(load, C=C, service_rate=SR, setup=BASE_SETUP,
                                        drain=0.0, headroom=headroom, sizing_range=SRANGE,
                                        drain_time=BASE_DRAIN, decision_interval=DINT,
                                        sat_frac=SAT, proj_setup=proj_setup)
    return _metrics(_sample_open(supply, load))


@_memo
def run_hpa_conc(setup, conc_target) -> dict:
    load = run._load()
    sim = run_closed_loop(load, "concurrency", C=C, service_rate=SR, setup=setup,
                          drain=0.0, sat_frac=SAT, decision_interval=DINT,
                          metric_window=MW, headroom=HR, max_replicas=MAXR,
                          conc_target=conc_target, rho=RHO)
    return _metrics(sample(sim, sample_interval=SI, req_range=RR, work_range=WR))


@_memo
def run_capped(policy, shape, cap) -> dict:
    """One policy on one demand `shape` at one actuation ceiling `cap`
    (max_replicas). Mirrors the matching run.py scenario exactly except the cap
    is the swept variable — so a point at cap=MAXR (10) reproduces that
    scenario's summary row. Used only by the cap sweep."""
    load = run._load(shape)
    if policy == "ideal":
        supply = gen_supply_perfect(load, C=C, service_rate=SR, setup=0.0, drain=0.0,
                                    headroom=HR, sizing_range=SRANGE,
                                    decision_interval=DINT, sat_frac=SAT, max_replicas=cap)
        return _metrics(_sample_open(supply, load))
    if policy == "queue-aware":
        supply = gen_supply_queue_aware(load, C=C, service_rate=SR, setup=BASE_SETUP,
                                        drain=0.0, headroom=HR, sizing_range=SRANGE,
                                        drain_time=BASE_DRAIN, decision_interval=DINT,
                                        sat_frac=SAT, max_replicas=cap)
        return _metrics(_sample_open(supply, load))
    if policy == "qexp":
        supply = gen_supply_queue_aware_exp(load, C=C, service_rate=SR, setup=BASE_SETUP,
                                            drain=0.0, headroom=HR, sizing_range=SRANGE,
                                            drain_time=BASE_DRAIN, proj_setup=run.QEXP_PROJ_SETUP,
                                            decision_interval=DINT, sat_frac=SAT, max_replicas=cap)
        return _metrics(_sample_open(supply, load))
    if policy == "static":
        # static's "cap" IS its fixed fleet size (pre-warmed, up the whole run).
        supply = gen_supply_static(load, count=cap, C=C, service_rate=SR,
                                   setup=0.0, drain=0.0, sat_frac=SAT)
        return _metrics(_sample_open(supply, load))
    if policy == "hpa-queue":
        sim = run_closed_loop(load, "queue", C=C, service_rate=SR, setup=BASE_SETUP,
                              drain=0.0, sat_frac=SAT, decision_interval=DINT,
                              metric_window=MW, headroom=HR, max_replicas=cap, rho=RHO)
        return _metrics(sample(sim, sample_interval=SI, req_range=RR, work_range=WR))
    raise ValueError(f"unknown cap-sweep policy: {policy}")


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


def _emit_pivot(title, note, xlabel, xs, star_x, col_labels, cell_fn, md):
    """Pivot table: one row per x (e.g. cap), one column per policy. `cell_fn(col, x)`
    returns the formatted cell string; `star_x` flags the canonical baseline row.
    Same stdout + markdown twin-output shape as `_emit`, but the columns are the
    series (policies) rather than the fixed METRIC_COLS."""
    headers = [xlabel] + col_labels
    body = [[f"{x}*" if x == star_x else str(x)] + [cell_fn(col, x) for col in col_labels]
            for x in xs]
    widths = [max(len(headers[i]), max(len(r[i]) for r in body)) + 2
              for i in range(len(headers))]

    def line(vals):
        return "".join(str(v).rjust(widths[i]) for i, v in enumerate(vals))

    print(f"\n### {title}\n{note}")
    print(line(headers))
    print("-" * sum(widths))
    for r in body:
        print(line(r))

    md.append(f"### {title}\n")
    md.append(f"{note}\n")
    md.append("| " + " | ".join(headers) + " |")
    md.append("|" + "---|" * len(headers))
    for r in body:
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
        "good15": [m["_good15"] for m in metrics],
        "p90": [m["_p90"] for m in metrics],
        "prov": [m["_prov"] for m in metrics],
    }


def main():
    setups = [30, 60, 90]
    q_setups = [60, 90]
    drains = [3, 5, 8, 10, 15, 20, 30]
    md = ["# Parameter sweeps — trends & calibration\n",
          "**Demand shape:** every knob sweep below runs on the **bump** reference "
          "shape (the smooth triangular calibration demand) — only the knob varies, "
          "the demand does not. The one exception is the **Cap sweep** at the very "
          "end, which is run per sustained shape (trapezoid / step-up / step-down) "
          "and labels each explicitly.\n",
          "Metrics per run: `good%` (≤2s, pinned), `failed%` (>60s, pinned), "
          "`wait_p90` (s), `rep_max` (peak fleet), `rep·s` (usable replica-seconds), "
          "`prov·s` (billed incl. boot/drain), `util` (delivered ÷ usable capacity "
          "paid for). `*` = each section's own canonical baseline (setup=90; "
          "drain=20 for BOTH Q sizers — a standing rule so they compare on a level "
          "field; headroom=1.3; sat_frac=0.85).\n"]

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
        qa_rows.extend(([_star(s, BASE_SETUP), _star(d, BASE_DRAIN)], m)
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
                 xmark=BASE_DRAIN, mark_label="baseline")

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
    headrooms = [1.0, 1.1, 1.2, 1.3, 1.5, 1.75, 2.0]
    hr_qa = [run_qaware(BASE_SETUP, BASE_DRAIN, hr) for hr in headrooms]
    hr_qx = [run_qexp(BASE_SETUP, hr) for hr in headrooms]
    hr_rows = ([(["qaware", _star(hr, BASE_HR)], m) for hr, m in zip(headrooms, hr_qa)]
               + [(["qexp", _star(hr, BASE_HR)], m) for hr, m in zip(headrooms, hr_qx)])
    _emit("headroom — static per-replica margin (queue-aware vs Qexp)",
          "Static margin dial (§2.6) at the real 90s boot (both Q sizers at the shared "
          "drain=20). More headroom "
          "= more replicas = fewer requests per pod = shorter queue = less wait, "
          "monotonically, for more prov·s. This is headroom's CAPACITY role; its §2.7 "
          "speed role does not appear on the wait metric (see ρ note below). `*` = "
          "canonical baseline (1.3). The pick is the steepest part of the curve — max "
          "marginal quality per unit margin.", ["sizer", "headroom"], hr_rows, md)
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
    hrs2d = [1.0, 1.3, 1.5, 2.0]
    hd_groups, hd_rows = [], []
    for hr in hrs2d:
        metrics = [run_qaware(BASE_SETUP, d, hr) for d in drains]
        hd_rows.extend(([_star(hr, BASE_HR), _star(d, BASE_DRAIN)], m)
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
                 xmark=BASE_DRAIN, mark_label="baseline")

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

    # 7 — cap sweep: the actuation CEILING (max_replicas) as the swept axis, per
    # sustained shape. This is a DIFFERENT knob from HPA-queue's per-replica
    # q_target aggression (stability.md sweeps that, capped@10): raising the cap
    # lets a policy provision MORE; raising q_target makes HPA want LESS. The
    # finding: HPA-queue's raw desired (ceil of the whole backlog) runs far above
    # any sane cap, so it PINS to the cap and its cost rises ∝ cap — exactly like
    # `static`, whose fleet IS the cap. The work-rate Q sizers instead rise with
    # the cap only until they reach their natural peak (≈14–27 on these shapes),
    # then FLATTEN — a looser ceiling costs them nothing once it clears their peak.
    # So "a looser cap doesn't grow cost as fast" is a property of the Q sizers,
    # not of HPA. `ideal` is flat (peak ~5, cap never bites). Range stays bounded
    # (5→30) — no log axis.
    md.append("## Cap sweep — actuation ceiling (max_replicas) as the swept axis\n")
    md.append(
        "The seven scenarios pin `max_replicas` at the KEDA guide's 10. Here it is "
        "swept per sustained shape. **This is not the same knob as HPA-queue's "
        "`q_target`** (the per-replica queue-depth target that sets aggression — swept "
        "in `stability.md`, held ≤10 there): raising the *cap* lets a policy provision "
        "*more*; raising `q_target` makes HPA-queue want *fewer* replicas. So Dean's "
        "\"a less aggressive HPA doesn't grow cost as fast\" is about `q_target` "
        "(`stability.md`), not the cap — along *this* axis HPA-queue's cost grows fast.\n")
    md.append(
        "Reading the cost column: `hpa-queue` and `static` rise **∝ cap** — HPA's raw "
        "desired (`ceil` of the whole backlog) runs far above any sane cap, so it pins "
        "to the ceiling, just as `static`'s fleet *is* the ceiling; both hit ~2.5× ideal "
        "at cap 10 and climb to 7–9× by cap 30. The work-rate Q sizers (`queue-aware`, "
        "`qexp`) behave completely differently: their **usable** fleet peaks low (6–15 "
        "replicas on these shapes — see `rep_max`), well under every swept cap, so a "
        "looser ceiling can't be filled with useful work. Their cost still creeps up a "
        "little past that peak (speculative boot orders the backlog term issues and then "
        "cancels before they become usable — pure boot-lag waste) and then **flattens** "
        "by cap ≈15–20, staying ~1.4–2.1× ideal. Crucially that creep buys **zero** extra "
        "quality: `served ≤15s` is flat across the cap once it clears the usable peak. "
        "`ideal` is flat throughout (usable peak ~5, cap never binds).\n")
    md.append(
        "One caution on `hpa-queue`'s quality column: it is **non-monotone in the cap** "
        "(e.g. trapezoid dips at cap 15, stepup dips at cap 8) — the same deterministic "
        "dead-time / mistimed-scale-down fragility the `q_target` sweep shows in "
        "`stability.md`, not a smooth cap response. Cross-ref: for the *aggression* axis "
        "at a fixed cap, see that HPA-queue `q_target` sweep.\n")
    cap_labels = [p for p, _ in CAP_POLICIES]
    for shape in CAP_SHAPES:
        grid = {p: {cap: run_capped(p, shape, cap) for cap in CAPS}
                for p, _ in CAP_POLICIES}
        ideal = grid["ideal"]

        def cost_cell(pol, cap, _grid=grid, _ideal=ideal):
            prov = _grid[pol][cap]["_prov"]
            if pol == "ideal":
                return f"{prov:.0f}"
            iref = _ideal[cap]["_prov"]
            fac = prov / iref if iref else 0.0
            return f"{prov:.0f} ({fac:.1f}×)"

        def q_cell(pol, cap, _grid=grid):
            return f"{_grid[pol][cap]['_good15']:.1f}"

        _emit_pivot(
            f"cap sweep ({shape}) — cost: provisioned·seconds (×ideal)",
            "Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of "
            "`ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers "
            "plateau once the cap clears their natural peak.",
            "cap", CAPS, MAXR, cap_labels, cost_cell, md)
        _emit_pivot(
            f"cap sweep ({shape}) — quality: served ≤15s %",
            "Share served within 15s (the \"works\" bar). More ceiling buys the Q "
            "sizers headroom to clear the backlog; past their peak it stops mattering.",
            "cap", CAPS, MAXR, cap_labels, q_cell, md)

        groups = [_group(p, c, [grid[p][cap] for cap in CAPS])
                  for p, c in CAP_POLICIES]
        render_sweep(
            f"Cap sweep ({shape}) — cost ∝ cap (hpa-queue, static) vs plateau (Q sizers)",
            "actuation ceiling, max_replicas  — larger = higher cost allowed",
            CAPS, groups, f"{run.OUT}/17-sweep-cap-{shape}.png",
            xmark=MAXR, mark_label="baseline cap (10)")
    md.append(
        "**bump / spike are cap-inert for the Q sizers** and so are omitted from the "
        "per-shape switcher: their offered load needs only ≈4–6 replicas at the peak, "
        "well under every swept cap, so `queue-aware`/`qexp`/`ideal` never touch the "
        "ceiling there (only `hpa-queue`/`static`, which pin to the cap on any shape, "
        "would still scale with it).\n")

    path = f"{run.OUT}/sweep.md"
    with open(path, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"\n[wrote {path}]")
    print(f"[wrote {run.OUT}/11-sweep-setuplag.png, 12-sweep-drain.png, "
          f"13-sweep-qexp.png, 14-sweep-headroom.png, "
          f"15-sweep-headroom-drain.png, 16-sweep-headroom-proj.png, "
          f"17-sweep-cap-{{trapezoid,stepup,stepdown}}.png]")
    _save_cache()


if __name__ == "__main__":
    main()
