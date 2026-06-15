# PR #1129 Review — Quota-based limiter

**Status: DRAFT**
**PR:** [#1129](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1129)
**Author:** ev-shindin
**Filed:** 2026-05-13 | **Base:** main | **State:** open, no reviews yet
**Scale:** 23 files, +2481/−20 lines, 11 commits
**Reviewed:** 2026-06-15

---

## What it does

Adds a quota limiter as a startup-selectable alternative to physical GPU inventory discovery. Operators pick one mode via `--limiter-type`:

- `inventory` (default) — today's path; `TypeInventory` + GPU operator
- `quota --quota-config-file=/path/to/yaml` — pure operator-declared caps; **no Node API access**

New pieces: `QuotaInventory` (implements `Inventory`), `NamespaceAwareInventory` interface extension, `CompositeLimiter` (sequences entries), `NoOpLimiter` (test zero-value), `limiter_factory.go` (startup dispatch), config plumbing, `shouldCollectClusterInventory` gate in the saturation engine.

Architecture is clean. The `NewEngine` signature gains `gpuLimiter` (all three test callers updated). 69 new Ginkgo specs. Closes issue #1002.

---

## Findings

### B1 — `clampPoolLimit` makes `Limit=0` ambiguous in `GetResourcePools` output

**File:** `internal/engines/pipeline/quota_inventory.go` — `clampPoolLimit` + `GetResourcePools`

`clampPoolLimit(-1)` returns 0, relying on an implicit convention that `ResourcePool{Limit:0}` means "no constraint." But `Limit=0` also means "deny all" (a quota entry of 0). Any downstream code reading `GetResourcePools()` output cannot distinguish unlimited from zero-quota without going back to the original config. The allocator itself checks the original config value (so TryAllocate is correct), but the pool representation loses the distinction for observers.

**Suggested fix:** Add a separate `Unlimited bool` field to `ResourcePool`, or use a sentinel (e.g., `Limit=-1`) that is distinct from zero. At minimum, document the convention explicitly on `ResourcePool.Limit` and in the developer guide.

### B2 — Namespace-scope quota silently skipped on the V2 optimizer path

**File:** `internal/engines/pipeline/default_limiter.go` — `ComputeConstraints` + added comment

The comment acknowledges: *"namespace-aware constraints are not yet exposed via this method because the optimizer's ResourceConstraints shape is per-type."* If quota mode + namespace scope is deployed and the V2 optimizer path is active, namespace caps are silently unenforced. Whether this is currently reachable depends on which analyzer paths invoke `ComputeConstraints` vs `Limit()`.

**Suggested action:** File a follow-up issue (or add to #1003). Clarify in the developer guide or `ComputeConstraints` godoc whether namespace-scoped quota + V2 path is a supported combination today.

### N1 — `CompositeLimiter` comment mixes up `CurrentReplicas` and `TargetReplicas`

**File:** `internal/engines/pipeline/composite_limiter.go` — `Limit` comment

> "the decisions slice is the source of usage truth (see DefaultLimiter.calculateUsedGPUs), so each constituent sees the already-capped TargetReplicas from earlier constituents."

`calculateUsedGPUs` uses `CurrentReplicas`, not `TargetReplicas`. What makes most-restrictive-wins work is that `TryAllocate` receives the already-mutated `TargetReplicas`. Behavior is correct; the explanation is wrong. Nit but someone reading this to understand ordering semantics will be confused.

**Suggested fix:** "each constituent's `TryAllocate` call receives the `TargetReplicas` already reduced by earlier constituents; later constituents can only further cap, not increase."

### N2 — `Remaining()` over-reports when the `default` key fires for unlisted namespaces

**File:** `internal/engines/pipeline/quota_inventory.go` — `quotaAllocator.Remaining()`

`Remaining()` iterates `NamespaceQuotas` keys and skips `QuotaLimiterReservedNamespaceKey`. If unlisted namespaces are consuming quota via the default fallback, their usage is in `usedByNS[concrete-ns]` but `Remaining()` doesn't see those entries. Remaining can be higher than actual remaining. Currently Remaining is used for reporting only, so not a correctness bug, but worth a doc note.

### N3 — `"PR-1"` in a code comment

**File:** `internal/config/config.go` — `LimiterType` godoc

> "mutually exclusive in PR-1 — composing physical and quota bounds"

PR numbers in code comments don't age well. Suggest: "mutually exclusive in the initial implementation — composing physical and quota bounds is tracked in sub-issue #1003."

### N4 — CompositeLimiter partial-mutation comment slightly misleading on error path

**File:** `internal/engines/pipeline/composite_limiter.go` — `Limit` behavior doc

> "decisions made by earlier constituents stay applied (TryAllocate's in-memory usage updates are per-allocator, so partial commits do not leak)"

On error from constituent B, decisions mutated by constituent A (TargetReplicas reductions) do stay. The "do not leak" claim is only true for per-allocator usage state, not decisions slice mutations. Since an error aborts the cycle this is not a correctness problem. The comment could be clarified.

---

## Confirmed correct

- Most-restrictive-wins semantic is correct (despite the comment inaccuracy in N1)
- `QuotaInventory` mutex usage is correct; per-cycle allocator is appropriately non-reentrant
- `QuotaEntries()` deep copies — external mutation of config state blocked
- `shouldCollectClusterInventory` gate is clean, well-tested, correctly returns false for unknown types (empty string, "bogus")
- Validation accumulates all errors via `errors.Join` — good operator UX
- `SetLimiterForTest`/`ReloadQuotaForTest` exported from non-`_test.go` is correctly justified (cross-package test visibility constraint)
- All three `NewEngine` callers updated with `NewNoOpLimiter`
- The `default` reserved key collision with the K8s `default` namespace is prominently documented in both code and developer guide
- `loadQuotaLimiterEntries` correctly no-ops when `limiterType != LimiterTypeQuota`
- `QuotaForNamespace` return contract (`nil,true` for excluded; `map,false` for found/default; `empty-map,false` for strict-allowlist miss) is consistent with allocator usage

---

## Summary

Two behavioral items (B1, B2) worth raising with ev-shindin; four nits (N1–N4) that could be addressed or let go. B1 is the stronger one — the `Limit=0` ambiguity affects any future downstream consumer of `GetResourcePools()` output. B2 is mostly a documentation gap.
