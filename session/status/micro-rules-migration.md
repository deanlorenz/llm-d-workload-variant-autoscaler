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

## state-park — micro-rules-migration (source report)

```
Subagent addresses recorded (2a — the durable part):
  - (none ran this session) — the one coder dispatched tonight (42ce2f92, Step 2b harvest)
    completed and was independently verified BEFORE this park started; ListAgents at park time
    shows no agents spawned by this session still tracked (only an unrelated peer session,
    plans-a3, which this session did not spawn).
Nudges sent (2b — best effort, NOT a flush):
  - (none running)
Sources read this pass:
  - plans-tooling/planning/micro-rules-migration-plan.md — confirmed current, matches this report
  - plans-tooling git log (last 12 commits) — confirmed all pushed, working tree clean
  - plans/session/CURRENT.md (grep for plans-tooling/atomic-step-protocol-brainstorm) — confirmed
    it does NOT reflect tonight's mandate, only the earlier state-commands port
  - plans/session/status/ (ls) — confirmed no existing planner-side status file for this mission
  - ListAgents — confirmed no subagents from this session still tracked
  - re-ran ./scripts/conv-lint.sh, ./scripts/coll-lint.sh, ./tests/run.sh, ./scripts/coverage-check.sh
    against both real tables, live, at park time — not recalled from earlier in the conversation
Not read (and why):
  - plans/session/status/plans-tooling.md — the coder's own status file, out of my write scope as
    planner; already read in full earlier this session (see the conversation itself) for the Step
    2b accounting this report summarizes
  - roles/*.md, conventions/*.md individual files — already verified file-by-file earlier this
    session via conv-lint/coverage-check; re-reading each individually at park time would duplicate
    work the tools already did mechanically
Written to:
  - plans/session/status/micro-rules-migration.md — this file, new, full mission state
Handoffs emitted:
  - plans/session/handoffs/sync__micro-rules-migration-complete.md — asks sync to fold the mandate's
    completion into CURRENT.md, with the four explicitly-still-open items named so none reads as
    resolved
Committed:
  - 6e5dadd9 state(park): micro-rules-migration -- flush overnight mandate completion + sync handoff
    (plans branch, no DCO needed)
  - (plans-tooling's own commits, 3585b3b5 through 585fc823, were all made and pushed DURING the
    session itself, not as part of this park — listed in the status file body above, not re-listed
    here to avoid duplicating the same SHAs in two places)
Worktree exit:
  - not applicable — this session was never inside a worktree via EnterWorktree; all plans-tooling
    work was done via git -C / absolute-path commands from plans throughout the session (one
    narrow, explicitly Dean-granted cd exception used earlier for an unrelated, already-concluded
    phase). "Was never in a worktree" — confirmed via pwd/git branch --show-current at park time.
Verified from final location:
  - plans/session/status/micro-rules-migration.md — present (this file)
  - commit 6e5dadd9 — visible in git log
  - plans-tooling working tree — clean, confirmed via git status --short at park time
  - plans-tooling vs origin/plans-tooling — no diff, confirmed via git log at park time
Deliberately NOT done (park is additive, and accepts no work):
  - Did not fold the mandate's completion into CURRENT.md myself — filed the sync__ handoff instead,
    per the single-writer model.
  - Did not start the role: harvest pass, resolve the 5 flagged naming decisions, write the 3
    proposed model-doc additions, or attempt the plans-tooling→plans cutover merge — all four are
    explicitly Dean's call, named as open in the status file, not silently advanced.
  - Noticed no drift needing /s-state-sweep this pass.
```

## 2026-08-18 — discussion-only walkthrough session, no execution (Dean's explicit instruction)

Dean's framing this session: "I want to keep this session only for the discussion; for the runs
let's park, start [a] clear session, and do all the sweeps after that." Everything below is
mechanism design/decisions from walking the harvest end to end together — real findings, all
committed to `plans-tooling`, but **deliberately no execution of the queued tasks** (that happens
in the next, fresh session).

**Commits landed tonight, in order** (all on `plans-tooling`, local, not pushed — see that
worktree's own git log for full messages):
`ce72c625` (policy-writer kernel — how to write a convention) → `d0865c8f` (conv.sh tool changes:
suppress origin) → `60859fcf` (suppress status: too; 20 old-file citations flagged) → `9f7eacb1`
(rules-with-references model, Dean's 8 points) → `38e6612d` (`conventions/how-to-commit.md` —
first rules-with-references trial, probation) → `7d9110f1` (re-fetch works only via Bash — tested
live, load-bearing, undocumented) → `53e5cb40` (dedup mechanism feasible: `CLAUDE_CODE_SESSION_ID`
+ transcript line count, tested live) → `5450ec69` (conv.sh/sec.sh unified as one citation
mechanism) → `fe3881cb` (model-destination gap found: C3/C6 never actually migrated) →
`5f145c2c` (new `model/workspace-structure.md` created, fixes it) → `36c038aa` (plans:
`harvest-classification.md` C3/C6 rows repointed) → `3b22eadf` (coverage redefined:
source-line-verbatim, not table-row-cited) → `dfbaf642` (USER/repo genericization rule decided,
not dispatched) → `7002b922` (points 3/6 closed, coverage scope extended past C3/C6, new "Tasks
queued" section added).

**What this session actually did, mechanism-wise** — the two biggest shifts from where the
mandate stood at the last park:
1. **`conv.sh`/`sec.sh` unified into one citation mechanism** ("call conv.sh `<name>`" / "call
   sec.sh `<file>` `<heading>`"), confirmed live that re-fetch only works because both are Bash
   (not `Read`/`@`, which suppress redundant fetches — tested directly, documented as a
   load-bearing constraint nobody had checked before).
2. **Rules-with-references may replace flat collections** — Dean's model where a rule cites its
   own dependencies inline, conditionally, at the step where each applies, rather than a
   `### collection:` bundling everything eagerly. One real trial built
   (`conventions/how-to-commit.md`, `status: probation`) against the existing `committing`
   step-collection for later comparison. **Whether it replaces collections is explicitly still
   open** — decide only after more are authored, per Dean.

**Real content gap found and partially fixed**: C3 (Repository Layout, 59 lines) and C6 (Document
Taxonomy, 222 lines) were classified `dest: model` back in the original harvest but the actual
text was never moved anywhere — it still only existed in `session/CONVENTIONS.md`, the exact file
this migration exists to stop preloading. Fixed for these two: new
`plans-tooling/model/workspace-structure.md`, byte-diffed clean against source, confirmed
`sec.sh`-fetchable. **Coverage itself was redefined as a result** — no longer "does every
classification-table row have a citing `origin:`" (which only certifies the table, and the table
itself just proved it can have gaps) but **"does every line of every currently-loaded `.md` file
appear verbatim in some fetchable micro-convention or micro-model file."** This is a stronger,
different check than what `coverage-check.sh` does today.

**Two tasks queued for the next (execution) session, design settled, not started:**
1. Build the source-line coverage audit (per the redefinition above) and run it against
   `session/CONVENTIONS.md`, `session/CODER-CONVENTIONS.md`, and any other currently-loaded `.md`
   file; fix every gap found, not only the C3/C6 class.
2. Dispatch the USER/repo genericization (`roles/policy-writer.md` point 7) across the ~26 files
   already scoped there — `USER` (uppercase, substitutable-slot token) replaces the human's name;
   `repo` (lowercase) replaces WVA/Workload-Variant-Autoscaler.

Both are named by Dean as good candidates for the `dispatch-and-verify-a-background-coder` prompt.

**⚠️ Genuinely unresolved, flagged and not answered before park — carry verbatim.** Near the end
of this session Dean named a 5-item backlog review (from the pre-existing "still open" list in the
plan doc) and called one item — "5" — **"critical, blocking of migration, this will need a
separate session."** I asked directly which item he meant (offered the `role:`-destined memory
harvest as my best guess) and Dean's next message was `park` rather than a confirmation or
correction. **This is not confirmed either way.** The next session must not assume it was the
`role:` harvest — that is only a guess that was never validated. Re-ask Dean directly before
treating any specific backlog item as "the critical blocking one."

**No armed footguns beyond the above.** `plans-tooling` working tree clean at park time, verified
live (`git status --short` returns nothing). **15 commits ahead of `origin/plans-tooling`, not
pushed** — normal per this project's push-confirmation rule, not a defect, but stated exactly so a
cold resume doesn't assume they're already remote. No paused process, no sole-copy file at risk.

## state-park — micro-rules-migration (2026-08-18 discussion session, source report)

```
Subagent addresses recorded (2a — the durable part):
  - (none ran this session as background/resumable agents)
  - 2 Agent-tool calls this turn (claude-code-guide x2, @-ref/dedup docs check and JSON
    usage-field verification) both ran foreground, completed, output already captured
    inline in this transcript and reflected in file writes — no resume address needed.
Nudges sent (2b — best effort, NOT a flush):
  - (none running)
Sources read this pass:
  - plans-tooling/planning/micro-rules-migration-plan.md — confirmed 14 tonight's commits
    all present and in order
  - plans-tooling git log — confirmed working tree clean, 15 commits ahead of
    origin/plans-tooling (not zero — corrected before writing the report)
  - plans/session/status/micro-rules-migration.md — read in full before editing, confirmed
    it was the correct pre-existing file for this thread, not stale
  - ListAgents — confirmed no subagents from this session still tracked
  - plans git status --short — read before staging; confirmed extensive concurrent
    modification by other sessions, staged only my own file
Not read (and why):
  - plans-tooling/conventions/*.md, roles/*.md individually — already verified via
    conv-lint/live fetch tests throughout the session itself, re-reading each at park
    time would duplicate work already done with tool verification
Written to:
  - plans/session/status/micro-rules-migration.md — appended a new dated section (not a
    rewrite), covering tonight's 14 commits, the two real mechanism shifts, the C3/C6
    content-gap fix, the two queued tasks, and — critically — the unconfirmed backlog-item
    question, flagged verbatim rather than guessed at
Handoffs emitted:
  - (none this pass — nothing here is CURRENT.md-bound or another owner's task; this
    thread's own status file + the plans-tooling plan doc are sufficient)
Committed:
  - bff20833 state(park): micro-rules-migration — 2026-08-18 discussion session (plans,
    this park)
  - 14 commits on plans-tooling from earlier in this session (ce72c625 through 7002b922,
    full list in the status file body — not re-listed here to avoid duplicating the same
    SHAs in two places), plus one commit on plans (36c038aa, harvest-classification.md
    C3/C6 repoint) — all made during the session itself, before this park started
Worktree exit:
  - not applicable — this session was never inside a worktree via EnterWorktree; pwd
    confirmed plans throughout the entire session, no cd used for plans-tooling work
    (git -C / absolute paths only)
Verified from final location:
  - plans/session/status/micro-rules-migration.md — present
  - commit bff20833 — visible in git log
  - plans-tooling working tree — clean, confirmed via git status --short at park time
  - plans-tooling vs origin/plans-tooling — 15 commits ahead, NOT pushed (corrected
    in the report body after an initial draft under-stated this as "no footguns")
Deliberately NOT done (park is additive, and accepts no work):
  - Did not execute either queued task (source-line coverage audit; USER/repo dispatch) —
    per Dean's explicit "keep this session discussion-only, run the work after park+clear"
    instruction.
  - Did not resolve which backlog item Dean meant by "critical, blocking" — asked directly,
    got "park" as the reply, not a confirmation. Recorded as unresolved, not guessed at.
  - Did not push either branch's new commits — no push confirmation requested or given.
  - Noticed extensive concurrent drift in the shared plans/ tree (other sessions' WIP) but
    took no action — not this session's scope.
```
