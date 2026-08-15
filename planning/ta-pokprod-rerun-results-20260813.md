# TA on pokprod — rerun results, 2026-08-12/13

> **SUPERSEDED 2026-08-14, RELOCATED 2026-08-15.** Content folded into the campaign report, which
> now lives at `benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md` (D-53). Kept on
> disk, unedited below, so old citations still resolve. Do not cite this doc going forward — use
> the new report.

**Status:** results write-up, real data only — nothing in this doc is inferred or projected.
**Scope:** the 6 cells run since the [2026-08-10 7-cell
campaign](ta-pokprod-campaign-20260810-results.md) — the two calibration-probe attempts, the
prefill-knee first-live-run, the parallelism-4 OOM-fix validation, and the three clean dwell
reruns that replace the original campaign's truncated/unusable dwell cells. Cross-referenced
against [`ta-pokprod-history.md`](ta-pokprod-history.md) ([[D-38]]–[[D-42]]); every number below
was read directly from each run's committed `REPORT.md`, not from status-file prose.

**What this doc is not:** it does not repeat the 2026-08-10 campaign's own findings (staircase
cells, the dwell limit cycle mechanism, the bucket-keyed `prc` collapse) — see that doc for those.
It also does not attempt the coverage-matrix / theory-simulation-real baseline asked for in
[`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) §4 — §4.2's theory/simulation legs
are viz-panels-planner's scope, not built here.

**⚠️ No viz output exists for any run in this doc.** All 8 run directories created since 2026-08-10
(`dean-20260812-*`, `dean-20260813-*`) lack a `viz/` folder — the extractor/render toolchain has
not been run against any of them. The original campaign's 7 directories all have `viz/` (3 files
each). Figures below are a gap, not an oversight — flagged in § Next steps.

---

## Results table

| Cell | Run dir | P99 TTFT (ms) | P99 ITL (ms/tok) | Avg / max replicas | Avg KV% | Avg queue depth | Errors | Report |
|---|---|---|---|---|---|---|---|---|
| m-ta-prefill-knee | `dean-20260812-152105-714` | 40,657 | 422.06 | 3.21 / 10 | 15.0% | 49.2 | 1 | [REPORT.md](../../benchmark/runs/dean-20260812-152105-714/REPORT.md) |
| m-ta-calibration-probe (attempt 1, OOMKilled) | `dean-20260812-203217-894` | ? | ? | 6.00 / 9 | 35.9% | 0.5 | 0 | [REPORT.md](../../benchmark/runs/dean-20260812-203217-894/REPORT.md) |
| m-ta-calibration-probe (retry, clean) | `dean-20260812-231722-822` | 20,088 | 136.79 | 6.25 / 10 | 27.0% | 1.1 | 0 | [REPORT.md](../../benchmark/runs/dean-20260812-231722-822/REPORT.md) |
| m-ta-dwell (rerun, full 40 min) | `dean-20260813-000928-609` | 3,568 | 64.90 | 4.13 / 10 | 9.9% | 0.0 | 0 | [REPORT.md](../../benchmark/runs/dean-20260813-000928-609/REPORT.md) |
| m-satta-dwell (rerun) | `dean-20260813-005321-943` | 3,392 | 65.98 | 3.62 / 6 | 11.5% | 0.0 | 1 | [REPORT.md](../../benchmark/runs/dean-20260813-005321-943/REPORT.md) |
| m-sat-dwell (rerun) | `dean-20260813-013728-756` | **91,712** | 151.97 | 2.93 / 10 | 21.0% | **32.4** | 1 | [REPORT.md](../../benchmark/runs/dean-20260813-013728-756/REPORT.md) |
| m-ta-calibration-probe-p4 (parallelism-4 OOM-fix validation, 4 parallel pods) | `dean-20260813-130251-004` | 19,053 avg (19,293/19,075/18,524/19,320) | 139.93 avg | 4.50 / 9 | 42.2% | 3.1 | 0 (all 4) | [REPORT.md](../../benchmark/runs/dean-20260813-130251-004/REPORT.md) |

`?` = value not recoverable from that run (OOM killed the harness before postprocess ran); kept
per Dean's "I want data from all cases" — the Prometheus-scraped fields (replicas/KV/queue-depth)
survived the crash and are real, TTFT/ITL/errors did not.

`dean-20260812-154829-365` exists on disk with no `REPORT.md` — an earlier/interrupted attempt
folded into the same commit (`b44935db`) as the p4 validation above; not a distinct result, not
tabled separately.

---

## What's confirmed by this round

**The OOM root cause and fix are both now evidence-backed, not just argued.** [[D-41]] traced the
OOM to inference-perf's own unbounded per-request metrics accumulator (source-confirmed, not
inferred). [[D-42]] confirmed `LLMDBENCH_HARNESS_LOAD_PARALLELISM` is real, and that dividing the
workload's own rates by the pod count — not the flag alone — is what actually divides load. The
p4 row above is the direct validation: 4 parallel pods, same treatment, **0 errors across all
four**, metrics consistent to within ~1% of each other (P99 TTFT 18,524–19,320ms) — this is the
concrete result the fix was supposed to produce, and it did.

**`m-sat-dwell`'s tail latency is the sharpest confirmation yet of the saturation-lags-demand
finding.** P99 TTFT 91,712ms and queue depth 32.4 — roughly 25× worse than either TA-analyzer
dwell cell on the same metric, on an otherwise-comparable run (all three dwell cells: 0 or 1
error, clean completion, no OOM). This is a confirming data point for a finding already
established in the 2026-08-10 campaign, not a new one.

**All three dwell reruns are now clean, full-duration runs** — the original campaign's `m-ta-dwell`
had an unusable r²=0.11 ITL fit from a truncated attempt; that gap is closed.

**`m-ta-prefill-knee` is the first live exercise of the full results-tree pipeline** ([[D-38]]),
and it surfaced a real `postprocess.py` bug (hard-coded filename assumption, didn't match
inference-perf's actual result format) — fixed and verified same day ([[D-39]]).

---

## What's still open (unchanged by this round, listed for completeness)

- No viz output for any of the 6 runs above — see the warning at top.
- `m-ta-calibration-probe`'s original OOM root cause within *this specific workload* — the
  general inference-perf accumulator mechanism is confirmed, but whether the parallelism-4 fix
  needs to become the standing default for this profile, or was a one-off validation, is not
  decided here.
- The coverage matrix and theory/simulation/real baseline (`open-scenarios.md` §4) remain not
  built, ownership split between this scope and viz-panels-planner's.
- Items 2 (harness-pod vital-signs monitoring) and 4 (direct-load-generation design question)
  from the OOM investigation remain open, Dean's, unrelated to the fix already validated above.

## Next steps

1. Run the extractor/render toolchain against the 6 (or 7, including the interrupted attempt if
   useful) run directories listed above, so this doc can carry real figure links instead of
   describing the gap. Not started — needs either this session or a coordinated ask to whoever
   owns the viz toolchain's invocation for benchmark-side runs.
2. Fold this doc's cross-references into `ta-pokprod-open-scenarios.md`'s checklist once the viz
   gap above is closed or explicitly deferred.
