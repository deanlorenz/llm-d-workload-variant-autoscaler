# Harvest classification table — CONVENTIONS.md + CODER-CONVENTIONS.md

**Prerequisite for `conventions-harvest-spec.md` (Migration 1, M1.2–M1.4).** Per that spec's own
framing: this table is a **placement decision** (per-step convention fetched on demand, standing role
kernel, or model/taxonomy prose that isn't a rule at all) — not a correctness gate, and not on any
critical path. All rows below are **relocations** (existing written rules moving to a new home), which
per the design's own "Migration is not removal" rule need no per-row approval — only genuinely
**new-articulated** policy (a rule inferred from an incident but never actually written down) would need
Dean's sign-off, and none of the rows below are that; every one already exists as written text in
`session/CONVENTIONS.md` or `session/CODER-CONVENTIONS.md`. Worst case, a wrong placement is corrected
later at no cost — nothing here is destructive, and nothing is removed from its source file until
`coverage-check` (M1.3) confirms the mapping is total.

Scope: this pass covers only the two convention files, per Dean's request to validate the classification
scheme on the largest, clearest source before extending it to the ~30 `feedback_*`/`project_*` memories
and `governance-follow-ups.md` incidents (a separate, messier pass, not done as a full pass here — one
memory was pulled in early, 2026-08-15, at Dean's specific request; see the section below the two
tables).

Column `dest` uses:
- `conv:<topic>` → `conventions/<topic>.md` (fetched per-step by name)
- `role:<role>` → `roles/<role>.md` (standing kernel, always loaded for that role)
- `model` → `planning/doc-and-session-model.md` (design/taxonomy prose, not a rule)

---

## From `session/CONVENTIONS.md`

| # | Source (heading / description) | dest | Why |
|---|---|---|---|
| C1 | Checkpoint capture — Tier-1/Tier-2 loop, `session-snapshot.sh` invocation | `conv:checkpoint-capture` | Situational: invoked once at session start, not a standing behavior a role always holds in mind — fetched when starting or resuming a session. |
| C2 | Checkpoint capture — "why it is not optional" (compaction is the loss channel) | `conv:checkpoint-capture` | Rationale for C1; travels with it, same convention file. |
| C3 | Repository layout (bare repo + worktrees tree diagram) | `model` | Descriptive of the workspace's physical structure, not a rule anyone follows at a step — same class the harvest spec calls out explicitly ("the design of the system," not a rule). |
| C4 | Skills layout (`s-*` symlink convention) | `conv:skills-layout` | Situational: only relevant when adding a new skill, a specific, occasional action. |
| C5 | `plans/` structure (session/planning/scratch dirs) | `model` | Structural description, not a rule invoked at a step. |
| C6 | Document Taxonomy (Types 1–6, now design/epic-plan/code-spec/reference/review/session-state) | `model` | This *is* the taxonomy — explicitly the doc-and-session-model's own subject matter, already partially superseded by that doc. |
| C7 | Type 3 — behavioral-contract-change grep step | `conv:semantic-pivot-grep` | Already named as a memory (`feedback_semantic_pivot_grep`) — a per-step action a planner takes when authoring a plan with a contract change, and a coder takes when executing one. |
| C8 | Type 5 — CURRENT.md bounded shape (rolling window, history.md split, PR Status rules, editing discipline, single-writer model, editing lock) | `conv:current-md-format` | **Reclassified (2026-08-13, per Dean's correction below).** Originally `role:sync`. Same reasoning as the C12/C33/C20/C35 correction: no role holds standing behavioral posture — every role, sync included, gets its instructions from its own assigned doc/scope at the step where it's needed. Sync's "how to write CURRENT.md" is exactly this shape — fetched when sync actually writes, not held standing. Now consistent with C21-C23 (status-file format → `conv:status-files`) by the same test. |
| C9 | Review pipeline — four stages, checker contract | `conv:review-pipeline` | Fetched when running or requesting a review — situational, not standing for every role. |
| C10 | Plan document authoring — micro-rules structure (Reading Protocol, TOC, `toc-refresh.sh`) | `conv:plan-authoring` | Per-step: invoked when a planner authors or hands off a Type-3/code-spec doc. |
| C11 | Agent roles and document ownership table | `model` | Directly the role↔domain ownership model — explicitly named as its own residue class in the harvest spec's table (line 787-788 of the design doc: "the design of the system," not a rule). |
| C12 | `/s-coder` invocation requirement | `conv:session-start` | Not affected by the doc-ownership correction below (this is purely mechanical — load the coder rulebook — not a judgment about whose call something is). Fetched at session start, same as C14-C19's worktree-scope family. |
| C13 | Quick rule (what belongs in CURRENT.md vs. permanent docs) | `conv:current-md-format` | Same reclassification as C8 — same convention. |
| C14 | Worktree scope (read/write boundary, `repo/` is bare) | `conv:worktree-scope` | Concrete, checkable boundary invoked before every write — the harvest spec's own Prerequisite 2 already treats an equivalent (`step-check`) as per-step tooling, so the underlying rule is the same shape. |
| C15 | Pre-action gate (verify write scope before any write) | `conv:worktree-scope` | Same convention as C14 — this is the mechanical check that enforces C14, not a separate rule. |
| C16 | Switching worktrees — `EnterWorktree` only, never bare `cd` | `conv:worktree-scope` | Same family as C14/C15: the mechanics of respecting worktree scope. |
| C17 | `cd` to a sibling worktree forbidden, with the plan-agent subagent exception | `conv:worktree-scope` | Same family; the exception is a specific, rare procedure, still fetched on demand rather than held standing. |
| C18 | Git write-verbs never run outside sanctioned scope | `conv:worktree-scope` | Same family — a write-verb boundary, mechanically identical in shape to the file-write boundary. |
| C19 | `claude -p --allowed-tools` subprocess pattern | `conv:worktree-scope` | A specific procedural recipe for a rare case (permission-scoped subagent work) — textbook per-step lookup, not something to hold standing. |
| C20 | Discuss before implementing (CURRENT.md "next step" isn't authorization) | `conv:doc-ownership-boundary` | **Corrected again (2026-08-13) — my first reclassification to `conv:plan-authoring` was itself wrong.** Dean's fuller framing: when he's present, discussion is always fair game — this rule is really about the *unattended* case, where "CURRENT.md said next step X" is not the planner's own doc telling it to act; CURRENT.md is a ledger/calendar, not the planner's owned scope document. Deciding to proceed anyway is exactly the doc-ownership-boundary violation this convention exists to prevent — same convention as C33/C35, not the plan-authoring mechanics of C10. |
| C21 | Status files — broadcast liveness, one file per branch, read-only for others | `conv:status-files` | Format/mechanics of a recurring artifact — fetched when writing or reading a status file, not standing knowledge. |
| C22 | Every agent keeps its own state, commits it | `conv:status-files` | Same convention as C21 — the discipline around the same artifact. |
| C23 | Identity block (mandatory status-file header, 2026-08-13) | `conv:status-files` | Same artifact as C21/C22 — the newest addition to the same format. |
| C24 | Handoffs — serialize updates to shared state (no direct CURRENT.md edits) | `conv:handoffs` | Mechanical protocol for a recurring artifact type, fetched when writing a handoff. |
| C25 | `sync__` vs `plan__` distinction + the split-before-naming fix | `conv:handoffs` | Same convention as C24 — this is the addressing rule for the same artifact. |
| C26 | Sync session mechanics (`/sync-current`, `.DONE` + `git rm`) | `role:sync` | Standing behavior specific to the sync role's own execution loop, not something any other role fetches. |
| C27 | Handoff format (three header lines + prose) | `conv:handoffs` | Format spec for the same artifact as C24/C25. |
| C28 | `sync__` handoff must carry ref + resume prose | `conv:handoffs` | Same convention — a content requirement on the same artifact. |
| C29 | Triggers — doorbell format, no instructions in body | `conv:triggers` | Distinct artifact from handoffs (no prose body, different purpose) — its own convention, fetched when writing or receiving a trigger. |
| C30 | File naming — flat dir, `<recipient>__<topic>.md` prefix convention | `conv:handoffs` (+ cross-ref `conv:triggers`) | ⚠️ **Judgment call, not a clean fit — flagging rather than presenting as settled.** A real alternative exists: a fourth convention (`conv:artifact-naming` or similar) holding just the naming/state-machine mechanics shared by handoffs, triggers, *and* status files, with `handoffs`/`triggers`/`status-files` each citing it rather than one of the three owning it. I picked "fold into `handoffs`, cross-ref from `triggers`" because handoffs are documented first and more fully in both source files, but this is a real fork I should have asked about rather than decided. |
| C31 | State machine — `.md`/`.WIP`/`.DONE`, recipient owns transitions | `conv:handoffs` (+ cross-ref `conv:triggers`) | Same fork as C30 — see that row's flag. |
| C32 | Starting a new session without a CURRENT entry — write a `sync__` | `conv:handoffs` | A specific situational case of C24/C25 — same convention. |
| C33 | Coder-authored review docs are out of scope | `conv:doc-ownership-boundary` | **Reclassified (2026-08-13, Dean's correction), refined further** — not a role posture, and not really about coders specifically: this is one instance of the general boundary check every session runs when a question arises — is this within the doc I own, or does it reach a doc someone else owns (and if unattended, that owner alone resolves it, not this session guessing). Same convention as C20/C35. |
| C34 | Type 4 docs reflect code, not plans (no "pending PR-N" references) | `conv:dev-guide-updates` | Fetched when writing or updating a developer-guide doc — situational to that specific writing task. |
| C35 | Type 3 plans must name specific dev-guide sections | `conv:plan-authoring` | **Left at its original convention, but re-examined.** Unlike C20/C33 above, this genuinely is plan-authoring mechanics (what a planner must specify when writing a Type-3), not a doc-ownership-boundary question — there's no "whose call is this" ambiguity here, just a completeness requirement on the doc being written. Same convention as C10. |
| C36 | Document every deletion — deprecated or deferred | `conv:code-deletion` | Already flagged in the design doc's own TOC-citation example (`rules/code-deletion.md`) as exactly this kind of per-step-cited rule file. |
| C37 | Pre-push checklist (branch check, gofmt, tests, lint, DCO, build) | `conv:pre-push` | Textbook per-step checklist, run once before every push — the design doc's own citation example names `pre-push` explicitly as this shape. |
| C38 | No push without explicit confirmation | `conv:pre-push` | Situational, not absolute — conditional on being about to push at all. Stays a convention. See ⚠️ note below on C44/CC6. |
| C39 | Warn before pushing to an active PR branch | `conv:pre-push` | Same convention — an additional check within the same gate. |
| C40 | No GitHub actions without explicit confirmation | `conv:github-actions` | Distinct trigger condition (any GitHub write, not just push) from `pre-push` — its own convention, fetched whenever any GitHub-writing action is contemplated. |
| C41 | Force-push only after history rewrite, explain why | `conv:pre-push` | Same convention as C37-39 — a specific case of the push gate. |
| C42 | Commit messages must reflect the diff, esp. after rebase (+ the 4-step rebase procedure) | `conv:rebase-integrity` | Already named as a citable rule file in the design doc's own example (`rules/rebase.md`-shaped) — a specific, occasional procedure, not standing knowledge. |
| C43 | Merging upstream into main (`--ff-only`, never a merge commit) | `conv:git-remotes` | Situational: only relevant during the specific act of syncing main — fetched then, not held standing. |
| C44 | Never push to `upstream` | `role:coder` + `role:planner` (cross-cutting) | ⚠️ **Corrected on review** — originally placed as `conv:git-remotes`, inconsistent with CC6 (same substantive "never push" character, classified `role:coder`) on the same pass. Absolute and unconditional (true 100% of the time, no situational trigger) — same character as CC6, not C38/C45. Reclassified to match. No single existing role file fits cleanly since this binds every role that could conceivably run `git push`, not one role's own scope — flagged as cross-cutting rather than invented a placement. See `atomic-step-protocol-design-addendum-4.md` — this is exactly the posture-vs-checklist fork Dean raised as an open, undecided question; do not treat this reclassification as resolving that question, only as fixing an internal inconsistency within today's two-category scheme. |
| C45 | Every code branch has a matching origin branch | `conv:git-remotes` | Situational — a one-time setup checklist item when creating a branch, not an always-true posture. Stays a convention, unlike C44. |

## From `session/CODER-CONVENTIONS.md`

| # | Source (section) | dest | Why |
|---|---|---|---|
| CC1 | §0 — verify CWD/branch at session start | `conv:worktree-scope` | Mechanically identical to C14-C19 (CONVENTIONS.md's worktree-scope family) — this is the coder-specific instance of the same check, belongs in the same convention rather than a duplicate. |
| CC2 | §0 — re-verify before every edit / every commit | `conv:worktree-scope` | Same convention as CC1 — the repeated-check discipline around the same boundary. |
| CC3 | §0 — "why this matters" + the cp/mv-not-cd + `EnterWorktree` self-rescue fix | `conv:worktree-scope` | Same convention — this is the exact fix landed 2026-08-13 for the incident recorded in `governance-follow-ups.md`; belongs with the rest of the worktree-scope material it corrects. |
| CC4 | §0 — convenience alias (`bob-code` shell function) | `conv:worktree-scope` | A minor, optional mechanical aid for the same session-start check — same convention, not worth a separate one. |
| CC5 | §1 — worktree scope (edit boundary, single sanctioned write exception, pre-action gate) | `conv:worktree-scope` | Direct restatement/coder-specific instance of C14-C19 — same convention, avoid duplicating text that already exists in the CONVENTIONS.md version; the coder-specific "single sanctioned write exception" detail (handoffs + own status file) is the one piece worth keeping as an addition within the same convention file rather than a new one. |
| CC6 | §2 — local changes only, no pushes/PRs/GitHub actions | `role:coder` | This is a standing, absolute posture for the coder role (it may never push, ever) — not a situational lookup; a coder holds this every session, unconditionally. |
| CC7 | §3 — tests: write and run, WVA-specific gates (`make test`, `gofmt`, `make lint`, `go build`) | `conv:go-test-gates` | ⚠️ Split from CC8 into a separate convention; both are "checks a coder runs mid/end-of-task." Not fully confident the split is right rather than one combined `conv:coder-verification` covering both test-running and the semantic-pivot grep. |
| CC8 | §3 — semantic-pivot cross-reference check | `conv:semantic-pivot-grep` | Same convention as C7 (CONVENTIONS.md's version) — this is the coder-side half of the same rule; don't duplicate, fold into the one convention both roles reference. ⚠️ See CC7's flag on whether this and go-test-gates should be one file. |
| CC9 | §4 — developer-guide updates on your branch | `conv:dev-guide-updates` | Same convention as C34 — the coder-side instance of the same writing task. |
| CC10 | §4b — document every deletion (deprecated/deferred) | `conv:code-deletion` | Same convention as C36 — identical rule, stated once in CONVENTIONS.md's version and restated here; the coder-facing copy should fold into the single convention rather than persist as a duplicate. |
| CC11 | §4a — no plans-branch references in code-side artifacts (with the bad/good examples table) | `conv:plans-refs-in-code` | ⚠️ **Not fully confident.** "Has a worked example table" isn't a principled reason on its own to make this a standalone file rather than folding it into `conv:code-deletion` or `conv:dev-guide-updates` (both are also about what a coder writes into code-side artifacts). Gave it its own file mainly because the source text is long and example-heavy, not because I confirmed it's a genuinely distinct trigger/situation. |
| CC12 | §5.1 — status file format and rewrite discipline | `conv:status-files` | Same convention as C21-C23 — coder-side instance of the same artifact; the WVA-specific template (§9.1) travels with it as the convention's worked example. |
| CC13 | §5.2 — handoff destinations (`sync__` vs `plan__`) + split-before-naming | `conv:handoffs` | Same convention as C24-C32 — this is the coder-facing restatement (with the 2026-08-13 fix) of the identical rule; fold in rather than duplicate. |
| CC14 | §5.3 — triggers to siblings | `conv:triggers` | Same convention as C29-C31. |
| CC15 | §5.3 — "do not edit CURRENT.md directly" (coder write-scope restatement) | `role:coder` | This is the coder role's own absolute boundary (never write CURRENT.md) — standing, not situational; belongs with CC6 as part of what defines the role's permanent scope. **Duplicate of CC19** (§8's "may NOT do" list already states the identical rule) — both map to `role:coder`, so no placement error, but the harvest should fold these into one statement in `roles/coder.md` rather than write the same line twice. Flagged, not fixed here — the two source lines are legitimately separate restatements in CODER-CONVENTIONS.md itself (§5.3 in context of CURRENT.md ownership, §8 in context of the permission list), so dedup is a harvest-time judgment, not a table error. |
| CC16 | §5.4 — internal review request before push-ready (+ self-check with `/code-review --fix`) | `conv:review-pipeline` | Same convention as C9 — this is the coder-side trigger into the same review pipeline described in CONVENTIONS.md. |
| CC17 | §6 — WIP until Dean reviews, never self-declare done | `role:coder` | Standing posture — a coder never marks its own work "done," always and unconditionally, not a situational checklist item. |
| CC18 | §7 — things you may do without asking | `role:coder` | This is the role's own permission boundary — definitionally standing, it's what the role *is* allowed to do at all times. |
| CC19 | §8 — things you may NOT do without asking | `role:coder` | Same reasoning as CC18 — the negative space of the same permission boundary; belongs together with CC18 in the same kernel file, not split across two conventions. |
| CC20 | §9.1/§9.2/§9.3 — templates (status file, sync handoff, trigger) | (split: fold into `conv:status-files`, `conv:handoffs`, `conv:triggers` respectively) | Templates are the worked examples for their respective conventions, not a separate artifact — each fragment travels with the convention it's a template for rather than living in its own file. |

---

## From `feedback_*`/`project_*` memories — partial, started 2026-08-15

**Not the deferred full pass** (see the scope note at the top of this file — that pass, over ~30
memories plus `governance-follow-ups.md` incidents, is still not done). This section exists because
Dean asked for one specific memory to be harvested now, on its own — recorded here rather than
squeezed into the two tables above (which are scoped to the two convention files only) or held back
until the full memory pass happens. Expect this section to grow piecemeal, ahead of the full pass.

| # | Source (memory name) | dest | Why |
|---|---|---|---|
| M1 | `feedback_handoff_own_reply_never_marked_done` — never mark your own outgoing handoff `.DONE`; only the recipient does, when they've processed it | `conv:handoffs` | A sharper corollary of C31 (state machine, recipient owns transitions), not a duplicate: C31 states the general rule, this memory adds the specific failure mode (sender marks their own reply done) and its own mechanism for avoiding it (name out loud, before running `mv`, who sent the file and who is marking it done — if the answer is "I sent it," stop). Same convention family as C24/C25/C27/C28/C31/CC13; belongs alongside them rather than as a separate file, since it's the same artifact and the same rule, just learned the hard way. |



**`conventions/`** (20 files, revised 2026-08-13): `checkpoint-capture`, `skills-layout`,
`semantic-pivot-grep`, `review-pipeline`, `plan-authoring`, `worktree-scope`, `status-files`, `handoffs`,
`triggers`, `dev-guide-updates`, `code-deletion`, `pre-push`, `github-actions`, `rebase-integrity`,
`git-remotes`, `go-test-gates`, `plans-refs-in-code`, plus three added by the doc-ownership correction
below: `session-start`, `current-md-format`, `doc-ownership-boundary`.

**`roles/`** — **corrected count (an earlier draft of this line wrongly said "down to 1 confirmed
file"; that was wrong and flagged as such before Dean saw it).** Two files still hold real content:
`role:sync` (C26 — sync's own `/sync-current` execution mechanics) and `role:coder` (CC6, CC15, CC17,
CC18, CC19 — the coder's absolute, always-true permission boundary: never push, never edit CURRENT.md,
never self-declare done, the full may/may-not-do lists). **`role:planner` now holds nothing** — C20,
its only candidate row, was reclassified to `conv:doc-ownership-boundary` per the correction below.
**C12/C33/C20/C35 were reclassified from `role:coder`/`role:planner` to conventions** — per Dean's
correction, no role holds standing *behavioral posture in the sense of "assumes what its parent
wanted"*; every role, present-or-absent, consults its own assigned doc at the point of a judgment call.
This does **not** empty out `roles/coder.md` generally — CC6/CC15/CC17-19 survive there because they are
a different kind of content: an absolute, unconditional *permission boundary* (what the role may/may not
ever do), not a judgment-call posture about whose decision something is. `reviewer`, `designer`, and the
rest of the eleven-role model remain unpopulated by this pass regardless.

**`model`**: 3 items (C3, C5, C6/C11 — repository layout, `plans/` structure, document taxonomy +
ownership table) — all destined for `planning/doc-and-session-model.md`, which the design doc's own
residue-class table already names as the home for exactly this kind of content.

**Cross-file folding, not duplication.** Several CODER-CONVENTIONS.md sections restate a CONVENTIONS.md
rule for the coder's specific case (CC1-CC5, CC8-CC10, CC12-CC14, CC16) rather than stating a genuinely
different rule. Each is mapped to the *same* convention its CONVENTIONS.md counterpart uses, not a
duplicate — the harvest, when it runs, should fold the coder-specific detail (an example, a WVA-specific
gate list, a worked table) into that one convention file as an addition, not create two files carrying
the same rule under different names. This is itself a small judgment call, flagged here rather than
silently applied, since the alternative (one convention file per source section) would recreate exactly
the duplication-across-documents problem the whole migration exists to fix.

**Source conflicts found:** none. Both files agree wherever they overlap (worktree scope, handoffs,
triggers, status files, semantic-pivot grep, code-deletion, dev-guide updates) — CODER-CONVENTIONS.md's
own header ("If anything here conflicts with CONVENTIONS.md, CONVENTIONS wins") already establishes
precedence, and no actual content contradiction was found between the two on any classified item.

**Corrected on review (2026-08-13), not silently — three placements flagged rather than picked:**

1. **C44 reclassified** from `conv:git-remotes` to `role:coder`/`role:planner` (cross-cutting) — the
   original placement was inconsistent with CC6 (same substantive "never push" rule, already correctly
   `role:coder`) on the same pass. This surfaced the deeper, genuinely open question of how an *absolute,
   unconditional* rule should be classified when it's phrased as a mechanical checklist item — recorded
   as its own design question in
   [`atomic-step-protocol-design-addendum-4.md`](atomic-step-protocol-design-addendum-4.md) rather than
   resolved here. Dean's own framing: standing rules may need to be *reaffirmed* at the specific step
   where the risk is plausible, which is neither a pure role-kernel placement nor a pure per-step
   convention — a possible third category, not yet designed, explicitly uncertain ("we shall see").
2. **C30/C31 flagged, not re-decided** — folding shared naming/state-machine mechanics into
   `conv:handoffs` (cross-referenced from `conv:triggers`) was a real judgment call with a defensible
   alternative (a fourth, dedicated convention); flagged in the table rather than presented as settled.
3. **CC15/CC19 duplicate flagged** — the same "never edit CURRENT.md" rule appears at two source
   locations in CODER-CONVENTIONS.md and both correctly map to `role:coder`, but the harvest should state
   it once in `roles/coder.md`, not twice.

None of these change the file-list totals above; all three land in categories already counted. The
correction changes C44's destination only (from a `conv:` file to role kernels), so **`conv:git-remotes`**
now holds only C43 and C45.

## Repo-scope axis — designed 2026-08-16, not yet applied (harvest pass itself stays deferred)

**Why this exists.** A second VSCode workspace is being stood up
([`llm-scaler-workspace-bootstrap-design.md`](llm-scaler-workspace-bootstrap-design.md)) for a
different repo. Memories live under a bare-repo-path-keyed project directory
(`~/.claude/projects/-home-dean-code-...-repo/memory/`), so **no memory follows a new workspace
automatically** — a container at a different path gets a different, empty project dir. When the
deferred `feedback_*`/`project_*` harvest pass eventually runs (still ~30 memories, still not started
— this section only designs the axis it will need, per Dean's explicit scoping 2026-08-16: design now,
run later), each memory needs a second, independent classification alongside its existing `dest`
placement: **does this rule travel to a new repo, or does it stay behind?**

**The axis is orthogonal to `dest`, not a replacement for it.** `dest` answers *where within one
workspace's conventions/roles/model this rule lives*; the new axis answers *which workspaces should
ever see it at all*. A rule can be any combination — `conv:worktree-scope` is global (worktree
discipline has nothing to do with which repo), while a hypothetical `conv:ta-benchmark-setup` would be
repo-specific (WVA-only tooling) even though it's still a `conv:` placement, not a `model` or `role:`
one. The two axes answer different questions and must both be recorded, not merged into one.

**Two values, decided by one test — does the rule's truth depend on which repo you're in?**

- **global** — true regardless of repo: how Dean wants work done, not what the work is about. American
  English, no-push-without-confirmation, `uv` for Python, no in-place shell edits via `sed -i`, DCO
  discipline, worktree locality, the handoff-protocol mechanics themselves (`.md`/`.WIP`/`.DONE`,
  `sync__` vs `plan__`). Every convention-file row in the two tables above that survives the harvest
  test is a strong candidate for **global**, precisely because `session/CONVENTIONS.md` is largely
  Dean's cross-cutting process preferences wearing this-repo's file paths — the repo-specific part is
  almost entirely in the *paths and PR numbers*, not the *rule*.
- **repo-specific** — true only because of *this* repo's own state or history: WVA mission content (TA,
  multi-analyzer, pokprod), PR numbers, branch names, `Main`/`plans` worktree layout specifics beyond
  the generic bare-repo+worktrees pattern, any incident whose lesson is really "check this specific
  file" rather than "check files like this."

**Destination, per Dean's own ruling (handoff #2, 2026-08-16): global memories eventually live in
`dean-ai-overlay`**, the one thing that's already cross-repo — it's already wired into this container
via `.vscode/tasks.json` → `dean-ai-overlay/vscode/tasks.json`, so it's the only existing candidate that
*is* cross-repo rather than becoming so. Repo-specific memories stay exactly where they are, in this
project's own `memory/` directory. **Not designed here, left for the harvest pass itself**: the exact
mechanics of writing into `dean-ai-overlay` (a new memory type? a plain file drop? does it need its own
frontmatter schema distinct from the per-repo `memory/*.md` format?) — this section answers the
classification question, not the write-mechanics question.

**Why capture both axes in the same read, not two passes.** Sorting only by `dest` (today's two tables)
answers "which convention file" but leaves "does this survive to a new repo" completely undone — a
later pass would have to re-read the same ~30 files again just to answer the second question. The two
questions are answered by the same read of the same source text; splitting them into two passes is pure
waste, not a safety margin. This is the entire content of handoff #2's ask, and it's now satisfied by
recording the axis's existence and test here — **no memory has been re-classified under it yet**, since
that would be running the pass, which stays deferred.

**Content-loss discipline carries over unchanged.** The verify-or-copy-then-delete rule this table's
own top section already states ("nothing removed from a source file until `coverage-check` (M1.3)
confirms the mapping is total") applies identically once the harvest pass adds this second axis — a
`feedback_*`/`project_*` memory is deleted only once its content demonstrably exists as a rule *and*
its repo-scope classification is recorded, not before.

**One candidate check for whoever runs the eventual pass, not resolved here:** the convention-file rows
already classified above (C1-C45, CC1-CC20) were harvested for `dest` only, without this second axis in
mind. Re-running the global/repo-specific test against those same ~65 rows once the axis exists is cheap
(the read already happened; this is a second pass over notes already taken, not new research) and would
let the `conventions/` files themselves carry a global/repo-specific marker per rule — worth doing in the
same session that runs the `feedback_*`/`project_*` pass, not a separate task.

## ⚠️ Rows flagged — review status as of 2026-08-13 (second pass)

**Confirmed fine by Dean, no change:** C30/C31 (handoff/trigger naming fold — the fourth-convention
alternative was real but this placement is accepted as-is), CC15/CC19 (the CURRENT.md-edit duplicate —
accepted, dedup is a harvest-time detail not a table fix), CC7/CC8 (`go-test-gates` /
`semantic-pivot-grep` split), CC11 (`plans-refs-in-code` as its own file).

**Resolved by correction, not just flagged:**
- **C44** (never push to `upstream`) — reclassified from `conv:git-remotes` to a cross-cutting
  `role:coder`+`role:planner` placement; surfaced the open, undesigned "posture vs. checklist" question
  now recorded in [`atomic-step-protocol-design-addendum-4.md`](atomic-step-protocol-design-addendum-4.md).
  Placement itself is settled for this table; the deeper design question is not.
- **C8 / C13** (CURRENT.md's bounded-shape rules) — moved from `role:sync` to `conv:current-md-format`,
  now consistent with C21-C23's status-file treatment by the same test (fetched-when-writing, not
  standing knowledge).
- **C12** — unaffected by the doc-ownership correction (purely mechanical: load the coder rulebook, no
  judgment involved); stays `conv:session-start`.
- **C33 / C20** — reclassified to `conv:doc-ownership-boundary`: not standing posture, but the general
  "is this within the doc I own, or does it reach a doc someone else owns" check every role runs at a
  judgment call, per Dean's fuller framing (present vs. unattended, doc-ownership vs. session-to-doc
  binding, graduated strictness by role).
- **C35** — re-examined against the same test and left at `conv:plan-authoring`: this is a completeness
  requirement on a doc being written, not a doc-ownership-boundary question, so it doesn't belong with
  C33/C20 despite superficially similar wording ("planner must...").

**Still genuinely open, not yet resolved:**
- The **posture-vs-checklist** question itself (an absolute rule phrased as a mechanical action) —
  Dean's own "we shall see," recorded in full in `atomic-step-protocol-design-addendum-4.md`. C44 is
  its concrete example in this table; there may be others not yet re-examined against this test.
- Whether `roles/coder.md`'s and `roles/sync.md`'s surviving content (CC6/CC15/CC17-19, C26) needs
  further scrutiny under the same doc-ownership-boundary lens that moved C12/C33/C20 out — not
  re-checked in this pass, since those five rows are a different *kind* of content (absolute permission
  boundary, not a judgment-call posture) and weren't flagged as uncertain to begin with.

Everything else in the table is a first-pass placement with a stated reason, reviewed by Dean at the
level of "role-skills: good," "step-gate: good," etc. — not necessarily independently row-by-row
verified beyond what's captured in this section. Treat the absence of a note here as "not specifically
revisited," not as "guaranteed correct."
