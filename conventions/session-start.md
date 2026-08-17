# Session start

### convention: session-start
description: Coder sessions invoke /s-coder before touching any file, since CODER-CONVENTIONS.md is not auto-loaded.
scope: any coder session, at session start
trigger: session start, in any worktree, whether launched there or moved there via EnterWorktree
status: active
origin: session/CONVENTIONS.md § Agent roles and document ownership (C12)

**Coder sessions: invoke /s-coder before touching any file.** session/CODER-CONVENTIONS.md is
**not** auto-loaded — it used to be imported by plans/CLAUDE.md, which meant every planner, chat and
sync session paid for it while the sessions that actually needed it did not get it: code worktrees
carry only the upstream CLAUDE.md (`see @AGENTS.md`), and `EnterWorktree` re-roots the chain, so a
coder launched in a worktree — or one that moved into it — loaded none of its rules. The `s-coder`
skill loads it on demand and is reachable from every worktree via the container .claude/skills/
symlink. This applies to both launch paths: started in `plans` then `EnterWorktree`, or started
directly in the worktree.
