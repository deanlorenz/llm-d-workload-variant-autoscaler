#!/usr/bin/env bash
# step-check-signoff-repo.sh — build the throwaway repo for one step-check
# sign-off-policy case (S2). Invoked by tests/git-run.sh.
#
#   step-check-signoff-repo.sh <dir> <case>
#
# One baseline commit, working tree clean afterward, so scope containment
# passes trivially regardless of what --scope names in the case's own
# invocation — only the sign-off check has anything to say.
set -uo pipefail

die() {
    printf 'step-check-signoff-repo: %s\n' "$*" >&2
    exit 1
}

[ "$#" -eq 2 ] || die 'usage: step-check-signoff-repo.sh <dir> <case>'
dir=$1
case_name=$2

git -C "$dir" init -q -b main || die 'git init failed'
git -C "$dir" config user.name 'Test User' || die 'git config (user.name) failed'
git -C "$dir" config user.email 'test@example.invalid' || die 'git config (user.email) failed'
git -C "$dir" config commit.gpgsign false || die 'git config (commit.gpgsign) failed'

printf 'readme\n' >"$dir/README.md"
git -C "$dir" add -A || die 'git add failed'

case $case_name in
    code-with-signoff|plans-with-signoff)
        git -C "$dir" commit -q -s -m 'baseline' || die 'signed-off commit failed'
        ;;
    code-without-signoff|plans-without-signoff|missing-lineage)
        git -C "$dir" commit -q -m 'baseline' || die 'plain commit failed'
        ;;
    *)
        die "unknown case: $case_name"
        ;;
esac
