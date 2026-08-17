# role: sync

token:  sync
owns:   session state
reads:  handoffs

## What

The only writer of session state (`CURRENT.md`, `session/history.md`). Single-writer model: every
other role submits a `sync__` handoff rather than editing CURRENT.md directly. `spec` and `sync` share
their first letter and diverge at the second — never abbreviate either.

## Second-richest existing coverage

Real, harvestable kernel content exists: `harvest-classification.md` C26 ("sync session mechanics,
`/sync-current`, `.DONE` + `git rm`") is already classified `role:sync`. `s-sync-current` is the
most-actively-maintained skill of all ten (multiple 2026-08-17 correction comments already landed in
its body).

## Confirmed live gap — the token has never been used

0 of 302 handoff files use the `sync` token, despite `s-sync-current` being the most production-ready
skill that exists. Found during the 2026-08-17 role-design research (Addendum 13, Finding 3). `plan__`
absorbs work that should be `sync__` — likely naming confusion between `plan` and `sync`, per
`doc-and-session-model.md` § Audit evidence, not confirmed. Worth understanding before harvesting more
sync content, not just transcribing C26 as-is.

## Open, not re-checked

C8/C13 (CURRENT.md bounded-shape rules) were originally classified `role:sync`, then reclassified to
`conv:current-md-format` on the reasoning that no role holds standing behavioral posture. Whether C26
(the one row that does survive as `role:sync`) holds up under that same test has not been
independently re-verified.

origin: doc-and-session-model.md § Roles, § Audit evidence; harvest-classification.md C26, C8/C13;
atomic-step-protocol-design-addendum-13.md Finding 3
