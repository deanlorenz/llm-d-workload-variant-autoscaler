#!/usr/bin/env bash
# SessionStart hook: auto-starts this session's own Tier-1 checkpoint loop
# (scripts/session-snapshot.sh) exactly once, on any SessionStart source
# (startup/resume/clear/compact/fork).
#
# Why "any source" rather than resume-only: CONVENTIONS.md's own directive is
# unconditional -- "what every session does [...] start the detached loop once, at
# session start" -- with no exception carved out for a fresh startup. A fresh
# session is supposed to follow that on its own first read of CLAUDE.md/CONVENTIONS,
# but relying on that alone already failed once (this hook exists because a live
# session did not start its own Tier-1 until asked directly, despite reading those
# files). Firing this hook on every source closes that gap without waiting on
# session behavior to reliably self-correct.
#
# Safety: session-snapshot.sh carries its own per-transcript flock (added alongside
# this hook), so calling this speculatively on every SessionStart is safe -- a
# transcript that already has a live Tier-1 loop just gets a quiet refuse-and-exit,
# never a duplicate.
#
# Unlike sync-main-session-start.sh, this is NOT scoped to one designated worktree:
# every session, in every worktree, gets its own Tier-1. Digest naming uses the
# session_id (stable, harness-assigned) rather than a topic name a human would have
# to invent -- a human-readable rename is a later, optional step, not required for
# the loop to be correct.

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)
cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
source_val=$(printf '%s' "$input" | jq -r '.source // empty' 2>/dev/null)

if [ -z "$session_id" ] || [ -z "$transcript" ] || [ -z "$cwd" ]; then
  # Malformed or unexpected payload shape -- log and no-op rather than guess.
  printf '%s: missing session_id/transcript_path/cwd in SessionStart payload, skipping\n' \
    "$(basename "$0")" >> /tmp/tier1-session-start.log
  echo '{}'
  exit 0
fi

script="$(cd "$(dirname "$0")" && pwd)/session-snapshot.sh"
[ -x "$script" ] || { echo '{}'; exit 0; }

digest="$cwd/session/digests/session-${session_id}.raw.md"
mkdir -p "$(dirname "$digest")" 2>/dev/null

nohup bash "$script" --out "$digest" --file "$transcript" --interval 120 \
  >> /tmp/tier1-session-start.log 2>&1 &
disown 2>/dev/null || true

# Best-effort visibility: don't block SessionStart waiting on the child, and don't
# claim success we haven't checked -- the lock inside session-snapshot.sh is the
# actual source of truth for whether a loop is running for this transcript.
context="Tier-1 checkpoint loop start requested for this session (source: ${source_val:-unknown}), digest session/digests/session-${session_id}.raw.md. If one was already running for this transcript, the new attempt refused quietly (see /tmp/tier1-session-start.log)."

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
