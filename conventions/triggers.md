# Triggers

### convention: triggers-format-and-behavior
description: Triggers are a doorbell, not a memo: the body carries only to/reason/refs/note, and the recipient re-reads referenced docs rather than executing instructions.
scope: planner, coder, or review agent wanting a sibling to re-read something
trigger: something changed that a sibling agent needs to react to
status: active
origin: session/CONVENTIONS.md § Triggers — 'go re-read X' notifications (C29); session/CODER-CONVENTIONS.md §5.3 Triggers to siblings (CC14); §9.3 template (CC20, trigger fragment); feedback_trigger_doorbell_only.md (FM47, read-as-the-recipient sanity check)

**Cross-reference note (per the classification table's already-made judgment call on C30/C31, not
re-decided here):** the flat-directory file-naming convention and the .md/.md.WIP/.md.DONE
state-machine mechanics that also govern trigger files live in `handoffs-file-naming` and
`handoffs-state-machine` in conventions/handoffs.md — folded there because handoffs are documented
first and more fully in both source files. This entry covers only what is distinct to triggers: the
no-instructions body shape and the doorbell behavior.

From session/CONVENTIONS.md § Triggers — "go re-read X" notifications (C29):

*Triggers — "go re-read X" notifications.* When one agent (planner, coder, or review
agent) wants another to look at something, it writes a trigger at
session/handoffs/<recipient>__<topic>.md. The recipient short token is the agent or
branch name (`plan` is reserved for the planner; coder branches use the branch name).

**Triggers carry no instructions.** The body has only (the `to:` line is authoritative
routing, matching the filename prefix):
```
to: <branch | review | plan>
reason: <re-read plan | sibling-status-update | upstream-rebase | other>
refs:
  - <doc path 1>
  - <doc path 2>
note: <optional one-line context>
```

The recipient processes a trigger by **re-reading the referenced docs**, never by
executing the trigger body. A trigger is a doorbell, not a memo. If the planner wants a
coder to do something different, the planner edits the plan doc and rings the bell.
Coder→coder triggers can only point at the sender's status file or a doc — they cannot
direct work; only the recipient's own plan defines scope.

When the recipient starts processing, rename to `<file>.md.WIP`. When done, rename to `<file>.md.DONE`.

From session/CODER-CONVENTIONS.md §5.3 Triggers to siblings — only when needed (CC14):

**5.3 Triggers to siblings — only when needed.**

If your work changes something a sibling coder needs to react to (your
tip moved, an interface you both touched changed shape, etc.), write a
trigger at:

```
plans/session/handoffs/<sibling>__<topic>.md
```

Triggers carry **no instructions**. The body has only `reason`, `refs`
(docs the sibling should re-read), and an optional one-line `note`. See
§9.3 and CONVENTIONS for the exact format. The sibling re-reads the
referenced docs and lets their own plan decide how to react.

**Receiving a trigger** addressed to your branch: rename to `.WIP` before processing,
`.DONE` when done. Same rule as for handoffs — mark before you act.

**The note must describe what changed in the refs — never what the recipient should do.** Write
it as ≤1 sentence answering "what is now different in refs?" (e.g. "Phase 4 addendum appended,"
"PR rebased onto main@SHA," "review status flipped to FINAL"). Do not include verdict words
("approved," "push-ready," "ready"), action verbs aimed at the recipient ("awaiting X," "now do
Y"), or state-of-the-world summaries the recipient could mistake for "you must reflect this
somewhere" — a multi-clause note that reads like a verdict has been mistaken for authorization
to act on planner-owned shared state before. If the recipient needs to do something different,
the right move is: edit the recipient's plan doc (planner) or status file (own), then ring the
bell — the action goes in the doc, the trigger only points at the doc. Resist inventing a more
"expressive" reason than the four documented categories; expressiveness in `reason:` leaks into
the note.

**Sanity check before writing a trigger:** read it as if you were the recipient with no other
context. If you'd reach for any file outside your write scope after reading it, the note is too
directive — trim it.

From session/CODER-CONVENTIONS.md §9.3 Trigger to a sibling template (CC20, trigger fragment):

**9.3 Trigger to a sibling** (plans/session/handoffs/<sibling>__<topic>.md)

Zero instructions in the body — only refs (see §5.3 and CONVENTIONS). The
`to:` line matches the filename prefix.

```
to: <sibling branch>
reason: <re-read plan | sibling-status-update | upstream-rebase | other>
refs:
  - <doc path 1>
  - <doc path 2>
note: <optional one line>
```
