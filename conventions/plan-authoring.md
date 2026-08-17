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

### convention: plan-authoring-no-other-role-actions
description: A Type 3 task plan must never contain an imperative verb describing another role's action; the coder reading the plan executes every sentence as its own scope, even inside a 'deferred' section.
scope: planner authoring or finalizing a Type 3 plan, or a trigger note field
trigger: finalizing a Type 3 plan doc, or writing a trigger note field that quotes/summarizes plan content
status: active
origin: feedback_plan_doc_no_other_role_actions.md

A Type 3 task plan doc is the coder's **sole authoritative scope** — every imperative sentence in
it reads as "this is what I (the coder) should do." Writing a planner-owned or Dean-owned action
item into the plan using action verbs ("launch a research agent," "run X," "do Y when coding
starts") gets executed by the coder, even inside a section explicitly labeled "Deferred" or
"NOT a blocker" — a deferred/non-blocking label only means "not gating," not "not mine." Before
finalizing any Type 3 plan doc, scan every sentence for action verbs (launch, run, spawn, file,
open, ping, notify, deploy, push, post) and ask "who is the subject?" If the answer is "me, the
planner" or "Dean," that content does not belong in the plan doc at all — put it in CURRENT.md
next-steps or a planner-only task list instead. If an out-of-scope fact/question must be
*referenced* for context (so the coder understands why something is deferred), phrase it as inert
prose with an explicit scope disclaimer: "recorded here for context only... the coder does not act
on this — it is not a commit, not a test, not a research task for this worktree." Apply the same
scan to kickoff/trigger `note:` fields — a note must describe what changed in the refs, never what
should happen next, even when quoting or summarizing a plan section. This is a general Type 3
authoring check, not specific to research agents — any planner/Dean-owned action (file an issue,
notify a sibling, decide a threshold) is equally at risk if phrased as an instruction inside a
coder's plan.

### convention: plan-authoring-relative-links-worktree-boundary
description: Links inside a doc should be relative for GitHub/clone portability, but a relative link can never cross into a different worktree; verifying the target exists on disk is not the same check as verifying the link resolves for a reader.
scope: planner or coder writing a link inside any doc
trigger: adding a link in a doc that could point at a file in a different worktree
status: active
origin: feedback_relative_links_within_docs.md

Links written inside a document (not chat) should be relative paths, scoped to that doc's own
location — this repo uses a bare-repo-plus-worktrees layout, and docs get cloned/browsed on
GitHub, where an absolute local filesystem path is meaningless. But relative markdown links
cannot walk `../../` across a worktree boundary the way a shell can, even when both worktrees
share a parent directory and the resolved path is a real filesystem path — a renderer scoped to
one repo/worktree (VSCode, GitHub) cannot follow it. **Checking that the resolved path exists on
disk is not the same question as "does this link work when clicked from where the reader
actually opens it."** A naive existence check can report zero broken links while every
cross-worktree link is still broken.

**How to apply:** before trusting a link-checker's "0 broken links" result, ask whether any
linked target lives in a different worktree than the document itself. If so, there is no
relative path that both resolves on disk *and* renders correctly in GitHub/VSCode across a
worktree boundary — this is a genuine unsolved case in this repo's layout. Ask how it should be
handled (a plain-text path for manual navigation, a documented convention, etc.) rather than
assuming a scheme works because it exists on disk. Links that stay within the same worktree as
the doc: relative, and a naive existence check is a reasonable verification. (Distinct from the
already-settled chat-message case — see `conv:chat-links` — where the fix is a workspace-relative
markdown link, not this unsolved cross-worktree case.)
