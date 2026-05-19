# Current Work

**Last updated:** 2026-05-19

---

## Last session: Benchmark plan deep-dive — saturation_v2, simultaneous-saturation trap, L40+H100

Extensive benchmark planning session. Key outcomes:

- **GPU names corrected:** L4 → L40 throughout both plan docs.
- **Scenario 1 variants changed:** L40+A100 → **L40+H100** (better cost ratio 1:4.3).
  Cost weights: L40=15, H100=65.
- **Peak RPS revised:** 25 → **35 RPS**. At 25 RPS with 2L40+1H100 both systems land at
  57% utilisation — no steady-state difference. At 35 RPS (80% util for 2L40+1H100) WVA
  is stable; KEDA fires both ScaledObjects simultaneously and is trapped at 2L40+2H100.
- **Correct mechanism identified:** The steady-state cost gap comes from the
  **simultaneous-saturation trap** — EPP equalises KV% across variants, so both KEDA
  ScaledObjects fire simultaneously. WVA's aggregate optimizer adds only the cheapest
  variant. KEDA reaches a locally-stable over-provisioned state it cannot escape without
  cross-variant coordination. Cost advantage ~30–44% at steady state (Phase 2 peak).
- **Analyzer confirmed:** saturation_v2 alone (`analyzerName: "saturation"`). No
  multi-analyzer, no QueueingModel (not ready). saturation_v2 is token-based (k1/k2
  dual-capacity), aggregate cross-variant, pending-replica-aware.
- **New approach doc created:** `planning/benchmark-wva-vs-keda.md` (Type-1 design).
  Readable entry point: scenarios, structural argument, phase tables, design decisions,
  high-level gaps. Implementation reference plan has a forward-pointer to it.
- **Homogeneous cluster variant documented** (§ 2.2b of plan): same scenario works
  with cost weights as organisational tier labels on identical hardware.
- **Team discussion doc updated and pushed:**
  https://github.com/deanlorenz/llm-d-workload-variant-autoscaler/blob/plans/scratch/benchmark-team-discussion.md

PR #1092 short review comment draft at `scratch/PR1092-short-draft.md` is still pending
counter-proposal integration. See memory `project_pr1092_analysis.md` for full recap.

---

## PR Status

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| TA1                   | #1051 | **MERGED** 2026-05-12; remove worktree ~2026-05-26                | `c405e8d` |
| TA2                   | #1052 | **MERGED** 2026-05-19; remove worktree ~2026-06-02                | `a8aac2b7` |
| TA3                   | —     | Local only; rebase onto upstream/main now unblocked               | `7506634b` |
| engine-multi-analyzer | #1113 | DCO ✅ lint-and-test ✅ e2e-smoke 🔄 pending; awaiting review     | `a93bc5d` |
| engine-queue-fix      | —     | Local only (worktree); PR deferred until #1113 merges             | `01ed7d8` |

---

## Blocked on

- **#1113 (engine-multi-analyzer)** — e2e-smoke pending; awaiting review; engine-queue-fix PR waits on this

## Next steps

- **Now:** rebase TA3 onto upstream/main, then discuss TA3 PR-4+PR-5 before submitting
- After #1113 merges: open engine-queue-fix PR (force-push `01ed7d8` after rebasing onto new main tip)
- **Parallel track (NOT authorized yet):** WVA-vs-KEDA benchmark plan drafted at `planning/benchmark-wva-vs-keda-plan.md`. **Do not start coding.** The plan needs review + explicit go-ahead from Dean before any implementation begins — see the Benchmark section below.

---

## Benchmark: WVA vs KEDA Cost-Optimal Ramp (plan DRAFT — NOT AUTHORIZED)

> **STOP — do not begin implementation.** The plan below is a first draft. Dean has not
> yet reviewed or approved it. A new coding session that sees this entry MUST NOT start
> writing code, creating manifests, modifying the Makefile, or adding Go test files based
> on this plan. Open a discussion first, summarise the plan back to Dean, take feedback,
> and wait for an explicit "go ahead and implement" before touching any code worktree.
>
> The plan itself documents this gate at the top of `planning/benchmark-wva-vs-keda-plan.md`.
> When Dean approves, this block is removed and the status line updated.

**Docs:**
- `planning/benchmark-wva-vs-keda.md` — **Approach doc (Type-1, start here).** Scenarios,
  structural argument, phase tables, design decisions, high-level gaps. ~300 lines, readable.
- `planning/benchmark-wva-vs-keda-plan.md` — **Implementation reference (Type-3).** All
  details: exact configs, Go types, Ginkgo skeleton, kind dry-run, OpenShift sizing, coder
  guide (§ 8), implementation order (§ 8.13). ~2300 lines. Not reviewed/approved.

**Headline claim:** At 35 RPS peak load, WVA holds stably at 2L40+1H100 (cost 95/interval).
KEDA is trapped at 2L40+2H100 (cost 160/interval) — **~30–44% lower cost-weighted
GPU-hours at equivalent p99 ITL**, present at steady-state Phase 2 peak, not just ramp
transients. Mechanism: EPP equalises KV% across variants → both KEDA ScaledObjects fire
simultaneously → KEDA over-provisions both; WVA's aggregate optimizer adds only the cheaper
variant (L40=15) and stops.

**Scenario 1 — Cost-Optimal Ramp:**
- Pool: L40 (cost=15, max=2) + H100 (cost=65, max=3); 1:4.3 ratio; cluster 2×L40 + 16×H100
- Traffic: 30-min staircase ramp, 3 → 35 RPS, decode-heavy (1000 in / 4000 out), Poisson
- Analyzer: saturation_v2 alone (`scaleUpThreshold=0.85`, `scaleDownBoundary=0.70`)
- Comparison: WVA / keda-naive / keda-tuned (KV threshold 0.70)

**Scenario 2 — Starvation Prevention:**
- Two pools, label-partitioned nodes (`gpu.partition=premium|basic`), homogeneous hardware
- Pool-A (premium, H100 partition, cost=65), Pool-B (two variants: B-h100 cost=65, B-a100 cost=40)
- WVA steers Pool-B to B-a100 (cheaper); KEDA fills both partitions; Pool-A starves under KEDA
- Comparison: WVA / keda-naive / keda-tuned / keda-tuned-capped

**Entry points for REVIEW (before approving):**
1. `planning/benchmark-wva-vs-keda.md` — full approach; check scenarios, claim, decisions
2. `benchmark-wva-vs-keda-plan.md` § 2.2–2.2b — variant design, cost model, simultaneous-saturation analysis
3. `benchmark-wva-vs-keda-plan.md` § 3 — WVA configuration (saturation_v2)
4. `benchmark-wva-vs-keda-plan.md` § 4 — KEDA baselines; check they are fair
5. `benchmark-wva-vs-keda-plan.md` § 7.5 — OpenShift sizing; decide which option to run

**Entry points for IMPLEMENTATION (after approval):**
- Kind dry-run: `benchmark-wva-vs-keda-plan.md` § 6
- Coder guide: § 8 (file layout, Go types, Ginkgo skeleton, Makefile)
- Implementation order: § 8.13 (10 steps)

**Decisions already made (do not re-litigate):**
- Analyzer: saturation_v2 alone (no multi-analyzer, no QueueingModel — not ready)
- Peak RPS: 35 (not 25 — 25 gives no steady-state gap)
- Scenario 1 variants: L40 + H100 (not L40 + A100)
- maxReplicas: L40=2 (hardware cap; enforceable via VA spec on any cluster)
- Traffic: staircase ramp via chained GuideLLM jobs
- KEDA-tuned KV threshold: 0.70 (honest concession; WVA aggregate threshold ~0.85)
- ThroughputAnalyzer: disabled for this round (re-run after TA3 merges)
- Scenario 2 hardware: homogeneous + label partition (Option P2, default)
- Do not modify WVA controller code — driver-only work

**Before any coding starts:**
- Dean reviews approach doc and relevant plan sections.
- Open questions resolved in conversation.
- Plan frontmatter status updated to "Approved — ready for implementation".
- STOP block above removed from CURRENT.md.
- Explicit "go ahead and implement" from Dean.
- Only then does the coder begin at § 8.13 step 1.

**Benchmark future directions (not in scope for this round):**
- **Dynamic cross-tenant reallocation under a Pool-A spike** — requires WVA's Limited
  mode (not yet implemented; see `docs/design/modeling-optimization.md § Future Work:
  Limited Mode`). Scenario 2's prevention is static (cost gradient at scale-up time);
  under a sudden Pool-A spike after Pool-B already holds premium slots, WVA Unlimited
  will not migrate Pool-B off gpu1. Re-run Scenario 2 after Limited mode lands to
  demonstrate dynamic reallocation.
- **Proactive detection during rapid ramps** — re-run Scenario 1 with TA3's
  ThroughputAnalyzer enabled after TA3 merges, to expose the rate-based-detection
  advantage separately from the cost-coordination advantage.
- **SLO priority under contention** — explicit priority/criticality mechanism from
  the WVA design exists but requires Limited mode to engage. Adds a third scenario
  once that path is live.

---

## TA3 Paused State

Feature: ThroughputAnalyzer (TA) — E2E test scenarios

Phase:
- [x] Design discussion
- [x] Design frozen
- [x] Implementation
  - [x] PR-1/PR-2: query registration + collector wiring (TA1, #1051 — review resolved, CI green)
  - [x] PR-3: state management — ShapeTracker, ObservationWindow, SanityReport (TA2, #1052 — awaiting review)
  - [x] PR-4: ITL model + scaling signal (TA3 commit `52553dc`, not yet submitted)
  - [x] PR-4 addendum: GPS verification — `checkVariantGPSMismatch`, SC suppression on > 15% error, near-k_sat diagnostics (TA3, 2026-05-10)
  - [x] PR-5: wiring ThroughputAnalyzer into WVA engine (TA3 commit `8c67138`, not yet submitted)
  - [x] ENGINE: multi-analyzer pipeline — `analyzers` map, `RegisterAnalyzer`, combine logic (`engine-multi-analyzer`, PR #1113 submitted)
  - [x] ENGINE: SchedulerQueue wiring — `CollectSchedulerQueueMetrics` → `AnalyzerInput.SchedulerQueue` (`engine-queue-fix`, PR deferred)
- [x] E2E infrastructure — kind cluster up, Step 1a + 1b passed (31/31 smoke tests each)
- [x] E2E test scenarios — Steps 2a–2e complete; Scenario 1 PASSED (TA wiring health check); 3 pre-existing smoke failures; Step 2f (Scenarios 2+3) pending discussion
- [ ] PR review
- [ ] Merge

Design docs:
- `plans/planning/TA-Plan.md` — overall TA design
- `plans/planning/TA-overview.md` — supply/demand model and analyzer overview
- `plans/planning/TA-PR4-plan.md` — ITL model + scaling signal (PR-4)
- `plans/planning/TA-PR5-plan.md` — wiring PR plan (PR-5)
- `docs/developer-guide/throughput-analyzer.md` — user-facing reference

Plan doc:
- `plans/planning/TA-e2e-plan.md` — e2e execution steps, scenario specs, variable reference, infra issues

Next step:
- [ ] Triage 3 pre-existing smoke failures (smoke_test.go:339, :542, :1724) — are these regressions in main, or require TA3 action?
- [ ] Discuss Step 2f (Scenarios 2 and 3) before running

---

## ENGINE PRs

### engine-multi-analyzer (PR #1113)

**Branch:** `engine-multi-analyzer` in worktree `engine-multi-analyzer/`  
**Targets:** `main` — independent of all TA branches, no TA code included.  
**Tip:** `a93bc5d` (post DCO+gofmt interactive-rebase fix, force-pushed 2026-05-10)

**Three commits:**
- `5bbe8af` — implementation: generic `analyzers` map, `runAnalyzersAndScore()`, `combineAnalyzerResults()` any-up/all-down, `engine_combine_test.go` (31 specs)
- `db59b53` — docs: Multi-Analyzer Pipeline section in `saturation-scaling-config.md` and `saturation-analyzer.md`
- `a93bc5d` — `RegisterAnalyzer(name, interfaces.Analyzer)` method on `Engine`

### engine-queue-fix

**Branch:** `engine-queue-fix` (stacked on `engine-multi-analyzer`; worktree `engine-queue-fix/`)  
**Tip:** `01ed7d8` (1 commit ahead of engine-multi-analyzer)  
**PR:** not yet opened — waiting for #1113 to merge  
**What it adds:** calls `CollectSchedulerQueueMetrics(ctx, modelID)` in `prepareModelData`; threads result through `collectV2ModelRequest` → `runAnalyzersAndScore` → `runV2AnalysisOnly` → `AnalyzerInput.SchedulerQueue`.

---

## TA PR-5: Committed on TA3

**Commit:** `8c67138` on TA3 (new hash after TA3 rebase onto TA2)

Two-line wiring in `main.go`:
```go
registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer())
```

**TA3 compile status:** All unit tests pass (`go test ./internal/... ./pkg/... ./cmd/...`).

---

## E2E Plan: Step 1 Complete

**File:** `plans/planning/TA-e2e-plan.md` (rev 6 — 2026-04-27)

### Step 1a — PASSED (2026-04-27)
- 31/31 smoke tests in 536s
- kind cluster `kind-wva-gpu-cluster` is UP and can be reused
- WVA deployed with TA3 code (due to Makefile `IMG` always being set)

### Step 1b — PASSED (2026-04-27)
- 31/31 smoke tests in 544s
- WVA redeployed with `quay.io/dlorenz/llm-d-workload-variant-autoscaler:ta3-dev`
- EPP patch to v0.5.0 applied (version mismatch workaround)

### Step 2a–2e — COMPLETE (2026-05-11)
- 2a: cherry-picked 4 TA3 commits onto `ta3-e2e` (GPS verify, OL guard, unhealthy-pod, calibration-lock)
- 2b: built + pushed `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3-e2e`
- 2c: torn down cluster, rm -rf llm-d/
- 2d: fresh deploy with v0.6.0 llm-d, flow control on (E2E_TESTS_ENABLED=true); EPP v0.7.0 no crash
- 2e: **29/32 smoke tests passed** (1292s); **Scenario 1 (TA wiring) PASSED** in 210.503s
  - 3 failures in `smoke_test.go` (not throughput_analyzer_test.go) — pre-existing regressions vs newer main:
    - `:339` — "external metric item when exported_namespace is selected" (timeout)
    - `:542` — "isolated external metrics for each namespace-scoped controller"
    - `:1724` — "scale up LWS under load" (HPA desired=0 after 120s)

### E2E Infrastructure State

Kind cluster `kind-wva-gpu-cluster` — UP as of 2026-05-11.  
WVA deployed during Step 2d: `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3-e2e` — flow control enabled.

**Current e2e image** (TA3 + engine-multi-analyzer + queue-fix):  
`quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3-e2e` — pushed 2026-05-11 (after cherry-picks)

To resume e2e work on this cluster:
```bash
git checkout TA3
# Run smoke (includes Scenario 1 after writing the test file):
make test-e2e-smoke ENVIRONMENT=kind-emulator
# Run full TA scenarios only:
make test-e2e-full ENVIRONMENT=kind-emulator FOCUS="ThroughputAnalyzer"
```

If the cluster is gone, redeploy following `plans/planning/TA-e2e-plan.md § Step 1a` then `§ Step 1b`.

### Known infra issues (separate PRs — not in TA3)

Details in `plans/planning/TA-e2e-plan.md § Infrastructure notes`.

1. **EPP image mismatch** — `install.sh` patches EPP to `v0.7.0` which rejects `--kv-cache-usage-percentage-metric`; llm-d values are for v0.5.0. Workaround: `kubectl set image deployment/gaie-sim-epp -n llm-d-sim epp=ghcr.io/llm-d/llm-d-inference-scheduler:v0.5.0` after deploy.
2. **Gateway interactive prompt** — `install_core.sh` fires even with `INSTALL_GATEWAY_CTRLPLANE=true` unless `E2E_TESTS_ENABLED=true`. Workaround: prefix `E2E_TESTS_ENABLED=true` before `make deploy-e2e-infra`.
3. **Makefile IMG always set** — `IMG ?= $(IMG_REPO):$(IMG_TAG)` always expands; `deploy-e2e-infra` registry-image code path is unreachable.

---

## Key Design Decisions (confirmed)

**1. engine.go is decoupled from concrete analyzer types.**  
`analyzers` is `map[string]interfaces.Analyzer`. Plugin analyzers injected from `main.go` via `RegisterAnalyzer`.

**2. Saturation always runs (even when `enabled: false`).**  
Provides `Cost` and `AcceleratorName` in VariantCapacities for the optimizer.

**3. Combine algorithm — dimensionless normalization.**
```
util_excess_i = RC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)
util_slack_i  = SC_i / Σ_v(VariantCapacities_i_v.TotalCapacity)

combined.RC = max_i(util_excess_i) × sat_total   # any-up
combined.SC = min_i(util_slack_i)  × sat_total   # all-down; 0 if any analyzer disagrees
```

**4. ThroughputAnalyzerName stays in TA package** (`throughput.AnalyzerName`).

**5. Engine package stays in `saturation/` for now.**

**6. SchedulerQueue: TA handles it correctly; engine collection is a separate bug.**  
`ThroughputAnalyzer.Analyze()` already calls `estimateQueueDemand(input.SchedulerQueue, ...)` and
handles nil → 0 correctly. The gap is in `engine_v2.go` line 56 which always passes
`SchedulerQueue: nil` (TODO comment). `CollectSchedulerQueueMetrics` exists and is fully
implemented in the collector — the engine just never calls it. This affects both `saturation_v2`
and the TA equally. Fix belongs in a separate engine PR (see Issues to Open below).

**7. Tier-2 fallback B: use last fitted B across shape resets. ✅ Implemented (`7733471`).**  
On shape change, `observationWindow.Clear()` drops the tier back to Tier 2. Instead of pinning
`B = DefaultBaselineITLSec` (0.006), Tier 2 uses the last successful Tier-1 fitted B when one
exists — it reflects hardware/model characteristics, not workload shape.  
`lastFittedB float64` + `hasFittedB bool` in `variantState`; exposed in `ThroughputVariantState`.
4 new Ginkgo specs cover: save after Tier-1, survival through shape reset, Tier-2 uses it, default fallback.

---

## Deferred PR-3 (#1052) Fixes

Found during Claude code review; deferred to a follow-up PR after TA2 merges.

- **`DefaultWindowMaxSize` code/doc mismatch** — `constants.go` has `20`; docs table says `100`. Confirm intended value and align. (`internal/engines/analyzers/throughput/constants.go`)
- **Silent discard in `Analyze()`** — `a.Observe(...)` return value not assigned; change to `_ = a.Observe(...)` for clarity. (`analyzer.go`)
- **Misleading `CheckModelMetrics` doc** — comment says "callers should check `report.OK()` before Observe" but `Observe()` only short-circuits on `SanityIssueNoReplicas`. Reword to match actual contract. (`sanity.go`)
- **`averageShapeMetrics()` zero-count branch untested** — add test where all replicas have `IL ≤ 0` or `OL ≤ 0` and verify downstream `ShapeTracker` behavior.
- **No concurrent-access test** — add `go test -race` scenario for simultaneous `Observe()` + `VariantState()`.
- **`pod_name` fallback untested in collector** — add collector tests using `pod_name`-only labels for `GenerationTokenRate`, `KvUsageInstant`, `VLLMRequestRate`.
- **Unbounded `variantStates` map** — add eviction pass keyed on `lastObservedAt > 2×DefaultObservationMaxAge`; add `MaxLength` to `spec.modelID` CRD validation.
- **PromQL `Build()` escaping fragility** — move `EscapePromQLValue` into `Build()` or add explicit doc contract + test.
- **`SanityReport.Has()` → `slices.Contains`** — replace loop body with `return slices.Contains(r.Issues, issue)`. (`types.go`)
- **`issueSet` map → `sets.Set[SanityIssue]`** — replace `map[SanityIssue]struct{}` with `sets.New[SanityIssue]()` from `k8s.io/apimachinery/pkg/util/sets`. (`sanity.go`)

---

## Issues to Open (post-merge)

- **Engine SchedulerQueue wiring** — ✅ implemented on `engine-queue-fix` (`01ed7d8`); PR deferred until #1113 merges. Fix threads `CollectSchedulerQueueMetrics` through `prepareModelData` → `collectV2ModelRequest` → `runAnalyzersAndScore` → `runV2AnalysisOnly` → `AnalyzerInput.SchedulerQueue`.

- **Bob review 1.3 — ArrivalRate staleness check in `computeDemand`** — defer ArrivalRate
  staleness detection (warn when `ArrivalRate` metric is stale/zero while queue is non-empty)
  to a later observability PR. Related to the Prometheus gauge work below.

- **Prometheus gauges for ITL model coefficients** — export `wva_throughput_analyzer_itl_model_a`
  and `wva_throughput_analyzer_itl_model_b` gauges (labels: `namespace`, `model_id`, `variant`,
  `tier`) so operators can graph ITL model stability in Grafana. Separate observability PR
  after PR-5 merges. (From Bob's review, 3.1)
- **EPP image version mismatch** — `install.sh` patches EPP to v0.7.0 but local llm-d is v0.5.0; file as infra bug
- **Gateway prompt bug** — `install_core.sh` fires interactive prompt when `E2E_TESTS_ENABLED=false` even with explicit `INSTALL_GATEWAY_CTRLPLANE=true`; file as infra bug
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable; file as Makefile bug
- **ndots fix standalone PR** — commit `0614d9d` on TA3 (`test/e2e/fixtures/workload_builder.go`) needs its own PR to `main` before or alongside TA3 merge

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| plan-agent | `planning/PR1052-review.md` | FINAL | PR #1052 MERGED 2026-05-19; TA2 worktree clean, safe to remove ~2026-06-02; TA3 rebase now unblocked |
