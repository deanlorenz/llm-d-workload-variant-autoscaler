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

| A21 | §2e.2 `:1169-1170` | The import-cycle clearance is **false**. *"`internal/config` imports no `internal/engines` package"* ignores `internal/config/config_test.go`, which is **`package config`** and imports `throughput` for the drift guard on the duplicated `throughputAnalyzerName` literal (`config.go:338-341`). So `throughput → config` is a **test-binary** cycle: `go build ./...` stays green, `go test ./internal/config/...` fails. The text points away from its own cause. Replace with the shape now **implemented**: a `KSat()` accessor added to `SaturationScalingConfig` *inside* `internal/config` (+15 lines, uncommitted), so `throughput/analyzer.go` never imports config — verified, its imports are `domain`/`aggregation`/`logging` only. Must also **explicitly rule out deleting the drift guard**: it is §4b-classifiable and presents as a build fix, so nobody would think to classify it | reviewer F48; coder reached option 1 independently before the handoff was read; both verified by me in the dirty diff |
| A22 | throughout §2/§2d/§2f | Tip + status are stale by nine commits: `d9f3b97e` → **`b6bb525c`**, and *"C6c has zero edits, scoped read-only, held on Dean's call"* → C6c **landed** as `34b18bc5` (GPU-space pivot), then C6d `330fcd26`, C6e `784c2b5c`, C6f `a679f2ad`, C11 `b6bb525c`, C10 in flight. Every *"as of `d9f3b97e`"* line-reference label needs re-verification — the drift is actual, not prospective, and C6c–C6f touched exactly those files | PR-1 reviewer Part 2.1 + my verification |
| A23 | §rebase step | Must specify **`git rebase --onto upstream/main 075a208e`**. PR-1 squash-merged, so PR-2's merge-base is `aadaa596` (pre-PR-1) and a bare `git rebase upstream/main` sees all of PR-1 as added on both sides: **10 conflicts**, incl. `add/add` on `optimizer_combine_characterization_test.go` + `optimizer_scale_from_zero_test.go`. True surface is **2**: `analyzer_helpers.go` (PR-2's new comment vs `main`'s `buildCapacityMap` swap — take both) and `rescale.go` (**duplicate** `if anchor == nil` guard, arrived at independently). Preferred `rescale.go` resolution: take **`main`'s**, which is §4a-clean, so resolving the conflict removes a violation. Also record that local `ta-anchor-refactor-v2@075a208e` is **not** what merged — `a38d7b73`'s four fixes exist only on `origin/` and in `main` | PR-1 reviewer Part 4, measured via `git merge-tree` |
| A24 | §4 / §4a — supersedes A9/A10 | **11 of 17** commit messages carry a token (heading to ~14), in-tree count `1 → 22 → 36` across C6c–C6f. Critically, the plan's *"17 already inherited at `075a208e`, out of scope"* is **1** under a tighter grep: the plan's expression also catches **legitimate code identifiers** — golden-scenario names `A1`–`A4`/`C1`/`V1` and the `T1-ols` reason string — which must not be renamed. The two figures were never comparable and more of the debt is PR-2's own than credited. **Pin one grep expression in the plan before re-quoting any count** | PR-1 reviewer Part 5 |
| A25 | §2f | Steer C11's `Reason` constant spelling away from `a38d7b73`'s new `variant.ReasonOptimizationRefused` / `constants.K8SEventOptimizationRefused` family — different namespace, no technical collision, but two "Reason" families now coexist in-tree and §2f leaves the spelling to the coder. Optionally cite `a38d7b73`'s own `allPicked`-clears-and-breaks explanation as **independent corroboration** in merged code of §2f's ⚠ skip-not-zero-cap requirement | PR-1 reviewer Part 4.3 |
| A26 | §2f `(D-a)` | Population scope is wrong and the fix is free. **Three** populations reach the binder-miss branch, not one: **lapsed** (ran, scaled to zero, TA state deleted after `2*DefaultObservationMaxAge` — TA's own comment concedes *"degrades to the never-seen case"*), **cold-but-priceable** (sibling/deployment estimate), **cold** (`satReasonNoData`). Saturation tiers 1–2 return stored `EffectiveCapacity` *authoritatively* when `LearnedFrom == learnedFromLive`, so a **measured** PRC often exists for exactly that variant. The discriminator is already at the write site — the identity carrier is located **by name with no `Enabled`/`Live` check**, so `a.Reason` is readable in every configuration — and the merge **discards** it (`out.Reason` assigned only inside the `bByName` hit branch). Keep the two narrowings **visibly distinct**: *"admit only when saturation votes"* is dead by reachability (sat's voting predicate is its binding predicate); *"admit only when the carrier has no record"* survives. Splits `(D-a)` into population scope and a separate `N8`/`VG-up` question about sizing from a stale carrier — deferring `(D-a)` does **not** dispose of the latter | designer §1/§2, endorsing + refining review F44 |

| A27 | §verification `:2033-2040` | The C6c gate **fails by design and will trip C9**. It requires that after `grep -rn "ceil(" internal/engines/pipeline/`, *"`fairShareCap`'s must be **gone**, replaced by the whole-replica `floor` fill"* — but `fairShareCap` no longer exists under that name (it is `replicasToCover`) and the tree ships `ceil` there deliberately, with a written rationale. Re-express against the new name whichever way the rounding question is decided. **Note what survives intact:** the gate's own one-sentence rule at `:2039-2040` — *"round up when asking how many replicas a demand needs, round down when asking how many replicas a budget can afford"* — is exactly the two-directional policy the code implements at `:697-700`. So the gate is not wrong in principle, only in its `fairShareCap` clause and its name | designer §1.3, verified |
| A28 | §4a — **corrects B3, does not close it** | Review Finding 33's four cited lines **are** fixed (`4fb49ac6`, *"drop plans-branch paths from shipped comments"*), and a `plan__|review__|sync__` grep across `internal/` is clean at tip. But the designer's conclusion *"Finding 33 is CLOSED — do not route it"* rests on that narrow expression. A broader one finds **two surviving violations, both PR-2's own** (absent at base `075a208e` **and** on `upstream/main`): `analyzer_helpers.go:642` cites **`combined-analyzer-optimizer-design.md § invariants #7`** — a direct plans-branch document reference, the exact class §4a names — added by `8eb6ee2d`/`b106b929`; and `analyzer_helpers.go:88` reads *"Type-1 owner's, not this file's"*, a taxonomy/role token, added by **`b6bb525c`** — the current tip, i.e. **after** the cleanup commit. So the in-tree burden is **not** monotonically self-correcting as claimed; C11 re-added one. This is the fourth mutually-inconsistent §4a count from three sessions, and all four expressions missed both of these lines — which is the argument for A24's "pin one expression" being a plan step, not a preference. (Separately: `internal/collector/locator/locator.go:4` cites `docs/superpowers/specs/…-design.md` — **inherited**, not PR-2's; belongs to the `main`-side backlog in `governance-follow-ups.md`) | my grep + provenance check; supersedes the designer's §3 closure |

## B. Conditional — each waits on one decision

| # | Depends on | Change |
|---|---|---|
| B1 | **(vi) claim pricing** | Land the chosen disposition: accept-and-document / headroom partial / **option (d)** (`min(gpusPR / PRC)` over feasible candidates). If (d): record that its neutrality is **contingent** (via `ceil` + a binding bottleneck), *not* structural — golden scenario A has equal `GPUsPerReplica`, unequal PRC, and the reference **flips** `cheap → expensive`, halving the claim `0.5 → 0.25` GPUs. Also record that (d) changes the **ranking key** for any unequal-PRC role, which no golden covers |
| B2 | **(vii) Finding 28** | Add a discriminating spec for `fairShareRolePick`'s per-role budget. Reviewer's table: clamp-only passes **both** shipped specs, so `committed0`, `reserved`, the per-draw holdback and `firstDraw` are pinned by nothing. §C6e asked for "roles that would each individually fit but jointly overrun"; the shipped fixture has both roles individually exceeding `target`, which is what lets clamp-only pass. Technique already established by `34b18bc5` (call the returned pick closure directly). This is **Finding 20's shape recurring** |
| B3 | **(viii) Finding 33** | A step naming the four shipped §4a defects — `greedy_score_optimizer_test.go:1602-1603` (handoff **path**), `:1741-1743` (three handoff filenames, one written today), `:1604` ("open with the Type-1 owner" — a mis-routing I introduced, now in code), `:1736` (`784c2b5c`, a pre-rebase SHA). My recommendation: **not** C9 — the handoff refs are `.DONE`+`git rm`-ed before the PR merges, so they are dead on arrival |
| B4 | **(ii) C6e item 2** | If fixed: a **C6g** row in §0 between C6f and C11, and the git-order line updated. Rationale for a separate commit: it is entitlement accounting, not sentinel ranking, and C11 is already a behavior-change commit whose golden attribution should not absorb a second change |
| B5 | **(i) C6c fork** | Whichever of (a) restore `ceil` / (b) defer-not-evict / (c) `max(1, floor(x))` is chosen, applied as a **three-site** policy per A16 — not a single-expression edit |

| B6 | **(xii) Finding 47** | If the `fillRole` fixture is owed to C11 rather than to a `(D-a)` follow-up: a §C11 test row for it (~15 lines, `spent == 1` vs `spent == 10` pre-clamp). Not covered by the four shipped `maxTargetReplicas` unit specs, and `fillRole` is the only one of the three clamped sites that a tagged variant reaches **and** that has no test — `fairShareRolePick` is unreachable for a tagged variant (empty `AcceleratorName` fails the `available[...]` gate) |
| B8 | **(xiv) `replicasToCover` Σ-overshoot** | The `ceil` ships with a **known, coder-acknowledged consequence recorded only in a test comment**: `greedy_score_optimizer_test.go:1428-1430` — *"without that, Σ_role spend exceeds target by the round-up, which is the **deferred `replicasToCover` item** and not this one"* — and the C6e fixture is built from whole multiples specifically so it cannot trigger. Whatever Dean decides on the rounding, this deferral needs a **plan home and a §4b classification**; right now it exists nowhere but a comment inside a test that is designed not to exercise it. Independently of the rounding decision, this row should land |
| B7 | **(i) restated — T1-1 / AM-1** | The fork is **already resolved in-tree as (a)**: `replicasToCover:833-838` ships `ceil` with a written rationale at `:824-832`, and there is no `math.Floor` in non-test `greedy_score_optimizer.go`. So the row is no longer "apply one of three" but a **doc-vs-code divergence**: frozen Type 1 `:1159-1160` mandates `floor`, the tree ships `ceil`. Exactly one must move, and if the Type 1 moves this row becomes a no-op |

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
  **Reviewer Finding 44 makes the failure the whole reachable domain, not a point in it** (verified at
  `b6bb525c`): `aCarrier := binding; if satNR != nil { aCarrier = satNR }` (`:237-240`) plus `:211-213`
  means that when saturation binds, `binding == satNR == aCarrier` is **one pointer**, so `bByName`
  (`:260-263`) is built from the identical slice the merge iterates (`:265`) and the no-variant `else`
  is unreachable; `:230-232` returns nil when nothing qualifies. The write site is therefore reachable
  **only** with saturation present-but-not-binding and another analyzer binding-and-omitting — and in
  that state all three sub-cases are unsizable: sat `!Enabled` and sat `Enabled && !Live` never enter
  the `Enabled && Live` voting set (`:318`), while sat `Enabled && Live && !Informative` *does* vote but
  carries only NoData/Error rows at PRC 0, so the ballot-side `prc <= 0` gate skips it. `(D-a)` as
  written **cannot scale a variant from zero in any configuration.** Two consequences: (a) there is no
  *"only admit when saturation votes"* narrowing — the natural thing to reach for — because when
  saturation votes it also binds and the branch is unreachable, so that version is a feature that never
  fires and the amendment should say so; (b) **option 2 is out**, not merely weakest: in sub-case 3
  saturation *is* in the voting set pricing nothing usable, so a floor would grant a replica on the
  strength of a no-data ballot, contradicting the abstain-as-a-pricing-rule invariant. **The fork
  therefore collapses from a mechanism question to a scope question:** option 1 is the only mechanism
  that works (same state, one currency, cost = a synthetic value entering the vote — the `N8` question
  proper), and option 3 is "not in PR-2". Reviewer declines to choose between 1 and 3; my
  recommendation stays **(3)**.
- **Shipped production-prose defect, same amendment.** `analyzer_helpers.go:185-188`'s premise is false
  (`ResultIsInformative` is any-variant per `:57-62`, so a healthy binder can be informative in
  aggregate yet price nothing for one variant — the expected shape for a never-measured from-zero
  variant), *and* the sentence is incoherent about its subject: "a binder omits a variant only when the
  binder itself is … not-binding". Conclusion holds; re-justify on `:189-192`. Note this is **new PR-2
  prose**, which per A10 is the first production `.go` doc comment surface this mission touches.
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
