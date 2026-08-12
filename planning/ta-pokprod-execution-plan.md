# TA on pokprod — Execution Plan (Type 3)

**Status:** current. Phases 0–3 DONE; Phase 4 core scenarios mostly DONE, one fix still outstanding
(§5.4, T12); tooling track (§7.1 below) in progress. **Scope:** internal testing/ops; nothing here is
upstream-bound. **Author role:** plan-agent.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md) (Type 1 —
the durable contracts this plan executes against) · [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md)
(Type 3, the live scenario-design surface — dwell, band derivation, coverage matrix) ·
[`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger — `[[D-nn]]` fetchable by
`grep -n '^## D-nn'`).

> Hard constraints (Dean, 2026-07-28): never push to `upstream`; runbook + results are Dean's fork
> only; Ofer consumes code only (image/tag/branch); no GH posting by the plan-agent.

---

## 0. Starting state (captured 2026-07-28, historical)

**Ofer's fork identity — a durable fact, referenced throughout this mission.** Ofer = `biranofer`. His
WVA-side code fork is `biranofer/workload-variant-autoscaler` (no `llm-d-` prefix), branch
`feat/two-variant-keda` = upstream PR #1435 (two-variant benchmark, VA+HPA → KEDA ScaledObjects). His
benchmark harness fork is `biranofer/llm-d-benchmark`, branch `feat/multi-variant-benchmark` (unmerged
as of this capture). Not everything of his is merged — his fork is where he runs his own current
tests, and it's reference-only for this mission, never copied verbatim (architecture doc §1).

**The `benchmark` branch was stale at mission start.** Forked from an old main commit (~Jun 11), 105
commits behind current main at the time; its ~35 commits over that base were TA/multi-analyzer code
that had already merged into main independently — duplicate history, not work to preserve. The only
genuinely unpreserved work was untracked (a runbook, harness notes, three `results/` directories, and
local patches in the embedded harness clone) — captured in Phase 0 below.

**TA 0.9 PR status at mission start:** two of four TA-0.9 PRs (devguide, registration-safety) had
already merged to upstream main; the remaining two (model-level-demand, veto-liveness) were open and
needed only a forward-rebase, not the four-PR stack originally anticipated — see Phase 1 below.

**The runbook's own prior conclusion, carried forward as this mission's headline open question:** an
earlier claim that "TA drives scaling" was itself retracted by controlled testing — saturation-v2 plus
the cost-aware optimizer was shown to be the actual driver, with TA on-vs-off making no decision
difference. The goal this mission has never yet achieved: a clean test where TA *itself* drives a
decision saturation-v2 would not have made on its own. Tracked in Phase 4, §5.2 below.

---

## 1. Phase 0 — Preserve (zero-loss) — DONE

Immortalized the pre-branch-surgery state before any git rewrite. Untracked artifacts (runbook, harness
notes, `results/`, embedded-clone patches) committed onto the old `benchmark` branch, which was then
renamed `benchmark-ta3-legacy` and tagged `archive/benchmark-ta3-legacy` before a fresh `benchmark`
branch was created off current main. Sequence mattered — you cannot delete a branch checked out in its
own worktree, so rename-then-create-fresh-then-archive, in that order.

## 2. Phase 1 — Code-under-test branch + image — DONE

Goal: one clean, reproducible branch/tag/image = current main + the two then-open PRs (#1480, #1481).
Both PRs needed only a forward-rebase onto current main (their prerequisite PR had since merged) — they
did **not** need the in-place rebase-of-live-PR-branches that was initially (incorrectly) performed;
merging them un-rebased onto a fresh integration branch would have sufficed, and structural git ops on
live PR branches should not recur without Dean's consultation first.

**Delivered to Ofer:** branch `ta-testing`, tag `ta-0.9-test-20260730` (refreshed once, 2026-07-30,
after two more upstream PRs merged — #1502 and #1503 — onto the same C/D base; the original tag
`ta-0.9-test-20260728` is preserved as history, nothing lost by moving the branch to the new tip;
`origin/ta-testing` was already at the new tip independently, so only the tag needed a plain
non-force push — tag/image both pushed with Dean's authorization), image
`quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` (digest `sha256:80dec0e9…`). A stale
`origin/ta-testing` at the pre-refresh tip was flagged as a non-urgent cleanup, not actioned.

**Image currency, as of 2026-08-07:** use `:ta-0.9-anchor-20260807` (built from `main@d5d58640`) —
**not** `:ta-0.9-anchor-20260806`, which predates a post-merge fix (`a38d7b73`) correcting three defects
live in the newly opt-in TA path (a phantom role bucket suppressing scale-up, a silent QM-refusal
false-healthy state, and a scale-to-zero misread on a held variant). Verify image provenance by
grepping the extracted `/manager` binary for the string `OptimizationRefused` (0 in `:ta-0.9`/
`:ta-0.9-anchor-20260806`, 4 in `:ta-0.9-anchor-20260807`) — the Dockerfile sets no git-revision label,
so this is the only reliable provenance check.

**Cross-PR test-signature coupling, found during integration:** a textually-clean merge hid a semantic
conflict — one PR added a parameter the other PR's new whole-file test called with the old signature.
Fixed locally; flagged that whichever of the two source PRs merges to upstream *second* will hit the
identical break when rebased, and neither PR's own CI catches it beforehand.

## 3. Phase 2 — Fresh benchmark branch + KEDA harness — DONE (KEDA arm blocked separately)

Adopted PR #1435's WVA-side KEDA wiring as the concrete starting point, then parametrized every
environment-specific value to an explicit `.env`. The harness landed and has run twice (single-variant);
two-variant is built but unrun.

**What was adopted (10 files, all Tier B):** `add_variant.py` (renamed since to
`configure_variants.py` — a coder grepping the old name will find nothing), the two-variant scenario
guide, a new single-variant sat-V2 scenario, two new workload profiles, the KEDA-path doc rewrite, and
Makefile plumbing for the KEDA path. Creates no cluster-scoped objects — every object it makes is
namespaced.

**Hardcoded values parametrized:** accelerator name, image repos/tags, namespace, model, chart
versions — all moved to `.env`, no defaults, no inferred values. Full mapping is in the branch's own
`.env.sample`, not restated here.

**No-op dry-standup validation gate:** a `--print-only`/`--dry-run` mode emits the generated manifests
without applying; `kubectl apply --dry-run=client` / `kustomize build` / `helm template` validate them
with zero cluster contact. This phase's acceptance gate — no `oc apply` without `--dry-run` runs.
`python -m py_compile` / lint on the scripts and a `yaml`-validate pass on every scenario complete the
gate. **Residual-hardcode check** (must return zero matches outside `.env.sample` — see [[D-25]] for
the exact command): `grep -rn 'NVIDIA-H100\|nightly-d6d39be4\|0\.8\.0-rc5\|unsloth/Meta-Llama\|\bbiran\b\|v0\.14\.0' hack/ test/ docs/`.

**Branch/worktree wiring:** the fresh `benchmark` branch reused the existing `benchmark/` worktree path
(swap the checked-out branch, don't add a new worktree) so the VSCode workspace folder entry keeps
working with no reconfiguration. Documentation consolidation for this phase: see the doc-consolidation
decision, [[D-8]], in the architecture doc's cross-references — the runbook fold-in is tracked as an
open item there, not repeated here. **Fallback path, noted in the runbook:** if the KEDA path fails,
the archived VA+HPA runbook (`archive/benchmark-ta3-legacy`, §1 above) is the proven recovery path.

**⚠️ The KEDA arm within this phase is BLOCKED, not part of what's DONE.** Three verified blockers —
see [[D-7]] — gate it as a prerequisite, tracked in the tooling track (§4, T2/T3) below, not
parallelizable with using the arm.

## 4. Phase 3 — Clean stale pokprod + controlled-setup methodology — DONE

**Methodology (Dean redirection, supersedes an earlier full-standup/full-teardown framing):**
our-namespace-only, select exactly the safe steps, never a full teardown. Reuse shared cluster infra
(Prometheus, KEDA, the router control plane) — never install or reconfigure it. `standup -s/--step`'s
comma-list/range selector is sufficient to select exactly the needed namespace+WVA+modelservice(+EPP)
steps and skip the one genuinely cluster-scoped admin step — no fork patch is required for the
controlled flow itself.

**Deploy-shape hazard classification, corrected once live (2026-07-30):** an initial classification
skipped step 08 (per-model InferencePool+EPP deploy) alongside the genuinely cluster-scoped step 02,
conflating it with cluster-scoped "router control plane" language. Step 08's actual payload is a fully
namespace-scoped Helm release — skipping it hangs step 09's wait sub-step for the full 25-minute
timeout, because step 09 waits on the InferencePool step 08 would have created. **Live step list:**
03(patched), 04, 05, 07(patched), 08, 09 (+00 benign). Skip 02 only. Never teardown.

**The four genuinely-unconditional shared writes, verified in code (not dry-run — dry-run over-reports
writes, since every presence-probe returns empty in dry-run mode), all confirmed no-op on pokprod
specifically, one required a patch regardless:**
1. **step_03 `_apply_monitoring`** — `oc apply` on the `cluster-monitoring-config` ConfigMap in
   `openshift-monitoring`. No "already-enabled?" gate in the harness's own code; a wholesale replace
   would clobber any other key an admin had set. Verified: pokprod's existing ConfigMap has exactly
   the one key this write sets, so the render is identical — no-op *here*, but patched anyway since
   the underlying no-gate behavior isn't safe as a general practice.
2. **step_03 thanos-querier `ClusterRole` apply** — fires whenever the Prometheus CA cert is
   extractable (i.e. whenever the operator has admin). Verified: the ClusterRole already exists,
   not helm-owned — a reconcile no-op.
3. **step_02 SCC bindings / CRD installs** — moot; step_02 is skipped via `--step` regardless.
4. **step_07 gateway-provider re-apply** — installs istio-base+istiod cluster-wide, with **no
   presence gate at all** (unlike step_02's equivalent, which self-skips). Verified: istiod is
   already running and the GatewayClass is already `Accepted` — a live run without a gate would
   `helm upgrade --install` onto the shared, already-running control plane. **The one genuinely live
   hazard**, not belt-and-suspenders.

**Fork patches, committed and pushed to `origin/wva-ta-benchmark`** (fail-safe "skip only if already
present," mirroring step 02's own pattern): commit `e88b882` presence-gates writes 2 and 4 above (the
step-07 gateway-provider apply and the thanos ClusterRole apply) — eventual upstream candidates, once a
live run proves them out, not a current priority. Commit `963bb00` presence-gates write 1 (the
`cluster-monitoring-config` replace) — **fork-only by design, will never go upstream**, since it exists
to protect this specific shared-cluster testing, not as a general library improvement.

**What actually happened, 2026-07-30, Dean-approved:** the namespace cutover ran via a simpler path
than the originally-planned `llmdbenchmark teardown` — a plain `oc new-project dhl-wva-209` +
`oc delete project dhl-wva` (both namespace-scoped, no cluster-global impact) removed all 2026-06-15
leftovers in two commands instead of the itemized per-resource cleanup originally planned. Closes Phase
3; §5–6 below (Phase 4) now govern the live standup.

**Known non-blocking cleanup item, found during the first real standup:** the `.env`'s
`VLLM_IMAGE_REPO/TAG` pre-existing default resolves to `docker.io/vllm/vllm-openai:v0.14.0` —
`AGENTS.md` discourages `docker.io` for e2e work. Fine for a one-off benchmark run; tracked as a
cleanup item, not a blocker.

## 5. Phase 4 core — Scenarios + small e2e — DONE

### 5.1 Longer-term goals (per Dean, still the standing direction)

The eventual end-user deliverable must not depend on Dean's fork — it should enumerate the specific
safe `--step`s and run standard public `llm-d-benchmark`. Dean's fork is a testing safety net only; its
patches never become part of the shipped path. Three carried-forward goals: (1) Ofer running with the
WVA-under-test image is already achievable today via the `.env` seam, no code change needed; (2) an
end-user TA guide, in the spirit of the existing WVA-with-KEDA guide on `llm-d/llm-d`; (3) a Makefile
target + setup env that lets an end user safely test TA using public benchmark code with an explicit
safe `--step` list. Sequencing note: the two-variant scenario is not yet in public `llm-d-benchmark` —
it lives only on Ofer's fork — so the fully public end-user path is blocked on that landing upstream
first; this is a scheduling concern for whoever owns that upstream PR, not resolved here.

**A finding that bears directly on goal (3), confirmed by code (2026-07-30):** the scenario's
`gateway.className: istio` is a scenario literal, never cluster-detected — there is no detection layer
anywhere in the harness that probes the cluster's installed gateway provider and picks accordingly. It
happens to match pokprod by construction (the scenario was authored against a cluster that also runs
istio), not by inference. So the public-code end-user target must either (a) document the prerequisite
explicitly — the target cluster must already run the gateway provider the scenario names — or (b) make
`gateway.className` a required `.env`/CLI input rather than a scenario constant, which is the more
correct fit alongside a config-consolidation goal (variant-count + all config in one yaml). No code
change is needed to *use* this today — `--gateway-class` already exists as an override.

### 5.2 Step 0 — basic e2e sanity — DONE, signal confirmed

Goal was simplest-first: confirm the basic scale signal works end-to-end on pokprod at all, since it had
never been reliably observed before this mission (even the earlier "scale-up captured" evidence was
sat_v2-driven, not a clean basic scale-up). Standup mechanism: the corrected `benchmark-standup-shared`
step list from §4 above (step 08 included).

**Then — the headline scenario, never yet observed in a clean form:** TA driving a scaling decision
sat_v2 would not have made on its own (decode-heavy short requests, a slow RPS ramp so TA's
RequiredCapacity goes positive before sat_v2's KV/queue gate trips, TA-on vs TA-off controlled arms).
This experiment's setup/feasibility work is tracked separately
(`session/handoffs/plan__ta-sat-scaleup-lead-feasibility-answered.md`) — not restated here, and it
depends on but is separate from the sat-disable mechanism question (see [[D-10]]) since it runs TA+SAT
combined rather than needing SAT disabled.

**0.9-behavior scenarios exercised:** veto-liveness (an uninformative analyzer must not veto
scale-down), model-level demand (decode demand from a model-level arrival sum), registration-safety
(config-absent analyzers don't register and can't veto).

### 5.3 Grafana observability research — fact-finding only, not executed

Pure research into visualizing WVA's operational dashboard live during a pokprod run. **Nothing was
created on the cluster** — this remains fact-finding, not a task, per Dean's explicit "no edits for
now." Findings: WVA emits ~26 real metrics and ships a real dashboard definition with an
auto-resolving Grafana datasource template variable; the repo's own `make deploy-wva-on-k8s` observability
path is kind/plain-kubernetes-only and does not help on OpenShift (it would install a redundant
Prometheus against the shared cluster's own UWM/Thanos stack); no existing doc anywhere (this repo,
the llm-d/llm-d guides, or the harness) documents authenticating a Grafana datasource against
OpenShift's shared Thanos. A working recipe was reverse-engineered read-only from two independently
live Grafana instances already on pokprod — full 7-step recipe, the open decision points before
creating anything, and the one step needing Dean's explicit per-action go-ahead (a `ClusterRoleBinding`)
are preserved in the pre-restructure doc's §7.2 rather than duplicated here, since this remains
unexecuted fact-finding, not a live plan.

### 5.4 inference-perf load-gen fix — diagnosed, fix NOT YET IMPLEMENTED (coder task)

Corrected an earlier misdiagnosis: Ofer's scenario always declared `harness.name: inference-perf`
correctly (`harness.experimentProfile: shared_prefix_synthetic.yaml`) — the actual root cause is that
the Makefile unconditionally appends `-w $(BENCHMARK_WORKLOAD).yaml` to every `benchmark-run`
invocation, for both harnesses. `step_05_render_profiles.py`'s `_resolve()` is a three-tier fallback
(CLI/context value → scenario's own `plan_config` → hardcoded default) and the CLI value always wins —
so the Makefile's forced `-w` silently shadows a scenario's own `harness.experimentProfile` even when
it's already correctly declared. A separate local-`.in` filename-mismatch bug is real but downstream of
this — a symptom of routing custom profiles through a fragile side mechanism instead of the tool's own
catalog convention.

**Recommended fix, not yet implemented:** (1) make the Makefile's `-w` conditional, mirroring an
existing `$(if ...)` idiom already on the same line, defaulting `BENCHMARK_WORKLOAD` to empty rather
than a hardcoded profile — restores the scenario's own field as authoritative unless the user
explicitly overrides on the command line, harness-agnostic; (2) audit the other
`$(BENCHMARK_WORKLOAD)`-gated Makefile blocks so they no-op cleanly on an empty value instead of
erroring; (3) stop routing custom profiles through the local-`.in` mechanism — commit them directly
into the fork's native catalog path (`workload/profiles/inference-perf/<name>.yaml.in`), the same
convention Ofer's own profile already uses successfully (verified: survives editable-install
re-renders the same way his does; does not survive a hard reset unless committed to the branch).

**A first calibration workload was drafted against this fix, not yet run.**
`ta_calibration_probe.yaml.in` — a simpler bar than the full TA-lead experiment (just wants any signal
that TA calibrated at all, not a controlled TA-vs-sat_v2 comparison): fixed 4096-in/1024-out token
shape (matching an already-validated shape so the OLS fit isn't confounded by shape changes), 8-stage
rate sweep 2→20 RPS over 12 minutes — enough varied load for TA's `MinSamples=10`/`KSpread≥0.30`
requirement to flip its reason code off the default and show a nonzero `RequiredCapacity`. Verification
signal: watch `analyzer=throughput` log lines for the reason-code flip. **Unverified, flagged to
whoever runs it:** `total_count: 2000` per distribution is a generous guess (the 8-stage sum is ~7,100
requests) — inference-perf's behavior if a stage needs more distinct prompts than `total_count` was not
confirmed; verify empirically and raise if requests start erroring mid-stage.

### 5.5 Autoscaler-arm matrix + A/B hygiene

The autoscaler is the variable under test, so the arm is a first-class axis of every scenario:

| Arm | Mechanism | Selects |
|---|---|---|
| WVA-TA | WVA controller, ThroughputAnalyzer enabled alongside saturation | `guides/workload-autoscaling` |
| WVA-SAT | WVA controller, saturation-v2 only | `guides/workload-autoscaling` + analyzer config |
| KEDA-direct | no WVA controller; EPP + KEDA `ScaledObject` | `guides/epp-keda-saturation` — blocked, [[D-7]] |

`BENCHMARK_REPO_REF`/`BENCHMARK_SPEC` are derived from the arm choice, never hand-set — an arm cannot
select an unguarded ref by construction (architecture doc §5).

**Three contamination paths that must stay closed for an A/B across arms to mean anything:** a
scenario file gets mutated in place by a `sed -i` and stays mutated for the next arm's run from the
same directory; a "turn the analyzer on" helper also rewrites scaling *thresholds*, so it isn't a
single-variable change; and carry-over state (analyzer memory, prefix cache, leftover namespaced
objects) between arms. Also: a KEDA-bounds injection matches literal default strings — if upstream
changes those defaults, the injection silently no-ops and the arm quietly reverts to upstream scaling
behavior, same failure class as the threshold issue above.

---

## 6. Decisions (all resolved 2026-07-28)

- **Integration mechanic** — `git merge --no-ff`, preserving exact PR-commit provenance; a
  re-integration on PR update is a clean re-merge.
- **Tag/image names** — confirmed and executed; see §2 above for the current tags.
- **pokprod cleanup** — confirmed; full nuke of the stale namespace, fresh namespace stood up (§4).
- **Ofer handover** — Dean runs Step-0 sanity himself on the Tier-A image first; once it passes, the
  code (image/tag/branch) hands to Ofer for wider testing. Ofer's own KEDA-guide alignment is a separate
  discussion, opened in its own session when it starts.

**On Ofer's #1435 (verified harness-only):** touches only the Makefile, one doc, and files under
`hack/benchmark`/`test/benchmark` — no files under `internal/`, `pkg/`, `cmd/`, or `api/`. Correctly
excluded from the code-under-test image; his separate controller-side change lives on his own WVA fork
and Tier A does not depend on it.

---

## 7. Execution ownership & scope

The write-work is a coder's, in the code worktrees — the plan-agent cannot write there. It spans
multiple worktrees; every push is gated on Dean's explicit per-push confirmation regardless of worktree
(coders never push — Dean pushes after review).

**Phase 0–2 execution map** (historical — all rows DONE, kept for provenance of what ran where):

| Phase | Worktree | Coder work | Pushes |
|---|---|---|---|
| 0 | `benchmark` | commit untracked artifacts; rename/create-fresh/archive locally | archive tag + fresh `benchmark` → origin |
| 1a | `ta-veto-liveness` (D, #1481) | forward-rebase + `engine_v2.go`/`engine_v2_test.go`/pipeline-doc reconciliation, message-vs-diff, gates | none — do not push (would confuse PR #1481 reviewers) |
| 1b | `ta-model-level-demand` (C, #1480) | same reconciliation, plus `engine_v2_population_test.go` + one more doc | none — do not push (would confuse PR #1480 reviewers) |
| 1c | new `ta-testing` | merge the two PRs, assemble, gate, build, tag | branch + tag → fork; image → quay |
| 2 | `benchmark` (fresh) | wire the harness to Tier A, port runbook content | fresh-branch commits → fork |

**CURRENT.md / PR-status** updates go through `/sync-current` from handoffs — never a direct edit by
any session other than the dedicated sync session.

### 7.1 Tooling track — all `benchmark` worktree, all local, no pushes without Dean's per-push review

| # | Work | Owner | Status |
|---|---|---|---|
| T1 | Migrate the two fork-guard-rule violators out of the harness fork into WVA `hack/`, deduping against files WVA already owns | benchmark coder | open |
| T2 | Refresh the harness fork's `main` from true upstream; rebase the guard commits onto it; repoint KEDA mode at that ref. **Gates T3** | benchmark coder | open — see [[D-7]] |
| T3 | Make the KEDA-direct arm actually run; add it to the arm matrix; fix two cosmetic defects in the same Makefile block — a log line claims to "upgrade the llm-d-benchmark checkout" but the code that follows only checks the CRD, and a `-n $(BENCHMARK_NAMESPACE)` flag is passed to a cluster-scoped `get crd` (inert, but reads as though CRDs were namespaced) | benchmark coder | blocked on T2 |
| T4 | Context-keyed `.env` + fail-closed Makefile guard + assertion triple + arm-derived refs; extend `benchmark-preflight` beyond its one current call site to the other namespace-requiring targets | benchmark coder | open |
| T5 | `make benchmark-configure` wizard + the on-branch explaining skill | benchmark coder | open |
| T6 | The one consolidated runbook + its two link points + the pokprod-runbook fold-in (fold-vs-stub call is Dean's, [[D-8]]) | benchmark coder | open |
| T7 | Close the three cross-arm contamination paths + the literal-match injection hazard | benchmark coder | open |
| T8 | Pin `hack/benchmark` Python deps; add a fresh-checkout acceptance gate (the technique that caught a real data loss during the autoscaling-viz migration) | benchmark coder | open |
| T9 | Wire the gateway access-log follower into the run playbook so it applies automatically whenever a benchmark runs — **not a permission gap**, a wiring task | benchmark coder | **DONE, structurally verified 2026-08-12** ([[D-22]], [[D-27]]) — `BENCHMARK_GATEWAY_LOG_FOLLOWER` flag wired into `benchmark-run`; not yet exercised against a live cluster |
| T10 | File upstream `llm-d-benchmark` issues for the two harness-fork guards | Dean | later, Dean's call, after T2 isolates them |
| T11 | Dwell-run preconditions (PVC reclaim + gate, harness-pod scheduling, GPU footprint flag, controller restart, prompt post-run analysis) | benchmark coder | tracked in [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) — the run itself is live scenario work, not settled execution |
| T12 | Make the Makefile's forced `-w` workload flag conditional (§5.4 above); audit `$(BENCHMARK_WORKLOAD)`-gated blocks; commit custom profiles to the fork's native catalog instead of the local-`.in` mechanism | benchmark coder | open — see §5.4 |

**Still Dean's, not a tooling-track item:** the T6 fold-vs-stub call for the pokprod runbook; approval
of any cluster run, as always.

**Not in this plan's scope:** whether/when the `benchmark` branch's local-ahead-of-origin commits push —
Dean's, per push, whenever he chooses.
