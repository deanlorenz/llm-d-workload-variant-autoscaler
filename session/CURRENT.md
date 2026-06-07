# Current Work

**Last updated:** 2026-06-07

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md has per-task sections — add or update sections that belong to your current task; never overwrite a sibling task's state. **Per the doc taxonomy, CURRENT.md holds operational state and short abstracts only — design and per-PR detail live in `planning/`.**

---

## Recent activity

- **2026-06-07 — Optimizer Phase 2 complete.** All review findings (B1, B2, T1, N2, N3, N4) addressed in 3 commits on `multi-analyzer-optimizer` (tip `4bfac2fa`, 11 commits total on `multi-analyzer-threshold@b8b823b0`). All gates green, DCO-signed. **Awaiting Dean force-with-lease push and PR creation.** N4 (sort role keys in `costAwareScaleDownRoleIterated`) was committed in `4bfac2fa` before plan was updated to defer per PR #1237 alignment — sort is harmless; planner suggestion is leave as-is, revert if alignment preferred. See [`planning/multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) § Phase 2.
- **2026-06-07 — PR #1237 reviewed.** 6 comments posted on ev-shindin's `fix/role-aware-scaledown` PR (5 top-level + 1 inline on `cheapest := findCheapestVariant(variants)` covering redundancy, implicit-sort-order assumption, lazy walk, and equal-cost tiebreak). Awaiting author response. Post-#1237 rebase plan captured in optimizer plan § Phase 2.
- **2026-06-07 — PR #1225 merged.** `multi-analyzer-registration` landed as `f664a470` on upstream/main. `origin/main` fast-forwarded to match. `multi-analyzer-threshold` (#1228) can now rebase onto main directly and get a clean diff. `multi-analyzer-optimizer` can target main once #1228 merges (or main directly if landing standalone).
- **2026-06-07 — TA-PR5 plan verified** against current multi-analyzer docs. Two stale items fixed: `engine-queue-fix` absorbed into optimizer branch (`3fe287fe`); `NamedAnalyzerResult.SpareD` → `RoleSpare map[string]float64`. Plan ready for the TA3 coder once the multi-analyzer stack lands.
- **2026-06-05 — Optimizer (Item 1) implementation complete.** 7 commits on `multi-analyzer-threshold@b8b823b0`; tip `3fe287fe`. Cross-rebase done. SchedulerQueue wiring absorbed from `engine-queue-fix` (single commit `01ed7d8d` folded into commit 7). All gates green. Ready for force-with-lease push and PR creation. See [`planning/multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md).
- **2026-06-04 — TA-PR5 plan rewritten** for the 3-PR multi-analyzer split. Contract reframed; PR-5 wiring shrinks to a 2-line `cmd/main.go` change + error handling for the new `RegisterAnalyzer(...) error` API. See [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md).
- **2026-06-04 — Multi-analyzer doc taxonomy reorg.** Three per-PR plan docs (`multi-analyzer-{registration,threshold,optimizer}-plan.md`) + one cross-cutting design doc ([`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md)). The design doc holds mission, architecture, alternatives considered (incl. rejected combine-in-engine algorithm), and future direction. Per-PR plans are concrete implementation only.
- **2026-06-03 — Optimizer P/D design** settled on paired (n_P, n_D) scale-up + role-iterated scale-down (Evgeny's PR #1237 approach for the slice path). See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) §§ Architecture/D + Alternatives/A4.
- **2026-05-29 — PR1113 design split** into 3 PRs (registration / threshold / optimizer). See [`planning/PR1113-review.md`](../planning/PR1113-review.md) (historical review of original PR #1113).

---

## PR Status

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| TA1                   | #1051 | **MERGED** 2026-05-12; remove worktree ~2026-05-26                | `c405e8d` |
| TA2                   | #1052 | **MERGED** 2026-05-19; remove worktree ~2026-06-02                | `a8aac2b7` |
| TA3                   | —     | Local only; rebase onto upstream/main now unblocked               | `7506634b` |
| engine-multi-analyzer | #1113 | **Superseded** by `multi-analyzer-registration` (off current main). PR #1113 to be closed by Dean after talking to ev-shindin. Worktree retained for reference. | `fc403f75` |
| multi-analyzer-registration | #1225 | **MERGED** 2026-06-07 as `f664a470` on upstream/main | `5c73ea5f` |
| multi-analyzer-threshold | #1228 | **PR #1228 OPEN** (ready-for-review, ev-shindin); 4 commits directly on `main@f664a470`; force-pushed post-rebase; CI re-running | `b0a50fd3` |
| multi-analyzer-optimizer | — | Local only; 11 commits on `multi-analyzer-threshold@b8b823b0` (Phase 1 + Phase 2 complete; B1/B2/T1/N2/N3/N4 addressed). **Ready for push + PR creation** — awaiting Dean force-with-lease confirmation. | `4bfac2fa` |
| engine-queue-fix      | —     | **Absorbed** into multi-analyzer-optimizer commit 7 (`3fe287fe`). Branch + worktree can be closed/removed. | `01ed7d8` |

---

## Blocked on

- **PR #1228** — rebased onto `main@f664a470`; force-pushed to `origin/multi-analyzer-threshold` (tip `b0a50fd3`, 4 commits, clean diff). CI re-running post-rebase. Awaiting CI signal + ev-shindin review. PR #1113 stays open until Dean closes it post-coordination with ev-shindin. See [`planning/multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md).
- **multi-analyzer-optimizer** — Phase 1 + Phase 2 complete; 11 commits on `multi-analyzer-threshold@b8b823b0` (tip `4bfac2fa`). All review findings (B1, B2, T1, N2, N3, N4) addressed; all gates green. **Awaiting Dean force-with-lease push to `origin/multi-analyzer-optimizer` and PR creation.** Backup branch `backup/multi-analyzer-optimizer-pre-rebase@ae456aa0` available; can be dropped after PR opens. See [`planning/multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) § Phase 2.
- **engine-queue-fix** — absorbed (commit `01ed7d8d` folded into multi-analyzer-optimizer commit 7). Branch + worktree can be closed/removed.

## Next steps

- **Now:** threshold coder — rebase `multi-analyzer-threshold` onto `main`@`f664a470`; push; CI re-runs; await ev-shindin review on the clean diff.
- **Optimizer push + PR.** Force-with-lease push `multi-analyzer-optimizer` to origin (Phase 1 + Phase 2; tip `4bfac2fa`), then open PR (target `multi-analyzer-threshold` while #1228 is open, or `main` if landing standalone — see optimizer plan § Next steps). After push, close `engine-queue-fix` branch + remove its worktree (its commit was absorbed into the optimizer stack).
- **N4 decision.** Sort in `costAwareScaleDownRoleIterated` was committed in `4bfac2fa` before plan was updated to defer N4 per #1237 alignment. Sort is harmless. Suggested: leave as-is. Revert (12th commit) if alignment with #1237's stance is preferred.
- **TA3 coder** — rebase TA3 onto `main`@`f664a470`, then apply contract redesign per `TA-PR5-plan.md` §3 once #1228 + optimizer land. Plan is ready.
- The `engine-multi-analyzer` worktree's run-1 wrap-up is complete; worktree can be removed at Dean's discretion.
- **Parallel track (NOT authorized yet):** WVA-vs-KEDA benchmark — see § Benchmark below.

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

---

## TA3 (ThroughputAnalyzer) — paused

PR-4 (ITL model + scaling signal) and PR-5 (engine wiring) code-complete on TA3 branch (`7506634b`). E2E Steps 1a/1b/2a-2e PASSED on kind cluster `kind-wva-gpu-cluster`. Step 2f (full TA scenarios) pending discussion. Three pre-existing smoke failures (`smoke_test.go:339, :542, :1724`) need triage — regression in main vs. TA3-action.

**Plan docs:** [`planning/TA-Plan.md`](../planning/TA-Plan.md) (overall roadmap, per-PR status, design alternatives), [`planning/TA-PR4-plan.md`](../planning/TA-PR4-plan.md) (PR-4 details incl. Tier-2 fallback B with `lastFittedB`), [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md) (PR-5 wiring; rewritten 2026-06-04 against the 3-PR multi-analyzer split), [`planning/TA-e2e-plan.md`](../planning/TA-e2e-plan.md) (e2e execution + cluster state), [`docs/developer-guide/throughput-analyzer.md`](docs/developer-guide/throughput-analyzer.md) (Type 4 reference).

**Next steps for TA3:** rebase onto upstream/main; apply the contract redesign per `TA-PR5-plan.md` §3 once one of the multi-analyzer PRs merges; triage the 3 pre-existing smoke failures; discuss Step 2f.

---

## Multi-Analyzer mission

Three branches, one mission. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) for cross-cutting design (mission, architecture, alternatives considered, future direction) and [`planning/multi-analyzer-coder-rules.md`](../planning/multi-analyzer-coder-rules.md) for coder agent rules.

| Item | Branch / PR | Plan |
|---|---|---|
| Item 3 — Race-safe analyzer registry | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) **MERGED** 2026-06-07 | [`multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md) |
| Item 2 — Universal threshold post-step + aggregation helpers | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) | [`multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md) |
| Item 1 — Per-analyzer slice → optimizers (delete combine) | `multi-analyzer-optimizer` / not yet open | [`multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) |

The old `engine-multi-analyzer` branch and PR #1113 are **superseded** by the 3-PR split. PR #1113 stays open until Dean closes it post-coordination with ev-shindin.

---

## Deferred fixes (TA2 / PR-3 follow-ups)

10 specific fixes deferred from PR #1052 review for a grouped fixup PR after TA3 merges. See [`planning/PR1052-deferred-fixes.md`](../planning/PR1052-deferred-fixes.md).

---

## Issues to Open (post-merge)

- **Engine SchedulerQueue wiring** — ✅ absorbed into `multi-analyzer-optimizer` commit `3fe287fe`. Threads `CollectSchedulerQueueMetrics` through `prepareModelData` → `modelData.schedulerQueue` → `runV2AnalysisOnly` / `runAnalyzers` → `AnalyzerInput.SchedulerQueue` for all registered analyzers. Lands when the optimizer PR merges.

- **Bob review 1.3 — ArrivalRate staleness check in `computeDemand`** — defer ArrivalRate staleness detection (warn when `ArrivalRate` metric is stale/zero while queue is non-empty) to a later observability PR. Related to the Prometheus gauge work below.

- **Prometheus gauges for ITL model coefficients** — export `wva_throughput_analyzer_itl_model_a` and `wva_throughput_analyzer_itl_model_b` gauges (labels: `namespace`, `model_id`, `variant`, `tier`) so operators can graph ITL model stability in Grafana. Separate observability PR after PR-5 merges. (From Bob's review, 3.1)

- **EPP image version mismatch** — `install.sh` patches EPP to v0.7.0 but local llm-d is v0.5.0; file as infra bug.

- **Gateway prompt bug** — `install_core.sh` fires interactive prompt when `E2E_TESTS_ENABLED=false` even with explicit `INSTALL_GATEWAY_CTRLPLANE=true`; file as infra bug.

- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable; file as Makefile bug.

- **ndots fix standalone PR** — commit `0614d9d` on TA3 (`test/e2e/fixtures/workload_builder.go`) needs its own PR to `main` before or alongside TA3 merge.

- **Per-analyzer observability metrics** — once `multi-analyzer-optimizer` merges and `[]NamedAnalyzerResult` is flowing to the optimizers, expose each analyzer's per-VA demand/capacity as Prometheus gauges labeled by `analyzer_name`. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F4 for detail.

- **Engine model-level RC/SC for disaggregated models** — additive computation in `applyUniversalThreshold` is meaningless for disaggregated models. Once optimizer no longer reads model-level for disaggregated, the buggy computation becomes latent. Follow-up: remove or redefine. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F5 and `multi-analyzer-optimizer-plan.md` § Upstream interactions.

- **Restore TA's EPP/GPS-mismatch SC gate** — TA-PR5 drops the EPP-presence and GPS-mismatch gates that previously suppressed `SpareCapacity`. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F9 and `planning/TA-PR5-plan.md` §7.

- **Replica-count accounting consistency across analyzers** — TA uses `len(variantMetrics)`; sat_v2 uses `readyCount`. Reconcile to a single canonical source. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F8 and `planning/TA-PR5-plan.md` §7.

- **`enabled:false` analyzer should be exempt from `needsScaleDown`** — slice-predicate treats disabled analyzer (Spare=0) as a veto, breaking TA-only scale-down. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Alternatives → A8 and `planning/TA-PR5-plan.md` §7.

- **Cost picker integer-rounding suboptimality** — `CostAwareOptimizer` ranks by `cost/PerReplicaCapacity` and allocates `ceil(RC/PRC)` of the most-efficient variant; under integer rounding (RC < PRC) a high-PRC variant overshoots and can cost more than a cheaper low-PRC variant that still covers RC (e.g. A cost10/PRC10 vs B cost4/PRC3, RC=3 → picks A@10, B@4 is cheaper+sufficient). Pre-existing (legacy cost optimizer); unchanged by multi-analyzer slice migration or optimizer Phase 3 unification. Multi-dimensional bounded knapsack (NP-hard) but tiny in practice → brute force; or compromise = cheapest-efficiency bulk + direct-cost tail when last replica is below util X. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F13.

- **Per-role RC/SC canonical end-to-end (drop optimizer synthesis)** — optimizer Phase 3 uses option (b): synthesize a `"both"` role from model-level RC/SC for non-disaggregated models. Option (a) future: engine always populates `RoleCapacities` (incl. `"both"`), making per-role the single source of truth, dropping the model-level RC/SC scalars (resolves F5) and the `NamedAnalyzerResult.Remaining/Spare` scalars. Ripples into #1228 contract + TA analyzer. Open after optimizer PR merges. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F12.

- **Multi-analyzer dev-guide polish** — currently `docs/developer-guide/multi-analyzer-pipeline.md` is a stub on the optimizer branch with a link to the design doc on the plans-branch fork. After reviewer comments on #1225 + #1228 + optimizer PR are addressed and the PRs reach final shape, fold the design content (architecture, alternatives, future direction from [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md)) plus per-PR implementation detail into the dev-guide, replacing the stub. Cover all three PRs (registration / threshold / optimizer). Doc-only commit on each branch (or a single dev-guide commit landing after the merges).

- **Fold queueing-model into the V2 multi-analyzer engine** — open after the optimizer PR merges. QM (`engine_queueing_model.go`) is still a parallel data path that bypasses `runAnalyzersAndScore` and builds a single-entry slice by hand. Recommended approach: Option A (register QM under `SaturationAnalyzerName` so V2's slice-builder is the single upstream). Pre-existing QM oversights to fix at merge (none introduced by the optimizer PR): threshold post-step skipped; `SchedulerQueue` not threaded into QM's `AnalyzerInput`; `Role` never set on QM's `VariantCapacity` (disaggregation dispatch broken for QM-scaled P/D models); GPU limiter constraints not passed under `enableLimiter=true`. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F10.

- **Per-analyzer decision-enrichment hook (observability)** — today's `enrichDecisionsWithKvTokenData` is a sat_v2-specific post-optimizer step that runs only on V2; QM-scaled VAs and TA decisions don't get analogous enrichment for their own relevant computed metrics (KV tokens for sat_v2, ITL coefficients for TA, queue depth / arrival rate for QM). Generalize into a per-analyzer hook (or onto `NamedAnalyzerResult` itself) so any analyzer can publish its own observability fields without engine-side special casing. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction → F4.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| Dean (self) | `planning/PR1113-review.md` | DRAFT (design SETTLED) | PR #1113 fix design — settled on the 3-PR split. Re-validated 2026-05-29 against main `589646d7`. Pending Dean's final approval before reviewer discussion |
