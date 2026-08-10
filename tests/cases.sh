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
