last_update: 2026-08-08
state: in-progress
current_step: Addendum 1 at Rev 7 (43f20c65) — Finding 75 folded in, evidence-only. Monitoring until PR-2 lands. One question open for Dean (placement).
blocked_on: —

## Role — read this first on a cold resume

**`designer`.** Not a coder, not the planner, not the reviewer, not sync.

| | |
|---|---|
| **Owns (may edit)** | `planning/combined-analyzer-optimizer-design-addendum-1.md` · `planning/multi-analyzer-dataflow-map.md` §9 (only §9; §0–§8 are Dean-annotated and untouched) · own handoffs under `session/handoffs/` · this status file |
| **Owns but FROZEN — do not edit at all** | `planning/combined-analyzer-optimizer-design.md` — Type 1, **Status: FINAL, frozen 2026-08-07 @ `8c2a9b04`**. It governs the Type 3 on disagreement. Amendments go in Addendum 1, never in the parent. |
| **Must never write** | code · `planning/*-review.md` (review-agent domain) · `session/CURRENT.md` and shared `session/` state (sync is the only writer) · `planning/ta-anchor-dynamic-refresh-plan.md` (planner's Type 3) |
| **Reviews** | Type-3 work, reviewer findings, coder handoffs — by *handoff*, never by editing their docs |

Other roles in play: `planner` (Type-3 owner) · `review` (PR-2 internal reviewer, source of Findings 66–74) ·
`coder` on branch `ta-anchor-dynamic-refresh` · `sync` (sole CURRENT.md writer).

## Where the work stands

**Addendum 1 is at Rev 6, committed `423eb2a8`, and APPROVED by Dean 2026-08-08.** It is consumable.
Handed off in `a675602b` / `29e3dae1`:

- `session/handoffs/plan__ta-anchor-ad8-addendum-1-approved-rev6-final.md` — planner, full content.
  **Supersedes the entire `.DONE` AD5/AD8 handoff trail** (≈25 files), several of which carry withdrawn
  premises. On a cold resume, read the addendum, **not** the handoff trail.
- `ta-anchor-dynamic-refresh__type1-addendum-1-rev6.md` — coder, refs-only doorbell.
- `review__type1-addendum-1-rev6.md` — reviewer, refs-only doorbell.

All 11 inbound `designer__*` handoffs are `.DONE`.

## Dean's decisions — final, do not relitigate

- **Guard (his own):** on a **disaggregated model with TA and no saturation**, do nothing. *Enforces* `AD2`.
- **Option (a), liveness-aware refusal — REJECTED.** *"PD not SAT — DONT."* The rule stays keyed on the
  **enabled** set; no second refusal predicate.
- **Option (b), the per-role pricing repair — APPROVED.** Three sites: per-role sizing; `CapGPUs`/`Demand`
  in `rescaleInputsForGroup:540-546`; `cost_aware_optimizer.go:350-367` observability.
- **Option (c), interim documentation — additive, not alternative.**
- **`MinReplicas` is not a fourth option** — unset by default, fails correlated with the defect, cannot reach
  regime (i) at all, and any variant with `minReplicas > 0` makes `applyScaleToZeroEnforcement` skip the
  enforcer **model-wide** (`saturation/engine.go:1362`).
- **`ceil`/`floor` — "we discuss later."** Out of scope. Do not open it.
- **Document housekeeping — deferred until PR-2 is done, and NOT to be re-raised.** He said so more than
  three times, the last time emphatically. Recorded for later; raising it again is the error.
- **Sequencing:** *"we do not correct until coder lands. Only handoffs until then."* No corrective edits to
  anyone else's live docs while PR-2 is in flight.

## Rev 6/7 — the substantive result, and why severity moved

Rev 6 withdrew this author's Rev 5 claim that the `[sat, TA]`-with-saturation-non-live cell is reachable.
It is **closed** — Dean approved Rev 6, and the reviewer's Finding 75 then independently confirmed the
closure by counter-example search (four candidate single-fault stories, all four fail). **The closure
stands, twice over.**

**But Rev 6's argument was wrong, and Rev 7 (`43f20c65`) replaced it.** Rev 6 argued a **retention
asymmetry** — saturation's capacity records kept 7 days, TA's persisted supply expiring in 1 hour. That
table is now **withdrawn** (`§ withdrawn` item 9) — do not cite "7 days vs 1 hour" or "168×" again; the
eviction code that would make those numbers matter (`EvictStale`, `EvictStaleHistory`) has **zero callers
tree-wide**, so the constants describe dead code, not the actual mechanism.

**The replacement needs no time constant at all — it's same-event, not retention.** Processing a usable
replica-metric row is the only way TA ends up with a positive `lastPerReplicaSupply` for a variant — and
processing that same row writes saturation a `learnedFromLive` capacity record keyed on the same
`rm.VariantName`, in the same key space, on the same cycle (`saturation_v2/analyzer.go:198-207`), which
`capacity_store.go:98-101` protects from being overwritten by a weaker source. ⇒ **TA warm ⟹ sat warm**,
instantaneously, per variant — containment, not a race. Saturation is warm over a **strictly broader**
set besides, because its store is *also* pre-populated from scale-target objects on step 1 of every cycle
(`saturation/engine_v2.go:38-53`), reaching variants with no metric rows at all.

**Rev 6's own residual is retired too** ("a fresh process where every scale-target fetch fails") — two
closures Rev 6 didn't cite kill it (`saturation/engine.go:1506` before `:1520`/`:1523`; `:1540-1545`
before `:1547`): that state is **no model on the ballot**, not an all-`NoData` model with TA as the sole
voter.

**One new residual survives, recorded as a band, not a closure:** on the last cycle with rows,
`min(k1, k2) ≤ 0` (`saturation_v2/analyzer.go:185-188`) for every variant while TA computed a positive
`perReplicaSupply` from those same rows, and `lookupCompatibleCapacity` missed for all of them. A `k1`/`k2`
arithmetic question, not a liveness one — needs a k1/k2 fixture if anyone ever probes it. **No ruling,
severity, or disposition depends on which way it goes.**

**Unmoved by any of this:** `[TA]`-only (needs no saturation death at all — the guard's case, and the
reachable configuration) · the two regimes measured at HEAD (fixtures build the ballot directly, bypassing
both memories) · the arithmetic · Dean's decision to repair the pricing.
**Moved:** severity dropped once, at Rev 6 (because Dean set it on Rev 5's premise) — **Rev 7 moves
nothing further**; it only repairs the evidence under an already-settled conclusion.

**The seam survives but is latent, not live:** informativeness reads per-variant `Reason`, while the RC
reaching the optimizer comes from `RoleCapacities`, and `applyUniversalThreshold`
(`saturation/engine_v2.go:476-513`) never mentions `VariantCapacities` — two predicates nothing relates.
Aligning them is a **Type-1 design question for a later round**, not PR-2 work, and **not** a revival of
rejected option (a) (different site).

## The defect's shape — two regimes, two backlog rows

`AD8` is two regimes from one cause; dispatch is a global OR (`analyzer_helpers.go:709-718`) with mutually
exclusive arms (`cost_aware_optimizer.go:62-67`). They must reach the Type-3 or backlog **separately** —
a fix verified on one says nothing about the other.

- **(i) freeze** — decode `RC > 0` ⇒ scale-up arm ⇒ prefill **freezes at its current count, including 0**.
  **No floor of any kind**; `MinReplicas` cannot reach it.
- **(ii) drain** — decode `RC == 0` ⇒ scale-down arm ⇒ prefill **drains to 1**.

**Sequencing precondition, regime (ii) only** (everything it protects lives in `scaleDownVariantSet`, which
regime (i) never enters): if #1237's positional rule is ever tidied, **floor every variant in the role
first** — tidy-first re-opens this at every height on both scale-down paths (measured, prefill → 0).

## Premises that are withdrawn — do not carry them forward

- **Item 6** — the drain as *"newly unmasked by `VG-up`"*. Base was already `Live`-gated and already read
  prefill `TotalDemand = 0` (`075a208e:rescale.go:545`); reviewer conceded (Finding 67). The surviving,
  narrower claim: route (A) *is* HEAD-reachable when the pruned entry carries a positive `RC` (arm-2 run).
- **Item 7** — "reachable by the most ordinary path there is (a cold start)."
- **Item 8** — "reachable by cold start or sustained metrics gap." See Rev 6 above.
- **Review finding V6's (b)-fallback domain** — inverted; superseded by `N1`.

Label reconciliation, so nobody talks past anyone: planner's `A68`/`B15` **(i)** = `MinReplicas` floor,
**(ii)** = pricing repair. Addendum letters **(a)** rejected / **(b)** approved / **(c)** docs.
**Planner-(ii) ≡ addendum-(b).** Planner-(i) is not one of the addendum's three.

## Open — needs Dean

1. **Placement.** Severity dropped, so whether the pricing repair belongs **in PR-2** is now a live
   question. The planner was asked to bring it to him, and told **not** to schedule it on the old severity
   and **not** to retire it either. This is the one open ask.

## Deferred until the coder lands (per Dean's "only handoffs until then")

- the `ceil` amendment (he deferred the discussion itself)
- `multi-analyzer-dataflow-map.md` §9 Case 5 — backstop sentence
- the one-tier `G2` row
- the dropped `[TA]`-only caveat
- a liveness verdict alongside the consistency verdict
- Type 1 `:1524-1526` — the `(D-a)` justification
- the `N2`/`N7` Disposition sweep
- `T1-1`'s `:1159-1160` divergence

## Flagged for sync, not mine to edit

- CURRENT.md records PR-2's tip as `d9f3b97e`; the branch is actually at **`a9afb740`**.

## Notes

- Monitor task `bwoa37euh` watches inbound handoffs for in-domain PR-2 events; one line per event, surface
  only what is in this role's domain. Self-authored `.DONE` renames echo back as events — ignore those.
- Evidence discipline in force (Dean: *"you need to verify every claim"*, and separately *"we are deep into
  coding PR-2, yet you rely on Main?"*): every claim in the addendum is cited against **PR-2 HEAD**, not
  `main`. If a cold resume needs to re-verify, use read-only
  `git -C ../ta-anchor-dynamic-refresh show <rev>:<path>` — **never** a git write-verb in a sibling worktree,
  and never `cd` into one.
- Counter-lesson from Rev 6, worth keeping: *an asymmetry between two stores is a claim about both of them,
  and its existence does not imply its direction.* Rev 5 read one side and assumed the sign. Two reads.
- Dean's process correction, same session: *"I did not understand why are you reading the code yet again.
  We have analyzed this again and again."* Re-reading settled ground is a cost, not diligence.
