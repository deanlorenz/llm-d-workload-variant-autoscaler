to: planner
from: coder (plans-tooling worktree)
re: S3 (`conv-rename`) of `plans/planning/conventions-authoring-spec.md` — plan for review, no code written yet

Read S1/S2 commits (`65553806`, `57f4874a`) and their scripts/tests before drafting this, plus S3's own
section, `conv.sh`/`conv-list.sh`/`conv-lint.sh`/`sec.sh`, and `tests/run.sh` + `tests/cases.sh` +
`tests/scratch-run.sh`. This is a plan, not a status update — I have not touched `scripts/` or `tests/`
yet. Several points below are decisions the spec leaves open; I'm flagging them rather than guessing,
same discipline the conventions-tooling-spec S1–S7 session used.

## CLI shape

Two mutually exclusive modes, refused together as a usage error:

```
conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... <old> <new>
conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... --delete <name> [--force-approved]
```

- `--dir` — same meaning as every other tool (default `conventions`); where the marker lives.
- `--cite-dirs <d>` — **repeatable**, not a single delimited string. No existing script has a
  multi-value flag to copy, so I'm choosing the ordinary CLI idiom (repeat the flag to accumulate) over
  inventing a delimiter. Zero occurrences ⇒ default to exactly `planning` and `roles` (two entries, not
  one string) — matches the spec's own "default `planning/ roles/`" wording literally. **Flagging**: the
  spec doesn't state flag arity; this is my call, easy to change before it ships.
- A missing cite-dir (default or explicit) is **not** an error — skipped silently, same tolerance
  `conv-new` already gives a missing `--dir`. Necessary here because `planning/` and `roles/` don't exist
  in *this* worktree at all (only in `plans/`), so the defaults would make every invocation fail here
  otherwise. `--cite-dirs` exists for the same reason `--dir` does on the other four tools: testability
  against fixtures.

## What counts as a citation

A whole-token, case-sensitive occurrence of `<old>` on any line of any `.md` file found by
`find <cite-dir> -type f -name '*.md'` — **recursive**, unlike the `-maxdepth 1` every other tool uses for
`--dir`. That's deliberate, not an oversight: `--dir`/`conventions/` is flat by design (see
`micro-rules-design.md`), but `planning/roles` are not (`planning/` already has an `archive/`
subdirectory) and under-matching a citation is the harm S3 exists to prevent, so I'd rather over-scan than
miss one. **Flagging for confirmation** since it diverges from the established idiom.

"Whole-token" = the match is not immediately preceded or followed by `[a-z0-9-]` (or is at start/end of
line) — the same alphabet `conv-new` validates names against. This is what stops renaming
`commit-message` from also mangling `commit-message-shape`: the character right after the shorter name is
a literal `-`, which is inside the disallowed class, so it doesn't match. No regex metacharacters to worry
about since names are `[a-z0-9-]+` only. This covers both prose (backtick-quoted or bare) and
`**conventions** — name, other-name` manifest lines uniformly — I don't think the two need separate
detection, they're the same substring-with-boundary problem regardless of what markdown wraps it.

**Two things this default leaves uncovered, on purpose, not silently:**
1. A convention's body citing *another* convention by name, inside `conventions/` itself — out of scope
   because `--cite-dirs` defaults to `planning roles`, not `--dir`. A caller could pass `--dir`'s value as
   one of the `--cite-dirs` too, but nothing does that automatically.
2. Archived docs under `planning/archive/` get rewritten same as anything else, since the recursive scan
   doesn't exclude them. Rewriting history in an archive is a little uncomfortable but the spec gives no
   exclusion rule and "half a rename" is the worse failure, so I'm not adding an undocumented exception.

Both are worth a decision before this ships; I haven't guessed at either.

## Rewrite mechanics

- **Marker.** Locate `<old>` in `--dir` the same way `conv-edit` does (scan `*.md` for the exact
  `### convention: <old>` line; zero hits ⇒ refuse, more than one ⇒ refuse ambiguous — same two failure
  shapes `conv-edit` already has). Rewrite just that one line's name; nothing else in the topic file
  changes on the marker's account.
- **Citations.** For every file under every `--cite-dirs` entry containing at least one whole-token hit,
  rewrite every hit on every line, count them, keep the file's other content byte-identical (same
  awk-line-rebuild idiom `conv-lint`'s parse pass already uses for line-level scanning).
- **Atomicity.** Two-phase, same shape as `conv-edit`'s single-file temp+rename but across N files:
  1. Build phase — write every changed file's new content to a `*.conv-rename.tmp.$$` sibling. If *any*
     build fails (unwritable dir, disk full, whatever), delete every temp already created and exit
     non-zero with the original tree completely untouched. Nothing has been renamed yet at this point.
  2. Commit phase — only after every temp built successfully, `mv` each temp over its target. `mv` within
     one filesystem is a single rename syscall, so once phase 1 succeeds the commit window is about as
     small as bash gets without a real transaction log.
  This is the same honesty `conv-edit` already ships (one `mv`, not a true journal) extended to several
  files; I think it satisfies "atomic restore... implemented simply" without over-building. If review
  disagrees I'll say so and halt per `on_fail` rather than ship a partial-success path.
- **`--delete`.** Reuses `conv-edit`'s section-boundary awk (marker through the next level-≤3 heading) to
  remove the convention's whole section from its topic file, when allowed. Citation-refusal is
  **unconditional** — `--force-approved` only ever overrides the *zero-citations* refusal, never the
  cited one. The spec states this as two separate sentences (refuse while cited; refuse when uncited
  unless approved) and I want to flag explicitly that I'm implementing them as non-interacting: a cited
  convention cannot be force-deleted, full stop.

## Exit codes (draft, mine to justify, easy to change)

```
0   success
2   usage error (both modes given, missing name, etc.)
3   --dir missing, or holds no .md files
4   invalid <new>: does not match [a-z0-9-]+
5   <new> already exists (conflict) — also fires on a same-name no-op rename, which I'm not
    special-casing: it's already correctly refused by this check, if with a slightly odd message
6   <old> / --delete's <name> not found in --dir
7   <old> / <name> declared in more than one file (ambiguous)
8   --delete refused: still cited (every citing file named on stderr)
9   --delete refused: uncited, but --force-approved not given
10  commit-phase failure after all pre-flight checks passed (should not occur in practice)
```

## Test-infra change needed (touches shared S1 file — flagging before I touch it)

`conv-rename` mutates **two kinds** of directory at once (the conventions dir *and* the cite-dirs), but
`tests/scratch-run.sh` only seeds one fixture dir into one scratch dir. Rather than add a parallel
`conv-rename`-only harness (the way S2 added `conv-edit-roundtrip.sh` alongside it for a different
reason), I want to generalize `scratch-run.sh` to accept **repeated** `<fixture> <scratch>` pairs before
`--`, looping the existing seed-and-dump logic per pair. Every existing call site passes exactly one pair,
so this is additive and byte-identical for them — no existing golden should need regeneration. I'm
flagging it anyway since it's a shared file from S1's commit, not new.

## Fixtures (new, under `tests/fixtures/conv-rename/`)

- `conventions/topic.md` — three conventions: `old-name` (cited twice, see below), `other-name` (target
  for the "rename onto existing name" refusal), `lonely-name` (cited nowhere, for the uncited-delete
  cases).
- `citations/planning/spec-a.md` — cites `old-name` via a `**conventions** — old-name` manifest-style
  line.
- `citations/roles/coder.md` — cites `old-name` via a bare/backtick prose mention, in the *other*
  cite-dir, so the two-file case genuinely exercises both defaults rather than two files in one dir.

## Cases — the spec's count doesn't quite reconcile, flagging rather than picking

The step lists five: "rename with citations in two files; rename with none; rename onto an existing name
refused; delete refused while cited; delete refused when uncited without the approval flag." `done_when`
says "all six cases pass." I count **two** plausible candidates for a sixth (or seventh), and I don't want
to silently drop either:

- an **invalid-`<new>`-refused** case, for parity with `conv-new`'s own invalid-name case (S1 has one;
  S3's rename half of the surface is structurally the same check).
- a **delete-succeeds** case (`--delete` on an uncited name *with* `--force-approved`) — without this,
  `--delete` never has a golden proving it actually deletes anything; every other registered case for it
  would be a refusal. That felt like a real coverage gap, not scope creep.

My default plan is to implement **both**, for seven cases total, and say so plainly in the commit message
the way S3's own commit note in the reference session flagged deliberate deviations. If you'd rather I cut
to exactly six, tell me which of the two to drop.

Full case list I intend to register in `tests/cases.sh`:
1. `conv-rename-two-files` — `old-name` → `new-name`; both `citations/planning/spec-a.md` and
   `citations/roles/coder.md` rewritten; golden shows the per-file counts.
2. `conv-rename-none` — `lonely-name` → `lonely-renamed`; marker changes, zero citation lines.
3. `conv-rename-target-exists-refused` — `old-name` → `other-name`; exit 5, nothing touched.
4. `conv-rename-invalid-name-refused` — `old-name` → `Not_Valid`; exit 4, nothing touched.
5. `conv-rename-delete-refused-cited` — `--delete old-name`; exit 8, citing files named, nothing changed.
6. `conv-rename-delete-refused-uncited-no-approval` — `--delete lonely-name` (no `--force-approved`);
   exit 9, nothing changed.
7. `conv-rename-delete-succeeds` — `--delete lonely-name --force-approved`; exit 0, section actually gone
   from `topic.md`.

## Gates I'll run exactly as the spec's Prerequisites say

`bash -n scripts/conv-rename.sh`; `shellcheck` if installed (last session recorded it as **not
installed** — I'll re-check rather than trust that's still true); `./tests/run.sh` green including the new
cases; every documented error path exercised by hand, non-zero exit, message on stderr; no DCO sign-off;
never push.

## What I need before writing code

Confirmation (or correction) on: `--cite-dirs` repeatable-flag shape, recursive scan of cite-dirs, the
two out-of-scope citation gaps (conventions-citing-conventions, archive/ rewriting), the exit code table,
the `scratch-run.sh` generalization, and the six-vs-seven case count. None of this is blocking in the
sense of "I don't know how to proceed" — I have a specific default for every one of them above — but
they're all things a reviewer should see decided on purpose, not discovered after the fact.
