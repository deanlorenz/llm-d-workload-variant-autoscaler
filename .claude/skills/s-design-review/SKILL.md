---
name: s-design-review
description: Review implementation correctness against design documents for a specified scope. Reviewer-only — no code changes. Discusses findings with the user before finalizing. Produces a review doc in plans/planning/ (status DRAFT until finalized) and commits it to the plans branch. Invoke with /design-review <scope> where scope names a branch (TA3), a PR list (TA1,2,3), a design doc (TA-supply), or "next PR".
disable-model-invocation: true
---

# Design Review

**Arguments:** $ARGUMENTS (scope — e.g. "TA3", "TA1,2,3", "TA-supply", "next PR")

---

## Role declaration

State this at the start of the session:

> Operating as **review agent**. I read code and design docs, and write only to `plans/planning/*-review.md` files (Type 6). I do not write code, edit code files, or write into `*-plan.md` files.

Enforce this throughout. If asked to write code or edit non-review files, decline and explain the role boundary.

---

## Constraints (enforced throughout)

- **Reviewer only**: read files, never edit or create code files. No `git checkout`.
- **Output**: one `plans/planning/<scope>-review.md`, committed to the `plans` branch.
- **Document ownership** — three distinct agents, three distinct doc domains:
  - `*-review.md` → **review agent** (this skill): observations and root causes
  - `*-plan.md` → **plan agent**: implementation instructions derived from review findings
  - Code files → **coder**: executes plan docs
  - Never write into another agent's domain.
- **Status discipline**: the review doc is created with `Status: DRAFT` and updated to `Status: FINAL` only after the user explicitly confirms the findings. Other agents must not consume a DRAFT review doc.

---

## Step 1: Read session context

Read `plans/session/CURRENT.md` and `plans/session/CONVENTIONS.md`.

From CURRENT.md extract:
- Active PR table: branch → PR number, status, tip SHA
- Design doc references listed under the relevant feature section
- Implementation checklist (for "next PR" scope resolution)

---

## Step 2: Resolve scope

Parse $ARGUMENTS and map to plan docs and code packages:

| Argument form | Resolution |
|---|---|
| Branch name (e.g. "TA3") | Find in CURRENT.md PR table → collect the `TA-PR*-plan.md` docs for that branch's PR range → identify code packages from plan docs |
| PR list (e.g. "TA1,2,3") | Enumerate each branch, collect associated plan docs and code packages |
| Design doc name (e.g. "TA-supply") | Review code against `plans/planning/TA-supply.md` specifically |
| "next PR" | Find the next unchecked `[ ]` item in CURRENT.md's implementation checklist; read its plan doc |

Report the resolved scope to the user — which plan docs and code packages will be reviewed — and confirm before proceeding.

Determine the output filename from the scope:
- Branch name → `<component>-<branch>-review.md` (e.g. `TA-TA3-review.md`)
- PR list → `<component>-PR<range>-review.md` (e.g. `TA-PR1-3-review.md`)
- Design doc name → `<doc>-review.md` (e.g. `TA-supply-review.md`)
- "next PR" → use the PR identifier from the plan doc

Check that the output file does not already exist in `plans/planning/`. If it does, tell the user and ask whether to overwrite or pick a different name.

---

## Step 3: Read design and plan documents

Read all in-scope documents in this order:
1. Type 1 overall design docs referenced by CURRENT.md for this feature (e.g. `TA-supply.md`, `TA-demand.md`, `TA-overview.md`)
2. Type 3 phase plan docs for the in-scope PRs (e.g. `TA-PR4-plan.md`, `TA-PR5-plan.md`)

Build a model of:
- Intended algorithms and formulas (note them verbatim where possible)
- Invariants that must hold across all inputs
- Explicitly deferred items (not-in-this-PR)
- Design decisions recorded in the plan doc and their rationale

---

## Step 4: Read code independently

Read the implementation files **without yet checking against the design model**. Understand:
- What each exported function does
- What invariants it maintains or assumes
- Edge cases handled and not handled
- Any surprising logic or special-case paths

Form an independent understanding before comparing to design. Do not jump to conclusions based on design doc expectations.

---

## Step 5: Compare to design

Cross-reference the two models:
- **Algorithms**: does the code match the design formulas exactly? Note any discrepancy.
- **Invariants**: are they preserved across all code paths including edge cases?
- **Documented limitations**: are they correctly implemented or at least reflected in comments?
- **Not-in-scope items**: are they correctly absent? Or accidentally present?
- **Design decisions**: are they reflected in code and consistent with recorded rationale?

---

## Step 6: Classify findings (draft)

Assign each finding to one of:

| Class | Meaning |
|---|---|
| **Bug** | Must fix before merge: violated invariant, wrong formula, missing guard, incorrect behavior |
| **Doc gap** | Correct logic but non-obvious reasoning is unexplained; comment-only fix |
| **NTH** | Nice-to-have improvement; not blocking merge |
| **Confirmed correct** | Something that looks suspicious but is intentional; document to close the loop |

For bugs, record:
- Root cause (not just symptom) — enough for the plan agent to write a fix without re-reading the code
- Suggested fix direction
- Test scenario to add (the plan agent will write the exact spec)

---

## Step 7: Present and discuss findings

Present all findings to the user grouped by class. For each item, give:
- A short title
- One paragraph: what the issue is, why it matters, suggested fix direction

Then **wait for the user to respond to each finding**. The user may:
- Confirm the finding as stated
- Correct the framing or root cause
- Reclassify the item (e.g. "not a bug, intentional design decision X")
- Dismiss the item ("confirmed correct — here is why")
- Request deeper investigation before deciding

Work through all findings collaboratively. Update your understanding after each correction. Do not proceed to Step 8 until the user has reviewed and responded to all findings and explicitly says the review is ready to finalize (e.g. "finalize", "looks good", "write the doc").

---

## Step 8: Write review doc (DRAFT → FINAL)

Write `plans/planning/<output-filename>` incorporating all corrections from the discussion:

```
# <Component> Review — <scope>

**Status:** FINAL
**Branch reviewed:** <branch> (HEAD `<sha>`, covers <PR range>)
**Reviewed:** <date>
**Scope:** <packages / design docs covered>

---

## Summary

<2–3 sentences on overall correctness and what was found>

---

## Bugs (must fix before merge)

### Bug N — <title>

**Root cause:** ...
**Suggested fix direction:** ...
**Test to add:** ...

---

## Documentation gaps

### Doc N — <title>

**Suggested comment:** ...

---

## Nice to have

### NTH N — <title>

...

---

## Confirmed correct

- <item>: <why it was suspected and why it is correct>
```

If the doc was previously committed as a DRAFT (e.g. from a partial earlier run), overwrite it and update the status to FINAL.

Commit the review doc and drop a handoff file for the plan agent:

1. Stage the review doc.
2. Write `plans/session/handoffs/<scope>-review.md`:

```
to: plan-agent
doc: planning/<output-filename>
status: FINAL
note: <one sentence — what was reviewed and what kind of findings>
```

3. Commit both together:

```bash
mkdir -p plans/session/handoffs
git -C plans add planning/<output-filename> session/handoffs/<scope>-review.md
git -C plans commit -m "planning: <scope> code review [FINAL]"
```

Print the commit SHA and the file path when done. Tell the user to run `/sync-current` when they want CURRENT.md updated.

---

## Note on agent roles

This skill is the **review agent**. Its output (`*-review.md`) is an input to the **plan agent**, which reads FINAL review docs and writes `*-plan.md` implementation instructions. The **coder** executes plan docs. These roles are distinct — each agent reads only its upstream and writes only to its own domain.
