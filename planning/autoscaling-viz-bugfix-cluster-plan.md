# Panel bug-fix cluster — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 7. Source findings: [`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md)
§ Items A, B, D (the cross-cutting-observation item too — read it, it changes what "done" means here).

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal and scope {#goal}](#goal-and-scope-goal) L18:36
- [Fix 1 — figure title {#fix-1-title}](#fix-1--figure-title-fix-1-title) L37:65
- [Fix 2 — panel 1a triage (may not be a bug) {#fix-2-panel1a}](#fix-2--panel-1a-triage-may-not-be-a-bug-fix-2-panel1a) L66:85
- [Fix 3 — panel 3 legend, hatch, bar-top outline {#fix-3-panel3}](#fix-3--panel-3-legend-hatch-bar-top-outline-fix-3-panel3) L86:120
- [Verification {#verification}](#verification-verification) L121:134

## Goal and scope {#goal}

Three narrow, independently-verifiable fixes surfaced by Dean's 2026-08-13 review of a fresh panel-6
render. These are bugs or near-bugs (one — Fix 2 — may turn out to be correct behavior, not a
defect), distinct from the panel 3/1b structural redesign
([`autoscaling-viz-panel3-redesign-plan.md`](autoscaling-viz-panel3-redesign-plan.md)) and the panel
6 redesign ([`autoscaling-viz-panel6-redesign-plan.md`](autoscaling-viz-panel6-redesign-plan.md)),
which are separate Type 3s. Do this cluster first — it's lower-risk and some of its findings (e.g.
whether panel 3's missing series are a rendering bug vs. a scale problem) inform how the redesign
specs should be read.

**Per the review doc's cross-cutting observation:** before calling this done, spot-check the fixes
against more than the one sample Dean opened — pull 2-3 other already-rendered `panels.png` files
(e.g. from `plans/scratch/campaign-20260810-viz/` or other `benchmark/runs/*/viz/` dirs) and confirm
whether they show the same broken panes. Report what you find either way, even if the answer is
"these looked fine already."

[↑ TOC](#toc)

## Fix 1 — figure title {#fix-1-title}

**Confirmed root cause.** The sample's title read
`inference-perf-1786343242-zr01gi_1  ·  ?  ·  inference-perf  ·  ns=?`. Traced: `extract_real_trace.py`
builds `meta['model']`/`meta['namespace']` from `run_metadata.yaml` (`extract_real_trace.py:1230-1231`,
via `read_flat_yaml` at line 1145) — and for this run, `run_metadata.yaml` genuinely has neither key
(confirmed: `cat run_metadata.yaml` on the `m-satta-dwell` results leaf shows only
`harness_start`/`harness_stop`). **This is not an extractor bug reading the wrong field — the field
just isn't in that file for this harness.** The correct information exists elsewhere, confirmed
present:
- `config/<cell>.env` (sibling to the results leaf, one level up in the run root) has
  `BENCHMARK_NAMESPACE` and `BENCHMARK_MODEL_ID` as plain `KEY=value` lines.
- `<results-leaf>/ta_autoscale_dwell.yaml` (or the equivalent per-workload YAML) has `model_name`.
- **The workload/cell name itself** (`m-satta-dwell`, what Dean means by "workload" in "should
  reflect workload + run id") is the `.env` file's own basename, not a field inside any YAML —
  confirm how `--run` is invoked in practice (does the caller pass the cell name anywhere, or must
  the extractor infer it from the `.env` filename / `results-dir.txt` convention used by the
  campaign's `session-notes/campaign-runs/<cell>/results-dir.txt` files?). If no clean plumbing
  exists to get the cell name into the extractor's hands, that's worth flagging back rather than
  guessing at a brittle path convention.

**Fix:** extend the extractor's `meta` construction to fall back to `config/*.env` /
per-workload-YAML `model_name` when `run_metadata.yaml` doesn't have `model`/`namespace`, and thread
through whatever workload-name signal is available (env filename, an explicit new `--workload-name`
CLI flag, or similar) rather than defaulting to `?`. If truly nothing is available for a given run,
degrade to something informative (e.g. the run directory's own basename) rather than a bare `?`.

[↑ TOC](#toc)

## Fix 2 — panel 1a triage (may not be a bug) {#fix-2-panel1a}

**Not yet root-caused — triage first, don't assume a code defect.** Dean: "p1a is missing. In most
other panels.png it is ok." For the specific sample reviewed, panel 1a correctly shows "no
per-request trace in this bundle" because `m-satta-dwell`'s results leaf has no
`per_request_lifecycle_metrics.json` (confirmed via `find`; the extractor's own coverage row 15,
"Per-request trace present," FAILs with `n=0` for this run). **This may be entirely correct** — the
data genuinely isn't there for this run.

**What to actually check:** pick 2-3 of the other `panels.png` files where Dean says panel 1a looks
fine, and confirm those runs *do* have a captured per-request file. If they do, this "bug" is really
a data-collection gap for `m-satta-dwell` specifically (out of this Type 3's scope — flag it, don't
fix code for it) and the title/summary line's caveat text is already doing its job (it says "no
per-request trace… fetch results.json / per_request_lifecycle_metrics.json"). If instead you find a
run that *does* have the file but panel 1a still renders empty, that's a real extractor/renderer bug
— trace why the file isn't being picked up (path assumption, wrong glob, wrong harness auto-detect)
and fix it.

[↑ TOC](#toc)

## Fix 3 — panel 3 legend, hatch, bar-top outline {#fix-3-panel3}

Three independent readability fixes to panel 3 in `render_real_trace.py`, all landing regardless of
whether the structural redesign (separate Type 3) also happens — do these first since they're small
and the redesign doc assumes they're already done:

1. **Legend overflow.** Today's per-pod legend entries are full pod names (`f'{pod.split("-")[-1]}
   running'` at `render_real_trace.py:469`, similarly for waiting at line 480) — with 15 pods this
   overflows the panel. Replace with short numeric labels: assign each pod a stable number (e.g. by
   sorted pod name, so numbering is deterministic across a run and matches whatever ordering
   `ordered = sorted(pods.items())` already uses at line 463) and label as `f'pod {i+1} running'` /
   `f'pod {i+1} waiting'`. Consider a small legend key mapping number → full pod name in a corner
   annotation or the figure's footer text, so the mapping isn't lost — Dean didn't ask for this
   explicitly but it's a small addition that avoids losing information his fix otherwise discards;
   use judgment on whether it's worth the clutter.
2. **Hatch readability.** Today's waiting band: `color=BAND_SHADES[i % len(BAND_SHADES)], alpha=0.55,
   hatch='////', edgecolor=INK` (`render_real_trace.py:478-480`) — full pod color at reduced alpha,
   dark edge, which gets muddy with many overlapping pods. Try: drop the alpha reduction (full-
   saturation pod color) and use a white or near-white hatch/edge color instead of `INK`, so the
   hatch lines read as texture on a solid color rather than adding another layer of visual noise.
   This is "make it legible," not a pixel spec — use your own judgment on the exact hatch density/
   color if the first attempt still looks muddy with 15 pods.
3. **Bar-top outline.** Add a thin outline (e.g. `edgecolor=INK, linewidth=0.6` or similar) to each
   stacked bar segment's top edge — both running and waiting bars — so adjacent same-colored-ish
   segments are visually separable. Today's bars have `edgecolor='none'`/no edge on the running
   bars (line 469) and only the waiting bars get an edge (for the hatch, line 480) — extend edging to
   the running bars too, or at minimum their top edge.

**Do not** attempt the "missing total reqs" / "missing KV ceiling" complaint from Item D as part of
this Type 3 — those are addressed by the panel-3 structural redesign spec, since the fix is likely
"use a secondary axis or drop it" (a design decision, not a rendering bug) rather than "the series
was dropped by mistake."

[↑ TOC](#toc)

## Verification {#verification}

- Re-render at least 3 different campaign cells (mix of SAT-only/TA-only/SAT+TA, at least one with
  >10 pods) after each fix; view the PNGs, don't just check for a clean exit code.
- For Fix 1: confirm the title shows a real workload/model/namespace string, not `?`, on cells where
  the sibling `.env`/workload-YAML data is available; if a cell genuinely has none of it anywhere,
  confirm the degraded fallback is informative rather than blank.
- For Fix 2: write your triage finding (data-gap vs. real bug) into
  `session/status/autoscaling-viz.md` regardless of which it turns out to be — this doc should not
  be marked done on Fix 2 without that finding recorded.
- For Fix 3: confirm legend no longer overflows on a 15+-pod run, hatch is visually distinct pod-to-
  pod, and bar-top edges are visible.

[↑ TOC](#toc)

## Outcome (committed `037106f2`) {#outcome}

**Fix 1 (title `?`s).** `run_metadata.yaml` genuinely lacks `model`/`namespace` for the inference-perf
dwell/staircase harness runs (confirmed, not an extractor field-name bug). Added `find_cell_config()`
(globs `run_dir/../../config/*.env`, exactly one expected) and `find_workload_yaml()` (globs
`run_dir/*.yaml` for one with an indented `model_name:` under `server:` — `read_flat_yaml`'s
top-level-only regex can't see it) to `extract_real_trace.py`. Fallback chain: `model` =
`run_metadata.yaml` → `.env BENCHMARK_MODEL_ID` → workload-yaml `model_name`; `namespace` =
`run_metadata.yaml` → `.env BENCHMARK_NAMESPACE`; `workload` = `.env` basename (the actual cell name,
e.g. `m-satta-dwell`) preferred over the raw `harness_workload` filename when both exist — found live
during verification that one run's `run_metadata.yaml` *does* carry `harness_workload` but only as
the profile YAML's filename (`ta_autoscale_staircase.yaml`), not the human cell name, so cell name
wins. Renderer's title now shows `workload · run · model · harness · ns` instead of bare `?`s,
degrading to the run dir basename (always present) if every fallback is exhausted.

**Fix 2 (panel 1a triage — resolved as not a bug).** Confirmed by extracting a run known to have a
real `per_request_lifecycle_metrics.json` (`dean-20260810-080708-371`, 4.2 GB, `--head 2000`): panel
1a renders fully — arrival/departure curves, wait-band bars, real numbers. The review sample
(`m-satta-dwell`) has no per-request file at all (`find` confirms), so its empty panel 1a is a
**data-collection gap for that run, not a rendering or extraction defect**. No code changed for this
item.

**Fix 3 (panel 3 readability).** All three sub-fixes in `render_real_trace.py`: (a) legend now uses
numeric `pod N running/waiting` labels instead of full pod-name suffixes, which overflowed with 15+
pods, plus a compact `1=<suffix> 2=<suffix> ...` key line placed in the whitespace between panel 3's
x-axis and panel 4's title — first attempt used full pod names in the key and it visibly overlapped
the legend/next panel, caught by viewing the actual PNG, fixed by truncating to the short suffix
(same convention the old inline labels used) and tightening the y-offset; (b) waiting-band hatch
dropped its `alpha=0.55` reduction (full-saturation fill now) and switched `edgecolor` from `INK` to
near-white `#f5f5f5`, so the hatch reads as texture rather than a second muddying layer — visibly
cleaner on the 15-pod case; (c) running bars gained a thin `edgecolor=INK, linewidth=0.4` (previously
`edgecolor='none'`), matching the waiting bars, so adjacent same-ish-colored segments separate
visually.

**Verification**: re-rendered and viewed 4 cells spanning the pod-count/analyzer-mix space:
`m-satta-dwell` (15 pods, SAT+TA), `dean-20260810-080708-371` staircase (8 pods, SAT-only),
`m-ta-staircase` (3 pods, TA-only — also confirms panel 6's "saturation analyzer absent" annotation
fires correctly for a genuinely TA-only cell), and the shipped golden `staircase-20260803` bundle as
a backward-compat regression check (pre-panel-6, pre-Fix-1 bundle — renders clean, no crash).
`make test`/`lint`/`gofmt` N/A — Python-only worktree, no Makefile/test suite.

[↑ TOC](#toc)
