from: plans (atomic-step-protocol-brainstorm planner)
to: whichever session is currently acting as sync (session c1b50362, per its owned processes)
session: tier1-fix-and-guard-migration-restart

Note on routing: this is a task/notification for the sync ROLE, not a CURRENT-update request, so it
is deliberately `plan__`-prefixed rather than `sync__` -- per CONVENTIONS.md, `sync__` is exclusively
for requests to update CURRENT.md, consumed only by `/sync-current`. This handoff asks you to act on
your own running processes; it does not ask anyone to touch CURRENT.md.

Dean's direct instruction just now: "sync should start tier 1 for itself and the tier 2 + main."
Addressed to whichever session is currently acting as sync — that's you, `tick-shared-scan.sh`
(pid `3410333`) and `sync-main-watch.sh` (pid `3412453`) are both running under your `--origin-pid
3362193` right now, both still on the pre-migration guard code.

## What changed, commits `31d9911a` and `f9e1dba6`

1. **Guard mechanism migrated** — `tick-shared-scan.sh` and `sync-main-watch.sh` now source
   `scripts/lib/single-instance-guard.sh` and key their single-instance guard on the fixed role
   constant `"sync"`, not on `--origin-pid`. `--origin-pid` still does exactly one job in both — the
   `kill -0` kill-switch — unchanged. Practical effect for you: a future sync session picking up the
   role recognizes an instance you started; that did not work correctly under the old pid-keyed
   guard. See `planning/checkpoint-capture-spec.md` S4 and `planning/sync-watchers-spec.md` S2 for
   the full design.
2. **`sync-main-watch.sh` Defect C fixed** — its status file used to hardcode `state: watching`
   even after a crash (`cleanup()`'s "stopped" landed in the wrong field). Now genuinely reflects
   liveness. If you have tooling that greps `session/status/main.md` for `state: watching` as a
   liveness check, it is more trustworthy now than it was.
3. **Tier-1 marker-poisoning bug fixed** (`31d9911a`, unrelated to the guard work, found while
   testing it) — `session-snapshot.sh`'s marker could be poisoned by a `## `-prefixed heading
   inside a user turn's own text. Full account: `planning/checkpoint-capture-spec.md` S2 Defect 2.

## What you need to do, if you want to pick this up

Your two current loops (`3410333`, `3412453`) are still running fine under the old interface — no
urgency, nothing broken by leaving them as-is. Restarting them to run the new code is a real
deployment step, not mine to do on your processes without your own confirmation, per this project's
worktree/process-ownership conventions. When you're ready:

```
kill 3410333 3412453   # or let them idle -- your call, they aren't broken
nohup bash scripts/tick-shared-scan.sh --origin-pid <your real claude pid> --interval 300 &
nohup bash scripts/sync-main-watch.sh --origin-pid <your real claude pid> &
```

Both now recognize each other (and any future sync session's instance) via the `"sync"` role key,
not your pid — so a resume/reload on your side no longer risks a duplicate the way the old
interface did.

**Tier-1 for yourself** — you have no `session-snapshot.sh` loop running at all right now (checked:
`session/.tier2-registry` is empty, no process exists). If you want your own capture running:

```
nohup bash scripts/session-snapshot.sh \
  --out session/digests/sync-session.raw.md \
  --file <your own transcript path> \
  --origin-pid <your real claude pid> \
  --session-id c1b50362-abc7-4c15-87f2-4125ba0f0043 \
  --interval 120 &
```

**One thing to check before you do**: your prior `sync-session` capture (same digest name) never
actually appended anything — `session/digests/.sync-session.raw.md.mark` doesn't exist, and its
digest has been header-only since 2026-08-14. That predates today's fix and was never diagnosed to
a specific root cause beyond "the same class of bug" (see `session/status/single-instance-guard.md`
§ "Two live defects found along the way" for what was checked). Worth a look before assuming a
fresh start will behave differently — if it's the marker-poisoning bug, today's fix should be
enough; if it's something else, flag it back.

No reply required unless you find something that needs a decision from a planner. This is
informational + a request to act on your own processes at your convenience.
