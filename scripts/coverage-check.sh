#!/usr/bin/env bash
# coverage-check.sh — every classified row has a home, and can be found.
#
#   coverage-check.sh --table <file> [--table <file>]... [--conv-dir <dir>] [--role-dir <dir>]
#
# Step 5 of the micro-rules migration (Dean: "make sure EVERY existing rule has
# a new home and is reachable from all relevant entry points"). This answers
# the first half — "has a new home" — mechanically: a classification table
# (harvest-classification.md, memory-harvest-classification.md, ...) declares
# one row per source rule with a `dest` column. A row destined `conv:<topic>`
# or `role:<role>` is COVERED if some entry's `origin:` field, anywhere under
# --conv-dir or --role-dir, cites that row's own ID. A row destined `model` or
# `SKIP (...)` needs no conv/role entry at all — it is out of scope for this
# check by design, not silently ignored (both are counted and reported).
#
# Table format expected: a markdown table row `| <ID> | ... | <dest> | ... |`
# where <ID> matches [A-Z]+[0-9]+ (C1, CC6, FM12, PM6, GF4, M1, ...) and <dest>
# is the second-to-last or a clearly-`conv:`/`role:`/`model`/`SKIP` cell — this
# script does not parse column position, it scans every cell of every row for
# a dest-shaped token, so table layout drift doesn't silently break coverage.
#
# origin: field matching: an ID is considered cited if it appears as a whole
# word (word-boundary on both sides) anywhere in any origin: line. This
# matches both `(C1, C2)` and `CC6/CC15/CC17/CC18/CC19` and `harvest-
# classification.md C26, C8/C13` shapes already in use — deliberately loose,
# because the origin: field's job is human citation, not a second machine
# format; a false negative here (a real citation missed) is far more likely
# than a false positive (an unrelated token matching a real ID by accident),
# so this script is written to bias toward the former only where doing
# otherwise would require every origin: line rewritten to a stricter grammar,
# which is not this check's job to impose.
#
# Exit codes:
#   0  every conv:/role: row is covered
#   2  usage error
#   3  a --table file does not exist, or no --table given
#   4  at least one row is uncovered (every such row is reported on stderr,
#      grouped by source table)
set -uo pipefail

die() {
    local code=$1
    shift
    printf 'coverage-check: %s\n' "$*" >&2
    exit "$code"
}

tables=()
conv_dir=conventions
role_dir=roles

while [ "$#" -gt 0 ]; do
    case $1 in
        --table)
            [ "$#" -ge 2 ] || die 2 '--table needs a file argument'
            tables+=("$2")
            shift 2
            ;;
        --table=*)
            tables+=("${1#--table=}")
            shift
            ;;
        --conv-dir)
            [ "$#" -ge 2 ] || die 2 '--conv-dir needs a directory argument'
            conv_dir=$2
            shift 2
            ;;
        --conv-dir=*)
            conv_dir=${1#--conv-dir=}
            shift
            ;;
        --role-dir)
            [ "$#" -ge 2 ] || die 2 '--role-dir needs a directory argument'
            role_dir=$2
            shift 2
            ;;
        --role-dir=*)
            role_dir=${1#--role-dir=}
            shift
            ;;
        -h|--help)
            printf 'usage: coverage-check.sh --table <file> [--table <file>]... [--conv-dir <dir>] [--role-dir <dir>]\n'
            exit 0
            ;;
        *)
            die 2 "unexpected argument: $1"
            ;;
    esac
done

[ "${#tables[@]}" -ge 1 ] || die 3 'no --table given (need at least one classification table)'
for t in "${tables[@]}"; do
    [ -f "$t" ] || die 3 "no such table file: $t"
done

# Collect every origin: line's raw text, from every .md file in both dirs, so
# ID-matching is one grep against one blob rather than per-row file scans.
origin_blob=""
for d in "$conv_dir" "$role_dir"; do
    if [ -d "$d" ]; then
        while IFS= read -r f; do
            origin_blob="$origin_blob
$(grep '^origin:' "$f" 2>/dev/null || true)"
        done < <(find "$d" -maxdepth 1 -type f -name '*.md' | LC_ALL=C sort)
    fi
done

id_is_cited() {
    local id=$1
    printf '%s\n' "$origin_blob" | grep -qE "(^|[^A-Za-z0-9-])${id}([^A-Za-z0-9-]|\$)"
}

total_rows=0
covered=0
out_of_scope=0
uncovered_report=()

for table in "${tables[@]}"; do
    # Each markdown table row: '| <ID> | ... |'. Extract the ID (first cell)
    # and scan the rest of the line for a dest-shaped token.
    while IFS= read -r line; do
        case $line in
            '|'*'|'*) : ;;
            *) continue ;;
        esac
        id=$(printf '%s' "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}')
        case $id in
            [A-Z]*[0-9]) : ;;
            *) continue ;;
        esac

        # A row's "Source" cell (third pipe-delimited field) may itself name a
        # source file (a memory's filename, e.g. feedback_foo.md) rather than
        # only a heading description — some harvest tables cite the memory
        # filename in origin: instead of the row ID, since it is a more
        # concrete, independently resolvable reference. Either counts as a
        # citation.
        source_cell=$(printf '%s' "$line" | awk -F'|' '{gsub(/^[ \t]+|[ \t]+$/, "", $3); print $3}')
        source_file=""
        if printf '%s' "$source_cell" | grep -qoE '[A-Za-z_][A-Za-z0-9_.-]*\.md'; then
            source_file=$(printf '%s' "$source_cell" | grep -oE '[A-Za-z_][A-Za-z0-9_.-]*\.md' | head -1)
        fi

        dest=""
        if printf '%s' "$line" | grep -qE '`conv:[a-z0-9-]+`'; then
            dest="conv"
        elif printf '%s' "$line" | grep -qE '`role:[a-zA-Z0-9_+-]+`'; then
            dest="role"
        elif printf '%s' "$line" | grep -qE '`model`'; then
            dest="model"
        elif printf '%s' "$line" | grep -qE 'SKIP'; then
            dest="skip"
        else
            continue
        fi

        total_rows=$((total_rows + 1))

        case $dest in
            model|skip)
                out_of_scope=$((out_of_scope + 1))
                continue
                ;;
        esac

        if id_is_cited "$id" || { [ -n "$source_file" ] && id_is_cited "$source_file"; }; then
            covered=$((covered + 1))
        else
            uncovered_report+=("$table: row $id (dest: $dest) has no citing origin: line under --conv-dir $conv_dir or --role-dir $role_dir")
        fi
    done < "$table"
done

[ "$total_rows" -gt 0 ] || die 3 "no classification rows found in: ${tables[*]} (expected markdown table rows with an [A-Z]+[0-9]+ id cell and a conv:/role:/model/SKIP dest token)"

printf 'coverage-check: %d row(s) scanned, %d out-of-scope (model/SKIP), %d conv:/role: rows, %d covered, %d uncovered\n' \
    "$total_rows" "$out_of_scope" "$((total_rows - out_of_scope))" "$covered" "${#uncovered_report[@]}"

if [ "${#uncovered_report[@]}" -gt 0 ]; then
    for line in "${uncovered_report[@]}"; do
        printf 'coverage-check: [4] %s\n' "$line" >&2
    done
    exit 4
fi

exit 0
