# plan__ta-anchor-c11-ceiling-nil-maxreplicas-escape

from: review agent, PR-2 internal review (`ta-anchor-dynamic-refresh`)
to: planner (Type-1 owner for `combined-analyzer-optimizer-design.md`)
session: C11 pre-review — `(D-b)` cap instruction

re: **`(D-b)`'s per-site cap instruction leaves the sentinel unbounded when `MaxReplicas` is nil, at
all three grant sites.** A `(D-b)` amendment is needed whichever way the C11 diff goes.

**Timing:** C11 is being written right now — four source files modified and uncommitted at coder tip
`eb12089a`. This is information about the window, not a request to interrupt anyone; routing it to you
because `(D-b)` is Type-1 text and Dean's *"don't leave design decsions to coder"* means the coder
silently deviating from it is the wrong resolution even when the deviation is the correct code.

## The finding

`(D-b)` instructs, per grant site: *"fold into that same `headroom` computation, **including its
`headroom <= 0 → continue`**"* (`costGreedyRolePick`) · *"same clamp, same skip"* (`fairShareRolePick`) ·
*"add the ceiling to that same `break` condition"* (`fillRole`).

At all three sites that machinery sits **behind a nil-guard on `MaxReplicas`**, so a ceiling folded into
it inherits the guard and does not exist when `MaxReplicas` is unset. Verified at `eb12089a` (the Type 1
states its lines as of `d9f3b97e`; C6a–C6f moved all three, so these are re-derived):

**1. `cost_aware_optimizer.go:104-111`**
```go
if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
    headroom := *state.MaxReplicas - targets[vc.VariantName]
    if headroom <= 0 { continue }
    return vc.VariantName, headroom
}
return vc.VariantName, math.MaxInt        // ← outside the block (D-b) names
```
`(D-b)` cites *"`cap` = `MaxReplicas − targets[v]`, else `MaxInt`"*, so the `MaxInt` branch was seen —
and the fix was then located in the other one.

**2. `greedy_score_optimizer.go:711-717`** — same nil-guard around the only clamp and the only skip
(`fairShareRolePick` is now at `:621`).

**3. `rescale.go:454-460`** — worst of the three:
```go
for wantGPUs-spent >= g {
    if st.MaxReplicas != nil && *st.MaxReplicas > 0 && targets[vc.VariantName] >= *st.MaxReplicas { break }
    targets[vc.VariantName]++
    spent += g
}
```
A single `&&` chain rooted on `!= nil`, in a loop bounded by nothing else but `wantGPUs`. A conjunct
added to that chain reproduces precisely the unboundedness `(D-b)` opens by naming — *"`targets[v]++`
in a loop bounded only by `MaxReplicas`"*.

## Why it is the default case, not an edge

`MaxReplicas` is `*int` (`internal/domain/saturation_analyzer.go:325`), and the guard
`!= nil && > 0` treats nil and `0` alike as *unbounded*. The sentinel's target population is
**never-seen, zero-replica variants** — the population least likely to carry a tuned ceiling. So the
escape is not a corner of the fix; it is the shape the fix takes on an untuned variant.

Severity is then `(D-b)`'s own warning, unmitigated: *"a single never-seen variant can absorb the whole
budget one request-per-second at a time."* At `PRC = 1`, `fillRole` buys `wantGPUs / gpusPR` replicas of
a variant nobody has measured.

## Why this needs your amendment either way

- C11 follows `(D-b)` literally → a real code defect, and the instruction caused it.
- C11 hoists the clamp out of the nil-guard → correct code that **contradicts its governing text**, and
  `(D-b)`'s per-site table is wrong on all three rows.

Only the second is good code, and it still leaves the Type 1 needing a correction. Suggested shape for
both: the ceiling is an **unconditional** clamp on the sentinel variant's target — a *sibling* of the
`MaxReplicas` clamp, not nested inside it — carrying its own `<= 0 → continue`/`break`. Concretely
`cap = min(cap, 1 - targets[v])`, **not** `min(cap, 1)`: `(D-b)` is explicit that the bound is on the
target, *"not on a single iteration, so a repeated allocation loop cannot buy a second replica by going
round again"*, and a literal `min(cap, 1)` satisfies that sentence without satisfying the requirement.

The `→ continue`/`break` half stays load-bearing for the same reason `(D-b)` already gives: a picker that
*returns* `cap = 0` drives `n = 0 → utilByRole = 0 → deltaUtil = 0 → break`, killing the model's whole
allocation loop rather than moving to the next variant.

## Companion — an ordering constraint the frozen text cannot have known about

C6e rewrote `fairShareRolePick` after the Type 1 froze, and it now contains a floor that **raises**
`capN` past every bound computed before it:

```
:701   capN := replicasToCover(share, gpusPR)
:702   if firstDraw && capN < 1 { capN = 1 }     ← floor
:710   capN = min(capN, gpusAvail/gpusPR)
:711   if state.MaxReplicas != nil && ... { capN = min(capN, headroom) }
:718   if capN > 0 { ... return vc.VariantName, capN }
```

So a ceiling placed with the `MaxReplicas` clamp is safe, while one placed next to `replicasToCover` —
where replica counts are first computed, and a natural reading of "cap the sentinel at one replica" — is
**defeated by the next line**. `(D-b)`'s correctness at this site currently rests on function layout that
post-dates the freeze, and nothing states the dependency. A sentence in `(D-b)` and a comment at the
floor would both survive the next edit to that function.

Bounded, with one part I did **not** establish: the floor stays true for every role until the caller
commits (so a mis-ordered ceiling leaks once per role), but within a closure it cannot fire on a second
grant of the same variant, because `spentGPUs` goes positive once the caller writes the first grant back.
The one route to a genuine *target*-bound breach is two roles resolving to the same sentinel variant in
one pre-commit window (a variant serving both roles, or `role == "both"`). **I have not tested that and am
not asserting it is reachable** — flagging it as the case that would distinguish "leaks per role" from
"breaches the target bound".

## Scope note

Both items are pre-registered in `planning/ta-anchor-dynamic-refresh-review.md` § *C11
pre-registration* (Findings 42 and 43), committed at `470f4b8d` **before** the C11 diff existed, so they
can be scored as hits or misses once it lands. I have not looked at the uncommitted working tree.

Two things I am **not** doing, deliberately: not directing the coder (a trigger carries no instructions,
and the coder's scope comes from its own Type 3 — the route is your amendment, then your doorbell), and
not proposing the code myself.

## Also verified and passing, for the record

`(D-a)`'s argument that the sentinel can ride the existing gates rather than needing a separate
*admissible* predicate **holds at the tip**: exactly six anchor-`PRC <= 0` gates, the same six `(D-a)`
names (`cost_aware_optimizer.go:100`/`:135`/`:284`, `greedy_score_optimizer.go:686`, `rescale.go:446`/
`:579`), no seventh admitting the sentinel unaudited. The `prc <= 0` gates in `analyzer_helpers.go` and
the optimizers are ballot-side and never see it — the same reasoning `(D-a)` uses to clear
`applyAllocation`, and it checks out.
