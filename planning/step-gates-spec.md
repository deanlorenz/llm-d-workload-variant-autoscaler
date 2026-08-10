# Code spec — step gates: the post-step check and plan-lint

**code spec** · **Status: DRAFT** — awaiting Dean's finalization.

Third migration spec. Depends on [`conventions-tooling-spec.md`](conventions-tooling-spec.md); pairs with
[`conventions-authoring-spec.md`](conventions-authoring-spec.md).

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then start at your assigned step and read only that
step's section. No line numbers; do not run `toc-refresh.sh` on it.

---

## Intent

**intent** — Build the two gates the atomic-step design depends on: the **post-step check** that replaces
the per-call permission prompt, and **`plan-lint`** that makes a code spec's shape machine-checked instead
of diligence-checked.

**current call stack** — Neither exists. A coder's scope discipline is prose it is trusted to follow, and a
spec's completeness is whatever the spec owner remembered. Auto mode currently rests on physical
confinement (an orphan worktree, a narrow tool allowlist) rather than on a check.

**Stated plainly because it is a real gap:** an auto-mode coder has already run without the portable check
existing. Its safety came from the worktree being an empty orphan and its tool list being narrow — not from
anything verifying where it wrote. That is acceptable once, for a spec whose scope was a fresh directory.
It is not acceptable for a coder working inside an existing tree, which is what makes this spec a
prerequisite for the harvest.

**planned call stack** —

```
coder finishes a step
  → step-check --scope <paths> --lineage plans|code
        git status vs declared scope        → refuse to proceed if anything outside it changed
        sign-off policy for the lineage     → plans forbids DCO, code requires it
  → commit

spec owner finishes authoring, coder starts a range, r-confirm runs
  → plan-lint <spec>
        every step has all eight fields
        conventions: present (possibly `none`) and every name resolves
        Intent block has all five fields
        no line-number addressing anywhere
```

**new components** — `scripts/step-check`, `scripts/plan-lint`, tests.

**new conventions** — none yet. The rules these gates enforce are the strongest harvest candidates in the
migration, because a gate is a convention that has been made mechanical.

**Reassessment:** `plan-lint` was earlier called not-ready because no document used the new shape. Two now
do — this spec and its siblings — so it has real input and its fixtures can be drawn from them.

---

## Prerequisites

Continue in worktree `plans-tooling`.

**Gates** — `bash -n`; `shellcheck` if installed (say so if not); `./tests/run.sh` green; every documented
error path exits non-zero on stderr. No Go gates. No DCO on this lineage. **Never push.**

---

## Step index

**S1 — `step-check`, scope containment.** Compare `git status` against the step's declared `scope` and
refuse when anything outside it changed. This is the mechanism that lets the permission prompt go away, so
it must be conservative: unknown means refuse.

**S2 — `step-check`, sign-off policy per lineage.** The two lineages have *opposite* rules — code branches
require `Signed-off-by`, the plans lineage forbids it. A single hard-coded rule would be wrong half the
time, which is why this is a flag rather than an assumption.

**S3 — `plan-lint`, step schema.** All eight fields on every step, plus the five Intent fields. Mechanical,
and it is what keeps a runtime halt rare enough to be meaningful.

**S4 — `plan-lint`, convention resolution and addressing.** Every cited convention name resolves via
`conv-list`; `conventions:` present everywhere (possibly `none`); no line-number addressing survives.

**S5 — Documentation.** README sections, every example executed.

---

<!-- ─────────────── execution detail below ─────────────── -->

## S1 — `step-check`, scope containment

**brief** — `step-check --scope <path>...` fails if the working tree changed anywhere outside the declared
paths. It is what replaces a human eyeballing each write, so its bias must be toward refusal.

**scope** — `scripts/step-check`, `tests/`

**do**
1. Read changed paths from `git status --porcelain` — modified, staged, **and untracked**. Untracked
   matters: a coder creating a stray file outside scope is exactly the drift being caught.
2. A path is in scope if it equals a declared path or sits beneath a declared directory. Compare
   normalised paths; do not glob-match loosely.
3. Anything out of scope → list the offenders and exit non-zero. Clean → silent, exit 0.
4. `--allow-untracked <glob>` for legitimately ignored artefacts, off by default.
5. Cases: clean in-scope change; an out-of-scope modification; an out-of-scope **untracked** file; a
   nested in-scope path; an empty scope list (refuse — an empty scope is a spec defect, not permission).

**conventions** — none. Inline: unknown means refuse. A check that passes when it cannot tell is worse than
no check, because it manufactures confidence.

**verify** — `./tests/run.sh` green; the tests build a throwaway git repo rather than touching a real
worktree.

**done_when** — all five cases pass, including untracked detection and the empty-scope refusal.

**on_fail** — halt.

**record** — the path-normalisation rule, since `plan-lint` reads the same `scope` field.

[↑ Step index](#step-index)

## S2 — `step-check`, sign-off policy per lineage

**brief** — Sign-off is **required** on code branches and **forbidden** on the plans lineage. Encoding
either as the default would silently do the wrong thing on the other, and both failures are invisible
until a push is rejected or history has to be rewritten.

**scope** — `scripts/step-check`, `tests/`

**do**
1. `--lineage code|plans`, required — no default. An unspecified lineage exits non-zero.
2. `code`: the tip commit must carry `Signed-off-by:`; missing → non-zero.
3. `plans`: the tip commit must **not** carry it; present → non-zero, since it would have to be rewritten
   later.
4. Report which lineage rule was applied, so a passing run says what it checked rather than only that it
   passed.
5. Cases: code with sign-off passes; code without fails; plans without passes; plans with fails; missing
   `--lineage` fails.

**conventions** — none. Inline: no default for a flag whose two values have opposite meanings.

**verify** — `./tests/run.sh` green, all five cases, in a throwaway repo.

**done_when** — both lineages pass their own case and fail the other's, and the flag is mandatory.

**on_fail** — halt.

**record** — how the lineage is meant to be determined by a caller, if not passed explicitly.

[↑ Step index](#step-index)

## S3 — `plan-lint`, step schema

**brief** — Turn a spec's completeness into a machine check. A missing `conventions:` line is how
"halt when you have no rule" quietly becomes "proceed with nothing".

**scope** — `scripts/plan-lint`, `tests/`

**do**
1. Find step sections — headings matching `^## S[0-9]+`.
2. Each must carry all eight fields: `brief`, `scope`, `do`, `conventions`, `verify`, `done_when`,
   `on_fail`, `record`. Report every missing field with its step id.
3. The `## Intent` block must carry `intent`, `current call stack`, `planned call stack`,
   `new components`, `new conventions`.
4. Require a `## Step index` section and a brief in it for every step section that exists — a step with
   detail but no brief is invisible to the narrative.
5. Report all violations, then exit non-zero. Clean → silent, exit 0.
6. Cases: a clean spec (use `conventions-tooling-spec.md` as a fixture copy); one missing field; a step
   with no brief; a missing Intent field.

**conventions** — none. Inline: report every violation in one run.

**verify** — `./tests/run.sh` green; run against the three real specs in `../plans/planning/` and record
the result — if a real spec fails, that is a finding about the spec, not a licence to weaken the linter.

**done_when** — every check has a passing and a failing fixture, and the real specs' results are recorded.

**on_fail** — halt.

**record** — the outcome of linting the real specs, verbatim.

[↑ Step index](#step-index)

## S4 — `plan-lint`, convention resolution and addressing

**brief** — A spec citing a convention that does not exist must fail at authoring time, not at 3am inside
a coder. And no document may reintroduce line-number addressing.

**scope** — `scripts/plan-lint`, `tests/`

**do**
1. For each step's `conventions:` manifest, extract cited names and resolve each via `conv-list`. Unknown
   name → violation naming step and name.
2. The literal `none` is valid and must pass. An **absent** `conventions:` line is a violation. That
   asymmetry is the point: omission halts, explicit none proceeds.
3. Flag any `L<n>:<m>` range or `offset:<n> limit:<m>` occurrence as a violation.
4. `--no-conventions` skips resolution for use before `conventions/` exists; it must **warn**, never pass
   silently, so the gap is visible.
5. Cases: `none` passes; unknown name fails; absent line fails; a line-range reference fails;
   `--no-conventions` warns and passes.

**conventions** — none. Inline: `none` and absent must never be treated alike.

**verify** — `./tests/run.sh` green; with an empty `conventions/`, a spec citing any name fails without
`--no-conventions` and warns with it.

**done_when** — all five cases pass and the none-versus-absent distinction is proven by two cases.

**on_fail** — halt.

**record** — the citation syntax accepted, matched to `conv-rename`'s definition from its own S3.

[↑ Step index](#step-index)

## S5 — Documentation

**brief** — README sections for both gates, written against finished behaviour.

**scope** — `README.md`

**do**
1. One section each: synopsis, arguments, exit codes, worked example.
2. State that `step-check --lineage` has no default and why.
3. State that `plan-lint --no-conventions` is a temporary migration flag that warns.

**conventions** — none. Inline: no plans-branch identifiers.

**verify** — every example executed, output matches.

**done_when** — both documented, all examples verified by running them.

**on_fail** — halt.

**record** — anything the docs pass revealed about the interfaces.

[↑ Step index](#step-index)
