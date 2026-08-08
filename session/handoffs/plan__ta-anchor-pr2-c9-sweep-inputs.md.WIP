from: review (ta-anchor-dynamic-refresh internal reviewer)
to: planner
session: PR-2 C9 sweep inputs — corrected §4a ledger + two one-line findings

Routing these **before C9 lands** rather than after, because all of them are one-line fixes that C9 is
the natural host for. If C9 ships without them they each need a further commit, which is the opposite
of what C9 is for. Nothing here is blocking; nothing here is routed to the coder by me.

Branch state at time of writing: `ta-anchor-dynamic-refresh` @ `79a590d6`. Reviewed and written up in
`planning/ta-anchor-dynamic-refresh-review.md` (commits `dba35c60`, `34f3feab`, `e498c5d6`).

## 1. Corrected §4a ledger — two figures I had been quoting were wrong

Recounted at three tips with one fixed pattern (`C<n>[a-f]?` · `PR-1/2` · `W<n>` · `N<n>` · `U<n>` ·
`D-a/D-b` · `T1.<n>` · `FZ-admission`), **text files only** (`git grep -I`), over `internal/**` +
`docs/**`:

| tip | code/doc token locations | commit messages carrying a token |
|---|---|---|
| `075a208e` (PR-1 tip = base) | **7** (inherited, not PR-2's) | — |
| `b6bb525c` (C11) | **52** | 16 of 18 |
| `1a50b418` (C10) | **53** | 17 of 19 |
| `79a590d6` (fillRole tests) | **54** | **18 of 20** |

Corrections to what I previously reported:

- I quoted **53 code/doc locations "as of `b6bb525c`"**. It was 52 there; 53 is the post-C10 figure and
  54 is current. So PR-2 has introduced **47** locations on top of 7 inherited.
- I quoted **"17 of 19 commit messages" as of `b6bb525c`**. It was 16 of 18 there. 17 of 19 was right at
  C10 and it is now 18 of 20.
- An earlier count of mine reported ~61 locations. That run included 8 `Binary file … matches` lines from
  the dev-guide PNGs, whose bytes happen to match the pattern. Not token locations.

**Reword-window arithmetic, on the corrected basis.** The trajectory across the last three commits is
16 → 17 → 18, with C9 still to land. The branch needs a force-push regardless
(`origin/ta-anchor-dynamic-refresh@f6485980` is orphaned), so `rebase -i` + reword is free right now and
becomes a live-PR history rewrite the moment PR-2 opens. This remains Dean's call and "not worth it" is a
legitimate answer — I am only keeping the number honest.

## 2. Finding 49 — §4a token in a code comment (one line)

`internal/engines/analyzers/throughput/k_sat_test.go:163`

```go
// and whose scale-up watermark is 0.85. Pre-C10 this priced at k = 0.85;
```

"Before this change" carries the same meaning. Unlike the commit-message instances (fixable only by
reword) this is an ordinary edit.

Second instance, same class, from `79a590d6`: `internal/engines/pipeline/rescale_test.go`, in the
`fillRole` Describe's leading comment — "The from-zero admission ceiling (C11) is what stops a variant
admitted at PerReplicaCapacity = 1 from doing that". Dropping "(C11)" loses nothing; the sentence already
names the mechanism.

## 3. Finding 50 — `max` shadowing reintroduced (minor, two lines)

`internal/engines/pipeline/rescale_test.go:239` and `:248` declare `max := 3` / `max := 8`, shadowing the
Go builtin. Three facts:

- These are the **only two** `max :=` declarations in the repo at this tip (`internal/**`, `cmd/**`).
- The pattern was flagged by ev-shindin in the #1246 review (`roleBottleneckReplicas`,
  `roleAggRemaining`) and a cleanup item for it is still in the backlog.
- **Those flagged sites are now gone** — `analyzer_helpers.go:977` uses the builtin correctly
  (`max(int(math.Floor(...)), min(1, n))`). The codebase has moved off the pattern; these two lines are
  the sole place reintroducing it.

Not a gate failure — gocritic's builtin-shadow check is off by default and the coder's gates were green,
so this passes `make lint`. It is a convention regression against a maintainer's stated objection.
`maxRep := 3` costs nothing. No competing local idiom exists: no other pipeline test declares a
`MaxReplicas` local at all.

## 4. A §4a sub-class worth deciding on, because it will recur

`79a590d6`'s message ends: "Raised by the PR-2 internal review as Finding 47."

Attribution to an internal review document **by finding number** is unresolvable for anyone reading
`main`, and is arguably worse than a bare "the plan" because it reads as a precise citation. This will
recur every time a commit answers a review finding — the coder is now doing that regularly and the habit
is otherwise a good one. Two other soft instances in C10's message: "the plan has `resolveKSat`
type-assert …" and "Two deviations from the plan".

Neither carries a path or filename, so both sit outside §4a's literal prohibition. Worth an explicit
ruling on whether the class covers bare "the plan" and review-finding attributions, since the answer
changes whether C9's sweep is 54 locations or 54 plus a message pass. My read: the *substance* of these
attributions is always already in the message and stands without them, so dropping the identifier is
free — but that is a convention call, not a review finding.

## 5. Still-open C9 expectations from earlier findings (unchanged, restated for one place)

- `analyzer_helpers.go:213-216`'s "Not proactively selectable" comment is now false and needs correcting.
- The plans-branch **path/filename** class (distinct from the token class above).
- C9 must **not** describe the from-zero ceiling as an active guard — per Finding 46, nothing writes the
  tag, so `(D-a)` is deferred and the ceiling is dormant in production. A dev-guide sentence implying it
  currently bounds anything would be wrong.
