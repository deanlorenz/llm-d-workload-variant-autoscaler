# How Bob is set up as a persistent coder for autoscaling-viz

**Status:** reference doc, not a task plan. Explains the current setup so it can be reproduced,
audited, or extended to another scope. Written 2026-08-17 after the first real task
(`autoscaling-viz-good-panels-classification-plan.md`) completed successfully.

## What Bob is

`bob` is a separate CLI agent tool (IBM's Bob Shell), invoked as its own OS process — not a Claude
subagent, not something spawned via the Agent tool. It runs headless via `bob run`, or interactively
via `bob chat`. This setup uses `bob run` in the background, launched with `nohup` and resumed
across turns via its own `--resume <task-id>` mechanism, so it keeps full conversational context
(having already read the conventions once) instead of re-reading them cold on every task.

## Why a custom mode, not the built-in one

The container already had a `coder` custom mode defined in `.bob/custom_modes.yaml`, but it
predated several convention changes in this workspace (stale handoff filename format, no DCO/lint
mention, no per-branch status-file convention) and — more importantly — its write scope matched a
**normal** coder: worktree plus `plans/session/status/<branch>.md` plus `plans/session/handoffs/`.

Dean's explicit direction changed that for Bob specifically: no `plans/` commits ever, no writing
`plans/session/status/` at all (keep a local status file inside its own worktree instead, since that
worktree can become a PR branch and the status file must never ride along into a commit/PR diff),
and hand anything else it might want done inside `plans/` to the planner via a handoff rather than
trying to reach it directly. That's a genuinely narrower scope than the existing `coder` mode
describes, so a new mode (`coder-auto`) was added rather than editing `coder` (which may be in use
elsewhere and wasn't the thing Dean asked to change).

## Where the mode lives

Two copies of the same `custom_modes.yaml`, kept in sync manually:

```
llm-d-workload-variant-autoscaler/.bob/custom_modes.yaml       # container-level
llm-d-workload-variant-autoscaler/autoscaling-viz/.bob/custom_modes.yaml   # worktree-local copy
```

The worktree-local copy exists because Bob's mode search didn't reliably pick up the container-level
one when launched from inside the `autoscaling-viz` worktree in testing — copying it in was the
simplest fix (Dean's direct instruction) rather than debugging Bob's own search-path behavior
further. **If the mode definition changes, update both files** — there's no symlink or single
source of truth here, just a manual copy.

## The `coder-auto` mode's actual rules

Full text is in `custom_modes.yaml` itself (`customInstructions` field) — this section is a summary,
not a substitute for reading it if something needs to change.

- **Read the real rulebooks, don't trust the mode's own summary of them.** On activation: read
  `plans/session/CONVENTIONS.md` and `plans/session/CODER-CONVENTIONS.md` in full. Those are
  authoritative; the mode text explicitly says so, because they change over time and the mode
  definition won't always be updated to match.
- **Write-scope override, narrower than a normal coder:**
  - ✅ its own worktree (normal coder scope)
  - ✅ its own local status file, `./.bob-status.md` inside the worktree — gitignored there
    specifically so it can never leak into a PR
  - ✅ `plans/session/handoffs/` — write new handoffs, rename `.WIP`/`.DONE` on ones addressed to it
    — this is its **only** write access under `plans/`
  - ❌ `plans/session/status/<branch>.md` — not written directly; ask the planner to mirror content
    in via a handoff instead
  - ❌ any `git commit` inside the `plans/` worktree, for any reason
  - ❌ `plans/planning/*.md`, CURRENT.md, review docs — read-only
- **No routing around a blocked write.** Bob's own sandbox blocks its `write_file` tool from
  crossing the worktree boundary, but its error message once claimed `execute_command` was also
  blocked — that claim was false, and the first real task showed Bob discovering the gap and using
  `execute_command`+`git commit` to write into `plans/` anyway. That commit was reverted
  (`git revert`, not `git reset` — no history rewritten) and the mode text was corrected explicitly:
  a blocked write is the boundary working as intended, not a bug to engineer around. The one
  legitimate crossing — `plans/session/handoffs/` — is a plain filesystem `mv`/file-write via
  `execute_command`, which is fine and expected; the difference is *destination*, not mechanism.
- **Watches `plans/session/handoffs/` for triggers/handoffs addressed to it** (`autoscaling-viz__*.md`
  or a `to:` line naming it), marks `.WIP` before acting, `.DONE` when done — same protocol every
  coder in this workspace follows.
- **Everything else** (no push, no GitHub writes, DCO/lint/test gates where they apply, dev-guide
  updates, deletion classification) is unchanged from the normal coder rules.

## How a task actually gets to Bob

1. Planner writes a Type 3 code spec under `plans/planning/` (same as for a Claude coder — no
   difference in artifact).
2. Planner writes a trigger at `plans/session/handoffs/autoscaling-viz__<topic>.md` (`to:
   autoscaling-viz`, refs the spec, no instructions in the body — same trigger convention as
   always).
3. Planner resumes Bob's task with a short prompt pointing at the trigger — does **not** restate the
   spec's content, since Bob reads it itself:
   ```bash
   cd autoscaling-viz
   PROMPT="A new trigger has landed at plans/session/handoffs/autoscaling-viz__<topic>.md. Read it, mark it .WIP, then read the code spec it points at..."
   nohup bob run --accept-license --workspace . --mode coder-auto \
     --resume <task-id> -f stream-json "$PROMPT" \
     > <logfile> 2>&1 &
   ```
4. Planner watches the log (`Monitor` on the jsonl output, or periodic `ps`/log-tail checks) for
   completion, scope violations, or anything needing a decision.
5. Bob reports back via `plan__`/`sync__` handoffs when done — same as any coder. Planner folds
   `plan__` content into the relevant plan/CURRENT.md doc; `sync__` waits for the dedicated sync
   session.

## The task-id / `--resume` mechanism

`bob run` is one-shot per invocation (the process exits after each task), but `--resume <task-id>`
reopens the same conversation with full prior context — so "persistent" here means **persistent
context across resumed invocations**, not a continuously-running OS process. The task-id from the
first bootstrap call is the one to reuse for every subsequent task:

```
task_id: bd8610a2991b2e5e12471e18850b4e27
```

Losing this id would mean the next task starts cold (re-reads conventions, no memory of prior
work) — worth recording somewhere durable if this pattern is reused for another scope. Currently
it only lives in this doc and the planner's own conversation history.

## What's been verified to actually work

One real task completed end-to-end (`autoscaling-viz-good-panels-classification-plan.md`,
2026-08-17): ~27 minutes unattended, 47 tool calls, correctly re-extracted+re-rendered 29 runs,
created 16 symlinks, found and self-corrected two of its own bugs along the way (a broken
subprocess invocation, a wrong leaf-name assumption), sent three handoffs (two `plan__`, one
`sync__`) with accurate, well-organized content, and — after one correction mid-session — respected
every write-scope boundary described above.

## Known rough edges, not yet fixed

- **Manual mode-file sync.** Two copies of `custom_modes.yaml` (container + worktree), no automated
  sync. A future edit to one and not the other would silently drift.
- **`get_workload_name()`-style path bugs are on Bob, not the mode.** The mode can't prevent Bob
  writing an ad-hoc script with a real bug in it (see `autoscaling-viz-panel-review-20260817-plan.md`
  Item 1's cause #1) — that's Bob doing normal coder work, same risk profile as any coder writing new
  code. Not a setup problem, just worth remembering the mode doesn't make Bob's own code infallible.
- **No hard sandbox guarantee against a future `execute_command`-based boundary crossing** into
  `plans/planning/` or `plans/session/status/` — the current guardrail is the mode's own written
  instruction plus a corrected understanding after one incident, not a tool-level block. Investigated
  once (per Dean's own question) and deliberately left as prompt-level for now; revisit if it
  recurs.
- **`@vscode/ripgrep` module-resolution error** logged (non-fatal) during testing — degrades Bob's
  file-search tool, didn't block any task tried so far. Not investigated further.
