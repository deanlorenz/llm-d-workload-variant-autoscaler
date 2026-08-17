#!/usr/bin/env bash
# coll-lint.sh — structural proof that the collections are fetchable.
#
#   coll-lint.sh [--dir <dir>] [--conv-dir <dir>]
#
# Mirrors conv-lint.sh's checks for the '### collection: <name>' marker, plus
# one collection-specific check: every name listed in a members: field must
# resolve to something — either another declared collection, or a convention
# declared in --conv-dir. A dangling member reference is exactly as bad as
# conv-lint.sh's own PATHREF violation: it makes the collection unfetchable at
# the point a caller actually expands it, and fails silently until then.
#
# Checks, and the exit code each carries:
#
#   10  marker format      a '### collection: <name>' heading whose name is not
#                          [a-z0-9-]+, or which sits at a level other than 3
#   11  name uniqueness    the same name declared more than once, in any file
#   12  required fields    description, members, trigger, status, origin must
#                          all be present in the field block after the marker
#   13  status value       status must be exactly active or probation
#   14  heading level      no heading of level 2 or shallower may appear after
#                          the file's first collection marker
#   15  referenced path    same PATHREF rule as conv-lint.sh, applied to this
#                          file's own body prose (backtick-quoted path tokens)
#   16  dangling member    a name in some members: field resolves to neither a
#                          declared collection nor a declared convention
#   17  member cycle       a collection's members chain reaches itself
#
#   2   usage error
#   3   directory missing, or it holds no .md files
#
# All violations are always reported; the exit code is the lowest-numbered
# class present.
set -uo pipefail

MARKER_PREFIX='### collection: '
CONV_MARKER_PREFIX='### convention: '
REQUIRED_FIELDS='description members trigger status origin'

die() {
    local code=$1
    shift
    printf 'coll-lint: %s\n' "$*" >&2
    exit "$code"
}

dir=collections
conv_dir=conventions

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
        --conv-dir)
            [ "$#" -ge 2 ] || die 2 '--conv-dir needs a directory argument'
            conv_dir=$2
            shift 2
            ;;
        --conv-dir=*)
            conv_dir=${1#--conv-dir=}
            shift
            ;;
        -h|--help)
            printf 'usage: coll-lint.sh [--dir <dir>] [--conv-dir <dir>]\n'
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

conv_names_set=""
if [ -d "$conv_dir" ]; then
    conv_files=()
    while IFS= read -r f; do
        conv_files+=("$f")
    done < <(find "$conv_dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)
    if [ "${#conv_files[@]}" -gt 0 ]; then
        conv_names_set=$(awk -v prefix="$CONV_MARKER_PREFIX" '
            index($0, prefix) == 1 { print substr($0, length(prefix) + 1) }
        ' "${conv_files[@]}" | LC_ALL=C sort -u)
    fi
fi

# Parse pass — same shape as conv-lint.sh's, plus a MEMBERS record.
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

    if (rest ~ /^collection:/) {
        candidate = substr($0, length(prefix) + 1)
        if (level == 3 && substr($0, 1, length(prefix)) == prefix && candidate ~ /^[a-z0-9-]+$/) {
            name = candidate
            printf("COLL\t%s\t%d\t%s\n", FILENAME, FNR, name)
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
        if (key == "members")
            printf("MEMBERS\t%s\t%s\t%s\n", FILENAME, name, value)
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
declare -a coll_records=()
declare -a report_marker=()
declare -a report_level=()
declare -a report_path=()
declare -A members_of=()

while IFS=$'\t' read -r kind f1 f2 f3 f4; do
    [ -n "$kind" ] || continue
    case $kind in
        COLL)
            coll_records+=("$f1"$'\t'"$f2"$'\t'"$f3")
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
        MEMBERS)
            members_of["$f2"]=$f3
            ;;
        LEVEL)
            report_level+=("$f1:$f2: heading at level 2 or shallower after the first collection marker truncates the collection above it: $f4")
            ;;
        PATHREF)
            [ -e "$f4" ] || report_path+=("$f1:$f2: collection $f3 references a path that does not resolve: $f4")
            ;;
        *)
            die 2 "internal: unrecognized parse record: $kind"
            ;;
    esac
done <<<"$records"

report_duplicate=()
report_fields=()
report_status=()
report_dangling=()
report_cycle=()

for name in ${name_order+"${name_order[@]}"}; do
    if [ "${name_count[$name]}" -gt 1 ]; then
        report_duplicate+=("collection $name is declared ${name_count[$name]} times: ${name_places[$name]% }")
    fi
done

for record in ${coll_records+"${coll_records[@]}"}; do
    IFS=$'\t' read -r file lineno name <<<"$record"
    missing=''
    for key in $REQUIRED_FIELDS; do
        [ -n "${field_value["$file|$name|$key"]+set}" ] || missing="$missing $key"
    done
    [ -z "$missing" ] || report_fields+=("$file:$lineno: collection $name is missing required field(s):${missing}")

    status=${field_value["$file|$name|status"]-}
    if [ -n "$status" ] && [ "$status" != active ] && [ "$status" != probation ]; then
        report_status+=("$file:$lineno: collection $name has status '$status'; allowed values are active and probation")
    fi
done

# Dangling-member + cycle checks: every member must resolve to a declared
# collection name or a declared convention name.
is_declared_collection() {
    local n=$1
    for k in "${!name_count[@]}"; do
        [ "$k" = "$n" ] && return 0
    done
    return 1
}

is_declared_convention() {
    local n=$1
    [ -n "$conv_names_set" ] || return 1
    grep -qxF "$n" <<<"$conv_names_set"
}

# A '<prefix>*' member is dangling if no declared convention name starts with
# <prefix> — same semantics as coll.sh's own prefix_matches, checked
# structurally here rather than by fetching.
prefix_has_match() {
    local prefix=$1
    [ -n "$conv_names_set" ] || return 1
    grep -q "^$prefix" <<<"$conv_names_set"
}

for name in ${name_order+"${name_order[@]}"}; do
    raw=${members_of[$name]-}
    [ -n "$raw" ] || continue
    IFS=',' read -ra parts <<<"$raw"
    for member in "${parts[@]}"; do
        member=$(printf '%s' "$member" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        [ -n "$member" ] || continue
        case $member in
            *'*')
                prefix_has_match "${member%'*'}" || report_dangling+=("collection $name references member '$member', which matches no convention name in --conv-dir $conv_dir")
                continue
                ;;
        esac
        if ! is_declared_collection "$member" && ! is_declared_convention "$member"; then
            report_dangling+=("collection $name references member '$member', which is neither a declared collection nor a declared convention (--conv-dir $conv_dir)")
        fi
    done
done

# Cycle check: DFS from each collection through its own members-that-are-collections.
find_cycle() {
    local start=$1 current=$2 path=$3
    case " $path " in
        *" $current "*)
            report_cycle+=("collection $start has a cycle: $path -> $current")
            return
            ;;
    esac
    local raw=${members_of[$current]-}
    [ -n "$raw" ] || return
    IFS=',' read -ra parts <<<"$raw"
    local member
    for member in "${parts[@]}"; do
        member=$(printf '%s' "$member" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        [ -n "$member" ] || continue
        is_declared_collection "$member" || continue
        find_cycle "$start" "$member" "$path $current"
    done
}
for name in ${name_order+"${name_order[@]}"}; do
    find_cycle "$name" "$name" ""
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
        printf 'coll-lint: [%d] %s\n' "$code" "$line" >&2
    done
    note_class "$code"
}

emit 10 ${report_marker+"${report_marker[@]}"}
emit 11 ${report_duplicate+"${report_duplicate[@]}"}
emit 12 ${report_fields+"${report_fields[@]}"}
emit 13 ${report_status+"${report_status[@]}"}
emit 14 ${report_level+"${report_level[@]}"}
emit 15 ${report_path+"${report_path[@]}"}
emit 16 ${report_dangling+"${report_dangling[@]}"}
emit 17 ${report_cycle+"${report_cycle[@]}"}

exit "$exit_code"
