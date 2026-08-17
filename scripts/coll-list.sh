#!/usr/bin/env bash
# coll-list.sh — the computed collection index.
#
#   coll-list.sh [--dir <dir>]
#
# Scans <dir>/*.md (default collections/) for every '### collection: <name>'
# marker, reads the field lines that follow it, and prints one line per
# collection. Computing this is the reason no index file exists, same
# rationale as conv-list.sh.
#
# Output is one record per line, four fields separated by ' | ':
#
#   <name> | <status> | <description> | <members>
#
# sorted by name in the C locale. Downstream readers should split on ' | ' and
# expect exactly four fields.
#
# status rendering is identical to conv-list.sh's own scheme (PROBATION
# uppercased, NO-STATUS if absent). A collection with no description or no
# members line is listed with the matching placeholder rather than skipped.
#
# Exit codes:
#   0  index printed
#   2  usage error
#   3  directory missing, or it holds no .md files
#   4  the directory holds .md files but declares no collections
set -uo pipefail

MARKER_PREFIX='### collection: '

die() {
    local code=$1
    shift
    printf 'coll-list: %s\n' "$*" >&2
    exit "$code"
}

dir=collections

while [ "$#" -gt 0 ]; do
    case $1 in
        --dir)
            [ "$#" -ge 2 ] || die 2 '--dir needs a directory argument'
            dir=$2
            shift 2
            ;;
        --dir=*)
            dir=${1#--dir=}
            shift
            ;;
        -h|--help)
            printf 'usage: coll-list.sh [--dir <dir>]\n'
            exit 0
            ;;
        *)
            die 2 "unexpected argument: $1"
            ;;
    esac
done

[ -d "$dir" ] || die 3 "no such collections directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in collections directory: $dir"

listing=$(awk -v prefix="$MARKER_PREFIX" '
function emit() {
    if (name == "")
        return
    shown_status = status
    if (shown_status == "")
        shown_status = "NO-STATUS"
    else if (shown_status == "probation")
        shown_status = "PROBATION"
    shown_desc = (description == "" ? "(NO DESCRIPTION)" : description)
    shown_members = (members == "" ? "(NO MEMBERS)" : members)
    printf("%s | %s | %s | %s\n", name, shown_status, shown_desc, shown_members)
    name = ""
    status = ""
    description = ""
    members = ""
}

index($0, prefix) == 1 {
    emit()
    name = substr($0, length(prefix) + 1)
    in_fields = 1
    next
}

/^#/ {
    emit()
    in_fields = 0
    next
}

name != "" && in_fields == 1 {
    if ($0 ~ /^[[:space:]]*$/) {
        in_fields = 0
        next
    }
    if (index($0, "description: ") == 1)
        description = substr($0, 14)
    else if (index($0, "status: ") == 1)
        status = substr($0, 9)
    else if (index($0, "members: ") == 1)
        members = substr($0, 10)
}

END { emit() }
' "${files[@]}" | LC_ALL=C sort)

[ -n "$listing" ] || die 4 "no collections declared in $dir (found ${#files[@]} .md file(s) but no '${MARKER_PREFIX}' marker)"

printf '%s\n' "$listing"
