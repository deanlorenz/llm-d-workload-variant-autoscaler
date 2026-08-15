#!/usr/bin/env bash
# conv-new.sh — create a new convention, refusing a name that already exists.
#
#   conv-new.sh [--dir <dir>] <name> --topic <file>
#               [--description <text>] [--scope <text>] [--trigger <text>]
#               [--status <text>] [--origin <text>]
#
# Appends a '### convention: <name>' marker and its five field lines to
# <file>, creating <file> with a title heading if it does not exist yet.
# <dir> (default conventions/) is only the scope of the duplicate-name check;
# <file> is written to wherever it is given, whether or not that is inside
# <dir>.
#
# A field flag left unsupplied is written as a bare 'key:' with no trailing
# value or space. That line then fails to match the field-line pattern every
# reader of this format uses (conv-lint's key: <space>value shape), so it is
# invisible rather than present-with-empty-content — conv-lint reports it as
# a missing required field. This is deliberate: an empty field a linter can
# flag is honest, and inventing plausible content is not. --status is the one
# exception and defaults to 'active' when not given.
#
# Duplicate detection scans <dir>/*.md for the marker directly, the same way
# conv.sh finds holders, rather than shelling out to conv-list.sh — conv-list
# refuses outright when a directory holds no .md files yet, which is exactly
# the shape of the "brand new topic file" case this tool must allow.
#
# Exit codes are the contract:
#   0  created
#   2  usage error
#   3  invalid name (does not match [a-z0-9-]+)
#   4  name already exists (every file holding it is named on stderr)
set -uo pipefail

MARKER_PREFIX='### convention: '
FIELD_ORDER='description scope trigger status origin'

die() {
    local code=$1
    shift
    printf 'conv-new: %s\n' "$*" >&2
    exit "$code"
}

dir=conventions
topic=
name=
declare -A field_val=()
declare -A field_set=()

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
        --topic)
            [ "$#" -ge 2 ] || die 2 '--topic needs a file argument'
            topic=$2
            shift 2
            ;;
        --topic=*)
            topic=${1#--topic=}
            shift
            ;;
        --description|--scope|--trigger|--status|--origin)
            key=${1#--}
            [ "$#" -ge 2 ] || die 2 "--$key needs a text argument"
            field_val[$key]=$2
            field_set[$key]=1
            shift 2
            ;;
        --description=*|--scope=*|--trigger=*|--status=*|--origin=*)
            key=${1#--}
            key=${key%%=*}
            field_val[$key]=${1#*=}
            field_set[$key]=1
            shift
            ;;
        -h|--help)
            printf 'usage: conv-new.sh [--dir <dir>] <name> --topic <file> [--description T] [--scope T] [--trigger T] [--status T] [--origin T]\n'
            exit 0
            ;;
        --*)
            die 2 "unknown option: $1"
            ;;
        *)
            if [ -n "$name" ]; then
                die 2 "unexpected argument: $1"
            fi
            name=$1
            shift
            ;;
    esac
done

[ -n "$name" ] || die 2 'usage: conv-new.sh [--dir <dir>] <name> --topic <file> ... (no name given)'
[ -n "$topic" ] || die 2 '--topic <file> is required'

[[ $name =~ ^[a-z0-9-]+$ ]] || die 3 "invalid name '$name': must match [a-z0-9-]+"

if [ -z "${field_set[status]+set}" ]; then
    field_val[status]=active
    field_set[status]=1
fi

if [ -d "$dir" ]; then
    files=()
    while IFS= read -r f; do
        files+=("$f")
    done < <(find "$dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)

    if [ "${#files[@]}" -gt 0 ]; then
        holders=()
        want="$MARKER_PREFIX$name"
        for f in "${files[@]}"; do
            hits=$(awk -v want="$want" '$0 == want { c++ } END { print c + 0 }' "$f")
            [ "$hits" -gt 0 ] && holders+=("$f")
        done
        if [ "${#holders[@]}" -gt 0 ]; then
            printf 'conv-new: convention %s already exists\n' "$name" >&2
            for f in "${holders[@]}"; do
                printf 'conv-new:   %s\n' "$f" >&2
            done
            exit 4
        fi
    fi
fi

if [ ! -e "$topic" ]; then
    base=$(basename -- "$topic")
    base=${base%.md}
    title=$(printf '%s' "$base" | tr '-' ' ')
    title="$(printf '%s' "${title:0:1}" | tr '[:lower:]' '[:upper:]')${title:1}"
    printf '# %s\n' "$title" >"$topic" || die 2 "cannot create topic file: $topic"
fi

{
    printf '\n'
    printf '%s%s\n' "$MARKER_PREFIX" "$name"
    for key in $FIELD_ORDER; do
        if [ -n "${field_set[$key]+set}" ]; then
            printf '%s: %s\n' "$key" "${field_val[$key]}"
        else
            printf '%s:\n' "$key"
        fi
    done
} >>"$topic" || die 2 "cannot write to topic file: $topic"

printf '%s: created %s\n' "$topic" "$name"
