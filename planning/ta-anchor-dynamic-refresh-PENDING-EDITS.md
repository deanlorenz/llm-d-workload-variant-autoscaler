# PENDING Type-3 edits — NOT APPLIED, NOT A SPEC

> ⚠️ **This is not a plan document and carries no authority.** It is the planner's manifest of edits
> *proposed* to `ta-anchor-dynamic-refresh-plan.md` and awaiting Dean's single approval. Nothing here
> has been applied to any plan, and no coder should read scope from it — the authoritative Type 3 is
> [`ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) @ `1a116e7a`, and the Type 1
> [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (FINAL, frozen
> @ `8c2a9b04`) governs it on disagreement. Delete this file once the batch lands.

**Why it exists:** the batch grew 17 → ~23 sites across a long session that has compacted twice.
Recording it protects against exactly the silent content loss CONVENTIONS warns about, and lets Dean
review the batch as a list rather than as prose spread over many turns.

**Target file for every row unless stated:** `planning/ta-anchor-dynamic-refresh-plan.md`.
`scripts/toc-refresh.sh` runs **last**, after all rows are applied.

---

## A. Unconditional — apply on batch approval

| # | Site | Change | Origin |
|---|---|---|---|
| A1 | `:288` | C11 ranking claim is **inverted**: `Cost = 0` ⇒ the sentinel sorts **first**, not last | my verification |
| A2 | `:1315-1316` | same inversion | " |
| A3 | `:1324` | same inversion | " |
| A4 | `:1608-1612` | same inversion | " |
| A5 | `:2199-2200` | same inversion | " |
| A6 | `:288` | Cap placement: the one-replica ceiling must sit at the **granting site**, never in the `MaxReplicas` headroom branch — `cost_aware_optimizer.go:106` returns `math.MaxInt` when `MaxReplicas == nil`, so a cap placed there is a no-op | my verification |
| A7 | §C6c items 2/3/4 | corrections carried from the currency-pivot read | my verification |
| A8 | §C6d items 1/1b/2 | ditto | " |
| A9 | §4 | Commit-message reword cost is **13**, not nine or ten: 14 commits, 13 token-bearing, 10 token-bearing subjects, `34b18bc5` the only clean one. Supersedes the "9 now vs 16 later" framing | reviewer F-recount |
| A10 | §4a | Code/doc token locations ~**49**, not 32. New load-bearing fact: production `.go` doc comments went **0 → 19** at base `075a208e`, so **PR-2 is the first to reach production prose** (PR-1 leaked into test comments only) | reviewer F-recount |
| A11 | `:1630-1632` | The C6e golden rule ("goldens are expected to move, incl. `[sat]`-only P/D") is **structurally impossible** — with one active model `allocationMean = 0` so `target == claim`, and `claimGPUs` sums role claims, so the entitlement equals combined spend exactly. Sharper replacement: **no single-model golden *can* move**; the entitlement bug needs multi-model contention | coder + reviewer, independently; reviewer retracted his own contrary pre-registration |
| A12 | `:284` | "the pool was enforced, the fair share was not" is **half true** — in `allocateForModelPaired` the pre-C6e code drove the pool to **−5** on a 7-GPU pool, so the pool was not enforced there either | coder item 0 counterfactual |
| A13 | `:1555` | same correction | " |
| A14 | `:1753` | same correction | " |
| A15 | new §-entry | **DEFERRED** classification for the pool double-count (`analyzer_helpers.go:846-857`: `pick()` runs per role against the same un-decremented `available`; decrement only at the commit loop `:903`). Needs: what it did, why deferred, both candidate fix shapes (speculative decrement + rollback vs shrinking copy reconciled at commit). **Live, not latent**, in the pool-bound case | my correction of the coder's framing |
| A16 | §-note | The indivisible-unit floor now exists at **three** landed sites, each citing the others: `greedy_score_optimizer.go:458-460` (`bound = prc`), `:694` (`firstDraw && capN < 1`), `:822` (`math.Ceil` in `replicasToCover`). Any "floor everywhere" mandate applied literally now means reverting three sites, not one expression | my verification |
| A17 | §C9 | **Finding 29** — the new "Fair-share iteration" paragraph says the single-model case "gets `mean == 0`". It is **`allocationMean`** that is zeroed (`:292-297`); `mean` equals that model's own remaining and still governs the `w.remaining > mean` drop check at `:308`. As written it reads as the inverse | reviewer F29 |
| A18 | §C6f or §C11 | Give the unplanned dormant spec `537b0153` (test-only, +88, `PIt`, asserts the honest even split) a **§-home**, or an explicit "unplanned — revert if the claim-pricing disposition rejects it" note. It currently says in its own first line that it is not in the plan | reviewer, endorsing it |

## B. Conditional — each waits on one decision

| # | Depends on | Change |
|---|---|---|
| B1 | **(vi) claim pricing** | Land the chosen disposition: accept-and-document / headroom partial / **option (d)** (`min(gpusPR / PRC)` over feasible candidates). If (d): record that its neutrality is **contingent** (via `ceil` + a binding bottleneck), *not* structural — golden scenario A has equal `GPUsPerReplica`, unequal PRC, and the reference **flips** `cheap → expensive`, halving the claim `0.5 → 0.25` GPUs. Also record that (d) changes the **ranking key** for any unequal-PRC role, which no golden covers |
| B2 | **(vii) Finding 28** | Add a discriminating spec for `fairShareRolePick`'s per-role budget. Reviewer's table: clamp-only passes **both** shipped specs, so `committed0`, `reserved`, the per-draw holdback and `firstDraw` are pinned by nothing. §C6e asked for "roles that would each individually fit but jointly overrun"; the shipped fixture has both roles individually exceeding `target`, which is what lets clamp-only pass. Technique already established by `34b18bc5` (call the returned pick closure directly). This is **Finding 20's shape recurring** |
| B3 | **(viii) Finding 33** | A step naming the four shipped §4a defects — `greedy_score_optimizer_test.go:1602-1603` (handoff **path**), `:1741-1743` (three handoff filenames, one written today), `:1604` ("open with the Type-1 owner" — a mis-routing I introduced, now in code), `:1736` (`784c2b5c`, a pre-rebase SHA). My recommendation: **not** C9 — the handoff refs are `.DONE`+`git rm`-ed before the PR merges, so they are dead on arrival |
| B4 | **(ii) C6e item 2** | If fixed: a **C6g** row in §0 between C6f and C11, and the git-order line updated. Rationale for a separate commit: it is entitlement accounting, not sentinel ranking, and C11 is already a behavior-change commit whose golden attribution should not absorb a second change |
| B5 | **(i) C6c fork** | Whichever of (a) restore `ceil` / (b) defer-not-evict / (c) `max(1, floor(x))` is chosen, applied as a **three-site** policy per A16 — not a single-expression edit |

## C. Not in this batch — other owners

- `sync__` handoff carrying the A9/A10 recount into CURRENT.md (supersedes "all nine (6/9 subjects,
  8/9 bodies)" and "32 code/doc locations"). Blocked on the (vi)/reword-window rulings; I cannot edit
  CURRENT.md.
- Post-freeze Type-1 rationale touches: the claim-pricing rationale at `referenceVariantForRole:829-838`
  and **Finding 27**'s `:1530-1533`. The reviewer recommends deciding them **together**. Dean's, not mine.
- Routing: who owns post-freeze Type-1. The internal code reviewer has declined the "Type-1 owner"
  label I used in two handoffs; that error is also now in shipped code (see B3).

## Provenance

Handoffs feeding this batch, all read at their stated states:
`plan__ta-anchor-c6e-two-adjacent-defects.md.WIP`, `plan__ta-anchor-c6f-w4-no-spend-is-false.md.WIP`,
`plan__ta-anchor-claim-pricing-verdict-and-c6e-gap.md.WIP`; reviewer write-up
`planning/ta-anchor-dynamic-refresh-review.md` @ `ded9dc5f`. Branch tip at time of writing: `537b0153`.
