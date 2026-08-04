"""Build a self-contained comparison report (out/index.html) from the rendered
figures + summary table. Read-only over the sim: it just references the PNGs
already in out/ and parses out/summary.md.

Run:  ./.venv/bin/python report.py     (after run.py has produced the figures)

No server needed — open out/index.html directly (file://). Pure vanilla HTML/CSS/JS.
"""

import json
import os
import re

OUT = "out"

# All figures render at figsize=(11,15) dpi=120 -> 1320x1800 px. The Compare
# fit<->full slider interpolates pane image width between "fit to pane" and this.
FULL_W = 1320

# Scenario metadata mirrors run.py's outputs + the per-test framing. Strings are
# recalibrated to the sat_frac=0.7 results (see design-doc §6): all three complete
# 100%, so the story is the waiting-quality mix, NOT completion or peak-queue.
# Do NOT reintroduce the old "recovers completion / survives lag / overshoots"
# answers — they are false under this calibration.
SCENARIOS = [
    {"key": "ideal", "label": "Ideal",
     "png": "01-ideal.png", "latency": "01-ideal-latency.png",
     "setup": "setup=0 · size to CENTERED demand rate (DR) × headroom (clairvoyant)",
     "answers": "what does good look like? → 100% served ≤2s; never queues on a smooth bump"},
    {"key": "static", "label": "No scaling",
     "png": "07-static.png", "latency": "07-static-latency.png",
     "setup": "fixed fleet pinned at maxReplicaCount=10 for the whole run · no autoscaler, pre-warmed (setup=0)",
     "answers": "what if you just provision for max and never scale? → 100% prompt (never queues on this "
                "bump), but the most expensive fleet (6000 rep·s ≈ 3× ideal) at the lowest utilisation — "
                "promptness bought by paying for peak capacity through every valley"},
    {"key": "setup-lag", "label": "Setup lag",
     "png": "02-setup-lag.png", "latency": "02-setup-lag-latency.png",
     "setup": "setup=90 · the SAME demand-tracking commands as ideal, landing 90s late",
     "answers": "does a correct policy survive 90s boot lag? → still completes 100%, but only ~20% served promptly. "
                "⚠ confound: setup-lag→queue-aware changes TWO things at once (foresight lost, centered→trailing window, "
                "AND a backlog-drain term added) — not a clean A/B on the backlog term alone"},
    {"key": "queue-aware", "label": "Queue-aware",
     "png": "03-queue-aware.png", "latency": "03-queue-aware-latency.png",
     "setup": "setup=90, drain_time=30 · demand-tracking + backlog-drain (reactive, TRAILING)",
     "answers": "can a reactive backlog term rescue quality? → only modestly (~28% prompt), and it worsens the tail "
                "(chases the backlog after it has already piled up during the boot) — motivates anticipation, see Qexp"},
    {"key": "qexp", "label": "Qexp (anticipatory)",
     "png": "08-queue-aware-exp.png", "latency": "08-queue-aware-exp-latency.png",
     "setup": "setup=90, drain_time=30 · anticipatory: a PERIODIC control loop that sizes to the backlog PEAK "
              "projected over the committed boot schedule (up now + pending at their estimated land-times). Reads only "
              "the observable queue LEVEL — no foresight of arrivals",
     "answers": "does anticipating the boot-window pile-up help? → yes: ~35% prompt vs reactive's ~28%, tail p90 43s "
                "vs 51s, and a lower queue peak (583 vs 704) — at the SAME fleet cost (2130 vs 2169 prov·s). It orders "
                "sooner and HOLDS through the boot instead of chasing the queue after the fact. Still no foresight — "
                "it only projects the CURRENT queue forward (axis-2 dead-time compensation, not axis-1)"},
    {"key": "hpa-queue", "label": "HPA queue",
     "png": "04-hpa-queue.png", "latency": "04-hpa-queue-latency.png",
     "setup": "KEDA queue-depth · AverageValue target=1/replica → desired=ceil(Q) · setup=90, cap 10",
     "answers": "naive queue-depth scaling (target 1)? → 92.7% prompt, but pins at the maxReplicaCount=10 cap and "
                "burns ~2.5× the fleet (4860 vs ideal 1980 rep·s); the cold-start backlog is the only tail"},
    {"key": "hpa-concurrency", "label": "HPA concurrency",
     "png": "05-hpa-concurrency.png", "latency": "05-hpa-concurrency-latency.png",
     "setup": "KEDA running-count · AverageValue target c≈58/replica → desired=ceil(R/c) · setup=90, cap 10",
     "answers": "concurrency-only scaling? → catastrophic: the running-count signal is capacity-capped (R ≤ n·usable_C), "
                "so it is BLIND to the 2569-deep queue behind it, stalls at 4 replicas, 88% wait >60s. Concurrency alone "
                "cannot outrun boot lag"},
    {"key": "hpa-combined", "label": "HPA combined",
     "png": "06-hpa-combined.png", "latency": "06-hpa-combined-latency.png",
     "setup": "KEDA both triggers · desired=max(queue, concurrency) · up on either, down on both · setup=90, cap 10",
     "answers": "combining the two triggers (native KEDA max)? → the queue trigger rescues the concurrency blind spot; "
                "matches queue-depth (92.7% prompt, 4860 rep·s) — this is the well-lit path's saturation+running pairing"},
]

# Per-row "what it means" annotations for the Table tab. Keyed by the row's first
# cell (metric label, already stripped in summary.md). Percentile/family rows are
# matched by prefix so we don't enumerate every pNN.
ROW_MEANING = {
    # "offered" is the denominator for every quality %: dividing by it (not by
    # COMPLETED) is what guards against survivorship bias — a policy that strands
    # its slowest requests can't look good by counting only the survivors.
    "offered": "every request that arrived — the denominator (guards against survivorship bias)",
    "completed": "requests that finished within the run",
    "completed %": "completion rate — the 'did it finish at all' number",
    "unfinished": "still in system at trace end (permanently stranded)",
    # Cumulative "≤Ns %" rows are matched by the "≤" prefix in row_meaning()
    # below (labels/edges are dynamic, so we don't enumerate them here).
    "replica·seconds": "∫ READY replicas dt (accepting fleet only) — the usable-cost proxy",
    "provisioned·seconds": "∫ ALL billed replicas dt (booting + accepting + draining) — total fleet-time you pay for",
    "boot-lag waste·s": "provisioned − ready replica·seconds: capacity billed while booting or draining, never serving",
    "utilization": "delivered work ÷ usable capacity paid for; <1 idle fleet, ~1+ packed (packed can still fail latency — read next to the % bands)",
}


def row_meaning(label: str) -> str:
    if label in ROW_MEANING:
        return ROW_MEANING[label]
    if label.startswith("≤"):
        return ("cumulative — share of ALL offered served within this wait "
                "(the wait CDF sampled at this bound; rows climb toward 100%)")
    if label.startswith("failed"):
        return ("finished but slower than the last band edge — the slow tail on "
                "the OFFERED denominator (completed % − last ≤Ns %); unfinished "
                "requests are counted separately in the row above")
    if label.startswith("wait "):
        return "pre-service wait (dispatch − arrival), completed requests only"
    if label.startswith("time/work "):
        return ("time-in-system ÷ size — a slowdown proxy; informational only, NOT "
                "the scored signal (the bands score absolute wait, so short and long "
                "requests are held to the same 'promptly served' bar)")
    if label.startswith("replicas "):
        return "ready replica count over the run"
    return ""


# Glossary: the parameter/term definitions distilled from design-doc §2.6/§3.
GLOSSARY = [
    ("range vs interval",
     "A <b>range</b> is a lookback span (how far back a windowed average reaches, "
     "PromQL <code>metric[5m]</code>); an <b>interval</b> is a cadence (how often "
     "something recomputes/samples). Independent: average over 60s, decide every 15s."),
    ("the three meanings of “rate”",
     "<b>service_rate</b> = tokens/s one in-service request advances at (a backend "
     "property, fixed). <b>DR</b> (demand rate) = arrival_rate × E[size], tokens/s — "
     "a demand ESTIMATE, not a measurement. <b>measured throughput</b> = observed "
     "arrival/departure counts per second. Three different quantities the word "
     "“rate” gets loosely attached to; only measured throughput is one you actually "
     "observe directly."),
    ("DR — demand rate (was OWR)",
     "DR(t) = arrival_rate(t) × E[size], in <b>tokens/s</b> — the offered <i>work</i> "
     "rate, not requests/s (each request's work/size varies, so demand is measured in "
     "tokens). An <b>estimate</b>, not a measurement: arrival count is observable but a "
     "request's work (size) is not known at arrival. Valid as a proxy only under the "
     "<b>stationary-shape assumption</b> — arrival rate varies over time, the size "
     "distribution does not. (Named <code>owr</code> in the code / trace files.)"),
    ("C / sat_frac / usable ceiling",
     "<b>C</b> = raw per-backend concurrency limit (100 here). <b>sat_frac</b> = "
     "usable fraction (0.7); a backend saturates at the <b>usable ceiling</b> "
     "⌊sat_frac·C⌋ = 70 concurrent, a flat stand-in for the way real serving "
     "(vLLM) stops gaining goodput as concurrency climbs. Usable per-backend "
     "throughput = ⌊sat_frac·C⌋ × service_rate."),
    ("headroom",
     "Scale-up utilization target. headroom=1.2 sizes for ~1/1.2 ≈ 83% utilization, "
     "leaving slack for noise."),
    ("sizing_range / decision_interval / drain_time",
     "<b>sizing_range</b> (60s) = the lookback the sizer averages DR over. "
     "<b>decision_interval</b> (15s) = how often it recomputes the desired count. "
     "<b>drain_time</b> (30s, queue-aware only) = the deadline over which the "
     "backlog term aims to clear the current queue."),
    ("setup / drain",
     "<b>setup</b> = boot lag, start→up (dead time; 90s for the lagged scenarios). "
     "<b>drain</b> = drain time, stop→down."),
    ("foresight — seeing future arrivals (axis 1)",
     "Whether a sizer can see arrivals that haven't happened yet. A <b>centered</b> "
     "window [t−r/2, t+r/2] averages future arrivals into the estimate; a "
     "<b>trailing</b> window [t−r, t] sees only the past. This is real foresight, "
     "and <b>only the clairvoyant ideal sizer has it</b> — no deployable controller "
     "can see the future. This is the one axis that separates the ideal from every "
     "real strategy."),
    ("setup / dead-time compensation (axis 2 — NOT foresight)",
     "Whether a sizer acts early enough to cover boot lag: it must aim at the "
     "demand it will face at t+setup and credit the replicas already booting, so it "
     "doesn't re-order the same backlog every interval (integral windup). A "
     "<b>real</b> controller does this WITHOUT foresight — by projecting the current "
     "queue/backlog trend forward, not by peeking at future arrivals. <b>Qexp</b> "
     "(the anticipatory scenario, built) is exactly this: no axis-1 foresight, only "
     "axis-2 dead-time compensation. Orthogonal to axis 1 — a sizer can have either, "
     "both, or neither."),
    ("Qexp — the anticipatory queue-aware sizer",
     "A <b>periodic control loop</b> (the <code>08-queue-aware-exp</code> scenario). "
     "Each tick it re-reads the observable state — backlog level, up capacity, and the "
     "replicas already booting with their estimated land-times — and rolls the backlog "
     "forward under that committed boot schedule. It sizes to the <b>PEAK</b> of that "
     "projected backlog (not the backlog measured now, and not its eventual residual), "
     "so it orders enough to cover the pile-up that WILL accumulate during the boot and "
     "then HOLDS through the boot instead of chasing the queue after the fact. Same "
     "backlog-drain idea as reactive queue-aware; the difference is projecting forward "
     "vs measuring now. No axis-1 foresight — it never sees future arrivals."),
    ("observability wall",
     "The real system exposes only the queue <b>LEVEL</b> (depth right now), never "
     "per-request departures or per-batch drain rates. So a sizer cannot track "
     "individual cohorts through the queue — it can only read the current level and "
     "react. Qexp respects this: it projects the CURRENT level forward and drives "
     "scale-down off the OBSERVED backlog dropping, not off a modelled departure "
     "schedule. This is what keeps it deployable rather than a paper policy."),
    ("proj_setup — the conservatism dial",
     "The boot lead the projection ASSUMES (distinct from <code>setup</code>, the boot "
     "lag the sim actually applies). Under-predict (proj_setup &lt; setup) → the loop "
     "anticipates less and drifts toward reactive; over-predict (&gt; setup) → it orders "
     "earlier and trades a little cost for a shorter tail. Crucially the loop is "
     "<b>self-correcting</b>: because it re-observes the true level every tick, it stays "
     "stable across the whole range and never DEPENDS on the assumption being right — "
     "proj_setup just tunes how conservative it is. In the sweep, <b>good% peaks at the "
     "honest value</b> (proj_setup = setup) while tail p90 keeps improving as you "
     "over-predict — so it is a promptness-vs-tail-vs-cost knob, not a correctness knob."),
    ("quality bands",
     "Requests are scored by ABSOLUTE pre-service wait (not slowdown ratio): "
     "good ≤2s / almost ≤15s / mediocre ≤30s / meh ≤45s / bad ≤60s / failed >60s "
     "(good and failed pinned; the 2–60s middle is an even ramp). "
     "Percentages use the OFFERED denominator so bands + unfinished% sum to 100. "
     "The Table's <b>“≤Ns %” rows</b> and the <b>wait-CDF</b> figure show the same "
     "data <b>cumulatively</b> (share served <i>within</i> each bound, so each row "
     "climbs toward 100%); the stacked panel-1a figure shows the <b>exclusive</b> "
     "per-band shares. failed% = 100 − (≤60s %) − unfinished%."),
    ("goodput",
     "Throughput that actually meets the latency bar. Real serving throughput can "
     "keep rising while goodput collapses past a concurrency knee — which is why "
     "sat_frac caps the USABLE ceiling below raw C."),
    ("HPA/KEDA AverageValue formula",
     "The <code>04/05/06-hpa-*</code> scenarios are the well-lit KEDA path. Each "
     "trigger uses <b>metricType: AverageValue</b> (a per-replica target), so "
     "<code>desired = ceil(total_metric / per_replica_target)</code> and the current "
     "replica count <b>cancels out</b> — the sizer is stateless in n. Queue-depth "
     "target 1 → <code>ceil(Q)</code>; running-count target c → <code>ceil(R/c)</code>. "
     "These are <b>closed-loop</b>: they read the ACTUAL simulated queue/running "
     "signal, trailing-averaged over a 60s window (<code>avg_over_time</code>), decided "
     "every 15s — no foresight, purely reactive. Empty signal → <b>hold</b> at current n "
     "(cold start → 1); clamped to <b>[minReplicaCount, maxReplicaCount]</b> = [1, 10]."),
    ("KEDA multi-trigger combine (max)",
     "With multiple triggers KEDA takes the <b>max</b> of each trigger's desired count: "
     "scale <b>up on either</b>, <b>down only when both</b> agree lower. This is native "
     "behaviour, not custom logic — the <code>06-hpa-combined</code> scenario is exactly "
     "<code>max(ceil(Q), ceil(R/c))</code>. It is why the well-lit path pairs a "
     "saturation/queue trigger with a running-count trigger: the queue trigger covers "
     "the running-count signal's capacity-capped blind spot (see 05)."),
]


# --------------------------------------------------------------------------
# Shared narrative prose — the ONE source for the handcrafted framing text.
# Rendered into BOTH the HTML report (header + Table view) and REPORT.md so the
# two never drift. Written in light markdown (**bold**, `code`); _md_inline()
# converts to HTML, REPORT.md consumes it verbatim. Edit here → re-run report.py.
# --------------------------------------------------------------------------
INTRO = (
    "One request trace, several sizing approaches. **Every figure is the actual "
    "simulated execution** — a scaling *policy* only changes the supply trace; the "
    "graphs always reflect what really happened. Calibration is anchored to a real "
    "WVA decode-heavy benchmark: peak ~24 req/s, ~1000-token mean work, per-backend "
    "concurrency `C=100`, `service_rate ≈ 83` tokens/s (one backend clears ~8.3 "
    "req/s), usable ceiling `⌊0.7·C⌋ = 70` concurrent, and a **90 s replica boot** "
    "for the lagged scenarios."
)
STORY_NOTE = (
    "**Every scenario completes 100% of requests.** The story is *not* completion — "
    "it is the **waiting-time quality mix** (how prompt service was) and the **cost** "
    "(`replica·seconds` of fleet-time). A policy can \"finish everything\" and still "
    "be terrible, or be perfectly prompt and burn 3× the fleet."
)
READINGS = (
    "Readings: the **ideal** clairvoyant sizer is the only one that sees future "
    "arrivals — 100% prompt at the lowest real cost, the reference everything else is "
    "measured against. **No scaling** is also 100% prompt but pins at the max and "
    "burns ~3× the ideal fleet at the lowest utilisation — promptness bought by paying "
    "for peak through every valley. **Setup-lag → queue-aware → Qexp** is the "
    "deployable-sizer progression under 90s boot: a correct policy landing 90s late is "
    "only ~20% prompt; a reactive backlog term lifts that to ~28% but worsens the tail "
    "(it chases the queue after the pile-up); **Qexp** — the anticipatory periodic loop "
    "that sizes to the projected backlog peak — reaches ~35% prompt with a shorter tail "
    "(p90 43s vs 51s) and a lower queue peak, at the SAME fleet cost. **hpa-queue** and "
    "**hpa-combined** are prompt (~93% good) at ~2.5× the ideal fleet. "
    "**hpa-concurrency** is catastrophic — 88% wait over a minute — because its signal "
    "is capacity-capped and blind to the queue. **hpa-combined = hpa-queue**: the queue "
    "trigger dominates the KEDA `max`, rescuing concurrency's blind spot."
)
# Compact "story in one table" row subset (exact labels as they appear in
# summary.md). The quality rows are now the CUMULATIVE "served within Ns" CDF
# points (≤2s prompt … ≤60s within-a-minute); rows absent from summary.md are
# skipped. failed% is not a row anymore (= 100 − ≤60s − unfinished) but the
# ≤60s row and unfinished carry the same information.
STORY_ROWS = [
    "≤2s %", "≤15s %", "≤45s %", "≤60s %", "unfinished",
    "wait avg (s)", "wait p95 (s)", "replicas max", "replica·seconds",
    "provisioned·seconds", "utilization",
]


def parse_md_table(path):
    """Parse a GitHub-style pipe table into (headers, rows). Skips the --- rule."""
    if not os.path.exists(path):
        return [], []
    rows = []
    for line in open(path):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):   # separator rule
            continue
        rows.append(cells)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def section_of(label: str) -> str:
    """Group summary rows into labelled sections for the Table view."""
    if label in {"offered", "completed", "completed %", "unfinished"}:
        return "Volume & completion"
    if label.startswith("≤") or label.startswith("failed"):
        return "Waiting-time quality mix — cumulative % of offered served within"
    if label.startswith("wait "):
        return "Waiting time before service (s)"
    if label.startswith("time/work "):
        return "Time per work unit (s/unit) — informational, not scored"
    if (label.startswith("replicas ")
            or label in {"replica·seconds", "provisioned·seconds",
                         "boot-lag waste·s", "utilization"}):
        return "Fleet & cost"
    return ""


# cell shading — semi-transparent so the number stays legible on any theme.
_C_GOOD = "background:rgba(22,163,74,0.15)"     # green
_C_MEH = "background:rgba(245,158,11,0.16)"     # amber
_C_BAD = "background:rgba(239,68,68,0.15)"      # red


def _direction(label: str):
    """+1 = higher is better, −1 = lower is better, None = don't shade."""
    l = label.strip().lower()
    if l.startswith("≤"):                       # cumulative "served within Ns" — higher better
        return +1
    if l.startswith("failed"):                  # slow tail (>last edge) — lower better
        return -1
    if l.startswith(("wait ", "time/work ")):
        return -1
    if (l.startswith("replicas ")
            or l in {"unfinished", "replica·seconds", "provisioned·seconds",
                     "boot-lag waste·s"}):
        return -1
    if l in {"completed %", "completed"}:
        return +1
    return None                                 # offered, utilization, etc. — neutral


def _num(cell: str):
    try:
        return float(str(cell).replace(",", "").strip())
    except ValueError:
        return None


def _row_cell_styles(label, cells):
    """Direction-aware green/amber/red for one row's scenario cells. Best value
    → green, worst → red, linearly graded between; all-equal rows stay neutral."""
    d = _direction(label)
    vals = [_num(c) for c in cells]
    nums = [v for v in vals if v is not None]
    if d is None or len(nums) < 2 or max(nums) == min(nums):
        return ["" for _ in cells]
    lo, hi = min(nums), max(nums)
    out = []
    for v in vals:
        if v is None:
            out.append("")
            continue
        frac = (v - lo) / (hi - lo)             # 0..1
        score = frac if d > 0 else (1.0 - frac)  # 1 = best
        out.append(_C_GOOD if score >= 0.66 else
                   (_C_MEH if score >= 0.33 else _C_BAD))
    return out


def render_table_html(headers, rows):
    if not headers:
        return "<p>(no summary.md found — run run.py first)</p>"
    ncol = len(headers) + 1
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    th += '<th class="mean">what it means</th>'
    body = []
    cur = None
    for r in rows:
        sec = section_of(r[0])
        if sec and sec != cur:
            body.append(f'<tr class="sec"><td colspan="{ncol}">{esc(sec)}</td></tr>')
            cur = sec
        styles = _row_cell_styles(r[0], r[1:])
        tds = f"<td>{esc(r[0])}</td>"
        for c, st in zip(r[1:], styles):
            style = f' style="{st}"' if st else ""
            tds += f"<td{style}>{esc(c)}</td>"
        tds += f'<td class="mean">{esc(row_meaning(r[0]))}</td>'
        body.append(f"<tr>{tds}</tr>")
    return (f'<table class="sum"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def render_glossary_html():
    items = "".join(
        f"<dt>{term}</dt><dd>{definition}</dd>" for term, definition in GLOSSARY)
    return f'<dl class="gloss">{items}</dl>'


# ---- shared-prose converters (light markdown <-> html, both directions) ----
def _md_inline(s: str) -> str:
    """Render the light-markdown narrative constants (**bold**, `code`, *em*) to
    HTML. Text is otherwise trusted (our own constants), so no escaping."""
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", s)
    return s


def _html_to_md(s: str) -> str:
    """Render the HTML-authored GLOSSARY definitions down to markdown inline."""
    s = re.sub(r"</?b>", "**", s)
    s = re.sub(r"</?i>", "*", s)
    s = re.sub(r"<code>(.*?)</code>", r"`\1`", s)
    return s


def _md_table(headers, rows) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _subset(rows, labels):
    """Rows whose first cell is in `labels`, in `labels` order; missing skipped."""
    by = {r[0]: r for r in rows}
    return [by[l] for l in labels if l in by]


# Sweep heading (substring) → the line-plot PNG sweep.py renders for it. The
# figure is embedded right under its ### heading, above the numeric table.
SWEEP_FIGS = {
    "setup (boot lag) sweep": "11-sweep-setuplag.png",
    "drain_time aggression": "12-sweep-drain.png",
    "proj_setup dial": "13-sweep-qexp.png",
}


def render_sweeps_html(out_dir=OUT) -> str:
    """Parse out/sweep.md (### headings, prose paragraphs, pipe tables) into HTML
    for the Sweeps tab, embedding each sweep's line-plot PNG under its heading.
    Guarded: if sweep.py hasn't run, show a hint. The `*` baseline marker and
    shaded best/worst cells mirror the Table view."""
    path = os.path.join(out_dir, "sweep.md")
    if not os.path.exists(path):
        return ('<p class="tnote">(no <code>sweep.md</code> found — run '
                '<code>python sweep.py</code> first)</p>')
    # Block-parse: a line-buffer state machine over headings / tables / prose.
    lines = open(path).read().splitlines()
    html, i, n = [], 0, len(lines)
    intro_done = False
    while i < n:
        line = lines[i].rstrip()
        if line.startswith("# "):                       # top title → intro note
            i += 1
            continue
        if line.startswith("### "):
            heading = line[4:]
            html.append(f"<h3 class='sw'>{esc(heading)}</h3>")
            fig = next((v for k, v in SWEEP_FIGS.items() if k in heading), None)
            if fig and os.path.exists(os.path.join(out_dir, fig)):
                html.append(f'<figure class="swfig"><img src="{fig}" alt="{esc(heading)}">'
                            f'</figure>')
            i += 1
            continue
        if line.startswith("|"):                         # a pipe table block
            tbl = []
            while i < n and lines[i].lstrip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            html.append(_sweep_table_html(tbl))
            continue
        if line.strip():                                 # prose paragraph
            cls = "tnote" if not intro_done else "sw-note"
            intro_done = True
            html.append(f'<p class="{cls}">{_md_inline(line.strip())}</p>')
        i += 1
    return "".join(html)


def _sweep_table_html(tbl_lines) -> str:
    """Render one parsed sweep pipe-table (list of raw '| … |' lines) to HTML,
    shading the metric columns best→green/worst→red like the Table view. Param
    columns (leading non-metric cells) are left neutral; the `*` baseline row is
    highlighted."""
    rows = []
    for ln in tbl_lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):     # separator rule
            continue
        rows.append(cells)
    if not rows:
        return ""
    headers, body = rows[0], rows[1:]
    # Metric columns are the trailing ones sweep.py emits (good%, failed%, …);
    # everything before the first of those is a swept parameter. Detect by name.
    metric_names = {"good%", "failed%", "wait_p90", "rep_max", "rep·s",
                    "prov·s", "util"}
    first_metric = next((j for j, h in enumerate(headers) if h in metric_names),
                        len(headers))

    def col_dir(h):
        return +1 if h == "good%" else -1               # all others: lower better

    # Per-metric-column best/worst shading (column-wise, unlike the row-wise Table).
    col_styles = {}
    for j in range(first_metric, len(headers)):
        nums = [_num(r[j]) for r in body]
        vals = [v for v in nums if v is not None]
        if len(vals) < 2 or max(vals) == min(vals):
            continue
        lo, hi, d = min(vals), max(vals), col_dir(headers[j])
        col_styles[j] = []
        for v in nums:
            if v is None:
                col_styles[j].append("")
                continue
            frac = (v - lo) / (hi - lo)
            score = frac if d > 0 else (1.0 - frac)
            col_styles[j].append(_C_GOOD if score >= 0.66 else
                                 (_C_MEH if score >= 0.33 else _C_BAD))
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    out = [f'<table class="sum"><thead><tr>{th}</tr></thead><tbody>']
    for ri, r in enumerate(body):
        star = any("*" in c for c in r[:first_metric])   # baseline row marker
        tr = ' class="base"' if star else ""
        tds = ""
        for j, c in enumerate(r):
            st = col_styles.get(j, [""] * len(body))[ri] if j >= first_metric else ""
            style = f' style="{st}"' if st else ""
            tds += f"<td{style}>{esc(c)}</td>"
        out.append(f"<tr{tr}>{tds}</tr>")
    out.append("</tbody></table>")
    return "".join(out)


# Cross-policy tradeoff figures for the Tradeoffs tab: (caption-title, png, note).
# Rendered by run.py (render_wait_cdf / render_cost_quality).
TRADEOFF_FIGS = [
    ("Waiting-time CDF — all policies on one axis", "09-wait-cdf.png",
     "Each curve is a policy's <b>wait CDF over the OFFERED denominator</b>: height "
     "at time <i>t</i> = share of all arrivals served within <i>t</i> s. Curves that "
     "asymptote <b>below 100%</b> stranded work (unfinished). Read left-to-right: the "
     "further up-and-left, the prompter. Legend carries each policy's billed "
     "fleet-cost, so promptness and cost read together. This is the same data as the "
     "Table's “≤Ns %” rows, shown continuously."),
    ("Cost vs quality — the Pareto frontier", "10-cost-quality.png",
     "x = billed fleet-time (provisioned·seconds, the cost); y = promptness (% of "
     "offered served within 15s). The dashed line is the frontier over the "
     "<b>deployable</b> policies — anything below-and-right of it is dominated "
     "(something is both cheaper AND prompter). <b>ideal</b> is drawn apart as the "
     "clairvoyant reference (not deployable). This is where “same cost, better "
     "quality” becomes literal: Qexp sits on the frontier, queue-aware just inside it "
     "at ~the same cost."),
]


def render_tradeoffs_html(out_dir=OUT) -> str:
    """Embed the cross-policy CDF-overlay and cost-quality figures for the
    Tradeoffs tab. Guarded per-figure: a missing PNG (run.py not run) is skipped
    with a hint rather than a broken image."""
    blocks = []
    for title, png, note in TRADEOFF_FIGS:
        if not os.path.exists(os.path.join(out_dir, png)):
            blocks.append(f'<p class="tnote">(no <code>{esc(png)}</code> — run '
                          f'<code>python run.py</code> first)</p>')
            continue
        blocks.append(
            f"<h3 class='sw'>{esc(title)}</h3>"
            f'<p class="sw-note">{note}</p>'
            f'<figure class="tradefig"><img src="{png}" alt="{esc(title)}">'
            f'<a class="zoom" href="{png}" target="_blank">open full size &#8599;</a>'
            f"</figure>")
    return "".join(blocks)


def render_markdown(out_dir=OUT) -> str:
    """Generate REPORT.md programmatically from the SAME sources the HTML uses
    (summary.md + SCENARIOS + GLOSSARY + shared prose), so REPORT.md has
    identical scope to index.html — every rendered scenario, every metric row."""
    headers, rows = parse_md_table(os.path.join(out_dir, "summary.md"))
    scen = [s for s in SCENARIOS
            if os.path.exists(os.path.join(out_dir, s["png"]))]
    md = []
    md.append("# Autoscaling Behavioral Demo — comparison report\n")
    md.append(INTRO + "\n")
    md.append(
        "> This is the static, GitHub-renderable view. The interactive version\n"
        "> (tabbed compare / browse / table / glossary, with a zoom slider) lives at\n"
        "> [`out/index.html`](out/index.html) — open it locally; GitHub strips its JS/CSS.\n"
        "> Rebuild everything with `python run.py && python report.py`.\n")
    md.append(STORY_NOTE + "\n")
    md.append("---\n")
    md.append("## The story in one table\n")
    md.append("Quality rows are the **cumulative** share of offered requests served "
              "*within* each wait bound (the wait CDF sampled at 2 / 15 / 45 / 60 s); "
              "cost is fleet-time.\n")
    if headers:
        md.append(_md_table(headers, _subset(rows, STORY_ROWS)) + "\n")
    md.append(READINGS + "\n")
    md.append("<details><summary>Full metrics table (all rows)</summary>\n")
    if headers:
        md.append(_md_table(headers, rows) + "\n")
    md.append("</details>\n")
    md.append("---\n")
    # Cross-policy tradeoff figures (CDF overlay + cost-quality frontier).
    if any(os.path.exists(os.path.join(out_dir, p)) for _, p, _ in TRADEOFF_FIGS):
        md.append("## Cost & waiting-time tradeoffs\n")
        md.append("Two cross-policy views on one axis — the full waiting-time CDF and "
                  "the cost-vs-quality frontier.\n")
        for title, png, note in TRADEOFF_FIGS:
            if os.path.exists(os.path.join(out_dir, png)):
                md.append(f"**{title}.** {_html_to_md(note)}\n")
                md.append(f"![{title}]({out_dir}/{png})\n")
        md.append("---\n")
    md.append("## Scenarios\n")
    for i, s in enumerate(scen, 1):
        md.append(f"### {i} · {s['label']}\n")
        md.append(f"*{s['setup']}*\n")
        md.append(f"{s['answers']}\n")
        # REPORT.md sits one level above out/; the HTML lives inside out/ so it
        # references bare filenames. Prefix out_dir for the markdown links.
        md.append(f"![{s['key']}]({out_dir}/{s['png']})\n")
        lat = s.get("latency")
        if lat and os.path.exists(os.path.join(out_dir, lat)):
            md.append("<details><summary>latency</summary>\n")
            md.append(f"![{s['key']} latency]({out_dir}/{lat})\n")
            md.append("</details>\n")
    md.append("---\n")
    # Parameter-sweep line-plots (full numeric tables stay in out/sweep.md).
    sweep_figs = [("Setup-lag — quality collapse & cost vs boot time", "11-sweep-setuplag.png"),
                  ("Queue-aware — aggression vs quality & cost", "12-sweep-drain.png"),
                  ("Qexp — assumed boot lead vs quality & cost", "13-sweep-qexp.png")]
    if any(os.path.exists(os.path.join(out_dir, p)) for _, p in sweep_figs):
        md.append("## Parameter sweeps\n")
        md.append("Trend + calibration line-plots (full numeric tables in "
                  f"[`{out_dir}/sweep.md`]({out_dir}/sweep.md)). Solid = good %, "
                  "dashed = wait p90, dotted vertical = baseline.\n")
        for title, png in sweep_figs:
            if os.path.exists(os.path.join(out_dir, png)):
                md.append(f"![{title}]({out_dir}/{png})\n")
        md.append("---\n")
    md.append("## Glossary\n")
    for term, definition in GLOSSARY:
        md.append(f"**{term}.** {_html_to_md(definition)}\n")
    return "\n".join(md)


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autoscaling Behavioral Demo — Report</title>
<style>
:root{--fg:#1f2937;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--sel:#dbeafe;--bg:#fff;}
*{box-sizing:border-box;}
body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--fg);background:var(--bg);}
header{padding:18px 24px;border-bottom:1px solid var(--line);}
header h1{margin:0 0 4px;font-size:19px;}
header p{margin:0 0 6px;color:var(--muted);font-size:13px;max-width:1000px;}
header p:last-child{margin-bottom:0;}
header p b{color:var(--fg);}
.tnote{max-width:1000px;margin:0 0 16px;color:#374151;font-size:13.5px;line-height:1.55;}
.tnote b{color:var(--fg);}
.tnote code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12.5px;}
.tabs{display:flex;gap:6px;padding:12px 24px 0;border-bottom:1px solid var(--line);}
.tab{padding:8px 16px;border:1px solid var(--line);border-bottom:none;border-radius:8px 8px 0 0;background:#f9fafb;cursor:pointer;font-weight:600;font-size:13px;}
.tab.active{background:var(--bg);color:var(--accent);}
main{padding:20px 24px 60px;}
.view{display:none;}.view.active{display:block;}
.pick{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;}
.pick button{padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:#f9fafb;cursor:pointer;font-size:13px;}
.pick button.sel{background:var(--sel);border-color:var(--accent);color:var(--accent);font-weight:600;}
/* Compare: two half-width panes side by side, each its own scroll box; JS keeps
   their scroll positions in lockstep so the shared time axis stays aligned. */
.cmp{display:flex;gap:18px;align-items:flex-start;}
.pane{flex:1 1 0;min-width:0;}
/* grow to the full figure height (no vertical scrollbar); only scroll
   horizontally when zoomed past fit. overflow-y:hidden with height:auto means
   the box just expands to the image height. */
.scroll{overflow-x:auto;overflow-y:hidden;border:1px solid var(--line);border-radius:6px;background:#fff;}
.meta{font-size:12px;color:var(--muted);margin:2px 0 8px;min-height:48px;}
.meta b{color:var(--fg);}
figure{margin:0;}
figure img{height:auto;display:block;background:#fff;}
/* slider row */
.controls{display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;color:var(--muted);}
.controls input[type=range]{width:260px;}
.controls .lbl{font-weight:600;color:var(--fg);}
.hint{font-size:12px;color:var(--muted);margin:14px 0 6px;}
.zoom{font-size:12px;color:var(--accent);text-decoration:none;display:inline-block;margin-top:6px;}
table.sum{border-collapse:collapse;font-size:13px;}
table.sum th,table.sum td{border:1px solid var(--line);padding:5px 12px;text-align:right;}
table.sum th:first-child,table.sum td:first-child{text-align:left;}
table.sum th.mean,table.sum td.mean{text-align:left;color:var(--muted);font-size:12px;max-width:360px;white-space:normal;}
table.sum thead th{background:#f3f4f6;position:sticky;top:0;z-index:3;}
table.sum tr.sec td{background:#eef2ff;color:#3730a3;font-weight:700;text-align:left;border-top:2px solid #c7d2fe;}
dl.gloss{max-width:900px;}
dl.gloss dt{font-weight:700;margin:16px 0 3px;color:var(--fg);}
dl.gloss dd{margin:0;color:#374151;font-size:14px;}
dl.gloss code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12.5px;}
h3.sw{margin:26px 0 6px;font-size:15px;color:#3730a3;}
p.sw-note{max-width:1000px;margin:0 0 10px;color:#374151;font-size:13px;line-height:1.5;}
p.sw-note code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12px;}
table.sum tr.base td{font-weight:700;}
#view-sweeps table.sum{margin-bottom:8px;}
/* cross-policy tradeoff + sweep line-plot figures: cap to pane width, keep aspect */
figure.tradefig{margin:0 0 26px;max-width:1100px;}
figure.swfig{margin:2px 0 16px;max-width:1100px;}
figure.tradefig img,figure.swfig img{max-width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:6px;background:#fff;}
</style>
</head>
<body>
<header>
  <h1>Autoscaling Behavioral Demo — comparison report</h1>
  <p>__INTRO__</p>
  <p>__STORY__</p>
</header>
<div class="tabs">
  <div class="tab active" data-tab="compare">Compare</div>
  <div class="tab" data-tab="browse">Browse</div>
  <div class="tab" data-tab="table">Table</div>
  <div class="tab" data-tab="tradeoffs">Tradeoffs</div>
  <div class="tab" data-tab="sweeps">Sweeps</div>
  <div class="tab" data-tab="glossary">Glossary</div>
</div>
<main>
  <section class="view active" id="view-compare">
    <div class="controls">
      <span class="lbl">Zoom</span>
      <span>fit</span>
      <input type="range" id="zoomer" min="0" max="100" value="0">
      <span>full detail</span>
      <span id="zoomval"></span>
    </div>
    <div class="cmp">
      <div class="pane">
        <div class="pick" data-side="L"></div>
        <div class="meta" id="meta-L"></div>
        <div class="scroll" id="scroll-L"><figure><img id="img-L"></figure></div>
        <a class="zoom" id="zoom-L" target="_blank">open full size &#8599;</a>
      </div>
      <div class="pane">
        <div class="pick" data-side="R"></div>
        <div class="meta" id="meta-R"></div>
        <div class="scroll" id="scroll-R"><figure><img id="img-R"></figure></div>
        <a class="zoom" id="zoom-R" target="_blank">open full size &#8599;</a>
      </div>
    </div>
  </section>
  <section class="view" id="view-browse">
    <div class="pick" data-side="B"></div>
    <div class="meta" id="meta-B"></div>
    <div class="scroll"><figure><img id="img-B"></figure></div>
    <a class="zoom" id="zoom-B" target="_blank">open full size &#8599;</a>
    <p class="hint">latency — per-request time in system (coloured by request size):</p>
    <div class="scroll"><figure><img id="img-Blat"></figure></div>
  </section>
  <section class="view" id="view-table">
    <p class="tnote">__READINGS__</p>
    __TABLE__
  </section>
  <section class="view" id="view-tradeoffs">
    <p class="tnote">Cross-policy tradeoffs — the two views that put every policy on
    <b>one shared axis</b>: the full waiting-time <b>CDF</b> (how prompt), and the
    <b>cost&nbsp;vs&nbsp;quality</b> frontier (what the promptness costs). Unlike the
    per-scenario figures under Browse, these compare policies directly.</p>
    __TRADEOFFS__
  </section>
  <section class="view" id="view-sweeps">
    <p class="tnote">Parameter sweeps — trend + calibration figures and tables (not the
    seven canonical scenario figures). Each point re-runs the sim across a knob grid;
    a point at the baseline knobs reproduces the matching scenario's summary row. In
    the plots, <b>solid</b> = good&nbsp;% (left axis), <b>dashed</b> = wait&nbsp;p90
    (right axis), and the dotted vertical is the baseline. In the tables <b>*</b> marks
    the canonical baseline; metric cells are shaded best&rarr;green / worst&rarr;red
    down each column.</p>
    __SWEEPS__
  </section>
  <section class="view" id="view-glossary">
    __GLOSSARY__
  </section>
</main>
<script>
const SCEN = __SCEN__;
const FULL_W = __FULLW__;
const DEFAULTS = {L:"setup-lag", R:"queue-aware", B:"ideal"};
const state = Object.assign({}, DEFAULTS);
const byKey = k => SCEN.find(s => s.key === k) || SCEN[0];
function fillMeta(el, s){ el.innerHTML = "<b>"+s.label+"</b> &mdash; "+s.setup+"<br>answers: "+s.answers; }
function renderSide(side){
  const s = byKey(state[side]);
  const img = document.getElementById("img-"+side);
  img.src = s.png; img.alt = s.label;
  const zoom = document.getElementById("zoom-"+side);
  if (zoom) zoom.href = s.png;
  const meta = document.getElementById("meta-"+side);
  if (meta) fillMeta(meta, s);
  if (side === "B") document.getElementById("img-Blat").src = s.latency || "";
  document.querySelectorAll('.pick[data-side="'+side+'"] button').forEach(b => {
    b.classList.toggle("sel", b.dataset.key === state[side]);
  });
  applyZoom();
}
function buildPickers(){
  document.querySelectorAll('.pick').forEach(p => {
    const side = p.dataset.side;
    SCEN.forEach(s => {
      const b = document.createElement("button");
      b.textContent = s.label; b.dataset.key = s.key;
      b.onclick = () => { state[side] = s.key; renderSide(side); };
      p.appendChild(b);
    });
  });
}
// Compare-pane zoom: interpolate each pane image width between "fit to pane"
// (frac 0 => 100%, no horizontal scroll) and natural full detail (frac 1 => FULL_W).
function applyZoom(){
  const frac = (+document.getElementById("zoomer").value) / 100;
  document.getElementById("zoomval").textContent =
      frac === 0 ? "(fit)" : Math.round(100 + frac*(FULL_W/ (paneW()||FULL_W) *100 -100)) + "%";
  ["L","R"].forEach(side => {
    const img = document.getElementById("img-"+side);
    const pane = img.closest(".scroll").clientWidth - 2;   // minus border
    const w = pane + frac * (FULL_W - pane);
    img.style.width = Math.max(pane, w) + "px";
  });
}
function paneW(){
  const s = document.getElementById("scroll-L");
  return s ? s.clientWidth - 2 : 0;
}
// Synchronized HORIZONTAL scroll only: the panes have no vertical scrollbar
// (they grow to full figure height), so mirror scrollLeft to keep the shared
// time axis aligned when zoomed in.
function initSync(){
  const L = document.getElementById("scroll-L");
  const R = document.getElementById("scroll-R");
  let lock = false;
  function mirror(from, to){
    if (lock) return; lock = true;
    to.scrollLeft = from.scrollLeft;
    lock = false;
  }
  L.addEventListener("scroll", () => mirror(L, R));
  R.addEventListener("scroll", () => mirror(R, L));
}
function initTabs(){
  document.querySelectorAll('.tab').forEach(t => {
    t.onclick = () => {
      document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
      document.querySelectorAll('.view').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      document.getElementById('view-'+t.dataset.tab).classList.add('active');
      if (t.dataset.tab === "compare") applyZoom();
    };
  });
}
buildPickers(); initTabs(); initSync();
document.getElementById("zoomer").addEventListener("input", applyZoom);
window.addEventListener("resize", applyZoom);
["L","R","B"].forEach(renderSide);
</script>
</body>
</html>
"""


def build(out_dir=OUT, out_html=None, md_path="REPORT.md"):
    out_html = out_html or os.path.join(out_dir, "index.html")
    scen = [s for s in SCENARIOS
            if os.path.exists(os.path.join(out_dir, s["png"]))]
    headers, rows = parse_md_table(os.path.join(out_dir, "summary.md"))
    html = (TEMPLATE
            .replace("__SCEN__", json.dumps(scen))
            .replace("__FULLW__", str(FULL_W))
            .replace("__INTRO__", _md_inline(INTRO))
            .replace("__STORY__", _md_inline(STORY_NOTE))
            .replace("__READINGS__", _md_inline(READINGS))
            .replace("__TABLE__", render_table_html(headers, rows))
            .replace("__TRADEOFFS__", render_tradeoffs_html(out_dir))
            .replace("__SWEEPS__", render_sweeps_html(out_dir))
            .replace("__GLOSSARY__", render_glossary_html()))
    with open(out_html, "w") as f:
        f.write(html)
    print(f"[wrote {out_html}]  scenarios={[s['key'] for s in scen]}  "
          f"table_rows={len(rows)}")
    # REPORT.md is generated from the same sources → identical scope, no drift.
    with open(md_path, "w") as f:
        f.write(render_markdown(out_dir))
    print(f"[wrote {md_path}]  scenarios={len(scen)}")
    return out_html


if __name__ == "__main__":
    build()
