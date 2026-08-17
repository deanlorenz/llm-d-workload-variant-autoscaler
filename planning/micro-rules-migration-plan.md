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

Awaiting completion before touching `conventions/` further, to avoid a concurrent-edit collision with
the coder's own work.

Not yet committed to `roles/` structure decisions beyond what the frozen design already specifies —
no new fields, no new format. Next: Step 2, the actual harvest.
