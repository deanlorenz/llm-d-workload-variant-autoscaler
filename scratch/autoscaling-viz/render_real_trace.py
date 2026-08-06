#!/usr/bin/env python3
"""Render a real-run `bundle.json` into the autoscaling-viz panels.

    python3 render_real_trace.py --bundle real-trace/<label>/bundle.json

Colour vocabulary is imported from the synthetic PoC (`plots.py`) so a real run and
a simulated run can be read side by side without relearning the figure.

What is deliberately different from the synthetic figure:

  * Panel 4 draws all three queue sources rather than picking one. Which queue is
    *the* queue is an open design question (see README); until it is settled,
    showing all three is the honest option -- they measure different things and
    the difference is itself the finding.
  * Panels degrade. A run with no per-request trace still renders 2, 3, 4c and 5;
    the missing panels say why they are empty instead of vanishing.
  * Decision markers come from `desired` changes in the replica timeseries, which
    is WVA's decision as actually observed, not a simulated one.
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
except ImportError:
    sys.exit('error: matplotlib is required to render.\n'
             '  uv run --with matplotlib render_real_trace.py --bundle ...\n'
             'The extractor itself needs nothing beyond the standard library.')

try:
    from plots import (C_ARR, C_DEP, C_DES, C_CEIL, C_Q, C_WAIT, C_SERVED,
                       C_UP, C_DOWN, BAND_SHADES, GP_COLORS)
except ImportError:      # shareable standalone: fall back to the same hex values
    C_ARR, C_DEP, C_DES, C_CEIL = '#2563eb', '#059669', '#dc2626', '#7c3aed'
    C_Q, C_WAIT, C_SERVED = '#d97706', '#dc2626', '#16a34a'
    C_UP, C_DOWN = '#dc2626', '#2563eb'
    BAND_SHADES = ['#a7d8de', '#5fbcc7', '#2f9aa8', '#63c39a', '#9bd8b0']
    GP_COLORS = ['#15803d', '#65a30d', '#eab308', '#f59e0b', '#ea580c', '#b91c1c']

WAIT_EDGES = [2, 15, 30, 45, 60]        # absolute wait-before-service seconds
BIN = 5.0                                # histogram bin, seconds


# --------------------------------------------------------------------------- #

def rel(t, t0):
    return (t - t0) if t is not None else None


def binned_rate(times, t0, t1, bin_s=BIN):
    """Event times -> (centres, per-second rate)."""
    if not times:
        return [], []
    n = max(1, int((t1 - t0) / bin_s) + 1)
    counts = [0] * n
    for t in times:
        i = int((t - t0) / bin_s)
        if 0 <= i < n:
            counts[i] += 1
    return [(i + 0.5) * bin_s for i in range(n)], [c / bin_s for c in counts]


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


# --------------------------------------------------------------------------- #

def render(bundle, path, title=None, coverage=None):
    meta = bundle['meta']
    reqs = bundle.get('requests') or []
    reps = bundle.get('replicas') or []
    system = bundle.get('system') or []
    pods = bundle.get('pods') or {}
    der = bundle.get('derived') or {}

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

    fig, ax = plt.subplots(6, 1, figsize=(15, 17), sharex=True,
                           gridspec_kw={'height_ratios': [3, 3, 2, 3, 2.5, 2]})
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
        xs, ys = binned_rate([r['t_arr'] for r in reqs], t0, t1)
        a.plot(xs, ys, color=C_ARR, lw=1.6, label='offered (arrivals)')
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
        a.legend(fontsize=7, ncol=4, loc='upper left', framealpha=.9)
        n_tr = sum(1 for r in reqs if r.get('outcome') == 'truncated')
        a.set_title(f'requests: {len(reqs)} offered, {n_tr} cut off at run end'
                    + ('   — SAMPLE ONLY, rates understated' if sampled else ''),
                    fontsize=8, loc='right',
                    color='#b45309' if sampled else '#6b7280')
    else:
        empty(a, 'no per-request trace in this bundle — '
                 'fetch results.json / per_request_lifecycle_metrics.json')
    a.set_ylabel('requests / s')

    # --- panel 1b: token throughput vs capacity ---------------------------- #
    b = ax[1]
    # Generation rate is a counter-delta quantity, so it cannot be reconstructed from
    # the per-pod gauge series in the bundle. The two views that *are* available: token
    # completions from the request trace, and the saturated rate from the sat band.
    if reqs:
        dep = [(r['t_dep'], r.get('out_tok') or 0) for r in reqs
               if r.get('t_dep') is not None]
        n = max(1, int(span / BIN) + 1)
        acc = [0.0] * n
        for t, tok in dep:
            i = int((t - t0) / BIN)
            if 0 <= i < n:
                acc[i] += tok
        b.plot([(i + .5) * BIN for i in range(n)], [v / BIN for v in acc],
               color=C_DEP, lw=1.4, label='output tokens / s (completed)')
    sat = der.get('sat_band') or {}
    if sat.get('gen_tok_s'):
        b.axhline(sat['gen_tok_s'], color=C_CEIL, ls='--', lw=1.2,
                  label=f"saturated generation rate ({sat['gen_tok_s']:.0f} tok/s "
                        f"at kv>={sat.get('threshold')})")
    if not reqs and not sat.get('gen_tok_s'):
        empty(b, 'no throughput view available')
    else:
        b.legend(fontsize=7, loc='upper left', framealpha=.9)
    b.set_ylabel('tokens / s')

    # --- panel 2: replicas desired vs ready -------------------------------- #
    c = ax[2]
    if reps:
        xd, yd = step_series(reps, 'desired', t0)
        xr, yr = step_series(reps, 'ready', t0)
        # ready first, then desired on top: once ready catches up the two coincide, and
        # the decision line is the one that must stay legible.
        c.step(xr, yr, where='post', color=C_CEIL, lw=2.6, label='ready')
        c.fill_between(xr, yr, step='post', color=C_CEIL, alpha=.10)
        c.step(xd, yd, where='post', color=C_DES, lw=1.5, ls=(0, (4, 2)),
               label='desired (WVA/HPA)')
        lg = der.get('lags') or {}
        note = (f"boot {lg['boot_s_mean']:.0f}s mean over "
                f"{len(lg.get('boot_s') or [])} step(s)"
                if lg.get('boot_s_mean') else 'boot lag not measurable')
        if not lg.get('scaledown_observed'):
            note += ' · no scale-down in this run'
        c.set_title(note, fontsize=8, loc='right', color='#6b7280')
        c.legend(fontsize=7, loc='upper left', framealpha=.9)
    else:
        empty(c, 'no replica_status_timeseries.json')
    c.set_ylabel('replicas')

    # --- panel 3: per-pod concurrency, stacked ----------------------------- #
    d = ax[3]
    if pods:
        grid = sorted({round(s['t']) for p in pods.values() for s in p['series']})
        bottom = [0.0] * len(grid)
        for i, (pod, p) in enumerate(sorted(pods.items())):
            by_t = {round(s['t']): s.get('run') for s in p['series']}
            ys = [by_t.get(t) or 0.0 for t in grid]
            xs = [t - t0 for t in grid]
            d.bar(xs, ys, width=max(1.0, span / max(1, len(grid)) * .95),
                  bottom=bottom, color=BAND_SHADES[i % len(BAND_SHADES)],
                  label=pod.split('-')[-1], zorder=1)
            bottom = [bt + y for bt, y in zip(bottom, ys)]
        cap = der.get('capacity') or {}
        if cap.get('max_conc_pred') and reps:
            xr, yr = step_series(reps, 'ready', t0)
            d.step(xr, [v * cap['max_conc_pred'] for v in yr], where='post',
                   color=C_CEIL, ls='--', lw=1.4,
                   label=f"KV ceiling ({cap['max_conc_pred']:.0f}/pod)")
        r = der.get('router') or {}
        d.set_title(f"router: {r.get('leader_flips', '?')} leader flips, "
                    f"dispersion p95={r.get('disp_p95') and round(r['disp_p95'], 2)}"
                    f"{' — OSCILLATING' if r.get('oscillation_flag') else ''}",
                    fontsize=8, loc='right', color='#6b7280')
        d.legend(fontsize=6, ncol=6, loc='upper left', framealpha=.9)
    else:
        empty(d, 'no metrics/raw/ scrapes — per-pod view unavailable')
    d.set_ylabel('running / pod')

    # --- panel 4: the three queues (INTERIM — design deferred) ------------- #
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
        e.legend(fontsize=7, loc='upper left', framealpha=.9)
        e.set_title('INTERIM: all three queue sources shown; which one panel 4 '
                    'should draw is an open design question',
                    fontsize=8, loc='right', color='#b45309')
    else:
        empty(e, 'no queue signal (needs metrics/raw/ and/or a request trace)')
    e.set_ylabel('queued')

    # --- panel 5: concurrency L(t) ----------------------------------------- #
    f = ax[5]
    xs, ys = step_series(system, 'in_system', t0)
    if xs:
        f.plot(xs, ys, color=C_WAIT, lw=1.4,
               label='L(t) in system (from requests)'
                     + (' — SAMPLE' if sampled else ''))
    served = {}
    for p in pods.values():
        for s in p['series'] or []:
            if s.get('run') is not None:
                k = round(s['t'])
                served[k] = served.get(k, 0.0) + s['run']
    if served:
        ks = sorted(served)
        f.plot([k - t0 for k in ks], [served[k] for k in ks],
               color=C_SERVED, lw=1.4, label='being served (sum of pod running)')
    if xs or served:
        fit = der.get('itl_fit') or {}
        if fit.get('A_ms_per_req'):
            f.set_title(f"ITL = {fit['A_ms_per_req']:.3f}·k + {fit['B_ms']:.1f} ms "
                        f"on kv∈[{fit.get('y_lo')},{fit.get('y_hi')}] "
                        f"(r²={fit.get('r2', 0):.2f}, n={fit.get('n')})"
                        + ('  ρ=%.2f' % fit['rho'] if fit.get('rho') else ''),
                        fontsize=8, loc='right', color='#6b7280')
        f.legend(fontsize=7, loc='upper left', framealpha=.9)
    else:
        empty(f, 'no concurrency signal')
    f.set_ylabel('requests')
    f.set_xlabel('seconds since run start')

    for axis in ax:
        axis.grid(alpha=.25, lw=.5)
        axis.set_xlim(0, span)
        # WVA's observed decisions, drawn on every panel so the triggering signal
        # lines up with the decision instant.
        for p, q in zip(reps, reps[1:]):
            if q['desired'] != p['desired']:
                axis.axvline(rel(q['t'], t0), lw=.9, ls='--',
                             color=C_UP if q['desired'] > p['desired'] else C_DOWN,
                             alpha=.55, zorder=0)

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
