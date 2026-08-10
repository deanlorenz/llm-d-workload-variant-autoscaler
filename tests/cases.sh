# Case registry for tests/run.sh. Sourced, never executed.
#
#   case_register <name> <command> [arg...]
#
#     name     the golden lives at tests/expected/<name>.out; use
#              <tool>-<case>, e.g. sec-single-id
#     command  run with the worktree root as CWD and bin/ first on PATH
#
# Each case's transcript — exit code, stdout, stderr — is diffed against its
# golden, so error paths are registered exactly like success paths.
#
# No cases yet: the tools land in later steps.
