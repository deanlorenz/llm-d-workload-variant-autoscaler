# ThroughputAnalyzer — Forward Plan & Internal Issues

**Type:** 3 (task plan) · **Date:** 2026-06-17 · **Status:** ACTIVE
**Precondition:** PR #1250 merged `efca1b4c` + testing fixes `34c9be9b`/`b2f1d7ef` on
`upstream/main`.

This document is the single backlog for all TA follow-up work. It covers:
- Correctness bugs
- Silent error detection / observability gaps
- Test quality (unit + e2e)
- Critical longer-term TA design components
- Dev guide and user guide gaps

**Source:** `planning/PR1250-deep-review.md` (the independent post-implementation code review),
plus the dev guide accuracy audit of `docs/developer-guide/throughput-analyzer.md`.
Review tags in brackets (e.g. [C-B1]) trace to that doc.

---

## Priority key

| Priority | Meaning |
|---|---|
| **P0** | Correctness bug or safety regression — fix before TA is turned on in production |
| **P1** | High leverage: prevents operator confusion, unlocks future work, or is cheap and high-value |
| **P2** | Medium leverage: important quality debt |
| **P3** | Architectural / longer-term |

---

## Group 1 — Correctness bugs

### I-1 · Collector key unification [P0]

**What:** The scheduler-dispatch loop in `replica_metrics.go` keys pods using the `port` label
from the `inference_extension_scheduler_attempts_total` metric, while every other loop keys via
`buildInstanceKey` which derives port from the scrape `instance` label. When these two port
values differ, `ArrivalRate` lands in an orphan `podData` entry (dropped at line ~782) and the
KV/queue entry shows `hasArrivalRate=false` — triggering a "pod/pod_name label mismatch"
warning on *every* cycle. TA never sees valid EPP demand → always falls through to the
k\*-based local demand path.

**Also:** the skip-unknown `continue` in the 3 throughput loops masks key-skew (its comment
says "foreign pod" but these queries are model-scoped — a miss signals a bug, not noise).

**Files:** `internal/collector/replica_metrics.go` (scheduler loop ~L596; throughput loops
~L697-739), `registration/throughput_analyzer.go` (query groupby labels).

**Tests to add:**
- Collector test: pod present in scheduler metric with a *different* port than the instance
  label → `ArrivalRate` merges into the same `ReplicaMetrics` entry as KV data.
- Test: pod in throughput metric but not in KV metric → log a WARN (not silent skip).

**Review refs:** C-B1, C-B2, C-B3, C-D3, C-N5, C-S1.

---

### I-2 · Tier-2 ITL positivity guard [P1]

**What:** `resolveITLModel`'s constrained OLS path only checks `A > 0`; it does not verify
`A·DefaultKSat + B > 0`. With `lastFittedB` potentially negative (a valid Tier-1 B can be
slightly negative), Tier-2 can return a model where `ITLAt(k_sat) ≤ 0`. This is caught
downstream by the `itlSat <= 0` continue at `analyzer.go:270` — the variant is silently
skipped — but the asymmetry between Tier-1 and Tier-2 guards is a latent trap.

**Fix:** Factor a shared `validITLModel(A, B float64) bool` helper (checks `A > 0` AND
`A·DefaultKSat + B > 0`); use in both `FitITLModel` and `resolveITLModel`.

**Tests to add:** Tier-2 fit that yields valid A>0 but B negative enough that `A·kSat+B ≤ 0`
→ `resolveITLModel` returns `(_, false)`.

**Review refs:** A-B2, B-S1.

---

### I-3 · NaN k* not rejected in `ObservationWindow.Add` [P1]

**What:** `Add` checks `k < minK || k > maxK` (both false for NaN) so a NaN k passes the
range gate. Only ITL is NaN-checked. A NaN k appended to the window contaminates all
subsequent OLS fits until it ages out (30 min) or is displaced by 20 newer samples.

Currently defended by the collector's per-field guards (NaN k\* is filtered as
`KVOutOfRange`), but `Add`'s own contract is violated and one missing upstream guard
propagates to a 30-minute calibration disruption.

**Fix:** Add `math.IsNaN(k)` check at the top of `Add`; return `true` (dropped).

**Tests:** Confirm NaN k is rejected and `Len()` unchanged.

**Review refs:** A-B3.

---

### I-4 · A-B1 demand half: NaN/invalid k\* reaches `computeLocalDemand` [P2]

**What:** `computeVariantSupply` was fixed (I-1 from `34c9be9b`: uses nKV count, skips
`TotalKvCapacityTokens <= 0`). But `computeLocalDemand` still runs on the unfiltered
`variantMetrics` and only skips `m.KvUsageInstant <= 0` — it does not guard NaN or `k* > 1`.
A replica with `KvUsageInstant = NaN` or `1.5` reaches `model.ITLAt(k)`, producing a
potentially huge or NaN demand term.

**Fix:** Add `m.KvUsageInstant > 1 || math.IsNaN(m.KvUsageInstant)` guards in
`computeLocalDemand`, matching the sanitization `filterHealthyForShape` applies.

**Review refs:** A-B1 demand half.

---

## Group 2 — Silent error detection & observability

### I-5 · No log when TA is disabled; runtime configmap edit silently ignored [P0]

**What:**
1. When `throughputAnalyzerEnabled(cfg)` returns false at startup, there is *no log line*.
   An operator cannot confirm from logs whether TA evaluated the gate to false vs. code never
   reached that path.
2. The configmap reconciler runs live; an operator who adds `throughput` to the config at
   runtime sees the change accepted (it's stored in `cfg`) — but the registration is frozen
   after `StartOptimizeLoop`, so the edit silently has *no effect*. There is no warning.

**Fix:**
- Add an `else { setupLog.Info("ThroughputAnalyzer not registered — add 'throughput' to analyzers config and restart controller") }` branch.
- Emit a K8s Warning event (or at minimum a prominent `setupLog.Info`) whenever the
  configmap reconciler detects that the live config's TA-enabled state differs from the
  frozen registration state. The `K8SEventUnattributedReadyPods` precedent (same collector
  layer) shows how to do this.

**Review refs:** D-D3, D-D4, D-S4.

---

### I-6 · `FreshnessStatus` hardcoded "fresh" — staleness detection dead end-to-end [P1]

**What:** `replica_metrics.go` emits every `ReplicaMetrics` with `FreshnessStatus:"fresh"` and
`Age:0` unconditionally (line ~892), even though `trackMetricFreshness` just computed real
per-metric staleness into a local map. The sanity gate `m.Metadata.FreshnessStatus == "stale"`
in `sanity.go:53` is therefore *always* false → `SanityIssueStaleMetrics` is never raised →
stale k\*/ITL data enters the OLS fit without any exclusion.

**Fix:** Populate `FreshnessStatus`/`Age` from the worst per-pod per-metric timestamp at
assembly time. Or, if this is out of scope, delete `SanityIssueStaleMetrics` and the dead
`"stale"` branch to prevent false documentation of a safety gate that doesn't work.

**Review refs:** C-S5, B-N3 (dead branch in sanity.go).

---

### I-7 · nil-vs-zero for the three throughput fields (#1264) [P1]

**What:** `GenerationTokenRate`, `KvUsageInstant`, and `VLLMRequestRate` have no `has*`
sentinel. An absent k\* (pod not scraped for that query) is indistinguishable from a genuine
k\*=0 and flows into the OLS observation window as a real zero point, biasing the ITL(k)=A·k+B
fit toward the intercept.

**Fix:** Add `hasGenerationTokenRate`/`hasKvUsageInstant`/`hasVLLMRequestRate` boolean sentinels
to `podMetricData` (collector-internal) and exclude absent k\* from `ObservationWindow.Add` calls
and from `computeLocalDemand`/`computeVariantSupply`. The public-interface change (`*float64` in
`interfaces.ReplicaMetrics`) is issue #1264 and is a separate PR.

**Review refs:** C-D1, D-B1 (nil-vs-zero in sanity path).

---

### I-8 · TA calibration state has no Prometheus observability [P1]

**What:** There are no metrics gauges for:
- Observation window size and k-spread per variant
- Which tier (1=OLS, 2=constrained) is being used
- GPS mismatch count / consecutive mismatch streak
- `lastFittedB` / `hasFittedB` (indicates whether hardware baseline is learned)

These are the critical signals an operator needs to debug "TA is not scaling as expected."
Without them, diagnosing calibration issues requires debug-log analysis.

**Fix:** Add per-variant Prometheus gauges (labeled `namespace`/`model_id`/`variant`) for at
minimum: `wva_throughput_analyzer_obs_window_size`, `wva_throughput_analyzer_obs_kspread`,
`wva_throughput_analyzer_active_tier` (1 or 2), `wva_throughput_analyzer_gps_mismatch_streak`.
Expose `wva_throughput_analyzer_itl_model_{a,b}` (already noted in CURRENT.md Issues to Open).

---

### I-9 · SchedulerQueue wiring in engine_v2.go [P1]

**What:** `engine_v2.go` never calls `CollectSchedulerQueueMetrics`, so `AnalyzerInput.SchedulerQueue`
is always nil. Queue demand in the TA always equals 0. This is documented in the dev guide as a
known bug in a separate engine PR. Filing here so it doesn't get lost.

**Fix:** Wire `CollectSchedulerQueueMetrics` into the engine's per-model collection loop in
`engine_v2.go` before calling `Analyze`, and pass the result via `AnalyzerInput.SchedulerQueue`.

---

### I-10 · `throughputAnalyzerEnabled` gate ORs across all models — global registration [P2]

**What:** The gate iterates all models' saturation configs and returns `true` if *any* model
enables throughput. Registration is engine-global — one analyzer instance handles all models.
An operator who enables TA for one model registers it for *every* model, silently.
(The "per-cycle consumption gate" #1261 follow-up is the correct long-term fix; this item
covers the gap in the meantime.)

**Fix:** Document explicitly in code + dev guide that registration is global and which model's
config triggers it is irrelevant. Emit a log line naming which model's config entry triggered
registration.

---

## Group 3 — Test quality

### I-11 · Kill the split-contract test rot [P1]

**What:** ~20 unit assertions in `analyzer_test.go` are `Expect(RequiredCapacity).To(Equal(0.0))`
— unconditionally true because TA always leaves RC=0 and the engine post-step fills it.
The headline "scale up / scale down" tests assert an inequality that the test fixture itself
constructed; they would pass with tiering, GPS gating, or role aggregation completely broken.
The 5 GPS-fixture `It` blocks ("preserved fixtures for future SC gate") assert nothing and run
each CI cycle as no-ops with misleading names.

**Fix:**
1. Add one engine-integration test that creates a `ThroughputAnalyzer` + runs `Analyze` + applies
   the engine's universal threshold post-step and asserts a real RC or SC value. This is the unit
   that actually tests "TA produces a scale-up/down signal."
2. Delete the `== 0.0` assertions on RC/SC (they assert nothing) or add a comment block noting
   these are always-zero by design.
3. Convert the 5 GPS `It` blocks to `PIt` (Ginkgo pending) until the SC gate is re-added, so
   CI reports them as pending rather than meaningless pass.
4. Tighten the `muSat ± 10%` tolerance to ≤ 1% using in-test recomputed constants.

**Review refs:** A-D1, E-B1, E-B2, E-D1, E-D2.

---

### I-12 · `throughputAnalyzerEnabled` gate: zero unit tests [P1]

**What:** The gate that fixed the `saturation_v2_test.go:280` smoke failure has no unit tests.
Its three distinct branches (`absent → false`, `nil → true`, `*false → false`) and the
multi-entry OR behavior are untested.

**Fix:** Add a table test in `cmd/` (or extract the predicate to a testable internal package)
covering: no analyzers, throughput absent, `Enabled: nil`, `Enabled: &true`, `Enabled: &false`,
and multiple config entries where only one enables throughput.
Also add an integration-level assertion that the *default configmap* yields
`throughputAnalyzerEnabled == false`, pinning the "off by default" behavior in code.

**Review refs:** E-G1, D-D1.

---

### I-13 · Missing unit coverage for critical production branches [P1]

Specific gaps:
- **ITL-model guards** (E-G2): `NaN/Inf B` path and `A·kSat+B<=0` path in `FitITLModel` —
  neither rejection path has a test.
- **vLLM fallback demand** (E-G3): `computeDemand` vLLM branch — no test drives `Analyze` with
  `ArrivalRate=0, VLLMRequestRate>0`.
- **Collector throughput guards** (E-G4): NaN/Inf/out-of-range values for the 3 throughput fields
  (`kvUsageInstant=1.5`, `NaN`) should be dropped; not asserted.
- **GPS unit test** (E-G5): `checkVariantGPSMismatch` is never unit-tested directly (threshold
  boundary, low-k skip, zero-GPS skip, near-k_sat split).
- **Role mix** (E-G6): `aggregateRoleCapacities` "both"+"decode" combination not tested.
- **`Add` drop-bool through `Observe`** (E-G7): F4 drop-bool not asserted when k\* is out of
  range in `Observe`.

---

### I-14 · e2e test robustness [P1]

Three specific issues (review E-e1/E-e3/E-e4):

1. **Skip-on-restart-failure hides regressions** (E-e1): `restartWVAController` times out when
   the controller crash-loops → `Skip` → green-with-skips while the regression is live. Fix:
   distinguish RBAC/patch failure (legit Skip) from rollout timeout / unhealthy pods (should `Fail`).

2. **AfterAll restart is best-effort in 2 of 3 suites** (E-e3): smoke uses `Expect`, but the
   scale-up and TA-only `full` suites use `_ = restartWVAController(ctx)`, letting a timed-out
   restart leave TA registered and contaminating `saturation_v2_test.go:280`. Fix: `Expect` in all
   three AfterAll restarts. Add a defensive BeforeAll-restart-to-saturation-only on the `saturation_v2`
   suite so it's resilient to upstream cleanup failures.

3. **`restartWVAController` can return before the new config is read** (E-e4): the readiness
   poll checks `UpdatedReplicas >= 1 && ReadyReplicas == UpdatedReplicas` — the pre-restart
   state satisfies this immediately. Fix: gate on `dep.Status.ObservedGeneration >= dep.Generation`
   before evaluating replica readiness.

---

### I-15 · Collector event tests: positive edge missing [P1]

Three `TestCollectReplicaMetrics_Error*/NoMetrics*` tests can only assert the absence of an
event; the trigger edge ("available → error fires exactly one event") is untested. A bug that
never emits the event under any condition passes all three. Fix: seed `podData` (add a fake
source cycle), flip to error on cycle 2, assert exactly one event fires on the transition.
(The `_UnattributedReadyPodsEvent` test already does this correctly — model the others on it.)

**Review refs:** E-B3.

---

## Group 4 — Critical architectural follow-ups

### I-16 · effectiveEnabled per-cycle consumption gate [P1]

**What:** The registration gate in `cmd/main.go` is a stopgap. The correct fix is a per-cycle
consumption gate inside the engine (`effectiveEnabled`: absent entry → false, so runtime configmap
edits take effect without a restart). Plan: `planning/PR1266-fixup-effectiveEnabled.md`.

**When done:** the registration gate in `cmd/main.go` (`throughputAnalyzerEnabled`) and its
"requires restart" documentation should be removed.

---

### I-17 · Per-analyzer status return (#1261) [P2]

**What:** `AnalyzerResult` has no way to signal "suppress SpareCapacity" or "suppress
RequiredCapacity" to the engine. This blocks:
- Restoring the GPS-mismatch SC suppression gate (currently the dead `anyGPSMismatch` placeholder)
- Demand-gating on the sanity report (the `TODO(#1261)` in `analyzer.go:249`)
- EPP-absent SC suppression (the old pre-PR-5 behavior)

Filed as GitHub issue #1261. Requires extending the `interfaces.Analyzer` contract.

**Review refs:** A-D2.

---

### I-18 · Tier-3 knowledge store (zero-replica fallback) [P2]

**What:** `itl_knowledge_store.go` was removed in the merge. Tier-3 (scale-from-zero using the
last successful Tier-1 fit) is explicitly unimplemented. The `Analyze()` loop only iterates
variants with active replica metrics; zero-replica variants are invisible.

**Scope:** Requires restructuring `Analyze()` to iterate variants with state but no current
metrics (a separate pass), and persisting the last successful `ITLModel{A,B}` per variant
through scale-to-zero events.

**TA-Plan reference:** Phase 3 / `PR-4: Design Alternatives → Tier-3 knowledge store wiring`.

---

### I-19 · μ_RPS (request-rate supply model) [P3]

**What:** PR-X in `TA-Plan.md` Phase 3. Extend to request-rate-based supply (μ_RPS = req/s
per replica) vs demand (λ_req). Useful for models where output length varies widely across
requests (e.g. code generation) and tokens/sec supply is a poor proxy.

**Dependency:** Tier-1 μ_dec (shipped) must be validated first.

---

### I-20 · Prefill supply / TTFT prediction [P3]

**What:** PR-Y in `TA-Plan.md` Phase 3. Add TTFT knee prediction and N-based saturation
indicators for the prefill role. `TA-demand.md` has the multi-EPP queue-contribution design
(prefill queue contribution to decode demand deferred in #1250).

**Dependency:** Per-analyzer status return (#1261), disaggregated P/D E2E validation.

---

## Group 5 — Dev guide and documentation gaps

### I-21 · Dev guide PromQL examples are stale [P0]

**What:** `docs/developer-guide/throughput-analyzer.md` shows the three TA queries with
`sum by (pod)` / `max by (pod)` groupby. The actual registered queries (post A1 key-merge fix)
use `sum by (instance, pod, llm_d_ai_variant)`. An operator copying the PromQL example
from the doc will get wrong results (missing the instance key, missing the variant label).

**Location:** dev guide lines ~108, ~126, ~152 (PromQL code blocks) and the Query Design
Decisions table (~L200-210).

**Fix:** Update all three PromQL examples and the table to `instance, pod, llm_d_ai_variant`.
Also update the accompanying explanation of *why* `instance` is included (the key-merge
rationale).

---

### I-22 · Dev guide mentions removed `itl_knowledge_store.go` [P0]

**What:** The package structure section and Tier-3 calibration section still reference
`itl_knowledge_store.go` as "present in the package, not yet wired." The file was removed
before merge. An operator reading the dev guide cannot find this file; a contributor trying
to implement Tier-3 will be confused.

**Fix:** Remove the file from the package structure diagram; update the Tier-3 paragraph to
"tier-3 knowledge store is *not yet implemented*; the design is captured in `TA-Plan.md`
Phase 3" (or similar).

---

### I-23 · Dev guide `ReplicaCount` / supply section needs updating for `34c9be9b` [P1]

**What:** The supply section says `perReplicaSupply = totalSupply / n` — correct — but
does not explain that `n` (now `nKV`) excludes booting replicas, or that `ReplicaCount = nKV`
(not `len(variantMetrics)`). The distinction matters for understanding anticipated supply:
`PendingReplicas` covers the booting replicas, not `ReplicaCount`.

**Fix:** Add one paragraph in the Supply Estimation section explaining the `nKV` count and
its relationship to `PendingReplicas`, mirroring `34c9be9b`'s commit message.

---

### I-24 · User guide for the ThroughputAnalyzer is missing [P1]

**What:** There is a detailed dev guide (architecture, math, constants) but no *operator-facing*
user guide. An operator who wants to enable TA has to read the dev guide to understand it.
The user guide should cover: what TA does in plain language, when to enable it, what to expect
before calibration is complete (warm-up period, saturation-analyzer covers the gap), what
the key config fields mean (`score`, `enabled`, restart requirement), and how to tell if TA
is working (via logs and the observability metrics from I-8).

**Location:** `docs/user-guide/` (check where other user-guide docs live; there is a reference
to `user-guide/saturation-analyzer.md` in the dev guide's References section).

---

### I-25 · `DefaultKSat` / `DefaultBaselineITLSec` alignment [P2]

**What:** Two dev guide open items already identified:
- `DefaultKSat = 0.85` is per-TA-analyzer; needs alignment with EPP system-wide k_sat.
- `DefaultBaselineITLSec = 0.006` is H100-specific; non-H100 hardware (A100, AMD MI300X, etc.)
  will get wrong Tier-2 estimates before a Tier-1 fit succeeds.

**Fix:** (a) Wire into the EPP-visible k_sat config when that API exists. (b) Add a
per-accelerator-type baseline table or a configurable override for `DefaultBaselineITLSec`.
Until then, document the H100 assumption more prominently and note the impact on other hardware.

---

## Sequencing and suggested PR groupings

**Immediate (before TA is enabled in any production env):**

| Internal issue | Suggested PR | Rationale |
|---|---|---|
| I-21 (stale PromQL) | Fix dev guide — standalone, 1 commit | Doc-only, unblock operators |
| I-22 (knowledge store mention) | Same PR as I-21 | Doc-only |
| I-23 (ReplicaCount note) | Same PR as I-21 | Doc-only |
| I-5 (silent disabled / silent ignored) | Standalone PR, `cmd/main.go` only | Prevents the worst operator confusion; 1 commit |
| I-12 (gate unit tests) | Same PR as I-5 | Co-located; tests the same function |

**Next (quality debt before wide adoption):**

| Internal issues | Suggested PR | Notes |
|---|---|---|
| I-1 (collector key unification) | Collector correctness PR | Biggest correctness exposure; C-B1 to C-D3 |
| I-11 + I-13 + I-15 (test rot + gaps) | Test quality PR | Engine-integration test for RC/SC; GPS unit test; edge-case coverage |
| I-14 (e2e robustness) | E2E PR | Can be reviewed in isolation; `test/e2e/` only |

**Medium term:**

| Internal issues | Suggested PR | Notes |
|---|---|---|
| I-2 + I-3 + I-4 (math guards) | Math guards PR | Small, low-risk, cleanup |
| I-6 + I-7 (freshness + nil-vs-zero) | #1264 alignment PR | Pairs with issue #1264 |
| I-8 (observability metrics) | Metrics PR | New Prometheus gauges for calibration state |
| I-9 (SchedulerQueue wiring) | Engine PR (separate) | engine_v2.go, not TA itself |
| I-10 (global registration note) | Bundle with I-5 or standalone | Commentary + log, minimal code |
| I-24 (user guide) | User guide PR | Operator-facing doc |

**Architecture (P2/P3):**

| Internal issue | Notes |
|---|---|
| I-16 (effectiveEnabled) | Removes the restart requirement; plan at `planning/PR1266-fixup-effectiveEnabled.md` |
| I-17 (#1261 per-analyzer status) | Unlocks GPS SC gate + demand-gating-on-sanity |
| I-18 (Tier-3 knowledge store) | Scale-from-zero; requires loop restructure |
| I-19 (μ_RPS) | Phase 3 roadmap item |
| I-20 (prefill/TTFT) | Phase 3 roadmap item |
| I-25 (k_sat / baseline alignment) | Can be incremental: configurable override first |

---

## Dev guide accuracy audit — summary

| Section | Status | Issue |
|---|---|---|
| Configuration | ✓ Accurate | — |
| PromQL examples (3 query blocks) | **Stale** | I-21: `by (pod)` → `by (instance, pod, llm_d_ai_variant)` |
| Query Design Decisions table | **Stale** | I-21: same |
| Package structure (architecture) | **Stale** | I-22: mentions removed `itl_knowledge_store.go` |
| Tier 3 calibration | **Stale** | I-22: "present in package, not yet wired" — file removed |
| Supply Estimation | Mostly accurate | I-23: `nKV` / booting-replica distinction not explained |
| Demand Estimation | ✓ Accurate | EPP warm-up cascade described correctly (matches `34c9be9b`) |
| Known Regression (GPS SC gate) | ✓ Accurate | GPS gate was removed; correctly documented as follow-up |
| State and HA | ✓ Accurate | — |
| Analysis Pipeline diagram | ✓ Accurate | — |
| Scheduler Queue demand | ✓ Accurate | SchedulerQueue wiring bug noted inline |
| Constants and Tuning | ✓ Accurate | I-25: open items listed; H100 assumption documented |
| References | Minor | Points to plans-branch docs (`TA-Plan.md`) — fine but those are internal |
