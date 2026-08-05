# Current Work

**Last updated:** 2026-08-03

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts) — live WIP only:**

- **2026-08-05 — Anchor-refactor mission (goldens PR #1513 OPEN; PR-1 plan `ta-anchor-refactor-v2` FINAL,
  coder launched; PR-2 stub).** Reshaping the multi-analyzer engine so it builds the anchor (topology
  carrier) and passes the enabled-analyzer list as the ballot — "no special voting code" (Dean's corrected
  model). **goldens** `ta-anchor-goldens@a2f49ccf` = **PR [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) OPEN**
  (characterization gate freezing sat-v2-only decision-SET-identity keyed by VariantName; test-only +409/−0;
  base `upstream/main@9906dac5`; reviewer ev-shindin; `origin/ta-anchor-goldens` pushed; internal review
  FINAL — Finding 1 fixed, Finding 2 = `withSatEntry`-stability coordination note carried into the PR-1
  kickoff; **land-first** decided). **PR-1 mechanism REDESIGNED 2026-08-05** — the review agent found the
  stored-`ModelScalingRequest.Anchor` design (the Aug-4 fold-in, commits `68bda1a1`/`192ae06b`, and the
  abandoned branch commit `34055d77`) unnecessarily complex and **superseded** it with a no-stored-field
  two-phase mechanism. `planning/ta-anchor-refactor-review.md` restructured into Part 1 (review of the
  now-**SUPERSEDED** `ta-anchor-refactor-plan.md`) / Part 2 (redesign spec) / Part 3 (review of the v2
  plan, verdict APPROVE) / **Round 2** (2026-08-05, reconciled against plan tip `2e83c7fe`: verdict still
  APPROVE, zero MAJOR/correctness findings — the earlier `[sat,TA]` core concern is **RESOLVED**; 4
  doc-only findings V8/V9 should-fix + V10/V11 minor) — doc still **DRAFT** (Dean marks FINAL at his
  discretion). **`planning/ta-anchor-refactor-v2-plan.md` is now Status: FINAL** (`c279bdeb` folds
  Round-2 V8–V11; coder-ready): Phase-1 `runAnalyzersAndScore` tags every ballot entry `Enabled` (+
  existing `Live`), makes no decisions; Phase-2 `bindingAnchor` derives the anchor **on demand** by a
  per-variant merge keyed by `VariantName` ((a) identity from saturation, (b) sizing from the binding
  analyzer). **Scale-from-zero cost/PRC design** (Dean, 2026-08-05, commit `2e83c7fe` — supersedes the
  interim MAX-sentinel version `2ccf51b7`): TA emits PRC only (no Cost/AcceleratorName persistence); the
  (b)-sizing fallback is **enablement-gated** (valid only when saturation is enabled); `[TA]`-only
  zero-replica variants get PRC=0 (suppressed — reactive `scalefromzero` covers cold-start), with a
  documented (not gated) known-limitation that `[TA]`-only then cost-mis-ranks like `[sat]`-only until a
  separate pre-existing sat `Cost=0` bug is fixed (out of scope here). **Worktree/branch
  `ta-anchor-refactor-v2` created** off the goldens tip `a2f49ccf` (local only, unpushed — origin push
  pending Dean's OK). **Coder launched** — Commit 1 (§5 Phase-1 `Enabled` tag) landed, tip `6cea41f2`,
  in-progress on the remaining 4 commits (see `session/status/ta-anchor-refactor-v2.md`). Old branch
  `ta-anchor-refactor@34055d77` left unpushed, for Dean to `git boidem` at his convenience.
  Out-of-scope/deferred for PR-1: QM path (explicit-error refusal, DEFERRED §12), §2.4 partial
  scale-from-zero picker, AnalyzerName validation (separate PR), the sat `Cost=0`-for-zero-replica bug
  (separate fix). **PR-2 dynamic-refresh** `ta-anchor-dynamic-refresh` = PLAN STUB (deferred until PR-1
  lands; forward-note updated for the no-stored-field design, commit `99dc04c9`). Open GitHub-issue
  questions (Dean's call, none filed yet): the QM multi-analyzer-contract work, and the sat-v2
  zero-replica `Cost=0` bug. Design authority
  [`planning/combined-analyzer-optimizer-design.md`](../planning/combined-analyzer-optimizer-design.md);
  plans [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md) (FINAL) /
  [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (SUPERSEDED) /
  [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md).
- **2026-08-03 — ta-itl-demand-test-gaps → PR #1511 OPEN.** The 3 optional ITL/demand/supply test-gaps
  ev-shindin flagged in PR F #1503 (plus a folded-in `computeVariantSupply` direct-coverage pair) shipped
  as **PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** into upstream
  `main` (head `ta-itl-demand-test-gaps@96263639`, base `main@6bfb73e1`, 5 test-only commits DCO-signed,
  reviewer ev-shindin, assignee deanlorenz). Two internal reviews APPROVE; review FINAL
  [`planning/ta-itl-demand-test-gaps-review.md`](../planning/ta-itl-demand-test-gaps-review.md). Targeting
  0.9 (freeze 2026-08-06); MERGEABLE, awaiting Evgeny + CI. Deferred: `checkVariantGPSMismatch` diagnostic
  coverage → separate future test-only task.
- **2026-08-03 — sat_v2 cannot be disabled via config (F1 gap); Dean spawning a separate planner.**
  Root-caused (not a regression): `saturation/engine_v2.go` unconditionally prepends the saturation result
  and `effectiveEnabled` skips it by name, so `saturation:{enabled:false}` is a silent no-op — traced to
  deferred design item F1 "Pre-analysis extraction" ([`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md):506-511).
  The existing `planning/wva-analyzer-lifecycle-plan.md` Commit-2c "zero-signal" design is **REJECTED by
  Dean** ("risky hack"; warnings added to the plan, commit `663a9624`) — a real fix must solve
  `VariantCapacities` sourcing, not fake a neutral result. Dean is spawning a dedicated planner to
  scope/design it (possibly still in 0.9 — freeze was delayed). Surfaced while the **benchmark TA-lead
  experiment** coder is holding, blocked on separate planner deliverables (two-phase calibration+trigger
  workload + a "faster" methodology) plus an open feasibility question (does TA raise RC ahead of
  `k_sat=0.85`, or key off the same threshold?) — independent thread, do not conflate.
- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Recently landed (1-liners; fuller entries in [`session/history.md`](history.md) → *Activity log*):**

- 2026-07-30 — `ta-testing` refreshed → `6bfb73e1`; signed tag `ta-0.9-test-20260730` + quay image `:ta-0.9` (registry digest `sha256:80dec0e9728f…`) both pushed (executes the §4.1 refresh trigger).
- 2026-07-31 — CURRENT.md / history.md restructuring committed on `plans` (landed history extracted to the archive).

**Older / historical:** the compressed activity tail (TA 0.9 era back through 2026-05) lives in [`session/history.md`](history.md) → *Activity log* sections — fetch one section at a time per that file's Reading Protocol, do not inline here. Most recent landmark: **TA 0.9 fully landed (all six PRs #1478/#1479/#1480/#1481/#1502/#1503) 2026-07-30, `main` tip `6bfb73e1`.**

---

## PR Status — open / active only

Landed & closed rows (TA 0.9 stack, TA3 & earlier missions, upstream reviews & proposals) are
archived in [`session/history.md`](history.md) → *PR Status* sections. Only in-flight / actionable
rows stay here.

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| wva-analyzer-lifecycle | — | **PLAN — PARTIALLY REJECTED / re-scoping.** Config-driven analyzer activation + ManagedAnalyzer lifecycle. Splits into **Half A** (config-driven lifecycle + live-set refactor — Commits 1/3/4/5; ~1–2 days; `effectiveEnabled`/Commit 3g already on `main`; main risk = `NewEngine` ripple vs in-flight #1501) and **Half B** (genuinely disabling saturation — Commit 2c **REJECTED by Dean 2026-07-31**: "zero-signal" is a risky hack; needs F1 "pre-analysis extraction" to solve `VariantCapacities` sourcing; unscoped). Dean spawning a **separate planner** to scope the real sat_v2-disable fix; awaiting his call: carve Half-A-only vs scope Half-B/F1 vs hold. Warnings added to plan (`663a9624`). Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| ta-itl-demand-test-gaps | [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511) | **OPEN** — cover ITL-model / demand / supply guard branches (ev-shindin's PR F #1503 non-blocking notes + folded-in `computeVariantSupply` pair). Head `ta-itl-demand-test-gaps@96263639`, base `main@6bfb73e1`, 5 test-only commits DCO-signed, `origin/ta-itl-demand-test-gaps` pushed. Reviewer ev-shindin, assignee deanlorenz. Two internal reviews APPROVE; review FINAL [`planning/ta-itl-demand-test-gaps-review.md`](../planning/ta-itl-demand-test-gaps-review.md). Targeting 0.9 (freeze 2026-08-06). MERGEABLE; awaiting Evgeny + CI. Plan: [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md). | `96263639` |
| ta-anchor-goldens | [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) | **OPEN** — characterization "golden" gate (test-only, +409/−0, 1 file) freezing the saturation-only optimizer decision SET (keyed by VariantName; land-first ship gate for the anchor refactor). Head `ta-anchor-goldens@a2f49ccf`, base `upstream/main@9906dac5`, reviewer ev-shindin, `origin/ta-anchor-goldens` pushed. Internal review FINAL (Finding 1 fixed; Finding 2 = `withSatEntry`-stability note carried to PR-1 kickoff). Plan: [`planning/ta-anchor-goldens-plan.md`](../planning/ta-anchor-goldens-plan.md); review [`planning/ta-anchor-goldens-review.md`](../planning/ta-anchor-goldens-review.md). | `a2f49ccf` |
| ta-anchor-refactor | — | **SUPERSEDED (2026-08-05) by `ta-anchor-refactor-v2`** — see that row. Stored-`ModelScalingRequest.Anchor` design (Aug-4 review fold-in `68bda1a1`/`192ae06b`) found unnecessarily complex; superseded by a no-stored-field two-phase redesign. Plan doc header marked `Status: SUPERSEDED` (commit `9721b587`); kept for history (Part 1 subject of `planning/ta-anchor-refactor-review.md`). Branch commit `34055d77` left unpushed; Dean to `git boidem` at his convenience. Plan: [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (superseded). | `34055d77` (unpushed, superseded) |
| ta-anchor-refactor-v2 | — | **PLAN FINAL; worktree created (local); coder launched — Commit 1/5 landed.** Live PR-1 plan: no-stored-field two-phase anchor mechanism (Phase-1 tags ballot entries `Enabled`; Phase-2 `bindingAnchor` derives the anchor on demand, per-variant merge keyed by `VariantName`). Plan `Status: FINAL` (`c279bdeb`) on `plans`; review is Part 3 + **Round 2** of `planning/ta-anchor-refactor-review.md` (still DRAFT) — verdict APPROVE both rounds, zero MAJOR/correctness findings; Round 2 (2026-08-05, reconciled against `2e83c7fe`) resolved the earlier `[sat,TA]` core concern and found 4 doc-only findings V8–V11, all folded into the FINAL plan. Scale-from-zero cost/PRC design (`2e83c7fe`, supersedes the interim MAX-sentinel version `2ccf51b7`): TA emits PRC only, (b)-fallback enablement-gated, `[TA]`-only zero-replica suppressed to PRC=0 with a documented (not gated) known-limitation. Scope: 5 commits (Phase-1 / Phase-2 / QM-as-error+liveness-noop / TA-PRC-only complement / dev-guide); zero combine-arithmetic change; decision-SET-identity ship gate via #1513 goldens; opt-in enablement. Deferred/out-of-scope: QM path (DEFERRED §12), §2.4 partial scale-from-zero picker, AnalyzerName validation, sat `Cost=0`-for-zero-replica bug. Branch `ta-anchor-refactor-v2` @ `a2f49ccf` (interim base off goldens #1513, local-only/unpushed). Coder in-progress on Commit 1 (§5 Phase-1 `Enabled` tag) — landed at tip `6cea41f2`; status `session/status/ta-anchor-refactor-v2.md`. **Next:** origin push (Dean's OK, not a coding blocker); Dean marks the review doc FINAL at his discretion. Plan: [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md). | `6cea41f2` (Commit 1/5) |
| ta-anchor-dynamic-refresh | — | **PLAN STUB** — PR-2 dependent (multi-vote combine + per-iteration dynamic refresh + masked-bug fixes #1/#2/#3/#5). Deferred until PR-1 lands; do NOT start until Dean scopes it. Plan: [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md). | — |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |
| ta-testing (integration) | — | **REFRESHED 2026-07-30 → tip `6bfb73e1`** (§4.1 trigger EXECUTED). Repointed to `upstream/main` directly (`git checkout -B`, pointer move, no hand-merge) now C/D/E/F all merged. New signed tag `ta-0.9-test-20260730` **pushed to origin** (does not replace the historical `ta-0.9-test-20260728` on `db530eed`). All gates green (`make test`/lint/build; `pkg/` gone → drop from the 3-dir gofmt invocation past this tip). Image `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` **pushed to quay** (local ID `sha256:3d438b65c8…`, registry digest `sha256:80dec0e9728f…`, linux/amd64). **Integration role now vestigial** — a plain `main@6bfb73e1` checkout already has everything C/D/E/F contributed; branch value is just a stable Dean-owned tag/image pipeline name. Cleanup deferred (old tag + stale `origin/ta-testing`@`db530eed` + local `ta-model-level-demand` worktree — non-urgent, at Dean's direction). Status: `session/status/ta-testing.md`. | `6bfb73e1` |

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
  PRs merged; (2) the 3 optional test gaps on F are now **shipped as PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** (open, reviewer ev-shindin — see PR Status row); (3) PR #1501 ask-#1 watch (see PR Status row);
  (4) governance retrospective open Q — in [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md);
  (5) cleanup — old tag `ta-0.9-test-20260728` + stale `origin/ta-testing`@`db530eed` + local `ta-model-level-demand` worktree; non-urgent, raise removal with Dean (see `ta-testing` PR Status row).
- **TA 0.9 test-branch + controller-image refresh (§4.1 trigger — EXECUTED 2026-07-30).** Done: `ta-testing`
  repointed to `main@6bfb73e1`, signed tag `ta-0.9-test-20260730` pushed to origin, image `:ta-0.9` (digest
  `sha256:80dec0e9728f…`) pushed to quay — all Dean-authorized. See the `ta-testing` PR Status row; no
  outstanding action for this refresh.
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
- **sat_v2 cannot be disabled via config (F1 gap) — awaiting Dean's separate planner + scope call (2026-08-03).**
  Root cause: `saturation/engine_v2.go` unconditionally prepends the saturation result and
  `effectiveEnabled` only skips it by name, so `saturation:{enabled:false}` is a silent no-op. The real
  fix requires F1 "pre-analysis extraction" ([`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md):506-511)
  to source `VariantCapacities` independent of the saturation scaling contribution. The
  `wva-analyzer-lifecycle-plan.md` Commit-2c "zero-signal" design is **REJECTED** (risky hack; warnings
  committed `663a9624`). Dean is spawning a dedicated planner; do NOT start the real fix until he scopes
  it. Interacts with the benchmark TA-lead thread below (that coder wants sat_v2 off) — keep separate.
- **wva-analyzer-lifecycle (PLAN — PARTIALLY REJECTED / re-scoping):** ManagedAnalyzer lifecycle
  (Activate/Deactivate/Reactivate), config-driven registration, live-set refactor, effectiveEnabled fix,
  remove startup gate. **Split**: Half A (lifecycle/live-set — Commits 1/3/4/5, low-risk, ~1–2 days; note
  Commit 3g's effectiveEnabled fix already landed on `main`) vs Half B (disabling saturation — Commit 2c
  REJECTED, needs the F1 fix above). Awaiting Dean's carve/scope/hold decision (see PR Status row). Plan:
  [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the
  `PR1266-fixup-effectiveEnabled.md` stopgap.
- **anchor-refactor mission (ta-anchor-goldens #1513 → ta-anchor-refactor-v2 PR-1 → ta-anchor-dynamic-refresh PR-2):**
  goldens ship gate is **PR [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513)**
  (open, reviewer ev-shindin, land-first). **PR-1 was redesigned 2026-08-05**: the review agent found the
  stored-`.Anchor` design (Aug-4 fold-in `68bda1a1`/`192ae06b`, abandoned branch commit `34055d77`)
  superseded by a simpler no-stored-field two-phase mechanism — old plan `ta-anchor-refactor-plan.md` now
  `Status: SUPERSEDED`; live plan **`planning/ta-anchor-refactor-v2-plan.md`** is now **Status: FINAL**
  (`c279bdeb`). Reviewed across Part 3 + **Round 2** of `planning/ta-anchor-refactor-review.md` (still
  DRAFT) — **verdict APPROVE both rounds**, zero MAJOR/correctness findings; Round 2 (reconciled against
  plan tip `2e83c7fe`) resolved the earlier `[sat,TA]` core concern and found 4 doc-only findings V8–V11,
  all folded into the FINAL plan. Scale-from-zero cost/PRC design (`2e83c7fe`; supersedes the interim
  MAX-sentinel version `2ccf51b7`): TA emits PRC only, (b)-fallback enablement-gated, `[TA]`-only
  zero-replica suppressed to PRC=0 (documented, not gated, known-limitation — resolved later by a
  separate sat `Cost=0` fix). **Worktree/branch `ta-anchor-refactor-v2` created** off the goldens tip
  `a2f49ccf` (local only, unpushed). **Coder launched** — Commit 1/5 (§5 Phase-1 `Enabled` tag) landed,
  tip `6cea41f2`; in-progress on the remaining 4 (status: `session/status/ta-anchor-refactor-v2.md`). Old
  branch `ta-anchor-refactor@34055d77` left unpushed for Dean to `git boidem`. Still open: propose origin
  push `git push -u origin ta-anchor-refactor-v2` (Dean's OK, matching-origin convention, not a coding
  blocker); Dean marks the review doc FINAL at his discretion; two GitHub-issue questions (Dean's call,
  none filed): QM multi-analyzer-contract work, sat-v2 zero-replica `Cost=0` bug. PR-2 is a deferred stub
  (forward-note updated for the no-stored-field design, `99dc04c9`; do NOT start until PR-1 lands).
  Plans: [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md) (FINAL),
  [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (superseded),
  [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md).
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

**TA-lead experiment — "does ThroughputAnalyzer trigger scale-up faster than saturation?" (setup
check → planner, 2026-08-03).** Dean's next benchmark: run combined **TA+SAT** and test whether a
*calibrated* TA raises RequiredCapacity while `k* < k_sat = 0.85` — leading saturation's reactive
KV-threshold trip. **Coder is HOLDING** (clean baseline on `dhl-wva-209`, no run in flight); the
setup check went to the **planner**, who owes: (a) a **two-phase workload** (Phase A sub-scale
calibration sweeping KV util `[0.15, 0.85]` so TA collects ≥10 OLS samples with `KSpread ≥ 0.30`
and flips `T2-default → OLS-Ready` *without* itself scaling — `wva_sat2_short` jumps straight to
saturating rates, unsuitable; Phase B trigger step), and (b) a **"faster" methodology** (Δt from a
fixed reference to HPA `desiredReplicas: 2`, A/B SAT-only vs TA+SAT on identical workload, repeats +
noise floor). **Open feasibility question the planner must answer before a cluster run:** does TA's
`Analyze()` actually raise RC ahead of the KV threshold, or does it also key off `k* ≥ k_sat = 0.85`
(`DefaultKSat = 0.85`, "mirrors" saturation) — if the latter, a lead is impossible by construction
and the experiment needs reframing. Depends on (but is a **separate thread** from) the sat_v2-disable
F1 gap in § Next steps — the earlier attempt to isolate TA via `saturation:{enabled:false}` was the
no-op that surfaced that bug; the TA-lead experiment runs TA+SAT combined, so it does **not** need
sat_v2 disabled. Setup-check detail in handoff `plan__ta-sat-scaleup-lead-setup.md`.

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
- ~~**ta-itl-demand-test-gaps**~~ — **SHIPPED as PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** (open, reviewer ev-shindin; ITL-model validator + `computeLocalDemand` + folded-in `computeVariantSupply` pair). No longer a backlog item — tracked in PR Status. Plan: [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md).
- **`checkVariantGPSMismatch` test coverage (deferred, no owner)** — split out of #1511 (4 earlier skip guards to satisfy, no existing test block, diagnostic-only). Separate future test task; recorded in the `ta-itl-demand-test-gaps-plan.md` Commit-4 §. Create a branch when assigned.
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
