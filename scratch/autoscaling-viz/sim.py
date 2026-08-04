"""
Autoscaling behaviour simulator — phase 1.

One-dimensional load, one-dimensional backends, one global FIFO queue.
Deterministic playback of a *load trace* (requests) and a *supply trace*
(replica start/up/stop/down events) -> sampled time-series for plotting.

Service model: a per-request decode rate that depends on the pod's concurrency
(vLLM-style). Each in-service request advances at rate(k) tokens/s, where
k = in_service / usable_C in [0, 1] is the pod's load fraction; rate(0) =
rho * service_rate (empty pod, fastest) and rate(1) = service_rate (packed).
rho >= 1 is the empty/packed speedup ratio. rho = 1 recovers the earlier
fixed-rate model (rate == service_rate for every k), so it is the default and a
behaviour-preserving identity. The engine integrates this EXACTLY, per event: on
any change to a pod's in-service set it advances the batch by dt * rate(k_prev),
recomputes rate at the new k, and reschedules the pod's next completion (stale
completion events are filtered by a per-backend generation counter).

The SIZER is unchanged: it still plans on the fixed *saturated* rate
(service_rate), never crediting the low-load speedup — only the achieved latency
reflects it. See the design doc, section 2.7 (concurrency-dependent decode rate).

Nothing here is WVA code; it is a standalone teaching model.
"""

from __future__ import annotations

import bisect
import heapq
import json
import math
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Load generation
# --------------------------------------------------------------------------
def rate_profile(pattern: str, t: float, duration: float, peak: float) -> float:
    """Instantaneous target arrival rate (requests/sec) at time t."""
    if pattern == "uniform":
        return peak
    if pattern == "rising":
        return peak * t / duration
    if pattern == "bump":                       # triangular up then down
        m = duration / 2.0
        return peak * (t / m if t < m else max(0.0, (duration - t) / m))
    if pattern == "step":                       # low -> high plateau -> low
        lo, hi = 0.15 * peak, peak
        return hi if (0.3 * duration <= t <= 0.7 * duration) else lo
    if pattern == "spike":                       # steady baseline + a short tall burst
        # A burst much SHORTER than any sizing window: a windowed sizer (even a
        # perfectly clairvoyant centered one) averages the burst away and under-
        # provisions it. Baseline 0.4*peak; burst to 3*peak for 6s at mid-run.
        base = 0.4 * peak
        c = 0.5 * duration
        return 3.0 * peak if (c - 3.0 <= t <= c + 3.0) else base
    raise ValueError(f"unknown pattern {pattern!r}")


def gen_load(pattern="bump", duration=120.0, peak_rate=8.0,
             size_mean=4.0, size_dist="expo", seed=1) -> dict:
    """Non-homogeneous Poisson arrivals (via thinning) with random sizes."""
    rng = random.Random(seed)
    # Thinning bound must dominate the profile's TRUE maximum, not just peak_rate:
    # patterns like "spike" exceed peak_rate, and a too-low bound silently clips
    # the burst (acceptance prob >1 clamps to 1 -> arrivals capped at lam_max).
    n_scan = max(1000, int(duration * 4))
    prof_max = max(rate_profile(pattern, k * duration / n_scan, duration, peak_rate)
                   for k in range(n_scan + 1))
    lam_max = prof_max * 1.05 + 1e-9
    reqs, t, i = [], 0.0, 0
    while True:
        t += rng.expovariate(lam_max)
        if t >= duration:
            break
        if rng.random() <= rate_profile(pattern, t, duration, peak_rate) / lam_max:
            size = rng.expovariate(1.0 / size_mean) if size_dist == "expo" else size_mean
            reqs.append({"id": i, "arrival": round(t, 4), "size": round(size, 4)})
            i += 1
    return {
        "meta": {"pattern": pattern, "duration": duration, "peak_rate": peak_rate,
                 "size_mean": size_mean, "size_dist": size_dist, "seed": seed},
        "requests": reqs,
    }


# --------------------------------------------------------------------------
# Supply generation
# --------------------------------------------------------------------------
def offered_work_rate(load: dict, grid: list[float], range_s: float) -> list[float]:
    """Trailing offered-work-rate estimate on a time grid, tokens/sec.

    This is a demand *estimate*, not a pure measurement. The arrival *count* is
    observable, but a request's work (size in tokens) is not known at arrival —
    real serving knows the prefill/input length but not the decode/output length.
    Summing the actual in-window sizes is a valid proxy only under the
    stationary-shape assumption (arrival RATE varies over time, the request-size
    distribution does NOT), where it equals measured_arrival_rate x E[size]. The
    E[size] estimate may later be made time-varying; fixed is fine for now.
    See the design-doc Glossary.
    """
    arr = sorted((r["arrival"], r["size"]) for r in load["requests"])
    times = [a for a, _ in arr]
    cum = [0.0]
    for _, s in arr:
        cum.append(cum[-1] + s)

    def cum_work(t):
        return cum[bisect.bisect_right(times, t)]

    return [(cum_work(t) - cum_work(t - range_s)) / range_s for t in grid]


def gen_supply_perfect(load: dict, C=4, service_rate=2.0, setup=0.0, drain=0.0,
                       headroom=1.2, sizing_range=5.0, decision_interval=1.0,
                       sat_frac=1.0, max_replicas=None) -> dict:
    """Ideal baseline: desired count tracks offered work rate, near-zero setup.

    needed(t) = ceil(headroom * offered_work_rate(t) / per_backend); the
    resulting step function is turned into per-replica (start, stop) intervals
    LIFO. up = start + setup, down (target) = stop + drain.

    A backend saturates at a *usable* concurrency floor(sat_frac*C) rather than
    its raw slot count C — a lightweight stand-in for the way real serving
    (e.g. vLLM) stops gaining goodput, and eventually loses it, as concurrency
    climbs. So usable per-backend throughput is floor(sat_frac*C)*service_rate.

    Clairvoyant in two ways bundled together: (1) it estimates over a CENTERED
    sizing_range [t-r/2, t+r/2], so it sees future arrivals; (2) with setup=0 it
    also needs no lead time. The sizer still only ever targets the *averaged*
    offered-work-rate over the range, never the instantaneous peak.
    """
    duration = load["meta"]["duration"]
    grid = [i * decision_interval
            for i in range(int(duration / decision_interval) + 1)]
    half = sizing_range / 2.0                   # CENTERED range -> clairvoyant,
    owr = offered_work_rate(load, [t + half for t in grid], sizing_range)  # low-noise
    per_backend = int(sat_frac * C) * service_rate    # usable, not raw C
    needed = [max(0, math.ceil(headroom * w / per_backend)) for w in owr]
    if max_replicas is not None:                # optional cap (open-loop sizers
        needed = [min(n, max_replicas) for n in needed]   # are uncapped by default)

    replicas, active, nid = [], [], 0
    free_slots: list[int] = []                  # min-heap of idle slots to reuse
    next_slot = 0
    decisions, prev_n = [], 0                    # log each change in desired count
    for t, n, w in zip(grid, needed, owr):
        if n != prev_n:
            decisions.append({"t": t, "frm": prev_n, "to": n, "owr": w})
        while len(active) < n:                  # scale up: reuse lowest idle slot
            if free_slots:
                slot = heapq.heappop(free_slots)
            else:
                slot, next_slot = next_slot, next_slot + 1
            replicas.append({"id": nid, "slot": slot, "start": t, "up": t + setup,
                             "stop": None, "down": None})
            active.append(nid)
            nid += 1
        while len(active) > n:                  # scale down (LIFO), free the slot
            rid = active.pop()
            replicas[rid]["stop"] = t
            replicas[rid]["down"] = t + drain
            heapq.heappush(free_slots, replicas[rid]["slot"])
        prev_n = n
    end = grid[-1]
    for rid in active:                          # stop leftovers at trace end
        replicas[rid]["stop"] = end
        replicas[rid]["down"] = end + drain
    return {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                     "drain": drain, "headroom": headroom, "sat_frac": sat_frac,
                     "nslots": next_slot},
            "replicas": replicas, "decisions": decisions}


def gen_supply_queue_aware(load: dict, C=4, service_rate=2.0, setup=0.0, drain=0.0,
                           headroom=1.2, sizing_range=30.0, drain_time=30.0,
                           decision_interval=1.0, sat_frac=1.0,
                           boot_stagger=0.0, max_replicas=None) -> dict:
    """Reactive, QUEUE-AWARE sizing (no look-ahead / no anticipation).

    The controller sees only what it could actually measure at time t:
      * a *trailing* offered-work-rate estimate  owr(t) over [t-sizing_range, t]
      * the backlog of unserved work that has piled up so far

    Desired capacity covers the current inflow PLUS a term that drains the
    backlog over `drain_time` seconds:

        target_rate(t) = owr(t) + backlog(t) / drain_time
        needed(t)      = ceil(headroom * target_rate / (C*service_rate))

    A fluid forward pass estimates backlog under the capacity that is *actually
    up* at t (replicas ordered now boot `setup` later), so setup lag makes the
    backlog grow, which is exactly what drives the extra scale-up. This is a
    pure reactive controller: it does not discount capacity already booting, so
    during a long boot it keeps ordering -> it recovers the queue but overshoots.
    """
    duration = load["meta"]["duration"]
    grid = [i * decision_interval
            for i in range(int(duration / decision_interval) + 1)]
    owr = offered_work_rate(load, grid, sizing_range)  # TRAILING -> no peeking ahead
    per_backend = int(sat_frac * C) * service_rate     # usable, not raw C

    replicas, active, nid = [], [], 0
    free_slots: list[int] = []                      # min-heap of idle slots to reuse
    next_slot = 0
    backlog = 0.0                                   # fluid work-units estimate
    decisions, prev_n = [], 0                       # log each change in desired count

    def up_capacity(t):                             # work/s from replicas up now
        return sum(per_backend for r in replicas
                   if r["up"] <= t and (r["stop"] is None or t < r["stop"]))

    for t, w in zip(grid, owr):
        target = w + backlog / drain_time           # inflow + backlog-drain
        n = max(0, math.ceil(headroom * target / per_backend))
        if max_replicas is not None:
            n = min(n, max_replicas)                 # optional cap (uncapped default)
        if n != prev_n:
            decisions.append({"t": t, "frm": prev_n, "to": n,
                              "owr": w, "backlog": backlog})
        prev_n = n
        j = 0                                        # index within THIS tick's batch
        while len(active) < n:                      # scale up: reuse lowest idle slot
            if free_slots:
                slot = heapq.heappop(free_slots)
            else:
                slot, next_slot = next_slot, next_slot + 1
            replicas.append({"id": nid, "slot": slot, "start": t,
                             "up": t + setup + j * boot_stagger,  # cascaded boot
                             "stop": None, "down": None})
            active.append(nid)
            nid += 1
            j += 1
        while len(active) > n:                       # scale down (LIFO), free the slot
            rid = active.pop()
            replicas[rid]["stop"] = t
            replicas[rid]["down"] = t + drain
            heapq.heappush(free_slots, replicas[rid]["slot"])
        # advance fluid backlog under the capacity that is actually up right now
        backlog = max(0.0, backlog + (w - up_capacity(t)) * decision_interval)

    end = grid[-1]
    for rid in active:
        replicas[rid]["stop"] = end
        replicas[rid]["down"] = end + drain
    return {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                     "drain": drain, "headroom": headroom, "drain_time": drain_time,
                     "sat_frac": sat_frac, "nslots": next_slot},
            "replicas": replicas, "decisions": decisions}


def gen_supply_demand_predict(load: dict, C=4, service_rate=2.0, setup=0.0,
                              drain=0.0, headroom=1.2, sizing_range=30.0,
                              drain_time=30.0, decision_interval=1.0,
                              sat_frac=1.0, anticipation=1.0,
                              trend_window=None, max_replicas=None) -> dict:
    """DEFERRED / experimental — DEMAND-prediction sizer (NOT wired into the demo).

    This is a distinct axis from Qexp (gen_supply_queue_aware_exp, which predicts
    the QUEUE): here the sizer projects DEMAND itself forward by the boot lead
    time using a trailing linear trend (the simplest of many possible demand
    models — lots of prior art), so capacity ordered now, landing `setup` s later,
    is sized for the demand that will exist WHEN IT LANDS. Preserved because it is
    the promising next step ("pre-order by the full boot lead to hide the boot
    wall"), but the demand-prediction discussion is deferred: an *ideal* predictor
    approaches the clairvoyant ideal, and picking a real model deserves its own
    treatment. Kept out of run.py until then.

    No foresight of future arrivals (axis 1); it only extrapolates the trailing
    demand trend across the dead time (axis 2, dead-time compensation):

        slope   = (owr(t) - owr(t - trend_window)) / trend_window  # fill rate / dOWR/dt
        owr_hat = max(0, owr(t) + anticipation * slope * setup)    # demand at t+setup
        target  = owr_hat + backlog / drain_time
        needed  = ceil(headroom * target / per_backend)  -> clamp to max_replicas

    `anticipation` in [0,1] is the single anticipation knob (the swept dial):
      * 0.0  -> owr_hat == owr(t): degenerates to the reactive queue-aware sizer.
      * 1.0  -> full dead-time lead: order for demand one whole boot ahead.
    On the up-ramp (slope>0) it orders early, so capacity lands AS demand arrives
    (the mechanism that can actually move good%); on the down-slope (slope<0) it
    scales down early, trimming overshoot cost — but if demand turns back up it
    can under-serve, so more anticipation is not free.

    Note the "don't re-order booting capacity" concern (integral windup) is
    already handled by the absolute-count target: booting replicas live in the
    active set, so the while-loop only orders the shortfall (needed - up -
    booting). The fill-rate term is therefore spent on looking AHEAD, not on
    discounting in-flight capacity.

    The fluid backlog advances identically to the reactive sizer (under the
    capacity actually UP), so the two scenarios share the same physics and differ
    only in how the sizer decides — a clean A/B on anticipation.
    """
    duration = load["meta"]["duration"]
    grid = [i * decision_interval
            for i in range(int(duration / decision_interval) + 1)]
    owr = offered_work_rate(load, grid, sizing_range)  # TRAILING -> no peeking ahead
    per_backend = int(sat_frac * C) * service_rate     # usable, not raw C
    tw = trend_window if trend_window is not None else sizing_range
    lag = max(1, int(round(tw / decision_interval)))   # grid steps back for the slope

    replicas, active, nid = [], [], 0
    free_slots: list[int] = []                      # min-heap of idle slots to reuse
    next_slot = 0
    backlog = 0.0                                   # fluid work-units estimate
    decisions, prev_n = [], 0                       # log each change in desired count

    def up_capacity(t):                             # work/s from replicas up now
        return sum(per_backend for r in replicas
                   if r["up"] <= t and (r["stop"] is None or t < r["stop"]))

    for i, (t, w) in enumerate(zip(grid, owr)):
        w_prev = owr[max(0, i - lag)]                # trailing owr one window back
        slope = (w - w_prev) / (lag * decision_interval)  # fill rate (tokens/s per s)
        owr_hat = max(0.0, w + anticipation * slope * setup)  # demand projected fwd
        target = owr_hat + backlog / drain_time      # projected inflow + backlog-drain
        n = max(0, math.ceil(headroom * target / per_backend))
        if max_replicas is not None:
            n = min(n, max_replicas)                 # optional cap (uncapped default)
        if n != prev_n:
            decisions.append({"t": t, "frm": prev_n, "to": n,
                              "owr": w, "backlog": backlog})
        prev_n = n
        while len(active) < n:                       # scale up: reuse lowest idle slot
            if free_slots:
                slot = heapq.heappop(free_slots)
            else:
                slot, next_slot = next_slot, next_slot + 1
            replicas.append({"id": nid, "slot": slot, "start": t, "up": t + setup,
                             "stop": None, "down": None})
            active.append(nid)
            nid += 1
        while len(active) > n:                        # scale down (LIFO), free the slot
            rid = active.pop()
            replicas[rid]["stop"] = t
            replicas[rid]["down"] = t + drain
            heapq.heappush(free_slots, replicas[rid]["slot"])
        # advance fluid backlog under the capacity actually UP right now (same
        # physics as the reactive sizer -- only the DECISION above differs)
        backlog = max(0.0, backlog + (w - up_capacity(t)) * decision_interval)

    end = grid[-1]
    for rid in active:
        replicas[rid]["stop"] = end
        replicas[rid]["down"] = end + drain
    return {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                     "drain": drain, "headroom": headroom, "drain_time": drain_time,
                     "sat_frac": sat_frac, "anticipation": anticipation,
                     "trend_window": tw, "nslots": next_slot},
            "replicas": replicas, "decisions": decisions}


# --------------------------------------------------------------------------
# Shared actuation invariant (holds for EVERY sizer below and the closed-loop
# controllers): a sizer emits an absolute desired count D; actuation drives the
# total *commanded* fleet (current-up U + pending-booting P) toward D:
#     D >= U+P  -> order (D - U - P) new replicas
#     U < D < U+P -> cancel (U+P - D) PENDING only (never scale down current)
#     D <= U    -> cancel all pending, then retire (U - D) current, LIFO
# The inline `while len(active) </> n` loops implement exactly this: `active`
# holds every non-retired replica in mint order, and a pending replica's start
# is always more recent than any up replica's (start > t-setup vs <= t-setup),
# so LIFO pop removes pending before current. A sizer must therefore NEVER
# discount pending capacity itself (that is actuation's job) — it only decides D.
# --------------------------------------------------------------------------
def gen_supply_queue_aware_exp(load: dict, C=4, service_rate=2.0, setup=0.0,
                               drain=0.0, headroom=1.2, sizing_range=30.0,
                               drain_time=30.0, decision_interval=1.0,
                               sat_frac=1.0, proj_setup=None, boot_stagger=0.0,
                               max_replicas=None) -> dict:
    """Anticipatory QUEUE-aware sizing ("Qexp") as a PERIODIC control loop.

    Every tick it re-reads the observable state — current backlog level, capacity
    up now, and the pending replicas already committed (with their land-times) —
    and sizes to the PEAK of the backlog trajectory it projects forward under that
    committed schedule, clearing that peak over `drain_time`:

        cap(tau)      = up_capacity(t) + per_backend * (#pending landed by tau)
        B(tau)        = fluid roll-forward of backlog under cap(tau), clamped >= 0
        B_peak, t_pk  = max of B(tau) over [t, horizon_end] and when it occurs
        target        = owr(t) + B_peak / drain_time
        desired       = ceil(headroom * target / per_backend)  -> clamp max_replicas
        order         = desired - up - pending   (uniform actuation; never < 0 net)

    Why the PEAK, not the endpoint. The earlier version integrated the deficit to
    the END of the boot window; as committed pending drained the projected queue,
    B fell toward the RESIDUAL (often 0), which dropped the drain term and made the
    sizer CANCEL the very pending it was counting on (self-defeating oscillation).
    Sizing to the peak keeps the drain term equal to the worst backlog the loop
    must clear. The peak occurs at a physical land-time (where committed capacity
    crosses the inflow), so it does NOT drift tick-to-tick — no re-clocking of the
    deadline, without tracking individual requests.

    Observability. The loop reads only a LEVEL (backlog) plus the pending set +
    their ETAs — it never needs per-batch departures (which the real system does
    not expose). Scale-DOWN is driven purely by the OBSERVED backlog dropping.

    Self-correction. `proj_setup` (boot lead the projection ASSUMES; defaults to
    `setup`) and holding demand at the trailing owr are simplifying PREDICTIONS,
    not dependencies: if reality diverges (arrivals rise/fall, boots run slow/fast)
    the next tick re-observes the true backlog and re-sizes. Setting proj_setup !=
    setup deliberately mis-predicts the boot lead to exercise this.

    `boot_stagger` (u): replicas minted in one tick come up cascaded at
    t+setup+j*u (j = order within the batch), modelling limited boot concurrency.
    The projection reads each pending's stored land-time, so the cascade feeds the
    committed-capacity schedule automatically.

    No foresight of future arrivals and NO demand model (demand held at the
    trailing owr — demand prediction is the separate gen_supply_demand_predict).
    The fluid backlog itself advances identically to the reactive sizer (under the
    capacity actually UP), so the scenarios share physics and differ only in the
    sizing DECISION — a clean A/B on queue anticipation.
    """
    if proj_setup is None:
        proj_setup = setup
    duration = load["meta"]["duration"]
    grid = [i * decision_interval
            for i in range(int(duration / decision_interval) + 1)]
    owr = offered_work_rate(load, grid, sizing_range)  # TRAILING -> no peeking ahead
    per_backend = int(sat_frac * C) * service_rate     # usable, not raw C

    replicas, active, nid = [], [], 0
    free_slots: list[int] = []                      # min-heap of idle slots to reuse
    next_slot = 0
    backlog = 0.0                                   # fluid work-units estimate
    decisions, prev_n = [], 0                       # log each change in desired count

    def up_capacity(t):                             # work/s from replicas up now
        return sum(per_backend for r in replicas
                   if r["up"] <= t and (r["stop"] is None or t < r["stop"]))

    def peak_backlog(t, w, b0):
        """Roll the fluid backlog forward under the COMMITTED capacity schedule
        (up now + each pending at its ESTIMATED land-time) and return
        (B_peak, t_peak): the worst backlog on that trajectory and when it occurs.
        Sizing to this peak — not the endpoint/residual — is what keeps the drain
        term from collapsing as pending land. The peak sits at a projected
        land-time, so it does not drift across ticks (no deadline re-clocking).

        The land-time estimate is start + proj_setup — the projection's SIMPLE
        model, not reality's r["up"]. That is deliberate: proj_setup is an
        assumption (defaults to the true `setup`), and the sim may boot faster,
        slower, or cascaded (boot_stagger). When it diverges, reality lands less
        capacity than projected, the observed backlog next tick runs higher than
        expected, and the loop re-sizes — self-correction, not dependence. The
        pending SET is observable (pod not yet Ready, r["up"] > t); only its ETA
        is estimated. A pending the projection expected up by now (est < t) is
        treated as landing imminently (clamped to t)."""
        ups = sorted(max(t, r["start"] + proj_setup)  # ESTIMATED landings, not r[up]
                     for r in replicas
                     if t < r["up"] and (r["stop"] is None or t < r["stop"]))
        # look at least one boot-lead ahead, and far enough to see every committed
        # landing (so a heavily-staggered cascade is fully accounted for)
        horizon_end = t + proj_setup
        if ups:
            horizon_end = max(horizon_end, ups[-1])
        b, cap, prev = b0, up_capacity(t), t
        b_peak, t_peak = b, t
        for u in ups:
            if u > horizon_end:
                break
            if w > cap:                             # deficit -> backlog grows
                b = b + (w - cap) * (u - prev)
                if b > b_peak:
                    b_peak, t_peak = b, u
            else:                                   # surplus -> drains, clamp >= 0
                b = max(0.0, b + (w - cap) * (u - prev))
            cap += per_backend                      # this pending replica is now up
            prev = u
        if horizon_end > prev and w > cap:          # final growing segment
            b = b + (w - cap) * (horizon_end - prev)
            if b > b_peak:
                b_peak, t_peak = b, horizon_end
        return b_peak, t_peak

    for t, w in zip(grid, owr):
        b_peak, t_peak = peak_backlog(t, w, backlog)  # worst queue on committed path
        target = w + b_peak / drain_time            # inflow + clear the PEAK / drain
        n = max(0, math.ceil(headroom * target / per_backend))
        if max_replicas is not None:
            n = min(n, max_replicas)                 # optional cap (uncapped default)
        if n != prev_n:
            decisions.append({"t": t, "frm": prev_n, "to": n, "owr": w,
                              "backlog": backlog, "b_peak": b_peak, "t_peak": t_peak})
        prev_n = n
        j = 0                                        # index within THIS tick's batch
        while len(active) < n:                       # scale up: reuse lowest idle slot
            if free_slots:
                slot = heapq.heappop(free_slots)
            else:
                slot, next_slot = next_slot, next_slot + 1
            replicas.append({"id": nid, "slot": slot, "start": t,
                             "up": t + setup + j * boot_stagger,  # cascaded boot
                             "stop": None, "down": None})
            active.append(nid)
            nid += 1
            j += 1
        while len(active) > n:                        # scale down (LIFO -> pending 1st)
            rid = active.pop()
            replicas[rid]["stop"] = t
            replicas[rid]["down"] = t + drain
            heapq.heappush(free_slots, replicas[rid]["slot"])
        # advance fluid backlog under the capacity actually UP right now (same
        # physics as the reactive sizer -- only the DECISION above differs)
        backlog = max(0.0, backlog + (w - up_capacity(t)) * decision_interval)

    end = grid[-1]
    for rid in active:
        replicas[rid]["stop"] = end
        replicas[rid]["down"] = end + drain
    return {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                     "drain": drain, "headroom": headroom, "drain_time": drain_time,
                     "sat_frac": sat_frac, "proj_setup": proj_setup,
                     "boot_stagger": boot_stagger, "nslots": next_slot},
            "replicas": replicas, "decisions": decisions}


def gen_supply_static(load: dict, count: int, C=4, service_rate=2.0, setup=0.0,
                      drain=0.0, sat_frac=1.0) -> dict:
    """No-autoscaling baseline: a FIXED fleet of `count` replicas, up for the
    whole trace. There are no scale decisions — you provision once and leave it.

    Pre-warmed by default (setup=0, up at t=0): the boot is paid for before the
    run, so the fleet is usable from the first request. This is the classic
    static-provisioning reference — perfect promptness when `count` covers the
    peak, at the cost of the full fleet for the full duration (no scale-down in
    the valleys, so utilisation is whatever the load happens to fill).
    """
    duration = load["meta"]["duration"]
    replicas = [{"id": i, "slot": i, "start": 0.0, "up": setup,
                 "stop": duration, "down": duration + drain}
                for i in range(count)]
    return {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                     "drain": drain, "headroom": 1.0, "sat_frac": sat_frac,
                     "nslots": count},
            "replicas": replicas, "decisions": []}


# --------------------------------------------------------------------------
# HPA / KEDA-style closed-loop controllers
# --------------------------------------------------------------------------
def make_controller(kind: str, q_target=1.0, conc_target=58.0):
    """HPA/KEDA-style controllers using the AverageValue (per-replica) target
    type, so the current replica count cancels out of the formula:

        desired = ceil(total_metric / per_replica_target)

    replicating the llm-d "well-lit path for scaling with KEDA". The metrics are
    the ACTUAL measured signals (see Simulator: queued count Q and pool-wide
    running count R), trailing-averaged over the metric window — there is no
    foresight. A zero metric HOLDS the current count (and a cold start with n=0
    floors to 1): this mirrors KEDA declining to scale a target down to zero on
    an empty signal, and it is why a standalone baseline stays put once its
    signal drains to zero.

      queue        metric = queued requests Q, target = q_target (1 per replica)
                   -> desired = ceil(Q / q_target)
      concurrency  metric = running requests R, target = conc_target (< usable C)
                   -> desired = ceil(R / conc_target)
      combined     -> max(queue, concurrency) — the native KEDA multi-trigger
                   rule (take the largest per-trigger desired): scale UP if
                   EITHER trigger wants up, scale DOWN only when BOTH agree on a
                   lower count. "hold" is represented as the current count n, so
                   the max naturally yields up-on-either / down-on-both.

    Returns a closure decide(avg_q, avg_r, n) -> desired (pre-clamp; the
    Simulator applies min/max replica bounds).
    """
    def d_queue(avg_q, avg_r, n):
        if avg_q <= 0.0:                       # empty queue -> hold (cold: ->1)
            return n if n > 0 else 1
        return max(1, math.ceil(avg_q / q_target))

    def d_conc(avg_q, avg_r, n):
        if avg_r <= 0.0:                       # nothing running -> hold (cold: ->1)
            return n if n > 0 else 1
        return max(1, math.ceil(avg_r / conc_target))

    if kind == "queue":
        return d_queue
    if kind == "concurrency":
        return d_conc
    if kind == "combined":
        return lambda avg_q, avg_r, n: max(d_queue(avg_q, avg_r, n),
                                           d_conc(avg_q, avg_r, n))
    raise ValueError(f"unknown controller kind {kind!r}")


# --------------------------------------------------------------------------
# Simulator
# --------------------------------------------------------------------------
@dataclass
class Backend:
    id: int
    C: int
    service_rate: float         # nominal (packed) tokens/s per in-service request
    up: float
    stop: float
    down: float                 # target down time
    usable_C: int = 0           # accepting ceiling = floor(sat_frac*C); 0 => raw C
    rho: float = 1.0            # empty/packed decode-rate speedup (>=1; 1 = fixed)
    in_service: int = 0
    accepting: bool = False     # up..stop
    alive: bool = False         # up..actual_down
    pending_down: bool = False
    actual_down: float | None = None
    # concurrency-dependent decode-rate engine state (see module docstring / §2.7)
    inflight: list = field(default_factory=list)  # Reqs currently served on this pod
    rate: float = 0.0           # current per-request token rate = rate_at(k)
    last_update: float = 0.0    # time inflight `remaining` were last advanced
    comp_seq: int = 0           # generation counter; stale completions are ignored

    def rate_at(self, k: float) -> float:
        """Per-request decode rate at load fraction k = in_service/usable_C.
        Linear-ITL form ITL(k) = B + A*k with ITL(1)=1/sr (packed) and
        ITL(0)=1/(rho*sr) (empty), so rate(k)=1/(B+A*k). rho=1 => rate==sr."""
        inv = 1.0 / self.service_rate
        B = inv / self.rho
        A = inv * (1.0 - 1.0 / self.rho)
        return 1.0 / (B + A * k)


@dataclass
class Req:
    id: int
    arrival: float
    size: float
    start: float | None = None
    remaining: float = 0.0      # tokens left to decode (set to size at dispatch)


class Simulator:
    def __init__(self, load: dict, supply: dict, controller=None,
                 decision_interval=15.0, metric_window=60.0, rho=1.0):
        self.load = load
        self.supply = supply
        self.duration = load["meta"]["duration"]
        m = supply["meta"]
        sat = m.get("sat_frac", 1.0)
        self.rho = m.get("rho", rho)     # empty/packed decode speedup (>=1; 1=fixed)
        self.backends = {}
        for r in supply["replicas"]:
            cap = r.get("C", m["C"])
            self.backends[r["id"]] = Backend(
                id=r["id"], C=cap,
                service_rate=r.get("service_rate", m["service_rate"]),
                up=r["up"], stop=r["stop"], down=r["down"],
                usable_C=max(1, int(r.get("sat_frac", sat) * cap)),
                rho=self.rho)
        self.queue: deque[Req] = deque()
        # event heap: (time, seq, kind, payload)
        self._seq = 0
        self.events: list = []
        # logs
        self.arr_log: list[tuple[float, float]] = []   # (t, size)
        self.dep_log: list[tuple[float, float]] = []
        self.dep_by_backend: dict[int, list] = defaultdict(list)  # bid -> [(t,size)]
        self.snaps: list[dict] = []                      # per-event state snapshots
        self.req_done: list[dict] = []                   # per-request completion records

        # closed-loop control state (None controller => open-loop playback of a
        # pre-built supply trace, unchanged). In closed-loop mode supply starts
        # with an empty replica list; the controller mints/retires replicas as it
        # observes the live queue/running signal, and supply["replicas"] is grown
        # in place so sample()/plots see the same dict shape as the open-loop path.
        self.controller = controller
        self.decision_interval = decision_interval
        self.metric_window = metric_window
        if controller is not None:
            self.cl_C = m["C"]
            self.cl_sr = m["service_rate"]
            self.cl_setup = m.get("setup", 0.0)
            self.cl_drain = m.get("drain", 0.0)
            self.cl_sat = m.get("sat_frac", 1.0)
            self.cl_min = m.get("min_replicas", 1)       # KEDA minReplicaCount
            self.cl_max = m.get("max_replicas", 10)      # KEDA maxReplicaCount
            self._nid = 0
            self._next_slot = 0
            self._free_slots: list[int] = []             # min-heap of idle slots
            self._rec_by_id: dict[int, dict] = {}
            self._commanded: list[int] = []              # ordered & not yet stopped
            self._n_commanded = 0

    def _push(self, t, kind, payload=None):
        heapq.heappush(self.events, (t, self._seq, kind, payload))
        self._seq += 1

    def _snapshot(self, t):
        insvc = {b.id: b.in_service for b in self.backends.values()
                 if b.alive and b.in_service > 0}
        self.snaps.append({"t": t, "qlen": len(self.queue), "insvc": insvc})

    def _free_backend(self):
        """Accepting backend with the most free slots (spread load); None if full."""
        best, best_free = None, 0
        for b in self.backends.values():
            if b.accepting:
                free = b.usable_C - b.in_service
                if free > best_free:
                    best, best_free = b, free
        return best

    def _advance(self, b, now):
        """Advance every in-service request on `b` by the tokens decoded since the
        pod's last state change, at the rate that held over that interval. Call
        BEFORE mutating in_service so the elapsed span is charged at the old rate."""
        dt = now - b.last_update
        if dt > 0.0 and b.rate > 0.0:
            for r in b.inflight:
                r.remaining -= dt * b.rate
        b.last_update = now

    def _reschedule(self, b, now):
        """Recompute `b`'s decode rate at its current concurrency and push a fresh
        completion for its earliest-finishing request, bumping the generation so
        any previously-scheduled completion for `b` is ignored when it pops."""
        if b.in_service > 0:
            b.rate = b.rate_at(b.in_service / b.usable_C)
            rmin = min(r.remaining for r in b.inflight)
            b.comp_seq += 1
            self._push(now + max(0.0, rmin) / b.rate, "completion",
                       (b.id, b.comp_seq))
        else:
            b.rate = 0.0

    def _dispatch(self, now):
        while self.queue:
            b = self._free_backend()
            if b is None:
                break
            req = self.queue.popleft()
            req.start = now
            req.remaining = req.size
            self._advance(b, now)          # charge existing batch at the old rate
            b.inflight.append(req)
            b.in_service += 1
            self._reschedule(b, now)       # higher concurrency -> new (slower) rate

    # ----- closed-loop control helpers (only used when self.controller set) ---
    def _trailing_avg(self, key_fn, a, b):
        """Time-weighted average of a right-continuous step series (read off the
        event snapshots) over [a, b]. Used to turn the discrete queue/running
        snapshots into a Prometheus-style avg_over_time metric the controller
        reads. Returns 0.0 for an empty/degenerate window."""
        if b <= a:
            return 0.0
        snaps = self.snaps
        ts = [s["t"] for s in snaps]
        total, x = 0.0, a
        while x < b:
            i = bisect.bisect_right(ts, x) - 1
            v = key_fn(snaps[i]) if i >= 0 else 0.0
            j = bisect.bisect_right(ts, x)               # first snapshot after x
            nxt = ts[j] if j < len(ts) else b
            seg_end = min(nxt, b)
            total += v * (seg_end - x)
            x = seg_end
        return total / (b - a)

    def _mint(self, t):
        """Order one new replica at time t: booted (accepting) at t+setup. Reuse
        the lowest idle slot so the panel-3 band set stays small and stable."""
        slot = heapq.heappop(self._free_slots) if self._free_slots else self._next_slot
        if slot == self._next_slot:
            self._next_slot += 1
        rid, self._nid = self._nid, self._nid + 1
        rec = {"id": rid, "slot": slot, "start": t, "up": t + self.cl_setup,
               "stop": None, "down": None}
        self.supply["replicas"].append(rec)
        self._rec_by_id[rid] = rec
        self.backends[rid] = Backend(
            id=rid, C=self.cl_C, service_rate=self.cl_sr,
            up=rec["up"], stop=None, down=None,
            usable_C=max(1, int(self.cl_sat * self.cl_C)), rho=self.rho)
        self._push(rec["up"], "up", rid)
        self._commanded.append(rid)
        self._n_commanded += 1

    def _retire(self, t):
        """Scale down LIFO: stop the most-recently ordered replica now (drain),
        down it at t+drain. The stop/down events drive the accepting/alive flags,
        so a replica cancelled mid-boot simply never becomes accepting."""
        rid = self._commanded.pop()
        rec = self._rec_by_id[rid]
        rec["stop"] = t
        rec["down"] = t + self.cl_drain
        b = self.backends[rid]
        b.stop, b.down = rec["stop"], rec["down"]
        self._push(rec["stop"], "stop", rid)
        self._push(rec["down"], "down", rid)
        heapq.heappush(self._free_slots, rec["slot"])
        self._n_commanded -= 1

    def _reconcile(self, t, desired):
        while self._n_commanded < desired:
            self._mint(t)
        while self._n_commanded > desired:
            self._retire(t)

    def run(self):
        for r in self.load["requests"]:
            self._push(r["arrival"], "arrival",
                       Req(id=r["id"], arrival=r["arrival"], size=r["size"]))
        for b in self.backends.values():
            self._push(b.up, "up", b.id)
            if b.stop is not None:
                self._push(b.stop, "stop", b.id)
            if b.down is not None:
                self._push(b.down, "down", b.id)
        if self.controller is not None:            # closed-loop: periodic decisions
            k = 0
            while k * self.decision_interval <= self.duration:
                self._push(k * self.decision_interval, "decide", None)
                k += 1

        while self.events:
            t, _, kind, payload = heapq.heappop(self.events)

            if kind == "arrival":
                self.arr_log.append((t, payload.size))
                self.queue.append(payload)
                self._dispatch(t)

            elif kind == "up":
                b = self.backends[payload]
                if b.actual_down is None:          # ignore if already downed
                    b.alive = True                 # (commanded+cancelled mid-boot)
                    b.accepting = (b.stop is None or t < b.stop)
                    self._dispatch(t)

            elif kind == "stop":
                self.backends[payload].accepting = False   # drain: no new work

            elif kind == "down":
                b = self.backends[payload]
                if b.in_service > 0:
                    b.pending_down = True                  # defer until drained
                else:
                    b.alive = False
                    b.actual_down = t

            elif kind == "completion":
                bid, seq = payload
                b = self.backends[bid]
                if seq != b.comp_seq or not b.inflight:
                    continue                     # stale: superseded by a reschedule
                self._advance(b, t)              # bring the batch's remaining to now
                req = min(b.inflight, key=lambda r: r.remaining)  # earliest-finishing
                b.inflight.remove(req)
                b.in_service -= 1
                self.dep_log.append((t, req.size))
                self.dep_by_backend[bid].append((t, req.size))
                self.req_done.append({
                    "done": t, "arrival": req.arrival, "size": req.size,
                    "latency": t - req.arrival,          # total time in system
                    "wait": (req.start - req.arrival) if req.start is not None else 0.0,
                    "service": (t - req.start) if req.start is not None else 0.0})
                if b.pending_down and b.in_service == 0:
                    b.alive = False
                    b.actual_down = t
                    b.pending_down = False
                self._reschedule(b, t)           # fewer reqs -> faster; next completion
                self._dispatch(t)

            elif kind == "decide":
                # read the ACTUAL signal, trailing-averaged over [t-window, t]
                # (no foresight), then reconcile toward the HPA/KEDA desired
                # count, clamped to [minReplicaCount, maxReplicaCount].
                a = max(0.0, t - self.metric_window)
                avg_q = self._trailing_avg(lambda s: s["qlen"], a, t)
                avg_r = self._trailing_avg(
                    lambda s: sum(s["insvc"].values()), a, t)
                prev = self._n_commanded
                desired = self.controller(avg_q, avg_r, prev)
                desired = max(self.cl_min, min(self.cl_max, desired))
                if desired != prev:                 # log each change in desired
                    self.supply.setdefault("decisions", []).append(
                        {"t": t, "frm": prev, "to": desired,
                         "avg_q": avg_q, "avg_r": avg_r})
                self._reconcile(t, desired)
                self._dispatch(t)

            self._snapshot(t)

        # any backend never explicitly downed -> alive to end
        for b in self.backends.values():
            if b.actual_down is None:
                b.actual_down = b.down if b.down is not None else self.duration
        return self


def run_closed_loop(load: dict, kind: str, C=4, service_rate=2.0, setup=0.0,
                    drain=0.0, sat_frac=1.0, decision_interval=15.0,
                    metric_window=60.0, q_target=1.0, conc_target=None,
                    headroom=1.2, min_replicas=1, max_replicas=10,
                    rho=1.0) -> Simulator:
    """Build + run an HPA/KEDA-style closed-loop scenario end to end.

    Unlike gen_supply_* (open-loop pre-passes over the load trace), the
    controller here reads the ACTUAL simulated queue/running signal every
    decision_interval, trailing-averaged over metric_window, and reconciles the
    live fleet toward its desired count (LIFO scale-down; boot lag = setup). The
    per-replica concurrency target defaults to the usable ceiling discounted by
    headroom (⌊sat·C⌋/headroom), matching the ~83% utilisation the work-rate
    sizers aim for. Returns the finished Simulator — feed it to sample() as usual.
    """
    usable_C = max(1, int(sat_frac * C))
    if conc_target is None:
        conc_target = max(1.0, usable_C / headroom)
    controller = make_controller(kind, q_target=q_target, conc_target=conc_target)
    supply = {"meta": {"C": C, "service_rate": service_rate, "setup": setup,
                       "drain": drain, "headroom": headroom, "sat_frac": sat_frac,
                       "nslots": 0, "kind": kind, "q_target": q_target,
                       "conc_target": conc_target, "metric_window": metric_window,
                       "min_replicas": min_replicas, "max_replicas": max_replicas,
                       "rho": rho},
              "replicas": []}
    sim = Simulator(load, supply, controller=controller,
                    decision_interval=decision_interval,
                    metric_window=metric_window, rho=rho).run()
    supply["meta"]["nslots"] = sim._next_slot
    return sim


# --------------------------------------------------------------------------
# Sampling to a uniform grid for plotting
# --------------------------------------------------------------------------
def _step_lookup(snaps, key, grid, default):
    """Value of snaps[..][key] as a right-continuous step function on grid."""
    ts = [s["t"] for s in snaps]
    out = []
    for t in grid:
        i = bisect.bisect_right(ts, t) - 1
        out.append(snaps[i][key] if i >= 0 else default)
    return out


def _windowed_rate(log, grid, window):
    """Trailing windowed rate: (count, work) per second over [t-window, t]."""
    times = [x[0] for x in log]
    cum_n = list(range(len(log) + 1))
    cum_w = [0.0]
    for _, w in log:
        cum_w.append(cum_w[-1] + w)

    def at(cum, t):
        return cum[bisect.bisect_right(times, t)]

    rate_n = [(at(cum_n, t) - at(cum_n, t - window)) / window for t in grid]
    rate_w = [(at(cum_w, t) - at(cum_w, t - window)) / window for t in grid]
    return rate_n, rate_w


def sample(sim: Simulator, sample_interval=0.25, req_range=15.0, work_range=60.0,
           wait_edges=None) -> dict:
    dur = sim.duration
    grid = [round(i * sample_interval, 6)
            for i in range(int(dur / sample_interval) + 1)]

    # request counts on the short range; work rates on the long (Prom-like) range
    arr_n, _ = _windowed_rate(sim.arr_log, grid, req_range)
    dep_n, _ = _windowed_rate(sim.dep_log, grid, req_range)
    _, arr_w = _windowed_rate(sim.arr_log, grid, work_range)
    _, dep_w = _windowed_rate(sim.dep_log, grid, work_range)

    # desired: start<=t<stop ; actual: up<=t<actual_down ; draining: stop<=t<down
    def count(pred):
        return [sum(1 for b in sim.backends.values() if pred(b, t)) for t in grid]

    reps = sim.supply["replicas"]
    desired = [sum(1 for r in reps
                   if r["start"] <= t and (r["stop"] is None or t < r["stop"]))
               for t in grid]
    actual = count(lambda b, t: b.up <= t < (b.actual_down or dur))
    draining = count(lambda b, t: (b.stop is not None and b.stop <= t
                                   < (b.actual_down or dur)))
    # provisioned = everything you are billed for: from the moment a replica is
    # ORDERED (start) — including the boot window before it accepts (start..up) —
    # through to full termination (actual_down). = booting + accepting + draining.
    # The gap provisioned − actual is the boot-lag waste that scaling churn adds:
    # capacity paid for but not yet (or no longer) usable.
    provisioned = [sum(1 for r in reps
                       if r["start"] <= t < (sim.backends[r["id"]].actual_down or dur))
                   for t in grid]

    qlen = _step_lookup(sim.snaps, "qlen", grid, 0)

    # in-system concurrency from the event snapshots
    ids = sorted(sim.backends.keys())
    in_service_total, nsys = [], []
    ts = [s["t"] for s in sim.snaps]
    for k, t in enumerate(grid):
        j = bisect.bisect_right(ts, t) - 1
        cur = sim.snaps[j]["insvc"] if j >= 0 else {}
        tot = sum(cur.values())
        in_service_total.append(tot)
        nsys.append(tot + qlen[k])                       # in system = serving + queued

    # A "slot" is a persistent backend position: when the pool scales down then up,
    # a freed slot is reused instead of minting a new identity, so the stack shows a
    # small stable set of bands (<= peak concurrency), not one band per lifecycle.
    slot_of = {r["id"]: r.get("slot", r["id"]) for r in reps}
    nslots = sim.supply["meta"].get("nslots", len(ids))
    slot_ids = list(range(nslots))

    C, service_rate = sim.supply["meta"]["C"], sim.supply["meta"]["service_rate"]
    sat = sim.supply["meta"].get("sat_frac", 1.0)
    usable_C = max(1, int(sat * C))                       # vLLM goodput ceiling
    # Usable capacity counts only ACCEPTING backends. A draining replica is alive
    # and still finishing its in-flight work, but cannot take new work, so it is
    # NOT capacity for the scale decision (the queue-aware sizer already excludes
    # it). Its residual delivered work therefore pokes ABOVE this ceiling in
    # panels 3/5 — which is exactly the point: draining work is not headroom.
    accepting = [a - d for a, d in zip(actual, draining)]
    capacity_work = [c * usable_C * service_rate for c in accepting]  # throughput ceiling (work/s)
    capacity_slots = [c * usable_C for c in accepting]   # usable concurrency ceiling (slots)

    # per-SLOT work being delivered RIGHT NOW = (in-service on that slot) * rate.
    # Instantaneous, NOT a windowed completion rate: work is counted while it is
    # being done (from the first dispatch), not lumped at departure. Summed over
    # slots this equals in_service_total * rate; the demand line (below) is L(t)*rate,
    # so the vertical gap between the stack and demand is the queued (starved) work,
    # and demand poking above capacity_work marks under-provisioning.
    # Split the per-slot work into ACCEPTING work (rides under the ceiling) and
    # DRAINING work (a stopped-but-not-yet-down backend still finishing in-flight
    # requests). Draining work is not usable capacity, so we (a) draw it hatched,
    # bursting ABOVE the ceiling, and (b) remove it from the demand line — the
    # ceiling already excludes draining backends, so demand should only reflect
    # work competing for accepting capacity (accepting-in-service + queued).
    band = {s: [0.0] * len(grid) for s in slot_ids}
    band_drain = {s: [0.0] * len(grid) for s in slot_ids}
    drain_work = [0.0] * len(grid)                        # Σ draining in-service·rate
    snap_ts = [s["t"] for s in sim.snaps]
    for k, t in enumerate(grid):
        j = bisect.bisect_right(snap_ts, t) - 1
        cur = sim.snaps[j]["insvc"] if j >= 0 else {}
        for bid, c in cur.items():
            b = sim.backends[bid]
            is_drain = (b.stop is not None and b.stop <= t < (b.actual_down or dur))
            w = c * service_rate
            if is_drain:
                band_drain[slot_of.get(bid, bid)][k] += w
                drain_work[k] += w
            else:
                band[slot_of.get(bid, bid)][k] += w
    demand_work = [n * service_rate - dw                  # exclude draining in-flight
                   for n, dw in zip(nsys, drain_work)]

    # per-pod drain-start instants: the moment a backend stops accepting and
    # begins draining its in-flight work. Only pods that actually had work to
    # drain (actual_down strictly after stop) get a marker; end-of-trace stops
    # are excluded. Panel 3 draws a dotted line in the pod's colour here, so the
    # band lifting above the ceiling is tied to a visible cause.
    drain_starts = sorted(
        ({"slot": slot_of.get(b.id, b.id), "t": b.stop}
         for b in sim.backends.values()
         if b.stop is not None and b.stop < dur
         and (b.actual_down or dur) > b.stop + 1e-9),
        key=lambda d: d["t"])

    # cumulative arrivals / departures (Little's Law geometry: vertical gap = L)
    def _cum(log):
        times = [x[0] for x in log]
        return [bisect.bisect_right(times, t) for t in grid]
    cum_arr = _cum(sim.arr_log)
    cum_dep = _cum(sim.dep_log)

    # goodput quality bands by ABSOLUTE waiting time (queue delay before service
    # starts). 0 = best. We deliberately do NOT normalise by request size: a short
    # request that waited 30s is no more "failed" than a long one that waited 30s
    # (the earlier slowdown-ratio model guillotined short requests unfairly).
    # Thresholds are wall-clock seconds; tune via wait_edges. Default pins
    # good/failed and ramps the middle: instant service (≤2s) is "good", "almost"
    # extends to ~one clean service time (≤15s) as a reasonable wait, anything past
    # a minute is "failed", and the 15–60s middle is sliced into a quality gradient
    # (mediocre ≤30 / meh ≤45 / bad ≤60).
    edges = wait_edges if wait_edges is not None else [2.0, 15.0, 30.0, 45.0, 60.0]
    band_logs = [[] for _ in range(len(edges) + 1)]
    for r in sim.req_done:
        w = r["wait"]
        band_logs[sum(1 for e in edges if w >= e)].append((r["done"], 1.0))
    gp_bands = [_windowed_rate(sorted(bl), grid, req_range)[0] for bl in band_logs]
    _names = ["good", "almost", "mediocre", "meh", "bad", "failed"]
    gp_labels = [f"{_names[i]} (≤{edges[i]:g}s)" for i in range(len(edges))]
    gp_labels.append(f"{_names[len(edges)]} (>{edges[-1]:g}s)")

    lat = sorted(sim.req_done, key=lambda r: r["done"])

    # -- decision log: annotate each change in DESIRED count with the "why".
    # Open-loop sizers logged the offered-work-rate (+backlog); closed-loop
    # sizers logged the trailing signal averages. Format a compact reason keyed
    # off the supply kind so the figure can print a numbered decision key, and
    # tag decisions the [min,max] clamp actually bit.
    meta = sim.supply["meta"]
    kind = meta.get("kind")                              # closed-loop only
    q_t = meta.get("q_target", 1.0) or 1.0
    c_t = meta.get("conc_target", 1.0) or 1.0
    cl_min, cl_max = meta.get("min_replicas", 1), meta.get("max_replicas", 10)

    def _clamp_tag(to, raw):
        if raw > cl_max and to == cl_max:
            return " (cap)"
        if raw < cl_min and to == cl_min:
            return " (min)"
        return ""

    decisions = []
    for d in sim.supply.get("decisions", []):
        to = d["to"]
        if "owr" in d:                                   # open-loop sizer
            if d.get("backlog", 0) > 1:
                why = f"DR {d['owr']:.0f}+bklog {d['backlog']:.0f} ⇒ {to}"
            else:
                why = f"DR {d['owr']:.0f} w/s ⇒ {to}"
        elif kind == "queue":
            raw = max(1, math.ceil(d["avg_q"] / q_t))
            why = f"Q̄ {d['avg_q']:.0f} ⇒ ⌈{d['avg_q']:.0f}/{q_t:.0f}⌉={raw}{_clamp_tag(to, raw)}"
        elif kind == "concurrency":
            raw = max(1, math.ceil(d["avg_r"] / c_t))
            why = f"R̄ {d['avg_r']:.0f} ⇒ ⌈R/{c_t:.0f}⌉={raw}{_clamp_tag(to, raw)}"
        elif kind == "combined":
            qd = max(1, math.ceil(d["avg_q"] / q_t))
            cd = max(1, math.ceil(d["avg_r"] / c_t))
            raw = max(qd, cd)
            why = (f"Q̄{d['avg_q']:.0f}⇒{qd} · R̄{d['avg_r']:.0f}⇒{cd} "
                   f"(max {raw}){_clamp_tag(to, raw)}")
        else:
            why = f"⇒ {to}"
        decisions.append({"t": d["t"], "frm": d["frm"], "to": to,
                          "up": to > d["frm"], "why": why})

    return {
        "grid": grid, "req_range": req_range, "work_range": work_range,
        "arr_n": arr_n, "dep_n": dep_n, "arr_w": arr_w, "dep_w": dep_w,
        "desired": desired, "actual": actual, "draining": draining,
        "provisioned": provisioned,
        "accepting": accepting, "decisions": decisions,
        "qlen": qlen, "capacity_work": capacity_work, "capacity_slots": capacity_slots,
        "in_service_total": in_service_total, "nsys": nsys,
        "backend_ids": slot_ids, "backend_work": band,
        "backend_work_drain": band_drain, "drain_starts": drain_starts,
        "demand_work": demand_work,
        "cum_arr": cum_arr, "cum_dep": cum_dep,
        "gp_bands": gp_bands, "gp_labels": gp_labels, "gp_edges": list(edges),
        "lat_done": [r["done"] for r in lat],
        "lat_value": [r["latency"] for r in lat],
        "lat_size": [r["size"] for r in lat],
        "req_wait": [r["wait"] for r in lat],                       # queue delay
        "req_tpw": [(r["latency"] / r["size"]) if r["size"] > 0     # time / work unit
                    else float("inf") for r in lat],
        "meta": {"load": sim.load["meta"], "supply": sim.supply["meta"]},
    }


# --------------------------------------------------------------------------
# Summary report (standard TTFT/TPOT-style comparison table)
# --------------------------------------------------------------------------
def _percentile(sorted_vals: list[float], p: float) -> float:
    """Linear-interpolated percentile (matches numpy's default)."""
    n = len(sorted_vals)
    if n == 0:
        return float("nan")
    if n == 1:
        return sorted_vals[0]
    rank = (p / 100.0) * (n - 1)
    lo, hi = math.floor(rank), math.ceil(rank)
    if lo == hi:
        return sorted_vals[int(rank)]
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def summarize(ts: dict, ps=(50, 75, 90, 95, 99)) -> dict:
    """Per-run comparison metrics people expect side-by-side across policies:
    waiting time (TTFT-like) and time-per-work-unit (TPOT-like) distributions,
    plus replica-count cost stats.
    """
    def dist(vals):
        s = sorted(v for v in vals if v != float("inf"))
        d = {"avg": (sum(s) / len(s)) if s else float("nan")}
        for p in ps:
            d[f"p{p}"] = _percentile(s, p)
        return d

    actual = ts["actual"]
    n = len(actual)
    ra = sum(actual) / n if n else 0.0
    var = sum((x - ra) ** 2 for x in actual) / n if n else 0.0
    grid = ts["grid"]
    dt = (grid[1] - grid[0]) if len(grid) > 1 else 1.0
    offered = ts["cum_arr"][-1] if ts["cum_arr"] else 0        # total requests seen
    completed = len(ts["req_wait"])

    # per-quality-band breakdown, matching panel-1a colours (bands split by
    # absolute waiting time). Denominator is OFFERED, so the band %s plus
    # the unfinished % sum to 100 — a stranded request is not silently dropped
    # from the failure accounting the way it is from panel 1a (completed-only).
    edges = ts.get("gp_edges", [2.0, 15.0, 30.0, 45.0, 60.0])
    _names = ["good", "almost", "mediocre", "meh", "bad", "failed"]
    band_labels = [f"{_names[i]} (≤{edges[i]:g}s)" for i in range(len(edges))]
    band_labels.append(f"{_names[len(edges)]} (>{edges[-1]:g}s)")
    band_counts = [0] * (len(edges) + 1)
    for w in ts["req_wait"]:
        band_counts[sum(1 for e in edges if w >= e)] += 1
    band_pct = [(100.0 * c / offered) if offered else float("nan")
                for c in band_counts]

    # cumulative "served within" view: the empirical wait CDF sampled at each
    # band edge = share of OFFERED served within Ns. within_pct[i] = P(wait ≤
    # edges[i]) over the offered denominator (unfinished requests are not in
    # req_wait, so they correctly count as "not within"). This is the SLO-
    # attainment reading and pairs 1:1 with the wait-CDF figure. Computed from
    # raw waits, not by summing rounded band %s, so it stays exact.
    within_labels = [f"≤{e:g}s" for e in edges]
    within_pct = [(100.0 * sum(1 for w in ts["req_wait"] if w <= e) / offered)
                  if offered else float("nan") for e in edges]

    # utilization = work actually delivered ÷ usable throughput-capacity paid
    # for. Denominator uses ACTUAL replica-seconds (fleet you paid for) times the
    # usable per-backend throughput ceiling. All policies deliver the same total
    # work, so this cleanly separates OVER-provisioned (low util: hpa-queue) from
    # STARVED (util near/above 1 yet high wait: hpa-concurrency) — a small fleet
    # kept busy still fails on latency, which the % bands then expose.
    sup = ts.get("meta", {}).get("supply", {})
    usable_C = max(1, int(sup.get("sat_frac", 1.0) * sup.get("C", 1)))
    cap_work_time = usable_C * sup.get("service_rate", 1.0) * (sum(actual) * dt)
    work_done = sum(ts.get("lat_size", []))
    utilization = (work_done / cap_work_time) if cap_work_time else float("nan")
    return {
        # completion is a headline: wait/tpw percentiles below cover only the
        # COMPLETED requests, so a policy that strands work looks unfairly good
        # unless you read the completion rate alongside.
        "offered": offered,
        "completed": completed,
        "unfinished": offered - completed,
        "completed_pct": (100.0 * completed / offered) if offered else float("nan"),
        "n_reqs": completed,
        "wait": dist(ts["req_wait"]),
        "tpw": dist(ts["req_tpw"]),
        "band_labels": band_labels,          # 6 labels (5 edges' bands, incl. tail)
        "band_pct": band_pct,                # % of OFFERED per band (sums w/ unfinished)
        "within_labels": within_labels,      # 5 edge labels (≤2s … ≤60s)
        "within_pct": within_pct,            # cumulative % of OFFERED served ≤ edge (CDF)
        "replicas": {"avg": ra, "std": var ** 0.5,
                     "max": max(actual) if actual else 0,
                     "rep_seconds": sum(actual) * dt,
                     # total billed fleet-time (booting + accepting + draining) and
                     # the boot-lag waste on top of usable rep_seconds.
                     "prov_seconds": sum(ts.get("provisioned", actual)) * dt,
                     "boot_waste": (sum(ts.get("provisioned", actual)) - sum(actual)) * dt},
        "utilization": utilization,
    }


if __name__ == "__main__":
    load = gen_load()
    supply = gen_supply_perfect(load)
    ts = sample(Simulator(load, supply).run())
    print(json.dumps({"grid_pts": len(ts["grid"]),
                      "reqs": len(load["requests"]),
                      "replicas": len(supply["replicas"]),
                      "peak_desired": max(ts["desired"]),
                      "peak_qlen": max(ts["qlen"])}, indent=2))
