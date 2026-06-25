---
type: review
pr: 1127
title: "checklists for analyzer in WVA"
author: asm582
status: LGTM — future items captured below
date: 2026-06-25
---

# PR #1127 — Future Items

LGTM given current scope. Items below are not blockers; file as GitHub issues at Dean's direction.

---

## F1 — Living scenario taxonomy doc

The three scenarios in `analyzer-checklists.md` (Prefill-heavy, Decode-heavy, Symmetrical) are
explicitly illustrative. There is no home for growing this list over time as new use cases emerge
(ramp/staircase, cold-start, burst, decode-heavy with KV pressure, …).

**Action:** Create a living doc (or section) that serves as the canonical scenario registry. New
analyzer PRs and blog posts draw from it; it is extended as community requirements become concrete.
The checklists doc links to it as the authoritative source.

---

## F2 — Periodic re-evaluation of existing analyzers

Currently benchmark results are captured once, at PR time. As scenarios are added and larger
changes (model upgrades, EPP changes, new WVA releases) land, existing analyzer results go stale.

**Action:** Define a cadence (per release, per blog, or triggered by significant infra change) for
re-running benchmarks across all registered analyzers. Costly and out of current scope — needs
resource/process discussion before committing to a frequency.

---

## F3 — Baseline is a moving target; new analyzer PR as re-run opportunity

A new analyzer being submitted is a natural trigger to:
1. Re-run existing analyzers under the same conditions — confirms the baseline and produces an
   honest head-to-head comparison.
2. Verify that when the new analyzer is **not** enabled, existing benchmark numbers are unaffected
   (no side-effect regression).

**Action:** Add to the checklist: new analyzer PRs should include a re-run of at least the
relevant reference analyzer(s) under identical settings, and confirm no regression on the
non-enabled path. Ties to F2 (shared re-evaluation process).

---

## F4 — User guide requirement (author-added, confirm coverage)

The PR author added a recording / user guide requirement (results formatted per `benchmark.md`
template, with config parameters alongside results). Confirm this is sufficient or whether a
dedicated per-analyzer user guide (configuration + expected outcomes) should be a separate
checklist item — consistent with the initial graduation-target proposal.
