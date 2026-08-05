# Planner note → reviewer: scale-from-zero cost/PRC design discussion + pending plan changes

**Type:** discussion note (planner-authored) · **Date:** 2026-08-05
**Subject plan:** [`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md) (DRAFT) — §2, §7b (Commit 4), §7c, §12, Test 7, Test 10
**Design authority:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (Type 1)
**Status of the plan doc:** **FOLDED IN (2026-08-05).** Both design calls below (Q1/Q2) are
**RESOLVED — Dean approved both.** The plan (§2 merge/fallback, §3 scope, §7b Commit 4, §7c, §10
inventory, §12 deferrals, §13 checklist, Test 7, Test 10) now reflects the decided design: no
`fallbackVariantCost` sentinel, no TA-side `lastCost`/`lastAcceleratorName`; §7b emits the persisted
`lastPerReplicaSupply` (PRC only) for a previously-live-now-zero variant; the §2 (b)-fallback is
enablement-gated; the "`[TA]`-only now behaves like `[sat]`-only" mis-ranking is a documented
known-limitation (not gated). This note is retained as the discussion record for the review pass.

---

## Why this note exists

Dean opened a "discuss and finalize" thread (2026-08-05) on the cost/PRC fallback mechanism the plan
uses for scale-from-zero. The discussion changed the §7b design materially and exposed one merge-level
design fork (§2). This note captures: (A) what is decided and folded in, (B) the §2 refinement (Q1, **approved**),
(C) a known limitation the changes create (Q2, **accepted**), and (D) the two questions — both now
**RESOLVED** by Dean's 2026-08-05 decision. The reviewer's next pass should verify the correctness of
A–C against the code and flag anything the planner has wrong; D is settled.

Verbatim governing directives from the thread (most recent first):

> **(2026-08-05, decision — approves Q1 and Q2)** "2 refinement is OK. [sat] -- trivial; [TA] -- no
> sat fallback PRC; [sat,TA] must be consistent, either anchor or only sat. / [TA] only behaves like
> [sat] only now. Same limit until bug is fixed. Document. don't gate. we fix by fixing sat cost=0
> bug. / fix the docs if needed. commit and I will tell the reviewer."

> **(2026-08-05)** "lastPRC is real. It has to be TA specific for TA only because
> per-model-demand would use same TA metric — using sat's PRC would just be wrong. Need to verify that
> sat's PRC is NOT used in this case. For [sat,TA] case, it should be the anchor's PRC and model-demand
> metric. Whatever is used, it should be consistent between the demand and PRC. / Cost from sat is
> correct — it is the only real source — but, not PRC from sat. / cost=0 for zero replicas is a bug.
> It should be fixed. The question is about its net effect. …"

> **(2026-08-05, follow-up)** "the satv2 cost=0 bug seems completely separate to this TA work. It pops
> here too but it is unchanged. A separate PR I think. Lets create a separate plan for it later. It is
> small, but not ours. For now focus on our PRs."

> **(earlier)** "there is work on the policy which may have cost entries. … no need to add our own
> mechanism here. … [never-seen accelerator] it does not know its own cost. It is a hack to bypass an
> existing bug. — lets discuss and finalize."

---

## (A) Decided — to fold into the plan

1. **Remove the `fallbackVariantCost` MAX sentinel and the TA-side `lastCost` / `lastAcceleratorName`
   persistence from §7b** (currently plan L613–659, L667–683). Rationale: `Cost` and `AcceleratorName`
   are **(a)-identity fields sourced from saturation** (plan §2 Table 1, L150–151). They are not TA's
   to emit or persist. §7b keeps **`lastPerReplicaSupply` only** — real TA data ("lastPRC is real").

2. **Remove the "ranking-inversion guard" from §7b** (plan L667–683). That guard had TA re-emit a
   non-zero `Cost` so `costEfficiency = Cost/PRC` would not invert to 0. It was TA compensating for a
   saturation bug — which Dean has ruled is not TA's job. It goes away with (1). See (C) for the
   consequence.

3. **Strike the sat_v2 `Cost=0`-for-zero-replica bug from our scope.** It is pre-existing, unchanged
   by our work, and not ours. Origin: `aggregateByVariant` builds its `variantCost` lookup from live
   `inputMetrics` only, so a zero-replica variant gets `Cost = 0.0`
   ([`saturation_v2/analyzer.go` ~L353–373](../../Main/internal/engines/analyzers/saturation_v2/analyzer.go)),
   even though the correct spec cost already exists one call up in `prepareModelData`'s `variantCosts`
   map ([`saturation/engine.go` ~L1490–1520](../../Main/internal/engines/saturation/engine.go)). §7c
   and §12 should record it as "pops here too, unchanged; separate small plan later," **not** as a
   deferral we own. Do not add a fix, a workaround, or a TA-side plug for it.

---

## (B) Proposed — the §2 per-variant (b) fallback refinement

Dean's requirement "sat's PRC must NOT be used under [TA]-only" is, on inspection, a **code change to
the §2 merge**, not merely a verification — because the current merge design *does* pull sat's PRC:

> Plan §2 (L187–203), today: for a variant the binding analyzer (TA) has no entry for,
> "**fall back to sat's own (b) for that variant**."

Under **[TA]-only**, that fallback borrows **sat's PRC** — exactly what Dean says is wrong (demand
comes from TA's per-model-demand metric, so pairing it with sat's PRC is an inconsistent replica-count
computation). With §7b persisting `lastPerReplicaSupply`, a **previously-live-now-zero** variant *does*
get a TA (b) entry, so the fallback never fires for it — TA's real PRC is used, consistent. The
fallback only fires for a **never-seen** variant (no TA history at all).

**Proposed refinement (the planner's recommendation):**

> Sat's (b) PRC is a valid fallback **sizing** source **only when saturation is enabled**. Saturation
> remains the **(a)-identity carrier** in every config, but under [TA]-only it is *not* a (b) source.
> A variant with no TA (b) entry and no persisted TA PRC gets **PRC = 0 → not proactively selectable**;
> genuine cold-starts fall to the existing reactive `scalefromzero` engine.

Consistency across the three configs after the refinement:

| Config | (a) identity source | (b) PRC source | Fallback when binding analyzer misses a variant |
|---|---|---|---|
| `[saturation]`-only | sat | sat | sat's own (b) — valid (sat enabled) |
| `[sat,TA]` | sat | anchor/combine | sat's (b) — valid (sat enabled) → "anchor's PRC" |
| `[TA]`-only | sat | TA | **suppressed** — PRC=0, not selectable; reactive net covers cold-start |

Only behavioral delta introduced: under **[TA]-only**, a never-seen variant that happens to have a
*compatible-sibling* sat estimate stops borrowing that estimate (never-seen with no estimate was PRC=0
either way). The rejected alternative — TA emits a fabricated baseline PRC (old §7b's `PRC=1`) so
never-seen is selectable — is the "hack to bypass an existing bug" Dean flagged, and it trips the
no-hardcoding rule.

**What the reviewer should verify on (B):**
- That the refinement is expressible cleanly in `bindingAnchor` (plan §6, `analyzer_helpers.go`) — i.e.
  the getter knows which analyzers are enabled at merge time and can gate the sat-(b) fallback on it,
  without disturbing the load-bearing ordering rule (fallback runs before the combine-ballot prune,
  plan L197–203).
- That it does not change [sat,TA] or sat-only behavior (goldens / Test 9 must stay green).
- That a Test asserting "under [TA]-only, sat's PRC is not read for a zero-replica variant" (both the
  previously-live path uses `lastPerReplicaSupply`, and the never-seen path yields PRC=0) is
  realizable against real `req`/fixtures.

---

## (C) Known limitation the changes create (needs Dean's acceptance — Q2)

Removing the TA cost guard (A.2) means: under **[TA]-only**, a **previously-live-now-zero** variant
that comes back gets **`Cost = 0` from sat's (a)** (the sat bug in A.3) + a **real PRC from TA** →
`costEfficiency = 0/PRC = 0` ([`cost_aware_optimizer.go` L234–238](../../Main/internal/engines/pipeline/cost_aware_optimizer.go)) →
ranked **cheapest**, picked first on scale-up ([`costGreedyRolePick` L81–105](../../Main/internal/engines/pipeline/cost_aware_optimizer.go)).

Net effect analysis (the "is that the case?" question):
- **Scale-from-zero still works** — the variant *is* selected (in fact more eagerly). §7b's core value
  (proactive return of a previously-live variant) is intact.
- The harm is **cost-suboptimality**, not a functional break: the returning variant can be picked over
  a genuinely cheaper running variant. Two sub-outcomes depending on load:
  - **Flap** — if load then dips enough to create spare, scale-down sheds the most-expensive first
    (now the returned variant, once its real cost is revealed) → back to zero → `Cost=0` again → next
    rise re-picks it. Sustains only while load oscillates across the up/down boundary. No damping
    exists in the cost optimizer to suppress it.
  - **Stuck-suboptimal** — if load stays high enough that the extra replica is genuinely needed, it is
    never shed (`safeRemovalReplicasForRole` returns 0 with no spare) → a *persistent* costlier
    allocation, silent, no self-correction. The quieter and arguably worse of the two.
- Both are the **sat `Cost=0` bug's** effect, resolved when the separate sat_v2 cost fix lands. That
  fix is purely a cost-priority improvement — orthogonal to whether scale-from-zero *functions*.

Proposed disposition: document this in §7c as an accepted known-limitation (resolved by the separate
sat PR), **not** a hard dependency of PR-1.

---

## (D) Resolved — Dean's 2026-08-05 design calls

- **Q1 — APPROVED ("2 refinement is OK").** The §2 refinement in (B) is adopted: sat's (b) PRC is a
  valid fallback source **only when saturation is enabled**. `[sat]`-only is trivial (sat is (a) and
  (b)); `[TA]`-only takes **no sat fallback PRC** (a variant with no TA (b) entry → PRC=0, not
  proactively selectable; reactive `scalefromzero` covers cold-start); `[sat,TA]` **must be
  consistent** — the (demand, PRC) pair comes from a single source, "either anchor or only sat," never
  TA-demand paired with sat-PRC.
- **Q2 — ACCEPTED ("document, don't gate").** The (C) known-limitation is documented in §7c and §12 as
  resolved-by-the-separate-sat-PR; it is **not** a hard dependency of PR-1. Dean's framing: "`[TA]`-only
  now behaves like `[sat]`-only — same limit until the bug is fixed. We fix by fixing the sat cost=0
  bug." The sat `Cost=0` bug itself is out of our scope ("completely separate … not ours").

**Done (2026-08-05):** the planner folded §2 / §3 / §7b / §7c / §10 / §12 / §13 / Test 7 / Test 10 in one
pass, re-ran `toc-refresh.sh`, and (per Dean) commits the plan + this note to the `plans` branch — Dean
notifies the reviewer himself. A clean `sync__` handoff supersedes
`sync__ta-anchor-refactor-v2-scope-expansion.md` (which describes the now-removed sentinel design).

---

## Pointers for the review pass

- Plan sections to re-read after fold-in: §2 (merge + fallback ordering, L187–208), §7b (L590–720),
  §7c (L721–755), §12 (deferrals).
- Code the claims rest on: `costGreedyRolePick` / `costEfficiency`
  ([`cost_aware_optimizer.go` L81–105, L234–238](../../Main/internal/engines/pipeline/cost_aware_optimizer.go)),
  `aggregateByVariant` Cost=0 origin
  ([`saturation_v2/analyzer.go` L340–457](../../Main/internal/engines/analyzers/saturation_v2/analyzer.go)),
  spec-cost already computed for zero-replica variants
  ([`saturation/engine.go` L1490–1520](../../Main/internal/engines/saturation/engine.go)),
  `bindingAnchor`/merge site (plan §6 → `analyzer_helpers.go`), §7b persistence site in
  [`throughput/analyzer.go`](../../Main/internal/engines/analyzers/throughput/analyzer.go).
