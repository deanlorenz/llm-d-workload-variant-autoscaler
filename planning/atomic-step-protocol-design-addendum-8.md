# Addendum 8 — plans-tooling becomes the main dev branch for plans, not a throwaway kickoff worktree

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (design, FINAL, frozen
2026-08-10) § Migration, specifically the "Own worktree for the tooling, copied over at an atomic
deliberate kickoff" decision recorded in that design's own digest and § Decided list. The parent is not
edited: this is the amendment channel it names.

**Status: decided by Dean, 2026-08-15.**

---

## What changed

The original plan (per the frozen design and its digest) treated `plans-tooling` as a **throwaway
development worktree**: build the migration tooling there in isolation, then copy the finished result
into `plans/` in one deliberate kickoff action, after which `plans-tooling`'s own development history
would stay behind on its own branch, not become part of `plans`'s ongoing history.

Dean, 2026-08-15: *"We are going to use plans-tooling for all code work and for all rules migration
work. It will become our main dev branch for plans."*

This is a real scope change, not a rewording:

- `plans-tooling` is no longer scoped to *just* the tooling spec's four scripts (`sec`/`conv`/
  `conv-list`/`conv-lint`) plus the authoring spec's three (`conv-new`/`conv-edit`/`conv-rename`). It
  becomes the working branch for **all** code work on the plans tree and **all** rules-migration work
  going forward — a durable branch, not a scratch worktree with a planned end-of-life copy-over.
- The "atomic deliberate kickoff copy" step (moving `plans-tooling`'s content into `plans/` in one
  action, per the design's own § Decided list) is **superseded by this decision** — if `plans-tooling`
  *is* the dev branch now, there may be no separate copy-over step at all, or it may become a
  fast-forward/merge instead of a copy. Not resolved here; flagged as an open consequence below.

## Immediate practical effect

A coder session and an internal code-reviewer session are being started in `plans-tooling`
(2026-08-15), with the coder's first task being the `conventions-authoring-spec.md` slice
(`conv-new`/`conv-edit`/`conv-rename`, S1-S3) — the natural next step after the already-landed
read-side tools, on a spec already reviewed as good. This addendum records the branch-role change that
makes that assignment durable rather than scoped to one throwaway task.

One untracked leftover exists in the worktree from an earlier trial harvest pass:
`conventions/code-deletion.md`, never committed. Flagged for the coder to check in about rather than
silently absorb or discard, since its provenance (a planner's own trial, not part of any spec) isn't
something a coder should resolve unilaterally.

## Background-agent launch, 2026-08-15 — mechanism found, one defect fixed

Dean asked for a coder and internal-code-reviewer, both persistent sessions he directs only through
the planner (not directly), with a read-only progress view he can watch. Findings from actually doing
this, captured as they occurred rather than only at the end:

- **`claude --bg`** (background agent, distinct from both `claude -p` one-shot and the in-process
  `Agent` tool) is the correct primitive — `claude agents --json` gives structured status
  (`state`/`status`/`waitingFor`) for scripting, `claude logs <id>` gives raw terminal output (not
  reliably clean — see below), `claude attach <id>` opens it interactively, `claude stop <id>` ends it.
- **`claude logs <id>` returns raw ANSI/terminal escape sequences**, not clean text — unusable for a
  planner to parse directly. `claude agents --json` is the reliable structured-status path instead.
- **Real defect, found and fixed:** launching with `--permission-mode acceptEdits` left both agents
  stuck at `state: blocked, waitingFor: "permission prompt"` — `acceptEdits` only covers file-edit
  operations, not the broader tool calls (Bash, reads outside default-allowed paths, etc.) a session
  needs just to start working, and nobody is present to answer an interactive prompt for a background
  agent. Fixed by relaunching with `--permission-mode auto`, which matches this project's own documented
  model (CONVENTIONS.md: interactive only on genuine judgment calls, everything else unprompted) —
  confirmed unblocked (`state: working`) after relaunch. **Anyone launching a `claude --bg` agent in this
  project should default to `--permission-mode auto`, not `acceptEdits`.**
- **VS Code has no native support for this workflow, researched and confirmed (not guessed):** no
  panel/tree view for background agents, no passive live-streaming view, no way to restrict which
  session type opens interactively vs. only via background dispatch. The closest approximation for
  Dean's "read-only progress view" ask is running `claude agents` in a VS Code integrated terminal
  himself and leaving it open — an interactive TUI he doesn't type into, not a true passive stream.
  Dean explicitly deferred formalizing the "planners are the only interactive webview sessions, every
  other role is agent-only" governance model as its own design item — this is recorded here as the
  supporting research, not as that decision.
- **Session auto-naming picked up "Planner" as the role suffix for the coder** (`"name":
  "📐 coder-session-plans-tooling-branch Planner"`) — the auto-namer inferred the role word from
  context and got it wrong (coder ≠ planner). Cosmetic, not corrected, flagged in case it causes
  confusion later when distinguishing agents by name alone.
- **Two live agents as of this writing:** coder `14d876ac` (plans-tooling, building
  conv-new/conv-edit/conv-rename per `conventions-authoring-spec.md` S1-S3), reviewer `3da4ba42`
  (launched from `plans`, scoped to review the coder's work once ready, explicitly told to wait).

## Still open — consequences not yet worked out

- **What happens to the planned "copy into `plans/`" kickoff step**, now that `plans-tooling` is meant
  to persist as the dev branch rather than be retired after one copy. Candidates: `plans-tooling`
  effectively *becomes* `plans` (a rename/merge), or `plans` stays the canonical branch and
  `plans-tooling` becomes a long-lived feature branch that periodically merges forward — not decided.
- **Governance implications** — `session/CONVENTIONS.md`'s existing rules about who may write to
  `planning/` (multi-writer) versus `session/` (single-writer via sync) were written assuming `plans` is
  the one active branch for this kind of work. Whether those rules need restating for a dual-branch
  (`plans` + `plans-tooling`) reality, or whether `plans-tooling` simply inherits them as-is once it's
  understood as "the same branch, different name," is not addressed here.
- **DCO/gate posture — resolved for now, revisit later.** `conventions-authoring-spec.md`'s own
  Prerequisites say "No DCO on this lineage. Never push." for `plans-tooling`, written under the
  throwaway-worktree assumption. Dean's call, 2026-08-15: **keep this as the default for now** — nothing
  about the main-dev-branch decision itself changes push/DCO rules; the coder launched today stays
  local-only, no DCO required, until Dean explicitly revisits this Prerequisite. Not a permanent answer,
  just the safe default while the branch-role change's other consequences are still being worked out.
