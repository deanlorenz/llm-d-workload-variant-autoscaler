name: micro-rules-migration
id: (see this session's own transcript)
role: planner
branch: plans (this status file); plans-tooling (the actual work)
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans-tooling
owned_doc: plans-tooling/planning/micro-rules-migration-plan.md
task: Dean's 5-step overnight mandate (2026-08-17) -- harvest CONVENTIONS.md/CODER-CONVENTIONS.md
  and memories into the conv/coll micro-rules mechanism; build entry points; run a coverage check.
status_file: session/status/micro-rules-migration.md

last_update: 2026-08-17T07:00:00Z (approximate -- see plans-tooling git log for exact commit times)
state: idle (all 5 mandate steps substantively complete; explicitly open items remain, listed below)
current_step: none -- parked after finishing the autonomous overnight run
notes: freeform below

## What happened, in one paragraph

Dean's instruction: "we now have many many docs... you can try to fulfill the overall mission as
best as you can and I can review... easier to correct later." Five steps: (1) define the 11 roles,
(2) harvest CONVENTIONS.md + CODER-CONVENTIONS.md + memories + governance-follow-ups.md, (3) fetch
triggers, (4) entry points (role-collections, step-collections, pre-packaged prompts), (5) a
coverage check. All done tonight in `plans-tooling` (Addendum 8's migration dev branch, not
`plans` -- `plans/CLAUDE.md` untouched, per Dean's explicit "build alongside, do not flip yet").
Every commit pushed to `origin/plans-tooling` as work proceeded (confirmed empty
`origin/plans-tooling..plans-tooling` diff at park time).

## State, per step (full detail in the owned doc's own checklist)

- **Step 1** -- 11 role specs, thin by design. `dean` (the human) correctly has no kernel.
- **Step 2** -- full harvest into `conventions/` (22 topic files, ~80 entries), two background-coder
  dispatches (Step 2a: CONVENTIONS.md/CODER-CONVENTIONS.md; Step 2b: ~78 memories +
  governance-follow-ups.md), **both independently verified** by me, not trusted from the coder's own
  report alone -- `conv-lint.sh` clean, source files byte-diffed as untouched, verbatim spot-checks
  passed.
- **Step 3** -- free, confirmed as a side effect of Step 2's own `conv-new.sh` calls.
- **Step 4** -- new tools `coll.sh`/`coll-list.sh`/`coll-lint.sh` (a `### collection: <name>` marker,
  `members:` field, prefix-matching via a trailing `*` against declared convention names -- needed
  because this codebase's multi-entry topics use a `<topic>-<subname>` naming pattern). 11
  role-collections (all 11 roles, `dean` excluded), 8 step-collections, 2 pre-packaged prompts.
- **Step 5** -- new tool `coverage-check.sh` (parses a classification table's rows, checks every
  `conv:`/`role:`-destined row is cited by ID or source filename in some `origin:` line under
  `conventions/`/`roles/`). **One real bug found and fixed**: it originally scanned the whole table
  row for a dest-shaped token instead of just the dest cell, so a `Why` cell mentioning a rejected
  alternative destination produced a false uncovered reading (found via `harvest-classification.md`
  row FM14, which literally says "considered conv:X... placed at model"). Final run:
  **`harvest-classification.md` 62/62 covered, 0 gaps. `memory-harvest-classification.md` 42/54
  covered**, remaining 12 rows all individually accounted for (5 `role:` rows out of this pass's
  scope, 5 confirmed-redundant by the coder itself, 2 explicitly skipped pending Dean).

## A real process gap found and fixed along the way

Both harvest coders' briefs said "enrich the existing entry" for content that substantially already
existed, but never said "and add the new source to that entry's `origin:` citation too." This meant
real, verified harvest work was invisible to `coverage-check.sh` -- not a coder failure, a gap in my
own brief. Found via the tool's own honest output, not assumed. Fixed 17 citations across 10 files
by hand once the harvest coders were done and the files were stable (commits `d6ed57ac`, plus the
GF3/GF4 fix folded into the same pass). Worth carrying forward into any future harvest brief: state
explicitely that an addition to an existing entry must also add its own citation to that entry's
`origin:` line, not just the entry's body.

## Armed footguns / things worth carrying verbatim

- **None currently armed** -- no paused process, no uncommitted risky state, no sole-copy file
  hazard. `plans-tooling`'s working tree is clean and fully pushed.
- **CURRENT.md does not yet reflect this mandate at all.** Its existing `plans-tooling` entries
  describe the earlier (already-landed) state-commands port and the deferred Type-6 review --
  neither mentions tonight's 5-step migration. A `sync__micro-rules-migration-complete.md` handoff
  is being filed alongside this status file for the sync session to fold in.
- **The eventual cutover (merging `plans-tooling` into `plans`) has NOT happened and should not
  happen without Dean's explicit review and go-ahead** -- per his own instruction ("we flip this by
  merging plan-tooling into plans... once Dean reviews and approves"). Nothing in this session
  attempted or proposed that merge.

## Open, not resolved, explicitly Dean's call (not silently dropped)

1. The `role:`-destined harvest rows (`feedback_coder_no_current_edit.md`,
   `feedback_coder_no_unauthorized_subagents.md`, `feedback_sync_single_writer_model.md`,
   `project_sync_role_origin.md`) still need folding into `roles/coder.md`/`roles/sync.md` -- a
   separate pass, scoped and ready to run, not started.
2. Five small naming/placement decisions flagged in `memory-harvest-classification.md`: whether
   `conv:writing-style`/`conv:tooling-preferences` are worth creating (FM1/FM33); a `chat-links.md`
   fold-in for a mission-narrow viz memory (FM49); whether two mechanism-vs-rule borderline memories
   (`project_session_naming_mechanism.md`, `project_sync_role_origin.md`) belong in the rules
   mechanism at all (PM23/PM25).
3. Three proposed additions to `planning/doc-and-session-model.md` (PM6/PM16/PM17 -- benchmark
   harness architecture, the second-workspace bootstrap, the plans-branch-purpose fact), handed off
   in the Step 2b coder's own status file (`plans/session/status/plans-tooling.md`) rather than
   written, since that file was out of the coder's write scope. Dean's call whether they belong in
   the shared model doc or their own mission docs.
4. Whoever runs the next session on this mission should start from
   `plans-tooling/planning/micro-rules-migration-plan.md`'s own checklist -- it is current as of
   this park, committed `585fc823`, pushed.

## Verified before parking

- `plans-tooling` working tree clean, `git log origin/plans-tooling..plans-tooling` empty (fully
  pushed).
- `./scripts/conv-lint.sh` and `./scripts/coll-lint.sh` both exit 0 from `plans-tooling`.
- `./tests/run.sh` — 80/80 cases pass.
- `./scripts/coverage-check.sh` against both real tables — numbers exactly as stated above,
  re-verified at park time, not just recalled from earlier in the session.
