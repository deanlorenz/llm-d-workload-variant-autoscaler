from: plans (planner session "📐 TA-0.9 Planner")
session: ta-cd-review-triage

## Context

Triaged ev-shindin's review comments on the two OPEN TA-0.9 PRs — C (#1480,
`ta-model-level-demand`) and D (#1481, `ta-veto-liveness`) — with Dean, 2026-07-29. Four review
points, dispositions locked. No code written; both Type-3 plans updated; kickoff triggers placed;
reviewer replies drafted (held for Dean's approval — not posted).

## What changed (plans branch, planner-owned)

- **`planning/ta-veto-liveness-plan.md`** — new section **"Review follow-ups (round 2 —
  ev-shindin PR #1481 comments)"** ({#followups2}), three folds on top of the round-1 commits:
  - **D.1** — de-duplicate the `"no-data"`/`"error"` `VariantCapacity.Reason` sentinels
    (duplicated in `pipeline/analyzer_helpers.go` and the saturation_v2 producer). Shared exported
    constant in the lower layer if import layering allows; else a cross-package pin test.
  - **D.2** — selective prune of `lastGoodAnalysis` (evict departed model keys at the per-cycle
    boundary; NOT a per-cycle reset — the latch is cross-cycle; in-memory, also clears on restart).
  - **D.3** — **demand-liveness detector** (Dean's design answering the C-side "never-live demand"
    point): a second latch (throughput demand timestamp) in the SAME `lastGoodAnalysis` map under
    a synthetic inner key; WARN when supply is live but the supply↔demand timestamp gap ≥ the
    staleness window. **Observability only — cannot veto** (synthetic key never matches a real
    `nr.Name` in the keyed Live/veto reads; and zero demand is a legitimate state that only permits
    scale-down). Comment + dev-guide required. DEFERRED note: future per-pod demand extends the
    inner key with a pod component.
  - TOC refreshed (`toc-refresh.sh`).
- **`planning/ta-model-level-demand-plan.md`** — new section **"Review follow-ups (ev-shindin PR
  #1480 comments)"** ({#followups}), **both comment-only, no logic change on C**:
  - **C.1** — comment near the demand assembly: arrival=0 → demand=0 is intentional/safe (permits
    but never forces scale-down; never drives scale-up); cites decision #4 (no served-rate floor).
  - **C.2** — comment at `anyEPP := input.ArrivalRate > 0`: RequestRate is a completion rate (>0
    during drain) so it's deliberately NOT used as a broken-arrival cross-check; durable
    broken-arrival is surfaced by the engine liveness path's demand detector (D.3), not here.
  - TOC refreshed.
- Kickoff triggers placed (doorbell-only): `ta-veto-liveness__round2-followups.md`,
  `ta-model-level-demand__review-comments.md`.
- Reviewer reply drafts: `scratch/ta-cd-reviewer-replies-draft.md` (DRAFT — not posted; awaiting
  Dean's per-comment approval + explicit `gh` confirmation).

## Update CURRENT.md

- **PR Status rows** for C (#1480) and D (#1481): append that ev-shindin's review comments were
  triaged 2026-07-29 and round-2 folds are planned —
  - D #1481: "ev-shindin comments triaged → round-2 folds planned: D.1 sentinel de-dup, D.2
    lastGoodAnalysis prune, D.3 demand-liveness detector (warn-only, cannot veto). Plan updated
    ({#followups2}); kickoff trigger placed. Coding not yet started."
  - C #1480: "ev-shindin comments triaged → C.1/C.2 comment-only fold planned (no logic change).
    Plan updated ({#followups}); kickoff trigger placed. Coding not yet started."
- **Next steps** — under the TA 0.9 item, add: "C + D have ev-shindin review comments triaged
  (2026-07-29); round-2 folds planned and coder kickoffs placed (C: 2 comments; D: D.1 de-dup +
  D.2 prune + D.3 demand-liveness detector). Reviewer replies drafted in
  `scratch/ta-cd-reviewer-replies-draft.md`, awaiting Dean's approval before posting. No coder
  work started yet."
- **Recent activity** — optional tail 1-liner: "2026-07-29 — TA 0.9 C/D reviewer-comment triage:
  C comment-only (C.1/C.2); D round-2 folds (D.1 sentinel de-dup, D.2 prune, D.3 demand-liveness
  warn-only detector). Plans + kickoffs + reply drafts done; no code yet."

### Rebase (Dean-authorized 2026-07-29) — supersedes the no-rebase-live-PR default for C/D only

- Both C and D are to be **rebased onto current `upstream/main` (`28a58b77`)** as the first step
  of the round-2 coder work. Dean explicitly directed this (it overrides
  [[feedback-no-rebase-live-pr-branches]] for the C/D round-2 case only). Rebase step added to both
  plans as **C.0 {#c0}** / **D.0 {#d0}** (with the CONVENTIONS non-trivial-rebase procedure: coder
  writes the pre-rebase plan in its own status file, per-file diff inventory, per-commit
  message-vs-diff, post-rebase anchor re-verification).
- State to record: the local branches were **already** forward-rebased onto `11d70a8a` (the #1479
  merge) by a prior coder session but **never pushed** — local C `25f09a87` / D `b3f75650`, while
  origin/PRs still show pre-rebase C `7aec2645` / D `19c9a122` (see the two `plan__ta-*-rebased.md`
  handoffs). Upstream then advanced `11d70a8a`→`28a58b77` (#1473 Makefile, #1450
  saturation→saturationv1, #1448 pkg→internal/queueing, #1487 GLOBAL_OPT_INTERVAL wiring). The
  round-2 rebase carries them the rest of the way. Renames miss C/D's core files; **#1487** is the
  one D must re-verify (its liveness threshold reads `OptimizationInterval`).
- **PR Status rows** should additionally note: "to be rebased `11d70a8a`→`28a58b77` (Dean-authorized)
  as part of round-2; single `--force-with-lease` will carry origin from the pre-rebase tip to the
  folded+rebased tip." Net force-push jumps origin C `7aec2645`→(new) and D `19c9a122`→(new).

## Open questions / follow-ups

- Reply drafts need Dean's approval and an explicit `gh` confirmation before posting (no GitHub
  action without per-action confirmation). Also decide whether D's reply keeps the "related
  detector" paragraph.
- D.2 prune site: coder must locate the per-cycle model-enumeration site one layer above
  `updateLivenessAndSetLive`; flagged as a hand-back point in the plan if the active-model set
  isn't cleanly available there.
- D.1 shared-constant vs pin-test decision depends on the real import graph (producer package
  vs `pipeline`); coder decides, defaulting to the pin test if a shared constant would cycle.
