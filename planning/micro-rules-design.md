# Micro-Rules Design

**Status:** DESIGN — brainstormed 2026-06-19. Next session: refactor existing conventions into this structure.

---

## Reading Protocol

Read only this section and the TOC. Build a todo list.
Fetch each step with `Read <this-file> offset:<start> limit:<count>` where count = end - start + 1.
Do not read past the TOC unless fetching a specific section.

---

## TOC

- [Problem](#problem) L36:48
- [Solution Overview](#solution-overview) L49:64
- [Type 1 — Repeating Action Rules](#type-1--repeating-action-rules) L65:132
  - [Directory structure](#directory-structure) L67:84
  - [INDEX.md format](#indexmd-format) L85:100
  - [How it works](#how-it-works) L101:109
  - [Rule file format](#rule-file-format) L110:132
- [Type 2 — One-Off Sub-Task Detail](#type-2--one-off-sub-task-detail) L133:234
  - [Document structure](#document-structure) L135:148
  - [Region 1 — Reading Protocol](#region-1--reading-protocol) L149:163
  - [Region 2 — TOC](#region-2--toc) L164:185
  - [Region 3 — Content sections](#region-3--content-sections) L186:211
  - [Type 1 citations in the TOC](#type-1-citations-in-the-toc) L212:223
  - [Fetching a section](#fetching-a-section) L224:234
- [TOC Refresh Script](#toc-refresh-script) L235:252
- [Integration: CLAUDE.md Changes](#integration-claudemd-changes) L253:273
- [Still To Design](#still-to-design) L274:293
- [Next Session](#next-session) L294:302

## Problem

Conventions docs have grown too long. Rules read at session start lose to accumulated context by
the time a gate runs. By hour 3 of a session, "run make lint and fix all failures" is overridden
by "it basically passes, the one failure is minor."

Adding more prose to conventions has made this worse. The fix is to inject rules **just in time**,
at the moment they're needed — not at session start.

[↑ TOC](#toc)

---

## Solution Overview

Two complementary types of micro-rules:

**Type 1 — Repeating action rules:** Small standalone files, one per action type. The planner
cites the relevant file in the plan step. The coder reads it at that moment. Rule enters context
fresh, not hour-old.

**Type 2 — One-off sub-task detail:** The plan document itself, structured so agents read only
what they need. A TOC with markdown links and line ranges lets any agent fetch exactly the right
section without loading the full document.

[↑ TOC](#toc)

---

## Type 1 — Repeating Action Rules

### Directory structure

```
plans/rules/
  INDEX.md              ← auto-loaded via @rules/INDEX.md in plans/CLAUDE.md
  code-deletion.md
  pre-push.md
  rebase-pre.md
  rebase-post.md
  dev-doc-update.md
  ...
```

Flat directory. Naming convention: `<trigger>-<topic>.md`. Full path is always cited in the
plan step, so no discovery burden on the coder.

[↑ TOC](#toc)

### INDEX.md format

Modeled exactly on MEMORY.md — one line per rule, full path + one-line description:

```markdown
# Rules Index

- [code-deletion](rules/code-deletion.md) — classify every deletion as DEPRECATED or DEFERRED before committing
- [pre-push](rules/pre-push.md) — gofmt, test, lint, DCO, build checklist (run in order)
- [rebase-pre](rules/rebase-pre.md) — write pre-rebase plan before any non-trivial rebase
- [rebase-post](rules/rebase-post.md) — per-file diff + per-commit message-vs-diff check
- [dev-doc-update](rules/dev-doc-update.md) — name the exact sections before coding, not "update the dev guide"
```

[↑ TOC](#toc)

### How it works

1. `@rules/INDEX.md` is added to `plans/CLAUDE.md` — always in context for planner sessions.
2. Planner spots an action type → finds the rule in INDEX → cites the full path in the plan step:
   `"Before this step, read rules/code-deletion.md."`
3. Coder reads the cited file at that step. Rule is fresh in context.

[↑ TOC](#toc)

### Rule file format

Small — no reading protocol needed (these are short by design). Just the checklist or rule, no
preamble. A coder reading one of these files should be able to follow it immediately.

Example `rules/code-deletion.md`:
```markdown
# Code Deletion Rule

Before committing any removal of a file, function, struct, or significant block:

1. Classify: **DEPRECATED** (gone, no future work) or **DEFERRED** (design intent preserved).
2. For DEFERRED: one paragraph — what it did, why removed now, where future version lands.
3. Record the classification in your handoff to the planner.

The planner captures DEFERRED items in the relevant design doc and CURRENT.md Issues to Open.
Nothing is silently deleted.
```

[↑ TOC](#toc)

---

## Type 2 — One-Off Sub-Task Detail

### Document structure

Every plan document has three regions, in this order:

```
## Reading Protocol    ← always read, short
## TOC                 ← always read, line ranges + md links
## <section 1>         ← content, fetched on demand
## <section 2>
...
```

[↑ TOC](#toc)

### Region 1 — Reading Protocol

Boilerplate that appears verbatim at the top of every plan document:

```markdown
## Reading Protocol

Read only this section and the TOC below. Build a todo list from the TOC entries.
Fetch each step with: `Read <this-file> offset:<start-line> limit:<line-count>`
where line-count = end-line − start-line + 1.
Do not read past the TOC unless fetching a specific step.
```

[↑ TOC](#toc)

### Region 2 — TOC

One entry per section, indented to match header depth. Each entry is a markdown link
(GitHub-style anchor) plus a line range `L<start>:<end>`:

```markdown
## TOC

- [Step A — Setup](#step-a--setup) L42:89
  - [Step A.1 — Clone repo](#step-a1--clone-repo) L68:79
  - [Step A.2 — Install deps](#step-a2--install-deps) L80:89
- [Step B — Implement](#step-b--implement) L90:145
- [Step C — Verify](#step-c--verify) L146:180
```

Line range is inclusive. To fetch Step A (including sub-steps): `offset:42 limit:48`.
To fetch only Step A.1: `offset:68 limit:12`.

The TOC is the only place line numbers live — keep it accurate via the toc-refresh script.

[↑ TOC](#toc)

### Region 3 — Content sections

Standard markdown headers. Any nesting depth is fine. Each section ends with a back-to-TOC link:

```markdown
## Step A — Setup

...detail...

### Step A.1 — Clone repo

...detail...

[↑ TOC](#toc)

### Step A.2 — Install deps

...detail...

[↑ TOC](#toc)

## Step B — Implement
```

Back-to-TOC links are added automatically by `toc-refresh.sh`. The planner may add them manually during authoring; the script will not duplicate them.

### Type 1 citations in the TOC

The planner can add rule citations directly in the TOC entry, keeping them visible at the
planning level without burying them in section prose:

```markdown
- [Step A.3 — Remove old handler](#step-a3--remove-old-handler) L110:125
  *(before: read [rules/code-deletion.md](rules/code-deletion.md))*
```

[↑ TOC](#toc)

### Fetching a section

Given `L42:89` in the TOC:
- `Read <file> offset:42 limit:48`  (limit = 89 − 42 + 1)

The Read tool uses 1-based line numbers for offset.

[↑ TOC](#toc)

---

## TOC Refresh Script

`plans/scripts/toc-refresh.sh` — does three things in one invocation:
1. Adds missing `[↑ TOC](#toc)` links at the end of each section
2. Regenerates the `## TOC` block with GitHub-style anchors and `L<start>:<end>` ranges
3. Runs step 2 twice internally to stabilize line numbers (transparent to the caller)

Convention:
- Planner runs it as the last step before writing the trigger to the coder.
- If a plan doc is edited mid-session (step added, section moved), run it again.
- Idempotent — safe to run multiple times.

See the script itself for anchor-generation rules and back-to-TOC placement logic.

[↑ TOC](#toc)

---

## Integration: CLAUDE.md Changes

Two changes needed to activate this system:

1. Add to `plans/CLAUDE.md` (after existing `@session/` refs):
   ```
   @rules/INDEX.md
   ```

2. Add to `plans/CLAUDE.md` (in conventions / plan authoring guidance):
   > Every plan document must begin with a `## Reading Protocol` block and a `## TOC` block
   > with line ranges. Run `plans/scripts/toc-refresh.sh <file>` before handing the plan to
   > a coder. Cite relevant rule files from `rules/INDEX.md` in plan steps.

The rules directory and individual rule files are created as part of the conventions refactor
(next session).

[↑ TOC](#toc)

---

## Still To Design

**Hooks approach (not yet brainstormed):**
Claude Code `PreToolUse`/`PostToolUse` hooks in `settings.json` can enforce mechanical rules
at the action point, independent of what the coder remembers. This could:
- Intercept `git commit` → check DCO sign-off automatically
- Intercept `Edit`/`Write` → verify target path is in sanctioned scope
- Reduce or replace some type-1 rule files for purely mechanical checks

This is the stronger enforcement layer (doesn't rely on the coder remembering to read a file).
Brainstorm not yet done — separate session.

**Deferred:**
- Back-to-TOC link automation in toc-refresh.sh (v2)
- Rule file templating / authoring guide

[↑ TOC](#toc)

---

## Next Session

Refactor existing conventions into this structure:
1. Create `plans/rules/` with initial rule files (code-deletion, pre-push, rebase-pre/post, dev-doc-update, ...)
2. Update `plans/CLAUDE.md` to add `@rules/INDEX.md`
3. Retrofit key active plan docs (or at minimum establish the template for new ones)
4. Brainstorm hooks approach

[↑ TOC](#toc)
