# Per-panel corner-info allocation — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 7 / Item L. Source: [`autoscaling-viz-panel-review-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md)
§ Item L, Dean's proposed placement table.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L18:28
- [Data-availability check — done, per metric {#data-availability}](#data-availability-check--done-per-metric-data-availability) L29:68
- [Placement, final {#placement}](#placement-final-placement) L69:97
- [What NOT to do {#not-to-do}](#what-not-to-do-not-to-do) L98:108
- [Verification {#verification}](#verification-verification) L109:121

## Goal {#goal}

Add the per-panel top-right corner info Dean asked for (distinct from the figure's own title, which
Task 1 already handles — run/model/namespace/workload). This is additional summary info "mostly
from the summary report table," discussed before, allocated one metric-group per panel since not
everything fits on one figure. Dean's own proposed table (§ Item L of the follow-up review) is the
starting allocation; this spec resolves the three things that table left open (data availability,
router-imbalance placement, cost/utilization scoping) before handing to a coder.

[↑ TOC](#toc)

## Data-availability check — done, per metric {#data-availability}

Checked this session, against the current `extract_real_trace.py`/`render_real_trace.py`:

- **# requests total, cutoff count** — already computed today (panel 1a's own title,
  `f'requests: {len(reqs)} offered, {n_tr} cut off at run end'`). Just needs restyling/moving to the
  corner if it isn't already there in the right spot — likely already satisfied, confirm on render.
- **Cumulative % requests "good" (<30s)** — derivable from the same `wait_band()` bucketing panel 1a
  already does for its stacked bars (`WAIT_EDGES`, `r.get('outcome')`); not new data, a new
  aggregation over data already grouped.
- **TTFT / wait-time percentiles (p50/p75/p90/p95)** — **not a blocker, contrary to the follow-up
  review's own caution.** `r['ttft']` is already a per-request field populated whenever per-request
  data exists at all (`extract_real_trace.py` lines ~354-412) — today it's only consumed for
  wait-band bucketing (panel 1a), but the raw values are there. Percentiles are a new aggregation,
  not new extraction. Gated on the same per-request-availability condition panel 1a already has
  (empty when `reqs` is empty) — no new gate needed, reuse the existing one.
- **Boot-time mean, scale-down time, drain time** — already computed and already rendered as panel
  2's corner note today (`lg['boot_s_mean']`, `lg.get('scaledown_observed')`). Dean's ask here is
  "use shorter text," i.e. tighten the existing note, not add new data.
- **Router imbalance, leader flips, oscillation** — already computed and rendered, currently in
  panel 3's own corner (`der.get('router')`, `disp_p95`, `leader_flips`). Dean explicitly said
  "don't know" where this should go, given panel 3's corner is being reassigned to TTFT percentiles
  below — resolved in § Placement.
- **ITL, ρ** — already computed (`der.get('itl_fit')`, panel 5's own corner note today:
  `fit['A_ms_per_req']`, `fit['B_ms']`, `fit.get('rho')`). Not new data; Dean's ask was to move/bundle
  it with panel 6's "other analyzer logic" — resolved in § Placement, but see the caveat there.
- **Time per work unit** — panel 1b doesn't compute this today. Derivable from data panel 1b already
  has: total output tokens delivered over the run's own wall-clock span, or over a specific interval
  — coder's call on exact framing (mean seconds-per-1000-tokens, or tokens-per-second restated as a
  per-unit-time figure — pick whichever reads most naturally next to panel 1b's existing
  offered/delivered/capacity content).
- **Costs / utilization** — **new derived metric, not currently computed anywhere.** Two candidate
  numbers, both cheap from data already in every bundle: (a) utilization — mean or time-integrated
  `served_g / slots_g` from panel 5's own existing series (`render_real_trace.py` ~lines 746-762);
  (b) cost — replica-seconds, `Σ ready(t) · Δt` over the replica timeseries already read for every
  other panel. Pick one or both; this is genuinely new scope, budget more time for it than the other
  bullets above.

[↑ TOC](#toc)

## Placement, final {#placement}

Resolving the two things Dean's own table left open:

- **Router imbalance moves to panel 4.** Panel 3's corner is now TTFT percentiles (below); panel 4
  is otherwise not carrying corner info in Dean's table and has room. This is a placement call this
  spec is making, not Dean's explicit instruction — flag it back if he wants it somewhere else once
  rendered, but don't leave it stranded with no home.
- **ITL/ρ**: keep on panel 5 rather than moving to panel 6. Dean's own table said "6 (probably)... with
  other analyzer logic," but panel 6 (post-Task-3 redesign) is now a signed replica-delta-per-analyzer
  line graph with its own dense legend/marker-key content — cramming ITL/ρ text into that corner too
  risks the same density problem Task 2's fix-round and Task 3's own commit message both explicitly
  flagged as a recurring lesson on this branch. Panel 5 already renders this note today and has room;
  leave it there unless Dean says otherwise after seeing the render.

**Final table:**

| info | panel |
|---|---|
| # requests total, cutoff count; cumulative % "good" (<30s) | 1a |
| TTFT/wait-time p50/p75/p90/p95 | 3 |
| boot-time mean, scale-down time, drain time (shortened) | 2 |
| router imbalance, leader flips, oscillation | 4 |
| ITL, ρ | 5 (unchanged from today) |
| time per work unit | 1b |
| costs / utilization | 5 or new — coder's call, see above |

[↑ TOC](#toc)

## What NOT to do {#not-to-do}

- Do not touch the figure's own title (Task 1's domain, already correct).
- Do not touch panel 6's content or legend — it's dense enough post-Task-3; this spec deliberately
  keeps ITL/ρ off it for that reason.
- Do not invent new per-request extraction if `reqs` is empty for a given run — degrade the new
  corner text the same way panel 1a already degrades (no crash, an informative "unavailable" note),
  reusing the existing empty-bundle convention rather than a new one.

[↑ TOC](#toc)

## Verification {#verification}

- Re-render at least 2 cells: one with full per-request data (TTFT percentiles should populate) and
  one without (should degrade cleanly, matching panel 1a's own existing behavior for that case).
- Confirm no panel's corner text overflows or collides with its legend — check panel 3 (TTFT text +
  its own legend, post-Task-2/fix-round density work) and panel 4 (new router-imbalance text) most
  carefully, since those are the two panels gaining new text in a spot that previously had none or
  less.
- Confirm the cost/utilization number (whichever framing chosen) is sane against a hand-check on one
  run — e.g. utilization should be between 0 and 1, replica-seconds should roughly match `Σ ready`
  eyeballed off panel 2.

[↑ TOC](#toc)
