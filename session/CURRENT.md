# Current Work

**Last updated:** 2026-06-12

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-06-12 — PR #1266 opened** (`multi-analyzer-addendum`, tip `0eeb659c`). Addendum to #1246: disabled-analyzer veto bug fix (`effectiveEnabled` helper — `Enabled:false` was parsed but not checked at runtime, causing zero-SpareCapacity veto of scale-down), config-bridge + non-uniform Score tests, full rewrite of `docs/developer-guide/multi-analyzer-pipeline.md` (architecture diagram, data model, optimizer internals). Reviewer: ev-shindin. Plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md).
- **2026-06-10 — Optimizer #1246 MERGED** (`09e1c386` onto main, tip `ad1a8e1e`). ev-shindin approved 2026-06-09 with 2 noted items: (1) local `max` shadows Go builtin in `analyzer_helpers.go` `roleBottleneckReplicas`/`roleAggRemaining` — linter may flag (follow-up filed in Issues to Open); (2) `prcForVariant` O(V) scan in hot loop — non-blocking. Squash request (17→1) came with approval; merged as 17 commits. **Multi-analyzer mission complete** (#1225/#1228/#1246 all on main). SchedulerQueue wiring landed.
- **2026-06-11 — PR #1250 pushed (tip f5385168); 28 commits; awaiting re-review.** ev-shindin COMMENTED; two bugs found and fixed: Bug A (throughput metrics always-zero — key-mismatch in `replica_metrics.go` + missing `instance`/`llm_d_ai_variant` in 3 queries) and Bug B (3 comment items in `analyzer.go`). New test `TestCollectReplicaMetrics_ThroughputKeyMerge` added. Rebased onto `main@0e977b3b`; pushed force-with-lease. [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) filed (SC-gate + sanity extension). Follow-up: post comment to ev-shindin explaining key-mismatch discovery + Option A decision. Review: [`planning/PR1250-review.md`](../planning/PR1250-review.md).
- **2026-06-09 — TA3 PR #1250 opened.** Pushed `dbf3a981`; 24 commits, all gates verified. See [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md).

**Tail (compressed — recover via the ID/ref):**

- 2026-06-09 — #1245 (ScalingPolicy CRD) reviewed; comment posted ([issuecomment-4662740902](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1245#issuecomment-4662740902)); DRAFT review → [`planning/PR1245-review.md`](../planning/PR1245-review.md).
- 2026-06-11 — TA3 re-rebase impact verified: conflict surface = `cmd/main.go` only; TA3 queries already correct for post-#1260 world. → [`planning/PR1250-review.md`](../planning/PR1250-review.md) § Discussion.
- 2026-06-09 — #1246 rebased onto `main@badc48be` + lint-fix, pushed `ad1a8e1e`; all CI green; approved + merged 2026-06-10 (`09e1c386`). Phase 4 review FINAL: [`planning/multi-analyzer-optimizer-review.md`](../planning/multi-analyzer-optimizer-review.md).
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
| TA3                   | #1250 | **PR #1250 OPEN** (base `main`, assignee ev-shindin) 2026-06-09; 24 commits, all CI green. ev-shindin COMMENTED 2026-06-11. Two bugs to fix (key-mismatch always-zero + 3 comment items), then rebase + push. No #1260 dependency. SC-gate + sanity deferred → [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261). | `dbf3a981` |
| engine-multi-analyzer | #1113 | **Superseded** by the 3-PR split; Dean to close post-coordination with ev-shindin. Worktree retained. | `fc403f75` |
| multi-analyzer-registration | #1225 | **MERGED** 2026-06-07 (`f664a470` on main) | `5c73ea5f` |
| multi-analyzer-threshold | #1228 | **MERGED** 2026-06-08 (`d9e4ae1f` on main) | `d9e4ae1f` |
| (upstream) role-aware scale-down | #1237 | **MERGED** 2026-06-08 (`badc48be` on main) | `badc48be` |
| multi-analyzer-optimizer | #1246 | **MERGED** 2026-06-10 (`09e1c386` on main). ev-shindin approved; 2 follow-up items in Issues to Open. | `ad1a8e1e` |
| engine-queue-fix      | —     | **Absorbed** into multi-analyzer-optimizer commit 7 (`3fe287fe`). Branch + worktree can be closed/removed. | `01ed7d8` |
| multi-analyzer-addendum | #1266 | **PR #1266 OPEN** (base `main`, reviewer ev-shindin) 2026-06-12; 6 commits, all CI green. Addendum to #1246. | `0eeb659c` |

---

## Blocked on

- **PR #1250** (`TA3` → `main`) — pushed `f5385168` 2026-06-11; 28 commits above `main@0e977b3b`. Bug A + Bug B fixed. Awaiting ev-shindin re-review. Follow-up comment needed (Option A explanation). All CI pending.

## Next steps

- **TA3 (now):** Two bugs to fix before rebase — see [`planning/TA3.1-plan.md`](../planning/TA3.1-plan.md) § Complete #1250. Bug A: throughput queries missing `instance` in `by()` + 3 processing loops use bare pod name instead of `buildInstanceKey()` → GenerationTokenRate/KvUsageInstant/VLLMRequestRate always zero (fix: `throughput_analyzer.go` + `replica_metrics.go`). Bug B: three comment/doc items in `analyzer.go` (208/343/243). Then rebase onto current main, run gates, push. No #1260 dependency. After merge: discuss E2E Step 2f; triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`).
- **multi-analyzer-addendum (now):** Await ev-shindin review of [#1266](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1266).
- **Post-#1246-merge cleanup:** close `engine-queue-fix` branch+worktree; drop `backup/multi-analyzer-optimizer-pre-rebase@ae456aa0`; close PR #1113 + remove `engine-multi-analyzer` worktree; remove `multi-analyzer-optimizer` worktree at discretion.
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

PR-4 + PR-5 code-complete on TA3 (`5e316104`, on `multi-analyzer-optimizer@4bfac2fa`). All gates green per coder. Review **FINAL** ([`planning/TA-PR5-review.md`](../planning/TA-PR5-review.md)). E2E Steps 1a/1b/2a-2e PASSED on kind `kind-wva-gpu-cluster`; Step 2f pending discussion; 3 pre-existing smoke failures (`smoke_test.go:339, :542, :1724`) to triage. Rebase onto `main@badc48be` done; PR #1250 open. Review follow-ups tracked in [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md) (§3.1, §6.1).

**Plan docs:** [`planning/TA-Plan.md`](../planning/TA-Plan.md), [`planning/TA-PR4-plan.md`](../planning/TA-PR4-plan.md), [`planning/TA-PR5-plan.md`](../planning/TA-PR5-plan.md), [`planning/TA-PR5-review.md`](../planning/TA-PR5-review.md), [`planning/TA3.1-plan.md`](../planning/TA3.1-plan.md) (PR-B — STANDBY; D1/D2/T1/T2 in #1250), [`planning/TA-e2e-plan.md`](../planning/TA-e2e-plan.md), [`docs/developer-guide/throughput-analyzer.md`](docs/developer-guide/throughput-analyzer.md) (Type 4 reference).

**Next steps for TA3:** Fix Bug A (key-mismatch: `throughput_analyzer.go` + `replica_metrics.go`) + Bug B (comment items in `analyzer.go`). Rebase onto current main. No #1260 dependency. Full task in [`planning/TA3.1-plan.md`](../planning/TA3.1-plan.md) § Complete #1250. Then: discuss E2E Step 2f; triage the 3 pre-existing smoke failures.

---

## Multi-Analyzer mission

Three branches, one mission. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) for cross-cutting design (mission, architecture, alternatives considered, future direction) and [`planning/multi-analyzer-coder-rules.md`](../planning/multi-analyzer-coder-rules.md) for coder agent rules.

| Item | Branch / PR | Plan |
|---|---|---|
| Item 3 — Race-safe analyzer registry | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) **MERGED** 2026-06-07 | [`multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md) |
| Item 2 — Universal threshold post-step + aggregation helpers | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) **MERGED** | [`multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md) |
| Item 1 — Per-analyzer slice → optimizers (delete combine) | `multi-analyzer-optimizer` / [#1246](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1246) **MERGED** 2026-06-10 | [`multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) |

The old `engine-multi-analyzer` branch and PR #1113 are **superseded** by the 3-PR split. PR #1113 stays open until Dean closes it post-coordination with ev-shindin.

---

## Deferred fixes (TA2 / PR-3 follow-ups)

10 specific fixes deferred from PR #1052 review for a grouped fixup PR after TA3 merges. See [`planning/PR1052-deferred-fixes.md`](../planning/PR1052-deferred-fixes.md).

---

## Issues to Open (post-merge)

Multi-analyzer — full detail in [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction:

- Per-analyzer status-return state (`AnalyzerStatus`: SuppressSC/SuppressRC/Fail; restores TA EPP-queue + GPS gating; subsumes F9) → **F3** — **FILED as [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261)** (framed as analyzer interface extension: accept-for-SC/RC/all + sanity helper mechanism; motivated by TA3 #1250 review)
- Remove `llm_d_ai_variant` from all PromQL groupbys post-#1260 — **FILED as [#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263)** (move VA attribution fully to collector layer; unblocks InferencePool-selector scoping #1072)
- Distinguish unavailable metric from genuine zero in `ReplicaMetrics` (`*float64` nil semantics for 3 throughput fields + sanity update) — **FILED as [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264)** (prerequisite: #1250 Bug A fix; follow-up after #1250 merges)
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- Engine model-level RC/SC for disaggregated models (latent additive bug) → **F5**
- Replica-count accounting consistency (TA `len(variantMetrics)` vs sat_v2 `readyCount`) → **F8**
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10**
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- Engine SchedulerQueue wiring — ✅ landed with #1246 merge (2026-06-10, `09e1c386`).

Infra / misc (no design-doc home; file as separate issues):

- **Bob review 1.3** — ArrivalRate staleness check in `computeDemand` (observability PR).
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); observability PR after PR-5.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- **ndots fix standalone PR** — TA3 commit `0614d9d` (`test/e2e/fixtures/workload_builder.go`) needs its own PR before/with TA3 merge.
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| Dean (self) | `planning/PR1113-review.md` | DRAFT (design SETTLED) | PR #1113 fix design — settled on the 3-PR split. Re-validated 2026-05-29 against main `589646d7`. Pending Dean's final approval before reviewer discussion |
| planner | `planning/open-items-roadmap.md` | DRAFT (survey complete) | Cross-PR/cross-doc backlog catalog (~58 open + 10 recently-closed); Eisenhower×S/M/L rubric agreed. Next session: (1) fold in PR #1245 review residue (not in survey — review came after roadmap was drafted), (2) score by area starting with multi-analyzer, (3) refine dep graph from scoring outcomes. Plus uncommitted on plans branch: optimizer-review.md (P4 addendum), open-items-roadmap.md (new), multi-analyzer-design.md (F10/F11 from sibling planner) — commit when convenient. |
