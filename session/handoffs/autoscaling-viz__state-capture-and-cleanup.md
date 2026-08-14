to: autoscaling-viz
reason: re-read plan
refs:
  - session/handoffs/autoscaling-viz__task6-version-stamp-and-regen.md.WIP — stuck; Task 6 is
    actually closed on the planner's side (see autoscaling-viz__task6-resolution.md), this trigger's
    own .WIP state was never flipped to .DONE
  - session/handoffs/autoscaling-viz__task6-resolution.md — unprocessed, contains the resolution
  - session/handoffs/autoscaling-viz__task7-corner-info.md — released, unprocessed
  - planning/autoscaling-viz-followon-plan.md — epic plan, scope-boundary section added at the top
  - session/status/autoscaling-viz.md — your own status file, currently stale-tailed
note: general instruction, not tied to one task — before picking up Task 7, do a full capture sweep
  of your own session: (1) resolve the stuck task6-version-stamp-and-regen.md.WIP by reading
  task6-resolution.md and flipping the trigger to .DONE yourself (you are its recipient, only you
  transition its state); (2) make sure your own session/status/autoscaling-viz.md reflects
  everything through Task 6's actual close (the cross-worktree incident, the benchmark-side
  pull-up resolution, the corrected output-location instruction now in the version-stamp spec) —
  it currently still ends mid-way through older content; (3) if you're holding any findings,
  decisions, or context in your own working memory/conversation that hasn't landed in a status
  file, plan doc, or handoff, write it down now, before continuing — same request Dean gave the
  planner side, extended to you. Read the epic plan's new top-of-doc scope-boundary section too —
  it's a durable rule (output placement is benchmark's, per-request/extraction-tool work is
  benchmark's unless assigned here, panel rendering is squarely yours) that should shape how you
  read future specs, not just this one.
