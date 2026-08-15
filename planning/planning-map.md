# Planning map — what we have, by topic and type

**Status: DRAFT — first pass, for discussion.** Built by scanning every file in `planning/` plus
[`session/CURRENT.md`](../session/CURRENT.md)'s PR Status table. Not exhaustive on every doc's
internal detail — links go to the real docs for that. This is the index, not a replacement for any
of them.

**Type names** (see [`session/CONVENTIONS.md`](../session/CONVENTIONS.md) and
[`doc-and-session-model.md`](doc-and-session-model.md), which is migrating the numbers to names —
both are used below since the migration isn't finished):

| # | Name | What |
|---|---|---|
| 1 | design | Mission-level concepts/algorithms/goals. Frozen once written. |
| 2 | roadmap (epic plan) | Mission-level living plan, tracks progress across PRs. |
| 3 | task plan (code spec) | One per PR/implementation step. Coder executes this. |
| 4 | reference | Post-implementation docs — live on **code branches** under `docs/developer-guide/`, not here. |
| 5 | session state | `session/CURRENT.md`, `session/history.md`. |
| 6 | review | Implementation-correctness findings. `Status: DRAFT` until Dean finalizes. |

Two doc shapes don't fit that spine and get their own sections below: **community PR reviews**
(reviewing *other* contributors' upstream PRs, not our own missions) and **internal tooling docs**
(process/session-management, not WVA product work).

---

## How to read this

For each topic: **Type 1 → Type 2 → Type 3(s) → Type 6(s) → PR(s) + current status.** A missing
link means that type doesn't exist for this topic — some missions never got a Type 1, some never
needed a Type 2, some Type 3s have no Type 6 yet. Gaps are called out explicitly, not left silent.

PR status is a **pointer to `session/CURRENT.md`**, not restated in detail — that table is the
single source of truth and changes faster than this doc should chase it. Where a PR has already
landed, only the PR number + merged/closed state is repeated here for orientation.

---

## 1. ThroughputAnalyzer (TA) — the core mission

The oldest and largest thread. Runs through several sub-phases; later ones supersede earlier ones
in scope but the docs are kept, not deleted.

**Type 1 (design):**
- [`TA-notation.md`](TA-notation.md), [`TA-overview.md`](TA-overview.md), [`TA-supply.md`](TA-supply.md), [`TA-demand.md`](TA-demand.md) — the core theory, split by concern.

**Type 2 (roadmap):**
- [`TA-Plan.md`](TA-Plan.md) — original mission roadmap.
- [`TA-forward-plan.md`](TA-forward-plan.md) — post-#1250 backlog (26 issues + 5 deferred features, P0/P1/P2 tiers). This is the live one for "what's left."
- [`TA-e2e-plan.md`](TA-e2e-plan.md) — E2E test roadmap, its own track.

**Type 3 (task plans) — original PR-1..5 stack, all landed:**
- [`TA-PR1-plan.md`](TA-PR1-plan.md) … [`TA-PR5-plan.md`](TA-PR5-plan.md), plus [`TA-PR5-bob.md`](TA-PR5-bob.md) (variant/experiment doc, check before trusting the name) and [`TA3.1-plan.md`](TA3.1-plan.md) (a later phase, not a typo of TA-PR3).

**Type 3 (task plans) — the lettered follow-up PRs (post-TA3, all their own small missions):**
- [`ta-devguide-fixes-plan.md`](ta-devguide-fixes-plan.md) → review [`ta-devguide-fixes-review.md`](ta-devguide-fixes-review.md)
- [`ta-registration-safety-plan.md`](ta-registration-safety-plan.md) → review [`ta-registration-safety-review.md`](ta-registration-safety-review.md)
- [`ta-gate-observability-plan.md`](ta-gate-observability-plan.md) → review [`ta-gate-observability-review.md`](ta-gate-observability-review.md)
- [`ta-model-level-demand-plan.md`](ta-model-level-demand-plan.md) → review [`ta-model-level-demand-review.md`](ta-model-level-demand-review.md)
- [`ta-veto-liveness-plan.md`](ta-veto-liveness-plan.md) → review [`ta-veto-liveness-review.md`](ta-veto-liveness-review.md)
- [`ta-correctness-guards-plan.md`](ta-correctness-guards-plan.md) → review [`ta-correctness-guards-review.md`](ta-correctness-guards-review.md)
- [`ta-itl-demand-test-gaps-plan.md`](ta-itl-demand-test-gaps-plan.md) → review [`ta-itl-demand-test-gaps-review.md`](ta-itl-demand-test-gaps-review.md)

**PRs / status:** all six TA 0.9 PRs (#1478, #1479, #1480, #1481, #1502, #1503) **MERGED**
2026-07-30, `main` tip `6bfb73e1`. The lettered follow-ups above are also merged (F's #1511
MERGED 2026-08-07; the others landed earlier — check `session/history.md` → PR Status for exact
SHAs, not restated here). **Open backlog:** `TA-forward-plan.md`'s P1 items (collector key
unification I-1, test-rot I-11) — see CURRENT.md § Next steps.

**Gap:** no single Type 6 covers the *whole* TA3 mission; each lettered follow-up has its own,
which is fine but means "is TA3 done" requires reading `TA-forward-plan.md`, not a review doc.

---

## 2. Multi-analyzer engine

Sibling to TA — the engine architecture TA (and saturation) plug into.

**Type 1 (design):**
- [`multi-analyzer-design.md`](multi-analyzer-design.md) — the core design, § Future direction is
  the live backlog (F3, F4, F10, F12, F13 — tracked in CURRENT.md § Issues to Open).
- [`error-paths-design.md`](error-paths-design.md) — analyzer error/lifecycle semantics, feeds
  `wva-analyzer-lifecycle-plan.md` below.

**Type 2 (roadmap):**
- [`ENGINE-multi-analyzer-plan.md`](ENGINE-multi-analyzer-plan.md)
- [`multi-analyzer-addendum-plan.md`](multi-analyzer-addendum-plan.md) — amends the above.

**Type 3 (task plans):**
- [`multi-analyzer-registration-plan.md`](multi-analyzer-registration-plan.md)
- [`multi-analyzer-threshold-plan.md`](multi-analyzer-threshold-plan.md)
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md)
- [`wva-analyzer-lifecycle-plan.md`](wva-analyzer-lifecycle-plan.md) — **PARTIALLY REJECTED**, see
  CURRENT.md PR Status row. Half A (lifecycle) viable, Half B (disabling saturation) needs the F1
  pre-analysis-extraction fix first, unscoped.
- [`PR1266-fixup-effectiveEnabled.md`](PR1266-fixup-effectiveEnabled.md) — superseded by the above.

**Reference (working notes, not Type 1/2/3):**
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md), [`multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md), [`multi-analyzer-postrefactor-map.md`](multi-analyzer-postrefactor-map.md), [`scale-from-to-zero-analysis.md`](scale-from-to-zero-analysis.md) — trace/analysis docs, cited by other plans rather than standalone missions.

**PRs / status:** engine split + registration/threshold/optimizer PRs — landed (see
`session/history.md`). **Open:** `wva-analyzer-lifecycle-plan.md`'s carve/scope decision is
**blocked on Dean** (CURRENT.md § Next steps). F1 pre-analysis-extraction is a prerequisite for
Half B and is itself unscoped.

---

## 3. Combined-analyzer-optimizer / anchor-refactor — the current biggest mission

**Type 1 (design):**
- [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (FINAL) +
  [`combined-analyzer-optimizer-design-addendum-1.md`](combined-analyzer-optimizer-design-addendum-1.md)
  (Rev 7, governs the anchor-refactor/PR-2 overlap) → review
  [`combined-analyzer-optimizer-design-review.md`](combined-analyzer-optimizer-design-review.md).

**Type 3 (task plans) — three PRs, one goldens gate:**
- [`ta-anchor-refactor-plan.md`](ta-anchor-refactor-plan.md) → review [`ta-anchor-refactor-review.md`](ta-anchor-refactor-review.md) — **superseded**, see
  [`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md) below (also
  [`ta-anchor-refactor-v2-coder-checklist.md`](ta-anchor-refactor-v2-coder-checklist.md),
  [`ta-anchor-refactor-v2-scale-from-zero-note.md`](ta-anchor-refactor-v2-scale-from-zero-note.md))
  → review [`ta-anchor-refactor-v2-code-review.md`](ta-anchor-refactor-v2-code-review.md)
  (`Status: DRAFT`, pending Dean's FINAL call — content is done, just not stamped).
- [`ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md) → review [`ta-anchor-goldens-review.md`](ta-anchor-goldens-review.md) — content already landed via PR-1's squash; PR is now a no-op needing only a close call.
- [`ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) (+ its
  [`ta-anchor-dynamic-refresh-PENDING-EDITS.md`](ta-anchor-dynamic-refresh-PENDING-EDITS.md)) →
  review [`ta-anchor-dynamic-refresh-review.md`](ta-anchor-dynamic-refresh-review.md) (Findings
  76/77/78, internal review clean, no external review yet).

**PRs / status:** PR-1 `ta-anchor-refactor-v2` = **#1516 MERGED** 2026-08-07 (squash `57f3fe64`).
PR-2 `ta-anchor-dynamic-refresh` = **#1523 OPEN, pushed, CI green**, awaiting external review —
full detail in CURRENT.md § Recent activity, not restated here. Goldens = **#1513 OPEN but no-op**,
needs only a close call.

**Gap:** two PR-1 review docs are `Status: DRAFT` despite being functionally done — needs Dean's
FINAL stamp, tracked as an open item, not a missing artifact.

---

## 4. Optimizer / cost allocation

**Type 1 (design):**
- [`optimal-cost-allocation-design.md`](optimal-cost-allocation-design.md)
- [`optimizer-coordination-design.md`](optimizer-coordination-design.md) — the "clean design"
  rewrite for PD-role-ceiling, in progress (Phase 2 drafted, awaiting Dean).
- [`p-d-logic-explainer.md`](p-d-logic-explainer.md) — explainer, not a mission doc.

**Type 3 (task plans):**
- [`optimal-cost-allocation-plan.md`](optimal-cost-allocation-plan.md)
- [`optimizer-pd-role-ceiling-plan.md`](optimizer-pd-role-ceiling-plan.md) → review
  [`optimizer-pd-role-ceiling-review.md`](optimizer-pd-role-ceiling-review.md).

**PRs / status:** `optimizer-pd-role-ceiling` — **implemented, all 10 tests landed, not pushed**;
dev-guide edits made but uncommitted; blocked on the Phase-2 clean-design discussion in
`optimizer-coordination-design.md` before push (CURRENT.md PR Status row).

**No Type 2** for this topic — it has never had a standalone roadmap; the design docs double as
both. Worth deciding if that's fine permanently or a gap to fill once PD-role-ceiling ships.

---

## 5. pokprod TA benchmark campaign

The largest non-code-PR effort — cluster experiments, not a GitHub PR stack (yet).

**Type 1 (design):**
- [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md) — durable contracts
  (env-guard, safety rules).

**Type 2 (roadmap):**
- [`ta-pokprod-roadmap.md`](ta-pokprod-roadmap.md) (early) →
  [`ta-pokprod-testing-plan.md`](ta-pokprod-testing-plan.md) (**SUPERSEDED**, split 2026-08-12) →
  [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (current — tooling track T1-T12) +
  [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) (current — live scenario surface,
  "what still needs Dean at a glance").
- [`ta-pokprod-history.md`](ta-pokprod-history.md) — append-only decision ledger (D-1…D-53+),
  grep-lookup by design, not read top-to-bottom.

**Type 3 (task plans):**
- [`pokprod-scratch-tools-doc-coverage-cleanup-plan.md`](pokprod-scratch-tools-doc-coverage-cleanup-plan.md) — draft cleanup for 5 undocumented scratch tools (D-51, not started).
- [`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md) — per-request trace recovery tool.

**Results docs (not Type 6 — empirical findings, not code review):**
- [`ta-pokprod-campaign-report.md`](ta-pokprod-campaign-report.md) — **current authoritative
  report**, 21 experiments / 6 workload shapes, coverage matrix closed.
- [`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md),
  [`ta-pokprod-rerun-results-20260813.md`](ta-pokprod-rerun-results-20260813.md) — superseded by
  the above, kept with pointer headers.
- [`ta-pokprod-campaign-report-v2-spec.md`](ta-pokprod-campaign-report-v2-spec.md),
  [`ta-pokprod-workload-coverage.md`](ta-pokprod-workload-coverage.md) — supporting specs.

**Status:** no PR yet — this is pre-product cluster validation. Open items tracked in
`ta-pokprod-open-scenarios.md`, not restated here; two are flagged actionable (report relocation
to `benchmark/docs/`, in flight; scratch-tools doc cleanup, not started).

---

## 6. autoscaling-viz — visualization/analysis toolchain

**Type 1 (design):**
- [`autoscaling-viz-design.md`](autoscaling-viz-design.md)

**Type 2 (roadmap):**
- [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md) — the live epic (6 items,
  most still open).

**Type 3 (task plans) — many, one per panel/feature; this cluster has the most churn:**
- [`autoscaling-viz-bugfix-cluster-plan.md`](autoscaling-viz-bugfix-cluster-plan.md)
- [`autoscaling-viz-corner-info-plan.md`](autoscaling-viz-corner-info-plan.md)
- [`autoscaling-viz-decision-panel-plan.md`](autoscaling-viz-decision-panel-plan.md) — panel 6, landed.
- [`autoscaling-viz-drain-window-fix-plan.md`](autoscaling-viz-drain-window-fix-plan.md)
- [`autoscaling-viz-panel3-redesign-plan.md`](autoscaling-viz-panel3-redesign-plan.md),
  [`autoscaling-viz-panel3-visual-scheme-plan.md`](autoscaling-viz-panel3-visual-scheme-plan.md)
- [`autoscaling-viz-panel6-redesign-plan.md`](autoscaling-viz-panel6-redesign-plan.md)
- [`autoscaling-viz-version-stamp-and-regen-plan.md`](autoscaling-viz-version-stamp-and-regen-plan.md)

**Type 6 (reviews):**
- [`autoscaling-viz-review-20260813.md`](autoscaling-viz-review-20260813.md),
  [`autoscaling-viz-panel-review-20260813.md`](autoscaling-viz-panel-review-20260813.md) (+
  [`...-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md)),
  [`autoscaling-viz-panel-review-20260814.md`](autoscaling-viz-panel-review-20260814.md),
  [`autoscaling-viz-review-ongoing.md`](autoscaling-viz-review-ongoing.md) — living review, not a
  one-shot doc; check its own header for current state.

**Status:** no PR — lives entirely in its own `autoscaling-viz` branch/worktree, not headed
upstream. Panel 4 (queue-source) deferred by Dean. State: `session/status/autoscaling-viz.md`.

**Gap worth naming:** this is the cluster with the most Type-3-per-feature churn relative to its
one Type 2 — worth asking whether some of these should have been tracked as sub-items inside
`autoscaling-viz-followon-plan.md` instead of separate files.

---

## 7. Benchmark harness & observability (distinct from the pokprod campaign above)

**Type 1 (design):**
- [`benchmark-observability-plan.md`](benchmark-observability-plan.md) — decision-table +
  correctness-script direction (this is really Type-1-ish despite the "-plan" name — check content
  before citing as a Type 3).
- [`wva-saturation-cycle-log-plan.md`](wva-saturation-cycle-log-plan.md) — small, standalone
  logging-instrumentation mission.

**Separate, NOT-AUTHORIZED track:**
- [`benchmark-wva-vs-keda.md`](benchmark-wva-vs-keda.md) (Type 1) +
  [`benchmark-wva-vs-keda-plan.md`](benchmark-wva-vs-keda-plan.md) (Type 3) — **do not implement**;
  needs Dean's explicit go-ahead first (see CURRENT.md's STOP block).

**Status:** harness tooling itself is tracked via `session/status/benchmark.md`, not a plan doc —
the plan docs here are about *what to measure*, not the harness build-out.

---

## 8. Collector / VA attribution

**Type 3 (task plans):**
- [`collector-va-attribution-plan.md`](collector-va-attribution-plan.md)
- [`PR1267-impact-and-decisions.md`](PR1267-impact-and-decisions.md),
  [`PR1275-closure-capture.md`](PR1275-closure-capture.md) — PR-scoped decision captures, not full
  Type 3s.

**No Type 1/2** — small enough it never needed one.

---

## 9. Release process

- [`ta-0.9-epic-issues.md`](ta-0.9-epic-issues.md) — epic/issue tracking for the 0.9 release.
- [`ta-0.9-release-notes.md`](ta-0.9-release-notes.md) — release-notes mechanism + Highlights
  drafts. **Unblocked as of the 2026-08-07 code freeze** — see CURRENT.md § Next steps for the
  open tag-point question.

**Not a mission** — a process/release doc, listed here for completeness rather than under the
Type 1-6 spine.

---

## 10. Standalone / small, one-off

Each of these is its own small thing, not part of a named mission:

- [`analyzer-metric-interface-proposal.md`](analyzer-metric-interface-proposal.md) — working notes
  behind PR #1444 → issue #1455 (deprioritized).
- [`autoscaling-evaluation-framework.md`](autoscaling-evaluation-framework.md) — theoretical
  framework, standalone discussion doc.
- [`WVA_position.md`](WVA_position.md) — product positioning/value-prop, not implementation.
- [`wva-1318-k2source-fix-plan.md`](wva-1318-k2source-fix-plan.md) — small standalone fix.
- [`open-items-roadmap.md`](open-items-roadmap.md) — cross-cutting Q1/Q2 priority scoring, already
  consumed (issues filed); historical now.

---

## Community PR review — reviewing *other* contributors' upstream PRs

Distinct category: not our missions, not our code. Each is a one-shot review of someone else's PR
against the upstream project.

| Doc | PR | Status |
|---|---|---|
| [`PR1113-review.md`](PR1113-review.md) | [#1113](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1113) | DRAFT |
| [`PR1129-review.md`](PR1129-review.md) | [#1129](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1129) | FINAL |
| [`PR1245-review.md`](PR1245-review.md) | [#1245](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1245) | DRAFT |
| [`PR1392-review.md`](PR1392-review.md) | #1392 | (frontmatter-tagged, check header) |
| [`PR1442-review.md`](PR1442-review.md) | #1442 | (frontmatter-tagged, check header) |
| [`PR1452-review.md`](PR1452-review.md) | #1452 | rescale Alpha — merged; RC-2/RC-4 re-check pending when Beta lands (CURRENT.md § Next steps) |
| [`PR1470-review.md`](PR1470-review.md) | #1470 | (frontmatter-tagged, check header) |
| [`PR1501-review.md`](PR1501-review.md) | #1501 | FINAL — COMMENTED posted 2026-07-30, incoming, no worktree |
| [`PR1052-deferred-fixes.md`](PR1052-deferred-fixes.md) | #1052 | deferred-fixes list, not a full review |

**Not verified line-by-line here** — several use a YAML frontmatter (`type: review`, `pr:`, `title:`)
instead of the older `Status:` line; worth a pass to normalize if this doc gets adopted.

---

## Internal tooling (session/process infrastructure, not WVA product)

Real work, but a different axis entirely — building the AI-assistant workflow itself, not the
autoscaler. Grouped here so it doesn't clutter the product-mission view above.

**The atomic-step-protocol track (checkpoint/session tooling — the biggest sub-cluster):**
- [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (FINAL, frozen) + 8 addenda
  ([`-addendum-1`](atomic-step-protocol-design-addendum-1.md) through
  [`-addendum-8`](atomic-step-protocol-design-addendum-8.md)) — addendum-7 is the most recent
  (origin-pid guard rewrite, 2026-08-14/15).
- Predecessor: [`micro-rules-design.md`](micro-rules-design.md) — superseded by the above.

**Doc/session model migration:**
- [`doc-and-session-model.md`](doc-and-session-model.md) + [`-addendum-1`](doc-and-session-model-addendum-1.md) — the Type-N → named-type migration this very doc's header refers to.

**Conventions authoring tooling:**
- [`conventions-tooling-spec.md`](conventions-tooling-spec.md),
  [`conventions-authoring-spec.md`](conventions-authoring-spec.md),
  [`conventions-harvest-spec.md`](conventions-harvest-spec.md),
  [`role-skills-spec.md`](role-skills-spec.md), [`step-gates-spec.md`](step-gates-spec.md),
  [`harvest-classification.md`](harvest-classification.md) — one connected effort, splitting
  CONVENTIONS.md into fetch-on-demand pieces. Not yet built.

**Other:**
- [`state-commands-design.md`](state-commands-design.md) — `/s-state-park` etc., landed as skills.
- [`context-cost-reduction-plan.md`](context-cost-reduction-plan.md) — DONE.
- [`spec-as-code-design.md`](spec-as-code-design.md) — AI-authoring-workflow vision, separate from
  atomic-step-protocol; status unclear, worth checking if still active.
- [`litellm-gateway-latency-plan.md`](litellm-gateway-latency-plan.md) — infra investigation
  (proxy latency triage), resolved per memory, not WVA-related at all.
- [`governance-follow-ups.md`](governance-follow-ups.md) — process-incident retrospective
  (scope-boundary violations), open questions not yet actioned.

---

## Gaps and questions this pass surfaced (not fixed, just named)

1. **No Type 2 (roadmap)** for: optimizer/cost-allocation, collector/VA-attribution, benchmark
   harness/observability. Possibly fine — these may be small enough to never need one — but worth
   a deliberate yes/no rather than an accidental gap.
2. **Two DRAFT review docs are functionally FINAL** (`ta-anchor-refactor-v2-code-review.md` and its
   companion) — just needs Dean's stamp, already tracked in CURRENT.md but easy to lose in this
   many files.
3. **autoscaling-viz has 9 Type-3 docs under one Type 2** — the most fragmented cluster relative
   to its roadmap. Worth asking if some should merge into the followon-plan as line items.
4. **Community PR-review docs use two different header conventions** (`Status:` line vs YAML
   frontmatter) — cosmetic, but makes them harder to grep uniformly.
5. **This doc itself will drift** — no mechanism keeps it current. Suggest either a
   `toc-refresh.sh`-style regen script, or treating it as a point-in-time snapshot to be
   regenerated on request rather than maintained continuously (matches how `ta-pokprod-history.md`
   treats its own append-only ledger — don't invent a second maintenance burden).

---

## What this doc deliberately does NOT do

- Does not restate PR status detail — `session/CURRENT.md` is authoritative, this only points.
- Does not open `planning/archive/` (13 files) — everything there is superseded content already
  described by its citing doc above. Say the word if you want that layer indexed too.
- Does not touch `session/status/*.md` or `session/handoffs/*.md` — those are live/ephemeral,
  covered by CURRENT.md's own rolling window, not this static map.
- Does not classify or link Type 4 (reference) docs — they live on code branches under
  `docs/developer-guide/`, not in this `plans` worktree, so there's nothing here to link to yet.
