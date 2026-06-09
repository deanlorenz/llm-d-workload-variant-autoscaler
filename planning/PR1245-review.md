# PR #1245 — ScalingPolicy CRD (minimal core) — Review

Status: DRAFT
PR: https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1245
Author: ev-shindin · Base: main · One new file: `docs/proposals/design-scalingpolicy-crd.md` (+144)
Companion: #1194 (full analysis, kept open) · VA-deprecation tracker: #1130 · quota: #1162/#1002

---

## Corrected design model (from discussion with author + Dean, 2026-06-09)

The proposal text reads narrower than the intended design. Confirmed intent:

- **One CRD, attached at multiple tree-A levels, with inheritance.** A node with no CR
  inherits its parent's **resolved** policy (not just "merge when multiple CRs exist").
- **Root CR is mandatory and definitional.** One per WVA controller. Two modes:
  cluster-scoped (one cluster CR) or namespace-scoped (one CR per namespace, RBAC-enforced).
  The root CR's `analyzers[]` = enabled set + default thresholds/scores ≈ registration trigger;
  lower tiers' `analyzers[]` = overrides.
- **SOT-level facts (cost, min/max, modelID) are NOT this CRD's job.** They stay on the
  HPA/KEDA CR (VA today; annotations post-VA). Virtual-VA completeness = ScalingPolicy +
  HPA-CR facts *together*. (This dissolves the first-pass "min/max/cost gaps" findings.)
- **P/D: one role per pool, one model per pool (current + converging EPP).** Role overrides
  live *inside* the pool CR; `priority` is per-pool and singular → no cross-pool coordination
  needed today. Reopens only if EPP later splits a model across role-pools.
- **Limiters/quota:** external quota (#1162) and physical limits are not WVA-owned.
  Dean's position: don't carry external limiters/quota in the WVA CRD; prefer a **unified
  WVA-native cap** that inherits like any other policy, validated at each level to stay
  ≤ quota and ≤ physical limits, reflected in `effectivePolicy`. (Existing WVA limiter
  config may already be a quota-style admin cap on max GPU/cluster.) Naming ("caps") not
  worth arguing with author.

## Findings (all clarity-level except #4)

1. **Inheritance described as merge only (§4).** Silent on the no-CR case (the common one).
2. **Root CR dual-purpose (§3).** `analyzers[]` definitional at root, override below.
3. **Controller modes (§4).** Text assumes cluster-scoped; namespace-scoped mode unstated.
4. **`limiters`/`quota` (§3 L77–90, §4 L100).** External quota embedded as a WVA field while
   also stated not-WVA-owned; "excluded from merge" contradicts "lower tiers inherit resolved
   policy." Only finding that may touch the schema.
5. **Priority across role-pools (§3).** Unambiguous today (1 model/pool); state the assumption
   + bounded deferral.
6. **Schema vs current engine (§3).** Per-pool analyzer disable/thresholds are schema-supported,
   not in the engine today.

Out of scope by the corrected model (not raised on PR): cost / min-max / virtual-VA — live on
HPA/KEDA CR (#1130 track), not this PR.

---

## Comment to post (global, single comment) — NOT YET POSTED

Agree with the scope and the §2/§3 answers. A few clarity items, mostly on §3–§5 where the text describes a model narrower than the design seems to intend.

**1. Inheritance is described as merge only (§4).** The text covers what happens when multiple CRs exist (merge, higher tier wins) but not what happens when a node has *no* CR — the common case. Suggest stating it: *a pool/namespace with no `ScalingPolicy` inherits its parent's resolved policy.* WVA could also generate an empty per-pool CR so the effective policy is visible through its status — which directly answers §5's open question (default-only pools): the question becomes "where is inherited policy surfaced," not "is there policy."

**2. Root CR is dual-purpose (§3).** `analyzers[]` has two meanings by tier: at the root tier it is **definitional** (the enabled-analyzer set + default thresholds/scores — effectively the registration list); at lower tiers it is an **override**. The text treats it uniformly. One line distinguishing the two would prevent reading the root list as just another override.

**3. Controller modes (§4).** §4 assumes a cluster-scoped controller with namespace tenants. WVA can also run namespace-scoped (root CR = the namespace CR, no cluster tier) — the "cluster-default + namespace" framing and the RBAC argument change shape in that mode. Worth one sentence stating which modes are in scope.

**4. `limiters`/`quota` ownership (§3 lines 77–90; §4 line 100).** As written, external quota (#1162) sits *inside* `ScalingPolicy` as a limiter, while §3 also says it isn't WVA-owned. "Excluded from the merge / cluster-default-only" is correct for an external constraint, but conflicts with the inheritance model for anything WVA *does* own. Suggest treating any WVA-owned cap as ordinary inheritable policy — validated at each level so the effective cap stays ≤ quota and ≤ physical limits, reflected in `effectivePolicy`. That removes the apparent contradiction between "limiters excluded from merge" and "lower tiers inherit resolved policy."

**5. Priority across role-pools (§3).** With one model per pool today, a single per-pool `priority` is unambiguous — no coordination needed. Recommend stating that explicitly, plus that if a future EPP splits one model into separate role-pools, cross-pool priority precedence is decided then. Converts a silent assumption into a bounded deferral.

**6. Schema vs. current engine (§3).** The schema permits per-pool analyzer enable/disable and per-pool thresholds; the engine applies a single global threshold set today. Suggest noting these as schema-supported / engine-future so the schema isn't read as current behavior.

(2) and (5) are one-line clarifications; (1), (3), (6) are short additions; (4) is the only one that may touch the schema.
