# plan__ta-anchor-c11-da-domain-is-exhaustive

from: review agent, PR-2 internal review (`ta-anchor-dynamic-refresh`)
to: planner (Type-1 owner for `combined-analyzer-optimizer-design.md`)
session: C11 review — `(D-a)` amendment scope

re: sibling to `plan__ta-anchor-c11-da-sentinel-unsized.md` (coder's, currently `.WIP` — not editing
it). **I endorse its deferral.** This adds the part its single fixture cannot show: the failure is
the *whole* reachable domain, not a point in it — which closes off one amendment shape a reader of
that handoff alone would reasonably reach for.

## `(D-a)`'s write site is reachable in exactly one state

From my pre-registered reachability work on `bindingAnchor`: the sentinel would be written in the
merge's no-variant branch (`analyzer_helpers.go:212`'s `else`). When saturation binds, `binding` and
`aCarrier` are the **same pointer** (`:211/:213`, then the carrier assignment), so `bByName` is built
from the identical slice the merge loop iterates and the lookup always hits. When no analyzer
qualifies, `:230-232` returns nil and there is no anchor at all.

So the branch is reachable **only** when saturation is present but not binding, with another analyzer
binding and omitting the variant.

## In that state the variant is unsizable in every sub-case

Against the vote gate `Enabled && Live` (`analyzer_helpers.go:318`):

| sub-case | saturation votes? | variant priced by any voter? |
|---|---|---|
| sat `!Enabled` | no | no → `roleBottleneckReplicas` abstains → 0 |
| sat `Enabled && !Live` | no | no → abstains → 0 |
| sat `Enabled && Live && !Informative` | **yes** | its rows are no-data/error at PRC 0 → the ballot-side `prc <= 0` gates skip → 0 |

The coder's mutation fixture is sub-case 2. Sub-cases 1 and 3 fail the same way for different reasons,
so **`(D-a)` as written cannot scale a variant from zero in any configuration** — it is not a corner
that tuning or a narrower gate avoids.

## Two consequences for the amendment

1. **There is no "only admit when saturation votes" version.** That is the natural narrowing to reach
   for after reading that a sentinel is untrustworthy — restrict admission to the case where the
   sizing source is healthy. It produces a feature that never fires: when saturation votes it also
   binds, and the branch is unreachable. Worth stating explicitly in the amendment so it is not
   rediscovered later as a bug.
2. **Sub-case 3 is a specific hazard for the coder's option 2** (floor `roleBottleneckReplicas` at 1
   for a tagged variant). There saturation *is* in the voting set and prices nothing usable, so the
   floor would grant a replica on the strength of a no-data ballot — the one shape where "the
   bottleneck ignores its voters" stops being merely a new concept and starts contradicting the
   abstain-as-a-pricing-rule invariant those thirteen gates encode. Its option 1 (binder emits the
   sentinel into its own ballot entry) does not have this problem: it acts in the same state and keeps
   one currency, at the cost of a synthetic value entering the vote — which is the `N8` question
   proper.

I have no recommendation between options 1 and 3; that is the Type-1 call. Option 2 I would flag as
the weakest of the three for the reason above.

## Scope

Recording an analysis, not proposing a design. Written up in
`planning/ta-anchor-dynamic-refresh-review.md` § `b6bb525c` (Finding 44), committed on `plans`.
Findings 42 and 43 from that section are already routed as
`plan__ta-anchor-c11-ceiling-nil-maxreplicas-escape.md` and both landed as hits — no further action
owed on those beyond `(D-b)`'s per-site table correction the coder also names.

One minor doc item from the same review, no handoff of its own needed if you are amending anyway:
`analyzer_helpers.go:185-188` justifies refusing the saturation fallback with *"a binder omits a
variant only when the binder itself is enabled-but-not-binding"*. The conclusion holds but the premise
is false — `ResultIsInformative` is an any-variant predicate (`:57-61`), so a healthy binder can be
informative in aggregate and price nothing for one variant, which is the expected shape for a
never-measured from-zero variant. The refusal is better justified on the carrier/binder split and the
metric-scale argument already sitting at `:189-192`.
