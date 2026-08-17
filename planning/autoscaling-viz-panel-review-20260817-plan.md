# Panel review 2026-08-17 (good-panels visual QA) — Code Spec (Type 3)

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

**Status:** READY

**Owner:** autoscaling-viz coder (Bob, `coder-auto` mode). Source: Dean's direct visual review of 4
of the 16 `good-panels.png` outputs from the 2026-08-17 classification pass
(`autoscaling-viz-good-panels-classification-plan.md`), plus one item found while root-causing a
review comment (title bug). All items independently confirmed against actual renders and/or source
code before this spec was written — see each item's own evidence.

## TOC {#toc}

- [Item 1 — title shows run ID only, not workload {#item-1-title}](#item-1--title-shows-run-id-only-not-workload-item-1-title) L27:50
- [Item 2 — panel 1a corner-text overlaps the panel title {#item-2-p1a-overlap}](#item-2--panel-1a-corner-text-overlaps-the-panel-title-item-2-p1a-overlap) L51:61
- [Item 3 — panel 3 per-pod color-key strip sits too far right {#item-3-p3-colorkey}](#item-3--panel-3-per-pod-color-key-strip-sits-too-far-right-item-3-p3-colorkey) L62:80
- [Item 4 — panel 4 header extra blank line {#item-4-p4-header}](#item-4--panel-4-header-extra-blank-line-item-4-p4-header) L81:90
- [Item 5 — pod sort order needs a tie-breaker {#item-5-pod-sort-tiebreak}](#item-5--pod-sort-order-needs-a-tie-breaker-item-5-pod-sort-tiebreak) L91:106
- [Item 6 — panel 5's in-system line should align with panel 3's buckets {#item-6-p5-alignment}](#item-6--panel-5s-in-system-line-should-align-with-panel-3s-buckets-item-6-p5-alignment) L107:119
- [Item 7 — panel 6: distinguish genuinely-silent analyzer ticks from no data at all {#item-7-p6-silent-ticks}](#item-7--panel-6-distinguish-genuinely-silent-analyzer-ticks-from-no-data-at-all-item-7-p6-silent-ticks) L120:145
- [Item 8 — panel 3 pod-removed signal over-fires on dwell-cycling workloads {#item-8-p3-drain-overfire}](#item-8--panel-3-pod-removed-signal-over-fires-on-dwell-cycling-workloads-item-8-p3-drain-overfire) L146:173
- [Explicitly out of scope {#out-of-scope}](#explicitly-out-of-scope-out-of-scope) L174:186
- [Verification {#verification}](#verification-verification) L187:218

## Item 1 — title shows run ID only, not workload {#item-1-title}

Confirmed on `dean-20260810-064736-555`: rendered title is bare `dean-20260810-064736-555`, dropping
workload/model/harness/namespace entirely, even though `bundle.json`'s own `meta.workload` correctly
holds `m-satta-staircase`. Two independent causes, both real:

1. **One-off cause, already done, no action needed here.** The batch script Bob wrote for the
   good-panels pass (`/tmp/batch_extract_render.py`, not part of this repo) had its own
   `get_workload_name()` look for `REPORT.md` at `results/<leaf>/REPORT.md` — one level too deep.
   `REPORT.md` actually lives at the run root, `benchmark/runs/<run>/REPORT.md`. The lookup silently
   failed and fell back to the run ID, which was then passed as `--title <run_id>`.
2. **Real defect in `render_real_trace.py`, needs fixing.** `render.py:391`:
   `head = title or (f"{workload + '  ·  ' if workload else ''}{run_id}  ·  " ...)`. Any non-empty
   `--title` value **fully replaces** the entire composite string — it isn't a workload override,
   it's a whole-title override. This is a footgun: a caller who passes a workload name (a
   reasonable thing to want) loses the run ID/model/harness/namespace entirely, with no error or
   warning. Fix: make `--title`, when provided, substitute only the workload segment of the
   composite (i.e. treat it as an explicit `workload` override, not a full head replacement) —
   `head = f"{title + '  ·  ' if title else (workload + '  ·  ' if workload else '')}{run_id} · ..."`
   or equivalent. Confirm the CLI help text (`ap.add_argument('--title')`, ~line 1522) documents the
   corrected semantics.

[↑ TOC](#toc)

## Item 2 — panel 1a corner-text overlaps the panel title {#item-2-p1a-overlap}

Confirmed visually on `dean-20260810-064736-555`: panel 1a's left-side title ("1a · request
throughput + goodput quality  (bars: ...)") and its right-side corner text ("requests: N offered, N
cut off at run end, N% good (<30s)") collide around the panel's horizontal center when both are
long. **Low priority per Dean.** Fix: shorten the left-side title text (the `(bars: ... curves:
...)` parenthetical is the obvious trim candidate) rather than touching the right-side corner text,
which carries real per-run numbers that shouldn't be truncated.

[↑ TOC](#toc)

## Item 3 — panel 3 per-pod color-key strip sits too far right {#item-3-p3-colorkey}

The per-pod color-key strip (`render.py:1038`, `d.inset_axes([1.12, 0, 0.03, 1], ...)`) sits at
`x=1.12` in the panel's own axes-fraction coordinates — outside the panel's right edge, separated
from the main plot by a visible gap, unlike panel 4's KV-heatmap colorbar
(`render.py:1188`, `fig.colorbar(...)`) which sits close against its own panel. Dean's ask: bring
panel 3's strip in, matching panel 4's tighter, more integrated feel.

The `1.12` value was itself a prior fix (see the comment immediately above it, `render.py:1032-1036`)
— it was originally at `1.02` and collided with panel 3's own secondary y-axis ticks/label, which
occupy roughly `x∈[1.0, 1.08]`. Moving the strip inward without reopening that collision means either
(a) narrowing/repositioning the secondary axis first, or (b) placing the strip in unused vertical
space rather than purely by shrinking its x-offset, or (c) adopting the same `fig.colorbar`-style
mechanism panel 4 uses if that naturally sits closer without the collision. Coder's call on the
exact mechanism; verify the fix against a 15+-pod run (the case that originally motivated `1.12`) to
confirm the secondary-axis collision doesn't reopen.

[↑ TOC](#toc)

## Item 4 — panel 4 header extra blank line {#item-4-p4-header}

Confirmed visually on `dean-20260810-064736-555` and others: the pod-number-to-name key text above
panel 4 ("1=d9w4f 2=qw5dx 3=6drrt") has a visible extra vertical gap between it and panel 4's own
title, wider than the equivalent gap elsewhere in the figure. Locate the text-placement call for
this key (likely near panel 4's own setup, analogous to panel 3's `d.text(0.5, -0.14, key, ...)` at
`render.py:1018`) and tighten the vertical offset to match the spacing convention used elsewhere.

[↑ TOC](#toc)

## Item 5 — pod sort order needs a tie-breaker {#item-5-pod-sort-tiebreak}

`render.py:715-717` (panel 3) and `:1083-1084` (panel 4) both sort pods by
`min(s['t'] for s in kv[1]['series'])` — first-appearance time — with **no tie-breaker**. When two
or more pods scale up in the same tick (a common case for batched replica creation), their relative
order is whatever Python's stable sort happens to preserve from dict-iteration order, not anything
meaningful. Dean's ask: break ties by **scale-down time** — among pods with equal first-appearance
time, the one that scales down later sorts first (or last — confirm which reads as "older always on
bottom" per the existing panel 3 stacking convention, `Item AB` in
`autoscaling-viz-warmup-anchor-and-panel-polish-plan.md`). Scale-down time for a pod is its own last
sample's timestamp (or its matched drain window's start, if using `pod_drain_windows()` output —
coder's call on which is more meaningful, but be consistent between panel 3 and panel 4 since they
share this ordering by design). Apply the same tie-breaker at both sort call sites.

[↑ TOC](#toc)

## Item 6 — panel 5's in-system line should align with panel 3's buckets {#item-6-p5-alignment}

Dean's ask: panel 5's `in system` line (`L(t)`, red) should visually align with panel 3's own
stacked-bar buckets — currently it reads as offset from them. Both panels resample onto the same
`grid`/`GRID` (2.0s step, `render.py:92,374`) and share `t0`, so investigate whether panel 3's bars
are drawn centered on each grid tick (bar center = tick) while panel 5's line samples at the tick
edge, or a similar half-step mismatch — check `ax.bar()`'s own `align` parameter on panel 3 against
however panel 5's line x-values are computed. Fix whichever side is inconsistent with the other;
confirm by re-rendering a run with a sharp step (e.g. a boot ramp) and checking the visual alignment
directly, not just the numbers.

[↑ TOC](#toc)

## Item 7 — panel 6: distinguish genuinely-silent analyzer ticks from no data at all {#item-7-p6-silent-ticks}

Confirmed on `dean-20260814-053822-692` (and likely `dean-20260813-005321-943`,
`dean-20260810-092644-320` — same symptom flagged by Dean, not independently re-verified on those
two but sharing the calibration-probe workload shape): the `throughput` (TA) line in panel 6 stops
at t≈850s while the run and `saturation`'s own line continue to ~1080s.

**Root-caused to the source, not a rendering defect — but the render gives no visual cue.** Traced
via `controller.log`: TA genuinely logs `"variants": []` (no variant, no `prc`) every tick for the
run's final ~360s — a real behavior, separately reported as a controller-side finding
(`plan__ta-prc-loss-on-idle-blocks-scaledown.md`, not this scope's to fix). The extractor
(`render.py:1321-1323`'s filter, mirrored in whatever produces `by_analyzer` in `extract_real_trace.py`)
correctly drops ticks with no `prc` — there's nothing to plot. **The problem is purely that this
looks identical to "no data ever existed here."**

This is a distinct case from the existing "absent, not voting" dashed-line treatment
(`render.py:1335-1340`), which fires when an analyzer isn't in the *configured* list at all but
still logs real data. Here the analyzer **is** configured and voting earlier in the run, then goes
silent (empty `variants`) for a stretch. Add a visual cue for this case: e.g. a short faded/dotted
"tail" segment at the last real value extending to the point the line stops, or a small annotation
("no variant reported after t=X") — coder's call on exact treatment, but it must be visually
distinct from both the existing absent-analyzer dashing and a plain missing-controller-log
`empty()` degrade. Verify against `dean-20260814-053822-692` specifically.

[↑ TOC](#toc)

## Item 8 — panel 3 pod-removed signal over-fires on dwell-cycling workloads {#item-8-p3-drain-overfire}

Confirmed on `dean-20260813-013728-756` (`m-sat-dwell`, 18 pods): the "pod removed near a
scale-down event" hatch marks **10 of 18 pods (55%)**, against only **6 real `desired` step-downs**
across the whole run. `pod_drain_windows()`'s own docstring
(`extract_real_trace.py:935-967`) already documents this as a loose correlation by design
(`DRAIN_MATCH_WINDOW_S = 120.0`, proximity-based, not a true per-pod removal signal) — this is not a
newly-discovered bug in the matching logic itself, but confirmation that the 120s window is too
generous for a workload that cycles scale-up/down repeatedly and densely (a dwell profile), where
many pods' natural end-of-life coincidentally falls within 120s of *some* drain event without
actually being that event's drain.

**Do not silently tighten `DRAIN_MATCH_WINDOW_S` without checking regressions** — a previous task's
own verification (`autoscaling-viz-drain-window-fix-plan.md`) tuned related matching behavior
carefully against real data; changing the window naively could reintroduce the false-negative
problem that work fixed. Options, in order of preference: (a) make the window duration-aware (e.g.
scale it against the run's own scale-event frequency, so a dwell run with frequent transitions gets
a tighter window than a staircase run with few), (b) add a corroborating signal beyond timing
proximity if one exists (check whether `replicas`' own per-transition pod-count delta can
disambiguate which specific pod(s) a given step-down actually removed, vs. just "some pod ended
near this time"), (c) if neither is feasible cheaply, at minimum document the known
over-firing-on-dense-cycling-workloads limitation more prominently (the render's own label already
says "not necessarily draining -- see docs," but doesn't quantify how often that hedge matters).
Bring findings back via handoff before committing to (a) or (b) if the fix isn't obviously safe —
this touches logic another task already tuned carefully.

[↑ TOC](#toc)

## Explicitly out of scope {#out-of-scope}

- **The TA/PRC-loss root cause itself** (why TA stops reporting a variant once demand disappears) —
  WVA controller code, not this worktree. Tracked in
  `plan__ta-prc-loss-on-idle-blocks-scaledown.md`. Item 7 above is the viz-side symptom only.
- **Re-rendering all 16 GOOD runs** after these fixes land — a separate follow-up pass, not bundled
  into this spec. Verify each item on the specific run(s) that surfaced it; a full re-render sweep
  is its own task once these are confirmed correct.
- **Any change to `DRAIN_MATCH_WINDOW_S` without the handoff described in Item 8** — do not treat
  "make the number smaller" as an obvious safe fix.

[↑ TOC](#toc)

## Verification {#verification}

Per item, re-render the specific run named in that item's own evidence and view the PNG (not just
exit-code) before considering it done:

- Item 1: re-render `dean-20260810-064736-555` with the corrected title logic (no `--title` flag,
  letting the composite build naturally) and confirm the title shows workload · run · model ·
  harness · ns, not just the run ID. Also test passing an explicit `--title` value and confirm it
  now substitutes only the workload segment, not the whole string.
- Item 2: confirm the two title texts on panel 1a no longer visually overlap on
  `dean-20260810-064736-555`.
- Item 3: confirm panel 3's color-key strip sits closer to the main plot without colliding with the
  secondary axis, on both a low-pod-count run and a 15+-pod run (the case `1.12` was originally
  chosen for).
- Item 4: confirm the extra blank line above panel 4's title is gone.
- Item 5: confirm two pods with an identical first-appearance tick sort deterministically by the new
  tie-breaker, on a run where this actually occurs (check `dean-20260814-035754-869` or
  `dean-20260813-013728-756`, both multi-pod runs, for a same-tick scale-up batch first).
- Item 6: confirm panel 5's `L(t)` line visually aligns with panel 3's bucket centers on a run with
  a sharp step (e.g. a boot ramp).
- Item 7: confirm the new visual cue appears on `dean-20260814-053822-692`'s panel 6 where TA's line
  stops, and does NOT appear on a run where an analyzer is absent-from-config instead (confirm the
  two cases stay visually distinct).
- Item 8: report findings per the handoff instruction in Item 8 before implementing a fix; if a fix
  ships, verify against `dean-20260813-013728-756` (should reduce the false-positive rate) AND
  re-verify a cell used in the original drain-window-fix verification (`m-satta-dwell`, `m-sat-dwell`)
  for no regression.

Report final status per item (fixed / needs-decision-first / n/a) in your local status file and a
`plan__` handoff, per the usual protocol.

[↑ TOC](#toc)
