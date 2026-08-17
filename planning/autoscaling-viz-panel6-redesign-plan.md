# Panel 6 redesign: signed replica-delta per analyzer — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 7. Source finding: [`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md)
§ Item H. Supersedes the shipped design in
[`autoscaling-viz-decision-panel-plan.md`](autoscaling-viz-decision-panel-plan.md) (implemented as
`cff4e4c0`) — that Type 3 is superseded, not this one built on top of it as an addendum, because the
plotted quantity itself changes, not just its presentation.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L23:34
- [What's already there, confirmed {#existing}](#whats-already-there-confirmed-existing) L35:47
- [What's missing — extractor change needed {#extractor-gap}](#whats-missing--extractor-change-needed-extractor-gap) L48:77
- [Finding from the 2026-08-13 all-cells render sweep — "absent" and "still reporting" coexist {#absent-vs-reporting}](#finding-from-the-2026-08-13-all-cells-render-sweep--absent-and-still-reporting-coexist-absent-vs-reporting) L78:99
- [Panel design — the new plot {#design}](#panel-design--the-new-plot-design) L100:120
- [What to keep from the shipped version {#keep}](#what-to-keep-from-the-shipped-version-keep) L121:136
- [Verification {#verification}](#verification-verification) L137:148

## Goal {#goal}

Replace panel 6's current reason-code marker strip with a **signed replica-delta-per-analyzer line
graph**. Dean, reviewing the shipped version: "text/graph — good direction but looks weird." The
redesign: each analyzer gets its own line/marker series, plotted in **replica-count units on the
y-axis**, signed — negative when that analyzer's own capacity math implies scale-*down* pressure,
positive when it implies scale-*up* pressure. The reason code (`P1-obs`/`P2-hist`/etc., or the
throughput analyzer's own vocabulary) becomes an indicator on the line — marker style, color, or
annotation — rather than being the only content, as it is today.

[↑ TOC](#toc)

## What's already there, confirmed {#existing}

Read directly (`render_real_trace.py:590-642`, `extract_real_trace.py:679-738`, this session,
2026-08-13): the shipped panel 6 draws one horizontal lane per analyzer (`saturation`, `throughput`),
with a `scatter` marker per `analyzer-result` tick colored by `reason`, plus the analyzer-absent
annotation and the shared decision-`axvline` loop every panel already gets for free
(`render_real_trace.py:645-658` — do not touch this shared loop, panel 6 keeps getting it
automatically). `bundle['derived']['scaling_log']['by_analyzer'][name]` is a list of
`{t, reason, variant}` dicts, one per (analyzer, variant, tick) triple — this is what today's
scatter plots.

[↑ TOC](#toc)

## What's missing — extractor change needed {#extractor-gap}

**The signed-delta computation needs fields the extractor currently drops.** Confirmed at
`extract_real_trace.py:713-720`: when parsing an `analyzer-result` line, the extractor reads
`rec.get('analyzer')`, `rec.get('variants')`, and per-variant `v.get('reason')`/`v.get('name')` —
but the top-level `analyzer-result` payload also carries `supply`, `demand`, `util`, `rc`, `sc`
(confirmed from raw `controller.log` samples, e.g.
`{"analyzer": "saturation", "supply": 329011, "demand": 74252, "util": 0.23, "rc": 0,
"sc": 222936.7, "variants": [{"name": "...", "prc": 329011, "role": "decode", "reason": "P3-k2"}]}`),
and each variant carries `prc`. **None of `rc`/`sc`/`util`/`prc` are stored in `by_analyzer` today**
— only `t`/`reason`/`variant` survive.

**Extractor fix:** extend the `by_analyzer` record (or add a parallel per-analyzer-tick list) to
also carry `rc`, `sc`, and the per-variant `prc` for that tick, so the renderer has what it needs for
the delta computation below. Keep the existing `t`/`reason`/`variant` fields — this is additive, not
a replacement of the existing shape, since Fix 2 of the bug-fix cluster or other consumers may still
want the plain reason-code record.

**Delta formula — the coder's to derive, not fixed here.** This Type 3 specifies the *shape* Dean
wants (signed, in replica units, one line per analyzer), not the exact arithmetic. A reasonable
starting point, to verify against real data before committing: `sc/prc − rc/prc` per analyzer per
tick (using the analyzer's own aggregate `rc`/`sc` and a representative `prc` — if multiple variants
report different `prc`, decide whether to use a per-variant series or an aggregate; check whether
`rc`/`sc` are already per-model-aggregate values or need summing across variants first). Whatever
formula is chosen, verify manually against 2-3 ticks in a real `controller.log` where you can hand-
compute the expected sign (e.g. a tick right before a confirmed scale-up should read positive) before
trusting the plotted output.

[↑ TOC](#toc)

## Finding from the 2026-08-13 all-cells render sweep — "absent" and "still reporting" coexist {#absent-vs-reporting}

**Confirmed on `m-ta-staircase` (TA-only cell), this session:** the `saturation_absent_at` line
fires on **every tick** (37/37, matching the analyzer-absent line's own known per-tick cadence, not
once per run — see the earlier correction in `autoscaling-viz-decision-panel-plan.md`), and yet
`by_analyzer['saturation']` has 37 real records with real reason codes (`P4-k1`, `P3-k2`, …) across
the same run. Both are true at once: saturation is absent from the configured list (will not vote,
confirmed by the log line's own text) **and** still computes and emits `analyzer-result` lines with
real `rc`/`sc`/`prc`/`reason` values every tick — consistent with the campaign doc's Finding 1
(disabling saturation stops it *voting*, not stops it *computing/logging*).

**Implication for this redesign:** plotting saturation's signed replica-delta line on a TA-only run
would show a real, non-zero signal for an analyzer that structurally cannot act on it. The current
shipped panel already has this same latent confusion (a reason-code marker sits right next to the
"did not vote" annotation) — carry the same annotation forward, but consider whether the redesigned
line itself needs a visual treatment (e.g. dashed/greyed instead of solid) for an absent analyzer's
line, so the shape doesn't read as "this analyzer's vote mattered here." Not a hard requirement —
use judgment; the annotation may already be sufficient once the line is signed and more legible than
today's flat marker strip. Flag whichever choice is made in the commit message.

[↑ TOC](#toc)

## Panel design — the new plot {#design}

- **Y-axis: replica count**, signed, symmetric around 0 (e.g. `ax.axhline(0, ...)` as a zero
  reference line).
- **One line or marker-only series per analyzer** present in the bundle (typically `saturation`,
  `throughput`) — reuse the existing color convention (each analyzer could keep a fixed color, e.g.
  via `C_UP`/`C_DOWN`-style constants or a small fixed 2-3 color set from `plots.py`, consistent with
  how other panels assign fixed roles to fixed colors — don't reuse `GP_COLORS`' categorical palette
  here since this is now a per-series identity, not a category).
- **Reason code as an indicator on the line**, not the only content: e.g. marker shape or a small
  annotation at points where the reason code changes, rather than the primary visual signal. Use
  judgement on legibility — a color-coded marker per reason (like today) layered on top of the new
  line, or a periodic text annotation, are both reasonable; pick whichever reads more clearly once
  you see it rendered against real data.
- **Keep the analyzer-absent annotation and the degrade-to-`empty()` path** (see § Keep below) —
  these don't change, only the plotted quantity and axis do.
- **Legend**: analyzer name → color/line-style key, plus whatever reason-code indicator convention
  was chosen.

[↑ TOC](#toc)

## What to keep from the shipped version {#keep}

Do not re-derive from scratch — these parts of `cff4e4c0` are correct and should carry over
unchanged:

- The analyzer-absent annotation logic (`render_real_trace.py:620-630`), including its two-branch
  handling (single-lane vs. multi-lane text placement).
- The `empty(g, ...)` degrade path when no scaling-decision data is in the bundle
  (`render_real_trace.py:636-638`).
- Reliance on the shared `axvline` decision-marker loop (`render_real_trace.py:645-658`) — panel 6
  gets scale-up/scale-down markers for free; do not add a second, redundant marker system.
- The panel's position in the `subplots(7, 1, ...)` grid and shared `grid`/`t0`/`span` — only the
  content of the plot changes, not its slot or x-alignment machinery.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render at least 2 cells: one SAT+TA (both lanes active, e.g. `m-satta-dwell`) and one TA-only
  (confirm the absent-analyzer annotation still fires correctly for the `saturation` lane).
- Hand-verify the delta formula's sign against 2-3 specific ticks in the raw `controller.log`: find a
  tick immediately preceding a confirmed `scaling-decision` `action: "scale-up"` for that analyzer's
  variant and confirm the plotted value is positive there (and the reverse for scale-down).
- Confirm the y-axis reads in replica-count units and the zero-reference line is present.
- Confirm this doesn't regress the analyzer-absent annotation or the shared decision-vline behavior
  verified in the original Type 3.

[↑ TOC](#toc)

## Outcome (committed `3f12aaa1`) {#outcome}

**Extractor**: `by_analyzer` records now also carry the analyzer's aggregate `rc`/`sc` for that tick
plus the reporting variant's `prc`, additive to the existing `t`/`reason`/`variant` fields.

**Delta formula, derived not copied.** The spec's own suggested starting point (`sc/prc − rc/prc`)
had the sign backwards — confirmed by reading the saturation engine's actual source
(`applyUniversalThreshold` in `internal/engines/saturation/engine_v2.go`): `RequiredCapacity` is
capacity deficit (scale-up pressure), `SpareCapacity` is capacity surplus (scale-down pressure), both
independently `max(0, ...)`-clamped so never simultaneously positive. Used `rc/prc − sc/prc` instead.
Hand-verified against 2 real controller.log ticks: a `throughput` tick immediately before a confirmed
scale-up (`curr=1,tgt=2`) computed `rc/prc=+0.110`; a `saturation` tick at a confirmed scale-down
(`curr=3,tgt=1`, `sc>0,rc=0`) computed negative. Both match the expected sign.

**Panel redesign**: one signed line per analyzer (fixed `ANALYZER_COLORS`, a per-series-identity
palette, deliberately not `GP_COLORS`/`BAND_SHADES` which are per-distinct-value categorical and
would reassign colors across runs), zero-reference `axhline`, replica-count y-axis, reason code as a
marker shape overlay with a compact text key (`markers: ^=P1-obs D=P2-hist ...`) rather than a second
full legend column. Absent-but-still-reporting analyzer's line renders dashed + faded (confirmed real
via a TA-only run: `saturation` genuinely absent from the configured list yet still logging real
`rc`/`sc`/`prc` every tick).

**One self-caught layout collision during verification**: the reason-marker text key first landed
below the axis at y=-0.22, directly colliding with the figure's one x-axis label (panel 6 is the
bottom-most panel and owns that label) — moved inside the axes, bottom-right corner, before commit.

**Verification**: re-rendered and viewed `m-satta-dwell` (15-pod SAT+TA, both analyzer lines visible,
signed values visually consistent with panel 2's replica trajectory — positive during the 0-350s
scale-up, negative through the 350-1300s scale-down, rising back near 1600-2000s), `m-ta-staircase`
(TA-only, saturation's line correctly dashed/faded, absent-annotation still fires), a
`--controller-log /dev/null` degrade-path check, and the golden pre-panel-6 bundle (no `scaling_log`
key at all — degrades cleanly, no crash). `make test`/`lint`/`gofmt` N/A.

[↑ TOC](#toc)
