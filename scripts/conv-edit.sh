#!/usr/bin/env bash
# conv-edit.sh — replace one convention's section in place.
#
#   conv-edit.sh [--dir <dir>] <name> --from <file>
#
# Locates <name> the same way conv.sh does — scanning <dir>/*.md (default
# conventions/) for its '### convention: <name>' marker — then replaces that
# section, heading through the next heading of level 3 or shallower (the same
# boundary rule sec.sh and conv-lint.sh use), with the contents of <file>.
# Everything above and below the section is untouched, byte for byte.
#
# <file> must supply the section whole, marker included: its first line must
# be the exact '### convention: <name>' heading being replaced. There is no
# fallback that reuses the old marker when it is missing — this tool never
# invents content, so a replacement that drops the marker is rejected rather
# than silently patched, which is also what keeps
#
#   conv <name> > a; conv-edit <name> --from a; conv <name> > b; diff a b
#
# byte-exact: a is exactly what conv prints, marker included, so --from's
# contract matches what conv already hands back.
#
# Writes happen via a temp file in the same directory followed by an atomic
# rename; the original is never edited in place, and any failure leaves it
# untouched.
#
# Exit codes are the contract:
#   0  section replaced
#   2  usage error
#   3  no convention named <name> in <dir>
#   4  <name> is declared in more than one file under <dir> (ambiguous)
#   5  --from file missing or unreadable
#   6  --from's first line is not the exact marker for <name>
set -uo pipefail

MARKER_PREFIX='### convention: '

die() {
    local code=$1
    shift
    printf 'conv-edit: %s\n' "$*" >&2
    exit "$code"
}

dir=conventions
name=
from=

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
        --from)
            [ "$#" -ge 2 ] || die 2 '--from needs a file argument'
            from=$2
            shift 2
            ;;
        --from=*)
            from=${1#--from=}
            shift
            ;;
        -h|--help)
            printf 'usage: conv-edit.sh [--dir <dir>] <name> --from <file>\n'
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

[ -n "$name" ] || die 2 'usage: conv-edit.sh [--dir <dir>] <name> --from <file> (no name given)'
[ -n "$from" ] || die 2 '--from <file> is required'
[ -d "$dir" ] || die 3 "no such conventions directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in conventions directory: $dir"

want="$MARKER_PREFIX$name"
holders=()
for f in "${files[@]}"; do
    hits=$(awk -v want="$want" '$0 == want { c++ } END { print c + 0 }' "$f")
    [ "$hits" -gt 0 ] && holders+=("$f")
done

if [ "${#holders[@]}" -eq 0 ]; then
    die 3 "no convention named $name in $dir"
elif [ "${#holders[@]}" -gt 1 ]; then
    printf 'conv-edit: convention %s is defined in %d files\n' "$name" "${#holders[@]}" >&2
    for f in "${holders[@]}"; do
        printf 'conv-edit:   %s\n' "$f" >&2
    done
    exit 4
fi
target=${holders[0]}

[ -f "$from" ] || die 5 "no such file: $from"
[ -r "$from" ] || die 5 "file is not readable: $from"

first_line=$(head -n 1 -- "$from")
[ "$first_line" = "$want" ] || die 6 "$from does not begin with the exact marker '$want' (got: ${first_line:-<empty file>})"

# Trim trailing blank lines from the replacement, the same trim sec.sh applies
# on read, so a round trip through conv | conv-edit reproduces byte-exact
# content rather than accumulating blank lines on every pass.
replacement=$(awk '{ line[NR] = $0 } END {
    end = NR
    while (end > 0 && line[end] ~ /^[[:space:]]*$/)
        end--
    for (n = 1; n <= end; n++)
        print line[n]
}' "$from")

span=$(awk -v want="$want" '
{
    line[NR] = $0
    if ($0 ~ /^#+[[:space:]]/) {
        rest = $0
        sub(/^#+/, "", rest)
        level = length($0) - length(rest)
        headings++
        hline[headings] = NR
        hlevel[headings] = level
        htext[headings] = $0
    }
}
END {
    for (i = 1; i <= headings; i++) {
        if (htext[i] == want) {
            if (matched) {
                print "AMBIGUOUS"
                exit
            }
            matched = i
        }
    }
    if (!matched) {
        print "NOTFOUND"
        exit
    }
    start = hline[matched]
    end = NR
    for (i = matched + 1; i <= headings; i++) {
        if (hlevel[i] <= 3) {
            end = hline[i] - 1
            break
        }
    }
    # Trim trailing blank lines from what counts as "replaced", the same
    # trim sec.sh applies on read. Any blank lines between the old content
    # and whatever follows (next heading, or EOF) are a neighbour, not part
    # of this section, and must pass through untouched rather than being
    # resynthesized — otherwise a replacement with no trailing blank of its
    # own would glue directly onto the next heading.
    while (end > start && line[end] ~ /^[[:space:]]*$/)
        end--
    print "OK\t" start "\t" end
}
' "$target")

case $span in
    NOTFOUND)   die 3 "marker for $name disappeared from $target between scan and edit" ;;
    AMBIGUOUS)  die 4 "convention $name is declared more than once in $target" ;;
esac
IFS=$'\t' read -r _ start end <<<"$span"

tmp="$target.conv-edit.tmp.$$"
# The replacement travels through the environment rather than as an awk -v
# assignment: -v processes backslash escapes in its value, and convention
# bodies are free-form text that may contain literal backslashes.
CONV_EDIT_REPLACEMENT=$replacement
export CONV_EDIT_REPLACEMENT
awk -v start="$start" -v end="$end" '
BEGIN { n = split(ENVIRON["CONV_EDIT_REPLACEMENT"], rlines, "\n") }
{
    if (NR == start) {
        for (i = 1; i <= n; i++)
            print rlines[i]
    }
    if (NR < start || NR > end)
        print
}
' "$target" >"$tmp" || { rm -f -- "$tmp"; die 2 "failed to build replacement content for: $target"; }

mv -- "$tmp" "$target" || { rm -f -- "$tmp"; die 2 "failed to install replacement for: $target"; }

printf '%s: replaced %s\n' "$target" "$name"
