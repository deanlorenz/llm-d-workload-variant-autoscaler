# role: confirm

token:  confirm
owns:   review of a code spec
reads:  code spec, epic plan, design

## What

Checks that a code spec correctly instantiates the epic plan and design — "design → plan" confirmation,
the layer immediately below Dean's own plan-finalization. One of the three roles that produce a review
artifact (with `verify` and `pr`).

## Open, unresolved — build together with verify

`s-design-review` is the closest existing skill, but it is explicitly ambiguous between this role and
`verify` (`doc-and-session-model.md` § Skill surface: "confirm or verify — ambiguous... resolve when
splitting"). Per Addendum 13's build order, this role should be designed together with `verify`, not
separately — separating them *is* the work.

## Gaps (skipped, not invented)

No harvested kernel content exists specific to confirm (vs. the generic 4-stage review pipeline both
confirm and verify draw on). No rule states this role's own permission boundary independent of
verify's.

origin: doc-and-session-model.md § Roles; atomic-step-protocol-design.md § The four reviews are
distinct
