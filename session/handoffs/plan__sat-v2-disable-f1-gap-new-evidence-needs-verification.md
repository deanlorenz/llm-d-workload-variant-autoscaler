from: sync-session (plans)
to: plan (owner of ta-anchor-dynamic-refresh-plan.md / PR-2's internal review)
session: sat-v2-disable-f1-gap-new-evidence-needs-verification

## What this is

A finding, not a resolution. Do not treat this as "the F1 gap is fixed" — it needs your verification
and, if confirmed, a numbered finding in PR-2's own review doc before CURRENT.md or anyone else
treats it as settled. Dean's own framing: "the disable_sat [entry] should sit there until we merge
into main and can safely say it is resolved. The problem is not that it is sitting in CURRENT but
that it was not marked as being resolved in PR-2 and needs verification."

## Background

`session/CURRENT.md` has carried an open item since 2026-08-03: `saturation/engine_v2.go`
unconditionally prepends the saturation result and `effectiveEnabled` only skips it by name, so
`saturation:{enabled:false}` was a silent no-op (the "F1 pre-analysis-extraction gap"). This blocked
`wva-analyzer-lifecycle-plan.md`'s Half B (genuinely disabling saturation).

## What I found, 2026-08-16, reading code directly

- `Main/internal/engines/saturation/engine_v2.go:147` (confirmed on `main`, tip `bebbe88f`, not
  just a branch): `satVotes := len(config.Analyzers) == 0 || effectiveEnabled(domain.SaturationAnalyzerName, config)`.
  Saturation is still computed and appended as an "identity carrier" but tagged
  `Enabled: satVotes`.
- `analyzer_helpers.go:341-344`'s `votingResults()` filters strictly on `e.Enabled && e.Live` before
  the RC/SC combine math runs — from reading the code alone, a config-disabled saturation entry is
  excluded from voting, not just cosmetically marked.
- `git log -S'satVotes := len(config.Analyzers)'` on `main` attributes this to `57f3fe64` (PR-1
  #1516, merged 2026-08-07) — landed as a side effect of PR-1's analyzer-enablement work, not as a
  standalone F1 commit anyone tracked as "the F1 fix."

## What I have NOT done, and why this is a handoff instead of a CURRENT.md close-out

- **Not verified against PR-2's actual test suite.** I read the mechanism; I did not run or find an
  existing test that exercises `saturation:{enabled:false}` end-to-end and confirms RC/SC actually
  changes as expected.
- **Not confirmed this was an intended, reviewed fix for the F1 gap specifically** — it may be an
  incidental side effect of PR-1's analyzer-enablement work that happens to also satisfy F1's
  requirement, in which case it may have its own untested edge cases nobody has looked for
  (interaction with `Live`, with the "identity carrier" append when `Analyzers` list is empty vs.
  explicit, etc.).
- **PR-2 (`ta-anchor-dynamic-refresh`, #1523)'s own internal review is already marked
  "clean (Findings 76/77/78)"** — this would be a new finding, not yet numbered, not yet in that
  review doc. I have not added it there; that's not my write scope, and per this project's own
  review-agent role boundary, this needs someone acting as reviewer, not sync, to add it properly.

## What I'm asking

1. Verify: does a config that sets `saturation:{enabled:false}` actually produce the expected
   RC/SC behavior end-to-end on PR-2 (or `main`, since the mechanism is already there)? Existing
   test coverage, or a new test if none exists.
2. If verified, add a numbered finding to whichever review doc is appropriate (PR-1's own review
   was already FINAL before this was noticed, so this may belong as a new finding on PR-2's review,
   or as a fresh standalone note — your call as the owning planner) stating explicitly that the F1
   gap is closed, by which commit, and how it was verified.
3. Only once that's done should CURRENT.md's sat_v2 entry be updated to say resolved — I've
   corrected my own earlier overstatement there already (I initially wrote "RESOLVED," which was
   wrong; it now says "STILL OPEN — new evidence found, needs verification").

No urgency implied — Dean's own framing was corrective, not "drop everything," but wanted this
routed to whoever can actually verify and document it rather than left as an unrouted CURRENT.md
note.
