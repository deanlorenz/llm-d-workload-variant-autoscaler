# Current Work

**Last updated:** 2026-06-09

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-06-09 — Optimizer #1246: rebased onto `main@badc48be` (#1237) + lint fixed; pushed.** New tip `ad1a8e1e` (17 commits = 16 rebased + 1 lint-fix on top of `badc48be`). Reuses #1237's `scaleDownVariantSet` as the shared shedding primitive (generalized with `maxRemovable`/`onRemove` callbacks); adds deterministic `sortVariantsForScaleDown` (Cost-desc → score-weighted PRC-asc → name-asc); old `findCheapestVariant`/`sortByCostDesc` deleted. All gates green (`make lint` 0, test 136/136, -race clean, DCO 17/17). CI on `ad1a8e1e`: `lint-and-test` ✅ (was the failing gate); `e2e-tests-smoke` IN_PROGRESS; other gates ✅/SKIPPED. PR body bullet fixed for current Phase-3 vocabulary ("paired" → "joint"). Phase 4 review FINAL in [`planning/multi-analyzer-optimizer-review.md`](../planning/multi-analyzer-optimizer-review.md). Awaiting ev-shindin review.
- **2026-06-09 — TA3 re-rebase impact verified.** Contract (`interfaces/analyzer.go`) + `aggregation` pkg byte-identical at TA3 base `4bfac2fa` → optimizer tip; #1237 touches none of interfaces/engine/throughput → no analyzer adaptation; conflict surface = `cmd/main.go` only; H1 (`RegisterAnalyzer` error-return) now lint-blocking, applied during the re-rebase. See [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md) § Re-rebase impact analysis.

**Tail (compressed — recover via the ID/ref):**

- 2026-06-08 — #1246 opened (base `main`, ev-shindin), tip `ee8bd815`; completes the 3-PR split.
- 2026-06-08 — #1228 threshold MERGED `d9e4ae1f`; #1237 role-aware scale-down MERGED `badc48be`; #1225 registration MERGED `f664a470` (06-07).
- 2026-06-08 — TA3 PR-5 review FINAL ([`TA-PR5-review.md`](../planning/TA-PR5-review.md)): D1/D2 docs, T1 renames, T2 specs; SC-gate→F3; H1 on rebase; don't-touch `anyEPP`/`anyGPSMismatch` + GPS fixtures.
- 2026-06-08 — optimizer Phase 1/2/3 + cleanup on-branch → `3fe287fe`/`4bfac2fa`/`680b1fb8`/`1648f3f6`/`ee8bd815`; detail in optimizer-plan §§ Phase 2/3 + commit stack.
- 2026-06-07 — #1237 reviewed (6 comments) pre-merge; TA-PR5 plan verified (engine-queue-fix absorbed `3fe287fe`; `SpareD`→`RoleSpare`) → TA-PR5-plan / optimizer-plan.
- 2026-06-04 — TA-PR5 plan rewritten for the 3-PR split; multi-analyzer doc taxonomy reorg → `planning/` (design doc + 3 per-PR plans).
- 2026-06-03 / 05-29 — optimizer P/D design settled (design §§ Architecture/D, A4); PR #1113 split into 3 PRs → [`PR1113-review.md`](../planning/PR1113-review.md).

---

## PR Status

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| TA1                   | #1051 | **MERGED** 2026-05-12; remove worktree ~2026-05-26                | `c405e8d` |
| TA2                   | #1052 | **MERGED** 2026-05-19; remove worktree ~2026-06-02                | `a8aac2b7` |
| TA3                   | —     | PR-5 code complete + reviewed FINAL; **cleared to rebase onto `main@badc48be` now (sibling of #1246)** — coder triggered (rebase + H1 + green gates incl `make lint`), then Dean opens PR (base main). See § TA3. | `5e316104` |
| engine-multi-analyzer | #1113 | **Superseded** by the 3-PR split; Dean to close post-coordination with ev-shindin. Worktree retained. | `fc403f75` |
| multi-analyzer-registration | #1225 | **MERGED** 2026-06-07 (`f664a470` on main) | `5c73ea5f` |
| multi-analyzer-threshold | #1228 | **MERGED** 2026-06-08 (`d9e4ae1f` on main) | `d9e4ae1f` |
| (upstream) role-aware scale-down | #1237 | **MERGED** 2026-06-08 (`badc48be` on main) | `badc48be` |
| multi-analyzer-optimizer | #1246 | **PR #1246 OPEN** (base `main`, ev-shindin). Rebased onto `main@badc48be` (#1237) + lint-fixed; force-with-lease pushed. CI: `lint-and-test` ✅ (the previously-failing gate); `e2e-tests-smoke` IN_PROGRESS; other gates ✅/SKIPPED. PR body fixed for current Phase-3 vocabulary. Awaiting reviewer. | `ad1a8e1e` |
| engine-queue-fix      | —     | **Absorbed** into multi-analyzer-optimizer commit 7 (`3fe287fe`). Branch + worktree can be closed/removed. | `01ed7d8` |

---

## Blocked on

- **PR #1246** — rebased onto `main@badc48be` (#1237) + lint-fixed; force-with-lease pushed (`ad1a8e1e`). CI green except `e2e-tests-smoke` IN_PROGRESS. Awaiting ev-shindin review.
- **TA3** — **cleared to rebase onto `main@badc48be` now** (sibling of #1246, not dependent — verified TA3 needs only the merged contract on main; 21 commits touch no optimizer/engine/interfaces files). Coder triggered: `git rebase --onto main 4bfac2fa TA3` + H1 + full gates incl `make lint`. Caveat: TA's signal is discarded on main until #1246 merges, so full e2e needs #1246 (comment-triggered, not the blocking gate).

## Next steps

- **Optimizer (now):** await `e2e-tests-smoke` complete + ev-shindin review on #1246; respond to comments.
- **TA3 (now):** coder rebases onto `main@badc48be` (sibling PR) + H1 + green gates incl `make lint`; hand back → planner verify → Dean opens PR (base main). Then review follow-ups (D1/D2/T1/T2); discuss E2E Step 2f; triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`).
- **N4 decision (open):** sort in `scaleDownRoleIterated` — harmless; leave as-is unless #1237-alignment preferred.
- **Post-#1246-open cleanup:** close `engine-queue-fix` branch+worktree; drop `backup/multi-analyzer-optimizer-pre-rebase@ae456aa0`; remove `engine-multi-analyzer` worktree at discretion.
- **Parallel track (NOT authorized):** WVA-vs-KEDA benchmark — see § Benchmark.

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

---

## TA3 (ThroughputAnalyzer) — PR-5 code complete; awaiting re-rebase + Dean review

PR-4 + PR-5 code-complete on TA3 (`5e316104`, on `multi-analyzer-optimizer@4bfac2fa`). All gates green per coder. Review **FINAL** ([`planning/TA-PR5-review.md`](../planning/TA-PR5-review.md)). E2E Steps 1a/1b/2a-2e PASSED on kind `kind-wva-gpu-cluster`; Step 2f pending discussion; 3 pre-existing smoke failures (`smoke_test.go:339, :542, :1724`) to triage. **Rebase onto `main@badc48be` cleared now** (sibling of #1246, not dependent) + H1 + review follow-ups tracked in [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md) (§ Re-rebase impact analysis, §3.1, §6.1).

**Plan docs:** [`planning/TA-Plan.md`](../planning/TA-Plan.md), [`planning/TA-PR4-plan.md`](../planning/TA-PR4-plan.md), [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md), [`planning/TA-PR5-review.md`](../planning/TA-PR5-review.md), [`planning/TA-e2e-plan.md`](../planning/TA-e2e-plan.md), [`docs/developer-guide/throughput-analyzer.md`](docs/developer-guide/throughput-analyzer.md) (Type 4 reference).

**Next steps for TA3:** rebase onto `main@badc48be` **now** (sibling PR, cleared — `git rebase --onto main 4bfac2fa TA3`) + apply H1 + green gates incl `make lint` → hand back → planner verify → Dean opens PR (base main). Then review follow-ups (D1+D2 docs, T1 test renames, T2 aggregation-helper specs); discuss E2E Step 2f; triage the 3 pre-existing smoke failures.

---

## Multi-Analyzer mission

Three branches, one mission. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) for cross-cutting design (mission, architecture, alternatives considered, future direction) and [`planning/multi-analyzer-coder-rules.md`](../planning/multi-analyzer-coder-rules.md) for coder agent rules.

| Item | Branch / PR | Plan |
|---|---|---|
| Item 3 — Race-safe analyzer registry | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) **MERGED** 2026-06-07 | [`multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md) |
| Item 2 — Universal threshold post-step + aggregation helpers | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) **MERGED** | [`multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md) |
| Item 1 — Per-analyzer slice → optimizers (delete combine) | `multi-analyzer-optimizer` / [#1246](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1246) **OPEN** | [`multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) |

The old `engine-multi-analyzer` branch and PR #1113 are **superseded** by the 3-PR split. PR #1113 stays open until Dean closes it post-coordination with ev-shindin.

---

## Deferred fixes (TA2 / PR-3 follow-ups)

10 specific fixes deferred from PR #1052 review for a grouped fixup PR after TA3 merges. See [`planning/PR1052-deferred-fixes.md`](../planning/PR1052-deferred-fixes.md).

---

## Issues to Open (post-merge)

Multi-analyzer — full detail in [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction:

- Per-analyzer status-return state (`AnalyzerStatus`: SuppressSC/SuppressRC/Fail; restores TA EPP-queue + GPS gating; subsumes F9) → **F3**
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- Engine model-level RC/SC for disaggregated models (latent additive bug) → **F5**
- Replica-count accounting consistency (TA `len(variantMetrics)` vs sat_v2 `readyCount`) → **F8**
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10**
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- `enabled:false` analyzer exempt from `needsScaleDown` → **A8**
- Engine SchedulerQueue wiring — ✅ absorbed into optimizer `3fe287fe`; lands when #1246 merges.

Infra / misc (no design-doc home; file as separate issues):

- **Multi-analyzer dev-guide polish** — fold design content (architecture, alternatives, future direction) + per-PR detail into `docs/developer-guide/multi-analyzer-pipeline.md`, replacing the stub and its plans-branch-fork link, once #1225/#1228/#1246 reach final shape. Doc-only commit per branch (or one after merges).
- **Bob review 1.3** — ArrivalRate staleness check in `computeDemand` (observability PR).
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); observability PR after PR-5.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- **ndots fix standalone PR** — TA3 commit `0614d9d` (`test/e2e/fixtures/workload_builder.go`) needs its own PR before/with TA3 merge.
- **Greedy fair-share priority test coverage** — #1246 B1 fix removed hardcoded `Score:1.0` from test helpers; only one T1.3 multi-model integration test covers the priority path. Add a multi-model fair-share test with **non-uniform `Score`** across analyzers. From the Phase 4 review (non-blocking); file post-#1246-merge.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| Dean (self) | `planning/PR1113-review.md` | DRAFT (design SETTLED) | PR #1113 fix design — settled on the 3-PR split. Re-validated 2026-05-29 against main `589646d7`. Pending Dean's final approval before reviewer discussion |
