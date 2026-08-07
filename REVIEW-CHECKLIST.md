# Autoscaling-viz — multi-shape integration: REVIEW & RESUME state

**Status:** implementation + verification COMPLETE; committed locally on `plans` (scratch/POC,
no DCO); **not pushed**; awaiting Dean's review.
**Date:** 2026-08-05

## What this is

The `plans/scratch/autoscaling-viz/` teaching deck now renders **all 5 demand shapes**
(`bump` / `trapezoid` / `stepup` / `stepdown` / `spike`) with a **uniform max-replica cap
enforced at actuation** across every sizer. This file is the resume point after a clean
restart. The approved plan lived at `~/.claude/plans/gentle-singing-lantern.md` — **outside the
repo, lost on clean** — so its decisions were folded into the committed design doc before this
commit (see Pointers).

## Done this session (all committed in this unit)

- **§0 cap-at-actuation for all sizers** — `run.py`: `cap_for(shape)`, `CAP_DEFAULT = 10`,
  `CAP_BY_SHAPE = {}` (empty ⇒ 10 everywhere); `max_replicas=cap_for(shape)` wired into the 6 WVA
  calls + `run_closed_loop` + `gen_supply_static`. WVA cap is cap-only, no floor.
- **§1 run.py parametrized by shape** — loops `DEMO_SHAPES`, emits `{stem}-{shape}.png` /
  `{stem}-{shape}-latency.png`, `09-wait-cdf-{shape}.png`, `10-cost-quality-{shape}.png`,
  `summary-{shape}.md` (+ `summary.md` = bump alias).
- **§2 report.py** — `SHAPES` / `SHAPE_NOTES`; Compare shape switcher (both panes); Browse
  all-shapes gallery (main + collapsible latency); Table per-shape tables + switcher; Tradeoffs
  per-shape figures.
- **§4 REPORT.md** — per-shape **Demand shapes** section.
- **stability.py** — "uncapped by design" intro note.
- **Verification** — `run.py` / `report.py` / `stability.py` re-run clean; markdown double-label
  stutter fixed; figure inventory checked (old unsuffixed PNGs removed).
- **Cap-lesson eval → no escalation.** At cap=10 the Q-vs-HPA lesson holds on all shapes, so
  `CAP_BY_SHAPE` stays empty (10 everywhere). Details in design doc §8.1 item 11.
- **Design-doc capture** — §8.1 item 11 (cap decision + eval + multi-shape + spike lesson),
  §6.1 cap bullet, §6.5 spike-vs-standalone-stress distinction, items 8/9 marked done, §9 Files
  refreshed (+109/−22).

## Review checklist (do this on the clean session)

- **A — the rendered deck** (highest value; docs only describe it). Open
  `out/index.html` (`file://`): Compare switcher swaps *both* panes + banner; Browse shows all 5
  shapes for a chosen policy; Table shows correct per-shape numbers; Tradeoffs shows 5 separate
  cost-quality + wait-CDF figures (bump first); spike banner reads as a real lesson.
- **B — the frozen numbers** in design doc §8.1 item 11, checked against `out/summary-*.md`:
  trapezoid +11.3 pp / stepup +8.8 pp / stepdown +10.3 pp (good%≤15 s, qexp − qaware); HPA
  ≈1.8–2.5× qexp replica·s; spike 7–57 % dropped. These are now durable record — confirm none is
  wrong.
  > ⚠️ **STALE as of 2026-08-06 — do not re-verify these three deltas yet.** The warm-start fix
  > (follow-up 3 below) invalidated them, and the burn-in prelude will move them again. They are
  > re-frozen in **one** pass after burn-in lands. `stepdown +10.3 pp` in particular is now
  > structurally gone (both Q sizers saturate on a pure scale-down). The **HPA "≈2.5×" wording
  > stays regardless** (Dean's standing call).
- **C — three judgment calls** (are these what you want recorded?): (1) escalate-to-15-never-higher
  rule + two triggers + the no-escalation verdict; (2) spike = teaching-only, not calibrated, as a
  first-class rendered shape distinct from §6.5's ideal-only stress; (3) flat per-shape switcher
  **supersedes** item 9's two-level category→workload chooser (recorded as abandoned).
- **D — push decision.** Commit is local only. Pushing needs Dean's explicit OK; `plans` →
  `origin` only, **never upstream**; `--force-with-lease` only after history rewrite.

## How to resume

- Be in the `plans` worktree (`.../llm-d-workload-variant-autoscaler/plans`).
- Deck: `scratch/autoscaling-viz/out/index.html`.
- Decisions: `scratch/autoscaling-viz/autoscaling-behavioral-demo-design.md` §8.1 item 11 (cap +
  multi-shape), §6.1 (cap bullet), §6.5 (spike distinction).
- Regenerate if needed: `./.venv/bin/python run.py && ./.venv/bin/python report.py`
  (python3.12 venv; prefer `uv` for new deps).
- `stability.py` is uncapped by design (measures knob response, 4 shapes) — do not add a cap.

## Not done / open

- Dean's review (A/B/C/D) then the push decision. Nothing else pending in this mission.

---

## Round 2 (2026-08-05) — Dean reviewed A + B; 7 changes LOCKED

**Status of round 2:** all 7 items IMPLEMENTED + regenerated 2026-08-06 (plots.py + sweep.py +
report.py; `run.py`/`sweep.py`/`stability.py`/`report.py` re-run clean). **Uncommitted** — deck
regenerated on top of `6f36b905`, pending Dean's re-review then a commit. Verification below.

**Round-2 verification (structural, on the regenerated `out/index.html`):**
- Per-tab independent shape switchers present + wired: `data-shape-for` = compare / browse / table /
  tradeA / tradeB / cap (each its own `.shapepick`; `setShapeFor(scope,…)` redraws only that tab via
  `SHAPE_RENDER`). No shared `state.shape` string; no orphaned `setShape()`.
- Compare: `levelMetas()` equalizes `meta-L`/`meta-R` to the taller; re-runs on tab-activate + resize.
- Browse: single-shape switcher (main + collapsible latency), gallery loop removed.
- Table: 5 per-shape tables, each with a dark-red ruled-off `failed (>60s) %` row (`tr.failrow`);
  independent switcher.
- Tradeoffs: side-by-side A/B columns, each rendering its shape's cost-quality + wait-CDF.
- Sweeps: sticky jump-nav (8 buttons, all targets resolve) + new cap-sweep section (trapezoid /
  stepup / stepdown, each with the two-panel figure + cost/quality sub-tables; bump/spike noted
  cap-inert). Cap switcher offers only the swept shapes (read from the DOM).

**To re-review (open `out/index.html` via `file://`):** confirm each tab's switcher swaps only its
own content; Compare panes start level; Table failed row reads dark-red; Tradeoffs shows two shapes
at once; Sweeps nav jumps + cap section switches. Then the push decision (item D) — still needs
Dean's explicit OK.

### Round-2 follow-ups (2026-08-06, Dean flagged two issues on the `dd648c93` render)

1. **Table tab "missing shape selector".** Root cause: the picker buttons also carry `data-shape`,
   and `renderTableShape` hid by `#view-table [data-shape]` (descendant) — so 4 of the 5 pills got
   hidden along with the non-selected content divs, collapsing the switcher to one pill. Fix: scope
   to direct children `#view-table > [data-shape]` (the 5 content divs only). Verified with jsdom —
   picker now shows all 5 pills, exactly one content div visible. (The cap sweep already dodged this
   by using a distinct `data-cap-shape`.)
2. **Sweeps "not clear what shape was used".** The six knob sweeps all run on the **bump** reference
   shape but said so nowhere. Added an explicit shape note in three places: `sweep.py` intro (→
   `out/sweep.md`), the deck Sweeps intro tnote (`report.py` → `index.html`), and the `REPORT.md`
   Parameter-sweeps intro. Cap sweep already names its shape per figure/switcher.

Both fixes regenerated (`sweep.py` → `report.py`) and re-verified via jsdom. **Uncommitted** at time
of writing → committing now on top of `dd648c93`; still not pushed (item D pending Dean's OK).

3. **Cold-start artifact — warm-start LANDED, burn-in prelude APPROVED (2026-08-06).** Dean:
   *"shapes like step down actually test a steep step up first, creating a queue and affecting the
   rest of the test"*; *"the demand is 'broken' in the same fashion"*; *"all should start flat rate
   not from zero."* Root cause: no history before t=0, producing **two coupled artifacts** — a
   fleet that cold-boots from 0 regardless of t=0 demand, and trailing-window estimators (sizer
   input **and** plotted offered curves) that read ~0 at t=0 and ramp over the window. Design
   captured in design doc **§2.4 "Initial state"** (+ the real-trace caveat) and **§8.2**.

   **Landed + verified in `sim.py`** (analytic seed `W0 = rate_profile(shape,0) × size_mean`,
   self-zeroing for `bump`): `initial_rate` / `initial_work_rate` / `_warm_replicas` /
   `_initial_fleet_count`; seeded `offered_work_rate` (sizer input) and `_windowed_rate` +
   `sample()` offered curves; warm fleets in all open-loop sizers **and** the closed-loop
   `Simulator` (`_seed_warm_fleet`, `start = up = 0`, billed from t=0). Verified: warm fleet per
   shape (bump 0 / trapezoid 2 / stepup 2 / stepdown 5 / spike 2), `actual[t=0]` matches, closed
   loop **holds** at `n0` (controllers hold on a zero metric) instead of collapsing to `min`,
   stepdown's early `peak_qlen` now 0.0, all demand curves start flat. Full regen clean.

   **Consequence — `stepdown` flipped from hardest shape to easiest**, and its old "hardest"
   numbers were the artifact. Dean's three calls: (1) **reframe** the §8.1 finding as a pure
   scale-down test (done); (2) **update** the frozen numbers to post-fix values; (3) **seed
   in-flight state too** so served-throughput and in-system `L(t)` also start flat.

   **(3) resolved as a burn-in prelude, not analytic injection** (Dean: *"burn-in is obviously
   better… it also solves the demand part — only need to start from non-zero replicas"*, plus the
   hard requirement *"you MUST disable any autoscaling at the warm up time"*). My earlier
   "too expensive" caution was **mispriced**: it costed a *negative-time* design; the positive-time
   offset framing (`t0 = T_burn` in the load meta; shift only in `sample()`) is ~8 sites and
   *deletes* the analytic estimator seed. Measured: `run.py` **61 s** → ~75 s; `sweep.py` **3 s**
   warm (204/204 from `out/.sweep-cache.json`) with one cold ~5 min pass when burn-in changes the
   cache key. Spec in design §8.2.

   **Sequencing (agreed):** apply only the burn-in-*invariant* doc edits now — the §8.1 stepdown
   reframe, §2.4 mechanism + real-trace caveat, §8.2 items incl. Dean's two forward directions
   (**input-signal noise**, **request-shape change**, under his framing that *right-sizing /
   steady state is the actual money-saver, transition speed less so*) — and mark §B's deltas
   **STALE**. Numbers are re-frozen in **one** pass after burn-in lands, not twice.

   **Still open:** implement burn-in (`sim.py` + `run.py` + `sweep.py` cache key) → regenerate
   (one cold sweep) → verify served-side and `L(t)` also start flat → then the single number-freeze
   pass in design §8.1 item 11 + §B here, and refresh §2.4's "successor, in flight" note to
   past tense. Item **D (push) still pending Dean's OK**; everything remains local on `plans`.

4. **`stress_ideal.py`'s figure was missed by the burn-in regeneration — found and FIXED 2026-08-07.**
   The regenerate step in follow-up 3 covered `run.py` / `sweep.py` / `report.py` but not
   `stress_ideal.py`, which consumes `run.BURN_IN` (`stress_ideal.py:38`) and therefore also changed
   output. So `out/stress-ideal-spike.png` was still a **pre-burn-in** render. Established from
   history rather than inferred: the PNG was last written by `e95901a0` (2026-08-05), burn-in entered
   `run.py` / `sim.py` in `4556398f` (2026-08-07), and `b7d8d5c1` *"regenerate all artifacts under
   burn-in"* did not touch it. A fresh render differs in **140,382 of 2,613,600 pixels (5.37 %)**,
   with the diff bounded to (99,238)–(1191,1749) — inside the plot area, so curves moved, not
   metadata or a timestamp.

   This was the single artifact contradicting this file's *"deck regenerated & honest"* status, and it
   is worth knowing it was the **only** one: a full regeneration on 2026-08-07 reproduced **161 of 162**
   tracked artifacts byte-for-byte (across a Python 3.12 → 3.14 change), this figure being the lone
   exception. Corrected render is committed. Lesson for the next regeneration: the deck has **four**
   entry points, not three — `run.py`, `sweep.py`, `report.py`, **and** `stress_ideal.py`.

**Original locked plan (for reference):** design decisions locked in discussion; deck was at
`6f36b905` when the plan was written.

- **B (numbers) = GREEN** *(as of 2026-08-05; the three deltas are **SUPERSEDED** by follow-up 3 —
  warm-start + burn-in. Historical record, do not re-verify.)* Deltas exact (trapezoid +11.3 /
  stepup +8.8 / stepdown +10.3 pp good%≤15s); spike 7–57 % dropped; static@10 100 %/0-failed; HPA
  replica·s 1.80–2.52× qexp — **"2.5×" wording stays (Dean: good enough), do not change**.
- **Stability** — leave `out/stability.md` standalone (not a tab); Dean reviewed the md, good as-is.

**Plan (7 items):**
1. **Per-tab independent shape state.** Today Compare+Table share one global `state.shape` via
   `setShape()` ("Table follows compare" — disliked). Give every tab its own Compare-style pill switcher.
2. **Compare — level the panes.** Misalignment is variable-height `meta-L`/`meta-R` text, not the PNGs
   (fixed 1320×1800). JS-equalize both meta heights to the taller so figures start level.
3. **Browse — switcher, not gallery.** Replace all-shapes gallery with a shape switcher (one shape's main
   + foldable latency for the chosen policy). Keep the fold.
4. **Table — independent switcher + dark-red failed row.** Own shape state; style `failed (>60s) %` row
   dark-red font + top border rule separating it from the served-within bands.
5. **Tradeoffs — full side-by-side.** Pick shape A / shape B; render each shape's cost-quality + wait-CDF
   in L/R columns. Shorten `render_wait_cdf` (11×5.4) + `render_cost_quality` (9.5×6) in plots.py so CDF +
   Pareto both fit on screen.
6. **Sweeps — cumulative line + nav.** (a) In `render_sweep` quality panel, add a per-group cumulative
   **served ≤15s (good+almost)** line, KEEP the existing ≤2s good line (`s["within_pct"][1]`; add `_good15`
   to `sweep.py` `_metrics`, `good15` to `_group`). (b) Add jump-to-section nav buttons.
7. **NEW cap sweep.** None exists (`MAX_REPLICAS=10` is a fixed constant, never swept). Add to sweep.py:
   sweep `max_replicas ∈ [5,8,10,12,15,20,30]` per shape (**per-shape switcher**: stepup+stepdown+trapezoid
   where the cap bites the Q sizers; bump/spike cap-inert — note them). Emit cost (**provisioned·seconds**)
   + **factor-vs-ideal** tables (ideal ≈1714 bump / 2227 stepup / 1976 stepdown prov·s) + a two-panel
   `render_sweep` figure; land it as a new **Sweeps** section. Teaching point: HPA desired (557–1766) ≫ any
   sane cap ⇒ HPA pins to the cap like `static` (cost ∝ cap); Q sizers rise with cap then flatten at their
   natural peak (14–27); ideal flat (peak ~5). Range stays bounded — no log axis.

**Implementation order:** plots.py + sweep.py → regen `run.py` (tradeoff figs) + `sweep.py` (sweeps + cap)
→ report.py (all HTML) → regen `report.py` → verify.
Regenerate: `./.venv/bin/python run.py && ./.venv/bin/python sweep.py && ./.venv/bin/python report.py`.
`stability.py` stays uncapped by design — do not add a cap.
