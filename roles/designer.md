# role: designer

token:  designer
owns:   design
reads:  conversation, incidents, code

## What

Produces a design doc (`planning/*-design.md`) from conversation — concepts, algorithms, goals.
Frozen once work starts; amended through an explicit addendum, never edited in place.

## Gaps (skipped, not invented)

No harvested kernel content exists for this role — no pre-existing prose in `CONVENTIONS.md`/
`CODER-CONVENTIONS.md` describes designer behavior specifically, and no skill implements it. Per
Dean's instruction, this gap is skipped rather than filled with invented content. Revisit once real
source material exists (an incident, a memory, or Dean's own statement about how a designer should
behave).

origin: doc-and-session-model.md § Roles
