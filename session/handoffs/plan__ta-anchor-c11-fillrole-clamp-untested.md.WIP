# plan__ta-anchor-c11-fillrole-clamp-untested

from: review (PR-2 internal code reviewer)
to: planner (ta-anchor-dynamic-refresh Type-3 owner)
cc: Type-1 owner — attaches to the `(D-a)` disposition, not to `(D-b)`'s correctness
date: 2026-08-07
re: sibling to `plan__ta-anchor-c11-da-domain-is-exhaustive.md` (now `.WIP`, so not edited). One
test-coverage item on `b6bb525c`. Full write-up: `planning/ta-anchor-dynamic-refresh-review.md`
§ Finding 47.

## The item

`(D-b)` clamps three grant sites. Two of them a tagged variant can actually reach; the third it cannot.
Test coverage does not line up with that split, and the disclosure lines up with it backwards:

| site | tagged variant reaches it | C11 test | gap disclosed |
|---|---|---|---|
| `costGreedyRolePick` | yes | 3 behavioural specs | n/a |
| `fairShareRolePick` | **no** — `available[vc.AcceleratorName]` gate, empty on a never-measured variant | none | **yes**, reasoned in the test comment |
| `fillRole` | **yes** | **none** | **no** |

`fillRole`'s only pre-clamp gates are `rescale.go:446` `PerReplicaCapacity <= 0` — which a `PRC = 1`
sentinel passes by construction — and `:450` `g <= 0`, which reads `gpusPerReplicaFromState`, i.e.
**state**, not capacity. The empty-`AcceleratorName` fact that legitimately excuses
`fairShareRolePick` does not apply here.

This is also the site the commit itself nominates as the worst case: `rescale.go:456-459` ("*this loop
is otherwise unbounded whenever MaxReplicas is unset -- which is where a from-zero variant would absorb
the whole role's GPUs one unit of capacity at a time*") and `analyzer_helpers.go:103-104` ("*fillRole's
loop is bounded only inside the MaxReplicas condition*"). The inner loop breaks only under `bounded`,
so the one-bite claim rests at this site on prose alone — and per Finding 46 nothing writes the tag, so
production exercises none of it either. Unvalidated, not merely uncovered.

## What I am *not* charging to C11

`fillRole` has zero direct test references tree-wide, which is **pre-existing**. C11 did not remove
coverage. The narrower charge: a guard was added at a reachable, untested site, no test came with it,
and the justification written for skipping the *other* site makes the silence here read as coverage.

Nor is this a defect in `(D-b)`. I reviewed the clamp itself as correct at all three sites, untagged
behaviour verbatim (Finding 42, HIT).

## Why it is cheap, and why the fixture is worth having

`fillRole` is unexported but in-package and takes plain arguments — no `available` map, no interfaces.
A tagged `VariantCapacity{PerReplicaCapacity: 1, Reason: ReasonFromZeroAdmission}`, a state with
`GPUsPerReplica: 1` and `MaxReplicas` nil, `wantGPUs: 10` → assert `spent == 1`, `targets[v] == 1`.
Against the pre-C11 body the same fixture returns `spent == 10`. A 10× miss is the strongest
discrimination signal anywhere in C11, and it is the one left on the table.

## Disposition question (yours; I am not proposing a commit)

Severity is low **today** — the site is dormant while `(D-a)` is deferred — and becomes the untested
half of the guard at the exact moment `(D-a)` lands. Two acceptable shapes, one not:

1. Land the ~15-line fixture with C11 while the code is fresh.
2. Record it as owed work in the `(D-a)` follow-up, explicitly.
3. **Not** acceptable: treated as covered by the four `maxTargetReplicas` unit specs. Those prove the
   helper returns the right number; they say nothing about the loop honouring it.

If C9 is the natural host rather than an amendment to C11, that is entirely your call — C9 already owes
a dev-guide pass that must not describe the ceiling as active (Finding 46), and the two travel together.
