from: review (PR-2 internal code reviewer, ta-anchor-dynamic-refresh)
to: planner
session: claim-pricing verdict + C6e site-(ii) coverage gap + §4a recount

Reviewed C6e (`784c2b5c`), noted C6f (`a679f2ad`), reviewed the unplanned dormant spec
(`537b0153`), and adjudicated all three `review__ta-anchor-claim-*` handoffs. Findings 28–33 are
written up in `planning/ta-anchor-dynamic-refresh-review.md` @ `ded9dc5f`; the three triggers are
`.DONE`. This handoff carries only what needs a decision or a plan edit.

**I have not rung the coder's bell.** Per CONVENTIONS, if any of this should change what the coder
does, you edit the plan and trigger it. Nothing below is routed to the coder by me.

---

## 1. Claim pricing — the defect is real and the measurement stands, but not for the stated reason

Verified at tip: `claimGPUs:86-97` takes **both** conversion factors from the reference variant, and
`referenceVariantForRole:840-843` filters on `PerReplicaCapacity > 0` and nothing else. Both measured
rows re-derived independently and both reproduce (X +3 / Y +1 asymmetric; X +2 / Y +2 symmetric, the
latter over three iterations). Pure redistribution, pool honored 4 = 4 either way, invisible to every
golden.

**Finding 32 — your addendum's independent derivation cannot execute.** It applies the
`w.remaining <= mean` branch (`greedy_score_optimizer.go:295-296`) to `active[0]`, but `active[0]`
after `sortByRemainingDesc` (`:289-290`) is the **maximum**, so that branch is unreachable unless every
active model's remaining is equal. Asymmetric row: real values are `allocationMean = mean = 6` and
`target = 3`, not `1.5`/`7.5`. The outcome survives because the bottleneck binds at 3 either way, so
the row is right for the wrong reason; the symmetric row's first step is genuinely `3 <= 3` and then
takes the same unreachable branch, with the true path being three iterations to the same X 3 / Y 3.

Flagging it because the addendum concluded *"treat it as settled"* on the strength of that arithmetic.
**It is settled — by my re-derivation.** The same slip would change the answer materially in any
fixture where `capN` rather than the bottleneck binds, which is most of the interesting ones.

**Finding 31 — a sharper root than "reference selection ignores headroom", and a fourth option.**
`referenceVariantForRole`'s doc comment (`:829-838`) dismisses reference ≠ picked with *"the cap
divides by whichever candidate the picker landed on"*. You correctly note it names the wrong
approximation (per-replica capacities, not `GPUsPerReplica`). The second half: that sentence answers a
question about the **cap**, which is consistent with the spend by construction, while the defect is in
the **claim** — the ranking key and the per-pass `target`. It closes a question nobody needed answered.

Deeper: `sortByCostEfficiencyAsc` orders by `Cost / PRC`, i.e. **money** per unit capacity, so the
reference is the money-cheapest variant — and its `GPUsPerReplica` then denominates a **GPU** quantity.
Nothing ties the money-cheapest variant to the GPU cost of serving the demand. Headroom-blindness is
the sub-case where that divergence is permanent rather than transient, which is why both reproducers
are built on it: it is the shared **trigger**, not the shared root. Consequence for your fix menu: the
~3-line headroom filter removes both measured cases but does not make the claim consumption-faithful,
so it converts a measured distortion into a narrower unmeasured one — as you say yourself.

**Option (d), which none of the three handoffs raises.** Select the reference *for pricing* by **GPU**
efficiency — `min(gpusPR / PRC)` over the role's feasible candidates — instead of cost efficiency.
The claim becomes a true lower bound on the GPUs needed to serve the role, so it can never be inflated;
it is headroom-independent, so it also covers the transient case the filter misses; it degenerates to
today's value whenever a role's variants share `GPUsPerReplica`, which is every existing fixture; and
under-claiming is the conservative direction (lower rank, lower `target`) while spend stays bounded by
the cap, which already converts through the picked variant. Cost comparable to the headroom filter.
Limit: it changes pricing only, not pick order, so the claim becomes a floor on the model's true GPU
need rather than a prediction of its spend.

**Not my call.** The Type 1 is frozen at `8c2a9b04` and both handoffs address me as "Type-1 owner" —
I am the internal code reviewer. The choice between accept-and-document, the headroom partial, and
option (d) has PR-2 scope implications that are Dean's and yours. Recorded, routed, not decided. Note
this is the **second** frozen-Type-1 rationale defect needing a post-freeze touch at Dean's
discretion, alongside Finding 27's `:1530-1533` — they should probably be decided together.

**The dormant spec landed while I was verifying** — `537b0153`, test-only +88, exactly the shape you
recommended: `PIt`, asserts the honest even split (X 3 / Y 3) rather than today's 3/1, pins **both**
sides of the redistribution, verified red when temporarily enabled. Reviewed and endorsed. Two things
for you: it is **not in the plan** and says so in its own first line, so it needs either a §-home or an
explicit "unplanned, revert-if-the-disposition-rejects-it" note; and the coder had offered me the
"say the word" decision on its shape, which I did not answer — a reviewer cannot direct a coder. It
resolved correctly without me.

## 2. Finding 28 — C6e pins the clamp but not `fairShareRolePick`'s per-role budget

§C6e names two defects to pin. The suite pins one. Structural reason: **with a single analyzer entry,
the clamp's per-entry running balance and the picker's per-model ledger are the same constraint**, so a
sat-only spec cannot separate them. Fixing the clamp alone yields decode-v 4, prefill-v 2, spent 7 —
identical to the assertions.

| fix variant | spec 1 (sat-only) | spec 2 (two voters) |
|---|---|---|
| neither (pre-C6e) | RED | RED |
| picker budget only | — | RED (2 / 2 / spent 3) |
| **clamp only** | **GREEN** | **GREEN** (4 / 2 / spent 7) |

So spec 2 is a genuine clamp discriminator, but `committed0`, `reserved`, the per-draw holdback and
`firstDraw` — the bulk of a +241 production diff — are pinned by nothing. Two aggravators: the fixture
comment narrates the holdback causally (*"its share is 7 less the one GPU held back for prefill"*) in a
way the assertion cannot distinguish from the clamp acting alone; and §C6e **asked for** "roles that
would each individually fit but jointly overrun", whereas in the shipped fixture both roles
individually exceed `target`, which is exactly what lets the clamp-only variant pass.

The discriminating technique is established one commit earlier by the same coder — `34b18bc5`'s
message on calling the returned pick closure directly. This is **Finding 20's shape recurring**, and
Finding 20 is already in the plan, so the general instruction exists; C6e is where it was not applied.
If you want the budget half pinned, that is a plan edit (an added spec), not something I can direct.

**Also for the C9 dev-guide pass — Finding 29:** the new "Fair-share iteration" paragraph says the
single-model case "gets `mean == 0`". It is `allocationMean` that is zeroed (`:292-297`); `mean` itself
equals that model's own remaining and still governs the `w.remaining > mean` drop check at `:308`.
Since the same section uses `mean` as the water level, the sentence currently reads as the inverse of
what happens.

**Corrected in my own doc:** I had pre-registered that a `[sat]`-only golden was *expected* to move at
C6e and that "no golden moved" would be the signal to look harder. That was wrong and the coder is
right — and it generalises further than the commit claims: because `claimGPUs` **sums** role claims in
GPUs and `allocationMean = 0` for one active model, the entitlement equals the roles' combined spend
exactly, so the fair-share entitlement bug is unreachable without multi-model contention and no
single-model golden *can* move.

## 3. §4a — recount, and one item that should not ship

Enumerated per commit and per file this time (I have under-matched twice).

**Messages: 14 commits · 13 token-bearing · 10 token-bearing subjects · `34b18bc5` still the only
clean one.** This supersedes "all nine (6/9 subjects, 8/9 bodies)" in CURRENT.md and Finding 13, and
my own "ten". **Reword cost is now 13, not nine or ten**, still ~free while the branch is unpushed and
needs a force-push anyway, still a live-PR history rewrite once PR-2 opens.

**Code/docs, attributed against base `075a208e`:** production `.go` doc comments went **0 → 19** —
PR-1 leaked into test comments only; **PR-2 is the first to reach production prose**
(`analyzer_helpers.go` 12, `rescale.go` 4, `greedy_score_optimizer.go` 2, `optimizer_interfaces.go` 1).
Tests ~11 → 41; dev-guide 1 → 5 (`multi-analyzer-pipeline.md` gained `N7`×2, `N8`, "Type-1 owner").
CURRENT.md's "32 code/doc locations" is now ~49. Growth is linear in commits, so C9's cleanup grows
with every prose-bearing commit.

**Finding 33 — the one item I would not leave for C9.** Two shipped test comments now cite
plans-branch **paths**, a worse class than bare tokens:

- `greedy_score_optimizer_test.go:1602` → `plans/session/handoffs/plan__ta-anchor-c6f-w4-no-spend-is-false.md`
- `greedy_score_optimizer_test.go:1741` → `Refs:` three `review__ta-anchor-claim-*.md` handoffs

A token like `W4` is at least guessable; a path into an orphan branch is unresolvable by construction,
and these name **handoffs** specifically — the most ephemeral artifacts we have, renamed `.DONE` and
`git rm`-ed in a later sync commit. The references will be dead before the PR merges. The intent is
right (a reader of a dormant spec needs to know where the open question lives); the compliant form is
prose with no path. Base `075a208e` has exactly one such path anywhere
(`docs/developer-guide/throughput-analyzer.md:698`, pre-existing, already in `main`, already in
`governance-follow-ups.md`) — that precedent explains the habit but does not license extending it.
Same commit also cites `784c2b5c` in a comment, a pre-rebase SHA that will not survive the `rebase -i`
the branch already needs.

## Evidence

Read-only at worktree `ta-anchor-dynamic-refresh`, tip `537b0153`:
`internal/engines/pipeline/greedy_score_optimizer.go:85-106,:285-308,:330,:338,:346-351,:829-843`;
`greedy_score_optimizer_test.go:1571-1745`; `analyzer_helpers.go:275`;
`internal/engines/analyzers/saturation_v2/analyzer.go` (`aggregateByRole`);
`internal/engines/analyzers/throughput/analyzer.go` (`aggregateRoleCapacities`);
`internal/engines/analyzers/saturation/engine_v2.go:508`. Token scans run at both `075a208e` and
`537b0153`. My write-up: `planning/ta-anchor-dynamic-refresh-review.md` @ `ded9dc5f`.

No file outside `planning/ta-anchor-dynamic-refresh-review.md` and this handoff was edited; the three
`review__ta-anchor-claim-*` triggers are `.DONE`.
