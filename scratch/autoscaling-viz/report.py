"""Build a self-contained comparison report (out/index.html) from the rendered
figures + summary table. Read-only over the sim: it just references the PNGs
already in out/ and parses out/summary.md.

Run:  ./.venv/bin/python report.py     (after run.py has produced the figures)

No server needed — open out/index.html directly (file://). Pure vanilla HTML/CSS/JS.
"""

import json
import os

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
     "setup": "setup=0 · size to CENTERED offered-work-rate × headroom (clairvoyant)",
     "answers": "what does good look like? → 100% served ≤2s; never queues on a smooth bump"},
    {"key": "setup-lag", "label": "Setup lag",
     "png": "02-setup-lag.png", "latency": "02-setup-lag-latency.png",
     "setup": "setup=90 · the SAME demand-tracking commands as ideal, landing 90s late",
     "answers": "does a correct policy survive 90s boot lag? → still completes 100%, but only ~20% served promptly. "
                "⚠ confound: setup-lag→queue-aware changes TWO things at once (foresight lost, centered→trailing window, "
                "AND a backlog-drain term added) — not a clean A/B on the backlog term alone"},
    {"key": "queue-aware", "label": "Queue-aware",
     "png": "03-queue-aware.png", "latency": "03-queue-aware-latency.png",
     "setup": "setup=90, drain_time=30 · demand-tracking + backlog-drain (reactive, TRAILING)",
     "answers": "can a reactive backlog term rescue quality? → only modestly (~28% prompt), and it worsens the tail"},
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
    "offered": "every request that arrived — the denominator (guards against survivorship bias)",
    "completed": "requests that finished within the run",
    "completed %": "completion rate — the 'did it finish at all' number",
    "unfinished": "still in system at trace end (permanently stranded)",
    "good (≤2s) %": "share of OFFERED served within 2s of arrival — the scored 'prompt' band",
    "almost (≤10s) %": "share of offered served in 2–10s",
    "bad (≤30s) %": "share of offered served in 10–30s",
    "really bad (≤60s) %": "share of offered served in 30–60s",
    "failed (>60s) %": "share of offered that waited over 60s before service (worst band)",
    "replica·seconds": "∫ ready replicas dt — a cost proxy",
}


def row_meaning(label: str) -> str:
    if label in ROW_MEANING:
        return ROW_MEANING[label]
    if label.startswith("wait "):
        return "pre-service wait (dispatch − arrival), completed requests only"
    if label.startswith("time/work "):
        return "time-in-system ÷ size (slowdown proxy; informational only, NOT the scored signal)"
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
     "property, fixed). <b>owr</b> (offered-work-rate) = arrival_rate × E[size], a "
     "demand ESTIMATE. <b>measured throughput</b> = observed arrival/departure "
     "counts per second, a measurement. Only the last keeps the bare word “rate”."),
    ("owr (offered work rate)",
     "owr(t) = arrival_rate(t) × E[size], tokens/s. An <b>estimate</b>, not a "
     "measurement: arrival count is observable but a request's work (size) is not "
     "known at arrival. Valid as a proxy only under the <b>stationary-shape "
     "assumption</b> — arrival rate varies over time, the size distribution does not."),
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
     "<b>sizing_range</b> (60s) = the lookback the sizer averages owr over. "
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
     "queue/backlog trend forward, not by peeking at future arrivals. <b>expQ</b> "
     "(anticipatory, to build) is exactly this: no axis-1 foresight, only axis-2 "
     "dead-time compensation. Orthogonal to axis 1 — a sizer can have either, "
     "both, or neither."),
    ("quality bands",
     "Requests are scored by ABSOLUTE pre-service wait (not slowdown ratio): "
     "good ≤2s / almost ≤10s / bad ≤30s / really bad ≤60s / failed >60s. "
     "Percentages use the OFFERED denominator so bands + unfinished% sum to 100."),
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
    if label.startswith(("good ", "almost ", "bad ", "really bad ", "failed ")):
        return "Waiting-time quality mix (% of offered)"
    if label.startswith("wait "):
        return "Waiting time before service (s)"
    if label.startswith("time/work "):
        return "Time per work unit (s/unit) — informational, not scored"
    if label.startswith("replicas ") or label == "replica·seconds":
        return "Fleet & cost"
    return ""


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
        tds = "".join(f"<td>{esc(c)}</td>" for c in r)
        tds += f'<td class="mean">{esc(row_meaning(r[0]))}</td>'
        body.append(f"<tr>{tds}</tr>")
    return (f'<table class="sum"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def render_glossary_html():
    items = "".join(
        f"<dt>{term}</dt><dd>{definition}</dd>" for term, definition in GLOSSARY)
    return f'<dl class="gloss">{items}</dl>'


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
header p{margin:0;color:var(--muted);font-size:13px;max-width:1000px;}
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
table.sum thead th{background:#f3f4f6;}
table.sum tr.sec td{background:#eef2ff;color:#3730a3;font-weight:700;text-align:left;border-top:2px solid #c7d2fe;}
dl.gloss{max-width:900px;}
dl.gloss dt{font-weight:700;margin:16px 0 3px;color:var(--fg);}
dl.gloss dd{margin:0;color:#374151;font-size:14px;}
dl.gloss code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12.5px;}
</style>
</head>
<body>
<header>
  <h1>Autoscaling Behavioral Demo — comparison report</h1>
  <p>One request trace, several sizing approaches. Every figure is the <b>actual
     simulated execution</b> (clairvoyant rendering — a policy only changes the
     supply trace). Compare two approaches side by side, browse one in full, read
     all approaches as one annotated table, or look up a term in the glossary.</p>
</header>
<div class="tabs">
  <div class="tab active" data-tab="compare">Compare</div>
  <div class="tab" data-tab="browse">Browse</div>
  <div class="tab" data-tab="table">Table</div>
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
    __TABLE__
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


def build(out_dir=OUT, out_html=None):
    out_html = out_html or os.path.join(out_dir, "index.html")
    scen = [s for s in SCENARIOS
            if os.path.exists(os.path.join(out_dir, s["png"]))]
    headers, rows = parse_md_table(os.path.join(out_dir, "summary.md"))
    html = (TEMPLATE
            .replace("__SCEN__", json.dumps(scen))
            .replace("__FULLW__", str(FULL_W))
            .replace("__TABLE__", render_table_html(headers, rows))
            .replace("__GLOSSARY__", render_glossary_html()))
    with open(out_html, "w") as f:
        f.write(html)
    print(f"[wrote {out_html}]  scenarios={[s['key'] for s in scen]}  "
          f"table_rows={len(rows)}")
    return out_html


if __name__ == "__main__":
    build()
