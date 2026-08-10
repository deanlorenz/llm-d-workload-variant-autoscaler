#!/usr/bin/env bash
# conv.sh — print named conventions, wherever they live.
#
#   conv.sh [--dir <dir>] <name>...
#
# There is no index file. A convention is declared by a heading of the exact form
#
#   ### convention: <name>
#
# so the marker carries the name and a scan cannot go stale the way a stored
# index can. <dir> defaults to conventions/.
#
# Extraction is delegated to scripts/sec.sh. This script contains no section
# logic of its own: two copies of the heading-level arithmetic would drift, and
# the drift would be silent.
#
# Every name is resolved before anything prints, so a failing call emits no
# partial convention.
#
# Exit codes are the contract:
#   0  every convention printed
#   2  usage error
#   3  directory missing, or it holds no .md files
#   4  at least one name is not defined anywhere (every such name is named on stderr)
#   5  at least one name is defined in more than one file (every file is named)
#
# When both 4 and 5 apply, both are reported on stderr and the exit code is 4.
# Uniqueness is conv-lint's job to report; conv's job is to refuse to choose.
set -uo pipefail

SELF_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || {
    printf 'conv: cannot resolve script directory\n' >&2
    exit 2
}
SEC="$SELF_DIR/sec.sh"
MARKER_PREFIX='### convention: '
# sec.sh matches heading text with the leading hashes stripped.
SEC_ID_PREFIX='convention: '

die() {
    local code=$1
    shift
    printf 'conv: %s\n' "$*" >&2
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
            printf 'usage: conv.sh [--dir <dir>] <name>...\n'
            exit 0
            ;;
        --*)
            die 2 "unknown option: $1"
            ;;
        *)
            break
            ;;
    esac
done

[ "$#" -ge 1 ] || die 2 'usage: conv.sh [--dir <dir>] <name>... (no name given)'
[ -x "$SEC" ] || die 2 "extractor not found or not executable: $SEC"
[ -d "$dir" ] || die 3 "no such conventions directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in conventions directory: $dir"

# Count exact marker lines for one name in one file.
marker_count() {
    awk -v want="$MARKER_PREFIX$2" '$0 == want { hits++ } END { print hits + 0 }' "$1"
}

# Every declared name, sorted, one per line. Used for near-miss suggestions.
declared_names() {
    awk -v prefix="$MARKER_PREFIX" '
        index($0, prefix) == 1 { print substr($0, length(prefix) + 1) }
    ' "${files[@]}" | LC_ALL=C sort -u
}

# Names related to a typo: either contains the query or is contained by it,
# case-insensitively. Cheap, deterministic, and enough to catch a wrong plural
# or a dropped word.
near_misses() {
    local query
    query=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
    declared_names | while IFS= read -r candidate; do
        local lowered
        lowered=$(printf '%s' "$candidate" | tr '[:upper:]' '[:lower:]')
        case $lowered in
            *"$query"*) printf '%s\n' "$candidate" ;;
            *) case $query in
                   *"$lowered"*) printf '%s\n' "$candidate" ;;
               esac ;;
        esac
    done
}

names=("$@")
resolved=()
unresolved=0
duplicated=0

for name in "${names[@]}"; do
    holders=()
    for f in "${files[@]}"; do
        [ "$(marker_count "$f" "$name")" -gt 0 ] && holders+=("$f")
    done

    if [ "${#holders[@]}" -eq 0 ]; then
        unresolved=$((unresolved + 1))
        resolved+=('')
        printf 'conv: no convention named %s in %s\n' "$name" "$dir" >&2
        suggestions=$(near_misses "$name")
        if [ -n "$suggestions" ]; then
            while IFS= read -r s; do
                printf 'conv:   did you mean: %s\n' "$s" >&2
            done <<<"$suggestions"
        fi
    elif [ "${#holders[@]}" -gt 1 ]; then
        duplicated=$((duplicated + 1))
        resolved+=('')
        printf 'conv: convention %s is defined in %d files\n' "$name" "${#holders[@]}" >&2
        for f in "${holders[@]}"; do
            printf 'conv:   %s\n' "$f" >&2
        done
    else
        resolved+=("${holders[0]}")
    fi
done

[ "$unresolved" -eq 0 ] || exit 4
[ "$duplicated" -eq 0 ] || exit 5

for i in "${!names[@]}"; do
    [ "$i" -eq 0 ] || printf '\n'
    "$SEC" "${resolved[i]}" "$SEC_ID_PREFIX${names[i]}" || exit $?
done
