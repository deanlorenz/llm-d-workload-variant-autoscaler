# Doc ownership boundary

### convention: doc-ownership-boundary-discuss-before-implementing
description: CURRENT.md's 'next step' is a continuity note, not authorization to proceed unattended on a non-trivial implementation task.
scope: any session, especially unattended, deciding whether to act on what a shared doc says
trigger: about to begin a non-trivial implementation task based on CURRENT.md's stated next step
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Discuss before implementing (C20)

**Discuss before implementing.**
Never begin a non-trivial implementation task based solely on what CURRENT.md says is the "next
step." The "Next step" field is a continuity note, not an authorization to proceed. After
resolving the last open task, summarize what was done and ask what to work on next. This applies
even when a detailed plan doc exists — the plan is background for the discussion, not a substitute
for it.

### convention: doc-ownership-boundary-coder-review-docs
description: Coder-authored review docs are out of scope; process-flavored findings go in the handoff to the planner, not a Type 6 doc.
scope: coder agent
trigger: coder learns something process-flavored during its work
status: active
origin: session/CONVENTIONS.md § Handoffs section, Coder-authored review docs are out of scope (C33)

*Coder-authored review docs are out of scope.* Coders ship Type 4 docs (reference
material under docs/) inside their worktree as part of the PR. They never write Type 6
review docs. If a coder learned something process-flavored, it goes in the handoff to
planner, not a Type 6 doc. Type 6 is exclusively external-lens (reviewer, triage,
conversation outcomes).

### convention: doc-ownership-boundary-design-decisions-belong-to-dean
description: Design decisions (naming, string literals, API surface, observable behavior) belong to Dean; surface options rather than deciding unilaterally, elevate forks early, and give structured review summaries.
scope: planner or coder about to make or has made a design choice
trigger: picking between two reasonable options for anything user-visible, or discovering a design fork mid-implementation
status: active
origin: feedback_doc_accuracy_discipline.md

**Design decisions belong to Dean, not the planner or coder.** Any choice involving naming,
string literals, API surface, or observable behavior must be surfaced to Dean before committing
to it — not decided unilaterally in a handoff. Implementation details (where to add a helper,
how to structure a loop) are planner/coder discretion; design choices are not. Concrete trigger:
when writing a handoff and you find yourself picking between two reasonable options (e.g.
"unknown" vs "no-data" vs "error" for a fallback label), stop — write the options with one-line
rationales and ask Dean. Only after Dean answers does the handoff get the chosen value.

**Design evolution is normal — but elevate forks early.** Seeing the implementation sometimes
reveals design gaps; that is fine and expected. The problem is making the fork decision
silently. Surface it as soon as it is noticed, before writing the handoff, not after. This
applies to coders as much as planners/reviewers — a coder fixing a genuine bug can silently
change a formula's semantics as a side effect of the fix, and the bug-fix narrative can be true
and complete as far as it goes while still omitting the second, unrelated decision riding along
inside it.

**Structured review summary before asking Dean to review.** After a coding round, don't just say
"gates green." Provide: decisions made autonomously (with brief rationale — Dean can override),
what the diff adds in behavioral/observable terms (not file names), and what to focus on — the
parts Dean most needs to look at. This replaces "scan the raw diff"; Dean should not have to read
code to discover that a design choice was made.

**Handoff precision for small changes.** A precise handoff lists every artifact to touch —
including pre-existing doc descriptions that need updating — not just the new additions. "Update
cycle-log.md" is not precise; "in cycle-log.md table line 44, change the supply description from
X to Y" is precise. A coder given a small-change handoff should not have creative latitude on
what to update — every change is specified.

**Coders write docs against finished code.** Docs written by the planner during design are
design intent, not a finished reference — the coder writes the actual doc content after the code
exists, verified against the real variable/expression, not copied verbatim from the plan's
necessarily-imprecise draft language.

### convention: doc-ownership-boundary-formula-fork-corollary
description: A bug fix that also changes a plan-specified formula's output for an input class the plan's examples didn't cover must be flagged as its own decision point, not folded silently into the bug-fix narrative.
scope: coder fixing a bug in code that implements a plan-specified formula/algorithm
trigger: a bug fix requires deviating from a plan's literal formula/algorithm
status: active
origin: governance-follow-ups.md § 2026-07-27 PR C silent formula-semantics fork; feedback_doc_accuracy_discipline.md § Design forks apply to coders too

**Concrete case.** A coder fixed a genuine warm-up bug (a demand formula needed to read tracked
shape data instead of live per-cycle data) and, as a side effect of that data-source fix, also
silently changed the formula's *weighting semantics* — the plan specified a rate-weighted average
across all replicas; the fix shipped an equal-weight average across a subset of variants instead.
The status-file note documented the source-of-data change but not the weighting-scheme change, so
the divergence from the plan's literal spec was invisible until a reviewer re-derived the formula
by hand against the plan's wording. Dean's ruling: unacceptable — coders must never do this
silently; they can suggest it as a decision for the planner or for Dean, not hide it.

**How to apply.** When a bug fix requires deviating from a plan's literal formula/algorithm, ask
"does my fix change the *output* for any input the plan's examples didn't cover?" before writing
it up. If yes, that is a second, separate decision fork — name it explicitly as its own paragraph
with its own "is this intended?" question, even inside a status file that is otherwise reporting
the fix as already-resolved. Do not let a real bug fix's narrative absorb an unrelated semantic
change.
