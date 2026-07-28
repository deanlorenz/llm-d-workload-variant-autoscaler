---
type: review
pr: 1470
title: "fix(saturation-v2): charge waiting requests by P/D role"
author: ev-shindin
status: FINAL — APPROVE review posted 2026-07-27 (LGTM, no blocking findings)
date: 2026-07-27
---

# PR #1470 Review — charge local-queue waiting requests by P/D role

**PR:** [#1470](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1470) — fixes #1456
**Author:** ev-shindin
**Base:** main | **Head:** `fix/1456-saturation-v2-decode-waiting-demand` (ev-shindin fork) @ `b23fe5c9` | **State:** open
**Scale:** 10 files, +578/−41
**CI:** all green (lint-and-test 3m27s, e2e-tests-full 14m51s, e2e-tests-smoke 8m59s, DCO, signed-commits, kustomize-build)
**Reviewed:** 2026-07-27 (no prior reviews/comments on the PR)

---

## What it does

Corrects the local-engine-queue demand term in the saturation **V2** analyzer to charge waiting
requests **by P/D role**, instead of the previous flat `QueueLength × AvgInputTokens` applied to
every replica regardless of role.

| Role | Per-request charge |
|------|--------------------|
| `prefill` | `AvgInputTokens` |
| `decode` / `both` | `AvgInputTokens + AvgOutputTokens` |

The charge is centralized in a new `waitingQueueDemand(rm, role)` helper, called from both the main
path (`computeReplicaCapacity`) and the fallback path (`computeReplicaCapacityFallback`, no
`vllm:cache_config_info`). The role is plumbed from `input.VariantStates[].Role` via a new
`rolesByVariant` map into both paths. Supporting changes:

- **`domain.RoleDecode = "decode"`** added; `estimateSchedulerQueueDemand` switched off its bare
  `"prefill"`/`"decode"` string literals onto the `domain.Role*` constants (pure refactor).
- **Input hardening** in `waitingQueueDemand`: computes the charge in `float64` and rejects the
  result with a single `!(demand > 0) || demand >= float64(math.MaxInt64)` gate before the `int64`
  conversion — covering NaN, ±Inf, negative, and finite-but-out-of-range values. Multiply-then-
  truncate (vs. the old truncate-then-multiply) also removes per-request rounding drift.
- **Gate on combined cost**, so an output-only decode replica (`AvgInputTokens == 0`,
  `AvgOutputTokens > 0`) is no longer charged zero.
- **`variants[].role`** emitted on the `analyzer-result` log line, canonicalized so an unset role
  renders as `both`.
- **Docs**: per-role formula + operational note in `saturation-scaling-config.md`; `role` field +
  rewritten `demand` description in `cycle-log.md`; "unbounded above" note on
  `wva_saturation_utilization` in `prometheus.md`.

---

## Verdict

**Correct, unusually well-documented, thoroughly unit-tested. No blocking findings.**

This is a high-quality PR. The two genuine risk areas are both **self-flagged by the author** in the
PR body ("Reviewer notes") and I confirmed both against the source — they are real, accepted
trade-offs, out of scope to fix here. The remaining items are discussion/observability notes. My
recommendation is **approve**, optionally after the author files the two pre-existing items as
tracking issues (they offered to).

---

## Logical-path verification — the `(analyzer, role)` separation (per Dean's framing)

**Framing (Dean):** when a scaled target carries a role, each role's analyzer should conceptually
be a *separate* analyzer — `(analyzer, role)` produces a per-role metric that is **non-comparable**
across roles (prefill demand is in `I` units, decode demand in `I+O` units, and scaling one role
does not relieve the other). The code does **not** model this as first-class separate analyzers
(true for both satV2 and TA), so the question is whether the calculation still works out under this
PR's role-aware charge. **It does — verified end to end.**

The decision path already uses **`(model, role)` as the allocation unit**, so the two roles'
non-comparable demands never meet on any path that produces a scaling decision:

1. **Per-replica charge is role-correct.** `waitingQueueDemand(rm, role)` uses the replica's variant
   role (`rolesByVariant[rm.VariantName]` ← `VariantStates[].Role`): prefill → `q·I`, decode/both →
   `q·(I+O)`. (`analyzer.go:88,164,327`)
2. **Per-variant sum is role-homogeneous.** A variant has exactly one role, so
   `VariantCapacity.TotalDemand` (sum of `ReplicaDemand` over that variant's replicas) is in a single
   role's unit. (`analyzer.go:385,412`)
3. **Per-role aggregate is same-unit.** `aggregateByRole` → `aggregation.AggregateByRole` filters
   variants by role and sums, then adds the same-role scheduler-queue split (`queueDemand.byRole`,
   which uses the identical prefill=`I` / decode·both=`I+O` convention). Returns **nil** only when no
   variant has a genuine role (all `""`/`both`). (`analyzer.go:438-475`)
4. **Thresholding is per-role.** `applyUniversalThreshold` computes RC/SC for each
   `RoleCapacities[role]` from that role's own `TotalDemand`/`TotalSupply`. (`engine_v2.go:274-290`)
5. **The optimizer consumes per-role, not pooled.** `initRoleState` — disaggregated
   (`RoleCapacities != nil`) ⇒ `pickerState[i][role] = RoleCapacities[role].RequiredCapacity`,
   `RoleSpare[role] = …SpareCapacity`; **the pooled model-level `Result.RequiredCapacity/SpareCapacity`
   are never read on this branch.** Non-disaggregated (`nil`) ⇒ one synthetic `both` role from the
   model-level scalars — sound because every variant is then the same `both` unit. `roleBottleneckReplicas`
   / `roleAggRemaining` / joint-commit all key on `(model, role)`. (`analyzer_helpers.go:76-158`)
6. **Observability is per-variant (role-homogeneous).** `wva_saturation_utilization` is emitted per
   variant from `VariantCapacity.Utilization` (`cost_aware_optimizer.go:302`), a role-homogeneous
   ratio. The **only** cross-role pooling is the model-level `Result.TotalDemand/TotalSupply/Utilization`,
   and it surfaces **only** in the `analyzer-result` log line's `util` field (`engine_v2.go:452`) —
   diagnostic, never a decision or alert input.

**Conclusion.** The PR's role-aware charge rides the existing per-role plumbing correctly; prefill-`I`
and decode-`(I+O)` demands are never compared or summed against a shared supply where a scaling
decision is made. The calculation works out.

**Residual (matches Dean's observation; NOT introduced or worsened here as a decision defect).** The
architecture reconstructs role separation *downstream* (RoleCapacities + `initRoleState`) rather than
modeling `(analyzer, role)` as a first-class comparable-metric stream. This PR neither fixes nor
regresses that. The one place the un-clean pooling is *observable* is model-level `Result.Utilization`
— which this PR makes a **larger** cross-unit blend for disaggregated models (decode now contributes
`I+O`). It is log-only today, so harmless; but it is a live trap if anyone ever routes model-level
utilization into a decision or an operator alert for a disaggregated model. The clean redesign
(each `(analyzer, role)` as a distinct demand/supply stream reconciled in utilization space) is a
separate design item — see [`optimizer-coordination-design.md`](optimizer-coordination-design.md) and
the analyzer-metric-interface proposal (#1444 / issue #1455).

---

## Confirmed correct (verified against PR-head source `b23fe5c9`)

- **Role source is consistent across all three consumers.** The role fed to `waitingQueueDemand`
  (`rolesByVariant[rm.VariantName]`, `analyzer.go:76,88`), the role in `VariantCapacity.Role` that
  feeds `activeRoles` and the log line (`aggregateByVariant`, `analyzer.go:416` → `vs.Role`), and
  the role used by `estimateSchedulerQueueDemand` (via `activeRoles`) **all derive from the same
  `input.VariantStates[].Role`**. There is no path by which the queue charge and the role-attribution
  bookkeeping can disagree for a given variant.
- **The literal→constant refactor in `estimateSchedulerQueueDemand` is behavior-preserving.**
  `RoleBoth="both"`, `RolePrefill="prefill"`, `RoleDecode="decode"` (new) match the old string
  literals exactly; the `default` arm still handles `both`/unknown identically. No semantic change.
- **`canonicalRole` refactor is behavior-preserving.** `activeRoles[canonicalRole(vc.Role)]`
  reproduces the old inline `if role == "" { role = RoleBoth }`.
- **The `int64` conversion guard is sound, including the `>=` boundary.** `QueueLength` is `int`,
  `AvgInputTokens`/`AvgOutputTokens` are `float64`. `!(demand > 0)` correctly rejects NaN (all NaN
  comparisons are false) and non-positive values that `x <= 0` would miss; `demand >= float64(math.MaxInt64)`
  correctly rejects the `2^63` round-up case that a `>` bound would admit into an overflow. All of
  this is pinned by tests (`math.NaN()`, `±Inf`, `1e300`, `math.Pow(2,62)×2`).
- **Output-only decode fix is real and tested.** `waitingQueueDemand(outputOnly, RoleDecode) == 200`
  where the old input-only formula returned 0.
- **Test coverage is thorough.** Unit tests on `waitingQueueDemand` cover every role, empty/negative
  queue, absent metrics, output-only, non-finite, and out-of-range. `Analyze`-level tests exercise
  both the main and fallback paths **through the public entry point** (not just the helper), which
  specifically guards the role hand-off `computeReplicaCapacity → computeReplicaCapacityFallback`
  against a hardcoded role — a genuinely valuable test, called out in a comment. A two-variant P/D
  model asserts per-variant demand and the model-level sum.
- **Docs match code.** The rewritten `cycle-log.md` `demand` description (three terms: resident KV +
  role-aware local-queue projection + `SchedulerQueue`) matches the actual `Analyze` composition;
  the `prometheus.md` "unbounded above" correction is accurate for the V2 `TotalDemand/TotalCapacity`
  ratio.
- **E2E honestly deferred.** The checklist explains why no V2 e2e fixture can exercise this
  (`--fake-metrics` sets only kv/running/waiting; `AvgInputTokens`/`AvgOutputTokens` come from
  5m-rate PromQL over token histograms that static fakes never populate → both `0` → queue term
  inert). This is consistent with the known TA-forward-plan e2e-coverage gap (I-14); the unit story
  is the right substitute. The comment fix in `throughput_analyzer_test.go` correctly updates the
  "cosmetic for V2" rationale to name both token averages.

---

## Reviewer notes (author-flagged; confirmed, non-blocking)

### RN-1 — Fallback-path unit mismatch is worsened, not introduced (author-flagged)

On the fallback path, `EffectiveCapacity` is `EffectiveMaxBatchedTokens` — a **per-step** budget the
store itself calls "a safe lower bound" — while the queue addend is in **absolute KV tokens**. The
two are not the same unit, so a deep queue can push `replicaDemand` past `effectiveCapacity` and
report saturation the replica's actual KV occupancy doesn't support. Raising the per-request charge
(`I → I+O`) **lowers the queue depth at which that false positive fires**.

Confirmed in `computeReplicaCapacityFallback`: `isSaturated := replicaDemand >= effectiveCapacity`
with `replicaDemand = KvCacheUsage×effectiveCapacity + waitingQueueDemand(...)`. The code comment
documents this precisely and a test pins the safe end (idle replica, shallow queue → not saturated).
**Genuinely pre-existing**; fixing it means pairing the fallback path's demand and capacity units,
out of scope. → **Endorse filing as a separate issue** (author offered).

### RN-2 — Interaction with P1-observed k2 amplifies the first scale-up step (author-flagged)

Confirmed accurate against `computeK2` (`analyzer.go:302`): when `queueLen >= queueLengthThreshold`
and `tokensInUse > 0`, k2 is **pinned to `tokensInUse`** (Priority-1 "observed"). In that regime
`effectiveCapacity = min(k1, tokensInUse)`, so the replica's `demand/capacity` is
`(tokensInUse + q·(I+O)) / tokensInUse = 1 + q·(I+O)/tokensInUse`. Because the queue charge lands on
the **numerator** while the denominator is pinned, raising `I → I+O` increases the **magnitude** of
the first scale-up step for long-generation workloads (not merely its trigger point). This is the
intended scale-up bias (the PR argues under-provisioning decode → preemption/recompute thrash), but
it is the residual behavior most worth watching on a real cluster post-merge.

### RN-3 — Highest operator-facing impact is the non-disaggregated default

Because an absent `llm-d.ai/role` label canonicalizes to `both`, **the common single-variant case
now includes output tokens** wherever replicas have a non-empty local queue. This is the physically
correct charge, but it is a behavior change for the majority of deployments, not just P/D setups.
The release note and the `saturation-scaling-config.md` operational note document the expected metric
moves (`wva_saturation_utilization`↑, `wva_required_capacity{unit="continuous"}`↑,
`wva_spare_capacity`↓, one-time `wva_desired_replicas` step, `wva_kv_cache_tokens_used` unaffected)
and the alert re-baselining need. **Communication is adequate**; flagging for maintainer awareness
as the load-bearing user-visible effect of the PR.

### RN-4 — WAITING_FOR_REMOTE_KVS double-count (author-flagged)

Transfer-pending decode requests (vLLM `WAITING_FOR_REMOTE_KVS`) already have blocks allocated, so
part of their prompt KV is inside `KvCacheUsage` **and** counted again in the queue term. The code
comment notes the overlap shrinks toward zero under KV pressure (block allocation failing) — i.e. in
the saturated regime where the decision is actually made. Accepted approximation.

---

## Nits / not-blocking

- **NTH-1 — canonicalization duplicated across a package boundary.** `logAnalyzerResult`
  (`internal/engines/saturation/engine_v2.go`) inlines `if role == "" { role = domain.RoleBoth }`
  rather than reusing `canonicalRole`, because that helper is unexported in package `saturation_v2`.
  The duplication is unavoidable without exporting the helper; harmless, noting only so a future
  reader doesn't "fix" one site and miss the other.
- **RN-4-adjacent — fail-safe direction of the guard.** When `waitingQueueDemand` rejects a
  corrupt/overflow input it returns `0`, i.e. it **under-reports** demand. On the demand side that is
  the conservative direction (won't manufacture spurious scale-up), and the collector already filters
  NaN/Inf upstream, so it only fires on genuinely non-physical data. Worth a sentence in discussion
  only if we want the guard to instead surface a warning log rather than silently zeroing.

---

## Suggested review outcome

- **Approve.** No blocking findings; the two real risks (RN-1, RN-2) are pre-existing / intended and
  documented in-code.
- Optionally ask the author to open the two offered tracking issues:
  - fallback-path demand/capacity unit pairing (RN-1),
  - post-merge watch on long-generation first-step magnitude under P1-obs k2 (RN-2) — or fold that
    into an existing V2-calibration tracking issue.
- Cross-links for context (plans-branch only, do not cite in a GitHub comment):
  `planning/PR1442-review.md` (V2-default flip), `planning/optimizer-coordination-design.md`
  (demand/supply/utilization framing), `planning/TA-forward-plan.md` I-14 (e2e coverage gap), I-26
  (throughput-only-driven models never emit saturation gauges — unrelated but same file region).
