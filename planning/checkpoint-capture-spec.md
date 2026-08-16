# Code spec — checkpoint capture (Tier-1/Tier-2, session-start hook)

**code spec** · **Status: DRAFT — mixed retroactive and forward-looking, revised 2026-08-16.** Most of
this spec documents what already exists, closing the governance gap
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

**S0 — `scripts/lib/single-instance-guard.sh` (new, forward-looking).** Extracts the guard logic
currently duplicated in `session-snapshot.sh` and `tick-shared-scan.sh` (and, out of this spec's
scope, `sync-main-watch.sh`) into two shared functions, per
[`atomic-step-protocol-design-addendum-10.md`](atomic-step-protocol-design-addendum-10.md):

```
guard_acquire <name> <origin-pid>   # mkdir-based atomic dedup + pgrep liveness check, unchanged from
                                     # Addendum 7 for the instant-race case; on finding an existing
                                     # guard, checks its recorded holder pid via kill -0 first
                                     # (immediate reclaim if genuinely dead), falling back to the
                                     # existing 1-week mtime-age threshold only if the pid check is
                                     # inconclusive (pid reused by an unrelated process) -- retries
                                     # acquisition once after a reclaim, returns non-zero with a clear
                                     # stderr message if still held after that.
guard_release <name>                 # rmdir, idempotent if already gone.
```

Must build first — S2 and S4 both source this file rather than inlining their own copies. **This is the
one step in this spec that is pure new code, not a fix to something shipped.** Also owns writing the
holder's own pid into the guard directory at acquisition time (a small file inside it), since that pid
is what the staleness check in a later acquisition attempt reads.

**S0b — handle registry (new, forward-looking, additive).** Per the same addendum: each script sourcing
`single-instance-guard.sh` also drops a small file naming its own pid and origin-pid into a known
directory (exact path/naming not finalized in the addendum — coder's call, document the choice made) on
start, removed on clean exit. **Does not replace or weaken the existing `--origin-pid`/`kill -0`
dead-man's-switch** (each loop still self-checks its own origin session, unchanged) — this is a second,
independent mechanism so an external cleanup pass or a human can find and reap running instances without
parsing `ps`/`pgrep` output for script-specific argv patterns. No reaper script is specified by this
step — building one (or deciding it's a manual `ls` + `kill` command instead) is explicitly left open by
Addendum 10 and not required for S0/S0b to be considered done.

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
dead-man's-switch (checked with `kill -0` each pass) stays exactly as designed, unchanged. **Guard
mechanism changes**: today this script inlines its own `mkdir`/`pgrep`/mtime-only staleness block;
per S0, it must be rewritten to source `single-instance-guard.sh` and call `guard_acquire`/
`guard_release` instead, gaining the pid-based staleness check and the handle-registry drop as a
byproduct. **Consumer of Defect 1 above** — this script's own contract (require `--origin-pid` unless
`--once`) is correct and unchanged; the defect is entirely in its caller, `tier1-session-start.sh`
(S6), not here.

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
backstop against a runaway loop, not a tight budget. Same `--origin-pid` dead-man's-switch as S2,
unchanged. **Same guard-mechanism change as S2**: must be rewritten to source
`single-instance-guard.sh` (S0) rather than inlining its own copy of the guard block. Explicitly not yet
started for real on this machine as of this writing (per `atomic-step-protocol-design-addendum-8.md`'s
own tracking) — built and sandbox-verified, never run live; the S0 rewrite should land before its first
real run, not after. No other defect found in the script's non-guard logic; its non-running status is
an operational gap, not a code defect.

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
Also **not wired into `container-settings.json`** — per Addendum 7's own "Still open" list, applying that
hook entry needs Dean's explicit approval, separate from fixing the script's own bug.
