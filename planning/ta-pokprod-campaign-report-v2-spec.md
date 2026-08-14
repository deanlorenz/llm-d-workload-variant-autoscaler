# TA on pokprod — Campaign Report v2 (spec, for review before writing)

**Purpose:** replace the current sprawl (`ta-pokprod-campaign-20260810-results.md` +
`ta-pokprod-rerun-results-20260813.md`, both history-heavy) with one report that leads with
cross-cutting conclusions and current data, not "how we got here." Per Dean's direction
2026-08-14: no benchmark history/narrative in the new report; per-run detail reports can still
exist, but there must be one summary table over all of them.

---

## Section 1 — Workload × WVA-config grid

One block per workload template (all 6, sparse grid — a workload with only 1 config run shows
"not run" in the other 2 columns, per Dean's answer). Columns: **sat**, **TA**, **satTA**.

Per workload block:
1. **Load-composition text** — stages, rate/distribution, request shape (in/out tokens), pulled
   from the workload `.yaml.in`'s own docstring + its stage definitions. Written once per
   workload, not per config (the load shape doesn't change across configs, only which analyzer(s)
   are enabled).
2. **Key-measurements table** — one column per config that has a run. Rows: P99 TTFT, P99 ITL,
   avg/max replicas, avg KV%, avg queue depth, errors. Pulled from each run's REPORT.md (same
   fields already in the two source docs).
3. **Panels row** — one cell per config, each cell a full markdown link to that config's latest
   `panel.png` (or whichever filename the toolchain emits). **Placeholder text where no viz/
   output exists yet** (true for every run right now) — never a broken link. Only ever links the
   latest-regenerated version once viz output exists; stale/superseded panel files are never
   linked.
4. **Run-report link** — one link per config to that run's own report (REPORT.md or the relevant
   per-run doc/section).

**Cross-config comparison note per workload** (short prose, 2-4 sentences) — what the sat vs. TA
vs. satTA columns actually show, where comparable. Skipped for single-config workloads.

## Section 2 — Cross-cutting analysis by topic

Reorganized prose, not new investigation — pulled and consolidated from the existing docs
(campaign results, rerun results, dwell-deep-dive status, history ledger). Topics, one subsection
each:
- The dwell limit cycle (P1-obs mechanism, created→ready lag, bucket-keyed `prc` collapse)
- Saturation-lags-demand (tail latency comparison, sat-only vs TA-analyzer cells)
- The knee/piecewise ITL model (mechanistic explanation, k_knee vs k_sat)
- Queue/drain behavior (what's measured, what isn't — per-request-trace dependency)
- Controller-restart hold-at-current-replicas policy question (D-46 finding)

No new claims — this section's job is to lift the "What's confirmed" / "Finding N" prose already
written elsewhere into one place, organized by topic instead of by run.

## Section 3 — Run index

**One summary table, all runs, one row each.** Columns: run ID, date/time, workload, WVA config,
**completed?** (did the harness run to completion without crashing/OOMing — distinct from whether
it hit its measurement goal), and a full markdown link to the run's results directory. Measurement
outcomes (TTFT, errors, etc.) stay in Section 1's per-workload tables, not duplicated here — this
table is purely an index: what ran, when, did it finish, where's the data.

Per-run detail reports (REPORT.md, or the existing rerun-results doc's per-cell rows) remain as
they are — this table indexes them, doesn't replace them.

---

## What happens to the two existing docs

`ta-pokprod-campaign-20260810-results.md` and `ta-pokprod-rerun-results-20260813.md` — content
gets absorbed into the new report's three sections; the two originals get a superseded-pointer
header (same pattern as the old `ta-pokprod-testing-plan.md` fold), not deleted, so any external
citation by old section number still resolves.

## Panel generation — handoff, not blocking

No run since 2026-08-10 has `viz/` output. Per Dean's direction: hand off to viz-panels-planner as
a single batch ask (all runs needing panels, listed together) rather than the report waiting on
it. Report ships now with explicit "panel pending" placeholders; updated in place once panels
land. If that planner scope isn't responsive, escalate to Dean rather than generating panels
myself (viz tooling is that scope's, not mine, per the ownership boundary settled 2026-08-13).

---

**Open question for Dean before I write this:** does this spec match what you want, or is there a
structural piece I've missed? Once approved, this is a substantial rewrite (>3 files touched —
two superseded, one new) so I'll show the actual draft before committing, per the large-change
approval rule.
