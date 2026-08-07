# autoscaling-viz — visualize a real llm-d benchmark run

Turns a benchmark run directory into a small JSON bundle and a set of panels showing
what the autoscaler actually did: offered load, served load, replicas desired vs
ready, per-pod work, queueing, and concurrency.

Two things live here:

- **the real-trace path** (`fetch_run.sh` → `extract_real_trace.py` → `render_real_trace.py`)
  — reads *your* benchmark output. This is what you want.
- **the synthetic simulator** (`sim.py`, `run.py`, `plots.py`) — a clairvoyant
  autoscaling model used to reason about scaling policy on made-up traces. Untouched
  by the real-trace path; ignore it unless you are working on the model.

## Getting it

Everything you need is this one directory — no repo layout assumptions, no config
outside it. It is a standalone branch with nothing else in it, so one clone gets you
the tools and a worked example and no unrelated repo history.

```bash
git clone -b autoscaling-viz \
  https://github.com/deanlorenz/llm-d-workload-variant-autoscaler.git autoscaling-viz
cd autoscaling-viz
```

A **worked example** ships under `real-trace/staircase-20260803/` — a real single-variant
scale-up run, carrying its `bundle.json`, `coverage.json`, `provenance.json` and a
rendered `panels.png`. So you can see what the output looks like, and re-render it, before
pointing anything at your own data or a cluster:

```bash
uv run --with matplotlib render_real_trace.py \
  --bundle real-trace/staircase-20260803/bundle.json
```

`results/` is where *published* bundles land (see **Sharing results** below). It is tracked
and carries nothing but its own `README.md` until someone publishes a run.

## Requirements

Python 3.9+ and, for rendering only, `matplotlib`. `fetch_run.sh` and
`extract_real_trace.py` are standard library only — no install step, nothing to pin.
If your data is on a cluster PVC you also need `oc` or `kubectl` with read access to
that namespace.

```bash
uv run --with matplotlib render_real_trace.py --bundle ...   # no venv to manage
```

or, if you would rather have a venv:

```bash
uv venv && uv pip install matplotlib && .venv/bin/python render_real_trace.py ...
```

## Three commands

### 1. Fetch (skip if the run is already on your disk)

```bash
# what runs are on the PVC?
./fetch_run.sh -n <namespace> -p <pod-that-mounts-the-pvc> -l

# pull one
./fetch_run.sh -n <namespace> -p <pod> -r /requests/<run-dir> -o real-trace/<label>
```

The fetch is **read-only** on the cluster: `get`, `exec ls|cat|python3`, and `cp`
*from* the pod. It never creates or modifies anything, so it is safe to point at a
shared namespace. It needs a pod that already mounts the results PVC — if there
isn't one, ask the namespace owner rather than creating one.

By default the multi-GB per-request file is **skipped** and a 50-record head sample is
cut *at the source* instead. Pass `-f` to take the whole thing. Run `./fetch_run.sh -h`
for all flags.

### 2. Extract

```bash
python3 extract_real_trace.py --run real-trace/<label> --out real-trace/<label>
```

Writes two files:

| file | what it is |
|---|---|
| `bundle.json` | everything the panels need, ~1 MB instead of the run's GBs |
| `coverage.json` | which panels and calibrations **this run** can support |

Useful flags: `--no-per-request` (skip the big file entirely — panels 2–5 still work),
`--head N` (read only the first N requests).

**Read the coverage table.** It prints on stdout and a `FAIL` row is information, not
breakage — it means this particular run does not exercise that behavior. For example
`Scale-down present  FAIL` just says nothing scaled down during the run, so there is
no drain to draw. Same for the warnings and the self-check failures at the bottom:
they tell you which conclusions the data will and will not support.

### 3. Render

```bash
python3 render_real_trace.py --bundle real-trace/<label>/bundle.json
```

## What the panels show

| panel | content |
|---|---|
| 1a | request arrival rate vs completion rate, split by how long each request waited |
| 1b | work throughput (tokens/s) against usable capacity |
| 2 | replicas desired vs ready, with boot and drain markers |
| 3 | per-backend work, stacked — shows router imbalance directly |
| 4 | global queue depth *(deferred — see below)* |
| 5 | concurrency L(t) |

Panel 4 is **not final**: there are three distinct queues in this system (EPP
flow-control, EPP dispatch, and per-vLLM `num_requests_waiting`) and they mean
different things. The extractor records all three plus a derived global queue; which
one panel 4 should draw is an open design question. Everything needed to decide is
already in `bundle.json` under `system[]`.

## What it reads, and what it needs

Auto-detected from `run_metadata.yaml: harness_name`. Both harnesses work:

| | inference-perf | guidellm |
|---|---|---|
| per-request file | `per_request_lifecycle_metrics.json` (GBs) | `results.json` (100–200 MB) |
| timestamps | monotonic — must be anchored to the scrape clock | epoch, already on the scrape clock |
| output token count | client count is inflated ~2× (streamed chunks double-counted); the server count is used | exact, via `ignore_eos` + `max_completion_tokens` |

Everything else is optional and degrades to a coverage row:

```
<run-dir>/
  run_metadata.yaml                              harness, model, namespace, timing
  metrics/raw/<pod>_<epoch>_metrics.log          REQUIRED for panels 2-5
  metrics/processed/replica_status_timeseries.json    desired/ready replicas
  metrics/processed/pod_startup_times.json            boot lag fallback
  metrics/processed/wva_target_timeseries.json        WVA decisions, if captured
  results.json | per_request_lifecycle_metrics.json   panels 1 and 4
```

`metrics/raw/` is the only time-resolved metrics source and the one thing that cannot
be substituted. `metrics/processed/metrics_summary.json` looks promising but holds
run-long aggregate statistics with no time axis, so it is not used.

The `metrics/processed/wva_*.json` files come from `hack/benchmark/post_run_analyze.sh`
in the WVA repo. If you want WVA's own decision timeseries in the bundle, **run that
script promptly after the run** — its first step reads the controller log through
`kubectl`, which rotates its buffer. Once rotated, those decisions are gone.

## Getting the most out of the next run

Two things are hard to get from existing runs, so they are worth designing in:

1. **Dwell in the mid KV band (0.3–0.85).** Fitting the concurrency-vs-latency slope
   `A` and locating the throughput knee both need time spent *below* saturation.
   Runs that jump straight to a saturating rate produce a strong `A` fit only by luck.
2. **Include a short-output shape.** The `ITL = A·k + B` relation is linear only
   between a lower knee `y` and 0.85. Decode-heavy shapes put `y` at 0; the knee only
   becomes visible when prefill dominates *in time*, which needs output/input well
   under 1 — a 1000/250 shape is still decode-dominated.

Also worth capturing: a deliberate scale-down (to measure drain vs kill), three or
more replicas (to see router oscillation), and `post_run_analyze.sh` run immediately.

## Sharing results

`bundle.json` is small enough to commit, which makes runs comparable across people and
machines without moving raw data. The layout, and the rules about what must never go
into a bundle, are in
[`real-trace-viz-plan.md`](real-trace-viz-plan.md) §15.

The extractor never copies prompt or response text into the bundle — guidellm embeds
full prompts in every record, which is both bulk and, on a real workload, potentially
sensitive.

## Where the reasoning lives

[`real-trace-viz-plan.md`](real-trace-viz-plan.md) — the derivations behind all of the
above: the time-anchor problem (§2), token accounting (§3), the three queues (§4), the
saturation threshold and ITL validity window (§5), the capacity model (§6), and the
extractor spec (§8). Start at §1.0 for what data exists and where.
