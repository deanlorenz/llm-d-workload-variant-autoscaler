#!/usr/bin/env bash
# Shared config loader for the sync-main script family. Sourced, never executed:
#   . "$(dirname "$0")/lib/sync-main-config.sh"
#
# Reads session/sync-main.conf (WORKTREE, TRACKED_BRANCH, UPSTREAM_REMOTE) into the calling
# script's own variables of the same names. Design: planning/sync-watchers-spec.md S5.
#
# UPSTREAM_REMOTE may be empty -- that is a valid, supported value meaning "no upstream configured
# yet," not a config error. Callers that need to fetch/merge from an upstream must check for this
# themselves and no-op loudly; this loader does not decide that for them.
#
# WORKTREE and TRACKED_BRANCH must both be non-empty -- there is no supported "no worktree" or "no
# tracked branch" state for THIS half (unlike UPSTREAM_REMOTE): a script in this family has nothing
# useful to do at all without knowing which worktree and branch it is watching.

# shellcheck disable=SC2034  # WORKTREE/TRACKED_BRANCH/UPSTREAM_REMOTE are consumed by the
# sourcing script, not this function -- that is the whole point of a sourced loader.
sync_main_load_config() {
  local conf="$1"
  if [ ! -r "$conf" ]; then
    printf '%s: cannot read config %s\n' "${0##*/}" "$conf" >&2
    return 1
  fi

  # Set in the CALLING script's scope, not local -- that is the whole point of a sourced loader.
  # shellcheck disable=SC2034
  WORKTREE=""
  # shellcheck disable=SC2034
  TRACKED_BRANCH=""
  # shellcheck disable=SC2034
  UPSTREAM_REMOTE=""

  local line
  while IFS= read -r line; do
    case "$line" in
      \#*|'') continue ;;
      WORKTREE=*)        WORKTREE="${line#WORKTREE=}" ;;
      TRACKED_BRANCH=*)  TRACKED_BRANCH="${line#TRACKED_BRANCH=}" ;;
      UPSTREAM_REMOTE=*) UPSTREAM_REMOTE="${line#UPSTREAM_REMOTE=}" ;;
    esac
  done < "$conf"

  if [ -z "$WORKTREE" ] || [ ! -d "$WORKTREE" ]; then
    printf '%s: config %s has no usable WORKTREE (got %s)\n' "${0##*/}" "$conf" "${WORKTREE:-<empty>}" >&2
    return 1
  fi
  if [ -z "$TRACKED_BRANCH" ]; then
    printf '%s: config %s has no TRACKED_BRANCH\n' "${0##*/}" "$conf" >&2
    return 1
  fi
  # UPSTREAM_REMOTE empty is fine -- callers check it themselves.
  return 0
}
