# Panel review, 2026-08-13 — findings from Dean's first look at panel 6

**Status:** DRAFT — Dean's raw feedback, captured and organized; not yet split into Type 3 code
specs. Source: Dean reviewing `session-notes/review-samples/m-satta-dwell-panels-with-panel6.png`
(freshly re-rendered from `cff4e4c0` against the real `m-satta-dwell` cell) plus his standing
observation of `panels.png` files across other already-rendered runs.

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Cross-cutting observation — broken panes are common {#cross-cutting}](#cross-cutting-observation--broken-panes-are-common-cross-cutting) L25:35
- [Item A — figure title is broken {#item-a-title}](#item-a--figure-title-is-broken-item-a-title) L36:49
- [Item B — panel 1a renders empty on some runs {#item-b-panel1a-empty}](#item-b--panel-1a-renders-empty-on-some-runs-item-b-panel1a-empty) L50:65
- [Item C — panel 1b: cap y-axis when capacity dwarfs work {#item-c-panel1b-yaxis}](#item-c--panel-1b-cap-y-axis-when-capacity-dwarfs-work-item-c-panel1b-yaxis) L66:93
- [Item D — panel 3: legend overflow, missing series, hatch readability, bar-top outline {#item-d-panel3-bugs}](#item-d--panel-3-legend-overflow-missing-series-hatch-readability-bar-top-outline-item-d-panel3-bugs) L94:120
- [Item E — panel 3/1b: sim-vs-real work-unit divergence {#item-e-sim-real-divergence}](#item-e--panel-31b-sim-vs-real-work-unit-divergence-item-e-sim-real-divergence) L121:136
- [Item F — panel 3 redesign: request-domain breakdown {#item-f-panel3-redesign}](#item-f--panel-3-redesign-request-domain-breakdown-item-f-panel3-redesign) L137:162
- [Item G — panel 4: parked, not decided {#item-g-panel4-parked}](#item-g--panel-4-parked-not-decided-item-g-panel4-parked) L163:174
- [Item H — panel 6 redesign: signed replica-delta per analyzer {#item-h-panel6-redesign}](#item-h--panel-6-redesign-signed-replica-delta-per-analyzer-item-h-panel6-redesign) L175:198
- [Convergence principle {#convergence}](#convergence-principle-convergence) L199:217
- [Cross-references](#cross-references) L218:226

## Cross-cutting observation — broken panes are common {#cross-cutting}

Dean: "Half of existing panels.png files have at least one broken pane. Review samples is no
exception." This is not scoped to the panel-6 sample — it's a standing quality problem across
`autoscaling-viz`'s rendered output. Before any redesign work lands, **someone should inventory
which existing `panels.png` files have which broken panes**, so the fixes below (Items A/B/D) are
verified against more than the one sample Dean happened to open. Not yet done — flag for whoever
picks up the bug-fix cluster.

[↑ TOC](#toc)

## Item A — figure title is broken {#item-a-title}

**DECIDED fix.** The sample's title reads `inference-perf-1786343242-zr01gi_1  ·  ?  ·  inference-perf  ·  ns=?` —
`meta.get('model')` and `meta.get('namespace')` both resolved to `?`. Dean: "title - broken. should
reflect workload + run id." The title should name the **workload** (e.g. `m-satta-dwell`, not the
harness's internal leaf directory name) and the **run id**, not fall back to `?` for fields the
extractor couldn't populate. Likely fix is in the extractor (`meta` construction in
`extract_real_trace.py`) rather than the renderer — the renderer just prints what `meta` gives it.
Investigate why `model`/`namespace` are unpopulated for this run (this cell's `run_metadata.yaml`
may be missing them, or the extractor may be looking in the wrong place) before assuming the fix is
renderer-side.

[↑ TOC](#toc)

## Item B — panel 1a renders empty on some runs {#item-b-panel1a-empty}

**Bug, needs triage — not yet root-caused.** Dean: "p1a is missing. In most other panels.png it is
ok." The sample's panel 1a shows "no per-request trace in this bundle" because this particular run
(`m-satta-dwell`'s `inference-perf-1786343242-zr01gi_1`) has no `per_request_lifecycle_metrics.json`
captured (confirmed: `find` on that results leaf shows no such file, and the extractor's own
coverage row 15 — "Per-request trace present" — FAILs with `n=0`). **This may be correct behavior
for this specific run**, not a bug in the code — but Dean's comparison is against *other* already-
rendered `panels.png` files where 1a is fine, so the open question is whether those other runs
actually have per-request data and this one genuinely doesn't (in which case Item A/data-collection
territory, not a renderer bug), or whether the extractor is failing to find per-request data that
does exist for this run. **Check whether `per_request_lifecycle_metrics.json` exists anywhere under
this run's results tree (not just the leaf checked) before concluding this is a real code defect.**

[↑ TOC](#toc)

## Item C — panel 1b: cap y-axis when capacity dwarfs work {#item-c-panel1b-yaxis}

**DECIDED design change.** Dean: "need to cap Y axis when capacity much bigger than work. Too small
to see the work breakdown. Better to set y-max not larger than 1.5x work and cut off the capacity.
Panel 5 good enough to show the wasted capacity. Can add a replica count label to every scaling
line." Confirmed by the sample: panel 1b's y-axis is dominated by the capacity ceiling line
(up to ~50000 tok/s), compressing the offered/delivered work stack (which peaks far lower) into an
unreadable sliver at the bottom.

**Fix, as clarified:**
- Set `y_max = 1.5 × max(work curve)` (offered or delivered, whichever is larger at any point),
  not `max(capacity ceiling)`.
- The capacity/ceiling line gets visually **clipped** at that y-max rather than forcing the axis to
  scale to it — but **label the true (off-chart) ceiling value** where the line exits the top of
  the plot (an arrow or text tag), so the reader isn't left wondering what the real number is.
- Panel 5 already does an adequate job of showing wasted capacity (the shaded region between served
  and slot capacity) — panel 1b doesn't need to duplicate that; capping its axis is fine precisely
  *because* panel 5 is the panel responsible for the capacity-vs-used story.
- Add a replica-count label to each step of the ceiling line (since the ceiling is `ready × rate`,
  a step change in the line corresponds to a replica-count change — annotate it, e.g. "×3" at each
  step), so a reader can see *why* the ceiling jumped without cross-referencing panel 2.

Same y-axis-capping treatment applies to panel 3 (see Item F) wherever its KV ceiling line has the
same domination problem — this item's fix pattern (cap, clip, label true value) is the general
convention, not a one-off for 1b.

[↑ TOC](#toc)

## Item D — panel 3: legend overflow, missing series, hatch readability, bar-top outline {#item-d-panel3-bugs}

**Mix of bugs and a readability design change** — the deeper structural redesign of panel 3 is
Item F; this item covers the narrower fixes Dean called out that apply regardless of whether the
structural redesign lands:

- **Legend overflow.** The sample's per-pod legend lists 15 full pod names ("2qvfm running",
  "2vxwj running", …) which overflows the panel. Dean: "can just number the pods 1, 2, 3, 4, …" —
  replace pod-name legend entries with short numeric labels (assign stable numbers per pod, e.g. by
  first-seen order or sorted name, and use "pod 1 running" etc.).
- **Missing total-requests overlay and missing KV ceiling.** Dean: "Missing total reqs. missing KV
  ceiling." — in the sample these may be present in the underlying code but rendering invisibly
  (scale-squashed, same failure mode as Item C) rather than genuinely absent; check the render code
  path before assuming the series was dropped. Cross-reference Item F, which resolves the ceiling
  placement question (secondary axis or drop) as part of the structural redesign.
- **Hatch readability.** Dean: "dashed fill is hard to read with many colors. Perhaps use original
  colors with thin white dashes? Need something more readable." Today's "waiting" band uses
  `hatch='////'` in the pod's own color at reduced alpha with a dark (`INK`) edge — with 15 pods,
  this becomes visually noisy. Try: full-saturation pod color, thin white (not dark) hatch lines, no
  alpha reduction — or another scheme the coder finds more legible; this is a "make it readable,"
  not a pixel-exact spec.
- **Bar-top outline.** Dean: "Also add outline to bars tops." — each stacked bar segment should get
  a thin outline on its top edge (not just the overall stack), to make individual pod contributions
  legible when they're visually similar in color/height.

[↑ TOC](#toc)

## Item E — panel 3/1b: sim-vs-real work-unit divergence {#item-e-sim-real-divergence}

**DECIDED direction, needs a coder investigation pass to realize.** Dean: "Work/s on the simulated
panels is broken in latest figs — goes too low. Should use the same requests breakdown as the real
panel 3, or vice versa (real should use work as unit — if can infer time in system)." This is the
first concrete instance of the [convergence principle](#convergence) below: the simulated renderer's
work/s panel and the real renderer's panel 3 currently disagree in a way that isn't just cosmetic —
one of them is producing numbers Dean doesn't trust ("goes too low"). Two candidate resolutions, not
yet chosen between: (a) make the real panel 3 emit a work/s view derived from time-in-system (if
that's inferable from available data), so real and simulated both speak "work," or (b) make the
simulated panel adopt the real panel 3's request-count breakdown instead. **Do not silently pick one
— this needs a short investigation into whether time-in-system is actually inferable for real runs
before deciding**, then a decision recorded here before a coder implements either direction.

[↑ TOC](#toc)

## Item F — panel 3 redesign: request-domain breakdown {#item-f-panel3-redesign}

**DECIDED design**, arrived at after two rounds of back-and-forth (the original ask mentioned a
stacked queue graph and a separate panel 4 redesign; both collapsed into this single item once Dean
clarified). Panel 3 becomes the canonical **request-domain** panel:

- **Breakdown:** per-replica running, draining, waiting, EPP queue, and total-in-system — i.e. the
  existing stack (running/waiting/router-residual) plus an explicit **draining** band (today's
  panel 2 already tracks drain events; panel 3 should surface draining requests as their own band,
  not folded into "running").
- **KV ceiling placement:** if the KV-ceiling line's max is more than 10% off the total-request-in-
  system max, put it on a **secondary y-axis** rather than let it compress the request breakdown
  (same failure mode and same general fix pattern as Item C) — or **drop it from panel 3 entirely**
  if a secondary axis still reads poorly. Both are acceptable outcomes; which one is the coder's
  call per-run, not a fixed rule.
- **Units:** requests, not work/s (see the convergence principle below — panel 4's work/s role is
  explicitly parked, not merged into panel 3).

This **supersedes** the design half of Item D (legend/hatch/outline fixes still apply verbatim to
whatever panel 3 becomes) and **absorbs** what earlier framing called "panel 4's stacked-queue
graph" — Dean: "Maybe if panel 3 looked OK I would not have a problem with 4" — i.e. the felt need
for a redesigned panel 4 was actually a panel-3 readability problem; fixing panel 3 removes the
pressure to redesign panel 4 for now (see Item G).

[↑ TOC](#toc)

## Item G — panel 4: parked, not decided {#item-g-panel4-parked}

**Explicitly NOT decided — do not treat as a task.** Dean, after Item F's panel-3 redesign
absorbed most of what panel 4 was going to be asked to do: "Maybe p4 not needed. Looks like p1b
already takes care of everything we wanted p4 to cover... Let's brainstorm on p4 later... You can
use the undecided p4 for experiments." Panel 4 stays exactly as it is today (the three-queue-
source INTERIM view, per the Type 1's own open-design-question framing) and is explicitly reserved
as a sandbox for future experiments, not a target for this review's fix/redesign work. Do not fold
panel-4 changes into the coder session spawned from this doc.

[↑ TOC](#toc)

## Item H — panel 6 redesign: signed replica-delta per analyzer {#item-h-panel6-redesign}

**DECIDED design**, replacing the first cut shipped in `cff4e4c0`. Dean, on the shipped version:
"text/graph — good direction but looks weird." Confirmed and clarified: rather than a flat marker
strip colored by reason code (today's implementation), panel 6 should plot **each analyzer's implied
replica-count vote as a signed line/marker series**:

- **Y-axis: replica count** (not an abstract "lane" position).
- **Signed value per analyzer per tick**, derived from that analyzer's own capacity math:
  - Negative when the analyzer's `rc`/`prc`-derived computation implies scale-*down* pressure.
  - Positive when its `sc`/`prc`-derived computation implies scale-*up* pressure.
  - (Exact formula — e.g. `sc/prc − rc/prc`, or per-variant `prc`-normalized values — is the
    coder's to work out from the `analyzer-result` JSON fields already parsed in `cff4e4c0`; this
    item specifies the shape Dean wants to see, not the arithmetic.)
- **Two series (one per analyzer present)**, each a line or marker-only graph.
- **Reason code still shown**, but as an indicator on the line (marker style, color, or annotation)
  rather than being the only content, the way it is today.

This keeps the same underlying data (`bundle['derived']['scaling_log']`, already extracted) — it's
a rendering change, not an extraction change. The analyzer-absent annotation and the degrade-message
path from the original Type 3 both still apply; only the plotted quantity and axis change.

[↑ TOC](#toc)

## Convergence principle {#convergence}

**DECIDED direction, governs Items C/F/H and any future panel work.** Dean: "The key is to use same
or very similar panels for simulated and real tests... converge on panels for both. Fix bugs in
both. We need to see how these look with correct results." This is not itself a single task — it's
the standard every panel-shape decision from here on must satisfy: whatever `render_real_trace.py`
draws for a given concern (work throughput, request breakdown, scaling reasons), the simulated
renderer (`plots.py`/sim tooling) should draw the *same shape* for the *same concern*, so a real run
and a simulated run read side-by-side without relearning the figure — this is explicitly already a
stated design goal in `render_real_trace.py`'s own module docstring ("Colour vocabulary AND panel
composition are taken from the synthetic PoC... so a real run and a simulated run can be read side
by side"), and this review's findings are about closing the gap where that goal has drifted (Item E
is the sharpest known instance). Bug fixes (Items A/B/D) and design changes (C/F/H) should be
verified against **both** renderers before being called done, not just `render_real_trace.py`.

[↑ TOC](#toc)

---

## Cross-references

- Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
- Original panel-6 Type 3: [`autoscaling-viz-decision-panel-plan.md`](autoscaling-viz-decision-panel-plan.md)
- Type 1: [`autoscaling-viz-design.md`](autoscaling-viz-design.md)
- Sample reviewed: `autoscaling-viz/session-notes/review-samples/m-satta-dwell-panels-with-panel6.png`
  (+ matching `bundle.json`/`coverage.json` in the same directory)

[↑ TOC](#toc)
