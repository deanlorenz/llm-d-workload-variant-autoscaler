# Code spec — sync-main watcher family

**code spec** · **Status: DRAFT — mixed retroactive and forward-looking, written 2026-08-16.**

## At a glance

**Mission:** document the four sync-main scripts (watcher, one-shot, status, session-start hook) as
they actually exist, and record three live bugs found while doing so.

**Approach:**
- S1 `sync-main-session-start.sh` — the `SessionStart` hook. Contains Defect A and Defect B.
- S2 `sync-main-watch.sh` — the continuous watcher. Contains Defect C (status lies about liveness).
  Guard block forward-looking, keyed on the fixed role constant `"sync"` (not a session, not a pid —
  see Addendum 10's corrected design), must move to the shared library `checkpoint-capture-spec.md`
  S0 specifies.
- S3 `sync-main-once.sh` — one-shot equivalent, no guard needed, no defect.
- S4 `sync-main-status.sh` — read-only status check, no defect.
- `sync-current-watch.sh` is explicitly out of scope (different purpose, needs its own spec).

**Needs you:**
- Nothing blocking right now. Three defects (A: hook launches the watcher without a required flag,
  always fails; B: a stale comment describing a mechanism that no longer exists; C, found in design
  review: the status file lies about liveness after a crash, so the auto-start hook's own success
  check reports false positives) are documented for whoever picks this spec up — no decision from you
  needed to record them, only to prioritize the fix.

**Checklist:**
- [ ] Assign a coder once `single-instance-guard.sh` (S0 in `checkpoint-capture-spec.md`) exists.
- [ ] Fix Defect A (`--origin-pid "$PPID"` on the launch line).
- [ ] Fix Defect B (rewrite the stale flock comment, and the separate stale "any Claude process
  anywhere" claim in the same comment block, per `checkpoint-specs-review.md` Finding 9).
- [ ] Fix Defect C (`write_status` must set `state` from its actual liveness, not a hardcoded string).
- [ ] Migrate S2's guard block to the shared library, keyed on `"sync"`.
- [ ] Decide whether `sync-current-watch.sh` gets folded into this spec or its own.

Most of this spec documents what already exists. **The guard mechanism in S2 (`sync-main-watch.sh`) is
forward-looking**, per [`atomic-step-protocol-design-addendum-10.md`](atomic-step-protocol-design-addendum-10.md)
— it must be rewritten to source the shared `scripts/lib/single-instance-guard.sh` library specified in
[`checkpoint-capture-spec.md`](checkpoint-capture-spec.md) S0, not keep its own inline copy of the guard
block. Two live defects were found while writing this spec, both unrelated to the guard mechanism —
recorded below, not fixed by the planner.

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

**Defect A, live, found while writing this spec, not yet fixed.** `sync-main-session-start.sh` (S1)
launches `sync-main-watch.sh` (S2) **without `--origin-pid`** (its line 55: `nohup bash "$watch_script"
...`), but S2 requires that flag **unconditionally** — unlike `session-snapshot.sh`, there is no
`--once` escape at all; S2's argument-parsing does a hard `die` on a missing `--origin-pid` with no
exception. **This means the hook's auto-start attempt fails every time it actually reaches line 55.**
Related to, but distinct from, the previously-reported symptom in
`session/handoffs/plan__sync-main-hook-silent-noop-and-tier1-tier2-boundary.md.WIP` (sync's own finding:
S1's `cwd` string-match at line 10 can silently no-op before ever reaching the launch line at all) — that
handoff diagnosed one failure mode; this spec adds a **second, independent** one that would still fire
even if the `cwd` match succeeds. Both need fixing for the hook to actually work. Fix for Defect A is
mechanical (pass `--origin-pid "$PPID"`, same fix shape as `checkpoint-capture-spec.md`'s Defect 1 for
`tier1-session-start.sh` — the same class of bug, in a sibling hook, not previously connected).

**Defect B, live, found while writing this spec, not yet fixed.** `sync-main-session-start.sh`'s own
comment block (lines 30-48) says *"the authoritative single-instance guard is an flock inside
sync-main-watch.sh itself"* — stale. `sync-main-watch.sh` (confirmed by direct read) uses the
`mkdir`/`pgrep` dual-guard from Addendum 7, not flock; that comment predates the Addendum 7 migration
and was never updated when the mechanism changed, matching the pattern already found and fixed in
`tier1-session-start.sh`'s own header (`checkpoint-capture-spec.md` Defect 1). The comment's
*substance* (heartbeat check is a racy early-out, not the real guard; do not remove either check) is
still correct and should be preserved — only the "it's an flock" detail needs updating to name the
actual current mechanism.

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

**S1 — `sync-main-session-start.sh` (`SessionStart` hook, contains Defect A and Defect B).** Fires for
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

**S4 — `sync-main-status.sh` (read-only, no defect found).** Prints a one-line verdict
(RUNNING/STALE-NOT-RUNNING/NOT RUNNING) computed from the status file's `last_check` age against a
150s threshold (~2.5× S2's 60s poll interval — the same multiplier `tier1`/Tier-2 family uses elsewhere
for "how much slack before calling a heartbeat dead"), then dumps the full status file. Deliberately
does the date-math itself rather than leaving it to the caller's command line, specifically so the
command a session runs has no `$(...)` substitution and is therefore allowlistable without a permission
prompt — a real, load-bearing design choice, not an arbitrary implementation detail. No defect found.

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
