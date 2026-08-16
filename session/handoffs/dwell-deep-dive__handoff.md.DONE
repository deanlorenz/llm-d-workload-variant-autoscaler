from: plans (planner session, pokprod benchmark thread)
to: a new dedicated session (Dean is opening one, 2026-08-10)
session: dwell limit cycle — deep dive

## Why this handoff exists

Dean wants to go deep on the dwell limit cycle and asked for it to be its own dedicated session rather
than folded into the ongoing pokprod benchmark thread. This handoff is meant to be sufficient on its own
— read it and the two docs it points at, and you should not need to ask the prior session anything to
get started.

## What "the dwell limit cycle" is

Across two campaign cells run on `dhl-wva-209` (pokprod) on 2026-08-10 — `m-satta-dwell` (saturation +
throughput analyzer both configured) and `m-sat-dwell` (saturation only) — the controller's desired
replica count rides up to the cap of **10**, then falls back to **2**, then climbs again: **two full
excursions** inside one ~35-minute run, on a workload whose offered rate is a five-stage staircase-then-
hold-then-drain, not itself oscillating at that period. See panel 2 in either cell's figures — the
`desired` (red) and `ready` (purple) traces visibly saw-tooth between 2 and 10.

**What's established (Finding 2 in the results doc, high confidence):** the cycle is **analyzer-
independent** — both cells show the same shape despite different analyzer configs — so it's a property
of the controller/workload interaction, not of which analyzer is voting. Panel 2 also shows the
mechanism is **replica lag**: in `m-satta-dwell` the `desired` line jumps to 10 while `ready` trails by
300+ seconds (boot mean **316 s over 9 steps**, vs 70–95 s on the non-dwell staircase cells) — the
controller keeps asking for more capacity while the previous batch of pods is still booting.

**What's NOT established, and is presumably the point of the deep dive:** *why* the lag is that long on
this profile specifically, whether it's a workload artifact (a profile-specific interaction, not a
general property) or a controller-design issue, and what — if anything — should change. Finding 4 in the
same doc (`rc = 0` and util ≈ 0.2 while the replica target still oscillates) may or may not be the same
phenomenon; it is explicitly flagged as uninvestigated and could be a second, related thread.

## Where everything is

**Primary doc:** [`planning/ta-pokprod-campaign-20260810-results.md`](../../planning/ta-pokprod-campaign-20260810-results.md)
— read **Finding 2** (the dwell limit cycle itself) and **Finding 4** (the `rc=0` oscillation, possibly
related) in full. The doc also carries corrections made *during* this handoff's authoring session —
worth reading before trusting anything: Finding 3 was originally misattributed to the wrong cell and has
since been corrected in place; the "1a gap" section's original root-cause claim was flat wrong and is
also corrected in place. Read the doc as it stands now, not from memory of an earlier summary.

**Design context:** [`planning/ta-pokprod-testing-plan.md`](../../planning/ta-pokprod-testing-plan.md)
§7.6 "The mid-band dwell is a controller-configuration lever, not a workload lever" and §7.6.1 (cold-
resume state) — this is the *design* argument that predicted the dwell would be hard to reach by raising
offered rate alone, written before the campaign ran. §7.4 carries the original scenario asks this
profile was built to satisfy.

**The workload itself:** `benchmark/dean-*/results/*/ta_autoscale_dwell.yaml` (any dwell cell's results
dir carries a copy) — this file's own header is unusually detailed prior art: it documents the rate-
invariance hypothesis, the replica-quantization-sawtooth fallback, exact sizing math, and an explicit
"honest caveat" section written *before* the run, predicting some of what was then observed. Read this
before re-deriving anything it already covers.

**Raw evidence, per stage** (per-request trace is NOT available for dwell cells — see below):
`benchmark/dean-*/results/*/stage_N_lifecycle_metrics.json` (5 files per cell) and
`summary_lifecycle_metrics.json`. `controller.log` in the same directory carries the WVA controller's
own per-tick decisions and reason codes (`P1-obs`/`P2-hist`/`P3-k2`/`P4-k1`, source-checked against
`saturation_v2/types.go`) if the deep dive needs to look at *why* a given tick scaled rather than just
*that* it did.

**Figures:** currently mirrored at `plans/scratch/campaign-20260810-viz/{m-satta-dwell,m-sat-dwell,m-ta-dwell}.png`
— **this mirror is being deprecated** (see the results doc's new § *Folder structure*; Dean wants
figures living with their run data, not copied). If that migration has landed by the time you read this,
prefer whatever `benchmark/runs/<id>/viz/panels.png` now exists; the mirror was only ever a stopgap so
the results doc's links would resolve.

## Known gaps that bear directly on this investigation

- **No per-request trace for the dwell cells.** `per_request_lifecycle_metrics.json` is 0 bytes in every
  dwell cell — almost certainly an OOM against the harness pod's memory limit (the workload file's own
  sizing math predicts this at ~11.3 GB against an ~11.9 GB failure boundary). Per-stage summaries
  survived intact and are a real fallback (rate, latency distribution, failure count, token throughput —
  5 data points per cell, one per stage) but there is no continuous per-request timeline for the dwell
  cells. Dean has separately asked to disable per-request collection in inference-perf generally (it's
  unreliable, disk-heavy, and per-*packet* rather than per-*request* despite the name) and find fallback
  signals from other logs instead — that discovery task is tracked in the results doc and may or may not
  be relevant to what you need for the dwell investigation specifically.
- **No scaling-decision-reason panel exists.** Dean wants to see the reason codes plotted, not just
  grepped. If your deep dive needs to correlate replica changes with *why* the controller decided that,
  today that means reading `controller.log` by hand — there's no rendered panel for it yet.
- **One run per cell, no repeats.** Both dwell cells are single runs. If the deep dive concludes
  something mechanism-level, it is not yet backed by repetition.
- **`m-ta-dwell` (TA-only) is not usable** — truncated at ~360 s of a ~40-minute planned run (the
  campaign was stopped mid-cell), so the three-way analyzer comparison that exists for the staircase
  profile (Finding 1) does not yet exist for dwell.

## Scope note

This session's write scope is presumably the same as any planner/coder session on this project — see
`plans/session/CONVENTIONS.md` if you haven't already, particularly the worktree-scope and git
write-verb rules. Nothing about this handoff authorizes anything beyond normal scope; it's a pointer to
where the open question lives, not new permissions.
