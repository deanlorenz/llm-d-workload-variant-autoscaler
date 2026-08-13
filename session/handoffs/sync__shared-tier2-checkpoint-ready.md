from: atomic-step-protocol-brainstorm (designer/planner session, plans worktree)
to: sync
session: atomic-step-protocol-brainstorm

## What changed

Two small fixes, one new addendum, one new script, one script edit — all on `plans`, uncommitted
pending Dean's review (per the >3-file / substantial-single-file-edit approval rule):

1. **`session/CODER-CONVENTIONS.md`** — fixed two self-contradictions found via a live incident report
   from Dean (coders conflating `sync__`/`plan__` handoffs into one file defaulting to `sync__`; §0's
   own "why this matters" bullet modeling the forbidden bare-`cd` pattern as the sanctioned handoff-write
   recipe). §0 now points to `cp`/`mv` plus an explicit `EnterWorktree(path: ...)` self-rescue line; §5.2
   now opens with a "split before naming" instruction ahead of the sync__/plan__ destination bullets.
2. **`planning/governance-follow-ups.md`** — new dated section (`## CODER-CONVENTIONS.md
   self-contradiction incidents (2026-08-13)`) recording both incidents, tagged as "relocated" (existing
   written rule, not new policy) for `atomic-step-protocol-design.md`'s Migration 1 (M1.2 harvest) to
   pick up later — not restated here since it's a plans-branch-internal governance doc, not
   CURRENT-facing.
3. **`planning/atomic-step-protocol-design-addendum-2.md`** (new) — the shared-Tier-2 checkpoint design
   Dean asked for ("one tick for all live sessions... mostly shell work + autonomic model work, not
   running in the session's context"). Amends `atomic-step-protocol-design.md`'s checkpoint-capture
   content per that design's own amend-by-addendum discipline. Tier-1 stays per-session and unchanged;
   only Tier-2 (rare, cheap-model consolidation) centralizes, owned/monitored/started by the sync
   session, same detached-nohup pattern as today's per-session loops. Retirement bounds the scan
   (mtime stale >7 days → one final sweep → marker file → self-heals if the session wakes up); a daily
   token cap (50,000, combined across all sessions) is a backstop against a bug, not a tight budget.
4. **`scripts/session-snapshot.sh`** (edited) — added a self-registration block: on start, if given both
   `--file` and `--digest`, writes/overwrites one line in `session/.tier2-registry` mapping transcript
   path → digest path, so the shared scanner has a way to know which digest belongs to which session
   (no such mapping existed before this).
5. **`scripts/tick-shared-scan.sh`** (new) — the shared Tier-2 loop itself. Reads the registry, retires
   stale sessions, checks the daily cap, and calls the existing unmodified `tick-consolidate.sh` per
   session with new content. `--once` for testing, detached-loop mode otherwise.

**Verified, not just written:** all six behavior paths tested end-to-end in a scratch sandbox (never the
real `plans/` state) — empty registry, no-new-content no-op with zero token cost, real consolidation with
correct one-line token logging, daily-cap trip, retire-then-skip, and self-heal on wake-up. Found and
fixed one real bug during testing: the scanner initially logged a token cost on every no-op pass
(would have defeated the free/cheap split); fixed by keying off `tick-consolidate.sh`'s own stderr text
rather than exit code, which cannot distinguish "no call made" from "call made, commit failed after."
`shellcheck` clean on both scripts.

## Update CURRENT.md

Two separate, unrelated gaps this handoff closes:

**(a) The `atomic-step-protocol-brainstorm` reading list was never reachable from CURRENT.md.** It lives,
committed, at `session/digests/atomic-step-protocol-brainstorm.md` (commit `e8b47c46`) — nothing was
lost, but nothing pointed a fresh session at it either. Please add a line/pointer under the
`atomic-step-protocol-brainstorm` mission (wherever CURRENT.md's per-task structure fits it — this
appears to be a new mission not yet represented there) citing that digest, specifically its
`## Review triage for Dean` section (the read order: harvest, step-gates, authoring, role-skills; each
spec's `## Intent` + `## Step index` only, ~64–91 lines) as the standing reading-list pointer.

**(b) The checkpoint-tick status in CURRENT.md / CONVENTIONS.md is stale and self-contradictory.**
`session/.tick-disabled` is still present, with a commit message reading "retire the scheduled checkpoint
tick" — accurate for the old single-cron mechanism, but it reads as a blanket retirement and contradicts
the same digest's later ruling that the redesigned two-tier tick should run in every session. Please note
in CURRENT.md (or flag for whoever next touches `CONVENTIONS.md`'s § Checkpoint capture) that: the
per-session two-tier design (Tier-1 free/model-free, Tier-2 rare/cheap-model) is current and correct: the
**new addition, this handoff, is that Tier-2 is being centralized** per
`planning/atomic-step-protocol-design-addendum-2.md`, owned by the sync session rather than run
independently per-session. `CONVENTIONS.md`'s own text has not been corrected yet — tracked as a "still
open" item in the addendum, not done as part of this handoff (out of this session's write scope to touch
CONVENTIONS.md directly without more explicit sign-off, given how load-bearing that file is).

**(c) Please add `sync` as the owner of the shared Tier-2 loop going forward.** Per the addendum: start
`scripts/tick-shared-scan.sh` detached (same `nohup ... &` pattern as today's per-session Tier-1 loops)
from the sync session, and note in whatever sync-session status/state doc is appropriate that it is
responsible for noticing if that loop has died (crash, machine sleep, a prior sync session closing) and
restarting it. It is explicitly acceptable for it to pause when no sync session is active — no standing
daemon, no systemd unit, matches the addendum's decided lifecycle model.

## Open questions / follow-ups

- `CONVENTIONS.md`'s checkpoint-capture section still needs a direct correction pass (see (b) above) —
  flagged, not actioned by this session.
- `--consolidate-every` (the existing per-session Tier-2 path in `session-snapshot.sh`) is not retired by
  this addendum. A session still using it will keep doing its own Tier-2 work independently of the shared
  scanner — harmless (idempotent, a second call finds nothing new) but redundant. Whether to drop
  `--consolidate-every` from the standard per-session startup recipe once the shared scanner is live is
  an open follow-up, not resolved here.
- Per-call token usage in the ledger is currently a placeholder estimate (488 tokens/call, from the
  digest's own single historical measurement), not the real usage of each call — `tick-consolidate.sh`
  does not yet surface parseable per-call usage. Flagged as a candidate follow-up.
- Nothing in `session/.tier2-registry`, `session/.tier2-usage.log`, or `session/.retired/` exists yet in
  the real `plans/` worktree — only sandbox-tested. Starting the real loop is the action this handoff is
  requesting, not something already done.
