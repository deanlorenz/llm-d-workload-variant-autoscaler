last_update: 2026-07-29T23:40:00+03:00
state: awaiting-review
current_step: Phase 2 (§5) DONE — env parametrization + pokprod KEDA runbook committed on benchmark; STOPPED before push (Dean's)
blocked_on: none — commit 6505de62 ready for Dean's review + push (fork only)

## Branch
benchmark at /home/dean/.../benchmark worktree ; new tip 6505de62
  (6505de62 [this session] on top of 9bd53d7b [#1435 KEDA harness adoption] on top of the fresh 11d70a8a base)
archive/benchmark-ta3-legacy tag -> 892e1efa (VA+HPA legacy runbook + notes; recovery handle)

## This session — Phase 2 §5 (parametrize + runbook)
Commit 6505de62 (DCO signed): "benchmark(two-variant): parametrize env-specific values via .env; add pokprod KEDA runbook"
10 files, +586/-56. Tier B only, fork-only, no cluster contact.

### What was done
- hack/benchmark/.env.sample (NEW) — every §5.2 env-specific var, NO live defaults for env-specific keys.
- .gitignore — hack/benchmark/.env ignored.
- Makefile — `-include hack/benchmark/.env` BEFORE the `?=` defaults (.env wins; CLI still wins over .env);
  token-`sed` __VAR__ → .env value into the copied scenario at benchmark-standup AND benchmark-run,
  each with a residual-`__TOKEN__` guard that aborts + lists any unset var; benchmark-add-variant now
  requires ACCELERATOR_NAME/PRIMARY_COST/PRIMARY_MIN/PRIMARY_MAX and passes them + --prometheus-url.
- scenarios/guides/{two-variant-wva,wva-sat2-tp1}.yaml — tokenized image/chart/model/workdir/release.
- add_variant.py — --prometheus-url now required; added required --accelerator-name/--primary-cost/
  --primary-min/--primary-max; removed hardcoded NVIDIA-H100 / cost 10 / min 1 / max 10.
- post_run_analyze.sh — dropped hardcoded `biran` default namespace (now requires BENCHMARK_NAMESPACE
  or arg 2); genericized biran-* comment examples. plot_two_variant_pipeline.py + .j2 — biran/model
  literal comments genericized.  [NOTE: these 3 files are beyond the §5.2 table — small comment/default
  cleanups to satisfy §5.6; flagged to Dean below.]
- docs/two-variant-wva-pokprod-runbook.md (NEW) — Tier-B KEDA runbook ported from the archived VA+HPA
  runbook (§1 env / §2 host tools / §3 CLI / §4 .env / §5 Tier-A image / §6 standup / §7 add-variant /
  §8 enable-v2 / §9 verify TA / §10 load+signals / §11 troubleshooting / §12 compat / §13 fallback /
  §14 teardown). Reframed to `make benchmark-*` + .env; dropped :ta3-build/chart-0.6.0/manual-relabel/
  historical-findings.

### Verified (Step 5, no cluster contact)
- py_compile add_variant.py + plot_two_variant_pipeline.py OK; bash -n post_run_analyze.sh OK.
- make -n parses benchmark-standup / benchmark-run / benchmark-add-variant.
- Token-render simulation on BOTH guides with .env.sample values → residual __TOKEN__ = 0, valid YAML,
  correct image/chart/model render.
- §5.6 residual-hardcode grep: harness deploy files CLEAN; `\bbiran\b` fully gone from hack/ test/.
  Remaining grep hits are ALL out-of-scope pre-existing prose/fixtures (NOT env config, NOT harness):
  docs/developer-guide/prometheus.md (JSON output samples), docs/benchmark.md + benchmark-guide.md
  (prose), hack/vllm-benchmark-deployment.yaml:7 (generic <model-id> example comment),
  test/utils/unitutils.go:169 (Go test arg). Plus docs/developer-guide/two-variant-wva-benchmark.md
  (#1435's dev-guide — prose; reworked separately if Dean wants). Left untouched — scope call, see below.

## Decisions carried in (Dean, prior session) — reflected in the commit
- vllm registry: VLLM_IMAGE_REPO parametrized, docker.io default kept  (AGENTS.md docker.io conflict — FLAGGED, not resolved).
- chart: WVA_CHART_VERSION=0.8.0-rc5 (Ofer's) + our WVA_IMAGE_TAG=ta-0.9  (compat risk documented in runbook §12).
- prom url: existing Makefile default kept; .env overrides via being -include'd before the ?=.

## Reclone
Embedded gitignored llm-d-benchmark/ clone present and on Ofer's origin biranofer/llm-d-benchmark.git
@ feat/multi-variant-benchmark (tip 6d5ff6b) — reclone effectively current; not committed (gitignored).

## Not done (STOPPED — Dean's / later phases)
- No push (commit 6505de62 → origin/benchmark) — awaiting Dean's explicit OK. Fork only, never upstream.
- Phase 3 (clean stale pokprod) + live standup / any oc apply — cluster-side, Dean/Ofer, separate.
- Tier-A :ta-0.9 image build/push — deferred (Dean); stays a .env var.

## For Dean (review points)
1. §5.6 grep scope: I read it as "harness deploy files → zero"; the doc-prose/Go-test hits are legit
   examples left as-is. Confirm, or say if you want the docs/test scrubbed too.
2. 3 files touched beyond the §5.2 table (post_run_analyze.sh default + plot/.j2 comments) — OK?
3. Runbook filename: chose docs/two-variant-wva-pokprod-runbook.md (KEDA/ta-0.9 reality) instead of
   reusing the stale "ta3" name. Rename if you prefer.
4. AGENTS.md forbids docker.io in e2e; VLLM_IMAGE_REPO defaults to docker.io/vllm/vllm-openai per your
   call — reconcile the doc vs the default when convenient.

## Phase 0 (prior session, 2026-07-28) — resolved
Fresh benchmark created off main; old branch renamed benchmark-ta3-legacy (tip 892e1efa, docs-only,
results discarded per Dean); archive/benchmark-ta3-legacy tag -> 892e1efa. #1435 KEDA harness later
adopted (9bd53d7b). Local untracked reference-legacy/ (56K) retained: profiles/*.yaml.in,
two-variant-wva.patched.yaml, benchmark-settings.env, benchmark-s1-manual-run.md, README.md.
