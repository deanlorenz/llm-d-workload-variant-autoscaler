# Addendum 10 — checkpoint-guard redesign: pid-based staleness, shared library, handle registry

**Amends** [`atomic-step-protocol-design-addendum-7.md`](atomic-step-protocol-design-addendum-7.md)
(single-instance guards and drain-before-exit) and, by extension,
[`atomic-step-protocol-design-addendum-2.md`](atomic-step-protocol-design-addendum-2.md) (the original
flock guard Addendum 7 superseded). Addendum 7 is **not edited**: this is a further amendment on the
same mechanism, triggered by Dean questioning the mechanism's shape while a retroactive Type 3 spec for
this script family was being drafted.

**Status: decided 2026-08-16. Not yet built — this is the design the pending retroactive spec
([`checkpoint-capture-spec.md`](checkpoint-capture-spec.md)) will document once revised to match.**

## At a glance

**Mission:** the guard mechanism from Addendum 7 is duplicated near-identically in 3+ scripts and has
a weak staleness signal (mtime-only). Fix both.

**Approach:**
- Keep `mkdir` for the instant-race case (already correct, already cheap).
- Staleness detection upgraded: pid-alive check (`kill -0`) as primary signal, existing mtime-age
  threshold kept as fallback for the pid-reuse edge case — never worse than today, better in the
  common case.
- Git-native locking (commit-race leader election) considered and rejected for this — `mkdir` already
  solves it for free.
- Deduplicate into `scripts/lib/single-instance-guard.sh`, sourced by every affected script.
- Additive handle registry so external cleanup can find running instances without parsing `ps`.

**Needs you:** nothing right now.

**Checklist:**
- [ ] Build `single-instance-guard.sh`.
- [ ] Migrate `session-snapshot.sh`, `tick-shared-scan.sh`, `sync-main-watch.sh` to use it.
- [ ] Design the handle registry's exact path/naming (open).
- [ ] `checkpoint-capture-spec.md` and `sync-watchers-spec.md` already revised to reflect this.

---

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
