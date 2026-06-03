# Multi-Analyzer Split — Coder Mission

Mission-specific addendum for the three coder agents working on the
multi-analyzer PR split. Universal coder rules live in
`plans/session/CODER-CONVENTIONS.md` (loaded automatically); this doc
only carries what is specific to this mission.

## Required reading (in order, before any edit)

1. **`plans/session/CONVENTIONS.md`** — project conventions: worktree
   layout, document taxonomy (Type 1-6), agent roles and doc ownership,
   universal working rules. Authoritative source for everything; if
   anything in CODER-CONVENTIONS or this file conflicts with
   CONVENTIONS, CONVENTIONS wins.
2. **`plans/session/CODER-CONVENTIONS.md`** — coder-role rules: worktree
   scope, no-push, tests, dev-guide, status / handoff / trigger flow,
   WIP discipline, may / may-not lists, templates. Loaded automatically
   via CLAUDE.md.
3. **`plans/session/CURRENT.md`** — session state, PR status, and the
   "Multi-Analyzer Split — coder sessions" section that lists the three
   branches and their roadmap mapping.
4. **`plans/planning/PR1113-review.md`** — the fix design. The
   Implementation roadmap section is your per-branch scope source. The
   Migration audit lists tests that move with their analyzers.
5. **Your per-branch plan doc** — `plans/planning/multi-analyzer-<role>-plan.md`
   when present (see table below). The plan doc is your only source of
   scope; CODER-CONVENTIONS describes *how* you work, the plan describes
   *what* you do.
6. This document — mission-specific gotchas (below).

## Mission scope by branch

| Branch | Worktree | Item | Plan doc |
|---|---|---|---|
| `multi-analyzer-registration` | `multi-analyzer-registration/` | Item 3 — analyzer registration; race-fix | (PR-only; review doc is `PR1113-review.md`) |
| `multi-analyzer-threshold` | `multi-analyzer-threshold/` | Item 2 — engine universal threshold post-step | `multi-analyzer-threshold-plan.md` |
| `multi-analyzer-optimizer` | `multi-analyzer-optimizer/` | Item 1 — delete combine; per-analyzer slice | `multi-analyzer-optimizer-plan.md` |

## Developer-guide files for this mission

Per CODER-CONVENTIONS §4, every code change reflecting user-visible or
architecturally-visible behavior gets reflected in
`docs/developer-guide/`. For this mission the relevant files are:

- `docs/developer-guide/saturation-scaling-config.md` (Multi-Analyzer
  Pipeline section)
- `docs/developer-guide/saturation-analyzer.md`
- `docs/developer-guide/throughput-analyzer.md`

Either update an existing file or add a new one if your change has no
home.

## Mission-specific gotchas

(Empty for now. Add here if a mission-level constraint emerges that
isn't in CONVENTIONS, CODER-CONVENTIONS, the review doc, or your plan
doc.)
