from: review (ta-anchor-dynamic-refresh internal reviewer)
to: planner
session: type-1 verdicts — fairShareCap rounding, row-7 contradiction

Answering the two `review__ta-anchor-type1-*` handoffs. Both are now `.DONE`. Full reasoning is in
`planning/ta-anchor-dynamic-refresh-review.md` § *Type-1 adjudications routed to me*; this is the
verdict summary.

**Scope.** A Type 1 is not in my write scope (role table: reviewer writes Type 6 + handoffs; Type 1 is
a read for every role). I own the verdict, not the amendment. I have not touched
`combined-analyzer-optimizer-design.md`. Dean's instruction reached me second-hand inside a trigger,
which does not move that boundary — the amendment needs whoever owns the frozen doc.

## 1. `fairShareCap` ceil vs floor (my Finding 22) — the frozen mandate is defective; amend it

Your non-termination proof is **correct and independently verified**. `fairShareScaleUp` is a bare
`for {}` (`greedy_score_optimizer.go:210`), exits only on `len(active) == 0` or `totalGPUs == 0`. Under
the coder's option (b), a sub-one-replica entitlement grants nothing → `allocated` false → the
`w.remaining = -1` eviction is skipped → `totalGPUs` never moves → spins forever. With one such model
active, `mean == remaining` so the `:255` reset does not fire, and `len(active) == 1` forces
`allocationMean = 0` so `target = remaining > 0` re-enters the same path. Option (b) needs a new
termination invariant; it is not a drop-in.

**Third option neither you nor the coder named, and my first recommendation:**

    fairShareCap = max( 1, floor( remaining_GPUs / GPUsPerReplica[vc] ) )
    capN         = min( fairShareCap, gpusAvail / GPUsPerReplica[vc] )

- 0.4 replicas → 1 (today 1; frozen T1 **0 = evicts**)
- 2.4 replicas → **2** (today 3 = the over-grant the T1 wanted gone; frozen T1 2)
- 3.0 replicas → 3 (unchanged)

It honors the Type 1's stated intent ("a partial replica is not affordable") while removing both the
eviction and the non-termination hazard: a grant of ≥ 1 always happens when the pool allows, so the
loop progresses. Termination is preserved exactly as today — the picker still returns `("", 0)` when
every variant is unpriceable / pool-starved / at `MaxReplicas` headroom, which still reaches
`remaining = -1`. The pool stays enforced by the unchanged `min`.

**Verdict.** `:1159-1160` as written is defective — not because `floor` is the wrong rounding, but
because `floor` alone repurposes a *sizing* result as an *eviction* signal, which the loop's contract
cannot absorb. `gpusAvail/gpusPR` already floors against the real pool, so the pool term alone prevents
overcommit; the mandate treats a water-level gap as a spendable budget. That is the same category error
the doc's own `:1281` and `:2260` passages warn against ("the pool is enforced, the fair share is not")
— both verified verbatim, and that tension is why this is an amendment question, not a compliance one.

Ranked: (1) option (c) above; (2) your recommendation — restore `ceil` + amend the T1 (zero risk, but
leaves the over-grant); (3) option (b) only with an explicit new termination invariant.

**I have not measured option (c)** and cannot — it needs a code edit, outside my scope. It would move
some of the coder's 9 failures (those asserting `ceil(x)` for non-integer `x > 1`) but **not** the
`bv 6→2` collapse, which was eviction. That measurement is the missing evidence and it is the coder's
to produce. **Still Dean's call** — I am supplying a third option and a defect verdict, not resolving
the fork.

## 2. Row-7 contradiction — I concur; the strike must be narrower than either of us said

The coder resolved it correctly: `coveragePerGPU` matches the `:1181-1186` blockquote and row 7
(`:2482`) verbatim — `max_i` of `prc/GPUsPerReplica`, dimensionless, comparator-only.

Corroboration you can use: the binder's-PRC reading is not implementable without giving
`sortVariantsForScaleDown` the role *and* a ballot to run, and the Type 1's own parenthetical concedes
it — "(which requires the function to learn which role it is ordering)". The superseded reading carries
its own admission of the cost that makes it the loser. C6d threads only `stateMap` for
`GPUsPerReplica`.

**Refinement.** You flagged that one clause of the superseded sentence is still live. It is **two**, and
both are implemented, so a wholesale strike of `:1176-1179` would drop two *satisfied* requirements:

- "tie-break on the *binder's* PRC (which requires …)" — **superseded, strike this only**
- "name-ascending as the final key" — **live**, implemented as the comparator's third key
- "give a variant with no scale-down ballot … the same key today's weighted sum yields" — **live**,
  implemented via `best` initialized `0.0` (the old Σ over an empty set was also 0)

Suggest re-homing both survivors into the blockquote so they are not orphaned when the mechanism clause
goes. No code change and no Type-3 change; you explicitly requested no Type-3 action from me and I took
none.

**One claim in your handoff I cannot let stand as reasoning**, though the conclusion is right: "no
#1513 golden has an exact Cost tie and none moved." B1 *does* have a genuine `Cost: 5.0` tie
(`prefill-v` / `decode-v`) — it is split across role buckets. The durable reason is per-scenario: the
row-7 key is unreachable in all eight goldens because Cost-desc resolves first in every bucket holding
two variants (A3 5 vs 15; B2 prefill 5 vs 15; B1's tie is cross-bucket; the rest are single-variant).
Table is in the review doc. Worth fixing in whatever text inherits this, because under the
"no tie exists" reason, adding a second decode variant at Cost 5.0 would still read as safe while
quietly making the key live.

## Also from the C6d review, since it bears on your fold-in bookkeeping

- **C6d is the tenth §4a-leaking commit, and the first to leak into *production* comments** — `N7` in
  `analyzer_helpers.go` goes 3 → 7. Finding 13's reword window is now ten messages, not nine. The four
  new production tokens are C9-fixable prose and are additional to the 32 already inventoried.
- **Finding 25 (new, should-fix, safe today):** `votesFromRoleSpare` still reads `e.RoleSpare[role]`
  bare, so a *missing* key materializes as a `0` vote — which is N7's **veto** value, not abstain. C6d
  fixed the veto predicate and `applyDeallocationForRole` but not the ballot. Safe today only because
  the shapes producing a missing key also leave that role with no anchor variants to shed. Invariant to
  document in C9: *an analyzer's `RoleSpare` key set must not diverge from the role set of the variants
  it prices* — it fails toward over-removal, since under uniform scores a `0` binds.
- **Finding 26 (new, should-fix, test-only):** the coder's N7-abstain fixture is green only on an
  inherited 3:1 score spread; normalize the scores to the shipped default and it goes red. It currently
  encodes Finding 25's defect as the intended contract.
- **Finding 4 CLOSED** on the code (per-variant veto re-check confirmed).
