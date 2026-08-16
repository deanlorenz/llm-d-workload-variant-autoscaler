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
# Safety: session-snapshot.sh's own single-instance guard (lib/single-instance-guard.sh,
# keyed on --session-id since the 2026-08-16 migration -- not a flock, that predates
# the Addendum-7/10 rework) makes calling this speculatively on every SessionStart safe --
# a transcript that already has a live Tier-1 loop just gets a quiet refuse-and-exit,
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

# --session-id fixes Defect 1: session-snapshot.sh has required --origin-pid + --session-id
# unconditionally (unless --once) since the 2026-08-16 guard migration; this hook omitted both,
# so every hook-started loop would die on launch. $PPID here is this hook's own parent -- the
# Claude session process that triggered SessionStart, same value class as sync-main-session-start.sh
# now captures for its own hook (not independently verified against a real SessionStart firing,
# for the same reason noted there: no pid field in the hook's own JSON payload to cross-check).
#
# --digest deliberately NOT passed (per checkpoint-specs-review.md Finding 5): tick-consolidate.sh
# hard-dies without a digest file that already carries a "Captured through:" marker, and no digest
# with that marker exists until a session creates one by hand (there is no seeding mechanism today).
# Passing --digest here without seeding would break every consolidation attempt for hook-started
# sessions; seeding one is a design decision (what marker value, what header) left open, not made
# here. Hook-started sessions get Tier-1 (free, the actual fix this defect is about) but not Tier-2
# self-registration -- a session that wants Tier-2 still creates its own digest and re-launches with
# --digest, same as before this fix.
nohup bash "$script" --out "$digest" --file "$transcript" --origin-pid "$PPID" \
  --session-id "$session_id" --interval 120 \
  >> /tmp/tier1-session-start.log 2>&1 &
disown 2>/dev/null || true

# Best-effort visibility: don't block SessionStart waiting on the child, and don't
# claim success we haven't checked -- the lock inside session-snapshot.sh is the
# actual source of truth for whether a loop is running for this transcript.
context="Tier-1 checkpoint loop start requested for this session (source: ${source_val:-unknown}), digest session/digests/session-${session_id}.raw.md. If one was already running for this transcript, the new attempt refused quietly (see /tmp/tier1-session-start.log)."

jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
exit 0
