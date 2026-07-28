---
type: review
pr: 1452
title: "feat(rescale): priority-weighted GPU rescale under contention (Alpha)"
author: ev-shindin
status: FINAL — APPROVED 2026-07-28 (author responded, RC-2/RC-4 held for direct follow-up)
date: 2026-07-26
---

# PR #1452 Review — priority-weighted GPU rescale under contention (Alpha)

**PR:** [#1452](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452)
**Author:** ev-shindin
**Base:** main | **Head:** `feat/rescale-alpha` (ev-shindin fork) | **State:** open
**Scale:** 15 files, +1866/−14
**CI:** all green (lint-and-test 3m30s, e2e-tests-full 14m12s, e2e-tests-smoke 10m41s, DCO, signed-commits, kustomize-build)
**Reviewed:** 2026-07-26 (no prior reviews/comments on the PR)
**Base sha:** merge-base `d6d39be`; local Main at `f5b7577c` (branch not rebased onto current main — see TODO-2)

---

## What it does

Adds an **opt-in, off-by-default** redistributive pass (`enableRescale`) to the V2 GPU-limited
(`GreedyByScoreOptimizer`) path. Under contention it redistributes a competition group's **whole
budget** by `priority × demand`, reclaiming GPUs from over-share / lower-priority models so
starved higher-priority ones can grow — instead of today's additive fair-share that only hands out
*free* GPUs.

Mechanics:
- Competition group = `(accelerator type, budget scope)`; scope is `cluster` or `namespace-N`.
- **Scope-coupled enablement:** rescale runs at a scope iff a budget exists there **and** the flag
  is set at that same scope. Cluster flag = global saturation `default`.`enableRescale`; namespace
  flag = that namespace's **own** `default` (never the global fallback).
- **Water-filling** (`computeRescaleTargets`, pure): floors reserved first, `share = floor +
  (budget − Σfloor)·weight/Σweight`, iteratively capped at `min(demand, maxReplicas)` with freed
  excess re-split, largest-remainder integer rounding, whole-replica quantization at each variant's
  `gpusPerReplica`.
- **Paced, never-over-budget:** reclaims free nothing the same cycle (usage is `CurrentReplicas`-
  based); fills gated by physically-free GPUs. A namespace fill is bounded by `min(quota free,
  cluster physical free)` and debits **both** budgets.
- **P/D:** model GPU target split across roles by role demand, each role's floor reserved first;
  reclaim/fill run per role over one shared free-this-cycle counter.
- Reclaim scale-downs tagged `DecisionReasonRescale`.

Design doc shipped in the PR: `docs/plans/engine/rescale-alpha.md` (proposal `docs/proposals/design-rescale.md`, PR #1238).

---

## Verdict

**Solid Alpha. No correctness bugs found; the core algorithm matches the design and is unusually
well-tested.** Three substantive discussion points, all traced to the same root cause (see § Design
framing): rescale reimplements fairness+ordering as a bespoke, isolated pass rather than extending
the existing negotiation, so it doesn't inherit three properties the existing path has —
(1) the multi-analyzer scale-down safety gate (confirmed with a worked numeric trace), (2)
scope-neutral priority ordering, (3) joint cross-role synchronization for P/D fills (confirmed with a
worked numeric counter-example). All non-blocking for an off-by-default Alpha, but worth explicit
author confirmation before it graduates.

---

## Confirmed correct (traced against design + tests)

- **Water-fill** reproduces both worked examples (A2/B6; cap+re-split → A4/B4); floors reserved
  first; `Σfloor > budget` → Conflict clamp to floors (`overBudget=true`).
- **Rounding** (`roundExtras` / `apportionLeftover`): largest-remainder with cap-skip and
  deterministic key tie-break; preserves `Σtargets ≤ budget`.
- **Fill pacing:** `freeThisCycle` gates fills to physically-free GPUs; reclaims add nothing this
  cycle → group never over physical/quota budget. Namespace fill debits both maps, bounded by
  `min(quota, cluster)` → cannot over-subscribe or drive either budget negative.
- **P/D role split** (`distributeGPUsByWeight`) reserves per-role floors then splits by role demand;
  cold-start (zero demand/current, nonzero floors) keeps each role's floor.
- **`(namespace, ModelID)` keying** everywhere (bookkeeping + fill tie-break); deterministic group
  and intra-group ordering.
- **Reason survives enforcement:** `updateDecisionAction` preserves `ReasonCategory()`, only
  defaulting to V2 when empty — so `DecisionReasonRescale` is not overwritten.
- **Inert without the limiter:** `selectV2Optimizer` returns `GreedyByScoreOptimizer` only when
  constraint-backed providers exist; otherwise `CostAwareOptimizer`, on which the engine's
  type-assert fails and `.Rescale` is never set. Combined with the `Rescale.any()` short-circuit,
  both "flag off" and "no limiter" paths are structurally unchanged.
- **Config plumbing:** `EnableRescale` read only from `default` entries; `RescaleEnabledForNamespaceLocal`
  is namespace-local (no global fallback); `default` entries are stored raw (not via `Merge`), so
  `Merge` omitting `EnableRescale` does not drop the flag on the read path. Per-model override cannot
  set it (test covers this).
- **Test coverage** is genuinely thorough: 26 optimize-level scenarios (pacing, scope-coupling,
  cluster-vs-namespace bounding + double-debit, P/D splits, MaxReplicas cap + budget return,
  `gpusPerReplica>1` quantization, deterministic ordering across a shared pool, multi-accel skip,
  same-ModelID-different-ns independence, unlimited/over-subscribed skip, Conflict path) + water-fill
  units + config-accessor tests.

---

## Findings

### RC-1 (question to author) — `DecisionReasonRescale` has no in-tree stabilization consumer

The interface constant comment says the tag exists so "downstream stabilization must not damp [the
reclaim] as if it were noise." No code in-tree consumes `DecisionReasonRescale` for that purpose:
the only "damping" is an **unimplemented TODO** in the separate `gpurebalance` plugin (an HPA
max-replica-ceiling mechanism driven by queue depth), which never reads `DecisionReason`. Today the
tag flows only to the Prometheus reason label (`EmitReplicaScalingMetrics`) — a real but
observability-only benefit.

Not a bug (forward-looking + useful in metrics). Disposition: **phrase as a question to the author;
no GH comment for now.**

> Draft question: "`DecisionReasonRescale` — I don't see an in-tree consumer that treats it
> specially for stabilization/damping yet (the gpurebalance damping is a TODO on a separate
> HPA-ceiling path and doesn't read `DecisionReason`). Today it flows only to the reason metric
> label. Is the 'downstream stabilization must not damp' comment describing intended future
> behavior? If so, could we word it as 'reserved for future stabilization; currently surfaced as a
> distinct metric reason' so it doesn't read as an existing guarantee?"

### RC-2 (question to author + our TODO) — reclaim bypasses the existing multi-analyzer scale-down safety gate

**What the "combined analyzer signal" is, precisely** (traced through `analyzer_helpers.go` /
`cost_aware_optimizer.go`, used by the *regular* `scaleDownRoleIterated` path):
- Scale-up sizing (`roleBottleneckReplicas`): `max` across analyzers of `ceil(unmet demand / PRC)`
  — size to the hungriest analyzer.
- Scale-down gating (`needsScaleDownForRole`): **unanimity** — a role is scale-down-eligible only if
  *every* analyzer's `RoleSpare[role] > 0`. One skeptical analyzer vetoes scale-down for that role.
- Scale-down sizing (`safeRemovalReplicasForRole`): `min` across analyzers of `floor(spare/PRC)` —
  bounded by the *most conservative* analyzer.
- Ordering (`fairShareValue`): `priority × Σ(Score-weighted per-role remaining)` across analyzers.

**What rescale's reclaim does instead:** `reclaimRole` (rescale.go) calls `scaleDownVariantSet`
directly with a custom `maxRemovable`/`onRemove` pair derived purely from the saturation water-fill
delta (`deltaGPUs`). It **never calls `needsScaleDownForRole` or `safeRemovalReplicasForRole`** —
confirmed by reading both call sites; `scaleDownRoleIterated` gates every role with the former and
bounds every removal with the latter, `reclaimRole` does neither. It only inherits
`scaleDownVariantSet`'s own floor protections (`minReplicas`, cheapest-at-1), not the multi-analyzer
spare gate above it.

**Concrete risk:** if saturation (KV-cache/queue) sees spare on a role while a co-enabled TA
(queueing-model token demand) has `RoleSpare[role] ≤ 0` (fully loaded), the regular path refuses to
touch that role (`needsScaleDownForRole` vetoes it) — rescale's reclaim does not consult TA at all
and can shed replicas from that same role down to the saturation-only water-fill target. This is a
strictly weaker safety property than every other scale-down path in the codebase, in a config the
engine already supports (saturation + TA together).

**TA-only baseline (saturation off) — confirmed safe.** `applyRescale`'s per-request loop skips any
request with `saturationEntry(...) == nil` before grouping; with saturation off, `groups` stays
empty and neither `available` map is ever touched. Rescale is a complete no-op when TA is on and
saturation is off. The risk is specifically **saturation + TA both enabled**, not TA-only.

- Minor related inconsistency: scale-*down ordering* (`sortVariantsForScaleDown`) IS multi-analyzer
  Score-weighted, but the *target* (how many GPUs to reclaim) is saturation-only — so *which*
  replicas get shed is analyzer-aware while *how many* is not.
- Same root as `roleDemandGPUs`: demand-in-GPUs is estimated from only the single most-cost-efficient
  variant's per-replica capacity — fine for homogeneous roles, an approximation otherwise.
- No documented rationale found: the design doc's algorithm section sources `demandGPUs_i` from
  `satEntry.TotalDemand`/`RoleCapacities` exclusively; multi-analyzer combination isn't discussed.
  Reads as an Alpha scope-simplification, not a stated tradeoff.

**Verified with a concrete trace (TODO-1, resolved — not just plausible, confirmed):** single-role
model M, 1 variant (`PerReplicaCapacity=1000`), current=6 GPUs. Saturation reports `TotalDemand=4000`
(plenty of spare). A co-enabled TA independently reports `RoleSpare["both"] ≤ 0` (queue-model says
fully loaded). Peer B in the group: `Priority=3, Demand=6000`, current=0; group budget=8
(`free=2 + currentUsage 6+0`). Hand-running `computeRescaleTargets`: `weight_M=1×4000=4000`,
`weight_B=3×6000=18000`. Round 1: `share_B = 8·18000/22000 ≈ 6.55 ≥ headroom(6)` → B caps at 6,
`remaining=2`. Round 2: only M active, `share = 2·4000/4000 = 2` → `extra[M]=2`. **Target: M=2, B=6.**
M's current (6) exceeds its target (2) → `reclaimRole` sheds **4 GPUs from M unconditionally**.

Meanwhile under the regular path, `needsScaleDownForRole(s, "both")` loops every analyzer in `s`;
TA's `RoleSpare["both"] ≤ 0` makes it return `false` on the very first check —
`scaleDownRoleIterated` would **never touch M at all**. Confirmed: under saturation+TA both enabled,
rescale reclaims GPUs from a role the existing scale-down gate would categorically refuse to shed
from.

Disposition: **question to author** (is bypassing the multi-analyzer gate intentional for Alpha?).
TODO-1 closed — no further verification needed before raising the question.

> Draft question: "`reclaimRole` sheds replicas via a custom bound purely from the saturation
> water-fill delta — it doesn't call `needsScaleDownForRole`/`safeRemovalReplicasForRole`, so it can
> remove replicas from a role a co-enabled analyzer (e.g. TA) still considers fully loaded
> (`RoleSpare ≤ 0`), which `scaleDownRoleIterated` would refuse to do. Worked example: [saturation
> demand 4000/1000 PRC with 6 current GPUs, TA RoleSpare≤0, group budget forces target=2] — rescale
> reclaims 4 GPUs from a role TA considers fully loaded, which `scaleDownRoleIterated` would refuse
> to touch. Is saturation-only demand/reclaim intentional for Alpha, or should reclaim reuse the
> existing multi-analyzer gate/bound?"

### RC-3 (question to author) — cross-scope fill order doesn't match the regular allocation path's priority ordering

Checked directly against `fairShareScaleUp`/`Optimize`: the regular additive path does **not** group
by scope at all. It runs one iterative mean-based loop over the full union of scale-up work (cluster-
and namespace-scoped models together); each iteration serves the model with the highest `remaining`
(`priority × weighted demand`) regardless of which scope's budget it draws from. Per-model *budget*
differs by namespace (`effectiveAvailable`), but *who is served first* is governed by priority×demand
across the whole set, not by scope.

Rescale's group ordering (`slices.SortFunc(keys, ... accType, scope)`) sorts cluster (`scope=""`)
before every namespace scope, then sorts by priority **only within each group**. So — per the "if
it doesn't match current logic, it should" principle — this is a real deviation, not a benign doc
note: a low-priority cluster-scope model can claim scarce shared physical GPUs ahead of a
high-priority namespace-scope model on the same accelerator type, the inverse of what
"priority-weighted" promises.

**Caveat:** this only bites when the shared physical pool is oversubscribed across a cluster group
and a namespace group in the same cycle — exactly the physical∧quota partition the design already
**defers to #1003**. It does not change any *limit* (budgets are fixed before ordering: `free +
currentUsage`, order-independent); it's a same-cycle fill-pacing tie-break. So this may be a known,
accepted Alpha limitation rather than an oversight — worth asking rather than asserting.

Disposition: **question to author**, not just a doc note.

> Draft question: "Cross-scope fill order (cluster before namespace, sorted by `accType, scope`)
> doesn't match the regular additive path, which interleaves by priority across scope boundaries via
> a single mean-based loop. Under a same-type physical-pool oversubscription across a cluster group
> and a namespace group, this lets a lower-priority cluster model win scarce GPUs ahead of a
> higher-priority namespace model — the inverse of the priority ordering the PR promises. Is this
> accepted as part of the #1003-deferred physical∧quota gap, or should cross-scope fill also
> interleave by priority?"

### RC-4 (question to author) — P/D fill has no joint cross-role synchronization; can transiently invert the prefill:decode ratio

Checked precisely what the regular path's P/D "coupling constraint" is: not "max utilization" but a
**joint min-utilization throttle**. Each iteration of `allocateForModelPaired` picks a *candidate*
for every role from a budget snapshot taken before any role commits, computes
`deltaUtil = min` utilization achieved across roles, and applies that **same** `deltaUtil` to size
every role's commit. If any role can't pick at all, the **whole iteration aborts — no role ever
commits alone.** This structurally prevents one role racing ahead of its pair while the other
starves under scarce budget.

Rescale's P/D fill has no such synchronization. `rescaleModelDecisions` processes roles
**sequentially** (alphabetically — `decode` before `prefill`) against **one shared `freeThisCycle`
counter**, each role's `fillRole` call fully executing (and depleting the counter) before the next
role runs at all:

```go
for _, role := range roles {          // "decode", then "prefill"
    want := rt - rc
    if want > *freeThisCycle { want = *freeThisCycle }
    *freeThisCycle -= fillRole(..., want)
}
```

**Concrete counter-example:** model B, prefill demand 6000 / decode demand 2000 (true ratio 3:1
prefill-heavy — matches the PR's own "splits a P/D fill proportionally to role demand" test, which
targets prefill=6/decode=2), both roles at 0. That test only exercises `freeThisCycle=8` (exactly
enough for both). With a scarcer `freeThisCycle=3` — ordinary under contention, since it's the
*whole group's* shared physical pool, not per-model — decode runs first: `want=2 ≤ 3` → fills fully
to **2**, `freeThisCycle → 1`. Prefill runs next: `want=6` capped to `min(6,1)=1` → fills to only
**1**. End of cycle: decode=2 (100% of its target), prefill=1 (17% of its target) — the achieved
ratio (2:1 decode-heavy) is **inverted** relative to the true demand ratio (3:1 prefill-heavy). The
regular `allocateForModelPaired` cannot produce this: its per-iteration joint pick advances both
roles together, and if the shared budget can't serve both, the whole iteration — and thus the
model's whole turn — stops for both simultaneously.

This self-corrects over subsequent cycles (targets are recomputed from demand each cycle, not from
the shortfall, so decode stops growing once at target and later free capacity flows to prefill), but
during the transient a live P/D deployment runs with a materially wrong prefill:decode ratio — a real
serving-capacity issue, not just a bookkeeping curiosity. And because scarcity is the exact condition
rescale exists for, this is likely to occur in normal operation, not a rare edge case. No existing
test exercises a scarce same-cycle P/D fill (checked — the only P/D fill test uses exactly-sufficient
budget).

Third instance of the same root-cause pattern as RC-2/RC-3 (see § Design framing): bespoke sequential
application that doesn't inherit the existing algorithm's synchronization.

Disposition: **question to author.**

> Draft question: "Rescale's P/D fill processes roles sequentially against one shared
> `freeThisCycle` counter (no joint min-utilization throttle like `allocateForModelPaired`'s
> per-iteration `deltaUtil`). Worked example: prefill:decode demand 6000:2000 (true ratio 3:1),
> `freeThisCycle=3` → decode fills fully (2/2) before prefill gets anything, landing at
> prefill:decode = 1:2 — an inverted ratio for at least one cycle. Is this an accepted Alpha-scope
> transient (self-corrects over subsequent cycles), or should P/D fill also jointly throttle by role
> utilization the way the regular path does?"

### NTH-1 (accepted, no action) — variant reallocation across models is out of scope, unchanged from today

Dean's observation, verified: "variant" is always model-scoped (`VariantCapacities`/`VariantStates`
are per-model) — two competing models never share a variant to swap between. Both the regular
optimizer and rescale operate purely on **per-accelerator-type replica-count budgets**; each model
picks among its *own* variants independently by its own greedy heuristic (cost-efficiency ascending
for fill, cost-descending for reclaim), with zero awareness of what a competing model would prefer.
"Move A off variant V1 so B can use V1" isn't something either path does or has ever done —
allocation is GPU-count fair-share at the type level, not variant-assignment coordination. Confirmed
accurate, unchanged from existing behavior. No action; worth a doc note only.

### NTH-2 (accepted, no action; verified logically — worth saying so if this becomes a GH comment) — "byte-identical when off" asserted behaviorally, not as a golden diff

`o.Rescale.any()` short-circuits `applyRescale` entirely; the only added off-path code is a
`handled[...]` check against an empty map (always false) and an append of a nil slice. The off-path
is provably identical by inspection, so the behavioral spot-check (no rescale reason, A un-reclaimed)
is sufficient — a golden side-by-side test would add nothing. No action.

---

## Design framing — "set limits then converge" vs. "simulate-free-and-reallocate"

Dean's question: is the PR's approach "set logical fairness limits, then trigger normal allocation
under those limits" rather than "simulate freeing everything and rerun the existing fair-share
reallocation"? **Confirmed: yes, the former.**

`computeRescaleTargets` is a standalone, PR-authored proportional water-fill formula
(`floor + remainder·priority×demand/Σweight`, iteratively capped, largest-remainder rounding) — a
*different fairness rule* from the existing `fairShareScaleUp` (an iterative mean-based negotiation:
repeatedly give to whoever's most-below-mean). Given targets, rescale applies them directly via
`scaleDownVariantSet`/`fillRole` — it never calls back into
`allocateForModelPaired`/`fairShareRolePick`/`fairShareScaleUp`.

**Why "simulate-free-and-reallocate via the existing algorithm" isn't actually available as a
lower-risk alternative:** the existing algorithm has **no reclaim primitive at all** —
`allocateForModelPaired` only ever adds (no negative branch), and within one cycle, scale-up and
scale-down are two passes that don't feed each other (a model's own scale-down doesn't get
redistributed to another model until the *next* cycle). That's the literal problem statement in the
PR description. So "just rerun current allocation" can't solve this by itself — it would require
inventing a new *reset-then-renegotiate* variant of the existing algorithm (fabricate a hypothetical
"all models at floor" state, then run the mean-based loop over it), which is new machinery of
comparable size to what the PR already wrote, not a smaller reuse of what exists.

**So the PR's real disadvantage isn't "it's not simulate-and-reuse" — it's that its bespoke
formula+applier doesn't inherit three properties the existing negotiation has for free, and
RC-2/RC-3/RC-4 are all symptoms of that one root cause:**
- RC-2: bespoke reclaim ⇒ doesn't inherit the multi-analyzer safety gate
  (`needsScaleDownForRole`/`safeRemovalReplicasForRole`).
- RC-3: bespoke group ordering ⇒ doesn't inherit the existing loop's scope-neutral priority ordering.
- RC-4: bespoke sequential per-role fill ⇒ doesn't inherit the existing joint min-utilization
  throttle (`deltaUtil`) that keeps P/D roles synchronized under scarce budget.

A third option worth naming for our own framing (not proposing to the author): extend the existing
mean-based negotiation itself to support reclaim, which would inherit both properties automatically
but is a much larger, riskier change to the core allocator than an isolated, opt-in Alpha module.
Given the feature is off-by-default and Alpha, the PR's scope tradeoff is defensible — but it should
be an *explicit* tradeoff the author confirms, which is what RC-2/RC-3 are asking.

---

## Our TODOs (internal — not GitHub)

- ~~**TODO-1 (verify):** exercise `enableRescale` under a saturation + Throughput Analyzer
  multi-analyzer config.~~ **RESOLVED** — closed with a worked numeric trace under RC-2 above:
  confirmed rescale reclaims 4 GPUs from a role a co-enabled TA reports as fully loaded
  (`RoleSpare ≤ 0`), which the regular `scaleDownRoleIterated` path would refuse to touch at all.
  Open decision (now folded into the RC-2 author question): gate rescale to saturation-only configs,
  reuse the existing multi-analyzer gate/bound, or fold the combined signal into the water-fill
  weight.
- **TODO-2 (note to author):** ask ev-shindin to rebase onto current `main` (base `d6d39be` → Main
  `f5b7577c`) before merge. CI green, no conflict — just keeping the branch current. No GH comment
  for now.

## Questions for the author (hold — no GH post yet)

1. RC-1 wording of the `DecisionReasonRescale` comment (reserved-for-future vs existing guarantee).
2. RC-2 — reclaim bypasses `needsScaleDownForRole`/`safeRemovalReplicasForRole` (confirmed with a
   worked trace: reclaims from a role TA reports fully loaded); intentional for Alpha, or should
   reclaim reuse the existing multi-analyzer gate/bound?
3. RC-3 — cross-scope fill order (cluster before namespace) doesn't interleave by priority the way
   the regular additive path does; accepted as part of the #1003-deferred gap, or should it match?
4. RC-4 — P/D fill has no joint min-utilization throttle (confirmed with a worked counter-example:
   scarce same-cycle budget can invert the prefill:decode ratio for at least one cycle); accepted as
   a self-correcting Alpha-scope transient, or should P/D fill jointly throttle like the regular
   path?

## Notes for a future GH comment (not posted yet)

- NTH-2 ("off path unchanged"): if we post, say this was **verified logically** (control-flow
  inspection — `Rescale.any()` false ⇒ `applyRescale` never runs ⇒ the two new lines in `Optimize`
  are no-ops), not just inferred from the tests passing.

---

## GH review comment — POSTED 2026-07-27

Posted as a review **comment** (state `COMMENTED`), not an approval:
[pullrequestreview-4788208596](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452#pullrequestreview-4788208596).
Matches the voice of the actual posted #1442/#1392 reviews (short intro, numbered non-blocking
items, function names not line numbers, casual-precise). RC-1/2/3/4 map 1:1 to items 1-4; TODO-2
folded in as the closing minor note; NTH-1/NTH-2 omitted (no action needed, nothing to ask). Explicit
non-blocking framing added per Dean's instruction before posting.

> Nice mechanism — `computeRescaleTargets` reproduces the proposal's worked examples exactly, and the
> pacing/never-over-budget guarantees hold up (traced the double-debit and free-capacity-gating by
> hand). Test coverage is unusually thorough for an Alpha, and I confirmed by inspection that the
> off-flag and no-limiter paths are structurally unchanged.
>
> Opt-in and off-by-default, so no behavior changes today, and nothing below is strictly blocking
> for an Alpha — but a few questions before it's on anywhere:
>
> 1. **`DecisionReasonRescale` — stabilization consumer coming later?** The comment says downstream
>    stabilization must not damp a reclaim as noise, but nothing in-tree special-cases this reason
>    yet (`gpurebalance`'s damping is a TODO and doesn't read `DecisionReason`). Today it only feeds
>    the metrics label. Forward-looking, or is there a consumer I'm missing?
>
> 2. **Reclaim bypasses the multi-analyzer scale-down gate — intentional?** `reclaimRole` sheds
>    replicas from a bound computed purely off the saturation water-fill delta — it skips
>    `needsScaleDownForRole`/`safeRemovalReplicasForRole`, which `scaleDownRoleIterated` uses to
>    require every analyzer's agreement before touching a role. So if a co-enabled analyzer (e.g. TA)
>    reports a role fully loaded (`RoleSpare ≤ 0`) while saturation sees spare, the regular path
>    leaves it alone but rescale reclaims anyway. Example: model at 6 GPUs, saturation-only demand
>    implies a target of 2, TA reports the role fully loaded — rescale still sheds 4 GPUs from it. Is
>    saturation-only reclaim deliberate for Alpha, or should it reuse the existing gate?
>
> 3. **Cross-scope fill order vs. the regular path's priority ordering.** `fairShareScaleUp`
>    interleaves cluster- and namespace-scoped models in one priority-ordered loop; rescale processes
>    cluster groups entirely before namespace groups, priority only breaking ties within a group. So
>    under a same-type physical-pool oversubscription across scopes, a lower-priority cluster model
>    could win scarce GPUs over a higher-priority namespace one. Looks like it only bites in the
>    physical∧quota case already deferred to #1003 — just confirming that's the intended scope.
>
> 4. **P/D fill has no joint per-role throttle.** The regular path (`allocateForModelPaired`)
>    throttles both roles to the same `deltaUtil` each iteration and never commits one without the
>    other. Rescale's P/D fill instead processes roles sequentially off one shared `freeThisCycle`
>    counter, so a scarce cycle can fill one role to 100% of target while its pair gets almost
>    nothing. Example: prefill:decode demand 6000:2000 (true ratio 3:1), only 3 GPUs free → decode
>    fills fully (2/2) before prefill's turn, landing at 1:2 — inverted for that cycle. Self-corrects
>    over later cycles, but worth confirming the transient's acceptable for Alpha.
>
> Minor: branch's a bit behind current `main` — worth a rebase before merge, no urgency since CI's
> green.

**Status:** posted as `COMMENTED`, not approved. **Not yet done:** approving the PR — hold until
ev-shindin responds to items 2 and 4 (the two genuine open correctness questions), or Dean decides
to approve regardless given the off-by-default Alpha scope.

---

## Author response + resolution (2026-07-28)

ev-shindin replied on the PR (2026-07-28,
[issuecomment-5101323448](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452#issuecomment-5101323448)):
*"All points you raised are valid and will be addressed in the beta version. Please look to
[#1447](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1447)."*

**Checked #1447's Alpha/Beta/Stable roadmap against all four items — only partially accurate as
stated:**

| Item | Covered by #1447? |
|---|---|
| RC-1 (`DecisionReasonRescale` — no stabilization consumer) | **Yes** — Alpha's checklist explicitly names "reclaim bypasses scale-down damping" as current-and-intentional (dependency: #1353 in-WVA stabilization + direct actuation must land first); Beta's hysteresis (min share-gap / cool-down) is the forward path. Matches our hypothesis exactly. |
| RC-2 (reclaim bypasses the multi-analyzer scale-down gate) | **No** — the issue never mentions analyzer combination, TA, or `RoleSpare`, in Alpha, Beta, or Stable. |
| RC-3 (cross-scope fill order vs. #1003-deferred partition) | **Yes** — Stable's "multiple budgets... physical∧quota composition depends on #1003" is exactly this. |
| RC-4 (P/D fill has no joint per-role throttle) | **No** — no mention of P/D, roles, or prefill/decode balance anywhere in the issue. |

So RC-1 and RC-3 are genuinely tracked; **RC-2 and RC-4 — the two items that are actual correctness
gaps rather than design-scope questions — are not captured in #1447's text.** Flagged this to Dean.

**Dean's resolution (2026-07-28):** good enough for Alpha (off-by-default). Dean will follow up with
Evgeny **directly** (not via GH) to ensure RC-2/RC-4 aren't lost heading into Beta — they're captured
in the PR comment thread and in Dean's own docs (this review doc) regardless of #1447's current text.
**PR #1452 approved**
([pullrequestreview-4795542140](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1452#pullrequestreview-4795542140)),
with a closing comment noting the same split (RC-1/RC-3 tracked by #1447; RC-2/RC-4 to be confirmed
directly with Evgeny).

**Review closed.** No further action from us unless Dean's direct follow-up with Evgeny surfaces new
scope.

## Follow-up tracking (not yet done)

- **Close as DONE when PR #1452 merges** — update this doc's status and the CURRENT.md PR Status row
  from "approved" to "merged" once it lands.
- **RC-2 (multi-analyzer scale-down gate bypass) and RC-4 (P/D joint per-role throttle) are not
  covered by #1447's text**, despite ev-shindin's "all points valid, addressed in beta" reply. Dean
  is following up with Evgeny directly as the primary path — this is the backstop: when Beta-stage
  rescale PRs land (tracked under #1447's Beta milestone), re-check them against RC-2/RC-4 here
  before assuming they're resolved, in case the direct conversation didn't fully thread through to
  the eventual PR.
