last_update: 2026-08-10T00:00:00Z
state: in-progress
current_step: S1–S7 all landed; nothing pushed; awaiting Dean's review

## Step log
- S1 · 55623480 · verify pass · harness + fixtures; run.sh reports 0 cases, exit 0; --update idempotent
- S2 · 6d8ab18a · verify pass · sec.sh single id; 4 level-arithmetic cases green; bad id exits 4 on stderr
- S3 · 0550806d · verify pass · sec.sh multi-id + error paths; 8 cases green; bad-among-good emits nothing
- S4 · b8469d9e · verify pass · conv.sh discovery, delegates to sec.sh; 12 cases green
- S5 · 6e37a1f1 · verify pass · conv-list.sh computed index; 14 cases green; order byte-stable
- S6 · 7a04f3b3 · verify pass · conv-lint.sh, 6 checks each with a pass and a fail case; 21 cases green
- S7 · b883f4ae · verify pass · README; all 6 examples executed and diffed against the text

## Gates
- `bash -n` — run on every script at every step; clean.
- `shellcheck` — **NOT INSTALLED** in this environment (`command -v shellcheck` fails). Flagging rather
  than skipping silently. No script has ever been shellchecked; that gate is unmet, not passed.
- `./tests/run.sh` — 21 cases, 0 failed, exit 0 at the final tip.
- Every documented error path was run by hand and exits non-zero with its message on stderr.
- No push, no `gh`, no DCO sign-off. `pwd` + `git branch --show-current` re-verified before all 7 commits.

## Deliverables
- `scripts/sec.sh`, `scripts/conv.sh`, `scripts/conv-list.sh`, `scripts/conv-lint.sh`
- `tests/run.sh`, `tests/cases.sh`, `tests/expected/*.out` (21 goldens), `tests/fixtures/`
- `README.md`

## Record — decisions a reviewer should check
1. **Golden format.** A golden is a transcript, not bare stdout: `exit: N`, `--- stdout ---`,
   `--- stderr ---`. The spec asked for one file per case; folding the exit code and stderr into that
   one file is what lets a golden prove "an error path exits non-zero with a message on stderr".
2. **Case registry.** S2/S3/S6 say "register cases in `tests/run.sh`". They are registered in
   `tests/cases.sh`, which `run.sh` sources — same `tests/` scope, but the file differs from the wording.
3. **Convention field syntax.** `### convention: <name>` followed by bare `description:` / `scope:` /
   `trigger:` / `status:` / `origin:` lines. Taken from the spec's own `status: probation` example; the
   spec never states the syntax outright.
4. **S3 changed S2 behavior on purpose.** Trailing blank lines are now trimmed from each section so the
   multi-id blank-line separator means exactly one blank line. Three single-id goldens were regenerated
   for that reason and lost one trailing blank line each — nothing else. Stated in the S3 commit message
   as well; no golden was ever weakened to make a tool pass.
5. **Ambiguity landed in S2, not S3.** S2 said nothing about multiple matches, and S3 forbids picking the
   first, so exiting 5 was the only behavior consistent with the spec. Implemented early rather than
   guessed at.
6. **S5 exit 4.** A directory holding markdown but declaring no conventions exits non-zero. The spec did
   not list this case; the inline rule "loud failure over silent empty output" decides it.
7. **`--dir` on `conv-list` / `conv-lint`.** The spec only gives `--dir` to `conv`. The other two need it
   to be testable against fixtures, so they have it too, same syntax.
8. **`conv-lint` heading-level rule.** Implemented as: any heading at level 2 or shallower **after a
   file's first convention marker** is a violation. The spec says "no `##` inside a convention section",
   which cannot be decided from the text alone — where a convention's intended body ends is not
   recoverable once a `##` has split it. The rule as implemented is the checkable form of the same harm.
   **Worth Dean's eye**: it forbids a topic file from using `##` sections after its conventions begin.
9. **`conv-lint` exit code with several classes.** All violations are always reported; the exit code is
   the lowest-numbered class present. A caller cannot tell "class 15 only" from "10 and 15" by code alone.
10. **Near-miss suggestions were implemented** (S4 `record` asked). Case-insensitive containment in
    either direction over all declared names — cheap and deterministic. `commit-message` suggests
    `commit-message-shape`.

## Open questions for Dean — none blocking, none guessed at
- **S5 step 1 vs step 2.** Step 1 says read `description`, `status` **and `scope`**; step 2 says print
  name, status, description. I followed step 2 and did not parse `scope`, rather than carry a field that
  is never emitted. If `scope` belongs in the output line, the format and the goldens change.
- **`shellcheck` is absent.** Install it and re-run before this is trusted, or accept `bash -n` only.

## Record — what writing the README exposed about the tools
- **`conv-lint`'s path check is CWD-relative.** Documenting it made the implicit dependency obvious: the
  paths inside a convention are written relative to some root, and the linter silently assumes that root
  is the current directory. A `--root` flag would make it explicit. Left as-is; not in any step's scope.
- **`conv-list`'s ` | ` separator is not escape-safe.** A description containing ` | ` would produce four
  fields and break a downstream parser. Nothing in the fixtures does, and no step asked for escaping, but
  `plan-lint` and the role kernels are named as future readers of this format, so it should be decided
  before they are written.
- **`sec` emits no record delimiter.** With several ids the sections are separated by a blank line only,
  so a caller cannot tell where one section ended and the next began without re-deriving it from the
  headings. Fine for a human reader, thin for a machine one.
- **Asymmetric addressing.** `sec` takes an explicit file while the three `conv` tools take a directory.
  That is deliberate (a caller of `sec` knows its file) but reads as inconsistent in the README's table.

## Not done
- Nothing pushed; no `gh` invoked. Copying into `plans/scripts/` is the kickoff commit, not this work.
- No pre-commit hook installed for `conv-lint` (S6 mentions it runs in one; installing it was not in scope).
