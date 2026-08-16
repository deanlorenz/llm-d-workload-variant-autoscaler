#!/usr/bin/env bash
# scratch-run.sh — run a command against deterministic scratch copies of one or
# more fixture dirs, then dump the resulting trees so a golden can prove what a
# mutating tool actually wrote, not just what it printed.
#
#   scratch-run.sh <fixture-dir-or--> <scratch-dir> [<fixture-dir-or--> <scratch-dir>]... -- <command>...
#
# Each <fixture-dir-or-> is a directory whose *.md files are copied into the
# <scratch-dir> that follows it, or the literal - for an empty scratch dir.
# Every <scratch-dir> is wiped and recreated on every invocation, so a case is
# unaffected by whatever a previous run left behind — callers pass the same
# fixed path every time rather than a fresh mktemp one, because a mutating
# tool's own stdout (e.g. conv-new printing the path it wrote to) has to stay
# identical across runs to diff against a golden.
#
# Several pairs are accepted because a tool can mutate more than one kind of
# directory in one run: conv-rename touches both the conventions dir holding
# the marker and the cite-dirs holding the citations, and a case has to prove
# what happened in all of them — including that a refusal happened in none.
# Seeding is per pair and flat, one directory's *.md files at a time, so a
# fixture tree that is nested on disk is passed as one pair per level. Order
# matters in exactly one way: list a parent scratch dir before any scratch dir
# nested inside it, or the parent's wipe removes the child.
#
# All pairs are seeded, then the command runs once, then all pairs are dumped,
# in the order given.
#
# Exit code is the wrapped command's, not this script's own setup/dump
# bookkeeping around it.
set -uo pipefail

die() {
    printf 'scratch-run: %s\n' "$*" >&2
    exit 2
}

usage='usage: scratch-run.sh <fixture-dir-or--> <scratch-dir> [<fixture> <scratch>]... -- <command>...'

pairs=()
while [ "$#" -gt 0 ] && [ "$1" != -- ]; do
    if [ "$#" -lt 2 ] || [ "$2" = -- ]; then
        die "fixture $1 has no scratch dir after it"
    fi
    pairs+=("$1" "$2")
    shift 2
done

[ "${#pairs[@]}" -gt 0 ] || die "$usage"
[ "${1-}" = -- ] || die "expected -- before the command, got: ${1-<end of arguments>}"
shift
[ "$#" -ge 1 ] || die 'no command given after --'

for ((i = 0; i < ${#pairs[@]}; i += 2)); do
    fixture=${pairs[i]}
    scratch=${pairs[i + 1]}

    rm -rf -- "$scratch" || die "cannot clear scratch dir: $scratch"
    mkdir -p -- "$scratch" || die "cannot create scratch dir: $scratch"

    if [ "$fixture" != - ]; then
        [ -d "$fixture" ] || die "no such fixture directory: $fixture"
        shopt -s nullglob
        seed_files=("$fixture"/*.md)
        shopt -u nullglob
        if [ "${#seed_files[@]}" -gt 0 ]; then
            cp -- "${seed_files[@]}" "$scratch/" || die "cannot seed scratch dir from: $fixture"
        fi
    fi
done

"$@"
rc=$?

for ((i = 0; i < ${#pairs[@]}; i += 2)); do
    scratch=${pairs[i + 1]}
    printf -- '--- %s ---\n' "$scratch"
    while IFS= read -r f; do
        printf -- '-- %s --\n' "$f"
        cat -- "$f"
    done < <(find "$scratch" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)
done

exit "$rc"
