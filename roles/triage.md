# role: triage

token:  triage
owns:   a fixup code spec, or additions to an existing one
reads:  PR comments, CI output

## What

Opens on first external review, not at PR creation. Its output becomes a new code spec, additions to
the existing one, or both.

## Confirmed live gap — existing skill's output type doesn't match this role's own "owns"

`s-pr-triage` is a clean 1:1 mapping mechanically (fetches CI status + all comment sources, synthesizes
per-commenter status, derives pending actions) — but it produces a review/summary doc
(`planning/PR<N>-review.md`), not the fixup code spec this role is defined to own. Found during the
2026-08-17 role-design research (Addendum 13, Finding 4). Converting a triage doc into a code spec is
currently a manual step with no rule or skill covering it. Fix as part of building this role.

origin: doc-and-session-model.md § Roles, § Kinds the audit found (fixup code spec precedent:
`PR1266-fixup-effectiveEnabled.md`); atomic-step-protocol-design-addendum-13.md Finding 4
