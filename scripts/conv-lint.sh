#!/usr/bin/env bash
# conv-lint.sh — structural proof that the conventions are fetchable.
#
#   conv-lint.sh [--dir <dir>]
#
# Every check here exists because its absence fails silently: a malformed marker
# makes a convention unfetchable, and a caller then halts as though it had never
# existed. Clean input produces no output and exit 0. Bad input reports every
# violation, with file and name, and exits non-zero.
#
# Checks, and the exit code each carries:
#
#   10  marker format      a '### convention: <name>' heading whose name is not
#                          [a-z0-9-]+, or which sits at a level other than 3
#   11  name uniqueness    the same name declared more than once, in any file
#   12  required fields    description, scope, trigger, status, origin must all
#                          be present in the field block after the marker
#   13  status value       status must be exactly active or probation
#   14  heading level      no heading of level 2 or shallower may appear after
#                          the file's first convention marker: it would truncate
#                          the convention it falls inside at extraction time
#   15  referenced path    a backtick-quoted token in a convention that looks
#                          like a path (contains / or ends in .md or .sh) must
#                          resolve on disk, relative to the current directory
#
#   2   usage error
#   3   directory missing, or it holds no .md files
#
# All violations are always reported; the exit code is the lowest-numbered class
# present, so a caller can branch on the most structural failure while still
# seeing the rest. A linter that reported one problem of six would cost six runs.
set -uo pipefail

MARKER_PREFIX='### convention: '
REQUIRED_FIELDS='description scope trigger status origin'

die() {
    local code=$1
    shift
    printf 'conv-lint: %s\n' "$*" >&2
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
            printf 'usage: conv-lint.sh [--dir <dir>]\n'
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

# Parse pass. Emits one tab-separated record per finding, in file then line
# order, so every report below is deterministic without needing a sort.
#
#   CONV       file  line  name
#   MARKERBAD  file  line  raw-heading
#   FIELD      file  name  key   value
#   LEVEL      file  line  name  raw-heading
#   PATHREF    file  line  name  token
records=$(awk -v prefix="$MARKER_PREFIX" '
FNR == 1 {
    seen_marker = 0
    in_fields = 0
    name = ""
}

/^#+[[:space:]]/ {
    rest = $0
    sub(/^#+/, "", rest)
    level = length($0) - length(rest)
    gsub(/^[[:space:]]+/, "", rest)
    gsub(/[[:space:]]+$/, "", rest)

    if (rest ~ /^convention:/) {
        candidate = substr($0, length(prefix) + 1)
        if (level == 3 && substr($0, 1, length(prefix)) == prefix && candidate ~ /^[a-z0-9-]+$/) {
            name = candidate
            printf("CONV\t%s\t%d\t%s\n", FILENAME, FNR, name)
            in_fields = 1
        } else {
            printf("MARKERBAD\t%s\t%d\t%s\n", FILENAME, FNR, $0)
            name = ""
            in_fields = 0
        }
        seen_marker = 1
        next
    }

    if (seen_marker == 1 && level <= 2)
        printf("LEVEL\t%s\t%d\t%s\t%s\n", FILENAME, FNR, (name == "" ? "-" : name), $0)

    # A heading at level 3 or shallower closes the current convention; a deeper
    # one stays inside it, exactly as the extractor sees it.
    if (level <= 3) {
        name = ""
        in_fields = 0
    }
    next
}

in_fields == 1 {
    if ($0 ~ /^[[:space:]]*$/) {
        in_fields = 0
    } else if ($0 ~ /^[a-z][a-z-]*:[[:space:]]/) {
        key = $0
        sub(/:.*$/, "", key)
        value = substr($0, length(key) + 2)
        gsub(/^[[:space:]]+/, "", value)
        gsub(/[[:space:]]+$/, "", value)
        printf("FIELD\t%s\t%s\t%s\t%s\n", FILENAME, name, key, value)
    }
}

name != "" {
    tail = $0
    while (match(tail, /`[^`]+`/)) {
        token = substr(tail, RSTART + 1, RLENGTH - 2)
        tail = substr(tail, RSTART + RLENGTH)
        if (token ~ /^[^[:space:]*?]+$/ && (token ~ /\// || token ~ /\.(md|sh)$/))
            printf("PATHREF\t%s\t%d\t%s\t%s\n", FILENAME, FNR, name, token)
    }
}
' "${files[@]}")

declare -A field_value=()
declare -A name_count=()
declare -A name_places=()
declare -a name_order=()
declare -a conv_records=()
declare -a report_marker=()
declare -a report_level=()
declare -a report_path=()

while IFS=$'\t' read -r kind f1 f2 f3 f4; do
    [ -n "$kind" ] || continue
    case $kind in
        CONV)
            conv_records+=("$f1"$'\t'"$f2"$'\t'"$f3")
            if [ -z "${name_count[$f3]+set}" ]; then
                name_count[$f3]=0
                name_places[$f3]=''
                name_order+=("$f3")
            fi
            name_count[$f3]=$((name_count[$f3] + 1))
            name_places[$f3]="${name_places[$f3]}$f1:$f2 "
            ;;
        MARKERBAD)
            report_marker+=("$f1:$f2: marker is not '${MARKER_PREFIX}<name>' with name matching [a-z0-9-]+: $f3")
            ;;
        FIELD)
            field_value["$f1|$f2|$f3"]=$f4
            ;;
        LEVEL)
            report_level+=("$f1:$f2: heading at level 2 or shallower after the first convention marker truncates the convention above it: $f4")
            ;;
        PATHREF)
            [ -e "$f4" ] || report_path+=("$f1:$f2: convention $f3 references a path that does not resolve: $f4")
            ;;
        *)
            die 2 "internal: unrecognized parse record: $kind"
            ;;
    esac
done <<<"$records"

report_duplicate=()
report_fields=()
report_status=()

for name in ${name_order+"${name_order[@]}"}; do
    if [ "${name_count[$name]}" -gt 1 ]; then
        report_duplicate+=("convention $name is declared ${name_count[$name]} times: ${name_places[$name]% }")
    fi
done

for record in ${conv_records+"${conv_records[@]}"}; do
    IFS=$'\t' read -r file lineno name <<<"$record"
    missing=''
    for key in $REQUIRED_FIELDS; do
        [ -n "${field_value["$file|$name|$key"]+set}" ] || missing="$missing $key"
    done
    [ -z "$missing" ] || report_fields+=("$file:$lineno: convention $name is missing required field(s):${missing}")

    status=${field_value["$file|$name|status"]-}
    if [ -n "$status" ] && [ "$status" != active ] && [ "$status" != probation ]; then
        report_status+=("$file:$lineno: convention $name has status '$status'; allowed values are active and probation")
    fi
done

exit_code=0
note_class() {
    local code=$1
    if [ "$exit_code" -eq 0 ] || [ "$code" -lt "$exit_code" ]; then
        exit_code=$code
    fi
}

emit() {
    local code=$1
    shift
    [ "$#" -gt 0 ] || return 0
    local line
    for line in "$@"; do
        printf 'conv-lint: [%d] %s\n' "$code" "$line" >&2
    done
    note_class "$code"
}

emit 10 ${report_marker+"${report_marker[@]}"}
emit 11 ${report_duplicate+"${report_duplicate[@]}"}
emit 12 ${report_fields+"${report_fields[@]}"}
emit 13 ${report_status+"${report_status[@]}"}
emit 14 ${report_level+"${report_level[@]}"}
emit 15 ${report_path+"${report_path[@]}"}

exit "$exit_code"
