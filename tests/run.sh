#!/usr/bin/env bash
# Golden-file test harness for the section and convention tools.
#
# Cases are registered in tests/cases.sh. Each case runs a command and its
# transcript is compared with the committed golden at tests/expected/<name>.out.
# The transcript records the exit code, stdout, and stderr separately, so a case
# cannot pass by producing the right text with the wrong exit status, and an
# empty result never looks like a failure.
#
#   ./tests/run.sh            compare against the goldens; non-zero if any differ
#   ./tests/run.sh --update   regenerate the goldens deliberately
set -uo pipefail

die() {
    printf 'run.sh: %s\n' "$*" >&2
    exit 2
}

TESTS_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || die 'cannot resolve tests directory'
ROOT=$(dirname -- "$TESTS_DIR")
EXPECTED_DIR="$TESTS_DIR/expected"
CASES_FILE="$TESTS_DIR/cases.sh"

UPDATE=0
case "${1-}" in
    '')        ;;
    --update)  UPDATE=1 ;;
    -h|--help) printf 'usage: run.sh [--update]\n'; exit 0 ;;
    *)         die "unknown argument: $1" ;;
esac
[ "$#" -le 1 ] || die "too many arguments: expected at most 1, got $#"

# Tools are found on PATH so a case can name one without knowing where it lives.
PATH="$ROOT/scripts:$PATH"
export PATH

[ -f "$CASES_FILE" ] || die "missing case registry: $CASES_FILE"
[ -d "$EXPECTED_DIR" ] || die "missing golden directory: $EXPECTED_DIR"

CASE_NAMES=()
CASE_CMDS=()

case_register() {
    [ "$#" -ge 2 ] || die 'case_register needs a case name and a command'
    local name=$1
    shift
    local known
    for known in ${CASE_NAMES+"${CASE_NAMES[@]}"}; do
        [ "$known" = "$name" ] && die "duplicate case name: $name"
    done
    CASE_NAMES+=("$name")
    CASE_CMDS+=("$(printf '%q ' "$@")")
}

# Run one case and print its transcript. Stdout and stderr are captured apart
# so their interleaving cannot make a golden order-dependent.
transcript() {
    local cmd=$1
    local out err rc
    out=$(mktemp) || die 'mktemp failed'
    err=$(mktemp) || die 'mktemp failed'
    (cd -- "$ROOT" && eval "$cmd") >"$out" 2>"$err"
    rc=$?
    printf 'exit: %d\n' "$rc"
    printf -- '--- stdout ---\n'
    cat -- "$out"
    printf -- '--- stderr ---\n'
    cat -- "$err"
    rm -f -- "$out" "$err"
}

# shellcheck source=tests/cases.sh
source "$CASES_FILE" || die "failed to load case registry: $CASES_FILE"

total=${#CASE_NAMES[@]}
failed=0

for ((i = 0; i < total; i++)); do
    name=${CASE_NAMES[i]}
    golden="$EXPECTED_DIR/$name.out"
    actual=$(transcript "${CASE_CMDS[i]}")

    if [ "$UPDATE" -eq 1 ]; then
        printf '%s\n' "$actual" >"$golden" || die "cannot write golden: $golden"
        printf 'UPDATE  %s\n' "$name"
        continue
    fi

    if [ ! -f "$golden" ]; then
        printf 'MISSING %s\n' "$name"
        printf 'run.sh: no golden for case %s at %s\n' "$name" "$golden" >&2
        failed=$((failed + 1))
        continue
    fi

    if diff -u -- "$golden" <(printf '%s\n' "$actual"); then
        printf 'PASS    %s\n' "$name"
    else
        printf 'FAIL    %s\n' "$name"
        failed=$((failed + 1))
    fi
done

if [ "$UPDATE" -eq 1 ]; then
    printf '%d case(s) updated\n' "$total"
    exit 0
fi

printf '%d case(s), %d failed\n' "$total" "$failed"
[ "$failed" -eq 0 ] || exit 1
exit 0
