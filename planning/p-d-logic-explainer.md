# P/D Scaling Logic — One-Pager

**What this doc is.** A simple summary of how the optimizer scales models with
prefill (P) and decode (D) roles. Compares PR #1237 to our optimizer-branch
design and lists the failure modes the analysis covered.

## What P/D means

A disaggregated model splits work across role-tagged variants:

- **P (prefill)** — input token processing.
- **D (decode)** — output token generation.

Each user request consumes both. Lose all P → nothing starts. Lose all D →
started requests can't produce output. Roles are complementary, not
substitutes.

## Per-role state

Each (model, role) carries its own:

- **Demand** — workload need in role-specific units (e.g. kv-tokens/s).
- **Capacity** — replicas × PRC (per-replica capacity).
- **RC** — engine-written: more capacity needed.
- **SC** — engine-written: headroom available to shed.

Stored on `RoleCapacities[role]` (per-analyzer) on the analyzer result.

## Scaling operations

**Scale-up: joint, atomic.** When at least one role has `RC > 0`, the
optimizer adds replicas. Roles couple at user-request level — a request
requires both — so the served fraction is bounded by the bottleneck:

    util(model) = min(util_P, util_D)

Picker sizes each role independently from its own RC, then trims the
over-allocated role at commit time so both advance by the same util delta.
Atomic: commit only the matched portion; release excess to the next
iteration.

**Scale-down: independent.** Each role sheds against its own SC; roles do
not couple. Removing a prefill replica only affects P-supply. Per-role
cheapest-variant protection prevents zeroing a role.

## Examples (PRC_P = PRC_D = 100, scaleDown threshold = 0.8 → SC = TS − 1.25·TD)

**Ex. 1 — symmetric scale-up (cold start).** Demand_P=100, Cap_P=0;
Demand_D=50, Cap_D=0. n_P=2, n_D=1. Commit (2, 1). util_P=util_D=1.

**Ex. 2 — asymmetric scale-up (D grew, P steady).** Demand_P=100,
Cap_P=100; Demand_D=80, Cap_D=50. P needs 0 replicas (already at util=1),
D needs 1. Commit (0, 1). util_P stays 1; util_D goes from 0.625 → 1.

**Ex. 3 — asymmetric scale-down (P spare, D saturated).** Cap_P=200,
Demand_P=80 → SC_P = 100; Cap_D=100, Demand_D=100 → SC_D = 0. P sheds 1
(floor(100/100)=1). D unchanged. Post-state (1, 1) fully served.

**Ex. 4 — sub-replica spare, no-op.** Cap_P=200, Demand_P=150 → SC_P = 12.5;
Cap_D=100, Demand_D=90 → SC_D = -12.5 (clamped to 0). Both `floor(SC/PRC)=0`.
No shed. Both roles stay over-supplied; next cycle revisits.

## #1237 vs our design

| Aspect | PR #1237 (on `main`) | Our optimizer branch |
|---|---|---|
| Scope | Single-analyzer scale-down only | Multi-analyzer scale-up + scale-down |
| Scale-down | Role-iterated, per-role spare from `RoleCapacities[role].SC` | Role-iterated, per-role spare from `RoleSpare[role]` aggregated across analyzers (`min_i floor`) |
| Scale-up | Unchanged legacy path | Joint min-util commit (Phase 2 B2) |
| Atomic scale-up | N/A | Yes — over-allocated role trimmed |
| Generalizes to >2 roles | No (P/D coded via map iteration) | Yes (min over any role tuple) |

Both correctly fix the asymmetric scale-down bug (model-level aggregate
spare driving removal of a saturated role). Our branch additionally fixes
asymmetric scale-up.

## Failure modes checked

| Case | Pre-phase-2 (current optimizer tip) | Phase-2 (in flight) | PR #1237 |
|---|---|---|---|
| Symmetric scale-up | Correct | Correct | N/A |
| Asymmetric scale-up: P-only demand | Correct (via α=0 edge case) | Correct | N/A |
| Asymmetric scale-up: D-only demand | **BUG — routes to scale-down** | Correct | N/A |
| Symmetric scale-down | Correct | Correct | Correct |
| Asymmetric scale-down: P-spare, D-saturated | Correct (role-iterated) | Correct | Correct |
| Asymmetric scale-down: D-spare, P-saturated | Correct | Correct | Correct |
| Cold start (both roles 0) | Correct | Correct | N/A |
| Cold start (D-only) | **BUG — same as D-only demand** | Correct | N/A |
| Cold start (P-only) | Correct | Correct | N/A |

The scale-up D-only-demand bug surfaces when workload α shifts so D-demand
grows while P stays fully provisioned (e.g., decode-heavy traffic burst).
`initDisaggregatedRemaining` sets model-level `Remaining = RC_P = 0` →
`needsScaleUp(s)` returns false → optimizer routes to scale-down → D
under-provisioning persists silently. PR #1237 doesn't address this
(scale-down only). Phase 2's `RolePairedState` + `needsScaleUpPaired` fixes it.

## On the "single P replica too much for D" framing

I could not construct a case where shedding one P replica forces D to
need more replicas than D currently has. Removing P-replicas reduces
P-capacity; it does not change D-demand or D-capacity. Per-role
`SafeRemovalReplicas = floor(SC/PRC)` correctly bounds shed by
each role's own headroom — never below that role's demand.

The closest mode found is the **scale-up** asymmetric-demand bug above.
If a specific scale-down scenario was in mind that this analysis hasn't
captured (e.g., a particular interaction with PRC granularity, threshold,
or minReplicas), flag it for re-analysis.

## References

- [`multi-analyzer-design.md`](multi-analyzer-design.md) § Architecture/D —
  full design rationale (cross-analyzer/cross-role calculus, joint-min
  coupling, generalization beyond P/D).
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md)
  § Phase 2 — implementation guide for the scale-up fix and the post-#1237
  rebase plan.
- [`multi-analyzer-optimizer-review.md`](archive/multi-analyzer-optimizer-review.md)
  — the review that surfaced B1, B2, T1, N2, N3 (FINAL).
- PR [#1237](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1237)
  — single-analyzer scale-down fix on `main`.
