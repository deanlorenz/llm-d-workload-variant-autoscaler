# Code spec — checkpoint capture (Tier-1/Tier-2, session-start hook)

**code spec** · **Status: DRAFT — mixed retroactive and forward-looking, revised 2026-08-16.**

## At a glance

**Mission:** document the six checkpoint-capture scripts as they exist, and specify the shared guard
library (Addendum 10, **retracted-then-corrected** 2026-08-16) they should be rewritten to use — keyed
on logical identity (session_id, or a fixed role constant), never on a process pid.

**Approach:**
- S0/S0b — new: `scripts/lib/single-instance-guard.sh` (momentary mkdir+pgrep lock, keyed on whatever
  logical identity the caller needs — a session_id for per-session scripts, a fixed role constant like
  `"sync"` for shared-instance scripts) and an additive handle registry (needs re-keying, not yet
  designed in detail). Build first; everything else depends on it.
- S1 `session-extract.sh` — unchanged, no defect.
- S2 `session-snapshot.sh` — Tier-1, free, one per **session**. Needs a new `--session-id` argument;
  guard block must source S0, keyed on `session_id`.
- S3 `tick-consolidate.sh` — Tier-2, cheap-model. No defect.
- S4 `tick-shared-scan.sh` — shared Tier-2, one instance **system-wide** regardless of which sync
  session owns it. Guard block must source S0, keyed on the fixed role constant `"sync"`, not any
  session_id. Never run live yet.
- S5 `tick-live-index.sh` — session identity snapshot. No defect.
- S6 `tier1-session-start.sh` — `SessionStart` hook. Contains Defect 1; also needs to start passing
  `--session-id` once S2 requires it.

**Needs you:** nothing blocking. Defect 1 (hook omits a required flag, would fail every invocation if
ever wired up) is documented for whoever picks this up; the hook itself still needs your explicit
approval before it's wired into `container-settings.json` at all (per Addendum 7's own "Still open"
list), separate from fixing the bug.

**Checklist:**
- [ ] Build S0/S0b (`single-instance-guard.sh`, keyed on logical identity; handle registry re-keyed,
  not yet designed).
- [ ] Migrate S2 (session_id key) and S4 (fixed `"sync"` key) to source it.
- [ ] Add `--session-id` to S2 and S6's launch of it.
- [ ] Decide + fix Defect 1's `--digest` gap (seed a digest file with a marker, or leave hook-started
  sessions deliberately unregistered for Tier-2 — a decision, not a mechanical flag add).
- [ ] Fix Defect 1 in S6 (`--origin-pid "$PPID"`), verify `$PPID` is really the session's own pid in a
  `SessionStart` hook context.
- [ ] Fix S6's stale header comment (still describes the superseded flock mechanism).
- [ ] Behavioral verification per Addendum 7's checklist before any production restart.
- [ ] Your call, separately: approve wiring S6 into `container-settings.json`.

Most of this spec documents what already exists, closing the governance gap
[`atomic-step-protocol-design-addendum-7.md`](atomic-step-protocol-design-addendum-7.md) already
diagnosed in its own postmortem: *"Root cause: no written purpose statement to check the code against, so
the template was existing code rather than intent."* **The guard mechanism specifically (S2/S4's
single-instance logic) is forward-looking, not retroactive** — it documents the redesign decided in
[`atomic-step-protocol-design-addendum-10.md`](atomic-step-protocol-design-addendum-10.md), not the
mechanism currently shipped. A coder assigned this spec is building toward Addendum 10's design for the
guard, and documenting-as-is for everything else. Do not assume every step below describes code that
already exists — S2 and S4 name explicitly what changes.

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then read only the step covering the script you're
reviewing or touching — by heading, not by line number.

---

## Intent

**intent** — Get the user's own words durably onto disk as a session runs, cheaply enough that an idle
session costs nothing, with a rare, cheap-model consolidation pass folding new content into a durable
digest. Two tiers, deliberately split by cost: Tier-1 (`session-snapshot.sh`, `session-extract.sh`) is
free — shell-only, no model, no request. Tier-2 (`tick-consolidate.sh`, and its shared-scan variant
`tick-shared-scan.sh`) is rare and cheap — a small model, invoked only when Tier-1's count-check finds
something new. `tier1-session-start.sh` is the `SessionStart` hook meant to auto-arm Tier-1 without
relying on a session reading `CONVENTIONS.md` and remembering to start it manually — that reliance
already failed once (see its own header comment). `tick-live-index.sh` is a separate, later addition:
a machine-readable snapshot of every session's self-declared identity, for staleness detection and
handoff-routing (design in
[`atomic-step-protocol-design-addendum-3.md`](atomic-step-protocol-design-addendum-3.md)).

**current call stack, as-built (2026-08-16), not as originally planned:**

```
SessionStart hook            → tier1-session-start.sh (NOT wired into any hook config — see Defect 1)
                                  → session-snapshot.sh --origin-pid <pid> --out <digest>.raw.md --file <transcript>
                                       (free: extracts new turns via session-extract.sh, appends, advances marker)
                                       (optionally, every --consolidate-every passes: calls tick-consolidate.sh)
shared Tier-2, sync-owned      → tick-shared-scan.sh --origin-pid <pid>
                                  (scans session/.tier2-registry, retires stale entries, calls
                                   tick-consolidate.sh per session with new content, tracks a daily
                                   token cap in session/.tier2-usage.log)
live-session snapshot          → tick-live-index.sh (reads session/status/*.md identity blocks,
                                  computes age-based and peer-comparison staleness)
```

**Defect 1, live, found while writing this spec, not yet fixed.** `tier1-session-start.sh` calls
`session-snapshot.sh` **without** `--origin-pid` (line 46 of that script, as of this writing) — but
`session-snapshot.sh` requires that flag unless `--once` is passed (validated at its own argument-parsing
stage; missing it is a hard `die`). This means **the hook, if ever wired up, would fail every single
invocation.** It has not bitten anyone because — per
[`atomic-step-protocol-design-addendum-7.md`](atomic-step-protocol-design-addendum-7.md)'s own "Still
open" list — the `container-settings.json` hook entry needed to actually fire this script has never been
applied. `tier1-session-start.sh`'s own header comment (line 15-18) also still describes
`session-snapshot.sh` as carrying "its own per-transcript flock" — stale, describing a mechanism that
existed before Addendum 7 replaced flock-based locking with the `--origin-pid` + mkdir/pgrep dual guard
across this whole script family. Both are documentation/wiring defects, not found by any prior review
because none has happened — recorded here for the coder assigned to fix them, not fixed by the planner
directly.

**new components** — one: `scripts/lib/single-instance-guard.sh`, a shared library extracting the
near-identical guard blocks currently duplicated across `session-snapshot.sh`, `tick-shared-scan.sh`,
and `sync-main-watch.sh` (the latter is out of this spec's own scope — see
[`sync-watchers-spec.md`](sync-watchers-spec.md) — but sources the same shared file once it exists, so
this spec's S0 below is a genuine dependency for that spec too). Everything else in this spec governs
already-shipped scripts; its remaining output is whatever fixes a coder makes against Defect 1 and any
design-review findings.

**new conventions** — `checkpoint-capture` was already identified as a harvest candidate in
[`harvest-classification.md`](harvest-classification.md) row C1/C2 (`conv:checkpoint-capture`, sourced
from `session/CONVENTIONS.md` § Checkpoint capture). This spec does not re-harvest; it documents the code
that convention describes.

---

## Prerequisites

No new worktree — all six scripts already live in `plans/scripts/`, on the `plans` branch. A coder
assigned a fix here works directly in `plans/`, per the normal coder worktree-scope rules (not an orphan
branch — these scripts are already part of `plans`'s own tree, unlike the still-isolated
`plans-tooling` lineage).

**Gates** — `bash -n <script>`; `shellcheck` if installed; behavioral verification per
[`atomic-step-protocol-design-addendum-7.md`](atomic-step-protocol-design-addendum-7.md)'s own "Verification
required before production restart" checklist (two simultaneous launches → exactly one survivor; a
planted stale guard is reclaimed; a planted fresh guard is respected; origin-death triggers final work
then exit; normal start releases its guard while the loop runs) for any change touching the guard
mechanism specifically. No Go, no DCO, no `make test` — this is shell tooling on the `plans` lineage.

---

## Step index

**S0 — `scripts/lib/single-instance-guard.sh` (new, forward-looking, corrected 2026-08-16).**
Extracts the guard logic currently duplicated in `session-snapshot.sh` and `tick-shared-scan.sh` (and,
out of this spec's scope, `sync-main-watch.sh`) into two shared functions, per the **corrected design**
in [`atomic-step-protocol-design-addendum-10.md`](atomic-step-protocol-design-addendum-10.md) — that
addendum's original pid-keyed design is **retracted**; do not build against it.

```
guard_acquire <name> <key>          # pgrep liveness check on <key> + mkdir-based atomic dedup, both
                                     # keyed on whatever logical identity actually needs "at most one"
                                     # for this caller -- a Claude session_id for session-snapshot.sh
                                     # (stable across resume/reload/wake), or a fixed project-defined
                                     # role constant like "sync" for scripts that are meant to have
                                     # exactly one shared instance regardless of which session started
                                     # it (tick-shared-scan.sh, sync-main-watch.sh -- see
                                     # sync-watchers-spec.md). NEVER a process pid, in either case. The
                                     # lock is momentary: mkdir is taken only for the instant it takes
                                     # to decide "am I the one starting this," and released immediately
                                     # after (whether starting or standing down) -- it is never held by
                                     # the running script itself. There is no staleness check to design
                                     # here: since the guard is never held long, there is no "holder"
                                     # that can go stale mid-run.
guard_release <name>                 # rmdir, idempotent if already gone. Called at the same startup
                                     # moment as guard_acquire, not on exit -- see the note below on
                                     # why this is not a lifetime-held lock.
```

**Discoverability** (whether a copy is already running, for `guard_acquire` to check) is `pgrep -f
"<script>[.]sh .*<key-bearing-flag> <key>"` — same shape as the existing `pgrep` check, corrected to
match on the caller's actual identity key (`session_id`, or a fixed role constant) instead of
`$origin_pid`. `--origin-pid` is **not removed** from any script's own argument list — it stays
exactly as designed, but it now does exactly one job (the kill-switch's
`kill -0` check in each script's main loop), fully decoupled from this guard's identity key.

The `<script>` half of the pattern is derived, not hand-typed per call site: the calling script's own
basename with `.sh` stripped (e.g. `session-snapshot.sh` → `session-snapshot`), so `guard_acquire`
takes the script name as an explicit argument rather than a coder re-deriving or hardcoding it per
caller — `guard_acquire <script-name> <key-flag> <key>`. The escaped `[.]sh` (not `.sh`, which matches
any character) is load-bearing, per Addendum 7.

The pgrep match must exclude the calling process's own pid, via `| grep -qv "^$$\$"` **evaluated inside
the sourced function itself** — `$$` resolves to the sourcing script's own pid because `source` doesn't
fork, so this is correct as written, but only as long as no coder "fixes" it into `$BASHPID` or a
subshell-captured value (either would silently break the self-exclusion). This exact bug — pgrep-only
dedup with no working self-exclusion — is what left **zero** survivors on two simultaneous launches
(4/4) during Addendum 7's own verification; state this constraint as a code comment directly on the
`grep -qv` line, not only here, so a future edit can't drift from it unnoticed.

Must build first — S2 and S4 both source this file rather than inlining their own copies. **This is the
one step in this spec that is pure new code, not a fix to something shipped.**

**S0b — handle registry (new, forward-looking, additive, needs re-keying).** The original sketch (a
small file per running instance, naming `<origin-pid>.<own-pid>`) inherited the same wrong identity
key as S0's original design and needs re-keying on `session_id` before it is built — not designed in
detail here. Purpose is unchanged: a second, independent mechanism so an external cleanup pass or a
human can find and reap running instances without parsing `ps`/`pgrep` output for script-specific argv
patterns. **Does not replace or weaken the existing `--origin-pid`/`kill -0` dead-man's-switch** — that
stays exactly as designed, in every script, unchanged by any of this. No reaper script is specified by
this step; building one is left open, not required for S0/S0b to be considered done.

**S1 — `session-extract.sh` (mechanical read-side, unchanged, no defect found).** Pulls genuine
user-authored turns (plain-string `user` records and mid-turn `queue-operation`/`enqueue` records,
deduplicated) out of a transcript JSONL, optionally bounded `--since` a timestamp. `--list` identifies
transcripts by their opening prompt. `--count`-only mode exists so a caller can check "is there anything
new" without pulling text into context. Gated by `session/.tick-disabled` unless
`SESSION_EXTRACT_ALLOW=1` is set (the kill-switch for the retired single-cron mechanism; Tier-1 and
Tier-2 both set this env var to opt past it, since they are the replacement, not the thing being
disabled). No defect found in this pass — reviewed for currency against Addendum 7's changes and found
unaffected (it has no lifecycle of its own; it is a pure, stateless extraction function called by both
tiers).

**S2 — `session-snapshot.sh` (Tier-1, free, per-session).** Detached loop, one per session, appends new
turns to a raw sidecar (`session/digests/<topic>.raw.md`), advances its own marker, never commits (a
crash or sleep loses nothing already written). Self-registers `(transcript, digest)` pairs into
`session/.tier2-registry` for the shared Tier-2 scanner to discover — best-effort, must never block
Tier-1's free-path guarantee (a registry-write failure is swallowed, not raised). `--origin-pid <pid>`
dead-man's-switch (checked with `kill -0` each pass) stays exactly as designed, unchanged — it
identifies whether the *owning Claude process* is still alive, nothing else. **Guard mechanism
changes, corrected 2026-08-16**: today this script inlines its own `mkdir`/`pgrep` block keyed on
`$origin_pid` — the wrong identity key, since a session's pid can change across a resume while the
logical session persists. Per S0's corrected design, this script needs a **new required argument,
`--session-id <session_id>`** (the Claude session's own stable UUID, separate from and in addition to
`--origin-pid`), and must be rewritten to source `single-instance-guard.sh`, calling
`guard_acquire "session-snapshot" "$session_id"` / `guard_release` — keyed on session_id, never on any
pid. **Consumer of Defect 1 above** — this script's own contract (require `--origin-pid` unless
`--once`) is correct and unchanged; the defect is entirely in its caller, `tier1-session-start.sh`
(S6), not here. Same caller also needs to start passing `--session-id`, since the hook payload
already carries `session_id` (confirmed in S6's own code).

**Contained Defect 2 in its non-guard logic (`pass()`'s marker derivation), found and fixed
2026-08-16 — the guard-mechanism review had no findings here, but this script's own marker logic
did.** `pass()` advanced its marker to the last line matching `grep '^## '` in the extracted text —
but a user turn's own body can contain a markdown heading (`## Verdict`, `## Findings`, …), which
that grep cannot distinguish from the extractor's own `## <timestamp>` heading. Two live loops
were poisoned this way (confirmed live, not hypothetical): `.atomic-step-protocol-brainstorm.raw.md.mark`
held the literal string `Findings`, and a second loop's marker was never written at all because its
transcript's very first extraction ended on a `## `-headed user turn. Both then called
`session-extract.sh --since <garbage>`, which matched nothing, forever — indistinguishable from
"genuinely caught up," `rc 0`, no error. **Fixed**: the marker candidate must match the extractor's
actual heading shape (`## ` followed by an ISO-8601 timestamp), not merely start with `## `; a pass
with no such candidate leaves the marker untouched and logs a distinct, loud warning rather than
silently advancing to nothing. Poisoned markers repaired by hand for the affected loops (the fix
alone does not retroactively un-poison an already-corrupted marker file).

**S3 — `tick-consolidate.sh` (Tier-2, per-session, cheap-model).** Invoked by S2 (via
`--consolidate-every`) or by the shared scanner S4. Sends only the new-since-marker turns to a small
model (default `aws/claude-haiku-4-5`) from a neutral `cd /tmp` (so the model never inherits this
project's `CLAUDE.md` chain, keeping the call genuinely cheap), asking it to classify each turn
KEEP/SKIP with a category and label — never to paraphrase, since the script splices the *original* text
back in verbatim for anything KEPT. Advances the digest's "Captured through" marker; commits the digest
file itself (the one place in this family that does commit, since durability-by-commit is explicitly
this tier's job, not Tier-1's). No defect found.

**S4 — `tick-shared-scan.sh` (Tier-2, shared, sync-owned).** Supersedes N independent per-session Tier-2
loops with one shared scanner reading `session/.tier2-registry`, retiring transcripts stale beyond
`--retire-days` (default 7, with self-healing wake-up if a retired transcript's mtime moves again), and
tracking a combined daily token cap (`--daily-cap`, default 50000) in `session/.tier2-usage.log` as a
backstop against a runaway loop, not a tight budget. Same `--origin-pid` dead-man's-switch as S2 for
the *kill-switch* only, unchanged — tied to whichever sync session currently owns this instance.

**Guard mechanism, corrected 2026-08-16 — a different identity axis from S2, and a general point
worth stating once here.** This script and `sync-main-watch.sh` (out of this spec's scope, see
`sync-watchers-spec.md`) are both **run by whichever session is currently acting as sync — a logical
role ID, not a Claude session_id.** Per Dean, verbatim: *"both sync-main and tier-2 tick are run by
sync__ — that is a logical id not a Claude session id. Whoever runs, runs under that ID."* This is not
a degenerate "no key" case, and not the same fix as S2 — it is the same general principle
(`guard_acquire`'s key is whatever logical identity actually needs "at most one") applied to a
different identity than a Claude session: `guard_acquire "tick-shared-scan" "sync"` — a **fixed,
project-defined role constant**, not derived from any session at all, so a different sync session
resuming ownership recognizes "already running" without needing to match its own session_id or any
other per-instance value. Must source `single-instance-guard.sh` (S0) rather than inlining its own
copy of the guard block, same mechanism as S2, keyed differently. Explicitly not yet started for real
on this machine as of this writing (per `atomic-step-protocol-design-addendum-8.md`'s own tracking) —
built and sandbox-verified, never run live; the S0 rewrite should land before its first real run, not
after. No other defect found in the script's non-guard logic; its non-running status is an operational
gap, not a code defect.

**S5 — `tick-live-index.sh` (session identity snapshot, standalone).** Scans `session/status/*.md` for
the identity block (added to `CONVENTIONS.md` 2026-08-13), computing two staleness signals: absolute
mtime age (shared `--stale-days` threshold with S4, deliberately one number not two) and peer-comparison
(a session whose identity block hasn't moved while its cohort has recently checked in, flagged even
before the absolute threshold fires). `--format json` (default) or `table`. No defect found; verified
2026-08-13 against both real (no-identity-block) and synthetic (fresh + stale) status files.

**S6 — `tier1-session-start.sh` (`SessionStart` hook, not wired up, contains Defect 1).** Fires on every
`SessionStart` source (startup/resume/clear/compact/fork) — deliberately unconditional, per
`CONVENTIONS.md`'s own unconditional "what every session does" framing — and is meant to auto-start S2
for that session's own transcript, keyed by `session_id` rather than a human-chosen topic name. Reads
the hook's JSON payload (`session_id`, `transcript_path`, `cwd`) from stdin; no-ops loudly (logs to
`/tmp/tier1-session-start.log`) on a malformed payload rather than guessing. **Contains Defect 1**: the
`nohup bash "$script" --out "$digest" --file "$transcript" --interval 120` call omits `--origin-pid`,
which S2 requires. Fix is mechanical — pass `--origin-pid "$PPID"` (the hook process's own parent, i.e.
the Claude session that triggered `SessionStart`) — but is a real behavioral change to verify, not a
one-line edit to apply blindly: confirm `$PPID` inside a `SessionStart` hook's execution context is
actually the session's own pid and not some intermediate shell, since a wrong pid here would make S2's
`kill -0` dead-man's-switch check the wrong process and either never fire (leak) or fire immediately
(the loop dies right away). Also carries the stale header-comment defect noted in `## Intent` above —
fix by rewriting the comment to describe the current `--origin-pid` guard, not the superseded flock.
Per this spec's new `--session-id` requirement on S2, the same launch line also needs
`--session-id "$session_id"` added (the hook payload already carries this field — no new lookup
needed) so S2's guard has a key to acquire on at all once the S0 migration lands.

**Defect 1 also omits `--digest`, found in design review (`checkpoint-specs-review.md` Finding 5) —
not a second flag to bolt on blindly.** The launch line builds only a `--out <digest>.raw.md` sidecar
path; without `--digest`, S2's Tier-2 self-registration never fires (`session-snapshot.sh` gates
registration on both `$tfile` and `$digest` being non-empty) and `--consolidate-every` can never
trigger either. This isn't a one-flag mechanical fix: `tick-consolidate.sh` hard-dies without a digest
file that already carries a "Captured through:" marker, so fixing this means deciding — before a
coder touches it — whether the hook should also create/seed a digest file with that marker, or leave
hook-started sessions deliberately without Tier-2 registration. **Left as an explicit open decision
for whoever picks up this defect, not resolved here.**
Also **not wired into `container-settings.json`** — per Addendum 7's own "Still open" list, applying that
hook entry needs Dean's explicit approval, separate from fixing the script's own bug.
