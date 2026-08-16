#!/usr/bin/env bash
# step-check-scope-repo.sh — build the throwaway repo for one step-check
# scope-containment case (S1). Invoked by tests/git-run.sh; never touches a
# real worktree.
#
#   step-check-scope-repo.sh <dir> <case>
#
# Baseline (committed): src/a.md, src/nested/b.md, other/c.md, README.md.
# Each case then applies one uncommitted mutation to the working tree, since
# step-check reads git status, not history.
set -uo pipefail

die() {
    printf 'step-check-scope-repo: %s\n' "$*" >&2
    exit 1
}

[ "$#" -eq 2 ] || die 'usage: step-check-scope-repo.sh <dir> <case>'
dir=$1
case_name=$2

git -C "$dir" init -q -b main || die 'git init failed'
git -C "$dir" config user.name 'Test User' || die 'git config (user.name) failed'
git -C "$dir" config user.email 'test@example.invalid' || die 'git config (user.email) failed'
git -C "$dir" config commit.gpgsign false || die 'git config (commit.gpgsign) failed'

mkdir -p -- "$dir/src/nested" "$dir/other" || die 'mkdir failed'
printf 'a\n' >"$dir/src/a.md"
printf 'b\n' >"$dir/src/nested/b.md"
printf 'c\n' >"$dir/other/c.md"
printf 'readme\n' >"$dir/README.md"
git -C "$dir" add -A || die 'git add (baseline) failed'
git -C "$dir" commit -q -m 'baseline' || die 'baseline commit failed'

case $case_name in
    clean)
        # A tracked, in-scope edit: the case step-check must pass silently.
        printf 'a changed\n' >>"$dir/src/a.md"
        ;;
    out-of-scope-modified)
        # A tracked edit outside every declared scope path.
        printf 'c changed\n' >>"$dir/other/c.md"
        ;;
    out-of-scope-untracked)
        # A brand-new, never-added file outside every declared scope path —
        # the drift an untracked-file check exists to catch.
        printf 'stray\n' >"$dir/stray.md"
        ;;
    nested-in-scope)
        # A tracked edit two levels under a directory scope path.
        printf 'b changed\n' >>"$dir/src/nested/b.md"
        ;;
    empty-scope)
        # No mutation: this case is about the absent --scope flag, not the
        # tree, and step-check must refuse before even reading git status.
        ;;
    *)
        die "unknown case: $case_name"
        ;;
esac
