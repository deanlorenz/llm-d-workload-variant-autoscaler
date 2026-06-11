# PR #1250 Review Summary

**Status: DRAFT**

**PR:** [engines/analyzers/throughput: ThroughputAnalyzer — ITL model, scaling signal, and engine wiring](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1250)
**Head:** `dbf3a98`
**Reviewed:** 2026-06-11

---

## CI

- ✅ DCO
- ✅ check-code-changes (both triggers)
- ✅ check-full-tests
- ✅ lint-and-test
- ✅ e2e-tests-smoke
- ✅ kustomize-build
- ✅ gate / gatekeeper
- ✅ doc-only-status
- ✅ remove-lgtm / signed-commits
- ⏭ report-status, assign-to-original-author, build-image, e2e-openshift, e2e-tests-full (all expected skips)

---

## Review Status

ev-shindin: **COMMENTED** (no APPROVED yet). Strongly positive overall tone. One rebase-gated blocker, two documented-regression acknowledgment requests, one advisory.

---

## Comment Threads

### ev-shindin — review body

Overall assessment positive: division guards solid throughout (`safeDivide`, `<=0` skips, count/weight fallbacks), doc comments carry domain notation, test coverage (+1385 lines) excellent, engine wiring (`RegisterAnalyzer` error handled) clean.

Flags: (1) PR base `badc48be` is behind current `main`; rebase required. The `by (pod)` change in the three throughput queries becomes a functional bug on current main — see inline threads. (2) #1246 already merged, so rebasing brings it in automatically.

### ev-shindin — inline threads

**`internal/collector/registration/throughput_analyzer.go` lines 108, 120, 133 — open, unanswered**
Same issue on three queries. TA3 drops `llm_d_ai_variant` from `by ()`. On the old base, pod→VA was via `FindVAForPod` (owner traversal) so dropping the label was harmless. On current `main`, pod→VA attribution reads `llm_d_ai_variant` off the metric series (`replica_metrics.go:319`). After rebase, `by (pod)` strips the label → collector gets empty `vaName` → `groupByVariant` sees nothing → analyzer receives no decode-rate / k* data → no signal.

Two options offered: **(A)** restore the label in all three queries now; **(B)** wait for #1260 (pod→VA derivation, implements #1210) to merge — collector then derives pod→VA itself, `by (pod)` is correct as-is.

**Decision: Option A (revised) — key-mismatch bug discovered; no #1260 dependency.**
Post-triage analysis found a pre-existing key-mismatch bug (introduced in #1051/TA1): the three throughput processing loops in `replica_metrics.go` use bare `value.Labels["pod"]` as the `podData` map key, while all other loops use `buildInstanceKey()` → composite `"pod:port"`. The entries never merge; `GenerationTokenRate`, `KvUsageInstant`, `VLLMRequestRate` are always zero. Fixing this requires `instance` in the `by()` clause (so `buildInstanceKey()` has the label it needs).

Full fix: `by (pod)` → `by (instance, pod, llm_d_ai_variant)` in all 3 queries (matching the saturation pattern) + use `buildInstanceKey()` in the 3 processing loops. The `llm_d_ai_variant` addition is temporary; it is removed post-#1260+[#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263). See [`planning/TA3.1-plan.md`](TA3.1-plan.md) § Complete #1250 for full coder task.

Follow-up posted ([issuecomment-4685034585](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1250#issuecomment-4685034585)) explaining key-mismatch discovery, Option A switch, and push.

**`internal/engines/analyzers/throughput/analyzer.go` line 343 — open, unanswered**
GPS-mismatch / no-EPP spare-capacity gate was computed but then discarded (Known Regression in PR). Reviewer asks to link a follow-up issue and explicitly call out the scale-**down** risk: a wrong ITL model or EPP-absent variant can publish spare capacity and drive scale-down on uncertain data.

**Resolution:** Deferred to [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) (analyzer interface extension). The fix is not a simple gate restore but a richer result type from the analyzer interface that lets the optimizer decide whether to accept a result for SC/RC/all. PR doc should note scale-down risk with issue link. ITL(k*) fallback mechanism limits the risk: implausible model parameters trigger a conservative (high-ITL) estimate → supply is conservative → SC less likely.

**`internal/engines/analyzers/throughput/analyzer.go` line 243 — open, unanswered**
`OK`-failing sanity report does not skip the variant; stale/invalid metrics flow into `computeDemand`. Reviewer asks: confirm acceptable, or gate the demand path on `lastSanityReport`.

**Resolution:** Deferred to [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) (same issue — analyzer interface extension + sanity helper mechanism). See λ_dec analysis below — the existing fallback cascade in `computeDemand` already degrades gracefully; the risk is bounded. PR doc should note the deferral with issue link.

**`internal/engines/analyzers/throughput/analyzer.go` line 208 — open, unanswered**
`Analyze` lock sequence (role-update lock → `Observe` internal lock → main lock) is safe under the single-threaded optimize loop, but a concurrent `VariantState()` snapshot could observe partial state. Reviewer flags it as "fine to leave" — just requests a one-line comment that `Analyze` is assumed single-flight.

**Resolution:** Add the one-line comment. Low effort, uncontroversial.

---

## Pending Actions

**Bugs to fix before rebase (coder task — see `planning/TA3.1-plan.md` § Complete #1250):**
- [ ] **Bug A** — `internal/collector/registration/throughput_analyzer.go`: `by (pod)` → `by (instance, pod, llm_d_ai_variant)` in 3 queries; add preserve comments.
- [ ] **Bug A** — `internal/collector/replica_metrics.go`: replace bare `podData[podName]` key with `podData[instanceKey]` via `buildInstanceKey()` in 3 throughput loops.
- [ ] **Bug B** — `analyzer.go:208`: add single-flight assumption comment.
- [ ] **Bug B** — `analyzer.go:343` and `:243`: update TODO comments linking [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261).

**Planner actions (already done):**
- [x] Reply posted: Option B (gated on #1260) — note: superseded by Bug A discovery; Option A now applies with `instance` added.
- [x] [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) opened for SC-gate + sanity extension.

**Remaining planner actions:**
- [ ] Update PR description: scale-down risk callout + [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261) link — draft for Dean, post after coder pushes.
- [ ] Rebase TA3 onto current main after bug fixes; push (needs Dean's approval).

---

## Discussion

### Rebase impact analysis

**Direct file conflicts (only one):** `cmd/main.go`.

TA3 adds: `registration` and `throughput` imports; `RegisterThroughputAnalyzerQueries` + `RegisterAnalyzer` calls just before `engine.StartOptimizeLoop`.

#1260 adds (inferred from PR description): new `internal/collector/podvamap` package; `APIReader` field in engine; wiring in `cmd/main.go` to pass `mgr.GetAPIReader()` into the engine; changes in `replica_metrics.go` to use the derived map rather than the label.

The `cmd/main.go` conflict is likely mechanical — TA3 adds at the end of the engine-init block; #1260 adds APIReader wiring in a different part of main. Both changes are logically independent and should resolve cleanly. Risk: low.

**Semantic non-conflict:** TA3's `registration/throughput_analyzer.go` (new file, not in #1260's diff) registers queries using `by (pod)`. After #1260 lands, the collector derives pod→VA from `podvamap.Lookup` rather than the `llm_d_ai_variant` label on the metric series. TA3's queries drop `llm_d_ai_variant` from `by()` — this is exactly correct for the post-#1260 world. No semantic conflict; no code change needed.

**Verification needed post-rebase:**
1. Run `make test` — confirm no regressions.
2. Run E2E smoke to confirm the throughput analyzer receives non-empty `byVariant` data (signal flows end-to-end through the new podvamap derivation path).
3. Check that `groupByVariant` keyed by podvamap-derived vaName correctly routes decode-rate / k* metrics to the throughput analyzer's variant states.
4. Sweep comments in `throughput_analyzer.go` lines 108/120/133 — remove or update any `Preserves llm_d_ai_variant …` language if it exists (the label is intentionally absent post-#1260).

### λ_dec accuracy under sanity failures

**`computeDemand` has a three-level fallback cascade:**
1. **EPP path:** `λ_dec = Σ ArrivalRate_r × AvgOutputTokens_r` (when EPP deployed and reporting)
2. **vLLM rate fallback:** `λ_dec = Σ VLLMRequestRate_r × AvgOutputTokens_r` (EPP absent)
3. **Local demand (scale-up only):** `λ_local = Σ k_r* × KV_max_r / KVreq / ITL(k_r*)` (both rates unavailable)

Path 3 is annotated in code as scale-up only. When EPP and vLLM rate metrics are both stale/absent, the system falls to the k*-based path — which can signal scale-up but cannot drive a false SC.

**Sanity issues mapped to λ_dec impact:**

| Issue | Affects paths | Mitigation |
|---|---|---|
| `SanityIssueStaleMetrics` | EPP + vLLM rate paths (ArrivalRate, VLLMRequestRate stale) | Cascade falls to k*-local (scale-up only) |
| `SanityIssueMissingShape` | EPP + vLLM rate paths (AvgOutputTokens bad) | `hasShape` guard at top of variant loop skips variant entirely if shape invalid |
| `SanityIssueMissingKV` | Local path only | `TotalKvCapacityTokens <= 0` guard in `computeLocalDemand` excludes replica |
| `SanityIssueKVOutOfRange` | Local path only | `KvUsageInstant <= 0` guard in `computeLocalDemand` excludes replica |
| `SanityIssueITLNonPositive` | Local path (ITL(k*) computation) | ITL model fallback handles bad AvgITL; `itlAtK <= 0` guard excludes replica |
| `SanityIssueNoReplicas` | All paths | No metrics → `computeDemand` returns 0 → variant skipped |

**Conclusion:** Sanity failures do not create a path to false SC on the demand side. The worst-case degradation is that λ_dec goes to 0 (no viable path for any replica) → `demand = 0` → variant contributes no SC signal from its demand ratio. The supply side is protected separately by the ITL(k*) fallback (bad model parameters → conservative high-ITL supply estimate → SC suppressed there too).

The reviewer's concern is real as a design gap — sanity failures should produce a richer result code rather than silently falling through — but TA3 is not in a dangerous state while the issue is open. The deferral is reasonable.

**Issue scope:** the analyzer interface extension should cover: (1) a richer return type letting the optimizer decide accept-for-SC / accept-for-RC / accept-all based on analyzer-reported status; (2) a sanity-helper mechanism so analyzers have a standard way to run metric checks and populate that status. This subsumes the specific GPS/EPP gate and generalizes it.
