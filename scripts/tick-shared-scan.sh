#!/usr/bin/env bash
# Shared Tier-2 checkpoint consolidation across every live session, in one place instead of
# one loop per session. See planning/atomic-step-protocol-design-addendum-2.md.
#
# Motivation (Dean, 2026-08-13): "Can we have one tick for all live sessions? this is mostly
# shell work + autonomic model work (not running in the session's context)." Tier-1
# (session-snapshot.sh) is already free and stays per-session — there is no redundancy there
# worth removing. Only Tier-2 (the rare, cheap-model consolidation call) centralizes.
#
# Ownership: the sync session starts and monitors this loop (detached nohup, same pattern as
# per-session Tier-1). It is acceptable for it to pause when no sync session is active; the
# next one notices and restarts it. No standing daemon, no systemd unit.
#
# Single-instance guard: an flock on a dedicated lock file, held for the process's whole life
# (fd 9, opened once at startup, never closed). A second invocation -- a second sync session,
# or the same one restarted without checking first -- refuses the lock and exits 0 quietly, so
# it is always safe to call the start routine speculatively. Same pattern as
# scripts/sync-main-watch.sh, which hit exactly this race (2026-08-10 incident: a racy
# heartbeat-only "already running?" check let two live watchers run simultaneously undetected).
#
# Dead-man's-switch: exits once Main sync (the sync session that owns this loop, per the
# Ownership note above) is no longer active. Tied specifically to Main sync's own status file
# (session/status/main.md) rather than "any Claude process is running anywhere" --
# sync-main-watch.sh's `pgrep -x claude` check is intentionally NOT reused here: a process
# literally named `claude` carries no session identity, so that check would keep this loop
# alive because of an unrelated Claude session in a different project folder, which is a real
# over-broad-liveness bug, not a feature, for a loop whose whole reason to exist is serving
# Main sync's own work. Checked via main.md's `last_check` timestamp, which that session
# rewrites at its own heartbeat cadence; stale past --main-sync-timeout means Main sync is
# gone, so this loop should be too. This is a narrower fix than the broader open question of
# whether nohup/detachment is even needed for either watcher if Main sync could start reliably
# on its own -- that question is explicitly NOT addressed here (Dean, 2026-08-13: fix the
# narrow over-broad-scope bug now, defer the rest).
#
# Discovery: no liveness protocol. Every registered (transcript -> digest) pair from
# session/.tier2-registry is scanned every pass; Tier-1's own free count-check means a closed
# session with nothing new costs ~nothing to check.
#
# Retirement: a transcript whose mtime is stale for more than RETIRE_DAYS gets exactly one
# final consolidation sweep, then a marker file at session/.retired/<sha256(transcript path)>
# excludes it from future scans. If the transcript's mtime later moves past the threshold
# again (the session "woke up"), the marker is deleted on the next scan and it rejoins the
# pool -- no separate un-retire step.
#
# Token budget: a backstop against a bug, not a tight allowance. Each consolidation call's
# actual token usage is appended to session/.tier2-usage.log; before each new call this script
# sums today's entries and skips consolidation for the rest of the day if the sum already
# meets DAILY_CAP. A skipped session's raw sidecar keeps accumulating untouched -- nothing is
# lost, only delayed to the next day's pass.
#
# Usage:
#   tick-shared-scan.sh [--once] [--interval <seconds>] [--retire-days <n>] [--daily-cap <tokens>]
#                        [--main-sync-timeout <seconds>] [--no-main-sync-check] [--lock-file <path>]
#
#   --once                single pass then exit, for testing
#   --interval             seconds between passes (default 300 -- Tier-2 is meant to be rare)
#   --retire-days           mtime staleness threshold for retirement (default 7)
#   --daily-cap             combined token cap per UTC day across all sessions (default 50000)
#   --main-sync-timeout      seconds since Main sync's own status-file heartbeat before this
#                            loop treats Main sync as gone and self-exits (default 150 --
#                            matches sync-main-session-start.sh's own alive-threshold, ~2.5x
#                            that watcher's 60s poll interval)
#   --no-main-sync-check     skip the dead-man's-switch entirely (testing only -- a real
#                            deployment should never need this)
#   --lock-file              path for the single-instance flock (default
#                            /tmp/tick-shared-scan.lock)
#   --main-status            path to Main sync's status file, checked by the dead-man's-switch
#                            (default plans/session/status/main.md -- override for testing)
#
# Exits non-zero and explains itself on stderr for a real failure. A quiet pass with nothing
# to do exits 0 with a one-line note -- that must never look like a crash, and a crash must
# never look like a quiet pass. A redundant instance refusing the lock also exits 0 -- that is
# the intended outcome of calling the start routine speculatively, not a failure.

set -uo pipefail

once=0
interval=300
retire_days=7
daily_cap=50000
main_sync_timeout=150
check_main_sync=1
lock_file="/tmp/tick-shared-scan.lock"

here="$(cd "$(dirname "$0")" && pwd)"
plans_dir="$(cd "$here/.." && pwd)"
consolidate="$here/tick-consolidate.sh"
registry="$plans_dir/session/.tier2-registry"
retired_dir="$plans_dir/session/.retired"
usage_log="$plans_dir/session/.tier2-usage.log"
main_status="$plans_dir/session/status/main.md"

die() { printf '%s: %s\n' "${0##*/}" "$1" >&2; exit "${2:-2}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --once)                 once=1; shift ;;
    --interval)             interval="${2:-}";           [ -n "$interval" ]           || die "--interval needs a value";           shift 2 ;;
    --retire-days)          retire_days="${2:-}";         [ -n "$retire_days" ]        || die "--retire-days needs a value";        shift 2 ;;
    --daily-cap)            daily_cap="${2:-}";           [ -n "$daily_cap" ]          || die "--daily-cap needs a value";          shift 2 ;;
    --main-sync-timeout)    main_sync_timeout="${2:-}";   [ -n "$main_sync_timeout" ]  || die "--main-sync-timeout needs a value";  shift 2 ;;
    --no-main-sync-check)   check_main_sync=0; shift ;;
    --lock-file)            lock_file="${2:-}";           [ -n "$lock_file" ]          || die "--lock-file needs a value";          shift 2 ;;
    --main-status)          main_status="${2:-}";         [ -n "$main_status" ]        || die "--main-status needs a value";        shift 2 ;;
    -h|--help)              sed -n '2,73p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)                      die "unknown argument: $1" ;;
  esac
done

[ -x "$consolidate" ] || die "cannot execute $consolidate"
case "$interval" in ''|*[!0-9]*) die "--interval must be a whole number of seconds" ;; esac
case "$retire_days" in ''|*[!0-9]*) die "--retire-days must be a whole number" ;; esac
case "$daily_cap" in ''|*[!0-9]*) die "--daily-cap must be a whole number of tokens" ;; esac
case "$main_sync_timeout" in ''|*[!0-9]*) die "--main-sync-timeout must be a whole number of seconds" ;; esac

mkdir -p "$retired_dir" || die "cannot create $retired_dir"
touch "$usage_log" || die "cannot write $usage_log"

# Single-instance guard. Held for this process's entire life (fd 9 opened once, never
# explicitly closed -- the kernel releases it when the process exits, by crash or by design).
# A held lock means a live instance already exists; refuse quietly rather than race it, per
# the sync-main-watch.sh precedent (2026-08-10 incident).
exec 9>"$lock_file" || die "cannot open lock file: $lock_file"
if ! flock -n 9; then
  printf '%s: another instance already holds %s -- exiting quietly, this is expected when\n' \
    "${0##*/}" "$lock_file" >&2
  printf '  the start routine is called speculatively; nothing was scanned this invocation.\n' >&2
  exit 0
fi

# Dead-man's-switch: is Main sync still around? See the file header for why this checks
# main.md's own heartbeat specifically rather than "any Claude process anywhere."
main_sync_alive() {
  [ "$check_main_sync" -eq 1 ] || return 0
  [ -f "$main_status" ] || return 1
  local last_check last_check_epoch age
  last_check=$(grep -m1 '^last_check:' "$main_status" | cut -d' ' -f2-)
  last_check_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)
  [ "$last_check_epoch" -gt 0 ] || return 1
  age=$(( $(date +%s) - last_check_epoch ))
  [ "$age" -lt "$main_sync_timeout" ]
}

# Deterministic short key for a transcript path, used as the retirement marker filename.
# Not security-sensitive -- just needs to be stable and filesystem-safe.
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

  # De-duplicate to the latest registration per transcript (session-snapshot.sh already
  # overwrites on restart, but a manual edit or a race could leave stragglers).
  local entries
  entries=$(awk -F'\t' '{ latest[$2]=$0 } END { for (k in latest) print latest[k] }' "$registry")

  [ -n "$entries" ] || { printf '%s: registry is empty -- nothing to scan\n' "${0##*/}" >&2; return 0; }

  local tfile dfile key now_epoch mtime_epoch age_days
  now_epoch=$(date -u +%s)

  while IFS=$'\t' read -r _ts tfile dfile; do
    if [ -z "$tfile" ] || [ -z "$dfile" ]; then continue; fi
    key=$(marker_key "$tfile")

    if [ -f "$tfile" ]; then
      mtime_epoch=$(stat -c %Y "$tfile" 2>/dev/null || stat -f %m "$tfile" 2>/dev/null)
    else
      # Transcript vanished (pruned, renamed) -- treat as immediately eligible for retirement,
      # one last no-op attempt below will simply fail to read it and this loop moves on.
      mtime_epoch=0
    fi
    age_days=$(( (now_epoch - mtime_epoch) / 86400 ))

    if [ -f "$retired_dir/$key" ]; then
      if [ "$age_days" -lt "$retire_days" ]; then
        # Woke back up: self-heal by rejoining the normal pool. No separate un-retire path.
        rm -f "$retired_dir/$key"
      else
        # Already retired and still stale: skip entirely, no further consolidation attempts.
        continue
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

    # tick-consolidate.sh exits 0 both when it found nothing new (no model call at all, no
    # cost) and after a real model call + commit -- exit code alone cannot tell them apart, and
    # logging a token cost for the "nothing new" case would inflate the budget on every idle
    # session's every pass, defeating the whole point of the free/cheap split. Its own stderr
    # text does distinguish "no call was made" ("nothing new since ...") from every other exit
    # path, including a post-call commit failure (rc 8/9) where the cost was genuinely incurred
    # even though the run overall failed -- so log for every outcome except the explicit no-op,
    # until real per-call usage plumbing lands (see the addendum's "still open" note;
    # ATTRIBUTE_UNKNOWN_TOKENS is the digest's own measured ~488-token average, used only as a
    # placeholder estimate for an actual model call).
    if printf '%s' "$call_out" | grep -q 'nothing new since'; then
      : # no model call was made -- log nothing
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
  if ! main_sync_alive; then
    printf '%s: Main sync heartbeat stale past %ss -- self-exiting (stateless by design, not a crash)\n' \
      "${0##*/}" "$main_sync_timeout" >&2
    exit 0
  fi
  pass
  sleep "$interval"
done
