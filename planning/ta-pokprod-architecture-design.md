# TA on pokprod — Architecture (Type 1)

**Status:** current. **Type:** design — durable contracts, frozen unless architecturally replanned.
**Scope:** how the WVA-under-test and the benchmark harness that tests it relate, and the standing
safety/configuration rules that bind every phase of work on the shared pokprod cluster.

**Companion docs:** [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (Type 3, phased
execution) · [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) (Type 3, live scenario
work) · [`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger — every `[[D-nn]]` reference
below is fetchable there by `grep -n '^## D-nn'`).

---

## 1. Two-tier separation

The code being tested and the benchmark that tests it are two independent things, kept apart even
locally. [[D-1]]

**Tier A — code-under-test.** A clean integration branch/tag/image, reproducible and shareable via
Dean's fork. Lives in its own dedicated code worktree, never the benchmark worktree. Fork-only, never
upstream — the integration itself is test-only and never opened as an upstream PR (its constituent PRs
keep their own PR life). Changes only flow in from the owning PR worktrees, never hand-edited in the
benchmark tree.

**Tier B — benchmark harness.** Dean's, fork-only, not code. A `benchmark` branch + the
`llm-d-benchmark` guide framework, referencing the Tier-A image by `repository:tag` — the *only*
coupling between the tiers. Runbook + `results/` live here only, never pushed upstream.

Ofer pulls Tier A only, never Tier B.

---

## 2. Shared-cluster safety invariants

pokprod is a shared OpenShift cluster (Dean and Ofer both hold admin), so an unscoped or defaulted
command can silently land in the wrong namespace or mutate cluster-global state. [[D-2]]

1. **Operate only in the target namespace set for the benchmarking config in use** — a property of the
   `.env`/config a run is invoked with, never of who is running it, and never inferred from a
   current-context default. When a new context/namespace pair is established, it must be confirmed
   explicitly with the user before use. [[D-15]]
2. **Every environment value comes from an explicit `.env`** — namespace, model, instance, image,
   accelerator, URLs. This binds any invocation of the benchmark Makefile targets, structurally, not
   as a matter of personal discipline. [[D-16]]
3. **Any teardown requires the operator's explicit approval for that specific action**, and an explicit
   namespace arg. This holds for anyone using the benchmark targets, scoped to the namespace explicitly
   set for benchmarking — never anything outside it. [[D-17]]
4. **Never change any cluster-global / out-of-namespace setting** — Prometheus/monitoring config, router
   control plane, gateway settings, or anything cluster-scoped. Before applying any kustomize/helm
   manifest, verify it creates or mutates nothing cluster-scoped or outside the target namespace; if it
   does, stop and surface it rather than applying.

**The safety net has three independent levels**, only two of which are mechanical: [[D-3]]

| Level | Layer | Enforced by |
|---|---|---|
| L1 | operator discipline — explicit `-n`, no teardown without approval | the human, and this section |
| L2 | this repo's Makefile targets, scripts, and preflight | the WVA branch |
| L3 | the harness fork's presence-gates on cluster-scoped standup steps | the harness fork |

**The L3 hazard is inverted from the obvious one.** A presence-gate skips because a shared object
*already exists*; absence therefore reads as "not installed yet — go install it," so a deleted
precondition silently converts a safe standup into a destructive one. L3 must be verified present in
the code that will actually execute, not assumed.

---

## 3. Two-fork contract

Two forks back this mission, with non-overlapping contents. [[D-4]]

| Fork | Contains | Lifetime |
|---|---|---|
| WVA (`deanlorenz/llm-d-workload-variant-autoscaler`) | tools, Makefile, `hack/`, scenarios, workload profiles, docs | temporary measure — expected to move upstream |
| harness (`deanlorenz/llm-d-benchmark`) | **guards only** — presence-gates for cluster-scoped operations upstream's standup would otherwise perform | longer-lived; guards become upstream issues later |

**Rule:** anything in the harness fork that is not a guard belongs in WVA `hack/`. The harness fork
makes the tools installed on the cluster *safe*; it is not where tools live.

**Ownership boundary:** the WVA fork's tooling changes stay on Dean's fork for now — not upstream —
until Dean scopes what belongs as issues/PRs on the public repos. [[D-14]]

---

## 4. Artifact tree — one root, results persisted in git

Benchmarking artifacts previously spread across five unrelated trees with inconsistent tracking. Target
layout, one root, lifecycle visible in the directory name: [[D-5]] [[D-13]]

```
benchmark/
├── tools/ → ../hack/benchmark      symlink — nothing moves
├── campaigns/<date>/                curated, permanent, TRACKED (legacy shape, see below)
└── runs/<run-id>/                   ONE run, everything about it, one lifecycle
    ├── config/                      the reproducible set: .env used, workload profile,
    │                                  analyzer config, image pin
    ├── raw/                         harness output, scrapes — large, disposable
    └── viz/                        figures + coverage — coupled to raw/, never mirrored
```

`BENCHMARK_WORKSPACE` points at `benchmark/runs/` (not a per-username glob — the prior ignore rule was
`dean-*/`, which only matched one user). Raw runs stay untracked (GB-scale, and historically
token-bearing — see §5); the tracked, reproducible persistence is the `config/` + curated `viz/`
material.

**Figures live with their results, not as copies.** If a result is deleted, its figures and coverage
data delete with it — no separate mirror to keep in sync. [[D-13]] **RECONCILED 2026-08-12** — the
target layout above is now built and populated: the 7 pre-existing 2026-08-10 campaign directories were
migrated into `runs/<id>/{config,raw,viz}/` (56 tracked files), and the parallel cell-keyed
`session-notes/campaign-viz/` mirror this section previously flagged as an unreconciled duplicate is
now deleted, verified byte-identical against the canonical copies first. [[D-27]]

**Live-cluster verification is still the one standing gap.** The migration and T9's wiring (§6) are
both verified structurally (dry-run renders, credential scans, YAML well-formedness) but neither has
been exercised against a real `benchmark-run` invocation or a live cluster.

**Convention for a campaign/run summary:** a short metrics table, then a `<details>` block of
relative-path figure embeds (from upstream commit `cde8646c`, #947). **Rejected:** filing results under
`docs/developer-guide/` — that placement's own precedent (#947) was deleted five months later as
"outdated." A dated results directory is inherently historical and Type-4 docs must track current code,
so that placement guarantees rot.

---

## 5. Configuration contract

`.env` handling is fail-closed, keyed per kube context: [[D-6]]

1. Benchmark targets must not run without a `.env` — enforced unconditionally in the Makefile.
2. One `.env` per kube context, discovered by filename (`hack/benchmark/env/<context>.env`). If absent
   for the current context, targets refuse and point at the wizard.
3. An embedded assertion triple — `WVA_ENV_CONTEXT` / `WVA_ENV_SERVER` / `WVA_ENV_NAMESPACE` — checked
   against the live context before anything runs. The filename gives discovery; the triple gives
   correctness.
4. A wizard (`make benchmark-configure`) that confirms every choice, warns on dangerous ones, and
   materializes an explicit, auditable `.env` — deterministic, agent-free.
5. An on-branch skill that explains but never enforces (a skill only helps Claude Code users; the
   Makefile guard and the wizard must stand alone).

**Arm-derived refs.** `BENCHMARK_REPO_REF` and `BENCHMARK_SPEC` are derived from the autoscaler arm
under test, never hand-set — an arm cannot select an unguarded ref by construction.

⚠️ **Open, unresolved:** whether one kube context can legitimately map to multiple namespaces — if so,
the context-keyed `.env` needs to tie to one target namespace explicitly, not assume a 1:1 mapping.

---

## 6. Bearer-token hazard — mechanism understood, rotation still owed

Harness pods embed the operator's live kube context (upstream `llm-d-benchmark` behavior, not a WVA-fork
addition) so they can talk to the cluster from inside it. This means every campaign run carries a live
bearer token, in `environment/context.ctx` per cell. [[D-9]] [[D-27]]

**2026-08-11:** the then-known copies (`run/*.yaml` manifests) were removed and verified clean
tree-wide; token refreshed. **2026-08-12, corrected:** the same credential persists in a *different*
file per cell — `environment/context.ctx`, untouched by the 08-11 removal since that targeted a
different manifest. It never reaches git (verified via `git add --dry-run` plus three independent
credential grep passes across the full migrated set, zero hits), but it remains on disk and **rotation
is still owed** — the substance of the ask is unchanged from [[D-9]], only the file path was wrong.

**Not fixed, still:** the mechanism recurs on every future run regardless of which file currently
carries it — a real fix (e.g. a scoped service-account token instead of embedding the operator's
personal one) is upstream harness work, not scheduled here. Anyone extending this architecture with a
new artifact-persistence path must re-verify it doesn't carry a live credential forward, and should not
assume the specific file name found so far is the only place to check.
