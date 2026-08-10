#!/usr/bin/env bash
# sec.sh — print sections of a markdown file, addressed by heading.
#
#   sec.sh <file> <id>...
#
# An id resolves against a heading's GitHub anchor slug (lowercased, punctuation
# dropped, spaces to hyphens) or against the exact heading text. The heading line
# itself is part of the output.
#
# A section ends at the next heading whose level is less than or equal to the
# matched heading's level, or at end-of-file. A deeper heading stays inside the
# section — that level arithmetic is the whole correctness question here.
#
# With several ids, sections are emitted in the order the ids were given,
# separated by one blank line. Trailing blank lines are trimmed from each section
# so that separator means exactly one blank line regardless of the source layout.
#
# Every id is resolved before anything is printed, so a failing call emits no
# partial section.
#
# Exit codes are the contract:
#   0  every section printed
#   2  usage error
#   3  file missing or unreadable
#   4  at least one id resolved to no heading (every such id is named on stderr)
#   5  at least one id resolved to more than one heading (never silently the first)
#
# When both 4 and 5 apply, both are reported on stderr and the exit code is 4.
set -uo pipefail

die() {
    local code=$1
    shift
    printf 'sec: %s\n' "$*" >&2
    exit "$code"
}

[ "$#" -ge 2 ] || die 2 "usage: sec.sh <file> <id>... (got $# argument(s))"

file=$1
shift

[ -f "$file" ] || die 3 "no such file: $file"
[ -r "$file" ] || die 3 "file is not readable: $file"

# Ids travel through the environment rather than as awk arguments so that no id
# is reinterpreted as a filename or as an awk assignment.
SEC_IDS=$(printf '%s\n' "$@")
export SEC_IDS

awk -v file="$file" '
function slug(text,    lowered, i, ch, out) {
    lowered = tolower(text)
    out = ""
    for (i = 1; i <= length(lowered); i++) {
        ch = substr(lowered, i, 1)
        if (ch ~ /[a-z0-9_-]/)
            out = out ch
        else if (ch == " " || ch == "\t")
            out = out "-"
    }
    return out
}

{
    line[NR] = $0
    if ($0 ~ /^#+[[:space:]]/) {
        rest = $0
        sub(/^#+/, "", rest)
        level = length($0) - length(rest)
        gsub(/^[[:space:]]+/, "", rest)
        gsub(/[[:space:]]+$/, "", rest)
        headings++
        hline[headings] = NR
        hlevel[headings] = level
        htext[headings] = rest
        hslug[headings] = slug(rest)
    }
}

END {
    wanted = split(ENVIRON["SEC_IDS"], want, "\n")

    unresolved = 0
    ambiguous = 0

    # Resolve every id first: a failure must not leave partial output behind.
    for (q = 1; q <= wanted; q++) {
        found = 0
        for (i = 1; i <= headings; i++)
            if (hslug[i] == want[q] || htext[i] == want[q])
                hit[q, ++found] = i
        count[q] = found

        if (found == 0) {
            unresolved++
            printf("sec: no heading in %s matches id: %s\n", file, want[q]) > "/dev/stderr"
        } else if (found > 1) {
            ambiguous++
            printf("sec: ambiguous id in %s: %s matches %d headings\n", file, want[q], found) > "/dev/stderr"
            for (k = 1; k <= found; k++)
                printf("sec:   line %d: %s\n", hline[hit[q, k]], line[hline[hit[q, k]]]) > "/dev/stderr"
        }
    }

    if (unresolved > 0)
        exit 4
    if (ambiguous > 0)
        exit 5

    for (q = 1; q <= wanted; q++) {
        chosen = hit[q, 1]
        start = hline[chosen]
        end = NR
        for (i = chosen + 1; i <= headings; i++)
            if (hlevel[i] <= hlevel[chosen]) {
                end = hline[i] - 1
                break
            }
        while (end > start && line[end] ~ /^[[:space:]]*$/)
            end--

        if (q > 1)
            print ""
        for (n = start; n <= end; n++)
            print line[n]
    }
}
' "$file"
