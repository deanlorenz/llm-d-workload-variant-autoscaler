last_update: 2026-08-17T00:00:00Z
state: in-progress
current_step: step-gates-spec.md S3 landed (commit 028b402f); starting S4 (plan-lint, step schema). S1-S3 of conventions-authoring-spec.md remain landed as below and untouched this session.

## Role and scope
Coder session. Branch/worktree: `plans-tooling` only (this worktree is my full scope — I never write
outside it except this status file and handoffs under `plans/session/handoffs/`, both reached by absolute
path on the shared plans worktree filesystem). Not a planner: I execute the steps I'm assigned, I don't
redesign the spec.

Current assignment (this session, 2026-08-17): all of `plans/planning/step-gates-spec.md`, S1 through S7,
handed to a coder by Dean despite its own `Status: DRAFT` line — Dean confirmed the DRAFT tag means
"not yet reviewed", not "incomplete", and said to proceed regardless.

Prior assignment (earlier session, landed and unrelated to this one): S3 of
`plans/planning/conventions-authoring-spec.md` (`scripts/conv-rename`). Kept verbatim below rather than
overwritten — this status file is one file per branch, not per spec, and the earlier work is still the
most recent state of that spec.

Note: `conventions/` in this worktree is an untracked leftover from an earlier planner trial, not part of
either spec this worktree has executed — left untouched throughout.

## Step log — step-gates-spec.md (this session)
- S1 · a04ca96e · landed · `scripts/step-check` scope containment (git status vs declared --scope;
  untracked counts; empty scope refused; rename entries count both sides)
- S2 · 3cbaa408 · landed · `scripts/step-check` sign-off policy per lineage (--lineage code|plans
  mandatory, no default; checks HEAD's own commit message for `Signed-off-by:`)
- S3 · 028b402f · landed · `scripts/step-check` judgment mark (Addendum 1's isolate/tag/surface,
  mechanically; plus the reverse unlogged-tag check)
- S4-S7 (`scripts/plan-lint`, README) — not started as of this checkpoint.

### Design decisions recorded (none required a judgment-mark — see below)
- **Tool names have no `.sh` suffix**: `scripts/step-check` / `scripts/plan-lint`, exactly as the spec's
  own scope/Intent fields write them throughout — a deliberate departure from every prior tool in this
  worktree (`sec.sh`, `conv.sh`, …), taken literally rather than corrected.
- **Ledger format** (`--ledger <file>`, read by S3): reuses the step-log line shape
  `S<n> · commit <sha> · verify pass · <one line>` that `atomic-step-protocol-design.md` §Coder state
  already specifies for ordinary step work (this file uses the same shape, just above), and adds a
  parallel `S<n> · judgment <slug> · <ambiguous/assumed/why/revert/decision prose>` line for Addendum 1's
  proceed-and-mark obligations — that second shape was not specified anywhere and had to be invented.
- **`--step <id>` flag added** (not in the Intent block's abbreviated call-stack diagram) — required
  together with `--ledger`, since "at this step" (S3's own brief) needs something to scope the forward
  judgment checks against; the ledger accumulates across a whole run. Added the same way `--ledger` itself
  was added beyond that diagram.
- **`--handoffs-dir` default is lineage-conditional** (`session/handoffs` for `plans`,
  `../plans/session/handoffs` for `code`) — derived from CODER-CONVENTIONS.md §5.2's own description of
  where a coder's handoffs actually live relative to its worktree; overridable, and every test overrides
  it since a throwaway repo has no sibling `plans/` worktree.
- **Isolation's "not the same commit as ordinary work" check requires a `commit <sha>` ledger line for
  the same step to exist at all** — no such line means isolation is refused (class 41), not silently
  passed, per S1's own "unknown means refuse" bias applied consistently to S3.
- None of the above needed Addendum 1's proceed-and-mark mechanism (no `judgment/*` tag, no
  `spec__*.md` handoff): each is an ordinary tool-interface design decision inside a deliberately
  underspecified spec surface, the same kind of decision `### convention: <name>`'s marker syntax or
  conv-rename's citation-matching rule already made without invoking that mechanism. Nothing here was a
  *reversible ambiguity about required behavior* — the six-per-step test matrices the spec names are all
  satisfied exactly as written.

## Gates (per spec Prerequisites) — step-gates-spec.md, through S3
- `bash -n` on every new/changed file: OK
- `shellcheck` 0.9.0: clean on every new/changed file
- `./tests/run.sh`: 53/53; every prior golden re-verified after each `--update`, with `git diff`
  inspected before committing to confirm only the predicted files moved
- No DCO sign-off; nothing pushed

## Step log — conventions-authoring-spec.md (earlier session, unchanged)
- S1 · 65553806 · landed by prior session · conv-new.sh
- S2 · 57f4874a · landed by prior session · conv-edit.sh
- S3 · afd17a4a · landed by prior session · conv-rename.sh
  - Plan: `plans/session/handoffs/plan__s3-conv-rename-plan.md`. Approval:
    `plans/session/handoffs/coder-plans-tooling__s3-plan-approved.md` — read, marked `.WIP` on read,
    `.DONE` once incorporated. Everything the plan flagged was approved as proposed: repeatable
    `--cite-dirs`, recursive cite-dir scan, both documented scope gaps, the exit-code table, the
    `scratch-run.sh` generalization, seven test cases instead of the spec's literal six.
  - Completion handoff to the planner: `plans/session/handoffs/plan__s3-conv-rename-done.md`.
  - Two additions that were NOT in the approved plan, both additive and both named in the commit
    message: a fourth fixture file at `citations/planning/archive/old-doc.md` (nothing else exercised
    the recursive scan or the archive-rewriting decision), and `--force-approved` on the still-cited
    deletion case (strictly stronger — proves the citation refusal is unconditional).
  - Gates at that point: `bash -n` OK; shellcheck 0.9.0 clean except a pre-existing SC2148 on
    `tests/cases.sh` (sourced file, no shebang, left for whoever owns that file); `./tests/run.sh` 37/37,
    no pre-existing golden changed; every documented error path exercised by hand; no DCO; nothing pushed.
- S4 (pre-commit hook) and S5 (documentation) of that spec: not started, still open.

## Not done / known limitations
- `plan-lint` (S4-S7 of step-gates-spec.md) not started as of this checkpoint.
- Two S3 isolation sub-checks are implemented but not exercised by any registered test case (out of the
  spec's own six): an out-of-scope path inside the tagged commit, and a judgment step with no recorded
  ordinary-work commit at all. Both follow directly from the "unknown means refuse" bias already
  established in S1; flagged here per the same discipline that caught conv-rename's own unlisted-fixture
  additions, not because either is in doubt.
- `conventions-authoring-spec.md` S4 (pre-commit hook) and S5 (documentation) remain open from the earlier
  session; out of scope for this session's assignment.

## Open questions for Dean
- None yet for step-gates-spec.md. Will surface here (and via a `plan__` handoff if it needs a decision)
  if S4-S7 turn up a genuine spec gap rather than an ordinary interface decision.
