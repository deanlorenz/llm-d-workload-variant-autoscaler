# role: spec

token:  spec
owns:   code spec; push, PR open, CI watch, immediate corrections
reads:  epic plan, design, reviews

## What

Owns one executable unit of work (typically a PR, not always known as one in advance — hence "spec"
not "PR plan"). Owns landing, not just authoring: judges push-readiness, performs the push, opens the
PR, follows CI, triggers immediate corrections. Coders never push — this role does.

## Open discrepancy — not resolved here

`atomic-step-protocol-design.md`'s "four reviews" table says External review reads "the code spec";
`doc-and-session-model.md`'s role table says `pr` reads "the PR." Found during the 2026-08-17
role-design research (Addendum 13, Finding 5) — may be the same role described inconsistently, or two
genuinely different things. Not resolved here.

## Gaps (skipped, not invented)

No standing kernel content harvested yet. Real, fetchable convention material exists (pre-push
checklist, no-push-without-confirmation, warn-before-pushing-to-open-PR, no-GitHub-without-
confirmation, force-push-only-after-rewrite — all in `session/CONVENTIONS.md`) but harvesting that
into `conventions/` is Step 2's job, not this file's. `s-plan` implements this role conflated with
`epic` — same skill, undifferentiated.

origin: doc-and-session-model.md § Roles, § Artifact types
