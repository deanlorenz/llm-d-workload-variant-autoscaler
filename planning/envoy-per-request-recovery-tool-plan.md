# Envoy per-request recovery tools (Type 3)

**Status:** documenting existing code retroactively (2026-08-14) — closes a real doc-coverage
gap flagged by viz-panels-planner (`session/handoffs/plan__envoy-per-request-tool-scope-and-process-gap.md`).
Covers **two** tools, not one — `session-notes/scratch/envoy_per_request.py` and
`session-notes/scratch/serving_replicas.py` (which imports directly from the former). Both real,
working, validated code, sitting in scratch/ since 2026-08-08 with no Type 3/1/6 coverage. This
doc captures what they do, why, and their known limitation — not a plan for new work, unless/
until the generalization question below is resolved.

**Correction 2026-08-14 (same day, before this doc was even committed):** the "was staying in
scratch/ deliberate or an oversight" question this doc originally left fully open actually has a
real, findable answer that predates the question — `session/status/benchmark.md` §17.7
(2026-08-08) already lists both tools as **"promotion candidates for `hack/benchmark/`"**. So the
honest state is neither "deliberate" nor "pure oversight": promotion was flagged six days ago and
never executed. That's a real gap in its own right (a flagged action that silently didn't
happen), distinct from either the "we meant to leave it exploratory" or "nobody noticed" readings.

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

## Companion tool: `serving_replicas.py`

Derives a **time-weighted serving replica count per stage from routing, not the controller**.
Imports `STAGES`/`assign_stages`/`fmt`/`parse` directly from `envoy_per_request.py` — same
ladder-run-specific hard limit, not independently generalizable.

**Why it exists:** the controller log's `curr` field is wrong for a latency model twice over —
60s sample resolution (a pod ready at :54 isn't observed until the next :40 sample), and it
counts pods that are Pending/pulling-image/loading-model as "current" while they supply zero
capacity, backwards for explaining latency. `UPSTREAM_HOST` settles it directly: a replica is
serving when the gateway is actually sending it requests, so each pod's `[first arrival, last
arrival]` interval, time-weighted per stage, is a routing-derived ground truth independent of the
controller.

**Validated against the controller-derived estimate, not asserted alone:** the two agree within
0.10 replicas on 6 of 8 stages; they diverge exactly where expected — stage 0 (serving 1.59 vs
`curr` 2.27, `curr` overstates by 43% because most counted replicas hadn't finished loading) and
stage 6 (3.45 vs 3.61, one replica counted from 21:14:39 but serving nothing until 21:15:28).
Corroborates a third finding from a third source: the replica the cold-`prc` cascade killed
served only 599 requests in its entire 426s life.

**Known caveat, stated in its own docstring:** a draining pod is credited as serving until its
final request, so the count lags actual termination slightly (a couple of seconds at this run's
rate) — the intended behavior (idle-but-has-capacity should count), not a bug, but worth knowing
when reading a stage boundary precisely.

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

## Status — answered by the coder, 2026-08-14

`session/handoffs/plan__benchmark-doc-coverage-answers-20260814.md` (from evidence, not
recollection — checked `git log` and prior session notes directly):

1. **Not being generalized.** `git log` on `envoy_per_request.py` shows no commits since
   `9e360b18` (2026-08-08, the day it was written) — dormant, not active.
2. **Oversight, not deliberate.** Confirmed by the coder's own prior session notes (§17.7, same
   day the tool was written): both `envoy_per_request.py` and `serving_replicas.py` were already
   flagged as "promotion candidates for `hack/benchmark/`" at the time, and the promotion never
   happened. Matches this doc's own correction above.
3. **Five MORE undocumented tools exist at the same never-promoted level**, all named in the
   coder's own §16.5 (2026-08-07, one day earlier) as promotion candidates, still in `scratch/`,
   confirmed via direct check that none have been promoted under any name:
   - `verify_decision_rule.py` (111 lines)
   - `server_token_truth.py` (92 lines)
   - `stage_table.py` (105 lines)
   - `stage_vs_replicas.py` (140 lines)
   - `watch_pvc_space.sh`

   **Explicitly not validated by the coder to the same standard** as the two covered by this doc —
   flagged as fact (existence, scratch-status), not vouched for correctness. That's a separate
   task if wanted, not assumed here.

**This means the doc-coverage gap is at minimum 8 tools, not 2** (the two covered by this doc +
these 5 + one already covered). This doc's own scope stays limited to the two it validates
directly; the other five are a distinct, larger cleanup — not silently absorbed into this Type 3.
