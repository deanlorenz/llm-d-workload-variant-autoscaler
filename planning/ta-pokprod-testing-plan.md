# TA on pokprod — Testing Plan (Type 3, internal)

**Status:** DRAFT — awaiting Dean review before any execution.
**Author role:** plan-agent. **Scope:** internal testing/ops; nothing here is upstream-bound.
**Created:** 2026-07-28.

> Hard constraints for this mission (Dean, 2026-07-28):
> - **Never push anything to `upstream`.** Runbook, results, benchmark harness → Dean's fork only.
> - **Strict separation of code-under-test from benchmark artifacts**, even locally (see § Architecture).
> - Runbook + `results/` are **not code** — they live only on Dean's `benchmark` branch/fork.
> - Ofer must be able to consume **code only** (image / tag / branch) and test it in his own framework.
> - No GH posting by the plan-agent. Execution steps below are for a coder or Dean, not the planner.

---

## Table of contents

- [1. Where we are (findings)](#1-where-we-are-findings) — L48:99
- [2. Architecture — two-tier separation](#2-architecture--two-tier-separation) — L101:333
  - 2a. pokprod shared-cluster safety invariants — L133:167
  - 2b. Two-fork contract — what lives where — L170:206
  - **2b-bis. Artifact tree — one root, results persisted in git (2026-08-10) — L209:277**
  - 2c. Configuration contract — fail-closed, per kube context — L280:332
- [3. Phase 0 — Preserve (zero-loss)](#3-phase-0--preserve-zero-loss) — L335:362
- [4. Phase 1 — Code-under-test branch + image](#4-phase-1--code-under-test-branch--image) — L365:503
  - 4.1 Refresh trigger — ARMED 2026-07-30 — L425:453
  - 4.2 Tier-A image currency — three tags exist — L456:503
- [5. Phase 2 — Fresh benchmark branch + KEDA harness (blend #1435, parametrized)](#5-phase-2--fresh-benchmark-branch--keda-harness-blend-1435-parametrized) — L506:721
  - 5.5 Branch / worktree wiring & runbook (item 4 = the doc plan) — L617:662
  - 5.7 The KEDA arm is present but unrunnable — L680:721
- [6. Phase 3 — Clean stale pokprod + controlled-setup methodology](#6-phase-3--clean-stale-pokprod--controlled-setup-methodology) — L724:935
- [7. Phase 4 — Scenarios + small e2e](#7-phase-4--scenarios--small-e2e) — L939:1498
  - 7.4 Scenario gaps from the ladder-run cross-check — L1241:1315
  - **7.4.4 Workload coverage matrix + theory/simulation/real baseline (2026-08-11) — L1317:1350**
  - 7.5 Autoscaler-arm matrix + A/B hygiene — L1352:1380
  - **7.6 The mid-band dwell is a controller-configuration lever, not a workload lever — L1383:1498**
  - 7.6.1 Cold-resume state (2026-08-08) — L1467:1498
- [8. Decisions (all resolved 2026-07-28)](#8-decisions-all-resolved-2026-07-28) — L1500:1523
- [9. Execution ownership & scope](#9-execution-ownership--scope) — L1525:end
  - 9.1 Tooling track (T1–T11) — L1556:end

> **TOC maintenance:** `scripts/toc-refresh.sh` **does not work on this file** — it requires a
> literal `^## TOC` heading and this doc uses `## Table of contents`, so the script exits at its
> heading probe without saying so. Ranges here are hand-maintained; re-derive with
> `grep -n '^## \|^### '` and end each range 2 lines before the next same-or-higher heading.

---

## 1. Where we are (findings)

State captured 2026-07-28, read-only:

- **The `benchmark` worktree/branch is stale.** Forked from old main `526ce851` (~Jun 11);
  **105 commits behind** current main. Its ~35 commits over that base are TA/multi-analyzer
  **code that has since merged into main** (#1250, #1225/#1228/#1246/#1266, …) — duplicate
  history, i.e. "past noise", not work to preserve.
- **Only unpreserved work is untracked** (2026-06-15 session):
  `docs/two-variant-wva-ta3-runbook.md` (28 KB), `docs/guidellm-harness-notes.md` (9 KB),
  `results/` (3 dirs: `ta-scaleup-retest`, `armB-satv2-only`, `hftoken-verify`), and local
  patches in the embedded `llm-d-benchmark/` clone.
- **Main compiles now; CURRENT.md is stale on this.** #1477 was **CLOSED**; the compile fix
  landed as **#1483 (`fafbc4dd`)**. Upstream main = `31fd0f84`; **#1470 and #1452 both MERGED**
  (CURRENT.md still lists them "reviewed, not merged"). Local `Main` is one behind (`ef28744b`).
- **TA 0.9 PR status (as of 2026-07-28, re-verified):** **A #1478 (devguide) and A′ #1479
  (registration-safety) are MERGED** into upstream main today (`827c8542`, `11d70a8a`). Only
  **C #1480 (model-level-demand)** and **D #1481 (veto-liveness)** remain **OPEN**. A
  forward-rebase already ran (the open branches' merge-base with upstream/main is #1478's
  `827c8542`; branches clean, not mid-rebase). **Consequence:** the A′→D shared-`engine_v2.go`
  dependency **dissolves** — A′ is now in main, so rebasing D onto current main resolves it. The
  integration is now **main (already has A + A′) + C + D** = two PRs to stack, not four.
- **Ofer = `biranofer`.** His code fork is **`biranofer/workload-variant-autoscaler`** (note:
  no `llm-d-` prefix), branch **`feat/two-variant-keda`** = PR **#1435** (two-variant benchmark
  VA+HPA → KEDA ScaledObjects). His benchmark harness is **`biranofer/llm-d-benchmark`**, branch
  **`feat/multi-variant-benchmark`** (unmerged; PR #1451 closed; ClusterRole-naming fix #1673
  merged 2026-07-24). **Not everything is merged — his fork is where he runs current tests.**
- **The integration seam** (his `two-variant-wva.yaml` guide):
  `repository: quay.io/deanlorenz/llm-d-workload-variant-autoscaler`, `tag: ta3`. The harness
  consumes the WVA controller **purely by image reference** — this is the plug-in point for
  Dean's code-under-test.
- **Runbook's own conclusion (§12):** the earlier "TA drives scaling" claim was **retracted** —
  controlled Arm-B showed **sat_v2 + cost-aware optimizer** was the driver; TA on-vs-off made no
  decision difference. **The real open goal (§14) is still: a clean test where TA *itself*
  drives a decision sat_v2 would not.** This has never been observed.

**Update 2026-08-08 — this is a tooling plan as well as a test plan (Dean).** The deliverable is
not only "run TA on pokprod" but a **shareable benchmark tooling kit** Ofer can consume by checking
out a branch and adding a worktree. Findings since the 07-28 capture:

- **The harness is as-built, not hypothetical.** `hack/benchmark/` carries **33 files, 22 of them
  branch-added** (scripts, scenario guides, workload profiles, preflight, gateway log-follower).
  The branch is **9 commits ahead of `origin/benchmark`** with several dirty paths — all local,
  nothing pushed.
- **Two runs of record, both single-variant:** the 2026-08-03 staircase and the 2026-08-07 8-stage
  ladder. **Two-variant is built but has never been run.** Analysis lives on the branch in
  `session-notes/status/benchmark.md` §17 (§17.8 = consolidated open items).
- **Tooling and guards belong in two different forks** — §2b. This was implicit until 2026-08-07
  and produced drift in both directions.
- **The KEDA arm has never run and cannot run as configured** — three verified blockers in §5.7.

---

## 2. Architecture — two-tier separation

The governing principle from Dean: the code being tested and the benchmark that tests it are
**two independent things**, kept apart even locally. Ofer pulls the first, never the second.

**Tier A — Code-under-test (reproducible, clean, sharable via Dean's fork):**
- A clean integration branch = **current main (already contains A #1478 + A′ #1479) + C #1480
  + D #1481**. Lives in its **own dedicated code worktree** (e.g. `ta-testing`), never the
  benchmark worktree and never a PR worktree.
- **Fork-only, never upstream.** Branch + tag pushed to **origin (`deanlorenz` fork)**; image to
  **`quay.io/deanlorenz`**. Ofer has fork access → consumes by branch / tag / image. This is a
  test-only integration; it is **never opened as an upstream PR** (C and D keep their own PR life).
- Produces two reproducible artifacts: a **git tag** (immutable checkout point — the answer to
  "where did we get the code") and a **container image**
  `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:<tag>`. **A rebuild is required** — the
  old `:ta3` image predates all of TA3-merge, multi-analyzer, sat-v2, and the 0.9 work.
- **Changes only flow in from the PR worktrees** (`ta-veto-liveness`, `ta-model-level-demand`)
  or new yet-to-merge PR branches — never hand-edited in the benchmark tree. If a fix is needed
  mid-test, it is made in the owning PR worktree, re-integrated, re-tagged, re-imaged.
- Ofer can also cross-check against his own `feat/two-variant-keda`.

**Tier B — Benchmark harness (Dean's, fork-only, not code):**
- A **fresh `benchmark` branch** (WVA worktree) + the `llm-d-benchmark` guide framework.
- Adopts **Ofer's KEDA / guide-based path**: his `feat/multi-variant-benchmark` two-variant-wva
  guide, with `tag:` pointed at the Tier-A image.
- **Runbook + `results/` live here only**, never pushed upstream.
- This tree *references* the Tier-A image; it does **not** contain the WVA source under test as
  its build source. (The WVA worktree still has source on disk, but the deployed controller is
  the Tier-A image, not a build of the benchmark branch.)

Seam between tiers = the image `repository:tag` in the guide. That is the *only* coupling.

### 2a. pokprod shared-cluster safety invariants (2026-07-28, per Dean)

pokprod is a **shared OpenShift cluster** (not pure k8s — expect OCP-specific objects:
`Route`, `ServiceMonitor`/`PodMonitor` with TLS, SCCs, `oc` not just `kubectl`). Dean **and Ofer
both hold admin**, so an unscoped or defaulted command can silently land in the wrong namespace or
mutate cluster-global state. These invariants bind every phase and must be restated in the runbook:

- **Operate only in the target namespace set for this benchmarking config** (currently
  `dhl-wva-209`, per Phase 3) — **CORRECTED 2026-08-11 (D-15):** not "Dean's namespace." The namespace
  is a property of the `.env`/config a run is invoked with, not of who is running it. Every
  `oc`/harness/helm/kustomize invocation carries an explicit `-n <target namespace>`; never rely on the
  current-context namespace. When a new context is created and a new namespace is established, it must
  be **confirmed explicitly with the user** before use — no context silently inherits or infers a
  namespace. All subsequent operations for that context are confined to the confirmed namespace.
- **Every environment value comes from the explicit `.env`** — namespace, model, instance, image,
  accelerator, URLs. Never a harness default or inferred value: a default could resolve into another
  user's namespace or a cluster-global object. **CORRECTED (D-16):** this is why *any* invocation of the
  benchmark Makefile targets uses a fully-populated `.env` — not specific to one operator. Anyone using
  the targets should be structurally prevented from landing on the wrong namespace by omission, not
  relying on personal discipline.
- **Any teardown on a shared cluster requires the operator's explicit approval for that specific
  action** — no teardown/delete is initiated or directed by the plan-agent, and none runs without that
  sign-off. Never run a delete/teardown without an explicit namespace arg. **CORRECTED (D-17):** this
  invariant holds for **anyone** using the benchmark targets, not a named person, and it is scoped to
  the namespace explicitly set for benchmarking — never touch anything outside it, especially for
  teardown.
- **Never change any cluster-global / out-of-namespace setting** — Prometheus/monitoring stack config,
  router control plane, routing rules, HTTP/gateway settings, or anything cluster-scoped. Dean *has*
  the admin rights to do this by mistake; the guard is procedural. **Before applying any kustomize or
  helm manifest, verify it does not create or mutate cluster-scoped / other-namespace objects** (scan
  for `ClusterRole`/`ClusterRoleBinding`, resources without a `namespace:`, or edits to shared
  monitoring/gateway CRs); if it does, stop and surface it to Dean rather than applying.

**The safety net has three levels** (named in `preflight_shared_cluster.py`'s docstring; each is
independent, and only L2/L3 are mechanical):

| Level | Layer | Enforced by |
|---|---|---|
| **L1** | operator discipline — explicit `-n`, no teardown without approval | the human, and this section |
| **L2** | this repo's Makefile targets, scripts, and `benchmark-preflight` | WVA branch (§2c) |
| **L3** | the llm-d-benchmark fork's presence-gates on cluster-scoped standup steps | harness fork (§2b) |

**The L3 hazard is inverted from the obvious one.** A presence-gate skips because a shared object
*already exists*. Absence therefore reads as "not installed yet — go install it", so **a deleted
precondition silently converts a safe standup into a destructive one.** Worst case on the books: a
real prometheus-adapter install claiming the cluster-wide `external.metrics` APIService that KEDA
owns. This is why L3 must be *verified present in the code that will execute*, not assumed.

### 2b. Two-fork contract (Dean, 2026-08-07) — what lives where

Two forks back this mission, with **non-overlapping** contents:

| Fork | Contains | Lifetime |
|---|---|---|
| `deanlorenz/llm-d-workload-variant-autoscaler` (**WVA**) | the tools, the Makefile, `hack/`, scenarios, workload profiles, docs | **temporary measure** — expected to move upstream; Ofer clones the branch, worktrees it, or merges what he wants |
| `deanlorenz/llm-d-benchmark` (**harness**) | **guards only** — presence-gates for the cluster-scoped operations upstream's standup would otherwise perform | longer-lived; the guards are to be **opened as upstream issues later** |

**Rule:** anything in the harness fork that is not a guard belongs in WVA `hack/`. The harness fork
is what makes the tools installed on the cluster *safe*; it is not where tools live. Ofer can use it
as-is; the local clone the Makefile pulls can be nothing but the part that runs on the cluster,
since everything else is in `hack/` and pathed on the fly anyway.

**Audit against that rule (2026-08-08, read-only).** Four fork-authored commits on
`wva-ta-benchmark`:

| Commit | Touches | Verdict |
|---|---|---|
| `963bb00` | `standup/steps/step_03_workload_monitoring.py` +55/−16 | **guard ✓** — don't overwrite the shared `cluster-monitoring-config` |
| `e88b882` | `standup/steps/step_07_deploy_setup.py` +64, `standup/wva.py` +52 | **guard ✓** — presence-gate cluster-scoped gateway/RBAC |
| `7a1b478` | `llmdbenchmark/analysis/output_token_correction.py` +306, `analysis/__init__.py` +17 | **violates** — pure tooling, and it *duplicates* WVA's `correct_output_tokens.py` (88) + `completion_tokens_scan.py` (166). The clone's copy is already **modified-uncommitted**, i.e. the duplicate is actively drifting |
| `cfe6088` | `workload/profiles/guidellm/wva_sat2_short.yaml.in` (16), `workload/profiles/inference-perf/ta_calibration_probe.yaml.in` (73) | **violates** — identical filenames *and* line counts to files WVA already owns. `sync_workloads.py` exists precisely so these stay a **cache**, not commits (four untracked `workload/profiles/inference-perf/*` files are that mechanism working correctly) |

Migrating the two violators out leaves the harness fork at **2 commits / 3 files, all under
`standup/`** — which is also the shape that makes the eventual upstream issues a direct extract.

**Not a cleanup item:** `50c8da8` + `6d5ff6b` ("multi-variant / Topology B") are **Ofer's**;
`6d5ff6b` is the tip of `ofer/feat/multi-variant-benchmark`. Whether they belong under a guards-only
rule is his call, not ours.

**Verification, not trust.** `preflight_shared_cluster.py::check_fork_guards` greps the *configured
clone* for each guard symbol and registers the result as `gating=True`, so a missing guard is a
`FAIL` that increments `rep.failed` and exits non-zero. That is a **property** test. Identity comes
separately, from defaulting `BENCHMARK_REPO_URL` to Dean's fork (§2c) — under the guards-only
contract the fork carries no tooling for anyone to extend, so Ofer never needs a harness fork of his
own and there is exactly one correct value. **The default supplies the right answer; the gate
catches a wrong one.**

### 2b-bis. Artifact tree — one root, results persisted in git (Dean, 2026-08-10)

**Problem.** Benchmarking artifacts are spread across five unrelated trees, so "is this preserved?"
needs five separate answers: `hack/benchmark/` (tools, `.env`s, scenarios, workloads — tracked),
`test/benchmark/` (Go scenarios — tracked), `session-notes/` (scratch, handoffs, issues, status —
tracked **with two mid-tree ignore carve-outs**), `dean-*/` (raw run output — fully ignored), and
`docs/developer-guide/benchmark-panels/` (five PNGs from #947 — tracked but **orphaned**, see below).

**Target layout** — one root, lifecycle visible in the directory name:

```
benchmark/                        NEW tree, the single root
├── tools/ → ../hack/benchmark    SYMLINK — nothing moves (Dean: "let's not move hack/benchmark for now")
├── campaigns/<YYYYMMDD>/         curated + permanent           TRACKED
│   ├── README.md                 summary + <details> figure embeds
│   └── <cell>/panels.png, coverage.json
└── runs/$USER-<ts>-<pid>/        all machine-generated output   not tracked
```

**Decisions, all Dean's, 2026-08-10:**

1. **All results live on the `benchmark` branch** — not a separate results branch, not `plans`.
2. **`hack/benchmark/` does not move.** `benchmark/tools` is a **symlink** to it. Zero churn: no
   Makefile path edits, no script moves, no `__file__` breakage.
3. **`session-notes/campaign-runs/` → `benchmark/campaigns/`, and it becomes TRACKED** (today it is
   ignored at `.gitignore:84`). Dean: *"I don't want to gitignore the results as a whole anyway."*
   The campaign **drivers** stay at `hack/benchmark/campaign/` — those are tooling, reached via the
   symlink.
4. **`BENCHMARK_WORKSPACE` moves to `benchmark/runs/`.**

**Why (4) is load-bearing and not cosmetic.** Run output lands in `$(BENCHMARK_WORKSPACE)/$${USER}-*/`
(`Makefile:845,881,893`), and the ignore rule is the literal glob **`dean-*/`** (`.gitignore:43`).
The glob only matches *Dean's* username: **Ofer's runs land as `ofer-*/` and are not ignored at all**,
surfacing as untracked clutter in his `git status` on a fresh clone. Relocating the workspace fixes it
for every user with one rule, and satisfies Dean's *"in normal operation a user just calls the
benchmark make targets — results should be uploaded into their worktree"* by default rather than by
configuration.

**Raw runs stay out of git even though results are tracked.** `benchmark/runs/` is GB-scale per
campaign and — critically — **token-bearing** (see the hazard below). Tracked persistence is
`benchmark/campaigns/`: curated figures, coverage, and the summary, ~2 MB/cell. If raw runs should be
tracked too, that is a separate size decision and is **not** assumed here.

**Convention adopted for the campaign README** — from **`cde8646c`** (#947, kahilam, 2026-04-10),
which is upstream on `main`: a short metrics table, then a `<details><summary>Dashboard Panels
(N)</summary>` block wrapping relative-path image embeds, with figures in a sibling directory.

**Convention rejected — placement under `docs/`.** #947 filed its results as
`docs/developer-guide/benchmark-summary.md` + `BENCHMARK_PHASE_1_AND_2.md`. **Both were deleted five
months later** by #1053 and #1054, each titled *"Remove outdated …"*, leaving the five PNGs tracked and
referenced by nothing. That is the precedent's own verdict: a dated results snapshot filed as Type-4
developer-guide material **rots**, because Type 4 must reflect current code while a campaign result is
inherently historical. A dated `benchmark/campaigns/<YYYYMMDD>/` is self-evidently historical and
cannot accrue that pressure. Dean, independently: *"I don't think it should be under docs."*

🚨 **BLOCKER on committing anything from the results tree — a live credential.** Every cell's
`run/inference-perf-*.yaml` carries `LLMDBENCH_BASE64_CONTEXT_CONTENTS`, which base64-decodes to a
kubeconfig holding a live `sha256~…` OpenShift bearer token for `DEAN@il.ibm.com` on
`api.pokprod001.ete14.res.ibm.com` — **7 copies**. `benchmark/campaigns/` is pushed to the
`deanlorenz` fork, so committing as-is **publishes it**. Required before the first campaign commit:
the token is **rotated** (Dean's), and `run/*.yaml` is **excluded** from whatever gets committed —
rotation alone is not sufficient, since a rotated-but-committed token still leaks the cluster
endpoint, username, and the manifest shape. Scrubbing is not the same as excluding; prefer excluding.

**Ownership.** The whole change is the **benchmark coder's** — `benchmark/`, `session-notes/`,
`.gitignore`, and the `Makefile` are all outside planner write scope. The planner's contribution is
this section, the campaign write-up
([`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md)), and the
figures currently mirrored at `plans/scratch/campaign-20260810-viz/` (a **mirror**, not the canonical
home — supersede it once `benchmark/campaigns/20260810/` exists).

### 2c. Configuration contract — fail-closed, keyed per kube context (Dean, 2026-08-07/08)

Today `.env` is **fail-open**: `Makefile:45` is `-include hack/benchmark/.env`, and the leading `-`
suppresses the missing-file error, so an absent `.env` is silently tolerated and the `?=` defaults
take over. On a shared cluster the failure mode of a default is not "it didn't run" — it is "it ran,
plausibly, against the wrong target". Two defaults make that concrete: `BENCHMARK_REPO_URL`
(`Makefile:46`) points at **upstream** llm-d-benchmark, so the *guarded* fork arrives only via
`.env`; and `BENCHMARK_REPO_REF` (`Makefile:49`) resolves in KEDA mode to a ref with **no guards at
all** (§5.7).

Dean's requirements, in his ordering — *"safely running in a shared cluster is the most important
thing"*:

1. **Benchmark targets must not run without a `.env`.** The guard is unconditional and lives in the
   **Makefile** — not in a doc, not in a skill. *"Our benchmark targets should not run without .env
   and the benchmark repo should be explicit."*
2. **One `.env` per target cluster / kube context**, discovered by name:
   `hack/benchmark/env/<context>.env`. If the file for the current context is absent, targets refuse
   and point at the wizard. (*"we can have an env per target cluster or per k8s context — we should
   look for the specific .env for the context and ask to create it if needed"*.)
   > REVIEW: can one context be used on multiple NSs? Need to tie to one target NS.  
3. **An embedded assertion triple** — `WVA_ENV_CONTEXT` / `WVA_ENV_SERVER` / `WVA_ENV_NAMESPACE` —
   checked against the live context before anything runs. The filename gives *discovery*; the triple
   gives *correctness*. A single `.env` cannot detect a config/cluster mismatch; a context-keyed one
   carrying an assertion cannot miss it. (OpenShift context names already encode
   `<namespace>/<apiserver>/<user>`, so the triple is derivable, not hand-typed.)
4. **A wizard** — `make benchmark-configure` → `hack/benchmark/configure_env.py`: walks the options,
   **confirms every choice**, **warns about the dangerous ones**, and materializes an explicit
   `.env`. Deterministic and agent-free.
5. **An on-branch skill** — `.claude/skills/benchmark-configure/` — that *explains*. It ships with
   the branch so it reaches Ofer (*"a shared skill that is included on the branch"*), but it is
   **never the enforcement layer**: a skill only helps Claude Code users, so the Makefile guard and
   the wizard must stand alone.

**Why materialize rather than derive.** The alternative Dean raised was deriving everything from the
scope triple (cluster / namespace / test) at run time. Adopted as **wizard input, not run-time
behavior**: the wizard derives the defaults, then writes an explicit auditable file. Run-time
derivation has exactly the failure mode this section exists to prevent.

**Arm-derived refs.** The autoscaler arm is part of the scope, so **`BENCHMARK_REPO_REF` and
`BENCHMARK_SPEC` are derived from the arm and never hand-set** (arms in §7.5; why it is load-bearing
in §5.7). The wizard asks which arm and pins both together, so an arm **cannot select an unguarded
ref by construction**.

**Where the preflight gate belongs.** `benchmark-preflight` (`Makefile:579-587`) exists and is
thorough — it passes both `--repo-dir` and `--expect-ref` — but it has **exactly one call site**:
`benchmark-standup-shared` (`Makefile:604`). The other twelve namespace-requiring targets never
invoke it. It moves onto at least `benchmark-run`, `benchmark-standup`, `benchmark-run-all`,
`benchmark-teardown`, and `benchmark-install`.

**Correction to an earlier note in this plan:** `benchmark-standup-shared` skips **only `step_02`**
(admin CRDs/SCCs) — its step list is `0,3,4,5,7,8,9`, so **step 8 does run**. Any statement that it
skips "02 and 08" is wrong.

---

## 3. Phase 0 — Preserve (zero-loss)

Goal: immortalize the 2026-06-15 state before any branch surgery. Nothing is deleted until it is
verified captured (CONVENTIONS: verify-or-copy-then-delete).

1. **Inventory the untracked artifacts** on `benchmark`: the runbook, harness notes, `results/`,
   and the embedded-clone local patches. Confirm each has no other home yet.
2. **Filter the 68 local-vs-origin commits** for any *genuine benchmark-harness* commit that is
   NOT already on `origin/benchmark` and NOT merged to main (i.e. real unpreserved harness work).
   Expectation from survey: the local commits are TA code (already merged) + upstream PR pulls;
   the 2 real harness commits are already on `origin/benchmark` (BASENAME, scenario-1 guide).
   **Verify this before treating the branch as disposable.**
3. **Commit** the untracked runbook + notes + `results/` onto the current `benchmark` branch.
   **Do NOT commit `.claude/settings.json`** — leave it untracked (local worktree config, preserved
   in place per §5).
4. **Rename, then create fresh, then archive** (Dean's rule — free the name `benchmark`). Sequence
   matters because `git boidem` deletes the local branch and **you cannot delete a branch checked
   out in its own worktree**:
   1. `git branch -m benchmark benchmark-ta3-legacy` (worktree now on `benchmark-ta3-legacy`).
   2. `git switch -c benchmark 11d70a8a` (fresh `benchmark` off current main; worktree now on it —
      this frees `benchmark-ta3-legacy` for archiving). Harness wiring of this fresh branch is Phase 2.
   3. `git tag archive/benchmark-ta3-legacy benchmark-ta3-legacy` (local snapshot tag — the
      permanent recovery handle).
   4. **STOP — do not push, do not delete the local branch.** Write a handoff listing what Dean
      must push (tag `archive/benchmark-ta3-legacy` + fresh `benchmark` → origin) and that the
      local `benchmark-ta3-legacy` branch is deleted only *after* the tag is pushed. **Fork only —
      never upstream.** (`git boidem` itself pushes, so it is Dean's to run, not the coder's.)

---

## 4. Phase 1 — Code-under-test branch + image

Goal: one clean, reproducible branch/tag/image = current main (has A + A′) + C #1480 + D #1481.

**Prereq — the two open PRs on current main.** C and D both sit on `827c8542` (post-#1478 A,
**pre-#1479 A′**). Current main is `11d70a8a` = that + A′. **Both C and D need a 1-commit
forward-rebase onto `11d70a8a`, and BOTH conflict with A′ on `internal/engines/saturation/engine_v2.go`
+ `engine_v2_test.go` + `docs/developer-guide/multi-analyzer-pipeline.md`** (verified
`git diff --name-only` overlap 2026-07-28). C additionally overlaps `engine_v2_population_test.go`
and `throughput-analyzer.md`; D additionally overlaps nothing new. Neither is a clean fast-forward
— each needs an `engine_v2.go` reconciliation against merged A′. ⚠️ **Cross-rebase hazard
persists:** these PRs originated on `55e24be9`, before #1483's `interfaces → domain` rename;
three-way merges can **silently drop hunks**. CONVENTIONS pre-rebase discipline is mandatory:
- Pre-rebase plan per branch (coder records in `plans/session/status/<branch>.md`).
- Per-file diff inventory + per-commit message-vs-diff check after each rebase.
- **Correction (per Dean 2026-07-28):** the open PRs #1480/#1481 do **not** need this rebase.
  C and D sit on `827c8542`, an ancestor of current main, so the integration branch can merge
  them **un-rebased**. Rebasing the live PR branches in place was an unnecessary plan-agent
  implementation choice — do **not** repeat structural git ops on live PR branches without
  consulting Dean first.

**Integration branch** (test-only; fork-only; **never** an upstream PR):
1. Branch off **current upstream main** in its own worktree, name e.g. `ta-testing`.
2. Apply the two open PRs. With A′ now in main the ordering constraint is gone; both C and D
   layer cleanly on current main. Cherry-pick / merge the rebased commits; run gates after each.
3. **Message-vs-diff check on the assembled branch** (the interfaces→domain move makes silent
   hunk loss a real risk). Gates: `make test`, `gofmt -l`, `make lint`, `go build ./...`.
4. **Tag** the integration commit for reproducibility, e.g. `ta-0.9-test-20260728` (immutable
   checkout point — this is what "where did we get the code" resolves to).
5. **Build the image** from this worktree: `make docker-build
   IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (host is linux/x86_64 =
   OpenShift amd64, native build correct; replaces the old `:ta3`). **`docker-push` to quay is
   Dean's** (creds + push gate); do it at deploy time. Record the digest in the runbook (Tier B).
6. **Push branch + tag to origin (`deanlorenz` fork)** — **deferred to Ofer handover** (decision #7:
   only after Step-0 sanity passes). Subject to Dean's explicit per-push confirmation; **never upstream**.

**Push policy correction (2026-07-28, per Dean):** the **open PRs #1480/#1481 do NOT chase main**
— rebase happens only at reviewer request or just before final merge. Moreover the C/D PR
branches did **not** need rebasing *at all* for this exercise: the integration branch could have
merged them un-rebased (they're ancestors of current main). The in-place rebase of the live PR
branches was an unnecessary plan-agent choice and must not recur without consulting Dean.
**State (2026-07-28):** local `ta-model-level-demand` (`25f09a87`) and `ta-veto-liveness`
(`b3f75650`) are rebased **ahead of** their origin PR tips (`7aec2645` / `19c9a122`). Per Dean:
**leave as-is, do NOT push** — pushing would confuse reviewers of #1480/#1481. Harmless while
unpushed. `ta-testing` branch (`db530eed`) + image `:ta-0.9` (digest `sha256:80da87a4…`) **pushed
to fork/quay 2026-07-28** (Dean authorized both).

**Deliverable to Ofer:** branch `ta-testing` + tag `ta-0.9-test-20260728` + image `…:ta-0.9`
(+ digest), all on Dean's fork / quay. He points his guide `tag:` at it, or checks out the tag.

**⚠️ Cross-PR test-signature coupling (found during 1c integration, 2026-07-28).** The C+D
`--no-ff` merge was *textually* clean but had a **semantic** conflict git could not see: C adds an
`arrivalRate float64` parameter to `runAnalyzersAndScore`, and D's new whole-file test
`engine_v2_liveness_test.go` (no textual overlap → unflagged) calls the pre-C signature. It failed
only at `go vet`; fixed in `ta-testing` by adding `arrivalRate=0` to the 6 call sites. **Consequence
for the real PRs:** whichever of #1480 (C) / #1481 (D) merges to upstream **second** will hit this
same break when rebased onto the C-or-D-containing main — the second PR needs the identical
test-call-site fixup, and neither PR's own CI catches it beforehand (independent branches). Flag
to reviewer/author before the second merge.

### 4.1 Refresh trigger — ARMED 2026-07-30 (PR E and PR F both merged)

**Confirmed via a fresh `upstream/main` fetch (read-only):** PR E landed as **#1502** ("feat(controller):
warn operator when a live ConfigMap edit can't change ThroughputAnalyzer registration", commit
`1d5553ee`) and PR F landed as **#1503** ("fix(throughput,saturation): correctness guards for
ThroughputAnalyzer and the liveness engine", commit `6bfb73e1`) — both on top of `f5261c8e`/`f9f04d81`
(D/C) and `da58c0e0` (#1486). New `upstream/main` tip: **`6bfb73e1`**.

**Refresh mechanism (per Dean: "update the test code branch and our controller image") — FULLY
DONE, including both pushes (2026-07-30):**
1. In the `ta-testing` worktree — coder-scoped work — the branch was recreated pointing at the new
   `upstream/main` tip `6bfb73e1` (the old `db530eed` C+D-only assembly predates the real upstream
   merges and has diverged history; its content is preserved forever under the local tag
   `ta-0.9-test-20260728` — nothing lost by moving the branch). Tagged `ta-0.9-test-20260730`
   (annotated, GPG-signed). All gates green. Image built locally, then pushed.
2. **No branch push, no force needed** — `origin/main` (Dean's fork) was independently verified to
   already be at `6bfb73e1`, identical to `upstream/main` and to the new `ta-testing` tip (already
   fast-forwarded and pushed there before this refresh ran), so the `ta-testing` *branch* was never
   pushed — it would only be a redundant, already-public commit. The stale `origin/ta-testing`
   (still at `db530eed`) is a non-urgent cleanup, not actioned.
3. **Both remaining pushes done, Dean-authorized ("quay creds in env. go ahead. push git and
   docker."):**
   - `git push origin ta-0.9-test-20260730` — plain, non-force tag push. **Pushed.**
   - `make docker-push IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` — **Pushed.**
     Digest `sha256:80dec0e9728f4e7d1d06a952f43330e8b1ac5f09592284f87c0e9981c05e19ca`.

**Deliverable to Ofer (updated):** tag `ta-0.9-test-20260730` (on `origin`, == `upstream/main` @
`6bfb73e1` = C #1480 + D #1481 + E #1502 + F #1503 + #1486) + image
`quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (digest `sha256:80dec0e9…`), both live
on Dean's fork / quay.

### 4.2 Tier-A image currency — three tags exist; use `:ta-0.9-anchor-20260807` (2026-08-07)

The Tier-A seam is a `.env` value (`WVA_IMAGE_TAG`), so which image is current is a fact that has
to be recorded somewhere the runner will look. Three tags now exist in
`quay.io/deanlorenz/llm-d-workload-variant-autoscaler`:

| tag | built from | manifest digest | has the anchor refactor? | has `a38d7b73`? |
|---|---|---|---|---|
| `:ta-0.9` | `main@6bfb73e1` | `sha256:80dec0e9…` | no | no |
| `:ta-0.9-anchor-20260806` | `ta-anchor-refactor-v2@075a208e` | `sha256:d6456071…` | yes (pre-merge branch) | **no** |
| **`:ta-0.9-anchor-20260807`** | **`main@d5d58640`** | **`sha256:ab4c8503…`** | **yes (as merged)** | **yes** |

**Use the 20260807 tag.** The 20260806 build predates ev-shindin's `a38d7b73`
*"fix(pipeline): correct role handling and hold reporting in the anchor refactor"*, which he pushed
onto PR-1 before it merged. That commit fixes three problems that are live in the newly opt-in TA
path, and all three would distort a benchmark run: a blank `Role` on the scale-from-zero
`VariantCapacity` manufactured a phantom `RoleBoth` bucket that suppressed **all** scale-up on a
P/D model with any zero-replica variant; the QM refusal reported `OptimizationReady=True` with no
event, so a cluster that had stopped autoscaling looked healthy; and a held variant with a resolved
accelerator but no prior replica count published `wva_desired_replicas=0`, which KEDA reads as
scale-to-zero for a variant that is serving traffic. Benchmarking the 20260806 image would be
measuring a controller that no longer exists.

**How the difference was established** (repeatable — the Dockerfile sets no git-revision label, so
image provenance is not readable from labels alone): `a38d7b73` introduces the string constant
`"OptimizationRefused"` in `internal/constants/constants.go` and `internal/variant/types.go`, so
grepping the built `/manager` binary for it is decisive. The image is distroless and has no shell,
so extract the binary rather than exec into it:

```bash
cid=$(docker create <image>) && docker cp "$cid:/manager" /tmp/m && docker rm "$cid"
grep -c OptimizationRefused /tmp/m    # 20260807 → 4 ; 20260806 → 0 ; ta-0.9 → 0
```

**Consequence for Phase 2/3 — already applied.** Build and quay push are done (2026-08-07; local
`RepoDigest` verified equal to the registry `Digest`), and `hack/benchmark/.env` already pins
`WVA_IMAGE_TAG=ta-0.9-anchor-20260807`, with the superseded digest kept as a comment above it. That
file is untracked (local config), so the pin is not recoverable from git history — this table is the
record of what each tag contains.

**Caveat for reading earlier output:** the run directories `dean-20260807-201009-695` and
`dean-20260807-210058-612` record `running_image: …:ta-0.9-anchor-20260806` in their
`environment/images.yaml`, because they were produced (20:10, 21:00) before the 20260807 image
existed. Neither holds `metrics/raw` scrapes, so neither appears to be a completed measured run —
but if either is ever read as evidence about the anchor refactor, it is evidence about the
**pre-`a38d7b73`** controller, not the merged one. Runs from the 20260807 pin onward are the merged
code.

---

## 5. Phase 2 — Fresh benchmark branch + KEDA harness (blend #1435, parametrized)

Goal (this phase): a fresh Tier-B harness **present on the branch** that follows the KEDA path,
with **every environment-specific value parametrized to an explicit `.env`**, validated by a
**no-op dry standup** — **no cluster contact**. The controller image (`:ta-0.9` seam) is a `.env`
variable and **deferrable**. Executed by the **benchmark coder** in the `benchmark` worktree; the
plan-agent does not write harness code.

**Status 2026-08-08 — this phase is largely BUILT, and the KEDA arm within it is BLOCKED.** The
harness landed and has run twice (single-variant, §1). Two-variant is built but unrun. The KEDA path
below was adopted as designed and is wired end-to-end in the Makefile — but it **has never executed
and cannot as configured**: three verified blockers in **§5.7**, whose fix (refreshing the harness
fork's `main` and rebasing the guards onto it) is a **prerequisite** for the arm rather than part of
it. Everything from §5.0 to §5.6 below is retained as the record of what was adopted and why; §5.7
is what remains.

### 5.0 Approach — (A) blend (DECIDED 2026-07-28, per Dean)

**Adopt PR #1435's WVA-side changes as the concrete KEDA starting point** (it is the only
end-to-end-validated two-variant KEDA wiring), **then parametrize every environment-specific value
to an explicit `.env`** per §2a. The **3 canonical guides are the source of truth for install
*shape***; #1435 is the source of the concrete wiring; Ofer's fork is reference-only, never copied
verbatim.

The 3 guides:
- **llm-d/llm-d** `guides/workload-autoscaling/README.wva.md` — canonical KEDA install. Key shape:
  **KEDA CRD must exist before the controller starts** (WVA only watches ScaledObjects if the CRD
  is present at startup); **namespace-scoped via `--watch-namespace=<ns>`**; Prometheus over
  HTTPS/TLS (secret `prometheus-tls-cert` from the monitoring CA); apply the ScaledObject kustomize
  overlay and **update `serverAddress` + `namespace` in the trigger** (do **not** also apply
  `hpa.yaml`); saturation-V2 via configmap `wva-saturation-scaling-config`.
- **llm-d/llm-d-benchmark** — harness / scenario-runner guides (`multi-variant-benchmark.md`,
  `standup.md`, `run.md`, `workload-variant-autoscaler.md`).
- **WVA repo** — `docs/developer-guide/two-variant-wva-benchmark.md` (#1435 rewrites it for KEDA).

Ofer's fork refs (reference-only): harness `biranofer/llm-d-benchmark` @ `feat/multi-variant-benchmark`;
WVA-side `biranofer/workload-variant-autoscaler` @ `feat/two-variant-keda` (#1435).

### 5.1 What to adopt from #1435 (10 files, WVA-side — all Tier B)

| Area | File | Purpose |
|---|---|---|
| script | `hack/benchmark/add_variant.py` (+401/−181) | VA+HPA → KEDA `ScaledObject` + `TriggerAuthentication`; primary bootstrap (legacy-HPA→SO conversion); SA-token-secret + model-id autodetect; `fix_variant_pod_label()`; `--prometheus-url` |
| script | `hack/benchmark/dump_capacity_demand_estimate.py` (+1/−1) | EPP pod match accepts `router-epp` (not only `gaie-epp`) |
| script | `hack/benchmark/dump_wva_target_timeseries.py` (+26/−3) | wider multi-iteration window; variant tag matches `-v2-` anywhere (SO names are `…-v2-scaler`) |
| script | `hack/benchmark/plot_two_variant_pipeline.py` (+3/−3) | plot title reports per-variant **max** replicas |
| scenario | `hack/benchmark/scenarios/guides/two-variant-wva.yaml` (+72/−75) | flip primary to KEDA (`variantAutoscaling.enabled:false`, `hpa.enabled:false`); **removes** hardcoded `llm-d.ai/variant` label; EPP config `inferenceExtension:`→`router.epp:` |
| scenario (NEW) | `hack/benchmark/scenarios/guides/wva-sat2-tp1.yaml` (+257) | single-variant TP=1 sat-V2 scenario — **carries the most hardcoding** (see 5.2) |
| workload (NEW) | `test/benchmark/scenarios/prefill_heavy_15rps_900s.yaml.in` | 4K/1K, 15 RPS Poisson, 900s |
| workload (NEW) | `test/benchmark/scenarios/prefill_rampup_2_6_10.yaml.in` | ramp 2→6→10 RPS |
| docs | `docs/developer-guide/two-variant-wva-benchmark.md` (+94/−88) | rewrite for KEDA path; drop prometheus-adapter prereq; add KEDA-CRD prereq + failure modes |
| build | `Makefile` (+45/−6) | `PROMETHEUS_URL` var; autodetect configmap/deployment (kustomize vs helm); `BENCHMARK_MODEL_ID` default empty; copy-in parity for `benchmark-run` |

**#1435 creates NO cluster-scoped objects** — every object it makes (`ScaledObject`,
`TriggerAuthentication wva-prometheus-auth`, KEDA-managed HPA `wva-keda-hpa-<dep>`, deployment
label patch) is namespaced. Good for §2a.

> **⚠ Script renamed since #1435 — `add_variant.py` → `configure_variants.py`** (commit
> `ca825621`, on this branch). The names above and in §5.2 / §5.4 are #1435's, kept so the
> provenance still reads; **every reference to `add_variant.py` in this section means
> `hack/benchmark/configure_variants.py`.** A coder grepping for the old name will find nothing.

### 5.2 Hardcoded values to parametrize (→ explicit `.env`, no defaults)

| File | Literal | → becomes |
|---|---|---|
| `add_variant.py` (`make_variant_scaledobject`, primary + variant SO labels) | `inference.optimization/acceleratorName: "NVIDIA-H100-80GB-HBM3"` | `.env` `ACCELERATOR_NAME` / `--accelerator-name` (or auto-detect from node GPU labels) |
| `wva-sat2-tp1.yaml:~35` | image `ghcr.io/llm-d/…-autoscaler` `tag: nightly-d6d39be4` | `.env` `WVA_IMAGE_REPO` / `WVA_IMAGE_TAG` (the `:ta-0.9` seam; **deferrable**) |
| `wva-sat2-tp1.yaml` | `vllm/vllm-openai` `tag: v0.14.0` | `.env` `VLLM_IMAGE_TAG` |
| `wva-sat2-tp1.yaml` + all example `make` comments | namespace `biran`; model `unsloth/Meta-Llama-3.1-8B-Instruct`; `workDir ~/data/wva-sat2-tp1` | `$NS`=`dhl-wva-209`; `BENCHMARK_MODEL_ID`; `.env` workdir |
| `wva-sat2-tp1.yaml` / `two-variant-wva.yaml` | `chartVersions.wva: 0.8.0-rc5`, `prometheusAdapter: 5.2.0`; PodMonitor `release: llmd` | `.env` (**note:** `0.8.0-rc5` pin is stale/inconsistent — KEDA path needs a post-#1341 build; reconcile with the `:ta-0.9` image) |
| `add_variant.py` (`--prometheus-url` default) | `https://thanos-querier.openshift-monitoring.svc…:9091` | already a `PROMETHEUS_URL` Makefile var — source from `.env` |
| `add_variant.py` (primary defaults) | `primary_cost 10.0`, min 1, max 10 | `.env` `PRIMARY_COST/MIN/MAX` |

Derived/constant (OK to keep): `TriggerAuthentication` name `wva-prometheus-auth` (namespaced),
`wva-keda-hpa-<dep>` HPA name, KEDA behavior constants (`pollingInterval 15`, `cooldownPeriod
300`, `scaleDown win 120`, …), SA-token fallback `wva-controller-manager-token` (autodetect first).

**Already fixed by #1435 (no action):** the env-specific `llm-d.ai/variant:
"unsloth--6b24a594-instruct-decode"` label at today's `two-variant-wva.yaml:122` is **removed** by
#1435 (set at runtime by `fix_variant_pod_label()`). **No `serverName`/`wva-system` TLS literal
exists in #1435** — trust is handled by the token-secret CA (`service-ca.crt`→`ca.crt` fallback).
(This supersedes the earlier plan's ServiceMonitor-`serverName` and `llm_d_ai_variant`-relabel
worries — both are moot on the #1435 base.)

### 5.3 §2a shared-cluster safety audit (must hold before any apply — Phase 3, not this phase)

- **Only cluster-scoped write in the whole flow:** `benchmark-standup` (Makefile ~L397–403) runs
  `kubectl create clusterrole prometheus-adapter-resource-reader` when
  `BENCHMARK_SKIP_PROMETHEUS_ADAPTER=true`. The KEDA path **does not need it** (#1435 drops its
  docs). **Do not run that path on pokprod;** removing that Makefile block is a recommended
  follow-up.
- **KEDA CRD** (`scaledobjects.keda.sh`) is a **cluster prereq** — verify present on pokprod; **do
  NOT install/modify** it.
- `oc label namespace $NS openshift.io/user-workload-monitoring=enabled` (Makefile ~L431) — a
  namespaced label but touches monitoring; **verify already enabled on `dhl-wva-209`; do not toggle
  cluster monitoring.**
- `thanos-querier.openshift-monitoring` + WVA SA `cluster-monitoring-view` — shared, **read-only
  reliance**, fine; no cluster RBAC created.
- Every install/query carries explicit `-n dhl-wva-209`; controller install uses
  `--watch-namespace=dhl-wva-209`; ScaledObject trigger `namespace`/`serverAddress` pinned to `.env`.

### 5.4 No-op dry standup (this phase's validation gate — no cluster mutation)

- Add / verify a **`--print-only` (or `--dry-run`) mode in `add_variant.py`** that emits the
  ScaledObject + TriggerAuthentication manifests to stdout instead of applying (it currently
  applies imperatively via kubectl).
- Render the two-variant scenario + generated manifests against `.env` values;
  `kubectl apply --dry-run=client -f -` on the generated manifests; `kustomize build` /
  `helm template` the controller + ScaledObject overlays. **No `oc apply`, no live cluster calls.**

### 5.5 Branch / worktree wiring & runbook

1. **Create the fresh `benchmark` branch** off current main (name freed in Phase 0). **Reuse the
   existing `benchmark/` worktree path** — swap its checked-out branch rather than adding a new
   worktree, so the `wva.code-workspace` folder entry ("benchmark") keeps working with **no VSC
   reconfiguration**. Preserve the untracked `benchmark/.claude/settings.json`. (Minor cleanup: the
   workspace has a stale `git push origin thpt-analyzer` auto-approve — drop when convenient.)
2. **Wire the harness to Tier A:** point the guide's `tag:` (`.env` `WVA_IMAGE_TAG`) at `…:ta-0.9`.
   Keep the embedded `llm-d-benchmark` clone on Ofer's `feat/multi-variant-benchmark` so Dean and
   Ofer run the same scenario definition. **Note:** that clone's `docs/multi-variant-benchmark.md`
   guide is still the **pre-KEDA VA+HPA** recipe — the KEDA path lives only in the WVA-repo
   `hack/benchmark` files copied into the clone by `make benchmark-standup` (Makefile ~L379–421;
   the `awk` block rewrites `scaledObject:` bounds from `BENCHMARK_KEDA_*`).
3. **New `.env.sample`** with `dhl-wva-209` + every value in 5.2 as an explicit placeholder (no
   defaults, no inferred values) — the §2a `.env` discipline.
4. **Documentation — ONE new runbook (Dean, 2026-08-08).** His instruction was to collapse three
   proposed artifacts into a single new one: *"README → new guide linked from main bench guide (a new
   runbook). GETTING_STARTED → in same guide. tools guide → in same guide."*

   **New file:** `docs/developer-guide/benchmark-tooling-runbook.md`. Sections, in order:
   *Getting started* (add a worktree, clone, `make benchmark-configure`, first dry run) ·
   *Tool inventory* (the 22 branch-added files under `hack/benchmark/`, grouped by role) ·
   *Makefile target surface* · *Two-repo topology and the guards-only contract* (§2b) ·
   *Autoscaler arms and how to select one* (§7.5) · *Shared-cluster safety — L1/L2/L3 + preflight*
   (§2a, §2c) · *Run → harvest → analyze loop* · *Troubleshooting*.

   **Linked from the main bench guide** `docs/developer-guide/benchmark-guide.md` (221 lines,
   "Running WVA Scaling Benchmarks") at **two** named points: its `## Prerequisites` section (the
   KEDA CRD prereq and the `.env` gate) and `## Step 4: Clone the Repository` (worktree + wizard).
   No other section of that file changes.

   **Folded in, not left as a second runbook:** `docs/two-variant-wva-pokprod-runbook.md` (405
   lines, fork-owned, from `6505de62`) currently sits at top-level `docs/` rather than
   `developer-guide/` and already covers much of this ground. It becomes the **pokprod section** of
   the new file. *(Decision for Dean: fold-and-delete, or fold-and-leave-a-stub. Recommendation:
   fold and delete — a fork-only doc outside `developer-guide/` is exactly the kind of thing that
   goes stale unnoticed.)*

   **Left alone, linked only:** `docs/developer-guide/two-variant-wva-benchmark.md` (462 lines,
   already rewritten for the KEDA path on this branch) stays the two-variant **scenario** doc.
   `docs/benchmark.md` (589 lines, upstream "Benchmark Results") is untouched.

   Port only still-relevant legacy runbook content — environment/standup/RBAC/signals — dropping the
   `:ta3`-specific and VA+HPA-specific steps the KEDA path supersedes. Runbook + `results/` are
   committed on this branch, **fork only**.
5. **Fallback noted in the runbook:** if the KEDA path fails, the archived VA+HPA runbook
   (`archive/benchmark-ta3-legacy`) is the proven recovery path.

### 5.6 Verification (no cluster contact)

- `python -m py_compile` / lint on the scripts; `yaml`-validate all scenarios; `kustomize build` /
  `helm template` the overlays; `kubectl apply --dry-run=client` on generated manifests.
- **Residual-hardcode grep = zero** outside `.env.sample`:
  `grep -rn 'NVIDIA-H100\|nightly-d6d39be4\|0\.8\.0-rc5\|unsloth/Meta-Llama\|\bbiran\b\|v0\.14\.0' hack/ test/ docs/`.
- Dry standup completes with no `oc`/`kubectl apply` (without `--dry-run`) run.

**Out of scope this phase:** live cluster standup / any `oc apply` (Phase 3+, needs Dean); the
controller image build/push (Tier A, deferred — `:ta-0.9` stays a `.env` var).

**Separation invariant to state in the runbook:** the controller under test is always the Tier-A
image/tag; if it must change, the change is made in a code worktree (PR branch) → re-tag → re-image
→ update `tag:` here. The benchmark branch never carries WVA controller source edits.

### 5.7 The KEDA arm is present but unrunnable — three verified blockers (2026-08-08)

Dean, 2026-08-08: *"we need to KEDA benches too."* The wiring exists. `BENCHMARK_DIRECT_KEDA=true`
(`Makefile:48`, branch at `Makefile:417`) selects controller-free EPP+KEDA autoscaling instead of
WVA, with four tunables (`BENCHMARK_KEDA_{MIN,MAX}_REPLICAS`, `_SCALE_{UP,DOWN}_PERIOD`,
`Makefile:103-106`) and a KEDA-CRD precondition check. It has never run, and as configured it cannot.
Verified read-only:

1. **Its spec is absent from the fork.** `Makefile:61` selects `guides/epp-keda-saturation` in KEDA
   mode. That path exists on **neither** fork ref — `wva-ta-benchmark` and `origin/main` carry only
   `guides/workload-autoscaling` (scenario + `.j2` specification), and `wva-ta-benchmark` is the only
   one of the two that has even that. `epp-keda-saturation` is presumably on true upstream `main`
   post-Feb-2026, but the clone has **no upstream llm-d remote** (only `origin` = Dean's fork, and
   `ofer`, whose push URL is deliberately the literal `READ-ONLY-MIRROR-DO-NOT-PUSH-TO-OFER`), so
   **its existence is unverified** — and a `git fetch` in a tree this role does not own is not the
   planner's to run.
2. **Its ref default selects the unguarded branch.** `Makefile:49` flips `BENCHMARK_REPO_REF` to
   `main` when `BENCHMARK_DIRECT_KEDA=true`. The fork's `origin/main` is at **`b70cf76`,
   2026-02-17** ("Add CKS nightly benchmark workflow (#694)"); **none of the four fork-authored
   commits is an ancestor of it**, and it contains **zero** occurrences of the
   `cluster-monitoring-config` guard symbol. It also lacks the WVA spec from (1). So KEDA mode names
   a ref with **no guards and no scenarios** — note that *neither* branch of that `$(if …)` names
   `wva-ta-benchmark`, the branch the clone is actually on.
3. **Both exits from the resulting error lose something.** `benchmark-standup` asserts the clone's
   branch equals `BENCHMARK_REPO_REF` (`Makefile:432-445`, under a "CLONE SAFETY" comment) and
   hard-errors otherwise, so KEDA mode refuses to start. Correct — but the two ways out are: move
   the clone to `main`, which drops the guards (`check_fork_guards` then fails correctly, since it
   registers `gating=True` → `rep.failed` → non-zero exit); or set `BENCHMARK_CLONE_FORCE_SYNC=true`
   (`Makefile:60`), which hard-resets to `origin/main` and destroys the guards **and** the local
   commits — `Makefile:451` says so explicitly.

**Consequence — a prerequisite, not a task.** Under the §2b guards-only contract the fix is: refresh
the harness fork's `main` from true upstream, **rebase the two guard commits onto it**, and have KEDA
mode select *that* ref. This **gates** the KEDA arm and is not parallelizable with it. It is also the
cheapest moment to do it, because the guards-only migration (§2b) is touching those same two commits
anyway.

**Two cosmetic defects in the same block, worth fixing while it is open:** `Makefile:423` prints
*"upgrading the llm-d-benchmark checkout to '<ref>'"* but the code that follows only checks the CRD —
it upgrades nothing; and `Makefile:424` passes `-n $(BENCHMARK_NAMESPACE)` to a `get crd`, which is
cluster-scoped, so the flag is inert but reads as though CRDs were namespaced.

---

## 6. Phase 3 — Clean stale pokprod + controlled-setup methodology

**Methodology pivot (2026-07-30, Dean redirection — supersedes the earlier full-standup/full-teardown
framing).** Do not run llm-d-benchmark's full `make benchmark-standup` / full-teardown flow as a black
box. Instead: **our-NS-only, select exactly the safe steps, never a full teardown.** Established by
read-only recon of the embedded clone (full detail: `session/status/benchmark.md`); this section is the
durable capture.

### 6.1 Governing principles

- **Our-NS-only, always explicit.** Every `llmdbenchmark`/`oc`/harness invocation carries `-p dhl-wva-209`
  (standup/run) or `-n dhl-wva-209` (`oc`) — never the current-context default (the CLI is "notorious for
  default-NS overwrites").
- **Reuse shared infra; never install/modify it.** pokprod already has a shared Prometheus+operator
  (`prometheus-adapter` in `workload-variant-autoscaler-monitoring`, 64d old), shared KEDA
  (`scaledobjects.keda.sh` CRD + `openshift-keda/keda-metrics-apiserver`), and a shared router control
  plane (GAIE). Our project only enables UWM collection for our-NS metrics and consumes them — it never
  (re)installs or reconfigures any of the three.
- **Never run a full teardown.** `standup step_04_clean_cluster_roles` deletes cluster-scoped
  ClusterRoles/Bindings — admin-only, shared-cluster-wide, **never run it.** Cleanup between runs is
  namespace-scoped only: run-phase `step_01_cleanup_previous` / `step_11_cleanup_post`.
- **Own the outcome without forking the flow.** `standup -s/--step` takes a comma-list or ranges
  (`0,1,5` / `1-7`) with per-step `should_skip(context)`; `-p/--namespace` sets deploy+benchmark NS;
  `--no-monitoring` disables PodMonitor+GAIE ServiceMonitor. This is enough to select exactly the
  namespace+WVA+modelservice(+EPP) steps, skip the one genuinely cluster-scoped admin step, and never
  invoke teardown — **no fork patch is required** for the controlled flow itself.
- **Packaging:** install is editable (`pip install -e .`) — our fork's edits win over any packaged
  version; risky `apply`s live inside editable clone steps. The remote `llm-d-planner@v0.1.0` dependency
  is validation-only (no cluster writes).

### 6.2 Ofer's 11-step standup — hazard classification (fully resolved 2026-07-30, via `--dry-run` + read-only pokprod checks)

A `--dry-run` render (uv venv, editable install of the fork clone, no cluster writes) confirmed the
scenario's actual deploy shape and — critically — that **dry-run over-reports writes**: every
`oc get crd`/secret/cm presence-probe returns empty in dry-run mode, so it shows install commands a
*live* run would skip. The table below is the corrected, code-confirmed model, not the dry-run's
worst-case view.

**Deploy shape for `two-variant-wva`:** method = **modelservice** (→ step_09), gateway class =
**istio**. All three `06_*` alternates (fma/kustomize/standalone) are skipped for this scenario —
the earlier fma-ClusterRole and kustomize-router hazards **do not fire here at all.**

| Step | What it does | Verdict |
|---|---|---|
| 00 `ensure_infra` | validates deps, prints banner | benign |
| 02 `admin_prerequisites` | cluster-scoped Gateway API + inference-ext CRDs + OpenShift SCCs (+ optional Prom CRDs) | **SKIP** via `--step` — all already present on pokprod, and its istio-install sub-step is self-gated (no-op live either way) |
| 03 `workload_monitoring` | WVA install + 2 unconditional cluster-scoped applies (below) | **NEEDED — patched** |
| 04 `model_namespace` | model NS/PVCs, all namespace-scoped | NEEDED, safe |
| 05 `harness_namespace` | harness+model NS, namespace-scoped | NEEDED, safe |
| 06_fma / 06_kustomize / 06_standalone | alternate deploy methods | **moot** — none active for this scenario (method = modelservice) |
| 07 `deploy_setup` | gateway-provider helmfile (istio-base+istiod) + the namespace `infra-{release}` gateway | **NEEDED — patched** (see below; the only step with **no** native presence gate) |
| 08 `deploy_gaie` | per-model **InferencePool + EPP** (Endpoint Picker) Helm release | **NEEDED — CORRECTED 2026-07-30, was wrongly SKIP** (see below) |
| 09 `deploy_modelservice` | vLLM modelservice + Gateway + Route, namespace-scoped | NEEDED, safe |
| 10/11 `smoketest`/`inference_test` | validation | read-mostly, safe |

**⚠️ Correction (2026-07-30, found live during the first real standup) — step 08 must NOT be
skipped.** The original classification conflated step 08 with the shared/cluster-scoped "router
control plane" language from §6.1 and skipped it alongside step 02. That was wrong: step 08's actual
payload here is a per-model, **fully namespace-scoped** Helm release
(`<model>-gaie`, chart `oci://registry.k8s.io/gateway-api-inference-extension/charts/inferencepool`,
`namespace: dhl-wva-209`, `createNamespace: false`, no `ClusterRole`/`ClusterRoleBinding` anywhere in
its helmfile) — it deploys the `InferencePool` CR + EPP (Endpoint Picker) pod *for this specific
model*, not a shared cluster-wide component. **Symptom when skipped:** step 09's "inference pool"
wait sub-step polls for pods behind an `InferencePool` that was never created — `oc get inferencepool
-n dhl-wva-209` returns empty, no EPP pod exists anywhere in the namespace — so it hangs for the full
25-minute timeout and the standup reports a failure at [09], even though the decode pod itself came
up healthy and is genuinely serving. This generalizes beyond `wva-sat2-tp1` to any modelservice-deploy
scenario (`should_skip` for step 08 only checks `"modelservice" not in deployed_methods`, not any
cluster-scope condition). **Fix:** step 08 belongs in the NEEDED set alongside 03/04/05/07/09 — only
step 02 is the genuinely cluster-scoped step to skip.

**The 4 genuinely-unconditional shared writes (confirmed in code, not dry-run artifacts) — all
verified no-op on pokprod, one required a patch:**

1. **step_03 `_apply_monitoring`** — `oc apply -f 03_cluster-monitoring-config.yaml` (ConfigMap
   `cluster-monitoring-config` in `openshift-monitoring`, `data.config.yaml: enableUserWorkload: true`).
   **No "already-enabled?" gate in Ofer's code** — `oc apply` replaces `config.yaml` wholesale, which
   would clobber any other monitoring-stack settings an admin had configured in that same key.
   Verified on pokprod: the existing ConfigMap's `data.config.yaml` is **exactly**
   `enableUserWorkload: true` (no other keys) → the render is identical → **confirmed no-op on
   pokprod specifically.** Patched anyway (see below) since the no-gate behavior isn't safe in
   general.
2. **step_03 thanos-querier ClusterRole apply** (inside `install_prometheus_adapter`, outside the
   PA-reuse `if`/`else` → fires whenever the Prometheus CA cert is extractable, which it is when
   Dean has admin). Verified: `allow-thanos-querier-api-access` ClusterRole already exists (99d,
   not helm-owned) → apply is a **reconcile no-op.**
3. **step_02 SCC bindings / CRD installs** — moot, step_02 is skipped via `--step` regardless.
4. **step_07 gateway-provider re-apply** — `helmfile apply 09_helmfile-gateway-provider.yaml`
   installs istio-base+istiod v1.29.2 cluster-wide, **with no presence gate at all** (unlike
   step_02's equivalent istio-install, which does self-skip). Verified: istiod is Running in
   `istio-system` (72d) and the `istio` GatewayClass is `Accepted` on pokprod → a live run would
   `helm upgrade --install` onto the shared, already-running control plane — **the one genuinely
   live hazard**, not merely belt-and-suspenders.

**Fork patches — COMMITTED + PUSHED to `origin/wva-ta-benchmark`** (2026-07-30, DCO-signed, per Dean
"OK on all. proceed."; verified present on the remote). Design = fail-safe "skip only if already
present" — mirrors step_02's own presence gate (installs when absent, reuses when present). Dean's
**bucket split governs their upstream fate — do not conflate the two:**

- **Bucket 1 — "should-have" gates, eventual upstream candidates, NOT priority now** (commit
  `e88b882`, "presence-gate cluster-scoped gateway/RBAC applies (mirror step_02)"):
  - `step_07_deploy_setup.py` — `_gateway_provider_present()` probes a per-provider CRD
    (`{"istio": "gateways.networking.istio.io"}`); the gateway-provider helmfile apply now runs only
    when that CRD is absent. This is the ONE genuine live hazard (§6.2 above) — ungated it would
    upgrade/adopt the shared istiod. The namespace-scoped `infra-{release}` gateway apply is unchanged.
  - `wva.py` — `_cluster_roles_present()` parses the rendered `22_prometheus-rbac` for `ClusterRole`
    names and probes each with `oc get clusterrole --ignore-not-found`; the thanos ClusterRole apply
    (already best-effort/non-fatal) now skips only when every declared ClusterRole already exists.
  - **Policy (Dean, verbatim intent):** these are consistency improvements worth eventually proposing
    to `llm-d/llm-d-benchmark` as upstream issues/PRs — *after* a live run proves them out. **Not now:
    "we do not push anything to upstream or wait for it."** No action until a successful standup.
- **Bucket 2 — fork-only safety net, will NEVER go upstream** (commit `963bb00`, "shared-cluster —
  don't overwrite cluster-monitoring-config"): `step_03_workload_monitoring.py`'s `_uwm_enabled()`
  probes the `openshift-user-workload-monitoring` namespace and skips the `cluster-monitoring-config`
  apply when UWM is already on (WVA install + namespace label still run after, as before). This
  patch stays fork-only by design — **the public-code end-user make target must not rely on it**
  (§7.0 goal #3); it exists only to protect *our* shared-cluster testing. **This supersedes §6.3
  Item 1's "worth upstreaming" framing above for this specific patch** — Bucket 1 is the upstream
  candidate, Bucket 2 is not.

All three helpers return `False` in dry-run (preserves original render behavior); verified via
`py_compile` + step-registry import + a re-run of the full dry-run render (identical output).

**Operational wrapper (Tier-B WVA Makefile, uncommitted in the `benchmark` worktree — `make` reads
the working tree):** new `BENCHMARK_STEPS` passthrough (`--step`) + a `benchmark-standup-shared`
target, originally `benchmark-standup BENCHMARK_STEPS=0,3,4,5,7,9` (skips `02`/`08`). **Corrected
2026-07-30** (see §6.2's step-08 correction) to `BENCHMARK_STEPS=0,3,4,5,7,8,9` (skips `02` only).
Safety comes from the step selection + the Bucket-1 gates, not the Bucket-2 safety net.

**Live step list (CORRECTED 2026-07-30 — step 08 added back in):** **03(patched), 04, 05,
07(patched), 08, 09** (+00 benign). SKIP **02 only.** Never teardown. Charts verified present at OCI
(WVA `0.8.0-rc5`, digest `sha256:3067b743…`; `prometheus-adapter` `5.2.0`). The full expanded live
command (`make -n benchmark-standup-shared BENCHMARK_NAMESPACE=dhl-wva-209`) was captured and
safety-audited: the ClusterRole-stub block is confirmed **GATED OFF** (`BENCHMARK_SKIP_PROMETHEUS_ADAPTER`
unset → `[ "" = "true" ]` is false, no cluster-scoped write from the wrapper itself); the only
namespace-scoped mutation from the wrapper is the UWM label on `dhl-wva-209`.

**Found live during the first real standup (2026-07-30):** running with the original (uncorrected)
`0,3,4,5,7,9` list, the decode pod deployed and became healthy (confirmed serving real completions
via a direct in-pod HTTP request), but step 09's "inference pool" wait hung the full 25 minutes and
failed, because step 08 — which creates the `InferencePool` + EPP pod step 09 waits on — never ran.
See §6.2's correction for the full diagnosis. **Re-run with the corrected step list is the next
action**, pending Dean's go-ahead.

(Known non-blocking flag, pre-existing in `.env`: `VLLM_IMAGE_REPO/TAG` resolves to
`docker.io/vllm/vllm-openai:v0.14.0` — AGENTS.md discourages `docker.io` for e2e; fine for a one-off
benchmark run, tracked as a cleanup item, not a blocker.)

### 6.3 Research findings (planner, read-only, 2026-07-30) — Ofer's step_03 gap; modelservice/istio literal vs. detected

Two questions handed to the planner (`session/handoffs/plan__benchmark-standup-shared-write-questions.md`),
answered by reading `ofer/feat/multi-variant-benchmark` (his tip, unpatched) vs. our fork's patched
working tree (at the time, uncommitted local edits — since committed/pushed as `e88b882`/`963bb00`,
§6.2) and his own docs.

**Item 1 — how does Ofer avoid the step_03 `cluster-monitoring-config` write?** He doesn't, in any
purpose-built way. Confirmed by diffing our patched working tree against `ofer/feat/multi-variant-benchmark`:
the entire `_uwm_enabled()` gate (§6.2) is our fork's addition — his `_apply_monitoring` has always
applied unconditionally. His own docs (`docs/workload-variant-autoscaler.md`) *do* document
multi-tenant "install-if-absent, reuse-if-present" semantics — but only for `prometheus-adapter`, its
`prometheus-ca` ConfigMap, and the `allow-thanos-querier-api-access` ClusterRole (which have their own
native reuse-checks in `wva.py`, independent of our patch). The `cluster-monitoring-config`
ConfigMap-replace is not mentioned in that multi-tenant table at all. Two existing knobs bear on it but
neither is a precise fit: `monitoring.enabled: false` skips the whole monitoring subsystem (too broad —
also drops PodMonitor/adapter setup), and `--non-admin` skips step_03 in its entirety including the WVA
controller install (also too broad, and matches the "one admin bootstraps once, others run
`--non-admin`" pattern implied by the reuse table — but doesn't give a *targeted* skip for this one
write). **Conclusion:** this is a genuine gap in the public code, not something Ofer's workflow
specifically defeats — most likely he simply hasn't hit it because his own test clusters don't carry
pre-existing custom monitoring-stack config to clobber. Our `_uwm_enabled()` patch is the correct,
narrowly-targeted fix.

**Correction (2026-07-30, per Dean's bucket split in §6.2) — do not upstream this specific patch.**
The line above ("worth upstreaming") is superseded: Dean's categorization puts `_uwm_enabled()` in
**Bucket 2 (fork-only safety net, never upstream)** — it exists to protect *our* shared-cluster
testing, not as a general library improvement, and the public-code end-user path must not rely on it.
Only the Bucket-1 gates (step_07 gateway-provider presence, `wva.py` thanos ClusterRole presence) are
eventual upstream candidates, and only after a live run proves them out — not a current priority.
**This item is CLOSED** — a definitive answer was requested and delivered; no further planner action
needed regardless of the Bucket-2 patch's own defensive coverage.

**Item 2 — is `modelservice`/`gateway.className=istio` cluster-detected or a scenario literal?** Purely
literal, confirmed by code: `deployed_methods` resolves from `_resolve_deploy_methods()` (`cli.py`),
whose priority is `--methods` CLI flag → the scenario's `<method>.enabled` keys → a phase default —
never a cluster query. `gateway.className` is read via `_require_config(plan_config, "gateway",
"className")` — a required config field, overridable only by `--gateway-class`. There is **no
detection layer anywhere** in the tool that probes the cluster's installed gateway provider and picks
accordingly; our own new `_gateway_provider_present()` (§6.2) is a one-way presence *check* used to
skip a redundant install, not a selection mechanism. The scenario's `istio` literal happens to match
pokprod by construction (the scenario was authored against a cluster that also runs istio), not by
inference. **Consequence for the public-code end-user path (§7.0 goal #3):** the makefile target must
either (a) document the prerequisite explicitly (target cluster must already run the gateway provider
named in the scenario), or (b) make `gateway.className` a required `.env`/CLI input rather than a
scenario constant — relevant directly to Dean's CONFIG-CONSOLIDATION goal (variant-count + all config
in one yaml). No code or upstream change needed to *use* this today — `--gateway-class` already exists
as the override lever.

### 6.4 What actually happened (2026-07-30, Dean-approved, DONE)

The namespace cutover ran ahead of the full controlled-setup design via a simpler path than the
originally-planned `llmdbenchmark … teardown -p dhl-wva`:
- `oc new-project dhl-wva-209` — created, context switched, namespace empty/Active.
- `oc delete project dhl-wva` — the old 45-day legacy VA+HPA stack fully nuked (no GPU pods were
  running); project confirmed `NotFound`, clean termination.
- Both steps are **namespace-scoped deletes**, no cluster-global impact; every subsequent command in this
  session carries explicit `-n dhl-wva-209`.

This closes the original Phase 3 goal (remove 2026-06-15 leftovers, stand up fresh) without needing the
`llmdbenchmark teardown` command path or the itemized `oc delete podmonitor/deploy/role` cleanup listed
in the pre-pivot plan — a plain project delete removed all of it at once. **No further Phase 3 action
needed;** §6.1–6.3 above now govern the *live standup*, which is Phase 4's concern (§7).

---

## 7. Phase 4 — Scenarios + small e2e

### 7.0 Longer-term goals & deliverable shape (2026-07-30, per Dean — supersedes
`project_benchmark_makefile_two_variant_todo`)

**MECHANISM (important distinction):** the eventual **end-user deliverable must not depend on our
fork.** It enumerates the specific safe `--step`s (§6.2's provisional list) and runs **standard PUBLIC**
`llm-d-benchmark`. Our fork (`deanlorenz/llm-d-benchmark`) is a **testing safety net only** — we may
patch it to make the skips fail-safe *while we test*, but that patching never becomes part of the
shipped path.

**Sequencing dependency:** the two-variant scenario is **not yet in public `llm-d-benchmark`** — it
lives on Ofer's `feat/multi-variant-benchmark` (mirrored on our fork's `wva-ta-benchmark` branch, used
for *our* testing now). The public-code end-user path is blocked on that scenario landing upstream
first; this is a sequencing concern for whoever schedules the upstream PR, not something this plan
resolves.

**Three longer-term goals to carry forward:**
1. **Ofer runs with our controller image** — already achievable today via the `WVA_IMAGE_REPO`/
   `WVA_IMAGE_TAG` `.env` seam (§5.2/§5.5); no code change needed.
2. **An end-user TA guide**, in the spirit of the existing WVA-with-KEDA guide on `llm-d/llm-d`
   (`guides/workload-autoscaling/README.wva.md`, read in §5.0).
3. **A Makefile target + setup env** that lets an end user safely test TA using **public** benchmark
   code with an explicit safe `--step` list (not our fork) — the shipped form of §6.1–6.2's controlled
   flow. (Supersedes the deferred "generalize `benchmark-standup` for two-variant + WVA-image-override"
   note; that note is now absorbed here.)

### 7.1 Step 0 — basic e2e sanity

Goal: **simplest-first.** Confirm the basic scale signal works end-to-end on pokprod *at all*
before any TA-isolation. Dean's guidance: **we have never reliably gotten the scale signal** —
even the 2026-06-15 "scale-up captured" (§12) was sat_v2-driven and the runbook itself (§14) says
a clean basic scale-up was not achieved. So treat the plumbing as **unproven** and start there.

**Standup mechanism for this phase (per §6.1–6.2, CORRECTED 2026-07-30):** `make
benchmark-standup-shared BENCHMARK_NAMESPACE=dhl-wva-209` (`BENCHMARK_STEPS=0,3,4,5,7,8,9`, skip `02`
only) — the new Makefile wrapper, **not** the bare `make benchmark-standup`. Runs against the fork's
Bucket-1-patched step_07/`wva.py` (§6.2, committed+pushed) and standard step_03 (Bucket-2's
`_uwm_enabled()` is also present but defense-in-depth, not relied on). **Step 08 must be included** —
it deploys the per-model InferencePool+EPP that step 09 depends on; the original `0,3,4,5,7,9` list
(without 08) was run live and failed at [09] after a 25-minute timeout for exactly this reason (§6.2).
All identified cluster-scoped writes are confirmed no-op on pokprod or neutralized by a patch; the
live run is blocked only on Dean's explicit go-ahead to re-run with the corrected step list.

**Step 0 (do first) — a few basic e2e on pokprod, simplest possible (DECIDED 2026-07-28).**
Shape: **single variant, small model, small → bigger workload, clear expected scaling signal
1 → 2.** With the Tier-A image deployed: drive a constant→stepped load and confirm the whole
chain moves — load → `wva_desired_replicas` rises from 1 → 2 → HPA `REPLICAS` follows → a second
pod actuates. min=1, hold each step ≥6 min (autoscale lag ~2 min). This is the "does anything
scale" gate; nothing below is meaningful until this is green and reproducible. Mirror `test/e2e/`
load drivers (§14.1); custom in-cluster loadgen (runbook §13.2) is the reliable fallback if
guidellm delivers 0 load again. **A small model keeps GPU footprint low and the 1→2 boundary
unambiguous.**

**Then — headline scenario — TA drives a decision sat_v2 would not.** Per runbook §14: decode-heavy
short requests + a *slow* RPS ramp so TA's RequiredCapacity goes positive **before** sat_v2's
KV/queue gate trips. Controlled arms: TA-on vs TA-off (as in the Arm-B methodology) to prove the
delta is TA, not sat_v2. This is the never-yet-seen result.

**New 0.9-behavior scenarios (Tier-A specific):**
- **Veto-liveness (#1481):** an uninformative analyzer (never-had-metrics / error / stale) must
  **not** veto scale-down; a live analyzer still can. Cluster analogue of the unit tests — e.g.
  kill/stall a metric source and confirm scale-down is *not* blocked; safety floor = no live
  analyzer → no scale-down.
- **Model-level demand (#1480):** decode demand computed from a model-level arrival sum; verify
  aggregation across variants matches expectation under multi-variant load.
- **Registration-safety (#1479):** config-absence → analyzer not registered (opt-in); confirm the
  startup non-registration log and that a disabled analyzer cannot veto.

**Small e2e (mirror `test/e2e/`):** §14 direction — start from the repo's known-working e2e load
drivers and HPA-actuation assertions (`wva_desired_replicas` → HPA → replicas), mirror that load
path rather than fighting guidellm. If guidellm still delivers 0 load, use `inference-perf` (the
scenario supports it) or the custom in-cluster loadgen (runbook §13.2).

**Output:** a scenario matrix (name / hypothesis / load shape / TA-vs-sat_v2 arm / expected
signal / pass criteria) captured in the runbook (Tier B), each event summarized with the analyzer
scores that drove it (`--v=4`).

### 7.2 Grafana observability during benchmark runs (fact-finding, 2026-07-31 — NOT executed)

**Goal:** see the WVA Grafana operational dashboard live in a browser while a benchmark runs on
pokprod. Pure research so far — **nothing below has been created on the cluster.**

> **⚠️ HARD RULE (Dean, 2026-07-31): never create a `ClusterRoleBinding` (or any other
> cluster-scoped RBAC object) automatically. Any such action requires Dean's explicit, per-action
> permission — same standing rule as every other cluster-scoped write in this plan (§2a), called
> out again here because the recipe below specifically needs one.**

**What already exists (verified, all read-only checks):**
- WVA emits ~26 real Prometheus metrics (`internal/constants/metrics.go:166-281` — `wva_desired_replicas`,
  `wva_saturation_utilization`, `wva_spare_capacity`, `wva_required_capacity`, etc.).
- A real dashboard definition: `deploy/grafana/operational-dashboard.json` (46 KB) — replica overview,
  scaling decisions, saturation utilization, capacity breakdown, GPU discovery, KV cache, queue depth.
- It uses a Grafana **template variable** (`datasource_uid`, type `datasource`, filtered to
  `query: "prometheus"`, **default value literally `"prometheus"`**) — not a hardcoded UID. Naming
  the datasource CR `prometheus` makes the dashboard resolve it with zero JSON editing.
- `docs/user-guide/monitoring.md` documents installing it via `make deploy-wva-on-k8s` (Grafana +
  kube-prometheus-stack, sidecar-loaded dashboard ConfigMap) — but that whole path is **kind-emulator /
  plain-kubernetes only**. Confirmed by reading `deploy/lib/infra_monitoring.sh` →
  `deploy_prometheus_stack()` is environment-specific: `deploy/openshift/install.sh`'s implementation
  (`:113-117`) only calls `find_thanos_url()` — it installs **no Grafana at all** on OpenShift.
  `deploy/kind-emulator/install.sh:249` and `deploy/kubernetes/install.sh:33` are the ones that
  `source deploy_prometheus_kube_stack.sh` (installs kube-prometheus-stack's own bundled Prometheus +
  Grafana, ConfigMap+sidecar dashboard loading — **this is "the setup script that works with WVA
  kind"** Dean flagged). **It does not help directly on pokprod**: it installs an entirely new
  Prometheus (redundant with — and itself a cluster-scoped-CRD-installing action against — the shared
  UWM/Thanos stack we're explicitly not supposed to touch, §2a), not a datasource pointed at existing
  Thanos. Useful only as a reference for the ConfigMap/sidecar dashboard-loading convention, not as
  something to run on OpenShift.
- A second dashboard (`deploy/grafana/benchmark-dashboard.json` + `benchmark-grafana.yaml`, from PR
  #900) is dead code — not referenced by any current Makefile target, script, or CI job.
- The `llm-d/llm-d` canonical guide (`docs/operations/observability/setup.md`) confirms the OpenShift
  Thanos URL (`https://thanos-querier.openshift-monitoring.svc.cluster.local:9091`) but gives **no**
  auth/RBAC guidance beyond "configure TLS." Its install script
  (`guides/recipes/observability/install-prometheus-grafana.sh`) **explicitly refuses to run on
  OpenShift** ("this script does not support OpenShift... use built-in user workload monitoring
  instead") and has zero ServiceAccount/bearer-token logic anywhere in it.
- A third-party doc (shuynh2017/opendatahub-operator, `docs/install/wva/3.5-ea2-installation-procedure.md`
  § "Observability - WVA Grafana Dashboard") is a manual, browser-only import walkthrough — assumes a
  Grafana instance + Prometheus datasource already exist, links the same `operational-dashboard.json`,
  and flags one genuinely useful gotcha: **leave the dashboard's `namespace_label` variable set to
  `exported_namespace`** (matches the `honorLabels`/ServiceMonitor relabeling gotcha already documented
  in `docs/user-guide/monitoring.md`).

**The gap, confirmed precisely: nowhere in this repo, the llm-d/llm-d guides, or the llm-d-benchmark
harness is there a documented recipe for authenticating a Grafana datasource against OpenShift's
shared Thanos.** That's exactly the "access keys" piece Dean anticipated being the hard part.

**The recipe that already works — reverse-engineered (read-only) from two independent, currently-live
Grafana instances on pokprod (`observability-hub`, `dpikus-precise`, both using `grafana-operator`
`grafana.integreatly.org` v5, confirmed cluster-wide-installed, not something we'd need to install):**

1. `Grafana` CR (grafana-operator) — minimal spec, a label (e.g. `app: grafana`) for the datasource's
   `instanceSelector` to match.
2. A dedicated `ServiceAccount` (e.g. `grafana-sa`) in our own namespace (`dhl-wva-209`).
3. A static long-lived token `Secret` (`type: kubernetes.io/service-account-token`, annotated
   `kubernetes.io/service-account.name: grafana-sa`) — supplies the bearer token without needing
   `TokenRequest`/projected-volume machinery.
4. **⚠️ A `ClusterRoleBinding` of that ServiceAccount to `cluster-monitoring-view`** — the same
   ClusterRole the WVA controller itself already uses to read Thanos. **This is the step covered by
   the hard rule above — do not create it without Dean's explicit go-ahead**, even though it's the
   same ClusterRole already in use elsewhere on this cluster.
5. `GrafanaDatasource` CR, **named `prometheus`** (to match the dashboard's template-variable default),
   `type: prometheus`, `url: https://thanos-querier.openshift-monitoring.svc.cluster.local:9091`,
   `access: proxy`, `jsonData: {httpHeaderName1: Authorization, tlsSkipVerify: true}`,
   `secureJsonData: {httpHeaderValue1: "Bearer ${token}"}`, `valuesFrom` → the step-3 Secret's `token`
   key. Both live reference instances use this exact URL independently — strong signal it's the
   standard, not a one-off.
6. `GrafanaDashboard` CR — `spec.json:` = the raw contents of `deploy/grafana/operational-dashboard.json`
   pasted inline (confirmed shape from `dpikus-precise`'s `vllm-overview` dashboard CR), plus
   `instanceSelector.matchLabels` matching step 1's Grafana CR.
7. A `Route` (edge TLS) exposing the Grafana `Service` externally — not operator-managed in the
   reference instances (no `ownerReferences`), so likely a plain `oc expose service`/`oc create route`
   alongside the CRs.

**Open decision points for Dean before any of this is created:**
- Confirm the `ClusterRoleBinding` step (4) explicitly, separately from the rest — per the hard rule.
- Datasource/dashboard naming (`prometheus` recommended, to get the template-variable auto-resolve).
- Whether Grafana admin credentials should be a `Secret` reference (more correct) vs. the plaintext
  `spec.config.security.admin_password` the reference instances use (simpler, but not our habit
  elsewhere in this project).
- Whether this lives in `dhl-wva-209` itself (single-namespace, benchmark-scoped) or the coder proposes
  something else.
- Whether/how to fold this into the `benchmark-standup-shared` Makefile flow (a later automation step,
  not needed for a first manual proof-of-concept).

**Not yet done:** turning this into a coder task plan / handoff. This section is fact-finding only,
per Dean's explicit "no edits for now."

### 7.3 inference-perf load-gen fix + a first "does TA do anything" workload (2026-07-31, corrects a prior handoff)

**Corrects `session/handoffs/plan__benchmark-harness-guidellm-vs-inferenceperf.md`'s diagnosis.**
That handoff claimed "Ofer ran guidellm, not inference-perf" and proposed patching the Makefile's
local-`.in` copy branch to fix an inference-perf filename mismatch. **Both are wrong — verified
directly against Ofer's fork (2026-07-31):**

```
$ git show ofer/feat/multi-variant-benchmark:config/scenarios/guides/two-variant-wva.yaml
...
  harness:
    name: inference-perf
    experimentProfile: shared_prefix_synthetic.yaml
```

Ofer's scenario declares `harness.name: inference-perf` — the `-l guidellm` string the prior
handoff cited is a **usage-comment example** a few lines above, not the actual config. **We need
both harnesses** (Dean): guidellm already works via native catalog profiles (proven —
`wva_sat2_short`, the sat-only validation run); inference-perf is specifically needed because its
native `load.stages` schema supports **staged/ramped rate profiles** — exactly what a
calibration-then-trigger workload needs, and something guidellm's profile format doesn't offer as
cleanly.

**The real root cause (not the local-`.in` filename mismatch):** `Makefile:568` unconditionally
appends `-w $(BENCHMARK_WORKLOAD).yaml` to every `benchmark-run` invocation, for **both** harnesses
— `step_05_render_profiles.py`'s `_resolve()` (`llmdbenchmark/executor/step.py:151-171`) is a
three-tier fallback (CLI/context value → scenario `plan_config` → hardcoded default), and the CLI
value is Tier 1, unconditionally winning over the scenario's own `harness.experimentProfile` field
— even when the scenario already correctly declares one (ours does: both `two-variant-wva.yaml:279-281`
and `wva-sat2-tp1.yaml:213-215` already say `harness: {name: inference-perf, experimentProfile: ...}`,
matching Ofer's exact shape). The Makefile's forced `-w` silently shadows this every time. The
local-`.in` copy-branch bug the prior handoff found is a real bug, but it's downstream of this — a
symptom of routing custom profiles through a separate, fragile mechanism instead of the tool's own
catalog convention (`workload/profiles/<harness>/<name>.yaml.in`, committed to the fork, exactly how
Ofer's own `shared_prefix_synthetic.yaml.in` lives on his branch).

**Recommended fix (not yet implemented — coder task):**
1. Make `Makefile:568`'s `-w` conditional, mirroring the existing `$(if $(BENCHMARK_MODEL_ID),-m
   $(BENCHMARK_MODEL_ID),)` idiom on the same line: `$(if $(BENCHMARK_WORKLOAD),-w
   $(BENCHMARK_WORKLOAD).yaml,)`, with `BENCHMARK_WORKLOAD ?=` defaulting to empty rather than
   `prefill_heavy.yaml`. This restores the scenario's own `harness.experimentProfile` as authoritative
   whenever the user doesn't explicitly ask for a different profile on the command line — harness-agnostic,
   fixes both guidellm and inference-perf the same way, no per-harness special-casing.
2. Audit the other `$(BENCHMARK_WORKLOAD)`-gated blocks (`:498,505,549,554` — the direct-KEDA
   endpoint injection, the inference-perf catalog auto-fetch, and the local-`.in`/local-file copy
   branches) so they no-op cleanly when `BENCHMARK_WORKLOAD` is empty, rather than erroring on an
   empty path.
3. **Custom profiles stop going through the local-`.in` mechanism entirely.** Commit them directly
   into the embedded clone's native catalog path on our fork (`wva-ta-benchmark` branch):
   `workload/profiles/inference-perf/<name>.yaml.in`, referenced purely via the scenario's own
   `harness.experimentProfile: <name>.yaml` — same convention Ofer's `shared_prefix_synthetic.yaml.in`
   already uses successfully. (Verified this survives editable-install re-renders the same way his does;
   it does *not* survive a `git reset --hard origin/wva-ta-benchmark` unless committed to that branch —
   commit it, don't leave it as a local uncommitted file in the clone.)

**A first workload — "does TA do anything at all" (simpler bar than the full TA-lead experiment in
`plan__ta-sat-scaleup-lead-setup.md`, which remains open separately).** Per that handoff: TA needs
`MinSamples=10` with `KSpread≥0.30` to flip its `reason` off `T2-default`
(`GLOBAL_OPT_INTERVAL=60s` ⇒ needs ~10+ min of varied load). This profile doesn't try to stay under
saturation's 0.85 KV threshold — that constraint is specific to the fuller "TA leads" experiment;
here we just want TA to calibrate and show *any* signal (reason flip, nonzero RC) so the coder has
something concrete to look at. Fixed token shape (matches the already-validated `wva_sat2_short`
guidellm shape: ~4096 in / ~1024 out) so the OLS fit isn't confounded by shape changes; only the
rate varies, sweeping from near-idle to above the known-saturating rate (12-24 RPS, per
`wva_sat2_short`) over 8 stages / 12 minutes:

```yaml
# workload/profiles/inference-perf/ta_calibration_probe.yaml.in
# Sweeps rate from near-idle to above-saturating at a fixed token shape, so TA
# (10 samples, KSpread>=0.30 to leave T2-default) gets a chance to calibrate
# and show a signal. Does not try to stay under k_sat=0.85 -- unlike a true
# TA-vs-saturation lead experiment, this just checks TA reacts at all.
load:
  type: constant
  stages:
  - rate: 2
    duration: 90
  - rate: 4
    duration: 90
  - rate: 6
    duration: 90
  - rate: 8
    duration: 90
  - rate: 10
    duration: 90
  - rate: 13
    duration: 90
  - rate: 16
    duration: 90
  - rate: 20
    duration: 90
api:
  type: completion
  streaming: true
server:
  type: vllm
  model_name: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
  base_url: REPLACE_ENV_LLMDBENCH_HARNESS_STACK_ENDPOINT_URL
  ignore_eos: true
tokenizer:
  pretrained_model_name_or_path: REPLACE_ENV_LLMDBENCH_DEPLOY_CURRENT_MODEL
data:
  type: random
  input_distribution:
    min: 4000
    max: 4200
    mean: 4096
    std_dev: 50
    total_count: 2000
  output_distribution:
    min: 950
    max: 1100
    mean: 1024
    std_dev: 30
    total_count: 2000
report:
  request_lifecycle:
    summary: true
    per_stage: true
    per_request: true
storage:
  local_storage:
    path: /workspace
```

**Unverified, flag to coder:** `total_count: 2000` is a generous guess (the 8-stage sum is ~7,100
requests at the given rates × durations) — I did not confirm inference-perf's exhaustion behavior
(cycles vs. errors) if a stage needs more distinct prompts than `total_count`. Verify empirically;
raise if requests start erroring out partway through a stage.

**Verification signals (same as the fuller experiment):** `analyzer=throughput` log lines — watch
`reason` flip off `T2-default`, and `RequiredCapacity` go nonzero at some point during the sweep.

### 7.4 Scenario gaps from the ladder-run cross-check (2026-08-08)

Source: handoff `plan__benchmark-next-run-capture-list.md` from the `benchmark` session, itself the
product of an independent cross-check by the `autoscaling-viz` session. The harness-side items in
that handoff are the coder's and are tracked in its own `session-notes/status/benchmark.md` §17.8;
the three below change the **workload scenario**, which is not the coder's to change, and are
therefore plan-level.

**Status: OPEN — recorded, not decided.** Planner recommendation: **take all three.** 7.4.1 + 7.4.3
together are exactly the right-sizing / steady-state emphasis Dean named (*right-sizing and
steady-state are the premise of autoscaling and the real money-saver, more than transition speed*),
and 7.4.2 is one extra leg. Any run needs Dean's approval regardless, so writing these down as open
costs nothing and holds nothing up.

> **⚠ Read §7.6 before acting on 7.4.1 or 7.4.2.** A later addendum from the coder shows that
> **7.4.1's stated mechanism cannot deliver 7.4.1's stated goal** — steady-state KV under a tracking
> controller is a *controlled* variable, so the dwell is an analyzer-configuration lever, not an
> offered-rate one; 7.4.2 has the same defect, more sharply. The *goals* stand; the *mechanisms* are
> superseded. §7.6 also records that the coder reports Dean approved all three and has implemented
> them — **unconfirmed by the planner**, which is why this marker still reads OPEN.

**7.4.1 A mid-band dwell stage — the largest gap.** Hold an offered rate that parks KV utilization in
**0.3–0.85** for **≥3 min**. **No run in any pool has ever dwelt there** — every run to date is
either sub-saturation (the 08-07 ladder tops out at kv 0.67 @ 20 RPS) or pinned at kv ≈ 0.99 (arm B).
The interesting region is between them, and it is precisely the region an autoscaler is supposed to
hold a service in. It is also what makes the concurrency-vs-latency slope fittable and the throughput
knee locatable. The ladder is close, so this is likely one or two more rungs above 20 RPS held long
enough to be a dwell rather than a step. **The rate must be found by measurement, not predicted** —
the RPS↔KV relationship is the thing being characterized. The coder has offered a short probe run to
locate it first, which needs Dean's approval like any other run.

> **The exact no-action band, computed from the applied thresholds (Dean, 2026-08-11: "need to compute
> exact expected band based on applied up/down thresholds").** Not a separate calculation — the band is
> the direct definition of `saturation_v2`'s two universal thresholds
> (`internal/config/saturation_scaling.go:54-64`):
> `requiredCapacity = max(0, demand/ScaleUpThreshold − supply)` fires scale-up once
> `demand/supply > 0.85`; `spareCapacity = max(0, supply − demand/ScaleDownBoundary)` allows scale-down
> once `demand/supply < 0.70`. **So the no-action band is exactly `[0.70, 0.85]`** — narrower than the
> `0.3–0.85` this section names, which was never the band implied by the thresholds, only a wide guess
> at "somewhere mid-range." **0.67 is just below 0.70, outside the band on the low side** — close, and
> consistent with this section's own "sub-saturation" framing, but not inside it. Restated for §7.6:
> the test is whether steady state lands in `[0.70, 0.85]` (or the equivalent band for whichever
> analyzer combination is under test — TA's own thresholds, and TA+SAT's combined behavior, are not
> necessarily this same interval and have not been separately derived), not `[0.3, 0.85]`.

**7.4.2 One short-output leg.** E.g. **2000 in / 100 out**, to probe the ITL lower knee. The
arithmetic is the point: 4K-in/1K-out is still **decode**-dominated in time, so the current
"long input" shapes are not prefill-heavy in any useful sense — **prefill-heavy needs short outputs,
not merely long inputs.** Corroborating measurement from the ladder run: `itl ~ running` alone
reaches r² 0.93–0.94 *below* the band and adding a prefill term buys **+0.001**, whereas in-band it
buys **+0.236**. Prefill is a regime-specific term, so a shape that isolates it is worth having.

**7.4.3 Let the run outlive the cooldown.** **≥300 s of collection after load stops**, or scale-down
never lands inside the measurement window. The closing 20→2 RPS step is already the right shape — it
is the *collection window* that needs extending, not the load profile. A ramp-down is also the honest
test of rescaling, because scale-down has no boot lag. Named next after these, per Dean: more noise in
the input signal, and a change in request shape. **Agreed, 2026-08-11**, with an addition: *"if we have
[a] scenario that start[s] from more than 0 replicas, we need [to] cut the boot period out of the
results (like we did in the simulations)."* Any cell whose scenario starts at `minReplicas > 0` (or
whose ScaledObject is pre-warmed above 0 before the workload begins) must have its analysis window
start **after** boot lag clears, the same convention the `autoscaling-viz` simulation work already
applies. **Not yet implemented in the extractor** — `extract_real_trace.py` currently analyzes from
t=0 regardless of starting replica count. Candidate for the viz Type 1's coverage-check / self-check
section, or a dedicated extractor flag; not designed here.

**Measurement constraint — restate this wherever the plan or the runbook specifies metrics
collection.** The ladder run contains a **routing oscillation** with a period of **6–11 s**, tracking
mean request sojourn time (ratio 0.92–1.09 across all six loaded stages as sojourn moves 5.7 →
12.0 s); per-pod arrivals oscillate at r **+0.25…+0.73** while the *pooled* stream looks flat
(r ≈ +0.09–0.14) because co-loaded pods run anti-phase and cancel. At ~15.7 s between scrapes,
**Nyquist is ~31 s**, so this whole band is aliased away in **every gauge-derived series** — ours, and
by extension anything WVA or a Grafana panel computes the same way. **A finer scrape rate does not fix
this and neither does a per-pod gauge**; it was visible solely because the gateway access log records
`UPSTREAM_HOST`. That is why the per-request trace is a requirement, not a nice-to-have — and why the
gateway log-follower (built, **not yet applied** — see §9 T9) matters.

**Two corrections to propagate if any doc, handoff, or derived note quotes them.**
- **The decision rule is not `ceil(demand/prc)`** — that form was retracted. Verified 65/65 cycles:
  `rc = demand/0.85 − supply`, then `curr + ceil(rc/prc)` applied to the **residual**.
- **`bytes_sent` is not a per-request output-token weight.** The median calibrates (511 implied vs a
  true 512) but the dispersion does not — ~14% p5→p95 vs `output_len`'s ~44%, and implied bytes/token
  drifts 170–187 across stages. Stage-level totals only. Likewise
  **`x-envoy-upstream-service-time` is not TTFT** (flat 7–9 ms while harness TTFT climbs
  47 → 183 ms).

**Retention rule carries an exception.** The multi-GB per-replica files go; **`metrics/raw/` stays**
(12–35 MB/run, compresses ~10×, and the only time-resolved source of KV / running / waiting / ITL /
preemption). A blunt reading of "delete the big data" would take it — and did, once, during the
autoscaling-viz migration, which is where the **fresh-checkout acceptance gate** (§9 T8) comes from.

### 7.4.4 Workload coverage matrix + theory/simulation/real baseline (Dean, 2026-08-11)

**Two new asks, neither built.** *"I need a coverage matrix on the workloads. We need a test plan that
explains each workload and what we expect in principle."* Real gap: nothing today lists every
`ta_autoscale_*.yaml`/`ta_prefill_knee.yaml` workload alongside its purpose and its expected outcome.
This doc explains individual workloads inline as they're introduced (§7.4.1's mid-band ask, §7.4.2's
short-output leg, §7.6's sawtooth) but there is no single table a cold reader can scan to see the whole
set at once, or to notice a gap in coverage.

**The second ask is a methodology, not a table:** *"we should have theory based on simulation + viz,
simulation based on actual workload generated + viz. This will give us a synthetic baseline before we
actually benchmark (can ref the results from the plan)."* Read precisely, this is **three** artifacts
per workload, not one, in a specific order:
1. **Theory** — a prediction from the analytical model alone (the capacity/ITL formulas the viz Type 1
   states — see [`autoscaling-viz-design.md`](autoscaling-viz-design.md)), rendered through the
   `autoscaling-viz` panel set on synthetic input.
2. **Simulation from the actual generated workload** — the same panel set, but driven by the real
   request stream the harness would generate for that workload spec (not the analytical idealization),
   still before touching a cluster. `autoscaling-viz`'s existing `sim_from_run.py`/`run_inputs.py`
   toolchain (see `autoscaling-viz/planning/sim-from-benchmark-plan.md`) is the closest existing
   precedent for this step, though it was built for a different purpose (calibration against an
   already-real run) and would need checking against this use (a synthetic baseline built *before* the
   real run exists).
3. **Real** — the actual benchmark result, compared against (1) and (2) rather than read cold.

**Why this matters and is not just extra process:** it gives a way to tell, before spending cluster
time, whether a workload is even capable of exercising what it's meant to test — e.g. this session's own
sawtooth cells ran but were too short to reach steady state (§7.6, corrected), a fact a theory pass
would likely have flagged before the run. **Not designed here.** Candidate homes: the coverage matrix
and the theory/simulation legs are viz-side (`autoscaling-viz-design.md`, per Dean's own scoping — viz
owns "synthetic simulation" and "simulation-following-a-test"); the workload-spec-to-purpose mapping
itself may belong in the not-yet-written benchmark Type 1 instead, since it's about what benchmark
*runs*, not what viz *computes*. Split TBD when both Type 1s exist. Added to the documentation drift
checklist in [`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md).

### 7.5 Autoscaler-arm matrix + A/B hygiene (2026-08-08)

The variable under test is the **autoscaler**, so the arm is a first-class axis of every scenario,
not a flag:

| Arm | Mechanism | Selects |
|---|---|---|
| **WVA-TA** | WVA controller, ThroughputAnalyzer enabled (alongside saturation) | `guides/workload-autoscaling` |
| **WVA-SAT** | WVA controller, saturation-v2 only | `guides/workload-autoscaling` + analyzer config |
| **KEDA-direct** | no WVA controller; EPP + KEDA `ScaledObject` | `guides/epp-keda-saturation` — **blocked, §5.7** |

`BENCHMARK_REPO_REF` and `BENCHMARK_SPEC` are **derived from this choice** (§2c), never hand-set — so
an arm cannot select an unguarded ref by construction.

**Three known contamination paths that destroy attributability.** All three must be closed before an
A/B across arms means anything:

1. **The scenario file is mutated in place and stays mutated.** `Makefile:611-620` rewrites
   `base_url` with `sed -i.bak` in direct-KEDA mode and removes only the `.bak` — the scenario keeps
   the edit. Run a WVA arm after a KEDA arm from the same scenarios directory and it silently
   inherits the gateway `base_url`.
2. **`benchmark-enable-v2-saturation` rewrites *thresholds* alongside analyzers**, so "turn the
   analyzer on" is not a single-variable change.
3. **Carry-over state between arms** — analyzer memory, vLLM prefix cache, and leftover namespaced
   objects.

Also: the `awk` block at `Makefile:526-539` injects the KEDA bounds by matching the **literal**
strings `periodSeconds: 180` / `periodSeconds: 300`. If upstream changes those defaults the injection
**silently no-ops** and the arm quietly reverts to upstream scaling behavior — same failure class as
(2): a knob that appears set and is not.

### 7.6 The mid-band dwell is a controller-configuration lever, not a workload lever (2026-08-08)

Source: handoff `plan__benchmark-dwell-operating-point.md` (now `.DONE`), an **addendum** to the
capture list behind §7.4 — delivered as a separate file because a sender does not edit a handoff it
has already sent. The coder's own record is `benchmark/session-notes/status/benchmark.md` §17.12.
This section supersedes §7.4.1's *mechanism*; §7.4.1's *goal* still stands.

**The claim.** Raising the offered rate may not move steady-state KV utilization at all. Under a
controller that is tracking, replicas rise with load and per-replica KV is held near whatever the
controller's operating point implies — so in steady state KV is closer to rate-**invariant** than
rate-proportional. It is a **controlled variable**, and the controller is the thing that sets where it
sits.

**Why that is the economical explanation for §7.4.1's own observation.** "No run in any pool has ever
dwelt in 0.3–0.85" is a fact about *configuration*, not about rate:

| Run | KV reached | Why |
|---|---|---|
| 08-07 ladder | 0.67 @ 20 RPS | ThroughputAnalyzer dominated the combine and provisioned **ahead of** saturation ⇒ holds KV low *by construction* |
| arm B | ≈ 0.99 | its `ScaledObject` was capped at **2 replicas** — not because its load was higher |

Neither number is really a fact about the offered rate. So §7.4.1 as written asks the *workload
profile* to do something only the *analyzer configuration* can do.

> **⚠ CORRECTED 2026-08-11 — the goal below was misstated. Not forcing a band; verifying arrival at
> one.** Dean, 2026-08-11: *"we don't have a goal of forcing a band. One of the tests we want is that
> in steady state autoscaling lands eventually with the right size, i.e. in the right band. We can
> measure transition time, but we care more about eventual steady state. Runs must be long enough to
> stabilize. This applies for sat only and for any other analyzer combination."* The (a)/(b) framing
> below still names the real fork (an uncapped SAT-only config vs. a deliberate cap), but its purpose is
> **not** "manufacture a dwell so a slope is fittable" — it is "run long enough, under whichever
> analyzer combination is under test, that eventual steady state is observable at all," transition time
> being a secondary measurement, not the target. Every rung run so far (§ *the sawtooth ran already*,
> below) was too short to test this — that is the actual finding, not a failed dwell attempt.

**The decision — OPEN, Dean's.** The lever is the operating point, and there are two candidates. The
coder explicitly has no standing to choose: both are analyzer/scenario changes, not workload changes.

| Option | Configuration | Steady state | Extra cost | What the run then measures |
|---|---|---|---|---|
| **(a)** | Saturation analyzer alone, **uncapped** — TA off, `maxReplicas` left at 10 | SAT's own scale-up/scale-down watermarks are **0.85 / 0.70**, so its steady state sits *inside* the requested band by design — band and watermarks are nearly the same interval | **none** — no extra requests | SAT's own right-sizing, **not** the combined optimizer's |
| **(b)** | A deliberate replica cap | parks KV wherever you choose | none | **the cap.** Every latency number at a binding cap is a measurement of the cap |

Arm B was already configuration (a), and missed the band **only** because of the replica cap.

**Decision — (a). Dean, 2026-08-11: settled, and the test generalizes beyond SAT-alone.** *"For any
analyzer combination (also for TA only, TA+sat) — we observe real band. Not force it with max/min."*
(a) is the first instance of a general test, not a SAT-specific one: for **every** configuration under
test — SAT-only, TA-only, TA+SAT — the question is whether that configuration's own steady state lands
in the no-action band its own thresholds imply, observed rather than forced. (b)'s deliberate replica
cap is not part of this test at all; it remains legitimate only as a separate, knowingly-chosen
instrument (a known KV level with the autoscaler intentionally out of the loop), never as how the
"does it land in-band" question gets answered. **Not yet derived:** TA's own no-action band, and the
combined TA+SAT band, are not necessarily `[0.70, 0.85]` — that interval is SAT's specifically, from its
two thresholds. Deriving the equivalent band for TA and for TA+SAT is a prerequisite for testing them,
not yet done.

**The sawtooth already ran — this is not a fallback still to try.** `ta_autoscale_dwell.yaml.in`'s two
360 s rungs (20 and 26 RPS) executed in the 2026-08-10 campaign as all three `*-dwell` cells
(`m-satta-dwell`, `m-sat-dwell`, `m-ta-dwell` — confirmed by reading each cell's actual workload spec,
not inferred). **Neither sat-voting cell reached steady state at either rung** — both hit the replica
cap of 10 **twice** (a limit cycle, analyzer-independent; campaign doc Finding 2), not a dwell.
`m-ta-dwell` is unusable (truncated ~360 s of a ~40 min plan). So this result does **not** confirm (a) —
read correctly post-correction, it shows the runs were **too short to test steady-state arrival at
all**, which is the dwell deep-dive's actual starting question (how long is long enough), not evidence
against (a) or (b) either way.

**The same defect applies to §7.4.2, more sharply.** A knee is a property of load **per replica**, and
the autoscaler's job is to keep load per replica *off* the knee. Sweeping offered rate under an active
controller samples the **operating point**, not the curve. `ta_prefill_knee.yaml.in` is not wasted —
per-stage ITL against *measured* concurrency-per-replica is still a valid point at each rung — but the
sharp instrument for a knee is a **fixed replica count with autoscaling off**, which is again a
scenario decision, not a workload one.

**PVC ceiling — a deliberate omission, not an oversight.** A rung above 26 RPS does not fit: 32 RPS ×
300 s is another ~9,600 requests ≈ **5.1 GB** of per-request trace, and the **20Gi** results PVC
cannot hold that beside the two dwell rungs. It is the natural follow-up run **if both rungs read
low**.

**Status of §7.4's three asks.** The coder reports that Dean **approved all three** and that it has
implemented them — two new files,
`hack/benchmark/workloads/inference-perf/ta_autoscale_dwell.yaml.in` and `ta_prefill_knee.yaml.in`.
The planner has **not** independently confirmed that approval, and §7.4 therefore keeps its OPEN
marker. This section is itself the evidence that the asks were not self-contained: 7.4.1's stated
mechanism cannot deliver 7.4.1's stated goal. **What the plan needs from Dean is one line:** confirm
the three asks, and pick (a) or (b) — or accept the quantization fallback as the next run and defer
(a)/(b) until its result is in.

#### 7.6.1 Cold-resume state (2026-08-08)

**Staged and unlaunched.** No cluster action has been taken and no run is proposed. Dean's standing
rule holds: **no run without his explicit approval.**

- **Config staged, not launched:** the two workload files above, on the `benchmark` branch, **local
  only** — that branch is 9 commits ahead of `origin/benchmark` with several dirty paths (§9.1).
- **Four preconditions before the dwell run** (coder's §17.12): reclaim the results PVC to
  **≥14 GB** with `verify_pvc_vs_host.py` **gating** it; confirm the **96Gi** harness pod schedules;
  set the **5-GPU** footprint flag; and run **`post_run_analyze.sh` immediately** after the run — the
  ladder run has no `metrics/processed/wva_*` precisely because that step was not run promptly and
  the controller log is read from a rotating buffer.
- **Restart the controller before each run.** Capacity history is bucket-keyed and was found
  contaminated *across* runs; this is an adopted protocol, not a suggestion.
- **GPU state:** the ladder run's GPUs are released; **one GPU remains held** by the decode replica's
  `minReplicas=1` steady state — a separate open question (coder's §17.8 item 3).
- **T9 gates the per-request trace, applied per-test, not in advance.** Without the gateway log-follower
  applied, every per-request trace is a bet against log rotation (§9.1 T9) — and per §7.4 the routing
  oscillation is invisible without it. **Corrected 2026-08-11:** this is not a standing prerequisite to
  clear ahead of the campaign; it applies as part of the test playbook when an actual test is about to
  run, with no permission scope beyond that run.

**Next steps, in order.**

1. **Dean** — confirm §7.4's three asks (still owed, separate from the (a)/(b) decision below).
2. **(a)/(b) — DECIDED 2026-08-11.** (a), generalized to any analyzer combination, observed not forced.
3. **Dean** — apply the gateway log-follower (T9) **as part of the test playbook when the run actually
   fires**, not as an advance step; otherwise step 4 may yield no per-request trace.
4. **Coder** — satisfy the four preconditions; restart the controller.
5. **Dean** — approve the run. **Coder** — run it, then `post_run_analyze.sh` **immediately**.
6. **SUPERSEDED — the two rungs already ran, and they did not read 0.67 or land in-band.** Both
   sat-voting sawtooth cells hit the replica cap of 10 twice (a limit cycle, campaign 2026-08-10;
   see [`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md) Finding 2)
   — too short to reach steady state at all, not a clean read either direction. (a) is decided
   regardless (step 2), so this step's original branch (confirm rate-invariance → make (a)/(b)
   necessary) is moot; what the dwell deep-dive session actually needs to establish is run duration —
   see `session/handoffs/dwell-deep-dive__handoff.md`.
7. **Only if a longer dwell run still reads outside `[0.70, 0.85]`** (§7.4.1's corrected band, above) —
   the 32 RPS follow-up run, which needs the PVC headroom first.

---

## 8. Decisions (all resolved 2026-07-28)

- **Integration mechanic — `git merge --no-ff`** (preserves exact PR-commit provenance;
  re-integration on PR update is a clean re-merge). Only C #1480 + D #1481 merge onto current
  main; D needs the `engine_v2.go` reconciliation against merged A′ first (rebase, then merge).
- **Tag / image names — CONFIRMED:** git tag `ta-0.9-test-20260728`; image tag `:ta-0.9` on
  `quay.io/deanlorenz/llm-d-workload-variant-autoscaler`. Archive old branch as
  `benchmark-ta3-legacy`.
- **pokprod cleanup — CONFIRMED:** full nuke of `dhl-wva`; fresh namespace `dhl-wva-209` (§6).
- **Ofer handover (decision #7):** Dean runs the Step-0 sanity scenarios himself on the Tier-A
  image. **Once sanity passes, hand the code (image/tag/branch) to Ofer for wider testing.**
  While those runs are in flight, Ofer's KEDA guide + his current-testing alignment is a
  **separate discussion in another session**; when it starts, open a kickoff handoff for it.
  No plan-agent GH contact.

**On Ofer's #1435 (harness-only — verified):** `gh pr view 1435 --json files` shows it touches
**only** `Makefile`, `docs/developer-guide/two-variant-wva-benchmark.md`, `hack/benchmark/*.py`,
`hack/benchmark/scenarios/guides/*.yaml`, and `test/benchmark/scenarios/*.yaml.in` — **no files
under `internal/`, `pkg/`, `cmd/`, or `api/`.** It is a **benchmark-harness change (Tier B)**, not
controller code, so it is **correctly excluded from the code-under-test image**. His controller-side
change lives separately in `biranofer/workload-variant-autoscaler @ feat/two-variant-keda`; Tier A
does not depend on either — it is main + C + D only.

---

## 9. Execution ownership & scope

**Yes — the write-work is a coder's, in the worktrees.** The plan-agent cannot write in code
worktrees (scope boundary), so every git-surgery / build step below is coder work. It is **not one
session** — it spans four worktrees, and every push is gated on Dean's explicit per-push
confirmation (coders never push at all — Dean runs each push after review).

Execution map (order = dependency order):

| # | Worktree | Coder work (local only) | Pushes (Dean, after review) |
|---|---|---|---|
| Phase 0 | `benchmark` | commit untracked runbook/notes/`results/`; rename `benchmark`→`benchmark-ta3-legacy`; create fresh `benchmark` off main locally; `git boidem` archive tag locally | archive tag `archive/benchmark-ta3-legacy` → origin; fresh `benchmark` → origin |
| Phase 1a | `ta-veto-liveness` (D) | rebase D `827c8542`→`11d70a8a` + reconcile `engine_v2.go`/`engine_v2_test.go`/pipeline-doc vs merged A′; message-vs-diff; gates | **none — do NOT push** (would confuse PR #1481 reviewers; rebase-in-place was unnecessary) |
| Phase 1b | `ta-model-level-demand` (C) | rebase C `827c8542`→`11d70a8a` + reconcile `engine_v2.go`/`engine_v2_test.go`/`engine_v2_population_test.go`/2 docs vs merged A′; message-vs-diff; gates | **none — do NOT push** (would confuse PR #1480 reviewers; rebase-in-place was unnecessary) |
| Phase 1c | **new** `ta-testing` | branch off main; `merge --no-ff` C then D; assembled message-vs-diff; gates; `docker-build`; tag `ta-0.9-test-20260728` | branch + tag → fork; image `:ta-0.9` → quay |
| Phase 2 | `benchmark` (fresh) | wire guide `tag:`→`:ta-0.9`; port relevant runbook bits; adopt Ofer's guide | fresh-branch commits → fork |

- Phase 1a/1b were **only** needed to assemble the `ta-testing` integration branch — **not**
  for the PRs themselves (the PRs don't chase main). Merging the un-rebased C/D would have
  sufficed; rebasing the live PR branches in place was avoidable. 1a and 1b are independent
  (parallelizable); 1c depends on both.
- Rebase discipline (CONVENTIONS pre-rebase plan, per-file diff inventory, per-commit
  message-vs-diff) is **mandatory** — the pre-#1483 `interfaces → domain` origin makes silent
  hunk loss a real risk.
- **Launching the coder:** a coder session per worktree (Dean starts Bob in the worktree, or the
  plan-agent spawns via the sanctioned cd+Agent pattern from `plans/` — Dean's call which).
- **Dean / Ofer:** Phase 3 cluster teardown (`dhl-wva`→`dhl-wva-209`); Phase 4 Step-0 sanity
  (Dean); Ofer consumes Tier-A image/tag after sanity passes.
- **CURRENT.md / PR-status:** updated by the plan-agent via `/sync-current` from handoffs — not
  as part of executing this plan.

### 9.1 Tooling track (added 2026-08-08) — all `benchmark` worktree, all local

Phases 0–1 above are done; this is the work the 2026-08-07/08 direction adds. Everything marked
"benchmark coder" is coder work in the `benchmark` worktree, **local only, no pushes** — Dean pushes
after review, per push. Dependency order matters only where stated.

| # | Work | Owner | Section |
|---|---|---|---|
| **T1** | Migrate `7a1b478` + `cfe6088` out of the harness fork into WVA `hack/`, deduping against the files WVA already owns; resolve the clone's uncommitted `output_token_correction.py` drift. Leaves the fork at 2 commits / 3 files, all under `standup/` | benchmark coder | §2b |
| **T2** | Refresh the harness fork's `main` from true upstream; **rebase the two guard commits onto it**; repoint KEDA mode at that ref. **Gates T3.** Cheapest while T1 has those commits open | benchmark coder | §5.7 |
| **T3** | Make the KEDA-direct arm actually run; add it to the arm matrix. Fix the two cosmetic defects in the same Makefile block | benchmark coder | §5.7, §7.5 |
| **T4** | Context-keyed `.env` (`hack/benchmark/env/<context>.env`) + **fail-closed** Makefile guard + the `WVA_ENV_*` assertion triple + arm-derived `BENCHMARK_REPO_REF`/`BENCHMARK_SPEC`; move `benchmark-preflight` onto `benchmark-run`, `benchmark-standup`, `benchmark-run-all`, `benchmark-teardown`, `benchmark-install` | benchmark coder | §2c |
| **T5** | `make benchmark-configure` → `hack/benchmark/configure_env.py` wizard, plus the on-branch `.claude/skills/benchmark-configure/`. The skill explains; it never enforces | benchmark coder | §2c |
| **T6** | The one runbook `docs/developer-guide/benchmark-tooling-runbook.md`, its two link points in `benchmark-guide.md`, and the fold-in of `docs/two-variant-wva-pokprod-runbook.md` | benchmark coder | §5.5 item 4 |
| **T7** | Close the three cross-arm contamination paths and the literal-match `awk` injection | benchmark coder | §7.5 |
| **T8** | Pin `hack/benchmark` Python deps in a tracked requirements file; add a **fresh-checkout acceptance gate** — simulate a clean clone and confirm the documented flow works end to end. This is the technique that caught the `metrics/raw/` loss during the autoscaling-viz migration (8 PASS/7 FAIL from a clone vs 12/4 locally) | benchmark coder | §7.4 |
| **T9** | Apply the gateway access-log follower (`hack/benchmark/gateway-log-follower.{sh,yaml}`) — **CORRECTED 2026-08-11: not standing infrastructure, applied per-test.** Dean: *"T9 should only run with a test, part of the playbook, no extra permissions above an actual test."* The `kubectl apply` runs as **part of the test playbook**, gated to an actual test execution, needing no permission beyond what that run already needs — not a one-time cluster-admin action taken in advance. Still needs Dean applying it (the coder's permission classifier blocks the apply either way), but the *trigger* is "a real test is about to run," not a standing prerequisite to clear once | **Dean, per-test** | §7.4 |
| **T10** | File upstream llm-d-benchmark issues for the two guards — **later**, Dean's call, after T2 has them isolated | **Dean** | §2b |
| **T11** | Dwell-run preconditions for the staged `ta_autoscale_dwell` / `ta_prefill_knee` run: reclaim the results PVC to **≥14 GB** with `verify_pvc_vs_host.py` **gating** it, confirm the 96Gi harness pod schedules, set the 5-GPU footprint flag, **restart the controller** (capacity history is contaminated across runs), and run `post_run_analyze.sh` **immediately** after | benchmark coder | §7.6.1 |

**Scenario decisions still Dean's:** §7.4.1 / §7.4.2 / §7.4.3 (recorded OPEN with a recommendation to
take all three) — **plus the §7.6 operating-point fork, (a) saturation-alone-uncapped vs (b) a
deliberate replica cap, which §7.4.1 cannot be executed without** (or an explicit deferral behind the
§7.6 quantization fallback run) — the §5.5-item-4 fold-and-delete-vs-stub call for the pokprod
runbook, and — as always — approval of any cluster run.

**Not in this plan's scope:** the `benchmark` branch is 9 commits ahead of `origin/benchmark` with
several dirty paths, all local. Whether and when that pushes is Dean's, per push.
