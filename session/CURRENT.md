# Current Work

**Last updated:** 2026-06-05

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md has per-task sections — add or update sections that belong to your current task; never overwrite a sibling task's state. **Per the doc taxonomy, CURRENT.md holds operational state and short abstracts only — design and per-PR detail live in `planning/`.**

---

## Recent activity

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
| multi-analyzer-registration | #1225 | **PR #1225 OPEN** (ready-for-review, ev-shindin); 5 commits on `main`@`eb327cc2`; CI in progress | `6339e495` |
| multi-analyzer-threshold | #1228 | **PR #1228 OPEN** (ready-for-review, ev-shindin); 4 commits on `multi-analyzer-registration`@`66001d47`. Stacked on #1225 — diff includes both PRs' commits until #1225 merges and threshold rebases onto main | `b8b823b0` |
| multi-analyzer-optimizer | — | Local only (post-rebase); 7 commits on `multi-analyzer-threshold@b8b823b0`. **Ready for push + PR creation** — awaiting Dean force-with-lease confirmation. SchedulerQueue wiring from engine-queue-fix absorbed. | `3fe287fe` |
| engine-queue-fix      | —     | **Absorbed** into multi-analyzer-optimizer commit 7 (`3fe287fe`). Branch + worktree can be closed/removed. | `01ed7d8` |

---

## Blocked on

- **PR #1225** — opened 2026-06-01; awaiting CI + reviewer feedback. PR #1113 stays open until Dean closes it post-migration. See [`planning/multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md).
- **PR #1228** — opened 2026-06-02; awaiting CI + reviewer feedback. Stacked on #1225. See [`planning/multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md).
- **multi-analyzer-optimizer** — all 7 commits landed locally on `multi-analyzer-threshold@b8b823b0`. Cross-rebase complete; gates green; SchedulerQueue wiring absorbed from engine-queue-fix. **Awaiting Dean force-with-lease push to `origin/multi-analyzer-optimizer` and PR creation.** See [`planning/multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md).
- **engine-queue-fix** — absorbed (commit `01ed7d8d` folded into multi-analyzer-optimizer commit 7). Branch + worktree can be closed/removed.

## Next steps

- **Now:** monitor PR #1225 / #1228 CI; respond to ev-shindin reviews when they land.
- **Optimizer push + PR.** Force-with-lease push `multi-analyzer-optimizer` to origin, then open PR (target `multi-analyzer-threshold` while #1228 is open, or `main` if landing standalone — see optimizer plan § Next steps). After push, close `engine-queue-fix` branch + remove its worktree (its commit was absorbed into the optimizer stack).
- The `engine-multi-analyzer` worktree's run-1 wrap-up is complete; worktree can be removed at Dean's discretion.
- **Other:** rebase TA3 onto upstream/main, then discuss TA3 PR-4+PR-5 before submitting.
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
| Item 3 — Race-safe analyzer registry | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) | [`multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md) |
| Item 2 — Universal threshold post-step + aggregation helpers | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) | [`multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md) |
| Item 1 — Per-analyzer slice → optimizers (delete combine) | `multi-analyzer-optimizer` / not yet open | [`multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) (slim candidate at [`-draft`](../planning/multi-analyzer-optimizer-plan-draft.md)) |

The old `engine-multi-analyzer` branch and PR #1113 are **superseded** by the 3-PR split. PR #1113 stays open until Dean closes it post-coordination with ev-shindin.

---

## Deferred fixes (TA2 / PR-3 follow-ups)

10 specific fixes deferred from PR #1052 review for a grouped fixup PR after TA3 merges. See [`planning/PR1052-deferred-fixes.md`](../planning/PR1052-deferred-fixes.md).

---

## Issues to Open (post-merge)

- **Engine SchedulerQueue wiring** — ✅ implemented on `engine-queue-fix` (`01ed7d8`); PR deferred until #1113/#1225 merges. Fix threads `CollectSchedulerQueueMetrics` through `prepareModelData` → `collectV2ModelRequest` → `runAnalyzersAndScore` → `runV2AnalysisOnly` → `AnalyzerInput.SchedulerQueue`.

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

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| Dean (self) | `planning/PR1113-review.md` | DRAFT (design SETTLED) | PR #1113 fix design — settled on the 3-PR split. Re-validated 2026-05-29 against main `589646d7`. Pending Dean's final approval before reviewer discussion |
| Dean (self) | `session/handoffs/plan__threshold-coder-rules-gap.md` | OPEN | Plan-agent decision pending: whether/how to restate CONVENTIONS' "no `cd`/`-C` to a sibling worktree for git" rule operationally inside `planning/multi-analyzer-coder-rules.md`. 4 options listed |
