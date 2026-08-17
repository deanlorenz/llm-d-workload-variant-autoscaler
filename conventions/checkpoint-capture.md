# Checkpoint capture

### convention: checkpoint-capture
description: Session-start loop that captures decisions to disk cheaply, so compaction never silently drops them.
scope: every session, started once at session start
trigger: session start, or resuming a session
status: active
origin: session/CONVENTIONS.md § Checkpoint capture — a model-free loop, not a scheduled tick (C1, C2)

**Checkpoint capture — a model-free loop, not a scheduled tick.**

> ⛔ **The scheduled cron "CHECKPOINT TICK" is RETIRED (2026-08-11). Do not schedule one.** If your
> session already has one, **cancel it now**. scripts/session-extract.sh refuses while
> session/.tick-disabled exists, so a tick from an older session does no work — but only that session
> can cancel its own job, since cron jobs are session-scoped and invisible to everyone else.
>
> Measured 2026-08-10: **71 firings, 9 useful updates**, roughly a third of the day's ~406 API requests
> and on the order of **9M input tokens**. The per-tick text was never the cost — each firing was a
> separate request that re-uploaded the whole session. And the premise was wrong: idle time was assumed
> free, but idle is exactly when the prompt cache has expired, so an *idle* tick is the most expensive
> kind.

**What every session does instead:** start the detached loop once, at session start.

```
nohup ./scripts/session-snapshot.sh --out session/digests/<topic>.raw.md \
      --file <this session's transcript> --interval 120 &
```

Two tiers, and the split is the whole point:

- **Tier 1 — free.** The loop gates on `session-extract.sh --count`, which is pure shell. Zero means it
  does nothing: no request, no tokens, no model. New turns are appended to a local raw ledger beside the
  digest. **An idle session costs exactly nothing.**
- **Tier 2 — rare and cheap.** Only once the ledger has accumulated does consolidation into the digest
  run, in a **separate small-model process** whose context is the extract alone rather than this
  session's history. Text-in, text-out: the shell does all file and git work, so the model never needs
  to drive tools.

Pin the transcript with `--file`. Resolving it by mtime is wrong whenever sessions share a project
directory — the other session's file becomes newest the moment it writes.

scripts/session-extract.sh does the mechanical half (`--since <UTC>`; `--list` identifies transcripts
by their opening prompt). Full contract and rationale:
[planning/doc-and-session-model.md](../planning/doc-and-session-model.md) § Checkpointing.

**Why it is not optional.** Compaction — not crashes — is the loss channel. It replaces the working
context, so a decision or a not-yet-done next step the summarizer dropped is gone from the running
session while sitting unread on disk. One measured session compacted **54 times**. Nothing bridges disk
and context except text written into a file the next context window will actually read.

**Two early defects, both fixed 2026-08-10.** The tick's own prompt was captured as a turn, and — the
serious one — **mid-turn messages were silently missed**: a message sent while a turn is running is
recorded as `type: "queue-operation"` / `operation: "enqueue"`, never as a `user` record, so a
`user`-only filter returned nothing and looked exactly like "nothing was said". Three rulings were lost
that way before it was caught. Both shapes are now read, `enqueue` only, deduplicated on text.
