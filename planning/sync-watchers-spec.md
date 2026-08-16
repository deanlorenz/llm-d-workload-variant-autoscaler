# Code spec — sync-main watcher family

**code spec** · **Status: DRAFT — retroactive, written 2026-08-16, all three found defects and the
guard migration now landed 2026-08-16.**

## At a glance

**Mission:** document the four sync-main scripts (watcher, one-shot, status, session-start hook) as
they actually exist.

**Approach:**
- S1 `sync-main-session-start.sh` — the `SessionStart` hook. Defect A and Defect B, both **FIXED**.
- S2 `sync-main-watch.sh` — the continuous watcher. Defect C (status lied about liveness), **FIXED**
  by the coder who built the guard library. Guard block **migrated** to the shared library
  (`scripts/lib/single-instance-guard.sh`), keyed on the fixed role constant `"sync"` (not a session,
  not a pid — see Addendum 10's corrected design).
- S3 `sync-main-once.sh` — one-shot equivalent, no guard needed, no defect.
- S4 `sync-main-status.sh` — read-only status check, no defect.
- `sync-current-watch.sh` is explicitly out of scope (different purpose, needs its own spec).

**Needs you:** nothing blocking. `sync-current-watch.sh` still needs its own spec or a decision to
fold it into this one — not resolved here.

**Checklist:**
- [x] Build `single-instance-guard.sh` (S0 in `checkpoint-capture-spec.md`) — landed, `f9e1dba6`.
- [x] Fix Defect A (`--origin-pid "$PPID"` on the launch line) — landed, not independently verified
  against a real `SessionStart` firing (see Defect A's own text for why).
- [x] Fix Defect B (rewrite the stale flock comment, and the separate stale "any Claude process
  anywhere" claim in the same comment block).
- [x] Fix Defect C (`write_status` now sets `state` from its actual liveness, not a hardcoded string)
  — landed by the coder, `f9e1dba6`.
- [x] Migrate S2's guard block to the shared library, keyed on `"sync"` — landed, `f9e1dba6`.
- [x] Fix the `date -d ""` dead-watcher-reads-RUNNING bug in S4 and S1's duplicate of the same logic.
- [ ] Decide whether `sync-current-watch.sh` gets folded into this spec or its own.
- [ ] Restart the two live production processes (`tick-shared-scan.sh`, `sync-main-watch.sh`) under
  the migrated code — deployment step, deliberately left to whichever session currently owns the
  sync role (see `session/handoffs/plan__sync-role-restart-tier1-tier2-main-under-fixed-guard.md`).

This spec documents what already exists. All defects found while writing it, and the guard-library
migration it called for, have since landed — see each step below for the fix detail and what was and
was not independently verified.

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then read only the step covering the script you're
touching — by heading, not by line number.

---

## Intent

**intent** — Keep local `main` fast-forwarded to `upstream/main` and pushed to `origin/main`, without a
model in the loop for the mechanical polling/fetch/merge/push work, and surface state via a status file
(`session/status/main.md`) rather than conversation notifications (a watcher started this way is not
harness-tracked). Four scripts, one purpose, three different invocation shapes: a continuous watcher
(S2), a one-shot equivalent for a session that doesn't want a background loop (S3), a read-only status
check (S4), and a `SessionStart` hook that auto-starts S2 when nobody has (S1).

**current call stack, as-built (2026-08-16):**

```
SessionStart hook (this worktree only)  → sync-main-session-start.sh
                                             → (if no live heartbeat) sync-main-watch.sh --origin-pid <pid>
                                                  (polls upstream/main every 60s via git ls-remote;
                                                   on SHA change: fetch, merge --ff-only, push origin main;
                                                   writes session/status/main.md every pass)
one-shot alternative                     → sync-main-once.sh (same fetch/merge/push, no loop, no --origin-pid)
read-only check                          → sync-main-status.sh (RUNNING/STALE/NOT-RUNNING verdict + cat status)
```

**Defect A — FIXED 2026-08-16.** `sync-main-session-start.sh` (S1) launched `sync-main-watch.sh` (S2)
**without `--origin-pid`**, but S2 requires that flag **unconditionally** — unlike
`session-snapshot.sh`, there is no `--once` escape at all; S2's argument-parsing does a hard `die` on
a missing `--origin-pid` with no exception. **This meant the hook's auto-start attempt failed every
time it actually reached the launch line.** Fixed by passing `--origin-pid "$PPID"` — the same fix
shape as `checkpoint-capture-spec.md`'s Defect 1 for `tier1-session-start.sh`. **Not independently
verifiable against a real `SessionStart` firing** (no pid field exists in the hook's own JSON payload
to cross-check `$PPID` against, and simulating the hook's exact process-parentage outside a real
session resume is not reliable) — confirmed only indirectly: the currently-running watcher (started
by hand before this fix existed) carries the real long-lived Claude session pid as its
`--origin-pid`, the same value class `$PPID` now captures automatically in the same position.
**Lower-severity than it looks even if wrong**: since the 2026-08-16 guard migration, `--origin-pid`
is only the kill-switch, not the single-instance identity — a wrong pid here leaks or exits early, it
does not create a duplicate watcher.

Still separate and still open: `session/handoffs/plan__sync-main-hook-silent-noop-and-tier1-tier2-boundary.md.WIP`
(sync's own finding: S1's `cwd` string-match at line 10 can silently no-op before ever reaching the
launch line at all) — that is a different failure mode from Defect A and is not touched by this fix.

**Defect B — FIXED 2026-08-16.** `sync-main-session-start.sh`'s own comment block said *"the
authoritative single-instance guard is an flock inside sync-main-watch.sh itself"* — stale.
`sync-main-watch.sh` now sources `lib/single-instance-guard.sh`'s momentary mkdir+pgrep dedup, keyed
on the fixed role constant `"sync"` (not the mkdir/pgrep-keyed-on-pid shape this comment was already
stale against before today, and not an flock either — that mechanism predates Addendum 7 entirely).
The comment's separate stale claim (self-exits once "neither a VS Code-WSL connection nor a Claude
process remains anywhere in this WSL instance") is also corrected — the kill-switch checks one
specific `--origin-pid`, not "any Claude process anywhere." Both corrected in place; the comment's
*substance* (heartbeat check is a racy early-out, not the real guard; do not remove either check) was
already correct and is preserved.

**new components** — none beyond what `checkpoint-capture-spec.md` S0 already specifies
(`scripts/lib/single-instance-guard.sh`) — S2 below is a second consumer of that same library, not a
new one.

**new conventions** — none identified beyond what harvest-classification.md already covers for this
family under `conv:checkpoint-capture` and the sync role generally.

---

## Prerequisites

No new worktree — all four scripts live in `plans/scripts/`, on the `plans` branch. Depends on
`checkpoint-capture-spec.md` S0 (`single-instance-guard.sh`) landing first if S2's guard rewrite is
picked up in the same coder run as that spec; otherwise S2's guard fix can wait until S0 exists.

**Gates** — `bash -n <script>`; `shellcheck` if installed; behavioral verification per
`atomic-step-protocol-design-addendum-7.md`'s checklist for any change touching S2's guard. No Go, no
DCO, no `make test`.

---

## Step index

**S1 — `sync-main-session-start.sh` (`SessionStart` hook, Defect A and Defect B both FIXED).** Fires for
every worktree's session (container-level `settings.json` is shared) but no-ops everywhere except the
one designated sync-main worktree (`SYNC_WORKTREE`, a hardcoded absolute path — string-compared against
the hook payload's `cwd`, exactly, with no normalization; a mismatch here is the previously-reported,
still-open silent-no-op symptom, out of this spec's fix scope but named for completeness since it
compounds with Defect A). Checks the status file's own heartbeat age (<150s ⇒ alive, skip) before
auto-starting S2 — explicitly documented as a racy early-out, not the real guard (the real guard lives
inside S2 itself, per Addendum 7, not flock as the stale comment claims — Defect B). **Contains Defect
A**: the actual `nohup bash "$watch_script" ...` launch line omits `--origin-pid`, which S2 requires
unconditionally. Fix: pass `--origin-pid "$PPID"`, same verification caution as
`checkpoint-capture-spec.md` S6 (confirm `$PPID` inside this hook's execution context really is the
Claude session's own pid).

**S2 — `sync-main-watch.sh` (continuous watcher, guard mechanism forward-looking, contains Defect C).**
Polls `git ls-remote upstream main` every 60s (a ref query only — cheap, no fetch unless the SHA
actually moved); on a real change, fetches, `merge --ff-only` (never a merge commit; a non-fast-forward
means main has diverged and needs a human, so the push is skipped entirely rather than attempted), then
pushes to `origin/main`. Writes `session/status/main.md` every pass via `write_status()`, and via a
`trap ... EXIT` on any exit path.

**Contains Defect C, found in design review (`checkpoint-specs-review.md` Finding 4), not by the
planner directly.** `write_status()` hardcodes `state: watching` unconditionally (its own line 69) —
`cleanup() { write_status "stopped" ...; }` passes `"stopped"` as the `step` parameter, which lands in
`current_step`, never in `state`. **The trap does NOT make the status honest** — after any exit,
clean or crashed, the file still reads `state: watching`. This matters beyond cosmetics:
`sync-main-session-start.sh`'s own auto-start success check (`grep -q '^state: watching'`) will report
success for a watcher that has already crashed. Fix: `write_status` must actually set the `state` field
from its own `step`/liveness argument, not a fixed string.

`--origin-pid <pid>` dead-man's-switch, unchanged, stays exactly as designed for the kill-switch —
checked with `kill -0` each poll, one final sync before exiting when the origin is gone. **Guard
mechanism, corrected 2026-08-16 — keyed on a logical role, not a session or a pid.** This script (like
`tick-shared-scan.sh` in `checkpoint-capture-spec.md` S4) is run by whichever session currently acts as
**sync** — per Dean, verbatim: *"both sync-main and tier-2 tick are run by sync__ — that is a logical
id not a Claude session id. Whoever runs, runs under that ID."* Today this script inlines its own
`mkdir`/`pgrep` block keyed on `$origin_pid` (lines 31-55) — the wrong key, same class of error
addendum-10 retracted for the per-session scripts, just wrong for a different reason here (this
script's own identity isn't per-session at all). Per Addendum 10's corrected design, must be rewritten
to source `single-instance-guard.sh` and call `guard_acquire "sync-main-watch" "sync"` (the fixed role
constant, same one `tick-shared-scan.sh` uses) — a different sync session resuming ownership recognizes
"already running" by matching the same constant, not any session-specific value. This is the third
confirmed site of the same duplicated guard block (alongside `session-snapshot.sh` and
`tick-shared-scan.sh`) — three independent copies, now one shared consumer count for
`single-instance-guard.sh`, two of the three keyed on the `"sync"` role constant and one keyed on
`session_id`.

**S3 — `sync-main-once.sh` (one-shot, no guard needed, no defect found).** Same fetch/`ff-only`-merge/
push work as S2's `sync_pass()`, without a loop and without `--origin-pid` — a single invocation is its
own single instance by construction, so it correctly has no guard logic to begin with (not an omission,
a genuine non-need). Preserves the watcher's `last_sync` field across a run that finds nothing to do
(read from the existing status file before overwriting it), so a one-shot check never erases evidence of
when the last real sync actually happened. Refuses to run if the `Main` worktree isn't actually on
`main` (a real safety check, not a formality — a one-shot sync on the wrong branch would silently do
nothing useful while reporting success-shaped output). No defect found.

**S4 — `sync-main-status.sh` (read-only, contained a dead-watcher-reads-RUNNING bug, FIXED
2026-08-16).** Prints a one-line verdict (RUNNING/STALE-NOT-RUNNING/NOT RUNNING) computed from the
status file's `last_check` age against a 150s threshold (~2.5× S2's 60s poll interval — the same
multiplier `tier1`/Tier-2 family uses elsewhere for "how much slack before calling a heartbeat dead"),
then dumps the full status file. Deliberately does the date-math itself rather than leaving it to the
caller's command line, specifically so the command a session runs has no `$(...)` substitution and is
therefore allowlistable without a permission prompt — a real, load-bearing design choice, not an
arbitrary implementation detail.

**Found (llm-scaler portability sweep, 2026-08-16), same bug duplicated in S1's own heartbeat
early-out:** `date -d "$last_check" +%s` **succeeds** (rc 0) when `$last_check` is empty, returning
midnight-today's epoch rather than erroring — so the `|| echo 0` fallback never fires on this path,
and a status file with an empty or missing `last_check:` line reads as "last check 0-149s ago" (i.e.
RUNNING) for roughly 2.5 minutes after local midnight, regardless of whether a watcher is actually
alive. Same bug class as the `stat -f %m` issue fixed elsewhere in this family — a command that
succeeds on bad input defeats a `||` fallback that assumes the command errors. Fixed by checking
`[ -n "$last_check" ]` before ever calling `date`, in both S4 and S1's duplicate of the same logic.

## Explicitly out of scope — `sync-current-watch.sh` needs its own spec, not this one

`sync-current-watch.sh` exists in the same `scripts/` directory and shares this family's naming
convention (`sync-*`) but has a genuinely different purpose (watching for pending `sync__*.md` handoffs
against `session/CURRENT.md`'s own last-sync commit — a CURRENT.md-freshness check, not an
upstream/main fast-forward), so it is deliberately **not** folded into this spec under a shared title
that would misdescribe it. **Confirmed still on the old flock + `anchor_alive()` pattern** (checked
directly, 2026-08-13 and again 2026-08-16) — not migrated to Addendum 7's guard mechanism, and not
named in Addendum 7's own "Still open" list either, so this is a real, currently-untracked gap: three
scripts share one guard shape (soon four, once S2 above is fixed) and a fifth, closely-related script
in the same directory still runs the superseded one. Flagged here so it is not lost; a fifth Type 3 (or
an extension of this one, once written) is needed to cover it properly — not written in this pass.
