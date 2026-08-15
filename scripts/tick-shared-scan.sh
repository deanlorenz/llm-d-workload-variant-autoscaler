#!/usr/bin/env bash
# Shared Tier-2 consolidation: one loop for all live sessions instead of one per session.
# Design: planning/atomic-step-protocol-design-addendum-2.md (+ addendum-7 for the guards).
# Tier-1 (session-snapshot.sh) stays per-session -- it is already free. Only Tier-2 centralizes.
#
# Owned by the sync session, started detached. Pausing when no sync session is active is fine;
# the next one restarts it. No daemon, no systemd unit.
#
# Scans every (transcript -> digest) pair in session/.tier2-registry each pass; no liveness
# protocol, since Tier-1's count-check makes an idle session ~free to check.
#
# Usage:
#   tick-shared-scan.sh --origin-pid <pid> [--interval <seconds>] [--retire-days <n>]
#                        [--daily-cap <tokens>]
#   tick-shared-scan.sh --once [--retire-days <n>] [--daily-cap <tokens>]
#
#   --origin-pid    pid of the Claude session that started this loop. Required unless --once.
#                    Checked with `kill -0` each pass; when it is gone, run one final scan and exit.
#   --interval      seconds between passes (default 300)
#   --retire-days   transcript mtime staleness before retirement (default 7)
#   --daily-cap     combined token cap per UTC day across all sessions (default 50000)
#   --once          single pass then exit, for testing. Skips --origin-pid and the dedup guards.
#
# Exit codes: non-zero for a real failure; 0 for a quiet pass and for a redundant instance
# standing down. A crash must never look like a quiet pass.
#
# Linux only: uses `date -r <file>` (GNU coreutils) for mtime. BSD/macOS `date -r` takes seconds.

set -uo pipefail

once=0
interval=300
retire_days=7
daily_cap=50000
origin_pid=""

here="$(cd "$(dirname "$0")" && pwd)"
plans_dir="$(cd "$here/.." && pwd)"
consolidate="$here/tick-consolidate.sh"
registry="$plans_dir/session/.tier2-registry"
retired_dir="$plans_dir/session/.retired"
usage_log="$plans_dir/session/.tier2-usage.log"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --once)                 once=1; shift ;;
    --interval)             interval="${2:-}";           [ -n "$interval" ]           || die "--interval needs a value";           shift 2 ;;
    --retire-days)          retire_days="${2:-}";         [ -n "$retire_days" ]        || die "--retire-days needs a value";        shift 2 ;;
    --daily-cap)            daily_cap="${2:-}";           [ -n "$daily_cap" ]          || die "--daily-cap needs a value";          shift 2 ;;
    --origin-pid)           origin_pid="${2:-}";          [ -n "$origin_pid" ]         || die "--origin-pid needs a value";         shift 2 ;;
    -h|--help)              sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)                      die "unknown argument: $1" ;;
  esac
done

[ -x "$consolidate" ] || die "cannot execute $consolidate"
case "$interval" in ''|*[!0-9]*) die "--interval must be a whole number of seconds" ;; esac
case "$retire_days" in ''|*[!0-9]*) die "--retire-days must be a whole number" ;; esac
case "$daily_cap" in ''|*[!0-9]*) die "--daily-cap must be a whole number of tokens" ;; esac
if [ "$once" -ne 1 ]; then
  [ -n "$origin_pid" ] || die "--origin-pid is required (unless --once) -- see -h"
  case "$origin_pid" in ''|*[!0-9]*) die "--origin-pid must be a numeric pid" ;; esac
fi

mkdir -p "$retired_dir" || die "cannot create $retired_dir"
touch "$usage_log" || die "cannot write $usage_log"

# Single-instance guards; see planning/atomic-step-protocol-design-addendum-7.md.
# Guard 1 (mkdir, atomic): are two instances starting at the same instant?
# Guard 2 (pgrep): is a fully-started scanner already running?
# Neither covers the other's window. Held only during startup, removed inline.
if [ "$once" -ne 1 ]; then
  dedup_dir="${TMPDIR:-/tmp}/tick-shared-scan.dedup.$origin_pid"

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
  if pgrep -f "tick-shared-scan[.]sh .*--origin-pid $origin_pid" 2>/dev/null | grep -qv "^$$\$"; then
    printf '%s: another instance already running for --origin-pid %s -- exiting quietly\n' \
      "${0##*/}" "$origin_pid" >&2
    rmdir "$dedup_dir" 2>/dev/null
    exit 0
  fi
  rmdir "$dedup_dir" 2>/dev/null   # startup done; guard no longer needed
fi

# Stable, filesystem-safe key for a transcript path; used as the retirement marker filename.
marker_key() {
  printf '%s' "$1" | sha256sum | awk '{print $1}'
}

# Sum today's (UTC) token usage from the ledger. Format per line: "<ISO8601Z> <tokens>".
tokens_used_today() {
  local today
  today="$(date -u +%F)"
  awk -v d="$today" '$1 ~ "^"d { sum += $2 } END { print sum+0 }' "$usage_log" 2>/dev/null
}

pass() {
  local budget_used
  budget_used=$(tokens_used_today)
  if [ "$budget_used" -ge "$daily_cap" ]; then
    printf '%s: daily cap reached (%s/%s tokens) -- skipping this pass\n' \
      "${0##*/}" "$budget_used" "$daily_cap" >&2
    return 0
  fi

  [ -f "$registry" ] || { printf '%s: no registry yet (%s) -- nothing to scan\n' "${0##*/}" "$registry" >&2; return 0; }

  # Keep only the latest registration per transcript, in case of stragglers.
  local entries
  entries=$(awk -F'\t' '{ latest[$2]=$0 } END { for (k in latest) print latest[k] }' "$registry")

  [ -n "$entries" ] || { printf '%s: registry is empty -- nothing to scan\n' "${0##*/}" >&2; return 0; }

  local tfile dfile key now_epoch mtime_epoch age_days
  now_epoch=$(date -u +%s)

  while IFS=$'\t' read -r _ts tfile dfile; do
    if [ -z "$tfile" ] || [ -z "$dfile" ]; then continue; fi
    key=$(marker_key "$tfile")

    if [ -f "$tfile" ]; then
      mtime_epoch=$(date -r "$tfile" +%s 2>/dev/null || echo 0)
    else
      # Transcript gone (pruned/renamed): retire it. The read below fails harmlessly first.
      mtime_epoch=0
    fi
    age_days=$(( (now_epoch - mtime_epoch) / 86400 ))

    if [ -f "$retired_dir/$key" ]; then
      if [ "$age_days" -lt "$retire_days" ]; then
        rm -f "$retired_dir/$key"   # woke back up; rejoin the pool
      else
        continue                    # retired and still stale
      fi
    fi

    [ -r "$tfile" ] || continue
    [ -r "$dfile" ] || { printf '%s: registered digest unreadable, skipping: %s\n' "${0##*/}" "$dfile" >&2; continue; }

    budget_used=$(tokens_used_today)
    if [ "$budget_used" -ge "$daily_cap" ]; then
      printf '%s: daily cap reached mid-scan (%s/%s tokens) -- stopping this pass\n' \
        "${0##*/}" "$budget_used" "$daily_cap" >&2
      return 0
    fi

    local call_tokens rc call_out
    call_out=$("$consolidate" --digest "$dfile" --file "$tfile" 2>&1)
    rc=$?

    # Charge the budget for every outcome except the explicit no-op: rc 0 covers both "nothing
    # new" (no model call) and a real call, so only its stderr text distinguishes them. 488 is a
    # measured per-call average, a placeholder until real usage is plumbed through.
    if printf '%s' "$call_out" | grep -q 'nothing new since'; then
      : # no model call; charge nothing
    else
      call_tokens="${TICK_ASSUMED_TOKENS_PER_CALL:-488}"
      printf '%s %s\n' "$(date -u +%FT%TZ)" "$call_tokens" >> "$usage_log"
    fi

    if [ "$rc" -eq 0 ]; then
      printf '%s: %s -> %s: %s\n' "${0##*/}" "$(basename "$tfile")" "$(basename "$dfile")" \
        "$(printf '%s' "$call_out" | tail -1)" >&2
    else
      printf '%s: consolidate failed rc=%s for %s: %s\n' \
        "${0##*/}" "$rc" "$(basename "$tfile")" "$(printf '%s' "$call_out" | tail -1)" >&2
      # Do not die: one bad transcript must not stop the scan of every other session.
    fi

    if [ "$age_days" -ge "$retire_days" ]; then
      touch "$retired_dir/$key" || printf '%s: could not write retirement marker %s\n' "${0##*/}" "$key" >&2
    fi
  done <<EOF
$entries
EOF
}

if [ "$once" -eq 1 ]; then
  pass
  exit 0
fi

while true; do
  # Origin gone: run one final scan, THEN exit. Never skip it.
  if ! kill -0 "$origin_pid" 2>/dev/null; then
    printf '%s: origin pid %s is gone -- final scan, then exit\n' "${0##*/}" "$origin_pid" >&2
    pass
    exit 0
  fi
  pass
  sleep "$interval"
done
