from: planner (doc-coverage audit, 2026-08-16)
to: plan (atomic-step-protocol-brainstorm — you own the process fix, per Dean's explicit instruction)
session: call-stack docs, two process asks — Type 3 scoping + a Type 6/Type 2 home for post-coding stacks

## Why this is coming to you

Dean, after reviewing `planning/doc-coverage-audit-20260816.md` (a doc-coverage audit across all
Type-1 missions — not restated here, read it if you want the full context): **"atomic-step currently
owns the process fixing. It should do it."** Two asks, both his decisions, not mine to design.

## Background — what the audit found, briefly

Your `## Intent` field's `current call stack` / `planned call stack` (per
`atomic-step-protocol-design.md:242-243`) is already a real, working mechanism — 11 Type-3 docs in
this cluster carry it. The audit found it works well *inside* your cluster but has never been
generalized as a convention for Type-3 docs outside it (e.g. no WVA-product-mission Type 3 has one).
Separately, `multi-analyzer-postrefactor-map.md` (a standalone "source trace" doc, per
`doc-and-session-model.md:114` — Dean already ruled 2026-08-07 these are "traces, not authorities,"
and flagged the kind as deserving its own type name, never promoted) is now confirmed **stale**: three
items it tagged `[next PR]` have already landed in PR-2's code.

Dean's response to both findings, verbatim below.

## Ask 1 — Type 3 call-stack scoping

> "yes, type 3 should have a current call stack like atomic-step, but scoped only to the specific
> type 3 (only show affected stacks)."

Reading: the `current call stack` field, generalized as a convention for Type-3 docs beyond this
cluster, should show **only the stack paths this specific Type 3 touches** — not the whole mission's
call graph. This is a **narrower** ask than what `multi-analyzer-postrefactor-map.md` does today (that
doc tours the *entire* optimize-cycle call stack, tagged `[this PR]`/`[next PR]`); Dean is asking for
something closer to your own `sync-watchers-spec.md`'s `## Intent` shape (a compact box diagram of just
the scripts/paths that spec touches) generalized outward, not for the full-tour shape to spread.

## Ask 2 — where does a post-coding, aggregated call-stack live?

> "post coding call stack I am still not sure. review type 6 docs can add it — makes the review easier
> to follow and understand where changes were made. again scoped to particular change. However, should
> also be tied to type 4 (maybe not committed in guides, but traceable in my plans). type 4 say what
> exists. They accumulate all code changes that actually happened (ie, multiple stacks, from multiple
> type 3,6 will become a single call stack). I think this is still the right approach, we just need a
> good home for it. I suggest we put it in the type 2 for now. Type 2 already aggregates multiple type
> 3 docs. Its mission is already to explain how the type 1 is achieved. We move it later."

Reading this as two distinct pieces, both his call, not for you to re-derive:

1. **Type 6 (review) may add a scoped call-stack** — one change, one review, easier to follow. This is
   the same "only affected stacks" scoping as Ask 1, applied at review time instead of plan time.
2. **The accumulated/aggregate stack — many Type 3s' and Type 6's individual stacks, merged into one
   picture of what actually exists in code — gets a temporary home in Type 2.** Not Type 4: Type 4 is
   what ships in the PR, on the code branch, and per CONVENTIONS "reflects actual current code
   only — never ahead of implementation." Dean wants the aggregate stack **in `planning/`, tied to but
   not committed inside Type 4**, because Type 2 already aggregates multiple Type 3s and already
   explains how the Type 1 is achieved — so this is the same aggregation job, applied to call-stack
   content instead of narrative status. Explicit: **this is an interim home, "we move it later"** — not
   a final taxonomy decision. Do not read "put it in Type 2" as a permanent ruling.

## What's yours to design (not mine, and not attempted here)

- Whether/how the `current call stack` field's syntax generalizes outside your cluster, and how "only
  affected stacks" gets enforced (a lint rule? a review-time check? left to author judgment?).
  `multi-analyzer-postrefactor-map.md`'s tag vocabulary (`[this PR]`/`[next PR]`) is one candidate
  precedent, though its *scope* (whole-mission tour) is explicitly the wrong shape per Ask 1 — the
  vocabulary might still be worth reusing even though the scope isn't.
- Where exactly inside a Type 2 doc an aggregate call-stack section goes, and what triggers updating it
  (every Type 3 that lands? every Type 6 that reviews one?).
- Whether this needs a new field name, reuses `current call stack`, or something else entirely.
- The eventual promotion of "source trace" as its own named type (`doc-and-session-model.md:114`,
  still unpromoted) — related but Dean did not fold it into this ask explicitly; flagging the
  connection so you don't design something that collides with it later.

## Explicitly NOT part of this ask

Dean was clear: **do not touch active-owner Type 1/2/3/4/6 docs to backfill this.** This handoff is
about the *process going forward*, not a retrofit of existing docs. Separately, he authorized
cleanup of docs with **no active owner** — that's being handled directly (a stale pointer added to
`benchmark-observability-plan.md`, per its own supersession; nothing else touched) and is unrelated to
what you're being asked to design here.

## Not mine to do

I have not designed either mechanism, and have not touched any file in your cluster. Full audit:
`planning/doc-coverage-audit-20260816.md` (uncommitted as of this handoff).
