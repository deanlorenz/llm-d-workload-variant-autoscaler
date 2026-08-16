#!/usr/bin/env bash
# step-check-judgment-repo.sh — build the throwaway repo for one step-check
# judgment-mark case (S3). Invoked by tests/git-run.sh.
#
#   step-check-judgment-repo.sh <dir> <case>
#
# Every case uses branch "demo", step "S03", slug "fixture-count-ambiguous",
# and scope "src" (all files that matter live under src/). A ledger and a
# handoffs directory are written inside <dir> so the case's own step-check
# invocation can point --ledger/--handoffs-dir at them with a plain relative
# path once tests/git-run.sh has cd'd in.
set -uo pipefail

die() {
    printf 'step-check-judgment-repo: %s\n' "$*" >&2
    exit 1
}

[ "$#" -eq 2 ] || die 'usage: step-check-judgment-repo.sh <dir> <case>'
dir=$1
case_name=$2

branch=demo
step=S03
slug=fixture-count-ambiguous

git -C "$dir" init -q -b "$branch" || die 'git init failed'
git -C "$dir" config user.name 'Test User' || die 'git config (user.name) failed'
git -C "$dir" config user.email 'test@example.invalid' || die 'git config (user.email) failed'
git -C "$dir" config commit.gpgsign false || die 'git config (commit.gpgsign) failed'
git -C "$dir" config tag.gpgsign false || die 'git config (tag.gpgsign) failed'

mkdir -p -- "$dir/src" || die 'mkdir failed'
printf 'seed\n' >"$dir/README.md"
git -C "$dir" add -A || die 'git add (seed) failed'
git -C "$dir" commit -q -m 'seed' || die 'seed commit failed'

commit_work() {
    printf '%s\n' "$1" >"$dir/src/thing.md"
    git -C "$dir" add -A || die 'git add (work) failed'
    git -C "$dir" commit -q -m "$2" || die 'work commit failed'
    git -C "$dir" rev-parse HEAD || die 'rev-parse (work) failed'
}

commit_judgment() {
    printf '%s\n' "$1" >"$dir/src/extra.md"
    git -C "$dir" add -A || die 'git add (judgment) failed'
    git -C "$dir" commit -q -m "$2" || die 'judgment commit failed'
    git -C "$dir" rev-parse HEAD || die 'rev-parse (judgment) failed'
}

write_ledger() {
    # $1: commit line ('' to omit) $2: judgment line ('' to omit)
    {
        printf 'last_update: 2026-01-01T00:00:00Z\n'
        printf 'state: in-progress\n'
        printf '\n'
        printf '## Step log\n'
        [ -z "$1" ] || printf '%s\n' "$1"
        [ -z "$2" ] || printf '%s\n' "$2"
    } >"$dir/ledger.md"
}

write_handoff() {
    mkdir -p -- "$dir/handoffs" || die 'mkdir (handoffs) failed'
    printf 'from: %s\nto: spec-owner\nsession: test\n\nJudgment %s was surfaced for review.\n' \
        "$branch" "$1" >"$dir/handoffs/spec__$1.md"
}

case $case_name in
    clean)
        work_sha=$(commit_work 'first' 'S03 work')
        judgment_sha=$(commit_judgment 'first' 'S03 judgment')
        git -C "$dir" tag "judgment/$branch/$step-$slug" "$judgment_sha" || die 'git tag failed'
        write_ledger \
            "$step · commit $work_sha · verify pass · ordinary work for $step" \
            "$step · judgment $slug · ambiguous: fixture count · assumed: use the larger set · why: spec silent · revert: git revert judgment/$branch/$step-$slug · decision: spec owner"
        write_handoff "$slug"
        ;;
    no-tag)
        work_sha=$(commit_work 'first' 'S03 work')
        write_ledger \
            "$step · commit $work_sha · verify pass · ordinary work for $step" \
            "$step · judgment $slug · ambiguous: fixture count · assumed: use the larger set · why: spec silent · revert: git revert judgment/$branch/$step-$slug · decision: spec owner"
        write_handoff "$slug"
        ;;
    shares-commit)
        work_sha=$(commit_work 'first' 'S03 work')
        git -C "$dir" tag "judgment/$branch/$step-$slug" "$work_sha" || die 'git tag failed'
        write_ledger \
            "$step · commit $work_sha · verify pass · ordinary work for $step" \
            "$step · judgment $slug · ambiguous: fixture count · assumed: use the larger set · why: spec silent · revert: git revert judgment/$branch/$step-$slug · decision: spec owner"
        write_handoff "$slug"
        ;;
    unlogged-tag)
        work_sha=$(commit_work 'first' 'S03 work')
        judgment_sha=$(commit_judgment 'first' 'S03 judgment, never logged')
        other_slug=never-logged
        git -C "$dir" tag "judgment/$branch/$step-$other_slug" "$judgment_sha" || die 'git tag failed'
        write_ledger "$step · commit $work_sha · verify pass · ordinary work for $step" ''
        ;;
    no-handoff)
        work_sha=$(commit_work 'first' 'S03 work')
        judgment_sha=$(commit_judgment 'first' 'S03 judgment')
        git -C "$dir" tag "judgment/$branch/$step-$slug" "$judgment_sha" || die 'git tag failed'
        write_ledger \
            "$step · commit $work_sha · verify pass · ordinary work for $step" \
            "$step · judgment $slug · ambiguous: fixture count · assumed: use the larger set · why: spec silent · revert: git revert judgment/$branch/$step-$slug · decision: spec owner"
        ;;
    ledger-omitted)
        commit_work 'first' 'S03 work' >/dev/null
        ;;
    *)
        die "unknown case: $case_name"
        ;;
esac

# ledger.md and handoffs/ are test scaffolding, not step work: commit them
# (when present) so the tree is clean before step-check runs. In real use
# these live in a sibling plans/ worktree and never appear in a coder's own
# git status at all; committing them here is the throwaway-repo equivalent.
if [ -n "$(git -C "$dir" status --porcelain)" ]; then
    git -C "$dir" add -A || die 'git add (fixture wrap-up) failed'
    git -C "$dir" commit -q -m 'test fixture: ledger and handoffs' || die 'fixture wrap-up commit failed'
fi
