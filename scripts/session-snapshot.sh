#!/usr/bin/env bash
# Panic-recovery writer. Goal (a) of session checkpointing: get the user's own words
# onto disk in a small, pre-extracted form, continuously, with ZERO involvement of the
# session — no model, no context cost, no output, no commits.
#
# This is deliberately separate from the checkpoint tick, which is goal (b): judging
# that the session is missing something and getting it back in front of the session.
# (b) needs a model and therefore costs context; (a) needs none, so it should be free
# and always on.
#
# Run it detached, once per session:
#   nohup ./scripts/session-snapshot.sh --out session/digests/<topic>.raw.md &
#
# Every interval it appends turns newer than its own marker and advances the marker.
# It keeps a marker separate from the digest's "Captured through", because the tick
# advances that one and the two must not race.
#
# It does NOT commit. A crash or a sleeping machine does not lose a written file, and
# committing on a loop would hammer the shared git index where a failed commit is a
# silent non-save. Durability by commit is the tick's business, not this loop's.
#
# Usage:
#   session-snapshot.sh --out <file> [--interval <seconds>] [--once]
#
#   --out        raw sidecar to append to (created if absent)
#   --interval   seconds between passes (default 120 — cheap, it is pure local CPU)
#   --once       single pass then exit, for testing

set -uo pipefail

out=""
interval=120
once=0
tfile=""

here="$(cd "$(dirname "$0")" && pwd)"
extract="$here/session-extract.sh"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --out)      out="${2:-}";      [ -n "$out" ]      || die "--out needs a value";      shift 2 ;;
    --interval) interval="${2:-}"; [ -n "$interval" ] || die "--interval needs a value"; shift 2 ;;
    --file)     tfile="${2:-}";    [ -n "$tfile" ]    || die "--file needs a value";     shift 2 ;;
    --once)     once=1; shift ;;
    -h|--help)  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)          die "unknown argument: $1" ;;
  esac
done

[ -n "$out" ] || die "--out is required"
[ -x "$extract" ] || die "cannot execute $extract"
case "$interval" in ''|*[!0-9]*) die "--interval must be a whole number of seconds" ;; esac

mark="$(dirname "$out")/.$(basename "$out").mark"
log="$(dirname "$out")/.$(basename "$out").log"
mkdir -p "$(dirname "$out")" || die "cannot create $(dirname "$out")"

# Pinning the transcript is strongly advised: session-extract.sh otherwise resolves it by
# mtime, and a second session sharing this project directory becomes "newest" as soon as it
# writes — at which point this loop starts mirroring the wrong conversation.
[ -n "$tfile" ] || printf '%s: WARNING no --file; transcript resolved by mtime each pass\n' \
  "${0##*/}" >&2

if [ ! -f "$out" ]; then
  {
    printf '# Raw session capture (panic recovery)\n\n'
    printf 'Appended continuously by `scripts/session-snapshot.sh`. Regenerable from the session\n'
    printf 'transcript, so it is a convenience rather than a source of truth: it exists so that\n'
    printf 'recovery after a crash is reading a small file instead of parsing a large one.\n\n'
    printf 'Not committed and not curated. The distilled, committed artifact is the digest\n'
    printf 'beside it.\n'
  } > "$out" || die "cannot write $out"
fi

pass() {
  local since="" new rc
  [ -f "$mark" ] && since="$(cat "$mark" 2>/dev/null)"

  # Never discard stderr: an extractor failure would otherwise look exactly like
  # "no new turns" and this loop would go quietly dead. It already did once, when a
  # queue-operation record with a null content aborted jq.
  set -- ${tfile:+--file "$tfile"} ${since:+--since "$since"}
  # This loop is the replacement for the retired tick, not a caller of it, so it opts past
  # the kill-switch. Gating happens here in shell: no model is involved at any point, which
  # is what makes an idle session cost exactly nothing.
  new="$(SESSION_EXTRACT_ALLOW=1 "$extract" "$@" 2>>"$log")"; rc=$?
  if [ "$rc" -ne 0 ]; then
    printf '[%s] extract failed rc=%s — see %s\n' "$(date -u +%FT%TZ)" "$rc" "$log" >> "$log"
    return 0
  fi

  # No new turns: touch nothing at all, so the file's mtime stays meaningful.
  printf '%s' "$new" | grep -q '^## ' || return 0

  {
    printf '\n---\n\n'
    printf '%s\n' "$new"
  } >> "$out"

  # Advance to the newest captured timestamp, not to "now": a turn landing during this
  # pass must still be picked up next time.
  printf '%s\n' "$new" | grep '^## ' | tail -1 \
    | sed 's/^## //; s/  *(mid-turn)$//' > "$mark"
}

if [ "$once" -eq 1 ]; then
  pass
  exit 0
fi

while true; do
  pass
  sleep "$interval"
done
