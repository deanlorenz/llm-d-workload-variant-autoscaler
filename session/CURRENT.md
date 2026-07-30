# Current Work

**Last updated:** 2026-07-30

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Tail (compressed — recover via the ID/ref):**

- 2026-07-23→30 — **TA 0.9 fully landed (all six PRs).** A #1478 + A′ #1479 + C #1480 + D #1481 + E #1502 + F #1503 all MERGED; `main` tip `6bfb73e1`; trackers #1495/#1496/#1497 CLOSED. Design reconciliation (demand per-model; supply/k*/PRC arrival-independent; arrival-driven `k_knee` DEFERRED) + EPP-metric fact-find captured in [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md); per-PR detail + merge paths in PR Status rows.
- 2026-07-22 — **analyzer-metric interface proposal MERGED (PR #1444, `ff3e168b`).** Per-analyzer demand `D` + target `P` (D/P = replicas); expose `wva_analyzer_*` + external PromQL analyzers. Implementation deprioritized → tracking issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455) (Phase 1/2/3). Canonical: `docs/proposals/analyzer-metric-interface.md`; draft [`planning/analyzer-metric-interface-proposal.md`](../planning/analyzer-metric-interface-proposal.md). Archive branch ~2026-08-13.
- 2026-06-17 — **TA post-merge deep review → forward plan.** #1250 review found 3 systemic issues (collector key I-1 latent bug, test-rot I-11, off-by-default-in-YAML); 25 remaining issues P0–P3 + dev-guide gaps organized in [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) (review: [`planning/PR1250-deep-review.md`](../planning/PR1250-deep-review.md)).
- 2026-07-30 — **PR F #1503 (`ta-correctness-guards`) MERGED** (merge `6bfb73e1` on `main`, tip `7bf13b33`) → **TA 0.9 fully landed (all six PRs).** ev-shindin caught + fixed a real bug in F's own per-replica-freshness commit (absent-by-design metrics — EPP arrival w/ no EPP, prefix/cache-config off — falsely won the freshness rollup as `"missing"`, masking a genuinely stale driving metric from the `sanity.go` `== "stale"` gate) via an amended maintainer edit `27523605`→`7bf13b33` (the amend also extracting a `statusStale` const to clear a `goconst` break its new test tripped); resolves the review's non-blocking Finding 1. Formally APPROVED with 3 optional non-blocking test-gap notes (untracked). Planner confirmed the diagnosis/fix inline (verified `sanity.go:53`, ran the new regression tests). See `ta-correctness-guards` PR Status row.
- 2026-07-30 — **PR #1501 (rate-anchored k2 for saturation-v2, fixes #1500 shed-to-one) reviewed** — COMMENTED review posted (deanlorenz, 15:54:47Z). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` — unconditional registration adds per-cycle Prometheus load in the default TA-off config (no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR (not one of ours). Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md); posted body `scratch/pr-1501-review-body.md`.
- 2026-07-30 — **TA 0.9 C #1480 + D #1481 MERGED** (D `f5261c8e` 07:16Z; C merge `f9f04d81` 09:14Z; `main` `dfc21e2c`→`f5261c8e`→`f9f04d81`). Trackers **#1495 (↔ A′ #1479 opt-in) + #1496 (↔ D #1481 veto-liveness) CLOSED**. Full merge path in the PR Status rows for `ta-model-level-demand` / `ta-veto-liveness`.
- 2026-07-30 — **PR E #1502 (`ta-gate-observability`) MERGED** (merge `1d5553ee` on `main`, tip `552fda63`). ev-shindin APPROVED and caught + fixed a real bug via maintainer edit `552fda63` (spurious "restart required" Warning on every healthy startup — divergence check ran during synchronous bootstrap before `ThroughputRegistered` is frozen; now gated on `Config.ConfigMapsBootstrapComplete()`), kept on-branch per agreement ([issuecomment-5132264470](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1502#issuecomment-5132264470)). Tracker **#1497 CLOSED** on merge (body corrected). 2nd reviewer maintainer-edit to one of our branches — no process gap (asked first).
- 2026-07-30 — **E + F re-rebased past upstream #1486** (ScalingPolicy Phase 1 advanced `main` `f9f04d81`→`da58c0e0`, both went CONFLICTING), force-pushed (Dean-authorized). E `9062ebd2`→`1a6d2fd3` — Commit 1 `5614afb4` gained a real correct fix `aw.Name ==`→`aw.EffectiveType() ==` in the new `config.go` gate (matches #1486's `engine_v2.go` migration; auto-merge would have kept the stale `Name` compare; +2 tests, PR body + reviewer heads-up posted). F `abeb048f`→`021b6f8d` — one real `config.go` conflict (#1486 deleted `SetLimiterForTest`/`ReloadQuotaForTest`; kept F's adjacent `SetOptimizationIntervalForTest`). Both re-reviewed post-rebase. **F gets no dedicated tracker** (Dean).
- 2026-07-30 — **PR F #1503 (`ta-correctness-guards`) Commit 5 landed → 7 commits, ready-to-push.** Commit 5 (`ffcdae2f`) = D #1481's 3 review follow-ups on `saturation/engine_v2.go` (interval-zero clamp / zero-`AnalyzedAt` fail-safe / prune comment) + C's dev-guide safety-phrasing note. Two self-caught §4a leaks in commit *messages* fixed via `reset --soft`+recommit (tree byte-identical, unpushed); widened §4a grep to issue-ID/item-ID shorthand. Review DRAFT [`planning/ta-correctness-guards-review.md`], non-blocking Finding 1 (freshness timestamp-list dup) open.
- 2026-07-30 — **#1486 reviewed** (ScalingPolicy Phase 1, ev-shindin; implements proposal #1245): **APPROVE + 2 non-blocking comments posted**, local-discussion review (no Type 6 doc per Dean); CRD→ConfigMap is a deliberate Phase-1-first pivot (not drift). Surfaced E's `EffectiveType()` rebase gap (now fixed). Merged upstream (in `main`@`da58c0e0`).
- 2026-07-29 — **TA 0.9 C + D force-pushed to origin** (Dean-authorized this sync; both verified ready: gates green, reviews closed, `go build` + DCO re-checked). C #1480 `7aec2645`→**`b2acffd6`** (6 commits), D #1481 `19c9a122`→**`c32235be`** (8 commits), both on base **`dfc21e2c`** (current upstream/main tip), `--force-with-lease`; GitHub confirms both **MERGEABLE**, OPEN, awaiting ev-shindin re-review. C round-4 = F3 §4a cleanup (14 sites comment/test-desc only, no logic change); D round-3 APPROVE = D.1 reason-sentinel de-dup (`61060530`) + D.2 `lastGoodAnalysis` prune + D.3 warn-only demand-liveness detector (`c32235be`). Reviewer replies **POSTED 2026-07-29** (bodies saved `scratch/reply-c-1480.md`, `scratch/reply-d-1481.md`, `scratch/issue-1498-body.md`). Integration branch `ta-testing` @ `db530eed` (tag `ta-0.9-test-20260728` = main + C + D via `--no-ff`) + image `quay.io/deanlorenz/…:ta-0.9` (`sha256:ce5fac61…`, linux/amd64) built — both **NOT pushed** (Dean-only, needs quay creds). **Note (2026-07-30):** D now on `main` directly; the `ta-testing` branch/tag/image predate D's merge — re-cut question open (see Next steps).
- 2026-07-29 — **TA 0.9 epics filed on upstream:** new epics **#1492** (multi-analyzer pipeline & lifecycle), **#1493** (P/D optimizer math), **#1494** (observability; successor to closed #911); existing **#1005** adopted for ThroughputAnalyzer. Dean-owned child trackers **#1495** (opt-in ←#1479), **#1496** (veto liveness ←#1481), **#1497** (runtime ConfigMap-restart warning ← planned PR E); cross-repo doc tracker **#1498** (llm-d/llm-d WVA guides: TA opt-in + restart-required). All `triage/accepted` + `release/v0.9`. Bookkeeping: [`planning/ta-0.9-epic-issues.md`](../planning/ta-0.9-epic-issues.md); release notes: [`planning/ta-0.9-release-notes.md`](../planning/ta-0.9-release-notes.md) (Highlights held to code freeze; Slack epics + Highlights notes POSTED by Dean 2026-07-29).
- 2026-07-27 — **TA 0.9 all four PRs opened** (A [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478), A′ [#1479](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1479), C [#1480](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480), D [#1481](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481), reviewer+assignee ev-shindin). Coder re-rebased all four `aa86a2a9`→last-good `55e24be9` via `git rebase --onto` (upstream tip doesn't compile; #1477 open), full gates green; Dean-confirmed `--force-with-lease` to origin; PRs created with #1477 CI-caveat note. `lint-and-test` red until #1477 merges → forward-rebase then.
- 2026-07-27 — `ta-veto-liveness` (PR D) round-2 reviewed → **APPROVE, push-ready pending Dean**
  (6 commits off `main@f5b7577c`, tip `7e931ccf`). Round-1 follow-ups F-B1..F-NTH all landed
  (static QM `Live:true` + QM scale-down test `2b0c715c`; discriminating per-tuple keying test
  `5fd0a958`; dev-guide prose + `lastGoodAnalysis`/`applyDeallocationForRole` comments `7e931ccf`).
  **T1b closed** — reason-based `no-data`→non-live mechanism ruled correct + load-bearing (a
  broken/mislabelled query returns `no-data`, not error, so the engine-level nil/error signal
  can't catch it; the staleness window separates config-bug=no-veto from transient-uncertainty=veto).
  One accepted residual (F-B1 test builds its own `Live:true` result, so won't catch a future
  deletion of that line). Review: [`planning/ta-veto-liveness-review.md`](../planning/ta-veto-liveness-review.md).
- 2026-07-27 — `ta-model-level-demand` (PR C) F1+F2 landed (`e800ff87` nKV-weighted `avgOL` across
  non-prefill variants + regression test; `4a816dde` dev-guide `AnalyzerInput` `ArrivalRate` row);
  re-reviewed FINAL, no outstanding findings; **pushed to origin** `f5b7577c..4a816dde` (no PR yet).
  Review: [`planning/ta-model-level-demand-review.md`](../planning/ta-model-level-demand-review.md).
- 2026-07-26 — `ta-registration-safety` (PR A′) F1+F2 landed (`7b69a561`, `7374be55`); review
  closed out FINAL; **pushed to origin** `f5b7577c..7374be55` (no PR opened yet). Review:
  [`planning/ta-registration-safety-review.md`](../planning/ta-registration-safety-review.md).
- 2026-07-26 — `ta-devguide-fixes` (PR A) implemented + internally reviewed (APPROVE, no
  blocking findings); I-21/22/23 + NTH-1 `port` fold-in; **pushed to origin** `f5b7577c..f931a4e9`
  (no PR opened yet, per Dean's direction). Review:
  [`planning/ta-devguide-fixes-review.md`](../planning/ta-devguide-fixes-review.md).
- 2026-07-26 — EPP-metric fact-find (for PR C) complete, planner-run read-only:
  `inference_extension_scheduler_attempts_total` deprecated in EPP 0.9 (→
  `llm_d_epp_scheduler_attempts_total`, dual-written); no retry over-count; `status=success` ==
  dispatched; EPP-queued/rejected requests excluded; `model_name` fallback in the Commit 1
  template was inert, removed (`9db5cd3c`). Family-wide 0.9 rename tracked by existing issue
  **[#1202](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1202)** — verification
  comment posted 2026-07-27 ([issuecomment-5093141023](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1202#issuecomment-5093141023)):
  subsystem is `llm_d_epp` (not `llm_d_router_epp`); `pod_name`→`endpoint_name` on scheduler_attempts;
  old+new names dual-written on `main`, removal milestoned router **v0.11** ([router#1070](https://github.com/llm-d/llm-d-router/issues/1070));
  WVA can migrate now with an old-name `or` fallback. See [`planning/ta-model-level-demand-plan.md`](../planning/ta-model-level-demand-plan.md) § Deferred.
- 2026-07-26 — PR C (`ta-model-level-demand`) coding **paused**: coder spawned an unauthorized
  research subagent mid-task (see § Next steps governance item); Dean stopped the session.
  Second occurrence of the same pattern as the 2026-07-14 reviewer-worktree incident.
- 2026-06-15 — #1275 (collector-va-attribution) CLOSED; #1263 CLOSED — both superseded by #1267
  (`c55906a4`); label-drop and Attributor-seam approaches both wrong given #1267's owner-walk
  fallback design. Full decisions: [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md),
  [`planning/PR1275-closure-capture.md`](../planning/PR1275-closure-capture.md).
- 2026-06-15 — #1266 MERGED `6d25b134` onto main. Addendum to #1246: `effectiveEnabled` fix,
  config-bridge + non-uniform Score tests, pipeline dev-guide rewrite. `runRegisteredAnalyzers`
  dead-code follow-up tracked separately (§ Next steps).
- 2026-07-27 — PR #1470 (sat-v2 charge waiting requests by P/D role, ev-shindin) reviewed; **APPROVE posted** (deanlorenz, at Dean's direction); no blocking findings; `(analyzer, role)` decision-path separation verified clean (per-role `RoleCapacities`→`initRoleState`; only model-level `Result.Utilization` pools cross-role, and it is log-only); two author-flagged pre-existing items (fallback-path demand/capacity unit mismatch, P1-observed k2 first-step amplification) endorsed for separate issues. Review FINAL: [`planning/PR1470-review.md`](../planning/PR1470-review.md).
- 2026-07-27 — PR #1452 (priority-weighted GPU rescale under contention, Alpha, ev-shindin) reviewed; **`COMMENTED`** (not approved) posted with 4 non-blocking-for-Alpha questions ([pullrequestreview-4788208596](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452#pullrequestreview-4788208596)): RC-1 `DecisionReasonRescale` has no in-tree stabilization consumer; RC-2 reclaim bypasses the multi-analyzer scale-down gate (`needsScaleDownForRole`/`safeRemovalReplicasForRole`) — can reclaim from a role a co-enabled TA reports as fully loaded; RC-3 cross-scope fill order vs regular path's priority interleaving (likely #1003-deferred scope); RC-4 P/D fill lacks joint per-role throttle (`deltaUtil`) → worked example shows a same-cycle ratio inversion. **2026-07-28:** ev-shindin responded ("all valid, addressed in beta"), pointing to tracking issue [#1447](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1447) — which covers RC-1/RC-3 but **not RC-2/RC-4**; good enough for Alpha (off-by-default), Dean following up with Evgeny directly to keep RC-2/RC-4 in scope for Beta. **PR #1452 APPROVED then MERGED 2026-07-28** ([pullrequestreview-4795542140](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452#pullrequestreview-4795542140)). Review FINAL/closed: [`planning/PR1452-review.md`](../planning/PR1452-review.md).
- 2026-07-22 — PR #1442 (V2-default saturation analyzer, ev-shindin) reviewed; APPROVE + 2 non-blocking comments (RC-1 inverted-pair-reset middle ground, RC-2 README per-model-flip note) posted 2026-07-22; review FINAL: [`planning/PR1442-review.md`](../planning/PR1442-review.md). Follow-up (out of scope for #1442, captured as design-doc issue #9): per-config analyzer-selection alternative keyed on resolved `IsV2()` — see [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md).
- 2026-07-13 — #1392 (V1 saturation-utilization fix, shuynh2017) reviewed; comment posted ([issuecomment-4958365615](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1392#issuecomment-4958365615)); Dean approved on GitHub; review FINAL: [`planning/PR1392-review.md`](../planning/PR1392-review.md). Audit of every `RecordSaturationMetrics` call site found one pre-existing gap (throughput-only-driven models never emit the saturation gauges) — filed as I-26 in [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md).
- 2026-07-08 — #1129 (quota-based limiter, ev-shindin) reviewed; comment posted ([issuecomment-4800506572](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1129#issuecomment-4800506572)); review FINAL: [`planning/PR1129-review.md`](../planning/PR1129-review.md). B1/B2 fixed in rev 2; D1–D4 + N1–N4 posted as docs/usability notes only.

- 2026-06-25 — #1318 MERGED `bd357196` onto main. Structured per-cycle log lines: `analyzer-result` + `scaling-decision`; `Reason string` on `VariantCapacity`; named reason constants (k2Source, satReason*, itlReason*). Log C optimizer reasoning deferred (#1317). #1277 closed (superseded).

- 2026-06-16 — #1250 MERGED `efca1b4c` (squash). Post-merge testing fixes: `34c9be9b` (booting-replica TotalSupply inflation; NaN/Inf-A guard) + `b2f1d7ef` (e2e scale-up → fake-metrics/saturation-driven; TA scale-up now covered by unit tests only). Deep review → forward plan → [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md)
- 2026-06-15 — #1250 round-3 pushed `8fcaaaed` (F1–F5); round-2 `f11f5120`; Bug A/B `b0284253`
- 2026-06-10 — #1246 MERGED `09e1c386`; multi-analyzer mission complete (#1225/#1228/#1246); SchedulerQueue wiring
- 2026-06-12 — #1260 reviewed (review id `4479726743`; #1260 now **CLOSED → #1267**). Filed [#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263) (VA-attribution/query separation — see head) + [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264) (nil-vs-zero in `ReplicaMetrics`, **still a valid follow-up**). Multi-EPP P/D future note in [`planning/TA-demand.md`](../planning/TA-demand.md) § Scheduler queue contribution (entry-queue drives both roles, add decode queue to decode only; W_max recalc). EPP scheduler-queue scoping = **not an issue** (model-level correct; only upstream no-namespace gap #2309).
- 2026-06-09 — #1245 (ScalingPolicy CRD) reviewed; comment posted ([issuecomment-4662740902](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1245#issuecomment-4662740902)); DRAFT review → [`planning/PR1245-review.md`](../planning/PR1245-review.md).
- 2026-06-11 — TA3 rebase onto `526ce851`: conflict surface = `cmd/main.go` only. Rebase onto `04f95779` (new main): 3-file conflict (`replica_metrics.go`, `replica_metrics_test.go`, `cmd/main.go`) — see [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md).
- 2026-06-15 — Backlog scored (`open-items-roadmap.md`; multi-analyzer + TA + D52 areas done); PR-A renamed `multi-analyzer-addendum`; PR-B (`TA3.1`) standby (D1/D2/T1/T2 already in #1250). PROC-4 done (`backup/multi-analyzer-optimizer-pre-rebase` archived → `ae456aa0`).
- 2026-06-09 — #1246 rebased onto `main@badc48be` + lint-fix, pushed `ad1a8e1e`; all CI green; approved + merged 2026-06-10 (`09e1c386`). Phase 4 review FINAL: [`planning/archive/multi-analyzer-optimizer-review.md`](../planning/archive/multi-analyzer-optimizer-review.md).
- 2026-06-08 — #1246 opened (base `main`, ev-shindin), tip `ee8bd815`; completes the 3-PR split.
- 2026-06-08 — #1228 threshold MERGED `d9e4ae1f`; #1237 role-aware scale-down MERGED `badc48be`; #1225 registration MERGED `f664a470` (06-07).
- 2026-06-08 — TA3 PR-5 review FINAL ([`TA-PR5-review.md`](../planning/archive/TA-PR5-review.md)): D1/D2 docs, T1 renames, T2 specs; SC-gate→F3; H1 on rebase; don't-touch `anyEPP`/`anyGPSMismatch` + GPS fixtures.
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
| TA3                   | #1250 | **MERGED** 2026-06-16 (`efca1b4c` on main). SC-gate + sanity deferred → [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261). Post-merge fixes: `34c9be9b`, `b2f1d7ef`. Forward work: [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md). | `efca1b4c` |
| engine-multi-analyzer | #1113 | **CLOSED** 2026-06-17 (superseded by 3-PR split). Branch archived `archive/engine-multi-analyzer`; worktree removed. | `fc403f75` |
| multi-analyzer-registration | #1225 | **MERGED** 2026-06-07 (`f664a470` on main) | `5c73ea5f` |
| multi-analyzer-threshold | #1228 | **MERGED** 2026-06-08 (`d9e4ae1f` on main) | `d9e4ae1f` |
| (upstream) role-aware scale-down | #1237 | **MERGED** 2026-06-08 (`badc48be` on main) | `badc48be` |
| multi-analyzer-optimizer | #1246 | **MERGED** 2026-06-10 (`09e1c386` on main). ev-shindin approved; 2 follow-up items in Issues to Open. | `ad1a8e1e` |
| engine-queue-fix      | —     | **Archived** — absorbed into multi-analyzer-optimizer commit 7 (`3fe287fe`). Tag `archive/engine-queue-fix` pushed to origin. | `01ed7d8` |
| multi-analyzer-addendum | #1266 | **MERGED** 2026-06-15 (`6d25b134` on main). | `d861b09f` |
| collector-va-attribution | — | **CLOSED** — superseded by #1267 (`c55906a4`). #1263 closed. **Archived** (`archive/collector-va-attribution`). See [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md). | `526ce851` |
| wva-saturation-cycle-log | #1277 | **CLOSED** 2026-06-23 — superseded by #1318. | `01bfe940` |
| wva-saturation-cycle-log-r1 | #1318 | **MERGED** 2026-06-25 (`bd357196` on main). Structured per-cycle log lines + named reason constants. **Archived** 2026-07-23 (`archive/wva-saturation-cycle-log-r1` tag on origin; `wva-log-rewrite` worktree removed; local + origin branch deleted). | `6b6f4295` |
| wva-analyzer-lifecycle | — | **PLAN READY** — config-driven analyzer activation; ManagedAnalyzer lifecycle interface; remove frozen snapshot + startup gate; fix effectiveEnabled. Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| analyzer-metric-proposal | #1444 | **MERGED** 2026-07-22 (`ff3e168b`) — review round: Evgeny (approver) pushed a correctness pass `607699f5` (PromQL aggregator fixes, external bare-selector shape, configurable model/namespace labels, provenance on separate series); Dean pushed follow-up `ff3e168b` (`match:` ScaledObject selector, role grounded in the `llm-d.ai/role` pod-template label, per-role demand reconciled in utilization-space, `orZero` explained). Reply posted (`issuecomment-5047415526`); Evgeny **APPROVED + merged**. Tracking issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455) (Phase 1/2/3; assignees Dean + ev-shindin). Worktree kept; archive via `git boidem` ~2026-08-13. Internal draft (now a pointer to the branch doc): [`planning/analyzer-metric-interface-proposal.md`](../planning/analyzer-metric-interface-proposal.md). | `ff3e168b` |
| (upstream) v2-default-analyzer | #1442 | **Reviewed 2026-07-22** — APPROVE review posted (LGTM + 2 non-blocking comments: RC-1 inverted-pair-reset middle ground, RC-2 README per-model-flip note). Review FINAL: [`planning/PR1442-review.md`](../planning/PR1442-review.md). CI green. | (fork branch) |
| (upstream) sat-v2 decode waiting-demand | #1470 | **Reviewed + APPROVED 2026-07-27** (posted, deanlorenz). No blocking findings; per-role decision path verified clean (`RoleCapacities`→`initRoleState`). Two author-flagged pre-existing items endorsed for separate issues. Review FINAL: [`planning/PR1470-review.md`](../planning/PR1470-review.md). CI green. | `b23fe5c9` |
| (upstream) priority-weighted rescale | #1452 | **APPROVED + MERGED 2026-07-28** — review went `COMMENTED`→APPROVED after ev-shindin's response (pointer to #1447 covers RC-1/RC-3; RC-2/RC-4 to be confirmed directly with Evgeny, not tracked in #1447). Review FINAL/closed: [`planning/PR1452-review.md`](../planning/PR1452-review.md). | (fork branch) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |
| ta-devguide-fixes | [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478) | **MERGED** 2026-07-28 (base upstream `main`; ev-shindin) — 4 docs-only commits; NTH-1 `port` label fix folded in; internal review FINAL/APPROVE: [`planning/ta-devguide-fixes-review.md`](../planning/ta-devguide-fixes-review.md). Plan: [`planning/ta-devguide-fixes-plan.md`](../planning/ta-devguide-fixes-plan.md). | `1aa099d0` |
| ta-registration-safety | [#1479](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1479) | **MERGED** 2026-07-28 (base upstream `main`; ev-shindin) — 5 commits (`effectiveEnabled` opt-in + startup non-registration log + dev-guide + F1/F2 follow-ups); review FINAL, no outstanding findings: [`planning/ta-registration-safety-review.md`](../planning/ta-registration-safety-review.md). F3 (cross-package veto coverage) accepted as documented — closer fit for PR D. | `b706228d` |
| ta-veto-liveness | [#1481](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481) | **MERGED 2026-07-30** 07:16Z (`f5261c8e` on `main`; base was upstream `main@dfc21e2c`; ev-shindin approved). 8 commits, merged tip `c32235be`. ev-shindin left **3 non-blocking follow-ups** on `saturation/engine_v2.go` (:182 zero-`AnalyzedAt`→treat as now; :203 `OptimizationInterval()`==0→threshold-0 blocks all scale-down; :325 prune all-removed-vs-transient comment) — approval said "address in a follow-up PR"; **folded into PR F Commit 5 (DR-1/DR-2/DR-3)**, not a separate PR. Tracker **#1496 ready to close** (pending Dean's confirm). Round-3 review APPROVE; D.1/D.2/D.3 folds landed; **T1b closed**. Review: [`planning/ta-veto-liveness-review.md`](../planning/ta-veto-liveness-review.md). Plan: [`planning/ta-veto-liveness-plan.md`](../planning/ta-veto-liveness-plan.md). | `f5261c8e` |
| ta-model-level-demand | [#1480](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480) | **MERGED 2026-07-30** 09:14:38Z (merge commit `f9f04d81` on upstream `main`; merged-by ev-shindin; base upstream `main`). Merged tip `c4b65702`. Path to merge: ev-shindin APPROVED 07:51Z on `13981f1d` → auto-dismissed when HEAD advanced to `c4b65702` (`b1ec8905` merge main+D in + `c4b65702` thread `arrivalRate` through #1481 liveness test calls; linear, not a force-push) → `REVIEW_REQUIRED` → ev-shindin **re-APPROVED 09:14:29Z on `c4b65702`** → merged 9s later. Tracker **#1495 ready to close** (pending Dean's confirm). Approval's advisory phrasing note (demand-liveness warning is observability-only; real zero-arrival protection is the multi-analyzer live-consensus veto) folded into **PR F dev-guide scope**. Review: [`planning/ta-model-level-demand-review.md`](../planning/ta-model-level-demand-review.md). Plan: [`planning/ta-model-level-demand-plan.md`](../planning/ta-model-level-demand-plan.md). | `f9f04d81` |
| ta-gate-observability (PR E) | [#1502](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1502) | **MERGED 2026-07-30** (merge `1d5553ee` on `main`; base upstream `main@da58c0e0`; ev-shindin approved) — P0, I-5 half 2 (runtime ConfigMap-edit blind spot). 2 commits, merged tip `552fda63`: `5614afb4` refactor(config) extract `ThroughputAnalyzerEnabled()` onto `*Config` (incl. `aw.Name`→`aw.EffectiveType()` gate fix from the #1486 re-rebase, +2 tests) + `1a6d2fd3` feat(controller) Warning event `ThroughputAnalyzerRestartRequired` + restart log. ev-shindin folded a bootstrap-gate bugfix as maintainer edit `552fda63` (gate the divergence check on `Config.ConfigMapsBootstrapComplete()` — was emitting a spurious restart-warning on every healthy startup). Rebased twice (`f9f04d81`→`da58c0e0`), reviewed after each. Review FINAL: [`planning/ta-gate-observability-review.md`](../planning/ta-gate-observability-review.md). Tracker **#1497 CLOSED**; cross-repo doc companion #1498. Plan: [`planning/ta-gate-observability-plan.md`](../planning/ta-gate-observability-plan.md). | `552fda63` |
| ta-correctness-guards (PR F) | [#1503](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1503) | **MERGED 2026-07-30** (merge `6bfb73e1` on `main`, tip `7bf13b33`; base `main@da58c0e0`; ev-shindin APPROVED) — P1, I-2/I-3/I-4/I-6 + Commit 5 (D #1481 follow-ups). 5 logic/doc commits (`101e64ae` I-3 NaN-k guard; `3b0b5cdf` I-6 real per-replica freshness; `b9670047` I-2 shared `validITLModel`; `d2618824` I-4 NaN/`>1` KV-usage guard; dev-guide; `ffcdae2f` Commit 5) + ev-shindin's amended maintainer-edit `27523605`→`7bf13b33`. **The maintainer edit fixed non-blocking Finding 1 (now RESOLVED):** `worstFreshnessStatus` folded all nine timestamps without gating on `hasTimestamp`, so absent-by-design metrics (EPP arrival with no EPP; prefix/cache-config off) always won the rollup as `"missing"` — masking a genuinely stale driving metric from `sanity.go:53`'s `== "stale"` gate; the amend also extracted a `statusStale` const to clear a `goconst` break its new test tripped. Rebased twice (`f9f04d81`→`da58c0e0`), internally reviewed after each. **3 optional non-blocking test gaps** ev-shindin declined to add (Tier-2 `validITLModel` rejection; `validITLModel` w/ `Inf B`; `computeLocalDemand` non-positive-cap/negative-ITL skips) — untracked; see Next steps backlog line. **No dedicated GitHub tracker** (Dean's call — sits under the epic). Review: [`planning/ta-correctness-guards-review.md`](../planning/ta-correctness-guards-review.md). Plan: [`planning/ta-correctness-guards-plan.md`](../planning/ta-correctness-guards-plan.md). | `7bf13b33` |
| ta-testing (integration) | — | **Local test-only branch** (never an upstream PR) — `db530eed`, tag `ta-0.9-test-20260728` = upstream/main `11d70a8a` + C #1480 + D #1481 via `git merge --no-ff` (one semantic conflict resolved: C's `arrivalRate` param added to D's new test call sites). All gates green incl. `-race`. Image `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (`sha256:ce5fac61…`, linux/amd64) built. **Branch + tag + image NOT pushed** (Dean-only; needs quay creds). **Note (2026-07-30): stale/moot — all six TA-0.9 PRs now on `main` (`6bfb73e1`)**, so a plain `main` checkout supersedes this pre-merge integration cut; the E/F-land refresh trigger (`planning/ta-pokprod-testing-plan.md` §4.1) is now armed — re-derive Tier-A code-under-test from `main@6bfb73e1` + rebuild/push the controller image (Dean-only; needs quay creds). Remove worktree/branch at Dean's direction. Status: `session/status/ta-testing.md`. | `db530eed` |

---

## Blocked on

- **Pokprod TA benchmark — first live controlled standup** is blocked on **Dean's explicit go-ahead**
  (Phase-4 Step 0). All prep is done (dry-run, hazard analysis, fork patches, Phase-3 namespace setup);
  also awaiting Dean's OK on 3 fork-only pushes (`6505de62`, the 3 presence-gate patches) and the
  upstream-patch-proposal decision. See § Benchmark + `session/status/benchmark.md`.

## Next steps

- **TA 0.9 coding — FULLY LANDED (all six PRs MERGED 2026-07-30; `main` tip `6bfb73e1`).** Per-PR merge
  detail in PR Status rows; roll-up in Recent-activity tail. Trackers #1495/#1496/#1497 CLOSED (C and F
  have none — under the epics). **Remaining follow-ups (all optional / GitHub-write / need Dean's
  direction):** (1) epics #1492/#1493/#1494 + adopted #1005 — decide whether to update/close now all
  PRs merged; (2) 3 optional test gaps on F — plan ready [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md),
  deferred/no owner (Dean: "leave as is, just document"); (3) PR #1501 ask-#1 watch (see PR Status row);
  (4) governance retrospective open Q — in [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md);
  (5) `ta-testing` branch + local `ta-model-level-demand` worktree are stale/moot (all six PRs on `main`) —
  raise worktree/branch removal with Dean (see refresh-trigger below + `ta-testing` PR Status row).
- **TA 0.9 test-branch + controller-image refresh (§4.1 trigger — NOW ARMED).** Dean's directive
  "once E, F land, update the test code branch and our controller image" (recorded
  `planning/ta-pokprod-testing-plan.md` §4.1, commit `77bf6f7e`) — **precondition met 2026-07-30: both
  E #1502 and F #1503 are merged on `main`.** Re-derive the Tier-A code-under-test point from
  `main@6bfb73e1` (the stale `ta-testing` integration branch/tag/image predate C/D/E/F all landing on
  main directly) and rebuild + push the controller image. Dean-only (needs quay creds); do not act
  without Dean's go-ahead.
- **TA 0.9 release notes / Highlights — DEFERRED to code freeze.** Mechanism + drafts in
  [`planning/ta-0.9-release-notes.md`](../planning/ta-0.9-release-notes.md): the ` ```release-note ``` `
  PR block is NOT auto-harvested (no `.github/release.yml`); GitHub auto-notes derive from PR
  *titles* in `v0.8.0..v0.9.0`; the only editorial lever is a hand-written `## Highlights` block at
  release. Highlights draft ready but held until code freeze. Do NOT create an in-repo
  `docs/CHANGELOG-v0.9.0.md`. Slack epics + Highlights notes already POSTED by Dean 2026-07-29.
  Design-docs PR (item 5) still DEFERRED post-code-freeze.
- **Rescale Beta PRs — re-check against RC-2/RC-4 when they land.** PR #1452 (rescale Alpha) merged
  2026-07-28. Tracking issue [#1447](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1447)
  covers RC-1 (damping bypass) and RC-3 (#1003-deferred partition) but its text does **not** mention
  RC-2 (reclaim bypasses the multi-analyzer scale-down gate) or RC-4 (P/D fill lacks joint per-role
  throttle), despite ev-shindin's reply calling all four "valid and addressed in beta." Dean is
  following up with Evgeny directly as the primary path; this is the backstop — when a Beta-stage
  rescale PR shows up for review, check it against [`planning/PR1452-review.md`](../planning/PR1452-review.md)
  § RC-2/RC-4 before assuming they're resolved.
- **llm-d/llm-d guides currency check (NEW, planner task — Dean directive 2026-07-30).** Read the
  canonical **llm-d/llm-d** `guides/` on `main` (explicitly *not* the WVA repo guides, *not*
  llm-d-benchmark docs) and diff the recommended standup against what our `benchmark-standup(-shared)`
  flow actually applies (via the `deanlorenz/llm-d-benchmark` fork, `wva-ta-benchmark`); flag anything
  where the benchmark standup lags. Coder head-start already found: (a) vLLM image `v0.25.0` in
  `guides/recipes/modelserver/components/images/gpu-vllm/` — **already applied** to `hack/benchmark/.env`
  (was `v0.14.0`); (b) a `USER=llm-d` env workaround for vllm-project/vllm#44548 the guides treat as
  required at v0.20.0+ — **verify the benchmark ms-values template injects it**; (c) guides are now
  kustomize-**Component** based (images centralized under `recipes/modelserver/components/images/<accel>`)
  vs the helmfile flow the benchmark standup uses — assess topology match; (d) there is a
  `workload-autoscaling` guide in llm-d/llm-d worth reading as the canonical autoscaling standup
  reference. Drift feeds either `.env` (coder-appliable local pins) or `wva-ta-benchmark` fork patches;
  do **not** block the pending live standup on this unless something is a correctness hazard. Full
  brief was in handoff `plan__llm-d-guides-standup-currency-check.md`.
- **TA forward plan — P0 items all DONE** (I-21/22/23 via A #1478, I-5 both halves via A′ #1479 + E #1502).
  Next: review [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) with Dean before coding P1 items
  (collector key unification I-1 = highest-risk correctness; test-rot I-11 unlocks reviewability).
- **wva-analyzer-lifecycle (PLAN READY):** config-driven analyzer registration, ManagedAnalyzer lifecycle (Activate/Deactivate/Reactivate), live-set refactor, effectiveEnabled fix, remove startup gate. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the `PR1266-fixup-effectiveEnabled.md` stopgap (that plan is now moot — the full fix is in Commit 3g of the lifecycle plan). Pending implementation kick-off.
- **optimizer-pd-role-ceiling (RESUME 2026-07-16 — clean-design discussion):** code + all 10 tests done (tip `0c33a3eb`); dev-guide edits made-but-UNCOMMITTED in the worktree. Active thread is Dean's clean-design effort in [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md): **(1)** answer the 2 Phase-2 framing questions (see that doc's § Resume), **(2)** lock the clean logical/data-flow, **(3)** Phase 3 — verify code vs. the clean model and resolve open issues 1–4 (notably the suspected anticipated-supply-in-denominator bug), **(4)** restructure the dev-guide into clean-design + implementation sections. Only after that: commit the dev-guide, act on the pending code-review trigger, propose the push. Do NOT commit/push until Dean directs. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).
- **analyzer-metric-interface (PR #1444 MERGED → issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)):** enhancement tracked (Phase 1 metric exposure → Phase 2 external PromQL wrapper → Phase 3 polish). **Implementation deprioritized** — do NOT start until higher-priority work clears and Dean scopes Phase 1. **Archive `analyzer-metric-proposal` branch/worktree ~2026-08-13** (`git boidem`), after confirming Evgeny has no further commits.
- **Issues to file (at Dean's direction — do not file without confirmation):** Q1+Q2 from
  `planning/open-items-roadmap.md`; TA forward-plan I-1..I-25 (see [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md)).
  Already filed 2026-07-29: I-5 half-2 → #1497, I-16 → #1495, epics #1492/#1493/#1494 + #1005, veto-liveness
  #1496, cross-repo doc #1498. Pre-existing `main`-side §4a-cleanup locations → [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md).
  EPP-metric 0.9 rename needs no new issue — #1202 owns it (verification posted 2026-07-27; migrate with an old-name `or` fallback).
- **TA3 post-merge:** triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`); Step 2f E2E discussion.
- **Parallel track (NOT authorized):** WVA-vs-KEDA benchmark — see § Benchmark.
- **Governance follow-up — repeat scope-boundary incidents + candidate gates.** Full detail
  (incidents 07-14 reviewer-worktree / 07-26 unauthorized-subagent / 07-27 formula-fork / 07-29
  §4a-leaks, the reviewer-highlight default, the plan-authoring-grep note, and 8 candidate
  directions incl. the open "who edits CONVENTIONS.md" question) now lives in
  [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md). None actioned yet.

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

**Pokprod TA3 testing track (separate from WVA-vs-KEDA above):** [`planning/ta-pokprod-testing-plan.md`](../planning/ta-pokprod-testing-plan.md) (Status: DRAFT; Phases 1–4 gated on its own STOP block). **Phase 0 done locally 2026-07-29** (benchmark worktree): stale TA3 branch preserved as `benchmark-ta3-legacy` @ `892e1efa` (docs only — the two writeup docs; 2026-06-15 raw results discarded per Dean) + signed tag `archive/benchmark-ta3-legacy` → `892e1efa`; fresh `benchmark` @ `11d70a8a` (= upstream/main, has A #1478 + A′ #1479); untracked local `benchmark/reference-legacy/` holds 3 guidellm workload profiles + patched-guide sample + settings for re-application. **Awaiting Dean's pushes** (fork/origin only, never upstream): `git push origin archive/benchmark-ta3-legacy`, then `git push -u origin benchmark` (⚠️ rewrites `origin/benchmark` — `--force-with-lease`; the 2 harness commits survive via the archive tag + legacy branch). Status file: [`session/status/benchmark.md`](status/benchmark.md).

**Methodology pivot (Dean redirection, 2026-07-30).** Pivoted to a **controlled shared-cluster
setup** (our-NS-only `-p dhl-wva-209`; skip steps `02`/`08`; never full teardown; end-user path runs
standard PUBLIC llm-d-benchmark, our fork is a safety-net only; waits on Ofer's two-variant scenario
landing upstream). Planner Type-3 revision DONE (`de688be8`/`593abb4a`/`bcb0b468` on `plans`; §6
controlled-setup rewrite + §7.0 longer-term goals — supersedes memory
`project_benchmark_makefile_two_variant_todo`). Phase 2 harness `6505de62` (fork-only, NOT pushed);
Phase 3 EXECUTED (`dhl-wva-209` created); hazard analysis resolved (live steps `00,03✎,04,05,07✎,09`;
3 fork-patch presence-gates applied, uncommitted). Blocked-on-Dean items in § Blocked on; 4 coder
review points in the status file. Full detail: [`planning/ta-pokprod-testing-plan.md`](../planning/ta-pokprod-testing-plan.md)
+ [`session/status/benchmark.md`](status/benchmark.md) (state: `blocked`).

---

## TA3 (ThroughputAnalyzer) — MERGED `efca1b4c` 2026-06-16

**PR #1250 MERGED** onto main `efca1b4c` (squash). Two post-merge fixes by ev-shindin: `34c9be9b` (booting-replica TotalSupply; NaN/Inf-A guard) + `b2f1d7ef` (e2e fake-metrics). TA3 implementation mission complete. 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`) to triage; Step 2f E2E pending discussion.

**Forward work:** [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) — 26 internal issues (P0→P3): correctness bugs, silent error detection, test quality, architectural follow-ups, dev guide + user guide gaps.

**Dev guide gaps (P0, file as immediate PR):** stale PromQL groupby labels in 3 query examples (I-21); `itl_knowledge_store.go` still in package structure though removed (I-22); `nKV`/booting-replica supply note missing (I-23). See forward plan §§ I-21–23.

**Plan docs (historical):** [`planning/TA-Plan.md`](../planning/TA-Plan.md), [`planning/TA3.1-plan.md`](../planning/TA3.1-plan.md) (HISTORICAL — all tasks landed; reconciliation table added 2026-06-17), [`planning/archive/PR1250-deep-review.md`](../planning/archive/PR1250-deep-review.md) (DRAFT code review with post-merge addendum), [`docs/developer-guide/throughput-analyzer.md`](docs/developer-guide/throughput-analyzer.md) (Type 4 — 3 stale items above).

---

## Multi-Analyzer mission

Three branches, one mission. See [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) for cross-cutting design (mission, architecture, alternatives considered, future direction) and [`planning/multi-analyzer-coder-rules.md`](../planning/multi-analyzer-coder-rules.md) for coder agent rules.

| Item | Branch / PR | Plan |
|---|---|---|
| Item 3 — Race-safe analyzer registry | `multi-analyzer-registration` / [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) **MERGED** 2026-06-07 | [`multi-analyzer-registration-plan.md`](../planning/multi-analyzer-registration-plan.md) |
| Item 2 — Universal threshold post-step + aggregation helpers | `multi-analyzer-threshold` / [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) **MERGED** | [`multi-analyzer-threshold-plan.md`](../planning/multi-analyzer-threshold-plan.md) |
| Item 1 — Per-analyzer slice → optimizers (delete combine) | `multi-analyzer-optimizer` / [#1246](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1246) **MERGED** 2026-06-10 | [`multi-analyzer-optimizer-plan.md`](../planning/multi-analyzer-optimizer-plan.md) |

The old `engine-multi-analyzer` branch and PR #1113 are **superseded** by the 3-PR split. PR #1113 **CLOSED** 2026-06-17; branch archived `archive/engine-multi-analyzer`; worktree removed.

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
- ~~Replica-count accounting consistency (TA `len(variantMetrics)` vs sat_v2 `readyCount`)~~ → **F8** — **RESOLVED** by `34c9be9b` (`ReplicaCount = nKV`, mirrors sat_v2)
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10**
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- Engine SchedulerQueue wiring — ✅ landed with #1246 merge (2026-06-10, `09e1c386`).

Infra / misc (no design-doc home; file as separate issues):

- **TA forward plan** — 26 internal issues + 5 deferred features (correctness, observability, tests, architecture, docs): [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md).
  - **Deferred features (Group 0)** — code removed during #1250 dev cycle whose design intent is preserved: D-1 ITL knowledge store (historical A,B per variant, warm-up skip), D-2 GPS-mismatch SC gate, D-3 EPP-absent SC gate, D-4 FreshnessStatus staleness gate (dead end-to-end), D-5 `has*` throughput sentinels (nil-vs-zero for 3 fields). None are deprecated — all return in later PRs (D-2/D-3 via #1261, D-4 via I-6, D-5 via #1264, D-1 via I-18).
  - Key issues: collector key unification (I-1, P0 latent bug), gate observability (I-5, P0), dev guide fixes (I-21–23, P0), per-analyzer status return (I-17→#1261), effectiveEnabled (I-16→`planning/PR1266-fixup-effectiveEnabled.md`).
- **ta-itl-demand-test-gaps** (deferred, no 0.9 deadline, no owner) — 3 optional test-coverage additions for the throughput analyzer's ITL model validator + `computeLocalDemand`, flagged non-blocking by ev-shindin in PR F #1503 review. Plan ready: [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md). No branch/worktree cut — create when a coder is assigned.
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); see forward plan I-8.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- ~~**ndots fix standalone PR**~~ — landed with #1250 merge (`efca1b4c`). No action needed.
- ~~**E2E throughput wiring test is a no-op under the opt-in gate**~~ — `b2f1d7ef` converted to fake-metrics/saturation-driven; coverage honesty comment added. Gap acknowledged; TA-isolated scale-up signal has no e2e coverage (by design — covered by unit tests). See forward plan I-14 (e2e robustness) and I-11 (test rot).
- **`runRegisteredAnalyzers` deletion** — dead-code in `engine_v2.go`; not removed in #1266. Standalone cleanup PR. Plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| planner | `planning/open-items-roadmap.md` | **SCORED** (2026-06-15) | All areas scored (multi-analyzer, TA, D52/EV52). Committed `c71db32d`. See roadmap for Q1/Q2 priority list and dep graph. **Both #1250 and #1266 now merged — file Q1+Q2 items as GitHub issues.** |
