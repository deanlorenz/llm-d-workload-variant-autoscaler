# Section, convention, and step-gate tooling

Scripts for fetching documentation by heading instead of by line number, plus two gates that check a
coder's work and a spec's shape mechanically, plus a golden-file test harness. Run everything from the
root of this worktree.

| Tool | Purpose |
|---|---|
| `scripts/sec.sh` | print one or more sections of a markdown file, addressed by heading |
| `scripts/conv.sh` | print named conventions, finding which topic file holds each one |
| `scripts/conv-list.sh` | print the computed convention index: name, status, description |
| `scripts/conv-lint.sh` | check that the conventions are structurally fetchable |
| `scripts/step-check` | post-step gate: scope containment, sign-off policy, judgment mark |
| `scripts/plan-lint` | check a code spec's step schema, convention citations, and judgments |

`scripts/conv-new.sh`, `scripts/conv-edit.sh`, and `scripts/conv-rename.sh` are the write-side
counterparts already built in this worktree — they add, edit, and rename conventions — but are
documented under their own migration step rather than here.

## Two addressing rules that are easy to get wrong

**An id is a heading slug or the exact heading text.** The slug is the GitHub anchor form: lowercased,
punctuation dropped, spaces turned into hyphens. `## Alpha child` is addressable as either
`alpha-child` or `Alpha child`. If two headings in a file produce the same slug, that id is ambiguous
and every tool refuses it rather than picking one.

**A section ends at the next heading of the same or higher level.** A deeper heading stays inside. So
a `##` section swallows a `####` subsection that follows it, and is terminated by the next `##` or
`#`. This is why `conv-lint.sh` rejects a `##` heading placed after a convention marker: it would
silently truncate the convention above it.

**No tool takes or emits line numbers.** Nothing here accepts an offset or a length, and nothing here
prints a line range. Line numbers are a global index over a mutable file, so any insertion
invalidates every number below it. The only place a line number appears at all is inside an error
message, to help a human find a malformed heading.

## `scripts/sec.sh`

```
sec.sh <file> <id>...
```

Prints each addressed section, heading line included, in the order the ids were given, separated by
one blank line. Trailing blank lines are trimmed from each section so that separator is always
exactly one blank line. Every id is resolved before anything is printed, so a call that fails emits
no partial section.

| Exit | Meaning |
|---|---|
| 0 | every section printed |
| 2 | usage error |
| 3 | file missing or unreadable |
| 4 | at least one id matched no heading; every such id is named on stderr |
| 5 | at least one id matched more than one heading; every colliding heading is named |

When both 4 and 5 apply, both are reported and the exit code is 4.

Worked example — a section that contains a deeper subsection:

```
$ ./scripts/sec.sh tests/fixtures/doc-a.md beta
## Beta

Beta body before the subsection.

#### Beta deep

A level-4 subsection. Fetching `beta` must absorb it — a deeper heading is
part of the section, not a terminator.

More Beta body after the level-4 subsection.
```

An ambiguous id fails rather than choosing (output on stderr):

```
$ ./scripts/sec.sh tests/fixtures/doc-a.md set-up
sec: ambiguous id in tests/fixtures/doc-a.md: set-up matches 2 headings
sec:   line 26: ## Set Up
sec:   line 30: ## set-up
$ echo $?
5
```

## `scripts/conv.sh`

```
conv.sh [--dir <dir>] <name>...
```

A convention is declared by a heading of the exact form `### convention: <name>`. `conv.sh` scans
`<dir>/*.md` for that marker, then hands the file and heading to `sec.sh` — it holds no section logic
of its own. `<dir>` defaults to `conventions/`. There is no index file: the marker carries the name,
so a scan cannot go stale the way a stored index can.

| Exit | Meaning |
|---|---|
| 0 | every convention printed |
| 2 | usage error |
| 3 | directory missing, or it holds no `.md` files |
| 4 | at least one name is not defined anywhere; near-miss names are suggested |
| 5 | at least one name is defined in more than one file; every file is named |

When both 4 and 5 apply, both are reported and the exit code is 4. Reporting duplicate names is
`conv-lint.sh`'s job; `conv.sh`'s job is to refuse to choose between them.

Worked example:

```
$ ./scripts/conv.sh --dir tests/fixtures/conventions one-commit-per-step
### convention: one-commit-per-step
description: Each spec step lands as exactly one commit.
scope: spec-driven coding sessions
trigger: finishing a step
status: active
origin: atomic-step protocol design

One commit per step keeps the step boundary reviewable. A step that needs two
commits is two steps.
```

## `scripts/conv-list.sh`

```
conv-list.sh [--dir <dir>]
```

Prints one record per convention, three fields separated by ` | `:

```
<name> | <status> | <description>
```

sorted by name in the C locale, so the output is byte-identical across runs and diffs cleanly.
Readers should split on ` | ` and expect exactly three fields.

The status field is rendered rather than copied. `probation` prints as uppercase `PROBATION` to draw
the eye: such a convention is still binding, and the mark means "not yet ratified", never "not in
force". A convention with no `status` line prints `NO-STATUS`; any other value prints verbatim. A
convention with no `description` line prints `(NO DESCRIPTION)` rather than being skipped, since
skipping it would hide the very defect `conv-lint.sh` exists to find.

| Exit | Meaning |
|---|---|
| 0 | index printed |
| 2 | usage error |
| 3 | directory missing, or it holds no `.md` files |
| 4 | the directory holds markdown but declares no conventions |

Worked example:

```
$ ./scripts/conv-list.sh --dir tests/fixtures/conventions
archive-never-delete | active | Archive a finished branch instead of deleting it.
commit-message-shape | active | Subject line is imperative, under 72 characters, no trailing period.
no-dco-on-plans | PROBATION | The plans lineage takes no DCO sign-off.
no-push-without-confirmation | active | Never run git push without explicit confirmation for that push.
one-commit-per-step | active | Each spec step lands as exactly one commit.
verify-cwd-before-commit | active | Run pwd and git branch --show-current immediately before every commit.
```

## `scripts/conv-lint.sh`

```
conv-lint.sh [--dir <dir>]
```

Clean input produces no output and exits 0. Bad input reports every violation on stderr, with file,
line, and convention name, and exits non-zero. All violations are always reported; a linter that
reported one problem of six would cost six runs.

| Exit | Check |
|---|---|
| 0 | clean |
| 2 | usage error |
| 3 | directory missing, or it holds no `.md` files |
| 10 | marker format — the name must match `[a-z0-9-]+` and the marker must sit at level 3 |
| 11 | name uniqueness — a name may be declared only once across all topic files |
| 12 | required fields — `description`, `scope`, `trigger`, `status`, `origin` must all be present |
| 13 | status value — must be exactly `active` or `probation` |
| 14 | heading level — no heading at level 2 or shallower after a file's first convention marker |
| 15 | referenced path — a backtick-quoted token that looks like a path must resolve on disk |

The exit code is the lowest-numbered class present, so a caller can branch on the most structural
failure while still seeing everything else on stderr.

A token counts as a path for check 15 if it contains `/` or ends in `.md` or `.sh`, and it is
resolved relative to the current directory — so run `conv-lint.sh` from the root that the paths are
written against.

Worked examples — a clean directory says nothing:

```
$ ./scripts/conv-lint.sh --dir tests/fixtures/conventions
$ echo $?
0
```

and a defective one names the defect (output on stderr):

```
$ ./scripts/conv-lint.sh --dir tests/fixtures/bad/fields
conv-lint: [12] tests/fixtures/bad/fields/fields.md:5: convention missing-two-fields is missing required field(s): trigger origin
$ echo $?
12
```

## `scripts/step-check`

```
step-check --scope <path> [--scope <path> ...] --lineage code|plans
           [--allow-untracked <glob>]...
           [--ledger <file> --step <id> [--handoffs-dir <dir>]]
```

Runs once a coder believes a step is finished, replacing a human eyeballing every write with a
mechanical check. Three independent checks, run from inside the git working tree the step happened in:

- **Scope containment.** Every changed path — `git status --porcelain`: modified, staged, and
  untracked alike — must equal a declared `--scope` path or sit beneath one. Bias is toward refusal:
  a path this script cannot place inside scope counts as outside it, and calling it with no `--scope`
  at all is refused rather than read as "everything is permitted".
- **Sign-off policy.** `--lineage` has **no default** — an unspecified or unrecognised value is a
  usage error, never a guess. The two lineages want opposite things from the tip commit (`code`
  requires `Signed-off-by`, the plans lineage forbids it), so defaulting to either would be silently
  wrong on the other half of the time. On a pass, the applied rule is printed to stdout so a clean run
  says what it checked, not only that it passed.
- **Judgment mark.** With `--ledger` and `--step` both given, verifies the proceed-and-mark obligations
  for a coder allowed to proceed past a reversible ambiguity rather than halt on it, against that
  coder's own `session/status/<branch>.md`: an isolated, tagged, surfaced commit for every judgment
  the ledger names, and — independent of `--step` — no `judgment/*` tag left with no ledger entry at
  all. `--ledger` omitted skips this whole check and says so on stderr, so a caller cannot mistake "no
  flag" for "checked and clean".

| Exit | Meaning |
|---|---|
| 0 | clean |
| 2 | usage error (bad arguments, not inside a git working tree, no commits yet, `--lineage`/`--step` missing or invalid) |
| 20 | scope containment: a change landed outside every declared scope path |
| 21 | scope containment: no `--scope` was given at all |
| 30 | sign-off policy: the tip commit violates the declared lineage's rule |
| 40 | judgment mark: no tag for a ledger-named judgment |
| 41 | judgment mark: tag not isolated (out-of-scope path, shares a commit with recorded step work, or isolation cannot be established) |
| 42 | judgment mark: no handoff surfaces the judgment |
| 43 | judgment mark: a `judgment/*` tag has no ledger entry at all |

All violations found are reported before exiting; the exit code is the lowest-numbered class present.

Worked example — a clean step, checked against its own scope (the test suite's own throwaway-repo
builder, run by hand here rather than through `tests/run.sh`):

```
$ ./tests/git-run.sh /tmp/demo ./tests/step-check-scope-repo.sh clean -- \
      step-check --scope src/a.md --lineage plans
step-check: --ledger not given; judgment-mark checks skipped
step-check: lineage=plans: no Signed-off-by on the tip commit, as required
$ echo $?
0
```

and a change outside the declared scope refuses (output on stderr; the judgment-mark skip notice
still prints regardless, since `--ledger` was not given either way):

```
$ ./tests/git-run.sh /tmp/demo ./tests/step-check-scope-repo.sh out-of-scope-modified -- \
      step-check --scope src/a.md --lineage plans
step-check: [20] change outside declared scope: other/c.md
step-check: --ledger not given; judgment-mark checks skipped
$ echo $?
20
```

## `scripts/plan-lint`

```
plan-lint [--dir <conventions-dir>] [--no-conventions]
          [--judgments <repo-dir>] <spec-file>
```

Turns a code spec's completeness into a machine check: every `## S<n>` step section must carry all
eight fields (`brief`, `scope`, `do`, `conventions`, `verify`, `done_when`, `on_fail`, `record`), the
`## Intent` block must carry its own five, every step must have a brief inside `## Step index`, every
cited convention name must resolve, no line-number addressing may survive anywhere in the file, and no
`judgment/*` tag naming one of this spec's steps may sit unresolved.

`--no-conventions` is a **temporary migration flag**, for use before `conventions/` exists yet: it
skips name resolution, but always warns on stderr that it did — resolution silently not running would
look identical to "resolved and clean". It is expected to be dropped once every spec citing a
convention has a `conventions/` to resolve against. `--judgments` works the same way for the
unresolved-judgment check: omitted skips and announces, given points at the git repository (a coder's
own worktree, not this one) whose `judgment/*` tags to consider.

Clean input produces no output (besides any skip announcements above) and exits 0. Bad input reports
every violation before exiting non-zero — never stops at the first.

| Exit | Meaning |
|---|---|
| 0 | clean |
| 2 | usage error |
| 3 | spec file missing or unreadable |
| 20 | step schema: a step is missing one or more of the eight fields |
| 21 | step schema: no Step index section, or a step has no brief in it |
| 22 | step schema: the Intent block is missing one or more of its five fields |
| 30 | convention resolution: a cited name does not resolve via `conv-list.sh` |
| 31 | convention resolution: a step's conventions field is absent or empty |
| 32 | addressing: a line-number reference survives somewhere in the file |
| 40 | unresolved judgment: a `judgment/*` tag naming a step in this spec is neither reverted nor decided |

The exit code is the lowest-numbered class present.

Worked example — a spec fixture copied from a real spec, clean:

```
$ ./scripts/plan-lint --dir tests/fixtures/conventions tests/fixtures/plan-lint/clean-spec.md
plan-lint: --judgments not given; unresolved-judgment checks skipped
$ echo $?
0
```

and one citing a convention that does not exist (output on stderr; a real citation in the same
manifest, `one-commit-per-step`, resolves silently alongside it):

```
$ ./scripts/plan-lint --dir tests/fixtures/conventions tests/fixtures/plan-lint/minimal-spec.md
plan-lint: --judgments not given; unresolved-judgment checks skipped
plan-lint: [30] tests/fixtures/plan-lint/minimal-spec.md: step S1 cites unknown convention: made-up-name
$ echo $?
30
```

## Tests

```
./tests/run.sh            compare every case against its golden; non-zero if any differ
./tests/run.sh --update   regenerate the goldens deliberately
```

Cases are registered in `tests/cases.sh` by calling `case_register <name> <command>...`. Each case
runs with this worktree root as the working directory, and its transcript — exit code, then stdout,
then stderr — is compared with `tests/expected/<name>.out` using `diff`. Recording the exit code and
stderr in the golden is what keeps an empty result distinguishable from a failure, and it means error
paths are registered exactly like success paths.

Fixtures live under `tests/fixtures/`. `doc-a.md` carries the awkward heading shapes on purpose:
nested levels, a level-4 subsection inside a level-2 section, two headings that slug identically, and
a section running to end-of-file. The `bad/` subdirectories hold one defect each, so a failing case
names its own violation and nothing else. `tests/fixtures/plan-lint/` holds `plan-lint`'s own spec
fixtures the same way — `clean-spec.md` is a copy of a real spec, the rest are that shape with one
defect each.

`step-check`'s sign-off and judgment-mark cases, and `plan-lint`'s unresolved-judgment cases, need
real git state — commits, tags, sometimes a real `git revert` — that no static markdown fixture can
represent. Each such case builds a throwaway repository via a small per-suite builder script
(`tests/step-check-scope-repo.sh`, `tests/step-check-signoff-repo.sh`,
`tests/step-check-judgment-repo.sh`, `tests/plan-lint-judgments-run.sh`), and never touches this
worktree's own git state. `tests/git-run.sh` wipes a scratch directory, hands it to one of those
builders, `cd`s in, and runs the command under test — `step-check` expects to run from inside the
repo it is checking. `plan-lint` does not: it takes a judgments repo as one argument among several
rather than expecting to run from inside it, so `tests/plan-lint-judgments-run.sh` builds without
ever changing directory.

There is no Go here and nothing that ships in a pull request, so the usual build and test gates do
not apply. What replaces them: `bash -n` on every script, `shellcheck` where it is installed, the
golden suite above, and the rule that every documented error path exits non-zero with a message on
stderr.

## Where this code lives

These scripts are developed on their own branch and are **copied into `plans/scripts/` at kickoff**.
They are not pushed from here. Treat this worktree as the place the tools are written and tested, not
as the place they are consumed from.
