#!/usr/bin/env bash
# conv-edit-roundtrip.sh — the round-trip proof conv-edit's spec calls for:
#
#   conv <name> > a; conv-edit <name> --from a; conv <name> > b; diff a b
#
#   conv-edit-roundtrip.sh <dir> <name>
#
# Temp files hold a and b; their paths never reach stdout, so this stays
# deterministic for golden comparison even though it uses mktemp.
set -uo pipefail

die() {
    printf 'conv-edit-roundtrip: %s\n' "$*" >&2
    exit 2
}

[ "$#" -eq 2 ] || die 'usage: conv-edit-roundtrip.sh <dir> <name>'
dir=$1
name=$2

a=$(mktemp) || die 'mktemp failed'
b=$(mktemp) || die 'mktemp failed'
trap 'rm -f -- "$a" "$b"' EXIT

./scripts/conv.sh --dir "$dir" "$name" >"$a" || exit $?
./scripts/conv-edit.sh --dir "$dir" "$name" --from "$a" || exit $?
./scripts/conv.sh --dir "$dir" "$name" >"$b" || exit $?

if diff -u -- "$a" "$b" >&2; then
    printf 'round-trip byte-exact\n'
else
    printf 'round-trip differs\n' >&2
    exit 1
fi
