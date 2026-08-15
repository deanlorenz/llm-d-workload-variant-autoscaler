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

- [Confirmed good, no action {#confirmed-good}](#confirmed-good-no-action-confirmed-good) L25:39
- [Item Q — panel 1b text: mean±std, not just mean {#item-q-1b-text}](#item-q--panel-1b-text-meanstd-not-just-mean-item-q-1b-text) L40:48
- [Item R — panel 3: waiting overlay — thinnest possible diagonal white lines {#item-r-panel3-diagonal}](#item-r--panel-3-waiting-overlay--thinnest-possible-diagonal-white-lines-item-r-panel3-diagonal) L49:74
- [Item S — panel 4 redesign: stack (a)/(b), fix (a), consider per-pod-stats alternative {#item-s-panel4}](#item-s--panel-4-redesign-stack-ab-fix-a-consider-per-pod-stats-alternative-item-s-panel4) L75:96
- [Item T — panel 6: y-axis label + marker-label-on-first-occurrence {#item-t-panel6-label}](#item-t--panel-6-y-axis-label--marker-label-on-first-occurrence-item-t-panel6-label) L97:110
- [Item U — "WEAK TIME ANCHOR" in the title: relocate out of the main title, not just explain it {#item-u-weak-anchor}](#item-u--weak-time-anchor-in-the-title-relocate-out-of-the-main-title-not-just-explain-it-item-u-weak-anchor) L111:131
- [Item V — CONFIRMED: no cross-panel contradiction; two real findings underneath {#item-v-correctness}](#item-v--confirmed-no-cross-panel-contradiction-two-real-findings-underneath-item-v-correctness) L132:175
- [Item W — RESOLVED: "drain window" is mislabeled — no real per-pod drain signal exists; relabel to what it actually shows {#item-w-drain-window-root-cause}](#item-w--resolved-drain-window-is-mislabeled--no-real-per-pod-drain-signal-exists-relabel-to-what-it-actually-shows-item-w-drain-window-root-cause) L176:248
- [Cross-references](#cross-references) L249:263

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

## Item R — panel 3: waiting overlay — thinnest possible diagonal white lines {#item-r-panel3-diagonal}

Task 8 changed the waiting band's hatch from diagonal (`/`) to horizontal (`-`) lines, to
distinguish it from draining's dots — a change Dean never asked for; he flagged this directly:
"not sure why 8 asked for horizontal — I never asked for that." **Root cause: my own Type 3 spec**
(`autoscaling-viz-panel3-visual-scheme-plan.md`, sourced from `autoscaling-viz-panel-review-20260813-followup.md`
§ Item K) mis-paraphrased Dean's original ask — "dots for draining, dashes for waiting" as a visual
**distinction** requirement — into a specific **mechanism** requirement ("change the hatch character
to a dashed-line style"). The coder faithfully implemented the flawed spec; matplotlib has no literal
"dash" hatch character (only `/,\,|,-,+,x,o,O,.,*,X`), so `-` (horizontal) was a defensible reading
of the flawed spec on its own terms — but it wasn't what Dean wanted.

**Dean's exact correction:** "I want the thinest possible diagonal white lines." Requirements,
precisely:
1. **Diagonal** (`/`, back to what Task 8 replaced) — not horizontal.
2. **White** — the hatch line color itself, not just distinguishable from draining's dots.
3. **Thinnest possible** — minimize the hatch line weight, distinct from the overlay border line
   weight (which Dean separately confirmed is already good — "line width and color is good" referred
   to the overlay's own border, not the hatch fill).

Draining stays as dots (unchanged, not mentioned as needing a change). A fresh Type 3 (or a
targeted amendment to the visual-scheme plan) must carry this exact wording — not "revert to
diagonal" alone — before dispatch to the coder.

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

## Item U — "WEAK TIME ANCHOR" in the title: relocate out of the main title, not just explain it {#item-u-weak-anchor}

Dean's original question: **what does "weak time anchor" mean, and why does it appear in the
figure title?** My first-pass resolution proposed a plain-language explanation in place (Type 4
reference or expanded code comment) while leaving the text in the title. **Dean's correction on
that framing: "even with better explanation, does not belong in main title."** The defect isn't
that the phrase is unexplained — it's that a caveat this technical has no business occupying the
figure's main title regardless of how well it's glossed. Resolution changes from *explain it
better where it is* to **move it out of the title entirely**.

The mechanism exists in code (`render_real_trace.py`'s `weak = anchor.get('trustworthy') is False`,
driving the title suffix) and the footer already names *why* it fired for this specific run
("engine occupancy exceeds request-derived in-system count on 7% of scrapes despite
corr=0.9995...") — so the caveat's content is already captured somewhere reasonable (the footer).
**Not yet decided:** whether the fix is simply dropping the title suffix (since the footer already
carries the explanation) or moving it to a smaller/secondary annotation elsewhere on the figure.
That placement call, and any accompanying doc work, needs a fresh Type 3 before dispatch — not yet
written.

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

## Item W — RESOLVED: "drain window" is mislabeled — no real per-pod drain signal exists; relabel to what it actually shows {#item-w-drain-window-root-cause}

**Dean's hypothesis, verbatim:** "review the drain — does not match the scale-down events. I think
it may be related to the mismatch I already saw in previous fig. p3 may be showing the data upon
entry time rather than current time. Requests in epp queue, requests per pod, requests per draining
pods, and waiting per pod, are all current time, not entry time. All probably available as metrics."
Investigated against the fresh `m-satta-dwell` render (7 drain events / 6 pods with drain windows).

**Ruled out — not an entry-time-vs-current-time indexing bug.** Panel 3's underlying per-pod
`run`/`wait` series are all correctly keyed by the sample's own scrape timestamp (`s['t']`), both in
the renderer and the extractor's `GAUGE_MAP` (`vllm:num_requests_running`/`waiting` — live
current-value gauges, not queue-entry-time markers). No entry-time indexing bug found in the data
series themselves.

**Ruled out — not abrupt teardown with request loss either.** An intermediate hypothesis (pods
killed with no grace period, requests simply lost) was checked directly against EPP's own
`q_dispatch` series (`inference_objective_running_requests` — ground truth independent of per-pod
scrape gaps) around each pod's disappearance. For 3 of 4 transitions (`mhrkh`; `9kb6w`+`gzvfj`;
`l9s5k`), total system load is smoothly **conserved** across the departing pod's last sample — no
step-down proportional to what it was carrying (e.g. `mhrkh` held run=28 at its last sample;
`q_dispatch` shows 193→215 across that tick, essentially unchanged). One case (`njwp6`+`2vxwj`
dying on the same tick) showed a single-scrape `q_dispatch=0` anomaly that self-corrects on the very
next tick — a transient reporting gap, not sustained loss. So the data doesn't show requests being
dropped either.

**Actual root cause, confirmed by Dean's own framing: the pod is either live or draining, never
both — and every one of these windows shades time when the pod was still live.** Checked every
pod's own `run` series across its full drain window (`autoscaling-viz/extract_real_trace.py:854-934`,
`pod_drain_windows()`):

| pod | drain window | `run` inside the window |
|---|---|---|
| `2vxwj` | [881, 944] (63s) | 0 → 1 → **19 → 20** → 15 → 13 |
| `9kb6w` | [411, 537] (126s) | 0 → 1 → 2 → 1 → 2 → 1×5 |
| `gzvfj` | [458, 537] (79s) | 2 → 1 → 1 → 2 → 1 → 1 |
| `l9s5k` | [615, 727] (112s) | 2 → 2 → **5** → 3 → 3 → 3 → 2 → 3 → 2 |
| `mhrkh` | [65, 127] (62s, pod-relative) | 0 → 1 → **72** → 32 → 31 → 28 |
| `njwp6` | [771, 944] (173s) | 12 → 20 → 15 → 20 → 20 → 19 → 19 → 15 → 18 → 18 → 17 → 14 |

Every window's *entire span* is filled with normal, healthy scrapes — several climbing or spiking
(`mhrkh` to 72) — with no sub-interval that looks like a wind-down. The pod is being scraped
normally, serving normally, all the way through its last sample. **By Dean's rule, this means the
window is currently shading time the pod was fully live, not draining** — it isn't a partial
mismatch, the whole window is mislabeled.

**Why: the code was never given a real per-pod drain signal, because none exists in the current
data pipeline.** `pod_drain_windows()` infers "this pod is draining" from two proxies: (1) the
nearest *fleet-level* `desired`-drop timestamp, and (2) "this pod's own metrics disappeared soon
after." Neither is a per-pod live/drain signal — confirmed by checking the full gauge set actually
scraped (`extract_real_trace.py:56-60`, `GAUGE = {run, wait, kv}`): only vLLM-native metrics, no
kube-state-metrics pod-phase, no pod-deletion timestamp, no EPP routing-exclusion signal. There is
currently no way to know, from this data, when a specific pod was actually marked for removal versus
just still being scraped normally until it disappeared.

**Resolution, confirmed by Dean:** the feature's honest purpose is narrower than its current label
claims — it is "a visual aid to show which pod was taken down at a given scale-down event," not a
claim about drain/grace-period behavior. **Action: relabel/re-caption, don't remove.** Keep the
shaded band (it correctly identifies which pod and roughly when), but its text/legend must stop
saying "draining" and say something like "pod removed at scale-down event" instead — matching what
the signal actually is, not implying knowledge of in-flight-request wind-down that isn't there.
Needs a fresh Type 3 before dispatch to the coder — this doc establishes the resolved direction, not
the exact wording/styling.

**Separate, explicit TODO opened by Dean: find a real per-pod drain signal.** Not scoped or
scheduled here — candidates to consider when picked up: kube-state-metrics pod-phase/deletion
timestamp if scraped elsewhere in the harness, or an EPP-side "excluded from routing" signal if one
exists. Until such a signal exists, panel 3 cannot show true per-pod drain state, only the
relabeled proxy above.

[↑ TOC](#toc)

---

## Cross-references

- Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
- Sample reviewed (Items Q-V): `autoscaling-viz/session-notes/review-samples/m-ta-prefill-knee-fresh-b7920cd3.png`
  (+ matching `-bundle.json`/`-coverage.json`)
- Sample reviewed (Item W, drain-window investigation): `autoscaling-viz/session-notes/review-samples/m-satta-dwell-fresh-d7fa6ee5.png`
  (+ matching `-bundle.json`/`-coverage.json`)
- Related backlog item (finding 3's mechanism): `session/CURRENT.md` § bucket-keyed `prc` collapse;
  `autoscaling-viz/planning/sim-from-benchmark-plan.md` §1.2
- Related but distinct — do not conflate: `autoscaling-viz-drain-window-fix-plan.md` (Item O, the
  ~15-16s drain-window-end scrape-cadence lag) is a different defect in the same function, already
  addressed by commit `e188d244`'s backward-scan clipping fix. Item W is about what the window's
  *content* depicts once its bounds are correct, not about the bounds' timing precision.

[↑ TOC](#toc)
