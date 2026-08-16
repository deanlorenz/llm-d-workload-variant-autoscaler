# Addendum 10 — checkpoint-guard redesign: pid-based staleness, shared library, handle registry

**⚠️ RETRACTED 2026-08-16, same day as written. Superseded by § Corrected design below.** This
addendum's original content (kept intact below the retraction notice, per this project's own
never-silently-rewrite discipline) proposed keying the single-instance guard on `--origin-pid`. That
premise is wrong: **`--origin-pid` identifies a Claude *process*, not a Claude *session*, and a
session's underlying process pid can and does change across a restart/resume while the logical
session persists.** A pid-keyed lock cannot express "one running copy per session, for the session's
whole life" — the exact semantic this mechanism needs. Root-caused by Dean during a live walkthrough
of a real running process (see § Corrected design). Everything downstream of the wrong premise in the
original content — the pid-based staleness check, the pid-reuse fallback reasoning, the handle-registry
sketch keyed on `<origin-pid>.<own-pid>` — inherits the same error and must not be built as originally
written here.

**Amends** [`atomic-step-protocol-design-addendum-7.md`](atomic-step-protocol-design-addendum-7.md)
(single-instance guards and drain-before-exit) and, by extension,
[`atomic-step-protocol-design-addendum-2.md`](atomic-step-protocol-design-addendum-2.md) (the original
flock guard Addendum 7 superseded). Addendum 7 is **not edited**: this is a further amendment on the
same mechanism, triggered by Dean questioning the mechanism's shape while a retroactive Type 3 spec for
this script family was being drafted.

**Status: original content decided-then-retracted 2026-08-16. Corrected design below, same day,
following a careful step-by-step semantics discussion. Not yet built.**

## At a glance

**Mission:** fix the single-instance guard's identity key. It is currently `--origin-pid` (a process
pid); it must be the session's own stable identifier (`session_id`, a UUID stable across
resume/reload/wake) — `--origin-pid` stays, but only for the unrelated kill-switch check.

**Approach (corrected, see full section below):**
- `session_id` is the key for both discoverability (`pgrep`) and the momentary start-time lock
  (`mkdir`) — never a pid.
- `--origin-pid` stays exactly as it is today, doing exactly one job: the kill-switch's `kill -0`
  check, decoupled entirely from lock identity.
- The lock is **momentary, not held** — taken only for the duration of "am I the one starting this,"
  released immediately once that question is answered. There is no "holder" to go stale while a script
  runs; the running script itself is discovered via `pgrep` on `session_id`, not via anything the lock
  tracks.
- Semantics: **at most one** running copy per session (for `session-snapshot.sh`) or per worktree (for
  `sync-main-watch.sh`) — never "exactly one" (idle-with-zero is fine) and never "at least one" (nothing
  guarantees restart).
- A live, running production process (pid `16342`, this session, alive since 2026-08-13) was checked
  directly and confirmed to have **no `--origin-pid` at all** — it predates the kill-switch entirely and
  cannot be killed by it. Not a "maybe broken" — confirmed structurally absent.
- Git-native locking, socket-bind, and FD/EOF-based liveness detection were all explored and are
  recorded in the discussion history below for their own reasoning, but none is the mechanism going
  forward — `pgrep` + momentary `mkdir`, both keyed on `session_id`, is.

**Needs you:** nothing right now on this addendum specifically — the semantics are agreed. Building
`single-instance-guard.sh` against the corrected key, and fixing the four confirmed old-interface
production loops, are the next steps.

**Checklist:**
- [ ] Rewrite `checkpoint-capture-spec.md` S0/S0b and `sync-watchers-spec.md` S2 to key on
  `session_id`, not `--origin-pid`, for the lock/lookup; keep `--origin-pid` solely for the
  kill-switch.
- [ ] Build `single-instance-guard.sh` against the corrected key.
- [ ] Confirm whether all four "old-interface" production loops CURRENT.md names are missing
  `--origin-pid` entirely (like pid `16342`, confirmed) or just the guard mechanism — different fix.
- [ ] Re-verify `checkpoint-specs-review.md`'s Finding 2 against this corrected design — it was raised
  against the retracted premise and needs re-examination, not blind acceptance.

---

## Corrected design (2026-08-16, same day, following a careful step-by-step discussion)

### What are we protecting, and what semantics do we actually want

Dean's own framing, which the discussion started from rather than assuming: *"what semantics do we
want? exactly one script running per session? at least one? at most one? what are we protecting?"*
Worked through per script, since the two scripts in this family answer differently:

- **`session-snapshot.sh` — one per session**, not one per pid. *"session comes alive, resumes, window
  reloaded — script fires — need one copy only, always running, until session is dead. pid was used to
  track the session for the deadman kill switch. why would 2 claude sessions have same pid? but even if
  they do, should still have 2 copies. so a pid is wrong lock. good for kill switch only."* On every
  resume/wake — still the same logical session — the session must check whether its own snapshot loop is
  still running, and (re)start it if not.
- **`sync-main-watch.sh` — one per worktree**, started by the sync session. Every time sync starts or
  resumes, it must check whether main's watcher is still running. If sync itself is dead, main's watcher
  should die too — a different dependency chain than the per-session case.
- **Protection wanted, both cases: at most one.** Not "exactly one" (an idle period with zero running
  copies is a perfectly normal state — a session that hasn't started its loop yet, or whose loop
  correctly exited when the session died) and not "at least one" (nothing in either script's purpose
  requires guaranteeing a copy is always running; that would need a separate restart-guarantee mechanism
  this addendum doesn't provide).

Three distinct sub-problems, named explicitly rather than conflated: (1) checking whether the script
itself is alive, (2) checking whether the owning session is alive (the kill-switch, unrelated to (1)),
and (3) the lock that prevents two starts from both succeeding.

### The identity-key error, found by checking a real running process

The corrected key is `session_id` (the Claude session's own stable UUID, unchanged across resume/
reload/wake/compaction) for both (1) and (3) above. `--origin-pid` stays exactly where it is, doing
exactly (2) — nothing else.

This was root-caused, not asserted, by checking a real live process rather than reasoning in the
abstract. Pid `16342` is a `session-snapshot.sh` loop for **this exact session**
(`f0196004-c4a5-494c-8b98-1d4176b68ba0`), running continuously since 2026-08-13 — three days, across at
least one restart of the Claude Code process itself (today's actual `claude` process is a different pid,
`3363929`, started 2026-08-15). Direct inspection (`ps -p 16342`, `/proc/16342/cmdline`) confirmed **this
running process has no `--origin-pid` argument at all** — it predates the kill-switch mechanism entirely.
Dean's read, and the correct one: *"maybe indicate that kill switch did not work"* was the wrong framing
to jump to — the actual finding is sharper: **there is no kill-switch here to be broken; this process was
never given one to check.** It will run forever regardless of whether the session is alive, since nothing
in it watches anything. This is one of the four "old-interface production loops" CURRENT.md already
names — now confirmed structurally, not just by inventory count.

### Mechanisms explored, and why they were set aside

Two alternative mechanisms were investigated directly (not just discussed) before returning to `pgrep`:

- **`git`-native locking** (a dedicated commit per attempt, atomicity via ref-update CAS, "only one wins
  the latest commit" as leader election) — raised again in this discussion, same verdict as
  [Addendum 9](atomic-step-protocol-design-addendum-9.md) reached for the mailbox-vs-notes question:
  `mkdir` already solves the momentary-lock problem for free, with no repository, no commit churn, and no
  cleanup discipline beyond what already exists. Git-native locking is not needed here either.
- **Unix domain socket bind** — a real candidate (Dean's own proposal: bind a socket, the OS releases the
  bind automatically if the process dies, avoiding a lingering-lock-file problem entirely). Tested
  directly, not assumed: **a SIGKILL'd process's socket *file* does NOT disappear from disk** — only the
  kernel's internal bind is released; a fresh bind attempt against the stale file fails with
  `EADDRINUSE` until something unlinks it first. Worse, testing the natural detection method (`connect()`
  to check if anything is still listening) produced a **false positive** — a successful connect to a
  socket with zero live listeners, a real and non-obvious kernel-backlog subtlety that was not fully
  chased down before Dean redirected: *"go back to pgrep mechanism."* Recorded here so this path is not
  reattempted without knowing why it surprised us once already.
- **FD/EOF-based session-liveness detection** (`exec FD< <(:)`, a script blocking on `cat <FD` and reacting
  to the pipe's EOF when the session dies) — proposed as an alternative to the kill-switch specifically,
  but Dean's own framing puts it out of scope for the moment: *"the EOF mechanism is only [relevant] if
  the current kill switch is broken."* Since the kill-switch (`--origin-pid` + `kill -0`) itself was not
  found to be broken — only *absent* from old-interface processes that never had it — this mechanism is
  not needed to fix what was actually found. Kept as a candidate for later if the existing kill-switch
  mechanism itself is ever shown to fail while genuinely present.

### The corrected mechanism

- **Discoverability (was Guard 2, `pgrep`)**: unchanged in shape, corrected in key. `pgrep -f
  "session-snapshot[.]sh .*--session-id <session_id>"` (or the equivalent per-script pattern), matching
  on the stable session UUID instead of a pid that can change across a restart.
- **Momentary start-lock (was Guard 1, `mkdir`)**: unchanged in shape, corrected in key. `mkdir
  "${TMPDIR:-/tmp}/<script>.dedup.<session_id>"`, held only for the instant it takes to decide "am I the
  one starting this," released immediately after — **the lock is never held by the running script
  itself.** Dean's own restatement, confirmed as the intended model: *"the lock is only taken, per
  session, when checking if script is already running. multiple starts are bad."* There is no ongoing
  "holder" to go stale while a script runs — the running script is discovered via the `pgrep` check
  above, not via anything the lock tracks. This makes the retracted content's entire pid-based staleness
  design (§ above) moot, not merely wrong: staleness detection was solving for a "held lock" model that
  was never actually how the mechanism worked, once the identity key is corrected.
- **Kill-switch (unchanged, unrelated to the above)**: `--origin-pid <pid>` + `kill -0` each pass, exactly
  as designed in Addendum 7 — decoupled entirely from lock identity. A session's underlying process pid
  is re-derivable at any point the kill-switch needs to check; it is never used to *find* or *lock* the
  script, only to decide whether the owning session is still alive.

### The identity key generalizes: not every script keys on a Claude session

`session-snapshot.sh` keys on `session_id` because its own semantic is genuinely "one per session."
`sync-main-watch.sh` and `tick-shared-scan.sh` do not share that semantic — both are run by whichever
session currently acts as **sync**, and per Dean, verbatim: *"both sync-main and tier-2 tick are run by
sync__ — that is a logical id not a Claude session id. Whoever runs, runs under that ID."* So
`guard_acquire`'s key argument is not "always `session_id`" — it is **whatever logical identity
actually needs 'at most one,'** and for these two scripts that identity is a fixed, project-defined role
constant (e.g. `"sync"`), never derived from any particular Claude session at all. A different sync
session resuming ownership recognizes "already running" by matching the same role constant, not by
matching a session_id it never had in the first place. `guard_acquire`'s interface (`<name> <key>`)
already supports this without modification — a role-constant key is not a degenerate/special case of
the function, it is the same function applied to a different, equally valid identity axis.

### Still open, carried forward from the retracted content where still relevant

- The handle-registry idea (external cleanup without parsing `ps`) may still have value, but its
  original sketch (`<script-name>.<origin-pid>.<own-pid>`) needs re-keying on `session_id` before it's
  worth designing further — not done here.
- `checkpoint-specs-review.md`'s Finding 2 was raised against the retracted pid-based-staleness premise
  and needs re-examination against this corrected design, not blind carry-forward.
- Whether the other three named-in-CURRENT.md "old-interface" production loops share pid `16342`'s exact
  defect (no `--origin-pid` at all) or a different gap is not yet checked here.

---

## Retracted original content (kept for the record, not to be built as written)

The section below is the addendum's original text, dated 2026-08-16 before the correction. Preserved
intact rather than deleted, per this project's discipline that migration/correction is not removal.

## What prompted it

While drafting a retroactive Type 3 for the checkpoint-capture script family (`session-snapshot.sh`,
`tick-shared-scan.sh`, `sync-main-watch.sh`, others sharing the same guard pattern), Dean flagged that
Addendum 7's guard mechanism — despite being the first properly-designed version of this locking scheme
— might itself be worth questioning, not just documenting as settled: *"I feel most of the mechanisms we
need can be refactored as shared functions that all scripts can use. I feel the flock mechanism was a
bit complicated."* (The "flock" reference is to the pre-Addendum-7 mechanism it already superseded; the
underlying concern — is the current guard shape more complex than it needs to be — applies to the
`mkdir`+`pgrep` scheme Addendum 7 actually shipped, not literally to flock.)

Direct check confirmed the concern: the guard block (`dedup_dir`, the `mkdir`/`rmdir` pair, the stale-
reclaim check, the `pgrep -f ... | grep -qv "^$$\$"` liveness check) is implemented **near byte-
identically in at least three separate scripts** (`session-snapshot.sh`, `tick-shared-scan.sh`,
`sync-main-watch.sh`) — confirmed duplication, not a suspicion.

Dean's stated concerns, addressed in order below:

1. Cost discipline: *"cost is on script not model. Local compute is free."* — already the governing
   principle for the mailbox/broadcast design in
   [Addendum 9](atomic-step-protocol-design-addendum-9.md); this addendum applies the same discipline
   to the guard mechanism.
2. Daily caps matter everywhere background mechanisms run, and cheap-model-for-mechanical-work is a
   real experience: *"It cost $500 when I left it on!"* — validates the original Tier-1/Tier-2 free/cheap
   split's motivation; not itself a change to this addendum's scope, recorded so the motivation is not
   lost.
3. Dislike of lingering/fragile lock files, especially breakage on `/tmp` being cleared (WSL restart):
   *"I don't like it if the mechanism breaks when I clean /tmp."*
4. A git-native alternative was raised (*"we are already using git for lock safety, may be easier...
   use commits to get atomicity or leader election — only one wins latest commit"*) and evaluated
   directly against the two distinct sub-problems below, not accepted or rejected wholesale.

## Two sub-problems, evaluated separately

**Sub-problem A — the instant-race case** (two instances launching within milliseconds of each other).
**Kept as-is: `mkdir`, unchanged.** `mkdir` is already atomic at the filesystem level (the same
primitive `.git/index.lock` itself is built on), needs no repository, no commit, no cleanup discipline
beyond what already exists, and — checked directly, not assumed — the current mechanism **already**
holds the guard only briefly ("held only during startup, removed inline," per Addendum 7's own text),
so the "lingering lock" worry does not actually describe this case. A git-commit-based leader election
was considered for this sub-problem specifically and rejected: it would add object churn and a
commit/cleanup discipline to something that happens on every session start, for a race window `mkdir`
already closes for free.

**Sub-problem B — stale-guard detection** (a holder died between `mkdir` and its own `rmdir` — SIGKILL,
OOM, an abrupt sleep). **This is where the current design was genuinely weak, and where it changes.**
Today's mechanism is purely time-based: if the guard directory's mtime is over a week old, assume the
holder is dead and reclaim. Weak because age is a *proxy* for death, not proof — and, worked through
explicitly with Dean, the actual protection this exists for is narrow and specific: *"this is for a rare
exit/error while still holding the lock. A new script trying to obtain the lock is the one checking for
a stale lock."*

**Decided: pid-based liveness as the primary signal, mtime-age kept as a fallback, not replaced.**

- The guard directory records its holder's own pid (a small file inside it, written right after the
  `mkdir` succeeds).
- A new script attempting to acquire an already-held guard reads that pid and checks `kill -0
  <held-pid>` — if genuinely dead, reclaim **immediately**, not after a week. This reuses a primitive
  the codebase already relies on elsewhere (`--origin-pid`'s own dead-man's-switch check), so it is not
  a new kind of check being introduced, just applied one layer earlier.
- **The one real risk, named rather than glossed over: pid reuse.** If the dead holder's pid is reused
  by an unrelated process before the next acquisition attempt runs, `kill -0` would report "alive" for
  the wrong process, and the stale guard would never be reclaimed by the pid check alone. **The
  existing mtime-age threshold (1 week, unchanged) stays as the fallback for exactly this case** —
  correctness in the common case (pid genuinely dead → immediate reclaim), with the worst case bounded
  to *no worse than today's existing behavior* (falls back to the same week-long wait Addendum 7 already
  accepted), never worse. Explicitly the reasoning that closed this question: *"this is better but need
  to understand what protection we are talking about... using pid is better than mtime — agree."*

## Shared library — deduplicate now, not later

**Decided: factor the guard logic into one shared file, `scripts/lib/single-instance-guard.sh`,
sourced by every script in this family**, rather than writing a retroactive spec (or any further code)
against three independent copies that are about to change shape anyway (per Sub-problem B's revision).
Refactoring now — rather than scoping it as a separate later task — avoids documenting duplication that
is already known to be wrong and already being revised in this same pass.

Interface sketch, not finalized in detail (the coder assigned this work fills in the exact shape):

```
guard_acquire <name> <origin-pid>   # mkdir + write-pid; on failure, run the pid-then-mtime staleness
                                     # check, reclaim if warranted, retry once; return non-zero + a
                                     # clear stderr message if still held after that
guard_release <name>                 # rmdir, idempotent if already gone
```

Every caller (`session-snapshot.sh`, `tick-shared-scan.sh`, `sync-main-watch.sh`, and any future script
needing the same single-instance property) sources this file and calls these two functions instead of
inlining the `mkdir`/`pgrep`/staleness logic itself.

## Handle registry — additive, not a replacement for self-checking

The existing `--origin-pid` + `kill -0` dead-man's-switch (each loop checks whether *its own* origin
session is still alive, and self-exits with a final drain if not) is **correct and stays exactly as
designed** — Dean's own words: *"self-check stays (it's correct)."* What's added is a second, independent
mechanism for a different consumer: a human or an external cleanup pass that wants to find and reap
running checkpoint scripts **without needing to know each script's own internal liveness logic**.

**Decided: a lightweight handle registry**, one small file per running instance in a known directory
(e.g. `/tmp/checkpoint-handles/<script-name>.<origin-pid>.<own-pid>`), written on start, removed on
clean exit. An external reaper (a script, or a human running one command) can then list that directory,
check each handle's own-pid for liveness, and kill/clean up anything whose process is actually gone
without ever needing to parse `ps` output for script-specific argv patterns (which is what
`kill_stale_or_orphaned` logic would otherwise have to do today, per the same `pgrep -f
"<script>[.]sh .*--origin-pid <pid>"` pattern already used three times for the acquisition-time
liveness check). This is additive — closes the gap Dean named (*"all scripts must create handles in
some dir, so cleanup can find them"*) without touching or weakening the self-check that already
correctly handles the common case.

## Still open

- **Exact registry directory/naming and whether the reaper is a script, a skill, or a manual command**
  — not decided, deliberately deferred until the shared-library refactor itself is built and the actual
  interface between `guard_acquire`/`guard_release` and a registry entry is concrete.
- **Whether the registry entry and the guard-directory pid-file are the same artifact or two separate
  ones** — plausibly the same file could serve both purposes (acquisition-time staleness check, and
  external-reaper discoverability), but this is an implementation detail for whoever builds
  `single-instance-guard.sh`, not resolved here.
- **This addendum's own content still needs to be folded into a revised
  [`checkpoint-capture-spec.md`](checkpoint-capture-spec.md)** before any coder touches the affected
  scripts — the spec draft that existed before this design discussion documented the *old* (duplicated,
  mtime-only) mechanism and needs revision to match this addendum, not extension.
