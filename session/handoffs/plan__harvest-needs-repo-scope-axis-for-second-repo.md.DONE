from: planner (llm-scaler workspace bootstrap design)
to: plan (atomic-step-protocol-brainstorm — you own harvest-classification.md)
session: memory harvest needs a repo-specific vs global classification axis

## The ask, in one sentence

When the deferred `feedback_*`/`project_*` memory pass runs, classification needs a
**repo-specific vs global** axis alongside the existing `conv:` / `role:` / `model` placement —
because a second workspace is being stood up and the global ones have to be reachable from both.

Dean's framing: the memory harvest is yours (atomic-step Type-2 work), but it must be **applied in
the context of this migration**. This handoff is the migration's one requirement on it.

## What I verified before asking (so this isn't a duplicate)

Read `planning/harvest-classification.md` directly — committed `900024f5`, 215 lines. Two things:

- Its scope note says the current pass **deliberately covers only the two convention files**, "per
  Dean's request to validate the classification scheme on the largest, clearest source before
  extending it to the ~30 `feedback_*`/`project_*` memories" — explicitly "a separate, messier pass,
  not done as a full pass here."
- It already has `## From feedback_*/project_* memories — partial, started 2026-08-15`, holding one
  memory harvested early at Dean's request, noting "expect this section to grow piecemeal, ahead of
  the full pass."

So I am **not** asking you to create anything, and not proposing a parallel effort. The pass exists
and is deliberately deferred; this is a requirement to fold into it when it runs.

## Why the axis matters — and why retrofitting is the expensive path

Memories are keyed to the **bare-repo path**:
`~/.claude/projects/-home-dean-code-llm-d-llm-d-workload-variant-autoscaler-repo/memory/`
(that slug is the absolute path with `/` → `-`). A container at a different path gets a different
project dir, so **no memory follows a new workspace automatically.**

Dean's ruling on that (D3 of my doc): harvest into rules first, let the new workspace regenerate its
own memories one by one, copy over only what's important and left, then re-evaluate and clean up. Plus:
**"global memories should eventually live in `dean-ai-overlay`"** — that's the piece needing the axis.
Two destinations, decided per memory:

- **global** — how Dean wants work done, independent of repo: American English, no-push-without-
  confirmation, uv-for-python, no-in-place-shell-edits, DCO discipline, worktree locality,
  handoff-protocol mechanics. Destined for a cross-repo home (`dean-ai-overlay` is currently the only
  candidate that already *is* cross-repo, and is already wired into this container via
  `.vscode/tasks.json` → `dean-ai-overlay/vscode/tasks.json`).
- **repo-specific** — WVA missions, PR numbers, branch state, the pokprod campaign, TA internals.
  Stays behind; must **not** land in the new workspace as noise.

The cost argument: a pass that sorts only by *topic* produces a correct `conv:`/`role:` placement and
still leaves the global/repo split undone — so someone re-reads ~45 files later to answer a second
question. Capturing both axes in one read is nearly free; splitting it into two passes is not. That is
the whole of my ask.

## One thing I'd flag, not prescribe

The harvest is the step where content loss is easy and **invisible** — the failure mode
`feedback_current_state_preservation` describes. Worth the verify-or-copy-then-delete discipline per
file: a `feedback_*` memory is deleted only once its content demonstrably exists as a rule. You may
already have this covered — `harvest-classification.md`'s own framing (nothing removed from a source
until `coverage-check` M1.3 confirms the mapping is total) reads like exactly the right mechanism, and
if so the memory pass just inherits it and this paragraph is redundant. Noting it in case memories are
looser than convention files, since they have no `coverage-check` equivalent.

## Also worth knowing, since it may affect your design

A claim in my doc's earlier revision — that `feedback_*` could be **shared by symlink** between the two
workspaces — was **withdrawn**, for reasons that bear on the harvest's value:

- it preserves the *memory* form (probabilistic recall by description-match) for content that should be
  a *rule* (deterministic fetch by name) — i.e. it entrenches the form the harvest exists to replace;
- it makes both workspaces' memory dirs a shared mutable surface, so a write from either changes the
  other's behavior invisibly;
- it depends on an unverified platform assumption (that recall follows symlinks into `memory/`).

Harvesting needs none of those, which is why Dean's ruling is the better mechanism and why the
symlink-recall verification question is **dropped rather than carried**. Recording it so nobody
re-derives the idea and re-opens the question.

## Not mine to do

I have not touched `harvest-classification.md` — it's yours and may be under active edit. My doc
(`planning/llm-scaler-workspace-bootstrap-design.md`, DRAFT, uncommitted) has this in § D3, with § 8
listing exactly what I read. Related but separate handoff sent the same day:
`plan__sync-main-generalize-for-second-repo.md`.
