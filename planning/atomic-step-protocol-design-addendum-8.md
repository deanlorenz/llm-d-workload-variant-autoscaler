# Addendum 8 — plans-tooling becomes the main dev branch for plans, not a throwaway kickoff worktree

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (design, FINAL, frozen
2026-08-10) § Migration, specifically the "Own worktree for the tooling, copied over at an atomic
deliberate kickoff" decision recorded in that design's own digest and § Decided list. The parent is not
edited: this is the amendment channel it names.

**Status: decided by Dean, 2026-08-15.**

---

## What changed

The original plan (per the frozen design and its digest) treated `plans-tooling` as a **throwaway
development worktree**: build the migration tooling there in isolation, then copy the finished result
into `plans/` in one deliberate kickoff action, after which `plans-tooling`'s own development history
would stay behind on its own branch, not become part of `plans`'s ongoing history.

Dean, 2026-08-15: *"We are going to use plans-tooling for all code work and for all rules migration
work. It will become our main dev branch for plans."*

This is a real scope change, not a rewording:

- `plans-tooling` is no longer scoped to *just* the tooling spec's four scripts (`sec`/`conv`/
  `conv-list`/`conv-lint`) plus the authoring spec's three (`conv-new`/`conv-edit`/`conv-rename`). It
  becomes the working branch for **all** code work on the plans tree and **all** rules-migration work
  going forward — a durable branch, not a scratch worktree with a planned end-of-life copy-over.
- The "atomic deliberate kickoff copy" step (moving `plans-tooling`'s content into `plans/` in one
  action, per the design's own § Decided list) is **superseded by this decision** — if `plans-tooling`
  *is* the dev branch now, there may be no separate copy-over step at all, or it may become a
  fast-forward/merge instead of a copy. Not resolved here; flagged as an open consequence below.

## Immediate practical effect

A coder session and an internal code-reviewer session are being started in `plans-tooling`
(2026-08-15), with the coder's first task being the `conventions-authoring-spec.md` slice
(`conv-new`/`conv-edit`/`conv-rename`, S1-S3) — the natural next step after the already-landed
read-side tools, on a spec already reviewed as good. This addendum records the branch-role change that
makes that assignment durable rather than scoped to one throwaway task.

One untracked leftover exists in the worktree from an earlier trial harvest pass:
`conventions/code-deletion.md`, never committed. Flagged for the coder to check in about rather than
silently absorb or discard, since its provenance (a planner's own trial, not part of any spec) isn't
something a coder should resolve unilaterally.

## Still open — consequences not yet worked out

- **What happens to the planned "copy into `plans/`" kickoff step**, now that `plans-tooling` is meant
  to persist as the dev branch rather than be retired after one copy. Candidates: `plans-tooling`
  effectively *becomes* `plans` (a rename/merge), or `plans` stays the canonical branch and
  `plans-tooling` becomes a long-lived feature branch that periodically merges forward — not decided.
- **Governance implications** — `session/CONVENTIONS.md`'s existing rules about who may write to
  `planning/` (multi-writer) versus `session/` (single-writer via sync) were written assuming `plans` is
  the one active branch for this kind of work. Whether those rules need restating for a dual-branch
  (`plans` + `plans-tooling`) reality, or whether `plans-tooling` simply inherits them as-is once it's
  understood as "the same branch, different name," is not addressed here.
- **DCO/gate posture — resolved for now, revisit later.** `conventions-authoring-spec.md`'s own
  Prerequisites say "No DCO on this lineage. Never push." for `plans-tooling`, written under the
  throwaway-worktree assumption. Dean's call, 2026-08-15: **keep this as the default for now** — nothing
  about the main-dev-branch decision itself changes push/DCO rules; the coder launched today stays
  local-only, no DCO required, until Dean explicitly revisits this Prerequisite. Not a permanent answer,
  just the safe default while the branch-role change's other consequences are still being worked out.
