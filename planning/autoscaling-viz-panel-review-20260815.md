# Panel review, 2026-08-15 — Dean's review of the fresh m-ta-prefill-knee render

**Status:** DRAFT. Source: Dean reviewing `m-ta-prefill-knee-fresh-b7920cd3.png` — the only
per-request-data-bearing run, freshly rendered against current tip `b7920cd3` (confirmed stamp-
matching). **Note on panel numbering:** the figure's own panel 6 (signed replica-delta per
analyzer) is what Dean's feedback calls "p5" below — the actual concurrency panel (L=λW) is panel 5.
Renumbered correctly throughout this doc; flagging the mismatch since Dean's own message used the
renderer's pre-Task-3 numbering by mistake, not a document defect.

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Confirmed good, no action {#confirmed-good}](#confirmed-good-no-action-confirmed-good) L24:38
- [Item Q — panel 1b text: mean±std, not just mean {#item-q-1b-text}](#item-q--panel-1b-text-meanstd-not-just-mean-item-q-1b-text) L39:47
- [Item R — panel 3: waiting overlay back to diagonal hatch {#item-r-panel3-diagonal}](#item-r--panel-3-waiting-overlay-back-to-diagonal-hatch-item-r-panel3-diagonal) L48:57
- [Item S — panel 4 redesign: stack (a)/(b), fix (a), consider per-pod-stats alternative {#item-s-panel4}](#item-s--panel-4-redesign-stack-ab-fix-a-consider-per-pod-stats-alternative-item-s-panel4) L58:79
- [Item T — panel 6: y-axis label + marker-label-on-first-occurrence {#item-t-panel6-label}](#item-t--panel-6-y-axis-label--marker-label-on-first-occurrence-item-t-panel6-label) L80:93
- [Item U — "WEAK TIME ANCHOR" in the title: needs explaining, not just displaying {#item-u-weak-anchor}](#item-u--weak-time-anchor-in-the-title-needs-explaining-not-just-displaying-item-u-weak-anchor) L94:107
- [Item V — CONFIRMED: no cross-panel contradiction; two real findings underneath {#item-v-correctness}](#item-v--confirmed-no-cross-panel-contradiction-two-real-findings-underneath-item-v-correctness) L108:153
- [Cross-references](#cross-references) L154:162

## Confirmed good, no action {#confirmed-good}

- **Panel 1a** — "ok."
- **Panel 1b** — "good," besides the text refinement in Item Q.
- **Panel 2** — "ok."
- **Panel 3** — "good," TTFT text good, waiting-vs-ready-replica match confirmed correct (see Item
  V) besides the hatch-style preference in Item R. **No drain data in this run to review that part
  of panel 3 against** — `m-ta-prefill-knee` has no scale-down event, so the draining band is
  untested by this sample.
- **Panel 5** (concurrency, L=λW) — "good."
- **Footer** — "ok, refine later" — no action now, revisit when other panel work settles.
- **Overall** — "good."

[↑ TOC](#toc)

## Item Q — panel 1b text: mean±std, not just mean {#item-q-1b-text}

Current corner text (Task 7): `"0.62s per 1000 tokens (mean, delivered)"`. Dean: should be
**mean ± std**, not mean alone — the spread matters as much as the central value for this metric.
Straightforward addition to the existing computation in `render_real_trace.py` (the mean is already
derived from the delivered-work series; add the same series' std alongside it).

[↑ TOC](#toc)

## Item R — panel 3: waiting overlay back to diagonal hatch {#item-r-panel3-diagonal}

Task 8 changed the waiting band's hatch from diagonal (`/`) to horizontal (`-`) lines, to
distinguish it from draining's dots. Dean's preference, after seeing it rendered: **go back to
diagonal** for waiting. Overlay line weight and color from Task 8 are confirmed good — "line width
and color is good," just the specific hatch character for waiting should revert. Draining stays as
dots (unchanged, not mentioned as needing a change).

[↑ TOC](#toc)

## Item S — panel 4 redesign: stack (a)/(b), fix (a), consider per-pod-stats alternative {#item-s-panel4}

Panel 4 remains explicitly parked as a sandbox per the epic plan's Item 2 — this is exploratory
feedback for that eventual redesign, not a task to schedule yet on its own. Three distinct points,
captured precisely rather than merged:

1. **(a) and (b) should be stacked**, not drawn as separate overlaid lines as today.
2. **(a) [derived flow-control, `in-system − dispatch`] looks wrong** — Dean flags the shape/values
   as suspect, not just the presentation. Not yet investigated by this session — worth checking
   against real data before any redesign locks in a stacking behavior for a series that might itself
   be buggy.
3. **The whole panel is probably better captured by panel 5** (the concurrency view already does
   the "how much is queued vs. served vs. capacity" job well) — raising the question of whether
   panel 4 is worth keeping in its current queue-sources form at all.
4. **Alternative use floated, not decided:** repurpose panel 4's slot for **per-pod stats** — KV%,
   num running, GPS, PPS, one line per pod plus a per-pod average. This is a genuinely different
   panel concept, not a tweak to the existing queue-sources content. **Not scoped, not decided** —
   flagged as a direction to consider whenever panel 4 actually gets picked up, per the epic plan's
   "brainstorm later" framing.

[↑ TOC](#toc)

## Item T — panel 6: y-axis label + marker-label-on-first-occurrence {#item-t-panel6-label}

Two small, additive requests on the Task 3 panel 6 redesign, which Dean otherwise called "a very
good attempt":

1. **Y-axis label:** change to **"replica-delta"** (currently unlabeled or generic — confirm exact
   current label before editing).
2. **Marker legend is a bit hard to follow.** Suggested fix: **annotate the marker's reason-code
   label (P1-obs, P2-hist, P3-k2, P4-k1, T1-ols, T2-default, T2-pinned, …) directly on the first
   occurrence of each marker type** in the plot itself, rather than relying solely on the legend box
   to carry that mapping.

[↑ TOC](#toc)

## Item U — "WEAK TIME ANCHOR" in the title: needs explaining, not just displaying {#item-u-weak-anchor}

Dean's direct question: **what does "weak time anchor" mean, and why does it appear in the figure
title?** Not yet answered in this doc — this is a real documentation gap, not a code defect. The
mechanism exists in code (`render_real_trace.py`'s `weak = anchor.get('trustworthy') is False`,
driving the title suffix) and the footer already names *why* it fired for this specific run
("engine occupancy exceeds request-derived in-system count on 7% of scrapes despite
corr=0.9995...") — but nothing explains *what a time anchor is* or *why its trustworthiness matters*
to a reader encountering this for the first time. Needs a plain-language explanation, likely a
doc addition (Type 4 reference or an expanded code comment) rather than a code change — flagged, not
yet resolved.

[↑ TOC](#toc)

## Item V — CONFIRMED: no cross-panel contradiction; two real findings underneath {#item-v-correctness}

Dean raised four correctness questions. Traced all four directly against this render's own
`bundle.json` before answering:

**1. Panel 3 waiting matches ready replicas — confirmed correct**, per Dean's own read. No further
action.

**2. "req in system is suspect — p1b suggests high completion until 600s then low, doesn't match
p3" — investigated, NOT a contradiction.** Completion counts, bucketed by 100s window, show a real,
large drop at exactly this point: ~4500 completions/100s through t≈500-600s, collapsing to
~450-540/100s from t≈600s onward (roughly a 9x drop) — this is genuinely reflected in panel 1b's
offered/delivered curves, which are correct. Separately, `system.in_system` after t≈600s is **not
zero** — it's real but small (single digits to low teens), which reads as empty at this chart's
y-axis scale (peaked near 2000 during the earlier burst). **These are the same true story told at
two different scales, not a contradiction**: a massive completion burst ends abruptly around
t≈600s, followed by a long low-and-noisy tail with very little in flight. Worth considering for
Item S/panel-4-or-5 rework: a log-scale or zoomed inset for the post-burst tail would make this
readable without needing to explain it after the fact.

**3. "Why does scale-up trigger after 600s?" — investigated, root cause identified.** The throughput
analyzer's scale-up decisions to 8 (t≈628s) and 10 replicas (t≈644s) are driven by a **transient
collapse in the analyzer's own `prc` (per-replica capacity) estimate**, not by rising demand: traced
`derived.scaling_log.by_analyzer.throughput` directly — `prc` reads 1563 tok/s at t≈554s, collapses
to **56 tok/s** at t≈615s (the tick immediately preceding the scale-up sequence), then recovers to
260-670 tok/s over the following ticks. `rc` (required capacity) spikes to 320 at that same t≈615s
tick purely because `rc = demand/threshold − supply` and `supply = curr × prc` — a collapsed `prc`
mechanically inflates the replica ask (`ceil(rc/prc)`) even with flat or falling demand. **This is
the same `prc`-instability-during-demand-transition mechanism already documented in
`autoscaling-viz/planning/sim-from-benchmark-plan.md` §1.2** (the "9 target changes across
20:42-21:02 while demand rose monotonically" finding from the original ladder-run analysis) and
matches the still-open, tracked "bucket-keyed `prc` collapse" backlog item referenced in
`session/CURRENT.md`. Not a new bug — a fresh, independent confirmation of a known, already-
tracked estimator-instability mechanism, this time triggered by demand *falling* rather than rising.

**4. "No requests in system after 600s (p3/p4/p5) — why still showing data in p1b?" — resolved by
finding 2 above.** Panels 3/4/5 aren't actually showing zero — they're showing real small values
invisible at their y-axis scale (see finding 2). Panel 1b is correctly showing the real completion
count for work that was already in flight before the demand cliff — a 30s-trailing window naturally
keeps showing declining-but-nonzero throughput for a while after arrivals stop, which is expected
behavior for that window, not a bug.

[↑ TOC](#toc)

---

## Cross-references

- Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
- Sample reviewed: `autoscaling-viz/session-notes/review-samples/m-ta-prefill-knee-fresh-b7920cd3.png`
  (+ matching `-bundle.json`/`-coverage.json`)
- Related backlog item (finding 3's mechanism): `session/CURRENT.md` § bucket-keyed `prc` collapse;
  `autoscaling-viz/planning/sim-from-benchmark-plan.md` §1.2

[↑ TOC](#toc)
