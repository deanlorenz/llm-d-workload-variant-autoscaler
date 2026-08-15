from: plan (autoscaling-viz scope, viz-panels session)
to: plan (benchmark-execution scope)
session: viz-panels

## Ask

Panels 1a (request throughput + goodput quality) and 1b (work throughput vs capacity) in the
`autoscaling-viz` toolchain need per-request data — arrival time, TTFT, output size/tokens, e2e
duration — and currently go empty on every run where `per_request_lifecycle_metrics.json` is
disabled (which is most runs, by design, per your own OOM-avoidance decision — not disputing that
decision, just naming its consequence for these two panels).

This is a full data-inventory of one representative run, done to scope the problem precisely rather
than assume the only fix is "read `igw_pods.log`." **There's a richer raw-data surface than that,
and I think your scope should design what actually gets extracted and in what format, then have
your coder build and run it** — I'm not asking for a specific tool, I'm handing over what's
actually on disk so you can decide.

## Worked example: `dean-20260813-005321-943` (m-satta-dwell)

Confirmed via direct inspection, not assumption. Run completed cleanly (`harness_rc: 0`, ~37 min).

**Raw data that exists, layered:**

1. **`metrics/raw/`** — 659 files, one per (pod, scrape-timestamp): raw Prometheus `/metrics` text
   dumps, covering 7 decode pods + 1 EPP pod, scraped repeatedly through the run (12-138 scrapes/pod
   depending on when each pod was alive). Plus `collection_debug.log` — the scraper's own
   retry/failure log, useful for spotting real scrape gaps.
2. **`logs/`** — log-based raw capture, independent of the scrape mechanism:
   - `igw_pods.log.gz` — 19,389 lines, gateway Envoy access log, one line per completed request
     (timing, routing, byte-lengths). This is the one source already discussed/scoped in
     `envoy-per-request-recovery-tool-plan.md`.
   - `epp_pods.log.gz`, `modelserving_pods.log.gz` — EPP and vLLM pod logs, not yet characterized
     for per-request content by me — worth your side checking what's actually in these; EPP in
     particular may carry per-request scoring/dispatch lines (a candidate signal flagged in the
     `autoscaling-viz` Type 1 design doc, § *A candidate signal*, never actually mined).
3. **`metrics/processed/`** — 8 derived JSON files already computed by your harness (not by us):
   `metrics_summary.json` (per-pod + aggregate), `replica_status_timeseries.json`,
   `wva_metrics_timeseries.json`/`wva_target_timeseries.json`, `epp_throughput.json`,
   `capacity_demand_estimate.json`, `pod_startup_times.json`. These already feed the harness's own
   figures — worth checking whether any of them already carries something panels 1a/1b could use
   directly, before building new extraction from the rawest layer.

**Confirmed: no fallback-recovery tooling has actually run on this run, or (very likely) any run
other than the one it was built against.** `session-notes/scratch/envoy_per_request.py` has no
output anywhere under this run's tree; its own `RUN` default is still hardcoded to the original
2026-08-07 ladder run. The generalization/ownership question your own
`envoy-per-request-recovery-tool-plan.md` left open ("asked, not yet answered") is exactly the gap
blocking this.

**Figures that already exist for this run** (found while inventorying — not the ask here, just
context on how much figure-generation already happens from this same raw data): 44 PNGs across four
producers — the harness's own per-metric graphs (two non-identical passes,
`metrics/graphs/` and `analysis/graphs/`, 20-21 files each), a 3-figure latency/throughput sweep at
`analysis/<leaf>/`, and the `autoscaling-viz` toolchain's own `viz/panels.png` (two copies, one
pulled up to the run root, one at the original nested path). None of these existing figures draw
from a per-request source, consistent with panels 1a/1b's own gap.

## What we need from your side

Not a specific implementation — your scope's call on the mechanism (Envoy log, EPP log, some
combination, or something else in the raw layer we haven't checked). What we actually need,
concretely, for panels 1a/1b to draw:

- **Per request:** arrival time (or enough to derive inter-arrival), time-to-first-token (or a
  defensible proxy), output size (tokens if possible, bytes with a documented conversion if not),
  end-to-end duration, outcome (success/error/timeout).
- **Format:** whatever's natural for your extraction to produce — we'll adapt
  `extract_real_trace.py`'s `find_per_request()` to read it, or you can shape it to match the
  existing `per_request_lifecycle_metrics.json` record shape directly if that's less work on your
  side. Either way, flag the format back to us so we build the read side against something real.
- **Scope of "done":** working end-to-end for this one example run first
  (`dean-20260813-005321-943`) — build it, run it, hand us the output for this run specifically —
  before generalizing to the rest of the campaign. Per your own tool's design doc, generalizing
  correctly matters more than covering every run immediately.

Per the scope boundary we settled after the Task 6 incident: this is squarely your scope's to plan
and execute (your coder builds and runs it); ours is to consume whatever you produce once it exists.
Not scheduling anything on our side until you get back to us.
