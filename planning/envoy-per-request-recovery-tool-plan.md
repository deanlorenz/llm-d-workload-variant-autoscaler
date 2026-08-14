# Envoy per-request recovery tool (Type 3)

**Status:** documenting existing code retroactively (2026-08-14) — closes a real doc-coverage
gap flagged by viz-panels-planner (`session/handoffs/plan__envoy-per-request-tool-scope-and-process-gap.md`).
The tool itself is real, working, validated code, sitting in
`benchmark/session-notes/scratch/envoy_per_request.py` since 2026-08-08 with no Type 3/1/6
coverage. This doc captures what it does, why, and its known limitation — not a plan for new
work, unless/until the generalization question below is resolved.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md)
(Type 1 — this tool is a fallback signal for the per-request-collection-disabled decision
documented there) · [`ta-pokprod-history.md`](ta-pokprod-history.md).

---

## What it does

Recovers a per-request trace for a run whose `per_request_lifecycle_metrics.json` is missing or
unusable (OOM'd harness, tokenizer defects, etc.) by parsing istio-proxy's Envoy access log
(`logs/igw_pods.log`), which every request traverses regardless of what the harness itself
managed to serialize. Built specifically against the 2026-08-07 ladder run
(`dean-20260807-234050-328`), whose harness file is 0 bytes (OOM during serialization).

**What it recovers, better than the lost file in three respects:** wall-clock UTC timestamps
(no clock-anchoring needed), per-request routing attribution (`UPSTREAM_HOST` — the harness file
never had this at all), and a tokenizer-independent response-size measure (`bytes_sent`) immune
to this particular run's output-token defect.

**What it does NOT recover:** per-request TTFT (Envoy sees one duration, not the token stream)
and exact per-request output-token count. `bytes_sent` is stage-level-only — its p50 calibrates
against real output length (0.2% off) but its per-request *spread* does not (bytes/token drifts
170–187 across stages), so it cannot rank individual requests by output size. `upstream_ms` is
explicitly NOT a TTFT substitute — validated flat at 7–9ms across all 8 stages while real TTFT
climbs 47→183ms; it only times request acceptance, not prefill.

## Validation performed (real, not claimed)

- Request count: 22,200 in-window POSTs vs 22,200 harness successes — exact match.
- Mean duration: 8,817ms vs 8,850ms predicted from stage means (0.37% off).
- `bytes_sent` p50 implies 511 output tokens vs a true mean of 512 (0.2% off).
- Independently cross-checked per-stage (not pooled) against the harness's own `request_latency`
  by a separate autoscaling-viz session (2026-08-08): mean sojourn 0.23–0.42% low, p95 within
  0.08–0.93%, on every one of 8 stages. Consistently *slightly* low is the expected sign (excludes
  client-side handling).
- Stage-boundary self-validation: observed per-stage rate (1.95, 4.87, 7.76, 9.69, 11.66, 14.52,
  19.32, 2.01 req/s) reproduces the configured ladder (2, 5, 8, 10, 12, 15, 20, 2) to within
  normal sampling variance.

## Known hard limits

- **Stage-assignment is ladder-run-specific.** `assign_stages` partitions on cumulative per-stage
  request counts against a hardcoded `STAGES` list (`(2, 600), (5, 1500), ...`) that matches only
  the 2026-08-07 ladder run's exact shape. It hard-fails (not warns) on a count mismatch, by
  design — a truncated trace produces a silently *shifted* grid, not a partial one, so failing
  loudly is the correct behavior for this run, but it means the tool does not run against a
  differently-shaped workload (dwell, staircase, calibration-probe) without rework.
- **Envoy log durability is a cliff, not a slope.** The access log lives in the gateway
  container's stdout, subject to kubelet log rotation (measured 50MB reachable budget, only the
  latest of 5 on-disk files reachable via `kubectl logs`). Rotation evicts the *start* of a run
  window first — exactly the low-rate/scale-up region most valuable for autoscaling analysis.
  `--rotation-budget` reports current headroom; the exposure is on future/uncopied runs only —
  this run's trace is already safe on disk.
- **Dedup is required for gateway-log-follower captures.** The follower's `--since-time` watermark
  has 1-second granularity against 20+ lines/second of traffic, so it's deliberately
  at-least-once. Dedup on `x-request-id` (falling back to line-identity if absent) is on by
  default; duplicates left in would inflate the request count and trip the stage-assignment gate.

## Open question, not resolved by this doc

**Whose scope should own generalizing this beyond the ladder run, and where should the
log-parsing/dedup/stage-assignment logic live** — as a benchmark-scope module the viz toolchain
consumes, or rebuilt fresh inside `extract_real_trace.py` treating this as reference only? Raised
by viz-panels-planner, not decided here. Per-request collection is disabled by standing policy
(architecture doc, OOM risk) — this tool is the fallback signal path for that gap, so the
ownership question matters for closing it, but is explicitly out of scope for this
retroactive-documentation pass.

## Status — asked, not yet answered

A parallel handoff (`session/handoffs/plan__benchmark-doc-coverage-gap-check-with-coder.md`,
sent 2026-08-14, open) asks the benchmark coder whether anyone is actively generalizing this tool
beyond the ladder run, whether staying in scratch/ was deliberate or an oversight, and whether
other similarly-undocumented tools exist. **None of those questions are answered yet** — this
section will be updated once the coder responds, not before.
