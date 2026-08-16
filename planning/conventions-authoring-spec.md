# Code spec — convention authoring tools

**code spec** · **Status: DRAFT** — awaiting Dean's finalization.

## At a glance

**Mission:** the write side of the convention system — `conv-new`, `conv-edit`, `conv-rename` (+
refusal-to-delete), a pre-commit hook, README — so `conventions/` is never hand-edited.

**Approach:** S1/S2 landed (`conv-new` commit `65553806`, `conv-edit` commit `57f4874a`, both on the
`plans-tooling` worktree). S3 (`conv-rename`) has an approved plan and a coder actively implementing it
as of 2026-08-16 (second attempt — the first coder session ended before seeing the approval; see
[`atomic-step-protocol-design-addendum-9.md`](atomic-step-protocol-design-addendum-9.md) for why that
kept happening and the fix). S4 (pre-commit hook) and S5 (README) not started.

**Needs you:** the open gap flagged in this spec's own Intent (no tool-mediated way to move a
convention between topic files) — still undecided, not blocking S3.

**Checklist:**
- [x] S1 `conv-new.sh` — landed.
- [x] S2 `conv-edit.sh` — landed.
- [ ] S3 `conv-rename.sh` — plan approved, coder in progress.
- [ ] S4 pre-commit hook — not started.
- [ ] S5 README — not started.
- [ ] Decide the move-between-topics gap (flagged, not designed).

Second of the migration specs. Depends on
[`conventions-tooling-spec.md`](conventions-tooling-spec.md) having landed (`sec`, `conv`, `conv-list`,
`conv-lint`).

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then start at your assigned step and read only that
step's section. Do not read the whole document. No line numbers; do not run `toc-refresh.sh` on it.

---

## Intent

**intent** — Build the write side, so `conventions/` is never edited freehand. Structure there is
load-bearing and every malformation fails **silently**: a malformed marker makes a convention
unfetchable, and a coder then halts as though it never existed.

**current call stack** — Read-side only. `conv <name>` fetches, `conv-lint` validates, `conv-list`
indexes. Nothing writes. So the harvest would be done by hand into a format the tooling depends on —
precisely what the design forbids.

**planned call stack** —

```
Dean says something normative, or an incident happens
  → policy-writer proposes            (judgment; not this spec)
  → conv-new <name> --topic <file>    creates marker + required fields, refuses duplicates
  → conv-edit <name>                  extract, replace in place, neighbours untouched
  → conv-rename <old> <new>           rename + rewrite every citation, or refuse
  → pre-commit hook                   conv-lint gate on anything staged under conventions/
```

**new components** — `scripts/conv-new`, `scripts/conv-edit`, `scripts/conv-rename`, a pre-commit hook, tests.

**new conventions** — none yet; `conventions/` is still empty at this point. Rules are stated inline per
step, and this spec's own subject matter is the first harvest candidate.

**Reassessment worth stating:** `conv-rename` was earlier called not-ready because "citation rewriting has
nothing to scan until step manifests exist". That was wrong as a blocker — fixtures can supply citations,
so it is testable now. What is still true is that its *real* input set is empty until the harvest runs.

**Open gap, flagged by Dean 2026-08-13, not yet designed:** `conv-new <name> --topic <file>` sets a
convention's topic file once, at creation, and `conv-rename <old> <new>` (S3) only renames the
convention's *name* — rewriting citations to match — within whatever topic file it already lives in.
Neither handles **moving an existing convention's content to a different topic file** while keeping its
name. This is a real, distinct operation, not a variant of either existing one: `conv-edit`'s "extract,
replace in place, neighbours untouched" mechanics assume the convention stays in its current file, and a
cross-file move needs the same atomicity discipline S3 already requires for rename (stage all edits,
restore everything on any failure) but applied to a delete-from-file-A + insert-into-file-B rather than an
in-place text replace. Concretely useful for the harvest itself: a first-pass classification (see
`harvest-classification.md`) can guess a convention's topic wrong, and today there is no tool-mediated way
to correct that — only hand-editing, which is exactly what this spec exists to prevent. Left as an open
item for finalization rather than designed here; a plausible shape is a `--move-to <file>` flag on
`conv-rename` (reusing its existing citation-rewrite machinery, since citations reference the convention by
name, not by topic file, so a move alone needs no citation rewrite at all — only a rename does) but this is
not decided.

---

## Prerequisites

Worktree `plans-tooling` already exists and holds the read-side tools. Continue there — this spec extends
the same codebase, so a separate worktree would only create a merge.

**Gates** — no Go, no `make test`, no `gofmt`. The plans lineage takes **no DCO sign-off**. Instead:
`bash -n`; `shellcheck` if installed (say so if not); `./tests/run.sh` green; every documented error path
exits non-zero with a message on stderr. **Never push.**

---

## Step index

**S1 — `conv-new`.** Create a convention with the exact marker and every required field, refusing a name
that already exists anywhere. Refusal is the feature: duplicate names make `conv` ambiguous, and the
whole no-index design rests on names being unique.

**S2 — `conv-edit`.** Replace one section in place, leaving neighbours byte-identical. This is the narrow
case of the writing problem the design parks in general: tractable here only because sections are small
and heading-delimited. Verified by round-trip, not by eye.

**S3 — `conv-rename` and refusal-to-delete.** Rename plus rewrite every citation, or refuse. A rename
that half-succeeds is worse than one that fails, so the failure mode must be atomic.

**S4 — Pre-commit hook.** `conv-lint` as a git gate, so structure is enforced against whoever edits —
human or agent, any harness. Git-level on purpose: the portable layer, not a Claude Code hook.

**S5 — Documentation.** README section per tool, every example executed.

---

<!-- ─────────────── execution detail below ─────────────── -->

## S1 — `conv-new`

**Status: LANDED, commit `65553806` on `plans-tooling`.** As-built deviation from the brief below,
worth recording rather than silently accepted: the coder implemented the duplicate-name check by
scanning the target `--dir`'s markers directly (same technique `conv.sh` itself uses to find a
convention's holder file) rather than shelling out to `conv-list.sh` as line 131 below implies —
`conv-list.sh` hard-fails with exit 3 on a directory holding zero `.md` files, which is exactly the
"fresh topic file" case S1 needs to handle cleanly. A deliberate, reasoned deviation, not an oversight.

**brief** — `conv-new <name> --topic <file>` appends a new convention section with the marker and the
five required fields. It refuses if the name exists in any topic file. Provenance is a required field, not
an optional nicety: without `origin`, a probation judgment years later is guesswork.

**scope** — `scripts/conv-new`, `tests/`

**do**
1. Validate `<name>` against `[a-z0-9-]+`; reject anything else with the reason.
2. Refuse if `conv-list` already reports that name — exit non-zero naming the file that holds it.
3. Append to `--topic <file>` (create the file with a title if absent):
   `### convention: <name>` then field lines `description`, `scope`, `trigger`, `status`, `origin`.
   `status` defaults to `active`. Accept each field as a flag; leave unsupplied ones as an empty value the
   linter will catch rather than inventing content.
4. Print the path and the created name.
5. Cases: fresh name into an existing topic; fresh name into a new topic file; duplicate name refused;
   invalid name refused.

**conventions** — none. Inline: never invent field content — an empty `description` that `conv-lint`
flags is honest, a plausible generated one is not.

**verify** — `bash -n`; `./tests/run.sh` green; after creating a convention, `conv <name>` fetches it and
`conv-lint` reports only the expected empty-field violations.

**done_when** — all four cases pass, and a created convention is immediately fetchable by `conv`.

**on_fail** — halt.

**record** — the flag names for the five fields, since the policy-writer role will script against them.

[↑ Step index](#step-index)

## S2 — `conv-edit`

**Status: LANDED, commit `57f4874a` on `plans-tooling`.** As-built note, not a deviation: the trickiest
part in practice was the section boundary on write, not on read — trailing blank lines between a
convention's content and whatever follows (next heading, or EOF) belong to the file's structure, not to
the section being replaced. A naive splice at the untrimmed boundary glued the replacement directly onto
the next heading; the fix mirrors `sec.sh`'s own read-side trim. Caught by testing against the fixture
before writing the golden, not by the golden itself — worth recording as a real instance of "verify by
running, not by reading," the same discipline this spec's own S1 already names.

**brief** — Replace a single convention's body in place. Everything above and below must come out
byte-identical; that is the whole correctness claim and it must be proven by comparison, not inspection.

**scope** — `scripts/conv-edit`, `tests/`

**do**
1. `conv-edit <name> --from <file>` replaces the named section with the contents of `<file>`.
2. Locate the section as `conv` does; replace from its heading to the next heading of the same or higher
   level; leave the rest untouched.
3. Preserve the marker line unless the replacement supplies one — a replacement that silently drops the
   marker would make the convention unfetchable, which is the failure this tooling exists to prevent.
4. Write via a temp file and atomic rename; never edit in place.
5. Cases: edit a middle section; edit the first; edit the last; a replacement lacking the marker is
   rejected.
6. **Round-trip case:** `conv <name> > a; conv-edit <name> --from a; conv <name> > b; diff a b` is empty,
   and the containing file is unchanged outside the section.

**conventions** — none. Inline: no `sed -i`; temp file plus rename.

**verify** — `./tests/run.sh` green including the round-trip; `git diff --stat` on the fixture shows only
the intended section's lines.

**done_when** — the round-trip is byte-exact and neighbours are provably untouched.

**on_fail** — halt.

**record** — whether any fixture needed a trailing-newline concession, and why.

[↑ Step index](#step-index)

## S3 — `conv-rename` and refusal-to-delete

**brief** — Rename a convention and rewrite every citation of it, or change nothing at all. Half a rename
leaves dangling citations that fail at fetch time — a coder halting on a convention that exists under
another name.

**scope** — `scripts/conv-rename`, `tests/`

**do**
1. `conv-rename <old> <new>`: validate `<new>`, refuse if it already exists.
2. Find citations of `<old>` across `--cite-dirs` (default `planning/ roles/`): step manifest lines and
   prose references.
3. Rewrite the marker and every citation. **Atomic:** stage all edits, and if any file cannot be written,
   restore everything and exit non-zero. Never leave a partial rename.
4. Report the count of citations rewritten, per file.
5. `--delete <name>` refuses while any citation exists, naming them. With zero citations it still refuses
   unless `--force-approved` is passed, because removal needs long probation and Dean's approval — the
   tool must not be the thing that makes removal easy.
6. Cases: rename with citations in two files; rename with none; rename onto an existing name refused;
   delete refused while cited; delete refused when uncited without the approval flag.

**conventions** — none. Inline: atomicity over partial success; a tool that half-applies is worse than one
that refuses.

**verify** — `./tests/run.sh` green; after a rename, `conv <new>` resolves, `conv <old>` exits non-zero,
and `grep -r <old>` over the cite dirs finds nothing.

**done_when** — all six cases pass and no case leaves a partially-renamed tree.

**on_fail** — halt. If atomic restore cannot be implemented simply, halt and say so rather than shipping a
best-effort rename.

**record** — what counts as a citation, since `plan-lint` must use the same definition.

[↑ Step index](#step-index)

## S4 — Pre-commit hook

**brief** — Enforce structure at the git layer so it binds whoever made the edit — human or agent, any
harness. This is the portable enforcement the design prefers over harness-specific hooks.

**scope** — `hooks/pre-commit-conv-lint`, `tests/`

**do**
1. A hook script that finds staged files under `conventions/`, runs `conv-lint` on them, and rejects the
   commit non-zero on any violation, printing them.
2. No staged conventions → exit 0 silently and instantly. It must not slow unrelated commits.
3. Ship it as a file plus install instructions; do **not** install it into any live `.git/hooks` —
   installation is a deliberate act by whoever owns the repo.
4. Cases: staged clean convention passes; staged malformed one is rejected; unrelated staged file is
   untouched.

**conventions** — none. Inline: the hook must not modify anything; it decides only.

**verify** — the three cases pass in a throwaway git repo created by the test, never in a real worktree.

**done_when** — a malformed staged convention cannot be committed, and unrelated commits are unaffected.

**on_fail** — halt.

**record** — the install command, and confirmation the tests used a throwaway repo rather than a live one.

[↑ Step index](#step-index)

## S5 — Documentation

**brief** — README sections for the four write-side tools, written against finished behaviour.

**scope** — `README.md`

**do**
1. One section per tool: synopsis, arguments, exit codes, a worked example run against fixtures.
2. State the two refusal policies plainly: duplicate names are refused, and deletion is refused while
   cited and again without explicit approval.
3. Document the hook's install step and that it is deliberately not auto-installed.

**conventions** — none. Inline: no plans-branch identifiers; this README travels with the code.

**verify** — every example executed and its output matches what is shown.

**done_when** — all four documented, all examples verified by running them.

**on_fail** — halt.

**record** — anything writing the docs revealed about the interfaces.

[↑ Step index](#step-index)
