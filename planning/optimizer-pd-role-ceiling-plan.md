# Optimizer P/D Role-Ceiling Fix — Plan

**Status:** IMPLEMENTED, all 10 planned tests landed (6 commits on `optimizer-pd-role-ceiling`,
tip `0c33a3eb`, all gates green). **Dev-guide: incremental edits made by the planner, currently
UNCOMMITTED in the worktree** (`M multi-analyzer-pipeline.md`) — saturation single-source note +
worked example + edge-case table + why-coupled paragraph; pending Dean's review before commit. A
**larger clean/implementation restructure of the dev-guide is under discussion** — see
[`optimizer-coordination-design.md`](optimizer-coordination-design.md) (design + discussion
capture, resumes 2026-07-16). Not yet pushed to origin; a pre-push code-review trigger has been
sent per CONVENTIONS §5.4.
**Type:** Type 3 task plan (single doc — design + plan combined; this is a single-PR-scoped
fix, not a multi-PR mission, so it does not need a separate Type 1 doc).
**Related:** [`multi-analyzer-design.md`](multi-analyzer-design.md) § Architecture/D, § F11;
[`p-d-logic-explainer.md`](p-d-logic-explainer.md); [`error-paths-design.md`](error-paths-design.md)
(file-touch overlap only — see § Related work).

---

## Reading Protocol {#reading-protocol}

Read only this section and the TOC. Build a todo list.
Fetch each step with `Read <this-file> offset:<start> limit:<count>` where count = end - start + 1.
Do not read past the TOC unless fetching a specific section.

---

## TOC {#toc}

- [Background](#background) L41:66
- [Problem statement](#problem-statement) L67:113
- [Related work](#related-work) L114:140
- [Design — corrected algorithm](#design--corrected-algorithm) L141:297
- [Open implementation questions](#open-implementation-questions) L298:315
- [Test plan](#test-plan) L316:396
- [Dev-guide impact](#dev-guide-impact) L397:429
- [Deletion / behavior-change classification](#deletion--behavior-change-classification) L430:454
- [Implementation phases — 6 commits landed, 1 dev-guide gap pending](#implementation-phases--6-commits-landed-1-dev-guide-gap-pending) L455:492
- [Branch / worktree](#branch--worktree) L493:504
- [Re-validation against the anchor refactor (2026-08-16) — no planner active, taken over per Dean's 7-day rule](#re-validation-against-the-anchor-refactor-2026-08-16--no-planner-active-taken-over-per-deans-7-day-rule) L505:598

## Background

Found during a short investigation (2026-07-13, `plans` branch session) into whether `sat_v2`'s
P/D disaggregation logic on current `main` (`6e3ceb3e`) correctly avoids allocating one role
(prefill or decode) beyond what its paired role can support. The mechanism traced:

- `sat_v2`'s `aggregateByRole` (`saturation_v2/analyzer.go:425`) detects disaggregation from
  pod-template labels (`llm-d.ai/role: prefill|decode`, via `getRoleFromScaleTarget`,
  `engine.go:982`) and produces `RoleCapacities[role]` — per-role `TotalSupply`/`TotalDemand`,
  later calibrated into `RequiredCapacity`/`SpareCapacity` by the engine's universal-threshold
  post-step (`applyUniversalThreshold`, `engine_v2.go:254`).
- `internal/engines/pipeline/analyzer_helpers.go`'s `initRoleState` + `allocateForModelPaired`
  implement the scale-up coupling: each role is sized independently, then the joint commit is
  supposed to be trimmed to the min-util role. Scale-down is deliberately independent per role
  (unchanged by this plan — see `p-d-logic-explainer.md`).
- Both `CostAwareOptimizer` and `GreedyByScoreOptimizer` call into this same shared machinery,
  so the fix applies uniformly regardless of `enableLimiter`.
- This is on by default whenever a workload's pods carry the `llm-d.ai/role` label — no
  separate feature flag. No outstanding question about whether this label convention still
  matches the newer llm-d Router "Disaggregation Sidecar" design (checked separately during
  the investigation; open item, not blocking this fix — see the session's prior findings).

[↑ TOC](#toc)

---

## Problem statement

Two conflated defects in `allocateForModelPaired`'s scale-up loop (`analyzer_helpers.go:270`),
confirmed by direct code trace and cross-checked against an existing test:

**1. Hard-abort conflation.** `pick()` returning `""` (no candidate variant with headroom) sets
`allPicked = false`, which `break`s the *entire* joint-allocation loop for *every* role this
reconcile cycle — not just the constrained one. This fires whenever a role hits `maxReplicas`
or (for `GreedyByScoreOptimizer`) its accelerator pool is exhausted, **regardless of whether
that role's own demand is even unmet**.

**2. Marginal- vs. achieved-util conflation.** Even without the hard abort, today's
`utilByRole[role] = n×PRC / remainingDemand` is a *this-round-marginal* ratio. A role that can't
add more this round computes `util = 0`, which (via `deltaUtil = min(...)`) drags the *entire*
joint commit to 0, triggering the second early exit (`if deltaUtil <= 0 { break }`) — same net
effect via a different code path. Both early exits must be removed together; fixing only one
just relocates the bug.

**Concrete repro** (from the investigation): P at `maxReplicas=2`, PRC=100 → supply=200,
demand=300 → achievable ceiling util=0.667 (structurally can never do better). D at 1 replica,
PRC=100 → supply=100, demand=300 → util=0.33, fully unconstrained. Expected: D scales toward
0.667 to match P's ceiling. **Actual, on current `main`:** D gets zero allocation, every
reconcile cycle, indefinitely — a steady-state stuck condition, not a transient blip, since
nothing about `maxReplicas` or the demand numbers changes between cycles.

**More general variant, easier to trigger, currently untested:** a role that is *already
satisfied* (demand met) but happens to sit at `maxReplicas` — an entirely ordinary, unremarkable
steady state — still fails `pick()` on every call, regardless of whether it needs anything, and
still aborts the sibling role's allocation.

**Confirmed against an existing test, not just hypothetical:** `greedy_score_optimizer_test.go:997`
("should handle GPU exhaustion for one role without affecting the other") currently *asserts the
bug as correct* — its own comment says "Paired allocation: if P-side (H100) is exhausted, the
pair cannot commit. Both prefill and decode stay at their current replicas." This test must be
rewritten, not just left passing, as part of this fix.

**Confirmed against design intent, not just implementation:** `multi-analyzer-design.md`'s
"0-cases" paragraph (§ Architecture/D) describes a continuous, graceful `min()`-based joint
bound — *"If `Capacity_role=0` and `Demand_role>0`, then `util_role=0`... the min pulls
allocation toward whichever role is currently lagging."* The design never distinguishes "no
capacity yet" from "structurally capped, will never get more." The hard-abort behavior in code
is an implementation artifact, not something the design calls for.

[↑ TOC](#toc)

---

## Related work

**No mechanism overlap, file-touch overlap only:**

- `error-paths-design.md` (Status: DRAFT) — analyzer-level `MeasurementBias` signal propagation
  (`SCBias`/`RCBias` on `AnalyzerResult`/`VariantCapacity`), feeding the engine's threshold
  post-step. Entirely orthogonal mechanism — it never touches `allocateForModelPaired` or
  `RolePickFn`. File-touch overlap: its checklist includes "Optimizer: per-variant bias-aware
  allocation," which would touch the same `cost_aware_optimizer.go`/`greedy_score_optimizer.go`
  files this fix touches. Whichever PR lands second rebases around the first — no design
  coupling required, just a sequencing note for whoever picks up either PR.

**Forward-looking alignment:**

- `multi-analyzer-design.md` § F11 (Joint-allocation generalization beyond P/D) — this fix's
  `jointCap = min_role(candidateCeiling_role)` formula generalizes to N roles/legs without
  modification, directly supporting F11's stated direction (`min(util_P, util_D)` →
  `min over legs`). This fix is a **prerequisite correctness fix**, not a blocker for F11 — but
  F11 should build on the corrected formula, not the current buggy one.
- `open-items-roadmap.md` `MA-F11` / `MA-CAV-2` are related but distinct (arity generalization /
  cross-analyzer `RoleCapacities` aggregation strategy). No existing roadmap item covers this
  specific defect — confirmed via grep during investigation. This is net-new.

[↑ TOC](#toc)

---

## Design — corrected algorithm

Two orthogonal computations, currently tangled into one loop — kept apart:

1. **Per-role achievable amount this round** (`n_role`, from `pick()` + `roleBottleneckReplicas`
   + `capByRole` — unchanged from today) — single-role, resource-only (`maxReplicas`, and for
   `GreedyByScoreOptimizer` the currently-available GPU map). **Treated as a plain number, never
   special-cased.** A failed `pick()` means `n_role = 0` for this role this round — no different
   in kind from `n_role = 1`. This also means the fix is forward-compatible with any future
   finer-grained pick semantics (e.g., per-variant-attempt granularity within a role) without
   changing the core formula below.

2. **Cross-role demand coupling** — resource-blind, computed purely from `TotalSupply`/
   `TotalDemand` already on `RoleCapacities`, plus one snapshot taken once per model per
   `initRoleState` call:

   ```
   trueRC_role            = RoleCapacities[role].RequiredCapacity     (read directly off the
                                                                        analyzer's saturation
                                                                        entry via a small new
                                                                        helper, saturationRoleView;
                                                                        fixed for the whole
                                                                        allocateForModelPaired
                                                                        call — never from
                                                                        pickerState)

   denom_role             = trueRC_role + TotalAnticipatedSupply_role

   committed_role         = Σ over role's variants v: (targets[v] − stateMap[v].CurrentReplicas)
                            × PRC_v                (actual replica commits made so far THIS
                                                     call — not a pickerState delta)

   achievedSoFar_role     = (TotalSupply_role + committed_role) / denom_role
                            — clamped to max(·, 1.0) when trueRC_role <= 0

   candidateCeiling_role  = achievedSoFar_role + (n_role × PRC_role) / denom_role

   jointCap               = min_role(candidateCeiling_role)     — over roles with denom_role > 0
                            only; denom_role <= 0 (no real demand) roles are excluded and forced
                            to k_role = 0

   k_role                 = 0                                        if denom_role <= 0 or
                                                                       n_role == 0 or raw <= 0
                            clamp( max(floor(raw), 1), 0, n_role )   otherwise
                            where raw = (jointCap − achievedSoFar_role) × denom_role / PRC_role
   ```

   **Resolved during implementation** (landed across 4 commits on `optimizer-pd-role-ceiling`;
   planner-approved 2026-07-14) — the plan originally left two points open, the coder's own test
   design surfaced two more:

   1. **Where to read `trueRC_role`/`denom_role` from.** Not inside `initRoleState` as originally
      suggested. The plan's first answer here (commit `a694012a`) was a local snapshot of
      `pickerState[satIdx][role]` at the top of `allocateForModelPaired` — reasoned as sufficient
      because `GreedyByScoreOptimizer.allocateForModel` externally caps `pickerState` to that
      iteration's fair-share budget *before* calling in, so snapshotting inside `initRoleState`
      would capture the pre-cap value. That reasoning holds for the *denominator*, but turned out
      insufficient for the numerator (see point 4 below) — commit `911e13b7` replaced it with a
      direct read off the analyzer's `RoleCapacities` via `saturationRoleView(s)`, snapshotted
      once per call, bypassing `pickerState` entirely. Zero signature changes either way.
   2. **`denom_role` derivation.** `RoleCapacity` has no `scaleUp` field, and
      `NamedAnalyzerResult.ScaleUpThreshold` is unpopulated by every existing pipeline-package test
      fixture — using it directly would make every disaggregated unit test divide by zero.
      Derived algebraically instead from the RC formula itself (`RC = max(0, TotalDemand/scaleUp −
      TotalAnticipatedSupply)`, exact whenever `RC > 0`): `denom_role = trueRC_role +
      TotalAnticipatedSupply_role`. Degrades to an exact match for today's marginal-ratio math
      whenever `TotalAnticipatedSupply_role = 0` (true of every existing "should keep passing
      unchanged" P/D test).
   3. **Planner amendment — `achievedSoFar` clamp when `trueRC_role <= 0`.** The `denom_role`
      approximation above is only exact when `RC > 0` (unclamped). When a role's demand is already
      fully met by anticipated/booting supply (`RC` clamped to 0), the approximation's denominator
      can be *larger* than the true `TotalDemand/scaleUp`, making `achievedSoFar` compute to less
      than 1.0 even though the role needs nothing more — which would wrongly drag down `jointCap`
      for the *other*, still-needy role. Fix: whenever `trueRC_role <= 0`, clamp `achievedSoFar_role`
      to `max(computed, 1.0)`. This is exact, not approximate — `RC <= 0` always means the
      demand-side target is already met, regardless of how the denom was derived. Verified by the
      "satisfied-but-capped" test (§ Test plan, item 2).
   4. **Found post-Commit-1, by the coder, while designing the FairShare-pressure test (item 6):
      `achievedSoFar`'s numerator must come from actual commits, not `pickerState`.** The original
      fix (`a694012a`) read the numerator as `trueRC_role − pickerState[i][role]` — a delta against
      the at-entry `pickerState` snapshot. That's only a faithful proxy for "how much has this role
      achieved this call" when nothing external touches `pickerState` between outer calls.
      `GreedyByScoreOptimizer.allocateForModel` violates that on every call after the first: it
      rebuilds `pickerState` fresh from `RequiredCapacity` and externally caps it to that
      iteration's fair-share budget before calling in. Whenever more than one model competes for
      the same GPU pool, that cap sits below the true remaining demand — and reading the numerator
      off the capped `pickerState` value misread the unfunded gap as "already achieved," inflating
      one role's progress and letting a sibling role over-commit past its true joint ceiling. No
      test in the original round exercised genuine multi-model fair-share competition, which is
      why this went uncaught until the FairShare-pressure test was designed. Fixed in `911e13b7`:
      `committed_role` is now computed directly from `targets[v] - stateMap[v].CurrentReplicas`
      (summed over the role's variants, × PRC) — exact regardless of how many outer fair-share
      calls have run, since `targets[]` persists and accumulates across the whole optimizer pass.
   5. **Rounding.** Today's single global "round up to at least 1 replica" guard (applied once,
      after the removed `deltaUtil<=0` break had already ruled out non-positive deltas) moves
      per-role, gated on `raw > 0`:
      ```go
      k := 0
      if prc > 0 && denom > 0 && n > 0 {
          raw := (jointCap - achievedByRole[role]) * denom / prc
          if raw > 0 {
              k = min(max(int(math.Floor(raw)), 1), n)
          }
      }
      ```
      Verified against the asymmetric demand-proportional case (RC 15000/5000): without the
      per-role round-up, decode's fractional 0.667-replica increment would floor to 0 and silently
      drop a replica the current code correctly grants.

   The `min` still applies to `candidateCeiling` (what each role *could* reach this round if given
   everything pickable) — **not** to `achievedSoFar` directly. Taking the min of the pre-round
   achieved values alone would make cold start (both roles at 0) always compute `jointCap = 0` and
   never progress — the same failure mode as the `deltaUtil<=0` break, just moved into the
   formula. `candidateCeiling` is what avoids that.

3. **Loop termination: the existing `anyPositive` check is sufficient, unchanged.** Both early
   exits (`allPicked=false → break`, `deltaUtil<=0 → break`) are **removed**. The loop keeps
   iterating as long as `anyRoleNeedsScaleUp` (unchanged gate) — and within an iteration, if
   `k_role = 0` for every role (nobody could move at all, whether from a resource ceiling or
   from having already reached `jointCap`), the existing end-of-iteration `if !anyPositive {
   break }` check stops the loop. No new stopping logic needed.

4. **Commit stays batched, not sequential — this is what avoids needing a retroactive
   correction.** Gather every role's `n_role` (candidate pick) *before* writing anything to
   `targets[]`, compute `jointCap` from all of them, then commit every role's `k_role`
   simultaneously. A role is never over-committed relative to a sibling's later-discovered
   constraint, because no commit happens until every role's number for this round is known —
   exactly the shape `allocateForModelPaired` already has today (`variantByRole`/`capByRole`
   gathered first, `targets[v] += k` only at the end); only the util formula changes.

**Worked example** (from design discussion): P already at `achievedSoFar_P = 0.67`, frozen
(`n_P = 0` this round, e.g. at `maxReplicas`) → `candidateCeiling_P = 0.67`. D at
`achievedSoFar_D = 0.33`, unconstrained, could reach 1.0 if fully committed this round →
`candidateCeiling_D = 1.0`. `jointCap = min(0.67, 1.0) = 0.67`. `k_P = clamp((0.67−0.67)×.../PRC,
0, 0) = 0` (P's increment is 0, correctly — it's already ahead). `k_D` brings D from 0.33 up to
0.67 (D's increment matches the gap, not its own unconstrained ceiling). Next iteration,
`achievedSoFar` is recomputed fresh for both roles from their new state.

**Invariant to preserve, not build:** `fairShareValue`/`pickerState[i][role]` (used to rank
*models* against each other in `GreedyByScoreOptimizer`'s multi-model fair-share loop) already
derives purely from `RequiredCapacity` (demand-side), with **no** `maxReplicas` influence. This
fix must not change that — `maxReplicas` stays a within-model, per-role allocation concern; it
never feeds into cross-model fairness ranking. Confirmed already true in current code
(`initRoleState`'s `pickerState[i][role] = rc.RequiredCapacity`); the regression test locking this
in landed as commit `911e13b7`'s "FairShare-pressure invariant" context — a 2-model P/D
competition over a shared, constrained GPU pool, asserting identical outcomes whether or not one
model's variant carries a non-binding `maxReplicas`. This is also the test whose design surfaced
point 4 above.

**Scope, confirmed:** this fix covers *both* failure modes identified in § Problem statement —
the under-served-and-capped case and the satisfied-but-capped case — since both go through the
identical code path and the corrected formula handles both without special-casing.

[↑ TOC](#toc)

---

## Open implementation questions

Left for the coder to resolve at implementation time — these are mechanical, not design forks.
The first two below were resolved during implementation kickoff — see § Design — corrected
algorithm, "Resolved during implementation," for the settled answers.

- ~~Where to snapshot `originalRC_role`~~ — **RESOLVED**: local snapshot at the top of
  `allocateForModelPaired`, not inside `initRoleState`. See § Design.
- ~~Whether `n_role` needs a `RolePickFn` signature change~~ — **CONFIRMED, no change needed**:
  `n_role` is already computed today as `min(roleBottleneckReplicas(...), capByRole[role])` for
  both `costGreedyRolePick` and `fairShareRolePick`; this fix reuses that value.
- `scaleDownRoleIterated` is **out of scope** — scale-down stays independent per role, unchanged,
  per existing design (`p-d-logic-explainer.md`). Do not touch it as part of this fix.

[↑ TOC](#toc)

---

## Test plan

**Status: all 10 items landed**, spanning `a694012a`, `911e13b7`, `4fdd1123`, `69c759a1`,
`0c33a3eb` (test files) and `2e3f023d` (dev-guide). Items 9/10 were found during a planner
corner-case audit (2026-07-14) and closed by `0c33a3eb`. `make test`/`gofmt`/`make lint`/
`go build ./...`/`go vet` all verified green on the branch per the coder's status file.

**Must change (inverts an existing assertion) — DONE, `a694012a`:**

- `greedy_score_optimizer_test.go:997` ("should handle GPU exhaustion for one role without
  affecting the other") — fixture recalibrated to non-zero `TotalSupply` (prefill 200/decode
  100, `TotalDemand=300` each) and the assertion now expects `decode-v` to advance toward the
  0.667 ceiling while `prefill-v` stays unchanged. Comment rewritten (no longer states the bug as
  intentional design).

**New tests — DONE:**

1. **Capped-with-unmet-demand** — `a694012a`, `cost_aware_optimizer_test.go`: "should advance the
   unconstrained role to match a maxReplicas-capped role's achievable ceiling".
2. **Satisfied-but-capped** — `a694012a`, same file: "should let the unconstrained role advance
   freely when the capped role is already satisfied" (exercises the `achievedSoFar` clamp,
   resolution 3).
3. **Cold start regression guard** — `a694012a`, same file: "should make joint progress from a
   cold start in one commit (both roles at 0 achieved)".
4. **Multi-variant-per-role** — `4fdd1123`, `cost_aware_optimizer_test.go`: "should pick up a
   role's next-cheapest variant across iterations once the cheapest exhausts".
5. **Synthetic 3-role sanity check** — `4fdd1123`, same file: "should generalize the joint
   ceiling bound across three synthetic roles".
6. **FairShare-pressure invariant** — `911e13b7`, `greedy_score_optimizer_test.go`: 2-model P/D
   fair-share competition over a shared, constrained GPU pool; identical outcomes whether or not
   one model's variant carries a non-binding `maxReplicas`. This is the test whose design
   surfaced the numerator bug fixed by the same commit (§ Design, resolved-during-implementation
   point 4).
7. **Multi-analyzer `RoleCapacities` divergence (achieved/denom)** — `69c759a1`,
   `cost_aware_optimizer_test.go`: "should compute achieved-so-far from the saturation entry
   only, even when another analyzer disagrees". Saturation and throughput both populate
   `RoleCapacities` for the same role with different `RequiredCapacity` (200 vs 500) —
   `achievedSoFar`/`denom` must read saturation's alone (matching the existing `saturationEntry`
   single-canonical-source convention), never the other analyzer's value. Not anticipated in the
   original design discussion — found while confirming corner-case coverage was complete.
8. **Multi-analyzer `RoleCapacities` divergence (`n_role` sizing)** — `69c759a1`, same file:
   "should still size n_role from the max across all analyzers, not the saturation entry alone".
   Companion to item 7: narrowing `achievedSoFar`/`denom` to saturation-only must not also narrow
   `roleBottleneckReplicas`'s cross-analyzer max, which is a different, intentionally-still-
   aggregating code path.

9. **Fractional round-up-to-1, isolated** — `0c33a3eb`, `cost_aware_optimizer_test.go`: "should
   round a fractional replica gap up to 1, not floor it to 0". Planner-verified by independent
   hand-trace (not just the coder's commit message): prefill cold-starts at `maxReplicas=1`
   becoming `jointCap=1.0`; decode starts at `achieved=0.667`, needs a `raw=0.5` fractional
   increment that only the `max(floor(raw),1)` guard (§ Design, resolution 5) rounds up to 1. The
   trace also surfaces a subtlety beyond the commit message: decode's integer-replica commit
   slightly *overshoots* the exact gap (`achieved` ends at `1.333`, past `jointCap`), and the
   formula correctly emits `k=0` for it on the next iteration (`raw<0` guard) rather than
   misbehaving — confirms the negative-delta path is sound, not just the round-up path.
10. **Mid-call transition from headroom to capped, after partial progress** — `0c33a3eb`, same
    file: "should freeze a role's contribution correctly after it becomes capped mid-call, not
    just when already capped from the start". Planner-verified by independent hand-trace: prefill
    starts with real headroom (`maxReplicas=2`, 0 current), defines `jointCap=0.4` in iteration 1
    using its full headroom, which exhausts its cap as a *result* of that same commit; iteration 2
    correctly freezes prefill's contribution (`n=0`, `achieved` unchanged at `0.4`) while decode's
    own iteration-2 `achieved` (`0.5`) already exceeds the frozen `jointCap`, correctly emitting
    `k=0` for decode too rather than over-committing. Confirms `committed_role`/`n_role` really are
    recomputed correctly from live state regardless of *when* a role became capped, closing the
    gap items 9/10 were opened to cover.

**Kept passing unchanged, no edits needed, confirmed:** `cost_aware_optimizer_test.go`
"Disaggregated (P/D)" contexts predating this fix (symmetric scale-up, D-only demand,
independent scale-down).

**Deliberately left untested (coder + planner concur, low priority):** a role with an entry in
`RoleCapacities` but zero matching variants (`variantsForRole` returns empty) — `pick()` returns
`("", 0)` immediately, and the role degrades to the same "frozen role contributes its achieved
fraction" path already covered by the maxReplicas-capped tests (1/2/7), just via `capN=0` for a
structural reason instead of a resource one. No new code path; every real role has ≥1 variant in
production.

[↑ TOC](#toc)

---

## Dev-guide impact

**Mostly DONE, one gap found by planner review (2026-07-15).** Commit `2e3f023d`
(`docs/developer-guide/multi-analyzer-pipeline.md`) replaces the pre-fix marginal-util
description (`Δ_util = min_role util_role`) and the `roleAggRemaining` reference (function
removed, see § Deletion) with the corrected `achievedSoFar` / `candidateCeiling` / `jointCap`
formula, and states explicitly that a role frozen at its own resource ceiling contributes its
*achieved* (not zero) util to the min. Verified accurate against the actual committed code.

**Gap — now edited, UNCOMMITTED (2026-07-15).** `2e3f023d` landed *before* the
multi-analyzer-divergence tests (§ Test plan items 7/8, commit `69c759a1`) and never named the
saturation-only single-source rule. The planner (authorized by Dean; coder done) edited the
dev-guide directly in the worktree to close this and, while there, added: a **worked example**
(the maxReplicas-capped repro, iteration-by-iteration), an **edge-case → behavior → test table**
(all 9 landed scenarios), a **"why roles are coupled"** paragraph, and the **`saturationRoleView`
single-source** note folded into the `denom_role` definition. **These edits are UNCOMMITTED** in
the `optimizer-pd-role-ceiling` worktree (`git status`: `M multi-analyzer-pipeline.md`, tip
`0c33a3eb`) — not yet committed pending Dean's review.

**Dev-guide is now planner-owned — coder must not touch it.** The earlier trigger
`session/handoffs/pd-role-ceiling__devguide-multi-analyzer-gap.md` (to the coder) is **superseded**:
the planner is handling the dev-guide directly. The coder is done on this branch.

**Larger follow-on (under discussion, not started):** a structural rewrite of the dev-guide into a
*clean-design* section + an *implementation* section, per the design captured in
[`optimizer-coordination-design.md`](optimizer-coordination-design.md). The uncommitted edits above
are the *incremental* improvement; the clean/implementation split is the bigger effort resuming
2026-07-16.

[↑ TOC](#toc)

---

## Deletion / behavior-change classification

Per `CONVENTIONS.md` "document every deletion" — this PR changes existing behavior, not just
adds code, so it must be classified:

**Changed (correctness fix, not deprecated/deferred) — landed in `a694012a`:**
- `allPicked=false → break` early exit in `allocateForModelPaired` — **removed.**
- `if deltaUtil <= 0 { break }` early exit — **removed.**
- Both replaced by the achieved/candidate-ceiling formula plus the existing `anyPositive` check
  as the sole loop terminator.
- **Why removed now (not deferred):** both were incorrect conflations of "single-role resource
  exhaustion" with "no joint progress possible anywhere," confirmed against design intent
  (`multi-analyzer-design.md` § Architecture/D "0-cases") and reproduced concretely (steady-state
  stuck D, reproducible on current `main`). This is a bug fix; there is no future version of the
  old behavior to preserve intent for.

**DEPRECATED — `roleAggRemaining` helper, removed in `a694012a`.** Computed the this-round
cross-analyzer remaining demand for a role, feeding the old marginal-ratio `utilByRole`
computation. Superseded by the `achievedSoFar`/`committed_role` formula above, which doesn't need
a per-round remaining-demand figure — no future consumer, no deferred intent.

[↑ TOC](#toc)

---

## Implementation phases — 6 commits landed, 1 dev-guide gap pending

0. **Red first.** Folded into `a694012a` (fixture recalibration + new tests written and run
   against the fix in the same commit).
1. **Commit `a694012a`** — `fix(optimizer): stop P/D joint scale-up hard-abort on single-role
   cap`. Rewrites `allocateForModelPaired`, removes both early exits, adds the achieved/candidate-
   ceiling formula, recalibrates the line-997 fixture, adds 3 new tests, removes `roleAggRemaining`
   (dead code).
2. **Commit `911e13b7`** — `fix(optimizer): compute achieved-so-far from actual commits, not
   pickerState`. The numerator fix (§ Design, resolved-during-implementation point 4), found while
   designing the FairShare-pressure test; adds that test.
3. **Commit `4fdd1123`** — `test(optimizer): cover multi-variant-per-role and >2-role joint
   allocation`. Test-only, two more § Test plan scenarios.
4. **Commit `2e3f023d`** — `docs(optimizer): document the corrected joint-allocation formula`.
   Dev-guide update (later found to predate items 7/8 — see § Dev-guide impact).
5. **Commit `69c759a1`** — `test(optimizer): cover multi-analyzer RoleCapacities aggregation`.
   Test-only, § Test plan items 7/8 — found post-review, not anticipated in the original design.
6. **Commit `0c33a3eb`** — `test(optimizer): cover fractional round-up and mid-call cap
   transition`. Test-only, § Test plan items 9/10 — closes the planner corner-case audit gaps;
   all 10 planned tests now landed, planner-verified by independent hand-trace.
7. **Commit 8 — EDITED, UNCOMMITTED (planner, 2026-07-15).** Dev-guide edits made directly in the
   worktree (not the coder): `saturationRoleView` single-source note + worked example + edge-case
   table + "why roles coupled" paragraph. Shows as `M multi-analyzer-pipeline.md` in the worktree,
   tip still `0c33a3eb`. **Not committed** — pending Dean's review. See § Dev-guide impact.
8. **Follow-on (under discussion, not started).** Structural dev-guide rewrite into clean-design +
   implementation sections, per [`optimizer-coordination-design.md`](optimizer-coordination-design.md).
   Resumes 2026-07-16 after Dean confirms the clean-design framing.

All gates green (`make test`, `gofmt`, `make lint`, `go build ./...`, `go vet`) as of commit
`0c33a3eb`; DCO sign-off verified on all 6 landed commits. Not yet pushed to origin — a
`review__optimizer-pd-role-ceiling-ready.md` trigger has already been sent for the pre-push code
review per CONVENTIONS §5.4; the uncommitted dev-guide edits (and any rewrite) should land before
that review is acted on.

[↑ TOC](#toc)

---

## Branch / worktree

Worktree at `optimizer-pd-role-ceiling/`, branch `optimizer-pd-role-ceiling`, off `main`
(`6e3ceb3e`). Registered in `wva.code-workspace`. Tip `0c33a3eb`, 6 commits ahead of `main`. Not
yet pushed to origin — per CONVENTIONS, every code branch needs a matching origin branch, but
only after explicit push confirmation; propose the push once the dev-guide gap lands and the
pending code review is done.

[↑ TOC](#toc)

---

## Re-validation against the anchor refactor (2026-08-16) — no planner active, taken over per Dean's 7-day rule

**This thread has had no commit or status update since 2026-07-28 (19 days) — inactive by Dean's
standing rule ("any planner not committing in the last week is inactive; take over their docs so
everything is documented if they come back").** A fact-finding handoff sent 2026-08-09
(`plan__optimizer-pd-role-ceiling-revalidate-against-pr2.md`) sat unanswered for a week; it is
answered here, read-only — **no code was changed, nothing was pushed, no rebase was performed.**
This section documents findings only, so a returning planner (or Dean) has everything needed to
make the park/revive/close call themselves.

**Corrected context vs. the week-old handoff, first:** PR-2 is
[#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523), not an unpushed
local branch — **OPEN, pushed, CI all-green**, tip `14a5d6cc` (28 commits), not `6d55fbd7`/26
commits as the handoff said. `main`'s current tip is `bebbe88f` (2026-08-12), which already
includes PR-1 (`57f3fe64`) and its `RoleBoth` follow-up fix (`a38d7b73`). The uncommitted
dev-guide edit noted in § Implementation phases item 7 was confirmed **still present and
undisturbed** (`git status --short` only, no other command touched it) — it remains the only copy.

**Q1 — do the 10 landed tests still assert something true and reachable?** No, for a concrete
mechanical reason plus a deeper one. Mechanically: `main`'s `NamedAnalyzerResult` gained `Live` and
`Enabled` fields (from PR-1's analyzer-enablement work); this branch's `withSatEntry`/
`withSatEntryPD` fixture helpers never set either, so `bindingAnchor` now returns `nil` for every
fixture and `CostAwareOptimizer.Optimize` silently skips the model (`cost_aware_optimizer.go:49-51`)
— every test's expectations would fail against an empty decision map. `main`'s own equivalent
fixture helper was updated with exactly `Enabled: true, Live: true` when PR-1 landed
(`cost_aware_optimizer_test.go:14-30` on `main`), confirming the fix shape. But fixing the fixtures
only rescues **4 of the 10** to genuine value — those 4 already have equivalent coverage on `main`
today. The other **6 — including this mission's own last two commits** (fractional round-up,
mid-call cap transition) — assert against `jointCap`/`achievedByRole`/`denomByRole`, a formula
`main`'s rewritten `allocateForModelPaired` (`analyzer_helpers.go:469-573`) no longer computes at
all; it derives `demand` fresh from `pickerState` each iteration and sizes via `deltaUtil`/
`utilByRole` instead. Those 6 test titles are absent from both `main` and PR-2's test files —
never merged anywhere. Porting them means **re-deriving expected values against the new formula**,
not a mechanical fixture fix, and they cover ground `main` currently has zero coverage for
(multi-analyzer achieved-so-far isolation, cross-iteration next-cheapest-variant switching, 3-role
generalization, plus the two corner cases above).

**Q2 — is the suspected bug still live** (anticipated supply in the denominator, not counted toward
achieved)? **Unresolved, and now with a documented contradiction.** The formula itself —
`RequiredCapacity = TotalDemand/scaleUp − TotalAnticipatedSupply` in `applyUniversalThreshold`
(`saturation/engine_v2.go`) — is **byte-identical across the dormant branch, `main`, and PR-2**;
neither refactor touched it. The optimizer-side code this doc's D1 finding cited
(`analyzer_helpers.go:307-354` on the dormant branch, the `achievedByRole` reconstruction) was
rewritten away by `main`'s new `allocateForModelPaired`, so **that specific line-level citation is
dead** — but the same conflation persists one layer up: `main`'s `demand` (denominator of
`utilByRole`) is seeded from `RequiredCapacity`, which already has anticipated supply subtracted at
the source, so anticipated supply still shrinks the remaining-demand target rather than adding to
an achieved numerator — the same shape Open issue #2 describes, reached through a different path.
**Countervailing evidence this may not be a bug at all:** `ta-anchor-dynamic-refresh-plan.md:1689-
1695` states, from a separate investigation into this exact formula, *"The engine's threshold
post-step is correct and is not the bug... do not 'fix' it... Recorded because the opposite
conclusion was reached once and abandoned."* This is a genuine, unresolved disagreement between two
planning threads, not a stale finding to quietly close.

**Q3 — does the clean-design model in `optimizer-coordination-design.md` still hold?**
**Partially.** The supply taxonomy and its data-layer mapping (`aggregation.go`'s `SumTotalSupply`/
`SumTotalAnticipatedSupply`/`SumTotalDemand`) are unchanged in name and purpose on `main` — that part
holds. `applyUniversalThreshold`'s formula (Q2) is unchanged — that part holds too. **What's stale
is the doc's Phase-3 code-verification artifact**: every line citation (`analyzer_helpers.go:307-
354` etc.) points at the now-rewritten `allocateForModelPaired`; D1/D2/D3 as *code citations* are
dead, though D1's underlying *claim* is not (see Q2). One doc caveat is now resolvable and closes
cleanly: D4 flagged `effectiveAvailable`/#1129 as "not verifiable on this branch" — confirmed
present on `main` at `greedy_score_optimizer.go:373`, and the doc's own provisional verdict ("the
current `NamespaceAwareInventory` + `NamespacePools` path is a correct approximation") stands. The
two Phase-2 framing questions (fair-share "what is share measured in," "what does priority do") are
still unanswered by any thread since. **Net: the taxonomy survives; the verification pass against
code needs to be redone, not resumed** — Phase 3 ran once against code that no longer exists.

**Q4 — rebase cost onto current `main`, and does `make lint` pass under 2.10.0?** **Small footprint
by line count, high conflict risk by location, lint status genuinely unknown.** This branch's own
unique work touches only 4 files (~600 lines net: `analyzer_helpers.go`, two test files, the
dev-guide). But `analyzer_helpers.go` is exactly where `main` independently rewrote
`allocateForModelPaired` — the same function this branch's fix commits (`a694012a`, `911e13b7`)
modified — so a real rebase would very likely stop mid-function with a substantive conflict, not a
clean line-shift; re-deriving the fix against the new formula, not a textual reapply.
`greedy_score_optimizer_test.go` is the second collision point (`main` grew it to +708 lines for
new limiter-aware paths). Toolchain: this branch pins `go 1.25.0`/lint `v2.8.0`; `main` is on
`go 1.26.0`/lint `v2.10.0` (PR #1512) — **`optimizer-pd-role-ceiling` is now the only tracked branch
that hasn't re-verified `make lint` under the new toolchain** (PR-2 already has). Not run in this
pass, deliberately — a read-only fact-finding task doesn't build against a worktree whose own
dependent code has since been replaced upstream.

**Summary for whoever makes the park/revive/close call:** 4 of the 10 tests are cheap to fix but
low-value (redundant with `main`). The other 6 are the actual asset this branch was building —
coverage `main` still lacks — but reviving them costs a real re-derivation against the rewritten
formula, not a mechanical port. The suspected bug (Q2) is a live, unresolved disagreement between
this mission's design doc and PR-2's plan doc, not something either refactor settled. The rebase
(Q4) is small in scope but lands on the one file both sides rewrote. None of this was acted on;
all of it is now documented per Dean's standing rule.

Handoff `plan__optimizer-pd-role-ceiling-revalidate-against-pr2.md` closed (`.DONE`) on landing this
section — its fact-finding request is fully answered above.

[↑ TOC](#toc)
