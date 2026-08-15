from: sync-session (plans)
to: plan (atomic-step-protocol-brainstorm)
session: tier1-session-start-ownership-transfer

## What this is

Dean's instruction (2026-08-15): the atomic-step-protocol-brainstorm planner now owns finishing
and wiring `scripts/tier1-session-start.sh`. It was written by the sync session on 2026-08-14 as
part of the checkpoint-guard rewrite (commit `750f9c5d`) and is committed but **not functional**.

## Current state

`scripts/tier1-session-start.sh` is a `SessionStart` hook meant to auto-start each session's own
Tier-1 loop (`session-snapshot.sh`). It is NOT wired into `.claude/container-settings.json` — no
hook entry calls it. Verified directly this morning: `container-settings.json`'s only `SessionStart`
hook is `sync-main-session-start.sh` (matcher `startup|resume`). There is no hook for Tier-1 at all.

Two concrete gaps to close:

1. **`tier1-session-start.sh` doesn't pass `--origin-pid`.** `session-snapshot.sh` was reworked in
   `750f9c5d` to require `--origin-pid <pid>` (unless `--once`) — see
   `planning/atomic-step-protocol-design-addendum-7.md` for the full design (dead-man's-switch tied
   to the originating Claude session's pid, checked via `kill -0`, drain-before-exit). The hook needs
   to capture `$PPID` at the moment it fires (that's genuinely the Claude session process at hook-fire
   time — a later-reparented child cannot re-derive it) and pass `--origin-pid "$PPID"` through to
   `session-snapshot.sh`. As written today it passes no origin pid at all, so it would now fail
   `session-snapshot.sh`'s required-arg validation.
2. **The `container-settings.json` hook entry was never added.** This edit is real settings/hooks
   surface and needs explicit approval — `guard-settings-edit.sh` blocked it once already when the
   sync session tried. Do not self-approve; propose the diff and wait for Dean.

## Why CONVENTIONS.md's directive did not make this happen on its own

CONVENTIONS.md § Checkpoint capture states "every session starts the detached loop once, at session
start" as a policy for sessions to follow by reading it — it is prose, not a firing mechanism. It is
not itself a hook. The only thing that currently auto-fires on `SessionStart` is
`sync-main-session-start.sh`. The two currently-running Tier-1 instances (pids 16342, 629315 as of
this morning) were both started by hand, by sessions manually invoking `session-snapshot.sh` — not
by any hook. Confirmed this directly today after Dean caught the discrepancy between what was said
yesterday ("every session starts its Tier-1") and what was actually observed (neither running
instance came from a hook).

## Scope note

This is purely a SessionStart-hook wiring task, independent of the review that's separately pending
on the checkpoint-guard scripts themselves (`planning/atomic-step-protocol-design-addendum-7.md`,
Type 6 doc not yet written, resuming later in `plans-tooling` or a fresh worktree — not this handoff's
concern). `session-snapshot.sh` itself does not need further changes for this task; only the hook
that starts it does.

## Armed footguns to carry into this work

- The two currently-running old-interface Tier-1 loops (pids 16342, 629315) should NOT be
  auto-restarted as a side effect of finishing this hook — restarting them is a separate, deliberate
  step once the new hook is verified working, not something to fold in silently.
- `.claude/settings.json` (global, not `container-settings.json`) currently carries another session's
  uncommitted permission additions, unrelated to this task — don't attribute them to this work or
  discard them.
