# role: epic

token:  epic
owns:   epic plan
reads:  design

## What

Takes a design and breaks it into units of work — turns abstract items into a concrete code roadmap.
The unit is typically a PR. Mandatory for multi-PR work; skipping it is where abstract design turns
directly into code with no recorded alternatives.

## Open discrepancy — not resolved here

`CONVENTIONS.md`'s old Type-2 framing calls this artifact "transient — no longer needed after the
mission completes." `doc-and-session-model.md` calls it "durable, not transient." Direct
contradiction between two authoritative docs, found during the 2026-08-17 role-design research
(Addendum 13, Finding 5) — not resolved by this harvest pass. Flagged for Dean.

## Gaps (skipped, not invented)

No harvested kernel content exists. `s-plan` implements this role conflated with `spec` (see
`roles/spec.md`) — the same skill covers both, undifferentiated.

origin: doc-and-session-model.md § Roles, § Artifact types
