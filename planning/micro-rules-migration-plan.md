# Code spec — micro-rules migration: harvest, triggers, collections, coverage

**code spec** · **Status: EXECUTING — Dean approved autonomous execution 2026-08-17, "easier to
correct later," reviews cold.** Built and executed in `plans-tooling`, the migration's own dev branch
(Addendum 8) — **not** `plans`. Cutover to `plans` happens by merging this branch in, once Dean
reviews and approves; `plans/CLAUDE.md` is not touched by this spec at all.

## At a glance

**Mission:** per Dean, 2026-08-17 (restating Addendum 15's mission): break `CONVENTIONS.md`,
`CODER-CONVENTIONS.md`, and memories into load-on-demand pieces, using the fetch mechanism that
already exists (`conv`/`sec`, extended rather than replaced) — not a new system.

**Approach, Dean's own five steps, executed in order:**
1. Define the roles — the *what*, not the *how*. A spec for roles; gaps in new (unbuilt) roles are
   skipped, not blockers.
2. Harvest every rule and memory into one mechanism (the existing `conv` format, extended).
3. Create fetch triggers per rule — already substantially built (`trigger:` field exists in the
   format); this step is populating it correctly for every harvested rule, not inventing a new field.
4. Build the entry points: (4.1) rule-collections per role, (4.2) rule-collections per common step,
   (4.3) pre-packaged prompts for common tasks (prose + rules) — all three are documents themselves,
   with their own fetch triggers, same mechanism as a convention.
5. Coverage test — every existing rule reachable from every relevant entry point. Exact test shape
   still open (Dean: "I still don't know what they are... can at least run coverage tests").

**Explicit non-goals, per Dean:** no human-readable re-classification pass yet — first instance is a
direct functional replacement for `CONVENTIONS.md`/`CODER-CONVENTIONS.md`, not a prettier taxonomy.
Tools are built **only as needed per step**, not speculatively ahead of time.

**Needs you:** review cold, correct what's wrong — Dean's own framing, not a request for approval
before proceeding.

**Checklist:**
- [ ] Step 1 — role specs (skip roles with no source material; note the skip, don't invent content).
- [ ] Step 2 — harvest CONVENTIONS.md + CODER-CONVENTIONS.md + `feedback_*`/`project_*` memories +
  `governance-follow-ups.md` incidents into the `conv` format.
- [ ] Step 3 — `trigger:` field populated correctly for every harvested item.
- [ ] Step 4.1 — role-collections.
- [ ] Step 4.2 — common-step collections.
- [ ] Step 4.3 — pre-packaged task/step prompts.
- [ ] Step 5 — coverage check: every source rule reachable from at least one entry point.
- [ ] Tools built only as each step actually needs them (§ Tooling below tracks what's built vs.
  still using existing `conv`/`sec`/`conv-new`/`conv-list`/`conv-lint`).

---

## Why this doc exists, and why it is not `atomic-step-protocol-design.md` itself

The frozen design (`plans/planning/atomic-step-protocol-design.md`) already names this exact migration
(§ Migration, M1.0-M1.4) and is the authority on the *shape* (three residue classes: per-step
convention / role kernel / model prose; the `### convention:` format; `conv <name>` fetch). This doc is
the **execution log** for actually running that migration tonight, per Dean's explicit five-step
ordering and scope decisions — it does not amend the frozen design, it executes it. Where this doc's
own decisions differ from a literal reading of M1.0-M1.4 (e.g., building role specs *before* the full
coverage tool, rather than M1.0's "tooling complete before extraction" ordering), that is Dean's
explicit call tonight ("build tools only as needed"), recorded here, not a silent deviation.

## Format used throughout (existing, not new)

```
### convention: <name>
description: <one line>
scope:       <role(s) this applies to, or "all">
trigger:     <when this fires — BEFORE commit, session start, etc.>
status:      active | probation
origin:      <source citation — file:section or memory name>
```

Built and hardened already: `conv-new.sh` (create), `conv-edit.sh` (in-place edit), `conv-rename.sh`
(rename + citation rewrite), `conv.sh` (fetch by name), `conv-list.sh` (computed index), `conv-lint.sh`
(structural check). All operate on any `--dir`, defaulting to `conventions/`.

**Extension needed for role-collections/step-collections/pre-packaged prompts (Step 4):** these are
not single conventions — they are named groups that *reference* several conventions/kernel lines
together. Not yet decided whether they get a new marker (`### collection: <name>`) in the same
`conv`-fetchable files, or a separate directory with its own tiny fetch tool. Decide at Step 4, not
before — per Dean's "build tools only as needed."

## Step log

### Step 1 — role specs (2026-08-17)

All 11 role files written to `roles/<name>.md` — owns/reads/token from `doc-and-session-model.md` §
Roles, thin by design (the "what," not the "how"). Deliberately skipped rather than invented:
`designer`, `epic`, `spec`, `confirm`, `verify`, `pr` all have zero-to-thin harvested kernel content —
their files say so explicitly and cite the gap rather than filling it.

Carried forward 5 real findings from `atomic-step-protocol-design-addendum-13.md` into the specific
role files they belong to, so they are not lost in a separate doc nobody re-reads while harvesting:
- `verify.md` — `s-design-review`'s step order is backwards for this role (code-first is the rule;
  the skill reads design/plan first). Live defect, not just a design gap.
- `triage.md` — `s-pr-triage` produces a review doc, not the fixup code spec this role owns.
- `sync.md` — 0/302 handoffs use the `sync` token despite the richest skill coverage of any role.
- `epic.md` / `spec.md` — the transient-vs-durable and code-spec-vs-PR read-scope discrepancies.
- `coder.md` — the benchmark-tester exception (not really a coder, needs its own role — undecided)
  and the still-open C44 posture-vs-checklist question.

### Step 2 — harvest (in progress, 2026-08-17)

Dispatched to a background coder (`ba4d7081`, `--add-dir` to `plans` for read access to the source
files, `--permission-mode auto`) rather than done by hand inline — genuinely mechanical, judgment
already made in `harvest-classification.md`'s own table, ~65 rows across ~20 `conv:<topic>`
destinations. Scoped explicitly to `conv:` destinations only — `role:`/`model` destinations are out of
scope for this pass (role content is Step 1's territory, already done thin; `model` destinations go to
`doc-and-session-model.md`, not touched here). C44 (the cross-cutting, still-open posture-vs-checklist
row) explicitly excluded from the batch, not silently skipped.

**Complete and independently verified** (2026-08-17): 20 topic files, 45 entries, `conv-lint.sh` clean,
source files byte-identical, verbatim-text spot-check passed (`pre-push.md` diffed word-for-word
against `session/CONVENTIONS.md` § Pre-push checklist). One genuine table gap the coder flagged
(CODER-CONVENTIONS.md §1's pathspec-commit paragraph, no row in the table) — resolved below via the
memory pass: it's `feedback_shared_git_index_pathspec_commits.md`, already written down, just never
cross-referenced into the table.

### Step 2b — memory + governance-incident harvest (2026-08-17)

Scope: the `feedback_*`/`project_*` memories (78 files) plus `governance-follow-ups.md`'s incident
list — the "separate, messier pass" `harvest-classification.md` itself deferred. Repo-scope axis
stays explicitly out of scope, per that same doc's own design-now-run-later note.

Built `planning/memory-harvest-classification.md` (committed `3585b3b5`) the same way Dean built the
original table — read every memory (via a research agent doing bulk extraction, judgment calls made
by the planner from that extraction, not delegated), classify `dest`. Findings: the volume is
overwhelmingly restatement, not new rules — ~27 of 36 `project_*` memories are `SKIP (mission-local)`
(mission state belongs in that mission's own doc, not the rules mechanism), and most `feedback_*`
memories fold into the same handful of existing topic files (worktree-scope, handoffs, pre-push,
git-remotes) as enrichment rather than new entries. Only 2 new topic files warranted
(`conv:chat-links`, `conv:tool-authoring`); a few more flagged as Dean's call, not decided
unilaterally (`conv:writing-style`, `conv:tooling-preferences`, a couple of `model`-doc placements).

Dispatched to a background coder (`42ce2f92`, same pattern as Step 2a) to execute the table — read
each memory, enrich or create the target file, skip everything `SKIP` or flagged. `model`-destined
rows are explicitly NOT written by this coder (no write access to `doc-and-session-model.md` in
scope) — it hands those off as proposed additions in its status file instead.

### Step 3 — trigger: field coverage

**Turned out to already be satisfied as a side effect of Step 2a**, not a separate pass: every
`conv-new.sh` call requires `--trigger`, and the Step 2a coder supplied a specific, well-formed one
for all 45 entries (verified: `grep -c` on marker vs. trigger-field count matches across every file,
zero empty/placeholder values). Nothing further to build here — Step 3 is a verification checklist
item on every future harvest batch (including Step 2b's), not its own implementation step.

### Step 4 — entry points (design decided 2026-08-17, build next)

**Decision: a sibling marker, not a separate mechanism.** `### collection: <name>` at the same
heading level as `### convention: <name>`, living in a new `collections/` directory (not mixed into
`conventions/` — collections reference conventions by name, mixing the two would make `conv-lint.sh`'s
own path/name scanning ambiguous about which marker it's validating). Fields: `description`,
`members` (comma-separated names — conventions and/or other collections, allowing nesting), `trigger`,
`status`, `origin` — same five-field shape as a convention, since a collection is fetched the same way
(on demand, by name) and needs the same lint guarantees (unique name, required fields). Body prose is
optional framing text, not a rule restatement.

Reuses every existing pattern rather than inventing one: `coll.sh` mirrors `conv.sh` (resolve name →
print members' own `conv <name>` output in sequence, recursing through nested collections), `coll-
list.sh` mirrors `conv-list.sh`, `coll-lint.sh` mirrors `conv-lint.sh` (plus one new check: every
listed member name must resolve via `conv-list.sh`/`coll-list.sh`, catching a stale reference the way
`conv-lint.sh`'s PATHREF check catches a stale path). Three small new scripts, not a rewrite of the
existing three — kept separate because a collection and a convention are different fetch semantics
(a convention prints itself; a collection prints what it points at), and conflating them into one
tool with a mode flag would make both harder to read.

- **4.1 role-collections**: one `### collection:` entry per role with real harvested content,
  `members` = every convention that role's own file content or the classification table implies it
  needs beyond its thin kernel (e.g. `role:coder` implies `worktree-scope`, `handoffs`, `pre-push`,
  `code-deletion`, `dev-guide-updates`, `go-test-gates`, `plans-refs-in-code`, `review-pipeline`,
  `semantic-pivot-grep`, `session-start`, `status-files`, `triggers`).
- **4.2 step-collections**: `committing`, `pushing`, `writing-a-handoff`, etc. — named by the action,
  cutting across roles.
- **4.3 pre-packaged prompts**: same marker, `members` plus a fuller prose body (the "prompt" part) —
  a collection with a task-shaped write-up rather than just a bare reference list.

Not yet built — next action.
