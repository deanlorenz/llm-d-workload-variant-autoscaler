# plan__ta-anchor-fork-priced-before-its-mitigation

from: review — PR-2 internal code reviewer, `planning/ta-anchor-dynamic-refresh-review.md`
to:   planner — Type-3 owner, `planning/ta-anchor-dynamic-refresh-plan.md`
session: T1-1 ceil/floor fork — its decision input is stale
date: 2026-08-08
ask: one fact you may want before you route the fork to Dean. No verdict from me; the fork is his call.
re: your `plan__ta-anchor-c6c-ceil-eviction-fork.md` (`.DONE`) and the designer's
    `plan__ta-anchor-designer-withdraws-t1-1-and-the-coder-accusation.md` (`.WIP`, cc me)

---

## The fork is priced at C6c; the PR later shipped the mitigation for that price

**The 9-failure measurement was taken on a code shape that no longer exists.** Verified at HEAD
`a9afb740` (25 commits on `075a208e` — `rev-list --count`, not a subject-line compare):

- `firstDraw` is **absent** at C6c `34b18bc5` and was **introduced by C6e `784c2b5c`**, two commits later.
- The guard is `if firstDraw && capN < 1 { capN = 1 }` at `greedy_score_optimizer.go:702`, and its comment
  is the C6c eviction diagnosis restated as a fix: *"only before the first commit is an empty pick fatal
  to the whole model rather than a defer."*

Chain verified by reading, four links:

1. `firstDraw := spentGPUs == 0` (`:660`) — true only while nothing is committed for the model.
2. The guard forces `capN = 1`, so a first draw with a priced, affordable, headroom-uncapped candidate
   cannot be empty.
3. `allocateForModel` returns **`w.remaining < oldRemaining`** — progress, not pick-emptiness.
4. So a non-empty first draw ⇒ `allocated == true` ⇒ `!allocated → w.remaining = -1` never fires. That
   assignment is the eviction the coder diagnosed.

**The guard does strictly more work under `floor` than under `ceil`.** `replicasToCover` returns 0 only
when `entitlementGPUs <= 0`; otherwise `ceil ≥ 1`. So under the shipped `ceil` the guard fires *only* on an
exhausted balance. Under `floor` it fires whenever `0 < share < gpusPR` — exactly the sub-replica
entitlement that produced the collapse-to-1 signature in the coder's table. C6e was written for the `ceil`
world and is, incidentally, the `floor` mitigation.

Set against the coder's option (b): *"`capN == 0` must mean defer, not evict, which means `!allocated` can
no longer unconditionally set `remaining = -1` … more than a one-line commit."* C6e reaches the same end
from the other side — instead of making `!allocated` non-fatal, it makes the first draw non-empty so
`!allocated` cannot fire for a model with a viable candidate. For the dominant case that work is already
in the branch.

## What I am not claiming

I have **not** re-measured, and I do not build or test in the coder's worktree, so no failure count from me
is signed off. I claim the *mechanism* is neutralized for the first-draw case, by reading; I do **not**
claim the 9 becomes any particular number. Two residuals the guard does not touch: draws after the first
(where `capN == 0` now genuinely defers, because `allocated` is already true — the intended behavior), and
a first draw with no priced or affordable candidate, which the fork does not affect either way.

## Why this is yours rather than mine

Both prior handoffs are accurate and omit the same fact. Yours records the fork as open and "avoided by
construction"; the designer's §2 withdraws T1-1's urgency as a doc-vs-code divergence with "the branch
currently compiled is the safe one." Neither notes that a mitigation for the measured cost shipped two
commits after the measurement. Net effect: **Dean would be deciding a fork priced at C6c in a PR that has
since addressed that price.**

The refresh is cheap — `math.Ceil` → `math.Floor` at `:837`, run the existing suite at HEAD. Re-measuring
is a coder action and I am not directing it; the fork is Dean's call and I am not making it. Flagging only
that the decision input is historical, and inexpensively refreshable while the branch is unpushed.

## Two smaller corrections in the same area

1. **§6's grep does not work, and the suggested repair undercounts.** Case-sensitive `grep -rn "ceil("`
   over `internal/engines/pipeline/` returns **30 hits, all in `_test.go` files**, none in non-test code —
   they are `ceil(x/y)` notation in test names and worked comments describing the demand→replica
   conversion that stays. The coder's `-i` repair finds **four** non-test sites across `internal/`, not
   three: `greedy_score_optimizer.go:837` (the fork), `analyzer_helpers.go:629`, `rescale.go:598`, and
   `queueingmodel/analyzer.go:379` — the last omitted by scoping to `pipeline/`. The three non-fork sites
   all stay.

2. **`floor` mostly means *minimum* in the file that owns the policy.** `greedy_score_optimizer.go` has
   four `floor` mentions (`:453`, `:595`, `:659`, `:829`) plus one `math.Ceil` (`:837`), and **only `:829`
   is a round-down statement** — `:595` and `:659` are C6e additions about the holdback floors. A token
   search for the rounding policy runs 3:1 false positives inside that file. If the fork resolves, eight
   endorsement sites move together and only **one** (`:837`) is reachable by `git grep -i ceil`; this
   corrects my own earlier "two of eight," which credited the grep with a hit on "floored".

## Scope

No code, Type-1, Type-3, or CURRENT.md edit. Writes: this file, and the Finding 64 section in my own
review doc. I did not rename the designer's `.WIP` handoff or the coder's `.DONE` ones — not mine to move.
