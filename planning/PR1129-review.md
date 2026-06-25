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

## New findings (from design analysis)

### D1 — No-reload constraint is not prominently documented for operators

**Files:** `docs/developer-guide/quota-limiter.md`, `internal/config/config.go`, `internal/engines/pipeline/quota_inventory.go`

The quota file is read **once at startup** and the limiter is built once in `main.go` — there is no live-reload path. `QuotaInventory.Refresh()` is a deliberate no-op. This is documented in struct comments (`limiterConfig`: *"no live-reload path"*) and the `Refresh()` godoc, but the developer guide never says "restart required to change quotas."

This is a real operator footgun: a common Kubernetes pattern is to mount a ConfigMap as a file volume. Kubernetes silently hot-updates that file on disk. An operator who edits the quota ConfigMap will see the file change with zero effect on the running controller — the limiter object in memory is never replaced. No warning, no log message, no error.

**Suggested additions:**
1. A prominent note in the developer guide: *"Quota configuration is loaded once at startup. Changing the quota file while the controller is running has no effect; restart the controller to pick up changes."*
2. If the quota file path is accessible at runtime (it is — it's on `cfg.limiter.quotaConfigFile`), add a periodic or on-demand check that re-reads the file and logs a warning when the on-disk content differs from what was loaded. Even a startup-only hash comparison with a "file changed, restart required" warning in the controller logs would help.

### D2 — `--limiter-type` is a global switch; per-entry `type: quota` field is redundant and misleading

**Files:** `internal/config/quota_limiter.go`, `internal/engines/pipeline/limiter_factory.go`

The `--limiter-type` flag selects between `inventory` and `quota` modes globally for the entire controller. Within quota mode, every entry in the YAML file's `limiters` list MUST have `type: "quota"` — `Validate()` rejects any other value.

This means the `type` field on each `QuotaLimiterConfig` entry is presently useless: it can only ever be `"quota"` (if it's anything else the entry fails validation), and the choice of `inventory` vs `quota` is made at the flag level, not at the per-entry level. An operator reading the YAML schema might reasonably ask: *"Can I declare one cluster-scope entry as `type: inventory` and one namespace-scope entry as `type: quota`?"* The answer is no — but neither the developer guide nor the validation error message explains this clearly.

**Suggested clarifications:**
1. Developer guide: explicitly state that `--limiter-type` is a global switch; the `type` field on individual entries is a type discriminator reserved for future limiter types (e.g., `reservation`, `priority`) and must be `"quota"` for all current entries.
2. The validation error message for `type != "quota"` could say: *"type must be \"quota\" (the per-entry type discriminator; the global --limiter-type flag selects between inventory and quota modes)"*.

### D3 — Deny-by-default semantics are not clear in the configuration docs

**Files:** `docs/developer-guide/quota-limiter.md` — "Special values" table and "Namespace lookup rules"

The PR uses `"quota mode = closed allowlist"` semantics: any accelerator type or namespace not explicitly listed in the config is **denied** (treated as quota=0). This is the right default for a security-conscious resource cap, but the developer guide does not call it out directly.

Specific gaps:

**Cluster scope:** if an operator wants to cap H100 at 4 but leave A100 unlimited, they must write:
```yaml
quotas:
  H100: 4
  A100: -1   # must explicitly list to allow
```
If `A100` is simply omitted, all A100 allocation is denied. The special-values table only says "missing entry = denied" in passing; there is no example of "unlimited except for listed types" and no warning that unlisted GPU types are silently denied.

**Namespace scope + `default` key:** to allow unlimited GPUs for all namespaces except explicit caps, the operator must write `"default": {"H100": -1}`. But `-1` for the default key still requires enumerating every GPU type the operator wants to allow for unlisted namespaces. If a new GPU type (e.g., `B200`) is added to the cluster and the quota YAML is not updated, all B200 allocations are silently denied for any namespace relying on the default fallback.

**Suggested additions:**
1. A dedicated "deny by default" callout in the developer guide, early in the Configuration section: *"Any accelerator type or namespace not explicitly listed (or covered by the `default` key) is denied. This is intentional; add `-1` for types you want to leave uncapped."*
2. An example in the namespace scope section showing "unlimited for all namespaces/types except explicit caps" with a note about the per-GPU-type enumeration requirement.

### D4 — Fair-share semantics with heterogeneous quotas are undocumented; behavior may surprise operators

**Files:** `internal/engines/pipeline/greedy_score_optimizer.go` — `fairShareScaleUp`, `allocateForModel`, `effectiveAvailable`; `docs/developer-guide/quota-limiter.md`

The V2 `GreedyByScoreOptimizer` fair-share algorithm is **saturation-need-based and model-count-based**, not quota-aware. The mean is computed as `totalClusterGPUs / numActiveModels`. Namespace quotas act as hard upper bounds applied after the mean is set — they do not weight the fair-share calculation.

**Worked example — what actually happens:**

3 models across 3 namespaces, cluster quota 8 GPUs of type A100:
- M1 (NS1): saturation deficit = 3 GPUs, namespace quota = 2
- M2 (NS2): saturation deficit = 4 GPUs, namespace quota = 4
- M3 (NS3): saturation deficit = 4 GPUs, namespace quota = 4

_Round 1:_ mean = 8 / 3 ≈ 2.67. M2 and M3 process first (higher deficit). Each gets ≈ 2.67 (not quota-constrained since quota 4 > mean 2.67). M1 processes last; quota of 2 caps it below the mean — it gets 2, not 2.67. Cluster remaining after round 1: ≈ 0.67.

_Round 2:_ M1 is satisfied (got its max). M2 and M3 still need ≈ 1.33 each. Mean = 0.67 / 2 ≈ 0.33. Each gets ≈ 0.33 more.

_Final:_ M1 = 2, M2 ≈ 3, M3 ≈ 3.

**The outcome is correct,** but the path matters:

1. The 0.67 GPUs freed by M1's quota undershoot are only available to M2/M3 in **round 2**, not round 1. Within a single cycle with many models, this delay is fine — the loop iterates until no further allocation is possible. But it is not documented.

2. **Fair share is per-model, not per-namespace.** If NS1 has 3 models and NS2 has 1 model, NS1's models occupy 3 fair-share slots. NS1 collectively gets 3× the mean allocation per round relative to NS2, regardless of their respective quotas. An operator who expects "each namespace gets an equal share of the cluster" will be surprised.

3. **Quota size is not a scheduling weight.** A namespace with quota 100 has no priority advantage over one with quota 4. The quota only prevents the large-quota namespace from exceeding its cap; it does not entitle it to proportionally more fair-share rounds.

**Suggested additions to developer guide:**
- A "Fair-share interaction" section in `docs/developer-guide/quota-limiter.md` (or the optimizer doc) explaining: fair share is computed relative to model count and saturation need, not relative to quota size; quotas are hard ceilings, not weights; fairness is per-model, not per-namespace. The worked example above (or a simplified version) would make this concrete.

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
