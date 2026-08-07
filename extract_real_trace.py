#!/usr/bin/env python3
"""Extract a real benchmark run into a compact `bundle.json` + `coverage.json`.

One run directory in, two small files out. The bundle is the complete input to the
autoscaling-viz panels; the coverage report says which panels and which calibrations
*this particular run* can actually support.

Two harnesses are supported and auto-detected from `run_metadata.yaml: harness_name`:

  inference-perf   per_request_lifecycle_metrics.json  (can be multi-GB)
  guidellm         results.json                        (100-200 MB)

Design constraints (this is meant to run on someone else's machine, on their data):
  * standard library only
  * no hardcoded pod names, namespaces, model ids or run ids
  * every optional artifact may be missing -> a coverage FAIL row, never a traceback
  * the big per-request files are streamed, never json.load()ed whole
  * prompt text is never copied into the bundle

Usage:
    python3 extract_real_trace.py --run <run-dir> [--out <dir>]
                                  [--no-per-request] [--head N] [--quiet]

See real-trace-viz-plan.md sections 8 (spec), 1.2 (readers) and 9 (coverage).
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys

# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #

SAT = 0.85          # kv fraction at/above which the engine is saturated (Dean)
FIT_HI = 0.85       # upper edge of the ITL linear-validity window
Y_LO_SCAN = (0.0, 0.1, 0.2, 0.3, 0.4)   # candidate lower knees
MIN_FIT_N = 8       # minimum stable intervals for a usable A
MAX_DT = 40.0       # reject scrape intervals longer than this (missed rounds)
STABLE_DRUN = 25    # |delta running| tolerated inside a "stable" interval

# anchor validation: engine occupancy must not exceed request-derived in-system
# count (see anchor_offset). Tolerances absorb per-pod scrape skew, nothing more.
OVER_L_FLOOR = 3.0      # requests of slack at small occupancy
OVER_L_REL = 0.10       # ... or this fraction of occupancy, whichever is larger
OVER_L_MAX_FRAC = 0.05  # fraction of scrapes allowed to exceed that slack

GAUGE = {
    'run':  'vllm:num_requests_running',
    'wait': 'vllm:num_requests_waiting',
    'kv':   'vllm:kv_cache_usage_perc',
}
CTR = {
    'gen':     'vllm:generation_tokens_total',
    'prompt':  'vllm:prompt_tokens_total',
    'ok':      'vllm:request_success_total',
    'preempt': 'vllm:num_preemptions_total',
    'pfxh':    'vllm:prefix_cache_hits_total',
    'pfxq':    'vllm:prefix_cache_queries_total',
}
HIST = {
    'itl': 'vllm:inter_token_latency_seconds',
    'e2e': 'vllm:e2e_request_latency_seconds',
    'pf':  'vllm:request_prefill_time_seconds',
    'dec': 'vllm:request_decode_time_seconds',
    'qw':  'vllm:request_queue_time_seconds',
    'ttft': 'vllm:time_to_first_token_seconds',
}
CACHE_CFG = 'vllm:cache_config_info'
EPP_RUNNING = 'inference_objective_running_requests'
# EPP pods are named ...-gaie-epp-... on some installs and ...-router-epp-... on others.
EPP_RE = re.compile(r'(gaie-epp|router-epp|[-_]epp[-_])')

WARN: list[str] = []


def warn(msg: str) -> None:
    WARN.append(msg)


# --------------------------------------------------------------------------- #
# tiny helpers
# --------------------------------------------------------------------------- #

def read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        if default is None:
            warn(f'unreadable {os.path.basename(path)}: {exc}')
        return default


def read_flat_yaml(path):
    """run_metadata.yaml is flat `key: "value"`, but some values span lines.

    Only top-level `key:` lines are taken; continuation lines are ignored. This
    avoids a PyYAML dependency (constraint: standard library only).
    """
    out = {}
    try:
        with open(path) as fh:
            for line in fh:
                m = re.match(r'^([A-Za-z_][\w.]*):\s*(.*)$', line)
                if m:
                    out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def iso_dur_seconds(s):
    """PT803.44S -> 803.44 . Returns None when unparseable."""
    if not s:
        return None
    m = re.match(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?$', s.strip())
    if not m:
        return None
    h, mi, sec = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(sec or 0)


def iso_epoch(s):
    """Parse an ISO-8601 instant to epoch seconds without dateutil."""
    if not s:
        return None
    s = s.strip().replace('Z', '+00:00')
    try:
        import datetime
        return datetime.datetime.fromisoformat(s).timestamp()
    except (ValueError, ImportError):
        return None


def pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    i = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
    return v[i]


def mean(vals):
    return sum(vals) / len(vals) if vals else None


def linfit(xs, ys):
    """Ordinary least squares. Returns (slope, intercept, r2, n)."""
    n = len(xs)
    if n < 2:
        return None, None, None, n
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None, None, None, n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx
    b = my - a * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = 0.0 if syy <= 0 else max(0.0, 1.0 - sum((y - (a * x + b)) ** 2
                                                 for x, y in zip(xs, ys)) / syy)
    return a, b, r2, n


# --------------------------------------------------------------------------- #
# streaming JSON record reader
# --------------------------------------------------------------------------- #

def iter_json_objects(fh, marker=None, chunk=1 << 20, limit=None):
    """Yield decoded top-level JSON objects from the array following `marker`.

    Needed because the per-request files reach several GB; json.load() on those
    is not an option on a laptop. Brace-depth scan with string/escape awareness.
    """
    buf = ''
    if marker:
        while True:
            if marker in buf:
                buf = buf[buf.index(marker) + len(marker):]
                break
            piece = fh.read(chunk)
            if not piece:
                return
            buf += piece
            # bound the search buffer, keeping an overlap for a split marker
            if len(buf) > 8 * chunk:
                buf = buf[-(len(marker) + 8):]

    depth = 0
    start = None
    in_str = False
    esc = False
    emitted = 0
    i = 0
    while True:
        while i < len(buf):
            ch = buf[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        yield json.loads(buf[start:i + 1])
                    except ValueError as exc:
                        warn(f'skipped malformed record: {exc}')
                    emitted += 1
                    if limit and emitted >= limit:
                        return
                    buf = buf[i + 1:]
                    i, start = 0, None
                    continue
            elif ch == ']' and depth == 0:
                return
            i += 1
        piece = fh.read(chunk)
        if not piece:
            return
        if depth == 0:
            buf, i = piece, 0     # between records: safe to drop the prefix
        else:
            buf += piece


# --------------------------------------------------------------------------- #
# demand readers (section 1.2)
# --------------------------------------------------------------------------- #

def read_guidellm(path, limit=None):
    """benchmarks[0].requests.{successful,incomplete,errored}[]

    Timestamps are epoch floats on the same clock as the scrape filenames, so no
    anchoring is needed. `ignore_eos` + `max_completion_tokens` make the output
    token count exact -> no inflation correction (see plan section 1.2).
    """
    out = []
    for outcome, marker in (('ok', '"successful": ['),
                            ('truncated', '"incomplete": ['),
                            ('error', '"errored": [')):
        with open(path) as fh:
            for rec in iter_json_objects(fh, marker=marker, limit=limit):
                if rec.get('type_') != 'generative_request_stats':
                    continue
                t0 = rec.get('request_start_time')
                t1 = rec.get('request_end_time')
                if t0 is None:
                    continue
                info = rec.get('info') or {}
                tim = info.get('timings') or {}
                ft = tim.get('first_token_iteration')
                lt = tim.get('last_token_iteration')
                nit = tim.get('token_iterations')
                itl = None
                if ft and lt and nit and nit > 1:
                    itl = (lt - ft) / (nit - 1) * 1000.0
                elif rec.get('inter_token_latency_ms') is not None:
                    itl = rec['inter_token_latency_ms']
                ttft = rec.get('time_to_first_token_ms')
                out.append({
                    't_arr': t0,
                    't_dep': t1,
                    'in_tok': rec.get('prompt_tokens'),
                    'out_tok': rec.get('output_tokens'),
                    'ttft': (ttft / 1000.0) if ttft is not None else None,
                    'itl_true': itl,
                    'outcome': outcome,
                })
    return out


def read_inference_perf(path, limit=None):
    """Flat array of per-request records; payload lives under info.response_info.

    Two traps, both verified on a real run:

    * `start_time` / `end_time` are a *monotonic* clock, not epoch, so these need
      the section-2 anchor (see anchor_offset).
    * the client output count is inflated ~2x versus the server count
      (`output_tokens` 1018 vs `server_usage.completion_tokens` 516 on the
      reference run) because streamed chunks are double-counted. The server
      count wins, always, and it is also the correct ITL denominator.

    `info.extra_info.raw_response` holds the entire response body; it is never read.
    """
    out = []
    with open(path) as fh:
        for rec in iter_json_objects(fh, marker='[', limit=limit):
            t0 = rec.get('start_time', rec.get('arrival'))
            t1 = rec.get('end_time', rec.get('depart'))
            if t0 is None:
                continue
            info = rec.get('info') or {}
            ri = info.get('response_info')
            if not isinstance(ri, dict):
                ri = {}
            srv = ri.get('server_usage') or {}
            out_tok = srv.get('completion_tokens')
            client_tok = ri.get('output_tokens')
            if out_tok is None:
                out_tok = client_tok
            tt = [t for t in (ri.get('output_token_times') or [])
                  if isinstance(t, (int, float))]
            itl = None
            if tt and out_tok and out_tok > 1:
                itl = (max(tt) - min(tt)) / (out_tok - 1) * 1000.0
            ttft = ri.get('time_to_first_token')
            if ttft is None and tt:
                ttft = min(tt) - t0
            err = rec.get('error')
            out.append({
                't_arr': t0,
                't_dep': t1,
                'in_tok': srv.get('prompt_tokens', info.get('input_tokens')),
                'out_tok': out_tok,
                'out_tok_client': client_tok,
                'ttft': ttft,
                'itl_true': itl,
                'outcome': 'error' if err else 'ok',
            })
    return out


def anchor_offset(requests, pods, guess=None, span=180, step=1.0):
    """Put a monotonic-clock demand trace on the scrape clock (plan section 2).

    Cross-correlate in-system count from the request trace against summed per-pod
    engine occupancy from the scrapes, scanning offsets around `guess`.

    The engine-side signal is `num_requests_running + num_requests_waiting`, not
    `running` alone. `running` is clipped at the engine's own concurrency limit
    (the per-pod KV ceiling), so once a pod saturates it flattens into a plateau
    while the request-derived count keeps climbing. Correlating a clipped signal
    lets the maximum sit anywhere along that plateau: on the 2026-08-07 staircase
    run `running` alone peaked at corr 0.945 a full 32 s late, where
    `running + waiting` scores 1.000 at the true alignment.

    Reported, not hidden: a poor correlation, or engine occupancy exceeding the
    request-derived in-system count, means the anchor is untrustworthy and every
    arrival-time-dependent panel should be read with that in mind.
    """
    if not requests or not pods:
        return {'offset': guess or 0.0, 'corr': None, 'method': 'none'}

    obs = {}
    for samples in pods.values():
        for s in samples:
            run, wait = s['g'].get('run'), s['g'].get('wait')
            if run is None and wait is None:
                continue
            k = round(s['t'])
            obs[k] = obs.get(k, 0.0) + (run or 0.0) + (wait or 0.0)
    if len(obs) < 5:
        return {'offset': guess or 0.0, 'corr': None, 'method': 'insufficient-scrapes'}

    ev = []
    for r in requests:
        ev.append((r['t_arr'], 1))
        if r['t_dep'] is not None:
            ev.append((r['t_dep'], -1))
    ev.sort()

    if guess is None:
        guess = min(obs) - min(r['t_arr'] for r in requests)
    ot = sorted(obs)
    req_span = max(r['t_arr'] for r in requests) - min(r['t_arr'] for r in requests)
    obs_span = max(ot) - min(ot)
    if obs_span > 0 and req_span < 0.2 * obs_span:
        # A head sample cannot anchor a full run: correlating a 9 s slice against a
        # 20 min scrape window finds a spurious maximum. Refuse and say so.
        return {'offset': guess, 'corr': None, 'method': 'refused-short-trace',
                'trustworthy': False, 'req_span_s': req_span,
                'scrape_span_s': obs_span}

    ov = [obs[t] for t in ot]
    mo = sum(ov) / len(ov)
    dev_o = [v - mo for v in ov]
    norm_o = math.sqrt(sum(d * d for d in dev_o)) or 1.0

    def in_system(off):
        """in-system count of the shifted demand trace, sampled at the scrape times"""
        pv, cur, j = [], 0, 0
        for t in ot:
            while j < len(ev) and ev[j][0] + off <= t:
                cur += ev[j][1]
                j += 1
            pv.append(cur)
        return pv

    best = None
    n_steps = int(span / step)
    for i in range(-n_steps, n_steps + 1):
        off = guess + i * step
        pv = in_system(off)
        mp = sum(pv) / len(pv)
        dev_p = [v - mp for v in pv]
        norm_p = math.sqrt(sum(d * d for d in dev_p))
        if norm_p <= 0:
            continue
        corr = sum(a * b for a, b in zip(dev_o, dev_p)) / (norm_o * norm_p)
        if best is None or corr > best['corr']:
            best = {'offset': off, 'corr': corr}
    if best is None:
        return {'offset': guess, 'corr': None, 'method': 'degenerate'}

    # Independent physical check at the chosen offset. Every request an engine
    # holds has arrived and has not yet departed, and the client's clock is the
    # outer one on both ends (it sends before the engine admits, and sees the last
    # token after the engine emits it), so engine occupancy can never exceed the
    # request-derived in-system count. Correlation is scale-free and blind to this,
    # which is how the `running`-only anchor shipped; a mis-anchored trace cannot
    # satisfy it.
    #
    # The tolerance covers measurement skew, not error: pods are scraped at
    # independent instants, so a sum over pods mixes instants up to a scrape period
    # apart, and during a ramp the true count moves several requests per second.
    # On the 2026-08-07 staircase this is a clean separation - at the true offset
    # the worst excess is 1.6% of occupancy and nothing trips the tolerance, while
    # every offset 2 s or more away puts 17-40% of samples over it (engines holding
    # requests that, on the shifted clock, had not arrived yet).
    pv = in_system(best['offset'])
    viol = worst = 0
    for o, p in zip(ov, pv):
        if o > p + max(OVER_L_FLOOR, OVER_L_REL * o):
            viol += 1
        if o > 0:
            worst = max(worst, (o - p) / o)
    best.update(method='cross-correlation', guess=guess,
                shift_from_guess_s=best['offset'] - guess,
                signal='run+wait', n_scrapes=len(ot),
                over_l_samples=viol, over_l_frac=viol / len(ot),
                over_l_worst_rel=worst,
                trustworthy=(best['corr'] >= 0.6
                             and viol <= OVER_L_MAX_FRAC * len(ot)))
    return best


def find_per_request(run_dir, harness):
    """All per-request files, in read order.

    inference-perf writes one file per load stage when the scenario is staged
    (`stage_0_lifecycle_metrics.json`, ...) and a single combined file otherwise.
    `summary_lifecycle_metrics.json` is aggregate stats, not per-request: skipped.
    """
    def is_array(p):
        """`stage_N_lifecycle_metrics.json` and `summary_...` are aggregate objects,
        not per-request arrays. Peek at the first token rather than trusting names."""
        try:
            with open(p) as fh:
                return (fh.read(4096).lstrip() or ' ')[0] == '['
        except OSError:
            return False

    if harness == 'guidellm':
        p = os.path.join(run_dir, 'results.json')
        return [p] if os.path.exists(p) else []

    for name in ('per_request_lifecycle_metrics.json', 'results.json'):
        p = os.path.join(run_dir, name)
        if os.path.exists(p) and is_array(p):
            return [p]
    stages = [p for p in sorted(
        glob.glob(os.path.join(run_dir, 'stage_*_lifecycle_metrics.json')),
        key=lambda q: int(re.search(r'stage_(\d+)_', q).group(1))) if is_array(p)]
    if stages:
        return stages
    head = os.path.join(run_dir, 'per_request_head.json')
    if os.path.exists(head) and is_array(head):
        warn('only per_request_head.json present - the demand trace is a SAMPLE, '
             'not the full run; every rate-based panel understates load. Re-fetch '
             'per_request_lifecycle_metrics.json for the real thing.')
        return [head]
    return []


# --------------------------------------------------------------------------- #
# Prometheus scrape parsing (section 8.2 - all three rules are load-bearing)
# --------------------------------------------------------------------------- #

def strict(line, name):
    """Exact family match.

    Without the next-character check, `vllm:num_requests_waiting` also matches
    `vllm:num_requests_waiting_by_reason` and the queue reads as zero. That bug
    produced a confident, wrong "vLLM never queues" claim in an earlier revision.
    """
    return (line.startswith(name)
            and len(line) > len(name)
            and line[len(name)] in '{ ')


def _val(line):
    try:
        return float(line.rsplit(None, 1)[1])
    except (IndexError, ValueError):
        return None


def parse_scrape(path):
    """One scrape file -> {'g':{}, 'c':{}, 'h':{key:(sum,count)}, 'cfg':{}, 'epp':v}"""
    g, c, h, cfg = {}, {}, {}, {}
    epp = None
    try:
        with open(path, errors='replace') as fh:
            lines = fh.readlines()
    except OSError:
        return None
    for raw in lines:
        line = raw.strip()
        if not line or line[0] == '#':
            continue
        for key, name in GAUGE.items():
            if strict(line, name):
                v = _val(line)
                if v is not None:
                    g[key] = g.get(key, 0.0) + v if key in ('run', 'wait') else v
        for key, name in CTR.items():
            if strict(line, name):
                v = _val(line)
                if v is not None:
                    c[key] = c.get(key, 0.0) + v
        for key, name in HIST.items():
            for suffix, slot in (('_sum', 0), ('_count', 1)):
                if strict(line, name + suffix):
                    v = _val(line)
                    if v is not None:
                        cur = list(h.get(key, (0.0, 0.0)))
                        cur[slot] += v
                        h[key] = tuple(cur)
        if strict(line, CACHE_CFG):
            for k, v in re.findall(r'(\w+)="([^"]*)"', line):
                cfg[k] = v
        if strict(line, EPP_RUNNING):
            v = _val(line)
            if v is not None:
                epp = (epp or 0.0) + v
    return {'g': g, 'c': c, 'h': h, 'cfg': cfg, 'epp': epp}


def scan_raw(run_dir):
    """metrics/raw/*_metrics.log -> per-pod time-ordered samples + engine config.

    Filenames are `<pod>_<epoch>_metrics.log`.
    """
    raw = os.path.join(run_dir, 'metrics', 'raw')
    files = sorted(glob.glob(os.path.join(raw, '*_metrics.log')))
    pods, epp_series, cfg = {}, [], {}
    for path in files:
        m = re.match(r'^(.+)_(\d{9,})_metrics\.log$', os.path.basename(path))
        if not m:
            continue
        pod, t = m.group(1), float(m.group(2))
        s = parse_scrape(path)
        if s is None:
            continue
        if s['cfg'] and not cfg:
            cfg = s['cfg']
        if EPP_RE.search(pod):
            if s['epp'] is not None:
                epp_series.append({'t': t, 'dispatch': s['epp']})
            continue
        if not s['g'] and not s['c']:
            continue                      # a not-yet-ready pod: empty scrape
        pods.setdefault(pod, []).append({'t': t, **s})
    for v in pods.values():
        v.sort(key=lambda r: r['t'])
    epp_series.sort(key=lambda r: r['t'])
    return pods, epp_series, cfg


def pod_intervals(samples):
    """Consecutive same-pod scrape pairs -> rate intervals.

    Counter deltas are only meaningful within one pod, and only when the counter
    did not go backwards (a restart) and dt is sane.
    """
    out = []
    for a, b in zip(samples, samples[1:]):
        dt = b['t'] - a['t']
        if dt <= 0 or dt > MAX_DT:
            continue
        rec = {'t0': a['t'], 't1': b['t'], 'dt': dt,
               'kv': b['g'].get('kv'), 'kv0': a['g'].get('kv'),
               'run': b['g'].get('run'), 'run0': a['g'].get('run'),
               'wait': b['g'].get('wait')}
        for key in CTR:
            x, y = a['c'].get(key), b['c'].get(key)
            rec[key + '_rate'] = ((y - x) / dt
                                  if x is not None and y is not None and y >= x
                                  else None)
        for key in HIST:
            x, y = a['h'].get(key), b['h'].get(key)
            # difference sum and count, then divide. Never the cumulative ratio:
            # that reports a run-long average and hides all dynamics.
            if x and y and y[1] > x[1] and y[0] >= x[0]:
                rec[key + '_ms'] = (y[0] - x[0]) / (y[1] - x[1]) * 1000.0
            else:
                rec[key + '_ms'] = None
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# supply
# --------------------------------------------------------------------------- #

def read_replicas(run_dir):
    d = read_json(os.path.join(run_dir, 'metrics', 'processed',
                               'replica_status_timeseries.json'), default={})
    snaps = (d or {}).get('snapshots') or []
    out = []
    for s in snaps:
        t = iso_epoch(s.get('timestamp'))
        if t is None:
            continue
        des = rdy = avail = 0
        for c in s.get('controllers') or []:
            des += c.get('desired_replicas') or 0
            rdy += c.get('ready_replicas') or 0
            avail += c.get('available_replicas') or 0
        out.append({'t': t, 'desired': des, 'ready': rdy, 'available': avail})
    out.sort(key=lambda r: r['t'])
    return out


def read_wva_processed(run_dir):
    """Reuse Ofer's post_run_analyze.sh output when it exists (plan section 1.1a).

    Absent on runs where the script was never run promptly -- the controller log
    it reads is rotated by kubectl, so those decisions are unrecoverable.
    """
    p = os.path.join(run_dir, 'metrics', 'processed')
    found = {}
    for name, key in (('wva_target_timeseries.json', 'wva_target'),
                      ('capacity_demand_estimate.json', 'capacity_demand'),
                      ('epp_throughput.json', 'epp_throughput'),
                      ('wva_metrics_timeseries.json', 'wva_metrics'),
                      ('hpa_desired_timeseries.json', 'hpa_desired')):
        d = read_json(os.path.join(p, name), default=False)
        if d is not False:
            found[key] = d
    return found


def lags(replicas, startup):
    """decision->ready boot lag per step, plus drain if a scale-down exists."""
    boot, decision, drain, scaledown = [], [], [], False
    pending = []
    for a, b in zip(replicas, replicas[1:]):
        if b['desired'] > a['desired']:
            pending.append((b['t'], b['desired']))
        if b['desired'] < a['desired']:
            scaledown = True
        if b['ready'] > a['ready']:
            while pending and pending[0][1] <= b['ready']:
                decision_t, _ = pending.pop(0)
                boot.append(b['t'] - decision_t)
        if b['ready'] < a['ready']:
            drain.append(b['t'])
    if not boot and startup:
        vals = [v for v in (startup or {}).values() if isinstance(v, (int, float))]
        boot = vals
    return {'boot_s': boot, 'boot_s_mean': mean(boot),
            'decision_s': decision, 'drain_events': drain,
            'scaledown_observed': scaledown}


# --------------------------------------------------------------------------- #
# derived
# --------------------------------------------------------------------------- #

def stable_intervals(pods, replicas):
    """Intervals safe to fit against.

    Excluded: big concurrency swings, intervals that straddle a replica-Ready
    transition (the served population changes underneath), and insane dt.
    """
    ready_ts = [b['t'] for a, b in zip(replicas, replicas[1:])
                if b['ready'] != a['ready']]
    out = []
    for pod, samples in pods.items():
        for iv in pod_intervals(samples):
            if iv['run'] is None or iv['run0'] is None:
                continue
            if abs(iv['run'] - iv['run0']) > STABLE_DRUN:
                continue
            if any(iv['t0'] < rt <= iv['t1'] for rt in ready_ts):
                continue
            iv['pod'] = pod
            out.append(iv)
    return out


def sat_band(ivs):
    band = [iv for iv in ivs if (iv['kv'] or 0) >= SAT]
    if not band:
        return {'threshold': SAT, 'n': 0}
    runs = [iv['run'] for iv in band if iv['run'] is not None]
    return {
        'threshold': SAT, 'n': len(band),
        'run_mean': mean(runs), 'run_max': max(runs) if runs else None,
        'itl_ms': mean([iv['itl_ms'] for iv in band if iv['itl_ms']]),
        'gen_tok_s': mean([iv['gen_rate'] for iv in band if iv['gen_rate']]),
        'req_s': mean([iv['ok_rate'] for iv in band if iv['ok_rate']]),
        'preempt_s': mean([iv['preempt_rate'] for iv in band
                           if iv['preempt_rate'] is not None]),
        'qwait_s': mean([iv['qw_ms'] for iv in band if iv['qw_ms']]),
        'kv_mean': mean([iv['kv'] for iv in band if iv['kv'] is not None]),
    }


def itl_fit(ivs, max_conc_pred):
    """Scan the lower knee y_lo; the window is [y_lo, 0.85] (plan section 5.2).

    y_lo = 0 for decode-heavy (the fitted intercept IS the true B); for heavier
    prefill the knee moves up and the intercept becomes an extrapolation, which
    `B_extrapolated` flags rather than hides.
    """
    best = None
    for y_lo in Y_LO_SCAN:
        pts = [(iv['run'], iv['itl_ms']) for iv in ivs
               if iv['itl_ms'] and iv['run'] is not None
               and iv['kv'] is not None and y_lo <= iv['kv'] <= FIT_HI]
        if len(pts) < MIN_FIT_N:
            continue
        a, b, r2, n = linfit([p[0] for p in pts], [p[1] for p in pts])
        if a is None:
            continue
        if best is None or r2 > best['r2']:
            best = {'y_lo': y_lo, 'y_hi': FIT_HI, 'A_ms_per_req': a,
                    'B_ms': b, 'r2': r2, 'n': n}
    if best is None:
        return {'y_hi': FIT_HI, 'n': 0, 'note': 'insufficient stable intervals'}
    low = [iv['itl_ms'] for iv in ivs
           if iv['itl_ms'] and (iv['kv'] or 0) < 0.05]
    best['B_measured_ms'] = mean(low)
    best['B_measured_n'] = len(low)
    best['B_extrapolated'] = best['y_lo'] > 0
    if best['B_ms'] and best['B_ms'] > 0 and max_conc_pred:
        best['rho'] = (best['A_ms_per_req'] * max_conc_pred + best['B_ms']) / best['B_ms']
    return best


def capacity(cfg, ivs, shape):
    """KV footprint ~ I*(1-pfx_hit) + O/2 tokens per running request.

    Validated to <1% twice on reference runs with zero free parameters. Read the
    config gauge; never assume gpu_memory_utilization.
    """
    out = {}
    try:
        nb = int(cfg.get('num_gpu_blocks'))
        bs = int(cfg.get('block_size'))
        out['num_gpu_blocks'], out['block_size'] = nb, bs
        out['kv_tokens'] = nb * bs
    except (TypeError, ValueError):
        out['kv_tokens'] = None
    out['gpu_mem_util'] = cfg.get('gpu_memory_utilization')
    out['prefix_caching'] = cfg.get('enable_prefix_caching')
    hits = sum(iv['pfxh_rate'] or 0 for iv in ivs)
    qs = sum(iv['pfxq_rate'] or 0 for iv in ivs)
    out['pfx_hit'] = (hits / qs) if qs > 0 else 0.0
    i_tok, o_tok = shape.get('in_tok'), shape.get('out_tok')
    if i_tok and o_tok:
        out['footprint_tok'] = i_tok * (1 - out['pfx_hit']) + o_tok / 2.0
        if out.get('kv_tokens') and out['footprint_tok'] > 0:
            out['max_conc_pred'] = out['kv_tokens'] / out['footprint_tok']
    runs = [iv['run'] for iv in ivs if iv['run'] is not None]
    out['max_conc_obs'] = max(runs) if runs else None
    kv_at_peak = [iv['kv'] for iv in ivs
                  if iv['run'] == out['max_conc_obs'] and iv['kv'] is not None]
    out['kv_at_peak_conc'] = mean(kv_at_peak)
    out['regime'] = ('memory-bound' if (out['kv_at_peak_conc'] or 0) >= SAT
                     else 'compute-bound-or-unsaturated')
    return out


def tput_knee(ivs):
    """Peak generation throughput vs concurrency; confident only if both sides exist."""
    pts = [(iv['run'], iv['gen_rate']) for iv in ivs
           if iv['gen_rate'] and iv['run'] is not None]
    if len(pts) < 6:
        return {'confident': False, 'n': len(pts)}
    peak = max(pts, key=lambda p: p[1])
    left = sum(1 for r, _ in pts if r < peak[0])
    right = sum(1 for r, _ in pts if r > peak[0])
    return {'run': peak[0], 'gen_tok_s': peak[1], 'n': len(pts),
            'n_left': left, 'n_right': right,
            'confident': left >= 3 and right >= 3}


def router_stats(pods, epp_series):
    """Dispersion of concurrency across pods, and sign flips of the leader."""
    by_t = {}
    for pod, samples in pods.items():
        for s in samples:
            if s['g'].get('run') is not None:
                by_t.setdefault(round(s['t']), {})[pod] = s['g']['run']
    disp, leader = [], []
    for t in sorted(by_t):
        vals = by_t[t]
        if len(vals) < 2:
            continue
        lo, hi = min(vals.values()), max(vals.values())
        tot = sum(vals.values())
        if tot > 0:
            disp.append((hi - lo) / tot)
        leader.append(max(vals, key=vals.get))
    flips = sum(1 for a, b in zip(leader, leader[1:]) if a != b)
    return {'disp_p50': pct(disp, 0.5), 'disp_p95': pct(disp, 0.95),
            'leader_flips': flips, 'n': len(disp),
            'oscillation_flag': bool(disp and (pct(disp, 0.95) or 0) > 0.5
                                     and flips >= 3)}


def queues(replicas, pods, epp_series, requests):
    """One global queue, sourced deliberately (plan section 4).

    (a) flow-control  - not exposed by current EPP builds; recovered by
        subtraction L(t)_demand - q_dispatch when a demand trace exists.
    (b) dispatch      - EPP `inference_objective_running_requests`: everything
        in the system, waiting AND being served. Equals panel 5, not a queue.
    (c) engine        - sum of per-pod vllm:num_requests_waiting.
    """
    eng = {}
    for pod, samples in pods.items():
        for s in samples:
            if s['g'].get('wait') is not None:
                k = round(s['t'])
                eng[k] = eng.get(k, 0.0) + s['g']['wait']
    disp = {round(r['t']): r['dispatch'] for r in epp_series}

    inflight = None
    if requests:
        ev = []
        for r in requests:
            ev.append((r['t_arr'], 1))
            if r['t_dep'] is not None:
                ev.append((r['t_dep'], -1))
        ev.sort()
        cur, inflight = 0, {}
        for t, d in ev:
            cur += d
            inflight[round(t)] = cur

    ts = sorted(set(list(eng) + list(disp) + (list(inflight) if inflight else [])))
    series = []
    for t in ts:
        row = {'t': t, 'q_engine': eng.get(t), 'q_dispatch': disp.get(t)}
        if inflight is not None:
            row['in_system'] = inflight.get(t)
            if row['q_dispatch'] is not None and row['in_system'] is not None:
                # Deliberate: this is the PoC's single global queue.
                row['q_flow'] = max(0.0, row['in_system'] - row['q_dispatch'])
        series.append(row)
    return series


# --------------------------------------------------------------------------- #
# coverage report (section 9)
# --------------------------------------------------------------------------- #

def coverage(ivs, fit, sat, knee, lag, cap, router, qseries, pods, requests, shape):
    def row(name, ok, detail):
        return {'capability': name,
                'verdict': 'PASS' if ok else 'FAIL',
                'detail': detail}

    kvs = [iv['kv'] for iv in ivs if iv['kv'] is not None]
    span = (max(kvs) - min(kvs)) if kvs else 0
    bands = len({int((iv['kv'] or 0) * 10) for iv in ivs
                 if iv['kv'] is not None and iv['kv'] <= FIT_HI})
    mid = [iv for iv in ivs if 0.80 <= (iv['kv'] or 0) <= 0.90]
    lowb = [iv for iv in ivs if (iv['kv'] or 0) < 0.05]
    qflow = [r['q_flow'] for r in qseries if r.get('q_flow') is not None]
    qeng = [r['q_engine'] for r in qseries if r.get('q_engine') is not None]

    rows = [
        row('Calibrate A', fit.get('n', 0) >= MIN_FIT_N and bands >= 3 and span >= 0.4,
            f"n={fit.get('n', 0)} bands={bands} kv_span={span:.2f}"),
        # B is trustworthy either directly (window starts at 0, so the intercept is
        # measured) or by agreement with the low-concurrency observations.
        row('Trust B',
            (len(lowb) >= 5 and not fit.get('B_extrapolated', True))
            or (fit.get('B_ms') and fit.get('B_measured_ms')
                and abs(fit['B_ms'] - fit['B_measured_ms'])
                <= 0.25 * fit['B_measured_ms']),
            f"y_lo={fit.get('y_lo')} B_fit={fit.get('B_ms')} "
            f"B_meas={fit.get('B_measured_ms')} n_low={len(lowb)}"),
        row('Characterize saturation', sat.get('n', 0) >= 10, f"n={sat.get('n', 0)}"),
        row('Exercise the 0.85 ceiling', len(mid) >= 3, f"n_0.80_0.90={len(mid)}"),
        row('Locate the throughput knee', bool(knee.get('confident')),
            f"n={knee.get('n')} left={knee.get('n_left')} right={knee.get('n_right')}"),
        row('Scale-down present', bool(lag.get('scaledown_observed')),
            f"drain_events={len(lag.get('drain_events') or [])}"),
        row('Drain-vs-kill measurable',
            bool(lag.get('scaledown_observed')) and bool(requests),
            'needs a scale-down and a per-request trace'),
        # PASS here means "observable at all", not "a meaningful share of the
        # backlog" - so the detail carries the engine queue alongside it for scale.
        # Queue (a) is recovered by subtraction and is extremely anchor-sensitive:
        # a mis-anchored demand trace inflates it (a 32 s error read p95=155 on a
        # run whose true p95 is 4).
        row('Queue (a) material', bool(qflow) and (pct(qflow, 0.95) or 0) > 1,
            f"p95={pct(qflow, 0.95)} max={max(qflow):.0f} "
            f"(vs engine queue max={max(qeng):.0f})" if qflow and qeng
            else (f"p95={pct(qflow, 0.95)}" if qflow else 'no demand trace')),
        row('Queue (c) material', bool(qeng) and max(qeng) > 1,
            f"max={max(qeng) if qeng else None}"),
        row('Router oscillation observable', len(pods) >= 2,
            f"pods={len(pods)} flips={router.get('leader_flips')} "
            f"disp_p95={router.get('disp_p95')} "
            f"oscillating={router.get('oscillation_flag')}"),
        row('rho model valid at top', (sat.get('preempt_s') or 0) < 0.05,
            f"preempt/s={sat.get('preempt_s')}"),
        row('Capacity model checkable',
            bool(cap.get('max_conc_pred')) and bool(cap.get('max_conc_obs')),
            f"pred={cap.get('max_conc_pred')} obs={cap.get('max_conc_obs')}"),
        row('Boot lag measured', bool(lag.get('boot_s')),
            f"n={len(lag.get('boot_s') or [])} mean={lag.get('boot_s_mean')}"),
        row('Signal completeness',
            bool(pods) and min(len(v) for v in pods.values()) >= 5 if pods else False,
            '; '.join(f'{k.split("-")[-1]}={len(v)}' for k, v in pods.items()) or 'none'),
        row('Per-request trace present', bool(requests), f"n={len(requests)}"),
    ]
    if shape.get('in_tok') and shape.get('out_tok'):
        # The knee model: decode-heavy shapes have y=0 (the fitted intercept IS the
        # true B); the more prefill dominates, the higher the knee. This row tests
        # the prediction against the fitted window rather than assuming it.
        ratio = shape['out_tok'] / shape['in_tok']
        heavy = ratio < 0.5
        y = fit.get('y_lo')
        agrees = y is not None and ((y > 0) == heavy)
        rows.append(row('Knee matches shape prediction', agrees,
                        f"in={shape['in_tok']} out={shape['out_tok']} out/in={ratio:.2f} "
                        f"({'prefill-heavy -> expect y>0' if heavy else 'decode-heavy -> expect y=0'})"
                        f"; fitted y_lo={y}"))
    n_pass = sum(1 for r in rows if r['verdict'] == 'PASS')
    return {'rows': rows, 'n_pass': n_pass, 'n_fail': len(rows) - n_pass,
             'saturation_threshold': SAT, 'warnings': WARN}


# --------------------------------------------------------------------------- #
# self-checks (section 8.4) - fail loudly, never silently
# --------------------------------------------------------------------------- #

def self_checks(requests, ivs, cap, meta, anchor=None):
    out = []

    def chk(name, ok, detail):
        out.append({'check': name, 'ok': bool(ok), 'detail': detail})

    if requests:
        span = max(r['t_arr'] for r in requests) - min(r['t_arr'] for r in requests)
        dur = meta.get('load_duration_s')
        chk('arrival span vs harness duration',
            dur is None or abs(span - dur) < 0.35 * max(span, dur or 1),
            f'span={span:.0f}s harness={dur}')
        bad = [r for r in requests
               if r['t_dep'] is not None and r['t_dep'] < r['t_arr']]
        chk('no request departs before it arrives', not bad, f'violations={len(bad)}')
    if ivs:
        chk('kv within [0,1]',
            all(0 <= (iv['kv'] or 0) <= 1.001 for iv in ivs), 'gauge sanity')
    if cap.get('max_conc_pred') and cap.get('max_conc_obs'):
        err = abs(cap['max_conc_pred'] - cap['max_conc_obs']) / cap['max_conc_pred']
        chk('capacity model vs observed peak concurrency', err < 0.25,
            f"pred={cap['max_conc_pred']:.1f} obs={cap['max_conc_obs']} err={err:.1%}")
    if anchor and anchor.get('over_l_frac') is not None:
        # A mis-anchored request trace shows up here as engines holding requests
        # that, on the shifted clock, have not arrived yet or have already left.
        # This is the check that would have caught the `running`-only correlation.
        n, corr = anchor.get('n_scrapes') or 0, anchor.get('corr')
        chk('engine occupancy never exceeds request-derived in-system count',
            anchor['over_l_frac'] <= OVER_L_MAX_FRAC,
            f"over-L samples={anchor.get('over_l_samples')}/{n} "
            f"({anchor['over_l_frac']:.1%}), worst excess "
            f"{anchor.get('over_l_worst_rel', 0):.1%} of occupancy; anchor shift "
            f"{anchor.get('shift_from_guess_s')}s on {anchor.get('signal')} "
            f"at corr={'None' if corr is None else format(corr, '.4f')}")
    return out


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def build(run_dir, want_per_request=True, head=None):
    md = read_flat_yaml(os.path.join(run_dir, 'run_metadata.yaml'))
    harness = (md.get('harness_name') or '').strip().lower()
    if not harness:
        harness = ('guidellm' if os.path.exists(os.path.join(run_dir, 'results.json'))
                   else 'inference-perf')
        warn(f'harness_name absent; inferred {harness} from directory contents')

    pods, epp_series, cfg = scan_raw(run_dir)
    replicas = read_replicas(run_dir)
    startup = read_json(os.path.join(run_dir, 'metrics', 'processed',
                                     'pod_startup_times.json'), default={})
    wva = read_wva_processed(run_dir)
    if not wva:
        warn('no post_run_analyze.sh output (wva_target_timeseries.json etc.) - '
             'WVA decision timeseries unavailable for this run; see plan 1.1a')

    requests = []
    anchor = {'offset': 0.0, 'corr': None, 'method': 'not-needed'}
    if want_per_request:
        paths = find_per_request(run_dir, harness)
        if not paths:
            warn('per-request file not found; panels 1 and 4 will be unavailable')
        else:
            reader = read_guidellm if harness == 'guidellm' else read_inference_perf
            for p in paths:
                try:
                    requests += reader(p, limit=head)
                except OSError as exc:
                    warn(f'per-request read failed for {os.path.basename(p)}: {exc}')
            requests.sort(key=lambda r: r['t_arr'])

    if requests and harness != 'guidellm':
        # guidellm timestamps are already epoch on the scrape clock; inference-perf
        # is monotonic and must be anchored (plan section 2).
        hs = iso_epoch(md.get('harness_start'))
        guess = (hs - requests[0]['t_arr']) if hs else None
        anchor = anchor_offset(requests, pods, guess=guess)
        off = anchor['offset']
        if off:
            for r in requests:
                r['t_arr'] += off
                if r['t_dep'] is not None:
                    r['t_dep'] += off
        if not anchor.get('trustworthy', True):
            # Name the criterion that actually failed: a high correlation with a
            # failing physical check is a different diagnosis from a low one.
            why = (f"corr={anchor.get('corr')}" if (anchor.get('corr') or 1.0) < 0.6
                   else f"engine occupancy exceeds request-derived in-system count "
                        f"on {anchor.get('over_l_frac', 0):.0%} of scrapes despite "
                        f"corr={anchor.get('corr')}")
            warn(f'time anchor is weak ({why}); arrival-time panels are '
                 'unreliable for this run')

    shape = {}
    oks = [r for r in requests if r['outcome'] == 'ok']
    if oks:
        shape = {'in_tok': pct([r['in_tok'] for r in oks if r['in_tok']], 0.5),
                 'out_tok': pct([r['out_tok'] for r in oks if r['out_tok']], 0.5)}

    ivs = stable_intervals(pods, replicas)
    all_ivs = [iv for s in pods.values() for iv in pod_intervals(s)]
    cap = capacity(cfg, all_ivs, shape)
    fit = itl_fit(ivs, cap.get('max_conc_pred'))
    sat = sat_band(ivs)
    knee = tput_knee(ivs)
    lag = lags(replicas, startup)
    router = router_stats(pods, epp_series)
    qseries = queues(replicas, pods, epp_series, requests)

    meta = {
        'run': os.path.basename(os.path.abspath(run_dir)),
        'harness': harness,
        'harness_version': (md.get('harness_version') or '').split('\n')[0][:80],
        'model': md.get('model'),
        'namespace': md.get('namespace'),
        'workload': md.get('harness_workload'),
        'harness_start': md.get('harness_start'),
        'harness_start_epoch': iso_epoch(md.get('harness_start')),
        'load_duration_s': iso_dur_seconds(md.get('harness_delta')),
        'shape': shape,
        'engine': cfg,
        'n_pods_seen': len(pods),
        'time_anchor': anchor,
        'extractor_version': EXTRACTOR_VERSION,
    }
    infl = [r['out_tok_client'] / r['out_tok'] for r in requests
            if r.get('out_tok_client') and r.get('out_tok')]
    if infl:
        # ~2x on inference-perf: streamed chunks double-counted client-side.
        meta['inflation_factor'] = mean(infl)

    system = []
    for r in qseries:
        system.append(r)

    bundle = {
        'meta': meta,
        'requests': requests,
        'replicas': replicas,
        'system': system,
        'pods': {pod: {'n_samples': len(s),
                       'series': [{'t': x['t'], **x['g']} for x in s]}
                 for pod, s in pods.items()},
        'derived': {
            'sat_band': sat, 'itl_fit': fit, 'capacity': cap,
            'tput_knee': knee, 'lags': lag, 'router': router,
            'stable_intervals': len(ivs), 'all_intervals': len(all_ivs),
            'wva_processed_present': sorted(wva),
        },
        'self_checks': self_checks(requests, all_ivs, cap, meta, anchor),
    }
    cov = coverage(ivs, fit, sat, knee, lag, cap, router, qseries,
                   pods, requests, shape)
    return bundle, cov


EXTRACTOR_VERSION = '0.1.0'


def print_coverage(cov, meta):
    print(f"\n{meta['run']}  [{meta['harness']}]  {meta.get('model') or '?'}")
    print(f"  {cov['n_pass']} PASS / {cov['n_fail']} FAIL"
          f"   (saturation threshold {cov['saturation_threshold']})")
    print('  ' + '-' * 74)
    for r in cov['rows']:
        mark = 'PASS' if r['verdict'] == 'PASS' else 'FAIL'
        print(f"  {mark:4}  {r['capability']:<32} {r['detail']}")
    if cov['warnings']:
        print('\n  warnings:')
        for w in cov['warnings']:
            print(f'    - {w}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True, help='run directory')
    ap.add_argument('--out', help='output directory (default: --run)')
    ap.add_argument('--no-per-request', action='store_true',
                    help='skip the large per-request file; panels 2-5 still work')
    ap.add_argument('--head', type=int,
                    help='read only the first N per-request records (sampling)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if not os.path.isdir(a.run):
        print(f'error: not a directory: {a.run}', file=sys.stderr)
        return 2
    out_dir = a.out or a.run
    os.makedirs(out_dir, exist_ok=True)

    bundle, cov = build(a.run, want_per_request=not a.no_per_request, head=a.head)

    bp = os.path.join(out_dir, 'bundle.json')
    cp = os.path.join(out_dir, 'coverage.json')
    with open(bp, 'w') as fh:
        json.dump(bundle, fh, separators=(',', ':'))
    with open(cp, 'w') as fh:
        json.dump(cov, fh, indent=2)

    if not a.quiet:
        print_coverage(cov, bundle['meta'])
        print(f"\n  wrote {bp} ({os.path.getsize(bp) / 1e6:.1f} MB)")
        print(f"  wrote {cp}")
        failed = [c for c in bundle['self_checks'] if not c['ok']]
        if failed:
            print('\n  SELF-CHECK FAILURES:')
            for c in failed:
                print(f"    - {c['check']}: {c['detail']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
