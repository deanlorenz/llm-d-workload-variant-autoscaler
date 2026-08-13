from: sync
to: plan
session: tick-shared-scan lock + start-ownership gap

## What this is

`scripts/tick-shared-scan.sh` (approved by Dean 2026-08-13, committed `3354232a`) has no
single-instance guard — no `flock`, nothing. Its own header comment says "the sync session
starts and monitors this loop," matching `atomic-step-protocol-design-addendum-2.md`'s
"Ownership and lifecycle" section: **exactly one instance**, sync-owned, unlike the per-session
Tier-1 loops where each session legitimately starts its own.

That singular-ownership model is exactly why the missing lock is a real gap, not a
theoretical one: a second sync session (or the same one, restarted and not checking first)
starting it again produces two loops racing over the same `session/.tier2-registry`,
`session/.retired/`, and `session/.tier2-usage.log` — the daily-cap accounting in particular
assumes one writer summing one log.

## Precedent already in this repo

Both sync watchers (`sync-main-watch.sh`, `sync-current-watch.sh`) hit this exact failure —
a heartbeat-only "is one already running?" check turned out racy and let two live instances
run simultaneously undetected (2026-08-10 incident, `sync-main-watch.sh`). The fix that
landed in both: an `flock` on a dedicated `/tmp/*.lock` file, held for the process's whole
life, checked by every start path so it's safe to call the start routine speculatively — a
redundant instance just refuses the lock and exits 0. See either script's current top-of-file
comments for the exact pattern (self-pid recorded via `truncate` + write on the same fd,
holder's pid read *before* the truncating `exec 9>>` open so a duplicate can report who holds
it).

## What's needed

1. **A lock**, same shape as the two sync watchers', added to `tick-shared-scan.sh`.
2. **A clear "how do I know if it's already running, and how do I (re)start it" procedure**
   for the sync session — not necessarily a full skill, but at minimum a status file
   (`session/status/tick-shared-scan.md`?) so a fresh sync session can tell at a glance
   whether the loop is alive without grepping `ps`.
3. **Whether the sync-main SessionStart-hook auto-start pattern applies here too** — i.e.
   should entering the `plans` worktree also auto-start `tick-shared-scan.sh` if it's not
   running (same stateless/dead-man's-switch design Dean asked for on the sync watchers:
   restart on VS Code/Claude entry, self-exit when nobody's around), or is a manual
   `/s-sync-main`-style command the right level of ceremony for something that runs every
   5 minutes and touches multiple sessions' digests. Not resolved — this handoff is raising
   the question, not answering it.

## Not done by sync

Sync did not add the lock unilaterally. Dean approved the script as committed; patching it
immediately after approval, before he'd seen the patch, would mean starting code he hadn't
actually reviewed. This is deliberately a `plan__` handoff (design/ownership question) rather
than something sync just fixed and reported.

## Current state

`tick-shared-scan.sh` has **not been started**. No `session/.tier2-registry` exists yet — it
has never run on this machine. Holding until this is resolved.
