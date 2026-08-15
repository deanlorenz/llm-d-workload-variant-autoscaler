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
