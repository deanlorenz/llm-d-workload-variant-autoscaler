# Current Work

**Last updated:** 2026-05-11

---

## PR Status

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| TA1                   | #1051 | CI green; awaiting approval (no LGTM yet)                         | `900c94c` |
| TA2                   | #1052 | CI green; awaiting approval                                       | `99a35b0` |
| TA3                   | —     | Local only; rebase after TA2 merges                               | `cacb0e5` |
| engine-multi-analyzer | #1113 | DCO ✅ lint-and-test ✅ e2e-smoke 🔄 pending; awaiting review     | `a93bc5d` |
| engine-queue-fix      | —     | Local only (worktree); PR deferred until #1113 merges             | `01ed7d8` |

---

## Blocked on

- **TA1 (#1051)** — awaiting approval; TA2 and TA3 cannot merge until TA1 lands
- **TA2 (#1052)** — awaiting approval; TA3 rebase waits on TA2 merge
- **#1113 (engine-multi-analyzer)** — e2e-smoke pending; awaiting review; engine-queue-fix PR waits on this

## Next steps

- After TA1 merges: rebase TA2 onto new upstream/main tip
- After TA2 merges: rebase TA3, discuss TA3 PR-4+PR-5 before submitting
- After #1113 merges: open engine-queue-fix PR (force-push `01ed7d8` after rebasing onto new main tip)

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

**Branch:** `engine-multi-analyzer` in worktree `.claude/worktrees/engine-multi-analyzer/`  
**Targets:** `main` — independent of all TA branches, no TA code included.  
**Tip:** `a93bc5d` (post DCO+gofmt interactive-rebase fix, force-pushed 2026-05-10)

**Three commits:**
- `5bbe8af` — implementation: generic `analyzers` map, `runAnalyzersAndScore()`, `combineAnalyzerResults()` any-up/all-down, `engine_combine_test.go` (31 specs)
- `db59b53` — docs: Multi-Analyzer Pipeline section in `saturation-scaling-config.md` and `saturation-analyzer.md`
- `a93bc5d` — `RegisterAnalyzer(name, interfaces.Analyzer)` method on `Engine`

### engine-queue-fix

**Branch:** `engine-queue-fix` (stacked on `engine-multi-analyzer`; worktree `.claude/worktrees/engine-multi-analyzer/`)  
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
