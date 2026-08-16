# TA on pokprod — Clean recapture campaign (Type 3)

**Status:** SCOPED, Dean-approved 2026-08-16, not yet executed. Supersedes nothing — the existing
21-run-leaf dataset stays on disk and cited as-is; this is a fresh, deliberately staged re-run to
get a clean dataset with warmup + fixed log capture, not a correction to prior results.

**Companion docs:** [`ta-pokprod-roadmap.md`](ta-pokprod-roadmap.md) (Type 2 — this is Phase 9) ·
[`ta-pokprod-history.md`](ta-pokprod-history.md) (D-63/D-64 — the gaps this campaign fixes) ·
[`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md) (per-request
extraction, unaffected by this — still needed regardless of warmup/log-capture fixes, since
per-request collection stays disabled by standing OOM policy).

---

## Why — three real gaps found this session, one fix each

1. **Stage-0 truncation** (D-59/D-63) — kubelet log rotation evicts the start of a run window
   from the post-run harvest, hitting exactly the region most valuable for autoscaling analysis
   (initial scale-up). Root cause: the harvest never reads from the gateway-log-follower's
   durable PVC copy, which already has the complete trace. **Fix: point the harvest at the
   follower's PVC file directly** (D-63 option (a), already validated working via the one-off
   re-harvest) — not a fallback, not an upstream fix, just read from the right place.
2. **No warmup stage** — every workload's stage 0 (or the run's very first moments) is hit by
   whatever startup variance exists (pod scheduling, model load, first-request latency spikes)
   with no buffer before the "real" measurement stages begin. **Fix: prepend a fixed-duration
   low-rate warmup stage** to every workload profile, before its existing stages, discarded from
   analysis (not counted toward any stage's numbers) but present in the raw capture.
3. **Log-capture gaps beyond the one already found** — the truncation fix addresses the gateway
   access log specifically; other log/metric sources may have the same or a different capture gap
   never checked. **Not assumed fixed by (1) alone** — verify during the gap-affected re-runs below.

## Exploratory instrumentation — capture liberally, decide later

Per Dean's explicit direction: "might as well capture the data, we can decide later if we keep
it." Add scrapes/flags now, during this campaign, rather than waiting for a specific need:

- Anything from D-57's research findings not yet captured (vLLM's `--collect-detailed-traces`
  OTel spans — real, shipped, not yet turned on anywhere; even though `--enable-per-request-metrics`
  itself doesn't exist on v0.20.2, per D-61, detailed tracing may).
- EPP's `"Before running filter plugins"` per-request pod-state snapshot (D-55) — not currently
  captured into any structured file, only visible via raw log grep.
- Any other vLLM flag or EPP config surfaced by future investigation — this campaign is the
  container to add capture to, not a one-time list closed now.
- **No content decision implied by capturing** — what's kept, promoted, or discarded is separate,
  later. Capture cost is cheap; re-running a whole campaign to add a scrape later is not.

## Staging — gaps first, then the full campaign

**Stage A — gap-affected runs only.** The runs that hit stage-0 truncation, missing per-request
data, or other capture gaps this session: the 3 original dwell cells, the calibration-probe
OOM/retry pair, the p4-parallelism run's 4 leaves, and `dean-20260813-005321-943` specifically
(already covered by the one-off re-harvest, D-64 — folds into this campaign's dataset once done,
not re-run again). Validates the warmup + log-capture fixes on a small set before committing GPU
time to everything.

**Stage B — full campaign.** All 6 workload templates × every config each workload's own design
calls for (matching the existing coverage-matrix scope, D-47/D-50) — re-run from scratch with
warmup + fixed capture + whatever exploratory instrumentation Stage A validated as working
cleanly. Treat the existing 21-leaf dataset as historical once this lands, not deleted, cited by
its own commit/run-IDs same as any other landed data.

## What this does NOT do

- Does not change the per-request-collection-disable policy (D-12) — estimation (D-57 onward)
  remains the fallback path regardless of this campaign's other fixes.
- Warmup duration/rate is decided (below) — not open anymore.
- Does not commit to keeping any exploratory instrumentation captured — that's a later, separate
  decision per workload/scrape.
- Does not affect the doc-coverage cleanup thread (D-51/D-56) or the dwell-forecast Type-1
  scoping (D-21) — both stay exactly where they are, unrelated to this campaign.

## Warmup, decided 2026-08-16

**4-5 minutes fixed, not a readiness-gated wait.** Every workload starts cold at
`minReplicas: 1` (confirmed — every variant config checked has this), so warmup has to actually
*trigger and complete* the initial scale-up, not just run traffic at replica 1 for a while.
Single-pod boot time observed across this campaign is consistently 65-96s (`Avg pod startup`
across 10 real REPORT.md files) — but that's one pod's boot only, not the full
decision-cycle-then-scale-up loop, and the dwell deep-dive found created→ready lag *worsens* with
concurrent boot count. 4-5 min is a generous margin over the observed single-boot number,
covering the controller's own decision cycle plus concurrent-boot lag, without needing to build
and validate a live readiness-check mechanism across 6 differently-shaped workloads with
different target replica counts. **Rate: whatever's needed to actually cross the scale-up
threshold** (not idle/near-zero traffic) — the point is to trigger and observe the real scale-up,
not merely wait out a clock while nothing happens.

## Open, before Stage A can launch

- **Exact workload-file diffs** — prepending a warmup stage touches every `.yaml.in` profile;
  per the semantic-pivot cross-reference convention, needs a grep-verification step once written
  (does anything downstream assume stage 0 is the first *real* stage — the coverage-matrix doc,
  any analysis script's stage indexing).
- **Any cluster run** — standing rule, Dean's explicit go-ahead needed before Stage A executes,
  same as every other run this mission.
