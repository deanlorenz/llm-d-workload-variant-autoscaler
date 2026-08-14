# Addendum 5 — an always-loaded convention-trigger index, anchored to CLAUDE.md's import chain

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10), specifically § Micro-conventions' comparison table (*"conventions must **not** be
auto-loaded"*) and § Addressing and fetch. The parent is **not edited**: this is the amendment channel
it names. Additive — proposes a new, small always-loaded layer alongside the existing fetch-on-demand
mechanism, not a replacement for it.

**Status: proposed 2026-08-13, with supporting measurement; mechanism not yet built, one open sub-question
(recognition reliability) explicitly unresolved.**

---

## What prompted it

Dean, reasoning about two existing session mechanisms:

> *"we have 2 mechanisms — 1. the memory-like triggers, semantic, based on good behavior. 2. the
> hooks-like trigger, gates, based on enforcement. ... The whole idea of the per-step atomic-rules is to
> make sure they are not skipped/forgotten ... I don't think it is a 1 vs 0 problem, there is a middle
> point. We can still load wholesale, but we don't need the full, detailed, verbose prose. The details
> belong in the full conventions — fetched on demand when that rule is fired. The trigger needs to be
> loaded wholesale."*

The architectural question raised: how do we create our own reliable triggers — small enough to always
sit in context, capable of firing a full on-demand lookup without needing a step to have explicitly
cited the rule in advance — for the "good behavior, semantic" half specifically (the hook-enforced half
is already covered per the parent design's Enforcement section and its planned M1.1 hooks).

## The measurement that changed the frame

The parent design's own comparison table (§ Micro-conventions) states conventions must not be
auto-loaded, contrasted directly against memory's `MEMORY.md` always-loaded index. Before proposing
anything, the actual token cost was measured rather than assumed:

| | Measured value |
|---|---|
| `CONVENTIONS.md` + `CODER-CONVENTIONS.md` combined (today, always loaded in full) | ~17,900 tokens |
| A `MEMORY.md`-style one-line-per-rule index, sized from real per-line cost (234 chars/line measured from the actual `MEMORY.md`), across the 65 rules identified in [`harvest-classification.md`](harvest-classification.md) | ~3,770 tokens |
| Per-rule full-body fetch cost, sized from 3 real memory files' average (3,448 chars) | ~860 tokens, paid once per rule actually needed per session |

**The always-loaded index is ~4.7× cheaper than today's two files, not more expensive** — the original
"must not be auto-loaded" call appears to have conflated *the index* (cheap, what memory actually
auto-loads) with *full convention bodies* (expensive, correctly still fetch-on-demand only — this part
of the existing design is unaffected and correct). A session that only ever needs a handful of the 65
rules in one pass comes out ahead of today's two-full-files-always model; only a session that ends up
needing most or all 65 rules would approach the same total cost, and even then no worse.

**This does not reopen § Addressing and fetch's fetch-mechanics** — `sec`/`conv`, heading-addressing,
multi-name-per-call, loud-failure-on-unresolved-name all stand exactly as designed. This addendum adds a
new *discovery* layer on top: today, a rule is discovered either because a step's `conventions:` field
named it (anticipated case) or not at all (unanticipated case — exactly the gap Addendum 1's
proceed-and-mark mechanism exists to absorb, since an unanticipated ambiguity is precisely what forces a
coder into a judgment call). A reliable, cheap, always-present trigger index is aimed at shrinking how
often the unanticipated case occurs, by giving every session — not just a coder executing a cited step —
a standing chance to recognize "there's a named rule for this" even when nothing told it to look.

## Where the index should live — resolved

Two candidate delivery mechanisms were compared, using Claude Code's actual documented behavior
(researched via the `claude-code-guide` agent, sourced from `memory.md` — see citations below), not
assumption:

- **`MEMORY.md`'s mechanism**: loaded once at session start (capped at the first 200 lines / 25KB),
  **never automatically re-injected — not even after compaction.** A long session's index entry can
  simply decay out of practical attention the same way any other early-context content does, with no
  refresh at all. This is a real, documented weakness in the exact model that inspired the question, not
  a solved reference case.
- **Root `plans/CLAUDE.md`'s mechanism** (the existing import chain that already delivers
  `CONVENTIONS.md`/`CODER-CONVENTIONS.md` today): injected as a user message at session start, **and
  automatically re-read from disk and re-injected after every `/compact`.** Nested/path-scoped
  `CLAUDE.md` content only reloads lazily on a matching file touch, so this compaction-survival property
  is specific to the *project-root* file, not nested imports generally.

**Decided:** the convention-trigger index should be anchored to `plans/CLAUDE.md`'s import chain (a
small, dedicated file it imports, or content inlined there directly) rather than mimicking `MEMORY.md`'s
mechanism — it inherits the compaction-survival property for free, which is the more reliable foundation
given the index's whole purpose is to still be effectively present arbitrarily late in a long session.

## What the index actually contains — not yet designed in detail

Sketch only, following the existing convention marker's own fields (§ Micro-conventions):

```
### convention: commit-dco
description: every commit carries a DCO Signed-off-by trailer
trigger:     BEFORE commit
```

An index line would plausibly be `name` + `description` + `trigger` — the same three fields already
defined per-convention, just surfaced as one line each in a compact always-loaded list, with the full
body (rationale, `origin:`, examples) staying exactly where it is today, fetched via `conv <name>` only
when the index line's match causes a session to look.

## Still open — the harder half, not resolved here

**Recognition reliability.** The index solves *size* and *survival*; it does not solve whether the
model reliably *notices* a match between the current situation and an index line — this is the same
failure mode memory already has (a relevant memory line sits in context but doesn't get recalled because
its wording doesn't evoke the right association, or attention has simply drifted past it despite the
text technically still being present). Dean's own "we shall see" on the related reaffirmed-bundle
question (Addendum 4) applies here with equal force. No mechanism is proposed to harden this — it is
recorded as the open half of the problem, not glossed over because the token-cost half turned out
favorable.

**Relationship to Addendum 4.** That addendum's "reaffirmed rule bundle" question (should certain
standing rules be re-surfaced specifically at the moment a risky action becomes plausible, e.g. at
commit/push time) and this addendum's always-loaded index are related but distinct: Addendum 4 is about
*re-affirming specific, already-identified* standing rules at a specific moment; this addendum is about
*discovering* a rule at all, in a situation nobody anticipated citing it for. A convention could plausibly
need both — appear in the always-loaded index for discovery, and separately be tagged for reaffirmation
at specific trigger moments — but that composition is not designed here.

**Not yet decided:** exact file location and name; whether it is one flat list or grouped by role/scope;
whether `conv-list`'s existing computed-index mechanism (§ Micro-conventions: "no stored index... so it
cannot drift") can generate this file automatically rather than requiring separate maintenance, which
would resolve the "does the index drift from the actual convention set" question before it becomes one;
and how (or whether) this composes with the eleven-role model's own kernel files once those exist.

## Refinement — a two-level index, project-scoped (Dean, 2026-08-14)

Two related improvements on the single-level index above, proposed together:

> *"we load some index. always in context. that index must trigger fetch of the full rules when needed.
> each item can be broad. trigger a fetch of a sub index. only when sub index is triggered actual full
> rule is read. the sub index is refreshed (if needed) every time the main index is triggered. If not
> refreshed (not needed anymore) it drifts away. We pay the full penalty only if all rules are triggered
> and then we are no worse than bulk loading them up front as we do today."*

**Three tiers, not two:**

1. **Main index** — always loaded, anchored to `plans/CLAUDE.md`'s import chain (per the decision
   above). Entries are **broad categories**, not individual rules — e.g. `git-safety`,
   `worktree-and-scope`, `inter-session-comms`, `coding-and-verification`, `authoring-and-process`
   (a plausible first grouping of the 17-20 conventions in `harvest-classification.md`; not finalized).
   Because categories scale far slower than individual rules as the rulebook grows, this tier's size is
   much more stable than a flat 65-entry index would be.
2. **Sub-index** — one per category, **memory-shaped but project-scoped**: same shape as a memory
   (description that triggers recall; body with why/how-to-apply) but stored under `plans/`
   (`conventions/` or a sibling directory), not in the global `~/.claude/.../memory/` tree. Dean's own
   reasoning for keeping it project-scoped rather than global memory: *"we don't need a global memory
   for per-project rules... I don't like it as much as per project scope."* A genuinely global memory
   that just says "go read sub-index X from this project" would work mechanically but was explicitly
   rejected on scope grounds, not mechanism grounds. **Lean, not a final decision** — *"This is why I
   lean toward memory-shaped. We can try and see how it works."*
3. **Full convention** — unchanged, fetched via `conv <name>` exactly as designed today, only once the
   sub-index narrows to a specific rule.

**The cost property, precisely.** The main index is a small, fixed, permanent cost. A sub-index is paid
only when its category is actually touched — and once loaded, it is not actively pinned in place; it
simply occupies context and its practical relevance fades the same way any other content's does.
Re-triggering the main index for that category re-pays the sub-index cost (a "refresh" that happens by
relevance, not on a schedule) if it's still needed, or the sub-index just drifts out of effective
attention if it's not. **Worst case bound: if every category and every rule in it ends up triggered in
one session, total cost converges to today's bulk-load-everything-up-front model — never worse, only
better in the common case where most rules are never needed in a given session.**

This composes cleanly with the single-level index's own token math above: the main index is cheaper
still than a flat 65-line index (fewer, broader entries), and the sub-index tier absorbs the "pay per
rule actually needed" cost at a coarser, more naturally-scoped grain (a whole category's worth of
related rules recalled together, which also plausibly improves recognition — a coder deep in a git
operation is likely to need more than one git-safety rule at once, so loading the category's sub-index
in one shot is not wasted the way loading 4-5 unrelated single-rule indices would be).

**Not yet decided:** the actual category boundaries (the five-category sketch above is illustrative, not
adopted); whether "try and see how it works" means building a small pilot with 1-2 categories before
committing the whole rulebook to this shape; and whether the sub-index file format should be identical
to a real memory file's frontmatter (`name`/`description`/`metadata: type`) for tooling reuse, or a
distinct shape specific to this project. Recognition reliability (§ Still open, above) applies at both
the main-index-to-sub-index hop and the sub-index-to-full-rule hop — two chances to miss a match instead
of one, which is a real cost of the extra tier not to lose sight of against its token-cost benefit.

## Sources

Claude Code's CLAUDE.md/memory injection behavior, per `claude-code-guide` agent research against
`memory.md` (2026-08-13): CLAUDE.md delivered as a user message after the system prompt, loaded once at
session start; nested/path-scoped `CLAUDE.md` reloads only lazily on a matching file touch; project-root
CLAUDE.md specifically is re-read from disk and re-injected after `/compact`; `MEMORY.md` is loaded only
at session start, capped at 200 lines/25KB, with no automatic re-injection at any point thereafter.
