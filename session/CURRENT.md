# Current Work

**Last updated:** 2026-07-23

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts):**

- **2026-07-21 — Metric-based analyzer interface proposal → PR #1444 (OPEN).** New external-facing proposal: each analyzer produces, per finest-grain item, a **demand** `D` and a **target** `P` (per-replica capacity), same unit so `D/P` = replicas — shape symmetric with KEDA/HPA. Two goals: (1) expose all analyzer results (internal + external) as `wva_analyzer_*` metrics; (2) define external analyzers as PromQL (analyzer-centric definition + selector, pod→ScaledObject reduction default `avg`, ordered target fallbacks with observability-only `e` label). No code changes; optimizer coordination + actuation unchanged; each ScaledObject owned by exactly one of {KEDA, WVA}. Internal working draft (retains open-questions + cross-refs to [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md)): [`planning/analyzer-metric-interface-proposal.md`](../planning/analyzer-metric-interface-proposal.md). Promoted to code branch `analyzer-metric-proposal` (worktree kept) as `docs/proposals/analyzer-metric-interface.md` (house template, Status: Draft, author Dean); committed `39a83d0b` (DCO-signed), pushed origin, **PR [#1444](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1444)** to upstream `main`, reviewer ev-shindin. **2026-07-22 update:** went through a review round — Evgeny (approver) pushed a correctness pass (`607699f5`: PromQL aggregator fixes, external bare-selector shape, configurable model/namespace labels, provenance on separate series); Dean pushed follow-up refinements (`ff3e168b`: `match:` ScaledObject selector, role grounded in the `llm-d.ai/role` pod-template label, per-role demand reconciled in utilization-space, `orZero` explained); reply posted to Evgeny. Tip `ff3e168b`; **PR #1444 MERGED 2026-07-22 — Evgeny approved, CI green** (proposal now on upstream `main`). Internal draft reduced to a pointer to the canonical branch doc; `optimizer-coordination-design.md` gained the interface-proposal pointer + the per-role-demand/utilization reconciliation note. Tracking issue **[#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)** opened (assignees Dean + ev-shindin; umbrella Phase 1/2/3). Implementation **not started — deprioritized** behind higher-priority work. Authoring worktree/branch kept ~3 weeks then archive via `git boidem` (~2026-08-13; Evgeny may still commit).
- **2026-06-17 — TA post-merge deep review + forward plan.** Independent code review of all #1250 code completed ([`planning/PR1250-deep-review.md`](../planning/PR1250-deep-review.md), Status: DRAFT). Found 3 systemic issues: (1) no single canonical collector instance key — scheduler loop keys on wrong port label, so `ArrivalRate` silently never merges into KV data (config-masked today, latent correctness bug); (2) split-contract test rot — ~20 unit assertions are `Expect(RC)==0` (unconditionally true), headline scale tests are tautological; (3) "off by default" lives in YAML content not code — gate defaults `nil→true`, runtime edit silently ignored. Two post-merge fixes by ev-shindin (`34c9be9b` booting-replica supply, `b2f1d7ef` e2e fake-metrics) supersede some findings; remaining 25 internal issues organized in [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) with P0/P1/P2/P3 priority + PR groupings. Dev guide has 3 stale items (I-21 PromQL, I-22 removed file, I-23 ReplicaCount); user guide is missing (I-24).
- **2026-06-15 — #1275 (collector-va-attribution) CLOSED; #1263 CLOSED.** Both superseded by #1267 (`c55906a4`, merged): #1267 retained `llm_d_ai_variant` as the label fast-path and added owner-walk locator fallback (`locator.PodLocator`) — the label-drop premise of #1263 and the Attributor-seam approach of #1275 are both wrong given #1267's design (dropping the label kills shadow-pod attribution). `collector-va-attribution` branch to archive. The only non-superseded piece from #1275 is the `UnattributedReadyPods` K8s event — decision pending: fold into standalone issue. Full decisions: [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md), [`planning/PR1275-closure-capture.md`](../planning/PR1275-closure-capture.md).
- **2026-06-15 — #1266 MERGED** (`6d25b134` onto main). Addendum to #1246: `effectiveEnabled` bug fix (explicit `Enabled:false` now skips run + append), config-bridge + non-uniform Score tests, full pipeline dev guide rewrite. Note: `runRegisteredAnalyzers` dead-code was NOT removed in this PR — it remains in `engine_v2.go`; follow-up plan at [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4. `effectiveEnabled` opt-in fix (absent entry → false): [`planning/PR1266-fixup-effectiveEnabled.md`](../planning/PR1266-fixup-effectiveEnabled.md).
- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Tail (compressed — recover via the ID/ref):**

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
| collector-va-attribution | — | **CLOSED** — superseded by #1267 (`c55906a4`). #1263 closed. Archive branch via `git boidem collector-va-attribution`. See [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md). | `526ce851` |
| wva-saturation-cycle-log | #1277 | **CLOSED** 2026-06-23 — superseded by #1318. | `01bfe940` |
| wva-saturation-cycle-log-r1 | #1318 | **MERGED** 2026-06-25 (`bd357196` on main). Structured per-cycle log lines + named reason constants. | `6b6f4295` |
| wva-analyzer-lifecycle | — | **PLAN READY** — config-driven analyzer activation; ManagedAnalyzer lifecycle interface; remove frozen snapshot + startup gate; fix effectiveEnabled. Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| analyzer-metric-proposal | #1444 | **MERGED** 2026-07-22 (`ff3e168b`) — review round: Evgeny (approver) pushed a correctness pass `607699f5` (PromQL aggregator fixes, external bare-selector shape, configurable model/namespace labels, provenance on separate series); Dean pushed follow-up `ff3e168b` (`match:` ScaledObject selector, role grounded in the `llm-d.ai/role` pod-template label, per-role demand reconciled in utilization-space, `orZero` explained). Reply posted (`issuecomment-5047415526`); Evgeny **APPROVED + merged**. Tracking issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455) (Phase 1/2/3; assignees Dean + ev-shindin). Worktree kept; archive via `git boidem` ~2026-08-13. Internal draft (now a pointer to the branch doc): [`planning/analyzer-metric-interface-proposal.md`](../planning/analyzer-metric-interface-proposal.md). | `ff3e168b` |
| (upstream) v2-default-analyzer | #1442 | **Reviewed 2026-07-22** — APPROVE review posted (LGTM + 2 non-blocking comments: RC-1 inverted-pair-reset middle ground, RC-2 README per-model-flip note). Review FINAL: [`planning/PR1442-review.md`](../planning/PR1442-review.md). CI green. | (fork branch) |

---

## Blocked on

None currently.

## Next steps

- **TA forward plan — immediate P0 items (now):**
  - **I-21/I-22/I-23** — fix dev guide: stale PromQL examples (`by (pod)` → `by (instance, pod, llm_d_ai_variant)`), remove `itl_knowledge_store.go` from package structure, add `nKV`/booting-replica note. Single PR, doc-only. Plan: [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) § I-21–23.
  - **I-5** — gate observability: log "TA not registered" on the disabled path; K8s Event when runtime configmap edit is silently ignored. Fold I-12 (gate unit tests + default-config test) into same PR. See forward plan § I-5, I-12.
  - **Discuss priorities:** review forward plan with Dean before coding any P1 items (collector key unification I-1 is the highest-risk correctness item; test-rot I-11 unlocks future reviewability).
- **wva-analyzer-lifecycle (PLAN READY):** config-driven analyzer registration, ManagedAnalyzer lifecycle (Activate/Deactivate/Reactivate), live-set refactor, effectiveEnabled fix, remove startup gate. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the `PR1266-fixup-effectiveEnabled.md` stopgap (that plan is now moot — the full fix is in Commit 3g of the lifecycle plan). Pending implementation kick-off.
- **optimizer-pd-role-ceiling (RESUME 2026-07-16 — clean-design discussion):** code + all 10 tests done (tip `0c33a3eb`); dev-guide edits made-but-UNCOMMITTED in the worktree. Active thread is Dean's clean-design effort in [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md): **(1)** answer the 2 Phase-2 framing questions (see that doc's § Resume), **(2)** lock the clean logical/data-flow, **(3)** Phase 3 — verify code vs. the clean model and resolve open issues 1–4 (notably the suspected anticipated-supply-in-denominator bug), **(4)** restructure the dev-guide into clean-design + implementation sections. Only after that: commit the dev-guide, act on the pending code-review trigger, propose the push. Do NOT commit/push until Dean directs. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).
- **analyzer-metric-interface (PR #1444 MERGED → issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)):** enhancement tracked (Phase 1 metric exposure → Phase 2 external PromQL wrapper → Phase 3 polish). **Implementation deprioritized** — do NOT start until higher-priority work clears and Dean scopes Phase 1. **Archive `analyzer-metric-proposal` branch/worktree ~2026-08-13** (`git boidem`), after confirming Evgeny has no further commits.
- ~~**#1266 effectiveEnabled fixup:**~~ **SUPERSEDED** by wva-analyzer-lifecycle plan (see above). Do not implement `planning/PR1266-fixup-effectiveEnabled.md`.
- **runRegisteredAnalyzers deletion:** dead-code in `engine_v2.go`; plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Issues to file:** Q1+Q2 from `planning/open-items-roadmap.md`; TA forward plan internal issues I-1 through I-25 (file as GitHub issues at Dean's direction — do not file without confirmation).
- **TA3 post-merge:** triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`); Step 2f E2E discussion.
- **Parallel track (NOT authorized):** WVA-vs-KEDA benchmark — see § Benchmark.
- **Governance follow-up — reviewer-worktree incident (2026-07-14).** A reviewer ran `git stash` +
  `git checkout` directly in a coder's active worktree for a lookup that had a read-only answer
  (`git show <rev>:<path>`); state was recovered byte-identical, but Dean wants a *gate*, not
  another prose reminder, since this is a second occurrence of a rule already in CONVENTIONS.md.
  Candidate directions to evaluate (not yet designed): (1) mechanical enforcement via a
  PreToolUse-style hook / `settings.json` permission rule blocking `git stash|checkout|reset|
  rebase|merge` when CWD ≠ the session's declared worktree — `update-config` skill is the likely
  entry point; (2) a `REVIEWER-CONVENTIONS.md` with its own pre-action checklist, mirroring
  `CODER-CONVENTIONS.md`; (3) clarify who may edit `CONVENTIONS.md` itself — currently unowned in
  the doc-ownership table; (4) name a concrete safe pattern for "run code at a historical
  revision" (temp worktree/clone) so it isn't improvised under pressure again. CONVENTIONS.md's
  incident note currently points at the now-consumed handoff
  (`session/handoffs/plan__review-agent-worktree-incident-and-gates.md`) — that pointer will 404
  after this sync; flagging for Dean rather than editing CONVENTIONS.md directly (ownership of
  that file is itself one of the open questions above).

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

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
