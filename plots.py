"""Render a sampled simulation into the standard trace figure.

All panels share the time axis. A vertical line is drawn at every SCALE DECISION
(a change in the desired replica count) across ALL panels, so you can drop your
eye down any panel at that instant and read the event that triggered it — the
whole point is to see *why* a decision was made when it was made. The lines are
direction-coloured (red dashed = scale-up, blue dashed = scale-down), each keyed
by a circled number planted on the panel-4 x-axis (right on the decision line) to
the numbered reason strip at the foot of the figure. Panel 2 adds the "took effect" moments
(purple dotted = boot done, grey dash-dot = drain done: when actual replicas actually
changed, one setup-lag / drain later). Actual
replicas and the capacity ceiling share one purple; draining work rides above the
ceiling in each pod's own colour. Tick-aligned gridlines come from matplotlib's
own grid.

Every curve is derived from the actual simulated execution: a scaling *policy*
only changes the supply trace; the graphs always reflect what really happened.
"""

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from sim import summarize

C_ARR = "#2563eb"      # arrival / offered   (blue)
C_DEP = "#059669"      # departure / done    (green)
C_DES = "#dc2626"      # desired / required  (red)
# one "paid-for capacity" colour shared by the actual-replica line (panel 2) and
# the capacity ceiling (panels 1b/3/5). Purple, chosen NOT to clash with the
# teal/green per-pod bands on panel 3.
C_CEIL = "#7c3aed"     # actual replicas + capacity ceiling (purple)
C_ACT = C_CEIL         # actual replicas share the ceiling colour
C_CAP = C_CEIL         # ceiling on 1b/3/5 is the same purple
C_Q = "#d97706"        # queue               (amber)  [panel 4]
C_SYS = "#7c3aed"      # in-system L(t)      (purple; cumulative figure only)
C_WAIT = "#dc2626"     # panel 5 waiting / in-system L(t)  (red)
C_SERVED = "#16a34a"   # panel 5 being served              (green)

# scale-event colours: direction-coded so up/down read at a glance.
C_UP = "#dc2626"       # scale-UP decision      (red, dashed)
C_DOWN = "#2563eb"     # scale-DOWN decision    (blue, dashed)
C_EFF_UP = C_CEIL      # took effect: boot done (purple, dotted — matches actual)
C_EFF_DN = "#9ca3af"   # took effect: drain done (grey, dash-dot — distinct dash)

# small fixed palette of one-hue shades: identical backends read as one pool,
# shades only separate adjacent bands. Cycles, so band count is irrelevant.
BAND_SHADES = ["#a7d8de", "#5fbcc7", "#2f9aa8", "#63c39a", "#9bd8b0"]

# goodput quality: an even green->red ramp over the six bands (little/no waiting
# -> long wait before service). Bands split by ABSOLUTE waiting time (FIFO-fair;
# not normalised by request size). 6 colours: good/almost/mediocre/meh/bad/failed.
GP_COLORS = ["#15803d", "#65a30d", "#eab308", "#f59e0b", "#ea580c", "#b91c1c"]

# work COMPOSITION by request size (panel 1b): a light pastel blue ramp, small->large
# — distinct from GP_COLORS (goodput green->red) and BAND_SHADES (per-pod teal). Kept
# light (used at low alpha too) since panel 1b already carries arrival/capacity lines
# in saturated blue/purple — a heavy stack would compete with them.
SIZE_SHADES = ["#dbeafe", "#93c5fd", "#60a5fa"]


def _changes(series):
    """Indices where a step series changes value, with direction: +1 up / −1 down.
    A change in `desired` is a scale DECISION; a change in `actual` is the moment
    it TOOK EFFECT (one setup-lag later, or a drain completing)."""
    out, prev = [], None
    for k, v in enumerate(series):
        if prev is not None and v != prev:
            out.append((k, 1 if v > prev else -1))
        prev = v
    return out


def _mark_decisions(ax, decisions, label=False):
    """Vertical line at each scale DECISION, drawn on EVERY panel so the
    triggering event in any panel lines up with the decision time. Direction-
    coded: red dashed = scale-up, blue dashed = scale-down. Driven by the exact
    decision times (not grid indices). zorder above the opaque stackplots
    (panels 1a/3) so it is never painted over."""
    seen_up = seen_dn = False
    for d in decisions:
        up = d["up"]
        lbl = "_nolegend_"
        if label:
            if up and not seen_up:
                lbl, seen_up = "scale-up", True
            elif not up and not seen_dn:
                lbl, seen_dn = "scale-down", True
        ax.axvline(d["t"], color=(C_UP if up else C_DOWN), lw=1.0,
                   ls=(0, (4, 3)), alpha=0.55, zorder=3, label=lbl)


def _decision_numbers(ax, decisions, y=0.0):
    """Circled sequence number planted ON the given panel's x-axis (y=0 in axes
    fraction), one per decision, coloured by direction (red up / blue down). It
    sits directly on the decision's vertical line so the number reads as attached
    to it — and keys into the decision strip at the foot of the figure."""
    tr = ax.get_xaxis_transform()
    for i, d in enumerate(decisions, 1):
        ax.text(d["t"], y, str(i), transform=tr, ha="center", va="center",
                fontsize=6.5, color="white", zorder=6, clip_on=False,
                bbox=dict(boxstyle="circle,pad=0.16", linewidth=0,
                          fc=(C_UP if d["up"] else C_DOWN)))


def _mark_effects(ax, grid, changes):
    """Where actual replicas changed = a boot finished (up) or a drain completed
    (down). Direction-coded and dash-distinct from the dashed decision lines:
    boot-done is purple dotted (matches the actual-replica line), drain-done is
    grey dash-dot. Panel 2 only."""
    seen_up = seen_dn = False
    for k, dirn in changes:
        up = dirn > 0
        lbl = "_nolegend_"
        if up and not seen_up:
            lbl, seen_up = "took effect (boot done)", True
        elif not up and not seen_dn:
            lbl, seen_dn = "took effect (drain done)", True
        ax.axvline(grid[k], color=(C_EFF_UP if up else C_EFF_DN), lw=1.0,
                   ls=((0, (1, 2)) if up else (0, (5, 2, 1, 2))),
                   alpha=0.85, zorder=3.2, label=lbl)


def _render_key(ax, decisions, prc=None):
    """Bottom text strip: numbered list of every scale decision and its reason,
    keyed to the circled numbers on the panel-4 x-axis. Multi-column when dense.
    The title states per-replica usable capacity (w/s), so the open-loop
    'DR … ⇒ n' reads as n = ⌈headroom · DR / PRC⌉  (DR = demand rate; code `owr`)."""
    ax.axis("off")
    prc_txt = f"per-replica capacity ≈ {prc:.0f} w/s;  " if prc else ""
    ax.text(0.0, 0.99, f"decision key  ({prc_txt}number ↔ marker on panel 4 x-axis)",
            transform=ax.transAxes, ha="left", va="top", fontsize=10,
            fontweight="bold")
    if not decisions:
        ax.text(0.0, 0.78, "no scale decisions in this run", ha="left", va="top",
                fontsize=9, color="#64748b", transform=ax.transAxes)
        return
    n = len(decisions)
    ncol = 1 if n <= 10 else (2 if n <= 24 else 3)
    per = math.ceil(n / ncol)
    dy = 0.80 / per
    for i, d in enumerate(decisions):
        col, row = i // per, i % per
        x = 0.005 + col * (1.0 / ncol)
        y = 0.78 - row * dy
        c = C_UP if d["up"] else C_DOWN
        arrow = "▲" if d["up"] else "▼"
        ax.text(x, y, f"{i + 1}.", ha="left", va="top", fontsize=7.5,
                fontweight="bold", color=c, transform=ax.transAxes)
        ax.text(x + 0.028, y, f"{d['t']:.0f}s  {d['frm']}{arrow}{d['to']}   {d['why']}",
                ha="left", va="top", fontsize=7.5, color="#1e293b",
                transform=ax.transAxes)


def render(ts: dict, title: str, path: str):
    g = ts["grid"]
    rw, ww = ts["req_range"], ts["work_range"]
    decisions = ts.get("decisions", [])
    # headline stats for each panel's right-side title. NOTE: named `stat`, not `s`
    # — panel 3 below reuses `s` as a per-drain-start loop variable (`s = ds["slot"]`),
    # which would silently clobber a same-named summary dict for every panel after it.
    stat = summarize(ts)
    # 6 shared-x plot panels + a thin 7th text strip for the decision key.
    fig = plt.figure(figsize=(11, 16.5))
    gs = fig.add_gridspec(7, 1, height_ratios=[1, 1, 1, 1, 1, 1, 1.15], hspace=0.42)
    ax = [fig.add_subplot(gs[0])]
    ax += [fig.add_subplot(gs[i], sharex=ax[0]) for i in range(1, 6)]
    key_ax = fig.add_subplot(gs[6])
    for a in ax[:-1]:
        a.tick_params(labelbottom=False)

    # 1a — request throughput; departures split into goodput-quality bands
    # (colour = absolute waiting time before service started; FIFO-fair).
    # The stack sums to the departure rate; arrival rate overlaid for the gap.
    ax[0].stackplot(g, *ts["gp_bands"], colors=GP_COLORS, labels=ts["gp_labels"],
                    alpha=0.9, edgecolor="none")
    # thin dark outline tracing the TOTAL departure curve (stack top), so the
    # departure boundary reads crisply against the arrival line above it.
    dep_total = [sum(v) for v in zip(*ts["gp_bands"])]
    ax[0].plot(g, dep_total, color="#1f2937", lw=0.8, alpha=0.8, zorder=2.5)
    ax[0].plot(g, ts["arr_n"], color=C_ARR, lw=2.4, label="arrival rate")
    ax[0].set_ylabel("requests / s")
    ax[0].set_title(f"1a · request throughput + goodput quality  ({rw:.0f}s avg)",
                    loc="left", fontsize=10)
    ax[0].set_title(f"served ≤30s: {stat['within_pct'][2]:.1f}%",
                    loc="right", fontsize=9, color="#374151")

    # 1b — work rates; completed work split into size-composition bands (small /
    # medium / large tercile of this run's completed sizes) instead of one line —
    # shows how much of the delivered work came from large vs small items.
    ax[1].plot(g, ts["arr_w"], color=C_ARR, label="offered (arrival)")
    ax[1].stackplot(g, *ts["size_bands"], colors=SIZE_SHADES, labels=ts["size_labels"],
                    alpha=0.6, edgecolor="none")
    # thin dark outline tracing the TOTAL completed-work curve (stack top), same
    # treatment as panel 1a's departure outline — not per-band edges.
    dep_total_w = [sum(v) for v in zip(*ts["size_bands"])]
    ax[1].plot(g, dep_total_w, color="#1f2937", lw=0.8, alpha=0.8, zorder=2.5)
    ax[1].plot(g, ts["capacity_work"], color=C_CAP, ls="--", label="capacity ceiling")
    # shade the headroom between what was completed and the ceiling: capacity you
    # paid for but did not use (only where the ceiling sits above completions).
    ax[1].fill_between(g, ts["dep_w"], ts["capacity_work"],
                       where=[c > d for c, d in zip(ts["capacity_work"], ts["dep_w"])],
                       interpolate=True, color=C_CAP, alpha=0.15,
                       label="unused capacity")
    ax[1].set_ylabel("work / s")
    ax[1].set_title(f"1b · work throughput  ({ww:.0f}s avg, Prom-style)", loc="left",
                    fontsize=10)
    ax[1].set_title(f"{stat['replicas']['rep_seconds']:.0f} rep·s",
                    loc="right", fontsize=9, color="#374151")

    # 2 — backends desired vs actual, with the DRAINING slice broken out.
    # A draining replica is alive and still finishing its in-flight work, but is
    # NOT accepting new work — so it does not count as usable capacity for the
    # scale decision (the queue-aware sizer already excludes it). We show it as a
    # hatched band riding just UNDER the actual line (accepting..actual), not a
    # separate quantity floating up from zero, so you read actual = accepting +
    # draining at a glance. tiny opposite y-offsets so equal lines don't hide.
    actual = ts["actual"]
    accepting = ts["accepting"]
    ax[2].step(g, [d + 0.05 for d in ts["desired"]], where="post", color=C_DES,
               label="desired", lw=2.2, alpha=0.9)
    ax[2].step(g, [a - 0.05 for a in actual], where="post", color=C_ACT,
               label="actual (alive)", lw=2.2, alpha=0.9)
    ax[2].fill_between(g, accepting, actual, step="post", facecolor="none",
                       hatch="////", edgecolor=C_ACT, linewidth=0.0, alpha=0.6,
                       label="draining (not usable capacity)")
    _mark_effects(ax[2], g, _changes(actual))
    ax[2].set_ylabel("backends")
    ax[2].yaxis.set_major_locator(MaxNLocator(integer=True))
    ax[2].set_title("2 · autoscaling: desired vs actual replicas "
                    "(draining ≠ usable capacity)", loc="left", fontsize=10)
    ax[2].set_title(f"{stat['replicas']['prov_seconds']:.0f} prov·s",
                    loc="right", fontsize=9, color="#374151")

    # 3 — per-backend work being delivered NOW (stack, from first dispatch) vs work
    # demanded by requests in system (L·rate) vs capacity ceiling (actual replicas in
    # work units). Stack rides under demand by exactly the queued (starved) work;
    # demand above the ceiling = under-provisioned.
    ids = ts["backend_ids"]
    stacks = [ts["backend_work"][i] for i in ids]
    if stacks:
        colors = [BAND_SHADES[k % len(BAND_SHADES)] for k in range(len(ids))]
        ax[3].stackplot(g, *stacks, colors=colors, edgecolor="white", linewidth=0.15,
                        labels=["_nolegend_"] * len(ids))
    # draining work (a stopped backend's in-flight requests) is NOT usable
    # capacity, so it is not in the demand line or under the ceiling. Draw it in
    # the SAME per-pod colour, stacked ON TOP of the accepting stack (slightly
    # translucent), so a pod's band simply lifts above the ceiling when it stops
    # accepting — position, not a new colour, is the "draining" signal. A dotted
    # vertical line in the pod's colour marks the instant each pod began draining.
    drains = ts.get("backend_work_drain", {})
    acc_tot = [sum(vals) for vals in zip(*stacks)] if stacks else [0.0] * len(g)
    base = list(acc_tot)
    drew = False
    for k, i in enumerate(ids):
        dv = drains.get(i)
        if not dv or not any(v > 0 for v in dv):
            continue
        top = [b + d for b, d in zip(base, dv)]
        shade = BAND_SHADES[k % len(BAND_SHADES)]
        # thin, dark, solid outline so the draining slice reads as distinct from
        # the accepting band underneath it (per-pod fill colour is the same hue).
        ax[3].fill_between(g, base, top, facecolor=shade, alpha=0.5,
                           edgecolor="#1f2937", linewidth=0.6,
                           label=("draining (above ceiling ⇒ not capacity)"
                                  if not drew else "_nolegend_"))
        drew = True
        base = top
    drew_line = False
    for ds in ts.get("drain_starts", []):
        s = ds["slot"]
        ax[3].axvline(ds["t"], color=BAND_SHADES[s % len(BAND_SHADES)], lw=1.0,
                      ls=":", alpha=0.75, zorder=3.5,
                      label=("drain start" if not drew_line else "_nolegend_"))
        drew_line = True
    ax[3].plot(g, ts["demand_work"], color=C_DES, lw=1.8,
               label="work demand (L·service_rate)")
    ax[3].plot(g, ts["capacity_work"], color=C_CAP, ls="--", label="capacity ceiling")
    ax[3].set_ylabel("work / s")
    ax[3].set_title("3 · work delivered per backend (stacked) vs demand & capacity",
                    loc="left", fontsize=10)

    # 4 — queue length
    ax[4].fill_between(g, ts["qlen"], color=C_Q, alpha=0.25)
    ax[4].plot(g, ts["qlen"], color=C_Q, label="queue length")
    ax[4].set_ylabel("queued reqs")
    ax[4].set_title("4 · global queue depth", loc="left", fontsize=10)
    ax[4].set_title(f"wait p75: {stat['wait']['p75']:.1f}s",
                    loc="right", fontsize=9, color="#374151")

    # 5 — concurrency: in-system L(t) vs slot capacity (residence-time story)
    # gap between served and in-system IS the queued count -> shade it (also
    # separates the two lines where they'd otherwise coincide at queue=0)
    # idle-slot headroom: capacity paid for but not serving (only where the ceiling
    # sits above the served count — i.e. when there is no queue, since a non-empty
    # queue fills every slot). Purple, matching the panel-1b unused-capacity fill.
    ax[5].fill_between(g, ts["in_service_total"], ts["capacity_slots"],
                       where=[c > s for c, s in zip(ts["capacity_slots"],
                                                    ts["in_service_total"])],
                       interpolate=True, color=C_CAP, alpha=0.15,
                       label="unused capacity")
    ax[5].fill_between(g, ts["in_service_total"], ts["nsys"], color=C_WAIT, alpha=0.16,
                       label="queued (L − served)")
    ax[5].plot(g, ts["nsys"], color=C_WAIT, lw=1.6, alpha=0.9, label="in system  L(t)")
    ax[5].plot(g, ts["in_service_total"], color=C_SERVED, lw=1.4, alpha=0.95,
               label="being served")
    ax[5].plot(g, ts["capacity_slots"], color=C_CEIL, ls="--",
               label="usable slot capacity (accepting×⌊sat·C⌋)")
    ax[5].set_ylabel("requests")
    ax[5].set_xlabel("time (s)")
    ax[5].set_title("5 · concurrency: requests in system vs slot capacity  "
                    "(L = λ·W)", loc="left", fontsize=10)
    ax[5].set_title(f"failed: {stat['band_pct'][-1]:.1f}%",
                    loc="right", fontsize=9, color="#374151")

    # scale-DECISION lines on every panel (direction-coloured), so the event that
    # triggered a decision can be read straight down any panel at that instant.
    for a in ax:
        a.grid(True, alpha=0.2)                       # tick-aligned gridlines
        _mark_decisions(a, decisions, label=(a is ax[0]))
        if a in (ax[0], ax[1]):
            # panels 1a/1b carry a busy stacked-band key; keep it narrow (single
            # column) and tucked top-left so it never sits over the ramp data.
            a.legend(loc="upper left", fontsize=6.5, ncol=1,
                     labelspacing=0.3, handlelength=1.2, borderpad=0.4,
                     framealpha=0.85)
        else:
            a.legend(loc="upper right", fontsize=8, ncol=2)
        a.margins(x=0)
    _decision_numbers(ax[4], decisions)               # ① ② … planted on the panel-4 x-axis
    sup = ts.get("meta", {}).get("supply", {})
    prc = max(1, int(sup.get("sat_frac", 1.0) * sup.get("C", 1))) * sup.get("service_rate", 1.0)
    _render_key(key_ax, decisions, prc)               # numbered reason list

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.99))
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def render_cumulative(ts: dict, title: str, path: str):
    """Cumulative arrivals A(t) vs departures D(t). Vertical gap = number in
    system L(t); horizontal gap = wait W; area between = total time-in-system."""
    g = ts["grid"]
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.step(g, ts["cum_arr"], where="post", color=C_ARR, lw=1.8,
            label="cumulative arrivals  A(t)")
    ax.step(g, ts["cum_dep"], where="post", color=C_DEP, lw=1.8,
            label="cumulative departures  D(t)")
    ax.fill_between(g, ts["cum_dep"], ts["cum_arr"], step="post",
                    color=C_SYS, alpha=0.15,
                    label="area between = total time-in-system")
    # mark one instant to show the vertical L(t) reading
    k = len(g) // 2
    ax.annotate("", xy=(g[k], ts["cum_arr"][k]), xytext=(g[k], ts["cum_dep"][k]),
                arrowprops=dict(arrowstyle="<->", color=C_SYS, lw=1.2))
    ax.text(g[k], (ts["cum_arr"][k] + ts["cum_dep"][k]) / 2,
            "  L(t) = in system", color=C_SYS, fontsize=8, va="center")
    _mark_decisions(ax, ts.get("decisions", []), label=True)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("cumulative requests")
    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=9)
    ax.margins(x=0)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def render_latency(ts: dict, title: str, path: str):
    """Standalone latency view: per-request time-in-system, coloured by size."""
    fig, ax = plt.subplots(figsize=(11, 4))
    sc = ax.scatter(ts["lat_done"], ts["lat_value"], c=ts["lat_size"],
                    cmap="viridis", s=14, alpha=0.7, edgecolors="none")
    fig.colorbar(sc, ax=ax, label="request size (work units)")
    ax.set_xlabel("departure time (s)")
    ax.set_ylabel("time in system (s)")
    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.margins(x=0)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Cross-policy comparison figures (CDF overlay, cost-quality frontier) and
# parameter-sweep line plots. Unlike the per-scenario trace above, these put
# multiple policies / knob settings on ONE shared axis.
# --------------------------------------------------------------------------

# One stable colour + dash per policy so the CDF and the cost-quality scatter
# agree at a glance. Order mirrors the narrative (ideal reference first, the
# hero qexp in the middle). hpa-combined is dashed because it overlaps hpa-queue.
POLICY_STYLE = {
    "ideal":           ("#111827", "-"),    # near-black — the clairvoyant reference
    "static":          ("#9ca3af", "-"),    # grey — dumb always-on
    "setup-lag":       ("#dc2626", "-"),    # red
    "queue-aware":     ("#f59e0b", "-"),    # amber
    "qexp":            ("#16a34a", "-"),    # green — the hero
    "hpa-queue":       ("#2563eb", "-"),    # blue
    "hpa-concurrency": ("#7c3aed", "-"),    # purple
    "hpa-combined":    ("#0891b2", "--"),   # teal dashed (overlaps hpa-queue)
}


def _style(name):
    return POLICY_STYLE.get(name, ("#6b7280", "-"))


def render_wait_cdf(runs: dict, costs: dict, title: str, path: str,
                    edges=(2.0, 15.0, 30.0, 45.0, 60.0), xmax=None):
    """Overlay every policy's waiting-time CDF on one axis: y = share of OFFERED
    served within t seconds (a policy that strands work asymptotes below 100%,
    since unfinished requests are not in req_wait but still count in the offered
    denominator). Vertical guides mark the quality-band edges; each legend entry
    carries the policy's billed fleet cost so promptness and cost read together.
    `runs` = {name: ts}; `costs` = {name: provisioned·seconds}.

    The denominator is the trace's explicit `offered` count, never `cum_arr[-1]`:
    under a burn-in prelude the offered series deliberately opens at L(t0) rather
    than 0 (Little's-Law geometry needs a common baseline on both series), so
    `cum_arr[-1]` is `offered + L(t0)` and would depress every ceiling — enough to
    put the figure in contradiction with its own summary table.

    `xmax=None` autoscales the axis to the worst observed wait across `runs`. Each
    curve is also extended by an explicit terminal segment out to the right spine:
    a step CDF that stops at its largest observed wait degenerates to a
    zero-width vertical hairline for a policy that queued nothing, which hides
    under the y-axis spine and reads as a missing curve rather than a perfect one.
    Coincident curves are drawn widest-first so overlapping policies nest visibly
    instead of the last one painting over all the rest."""
    # The axis extent must be known before any curve is drawn, since each one is
    # extended to the right spine.
    worst = 0.0
    for ts in runs.values():
        if ts.get("req_wait"):
            worst = max(worst, max(ts["req_wait"]))
    if xmax is None:
        xmax = max(worst * 1.08, max(edges) * 1.05)

    fig, ax = plt.subplots(figsize=(11, 4.2))
    n = max(1, len(runs) - 1)
    for i, (name, ts) in enumerate(runs.items()):
        waits = sorted(ts["req_wait"])
        offered = ts.get("offered") or len(waits)
        if not waits or not offered:
            continue
        xs, ys = [0.0], [0.0]                          # step CDF over OFFERED
        for j, w in enumerate(waits, 1):
            xs.append(w)
            ys.append(100.0 * j / offered)
        xs.append(xmax)                                # hold the ceiling to the spine
        ys.append(ys[-1])
        color, dash = _style(name)
        cost = costs.get(name)
        lbl = name + (f"  ({cost:.0f} prov·s)" if cost is not None else "")
        ax.step(xs, ys, where="post", color=color, linestyle=dash,
                lw=3.4 - 2.2 * (i / n), alpha=0.9, label=lbl)
    for e in edges:
        ax.axvline(e, color="#9ca3af", ls=":", lw=0.8, alpha=0.7)
        ax.text(e, 1.5, f"{e:g}s", fontsize=8, color="#6b7280",
                ha="center", va="bottom", rotation=90)
    ax.set_xlim(0, xmax)
    # A little headroom above 100: on a shape where most policies queue nothing, the
    # coincident ceiling curves sit exactly at 100 and would otherwise be painted over
    # by the top spine and read as absent.
    ax.set_ylim(0, 102)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("waiting time before service, t (s)")
    ax.set_ylabel("served within t  (% of offered)")
    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9,
              framealpha=0.9, title="policy (billed cost)")
    fig.text(0.012, 0.012,
             "Policies that queue nothing coincide exactly along the ceiling; line width "
             "descends in legend order so overlapping curves stay visible.",
             fontsize=8, color="#6b7280", ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def _pareto_frontier(pts: dict):
    """pts: name -> (cost, quality). Return the non-dominated set (minimise cost,
    maximise quality) sorted by cost — the upper-left staircase where each extra
    unit of cost buys strictly more quality."""
    items = sorted(pts.items(), key=lambda kv: (kv[1][0], -kv[1][1]))
    front, best_q = [], -1.0
    for name, (cost, q) in items:
        if q > best_q:
            front.append((name, cost, q))
            best_q = q
    return front


def render_cost_quality(summaries: dict, title: str, path: str,
                        extra_points=None, label_overrides=None):
    """Cost–quality frontier: x = billed fleet-time (provisioned·seconds),
    y = promptness (% of offered served within 15s). One labelled point per
    policy. The clairvoyant IDEAL is a separate reference star (not deployable);
    the dashed line is the Pareto frontier over the DEPLOYABLE policies — any
    point below-and-right of it is dominated (something is both cheaper AND
    prompter). This is where 'same cost, better quality' becomes visible.

    `extra_points` overlays off-baseline operating points of policies already
    shown — a list of (label, cost, quality, base_name) tuples. They take the
    base policy's colour (via `base_name`) but draw as hollow markers so the
    swept variant reads as the same algorithm at a different knob (e.g. the two
    Q sizers at higher headroom — how much further up the frontier more static
    margin buys). They ARE folded into the frontier and the axis ranges.
    `label_overrides` maps a summary name to its annotation text (colour still
    resolves from the real name), so the baseline Q points can carry their
    headroom too — e.g. queue-aware -> 'qaware(1.3)'."""
    extra_points = extra_points or []
    label_overrides = label_overrides or {}
    pts = {}
    for name, s in summaries.items():
        cost = s["replicas"]["prov_seconds"]
        wp = s.get("within_pct", [])
        q = wp[1] if len(wp) > 1 else float("nan")     # served ≤15s = CDF@edge[1]
        pts[name] = (cost, q)
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    deploy = {n: p for n, p in pts.items() if n != "ideal"}
    for label, cost, q, _base in extra_points:            # extras join the frontier
        deploy[label] = (cost, q)
    front = _pareto_frontier(deploy)
    if front:
        ax.plot([c for _, c, _ in front], [q for _, _, q in front],
                color="#9ca3af", ls="--", lw=1.4, zorder=1,
                label="Pareto frontier (deployable)")
    # label deconfliction: some policies land on near-identical (cost, quality)
    # — hpa-combined overlaps hpa-queue by design. Nudge a colliding label below
    # its point instead of overprinting the one already placed there.
    all_costs = [c for c, _ in pts.values()] + [c for _, c, _, _ in extra_points]
    all_q = [q for _, q in pts.values()] + [q for _, _, q, _ in extra_points]
    xr = (max(all_costs) - min(all_costs)) or 1.0
    yr = (max(all_q) - min(all_q)) or 1.0
    # The two Q sizers each contribute a tight cluster of headroom points (qexp is
    # near-saturated by 1.3, so its trio bunches along the top) — auto-nudge can't
    # separate three near-collinear labels, so place them deterministically:
    # leftmost anchors left, middle above, rightmost right; qexp trio above the
    # line, qaware trio below it.
    QPLACE = {"qexp(1.3)": (-8, 8, "right"), "qexp(1.5)": (0, 12, "center"),
              "qexp(2.0)": (8, 8, "left"),
              "qaware(1.3)": (-8, -15, "right"), "qaware(1.5)": (0, -18, "center"),
              "qaware(2.0)": (8, -12, "left")}

    def _annotate(disp, cost, q, color):
        if disp in QPLACE:
            dx, dy, ha = QPLACE[disp]
            ax.annotate(disp, (cost, q), textcoords="offset points",
                        xytext=(dx, dy), fontsize=9, color=color, ha=ha)
        else:
            collide = any(abs(cost - pc) / xr < 0.03 and abs(q - pq) / yr < 0.03
                          for pc, pq in placed)
            ax.annotate(disp, (cost, q), textcoords="offset points",
                        xytext=(9, -13) if collide else (9, 5), fontsize=9, color=color)
        placed.append((cost, q))

    placed = []
    for name, (cost, q) in pts.items():
        color, _ = _style(name)
        if name == "ideal":
            ax.scatter([cost], [q], marker="*", s=340, color=color, zorder=4,
                       edgecolors="white", linewidths=0.8)
            ax.annotate("ideal (clairvoyant)", (cost, q),
                        textcoords="offset points", xytext=(10, -4), fontsize=9)
        else:
            ax.scatter([cost], [q], s=95, color=color, zorder=3,
                       edgecolors="white", linewidths=0.8)
            _annotate(label_overrides.get(name, name), cost, q, "#000000")
    # off-baseline sweep variants: hollow marker in the base policy's colour.
    for label, cost, q, base in extra_points:
        color, _ = _style(base)
        ax.scatter([cost], [q], s=80, facecolors="none", edgecolors=color,
                   linewidths=1.7, zorder=3)
        _annotate(label, cost, q, color)
    ax.set_xlabel("billed fleet-time — provisioned·seconds   (cost →)")
    ax.set_ylabel("served within 15s   (% of offered — promptness →)")
    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.margins(0.13)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def render_sweep(title, xlabel, xs, groups, path, xmark=None, mark_label="baseline"):
    """Two-panel parameter-sweep figure. Panel A (quality): good% (solid, left
    axis) and wait p90 (dashed, right axis) vs the swept knob. Panel B (cost):
    provisioned·seconds vs the knob. `groups` = list of
    {label, good, p90, prov, color}; multiple groups overlay (e.g. two setups).
    `xmark` draws a baseline guide line on both panels."""
    fig, (axq, axc) = plt.subplots(1, 2, figsize=(11, 4.3))
    axp = axq.twinx()
    for g in groups:
        c = g.get("color", "#2563eb")
        if "good15" in g:
            # cumulative served ≤15s (the "actual quality" bar): faint, same
            # colour, triangle marker — always ≥ the ≤2s line it sits above.
            axq.plot(xs, g["good15"], "-^", color=c, lw=1.6, ms=4, alpha=0.4)
        axq.plot(xs, g["good"], "-o", color=c, lw=2, ms=4, label=g["label"])
        axp.plot(xs, g["p90"], "--s", color=c, lw=1.4, ms=3, alpha=0.65)
        axc.plot(xs, g["prov"], "-o", color=c, lw=2, ms=4, label=g["label"])
    axq.set_xlabel(xlabel)
    axc.set_xlabel(xlabel)
    axq.set_ylabel("served % (solid ● ≤2s · faint ▲ ≤15s)")
    axp.set_ylabel("wait p90 (s) — dashed")
    axc.set_ylabel("provisioned·seconds (fleet cost)")
    axq.set_title("quality", loc="left", fontsize=10)
    axc.set_title("cost", loc="left", fontsize=10)
    for a in (axq, axc):
        a.grid(True, alpha=0.25)
        if xmark is not None:
            a.axvline(xmark, color="#111827", ls=":", lw=1.0, alpha=0.6)
    if len(groups) > 1:
        axq.legend(loc="best", fontsize=8)
        axc.legend(loc="best", fontsize=8)
    if xmark is not None:
        axq.annotate(mark_label, (xmark, axq.get_ylim()[1]),
                     textcoords="offset points", xytext=(3, -3),
                     fontsize=8, color="#111827", va="top")
    fig.suptitle(title, x=0.01, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
