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
