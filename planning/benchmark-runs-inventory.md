# Benchmark runs inventory — collection / extraction / viz status across every run

**Status:** SNAPSHOT as of 2026-08-17 ~18:45 (see § Refresh protocol to update). Refreshed after
the `good-panels.png` classification pass (`planning/autoscaling-viz-good-panels-classification-plan.md`,
executed by the autoscaling-viz coder/Bob) — this pass *did* run code against runs (extraction +
rendering, both read-write inside `benchmark/runs/<run>/viz/`, the canonical location), unlike every
prior snapshot of this doc which was read-only inspection only. Owner: viz-panels planner (this
session) for the viz/Good-panels columns and the refresh mechanics; the collection/extraction
columns describe `benchmark`-scope's own artifacts and should be cross-checked with them, not
treated as this scope's authority on collection/extraction correctness.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Headline findings {#headline}](#headline-findings-headline) L24:85
- [Status legend {#legend}](#status-legend-legend) L86:124
- [Table — all 34 runs {#table}](#table--all-34-runs-table) L125:185
- [Campaign note — Stage A clean-recapture, now complete {#active-campaign}](#campaign-note--stage-a-clean-recapture-now-complete-active-campaign) L186:209
- [Known caveats affecting multiple rows {#caveats}](#known-caveats-affecting-multiple-rows-caveats) L210:242
- [Refresh protocol — the mission/flow/checklist {#refresh}](#refresh-protocol--the-missionflowchecklist-refresh) L243:309

## Headline findings {#headline}

**Superseded by the 2026-08-17 good-panels pass (findings 1 and 2 below are now resolved, kept for
history rather than deleted):**

1. ~~Every one of the 22 pre-2026-08-16 runs was extracted in a single batch on 2026-08-14, stamped
   `extractor_sha=870fff6d` — all STALE.~~ **RESOLVED 2026-08-17**: all 29 extractable runs
   (COLLECTION-FAILED runs excluded) re-extracted and re-rendered at tip `a1a815a7`. See finding 6.
2. ~~All 9 runs from 2026-08-16 have never been extracted at all (`NOT_ATTEMPTED`).~~ **RESOLVED
   2026-08-17**: extracted and rendered along with everything else in the same pass; see finding 6
   for why none of the 10 Stage-A runs (9 + 1 more that landed since) are `good-panels.png`-worthy.
3. **3 runs across the set have no `REPORT.md` and empty `results/`** — genuine collection
   `FAILED`s, not extraction gaps: `dean-20260812-154829-365` (harness process died/disconnected
   mid-wait, no error, no results), `dean-20260814-031317-105` and `dean-20260814-043416-513` (both
   aborted at harness step `[04] verify_model` — pre-flight endpoint checks failed before any load
   generation started).
4. **2 of the Stage-A warmup runs are collection `FAILED`** (`dean-20260816-094045-651`,
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

**New, from the 2026-08-17 good-panels pass:**

6. **16 of 29 extractable runs are GOOD (trustworthy) — `good-panels.png` symlink created.** Current
   render at tip `a1a815a7`, per-request trace `PASS` (real or estimated — see finding 7). Run
   `ls benchmark/runs/*/viz/good-panels.png` to see exactly this set; it will stay accurate as long
   as this pass's classification isn't stale relative to a future re-render.
7. **8 of the 16 GOOD runs are GOOD only because of the estimated-data fallback** (landed at
   `deaf4886`, `Item AD` in `autoscaling-viz-warmup-anchor-and-panel-polish-plan.md`), not real
   per-request data. The stale 2026-08-14 bundles showed `FAIL` for these; the fresh extraction
   picked up each run's pre-existing `per_request_estimated.json` and surfaced it as `PASS`
   (visibly labeled ESTIMATED by the renderer, not silently treated as measured). Affected:
   `dean-20260810-092644-320`, `-100827-539`, `dean-20260812-203217-894`, `-231722-822`,
   `dean-20260813-005321-943`, `-013728-756`, `dean-20260814-044129-931`, `-050448-704`,
   `-053822-692` (9 listed, 8 counted — `-053822-692` doubles as both a plain re-render and this
   category; see the table's per-row detail).
8. **12 runs are MISSING-unobtainable** — no real, estimated, or raw-Envoy-log signal exists on
   disk for any of them; nothing short of re-running the workload could produce per-request data.
   Includes 2 pre-2026-08-16 runs (`dean-20260813-000928-609`, `dean-20260813-130251-004`) and all
   10 Stage-A warmup-campaign runs that didn't collection-fail outright — **this means the Stage-A
   warmup workload configuration, as currently run, does not produce per-request files at all**,
   consistent across all 10 successfully-collected cells, not an extraction gap.
9. **1 run is MISSING-obtainable-elsewhere**: `dean-20260810-105211-685` (m-ta-dwell) has a 54 MB
   raw Envoy access log (`igw_pods.log`) but no `per_request_estimated.json` yet — `benchmark` scope
   could run the estimation tool against it to produce one, at their discretion. Handed off via
   `plan__viz-good-panels-missing-obtainable-data.md`; not acted on by this pass.
10. **3 new runs found since the last snapshot** (`dean-20260816-153947-120`,
    `-161824-974`, `-174704-649`) — all extracted/rendered in this same pass, all MISSING-unobtainable
    (consistent with finding 8's warmup-configuration observation).

[↑ TOC](#toc)

## Status legend {#legend}

**Collection** — did the harness/load-generator/cluster-side telemetry actually capture usable data:
- `SUCCESS` — clean completion, no error/truncation signal, real data present.
- `PARTIAL` — some real data landed, but a real gap or an unresolved orchestrator-level failure
  marker exists (see each row's evidence for which).
- `FAILED` — no usable request-level data; `results/` empty or the harness aborted before load
  generation started.
- `WIP` — reserved for a run actively being touched right now (see § Campaign note); none of
  the surveyed runs were caught mid-write at survey time, but this status exists for the next
  refresh to use if it lands mid-campaign.

**Extraction** — has `extract_real_trace.py` been run against this run's data, and is the result
current:
- `SUCCESS` — bundle exists and its `extractor_sha` matches current code.
- `STALE` (not seen this pass) — bundle/coverage exist but were produced by older code than
  current tip.
- `NOT_ATTEMPTED` (not seen this pass) — no bundle/coverage anywhere for this run.
- `FAILED` (not seen this pass) — an extraction was attempted and errored.

**Viz** — is a rendered panels PNG current:
- `CURRENT` — PNG's own stamp matches current code AND a current-data bundle.
- `STALE_CODE` (not seen this pass) — PNG exists, was rendered from the same (stale) bundle its
  coverage.json describes — i.e. self-consistent but old.
- `MISSING` (not seen this pass) — no render exists anywhere for this run.

**Good panels?** (new 2026-08-17) — is `panels.png` both current AND backed by real informative
data, i.e. is `benchmark/runs/<run>/viz/good-panels.png` a trustworthy symlink to trust at a glance:
- `YES` — Viz is `CURRENT` and `coverage.json`'s `"Per-request trace present"` row is `PASS` (real
  or estimated data both count). `good-panels.png` exists, points at `panels.png`.
- `NO — MISSING-UNOBTAINABLE` — Viz is `CURRENT` but per-request trace is `FAIL`, and nothing on
  disk (no real file, no `per_request_estimated.json`, no raw Envoy log) could produce it.
- `NO — MISSING-OBTAINABLE` — same `FAIL`, but a raw source exists that `benchmark` scope's own
  tooling could turn into per-request data; not extracted here, per this scope's own boundary
  (see `autoscaling-viz-good-panels-classification-plan.md` § Scope boundary).
- `NO — COLLECTION-FAILED` — no viz possible; Collection is `FAILED`, not this column's concern.

[↑ TOC](#toc)

## Table — all 34 runs {#table}

Workload names are taken from each run's own `REPORT.md` first `### ` heading, except where noted.
Extraction sha/timestamp is from `coverage.json` where present. Full per-run evidence (log lines,
file counts, byte-identical-copy checks) lives in the survey workflow's journal, not repeated here
— see § Refresh protocol for how to regenerate it. Extraction/Viz for the 29 non-collection-failed
rows below are current as of the 2026-08-17 good-panels pass, tip `a1a815a7`; Collection is
unchanged from the last collection-focused survey (this pass didn't re-check it).

| Run ID | Workload | Collection | Extraction (sha / when) | Viz | Good panels? |
|---|---|---|---|---|---|
| `dean-20260810-064736-555` | m-satta-staircase | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260810-072736-888` | b-satta-staircase | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260810-080708-371` | m-sat-staircase | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260810-084756-739` | m-ta-staircase | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260810-092644-320` | m-satta-dwell | PARTIAL¹ | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=21120) |
| `dean-20260810-100827-539` | m-sat-dwell | PARTIAL (orchestrator FAILED marker²) | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=20979) |
| `dean-20260810-105211-685` | m-ta-dwell | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-OBTAINABLE (raw Envoy log 54MB present, no estimated.json yet; handoff sent) |
| `dean-20260812-152105-714` | m-ta-prefill-knee | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260812-154829-365` | *(no REPORT.md; inferred `ta_calibration_probe`)* | **FAILED** — harness died mid-wait, no results | NOT_ATTEMPTED | MISSING | NO — COLLECTION-FAILED |
| `dean-20260812-203217-894` | m-ta-calibration-probe | PARTIAL — `analyze_results` found 0 stage files² | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=7110) |
| `dean-20260812-231722-822` | m-ta-calibration-probe | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=7110) |
| `dean-20260813-000928-609` | m-ta-dwell | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE (no real/est/envoy signal) |
| `dean-20260813-005321-943` | m-satta-dwell | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=21120) |
| `dean-20260813-013728-756` | m-sat-dwell | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=21120) |
| `dean-20260813-130251-004` | m-ta-calibration-probe-p4 | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17, leaf `_1`) | CURRENT | NO — MISSING-UNOBTAINABLE (no real/est/envoy signal, leaf `_1`) |
| `dean-20260814-031317-105` | *(no REPORT.md; stack "llama-8b")* | **FAILED** — aborted at `[04] verify_model` | NOT_ATTEMPTED | MISSING | NO — COLLECTION-FAILED |
| `dean-20260814-032308-959` | m-sat-prefill-knee | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260814-035754-869` | m-satta-prefill-knee | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES |
| `dean-20260814-043416-513` | *(no REPORT.md; stack "llama-8b")* | **FAILED** — aborted at `[04] verify_model` (endpoint timeout) | NOT_ATTEMPTED | MISSING | NO — COLLECTION-FAILED |
| `dean-20260814-044129-931` | m-sat-calibration-probe | PARTIAL (orchestrator FAILED marker²) | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=7110) |
| `dean-20260814-050448-704` | m-sat-calibration-probe | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=7110) |
| `dean-20260814-053822-692` | m-satta-calibration-probe | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | YES (per_req PASS via estimated, n=7110) |
| `dean-20260816-094045-651` | m-satta-dwell-warmup | **FAILED** — harness treatment error, no stage files³ | NOT_ATTEMPTED | MISSING | NO — COLLECTION-FAILED |
| `dean-20260816-101437-420` | m-satta-dwell-warmup | PARTIAL (orchestrator FAILED marker²) | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-105035-918` | m-sat-dwell-warmup | **FAILED** — load-gen crashed (tokenizer/prompt-length error)³ | NOT_ATTEMPTED | MISSING | NO — COLLECTION-FAILED |
| `dean-20260816-114054-872` | m-sat-dwell-warmup | PARTIAL — transient metrics-scrape curl errors, 1 empty timeseries file | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-120617-342` | m-sat-dwell-warmup | PARTIAL — empty WVA timeseries, unfilled TTFT/ITL | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-121254-238` | m-sat-dwell-warmup | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-130920-917` | m-ta-dwell-warmup | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-140547-777` | m-satta-dwell-warmup | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-150044-949` | m-sat-calibration-probe-warmup | SUCCESS | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-153947-120` | m-ta-calibration-probe-warmup | SUCCESS⁴ | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-161824-974` | m-satta-calibration-probe-warmup | SUCCESS⁴ | SUCCESS (`a1a815a7`, 2026-08-17) | CURRENT | NO — MISSING-UNOBTAINABLE |
| `dean-20260816-174704-649` | m-ta-calibration-probe-p4-warmup | SUCCESS⁴ | SUCCESS (`a1a815a7`, 2026-08-17, leaf `_1` of 4) | CURRENT | NO — MISSING-UNOBTAINABLE |

¹ `m-satta-dwell` — 2026-08-10's own PARTIAL marker predates this doc; see the run's own
`results/<leaf>/` for detail if re-investigating.
² Orchestrator logs `Run failed` / `Some treatments had errors`, but the underlying data collection,
analysis, and REPORT.md metrics are real and complete — matches the known non-fatal-`if errors:`
harness bug (§ Known caveats), not independently re-diagnosed as anything else here.
³ Genuinely FAILED, not the false-alarm pattern — REPORT.md's own TTFT/ITL cells are unfilled (`?`)
and the harness's `analyze_results` step found zero `stage_*.json` result files, consistent with a
real load-generation-side failure, not just an orchestrator log-level quirk.
⁴ Collection status inferred from a clean extraction+render with no error and a populated REPORT.md,
not independently re-verified against harness logs the way the 2026-08-16 rows above were — these 3
runs were not in the last collection-focused survey pass; flagged as inferred rather than
re-diagnosed from scratch.

[↑ TOC](#toc)

## Campaign note — Stage A clean-recapture, now complete {#active-campaign}

**Superseded 2026-08-17 — Stage A is done, not active.** The 9 2026-08-16 runs plus the 3 newer
runs found in this pass are `benchmark` scope's own **Stage A clean-recapture campaign**
(`planning/ta-pokprod-clean-recapture-plan.md`), launched in response to this session's warm-up-step
proposal (`session/handoffs/plan__benchmark-warmup-step-proposal.md`). All cells are now extracted
and rendered at current tip. A real harness-memory-sizing bug (32Gi default vs the 96Gi this
workload needs) was found and fixed mid-campaign, causing the 2 remaining `FAILED` collection rows
in the table (`dean-20260816-094045-651`, `-105035-918`) — consistent with the FAILED/PARTIAL
pattern already documented per-row.

**The campaign's own result, from this pass's perspective**: every successfully-collected Stage-A
cell (10 of 12, the 2 FAILED excluded) rendered clean but is `MISSING-unobtainable` for per-request
trace — **the warmup workload configuration, as currently run, does not produce per-request files
at all**, consistently across all 10 cells. This is a data-collection-configuration fact, not a
per-run anomaly or an extraction gap; not independently root-caused here (that's `benchmark` scope's
own workload-config territory), just observed and recorded consistently.

If a new Stage-B (or similar) campaign starts producing more runs, re-run the survey (§ Refresh
protocol) rather than assume this table stays current — this note describes what happened, not a
standing guarantee about future campaigns.

[↑ TOC](#toc)

## Known caveats affecting multiple rows {#caveats}

- **Non-fatal-labeled orchestrator failure, mislabeled at a higher level.** A missing
  `run_metadata.yaml` triggers a WARNING ("cannot window the follower's IGW capture, falling back to
  the gateway pod's own rotation-vulnerable log") which, via a separate bug in `run_cell.sh`'s
  unconditional `if errors:` check, escalates to an `ERROR - Run failed` / `Some treatments had
  errors` line at the orchestrator level — even when the underlying treatment completed and
  produced real data. Already documented in `session/CURRENT.md` (2026-08-14 benchmark entry); not
  re-diagnosed here, just applied as the explanation wherever this exact signature recurred.
- **Duplicate viz artifacts — canonical location now decided and applied.** Most pre-2026-08-16 runs
  still carry two copies of `bundle.json`/`coverage.json`/`panels.png` — one at the run root's
  `viz/`, one nested under `results/<leaf>/viz/`. **The run-root copy is canonical** (decided during
  the 2026-08-14 "viz pull-up" work, `session/status/benchmark.md` §20.36; enforced by
  `benchmark/.gitignore`'s own allowlist, which un-ignores `runs/*/viz/` but not
  `runs/*/results/*/viz/`). The 2026-08-17 good-panels pass wrote only to the run-root copy per this
  rule — **the nested copies are now stale relative to the run-root ones and were deliberately left
  alone**, not deleted (out of scope for that pass). Do not treat a nested copy as authoritative for
  anything going forward; if a script or a human finds a nested `results/<leaf>/viz/`, the run-root
  `viz/` one level up is the one to trust.
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

**Note on the 2026-08-17 refresh — different mechanism, not a re-run of the flow below.** That
snapshot came from the autoscaling-viz coder's (Bob's) own good-panels classification pass
(`autoscaling-viz-good-panels-classification-plan.md`), which is write-capable (it re-extracts and
re-renders, not just inspects) and reports its findings via a `plan__` handoff that this doc's owner
folds in — it did not use the read-only Workflow-of-agents flow below. The flow below remains the
right mechanism for a **pure inspection** refresh (e.g. checking for new runs with no code changes
to run); reach for the good-panels Type 3 instead when the goal is also to bring stale viz output
current and produce `good-panels.png` symlinks.

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
