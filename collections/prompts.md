# Pre-packaged prompts

Same marker as a role/step-collection (`members` + fetchable-by-name), but the body is a fuller
task write-up — "here is what you need to do to fulfill this step, here is the checklist to make
sure it's done correctly" (Dean's own framing, `micro-rules-migration-plan.md`'s Step 4.3 line) —
rather than a bare reference list. A prompt fills in with concrete values at the point it's fetched;
the members are what a caller should also load before starting.

### collection: rebase-a-live-branch
description: Pre-packaged checklist for rebasing a multi-commit stack onto a moved base.
members: rebase-integrity-commit-message-vs-diff, worktree-scope-shared-git-index-pathspec-commit
trigger: about to rebase a branch with more than one commit, where the base has moved underneath it
status: active
origin: session/CONVENTIONS.md § Commit messages must reflect the diff; conventions/rebase-integrity.md

**Before rebasing**, confirm this actually needs the full procedure below: a single-commit rebase, or
one that applies cleanly with no conflicts, doesn't. It applies when BOTH are true — a multi-commit
stack, AND at least one touched file has been modified on the new base.

If both hold:

0. **Write a pre-rebase plan first**, not after. Ordered commit list, one-line "behavior to preserve"
   per commit (mined from its own message), files expected to conflict, and the post-rebase
   verification checklist you'll run. Where it lives depends on your role's write scope — a coder
   records it in its own status file or a handoff, never under plans/planning/ directly.
1. **Run the rebase.**
2. **Per-file diff inventory.** For each touched file, `git diff <pre-rebase-tip> <post-rebase-tip> --
   <file>` and confirm every claimed behavior in the rebased commits' messages is still present.
3. **Per-commit message-vs-diff check.** Read each post-rebase commit's diff against its own message.
   A message that says "Engine populates Score" with no matching hunk is a broken commit, not a
   passable one — fix before considering the rebase done.
4. **Backstop test**, where feasible: a test asserting the claimed behavior, added *before* the
   rebase, so silent loss converts to a red test rather than an eyeball miss.

**Never rebase a branch with an open PR without Dean's explicit go-ahead** — a plan step that requires
it is a signal the plan is wrong, not authorization. Assemble integration branches by merging
un-rebased branches into a throwaway instead, if that's what's actually needed.

### collection: dispatch-and-verify-a-background-coder
description: Pre-packaged checklist for handing mechanical harvest/build work to a background coder and independently verifying its output.
members: worktree-scope-shared-git-index-pathspec-commit, doc-ownership-boundary-discuss-before-implementing
trigger: about to spawn a background coder for judgment-already-made mechanical work, or about to accept its report
status: active
origin: this migration's own Step 2a/2b pattern, 2026-08-17

**Before dispatching:** the judgment calls must already be made (a classification table, a plan doc)
— a coder executes, it doesn't re-decide placement. Write the brief to a file, not inline, so it's
reviewable before the dispatch. The brief must state explicitly: exact scope (which rows/files), what
NOT to touch (source files, other roles' directories, anything flagged ambiguous), that it must not
push or mark its own work done, and where to write its status file.

**Dispatch:** `claude --bg --permission-mode auto --add-dir <any path it needs read access to
outside its own worktree> -- "$(cat brief.md)"` — the `--` separator is required, `--add-dir` is
variadic and will otherwise swallow the prompt string as another directory argument.

**While it runs:** poll via `claude agents --json`, not `claude logs` (raw ANSI, not useful) and
never by reading its transcript file directly (full JSONL conversation, will overflow your own
context). If two coders might touch the same file concurrently, check their declared scopes for a
real collision before assuming "fine if you're careful" — stop one if a genuine collision exists.

**When it reports done — verify, don't just read the commit message:**
1. Run the project's own lint/structural check tool on whatever it built.
2. `git status`/`git diff --stat` on every source file it claims it left untouched — confirm empty.
3. Spot-check at least one output entry word-for-word against its real source, not just the
   commit message's summary of it.
4. Read its status file in full, including anything it flagged as ambiguous or skipped — that's
   often more informative than what it successfully completed.
5. Run the full test suite if one exists, and confirm the diff of what changed is exactly what the
   brief scoped, nothing more.

**Committing your own work alongside a still-running coder:** never `git add -A`. Stage and commit
your own files by explicit pathspec only, leaving the coder's uncommitted changes in the working
tree untouched — the shared git index makes a blanket add unsafe.
