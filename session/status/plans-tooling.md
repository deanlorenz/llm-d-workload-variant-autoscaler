last_update: 2026-08-17T00:00:00Z
state: in-progress
current_step: step-gates-spec.md S1-S7 all landed (commits a04ca96e..b320df1a). Both scripts/step-check and scripts/plan-lint complete, tested, documented. Awaiting review — not marked done by my own hand.

## Role and scope
Coder session. Branch/worktree: `plans-tooling` only (this worktree is my full scope — I never write
outside it except this status file and handoffs under `plans/session/handoffs/`, both reached by absolute
path on the shared plans worktree filesystem). Not a planner: I execute the steps I'm assigned, I don't
redesign the spec.

Assignment (this session, 2026-08-17): all of `plans/planning/step-gates-spec.md`, S1 through S7, handed
to a coder by Dean despite its own `Status: DRAFT` line — Dean confirmed the DRAFT tag means "not yet
reviewed", not "incomplete", and said to proceed regardless. **Complete as of this checkpoint.**

Prior assignment (earlier session, landed and unrelated to this one): S3 of
`plans/planning/conventions-authoring-spec.md` (`scripts/conv-rename`). Kept verbatim below rather than
overwritten — this status file is one file per branch, not per spec, and the earlier work is still the
most recent state of that spec.

Note: `conventions/` in this worktree is an untracked leftover from an earlier planner trial, not part of
either spec this worktree has executed — left untouched throughout, both sessions.

## Step log — step-gates-spec.md (this session, complete)
- S1 · a04ca96e · landed · `scripts/step-check` scope containment (git status vs declared --scope;
  untracked counts; empty scope refused; rename entries count both sides)
- S2 · 3cbaa408 · landed · `scripts/step-check` sign-off policy per lineage (--lineage code|plans
  mandatory, no default; checks HEAD's own commit message for `Signed-off-by:`)
- S3 · 028b402f · landed · `scripts/step-check` judgment mark (proceed-and-mark's isolate/tag/surface,
  mechanically; plus the reverse unlogged-tag check)
- S4 · 3b473787 · landed · `scripts/plan-lint` step schema (eight step fields, five Intent fields,
  Step-index briefs; one awk parse pass, tab-separated records, same shape conv-lint.sh uses)
- S5 · f67350dc · landed · `scripts/plan-lint` convention resolution and addressing (cites resolved via
  `conv-list.sh`; none-vs-absent asymmetry; line-number-reference scan)
- S6 · 07f9502e · landed · `scripts/plan-lint` unresolved judgments (`--judgments <repo-dir>`; reverted
  via real `This reverts commit <sha>.` text; `decided: <slug>` lines; foreign-step tags ignored)
- S7 · b320df1a · landed · README sections for both tools, every worked example (old and new) re-run and
  diffed byte-for-byte before committing

### Design decisions recorded (none required a judgment-mark — see below)
- **Tool names have no `.sh` suffix**: `scripts/step-check` / `scripts/plan-lint`, exactly as the spec's
  own scope/Intent fields write them throughout — a deliberate departure from every prior tool in this
  worktree (`sec.sh`, `conv.sh`, …), taken literally rather than corrected. Caught the flip side of this
  during S5: the sibling `conv-list.sh` *does* keep its `.sh` suffix, and an early draft called it bare
  `conv-list` — fixed once conv-list wasn't found on PATH.
- **Ledger format** (`--ledger <file>`, read by S3): reuses the step-log line shape
  `S<n> · commit <sha> · verify pass · <one line>` that `atomic-step-protocol-design.md` § Coder state
  already specifies for ordinary step work (this file's own step-log lines above use the same shape), and
  adds a parallel `S<n> · judgment <slug> · <ambiguous/assumed/why/revert/decision prose>` line for the
  proceed-and-mark obligations — that second shape was not specified anywhere and had to be invented.
- **`--step <id>` flag added** (not in the Intent block's abbreviated call-stack diagram) — required
  together with `--ledger`, since "at this step" (S3's own brief) needs something to scope the forward
  judgment checks against; the ledger accumulates across a whole run. Added the same way `--ledger` itself
  was added beyond that diagram.
- **`--handoffs-dir` default is lineage-conditional** (`session/handoffs` for `plans`,
  `../plans/session/handoffs` for `code`) — derived from CODER-CONVENTIONS.md § 5.2's own description of
  where a coder's handoffs actually live relative to its worktree; overridable, and every test overrides
  it since a throwaway repo has no sibling `plans/` worktree.
- **Isolation's "not the same commit as ordinary work" check requires a `commit <sha>` ledger line for
  the same step to exist at all** — no such line means isolation is refused (class 41), not silently
  passed, per S1's own "unknown means refuse" bias applied consistently to S3.
- **plan-lint's `**conventions**` citation syntax**: comma-separated names after the field's em-dash, up
  to the first period, each truncated at the first character outside `[a-z0-9-]+` — matches the shape
  `scripts/conv-rename.sh`'s own S3 commit message documents ("a step's `**conventions** — name, other`
  manifest line"). Caught a real bug against the actual `conventions-tooling-spec.md` fixture: "none (see
  § Intent)" was initially treated as an unresolved citation reading that whole parenthetical, not as
  `none` with a trailing aside — fixed by checking the manifest's *first token* against `none`, not the
  whole remainder, and truncating every individual cited name the same way.
- **plan-lint's `--judgments` "reverted" check** is a fact about git, not a text search either: does any
  commit reachable from any ref carry `This reverts commit <full sha>.` — the exact line `git revert`
  itself writes. Test fixtures use a real `git revert --no-edit`, never a hand-written commit message, so
  the exact trailer text is never guessed at.
- None of the above needed the proceed-and-mark mechanism itself (no `judgment/*` tag, no `spec__*.md`
  handoff): each is an ordinary tool-interface design decision inside a deliberately underspecified spec
  surface, the same kind of decision `### convention: <name>`'s marker syntax or conv-rename's
  citation-matching rule already made without invoking that mechanism. Nothing here was a *reversible
  ambiguity about required behavior* — every case matrix the spec names is satisfied exactly as written.

## Gates (per spec Prerequisites) — step-gates-spec.md, all seven steps
- `bash -n` on every new/changed file: OK, every step
- `shellcheck` 0.9.0: clean on every new/changed file, every step (confirmed installed and used
  throughout, consistent with the earlier session's own correction of a stale "not installed" note)
- `./tests/run.sh`: 67/67 at final checkpoint; every prior golden re-verified after each `--update`,
  with `git diff` inspected before every commit to confirm only the predicted files moved (documented
  per-commit: 5 new S1 cases; 2 golden ripples + 5 new S2 cases; 9 golden ripples + 6 new S3 cases; 4
  new S4 cases; 4 new S5 cases; 8 golden ripples + 6 new S6 cases; 0 golden changes for S7 since README
  isn't part of the golden suite)
- Every documented error path exercised, non-zero with a message on stderr — both scripts' full exit-code
  tables (step-check: 2, 20, 21, 30, 40-43; plan-lint: 2, 3, 20-22, 30-32, 40) hit by at least one
  registered golden case
- No DCO sign-off anywhere (plans lineage); nothing pushed

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
- S4 (pre-commit hook) and S5 (documentation) of that spec: not started, still open — out of scope for
  this session.

## Not done / known limitations
- Two S3 (`step-check`) isolation sub-checks are implemented but not exercised by any registered test
  case (out of the spec's own six): an out-of-scope path inside the tagged commit, and a judgment step
  with no recorded ordinary-work commit at all. Both follow directly from the "unknown means refuse" bias
  already established in S1; flagged here per the same discipline that caught conv-rename's own
  unlisted-fixture additions, not because either is in doubt.
- The pre-existing SC2148 shellcheck finding on `tests/cases.sh` (sourced file, no shebang) remains
  unfixed — noted by the prior session as "left for whoever owns that file"; still true, still untouched
  by this session either.
- `conventions-authoring-spec.md` S4 (pre-commit hook) and S5 (documentation) remain open from the earlier
  session; out of scope for this session's assignment.
- README.md's tool table now names `conv-new.sh`/`conv-edit.sh`/`conv-rename.sh` as existing-but-
  undocumented-here in one sentence, rather than writing their sections — that gap is
  `conventions-authoring-spec.md` S5's own responsibility, not this spec's.

## Open questions for Dean
- None for step-gates-spec.md. Every genuine interface gap in the spec's own text (citation syntax, the
  --step flag, --handoffs-dir's default, the ledger's judgment-line shape) was resolved as an ordinary
  tool-authoring decision and recorded above, not escalated — consistent with how the read-side tools'
  own marker syntax was decided without a judgment-mark. Happy to walk through any of them if Dean wants
  a different shape before this lands in `plans/scripts/`.
