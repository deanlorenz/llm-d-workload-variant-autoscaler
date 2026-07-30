# Current Work

**Last updated:** 2026-07-31

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts) — live WIP only:**

- **2026-07-31 — CURRENT.md / history.md restructuring (this sync session).** Extracted all landed
  history out of CURRENT.md into a new TOC-indexed, fetch-on-demand archive
  [`session/history.md`](history.md) (3 *PR Status* tables + 2 *Activity log* sections + TA3 /
  Multi-Analyzer / Deferred-fixes *Mission* blocks — copied verbatim, verified present before any
  deletion). CURRENT.md slimmed 301→~181 lines: recent-activity tail → history pointer; PR Status
  keeps only the 4 open/actionable rows; missions collapsed to a one-line pointer. Ripple edits in
  the same commit so a future sync won't re-accrete: `session/CONVENTIONS.md` Type-5 § + s-sync-current
  SKILL Step 3a now direct landed rows/tail/missions into history.md and re-run `toc-refresh.sh`.
  Committed on `plans`; not pushed (origin/plans several commits behind, awaiting Dean's go-ahead).
- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Landed / historical:** the compressed activity tail (TA 0.9 era back through 2026-05) now lives in [`session/history.md`](history.md) → *Activity log* sections. Fetch one section at a time per that file's Reading Protocol — do not inline it here. Most recent landmark: **TA 0.9 fully landed (all six PRs #1478/#1479/#1480/#1481/#1502/#1503) 2026-07-30, `main` tip `6bfb73e1`.**

---

## PR Status — open / active only

Landed & closed rows (TA 0.9 stack, TA3 & earlier missions, upstream reviews & proposals) are
archived in [`session/history.md`](history.md) → *PR Status* sections. Only in-flight / actionable
rows stay here.

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| wva-analyzer-lifecycle | — | **PLAN READY** — config-driven analyzer activation; ManagedAnalyzer lifecycle interface; remove frozen snapshot + startup gate; fix effectiveEnabled. Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |
| ta-testing (integration) | — | **Local test-only branch** (never an upstream PR) — `db530eed`, tag `ta-0.9-test-20260728` = upstream/main `11d70a8a` + C #1480 + D #1481 via `git merge --no-ff` (one semantic conflict resolved: C's `arrivalRate` param added to D's new test call sites). All gates green incl. `-race`. Image `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (`sha256:ce5fac61…`, linux/amd64) built. **Branch + tag + image NOT pushed** (Dean-only; needs quay creds). **Note (2026-07-30): stale/moot — all six TA-0.9 PRs now on `main` (`6bfb73e1`)**, so a plain `main` checkout supersedes this pre-merge integration cut; the E/F-land refresh trigger (`planning/ta-pokprod-testing-plan.md` §4.1) is now armed — re-derive Tier-A code-under-test from `main@6bfb73e1` + rebuild/push the controller image (Dean-only; needs quay creds). Remove worktree/branch at Dean's direction. Status: `session/status/ta-testing.md`. | `db530eed` |

---

## Blocked on

- **Pokprod TA benchmark — first live controlled standup** is blocked on **Dean's explicit go-ahead**
  (Phase-4 Step 0). All prep is done (dry-run, hazard analysis, fork patches, Phase-3 namespace setup);
  also awaiting Dean's OK on 3 fork-only pushes (`6505de62`, the 3 presence-gate patches) and the
  upstream-patch-proposal decision. See § Benchmark + `session/status/benchmark.md`.

## Next steps

- **TA 0.9 coding — FULLY LANDED (all six PRs MERGED 2026-07-30; `main` tip `6bfb73e1`).** Per-PR merge
  detail + roll-up in [`session/history.md`](history.md) (PR Status + Activity log). Trackers #1495/#1496/#1497 CLOSED (C and F
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

## Completed missions (archived)

Full blocks for the **TA3 (ThroughputAnalyzer)** mission, the **Multi-Analyzer** mission, and the
**Deferred fixes (TA2 / PR-3 follow-ups)** list now live in [`session/history.md`](history.md) →
*Mission* / *Deferred fixes* sections. Live forward work from those missions stays in § Next steps
and § Issues to Open below (TA3 smoke-failure triage; the TA forward plan; the deferred TA2 fixes).

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
