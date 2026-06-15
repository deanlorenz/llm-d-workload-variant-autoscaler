# Current Work

**Last updated:** 2026-06-16

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-06-15 — #1275 (collector-va-attribution) CLOSED; #1263 CLOSED.** Both superseded by #1267 (`c55906a4`, merged): #1267 retained `llm_d_ai_variant` as the label fast-path and added owner-walk locator fallback (`locator.PodLocator`) — the label-drop premise of #1263 and the Attributor-seam approach of #1275 are both wrong given #1267's design (dropping the label kills shadow-pod attribution). `collector-va-attribution` branch to archive. The only non-superseded piece from #1275 is the `UnattributedReadyPods` K8s event — decision pending: fold into #1250 rebase or standalone issue. Full decisions: [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md), [`planning/PR1275-closure-capture.md`](../planning/PR1275-closure-capture.md).
- **2026-06-15 — #1266 MERGED** (`6d25b134` onto main). Addendum to #1246: `effectiveEnabled` bug fix (explicit `Enabled:false` now skips run + append), config-bridge + non-uniform Score tests, full pipeline dev guide rewrite + `runRegisteredAnalyzers` dead-code removal. Follow-up: `effectiveEnabled` opt-in fix (absent entry → false) — plan at [`planning/PR1266-fixup-effectiveEnabled.md`](../planning/PR1266-fixup-effectiveEnabled.md).
- **2026-06-10 — Optimizer #1246 MERGED** (`09e1c386` onto main, tip `ad1a8e1e`). ev-shindin approved 2026-06-09 with 2 noted items: (1) local `max` shadows Go builtin in `analyzer_helpers.go` `roleBottleneckReplicas`/`roleAggRemaining` — linter may flag (follow-up filed in Issues to Open); (2) `prcForVariant` O(V) scan in hot loop — non-blocking. Squash request (17→1) came with approval; merged as 17 commits. **Multi-analyzer mission complete** (#1225/#1228/#1246 all on main). SchedulerQueue wiring landed.
- **2026-06-16 — #1250 round-2 review fixes pushed** (`f11f5120`, 33 commits). Smoke `saturation_v2_test.go:280` root cause = throughput analyzer registered unconditionally + consumed in optimizer scale-down min-aggregation (post-#1246) → no-data `RoleSpare≤0` vetoes saturation scale-down. Fix: opt-in **registration gate** (`throughputAnalyzerEnabled` in `cmd/main.go`) — default config never registers TA → behaves as if absent. Plus OLS healthy-filter + ITL-sat guard + dead-code removal + nits + dev-guide. Internal review PASS, all gates green. Deferred runtime gate: [`planning/PR1266-fixup-effectiveEnabled.md`](../planning/PR1266-fixup-effectiveEnabled.md) (removes the stopgap). Earlier: rebased onto `main@04f95779` + Bug A/B/C (`b0284253`).
- **2026-06-11 — PR #1250 Bug A + Bug B fixed.** Bug A: throughput metrics always-zero (key-mismatch in `replica_metrics.go` + missing `instance`/`llm_d_ai_variant` in 3 queries). Bug B: 3 comment items in `analyzer.go`. Test `TestCollectReplicaMetrics_ThroughputKeyMerge` added. [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) filed.

**Tail (compressed — recover via the ID/ref):**

- 2026-06-12 — #1260 reviewed (review id `4479726743`; #1260 now **CLOSED → #1267**). Filed [#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263) (VA-attribution/query separation — see head) + [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264) (nil-vs-zero in `ReplicaMetrics`, **still a valid follow-up**). Multi-EPP P/D future note in [`planning/TA-demand.md`](../planning/TA-demand.md) § Scheduler queue contribution (entry-queue drives both roles, add decode queue to decode only; W_max recalc). EPP scheduler-queue scoping = **not an issue** (model-level correct; only upstream no-namespace gap #2309).
- 2026-06-09 — #1245 (ScalingPolicy CRD) reviewed; comment posted ([issuecomment-4662740902](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1245#issuecomment-4662740902)); DRAFT review → [`planning/PR1245-review.md`](../planning/PR1245-review.md).
- 2026-06-11 — TA3 rebase onto `526ce851`: conflict surface = `cmd/main.go` only. Rebase onto `04f95779` (new main): 3-file conflict (`replica_metrics.go`, `replica_metrics_test.go`, `cmd/main.go`) — see [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md).
- 2026-06-15 — Backlog scored (`open-items-roadmap.md`; multi-analyzer + TA + D52 areas done); PR-A renamed `multi-analyzer-addendum`; PR-B (`TA3.1`) standby (D1/D2/T1/T2 already in #1250). PROC-4 done (`backup/multi-analyzer-optimizer-pre-rebase` archived → `ae456aa0`).
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
| TA3                   | #1250 | **PR #1250 OPEN** (base `main`, assignee ev-shindin); 33 commits. Round-2 review fixes pushed `f11f5120` 2026-06-16 (throughput opt-in gate = smoke fix; OLS filter + ITL-sat guard; dead-code removal; nits; dev-guide). Internal review PASS; all gates green. **Awaiting CI + ev-shindin re-review.** SC-gate + sanity deferred → [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261). | `f11f5120` |
| engine-multi-analyzer | #1113 | **Superseded** by the 3-PR split; Dean to close post-coordination with ev-shindin. Worktree retained. | `fc403f75` |
| multi-analyzer-registration | #1225 | **MERGED** 2026-06-07 (`f664a470` on main) | `5c73ea5f` |
| multi-analyzer-threshold | #1228 | **MERGED** 2026-06-08 (`d9e4ae1f` on main) | `d9e4ae1f` |
| (upstream) role-aware scale-down | #1237 | **MERGED** 2026-06-08 (`badc48be` on main) | `badc48be` |
| multi-analyzer-optimizer | #1246 | **MERGED** 2026-06-10 (`09e1c386` on main). ev-shindin approved; 2 follow-up items in Issues to Open. | `ad1a8e1e` |
| engine-queue-fix      | —     | **Absorbed** into multi-analyzer-optimizer commit 7 (`3fe287fe`). Branch + worktree can be closed/removed. | `01ed7d8` |
| multi-analyzer-addendum | #1266 | **MERGED** 2026-06-15 (`6d25b134` on main). | `d861b09f` |
| collector-va-attribution | — | **CLOSED** — superseded by #1267 (`c55906a4`). #1263 closed. Archive branch via `git boidem collector-va-attribution`. See [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md). | `526ce851` |

---

## Blocked on

- **PR #1250** (`TA3` → `main`) — tip `f11f5120`; 33 commits; round-2 review fixes pushed 2026-06-16. Smoke root cause (throughput veto of saturation scale-down) fixed via opt-in registration gate. Awaiting CI + ev-shindin re-review.

## Next steps

- **TA3 (now):** Round-2 review fixes pushed (`f11f5120`); internal review PASS, all gates green. Await CI + ev-shindin re-review. After merge: discuss E2E Step 2f; triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`); ndots standalone PR.
- **Deferred (TA3 follow-up, post-gate):** harden throughput analyzer before it is ever enabled — review items 1/2 are folded now, but the SanityReport-capture/demand-gating nit stays with [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261). Registration gate is a stopgap to be **removed** when the `effectiveEnabled` opt-in consumption gate lands ([`planning/PR1266-fixup-effectiveEnabled.md`](../planning/PR1266-fixup-effectiveEnabled.md)).
- **#1266 fixup (now):** `effectiveEnabled` opt-in fix — absent entry should return `false`. Single commit, base `main`. Plan: [`planning/PR1266-fixup-effectiveEnabled.md`](../planning/PR1266-fixup-effectiveEnabled.md).
- **Post-#1246-merge cleanup:** archive `engine-queue-fix` branch (PROC-3; use `git boidem`); ~~drop `backup/multi-analyzer-optimizer-pre-rebase`~~ DONE (archived `ae456aa0` 2026-06-15); close PR #1113 + remove `engine-multi-analyzer` worktree (PROC-2/5, post-#1266 merge); remove `multi-analyzer-optimizer` worktree at discretion.
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

**Next steps for TA3:** Pushed `b0284253` (2026-06-16). Awaiting CI + ev-shindin re-review. After merge: E2E Step 2f, triage smoke failures, ndots PR.

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
- ~~Remove `llm_d_ai_variant` from all PromQL groupbys~~ — **FILED as [#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263); CLOSED** — superseded by #1267 (label retained as fast path + shadow-pod resolution; owner-walk handles Deployment/LWS). See [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md).
- Distinguish unavailable metric from genuine zero in `ReplicaMetrics` (`*float64` nil semantics for 3 throughput fields + sanity update) — **FILED as [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264)** (prerequisite: #1250 Bug A fix; follow-up after #1250 merges)
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- ~~Engine model-level RC/SC for disaggregated models~~ → **F5** CLOSED (resolved by #1246 `initRoleState`)
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
- **E2E throughput wiring test is a no-op under the opt-in gate** — `test/e2e/throughput_analyzer_test.go` ("ThroughputAnalyzer wiring health check") now passes via saturation alone because the controller starts on the default (saturation-only) config and registration is frozen post-start. Follow-up: restart the controller after writing the both-enabled config (true wiring check), or rename/rescope the test. Coder documented the gap in-code (`82611630`). **Not yet filed.**
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| Dean (self) | `planning/PR1113-review.md` | DRAFT (design SETTLED) | PR #1113 fix design — settled on the 3-PR split. Re-validated 2026-05-29 against main `589646d7`. Pending Dean's final approval before reviewer discussion |
| planner | `planning/open-items-roadmap.md` | **SCORED** (2026-06-15) | All areas scored (multi-analyzer, TA, D52/EV52). Committed `c71db32d`. See roadmap for Q1/Q2 priority list and dep graph. Next: file Q1+Q2 items as GitHub issues after #1266 merges. |
