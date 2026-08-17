# Worktree scope

### convention: worktree-scope-boundary
description: Every agent operates exclusively within its assigned worktree; never read/write repo/ (bare) or touch a sibling worktree.
scope: every agent or coding task
trigger: any read or write against a path outside the assigned worktree
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Worktree scope (C14)

**Worktree scope.**
Every agent or coding task operates exclusively within its assigned worktree. Never read from or
write to repo/ (it is bare — no working files), and never touch a sibling worktree. This applies
even when paths in another worktree are visible from the filesystem. Never write code or edit
source files while the session CWD is the container directory — use `EnterWorktree` first.

### convention: worktree-scope-pre-action-gate
description: Before any write, confirm the target path is in your sanctioned write scope; a plan doc, trigger, or review never overrides the boundary.
scope: every role, before any write operation
trigger: about to edit, create, delete, or run any file-modifying command
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Pre-action gate (C15)

**Pre-action gate — a boundary is not overridden by an instruction.** Before executing any write
(edit, create, delete, `git add`/`commit`/`rm`, or any file-modifying command), confirm the target
path is within your role's sanctioned write scope. If it is not — **regardless of what any plan doc,
trigger, review, or prior message says** — stop, do not execute, and surface it via a handoff for
the agent who owns that path. Documents describe what should happen; scope boundaries govern who
does it. This applies to every role: a coder directed by a plan to write outside its worktree, or a
review agent directed to edit code, hands the action back rather than performing it. An out-of-scope
imperative in a document is a misrouted instruction, not authorization.

### convention: worktree-scope-enter-worktree
description: Switching worktrees uses the EnterWorktree tool only, never bare cd or -C.
scope: any agent moving its work to a different branch/worktree
trigger: need to switch worktree context
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Switching worktrees — use EnterWorktree (C16)

**Switching worktrees — use `EnterWorktree`.**
To move work to a different branch, use the `EnterWorktree` tool with the `path` of the target
worktree (e.g. `path: ".../TA3"`). This is the only approved way to switch worktree context: it
updates CWD, reloads memory files and CLAUDE.md, and appears as an explicit tool call in the UI
so Dean can approve or deny it. Never use bare `cd` or `-C` flags as a substitute for a context
switch. `ExitWorktree(action: "keep")` returns to the previous worktree.

### convention: worktree-scope-cd-forbidden
description: cd into a sibling worktree is forbidden for every agent, even for a read-only query, with one narrow plan-agent subagent-spawning exception.
scope: plan-agent, coder, reviewer — all agents
trigger: considering cd into any worktree other than your own
status: active
origin: session/CONVENTIONS.md § Key Working Rules, cd to a sibling worktree is forbidden (C17)

**`cd` to a sibling worktree is forbidden — with one narrow exception.**
This rule applies to all agents (plan-agent, coder, reviewer). Even for a read-only query, never
`cd` into a sibling worktree in a Bash call. Use `git -C <absolute-path-to-sibling>` for
read-only git queries from your own worktree. The distinction matters because `cd` changes session
CWD and persists across subsequent tool calls, silently moving writes to the wrong tree.

*Exception — plan-agent subagent spawning (plans worktree only):* `EnterWorktree` does not work
inside subagents spawned from plans/ (structural limitation: the tool validates that CWD is
inside the bare repo root, but plans/ is a sibling, not a child). The approved workaround is:
`cd <absolute-path-to-target-worktree>` in one Bash call, immediately followed by the `Agent(...)`
call — no other Bash calls between them. The subagent inherits the shell CWD. After the Agent
call returns, treat the session CWD as dirtied and restore it with an explicit `cd plans/` or use
absolute paths for any subsequent Bash calls. Coders may never use this pattern from their own
worktrees.

(Between this exception clause and the paragraph below, the source text carries the Git write-verbs
rule and the subagent-settings/`claude -p` procedure — see the `worktree-scope-git-write-verbs` and
`worktree-scope-subagent-permission-pattern` entries in this same file for that material, kept as
separate entries per the classification table's own row split.)

The subagent brief for this pattern must state:
- which worktree it is starting in and why
- that its first action must be `pwd` + `git branch --show-current` to verify CWD
- its task scope (reads unrestricted; writes only within that worktree unless the task is
  explicitly a planner handoff)

Prerequisite: `EnterWorktree` requires the session to already be inside a git repository (any
worktree). If the session starts in the container directory, `cd` into any worktree first.

**This rule has been violated repeatedly, by every role, even by the agent that just named the
risk.** Confirmed recurrences: a plan-agent chained `cd <sibling> && git log` then ran a later
`git add` from that sibling tree (caught only by luck before commit); a reviewer bare-`cd`'d into
a coder's active worktree mid-review, then — still inside that `cd`'d context — ran `git stash`
and `git checkout` while the coder was actively editing (see `worktree-scope-git-write-verbs`);
the same reviewer role repeated the bare-`cd` three more times in one later session despite
active self-monitoring, self-catching the first, missing the second until an unrelated command
failed, and repeating a third time immediately after adding a precautionary `pwd` check because
of the second. **Conclusion: a written rule is a reminder, not a gate — it can be skipped under
task pressure, especially when chained with an otherwise-harmless command.** The trigger pattern
each time was `cd <dir> && <read-only-command>` — the `&&`-chaining habit is what needs to go, not
just the eventual write. After `EnterWorktree`/`ExitWorktree`, do not add any `cd` at all, not even
back to your own current worktree — the CWD is already correct; use plain commands or absolute
paths. This is further evidence prose alone is insufficient for the reviewer role specifically,
which routinely needs sibling-worktree reads — exactly the condition that makes the `cd` shortcut
tempting — and is the standing case for a mechanical gate (hook/permission rule) rather than more
prose.

**Why `isolation: "worktree"` on the Agent tool doesn't substitute for this pattern:** that option
creates a *new, throwaway* worktree, not a handle onto an *existing* one, and the Agent tool has no
`cwd` parameter to target an existing worktree directly — the `cd` + immediately-following `Agent(...)`
call is the only way to hand a subagent an existing worktree's CWD.

### convention: worktree-scope-git-write-verbs
description: Git write-verbs (stash, checkout, reset, rebase, merge, commit, branch -D, clean) never run outside your own sanctioned scope, not even for a lookup.
scope: every agent, any git command that mutates working tree/index/refs
trigger: about to run a git write-verb against any worktree
status: active
origin: session/CONVENTIONS.md § Key Working Rules, Git write-verbs are never run outside your own sanctioned scope (C18)

**Git write-verbs are never run outside your own sanctioned scope — not even for a lookup.**
`git stash`, `git checkout` (writing working tree/index), `git reset`, `git rebase`, `git merge`,
`git commit`, `git branch -D`, `git clean` are write operations. The read-only-vs-write line
governs every one of these the same way it governs plain file edits — "I'm just checking
something" or "I'll put it back after" is not an exception, because the target worktree may be
actively edited by another agent at that exact moment, and a stash/checkout can silently capture
or clobber their in-progress, uncommitted work. If you need historical content, use
`git show <rev>:<path>` or `git log -p -- <path>` — both read-only. If you need to *execute* code
against a historical revision, use an isolated temp worktree/clone, never the shared active tree.
If you notice a file differs from what you just read (a sign the tree is being actively edited by
someone else), that is a signal to do less there, not neutral background information. If a mistake
happens anyway: stop and surface it immediately — do not chain further git-surgery commands to
self-correct; let the tree's owner direct recovery. (Incident: 2026-07-14, reviewer role; see
plans/session/CURRENT.md § Next steps — "Governance follow-up — reviewer-worktree incident
(2026-07-14)" — for the follow-up discussion on mechanical enforcement.)

### convention: worktree-scope-subagent-permission-pattern
description: A subagent spawned from plans/ inherits shell CWD but not the session's project settings; use claude -p --allowed-tools as a Bash subprocess when a task needs permissions scoped to the target worktree.
scope: plan-agent spawning a subagent that needs worktree-scoped permissions
trigger: a subagent's task needs tool permissions scoped to a worktree other than plans/
status: active
origin: session/CONVENTIONS.md § Key Working Rules, cd to a sibling worktree is forbidden — subagent settings note (C19)

The subagent inherits the shell CWD but **not** the session's project settings. Settings
for a spawned Agent are always loaded from the session's startup project (plans/), not from
the bash CWD at Agent call time. If a task needs permissions scoped to the target worktree,
use `claude -p --allowed-tools` as a Bash subprocess instead of the Agent tool:

```bash
cd <worktree> && claude -p "<task>" --allowed-tools "<tool1>,<tool2>" --no-session-persistence
```

This subprocess starts fresh with the target worktree's CWD and its own settings, and
`--allowed-tools` passes the exact permissions inline — no settings file required.

The only permission this pattern needs granted in `plans` is `Bash(claude -p *)` in
plans/.claude/settings.local.json. For a short task, run it blocking and report the
result inline; for a long task, run it with `run_in_background: true` and pick up the
result via the task notification / output file.

### convention: worktree-scope-coder-session-start-check
description: A coder verifies CWD and branch at session start, re-verifies before every edit and before every commit; two non-negotiable gates.
scope: coder agent
trigger: session start, session resume, starting a new handoff/trigger, immediately before every git commit
status: active
origin: session/CODER-CONVENTIONS.md §0 Session start — verify you're in the target worktree (CC1, CC2, CC3, CC4)

**0. Session start — verify you're in the target worktree.**

**Standard coder workflow:** Start Bob Shell from within the target worktree,
not from plans/ or the container directory.

```bash
 # Correct workflow
cd /path/to/llm-d-workload-variant-autoscaler/TA3
bob --chat-mode=coder

 # Wrong - do not start from plans/ or container
cd /path/to/llm-d-workload-variant-autoscaler/plans
bob --chat-mode=coder  # ✗ Wrong location
```

**At session start, verify your CWD:**

1. Run `pwd` and `git branch --show-current`
2. Confirm you're in the target worktree (e.g., TA3/ on branch `TA3`)
3. If not, **STOP** and inform the user:
4. Run `git status` — note ALL modified, staged, and untracked files. This is your full work scope regardless of how the session was triggered. **Never declare work done while `git status` shows uncommitted changes that belong to your branch.** A trigger names what to re-read; it does not limit your scope to its stated topic.

**Re-verify before any edit (session resume or handoff processing):**

When resuming a paused session or starting work on a new handoff/trigger,
run `pwd` + `git branch --show-current` again before the first file edit.
Shell CWD can drift between sessions. Confirm the branch name matches your
assigned worktree before touching any file.

**Re-verify before every `git commit`:**

Run `pwd` + `git branch --show-current` immediately before every commit
command. A commit issued from the wrong CWD silently lands on the wrong
branch with no error. This check costs two seconds and prevents silent
cross-branch contamination.

```bash
 # Mandatory pattern before every commit:
pwd && git branch --show-current
git add <files>
git commit -s -m "..."
```

These two gates are non-negotiable. Skip neither, even for trivial one-line
fixes. If either check shows the wrong location, stop and surface it via
your status file before proceeding.

```
ERROR: Coder session started in wrong location.

Current: /path/to/plans (branch: plans)
Expected: /path/to/TA3 (branch: TA3)

Please restart Bob Shell from the target worktree:
  cd /path/to/TA3
  bob --chat-mode=coder
```

**Why this matters:**
- `read_file` tool has path restrictions — starting in the target worktree
  makes all code files directly accessible
- All gates (`make test`, `make lint`, `git` commands) run in correct context
- Status/handoff writes never require leaving your worktree — `cp`/`mv`
  the file into plans/session/... by absolute or relative path (§1, §5).
  If you ever do find yourself outside your worktree, the fix is
  `EnterWorktree(path: <absolute-path-to-your-worktree>)`, never `cd`.

**Convenience alias (optional):**

Add to ~/.bashrc or ~/.zshrc:

```bash
 # Start Bob Shell coder in a worktree
bob-code() {
  local worktree="${1:-.}"
  if [[ ! -d "$worktree/.git" ]] && [[ ! -f "$worktree/.git" ]]; then
    echo "Error: $worktree is not a git worktree"
    return 1
  fi
  cd "$worktree" && bob --chat-mode=coder
}

 # Usage:
 #   bob-code TA3
 #   bob-code ../multi-analyzer-optimizer
 #   bob-code .  # current directory
```

### convention: worktree-scope-write-exception
description: The coder's one sanctioned write exception outside its own worktree: plans/session/handoffs/ and its own plans/session/status/<branch>.md.
scope: coder agent
trigger: writing a handoff, trigger, or status file
status: active
origin: session/CODER-CONVENTIONS.md §1 Worktree scope — single sanctioned write exception (CC5, partial)

**Single sanctioned write exception outside your worktree:** you may
write and `mv` files under plans/session/handoffs/ (your handoffs to
the planner, triggers to siblings) and write your own status file at
plans/session/status/<your-branch>.md. These are the only paths
outside your worktree where edits are allowed. See §5.

If a task seems to require touching anything else outside your worktree,
stop and write a handoff describing why — do not edit.

**Mechanism: the Write/Edit tools are blocked on these two paths from an isolated worktree
session even though the exception is sanctioned — Bash `cp`/`mv` are not blocked and are the
working recipe.** Measured directly: `Write` (new file) and `Edit` (existing file) against
session/handoffs/ are refused by the worktree-isolation guard, *even when* settings.json
allowlists `Edit()` on that exact path — the file-tool guard is unconditional and preempts the
permission allowlist, so the allowlist entry is inert. Bash `cp <worktree-file> <shared-dir>/`
and `mv <shared-dir>/x.md x.md.WIP` both work. Working recipe: draft the file in your own
worktree, Bash `cp` it into the shared directory (again to revise), `mv` to flip
.md → `.WIP` → `.DONE`. (A terminal-launched coder worktree may instead find Write/Edit
succeed in place on these two paths without the `cp` step — the launch model changes which
tools are gated, not the write-exception itself; if a direct Write/Edit fails here, fall back
to the `cp`/`mv` recipe rather than concluding the exception is inoperable.) **One refusal from
one tool is not a fact about the filesystem or the protocol** — before asserting a
protocol/infrastructure-level defect (e.g. "the state machine is inoperable across
worktrees"), test the adjacent operations, since the untested ones may simply use a different
tool. This does not widen write scope generally — default worktree locality and the
cd-forbidden rule above still hold, and git write-verbs outside your own worktree are still
never OK regardless of which tool would technically succeed.

**A doc's own early shorthand can contradict its later correct instruction, and readers absorb
the terse first version before ever reaching the fuller correct one.** CODER-CONVENTIONS.md
§0 once described this write-exception's recipe as "just `cd` to session/... for status/handoff
writes" — directly contradicting the no-bare-`cd` rule above and its own correct `cp`/`mv`
recipe three sections later. Already fixed in the source doc; the lesson survives independent
of that specific fix — when writing or reviewing a rule file, a compressed first-mention that
gets the mechanism wrong is worse than no first mention, because it's what gets read and acted
on first.

(CC5's citation also covers the edit-boundary and pre-action-gate restatements in
session/CODER-CONVENTIONS.md §1 — those duplicate `worktree-scope-boundary` (C14) and
`worktree-scope-pre-action-gate` (C15) verbatim in substance and are not re-quoted here, per the
classification table's own instruction to avoid duplicating text that already exists in the
CONVENTIONS.md version.)

### convention: worktree-scope-shared-git-index-pathspec-commit
description: In a worktree shared by concurrent sessions, never git add alone or commit -a; commit with an explicit pathspec so you can't sweep in another session's staged files.
scope: any session committing in a worktree shared by multiple concurrent sessions (e.g. plans)
trigger: about to git commit in a shared worktree
status: active
origin: feedback_shared_git_index_pathspec_commits.md

In a worktree shared by multiple concurrent sessions (e.g. `plans`), all of them share **one git
index**. A plain `git add <file>` from one session can sit in the shared index and get swept into
a totally unrelated commit by a *different* session, silently: the losing session's own
`git commit` returns "no changes added to commit" (its file was already committed by the other
session's commit), and the winning commit's message no longer accurately describes its diff — a
hard-reject condition per `rebase-integrity-commit-message-vs-diff`, triggered here with no
warning from git at all.

**Rule: in a shared worktree, never `git add` alone, never `git commit -a`, and never
`git restore --staged` someone else's staged file "to clean up."** Commit with a pathspec
instead:

```
git commit -s -m "..." -- <path> [<path> ...]
```

**Caveat for brand-new (untracked) files:** a pathspec commit only reaches paths git already
knows — it errors "did not match any file(s) known to git" on an untracked path. There is no way
to commit a new file without staging it first. Mitigation: chain
`git add <paths> && git commit -s -m ... -- <paths>` as one shell invocation, minimizing the
window the new file sits in the shared index — the pathspec on the commit itself still protects
against sweeping up *other* people's staged work.

**How to apply:** before any `git commit` in a shared worktree, use the pathspec form. If
`git status` shows staged files you don't recognize, don't `git restore --staged` them before
your commit — that would silently discard another session's work in progress; leave them and let
the pathspec do the isolating.

### convention: worktree-scope-default-locality
description: Default to your own worktree for every git operation; -C or an absolute path to a sibling is a deliberate exception for read-only history, never a reflex.
scope: every agent or coding task
trigger: reaching for -C, cd, or an absolute path to any worktree other than your own
status: active
origin: feedback_worktree_default_locality.md

**Default rule: every git operation runs from your own worktree, against your own branch.**
Exceptions are exceptions, not defaults:

- `git -C <sibling-worktree> <read-only-cmd>` — fine when you genuinely need committed code or
  history from another branch (comparing to a sibling's tip, reading a doc that exists only on
  another branch). Use an absolute path when ambiguous.
- `cd <sibling-worktree>` — almost never; see `worktree-scope-cd-forbidden` above.
- `git -C <sibling-worktree> <write-cmd>` — never without explicit Dean instruction; see
  `worktree-scope-git-write-verbs` above.

Most "I need to look at the other branch" questions are answered by `git log <other-branch>` from
your own CWD, or `Read` on the file by absolute path — neither needs `-C` or `cd`. Reaching for
`-C` or `cd` should be a deliberate choice ("I need committed state from a sibling I cannot see
from here"), not a reflex — before adding `-C` to a git command, ask whether it's answerable from
your own worktree first. When you do use `-C` or an absolute path, say so in your reply and why
the exception is needed — that keeps the discipline visible rather than silent.

### convention: worktree-scope-write-confinement-mechanism
description: How coder write-confinement is actually enforced (or not) at launch time: webview+multi-root-workspace does NOT confine; terminal-launch-from-worktree does, out of the box; bypassPermissions defeats both.
scope: anyone launching or configuring a coder session
trigger: deciding or reasoning about whether a coder session is actually confined to its worktree
status: active
origin: project_coder_write_confinement.md

The write boundary is fixed **at launch**: launch CWD (project directory) plus
`permissions.additionalDirectories`. `cd` never moves it — an out-of-scope `cd` auto-resets to
the project directory.

**The webview does NOT confine coders, contrary to the natural assumption.** A CC VSCode
extension webview running in a multi-root workspace injects **every workspace folder as a
writable `additionalDirectory`**. `EnterWorktree` only re-roots the *project directory* — it does
not prune those injected directories. So a coder that `EnterWorktree`s into its branch can still
Edit/Write into every sibling worktree listed in the workspace, with no prompt. Confinement
observed under this setup is discipline (following the conventions), not enforcement.

**Terminal-launch-from-worktree DOES confine, out of the box, zero setup.** The `claude` CLI
never reads `.code-workspace`; the workspace-folder→additionalDirectory injection is
webview-exclusive. /ide only wires diff/diagnostics/selection — it does not change the write
boundary. So `claude` launched with CWD = a given worktree has a write scope of exactly that
worktree, while reads still work globally via a broad `Read` allow-rule.

**One setup cost of switching to terminal-launch: the sanctioned cross-worktree writes
(`plans/session/handoffs/**`, plans/session/status/<branch>.md) need their own allow-rules
copied into the user-global settings file** — otherwise they prompt, since `plans` is out of
write scope from a worktree launch. Once copied (absolute paths — harmless in other projects),
Write/Edit succeed prompt-free in those two paths from a terminal-launched coder worktree, making
the `cp`-via-Bash workaround (see `worktree-scope-write-exception` above) unnecessary under this
launch model specifically — write those two paths in place instead of staging in an in-worktree
outbox directory.

**Residual hole under both launch models: `bypassPermissions` drops the boundary entirely.**
`acceptEdits` does not widen scope (still confined). So "coders never run in bypass" is the only
discipline left once terminal-launch is in place. A global `PreToolUse` hook or sandbox
filesystem-allow-write rule is the only thing that also survives bypass mode.

**Terminal-launch has its own correctness gap: it loads no coder conventions at all**, unless
the session invokes the `s-coder` skill (or equivalent) explicitly — CODER-CONVENTIONS.md is
imported only by the file the terminal-launched worktree's own CLAUDE.md chain does not reach.
A confinement fix that doesn't also carry the rulebook to the confined session is a regression
disguised as a win: no worktree-scope rules, no handoff protocol, no DCO discipline, no pre-push
checklist reach a coder that launched this way and never loaded them by hand.
