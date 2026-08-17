# Semantic pivot grep

### convention: semantic-pivot-grep
description: A behavioral-contract change requires a companion grep step naming the search term and files to scan, run before committing.
scope: planner authoring a plan step that changes a behavioral contract; coder executing that step
trigger: rename, panic-to-error, sync-to-async, or any other behavioral-contract change
status: active
origin: session/CONVENTIONS.md § Document Taxonomy, Type 3 (C7); session/CODER-CONVENTIONS.md §3 Semantic-pivot cross-reference check (CC8)

From session/CONVENTIONS.md § Document Taxonomy, Type 3 — task plan (the planner-authoring statement):

Any step that changes a function's behavioral contract (rename, panic→error, sync→async,
etc.) must include a companion verification step: the exact `grep` search term and the files
to scan for stale cross-references in comments and docstrings. The coder executes this grep
and updates every hit before committing. If the plan omits this step, the coder writes a
handoff noting the gap rather than inferring scope.

From session/CODER-CONVENTIONS.md §3 — Semantic-pivot cross-reference check (the coder-execution statement):

**Semantic-pivot cross-reference check.** When the plan specifies a behavioral contract
change (rename, panic→error, sync→async, etc.), the plan will include a grep step with the
old search term and files to scan. Run that grep after implementation and update every hit
in comments and docstrings. If the plan omits the grep step, do not infer scope — write a
handoff to the planner noting the gap and what term to search.
