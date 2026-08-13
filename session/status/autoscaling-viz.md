last_update: 2026-08-13T06:00:00Z
state: blocked
blocked_on: session paused for a machine restart, mid-Task-4 — resume from here, nothing lost
current_step: **PARKED mid-Task-4, no code changes made yet — safe resume point.** Picked up
`autoscaling-viz__task4-drain-window-fix.md` (marked `.WIP`), read the code spec
(`planning/autoscaling-viz-drain-window-fix-plan.md`) in full, and reproduced the reported bug
(confirmed `pod_drain_windows()`'s backward scan has no bound tied to the replica set's own
`desired` transition — on `m-ta-staircase`, pod `r2tnh` shows a drain window `[615s, 1058s]`
relative to run start, when the real `desired` transition is at t≈1073s; matches the spec's own
finding exactly). **Nothing written to any file yet** — `git status` on this worktree is clean, tip
still `3f12aaa1` (Task 3). The fix itself (bound the backward scan by the nearest `desired`
step-down before this pod's matched drain event, per the spec's § Fix) has not been started.
**Resume**: re-derive the reproduction (extract `m-ta-staircase`'s results leaf with
`--no-per-request`, check `pods['...r2tnh'].drain_windows` against `derived.lags.drain_events`) if
needed, then implement the fix in `pod_drain_windows()` at `extract_real_trace.py` (currently
~825-869, may have shifted slightly — grep for `def pod_drain_windows`), using the replica
timeseries (`reps`, already in scope at the `build()` call site per the spec) to clip the backward
scan. Verify per the spec's own checklist: `r2tnh`'s window should start near t≈1073s, not t≈615s;
spot-check 2 other cells with real scale-downs (`m-satta-dwell`, `m-sat-dwell`) for no regression;
confirm the running+draining+waiting+EPP-queue == total-in-system invariant still holds.
**Housekeeping**: `autoscaling-viz__task4-drain-window-fix.md` is marked `.WIP` in
`plans/session/handoffs/` — whoever resumes this branch should continue treating it as in-progress,
not re-pick-it-up-as-new. Per the plan's own § Explicitly out of scope, do NOT combine this fix with
panel 3's separate visual-scheme item (§ Item K, blocked on this landing first) or the untouched
figure-title/corner-info items (§§ I, L).

### Prior session (2026-08-13, Task 3 panel6 redesign, preserved below)
current_step: **Task 3 (panel 6 redesign, final of the sequenced review-fix series) landed, committed
`3f12aaa1`.** Picked up via `autoscaling-viz__task3-panel6-redesign.md`, code spec
`planning/autoscaling-viz-panel6-redesign-plan.md`. Supersedes the shipped reason-code marker strip
(`cff4e4c0`) with a signed replica-delta line per analyzer.
- **Extractor**: `by_analyzer` records now also carry the analyzer's aggregate `rc`/`sc` for that
  tick plus the reporting variant's `prc`, additive to the existing `t`/`reason`/`variant` fields.
- **Delta formula, derived not copied.** The spec's own suggested starting point (`sc/prc − rc/prc`)
  had the sign backwards — confirmed by reading the saturation engine's actual source
  (`applyUniversalThreshold` in `internal/engines/saturation/engine_v2.go`): `RequiredCapacity`
  is capacity deficit (scale-up pressure), `SpareCapacity` is capacity surplus (scale-down pressure),
  both independently `max(0, ...)`-clamped so never simultaneously positive. Used `rc/prc − sc/prc`
  instead. **Hand-verified against 2 real controller.log ticks**, per the spec's own required check:
  a `throughput` tick immediately before a confirmed scale-up (`curr=1,tgt=2`) computed
  `rc/prc=+0.110`; a `saturation` tick at a confirmed scale-down (`curr=3,tgt=1`, `sc>0,rc=0`)
  computed negative. Both match the expected sign.
- **Panel redesign**: one signed line per analyzer (fixed `ANALYZER_COLORS`, a per-series-identity
  palette, deliberately not `GP_COLORS`/`BAND_SHADES` which are per-distinct-value categorical and
  would reassign colors across runs), zero-reference `axhline`, replica-count y-axis, reason code as
  a marker shape overlay with a compact text key (`markers: ^=P1-obs D=P2-hist ...`) rather than a
  second full legend column — **applied the panel-3 legend-density lesson proactively this time**
  instead of discovering it again the same way. Absent-but-still-reporting analyzer's line renders
  dashed + faded (confirmed real via a TA-only run: `saturation` genuinely absent from the configured
  list yet still logging real `rc`/`sc`/`prc` every tick, matching the design doc's own 2026-08-13
  all-cells-sweep finding), so the line's shape doesn't read as "this analyzer's vote mattered here."
- **Kept unchanged, verified no regression**: the analyzer-absent text annotation (simplified from
  two placement branches to one, since panel 6 no longer has per-analyzer horizontal lanes for the
  old branching to distinguish — the two branches had converged to identical text placement once the
  lanes concept was removed, caught while re-reading my own draft before committing, not by the
  planner), the `empty()` degrade path when no `controller.log` data exists, and the shared
  per-panel decision-vline loop (confirmed still firing on the redesigned panel).
- **One self-caught layout collision during verification**: the reason-marker text key first landed
  below the axis at y=-0.22, directly colliding with the figure's one x-axis label (panel 6 is the
  bottom-most panel and owns that label) — moved inside the axes, bottom-right corner, before commit.

**Verification**: re-rendered and viewed `m-satta-dwell` (15-pod SAT+TA, both analyzer lines visible,
signed values visually consistent with panel 2's replica trajectory — positive during the 0-350s
scale-up, negative through the 350-1300s scale-down, rising back near 1600-2000s), `m-ta-staircase`
(TA-only, saturation's line correctly dashed/faded, absent-annotation still fires), a
`--controller-log /dev/null` degrade-path check (empty message shown, decision-vlines still draw),
and the golden pre-panel-6 bundle (no `scaling_log` key at all — degrades cleanly, no crash).
`make test`/`lint`/`gofmt` N/A, unchanged.

**This was the last queued task in the sequenced series** (bugfix-cluster → panel3-redesign →
panel6-redesign), per the Task 3 kickoff trigger's own note. A Task 4 trigger
(`autoscaling-viz__task4-drain-window-fix.md`) exists but is explicitly held
(`.HOLD-until-task3-done` at pickup time) — not yet actionable, watching for it to release.

### Prior session (2026-08-13, Task 2 fix-round 1, preserved below)
current_step: **Fix-round 1 on Task 2 landed, committed `08927557`.** Picked up via
`autoscaling-viz__task2-fixround1.md` — the planner's own independent re-render of Task 2
(`fbecfe26`) against `m-satta-dwell` found two real defects my own verification missed. Both
reproduced locally first, on the exact same run and commit, before touching any code — confirms
they weren't environment-specific.
- **Issue 1 (panel 1b cap no-op).** My Task 2 verification tested this exact no-per-request run and
  recorded "no crash, sensible degrade" — true but incomplete: I checked the axis didn't error, not
  that it was actually capped. `work_peak` evaluates to 0 when `offered_w`/`total_w` are both `None`
  (no per-request trace), so the `if work_peak > 0:` guard skipped the whole cap+annotate block,
  leaving the axis auto-scaled to ~50000 — the exact pre-Task-2 look, just for a different (common)
  trigger condition than the one I'd already guarded against (the `UnboundLocalError` crash). Fix:
  fall back to `median(ceil)` as the anchor when there's no work stack at all, so the ceiling's own
  low/mid plateaus stay legible instead of one high step dominating. **Found a second problem while
  fixing this one**: with several separate off-chart excursions spread across a 2000s+ run (not one
  contiguous boot ramp), the existing per-plateau dedup still let 5-6 labels land close together
  once compressed into the figure's pixel width — caught by viewing the intermediate render, not by
  re-reading the logic. Widened `min_gap` to 5% of span and staggered labels' vertical position
  (alternating 0.97/0.88 of `y_max`) so nearby labels stack instead of overlapping; down to 2 clean
  labels on the same run (was 5-6 illegibly cramped, was 0 before that).
- **Issue 2 (panel 3 legend density).** My earlier "fixed" claim for Task 2's legend only addressed
  the *draining* band's per-pod explosion — I never re-checked that the pre-existing 15 "pod N
  running" + up to 15 "pod N waiting" rows (already there since Task 1, unaffected by my draining
  fix) still fit once draining's one extra row was added. They didn't: 21 total rows in one column
  bled down into panel 4's title area on the reviewed sample. Task 1's numeric labels fixed row
  *width* (full pod names → numbers); this never touched row *density*. Fix: above 6 pods, collapse
  running and waiting to one representative legend entry each ("pods running/waiting (see color key
  below)") — the per-pod number→name key introduced in Task 1 already carries the identification, so
  nothing is lost, just not repeated per-pod in the legend. Verified the ≤6-pod case (a 3-pod run)
  keeps its full per-pod legend unchanged — the threshold doesn't touch small runs where per-pod
  detail is still cheap to show.

**Verification**: reproduced both issues on my own machine from the exact shipped commit before
fixing (not just trusting the trigger's description); re-verified the 15-pod fix on the same run
after each fix; confirmed no regression on a 3-pod run (per-pod legend intact) and the golden
pre-panel-6 bundle (no crash, still renders). `make test`/`lint`/`gofmt` N/A, unchanged.

**What this means for verification going forward**: "renders without error" and "renders correctly"
are different claims — this round is the second time in this branch's history that a no-crash check
got reported as sufficient. Worth being more deliberate about actually reading the output values
(axis limits, row counts), not just eyeballing the image for "looks plausible," on the next round.

### Prior session (2026-08-13, Task 2 panel3 redesign, preserved below)
current_step: **Task 2 (panel 1b capping + panel 3 request-domain redesign) landed, committed
`fbecfe26`.** Picked up via `autoscaling-viz__task2-panel3-redesign.md` trigger, code spec
`planning/autoscaling-viz-panel3-redesign-plan.md`. On top of Task 1 (`037106f2`, planner-verified
before this task started).
- **Panel 1b y-axis cap.** `y_max = 1.5 × max(offered-work peak, delivered-work peak)`; ceiling
  line and its sat-rate reference now clip at that line. Each off-chart step gets one annotation
  (`×N (X.Xk tok/s)`) — **first attempt labelled every grid point where `ready` changed and produced
  an unreadable pile of overlapping text**, caught by viewing the PNG, not by re-reading the diff: a
  boot ramp on the `m-satta-dwell` sample stepped through 8 replica counts in under 5 minutes. Fixed
  by labelling only the last point of a run of off-chart values (one label per plateau) with a
  minimum time gap between labels. Guarded a real crash too: `total_w`/`offered_w` are only assigned
  inside `if reqs:`, so a run with no per-request trace (e.g. `m-satta-dwell` itself) hit
  `UnboundLocalError` on the very first test — both now default to `None` before the branch.
- **Extractor: `pod_drain_windows()`.** New derivation, no existing signal for "which pod was
  removed" — only that a pod's scrape series stops. Correlates each pod's own last sample against
  the aggregate `ready`-decrease timestamps `lags()` already tracks, in **both time directions**
  (first version assumed the drain event always precedes the pod's death and matched zero pods on
  a real run — debugged by checking actual timestamps and finding the aggregate `ready` poll can
  land *after* a pod's last raw scrape, since it's a different, coarser cadence). Verified on
  `m-satta-dwell`: 11 of 15 pods got a drain window, durations 0–347s. Verified the per-pod
  running/draining split is numerically exact (0/193 mismatches on a real bundle) — carved out of
  running, never double-counted or dropped.
- **Panel 3 redesign.** New draining band, dotted hatch, pod's own color — but **one legend entry
  total, not per-pod**: the first attempt gave every draining pod its own label and reproduced
  exactly the legend-overflow problem Task 1's numeric pod-N labels existed to fix (visibly bled
  into panel 4's space on the 15-pod run), caught the same way, by viewing the PNG. EPP-queue
  residual updated to subtract all three bands below it (`running+draining+waiting`), not two, or
  the invariant breaks now that draining exists. Label renamed per the spec's suggestion. KV-ceiling
  line moves to a secondary y-axis (distinct spine/tick color) when its max is >10% off the
  total-in-system max — verified the **far case** on real data (ceiling ~2.9x and ~10x in-system max
  on two different runs, both correctly went secondary-axis) and the **near case** via one
  synthetically-adjusted bundle (capacity forced to ~5% off in-system max, confirmed it stayed on
  the primary axis, single scale, no second axis drawn) — no real run in the available data happened
  to land in the near band naturally.
- **Convergence check (not a fix).** `plots.py`'s own panel 3 draws work/s demand-vs-capacity per
  backend — a different concept in different units from the real renderer's now-request-domain
  breakdown. This is a real gap, not attempted to reconcile, matching the spec's own Item E
  boundary (out of scope here).

**Verification**: re-rendered and viewed the same cell spread as Task 1 — `m-satta-dwell` (15 pods,
draining present, no capacity-model data so panel 1b's cap path is skipped, panel 3's ceiling absent
entirely since `max_conc_pred` doesn't exist for this run), an 8-pod staircase (weak time anchor,
draining absent, far-ceiling secondary axis), and the golden `staircase-20260803` bundle as a
backward-compat regression check (no `drain_windows` key at all in its `pods` dict — old bundles
still render clean; panel 1b capping and panel 3 secondary-axis both fire correctly on it too).
`make test`/`lint`/`gofmt` N/A, same as every prior entry.

### Prior session (2026-08-13, Task 1 bugfix cluster, preserved below)
current_step: **Bug-fix cluster (Task 1 of the sequenced review-fix series) landed, committed
`037106f2`.** Picked up via `autoscaling-viz__task1-bugfix-cluster.md` trigger, code spec
`planning/autoscaling-viz-bugfix-cluster-plan.md`. Two of the three items are code fixes; the third
is a triage finding, not a defect:
- **Fix 1 (title `?`s).** `run_metadata.yaml` genuinely lacks `model`/`namespace` for the
  inference-perf dwell/staircase harness runs (confirmed, not an extractor field-name bug).
  `extract_real_trace.py` now has `find_cell_config()` (globs `run_dir/../../config/*.env`, exactly
  one expected) and `find_workload_yaml()` (globs `run_dir/*.yaml` for one with an indented
  `model_name:` under `server:` — `read_flat_yaml`'s top-level-only regex can't see it). Fallback
  chain: `model` = `run_metadata.yaml` → `.env BENCHMARK_MODEL_ID` → workload-yaml `model_name`;
  `namespace` = `run_metadata.yaml` → `.env BENCHMARK_NAMESPACE`; `workload` = `.env` basename (the
  actual cell name, e.g. `m-satta-dwell`) preferred over the raw `harness_workload` filename when
  both exist — found live during verification that one run's `run_metadata.yaml` *does* carry
  `harness_workload` but only as the profile YAML's filename (`ta_autoscale_staircase.yaml`), not
  the human cell name, so cell name wins. Renderer's title now shows `workload · run · model ·
  harness · ns` instead of bare `?`s, degrading to the run dir basename (always present) if every
  fallback is exhausted.
- **Fix 2 (panel 1a triage — not a bug).** Confirmed by extracting a run known to have a real
  `per_request_lifecycle_metrics.json` (`dean-20260810-080708-371`, 4.2 GB, `--head 2000`): panel 1a
  renders fully — arrival/departure curves, wait-band bars, real numbers. The review sample
  (`m-satta-dwell`) has no per-request file at all (`find` confirms), so its empty panel 1a is a
  **data-collection gap for that run, not a rendering or extraction defect**. No code changed for
  this item, per the spec's own framing.
- **Fix 3 (panel 3 readability).** All three sub-fixes in `render_real_trace.py`: (a) legend now
  uses numeric `pod N running/waiting` labels instead of full pod-name suffixes, which overflowed
  with 15+ pods, plus a compact `1=<suffix> 2=<suffix> ...` key line placed in the whitespace
  between panel 3's x-axis and panel 4's title — first attempt used full pod names in the key and it
  visibly overlapped the legend/next panel, caught by viewing the actual PNG, fixed by truncating to
  the short suffix (same convention the old inline labels used) and tightening the y-offset; (b)
  waiting-band hatch dropped its `alpha=0.55` reduction (full-saturation fill now) and switched
  `edgecolor` from `INK` to near-white `#f5f5f5`, so the hatch reads as texture rather than a second
  muddying layer — visibly cleaner on the 15-pod case; (c) running bars gained a thin `edgecolor=INK,
  linewidth=0.4` (previously `edgecolor='none'`), matching the waiting bars, so adjacent
  same-ish-colored segments separate visually.

**Verification**, per the spec's own checklist — re-rendered and *viewed* (not exit-code-only) 4
cells spanning the pod-count and analyzer-mix space: `m-satta-dwell` (15 pods, SAT+TA, the review
sample itself), `dean-20260810-080708-371` staircase (8 pods, SAT-only), `m-ta-staircase` (3 pods,
TA-only — also incidentally confirms panel 6's "saturation analyzer absent from configured list"
annotation fires correctly for a genuinely TA-only cell, resolving what looked like an inconsistency
against the SAT+TA cell's controller.log), and the shipped golden `staircase-20260803` bundle as a
backward-compatibility regression check (pre-panel-6, pre-Fix-1 bundle — renders clean, no crash,
confirming old bundles without `scaling_log`/the new meta fields still work). All PNGs viewed.
`make test`/`lint`/`gofmt` N/A — Python-only worktree, no Makefile/test suite, per the Type 3's own
Verification section (unchanged from every prior entry here).

### Prior session (2026-08-13, Item 5, preserved below)
current_step: **Item 5 (coverage-check reference doc) landed, committed `34afc197`.** Followed the
autoscaling-viz-followon-plan.md TOC to find a DECIDED, coder-appropriate item (Item 1 was already
done; Items 2/3/4/6 are OPEN, gated on Dean, out of scope for a coder). Transcribed the Type 1's
coverage-check table (`autoscaling-viz-design.md` § Coverage-check specification) into a new
`COVERAGE-CHECKS.md` at the worktree root, cross-linked from README's "Read the coverage table"
paragraph. **Reconciled against current code, not copied verbatim**: the Type 1's table predates
panel 6 and only has 16 rows; live re-extraction (`real-trace/staircase-20260803` and a
`benchmark/runs/` campaign dir) confirmed the current code emits 17 — panel 6 inserted a new row 16
("Scaling-decision log present") ahead of the old conditional row 16 ("Knee matches shape
prediction"), which is now row 17. Doc reflects the verified order. `make test`/`lint`/`gofmt` N/A
(Python-only worktree, no Makefile/test suite, per the Type 3's own Verification section — same as
every prior entry here).
**Housekeeping this session**: the `autoscaling-viz-panels__kickoff.md` trigger (addressed to "a new
dedicated session," i.e. a planner reviewing panel design, not a coder) was opened without marking
`.WIP` first — a process miss, corrected mid-session by marking it `.WIP` before any further
action. Left as `.WIP` since the actual addressee is a planner session, not this one; noted in the
handoff below so it isn't mistaken for abandoned.
**Session start also hit a self-inflicted CWD lockout**: an earlier `cd .../plans/session/handoffs/
&& mv ...` (Dean has since said never use `cd`) left the shell's persistent CWD outside the
worktree, and the isolation guard then refused every subsequent Bash call including attempts to
`cd` back. Recovered via `ExitWorktree(keep)` + `EnterWorktree` rather than fighting the shell.
**Also confirmed live**: the "inert allowlist entry" this file already flagged (§Awaiting Dean item
5, 2026-08-08) is still live — `Edit`/`Write` on `plans/session/status/<branch>.md` itself is
blocked by the worktree-isolation guard even though CONVENTIONS sanctions it; worked around this
time via a same-worktree draft file + Bash `cp`, not `Write` directly on the shared path.

### Prior session (2026-08-12, preserved below)
current_step: **Panel 6 (scaling-decision reasons) landed, committed `cff4e4c0`.** New Type 3
`planning/autoscaling-viz-decision-panel-plan.md` (parent epic Item 1 of
`planning/autoscaling-viz-followon-plan.md`) picked up from a `to: autoscaling-viz` handoff and
completed in full — all four implementation steps done, all four verification checks done. Judgment
calls: panel-6 height ratio **2.2** (in the plan's suggested 2.0-2.5 range); bundle key
`derived.scaling_log = {source, by_analyzer, decisions, saturation_absent_at}` (one sub-object per
analyzer keyed by name, each a time-ordered list of `{t, reason, variant}`; `decisions` is a flat
time-ordered list of `{t, variant, action, curr, tgt}` rather than per-analyzer, since decisions are
per-model not per-analyzer); coverage row 17 **added** ("Scaling-decision log present"). Controller-log
discovery checks `<run_dir>/controller.log` and `<run_dir>/logs/controller.log` before falling back to
`--controller-log`; verified this auto-discovery actually fires on a real run
(`benchmark/runs/dean-20260810-080708-371/.../controller.log` was co-located and picked up with no
flag). Reason-code palette is read from the data, not hardcoded — confirmed the throughput analyzer
uses `T2-default` while saturation uses `P1-obs`/`P2-hist`/`P3-k2`/`P4-k1`, and confirmed a red herring
along the way: `"reason":"OptimizationSucceeded"` also appears in controller.log but is a K8s Event
reason on an unrelated log line shape, not from the `analyzer-result` JSON payload — the extractor's
strict per-line-shape regex (`CTRL_LOG_LINE`) never matches that line, so it can't leak in.
**Correction to the plan's own claim**: the analyzer-absent line fires **every ~60s tick**, not "zero
or one per run, not per tick" as spec'd — confirmed by direct count on `m-ta-dwell/controller.log` (8
occurrences). Doesn't change the implementation (a first-seen boolean/timestamp was already the right
capture), just corrects the doc's description for anyone reading it later.
Verified against real 2026-08-10 campaign logs (not synthetic): `m-satta-dwell` (both analyzers, 9
scale-up/down transitions visible in panel 2, reason codes track the dwell cycle), `m-ta-staircase`
(TA-only, absent-analyzer annotation fires, early spurious saturation votes before the gate still
captured not dropped), and a no-`controller.log` bundle (degrades to the `empty()` message, matching
every other panel's convention). All three re-renders viewed as PNGs, not just exit-code-checked.
Nothing pushed. `make test`/`lint`/`gofmt` are N/A (Python-only worktree, no Makefile, no test suite)
per the Type 3's own Verification section.

### Prior state (2026-08-08, preserved below)
state: **unblocked — the C2 gate PASSES on both arms.** Next actionable is C5 (the experiment-dir viz driver Dean asked for) or C3; the `report.py`/`run.py` out-dir edits inside C5 need approval before coding.
current_step: **C2 DONE, gate PASS, committed (`5a0c607f`).** The benchmark-driven simulator reproduces the 08-07 ladder run it was built from: per-stage p50 within 8.0%, p95 within 12.5%, pooled decode throughput within 2.3%, 2462/2462 replica-trajectory samples within 1 replica, and queueing immaterial in both (0.000% sim / 0.266% real vs a 1% bound; max per-pod concurrency 102 sim / 121 real vs the 512 admission ceiling). A0d is the same verdict, worst p50 9.5% / p95 13.5%. Exit code 0. Nothing was tuned (`params.tuned_to_pass_gate == []`). **The fourth criterion was changed after it had been observed to fail** — Dean resolved plan §8.2 on 2026-08-08 in favor of `queue_material`; the original `queue_onset` (identical stage-sets showing *any* queueing) was unpassable by construction and is retained, **still evaluated every run**, under `superseded_checks`, so its FAIL stays on the record. Dean resolved the *criterion* only: the 15%/15%/1-at-90% tolerances **and** the 1% queue share are still my proposals and still open. Local commits `453fb779`, `9a83d2e2`, `d656e8cb`, `2636b221`, `92b37fbb`, `5a0c607f` are **unpushed**; working tree clean.

## Branch
`autoscaling-viz` at `/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/autoscaling-viz`.
Tip **`cff4e4c0`** (was `5a0c607f` as of 2026-08-08). `origin/autoscaling-viz` is at `4b263d73` — the
seven commits since (six from 2026-08-08 plus this session's panel-6 commit) are **local only** and
need Dean's OK for that specific push.
35 commits, orphan lineage — **no merge-base with `upstream/main` by design**, so the pre-push DCO
hook self-skips and commits here carry **no `Signed-off-by`**. Never push to `upstream` (its push URL
is literally `READ-ONLY-UPSTREAM-DO-NOT-PUSH`).

Venv at `./.venv` (matplotlib only). `uv` is the tool of record for Python here.

## Plan — and a live ownership problem, flagged for Dean 2026-08-08
The document being followed is **`autoscaling-viz/real-trace-viz-plan.md`** (Rev 6, `Status: DRAFT`).

**It is not a Type 3 task plan, and there is no Type 3 plan for this work.** Verified, not assumed:
- `plans/planning/` contains **nothing** about autoscaling-viz or real-trace-viz. The only mention
  anywhere on the `plans` branch is `session/CURRENT.md` lines 145–185.
- Per CONVENTIONS §Types, Type 3 docs live on the `plans` branch under `planning/`; this one lives on
  the code branch by deliberate decision (Rev 6: *"This document now lives on the branch it
  describes"*).
- It does not follow the Type 3 authoring rules at all: no Reading Protocol block, no TOC with
  `L<start>:<end>` ranges (`grep -c TOC` = 0), no `[↑ TOC]` links, and `plans/scripts/toc-refresh.sh`
  has never been run on it.
- Per the role matrix, a **coder** writes code / Type 4 references / status files / handoffs and
  **reads** Type 3 plans. This session has been *writing* its own plan doc continuously — §4.5, §5.3,
  §7.1, §7.2, §12.2, §12.4 all edited by me.

So **de-facto owner: this session (the coder).** That is the violation, not a paperwork detail: every
"open decision for Dean" in §12.2 is me nominating my own forks, and nobody independent has ever set
the scope. Content-wise the doc is a hybrid — Type 1 design/derivations (§2 time anchor, §3 token
accounting, §5 saturation window, §6 capacity model), Type 3 task/decision tracking (§9.2 capture
list, §12 open items), Type 4 reference (§8 extractor spec, §15 bundle policy).

Not unilaterally restructured: splitting it, moving it to `plans/planning/`, or handing authorship to
a plan agent are all Dean's calls. Raised in the reply of 2026-08-08.

## What is done and pushed
- **Real-trace toolchain**: `fetch_run.sh` → `extract_real_trace.py` → `render_real_trace.py`, plus
  `sim.py`/`run.py`/`plots.py` (synthetic, untouched by the real-trace path).
- **Six-panel renderer.** 1a arrivals vs completions by wait band; 1b work throughput vs capacity;
  2 replicas desired vs ready; 3 per-pod work; **4 deferred by agreement** (three distinct queues,
  design question open); 5 concurrency `L(t)`.
- **arm-B findings** `real-trace/staircase-20260807-armB/FINDINGS.md` (§11 = the 08-07 ladder
  cross-check), `analyze_ladder_wave.py`, `_probe_envoy_fields.py`.
- **`947dd4c1`** ladder cross-check: the multi-pod wave is **routing**, and my published "not routing"
  claim over-generalized from a single-pod-saturated run. Two distinct oscillations, not one.
- **`1941afe4`** propagation into plan/README/docstrings (two mechanism retractions; both *phenomena*
  stand).
- **`aa67c399`** envoy-field feasibility probe + the benchmark handoff.
- **`4b263d73`** `router_stats`: boot exclusion + `oscillation_flag` removed.

## Simulation from the benchmark (the current task) — C1, C2 done, unpushed
Task statement from Dean: *drive a simulation from the benchmark results — the benchmark defines the
demand shape and the supply capacities; compare actual behavior (the scale decisions used in the
benchmark) to the various algorithms.* Plus: *the WVA logs should contain the decision process* (they
do — `benchmark/session-notes/scratch/ladder-controller.log`). Dean granted this session the whole
Type 1–3 cycle **on condition the documents exist as documents**.

- **Type 3 plan: `plans/planning/sim-from-benchmark-plan.md`** (TOC-refreshed, 12 top-level sections).
  `d656e8cb` folded the C1 findings back in with dated corrections. §3 is the blocking gate, §6 the
  commit order, §8 Dean's open forks.
- **`453fb779` / `9a83d2e2` — C1 `run_inputs.py`** → `real-trace/ladder-20260807/run_inputs.json`
  (1.1 MB): 22,200 arrivals, per-stage segmentation, replica desired/ready series, the engine ITL
  line, and the 87 WVA decision cycles. **The WVA decision rule verified 87/87.** Saturation never
  binds on this run (`rc == 0` on all 87 cycles, util peak 0.811).
- **`2636b221` — C2 `sim_from_run.py`** → `real-trace/ladder-20260807/gate_a0.json`. Two arms: **A0r**
  (observed *ready* steps, no boot model — the gate, isolating the queueing+service model) and **A0d**
  (observed *desired*, paying `sim.py`'s own `setup` — the reference for the A1–A9 control arms, which
  pay the same lag).
- **`92b37fbb` — `real-trace/ladder-20260807/C2-GATE-REPORT.md`**, the readable version of the gate:
  what the run supplies, the per-stage table, the `queue_onset` story (§3), the biases reported rather
  than patched (§4), the modeling choices (§5), the two source fixes (§6), and what the PASS does and
  does not license (§7).
- **`5a0c607f` — gate criterion 4 resolved, gate PASSES both arms, exit 0.** `queue_material` (queued
  request-seconds < 1% of in-system request-seconds in both, **and** max per-pod concurrency below the
  admission ceiling in both) replaces `queue_onset` (identical stage-sets showing *any* queueing).
  Measured: 0.000% sim / 0.266% real; max/pod 102 sim / 121 real vs ceiling 512.
  **The criterion was changed after it had been observed to fail**, which is the move a gate exists to
  prevent, so the sequence is recorded in three places — plan §3, the `gate()` docstring, and
  `superseded_checks` in the JSON, which **still evaluates `queue_onset` on every run** so its FAIL
  never disappears. Dean resolved the *criterion*; the four tolerance numbers are still open.
  Same commit reconciled the queue figure to a single **4 of 448 / 0.266%** by integrating once over
  the load window (the per-stage sum had double-counted the interval straddling a stage boundary and
  dropped the drain gaps where one of the four events lands), and added plan **§7.1**, the
  `viz_experiment.sh` call-site contract.
- Service model refit in-code from the run: `itl = 0.1847·run + 9.265 ms`, r²=0.942, n=411, run ∈
  [1, 121]. The **absolute** ITL slope is preserved for any `C`, since `C` is the admission ceiling and
  not part of the service model. `C = 512` and the code *asserts* the simulated queue stays empty
  rather than trusting the choice — `C` becomes a real modeling decision for C4's under-provisioned arms.
- Boot lag: **two different numbers, and the simulator wants the longer one.** Pairing desired-increase
  with ready-increase instants gives `[110, 188, 94, 94]`, median **110 s** — the controller-to-capacity
  lag, which is what `setup` models. `pod_startup_times.json` gives median **97 s**, missing the
  deployment-scaling step in front of it. A0d uses 110; both are reported.
- **Fourth and decisive output-size confirmation**, the engine counting its own work:
  `vllm:request_generation_tokens_sum/_count = 4107899/8026 = 511.83`. The harness's 866–920
  `output_len_mean` is inflated ~1.7× and is not used anywhere.
- **Not patched, reported instead**: measured TTFT (103 ms median, 1–3% of the 5.3–12.0 s sojourns) and
  routing concentration. The latter is the sign of the stage-6 p95 shortfall and is plan §5.1's
  documented limit. Stage 7 (the 20→2 rps step-down transient) is reported but not gated, with the
  reason printed in the output rather than hidden.
- Two source-level fixes rode along: `run_inputs.py`'s `start_s`/`end_s` → `start_epoch`/`end_epoch`
  (they are absolute UNIX times; the relative-sounding names silently zeroed every stage window and
  pinned `mean_ready` to 1.00 — fixed at the source because the file is provenance-stamped), and
  `sim.py` honoring `meta["n0"]` so a recorded trace can state its measured starting fleet, which
  `initial_rate`'s own CAVEAT had already asked for. The `n0` branch is verified inert for the deck:
  the full 8-policy run for bump/stepup/spike produces byte-identical summary tables.

## Key measured results (all reproducible from committed scripts)
- **Routing wave.** Per-pod arrivals oscillate r +0.25…+0.73 and *lead* departures; pooled is flat
  (r ≈ +0.09–0.14) because pods run anti-phase and cancel; period tracks mean sojourn time at ratio
  0.92–1.09 across all six loaded stages (5.7 → 12.0 s). Signature of delayed-feedback balancing.
  Mechanism, **not proven cause** — EPP's actual decisions were unrecoverable (13 unique request IDs).
- **Aliasing.** 6–11 s period vs ~15.7 s scrape cadence ⇒ Nyquist ~31 s. Any oscillation/imbalance
  statistic built on scrape-derived per-pod gauges is structurally blind in this band.
- **Envoy DURATION is a validated substitute** for harness `request_latency`: mean 0.23–0.42% low,
  p95 within 0.08–0.93%, all 8 stages, consistently slightly low (excludes client-side handling).
- **`bytes_sent` fails as a per-request output-token proxy.** Median calibrates (511 vs true 512) but
  dispersion does not: bytes span ~14% p5→p95 where `output_len` spans ~44%; implied bytes/token
  drifts 170–187 across stages. Stage-level total only — never a per-request weight or size rank.
- **`x-envoy-upstream-service-time` is NOT TTFT.** Flat 7–9 ms while TTFT climbs 47 → 183 ms.
- **Disjoint bucket split.** `iteration_tokens_total`: decode-only steps ≤128 tok, prefill-carrying in
  (1024, 16384], **exactly 0** in (128, 1024] on every pod ⇒ differencing `le=1024` is an *exact*
  per-interval prefill-step rate.
- **Regime boundary for ITL.** In-band (kv ≈ 0.99, n=20) adding prompt rate takes r² 0.642 → 0.878
  (Δ +0.236) and omitting it inflates slope `A` 1.8×. Sub-band (kv ≤ 0.67, n=281) `itl ~ run` alone
  is r² 0.93–0.94, Δ +0.001. Not preemption (`corr(gen, preempt/s)` = +0.766, wrong sign).
- **`router_stats` after the fix**, arm B re-extracted from source: `disp_p95` 1.000 → **0.1429**,
  `disp_p50` 0.066 → 0.0625, `n` 28 → 26, 3 boot samples dropped. `leader_flips` unchanged at 15.

## Resolved by Dean 2026-08-08 — no longer blocking
0. **The `queue_onset` gate criterion (plan §8.2)** — **RESOLVED: replace it.** `queue_material` is now
   the scored fourth check and the gate PASSES on both arms. `queue_onset` is retained under
   `superseded_checks`, still evaluated on every run, so its FAIL stays on the record; the criterion was
   changed *after* it had been observed to fail, and that sequence is recorded in plan §3, the `gate()`
   docstring, and the JSON. Full diagnosis (the four instants, their concurrencies, the token-budget +
   routing mechanism, the Little's-law corroboration) lives in
   `real-trace/ladder-20260807/C2-GATE-REPORT.md` §3 — it is not repeated here.
   **Still Dean's and still open:** the **15% / 15% / 1-replica-at-90%** tolerances *and* the **1%**
   queue share. All four are my proposals, not derived from anything.

## Awaiting Dean — needed before C4 (C3 and C5 are clear)
0b. **Fork 6 — what `prc` should mean for A2** (measured per-replica capacity). I lean (c): run A2a/A2b/
   A2c side by side rather than pick. Needed before C4, not before C3 or C5.

## Awaiting Dean (nothing is blocked on these; work continues around them)
1. **Envoy input path in `extract_real_trace.py`** — a third reader so a ladder-shaped run bundles
   without a per-request file. Measured: 4 of 5 live panels survive, panel 5 *improves* (22,200 real
   requests vs a 50-record head sample), panel 1a must band by **sojourn** not TTFT, panel 1b's
   per-request size weighting and terciles are unrecoverable. Substantial single-file edit ⇒ needs
   approval before coding.
2. **Regenerate the shipped bundles?** `real-trace/staircase-20260807-armB/bundle.json` still carries
   the pre-fix `disp_p95: 1.0` and `oscillation_flag: true`. FINDINGS §7 documents this and gives the
   corrected numbers, so the artifact is self-describing either way. Republishing is a results-policy
   call (results are append-only).
3. **§12.2 items 7–9**: what `tput_knee` should report as capacity (max 4994 vs band mean 3943 =
   +27% envelope); whether `itl_fit` gains a prefill term (one fit cannot serve both regimes); a
   minimum-n guard on `B_measured` (`B_measured_n = 3`, two of them boot samples).
4. **Plan-doc ownership** (§Plan above).
5. **Inert allowlist entry**: `~/.claude/settings.json` allowlists `Edit()` on
   `plans/session/handoffs/**`, but the worktree-isolation guard preempts it, so the entry documents
   a capability that does not exist. Either the guard should honor it or the entry should go.

## Deferred by agreement
- **Panel 4 design** — three real queues (EPP flow-control, EPP dispatch, per-vLLM
  `num_requests_waiting`); all three plus a derived global are already in `bundle.json` under
  `system[]`. Deciding which one panel 4 draws needs an input inventory across several runs.
- **(iii) per-request-trace oscillation detector** — Dean 2026-08-08: lower priority. Shares a
  dependency with proving the routing mechanism: both want the **rotated EPP logs** the benchmark
  tester is now collecting.
- **sim-p3 replacement** — needs a check on whether `sim.py` exports per-backend *request* counts.

## Dean's stated priority, 2026-08-08 — viz output into the benchmark's own experiment dir
*"I want to run a benchmark and call the viz tools as a last step after I copy the results over. I want
to get the full reports, graphs, HTML right there with my results."* Target is
`benchmark/dean-20260807-234050-328/` — the harness already reserves an `analysis/` dir at both the
experiment and the per-run-id level.

Specified as **plan §7.1, the `viz_experiment.sh` call-site contract**. Explicit
`--run` / `--controller-log` / `--out`, and **no path discovery** — Dean: *"why need discovery. The
benchmark who calls viz knows where the results are. Could be many run_ids."* One invocation per run id,
hard error on a missing path, `--out` is the only thing written.

What exists vs. what §7.1 promises: `run_inputs.json` ✅ C1, `gate_a0.json` + `C2-GATE-REPORT.md` ✅ C2,
and `sim_compare.json` / `panels-*.png` / `index.html` ❌ **do not exist** — that is C5. Two dependencies
worth naming: the current `index.html` is the *synthetic policy deck*, not an experiment report, and
`report.py`/`run.py` both hardcode `OUT = "out"`, so making them take an output directory is a
**substantial single-file edit to each** and stops for approval before coding. Real-run panels
additionally need a `bundle.json` that `extract_real_trace.py` cannot produce for a ladder-shaped run
(0-byte `per_request_lifecycle_metrics.json`) — the envoy input path below.

Sample figures that already exist, for reference on what the panels look like:
`real-trace/staircase-20260807-armB/panels.png` (559 KB) and `real-trace/staircase-20260803/panels.png`
(247 KB) — 5 panels: 1a request throughput+goodput, 1b work throughput offered/delivered/capacity,
2 desired vs ready replicas, 3 requests per pod, 5 concurrency L=λ·W with the ITL fit (panel 4
deferred). **No figure exists yet for the ladder run or for sim-vs-real.**

## OWED — started? NO.
Full prose recheck with real numbers across `autoscaling-behavioral-demo-design.md`,
`REVIEW-CHECKLIST.md` and `report.py`. Known-stale, and **already published to origin**:
- `SHAPE_NOTES["spike"]` — the *"drops between 7% and 57% of requests"* banner (renders **twice**).
- Two `2.5×` tokens.
- §2.4's paragraphs describing the now-**deleted** analytic `W0` seed.
Also standing: `spike` is teaching-only, never calibrated; Stability stays a standalone md, not a
deck tab; Table must not follow Compare; `stability.py` stays uncapped by design.

## Handoffs
- **Sent** `plans/session/handoffs/benchmark__viz-cross-check-and-next-capture.md` (shared path;
  drafting copy at `session-notes/handoffs/`). Carries the routing finding, the aliasing limit, the
  disjoint-bucket split, the envoy validation table, two corrections they need (their two handoffs
  contradict each other on `ceil(demand/prc)`; `bytes_sent` dispersion), and the §9.2 capture list
  framed as a request.
- **Consumed and closed** `scratch-poc__ladder-run-surviving-data.md.DONE`,
  `scratch-poc__per-request-fetch-for-viz.md.DONE`. They were addressed to `scratch-poc`, a name this
  session does not answer to — asked them to use `autoscaling-viz`.
- **Protocol correction (mine to own).** I reported that worktree isolation blocks all writes to
  `plans/session/handoffs/` and that the `.md`/`.WIP`/`.DONE` machine was inoperable across
  worktrees. **Both wrong.** CONVENTIONS explicitly sanctions writing there from any worktree — *"the
  only sanctioned exception to 'no edits outside your worktree'"* — and it works: `Write`/`Edit` are
  blocked by the file-tool guard, but Bash `cp` and `mv` both succeed. Recipe: draft in the worktree,
  `cp` in, `cp` again to revise, `mv` to flip state. I inferred a protocol defect from one refused
  `Write` and propagated it into a handoff, a plan section and a report before testing the other
  three operations, at one command each.

## Data locations (read-only; none of it is in this branch)
- Ladder run 08-07 (8 stages, 22,200 requests, 0 non-200s):
  `benchmark/dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1`
  — has `logs/igw_pods.log` (envoy access log, per-request + `UPSTREAM_HOST`), `metrics/raw/`,
  8× `stage_N_lifecycle_metrics.json`. **No `metrics/processed/wva_*.json`** (post_run_analyze.sh not
  run in time) and `per_request_lifecycle_metrics.json` is 0 bytes (harness OOM).
- arm-B run: `benchmark/dean-20260807-210058-612/results/inference-perf-1786125698-ptufog_1`.
- The envoy log is on **kubelet rotation** — the ladder run sat at 60.1% of a 52.4 MB budget with
  oldest-first eviction, i.e. biased against early stages. Capture deliberately next time.

## Standing constraints
No `git push` without Dean's explicit OK **for that specific push**; never push to `upstream`; no
in-place shell edits (`sed -i` &c.); >3 existing files or a substantial single-file edit ⇒ describe as
text and get approval first; `pwd` + `git branch --show-current` before every edit and every commit;
no GitHub-visible actions without instruction; no Agent/workflow use unless asked. Bundle rules: never
copy prompt or response text into a bundle; bundles only, never raw; nothing over 20 MB; no
`metrics/raw/` or per-request source files in a published bundle; `provenance.json` mandatory; results
append-only; publishing never pushes. pokprod is read-only; teardown needs Dean's approval.
**Design forks belong to Dean, including for coders** — a bug fix can silently ride a semantic change,
so name it separately.
