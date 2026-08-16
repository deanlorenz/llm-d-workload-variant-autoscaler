from: plans (single-instance-guard coder)
to: sync
session: single-instance-guard

## What changed

`scripts/lib/single-instance-guard.sh` built (new), and all three of its call sites migrated:
`session-snapshot.sh` (keyed on a new required `--session-id`), `tick-shared-scan.sh` and
`sync-main-watch.sh` (both keyed on the fixed role constant `"sync"`). `--origin-pid` untouched in
all three — still only the `kill -0` kill-switch. `sync-main-watch.sh`'s Defect C also fixed
(`write_status` now sets `state` from a real argument instead of hardcoding `watching`).

**Committed in `f9e1dba6` — but not as its own commit, and its message does not describe this work.**
Another session's commit swept my staged files in via the shared git index (detail and the suggested
convention fix are in `plan__shared-git-index-commit-collision.md`, which is a planner item, not
yours). Content verified intact against the working tree. **Not pushed.** `plans` is now 29 commits
ahead of `origin/plans`.

Full state, test results and the four judgment calls: **`session/status/single-instance-guard.md`**.

## Update CURRENT.md

Suggested addition to § Recent activity (in review, not complete — Dean has not reviewed):

**2026-08-16 — shared single-instance-guard library built; three call sites migrated; guard identity
key corrected.** Closes the "build S0" and "migrate S2/S4" checklist items in
[`planning/checkpoint-capture-spec.md`](../planning/checkpoint-capture-spec.md) and the guard half of
[`planning/sync-watchers-spec.md`](../planning/sync-watchers-spec.md) S2, against Addendum 10's
**corrected** (not retracted) design. The guard now keys on logical identity — a session id for
`session-snapshot.sh`, the fixed role constant `"sync"` for the two sync-owned loops — never a
process pid. Verified behaviorally, not by inspection: two simultaneous launches leave exactly one
survivor 5/5 for both key shapes, planted fresh guards are respected and left intact, week-old
guards reclaimed, guard released while the loop runs, and the `--origin-pid` kill-switch still runs
one final pass before exit. `shellcheck`/`bash -n` clean with zero new findings. **The bug fix
demonstrated end to end:** launching either sync-owned script now correctly stands down against the
live production instances that were started under a *different* `--origin-pid` — under the old
pid-keyed guard both would have started a duplicate, which for `sync-main-watch.sh` means two
watchers pushing to `origin/main`. Also fixed **Defect C** (the status file claimed `state: watching`
after every exit, clean or crashed, which made `sync-main-session-start.sh`'s auto-start success
check report healthy for a dead watcher). **Two judgment calls needing review:** an empty
`<key-flag>` means "the script name alone discriminates" (the role constant appears in no script's
argv and the specs never resolved that; adding a `--role` flag would have silently disabled the
guard, since the hook launch paths are out of scope this round), and a `/proc`-based narrowing filter
was added beyond the spec — **required, not polish**: a bare-name `pgrep` also matches the shell that
launched the script, which left **zero** survivors on the first role-keyed test until it was added.
It also removes the documented need to launch these loops through an on-disk wrapper to dodge pgrep
self-matching. State: [`session/status/single-instance-guard.md`](status/single-instance-guard.md).

## Blockers / next steps to record

- **Still open in both specs, deliberately untouched:** `tier1-session-start.sh` Defect 1 (+ its
  `--digest` decision), `sync-main-session-start.sh` Defects A and B, S0b's handle registry,
  `sync-current-watch.sh`'s own spec, and the `container-settings.json` hook wiring — all gated on
  Dean's approval, none started.
- **Defect B is still open and its location is worth recording correctly:** the stale flock claim and
  the stale "any Claude process anywhere in this WSL instance" claim are both in
  `sync-main-session-start.sh` (lines 45 and 34-36), a file this round was told to leave alone.
  `sync-main-watch.sh`'s own header is fixed.
- **⚠️ Armed footgun — capture is currently DOWN for two sessions, and two of the four old-interface
  production loops are gone.** `session-snapshot.sh` pids `16342` and `629315` are dead: I killed
  them during testing with an over-broad cleanup helper (my error, recorded in my status file). They
  were capturing **nothing** at the time — verified, see the next bullet — so nothing was lost, but
  they are not running now and I did not restart them (that is the separately-approved deployment
  step, and these `claude` processes carry no `--resume=<session-id>` in argv, so CURRENT.md's
  own pid-identification recipe does not apply to this launch shape). The other two loops
  (`tick-shared-scan.sh` `3410333`, `sync-main-watch.sh` `3412453`) are alive and untouched.
  Restart command shape is in my status file.
- **⚠️ Two live Tier-1 capture defects, silent, NOT fixed** (handed to a planner in
  `plan__tier1-capture-marker-poisoning.md`, not yours to consume): `session-snapshot.sh`'s marker
  can be overwritten by a `## ` heading inside the user's own turn text — the
  `atomic-step-protocol-brainstorm` marker currently reads literally `Findings`, so that session
  captured nothing from **2026-08-13** onward; and `sync-session.raw.md` has never been appended at
  all (no marker, `turns: 122` each pass, 379 bytes since 2026-08-14). Both fail with rc 0, so a
  broken capture is indistinguishable from an idle session.
- Nothing pushed. No GitHub action taken. No production loop restarted.
