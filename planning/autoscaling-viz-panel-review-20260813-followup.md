# Panel review, 2026-08-13 (follow-up) — Dean's review of the all-cells render sweep

**Status:** DRAFT. Source: Dean reviewing `m-sat-staircase.png`/`m-satta-staircase.png` and other
files from `session-notes/review-samples/all-panels-20260813/` — the first full render of every
campaign cell against `08927557` (Task 1 + Task 2 + its fix round, all landed). Distinct from and
follow-on to [`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md)
(this morning's review, which produced Tasks 1-3).

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Confirmed working — no action needed {#confirmed-working}](#confirmed-working--no-action-needed-confirmed-working) L22:37
- [Item I — figure title still needs work {#item-i-title}](#item-i--figure-title-still-needs-work-item-i-title) L38:47
- [Item J — CONFIRMED BUG: draining band shows requests with no draining pod {#item-j-drain-bug}](#item-j--confirmed-bug-draining-band-shows-requests-with-no-draining-pod-item-j-drain-bug) L48:78
- [Item K — panel 3 visual scheme: consistent per-pod color, dots/dashes as overlay {#item-k-panel3-visual}](#item-k--panel-3-visual-scheme-consistent-per-pod-color-dotsdashes-as-overlay-item-k-panel3-visual) L79:101
- [Item L — per-panel corner info: an explicit allocation {#item-l-corner-info}](#item-l--per-panel-corner-info-an-explicit-allocation-item-l-corner-info) L102:132
- [Item M — panel 6 not yet redesigned {#item-m-panel6-not-yet}](#item-m--panel-6-not-yet-redesigned-item-m-panel6-not-yet) L133:142
- [Cross-references](#cross-references) L143:151

## Confirmed working — no action needed {#confirmed-working}

Dean, on the all-cells sweep:
- **Panel 1b's y-axis cap** (Task 2 + fix round): "great. y-axis cap marked nicely. keep it." No
  further action.
- **Panel 2**: "good." No further action.
- **Panel 1a**: "good." No further action.
- **Panel 3's KV-ceiling secondary-axis behavior**: confirmed correct as shipped, after an initial
  mixup in this conversation about which panel a comparison referred to — Dean confirmed he wants
  the secondary axis kept for panel 3, and separately confirmed panel 1b's own (different) capping
  behavior is what he likes there. Both already match what's shipped; no change.
- **Pod-number-to-hash key** (Task 1's legend fix): "good, does not disturb the overall flow. not
  really needed, but good." No change requested.

[↑ TOC](#toc)

## Item I — figure title still needs work {#item-i-title}

Dean: "title needs fix" (on `m-satta-staircase`/`m-sat-staircase`, both already carry Task 1's
model/namespace/workload fallback). **Not yet root-caused in this session** — Task 1's fix landed
and was verified against `m-satta-dwell`; what specifically is still wrong on these two staircase
cells is not yet known. Needs a fresh look at the actual rendered title string on those two files
before scoping a fix (do not assume it's the same defect Task 1 already fixed).

[↑ TOC](#toc)

## Item J — CONFIRMED BUG: draining band shows requests with no draining pod {#item-j-drain-bug}

**Root-caused, this session.** Dean: "m-ta-staircase, 600s, no draining pod, yet drain marks on
graph." Verified directly against `m-ta-staircase`'s bundle:

- The run has exactly **one** real drain event, at t≈1073s (relative to run start) — confirmed via
  `derived.lags.drain_events`.
- Pod `r2tnh`'s replica desired/ready state shows `desired=3, ready=3` continuously from t≈615s to
  t≈1057s — **fully wanted and fully ready** the entire window, only becoming undesired at the real
  drain event (t≈1073s).
- Yet `pods['...r2tnh'].drain_windows` reports a window of **t≈615s to t≈1058s** (443 seconds) —
  covering almost the pod's entire serving history, not just the brief tail after it actually
  stopped being desired.

**Root cause, in `extract_real_trace.py`'s `pod_drain_windows()` (~line 825):** the function
correctly matches this pod's *end* (last sample, t≈1058s) against the real drain event at t≈1073s
(within `DRAIN_MATCH_WINDOW_S` = 120s — correct). But it then computes the window's *start* by
scanning backward through the pod's own samples for as long as `run > 0` holds continuously
(lines 863-868) — with no bound tied to when the replica set's own `desired` count actually
dropped. Since this pod had been continuously busy (`run > 0`) since t≈615s, the backward scan
walks all the way back there, mislabeling ~7 minutes of fully-desired, fully-ready serving time as
"draining."

**Fix direction (not yet implemented):** the drain window's start must be bounded by the actual
`desired` transition for the replica set this pod belongs to — i.e. intersect the backward
`run > 0` scan with "time since `desired` dropped below `ready`" (the same replica timeseries panel
2 already reads), not just "time since `run` was last zero." A pod cannot be draining before the
controller decided to shed it.

[↑ TOC](#toc)

## Item K — panel 3 visual scheme: consistent per-pod color, dots/dashes as overlay {#item-k-panel3-visual}

Dean's requested rule, restated precisely: **always use the same solid color for a given pod**
across running/draining/waiting (today's `BAND_SHADES`-by-sorted-order assignment is kept — Dean
confirmed no change needed to color *assignment*, only to how running/draining/waiting *reuse* it).
On top of that solid color:
- **draining** → dots overlay (already dotted hatch today — keep the hatch *type*, but see below on
  weight)
- **waiting** → dashed-line overlay (today uses diagonal `////` hatch — change to a dashed-line
  style, distinct from dots)
- **overlay weight**: "needs to be much finer/thinner" — today's hatch density/linewidth reads as
  too heavy; reduce both dot size and dash weight so the overlay reads as texture, not a competing
  fill.
- **bar outline**: "outline really helps readability — should use black outline on all bars but
  very very thin." Today's running bars already carry `edgecolor=INK, linewidth=0.4` (Task 2) —
  confirm this is already "very very thin" or reduce further; extend the same thin black outline
  to waiting and draining bars if not already applied uniformly.

This item is blocked on Item J's fix landing first — no point re-tuning the draining overlay's
visual weight against windows that are computed wrong.

[↑ TOC](#toc)

## Item L — per-panel corner info: an explicit allocation {#item-l-corner-info}

Dean: run/experiment-setup/workload info belongs in the **figure's own title** (already Task 1's
job — no change here). The **per-panel top-right corner text** is a separate, additional thing:
extra info "mostly from the summary report table," discussed before ("we had some good info in the
simulation panels"), not yet decided how to allocate across panels because not everything fits.
Dean's own proposed allocation, to be treated as the working assignment unless he says otherwise
when he sees it rendered:

| info | panel | note |
|---|---|---|
| # requests total, cutoff count | 1a | |
| cumulative % requests "good" (<30s) | 1a | |
| TTFT / wait-time p50, p75, p90, p95 | 3 | (moved here, not 1a — 1a already carries the wait-band histogram) |
| boot-time mean, scale-down time, drain time | 2 | "use shorter text" — panel 2 already has boot-lag text today, keep it tight |
| router imbalance, leader flips, oscillation | — | **Dean: "don't know"** — no panel assigned yet, explicitly undecided |
| ITL, ρ | 6 (probably) | "with other analyzer logic" — bundle with whatever Task 3's panel 6 redesign ends up showing |
| time per work unit | 1b | |
| costs / utilization | 5 | |

**This is a placement plan, not yet an implementation spec.** Before any coder work: (a) confirm
each metric is actually available in the bundle/coverage data at the point it would be rendered
(some, like TTFT percentiles, may need new extraction — check per-request data requirements against
Item B/Fix 2's known per-request-availability gaps before assuming it's free), (b) the router-
imbalance placement is explicitly unresolved, not defaulted anywhere, (c) panel 6's ITL/ρ placement
is contingent on Task 3's redesign existing first. Recommend a dedicated Type 3 once Task 3 lands
and the per-metric availability check is done — this is more than a "fix" cluster, it's new
rendering work across most panels.

[↑ TOC](#toc)

## Item M — panel 6 not yet redesigned {#item-m-panel6-not-yet}

Dean: "p6 does not work yet." Confirmed expected — Task 3 (the panel 6 redesign) was released to
the coder this session and has not landed yet. No new finding; every render in the current sweep
still shows the pre-redesign shipped panel 6. No action beyond letting Task 3 proceed.

[↑ TOC](#toc)

---

## Cross-references

- Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
- Prior review (this morning): [`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md)
- Task 2 spec (panel 3 redesign, where `pod_drain_windows` was introduced):
  [`autoscaling-viz-panel3-redesign-plan.md`](autoscaling-viz-panel3-redesign-plan.md)
- Sample reviewed: `autoscaling-viz/session-notes/review-samples/all-panels-20260813/`

[↑ TOC](#toc)
