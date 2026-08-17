# Scaling-decision-reason panel — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 1. Source requirement: [`autoscaling-viz-design.md`](autoscaling-viz-design.md) § *Known gap:
no scaling-decision-reason panel exists*; original ask in
[`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md) § *Missing: a
scaling-decision panel*.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L21:37
- [Data source — confirmed format {#data}](#data-source--confirmed-format-data) L38:81
- [Panel design {#design}](#panel-design-design) L82:116
- [Implementation steps {#steps}](#implementation-steps-steps) L117:149
- [Explicitly out of scope {#out-of-scope}](#explicitly-out-of-scope-out-of-scope) L150:163
- [Verification {#verification}](#verification-verification) L164:178

## Goal {#goal}

Add a seventh panel to `render_real_trace.py` (`autoscaling-viz/` worktree) showing WVA's logged
scaling *reasons* over time, aligned on the shared x-axis with panel 2 (desired vs. ready
replicas). Today, understanding *why* a scale decision fired requires a hand-grep of
`controller.log` per finding — this was the manual step that caught and corrected the campaign
doc's Finding 3 misattribution. The new panel makes that visible on the figure itself.

**Working data, already gathered — no new run needed:** the 2026-08-10 campaign's per-cell
controller logs, e.g.
`benchmark/session-notes/campaign-runs/m-satta-dwell/controller.log` (and sibling cells:
`m-sat-dwell`, `m-ta-dwell`, `m-sat-staircase`, `m-ta-staircase`, `m-satta-staircase`,
`b-satta-staircase`, `m-ta-prefill-knee`). Each has a matching rendered `bundle.json` under
`plans/scratch/campaign-20260810-viz/` or `benchmark/runs/<id>/viz/`.

[↑ TOC](#toc)

## Data source — confirmed format {#data}

Verified directly against `m-satta-dwell/controller.log` and cross-checked against
`m-ta-staircase/controller.log` for the multi-analyzer case (both `saturation` and `throughput`
present). Two line shapes carry everything needed, both single-line JSON payloads after a
tab-separated `timestamp \t level \t source \t message` prefix:

**`analyzer-result`** (one line per analyzer per tick):
```
{"modelID": "...", "namespace": "...", "analyzer": "saturation", "supply": 658022, "demand": 0,
 "util": 0, "rc": 0, "sc": 658022, "scaleUpThreshold": 0.85, "scaleDownBoundary": 0.7,
 "variants": [{"name":"unsloth--608e585a-instruct-decode-scaler","prc":329011,"role":"decode",
               "reason":"P4-k1"}]}
```
`analyzer` is `"saturation"` or `"throughput"` (confirmed both appear per-cell when both are
configured). `variants` is `[]` when the analyzer has nothing to report for that tick (e.g.
throughput analyzer not voting) — this is not an error, do not treat an empty list as missing data.
`reason` per variant is one of `P1-obs`/`P2-hist`/`P3-k2`/`P4-k1` (`saturation_v2/types.go`'s
`k2SrcObserved`/`k2SrcHistorical`/`k2SrcDerived`/`k2SrcFallback`) for the saturation analyzer;
confirm the throughput analyzer's own reason vocabulary against `throughput_analyzer`'s source
before assuming it reuses the same four codes — do not hardcode P1–P4 as universal without checking.

**`scaling-decision`** (one line per model per tick, decisions array covers all variants for that
model):
```
{"modelID": "...", "namespace": "...",
 "decisions": [{"name":"unsloth--608e585a-instruct-decode-scaler","curr":3,"tgt":1,
                "action":"scale-down"}]}
```
`action` is one of `scale-up` / `scale-down` / `no-change` (confirmed from sample; grep the source
at `saturation/engine_v2.go:752` for the authoritative enum before assuming this is exhaustive).

**Analyzer-absent line** (recurring — **CORRECTED 2026-08-12**, was wrongly stated below as "zero or
one per run, not per tick"; the coder counted 8 occurrences on `m-ta-dwell/controller.log` and it
fires on every ~60s tick, same cadence as `analyzer-result`):
```
INFO saturation/engine_v2.go:160 saturation analyzer is absent from the configured analyzer list:
it will not vote and cannot veto scale-down for this model {"modelID": "...", "namespace": "..."}
```
Confirmed present in `m-ta-dwell`, `m-ta-prefill-knee`, `m-ta-staircase` (the TA-only cells, where
saturation is intentionally not configured) — absent from the SAT/SAT+TA cells. This is the line
that settled the campaign doc's Finding 1; it is not JSON-only, the human-readable message itself
is the payload. Capturing only the **first** occurrence (a boolean/timestamp) is still the right
extraction for the panel's purposes — the annotation only needs to say the analyzer never voted for
this run, not render 8 near-duplicate timestamps.

[↑ TOC](#toc)

## Panel design {#design}

**New panel 6** (renumber nothing existing — append after today's panel 5 / `f`, in the same
`fig, ax = plt.subplots(6, 1, ...)` grid; bump to `subplots(7, 1, ...)` and extend
`height_ratios`). Shares the same `grid`/`t0`/`span` as every other panel so x-alignment with panel
2 is automatic, not a separate registration step.

**Content, per analyzer track** (one horizontal lane per analyzer present in the bundle — typically
1 or 2 lanes: `saturation`, `throughput`):

- **Reason-code strip**: a step/scatter series at a fixed y per analyzer, one marker per
  `analyzer-result` tick, colored by `reason` code. Use a small fixed categorical palette (reuse
  `GP_COLORS` or a similarly small existing palette from `plots.py` — do not invent a new one; see
  the dataviz skill's categorical-color guidance before picking colors). Markers, not a filled
  area — this is a categorical event stream, not a continuous quantity.
- **Decision markers**: reuse the existing `axvline` convention from `mark_effects`/the per-axis
  `desired`-change loop at the bottom of `render()` (lines ~596-605 in the current file) — these
  already draw on *every* panel, so panel 6 gets them for free via the same loop; no separate draw
  call needed. Confirm this by reading that loop before adding anything new.
  If a distinguishing overlay for `action` is wanted beyond what those shared lines already give,
  keep it a light annotation (e.g. a text label at the vline), not a second redundant vline system.
- **Analyzer-absent annotation**: if the absent-line is present for this model, add one static
  annotation per analyzer lane (e.g. `ax.text` at a fixed corner, or a title-line note like panel
  2's boot-lag note) stating "analyzer absent from configured list — did not vote" rather than
  leaving that lane blank with no explanation, since a reader unfamiliar with the log won't know
  why a lane is empty for the whole run.
- **Legend**: reason-code color key, same placement/size convention as the other panels' legends
  (see the `axis.legend(...)` block at the end of `render()`).
- **Degrade like every other panel**: if no controller.log / no `analyzer-result` data was
  extracted into the bundle for this run, call `empty(ax, 'no scaling-decision data in this
  bundle — ...')`, matching the existing pattern (see panels 1a/2/3/4/5's `if/else: empty(...)`
  blocks) rather than leaving a blank subplot with no message.

[↑ TOC](#toc)

## Implementation steps {#steps}

1. **Extractor side (`extract_real_trace.py`):** add parsing of `analyzer-result` and
   `scaling-decision` lines (and the analyzer-absent line) from `controller.log`, alongside
   whatever log-file discovery it already does for other inputs — grep the extractor for its
   existing log-parsing pattern (it likely already tails other `*.log` files) and follow that
   convention rather than inventing a new file-discovery mechanism. Store the parsed result under a
   new top-level bundle key, e.g. `bundle['derived']['scaling_log']` — pick a key name consistent
   with the existing `derived.{capacity,sat_band,lags,router,itl_fit}` shape, one sub-object per
   analyzer keyed by name, each holding a time-ordered list of `{t, reason, variant}` (from
   `analyzer-result`) and a separate list of `{t, action, variant, curr, tgt}` (from
   `scaling-decision`), plus a boolean/timestamp for the analyzer-absent line if present.
   **Controller.log may not be co-located with the other inputs the extractor already reads** — per
   `session/status/benchmark.md`, the harness does not capture it into every run dir; where it *was*
   hand-collected (the 2026-08-10 campaign cells), confirm the extractor's CLI/config already
   accepts a path to it, or add a `--controller-log` flag following the same argparse convention as
   its other input flags.
2. **Renderer side (`render_real_trace.py`):** add the panel-6 drawing code inside `render()`,
   following § Panel design above. Bump `subplots(6, 1, ...)` → `subplots(7, 1, ...)` and extend
   `height_ratios` (a value in the `2.0`–`2.5` range, consistent with the other categorical/event
   panels like panel 4, is a reasonable starting point — this is a judgment call for the coder, not
   a fixed spec).
3. **Coverage.json:** decide whether to add a 17th coverage-check row ("scaling-decision log
   present") — recommended, since every other data source has one (see Item 5 / the coverage-check
   table in the Type 1), but not mandatory for this Type 3's completion. If added, follow the exact
   `{capability, verdict, detail}` shape of the existing 16 rows.
4. **Re-render the existing campaign bundles** (`plans/scratch/campaign-20260810-viz/*.json` or
   `benchmark/runs/*/viz/`) to confirm the panel actually draws against real, already-gathered data
   for at least the SAT+TA dwell cell (has both analyzers, has a scale-down) and one TA-only cell
   (has the analyzer-absent line) — do not consider this done on synthetic/toy input alone.

[↑ TOC](#toc)

## Explicitly out of scope {#out-of-scope}

Do not touch, as part of this Type 3:

- Panel 4's queue-source design (still INTERIM/undecided — epic plan Item 2).
- `tput_knee()` / `capacity()` / any estimation-model code (epic plan Item 3 — gated on Dean).
- The EPP scorer debug-log signal (epic plan Item 4 — not yet scoped).
- The coverage-check reference doc (epic plan Item 5) and the folder-structure question (epic plan
  Item 6) — separate items; may be picked up in the same coder session only if explicitly asked,
  not assumed.
- Renumbering or otherwise altering panels 1a/1b/2/3/4/5 beyond what's needed to append panel 6.

[↑ TOC](#toc)

## Verification {#verification}

- `gofmt`/lint/tests are N/A — this worktree is Python-only, not a Go code branch; standard
  WVA pre-push checklist does not apply here.
- Confirm the new panel renders without error against all 7 campaign cells' bundles (or as many as
  have a `controller.log` captured — some cells may not, per `session/status/benchmark.md`'s note
  that the harness doesn't capture it by default; degrade gracefully per § Panel design for those).
- Confirm x-axis alignment visually against panel 2 on at least one cell with a scale-down event.
- Confirm the analyzer-absent annotation appears on the TA-only cells and does not appear on the
  SAT/SAT+TA cells.
- Write results + any judgment calls (height ratio chosen, bundle key name used, whether coverage
  row 17 was added) to `session/status/autoscaling-viz.md` — this is a live status file per
  CONVENTIONS' status-file convention, coder-owned.

[↑ TOC](#toc)

## Outcome (committed `cff4e4c0`) {#outcome}

All four implementation steps done, all four verification checks done. Judgment calls: panel-6
height ratio **2.2** (in the plan's suggested 2.0–2.5 range); bundle key
`derived.scaling_log = {source, by_analyzer, decisions, saturation_absent_at}` (one sub-object per
analyzer keyed by name, each a time-ordered list of `{t, reason, variant}`; `decisions` is a flat
time-ordered list of `{t, variant, action, curr, tgt}` rather than per-analyzer, since decisions are
per-model not per-analyzer); coverage row 17 **added** ("Scaling-decision log present"). Controller-log
discovery checks `<run_dir>/controller.log` and `<run_dir>/logs/controller.log` before falling back
to `--controller-log`; verified this auto-discovery actually fires on a real run. Reason-code palette
is read from the data, not hardcoded — confirmed the throughput analyzer uses `T2-default` while
saturation uses `P1-obs`/`P2-hist`/`P3-k2`/`P4-k1`, and confirmed a red herring along the way:
`"reason":"OptimizationSucceeded"` also appears in controller.log but is a K8s Event reason on an
unrelated log line shape, not from the `analyzer-result` JSON payload — the extractor's strict
per-line-shape regex (`CTRL_LOG_LINE`) never matches that line, so it can't leak in.

**Correction to this plan's own claim about tick frequency.** The analyzer-absent line fires
**every ~60s tick**, not "zero or one per run, not per tick" — confirmed by direct count on
`m-ta-dwell/controller.log` (8 occurrences). Doesn't change the implementation (a first-seen
boolean/timestamp was already the right capture), just corrects the description for anyone reading
this doc later.

Verified against real 2026-08-10 campaign logs (not synthetic): `m-satta-dwell` (both analyzers, 9
scale-up/down transitions visible in panel 2, reason codes track the dwell cycle), `m-ta-staircase`
(TA-only, absent-analyzer annotation fires, early spurious saturation votes before the gate still
captured not dropped), and a no-`controller.log` bundle (degrades to the `empty()` message, matching
every other panel's convention). All three re-renders viewed as PNGs, not just exit-code-checked.
`make test`/`lint`/`gofmt` N/A.

[↑ TOC](#toc)
