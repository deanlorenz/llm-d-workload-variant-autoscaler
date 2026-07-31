"""Render a sampled simulation into the standard trace figure.

All panels share the time axis. A vertical line is drawn at every SCALE DECISION
(a change in the desired replica count) across ALL panels, so you can drop your
eye down any panel at that instant and read the event that triggered it — the
whole point is to see *why* a decision was made when it was made. Direction
arrows (▲ scale-up / ▼ scale-down) sit at the top of panel 1a. Panel 2 adds the
"took effect" moments (when actual replicas actually changed, one setup-lag
later). Tick-aligned gridlines come from matplotlib's own grid.

Every curve is derived from the actual simulated execution: a scaling *policy*
only changes the supply trace; the graphs always reflect what really happened.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

C_ARR = "#2563eb"      # arrival / offered   (blue)
C_DEP = "#059669"      # departure / done    (green)
C_DES = "#dc2626"      # desired / required  (red)
C_ACT = "#0891b2"      # actual              (teal)
C_CAP = "#9ca3af"      # capacity ceiling    (grey)
C_Q = "#d97706"        # queue               (amber)
C_SYS = "#7c3aed"      # in-system L(t)      (purple)

# small fixed palette of one-hue shades: identical backends read as one pool,
# shades only separate adjacent bands. Cycles, so band count is irrelevant.
BAND_SHADES = ["#a7d8de", "#5fbcc7", "#2f9aa8", "#63c39a", "#9bd8b0"]

# goodput quality: green (little/no waiting) -> dark red (long wait before service).
# Bands split by ABSOLUTE waiting time (FIFO-fair; not normalised by request size).
GP_COLORS = ["#16a34a", "#a3c644", "#f59e0b", "#ef4444", "#7f1d1d"]


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


def _mark_decisions(ax, grid, changes, label=False):
    """Neutral vertical line at each scale decision, drawn on EVERY panel so the
    triggering event in any panel lines up with the decision time. zorder above
    the opaque stackplots (panels 1a/3) so it is never painted over."""
    first = True
    for k, _ in changes:
        ax.axvline(grid[k], color="#334155", lw=1.0, ls=(0, (4, 3)), alpha=0.5,
                   zorder=3, label=("scale decision" if (label and first) else "_nolegend_"))
        first = False


def _decision_arrows(ax, grid, changes):
    """Direction arrows just inside the top of the reference panel: red ▲ for a
    scale-up decision, blue ▼ for scale-down. x in data coords, y in axes frac."""
    tr = ax.get_xaxis_transform()
    for k, d in changes:
        ax.text(grid[k], 0.97, "▲" if d > 0 else "▼", transform=tr, ha="center",
                va="top", fontsize=9, color=(C_DES if d > 0 else C_ARR),
                zorder=5, clip_on=True)


def _mark_effects(ax, grid, changes):
    """Where actual replicas changed = a boot finished (up) or a drain completed
    (down). Teal dotted, distinct from the slate decision lines. Panel 2 only."""
    first = True
    for k, _ in changes:
        ax.axvline(grid[k], color=C_ACT, lw=1.0, ls=(0, (1, 2)), alpha=0.75,
                   zorder=3.2, label=("took effect" if first else "_nolegend_"))
        first = False


def render(ts: dict, title: str, path: str):
    g = ts["grid"]
    rw, ww = ts["req_range"], ts["work_range"]
    fig, ax = plt.subplots(6, 1, figsize=(11, 15), sharex=True)

    # 1a — request throughput; departures split into goodput-quality bands
    # (colour = absolute waiting time before service started; FIFO-fair).
    # The stack sums to the departure rate; arrival rate overlaid for the gap.
    ax[0].stackplot(g, *ts["gp_bands"], colors=GP_COLORS, labels=ts["gp_labels"],
                    alpha=0.9, edgecolor="none")
    ax[0].plot(g, ts["arr_n"], color=C_ARR, lw=2.4, label="arrival rate")
    ax[0].set_ylabel("requests / s")
    ax[0].set_title(f"1a · request throughput + goodput quality  ({rw:.0f}s avg)",
                    loc="left", fontsize=10)

    # 1b — work rates
    ax[1].plot(g, ts["arr_w"], color=C_ARR, label="offered (arrival)")
    ax[1].plot(g, ts["dep_w"], color=C_DEP, label="completed (departure)")
    ax[1].plot(g, ts["capacity_work"], color=C_CAP, ls="--", label="capacity ceiling")
    ax[1].set_ylabel("work / s")
    ax[1].set_title(f"1b · work throughput  ({ww:.0f}s avg, Prom-style)", loc="left",
                    fontsize=10)

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

    # 5 — concurrency: in-system L(t) vs slot capacity (residence-time story)
    # gap between served and in-system IS the queued count -> shade it (also
    # separates the two lines where they'd otherwise coincide at queue=0)
    ax[5].fill_between(g, ts["in_service_total"], ts["nsys"], color=C_Q, alpha=0.18,
                       label="queued (L − served)")
    ax[5].plot(g, ts["nsys"], color=C_SYS, lw=1.6, alpha=0.9, label="in system  L(t)")
    ax[5].plot(g, ts["in_service_total"], color=C_ACT, lw=1.2, alpha=0.85,
               label="being served")
    ax[5].plot(g, ts["capacity_slots"], color=C_CAP, ls="--",
               label="usable slot capacity (accepting×⌊sat·C⌋)")
    ax[5].set_ylabel("requests")
    ax[5].set_xlabel("time (s)")
    ax[5].set_title("5 · concurrency: requests in system vs slot capacity  "
                    "(L = λ·W)", loc="left", fontsize=10)

    # scale-DECISION lines on every panel (change in desired), so the event that
    # triggered a decision can be read straight down any panel at that instant.
    decisions = _changes(ts["desired"])
    for a in ax:
        a.grid(True, alpha=0.2)                       # tick-aligned gridlines
        _mark_decisions(a, g, decisions, label=(a is ax[0]))
        a.legend(loc="upper right", fontsize=8, ncol=2)
        a.margins(x=0)
    _decision_arrows(ax[0], g, decisions)             # ▲/▼ direction on top panel

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
    _mark_decisions(ax, g, _changes(ts["desired"]), label=True)
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
