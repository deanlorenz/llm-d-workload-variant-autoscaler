# Batch extract+render: all SUCCESS-collection runs at current code — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md).
Pure extraction+rendering pass, no code changes expected. Source:
[`benchmark-runs-inventory.md`](benchmark-runs-inventory.md) (2026-08-16 snapshot, now stale —
Stage A landed 3 more cells since it was written, listed below) plus a fresh re-check of every run's
collection status as of this spec.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L20:29
- [Run list — 31 runs, grouped {#run-list}](#run-list--31-runs-grouped-run-list) L30:54
- [Excluded, do not attempt {#excluded}](#excluded-do-not-attempt-excluded) L55:72
- [Procedure {#procedure}](#procedure-procedure) L73:92
- [Verification {#verification}](#verification-verification) L93:105

## Goal {#goal}

Every run listed below gets extracted and rendered fresh at current tip (`a1a815a7` or later —
confirm your own `git rev-parse --short HEAD` at execution time, don't assume this spec's cited sha
is still current if time has passed). This is the full-refresh option Dean chose explicitly: bring
every clean-collection run's viz status from STALE/NOT_ATTEMPTED to current in one pass, not a
sample.

[↑ TOC](#toc)

## Run list — 31 runs, grouped {#run-list}

**Pre-2026-08-16 (22 runs, all previously extracted at `870fff6d` or older — all now stale):**
`dean-20260810-064736-555`, `dean-20260810-072736-888`, `dean-20260810-080708-371`,
`dean-20260810-084756-739`, `dean-20260810-092644-320`, `dean-20260810-100827-539`,
`dean-20260810-105211-685`, `dean-20260812-152105-714`, `dean-20260812-203217-894`,
`dean-20260812-231722-822`, `dean-20260813-000928-609`, `dean-20260813-005321-943`,
`dean-20260813-013728-756`, `dean-20260813-130251-004`, `dean-20260814-032308-959`,
`dean-20260814-035754-869`, `dean-20260814-044129-931`, `dean-20260814-050448-704`,
`dean-20260814-053822-692`.

**2026-08-16 Stage A warmup campaign (10 runs, never extracted — includes 3 completed after the
inventory doc's own snapshot, verified clean here via each run's own harness log
`✅ Run complete` line before adding to this list):** `dean-20260816-101437-420`,
`dean-20260816-114054-872`, `dean-20260816-120617-342`, `dean-20260816-121254-238`,
`dean-20260816-130920-917`, `dean-20260816-140547-777`, `dean-20260816-150044-949`,
`dean-20260816-153947-120` *(m-ta-calibration-probe-warmup)*,
`dean-20260816-161824-974` *(m-satta-calibration-probe-warmup)*,
`dean-20260816-174704-649` *(m-ta-calibration-probe-p4-warmup)*.

Total: 29 runs. (The inventory doc's own 22+9=31 count included 2 runs now excluded — see below —
and this list adds the 3 newly-completed Stage A cells, netting to 29.)

[↑ TOC](#toc)

## Excluded, do not attempt {#excluded}

Per the inventory doc's own collection verdicts — genuinely FAILED collection, nothing to extract:
`dean-20260812-154829-365` (harness died mid-wait, empty results), `dean-20260814-031317-105` and
`dean-20260814-043416-513` (both aborted at pre-flight `verify_model`, empty results),
`dean-20260816-094045-651` and `dean-20260816-105035-918` (both genuine load-gen/harness failures,
confirmed via unfilled TTFT/ITL + zero `stage_*.json` files, not the false-alarm orchestrator-log
pattern). Do not spend time attempting these — there's nothing to extract.

**PARTIAL-collection runs are INCLUDED, not excluded** — `dean-20260810-100827-539`,
`dean-20260812-203217-894`, `dean-20260814-044129-931` all hit the known non-fatal
orchestrator-log-`Run-failed` pattern (real data, false alarm) and `dean-20260816-114054-872` /
`dean-20260816-120617-342` have real data with a known specific gap (empty WVA timeseries on the
latter two) — extract them anyway; the extractor's own coverage-check output will reflect whatever
real gaps exist, that's expected and fine.

[↑ TOC](#toc)

## Procedure {#procedure}

For each run in § Run list:
1. Extract fresh: point `extract_real_trace.py` at the run's results leaf (not the run root —
   confirmed earlier this session that `--run` must target `results/<leaf>/`, not the run directory
   itself, or you get a near-empty bundle).
2. Render fresh from that bundle.
3. Save output using this session's established naming convention:
   `session-notes/review-samples/<workload-name>-batchrefresh-<sha>.png` (+ `-bundle.json` /
   `-coverage.json`), where `<workload-name>` is the run's own `REPORT.md` heading and `<sha>` is
   the extractor sha actually stamped. If two runs share the same workload name (e.g. multiple
   `m-sat-dwell` runs pre-warmup vs the warmup one), disambiguate with the run ID suffix rather than
   overwriting — do not silently drop a run's own output because its filename collided with
   another's.
4. Confirm stamp match (`coverage.json` + PNG metadata) against current `git rev-parse --short
   HEAD` for every single render — this is a batch job, don't skip the check on any individual run
   just because earlier ones passed.

[↑ TOC](#toc)

## Verification {#verification}

- All 29 runs produce a render with no crash. If any run's extraction/render genuinely fails
  (not "shows expected gaps," but errors out), report it specifically rather than silently skipping
  — a batch job dropping a failure silently is worse than one that's loud about it.
- Spot-check at least 3-4 renders visually (not just exit-code) across different workload shapes
  before reporting done — pick ones you haven't already looked at closely this session.
- Report back via a `plan__` handoff listing every output path + confirmed stamp, not just a
  success count — Dean will want to pick specific ones to look at.
- This is a large batch — if it's going to take a long time, an interim progress note is fine, but
  don't hold the whole thing back waiting for 100% before saying anything.

[↑ TOC](#toc)

## Outcome (executed 2026-08-16, no code changes) {#outcome}

**35/35 leaves succeeded, 0 crashes**, extracted+rendered fresh against tip `a1a815a7` (the
panel3-stale-fill commit). Two runs (`dean-20260813-130251-004`, `dean-20260816-174704-649`) each
have 4 parallel results leaves, not 1 — all 4 extracted+rendered separately per leaf, not one picked
arbitrarily (31 runs named in § Run list → 35 actual leaves once these two are expanded).
`cross-treatment-comparison/` subdirectories under those same two runs are CSV summaries, not results
leaves, and were correctly skipped. The 5 genuinely-FAILED-collection runs named in § Excluded were
excluded as instructed.

Stamp match confirmed in **both** `coverage.json` and PNG-embedded metadata for all 35, not a sample —
checked every one. Visually spot-checked 4 across different shapes: a 2-pod staircase, a 13-pod
calibration probe with real saturation, a PARTIAL-collection run (included per § Run list's own
instruction), and a 19-pod `_warmup` profile with no controller.log/no per-request data exercising
several degrade paths at once — all clean, no defects.

All 35 saved to `session-notes/review-samples/` as
`<workload>-batchrefresh-a1a815a7[.png|-bundle.json|-coverage.json]`, disambiguated with the run ID +
leaf number wherever a workload name collided across runs (9 names did, more than anticipated in
§ Procedure's own "e.g. multiple `m-sat-dwell` runs" example).

`make test`/`lint`/`gofmt` N/A. Not push-ready — pure data refresh, nothing to review beyond Dean
spot-checking any of the 35. Reported via `plan__batch-refresh-all-success-runs-done.md`.

[↑ TOC](#toc)
