# Addendum 2 — shared Tier-2 checkpoint consolidation across live sessions

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (**design**, FINAL, frozen
2026-08-10), specifically its § Checkpoint capture content as inherited into
[`session/CONVENTIONS.md`](../session/CONVENTIONS.md). The parent is **not edited**: this is the
amendment channel it names. Additive; governs where the two overlap.

**Status: decisions confirmed by Dean 2026-08-13; scripts built and sandbox-verified same day,
not yet handed to a live sync session.**

## At a glance

**Mission:** replace N independent per-session Tier-2 loops with one shared, sync-owned scanner.

**Approach:**
- Tier-1 unchanged (free, per-session).
- One shared `tick-shared-scan.sh`, owned/started/monitored by the sync session — pauses when no
  sync session is active, next one restarts it.
- Retirement bounds the scan (stale >7 days → one final sweep → marker → self-heals on wake).
- Daily token cap (50k combined) as a bug backstop, not a tight budget.
- Guard mechanism superseded by [Addendum 10](atomic-step-protocol-design-addendum-10.md) — see that
  doc, not the flock described here originally.

**Needs you:** authorize starting the shared loop for real (never has been — sandbox-only so far).

**Checklist:**
- [x] Rebuild guard per Addendum 10 before first live run — done, `f9e1dba6`, 2026-08-16.
- [ ] Hand ownership to a live sync session.
- [ ] Authorize the first real start.

---

## What prompted it

Two things surfaced in the same conversation:

1. **A reading list got "lost."** It never actually was — it lives, committed, in
   [`session/digests/atomic-step-protocol-brainstorm.md`](../session/digests/atomic-step-protocol-brainstorm.md)
   (commit `e8b47c46`). The real gap: nothing pointed a fresh session at it. `CURRENT.md` has zero
   reference to this digest, by the parent design's own rule (a designer session cannot write
   CURRENT.md; reaching it needs a `sync__` handoff, which was never sent for this thread). Separately,
   `session/.tick-disabled` is still present on disk with a commit message reading literally "retire the
   scheduled checkpoint tick" (`a8a9aa36`, 2026-08-11) — which is accurate for the *old* single-cron
   mechanism, but reads as a blanket retirement and contradicts the same digest's later, same-era ruling
   that **the (redesigned, two-tier) tick should run in every session** (Dean, verbatim, digest line 62).
   Both loose ends are process bugs, not data loss: the content is safe, but nothing currently re-arms
   the tick per session and nothing currently tells a new session the tick's real status.
2. **Dean's actual ask:** *"Can we have one tick for all live sessions? this is mostly shell work +
   autonomic model work (not running in the session's context)."* — i.e. stop running N independent
   Tier-2 consolidation loops (one per session) when the work itself doesn't need to run inside any
   particular session's context.

## The amendment

**Tier-1 is unchanged.** It is already free (shell-only, no model call, no-ops on nothing-new) and
already per-session — there is no redundancy worth removing there. Only Tier-2 (the rare, cheap-model
consolidation step) centralizes.

### Ownership and lifecycle

- **The sync session owns, monitors, and (re)starts the shared Tier-2 loop.** Same detached-`nohup`
  pattern the parent design already uses for per-session Tier-1 loops — no new daemon machinery, no
  systemd unit, nothing outside the session/tool sandbox.
- **It is acceptable for the loop to pause when no sync session is active.** If it dies (crash, machine
  sleep, the owning sync session closing), it stays down until the next sync session notices and
  restarts it. This is a deliberate simplification — a true always-on daemon was considered and
  deferred; sync-session ownership is judged sufficient given how the sync session already exists to
  supervise shared state (per the single-writer model this design's parent doc otherwise doesn't touch).

### Session discovery and retirement

- **No liveness protocol.** The shared loop enumerates every session transcript it can find (across
  worktrees) and runs Tier-1's free count-check against each. A transcript with nothing new costs
  effectively nothing to check, so there is no need to distinguish "open" from "closed" sessions before
  checking.
- **Retirement bounds the scan as sessions accumulate.** A session whose transcript mtime is stale for
  **more than one week** gets exactly one final consolidation sweep (catching any tail content), then a
  marker file `session/.retired/<session-id>` excludes it from future scans.
- **Retirement self-heals.** On every scan, if a retired session's transcript mtime has moved past the
  threshold again (the session "woke up"), its marker file is deleted and it rejoins the normal pool —
  no explicit un-retire step, no separate code path.
- **Subtraction is a sorted-list diff** — enumerate all transcript IDs, enumerate all marker-file IDs,
  `comm -23` (or equivalent) between them. Good enough at local shell scale (tens to low hundreds of
  sessions); no index or database needed.
- Optionally, a session explicitly marked `DONE` (the `s-session-done` title-prefix convention) may be
  retired immediately regardless of mtime — not required for a first build, flagged as a cheap addition.

### Consolidation shape

- **Serialized, one cheap-model call per session with new content** — same per-session prompt/output
  shape as today's `tick-consolidate.sh`, just invoked in a loop by the shared owner instead of once per
  session. Batching several sessions into one call was considered and rejected: cross-contamination risk
  (one session's content bleeding into another's digest) and reduced cache benefit outweigh the modest
  reduction in fixed per-call overhead.
- Each session's consolidated output still lands in its own digest file,
  `session/digests/<topic>.md`, exactly as today — the shared loop does not change where output goes,
  only who triggers the write.

### Token budget — a backstop, not a tight allowance

Motivation: *"better monitor overall tokens used. stop tier 2 if too many tokens consumed."* The original
per-session tick was expensive because of re-upload cache misses on a 5-minute TTL, not because Tier-2's
own per-call cost was large (the digest measured **~488-token prompts, 9 useful calls out of 55 fired** on
the worst measured day). Centralizing removes the re-upload multiplication; the budget below exists to
catch a *bug* (e.g. many sessions going stale/thrashing at once, a malformed transcript causing a retry
storm) rather than to constrain ordinary use.

- **A running local counter, summed from actual per-call usage.** Each consolidation call's real token
  usage (prompt + completion, as returned by the call) is appended to a local ledger file (e.g.
  `session/.tier2-usage.log`, one line per call: timestamp + tokens). Before each new consolidation call,
  sum today's entries (filtered by date) and compare against the cap.
- **Cap: 50,000 tokens/day**, combined across all sessions' Tier-2 calls. Roughly 100× the single-day
  cost the digest measured (~488 tokens × ~9 useful calls). Generous enough not to trip on legitimate
  multi-session days; still catches a runaway loop calling far more often than intended.
- **On exceeding the cap:** skip consolidation for the remainder of the day (reset at UTC midnight, or
  whatever session-day boundary the shell scripts already use), and log why — a skipped session's Tier-1
  raw sidecar keeps accumulating untouched, so nothing is lost, only delayed to the next day's
  consolidation pass.

## What this does not change

- Tier-1 stays exactly as designed in the parent doc: free, per-session, model-free.
- The digest format, its "Dean's decisions / Key findings / Tasks listed / Open questions / Recap /
  Next" shape, and its deliberate exclusion from CURRENT.md are unchanged.
- The `.tick-disabled` kill switch still exists and still works as a per-worktree/per-session opt-out;
  this addendum does not remove it, only clarifies that its current commit message describes the retired
  *old* single-cron mechanism, not the redesigned two-tier one this addendum extends.

## Built and verified (2026-08-13)

- **`scripts/session-snapshot.sh`** gained a self-registration block: whenever it is started with both
  `--file` and `--digest`, it writes (or overwrites, keyed by transcript path) one tab-separated line
  `<ISO8601Z-registered-at>\t<transcript-path>\t<digest-path>` into `session/.tier2-registry`. Best-effort
  — a write failure there does not block Tier-1, which must stay free regardless of Tier-2's state.
  Verified: registering the same transcript twice with a different digest path overwrites in place
  (one line survives, pointing at the newer digest).
- **`scripts/tick-shared-scan.sh` (new)** — the shared Tier-2 loop. Reads `session/.tier2-registry`,
  de-duplicates to the latest registration per transcript, and for each pair not currently retired calls
  `tick-consolidate.sh --digest <dfile> --file <tfile>` (unchanged, per-session script, just invoked from
  a shared caller instead of from that session's own Tier-1 loop). Retirement markers live at
  `session/.retired/<sha256 of transcript path>` (stable, filesystem-safe key); the `--retire-days`
  threshold (default 7) and the daily token cap (`--daily-cap`, default 50000) are both flags, not
  hardcoded. Meant to be started detached (`nohup ... &`) by the sync session, same pattern as
  today's per-session Tier-1 loops; `--once` exists for testing without a live loop.
- **Token ledger** — `session/.tier2-usage.log`, one line per attempted model call
  (`<ISO8601Z> <tokens>`), summed by UTC calendar day before every consolidation attempt. **A real defect
  found and fixed during testing:** `tick-consolidate.sh` exits 0 both for "nothing new" (no model call,
  no cost) and after a real call+commit, so the scanner cannot key the log entry on exit code alone —
  doing so at first logged a token cost on every no-op pass, which would have inflated the ledger on
  every idle session's every scan and defeated the entire point of the free/cheap split. Fixed by keying
  off `tick-consolidate.sh`'s own stderr text (`"nothing new since ..."` is the only no-cost outcome;
  everything else, including a post-call commit failure, logs the placeholder estimate because the model
  call itself was genuinely made).
- **Verified by direct sandbox test** (six scenarios, a scratch git repo under `/tmp`, never the real
  `plans/` state): empty registry → no-op; registered pair with nothing new since the digest's marker →
  no-op, zero tokens logged; registered pair with a genuinely new turn → real model call, digest
  correctly updated, commit made, exactly one token-ledger line written; daily cap already exceeded →
  scan skipped entirely before any call; transcript stale past `--retire-days` → one final consolidation
  sweep, then a retirement marker written, then a second scan on the same stale transcript skips with
  zero cost; transcript's mtime moved back to "recent" → marker deleted on the next scan, pair rejoins
  the pool and resumes normal no-op/consolidate behavior with no double-processing. `shellcheck` clean on
  both changed/new scripts.
- **Single-instance guard + dead-man's-switch, added 2026-08-13 (same day, second pass).** Responds to
  sync's own `plan__tick-shared-scan-lock-and-start-ownership.md` handoff, which correctly flagged that
  the script had no `flock` at all — the same race `sync-main-watch.sh` hit on 2026-08-10 (a heuristic
  "already running?" check let two live watchers run simultaneously undetected). Fixed with an `flock`
  on fd 9, held for the process's whole life; a redundant instance refuses the lock and exits 0, so it is
  safe to call the start routine speculatively. **The dead-man's-switch deliberately does NOT reuse
  `sync-main-watch.sh`'s `pgrep -x claude` liveness check** — Dean caught that this is over-broad: a
  process literally named `claude` carries no session identity, so that check would keep this loop alive
  because of an unrelated Claude session in a different project folder, which has nothing to do with
  whether Main sync (the loop's actual owner, per Ownership above) is still around. Instead it checks
  Main sync's own `session/status/main.md` heartbeat (`last_check` staleness, default 150s threshold,
  matching `sync-main-session-start.sh`'s own alive-window) — a tighter binding to the specific session
  this loop exists to serve, not to "any Claude activity anywhere." New flags: `--main-sync-timeout`,
  `--no-main-sync-check` (testing only), `--lock-file`, `--main-status` (testing override, since the
  path is otherwise derived from the script's own location like `registry`/`retired_dir`/`usage_log`
  already were, all still non-overridable — a pre-existing limitation, not touched by this pass).
  Verified in a sandbox: a held lock causes a real invocation to refuse cleanly (exit 0, no scan
  attempted); a missing `main.md` self-exits immediately; a fresh heartbeat keeps the loop running
  (confirmed by letting `timeout` kill it mid-loop rather than self-exiting); a heartbeat already past
  the threshold self-exits on the very next check. `--once` is deliberately NOT gated by the
  dead-man's-switch — a single explicit test pass should always run regardless of Main sync's state.
  `shellcheck` clean after the change. **Explicitly not addressed** — the broader question of whether
  `nohup`/detachment is needed at all for either watcher if Main sync could start reliably on its own is
  a separate, larger design question Dean raised and deferred; only the narrow over-broad-liveness bug
  is fixed here.

## Still open

- **`CONVENTIONS.md`'s checkpoint-capture section is stale** relative to this addendum (and was already
  stale relative to the digest's "runs in every session" ruling before this addendum existed) — it
  describes the per-session-only two-tier design and the retirement framing without the shared-Tier-2
  piece. Per the parent design's own discipline, `CONVENTIONS.md` is a live always-loaded doc, not a
  frozen one, so it can be corrected directly rather than by addendum — but that edit is not yet done and
  is tracked here so it isn't lost a second time.
- **No `sync__` handoff has yet been sent** pointing CURRENT.md at the
  `atomic-step-protocol-brainstorm` digest or at this addendum. Until one is, a fresh session still has
  no CURRENT.md-visible trail to either.
- **Nothing is running yet in the real `plans/` worktree.** The scripts are built and verified only
  against sandbox data; `session/.tier2-registry`, `session/.tier2-usage.log`, and
  `session/.retired/` do not yet exist for real. Handing Tier-2 ownership to a live sync session (per
  the ownership model above) is the next step and is exactly what the pending `sync__` handoff is for.
- **Per-call token usage is still a placeholder estimate (488 tokens), not measured.**
  `tick-consolidate.sh` does not currently surface the model call's actual usage in a form the scanner
  can parse; until that plumbing exists, the ledger is only as accurate as the digest's own single
  historical measurement. Real usage reporting is a candidate follow-up, not required to start using the
  cap as a backstop.
- **Existing sessions' own per-session Tier-2 invocations are not yet retired.** `session-snapshot.sh`
  still supports `--consolidate-every` (calling `tick-consolidate.sh` itself, per the parent design) —
  this addendum does not remove that path. A session started with `--consolidate-every` set will keep
  doing its own Tier-2 work independently of the shared scanner, double-covering that session (harmless —
  `tick-consolidate.sh` is idempotent, a second call finds nothing new — but redundant). Whether to stop
  passing `--consolidate-every` in the standard per-session startup recipe once the shared scanner is live
  is a follow-up, not resolved here.
