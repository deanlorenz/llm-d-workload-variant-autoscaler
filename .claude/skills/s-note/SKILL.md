---
name: s-note
description: Drop a timestamped decision note during a coding session. Use when you make a low-level design or implementation decision that should be preserved for the plan doc. Invoke with /s-note <plan-doc> <decision text>.
disable-model-invocation: true
allowed-tools: Bash(date *), Bash(mkdir *), Bash(git -C plans *), Write
---

# Decision Note

**Arguments:** $ARGUMENTS — first token is the plan doc name (no path, no `.md`), rest is the decision text.

Example:
```
/s-note TA-review-fixes-plan chose per-pod filter over variant skip — cold-start pods should not block healthy ones
```

---

## Parse arguments

Split $ARGUMENTS on the first space:
- `plan_doc` = first token (e.g. `TA-review-fixes-plan`)
- `decision_text` = everything after the first space

If $ARGUMENTS is empty or contains no decision text (only one token), tell the user:

> Usage: /s-note \<plan-doc\> \<decision text\>
> Example: /s-note TA-review-fixes-plan chose per-pod filter because cold-start pods should not block healthy ones

Stop.

---

## Step 1: Get timestamp

```bash
date +%Y%m%d-%H%M%S
```

---

## Step 2: Ensure handoffs directory exists

```bash
mkdir -p plans/session/handoffs
```

---

## Step 3: Write the note file

Write `plans/session/handoffs/note-<timestamp>.md` using the Write tool:

```
to: plan-agent
plan: planning/<plan_doc>.md
status: DECISION
note: <first 100 characters of decision_text, truncated at a word boundary>
body: <full decision_text>
```

---

## Step 4: Commit

```bash
git -C plans add session/handoffs/note-<timestamp>.md
git -C plans commit -m "session: decision note for <plan_doc> — <first ~60 chars of decision_text>"
```

---

## Step 5: Confirm

Print one line: `Noted → plans/session/handoffs/note-<timestamp>.md`

Return immediately. Do not summarize or expand.
