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
**Correction 2026-08-15 (D-56): the actual count is 19 tools, not 7** — see
[`pokprod-scratch-tools-doc-coverage-cleanup-plan.md`](pokprod-scratch-tools-doc-coverage-cleanup-plan.md).

---

## Per-request data extraction/estimation for panels 1a/1b (2026-08-15) — resolves the open question above

**The ask, from viz-panels-planner:** panels 1a (throughput+quality) and 1b (work throughput vs
capacity) need per-request arrival time, TTFT, output size, e2e duration, outcome — currently
empty on every run collected under the standing per-request-disable policy. A full raw-data
inventory was handed over for one worked example (`dean-20260813-005321-943`, m-satta-dwell);
design and build is this scope's, viz only consumes the output.

**Framing correction before designing anything, Dean's direction:** the goal is extracting the
right data, not preserving any specific existing tool. Consolidate reusable *techniques* from the
tools already written into one coherent design; don't delete anything on disk in the process
(every scratch tool stays — see the cleanup-plan doc above for the separate promotion/deferral
question, unrelated to this design). Scope is broader than any single log source — checked and
ruled out, not assumed:

| Source | Per-request? | What it gives |
|---|---|---|
| `logs/igw_pods.log(.gz)` (Envoy access log) | ✅ | arrival time, e2e duration, routed pod, `bytes_sent` (output-size proxy, spread-unreliable) — no TTFT |
| EPP `"EPP received request"`/`"Request handled"` | ✅ | arrival time, routed endpoint, EPP-internal dispatch latency — no TTFT, no output size, no e2e duration |
| `metrics/processed/*.json` (harness-derived) | ❌ | aggregate/cumulative snapshots only, confirmed by direct inspection |
| `vllm:time_to_first_token_seconds_*` histogram (D-55) | per-stage bucket, not per-request | TTFT **distribution** per stage — the only TTFT signal that exists at all under the current collection policy |
| `vllm:request_generation_tokens_*` histogram | per-stage bucket | output-size **distribution** per stage |

**The real finding, and the design's honest ceiling:** under the current collection policy, **no
source gives true per-request TTFT or true per-request output-token count — full stop.** Only
per-stage *distributions* exist for those two fields. So this is estimation, not recovery: assign
each request a plausible TTFT/output-size drawn from its own stage's known distribution, anchored
to that request's real arrival time/duration/routing from Envoy (the one genuinely per-request
source). Confirmed with Dean 2026-08-15 — estimation is accepted as the ceiling for now
(per-request collection stays disabled, OOM risk unchanged); not treated as a temporary stopgap
pending a fix, since no fix removes the OOM risk on the harness side.

**Design, consolidating existing techniques rather than any one tool wholesale:**
1. **Per-request skeleton from Envoy** — generalize `envoy_per_request.py`'s parsing/dedup logic
   (real, validated, reusable as a technique) but **replace its hardcoded `STAGES`/ladder-specific
   `assign_stages`** with stage boundaries read from the run's own workload profile + harness
   metadata, not a literal constant — this is the actual generalization the "ownership" question
   was blocking on, and it's a design change, not a preservation of the existing function
   signature.
2. **Per-request TTFT/output-size estimate** — for each request, draw from its assigned stage's
   `vllm:time_to_first_token_seconds`/`vllm:request_generation_tokens` histogram (e.g. inverse-CDF
   sampling within the bucket the histogram's shape implies, or simplest-first: assign the
   bucket-conditional mean) — a new technique, not present in any existing scratch tool.
3. **Output format** — a per-request record shaped to match
   `per_request_lifecycle_metrics.json`'s existing field names where the estimate genuinely fills
   that role (`arrival_time`, `ttft` marked `estimated: true`, `output_tokens` marked
   `estimated: true`, `e2e_duration` real, `outcome` real) — so `extract_real_trace.py`'s existing
   `find_per_request()` needs a source-format branch, not a new schema, and every estimated field
   is distinguishable from a measured one downstream.
4. **Scope of "done," per viz-panels-planner's own request:** build and run against
   `dean-20260813-005321-943` only, first. Generalizing to the rest of the campaign is explicitly
   a later step, not this one's.

**Background investigation returned 2026-08-15 — a real finding, changes the picture.** vLLM has a
shipped flag, **`--enable-per-request-metrics`** (docs.vllm.ai, origin: GitHub feature request
#40076), that puts genuine per-request TTFT (`metrics.time_to_first_token_ms`) and output-token
count (standard OpenAI `usage.completion_tokens`) directly in each response body. **Crucially,
vLLM itself does not accumulate this anywhere — retention is entirely the caller's choice.** That
is a structurally different risk profile from the harness's own mechanism (D-41: one unbounded
Python list holding every full request/response body) — capturing just these two small fields per
response, streamed to a bounded aggregator instead of retained whole, would not inherit the OOM
mechanism that got per-request collection disabled in the first place.

EPP was checked too and is a dead end for this specific gap: `pkg/epp/handlers`'s
`RequestContext` struct genuinely holds the right fields (both timestamps, a `Usage` object) and
is not itself OOM-prone (discarded per request, never accumulated) — but none of it is currently
logged or exported, and no upstream work proposes to. Not a live candidate today. **One further
detail from a second research pass:** EPP has a "Latency Predictor" plugin with
`PreRequest`/`ResponseStreaming`/`ResponseComplete` lifecycle hooks carrying per-request token
counts, and upstream issue #2540 proposes per-request tracking generally — neither confirmed as
shipped/exported today, flagged as a lead worth re-checking if the vLLM flag path (below) doesn't
pan out.

**This finding does not retroactively obsolete the design above** — the vLLM flag needs its own
verification (does it work as documented on the image versions actually in use here, what's the
actual overhead, does the harness's own OpenAI-client parsing already surface `usage` today) before
it can replace estimation as the plan. Treating it as a **second, higher-priority thread**: verify
the flag on a real run before building more on the estimation path, since if it works cleanly, it
may make the histogram-based estimation approach a fallback rather than the primary mechanism.
Flagged for Dean's prioritization call, not decided here — the estimation build already handed to
the coder for the one example run stays in flight regardless, since it doesn't require this flag
and answers a real near-term need either way.

**A related, independently-found data point:** `logs/modelserving_pods.log` (the decode pod's own
`routing-proxy` sidecar, `llm-d-inference-scheduler`) initializes OpenTelemetry tracing on startup
("OpenTelemetry tracing initialized successfully," 10% sample ratio) — but every export attempt
fails (177 occurrences on the one example run): `dial tcp 127.0.0.1:4317: connect: connection
refused`. The OTel collector endpoint isn't running in this deployment, so traces are generated
and silently dropped, never reaching any sink. Consistent with the research finding above —
tracing infrastructure exists in the stack (both vLLM's own OTel support and this sidecar's) but
isn't wired to a working collector here. Not pursued as its own thread — the response-body flag
above is the more direct path to the same data without needing a collector deployed at all.

**Two other threads, unchanged:**
- **Longer-term alternative, noted not investigated:** replay/trace-based workloads (real request
  traces instead of fully synthetic generation — supported by the harness and inference-perf,
  possibly others) would carry real input/output-token-length stats for every request by
  construction. Not pursued now; flagged for the roadmap.
- **Alternative already checked and ruled out:** a separate plain-HTTP gateway access log beyond
  Envoy's — doesn't exist; `igw_pods.log` already *is* the gateway's access log, fully
  characterized above and in D-55.

**Not yet done:** the estimation build (handed to the coder, in progress) and verifying the
`--enable-per-request-metrics` flag (not yet started, not yet handed off — needs Dean's
prioritization call on sequencing first).
