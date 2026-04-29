# Current Work

**Last updated:** 2026-04-29  
**Branch:** TA3 (PR #1051 review done; TA2/TA3 rebased; TA3 still paused — see § TA3 Paused State)

---

## Current Task

Feature: ThroughputAnalyzer — PR #1051 review complete; TA2/TA3 rebased

**Status (2026-04-29):** All 5 PR #1051 review comments addressed and CI passing. PR description
updated to reflect the 3-query simplification. TA2 rebased onto `0c3933c`. TA3 rebased onto new TA2.
Plan files (TA-PR1/2/3-plan.md) updated with renamed constants (`KvUsageInstant`, `QueryKvUsageInstant`).

**What changed in TA1 (accumulated over 2026-04-28/29):**
- `QueryKvTokensUsed` → `QueryKvUsageInstant` (`kv_tokens_used` → `kv_usage_instant`)
- `KvUtilization` → `KvUsageInstant` (ReplicaMetrics field)
- Doc moved: `docs/user-guide/` → `docs/developer-guide/throughput-analyzer.md`
- Pending markers + architecture note added to doc (PR-3/PR-4 callouts)
- Duplicate-panic test replaces redundant test (comment 4)
- Pod/pod_name fallback doc comment added (comment 5)

**Branch tips after rebase:**
- TA1: `0c3933c` (pushed to origin, PR #1051 CI green)
- TA2: `ed63932` (local only — not pushed)
- TA3: `56fade2` (local only — not pushed)

Next step:
- [ ] Discuss TA2 changes and PR-4 before resuming TA3 work

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
  - [x] PR-5: wiring ThroughputAnalyzer into WVA engine (TA3 commit `8c67138`, not yet submitted)
  - [x] ENGINE: multi-analyzer pipeline — `analyzers` map, `RegisterAnalyzer`, combine logic (`engine-multi-analyzer`, ready to submit)
- [x] E2E infrastructure — kind cluster up, Step 1a + 1b passed (31/31 smoke tests each)
- [ ] E2E test scenarios — `test/e2e/throughput_analyzer_test.go` (3 scenarios, file written — discuss before running)
- [ ] PR review
- [ ] Merge

Design docs:
- `ideas/TA-Plan.md` — overall TA design
- `ideas/TA-overview.md` — supply/demand model and analyzer overview
- `ideas/TA-PR4-plan.md` — ITL model + scaling signal (PR-4)
- `ideas/TA-PR5-plan.md` — wiring PR plan (PR-5)
- `docs/developer-guide/throughput-analyzer.md` — user-facing reference

Plan doc:
- `ideas/TA-e2e-plan.md` — e2e execution steps, scenario specs, variable reference, infra issues

Next step:
- [ ] Discuss e2e test design (scenarios, load strategy, assertions) — awaiting discussion
- [ ] Review `test/e2e/throughput_analyzer_test.go` (drafted, not yet run)
- [ ] Run scenarios per `ideas/TA-e2e-plan.md § Task 2`

---

## ENGINE PR: Ready to Submit

**Branch:** `engine-multi-analyzer` (pushed to origin)  
**Targets:** `main` — independent of all TA branches, no TA code included.

**Three commits:**
- `b6d142a` — implementation: generic `analyzers` map in `Engine` struct, `runAnalyzersAndScore()` rewrite, `combineAnalyzerResults()` with dimensionless any-up/all-down, `engine_combine_test.go` (31 specs)
- `a1f094d` — docs: Multi-Analyzer Pipeline section in `saturation-scaling-config.md` and `saturation-analyzer.md`
- `9fc4a62` — `RegisterAnalyzer(name, interfaces.Analyzer)` method on `Engine` — lets callers inject plugin analyzers without engine.go knowing the concrete type

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

**File:** `ideas/TA-e2e-plan.md` (rev 6 — 2026-04-27)

### Step 1a — PASSED (2026-04-27)
- 31/31 smoke tests in 536s
- kind cluster `kind-wva-gpu-cluster` is UP and can be reused
- WVA deployed with TA3 code (due to Makefile `IMG` always being set)

### Step 1b — PASSED (2026-04-27)
- 31/31 smoke tests in 544s
- WVA redeployed with `quay.io/dlorenz/llm-d-workload-variant-autoscaler:ta3-dev`
- EPP patch to v0.5.0 applied (version mismatch workaround)

### E2E Infrastructure State

Kind cluster `kind-wva-gpu-cluster` is UP and ready.  
WVA deployed: `quay.io/dlorenz/llm-d-workload-variant-autoscaler:ta3-dev` (Step 1b).

To resume e2e work on this cluster:
```bash
git checkout TA3
# Run smoke (includes Scenario 1 after writing the test file):
make test-e2e-smoke ENVIRONMENT=kind-emulator
# Run full TA scenarios only:
make test-e2e-full ENVIRONMENT=kind-emulator FOCUS="ThroughputAnalyzer"
```

If the cluster is gone, redeploy following `ideas/TA-e2e-plan.md § Step 1a` then `§ Step 1b`.

### Known infra issues (separate PRs — not in TA3)

Details in `ideas/TA-e2e-plan.md § Infrastructure notes`.

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

**6. SchedulerQueue stays nil** — existing TODO.

---

## Issues to Open (post-merge)

- **Prometheus gauges for ITL model coefficients** — export `wva_throughput_analyzer_itl_model_a`
  and `wva_throughput_analyzer_itl_model_b` gauges (labels: `namespace`, `model_id`, `variant`,
  `tier`) so operators can graph ITL model stability in Grafana. Separate observability PR
  after PR-5 merges. (From Bob's review, 3.1)
- **EPP image version mismatch** — `install.sh` patches EPP to v0.7.0 but local llm-d is v0.5.0; file as infra bug
- **Gateway prompt bug** — `install_core.sh` fires interactive prompt when `E2E_TESTS_ENABLED=false` even with explicit `INSTALL_GATEWAY_CTRLPLANE=true`; file as infra bug
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable; file as Makefile bug
- **ndots fix standalone PR** — commit `0614d9d` on TA3 (`test/e2e/fixtures/workload_builder.go`) needs its own PR to `main` before or alongside TA3 merge
