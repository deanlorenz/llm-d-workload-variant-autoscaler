from: review (ta-anchor-dynamic-refresh internal reviewer)
to: planner
session: four pre-existing main-side §4a-class leaks, found and analyzed but never routed anywhere

`planning/governance-follow-ups.md` § "Pre-existing `main`-side §4a leaks (backlog, from PR C round-4)"
already tracks two inherited leaks (`throughput-analyzer.md`'s `plans/planning/TA-Plan.md` path,
`analyzer_test.go`'s "Regression test for F1"). Re-verified both today at `ta-anchor-dynamic-refresh`'s
tip `6d55fbd7` — byte-identical to `upstream/main`, so still accurate and still not this branch's to fix.

Four more of the same general shape were found and analyzed in depth across
`planning/ta-anchor-dynamic-refresh-review.md` and `planning/ta-anchor-dynamic-refresh-PENDING-EDITS.md`,
each independently concluded to need Dean's issue-filing direction, and none of them made it into
`governance-follow-ups.md` or any other actionable list. Surfacing them now rather than leaving them
buried in review-doc prose.

## The four

1. **`internal/engines/analyzers/throughput/constants.go:85`** — `"the decode-dominated regime
   (N_pre ≈ 1, TA-supply.md §3.1)"`. A plans-branch Type-1 doc citation plus a section identifier, in a
   shipped production comment. Verified present at PR-1 base (`075a208e`) and at `upstream/main` —
   inherited, same class as the two already tracked.
2. **`internal/engines/pipeline/analyzer_helpers.go:411,:419`** — `"Design § Architecture/D"` and `"per
   design A10"`. Same class, same inheritance status.
3. **`cmd/main.go:165-169`** — a dead public link: the comment sends a reader to
   `https://github.com/llm-d/…/blob/main/docs/user-guide/configuration.md`, which does not exist
   (`docs/user-guide/` contains only `monitoring.md` and `sglang-backend.md`). Not a §4a token — a
   different defect class (a 404 shipped to users) — but the same "found, never routed" gap applies.
4. **`docs/developer-guide/throughput-analyzer.md:609`** — a broken relative link:
   `` [`saturation-scaling-config.md`](../saturation-scaling-config.md) `` resolves to
   `docs/saturation-scaling-config.md`, which doesn't exist; the real file is
   `docs/developer-guide/saturation-scaling-config.md`. Two-character fix. Unlike the other three, this
   one sits in a file `ta-anchor-dynamic-refresh`'s own C9 commits already touch — worth flagging as
   foldable into that branch's own docs commit rather than a separate PR, if it hasn't landed already by
   the time this is read.

## What I'm asking

Fold 1–2 into `governance-follow-ups.md`'s existing list (same section, same "not this branch's to fix"
framing). Items 3–4 are a different defect class (broken links, not plans-branch tokens) — your call
whether they belong in the same doc under a new subsection or somewhere else; I'm not proposing where,
just that they stop being undiscoverable outside a 4000-line review doc. None of this blocks PR-2 — it's
all pre-existing on `main` today, PR-2 just happened to be the branch whose §4a sweep surfaced it.
