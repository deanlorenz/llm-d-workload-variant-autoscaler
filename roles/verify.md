# role: verify

token:  verify
owns:   review of code
reads:  code first, then the code spec

## What

Checks that the code matches what the spec promised — "plan → code" verification, the mirror of
`confirm`'s "design → plan" check. Reads code first, then the spec: an anti-anchoring rule, not
sequencing — reading the spec first shows what was promised instead of what was built.

## Confirmed live defect — the existing skill violates this role's own core rule

`s-design-review`'s actual step order reads design/plan (its Step 3) *before* code (its Step 4) — the
literal inverse of verify's mandated order. Found during the 2026-08-17 role-design research
(Addendum 13, Finding 1). If this skill is treated as verify's current implementation, it is actively
violating the role's own defining rule today, not just in an unbuilt design. Fix this as part of
building this role, not deferred.

## Open, unresolved — build together with confirm

Same skill-sharing situation as `confirm` — see that file. Separating the two roles is the actual
design work for both.

origin: doc-and-session-model.md § Roles; atomic-step-protocol-design.md § The four reviews are
distinct; atomic-step-protocol-design-addendum-13.md Finding 1
