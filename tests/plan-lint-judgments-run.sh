#!/usr/bin/env bash
# plan-lint-judgments-run.sh — build a throwaway git repo carrying judgment/*
# tags for one plan-lint S6 case, then run a command (plan-lint itself,
# pointed at the repo via --judgments). Never touches a real worktree, and
# — unlike tests/git-run.sh — never cd's into the repo it builds: plan-lint
# reads its spec file and its --judgments repo as two independent paths, so
# the wrapped command's own relative paths must keep resolving against this
# worktree's root.
#
#   plan-lint-judgments-run.sh <scratch-dir> <case-name> -- <command>...
set -uo pipefail

die() {
    printf 'plan-lint-judgments-run: %s\n' "$*" >&2
    exit 2
}

usage='usage: plan-lint-judgments-run.sh <scratch-dir> <case-name> -- <command>...'

[ "$#" -ge 4 ] || die "$usage"
scratch=$1
case_name=$2
shift 2

[ "$1" = -- ] || die "expected -- before the command, got: $1 ($usage)"
shift
[ "$#" -ge 1 ] || die 'no command given after --'

rm -rf -- "$scratch" || die "cannot clear scratch dir: $scratch"
mkdir -p -- "$scratch" || die "cannot create scratch dir: $scratch"

git -C "$scratch" init -q -b demo || die 'git init failed'
git -C "$scratch" config user.name 'Test User' || die 'git config (user.name) failed'
git -C "$scratch" config user.email 'test@example.invalid' || die 'git config (user.email) failed'
git -C "$scratch" config commit.gpgsign false || die 'git config (commit.gpgsign) failed'
git -C "$scratch" config tag.gpgsign false || die 'git config (tag.gpgsign) failed'

printf 'seed\n' >"$scratch/seed.md"
git -C "$scratch" add -A || die 'git add (seed) failed'
git -C "$scratch" commit -q -m seed || die 'seed commit failed'

tag_judgment() {
    # $1: tag name (branch/step/slug already assembled by the caller)
    printf 'work\n' >"$scratch/work.md"
    git -C "$scratch" add -A || die 'git add (work) failed'
    git -C "$scratch" commit -q -m 'judgment commit' || die 'judgment commit failed'
    sha=$(git -C "$scratch" rev-parse HEAD) || die 'rev-parse failed'
    git -C "$scratch" tag "$1" "$sha" || die 'git tag failed'
    printf '%s' "$sha"
}

case $case_name in
    none)
        # No mutation at all: the case is about the absence of any
        # judgment/* tag, not about anything else in the repo.
        ;;
    reverted)
        sha=$(tag_judgment judgment/demo/S1-some-slug)
        git -C "$scratch" revert --no-edit "$sha" >/dev/null \
            || die 'git revert failed'
        ;;
    unresolved)
        tag_judgment judgment/demo/S1-some-slug >/dev/null
        ;;
    foreign-step)
        tag_judgment judgment/demo/S99-other-slug >/dev/null
        ;;
    decided)
        tag_judgment judgment/demo/S1-some-slug >/dev/null
        ;;
    *)
        die "unknown case: $case_name"
        ;;
esac

exec "$@"
