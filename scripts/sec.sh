#!/usr/bin/env bash
# sec.sh — print one section of a markdown file, addressed by heading.
#
#   sec.sh <file> <id>
#
# An id resolves against a heading's GitHub anchor slug (lowercased, punctuation
# dropped, spaces to hyphens) or against the exact heading text. The heading line
# itself is part of the output.
#
# The section ends at the next heading whose level is less than or equal to the
# matched heading's level, or at end-of-file. A deeper heading stays inside the
# section — that level arithmetic is the whole correctness question here.
#
# Exit codes are a contract:
#   0  section printed
#   2  usage error
#   3  file missing or unreadable
#   4  id resolved to no heading
#   5  id resolved to more than one heading (never silently the first)
set -uo pipefail

die() {
    local code=$1
    shift
    printf 'sec: %s\n' "$*" >&2
    exit "$code"
}

[ "$#" -eq 2 ] || die 2 "usage: sec.sh <file> <id> (got $# argument(s))"

file=$1
id=$2

[ -f "$file" ] || die 3 "no such file: $file"
[ -r "$file" ] || die 3 "file is not readable: $file"

awk -v id="$id" -v file="$file" '
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
    matches = 0
    for (i = 1; i <= headings; i++)
        if (hslug[i] == id || htext[i] == id)
            sel[++matches] = i

    if (matches == 0) {
        printf("sec: no heading in %s matches id: %s\n", file, id) > "/dev/stderr"
        exit 4
    }
    if (matches > 1) {
        printf("sec: ambiguous id in %s: %s matches %d headings\n", file, id, matches) > "/dev/stderr"
        for (k = 1; k <= matches; k++)
            printf("sec:   line %d: %s\n", hline[sel[k]], line[hline[sel[k]]]) > "/dev/stderr"
        exit 5
    }

    chosen = sel[1]
    start = hline[chosen]
    end = NR
    for (i = chosen + 1; i <= headings; i++)
        if (hlevel[i] <= hlevel[chosen]) {
            end = hline[i] - 1
            break
        }

    for (n = start; n <= end; n++)
        print line[n]
}
' "$file"
