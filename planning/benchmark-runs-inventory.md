# Benchmark runs inventory — collection / extraction / viz status across every run

**Status:** SNAPSHOT as of 2026-08-16 ~15:30 (see § Refresh protocol to update). This is a
data-collection doc, not a fix-anything plan — no code was run against any run's data, everything
below is read-only inspection. Owner: viz-panels planner (this session) for the viz column and the
refresh mechanics; the collection/extraction columns describe `benchmark`-scope's own artifacts and
should be cross-checked with them, not treated as this scope's authority on collection/extraction
correctness.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Headline findings {#headline}](#headline-findings-headline) L22:54
- [Status legend {#legend}](#status-legend-legend) L55:81
- [Table — all 31 runs {#table}](#table--all-31-runs-table) L82:133
- [Active campaign note — Stage A clean-recapture {#active-campaign}](#active-campaign-note--stage-a-clean-recapture-active-campaign) L134:150
- [Known caveats affecting multiple rows {#caveats}](#known-caveats-affecting-multiple-rows-caveats) L151:178
- [Refresh protocol — the mission/flow/checklist {#refresh}](#refresh-protocol--the-missionflowchecklist-refresh) L179:236

## Headline findings {#headline}

1. **Every one of the 22 pre-2026-08-16 runs was extracted in a single batch on 2026-08-14
   23:36-23:37, stamped `extractor_sha=870fff6d` (or older, unstamped) — none have been re-extracted
   since.** Current code is `0aade22f`, several commits later (the whole panel-review + panel-4
   heatmap + follow-up + SAT-fix sequence from this session alone). **All 22 are STALE.** None of
   this session's visual fixes (Items Q/R/T/U/W, the KV%-heatmap panel 4, the follow-up polish) are
   visible in any of these 22 renders yet.
2. **All 9 runs from 2026-08-16 (today) have never been extracted at all** (`NOT_ATTEMPTED`) — these
   are the `benchmark`-scope's live warm-up-campaign runs (see § Active campaign note), landing
   faster than viz can keep up, which is expected given the campaign is still running.
3. **3 runs across the set have no `REPORT.md` and empty `results/`** — genuine collection
   `FAILED`s, not extraction gaps: `dean-20260812-154829-365` (harness process died/disconnected
   mid-wait, no error, no results), `dean-20260814-031317-105` and `dean-20260814-043416-513` (both
   aborted at harness step `[04] verify_model` — pre-flight endpoint checks failed before any load
   generation started).
4. **2 of today's 9 warmup runs are collection `FAILED`** (`dean-20260816-094045-651`,
   `dean-20260816-105035-918`) — both show substantial cluster-side telemetry (40-60MB raw metrics)
   but the load-generator/harness itself failed, so no per-request TTFT/ITL data exists. These
   correlate with the "4 consecutive OOMKilled/failed harness pods" the campaign's own progress
   handoff (`plan__stage-a-progress-3of7-and-harness-oom-fix.md`) reports finding and fixing — **not
   independently re-diagnosed here**, just consistent with that account.
5. **A recurring false-alarm pattern:** many runs' harness orchestrator logs an `ERROR - Run
   failed: ... Some treatments had errors` line even though the underlying treatment, data
   collection, and analysis all completed cleanly with real (non-placeholder) metrics. This
   correlates with a missing `run_metadata.yaml` triggering a **known, already-documented harness
   bug** (`session/CURRENT.md`, 2026-08-14 benchmark entry: `run_cell.sh`'s unconditional `if
   errors:` check fails a step on a log line already labeled non-fatal) — see § Known caveats. Rows
   below are marked `PARTIAL` rather than `SUCCESS` wherever this pattern is the *only* anomaly
   found, to flag it for a human rather than silently downgrading or upgrading the verdict.

[↑ TOC](#toc)

## Status legend {#legend}

**Collection** — did the harness/load-generator/cluster-side telemetry actually capture usable data:
- `SUCCESS` — clean completion, no error/truncation signal, real data present.
- `PARTIAL` — some real data landed, but a real gap or an unresolved orchestrator-level failure
  marker exists (see each row's evidence for which).
- `FAILED` — no usable request-level data; `results/` empty or the harness aborted before load
  generation started.
- `WIP` — reserved for a run actively being touched right now (see § Active campaign note); none of
  the surveyed runs were caught mid-write at survey time, but this status exists for the next
  refresh to use if it lands mid-campaign.

**Extraction** — has `extract_real_trace.py` been run against this run's data, and is the result
current:
- `SUCCESS` (not seen this pass) — bundle exists and its `extractor_sha` matches current code.
- `STALE` — bundle/coverage exist but were produced by older code than current tip.
- `NOT_ATTEMPTED` — no bundle/coverage anywhere for this run.
- `FAILED` (not seen this pass) — an extraction was attempted and errored.

**Viz** — is a rendered panels PNG current:
- `CURRENT` (not seen this pass) — PNG's own stamp matches current code AND a current-data bundle.
- `STALE_CODE` — PNG exists, was rendered from the same (stale) bundle its coverage.json describes
  — i.e. self-consistent but old.
- `MISSING` — no render exists anywhere for this run.

[↑ TOC](#toc)

## Table — all 31 runs {#table}

Workload names are taken from each run's own `REPORT.md` first `### ` heading, except where noted.
Extraction sha/timestamp is from `coverage.json` where present. Full per-run evidence (log lines,
file counts, byte-identical-copy checks) lives in the survey workflow's journal, not repeated here
— see § Refresh protocol for how to regenerate it.

| Run ID | Workload | Collection | Extraction (sha / when) | Viz |
|---|---|---|---|---|
| `dean-20260810-064736-555` | m-satta-staircase | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260810-072736-888` | b-satta-staircase | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260810-080708-371` | m-sat-staircase | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260810-084756-739` | m-ta-staircase | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260810-092644-320` | m-satta-dwell | PARTIAL¹ | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260810-100827-539` | m-sat-dwell | PARTIAL (orchestrator FAILED marker²) | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260810-105211-685` | m-ta-dwell | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260812-152105-714` | m-ta-prefill-knee | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260812-154829-365` | *(no REPORT.md; inferred `ta_calibration_probe`)* | **FAILED** — harness died mid-wait, no results | NOT_ATTEMPTED | MISSING |
| `dean-20260812-203217-894` | m-ta-calibration-probe | PARTIAL — `analyze_results` found 0 stage files² | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260812-231722-822` | m-ta-calibration-probe | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260813-000928-609` | m-ta-dwell | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260813-005321-943` | m-satta-dwell | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260813-013728-756` | m-sat-dwell | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260813-130251-004` | m-ta-calibration-probe-p4 | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260814-031317-105` | *(no REPORT.md; stack "llama-8b")* | **FAILED** — aborted at `[04] verify_model` | NOT_ATTEMPTED | MISSING |
| `dean-20260814-032308-959` | m-sat-prefill-knee | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260814-035754-869` | m-satta-prefill-knee | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260814-043416-513` | *(no REPORT.md; stack "llama-8b")* | **FAILED** — aborted at `[04] verify_model` (endpoint timeout) | NOT_ATTEMPTED | MISSING |
| `dean-20260814-044129-931` | m-sat-calibration-probe | PARTIAL (orchestrator FAILED marker²) | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260814-050448-704` | m-sat-calibration-probe | SUCCESS | STALE (unstamped, ~2026-08-14) | STALE_CODE |
| `dean-20260814-053822-692` | m-satta-calibration-probe | SUCCESS | STALE (`870fff6d`, 2026-08-14) | STALE_CODE |
| `dean-20260816-094045-651` | m-satta-dwell-warmup | **FAILED** — harness treatment error, no stage files³ | NOT_ATTEMPTED | MISSING |
| `dean-20260816-101437-420` | m-satta-dwell-warmup | PARTIAL (orchestrator FAILED marker²) | NOT_ATTEMPTED | MISSING |
| `dean-20260816-105035-918` | m-sat-dwell-warmup | **FAILED** — load-gen crashed (tokenizer/prompt-length error)³ | NOT_ATTEMPTED | MISSING |
| `dean-20260816-114054-872` | m-sat-dwell-warmup | PARTIAL — transient metrics-scrape curl errors, 1 empty timeseries file | NOT_ATTEMPTED | MISSING |
| `dean-20260816-120617-342` | m-sat-dwell-warmup | PARTIAL — empty WVA timeseries, unfilled TTFT/ITL | NOT_ATTEMPTED | MISSING |
| `dean-20260816-121254-238` | m-sat-dwell-warmup | SUCCESS | NOT_ATTEMPTED | MISSING |
| `dean-20260816-130920-917` | m-ta-dwell-warmup | SUCCESS | NOT_ATTEMPTED | MISSING |
| `dean-20260816-140547-777` | m-satta-dwell-warmup | SUCCESS | NOT_ATTEMPTED | MISSING |
| `dean-20260816-150044-949` | m-sat-calibration-probe-warmup | SUCCESS | NOT_ATTEMPTED | MISSING |

¹ `m-satta-dwell` — 2026-08-10's own PARTIAL marker predates this doc; see the run's own
`results/<leaf>/` for detail if re-investigating.
² Orchestrator logs `Run failed` / `Some treatments had errors`, but the underlying data collection,
analysis, and REPORT.md metrics are real and complete — matches the known non-fatal-`if errors:`
harness bug (§ Known caveats), not independently re-diagnosed as anything else here.
³ Genuinely FAILED, not the false-alarm pattern — REPORT.md's own TTFT/ITL cells are unfilled (`?`)
and the harness's `analyze_results` step found zero `stage_*.json` result files, consistent with a
real load-generation-side failure, not just an orchestrator log-level quirk.

[↑ TOC](#toc)

## Active campaign note — Stage A clean-recapture {#active-campaign}

The 9 2026-08-16 runs above are `benchmark` scope's own **Stage A clean-recapture campaign**
(`planning/ta-pokprod-clean-recapture-plan.md`), launched in direct response to this session's
warm-up-step proposal (`session/handoffs/plan__benchmark-warmup-step-proposal.md`). Per their own
progress handoff (`plan__stage-a-progress-3of7-and-harness-oom-fix.md`, still open as of this
snapshot): **3 of 7 planned cells done clean, cell 4 (`m-sat-calibration-probe-warmup`) running now,
3 more remain.** A real harness-memory-sizing bug (32Gi default vs the 96Gi this workload needs) was
found and fixed mid-campaign, causing 4 of the early attempts to OOM — consistent with the FAILED/
PARTIAL pattern seen in the earlier 2026-08-16 rows above.

**Do not treat this table's 2026-08-16 rows as final** — the campaign is actively producing more
runs; this snapshot is already behind it by the time you read this. Re-run the survey (§ Refresh
protocol) rather than trust these 9 rows once the campaign's own completion handoff lands.

[↑ TOC](#toc)

## Known caveats affecting multiple rows {#caveats}

- **Non-fatal-labeled orchestrator failure, mislabeled at a higher level.** A missing
  `run_metadata.yaml` triggers a WARNING ("cannot window the follower's IGW capture, falling back to
  the gateway pod's own rotation-vulnerable log") which, via a separate bug in `run_cell.sh`'s
  unconditional `if errors:` check, escalates to an `ERROR - Run failed` / `Some treatments had
  errors` line at the orchestrator level — even when the underlying treatment completed and
  produced real data. Already documented in `session/CURRENT.md` (2026-08-14 benchmark entry); not
  re-diagnosed here, just applied as the explanation wherever this exact signature recurred.
- **Byte-identical duplicate viz artifacts.** Most pre-2026-08-16 runs carry two copies of
  `bundle.json`/`coverage.json`/`panels.png` — one at the run root's `viz/`, one nested under
  `results/<leaf>/viz/` — confirmed byte-identical (md5/diff) wherever checked. Both are the same
  stale 2026-08-14 batch; refreshing needs updating both locations or establishing which one is
  canonical (not decided in this pass).
- **Some runs have no explicit `harness_rc`-style exit marker** even when otherwise SUCCESS —
  verdict rests on the absence of errors plus a `Run complete` / `BENCHMARK RUN SUMMARY` block plus
  a populated REPORT.md, not a single unambiguous return code. Flagged per-row in the survey
  journal (§ Refresh protocol) where this applied; not re-flagged per-row in the table above to
  keep it readable.
- **Three survey agents (`dean-20260813-000928-609`, `dean-20260812-203217-894`,
  `dean-20260814-035754-869`) ran under a safety-classifier timeout** (the model that normally
  double-checks agent tool calls was unavailable). One (`dean-20260812-203217-894`) was
  independently spot-checked against its own raw logs by the planner and confirmed accurate; the
  other two were not independently re-verified but follow the same evidence pattern as neighboring
  rows that were checked.

[↑ TOC](#toc)

## Refresh protocol — the mission/flow/checklist {#refresh}

**Mission:** answer, per run directory under `benchmark/runs/`, three questions — (1) did
collection produce usable data, (2) has extraction been run and is it current, (3) has viz been
rendered and is it current — using only read-only filesystem/log inspection, no script execution
that writes anything.

**Flow (what this pass actually did, repeatable):**

1. `ls benchmark/runs/` to get the current run-ID list. Diff against the last snapshot's list to
   find new runs.
2. Get the current extractor's short SHA: `git -C autoscaling-viz rev-parse --short HEAD`.
3. Launch one read-only survey agent per run ID (this pass used a `Workflow` with `parallel()` over
   all run IDs — see the script recorded at
   `~/.claude/projects/.../workflows/scripts/benchmark-runs-inventory-*.js` if resuming the exact
   same run, or re-author fresh using the checklist below).
4. Each agent, per run, checks:
   - **Workload name:** `REPORT.md`'s first `### ` heading. If missing, say so explicitly and infer
     from `plan/<stack>/config.yaml` / `workload/profiles/` as a fallback, flagged as inferred.
   - **Collection:** does `results/<leaf>/` exist and is it populated; tail the main harness
     stdout/stderr logs for completion vs. error/traceback text; check `metrics/raw/` and
     `results/<leaf>/logs/` file counts/sizes; grep case-insensitive for
     `evict|rotat|truncat` across all logs (including gzipped, via `zgrep`); check REPORT.md's own
     metrics table for unfilled (`?`) cells as a corroborating signal.
   - **Extraction:** does `viz/bundle.json`/`coverage.json` exist (check both the run root and
     `results/<leaf>/viz/`); read `coverage.json`'s `extractor_sha`/`extracted_at`; compare against
     the current sha from step 2.
   - **Viz:** does a `panels.png` exist; check its embedded PNG metadata (`identify -verbose
     <path>` for the `extractor_sha`/`render_sha` text chunks, or a PIL one-liner if available) or
     fall back to the coverage.json stamp; also check
     `autoscaling-viz/session-notes/review-samples/` for any file matching this run's ID or
     workload name, and confirm via byte-diff whether it's actually a copy of this run's own render
     or a distinct one before citing it.
5. Collect results, cross-reference against any open `benchmark`-scope handoffs/plan docs
   (`session/handoffs/plan__*`, the relevant Type 3) for context on *why* a run failed if the raw
   evidence alone doesn't say — cite the handoff, don't re-diagnose from scratch if someone already
   did.
6. Write/update this doc's table + headline findings; do not silently overwrite prior findings —
   diff old vs. new and account for anything removed, per the general CURRENT.md editing discipline
   (applies here too, even though this isn't CURRENT.md).

**Checklist to re-run this cold, from just this doc:**

- [ ] `ls benchmark/runs/` — get current run list, diff against the table above for new/removed rows.
- [ ] `git -C autoscaling-viz rev-parse --short HEAD` — get current extractor sha.
- [ ] For each new/changed run: workload name, collection status+evidence, extraction status+sha,
      viz status+path — using the exact checks in step 4 above.
- [ ] Check `session/handoffs/plan__*` and `benchmark__*` for any open campaign context explaining
      recent runs (e.g. an active multi-cell campaign) before concluding a run is simply
      failed/abandoned — an in-flight campaign's early cells can look like isolated failures without
      that context.
- [ ] Update the table, headline findings, and any campaign note. Keep old headline findings that
      are still true; retire ones that are now stale (e.g. once Stage A actually completes, replace
      the "active campaign" framing with a landed-result summary and move it toward
      `session/history.md` per the usual CURRENT.md-adjacent discipline).
- [ ] Re-run `bash plans/scripts/toc-refresh.sh planning/benchmark-runs-inventory.md`.

[↑ TOC](#toc)
