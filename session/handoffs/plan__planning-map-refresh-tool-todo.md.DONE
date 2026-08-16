from: sync-session (plans)
to: plan (atomic-step-protocol-brainstorm)
session: planning-map-refresh-tool-todo

## What this is

Add to your TODO list, not urgent: a refresh tool for `planning/planning-map.md`.

## Context

`planning/planning-map.md` (new, `Status: DRAFT`, Dean approved as "good enough for now" on
2026-08-15) is an index of every `planning/` doc, classified by type (design/roadmap/task-plan/
review) and topic cluster, with pointers into `session/CURRENT.md` for live PR status. Built by a
one-off scan; there is currently no mechanism keeping it current as new docs land or old ones get
superseded.

The doc's own § Gaps and questions names this explicitly (item 5): "This doc itself will drift —
no mechanism keeps it current." Two options were floated there, not decided:
1. A `toc-refresh.sh`-style regen script (matching the existing pattern for Type-3 plan TOCs).
2. Treat it as a point-in-time snapshot, regenerated on request rather than continuously
   maintained — matching how `ta-pokprod-history.md` treats its own append-only ledger.

## Why this planner

This falls naturally under the atomic-step-protocol-brainstorm track since it's tooling for
session/planning hygiene, same family as `toc-refresh.sh` and the checkpoint scripts, not a WVA
product concern.

## Not scoped yet — needs your design pass

- Which of the two options above (or a third) fits best.
- If it's a script: what it actually re-derives automatically (file list + rough type
  classification via header patterns) vs. what stays human-judgment (topic clustering, gap
  callouts) — likely a hybrid, not full regeneration, since the topic analysis in the current
  draft required reading content, not just listing files.
- Whether it belongs in `scripts/` alongside `toc-refresh.sh`, and whether it needs the same
  idempotent-rerun property.

No footguns, no blockers — this is a clean, deferred TODO item.
