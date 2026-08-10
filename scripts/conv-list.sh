#!/usr/bin/env bash
# conv-list.sh — the computed convention index.
#
#   conv-list.sh [--dir <dir>]
#
# Scans <dir>/*.md (default conventions/) for every '### convention: <name>'
# marker, reads the field lines that follow it, and prints one line per
# convention. Computing this is the reason no index file exists: a scan cannot
# disagree with the conventions, and a stored index can.
#
# Output is one record per line, three fields separated by ' | ':
#
#   <name> | <status> | <description>
#
# sorted by name in the C locale so the output diffs cleanly and is identical
# across runs. Downstream readers should split on ' | ' and expect exactly three
# fields.
#
# The status field is rendered, not copied verbatim:
#   active            status: active
#   PROBATION         status: probation — uppercased to draw the eye. A
#                     convention on probation is still binding; the mark means
#                     "not yet ratified", never "not in force".
#   <other>           any other status value, verbatim
#   NO-STATUS         no status field at all
#
# A convention with no description line is listed with a (NO DESCRIPTION)
# placeholder rather than skipped — silence would hide precisely what conv-lint
# exists to catch.
#
# Exit codes are the contract:
#   0  index printed
#   2  usage error
#   3  directory missing, or it holds no .md files
#   4  the directory holds .md files but declares no conventions
set -uo pipefail

MARKER_PREFIX='### convention: '

die() {
    local code=$1
    shift
    printf 'conv-list: %s\n' "$*" >&2
    exit "$code"
}

dir=conventions

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
            printf 'usage: conv-list.sh [--dir <dir>]\n'
            exit 0
            ;;
        *)
            die 2 "unexpected argument: $1"
            ;;
    esac
done

[ -d "$dir" ] || die 3 "no such conventions directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in conventions directory: $dir"

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
    printf("%s | %s | %s\n", name, shown_status, shown_desc)
    name = ""
    status = ""
    description = ""
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
}

END { emit() }
' "${files[@]}" | LC_ALL=C sort)

[ -n "$listing" ] || die 4 "no conventions declared in $dir (found ${#files[@]} .md file(s) but no '${MARKER_PREFIX}' marker)"

printf '%s\n' "$listing"
