# PR #1129 Review — Quota-based limiter

**Status: DRAFT**
**PR:** [#1129](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1129)
**Author:** ev-shindin
**Filed:** 2026-05-13 | **Base:** main | **State:** open, no reviews yet
**Scale (rev 2):** 31 files, +3763/−40 lines, 1 squashed commit (`2db0e361`)
**Last updated:** 2026-06-21
**Reviewed:** 2026-06-25

---

## What it does

Adds a quota limiter as a startup-selectable alternative to physical GPU inventory discovery. Operators pick one mode via `--limiter-type`:

- `inventory` (default) — today's path; `TypeInventory` + GPU operator
- `quota --quota-config-file=/path/to/yaml` — pure operator-declared caps; **no Node API access**

Rev 2 (squash) significantly expanded the scope beyond rev 1: the V2 optimizer path (GreedyByScore) now enforces namespace quotas with full V1/V2 parity.

New pieces: `QuotaInventory` (implements `Inventory` + `NamespaceAwareInventory`), `CompositeLimiter`, `NoOpLimiter`, `limiter_factory.go`, `ResourceConstraints.NamespacePools`, `ComputeConstraints` signature extension, `effectiveAvailable` in `GreedyByScoreOptimizer`, `computeCurrentGPUUsageByNamespace` + `gpuConstraintProviders` in `engine_v2.go`, config plumbing, `shouldCollectClusterInventory` gate. Closes issue #1002.

---

## Status of rev-1 findings

| Finding | Status |
|---------|--------|
| B1 — `clampPoolLimit` makes `Limit=0` ambiguous | **FIXED** |
| B2 — namespace quota silently skipped on V2 path | **FIXED** |
| N1 — `CompositeLimiter` comment mixes up `CurrentReplicas`/`TargetReplicas` | not addressed |
| N2 — `Remaining()` over-reports for default-key consumers | not addressed |
| N3 — `"PR-1"` in code comment | not addressed |
| N4 — CompositeLimiter error-path comment slightly misleading | not addressed |

---

## How B1 and B2 were fixed

### B1 fix — `GetResourcePools` now omits unlimited entries; `Limit<0` sentinel for namespace pools

`GetResourcePools()` (cluster scope) and `aggregateNamespacePools` both skip entries where `limit == QuotaUnlimited`, so an absent pool unambiguously means "no cap" and `Limit=0` unambiguously means "deny." `GetNamespaceResourcePools()` uses `Limit < 0` as an explicit "unlimited" sentinel in per-namespace pools (distinguishing it from "type not listed" which is a deny). `ResourcePool.Available()` carries a warning comment for callers that may see the sentinel. `mergeConstraints` skips negative-Limit pools. The convention is now correct and documented.

### B2 fix — V2 path now fully parity with V1

`ComputeConstraints` signature extended to `(ctx, usageByType, usageByNamespace)`. `ResourceConstraints` gains `NamespacePools map[string]map[string]ResourcePool`. When the inventory is `NamespaceAwareInventory`, `ComputeConstraints` calls `GetNamespaceResourcePools(activeNamespaces)` and populates `NamespacePools`; it also re-derives `Pools` from `aggregateNamespacePools` over the active set (so the cluster-level budget is consistent with what the optimizer partitions). `GreedyByScoreOptimizer.allocateForModel` calls `effectiveAvailable(available, nsBudget)` to build a per-model effective budget that enforces the closed-allowlist contract: a type not listed by the namespace is absent from `effAvail` and denied. `gpuConstraintProviders` extracts providers from `CompositeLimiter` constituents so multi-entry quota configs are all consulted.

---

## Remaining findings

### N1 — `CompositeLimiter.Limit` comment still mixes up `CurrentReplicas` and `TargetReplicas`

**File:** `internal/engines/pipeline/composite_limiter.go` — `Limit` method comment

> "the decisions slice is the source of usage truth (see DefaultLimiter.calculateUsedGPUs), so each constituent sees the already-capped TargetReplicas from earlier constituents."

`calculateUsedGPUs` uses `CurrentReplicas`, not `TargetReplicas`. The most-restrictive-wins property comes from `TryAllocate` receiving the mutated `TargetReplicas` — not from `calculateUsedGPUs`. Behavior is correct; the comment is wrong.

**Suggested fix:** "each constituent's `TryAllocate` receives the `TargetReplicas` already reduced by earlier constituents; later constituents can only further cap, not increase."

### N2 — `quotaAllocator.Remaining()` under-counts when the `default` key applies

**File:** `internal/engines/pipeline/quota_inventory.go` — `quotaAllocator.Remaining()`

`Remaining()` iterates over `NamespaceQuotas` keys and skips `QuotaLimiterReservedNamespaceKey`. If unlisted namespaces are consuming budget via the default-key fallback, their usage is tracked in `usedByNS[concrete-ns]` but `Remaining()` doesn't iterate those keys — it only looks at statically-declared namespace keys. Remaining can over-report. Currently used for reporting only (not allocation correctness), but worth a comment/docstring noting the limitation.

### N3 — `"PR-1"` in two places

**Files:**
- `internal/config/config.go` — `LimiterType` godoc: *"mutually exclusive in PR-1 — composing physical and quota bounds"*
- `docs/developer-guide/quota-limiter.md` — Startup wiring table: *"The two are mutually exclusive in PR-1 — quota mode does not consult physical inventory."*

Both references. PR numbers in code comments and shipped docs don't age well — the PR closes and the reference becomes meaningless. Suggest: "mutually exclusive in the initial implementation — composing physical and quota bounds is tracked in sub-issue #1003."

### N4 — CompositeLimiter error-path comment slightly misleading

**File:** `internal/engines/pipeline/composite_limiter.go` — struct-level comment

> "decisions made by earlier constituents stay applied (TryAllocate's in-memory usage updates are per-allocator, so partial commits do not leak)"

On error from constituent B, decisions mutated by constituent A (TargetReplicas reductions) do remain. The "do not leak" claim is only true for per-allocator usage state, not for decisions slice mutations. Since an error aborts the cycle this is not a correctness problem, but the claim is misleading.

---

## New observation — `effectiveAvailable` / `math.MaxInt` sentinel

**File:** `internal/engines/pipeline/greedy_score_optimizer.go` — `effectiveAvailable`

When a namespace has an unlimited quota for a type AND the cluster has no cap for that type, `effectiveAvailable` sets `eff[accType] = math.MaxInt`. This path appears safe in practice: the developer guide explicitly notes that "a purely unlimited namespace-quota config with no finite cluster cap does not scale under the V2 GreedyByScore optimizer (its fair-share loop stops when the finite cluster aggregate is zero)." Since the cluster has no cap for the type, `available[accType]` is absent, so the fair-share loop assigns no allocation target for that type — `math.MaxInt` in `effAvail` is never reached. **No new finding; the math.MaxInt path is dead code in the optimizer's normal flow.** However, there is no test exercising the unlimited-namespace-type path end-to-end through the `GreedyByScore` optimizer. Worth a note for future reviewers, but not a blocking issue.

---

## Confirmed correct (rev 2)

All items from rev 1 confirmed correct still hold. Additionally:

- `GetResourcePools` (namespace scope) now correctly aggregates only finite pools; unlimited omitted → no ambiguity
- `GetNamespaceResourcePools` closed-allowlist contract is consistent with V1 `tryAllocateNamespace` semantics (documented and tested)
- `aggregateNamespacePools` derives the cluster Pools aggregate from active namespaces (not the static config total), keeping it consistent with what the optimizer partitions
- `mergeNamespaceConstraints` + `tighterBudget` + `nsPoolBudget` correctly handle the unlimited sentinel (-1) — well tested
- `effectiveAvailable` correctly enforces the closed allowlist (types not in `nsBudget` are absent, not zero) — prevents cross-namespace quota leakage
- Reconcile loop in `allocateForModel` only decrements cluster budget for types that cluster caps, and only decrements namespace budget for finite caps — correct
- `computeCurrentGPUUsageByNamespace` materializes every request's namespace (including zero-replica new deployments) ensuring new-to-scale namespaces are still constrained
- `gpuConstraintProviders` correctly handles `NoOpLimiter` → nil providers → falls back to unlimited (cost-aware) optimizer
- `ComputeConstraints` signature change propagated to all callers

---

## Summary

B1 and B2 fully resolved. The PR is substantially stronger in rev 2. Remaining open items are N1–N4, all minor (comment/doc nits). No new behavioral findings. Suggest raising N1, N2, N3 with ev-shindin — N3 appears in both source code and the shipped developer guide so that's the most concrete one to call out.
