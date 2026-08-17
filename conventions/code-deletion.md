# Code deletion

### convention: code-deletion
description: Every code deletion must be classified DEPRECATED or DEFERRED in the handoff to the planner.
scope: any coder removing a file, function, struct, or significant code block
trigger: removing or substantially neutering existing behavior
status: active
origin: session/CODER-CONVENTIONS.md §4b, session/CONVENTIONS.md "Document every deletion"

This entry combines two rows that state the same rule from two sources with differing detail
(the CODER-CONVENTIONS.md version is fuller, with a concrete example — quoted below as primary;
the CONVENTIONS.md version follows as it adds the planner-side capture destination in its own
words).

From session/CODER-CONVENTIONS.md §4b:

When your task removes a file, function, struct, or significant code block, classify the
removal in your handoff to the planner. Use one of two labels:

**DEPRECATED** — the functionality is intentionally gone; no future work planned.
Example: `// DEPRECATED: itlKnowledgeStore — removed; functionality superseded by lastFittedB (in-session only)`

**DEFERRED** — the code is not ready yet (no consumer, engine contract not in place,
scope creep) but the *design intent* is worth preserving. Include in the handoff:
1. What the code did (one paragraph — enough to re-implement from scratch)
2. Why it was removed now
3. Where the future version should land (GitHub issue ref, plan-doc item, or "file issue")

The planner captures DEFERRED items in the relevant Type 1/Type 3 doc and in
CURRENT.md Issues to Open. Nothing is silently deleted — a future session must be
able to recover the design intent from plan docs alone.

This rule applies equally to partial removals: removing a gate (e.g. an `if anyGPSMismatch`
block) that was wired to produce real behavior counts as a deletion of that behavior and
must be classified. "The code still compiles and the tests pass" is not the bar — the bar
is "will a future developer know this feature existed and why it was removed?"

From session/CONVENTIONS.md § "Document every deletion — deprecated or deferred":

When a task plan removes a file, function, struct, or significant block of code, the plan
must classify the removal:
- **Deprecated** — functionality intentionally removed; no future work planned. State why.
- **Deferred** — functionality removed because it is not yet fully ready (no consumer,
  engine contract not in place, etc.) but the design intent is worth preserving. State what
  it did, why it was removed, and where the future version should land (issue or plan item).

The coder writes the classification in the handoff; the planner captures deferred items in
the relevant Type 1 or Type 3 doc and in CURRENT.md Issues to Open. Nothing is silently
deleted — a future session must be able to recover the intent from the plan docs alone.

**Incident basis.** During #1250 TA3 development, several valuable features were silently
removed with no classification at removal time: the ITL knowledge store, the GPS-mismatch
SpareCapacity gate, the EPP-absent SC gate, the FreshnessStatus staleness wiring, and the
`has*` throughput sentinels. None were documented as deprecated or deferred, so future sessions
had no way to know what was intentionally gone versus what should come back. This rule applies
equally to partial removals — removing a gate that was wired to produce real behavior counts as
a deletion of that behavior and must be classified. "The code still compiles and the tests
pass" is not the bar; the bar is "will a future developer know this feature existed and why it
was removed?"
