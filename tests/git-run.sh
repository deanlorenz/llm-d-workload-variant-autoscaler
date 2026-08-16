#!/usr/bin/env bash
# git-run.sh — build a throwaway git repo via a builder script, then run a
# command inside it. Generic harness shared by every git-based test suite
# (step-check's scope/sign-off/judgment cases, plan-lint's judgment cases):
# each suite supplies its own builder, this script only owns the
# wipe/build/cd/exec sequence so that mechanic is written once rather than
# once per suite.
#
#   git-run.sh <scratch-dir> <builder> <case-name> -- <command>...
#
# <builder> is invoked as `<builder> <scratch-dir> <case-name>` and must
# leave <scratch-dir> as a git repository in the state <case-name> describes.
# Its own stdout/stderr is swallowed on success (setup chatter is not the
# thing under test) and dumped on failure so a broken builder is debuggable.
#
# <scratch-dir> is wiped and recreated first, so a case is unaffected by
# whatever a previous run left behind — this never touches a real worktree.
#
# Exit code is the wrapped command's, via exec; this script produces no
# stdout of its own on the success path, so a golden shows only the wrapped
# command's transcript.
set -uo pipefail

die() {
    printf 'git-run: %s\n' "$*" >&2
    exit 2
}

usage='usage: git-run.sh <scratch-dir> <builder> <case-name> -- <command>...'

[ "$#" -ge 4 ] || die "$usage"

scratch=$1
builder=$2
case_name=$3
shift 3

[ "$1" = -- ] || die "expected -- before the command, got: $1 ($usage)"
shift
[ "$#" -ge 1 ] || die 'no command given after --'
[ -x "$builder" ] || die "builder not found or not executable: $builder"

rm -rf -- "$scratch" || die "cannot clear scratch dir: $scratch"
mkdir -p -- "$scratch" || die "cannot create scratch dir: $scratch"

builder_log=$(mktemp) || die 'mktemp failed'
if ! "$builder" "$scratch" "$case_name" >"$builder_log" 2>&1; then
    cat -- "$builder_log" >&2
    rm -f -- "$builder_log"
    die "builder failed for case $case_name: $builder"
fi
rm -f -- "$builder_log"

cd -- "$scratch" || die "cannot enter scratch dir: $scratch"
exec "$@"
