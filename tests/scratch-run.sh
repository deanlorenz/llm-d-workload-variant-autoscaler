#!/usr/bin/env bash
# scratch-run.sh — run a command against a deterministic scratch copy of a
# fixture dir, then dump the resulting tree so a golden can prove what a
# mutating tool actually wrote, not just what it printed.
#
#   scratch-run.sh <fixture-dir-or--> <scratch-dir> -- <command>...
#
# <fixture-dir-or-> is a directory whose *.md files are copied into
# <scratch-dir> before the command runs, or the literal - for an empty
# scratch dir. <scratch-dir> is wiped and recreated on every invocation, so
# a case is unaffected by whatever a previous run left behind — callers pass
# the same fixed path every time rather than a fresh mktemp one, because a
# mutating tool's own stdout (e.g. conv-new printing the path it wrote to)
# has to stay identical across runs to diff against a golden.
#
# Exit code is the wrapped command's, not this script's own setup/dump
# bookkeeping around it.
set -uo pipefail

die() {
    printf 'scratch-run: %s\n' "$*" >&2
    exit 2
}

[ "$#" -ge 4 ] || die 'usage: scratch-run.sh <fixture-dir-or--> <scratch-dir> -- <command>...'

fixture=$1
scratch=$2
shift 2
[ "$1" = -- ] || die "expected -- before the command, got: $1"
shift
[ "$#" -ge 1 ] || die 'no command given after --'

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

"$@"
rc=$?

printf -- '--- %s ---\n' "$scratch"
while IFS= read -r f; do
    printf -- '-- %s --\n' "$f"
    cat -- "$f"
done < <(find "$scratch" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)

exit "$rc"
