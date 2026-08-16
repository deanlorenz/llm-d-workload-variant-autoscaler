from: sync-session (plans)
to: plan (single-instance-guard coder)
session: single-instance-guard-current-entry-too-large

## What this is

Your `sync__single-instance-guard-landed.md` handoff got folded into `session/CURRENT.md` almost
verbatim (~37 lines, lines 13-49 as of this writing) — that was sync's mistake, not yours, but
Dean's correction applies going forward: **CURRENT.md holds a short summary + a pointer; the design
detail belongs in the doc you already own.**

You already point CURRENT.md at `session/status/single-instance-guard.md` for full state. Per Dean:
this content is "probably already captured" there or in the design docs it amends — please check,
and:

1. If everything in the current CURRENT.md entry (the guard identity-key fix, Defect C, the two
   armed footguns about killed loops and dead Tier-1 capture, the commit-collision note) is already
   in `session/status/single-instance-guard.md` and/or
   `planning/checkpoint-capture-spec.md`/`planning/sync-watchers-spec.md` — reply with a `sync__`
   handoff giving me a short summary (3-5 sentences) plus the doc ref, and I'll replace the current
   entry with it.
2. If anything is missing from those docs (in particular the two armed footguns — killed loops
   `16342`/`629315`, and the dead Tier-1 capture on the sync session's own transcript — since those
   read like live-state facts rather than design content), fold it in there first, then send the
   summary+ref reply.

Not urgent, no cluster/code action implied. This is a documentation-hygiene ask, not a task on the
guard mechanism itself.
