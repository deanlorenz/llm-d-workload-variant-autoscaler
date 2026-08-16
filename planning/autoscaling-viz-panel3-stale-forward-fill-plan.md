# Panel 3: single-tick forward-fill with stale-overlay marker — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 2. Source: live discussion 2026-08-16, following the panel 3 vs panel 5 discrepancy
investigation (`autoscaling-viz-review-ongoing.md` § 2026-08-16 warmup-anchor review, Question 2).
Panel 5 is explicitly OUT OF SCOPE for this spec — Dean's own framing: "For p5 it is an aggregate
so I am not sure we can show stale markers," left open, not solved here.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Why {#why}](#why-why) L21:44
- [Confirmed against real data before writing this {#confirmed}](#confirmed-against-real-data-before-writing-this-confirmed) L45:63
- [Item AE — fix the missing-vs-zero conflation {#item-ae-zero-conflation}](#item-ae--fix-the-missing-vs-zero-conflation-item-ae-zero-conflation) L64:85
- [Item AF — forward-fill exactly one tick, mark it stale {#item-af-forward-fill}](#item-af--forward-fill-exactly-one-tick-mark-it-stale-item-af-forward-fill) L86:113
- [What NOT to change {#not-to-change}](#what-not-to-change-not-to-change) L114:130
- [Verification {#verification}](#verification-verification) L131:146

## Why {#why}

Panel 3 currently treats "no sample at this grid tick for this pod" as `0.0` running-requests
(`by_t.get(t) or 0.0`, `render_real_trace.py:681,754`). This has two problems, both raised directly
by Dean:

1. **A missing scrape reads as "this pod suddenly has zero requests," which is wrong** — the pod is
   very likely still running whatever it was running a moment ago; the metrics endpoint just didn't
   respond that cycle. Panel 5 already forward-fills instead (`hold()`, "last value wins") for its
   own aggregate, which is part of why panel 3 and panel 5 can show different totals for what should
   be the same underlying quantity at a given instant — this spec brings panel 3 in line with that
   same principle, for its own per-pod bars.
2. **A genuine zero must never be indistinguishable from a missing sample.** `by_t.get(t) or 0.0`
   conflates them today — Python's `or` treats a real `0.0` value the same as a missing key. This is
   a real, separate bug regardless of the forward-fill question and must be fixed as part of this
   same change, not left for later.

Dean's own calibration on how far to carry a stale value forward: **exactly one tick, never more.**
"If current slot got no signal, copying previous slot's numbers is fine. Copying over more is
getting more and more suspect." Beyond one tick, this spec does not define new behavior — see
§ Confirmed for what real data shows about how often that even happens.

[↑ TOC](#toc)

## Confirmed against real data before writing this {#confirmed}

Real per-pod scrape cadence is **16s median** (checked directly: min 15s, p25/median/p75 all 16s,
max 24s, across `m-satta-dwell`'s pods). Checked how often a pod actually misses its own expected
tick (gap > 20s from that pod's own previous sample, not "missing relative to some other pod's
grid point" — the union-of-all-pods grid trivially never shows a pod missing relative to itself):

- `m-satta-dwell`: 18 real gaps found, **all single-tick, 0 multi-tick**.
- `m-sat-dwell-warmup`: 15 real gaps found, **all single-tick, 0 multi-tick**.

So in both sample runs, this is genuinely rare (a few dozen ticks out of many hundreds) and never
observed running longer than one tick. The "ongoing missing data, real problem for a live pod" case
Dean flagged as a legitimate concern has not shown up in real data yet — this spec does not need to
design a second visual tier for it, per Dean's own "keep the overlay simple" instruction. If a coder
or reviewer later finds a genuine multi-tick run on some other bundle, flag it rather than silently
extending the fill — this spec's forward-fill is capped at one tick by design, not by omission.

[↑ TOC](#toc)

## Item AE — fix the missing-vs-zero conflation {#item-ae-zero-conflation}

`render_real_trace.py:681` (draining band) and `:754` (waiting band) both use the pattern
`v = by_t.get(t) or 0.0` / `ys = [by_t.get(t) or 0.0 for t in pgrid]`. Change every such site in
panel 3's per-pod resolution to check for `None` explicitly:

```python
raw = by_t.get(t)
v = raw if raw is not None else 0.0  # placeholder -- Item AF's fill replaces this default
```

This item is a prerequisite for Item AF (you can't correctly forward-fill "missing" if "missing"
and "genuinely zero" look identical going in) — implement both items together in one pass, but keep
this distinction explicit in the code/comments since it's the load-bearing correctness fix, not
just plumbing for the visual feature.

**Also check the running band's own resolution** (wherever `run_ys` is built, same function) for the
same `or 0.0` pattern — the spec's examples above are draining/waiting, but if running uses the same
idiom it has the same bug and must be fixed too.

[↑ TOC](#toc)

## Item AF — forward-fill exactly one tick, mark it stale {#item-af-forward-fill}

For each pod's own per-band series (running, draining, waiting — whichever bands panel 3 draws),
when a grid tick has no sample (per Item AE's `is None` check):

- If the **immediately preceding** tick for that same pod had a real sample: use that value,
  and mark this tick's bar segment for that pod as **stale** (see overlay below).
- If the preceding tick was *also* filled (i.e. this would be the second consecutive fill for the
  same pod): do not extend the fill further. Per Dean's calibration, this spec does not define
  behavior beyond one tick — flag this case (e.g. a log line or a comment marking it as an
  unhandled edge case) rather than silently guessing at a second-tier treatment. Real data shows
  this essentially never happens; if a future render actually hits it, that is itself information
  worth surfacing, not smoothing over.

**Stale overlay — single, simple treatment, not a tiered system.** Dean's own framing: "stale is
stale ... I still want to see the old value ... I clearly see the last point in time where data was
actually scraped." Requirements:
- The bar segment still shows the carried-forward numeric value (height), not blanked or zeroed.
- A single, consistent visual marker distinguishes a stale bar from a fresh one — e.g. a hatch
  pattern, a distinct border style, or reduced opacity (coder's choice of exact treatment, but it
  must be visually different from both the running/draining/waiting hatches already established
  and from the outlier-marker gold used on panel 4, so nothing reads as the same signal as an
  unrelated existing overlay).
- No second/heavier treatment for "worse" staleness — per Dean, keep this simple; there is only one
  fill depth (one tick) to represent.

[↑ TOC](#toc)

## What NOT to change {#not-to-change}

- Panel 5's own `served_by_t`/`hold()` logic — explicitly out of scope. Dean: "For p5 it is an
  aggregate so I am not sure we can show stale markers" — left open, not solved here. Panel 5's
  actual `served_g` total may still be recomputed by this change if it happens to share code paths
  with panel 3's per-pod resolution — check for that and flag it if so, but do not redesign panel 5
  as part of this spec.
- Panel 3's existing hatch styles (diagonal waiting, dotted draining), color scheme, sort order
  (scale-up, per the prior round) — unchanged; only the missing-tick handling and its new overlay
  are added.
- Panel 4's per-pod KV% heatmap already has its own dead/live-pod distinction (a different gray
  fill for "no data at all," from the original heatmap spec) — that mechanism is unrelated and
  untouched; panel 3's new stale marker is about a *live* pod's *transient* single-tick gap, not
  panel 4's *dead-or-not-yet-live* distinction.

[↑ TOC](#toc)

## Verification {#verification}

- Confirm the `is None` fix (Item AE) doesn't change any rendered output on a bundle with no
  missing ticks at all — a genuine `0.0` sample must still render as an empty/zero-height segment,
  not disappear or change color.
- Re-render `m-satta-dwell` (18 real single-tick gaps confirmed present) and visually locate at
  least one stale-marked bar; confirm its height matches the pod's own preceding tick's value, and
  that the marker is visually distinct from draining/waiting hatches and from panel 4's outlier
  marks.
- Confirm no bundle currently in `session-notes/review-samples/` triggers the "second consecutive
  fill" flag-and-stop case — if one does, report it rather than silently extending the fill to make
  it disappear.
- Report back via a `plan__` handoff with exact render paths and confirmed stamps, per the usual
  protocol — do not mark push-ready without Dean's review of the actual rendered output.

[↑ TOC](#toc)
