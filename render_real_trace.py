#!/usr/bin/env python3
"""Render a real-run `bundle.json` into the autoscaling-viz panels.

    python3 render_real_trace.py --bundle real-trace/<label>/bundle.json

Colour vocabulary AND panel composition are taken from the synthetic PoC
(`plots.py`) so a real run and a simulated run can be read side by side without
relearning the figure. Where the synthetic figure shades a quantity, this one
shades the same quantity in the same colour.

What is deliberately different from the synthetic figure:

  * Rates use a trailing (Prometheus-style) window, not hard bins. Hard bins
    attribute a request's whole output to its completion instant, which turns a
    backlog drain into an impossible burst -- panel 1b showed a 0<->17000 tok/s
    sawtooth that was pure bin attribution. Panel 1a keeps bars for the quality
    composition, with the trailing total drawn over them; its window is pinned to
    the bar width (W_REQ = BIN) so the curve and the bars are the SAME estimator
    at the same resolution and the curve rides the bar tops. A wider window there
    reads as a contradiction: a 20 s trailing average over 10 s bars sits at the
    mean of each adjacent pair, which in this run's mid stage is ~12 req/s under
    a 24 req/s bar.
  * Work is measured in OUTPUT TOKENS only. That is the unit the measured
    saturation ceiling (`sat_band.gen_tok_s`) is expressed in; there is no
    calibrated prefill+decode ceiling to compare a combined figure against.
  * Panel 4 draws all three queue sources rather than picking one. Which queue is
    *the* queue is an open design question (see README); until it is settled,
    showing all three is the honest option -- they measure different things and
    the difference is itself the finding.
  * Panels degrade. A run with no per-request trace still renders 2, 3, 4c and 5;
    the missing panels say why they are empty instead of vanishing.
  * Decision markers come from `desired` changes in the replica timeseries, which
    is WVA's decision as actually observed, not a simulated one. Effect markers
    come from `ready` changes and from recorded drain events.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
except ImportError:
    sys.exit('error: matplotlib is required to render.\n'
             '  uv run --with matplotlib render_real_trace.py --bundle ...\n'
             'The extractor itself needs nothing beyond the standard library.')

try:
    from plots import (C_ARR, C_DEP, C_DES, C_CEIL, C_ACT, C_CAP, C_Q, C_SYS,
                       C_WAIT, C_SERVED, C_UP, C_DOWN, C_EFF_UP, C_EFF_DN,
                       BAND_SHADES, GP_COLORS, SIZE_SHADES)
except ImportError:      # shareable standalone: fall back to the same hex values
    C_ARR, C_DEP, C_DES = '#2563eb', '#059669', '#dc2626'
    C_CEIL = C_ACT = C_CAP = C_SYS = '#7c3aed'
    C_Q, C_WAIT, C_SERVED = '#d97706', '#dc2626', '#16a34a'
    C_UP, C_DOWN = '#dc2626', '#2563eb'
    C_EFF_UP, C_EFF_DN = '#7c3aed', '#9ca3af'
    BAND_SHADES = ['#a7d8de', '#5fbcc7', '#2f9aa8', '#63c39a', '#9bd8b0']
    GP_COLORS = ['#15803d', '#65a30d', '#eab308', '#f59e0b', '#ea580c', '#b91c1c']
    SIZE_SHADES = ['#dbeafe', '#93c5fd', '#60a5fa']

INK = '#1f2937'                 # the sim's stack-top outline colour

WAIT_EDGES = [2, 15, 30, 45, 60]        # absolute wait-before-service seconds
# Panel 1a bar width. Departures in this workload are not Poisson: output lengths
# are near-monodisperse (IQR 26 tok = 5% of the median), so a cohort admitted to
# the decode batch together finishes together and the freed slots admit the next
# cohort, which sustains a ~20 s wave. Measured on the mid stage: adjacent 10 s
# bins are uncorrelated (r=-0.03) while bins 20 s apart correlate +0.59. The
# resulting peak-to-trough spread is 64x at 5 s bins, 12x at 10 s, 2.7x at 20 s.
# 10 s keeps the wave legible without pretending it is noise.
BIN = 10.0
GRID = 2.0                               # resampling step for every smooth curve
W_REQ = BIN                              # trailing window for request rates
W_WORK = 30.0                            # trailing window for work rates


# --------------------------------------------------------------------------- #

def rel(t, t0):
    return (t - t0) if t is not None else None


def binned_rate(times, t0, t1, bin_s=BIN):
    """Event times -> (centres, per-second rate). Hard bins; panel 1a bars only."""
    if not times:
        return [], []
    n = max(1, int((t1 - t0) / bin_s) + 1)
    counts = [0] * n
    for t in times:
        i = int((t - t0) / bin_s)
        if 0 <= i < n:
            counts[i] += 1
    return [(i + 0.5) * bin_s for i in range(n)], [c / bin_s for c in counts]


def trailing(times, weights, grid, window):
    """Prometheus-style rate: sum of weights in (t-window, t], divided by window.

    This is the estimator the synthetic figure uses, and the reason to prefer it
    over hard bins is not cosmetic: a request's entire output is booked at its
    completion instant, so a bin narrower than the service time reports bursts
    that never happened. A trailing window spreads the same total over the
    interval it was actually earned in.
    """
    order = sorted(zip(times, weights))
    out, lo, hi, acc = [], 0, 0, 0.0
    for t in grid:
        while hi < len(order) and order[hi][0] <= t:
            acc += order[hi][1]
            hi += 1
        while lo < hi and order[lo][0] <= t - window:
            acc -= order[lo][1]
            lo += 1
        out.append(acc / window)
    return out


def hold(by_t, grid, default=0.0):
    """Step-hold a sampled gauge onto `grid` (last value wins; honest for gauges)."""
    ks = sorted(by_t)
    out, i, cur = [], 0, default
    for t in grid:
        while i < len(ks) and ks[i] <= t:
            v = by_t[ks[i]]
            if v is not None:
                cur = v
            i += 1
        out.append(cur)
    return out


def step_series(rows, key, t0):
    xs, ys = [], []
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        xs.append(rel(r['t'], t0))
        ys.append(v)
    return xs, ys


def wait_band(r):
    """Which quality band a request falls in, by absolute wait before first token."""
    if r.get('outcome') == 'error':
        return len(WAIT_EDGES)
    w = r.get('ttft')
    if w is None:
        return 0
    for i, e in enumerate(WAIT_EDGES):
        if w < e:
            return i
    return len(WAIT_EDGES)


def empty(ax, msg):
    ax.text(0.5, 0.5, msg, transform=ax.transAxes, ha='center', va='center',
            fontsize=9, color='#6b7280', style='italic')
    ax.set_yticks([])


def mark_effects(axis, reps, t0, drains, label=False):
    """Vertical at each moment a scale decision TOOK EFFECT, same convention as
    the synthetic figure's `_mark_effects`: a `ready` increase is a boot finishing
    (purple dotted), a `ready` decrease or a recorded drain event is a drain
    completing (grey dash-dot). Drawn on every panel so the effect instant lines
    up with whatever the panel shows happening at it -- the decision lines alone
    cannot show that the capacity did not arrive for another 94 s."""
    seen_up = seen_dn = False
    events = []
    for p, q in zip(reps, reps[1:]):
        if q.get('ready') is None or p.get('ready') is None:
            continue
        if q['ready'] != p['ready']:
            events.append((rel(q['t'], t0), q['ready'] > p['ready']))
    for t in drains or []:
        # a recorded drain event that the replica series did not resolve into a
        # `ready` step (same-sample scale-down) still belongs on the figure
        if not any(abs(t - t0 - e[0]) < 1.0 for e in events):
            events.append((t - t0, False))
    for t, up in sorted(events):
        lbl = '_nolegend_'
        if label and up and not seen_up:
            lbl, seen_up = 'took effect (boot done)', True
        elif label and not up and not seen_dn:
            lbl, seen_dn = 'took effect (drain done)', True
        axis.axvline(t, color=(C_EFF_UP if up else C_EFF_DN), lw=1.0,
                     ls=((0, (1, 2)) if up else (0, (5, 2, 1, 2))),
                     alpha=0.85, zorder=3.2, label=lbl)


def terciles(values):
    """Lower/upper tercile boundaries of a sample, or None if degenerate."""
    v = sorted(x for x in values if x)
    if len(v) < 6 or v[0] == v[-1]:
        return None
    return v[len(v) // 3], v[2 * len(v) // 3]


# --------------------------------------------------------------------------- #

def render(bundle, path, title=None, coverage=None):
    meta = bundle['meta']
    reqs = bundle.get('requests') or []
    reps = bundle.get('replicas') or []
    system = bundle.get('system') or []
    pods = bundle.get('pods') or {}
    der = bundle.get('derived') or {}
    cap = der.get('capacity') or {}
    sat = der.get('sat_band') or {}
    lg = der.get('lags') or {}

    # A shared PNG has to carry its own caveats -- whoever opens it will not have the
    # extractor's stdout. `sampled` in particular changes how panels 1a/1b/5 must be
    # read: every rate is understated, not merely noisy.
    warns = list((coverage or {}).get('warnings') or [])
    sampled = any('SAMPLE' in w for w in warns)

    # Common origin: earliest timestamp across every series we actually have.
    origins = [r['t'] for r in reps[:1]] + [s['t'] for s in system[:1]]
    origins += [min(r['t_arr'] for r in reqs)] if reqs else []
    for p in pods.values():
        if p.get('series'):
            origins.append(p['series'][0]['t'])
    if not origins:
        sys.exit('error: bundle has no time series at all')
    t0 = min(origins)
    ends = [r['t'] for r in reps[-1:]] + [s['t'] for s in system[-1:]]
    ends += [max(r['t_dep'] or r['t_arr'] for r in reqs)] if reqs else []
    for p in pods.values():
        if p.get('series'):
            ends.append(p['series'][-1]['t'])
    t1 = max(ends)
    span = t1 - t0
    grid = [i * GRID for i in range(int(span / GRID) + 1)]

    # ready replicas on the smooth grid: every capacity ceiling below is per-POD,
    # so it must be multiplied by the replica count in force at that instant.
    ready_g = hold({rel(r['t'], t0): r.get('ready') for r in reps}, grid)

    fig, ax = plt.subplots(6, 1, figsize=(15, 17), sharex=True,
                           gridspec_kw={'height_ratios': [3, 3, 2, 3, 2.5, 2.5]})
    anchor = meta.get('time_anchor') or {}
    weak = anchor.get('trustworthy') is False
    head = title or (f"{meta.get('run')}  ·  {meta.get('model') or '?'}  ·  "
                     f"{meta.get('harness')}  ·  ns={meta.get('namespace') or '?'}")
    if weak:
        head += '   [WEAK TIME ANCHOR — arrival-time panels unreliable]'
    fig.suptitle(head, fontsize=12, y=0.997)

    # --- panel 1a: request rate, completions split by wait quality ---------- #
    a = ax[0]
    if reqs:
        arr_t = [rel(r['t_arr'], t0) for r in reqs]
        dep_t = [rel(r['t_dep'], t0) for r in reqs if r.get('t_dep') is not None]
        bands = {}
        for r in reqs:
            if r.get('t_dep') is not None:
                bands.setdefault(wait_band(r), []).append(r['t_dep'])
        bottom = None
        labels = [f'wait <{WAIT_EDGES[0]}s'] + \
                 [f'{WAIT_EDGES[i - 1]}-{WAIT_EDGES[i]}s'
                  for i in range(1, len(WAIT_EDGES))] + \
                 [f'>{WAIT_EDGES[-1]}s / failed']
        for i in sorted(bands):
            xs2, ys2 = binned_rate(bands[i], t0, t1)
            if not xs2:
                continue
            if bottom is None:
                bottom = [0.0] * len(ys2)
            a.bar(xs2, ys2, width=BIN * 0.95, bottom=bottom,
                  color=GP_COLORS[min(i, len(GP_COLORS) - 1)],
                  label=labels[min(i, len(labels) - 1)], zorder=1)
            bottom = [b + v for b, v in zip(bottom, ys2)]
        # Total departure rate as a trailing curve THROUGH the bar tops: the bars
        # carry the composition, this carries the total. Same events (t_dep) and,
        # because W_REQ == BIN, the same estimator -- so at each bin's right edge
        # the curve equals that bar exactly and it weaves between them in the
        # middle. Wait time sets a bar segment's COLOUR, never its height or x.
        # Same dark ink as the synthetic figure's stack-top outline.
        a.plot(grid, trailing(dep_t, [1.0] * len(dep_t), grid, W_REQ),
               color=INK, lw=2.2, alpha=0.85, zorder=2.6,
               label=f'departure rate, total ({W_REQ:.0f}s trailing)')
        a.plot(grid, trailing(arr_t, [1.0] * len(arr_t), grid, W_REQ),
               color=C_ARR, lw=2.4, zorder=2.7,
               label=f'arrival rate ({W_REQ:.0f}s trailing)')
        n_tr = sum(1 for r in reqs if r.get('outcome') == 'truncated')
        a.set_title(f'requests: {len(reqs)} offered, {n_tr} cut off at run end'
                    + ('   — SAMPLE ONLY, rates understated' if sampled else ''),
                    fontsize=8, loc='right',
                    color='#b45309' if sampled else '#6b7280')
    else:
        empty(a, 'no per-request trace in this bundle — '
                 'fetch results.json / per_request_lifecycle_metrics.json')
    a.set_ylabel('requests / s')
    a.set_title(f'1a · request throughput + goodput quality  '
                f'(bars: {BIN:.0f}s bins, coloured by wait before first token)',
                loc='left', fontsize=10)

    # --- panel 1b: work throughput vs capacity ------------------------------ #
    # Work = OUTPUT TOKENS. Offered work is booked at arrival (the tokens that
    # request will demand), completed work at departure (the tokens delivered),
    # so the gap between the two curves is backlog in token units. The ceiling is
    # the measured saturated generation rate, which is PER POD -- hence
    # ready(t) x gen_tok_s, a step that rises when a boot completes.
    b = ax[1]
    drew_b = False
    if reqs:
        arr_t = [rel(r['t_arr'], t0) for r in reqs]
        arr_w = [float(r.get('out_tok') or 0) for r in reqs]
        b.plot(grid, trailing(arr_t, arr_w, grid, W_WORK), color=C_ARR, lw=2.4,
               zorder=2.7, label=f'offered work ({W_WORK:.0f}s trailing)')
        done = [r for r in reqs if r.get('t_dep') is not None]
        tc = terciles([r.get('out_tok') for r in done])
        if tc:
            lo_e, hi_e = tc
            buckets = [[], [], []]
            for r in done:
                ot = r.get('out_tok') or 0
                k = 0 if ot <= lo_e else (1 if ot <= hi_e else 2)
                buckets[k].append(r)
            stacks = [trailing([rel(r['t_dep'], t0) for r in bk],
                               [float(r.get('out_tok') or 0) for r in bk],
                               grid, W_WORK) for bk in buckets]
            lbls = [f'small (≤{lo_e:.0f} tok)', f'medium ({lo_e:.0f}–{hi_e:.0f})',
                    f'large (>{hi_e:.0f})']
            b.stackplot(grid, *stacks, colors=SIZE_SHADES, labels=lbls,
                        alpha=0.6, edgecolor='none')
            total_w = [sum(v) for v in zip(*stacks)]
        else:
            total_w = trailing([rel(r['t_dep'], t0) for r in done],
                               [float(r.get('out_tok') or 0) for r in done],
                               grid, W_WORK)
            b.stackplot(grid, total_w, colors=[SIZE_SHADES[1]], alpha=0.6,
                        edgecolor='none', labels=['completed work'])
        b.plot(grid, total_w, color=INK, lw=2.2, alpha=0.85, zorder=2.6,
               label='completed work, total')
        drew_b = True
    # Two measured per-pod token rates, and they are NOT interchangeable. The knee
    # rate is the most a pod ever sustained. The sat-band rate is what it delivers
    # once kv >= threshold, where preemption starts destroying already-generated
    # work -- lower, by the cost of running past the watermark. Using the sat-band
    # rate as THE ceiling put delivered work 29% above its own ceiling on the
    # 2026-08-07 staircase (peak 10201 tok/s against 2x3941), which is why the
    # knee is the ceiling here and the sat-band rate is drawn as a second, dotted
    # reference: the gap between them is what the 0.85 watermark buys.
    knee = der.get('tput_knee') or {}
    knee_rate = knee.get('gen_tok_s') if knee.get('confident') else None
    sat_rate = sat.get('gen_tok_s')
    ceil_rate = knee_rate or sat_rate
    if ceil_rate and reps:
        ceil = [v * ceil_rate for v in ready_g]
        src = (f"throughput knee, n={knee.get('n')}" if knee_rate
               else f"saturated at kv≥{sat.get('threshold')}")
        b.plot(grid, ceil, color=C_CAP, ls='--', lw=1.6, zorder=2.5,
               label=f'capacity ceiling (ready × {ceil_rate:.0f} tok/s per pod; {src})')
        if knee_rate and sat_rate and abs(sat_rate - knee_rate) > 0.02 * knee_rate:
            b.plot(grid, [v * sat_rate for v in ready_g], color=C_CAP, ls=':',
                   lw=1.3, alpha=0.8, zorder=2.4,
                   label=f'delivered rate once kv≥{sat.get("threshold")} '
                         f'({sat_rate:.0f} tok/s per pod — preemption cost)')
        if drew_b:
            # capacity paid for but not used, only where the ceiling is above what
            # was delivered. Same purple, same alpha as the synthetic figure.
            b.fill_between(grid, total_w, ceil,
                           where=[c > d for c, d in zip(ceil, total_w)],
                           interpolate=True, color=C_CAP, alpha=0.15,
                           label='unused capacity')
        drew_b = True
    if not drew_b:
        empty(b, 'no throughput view available')
    b.set_ylabel('output tokens / s')
    b.set_title(f'1b · work throughput: output tokens offered vs delivered vs '
                f'capacity  ({W_WORK:.0f}s trailing, Prom-style)',
                loc='left', fontsize=10)

    # --- panel 2: replicas desired vs ready --------------------------------- #
    c = ax[2]
    if reps:
        xs = [rel(r['t'], t0) for r in reps]
        dz = [r.get('desired') for r in reps]
        rz = [r.get('ready') for r in reps]
        # tiny opposite y-offsets and equal weights, exactly as the synthetic
        # figure: once ready catches up the two coincide, and neither may hide.
        c.step(xs, [v + 0.05 if v is not None else None for v in dz], where='post',
               color=C_DES, lw=2.2, alpha=0.9, label='desired (WVA)')
        c.step(xs, [v - 0.05 if v is not None else None for v in rz], where='post',
               color=C_ACT, lw=2.2, alpha=0.9, label='ready (alive)')
        # A replica that is alive but no longer wanted is draining: still finishing
        # in-flight work, not accepting new work, so NOT usable capacity. Kept even
        # though this run has none -- if a future run drains, the band appears
        # without a code change, and its absence here is itself the finding.
        if all(v is not None for v in dz + rz):
            accepting = [min(d, r) for d, r in zip(dz, rz)]
            if any(r > acc for r, acc in zip(rz, accepting)):
                c.fill_between(xs, accepting, rz, step='post', facecolor='none',
                               hatch='////', edgecolor=C_ACT, linewidth=0.0,
                               alpha=0.6, label='draining (not usable capacity)')
        note = (f"boot {lg['boot_s_mean']:.0f}s mean over "
                f"{len(lg.get('boot_s') or [])} step(s)"
                if lg.get('boot_s_mean') else 'boot lag not measurable')
        if not lg.get('scaledown_observed'):
            note += ' · no scale-down in this run'
        elif not any(r > min(d, r) for d, r in zip(dz, rz) if None not in (d, r)):
            note += ' · scale-down took effect within one scrape (no drain window)'
        c.set_title(note, fontsize=8, loc='right', color='#6b7280')
    else:
        empty(c, 'no replica_status_timeseries.json')
    c.set_ylabel('replicas')
    c.yaxis.set_major_locator(MaxNLocator(integer=True))
    c.set_title('2 · autoscaling: desired vs ready replicas', loc='left', fontsize=10)

    # --- panel 3: requests per pod -- running, waiting, then EPP ------------- #
    # Stack order is deliberate: all pods' RUNNING at the bottom (the work that is
    # actually progressing), then each pod's WAITING in the same colour but hatched
    # (admitted to that engine, not yet running), then whatever the router is
    # holding that no engine has yet.
    #
    # The top band is NOT `q_dispatch`: EPP's `inference_objective_running_requests`
    # already counts everything at the pods, waiting and running, so stacking it
    # would double-count the two bands below it. It is the residual
    # max(0, in_system − Σrun − Σwait), which makes the stack total identically
    # in_system -- so the overlay line rides on the stack top, and any daylight
    # between them is a decomposition error you can see.
    d = ax[3]
    if pods:
        pgrid = sorted({round(s['t']) for p in pods.values() for s in p['series']})
        xs = [t - t0 for t in pgrid]
        width = max(1.0, span / max(1, len(pgrid)) * 0.95)
        bottom = [0.0] * len(pgrid)
        run_tot = [0.0] * len(pgrid)
        wait_tot = [0.0] * len(pgrid)
        ordered = sorted(pods.items())
        for i, (pod, p) in enumerate(ordered):
            by_t = {round(s['t']): s.get('run') for s in p['series']}
            ys = [by_t.get(t) or 0.0 for t in pgrid]
            d.bar(xs, ys, width=width, bottom=bottom,
                  color=BAND_SHADES[i % len(BAND_SHADES)],
                  label=f'{pod.split("-")[-1]} running', zorder=1)
            bottom = [bt + y for bt, y in zip(bottom, ys)]
            run_tot = [a_ + y for a_, y in zip(run_tot, ys)]
        for i, (pod, p) in enumerate(ordered):
            by_t = {round(s['t']): s.get('wait') for s in p['series']}
            ys = [by_t.get(t) or 0.0 for t in pgrid]
            if not any(ys):
                continue
            d.bar(xs, ys, width=width, bottom=bottom,
                  color=BAND_SHADES[i % len(BAND_SHADES)], alpha=0.55,
                  hatch='////', edgecolor=INK, linewidth=0.0,
                  label=f'{pod.split("-")[-1]} waiting', zorder=1)
            bottom = [bt + y for bt, y in zip(bottom, ys)]
            wait_tot = [a_ + y for a_, y in zip(wait_tot, ys)]
        # router-side residual, on the pod grid (nearest system sample)
        sys_by_t = {round(s['t']): s.get('in_system') for s in system
                    if s.get('in_system') is not None}
        insys_p = hold(sys_by_t, pgrid) if sys_by_t else None
        if insys_p:
            epp = [max(0.0, n - r - w)
                   for n, r, w in zip(insys_p, run_tot, wait_tot)]
            if any(epp):
                d.bar(xs, epp, width=width, bottom=bottom, color=C_Q, alpha=0.75,
                      label='router-side (in system − Σrun − Σwait)', zorder=1)
        if cap.get('max_conc_pred') and reps:
            xr, yr = step_series(reps, 'ready', t0)
            d.step(xr, [v * cap['max_conc_pred'] for v in yr], where='post',
                   color=C_CEIL, ls='--', lw=1.6, zorder=2.5,
                   label=f"KV ceiling (ready × {cap['max_conc_pred']:.0f}/pod)")
        if sys_by_t:
            # thick overlay, NOT part of the stack
            xn, yn = step_series(system, 'in_system', t0)
            d.plot(xn, yn, color=C_WAIT, lw=2.4, alpha=0.9, zorder=2.8,
                   label='total requests in system (overlay)')
        r = der.get('router') or {}
        d.set_title(f"router: {r.get('leader_flips', '?')} leader flips, "
                    f"dispersion p95={r.get('disp_p95') and round(r['disp_p95'], 2)}"
                    f"{' — OSCILLATING' if r.get('oscillation_flag') else ''}",
                    fontsize=8, loc='right', color='#6b7280')
    else:
        empty(d, 'no metrics/raw/ scrapes — per-pod view unavailable')
    d.set_ylabel('requests')
    d.set_title('3 · requests per pod: running, waiting, router-side  '
                '(stack ≡ in system)', loc='left', fontsize=10)

    # --- panel 4: the three queues (INTERIM — design deferred) -------------- #
    e = ax[4]
    drawn = False
    for key, colour, lab in (
            ('q_engine', C_Q, '(c) engine: sum of vllm num_requests_waiting'),
            ('q_dispatch', C_WAIT, '(b) EPP dispatch: in system, waiting AND served'),
            ('q_flow', C_ARR, '(a) derived flow-control: in-system − dispatch')):
        xs, ys = step_series(system, key, t0)
        if xs:
            e.plot(xs, ys, color=colour, lw=1.3, label=lab)
            drawn = True
    if drawn:
        e.set_title('INTERIM: all three queue sources shown; which one panel 4 '
                    'should draw is an open design question',
                    fontsize=8, loc='right', color='#b45309')
    else:
        empty(e, 'no queue signal (needs metrics/raw/ and/or a request trace)')
    e.set_ylabel('queued')
    e.set_title('4 · queue sources', loc='left', fontsize=10)

    # --- panel 5: concurrency L(t) vs slot capacity ------------------------- #
    # Same composition as the synthetic figure: the gap between served and
    # in-system IS the queue (shaded red), and the gap between served and the
    # ceiling is capacity paid for and not used (shaded purple).
    f = ax[5]
    nsys_g = None
    sys_by_t = {rel(s['t'], t0): s.get('in_system') for s in system
                if s.get('in_system') is not None}
    if sys_by_t:
        nsys_g = hold(sys_by_t, grid)
    served_by_t = {}
    for p in pods.values():
        for s in p['series'] or []:
            if s.get('run') is not None:
                k = round(s['t'])
                served_by_t[k] = served_by_t.get(k, 0.0) + s['run']
    served_g = hold({k - t0: v for k, v in served_by_t.items()},
                    grid) if served_by_t else None
    slots_g = ([v * cap['max_conc_pred'] for v in ready_g]
               if cap.get('max_conc_pred') and reps else None)

    if served_g and slots_g:
        f.fill_between(grid, served_g, slots_g,
                       where=[c > s for c, s in zip(slots_g, served_g)],
                       interpolate=True, color=C_CAP, alpha=0.15,
                       label='unused capacity')
    if served_g and nsys_g:
        f.fill_between(grid, served_g, nsys_g, color=C_WAIT, alpha=0.16,
                       label='queued (L − served)')
    if nsys_g:
        f.plot(grid, nsys_g, color=C_WAIT, lw=1.6, alpha=0.9,
               label='in system  L(t)' + (' — SAMPLE' if sampled else ''))
    if served_g:
        f.plot(grid, served_g, color=C_SERVED, lw=1.4, alpha=0.95,
               label='being served (Σ pod running)')
    if slots_g:
        f.plot(grid, slots_g, color=C_CEIL, ls='--', lw=1.6,
               label=f"usable slot capacity (ready × {cap['max_conc_pred']:.0f})")
    if nsys_g or served_g:
        fit = der.get('itl_fit') or {}
        if fit.get('A_ms_per_req'):
            f.set_title(f"ITL = {fit['A_ms_per_req']:.3f}·k + {fit['B_ms']:.1f} ms "
                        f"on kv∈[{fit.get('y_lo')},{fit.get('y_hi')}] "
                        f"(r²={fit.get('r2', 0):.2f}, n={fit.get('n')})"
                        + ('  ρ=%.2f' % fit['rho'] if fit.get('rho') else ''),
                        fontsize=8, loc='right', color='#6b7280')
    else:
        empty(f, 'no concurrency signal')
    f.set_ylabel('requests')
    f.set_xlabel('seconds since run start')
    f.set_title('5 · concurrency: requests in system vs slot capacity  (L = λ·W)',
                loc='left', fontsize=10)

    drains = lg.get('drain_events') or []
    for i, axis in enumerate(ax):
        axis.grid(alpha=.25, lw=.5)
        axis.set_xlim(0, span)
        axis.margins(x=0)
        # WVA's observed decisions, drawn on every panel so the triggering signal
        # lines up with the decision instant...
        for p, q in zip(reps, reps[1:]):
            if q['desired'] != p['desired']:
                axis.axvline(rel(q['t'], t0), lw=1.0, ls=(0, (4, 3)),
                             color=C_UP if q['desired'] > p['desired'] else C_DOWN,
                             alpha=.55, zorder=3)
        # ...and the moments those decisions took effect, which is a different
        # instant entirely: one boot lag later for up, a drain later for down.
        mark_effects(axis, reps, t0, drains, label=(axis is ax[2]))
        if i in (0, 1, 3):
            axis.legend(loc='upper left', fontsize=6.5, ncol=1, labelspacing=0.3,
                        handlelength=1.4, borderpad=0.4, framealpha=0.85)
        else:
            axis.legend(loc='upper right', fontsize=7.5, ncol=2, framealpha=0.9)

    foot = ''
    if warns:
        foot = 'caveats: ' + '  |  '.join(
            w.split(' - ')[0].split(' -- ')[0] for w in warns)
    fails = [r['capability'] for r in (coverage or {}).get('rows', [])
             if r['verdict'] == 'FAIL']
    if fails:
        foot += ('\n' if foot else '') + 'not exercised by this run: ' + ', '.join(fails)
    if foot:
        fig.text(0.008, 0.004, foot, fontsize=7, color='#b45309', va='bottom')

    fig.tight_layout(rect=(0, 0.022 if foot else 0, 1, 0.985))
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--out', help='output PNG (default: panels.png beside the bundle)')
    ap.add_argument('--title')
    a = ap.parse_args(argv)

    with open(a.bundle) as fh:
        bundle = json.load(fh)
    here = os.path.dirname(os.path.abspath(a.bundle))

    cov = None
    cov_path = os.path.join(here, 'coverage.json')
    if os.path.exists(cov_path):
        with open(cov_path) as fh:
            cov = json.load(fh)

    out = a.out or os.path.join(here, 'panels.png')
    render(bundle, out, a.title, cov)
    print(f'wrote {out}')

    if cov:
        fails = [r['capability'] for r in cov['rows'] if r['verdict'] == 'FAIL']
        print(f"coverage: {cov['n_pass']} PASS / {cov['n_fail']} FAIL")
        if fails:
            print('  not supported by this run: ' + ', '.join(fails))
    else:
        print('note: no coverage.json beside the bundle — the figure will not carry '
              'its caveats. Re-run extract_real_trace.py to produce it.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
