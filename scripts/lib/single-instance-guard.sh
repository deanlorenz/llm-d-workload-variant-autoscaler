#!/usr/bin/env bash
# Shared single-instance guard: "at most one running copy per logical identity".
#
# Sourced, never executed:
#   guard_lib="$(dirname "$0")/lib/single-instance-guard.sh"
#   . "$guard_lib"
#
# Two functions, both called at the ONE startup moment where a script decides whether it is the
# copy that gets to run:
#
#   guard_acquire <script-name> <key-flag> <key>
#   guard_release <script-name> <key>
#
# Extracted from three near-identical inline copies (session-snapshot.sh, tick-shared-scan.sh,
# sync-main-watch.sh). Design: planning/atomic-step-protocol-design-addendum-7.md, as corrected by
# addendum-10's "Corrected design" section (addendum-10's original pid-keyed proposal is retracted
# and must not be built).
#
# WHAT THE KEY IS
# ---------------
# <key> is whatever logical identity actually needs "at most one" for this caller:
#
#   * a Claude session id, for a per-session script (session-snapshot.sh). Stable across
#     resume / window reload / wake / compaction -- unlike a process pid, which changes while the
#     logical session persists, so a pid-keyed guard cannot see the loop the session already has
#     running. That was the identity error this library exists to correct.
#
#   * a fixed, project-defined role constant ("sync"), for a script meant to have exactly one
#     shared instance no matter which session currently owns the role (tick-shared-scan.sh,
#     sync-main-watch.sh). A different session taking over the sync role must still recognize the
#     instance the previous one started, so the key must not be derived from any session at all.
#
# Never a process pid, in either case: a pid identifies a process, not a session and not a role.
#
# --origin-pid is a SEPARATE, UNRELATED mechanism and this library does not touch, replace or read
# it. It is each caller's kill-switch -- "is the Claude session that started me still alive",
# checked with `kill -0` in the main loop. Keying the guard on it was the exact conflation that
# made a session's own loop invisible to itself after a restart. Do not re-merge the two.
#
# WHY THE LOCK IS MOMENTARY
# -------------------------
# mkdir is taken only for the instant it takes to answer "am I the one starting this", and released
# immediately after -- whether this instance proceeds or stands down. It is never held for the
# script's running lifetime. Consequences, all deliberate:
#
#   * No pid is recorded anywhere in this guard, and there is no held-lock staleness check. A
#     pid-recording, staleness-checking design was drafted in addendum-10 and retracted: with a
#     momentary lock there is no "holder" that can go stale mid-run. Do not reintroduce it.
#   * A running instance is discovered by pgrep, not by anything the lock tracks.
#   * No EXIT trap. Addendum 7's "no trap" ruling stands: a trap would only matter for a lock held
#     across the script's lifetime, which this is not.
#
# TWO GUARDS, TWO WINDOWS, NEITHER COVERING THE OTHER
# ---------------------------------------------------
#   pgrep -- is a fully-started instance already running? Narrowed by _guard_is_instance() to
#            processes actually executing the script; see that function for why that is mandatory.
#   mkdir -- are two instances deciding at the very same instant, when neither is far enough along
#            for pgrep to see the other? Dropping this one left ZERO survivors on simultaneous
#            launch (both instances saw each other and both stood down), 4/4.
#
# Order matters: mkdir first, so exactly one instance proceeds to the pgrep check, and the loser
# exits before that check can mistake it for a running instance.
#
# Linux only: uses `date -r <file>` (GNU coreutils) for mtime. BSD/macOS `date -r` takes seconds.

# Path of the momentary dedup directory for one (script, identity) pair.
_guard_dir() {
  printf '%s/%s.dedup.%s' "${TMPDIR:-/tmp}" "$1" "$2"
}

# True when <pid> is a process genuinely EXECUTING <script-name>.sh, rather than one that merely
# mentions it somewhere in its argv.
#
# This filter is load-bearing, not defensive polish. `pgrep -f` matches the pattern anywhere in a
# process's argv, and the normal launch path puts the script's own name into a longer-lived
# process's argv: a session starting the loop runs something like
# `nohup bash scripts/<script>.sh --origin-pid N &` from a shell whose command line therefore
# contains the pattern and outlives the launch. Without this filter the freshly-started script sees
# its own launcher, concludes "one is already running", and stands down -- so the guard blocks every
# start instead of the second one. That is why launching had to be hidden behind an on-disk wrapper
# script to be tested at all; with this filter it does not.
#
# Recognized shapes are the ones this family actually uses: direct execution (argv[0] is the
# script) and shell invocation (argv[0] is a shell, argv[1] is the script -- `nohup` execs bash in
# place, so it does not add a level).
_guard_is_instance() {
  local pid="$1" script_name="$2" a0="" a1=""
  [ -r "/proc/$pid/cmdline" ] || return 1
  { IFS= read -r -d '' a0 || true; IFS= read -r -d '' a1 || true; } < "/proc/$pid/cmdline"
  case "${a0##*/}" in
    "${script_name}.sh")  return 0 ;;
    bash|sh|dash|ksh|zsh) [ "${a1##*/}" = "${script_name}.sh" ] && return 0 ;;
  esac
  return 1
}

# guard_acquire <script-name> <key-flag> <key>
#
#   <script-name>  the caller's basename with .sh stripped ("session-snapshot"). Passed in rather
#                  than derived here, so the pgrep pattern is visible at the call site.
#
#   <key-flag>     the flag that carries <key> in a running instance's argv ("--session-id"), or
#                  the empty string when the key is not argv-borne.
#
#                  Empty means the script name alone discriminates -- the right pattern for a
#                  script whose semantic is "one instance system-wide, whoever started it". Such a
#                  script has nothing else in its argv to match on, and requiring an argv-borne
#                  role flag would be worse than useless here: a caller that omitted the flag (the
#                  SessionStart hooks launch these scripts with a fixed argument list) would make
#                  every instance invisible to every other, silently disabling the guard. Matching
#                  the bare script name is also what lets a new sync session see an instance
#                  started by an older one -- the whole point of the role-constant key.
#
#                  A bare name matches broadly, so _guard_is_instance() below is required, not
#                  optional: without it the pattern also matches the shell that launched this very
#                  script, and every start stands down. Verified by direct test -- two simultaneous
#                  launches with a bare-name key left ZERO survivors until that filter was added.
#
#   <key>          the logical identity described in the file header.
#
# Returns:
#   0  Proceed. This instance holds the guard and MUST call guard_release before entering its loop
#      -- the lock is momentary by design.
#   1  Another instance is deciding at this same instant (mkdir lost the race). Nothing was
#      acquired, so do NOT call guard_release: the directory belongs to that other instance.
#      Stand down.
#   2  A fully-started instance is already running. The guard was taken and has already been
#      released internally. Stand down.
#   3  Caller error (bad or missing arguments). Nothing acquired.
#
# Standing down is success, not failure: callers print their own message and `exit 0` on 1 and 2.
guard_acquire() {
  local script_name="${1:-}" key_flag="${2-}" key="${3:-}" dir pattern

  case "$script_name" in
    '') printf 'guard_acquire: <script-name> is required\n' >&2; return 3 ;;
    *[!A-Za-z0-9._-]*) printf 'guard_acquire: bad <script-name>: %s\n' "$script_name" >&2; return 3 ;;
  esac
  # The key lands in both a directory name and a pgrep pattern, so keep it to characters that are
  # inert in each. Session ids (UUIDs) and role constants already are; this only stops a
  # mis-passed value from escaping the directory or corrupting the regex.
  case "$key" in
    '') printf 'guard_acquire: <key> is required\n' >&2; return 3 ;;
    *[!A-Za-z0-9._-]*) printf 'guard_acquire: bad <key>: %s\n' "$key" >&2; return 3 ;;
  esac
  case "$key_flag" in
    '') : ;;
    --[A-Za-z0-9-]*) : ;;
    *) printf 'guard_acquire: bad <key-flag>: %s\n' "$key_flag" >&2; return 3 ;;
  esac

  dir="$(_guard_dir "$script_name" "$key")"

  # Reclaim a guard abandoned by a process killed between its own mkdir and rmdir (SIGKILL, OOM, an
  # abrupt sleep). This is NOT the retracted held-lock staleness check: the window it covers is
  # sub-second, but without this a single kill inside that window wedges every future start
  # permanently. 1 week is far longer than any startup, so age alone is a safe abandonment signal.
  if [ -d "$dir" ] && [ "$(( $(date +%s) - $(date -r "$dir" +%s) ))" -gt 604800 ]; then
    rmdir "$dir" 2>/dev/null
  fi

  mkdir "$dir" 2>/dev/null || return 1

  if [ -n "$key_flag" ]; then
    pattern="${script_name}[.]sh .*${key_flag} ${key}"
  else
    pattern="${script_name}[.]sh"
  fi

  # The escaped [.]sh is load-bearing: a bare `.sh` matches any character in that position and
  # over-matches. Do not simplify it.
  #
  # The `grep -v "^$$\$"` below excludes this process's own pid, which pgrep -f necessarily matches
  # (our argv contains the pattern). `$$` is correct ONLY because it is expanded here, inside the
  # sourced function: `source` does not fork, so `$$` is the calling script's pid, and `$$` keeps
  # that value inside a pipeline subshell. Rewriting it to `$BASHPID` or to a value captured in a
  # subshell silently breaks self-exclusion, and pgrep dedup with broken self-exclusion is what left
  # ZERO survivors on two simultaneous launches, 4/4, in this mechanism's own earlier verification.
  # (`-v` rather than the historical `-qv` only because the surviving pids are needed below; the
  # self-exclusion regex is unchanged and still evaluated right here.)
  local pid
  for pid in $(pgrep -f "$pattern" 2>/dev/null | grep -v "^$$\$"); do   # $$ = THIS script's pid, never $BASHPID -- see above
    if _guard_is_instance "$pid" "$script_name"; then
      rmdir "$dir" 2>/dev/null
      return 2
    fi
  done

  return 0
}

# guard_release <script-name> <key>
#
# rmdir, idempotent if already gone. Called at the same startup moment as guard_acquire, on its
# success path only -- never from an exit path or a trap. See the file header on why this is not a
# lifetime-held lock.
guard_release() {
  local script_name="${1:-}" key="${2:-}"
  if [ -z "$script_name" ] || [ -z "$key" ]; then
    printf 'guard_release: <script-name> and <key> are required\n' >&2
    return 3
  fi
  rmdir "$(_guard_dir "$script_name" "$key")" 2>/dev/null
  return 0
}
