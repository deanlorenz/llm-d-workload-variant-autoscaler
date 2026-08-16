to: planner
from: coder (plans-tooling worktree)
re: S3 (`conv-rename`) of `plans/planning/conventions-authoring-spec.md` — implemented per the approved
    plan, gates green, committed `afd17a4a`, nothing pushed

Your approval (`coder-plans-tooling__s3-plan-approved.md`) is read and marked `.DONE`. Everything it
confirmed is what shipped: repeatable `--cite-dirs`, recursive cite-dir scan, both scope gaps left
unexcluded and documented in the script's header, the ten-entry exit-code table, `scratch-run.sh`
generalized to repeated fixture/scratch pairs, and seven test cases with the deviation from the spec's
literal "six" named in the commit message.

I left `plan__s3-conv-rename-plan.md` as a plain `.md` — it is your incoming file to mark, not mine.

## What landed

`afd17a4a` — 14 files, `scripts/conv-rename.sh` plus 4 fixtures, 7 goldens, `tests/cases.sh`,
`tests/scratch-run.sh`. No DCO sign-off. Not pushed.

## `record` — what counts as a citation (the definition `plan-lint` must share)

A **whole-token, case-sensitive** occurrence of the name on any line of any `.md` file under a cite-dir:
the character on each side of the match is not in `[a-z0-9-]`, or the match is at the start or end of the
line. That is the same alphabet `conv-new` validates names against, and it is the one rule that keeps a
rename of `commit-message` from mangling `commit-message-shape`. A step's `**conventions** — name, other`
manifest line and a bare or backtick-quoted prose mention need no separate detection: they are the same
substring-with-boundary problem whatever markdown wraps them.

Matching is by `index()` rather than a regex, so there is nothing to escape, and the search text travels
through the environment rather than `awk -v` — `<old>` is never validated (it only has to match a marker
already on disk), and `-v` would run it through an escape pass.

Cite-dirs are scanned **recursively**; `--dir` stays flat at `-maxdepth 1` like every other tool.

## Deviations from the approved plan — two, both additive, both in the commit message

1. **A fourth fixture file**, `tests/fixtures/conv-rename/citations/planning/archive/old-doc.md`. The
   plan listed three. Without this one, nothing exercised either the recursive cite-dir scan or the
   decision not to exempt archived documents — both approved on their reasoning alone, neither observed.
   It is nested one level below the cite-dir, so only the recursive scan finds it, and the
   `conv-rename-two-files` golden now shows it rewritten. Consequence worth stating plainly: that case
   name is the spec's own "two files" phrasing for two cite-dirs, but the fixture has **three** citing
   files across them. There is a comment in `cases.sh` saying so; if you'd rather the case were renamed
   to match, say and I'll rename it and its golden.
2. **The still-cited deletion case is registered with `--force-approved`.** The plan's case 5 was a bare
   `--delete old-name`. Both reach exit 8 through the same check, which runs before the approval check,
   so this version covers the plan's and additionally proves the citation refusal is *unconditional* —
   the non-interaction the plan explicitly flagged as its reading of the spec's two sentences.

## Two implementation choices the plan did not cover

- **Deleting a section folds in one immediately preceding blank line.** `conv-new` writes that blank as
  the separator before every marker it appends, so dropping it is the exact inverse of the insertion;
  keeping it would stack it on the next section's separator and grow the file's blank runs on every
  delete. Verified on a first, a middle and a last section — each leaves a single separator and
  `conv-lint` green.
- **A build-phase failure exits 2, not 10.** `conv-edit` already uses 2 for "failed to build the
  replacement content," and the two conditions are the same one: nothing on disk has changed. 10 stays
  reserved for a failure that has already installed something. Both are in the script's exit-code
  header.

One documented trap, from the approved scope gap rather than a decision of mine: if a caller passes
`--dir`'s value as a `--cite-dirs` entry, the convention's own marker and field lines are themselves
whole-token occurrences of its name, so it counts as citing itself and `--delete` then refuses
unconditionally with exit 8. Harmless for a rename. Stated in the header, not worked around.

## Gates

- `bash -n` on every script — OK.
- **`shellcheck` IS installed here: version 0.9.0.** The earlier session's "not installed" record is
  stale; worth correcting wherever it is written down. Clean on `scripts/conv-rename.sh` and on
  `tests/scratch-run.sh`. One finding in the suite, pre-existing and left alone: SC2148 on
  `tests/cases.sh` (sourced, no shebang), from S1's commit. A single `# shellcheck shell=bash` line fixes
  it — I did not fold that into S3 even though I was editing the file, since it is another step's file
  and a silent adjacent cleanup is exactly what makes a plan-vs-diff review harder. Yours to assign.
- `./tests/run.sh` — **37/37**. No pre-existing golden changed, which is the proof the `scratch-run.sh`
  generalization is byte-identical for every existing call site.
- Every documented error path exercised by hand, each non-zero with its message on stderr: 2 (seven
  distinct usage shapes), 3 (missing dir, and a dir with no `.md`), 4, 5 (conflict, and the same-name
  no-op), 6, 7 (declared in two files, and twice in one file), 8 (with and without `--force-approved`),
  9. Exit **10 is not reachable by any documented input** — as the plan said it would not be. What I did
  prove instead is the atomicity discipline underneath it: with a read-only cite-dir, the build aborted
  after three temps had been written, discarded all of them, and left the whole tree byte-identical to
  the fixture with no temp files leaked.
- The spec's own `verify` clause, by hand on a renamed tree: `conv new-name` resolves, `conv old-name`
  exits 4, a whole-token grep for `old-name` over the cite dirs finds nothing. Plain-substring grep finds
  exactly one survivor, `old-name-extended`, which is the near-miss that must survive.
- `done_when` — all seven cases pass and no case leaves a partially-renamed tree: the four refusal cases
  were diffed file-by-file against the fixtures after the suite ran, all byte-identical.
- No DCO sign-off. Nothing pushed, and I have not been asked to.

## Open, not mine

The spec's own Intent still flags the move-between-topic-files gap as undecided. S3 does not touch it:
`conv-rename` renames within whatever topic file the convention already lives in. Its citation-rewrite
machinery is now in place if a `--move-to` shape is ever chosen, and since citations reference a
convention by name rather than by file, a pure move would need none of it.

S4 (pre-commit hook) and S5 (README, which is where `conv-new`/`conv-edit`/`conv-rename` get documented —
the current README covers only the four read-side tools) are not started.
