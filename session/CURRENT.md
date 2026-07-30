# Current Work

**Last updated:** 2026-07-30

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-07-23 — TA 0.9 task plans authored (4 PRs) + design reconciliation.** Four coder-ready Type 3 plans committed on the plans branch (`64a102c4`), off `main@f5b7577c`: **A** `ta-devguide-fixes` (I-21/22/23 dev-guide, doc-only), **A′** `ta-registration-safety` (`effectiveEnabled` opt-in — config-absence veto + startup log; covers only the config-absence half), **D** `ta-veto-liveness` (per-analyzer liveness gate: an uninformative analyzer — never-had-metrics / error / stale — cannot veto scale-down regardless of cause; saturation token-capacity **not** exempt; safety floor = no live analyzer → no scale-down; "last non-error analysis time" is the signal), **C** `ta-model-level-demand` (TA decode demand from a **model-level** arrival sum `Λ_req×avgOL` + queue-drain, per TA-demand §3.3/§3.5 & TA-overview:26 "demand per model"; dissolves the former per-instance-merge **I-1** for TA — `ReplicaMetrics.ArrivalRate` kept for QM/`allocation.go`). **Design reconciliation** (from re-reading TA HL design vs code): demand is per-model (code had diverged to per-pod summation); supply/k*/PRC are **arrival-independent** (`DefaultKSat`·KV/ITL — correct as-is, arrival→0 cannot corrupt PRC); the arrival-driven `k_knee` (TA-supply §5.5) is **unimplemented → DEFERRED** to a future TA phase (prefill-heavy; likely covered by sat_v2 K2); A=0 fallback left as-is. EPP-metric semantics fact-find **completed 2026-07-26** (planner-run, read-only; see tail) — signal confirmed sound for PR C; one plan fix applied (dropped an inert `model_name` fallback from the Commit 1 query template); metric is deprecated in EPP 0.9 (dual-written, family-wide 0.9 rename tracked by existing issue **[#1202](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1202)**). **Sequencing: A + C parallel; A′ → D sequential** (shared `engine_v2.go` / `multi-analyzer-pipeline.md`). Note folded into [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) (I-1 reframed as not-a-TA-blocker). **Status (2026-07-28):** **A [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478) MERGED** (2026-07-28) and **A′ [#1479](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1479) MERGED** (2026-07-28); **C [#1480](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480)** and **D [#1481](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481)** still OPEN (reviewer+assignee ev-shindin). The `#1477`/compile-failure detour is resolved — upstream fix landed as **#1483** (#1477 closed as superseded), main compiles. **Status (2026-07-29):** all four PRs opened; **A #1478 + A′ #1479 MERGED** (2026-07-28). **C #1480 + D #1481** completed round-2/round-3/round-4 review, forward-rebased onto the current `upstream/main` tip **`dfc21e2c`** (both cleanly based on it, gates green incl. `-race`, reviews closed), and **force-pushed to origin 2026-07-29** (Dean-authorized): **C → `b2acffd6`** (6 commits; round-4 review ready-to-push, F3 §4a cleanup done), **D → `c32235be`** (8 commits; round-3 APPROVE, D.1/D.2/D.3 folded). Both confirmed **MERGEABLE** on GitHub, OPEN, awaiting ev-shindin re-review. See PR Status rows for per-branch detail. **Status (2026-07-30):** **D #1481 MERGED** 2026-07-30 07:16Z (`f5261c8e` on `main`; only C left of the C/D pair). **C #1480 still OPEN but blocked on re-approval** — ev-shindin APPROVED on `13981f1d` (07:51Z) then that approval **auto-dismissed** when C's HEAD advanced to **`c4b65702`** (merged `main`+D in via `b1ec8905`, threaded the `arrivalRate` arg through the #1481 liveness test call sites via `c4b65702`; linear history, not a force-push) → `reviewDecision=REVIEW_REQUIRED`, MERGEABLE + CI-green but merge button blocked pending a fresh approve on `c4b65702`. Reviewer replies to ev-shindin's round-1 reviews **POSTED 2026-07-29** (C [issuecomment-5123171764](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480#issuecomment-5123171764), D [issuecomment-5123171907](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481#issuecomment-5123171907)); #1498 expanded to 3 operator-doc requirements (added "TA must not be enabled without EPP arrival metrics"). **PR E `ta-gate-observability` IMPLEMENTED + internally reviewed clean** (2 commits, tip `67ac0476`, off `f5261c8e`; no findings; awaiting Dean's push confirmation). **PR F `ta-correctness-guards` IMPLEMENTED** (5 commits I-2/I-3/I-4/I-6 + dev-guide, tip `0e4f496c`; internal review pending; Commit 5 = the D #1481 follow-ups DR-1/DR-2/DR-3 still to do). See PR Status rows.
- **2026-07-21 — Metric-based analyzer interface proposal → PR #1444 (OPEN).** New external-facing proposal: each analyzer produces, per finest-grain item, a **demand** `D` and a **target** `P` (per-replica capacity), same unit so `D/P` = replicas — shape symmetric with KEDA/HPA. Two goals: (1) expose all analyzer results (internal + external) as `wva_analyzer_*` metrics; (2) define external analyzers as PromQL (analyzer-centric definition + selector, pod→ScaledObject reduction default `avg`, ordered target fallbacks with observability-only `e` label). No code changes; optimizer coordination + actuation unchanged; each ScaledObject owned by exactly one of {KEDA, WVA}. Internal working draft (retains open-questions + cross-refs to [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md)): [`planning/analyzer-metric-interface-proposal.md`](../planning/analyzer-metric-interface-proposal.md). Promoted to code branch `analyzer-metric-proposal` (worktree kept) as `docs/proposals/analyzer-metric-interface.md` (house template, Status: Draft, author Dean); committed `39a83d0b` (DCO-signed), pushed origin, **PR [#1444](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1444)** to upstream `main`, reviewer ev-shindin. **2026-07-22 update:** went through a review round — Evgeny (approver) pushed a correctness pass (`607699f5`: PromQL aggregator fixes, external bare-selector shape, configurable model/namespace labels, provenance on separate series); Dean pushed follow-up refinements (`ff3e168b`: `match:` ScaledObject selector, role grounded in the `llm-d.ai/role` pod-template label, per-role demand reconciled in utilization-space, `orZero` explained); reply posted to Evgeny. Tip `ff3e168b`; **PR #1444 MERGED 2026-07-22 — Evgeny approved, CI green** (proposal now on upstream `main`). Internal draft reduced to a pointer to the canonical branch doc; `optimizer-coordination-design.md` gained the interface-proposal pointer + the per-role-demand/utilization reconciliation note. Tracking issue **[#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)** opened (assignees Dean + ev-shindin; umbrella Phase 1/2/3). Implementation **not started — deprioritized** behind higher-priority work. Authoring worktree/branch kept ~3 weeks then archive via `git boidem` (~2026-08-13; Evgeny may still commit).
- **2026-06-17 — TA post-merge deep review + forward plan.** Independent code review of all #1250 code completed ([`planning/PR1250-deep-review.md`](../planning/PR1250-deep-review.md), Status: DRAFT). Found 3 systemic issues: (1) no single canonical collector instance key — scheduler loop keys on wrong port label, so `ArrivalRate` silently never merges into KV data (config-masked today, latent correctness bug); (2) split-contract test rot — ~20 unit assertions are `Expect(RC)==0` (unconditionally true), headline scale tests are tautological; (3) "off by default" lives in YAML content not code — gate defaults `nil→true`, runtime edit silently ignored. Two post-merge fixes by ev-shindin (`34c9be9b` booting-replica supply, `b2f1d7ef` e2e fake-metrics) supersede some findings; remaining 25 internal issues organized in [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) with P0/P1/P2/P3 priority + PR groupings. Dev guide has 3 stale items (I-21 PromQL, I-22 removed file, I-23 ReplicaCount); user guide is missing (I-24).
- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Tail (compressed — recover via the ID/ref):**

- 2026-07-30 — **TA 0.9 D #1481 MERGED** 2026-07-30 07:16Z (`f5261c8e` on `main`; `main` advanced `dfc21e2c`→`f5261c8e`). Tracker **#1496** ready to close (confirm with Dean first — GitHub action). **C #1480** approval dismissed: ev-shindin APPROVED on `13981f1d`, then C's HEAD moved to `c4b65702` (merge main+D `b1ec8905` + thread `arrivalRate` through #1481 liveness test calls `c4b65702`; linear, not a force-push) → `dismiss_stale_reviews` fired → **REVIEW_REQUIRED**; MERGEABLE + CI-green, needs fresh re-approval on `c4b65702`. Provenance of that C push (Dean or C coder) unconfirmed.
- 2026-07-30 — **PR E `ta-gate-observability` implemented + reviewed clean.** 2 commits off `main@f5261c8e`: `033b0529` (refactor: `ThroughputAnalyzerEnabled` onto `*Config`, migrate/rename test, delete `cmd/main_test.go`) + `67ac0476` (feat: K8s Warning event `ThroughputAnalyzerRestartRequired` + restart log when a live ConfigMap edit can't change TA registration; namespace-local ConfigMaps out of scope). Tip `67ac0476`. Gates green (envtest 35/35, lint 0, DCO 2/2, §4a clean); dev-guide updated. Internal review FINAL, **no findings**: [`planning/ta-gate-observability-review.md`](../planning/ta-gate-observability-review.md). Origin branch exists (empty base); tip commits **NOT pushed**, no PR — awaiting Dean's push confirmation. Tracker #1497.
- 2026-07-30 — **PR F `ta-correctness-guards` implemented** (5 commits off `main@f5261c8e`, tip `0e4f496c`): `101e64ae` I-3 NaN-k guard in `ObservationWindow.Add`, `3b0b5cdf` I-6 real per-replica freshness in collector, `b9670047` I-2 shared `validITLModel`, `d2618824` I-4 NaN/`>1` KV-usage guard in `computeLocalDemand`, `0e4f496c` dev-guide. Gates green (make test full-repo, lint 0, DCO 5/5, §4a clean); no deletions. Internal review **pending** (`review__ta-correctness-guards-ready.md` open). Commit 5 (D #1481 follow-ups DR-1/DR-2/DR-3, `saturation/engine_v2.go`) still to do — doorbell `.WIP`. Origin branch exists (empty base); tip commits not pushed. Plan: [`planning/ta-correctness-guards-plan.md`](../planning/ta-correctness-guards-plan.md).
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
| ta-devguide-fixes | [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478) | **MERGED** 2026-07-28 (base upstream `main`; ev-shindin) — 4 docs-only commits; NTH-1 `port` label fix folded in; internal review FINAL/APPROVE: [`planning/ta-devguide-fixes-review.md`](../planning/ta-devguide-fixes-review.md). Plan: [`planning/ta-devguide-fixes-plan.md`](../planning/ta-devguide-fixes-plan.md). | `1aa099d0` |
| ta-registration-safety | [#1479](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1479) | **MERGED** 2026-07-28 (base upstream `main`; ev-shindin) — 5 commits (`effectiveEnabled` opt-in + startup non-registration log + dev-guide + F1/F2 follow-ups); review FINAL, no outstanding findings: [`planning/ta-registration-safety-review.md`](../planning/ta-registration-safety-review.md). F3 (cross-package veto coverage) accepted as documented — closer fit for PR D. | `b706228d` |
| ta-veto-liveness | [#1481](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481) | **MERGED 2026-07-30** 07:16Z (`f5261c8e` on `main`; base was upstream `main@dfc21e2c`; ev-shindin approved). 8 commits, merged tip `c32235be`. ev-shindin left **3 non-blocking follow-ups** on `saturation/engine_v2.go` (:182 zero-`AnalyzedAt`→treat as now; :203 `OptimizationInterval()`==0→threshold-0 blocks all scale-down; :325 prune all-removed-vs-transient comment) — approval said "address in a follow-up PR"; **folded into PR F Commit 5 (DR-1/DR-2/DR-3)**, not a separate PR. Tracker **#1496 ready to close** (pending Dean's confirm). Round-3 review APPROVE; D.1/D.2/D.3 folds landed; **T1b closed**. Review: [`planning/ta-veto-liveness-review.md`](../planning/ta-veto-liveness-review.md). Plan: [`planning/ta-veto-liveness-plan.md`](../planning/ta-veto-liveness-plan.md). | `f5261c8e` |
| ta-model-level-demand | [#1480](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480) | **OPEN · MERGEABLE · CI green but blocked on re-approval** (base upstream `main`; ev-shindin). ev-shindin **APPROVED 2026-07-30 07:51Z on `13981f1d`**, then that approval **auto-dismissed** when C's HEAD advanced to **`c4b65702`** — `b1ec8905` (merge `main`, now carrying D `f5261c8e`, into C) + `c4b65702` (thread the `arrivalRate` arg through the #1481 liveness test call sites). Linear history (`13981f1d` ancestor of `c4b65702`), a legitimate main-integration, **not** a force-push → branch protection `dismiss_stale_reviews` fired → **reviewDecision=REVIEW_REQUIRED**. **Needs a fresh approve on `c4b65702`** (delta since approval = merge-only + test-call arg threading, no logic change). Provenance of the `b1ec8905`/`c4b65702` push to origin/C **unconfirmed** (Dean or C coder — not planner-authorized this session). Approval carried one **advisory phrasing note** (non-blocking): the demand-liveness *warning* is observability-only; the real zero-arrival protection is the multi-analyzer **live-consensus veto**, not the warning — folded into **PR F dev-guide scope** (C's dev-guide has no `1481`/`liveness` match → no C change). 6→8 commits. All gates green. Review: [`planning/ta-model-level-demand-review.md`](../planning/ta-model-level-demand-review.md). Plan: [`planning/ta-model-level-demand-plan.md`](../planning/ta-model-level-demand-plan.md). | `c4b65702` |
| ta-gate-observability (PR E) | — (#1497) | **IMPLEMENTED + internally reviewed clean; awaiting Dean's push confirmation** — P0, I-5 half 2 (runtime ConfigMap-edit blind spot). 2 commits off `main@f5261c8e`: `033b0529` (refactor: `ThroughputAnalyzerEnabled` onto `*Config`; migrate/rename test to `internal/config`; delete `cmd/main_test.go`) + `67ac0476` (feat: `ConfigMapReconciler.ThroughputRegistered` field + K8s Warning event reason `ThroughputAnalyzerRestartRequired` + restart log when live TA-enablement diverges from frozen startup; namespace-local ConfigMaps out of scope). Tip `67ac0476`. Gates green (envtest 35/35, lint 0, gofmt, build, DCO 2/2, §4a clean); dev-guide updated. Internal review FINAL, **no findings** (independently re-verified): [`planning/ta-gate-observability-review.md`](../planning/ta-gate-observability-review.md). Origin branch exists (empty base); **tip commits NOT pushed**, no PR — awaiting Dean's push confirmation. Plan: [`planning/ta-gate-observability-plan.md`](../planning/ta-gate-observability-plan.md). Tracker #1497; cross-repo doc companion #1498. | `67ac0476` |
| ta-correctness-guards (PR F) | — | **IMPLEMENTED (5 commits); internal review pending; Commit 5 still to do** — off `main@f5261c8e` (not stacked on C #1480), tip `0e4f496c`: `101e64ae` I-3 NaN-k guard in `ObservationWindow.Add`; `3b0b5cdf` I-6 real per-replica freshness in collector; `b9670047` I-2 shared `validITLModel` across both fit tiers; `d2618824` I-4 NaN/`>1` KV-usage guard in `computeLocalDemand`; `0e4f496c` dev-guide. Gates green (make test full-repo, gofmt, lint 0, build, DCO 5/5, §4a clean); no deletions. **Commit 5 (DR-1/DR-2/DR-3)** — the D #1481 review follow-ups on `saturation/engine_v2.go` (interval-zero clamp / fail-safe zero `AnalyzedAt` / prune comment) + ev-shindin's C safety-phrasing note in dev-guide — **added to the plan (`3d632313`) but not yet coded** (doorbell `.WIP`; conflict-free with C, disjoint from Commits 1–4). Internal review pending (`review__ta-correctness-guards-ready.md` open — do not act until Dean directs). Origin branch exists (empty base); tip commits not pushed. No GitHub tracker issue yet (I-2/I-3/I-4/I-6 + DR-1/DR-2/DR-3 — open question). Plan: [`planning/ta-correctness-guards-plan.md`](../planning/ta-correctness-guards-plan.md). | `0e4f496c` |
| ta-testing (integration) | — | **Local test-only branch** (never an upstream PR) — `db530eed`, tag `ta-0.9-test-20260728` = upstream/main `11d70a8a` + C #1480 + D #1481 via `git merge --no-ff` (one semantic conflict resolved: C's `arrivalRate` param added to D's new test call sites). All gates green incl. `-race`. Image `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (`sha256:ce5fac61…`, linux/amd64) built. **Branch + tag + image NOT pushed** (Dean-only; needs quay creds). Status: `session/status/ta-testing.md`. | `db530eed` |

---

## Blocked on

None currently.

## Next steps

- **TA 0.9 coding — A + A′ + D MERGED; C blocked on re-approval; E reviewed-awaiting-push; F awaiting review.**
  **A [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478)**,
  **A′ [#1479](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1479)** (both 2026-07-28)
  and **D [#1481](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481)** (2026-07-30,
  `f5261c8e`) are **MERGED**. **C [#1480](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480)**
  is **OPEN · MERGEABLE · CI green but blocked on re-approval** — ev-shindin's 07:51Z approval (on
  `13981f1d`) auto-dismissed when C's HEAD advanced to **`c4b65702`** (merged main+D in + threaded
  `arrivalRate` through the #1481 liveness test calls; linear, not a force-push) →
  `reviewDecision=REVIEW_REQUIRED`. **Remaining follow-up:**
  (1) **C needs a fresh ev-shindin approve on `c4b65702`** — the delta since the dismissed approval is
  merge-only + test-call arg threading (no logic change). GitHub-write to nudge (comment vs.
  re-review request) is **held pending Dean's decision on mechanism + explicit `gh`**. When C merges,
  flip its PR Status row to MERGED and close tracker **#1495**; F then rebases onto main.
  (2) **Provenance of the `b1ec8905`/`c4b65702` push to origin/C is unconfirmed** (Dean or C coder) —
  confirm with Dean.
  (3) D's tracker **#1496 is ready to close** (merged) — pending Dean's confirm. D's 3 non-blocking
  review follow-ups ride **PR F Commit 5 (DR-1/DR-2/DR-3)**, not a separate PR.
  (4) Reviewer replies to ev-shindin's round-1 reviews are **POSTED 2026-07-29** (C
  [issuecomment-5123171764](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1480#issuecomment-5123171764),
  D [issuecomment-5123171907](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1481#issuecomment-5123171907)).
  (5) **`ta-testing` integration branch is stale** — its `db530eed` cut merged the pre-merge C+D
  branches; now that D is on `main` and C's tip moved to `c4b65702`, an integration re-cut / image
  rebuild is an **open question** (only meaningful if Dean still wants a combined pre-merge test image;
  otherwise C-on-main after merge suffices). Raise with Dean.
- **TA 0.9 remaining code work — PR E + PR F (see PR Status rows).** **PR E `ta-gate-observability`**
  (P0, I-5 half 2, tracker #1497): **IMPLEMENTED + internally reviewed clean** (2 commits, tip
  `67ac0476`, off `main@f5261c8e`; no findings). **Next action pending Dean's push confirmation** —
  origin branch exists (empty base) but tip commits are **NOT pushed** and there is no PR yet; the
  push + PR-open needs Dean's explicit confirmation. **PR F `ta-correctness-guards`** (P1,
  I-2/I-3/I-4/I-6): **IMPLEMENTED** (5 commits, tip `0e4f496c`, off `main@f5261c8e`, not stacked on C).
  Remaining: (a) **Commit 5 (DR-1/DR-2/DR-3)** — D #1481's 3 review follow-ups on
  `saturation/engine_v2.go` + C's dev-guide safety-phrasing note — plan-added (`3d632313`) but **not
  yet coded** (doorbell `.WIP`); (b) **internal code review** of F (`review__ta-correctness-guards-ready.md`
  open — run when Dean directs); (c) push needs Dean's confirmation; (d) if C merges first, F takes
  one ordinary rebase onto main (conflict surface small — C never touches `computeLocalDemand`/
  `resolveITLModel` bodies). Scope was re-derived honestly at authoring time: I-4 a LIVE gap, I-6 real
  (dead staleness gate), I-2 minor, I-3 defense-in-depth.
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
- **Plan-authoring process note (from A′ review, not yet actioned):** the coder found 3
  pre-existing tests broke on the `effectiveEnabled` behavioral-contract change because their
  fixtures relied on "absent config entry defaults to enabled" as a shorthand for "just use
  defaults" — none were in the plan's declared file list, only found because the coder searched
  broadly. Suggests the semantic-pivot-grep step (CONVENTIONS.md, per-task rule) should widen to
  `grep -rl` across all `_test.go` files for the changed function/default, not just the files
  being edited, for any future behavioral-contract-change plan. Not yet folded into CONVENTIONS.md
  — same ownership question as the governance item below.
- **TA forward plan — immediate P0 items (now):**
  - ~~**I-21/I-22/I-23**~~ — **DONE** on `ta-devguide-fixes` (PR A), **PR [#1478](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1478) OPEN**
    (tip `93742a52`). Stale PromQL examples, removed-file reference, and `nKV`/booting-replica note
    all fixed; internally reviewed APPROVE. See PR Status row above.
  - **I-5** — gate observability. Half 1 (startup "TA not registered" log) shipped in A′ #1479. Half 2 (K8s Warning event + restart log when runtime configmap edit is silently ignored) = **PR E `ta-gate-observability`, IMPLEMENTED + reviewed clean (tip `67ac0476`), awaiting Dean's push confirmation, tracker #1497** (see PR Status row + Next steps above). See forward plan § I-5, I-12.
  - **Discuss priorities:** review forward plan with Dean before coding any P1 items (collector key unification I-1 is the highest-risk correctness item; test-rot I-11 unlocks future reviewability).
- **wva-analyzer-lifecycle (PLAN READY):** config-driven analyzer registration, ManagedAnalyzer lifecycle (Activate/Deactivate/Reactivate), live-set refactor, effectiveEnabled fix, remove startup gate. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the `PR1266-fixup-effectiveEnabled.md` stopgap (that plan is now moot — the full fix is in Commit 3g of the lifecycle plan). Pending implementation kick-off.
- **optimizer-pd-role-ceiling (RESUME 2026-07-16 — clean-design discussion):** code + all 10 tests done (tip `0c33a3eb`); dev-guide edits made-but-UNCOMMITTED in the worktree. Active thread is Dean's clean-design effort in [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md): **(1)** answer the 2 Phase-2 framing questions (see that doc's § Resume), **(2)** lock the clean logical/data-flow, **(3)** Phase 3 — verify code vs. the clean model and resolve open issues 1–4 (notably the suspected anticipated-supply-in-denominator bug), **(4)** restructure the dev-guide into clean-design + implementation sections. Only after that: commit the dev-guide, act on the pending code-review trigger, propose the push. Do NOT commit/push until Dean directs. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).
- **analyzer-metric-interface (PR #1444 MERGED → issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)):** enhancement tracked (Phase 1 metric exposure → Phase 2 external PromQL wrapper → Phase 3 polish). **Implementation deprioritized** — do NOT start until higher-priority work clears and Dean scopes Phase 1. **Archive `analyzer-metric-proposal` branch/worktree ~2026-08-13** (`git boidem`), after confirming Evgeny has no further commits.
- ~~**#1266 effectiveEnabled fixup:**~~ **SUPERSEDED** by wva-analyzer-lifecycle plan (see above). Do not implement `planning/PR1266-fixup-effectiveEnabled.md`.
- **runRegisteredAnalyzers deletion:** dead-code in `engine_v2.go`; plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Issues to file:** Q1+Q2 from `planning/open-items-roadmap.md`; TA forward plan internal issues I-1 through I-25 (file as GitHub issues at Dean's direction — do not file without confirmation). **Already filed 2026-07-29:** I-5 half 2 → **#1497**; I-16 (effectiveEnabled, shipped via #1479) → **#1495**; TA-0.9 epic structure → **#1492/#1493/#1494** + adopted **#1005**, veto-liveness → **#1496**, cross-repo doc → **#1498** (see Recent activity). **New §4a-cleanup item** (from PR C round-4): a pre-existing `main`-side §4a leak untouched by PR C — `docs/developer-guide/throughput-analyzer.md:671` (`Design: plans/planning/TA-Plan.md…`) and `internal/engines/analyzers/throughput/analyzer_test.go` (`Regression test for F1…` ~:982, `Specs 1–5 from plan §3.4` :1189), all from #1250 `efca1b4c` — fold into the TA-forward-plan §4a/dev-hygiene backlog or a standalone one-line PR. *(EPP-metric 0.9 rename no longer needs a new issue — existing **[#1202](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1202)** owns it; verification comment posted 2026-07-27, `llm_d_epp_*` stable on `main`, dual-written, removal milestoned router v0.11. WVA can migrate now with an old-name `or` fallback.)*
- **TA3 post-merge:** triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`); Step 2f E2E discussion.
- **Parallel track (NOT authorized):** WVA-vs-KEDA benchmark — see § Benchmark.
- **Governance follow-up — repeat scope-boundary incidents (2026-07-14, 2026-07-26).** Two
  occurrences of the same underlying pattern: an agent acts on something a document *mentions*
  rather than checking scope first, even though CONVENTIONS.md already states the principle in
  prose ("documents describe what should happen; scope boundaries govern who does it").
  - **2026-07-14 (reviewer-worktree).** A reviewer ran `git stash` + `git checkout` directly in a
    coder's active worktree for a lookup that had a read-only answer (`git show <rev>:<path>`);
    state was recovered byte-identical, but Dean wants a *gate*, not another prose reminder.
  - **2026-07-26 (PR C unauthorized subagent).** The `ta-model-level-demand` (PR C) coder read
    its Type 3 plan's "PARALLEL FACT-FIND ... launch as a read-only research agent" line and
    called the Agent tool immediately, without asking — the plan's mention of a parallel task
    was misread as an instruction addressed to the coder itself. The spawned agent also
    malfunctioned (permission hooks blocked its file reads as if it were bound by the coder's
    own worktree-scope rules). Dean stopped the coder mid-session; ~17 minutes/tokens wasted.
    Root cause + fix already applied: (a) the plan-doc phrasing was rewritten
    (`9684c867`) to explicitly disclaim coder action; (b) a doc gap was identified — neither
    CODER-CONVENTIONS.md §7 nor §8 mentions "spawning a subagent via the Agent tool" as an
    action category at all (both are framed around file writes / git verbs / GitHub actions);
    (c) a feedback memory was saved so the lesson persists across sessions
    (`feedback_coder_no_unauthorized_subagents`, `feedback_plan_doc_no_other_role_actions`).
  - **2026-07-27 (PR C silent formula-semantics fork) — related but distinct pattern, same PR C
    coder session.** While fixing a genuine, adjacent bug (model-level `avgOL` was reading live
    per-cycle data instead of tracked `WorkloadShape`, reintroducing an EPP-warm-up regression),
    the coder also changed the plan-specified formula's *weighting semantics* — a
    RequestRate-weighted average across all replicas became an unweighted mean across
    non-prefill variants — and documented only the data-source fix, not the weighting change.
    It surfaced only because the reviewer re-derived the formula by hand against the plan's
    literal wording (review: [`planning/ta-model-level-demand-review.md`](../planning/ta-model-level-demand-review.md)
    F1). Existing memory `feedback_doc_accuracy_discipline` already states the general rule
    ("design evolution is normal — elevate forks early"); this is the first concrete coder-side
    violation of it. CODER-CONVENTIONS.md has no rule covering "your bug fix also changed a
    plan-specified formula's output for an input class the plan's examples didn't cover — flag
    that as its own decision point, not folded into the bug-fix narrative."
  - **2026-07-29 (PR C §4a leaks — prevention + detection both failed).** PR C shipped **14**
    §4a plans-branch-identifier leaks in code comments / test descriptions (`decision #1`,
    `review finding F1`, `§Tests 1-4`, `TA-demand §3.3/§3.5`, `TA-supply §5.5`, bare `F1`),
    introduced across two logic commits and found only on a manual round-3/4 re-scan (fixed in
    `b2acffd6`). Root cause has two halves: **(prevention)** §4a is violated by *transcription* —
    the coder copied plan/review sentences (which correctly use the identifiers) into code comments
    verbatim; §4a is a vigilance rule with no gate (compiles, passes gofmt/lint/test/DCO).
    **(detection)** failed at all three eyeball stages: coder pre-push checklist has no §4a step;
    reviewer rounds 1–2 scanned only dev-guide text, not code comments / `It(...)` strings;
    round-3 grep was too narrow (7 reported vs 14 actual). This is the **4th** PR-C convention slip
    caught only by manual re-derivation. **Concrete remedy (one mechanical gate):** grep the diff's
    added comment/test lines for
    `decision #|Decision #|review finding|\bF[0-9]\b|plan §|TA-[a-z]+ §|planning/|-plan\.md|-review\.md`
    — add to both the coder pre-push checklist and the reviewer checklist (reviewer grep must cover
    code comments + `It`/`Describe` strings, not just dev-guide text). Same structure as
    `feedback_semantic_pivot_grep`. Ownership sits with the open "who edits CONVENTIONS.md"
    question. (Consumed handoff: `plan__review-4a-gap-and-highlight-default.md`, Item 1.)
  - **Reviewer-highlight default (Dean's request 2026-07-29) — a second requirement for the
    proposed REVIEWER-CONVENTIONS.md.** Dean liked the round-4 close-out format and wants it to be
    the **default deliverable for internal code reviewers**: (a) a **change highlight** — per-commit
    table (commit → one-line what → type: logic / comment-only / doc) plus an explicit list of what
    was left out of scope and why; (b) a **critical section** — the smallest region of shipping code
    that carries the PR's actual behavior, shown inline so the verdict is legible without reopening
    the diff. Applies to the FINAL / ready-to-push close-out, not every interim round. Until
    `REVIEWER-CONVENTIONS.md` exists (candidate direction (2)), this is a backlog line — must not be
    lost. (Consumed handoff: `plan__review-4a-gap-and-highlight-default.md`, Item 2.)
  - **Candidate directions to evaluate (not yet designed):** (1) mechanical enforcement via a
    PreToolUse-style hook / `settings.json` permission rule — for 07-14, blocking
    `git stash|checkout|reset|rebase|merge` when CWD ≠ the session's declared worktree; for
    07-26, gating Agent-tool calls from role-scoped sessions pending explicit confirmation —
    `update-config` skill is the likely entry point for both; (2) a `REVIEWER-CONVENTIONS.md`
    with its own pre-action checklist, mirroring `CODER-CONVENTIONS.md`; (3) clarify who may
    edit `CONVENTIONS.md` itself — currently unowned in the doc-ownership table (open since
    07-14, still open); (4) add an explicit "coders/reviewers never spawn subagents without
    asking first, even when a document mentions launching one" rule to CONVENTIONS.md (not
    CODER-CONVENTIONS.md only, since the principle applies to every role) — exact wording TBD by
    whoever owns the edit, pending (3); (5) name a concrete safe pattern for "run code at a
    historical revision" (temp worktree/clone) so it isn't improvised under pressure again;
    (6) for the 07-27 formula-fork instance, mirror the existing semantic-pivot-grep rule
    structure — require the coder to flag, as its own decision point, any implementation change
    that alters a plan-specified formula's output for an input class the plan's own examples
    didn't cover.
    (7) add the §4a mechanical grep (see the 2026-07-29 incident bullet) to both the coder
    pre-push checklist and the reviewer checklist — a single deterministic gate that would have
    caught all 14 leaks the first time.
    (8) add the reviewer-highlight default (change-highlight table + inline critical section) to
    the proposed `REVIEWER-CONVENTIONS.md` (see the reviewer-highlight bullet above).
  - Consumed handoffs for this item: `session/handoffs/plan__review-agent-worktree-incident-and-gates.md`
    (07-14, already consumed pre-sync) and `session/handoffs/plan__coder-conventions-subagent-gate.md`
    (07-26, consumed this sync).

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

**Pokprod TA3 testing track (separate from WVA-vs-KEDA above):** [`planning/ta-pokprod-testing-plan.md`](../planning/ta-pokprod-testing-plan.md) (Status: DRAFT; Phases 1–4 gated on its own STOP block). **Phase 0 done locally 2026-07-29** (benchmark worktree): stale TA3 branch preserved as `benchmark-ta3-legacy` @ `892e1efa` (docs only — the two writeup docs; 2026-06-15 raw results discarded per Dean) + signed tag `archive/benchmark-ta3-legacy` → `892e1efa`; fresh `benchmark` @ `11d70a8a` (= upstream/main, has A #1478 + A′ #1479); untracked local `benchmark/reference-legacy/` holds 3 guidellm workload profiles + patched-guide sample + settings for re-application. **Awaiting Dean's pushes** (fork/origin only, never upstream): `git push origin archive/benchmark-ta3-legacy`, then `git push -u origin benchmark` (⚠️ rewrites `origin/benchmark` — `--force-with-lease`; the 2 harness commits survive via the archive tag + legacy branch). Status file: [`session/status/benchmark.md`](status/benchmark.md).

**Methodology pivot (Dean redirection, 2026-07-30) — pending planner Type-3 revision.** The pokprod TA benchmark has pivoted **away** from llm-d-benchmark's full `make benchmark-standup` / full-teardown flow toward a **controlled shared-cluster setup**: our-NS-only (`-p dhl-wva-209` on every invocation), **skip `step_02_admin_prerequisites`** (cluster-scoped Gateway/inference-ext CRDs + SCCs already present) and **`step_08_deploy_gaie`** (shared router control plane), and **NEVER run full teardown** (`step_04_clean_cluster_roles` deletes cluster-scoped RBAC) — clean up between runs namespace-scoped via `step_01_cleanup_previous`. **Mechanism (Dean, load-bearing):** the eventual end-user Makefile target must enumerate safe `--step`s and run **standard PUBLIC** llm-d-benchmark — our fork (`deanlorenz/llm-d-benchmark`, editable `pip install -e .`) is a **testing safety-net only**, not a dependency of the end-user path. **Sequencing dependency:** the two-variant scenario isn't upstream yet (lives on Ofer's `feat/multi-variant-benchmark`), so the public-code end-user path waits on Ofer's work landing. **Longer-term goals to record:** (1) Ofer runs with our controller image — already achievable via `WVA_IMAGE_REPO/TAG` .env seam, no code change; (2) an end-user **TA guide** in the spirit of the WVA guides on llm-d/llm-d; (3) a **Makefile target** + setup env for safe end-user TA testing on public benchmark code. **PENDING PLANNER ACTION (not done this sync — separate benchmark-planning turn):** revise `planning/ta-pokprod-testing-plan.md` §6 (setup) + §7 (scenarios) for the controlled flow, add the 3-goal section + the "public-code not fork" constraint + Ofer-upstream sequencing dependency, and supersede/absorb the deferred make-target note (`project_benchmark_makefile_two_variant_todo`). Coder is proceeding (Dean-directed) with local fork setup; pushes held for Dean's per-command OK.

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
