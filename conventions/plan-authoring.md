# Plan authoring

### convention: plan-authoring-micro-rules
description: New Type 3 task plans follow the micro-rules structure: Reading Protocol, TOC block with line ranges, on-demand content sections, rule-file citations.
scope: planner authoring or handing off a Type 3 / code-spec doc
trigger: starting a new task plan, or handing one to a coder
status: active
origin: session/CONVENTIONS.md § Plan document authoring (Type 3 task plans) (C10)

**Plan document authoring (Type 3 task plans).**

New task plan documents follow the micro-rules structure (see planning/micro-rules-design.md):

1. **Reading Protocol block** — 3-line boilerplate at the top telling agents to only read the TOC,
   then fetch sections on demand. Copy verbatim from the design doc.
2. **TOC block** — markdown links with `L<start>:<end>` line ranges, one entry per section.
3. **Content sections** — fetched on demand via `Read <file> offset:<n> limit:<m>` (limit = end−start+1).
4. **Rule file citations** — when a step involves a repeating-rule action (code deletion, pre-push,
   rebase, dev-doc update), add a citation in the TOC entry or step prose:
   `*(before: read [rules/code-deletion.md](rules/rules-deletion.md))*`

**Before handing any plan doc to a coder**, run:

```bash
bash plans/scripts/toc-refresh.sh <plan-file.md>
```

This adds missing `[↑ TOC](#toc)` links and regenerates line ranges in the TOC. Idempotent — run
again after any structural edit (section added, moved, or removed).

⚠️ **Corrected 2026-08-10.** This sentence used to claim the available rule files were listed in
plans/rules/INDEX.md, "added to CLAUDE.md; always in context". Both halves were false — that path has
never existed and plans/CLAUDE.md never imported it, so anyone following it hit a dead end. The
replacement is `conventions/`, fetched by name with `conv <name>` and needing no index file; see
[planning/atomic-step-protocol-design.md](../planning/atomic-step-protocol-design.md)
§ Micro-conventions. It does not exist yet either — it is built in that design's Migration 1 — so until
then there are no rule files to cite.

### convention: plan-authoring-devguide-sections
description: A Type 3 plan touching files with a dev-guide counterpart must name the specific sections and what changes, not just say 'update the dev guide.'
scope: planner authoring a Type 3 plan whose scope touches dev-guide-covered code
trigger: writing or finalizing a Type 3 plan
status: active
origin: session/CONVENTIONS.md § Type 3 plans must name specific dev-guide sections (C35)

**Type 3 plans must name specific dev-guide sections, not just say "update the dev guide."**
Any Type 3 task plan that touches files with a dev-guide counterpart must enumerate, per
commit, exactly which sections of which docs/developer-guide/ files need to change — and
*what* changes (add, modify, remove). "Update the dev guide" without specifics is not
actionable for a coder and leads to stale docs after merge. If the planner is unsure which
sections are affected, that is a signal to re-read the current Type 4 doc before finalising
the plan. A coder that cannot find the dev-guide section in the plan must write a handoff
noting the gap rather than skipping the doc update.
