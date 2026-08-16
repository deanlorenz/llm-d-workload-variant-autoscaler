---
name: s-note
description: Capture a quick observation or a few notes, scoped by a fence, and route each one to wherever it actually belongs — your own doc, a sync__/plan__ handoff, or memory. Splits multi-part input into sub-notes and routes each independently. Asks if a sub-note's home is ambiguous rather than guessing. Invoke with /s-note followed by a fenced block.
allowed-tools: Bash(date *), Bash(pwd), Bash(git branch --show-current), Bash(git status:*), Bash(git add:*), Bash(git commit:*), Read, Write, Edit, AskUserQuestion
---

<!-- user-approved-settings-change: full redesign 2026-08-17 (Dean), same command name, replacing the
     prior single-destination decision-note mechanism entirely. Grants narrowed to match: the
     Bash(git -C plans *) wildcard is gone (it could reach git rm, ruled out everywhere else in this
     project — see session/CODER-CONVENTIONS.md and planning/state-commands-design.md § 8), replaced
     by plain CWD git (status/add/commit only, explicit pathspecs, matching s-state-park's own pattern).
     AskUserQuestion added since routing an ambiguous sub-note now asks rather than guesses. -->

# Quick Note

**Arguments:** `$ARGUMENTS` — a fenced block of one or more observations:

```
/s-note
\`\`\`
first observation, one or a few sentences

second, unrelated observation
\`\`\`
```

A single short note with no fence is also fine — treat the whole argument as one sub-note. The fence
matters when there is more than one distinct thing to say, or when the text itself contains blank lines
or characters that would otherwise be ambiguous about where the note ends.

If `$ARGUMENTS` is empty, tell the user:

> Usage: /s-note \`\`\`<one or more observations, blank-line-separated>\`\`\`

Stop.

---

## Step 1 — split into sub-notes

Split the fenced content on blank lines (or on an explicit numbered/bulleted list, if that is how it was
written) into independent sub-notes. Each sub-note should be one self-contained observation — a decision,
a finding, a correction, a TODO, a preference. Do not merge unrelated sub-notes to save a step, and do not
split a single coherent thought into fragments just because it spans a few sentences.

If the whole block is genuinely one thing, that is one sub-note. Splitting is about matching structure
already present in what was said, not manufacturing structure that isn't there.

## Step 2 — determine your own identity and write scope

```bash
pwd
git branch --show-current
```

Same role-aware write-scope split as `/s-state-park` Step 1 (coder vs. planner/reviewer/chat) — see
`planning/state-commands-design.md` § 5.1 if the distinction is unfamiliar. This determines where each
sub-note in Step 3 may land directly versus needing a handoff.

## Step 3 — route each sub-note independently

For each sub-note, decide its home using the same table `/s-state-park` uses (Step 4 there), reproduced
here for convenience:

| Sub-note is about | Home | Note |
|---|---|---|
| Your own current thread — a decision, finding, or WIP state for a Type 3 you own | your own Type 3 in `planning/` | Planner/reviewer only. |
| Your own liveness, current step, a footgun | your own `session/status/<branch>.md` | Include the identity block if creating fresh. |
| CURRENT.md, PR Status, or other shared `session/` state | `session/handoffs/sync__<topic>.md` | ⛔ Never edit CURRENT.md directly. |
| Another owner's plan doc | `session/handoffs/plan__<topic>.md` | ⛔ Their uncommitted work is invisible to you. |
| A durable fact about Dean, the project, or a preference — the kind of thing that belongs in memory | the memory directory | One fact per file; check for an existing file to update before creating a new one. |
| Genuinely unclear which of the above it is | — | **Ask, per Dean's explicit instruction — do not guess.** Use `AskUserQuestion`, offering the candidate homes you're weighing as options. |

**Ambiguity is common and expected, not a failure.** A quick note is by nature under-specified about where
it belongs — that is exactly why this step exists rather than a single fixed destination. When genuinely
unsure between two homes, ask; do not default to whichever is easiest to write to.

**Coders** have the narrower scope from `CODER-CONVENTIONS.md` §1/§5: your own worktree, plus exactly
`plans/session/status/<branch>.md` and `plans/session/handoffs/`. A sub-note that would otherwise go to a
Type 3 you don't own becomes a `plan__` handoff instead.

## Step 4 — write and commit each direct write

For any sub-note landing directly in a doc you own (not a handoff — handoffs need not be committed by the
submitting session, per the shared-filesystem handoff protocol):

```bash
git status --short
```

Read the output before staging — if it shows changes you didn't make, another session is active in this
tree; stage only your own file. Then, per this project's pathspec-only convention (never `git add -A`,
never a bare directory, never leaving a file staged in the shared index for another session to sweep up):

```bash
git add <the one file you wrote>
git commit -m "note: <topic> — <one line per sub-note landed here>"
```

If a sub-note produces a handoff instead, write it per the standard `session/handoffs/<prefix>__<topic>.md`
convention — no separate commit needed for handoffs.

## Step 5 — confirm

Print one line per sub-note: `Noted → <destination>` (a file path, or `handoff: <path>`, or
`asked — awaiting your answer`). Do not summarize or expand beyond that — this is a quick-capture skill,
not a report.

---

## Notes

- This is a lighter-weight, single-invocation version of `/s-state-park`'s own scan-and-route logic (Step
  3/4 there) — reuse that mental model rather than reinventing routing rules here.
- Never routes to CURRENT.md directly, never marks a handoff `.WIP`/`.DONE` (accepting/finishing work is a
  session's own act, not this skill's), never deletes or reorganizes existing content. If a note reveals
  that something existing needs restructuring, say so and suggest `/s-state-sweep` — do not do it here.
