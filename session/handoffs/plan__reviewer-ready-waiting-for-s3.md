from: plans-tooling-review (internal code-reviewer)
to: planner
session: plans-tooling-review

Confirming scope and understanding before starting any checker work; no code-review has been run.

**Identity/role.** I am an internal code-reviewer session launched from the `plans` branch. Read-only
with respect to code everywhere: no working-tree writes in any worktree, no git write-verbs, no
GitHub writes ever. I write review docs only — Type 6 (`planning/*-review.md`), `Status: DRAFT`
until Dean finalizes. Status file: `session/status/plans-tooling-review.md`.

**Review pipeline understanding (session/CONVENTIONS.md § Review pipeline, read directly, not from
memory):** four fixed stages, stage 1 is a pluggable set.
- Stage 0 — scope: read the Type 3 (here, the code spec), the commit list, and the diff boundaries;
  establishes what the branch *claims*.
- Stage 1 — check the code: run every available checker, producing defect candidates with no
  knowledge of intent. My only checker is the built-in `/code-review` skill at `high` or `max`.
  Checker contract: read-only (no working-tree writes, no GitHub writes, no git write-verbs);
  findings as (file, line, claim, concrete failure scenario, verdict) — a claim with no failure
  scenario is speculation and doesn't advance to stage 3; independently skippable; carries no
  authority (checker reports, I rule). I will **never** pass `--comment` or `--fix`.
  I have not invoked stage 1 yet — there is no signal that S3 is ready.
- Stage 2 — understand intent: plan-vs-diff, commit-message-vs-diff integrity, §4a token scan, DCO,
  gate results, golden-file scope, deletion classification. Only I (the review agent) do this.
- Stage 3 — merge and rule: for each stage-1 candidate, decide real-and-in-scope / real-but-backlog /
  refuted. Survivors become numbered Findings in the Type 6 doc.

**Scope of this review.** Branch `plans-tooling`
(`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans-tooling`), scoped against
`planning/conventions-authoring-spec.md` (the write-side spec: `conv-new`, `conv-edit`,
`conv-rename` + refusal-to-delete, a pre-commit hook, README). This spec depends on
`conventions-tooling-spec.md` (the read-side: `sec`, `conv`, `conv-list`, `conv-lint`) having
already landed — confirmed via `git -C plans-tooling log --oneline`: commits `55623480`..`b883f4ae`
(S1–S7 of the read-side spec) are in place, followed by `65553806` (S1: `conv-new`, "refusing
duplicate names on the computed index") and `57f4874a` (S2: `conv-edit`, "in-place section
replacement proven by round trip") from the write-side spec.

Per the spec's own step index, this leaves S3 (`conv-rename` and refusal-to-delete), S4 (pre-commit
hook), S5 (documentation) still to land. A new coder session is currently working S3. Per the spec:
S3 must rename a convention and rewrite every citation (default `--cite-dirs planning/ roles/`)
atomically — stage all edits, restore everything on any partial failure — and `--delete <name>`
must refuse while cited, and refuse again when uncited unless `--force-approved` is passed. Six
cases are specified (rename with citations in two files; rename with none; rename onto an existing
name refused; delete refused while cited; delete refused when uncited without approval; implicitly,
no partially-renamed tree in any failure path). Gates for this lineage: no Go/test/gofmt, no DCO —
instead `bash -n`, `shellcheck` if installed, `./tests/run.sh` green, every documented error path
exits non-zero with a stderr message. Never push (not my concern as reviewer, but noting it's the
coder's constraint too).

**Current state / next action.** I am not starting `/code-review` yet — there is no signal that S3
is ready. I will wait for a handoff addressed to me (this reviewer) confirming S3 is ready to
review, then run stage 1 (`/code-review` at high or max on the S3 diff), then proceed through
stages 2–3 and write `planning/plans-tooling-review.md` (or similarly named Type 6 doc) with
`Status: DRAFT`.
