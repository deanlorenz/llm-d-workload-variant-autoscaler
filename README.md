# Section and convention tooling

Four scripts for fetching documentation by heading instead of by line number, plus a golden-file test
harness. Run them from the root of this worktree.

| Tool | Purpose |
|---|---|
| `scripts/sec.sh` | print one or more sections of a markdown file, addressed by heading |
| `scripts/conv.sh` | print named conventions, finding which topic file holds each one |
| `scripts/conv-list.sh` | print the computed convention index: name, status, description |
| `scripts/conv-lint.sh` | check that the conventions are structurally fetchable |

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
names its own violation and nothing else.

There is no Go here and nothing that ships in a pull request, so the usual build and test gates do
not apply. What replaces them: `bash -n` on every script, `shellcheck` where it is installed, the
golden suite above, and the rule that every documented error path exits non-zero with a message on
stderr.

## Where this code lives

These scripts are developed on their own branch and are **copied into `plans/scripts/` at kickoff**.
They are not pushed from here. Treat this worktree as the place the tools are written and tested, not
as the place they are consumed from.
