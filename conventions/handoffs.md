# Handoffs

### convention: handoffs-serialize-shared-state
description: No session edits CURRENT.md or other canonical session/ shared files directly; write a sync__ handoff for the dedicated sync session to fold in instead.
scope: every session except the dedicated sync session
trigger: wanting to change CURRENT.md, the PR Status table, or any other canonical session/ shared file
status: active
origin: session/CONVENTIONS.md § Inter-agent communication, Handoffs — serialize updates to shared state (C24)

*Handoffs — serialize updates to shared state.* No session edits CURRENT.md, the PR Status
table, or any other canonical session/ shared file directly — not coders, not review
agents, not other planner instances. They write a handoff at
session/handoffs/sync__<topic>.md describing what the dedicated sync session should fold
in. The sync session is the single writer; the handoff queue avoids edit conflicts. Handoffs
need not be committed by the submitting session — all sessions share the plans/ worktree
filesystem, so the sync session reads uncommitted handoff files directly and commits/consumes
them in its batch.

### convention: handoffs-sync-vs-plan-split
description: sync__ is exclusively for CURRENT-update requests; plan__ is for a working planner's task/decision; split mixed content before naming the file.
scope: every session writing a handoff
trigger: about to name and write a handoff file
status: active
origin: session/CONVENTIONS.md § sync__ is exclusively for CURRENT-update requests (C25); session/CODER-CONVENTIONS.md §5.2 handoff destinations (CC13)

From session/CONVENTIONS.md (planner/general statement):

**`sync__` is exclusively for CURRENT-update requests — do not conflate it with `plan__`.**
A sync__<topic>.md handoff asks the sync session to change CURRENT.md / PR Status / shared
session/ state; it is the *only* prefix /sync-current consumes. A plan__<topic>.md
handoff is a task or decision-request for a **working planner** (fold findings into a plan
doc, design a workload, answer a feasibility question) — there are many concurrent planner
sessions, and the sync session must **never** consume `plan__` (doing so robs the intended
planner of their work item). A *mixed* handoff (planner-task plus suggested CURRENT edits)
stays `plan__`; the planner re-emits a clean `sync__` after folding, keeping sync
single-purpose. (Incident 2026-08-03: 16 `plan__` handoffs wrongly consumed as sync input.)

From session/CODER-CONVENTIONS.md §5.2 (coder-facing restatement, with the split-before-naming fix):

**5.2 Handoff — CURRENT-update (`sync__`) vs planner-task (`plan__`).**

Two distinct destinations, two distinct prefixes. Pick by *who acts on it*:

**Before naming the file, split the content first.** If what you want to say
is both "here's what changed, update CURRENT" and "here's a question/decision
for a planner," that is two handoffs, not one. Write the `sync__` file with
only the CURRENT-update content, and a separate `plan__` (or `<sibling>__`)
file with the rest. A single mixed file is the failure mode — coders keep
defaulting to `sync__` for the combined draft, then rewriting into two once
corrected. Decide the split before you decide the filename.

- **CURRENT.md / PR Status / blockers / next steps need to change** → write a
  **sync__<topic>.md** handoff (`to: sync`). This is the common end-of-work
  case: a commit you want reflected in CURRENT, a pause where you want project
  state captured.

  ```
  plans/session/handoffs/sync__<topic>.md
  ```

- **A working planner must decide or design something** (answer a question,
  fold a finding into a plan doc, scope follow-up work) → write a
  **plan__<topic>.md** handoff (`to: planner`). There are many concurrent
  planner sessions; the sync session never touches `plan__`.

  ```
  plans/session/handoffs/plan__<topic>.md
  ```

Format — three header lines (`from:` / `to:` / `session:`) plus freeform
prose; see §9.2 template. The `to:` line must match the prefix.

Write a handoff at meaningful gates, not per checkpoint — that's what the
status file is for.

The **sync session** processes `sync__` handoffs via /sync-current when
Dean asks; your handoff is then renamed to `<file>.md.DONE` and `git rm`-ed
in the sync commit. A `plan__` handoff is picked up by a planner session, not
by sync.

**Receiving a handoff from the planner** (e.g. a trigger addressed to your branch):
rename it to `<file>.md.WIP` before you start acting on it, and to `<file>.md.DONE`
when done. Never begin processing without marking `.WIP` first — it signals to the
planner that the file is being consumed and must not be edited.

### convention: handoffs-format
description: Handoff format: three header lines (from/to/session) plus freeform prose body; the to: line is authoritative routing.
scope: every session writing a handoff
trigger: writing any sync__ or plan__ handoff
status: active
origin: session/CONVENTIONS.md § Handoff format (C27); session/CODER-CONVENTIONS.md §9.2 template (CC20, handoff fragment)

Handoff format — three header lines plus freeform prose body (the `to:` line is authoritative
routing; the filename prefix is just the `ls`-glob convenience — if they disagree the file is
misfiled, so flag it rather than guess):
```
from: <branch or agent name>
to: <sync | planner | <branch> | review>
session: <short topic name>

<freeform: what was completed, what CURRENT should say, new/updated work items,
pending handoffs to add or remove, blockers to clear, next steps to record. Be
complete — the sync agent applies exactly what the handoff describes.>
```

**9.2 CURRENT-update handoff** (plans/session/handoffs/sync__<topic>.md)

Written when shared state (CURRENT.md, PR Status table, blockers, next
steps) needs to change (see §5.2). One-shot — not a living file. For a
decision/task aimed at a working planner instead, use the same shape with
a plan__<topic>.md name and `to: planner`.

```
from: <your branch>
to: sync
session: <short topic name>

 ## What changed
<commit shas, files touched, gates passed>

 ## Update CURRENT.md
<what the per-task section / PR Status row / blockers / next steps
should say>

 ## Open questions / follow-ups
<things to surface across sessions>
```

### convention: handoffs-sync-ref-and-prose
description: A sync__ handoff must carry both a ref to the full committed state file and short WIP prose sufficient for a cold resume.
scope: any session writing a sync__ handoff
trigger: writing a sync__ handoff
status: active
origin: session/CONVENTIONS.md § A sync__ handoff must carry two things (C28)

**A `sync__` handoff must carry two things: the ref and the resume prose.**

1. **A ref to the full, committed state file** — the authoritative path (session/status/<branch>.md,
   your Type 3 plus its section, a commit SHA), so CURRENT.md can point instead of storing.
2. **Short WIP prose sufficient for a cold resume** — enough that a brand-new session reading only
   CURRENT.md knows what is in flight, what is owed and by whom, and which footguns are armed, without
   opening the plan. You cannot write CURRENT.md yourself, so if you omit this the sync session either
   invents it or drops it; both are worse than you writing three accurate sentences.

A ref with no prose leaves CURRENT.md useless for triage; prose with no ref recreates the state-store
problem. Include both. Keep armed footguns verbose even when the rest is compressed — a paused
autoscaler, a sole surviving copy of a file, uncommitted edits in a worktree — those are
recoverability content, not narrative.

### convention: handoffs-file-naming
description: Flat handoffs directory, <recipient>__<topic>.md filename prefix encodes routing and must match the to: header.
scope: every session writing a handoff or trigger
trigger: naming a new handoff or trigger file
status: active
origin: session/CONVENTIONS.md § File naming (C30) — folded into handoffs per the classification table's own judgment call, cross-referenced from conv:triggers

**⚠️ Judgment call, flagged by the classification table, not re-decided here.** A real alternative
existed — a fourth, dedicated convention (`conv:artifact-naming` or similar) holding just the
naming/state-machine mechanics shared by handoffs, triggers, *and* status files, with each of those
three citing it rather than one of them owning it. The table folded this into `handoffs` (cross-
referenced from `triggers`) because handoffs are documented first and more fully in both source
files — accepted by Dean as-is on the 2026-08-13 review pass, not re-litigated by this harvest.

*File naming — flat directory, prefix encodes routing:*
```
session/handoffs/
  sync__anchor-opt-in-decision.md          # to the sync session (CURRENT-update, prose body)
  plan__threshold-coder-rules-gap.md       # to a working planner (task/decision, prose body)
  optimizer__plan-resume.md                # to multi-analyzer-optimizer coder (no-body trigger)
  threshold__rebase-target-shift.md        # to multi-analyzer-threshold coder (no-body trigger)
```

<recipient>__<topic>.md. Filter by `ls session/handoffs/<recipient>__*.md`.
Recipient tokens: `sync` (the sync session — CURRENT-update requests only), `plan` (a working
planner — tasks/decisions), short branch nicknames for coders, `review` for the review agent.
The prefix must match the `to:` header; if they disagree the file is misfiled.

### convention: handoffs-state-machine
description: Three-state file machine (.md / .md.WIP / .md.DONE); recipient owns all transitions; sender never edits after sending.
scope: sender and recipient of any handoff or trigger
trigger: starting to process a handoff/trigger addressed to you, or finishing one
status: active
origin: session/CONVENTIONS.md § State machine (C31) — folded into handoffs per the classification table's own judgment call, cross-referenced from conv:triggers

*State machine — three states, recipient owns all transitions.*

```
<file>.md      — open: sender A wrote it, B has not started
<file>.md.WIP  — B is processing: A must not edit
<file>.md.DONE — B finished
```

B marks `.WIP` immediately on start, `.DONE` when done. A never edits the file after
sending. If A needs to add something while B's file is `.WIP`, A creates a new sibling
handoff. All transitions are `mv` (not `rm`); `.DONE` files are removed by the planner
via `git rm` in the /sync-current commit, or accumulate harmlessly until cleanup.
Coders and the planner may write and rename files under plans/session/handoffs/ and
plans/session/status/ from any worktree — this is the only sanctioned exception to
"no edits outside your worktree."

### convention: handoffs-new-session-no-current-entry
description: Starting a new session without an existing CURRENT entry is handled the same way as any other shared-state update: write a sync__ handoff with everything needed to create the section.
scope: any new session with no existing CURRENT.md entry
trigger: session start with no prior CURRENT.md section for this work
status: active
origin: session/CONVENTIONS.md § Starting a new session without an existing CURRENT entry (C32)

*Starting a new session without an existing CURRENT entry:* write a sync__<topic>.md
handoff that includes everything needed to create the section — session name, task,
scope, initial work items. A new session is not structurally different from any other
shared-state update.
