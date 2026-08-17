# Case registry for tests/run.sh. Sourced, never executed.
#
#   case_register <name> <command> [arg...]
#
#     name     the golden lives at tests/expected/<name>.out; use
#              <tool>-<case>, e.g. sec-single-id
#     command  run with the worktree root as CWD and scripts/ first on PATH
#
# Each case's transcript — exit code, stdout, stderr — is diffed against its
# golden, so error paths are registered exactly like success paths.
#
# sec — single id. The four shapes that exercise the level arithmetic.
case_register sec-level2            ./scripts/sec.sh tests/fixtures/doc-a.md alpha
case_register sec-level3            ./scripts/sec.sh tests/fixtures/doc-a.md alpha-child
case_register sec-deeper-subsection ./scripts/sec.sh tests/fixtures/doc-a.md beta
case_register sec-end-of-file       ./scripts/sec.sh tests/fixtures/doc-a.md omega

# sec — multiple ids and error paths.
case_register sec-two-ids           ./scripts/sec.sh tests/fixtures/doc-a.md alpha omega
case_register sec-three-ids         ./scripts/sec.sh tests/fixtures/doc-a.md beta alpha-child omega
case_register sec-bad-among-good    ./scripts/sec.sh tests/fixtures/doc-a.md alpha no-such-id
case_register sec-ambiguous         ./scripts/sec.sh tests/fixtures/doc-a.md set-up

# conv — name-to-file discovery, then delegation to sec.
case_register conv-one-name       ./scripts/conv.sh --dir tests/fixtures/conventions commit-message-shape
case_register conv-three-names    ./scripts/conv.sh --dir tests/fixtures/conventions no-dco-on-plans archive-never-delete one-commit-per-step
case_register conv-unknown-name   ./scripts/conv.sh --dir tests/fixtures/conventions commit-message
case_register conv-duplicate-name ./scripts/conv.sh --dir tests/fixtures/conventions-dup doubly-defined

# conv-list — the computed index.
case_register conv-list-topic-files ./scripts/conv-list.sh --dir tests/fixtures/conventions
case_register conv-list-no-description ./scripts/conv-list.sh --dir tests/fixtures/conventions-nodesc

# conv-lint — one clean run, then one fixture directory per violation class.
case_register conv-lint-clean          ./scripts/conv-lint.sh --dir tests/fixtures/conventions
case_register conv-lint-marker-format  ./scripts/conv-lint.sh --dir tests/fixtures/bad/marker
case_register conv-lint-name-uniqueness ./scripts/conv-lint.sh --dir tests/fixtures/bad/duplicate
case_register conv-lint-required-fields ./scripts/conv-lint.sh --dir tests/fixtures/bad/fields
case_register conv-lint-status-value   ./scripts/conv-lint.sh --dir tests/fixtures/bad/status
case_register conv-lint-heading-level  ./scripts/conv-lint.sh --dir tests/fixtures/bad/levels
case_register conv-lint-referenced-path ./scripts/conv-lint.sh --dir tests/fixtures/bad/paths

# coll — collection expansion, against the same fixtures/conventions dir conv
# uses, so a collection member resolves against real fixture convention names.
case_register coll-flat-members   ./scripts/coll.sh --dir tests/fixtures/collections --conv-dir tests/fixtures/conventions coder-fixture
case_register coll-nested         ./scripts/coll.sh --dir tests/fixtures/collections --conv-dir tests/fixtures/conventions nested-fixture
case_register coll-prefix-member  ./scripts/coll.sh --dir tests/fixtures/collections --conv-dir tests/fixtures/conventions git-prefix-fixture
case_register coll-unknown-name   ./scripts/coll.sh --dir tests/fixtures/collections --conv-dir tests/fixtures/conventions no-such-collection
case_register coll-dangling-member ./scripts/coll.sh --dir tests/fixtures/bad-collections/dangling --conv-dir tests/fixtures/conventions dangling-fixture
case_register coll-cycle          ./scripts/coll.sh --dir tests/fixtures/bad-collections/cycle --conv-dir tests/fixtures/conventions cycle-a

# coll-list — the computed collection index.
case_register coll-list-fixture ./scripts/coll-list.sh --dir tests/fixtures/collections

# coll-lint — one clean run, then one fixture directory per violation class.
case_register coll-lint-clean          ./scripts/coll-lint.sh --dir tests/fixtures/collections --conv-dir tests/fixtures/conventions
case_register coll-lint-dangling       ./scripts/coll-lint.sh --dir tests/fixtures/bad-collections/dangling --conv-dir tests/fixtures/conventions
case_register coll-lint-cycle          ./scripts/coll-lint.sh --dir tests/fixtures/bad-collections/cycle --conv-dir tests/fixtures/conventions

# conv-new — mutates a topic file, so each case runs against a deterministic
# scratch copy (see tests/scratch-run.sh) rather than the committed fixtures.
# The golden captures both the tool's own stdout and the resulting file
# tree, so a wrong write is caught even if the tool's own message looks right.
case_register conv-new-existing-topic \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-new-existing-topic -- \
    ./scripts/conv-new.sh --dir tests/tmp/conv-new-existing-topic fresh-one \
    --topic tests/tmp/conv-new-existing-topic/commits.md \
    --description "A fresh convention added by a test." \
    --scope "test fixtures only" \
    --trigger "running the conv-new golden suite" \
    --origin "conv-new S1 test case"

# --origin is deliberately omitted here: the field prints as a bare 'origin:'
# with no value, which conv-lint's field-line pattern does not match, so the
# field reads as absent rather than empty. That is the mechanic behind "leave
# unsupplied fields empty rather than inventing content."
case_register conv-new-new-topic \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-new-new-topic -- \
    ./scripts/conv-new.sh --dir tests/tmp/conv-new-new-topic fresh-two \
    --topic tests/tmp/conv-new-new-topic/new-topic.md \
    --description "A convention in a topic file that did not exist yet." \
    --scope "test fixtures only" \
    --trigger "running the conv-new golden suite"

case_register conv-new-duplicate-refused \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-new-duplicate-refused -- \
    ./scripts/conv-new.sh --dir tests/tmp/conv-new-duplicate-refused commit-message-shape \
    --topic tests/tmp/conv-new-duplicate-refused/commits.md

case_register conv-new-invalid-name-refused \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-new-invalid-name-refused -- \
    ./scripts/conv-new.sh --dir tests/tmp/conv-new-invalid-name-refused "Not_Valid" \
    --topic tests/tmp/conv-new-invalid-name-refused/commits.md

# conv-edit — replace one section in place; --from fixtures are checked-in
# and read-only, so only the target conventions dir needs a scratch copy.
case_register conv-edit-first \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-edit-first -- \
    ./scripts/conv-edit.sh --dir tests/tmp/conv-edit-first commit-message-shape \
    --from tests/fixtures/conv-edit/replace-first.md

case_register conv-edit-middle \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-edit-middle -- \
    ./scripts/conv-edit.sh --dir tests/tmp/conv-edit-middle one-commit-per-step \
    --from tests/fixtures/conv-edit/replace-middle.md

# no-dco-on-plans runs to end-of-file in the fixture, so this also exercises
# the no-following-heading boundary.
case_register conv-edit-last \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-edit-last -- \
    ./scripts/conv-edit.sh --dir tests/tmp/conv-edit-last no-dco-on-plans \
    --from tests/fixtures/conv-edit/replace-last.md

case_register conv-edit-missing-marker-refused \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-edit-missing-marker-refused -- \
    ./scripts/conv-edit.sh --dir tests/tmp/conv-edit-missing-marker-refused commit-message-shape \
    --from tests/fixtures/conv-edit/missing-marker.md

# Round trip: conv | conv-edit --from <that output> | conv again must be
# byte-exact, and the containing file must show no other change.
case_register conv-edit-roundtrip \
    ./tests/scratch-run.sh tests/fixtures/conventions tests/tmp/conv-edit-roundtrip -- \
    ./tests/conv-edit-roundtrip.sh tests/tmp/conv-edit-roundtrip archive-never-delete

# conv-rename — mutates the conventions dir and the cite-dirs at once, so every
# case passes four fixture/scratch pairs to scratch-run.sh: the conventions dir
# holding the marker, and the three directories the citations live in. All four
# are dumped, which is what makes a refusal provable: a case that must change
# nothing shows every file exactly as the fixture has it.
#
# The pairs are flat, one per directory level, and a parent scratch dir is
# always listed before a scratch dir nested inside it (scratch-run wipes each
# one it is given). tests/fixtures/conv-rename/citations/planning/archive is
# therefore its own pair even though conv-rename finds it by scanning
# .../planning recursively — which is the point of having it: it proves both the
# recursive cite-dir scan and the deliberate decision not to exempt archived
# documents from a rename.
#
# So the "two files" of conv-rename-two-files is the spec's own phrasing for
# two cite-dirs; the fixture has three citing files across them (a manifest
# line in planning/, the same shape in planning/archive/, and two prose
# mentions in roles/), and the golden shows the count per file.

case_register conv-rename-two-files \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-two-files/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-two-files/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-two-files/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-two-files/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-two-files/conventions \
    --cite-dirs tests/tmp/conv-rename-two-files/planning \
    --cite-dirs tests/tmp/conv-rename-two-files/roles \
    old-name new-name

# lonely-name is cited nowhere, so this exercises the marker-only rewrite path:
# the topic file changes, no cite-dir file does.
case_register conv-rename-none \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-none/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-none/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-none/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-none/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-none/conventions \
    --cite-dirs tests/tmp/conv-rename-none/planning \
    --cite-dirs tests/tmp/conv-rename-none/roles \
    lonely-name lonely-renamed

case_register conv-rename-target-exists-refused \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-target-exists-refused/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-target-exists-refused/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-target-exists-refused/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-target-exists-refused/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-target-exists-refused/conventions \
    --cite-dirs tests/tmp/conv-rename-target-exists-refused/planning \
    --cite-dirs tests/tmp/conv-rename-target-exists-refused/roles \
    old-name other-name

# Registered for parity with conv-new's own invalid-name case: the rename half
# of this tool's surface runs the same [a-z0-9-]+ check on <new>.
case_register conv-rename-invalid-name-refused \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-invalid-name-refused/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-invalid-name-refused/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-invalid-name-refused/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-invalid-name-refused/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-invalid-name-refused/conventions \
    --cite-dirs tests/tmp/conv-rename-invalid-name-refused/planning \
    --cite-dirs tests/tmp/conv-rename-invalid-name-refused/roles \
    old-name "Not_Valid"

case_register conv-rename-delete-refused-cited \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-delete-refused-cited/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-delete-refused-cited/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-delete-refused-cited/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-delete-refused-cited/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-delete-refused-cited/conventions \
    --cite-dirs tests/tmp/conv-rename-delete-refused-cited/planning \
    --cite-dirs tests/tmp/conv-rename-delete-refused-cited/roles \
    --delete old-name --force-approved

case_register conv-rename-delete-refused-uncited-no-approval \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-delete-refused-uncited-no-approval/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-delete-refused-uncited-no-approval/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-delete-refused-uncited-no-approval/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-delete-refused-uncited-no-approval/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-delete-refused-uncited-no-approval/conventions \
    --cite-dirs tests/tmp/conv-rename-delete-refused-uncited-no-approval/planning \
    --cite-dirs tests/tmp/conv-rename-delete-refused-uncited-no-approval/roles \
    --delete lonely-name

# The one case where --delete actually deletes. Without it every registered
# deletion case is a refusal, and nothing would prove the section removal works
# at all — the spec's own five cases leave that hole.
case_register conv-rename-delete-succeeds \
    ./tests/scratch-run.sh \
    tests/fixtures/conv-rename/conventions tests/tmp/conv-rename-delete-succeeds/conventions \
    tests/fixtures/conv-rename/citations/planning tests/tmp/conv-rename-delete-succeeds/planning \
    tests/fixtures/conv-rename/citations/planning/archive tests/tmp/conv-rename-delete-succeeds/planning/archive \
    tests/fixtures/conv-rename/citations/roles tests/tmp/conv-rename-delete-succeeds/roles -- \
    ./scripts/conv-rename.sh --dir tests/tmp/conv-rename-delete-succeeds/conventions \
    --cite-dirs tests/tmp/conv-rename-delete-succeeds/planning \
    --cite-dirs tests/tmp/conv-rename-delete-succeeds/roles \
    --delete lonely-name --force-approved

# step-check — scope containment (S1). Each case builds its own throwaway git
# repo via tests/git-run.sh + tests/step-check-scope-repo.sh rather than
# touching a real worktree; step-check is found on PATH (see run.sh).
#
# --lineage plans on every case below (added in S2, when the flag became
# mandatory): the builder's baseline commit is never signed off, so plans —
# which forbids Signed-off-by — is the lineage that keeps these S1 cases
# passing on the sign-off check without changing anything the scope check
# itself proves.
case_register step-check-scope-clean \
    ./tests/git-run.sh tests/tmp/step-check-scope-clean \
    ./tests/step-check-scope-repo.sh clean -- \
    step-check --scope src/a.md --lineage plans

case_register step-check-scope-out-of-scope-modified \
    ./tests/git-run.sh tests/tmp/step-check-scope-out-of-scope-modified \
    ./tests/step-check-scope-repo.sh out-of-scope-modified -- \
    step-check --scope src/a.md --lineage plans

case_register step-check-scope-out-of-scope-untracked \
    ./tests/git-run.sh tests/tmp/step-check-scope-out-of-scope-untracked \
    ./tests/step-check-scope-repo.sh out-of-scope-untracked -- \
    step-check --scope src/a.md --lineage plans

# The scope path is a directory, and the mutation is two levels under it —
# proves the beneath-a-declared-directory rule, not just exact-path matches.
case_register step-check-scope-nested-in-scope \
    ./tests/git-run.sh tests/tmp/step-check-scope-nested-in-scope \
    ./tests/step-check-scope-repo.sh nested-in-scope -- \
    step-check --scope src --lineage plans

case_register step-check-scope-empty-scope-refused \
    ./tests/git-run.sh tests/tmp/step-check-scope-empty-scope-refused \
    ./tests/step-check-scope-repo.sh empty-scope -- \
    step-check --lineage plans

# step-check — sign-off policy per lineage (S2). Each case commits a clean
# baseline (signed off, or not) and leaves the working tree clean, so scope
# containment passes trivially and only the sign-off check has anything to
# report. --scope README.md is a real, uninteresting path — present only so
# these cases don't also trip the empty-scope refusal.
case_register step-check-signoff-code-with-signoff \
    ./tests/git-run.sh tests/tmp/step-check-signoff-code-with-signoff \
    ./tests/step-check-signoff-repo.sh code-with-signoff -- \
    step-check --scope README.md --lineage code

case_register step-check-signoff-code-without-signoff \
    ./tests/git-run.sh tests/tmp/step-check-signoff-code-without-signoff \
    ./tests/step-check-signoff-repo.sh code-without-signoff -- \
    step-check --scope README.md --lineage code

case_register step-check-signoff-plans-without-signoff \
    ./tests/git-run.sh tests/tmp/step-check-signoff-plans-without-signoff \
    ./tests/step-check-signoff-repo.sh plans-without-signoff -- \
    step-check --scope README.md --lineage plans

case_register step-check-signoff-plans-with-signoff \
    ./tests/git-run.sh tests/tmp/step-check-signoff-plans-with-signoff \
    ./tests/step-check-signoff-repo.sh plans-with-signoff -- \
    step-check --scope README.md --lineage plans

case_register step-check-signoff-missing-lineage-refused \
    ./tests/git-run.sh tests/tmp/step-check-signoff-missing-lineage-refused \
    ./tests/step-check-signoff-repo.sh missing-lineage -- \
    step-check --scope README.md

# step-check — judgment mark (S3). Branch demo, step S03, slug
# fixture-count-ambiguous, scope src throughout; see
# tests/step-check-judgment-repo.sh for exactly what each case builds.
case_register step-check-judgment-clean \
    ./tests/git-run.sh tests/tmp/step-check-judgment-clean \
    ./tests/step-check-judgment-repo.sh clean -- \
    step-check --scope src --lineage plans --ledger ledger.md --step S03 --handoffs-dir handoffs

case_register step-check-judgment-no-tag \
    ./tests/git-run.sh tests/tmp/step-check-judgment-no-tag \
    ./tests/step-check-judgment-repo.sh no-tag -- \
    step-check --scope src --lineage plans --ledger ledger.md --step S03 --handoffs-dir handoffs

case_register step-check-judgment-shares-commit \
    ./tests/git-run.sh tests/tmp/step-check-judgment-shares-commit \
    ./tests/step-check-judgment-repo.sh shares-commit -- \
    step-check --scope src --lineage plans --ledger ledger.md --step S03 --handoffs-dir handoffs

case_register step-check-judgment-unlogged-tag \
    ./tests/git-run.sh tests/tmp/step-check-judgment-unlogged-tag \
    ./tests/step-check-judgment-repo.sh unlogged-tag -- \
    step-check --scope src --lineage plans --ledger ledger.md --step S03 --handoffs-dir handoffs

case_register step-check-judgment-no-handoff \
    ./tests/git-run.sh tests/tmp/step-check-judgment-no-handoff \
    ./tests/step-check-judgment-repo.sh no-handoff -- \
    step-check --scope src --lineage plans --ledger ledger.md --step S03 --handoffs-dir handoffs

# No --ledger at all: judgment checks are skipped and announced; the repo's
# only commit is unsigned, so lineage=plans still passes cleanly overall.
case_register step-check-judgment-ledger-omitted \
    ./tests/git-run.sh tests/tmp/step-check-judgment-ledger-omitted \
    ./tests/step-check-judgment-repo.sh ledger-omitted -- \
    step-check --scope src --lineage plans --handoffs-dir handoffs

# plan-lint — step schema (S4). clean-spec.md is a fixture copy of the real
# conventions-tooling-spec.md (the spec's own suggestion for a clean case);
# the other three are that same file with one defect each.
case_register plan-lint-clean-spec \
    ./scripts/plan-lint tests/fixtures/plan-lint/clean-spec.md

case_register plan-lint-missing-field \
    ./scripts/plan-lint tests/fixtures/plan-lint/missing-field.md

case_register plan-lint-no-brief \
    ./scripts/plan-lint tests/fixtures/plan-lint/no-brief.md

case_register plan-lint-missing-intent-field \
    ./scripts/plan-lint tests/fixtures/plan-lint/missing-intent-field.md

# plan-lint — convention resolution and addressing (S5). The spec's own
# "none passes" case is already fully proven by plan-lint-clean-spec above
# (every step in that fixture declares literal none), so it is not repeated
# here under a second name. minimal-spec.md is a small, self-built fixture
# (not derived from a real spec) so each remaining case can isolate exactly
# one S5 violation; --dir points at the read-side tools' own
# tests/fixtures/conventions, which already declares one-commit-per-step.
case_register plan-lint-unknown-convention \
    ./scripts/plan-lint --dir tests/fixtures/conventions tests/fixtures/plan-lint/minimal-spec.md

case_register plan-lint-absent-conventions \
    ./scripts/plan-lint --dir tests/fixtures/conventions tests/fixtures/plan-lint/absent-conventions.md

case_register plan-lint-line-ref \
    ./scripts/plan-lint --dir tests/fixtures/conventions tests/fixtures/plan-lint/line-ref.md

case_register plan-lint-no-conventions-warns \
    ./scripts/plan-lint --no-conventions tests/fixtures/plan-lint/minimal-spec.md

# plan-lint — unresolved judgments (S6). judgments-spec.md is a clean
# one-step spec (conventions: none, so nothing from S5 fires) built solely
# to be the step a judgment/demo/S1-* tag can name; judgments-decided-spec.md
# is the same file with a `decided: some-slug` line added to S1. Each
# git-based case builds its own throwaway repo via
# tests/plan-lint-judgments-run.sh, which — unlike tests/git-run.sh — never
# cd's into the repo it builds, since plan-lint takes the repo as --judgments
# rather than expecting to run from inside it.
case_register plan-lint-judgments-none \
    ./tests/plan-lint-judgments-run.sh tests/tmp/plan-lint-judgments-none none -- \
    ./scripts/plan-lint --judgments tests/tmp/plan-lint-judgments-none tests/fixtures/plan-lint/judgments-spec.md

case_register plan-lint-judgments-reverted \
    ./tests/plan-lint-judgments-run.sh tests/tmp/plan-lint-judgments-reverted reverted -- \
    ./scripts/plan-lint --judgments tests/tmp/plan-lint-judgments-reverted tests/fixtures/plan-lint/judgments-spec.md

case_register plan-lint-judgments-decided \
    ./tests/plan-lint-judgments-run.sh tests/tmp/plan-lint-judgments-decided decided -- \
    ./scripts/plan-lint --judgments tests/tmp/plan-lint-judgments-decided tests/fixtures/plan-lint/judgments-decided-spec.md

case_register plan-lint-judgments-unresolved \
    ./tests/plan-lint-judgments-run.sh tests/tmp/plan-lint-judgments-unresolved unresolved -- \
    ./scripts/plan-lint --judgments tests/tmp/plan-lint-judgments-unresolved tests/fixtures/plan-lint/judgments-spec.md

case_register plan-lint-judgments-foreign-step \
    ./tests/plan-lint-judgments-run.sh tests/tmp/plan-lint-judgments-foreign-step foreign-step -- \
    ./scripts/plan-lint --judgments tests/tmp/plan-lint-judgments-foreign-step tests/fixtures/plan-lint/judgments-spec.md

# --judgments omitted: skipped and announced, same fixture as the "no tags"
# case above so the only difference in output is the announcement itself.
case_register plan-lint-judgments-omitted \
    ./scripts/plan-lint tests/fixtures/plan-lint/judgments-spec.md
