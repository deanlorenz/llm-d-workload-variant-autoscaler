from: sync-session (plans)
to: sync
session: checkpoint-guards-parked

Add to § Recent activity as a live-WIP entry.

**2026-08-14/15 — checkpoint scripts: origin-pid lifecycle + atomic single-instance guards.
Coded, tested, committed; review deliberately deferred to a worktree.** Commit **`750f9c5d`** on
`plans`, **local only — not pushed** (branch is 19 ahead of `origin/plans`, most of that other
sessions'). Three scripts reworked: `session-snapshot.sh` (Tier-1 capture), `tick-shared-scan.sh`
(Tier-2 shared consolidation), `sync-main-watch.sh` (main fast-forward). All three now take
`--origin-pid <pid>` — the Claude session that launched them, captured at launch since a detached
child reparents to init — checked with `kill -0` each pass, and on origin death they run **one final
unit of their own real work, then exit**. Dedup replaced lock files with two guards that answer two
different questions: an atomic `mkdir` on a fixed per-origin-pid path (two instances starting the
same instant, when nothing exists for `pgrep` to find) plus the `pgrep` check (a watcher already
running from an earlier launch); guard 1 is held across startup only and `rmdir`'d inline, with a
1-week mtime staleness reclaim as the backstop for a process killed mid-startup. No traps for the
guard. Design: new **`planning/atomic-step-protocol-design-addendum-7.md`** (84 lines).
Verified behaviorally, not by inspection: 5/5 exactly one survivor on simultaneous launch, planted
stale guard reclaimed, planted fresh guard respected and not deleted, guard released while the loop
runs, final pass evidenced in the log on origin death.
**Three defects were found and fixed en route, all the same shape — a guard released before the
thing it protects exists:** (1) the dead-man's-switch originally exited *before* the final pass,
which for the Tier-1/Tier-2 scripts defeats their entire purpose (and the same bug had been sitting
in `sync-main-watch.sh`'s `anchor_alive()` since 2026-08-12, uncaught); (2) a `pgrep`-only dedup had
no atomic step, so two simultaneous launches left **zero** survivors, 4/4; (3) `stat -f %m` is wrong
on GNU coreutils — `-f` takes a format, so `%m` became a filename operand and `stat` printed a
filesystem block while exiting 0, making the `|| echo 0` fallback unreachable and feeding prose into
`$(( ))`; replaced with `date -r`. Root cause of the pattern: **no Type 3 plan existed** — code was
written straight from conversation, so no review had anything to check against. The addendum is that
plan, written retroactively.
**Dean's parking instruction (2026-08-15): stop coding in `plans`.** Ongoing work belongs in a
worktree; the scripts are already coded so they stay here, and the **review resumes later in
`plans-tooling` or a fresh/temp worktree**, explicitly not mixed with `plans-tooling`'s in-flight work.
**⚠️ Review is INCOMPLETE and did not follow the convention.** Two ad-hoc `general-purpose` subagents
served as checkers; their findings were real and are fixed, but CONVENTIONS § Review pipeline requires
a **Type 6 doc** (`planning/*-review.md`, `Status: DRAFT`) from the review-agent role via
`/s-design-review`, and **no Type 6 doc exists**. Two questions left open rather than guessed: who
runs it (this session wrote the code, so self-review is the wrong shape — recommend spawning it), and
which scope form to use (design-doc scope fits; there is no branch/PR).
**⚠️ Armed footguns, carry verbatim:** (1) **`tier1-session-start.sh` is committed but NOT wired and
NOT functional** — it passes no `--origin-pid`, so it would now fail the new required-arg validation;
it also needs a `container-settings.json` SessionStart entry, which `guard-settings-edit.sh` blocked
once and which must not be self-approved. (2) **Four production loops still run the OLD interface**
(pids 16342, 629315 = `session-snapshot.sh`; 89026 = `sync-main-watch.sh`; 620370 =
`tick-shared-scan.sh`) — they work, they just predate the commit; restarting them under the new
interface is a separate approved step, gated on `tier1-session-start.sh` being finished.
(3) **`tick-live-index.sh:111` still carries the `stat -f %m` bug** — same latent crash, left as
out-of-scope. (4) **`.claude/settings.json` holds another session's uncommitted permission
additions** — untouched by this session, do not attribute or discard.
**State:** [`session/status/sync-session.md`](../status/sync-session.md) (full resume detail) ·
[`planning/atomic-step-protocol-design-addendum-7.md`](../../planning/atomic-step-protocol-design-addendum-7.md)
(design + verification checklist + defect history).
