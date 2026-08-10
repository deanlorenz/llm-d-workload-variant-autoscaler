# Current Work

**Last updated:** 2026-08-08

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts) — live WIP only:**

- **2026-08-07/09 — Anchor-refactor mission. PR-1 MERGED; PR-2 = #1523 OPEN, green, awaiting external
  review.**
  **PR-1 `ta-anchor-refactor-v2` = [#1516](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1516)
  MERGED** 2026-08-07 17:48:05Z, squash **`57f3fe64`** on `main` (29 files, +2077/−166). Full mission
  detail — the Aug-5 redesign, both review rounds, the C1–C5 close-out, ev-shindin's pre-merge
  `a38d7b73` (Finding 12 fixed, plus three further real defects in the newly opt-in TA path), and the
  DEPRECATED/DEFERRED classes — is archived in [`session/history.md`](history.md) → *Activity log — 2026-08*.
  **PR-1 residuals still live:** (a) review docs `planning/ta-anchor-refactor-v2-code-review.md` +
  `ta-anchor-refactor-review.md` Part 3/Round 2 are **committed `fe372ce8`** (1237 insertions, incl.
  the definitive push-ready APPROVE section; the sole-copy hazard is **gone** — no worktree-reset
  warning needed), and remain **`Status: DRAFT` pending Dean's FINAL call**; (b) goldens **#1513 is a no-op** (its content rode
  #1516's squash; diff vs `main` is empty) needing only a close call — GitHub write, Dean's;
  (c) superseded `ta-anchor-refactor@34055d77` unpushed, for `git boidem` at leisure.
  **PR-2 = [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) — OPEN, PUSHED,
  FULLY GREEN. Nothing blocked, nothing outstanding to push.** Tip **`14a5d6cc`**, **28 commits** on
  `main@a6b39809`; local ≡ origin ≡ PR head. `MERGEABLE` / `REVIEW_REQUIRED` — no *external* review
  submitted yet; internal review is complete and clean (Findings **76/77/78**). CI all pass — `gate`,
  `DCO`, `signed-commits`, `lint-and-test`, `kustomize-build`, `check-code-changes`, `e2e-tests-full`,
  `e2e-tests-smoke`; all 28 commits DCO- **and** crypto-signed.
  **Every previously-open decision is closed:** `AD8` (b) placement → **in this PR**, landed as `C12`
  (`4e5bbf12`, pre-rebase `136a214a`), reviewed defect-free (Finding 77); `ceil`/`floor` → **retracted,
  never a fork** (`1cca5563`); the §4a commit-message reword → **executed** during the rebase; the plan
  freeze → done; the rebase onto `main` → reviewed clean (Finding 78) and independently re-verified for
  dropped hunks (none).
  **No planner is standing by — deliberate, not abandonment;** the thread is fully resumable from its plan
  doc alone. **Live forward work, all released, none blocking merge:** `B2` (a discriminating spec for
  `fairShareRolePick`'s per-role budget) is **UNCLAIMED** — recommended as its own small test-only PR after
  #1523 merges; it pins existing-correct-but-under-tested behavior rather than fixing a defect.
  **Dean's, none blocking merge:** (a) two PR-*body* claims run ahead of the code — "partial proactive
  from-zero admission" is **built-not-enabled** (C11 (D-a) deferred), and the body omits that regime (i),
  the freeze, survives (`C12` closes only the drain); (b) **PR-2's 0.9 inclusion — open by design, his call
  after merge**; (c) requesting an external review on #1523.
  **⚠️ Armed footguns, carry verbatim:** (1) #1523 shows a **stale `github-actions` comment "Unsigned
  commits detected!"** — posted 9 s after the PR opened against the pre-re-sign push; the bot never
  retracts and `signed-commits` **passes**. Do not read it as a live failure and do not re-sign.
  (2) **Do NOT record PR-2 as in-or-out of 0.9** — the tag-is-freeze-marker /
  `release-0.9`-branch-is-actual-content distinction was about **PR-1**. (3) Plan **§1.1.0's ledger SHAs
  are pre-rebase and no longer resolve**, kept deliberately as history. (4) **`AD8` (b)'s "third site" is
  not a gap** — it is reached via the same abstain predicate at `votesFromTotalDemand`; do not schedule it.
  **State:** [`session/status/planner-ta-anchor-pr2.md`](status/planner-ta-anchor-pr2.md) (**CLOSED** —
  carries the handoff inventory + footgun list) · Type 3
  [`ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md) § *Where the branch
  actually is* + § *Open items and next steps* (**claim from that owner table**) · review doc
  `planning/ta-anchor-dynamic-refresh-review.md` Findings 76/77/78 · Type 1
  [`combined-analyzer-optimizer-design.md`](../planning/combined-analyzer-optimizer-design.md) FINAL
  @ `8c2a9b04` + Addendum **Rev 7 @ `43f20c65`** (governs where they overlap).
- **2026-08-07 — autoscaling-viz: real-trace toolchain built, MIGRATED to its own `autoscaling-viz`
  branch/worktree.** *WIP — no session running; resumable from its plan.* Four-command chain; 12 PASS / 4 FAIL on our 2026-08-03 staircase
  run, capacity model within **0.6%** of the observed ceiling with zero free parameters. All four FAILs
  collapse to one run-design change (hold at saturation, then step down with requests in flight).
  Panel 4 deferred by Dean. ⚠️ The preserve copy `~/viz-migration-preserve-20260807` is the **only**
  copy of `per_request_head.json` outside the worktree — do not delete yet. State + cold resume:
  `autoscaling-viz/real-trace-viz-plan.md` **in that worktree** (the old `scratch/autoscaling-viz/`
  paths are dead by design). No PR, not headed upstream.
- **2026-08-08 — autoscaling-viz: simulation driven from a real benchmark run; calibration gate PASSES
  both arms.** *Live.* C1 `run_inputs.py` + C2 `sim_from_run.py` landed; the WVA decision rule verified
  87/87; nothing tuned except the ITL line, fit once before any comparison. **Owed by Dean:** approval
  for the `report.py`/`run.py` out-dir edits that C5 needs, and the four tolerance numbers
  (15% / 15% / 1-replica / 1% queue share) — he resolved the *criterion*, not the numbers. ⚠️ The 4th
  gate criterion was replaced *after* it had failed (his call) and the original is deliberately retained
  and still evaluated — do not "clean it up". State:
  `autoscaling-viz/planning/sim-from-benchmark-plan.md` + `real-trace/ladder-20260807/C2-GATE-REPORT.md`.
- **2026-08-10 — pokprod benchmark: guard tooling + scenario matrix; autoscaling confirmed on the
  PR-2 image; overnight campaign complete, GPUs freed.** *WIP.* Ten local commits on `benchmark`
  (DCO-signed, nothing pushed). Built the env-guard contract Dean specified — a named `X.env`
  carrying `KUBE_CONTEXT`, verified against the live context, guarding the **10 destructive**
  targets only, `UNSAFE=confirm|once|silent` escape hatch, `make benchmark-init` wizard.
  `benchmark-apply-images` closes a real gap (image pin previously reached the cluster only via
  standup); verified working. **Autoscaling confirmed end-to-end on `ta-0.9-anchor-pr2-20260809`:**
  controller scaled 1→2→3 replicas under generated load. Three previously-unknown harness blockers
  found and fixed, each of which had been blocking *all* load generation (wrong workload-selection
  var, missing PyYAML on system `python3`, a substitution-token ordering bug). Cluster used
  **overnight with Dean's explicit approval** (including the un-pause), GPUs freed at the end per
  his instruction; **campaign stopped early** ("putting the laptop to sleep") but all 7 cells have
  data, 156 snapshots, every cell 100% hydrated (3 recovered offline from saved logs).
  **Four results, one retracted:**
  1. **RETRACTED — do not cite.** An initial reading ("saturation cannot be disabled on PR-2 — PR-2
     does not fix it") was **wrong**: Dean corrected it — disabling saturation was never meant to
     stop it computing/logging, only to stop it voting, and the code does exactly that
     (`saturation/engine_v2.go:147-157`, `satVotes` — verified in `main`). Counting
     `analyzer-result` log lines cannot answer that question. The **`saturation:{enabled:false}`
     silent-no-op backlog item is unaffected — left exactly as it was**, and `enabled:false` is a
     different mechanism from list-omission.
  2. **The dwell limit cycle is analyzer-independent** (HIGH confidence, strengthened by the
     retraction — the matrix is now a genuine 3-configuration comparison, not 2): both dwell
     configs hit the replica cap (10) twice, no staircase config exceeded 9. Tracks the workload,
     not the analyzer configuration — consistent with §18 and §7.6.
  3. **`prc` collapse is a third, separate variable** (MEDIUM): present in 2 of 5 non-dwell cells
     including one that did *not* limit-cycle, absent from others that did — so it is **not** the
     limit-cycle's cause, reproducing §18's own "mechanism, not tuning" diagnosis.
  4. **The replica target oscillates while `rc = 0` and util ≈ 0.2** — most interesting open
     thread, points at the decision/optimizer path rather than the analyzer. Not investigated.
  **Weakest link, carry verbatim:** one run per cell, no repeats, no noise floor; the image A/B
  additionally started from different replica counts (1 vs 2) — **mechanism observations, not
  benchmark results.** Also found: a harness reporting bug (an unconditional `if errors:` fails a
  step on a log line already labelled non-fatal, so `run_metadata.yaml` is never written) —
  candidate for the fork/upstream list. `m-ta-dwell` ran only ~10 of ~40 min; a clean re-run would
  complete the matrix.
  ⚠️ **Armed footguns, carry verbatim:** (1) **the ScaledObject is PAUSED at 0** (GPUs freed and
  verified twice) — **un-pausing is a mandatory first step of the next run**, or the trace is flat
  and reads as a legitimate no-scaling result; (2) **restart the controller between runs/cells** —
  in-memory capacity history makes run N a function of run N-1's load; (3) the PR-2 image
  (`ta-0.9-anchor-pr2-20260809`) is still **unverified against the parser** independent of this
  campaign's own results — short run → confirm fields populate → only then a long run;
  (4) `session-notes/local/` is **gitignored** — nothing there is preserved.
  State: [`session/status/benchmark.md`](status/benchmark.md) **§20** (live state; §18 = dwell
  findings, §19 = tooling round) — sole authority, coder-maintained. Planner-side items in
  `plan__benchmark-overnight-campaign.md`, `plan__benchmark-env-guard-design.md`, and the now-retraction
  notice `plan__benchmark-sat-disable-still-broken-on-pr2.md`.
- **2026-08-08 — pokprod benchmark: the Type 3 is now a tooling plan as well as a test plan.**
  *Blocked on Dean.* §7.6 is the substantive finding: steady-state KV under a tracking controller is a
  *controlled* variable, so §7.4.1's dwell cannot be reached by raising the offered rate — it is a
  configuration decision, not a workload one. Guards-only fork split now contractual; the `.env`
  contract is fail-closed and kube-context-keyed; the KEDA arm is present but unrunnable (3 verified
  blockers). **Owed by Dean:** (a) saturation-alone-uncapped *(recommended by coder and planner)* vs
  (b) a deliberate replica cap — or defer both behind the already-staged quantization-sawtooth run; and
  **T9**, applying the gateway access-log follower personally. Nothing launched, no cluster contact,
  nothing pushed. State: `planning/ta-pokprod-testing-plan.md` §7.6.1 (cold resume) + §9.1 (T1–T11 owners).
- **2026-08-03 — sat_v2 cannot be disabled via config (F1 gap).** *Blocked on Dean.* Not a regression:
  `saturation/engine_v2.go` unconditionally prepends the saturation result and `effectiveEnabled` only
  skips it by name, so `saturation:{enabled:false}` is a silent no-op. The lifecycle plan's Commit-2c
  "zero-signal" design is **REJECTED** ("risky hack", warnings committed `663a9624`); a real fix needs
  the F1 pre-analysis extraction so `VariantCapacities` is sourced independently of the saturation
  contribution. **Owed by Dean:** spawn the dedicated planner and scope it — do not start before that.
  Keep separate from the TA-lead benchmark thread, which runs TA+SAT combined and does **not** need
  sat_v2 disabled. State: `planning/wva-analyzer-lifecycle-plan.md` +
  [`multi-analyzer-design.md`](../planning/multi-analyzer-design.md):506-511.
- **2026-07-15 — optimizer-pd-role-ceiling: code + all 10 tests landed (`0c33a3eb`), gates green.**
  *WIP — no session running; resumable from its plan. Untouched ~3½ weeks.* ⚠️ Dev-guide edits the planner made directly are still
  **UNCOMMITTED** in the worktree (`M multi-analyzer-pipeline.md`). The active thread is Dean's
  clean-design effort: 2 Phase-2 framing questions unanswered, Phase 3 (verify code vs the clean model)
  not started, and a suspected real bug flagged — anticipated supply sits in the denominator rather than
  counting toward achieved. Nothing pushed. State: `planning/optimizer-pd-role-ceiling-plan.md` +
  [`optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) § Resume.
**Recently landed (1-liners; fuller entries in [`session/history.md`](history.md) → *Activity log*):**

- 2026-07-30 — `ta-testing` refreshed → `6bfb73e1`; signed tag `ta-0.9-test-20260730` + quay image `:ta-0.9` (registry digest `sha256:80dec0e9728f…`) both pushed (executes the §4.1 refresh trigger).
- 2026-07-31 — CURRENT.md / history.md restructuring committed on `plans` (landed history extracted to the archive).
- 2026-08-07 — `ta-itl-demand-test-gaps` **PR #1511 MERGED** 17:40:56Z (merge `8b3663ed` on `main`; test-only, 5 commits; landed via the background `main`-sync watcher). Residual: `checkVariantGPSMismatch` coverage still deferred (see § Issues to Open).

**Older / historical:** the compressed activity tail (TA 0.9 era back through 2026-05) lives in [`session/history.md`](history.md) → *Activity log* sections — fetch one section at a time per that file's Reading Protocol, do not inline here. Most recent landmark: **TA 0.9 fully landed (all six PRs #1478/#1479/#1480/#1481/#1502/#1503) 2026-07-30, `main` tip `6bfb73e1`.**

---

## PR Status — open / active only

Landed & closed rows (TA 0.9 stack, TA3 & earlier missions, upstream reviews & proposals) are
archived in [`session/history.md`](history.md) → *PR Status* sections. Only in-flight / actionable
rows stay here.

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| wva-analyzer-lifecycle | — | **PLAN — PARTIALLY REJECTED / re-scoping.** Config-driven analyzer activation + ManagedAnalyzer lifecycle. Splits into **Half A** (config-driven lifecycle + live-set refactor — Commits 1/3/4/5; ~1–2 days; `effectiveEnabled`/Commit 3g already on `main`; main risk = `NewEngine` ripple vs in-flight #1501) and **Half B** (genuinely disabling saturation — Commit 2c **REJECTED by Dean 2026-07-31**: "zero-signal" is a risky hack; needs F1 "pre-analysis extraction" to solve `VariantCapacities` sourcing; unscoped). Dean spawning a **separate planner** to scope the real sat_v2-disable fix; awaiting his call: carve Half-A-only vs scope Half-B/F1 vs hold. Warnings added to plan (`663a9624`). Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| ta-anchor-goldens | [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) | **OPEN but now a NO-OP — needs only a close call (Dean's; GitHub write).** Characterization "golden" gate (test-only, +409/−0, 1 file: `internal/engines/pipeline/optimizer_characterization_test.go`) freezing the saturation-only optimizer decision SET keyed by VariantName; was the land-first ship gate for the anchor refactor. **Its content is already in `main`:** PR-1 #1516 was rebased onto this branch's tip before opening, and #1516's **squash** merge (`57f3fe64`, 2026-08-07 17:48:05Z) therefore landed the file — `git diff 57f3fe64 a2f49ccf -- <that file>` is **empty**, so the PR has nothing left to contribute and its purpose was served. No code action; the coder must still **NOT** rewrite the goldens commits. Head `ta-anchor-goldens@a2f49ccf`, base `upstream/main@9906dac5`, reviewer ev-shindin, `origin/ta-anchor-goldens` pushed. Internal review FINAL (Finding 1 fixed; Finding 2 = `withSatEntry`-stability note, carried into PR-1 and landed there). Plan: [`planning/ta-anchor-goldens-plan.md`](../planning/ta-anchor-goldens-plan.md); review [`planning/ta-anchor-goldens-review.md`](../planning/ta-anchor-goldens-review.md). | `a2f49ccf` |
| ta-anchor-dynamic-refresh | [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) | **OPEN, pushed, CI all-green.** Tip `14a5d6cc`, 28 commits on `main@a6b39809`; local ≡ origin ≡ PR head. `MERGEABLE` / `REVIEW_REQUIRED` — internal review clean (Findings 76/77/78), **no external review yet**. All decisions closed (`AD8` (b) → `C12`; `ceil`/`floor` retracted; §4a reword executed; rebase clean). Open, none blocking merge: `B2` (**UNCLAIMED**), and Dean's PR-body accuracy + 0.9 call + review request. ⚠️ The **"Unsigned commits detected!"** bot comment is stale — `signed-commits` passes. Detail: [`session/status/planner-ta-anchor-pr2.md`](status/planner-ta-anchor-pr2.md) (CLOSED). | `14a5d6cc` |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |

---

## Blocked on

- **Pokprod TA benchmark — first live controlled standup** is blocked on **Dean's explicit go-ahead**
  (Phase-4 Step 0). All prep is done (dry-run, hazard analysis, fork patches, Phase-3 namespace setup);
  also awaiting Dean's OK on 3 fork-only pushes (`6505de62`, the 3 presence-gate patches) and the
  upstream-patch-proposal decision. See § Benchmark + `session/status/benchmark.md`.
- **The staged pokprod dwell run** is blocked on, in order: Dean's §7.6 (a)/(b) answer (or an
  explicit deferral), Dean applying the gateway access-log follower (§9.1 **T9** — the coder's
  permission classifier blocks the `kubectl apply`, and without it every per-request trace is a bet
  against log rotation), the coder's four preconditions (§7.6.1), and finally Dean's run approval.

## Next steps

- **TA 0.9 — LANDED (all six PRs MERGED 2026-07-30, `main` tip `6bfb73e1`; test-branch + `:ta-0.9`
  image refresh EXECUTED).** Detail in [`session/history.md`](history.md). **Live follow-ups, all
  Dean's:** (1) epics #1492/#1493/#1494 + adopted #1005 — update or close now every PR is merged;
  (2) PR #1501 ask-#1 watch (see its PR Status row); (3) governance retrospective open Q →
  [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md); (4) cleanup — old tag
  `ta-0.9-test-20260728`, stale `origin/ta-testing`@`db530eed`, local `ta-model-level-demand`
  worktree (non-urgent). The 3 optional test gaps on F are done (#1511); only the deferred
  `checkVariantGPSMismatch` coverage remains, in § Issues to Open.
- **TA 0.9 release notes / Highlights — ⏰ CODE FREEZE REACHED (2026-08-07). This is the freeze, NOT
  the final cut — critical fixes can still be pushed (Dean, 2026-08-07).** Verified state: tag
  **`v0.9.0` exists on upstream** (lightweight, → commit **`aadaa596`** = #1509 "fix(crd): restart
  when KEDA or LWS CRDs are installed after startup"), and asm582's release-prep
  **PR [#1522](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1522)
  MERGED** 18:07:18Z (`d5d58640`, pins `config/base/manager/kustomization.yaml`
  `newTag: main → v0.9.0`) — but **no GitHub Release is published yet** (latest is still v0.8.0), and
  there is **no `release-0.9` branch** (release-0.6/0.7/0.8 exist). **A lightweight tag can be
  re-pointed, and v0.8.0 ran rc2→rc5 before its final tag** — so neither the tag point nor the 0.9.0
  content set is settled. What the freeze does settle is the **"held until code freeze" trigger for
  the hand-written `## Highlights` block: that work is now unblocked.** Mechanism + drafts in
  [`planning/ta-0.9-release-notes.md`](../planning/ta-0.9-release-notes.md): the ` ```release-note ``` `
  PR block is NOT auto-harvested (no `.github/release.yml`); GitHub auto-notes derive from PR
  *titles* in `v0.8.0..v0.9.0`; Highlights is the only editorial lever. Do NOT create an in-repo
  `docs/CHANGELOG-v0.9.0.md`. Slack epics + Highlights notes already POSTED by Dean 2026-07-29.
  Design-docs PR (item 5) still DEFERRED post-code-freeze.
  **⚠️ Open question for Highlights, NOT a settled exclusion — three commits sit on `main` *after* the
  current tag point:** `8b3663ed` (#1511, test-only), **`57f3fe64` (#1516, the anchor refactor PR-1)**,
  and `d5d58640` (#1522's own prep commit). If the tag stays at `aadaa596` they are 0.10.0 material; if
  it is re-pointed (or an rc sequence runs, as in 0.8.0) they are in 0.9.0. **Do not describe #1516 as
  in-or-out of 0.9.0 until the final tag point is known** — check `git ls-remote --tags upstream` at
  writing time rather than trusting this line. Corollary of the same ordering: the tagged tree at
  `aadaa596` does **not** contain #1522's own `v0.9.0` image pin, which is itself a reason the tag is
  likely still to move. Raising any of this upstream is Dean's call; no GitHub write made.
- **Toolchain moved on `main` (2026-08-07, post-freeze) — affects every branch that rebases.**
  PR [#1512](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1512) (`a6b39809`, Wen Zhou)
  bumps **go.mod `go 1.25.0 → 1.26.0`** and **`GOLANGCI_LINT_VERSION v2.8.0 → v2.10.0`** (Makefile + the
  `ci-pr-checks` / `ci-e2e-openshift` lint action + Dockerfile + CONTRIBUTING + `docs/developer-guide/development.md`
  + `.claude/agents/go-reuse-checker.md`; 8 files, +9/−9). Two practical consequences: (1) **a green
  `make lint` from before this commit does not carry forward** — 2.8→2.10 is two minor releases of linter
  changes, so any branch whose gates were verified under 2.8.0 (now only `optimizer-pd-role-ceiling` @ `0c33a3eb` — **PR-2 is clear: #1523's
  `lint-and-test` passes under 2.10.0**) must re-run `make lint` after rebasing, and
  new findings there are the bump's, not a regression; (2) **no stale-binary hazard** — the Makefile rule is
  version-keyed (`bin/golangci-lint-$(GOLANGCI_LINT_VERSION)` + `ln -sf`), so `make lint` fetches 2.10.0 and
  re-points the symlink on its own. Local `go` is **already 1.26.0**, so there is no toolchain gap to close.
  Landing after the v0.9.0 tag point is consistent with the freeze still accepting fixes.
- **Pokprod benchmark tooling — two Dean-owned items (§9.1 of `ta-pokprod-testing-plan.md`).**
  **T9**: apply the gateway access-log follower (Dean personally — the coder's permission classifier
  blocks the `kubectl apply`). **T10**: file upstream llm-d-benchmark issues for the two guards-only-fork
  violators (later, after §2b's migration isolates them).
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
- **anchor-refactor mission — forward work only.** State and detail live in § Recent activity and
  the Type 3's owner table; not restated here. **Dean's, none blocking merge:** (a) request an
  **external review on #1523** (`REVIEW_REQUIRED`); (b) two PR-*body* claims run ahead of the code —
  "partial proactive from-zero admission" is built-not-enabled, and the body omits that regime (i), the
  freeze, survives; (c) **PR-2's 0.9 inclusion — open by design, decide after merge**; (d) close goldens
  **#1513** (no-op — GitHub write); (e) `git boidem` the superseded `ta-anchor-refactor@34055d77`
  (unpushed); (f) file, or decline, the two GitHub issues — QM multi-analyzer-contract work, and the
  sat-v2 zero-replica `Cost=0` bug (`AD7`/`N5`); (g) mark the PR-1 review docs **FINAL** — the
  reviewer's commit half is **DONE** (`fe372ce8`), both remain `Status: DRAFT` and only Dean's FINAL
  call is left. **Unclaimed, for a new planner:** `B2` (discriminating
  `fairShareRolePick` spec) as its own small test-only PR after #1523 merges; re-validating
  `optimizer-pd-role-ceiling` against the landed refactor
  (`plan__optimizer-pd-role-ceiling-revalidate-against-pr2.md`); and
  `plan__ta-anchor-dataflow-map-pr1-delta.md`, still open and deferred by Dean — **not sync's to consume**.
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
**The Type 3 now also carries a tooling track** (§9.1, T1–T11 with owners — T9/T10 are Dean's, see
§ Next steps) and a cold-resume block for the dwell-run redesign (§7.6.1); the methodology-pivot text
above stays accurate.

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
- Distinguish unavailable metric from genuine zero in `ReplicaMetrics` (`*float64` nil semantics for 3 throughput fields + sanity update) — **FILED as [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264)** (prerequisite: #1250 Bug A fix; follow-up after #1250 merges)
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10** — **this is also the re-enable path for the QM optimize path DEFERRED by PR-1 #1516 C3** (`optimizeQueueingModel`/`runQueueingModelAnalysis`/`buildQMConfig` stay in-tree behind a blank reference; re-enabling = restoring the dispatch). No separate backlog item.
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- Engine SchedulerQueue wiring — ✅ landed with #1246 merge (2026-06-10, `09e1c386`).

Infra / misc (no design-doc home; file as separate issues):

- **TA forward plan** — 26 internal issues + 5 deferred features (correctness, observability, tests, architecture, docs): [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md).
  - **Deferred features (Group 0)** — code removed during #1250 dev cycle whose design intent is preserved: D-1 ITL knowledge store (historical A,B per variant, warm-up skip), D-2 GPS-mismatch SC gate, D-3 EPP-absent SC gate, D-4 FreshnessStatus staleness gate (dead end-to-end), D-5 `has*` throughput sentinels (nil-vs-zero for 3 fields). None are deprecated — all return in later PRs (D-2/D-3 via #1261, D-4 via I-6, D-5 via #1264, D-1 via I-18).
  - Key issues: collector key unification (I-1, P0 latent bug), gate observability (I-5, P0), dev guide fixes (I-21–23, P0), per-analyzer status return (I-17→#1261), effectiveEnabled (I-16→`planning/PR1266-fixup-effectiveEnabled.md`).
- **`checkVariantGPSMismatch` test coverage (deferred, no owner)** — split out of #1511 (4 earlier skip guards to satisfy, no existing test block, diagnostic-only). **Survives #1511's merge — still open.** Separate future test task; recorded in the `ta-itl-demand-test-gaps-plan.md` Commit-4 §. Create a branch when assigned.
- **EPP system-wide `k_sat` unification (NEW 2026-08-07, surfaced by PR-2 C10)** — PR-2 makes TA resolve `k_sat` from the saturation analyzer's `KvCacheThreshold` (0.80) instead of its own hard-coded `0.85`, but the *system-wide* value the EPP uses is still a third, unrelated copy. The existing `TODO: unify with the system-wide k_sat used by the EPP` moves onto `resolveKSat` as the single place to fix. File at Dean's direction.
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); see forward plan I-8.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- **`runRegisteredAnalyzers` deletion** — dead-code in `engine_v2.go`; not removed in #1266. Standalone cleanup PR. Plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.
- **Align the informativeness predicate with the RC that reaches the optimizer (Type-1 design question, later round — not PR-2)** — `ResultIsInformative` scans only per-variant `Reason`, while the `RequiredCapacity` the optimizer consumes comes from `RoleCapacities` via `applyUniversalThreshold` (`saturation/engine_v2.go:476-513`), which never mentions `VariantCapacities` — so a saturation result can be non-informative while carrying a positive role RC. **Latent, not live** (Type-1 Addendum-1 Rev 6: the capacity store keeps saturation informative in every reachable configuration), which is why it is a design question rather than a bug to schedule. Closing it means either having informativeness consider role demand, or having the scheduler-queue term mark the variants it speaks for. Not a revival of the rejected liveness-aware-refusal option (different site — the liveness computation, not a second refusal predicate in the optimizer). File at Dean's direction.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| planner | `planning/open-items-roadmap.md` | **SCORED** (2026-06-15) | All areas scored (multi-analyzer, TA, D52/EV52). Committed `c71db32d`. See roadmap for Q1/Q2 priority list and dep graph. **Both #1250 and #1266 now merged — file Q1+Q2 items as GitHub issues.** |
| planner | `session/handoffs/plan__ta-anchor-doc-taxonomy-findings.md` | **OPEN** (`.WIP`) | Five doc-taxonomy findings for Dean to accept / reject / defer — **not** resolved by the Type-3 refresh. Deliberately still open. **Not sync's to consume.** |
| planner | `session/handoffs/plan__ta-anchor-dataflow-map-pr1-delta.md` | **OPEN** | Optional §9 addition to `multi-analyzer-dataflow-map.md`, deferred by Dean; partly overtaken — the map's §9 findings now live in the Type 1's § findings, so any delta is about the map's own currency. **Not sync's to consume.** |
