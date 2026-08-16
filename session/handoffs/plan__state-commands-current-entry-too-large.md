from: sync-session (plans)
to: plan (chat session, state-commands port)
session: state-commands-current-entry-too-large

## What this is

Your `sync__state-commands-skills-landed.md` handoff got folded into `session/CURRENT.md` almost
verbatim (~23 lines, lines 50-72 as of this writing) — that was sync's mistake, not yours, but
Dean's correction applies going forward: **CURRENT.md holds a short summary + a pointer; the design
detail belongs in the doc you already own.**

You already point CURRENT.md at `planning/state-commands-design.md` §§5-9 for full detail. Per
Dean: this content is "probably already captured" there — please check, and:

1. If everything in the current CURRENT.md entry (the three skills' scope, the mandatory-source-
   report rule, the two findings about subagent transcript persistence and worktree-exit
   correctness, the § 6.1 platform-facts caveat) is already in
   `planning/state-commands-design.md` — reply with a `sync__` handoff giving me a short summary
   (3-5 sentences) plus the doc ref, and I'll replace the current entry with it.
2. If anything is missing from that doc, fold it in there first, then send the summary+ref reply.

Not urgent, no action implied beyond the doc/CURRENT.md hygiene itself.
