# Panel 1b y-axis capping + panel 3 request-domain redesign — Code Spec (Type 3)

**Status:** READY FOR CODER, except § *Item E note* which is explicitly NOT in scope. Parent epic:
[`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md) Item 7. Source findings:
[`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md) §§ Items C, D
(design half), F, G, and the Convergence principle.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal and scope {#goal}](#goal-and-scope-goal) L21:36
- [Fix — panel 1b y-axis capping {#panel1b-cap}](#fix--panel-1b-y-axis-capping-panel1b-cap) L37:73
- [Redesign — panel 3 request-domain breakdown {#panel3-redesign}](#redesign--panel-3-request-domain-breakdown-panel3-redesign) L74:122
- [Panel 4 — do not touch {#panel4-noop}](#panel-4--do-not-touch-panel4-noop) L123:131
- [Convergence with the simulated renderer {#convergence}](#convergence-with-the-simulated-renderer-convergence) L132:143
- [Item E note — explicitly out of scope here {#item-e-note}](#item-e-note--explicitly-out-of-scope-here-item-e-note) L144:152
- [Verification {#verification}](#verification-verification) L153:170

## Goal and scope {#goal}

Two related changes to `render_real_trace.py`, both about the same underlying problem — a ceiling
line with a much larger range than the quantity it's overlaid on, compressing the thing the reader
actually wants to see:

1. **Panel 1b** gets a bounded y-axis (fix, not a redesign — same panel, same content, just capped).
2. **Panel 3** gets restructured into the canonical request-domain breakdown (running / draining /
   waiting / EPP-queue / total-in-system), replacing today's running+waiting+router-residual stack.

Depends on [`autoscaling-viz-bugfix-cluster-plan.md`](autoscaling-viz-bugfix-cluster-plan.md) having
already landed Fix 3 (legend numbering, hatch readability, bar-top outlines) — this spec assumes
those are in place and doesn't re-specify them.

[↑ TOC](#toc)

## Fix — panel 1b y-axis capping {#panel1b-cap}

Confirmed in code: the capacity ceiling line is drawn at `render_real_trace.py:385`
(`b.plot(grid, ceil, ...)`, `ceil = [v * ceil_rate for v in ready_g]`) and can reach ~5x the offered/
delivered work stack's peak on runs with many ready replicas — this is exactly what the reviewed
sample showed (ceiling to ~50000 tok/s, work stack peaking far lower), which compresses the
offered/delivered stackplot into an unreadable sliver.

**Fix:**
- Compute `y_max = 1.5 * max(peak of offered work curve, peak of delivered/total_w curve)` and call
  `b.set_ylim(0, y_max)` (or equivalent) before or after the plot calls — check matplotlib's
  behavior on `fill_between`/`stackplot` with clipped `ylim` to make sure the fill still renders
  correctly up to the axis edge rather than disappearing.
- The ceiling line (`b.plot(grid, ceil, ...)` at line 385) and its optional sat-rate reference line
  (line 388) will now visually run off the top of the axis wherever they exceed `y_max` — that's the
  intended "clip" behavior, not a bug to fix.
- **Label the true ceiling value where it exits the plot.** At each point the ceiling line crosses
  above `y_max`, add a small annotation at the top edge (e.g. `ax.annotate` with an upward arrow, or
  a text label near `y_max` reading the actual `ceil_rate * ready` value at that point) so the reader
  can still read off the real number. Simplest version: one label per replica-count step (see next
  bullet) rather than continuously along the line.
- **Add a replica-count label to each step of the ceiling line.** The ceiling is `ready_g[i] *
  ceil_rate` — a step change corresponds to a `ready` replica-count change. At each step, annotate
  with the replica count in force (e.g. `"×3"` near the step), so a reader sees why the ceiling moved
  without cross-referencing panel 2. This can double as the off-chart value label above — e.g.
  `"×3 (34.2k tok/s)"` at a step that's off-chart.
- The `fill_between(..., color=C_CAP, alpha=0.15, label='unused capacity')` block at line 395-398
  should still work sensibly against a clipped axis — the shaded "unused capacity" region will
  itself be clipped at `y_max`, which is fine; panel 5 remains the panel responsible for showing the
  full unused-capacity picture (see below), panel 1b only needs to not obscure the work breakdown.

**Do not** touch panel 5's ceiling line (`render_real_trace.py:574-575`) — Dean explicitly said panel
5 already does an adequate job showing wasted capacity; this fix is scoped to panel 1b (and,
separately, panel 3 below) only.

[↑ TOC](#toc)

## Redesign — panel 3 request-domain breakdown {#panel3-redesign}

Today's panel 3 (`render_real_trace.py:455-516`, the `d = ax[3]` block) stacks per-pod running, then
per-pod waiting (hatched), then a router-side residual band, with a KV-ceiling step line and a
total-in-system overlay. The redesign keeps the "stack ≡ in system" invariant but changes what's in
the stack:

**New bands, bottom to top** (all still per-pod where the underlying data is per-pod; router/EPP
bands are necessarily aggregate):
1. **Running** — unchanged, per-pod `run` series (`extract_real_trace.py`'s `vllm:num_requests_running`
   scrape), same as today.
2. **Draining** — new. A pod counts as draining at time `t` if it is `ready` but no longer part of
   the `desired` count WVA wants — i.e. cross-reference the pod against the replica desired/ready
   timeseries the same way `mark_effects`/panel 2 already do, rather than inventing a new signal.
   Concretely: today's `derived.lags.drain_events` is only a list of timestamps with no per-pod
   association (`extract_real_trace.py:742-760`) — this redesign needs to know *which* pod is
   draining and its in-flight (`run`) count during the drain window, which the current extraction
   doesn't carry. **This is new derivation work in the extractor, not just a renderer change**: add
   pod-level drain-window detection (a pod's own `run`/`wait` series continuing after the replica set
   it belongs to has been marked for scale-down) to `bundle['derived']` or per-pod series, then the
   renderer draws it as its own band using that pod's `run` count during the drain window (subtracted
   out of the "running" band above so the stack invariant holds — a draining pod's requests move
   from the "running" band to the "draining" band, they don't double up).
3. **Waiting** — unchanged, per-pod `wait` series (hatched, per Fix 3's readability changes).
4. **EPP queue** — this is today's router-side residual band (`max(0, in_system - Σrun - Σwait)`,
   `render_real_trace.py:487-492`) — keep the same derivation, rename the label/legend entry to "EPP
   queue" if that's a clearer name for what it represents (confirm against the panel's own docstring
   comment at lines 449-454 explaining why this is a residual, not `q_dispatch` directly — keep that
   reasoning intact, only the surface label may change).
5. **Total-in-system overlay** — unchanged, the thick `system`-sourced line at line 500-502; this
   should still ride exactly on the stack top (same invariant as today).

**KV ceiling placement.** Confirmed at `render_real_trace.py:493-497`
(`d.step(xr, [v * cap['max_conc_pred'] for v in yr], ...)`). Compare its max value against the
total-in-system max:
- If the ceiling's max is within 10% of the total-in-system max, keep it on the primary axis as
  today.
- If it's more than 10% off (either direction), move it to a **secondary y-axis**
  (`ax.twinx()` or equivalent) so it doesn't compress the stack, OR drop it from panel 3 entirely —
  both are acceptable; use judgment per-run, or make it a simple threshold-based code path that
  picks automatically (recommended, since panel 3 needs to render sensibly across many different
  runs without a human choosing each time). If a secondary axis is used, give it a distinct visual
  treatment (different tick color, e.g. `C_CEIL`, on that axis's spine/labels) so it's clearly a
  different scale.

**Units:** stays in requests, not work/s — do not fold in a work/s view here (see § Panel 4 below).

[↑ TOC](#toc)

## Panel 4 — do not touch {#panel4-noop}

Per the review doc's Item G, panel 4 is explicitly parked as a sandbox for future experimentation,
not a target for this Type 3. Leave `render_real_trace.py`'s panel-4 block (`e = ax[4]`, lines
518-536) exactly as-is. Do not fold any of panel 3's new bands into it, and do not remove its
INTERIM framing.

[↑ TOC](#toc)

## Convergence with the simulated renderer {#convergence}

Per the review doc's Convergence principle: once panel 3's redesign and panel 1b's capping land in
`render_real_trace.py`, check whether the simulated renderer (`plots.py` / the sim tooling under
`autoscaling-viz/`) draws an equivalent shape for the same concerns, and if not, note the gap in your
handoff/status update rather than silently leaving it — but **do not attempt to fix the simulated
renderer's own divergence as part of this Type 3** unless it's a small, obviously-safe change (e.g.
reusing the same color constant). The deeper sim-vs-real reconciliation is Item E, gated separately
(see below) — this Type 3 is scoped to `render_real_trace.py`/`extract_real_trace.py` only.

[↑ TOC](#toc)

## Item E note — explicitly out of scope here {#item-e-note}

The review doc's Item E (simulated panel's work/s reading "too low," possible unit mismatch with
real panel 3) is **not** part of this Type 3. It needs a short investigation (is time-in-system
actually inferable for real runs the way the simulated renderer assumes?) and an explicit decision
before any code changes — do not let this Type 3's work bleed into fixing Item E's divergence.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render the same 3+ cells used in the bug-fix cluster's verification, after this spec's changes
  land on top.
- Confirm panel 1b's work breakdown is now visually legible (not compressed to a sliver) on a run
  where the ceiling previously dwarfed it; confirm the off-chart ceiling value and replica-count
  labels are both present and readable.
- Confirm panel 3's new draining band actually appears on a run with a real scale-down + drain
  window (e.g. `m-satta-dwell`, which panel 2's own boot-lag note already shows a scale-down for);
  confirm the running/draining split doesn't double-count (spot check: running + draining + waiting +
  EPP-queue should still sum to total-in-system, same invariant as today).
- Confirm the KV-ceiling threshold logic picks the secondary-axis-vs-primary-axis behavior sensibly
  on at least one run where the ceiling and total-in-system are close (primary axis expected) and one
  where they're far apart (secondary axis or dropped expected).
- Record in `session/status/autoscaling-viz.md`: which convergence gaps were found (if any) between
  real and simulated renderers, without attempting to fix them here.

[↑ TOC](#toc)
