#!/usr/bin/env bash
# Build a machine-optimized index of live/recent sessions from their status-file identity
# blocks. See planning/atomic-step-protocol-design-addendum-3.md § Session self-declared
# identity + sync-maintained live index.
#
# Purpose (not mutually exclusive):
#   1. Resolving a handoff's `to:` field (role+task -> a concrete session to address).
#   2. Detecting stale/dead sessions: an absolute-age signal (mtime, default 7 days --
#      reuses the same threshold as tick-shared-scan.sh's retirement, one number instead of
#      two to keep in sync) AND a sharper peer-comparison signal -- if most other sessions
#      have checked in more recently than this one, that is evidence of a stuck session NOW,
#      well before the absolute-age threshold would ever flag it.
#   3. A reference for "what's the state of things" -- not meant to be read raw by Dean;
#      meant to be read by a session (or by Dean asking a session) and summarized.
#
# Ownership: the sync session runs this as part of its Tier-2 work (same rationale as
# tick-shared-scan.sh -- shell + a cheap/no model step, not run inside any one session's
# context). It is a read-only scan; nothing here writes to any status file.
#
# Identity block format (session/CONVENTIONS.md, added 2026-08-13), at the top of
# session/status/<branch>.md:
#   name: <value>
#   id: <value>
#   role: <value>
#   branch: <value>
#   worktree: <value>
#   owned_doc: <value>
#   task: <value>
#   status_file: <value>
# followed by the pre-existing last_update/state/current_step/... fields. Not every existing
# status file has this yet (added after many were already in use) -- a file with no
# identity block still appears in the index, with those fields empty, rather than being
# skipped or erroring.
#
# Usage:
#   tick-live-index.sh [--status-dir <dir>] [--stale-days <n>] [--format table|json]
#
#   --status-dir   directory of session/status/*.md files (default: session/status
#                   relative to this script's plans/ root)
#   --stale-days   absolute-age threshold in days for the age-based stale flag (default 7,
#                   matching tick-shared-scan.sh's --retire-days)
#   --format       "table" (human-scannable, still not the primary consumer) or "json"
#                   (default; one object per session, for a session to parse)
#
# Peer-comparison staleness is always computed regardless of --format: a session is flagged
# peer_stale=true if its last_update is older than the MEDIAN last_update across all other
# sessions by more than --stale-days/4 (a quarter of the absolute threshold -- sharper,
# deliberately not configurable separately per the design note that one number should
# anchor both signals rather than drift apart).

set -uo pipefail

status_dir=""
stale_days=7
format="json"

here="$(cd "$(dirname "$0")" && pwd)"
plans_dir="$(cd "$here/.." && pwd)"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --status-dir) status_dir="${2:-}"; [ -n "$status_dir" ] || die "--status-dir needs a value"; shift 2 ;;
    --stale-days) stale_days="${2:-}"; [ -n "$stale_days" ] || die "--stale-days needs a value"; shift 2 ;;
    --format)     format="${2:-}";     [ -n "$format" ]     || die "--format needs a value";     shift 2 ;;
    -h|--help)    sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die "unknown argument: $1" ;;
  esac
done

[ -n "$status_dir" ] || status_dir="$plans_dir/session/status"
case "$stale_days" in ''|*[!0-9]*) die "--stale-days must be a whole number" ;; esac
case "$format" in table|json) ;; *) die "--format must be table or json" ;; esac

[ -d "$status_dir" ] || die "no status directory: $status_dir"

command -v jq >/dev/null 2>&1 || die "jq is required"

now_epoch=$(date -u +%s)
stale_secs=$(( stale_days * 86400 ))

# One JSON object per status file, built with awk (field extraction) + jq (assembly), so a
# malformed or half-written file degrades to empty fields rather than aborting the whole scan.
records="[]"
found=0

for f in "$status_dir"/*.md; do
  [ -e "$f" ] || continue
  found=1

  # Identity block fields: simple "key: value" lines, only from the top of the file, stopping
  # at the first blank line or heading (so a "task:" mentioned later in freeform prose is
  # never mistaken for the identity field).
  block=$(awk '
    /^$/ { exit }
    /^##/ { exit }
    /^[a-z_]+:/ { print; next }
  ' "$f")

  get() {
    printf '%s\n' "$block" | awk -v k="$1" '
      index($0, k ": ") == 1 { print substr($0, length(k) + 3); exit }
    '
  }

  name=$(get name); id=$(get id); role=$(get role); branch=$(get branch)
  worktree=$(get worktree); owned_doc=$(get owned_doc); task=$(get task)
  status_file_field=$(get status_file)

  mtime_epoch=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
  age_secs=$(( now_epoch - mtime_epoch ))
  age_stale="false"
  [ "$age_secs" -gt "$stale_secs" ] && age_stale="true"

  rec=$(jq -n \
    --arg path "$f" \
    --arg name "$name" --arg id "$id" --arg role "$role" --arg branch "$branch" \
    --arg worktree "$worktree" --arg owned_doc "$owned_doc" --arg task "$task" \
    --arg status_file "$status_file_field" \
    --arg mtime_epoch "$mtime_epoch" --argjson age_stale "$age_stale" \
    '{path: $path, name: $name, id: $id, role: $role, branch: $branch, worktree: $worktree,
      owned_doc: $owned_doc, task: $task, status_file: $status_file,
      mtime_epoch: ($mtime_epoch | tonumber), age_stale: $age_stale}')

  records=$(printf '%s' "$records" | jq --argjson r "$rec" '. + [$r]')
done

[ "$found" -eq 1 ] || die "no status files in $status_dir"

# Peer-comparison staleness: median mtime across all sessions, then flag anything older than
# that median by more than a quarter of the absolute threshold. Computed over the whole set
# in one jq pass -- sharper and faster than the absolute-age signal, per the design note that
# a session out of step with an actively-checking-in cohort is evidence of trouble now.
quarter_secs=$(( stale_secs / 4 ))
records=$(printf '%s' "$records" | jq --argjson q "$quarter_secs" '
  (map(.mtime_epoch) | sort) as $sorted
  | ($sorted | length) as $n
  | (if $n == 0 then 0
     elif $n % 2 == 1 then $sorted[($n-1)/2]
     else ($sorted[$n/2 - 1] + $sorted[$n/2]) / 2
     end) as $median
  | map(. + {peer_stale: (($median - .mtime_epoch) > $q)})
')

if [ "$format" = "json" ]; then
  printf '%s\n' "$records" | jq '.'
else
  printf '%-28s %-10s %-24s %-30s %-6s %-6s\n' "NAME" "ROLE" "BRANCH" "TASK" "AGE!" "PEER!"
  printf '%s' "$records" | jq -r '
    .[] | [
      (.name // "(none)"), (.role // "(none)"), (.branch // "(none)"),
      ((.task // "(none)") | .[0:30]),
      (if .age_stale then "yes" else "" end),
      (if .peer_stale then "yes" else "" end)
    ] | @tsv' | awk -F'\t' '{printf "%-28s %-10s %-24s %-30s %-6s %-6s\n", $1, $2, $3, $4, $5, $6}'
fi
