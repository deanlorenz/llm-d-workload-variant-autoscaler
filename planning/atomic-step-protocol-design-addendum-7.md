# Addendum 7 — single-instance guards and drain-before-exit for the three checkpoint scripts

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (design, FINAL) and the
flock guard in [Addendum 2](atomic-step-protocol-design-addendum-2.md). Supersedes: the flock in
`tick-shared-scan.sh`, the `anchor_alive()` check in `sync-main-watch.sh`.

**Status: written retroactively 2026-08-14 (code came first — that was the process failure this
document exists to correct). Linux only. Its own mechanism further revised by
[Addendum 10](atomic-step-protocol-design-addendum-10.md) — pid-based staleness, shared library,
handle registry.**

## At a glance

**Mission:** give the checkpoint-script family (session-snapshot, tick-shared-scan, sync-main-watch)
a real single-instance guard and a guaranteed drain-before-exit, replacing an flock/anchor_alive
mechanism that had two real defects.

**Approach:** `--origin-pid` dead-man's-switch (unchanged, still correct) + two guards for the
startup race (`mkdir` atomic dedup, `pgrep` liveness check) + a 1-week stale-guard reclaim.

**Needs you:** nothing right now — but see Addendum 10, which changes the staleness signal and
deduplicates this mechanism into a shared library. Don't build fresh against this doc alone; read
Addendum 10 too.

**Checklist:**
- [x] Guards designed and behaviorally verified (5 scenarios, all pass).
- [ ] `tier1-session-start.sh` still needs `--origin-pid "$PPID"` wiring (tracked in
  `checkpoint-capture-spec.md`).
- [ ] `container-settings.json` hook entry still unapplied — needs your explicit approval.
- [ ] Four production loops still run the old interface — restart is separate, approved step.
- [ ] `tick-live-index.sh:111` still carries the `stat -f %m` bug, out of scope here.
- [ ] Superseded by Addendum 10's shared-library redesign — don't build fresh copies of this guard.

---

## Scripts and purposes

Each script's exit behavior follows from its own purpose. Do not copy a mechanism between them
without checking that the purpose supports it.

| Script | Purpose | Final work before exit |
|---|---|---|
| `session-snapshot.sh` | Tier-1 panic-recovery capture: user's words to disk, no model | **Required.** Capturing on session death is the point. |
| `tick-shared-scan.sh` | Tier-2 shared consolidation across sessions | **Required.** Registry content would otherwise wait for the next sync session. |
| `sync-main-watch.sh` | Keep local `main` fast-forwarded to `upstream/main` | Nice-to-have. State is idempotent; the next watcher's first poll recovers it. |

## Lifecycle

`--origin-pid <pid>` — the Claude session that started the loop, captured at launch (a detached
child reparents to init, so it cannot be re-derived later). Required unless `--once`. Checked with
`kill -0` each pass; when gone, run one final unit of work **then** exit.

No lock files, no status-file heartbeats, no anchor-process checks.

## Single-instance guards

Two questions, two mechanisms; neither covers the other's window:

1. **Two instances starting at the same instant** — nothing is running yet, so there is nothing to
   find. Needs an atomic test-and-set: `mkdir "$TMPDIR/<script>.dedup.<origin_pid>"`. Fixed path —
   any varying component (a timestamp, say) means two racers compute different names and both win.
2. **A watcher already running from an earlier launch** — needs `pgrep -f "<script>[.]sh
   .*--origin-pid <pid>"`, filtered through `grep -qv "^$$\$"` because `pgrep -f` matches this
   script's own argv.

Guard 1 is acquired first, guard 2 checked while it is held, then `rmdir` inline on both outcomes
(proceed or stand down). No trap — see below. Both skipped under `--once`.

**Stale guards:** a process killed between `mkdir` and `rmdir` leaves the directory behind. On
startup, if it exists and its mtime is over a week old, `rmdir` it and continue. One week is a
dead-holder safeguard, not a startup budget — it must be far longer than any real startup so that
age alone is a safe abandonment signal.

**No trap.** It would only cover "died before its own `rmdir`", which the staleness check already
covers, and in `sync-main-watch.sh` it collides with that script's existing `cleanup` EXIT trap.

## Verification required before production restart

Behavioral, not by inspection:

1. Two genuinely simultaneous launches → exactly one survivor. (The pgrep-only version left
   **zero**, 4/4 — both saw the other and both stood down.)
2. Planted stale guard → reclaimed.
3. Planted fresh guard → respected, and the incumbent's guard not deleted.
4. Origin killed → final work runs, evidenced in the log, then exit.
5. Normal start → guard already released while the loop runs.

Testing the guard mechanism alone is what let both prior defects through. Test what the script is
*for*.

## Defect history

- **Drain-before-exit missing.** `sync-main-watch.sh`'s original `anchor_alive()` (2026-08-12) checked
  liveness at the top of the loop and exited immediately. That shape was copied into the other two
  scripts during this rewrite. Root cause: no written purpose statement to check the code against, so
  the template was existing code rather than intent.
- **Dedup race.** pgrep-only had no atomic step. Fixed by guard 1.
- **`stat -f %m`.** Used as a BSD fallback; on GNU coreutils `-f` takes a *format*, so `%m` became a
  filename operand — `stat` printed a filesystem block and exited 0, making the `|| echo 0` branch
  unreachable and feeding prose into `$(( ))`. Replaced with `date -r <file> +%s`. Still present in
  `tick-live-index.sh:111`, out of scope here.

## Still open

- `tier1-session-start.sh` needs `--origin-pid "$PPID"` before the SessionStart hook can start these.
- The `container-settings.json` hook entry is unapplied (needs explicit approval).
- Four production loops still run the old interface; restart is a separate, approved step.
- `tick-live-index.sh:111` carries the `stat -f %m` bug.
