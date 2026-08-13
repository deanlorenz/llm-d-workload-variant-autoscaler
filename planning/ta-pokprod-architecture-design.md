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

   **Enforcement, decided [[D-44]]:** each `.env` names one specific namespace explicitly — it is
   never generic. Before any run, verify the active context's namespace (`oc project` — switching
   projects changes the active context) matches the `.env`'s named namespace exactly; **refuse to run
   on any mismatch**, fail closed, no override. This holds regardless of scope: WVA itself can run
   cluster-scoped or against a different namespace than the workload it serves, but every pokprod run
   in this mission is namespace-scoped for both the llm-d stack and the WVA controller — so the
   single-namespace check is sufficient here and does not need a multi-namespace variant.
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

Benchmarking artifacts previously spread across five unrelated trees with inconsistent tracking. Final
layout, [[D-32]] superseding an earlier `mv`-based two-step design ([[D-5]]/[[D-13]] first proposed a
nested `raw/` subfolder populated by relocating the harness's own output — that intermediate design was
built, then superseded before touching real data, so **only the final shape below is current**):

```
benchmark/
├── tools/ → hack/benchmark         symlink — nothing moves
├── campaigns/<date>/                curated, permanent, TRACKED (legacy shape, see below)
└── runs/<run-id>/                   the harness's own dean-<ts>-<pid> id, written HERE NATIVELY
    ├── config/                      TRACKED — .env used, workload profile, analyzer config,
    │                                  image pin: the reproducible set
    ├── viz/                         TRACKED — figures + coverage, coupled to the run, never mirrored
    ├── REPORT.md                    TRACKED — metrics table + relative links into config/viz/results
    └── results/, logs/, setup/, ... everything else the harness itself writes — UNTRACKED
```

`BENCHMARK_WORKSPACE` points at `benchmark/runs/`, so the harness writes its `<run-id>/` directory
**there directly** — no copy, no move. `.gitignore` is an allowlist, not a nested-folder rule:
`runs/*/*` ignored by default, then `config/`, `viz/`, and `REPORT.md` explicitly un-ignored. This
works for every user out of the box — the design it replaced used the glob `dean-*/`, which only
matched one username, so another user's run showed as untracked clutter.

**Figures live with their results, not as copies.** If a result is deleted, its figures and coverage
data delete with it — no separate mirror to keep in sync. [[D-13]] **RECONCILED 2026-08-12** — the
layout above is now built and populated: the 7 pre-existing 2026-08-10 campaign directories were
migrated into `runs/<id>/` (56 tracked files, `config`+`viz`+`REPORT.md`), and the parallel cell-keyed
`session-notes/campaign-viz/` mirror this section previously flagged as an unreconciled duplicate is
now **DEPRECATED** and deleted, verified byte-identical against the canonical copies first. [[D-27]]

**Three tools built to complete this design**, [[D-33]]: the `tools/` symlink itself; a `REPORT.md`
generator (`write_report.py`, wraps the existing metrics-table code with relative links, computes
nothing itself); a conservative pruning script (`prune_run.py`, dry-run by default, only ever removes a
file when its hash matches something already preserved elsewhere — never touches `metrics/raw/` or
`results/*/logs/`, since those are exactly where the per-request discovery work (§6) found real signal).

**Live-cluster verification is still the one standing gap, across the whole effort.** Every piece —
the `runs/` relocation, the `.gitignore` allowlist, the three tools, T9's wiring (§6) — is verified
structurally (dry-run renders, credential scans, YAML well-formedness, scratch-tree diffing) but **none
of it has been exercised against a real `benchmark-run` invocation or a live cluster.** Treat this as
standing risk until a real campaign run confirms the mechanism end to end, not resolved by any
individual verification pass.

**Convention for a campaign/run summary:** a short metrics table, then a `<details>` block of
relative-path figure embeds (from upstream commit `cde8646c`, #947). **Rejected:** filing results under
`docs/developer-guide/` — that placement's own precedent (#947) was deleted five months later as
"outdated." A dated results directory is inherently historical and Type-4 docs must track current code,
so that placement guarantees rot.

---

## 5. Configuration contract

`.env` handling is fail-closed. [[D-6]] **SETTLED 2026-08-10, superseding the naming below** —
[[D-31]] — Dean settled a fuller design with the coder while scoping an A/B run; it changes the naming
scheme and several other particulars. Current contract:

1. Benchmark targets must not run without a `.env` — enforced unconditionally, in one internal
   `benchmark-guard` target every other target calls (same pattern as the existing
   `benchmark-standup-shared` → `benchmark-preflight` gate) — **not a tiered automation model.**
2. **Naming: `X.env` where `X` is any name, not `<context>.env`.** [[D-31]] The context is declared
   *inside* the file and verified against the live one — this is better than a context-derived
   filename because the name can describe the campaign (`armA.env`, `pr2-ab.env`) rather than being
   hostage to a context string, and verification becomes explicit rather than filename-implicit.
   `BENCHMARK_ENV=<name>` → `hack/benchmark/<name>.env`. Unset is a hard error, not an empty default —
   closes the silent-empty-namespace hole from an unset `BENCHMARK_NAMESPACE ?=`.
3. The file declares `KUBE_CONTEXT`; declared context must **match**
   `kubectl config current-context` or the guard refuses, naming both. Required keys must all be
   present — fail-closed, listing every missing key at once, not one at a time.
4. `BENCHMARK_SPEC`/`BENCHMARK_HARNESS` are validated as a **pair** — the harness belongs to the spec
   of a run, not to the Makefile (it's whatever the scenario's `harness.name` declares), so an
   override of one without the other is the inconsistent state to catch.
5. `PROMETHEUS_URL` is **derived** from the cluster by default, not merely guarded; an override is
   correctness-checked (does it actually resolve to the right target?) and complained about if so —
   stronger than warn-and-proceed, because a wrong collection target yields plausible-looking numbers
   from the wrong place.
6. **One uniform override policy, not a tiered one:** every field may be overridden; every override
   complains loudly; the `.env` remains the reproducible record of what actually ran. Applies
   uniformly to scenario, harness, timeouts, and any other flag — Dean, verbatim: *"I prefer it is
   clear what actually ran... complain loudly. Still override is probably OK."*
7. `UNSAFE=true` is a **first-class escape hatch, not an oversight** — it downgrades every refusal to
   a loud warning naming which guard was bypassed. The guard's job is to make the safe path the
   default and the unsafe path deliberate, not to prevent it. Dean: *"if the user insists on UNSAFE
   mode they can override whatever they want."*
8. A wizard (`make benchmark-configure`) — **deferred, not on any critical path**, Dean's design
   preserved so it isn't lost: automatically directed-to on a new context with no `.env`; asks for
   critical info including the pinned image; applies the safest protections while warning of
   implications; may let a user run NS-level (rarely cluster-level) setup once, explicitly and with
   approval by default — only the WVA tests *on top* of that setup are automated.
9. An on-branch skill that explains but never enforces (a skill only helps Claude Code users; the
   Makefile guard and the wizard must stand alone).

**Arm-derived refs.** `BENCHMARK_REPO_REF` and `BENCHMARK_SPEC` are derived from the autoscaler arm
under test, never hand-set — an arm cannot select an unguarded ref by construction.

⚠️ **Open, unresolved:** whether one kube context can legitimately map to multiple namespaces — if so,
the context-keyed assertion (item 3) needs to tie to one target namespace explicitly, not assume a 1:1
mapping.

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
