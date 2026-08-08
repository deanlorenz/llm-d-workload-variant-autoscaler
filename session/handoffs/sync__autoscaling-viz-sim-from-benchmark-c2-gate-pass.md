from: autoscaling-viz
to: sync
session: autoscaling-viz — simulation driven from a benchmark run (C1/C2 done, gate PASS)

## What this asks for

Two things in CURRENT.md's `autoscaling-viz` entry (currently the **2026-08-07** bullet at
`session/CURRENT.md:145`):

1. **Fix a stale tip.** That entry ends with *"`origin/autoscaling-viz` @ `a40dae11`, local tip
   `40b28ee9` (1 commit ahead)"*. Both numbers are now wrong. Current: **`origin/autoscaling-viz` @
   `4b263d73`, local tip `5a0c607f`, six commits unpushed**, working tree clean. The push needs Dean's
   explicit OK for that specific push and has not been given.
2. **Add the new work item below.** It is a distinct thread from the real-trace toolchain the 08-07
   entry describes, and from the synthetic multi-shape deck. Nothing in the 08-07 entry needs deleting
   beyond the tip numbers — the migration narrative it carries is still accurate.

Authority for everything below is **`plans/session/status/autoscaling-viz.md`**, already updated (tip
`5a0c607f`, `state: unblocked`). Please point CURRENT at it rather than duplicating detail.

## Proposed new entry

**2026-08-08 — autoscaling-viz: a simulation driven *from* a real benchmark run; calibration gate
PASSES on both arms.** Dean's task: *"drive a simulation from the benchmark results — the benchmark
defines the demand shape and the supply capacities. We compare actual behavior (the scale decisions
used in the benchmark) to the various algorithm."* Plus his correction that the decision process is in
the WVA logs (it is — `benchmark/session-notes/scratch/ladder-controller.log`; the results dir has no
`metrics/processed/wva_*` because `post_run_analyze.sh` never ran). Type 3 plan
`autoscaling-viz/planning/sim-from-benchmark-plan.md` — 12 sections, TOC-refreshed, on the code branch
by the earlier deliberate decision, **not** under `plans/planning/`.

- **C1 `run_inputs.py`** (`453fb779`, `9a83d2e2`) → `real-trace/ladder-20260807/run_inputs.json`
  (1.1 MB): 22,200 real arrival timestamps, 8-stage segmentation, replica desired/ready series, the
  engine ITL line, and the 87 WVA decision cycles. **The WVA decision rule verified 87/87.**
  Saturation never binds on this run (`rc == 0` all 87 cycles, util peak 0.811) — so nothing here
  validates behavior at or past `k_sat`, and the C4 arms that under-provision will leave the calibrated
  envelope by construction.
- **C2 `sim_from_run.py`** (`2636b221`) + a readable report (`92b37fbb`,
  `real-trace/ladder-20260807/C2-GATE-REPORT.md`) → **the gate PASSES on both arms, exit 0**
  (`5a0c607f`). Two arms: **A0r** (observed *ready* steps, no boot model — the gate, isolating the
  queueing + service model) and **A0d** (observed *desired*, paying the 110 s `setup` — the reference
  the A1–A9 control arms are compared against, since they pay the same lag). A0r: per-stage p50 within
  **8.0%**, p95 within **12.5%**, pooled decode throughput within **2.3%**, **2462/2462**
  replica-trajectory samples within 1 replica, queueing immaterial in both (0.000% sim / 0.266% real
  against a 1% bound; max per-pod concurrency 102 sim / 121 real against the 512 admission ceiling).
  A0d same verdict, worst p50 9.5% / p95 13.5%. **Nothing was tuned** —
  `params.tuned_to_pass_gate == []` and it is true; the one number fit from data is the ITL line
  (`itl = 0.1847·run + 9.265 ms`, r² = 0.942, n = 411), fit once before any comparison.
- **The fourth gate criterion was changed after it had been observed to fail — Dean's call, and the
  sequence is on the record in three places.** As originally written, `queue_onset` demanded sim and
  run show queueing in the *same set of stages*; sim shows none, the run shows stages 1, 2, 6. It is
  unpassable by construction: the real signal is 4 of 448 intervals / **0.266%** of in-system
  request-seconds, produced by vLLM's per-step **token** budget plus mid-transition **routing**,
  neither of which `sim.py` contains (plan §5.1 documents that limit). Dean resolved plan §8.2 on
  2026-08-08 in favor of `queue_material` — *queued request-seconds < 1% of in-system request-seconds
  in both, **and** max per-pod concurrency below the admission ceiling in both* — which is scale-free,
  so it still bites on the C4 arms that will genuinely queue. `queue_onset` is **retained and still
  evaluated on every run** under `superseded_checks`, printed under a superseded banner, so its FAIL
  never disappears. Recorded in plan §3, the `gate()` docstring, and the JSON.
- **Still Dean's, still open:** the **15% / 15% / 1-replica-at-90%** tolerances *and* the **1%** queue
  share. All four are my proposals, not derived from anything. He resolved the *criterion*, not the
  numbers.

**Dean's stated priority for the next step (2026-08-08):** *"I want to run a benchmark and call the viz
tools as a last step after I copy the results over. I want to get the full reports, graphs, HTML right
there with my results"* — into the benchmark's own experiment dir,
`benchmark/dean-20260807-234050-328/`, which already reserves `analysis/` at both the experiment and
the per-run-id level. Specified as **plan §7.1, the `viz_experiment.sh` call-site contract**: explicit
`--run` / `--controller-log` / `--out`, **no path discovery**, per Dean — *"why need discovery. The
benchmark who calls viz knows where the results are. Could be many run_ids."* One invocation per run
id, hard error on a missing path, `--out` the only thing written. This lands with **C5**, and two of
its pieces are **substantial single-file edits awaiting Dean's approval before coding**: `report.py`
and `run.py` both hardcode `OUT = "out"` and must take an output directory instead.

## Blockers to change

- **CLEAR:** the `queue_onset` criterion (was the one blocker gating C3+). Resolved by Dean
  2026-08-08.
- **NEW, needed before C5 coding:** approval for the `report.py` / `run.py` output-directory edits
  (substantial single-file edits to pre-existing files).
- **STILL OPEN, unchanged:** the four gate tolerance numbers (plan §8.2); fork 6 — what `prc` should
  mean for arm A2, needed before C4 not C3/C5 (I lean: run A2a/A2b/A2c side by side rather than pick);
  the **envoy input path in `extract_real_trace.py`**, a substantial single-file edit that blocks the
  5-panel real-trace figure for ladder-shaped runs (`per_request_lifecycle_metrics.json` is 0 bytes,
  harness OOM); whether to regenerate the shipped arm-B bundle; §12.2 items 7–9; plan-doc ownership;
  the inert `Edit()` allowlist entry.

## Next steps to record

C3 (arm A1 — recompute `rc`/`sc` from `demand`/`supply`/thresholds rather than reading them from the
log, and *assert* saturation stays non-binding rather than assuming it) is unblocked and can start
without any further decision. C5 is Dean's stated priority but needs the approval above first. C4
needs fork 6. The OWED deck-prose recheck (spike banner, two `2.5×` tokens, §2.4's deleted analytic
`W0`) is unchanged and still not started.

## Pending handoffs

No change. `benchmark__viz-cross-check-and-next-capture.md` is still outstanding to the benchmark
session; both of their inbound handoffs remain `.DONE`.
