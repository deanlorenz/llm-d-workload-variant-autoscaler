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

Rev 2 (squash) significantly expanded scope: the V2 optimizer path (GreedyByScore) now enforces namespace quotas with full V1/V2 parity.

New pieces: `QuotaInventory` (implements `Inventory` + `NamespaceAwareInventory`), `CompositeLimiter`, `NoOpLimiter`, `limiter_factory.go`, `ResourceConstraints.NamespacePools`, `ComputeConstraints` signature extension, `effectiveAvailable` in `GreedyByScoreOptimizer`, `computeCurrentGPUUsageByNamespace` + `gpuConstraintProviders` in `engine_v2.go`, config plumbing, `shouldCollectClusterInventory` gate. Closes issue #1002.

---

## Status of rev-1 findings

| Finding | Status |
|---------|--------|
| B1 — `clampPoolLimit` makes `Limit=0` ambiguous | **FIXED** |
| B2 — namespace quota silently skipped on V2 path | **FIXED** |
| N1 — `CompositeLimiter` comment mixes up `CurrentReplicas`/`TargetReplicas` | not addressed |
| N2 — `Remaining()` over-reports for default-key consumers | not addressed |
| N3 — `"PR-1"` in code comment and developer guide | not addressed |
| N4 — CompositeLimiter error-path comment slightly imprecise | not addressed |

---

## How B1 and B2 were fixed

### B1 — `GetResourcePools` now omits unlimited entries; `Limit<0` sentinel for namespace pools

`GetResourcePools()` and `aggregateNamespacePools` skip entries where `limit == QuotaUnlimited`, so an absent pool unambiguously means "no cap" and `Limit=0` unambiguously means "deny." `GetNamespaceResourcePools()` uses `Limit < 0` as an explicit "unlimited" sentinel in per-namespace pools, distinguishing it from "type not listed" (a deny). `ResourcePool.Available()` carries a caller warning. `mergeConstraints` skips negative-Limit pools. The convention is correct and documented.

### B2 — V2 path now fully parity with V1

`ComputeConstraints` extended to `(ctx, usageByType, usageByNamespace)`. `ResourceConstraints` gains `NamespacePools`. When the inventory is `NamespaceAwareInventory`, `ComputeConstraints` populates `NamespacePools` and re-derives `Pools` from `aggregateNamespacePools` over active namespaces. `GreedyByScoreOptimizer.allocateForModel` uses `effectiveAvailable(available, nsBudget)` to enforce the closed-allowlist contract. `gpuConstraintProviders` extracts providers from `CompositeLimiter` constituents.

---

## Nits (N1–N4, not addressed)

### N1 — `CompositeLimiter.Limit` comment

`internal/engines/pipeline/composite_limiter.go` — "the decisions slice is the source of usage truth (see `calculateUsedGPUs`), so each constituent sees the already-capped `TargetReplicas`." `calculateUsedGPUs` uses `CurrentReplicas`, not `TargetReplicas`. What makes most-restrictive-wins work is that `TryAllocate` receives the already-mutated `TargetReplicas`. Behavior correct, comment misleading.

### N2 — `quotaAllocator.Remaining()` over-reports for default-key consumers

`internal/engines/pipeline/quota_inventory.go` — `Remaining()` iterates `NamespaceQuotas` keys and skips `QuotaLimiterReservedNamespaceKey`. Namespaces consuming via the `"default"` fallback have their usage in `usedByNS[concrete-ns]` but aren't counted in `Remaining()`. Reporting-only, not allocation correctness.

### N3 — `"PR-1"` in two places

`internal/config/config.go` (`LimiterType` godoc) and `docs/developer-guide/quota-limiter.md` (startup wiring table) both say "mutually exclusive in PR-1." Better: "mutually exclusive in the initial implementation — composing physical and quota bounds is tracked in sub-issue #1003."

### N4 — CompositeLimiter error-path comment

`internal/engines/pipeline/composite_limiter.go` — "partial commits do not leak." True for per-allocator usage state; `TargetReplicas` mutations from earlier constituents do stay on error. Errors abort the cycle so it's not a correctness issue, but the claim is slightly imprecise.

---

## Design / docs findings (from analysis)

### D1 — No-reload lifecycle not documented for operators

The quota file is loaded once at startup; `QuotaInventory.Refresh()` is a deliberate no-op. Code comments note "no live-reload path" but the developer guide doesn't say so. Worth adding a note: "Quota configuration is read once at startup; restart the controller to apply changes." This matters in practice because Kubernetes silently hot-updates ConfigMap-mounted files on disk, so an operator editing the quota ConfigMap will see no effect without a restart.

### D2 — Relationship between `--limiter-type` (global flag) and per-entry `type:` field

`--limiter-type` is a global switch: `inventory` or `quota` for the entire controller. Within quota mode, every YAML entry must have `type: "quota"` — any other value fails validation. The `type` field is a discriminator reserved for future limiter types, not a way to mix inventory and quota entries per limiter. The developer guide doesn't make this relationship explicit; an operator reading the schema may wonder whether `type: inventory` is valid in an entry.

### D3 — (Withdrawn)

"0 or missing entry → denied" is in the special-values table. Residual note: the `"default"` key in `namespaceQuotas` still requires enumerating every GPU type the operator wants to allow for unlisted namespaces; a new GPU type added to the cluster is silently denied unless the YAML is updated. This is a natural consequence of the design, not a gap in the implementation.

### D4 — Fair-share interaction with heterogeneous namespace quotas

The developer guide covers V2 namespace enforcement but doesn't describe how quotas interact with the fair-share loop. The fair-share mean is `totalClusterGPUs / numActiveModels` — it's based on model count and saturation need, not quota size. Quotas are applied as hard ceilings after the mean is computed.

**Worked example** (3 models, 3 namespaces, cluster quota 8 GPUs):
- M1 (NS1): wants 3, namespace quota 2
- M2 (NS2): wants 4, namespace quota 4
- M3 (NS3): wants 4, namespace quota 4

Round 1 mean = 8/3 ≈ 2.67. M2 and M3 are not quota-constrained (quota 4 > mean) and each get ~2.67. M1 is capped by its quota at 2 (below the mean), leaving ~0.67 in the cluster pool. Round 2: mean = 0.67/2 ≈ 0.33, split between M2 and M3. Final: M1=2, M2≈3, M3≈3.

The outcome is correct. Two things worth documenting: (1) a quota-constrained model's unused fair-share slot is redistributed in the next round, not the current one; (2) fairness is per-model, not per-namespace — a namespace running 3 models occupies 3 fair-share slots regardless of its quota size.

---

## Confirmed correct

- `QuotaInventory` mutex, per-cycle allocator snapshot — correct
- `GetNamespaceResourcePools` closed-allowlist contract — consistent with V1 `tryAllocateNamespace`, documented and tested
- `effectiveAvailable` enforces closed allowlist correctly (absent type = deny, not zero)
- Reconcile loop in `allocateForModel` — decrements cluster budget only for types cluster caps, namespace budget only for finite caps
- `computeCurrentGPUUsageByNamespace` materializes every request's namespace including zero-replica
- `gpuConstraintProviders` → `NoOpLimiter` → nil → falls back to cost-aware (unlimited) optimizer correctly
- Validation accumulates all errors via `errors.Join`
- All `NewEngine` callers updated with `NewNoOpLimiter`
- `math.MaxInt` in `effectiveAvailable` is dead code in practice (path only reachable when cluster has no cap, so fair-share loop doesn't allocate that type anyway)

---

## PR Comment Draft

> **For Dean's approval before posting. Do not post without confirmation.**

---

Solid implementation and good test coverage. Notes below are documentation gaps and future-enhancement suggestions only.

Missing user guide coverage: the feature is documented in `docs/developer-guide/quota-limiter.md` but `docs/user-guide/` and `docs/developer-guide/configuration.md` (where new flags belong) aren't updated. At minimum `configuration.md` and the user guide should reference the new doc.

---

### Implementation

Everything I checked looks good: `QuotaInventory` thread safety and per-cycle allocator snapshot, V1/V2 parity via `GetNamespaceResourcePools` + `effectiveAvailable`, closed-allowlist enforcement in `allocateForModel`, `mergeNamespaceConstraints` / `tighterBudget` / `nsPoolBudget` for the unlimited sentinel, and the `shouldCollectClusterInventory` gate.

One thing worth confirming: with `--limiter-type=quota` and no cluster-level cap for a GPU type, `effectiveAvailable` sets the budget to `math.MaxInt` for an unlimited namespace entry. The developer guide notes this path doesn't scale under GreedyByScore (fair-share loop stops when cluster aggregate is zero), so in practice it's dead code — but it's not tested end-to-end through the optimizer. Low priority, just flagging it.

---

### Docs / usability

**1. Quota reload lifecycle**

The developer guide doesn't mention that quota configuration is loaded once at startup and requires a controller restart to change. `Refresh()` being a no-op is correct by design, but it's worth a note given that Kubernetes silently hot-updates ConfigMap-mounted files — an operator who edits the quota ConfigMap and sees no effect may spend time debugging. Something like: *"Quota configuration is read once at startup. Restart the controller to apply changes."* in the Configuration section would help.

**2. `--limiter-type` is a global flag; per-entry `type:` field**

The `type: "quota"` field on each YAML entry is a discriminator for future limiter types (e.g., `reservation`, `priority`) and must currently always be `"quota"` — other values fail validation. Meanwhile, the choice between physical-inventory and quota enforcement is made globally via `--limiter-type`, not per entry. It would help to say this explicitly in the developer guide so operators don't wonder whether `type: inventory` is valid inside the YAML.

**3. Fair-share interaction with namespace quotas**

The guide covers what namespace quotas enforce but doesn't describe how they interact with the fair-share loop. A short note would be useful: the fair-share mean is `cluster GPUs / number of active models`, not quota-weighted. Quotas are hard ceilings applied after the mean is set, so a quota-constrained model that takes less than its fair-share slot leaves the remainder for subsequent rounds rather than for other models in the same round. Fairness is also per-model, not per-namespace — a namespace with more models gets proportionally more fair-share slots.

A worked example makes this concrete:
- 3 models across 3 namespaces, cluster 8 GPUs; M1 wants 3/quota 2, M2 wants 4/quota 4, M3 wants 4/quota 4
- Round 1 mean ≈ 2.67: M2 and M3 each get ≈ 2.67 (not quota-constrained), M1 is capped at 2
- Round 2: remaining ≈ 0.67 split between M2/M3 → final M1=2, M2≈3, M3≈3

The outcome is correct; knowing the path helps operators reason about convergence and per-namespace behavior.

---

### Nits

- `composite_limiter.go` `Limit()` comment: "the decisions slice is the source of usage truth (see `calculateUsedGPUs`), so each constituent sees the already-capped `TargetReplicas`." `calculateUsedGPUs` uses `CurrentReplicas`, not `TargetReplicas`. The most-restrictive-wins property actually comes from `TryAllocate` receiving the already-mutated `TargetReplicas`. Behavior is fine, comment is just misleading.

- `composite_limiter.go` struct comment: "partial commits do not leak" — this is true for per-allocator usage state, but `TargetReplicas` mutations from earlier constituents do persist on error. Errors abort the cycle so it's not an issue; the comment could be more precise.

- `quota_inventory.go` `quotaAllocator.Remaining()` (namespace scope): iterates `NamespaceQuotas` keys only, so namespaces consuming via the `"default"` fallback aren't counted, and `Remaining()` can over-report. Reporting-only, not allocation correctness — worth a comment on the method.

- `config.go` `LimiterType` godoc and `quota-limiter.md` startup wiring table both say "mutually exclusive in PR-1." PR references in code and shipped docs don't age well; "mutually exclusive in the initial implementation (composing with physical inventory is sub-issue #1003)" reads more clearly after the PR closes.
