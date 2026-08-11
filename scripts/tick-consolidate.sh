#!/usr/bin/env bash
# Tier 2 of checkpoint capture: fold new user turns into the digest, rarely and cheaply.
#
# Replaces the retired per-session cron tick, which cost ~9M input tokens in one day because
# every firing re-uploaded the whole session. Three properties make this cheap instead:
#
#   1. A SMALL MODEL, via the proxy (default aws/claude-haiku-4-5).
#   2. A TINY CONTEXT. The model is invoked from a neutral directory so no CLAUDE.md chain
#      loads, and it is sent only the new turns — never this session's history, never the digest.
#   3. NO TOOL USE. The model does text-in/text-out classification only; this script does every
#      read, write, git and marker operation. Small models fail at agentic tool use, and they
#      fail silently, which is the failure mode this whole mechanism exists to prevent.
#
# VERBATIM BY CONSTRUCTION: the model never echoes Dean's words back. It returns turn numbers
# plus a label, and this script splices in the exact text it already holds. A paraphrased
# ruling is the one thing a digest must never contain, so it is made structurally impossible
# rather than requested politely.
#
# Usage:
#   tick-consolidate.sh --digest <file> --file <transcript> [--model <name>] [--dry-run]
#
# Exits 0 having done nothing when there are no new turns. Any other problem exits non-zero
# with a message on stderr — an empty result and a failure must never look alike.

set -uo pipefail

digest=""; tfile=""; model="${TICK_MODEL:-aws/claude-haiku-4-5}"; dry=0
here="$(cd "$(dirname "$0")" && pwd)"
extract="$here/session-extract.sh"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --digest) digest="${2:-}"; [ -n "$digest" ] || die "--digest needs a value"; shift 2 ;;
    --file)   tfile="${2:-}";  [ -n "$tfile" ]  || die "--file needs a value";  shift 2 ;;
    --model)  model="${2:-}";  [ -n "$model" ]  || die "--model needs a value"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$digest" ] || die "--digest is required"
[ -n "$tfile" ]  || die "--file is required (never resolve the transcript by mtime)"
[ -r "$digest" ] || die "cannot read digest: $digest"
[ -r "$tfile" ]  || die "cannot read transcript: $tfile"
[ -x "$extract" ] || die "cannot execute $extract"
command -v claude >/dev/null 2>&1 || die "claude CLI not found"

marker=$(grep -m1 -o 'Captured through:\*\* `[^`]*`' "$digest" | sed 's/.*`\([^`]*\)`.*/\1/')
[ -n "$marker" ] || die "no 'Captured through:' marker in $digest"

turns=$(SESSION_EXTRACT_ALLOW=1 "$extract" --file "$tfile" --since "$marker" 2>/dev/null) \
  || die "extract failed" 3

n=$(printf '%s' "$turns" | grep -c '^## ' || true)
[ "$n" -gt 0 ] || { printf '%s: nothing new since %s\n' "${0##*/}" "$marker" >&2; exit 0; }

# Number the turns so the model can only ever refer to them by index.
numbered=$(printf '%s\n' "$turns" | awk '
  /^## / { i++; printf "\n=== TURN %d (%s) ===\n", i, $0; next }
  { print }')

prompt=$(cat <<'INSTRUCTIONS'
You are classifying turns from a work session so they can be recorded in a durable digest.
For EACH numbered turn, output exactly one line, nothing else:

  KEEP <n> | <category> | <short label, max 12 words>
  SKIP <n> | <reason, max 8 words>

<category> is one of: ruling, decision, question, task, finding

KEEP a turn if it contains any of: an instruction or ruling from the user; a decision or a
reversal; a question they asked that was not answered; a task named but not finished; a
measurement or fact worth keeping.

SKIP a turn that is only acknowledgement, small talk, a restatement, or a request for status.

Output ONLY those lines, one per turn, in order. No preamble, no summary, no markdown fences.
Do not quote or restate the turn text — it is already recorded elsewhere; the label is yours.

TURNS:
INSTRUCTIONS
)
prompt="$prompt
$numbered"

if [ "$dry" -eq 1 ]; then
  printf '%s\n' "$prompt"
  printf '%s: dry run — %s new turn(s), model %s not invoked\n' "${0##*/}" "$n" "$model" >&2
  exit 0
fi

# Neutral cwd: keeps the subprocess from loading this project's CLAUDE.md chain, which would
# otherwise add ~26k tokens of standing context to a call meant to be cheap. No pipe here —
# piping would mask the exit status, which bit an earlier version of this tooling.
verdicts=$(cd /tmp && printf '%s' "$prompt" | timeout 300 claude -p --model "$model" 2>&1)
rc=$?
[ "$rc" -eq 0 ] || die "model call failed (rc=$rc): $(printf '%s' "$verdicts" | head -2)" 4
printf '%s' "$verdicts" | grep -qE '^(KEEP|SKIP) ' \
  || die "unparseable model output: $(printf '%s' "$verdicts" | head -3)" 5

# Splice: for each KEEP, take the turn's ACTUAL text from what we already hold.
entry=$(printf '%s' "$verdicts" | grep '^KEEP ' | while IFS= read -r line; do
  idx=$(printf '%s' "$line" | awk '{print $2}')
  cat=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$2); print $2}')
  lab=$(printf '%s' "$line" | awk -F'|' '{gsub(/^ +| +$/,"",$3); print $3}')
  case "$idx" in ''|*[!0-9]*) die "model returned a non-numeric turn index: $line" 6 ;; esac
  [ "$idx" -ge 1 ] && [ "$idx" -le "$n" ] || die "turn index $idx out of range 1..$n" 6
  body=$(printf '%s\n' "$numbered" | awk -v want="$idx" '
    $0 ~ "^=== TURN "want" \\(" { on=1; next }
    /^=== TURN / { on=0 }
    on { print }')
  printf -- '- **%s** — %s\n' "$cat" "$lab"
  printf '%s\n' "$body" | sed '/^[[:space:]]*$/d; s/^/  > /'
done) || exit $?

[ -n "$entry" ] || { printf '%s: model kept nothing of %s turn(s)\n' "${0##*/}" "$n" >&2; }

newest=$(printf '%s' "$turns" | grep '^## ' | tail -1 | sed 's/^## //; s/  *(mid-turn)$//')
[ -n "$newest" ] || die "could not determine newest timestamp" 7

grep -q '^## Consolidated capture' "$digest" || printf '\n---\n\n## Consolidated capture\n\nAppended by `scripts/tick-consolidate.sh`: turns selected by a small model, text spliced verbatim\nby the script. Uncurated — the sections above are the curated record.\n' >> "$digest"

{ printf '\n### %s\n\n' "$newest"; [ -n "$entry" ] && printf '%s\n' "$entry"; } >> "$digest"

tmp=$(mktemp) || die "mktemp failed"
sed "s|Captured through:\*\* \`$marker\`|Captured through:** \`$newest\`|" "$digest" > "$tmp" \
  && mv "$tmp" "$digest" || die "failed to advance marker"

cd "$(dirname "$digest")" || die "cannot cd to digest directory"
msg="checkpoint(digest): consolidate $n turn(s) through $newest [$model]"
if ! git commit -q -m "$msg" -- "$(basename "$digest")" 2>/dev/null; then
  # One retry: the plans worktree is shared, so .git/index.lock contention is expected rather
  # than exceptional. A failed commit here is a silent non-save, hence the retry and the loud
  # exit — never a warning that reads like success.
  sleep 3
  git commit -q -m "$msg" -- "$(basename "$digest")" \
    || die "commit failed twice; digest is modified but UNCOMMITTED — content is on disk, commit it manually" 8
fi
git diff --quiet -- "$(basename "$digest")" \
  || die "digest still dirty after commit — verify manually" 9

printf '%s: consolidated %s turn(s), marker -> %s, model %s\n' "${0##*/}" "$n" "$newest" "$model" >&2
