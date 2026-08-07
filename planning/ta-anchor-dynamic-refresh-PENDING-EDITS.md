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
| A6 | `:288` | Cap placement: the one-replica ceiling must sit at the **granting site**, never in the `MaxReplicas` headroom branch. Widened from one site to **three**, all verified at `eb12089a`: `cost_aware_optimizer.go:104-111` (the `return …, math.MaxInt` at `:111` is *outside* the `MaxReplicas != nil` block); `greedy_score_optimizer.go:711-717` (clamp wholly inside the nil-guard); `rescale.go:454-460` (worst — a `for wantGPUs-spent >= g` loop whose **only** exit is a `break` guarded by `MaxReplicas != nil && > 0`, so an unset ceiling means replicas are granted until the GPU budget is exhausted). `MaxReplicas` is `*int` and nil/`0` are treated alike as unbounded, and the sentinel's population is never-seen zero-replica variants — the least likely to be tuned | my verification, then reviewer F42 independently at all 3 sites |
| A20 | A1–A5 addendum | The ranking inversion's **fix is `N5`, not a different sentinel value**: a never-measured variant's `Cost` arrives as `0` from the *same* zero-replica lookup that leaves `AcceleratorName` empty, so the ratio is `0/1` and it sorts first. `PRC = 1` stays the right choice and the property recovers with **no change to C11** once that lookup is fixed. Ties A1–A5 to the `N5` item currently listed as out-of-scope | coder, C11 impl |
| A19 | §C11 | Record the **post-freeze ordering dependency**: C6e's `firstDraw` floor at `greedy_score_optimizer.go:702` *raises* `capN` after `replicasToCover` at `:701` and before both bounds (`:710` pool, `:711-717` headroom). A ceiling placed next to `replicasToCover` — the natural reading of the Type-1 instruction — is therefore overwritten on the first draw. Single-role case is benign (`:702` raises to exactly 1 = the ceiling); the breach needs two roles resolving to the same sentinel variant in one pre-commit window, which **neither the reviewer nor I have established as reachable**. This is why the clamp shape is `min(cap, 1 - targets[v])` and not `min(cap, 1)` | reviewer F43 + my verification |
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
- **Post-freeze Type-1 `(D-b)` amendment — the third such item, and the only one that is a *text
  defect* rather than a rationale touch.** `(D-b)` says to fold the one-replica ceiling into the
  per-site `headroom` computation "including its `headroom <= 0 → continue`" / "same clamp, same
  skip" / "add the ceiling to that same `break` condition". Followed literally that nests the
  ceiling inside a nil-guard at all three grant sites (A6), so the ceiling does not exist on an
  untuned variant — which is the sentinel's whole population. Correct shape is an **unconditional
  sibling** clamp, `cap = min(cap, 1 - targets[v])`, with its own `continue`/`break`, placed after
  the pool bound (A19). **Needed whichever way the C11 diff goes.** I am not amending it: Dean
  divided scope so the plan reviewer handles Type 1 and I own the derived Type 3 only, and
  post-freeze Type-1 changes go through Dean. The handoff routes the amendment to me as "Type-1
  owner" — a label the same reviewer declined for himself — so this is a genuine routing conflict
  for Dean to settle, not something to resolve by guessing.
- **`(D-a)` cannot ship as written — a Type-1 *design* defect, the fourth post-freeze item, and the
  only one that is a regression rather than a text or rationale problem.** The sentinel is written onto
  the **anchor**, and the six `PRC <= 0` gates it clears are all selection-side. Sizing is not
  selection-side: `roleBottleneckReplicas:607-616` reads the **ballot** via
  `votesFromPickerState:511-518`, which calls `prcForVariant(e.Result, …)` — the entry's own Result,
  never the anchor — and abstains on `<= 0`. Every voter abstains ⇒ `binder < 0` ⇒ bottleneck `0` ⇒
  `min(0, cap) = 0` ⇒ `deltaUtil = 0` ⇒ the model's loop breaks, taking down **every variant behind the
  admitted one**. Verified by the coder's mutation on a `[sat-not-live] + [TA]` fixture: with the
  sentinel written the *measured* variant stays at 2; with it disabled it scales past 2. The admitted
  variant gains nothing and a working variant loses its scale-up. It is the same `cap = 0` hazard
  `(D-b)`'s own ⚠ describes, arriving through the bottleneck, where the ceiling is structurally
  powerless. Corroboration: Test 10's `revived` scales *because* TA emits a PRC-only row into its own
  ballot entry; `cold` (never seen) stays 0 — sizing has always come from the ballot, and `(D-a)` is
  the only proposed admission that writes the anchor alone. **Coder held it; the tree ships `(D-b)`
  only, gates green, no golden moved.** Three-way fork, explicitly Dean's: (1) binder emits the
  sentinel into its own ballot entry — closest to `revived`, one currency, but makes a synthetic value
  a *vote*, colliding with `N8`; (2) `roleBottleneckReplicas` floors at 1 for a tagged variant —
  localised, but invents a bottleneck that ignores its voters, contradicting the abstain-not-veto
  semantics stated at `:512-517`, and needs its own gate audit; (3) narrow C11 to `(D-b)` and route
  admission to `N5` — which A20 shows the ranking correction **already** depends on. My recommendation
  is **(3)**, and by decision rather than by default: it is the only branch that preserves current
  behavior, and it lands admission and ranking together on one real fix instead of a synthetic value.
  Needs a **DEFERRED** classification with design intent, not a silent narrowing.
- Routing: who owns post-freeze Type-1. The internal code reviewer has declined the "Type-1 owner"
  label I used in two handoffs; that error is also now in shipped code (see B3).

## Provenance

Handoffs feeding this batch, all read at their stated states:
`plan__ta-anchor-c6e-two-adjacent-defects.md.WIP`, `plan__ta-anchor-c6f-w4-no-spend-is-false.md.WIP`,
`plan__ta-anchor-claim-pricing-verdict-and-c6e-gap.md.WIP`,
`plan__ta-anchor-c11-ceiling-nil-maxreplicas-escape.md.WIP` (Findings 42/43, pre-registered at
`470f4b8d` *before* the C11 diff existed); reviewer write-up
`planning/ta-anchor-dynamic-refresh-review.md` @ `ded9dc5f`. Branch tip when the A19/A6-widening rows
were added: `eb12089a`, with **six** source files modified and uncommitted (C11 in flight, touching
all three grant sites).
