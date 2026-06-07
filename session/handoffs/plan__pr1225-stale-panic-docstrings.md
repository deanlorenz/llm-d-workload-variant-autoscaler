from: plans (triage)
session: pr1225-stale-panic-docstrings

## What changed

ev-shindin commented on 2026-06-07 that four stale "panic" references remain after
commit 6339e495 ("RegisterAnalyzer returns error instead of panic"). The commit
correctly updated RegisterAnalyzer's own docstring and implementation but missed
cross-references in struct field comments and StartOptimizeLoop — none of them were
in the diff context of the changed function lines.

## Fixes needed (multi-analyzer-registration branch)

**internal/engines/saturation/engine.go** — 3 places:

1. Line 152 (struct field comment, `analyzers`):
   "further RegisterAnalyzer calls panic."
   → "further RegisterAnalyzer calls return an error."

2. Line 166 (struct field comment, `started`):
   "calls panic so the contract \"register before Start\" is enforced rather than
   just documented."
   → "returns an error so the contract \"register before Start\" is enforced rather
   than just documented."

3. Line 279 (StartOptimizeLoop docstring):
   "flipped so subsequent RegisterAnalyzer calls panic."
   → "flipped so subsequent RegisterAnalyzer calls return an error."

**internal/engines/saturation/engine_register_test.go** — 1 place:

4. Line 142 (test It-block comment):
   "any post-Start RegisterAnalyzer panics before mutating anything."
   → "any post-Start RegisterAnalyzer returns an error before mutating anything."

Note: line 35 ("Configurable to record calls, return an error, or panic.") and
lines 40/47/48/242-256 in the test file are about spyAnalyzer's own panic mechanism
(used to simulate panicking analyzers in recovery tests) — those are still correct
and must NOT be changed.

## Deliverables

- Amend or add a fixup commit on top of origin/multi-analyzer-registration tip (6339e495)
  touching only the four comment lines above. No logic changes.
- Run make test + gofmt before the commit.
- Write a handoff back to plan with the commit sha so CURRENT.md / PR Status can
  be updated and a force-with-lease push to origin confirmed with Dean.

## Update CURRENT.md

- PR #1225 row: status remains "OPEN, awaiting approval"; note "docstring fixup
  in progress" instead of "ready-for-review".
- Blocked-on entry for #1225: update to "docstring fixup committed; awaiting
  force-with-lease push + ev-shindin re-review".
