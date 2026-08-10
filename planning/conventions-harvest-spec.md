# Code spec — the harvest and its coverage audit

**code spec** · **Status: DRAFT** — awaiting Dean's finalization.

Migration steps M1.2–M1.4 of [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md).

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then start at your assigned step and read only that
step's section. No line numbers; do not run `toc-refresh.sh` on it.

---

## Intent

**intent** — Move every existing rule into its new home with **nothing lost**, prove it mechanically, and
only then stop loading the old files. Constraint 8 of the design is the whole point: migration is not
removal, and no rule is removed without long probation and Dean's per-rule approval.

**⚠️ Read this before starting: half of this work is not coder work.**

Classifying a rule — per-step convention, standing role kernel, or model prose — is a **judgment call**, and
a coder must never make one. So this spec is split:

- **Prerequisite, by the policy-writer role, not a coder:** produce a **classification table** — one row per
  source item, with its destination and, where two sources disagree, the disagreement surfaced for Dean
  rather than resolved. Newly-articulated conventions (an incident happened, nobody ever wrote the rule) are
  new policy and need Dean's approval; relocations do not.
- **This spec, for a coder:** build the coverage checker, then apply the approved table **mechanically**.

A coder reaching a source item absent from the table must **halt**. That is the design working: an item
nobody classified is not an invitation to classify it.

**current call stack** — `session/CONVENTIONS.md` and `session/CODER-CONVENTIONS.md` are loaded by
`plans/CLAUDE.md` and carry everything: per-step rules, standing role rules, and the document/role model
itself. Roughly thirty `feedback_*` memories carry the same rules again, sometimes with different detail. The
incidents live in `planning/governance-follow-ups.md` and in review findings. `conventions/` is empty.

**planned call stack** —

```
bounded sources                      →  classification table (policy-writer + Dean)
  CONVENTIONS.md, CODER-CONVENTIONS.md
  feedback_* / project_* memories                    →  conventions/<topic>.md   via conv-new
  governance-follow-ups.md + review findings          →  roles/<role>.md
                                                      →  planning/doc-and-session-model.md
                                       →  coverage-check  (total mapping, no orphans)
                                       →  stop loading the old files
```

**new components** — `scripts/coverage-check`, the populated `conventions/` and `roles/`, and one edit to
`plans/CLAUDE.md`.

**new conventions** — this spec *creates* the initial set, from the approved table. It does not invent any.

---

## Prerequisites

1. `conventions-tooling-spec.md` and `conventions-authoring-spec.md` landed — `conv-new` is how content is
   written, because writing it by hand is what the design forbids.
2. `step-gates-spec.md` landed — a coder editing an existing tree needs `step-check`, unlike the fresh-orphan
   case.
3. **The approved classification table exists**, at `planning/harvest-classification.md`. Without it, stop:
   this spec has no input.

New worktree:

```
git -C repo worktree add ../plans-harvest --orphan plans-harvest
```

Note it must reach `../plans/` to read sources and write `conventions/` — so unlike the tooling worktrees,
its write scope genuinely extends into `plans/`, which is why `step-check` is a prerequisite rather than a
nicety.

**Gates** — `bash -n`, `./tests/run.sh`, `conv-lint` clean, `coverage-check` at zero gaps. No DCO on this
lineage. **Never push.**

---

## Step index

**S1 — `coverage-check`.** Enumerate every bounded source item and every destination, assert the mapping is
total with no orphans. Built first, because it is what turns "nothing was lost" from a promise into a
property — and it must exist before anything moves, so the starting gap count is known.

**S2 — Apply the table: conventions.** Create each classified convention via `conv-new`, copying text
verbatim. Copy, never move: the source keeps its text until coverage is total.

**S3 — Apply the table: role kernels.** Standing rules into `roles/*.md`, extending the thin kernels.

**S4 — Apply the table: model prose.** The taxonomy and role-model material into `doc-and-session-model.md`
— the class easiest to overlook, because it is not a rule at all.

**S5 — Drive coverage to zero and report.** Iterate until no gaps remain. Conflicts and unclassified items
are reported, never resolved.

**S6 — Stop loading the old files.** Only after coverage is zero: drop the imports, leave the frozen files in
place. This is migration, not removal — nothing is deleted and no per-rule approval is needed.

---

<!-- ─────────────── execution detail below ─────────────── -->

## S1 — `coverage-check`

**brief** — The audit that makes constraint 8 verifiable. Every source item maps to exactly one destination;
nothing is orphaned in either direction. A script, not a reading — a careful read is exactly what fails at
this scale.

**scope** — `scripts/coverage-check`, `tests/`

**do**
1. Enumerate source items: each `##`/`###` section of the two convention files; each `feedback_*` and
   working-practice `project_*` memory; each incident in `governance-follow-ups.md`. Emit a stable id per
   item.
2. Enumerate destinations: every `### convention:` name, every `roles/*.md` section, every
   `doc-and-session-model.md` section.
3. Read the classification table and assert: every source item has a row; every row's destination exists;
   no destination is claimed twice unless the table says a source legitimately splits.
4. Report three lists — **unmapped sources**, **rows pointing at missing destinations**, **destinations
   nobody claimed** — then exit non-zero if any is non-empty.
5. `--baseline` records current counts so progress is measurable rather than felt.
6. Cases: a complete tiny fixture set; one unmapped source; one row pointing nowhere; one orphan
   destination.

**conventions** — cite whatever `conv-list` reports at the time; if `conventions/` is still empty, use
`conventions: none` and say so in `record`.

**verify** — `./tests/run.sh` green; run against the real tree and record the **starting** gap counts.

**done_when** — all four cases pass and the real starting counts are recorded.

**on_fail** — halt.

**record** — the starting counts, verbatim. They are the migration's denominator.

[↑ Step index](#step-index)

## S2 — Apply the table: conventions

**brief** — Create each convention the table classifies as per-step, via `conv-new`, with text copied
verbatim from its source. Mechanical by construction: the judgment already happened in the table.

**scope** — `../plans/conventions/`

**do**
1. For each row destined for a convention: `conv-new <name> --topic <file>` with the table's
   `description`/`scope`/`trigger`, `status: active`, and `origin` naming the source item.
2. Copy the rule text **verbatim**. Do not summarise, tighten, or modernise wording. If a source rule is
   unclear, that is a finding for `record`, not something to improve while moving.
3. Where the table marks a rule as present in two sources with **differing detail**, copy the source the
   table designates and record the other in `origin` — the disagreement is information and must survive.
4. **Do not delete anything from any source file.** Copy-then-verify; the deletion question is S6's, and
   S6 deletes nothing either.
5. After each topic file, run `conv-lint` and fix only *structural* violations — never content.
6. Halt on any row whose source text you cannot locate, and on any source item with no row.

**conventions** — whatever the table assigns to this step; `none` if it assigns none.

**verify** — `conv-lint` clean; `conv <name>` fetches each created convention; `coverage-check` gap count
strictly decreased; every source file byte-identical to before (`git diff` shows no source changes).

**done_when** — every convention row applied, linter clean, sources unchanged.

**on_fail** — halt. A missing source text is a halt, never a paraphrase.

**record** — count created, and every rule whose wording was unclear.

[↑ Step index](#step-index)

## S3 — Apply the table: role kernels

**brief** — Standing rules — the ones that cannot be per-step — into `roles/*.md`, extending the thin
kernels from the roles spec.

**scope** — `../plans/roles/`

**do**
1. For each row destined for a kernel, append the rule verbatim under a clear heading in that role's file.
2. Preserve the kernel's opening expectation-setting content; new material goes after it, since that opening
   is what makes the halt rule land.
3. If a kernel exceeds **120 lines**, halt and report: a fat kernel means something classified as standing is
   really per-step, which is a table defect, not a formatting problem.
4. Do not remove anything from an existing kernel.

**conventions** — per the table.

**verify** — every kernel under 120 lines; `coverage-check` gap count decreased; no kernel lost a
pre-existing line (`git diff` shows additions only).

**done_when** — every kernel row applied, all kernels under budget, additions only.

**on_fail** — halt, naming the kernel and the rule that overflowed it.

**record** — per-kernel line counts before and after.

[↑ Step index](#step-index)

## S4 — Apply the table: model prose

**brief** — The document taxonomy, the role↔document ownership table, the handoff model. None of it is a rule
anyone follows at a step; it is the design of the system, and it is the class most likely to be dropped
because it does not look like either of the other two.

**scope** — `../plans/planning/doc-and-session-model.md`

**do**
1. For each row destined for the model doc, add the material to the matching section, or a new section if
   none fits.
2. That document is **FINAL and frozen**. Adding harvested material into it is the amendment channel, so
   record each addition in a `## Harvest additions` section with its source id — do not silently reword
   frozen text.
3. Where harvested prose contradicts the frozen model, the **model wins**: record the contradiction as a
   finding for Dean rather than editing either side.
4. Re-check the anchors-only TOC after additions; do not add line ranges.

**conventions** — per the table.

**verify** — every TOC anchor still resolves; `coverage-check` decreased; no frozen section reworded
(`git diff` shows additions and TOC entries only).

**done_when** — every model row applied, additions logged with source ids, no reworded frozen text.

**on_fail** — halt.

**record** — every contradiction found between harvested prose and the frozen model.

[↑ Step index](#step-index)

## S5 — Drive coverage to zero and report

**brief** — Iterate until `coverage-check` reports no unmapped sources, no rows pointing nowhere, and no
orphan destinations. This step is where "nothing lost" is actually established.

**scope** — `../plans/conventions/`, `../plans/roles/`, `../plans/planning/doc-and-session-model.md`

**do**
1. Run `coverage-check`; work the three lists down.
2. **An unmapped source is a halt, not a decision.** Classifying it would be exactly the judgment call the
   split forbids. Collect all of them and halt once with the full list rather than halting repeatedly.
3. Produce a report: counts before and after, every conflict surfaced, every item you halted on.
4. Do not mark anything resolved that you resolved by choosing.

**conventions** — per the table.

**verify** — `coverage-check` exits 0; `conv-lint` clean; every source file still byte-identical to its
pre-harvest state.

**done_when** — coverage is zero **or** the run halted with a complete list of what only Dean or the
policy-writer can decide. Both are valid outcomes; a forced zero is not.

**on_fail** — halt with the full list.

**record** — the final counts and the halt list.

[↑ Step index](#step-index)

## S6 — Stop loading the old files

**brief** — Retirement means **stop loading**, not delete. Every rule still exists and still binds, from a
new location. This needs no per-rule approval because nothing is removed.

**scope** — `../plans/CLAUDE.md`, `../plans/session/CONVENTIONS.md`,
`../plans/session/CODER-CONVENTIONS.md`

**do**
1. **Refuse to start unless `coverage-check` exits 0.** Re-run it; do not trust S5's report.
2. Remove the `@session/CONVENTIONS.md` and `@session/CODER-CONVENTIONS.md` imports from
   `plans/CLAUDE.md`. Leave `@session/CURRENT.md`.
3. Add to the top of each retired file: retired, not deleted; still true; its content now lives at the named
   destinations; nothing was removed.
4. **Delete nothing.** Not a section, not a file, not a memory. Removal is a separate question requiring long
   probation and Dean's per-rule approval.
5. Confirm a fresh session in `plans/` no longer loads either file, and record how that was confirmed.

**conventions** — per the table.

**verify** — `coverage-check` exits 0 immediately before the edit; the two files are byte-identical apart
from their new header; `plans/CLAUDE.md` has exactly one import left.

**done_when** — imports dropped, both files intact plus a header, coverage verified at the moment of the
edit rather than earlier.

**on_fail** — halt. If coverage is not zero, do not proceed — this is the one step whose precondition is
absolute.

**record** — how the "no longer loaded" claim was verified, and confirmation that nothing was deleted.

[↑ Step index](#step-index)
