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

- [1. Where we are (findings)](#1-where-we-are-findings) — L34:66
- [2. Architecture — two-tier separation](#2-architecture--two-tier-separation) — L68:104
- [3. Phase 0 — Preserve (zero-loss)](#3-phase-0--preserve-zero-loss) — L106:132
- [4. Phase 1 — Code-under-test branch + image](#4-phase-1--code-under-test-branch--image) — L134:176
- [5. Phase 2 — Fresh benchmark branch + adopt Ofer's harness](#5-phase-2--fresh-benchmark-branch--adopt-ofers-harness) — L178:212
- [6. Phase 3 — Clean stale pokprod](#6-phase-3--clean-stale-pokprod) — L214:230
- [7. Phase 4 — Scenarios + small e2e](#7-phase-4--scenarios--small-e2e) — L232:270
- [8. Open items / decisions remaining](#8-open-items--decisions-remaining) — L272:288
- [9. Execution ownership & scope](#9-execution-ownership--scope) — L290:end

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
4. **Rename the old branch first, then archive** (Dean's rule — free the name `benchmark` for the
   fresh branch). Proposed: rename `benchmark` → `benchmark-ta3-legacy`, then `git boidem`
   (tag `archive/benchmark-ta3-legacy`, push tag to origin, delete local). The snapshot tag is
   the permanent recovery handle. **Fork only — never upstream.**

---

## 4. Phase 1 — Code-under-test branch + image

Goal: one clean, reproducible branch/tag/image = current main (has A + A′) + C #1480 + D #1481.

**Prereq — the two open PRs on current main.** C and D were forward-rebased onto post-#1478 main
already; but #1479 (A′) merged *after* that, so **D still needs a rebase onto current tip and an
`engine_v2.go` reconciliation against the now-merged A′** (D and A′ shared that file). C is
independent. ⚠️ **Cross-rebase hazard persists:** these PRs originated on `55e24be9`, before
#1483's `interfaces → domain` rename; three-way merges can **silently drop hunks**. CONVENTIONS
pre-rebase discipline is mandatory:
- Pre-rebase plan per branch (coder records in `plans/session/status/<branch>.md`).
- Per-file diff inventory + per-commit message-vs-diff check after each rebase.
- Both PR branches keep their own upstream life — this rebase is needed for them regardless.

**Integration branch** (test-only; fork-only; **never** an upstream PR):
1. Branch off **current upstream main** in its own worktree, name e.g. `ta-testing`.
2. Apply the two open PRs. With A′ now in main the ordering constraint is gone; both C and D
   layer cleanly on current main. Cherry-pick / merge the rebased commits; run gates after each.
3. **Message-vs-diff check on the assembled branch** (the interfaces→domain move makes silent
   hunk loss a real risk). Gates: `make test`, `gofmt -l`, `make lint`, `go build ./...`.
4. **Tag** the integration commit for reproducibility, e.g. `ta-0.9-test-20260728` (immutable
   checkout point — this is what "where did we get the code" resolves to).
5. **Build & push the image** to `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9`
   (replaces the old `:ta3`). Record the digest in the runbook (Tier B).
6. **Push branch + tag to origin (`deanlorenz` fork)** for Ofer — subject to Dean's explicit
   per-push confirmation; **never to upstream**.

**Deliverable to Ofer:** branch `ta-testing` + tag `ta-0.9-test-20260728` + image `…:ta-0.9`
(+ digest), all on Dean's fork / quay. He points his guide `tag:` at it, or checks out the tag.

---

## 5. Phase 2 — Fresh benchmark branch + adopt Ofer's harness

Goal: a fresh Tier-B harness that follows llm-d-benchmark guides and Ofer's KEDA path, decoupled
from the stale TA code.

1. **Study Ofer's actual current setup first** (read-only). His harness is `biranofer/llm-d-benchmark`
   @ `feat/multi-variant-benchmark`; his WVA-side change is `biranofer/workload-variant-autoscaler`
   @ `feat/two-variant-keda` (#1435). Determine: (a) what the KEDA-based two-variant guide needs
   from the WVA controller (ScaledObjects vs the runbook's VA+HPA); (b) which of his changes are
   unmerged and therefore only in his fork; (c) the exact image/tag/config knobs the guide exposes.
2. **Create the fresh `benchmark` branch** off current main (name freed in Phase 0). **Reuse the
   existing `benchmark/` worktree path** — swap its checked-out branch rather than adding a new
   worktree, so the `wva.code-workspace` folder entry ("benchmark") keeps working with **no VSC
   reconfiguration**. Preserve the untracked `benchmark/.claude/settings.json`. (Minor cleanup:
   the workspace has a stale `git push origin thpt-analyzer` auto-approve — drop when convenient.)
3. **Wire the harness to Tier A:** point the guide's `tag:` at `…:ta-0.9`. Keep the embedded
   `llm-d-benchmark` clone on (or rebased onto) Ofer's `feat/multi-variant-benchmark` so Dean and
   Ofer run the same scenario definition.
4. **Port only the still-relevant runbook bits** — environment/standup/RBAC/signals — dropping the
   `:ta3`-specific and VA+HPA-specific steps that Ofer's KEDA path supersedes. Runbook + `results/`
   committed on this branch, **fork only**.
5. **Fallback noted in the runbook:** if the KEDA path fails, the archived VA+HPA runbook
   (`archive/benchmark-ta3-legacy`) is the proven recovery path.

**Separation invariant to state in the runbook:** the controller under test is always the Tier-A
image/tag; if it must change, the change is made in a code worktree (PR branch) → re-tag → re-image
→ update `tag:` here. The benchmark branch never carries WVA controller source edits.

---

## 6. Phase 3 — Clean stale pokprod

Goal: remove 2026-06-15 leftovers so old signals don't contaminate new runs. **Cluster-side —
Dean or Ofer runs; needs cluster access. Plan-agent does not execute.**

Per runbook §12 teardown (project `dhl-wva`):
- `llmdbenchmark … teardown -p dhl-wva` (helm releases + variants).
- `oc delete podmonitor wva-variant-relabel-decode wva-variant-relabel-decode-v2 -n dhl-wva`
- `oc delete deploy wva-loadgen -n dhl-wva`
- `oc delete role/rolebinding wva-supplemental-hpa-keda -n dhl-wva` (if used)
- Free GPUs: `oc scale deploy/<variant> -n dhl-wva --replicas=0` for any lingering variants.

**Decision needed (see § Open items):** full teardown vs. keep standing infra (gateway/EPP).
Confirm the `dhl-wva` project is disposable before deleting. `git status` / inventory the cluster
namespace first; do not delete what you cannot re-create from §§1–9.

---

## 7. Phase 4 — Scenarios + small e2e

Goal: **simplest-first.** Confirm the basic scale signal works end-to-end on pokprod *at all*
before any TA-isolation. Dean's guidance: **we have never reliably gotten the scale signal** —
even the 2026-06-15 "scale-up captured" (§12) was sat_v2-driven and the runbook itself (§14) says
a clean basic scale-up was not achieved. So treat the plumbing as **unproven** and start there.

**Step 0 (do first) — a few basic e2e on pokprod, simplest possible.** With the Tier-A image
deployed: drive a simple constant→stepped load and confirm the whole chain moves —
load → `wva_desired_replicas` rises → HPA `REPLICAS` follows → pods actuate. One variant, min=1,
hold each step ≥6 min (autoscale lag ~2 min). This is the "does anything scale" gate; nothing
below is meaningful until this is green and reproducible. Mirror `test/e2e/` load drivers
(§14.1); custom in-cluster loadgen (runbook §13.2) is the reliable fallback if guidellm delivers
0 load again.

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

---

## 8. Open items / decisions remaining

- **Integration mechanic:** with A + A′ merged, only C #1480 + D #1481 stack on current main —
  confirm cherry-pick vs merge; D needs the `engine_v2.go` reconciliation against merged A′.
- **Tag / image names:** proposed git tag `ta-0.9-test-20260728`, image tag `:ta-0.9`. Confirm.
- **pokprod cleanup depth:** full teardown vs keep standing gateway/EPP/controller. Confirm
  `dhl-wva` is disposable; decide whether a fresh namespace (new BASENAME) is cleaner than reusing.
- **Ofer sync:** short alignment on his KEDA guide before Phase 2 (what the guide needs from the
  controller; which of his changes are fork-only). Dean coordinates — no plan-agent GH contact.

---

## 9. Execution ownership & scope

- **Plan-agent (now):** authored this doc only. No file edits beyond it; no GH posting; no cluster
  or git-surgery actions.
- **Coder (later, in a code worktree):** Phase 0 commit/rename/archive, Phase 1 rebases +
  integration branch + tag + image build, Phase 2 fresh branch + harness wiring. Each under its
  own worktree scope; rebase discipline (message-vs-diff) mandatory; **no push without Dean's
  explicit per-push confirmation; never to upstream.**
- **Dean / Ofer:** Phase 3 cluster teardown; Phase 4 runs; Ofer consumes Tier-A image/tag.
- **CURRENT.md / PR-status:** updated by the plan-agent via `/sync-current` from handoffs — not
  as part of executing this plan.
