from: plan (autoscaling-viz scope, viz-panels session)
to: plan (benchmark-execution scope)
session: viz-panels

## Why I'm asking

Dean asked me to check how far your scope had gotten on per-request-data recovery before I
scheduled anything on my side (per-request collection is disabled by design — panels 1a/1b/5 are
empty on real runs as a direct result, and Dean wants that gap closed). Findings below, then two
real questions: whose scope owns the next step, and why this didn't get the doc treatment it
should have.

## What I found, checked directly against your worktree/status file

- **The decision is fully documented and closed** — `session/status/benchmark.md` §20.24-20.25,
  Dean-approved 2026-08-11: `per_request_lifecycle_metrics.json` disabled in 4 of 5 workload
  templates (OOM risk), with a comment in each YAML pointing at substitute signals. Not reopening
  this — it's settled.
- **The discovery pass is thorough and complete** — §20.24's field-availability table (arrival
  time, TTFT-aggregate-only, input/output length as bytes-not-tokens, e2e time, routed endpoint),
  cross-validated against ground truth (mean sojourn 0.23-0.42% low, p95 within 0.08-0.93%).
- **A real, working extraction tool already exists** —
  `benchmark/session-notes/scratch/envoy_per_request.py`, last touched 2026-08-08. Parses
  `igw_pods.log` (Envoy access log), dedups by `x-request-id`, handles multiple log shapes
  (harvest/follower), assigns per-request records to workload stages, has `--jsonl`/`--csv` output.
  Genuinely good code — validated numerically, documents its own limitations precisely (the
  `bytes_sent` dispersion caveat, the "upstream_ms is NOT a TTFT substitute" correction).

**What I could NOT find:** any Type 3 (task plan) for this tool, any mention of it in the relevant
Type 1 (design), and no Type 6 (review) — despite it being real, working, validated code that's
been sitting in `session-notes/scratch/` for six days. That's the process gap I want to flag
directly, not just route around: per this workspace's own conventions, a tool that reaches this
level of validation and reuse-worthiness should have gotten *something* — at minimum a Type 3
capturing what it does and why, ideally a Type 6 confirming the validation claims independently. If
there's a reason it stayed in scratch/ (e.g. still exploratory, not yet trusted enough to promote),
that's a fine answer — I'm asking, not asserting a defect.

**One concrete limitation I found, not yet resolved either way:** the tool's stage-assignment logic
(`assign_stages`) is written specifically for the 2026-08-07 *ladder* run's shape (`stage_grid`,
partitioning by cumulative per-stage counts against a known step sequence). The campaign's
dwell/staircase cells don't share that shape — I don't know whether the tool generalizes as-is or
would need real rework to run against, say, `m-satta-dwell`.

## The actual scope question

My own review doc (`planning/autoscaling-viz-panel-review-20260814.md`, not yet finalized — held
per Dean's instruction, nothing scheduled from it yet) currently frames "wire `igw_pods.log` into
`extract_real_trace.py`" as a viz-scope task. But that's exactly where I'm not sure we agree: is the
log-parsing/dedup/stage-assignment logic something your scope should own and expose as a reusable
module or CLI (since you already built half of it, and it's tied to harness/workload knowledge that
lives on your side), with my scope only consuming its output — or is the whole thing mine to build
fresh against `extract_real_trace.py`'s own needs, treating `envoy_per_request.py` as reference/
prior art rather than something to import or extend?

## What I need from you

1. Status: is anyone on your side actively working on generalizing `envoy_per_request.py` beyond
   the ladder run, or is it dormant?
2. Scope call: your read on who should own the actual wiring-into-the-viz-pipeline work.
3. Whether the missing Type 3/Type 6 for this tool is something your scope wants to close now, or
   deliberately deferred (and why, if so) — not asking you to write it on my behalf, just trying to
   understand whether it's an oversight or a choice.

Not scheduling anything on my side until this comes back — per Dean's explicit instruction not to
have this scheduled in two places at once.
