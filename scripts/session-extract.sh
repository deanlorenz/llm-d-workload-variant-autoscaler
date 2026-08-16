#!/usr/bin/env bash
# Extract genuine user turns from a Claude Code session transcript.
#
# Why this exists: compaction replaces a session's working context, so anything
# the summarizer dropped is gone from the running session while remaining on
# disk in the transcript. Distilling from live context cannot recover it; only
# reading the transcript can. This script does the mechanical half — pulling the
# highest-value, least-reconstructible content (the user's own words) out of a
# multi-megabyte JSONL — so a checkpoint tick can diff it against a working
# document and append what was never captured.
#
# Two record shapes carry what the user said, and both are required:
#   * type "user" with plain-string content — a normal turn. (Tool results are also
#     type "user" but carry structured content blocks, so they are skipped.)
#   * type "queue-operation" with operation "enqueue" — a MID-TURN message, sent
#     while a turn was still running. These never appear as "user" records, so a
#     filter that only looks at type "user" drops them silently. That was a real
#     defect: three of Dean's rulings arrived this way and went uncaptured, and the
#     empty result was indistinguishable from "nothing was said".
# Mid-turn entries are marked "(mid-turn)" in the output.
#
# Usage:
#   session-extract.sh [--since <ISO8601>] [--file <transcript.jsonl>]
#   session-extract.sh --list [--project-dir <dir>]
#
#   --since       only turns strictly after this timestamp (the digest's
#                 "captured through" marker); omit for all turns.
#                 TRANSCRIPT TIMESTAMPS ARE UTC — a local-time bound silently
#                 returns too much or nothing at all. Use `date -u`.
#   --file        explicit transcript; default is the most recently modified
#                 transcript for the current working directory's project
#   --list        list available transcripts, newest first, with their first
#                 prompt — for identifying which UUID was which session
#
# Exits non-zero and explains itself on stderr rather than printing nothing:
# an empty result and a broken invocation must not look alike.

set -uo pipefail

since=""
file=""
project_dir=""
do_list=0
count_only=0

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --since)       since="${2:-}"; [ -n "$since" ] || die "--since needs a value"; shift 2 ;;
    --file)        file="${2:-}";  [ -n "$file" ]  || die "--file needs a value";  shift 2 ;;
    --project-dir) project_dir="${2:-}"; [ -n "$project_dir" ] || die "--project-dir needs a value"; shift 2 ;;
    --list)        do_list=1; shift ;;
    --count)       count_only=1; shift ;;
    -h|--help)     sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)             die "unknown argument: $1" ;;
  esac
done

command -v jq >/dev/null 2>&1 || die "jq is required"

# Kill-switch (2026-08-11). The per-session checkpoint tick is retired: it cost on the
# order of 9M input tokens in one day for 9 useful digest updates, because every firing
# was a separate request that re-uploaded the entire session. Cron jobs are session-scoped
# and cannot be cancelled from outside the session that made them, so this is the only way
# to reach a tick armed by an older session — the message below is read by that session.
# scripts/session-snapshot.sh sets SESSION_EXTRACT_ALLOW=1, because the model-free loop is
# the replacement, not the thing being disabled.
here_dir="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$here_dir/../session/.tick-disabled" ] && [ "${SESSION_EXTRACT_ALLOW:-}" != "1" ]; then
  cat >&2 <<'DISABLED'
session-extract.sh: DISABLED — the scheduled checkpoint tick is retired.

If you are a session executing a "CHECKPOINT TICK" prompt:
  1. CANCEL that recurring cron job now (CronDelete) — it is yours, nobody else can.
  2. Do NOT retry, and do NOT report "nothing new": nothing was checked.
  3. Report that the tick is disabled and that you cancelled the job.

Capture now runs without a model, in scripts/session-snapshot.sh. See
session/CONVENTIONS.md § Checkpoint capture.
DISABLED
  exit 3
fi

# Claude Code stores transcripts under ~/.claude/projects/<cwd with / replaced by ->
if [ -z "$project_dir" ]; then
  project_dir="$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"
fi

if [ "$do_list" -eq 1 ]; then
  [ -d "$project_dir" ] || die "no project directory: $project_dir"
  found=0
  while IFS= read -r f; do
    found=1
    first=$(head -400 "$f" 2>/dev/null \
      | jq -r 'select(.type=="user") | select(.message.content|type=="string") | .message.content' 2>/dev/null \
      | grep -v '^<' | head -1 | cut -c1-90)
    printf '%s  %6s  %s\n' \
      "$(date -r "$f" '+%Y-%m-%d %H:%M')" \
      "$(du -h "$f" | cut -f1)" \
      "${first:-(no plain-text prompt found)}"
    printf '            %s\n' "$(basename "$f")"
  done < <(ls -t "$project_dir"/*.jsonl 2>/dev/null)
  [ "$found" -eq 1 ] || die "no transcripts in $project_dir"
  exit 0
fi

if [ -z "$file" ]; then
  [ -d "$project_dir" ] || die "no project directory: $project_dir"
  file=$(ls -t "$project_dir"/*.jsonl 2>/dev/null | head -1)
  [ -n "$file" ] || die "no transcripts in $project_dir"
  # newest-by-mtime is a convenience for interactive use and is WRONG whenever two
  # sessions share a project directory: the other session's file becomes newest the
  # moment it writes, and this silently starts extracting its turns instead of yours.
  # Any automated caller must pin --file.
  if [ "$(ls -t "$project_dir"/*.jsonl 2>/dev/null | wc -l)" -gt 1 ]; then
    printf '%s: WARNING resolved by mtime among %s transcripts — pin --file for automation\n' \
      "${0##*/}" "$(ls "$project_dir"/*.jsonl 2>/dev/null | wc -l)" >&2
  fi
fi
[ -r "$file" ] || die "cannot read transcript: $file"

printf 'transcript: %s\n' "$file" >&2
[ -n "$since" ] && printf 'since: %s\n' "$since" >&2

out=$(jq -r --arg since "$since" '
  # Strip NUL bytes from the text before anything downstream sees them. Bash command
  # substitution ($(...)) cannot represent a NUL byte -- it silently truncates the
  # captured string at the first one, non-deterministically (a repro attempt saw 0 or
  # all 124 heading matches for the identical input across different runs, timing-
  # sensitive). A transcript with any binary tool-result content embedded (an image
  # is the likely source) can carry NUL bytes in an otherwise-normal turn message
  # field, and this scripts own output is captured via $(...) by every caller
  # (session-snapshot.sh pass()). Sanitize here, once, at the source, rather than in
  # every consumer. Found 2026-08-16 (plan__session-snapshot-nul-byte-content-corruption.md);
  # a live re-check that day found the specific cited transcript no longer carrying
  # any NUL bytes in message.content, so the mechanism is confirmed real (Bash
  # command substitution genuinely truncates on NUL) but not re-confirmed as the
  # actual cause of that report -- keeping the fix regardless, since it is a real,
  # zero-cost hazard to close. No apostrophes in this comment block -- it lives
  # inside a single-quoted bash string passed to jq.
  def strip_nul: gsub("\u0000"; "");
  # Two record shapes carry what the user actually said, and missing the second one
  # silently drops whole decisions:
  #   type=="user" with a plain-string content  -> a normal turn
  #     (tool results are also type "user" but carry structured content blocks)
  #   type=="queue-operation", operation=="enqueue" -> a MID-TURN message, sent while a
  #     turn was still running. It never appears as a "user" record at all.
  # Guard .message with a type test: some records carry a string there and an
  # unguarded .message.content aborts the whole jq run.
    if .type=="user"
       and ((.message|type)=="object")
       and ((.message.content|type)=="string")
    then {ts: .timestamp, mid: false, text: (.message.content | strip_nul)}
    elif .type=="queue-operation" and .operation=="enqueue"
         and ((.content|type)=="string")   # some carry a null content; without this
                                           # guard startswith() below aborts the run
    then {ts: .timestamp, mid: true,  text: (.content | strip_nul)}
    else empty
    end
  # "dequeue" and "remove" also carry content: dequeue would duplicate the enqueue,
  # and remove is a message that was cancelled and therefore never said.
  | select(($since == "") or (.ts > $since))
  # A scheduled checkpoint prompt is itself one of these records (and is enqueued when
  # it fires mid-turn), so without this every tick re-reads its own instructions.
  | select(.text | startswith("CHECKPOINT TICK") | not)
' "$file" \
  | jq -s -r '
  # A queued message that drains AFTER the turn ends is recorded twice — once as the
  # enqueue, once as the resulting user turn ~30 s later. One injected mid-turn is
  # recorded only as the enqueue. So deduplicate on the text, keeping the earliest
  # occurrence, and restore chronological order (group_by sorts).
  # Two-stage on purpose: the stream above filters the multi-megabyte transcript, and
  # only the handful of surviving records is slurped here.
    group_by(.text) | map(min_by(.ts)) | sort_by(.ts) | .[]
  | "## " + .ts + (if .mid then "  (mid-turn)" else "" end) + "\n" + .text + "\n"
') || die "jq failed on $file" 3

n=$(printf '%s' "$out" | grep -c '^## ' || true)

# --count prints only the number, so a checkpoint tick can ask "is there anything new?"
# without pulling the text into its context. A no-op tick then costs almost nothing.
if [ "$count_only" -eq 1 ]; then
  printf '%s\n' "$n"
  exit 0
fi

printf '%s\n' "$out"
printf 'turns: %s\n' "$n" >&2
