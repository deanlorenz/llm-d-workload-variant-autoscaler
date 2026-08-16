#!/usr/bin/env bash
# conv-rename.sh — rename a convention and rewrite every citation of it, or
# change nothing at all. Also the refusal-to-delete surface.
#
#   conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... <old> <new>
#   conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... --delete <name> [--force-approved]
#
# Half a rename is worse than no rename: a citation left pointing at a name
# that no longer exists fails at fetch time, and the caller then halts as
# though the convention had never existed. So every write is staged into a
# temp sibling first, and the originals are only replaced once every staged
# file has been built successfully.
#
# --dir (default conventions/) is where the '### convention: <name>' marker
# lives, scanned flat, exactly as conv.sh, conv-edit.sh and conv-lint.sh scan
# it. --cite-dirs is where citations live.
#
# --cite-dirs is repeatable rather than a single delimited string: repeat the
# flag once per directory. With none given it defaults to two entries,
# planning and roles. A cite-dir that does not exist is skipped silently, the
# same tolerance conv-new gives a missing --dir — the defaults name
# directories that only exist in the plans worktree, so requiring them would
# make every invocation elsewhere fail.
#
# WHAT COUNTS AS A CITATION (the definition plan-lint must share): a
# whole-token, case-sensitive occurrence of the name on any line of any .md
# file under a cite-dir. "Whole-token" means the character on each side of the
# match is not in [a-z0-9-] (or the match is at the start or end of the line)
# — the same alphabet conv-new validates names against. That single rule is
# what keeps a rename of commit-message from also mangling
# commit-message-shape, and it covers both citation shapes uniformly: a step's
# '**conventions** — name, other-name' manifest line and a bare or
# backtick-quoted prose mention are the same substring-with-boundary problem
# regardless of the markdown around them.
#
# Unlike --dir, cite-dirs are scanned RECURSIVELY. That is deliberate, not an
# oversight: conventions/ is flat by design, but planning/ is not (it already
# holds an archive/ subdirectory), and under-matching a citation is the exact
# failure this tool exists to prevent, so it over-scans rather than misses one.
#
# Two consequences of that definition, documented rather than special-cased:
#
#   * A convention citing another convention inside --dir is out of scope,
#     because --dir is not a cite-dir. A caller may pass --dir's value as a
#     --cite-dirs entry, but then the renamed convention's own marker line and
#     the field lines around it are themselves whole-token occurrences of its
#     name, so they count as citations of itself — harmless for a rename, but
#     it makes --delete refuse unconditionally with exit 8.
#   * Documents under planning/archive/ are rewritten like anything else. No
#     exclusion is applied: rewriting history in an archive is uncomfortable,
#     but a half-applied rename is the worse failure.
#
# --delete <name> removes a convention's whole section from its topic file,
# and mostly refuses to. It refuses while any citation exists, naming every
# citing file; that refusal is unconditional and --force-approved does not
# override it. With zero citations it still refuses unless --force-approved is
# passed, because removal needs long probation and explicit approval — this
# tool must not be the thing that makes removal easy.
#
# Check order matters for what a failing run reports, so it is fixed: usage,
# then <new>'s spelling, then --dir, then locating <old> (reporting "not
# found" in preference to a conflict, since that is the more actionable of the
# two), then <new>'s conflict.
#
# Exit codes are the contract:
#   0   renamed, or deleted
#   2   usage error, or a staged file could not be built — the two conditions
#       that leave the tree exactly as it was. conv-edit already uses 2 for a
#       build failure, so they stay the same code across the two tools; only a
#       failure that has already changed something (10) gets its own.
#   3   --dir missing, or it holds no .md files
#   4   invalid <new>: does not match [a-z0-9-]+
#   5   <new> already exists (this also catches a same-name no-op rename)
#   6   <old>, or --delete's <name>, not found in --dir
#   7   the name's marker appears more than once (in one file or across files)
#   8   --delete refused: still cited, every citing file named on stderr
#   9   --delete refused: uncited, but --force-approved was not given
#   10  a staged file could not be installed, after every check had passed
set -uo pipefail

MARKER_PREFIX='### convention: '

die() {
    local code=$1
    shift
    printf 'conv-rename: %s\n' "$*" >&2
    exit "$code"
}

# Rewrite whole-token occurrences of CONV_RENAME_OLD with CONV_RENAME_NEW.
#
# Both travel through the environment rather than as awk -v assignments: -v
# processes backslash escapes in its value, and while a valid convention name
# cannot contain one, <old> is never validated — it only has to match a marker
# that is already on disk — so it must not be put through an escape pass.
#
# Scanning is by index() rather than a regex so there is nothing to escape at
# all. `prev` carries the character preceding the remaining text, which after
# a skipped near-miss is the last character of <old> itself: without that,
# "abab" would treat the second "ab" as line-initial and rewrite it.
#
# The awk programs below live in variables because two of them are used at
# more than one call site. shellcheck cannot tell an awk program held in a
# variable from a shell expression, so each one silences SC2016 for its own
# $0 and friends; they are awk's, deliberately unexpanded by the shell.
# shellcheck disable=SC2016
AWK_TOKEN_REWRITE='
function is_boundary(c) { return (c == "" || c !~ /[a-z0-9-]/) }
function rewrite(s,   out, rest, prev, after, pos, len_old) {
    out = ""
    rest = s
    prev = ""
    len_old = length(OLD)
    while ((pos = index(rest, OLD)) > 0) {
        if (pos > 1)
            prev = substr(rest, pos - 1, 1)
        after = substr(rest, pos + len_old, 1)
        out = out substr(rest, 1, pos - 1)
        if (is_boundary(prev) && is_boundary(after)) {
            out = out NEW
            COUNT++
        } else {
            out = out OLD
        }
        prev = substr(OLD, len_old, 1)
        rest = substr(rest, pos + len_old)
    }
    return out rest
}
BEGIN {
    OLD = ENVIRON["CONV_RENAME_OLD"]
    NEW = ENVIRON["CONV_RENAME_NEW"]
    COUNT = 0
    if (OLD == "") {
        FATAL = 1
        print "conv-rename: internal error: empty name to match" > "/dev/stderr"
        exit 2
    }
}
{
    line = rewrite($0)
    if (mode == "rewrite")
        print line
}
END {
    if (FATAL)
        exit 2
    if (mode == "count")
        print COUNT + 0
}
'

# Rewrite only the marker line, for the topic file when it is not also being
# rewritten as a citing file.
# shellcheck disable=SC2016
AWK_MARKER_ONLY='
BEGIN {
    want = ENVIRON["CONV_RENAME_WANT"]
    want_new = ENVIRON["CONV_RENAME_WANT_NEW"]
}
$0 == want { print want_new; next }
{ print }
'

# The section boundary, same rule sec.sh, conv-lint.sh and conv-edit.sh use:
# the marker heading through the line before the next heading of level 3 or
# shallower, with trailing blank lines trimmed off because they belong to the
# file's structure rather than to the section.
#
# One addition on top of conv-edit's version: a single immediately preceding
# blank line is folded into what gets removed. conv-new writes that blank as
# the separator before every marker it appends, so dropping it is the exact
# inverse of the insertion; leaving it would stack it on the separator of
# whatever follows and grow the file's blank runs on every delete.
# shellcheck disable=SC2016
AWK_SECTION_SPAN='
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
    want = ENVIRON["CONV_RENAME_WANT"]
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
    while (end > start && line[end] ~ /^[[:space:]]*$/)
        end--
    if (start > 1 && line[start - 1] ~ /^[[:space:]]*$/)
        start--
    print "OK\t" start "\t" end
}
'

AWK_DROP_RANGE='NR < from || NR > to'

# ---------------------------------------------------------------- arguments

dir=conventions
cite_dirs=()
delete_name=
force_approved=0
positional=()

usage() {
    printf 'usage: conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... <old> <new>\n'
    printf '       conv-rename.sh [--dir <dir>] [--cite-dirs <d>]... --delete <name> [--force-approved]\n'
}

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
        --cite-dirs)
            [ "$#" -ge 2 ] || die 2 '--cite-dirs needs a directory argument'
            cite_dirs+=("$2")
            shift 2
            ;;
        --cite-dirs=*)
            cite_dirs+=("${1#--cite-dirs=}")
            shift
            ;;
        --delete)
            [ "$#" -ge 2 ] || die 2 '--delete needs a name argument'
            case $2 in
                -*) die 2 "--delete needs a name argument, got an option: $2" ;;
            esac
            delete_name=$2
            shift 2
            ;;
        --delete=*)
            delete_name=${1#--delete=}
            shift
            ;;
        --force-approved)
            force_approved=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            die 2 "unknown option: $1"
            ;;
        *)
            positional+=("$1")
            shift
            ;;
    esac
done

new=
if [ -n "$delete_name" ]; then
    mode=delete
    if [ "${#positional[@]}" -gt 0 ]; then
        die 2 "--delete carries its own name; unexpected argument: ${positional[0]}"
    fi
    name=$delete_name
else
    mode=rename
    [ "$force_approved" -eq 0 ] || die 2 '--force-approved is only meaningful with --delete'
    case ${#positional[@]} in
        0) usage >&2; die 2 'no names given' ;;
        1) die 2 "rename needs both <old> and <new> (got only: ${positional[0]})" ;;
        2) ;;
        *) die 2 "unexpected argument: ${positional[2]}" ;;
    esac
    name=${positional[0]}
    new=${positional[1]}
fi

[ -n "$name" ] || die 2 'the convention name must not be empty'

if [ "$mode" = rename ]; then
    [[ $new =~ ^[a-z0-9-]+$ ]] || die 4 "invalid new name '$new': must match [a-z0-9-]+"
fi

if [ "${#cite_dirs[@]}" -eq 0 ]; then
    cite_dirs=(planning roles)
fi

# --------------------------------------------------------- locate the marker

[ -d "$dir" ] || die 3 "no such conventions directory: $dir"

files=()
while IFS= read -r f; do
    files+=("$f")
done < <(find "$dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)

[ "${#files[@]}" -gt 0 ] || die 3 "no .md files in conventions directory: $dir"

want="$MARKER_PREFIX$name"
holders=()
holder_hits=()
total_hits=0
for f in "${files[@]}"; do
    hits=$(awk -v want="$want" '$0 == want { c++ } END { print c + 0 }' "$f")
    if [ "$hits" -gt 0 ]; then
        holders+=("$f")
        holder_hits+=("$hits")
        total_hits=$((total_hits + hits))
    fi
done

[ "${#holders[@]}" -gt 0 ] || die 6 "no convention named $name in $dir"

# One check covers both duplication shapes: the same name declared in two
# files, and declared twice inside one file. Either makes every fetch of it
# ambiguous, so neither may be renamed or deleted blind.
if [ "$total_hits" -gt 1 ]; then
    printf 'conv-rename: convention %s is declared %d times\n' "$name" "$total_hits" >&2
    for ((i = 0; i < ${#holders[@]}; i++)); do
        printf 'conv-rename:   %s (%s)\n' "${holders[i]}" "${holder_hits[i]}" >&2
    done
    exit 7
fi
marker_file=${holders[0]}

if [ "$mode" = rename ]; then
    want_new="$MARKER_PREFIX$new"
    conflicts=()
    for f in "${files[@]}"; do
        hits=$(awk -v want="$want_new" '$0 == want { c++ } END { print c + 0 }' "$f")
        [ "$hits" -gt 0 ] && conflicts+=("$f")
    done
    if [ "${#conflicts[@]}" -gt 0 ]; then
        printf 'conv-rename: convention %s already exists\n' "$new" >&2
        for f in "${conflicts[@]}"; do
            printf 'conv-rename:   %s\n' "$f" >&2
        done
        exit 5
    fi
fi

# ------------------------------------------------------------ find citations

# Canonical paths are used for de-duplication only. Two cite-dirs may overlap
# (planning and planning/archive both passed, say), and the same file reached
# twice would be counted twice and staged twice — the second install silently
# discarding the first.
canon() {
    readlink -f -- "$1" 2>/dev/null || printf '%s' "$1"
}

CONV_RENAME_OLD=$name
CONV_RENAME_NEW=${new:-$name}
export CONV_RENAME_OLD CONV_RENAME_NEW

cite_files=()
cite_counts=()
cite_total=0
declare -A cite_seen=()
for d in ${cite_dirs+"${cite_dirs[@]}"}; do
    [ -d "$d" ] || continue
    while IFS= read -r f; do
        key=$(canon "$f")
        [ -n "${cite_seen[$key]+set}" ] && continue
        cite_seen[$key]=1
        hits=$(awk -v mode=count "$AWK_TOKEN_REWRITE" "$f") || die 2 "cannot read: $f"
        if [ "$hits" -gt 0 ]; then
            cite_files+=("$f")
            cite_counts+=("$hits")
            cite_total=$((cite_total + hits))
        fi
    done < <(find "$d" -type f -name '*.md' 2>/dev/null | LC_ALL=C sort)
done

# ------------------------------------------------------------------- refusals

if [ "$mode" = delete ]; then
    if [ "$cite_total" -gt 0 ]; then
        printf 'conv-rename: convention %s is still cited in %d file(s); refusing to delete\n' \
            "$name" "${#cite_files[@]}" >&2
        for ((i = 0; i < ${#cite_files[@]}; i++)); do
            printf 'conv-rename:   %s (%s)\n' "${cite_files[i]}" "${cite_counts[i]}" >&2
        done
        printf 'conv-rename: --force-approved does not override this; rename or remove the citations first\n' >&2
        exit 8
    fi
    if [ "$force_approved" -ne 1 ]; then
        printf 'conv-rename: convention %s has no citations, and is still not deletable without approval\n' "$name" >&2
        printf 'conv-rename: removal needs long probation and explicit approval; pass --force-approved to record it\n' >&2
        exit 9
    fi
fi

# --------------------------------------------------------------- build phase

# Every changed file is written to a temp sibling first. If any build fails,
# every temp already created is removed and nothing on disk has changed —
# there is no partial state to restore, because no original has been touched.
tmps=()
targets=()

drop_tmps() {
    local t
    for t in ${tmps+"${tmps[@]}"}; do
        rm -f -- "$t"
    done
}

stage() {
    local target=$1
    shift
    local tmp="$target.conv-rename.tmp.$$"
    if ! "$@" "$target" >"$tmp"; then
        rm -f -- "$tmp"
        drop_tmps
        die 2 "failed to build the new content for: $target"
    fi
    tmps+=("$tmp")
    targets+=("$target")
}

marker_is_cited=0
marker_key=$(canon "$marker_file")
for f in ${cite_files+"${cite_files[@]}"}; do
    if [ "$(canon "$f")" = "$marker_key" ]; then
        marker_is_cited=1
        break
    fi
done

if [ "$mode" = rename ]; then
    # The marker file goes first so the ordering of a report, and of the
    # install below, is fixed. When it is also a citing file its marker line
    # is itself a whole-token occurrence of the name, so the citation rewrite
    # already covers it and a second staged write would fight the first.
    if [ "$marker_is_cited" -eq 0 ]; then
        CONV_RENAME_WANT=$want
        CONV_RENAME_WANT_NEW=$want_new
        export CONV_RENAME_WANT CONV_RENAME_WANT_NEW
        stage "$marker_file" awk "$AWK_MARKER_ONLY"
    fi
    for f in ${cite_files+"${cite_files[@]}"}; do
        stage "$f" awk -v mode=rewrite "$AWK_TOKEN_REWRITE"
    done
else
    CONV_RENAME_WANT=$want
    export CONV_RENAME_WANT
    span=$(awk "$AWK_SECTION_SPAN" "$marker_file") || die 2 "cannot read: $marker_file"
    case $span in
        NOTFOUND)  die 6 "marker for $name disappeared from $marker_file between scan and delete" ;;
        AMBIGUOUS) die 7 "convention $name is declared more than once in $marker_file" ;;
    esac
    IFS=$'\t' read -r _ span_start span_end <<<"$span"
    stage "$marker_file" awk -v from="$span_start" -v to="$span_end" "$AWK_DROP_RANGE"
fi

# -------------------------------------------------------------- commit phase

# mv within one directory is a single rename, so this is the smallest commit
# window bash offers without a real transaction log. A failure here happens
# after every check has passed and cannot be provoked by any documented input;
# it is reported as its own exit code rather than folded into a usage error,
# and it says exactly how far it got, because the tree is then genuinely part
# renamed and a human has to finish it.
for ((i = 0; i < ${#targets[@]}; i++)); do
    if ! mv -- "${tmps[i]}" "${targets[i]}"; then
        printf 'conv-rename: failed to install %s after %d of %d file(s) were already installed\n' \
            "${targets[i]}" "$i" "${#targets[@]}" >&2
        printf 'conv-rename: the tree is partly rewritten; the remaining staged files are discarded\n' >&2
        for ((j = i; j < ${#tmps[@]}; j++)); do
            rm -f -- "${tmps[j]}"
        done
        exit 10
    fi
done

# ------------------------------------------------------------------- report

if [ "$mode" = delete ]; then
    printf '%s: deleted %s\n' "$marker_file" "$name"
    exit 0
fi

printf '%s: renamed %s -> %s\n' "$marker_file" "$name" "$new"
for ((i = 0; i < ${#cite_files[@]}; i++)); do
    printf '%s: %s citation(s) rewritten\n' "${cite_files[i]}" "${cite_counts[i]}"
done
printf '%d citation(s) rewritten across %d file(s)\n' "$cite_total" "${#cite_files[@]}"
