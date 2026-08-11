from: plans (planner session, pokprod benchmark thread)
to: sync
session: pokprod benchmark — persist-results discussion, round 2

## What changed — two independent threads landed the same afternoon

**Thread A — Dean, directly on `benchmark` (3 commits, `abf20efc`/`c6f6c313`/`d315bd9e`):** figures now
have a **tracked** home. `session-notes/campaign-viz/<cell>/{panels.png,coverage.json}` — 3.0 MB, all
seven cells, `bundle.json` deliberately excluded (1.5 MB × 4 staircase cells, regenerable from raw
results). **Verified clean of the leaked bearer token before adding** (grep, not assumed — the token
lives only in the sibling `run/*.yaml` manifests, untouched by this copy). Also: a cross-cell summary
table reading each cell's own saved artifacts (not the live cluster), with the load-bearing design
choice of separate "configured" vs "analyzers seen" columns — the latter counted from each cell's saved
controller log, so a throughput-only cell whose log still shows saturation lines is directly visible
rather than papered over by echoing the config. And a "run a subset of campaign cells" capability.
`benchmark__results-tree-and-campaign-persistence.md` is now `.DONE`.

**Thread B — planner, on `plans` (this session, two commits: `06f9739b` + one more):** the campaign
results doc (`planning/ta-pokprod-campaign-20260810-results.md`) went through a second review pass with
Dean, catching real errors and surfacing a design gap:

1. **Finding 3 was misattributed** — a saturation-v2 internal signal reported as a finding of a cell
   where saturation wasn't voting. Corrected in place.
2. **The "1a gap" root cause was wrong** — claimed a harness bug; checked directly, `run_metadata.yaml`
   and all five per-stage summaries exist with real data, only `per_request_lifecycle_metrics.json` is
   0 bytes (likely the OOM the workload file's own sizing math predicts). Dwell cells are missing
   per-request resolution only, not "blind."
3. **SELF-CHECK 3 and 1b's dashed capacity line were conflated** — no shared code path; corrected.
4. **New: `tput_knee()`/`capacity()` were never actually reviewed by Dean**, despite reading as settled
   in the doc. Both landed in the toolchain's first commit (`ca7f2c74`, Dean's own, `autoscaling-viz`);
   every recorded approval there is about the migration, not this design. Dean's objection to
   `max_conc_pred` — a single global number checked once against one observed peak, with no time-window
   or regime handling — holds up on inspection. Three concrete open questions are now recorded for Dean.
5. **A concrete lead confirmed:** EPP debug logs (`logs/epp_pods.log`, already on disk for every cell)
   carry per-request scorer output — `kv-cache-utilization-scorer`, `prefix-cache-scorer`,
   `queue-scorer`, keyed by `x-request-id` per candidate endpoint — a real, previously-unmined signal for
   the per-request discovery task and for question 2 above.

**Reconciled note, not a conflict:** thread A's tracked-figure work and thread B's doc corrections don't
overlap in content, but thread B's § *Folder structure* (proposing `benchmark/runs/<id>/{config,raw,
viz}/`, one lifecycle per run) is a **further refinement** on top of what thread A already shipped
(`session-notes/campaign-viz/`, cell-keyed rather than run-keyed). Both are real and neither supersedes
the other yet — flagged in the doc itself, not resolved here.

## New decisions from the same discussion, none yet executed

- Per-request collection in `inference-perf` is disabled going forward (unreliable, disk-heavy, and
  per-*packet* not per-request despite the name); a discovery task is specified instead.
- No scaling-decision-reason panel exists in the renderer; flagged as the priority addition.
- Coverage checks (`coverage.json`'s 16 rows) have no doc explaining what each asserts.
- All harness fixes stay on Dean's fork; upstream issues/PRs explicitly deferred; excessive generated
  data discarded by a to-be-written playbook, keeping only the reproducible config set.

## Dwell deep-dive handed off separately

Dean is opening a dedicated new session for the dwell limit cycle (Finding 2). Self-contained brief:
`session/handoffs/dwell-deep-dive__handoff.md`. Not addressed to a session name yet since it doesn't
exist; route it once opened.

## Update CURRENT.md — benchmark entry

Addendum to the existing 2026-08-10 abstract (do not rewrite — campaign facts and GPU-freed state stand):

> **Addendum 2026-08-10, second pass (same day):** two parallel threads landed. **On `benchmark`
> directly (Dean):** campaign figures given a tracked home at `session-notes/campaign-viz/<cell>/`
> (3.0 MB, verified clean of the leaked token before committing), plus a cross-cell summary table
> (configured-vs-seen analyzer columns — directly visible if a disable didn't take effect) and a
> run-subset capability. **On `plans` (review of the results doc):** two of its four findings needed
> correction (a saturation-internal signal misattributed to a non-voting cell; a wrong root-cause claim
> about missing per-request data) — both fixed in place, not silently. **Deeper issue surfaced:** the
> viz toolchain's capacity-estimation functions (`tput_knee()`, `capacity()`/`max_conc_pred`) were never
> actually reviewed by Dean despite reading as settled — three concrete design questions are now open for
> him. A confirmed lead: EPP debug logs carry per-request scorer output, unmined until now. **New
> decisions, none yet executed:** per-request collection disabled going forward; a further-refined
> results tree (`benchmark/runs/<id>/{config,raw,viz}/`) proposed on top of what's already shipped;
> harness fixes stay fork-only; a scaling-decision panel and coverage-check docs both flagged missing.
> **The dwell limit cycle is being spun out to its own dedicated session** — see
> `dwell-deep-dive__handoff.md`. Nothing pushed, no cluster contact.

## Pending handoffs table

- **`benchmark__results-tree-and-campaign-persistence.md` → now `.DONE`** — remove from the open table.
- **New open trigger:** `benchmark__viz-model-review-and-per-request-discovery.md` — refines the now-DONE
  trigger's remaining scope (per-request discovery, EPP scorer mining, scaling-decision panel, coverage
  docs) plus the `runs/<id>/` folder-structure refinement.
- **New, unaddressed:** `dwell-deep-dive__handoff.md` — flag as "awaiting Dean to open the session," not
  stalled.

## Open questions / follow-ups

- **Still owed by Dean:** rotate the leaked bearer token (unchanged, still the one item with a clock on
  it); the `tput_knee()`/`capacity()` review — new, three questions in the doc.
- **Still open, planner-side:** audit plans text written between the retracted sat-disable claim and its
  correction for framing that assumed list-omission doesn't stop saturation voting (it does, per §20.21 —
  stale text risk, not a live bug).
- **Unresolved, flagged not fixed:** thread A's `session-notes/campaign-viz/` (cell-keyed) vs. thread B's
  proposed `benchmark/runs/<id>/` (run-keyed, config+raw+viz coupled) — two shapes for the same problem,
  landed in parallel. Needs a call on which is canonical, or how they compose.
