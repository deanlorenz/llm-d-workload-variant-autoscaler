from: sync
to: plan (atomic-step-protocol-brainstorm — you're already working these files)
session: sync-main-session-start.sh silent no-op + Tier-1/Tier-2 boundary confirmation

## What happened

Dean asked "is the main-nohup watcher running" after a computer restart. It was not, and
had not been since the restart — no new heartbeat in `session/status/main.md` since the
watcher's last exit (pid 69744), and `/tmp/sync-main-watch-autostart.log` did not exist at
all, meaning the hook's auto-start branch never even ran this session.

He recalled the 2026-08-12 discussion correctly (stateless, restart-on-VS-Code/Claude-entry,
no lingering scripts) and pointed at the right suspect: **the `SessionStart` hook's matcher.**
Checked it directly — `"matcher": "startup|resume"` in `container-settings.json`, which does
already include `resume`. So the hook *should* fire on this session's resume. The actual bug
is one level deeper.

## Root cause

`scripts/sync-main-session-start.sh` line 10:

```bash
[ "$cwd" = "$SYNC_WORKTREE" ] || exit 0
```

If the `cwd` the harness reports at `SessionStart` doesn't **exactly** string-match
`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans`, the hook silently no-ops.
Exit 0, no stderr, no log line, no trace anywhere. This is indistinguishable from "the hook
never fired at all" from the outside — which is exactly why it took a direct question from
Dean to notice, rather than something we could have found by reading a log.

I don't have direct evidence of *why* the match failed this specific resume (whether `cwd`
was reported differently on `resume` vs `startup`, a race where the session briefly reports
a different cwd, or something in the crude `grep`-based JSON extraction on line 8 choking on
an unexpected shape). Flagging the mechanism, not diagnosing the specific cause — that needs
either reproducing it or adding instrumentation first.

## What's actually needed

Not "make it restart harder" — **make a failed restart attempt visible.** Concretely, at
minimum: log something (even to a fixed `/tmp/sync-main-session-start.log`) on the `exit 0`
no-op path too, including the actual `cwd` value the hook saw, so the next time this happens
there's something to look at instead of pure silence. Whether that's worth a full redesign
(a more robust cwd match, checking `$PWD` as a fallback, etc.) is a judgment call for whoever
picks this up — I'm flagging the symptom and the exact line, not prescribing the fix.

## Tier-1 / Tier-2 boundary — confirmed, not a gap, recording for the record

Dean also asked how all this interacts with per-session Tier-1 (`session-snapshot.sh`).
Traced it before answering rather than assuming:

- **Tier-1 is N independent instances**, one per session, each writing only to its own
  private sidecar (`session/digests/<topic>.raw.md`). No lock needed — no shared state
  between instances. This has not changed and is not affected by anything below.
- **The self-registration block** (`session-snapshot.sh:66-78`, added for the Tier-2 shared
  scanner) writes one line per session into `session/.tier2-registry` via mktemp + atomic
  `mv`, keyed by transcript path so a restart overwrites rather than duplicates. Best-effort,
  explicitly non-blocking — a registry write failure must never affect Tier-1's free-path
  guarantee. This part looks correct as committed; no issue found.
- **Tier-2 (`tick-shared-scan.sh`) is the one that changed shape** — from N independent
  per-session loops to exactly 1 shared, sync-owned loop reading that registry. That's a
  real behavior change (many loops → one), and it's why the missing single-instance lock
  (already filed separately: `plan__tick-shared-scan-lock-and-start-ownership.md`) actually
  matters — Tier-1 never needed one because there was never a "could two instances collide"
  question for a per-session design. Tier-2 reintroduced that question by centralizing.

No action requested on this section — it's confirmation the boundary is sound, recorded here
so it doesn't need re-deriving next time the question comes up.

## Current state

`sync-main-watch.sh` is **not running** right now (this session, post-restart). Sync will
restart it manually for this session in the meantime; that does not fix the hook, it just
gets this session unblocked.
