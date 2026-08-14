# Autoscaling-viz — Follow-on Work (Epic Plan)

**Status:** ACTIVE — one doc for all Type 1 follow-on items. Split trigger is **ownership, not
scope**: if a second planner session picks up one of the OPEN items below concurrently with this
one, split that item into its own Type 2 at that point (per CONVENTIONS, Type-2/Type-3 docs are
multi-writer, but two planners actively editing the same epic doc at once is exactly the collision
that convention exists to prevent). Single-planner, single-doc until that happens.

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

**What this doc is.** A Type 2 (roadmap) tracking every follow-on item flagged by
[`autoscaling-viz-design.md`](autoscaling-viz-design.md) (the Type 1, Status: DRAFT) as open —
panel gaps, the estimation-model open questions, the un-designed EPP-signal direction, and the
undocumented coverage checks. Each item below is either **DECIDED** (Dean has stated the
requirement; a Type 3 code spec can be written and handed to a coder) or **OPEN** (still needs
Dean's input before any code spec is written). Nothing in this doc authorizes a coder to touch
the estimation model (`tput_knee()`/`capacity()`) — that stays gated on Dean's review of the three
open questions in the Type 1, independent of anything below.

## TOC {#toc}

- [Item 1 — scaling-decision-reason panel {#item-1-decision-panel}](#item-1--scaling-decision-reason-panel-item-1-decision-panel) L34:51
- [Item 2 — panel 4 queue-source design {#item-2-panel4}](#item-2--panel-4-queue-source-design-item-2-panel4) L52:63
- [Item 3 — estimation-model open questions {#item-3-estimation}](#item-3--estimation-model-open-questions-item-3-estimation) L64:79
- [Item 4 — EPP scorer debug-log signal {#item-4-epp-signal}](#item-4--epp-scorer-debug-log-signal-item-4-epp-signal) L80:91
- [Item 5 — coverage-check reference doc {#item-5-coverage-doc}](#item-5--coverage-check-reference-doc-item-5-coverage-doc) L92:103
- [Item 6 — folder-structure / make-target consistency {#item-6-folder-structure}](#item-6--folder-structure--make-target-consistency-item-6-folder-structure) L104:114
- [Item 7 — 2026-08-13 panel review: bug-fix cluster + panel 3/1b/6 redesign {#item-7-panel-review}](#item-7--2026-08-13-panel-review-bug-fix-cluster--panel-31b6-redesign-item-7-panel-review) L115:178
- [Item 8 — backlog: viz output missing for 7 post-campaign runs {#item-8-rerun-viz-backlog}](#item-8--backlog-viz-output-missing-for-7-post-campaign-runs-item-8-rerun-viz-backlog) L179:210
- [Item 9 — version stamp renders + regenerate stale/missing viz output {#item-9-version-stamp-regen}](#item-9--version-stamp-renders--regenerate-stalemissing-viz-output-item-9-version-stamp-regen) L211:231
- [Cross-references](#cross-references) L232:238

## Item 1 — scaling-decision-reason panel {#item-1-decision-panel}

**DECIDED.** Dean asked for a bottom panel showing WVA's logged scaling *reasons*
(`P1-obs`/`P2-hist`/`P3-k2`/`P4-k1` capacity-source codes, `scaling-decision` actions), aligned on
the x-axis with panel 2's replica trace, instead of a hand-grep of `controller.log` per finding.
Stated as a requirement in both the campaign doc (`ta-pokprod-campaign-20260810-results.md` §
*Missing: a scaling-decision panel*) and the Type 1 (§ *Known gap*). Data confirmed present and
clean in the already-gathered 2026-08-10 campaign controller logs (`analyzer-result` and
`scaling-decision` JSON lines) — no new run needed.

**Code spec:** [`autoscaling-viz-decision-panel-plan.md`](autoscaling-viz-decision-panel-plan.md)
(Type 3, this session, 2026-08-12). **Implemented** (`cff4e4c0`), reviewed by Dean 2026-08-13 —
the shipped reason-code-marker design is now **superseded** by
[`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md) § Item H
(signed replica-delta per analyzer). See Item 7 below for the redesign's tracking.

[↑ TOC](#toc)

## Item 2 — panel 4 queue-source design {#item-2-panel4}

**PARKED 2026-08-13** (was OPEN). `render_real_trace.py` panel 4 is explicitly titled
`INTERIM: … which one panel 4 should draw is an open design question` in the renderer itself.
[`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md) § Item G
records Dean's call: the felt need for a panel-4 redesign was largely a panel-3 readability
problem, resolved by that review's Item F instead. Panel 4 stays exactly as-is (all three queue
sources drawn) and is explicitly reserved as a sandbox for future experiments — "brainstorm on p4
later." Do not schedule panel-4 work against this item; it is deliberately not a task.

[↑ TOC](#toc)

## Item 3 — estimation-model open questions {#item-3-estimation}

**OPEN, gated on Dean's review of the Type 1.** Three questions carried from the campaign doc,
restated in the Type 1 § *Open design questions*:

1. Should `capacity()` report a windowed/regime-classified value instead of one global number?
2. What is the local error of `max_conc_pred` as a function of time/regime, rather than one
   point-in-time comparison against `max_conc_obs`?
3. Is `tput_knee()`'s argmax-over-stable-bins the right quantity for the panel-1b/5 ceiling lines,
   given it's calibrated from the same curve it overlays?

No code spec possible until these are answered — this is explicitly the regime-decomposition
critique (Type 1 § *Known limitation*), separate from and out of scope for the panel work in Item 1.

[↑ TOC](#toc)

## Item 4 — EPP scorer debug-log signal {#item-4-epp-signal}

**OPEN, not yet scoped.** The EPP debug log (`logs/epp_pods.log`, confirmed present, 11 MB/cell for
the 2026-08-10 campaign) carries a per-request, per-pod signal (`kv-cache-utilization-scorer`,
`prefix-cache-scorer`, `queue-scorer` scores plus live KV/queue state) that neither `capacity()` nor
the coverage checks use today. Two candidate uses flagged in the Type 1 (§ *A candidate signal*),
neither designed in: a genuine per-request prefix-hit rate, and a windowed/regime-aware capacity
estimate feeding Item 3's open question 2. Deciding whether/how to use it is future work, contingent
on Item 3's resolution.

[↑ TOC](#toc)

## Item 5 — coverage-check reference doc {#item-5-coverage-doc}

**DECIDED as an ask, not yet written.** Campaign doc: "a short reference — one line per check,
naming the assertion and its threshold" for the extractor's 16 PASS/FAIL self-check rows, to live in
the `autoscaling-viz` worktree. The Type 1 § *Coverage-check specification* already contains exactly
this table (16 rows: capability / asserts / threshold / on-FAIL) — writing the doc is transcribing an
already-authored table into a Type 4 (reference) doc under `autoscaling-viz/`, not new design work.
Small, low-risk; can be folded into the same coder session as Item 1 or done separately. Not written
up as its own Type 3 yet — flag for Dean whether to bundle with Item 1's coder session.

[↑ TOC](#toc)

## Item 6 — folder-structure / make-target consistency {#item-6-folder-structure}

**OPEN, unresolved as of 2026-08-10.** Campaign doc § *Folder structure*: "I still don't understand
where the results live and what is the folder structure. Someone running the make target should get
a consistent result." Lives primarily on the `benchmark` worktree/branch (results-tree ownership),
not `autoscaling-viz` — cross-referenced here because it affects where a coder finds bundle.json/
coverage.json inputs for panel work, but the design decision itself is `benchmark`'s, not this epic's.
Do not schedule viz coder work against this until it resolves on the `benchmark` side.

[↑ TOC](#toc)

## Item 7 — 2026-08-13 panel review: bug-fix cluster + panel 3/1b/6 redesign {#item-7-panel-review}

**DECIDED (multiple sub-items) + one NEEDS-SCOPING.** Full findings:
[`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md), from
Dean's review of a fresh render of the Item-1 panel-6 sample plus his standing observation across
other already-rendered `panels.png` files. Summary:

- **Bug-fix cluster** (Items A, B, D of that doc): broken figure title, panel 1a rendering empty on
  some runs (root cause not yet confirmed — may be correct given missing per-request data, needs
  triage), panel 3 legend overflow / hatch readability / missing bar-top outlines.
- **DECIDED design changes**: panel 1b y-axis capping when capacity dwarfs work (Item C); panel 3
  redesigned to a request-domain breakdown — running/draining/waiting/EPP-queue/total, KV ceiling on
  secondary axis or dropped (Item F); panel 6 redesigned from reason-code markers to a signed
  replica-delta-per-analyzer line graph (Item H).
- **Explicitly parked, not a task**: panel 4 (Item G — superseded Item 2's OPEN status above; kept
  as a sandbox, not scheduled).
- **NEEDS-SCOPING before any coder work**: Item E, the sim-vs-real work-unit divergence (simulated
  work/s panel reads "too low" vs. real panel 3) — needs a short investigation (is time-in-system
  actually inferable for real runs?) before choosing a resolution direction; do not let a coder pick
  one unilaterally.
- **Governing principle** (Item *Convergence*): real and simulated renderers should converge on the
  same panel shapes for the same concern going forward — this governs how C/F/H get implemented,
  not just what they look like once done.

**Code specs, written 2026-08-13:**
- [`autoscaling-viz-bugfix-cluster-plan.md`](autoscaling-viz-bugfix-cluster-plan.md) — title fix,
  panel 1a triage, panel 3 legend/hatch/outline. Do this one first — lowest risk, and its findings
  (esp. panel 1a's root cause) inform how to read the redesign specs.
- [`autoscaling-viz-panel3-redesign-plan.md`](autoscaling-viz-panel3-redesign-plan.md) — panel 1b
  y-axis capping + panel 3 request-domain redesign (running/draining/waiting/EPP-queue/total, KV
  ceiling placement). Depends on the bug-fix cluster's Fix 3 landing first.
- [`autoscaling-viz-panel6-redesign-plan.md`](autoscaling-viz-panel6-redesign-plan.md) — supersedes
  Item 1's shipped design; signed replica-delta-per-analyzer line graph, requires an extractor change
  to carry `rc`/`sc`/`prc` through (currently dropped). Independent of the other two specs — can be
  done in any order relative to them.

Item E (sim-vs-real divergence) remains explicitly unscoped — none of the three specs above resolve
it, by design (each says so in its own scope section).

**Follow-up review, same day (all-cells render sweep):**
[`autoscaling-viz-panel-review-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md) —
Dean's review of the first full render of every campaign cell against Task 1+2's landed code.
Confirmed working, no action: panel 1b's y-axis cap, panel 2, panel 1a, panel 3's KV-ceiling
secondary-axis behavior, the pod-number legend key. New findings:
- **Item I** — figure title still wrong on some cells (`m-satta-staircase`/`m-sat-staircase`), not
  yet root-caused, separate from Task 1's already-fixed defect.
- **Item J — CONFIRMED BUG, code spec written**: `pod_drain_windows()`'s backward scan has no lower
  bound tied to the replica set's actual `desired` transition, so a pod that was busy for a long
  time before a drain event gets its *entire* busy history mislabeled as "draining." Root-caused
  against real data (`m-ta-staircase`, pod `r2tnh`). Spec:
  [`autoscaling-viz-drain-window-fix-plan.md`](autoscaling-viz-drain-window-fix-plan.md) — queued as
  **Task 4** (after Task 3 finishes; not interrupting it).
- **Item K** — panel 3 visual scheme (consistent per-pod color; dots=draining, dashes=waiting, both
  thinner; very thin black outline on all bars). Blocked on Item J landing first — no Type 3 yet.
- **Item L — code spec written 2026-08-14**, availability check done: TTFT percentiles are NOT
  blocked on new extraction (per-request `ttft` field already exists, just needs aggregation);
  router imbalance moves to panel 4 (resolving the "don't know" gap); ITL/ρ stays on panel 5 rather
  than moving to panel 6 (panel 6 is too dense post-Task-3); cost/utilization is genuinely new
  derived scope (replica-seconds and/or served/slots ratio, both cheap from existing series). Spec:
  [`autoscaling-viz-corner-info-plan.md`](autoscaling-viz-corner-info-plan.md) — queued as **Task 7**
  (after Task 6 finishes; not interrupting it).

[↑ TOC](#toc)

## Item 8 — backlog: viz output missing for 7 post-campaign runs {#item-8-rerun-viz-backlog}

**Low-priority backlog, not blocking.** Flagged via
`session/handoffs/plan__rerun-results-need-viz.md` (from the pokprod/benchmark-execution planner,
2026-08-13) — seven benchmark runs since the 2026-08-10 campaign have no `viz/` output, listed with
real result numbers (no figures) in
[`ta-pokprod-rerun-results-20260813.md`](ta-pokprod-rerun-results-20260813.md):
`dean-20260812-152105-714` (m-ta-prefill-knee), `dean-20260812-203217-894` (m-ta-calibration-probe,
OOM'd attempt), `dean-20260812-231722-822` (clean retry), `dean-20260813-000928-609` (m-ta-dwell
rerun), `dean-20260813-005321-943` (m-satta-dwell rerun), `dean-20260813-013728-756` (m-sat-dwell
rerun), `dean-20260813-130251-004` (m-ta-calibration-probe-p4, parallelism-4 validation).

**DONE, commit `cf76a238`.** The planner's initial read — "5 of 7 already covered by the
2026-08-13 all-cells sweep" — **did not hold up** and should not be trusted as a pattern: several
cell names (`m-ta-calibration-probe`, `m-ta-dwell`, `m-satta-dwell`, `m-sat-dwell`) each have more
than one real run directory, the sweep's PNGs carry no run ID in their title and no bundle saved
alongside them, and `ta-pokprod-rerun-results-20260813.md` itself states **"No viz output exists
for any run in this doc"** — directly contradicting the "already covered" framing. All 7 runs were
re-extracted fresh with unambiguous provenance, at
`session-notes/review-samples/backlog-rerun-20260813/<cell-name>/{bundle.json,coverage.json,panels.png}`.
One run (`dean-20260813-130251-004`) had 4 parallel results leaves, not one — all 4 extracted and
rendered separately. No code changes; pure toolchain invocation, no review trigger needed.

Two things worth carrying forward: the OOM'd attempt (`dean-20260812-203217-894`) visually confirms
the crash description (cut short mid-ramp, no scale-down reached); `m-sat-dwell`'s rerun (18 pods)
visually confirms the campaign's P99-TTFT/saturation-lags-demand finding — panel 6's saturation
delta and panel 4's queue-depth peak line up exactly in time. The pre-existing loose files at the
top of `session-notes/review-samples/` (Task 1-4 artifacts, the ambiguous `all-panels-20260813/`
sweep) are left untouched — reorganizing/committing them is a separate call, not done here.

[↑ TOC](#toc)

## Item 9 — version stamp renders + regenerate stale/missing viz output {#item-9-version-stamp-regen}

**DECIDED, code spec written 2026-08-14.** Dean's direct review of the 7 existing `panels.png`
files (the first time anyone opened one since 2026-08-12) found they're all stale — up to 6 commits
behind current render code, with no way to tell from the file itself — plus 14+ run directories
with no `viz/` output at all. Direct ask: "verify all panels.png are using the latest code, add a
version somewhere so we can track this."

**Code spec:** [`autoscaling-viz-version-stamp-and-regen-plan.md`](autoscaling-viz-version-stamp-and-regen-plan.md).
Two parts, in order: (1) stamp every render with the extractor's and renderer's own git SHA — in the
existing footer text (human-visible) and `coverage.json` (machine-checkable) — plus PNG-embedded
metadata (`tEXt`/`iTXt` chunks via matplotlib's `savefig(metadata=...)`) so a copy separated from its
sidecar `coverage.json` is still self-describing; (2) only then regenerate the 7 stale + up to 14
never-rendered run directories, so the regenerated batch doesn't recreate the same blind spot one
version later. Source handoff:
`session/handoffs/plan__viz-regen-batch-plus-versioning-ask.md`.

[↑ TOC](#toc)

---

## Cross-references

- Type 1: [`autoscaling-viz-design.md`](autoscaling-viz-design.md) (Status: DRAFT)
- Campaign doc: [`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md)
- Kickoff handoff: `session/handoffs/autoscaling-viz-panels__kickoff.md`

[↑ TOC](#toc)
