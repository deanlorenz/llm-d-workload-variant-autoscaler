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
#   session-snapshot.sh --out <file> --origin-pid <pid> [--interval <seconds>] [--once]
#
#   --out          raw sidecar to append to (created if absent)
#   --origin-pid   pid of the Claude session that started this loop. Required unless --once.
#                  Checked with `kill -0` each pass; when it is gone, run one final pass and exit.
#   --interval     seconds between passes (default 120)
#   --once         single pass then exit, for testing. Skips --origin-pid and the dedup guards.
#
# Linux only: uses `date -r <file>` (GNU coreutils) for mtime. BSD/macOS `date -r` takes seconds.

set -uo pipefail

out=""
interval=120
once=0
tfile=""
digest=""
consolidate_every=0
origin_pid=""
passes=0   # deliberately not "pass": that is the function name below

here="$(cd "$(dirname "$0")" && pwd)"
extract="$here/session-extract.sh"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --out)         out="${2:-}";         [ -n "$out" ]         || die "--out needs a value";         shift 2 ;;
    --interval)    interval="${2:-}";    [ -n "$interval" ]    || die "--interval needs a value";    shift 2 ;;
    --file)        tfile="${2:-}";       [ -n "$tfile" ]       || die "--file needs a value";        shift 2 ;;
    --digest)      digest="${2:-}";      [ -n "$digest" ]      || die "--digest needs a value";      shift 2 ;;
    --origin-pid)  origin_pid="${2:-}";  [ -n "$origin_pid" ]  || die "--origin-pid needs a value";  shift 2 ;;
    --consolidate-every)
                consolidate_every="${2:-}"; [ -n "$consolidate_every" ] || die "--consolidate-every needs a value"; shift 2 ;;
    --once)     once=1; shift ;;
    -h|--help)  sed -n '2,31p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)          die "unknown argument: $1" ;;
  esac
done

[ -n "$out" ] || die "--out is required"
[ -x "$extract" ] || die "cannot execute $extract"
case "$interval" in ''|*[!0-9]*) die "--interval must be a whole number of seconds" ;; esac
if [ "$once" -ne 1 ]; then
  [ -n "$origin_pid" ] || die "--origin-pid is required (unless --once) -- see -h"
  case "$origin_pid" in ''|*[!0-9]*) die "--origin-pid must be a numeric pid" ;; esac
fi

mark="$(dirname "$out")/.$(basename "$out").mark"
log="$(dirname "$out")/.$(basename "$out").log"
mkdir -p "$(dirname "$out")" || die "cannot create $(dirname "$out")"

# Single-instance guards; see planning/atomic-step-protocol-design-addendum-7.md.
# Guard 1 (mkdir, atomic): are two instances starting at the same instant?
# Guard 2 (pgrep): is a fully-started watcher already running?
# Neither covers the other's window. Held only during startup, removed inline.
if [ "$once" -ne 1 ]; then
  dedup_dir="${TMPDIR:-/tmp}/session-snapshot.dedup.$origin_pid"

  # Reclaim a guard abandoned by a process that died before its own rmdir (SIGKILL, OOM, sleep).
  # 1 week: far longer than any startup, so age alone is a safe abandonment signal.
  if [ -d "$dedup_dir" ] && [ "$(( $(date +%s) - $(date -r "$dedup_dir" +%s) ))" -gt 604800 ]; then
    rmdir "$dedup_dir" 2>/dev/null
  fi

  mkdir "$dedup_dir" 2>/dev/null || {
    printf '%s: another instance starting for --origin-pid %s -- exiting quietly\n' \
      "${0##*/}" "$origin_pid" >&2
    exit 0
  }

  # $$ must be excluded: pgrep -f matches this script's own argv, which contains the pattern.
  if pgrep -f "session-snapshot[.]sh .*--origin-pid $origin_pid" 2>/dev/null | grep -qv "^$$\$"; then
    printf '%s: another instance already running for --origin-pid %s -- exiting quietly\n' \
      "${0##*/}" "$origin_pid" >&2
    rmdir "$dedup_dir" 2>/dev/null
    exit 0
  fi
  rmdir "$dedup_dir" 2>/dev/null   # commit point: proceeding to become the watcher
fi

# Register (transcript -> digest) for the shared Tier-2 scanner; only this loop knows the pairing.
# Keyed by transcript so a restart overwrites. Best-effort: must never block Tier-1.
if [ -n "$tfile" ] && [ -n "$digest" ]; then
  registry="$here/../session/.tier2-registry"
  tmp_reg=$(mktemp "$(dirname "$registry").XXXXXX" 2>/dev/null) && {
    { [ -f "$registry" ] && grep -vF "	$tfile	" "$registry"; true; } > "$tmp_reg"
    printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$tfile" "$digest" >> "$tmp_reg"
    mv "$tmp_reg" "$registry" 2>/dev/null || rm -f "$tmp_reg"
  }
fi

# Unpinned, the extractor picks the newest transcript by mtime -- a sibling session in the same
# project directory then silently becomes the one mirrored here.
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

  set -- ${tfile:+--file "$tfile"} ${since:+--since "$since"}
  # Keep stderr: a silent extractor failure is indistinguishable from "no new turns".
  # SESSION_EXTRACT_ALLOW opts past the retired tick's kill-switch; no model is involved.
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

  # Advance to the newest captured timestamp, not "now", so a turn landing mid-pass is not skipped.
  printf '%s\n' "$new" | grep '^## ' | tail -1 \
    | sed 's/^## //; s/  *(mid-turn)$//' > "$mark"
}

# Tier 2: cheap model call, driven off accumulated passes rather than a clock.
consolidate() {
  [ "$consolidate_every" -gt 0 ] || return 0
  [ -n "$digest" ] || return 0
  [ $(( passes % consolidate_every )) -eq 0 ] || return 0

  local rc
  "$here/tick-consolidate.sh" --digest "$digest" ${tfile:+--file "$tfile"} >>"$log" 2>&1
  rc=$?
  # Never die here: a Tier-2 failure must not stop free Tier-1 capture. Log so it is not silent.
  [ "$rc" -eq 0 ] || printf '[%s] consolidate failed rc=%s\n' "$(date -u +%FT%TZ)" "$rc" >> "$log"
  return 0
}

if [ "$once" -eq 1 ]; then
  passes=1
  pass
  consolidate
  exit 0
fi

while true; do
  # Origin gone: capture what landed since the last pass, THEN exit. Capturing on session death
  # is this script's purpose, so the final pass must never be skipped.
  if ! kill -0 "$origin_pid" 2>/dev/null; then
    printf '[%s] origin pid %s is gone -- running final pass, then self-exiting (stateless by design, not a crash)\n' \
      "$(date -u +%FT%TZ)" "$origin_pid" >> "$log"
    pass
    consolidate
    exit 0
  fi
  passes=$(( passes + 1 ))
  pass
  consolidate
  sleep "$interval"
done
