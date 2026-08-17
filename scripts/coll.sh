#!/usr/bin/env bash
# coll.sh — print named collections, expanded to the conventions they point at.
#
#   coll.sh [--dir <dir>] [--conv-dir <dir>] <name>...
#
# A collection is declared by a heading of the exact form
#
#   ### collection: <name>
#
# holding a `members: <comma-separated names>` field. Fetching a collection
# prints, in member order, each member's own convention (via conv.sh) or —
# recursively — each nested collection's own expansion. There is no index file,
# for the same reason conv.sh has none: a scan cannot disagree with the
# collections declared, a stored index can.
#
# A member ending in '*' is a PREFIX match against declared convention names
# (never against collection names — a collection is always referenced by its
# exact name, since collections are meant to be named deliberately, not swept
# up accidentally by a wildcard). 'worktree-scope*' expands to every convention
# whose name starts with 'worktree-scope', in conv-list.sh's own sorted order.
# This exists because this codebase's own convention-naming convention is
# '<topic>-<subname>' for any topic with more than one entry — spelling out
# every sub-name in every role-collection would drift the moment a topic file
# gains a new entry. A prefix that matches zero conventions is class 4
# (unresolved), same as a literal name that matches nothing.
#
# <dir> (the collections directory) defaults to collections/. <conv-dir> (passed
# through to conv.sh as --dir) defaults to conventions/.
#
# Exit codes are the contract:
#   0  every collection fully expanded and printed
#   2  usage error
#   3  collections directory missing, or it holds no .md files
#   4  at least one name is not defined anywhere (every such name is named on stderr)
#   5  at least one name is defined in more than one file (every file is named)
#   6  a cycle was found while expanding a collection (the cycle is named on stderr)
#   7  a member name does not resolve as either a collection or a convention
#      (conv.sh's own 4/5 for that member are surfaced verbatim)
#
# Every top-level name is resolved, and every member transitively reachable from
# it is resolved, before anything prints — a failing call emits no partial
# collection, same discipline as conv.sh.
set -uo pipefail

SELF_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || {
    printf 'coll: cannot resolve script directory\n' >&2
    exit 2
}
CONV="$SELF_DIR/conv.sh"
CONV_LIST="$SELF_DIR/conv-list.sh"
MARKER_PREFIX='### collection: '

die() {
    local code=$1
    shift
    printf 'coll: %s\n' "$*" >&2
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
            printf 'usage: coll.sh [--dir <dir>] [--conv-dir <dir>] <name>...\n'
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

[ "$#" -ge 1 ] || die 2 'usage: coll.sh [--dir <dir>] [--conv-dir <dir>] <name>... (no name given)'
[ -x "$CONV" ] || die 2 "conv.sh not found or not executable: $CONV"
[ -x "$CONV_LIST" ] || die 2 "conv-list.sh not found or not executable: $CONV_LIST"
[ -d "$dir" ] || die 3 "no such collections directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in collections directory: $dir"

marker_count() {
    awk -v want="$MARKER_PREFIX$2" '$0 == want { hits++ } END { print hits + 0 }' "$1"
}

declared_names() {
    awk -v prefix="$MARKER_PREFIX" '
        index($0, prefix) == 1 { print substr($0, length(prefix) + 1) }
    ' "${files[@]}" | LC_ALL=C sort -u
}

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

# Resolve a collection name to the one file declaring it. Prints the file path
# on stdout; returns 4 (unresolved) or 5 (duplicated) exactly as conv.sh does,
# so both tools report the same way for the same class of failure.
resolve_file() {
    local name=$1
    local holders=()
    local f
    for f in "${files[@]}"; do
        [ "$(marker_count "$f" "$name")" -gt 0 ] && holders+=("$f")
    done
    if [ "${#holders[@]}" -eq 0 ]; then
        printf 'coll: no collection named %s in %s\n' "$name" "$dir" >&2
        local suggestions
        suggestions=$(near_misses "$name")
        if [ -n "$suggestions" ]; then
            while IFS= read -r s; do
                printf 'coll:   did you mean: %s\n' "$s" >&2
            done <<<"$suggestions"
        fi
        return 4
    elif [ "${#holders[@]}" -gt 1 ]; then
        printf 'coll: collection %s is defined in %d files\n' "$name" "${#holders[@]}" >&2
        for f in "${holders[@]}"; do
            printf 'coll:   %s\n' "$f" >&2
        done
        return 5
    fi
    printf '%s\n' "${holders[0]}"
    return 0
}

# Expand a '<prefix>*' member into every declared convention name starting
# with <prefix>, in conv-list.sh's own sorted order. Prints one name per line;
# prints nothing (and returns 4) if no convention matches.
prefix_matches() {
    local prefix=$1
    local matched=0
    local line convname
    while IFS= read -r line; do
        convname=${line%% | *}
        case $convname in
            "$prefix"*)
                printf '%s\n' "$convname"
                matched=1
                ;;
        esac
    done < <("$CONV_LIST" --dir "$conv_dir" 2>/dev/null)
    [ "$matched" -eq 1 ] || return 4
    return 0
}

# Read a collection's members: field, comma-separated, trimmed, order preserved.
members_of() {
    local file=$1 name=$2
    awk -v prefix="$MARKER_PREFIX$name" '
        $0 == prefix { in_block = 1; next }
        in_block && /^#/ { exit }
        in_block && index($0, "members: ") == 1 {
            print substr($0, 10)
            exit
        }
    ' "$file"
}

overall_exit=0
note_exit() {
    local code=$1
    if [ "$overall_exit" -eq 0 ] || [ "$code" -lt "$overall_exit" ]; then
        overall_exit=$code
    fi
}

# Expand one name into a flat, ordered list of convention names, resolving
# nested collections depth-first. Cycle detection walks the ancestor chain
# passed in $2 (space-separated, always starts empty at the top call).
expand=()
expand_into() {
    local name=$1 ancestors=$2
    local file rc
    case " $ancestors " in
        *" $name "*)
            printf 'coll: cycle detected: %s -> %s\n' "$ancestors" "$name" >&2
            note_exit 6
            return
            ;;
    esac

    file=$(resolve_file "$name")
    rc=$?
    if [ "$rc" -ne 0 ]; then
        note_exit "$rc"
        return
    fi

    local raw member
    raw=$(members_of "$file" "$name")
    if [ -z "$raw" ]; then
        printf 'coll: collection %s in %s has no members: field\n' "$name" "$file" >&2
        note_exit 7
        return
    fi

    IFS=',' read -ra parts <<<"$raw"
    for member in "${parts[@]}"; do
        member=$(printf '%s' "$member" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        [ -n "$member" ] || continue

        case $member in
            *'*')
                local pfx=${member%'*'}
                local matched
                if ! matched=$(prefix_matches "$pfx"); then
                    printf 'coll: member %s of collection %s matches no convention in %s\n' "$member" "$name" "$conv_dir" >&2
                    note_exit 4
                    continue
                fi
                while IFS= read -r conv_name; do
                    [ -n "$conv_name" ] && expand+=("$conv_name")
                done <<<"$matched"
                continue
                ;;
        esac

        # A member is a collection if any collections file declares it; else
        # it's assumed to be a convention name, resolved by conv.sh at print time.
        local is_collection=0
        local f2
        for f2 in "${files[@]}"; do
            if [ "$(marker_count "$f2" "$member")" -gt 0 ]; then
                is_collection=1
                break
            fi
        done
        if [ "$is_collection" -eq 1 ]; then
            expand_into "$member" "$ancestors $name"
        else
            expand+=("$member")
        fi
    done
}

names=("$@")
for name in "${names[@]}"; do
    expand_into "$name" ""
done

[ "$overall_exit" -eq 0 ] || exit "$overall_exit"
[ "${#expand[@]}" -gt 0 ] || die 3 'expansion produced no convention names'

"$CONV" --dir "$conv_dir" "${expand[@]}"
exit $?
